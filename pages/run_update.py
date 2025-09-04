PORT = 8502

import streamlit as st

import time
import json
import requests

from websocket import create_connection, WebSocketTimeoutException, WebSocketConnectionClosedException

st.set_page_config(page_title="Update Model Data", layout="wide")
st.title("Update Model Data")
st.divider()

if "job_id" not in st.session_state:
    st.session_state.job_id = None

with st.container(vertical_alignment="center", horizontal_alignment="center"):

    # Each button triggers a re-run and will flag it as True
    left, right = st.columns(2)

    with left:
        run_button      = st.button("Run", width="stretch")

    with right:
        restart_button  = st.button("Restart", width="stretch")

if run_button:

    response = requests.post(
        f"http://127.0.0.1:{PORT}/v1/api/consolidate_job"
    )
    response.raise_for_status()
    st.session_state.job_id = response.json()["job_id"]

if restart_button:

    if st.session_state.job_id:

        response = requests.post(
            f"http://127.0.0.1:{PORT}/v1/api/cancel_job/{st.session_state.job_id}"
        )
        response.raise_for_status()
        st.session_state.job_id = None

    st.rerun()

if st.session_state.job_id:

    st.toast(f"Consolidate data: {st.session_state.job_id}")

    ws = create_connection(
        f"ws://127.0.0.1:{PORT}/v1/ws/status/{st.session_state.job_id}",
        origin="http://localhost:8501",
        timeout=10,
    )

    ws.settimeout(1)

    with st.status(label=f"`{st.session_state.job_id}`", expanded=True) as status:

        bar = st.progress(0)

        try:
            while True:
                try:
                    raw = ws.recv()
                except WebSocketTimeoutException:
                    time.sleep(0.05)
                    continue

                status_response = json.loads(raw)
                print(status_response)

                if status_response.get("type") == "status":

                    progress = int(status_response.get("progress", 0))
                    log_message = status_response.get("message", "")
                    state = status_response.get("state", "")

                    bar.progress(progress, text=f"{progress}%")

                    with st.empty() as empty:
                        st.write(log_message)

                    if state == "completed":
                        bar.progress(100)
                        status.update(state="complete")
                        st.balloons()
                        break

                    if state in ("failed", "error"):
                        status.update(label="Pipeline failed", state="error")
                        st.error("Pipeline failed")
                        break

        finally:
            ws.close()