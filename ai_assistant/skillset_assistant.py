"""
Resource Skillset Matrix AI Assistant Coordinator.
Orchestrates LLM-grounded answers and a deterministic pandas fallback for Skillset_Matrix.csv.
Grounded strictly on Skillset_Matrix.csv - never mixes in data from other modules.
"""

import os
import re
import pandas as pd
from typing import Dict, Any, List, Optional
from .llm_client import LLMClient

DEFAULT_SKILLSET_CSV_PATH = "Skillset_Matrix.csv"
SKILLSET_FALLBACK_MESSAGE = "I couldn't find enough information in the Skillset Matrix data to answer that question."
SKILLSET_SOURCE_CITATION = "📊 Source: Skillset_Matrix.csv"

# Multi-value columns: each cell holds a comma-separated list of individual skills/tools.
SKILL_COLUMNS = ["Certifications", "Performance Test Tools", "Observability Tools", "AI Tools", "Others"]


def split_skill_cell(cell: Any) -> List[str]:
    """Splits a comma-separated skill cell into clean individual skill names."""
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):
        return []
    text = str(cell).strip()
    if not text or text.lower() == "unassigned":
        return []
    return [s.strip() for s in text.split(",") if s.strip()]


def skill_level_counts(df: pd.DataFrame, skill_col: str, level_col: str = "Resource Level") -> pd.DataFrame:
    """Explodes a multi-value skill column and counts (skill, level) pairs for stacked charting.
    Returns columns: [skill_col, level_col, 'Resources']."""
    if skill_col not in df.columns or level_col not in df.columns:
        return pd.DataFrame(columns=[skill_col, level_col, "Resources"])
    rows = []
    for _, row in df.iterrows():
        level = str(row[level_col]).strip()
        if not level or level.lower() == "unassigned":
            continue
        for skill in split_skill_cell(row[skill_col]):
            rows.append({skill_col: skill, level_col: level})
    if not rows:
        return pd.DataFrame(columns=[skill_col, level_col, "Resources"])
    exploded = pd.DataFrame(rows)
    return exploded.groupby([skill_col, level_col]).size().reset_index(name="Resources")


def tool_resource_matrix(df: pd.DataFrame, tool_col: str, name_col: str = "Resource Name") -> pd.DataFrame:
    """Builds a binary (tool x resource) presence matrix for heatmap charting.
    Rows are tool names, columns are resource names, values are 1 (has it) / 0 (doesn't)."""
    if tool_col not in df.columns or name_col not in df.columns:
        return pd.DataFrame()
    pairs = set()
    tools, names = set(), []
    for _, row in df.iterrows():
        name = str(row[name_col]).strip()
        if not name or name.lower() == "unassigned":
            continue
        names.append(name)
        for skill in split_skill_cell(row[tool_col]):
            tools.add(skill)
            pairs.add((skill, name))
    if not tools or not names:
        return pd.DataFrame()
    tools = sorted(tools)
    names = list(dict.fromkeys(names))
    matrix = pd.DataFrame(0, index=tools, columns=names)
    for skill, name in pairs:
        matrix.at[skill, name] = 1
    return matrix


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    """Pure-python markdown table generator (zero extra dependencies)."""
    if df.empty:
        return ""
    headers = list(df.columns)
    lines = []
    lines.append("| " + " | ".join(str(h) for h in headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[h]) for h in headers) + " |")
    return "\n".join(lines)


LIST_COLS = ["GPN", "Resource Name", "Resource Level", "Certifications", "Performance Test Tools",
             "Observability Tools", "AI Tools", "Others", "Location"]


class SkillsetMatrixAIAssistant:
    def __init__(self, csv_path: str = DEFAULT_SKILLSET_CSV_PATH, df: Optional[pd.DataFrame] = None):
        self.csv_path = csv_path
        self.raw_df = df if df is not None else self._load_csv(csv_path)
        self.llm_client = LLMClient()

    def _load_csv(self, path: str) -> pd.DataFrame:
        """Loads Skillset_Matrix.csv safely, trimming stray spaces around header names."""
        if not os.path.exists(path):
            return pd.DataFrame()
        try:
            df = pd.read_csv(path).fillna("Unassigned")
            df.columns = df.columns.str.strip()
            return df
        except Exception as e:
            print(f"[SkillsetMatrixAIAssistant] Failed to read {path}: {e}")
            return pd.DataFrame()

    def update_dataframe(self, df: pd.DataFrame):
        """Updates working DataFrame (e.g., when dashboard filter is active)."""
        self.raw_df = df.copy()

    def answer_question(self, user_question: str) -> Dict[str, Any]:
        """Main entrypoint: LLM-grounded answer first (grounded strictly on this dataset), deterministic
        pandas evaluation as fallback."""
        clean_q = user_question.strip()
        if not clean_q:
            return {
                "response": "Please enter a question about the Resource Skillset Matrix data.",
                "status": "empty_input"
            }

        if self.raw_df.empty:
            return {
                "response": f"{SKILLSET_FALLBACK_MESSAGE}\n\n{SKILLSET_SOURCE_CITATION}",
                "status": "empty_csv"
            }

        # 1. Primary Path: Direct LLM Grounded Synthesis using file data only
        if self.llm_client.is_available():
            try:
                llm_response = self.llm_client.generate_grounded_answer(
                    user_question=clean_q,
                    df=self.raw_df,
                    source_name="Skillset_Matrix.csv",
                    dataset_description=(
                        "Resource skillset matrix: certifications, performance test tools, observability tools, "
                        "AI tools and other skills held by each resource. Certifications/Tools columns each hold a "
                        "comma-separated list of individual skills for that resource."
                    )
                )
                if llm_response:
                    return {
                        "response": llm_response,
                        "operation": "llm_grounded",
                        "raw_results": None,
                        "table": None,
                        "chart_data": None
                    }
            except Exception as e:
                print(f"[SkillsetMatrixAIAssistant] LLM call failed, falling back to deterministic engine: {e}")

        # 2. Fallback Path: Deterministic Evaluation
        notice = self.llm_client.unavailable_notice()
        fast_res = self._eval_deterministic(clean_q)
        if fast_res is not None:
            if notice:
                fast_res["response"] = f"{notice}\n\n{fast_res['response']}"
            return fast_res

        return {
            "response": f"{notice}\n\n{SKILLSET_FALLBACK_MESSAGE}\n\n{SKILLSET_SOURCE_CITATION}" if notice else f"{SKILLSET_FALLBACK_MESSAGE}\n\n{SKILLSET_SOURCE_CITATION}",
            "operation": "unsupported",
            "raw_results": None,
            "table": None,
            "chart_data": None
        }

    def _table_response(self, df: pd.DataFrame, heading: str, operation: str = "filter") -> Dict[str, Any]:
        tbl = df[[c for c in LIST_COLS if c in df.columns]]
        body = dataframe_to_markdown(tbl) if not tbl.empty else "_No matching resources._"
        return {
            "response": f"{heading}\n\n{body}\n\n{SKILLSET_SOURCE_CITATION}",
            "operation": operation,
            "table": tbl,
            "chart_data": None
        }

    def _eval_deterministic(self, q: str) -> Optional[Dict[str, Any]]:
        """Evaluates question deterministically using pandas. No hardcoded skill/resource names -
        vocabulary is derived from whatever is actually present in self.raw_df."""
        df = self.raw_df.copy()
        q_lower = q.lower().strip()

        # Out-of-domain guard
        irrelevant_keywords = [
            "weather", "capital of", "president", "recipe", "stock price",
            "cricket", "movie", "song", "python code", "translate", "tell me a joke"
        ]
        if any(kw in q_lower for kw in irrelevant_keywords):
            return {
                "response": f"{SKILLSET_FALLBACK_MESSAGE}\n\n{SKILLSET_SOURCE_CITATION}",
                "operation": "unsupported",
                "table": None,
                "chart_data": None
            }

        # 1. Summary
        if any(w in q_lower for w in ["summary", "overview", "summarize", "situation"]):
            lines = ["### 📊 Resource Skillset Matrix Summary", f"- **Total resources tracked:** {len(df)}"]
            if "Resource Level" in df.columns:
                lines.append("\n**By resource level:**")
                lines += [f"- **{k}**: {v} resource(s)" for k, v in df["Resource Level"].astype(str).str.strip().value_counts().items()]
            if "Location" in df.columns:
                lines.append("\n**By location:**")
                lines += [f"- **{k}**: {v} resource(s)" for k, v in df["Location"].astype(str).str.strip().value_counts().items()]
            for col in SKILL_COLUMNS:
                if col in df.columns:
                    distinct = {s for cell in df[col] for s in split_skill_cell(cell)}
                    if distinct:
                        lines.append(f"\n**Distinct {col}:** {len(distinct)} ({', '.join(sorted(distinct))})")
            return {
                "response": "\n".join(lines) + f"\n\n{SKILLSET_SOURCE_CITATION}",
                "operation": "summary",
                "table": None,
                "chart_data": None
            }

        # 2. "What skills / tools does <resource> have" - resource name lookup
        if "Resource Name" in df.columns:
            for name in df["Resource Name"].dropna().astype(str).str.strip().unique():
                if name.lower() != "unassigned" and re.search(rf"\b{re.escape(name.lower())}\b", q_lower):
                    matched = df[df["Resource Name"].astype(str).str.strip().str.lower() == name.lower()]
                    return self._table_response(matched, f"Skillset for **{name}**:")

        # 3. Skill / tool lookup: "who has/knows <skill>", "resources with <skill>"
        skill_intent = any(w in q_lower for w in ["who has", "who knows", "who is certified", "resources with",
                                                    "which resources", "experience in", "experience with", "certified in"])
        skill_cols_present = [c for c in SKILL_COLUMNS if c in df.columns]
        if skill_cols_present:
            all_skills = {s for col in skill_cols_present for cell in df[col] for s in split_skill_cell(cell)}
            for skill in sorted(all_skills, key=len, reverse=True):  # longest match first (e.g. "github copilot" before "copilot")
                if skill.lower() in q_lower:
                    mask = pd.Series(False, index=df.index)
                    for col in skill_cols_present:
                        mask = mask | df[col].apply(lambda cell: skill.lower() in [s.lower() for s in split_skill_cell(cell)])
                    matched = df[mask]
                    if skill_intent or not matched.empty:
                        return self._table_response(matched, f"Found **{len(matched)}** resource(s) with **{skill}**:")

        # 4. Resource Level filter
        if "Resource Level" in df.columns:
            for level in df["Resource Level"].dropna().astype(str).str.strip().unique():
                if level.lower() != "unassigned" and level.lower() in q_lower:
                    matched = df[df["Resource Level"].astype(str).str.strip().str.lower() == level.lower()]
                    if any(w in q_lower for w in ["how many", "count", "number of"]):
                        return {
                            "response": f"There are **{len(matched)}** resource(s) at level **{level}**.\n\n{SKILLSET_SOURCE_CITATION}",
                            "operation": "count", "table": None, "chart_data": None
                        }
                    return self._table_response(matched, f"Found **{len(matched)}** resource(s) at level **{level}**:")

        # 5. Location filter
        if "Location" in df.columns:
            for loc in df["Location"].dropna().astype(str).str.strip().unique():
                if loc.lower() != "unassigned" and loc.lower() in q_lower:
                    matched = df[df["Location"].astype(str).str.strip().str.lower() == loc.lower()]
                    return self._table_response(matched, f"Found **{len(matched)}** resource(s) located in **{loc}**:")

        # 6. Breakdown / distribution
        if any(w in q_lower for w in ["breakdown", "distribution", "by level", "by location"]):
            for key, col, title in [("level", "Resource Level", "Skillset Matrix by Resource Level"),
                                     ("location", "Location", "Skillset Matrix by Location")]:
                if key in q_lower and col in df.columns:
                    counts = df[col].astype(str).str.strip().value_counts().to_dict()
                    lines = [f"**{title}** (Total: {len(df)}):"] + [f"- **{k}**: {v} resource(s)" for k, v in counts.items()]
                    return {
                        "response": "\n".join(lines) + f"\n\n{SKILLSET_SOURCE_CITATION}",
                        "operation": "group_by", "table": None, "chart_data": counts
                    }

        # 7. Total count
        if any(w in q_lower for w in ["how many", "total", "count"]):
            return {
                "response": f"There are **{len(df)}** resources in the Skillset Matrix.\n\n{SKILLSET_SOURCE_CITATION}",
                "operation": "count", "table": None, "chart_data": None
            }

        # 8. Show all
        if any(w in q_lower for w in ["show all", "list all", "all resources", "table"]):
            return self._table_response(df, f"Here are all **{len(df)}** resources in the Skillset Matrix:")

        return None

    @staticmethod
    def get_suggested_questions() -> List[str]:
        """Returns standard suggested questions for the Skillset Matrix UI chips."""
        return [
            "How many resources are tracked in the skillset matrix?",
            "Which resources have JMeter experience?",
            "Show skillset for Vaibhav.",
            "Who is certified in CTPT?",
            "Show skillset breakdown by resource level.",
            "Which resources use ChatGPT or Claude?",
            "Give me a summary of the skillset matrix.",
            "Show all resources in Noida."
        ]


def ask_skillset_assistant(question: str, df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """Convenience helper function to query the Skillset Matrix assistant."""
    assistant = SkillsetMatrixAIAssistant(df=df)
    return assistant.answer_question(question)
