import database as db


def test_add_and_get_user(sample_user):
    user = db.get_user(sample_user)
    assert user["name"] == "Test User"
    assert user["location_state"] == "Kerala"


def test_user_exists(sample_user):
    assert db.user_exists(sample_user) is True
    assert db.user_exists(999999) is False


def test_add_daily_log_upserts_by_date(sample_user):
    log_data = {
        "user_id": sample_user, "log_date": "2026-06-01",
        "total_sleep_minutes": 420, "steps": 8000, "mood": "good",
        "weight_kg": 60.0, "food_entries": [{"meal_type": "breakfast", "description": "Idli"}],
        "exercise_entries": [{"exercise_type": "yoga", "duration_minutes": 30}],
    }
    log_id_1 = db.add_daily_log(log_data)
    full = db.get_full_daily_log(log_id_1)
    assert full["log_details"]["steps"] == 8000
    assert len(full["food_entries"]) == 1

    # re-logging the same date should replace, not duplicate
    log_data["steps"] = 9500
    log_id_2 = db.add_daily_log(log_data)
    logs_in_range = db.get_logs_in_range(sample_user, "2026-06-01", "2026-06-01")
    assert len(logs_in_range) == 1
    assert logs_in_range[0]["steps"] == 9500


def test_daily_log_syncs_current_weight_to_user(sample_user):
    db.add_daily_log({"user_id": sample_user, "log_date": "2026-06-01", "weight_kg": 63.5})
    user = db.get_user(sample_user)
    assert user["current_weight_kg"] == 63.5


def test_chat_messages_persist_and_order(sample_user):
    db.add_chat_message(sample_user, "user", "hello")
    db.add_chat_message(sample_user, "model", "hi there")
    messages = db.get_recent_chat_messages(sample_user, limit=10)
    assert [m["role"] for m in messages] == ["user", "model"]
    assert messages[0]["content"] == "hello"


def test_delete_chat_messages_before_keeps_summaries(sample_user):
    id1 = db.add_chat_message(sample_user, "user", "old message")
    db.add_chat_message(sample_user, "summary", "a summary of old stuff")
    id3 = db.add_chat_message(sample_user, "user", "new message")
    db.delete_chat_messages_before(sample_user, id3)
    remaining = db.get_recent_chat_messages(sample_user, limit=10)
    roles = [m["role"] for m in remaining]
    assert "summary" in roles
    assert "new message" in [m["content"] for m in remaining]
    assert "old message" not in [m["content"] for m in remaining]


def test_user_memory_add_and_retrieve(sample_user):
    mem_id = db.add_user_memory(
        sample_user, "sleep", "Sleep drops on weekends", [0.1, 0.2, 0.3],
        confidence=0.7, evidence_start_date="2026-06-01", evidence_end_date="2026-06-14",
    )
    memories = db.get_all_user_memory(sample_user)
    assert len(memories) == 1
    assert memories[0]["fact"] == "Sleep drops on weekends"
    assert memories[0]["reinforcement_count"] == 1


def test_reinforce_user_memory_increments_count(sample_user):
    mem_id = db.add_user_memory(
        sample_user, "sleep", "Sleep drops on weekends", [0.1, 0.2, 0.3],
        confidence=0.6, evidence_start_date="2026-06-01", evidence_end_date="2026-06-14",
    )
    db.reinforce_user_memory(mem_id, "2026-06-21")
    memories = db.get_all_user_memory(sample_user)
    assert memories[0]["reinforcement_count"] == 2
    assert memories[0]["confidence"] > 0.6
    assert memories[0]["evidence_end_date"] == "2026-06-21"


def test_agent_trace_roundtrip(sample_user):
    db.add_agent_trace(sample_user, "nutrition", ["classify_intent", "nutrition_node"], 120)
    traces = db.get_recent_agent_traces(sample_user)
    assert len(traces) == 1
    assert traces[0]["intent"] == "nutrition"
    assert traces[0]["nodes_executed"] == ["classify_intent", "nutrition_node"]


def test_get_or_create_daily_log_is_idempotent(sample_user):
    log_id_1 = db.get_or_create_daily_log(sample_user, "2026-06-01")
    log_id_2 = db.get_or_create_daily_log(sample_user, "2026-06-01")
    assert log_id_1 == log_id_2


def test_add_food_entry_only_appends_without_wiping_day(sample_user):
    log_id = db.get_or_create_daily_log(sample_user, "2026-06-01")
    db.update_daily_log_fields(log_id, {"steps": 5000, "mood": "good"})
    db.add_food_entry_only(log_id, "breakfast", description="Idli and sambar")
    db.add_food_entry_only(log_id, "lunch", description="Rice and dal")

    full = db.get_full_daily_log(log_id)
    assert full["log_details"]["steps"] == 5000
    assert full["log_details"]["mood"] == "good"
    assert len(full["food_entries"]) == 2


def test_add_exercise_entry_only(sample_user):
    log_id = db.get_or_create_daily_log(sample_user, "2026-06-01")
    db.add_exercise_entry_only(log_id, "yoga", duration_minutes=30)
    full = db.get_full_daily_log(log_id)
    assert full["exercise_entries"][0]["exercise_type"] == "yoga"
    assert full["exercise_entries"][0]["duration_minutes"] == 30


def test_update_daily_log_fields_syncs_weight_to_user(sample_user):
    log_id = db.get_or_create_daily_log(sample_user, "2026-06-01")
    db.update_daily_log_fields(log_id, {"weight_kg": 58.2})
    user = db.get_user(sample_user)
    assert user["current_weight_kg"] == 58.2


def test_update_daily_log_fields_rejects_unknown_columns(sample_user):
    log_id = db.get_or_create_daily_log(sample_user, "2026-06-01")
    # 'user_id' is a real column but not in the allowed patch set - should
    # be silently filtered out rather than corrupting the row's ownership.
    db.update_daily_log_fields(log_id, {"user_id": 999999, "steps": 100})
    full = db.get_full_daily_log(log_id)
    assert full["log_details"]["user_id"] == sample_user
    assert full["log_details"]["steps"] == 100
    rows = [{
        "state": "Kerala", "dish_name": "Puttu", "meal_type": "breakfast",
        "description": "Steamed rice cake", "preference": "vegetarian",
        "primary_nutrient": "carbohydrates", "secondary_nutrient": "fiber",
        "tertiary_nutrient": None, "quaternary_nutrient": None,
        "embedding": "[0.1, 0.2, 0.3]",
    }]
    db.bulk_insert_rag_dishes(rows)
    assert db.rag_dishes_count() == 1
    dishes = db.get_all_rag_dishes()
    assert dishes[0]["dish_name"] == "Puttu"
    assert dishes[0]["embedding"] == [0.1, 0.2, 0.3]
