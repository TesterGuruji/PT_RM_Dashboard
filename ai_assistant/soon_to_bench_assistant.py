"""
DST Soon To Bench AI Assistant Coordinator.
Orchestrates LLM-grounded answers and a deterministic pandas fallback for DST_SoonTobench.csv.
"""

import os
import re
import pandas as pd
from datetime import date
from typing import Dict, Any, List, Optional
from .llm_client import LLMClient

DEFAULT_SOON_CSV_PATH = "DST_SoonTobench.csv"
SOON_FALLBACK_MESSAGE = "I couldn't find enough information in the DST Soon To Bench data to answer that question."
SOON_SOURCE_CITATION = "📊 Source: DST_SoonTobench.csv"

# Release-window buckets, keyed on days from today until the resource's End Date
RELEASE_WINDOWS = ["Overdue", "Next 30 days", "31–60 days", "60+ days", "No end date"]


def release_window(days_to_release) -> str:
    if pd.isna(days_to_release):
        return "No end date"
    if days_to_release < 0:
        return "Overdue"
    if days_to_release <= 30:
        return "Next 30 days"
    if days_to_release <= 60:
        return "31–60 days"
    return "60+ days"


def add_release_columns(df: pd.DataFrame, today: Optional[date] = None) -> pd.DataFrame:
    """Adds 'Days To Release' and 'Release Window' derived from End Date (never stored in the CSV)."""
    today = pd.Timestamp(today or date.today())
    out = df.copy()
    end = pd.to_datetime(out["End Date"], errors="coerce") if "End Date" in out.columns else pd.Series(pd.NaT, index=out.index)
    out["Days To Release"] = (end - today).dt.days
    out["Release Window"] = out["Days To Release"].map(release_window)
    return out


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


LIST_COLS = ["GPN", "Name", "Level", "Status", "End Date", "Days To Release", "Release Window", "Location", "Counsellor Name"]


class SoonToBenchAIAssistant:
    def __init__(self, csv_path: str = DEFAULT_SOON_CSV_PATH, df: Optional[pd.DataFrame] = None):
        self.csv_path = csv_path
        self.raw_df = df if df is not None else self._load_csv(csv_path)
        self.llm_client = LLMClient()

    def _load_csv(self, path: str) -> pd.DataFrame:
        """Loads DST_SoonTobench.csv safely, trimming stray spaces around header names."""
        if not os.path.exists(path):
            return pd.DataFrame()
        try:
            df = pd.read_csv(path).fillna("Unassigned")
            df.columns = df.columns.str.strip()
            return df
        except Exception as e:
            print(f"[SoonToBenchAIAssistant] Failed to read {path}: {e}")
            return pd.DataFrame()

    def update_dataframe(self, df: pd.DataFrame):
        """Updates working DataFrame (e.g., when dashboard filter is active)."""
        self.raw_df = df.copy()

    def answer_question(self, user_question: str) -> Dict[str, Any]:
        """Main entrypoint: LLM-grounded answer first, deterministic pandas evaluation as fallback."""
        clean_q = user_question.strip()
        if not clean_q:
            return {
                "response": "Please enter a question about the DST Soon To Bench data.",
                "status": "empty_input"
            }

        if self.raw_df.empty:
            return {
                "response": f"{SOON_FALLBACK_MESSAGE}\n\n{SOON_SOURCE_CITATION}",
                "status": "empty_csv"
            }

        today = date.today()
        context_df = add_release_columns(self.raw_df, today)

        # 1. Primary Path: Direct LLM Grounded Synthesis using file data
        if self.llm_client.is_available():
            try:
                llm_response = self.llm_client.generate_grounded_answer(
                    user_question=clean_q,
                    df=context_df,
                    source_name="DST_SoonTobench.csv",
                    dataset_description=(
                        "Resources whose current engagement ends soon and who will move to the bench. "
                        f"Today's date is {today.isoformat()}. 'Days To Release' is days from today until End Date "
                        "(negative means the End Date has passed); 'Release Window' buckets it."
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
                print(f"[SoonToBenchAIAssistant] LLM call failed, falling back to deterministic engine: {e}")

        # 2. Fallback Path: Deterministic Evaluation
        notice = self.llm_client.unavailable_notice()
        fast_res = self._eval_deterministic(clean_q, context_df)
        if fast_res is not None:
            if notice:
                fast_res["response"] = f"{notice}\n\n{fast_res['response']}"
            return fast_res

        return {
            "response": f"{notice}\n\n{SOON_FALLBACK_MESSAGE}\n\n{SOON_SOURCE_CITATION}" if notice else f"{SOON_FALLBACK_MESSAGE}\n\n{SOON_SOURCE_CITATION}",
            "operation": "unsupported",
            "raw_results": None,
            "table": None,
            "chart_data": None
        }

    def _table_response(self, df: pd.DataFrame, heading: str, operation: str = "filter") -> Dict[str, Any]:
        tbl = df[[c for c in LIST_COLS if c in df.columns]]
        body = dataframe_to_markdown(tbl) if not tbl.empty else "_No matching resources._"
        return {
            "response": f"{heading}\n\n{body}\n\n{SOON_SOURCE_CITATION}",
            "operation": operation,
            "table": tbl,
            "chart_data": None
        }

    def _counts_response(self, df: pd.DataFrame, col: str, title: str) -> Dict[str, Any]:
        counts = df[col].astype(str).str.strip().value_counts().to_dict()
        lines = [f"**{title}** (Total: {len(df)}):"] + [f"- **{k}**: {v} resource(s)" for k, v in counts.items()]
        return {
            "response": "\n".join(lines) + f"\n\n{SOON_SOURCE_CITATION}",
            "operation": "group_by",
            "table": None,
            "chart_data": counts
        }

    def _eval_deterministic(self, q: str, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Evaluates question deterministically using pandas."""
        q_lower = q.lower().strip()

        # Out-of-domain guard
        irrelevant_keywords = [
            "weather", "capital of", "president", "recipe", "stock price",
            "cricket", "movie", "song", "python code", "translate", "tell me a joke"
        ]
        if any(kw in q_lower for kw in irrelevant_keywords):
            return {
                "response": f"{SOON_FALLBACK_MESSAGE}\n\n{SOON_SOURCE_CITATION}",
                "operation": "unsupported",
                "table": None,
                "chart_data": None
            }

        # 1. Summary
        if any(w in q_lower for w in ["summary", "overview", "summarize", "situation"]):
            windows = df["Release Window"].value_counts().to_dict()
            lines = ["### 📊 DST Soon To Bench Summary", f"- **Total resources tracked:** {len(df)}"]
            lines.append("\n**By release window:**")
            lines += [f"- **{w}**: {windows[w]} resource(s)" for w in RELEASE_WINDOWS if w in windows]
            if "Status" in df.columns:
                lines.append("\n**By status:**")
                lines += [f"- **{k}**: {v} resource(s)" for k, v in df["Status"].astype(str).str.strip().value_counts().items()]
            return {
                "response": "\n".join(lines) + f"\n\n{SOON_SOURCE_CITATION}",
                "operation": "summary",
                "table": None,
                "chart_data": windows
            }

        # 2. Overdue (End Date already passed)
        if any(w in q_lower for w in ["overdue", "already ended", "past end date", "passed"]):
            return self._table_response(df[df["Release Window"] == "Overdue"],
                                        f"**{int((df['Release Window'] == 'Overdue').sum())}** resource(s) have an End Date that has already passed:")

        # 3. Releasing within N days / next N days / this month
        days_match = re.search(r"(\d+)\s*days?", q_lower)
        if days_match and any(w in q_lower for w in ["within", "next", "in the coming", "releasing", "release", "bench"]):
            n = int(days_match.group(1))
            upcoming = df[(df["Days To Release"] >= 0) & (df["Days To Release"] <= n)].sort_values("Days To Release")
            return self._table_response(upcoming, f"**{len(upcoming)}** resource(s) are due to release within the next **{n} days**:")
        if "this month" in q_lower or "next month" in q_lower:
            today = pd.Timestamp(date.today())
            target = today if "this month" in q_lower else today + pd.offsets.MonthBegin(1)
            end = pd.to_datetime(df["End Date"], errors="coerce")
            in_month = df[(end.dt.year == target.year) & (end.dt.month == target.month)].sort_values("Days To Release")
            return self._table_response(in_month, f"**{len(in_month)}** resource(s) have an End Date in **{target.strftime('%B %Y')}**:")

        # 4. Soonest / next to release
        if any(w in q_lower for w in ["soonest", "next to release", "earliest", "who is next", "first to"]):
            upcoming = df[df["Days To Release"] >= 0].sort_values("Days To Release")
            return self._table_response(upcoming.head(5), "Resources releasing soonest:")

        # 5. Status queries
        if "Status" in df.columns:
            for status in df["Status"].dropna().astype(str).str.strip().unique():
                if status.lower() in q_lower and status.lower() != "unassigned":
                    matched = df[df["Status"].astype(str).str.strip().str.lower() == status.lower()]
                    if any(w in q_lower for w in ["how many", "count", "number of"]):
                        return {
                            "response": f"There are **{len(matched)}** resource(s) with status **{status}**.\n\n{SOON_SOURCE_CITATION}",
                            "operation": "count",
                            "table": None,
                            "chart_data": None
                        }
                    return self._table_response(matched, f"Found **{len(matched)}** resource(s) with status **{status}**:")

        # 6. Breakdown queries
        if any(w in q_lower for w in ["breakdown", "distribution", "by level", "level wise", "by location", "by status", "by sector", "by counsellor"]):
            for key, col, title in [("level", "Level", "Soon To Bench by Level"), ("location", "Location", "Soon To Bench by Location"),
                                    ("sector", "Sector", "Soon To Bench by Sector"), ("counsellor", "Counsellor Name", "Soon To Bench by Counsellor"),
                                    ("status", "Status", "Soon To Bench by Status")]:
                if key in q_lower and col in df.columns:
                    return self._counts_response(df, col, title)

        # 7. Location / counsellor / name lookups
        for col, noun in [("Location", "located in"), ("Counsellor Name", "under Counsellor"), ("Name", "named")]:
            if col in df.columns:
                for value in df[col].dropna().astype(str).str.strip().unique():
                    if value.lower() != "unassigned" and re.search(rf"\b{re.escape(value.lower())}\b", q_lower):
                        matched = df[df[col].astype(str).str.strip().str.lower() == value.lower()]
                        return self._table_response(matched, f"Found **{len(matched)}** soon-to-bench resource(s) {noun} **{value}**:")

        # 8. Total count
        if any(w in q_lower for w in ["how many", "total", "count"]):
            return {
                "response": f"There are **{len(df)}** resources in the DST Soon To Bench list.\n\n{SOON_SOURCE_CITATION}",
                "operation": "count",
                "table": None,
                "chart_data": None
            }

        # 9. Show all
        if any(w in q_lower for w in ["show all", "list all", "all resources", "table"]):
            return self._table_response(df.sort_values("Days To Release"), f"Here are all **{len(df)}** soon-to-bench resources:")

        return None

    @staticmethod
    def get_suggested_questions() -> List[str]:
        """Returns standard suggested questions for the Soon To Bench UI chips."""
        return [
            "How many resources are soon to bench?",
            "Who is releasing within the next 30 days?",
            "Which resources are overdue for release?",
            "Show soon to bench breakdown by level.",
            "Who is next to release?",
            "Show soon to bench breakdown by location.",
            "Give me a summary of the soon to bench list.",
            "Show all resources with IN PROGRESS status."
        ]


def ask_soon_to_bench_assistant(question: str, df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """Convenience helper function to query the DST Soon To Bench assistant."""
    assistant = SoonToBenchAIAssistant(df=df)
    return assistant.answer_question(question)
