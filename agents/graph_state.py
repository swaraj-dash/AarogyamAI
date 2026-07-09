"""
Shared state for the AarogyamAI agent graph.

Kept as a single TypedDict (not a class hierarchy) because LangGraph passes
this dict between nodes and merges partial updates — every node function
takes `AgentState` and returns a partial dict of the fields it touched.
"""
from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
    user_id: int
    user_message: str
    intent: str                    # nutrition | fitness | analysis | chat
    profile: dict
    episodic_digest: str
    semantic_context: list[dict]
    rag_dishes: list[dict]
    response: str
    nodes_executed: list[str]
