"""API-only Streamlit console for QuerySmith."""

from __future__ import annotations
import os
import time
from typing import Any
import streamlit as st
from client import QuerySmithClient


BASE_URL = os.environ.get("QS_API_URL", "http://api:8000")
API_KEY = os.environ.get("QS_UI_API_KEY", "")

TERMINAL_STATUSES = {
    "SUCCEEDED",
    "FAILED",
    "BLOCKED",
    "CANCELLED",
    "NEEDS_CLARIFICATION",
}

POLL_INTERVAL_SECONDS = 0.75
MAX_DISPLAYED_EVENTS = 200


st.set_page_config(
    page_title="QuerySmith",
    page_icon="🔎",
    layout="wide",
)

st.title("QuerySmith")
st.caption("Ask questions about your connected data using natural language.")


def initialize_state() -> None:
    """Initialize persistent Streamlit session state."""

    if "active_query_id" not in st.session_state:
        st.session_state.active_query_id = None

    if "event_cursor" not in st.session_state:
        st.session_state.event_cursor = 0

    if "query_events" not in st.session_state:
        st.session_state.query_events = []


def reset_query_state() -> None:
    """Clear the current query while retaining application configuration."""

    st.session_state.active_query_id = None
    st.session_state.event_cursor = 0
    st.session_state.query_events = []


def store_events(events: list[dict[str, Any]]) -> None:
    """Store previously unseen execution events."""

    existing_sequences = {
        int(event["sequence"])
        for event in st.session_state.query_events
        if "sequence" in event
    }

    for event in events:
        sequence = int(event["sequence"])

        if sequence in existing_sequences:
            continue

        st.session_state.query_events.append(event)
        existing_sequences.add(sequence)

        st.session_state.event_cursor = max(
            int(st.session_state.event_cursor),
            sequence,
        )

    st.session_state.query_events = st.session_state.query_events[
        -MAX_DISPLAYED_EVENTS:
    ]


def render_events(status: str) -> None:
    """Render the stored execution events."""

    if status in {"FAILED", "BLOCKED"}:
        status_state = "error"
    elif status in TERMINAL_STATUSES:
        status_state = "complete"
    else:
        status_state = "running"

    label = (
        f"Query {status.lower().replace('_', ' ')}"
        if status in TERMINAL_STATUSES
        else "Query running"
    )

    with st.status(
        label,
        expanded=status not in TERMINAL_STATUSES,
        state=status_state,
    ):
        if not st.session_state.query_events:
            st.write("Waiting for execution events...")

        for event in st.session_state.query_events:
            event_type = event.get("event_type", "event")
            payload = event.get("payload") or {}
            st.write(f"{event_type}: {payload}")


def render_result(current: dict[str, Any]) -> None:
    """Render a terminal query result."""

    status = current["status"]
    result = current.get("result") or {}

    if status == "SUCCEEDED":
        analysis = result.get("analysis") or {}
        answer = analysis.get("answer_markdown") or "Query completed."

        st.markdown(answer)

        caveats = analysis.get("caveats") or []
        if caveats:
            with st.expander("Caveats"):
                for caveat in caveats:
                    st.write(caveat)

        execution = result.get("result") or {}
        rows = execution.get("rows") or []

        if rows:
            st.dataframe(
                rows,
                use_container_width=True,
            )
        else:
            st.info("The query completed but returned no rows.")

        sql = result.get("sql")
        if sql:
            with st.expander("Generated SQL"):
                st.code(sql, language="sql")

        return

    if status == "NEEDS_CLARIFICATION":
        st.warning(result or "The question needs clarification.")
        return

    if status == "CANCELLED":
        st.info("The query was cancelled.")
        return

    if status == "BLOCKED":
        st.error("The query was blocked by QuerySmith's security controls.")
        if result:
            st.write(result)
        return

    st.error("The query failed.")
    if result:
        st.write(result)


initialize_state()

if not API_KEY:
    st.error("QS_UI_API_KEY is not configured.")
    st.stop()

client = QuerySmithClient(BASE_URL, API_KEY)

try:
    active_query_id = st.session_state.active_query_id

    if active_query_id is None:
        question = st.chat_input("Ask a question about your data")

        if question:
            with st.spinner("Submitting your question..."):
                created = client.ask(question)

            st.session_state.active_query_id = created["query_id"]
            st.session_state.event_cursor = 0
            st.session_state.query_events = []
            st.rerun()

    else:
        query_id = str(active_query_id)

        st.caption(f"Query ID: `{query_id}`")

        event_page = client.events(
            query_id,
            int(st.session_state.event_cursor),
        )
        store_events(event_page.get("events") or [])

        current = client.query(query_id)
        current_status = str(current["status"])

        render_events(current_status)

        if current_status not in TERMINAL_STATUSES:
            if st.button(
                "Cancel",
                key=f"cancel-{query_id}",
                type="secondary",
            ):
                client.cancel(query_id)
                st.rerun()

            time.sleep(POLL_INTERVAL_SECONDS)
            st.rerun()

        else:
            render_result(current)

            if st.button(
                "Ask another question",
                key=f"new-question-{query_id}",
                type="primary",
            ):
                reset_query_state()
                st.rerun()

finally:
    client.close()