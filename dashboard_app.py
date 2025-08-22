import streamlit as st

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

login_page                  = st.Page("pages/login.py", title="Login")
historical_pipeline_page    = st.Page("Zhichao/historical_pipeline.py", title="Historical Pipeline", icon=":material/elderly:")
recruited_pipeline_page     = st.Page("Zhichao/recruited_pipeline.py", title="Recruited Pipeline", icon=":material/man:")
analysis_page               = st.Page("Yuntao/yuntao.py", title="Visualisations", icon=":material/bar_chart:")

if st.session_state.logged_in:
    pg = st.navigation(
        {
            "Data Pipeline" : [
                historical_pipeline_page,
                recruited_pipeline_page
            ],
            "Data Analysis" : [analysis_page]
        },
        position="sidebar"
    )
else:
    pg = st.navigation([login_page], position="hidden")

pg.run()