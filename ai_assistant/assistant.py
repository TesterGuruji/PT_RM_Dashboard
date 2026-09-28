"""
Pipeline Demand AI Assistant Coordinator.
Orchestrates query parsing, safe pandas execution, and response synthesis.
"""

import os
import pandas as pd
from typing import Dict, Any, List, Optional
from .prompts import FALLBACK_NOT_FOUND_MESSAGE, SOURCE_CITATION
from .llm_client import LLMClient
from .query_parser import QueryParser
from .query_executor import QueryExecutor

DEFAULT_CSV_PATH = "PipelineDemand_Details.csv"

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

def _with_notice(notice: Optional[str], text: str) -> str:
    return f"{notice}\n\n{text}" if notice else text

class PipelineAIAssistant:
    def __init__(self, csv_path: str = DEFAULT_CSV_PATH, df: Optional[pd.DataFrame] = None):
        self.csv_path = csv_path
        self.raw_df = df if df is not None else self._load_csv(csv_path)
        self.llm_client = LLMClient()
        self.parser = QueryParser(self.llm_client, df=self.raw_df)
        self.executor = QueryExecutor(self.raw_df)

    def _load_csv(self, path: str) -> pd.DataFrame:
        """Loads the PipelineDemand_Details.csv safely."""
        if not os.path.exists(path):
            return pd.DataFrame()
        try:
            return pd.read_csv(path).fillna("Unassigned")
        except Exception as e:
            print(f"[PipelineAIAssistant] Failed to read {path}: {e}")
            return pd.DataFrame()

    def update_dataframe(self, df: pd.DataFrame):
        """Updates working DataFrame (e.g., when dashboard filter is active or cache is refreshed)."""
        self.raw_df = df.copy()
        self.executor = QueryExecutor(self.raw_df)
        self.parser.update_dataframe(self.raw_df)

    def answer_question(self, user_question: str) -> Dict[str, Any]:
        """
        Main entrypoint: parses the question, executes pandas query, and returns formatted response.
        Returns a dict containing:
        - "response": formatted markdown answer
        - "operation": query operation type
        - "raw_results": computed results dict
        - "table": optional DataFrame for UI display
        - "chart_data": optional data for visualization
        """
        clean_q = user_question.strip()
        if not clean_q:
            return {
                "response": "Please enter a question about the Pipeline Demand data.",
                "status": "empty_input"
            }

        if self.raw_df.empty:
            return {
                "response": f"{FALLBACK_NOT_FOUND_MESSAGE}\n\n{SOURCE_CITATION}",
                "status": "empty_csv"
            }

        # 1. Primary Path: Direct LLM Grounded Synthesis using file data
        if self.llm_client.is_available():
            try:
                llm_response = self.llm_client.generate_grounded_answer(
                    user_question=clean_q,
                    df=self.raw_df,
                    source_name="PipelineDemand_Details.csv",
                    dataset_description="Upcoming performance testing demand, resource allocation, and fulfillment across sectors."
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
                print(f"[PipelineAIAssistant] LLM call failed, falling back to deterministic engine: {e}")

        # 2. Fallback Path: Deterministic Query Parser & Safe Pandas Execution
        notice = self.llm_client.unavailable_notice()
        structured_query = self.parser.parse(clean_q)
        computed_result = self.executor.execute(structured_query)

        if computed_result.get("status") == "unsupported" or computed_result.get("empty", False):
            return {
                "response": _with_notice(notice, f"{FALLBACK_NOT_FOUND_MESSAGE}\n\n{SOURCE_CITATION}"),
                "operation": "unsupported",
                "raw_results": computed_result,
                "table": None,
                "chart_data": None
            }

        formatted_text, display_table, chart_data = self._format_computed_output(clean_q, computed_result)

        return {
            "response": _with_notice(notice, formatted_text),
            "operation": computed_result.get("operation"),
            "raw_results": computed_result,
            "table": display_table,
            "chart_data": chart_data
        }

    def _format_computed_output(self, question: str, result: Dict[str, Any]) -> tuple[str, Optional[pd.DataFrame], Optional[Dict[str, Any]]]:
        """
        Formats computed pandas results into human-friendly Markdown with tables or chart data.
        """
        op = result.get("operation")
        display_table = None
        chart_data = None

        # 1. COUNT
        if op == "count":
            count = result.get("count", 0)
            target = result.get("target_column") or "pipeline demands"
            
            # Format custom natural description
            q_lower = question.lower()
            if "open" in q_lower:
                text = f"There are **{count}** open pipeline demands."
            elif "invalid" in q_lower:
                text = f"There are **{count}** invalid pipeline demands."
            elif "awaiting" in q_lower:
                text = f"There are **{count}** pipeline demands awaiting confirmation."
            elif "july" in q_lower:
                text = f"There are **{count}** pipeline demands starting in July 2026."
            elif "september" in q_lower:
                text = f"There are **{count}** pipeline demands starting in September 2026."
            elif "unassigned" in q_lower:
                text = f"There are **{count}** unassigned pipeline demands."
            else:
                text = f"There are **{count}** matching pipeline demands."

            return f"{text}\n\n{SOURCE_CITATION}", display_table, chart_data

        # 2. FILTER / LIST
        elif op == "filter" or op == "lookup":
            records = result.get("records", [])
            count = len(records)
            if count == 0:
                return f"No matching records found in Pipeline Demand data.\n\n{SOURCE_CITATION}", None, None

            df_out = pd.DataFrame(records)
            display_cols = ["Role ID", "Eng Name", "Sector", "Client", "Start Date", "Resource Level", "Status", "Sector PT lead"]
            actual_cols = [c for c in display_cols if c in df_out.columns]
            df_display = df_out[actual_cols]

            header = f"Found **{count}** matching demand{'s' if count != 1 else ''}:"
            table_md = dataframe_to_markdown(df_display)
            full_text = f"{header}\n\n{table_md}\n\n{SOURCE_CITATION}"

            return full_text, df_display, None

        # 3. GROUP BY / DISTRIBUTION
        elif op == "group_by":
            col = result.get("column", "Status")
            breakdown = result.get("breakdown", [])
            total = result.get("total_records", 0)

            lines = [f"**Demand Count by {col}** (Total: {total} records):"]
            for item in breakdown:
                lines.append(f"- **{item['name']}**: {item['count']} demand(s)")

            chart_data = {item["name"]: item["count"] for item in breakdown}
            full_text = "\n".join(lines) + f"\n\n{SOURCE_CITATION}"
            return full_text, None, chart_data

        # 4. RANKING
        elif op == "rank":
            col = result.get("column", "Resource Level")
            top_item = result.get("top_item")
            rank_data = result.get("rank_data", [])

            if not top_item:
                return f"{FALLBACK_NOT_FOUND_MESSAGE}\n\n{SOURCE_CITATION}", None, None

            lines = [f"**{top_item['name']}** has the highest demand with **{top_item['count']}** records."]
            if len(rank_data) > 1:
                lines.append("\n**Full Ranking:**")
                for idx, r in enumerate(rank_data, 1):
                    lines.append(f"{idx}. **{r['name']}**: {r['count']} demands")

            full_text = "\n".join(lines) + f"\n\n{SOURCE_CITATION}"
            chart_data = {r["name"]: r["count"] for r in rank_data}
            return full_text, None, chart_data

        # 5. SUMMARY
        elif op == "summary":
            total = result.get("total_demands", 0)
            open_count = result.get("open_demands", 0)
            invalid_count = result.get("invalid_demands", 0)
            awaiting_count = result.get("awaiting_confirmation", 0)
            assigned_count = result.get("assigned_demands", 0)
            unassigned_count = result.get("unassigned_demands", 0)

            lines = [
                "### 📊 Pipeline Demand Summary",
                f"- **Total Demands:** {total}",
                f"- **Open Demands:** {open_count}",
                f"- **Invalid Demands:** {invalid_count}",
                f"- **Awaiting Confirmation:** {awaiting_count}",
                f"- **Assigned to Leads:** {assigned_count}",
                f"- **Unassigned:** {unassigned_count}",
            ]

            status_dist = result.get("status_distribution", {})
            if status_dist:
                lines.append("\n**Status Breakdown:**")
                for k, v in status_dist.items():
                    lines.append(f"- {k}: {v}")

            full_text = "\n".join(lines) + f"\n\n{SOURCE_CITATION}"
            return full_text, None, status_dist

        # 6. COMPARE
        elif op == "compare":
            target_col = result.get("target_column", "Resource Level")
            comparisons = result.get("comparison", [])

            lines = [f"### ⚖️ Comparison of {target_col}:"]
            for comp in comparisons:
                lines.append(f"#### **{comp['item']}** (Total: {comp['total_count']})")
                for st_name, st_cnt in comp.get("status_breakdown", {}).items():
                    lines.append(f"  - Status `{st_name}`: {st_cnt}")

            full_text = "\n".join(lines) + f"\n\n{SOURCE_CITATION}"
            return full_text, None, None

        # Default fallback
        return f"{FALLBACK_NOT_FOUND_MESSAGE}\n\n{SOURCE_CITATION}", None, None

    @staticmethod
    def get_suggested_questions() -> List[str]:
        """Returns standard suggested questions for the UI chips."""
        return [
            "How many open demands are there?",
            "How many invalid demands are there?",
            "Which resource level has the highest demand?",
            "Show all demands assigned to Venkat.",
            "Show all unassigned demands.",
            "How many demands start in July 2026?",
            "Give me the demand count by status.",
            "Give me a summary of the pipeline.",
            "Which Sector PT lead has the most demands?",
            "Compare Staff 2 and Senior 3."
        ]


def ask_pipeline_assistant(question: str, df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """Convenience helper function to query the assistant."""
    assistant = PipelineAIAssistant(df=df)
    return assistant.answer_question(question)
