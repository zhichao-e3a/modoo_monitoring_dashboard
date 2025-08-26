from database.queries import RECRUITED
from database.SQLDBConnector import SQLDBConnector
from database.MongoDBConnector import MongoDBConnector

from utils.zc.zc_helpers import *

import streamlit as st

import time
import json
import asyncio

from websocket import create_connection, WebSocketTimeoutException

st.set_page_config(page_title="Recruited Pipeline", layout="wide")

if "main_csv" not in st.session_state:
    st.session_state.main_csv = None

if "pre_csv" not in st.session_state:
    st.session_state.pre_csv = None

if "start_pipeline" not in st.session_state:
    st.session_state.start_pipeline = None

if "job_id" not in st.session_state:
    st.session_state.job_id = None

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

    if st.session_state.start_pipeline:

        with st.status(label="Merging data", expanded=True) as status:

            bar = st.progress(0)

            # Start merge data
            db      = SQLDBConnector()
            mongo   = MongoDBConnector()

            place.write(":material/database: Querying MySQL")
            sql_df  = db.query_to_dataframe(
                RECRUITED.format(
                    numbers=get_query_string(main_df)[:-1],
                    start="'2025-03-01 00:00:00'",
                    end=f"'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'"
                )
            )
            place.write(f":material/done_outline: Queried {len(sql_df)} rows, {len(sql_df.columns)} columns")

            formatted_excel = format_excel_data(main_df, pre_df)

            merged_list     = merge_excel_sql(formatted_excel, sql_df)
            rows_added_raw  = len(merged_list) - asyncio.run(mongo.count_documents("rec_merged_data"))
            place.write(":material/database_upload: Uploading to MongoDB (rec_merged_data)")
            asyncio.run(mongo.upsert_records(merged_list, "rec_merged_data"))
            place.write(f":material/done_outline: Uploaded {rows_added_raw} rows to MongoDB (rec_raw_data)")
            # End merge data

            # Start get job ID
            response = requests.post("http://127.0.0.1:8000/run_rec_pipeline")
            response.raise_for_status()
            st.session_state.job_id = response.json()["job_id"]
            # End get job ID

            bar.progress(1/7)
            status.update(label=f"`{st.session_state.job_id}`")
            st.toast(f"Pipeline started: {st.session_state.job_id}")

            ws = create_connection(
                f"ws://127.0.0.1:8000/ws/status/{st.session_state.job_id}",
                origin="http://localhost:8501",
                timeout=1,
            )

            ws.settimeout(1)

            try:
                while True:
                    try:
                        raw = ws.recv()
                    except WebSocketTimeoutException:
                        time.sleep(0.05)
                        continue

                    status_response = json.loads(raw)

                    if status_response.get("type") == "status":

                        progress    = int(status_response.get("progress", 0))
                        log_message = status_response.get("message", "")
                        state       = status_response.get("state", "")

                        bar.progress(progress, text=f"{progress}%")

                        place.write(f"{log_message}\n")

                        if state == "completed":
                            status.update(state="complete")
                            st.balloons()
                            break

                        if state in ("failed", "unknown"):
                            status.update(label="Pipeline failed", state="error")
                            st.error("Pipeline failed")
                            break
            finally:
                ws.close()

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

            st.session_state.start_pipeline = True
            st.rerun()

        elif reupload_button:

            st.session_state.csv        = None
            st.session_state.pre_csv    = None
            st.session_state.post_csv   = None
            st.rerun()

