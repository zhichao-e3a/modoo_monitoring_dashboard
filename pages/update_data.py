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

        mongo   = MongoDBConnector(remote=True)

        all_patients = asyncio.run(
            mongo.get_all_documents(coll_name="patients_unified")
        )

        rec_patients, hist_patients = [], []
        valid_patients = 0

        for patient in all_patients:

            data_origin = patient["recruitment_type"]
            onset       = patient["onset_datetime"]
            delivery    = patient["delivery_type"]

            if data_origin == "recruited":
                rec_patients.append(patient)

            elif data_origin == "historical":
                hist_patients.append(patient)

            if onset and delivery != "c_section":
                valid_patients += 1

        st.write(f":material/groups: {len(rec_patients)} RECRUITED PATIENTS")
        st.write(f":material/groups: {len(hist_patients)} HISTORICAL PATIENTS")
        st.write(f":material/sentiment_satisfied: {valid_patients} VALID PATIENTS")

        rec_measurements    = asyncio.run(
            mongo.get_all_documents(
                coll_name   = "rec_processed_data",
                query       = {
                    "mobile" : {
                        "$in" : [i["patient_id"] for i in rec_patients]
                    }
                }
            )
        )

        hist_measurements   = asyncio.run(
            mongo.get_all_documents(
                coll_name   = "hist_processed_data",
                query       = {
                    "mobile" : {
                        "$in" : [i["patient_id"] for i in hist_patients]
                    }
                }
            )
        )

        st.write(f":material/done_outline: QUERIED {len(rec_measurements)+len(hist_measurements)} MEASUREMENTS")

        rec_data, rec_skipped   = consolidate_data(rec_measurements, rec_patients)
        hist_data, hist_skipped = consolidate_data(hist_measurements, hist_patients)

        st.write(f":material/person_alert: SKIPPED {rec_skipped["no_onset"]+hist_skipped["no_onset"]} DUE TO NO ONSET DATE")
        st.write(f":material/person_alert: SKIPPED {rec_skipped["c_section"]+hist_skipped["c_section"]} DUE TO C-SECTION")

        asyncio.run(mongo.upsert_records_hashed(rec_data, "consolidated_data"))
        asyncio.run(mongo.upsert_records_hashed(hist_data, "consolidated_data"))

        st.write(f":material/done_outline: UPLOADED {len(rec_data)+len(hist_data)} MEASUREMENTS TO MONGODB (consolidated_data)")