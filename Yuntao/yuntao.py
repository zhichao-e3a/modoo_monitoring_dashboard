from utils.yt.custom_data_page import *
from utils.yt.mongo_reader import *

import streamlit as st

import os

# Configure Streamlit to handle large files - this must be the first st command
st.set_page_config(
    page_title="Data Analysis Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# Display logos in sidebar
logo_path = "../resources/logo.png"
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, width=224)

# Increase the upload limit (set to 1GB)
st.cache_data.clear()
st._config.set_option('server.maxUploadSize', 1024)

# Create page selector
page = st.sidebar.selectbox(
    "Data Source",
    ["CSV", "MongoDB"],
    format_func=lambda x: f"Load from {x}"
)

# Reset settings button
if st.sidebar.button("Reset All Settings"):
    # Create a copy of keys since we'll be modifying the dict during iteration
    keys = list(st.session_state.keys())
    for key in keys:
        del st.session_state[key]
    st.rerun()

st.sidebar.markdown("---")

# Display selected page
if page == "CSV":
    show_custom_data_page()
else:
    show_mongodb_data_page()

os.get