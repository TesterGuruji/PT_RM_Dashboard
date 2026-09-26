import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime
from dotenv import load_dotenv
from ai_assistant import PipelineAIAssistant, DSTBenchAIAssistant

load_dotenv()

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION & ENTERPRISE DESIGN SYSTEM
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Performance Test Resourcing | Enterprise Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Enterprise CSS Design System (Power BI / ServiceNow / Datadog Aesthetic)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');

    :root {
        --primary-navy: #0F172A;
        --primary-slate: #1E293B;
        --brand-blue: #2563EB;
        --brand-blue-hover: #1D4ED8;
        --brand-blue-subtle: #EFF6FF;
        --brand-cyan: #0EA5E9;
        --surface-card: #FFFFFF;
        --surface-bg: #F8FAFC;
        --border-subtle: #E2E8F0;
        --border-medium: #CBD5E1;
        --text-primary: #0F172A;
        --text-secondary: #475569;
        --text-muted: #94A3B8;
        --success-bg: #ECFDF5;
        --success-text: #059669;
        --success-border: #A7F3D0;
        --warning-bg: #FFFBEB;
        --warning-text: #D97706;
        --warning-border: #FDE68A;
        --danger-bg: #FEF2F2;
        --danger-text: #DC2626;
        --danger-border: #FECACA;
        --info-bg: #EFF6FF;
        --info-text: #2563EB;
        --info-border: #BFDBFE;
    }

    /* Global Typography & Background */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        color: var(--text-primary);
        background-color: var(--surface-bg);
    }

    .main .block-container {
        padding-top: 1.25rem;
        padding-bottom: 2.5rem;
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 100%;
    }

    /* Professional Header Section */
    .dashboard-header-container {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding-bottom: 1rem;
        margin-bottom: 1.25rem;
        border-bottom: 1px solid var(--border-subtle);
    }
    .dashboard-eyebrow {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--brand-blue);
        margin-bottom: 0.25rem;
    }
    .dashboard-title {
        font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
        font-size: 1.65rem;
        font-weight: 700;
        color: var(--primary-navy);
        line-height: 1.2;
        margin: 0;
    }
    .dashboard-subtitle {
        font-size: 0.875rem;
        color: var(--text-secondary);
        margin-top: 0.25rem;
        margin-bottom: 0;
    }
    .meta-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.375rem;
        background: #FFFFFF;
        border: 1px solid var(--border-subtle);
        padding: 0.35rem 0.75rem;
        border-radius: 6px;
        font-size: 0.75rem;
        color: var(--text-secondary);
        font-weight: 500;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    }

    /* Enterprise KPI Metric Cards */
    .kpi-card {
        background: var(--surface-card);
        border: 1px solid var(--border-subtle);
        border-radius: 8px;
        padding: 1rem 1.15rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
        position: relative;
        overflow: hidden;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
        border-color: var(--border-medium);
    }
    .kpi-card::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: var(--card-accent, var(--brand-blue));
    }
    .kpi-label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-secondary);
        margin-bottom: 0.35rem;
    }
    .kpi-value {
        font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
        font-size: 1.85rem;
        font-weight: 700;
        color: var(--primary-navy);
        line-height: 1.1;
        margin-bottom: 0.35rem;
    }
    .kpi-subtext {
        font-size: 0.75rem;
        color: var(--text-muted);
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }
    .kpi-badge {
        display: inline-block;
        padding: 0.15rem 0.4rem;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 600;
    }

    /* Section Card Containers */
    .content-card {
        background: var(--surface-card);
        border: 1px solid var(--border-subtle);
        border-radius: 8px;
        padding: 1.25rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    .card-header-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #F1F5F9;
    }
    .card-title {
        font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
        font-size: 1rem;
        font-weight: 600;
        color: var(--primary-navy);
        margin: 0;
    }
    .card-subtitle {
        font-size: 0.75rem;
        color: var(--text-muted);
        margin: 0;
    }

    /* Status Badges */
    .badge-open {
        background-color: var(--info-bg);
        color: var(--info-text);
        border: 1px solid var(--info-border);
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.75rem;
    }
    .badge-awaiting {
        background-color: var(--warning-bg);
        color: var(--warning-text);
        border: 1px solid var(--warning-border);
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.75rem;
    }
    .badge-invalid {
        background-color: var(--danger-bg);
        color: var(--danger-text);
        border: 1px solid var(--danger-border);
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.75rem;
    }
    .badge-fulfilled {
        background-color: var(--success-bg);
        color: var(--success-text);
        border: 1px solid var(--success-border);
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.75rem;
    }

    /* Filter Toolbar Styling */
    .filter-toolbar {
        background: #FFFFFF;
        border: 1px solid var(--border-subtle);
        border-radius: 8px;
        padding: 1rem 1.25rem 0.75rem 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .filter-meta-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-top: 0.5rem;
        margin-top: 0.5rem;
        border-top: 1px solid #F1F5F9;
        font-size: 0.8rem;
        color: var(--text-secondary);
    }
    .results-count-pill {
        display: inline-flex;
        align-items: center;
        background: var(--brand-blue-subtle);
        color: var(--brand-blue);
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.75rem;
    }

    /* AI Assistant Card Styling */
    .ai-assistant-card {
        background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
        border: 1px solid #CBD5E1;
        border-radius: 8px;
        padding: 1.25rem;
        margin-top: 1.5rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
        position: relative;
    }
    .ai-badge {
        background: #1E293B;
        color: #FFFFFF;
        font-size: 0.7rem;
        font-weight: 700;
        padding: 0.2rem 0.55rem;
        border-radius: 4px;
        letter-spacing: 0.04em;
    }
    .ai-context-indicator {
        font-size: 0.75rem;
        color: var(--text-secondary);
        background: #F1F5F9;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        border: 1px solid var(--border-subtle);
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0F172A !important;
        color: #F8FAFC;
    }
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label {
        color: #E2E8F0 !important;
    }
    .sidebar-brand {
        padding: 0.5rem 0 1rem 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 1.25rem;
    }
    .sidebar-brand-title {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.05rem;
        font-weight: 700;
        color: #FFFFFF !important;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .sidebar-brand-subtitle {
        font-size: 0.7rem;
        color: #94A3B8 !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-top: 0.2rem;
    }
    .sidebar-section-header {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #64748B !important;
        font-weight: 700;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .sidebar-info-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 6px;
        padding: 0.75rem;
        margin-top: 1rem;
        font-size: 0.75rem;
        color: #94A3B8 !important;
    }

    /* Buttons & Controls */
    .stButton > button {
        border-radius: 6px;
        font-weight: 500;
        font-size: 0.825rem;
        transition: all 0.15s ease;
    }
    .stDownloadButton > button {
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.825rem;
    }
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
def load_data(file_path, expected_cols):
    """Loads dataset cleanly, populating missing values to prevent render crashes."""
    if not os.path.exists(file_path):
        return pd.DataFrame(columns=expected_cols)
    try:
        df = pd.read_csv(file_path)
        df = df.fillna('Unassigned') 
        return df
    except Exception as e:
        st.error(f"Failed to parse {file_path}: {e}")
        return pd.DataFrame(columns=expected_cols)

# -----------------------------------------------------------------------------
# SIDEBAR NAVIGATION & ENTERPRISE APP SHELL
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <div class="sidebar-brand-title">
            <span>⚡</span> Performance Resourcing
        </div>
        <div class="sidebar-brand-subtitle">Enterprise Resource Intelligence</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="sidebar-section-header">Trackers & Modules</div>', unsafe_allow_html=True)
    selection = st.radio(
        "Navigation", 
        list(FILES.keys()), 
        label_visibility="collapsed"
    )
    
    current_config = FILES[selection]
    file_path = current_config["path"]
    expected_cols = current_config["cols"]
    raw_df = load_data(file_path, expected_cols)
    
    st.markdown('<div class="sidebar-section-header">Data Source Operations</div>', unsafe_allow_html=True)
    
    if st.button("⟳ Refresh Data Cache", use_container_width=True):
        load_data.clear()
        st.session_state["cache_refreshed_toast"] = True
        st.rerun()
        
    if st.session_state.get("cache_refreshed_toast"):
        st.success("Data cache refreshed successfully.")
        st.session_state["cache_refreshed_toast"] = False

    st.markdown(f"""
    <div class="sidebar-info-card">
        <div style="font-weight:600; color:#F8FAFC; margin-bottom:4px;">Active Source</div>
        <div>📄 <code>{file_path}</code></div>
        <div style="margin-top:4px;">📊 <strong>{len(raw_df)}</strong> Total Records</div>
        <div style="margin-top:4px; font-size:0.7rem; color:#64748B;">Synced: {get_last_refresh_timestamp(file_path)}</div>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# MAIN DASHBOARD HEADER
# -----------------------------------------------------------------------------
refresh_time_str = get_last_refresh_timestamp(file_path)

c_header_left, c_header_right = st.columns([3, 1])

with c_header_left:
    st.markdown(f"""
    <div class="dashboard-eyebrow">Performance Test Resourcing</div>
    <h1 class="dashboard-title">{selection}</h1>
    <p class="dashboard-subtitle">{current_config['description']}</p>
    """, unsafe_allow_html=True)

with c_header_right:
    st.markdown(f"""
    <div style="text-align: right; padding-top: 0.5rem;">
        <span class="meta-badge">
            <span>🕒 Last synced:</span>
            <strong>{refresh_time_str}</strong>
        </span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)


# =============================================================================
# MODULE 1: PIPELINE DEMANDS (UNTOUCHED CORE LOGIC)
# =============================================================================
if selection == "Pipeline Demands":
    # -------------------------------------------------------------------------
    # DYNAMIC KPI INTELLIGENCE METRICS
    # -------------------------------------------------------------------------
    if not raw_df.empty and 'Status' in raw_df.columns:
        total_demands = len(raw_df)
        
        # Standardize status for accurate calculation
        status_series = raw_df['Status'].astype(str).str.strip().str.upper()
        
        open_count = int((status_series == 'OPEN').sum())
        awaiting_count = int((status_series == 'AWAITING CONFIRMATION').sum())
        invalid_count = int((status_series == 'INVALID').sum())
        fulfilled_count = int((status_series == 'FULFILLED').sum())
        
        open_pct = (open_count / total_demands * 100) if total_demands > 0 else 0
        
        # Check unassigned PT leads
        if 'Sector PT lead' in raw_df.columns:
            unassigned_leads = int((raw_df['Sector PT lead'].astype(str).str.strip().str.lower() == 'unassigned').sum())
        else:
            unassigned_leads = 0

        k1, k2, k3, k4, k5 = st.columns(5)

        with k1:
            st.markdown(f"""
            <div class="kpi-card" style="--card-accent: #0F172A;">
                <div class="kpi-label">Total Demands(FY-27)</div>
                <div class="kpi-value">{total_demands}</div>
                <div class="kpi-subtext">
                    <span>Active portfolio</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with k2:
            st.markdown(f"""
            <div class="kpi-card" style="--card-accent: #2563EB;">
                <div class="kpi-label">Open Demands</div>
                <div class="kpi-value" style="color:#2563EB;">{open_count}</div>
                <div class="kpi-subtext">
                    <span>Needs fulfillment</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with k3:
            st.markdown(f"""
            <div class="kpi-card" style="--card-accent: #F59E0B;">
                <div class="kpi-label">Awaiting Confirmation</div>
                <div class="kpi-value" style="color:#D97706;">{awaiting_count}</div>
                <div class="kpi-subtext">
                    <span>Lead validation</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with k4:
            st.markdown(f"""
            <div class="kpi-card" style="--card-accent: #EF4444;">
                <div class="kpi-label">Invalid</div>
                <div class="kpi-value" style="color:#DC2626;">{invalid_count}</div>
                <div class="kpi-subtext">
                    <span>Requires review</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with k5:
            st.markdown(f"""
            <div class="kpi-card" style="--card-accent: #64748B;">
                <div class="kpi-label">Unassigned Leads</div>
                <div class="kpi-value">{unassigned_leads}</div>
                <div class="kpi-subtext">
                    <span>Needs PT Lead</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height: 1.25rem;'></div>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # ENTERPRISE ANALYTICS VISUALIZATION SECTION
    # -------------------------------------------------------------------------
    if not raw_df.empty:
        chart_col1, chart_col2 = st.columns(2)
        
        # Chart 1: Demand Status Breakdown (Enterprise Donut Chart)
        with chart_col1:
            if 'Status' in raw_df.columns:
                plot_status_df = raw_df[raw_df['Status'] != 'Unassigned'].copy()
                plot_status_df['Clean_Status'] = plot_status_df['Status'].astype(str).str.strip().str.title()
                status_summary = plot_status_df['Clean_Status'].value_counts().reset_index()
                status_summary.columns = ['Status', 'Count']
                
                # Semantic Enterprise Color Mapping
                semantic_color_map = {
                    "Open": "#2563EB",
                    "Awaiting Confirmation": "#F59E0B",
                    "Invalid": "#EF4444",
                    "Fulfilled": "#10B981"
                }
                
                fig_status = px.pie(
                    status_summary,
                    names='Status',
                    values='Count',
                    hole=0.6,
                    color='Status',
                    color_discrete_map=semantic_color_map
                )
                
                fig_status.update_traces(
                    textposition='inside',
                    textinfo='percent',
                    hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>",
                    marker=dict(line=dict(color='#FFFFFF', width=2))
                )
                
                fig_status.update_layout(
                    title=dict(
                        text="<b>Demand Allocation by Status</b>",
                        font=dict(family="Plus Jakarta Sans, Inter", size=14, color="#0F172A")
                    ),
                    margin=dict(l=10, r=10, t=40, b=10),
                    height=360,
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.2,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=11)
                    ),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)"
                )
                
                st.plotly_chart(fig_status, use_container_width=True)

        # Chart 2: Month-wise Open Demand by Resource Level
        with chart_col2:
            if 'Start Date' in raw_df.columns and 'Resource Level' in raw_df.columns and 'Status' in raw_df.columns:
                plot_df = raw_df[
                    (raw_df['Start Date'] != 'Unassigned') & 
                    (raw_df['Resource Level'] != 'Unassigned') & 
                    (raw_df['Status'].astype(str).str.strip().str.upper() == 'OPEN')
                ].copy()
                plot_df['Start Date'] = pd.to_datetime(plot_df['Start Date'], errors='coerce')
                plot_df = plot_df.dropna(subset=['Start Date'])
                
                if not plot_df.empty:
                    plot_df['Month'] = plot_df['Start Date'].dt.strftime('%b %Y')
                    plot_df['Month_Sort'] = plot_df['Start Date'].dt.to_period('M')
                    
                    time_counts = plot_df.groupby(['Month', 'Month_Sort', 'Resource Level']).size().reset_index(name='Open Demands')
                    time_counts = time_counts.sort_values('Month_Sort')
                    
                    level_color_palette = ['#2563EB', '#0EA5E9', '#6366F1', '#8B5CF6', '#F59E0B', '#10B981']
                    
                    fig_level = px.bar(
                        time_counts,
                        x='Month',
                        y='Open Demands',
                        color='Resource Level',
                        barmode='group',
                        text='Open Demands',
                        color_discrete_sequence=level_color_palette
                    )
                    
                    fig_level.update_traces(
                        textposition='outside',
                        hovertemplate="<b>%{x}</b><br>Level: %{fullData.name}<br>Open Demands: %{y}<extra></extra>",
                        marker=dict(line=dict(color='#FFFFFF', width=1))
                    )
                    
                    chronological_months = list(dict.fromkeys(time_counts['Month'].tolist()))
                    
                    fig_level.update_layout(
                        title=dict(
                            text="<b>Month Wise Open Demand Count by Resource Level</b>",
                            font=dict(family="Plus Jakarta Sans, Inter", size=14, color="#0F172A")
                        ),
                        xaxis=dict(
                            title="",
                            categoryorder='array',
                            categoryarray=chronological_months,
                            showgrid=False
                        ),
                        yaxis=dict(
                            title="",
                            showgrid=True,
                            gridcolor="#F1F5F9",
                            dtick=1
                        ),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.25,
                            xanchor="center",
                            x=0.5,
                            title=dict(text=""),
                            font=dict(size=11)
                        ),
                        margin=dict(l=10, r=20, t=40, b=10),
                        height=360,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)"
                    )
                    
                    st.plotly_chart(fig_level, use_container_width=True)
                else:
                    st.info("No open demands found to chart by start month.")

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # ADVANCED FILTER TOOLBAR & DATA CONTROLS
    # -------------------------------------------------------------------------
    st.markdown("### 📋 Pipeline Demand Details")

    # Filter Controls Card
    with st.container():
        f_c1, f_c2, f_c3, f_c4 = st.columns([2, 1.2, 1.2, 1.2])
        
        with f_c1:
            search_query = st.text_input(
                "Global Search",
                placeholder="🔍 Search role, client, sector, or engineer...",
                label_visibility="collapsed",
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
        mask = display_df.apply(lambda row: row.astype(str).str.contains(search_query, case=False, na=False).any(), axis=1)
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
    ctrl_left, ctrl_right = st.columns([2, 1.5])

    with ctrl_left:
        total_recs = len(raw_df)
        shown_recs = len(display_df)
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:0.5rem; height: 100%; padding-top: 0.25rem;">
            <span class="results-count-pill">Showing {shown_recs} of {total_recs} demands</span>
            {f"<span style='font-size:0.75rem; color:#64748B;'>Filtered by: {selected_status if selected_status != 'All Statuses' else ''} {selected_level if selected_level != 'All Levels' else ''}</span>" if (selected_status != "All Statuses" or selected_level != "All Levels" or search_query) else ""}
        </div>
        """, unsafe_allow_html=True)

    with ctrl_right:
        btn_col1, btn_col2 = st.columns([1, 1])
        with btn_col1:
            edit_mode = st.toggle("✏️ Edit Mode", value=False, help="Enable inline cell editing and dynamic record updates", key="edit_mode_pipeline")
        with btn_col2:
            if not display_df.empty:
                export_df = display_df.drop(columns=['🗑️ Delete Row'], errors='ignore')
                csv_export = export_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Export CSV",
                    data=csv_export,
                    file_name=f"pipeline_demands_export_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="export_pipeline_btn"
                )

    # -------------------------------------------------------------------------
    # MAIN DATA TABLE & EDITOR
    # -------------------------------------------------------------------------
    if edit_mode:
        st.markdown("""
        <div style="background:#FFFBEB; border:1px solid #FDE68A; border-radius:6px; padding:0.6rem 0.9rem; font-size:0.8rem; color:#92400E; margin-bottom:0.75rem;">
            ⚠️ <strong>Edit Mode Active:</strong> Double-click any cell to modify values, add new rows at the bottom, or select <code>🗑️ Delete Row</code> to delete records. Remember to click <strong>Save Table Edits</strong> when finished.
        </div>
        """, unsafe_allow_html=True)

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
        if "Pipeline Demands" in selection and 'Status' in display_df.columns:
            def highlight_status(row):
                styles = [''] * len(row)
                if pd.notna(row.get('Status')):
                    val = str(row['Status']).strip().upper()
                    bg_color = ''
                    text_color = ''
                    if val == 'FULFILLED':
                        bg_color = '#ECFDF5'
                        text_color = '#059669'
                    elif val == 'INVALID':
                        bg_color = '#FEF2F2'
                        text_color = '#DC2626'
                    elif val == 'AWAITING CONFIRMATION':
                        bg_color = '#FFFBEB'
                        text_color = '#D97706'
                    elif val == 'OPEN':
                        bg_color = '#EFF6FF'
                        text_color = '#2563EB'
                    
                    if bg_color:
                        status_idx = row.index.get_loc('Status')
                        styles[status_idx] = f'background-color: {bg_color}; color: {text_color}; font-weight: 600;'
                return styles
            styled_df = display_df.style.apply(highlight_status, axis=1)

        if edit_mode:
            st.data_editor(
                styled_df, 
                use_container_width=True, 
                height=380,
                num_rows="dynamic",
                hide_index=True,
                key=editor_key,
                column_config=col_config
            )
        else:
            st.dataframe(
                styled_df,
                use_container_width=True,
                height=380,
                hide_index=True,
                column_config=col_config
            )
        
        # Edit State Handling & Save Serialization
        editor_state = st.session_state.get(editor_key, {})
        has_changes = any(len(v) > 0 for v in editor_state.values() if isinstance(v, dict) or isinstance(v, list))
        
        if has_changes:
            st.warning("⚠️ You have pending changes in the table above.")
            if st.button("💾 Save Table Edits to CSV", use_container_width=True, type="primary", key="save_pipeline_btn"):
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
                df_to_save = raw_df[[c for c in expected_cols if c in raw_df.columns]]
                df_to_save.to_csv(file_path, index=False)
                st.success("Successfully synchronized changes to CSV!")
                load_data.clear()
                st.rerun()
    else:
        st.markdown("""
        <div style="text-align:center; padding: 2.5rem; background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px;">
            <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">🔍</div>
            <div style="font-weight: 600; color: #0F172A;">No Matching Pipeline Demands</div>
            <div style="font-size: 0.825rem; color: #64748B; margin-top: 0.25rem;">Try adjusting or clearing your active search and filter selections above.</div>
        </div>
        """, unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # ✦ PIPELINE DEMAND AI ASSISTANT SECTION
    # -------------------------------------------------------------------------
    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

    with st.container():
        st.markdown("""
        <div class="ai-assistant-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span class="ai-badge">✦ AI ASSISTANT</span>
                    <span style="font-weight: 600; font-size: 0.95rem; color: #0F172A;">Pipeline Intelligence Assistant</span>
                </div>
                <span class="ai-context-indicator">Grounded strictly in <code>PipelineDemand_Details.csv</code></span>
            </div>
            <div style="font-size: 0.8rem; color: #475569; margin-bottom: 0.75rem;">
                Ask natural-language questions to analyze pipeline volume, fulfillment status, seniority breakdown, and lead allocations.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Contextual data detection
        is_filtered = (search_query != "" or selected_status != "All Statuses" or selected_level != "All Levels" or selected_lead != "All PT Leads") and not display_df.empty
        
        if is_filtered:
            st.markdown(f"""
            <div style="background:#EFF6FF; border:1px solid #BFDBFE; border-radius:6px; padding:0.4rem 0.75rem; font-size:0.775rem; color:#1D4ED8; margin-bottom:0.75rem;">
                🤖 <strong>Active Filter Context:</strong> AI Assistant is evaluating the current filtered view (<strong>{len(display_df)}</strong> matching demands).
            </div>
            """, unsafe_allow_html=True)
            working_df = display_df.drop(columns=['🗑️ Delete Row'], errors='ignore')
        else:
            st.markdown(f"""
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:0.4rem 0.75rem; font-size:0.775rem; color:#475569; margin-bottom:0.75rem;">
                🤖 <strong>Full Dataset Context:</strong> AI Assistant is evaluating all <strong>{len(raw_df)}</strong> pipeline demand records.
            </div>
            """, unsafe_allow_html=True)
            working_df = raw_df.copy()

        # Initialize Assistant
        ai_assistant = PipelineAIAssistant(df=working_df)

        if "ai_chat_history" not in st.session_state:
            st.session_state.ai_chat_history = []

        # Suggested Prompts Expander
        with st.expander("💡 **Suggested Inquiries** (Click to ask instantly)", expanded=len(st.session_state.ai_chat_history) == 0):
            suggested_list = PipelineAIAssistant.get_suggested_questions()
            sugg_cols = st.columns(2)
            clicked_suggestion = None
            for s_idx, s_text in enumerate(suggested_list):
                t_col = sugg_cols[s_idx % 2]
                with t_col:
                    if st.button(f"• {s_text}", key=f"btn_sugg_{s_idx}", use_container_width=True):
                        clicked_suggestion = s_text

        # Clear Chat Action
        if st.session_state.ai_chat_history:
            c_clear_space, c_clear_btn = st.columns([5, 1])
            with c_clear_btn:
                if st.button("🗑️ Clear History", key="clear_chat_btn", use_container_width=True):
                    st.session_state.ai_chat_history = []
                    st.rerun()

        # Render Conversation Transcript
        for chat_msg in st.session_state.ai_chat_history:
            with st.chat_message(chat_msg["role"]):
                st.markdown(chat_msg["content"])

        # Chat Input Box
        user_chat_query = st.chat_input("Ask any question about pipeline demand data...", key="pipeline_chat_input")
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
# MODULE 2: DST BENCH RESOURCES (MATCHING ENTERPRISE ARCHITECTURE & FEATURES)
# =============================================================================
elif selection == "DST Bench Resources":
    # -------------------------------------------------------------------------
    # DYNAMIC KPI INTELLIGENCE METRICS
    # -------------------------------------------------------------------------
    if not raw_df.empty and 'Status' in raw_df.columns:
        total_bench = len(raw_df)
        
        # Standardize status for accurate calculation
        status_series = raw_df['Status'].astype(str).str.strip().str.upper()
        
        profile_shared_count = int((status_series == 'PROFILE SHARED').sum())
        onboarding_billing_count = int(((status_series == 'ONBOARDING STARTED') | (status_series == 'BILLING STARTED')).sum())
        awaiting_count = int((status_series == 'AWAITING ENGAGEMENT').sum())
        
        # Compute Average Bench Days
        if 'Bench Days' in raw_df.columns:
            bench_days_series = pd.to_numeric(raw_df['Bench Days'], errors='coerce').dropna()
            avg_bench_days = int(round(bench_days_series.mean())) if not bench_days_series.empty else 0
        else:
            avg_bench_days = 0

        k1, k2, k3, k4, k5 = st.columns(5)

        with k1:
            st.markdown(f"""
            <div class="kpi-card" style="--card-accent: #0F172A;">
                <div class="kpi-label">Total Bench (Active)</div>
                <div class="kpi-value">{total_bench}</div>
                <div class="kpi-subtext">
                    <span>Active bench pool</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with k2:
            st.markdown(f"""
            <div class="kpi-card" style="--card-accent: #2563EB;">
                <div class="kpi-label">Profile Shared</div>
                <div class="kpi-value" style="color:#2563EB;">{profile_shared_count}</div>
                <div class="kpi-subtext">
                    <span>In client review</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with k3:
            st.markdown(f"""
            <div class="kpi-card" style="--card-accent: #10B981;">
                <div class="kpi-label">Onboarding / Billing</div>
                <div class="kpi-value" style="color:#059669;">{onboarding_billing_count}</div>
                <div class="kpi-subtext">
                    <span>Deployment started</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with k4:
            st.markdown(f"""
            <div class="kpi-card" style="--card-accent: #F59E0B;">
                <div class="kpi-label">Awaiting Engagement</div>
                <div class="kpi-value" style="color:#D97706;">{awaiting_count}</div>
                <div class="kpi-subtext">
                    <span>Ready for allocation</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with k5:
            st.markdown(f"""
            <div class="kpi-card" style="--card-accent: #8B5CF6;">
                <div class="kpi-label">Avg Bench Duration</div>
                <div class="kpi-value" style="color:#7C3AED;">{avg_bench_days} <span style="font-size:1rem; font-weight:500;">Days</span></div>
                <div class="kpi-subtext">
                    <span>Bench aging index</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height: 1.25rem;'></div>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # ENTERPRISE ANALYTICS VISUALIZATION SECTION
    # -------------------------------------------------------------------------
    if not raw_df.empty:
        chart_col1, chart_col2 = st.columns(2)
        
        # Chart 1: Bench Status Breakdown (Enterprise Donut Chart)
        with chart_col1:
            if 'Status' in raw_df.columns:
                plot_status_df = raw_df[raw_df['Status'] != 'Unassigned'].copy()
                plot_status_df['Clean_Status'] = plot_status_df['Status'].astype(str).str.strip().str.title()
                status_summary = plot_status_df['Clean_Status'].value_counts().reset_index()
                status_summary.columns = ['Status', 'Count']
                
                # Semantic Enterprise Color Mapping for DST Bench
                semantic_color_map = {
                    "Profile Shared": "#2563EB",
                    "Onboarding Started": "#10B981",
                    "Billing Started": "#059669",
                    "Awaiting Engagement": "#F59E0B"
                }
                
                fig_status = px.pie(
                    status_summary,
                    names='Status',
                    values='Count',
                    hole=0.6,
                    color='Status',
                    color_discrete_map=semantic_color_map
                )
                
                fig_status.update_traces(
                    textposition='inside',
                    textinfo='percent',
                    hovertemplate="<b>%{label}</b><br>Resources: %{value}<br>Share: %{percent}<extra></extra>",
                    marker=dict(line=dict(color='#FFFFFF', width=2))
                )
                
                fig_status.update_layout(
                    title=dict(
                        text="<b>Bench Allocation by Status</b>",
                        font=dict(family="Plus Jakarta Sans, Inter", size=14, color="#0F172A")
                    ),
                    margin=dict(l=10, r=10, t=40, b=10),
                    height=360,
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.2,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=11)
                    ),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)"
                )
                
                st.plotly_chart(fig_status, use_container_width=True)

        # Chart 2: Month-wise Release Count by Resource Level (or Distribution by Level)
        with chart_col2:
            date_col = 'Last Project Release Date' if 'Last Project Release Date' in raw_df.columns else None
            level_col = 'Resource Level' if 'Resource Level' in raw_df.columns else None
            
            plotted_chart = False
            if date_col and level_col:
                plot_df = raw_df[
                    (raw_df[date_col] != 'Unassigned') & 
                    (raw_df[level_col] != 'Unassigned')
                ].copy()
                plot_df['Parsed_Date'] = pd.to_datetime(plot_df[date_col], errors='coerce')
                plot_df = plot_df.dropna(subset=['Parsed_Date'])
                
                if not plot_df.empty:
                    plot_df['Month'] = plot_df['Parsed_Date'].dt.strftime('%b %Y')
                    plot_df['Month_Sort'] = plot_df['Parsed_Date'].dt.to_period('M')
                    
                    time_counts = plot_df.groupby(['Month', 'Month_Sort', level_col]).size().reset_index(name='Bench Resources')
                    time_counts = time_counts.sort_values('Month_Sort')
                    
                    level_color_palette = ['#2563EB', '#0EA5E9', '#6366F1', '#8B5CF6', '#F59E0B', '#10B981']
                    
                    fig_level = px.bar(
                        time_counts,
                        x='Month',
                        y='Bench Resources',
                        color=level_col,
                        barmode='group',
                        text='Bench Resources',
                        color_discrete_sequence=level_color_palette
                    )
                    
                    fig_level.update_traces(
                        textposition='outside',
                        hovertemplate="<b>%{x}</b><br>Level: %{fullData.name}<br>Resources: %{y}<extra></extra>",
                        marker=dict(line=dict(color='#FFFFFF', width=1))
                    )
                    
                    chronological_months = list(dict.fromkeys(time_counts['Month'].tolist()))
                    
                    fig_level.update_layout(
                        title=dict(
                            text="<b>Month Wise Release Count by Resource Level</b>",
                            font=dict(family="Plus Jakarta Sans, Inter", size=14, color="#0F172A")
                        ),
                        xaxis=dict(
                            title="",
                            categoryorder='array',
                            categoryarray=chronological_months,
                            showgrid=False
                        ),
                        yaxis=dict(
                            title="",
                            showgrid=True,
                            gridcolor="#F1F5F9",
                            dtick=1
                        ),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.25,
                            xanchor="center",
                            x=0.5,
                            title=dict(text=""),
                            font=dict(size=11)
                        ),
                        margin=dict(l=10, r=20, t=40, b=10),
                        height=360,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)"
                    )
                    
                    st.plotly_chart(fig_level, use_container_width=True)
                    plotted_chart = True

            if not plotted_chart:
                # Fallback: Location vs Resource Level breakdown
                if 'Location' in raw_df.columns and 'Resource Level' in raw_df.columns:
                    loc_df = raw_df[raw_df['Location'] != 'Unassigned'].copy()
                    loc_counts = loc_df.groupby(['Location', 'Resource Level']).size().reset_index(name='Bench Resources')
                    fig_loc = px.bar(
                        loc_counts,
                        x='Location',
                        y='Bench Resources',
                        color='Resource Level',
                        barmode='group',
                        text='Bench Resources',
                        color_discrete_sequence=['#2563EB', '#0EA5E9', '#6366F1', '#8B5CF6', '#F59E0B']
                    )
                    fig_loc.update_layout(
                        title=dict(
                            text="<b>Bench Resources by Location & Level</b>",
                            font=dict(family="Plus Jakarta Sans, Inter", size=14, color="#0F172A")
                        ),
                        margin=dict(l=10, r=20, t=40, b=10),
                        height=360,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)"
                    )
                    st.plotly_chart(fig_loc, use_container_width=True)
                else:
                    st.info("No timeline data available to chart.")

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # ADVANCED FILTER TOOLBAR & DATA CONTROLS
    # -------------------------------------------------------------------------
    st.markdown("### 📋 DST Bench Resource Details")

    # Filter Controls Card
    with st.container():
        f_c1, f_c2, f_c3, f_c4, f_c5 = st.columns([1.8, 1.2, 1.2, 1.2, 1.2])
        
        with f_c1:
            search_query_dst = st.text_input(
                "Global Search",
                placeholder="🔍 Search GPN, name, level, project, location...",
                label_visibility="collapsed",
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
        mask = display_df.apply(lambda row: row.astype(str).str.contains(search_query_dst, case=False, na=False).any(), axis=1)
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
    ctrl_left, ctrl_right = st.columns([2, 1.5])

    with ctrl_left:
        total_recs = len(raw_df)
        shown_recs = len(display_df)
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:0.5rem; height: 100%; padding-top: 0.25rem;">
            <span class="results-count-pill">Showing {shown_recs} of {total_recs} bench resources</span>
            {f"<span style='font-size:0.75rem; color:#64748B;'>Filtered by: {selected_status_dst if selected_status_dst != 'All Statuses' else ''} {selected_level_dst if selected_level_dst != 'All Levels' else ''} {selected_location if selected_location != 'All Locations' else ''}</span>" if (selected_status_dst != "All Statuses" or selected_level_dst != "All Levels" or selected_location != "All Locations" or search_query_dst) else ""}
        </div>
        """, unsafe_allow_html=True)

    with ctrl_right:
        btn_col1, btn_col2 = st.columns([1, 1])
        with btn_col1:
            edit_mode_dst = st.toggle("✏️ Edit Mode", value=False, help="Enable inline cell editing and dynamic record updates", key="edit_mode_dst")
        with btn_col2:
            if not display_df.empty:
                export_df = display_df.drop(columns=['🗑️ Delete Row'], errors='ignore')
                csv_export = export_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Export CSV",
                    data=csv_export,
                    file_name=f"dst_bench_export_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="export_dst_btn"
                )

    # -------------------------------------------------------------------------
    # MAIN DATA TABLE & EDITOR
    # -------------------------------------------------------------------------
    if edit_mode_dst:
        st.markdown("""
        <div style="background:#FFFBEB; border:1px solid #FDE68A; border-radius:6px; padding:0.6rem 0.9rem; font-size:0.8rem; color:#92400E; margin-bottom:0.75rem;">
            ⚠️ <strong>Edit Mode Active:</strong> Double-click any cell to modify values, add new rows at the bottom, or select <code>🗑️ Delete Row</code> to delete records. Remember to click <strong>Save Table Edits</strong> when finished.
        </div>
        """, unsafe_allow_html=True)

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
            def highlight_dst_status(row):
                styles = [''] * len(row)
                if pd.notna(row.get('Status')):
                    val = str(row['Status']).strip().upper()
                    bg_color = ''
                    text_color = ''
                    if val == 'PROFILE SHARED':
                        bg_color = '#EFF6FF'
                        text_color = '#2563EB'
                    elif val == 'ONBOARDING STARTED':
                        bg_color = '#ECFDF5'
                        text_color = '#059669'
                    elif val == 'BILLING STARTED':
                        bg_color = '#F0FDF4'
                        text_color = '#166534'
                    elif val == 'AWAITING ENGAGEMENT':
                        bg_color = '#FFFBEB'
                        text_color = '#D97706'
                    
                    if bg_color:
                        status_idx = row.index.get_loc('Status')
                        styles[status_idx] = f'background-color: {bg_color}; color: {text_color}; font-weight: 600;'
                return styles
            styled_df_dst = display_df.style.apply(highlight_dst_status, axis=1)

        if edit_mode_dst:
            st.data_editor(
                styled_df_dst, 
                use_container_width=True, 
                height=380,
                num_rows="dynamic",
                hide_index=True,
                key=editor_key_dst,
                column_config=col_config_dst
            )
        else:
            st.dataframe(
                styled_df_dst,
                use_container_width=True,
                height=380,
                hide_index=True,
                column_config=col_config_dst
            )
        
        # Edit State Handling & Save Serialization
        editor_state_dst = st.session_state.get(editor_key_dst, {})
        has_changes_dst = any(len(v) > 0 for v in editor_state_dst.values() if isinstance(v, dict) or isinstance(v, list))
        
        if has_changes_dst:
            st.warning("⚠️ You have pending changes in the table above.")
            if st.button("💾 Save Table Edits to CSV", use_container_width=True, type="primary", key="save_dst_btn"):
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
                df_to_save = raw_df[[c for c in expected_cols if c in raw_df.columns]]
                df_to_save.to_csv(file_path, index=False)
                st.success("Successfully synchronized changes to CSV!")
                load_data.clear()
                st.rerun()
    else:
        st.markdown("""
        <div style="text-align:center; padding: 2.5rem; background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px;">
            <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">🔍</div>
            <div style="font-weight: 600; color: #0F172A;">No Matching DST Bench Resources</div>
            <div style="font-size: 0.825rem; color: #64748B; margin-top: 0.25rem;">Try adjusting or clearing your active search and filter selections above.</div>
        </div>
        """, unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # ✦ DST BENCH AI ASSISTANT SECTION
    # -------------------------------------------------------------------------
    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

    with st.container():
        st.markdown("""
        <div class="ai-assistant-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span class="ai-badge">✦ AI ASSISTANT</span>
                    <span style="font-weight: 600; font-size: 0.95rem; color: #0F172A;">DST Bench Intelligence Assistant</span>
                </div>
                <span class="ai-context-indicator">Grounded strictly in <code>DST_Bench.csv</code></span>
            </div>
            <div style="font-size: 0.8rem; color: #475569; margin-bottom: 0.75rem;">
                Ask natural-language questions to analyze bench resources, aging duration, location distribution, and counsellor alignments.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Contextual data detection
        is_filtered_dst = (search_query_dst != "" or selected_status_dst != "All Statuses" or selected_level_dst != "All Levels" or selected_location != "All Locations" or selected_counsellor != "All Counsellors") and not display_df.empty
        
        if is_filtered_dst:
            st.markdown(f"""
            <div style="background:#EFF6FF; border:1px solid #BFDBFE; border-radius:6px; padding:0.4rem 0.75rem; font-size:0.775rem; color:#1D4ED8; margin-bottom:0.75rem;">
                🤖 <strong>Active Filter Context:</strong> AI Assistant is evaluating the current filtered view (<strong>{len(display_df)}</strong> matching bench resources).
            </div>
            """, unsafe_allow_html=True)
            working_df_dst = display_df.drop(columns=['🗑️ Delete Row'], errors='ignore')
        else:
            st.markdown(f"""
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:0.4rem 0.75rem; font-size:0.775rem; color:#475569; margin-bottom:0.75rem;">
                🤖 <strong>Full Dataset Context:</strong> AI Assistant is evaluating all <strong>{len(raw_df)}</strong> DST bench records.
            </div>
            """, unsafe_allow_html=True)
            working_df_dst = raw_df.copy()

        # Initialize DST Bench Assistant
        dst_ai_assistant = DSTBenchAIAssistant(df=working_df_dst)

        if "dst_ai_chat_history" not in st.session_state:
            st.session_state.dst_ai_chat_history = []

        # Suggested Prompts Expander
        with st.expander("💡 **Suggested Inquiries** (Click to ask instantly)", expanded=len(st.session_state.dst_ai_chat_history) == 0):
            suggested_list_dst = DSTBenchAIAssistant.get_suggested_questions()
            sugg_cols_dst = st.columns(2)
            clicked_suggestion_dst = None
            for s_idx, s_text in enumerate(suggested_list_dst):
                t_col = sugg_cols_dst[s_idx % 2]
                with t_col:
                    if st.button(f"• {s_text}", key=f"btn_sugg_dst_{s_idx}", use_container_width=True):
                        clicked_suggestion_dst = s_text

        # Clear Chat Action
        if st.session_state.dst_ai_chat_history:
            c_clear_space, c_clear_btn = st.columns([5, 1])
            with c_clear_btn:
                if st.button("🗑️ Clear History", key="clear_chat_dst_btn", use_container_width=True):
                    st.session_state.dst_ai_chat_history = []
                    st.rerun()

        # Render Conversation Transcript
        for chat_msg in st.session_state.dst_ai_chat_history:
            with st.chat_message(chat_msg["role"]):
                st.markdown(chat_msg["content"])

        # Chat Input Box
        user_chat_query_dst = st.chat_input("Ask any question about DST bench resource data...", key="dst_chat_input")
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
