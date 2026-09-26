"""
DST Bench AI Assistant Coordinator.
Orchestrates query parsing, safe pandas execution, and response synthesis for DST_Bench.csv.
"""

import os
import re
import pandas as pd
from typing import Dict, Any, List, Optional
from .llm_client import LLMClient

DEFAULT_DST_CSV_PATH = "DST_Bench.csv"
DST_FALLBACK_MESSAGE = "I couldn't find enough information in the DST Bench data to answer that question."
DST_SOURCE_CITATION = "📊 Source: DST_Bench.csv"

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


class DSTBenchAIAssistant:
    def __init__(self, csv_path: str = DEFAULT_DST_CSV_PATH, df: Optional[pd.DataFrame] = None):
        self.csv_path = csv_path
        self.raw_df = df if df is not None else self._load_csv(csv_path)
        self.llm_client = LLMClient()

    def _load_csv(self, path: str) -> pd.DataFrame:
        """Loads the DST_Bench.csv safely."""
        if not os.path.exists(path):
            return pd.DataFrame()
        try:
            return pd.read_csv(path).fillna("Unassigned")
        except Exception as e:
            print(f"[DSTBenchAIAssistant] Failed to read {path}: {e}")
            return pd.DataFrame()

    def update_dataframe(self, df: pd.DataFrame):
        """Updates working DataFrame (e.g., when dashboard filter is active)."""
        self.raw_df = df.copy()

    def answer_question(self, user_question: str) -> Dict[str, Any]:
        """
        Main entrypoint: parses the question, executes pandas query, and returns formatted response.
        """
        clean_q = user_question.strip()
        if not clean_q:
            return {
                "response": "Please enter a question about the DST Bench resource data.",
                "status": "empty_input"
            }

        if self.raw_df.empty:
            return {
                "response": f"{DST_FALLBACK_MESSAGE}\n\n{DST_SOURCE_CITATION}",
                "status": "empty_csv"
            }

        # 1. Deterministic Fast-Path
        fast_res = self._eval_deterministic(clean_q)
        if fast_res is not None:
            return fast_res

        # 2. LLM Fallback if available
        if self.llm_client.is_available():
            try:
                system_prompt = f"""You are a specialized assistant for DST Bench Resource data.
CSV Columns: GPN, Name, Resource Level, Status, Bench Days, Last Project Release Date, Last Project Name, Additional Comments, Location, Cousellor Name.
The current dataset has {len(self.raw_df)} records.
Data records summary:
{self.raw_df.to_string(index=False)}

Answer the user's question directly, concisely, and factually based ONLY on this dataset.
Never make up facts. End with: {DST_SOURCE_CITATION}"""
                response = self.llm_client.generate_text(clean_q, system_prompt=system_prompt)
                if response:
                    if DST_SOURCE_CITATION not in response:
                        response += f"\n\n{DST_SOURCE_CITATION}"
                    return {
                        "response": response,
                        "operation": "llm_generated",
                        "raw_results": None,
                        "table": None,
                        "chart_data": None
                    }
            except Exception as e:
                print(f"[DSTBenchAIAssistant] LLM generation error: {e}")

        # 3. Fallback
        return {
            "response": f"{DST_FALLBACK_MESSAGE}\n\n{DST_SOURCE_CITATION}",
            "operation": "unsupported",
            "raw_results": None,
            "table": None,
            "chart_data": None
        }

    def _eval_deterministic(self, q: str) -> Optional[Dict[str, Any]]:
        """Evaluates question deterministically using pandas."""
        df = self.raw_df.copy()
        q_lower = q.lower().strip()

        # Out-of-domain guard
        irrelevant_keywords = [
            "weather", "capital of", "president", "recipe", "stock price",
            "cricket", "movie", "song", "python code", "translate",
            "who is john doe", "tell me a joke"
        ]
        if any(kw in q_lower for kw in irrelevant_keywords):
            return {
                "response": f"{DST_FALLBACK_MESSAGE}\n\n{DST_SOURCE_CITATION}",
                "operation": "unsupported",
                "table": None,
                "chart_data": None
            }

        # 1. Summary of Bench Pool
        if any(w in q_lower for w in ["summary", "overview", "summarize", "situation"]):
            total = len(df)
            status_counts = df['Status'].value_counts().to_dict() if 'Status' in df.columns else {}
            avg_days = 0
            if 'Bench Days' in df.columns:
                avg_days = round(pd.to_numeric(df['Bench Days'], errors='coerce').mean(), 1)
            
            lines = [
                "### 📊 DST Bench Resource Summary",
                f"- **Total Bench Resources:** {total}",
                f"- **Average Bench Duration:** {avg_days} days"
            ]
            if status_counts:
                lines.append("\n**Status Breakdown:**")
                for st_name, count in status_counts.items():
                    lines.append(f"- **{st_name}**: {count} resource(s)")
            
            if 'Location' in df.columns:
                loc_counts = df['Location'].value_counts().to_dict()
                lines.append("\n**Location Distribution:**")
                for loc_name, count in loc_counts.items():
                    lines.append(f"- **{loc_name}**: {count} resource(s)")

            full_text = "\n".join(lines) + f"\n\n{DST_SOURCE_CITATION}"
            return {
                "response": full_text,
                "operation": "summary",
                "table": None,
                "chart_data": status_counts
            }

        # 2. Status Specific Queries (Counts & Lists)
        status_map = {
            "profile shared": "Profile Shared",
            "onboarding": "Onboarding Started",
            "onboarding started": "Onboarding Started",
            "billing": "Billing Started",
            "billing started": "Billing Started",
            "awaiting engagement": "Awaiting Engagement",
            "awaiting": "Awaiting Engagement"
        }

        matched_status = None
        for key, val in status_map.items():
            if key in q_lower:
                matched_status = val
                break

        # Check if question is asking for Count of Bench / Status
        is_count_query = any(w in q_lower for w in ["how many", "count", "number of", "total bench"])
        is_list_query = any(w in q_lower for w in ["show", "list", "display", "give me all", "who are", "which resources", "find"])

        if matched_status and 'Status' in df.columns:
            filtered = df[df['Status'].astype(str).str.strip().str.lower() == matched_status.lower()]
            count = len(filtered)
            if is_count_query and not is_list_query:
                return {
                    "response": f"There are **{count}** bench resource(s) with status **{matched_status}**.\n\n{DST_SOURCE_CITATION}",
                    "operation": "count",
                    "table": None,
                    "chart_data": None
                }
            else:
                # Show list/table
                display_cols = ["GPN", "Name", "Resource Level", "Status", "Bench Days", "Location", "Cousellor Name", "Last Project Release Date"]
                actual_cols = [c for c in display_cols if c in filtered.columns]
                tbl = filtered[actual_cols]
                table_md = dataframe_to_markdown(tbl)
                return {
                    "response": f"Found **{count}** bench resource(s) with status **{matched_status}**:\n\n{table_md}\n\n{DST_SOURCE_CITATION}",
                    "operation": "filter",
                    "table": tbl,
                    "chart_data": None
                }

        # 3. Location Queries
        if 'Location' in df.columns:
            for loc in df['Location'].dropna().unique():
                loc_str = str(loc).strip()
                if loc_str.lower() in q_lower and loc_str.lower() != 'unassigned':
                    filtered = df[df['Location'].astype(str).str.strip().str.lower() == loc_str.lower()]
                    count = len(filtered)
                    display_cols = ["GPN", "Name", "Resource Level", "Status", "Bench Days", "Location", "Cousellor Name"]
                    actual_cols = [c for c in display_cols if c in filtered.columns]
                    tbl = filtered[actual_cols]
                    table_md = dataframe_to_markdown(tbl)
                    return {
                        "response": f"There are **{count}** bench resource(s) located in **{loc_str}**:\n\n{table_md}\n\n{DST_SOURCE_CITATION}",
                        "operation": "filter",
                        "table": tbl,
                        "chart_data": None
                    }

        # 4. Counsellor Queries
        counsellor_col = 'Cousellor Name' if 'Cousellor Name' in df.columns else ('Counsellor Name' if 'Counsellor Name' in df.columns else None)
        if counsellor_col:
            for counsellor in df[counsellor_col].dropna().unique():
                c_str = str(counsellor).strip()
                if c_str.lower() in q_lower and c_str.lower() != 'unassigned':
                    filtered = df[df[counsellor_col].astype(str).str.strip().str.lower() == c_str.lower()]
                    count = len(filtered)
                    display_cols = ["GPN", "Name", "Resource Level", "Status", "Bench Days", "Location", counsellor_col]
                    actual_cols = [c for c in display_cols if c in filtered.columns]
                    tbl = filtered[actual_cols]
                    table_md = dataframe_to_markdown(tbl)
                    return {
                        "response": f"Found **{count}** bench resource(s) mentored by Counsellor **{c_str}**:\n\n{table_md}\n\n{DST_SOURCE_CITATION}",
                        "operation": "filter",
                        "table": tbl,
                        "chart_data": None
                    }

        # 5. Bench Days threshold (e.g. > 15, > 20, > 30, longest bench)
        if 'Bench Days' in df.columns and any(w in q_lower for w in ["bench day", "bench duration", "aging", "days"]):
            days_match = re.search(r"(\d+)\s*(days|day)?", q_lower)
            numeric_days = pd.to_numeric(df['Bench Days'], errors='coerce')
            if any(w in q_lower for w in ["greater than", "more than", "above", "over", ">="]):
                if days_match:
                    threshold = int(days_match.group(1))
                    filtered = df[numeric_days >= threshold]
                    count = len(filtered)
                    display_cols = ["GPN", "Name", "Resource Level", "Status", "Bench Days", "Location", "Cousellor Name"]
                    actual_cols = [c for c in display_cols if c in filtered.columns]
                    tbl = filtered[actual_cols]
                    table_md = dataframe_to_markdown(tbl)
                    return {
                        "response": f"There are **{count}** resource(s) on bench for **{threshold} days or more**:\n\n{table_md}\n\n{DST_SOURCE_CITATION}",
                        "operation": "filter",
                        "table": tbl,
                        "chart_data": None
                    }

        # 6. Group by / Breakdown queries
        if any(w in q_lower for w in ["breakdown", "distribution", "by location", "by level", "by status", "by counsellor"]):
            if "location" in q_lower and 'Location' in df.columns:
                counts = df['Location'].value_counts().to_dict()
                lines = [f"**Bench Resource Distribution by Location** (Total: {len(df)}):"]
                for loc_name, cnt in counts.items():
                    lines.append(f"- **{loc_name}**: {cnt} resource(s)")
                return {
                    "response": "\n".join(lines) + f"\n\n{DST_SOURCE_CITATION}",
                    "operation": "group_by",
                    "table": None,
                    "chart_data": counts
                }
            elif "level" in q_lower and 'Resource Level' in df.columns:
                counts = df['Resource Level'].value_counts().to_dict()
                lines = [f"**Bench Resource Count by Level** (Total: {len(df)}):"]
                for lvl_name, cnt in counts.items():
                    lines.append(f"- **{lvl_name}**: {cnt} resource(s)")
                return {
                    "response": "\n".join(lines) + f"\n\n{DST_SOURCE_CITATION}",
                    "operation": "group_by",
                    "table": None,
                    "chart_data": counts
                }
            elif "status" in q_lower and 'Status' in df.columns:
                counts = df['Status'].value_counts().to_dict()
                lines = [f"**Bench Resource Count by Status** (Total: {len(df)}):"]
                for st_name, cnt in counts.items():
                    lines.append(f"- **{st_name}**: {cnt} resource(s)")
                return {
                    "response": "\n".join(lines) + f"\n\n{DST_SOURCE_CITATION}",
                    "operation": "group_by",
                    "table": None,
                    "chart_data": counts
                }

        # 7. Total Bench Resources Count
        if any(w in q_lower for w in ["how many resources", "total bench", "total resources", "how many on bench", "bench count"]):
            total = len(df)
            return {
                "response": f"There are currently **{total}** total resources in the DST Bench pool.\n\n{DST_SOURCE_CITATION}",
                "operation": "count",
                "table": None,
                "chart_data": None
            }

        # 8. Comparison (e.g., Staff 1 vs Senior 3 or Pune vs Noida)
        if any(w in q_lower for w in ["compare", "versus", " vs "]):
            if "Resource Level" in df.columns:
                levels = [l for l in ["staff 1", "staff 2", "senior 1", "senior 2", "senior 3", "manager"] if l in q_lower]
                if len(levels) >= 2:
                    lines = ["### ⚖️ Resource Level Comparison:"]
                    for lvl in levels:
                        sub = df[df['Resource Level'].astype(str).str.strip().str.lower() == lvl]
                        lines.append(f"- **{lvl.title()}**: {len(sub)} resource(s)")
                    return {
                        "response": "\n".join(lines) + f"\n\n{DST_SOURCE_CITATION}",
                        "operation": "compare",
                        "table": None,
                        "chart_data": None
                    }

        # 9. General List / Show All
        if any(w in q_lower for w in ["show all", "list all", "all bench", "all resources", "table"]):
            display_cols = ["GPN", "Name", "Resource Level", "Status", "Bench Days", "Location", "Cousellor Name", "Last Project Release Date"]
            actual_cols = [c for c in display_cols if c in df.columns]
            tbl = df[actual_cols]
            table_md = dataframe_to_markdown(tbl)
            return {
                "response": f"Here are all **{len(df)}** DST Bench resources:\n\n{table_md}\n\n{DST_SOURCE_CITATION}",
                "operation": "filter",
                "table": tbl,
                "chart_data": None
            }

        return None

    @staticmethod
    def get_suggested_questions() -> List[str]:
        """Returns standard suggested questions for the DST Bench UI chips."""
        return [
            "How many resources are currently on bench?",
            "Show all resources with Profile Shared status.",
            "Which resources have bench duration of 20 days or more?",
            "Show bench resource breakdown by location.",
            "List all resources under Counsellor Dinesh.",
            "Give me a summary of the DST Bench pool.",
            "Show bench count by resource level.",
            "Show all resources located in Pune."
        ]


def ask_dst_bench_assistant(question: str, df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """Convenience helper function to query the DST bench assistant."""
    assistant = DSTBenchAIAssistant(df=df)
    return assistant.answer_question(question)
