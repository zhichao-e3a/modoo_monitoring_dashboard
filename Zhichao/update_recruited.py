from database.MongoDBConnector import MongoDBConnector

from utils.zc.zc_helpers import *

import streamlit as st

import asyncio

st.set_page_config(page_title="Update Recruited Patients", layout="wide")
st.title("Update Recruited Patients")
st.divider()

if "main_csv" not in st.session_state:
    st.session_state.main_csv = None

if "pre_csv" not in st.session_state:
    st.session_state.pre_csv = None

if "upload_data" not in st.session_state:
    st.session_state.upload_data = None

if not st.session_state.main_csv:

    st.session_state.main_csv = st.file_uploader(
        "Upload Recruited Patients XLSX file",
        type = "xlsx",
        accept_multiple_files = False
    )

if not st.session_state.pre_csv:

    st.session_state.pre_csv = st.file_uploader(
        "Upload Pre-Survey CSV file",
        type = "csv",
        accept_multiple_files = False
    )

if st.session_state.main_csv and st.session_state.pre_csv:

    place       = st.empty()

    main_file   = st.session_state.main_csv
    main_file.seek(0)
    main_df     = pd.read_excel(main_file)

    pre_file    = st.session_state.pre_csv
    pre_file.seek(0)
    pre_df      = pd.read_csv(pre_file)

    if st.session_state.upload_data:

        mongo   = MongoDBConnector()

        formatted_excel = format_excel_data(main_df, pre_df)

        rows_added_raw = len(formatted_excel) - asyncio.run(mongo.count_documents("consolidated_patients"))

        st.write(":material/database_upload: Uploading to MongoDB (consolidated_patients)")
        asyncio.run(mongo.upsert_records(formatted_excel, "consolidated_patients"))
        st.balloons()
        st.write(f":material/done_outline: Uploaded {rows_added_raw} rows to MongoDB (consolidated_patients)")

        st.session_state.main_csv       = None
        st.session_state.pre_csv        = None
        st.session_state.upload_data    = None

        st.rerun()

    else:

        with place.container():

            left, right = st.columns(2)

            with left:
                continue_button = st.button("Continue", width="stretch")

            with right:
                reupload_button = st.button("Reupload", width="stretch")

            st.dataframe(main_df)
            st.dataframe(pre_df)

        if continue_button:

            st.session_state.upload_data = True
            st.rerun()

        elif reupload_button:

            st.session_state.main_csv       = None
            st.session_state.pre_csv        = None
            st.session_state.upload_data    = None
            st.rerun()