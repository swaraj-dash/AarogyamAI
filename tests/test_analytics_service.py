from services.analytics_service import (
    compute_trend, compute_summary, compute_wellness_score, detect_notable_patterns,
)


def _log(date, sleep_min=420, steps=8000, mood="good", weight=60.0, hydration=2.5):
    return {
        "log_date": date, "total_sleep_minutes": sleep_min, "steps": steps,
        "mood": mood, "weight_kg": weight, "hydration_level": hydration,
        "food_entries": [], "exercise_entries": [],
    }


def test_compute_trend_detects_clear_increase():
    logs = [_log(f"2026-06-{d:02d}", steps=5000 + d * 500) for d in range(1, 11)]
    trend = compute_trend(logs, "steps")
    assert trend["direction"] == "increasing"
    assert trend["r_squared"] > 0.9
    assert trend["slope_per_day"] > 0


def test_compute_trend_detects_clear_decrease():
    logs = [_log(f"2026-06-{d:02d}", sleep_min=500 - d * 10) for d in range(1, 11)]
    trend = compute_trend(logs, "total_sleep_minutes")
    assert trend["direction"] == "decreasing"
    assert trend["slope_per_day"] < 0


def test_compute_trend_flat_noisy_data_not_overclaimed():
    import random
    random.seed(42)
    logs = [_log(f"2026-06-{d:02d}", steps=8000 + random.randint(-50, 50)) for d in range(1, 11)]
    trend = compute_trend(logs, "steps")
    assert trend["direction"] == "flat_or_noisy"


def test_compute_trend_insufficient_data():
    logs = [_log("2026-06-01"), _log("2026-06-02")]
    trend = compute_trend(logs, "steps")
    assert trend["direction"] == "insufficient_data"


def test_compute_summary_averages():
    logs = [_log(f"2026-06-{d:02d}", steps=10000) for d in range(1, 6)]
    summary = compute_summary(logs)
    assert summary["averages"]["steps"] == 10000
    assert summary["n_days_logged"] == 5


def test_compute_summary_empty_logs():
    summary = compute_summary([])
    assert summary["n_days_logged"] == 0
    assert summary["wellness_score"] is None


def test_wellness_score_ideal_values_score_high():
    averages = {"total_sleep_minutes": 480, "steps": 10000, "hydration_level": 3.0}
    score = compute_wellness_score(averages, avg_mood_score=5.0)
    assert score == 100.0


def test_wellness_score_poor_values_score_low():
    averages = {"total_sleep_minutes": 180, "steps": 1000, "hydration_level": 0.5}
    score = compute_wellness_score(averages, avg_mood_score=1.0)
    assert score < 50.0


def test_detect_notable_patterns_flags_strong_trend():
    logs = [_log(f"2026-06-{d:02d}", steps=5000 + d * 800) for d in range(1, 11)]
    patterns = detect_notable_patterns(logs)
    assert any("steps" in p for p in patterns)


def test_detect_notable_patterns_short_window_returns_empty():
    logs = [_log("2026-06-01"), _log("2026-06-02")]
    assert detect_notable_patterns(logs) == []
