import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

st.set_page_config(page_title="Resource Portfolio Master Dashboard", page_icon="📈", layout="wide")

# Custom UI Tuning
st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    div[data-testid="metric-container"] {
        border: 1px solid rgba(128,128,128,0.2);
        padding: 5% 10%;
        border-radius: 8px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
        background-color: var(--background-color);
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------
# CONFIGURATION & SCHEMA MAPPING
# -----------------------------------
FILES = {
    "PT Members": {
        "path": "GDS_PTMembers.csv",
        "description": "Overall PT members including ACTIVE & QUIT statuses.",
        "cols": ["GUI", "GPN", "Resource Name", "Status", "Seniority Date", "Location", "Level", "Counsellor Name"]
    },
    "Soon To Bench": {
        "path": "DST_SoonTobench.csv",
        "description": "Resources projected to roll off current engagements soon.",
        "cols": ["GUI", "GPN", "Resource Name", "Status", "Seniority Date", "Location", "Level", "Counsellor Name"]
    },
    "On Bench": {
        "path": "DST_Bench.csv",
        "description": "Resources currently actively on bench awaiting deployment.",
        "cols": ["GPN", "Name", "Resource Level", "Status", "Bench Days", "Last Project Release Date", "Last Project Name", "Additional Comments", "Location", "Cousellor Name"]
    },
    "Pipeline Demands": {
        "path": "PipelineDemand_Details.csv",
        "description": "Upcoming pipeline demands, fulfilled, and invalid requests.",
        "cols": ["Role ID", "Eng ID", "Eng Name", "Sector", "Client", "Start Date", "Resource Level", "Comments", "Status"]
    }
}

@st.cache_data
def load_data(file_path, expected_cols):
    """Loads sheet data cleanly, padding necessary schema to prevent render crashes."""
    if not os.path.exists(file_path):
        return pd.DataFrame(columns=expected_cols)
    try:
        df = pd.read_csv(file_path)
        # Assure any totally blank NaN entries render as identifiable string components.
        df = df.fillna('Unassigned') 
        return df
    except Exception as e:
        st.error(f"Failed to parse {file_path}: {e}")
        return pd.DataFrame(columns=expected_cols)

# -----------------------------------
# SIDEBAR NAVIGATION
# -----------------------------------
st.sidebar.title("Portfolio Navigation")
st.sidebar.markdown("Switch context between distinct trackers dynamically.")
selection = st.sidebar.radio("Select Tracker Scope:", list(FILES.keys()))

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Force Refresh Cache"):
    load_data.clear()
    st.rerun()

# -----------------------------------
# MAIN RENDER LOOP PER SHEET
# -----------------------------------
current_config = FILES[selection]
file_path = current_config["path"]
expected_cols = current_config["cols"]

st.title(f"📂 {selection} View")
st.caption(current_config["description"])

# Retrieve working dataset explicitly bounds checked against selected path.
df = load_data(file_path, expected_cols)

# -----------------------------------------------
# 1. ADD NEW DATA COMPONENT (DYNAMIC PARSER)
# -----------------------------------------------
with st.expander(f"➕ Add New Record manually to {file_path}", expanded=False):
    with st.form(key=f"form_{selection}", clear_on_submit=True):
        st.subheader("Data Intake Form")
        input_data = {}
        c1, c2 = st.columns(2)
        
        # We auto-generate inputs based on expected_cols constraint mapped specifically avoiding manual hardcoding mismatches
        for idx, col_name in enumerate(expected_cols):
            target = c1 if idx % 2 == 0 else c2
            with target:
                if 'Date' in col_name:
                    input_data[col_name] = st.date_input(f"{col_name} *")
                elif 'Days' in col_name:
                    input_data[col_name] = st.number_input(f"{col_name} *", min_value=0, step=1)
                else:
                    input_data[col_name] = st.text_input(f"{col_name} *")
        
        submit = st.form_submit_button("💾 Save to Sheet")
        if submit:
            # Normalize complex types prior to pandas push to maintain uniformity globally
            for col_name in expected_cols:
                if 'Date' in col_name:
                    try:
                        # Emulate the explicit formatting standard the users already injected (e.g. 10/1/2026) 
                        input_data[col_name] = input_data[col_name].strftime("%m/%d/%Y")
                    except Exception:
                        input_data[col_name] = ""
            
            new_row = pd.DataFrame([input_data])
            # Check headers. Crucial for first insertion creation vs append.
            has_headers = os.path.exists(file_path) and os.path.getsize(file_path) > 0
            new_row.to_csv(file_path, mode='a', header=not has_headers, index=False)
            
            st.success(f"Record successfully written into '{file_path}'!")
            load_data.clear()
            st.rerun()

st.markdown("---")

# -----------------------------------------------
# 2. OVERVIEW METRICS / KPIS
# -----------------------------------------------
st.subheader("📊 Key Performance Operations")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Extracted Records", len(df))

if not df.empty:
    if 'Status' in df.columns:
        # Prevent tracking issues mapping values if unassigned
        cleaned_status = df[df['Status'] != 'Unassigned']['Status']
        if not cleaned_status.empty:
            unique_statuses = cleaned_status.value_counts()
            if len(unique_statuses) > 0:
                m2.metric(f"Top Tag: {unique_statuses.index[0]}", unique_statuses.iloc[0])
            if len(unique_statuses) > 1:
                m3.metric(f"Runner-up Tag: {unique_statuses.index[1]}", unique_statuses.iloc[1])
                
    if 'Bench Days' in df.columns:
        avg_bench = pd.to_numeric(df['Bench Days'], errors='coerce').mean()
        m4.metric("Average Bench Duration", f"{avg_bench:.1f} Days" if pd.notna(avg_bench) else "N/A", delta_color="inverse")
    elif 'Sector' in df.columns:
        sectors = df['Sector'].nunique()
        m4.metric("Unique Client Sectors", sectors)

# -----------------------------------------------
# 3. INTERACTIVE VISUALIZATIONS
# -----------------------------------------------
st.subheader("📈 Functional Intelligence")
if not df.empty:
    vc1, vc2 = st.columns(2)
    chart_idx = 0
    
    # Priority schema plot targets mapped safely. Iterates plotting if available in respective csv.
    plot_columns = [col for col in ['Status', 'Location', 'Level', 'Resource Level', 'Sector', 'Client'] if col in df.columns]
    
    for plot_col in plot_columns:
        target_col = vc1 if chart_idx % 2 == 0 else vc2
        with target_col:
            # We enforce excluding purely missing elements mapped inherently as Unassigned to not skew charting
            plot_df = df[df[plot_col] != 'Unassigned']
            if not plot_df.empty:
                data_vis = plot_df[plot_col].value_counts().reset_index()
                data_vis.columns = [plot_col, 'Volume']
                
                # Pie for constrained groups, bar for scattered vectors visually mappings.
                if len(data_vis) <= 6:
                    fig = px.pie(data_vis, names=plot_col, values='Volume', hole=0.35, title=f"Allocation by {plot_col}")
                else:
                    fig = px.bar(data_vis, x=plot_col, y='Volume', color='Volume', title=f"Volume mapped per {plot_col}")
                
                st.plotly_chart(fig, use_container_width=True)
            chart_idx += 1
            
    # Conditional histogram specifically targeting bench timeframe risk.
    if 'Bench Days' in df.columns:
        numeric_bench = pd.to_numeric(df['Bench Days'], errors='coerce').dropna()
        if not numeric_bench.empty:
            target_col = vc1 if chart_idx % 2 == 0 else vc2
            with target_col:
                fig = px.histogram(numeric_bench, x=numeric_bench, nbins=15, title="Bench Duration Tally", color_discrete_sequence=['#ff6b6b'])
                fig.update_layout(xaxis_title="Days on Bench", yaxis_title="Resource Count")
                st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------
# 4. DATATABLE LOGIC BROWSER
# -----------------------------------------------
st.subheader("📋 Underlying Dataset Matrix")
search = st.text_input("🔍 Filter rows globally by text value", "")

display_df = df.copy()
if search and not display_df.empty:
    # Blanket cast search vector cross table string interpolation 
    mask = display_df.apply(lambda row: row.astype(str).str.contains(search, case=False, na=False).any(), axis=1)
    display_df = display_df[mask]

# Stylize specific conditional warnings dynamically identifying risks
def style_risk_factors(val):
    if isinstance(val, str) and (val.lower() == 'bench' or val.lower() == 'invalid'):
        return 'color: #dc3545; font-weight: bold;'
    elif isinstance(val, str) and (val.lower() == 'active' or val.lower() == 'fulfilled' or val.lower() == 'allocated'):
        return 'color: #28a745; font-weight: bold;'
    return ''

if not display_df.empty:
    if hasattr(display_df.style, 'map'):
        styled_df = display_df.style.map(style_risk_factors)
    else:
        styled_df = display_df.style.applymap(style_risk_factors)
        
    st.dataframe(styled_df, use_container_width=True, height=350)
else:
    st.info("No matching records found. Or the sheet itself is empty.")

# Output exporter component.
if not df.empty:
    csv_export = display_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label=f"📥 Download Current Filtered {selection} Schema as CSV",
        data=csv_export,
        file_name=f"export_{selection.replace(' ', '_')}.csv",
        mime="text/csv"
    )
