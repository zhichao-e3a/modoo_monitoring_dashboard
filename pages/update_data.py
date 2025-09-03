from database.MongoDBConnector import MongoDBConnector

from utils.data_processing import *

import streamlit as st

import asyncio

st.set_page_config(page_title="Update Model Data", layout="wide")
st.title("Update Model Data")
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

        mongo   = MongoDBConnector(remote=False)

        all_patients = asyncio.run(
            mongo.get_all_documents(coll_name="consolidated_patients")
        )
        rec_patients, hist_patients = [], []

        for patient in all_patients:

            data_origin = patient["data_origin"]

            if data_origin == "recruited":
                rec_patients.append(patient)
            elif data_origin == "historical":
                hist_patients.append(patient)

        rec_measurements    = asyncio.run(
            mongo.get_all_documents(
                coll_name   = "rec_processed_data",
                query       = {"mobile" : {"$in" : [i["_id"] for i in rec_patients]}}
            )
        )

        hist_measurements   = asyncio.run(
            mongo.get_all_documents(
                coll_name   = "hist_processed_data",
                query       = {"mobile" : {"$in" : [i["_id"] for i in hist_patients]}}
            )
        )

        rec_data    = consolidate_data(rec_patients, rec_measurements)
        hist_data   = consolidate_data(hist_patients, hist_measurements)

        asyncio.run(mongo.upsert_records_hashed(rec_data, "consolidated_data"))
        asyncio.run(mongo.upsert_records_hashed(hist_data, "consolidated_data"))
