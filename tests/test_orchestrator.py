import json

import database as db
from embeddings import DeterministicHashEmbedder
from llm_client import FakeLLMClient
from services.memory_service import SemanticMemory, WorkingMemory
from agents.orchestrator import build_graph, handle_message


def _make_graph(responses):
    llm = FakeLLMClient(responses=responses)
    sm = SemanticMemory(llm=llm, embedder=DeterministicHashEmbedder(dim=64))
    wm = WorkingMemory(llm=llm)
    return build_graph(llm=llm, semantic_memory=sm, working_memory=wm), llm


def test_routes_to_nutrition_node(sample_user):
    graph, llm = _make_graph(responses=[
        json.dumps({"intent": "nutrition"}),   # classify_intent
        "Try the Puttu with Kadala Curry for protein!",  # nutrition_node
    ])
    result = handle_message(sample_user, "what should I eat for breakfast", graph=graph)
    assert result["intent"] == "nutrition"
    assert "nodes_executed" in result
    assert result["nodes_executed"] == [
        "classify_intent", "retrieve_memory", "nutrition_node", "memory_writeback",
    ]
    assert result["response"] == "Try the Puttu with Kadala Curry for protein!"


def test_routes_to_fitness_node(sample_user):
    graph, llm = _make_graph(responses=[
        json.dumps({"intent": "fitness"}),
        "A 20 minute yoga session would suit you well.",
    ])
    result = handle_message(sample_user, "give me a workout plan", graph=graph)
    assert result["intent"] == "fitness"
    assert result["nodes_executed"][-2] == "fitness_node"


def test_routes_to_analysis_node(sample_user):
    graph, llm = _make_graph(responses=[
        json.dumps({"intent": "analysis"}),
        "Your steps have been trending upward this week.",
    ])
    result = handle_message(sample_user, "how is my progress this week", graph=graph)
    assert result["intent"] == "analysis"
    assert result["nodes_executed"][-2] == "analysis_node"


def test_routes_to_chat_node_for_general_message(sample_user):
    graph, llm = _make_graph(responses=[
        json.dumps({"intent": "chat"}),
        "I'm doing well, thanks for asking! How are you?",
    ])
    result = handle_message(sample_user, "how are you today", graph=graph)
    assert result["intent"] == "chat"
    assert result["nodes_executed"][-2] == "chat_node"


def test_malformed_classification_falls_back_to_keyword_heuristic(sample_user):
    graph, llm = _make_graph(responses=[
        "not valid json at all",       # classify_intent fails to parse -> keyword fallback
        "Here's a workout suggestion.",
    ])
    result = handle_message(sample_user, "suggest a good gym workout for me", graph=graph)
    assert result["intent"] == "fitness"  # keyword fallback should catch "gym"/"workout"


def test_memory_writeback_persists_conversation(sample_user):
    graph, llm = _make_graph(responses=[
        json.dumps({"intent": "chat"}),
        "Nice to hear from you!",
    ])
    handle_message(sample_user, "hey there", graph=graph)
    messages = db.get_recent_chat_messages(sample_user, limit=10)
    contents = [m["content"] for m in messages]
    assert "hey there" in contents
    assert "Nice to hear from you!" in contents


def test_agent_trace_is_logged(sample_user):
    graph, llm = _make_graph(responses=[
        json.dumps({"intent": "chat"}),
        "hello response",
    ])
    handle_message(sample_user, "hi", graph=graph)
    traces = db.get_recent_agent_traces(sample_user)
    assert len(traces) == 1
    assert traces[0]["intent"] == "chat"
    assert "classify_intent" in traces[0]["nodes_executed"]
    assert traces[0]["latency_ms"] >= 0


def test_nutrition_node_uses_rag_dishes(sample_user):
    embedder = DeterministicHashEmbedder(dim=64)
    from services import rag_service
    dish_rows = [{
        "state": "Kerala", "dish_name": "Puttu", "meal_type": "breakfast",
        "description": "Steamed rice cake", "preference": "vegetarian",
        "primary_nutrient": "carbohydrates", "secondary_nutrient": "fiber",
        "tertiary_nutrient": None, "quaternary_nutrient": None,
    }]
    texts = [rag_service._dish_embedding_text(r) for r in dish_rows]
    embs = embedder.embed(texts)
    db.bulk_insert_rag_dishes([{**dish_rows[0], "embedding": rag_service._to_json(embs[0])}])

    llm = FakeLLMClient(responses=[
        json.dumps({"intent": "nutrition"}),
        "You could try Puttu for a nutritious breakfast.",
    ])
    sm = SemanticMemory(llm=llm, embedder=embedder)
    wm = WorkingMemory(llm=llm)
    graph = build_graph(llm=llm, semantic_memory=sm, working_memory=wm, embedder=embedder)

    result = handle_message(sample_user, "what should I eat for breakfast", graph=graph)
    assert len(result["rag_dishes"]) >= 1
    assert result["rag_dishes"][0]["dish_name"] == "Puttu"
