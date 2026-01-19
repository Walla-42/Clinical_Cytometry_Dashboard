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
def get_genders(project_id):
    try:
        return db.get_genders(project_id)
    except DataAccessError:
        st.error("Failed to load gender information.")
        return None

@st.cache_data
def get_statistical_subset(condition, sample_type, time_point, treatment, gender=None):
    try:
        return db.get_statistical_subset(condition, sample_type, time_point, treatment, gender)
    except DataAccessError:
        st.error("Failed to load statistical subset.")
        return None

# View rendering functions
def conditional_colors(var):
    if var.lower() == "yes":
        return "background-color: #55c960"
    elif var.lower() == "no":
        return "background-color: #bf560b"
    return ""

def render_data_overview(df_freq):
    """Render the data overview section."""
    with st.container():
        st.header("Data Overview")

        uploaded_file = st.file_uploader("Upload cell count data", type=["csv"], key=f"upload_file")
        if uploaded_file:
            try:
                db.load_csv_data(uploaded_file)
                st.success("Data loaded successfully!")
                st.cache_data.clear()
            except DataAccessError as e:
                st.error(str(e.user_message))

        if df_freq is not None:
            st.dataframe(df_freq, width='stretch', height=1050)
        else:
            st.info("No data available yet. Please upload a CSV file.")

def render_statistical_analysis(project_id):
    """Render the statistical analysis section."""
    st.header("Statistical Analysis")

    
    conditions = get_conditions(project_id)
    sample_types = get_sample_types(project_id)
    time_points = get_time_points(project_id)
    treatments = get_treatments(project_id)
    gender = get_genders(project_id)

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        selected_condition = st.selectbox(
            "Condition:", 
            options=conditions if conditions else ["No conditions"],
            index=0
        )
    
    with col2:
        selected_treatment = st.selectbox(
            "Treatment:", 
            options=treatments if treatments else ["No treatments"],
            index=0
        )
    
    with col3:
        selected_time_points = st.selectbox(
            "Time Point:", 
            options=time_points if time_points else ["No time points"],
            index=0
        )
    
    with col4:
        selected_sample_type = st.selectbox(
            "Sample Type:", 
            options=sample_types if sample_types else ["No sample types"],
            index=0
        )
    with col5:
        selected_gender = st.selectbox(
            "Gender",
            options=(["All"] + gender) if gender else ["All"],
            index=0
        )
    
    #============================================ Plot Section =======================================================
    df_stats = get_statistical_subset(selected_condition, selected_sample_type, selected_time_points, selected_treatment, selected_gender)
    
    if df_stats is not None and not df_stats.empty:
        cell_populations = sorted(df_stats['population'].unique())
        
        with col6:
            pop = st.selectbox(
                "Cell Type:", 
                options=(["All"] + cell_populations) if cell_populations else ["All"],
                index=0
            )

        filtered_stats = df_stats
        if pop.lower() != "all":
            filtered_stats = df_stats[df_stats['population'] == pop]
        
        # chart
        fig = px.box(
            filtered_stats, 
            x="population", 
            y="percentage", 
            color="response",
            points="all",
            title="All Cell Populations: Responders vs Non-Responders",
            labels={"percentage": "Relative Frequency (%)", "response": "Response"}
        )
        st.plotly_chart(fig, width="stretch")
        
        #============================================ Data Summary Section =======================================================
        st.subheader("Data Summary")
        
        # Get unique subjects and their metadata for the filtered data
        unique_subjects = df_stats['subject'].unique().tolist()
        
        if unique_subjects:
            placeholders = ','.join(['?' for _ in unique_subjects])
            db.cursor.execute(
                f"SELECT subject, sex, response FROM subjects WHERE subject IN ({placeholders})",
                unique_subjects
            )
            subject_info = {row[0]: {'sex': row[1], 'response': row[2]} for row in db.cursor.fetchall()}
            
            # Total calculations
            total_samples = len(df_stats)
            total_subjects = len(unique_subjects)
            total_male = sum(1 for subj in unique_subjects if subject_info.get(subj, {}).get('sex') == 'M')
            total_female = sum(1 for subj in unique_subjects if subject_info.get(subj, {}).get('sex') == 'F')
            
            # Responder calculations
            responder_subjects = df_stats[df_stats['response'] == 'yes']['subject'].unique().tolist()
            responder_samples = len(df_stats[df_stats['response'] == 'yes'])
            responder_male = sum(1 for subj in responder_subjects if subject_info.get(subj, {}).get('sex') == 'M')
            responder_female = sum(1 for subj in responder_subjects if subject_info.get(subj, {}).get('sex') == 'F')
            
            # Non-responder calculations
            non_responder_subjects = df_stats[df_stats['response'] == 'no']['subject'].unique().tolist()
            non_responder_samples = len(df_stats[df_stats['response'] == 'no'])
            non_responder_male = sum(1 for subj in non_responder_subjects if subject_info.get(subj, {}).get('sex') == 'M')
            non_responder_female = sum(1 for subj in non_responder_subjects if subject_info.get(subj, {}).get('sex') == 'F')
            
            # Display in 3 columns
            col_total, col_responder, col_non_responder = st.columns(3)
            
            with col_total:
                st.metric("Total Samples", total_samples)
                st.metric("Total Subjects", total_subjects)
                st.write(f"**Males:** {total_male}")
                st.write(f"**Females:** {total_female}")
            
            with col_responder:
                st.metric("Responder Samples", responder_samples)
                st.metric("Responder Subjects", len(responder_subjects))
                st.write(f"**Males:** {responder_male}")
                st.write(f"**Females:** {responder_female}")
            
            with col_non_responder:
                st.metric("Non-Responder Samples", non_responder_samples)
                st.metric("Non-Responder Subjects", len(non_responder_subjects))
                st.write(f"**Males:** {non_responder_male}")
                st.write(f"**Females:** {non_responder_female}")

        #============================================ Statistics Section =======================================================
        st.subheader("Statistics")
        # Calculate t-tests for each cell population
        stats_results = []
        for cell_type in sorted(df_stats['population'].unique()):
            responders = df_stats[(df_stats['population'] == cell_type) & (df_stats['response'] == 'yes')]['percentage'].values
            non_responders = df_stats[(df_stats['population'] == cell_type) & (df_stats['response'] == 'no')]['percentage'].values
            
            avg_count = df_stats[df_stats['population'] == cell_type]['count'].mean()
            
            if len(responders) > 0 and len(non_responders) > 0:
                t_stat, p_value = ttest_ind(responders, non_responders, equal_var=False)
                significant = "Yes" if p_value < 0.05 else "No" # type: ignore 
                stats_results.append({
                    "Cell Type": cell_type,
                    "T-Statistic": f"{t_stat:.4f}",
                    "P-Value": f"{p_value:.6f}",
                    "Avg Count": f"{avg_count:.2f}",
                    "Significant (α=0.05)": significant
                })

        if stats_results:
            stats_df = pd.DataFrame(stats_results).style.map(conditional_colors)
            st.dataframe(stats_df, width='stretch', height=223)
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

