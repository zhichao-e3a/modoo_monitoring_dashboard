from database.MongoDBConnector import MongoDBConnector

from utils.zc.zc_helpers import *

import streamlit as st

import asyncio

st.set_page_config(page_title="Update Consolidated Database", layout="wide")
st.title("Update Consolidated Data")
st.divider()

if "start" not in st.session_state:
    st.session_state.start = None

with st.container(vertical_alignment="center", horizontal_alignment="center"):

    # Each button triggers a re-run and will flag it as True
    left, right = st.columns(2)

    with left:
        run_button      = st.button("Run", width="stretch")

    with right:
        restart_button  = st.button("Restart", width="stretch")

if run_button:
    st.session_state.start = True

if restart_button:
    st.session_state.start = None

if st.session_state.start:

    with st.status(label="Merging data", expanded=True) as status:

        mongo   = MongoDBConnector()

        all_patients = asyncio.run(mongo.get_all_documents(coll_name="consolidated_patients"))
        rec_patients, hist_patients = [], []

        for patient in all_patients:
            if patient["data_origin"] == "recruited":
                rec_patients.append(patient)
            elif patient["data_origin"] == "historical":
                hist_patients.append(patient)

        rec_measurements    = asyncio.run(mongo.get_all_documents(
            coll_name       = "rec_processed_data",
            query           = {"mobile" : {"$in" : [i["_id"] for i in rec_patients]}}
        ))

        hist_measurements   = asyncio.run(mongo.get_all_documents(
            coll_name   = "hist_processed_data",
            query       = {"mobile" : {"$in" : [i["_id"] for i in hist_patients]}}
        ))

        rec_data    = consolidate_data(rec_patients, rec_measurements, "recruited")
        hist_data   = consolidate_data(hist_patients, hist_measurements, "historical")

        asyncio.run(mongo.upsert_records(rec_data, "consolidated_data"))
        asyncio.run(mongo.upsert_records(hist_data, "consolidated_data"))
