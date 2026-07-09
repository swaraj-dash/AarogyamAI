# Migrating from v1 to v2

If you have an existing v1 AarogyamAI SQLite database with real user data,
`migrate_v1_to_v2.py` brings it up to the v2 schema without touching any
existing rows or columns.

## What it does

1. Takes a timestamped backup copy of your `.db` file before touching
   anything (`yourfile.db.v1_backup_20260709_120000`).
2. Adds two new columns to `users`: `current_weight_kg` and
   `auth_secret_hash` (guarded by a column-existence check, safe to re-run).
3. Backfills `current_weight_kg` for every existing user from their most
   recent `daily_logs.weight_kg` entry — v1 only ever stored weight inside
   individual daily logs, never on the user profile itself, so v2's
   nutrition/fitness prompts (which reference "current weight" directly)
   would otherwise see nothing for pre-existing users.
4. Creates the five v2-only tables — `chat_messages`, `user_memory`,
   `memory_consolidation_runs`, `agent_traces`, `rag_dishes` — via
   `CREATE TABLE IF NOT EXISTS`, so nothing in your existing tables is
   dropped or rewritten.

## Running it

```bash
python migrate_v1_to_v2.py /path/to/your/aarogyam.db
```

Then point `DATABASE_PATH` in your `.env` at the same file and start the
app as normal — it will pick up existing users/logs immediately.

## Optional: bootstrap semantic memory for existing users

Migration alone gives every pre-existing user the *tables* for semantic
memory, but not the memory itself — that only gets populated by running
consolidation. If you have months of historical logs for existing users,
it's worth backfilling once rather than waiting for the nightly job to
slowly build it up 14 days at a time:

```python
from services.memory_service import SemanticMemory
import database as db

sm = SemanticMemory()
conn = db.get_db_connection()
user_ids = [r["user_id"] for r in conn.execute("SELECT user_id FROM users").fetchall()]
conn.close()

for user_id in user_ids:
    result = sm.consolidate(user_id, lookback_days=90)
    print(user_id, result)
```

This costs one LLM call per user (plus one embedding call per extracted
fact) — fine for a handful of users, but batch/rate-limit it if you're
migrating a larger dataset.

## Rolling back

The migration never deletes anything, so rolling back just means pointing
`DATABASE_PATH` back at the `.v1_backup_*` file it created — the v2 tables
in the migrated file are simply ignored by v1 code, they don't need to be
removed.
