"""
This page exists to make the two v2 headline features literally visible,
not just true in the backend: the semantic memory the system has built up
about you, and the execution trace of the agent graph for each request
(which node handled it, in what order). Most "AI health app" portfolio
projects only show you the chat output — this shows you the reasoning
infrastructure behind it, which is the actual point of the rebuild.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

import database as db
from services.memory_service import SemanticMemory

st.set_page_config(page_title="Memory & Agents · AarogyamAI", page_icon="🧠", layout="wide")

if "user_id" not in st.session_state:
    st.warning("Please log in from the main page first.")
    st.stop()

user_id = st.session_state["user_id"]
st.title("Memory & Agent Inspector")

tab_memory, tab_traces, tab_consolidate = st.tabs(
    ["Semantic memory", "Agent traces", "Run consolidation"]
)

with tab_memory:
    st.subheader("Durable facts learned about you")
    st.caption(
        "Each row is a fact the memory-consolidation agent extracted from your logs, "
        "with a confidence score and a reinforcement count — a fact seen again in a "
        "later consolidation run increases both, rather than being stored as a duplicate."
    )
    memories = db.get_all_user_memory(user_id)
    if not memories:
        st.info("No semantic memory yet. Use the 'Run consolidation' tab to generate some from your logs.")
    else:
        for m in memories:
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 1, 1])
                col1.markdown(f"**[{m['category']}]** {m['fact']}")
                col2.metric("Confidence", f"{m['confidence']:.2f}")
                col3.metric("Reinforced", m["reinforcement_count"])
                st.caption(f"Evidence window: {m['evidence_start_date']} to {m['evidence_end_date']}")

with tab_traces:
    st.subheader("Recent agent execution traces")
    st.caption(
        "Every /chat message runs through the LangGraph orchestrator: classify intent → "
        "retrieve memory → specialist node → write back. This is that trajectory, logged."
    )
    traces = db.get_recent_agent_traces(user_id, limit=20)
    if not traces:
        st.info("No agent traces yet — send a message on the Chat page first.")
    else:
        for t in traces:
            with st.container(border=True):
                st.markdown(f"**Intent:** {t['intent']} &nbsp;|&nbsp; **Latency:** {t['latency_ms']}ms")
                st.code(" → ".join(t["nodes_executed"]), language=None)
                st.caption(t["created_at"])

with tab_consolidate:
    st.subheader("Manually trigger memory consolidation")
    st.caption(
        "In production this runs nightly via APScheduler for every user. This button "
        "lets you trigger it on demand — useful for a live demo where you don't want "
        "to wait until 2am for the memory to update."
    )
    lookback = st.slider("Lookback window (days)", min_value=3, max_value=30, value=14)
    if st.button("Run consolidation now", type="primary"):
        with st.spinner("Reading recent logs, extracting durable patterns, deduplicating..."):
            semantic_memory = SemanticMemory()
            result = semantic_memory.consolidate(user_id, lookback_days=lookback)
        st.success(f"Created {result['facts_created']} new facts, reinforced {result['facts_reinforced']} existing ones.")
        st.rerun()
