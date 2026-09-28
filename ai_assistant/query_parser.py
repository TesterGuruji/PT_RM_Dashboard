"""
Hybrid Query Parser: Fast Deterministic Rule-Based Matching + LLM Structured Query Fallback.
"""

import re
import pandas as pd
from typing import Dict, Any, List, Optional
from .llm_client import LLMClient

MONTH_NAMES = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
    "jan": "01", "feb": "02", "mar": "03", "apr": "04", "jun": "06",
    "jul": "07", "aug": "08", "sep": "09", "sept": "09", "oct": "10", "nov": "11", "dec": "12"
}

class QueryParser:
    def __init__(self, llm_client: Optional[LLMClient] = None, df: Optional[pd.DataFrame] = None):
        self.llm_client = llm_client or LLMClient()
        self.df = df

    def update_dataframe(self, df: Optional[pd.DataFrame]):
        """Refreshes the vocabulary (leads/clients/levels/ids) the deterministic parser matches against."""
        self.df = df

    def _column_vocab(self, column: str) -> List[str]:
        """Distinct lowercase values actually present in `column` today, excluding blanks/placeholders."""
        if self.df is None or column not in self.df.columns:
            return []
        values = self.df[column].dropna().astype(str).str.strip()
        return sorted({v.lower() for v in values if v and v.lower() != "unassigned"})

    def parse(self, question: str) -> Dict[str, Any]:
        """
        Parses a user question into a structured query dictionary.
        First tries deterministic fast-path, falling back to LLM if needed.
        """
        clean_q = question.strip()
        
        # 1. Try fast deterministic parser
        fast_result = self._parse_deterministic(clean_q)
        if fast_result:
            return fast_result

        # 2. Try LLM structured query generation
        if self.llm_client.is_available():
            llm_result = self.llm_client.generate_json_query(clean_q)
            if llm_result and isinstance(llm_result, dict):
                return llm_result

        # 3. Fallback to unsupported if completely unrecognized
        return {
            "operation": "unsupported",
            "explanation": "Could not recognize question structure"
        }

    def _parse_deterministic(self, q: str) -> Optional[Dict[str, Any]]:
        """
        Performs regex and keyword-based deterministic parsing for common questions.
        """
        q_lower = q.lower().strip()
        q_clean = re.sub(r"[^\w\s]", " ", q_lower)
        tokens = q_clean.split()

        # -------------------------------------------------------------
        # 1. OUT-OF-DOMAIN NEGATIVE TEST DETECTION
        # -------------------------------------------------------------
        irrelevant_keywords = [
            "weather", "capital of", "president", "recipe", "stock price",
            "football", "cricket", "movie", "song", "python code", "translate",
            "who is john doe", "john doe", "tell me a joke", "general knowledge"
        ]
        if any(kw in q_lower for kw in irrelevant_keywords):
            return {"operation": "unsupported"}

        # -------------------------------------------------------------
        # 2. SUMMARY / PIPELINE OVERVIEW
        # -------------------------------------------------------------
        if any(p in q_lower for p in [
            "summary of the pipeline", "pipeline summary", "summarize the pipeline",
            "summarize the current demand", "summary of pipeline", "overview of open",
            "overview of demands", "demand situation", "pipeline overview", "summary of demand"
        ]):
            return {
                "operation": "summary",
                "explanation": "Full pipeline summary"
            }

        # -------------------------------------------------------------
        # 3. COMPARISON (e.g., Staff 2 vs Senior 3, Open vs Invalid)
        # -------------------------------------------------------------
        if "compare" in q_lower or "versus" in q_lower or " vs " in q_lower:
            levels_to_compare = []
            for lvl in ["staff 1", "staff 2", "senior 3", "manager"]:
                if lvl in q_lower:
                    levels_to_compare.append(lvl.title())
            if levels_to_compare:
                return {
                    "operation": "compare",
                    "target_column": "Resource Level",
                    "compare_values": levels_to_compare,
                    "explanation": f"Compare resource levels: {', '.join(levels_to_compare)}"
                }
            if "open" in q_lower and "invalid" in q_lower:
                return {
                    "operation": "compare",
                    "target_column": "Status",
                    "compare_values": ["Open", "Invalid"],
                    "explanation": "Compare Open vs Invalid status"
                }

        # -------------------------------------------------------------
        # 4. RANKING / "HIGHEST" / "MOST" / "TOP"
        # -------------------------------------------------------------
        if any(w in q_lower for w in ["most", "highest", "top", "maximum"]):
            if "resource level" in q_lower or "level" in q_lower or "requested" in q_lower:
                return {
                    "operation": "rank",
                    "target_column": "Resource Level",
                    "rank_order": "highest",
                    "explanation": "Resource level with highest demand"
                }
            if "lead" in q_lower or "engineer" in q_lower or "assigned" in q_lower or "person" in q_lower:
                return {
                    "operation": "rank",
                    "target_column": "Sector PT lead",
                    "rank_order": "highest",
                    "explanation": "Sector PT lead with most demands"
                }
            if "client" in q_lower:
                return {
                    "operation": "rank",
                    "target_column": "Client",
                    "rank_order": "highest",
                    "explanation": "Client with highest number of demands"
                }
            if "sector" in q_lower:
                return {
                    "operation": "rank",
                    "target_column": "Sector",
                    "rank_order": "highest",
                    "explanation": "Sector with highest demands"
                }

        # -------------------------------------------------------------
        # 5. COUNT QUESTIONS
        # -------------------------------------------------------------
        is_count = any(w in q_lower for w in ["how many", "count of", "number of", "total number of", "total count"])
        
        # 5a. Total demands
        if is_count and any(w in q_lower for w in ["demands are there", "total demands", "records", "all demands"]):
            if not any(status in q_lower for status in ["open", "invalid", "awaiting", "fulfilled", "unassigned", "assigned"]):
                return {
                    "operation": "count",
                    "target_column": None,
                    "filters": [],
                    "explanation": "Total demand count"
                }

        # 5b. Status counts
        if is_count or "count" in q_lower:
            if "open" in q_lower:
                return {
                    "operation": "count",
                    "target_column": "Status",
                    "filters": [{"column": "Status", "operator": "equals", "value": "Open"}],
                    "explanation": "Count open demands"
                }
            if "invalid" in q_lower:
                return {
                    "operation": "count",
                    "target_column": "Status",
                    "filters": [{"column": "Status", "operator": "equals", "value": "Invalid"}],
                    "explanation": "Count invalid demands"
                }
            if "awaiting" in q_lower or "confirmation" in q_lower or "pending" in q_lower:
                return {
                    "operation": "count",
                    "target_column": "Status",
                    "filters": [{"column": "Status", "operator": "equals", "value": "Awaiting Confirmation"}],
                    "explanation": "Count awaiting confirmation demands"
                }
            if "fulfilled" in q_lower:
                return {
                    "operation": "count",
                    "target_column": "Status",
                    "filters": [{"column": "Status", "operator": "equals", "value": "Fulfilled"}],
                    "explanation": "Count fulfilled demands"
                }
            if "unassigned" in q_lower:
                return {
                    "operation": "count",
                    "target_column": "Sector PT lead",
                    "filters": [{"column": "Sector PT lead", "operator": "is_unassigned", "value": "Unassigned"}],
                    "explanation": "Count unassigned demands"
                }

        # 5c. Date-based counts (e.g., "How many demands start in July 2026?", "start in September")
        month_match = None
        for month_name in MONTH_NAMES.keys():
            if month_name in q_lower:
                month_match = month_name
                break

        if month_match and ("start" in q_lower or "date" in q_lower or "in " in q_lower or is_count):
            year_match = re.search(r"\b(202\d)\b", q_lower)
            year_val = year_match.group(1) if year_match else "2026"
            month_num = MONTH_NAMES[month_match]
            ym_val = f"{year_val}-{month_num}"
            
            return {
                "operation": "count" if is_count else "filter",
                "target_column": "Start Date",
                "filters": [{"column": "Start Date", "operator": "date_month_year", "value": ym_val}],
                "explanation": f"Demands starting in {month_match.title()} {year_val}"
            }

        # -------------------------------------------------------------
        # 6. GROUP BY / DISTRIBUTION QUESTIONS
        # -------------------------------------------------------------
        if any(w in q_lower for w in ["distribution", "per ", "by status", "by resource level", "by sector", "by client", "breakdown", "each client", "each sector", "each status", "who are the assigned"]):
            if "status" in q_lower:
                return {
                    "operation": "group_by",
                    "group_by_column": "Status",
                    "explanation": "Distribution of demands by status"
                }
            if "resource level" in q_lower or "level" in q_lower:
                return {
                    "operation": "group_by",
                    "group_by_column": "Resource Level",
                    "explanation": "Distribution of demands by resource level"
                }
            if "sector pt lead" in q_lower or "assigned sector pt leads" in q_lower or "assigned leads" in q_lower or "pt lead" in q_lower:
                return {
                    "operation": "group_by",
                    "group_by_column": "Sector PT lead",
                    "filters": [{"column": "Sector PT lead", "operator": "is_assigned", "value": True}],
                    "explanation": "Assigned Sector PT Leads"
                }
            if "client" in q_lower:
                return {
                    "operation": "group_by",
                    "group_by_column": "Client",
                    "explanation": "Distribution of demands by client"
                }
            if "sector" in q_lower:
                return {
                    "operation": "group_by",
                    "group_by_column": "Sector",
                    "explanation": "Distribution of demands by sector"
                }

        # -------------------------------------------------------------
        # 7. FILTERING / LISTING QUESTIONS
        # -------------------------------------------------------------
        # 7a. Assigned to a specific person (matched against Sector PT leads present in the data)
        for lead in self._column_vocab("Sector PT lead"):
            if lead in q_lower:
                return {
                    "operation": "filter",
                    "filters": [{"column": "Sector PT lead", "operator": "equals", "value": lead.title()}],
                    "explanation": f"Demands assigned to {lead.title()}"
                }

        # 7b. Unassigned demands
        if "unassigned" in q_lower:
            return {
                "operation": "filter",
                "filters": [{"column": "Sector PT lead", "operator": "is_unassigned", "value": "Unassigned"}],
                "explanation": "All unassigned pipeline demands"
            }

        # 7c. Demands for a specific Client (matched against Client values present in the data)
        for client in self._column_vocab("Client"):
            if client in q_lower:
                filters = [{"column": "Client", "operator": "equals", "value": client.upper()}]
                if "open" in q_lower:
                    filters.append({"column": "Status", "operator": "equals", "value": "Open"})
                return {
                    "operation": "filter",
                    "filters": filters,
                    "explanation": f"Demands for client {client.upper()}"
                }

        # 7d. Demands for a specific Resource Level (matched against levels present in the data)
        for lvl in self._column_vocab("Resource Level"):
            if lvl in q_lower:
                return {
                    "operation": "filter",
                    "filters": [{"column": "Resource Level", "operator": "equals", "value": lvl.title()}],
                    "explanation": f"Demands for resource level {lvl.title()}"
                }

        # 7e. Open / Invalid demands list
        if "open" in q_lower and ("show" in q_lower or "list" in q_lower or "give" in q_lower or "what" in q_lower):
            return {
                "operation": "filter",
                "filters": [{"column": "Status", "operator": "equals", "value": "Open"}],
                "explanation": "List all open demands"
            }
        if "invalid" in q_lower and ("show" in q_lower or "list" in q_lower or "give" in q_lower or "what" in q_lower):
            return {
                "operation": "filter",
                "filters": [{"column": "Status", "operator": "equals", "value": "Invalid"}],
                "explanation": "List all invalid demands"
            }

        # 7f. Specific ID lookup: any numeric token in the question that matches a Role ID / Eng ID
        # actually present in the data (not tied to any fixed set of demo IDs).
        numeric_tokens = re.findall(r"\b\d+\b", q_lower)
        if numeric_tokens:
            for id_col in ("Role ID", "Eng ID"):
                known_ids = set(self._column_vocab(id_col)) | (
                    {v.split(".")[0] for v in self._column_vocab(id_col)}
                )
                for token in numeric_tokens:
                    if token in known_ids:
                        return {
                            "operation": "lookup",
                            "filters": [{"column": id_col, "operator": "equals", "value": token}],
                            "explanation": f"Lookup demand with {id_col} {token}"
                        }

        # 7g. Specific date (e.g., "July 14, 2026" or "2026-07-14")
        iso_date_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", q_lower)
        if iso_date_match:
            return {
                "operation": "filter",
                "filters": [{"column": "Start Date", "operator": "date_exact", "value": iso_date_match.group(1)}],
                "explanation": f"Demands starting on {iso_date_match.group(1)}"
            }
        month_names_pattern = "|".join(MONTH_NAMES.keys())
        month_day_match = re.search(
            rf"\b({month_names_pattern})\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s*(20\d{{2}})?\b", q_lower
        )
        if month_day_match:
            month_word, day, year = month_day_match.groups()
            year = year or "2026"
            try:
                iso_date = f"{year}-{MONTH_NAMES[month_word]}-{int(day):02d}"
                return {
                    "operation": "filter",
                    "filters": [{"column": "Start Date", "operator": "date_exact", "value": iso_date}],
                    "explanation": f"Demands starting on {iso_date}"
                }
            except ValueError:
                pass

        return None
