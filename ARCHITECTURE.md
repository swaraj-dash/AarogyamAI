# Architecture

This document is the "why," not the "what" — README.md covers file layout
and setup. This covers the reasoning behind each structural decision, what
alternatives were considered, and where the current design intentionally
stops short of over-engineering.

## 1. Why a tiered memory system, and why this shape specifically

The core problem with v1 wasn't "the chat history is short" — 20 messages
is a reasonable window. It's that **nothing durable was ever extracted from
it, or from the daily logs sitting right next to it in the same
database.** Every AI call started from zero context beyond whatever fit in
that 20-message slice.

Three tiers, each solving a distinct failure mode:

- **Working memory** (`chat_messages` table). Fixes "state lives in
  process RAM." Also fixes "no summarization" — when the window overflows,
  the oldest chunk is rolled into an LLM-written summary row instead of
  being deleted outright. A user asking "what did I tell you about my
  knee earlier" 30 messages later gets a real (if compressed) answer
  instead of "I don't have that context."

- **Episodic memory** (`daily_logs` + friends, already existed in v1).
  Nothing new structurally — just given a clean read API
  (`EpisodicMemory.get_recent_logs` / `summarize_for_prompt`) so
  consolidation and the agent nodes don't each reinvent "turn N rows of
  SQL into a paragraph."

- **Semantic memory** (`user_memory` table) — the actual new capability.
  A nightly job asks the LLM to extract 2-6 *durable, general* facts from
  a rolling window of episodic data ("sleep consistently drops on
  weekends," not "slept 6h on Tuesday"). Each fact is embedded and checked
  against existing memory via cosine similarity
  (`MEMORY_DEDUP_SIMILARITY_THRESHOLD = 0.90`); a near-duplicate
  reinforces the existing row's `confidence` and `reinforcement_count`
  instead of creating a copy. This is what keeps memory *convergent* —
  without dedup, 90 days of logs would produce 90 days' worth of
  near-identical "sleep is low" facts instead of one fact that gets more
  confident over time.

Why not a single flat "memory" table? Because the three tiers have
genuinely different write/read patterns and lifetimes: working memory is
written on every turn and pruned aggressively; episodic memory is
immutable raw data; semantic memory is written rarely (nightly) and read
often. Collapsing them would mean every read path has to filter by type
anyway — might as well let the schema say so.

## 2. Why LangGraph instead of hand-rolled if/elif routing

The honest alternative here was: a dict of `{"nutrition": nutrition_fn,
"fitness": fitness_fn, ...}` and a plain function call. That would work,
and would be *less code*. Two reasons LangGraph earns its place instead:

1. **Shared pre-processing without re-running it per branch.** The
   `retrieve_memory` node runs exactly once regardless of which specialist
   node is chosen next — a hand-rolled dispatch would either duplicate
   that call in every branch function or need its own ad hoc "run this
   first" convention, which is what a graph framework already formalizes.
2. **Observability comes for free at the framework level.** `nodes_executed`
   is threaded through `AgentState` and every node appends to it — with a
   plain dispatch dict you'd have to hand-instrument every branch the same
   way, which people (including past-me) reliably forget to do consistently.

The tradeoff being paid: an extra dependency, and a slightly less
"obvious at a glance" control flow than if/elif. Worth it here because the
graph is explicitly the *product feature being demonstrated* — the whole
rebuild exists to show real agent orchestration, not just to solve
this specific health app.

## 3. Why brute-force numpy cosine similarity instead of FAISS/Chroma

v1 already had `faiss-cpu` in requirements.txt, unused. Adding it back
"because it's already there" without a real need would just be swapping
one kind of unused complexity for another. At this data scale — a few
hundred dishes, a few hundred memory facts per user — a linear scan in
numpy is:
- Faster to develop and audit (it's ~20 lines, readable top to bottom)
- Zero index files to go stale relative to the source table
- Trivial to unit test deterministically (see `tests/test_vector_store.py`)

**Where this stops working:** once any single table's embedded row count
gets into the tens of thousands *per query* (not per app — SQLite already
partitions this per-user for `user_memory`, so this is really only a
concern for `rag_dishes` if the catalog grew from ~50 dishes to a
national-scale menu database), a linear scan starts costing real latency.
At that point, swap the implementation behind `vector_store.top_k_similar`
for a call to pgvector (if you've already moved to Postgres for
multi-tenancy) or a managed vector DB — every caller only depends on that
one function's signature, not on numpy or SQLite specifically, so this is
a one-file change.

## 4. Why hybrid retrieval (hard filter + soft boost + semantic rerank) for RAG

A pure vector search over dishes has one serious failure mode for this
domain: a vegan user could semantically match to a very on-topic but
completely wrong dish (say, a paneer curry scores high on "high protein
vegetarian dinner" similarity but is not actually vegan). Diet
compatibility isn't a *preference* to rank by, it's a *hard constraint* —
so it's applied as a filter before embeddings are even considered, not as
a factor blended into the similarity score. Home-state match, by contrast,
genuinely is just a preference, so it's a small additive boost applied
after ranking, not a filter — a great semantically-matched dish from
another state should still be able to win.

## 5. Why SQLite (still) instead of Postgres

Unchanged from v1, and still the right call for a single-tenant portfolio
project: zero infra to run, trivial to inspect (`sqlite3 aarogyam.db`),
and WAL mode gives real concurrent-read/single-writer behavior, which is
all this workload needs (one bot process + one Streamlit process reading
the same file). The migration path is well-trodden if this ever needs to
be multi-tenant: Postgres + pgvector for the embedding tables, same
service-layer interfaces otherwise.

## 6. What's deliberately NOT here

- **No auth beyond a bare numeric ID.** Real auth (password hashing,
  sessions) is a solved problem and not what this rebuild is about;
  `users.auth_secret_hash` exists as a schema placeholder for whoever
  wants to add it, but wiring it up wasn't the point of this pass.
- **No fine-tuning / custom models.** Everything here is prompting +
  retrieval + orchestration over an off-the-shelf model, deliberately —
  that's the actual skill set being demonstrated (agent design, memory
  architecture, retrieval quality), not model training.
- **No distributed task queue for the nightly consolidation job.**
  APScheduler in-process is fine for one deployment; a multi-instance
  deployment would need the job itself moved to something like Celery/
  Cloud Scheduler so it doesn't run once per instance. Not needed at this
  scale, noted here so it's a conscious omission rather than an oversight.
