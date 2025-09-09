from __future__ import annotations

from resources.styles import BADGE_CSS

import streamlit as st

import json
import time
import contextlib
from dataclasses import dataclass

import requests
from websocket import create_connection, WebSocketTimeoutException, WebSocketConnectionClosedException

PORT = 8502
API_BASE = f"http://127.0.0.1:{PORT}/v1/api"
WS_BASE  = f"ws://127.0.0.1:{PORT}/v1/ws"
TIMEOUT  = (
    5,
    30
)

st.set_page_config(
    page_title="Update Model Data",
    layout="wide"
)

st.markdown(BADGE_CSS, unsafe_allow_html=True)

if "job_id_consolidate" not in st.session_state:
    st.session_state.job_id_consolidate: str | None = None
if "progress_consolidate" not in st.session_state:
    st.session_state.progress_consolidate: int = 0

@dataclass
class ApiError(Exception):
    message: str
    status_code: int | None = None

def start_consolidate_job() -> str:
    try:
        resp = requests.post(f"{API_BASE}/consolidate_job", timeout=TIMEOUT)
        if resp.status_code >= 400:
            raise ApiError(f"Start failed: HTTP {resp.status_code} - {resp.text[:200]}", resp.status_code)
        return resp.json().get("job_id")
    except requests.RequestException as e:
        raise ApiError(f"Start failed: {e}")

def cancel_job(job_id: str) -> None:
    try:
        resp = requests.post(f"{API_BASE}/cancel_job/{job_id}", timeout=TIMEOUT)
        if resp.status_code >= 400:
            raise ApiError(f"Cancel failed: HTTP {resp.status_code} - {resp.text[:200]}", resp.status_code)
    except requests.RequestException as e:
        raise ApiError(f"Cancel failed: {e}")

st.title("Update Model Data")
st.caption("Consolidate and refresh model-ready data")

st.markdown('<hr class="soft"/>', unsafe_allow_html=True)

colA, colB, colC = st.columns([1,1,1])
with colA:
    run_btn = st.button("Run", type="primary", use_container_width=True)
with colB:
    cancel_btn = st.button("Cancel", use_container_width=True)
with colC:
    restart_btn = st.button("Restart", use_container_width=True)

if run_btn:
    try:
        with st.spinner("Starting consolidate job"):
            st.session_state.job_id_consolidate = start_consolidate_job()
            st.session_state.progress_consolidate = 0
        st.toast(f"Consolidate job started: `{st.session_state.job_id_consolidate}`")
    except ApiError as e:
        st.error(e.message)

if cancel_btn and st.session_state.job_id_consolidate:
    try:
        with st.spinner("Cancelling job"):
            cancel_job(st.session_state.job_id_consolidate)
        st.info("Please restart")
    except ApiError as e:
        st.error(e.message)

if restart_btn:
    with contextlib.suppress(Exception):
        if st.session_state.job_id_consolidate:
            cancel_job(st.session_state.job_id_consolidate)
    st.session_state.job_id_consolidate = None
    st.session_state.progress_consolidate = 0
    st.rerun()

if not cancel_btn and st.session_state.job_id_consolidate:

    progress_bar = st.progress(st.session_state.progress_consolidate)
    status_box   = st.container()

    ws = None

    try:
        ws = create_connection(
            f"{WS_BASE}/status/{st.session_state.job_id_consolidate}",
            origin="http://localhost:8501",
            timeout=10,
        )
        ws.settimeout(1)

        with status_box:
            with st.status(label=f"`{st.session_state.job_id_consolidate}`", expanded=True) as status:
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

                        st.session_state.progress_consolidate = progress
                        progress_bar.progress(progress, text=f"{progress}%")

                        st.write(message)

                        if state == "completed":
                            progress_bar.progress(100)
                            status.update(state="complete")
                            st.balloons()
                            break

                        elif state in ("failed", "error"):
                            status.update(label="Consolidate failed", state="error")
                            st.error("Consolidate job failed. Check server logs for details.")
                            break

    except Exception as e:
        st.error(f"Live updates failed: {e}")

    finally:
        with contextlib.suppress(Exception):
            if ws is not None:
                ws.close()

st.markdown('<hr class="soft"/>', unsafe_allow_html=True)
