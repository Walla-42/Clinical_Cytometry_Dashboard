import streamlit as st
import plotly.express as px
from database import DataAccessError, Project_Database
from scipy.stats import ttest_ind
import pandas as pd

# Configure page
st.set_page_config(layout="wide", page_title="Bob's Clinical Trial Dashboard")

# Initialize database
@st.cache_resource
def init_db():
    try:
        return Project_Database()
    except DataAccessError as e:
        st.error(f"Database Error: {str(e.user_message)}")
        st.stop()

# Cached database queries
@st.cache_data
def get_relative_frequencies(project_id):
    try:
        return db.get_relative_frequencies(project_id)
    except DataAccessError:
        st.error("Failed to load relative frequencies data.")
        return None

@st.cache_data
def get_projects():
    try:
        return db.get_projects()
    except DataAccessError:
        st.error("Failed to load projects.")
        return None

@st.cache_data
def get_conditions(project_id):
    try:
        return db.get_conditions(project_id)
    except DataAccessError:
        st.error("Failed to load conditions.")
        return None

@st.cache_data
def get_sample_types(project_id):
    try:
        return db.get_sample_types(project_id)
    except DataAccessError:
        st.error("Failed to load sample types.")
        return None

@st.cache_data
def get_time_points(project_id):
    try:
        return db.get_time_points(project_id)
    except DataAccessError:
        st.error("Failed to load time points.")
        return None

@st.cache_data
def get_treatments(project_id):
    try:
        return db.get_treatments(project_id)
    except DataAccessError:
        st.error("Failed to load treatments.")
        return None

@st.cache_data
def get_statistical_subset(condition, sample_type, time_point, treatment):
    try:
        return db.get_statistical_subset(condition, sample_type, time_point, treatment)
    except DataAccessError:
        st.error("Failed to load statistical subset.")
        return None

# View rendering functions
def render_data_overview(df_freq):
    """Render the data overview section."""
    with st.container():
        st.header("Data Overview")

        if "file_upload_key" not in st.session_state:
            st.session_state.file_upload_key = 0

        uploaded_file = st.file_uploader("Upload cell count data", type=["csv"], key=f"upload_file_{st.session_state.file_upload_key}")
        if uploaded_file:
            try:
                db.load_csv_data(uploaded_file)
                st.success("Data loaded successfully!")
                st.cache_data.clear()
            except DataAccessError as e:
                st.error(str(e.user_message))

            st.session_state.file_upload_key += 1

        if df_freq is not None:
            st.dataframe(df_freq, width='stretch', height=600)
        else:
            st.info("No data available yet. Please upload a CSV file.")

def render_statistical_analysis(project_id):
    """Render the statistical analysis section."""
    st.header("Statistical Analysis")

    
    conditions = get_conditions(project_id)
    sample_types = get_sample_types(project_id)
    time_points = get_time_points(project_id)
    treatments = get_treatments(project_id)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        selected_condition = st.selectbox(
            "Condition:", 
            options=conditions if conditions else ["No conditions"],
            index=0
        )
    
    with col2:
        selected_sample_type = st.selectbox(
            "Sample Type:", 
            options=sample_types if sample_types else ["No sample types"],
            index=0
        )
    
    with col3:
        selected_time_points = st.selectbox(
            "Time Point:", 
            options=time_points if time_points else ["No time points"],
            index=0
        )
    
    with col4:
        selected_treatment = st.selectbox(
            "Treatment:", 
            options=treatments if treatments else ["No treatments"],
            index=0
        )
    
    # Fetch statistical data
    df_stats = get_statistical_subset(selected_condition, selected_sample_type, selected_time_points, selected_treatment)
    
    if df_stats is not None and not df_stats.empty:
        cell_populations = sorted(df_stats['population'].unique())
        
        with col5:
            pop = st.selectbox(
                "Cell Type:", 
                options=cell_populations if cell_populations else ["No cell types"],
                index=0
            )
        
        filtered_stats = df_stats[df_stats['population'] == pop]
        
        # chart
        fig = px.box(
            filtered_stats, 
            x="response", 
            y="percentage", 
            color="response", 
            points="all",
            title=f"{pop} %: Responders vs Non-Responders",
            labels={"percentage": "Relative Frequency (%)", "response": "Response"}
        )
        st.plotly_chart(fig, width="stretch")
        
        st.subheader("Statistics")
        
        # Calculate t-tests for each cell population
        stats_results = []
        for cell_type in sorted(df_stats['population'].unique()):
            responders = df_stats[(df_stats['population'] == cell_type) & (df_stats['response'] == 'yes')]['percentage'].values
            non_responders = df_stats[(df_stats['population'] == cell_type) & (df_stats['response'] == 'no')]['percentage'].values
            
            if len(responders) > 0 and len(non_responders) > 0:
                t_stat, p_value = ttest_ind(responders, non_responders, equal_var=False)
                significant = "Yes" if p_value < 0.05 else "No"
                stats_results.append({
                    "Cell Type": cell_type,
                    "T-Statistic": f"{t_stat:.4f}",
                    "P-Value": f"{p_value:.6f}",
                    "Significant (α=0.05)": significant
                })
        
        if stats_results:
            stats_df = pd.DataFrame(stats_results)
            st.dataframe(stats_df, width='stretch', height=200)
        else:
            st.warning("Insufficient data for statistical analysis.")
    else:
        st.warning("No data available for the selected filters.")


# App starts here: 
st.title("Bob's Clinical Trial Dashboard")
db = init_db()
projects = get_projects() or []
if not projects:
    st.error("No projects available. Please upload data.")

select_project = st.selectbox(
    "Project:",
    options=projects,
    index=0 if projects else 0,
)

overview_col, analysis_col = st.columns(2)
with overview_col:
    df_freq = get_relative_frequencies(select_project)
    render_data_overview(df_freq)

with analysis_col:
    render_statistical_analysis(select_project)

