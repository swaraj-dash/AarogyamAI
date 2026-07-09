import json
from datetime import datetime, timedelta

import database as db
from embeddings import DeterministicHashEmbedder
from llm_client import FakeLLMClient
from services.memory_service import EpisodicMemory, SemanticMemory, WorkingMemory
import config


def test_working_memory_appends_and_reads_window(sample_user):
    wm = WorkingMemory(llm=FakeLLMClient())
    wm.append(sample_user, "user", "hi")
    wm.append(sample_user, "model", "hello!")
    window = wm.get_window(sample_user)
    assert [m["content"] for m in window] == ["hi", "hello!"]


def test_working_memory_summarizes_when_window_overflows(sample_user, monkeypatch):
    monkeypatch.setattr(config, "MEMORY_WORKING_WINDOW", 6)
    monkeypatch.setattr(config, "MEMORY_SUMMARIZE_AFTER", 4)

    llm = FakeLLMClient(default_response="Summary: talked about sleep and food.")
    wm = WorkingMemory(llm=llm)
    for i in range(10):
        wm.append(sample_user, "user" if i % 2 == 0 else "model", f"message {i}")

    all_messages = db.get_recent_chat_messages(sample_user, limit=50)
    roles = [m["role"] for m in all_messages]
    assert "summary" in roles, "expected old messages to be rolled into a summary, not just dropped"
    # the oldest raw messages should have been deleted after summarization
    contents = [m["content"] for m in all_messages]
    assert "message 0" not in contents


def test_semantic_memory_consolidate_creates_facts(sample_user):
    today = datetime.now().date()
    logs_payload = [{
        "log_date": (today - timedelta(days=d)).isoformat(), "total_sleep_minutes": 300,
        "steps": 4000, "mood": "low", "weight_kg": 60.0,
        "food_entries": [], "exercise_entries": [],
    } for d in range(1, 8)]
    for log in logs_payload:
        db.add_daily_log({"user_id": sample_user, **{k: v for k, v in log.items()
                                                       if k not in ("food_entries", "exercise_entries")}})

    llm = FakeLLMClient(responses=[json.dumps({
        "facts": [
            {"category": "sleep", "fact": "Sleep is consistently low, around 5 hours", "confidence": 0.8},
            {"category": "mood", "fact": "Mood has been low this week", "confidence": 0.6},
        ]
    })])
    sm = SemanticMemory(llm=llm, embedder=DeterministicHashEmbedder(dim=64))
    result = sm.consolidate(sample_user, lookback_days=14)

    assert result["facts_created"] == 2
    memories = db.get_all_user_memory(sample_user)
    assert len(memories) == 2
    assert any("Sleep" in m["fact"] for m in memories)


def test_semantic_memory_consolidate_dedup_reinforces_existing(sample_user):
    embedder = DeterministicHashEmbedder(dim=64)
    existing_fact = "Sleep is consistently low, around 5 hours"
    db.add_user_memory(
        sample_user, "sleep", existing_fact, embedder.embed_one(existing_fact),
        confidence=0.6, evidence_start_date="2026-05-01", evidence_end_date="2026-05-14",
    )
    today = datetime.now().date()
    for d in range(1, 8):
        db.add_daily_log({
            "user_id": sample_user, "log_date": (today - timedelta(days=d)).isoformat(),
            "total_sleep_minutes": 300, "steps": 4000, "mood": "low",
        })

    llm = FakeLLMClient(responses=[json.dumps({
        "facts": [{"category": "sleep", "fact": existing_fact, "confidence": 0.8}]
    })])
    sm = SemanticMemory(llm=llm, embedder=embedder)
    result = sm.consolidate(sample_user, lookback_days=14)

    assert result["facts_created"] == 0
    assert result["facts_reinforced"] == 1
    memories = db.get_all_user_memory(sample_user)
    assert len(memories) == 1
    assert memories[0]["reinforcement_count"] == 2


def test_semantic_memory_consolidate_no_logs_returns_zero(sample_user):
    sm = SemanticMemory(llm=FakeLLMClient(), embedder=DeterministicHashEmbedder())
    result = sm.consolidate(sample_user, lookback_days=14)
    assert result == {"facts_created": 0, "facts_reinforced": 0}


def test_semantic_memory_retrieve_relevant(sample_user):
    embedder = DeterministicHashEmbedder(dim=64)
    db.add_user_memory(
        sample_user, "nutrition", "Protein intake is consistently below target",
        embedder.embed_one("Protein intake is consistently below target"),
        confidence=0.7, evidence_start_date="2026-06-01", evidence_end_date="2026-06-14",
    )
    db.add_user_memory(
        sample_user, "exercise", "Prefers yoga over gym workouts",
        embedder.embed_one("Prefers yoga over gym workouts"),
        confidence=0.7, evidence_start_date="2026-06-01", evidence_end_date="2026-06-14",
    )
    sm = SemanticMemory(llm=FakeLLMClient(), embedder=embedder)
    results = sm.retrieve_relevant(sample_user, "what should I eat for protein", top_k=1)
    assert len(results) == 1
    assert "Protein" in results[0]["fact"]
    assert "embedding" not in results[0]


def test_episodic_memory_summarize_for_prompt_handles_empty():
    assert "No logs" in EpisodicMemory.summarize_for_prompt([])
