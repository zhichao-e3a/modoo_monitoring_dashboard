import streamlit as st

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

login_page                  = st.Page("pages/login.py", title="Login")
update_recruited_page       = st.Page("Zhichao/update_recruited.py", title="Update Recruited Patients", icon=":material/update:")
historical_pipeline_page    = st.Page("Zhichao/run_pipeline.py", title="Run Database Pipeline", icon=":material/automation:")
# recruited_pipeline_page     = st.Page("Zhichao/recruited_pipeline.py", title="Recruited Pipeline", icon=":material/man:")
analysis_page               = st.Page("Yuntao/yuntao.py", title="Visualisations", icon=":material/bar_chart:")

if st.session_state.logged_in:
    pg = st.navigation(
        {
            "Data Pipeline" : [
                update_recruited_page,
                historical_pipeline_page,
                # recruited_pipeline_page
            ],
            "Data Analysis" : [analysis_page]
        },
        position="sidebar"
    )
else:
    pg = st.navigation([login_page], position="hidden")

pg.run()