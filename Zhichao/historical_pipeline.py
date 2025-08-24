from utils.zc.zc_helpers import *

import streamlit as st

import time
import json

from websocket import create_connection, WebSocketTimeoutException

st.set_page_config(page_title="Historical Pipeline", layout="wide")

st.session_state.job_id = None

with st.container(vertical_alignment="center", horizontal_alignment="center"):

    # Each button triggers a re-run and will flag it as True
    left, mid, right = st.columns(3)

    with left:
        run_button      = st.button("Run", width="stretch")

    with mid:
        restart_button  = st.button("Restart", width="stretch")

    with right:
        logs_button     = st.button("View Logs", width="stretch")

if run_button:

    response = requests.post("http://127.0.0.1:8000/run_hist_pipeline")
    response.raise_for_status()
    st.session_state.job_id = response.json()["job_id"]

if restart_button:

    st.snow()
    st.toast(f"Session restarted")
    st.session_state.job_id = None

if logs_button:

    st.toast("Feature not done hehe")

if st.session_state.job_id:

    st.toast(f"Pipeline started: {st.session_state.job_id}")

    ws = create_connection(
        f"ws://127.0.0.1:8000/ws/status/{st.session_state.job_id}",
        origin="http://localhost:8501",
        timeout=1,
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
                        st.write(f"{log_message}\n")

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
