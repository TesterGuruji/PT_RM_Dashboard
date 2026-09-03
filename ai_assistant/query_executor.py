"""
Safe Pandas Query Executor for Pipeline Demand Data.
Executes strictly validated structured queries without dynamic code evaluation.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional
from .prompts import ALLOWED_COLUMNS, ALLOWED_OPERATIONS, ALLOWED_OPERATORS

def prepare_pipeline_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepares a clean copy of the DataFrame with normalized helper columns for safe querying.
    Does not mutate the original DataFrame.
    """
    clean_df = df.copy().fillna("Unassigned")
    
    # Normalize string representations for case-insensitive matching
    for col in clean_df.columns:
        clean_df[col] = clean_df[col].astype(str).str.strip()

    # Create internal normalized helper columns
    if "Status" in clean_df.columns:
        clean_df["_status_norm"] = clean_df["Status"].str.lower()
    if "Sector PT lead" in clean_df.columns:
        clean_df["_lead_norm"] = clean_df["Sector PT lead"].str.lower()
    if "Resource Level" in clean_df.columns:
        clean_df["_level_norm"] = clean_df["Resource Level"].str.lower()
    if "Client" in clean_df.columns:
        clean_df["_client_norm"] = clean_df["Client"].str.lower()
    if "Sector" in clean_df.columns:
        clean_df["_sector_norm"] = clean_df["Sector"].str.lower()
    if "Eng Name" in clean_df.columns:
        clean_df["_eng_name_norm"] = clean_df["Eng Name"].str.lower()
    if "Role ID" in clean_df.columns:
        clean_df["_role_id_str"] = clean_df["Role ID"].str.replace(r"\.0$", "", regex=True)
    if "Eng ID" in clean_df.columns:
        clean_df["_eng_id_str"] = clean_df["Eng ID"].str.replace(r"\.0$", "", regex=True)

    # Date normalization
    if "Start Date" in clean_df.columns:
        clean_df["_start_date_dt"] = pd.to_datetime(clean_df["Start Date"], errors="coerce")
        clean_df["_start_ym"] = clean_df["_start_date_dt"].dt.strftime("%Y-%m")
        clean_df["_start_month_name"] = clean_df["_start_date_dt"].dt.strftime("%B").str.lower()
        clean_df["_start_year"] = clean_df["_start_date_dt"].dt.year
        clean_df["_start_date_str"] = clean_df["_start_date_dt"].dt.strftime("%Y-%m-%d")

    return clean_df


class QueryExecutor:
    """
    Validates and executes structured JSON queries safely over the pipeline DataFrame.
    """
    def __init__(self, raw_df: pd.DataFrame):
        self.raw_df = raw_df
        self.df = prepare_pipeline_dataframe(raw_df)

    def execute(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a validated query dictionary.
        Returns a computed result dictionary ready for response generation.
        """
        if not isinstance(query, dict):
            return {"status": "unsupported", "error": "Invalid query format"}

        operation = query.get("operation", "unsupported")
        if operation not in ALLOWED_OPERATIONS or operation == "unsupported":
            return {"status": "unsupported"}

        # 1. Apply Filters
        filtered_df = self._apply_filters(self.df, query.get("filters", []))

        # 2. Dispatch Operation
        if operation == "count":
            return self._execute_count(filtered_df, query)
        elif operation == "filter":
            return self._execute_filter(filtered_df, query)
        elif operation == "group_by":
            return self._execute_group_by(filtered_df, query)
        elif operation == "rank":
            return self._execute_rank(filtered_df, query)
        elif operation == "lookup":
            return self._execute_lookup(filtered_df, query)
        elif operation == "summary":
            return self._execute_summary(self.df, query)
        elif operation == "compare":
            return self._execute_compare(self.df, query)

        return {"status": "unsupported"}

    def _apply_filters(self, df: pd.DataFrame, filters: List[Dict[str, Any]]) -> pd.DataFrame:
        """Applies a list of verified filter conditions using vectorized pandas operations."""
        current_df = df.copy()
        if not filters or not isinstance(filters, list):
            return current_df

        for f in filters:
            if not isinstance(f, dict):
                continue
            col = f.get("column")
            op = f.get("operator")
            val = f.get("value")

            if col not in ALLOWED_COLUMNS:
                continue

            current_df = self._apply_single_filter(current_df, col, op, val)

        return current_df

    def _apply_single_filter(self, df: pd.DataFrame, col: str, op: str, val: Any) -> pd.DataFrame:
        """Applies a single validated filter constraint."""
        val_str = str(val).strip() if val is not None else ""
        val_lower = val_str.lower()

        # Map to internal normalized columns where applicable
        if col == "Status":
            norm_col = "_status_norm"
        elif col == "Sector PT lead":
            norm_col = "_lead_norm"
        elif col == "Resource Level":
            norm_col = "_level_norm"
        elif col == "Client":
            norm_col = "_client_norm"
        elif col == "Sector":
            norm_col = "_sector_norm"
        elif col == "Eng Name":
            norm_col = "_eng_name_norm"
        elif col == "Role ID":
            norm_col = "_role_id_str"
        elif col == "Eng ID":
            norm_col = "_eng_id_str"
        else:
            norm_col = col

        if norm_col not in df.columns:
            return df

        if op == "equals":
            return df[df[norm_col] == val_lower] if norm_col.startswith("_") else df[df[norm_col].astype(str) == val_str]
        elif op == "not_equals":
            return df[df[norm_col] != val_lower] if norm_col.startswith("_") else df[df[norm_col].astype(str) != val_str]
        elif op == "contains":
            return df[df[norm_col].str.contains(val_lower, case=False, na=False)]
        elif op == "is_unassigned":
            if norm_col in df.columns:
                mask = df[norm_col].isin(["unassigned", "", "none", "null", "nan"]) | df[norm_col].isna()
                return df[mask]
        elif op == "is_assigned":
            if norm_col in df.columns:
                mask = ~df[norm_col].isin(["unassigned", "", "none", "null", "nan"]) & df[norm_col].notna()
                return df[mask]
        elif op == "date_exact" and "_start_date_str" in df.columns:
            return df[df["_start_date_str"] == val_str]
        elif op == "date_month_year":
            # Handles "2026-07", "July 2026", "July", "September", etc.
            mask = pd.Series(False, index=df.index)
            if "_start_ym" in df.columns and val_str in df["_start_ym"].values:
                mask = mask | (df["_start_ym"] == val_str)
            if "_start_month_name" in df.columns:
                # Check month name match
                for month_word in ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]:
                    if month_word in val_lower:
                        mask = mask | (df["_start_month_name"] == month_word)
            return df[mask]
        elif op == "date_after" and "_start_date_dt" in df.columns:
            target_dt = pd.to_datetime(val_str, errors="coerce")
            if pd.notna(target_dt):
                return df[df["_start_date_dt"] > target_dt]
        elif op == "date_before" and "_start_date_dt" in df.columns:
            target_dt = pd.to_datetime(val_str, errors="coerce")
            if pd.notna(target_dt):
                return df[df["_start_date_dt"] < target_dt]

        return df

    def _execute_count(self, df: pd.DataFrame, query: Dict[str, Any]) -> Dict[str, Any]:
        count = len(df)
        return {
            "status": "success",
            "operation": "count",
            "count": count,
            "target_column": query.get("target_column"),
            "empty": False,
            "records_preview": self._format_records(df.head(5))
        }

    def _execute_filter(self, df: pd.DataFrame, query: Dict[str, Any]) -> Dict[str, Any]:
        records = self._format_records(df)
        return {
            "status": "success",
            "operation": "filter",
            "total_matches": len(df),
            "empty": len(df) == 0,
            "records": records
        }

    def _execute_group_by(self, df: pd.DataFrame, query: Dict[str, Any]) -> Dict[str, Any]:
        col = query.get("group_by_column") or query.get("target_column", "Status")
        if col not in self.df.columns:
            col = "Status"

        counts = df[col].value_counts().to_dict()
        breakdown = [{"name": str(k), "count": int(v)} for k, v in counts.items()]
        return {
            "status": "success",
            "operation": "group_by",
            "column": col,
            "breakdown": breakdown,
            "total_records": len(df),
            "empty": len(breakdown) == 0
        }

    def _execute_rank(self, df: pd.DataFrame, query: Dict[str, Any]) -> Dict[str, Any]:
        col = query.get("group_by_column") or query.get("target_column", "Resource Level")
        if col not in self.df.columns:
            col = "Resource Level"

        # Exclude 'Unassigned' if ranking people/leads unless that's all there is
        sub_df = df
        if col in ["Sector PT lead", "Sector PT Lead"] and len(df[df[col] != "Unassigned"]) > 0:
            sub_df = df[df[col] != "Unassigned"]

        counts = sub_df[col].value_counts()
        rank_data = [{"name": str(k), "count": int(v)} for k, v in counts.items()]
        
        top_item = rank_data[0] if rank_data else None
        return {
            "status": "success",
            "operation": "rank",
            "column": col,
            "top_item": top_item,
            "rank_data": rank_data,
            "empty": len(rank_data) == 0
        }

    def _execute_lookup(self, df: pd.DataFrame, query: Dict[str, Any]) -> Dict[str, Any]:
        records = self._format_records(df)
        return {
            "status": "success",
            "operation": "lookup",
            "records": records,
            "empty": len(records) == 0
        }

    def _execute_summary(self, df: pd.DataFrame, query: Dict[str, Any]) -> Dict[str, Any]:
        total_demands = len(df)
        open_demands = len(df[df["_status_norm"] == "open"]) if "_status_norm" in df.columns else 0
        invalid_demands = len(df[df["_status_norm"] == "invalid"]) if "_status_norm" in df.columns else 0
        awaiting_demands = len(df[df["_status_norm"] == "awaiting confirmation"]) if "_status_norm" in df.columns else 0
        fulfilled_demands = len(df[df["_status_norm"] == "fulfilled"]) if "_status_norm" in df.columns else 0
        
        status_dist = df["Status"].value_counts().to_dict() if "Status" in df.columns else {}
        level_dist = df["Resource Level"].value_counts().to_dict() if "Resource Level" in df.columns else {}
        client_dist = df["Client"].value_counts().to_dict() if "Client" in df.columns else {}
        sector_dist = df["Sector"].value_counts().to_dict() if "Sector" in df.columns else {}

        assigned_count = len(df[df["_lead_norm"] != "unassigned"]) if "_lead_norm" in df.columns else 0
        unassigned_count = total_demands - assigned_count

        return {
            "status": "success",
            "operation": "summary",
            "total_demands": total_demands,
            "open_demands": open_demands,
            "invalid_demands": invalid_demands,
            "awaiting_confirmation": awaiting_demands,
            "fulfilled_demands": fulfilled_demands,
            "assigned_demands": assigned_count,
            "unassigned_demands": unassigned_count,
            "status_distribution": status_dist,
            "level_distribution": level_dist,
            "client_distribution": client_dist,
            "sector_distribution": sector_dist,
            "empty": False
        }

    def _execute_compare(self, df: pd.DataFrame, query: Dict[str, Any]) -> Dict[str, Any]:
        compare_vals = query.get("compare_values", [])
        if not compare_vals:
            # Fallback to Staff 2 vs Senior 3 if unspecified
            compare_vals = ["Staff 2", "Senior 3"]

        col = query.get("target_column") or "Resource Level"
        if col not in self.df.columns:
            col = "Resource Level"

        comparison_results = []
        for val in compare_vals:
            val_lower = str(val).strip().lower()
            matched = df[df[col].astype(str).str.strip().str.lower() == val_lower]
            status_breakdown = matched["Status"].value_counts().to_dict() if "Status" in matched.columns else {}
            comparison_results.append({
                "item": str(val),
                "total_count": len(matched),
                "status_breakdown": status_breakdown
            })

        return {
            "status": "success",
            "operation": "compare",
            "target_column": col,
            "comparison": comparison_results,
            "empty": len(comparison_results) == 0
        }

    def _format_records(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Formats DataFrame rows into clean dicts without internal helper columns."""
        display_cols = [c for c in ALLOWED_COLUMNS if c in df.columns]
        return df[display_cols].to_dict(orient="records")
