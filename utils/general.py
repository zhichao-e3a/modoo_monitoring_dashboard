from config.configs import ST_CRED

import streamlit as st

def verify_login(username, password):

    if not username:
        st.warning("Please enter your username")

    elif not password:
        st.warning("Please enter your password")

    elif username == ST_CRED["ST_USER"] and password == ST_CRED["ST_PASS"]:
        st.success("Successfully logged in")
        st.session_state.logged_in = True
        st.rerun()

    else:
        st.warning("Wrong username or password")