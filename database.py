"""
SQLite schema + CRUD for AarogyamAI v2.

Carried over from v1 (still the right call for a single-tenant portfolio
project, see ARCHITECTURE.md for the Postgres migration note):
- One SQLite file, WAL mode enabled (v1 used the default rollback journal +
  a 20s busy timeout, which serializes writers under load; WAL lets readers
  and a writer proceed concurrently, which matters once the memory
  consolidation job runs in the background while the bot is also writing).
- sqlite3.Row for dict-style access.
- FK enforcement on.

New in v2:
- chat_messages: v1 kept chat history ONLY in `context.user_data['chat_history']`,
  which is process memory — it evaporates on every bot restart/deploy and is
  invisible to the Streamlit side entirely. This table makes conversational
  memory durable and interface-agnostic.
- user_memory: the semantic memory layer. Each row is a single durable fact
  the system has learned about a user ("sleep drops on weekends", "protein
  intake is a recurring gap"), with an embedding for retrieval, a
  reinforcement_count so repeated evidence strengthens a fact instead of
  duplicating it, and provenance (which log dates it was derived from).
- memory_consolidation_runs: an audit log of when the consolidation agent
  ran, over what window, and how many facts it touched — makes the memory
  system observable/debuggable instead of a black box.
- rag_dishes: the CSV is now loaded into SQLite once with a precomputed
  embedding per dish, so retrieval is vector similarity instead of pandas
  string equality (see services/rag_service.py).
"""
import json
import os
import random
import sqlite3
import time
from datetime import datetime, timedelta

import config


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DATABASE_PATH, timeout=20.0)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.row_factory = sqlite3.Row
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id            INTEGER PRIMARY KEY,
    name               TEXT NOT NULL,
    dob                TEXT NOT NULL,
    height_cm          REAL NOT NULL,
    gender             TEXT NOT NULL,
    location_state     TEXT NOT NULL,
    city               TEXT NOT NULL,
    food_preference    TEXT NOT NULL,
    health_goal        TEXT NOT NULL,
    preferred_exercise TEXT,
    medical_conditions TEXT,
    medications        TEXT,
    allergies          TEXT,
    surgical_history   TEXT,
    family_history     TEXT,
    current_weight_kg  REAL,                       -- v1 gap: weight only lived in daily_logs
    auth_secret_hash   TEXT,                        -- v2: optional password hash for web login
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_logs (
    log_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL,
    log_date            TEXT NOT NULL,
    total_sleep_minutes INTEGER,
    steps               INTEGER,
    mood                TEXT,
    weight_kg           REAL,
    selfie_path         TEXT,
    posture_pic_path    TEXT,
    travel_info         TEXT,
    hydration_level     REAL,
    stress_level        TEXT,
    menstrual_cycle_day INTEGER,
    task_completion     TEXT,
    focus_level         TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    UNIQUE(user_id, log_date)
);

CREATE TABLE IF NOT EXISTS food_entries (
    food_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    log_id          INTEGER NOT NULL,
    meal_type       TEXT NOT NULL,
    food_image_path TEXT,
    description     TEXT,
    FOREIGN KEY (log_id) REFERENCES daily_logs(log_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS exercise_entries (
    exercise_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    log_id           INTEGER NOT NULL,
    exercise_type    TEXT NOT NULL,
    details          TEXT,
    duration_minutes INTEGER,
    FOREIGN KEY (log_id) REFERENCES daily_logs(log_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reports (
    report_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    report_type TEXT NOT NULL,
    start_date  TEXT NOT NULL,
    end_date    TEXT NOT NULL,
    file_path   TEXT NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- ============================= v2: memory layer =============================

CREATE TABLE IF NOT EXISTS chat_messages (
    message_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    role         TEXT NOT NULL,              -- 'user' | 'model' | 'summary'
    content      TEXT NOT NULL,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS user_memory (
    memory_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL,
    category            TEXT NOT NULL,        -- sleep | nutrition | exercise | mood | pattern | preference
    fact                TEXT NOT NULL,        -- the durable statement, e.g. "Sleep drops below 6h on weekends"
    embedding            TEXT NOT NULL,       -- JSON list[float]
    confidence          REAL DEFAULT 0.6,
    reinforcement_count INTEGER DEFAULT 1,
    evidence_start_date TEXT,
    evidence_end_date   TEXT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS memory_consolidation_runs (
    run_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,
    window_start     TEXT NOT NULL,
    window_end       TEXT NOT NULL,
    facts_created    INTEGER DEFAULT 0,
    facts_reinforced INTEGER DEFAULT 0,
    ran_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS agent_traces (
    trace_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL,
    intent         TEXT,
    nodes_executed TEXT,                  -- JSON list, in execution order
    latency_ms     INTEGER,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS rag_dishes (
    dish_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    state              TEXT,
    dish_name          TEXT,
    meal_type          TEXT,
    description        TEXT,
    preference         TEXT,
    primary_nutrient   TEXT,
    secondary_nutrient TEXT,
    tertiary_nutrient  TEXT,
    quaternary_nutrient TEXT,
    embedding          TEXT                  -- JSON list[float], NULL until embedded
);
"""


def init_db():
    conn = get_db_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


# ------------------------------- users --------------------------------------

def generate_unique_user_id() -> int:
    conn = get_db_connection()
    try:
        c = conn.cursor()
        while True:
            ts_part = str(int(time.time() * 1000))[-3:]
            rand_part = str(random.randint(10, 99))
            user_id = int(ts_part + rand_part)
            c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if c.fetchone() is None:
                return user_id
    finally:
        conn.close()


def add_user(user_data: dict, user_id: int = None) -> int:
    conn = get_db_connection()
    try:
        if user_id is None:
            user_id = generate_unique_user_id()
        payload = dict(user_data)
        if isinstance(payload.get("preferred_exercise"), (list, tuple)):
            payload["preferred_exercise"] = json.dumps(payload["preferred_exercise"])
        conn.execute(
            """INSERT INTO users
               (user_id, name, dob, height_cm, gender, location_state, city,
                food_preference, health_goal, preferred_exercise,
                medical_conditions, medications, allergies, surgical_history,
                family_history, current_weight_kg)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id, payload.get("name"), payload.get("dob"),
                payload.get("height_cm"), payload.get("gender"),
                payload.get("location_state"), payload.get("city"),
                payload.get("food_preference"), payload.get("health_goal"),
                payload.get("preferred_exercise"), payload.get("medical_conditions"),
                payload.get("medications"), payload.get("allergies"),
                payload.get("surgical_history"), payload.get("family_history"),
                payload.get("current_weight_kg"),
            ),
        )
        conn.commit()
        return user_id
    finally:
        conn.close()


def user_exists(user_id: int) -> bool:
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return row is not None
    finally:
        conn.close()


def get_user(user_id: int) -> dict | None:
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_user_location(user_id: int, state: str, city: str):
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE users SET location_state = ?, city = ? WHERE user_id = ?",
            (state, city, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_user_field(user_id: int, field: str, value) -> None:
    allowed = {
        "health_goal", "food_preference", "current_weight_kg",
        "preferred_exercise", "medical_conditions",
    }
    if field not in allowed:
        raise ValueError(f"Field '{field}' is not editable via update_user_field")
    conn = get_db_connection()
    try:
        conn.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
        conn.commit()
    finally:
        conn.close()


# ----------------------------- daily logs -----------------------------------

def add_daily_log(log_data: dict) -> int:
    """Upsert-by-date: replaces any existing log for the same user+date.

    Kept from v1 (DELETE then INSERT, relying on ON DELETE CASCADE to also
    remove child food/exercise rows) because it's simple and correct for the
    "one log per day" invariant. The v1 UNIQUE constraint was missing at the
    DB level though — added `UNIQUE(user_id, log_date)` above so this
    invariant is enforced even if application code has a bug, not just
    assumed.
    """
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute(
            "SELECT log_id FROM daily_logs WHERE user_id = ? AND log_date = ?",
            (log_data["user_id"], log_data["log_date"]),
        )
        existing = c.fetchone()
        if existing:
            c.execute("DELETE FROM daily_logs WHERE log_id = ?", (existing["log_id"],))

        travel_info = log_data.get("travel_info")
        if isinstance(travel_info, dict):
            travel_info = json.dumps(travel_info)

        c.execute(
            """INSERT INTO daily_logs
               (user_id, log_date, total_sleep_minutes, steps, mood, weight_kg,
                selfie_path, posture_pic_path, travel_info, hydration_level,
                stress_level, menstrual_cycle_day, task_completion, focus_level)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                log_data["user_id"], log_data["log_date"],
                log_data.get("total_sleep_minutes"), log_data.get("steps"),
                log_data.get("mood"), log_data.get("weight_kg"),
                log_data.get("selfie_path"), log_data.get("posture_pic_path"),
                travel_info, log_data.get("hydration_level"),
                log_data.get("stress_level"), log_data.get("menstrual_cycle_day"),
                log_data.get("task_completion"), log_data.get("focus_level"),
            ),
        )
        log_id = c.lastrowid

        for food in log_data.get("food_entries", []):
            c.execute(
                "INSERT INTO food_entries (log_id, meal_type, food_image_path, description) "
                "VALUES (?, ?, ?, ?)",
                (log_id, food.get("meal_type"), food.get("food_image_path"), food.get("description")),
            )
        for ex in log_data.get("exercise_entries", []):
            c.execute(
                "INSERT INTO exercise_entries (log_id, exercise_type, details, duration_minutes) "
                "VALUES (?, ?, ?, ?)",
                (log_id, ex.get("exercise_type"), ex.get("details"), ex.get("duration_minutes")),
            )

        # keep current_weight_kg on the user profile in sync (v1 gap fixed)
        if log_data.get("weight_kg"):
            c.execute(
                "UPDATE users SET current_weight_kg = ? WHERE user_id = ?",
                (log_data["weight_kg"], log_data["user_id"]),
            )

        conn.commit()
        return log_id
    finally:
        conn.close()


def get_full_daily_log(log_id: int) -> dict:
    conn = get_db_connection()
    try:
        log_row = conn.execute("SELECT * FROM daily_logs WHERE log_id = ?", (log_id,)).fetchone()
        food_rows = conn.execute("SELECT * FROM food_entries WHERE log_id = ?", (log_id,)).fetchall()
        ex_rows = conn.execute("SELECT * FROM exercise_entries WHERE log_id = ?", (log_id,)).fetchall()
        return {
            "log_details": dict(log_row) if log_row else None,
            "food_entries": [dict(r) for r in food_rows],
            "exercise_entries": [dict(r) for r in ex_rows],
        }
    finally:
        conn.close()


def get_logs_in_range(user_id: int, start_date: str, end_date: str) -> list[dict]:
    conn = get_db_connection()
    try:
        logs = conn.execute(
            "SELECT * FROM daily_logs WHERE user_id = ? AND log_date BETWEEN ? AND ? "
            "ORDER BY log_date ASC",
            (user_id, start_date, end_date),
        ).fetchall()
        result = []
        for log in logs:
            log_dict = dict(log)
            log_dict["food_entries"] = [
                dict(r) for r in conn.execute(
                    "SELECT * FROM food_entries WHERE log_id = ?", (log["log_id"],)
                ).fetchall()
            ]
            log_dict["exercise_entries"] = [
                dict(r) for r in conn.execute(
                    "SELECT * FROM exercise_entries WHERE log_id = ?", (log["log_id"],)
                ).fetchall()
            ]
            result.append(log_dict)
        return result
    finally:
        conn.close()


def get_previous_day_image_paths(user_id: int, current_log_date: str) -> dict | None:
    conn = get_db_connection()
    try:
        previous_date = (
            datetime.strptime(current_log_date, "%Y-%m-%d").date() - timedelta(days=1)
        ).strftime("%Y-%m-%d")
        row = conn.execute(
            "SELECT selfie_path, posture_pic_path FROM daily_logs WHERE user_id = ? AND log_date = ?",
            (user_id, previous_date),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_or_create_daily_log(user_id: int, log_date: str) -> int:
    """Incremental-safe counterpart to add_daily_log's upsert-whole-day
    pattern: used when a handler only has ONE new piece of information
    (e.g. a single food entry from /logfood) and shouldn't have to know or
    overwrite the rest of the day's data just to record it."""
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT log_id FROM daily_logs WHERE user_id = ? AND log_date = ?",
            (user_id, log_date),
        ).fetchone()
        if row:
            return row["log_id"]
        cur = conn.execute(
            "INSERT INTO daily_logs (user_id, log_date) VALUES (?, ?)",
            (user_id, log_date),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def add_food_entry_only(log_id: int, meal_type: str, description: str = None,
                         food_image_path: str = None) -> int:
    conn = get_db_connection()
    try:
        cur = conn.execute(
            "INSERT INTO food_entries (log_id, meal_type, food_image_path, description) "
            "VALUES (?, ?, ?, ?)",
            (log_id, meal_type, food_image_path, description),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def add_exercise_entry_only(log_id: int, exercise_type: str, details: str = None,
                             duration_minutes: int = None) -> int:
    conn = get_db_connection()
    try:
        cur = conn.execute(
            "INSERT INTO exercise_entries (log_id, exercise_type, details, duration_minutes) "
            "VALUES (?, ?, ?, ?)",
            (log_id, exercise_type, details, duration_minutes),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_daily_log_fields(log_id: int, fields: dict):
    """Patch specific columns of an existing daily_logs row (used by /log
    to fill in sleep/steps/mood/etc. incrementally after
    get_or_create_daily_log, instead of requiring the whole day up front)."""
    allowed = {
        "total_sleep_minutes", "steps", "mood", "weight_kg", "hydration_level",
        "stress_level", "menstrual_cycle_day", "task_completion", "focus_level",
        "selfie_path", "posture_pic_path",
    }
    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        return
    conn = get_db_connection()
    try:
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(f"UPDATE daily_logs SET {set_clause} WHERE log_id = ?",
                     (*fields.values(), log_id))
        if "weight_kg" in fields and fields["weight_kg"]:
            row = conn.execute("SELECT user_id FROM daily_logs WHERE log_id = ?", (log_id,)).fetchone()
            if row:
                conn.execute("UPDATE users SET current_weight_kg = ? WHERE user_id = ?",
                             (fields["weight_kg"], row["user_id"]))
        conn.commit()
    finally:
        conn.close()


# ----------------------------- chat messages (v2) ---------------------------

def add_chat_message(user_id: int, role: str, content: str) -> int:
    conn = get_db_connection()
    try:
        cur = conn.execute(
            "INSERT INTO chat_messages (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_recent_chat_messages(user_id: int, limit: int) -> list[dict]:
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM chat_messages WHERE user_id = ? ORDER BY message_id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]
    finally:
        conn.close()


def delete_chat_messages_before(user_id: int, before_message_id: int):
    conn = get_db_connection()
    try:
        conn.execute(
            "DELETE FROM chat_messages WHERE user_id = ? AND message_id < ? AND role != 'summary'",
            (user_id, before_message_id),
        )
        conn.commit()
    finally:
        conn.close()


# ----------------------------- semantic memory (v2) -------------------------

def add_user_memory(user_id: int, category: str, fact: str, embedding: list[float],
                     confidence: float, evidence_start_date: str, evidence_end_date: str) -> int:
    conn = get_db_connection()
    try:
        cur = conn.execute(
            """INSERT INTO user_memory
               (user_id, category, fact, embedding, confidence,
                evidence_start_date, evidence_end_date)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, category, fact, json.dumps(embedding), confidence,
             evidence_start_date, evidence_end_date),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def reinforce_user_memory(memory_id: int, new_evidence_end_date: str, confidence_bump: float = 0.05):
    conn = get_db_connection()
    try:
        conn.execute(
            """UPDATE user_memory
               SET reinforcement_count = reinforcement_count + 1,
                   confidence = MIN(1.0, confidence + ?),
                   evidence_end_date = ?,
                   updated_at = CURRENT_TIMESTAMP
               WHERE memory_id = ?""",
            (confidence_bump, new_evidence_end_date, memory_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_all_user_memory(user_id: int) -> list[dict]:
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM user_memory WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["embedding"] = json.loads(d["embedding"])
            out.append(d)
        return out
    finally:
        conn.close()


def log_memory_consolidation_run(user_id: int, window_start: str, window_end: str,
                                  facts_created: int, facts_reinforced: int):
    conn = get_db_connection()
    try:
        conn.execute(
            """INSERT INTO memory_consolidation_runs
               (user_id, window_start, window_end, facts_created, facts_reinforced)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, window_start, window_end, facts_created, facts_reinforced),
        )
        conn.commit()
    finally:
        conn.close()


# ----------------------------- RAG dish store (v2) --------------------------

def bulk_insert_rag_dishes(rows: list[dict]):
    conn = get_db_connection()
    try:
        conn.executemany(
            """INSERT INTO rag_dishes
               (state, dish_name, meal_type, description, preference,
                primary_nutrient, secondary_nutrient, tertiary_nutrient,
                quaternary_nutrient, embedding)
               VALUES (:state, :dish_name, :meal_type, :description, :preference,
                       :primary_nutrient, :secondary_nutrient, :tertiary_nutrient,
                       :quaternary_nutrient, :embedding)""",
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def rag_dishes_count() -> int:
    conn = get_db_connection()
    try:
        return conn.execute("SELECT COUNT(*) FROM rag_dishes").fetchone()[0]
    finally:
        conn.close()


def get_all_rag_dishes(only_embedded: bool = True) -> list[dict]:
    conn = get_db_connection()
    try:
        query = "SELECT * FROM rag_dishes"
        if only_embedded:
            query += " WHERE embedding IS NOT NULL"
        rows = conn.execute(query).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            if d.get("embedding"):
                d["embedding"] = json.loads(d["embedding"])
            out.append(d)
        return out
    finally:
        conn.close()


# ----------------------------- agent traces (v2) -----------------------------

def add_agent_trace(user_id: int, intent: str, nodes_executed: list[str], latency_ms: int) -> int:
    conn = get_db_connection()
    try:
        cur = conn.execute(
            "INSERT INTO agent_traces (user_id, intent, nodes_executed, latency_ms) VALUES (?, ?, ?, ?)",
            (user_id, intent, json.dumps(nodes_executed), latency_ms),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_recent_agent_traces(user_id: int, limit: int = 20) -> list[dict]:
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM agent_traces WHERE user_id = ? ORDER BY trace_id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["nodes_executed"] = json.loads(d["nodes_executed"])
            out.append(d)
        return out
    finally:
        conn.close()


# ----------------------------- reports ---------------------------------------

def add_report_record(user_id: int, report_type: str, start_date: str, end_date: str, file_path: str) -> int:
    conn = get_db_connection()
    try:
        cur = conn.execute(
            """INSERT INTO reports (user_id, report_type, start_date, end_date, file_path)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, report_type, start_date, end_date, file_path),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
