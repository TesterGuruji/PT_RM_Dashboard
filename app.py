import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime
from dotenv import load_dotenv
from ai_assistant import PipelineAIAssistant, DSTBenchAIAssistant
from ai_assistant.llm_client import LLMClient

load_dotenv()

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION & ENTERPRISE DESIGN SYSTEM
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Resource Management | Performance Testing",
    page_icon=":material/groups:",
    layout="wide",
    initial_sidebar_state="auto"
)

# Corporate design system: native widgets are themed in .streamlit/config.toml; this CSS styles the custom HTML components
st.markdown("""
<style>
    :root {
        --ink-900: #0F1B2D;
        --ink-700: #33415C;
        --ink-500: #5C6B82;
        --ink-400: #7D8BA1;
        --line: #DDE2EA;
        --line-soft: #EBEEF3;
        --surface: #FFFFFF;
        --page: #F4F6F9;
        --brand: #1F5FBF;
        --brand-soft: #EAF1FB;
        --good: #0CA30C;
        --warning: #FAB219;
        --serious: #EC835A;
        --critical: #D03B3B;
    }

    .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1480px; }
    h1, h2, h3, h4 { letter-spacing: -0.01em; }

    /* Page header */
    .app-header { display: flex; justify-content: space-between; align-items: flex-end; gap: 1rem; flex-wrap: wrap;
        padding-bottom: 1rem; margin-bottom: 1.25rem; border-bottom: 1px solid var(--line); }
    .app-breadcrumb { font-size: 0.75rem; font-weight: 500; color: var(--ink-400); margin-bottom: 0.35rem; }
    .app-breadcrumb b { color: var(--ink-700); font-weight: 600; }
    .app-title { font-size: 1.6rem; font-weight: 700; color: var(--ink-900); margin: 0; padding: 0; line-height: 1.25; }
    .app-subtitle { font-size: 0.875rem; color: var(--ink-500); margin: 0.3rem 0 0 0; }
    .meta-row { display: flex; gap: 0.5rem; flex-wrap: wrap; }
    .meta-chip { display: inline-flex; align-items: center; gap: 0.35rem; background: var(--surface); border: 1px solid var(--line);
        border-radius: 999px; padding: 0.3rem 0.75rem; font-size: 0.75rem; color: var(--ink-500); white-space: nowrap; }
    .meta-chip b { color: var(--ink-900); font-weight: 600; }

    /* KPI strip */
    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0.75rem; margin-bottom: 1.25rem; }
    .kpi { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 0.95rem 1.1rem; }
    .kpi-label { font-size: 0.78rem; font-weight: 500; color: var(--ink-500); display: flex; align-items: center; gap: 0.4rem; }
    .kpi-value { font-size: 1.85rem; font-weight: 700; color: var(--ink-900); line-height: 1.15; margin: 0.35rem 0 0.2rem 0; }
    .kpi-value small { font-size: 0.95rem; font-weight: 500; color: var(--ink-500); margin-left: 0.2rem; }
    .kpi-foot { font-size: 0.75rem; color: var(--ink-400); }
    .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; flex: none; }

    /* White "cards" for keyed st.container(border=True, key="card-...") */
    div[class*="st-key-card-"] { background: var(--surface); border-radius: 8px; }
    .card-title { font-size: 0.95rem; font-weight: 600; color: var(--ink-900); margin: 0; line-height: 1.4; }
    .card-subtitle { font-size: 0.8rem; color: var(--ink-500); margin: 0.1rem 0 0.5rem 0; line-height: 1.4; }

    /* Suggested questions: compact, left-aligned list buttons */
    div[class*="st-key-btn_sugg"] button { justify-content: flex-start; min-height: 2.25rem; }
    div[class*="st-key-btn_sugg"] button > div { justify-content: flex-start; width: 100%; }
    div[class*="st-key-btn_sugg"] button p { font-size: 0.85rem; text-align: left; }

    /* Records toolbar */
    .result-pill { display: inline-flex; align-items: center; gap: 0.35rem; background: var(--brand-soft); color: var(--brand);
        border-radius: 999px; padding: 0.25rem 0.7rem; font-size: 0.75rem; font-weight: 600; }
    .filter-note { font-size: 0.75rem; color: var(--ink-500); margin-left: 0.5rem; }
    .notice { border-radius: 6px; padding: 0.55rem 0.8rem; font-size: 0.8rem; margin: 0.25rem 0 0.75rem 0; border: 1px solid; }
    .notice-warning { background: #FFF8E6; border-color: #F5D98B; color: #7A5200; }
    .notice-info { background: var(--brand-soft); border-color: #C5D8F3; color: #1B4F9C; }
    .notice-neutral { background: #F7F8FA; border-color: var(--line); color: var(--ink-700); }
    .empty-state { text-align: center; padding: 2.5rem 1rem; color: var(--ink-500); font-size: 0.85rem; }
    .empty-state b { display: block; color: var(--ink-900); font-size: 0.95rem; margin-bottom: 0.25rem; }

    /* AI assistant header */
    .ai-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; flex-wrap: wrap; }
    .ai-tag { font-size: 0.68rem; font-weight: 700; letter-spacing: 0.06em; color: var(--brand); text-transform: uppercase; }
    .source-chip { font-size: 0.72rem; color: var(--ink-500); background: #F7F8FA; border: 1px solid var(--line);
        border-radius: 999px; padding: 0.2rem 0.65rem; white-space: nowrap; }

    /* Sidebar */
    .sb-brand { padding: 0.25rem 0 1rem 0; margin-bottom: 0.75rem; border-bottom: 1px solid #24354F; }
    .sb-brand-title { font-size: 1rem; font-weight: 700; color: #FFFFFF; display: flex; align-items: center; gap: 0.55rem; }
    .sb-logo { width: 28px; height: 28px; border-radius: 6px; background: #1F5FBF; color: #FFFFFF; display: inline-flex;
        align-items: center; justify-content: center; font-size: 0.8rem; font-weight: 700; }
    .sb-brand-sub { font-size: 0.72rem; color: #7D8BA1; margin-top: 0.3rem; }
    .sb-label { font-size: 0.68rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: #7D8BA1; margin: 1.1rem 0 0.4rem 0; }
    .sb-card { background: #1A2940; border: 1px solid #24354F; border-radius: 8px; padding: 0.75rem; font-size: 0.75rem; color: #A9B6C8; }
    .sb-row { display: flex; justify-content: space-between; gap: 0.5rem; padding: 0.2rem 0; }
    .sb-row b { color: #FFFFFF; font-weight: 600; text-align: right; overflow-wrap: anywhere; }
    .sb-status { display: flex; align-items: center; gap: 0.45rem; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# CONFIGURATION & SCHEMA MAPPING
# -----------------------------------------------------------------------------
FILES = {
    "Pipeline Demands": {
        "path": "PipelineDemand_Details.csv",
        "description": "Monitor upcoming performance testing demand, resource allocation, and fulfillment across sectors.",
        "cols": ["Role ID", "Eng ID", "Eng Name", "Sector", "Sector PT lead", "Client", "Start Date", "Resource Level", "Comments", "Status"]
    },
    "DST Bench Resources": {
        "path": "DST_Bench.csv",
        "description": "Monitor performance test bench resources, bench duration, release timelines, locations, and counsellor allocations.",
        "cols": ["GPN", "Name", "Resource Level", "Status", "Bench Days", "Last Project Release Date", "Last Project Name", "Additional Comments", "Location", "Cousellor Name"]
    }
}

def get_last_refresh_timestamp(file_path: str) -> str:
    """Calculates last modification timestamp of the underlying data source."""
    if os.path.exists(file_path):
        mtime = os.path.getmtime(file_path)
        return datetime.fromtimestamp(mtime).strftime("%d %b %Y, %I:%M %p")
    return datetime.now().strftime("%d %b %Y, %I:%M %p")

@st.cache_data
def load_data(file_path, expected_cols, file_mtime=None):
    """Loads dataset cleanly, populating missing values to prevent render crashes.
    file_mtime is only part of the cache key, so edits made to the CSV outside the app invalidate the cache."""
    if not os.path.exists(file_path):
        return pd.DataFrame(columns=expected_cols)
    try:
        df = pd.read_csv(file_path)
        df = df.fillna('Unassigned') 
        return df
    except Exception as e:
        st.error(f"Failed to parse {file_path}: {e}")
        return pd.DataFrame(columns=expected_cols)

def restore_blank_cells(df, file_path):
    """Reverts display-only 'Unassigned' fills back to blanks for cells that were empty in the source CSV."""
    if not os.path.exists(file_path):
        return df
    original = pd.read_csv(file_path)
    df = df.copy()
    shared_idx = df.index.intersection(original.index)
    for col in df.columns.intersection(original.columns):
        was_blank = original.loc[shared_idx, col].isna()
        still_filled = df.loc[shared_idx, col].astype(str) == 'Unassigned'
        mask = was_blank & still_filled
        df.loc[mask[mask].index, col] = None
    return df

def restore_integer_columns(df):
    """Casts numeric columns holding only whole numbers to nullable Int64, so blanks don't turn 10 into 10.0 on save."""
    df = df.copy()
    for col in df.columns:
        values = df[col].dropna()
        if values.empty:
            continue
        numeric = pd.to_numeric(values, errors='coerce')
        is_number = values.map(lambda v: pd.api.types.is_number(v) and not pd.api.types.is_bool(v))
        if is_number.all() and numeric.notna().all() and (numeric % 1 == 0).all():
            df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
    return df

# -----------------------------------------------------------------------------
# UI COMPONENTS & CHART STYLING
# -----------------------------------------------------------------------------
# Categorical slots (validated for colour-vision deficiency); colour follows the entity, never its rank
CATEGORICAL_COLORS = ["#2A78D6", "#EB6834", "#1BAF7A", "#EDA100", "#E87BA4", "#008300", "#4A3AA7", "#E34948"]
OTHER_COLOR = "#A3ACB9"
STATUS_COLORS = {"good": "#0CA30C", "warning": "#FAB219", "serious": "#EC835A", "critical": "#D03B3B"}
LEVEL_ORDER = ["Analyst", "Staff 1", "Staff 2", "Staff", "Senior 1", "Senior 2", "Senior 3", "Senior",
               "Manager", "Senior Manager", "Associate Director", "Director"]
# One fixed colour per resource level everywhere in the app; unlisted levels fold to grey
LEVEL_COLORS = {"Staff 1": CATEGORICAL_COLORS[0], "Staff 2": CATEGORICAL_COLORS[1], "Senior 3": CATEGORICAL_COLORS[2],
                "Manager": CATEGORICAL_COLORS[3], "Senior 1": CATEGORICAL_COLORS[4], "Senior Manager": CATEGORICAL_COLORS[5],
                "Senior 2": CATEGORICAL_COLORS[6], "Director": CATEGORICAL_COLORS[7]}

PIPELINE_STATUS_ORDER = ["Open", "Awaiting Confirmation", "Fulfilled", "Invalid"]
PIPELINE_STATUS_COLORS = {"Open": "#2A78D6", "Awaiting Confirmation": STATUS_COLORS["warning"],
                          "Fulfilled": STATUS_COLORS["good"], "Invalid": STATUS_COLORS["critical"]}
# Bench lifecycle is ordered, so it uses a single-hue ramp from light (early) to dark (billing)
DST_STATUS_ORDER = ["Awaiting Engagement", "Profile Shared", "Onboarding Started", "Billing Started"]
DST_STATUS_COLORS = {"Awaiting Engagement": "#86B6EF", "Profile Shared": "#5598E7",
                     "Onboarding Started": "#2A78D6", "Billing Started": "#1C5CAB"}


def render_page_header(breadcrumb, title, subtitle, chips):
    chip_html = "".join(f'<span class="meta-chip">{label} <b>{value}</b></span>' for label, value in chips)
    st.markdown(f"""
    <div class="app-header">
        <div>
            <div class="app-breadcrumb">{breadcrumb}</div>
            <div class="app-title">{title}</div>
            <div class="app-subtitle">{subtitle}</div>
        </div>
        <div class="meta-row">{chip_html}</div>
    </div>
    """, unsafe_allow_html=True)


def render_kpis(items):
    """items: list of dicts with label, value, foot and optional unit / dot colour."""
    cards = []
    for item in items:
        dot = f'<span class="dot" style="background:{item["dot"]};"></span>' if item.get("dot") else ""
        unit = f'<small>{item["unit"]}</small>' if item.get("unit") else ""
        cards.append(f"""
        <div class="kpi">
            <div class="kpi-label">{dot}{item['label']}</div>
            <div class="kpi-value">{item['value']}{unit}</div>
            <div class="kpi-foot">{item['foot']}</div>
        </div>""")
    st.markdown(f'<div class="kpi-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def card_heading(title, subtitle=""):
    sub = f'<div class="card-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(f'<div class="card-title">{title}</div>{sub}', unsafe_allow_html=True)


def pct(part, whole):
    return f"{(part / whole * 100):.0f}%" if whole else "0%"


def level_color_map(levels):
    """Level -> colour for the given levels, in seniority order."""
    ordered = sorted(set(levels), key=lambda lv: (LEVEL_ORDER.index(lv) if lv in LEVEL_ORDER else len(LEVEL_ORDER), lv))
    return {lv: LEVEL_COLORS.get(lv, OTHER_COLOR) for lv in ordered}


def style_figure(fig, height=300):
    fig.update_layout(
        height=height,
        margin=dict(l=4, r=16, t=8, b=8),
        font=dict(family="Inter, system-ui, -apple-system, 'Segoe UI', sans-serif", size=12, color="#5C6B82"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(bgcolor="#0F1B2D", bordercolor="#0F1B2D", font=dict(color="#FFFFFF", family="Inter, sans-serif", size=12)),
        legend=dict(orientation="h", yanchor="top", y=-0.14, xanchor="left", x=0, title_text="", font=dict(size=12, color="#33415C")),
        bargap=0.45,
        barcornerradius=4,
    )
    fig.update_xaxes(showgrid=False, linecolor="#C9CFD8", ticks="", tickfont=dict(color="#5C6B82"), title_text="", automargin=True)
    fig.update_yaxes(gridcolor="#EBEEF3", zeroline=False, linecolor="#C9CFD8", ticks="", tickfont=dict(color="#5C6B82"), title_text="",
                     automargin=True, ticklabelstandoff=8)
    return fig


def status_breakdown_chart(status_values, order, colors, noun):
    """Horizontal bars in lifecycle order, each labelled with count and share."""
    clean = status_values.astype(str).str.strip().str.title()
    clean = clean[clean != "Unassigned"]
    counts = clean.value_counts()
    categories = [s for s in order if s in counts.index] + sorted(s for s in counts.index if s not in order)
    values = [int(counts[c]) for c in categories]
    total = sum(values)
    fig = go.Figure(go.Bar(
        x=values,
        y=categories,
        orientation="h",
        marker=dict(color=[colors.get(c, OTHER_COLOR) for c in categories], line=dict(width=0)),
        text=[f"{v}  ·  {pct(v, total)}" for v in values],
        textposition="outside",
        textfont=dict(color="#33415C", size=12),
        cliponaxis=False,
        hovertemplate=f"<b>%{{y}}</b><br>{noun}: %{{x}}<extra></extra>",
    ))
    style_figure(fig, height=max(200, 64 * len(categories) + 40))
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)", linecolor="#C9CFD8", tickfont=dict(color="#33415C", size=12))
    fig.update_xaxes(showticklabels=False, showline=False, range=[0, max(values + [1]) * 1.35])
    fig.update_layout(bargap=0.38, showlegend=False)
    return fig


def monthly_level_chart(df, date_col, level_col, noun):
    """Stacked monthly counts by resource level; returns None when there is nothing to plot."""
    plot_df = df[(df[date_col] != "Unassigned") & (df[level_col] != "Unassigned")].copy()
    plot_df["_date"] = pd.to_datetime(plot_df[date_col], errors="coerce")
    plot_df = plot_df.dropna(subset=["_date"])
    if plot_df.empty:
        return None
    plot_df["_month"] = plot_df["_date"].dt.to_period("M")
    counts = plot_df.groupby(["_month", level_col]).size().reset_index(name=noun).sort_values("_month")
    counts["Month"] = counts["_month"].dt.strftime("%b %Y")
    month_order = list(dict.fromkeys(counts["Month"]))
    colors = level_color_map(plot_df[level_col])
    fig = go.Figure()
    for level, color in colors.items():
        level_counts = counts[counts[level_col] == level]
        if level_counts.empty:
            continue
        fig.add_bar(
            x=level_counts["Month"], y=level_counts[noun], name=level,
            marker=dict(color=color, line=dict(color="#FFFFFF", width=2)),
            hovertemplate=f"<b>%{{x}}</b><br>{level}: %{{y}} {noun.lower()}<extra></extra>",
        )
    style_figure(fig, height=300)
    fig.update_layout(barmode="stack", legend_traceorder="normal")
    fig.update_xaxes(categoryorder="array", categoryarray=month_order)
    fig.update_yaxes(dtick=1, rangemode="tozero")
    return fig


def bench_aging_chart(df, days_col, name_col, id_col):
    """Horizontal bars of bench days per resource, longest first; returns None without numeric data."""
    aging = df[[name_col, id_col]].copy()
    aging["days"] = pd.to_numeric(df[days_col], errors="coerce")
    aging = aging.dropna(subset=["days"]).sort_values("days", ascending=False)
    if aging.empty:
        return None
    aging["label"] = aging[name_col].astype(str) + "  ·  " + aging[id_col].astype(str)
    fig = go.Figure(go.Bar(
        x=aging["days"], y=aging["label"], orientation="h",
        marker=dict(color=CATEGORICAL_COLORS[0], line=dict(width=0)),
        text=aging["days"].astype(int).astype(str) + " days", textposition="outside",
        textfont=dict(color="#33415C", size=12), cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>Bench days: %{x}<extra></extra>",
    ))
    style_figure(fig, height=max(200, 44 * len(aging) + 40))
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)", tickfont=dict(color="#33415C", size=12))
    fig.update_xaxes(showticklabels=False, showline=False, range=[0, aging["days"].max() * 1.3])
    fig.update_layout(bargap=0.4, showlegend=False)
    return fig


def show_chart(fig):
    st.plotly_chart(fig, width="stretch", theme=None, config={"displayModeBar": False})


def status_cell_style(colors):
    """Pandas Styler row function: tints the Status cell using the chart's status colours."""
    def _style(row):
        styles = [""] * len(row)
        if "Status" in row.index and pd.notna(row.get("Status")):
            color = colors.get(str(row["Status"]).strip().title())
            if color:
                styles[row.index.get_loc("Status")] = f"color: #0F1B2D; font-weight: 600; background-color: {color}22;"
        return styles
    return _style


# -----------------------------------------------------------------------------
# SIDEBAR NAVIGATION & ENTERPRISE APP SHELL
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div class="sb-brand">
        <div class="sb-brand-title"><span class="sb-logo">RM</span>Resource Management</div>
        <div class="sb-brand-sub">Performance Testing · Resourcing Console</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sb-label">Workspaces</div>', unsafe_allow_html=True)
    selection = st.radio(
        "Navigation",
        list(FILES.keys()),
        label_visibility="collapsed"
    )

    current_config = FILES[selection]
    file_path = current_config["path"]
    expected_cols = current_config["cols"]
    raw_df = load_data(file_path, expected_cols, os.path.getmtime(file_path) if os.path.exists(file_path) else None)
    refresh_time_str = get_last_refresh_timestamp(file_path)

    st.markdown('<div class="sb-label">Data Source</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="sb-card">
        <div class="sb-row"><span>File</span><b>{file_path}</b></div>
        <div class="sb-row"><span>Records</span><b>{len(raw_df)}</b></div>
        <div class="sb-row"><span>Last updated</span><b>{refresh_time_str}</b></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
    if st.button("Refresh data", icon=":material/refresh:", width="stretch"):
        load_data.clear()
        st.session_state["cache_refreshed_toast"] = True
        st.rerun()

    if st.session_state.get("cache_refreshed_toast"):
        st.toast("Data reloaded from source.", icon=":material/check_circle:")
        st.session_state["cache_refreshed_toast"] = False

    ai_client = LLMClient()
    if ai_client.is_available():
        ai_status_color, ai_status_text = STATUS_COLORS["good"], f"Connected · {ai_client.provider.title()} ({ai_client.model})"
    else:
        ai_status_color, ai_status_text = OTHER_COLOR, "Offline · built-in query engine"
    st.markdown('<div class="sb-label">AI Assistant</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="sb-card sb-status"><span class="dot" style="background:{ai_status_color};"></span>{ai_status_text}</div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# MAIN DASHBOARD HEADER
# -----------------------------------------------------------------------------
render_page_header(
    breadcrumb=f"Resource Management &nbsp;/&nbsp; <b>{selection}</b>",
    title=selection,
    subtitle=current_config["description"],
    chips=[("Records", len(raw_df)), ("Updated", refresh_time_str)],
)

if st.session_state.pop("records_saved_toast", False):
    st.toast("Changes saved to the source file.", icon=":material/check_circle:")


# =============================================================================
# MODULE 1: PIPELINE DEMANDS
# =============================================================================
if selection == "Pipeline Demands":
    # -------------------------------------------------------------------------
    # KPI STRIP
    # -------------------------------------------------------------------------
    if not raw_df.empty and 'Status' in raw_df.columns:
        total_demands = len(raw_df)

        # Standardize status for accurate calculation
        status_series = raw_df['Status'].astype(str).str.strip().str.upper()

        open_count = int((status_series == 'OPEN').sum())
        awaiting_count = int((status_series == 'AWAITING CONFIRMATION').sum())
        invalid_count = int((status_series == 'INVALID').sum())
        fulfilled_count = int((status_series == 'FULFILLED').sum())

        # Check unassigned PT leads
        if 'Sector PT lead' in raw_df.columns:
            unassigned_leads = int((raw_df['Sector PT lead'].astype(str).str.strip().str.lower() == 'unassigned').sum())
        else:
            unassigned_leads = 0

        render_kpis([
            {"label": "Total demands (FY-27)", "value": total_demands, "foot": f"{fulfilled_count} fulfilled to date"},
            {"label": "Open", "value": open_count, "foot": f"{pct(open_count, total_demands)} of all demands",
             "dot": PIPELINE_STATUS_COLORS["Open"]},
            {"label": "Awaiting confirmation", "value": awaiting_count, "foot": "Pending lead validation",
             "dot": STATUS_COLORS["warning"]},
            {"label": "Invalid", "value": invalid_count, "foot": "Requires review", "dot": STATUS_COLORS["critical"]},
            {"label": "Unassigned PT lead", "value": unassigned_leads,
             "foot": f"{pct(unassigned_leads, total_demands)} of all demands"},
        ])

    tab_overview, tab_records, tab_ai = st.tabs([
        ":material/monitoring: Overview", ":material/table_rows: Records", ":material/auto_awesome: AI Assistant"
    ])

    # -------------------------------------------------------------------------
    # OVERVIEW: ANALYTICS
    # -------------------------------------------------------------------------
    with tab_overview:
        if raw_df.empty:
            st.markdown('<div class="empty-state"><b>No pipeline demands yet</b>Add records in the Records tab.</div>', unsafe_allow_html=True)
        else:
            chart_col1, chart_col2 = st.columns([1, 1.35], gap="medium")
            with chart_col1:
                with st.container(border=True, key="card-pipeline-status"):
                    card_heading("Demand by status", "Count and share of all pipeline demands")
                    if 'Status' in raw_df.columns:
                        show_chart(status_breakdown_chart(raw_df['Status'], PIPELINE_STATUS_ORDER, PIPELINE_STATUS_COLORS, "Demands"))
            with chart_col2:
                with st.container(border=True, key="card-pipeline-monthly"):
                    card_heading("Open demand by start month", "Stacked by resource level")
                    fig_monthly = None
                    if {'Start Date', 'Resource Level', 'Status'} <= set(raw_df.columns):
                        open_df = raw_df[raw_df['Status'].astype(str).str.strip().str.upper() == 'OPEN']
                        fig_monthly = monthly_level_chart(open_df, 'Start Date', 'Resource Level', 'Demands')
                    if fig_monthly is not None:
                        show_chart(fig_monthly)
                    else:
                        st.caption("No open demands with a valid start date.")

    with tab_records:
        # -------------------------------------------------------------------------
        # ADVANCED FILTER TOOLBAR & DATA CONTROLS
        # -------------------------------------------------------------------------

        # Filter Controls Card
        with st.container(border=True, key="card-filters-pipeline"):
            f_c1, f_c2, f_c3, f_c4 = st.columns([2, 1.2, 1.2, 1.2])
        
            with f_c1:
                search_query = st.text_input(
                    "Search",
                    placeholder="Search role, client, sector or engineer",
                    label_visibility="collapsed",
                    icon=":material/search:",
                    key="search_query_pipeline"
                )
            
            with f_c2:
                # Dynamic Status Filter Options
                status_options = ["All Statuses"]
                if 'Status' in raw_df.columns:
                    unique_statuses = sorted([s for s in raw_df['Status'].dropna().unique() if s != 'Unassigned'])
                    status_options.extend(unique_statuses)
                selected_status = st.selectbox("Status Filter", status_options, label_visibility="collapsed", key="status_pipeline")
            
            with f_c3:
                # Dynamic Resource Level Filter Options
                level_options = ["All Levels"]
                if 'Resource Level' in raw_df.columns:
                    unique_levels = sorted([l for l in raw_df['Resource Level'].dropna().unique() if l != 'Unassigned'])
                    level_options.extend(unique_levels)
                selected_level = st.selectbox("Resource Level Filter", level_options, label_visibility="collapsed", key="level_pipeline")
            
            with f_c4:
                # Dynamic Sector PT Lead Filter Options
                lead_options = ["All PT Leads"]
                if 'Sector PT lead' in raw_df.columns:
                    unique_leads = sorted([ld for ld in raw_df['Sector PT lead'].dropna().unique() if ld != 'Unassigned'])
                    lead_options.extend(unique_leads)
                selected_lead = st.selectbox("PT Lead Filter", lead_options, label_visibility="collapsed", key="lead_pipeline")

        # Apply Active Filters
        display_df = raw_df.copy()

        # Enforce explicit data types across schema per constraints
        for col in display_df.columns:
            if col in ['GUI', 'GPN']:
                display_df[col] = pd.to_numeric(display_df[col], errors='coerce').fillna(0).astype(int)
            elif 'Date' in col:
                display_df[col] = pd.to_datetime(display_df[col], errors='coerce').dt.date
            else:
                display_df[col] = display_df[col].astype(str)

        # 1. Global Text Filter
        if search_query and not display_df.empty:
            mask = display_df.apply(lambda row: row.astype(str).str.contains(search_query, case=False, na=False, regex=False).any(), axis=1)
            display_df = display_df[mask]

        # 2. Status Filter
        if selected_status != "All Statuses" and 'Status' in display_df.columns:
            display_df = display_df[display_df['Status'].astype(str).str.strip().str.lower() == selected_status.strip().lower()]

        # 3. Resource Level Filter
        if selected_level != "All Levels" and 'Resource Level' in display_df.columns:
            display_df = display_df[display_df['Resource Level'].astype(str).str.strip() == selected_level.strip()]

        # 4. Sector PT Lead Filter
        if selected_lead != "All PT Leads" and 'Sector PT lead' in display_df.columns:
            display_df = display_df[display_df['Sector PT lead'].astype(str).str.strip().str.lower() == selected_lead.strip().lower()]

        # Filter Status & Action Bar
        ctrl_left, ctrl_right = st.columns([2, 1.5], vertical_alignment="center")

        with ctrl_left:
            total_recs = len(raw_df)
            shown_recs = len(display_df)
            active_filters = [f for f in (selected_status, selected_level, selected_lead) if not f.startswith("All ")]
            if search_query:
                active_filters.insert(0, f'"{search_query}"')
            filter_note = f'<span class="filter-note">Filtered by {", ".join(active_filters)}</span>' if active_filters else ""
            st.markdown(f'<span class="result-pill">{shown_recs} of {total_recs} demands</span>{filter_note}', unsafe_allow_html=True)

        with ctrl_right:
            btn_col1, btn_col2 = st.columns([1, 1])
            with btn_col1:
                edit_mode = st.toggle("Edit mode", value=False, help="Edit cells inline, add rows at the bottom, or mark rows for deletion", key="edit_mode_pipeline")
            with btn_col2:
                if not display_df.empty:
                    export_df = display_df.drop(columns=['🗑️ Delete Row'], errors='ignore')
                    csv_export = export_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Export CSV",
                        icon=":material/download:",
                        data=csv_export,
                        file_name=f"pipeline_demands_export_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        width="stretch",
                        key="export_pipeline_btn"
                    )

        # -------------------------------------------------------------------------
        # MAIN DATA TABLE & EDITOR
        # -------------------------------------------------------------------------
        if edit_mode:
            st.markdown(
                '<div class="notice notice-warning"><strong>Edit mode is on.</strong> Double-click a cell to change it, '
                'add rows at the bottom of the table, or tick <em>Delete Row</em> to remove a record. '
                'Changes are written to the source file only when you select <strong>Save changes</strong>.</div>',
                unsafe_allow_html=True)

        if not display_df.empty or raw_df.empty:
            editor_key = f"editor_{selection}"
        
            # Setup structured column configuration
            col_config = {}
            for col in display_df.columns:
                if col in ['GUI', 'GPN', 'Role ID', 'Eng ID']:
                    col_config[col] = st.column_config.NumberColumn(col, format="%d", min_value=0, step=1)
                elif 'Date' in col:
                    col_config[col] = st.column_config.DateColumn(col, format="MM/DD/YYYY")
                elif col == 'Status':
                    col_config[col] = st.column_config.SelectboxColumn(
                        col,
                        help="Pipeline Demand Status",
                        options=["Open", "Awaiting Confirmation", "Invalid", "Fulfilled"],
                        required=True
                    ) if edit_mode else st.column_config.TextColumn(col)
                elif col != '🗑️ Delete Row':
                    col_config[col] = st.column_config.TextColumn(col)
                
            if edit_mode:
                if not display_df.empty and '🗑️ Delete Row' not in display_df.columns:
                    display_df.insert(0, '🗑️ Delete Row', False)
                
            # Apply status highlight styling for read mode
            styled_df = display_df
            if 'Status' in display_df.columns:
                styled_df = display_df.style.apply(status_cell_style(PIPELINE_STATUS_COLORS), axis=1)

            if edit_mode:
                st.data_editor(
                    styled_df, 
                    width="stretch", 
                    height=380,
                    num_rows="dynamic",
                    hide_index=True,
                    key=editor_key,
                    column_config=col_config
                )
            else:
                st.dataframe(
                    styled_df,
                    width="stretch",
                    height=380,
                    hide_index=True,
                    column_config=col_config
                )
        
            # Edit State Handling & Save Serialization
            editor_state = st.session_state.get(editor_key, {})
            has_changes = any(len(v) > 0 for v in editor_state.values() if isinstance(v, dict) or isinstance(v, list))
        
            if has_changes:
                st.warning("You have unsaved changes in the table above.", icon=":material/edit_note:")
                if st.button("Save changes", icon=":material/save:", width="stretch", type="primary", key="save_pipeline_btn"):
                    explicit_deletes = []
                
                    # 1. Updates & Explicit Deletions
                    for idx_pos, changes in editor_state.get("edited_rows", {}).items():
                        true_idx = display_df.index[idx_pos]
                    
                        if changes.get('🗑️ Delete Row', False) is True:
                            explicit_deletes.append(true_idx)
                        else:
                            for col, val in changes.items():
                                if col != '🗑️ Delete Row':
                                    if raw_df[col].dtype != 'object':
                                        raw_df[col] = raw_df[col].astype('object')
                                    raw_df.at[true_idx, col] = val
                                
                    # 2. Native Deletions
                    deleted_indices = editor_state.get("deleted_rows", [])
                    if deleted_indices:
                        native_deleted = [display_df.index[i] for i in deleted_indices]
                        explicit_deletes.extend(native_deleted)
                    
                    # Process Deletions
                    if explicit_deletes:
                        raw_df = raw_df.drop(index=list(set(explicit_deletes)))

                    # Undo display-only 'Unassigned' fills before additions reset the index
                    raw_df = restore_blank_cells(raw_df, file_path)
                    
                    # 3. Additions
                    added_rows = editor_state.get("added_rows", [])
                    if added_rows:
                        new_df = pd.DataFrame(added_rows)
                        if '🗑️ Delete Row' in new_df.columns:
                            new_df = new_df.drop(columns=['🗑️ Delete Row'])
                        for c in raw_df.columns:
                            if c not in new_df.columns:
                                new_df[c] = None
                        raw_df = pd.concat([raw_df, new_df[raw_df.columns]], ignore_index=True)
                    
                    # Save back to CSV
                    df_to_save = restore_integer_columns(raw_df[[c for c in expected_cols if c in raw_df.columns]])
                    df_to_save.to_csv(file_path, index=False)
                    st.session_state["records_saved_toast"] = True
                    load_data.clear()
                    st.rerun()
        else:
            st.markdown('<div class="empty-state"><b>No matching demands</b>Adjust or clear the search and filters above.</div>', unsafe_allow_html=True)

    with tab_ai:
        # -------------------------------------------------------------------------
        # PIPELINE DEMAND AI ASSISTANT
        # -------------------------------------------------------------------------
        st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

        with st.container():
            st.markdown("""
            <div class="ai-head">
                <div>
                    <div class="ai-tag">AI Assistant</div>
                    <div class="card-title">Pipeline Intelligence Assistant</div>
                    <div class="card-subtitle">Ask about pipeline volume, fulfilment status, seniority mix and lead allocation.</div>
                </div>
                <span class="source-chip">Answers grounded in PipelineDemand_Details.csv</span>
            </div>
            """, unsafe_allow_html=True)

            # Contextual data detection
            is_filtered = (search_query != "" or selected_status != "All Statuses" or selected_level != "All Levels" or selected_lead != "All PT Leads") and not display_df.empty
        
            if is_filtered:
                st.markdown(f"""
                <div class="notice notice-info">
                    <strong>Filtered view:</strong> answers use only the current filter selection (<strong>{len(display_df)}</strong> matching demands).
                </div>
                """, unsafe_allow_html=True)
                working_df = display_df.drop(columns=['🗑️ Delete Row'], errors='ignore')
            else:
                st.markdown(f"""
                <div class="notice notice-neutral">
                    <strong>Full dataset:</strong> answers cover all <strong>{len(raw_df)}</strong> pipeline demand records.
                </div>
                """, unsafe_allow_html=True)
                working_df = raw_df.copy()

            # Initialize Assistant
            ai_assistant = PipelineAIAssistant(df=working_df)

            if "ai_chat_history" not in st.session_state:
                st.session_state.ai_chat_history = []

            # Suggested Prompts Expander
            with st.expander("Suggested questions", icon=":material/lightbulb:", expanded=len(st.session_state.ai_chat_history) == 0):
                suggested_list = PipelineAIAssistant.get_suggested_questions()
                sugg_cols = st.columns(2)
                clicked_suggestion = None
                for s_idx, s_text in enumerate(suggested_list):
                    t_col = sugg_cols[s_idx % 2]
                    with t_col:
                        if st.button(s_text, key=f"btn_sugg_{s_idx}", width="stretch"):
                            clicked_suggestion = s_text

            # Clear Chat Action
            if st.session_state.ai_chat_history:
                c_clear_space, c_clear_btn = st.columns([5, 1])
                with c_clear_btn:
                    if st.button("Clear chat", icon=":material/delete_sweep:", key="clear_chat_btn", width="stretch"):
                        st.session_state.ai_chat_history = []
                        st.rerun()

            # Render Conversation Transcript
            for chat_msg in st.session_state.ai_chat_history:
                with st.chat_message(chat_msg["role"]):
                    st.markdown(chat_msg["content"])

            # Chat Input Box
            user_chat_query = st.chat_input("Ask a question about pipeline demands", key="pipeline_chat_input")
            active_chat_query = clicked_suggestion or user_chat_query

            if active_chat_query:
                st.session_state.ai_chat_history.append({"role": "user", "content": active_chat_query})
                with st.chat_message("user"):
                    st.markdown(active_chat_query)

                with st.chat_message("assistant"):
                    with st.spinner("Analyzing Pipeline Demand records..."):
                        ans_res = ai_assistant.answer_question(active_chat_query)
                        ans_md = ans_res["response"]
                        st.markdown(ans_md)
                        st.session_state.ai_chat_history.append({"role": "assistant", "content": ans_md})


# =============================================================================
# MODULE 2: DST BENCH RESOURCES
# =============================================================================
elif selection == "DST Bench Resources":
    # -------------------------------------------------------------------------
    # KPI STRIP
    # -------------------------------------------------------------------------
    if not raw_df.empty and 'Status' in raw_df.columns:
        # Standardize status for accurate calculation
        status_series = raw_df['Status'].astype(str).str.strip().str.upper()
        total_bench = int((status_series != 'BILLING STARTED').sum())

        profile_shared_count = int((status_series == 'PROFILE SHARED').sum())
        onboarding_billing_count = int(((status_series == 'ONBOARDING STARTED') | (status_series == 'BILLING STARTED')).sum())
        awaiting_count = int((status_series == 'AWAITING ENGAGEMENT').sum())

        # Compute Average Bench Days
        if 'Bench Days' in raw_df.columns:
            bench_days_series = pd.to_numeric(raw_df['Bench Days'], errors='coerce').dropna()
            avg_bench_days = int(round(bench_days_series.mean())) if not bench_days_series.empty else 0
        else:
            avg_bench_days = 0

        render_kpis([
            {"label": "Active bench", "value": total_bench, "foot": "Excludes billing started"},
            {"label": "Awaiting engagement", "value": awaiting_count, "foot": "Ready for allocation",
             "dot": DST_STATUS_COLORS["Awaiting Engagement"]},
            {"label": "Profile shared", "value": profile_shared_count, "foot": "In client review",
             "dot": DST_STATUS_COLORS["Profile Shared"]},
            {"label": "Onboarding / billing", "value": onboarding_billing_count, "foot": "Deployment started",
             "dot": DST_STATUS_COLORS["Onboarding Started"]},
            {"label": "Avg bench duration", "value": avg_bench_days, "unit": "days", "foot": "Mean time on bench"},
        ])

    tab_overview, tab_records, tab_ai = st.tabs([
        ":material/monitoring: Overview", ":material/table_rows: Records", ":material/auto_awesome: AI Assistant"
    ])

    # -------------------------------------------------------------------------
    # OVERVIEW: ANALYTICS
    # -------------------------------------------------------------------------
    with tab_overview:
        if raw_df.empty:
            st.markdown('<div class="empty-state"><b>No bench resources yet</b>Add records in the Records tab.</div>', unsafe_allow_html=True)
        else:
            chart_col1, chart_col2 = st.columns([1, 1.35], gap="medium")
            with chart_col1:
                with st.container(border=True, key="card-dst-status"):
                    card_heading("Bench by stage", "Engagement lifecycle, earliest stage first")
                    if 'Status' in raw_df.columns:
                        show_chart(status_breakdown_chart(raw_df['Status'], DST_STATUS_ORDER, DST_STATUS_COLORS, "Resources"))
            with chart_col2:
                with st.container(border=True, key="card-dst-monthly"):
                    card_heading("Releases by month", "Last project release date, stacked by resource level")
                    fig_monthly = None
                    if {'Last Project Release Date', 'Resource Level'} <= set(raw_df.columns):
                        fig_monthly = monthly_level_chart(raw_df, 'Last Project Release Date', 'Resource Level', 'Resources')
                    if fig_monthly is not None:
                        show_chart(fig_monthly)
                    else:
                        st.caption("No valid release dates to chart.")

            if {'Bench Days', 'Name', 'GPN'} <= set(raw_df.columns):
                fig_aging = bench_aging_chart(raw_df, 'Bench Days', 'Name', 'GPN')
                if fig_aging is not None:
                    with st.container(border=True, key="card-dst-aging"):
                        card_heading("Bench aging", "Days on bench per resource, longest first")
                        show_chart(fig_aging)

    with tab_records:
        # -------------------------------------------------------------------------
        # ADVANCED FILTER TOOLBAR & DATA CONTROLS
        # -------------------------------------------------------------------------

        # Filter Controls Card
        with st.container(border=True, key="card-filters-dst"):
            f_c1, f_c2, f_c3, f_c4, f_c5 = st.columns([1.8, 1.2, 1.2, 1.2, 1.2])
        
            with f_c1:
                search_query_dst = st.text_input(
                    "Search",
                    placeholder="Search GPN, name, level, project or location",
                    label_visibility="collapsed",
                    icon=":material/search:",
                    key="search_query_dst"
                )
            
            with f_c2:
                # Dynamic Status Filter Options
                status_options_dst = ["All Statuses"]
                if 'Status' in raw_df.columns:
                    unique_statuses_dst = sorted([s for s in raw_df['Status'].dropna().unique() if s != 'Unassigned'])
                    status_options_dst.extend(unique_statuses_dst)
                selected_status_dst = st.selectbox("Status Filter", status_options_dst, label_visibility="collapsed", key="status_dst")
            
            with f_c3:
                # Dynamic Resource Level Filter Options
                level_options_dst = ["All Levels"]
                if 'Resource Level' in raw_df.columns:
                    unique_levels_dst = sorted([l for l in raw_df['Resource Level'].dropna().unique() if l != 'Unassigned'])
                    level_options_dst.extend(unique_levels_dst)
                selected_level_dst = st.selectbox("Resource Level Filter", level_options_dst, label_visibility="collapsed", key="level_dst")
            
            with f_c4:
                # Dynamic Location Filter Options
                location_options = ["All Locations"]
                if 'Location' in raw_df.columns:
                    unique_locations = sorted([loc for loc in raw_df['Location'].dropna().unique() if loc != 'Unassigned'])
                    location_options.extend(unique_locations)
                selected_location = st.selectbox("Location Filter", location_options, label_visibility="collapsed", key="loc_dst")

            with f_c5:
                # Dynamic Counsellor Filter Options
                counsellor_col_name = 'Cousellor Name' if 'Cousellor Name' in raw_df.columns else ('Counsellor Name' if 'Counsellor Name' in raw_df.columns else None)
                counsellor_options = ["All Counsellors"]
                if counsellor_col_name and counsellor_col_name in raw_df.columns:
                    unique_counsellors = sorted([c for c in raw_df[counsellor_col_name].dropna().unique() if c != 'Unassigned'])
                    counsellor_options.extend(unique_counsellors)
                selected_counsellor = st.selectbox("Counsellor Filter", counsellor_options, label_visibility="collapsed", key="counsellor_dst")

        # Apply Active Filters
        display_df = raw_df.copy()

        # Enforce explicit data types across schema
        for col in display_df.columns:
            if col in ['GPN', 'GUI']:
                display_df[col] = pd.to_numeric(display_df[col], errors='coerce').fillna(0).astype(int)
            elif col == 'Bench Days':
                display_df[col] = pd.to_numeric(display_df[col], errors='coerce').fillna(0).astype(int)
            elif 'Date' in col:
                display_df[col] = pd.to_datetime(display_df[col], errors='coerce').dt.date
            else:
                display_df[col] = display_df[col].astype(str)

        # 1. Global Text Filter
        if search_query_dst and not display_df.empty:
            mask = display_df.apply(lambda row: row.astype(str).str.contains(search_query_dst, case=False, na=False, regex=False).any(), axis=1)
            display_df = display_df[mask]

        # 2. Status Filter
        if selected_status_dst != "All Statuses" and 'Status' in display_df.columns:
            display_df = display_df[display_df['Status'].astype(str).str.strip().str.lower() == selected_status_dst.strip().lower()]

        # 3. Resource Level Filter
        if selected_level_dst != "All Levels" and 'Resource Level' in display_df.columns:
            display_df = display_df[display_df['Resource Level'].astype(str).str.strip() == selected_level_dst.strip()]

        # 4. Location Filter
        if selected_location != "All Locations" and 'Location' in display_df.columns:
            display_df = display_df[display_df['Location'].astype(str).str.strip().str.lower() == selected_location.strip().lower()]

        # 5. Counsellor Filter
        if counsellor_col_name and selected_counsellor != "All Counsellors" and counsellor_col_name in display_df.columns:
            display_df = display_df[display_df[counsellor_col_name].astype(str).str.strip().str.lower() == selected_counsellor.strip().lower()]

        # Filter Status & Action Bar
        ctrl_left, ctrl_right = st.columns([2, 1.5], vertical_alignment="center")

        with ctrl_left:
            total_recs = len(raw_df)
            shown_recs = len(display_df)
            active_filters = [f for f in (selected_status_dst, selected_level_dst, selected_location, selected_counsellor) if not f.startswith("All ")]
            if search_query_dst:
                active_filters.insert(0, f'"{search_query_dst}"')
            filter_note = f'<span class="filter-note">Filtered by {", ".join(active_filters)}</span>' if active_filters else ""
            st.markdown(f'<span class="result-pill">{shown_recs} of {total_recs} bench resources</span>{filter_note}', unsafe_allow_html=True)

        with ctrl_right:
            btn_col1, btn_col2 = st.columns([1, 1])
            with btn_col1:
                edit_mode_dst = st.toggle("Edit mode", value=False, help="Edit cells inline, add rows at the bottom, or mark rows for deletion", key="edit_mode_dst")
            with btn_col2:
                if not display_df.empty:
                    export_df = display_df.drop(columns=['🗑️ Delete Row'], errors='ignore')
                    csv_export = export_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Export CSV",
                        icon=":material/download:",
                        data=csv_export,
                        file_name=f"dst_bench_export_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        width="stretch",
                        key="export_dst_btn"
                    )

        # -------------------------------------------------------------------------
        # MAIN DATA TABLE & EDITOR
        # -------------------------------------------------------------------------
        if edit_mode_dst:
            st.markdown(
                '<div class="notice notice-warning"><strong>Edit mode is on.</strong> Double-click a cell to change it, '
                'add rows at the bottom of the table, or tick <em>Delete Row</em> to remove a record. '
                'Changes are written to the source file only when you select <strong>Save changes</strong>.</div>',
                unsafe_allow_html=True)

        if not display_df.empty or raw_df.empty:
            editor_key_dst = f"editor_{selection}"
        
            # Setup structured column configuration
            col_config_dst = {}
            for col in display_df.columns:
                if col in ['GPN', 'GUI']:
                    col_config_dst[col] = st.column_config.NumberColumn(col, format="%d", min_value=0, step=1)
                elif col == 'Bench Days':
                    col_config_dst[col] = st.column_config.NumberColumn(col, format="%d Days" if not edit_mode_dst else "%d", min_value=0, step=1)
                elif 'Date' in col:
                    col_config_dst[col] = st.column_config.DateColumn(col, format="MM/DD/YYYY")
                elif col == 'Status':
                    col_config_dst[col] = st.column_config.SelectboxColumn(
                        col,
                        help="DST Bench Resource Status",
                        options=["Profile Shared", "Onboarding Started", "Billing Started", "Awaiting Engagement"],
                        required=True
                    ) if edit_mode_dst else st.column_config.TextColumn(col)
                elif col == 'Resource Level' and edit_mode_dst:
                    col_config_dst[col] = st.column_config.SelectboxColumn(
                        col,
                        help="Seniority Level",
                        options=["Staff 1", "Staff 2", "Senior 1", "Senior 2", "Senior 3", "Manager", "Senior Manager", "Associate Director", "Director"]
                    )
                elif col == 'Location' and edit_mode_dst:
                    col_config_dst[col] = st.column_config.SelectboxColumn(
                        col,
                        help="Office Location",
                        options=["Noida", "Bengaluru", "Pune", "Gurugram", "Hyderabad", "Chennai", "Kolkata", "Kochi", "Trivandrum", "Coimbatore"]
                    )
                elif col != '🗑️ Delete Row':
                    col_config_dst[col] = st.column_config.TextColumn(col)
                
            if edit_mode_dst:
                if not display_df.empty and '🗑️ Delete Row' not in display_df.columns:
                    display_df.insert(0, '🗑️ Delete Row', False)
                
            # Apply status highlight styling for read mode
            styled_df_dst = display_df
            if 'Status' in display_df.columns:
                styled_df_dst = display_df.style.apply(status_cell_style(DST_STATUS_COLORS), axis=1)

            if edit_mode_dst:
                st.data_editor(
                    styled_df_dst, 
                    width="stretch", 
                    height=380,
                    num_rows="dynamic",
                    hide_index=True,
                    key=editor_key_dst,
                    column_config=col_config_dst
                )
            else:
                st.dataframe(
                    styled_df_dst,
                    width="stretch",
                    height=380,
                    hide_index=True,
                    column_config=col_config_dst
                )
        
            # Edit State Handling & Save Serialization
            editor_state_dst = st.session_state.get(editor_key_dst, {})
            has_changes_dst = any(len(v) > 0 for v in editor_state_dst.values() if isinstance(v, dict) or isinstance(v, list))
        
            if has_changes_dst:
                st.warning("You have unsaved changes in the table above.", icon=":material/edit_note:")
                if st.button("Save changes", icon=":material/save:", width="stretch", type="primary", key="save_dst_btn"):
                    explicit_deletes = []
                
                    # 1. Updates & Explicit Deletions
                    for idx_pos, changes in editor_state_dst.get("edited_rows", {}).items():
                        true_idx = display_df.index[idx_pos]
                    
                        if changes.get('🗑️ Delete Row', False) is True:
                            explicit_deletes.append(true_idx)
                        else:
                            for col, val in changes.items():
                                if col != '🗑️ Delete Row':
                                    if raw_df[col].dtype != 'object':
                                        raw_df[col] = raw_df[col].astype('object')
                                    raw_df.at[true_idx, col] = val
                                
                    # 2. Native Deletions
                    deleted_indices = editor_state_dst.get("deleted_rows", [])
                    if deleted_indices:
                        native_deleted = [display_df.index[i] for i in deleted_indices]
                        explicit_deletes.extend(native_deleted)
                    
                    # Process Deletions
                    if explicit_deletes:
                        raw_df = raw_df.drop(index=list(set(explicit_deletes)))

                    # Undo display-only 'Unassigned' fills before additions reset the index
                    raw_df = restore_blank_cells(raw_df, file_path)
                    
                    # 3. Additions
                    added_rows = editor_state_dst.get("added_rows", [])
                    if added_rows:
                        new_df = pd.DataFrame(added_rows)
                        if '🗑️ Delete Row' in new_df.columns:
                            new_df = new_df.drop(columns=['🗑️ Delete Row'])
                        for c in raw_df.columns:
                            if c not in new_df.columns:
                                new_df[c] = None
                        raw_df = pd.concat([raw_df, new_df[raw_df.columns]], ignore_index=True)
                    
                    # Save back to CSV
                    df_to_save = restore_integer_columns(raw_df[[c for c in expected_cols if c in raw_df.columns]])
                    df_to_save.to_csv(file_path, index=False)
                    st.session_state["records_saved_toast"] = True
                    load_data.clear()
                    st.rerun()
        else:
            st.markdown('<div class="empty-state"><b>No matching bench resources</b>Adjust or clear the search and filters above.</div>', unsafe_allow_html=True)

    with tab_ai:
        # -------------------------------------------------------------------------
        # DST BENCH AI ASSISTANT
        # -------------------------------------------------------------------------
        st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

        with st.container():
            st.markdown("""
            <div class="ai-head">
                <div>
                    <div class="ai-tag">AI Assistant</div>
                    <div class="card-title">DST Bench Intelligence Assistant</div>
                    <div class="card-subtitle">Ask about bench resources, bench aging, locations and counsellor alignment.</div>
                </div>
                <span class="source-chip">Answers grounded in DST_Bench.csv</span>
            </div>
            """, unsafe_allow_html=True)

            # Contextual data detection
            is_filtered_dst = (search_query_dst != "" or selected_status_dst != "All Statuses" or selected_level_dst != "All Levels" or selected_location != "All Locations" or selected_counsellor != "All Counsellors") and not display_df.empty
        
            if is_filtered_dst:
                st.markdown(f"""
                <div class="notice notice-info">
                    <strong>Filtered view:</strong> answers use only the current filter selection (<strong>{len(display_df)}</strong> matching bench resources).
                </div>
                """, unsafe_allow_html=True)
                working_df_dst = display_df.drop(columns=['🗑️ Delete Row'], errors='ignore')
            else:
                st.markdown(f"""
                <div class="notice notice-neutral">
                    <strong>Full dataset:</strong> answers cover all <strong>{len(raw_df)}</strong> DST bench records.
                </div>
                """, unsafe_allow_html=True)
                working_df_dst = raw_df.copy()

            # Initialize DST Bench Assistant
            dst_ai_assistant = DSTBenchAIAssistant(df=working_df_dst)

            if "dst_ai_chat_history" not in st.session_state:
                st.session_state.dst_ai_chat_history = []

            # Suggested Prompts Expander
            with st.expander("Suggested questions", icon=":material/lightbulb:", expanded=len(st.session_state.dst_ai_chat_history) == 0):
                suggested_list_dst = DSTBenchAIAssistant.get_suggested_questions()
                sugg_cols_dst = st.columns(2)
                clicked_suggestion_dst = None
                for s_idx, s_text in enumerate(suggested_list_dst):
                    t_col = sugg_cols_dst[s_idx % 2]
                    with t_col:
                        if st.button(s_text, key=f"btn_sugg_dst_{s_idx}", width="stretch"):
                            clicked_suggestion_dst = s_text

            # Clear Chat Action
            if st.session_state.dst_ai_chat_history:
                c_clear_space, c_clear_btn = st.columns([5, 1])
                with c_clear_btn:
                    if st.button("Clear chat", icon=":material/delete_sweep:", key="clear_chat_dst_btn", width="stretch"):
                        st.session_state.dst_ai_chat_history = []
                        st.rerun()

            # Render Conversation Transcript
            for chat_msg in st.session_state.dst_ai_chat_history:
                with st.chat_message(chat_msg["role"]):
                    st.markdown(chat_msg["content"])

            # Chat Input Box
            user_chat_query_dst = st.chat_input("Ask a question about bench resources", key="dst_chat_input")
            active_chat_query_dst = clicked_suggestion_dst or user_chat_query_dst

            if active_chat_query_dst:
                st.session_state.dst_ai_chat_history.append({"role": "user", "content": active_chat_query_dst})
                with st.chat_message("user"):
                    st.markdown(active_chat_query_dst)

                with st.chat_message("assistant"):
                    with st.spinner("Analyzing DST Bench records..."):
                        ans_res = dst_ai_assistant.answer_question(active_chat_query_dst)
                        ans_md = ans_res["response"]
                        st.markdown(ans_md)
                        st.session_state.dst_ai_chat_history.append({"role": "assistant", "content": ans_md})

