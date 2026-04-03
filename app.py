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
    "Performance Testing Members 👥": {
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
st.sidebar.title("Performance Test Resourcing Dashboard")
#st.sidebar.markdown("Switch context between distinct trackers dynamically.")
selection = st.sidebar.radio("Select Tracker:", list(FILES.keys()))

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

st.title(f" {selection}")
st.caption(current_config["description"])

# Retrieve working dataset explicitly bounds checked against selected path.
df = load_data(file_path, expected_cols)

# -----------------------------------------------
# 1. ADD NEW DATA COMPONENT (DYNAMIC PARSER)
# -----------------------------------------------
# with st.expander(f"➕ Add New Record manually to {file_path}", expanded=False):
#     with st.form(key=f"form_{selection}", clear_on_submit=True):
#         st.subheader("Data Intake Form")
#         input_data = {}
#         c1, c2 = st.columns(2)
        
#         # We auto-generate inputs based on expected_cols constraint mapped specifically avoiding manual hardcoding mismatches
#         for idx, col_name in enumerate(expected_cols):
#             target = c1 if idx % 2 == 0 else c2
#             with target:
#                 if 'Date' in col_name:
#                     input_data[col_name] = st.date_input(f"{col_name} *")
#                 elif 'Days' in col_name or col_name in ['GUI', 'GPN']:
#                     input_data[col_name] = st.number_input(f"{col_name} *", min_value=0, step=1, format="%d")
#                 else:
#                     input_data[col_name] = st.text_input(f"{col_name} *")
        
#         submit = st.form_submit_button("💾 Save to Sheet")
#         if submit:
#             # Normalize complex types prior to pandas push to maintain uniformity globally
#             for col_name in expected_cols:
#                 if 'Date' in col_name:
#                     try:
#                         # Emulate the explicit formatting standard the users already injected (e.g. 10/1/2026) 
#                         input_data[col_name] = input_data[col_name].strftime("%m/%d/%Y")
#                     except Exception:
#                         input_data[col_name] = ""
            
#             new_row = pd.DataFrame([input_data])
#             # Check headers. Crucial for first insertion creation vs append.
#             has_headers = os.path.exists(file_path) and os.path.getsize(file_path) > 0
#             new_row.to_csv(file_path, mode='a', header=not has_headers, index=False)
            
#             st.success(f"Record successfully written into '{file_path}'!")
#             load_data.clear()
#             st.rerun()

# st.markdown("---")

# -----------------------------------------------
# 4. DATATABLE LOGIC BROWSER & EDITOR
# -----------------------------------------------
#st.subheader("📋 Underlying Dataset Matrix & Editor")
st.subheader("📋 Table View")
# Provide explicit UI Controls
c_search, c_mode = st.columns([3, 1])

with c_search:
    search = st.text_input("🔍 Filter rows globally by text value", "")
    
with c_mode:
    st.markdown("<br>", unsafe_allow_html=True)
    edit_mode = st.toggle("✏️ Enable Edit Mode", value=False)

display_df = df.copy()

if edit_mode:
    st.markdown("⚠️ **Edit Mode Active:** You can double-click cells to edit, add records at the bottom, or check the '🗑️ Delete' box to remove rows.")
else:
    st.markdown("👁️ **View Mode Active:** Table is safely locked for browsing.")

# Enforce explicit data types across the entire schema per constraints
for col in display_df.columns:
    if col in ['GUI', 'GPN']:
        display_df[col] = pd.to_numeric(display_df[col], errors='coerce').fillna(0).astype(int)
    elif 'Date' in col:
        display_df[col] = pd.to_datetime(display_df[col], errors='coerce').dt.date
    else:
        display_df[col] = display_df[col].astype(str)

if search and not display_df.empty:
    mask = display_df.apply(lambda row: row.astype(str).str.contains(search, case=False, na=False).any(), axis=1)
    display_df = display_df[mask]

if not display_df.empty or df.empty:
    editor_key = f"editor_{selection}"
    
    # Build explicit UI column configurations locking datatypes natively into Streamlit
    col_config = {}
    for col in display_df.columns:
        if col in ['GUI', 'GPN']:
            col_config[col] = st.column_config.NumberColumn(col, format="%d", min_value=0, step=1)
        elif 'Date' in col:
            col_config[col] = st.column_config.DateColumn(col, format="MM/DD/YYYY")
        elif col != '🗑️ Delete Row':
            col_config[col] = st.column_config.TextColumn(col)
            
    if edit_mode:
        if not display_df.empty and '🗑️ Delete Row' not in display_df.columns:
            display_df.insert(0, '🗑️ Delete Row', False)
            
        st.data_editor(
            display_df, 
            use_container_width=True, 
            height=350,
            num_rows="dynamic",
            hide_index=True,
            key=editor_key,
            column_config=col_config
        )
    else:
        st.dataframe(
            display_df,
            use_container_width=True,
            height=350,
            hide_index=True,
            column_config=col_config
        )
    
    editor_state = st.session_state.get(editor_key, {})
    has_changes = any(len(v) > 0 for v in editor_state.values() if isinstance(v, dict) or isinstance(v, list))
    
    if has_changes:
        st.warning("⚠️ You have pending changes in the table above.")
        if st.button("💾 Save Table Edits to CSV", use_container_width=True):
            explicit_deletes = []
            
            # 1. Updates & Explicit Deletions
            for idx_pos, changes in editor_state.get("edited_rows", {}).items():
                true_idx = display_df.index[idx_pos]
                
                # If they clicked the Delete checkbox
                if changes.get('🗑️ Delete Row', False) is True:
                    explicit_deletes.append(true_idx)
                else:
                    for col, val in changes.items():
                        if col != '🗑️ Delete Row':
                            df.at[true_idx, col] = val
                            
            # 2. Native Deletions (if they still hit Backspace/Delete)
            deleted_indices = editor_state.get("deleted_rows", [])
            if deleted_indices:
                native_deleted = [display_df.index[i] for i in deleted_indices]
                explicit_deletes.extend(native_deleted)
                
            # Process all deletions
            if explicit_deletes:
                df = df.drop(index=list(set(explicit_deletes)))
                
            # 3. Additions
            added_rows = editor_state.get("added_rows", [])
            if added_rows:
                new_df = pd.DataFrame(added_rows)
                if '🗑️ Delete Row' in new_df.columns:
                    new_df = new_df.drop(columns=['🗑️ Delete Row'])
                for c in df.columns:
                    if c not in new_df.columns:
                        new_df[c] = None
                df = pd.concat([df, new_df[df.columns]], ignore_index=True)
                
            # Strict format adherence ensuring dynamic UI tracking columns never slip into the raw storage
            df_to_save = df[[c for c in expected_cols if c in df.columns]]
            df_to_save.to_csv(file_path, index=False)
            st.success("Successfully synchronized changes to CSV!")
            load_data.clear()
            st.rerun()
else:
    st.info("No matching records found. Or the sheet itself is empty.")

# Output exporter component.
if not df.empty:
    export_df = display_df.drop(columns=['🗑️ Delete Row'], errors='ignore')
    csv_export = export_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label=f"📥 Download table as CSV",
        data=csv_export,
        file_name=f"export_{selection.replace(' ', '_')}.csv",
        mime="text/csv"
    )
st.markdown("*******")

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
