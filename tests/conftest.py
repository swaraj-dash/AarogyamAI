import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

# Force fully offline/deterministic mode for the whole test session — no
# network calls, no API key required, reproducible embeddings/LLM stubs.
os.environ["AAROGYAM_OFFLINE_MODE"] = "true"
os.environ.setdefault("DATABASE_PATH", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "test_aarogyam.db"
))

import pytest

import config
import database as db


@pytest.fixture(autouse=True)
def fresh_database():
    """Every test gets a clean schema on a throwaway DB file."""
    orig_path = config.DATABASE_PATH
    if os.path.exists(config.DATABASE_PATH):
        try:
            os.remove(config.DATABASE_PATH)
        except PermissionError:
            pass
    db.init_db()
    yield
    if os.path.exists(config.DATABASE_PATH):
        try:
            os.remove(config.DATABASE_PATH)
        except PermissionError:
            pass
    config.DATABASE_PATH = orig_path


@pytest.fixture
def sample_user():
    user_data = {
        "name": "Test User", "dob": "1998-05-14", "height_cm": 172,
        "gender": "female", "location_state": "Kerala", "city": "Kochi",
        "food_preference": "vegetarian", "health_goal": "improve energy levels",
        "preferred_exercise": "yoga",
    }
    user_id = db.add_user(user_data, user_id=100001)
    return user_id
