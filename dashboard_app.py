from pathlib import Path

import streamlit as st

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

st.session_state.logged_in = True

ROOT = Path(__file__).resolve().parent

LOGIN               = ROOT / "pages" / "login.py"
DATA_MONITORING     = ROOT / "pages" / "etl_monitoring.py"
UPDATE_CONSOLIDATED = ROOT / "pages" / "update_data.py"
UPDATE_RECRUITED    = ROOT / "pages" / "update_patients.py"
UPDATE_HISTORICAL   = ROOT / "pages" / "run_pipeline.py"

login_page                  = st.Page(LOGIN, title="Login")
update_consolidated_page    = st.Page(UPDATE_RECRUITED, title="Update Patients", icon=":material/update:")
run_pipeline_page           = st.Page(UPDATE_HISTORICAL, title="Run Data Pipeline", icon=":material/automation:")
update_measurements_page    = st.Page(UPDATE_CONSOLIDATED, title="Update Model Data", icon=":material/database_upload:")
data_monitoring_page        = st.Page(DATA_MONITORING, title="Data Monitoring", icon=":material/monitor_heart:")

if st.session_state.logged_in:
    pg = st.navigation(
        {
            "Data Pipeline" : [
                update_consolidated_page,
                run_pipeline_page,
                update_measurements_page,
                data_monitoring_page,
            ]
        },
        position="sidebar"
    )
else:
    pg = st.navigation([login_page], position="hidden")

pg.run()