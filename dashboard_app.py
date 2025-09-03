from pathlib import Path

import streamlit as st

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

st.session_state.logged_in = True

ROOT = Path(__file__).resolve().parent

LOGIN               = ROOT / "pages" / "login.py"
DATA_MONITORING     = ROOT / "pages" / "etl_monitoring.py"
UPDATE_CONSOLIDATED = ROOT / "pages" / "update_data.py"
UPDATE_HISTORICAL   = ROOT / "pages" / "run_pipeline.py"

login_page                  = st.Page(LOGIN, title="Login")
update_measurements_page    = st.Page(UPDATE_CONSOLIDATED, title="Update Model Data", icon=":material/database_upload:")
run_pipeline_page           = st.Page(UPDATE_HISTORICAL, title="Run Data Pipeline", icon=":material/automation:")
data_monitoring_page        = st.Page(DATA_MONITORING, title="Data Monitoring", icon=":material/monitor_heart:")

if st.session_state.logged_in:
    pg = st.navigation(
        {
            "Data Pipeline" : [
                update_measurements_page,
                run_pipeline_page,
                data_monitoring_page,
            ]
        },
        position="sidebar"
    )
else:
    pg = st.navigation([login_page], position="hidden")

pg.run()