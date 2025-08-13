from helper import *

import json
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Recruited Patients", page_icon=":hospital:", layout="wide", initial_sidebar_state="expanded")

st.title("Recruited Patients")

st.divider()

with st.container(border=True):

    start_col, end_col = st.columns(2)

    with start_col:

        start = st.date_input(
            label="Start Date",
            value="2025-03-01 00:00:00",
            min_value="2025-03-01 00:00:00"
        )

    with end_col:

        end = st.date_input(
            label="End Date",
            value="today",
            min_value="2025-03-01 00:00:00"
        )

with st.container():

    with st.spinner("Fetching data..."):

        print(start, end)

        summary_df, n_unique_patients = get_patient_records(start=f"'{start} 00:00:00'", end=f"'{end} 00:00:00'")
        st.dataframe(summary_df)
        st.write(f"{n_unique_patients} unique patients in total from {start} to {end}")
        st.write(f"{sum(summary_df["measurements"])} measurements in total from {start} to {end}")