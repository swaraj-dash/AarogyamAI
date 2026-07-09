"""
Agent orchestration — replaces v1's ai_engine.py.

v1 had `langchain` / `langchain-google-genai` in requirements.txt but every
AI call in the actual codebase was a single prompt -> single Gemini
response -> json.loads(). No planning, no routing, no tool use, no
multi-step reasoning of any kind — despite the dependency being there.

v2 builds an actual LangGraph StateGraph:

    START -> classify_intent -> retrieve_memory -> {nutrition | fitness |
             analysis | chat} -> memory_writeback -> END

- classify_intent: LLM call that routes the user's message to a specialist
  node. Falls back to a keyword heuristic if the LLM output can't be parsed
  (never hard-fails a conversation over a routing hiccup).
- retrieve_memory: single shared node that pulls EpisodicMemory +
  SemanticMemory context ONCE, before branching — every specialist node
  gets the same grounded context instead of each one re-querying the DB.
- specialist nodes: each builds a focused prompt from (profile + episodic
  digest + semantic memory [+ RAG dishes for nutrition]) and calls the LLM.
- memory_writeback: persists the exchange to working memory (chat_messages)
  so the next turn's `retrieve_memory` (and the nightly consolidation job)
  sees it.
- Every run is instrumented: nodes_executed is threaded through state and
  written to `agent_traces` on completion, so the agent's execution path is
  inspectable after the fact instead of being a black box — the same
  "trajectory visibility" idea behind evaluating agent runs, applied here
  at the product level.

Everything depends on the LLMClient/Embedder interfaces, not concrete
Gemini classes, so `run(..., llm=FakeLLMClient(...))` exercises the full
graph topology in tests with zero network calls.
"""
from __future__ import annotations

import time

from langgraph.graph import StateGraph, END

import database as db
from agents.graph_state import AgentState
from llm_client import LLMClient, get_llm
from services import rag_service
from services.memory_service import EpisodicMemory, SemanticMemory, WorkingMemory

VALID_INTENTS = {"nutrition", "fitness", "analysis", "chat"}

_KEYWORD_FALLBACK = {
    "nutrition": ["eat", "food", "meal", "diet", "nutrition", "dish", "hungry", "recipe"],
    "fitness": ["workout", "exercise", "gym", "run", "fitness", "yoga", "training"],
    "analysis": ["trend", "progress", "how am i doing", "analysis", "report", "score"],
}


def _keyword_classify(message: str) -> str:
    lowered = message.lower()
    for intent, keywords in _KEYWORD_FALLBACK.items():
        if any(kw in lowered for kw in keywords):
            return intent
    return "chat"


def build_graph(llm: LLMClient = None, semantic_memory: SemanticMemory = None,
                working_memory: WorkingMemory = None, embedder=None):
    llm = llm or get_llm()
    semantic_memory = semantic_memory or SemanticMemory(llm=llm)
    working_memory = working_memory or WorkingMemory(llm=llm)
    embedder = embedder or semantic_memory.embedder

    def _track(state: AgentState, node_name: str) -> list[str]:
        return (state.get("nodes_executed") or []) + [node_name]

    def classify_intent(state: AgentState) -> dict:
        prompt = (
            "Classify the user's message into exactly one category: "
            "nutrition, fitness, analysis, or chat (general/other).\n"
            f'Message: "{state["user_message"]}"\n'
            'Respond as JSON: {"intent": "..."}'
        )
        intent = "chat"
        try:
            result = llm.call_structured(prompt)
            candidate = str(result.get("intent", "")).strip().lower()
            if candidate in VALID_INTENTS:
                intent = candidate
            else:
                intent = _keyword_classify(state["user_message"])
        except Exception:
            intent = _keyword_classify(state["user_message"])
        return {"intent": intent, "nodes_executed": _track(state, "classify_intent")}

    def retrieve_memory(state: AgentState) -> dict:
        user_id = state["user_id"]
        logs = EpisodicMemory.get_recent_logs(user_id, days=14)
        digest = EpisodicMemory.summarize_for_prompt(logs)
        semantic = semantic_memory.retrieve_relevant(user_id, state["user_message"])
        return {
            "episodic_digest": digest,
            "semantic_context": semantic,
            "nodes_executed": _track(state, "retrieve_memory"),
        }

    def _base_context(state: AgentState) -> str:
        profile = state.get("profile") or {}
        return (
            f"User profile: goal={profile.get('health_goal')}, "
            f"diet={profile.get('food_preference')}, state={profile.get('location_state')}.\n"
            f"Recent logs:\n{state.get('episodic_digest', '')}\n\n"
            f"Established long-term patterns:\n{SemanticMemory.format_for_prompt(state.get('semantic_context'))}"
        )

    def nutrition_node(state: AgentState) -> dict:
        profile = state.get("profile") or {}
        deficiency_hints = " ".join(
            m["fact"] for m in (state.get("semantic_context") or []) if m.get("category") == "nutrition"
        )
        query = f"{profile.get('health_goal', '')} {deficiency_hints}".strip() or "balanced healthy meal"
        dishes = rag_service.retrieve_dishes(
            food_preference=profile.get("food_preference", ""),
            query_text=query,
            home_state=profile.get("location_state"),
            embedder=embedder,
        )
        dish_lines = "\n".join(
            f"- {d['dish_name']} ({d['state']}, {d['meal_type']}): {d['description']}" for d in dishes
        )
        prompt = (
            f"{_base_context(state)}\n\nCandidate regional dishes:\n{dish_lines}\n\n"
            f'User message: "{state["user_message"]}"\n\n'
            "As a nutrition guide, recommend 1-3 of the candidate dishes (or general "
            "guidance if none fit) and explain why, referencing the user's established "
            "patterns where relevant. Keep it under 120 words."
        )
        response = llm.generate_text(prompt)
        return {"response": response, "rag_dishes": dishes, "nodes_executed": _track(state, "nutrition_node")}

    def fitness_node(state: AgentState) -> dict:
        prompt = (
            f"{_base_context(state)}\n\n"
            f'User message: "{state["user_message"]}"\n\n'
            "As a fitness guide, give specific, safe guidance grounded in the recent logs "
            "and long-term patterns above. Flag if medical conditions/injuries in the "
            "profile mean an exercise should be avoided. Keep it under 120 words."
        )
        response = llm.generate_text(prompt)
        return {"response": response, "nodes_executed": _track(state, "fitness_node")}

    def analysis_node(state: AgentState) -> dict:
        from services import analytics_service
        logs = EpisodicMemory.get_recent_logs(state["user_id"], days=14)
        summary = analytics_service.compute_summary(logs)
        patterns = analytics_service.detect_notable_patterns(logs)
        prompt = (
            f"{_base_context(state)}\n\n"
            f"Computed summary: {summary}\nNotable patterns: {patterns}\n\n"
            f'User message: "{state["user_message"]}"\n\n'
            "Answer the user's question about their own progress using ONLY the computed "
            "data above — do not invent numbers. Keep it under 120 words."
        )
        response = llm.generate_text(prompt)
        return {"response": response, "nodes_executed": _track(state, "analysis_node")}

    def chat_node(state: AgentState) -> dict:
        window = working_memory.get_window(state["user_id"])
        transcript = "\n".join(f"{m['role']}: {m['content']}" for m in window[-6:])
        prompt = (
            f"{_base_context(state)}\n\nRecent conversation:\n{transcript}\n\n"
            f'User message: "{state["user_message"]}"\n\n'
            "Respond as a warm, knowledgeable health companion. Keep it under 100 words."
        )
        response = llm.generate_text(prompt)
        return {"response": response, "nodes_executed": _track(state, "chat_node")}

    def memory_writeback(state: AgentState) -> dict:
        working_memory.append(state["user_id"], "user", state["user_message"])
        working_memory.append(state["user_id"], "model", state.get("response", ""))
        return {"nodes_executed": _track(state, "memory_writeback")}

    graph = StateGraph(AgentState)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("retrieve_memory", retrieve_memory)
    graph.add_node("nutrition_node", nutrition_node)
    graph.add_node("fitness_node", fitness_node)
    graph.add_node("analysis_node", analysis_node)
    graph.add_node("chat_node", chat_node)
    graph.add_node("memory_writeback", memory_writeback)

    graph.set_entry_point("classify_intent")
    graph.add_edge("classify_intent", "retrieve_memory")
    graph.add_conditional_edges(
        "retrieve_memory",
        lambda state: state["intent"],
        {
            "nutrition": "nutrition_node", "fitness": "fitness_node",
            "analysis": "analysis_node", "chat": "chat_node",
        },
    )
    for node in ("nutrition_node", "fitness_node", "analysis_node", "chat_node"):
        graph.add_edge(node, "memory_writeback")
    graph.add_edge("memory_writeback", END)

    return graph.compile()


_graph_singleton = None


def get_compiled_graph():
    global _graph_singleton
    if _graph_singleton is None:
        _graph_singleton = build_graph()
    return _graph_singleton


def handle_message(user_id: int, user_message: str, graph=None) -> dict:
    """Entry point used by both the Telegram bot and the Streamlit chat page."""
    graph = graph or get_compiled_graph()
    profile = db.get_user(user_id) or {}

    started = time.monotonic()
    final_state = graph.invoke({
        "user_id": user_id, "user_message": user_message, "profile": profile,
        "nodes_executed": [],
    })
    latency_ms = int((time.monotonic() - started) * 1000)

    db.add_agent_trace(
        user_id, final_state.get("intent", "unknown"),
        final_state.get("nodes_executed", []), latency_ms,
    )
    return final_state
