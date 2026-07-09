import os
import sqlite3

import migrate_v1_to_v2 as migrator

V1_SCHEMA = """
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY, name TEXT NOT NULL, dob TEXT NOT NULL,
    height_cm REAL NOT NULL, gender TEXT NOT NULL, location_state TEXT NOT NULL,
    city TEXT NOT NULL, food_preference TEXT NOT NULL, health_goal TEXT NOT NULL,
    preferred_exercise TEXT, medical_conditions TEXT, medications TEXT,
    allergies TEXT, surgical_history TEXT, family_history TEXT
);
CREATE TABLE daily_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
    log_date TEXT NOT NULL, total_sleep_minutes INTEGER, steps INTEGER,
    mood TEXT, weight_kg REAL, selfie_path TEXT, posture_pic_path TEXT,
    travel_info TEXT, hydration_level REAL, stress_level TEXT,
    menstrual_cycle_day INTEGER, task_completion TEXT, focus_level TEXT
);
"""


def _make_v1_db(path: str):
    conn = sqlite3.connect(path)
    conn.executescript(V1_SCHEMA)
    conn.execute(
        "INSERT INTO users (user_id, name, dob, height_cm, gender, location_state, city, "
        "food_preference, health_goal) VALUES (1, 'Legacy User', '1990-01-01', 165, 'female', "
        "'Kerala', 'Kochi', 'vegetarian', 'general wellness')"
    )
    conn.execute(
        "INSERT INTO daily_logs (user_id, log_date, weight_kg) VALUES (1, '2026-05-01', 55.0)"
    )
    conn.execute(
        "INSERT INTO daily_logs (user_id, log_date, weight_kg) VALUES (1, '2026-05-10', 54.2)"
    )
    conn.commit()
    conn.close()


def test_migration_adds_new_columns_and_backfills_weight(tmp_path):
    db_path = str(tmp_path / "v1_legacy.db")
    _make_v1_db(db_path)

    migrator.migrate(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    columns = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
    assert "current_weight_kg" in columns
    assert "auth_secret_hash" in columns

    user = conn.execute("SELECT * FROM users WHERE user_id = 1").fetchone()
    assert user["current_weight_kg"] == 54.2  # backfilled from most recent log, not the oldest

    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    for expected in ("chat_messages", "user_memory", "memory_consolidation_runs",
                      "agent_traces", "rag_dishes"):
        assert expected in tables
    conn.close()


def test_migration_creates_backup_file(tmp_path):
    db_path = str(tmp_path / "v1_legacy.db")
    _make_v1_db(db_path)
    migrator.migrate(db_path)

    backups = [f for f in os.listdir(tmp_path) if "v1_backup" in f]
    assert len(backups) == 1


def test_migration_is_idempotent(tmp_path):
    db_path = str(tmp_path / "v1_legacy.db")
    _make_v1_db(db_path)
    migrator.migrate(db_path)
    # second run should not raise (ADD COLUMN guarded, CREATE TABLE IF NOT EXISTS)
    migrator.migrate(db_path)

    conn = sqlite3.connect(db_path)
    columns = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
    assert columns.count("current_weight_kg") == 1
    conn.close()
