import streamlit as st

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

login_page  = st.Page("pages/login.py", title="Login")
zc_page     = st.Page("Zhichao/zhichao.py", title="Run Pipeline", icon=":material/automation:")
yt_page     = st.Page("Yuntao/yuntao.py", title="Visualisations", icon=":material/bar_chart:")

if st.session_state.logged_in:
    pg = st.navigation(
        {
            "Data Pipeline" : [zc_page],
            "Data Analysis" : [yt_page]
        },
        position="sidebar"
    )
else:
    pg = st.navigation([login_page], position="hidden")

pg.run()