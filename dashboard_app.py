from pathlib import Path

import streamlit as st

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

st.session_state.logged_in = True

ROOT = Path(__file__).resolve().parent

LOGIN               = ROOT / "pages" / "login.py"
PATIENT_ANALYTICS   = ROOT / "pages" / "patient_analytics.py"
UPDATE_MODEL_DATA   = ROOT / "pages" / "run_update.py"
RUN_PIPELINE        = ROOT / "pages" / "run_pipeline.py"
DATA_MONITORING     = ROOT / "pages" / "etl_monitoring.py"

login_page             = st.Page(LOGIN, title="Login")
patient_analytics_page = st.Page(PATIENT_ANALYTICS, title="Patient Analytics", icon=":material/person:")
update_model_data_page = st.Page(UPDATE_MODEL_DATA, title="Update Model Data", icon=":material/database_upload:")
run_pipeline_page      = st.Page(RUN_PIPELINE, title="Run Data Pipeline", icon=":material/automation:")
data_monitoring_page   = st.Page(DATA_MONITORING, title="Data Monitoring", icon=":material/monitor_heart:")

if st.session_state.logged_in:
    pg = st.navigation(
        {
            "ETL" : [
                patient_analytics_page,
                update_model_data_page,
                run_pipeline_page,
                # data_monitoring_page
            ]
        },
        position="sidebar"
    )
else:
    pg = st.navigation([login_page], position="hidden")

pg.run()