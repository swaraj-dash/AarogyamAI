"""
Tiered memory system — the actual fix for v1's biggest gap.

v1 had exactly one memory mechanism: `chat_history[-20:]` held in process
memory. It wasn't persisted, wasn't shared with the Streamlit side, and had
no notion of "durable fact about this user" at all — every AI call
re-derived everything from scratch or got nothing.

This module implements three tiers, modeled after how episodic/semantic
memory separation works in cognitive-architecture literature (and,
transparently, how Claude's own memory system is described in this
product's system prompt — same shape: recent turns fade into consolidated,
retrievable facts instead of being kept verbatim forever or dropped
outright):

1. WorkingMemory  — the current conversation window. Persisted (chat_messages
   table), not just in-process. When the window grows past
   MEMORY_SUMMARIZE_AFTER messages, the oldest chunk is rolled into a
   'summary' row via the LLM instead of being silently discarded — so
   "what did we talk about 40 messages ago" degrades gracefully instead of
   vanishing.

2. EpisodicMemory — the raw daily logs (sleep, food, exercise, mood), already
   in SQLite. This module just adds a clean read API over them shaped for
   memory consolidation.

3. SemanticMemory — the new layer. `consolidate()` reads a window of episodic
   data + recent conversation and asks the LLM to extract durable,
   general facts ("sleep consistently drops on weekends", "recurring
   protein gap"). Each fact is embedded and de-duplicated against existing
   memory via cosine similarity (see vector_store.top_k_similar) — a
   near-duplicate reinforces an existing fact's confidence rather than
   creating a copy, so memory converges instead of growing without bound.
   `retrieve_relevant()` is what nutrition/fitness/chat agents call before
   generating a response, so recommendations are actually informed by
   accumulated history instead of the single day in front of them.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

import config
import database as db
from embeddings import Embedder, get_embedder
from llm_client import LLMClient, get_llm
from vector_store import top_k_similar


class WorkingMemory:
    def __init__(self, llm: LLMClient = None):
        self.llm = llm or get_llm()

    def append(self, user_id: int, role: str, content: str):
        db.add_chat_message(user_id, role, content)
        self._maybe_summarize(user_id)

    def get_window(self, user_id: int) -> list[dict]:
        """Recent turns as [{'role': ..., 'content': ...}], oldest first.

        Includes the most recent rolled-up 'summary' row (if any) as
        synthetic context so the model doesn't lose the thread even after
        older turns have been summarized away.
        """
        messages = db.get_recent_chat_messages(user_id, config.MEMORY_WORKING_WINDOW)
        return [{"role": m["role"], "content": m["content"]} for m in messages]

    def _maybe_summarize(self, user_id: int):
        messages = db.get_recent_chat_messages(user_id, config.MEMORY_WORKING_WINDOW * 3)
        non_summary = [m for m in messages if m["role"] != "summary"]
        if len(non_summary) <= config.MEMORY_WORKING_WINDOW:
            return

        to_summarize = non_summary[:config.MEMORY_SUMMARIZE_AFTER]
        if not to_summarize:
            return

        transcript = "\n".join(f"{m['role']}: {m['content']}" for m in to_summarize)
        prompt = (
            "Summarize the key points of this earlier conversation segment in 2-3 "
            "sentences. Keep concrete facts (numbers, dates, named foods/exercises) "
            "and drop small talk.\n\nTranscript:\n" + transcript
        )
        summary_text = self.llm.generate_text(prompt)
        db.add_chat_message(user_id, "summary", summary_text.strip())

        cutoff_id = to_summarize[-1]["message_id"]
        db.delete_chat_messages_before(user_id, cutoff_id + 1)


class EpisodicMemory:
    @staticmethod
    def get_recent_logs(user_id: int, days: int) -> list[dict]:
        end = datetime.now().date()
        start = end - timedelta(days=days)
        return db.get_logs_in_range(user_id, start.isoformat(), end.isoformat())

    @staticmethod
    def summarize_for_prompt(logs: list[dict]) -> str:
        """Compact textual digest of raw logs, suitable for feeding an LLM
        without dumping full JSON (keeps consolidation prompts small)."""
        if not logs:
            return "No logs recorded in this window."
        lines = []
        for log in logs:
            sleep_h = round((log.get("total_sleep_minutes") or 0) / 60, 1)
            foods = ", ".join(f["description"] for f in log.get("food_entries", []) if f.get("description"))
            exercises = ", ".join(
                f"{e['exercise_type']} ({e.get('duration_minutes', '?')}min)"
                for e in log.get("exercise_entries", [])
            )
            lines.append(
                f"{log['log_date']}: sleep={sleep_h}h, steps={log.get('steps')}, "
                f"mood={log.get('mood')}, weight={log.get('weight_kg')}kg, "
                f"stress={log.get('stress_level')}, foods=[{foods}], exercise=[{exercises}]"
            )
        return "\n".join(lines)


class SemanticMemory:
    def __init__(self, llm: LLMClient = None, embedder: Embedder = None):
        self.llm = llm or get_llm()
        self.embedder = embedder or get_embedder()

    def consolidate(self, user_id: int, lookback_days: int = None) -> dict:
        """Run the memory-consolidation agent for one user.

        Returns a summary dict {'facts_created': n, 'facts_reinforced': n}
        so callers (the nightly job, or a manual "recompute memory" admin
        action) can log/observe what happened.
        """
        lookback_days = lookback_days or config.MEMORY_CONSOLIDATION_LOOKBACK_DAYS
        logs = EpisodicMemory.get_recent_logs(user_id, lookback_days)
        if not logs:
            return {"facts_created": 0, "facts_reinforced": 0}

        window_start = logs[0]["log_date"]
        window_end = logs[-1]["log_date"]
        digest = EpisodicMemory.summarize_for_prompt(logs)

        prompt = (
            "You are a health-memory consolidation agent. Given a window of daily "
            "health logs, extract 2 to 6 DURABLE, GENERAL facts about this person's "
            "patterns — not one-off events, only things that recur or trend across "
            "the window. Each fact must be a short standalone sentence.\n\n"
            f"Logs:\n{digest}\n\n"
            'Respond as JSON: {"facts": [{"category": "sleep|nutrition|exercise|mood|pattern", '
            '"fact": "...", "confidence": 0.0-1.0}]}'
        )
        result = self.llm.call_structured(prompt)
        candidate_facts = result.get("facts", [])

        existing = db.get_all_user_memory(user_id)
        created, reinforced = 0, 0

        for item in candidate_facts:
            fact_text = item.get("fact", "").strip()
            if not fact_text:
                continue
            category = item.get("category", "pattern")
            confidence = float(item.get("confidence", 0.6))
            fact_embedding = self.embedder.embed_one(fact_text)

            match = None
            if existing:
                ranked = top_k_similar(fact_embedding, existing, k=1)
                if ranked and ranked[0]["similarity_score"] >= config.MEMORY_DEDUP_SIMILARITY_THRESHOLD:
                    match = ranked[0]

            if match:
                db.reinforce_user_memory(match["memory_id"], window_end)
                reinforced += 1
            else:
                db.add_user_memory(
                    user_id, category, fact_text, fact_embedding,
                    confidence, window_start, window_end,
                )
                created += 1
                existing.append({"memory_id": None, "embedding": fact_embedding})

        db.log_memory_consolidation_run(user_id, window_start, window_end, created, reinforced)
        return {"facts_created": created, "facts_reinforced": reinforced}

    def retrieve_relevant(self, user_id: int, query_text: str, top_k: int = None) -> list[dict]:
        """Semantic recall: the facts most relevant to the current query.

        This is what turns a nutrition/fitness/chat response from
        "generic advice based on today's row" into "advice informed by
        this person's actual accumulated pattern".
        """
        top_k = top_k or config.MEMORY_RETRIEVAL_TOP_K
        memories = db.get_all_user_memory(user_id)
        if not memories:
            return []
        query_embedding = self.embedder.embed_one(query_text)
        ranked = top_k_similar(query_embedding, memories, k=top_k, min_score=0.05)
        for r in ranked:
            r.pop("embedding", None)
        return ranked

    @staticmethod
    def format_for_prompt(memories: list[dict]) -> str:
        if not memories:
            return "No established long-term patterns yet."
        return "\n".join(f"- [{m['category']}] {m['fact']} (confidence: {m['confidence']:.2f})" for m in memories)
