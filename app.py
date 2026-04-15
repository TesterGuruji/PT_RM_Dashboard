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
    # "Performance Testing Members 👥": {
    #     "path": "GDS_PTMembers.csv",
    #     "description": "Overall PT members including ACTIVE & QUIT statuses.",
    #     "cols": ["GUI", "GPN", "Resource Name", "Status", "Seniority Date", "Location", "Level", "Counsellor Name"]
    # },
    # "Soon To Bench": {
    #     "path": "DST_SoonTobench.csv",
    #     "description": "Resources projected to roll off current engagements soon.",
    #     "cols": ["GUI", "GPN", "Resource Name", "Status", "Seniority Date", "Location", "Level", "Counsellor Name"]
    # },
    # "On Bench": {
    #     "path": "DST_Bench.csv",
    #     "description": "Resources currently actively on bench awaiting deployment.",
    #     "cols": ["GPN", "Name", "Resource Level", "Status", "Bench Days", "Last Project Release Date", "Last Project Name", "Additional Comments", "Location", "Cousellor Name"]
    # },
    "Pipeline Demands": {
        "path": "PipelineDemand_Details.csv",
        "description": "Upcoming pipeline demands, fulfilled, and invalid requests.",
        "cols": ["Role ID", "Eng ID", "Eng Name", "Sector", "Sector PT lead", "Client", "Start Date", "Resource Level", "Comments", "Status"]
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
            
    # Apply styling for Pipeline Demands
    styled_df = display_df
    if "Pipeline Demands" in selection and 'Status' in display_df.columns:
        def highlight_status(row):
            styles = [''] * len(row)
            if pd.notna(row.get('Status')):
                val = str(row['Status']).strip().upper()
                bg_color = ''
                text_color = ''
                if val == 'FULFILLED':
                    bg_color = '#28a745'
                    text_color = 'white'
                elif val == 'INVALID':
                    bg_color = '#dc3545'
                    text_color = 'white'
                elif val == 'AWAITING CONFIRMATION':
                    bg_color = '#ffc107'
                    text_color = 'black'
                elif val == 'OPEN':
                    bg_color = '#007bff'
                    text_color = 'white'
                
                if bg_color:
                    status_idx = row.index.get_loc('Status')
                    styles[status_idx] = f'background-color: {bg_color}; color: {text_color}'
            return styles
        styled_df = display_df.style.apply(highlight_status, axis=1)

    if edit_mode:
        st.data_editor(
            styled_df, 
            use_container_width=True, 
            height=350,
            num_rows="dynamic",
            hide_index=True,
            key=editor_key,
            column_config=col_config
        )
    else:
        st.dataframe(
            styled_df,
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
                            # Prevent Strict Upcast Error by making column object type before setting value
                            if df[col].dtype != 'object':
                                df[col] = df[col].astype('object')
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
st.subheader("📊 Key Metrics")

if "Performance Testing Members" in selection:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Members", len(df))
    if not df.empty:
        if 'Status' in df.columns:
            active_count = len(df[df['Status'].astype(str).str.upper() == 'ACTIVE'])
            m2.metric("Active Members", active_count)
        if 'Location' in df.columns:
            locations = df[df['Location'] != 'Unassigned']['Location'].nunique()
            m3.metric("Unique Locations", locations)
        if 'Level' in df.columns:
            levels = df[df['Level'] != 'Unassigned']['Level'].nunique()
            m4.metric("Role Levels", levels)

if "Pipeline Demands" in selection:
    m1, m2, m3, m4 = st.columns(4)
    
    if not df.empty and 'Status' in df.columns and 'Start Date' in df.columns:
        # Prepare date parsing for Current Month metrics
        df_dates = df.copy()
        df_dates['Start Date'] = pd.to_datetime(df_dates['Start Date'], errors='coerce')
        
        now = datetime.now()
        current_month_mask = (df_dates['Start Date'].dt.month == now.month) & (df_dates['Start Date'].dt.year == now.year)
        
        # 1. Open Demand (Current Month)
        open_current_month = len(df_dates[current_month_mask & (df_dates['Status'].astype(str).str.upper() == 'OPEN')])
        m1.metric("Open Demands (Current Month)", open_current_month)
        
        # 2. Overall Open Demand
        overall_open = len(df[df['Status'].astype(str).str.upper() == 'OPEN'])
        m2.metric("Overall Open Demands", overall_open)
        
        # 3. Fulfilled (Current Month)
        fulfilled_current_month = len(df_dates[current_month_mask & (df_dates['Status'].astype(str).str.upper() == 'FULFILLED')])
        m3.metric("Fulfilled (Current Month)", fulfilled_current_month)
        
        # 4. Awaiting Confirmation Demand
        overall_fulfilled = len(df[df['Status'].astype(str).str.upper() == 'AWAITING CONFIRMATION'])
        m4.metric("Awaiting Confirmation", overall_fulfilled)
    else:
        m1.metric("Open Demands (Current Month)", 0)
        m2.metric("Overall Open Demands", 0)
        m3.metric("Fulfilled (Current Month)", 0)
        m4.metric("Overall Fulfilled", 0)
else:
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
#st.subheader("📈 Functional Intelligence")
if not df.empty:
    if "Performance Testing Members" in selection:
        st.markdown("### Resource Distribution Overview")
        
        # 1) Allocation by status pie chart & 2) Number of Resources distribution across location graph
        col1, col2 = st.columns(2)
        with col1:
            if 'Status' in df.columns:
                status_counts = df[df['Status'] != 'Unassigned']['Status'].value_counts().reset_index()
                status_counts.columns = ['Status', 'Count']
                fig_status = px.pie(status_counts, names='Status', values='Count', hole=0.4, title="1. Allocation by Status")
                st.plotly_chart(fig_status, use_container_width=True)
                
        with col2:
            if 'Location' in df.columns:
                loc_counts = df[df['Location'] != 'Unassigned']['Location'].value_counts().reset_index()
                loc_counts.columns = ['Location', 'Count']
                fig_loc = px.bar(loc_counts, x='Location', y='Count', title="2. Resources Distribution Across Location", color='Location')
                st.plotly_chart(fig_loc, use_container_width=True)
                
        # 3) Number of resources distribution across level graph & 4) Location vs Level wise graph
        col3, col4 = st.columns(2)
        with col3:
            if 'Level' in df.columns:
                level_counts = df[df['Level'] != 'Unassigned']['Level'].value_counts().reset_index()
                level_counts.columns = ['Level', 'Count']
                fig_level = px.bar(level_counts, x='Level', y='Count', title="3. Resources Distribution Across Level", color='Level')
                st.plotly_chart(fig_level, use_container_width=True)
                
        with col4:
            if 'Location' in df.columns and 'Level' in df.columns:
                loc_level_df = df[(df['Location'] != 'Unassigned') & (df['Level'] != 'Unassigned')]
                loc_level_counts = loc_level_df.groupby(['Location', 'Level']).size().reset_index(name='Count')
                fig_loc_level = px.bar(loc_level_counts, x='Location', y='Count', color='Level', barmode='group', title="4. Location vs Level Wise Distribution")
                st.plotly_chart(fig_loc_level, use_container_width=True)
                
        # 5) Seniority date vs Resource Name graph
        if 'Seniority Date' in df.columns and 'Resource Name' in df.columns:
            sen_df = df[(df['Seniority Date'] != 'Unassigned') & (df['Resource Name'] != 'Unassigned')].copy()
            sen_df['Seniority Date'] = pd.to_datetime(sen_df['Seniority Date'], errors='coerce')
            sen_df = sen_df.dropna(subset=['Seniority Date'])
            if not sen_df.empty:
                # Sort by date for a solid chronological order on the plot
                sen_df = sen_df.sort_values(by='Seniority Date')
                
                # Only show top 10 most senior (distinct) resources
                sen_df = sen_df.drop_duplicates(subset=['Resource Name']).head(10)
                
                hover_cols = [c for c in ['Location', 'Level', 'Status'] if c in sen_df.columns]
                fig_sen = px.scatter(
                    sen_df, 
                    x='Seniority Date', 
                    y='Resource Name', 
                    color='Level' if 'Level' in sen_df.columns else None,
                    title="5. Top 10 Most Senior Resources (Seniority Date vs Name)",
                    hover_data=hover_cols if hover_cols else None
                )
                fig_sen.update_traces(marker=dict(size=12, line=dict(width=1, color='DarkSlateGrey')))
                
                # Ensure the display logic adheres chronologically instead of alphabetically natively via layout overrides 
                fig_sen.update_layout(yaxis={'categoryorder': 'array', 'categoryarray': sen_df['Resource Name'].tolist()})
                st.plotly_chart(fig_sen, use_container_width=True)

    elif "Pipeline Demands" in selection:
        st.markdown("### Pipeline Demand Graphs")
        col1, col2 = st.columns(2)
        
        #with col1:
        if 'Status' in df.columns:
            plot_status = df[df['Status'] != 'Unassigned'].copy()
            plot_status['Status'] = plot_status['Status'].astype(str).str.title()
            status_counts = plot_status['Status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Count']
            
            color_map = {
                "Fulfilled": "green",
                "Invalid": "red",
                "Awaiting Confirmation": "yellow",
                "Open": "blue"
            }
            
            fig_status = px.pie(
                status_counts, 
                names='Status', 
                values='Count', 
                hole=0.4, 
                title="1. Status Wise Allocation",
                color='Status',
                color_discrete_map=color_map
            )
            st.plotly_chart(fig_status, use_container_width=True)
        #with col2:
        if 'Start Date' in df.columns and 'Resource Level' in df.columns:
            plot_df = df[(df['Start Date'] != 'Unassigned') & (df['Resource Level'] != 'Unassigned') & (df['Status'].str.lower() == 'open')].copy()
            plot_df['Start Date'] = pd.to_datetime(plot_df['Start Date'], errors='coerce')
            plot_df = plot_df.dropna(subset=['Start Date'])
            
            if not plot_df.empty:
                plot_df['Month'] = plot_df['Start Date'].dt.strftime('%b %Y')
                plot_df['Month_Sort'] = plot_df['Start Date'].dt.to_period('M')
                
                time_counts = plot_df.groupby(['Month', 'Month_Sort', 'Resource Level']).size().reset_index(name='Demand Count')
                time_counts = time_counts.sort_values('Month_Sort')
                
                fig_time = px.bar(time_counts, x='Month', y='Demand Count', color='Resource Level', barmode='group', title="2. Month Wise Demand Count by Resource Level")
                # Ensure chronological sorting on x-axis
                fig_time.update_xaxes(categoryorder='array', categoryarray=time_counts['Month'].unique())
                st.plotly_chart(fig_time, use_container_width=True)

    else:
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
