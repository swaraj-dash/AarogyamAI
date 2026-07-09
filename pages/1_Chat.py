import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

import database as db
from agents.orchestrator import handle_message
from services.memory_service import WorkingMemory

st.set_page_config(page_title="Chat · AarogyamAI", page_icon="💬")

if "user_id" not in st.session_state:
    st.warning("Please log in from the main page first.")
    st.stop()

user_id = st.session_state["user_id"]
st.title("Chat with AarogyamAI")
st.caption(
    "This is the exact same agent graph and memory system used by the Telegram bot — "
    "conversations here and there share history, because both read/write the same DB."
)

working_memory = WorkingMemory()
history = working_memory.get_window(user_id)

for msg in history:
    role = "assistant" if msg["role"] in ("model", "summary") else "user"
    with st.chat_message(role):
        if msg["role"] == "summary":
            st.caption(f"(summarized earlier context) {msg['content']}")
        else:
            st.write(msg["content"])

if prompt := st.chat_input("Ask about nutrition, fitness, or your recent trends..."):
    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = handle_message(user_id, prompt)
        st.write(result.get("response", ""))
        with st.expander("Agent trajectory (debug)"):
            st.json({
                "intent": result.get("intent"),
                "nodes_executed": result.get("nodes_executed"),
                "semantic_context_used": [m["fact"] for m in (result.get("semantic_context") or [])],
            })
    st.rerun()
