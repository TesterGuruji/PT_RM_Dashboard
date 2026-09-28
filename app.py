import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime
from dotenv import load_dotenv
from ai_assistant import PipelineAIAssistant, DSTBenchAIAssistant, SoonToBenchAIAssistant, SkillsetMatrixAIAssistant
from ai_assistant.soon_to_bench_assistant import RELEASE_WINDOWS, add_release_columns
from ai_assistant.skillset_assistant import SKILL_COLUMNS, skill_level_counts, tool_resource_matrix, split_skill_cell
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
    },
    "DST Soon To Bench Resources": {
        "path": "DST_SoonTobench.csv",
        "description": "Track resources whose engagements are ending, release dates, and who is due to join the bench next.",
        "cols": ["GPN", "Name", "Eng ID", "Eng Name", "Sector", "Start Date", "End Date", "Level", "Status", "Comments", "Location", "Counsellor Name"]
    },
    "Resource Skillset Matrix": {
        "path": "Skillset_Matrix.csv",
        "description": "Track certifications, performance test, observability and AI tool skills held by each resource.",
        "cols": ["GPN", "Resource Name", "Resource Level", "Certifications", "Performance Test Tools",
                 "Observability Tools", "AI Tools", "Others", "Location"]
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

def restore_blank_cells(df, file_path, strip_headers=False):
    """Reverts display-only 'Unassigned' fills back to blanks for cells that were empty in the source CSV.
    strip_headers matches CSVs whose header names carry stray spaces (the caller has already stripped df's)."""
    if not os.path.exists(file_path):
        return df
    original = pd.read_csv(file_path)
    if strip_headers:
        original.columns = original.columns.str.strip()
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


def skill_level_chart(df, skill_col, level_col="Resource Level", noun="Resources"):
    """Stacked bar: one bar per individual skill/tool/certification, stacked by resource level.
    Each skill cell holds a comma-separated list, exploded via skill_level_counts."""
    counts = skill_level_counts(df, skill_col, level_col)
    if counts.empty:
        return None
    colors = level_color_map(counts[level_col])
    skill_order = counts.groupby(skill_col)["Resources"].sum().sort_values(ascending=False).index.tolist()
    fig = go.Figure()
    for level, color in colors.items():
        level_counts = counts[counts[level_col] == level]
        if level_counts.empty:
            continue
        fig.add_bar(
            x=level_counts[skill_col], y=level_counts["Resources"], name=level,
            marker=dict(color=color, line=dict(color="#FFFFFF", width=2)),
            hovertemplate=f"<b>%{{x}}</b><br>{level}: %{{y}} {noun.lower()}<extra></extra>",
        )
    style_figure(fig, height=300)
    fig.update_layout(barmode="stack", legend_traceorder="normal")
    fig.update_xaxes(categoryorder="array", categoryarray=skill_order, tickangle=-20)
    fig.update_yaxes(dtick=1, rangemode="tozero")
    return fig


def ai_tool_heatmap_chart(df, tool_col="AI Tools", name_col="Resource Name"):
    """Heatmap grid: AI tool name x resource name, highlighting which resource has which tool."""
    matrix = tool_resource_matrix(df, tool_col, name_col)
    if matrix.empty:
        return None
    fig = go.Figure(go.Heatmap(
        z=matrix.values,
        x=list(matrix.columns),
        y=list(matrix.index),
        colorscale=[[0, "#EBEEF3"], [1, CATEGORICAL_COLORS[0]]],
        zmin=0, zmax=1,
        showscale=False,
        xgap=3, ygap=3,
        hovertemplate="<b>%{y}</b> · %{x}: %{z}<extra></extra>",
    ))
    style_figure(fig, height=max(220, 46 * len(matrix.index) + 60))
    fig.update_xaxes(showgrid=False, linecolor="rgba(0,0,0,0)", side="bottom", tickangle=-20)
    fig.update_yaxes(showgrid=False, linecolor="rgba(0,0,0,0)", autorange="reversed")
    fig.update_layout(margin=dict(l=4, r=16, t=8, b=8))
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


# Soon To Bench: release-window urgency uses the reserved status colours (always shown with a text label)
RELEASE_WINDOW_COLORS = {"Overdue": STATUS_COLORS["critical"], "Next 30 days": STATUS_COLORS["serious"],
                         "31–60 days": STATUS_COLORS["warning"], "60+ days": STATUS_COLORS["good"], "No end date": OTHER_COLOR}
SOON_STATUS_COLORS = {"In Progress": CATEGORICAL_COLORS[0], "Completed": CATEGORICAL_COLORS[2]}


def release_alert_chart(df):
    """Days from today to each resource's End Date (negative = overdue), most urgent first, coloured by release window."""
    alert = df[df["Days To Release"].notna()].sort_values("Days To Release")
    if alert.empty:
        return None
    alert = alert.assign(label=alert["Name"].astype(str) + "  ·  " + alert["GPN"].astype(str),
                         end=pd.to_datetime(alert["End Date"], errors="coerce").dt.strftime("%d %b %Y"))
    fig = go.Figure()
    for window in RELEASE_WINDOWS:
        part = alert[alert["Release Window"] == window]
        if part.empty:
            continue
        days = part["Days To Release"].astype(int)
        text = [(f"{-d} day{'s' if d != -1 else ''} overdue" if d < 0 else f"in {d} day{'s' if d != 1 else ''}") for d in days]
        fig.add_bar(
            x=days, y=part["label"], orientation="h", name=window,
            marker=dict(color=RELEASE_WINDOW_COLORS[window], line=dict(width=0)),
            text=[f"{t}  ·  {e}" for t, e in zip(text, part["end"])], textposition="outside", cliponaxis=False,
            textfont=dict(color="#33415C", size=12),
            customdata=part["end"], hovertemplate="<b>%{y}</b><br>End date: %{customdata}<br>Days to release: %{x}<extra>" + window + "</extra>",
        )
    style_figure(fig, height=max(220, 48 * len(alert) + 80))
    # A minimum 30-day span keeps one-day values from filling the plot and yields whole-day ticks
    span = max(abs(alert["Days To Release"].min()), abs(alert["Days To Release"].max()), 30)
    fig.update_yaxes(categoryorder="array", categoryarray=list(alert["label"]), autorange="reversed",
                     gridcolor="rgba(0,0,0,0)", tickfont=dict(color="#33415C", size=12))
    fig.update_xaxes(zeroline=False, showgrid=True, gridcolor="#EBEEF3", ticksuffix="d",
                     # Outside labels need room on both sides: overdue labels extend left of their bars
                     range=[min(0, alert["Days To Release"].min()) - span * (1.5 if alert["Days To Release"].min() < 0 else 0.1),
                            max(0, alert["Days To Release"].max()) + span * 0.9])
    fig.add_vline(x=0, line_width=1, line_color="#33415C")
    fig.add_annotation(x=0, y=1.02, yref="paper", text="Today", showarrow=False, font=dict(size=11, color="#33415C"), yanchor="bottom")
    fig.update_xaxes(tickformat="d")
    fig.update_layout(bargap=0.4, barmode="overlay", legend_traceorder="normal", margin=dict(t=28), showlegend=True)
    return fig


def level_window_chart(df):
    """Soon-to-bench count per resource level (seniority order), stacked by release window."""
    plot_df = df[df["Level"].astype(str).str.strip() != "Unassigned"].copy()
    if plot_df.empty:
        return None
    plot_df["Level"] = plot_df["Level"].astype(str).str.strip()
    levels = list(level_color_map(plot_df["Level"]).keys())
    counts = plot_df.groupby(["Level", "Release Window"]).size().reset_index(name="Resources")
    fig = go.Figure()
    for window in RELEASE_WINDOWS:
        part = counts[counts["Release Window"] == window]
        if part.empty:
            continue
        fig.add_bar(
            x=part["Level"], y=part["Resources"], name=window,
            marker=dict(color=RELEASE_WINDOW_COLORS[window], line=dict(color="#FFFFFF", width=2)),
            hovertemplate="<b>%{x}</b><br>" + window + ": %{y} resource(s)<extra></extra>",
        )
    style_figure(fig, height=300)
    # Legend stays visible even for one window: colour alone must never carry the urgency meaning
    fig.update_layout(barmode="stack", legend_traceorder="normal", showlegend=True, bargap=0.45 if len(levels) > 2 else 0.7)
    fig.update_xaxes(categoryorder="array", categoryarray=levels)
    fig.update_yaxes(dtick=1, rangemode="tozero")
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
# SHARED RECORDS-TAB SAVE LOGIC & AI ASSISTANT TAB (used by all three modules)
# -----------------------------------------------------------------------------
def save_editor_changes(raw_df, display_df, editor_state, file_path, expected_cols, loaded_mtime, strip_headers=False):
    """Applies data_editor edits/deletions/additions on top of raw_df and writes the result back to file_path.
    Returns False without writing if the file changed on disk since it was loaded (another user/process saved
    in the meantime), so a late save here can't silently clobber those changes."""
    if loaded_mtime is not None and os.path.exists(file_path) and os.path.getmtime(file_path) != loaded_mtime:
        st.error(
            "This file was changed elsewhere since you loaded it. Refresh the page and redo your edits before saving.",
            icon=":material/error:"
        )
        return False

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
        explicit_deletes.extend(display_df.index[i] for i in deleted_indices)
    if explicit_deletes:
        raw_df = raw_df.drop(index=list(set(explicit_deletes)))

    # Undo display-only 'Unassigned' fills before additions reset the index
    raw_df = restore_blank_cells(raw_df, file_path, strip_headers=strip_headers)

    # 3. Additions
    added_rows = editor_state.get("added_rows", [])
    if added_rows:
        new_df = pd.DataFrame(added_rows).drop(columns=['🗑️ Delete Row'], errors='ignore')
        for c in raw_df.columns:
            if c not in new_df.columns:
                new_df[c] = None
        raw_df = pd.concat([raw_df, new_df[raw_df.columns]], ignore_index=True)

    # Save back to CSV
    df_to_save = restore_integer_columns(raw_df[[c for c in expected_cols if c in raw_df.columns]])
    df_to_save.to_csv(file_path, index=False)
    st.session_state["records_saved_toast"] = True
    load_data.clear()
    return True


def render_ai_assistant_tab(assistant_class, working_df, session_key, key_prefix, source_csv, title, subtitle, chat_placeholder, spinner_text):
    """Renders the chat UI shared by the Pipeline / DST Bench / Soon-To-Bench AI Assistant tabs."""
    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

    with st.container():
        st.markdown(f"""
        <div class="ai-head">
            <div>
                <div class="ai-tag">AI Assistant</div>
                <div class="card-title">{title}</div>
                <div class="card-subtitle">{subtitle}</div>
            </div>
            <span class="source-chip">Answers grounded in {source_csv}</span>
        </div>
        """, unsafe_allow_html=True)

        assistant = assistant_class(df=working_df)

        if session_key not in st.session_state:
            st.session_state[session_key] = []

        with st.expander("Suggested questions", icon=":material/lightbulb:", expanded=len(st.session_state[session_key]) == 0):
            suggested_list = assistant_class.get_suggested_questions()
            sugg_cols = st.columns(2)
            clicked_suggestion = None
            for s_idx, s_text in enumerate(suggested_list):
                with sugg_cols[s_idx % 2]:
                    if st.button(s_text, key=f"{key_prefix}_{s_idx}", width="stretch"):
                        clicked_suggestion = s_text

        if st.session_state[session_key]:
            c_clear_space, c_clear_btn = st.columns([5, 1])
            with c_clear_btn:
                if st.button("Clear chat", icon=":material/delete_sweep:", key=f"{key_prefix}_clear_btn", width="stretch"):
                    st.session_state[session_key] = []
                    st.rerun()

        for chat_msg in st.session_state[session_key]:
            with st.chat_message(chat_msg["role"]):
                st.markdown(chat_msg["content"])

        user_chat_query = st.chat_input(chat_placeholder, key=f"{key_prefix}_input")
        active_chat_query = clicked_suggestion or user_chat_query

        if active_chat_query:
            st.session_state[session_key].append({"role": "user", "content": active_chat_query})
            with st.chat_message("user"):
                st.markdown(active_chat_query)

            with st.chat_message("assistant"):
                with st.spinner(spinner_text):
                    ans_md = assistant.answer_question(active_chat_query)["response"]
                    st.markdown(ans_md)
                    st.session_state[session_key].append({"role": "assistant", "content": ans_md})


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
    loaded_mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else None
    raw_df = load_data(file_path, expected_cols, loaded_mtime)
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
                    if save_editor_changes(raw_df, display_df, editor_state, file_path, expected_cols, loaded_mtime):
                        st.rerun()
        else:
            st.markdown('<div class="empty-state"><b>No matching demands</b>Adjust or clear the search and filters above.</div>', unsafe_allow_html=True)

    with tab_ai:
        # -------------------------------------------------------------------------
        # PIPELINE DEMAND AI ASSISTANT
        # -------------------------------------------------------------------------
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

        render_ai_assistant_tab(
            assistant_class=PipelineAIAssistant,
            working_df=working_df,
            session_key="ai_chat_history",
            key_prefix="btn_sugg",
            source_csv="PipelineDemand_Details.csv",
            title="Pipeline Intelligence Assistant",
            subtitle="Ask about pipeline volume, fulfilment status, seniority mix and lead allocation.",
            chat_placeholder="Ask a question about pipeline demands",
            spinner_text="Analyzing Pipeline Demand records...",
        )


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
                display_df[col] = pd.to_numeric(display_df[col], errors='coerce').astype('Int64')
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
                    if save_editor_changes(raw_df, display_df, editor_state_dst, file_path, expected_cols, loaded_mtime):
                        st.rerun()
        else:
            st.markdown('<div class="empty-state"><b>No matching bench resources</b>Adjust or clear the search and filters above.</div>', unsafe_allow_html=True)

    with tab_ai:
        # -------------------------------------------------------------------------
        # DST BENCH AI ASSISTANT
        # -------------------------------------------------------------------------
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

        render_ai_assistant_tab(
            assistant_class=DSTBenchAIAssistant,
            working_df=working_df_dst,
            session_key="dst_ai_chat_history",
            key_prefix="btn_sugg_dst",
            source_csv="DST_Bench.csv",
            title="DST Bench Intelligence Assistant",
            subtitle="Ask about bench resources, bench aging, locations and counsellor alignment.",
            chat_placeholder="Ask a question about bench resources",
            spinner_text="Analyzing DST Bench records...",
        )


# =============================================================================
# MODULE 3: DST SOON TO BENCH RESOURCES
# =============================================================================
elif selection == "DST Soon To Bench Resources":
    # The source CSV's header names carry stray spaces (" End Date"); work with trimmed names
    raw_df.columns = raw_df.columns.str.strip()
    release_df = add_release_columns(raw_df)
    # KPIs and charts cover only in-flight engagements; COMPLETED rows stay visible in Records and to the AI assistant
    if 'Status' in release_df.columns:
        active_df = release_df[release_df['Status'].astype(str).str.strip().str.upper() == 'IN PROGRESS']
    else:
        active_df = release_df.iloc[0:0]

    # -------------------------------------------------------------------------
    # KPI STRIP (IN PROGRESS only)
    # -------------------------------------------------------------------------
    if not raw_df.empty:
        window_counts = active_df["Release Window"].value_counts()
        upcoming = active_df[active_df["Days To Release"] >= 0].sort_values("Days To Release")
        if not upcoming.empty:
            next_row = upcoming.iloc[0]
            next_end = pd.to_datetime(next_row["End Date"], errors="coerce").strftime("%d %b %Y")
            next_kpi = {"label": "Next release in", "value": int(next_row["Days To Release"]), "unit": "days",
                        "foot": f"{next_row['Name']} · {next_end}"}
        else:
            next_kpi = {"label": "Next release in", "value": "—", "foot": "No upcoming end dates"}

        render_kpis([
            {"label": "Soon to bench", "value": len(active_df), "foot": "Engagements in progress"},
            {"label": "Overdue", "value": int(window_counts.get("Overdue", 0)), "foot": "End date has passed",
             "dot": RELEASE_WINDOW_COLORS["Overdue"]},
            {"label": "Next 30 days", "value": int(window_counts.get("Next 30 days", 0)), "foot": "Releasing within 30 days",
             "dot": RELEASE_WINDOW_COLORS["Next 30 days"]},
            {"label": "31–60 days", "value": int(window_counts.get("31–60 days", 0)), "foot": "Releasing in 31–60 days",
             "dot": RELEASE_WINDOW_COLORS["31–60 days"]},
            next_kpi,
        ])

    tab_overview, tab_records, tab_ai = st.tabs([
        ":material/monitoring: Overview", ":material/table_rows: Records", ":material/auto_awesome: AI Assistant"
    ])

    # -------------------------------------------------------------------------
    # OVERVIEW: ANALYTICS (IN PROGRESS only)
    # -------------------------------------------------------------------------
    with tab_overview:
        if active_df.empty:
            st.markdown('<div class="empty-state"><b>No in-progress engagements</b>Only resources with status IN PROGRESS are charted here; '
                        'all records are listed in the Records tab.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="notice notice-neutral"><strong>In-progress engagements only:</strong> KPIs and charts cover '
                        f'<strong>{len(active_df)}</strong> of {len(raw_df)} records; completed engagements are excluded.</div>', unsafe_allow_html=True)

            # Data-quality check: an End Date earlier than the Start Date usually means a typo
            starts = pd.to_datetime(active_df["Start Date"], errors="coerce") if "Start Date" in active_df.columns else None
            bad_dates = active_df[pd.to_datetime(active_df["End Date"], errors="coerce") < starts] if starts is not None else active_df.iloc[0:0]
            if not bad_dates.empty:
                who = ", ".join(f"{r['Name']} ({r['GPN']})" for _, r in bad_dates.iterrows())
                st.markdown(f'<div class="notice notice-warning"><strong>Check dates:</strong> {len(bad_dates)} record(s) have an '
                            f'End Date before the Start Date — {who}. Correct them in the Records tab.</div>', unsafe_allow_html=True)

            chart_col1, chart_col2 = st.columns([1, 1.35], gap="medium")
            with chart_col1:
                with st.container(border=True, key="card-stb-status"):
                    # Every charted row is IN PROGRESS, so status is broken down by release urgency instead
                    card_heading("By release status", "In-progress engagements by time to End Date")
                    window_order = [w.title() for w in RELEASE_WINDOWS]
                    window_colors = {w.title(): c for w, c in RELEASE_WINDOW_COLORS.items()}
                    show_chart(status_breakdown_chart(active_df["Release Window"], window_order, window_colors, "Resources"))
            with chart_col2:
                with st.container(border=True, key="card-stb-level"):
                    card_heading("Soon to bench by level", "In-progress engagements, stacked by release window")
                    fig_level = level_window_chart(active_df) if 'Level' in active_df.columns else None
                    if fig_level is not None:
                        show_chart(fig_level)
                    else:
                        st.caption("No resource levels to chart.")

            with st.container(border=True, key="card-stb-alert"):
                card_heading("Release alerts by date", "Days until each in-progress engagement's End Date, most urgent first")
                fig_alert = release_alert_chart(active_df)
                if fig_alert is not None:
                    show_chart(fig_alert)
                else:
                    st.caption("No valid end dates to chart.")

    with tab_records:
        # -------------------------------------------------------------------------
        # ADVANCED FILTER TOOLBAR & DATA CONTROLS
        # -------------------------------------------------------------------------
        with st.container(border=True, key="card-filters-stb"):
            # Six filters don't fit one row legibly: search, status and level first, then the rest
            f_c1, f_c2, f_c3 = st.columns([2, 1, 1])
            f_c4, f_c5, f_c6 = st.columns(3)

            with f_c1:
                search_query_stb = st.text_input(
                    "Search",
                    placeholder="Search GPN, name, engagement, sector or location",
                    label_visibility="collapsed",
                    icon=":material/search:",
                    key="search_query_stb"
                )

            def filter_options(col, all_label):
                values = sorted({str(v).strip() for v in raw_df[col].dropna() if str(v).strip() != 'Unassigned'}) if col in raw_df.columns else []
                return [all_label] + values

            with f_c2:
                selected_status_stb = st.selectbox("Status Filter", filter_options('Status', "All Statuses"), label_visibility="collapsed", key="status_stb")
            with f_c3:
                selected_level_stb = st.selectbox("Level Filter", filter_options('Level', "All Levels"), label_visibility="collapsed", key="level_stb")
            with f_c4:
                window_options = ["All Release Windows"] + [w for w in RELEASE_WINDOWS if w in set(release_df["Release Window"])]
                selected_window_stb = st.selectbox("Release Window Filter", window_options, label_visibility="collapsed", key="window_stb")
            with f_c5:
                selected_location_stb = st.selectbox("Location Filter", filter_options('Location', "All Locations"), label_visibility="collapsed", key="loc_stb")
            with f_c6:
                selected_counsellor_stb = st.selectbox("Counsellor Filter", filter_options('Counsellor Name', "All Counsellors"), label_visibility="collapsed", key="counsellor_stb")

        # Apply Active Filters
        display_df = raw_df.copy()

        # Enforce explicit data types across schema
        for col in display_df.columns:
            if col in ['GPN', 'Eng ID']:
                display_df[col] = pd.to_numeric(display_df[col], errors='coerce').astype('Int64')
            elif 'Date' in col:
                display_df[col] = pd.to_datetime(display_df[col], errors='coerce').dt.date
            else:
                display_df[col] = display_df[col].astype(str).str.strip()

        # 1. Global Text Filter
        if search_query_stb and not display_df.empty:
            mask = display_df.apply(lambda row: row.astype(str).str.contains(search_query_stb, case=False, na=False, regex=False).any(), axis=1)
            display_df = display_df[mask]

        # 2. Column Filters
        for col, selected in [('Status', selected_status_stb), ('Level', selected_level_stb),
                              ('Location', selected_location_stb), ('Counsellor Name', selected_counsellor_stb)]:
            if not selected.startswith("All ") and col in display_df.columns:
                display_df = display_df[display_df[col].str.lower() == selected.lower()]

        # 3. Release Window Filter (computed from End Date)
        if selected_window_stb != "All Release Windows":
            display_df = display_df[release_df.loc[display_df.index, "Release Window"] == selected_window_stb]

        # Filter Status & Action Bar
        ctrl_left, ctrl_right = st.columns([2, 1.5], vertical_alignment="center")

        with ctrl_left:
            active_filters = [f for f in (selected_status_stb, selected_level_stb, selected_window_stb, selected_location_stb, selected_counsellor_stb)
                              if not f.startswith("All ")]
            if search_query_stb:
                active_filters.insert(0, f'"{search_query_stb}"')
            filter_note = f'<span class="filter-note">Filtered by {", ".join(active_filters)}</span>' if active_filters else ""
            st.markdown(f'<span class="result-pill">{len(display_df)} of {len(raw_df)} soon-to-bench resources</span>{filter_note}', unsafe_allow_html=True)

        with ctrl_right:
            btn_col1, btn_col2 = st.columns([1, 1])
            with btn_col1:
                edit_mode_stb = st.toggle("Edit mode", value=False, help="Edit cells inline, add rows at the bottom, or mark rows for deletion", key="edit_mode_stb")
            with btn_col2:
                if not display_df.empty:
                    export_df = display_df.join(release_df[["Days To Release", "Release Window"]])
                    st.download_button(
                        label="Export CSV",
                        icon=":material/download:",
                        data=export_df.to_csv(index=False).encode('utf-8'),
                        file_name=f"dst_soon_to_bench_export_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        width="stretch",
                        key="export_stb_btn"
                    )

        # -------------------------------------------------------------------------
        # MAIN DATA TABLE & EDITOR
        # -------------------------------------------------------------------------
        if edit_mode_stb:
            st.markdown(
                '<div class="notice notice-warning"><strong>Edit mode is on.</strong> Double-click a cell to change it, '
                'add rows at the bottom of the table, or tick <em>Delete Row</em> to remove a record. '
                'Changes are written to the source file only when you select <strong>Save changes</strong>.</div>',
                unsafe_allow_html=True)

        if not display_df.empty or raw_df.empty:
            editor_key_stb = f"editor_{selection}"

            def with_existing(defaults, col):
                existing = [str(v).strip() for v in raw_df[col].dropna().unique()] if col in raw_df.columns else []
                return list(dict.fromkeys(defaults + [v for v in existing if v != 'Unassigned']))

            col_config_stb = {}
            for col in display_df.columns:
                if col in ['GPN', 'Eng ID']:
                    col_config_stb[col] = st.column_config.NumberColumn(col, format="%d", min_value=0, step=1)
                elif 'Date' in col:
                    col_config_stb[col] = st.column_config.DateColumn(col, format="MM/DD/YYYY")
                elif col == 'Status':
                    col_config_stb[col] = st.column_config.SelectboxColumn(
                        col, help="Engagement status", options=with_existing(["IN PROGRESS", "COMPLETED"], col), required=True
                    ) if edit_mode_stb else st.column_config.TextColumn(col)
                elif col == 'Level' and edit_mode_stb:
                    col_config_stb[col] = st.column_config.SelectboxColumn(
                        col, help="Seniority Level",
                        options=with_existing(["Staff 1", "Staff 2", "Senior 1", "Senior 2", "Senior 3", "Manager", "Senior Manager", "Associate Director", "Director"], col)
                    )
                elif col == 'Location' and edit_mode_stb:
                    col_config_stb[col] = st.column_config.SelectboxColumn(
                        col, help="Office Location",
                        options=with_existing(["Noida", "Bengaluru", "Pune", "Gurugram", "Hyderabad", "Chennai", "Kolkata", "Kochi", "Trivandrum", "Coimbatore"], col)
                    )
                else:
                    col_config_stb[col] = st.column_config.TextColumn(col)

            if edit_mode_stb:
                if not display_df.empty and '🗑️ Delete Row' not in display_df.columns:
                    display_df.insert(0, '🗑️ Delete Row', False)
                st.data_editor(
                    display_df,
                    width="stretch",
                    height=380,
                    num_rows="dynamic",
                    hide_index=True,
                    key=editor_key_stb,
                    column_config=col_config_stb
                )
            else:
                # Read mode shows the computed release columns next to End Date
                view_df = display_df.copy()
                insert_at = view_df.columns.get_loc("End Date") + 1 if "End Date" in view_df.columns else len(view_df.columns)
                view_df.insert(insert_at, "Days To Release", release_df.loc[view_df.index, "Days To Release"].astype("Int64"))
                view_df.insert(insert_at + 1, "Release Window", release_df.loc[view_df.index, "Release Window"])
                col_config_stb["Days To Release"] = st.column_config.NumberColumn("Days To Release", format="%d", help="Days from today to End Date; negative means overdue")

                def soon_row_style(row):
                    styles = status_cell_style(SOON_STATUS_COLORS)(row)
                    color = RELEASE_WINDOW_COLORS.get(row.get("Release Window"))
                    if color:
                        styles[row.index.get_loc("Release Window")] = f"color: #0F1B2D; font-weight: 600; background-color: {color}22;"
                    return styles

                st.dataframe(
                    view_df.style.apply(soon_row_style, axis=1),
                    width="stretch",
                    height=380,
                    hide_index=True,
                    column_config=col_config_stb
                )

            # Edit State Handling & Save Serialization
            editor_state_stb = st.session_state.get(editor_key_stb, {})
            has_changes_stb = edit_mode_stb and any(len(v) > 0 for v in editor_state_stb.values() if isinstance(v, (dict, list)))

            if has_changes_stb:
                st.warning("You have unsaved changes in the table above.", icon=":material/edit_note:")
                if st.button("Save changes", icon=":material/save:", width="stretch", type="primary", key="save_stb_btn"):
                    if save_editor_changes(raw_df, display_df, editor_state_stb, file_path, expected_cols, loaded_mtime, strip_headers=True):
                        st.rerun()
        else:
            st.markdown('<div class="empty-state"><b>No matching soon-to-bench resources</b>Adjust or clear the search and filters above.</div>', unsafe_allow_html=True)

    with tab_ai:
        # -------------------------------------------------------------------------
        # DST SOON TO BENCH AI ASSISTANT
        # -------------------------------------------------------------------------
        # Contextual data detection
        is_filtered_stb = (search_query_stb != "" or any(not f.startswith("All ") for f in (
            selected_status_stb, selected_level_stb, selected_window_stb, selected_location_stb, selected_counsellor_stb))) and not display_df.empty

        if is_filtered_stb:
            st.markdown(f"""
            <div class="notice notice-info">
                <strong>Filtered view:</strong> answers use only the current filter selection (<strong>{len(display_df)}</strong> matching soon-to-bench resources).
            </div>
            """, unsafe_allow_html=True)
            working_df_stb = raw_df.loc[display_df.index]
        else:
            st.markdown(f"""
            <div class="notice notice-neutral">
                <strong>Full dataset:</strong> answers cover all <strong>{len(raw_df)}</strong> soon-to-bench records.
            </div>
            """, unsafe_allow_html=True)
            working_df_stb = raw_df.copy()

        render_ai_assistant_tab(
            assistant_class=SoonToBenchAIAssistant,
            working_df=working_df_stb,
            session_key="stb_ai_chat_history",
            key_prefix="btn_sugg_stb",
            source_csv="DST_SoonTobench.csv",
            title="Soon To Bench Intelligence Assistant",
            subtitle="Ask about upcoming releases, overdue end dates, levels, locations and counsellors.",
            chat_placeholder="Ask a question about soon-to-bench resources",
            spinner_text="Analyzing Soon To Bench records...",
        )


# =============================================================================
# MODULE 4: RESOURCE SKILLSET MATRIX
# =============================================================================
elif selection == "Resource Skillset Matrix":
    # The source CSV's header names may carry stray spaces; work with trimmed names
    raw_df.columns = raw_df.columns.str.strip()

    # -------------------------------------------------------------------------
    # KPI STRIP
    # -------------------------------------------------------------------------
    if not raw_df.empty:
        def _distinct_skill_count(col):
            if col not in raw_df.columns:
                return 0
            return len({s for cell in raw_df[col] for s in split_skill_cell(cell)})

        render_kpis([
            {"label": "Resources tracked", "value": len(raw_df), "foot": "In the skillset matrix"},
            {"label": "Certifications", "value": _distinct_skill_count("Certifications"), "foot": "Distinct certifications held"},
            {"label": "Performance test tools", "value": _distinct_skill_count("Performance Test Tools"), "foot": "Distinct tools held"},
            {"label": "Observability tools", "value": _distinct_skill_count("Observability Tools"), "foot": "Distinct tools held"},
            {"label": "AI tools", "value": _distinct_skill_count("AI Tools"), "foot": "Distinct tools held"},
        ])

    tab_overview, tab_records, tab_ai = st.tabs([
        ":material/monitoring: Overview", ":material/table_rows: Records", ":material/auto_awesome: AI Assistant"
    ])

    # -------------------------------------------------------------------------
    # OVERVIEW: ANALYTICS
    # -------------------------------------------------------------------------
    with tab_overview:
        if raw_df.empty:
            st.markdown('<div class="empty-state"><b>No skillset records yet</b>Add records in the Records tab.</div>', unsafe_allow_html=True)
        else:
            chart_col1, chart_col2 = st.columns(2, gap="medium")
            with chart_col1:
                with st.container(border=True, key="card-skill-certs"):
                    card_heading("Certifications by level", "Resources per certification, stacked by resource level")
                    fig_certs = skill_level_chart(raw_df, "Certifications")
                    if fig_certs is not None:
                        show_chart(fig_certs)
                    else:
                        st.caption("No certification data to chart.")
            with chart_col2:
                with st.container(border=True, key="card-skill-pt"):
                    card_heading("Performance test tools by level", "Resources per tool, stacked by resource level")
                    fig_pt = skill_level_chart(raw_df, "Performance Test Tools")
                    if fig_pt is not None:
                        show_chart(fig_pt)
                    else:
                        st.caption("No performance test tool data to chart.")

            chart_col3, chart_col4 = st.columns(2, gap="medium")
            with chart_col3:
                with st.container(border=True, key="card-skill-obs"):
                    card_heading("Observability tools by level", "Resources per tool, stacked by resource level")
                    fig_obs = skill_level_chart(raw_df, "Observability Tools")
                    if fig_obs is not None:
                        show_chart(fig_obs)
                    else:
                        st.caption("No observability tool data to chart.")
            with chart_col4:
                with st.container(border=True, key="card-skill-ai"):
                    card_heading("AI tools by level", "Resources per tool, stacked by resource level")
                    fig_ai = skill_level_chart(raw_df, "AI Tools")
                    if fig_ai is not None:
                        show_chart(fig_ai)
                    else:
                        st.caption("No AI tool data to chart.")

            with st.container(border=True, key="card-skill-heatmap"):
                card_heading("Trending AI tool adoption", "Which resource has which AI tool")
                fig_heatmap = ai_tool_heatmap_chart(raw_df)
                if fig_heatmap is not None:
                    show_chart(fig_heatmap)
                else:
                    st.caption("No AI tool data to chart.")

    with tab_records:
        # -------------------------------------------------------------------------
        # ADVANCED FILTER TOOLBAR & DATA CONTROLS
        # -------------------------------------------------------------------------
        with st.container(border=True, key="card-filters-skill"):
            f_c1, f_c2, f_c3 = st.columns([2, 1, 1])

            with f_c1:
                search_query_skill = st.text_input(
                    "Search",
                    placeholder="Search name, level, certification, tool or location",
                    label_visibility="collapsed",
                    icon=":material/search:",
                    key="search_query_skill"
                )

            with f_c2:
                level_options_skill = ["All Levels"]
                if 'Resource Level' in raw_df.columns:
                    unique_levels_skill = sorted([l for l in raw_df['Resource Level'].dropna().unique() if l != 'Unassigned'])
                    level_options_skill.extend(unique_levels_skill)
                selected_level_skill = st.selectbox("Resource Level Filter", level_options_skill, label_visibility="collapsed", key="level_skill")

            with f_c3:
                location_options_skill = ["All Locations"]
                if 'Location' in raw_df.columns:
                    unique_locations_skill = sorted([loc for loc in raw_df['Location'].dropna().unique() if loc != 'Unassigned'])
                    location_options_skill.extend(unique_locations_skill)
                selected_location_skill = st.selectbox("Location Filter", location_options_skill, label_visibility="collapsed", key="loc_skill")

        # Apply Active Filters
        display_df = raw_df.copy()

        # Enforce explicit data types across schema
        for col in display_df.columns:
            if col == 'GPN':
                display_df[col] = pd.to_numeric(display_df[col], errors='coerce').astype('Int64')
            else:
                display_df[col] = display_df[col].astype(str).str.strip()

        # 1. Global Text Filter
        if search_query_skill and not display_df.empty:
            mask = display_df.apply(lambda row: row.astype(str).str.contains(search_query_skill, case=False, na=False, regex=False).any(), axis=1)
            display_df = display_df[mask]

        # 2. Resource Level Filter
        if selected_level_skill != "All Levels" and 'Resource Level' in display_df.columns:
            display_df = display_df[display_df['Resource Level'].astype(str).str.strip() == selected_level_skill.strip()]

        # 3. Location Filter
        if selected_location_skill != "All Locations" and 'Location' in display_df.columns:
            display_df = display_df[display_df['Location'].astype(str).str.strip().str.lower() == selected_location_skill.strip().lower()]

        # Filter Status & Action Bar
        ctrl_left, ctrl_right = st.columns([2, 1.5], vertical_alignment="center")

        with ctrl_left:
            active_filters = [f for f in (selected_level_skill, selected_location_skill) if not f.startswith("All ")]
            if search_query_skill:
                active_filters.insert(0, f'"{search_query_skill}"')
            filter_note = f'<span class="filter-note">Filtered by {", ".join(active_filters)}</span>' if active_filters else ""
            st.markdown(f'<span class="result-pill">{len(display_df)} of {len(raw_df)} resources</span>{filter_note}', unsafe_allow_html=True)

        with ctrl_right:
            btn_col1, btn_col2 = st.columns([1, 1])
            with btn_col1:
                edit_mode_skill = st.toggle("Edit mode", value=False, help="Edit cells inline, add rows at the bottom, or mark rows for deletion", key="edit_mode_skill")
            with btn_col2:
                if not display_df.empty:
                    export_df = display_df.drop(columns=['🗑️ Delete Row'], errors='ignore')
                    st.download_button(
                        label="Export CSV",
                        icon=":material/download:",
                        data=export_df.to_csv(index=False).encode('utf-8'),
                        file_name=f"skillset_matrix_export_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        width="stretch",
                        key="export_skill_btn"
                    )

        # -------------------------------------------------------------------------
        # MAIN DATA TABLE & EDITOR
        # -------------------------------------------------------------------------
        if edit_mode_skill:
            st.markdown(
                '<div class="notice notice-warning"><strong>Edit mode is on.</strong> Double-click a cell to change it, '
                'add rows at the bottom of the table, or tick <em>Delete Row</em> to remove a record. Skill columns take '
                'a comma-separated list (e.g. "JMeter, LoadRunner"). Changes are written to the source file only when you '
                'select <strong>Save changes</strong>.</div>',
                unsafe_allow_html=True)

        if not display_df.empty or raw_df.empty:
            editor_key_skill = f"editor_{selection}"

            col_config_skill = {}
            for col in display_df.columns:
                if col == 'GPN':
                    col_config_skill[col] = st.column_config.NumberColumn(col, format="%d", min_value=0, step=1)
                elif col == 'Resource Level' and edit_mode_skill:
                    col_config_skill[col] = st.column_config.SelectboxColumn(
                        col, help="Seniority Level",
                        options=["Staff 1", "Staff 2", "Senior 1", "Senior 2", "Senior 3", "Manager", "Senior Manager", "Associate Director", "Director"]
                    )
                elif col == 'Location' and edit_mode_skill:
                    col_config_skill[col] = st.column_config.SelectboxColumn(
                        col, help="Office Location",
                        options=["Noida", "Bengaluru", "Pune", "Gurugram", "Hyderabad", "Chennai", "Kolkata", "Kochi", "Trivandrum", "Coimbatore"]
                    )
                elif col in SKILL_COLUMNS:
                    col_config_skill[col] = st.column_config.TextColumn(col, help='Comma-separated list, e.g. "JMeter, LoadRunner"')
                elif col != '🗑️ Delete Row':
                    col_config_skill[col] = st.column_config.TextColumn(col)

            if edit_mode_skill:
                if not display_df.empty and '🗑️ Delete Row' not in display_df.columns:
                    display_df.insert(0, '🗑️ Delete Row', False)
                st.data_editor(
                    display_df,
                    width="stretch",
                    height=380,
                    num_rows="dynamic",
                    hide_index=True,
                    key=editor_key_skill,
                    column_config=col_config_skill
                )
            else:
                st.dataframe(
                    display_df,
                    width="stretch",
                    height=380,
                    hide_index=True,
                    column_config=col_config_skill
                )

            # Edit State Handling & Save Serialization
            editor_state_skill = st.session_state.get(editor_key_skill, {})
            has_changes_skill = edit_mode_skill and any(len(v) > 0 for v in editor_state_skill.values() if isinstance(v, (dict, list)))

            if has_changes_skill:
                st.warning("You have unsaved changes in the table above.", icon=":material/edit_note:")
                if st.button("Save changes", icon=":material/save:", width="stretch", type="primary", key="save_skill_btn"):
                    if save_editor_changes(raw_df, display_df, editor_state_skill, file_path, expected_cols, loaded_mtime, strip_headers=True):
                        st.rerun()
        else:
            st.markdown('<div class="empty-state"><b>No matching resources</b>Adjust or clear the search and filters above.</div>', unsafe_allow_html=True)

    with tab_ai:
        # -------------------------------------------------------------------------
        # SKILLSET MATRIX AI ASSISTANT
        # -------------------------------------------------------------------------
        # Contextual data detection
        is_filtered_skill = (search_query_skill != "" or selected_level_skill != "All Levels" or selected_location_skill != "All Locations") and not display_df.empty

        if is_filtered_skill:
            st.markdown(f"""
            <div class="notice notice-info">
                <strong>Filtered view:</strong> answers use only the current filter selection (<strong>{len(display_df)}</strong> matching resources).
            </div>
            """, unsafe_allow_html=True)
            working_df_skill = raw_df.loc[display_df.index]
        else:
            st.markdown(f"""
            <div class="notice notice-neutral">
                <strong>Full dataset:</strong> answers cover all <strong>{len(raw_df)}</strong> skillset matrix records.
            </div>
            """, unsafe_allow_html=True)
            working_df_skill = raw_df.copy()

        render_ai_assistant_tab(
            assistant_class=SkillsetMatrixAIAssistant,
            working_df=working_df_skill,
            session_key="skill_ai_chat_history",
            key_prefix="btn_sugg_skill",
            source_csv="Skillset_Matrix.csv",
            title="Skillset Matrix Intelligence Assistant",
            subtitle="Ask about certifications, tools, resource levels and locations — grounded strictly in Skillset_Matrix.csv.",
            chat_placeholder="Ask a question about the skillset matrix",
            spinner_text="Analyzing Skillset Matrix records...",
        )
