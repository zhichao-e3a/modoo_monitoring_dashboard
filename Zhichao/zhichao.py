from utils.zc.zc_helpers import *

import streamlit as st

import time

from websocket import create_connection, WebSocketTimeoutException

st.set_page_config(page_title="Zhichao", page_icon=":hospital:", layout="wide")
st.title("Run Data Pipeline")
st.divider()

if "job_id" not in st.session_state:
    st.session_state.job_id = None

if "logs" not in st.session_state:
    st.session_state.logs = []

with st.container():

    left, mid, right = st.columns(3)

    with left:

        if st.button("Run", width="stretch"):
            start = time.perf_counter()
            response = requests.post("http://127.0.0.1:8000/run_pipeline")
            response.raise_for_status()
            st.session_state.job_id = response.json()["job_id"]
            st.toast(f"Pipeline started: {st.session_state.job_id}")

    with mid:

        if st.button("Restart", width="stretch"):
            st.snow()

    with right:

        if st.button("View Logs", width="stretch"):
            st.toast("Feature not done hehe")

if st.session_state.job_id:

    ws = create_connection(
        f"ws://127.0.0.1:8000/ws/status/{st.session_state.job_id}",
        origin="http://localhost:8501",
        timeout=1,
    )

    ws.settimeout(1)

    with st.status(label=f"`{st.session_state.job_id}`", expanded=True) as status:

        if st.button("Stop Running (Restarts Session)"):
            for key in st.session_state.keys():
                if key != "logged_in":
                    del st.session_state[key]
            st.rerun()

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

                    if log_message not in st.session_state.logs:
                        print(log_message)
                        st.session_state.logs.append(log_message)

                    if state == "completed":
                        end = time.perf_counter()
                        status.update(state="complete")
                        status_message = f"Pipeline completed in {(end - start):.2f} seconds"
                        st.balloons()
                        break

                    if state in ("failed", "unknown"):
                        status.update(label="Pipeline failed", state="error")
                        st.error("Pipeline failed")
                        break

                # time.sleep(5)
        finally:
            ws.close()
