from __future__ import annotations

from resources.styles import BADGE_CSS

import streamlit as st

import json
import time
import contextlib
from dataclasses import dataclass

import requests
from websocket import create_connection, WebSocketTimeoutException, WebSocketConnectionClosedException

PORT        = 8502
API_BASE    = f"http://127.0.0.1:{PORT}/v1/jobs"
WS_BASE     = f"ws://127.0.0.1:{PORT}/v1/ws"
TIMEOUT     = (
    5,  # Connect
    30  # Read
)

st.set_page_config(
    page_title="Run Data Pipeline",
    layout="wide"
)

st.markdown(BADGE_CSS, unsafe_allow_html=True)

if "choice" not in st.session_state:
    st.session_state.choice: str | None = None
if "job_id_pipeline" not in st.session_state:
    st.session_state.job_id_pipeline: str | None = None
if "progress" not in st.session_state:
    st.session_state.progress: int = 0

@dataclass
class ApiError(Exception):
    message: str
    status_code: int | None = None

def start_job(choice: str) -> str:

    try:
        resp = requests.post(
            url     = f"{API_BASE}/pipeline_job/{choice}",
            timeout = TIMEOUT
        )

        if resp.status_code >= 400:
            raise ApiError(
                message = f"Start failed: HTTP {resp.status_code} - {resp.text[:200]}",
                status_code = resp.status_code
            )

        data = resp.json()

        return data.get("job_id")

    except requests.RequestException as e:

        raise ApiError(
             message = f"Start failed: {e}"
        )

def cancel_job(job_id: str) -> None:

    try:
        resp = requests.post(
            url     = f"{API_BASE}/cancel_job/{job_id}",
            timeout = TIMEOUT
        )

        if resp.status_code >= 400:
            raise ApiError(
                message = f"Cancel failed: HTTP {resp.status_code} - {resp.text[:200]}",
                status_code = resp.status_code
            )

    except requests.RequestException as e:

        raise ApiError(
            message = f"Cancel failed: {e}"
        )

st.title("Run Data Pipeline")
st.caption("Run this before updating model data")

st.markdown('<hr class="soft"/>', unsafe_allow_html=True)

if not st.session_state.choice:

    st.subheader("Choose Data Origin")

    choice = st.segmented_control(
        "Data Origin",
        options=["Recruited", "Historical"],
        selection_mode="single",
        width="stretch",
        key="choice_tmp"
    )

    st.write("")

    start = st.button("Continue", type="primary", use_container_width=True)

    if start:
        if choice:
            st.session_state.choice = "rec" if choice == "Recruited" else "hist"
            st.rerun()
        else:
            st.warning("Please pick an option to continue")

else:

    current = "Recruited" if st.session_state.choice == "rec" else "Historical"
    st.markdown(f"<span class='badge run'>Dataset: {current}</span>", unsafe_allow_html=True)

    colA, colB, colC = st.columns(3)

    with colA:
        run_btn = st.button("Run", type="primary", use_container_width=True)
    with colB:
        cancel_btn = st.button("Cancel", use_container_width=True)
    with colC:
        restart_btn = st.button("Restart", use_container_width=True)

    if run_btn:
        try:
            with st.spinner("Starting pipeline"):
                st.session_state.job_id_pipeline = start_job(st.session_state.choice)
                st.session_state.progress = 0
            st.toast(f"Pipeline started: `{st.session_state.job_id_pipeline}`")
        except ApiError as e:
            st.error(e.message)

    if cancel_btn and st.session_state.job_id_pipeline:
        try:
            with st.spinner("Cancelling job"):
                cancel_job(st.session_state.job_id_pipeline)
            st.info("Please restart")
        except ApiError as e:
            st.error(e.message)

    if restart_btn:
        with contextlib.suppress(Exception):
            if st.session_state.job_id_pipeline:
                cancel_job(st.session_state.job_id_pipeline)
        st.session_state.choice = None
        st.session_state.job_id_pipeline = None
        st.session_state.progress = 0
        st.rerun()

    if not cancel_btn and st.session_state.job_id_pipeline:

        progress_bar = st.progress(st.session_state.progress)
        status_box = st.container()

        ws = None

        try:
            ws = create_connection(
                f"{WS_BASE}/status/{st.session_state.job_id_pipeline}",
                origin="http://localhost:8501",
                timeout=10,
            )
            ws.settimeout(1)

            with status_box:
                with st.status(label=f"`{st.session_state.job_id_pipeline}`", expanded=True) as status:
                    while True:
                        try:
                            raw = ws.recv()
                        except WebSocketTimeoutException:
                            time.sleep(0.05)
                            continue
                        except WebSocketConnectionClosedException:
                            st.warning("WebSocket closed by server.")
                            break

                        try:
                            msg = json.loads(raw)
                        except json.JSONDecodeError:
                            continue

                        if msg.get("type") == "status":
                            progress = int(msg.get("progress", 0))
                            message  = msg.get("message", "")
                            state    = msg.get("state", "")

                            st.session_state.progress = progress
                            progress_bar.progress(progress, text=f"{progress}%")

                            st.write(message)

                            if state == "completed":
                                progress_bar.progress(100)
                                status.update(state="complete")
                                st.balloons()
                                break

                            elif state in ("failed", "error"):
                                status.update(label="Pipeline failed", state="error")
                                st.error("Pipeline failed. Check server logs for details.")
                                break

        except Exception as e:
            st.error(f"Live updates failed: {e}")

        finally:
            with contextlib.suppress(Exception):
                if ws is not None:
                    ws.close()

st.markdown('<hr class="soft"/>', unsafe_allow_html=True)
