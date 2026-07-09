"""
Streamlit entry point.

v1 gap fixed here: v1's Streamlit pages each imported Gemini directly and
used inconsistent model strings (gemini-1.0-pro / 1.5-flash-latest /
2.0-flash across different pages). Every page in v2 goes through the same
services/ and agents/ layer as the bot — one config.LLM_MODEL, one memory
system, one RAG index, shared between both interfaces because they share
the same SQLite file and the same Python modules.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

import config
import database as db
from services import analytics_service, rag_service
from services.memory_service import EpisodicMemory, SemanticMemory

st.set_page_config(page_title="AarogyamAI", page_icon="🩺", layout="wide")

db.init_db()
rag_service.build_index()


def _login_screen():
    st.title("AarogyamAI")
    st.caption("Your agentic health companion — now with an actual memory.")
    user_id_input = st.text_input("Enter your AarogyamAI ID (from the Telegram bot's /start)")
    if st.button("Log in", type="primary"):
        try:
            user_id = int(user_id_input.strip())
        except ValueError:
            st.error("That doesn't look like a valid ID.")
            return
        if not db.user_exists(user_id):
            st.error("No profile found for that ID. Complete /start in the Telegram bot first.")
            return
        st.session_state["user_id"] = user_id
        st.rerun()


def _dashboard(user_id: int):
    user = db.get_user(user_id)
    st.title(f"Welcome back, {user['name']}")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Log out"):
            del st.session_state["user_id"]
            st.rerun()

    logs = EpisodicMemory.get_recent_logs(user_id, days=14)
    summary = analytics_service.compute_summary(logs)

    metric_cols = st.columns(4)
    metric_cols[0].metric("Days logged (14d)", summary["n_days_logged"])
    metric_cols[1].metric("Wellness score", summary["wellness_score"] or "—")
    avg_sleep = summary["averages"].get("total_sleep_minutes")
    metric_cols[2].metric("Avg sleep", f"{avg_sleep / 60:.1f}h" if avg_sleep else "—")
    metric_cols[3].metric("Avg steps", summary["averages"].get("steps") or "—")

    patterns = analytics_service.detect_notable_patterns(logs)
    if patterns:
        st.subheader("Notable patterns")
        for p in patterns:
            st.markdown(f"- {p}")

    semantic_memory = SemanticMemory()
    memories = semantic_memory.retrieve_relevant(user_id, user.get("health_goal", ""), top_k=5)
    st.subheader("What AarogyamAI has learned about you")
    if memories:
        for m in memories:
            st.markdown(f"- **[{m['category']}]** {m['fact']} _(confidence: {m['confidence']:.2f})_")
    else:
        st.info("No long-term patterns yet — keep logging daily, and check back in a couple of weeks. "
                 "(Or use the Memory page to trigger consolidation manually for a demo.)")

    st.divider()
    st.caption(
        "Use the sidebar to chat, log your day, view analytics, generate a report, "
        "or inspect the memory system directly."
    )


def main():
    if "user_id" not in st.session_state:
        _login_screen()
    else:
        _dashboard(st.session_state["user_id"])


if __name__ == "__main__":
    main()
