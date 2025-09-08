PORT = 8502

import streamlit as st

import time
import json
import requests

from websocket import create_connection, WebSocketTimeoutException

st.set_page_config(page_title="Run Data Pipeline", layout="wide")
st.title("Run Data Pipeline")
st.divider()

if "choice" not in st.session_state:
    st.session_state.choice = None

if "job_id" not in st.session_state:
    st.session_state.job_id = None

if not st.session_state.choice:

    with st.container(vertical_alignment="center", horizontal_alignment="center"):

        left, right = st.columns(2)

        with left:
            recruited_button = st.button("Recruited", width="stretch")

        with right:
            historical_button = st.button("Historical", width="stretch")

        if recruited_button:
            st.session_state.choice = "rec"
            st.rerun()

        elif historical_button:
            st.session_state.choice = "hist"
            st.rerun()

else:
    with st.container(vertical_alignment="center", horizontal_alignment="center"):

        # Each button triggers a re-run and will flag it as True
        left, right = st.columns(2)

        with left:
            run_button      = st.button("Run", width="stretch")

        with right:
            restart_button  = st.button("Restart", width="stretch")

    if run_button:

        response = requests.post(
            f"http://127.0.0.1:{PORT}/v1/api/pipeline_job/{st.session_state.choice}"
        )
        response.raise_for_status()
        st.session_state.job_id = response.json()["job_id"]

    if restart_button:

        if st.session_state.job_id:

            response = requests.post(
                f"http://127.0.0.1:{PORT}/v1/api/cancel_job/{st.session_state.job_id}"
            )
            response.raise_for_status()
            st.session_state.choice = None
            st.session_state.job_id = None

        else:
            st.session_state.choice = None

        st.rerun()

    if st.session_state.job_id:

        st.toast(f"Pipeline started: {st.session_state.job_id}")

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

                    if status_response.get("type") == "status":

                        progress    = int(status_response.get("progress", 0))
                        log_message = status_response.get("message", "")
                        state       = status_response.get("state", "")

                        bar.progress(progress, text=f"{progress}%")

                        with st.empty() as empty:
                            st.write(f"{log_message}")

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
