from cache import get_mongo_connector

from pathlib import Path

import streamlit as st

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

st.session_state.logged_in = True

_ = get_mongo_connector()

ROOT = Path(__file__).resolve().parent

LOGIN               = ROOT / "pages" / "login.py"
PATIENT_ANALYTICS   = ROOT / "pages" / "patient_analytics.py"

login_page             = st.Page(LOGIN, title="Login")
patient_analytics_page = st.Page(PATIENT_ANALYTICS, title="Patient Analytics", icon=":material/person:")

if st.session_state.logged_in:
    pg = st.navigation(
        [
            patient_analytics_page
        ],
        position="sidebar"
    )
else:
    pg = st.navigation([login_page], position="hidden")

pg.run()