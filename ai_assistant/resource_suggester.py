"""
Pipeline Demand -> Resource Suggestion engine.
Deterministic (no LLM): for a given demand, extracts required skills from its free-text Comments,
matches them against Skillset_Matrix.csv, then ranks candidates by skill match, resource level and
current availability from DST_Bench.csv / DST_SoonTobench.csv.
"""

import re
import pandas as pd
from typing import Any, Dict, List, Optional
from .skillset_assistant import SKILL_COLUMNS, split_skill_cell
from .dst_assistant import add_bench_age_column

# DST_Bench status priority when a resource has multiple bench rows; lower = more available.
# 'Billing Started' means already engaged, so it is never treated as available.
_BENCH_STATUS_RANK = {"awaiting engagement": 0, "profile shared": 1, "onboarding started": 2}
_BENCH_UNAVAILABLE_STATUS = "billing started"


def build_skill_vocab(skillset_df: pd.DataFrame) -> List[str]:
    """Distinct skill/tool/certification names across the skillset matrix, longest first so multi-word
    skills (e.g. 'AWS Certified') are checked before any shorter skill that happens to be a substring."""
    if skillset_df is None or skillset_df.empty:
        return []
    vocab = set()
    for col in SKILL_COLUMNS:
        if col not in skillset_df.columns:
            continue
        for cell in skillset_df[col]:
            vocab.update(split_skill_cell(cell))
    return sorted(vocab, key=len, reverse=True)


def extract_required_skills(text: Any, skill_vocab: List[str]) -> List[str]:
    """Scans free-text (e.g. a demand's Comments) for any skill/tool name known to the skillset matrix."""
    if not text or not skill_vocab:
        return []
    text_lower = str(text).lower()
    found = []
    for skill in skill_vocab:
        if re.search(rf"\b{re.escape(skill.lower())}\b", text_lower):
            found.append(skill)
    return found


def _resource_skill_map(skillset_df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Precomputes {lowercased resource name -> {gpn, resource_level, skills set}} once per dataset."""
    mapping: Dict[str, Dict[str, Any]] = {}
    if skillset_df is None or skillset_df.empty or "Resource Name" not in skillset_df.columns:
        return mapping
    for _, row in skillset_df.iterrows():
        name = str(row.get("Resource Name", "")).strip()
        if not name or name.lower() == "unassigned" or name.lower() in mapping:
            continue
        skills = set()
        for col in SKILL_COLUMNS:
            if col in skillset_df.columns:
                skills.update(split_skill_cell(row[col]))
        mapping[name.lower()] = {
            "resource_name": name,
            "gpn": row.get("GPN"),
            "resource_level": str(row.get("Resource Level", "")).strip(),
            "skills": skills,
        }
    return mapping


def _best_bench_row(name: str, bench_df: pd.DataFrame) -> Optional[pd.Series]:
    """The most-available DST_Bench row for this resource name, or None if not on bench (or only
    'Billing Started', which means already engaged)."""
    if bench_df is None or bench_df.empty or "Name" not in bench_df.columns:
        return None
    matches = bench_df[bench_df["Name"].astype(str).str.strip().str.lower() == name.lower()]
    if matches.empty:
        return None
    matches = matches.copy()
    matches["_rank"] = matches["Status"].astype(str).str.strip().str.lower().map(
        lambda s: _BENCH_STATUS_RANK.get(s, 98) if s != _BENCH_UNAVAILABLE_STATUS else None
    )
    matches = matches.dropna(subset=["_rank"])
    if matches.empty:
        return None
    return matches.sort_values("_rank").iloc[0]


def _best_soon_row(name: str, soon_df: pd.DataFrame) -> Optional[pd.Series]:
    """The soonest-releasing DST_SoonTobench row (Status IN PROGRESS) for this resource name."""
    if soon_df is None or soon_df.empty or "Name" not in soon_df.columns or "Status" not in soon_df.columns:
        return None
    matches = soon_df[
        (soon_df["Name"].astype(str).str.strip().str.lower() == name.lower())
        & (soon_df["Status"].astype(str).str.strip().str.upper() == "IN PROGRESS")
    ]
    if matches.empty or "Days To Release" not in matches.columns:
        return None
    matches = matches.dropna(subset=["Days To Release"])
    if matches.empty:
        return None
    return matches.sort_values("Days To Release").iloc[0]


def resource_availability(name: str, bench_df: pd.DataFrame, soon_df: pd.DataFrame) -> Dict[str, Any]:
    """Availability for one resource name: on bench now, releasing soon, or unknown.
    tier: 0 = on bench (most available), 1 = releasing soon, 2 = unknown."""
    bench_row = _best_bench_row(name, bench_df)
    if bench_row is not None:
        status = str(bench_row["Status"]).strip()
        bench_days = pd.to_numeric(bench_row.get("Bench Days"), errors="coerce")
        bench_days = int(bench_days) if pd.notna(bench_days) else None
        detail = f"{status}" + (f" · {bench_days} day(s) on bench" if bench_days is not None else "")
        return {"status": "On Bench", "detail": detail, "tier": 0, "tie_break": -(bench_days or 0)}

    soon_row = _best_soon_row(name, soon_df)
    if soon_row is not None:
        days = int(soon_row["Days To Release"])
        end_date = soon_row.get("End Date", "")
        detail = f"On project until {end_date} · releases in {days} day(s)" if days >= 0 else \
                  f"On project, End Date {end_date} has passed (release overdue)"
        return {"status": "Releasing Soon", "detail": detail, "tier": 1, "tie_break": days}

    return {"status": "Unknown", "detail": "No bench or upcoming-release record found for this resource.",
            "tier": 2, "tie_break": 0}


class ResourceSuggester:
    """Matches Pipeline Demand rows to candidate resources using Skillset_Matrix.csv for skills and
    DST_Bench.csv / DST_SoonTobench.csv (already passed through add_release_columns) for availability.
    Purely deterministic - no LLM call, so it's fast and free to run on every filter/rerun."""

    def __init__(self, skillset_df: pd.DataFrame, bench_df: pd.DataFrame, soon_df: pd.DataFrame):
        self.skillset_df = skillset_df if skillset_df is not None else pd.DataFrame()
        # Bench Days is computed from Last Project Release Date (DST_Bench.csv no longer stores it directly)
        self.bench_df = add_bench_age_column(bench_df) if bench_df is not None else pd.DataFrame()
        self.soon_df = soon_df if soon_df is not None else pd.DataFrame()
        self.skill_vocab = build_skill_vocab(self.skillset_df)
        self.resource_map = _resource_skill_map(self.skillset_df)

    def suggest_for_demand(self, demand_row: pd.Series, top_n: int = 5) -> Dict[str, Any]:
        """Returns {'required_skills': [...], 'note': Optional[str], 'suggestions': [ranked candidate dicts]}."""
        required_skills = extract_required_skills(demand_row.get("Comments", ""), self.skill_vocab)
        required_level = str(demand_row.get("Resource Level", "")).strip().lower()
        note = None

        candidates = []
        for info in self.resource_map.values():
            matched = sorted(s for s in info["skills"] if s in required_skills)
            level_match = bool(required_level) and info["resource_level"].strip().lower() == required_level
            candidates.append({
                "resource_name": info["resource_name"],
                "gpn": info["gpn"],
                "resource_level": info["resource_level"],
                "matched_skills": matched,
                "match_count": len(matched),
                "level_match": level_match,
            })

        if required_skills:
            with_match = [c for c in candidates if c["match_count"] > 0]
            if with_match:
                candidates = with_match
            else:
                note = (f"None of the tracked resources have a skillset match for "
                        f"{', '.join(required_skills)} - showing resources at the required level instead.")
                candidates = [c for c in candidates if c["level_match"]] or candidates
        else:
            note = "No specific skill requirement was detected in this demand's Comments - ranking by resource level and availability only."
            candidates = [c for c in candidates if c["level_match"]] or candidates

        for c in candidates:
            avail = resource_availability(c["resource_name"], self.bench_df, self.soon_df)
            c["availability_status"] = avail["status"]
            c["availability_detail"] = avail["detail"]
            c["_tier"] = avail["tier"]
            c["_tie_break"] = avail["tie_break"]

        candidates.sort(key=lambda c: (-c["match_count"], 0 if c["level_match"] else 1, c["_tier"], c["_tie_break"]))
        for c in candidates:
            del c["_tier"], c["_tie_break"]

        return {"required_skills": required_skills, "note": note, "suggestions": candidates[:top_n]}

    def suggest_for_all(self, pipeline_df: pd.DataFrame, top_n: int = 3) -> pd.DataFrame:
        """One summary row per demand: detected requirement, top suggestion, and its availability."""
        rows = []
        for _, demand in pipeline_df.iterrows():
            result = self.suggest_for_demand(demand, top_n=top_n)
            top = result["suggestions"][0] if result["suggestions"] else None
            rows.append({
                "Role ID": demand.get("Role ID"),
                "Client": demand.get("Client"),
                "Resource Level": demand.get("Resource Level"),
                "Status": demand.get("Status"),
                "Detected Skills": ", ".join(result["required_skills"]) if result["required_skills"] else "-",
                "Top Suggestion": top["resource_name"] if top else "No candidate found",
                "Match": f"{top['match_count']} skill(s)" if top else "-",
                "Availability": top["availability_detail"] if top else "-",
            })
        return pd.DataFrame(rows)
