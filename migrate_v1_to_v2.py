"""
Migrates a v1 AarogyamAI database to the v2 schema.

Safe by construction:
- Takes a timestamped backup copy of the DB file before touching anything.
- Every change is additive (new tables via CREATE TABLE IF NOT EXISTS, new
  columns via ALTER TABLE ... ADD COLUMN guarded by a column-existence
  check). Nothing in v1's existing tables/rows/columns is deleted or
  rewritten.
- Idempotent: safe to run twice — already-migrated columns/tables are
  detected and skipped.

Usage:
    python migrate_v1_to_v2.py /path/to/v1_aarogyam.db
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
from datetime import datetime

import database as db


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)


def migrate(db_path: str):
    backup_path = f"{db_path}.v1_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    print(f"Backed up original database to: {backup_path}")

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    # --- new columns on existing tables ---
    if not _column_exists(conn, "users", "current_weight_kg"):
        conn.execute("ALTER TABLE users ADD COLUMN current_weight_kg REAL")
        print("Added users.current_weight_kg")
    if not _column_exists(conn, "users", "auth_secret_hash"):
        conn.execute("ALTER TABLE users ADD COLUMN auth_secret_hash TEXT")
        print("Added users.auth_secret_hash")
    conn.commit()

    # --- backfill current_weight_kg from the most recent daily_logs row ---
    users = conn.execute("SELECT user_id FROM users").fetchall()
    backfilled = 0
    for (user_id,) in users:
        row = conn.execute(
            "SELECT weight_kg FROM daily_logs WHERE user_id = ? AND weight_kg IS NOT NULL "
            "ORDER BY log_date DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        if row and row[0] is not None:
            conn.execute("UPDATE users SET current_weight_kg = ? WHERE user_id = ?", (row[0], user_id))
            backfilled += 1
    conn.commit()
    print(f"Backfilled current_weight_kg for {backfilled}/{len(users)} users")
    conn.close()

    # --- create all v2-only tables (chat_messages, user_memory,
    #     memory_consolidation_runs, agent_traces, rag_dishes) ---
    # database.init_db() uses CREATE TABLE IF NOT EXISTS throughout, so
    # this is safe to run against a v1 file: it only adds what's missing.
    import config
    config.DATABASE_PATH = db_path
    db.init_db()
    print("Created v2-only tables (chat_messages, user_memory, "
          "memory_consolidation_runs, agent_traces, rag_dishes)")

    print(
        "\nMigration complete. Optional next step: run a one-time historical "
        "memory bootstrap so existing users don't start with empty semantic "
        "memory —\n\n"
        "    from services.memory_service import SemanticMemory\n"
        "    sm = SemanticMemory()\n"
        "    for user_id in [...]:\n"
        "        sm.consolidate(user_id, lookback_days=90)\n"
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python migrate_v1_to_v2.py /path/to/v1_aarogyam.db")
        sys.exit(1)
    migrate(sys.argv[1])
