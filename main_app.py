from pathlib import Path

import streamlit as st

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

st.session_state.logged_in = True

ROOT = Path(__file__).resolve().parent

LOGIN               = ROOT / "pages" / "login.py"
PATIENT_ANALYTICS   = ROOT / "pages" / "patient_analytics.py"
MEASUREMENTS_EDA    = ROOT / "pages" / "eda.py"

login_page             = st.Page(LOGIN, title="Login")
patient_analytics_page = st.Page(PATIENT_ANALYTICS, title="Patient Analytics", icon=":material/person:")
measurements_eda_page  = st.Page(MEASUREMENTS_EDA, title="Data Analysis", icon=":material/frame_inspect:")

if st.session_state.logged_in:
    pg = st.navigation(
        [
            patient_analytics_page,
            measurements_eda_page
        ],
        position="sidebar"
    )
else:
    pg = st.navigation([login_page], position="hidden")

pg.run()