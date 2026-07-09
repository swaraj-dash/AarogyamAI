# AarogyamAI v2 — an agentic health companion with an actual memory

AarogyamAI is a Telegram bot + Streamlit dashboard that helps you track sleep,
food, exercise, and mood, and gives you AI-generated nutrition/fitness
guidance and reports. This is a from-scratch rebuild of an earlier version
of the project, focused on fixing its two biggest structural gaps:

1. **There was no memory system.** Chat history lived only in the bot
   process's RAM, in a hard-truncated `[-20:]` slice. It vanished on every
   restart and had zero connection to the app's own data — the bot could
   recommend a workout without knowing you'd logged 4 hours of sleep the
   night before.
2. **There was no retrieval and no agent.** "RAG" was a pandas
   string-equality filter on a CSV, and every "AI" call was a single
   prompt → single LLM response, despite `langchain`/`faiss-cpu` sitting
   unused in `requirements.txt`.

v2 fixes both, and cleans up everything else it touched along the way.

## What's actually new

| Area | v1 | v2 |
|---|---|---|
| Chat memory | In-process list, `[-20:]`, gone on restart | Persisted `chat_messages` table with rolling LLM summarization instead of hard truncation |
| Long-term memory | None | `user_memory`: durable facts extracted nightly by a consolidation agent, embedded, deduplicated against existing memory via cosine similarity, reinforced (not duplicated) on repeat evidence |
| RAG | `df['state'] == state` string match | Real embeddings (Gemini `text-embedding-004`, offline-testable via a deterministic hash embedder), hybrid retrieval: hard diet filter → home-state soft boost → semantic rerank |
| AI orchestration | Single prompt → single response per feature | A `LangGraph` agent graph: intent classification → shared memory retrieval → specialist node (nutrition/fitness/analysis/chat) → memory writeback, with every run's node path logged to `agent_traces` for observability |
| Trend detection | First-value-vs-last-value diff | Linear regression (slope + R²) — flags a trend as real only if R² ≥ 0.3, otherwise calls it noise instead of overclaiming |
| Model config | `gemini-1.0-pro` / `1.5-flash-latest` / `2.0-flash` scattered across pages | One `config.LLM_MODEL` |
| PDF reports | Emoji silently stripped, no historical context | Emoji mapped to readable labels instead of dropped; report includes a "what we've learned about you" section straight from semantic memory |
| Testing | None | 69 pytest tests covering vector math, embeddings, memory consolidation/dedup, RAG ranking, the full agent graph (via a scriptable fake LLM), analytics, database CRUD, and PDF generation — runs fully offline, no API key needed |

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design rationale and
[MIGRATION.md](MIGRATION.md) if you're moving data from a v1 database.

## Architecture at a glance

```
Telegram bot  ─┐                                   ┌─ Streamlit dashboard
               ├─► agents/orchestrator.py (LangGraph) ◄─┤
               │        │                                │
               │        ├─ classify_intent               │
               │        ├─ retrieve_memory ───► services/memory_service.py
               │        │                        ├─ WorkingMemory (chat_messages)
               │        │                        ├─ EpisodicMemory (daily_logs)
               │        │                        └─ SemanticMemory (user_memory + embeddings)
               │        ├─ nutrition_node ──────► services/rag_service.py ──► rag_dishes
               │        ├─ fitness_node
               │        ├─ analysis_node ───────► services/analytics_service.py
               │        ├─ chat_node
               │        └─ memory_writeback
               │
               └────────────────────► database.py (single SQLite file, WAL mode)
```

Both interfaces share the same SQLite file and the same Python modules —
there is exactly one memory system, one RAG index, and one LLM
configuration, not two of each drifting independently.

## Project layout

```
config.py               # single source of truth for all settings
database.py             # schema + CRUD (users, logs, chat, memory, RAG, traces)
vector_store.py         # cosine-similarity ranking (the "R" in RAG)
embeddings.py           # Embedder interface: Gemini (real) / deterministic hash (offline)
llm_client.py           # LLMClient interface: Gemini (real) / FakeLLMClient (offline/test)
services/
  memory_service.py     # WorkingMemory / EpisodicMemory / SemanticMemory
  rag_service.py         # hybrid dish retrieval
  analytics_service.py   # regression-based trend detection, wellness score
  report_generator.py    # PDF rendering (fpdf2)
  report_service.py      # ties analytics + memory + LLM + PDF together
agents/
  graph_state.py         # shared TypedDict state
  orchestrator.py         # the LangGraph agent graph
bot/
  main.py                 # Telegram entry point + nightly consolidation scheduler
  handlers/                # start, log_metrics, log_food, chat, report, profile, tools
app.py + pages/            # Streamlit dashboard (chat, logging, analytics, reports,
                            # profile, and a Memory & Agent inspector page)
rag_data/                  # seed CSV of regional dishes + nutrients
tests/                      # 69 tests, fully offline
```

## Running it

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in TELEGRAM_BOT_TOKEN and GOOGLE_API_KEY

# Telegram bot
python -m bot.main

# Streamlit dashboard
streamlit run app.py
```

Without a `GOOGLE_API_KEY`, the app automatically runs in
`AAROGYAM_OFFLINE_MODE` — the LLM and embedding calls are replaced with
deterministic stand-ins, so you can explore the full app (minus real AI
responses) with zero setup.

## Testing

```bash
pytest -q
```

All 69 tests run offline — no network access or API key required, because
every LLM/embedding call in the test suite goes through `FakeLLMClient` /
`DeterministicHashEmbedder` rather than the real Gemini API. This is the
same interface-first design that lets the LangGraph agent graph itself be
tested node-by-node without ever calling a real model.

## Where this stops scaling (and what to do about it)

Documented in detail in ARCHITECTURE.md, but briefly: the brute-force
numpy vector search is fine up to roughly 100k vectors per user/table; past
that, swap `vector_store.top_k_similar` for a call to pgvector or a managed
vector DB — nothing upstream of that one function needs to change, by
design. SQLite is fine for single-tenant/portfolio use; a multi-tenant
deployment would move to Postgres, which is also where you'd get pgvector
for the above.
