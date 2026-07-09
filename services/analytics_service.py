"""
Analytics service.

v1's "trend" logic (per the original docs) was a first-value-vs-last-value
diff — noisy for anything with day-to-day variance (sleep, mood, steps),
and it says nothing about whether a trend is a real pattern or just noise
in a 7-day window.

v2 fits a simple linear regression (numpy.polyfit, degree 1) over the time
series and reports both the slope (direction + magnitude, in real units per
day) and R² (how much of the variance the trend line actually explains).
An R² near 0 means "this metric bounced around, don't tell the user it's
'improving' or 'declining'" — a materially more honest signal than a two-point
diff, and exactly the kind of distinction a health app should not gloss over.
"""
from __future__ import annotations

from datetime import datetime

import numpy as np


def _extract_series(logs: list[dict], field: str) -> tuple[list[float], list[float]]:
    """Returns (day_offsets, values) for logs where `field` is not None,
    day_offsets normalized to 0..N so regression coefficients are in
    'per day' units regardless of the actual calendar range."""
    dated = [(l["log_date"], l.get(field)) for l in logs if l.get(field) is not None]
    if not dated:
        return [], []
    dated.sort(key=lambda x: x[0])
    base = datetime.strptime(dated[0][0], "%Y-%m-%d")
    xs = [(datetime.strptime(d, "%Y-%m-%d") - base).days for d, _ in dated]
    ys = [float(v) for _, v in dated]
    return xs, ys


def compute_trend(logs: list[dict], field: str) -> dict:
    xs, ys = _extract_series(logs, field)
    if len(xs) < 3:
        return {"field": field, "direction": "insufficient_data", "slope_per_day": 0.0,
                "r_squared": 0.0, "n_points": len(xs)}

    x = np.array(xs, dtype=np.float64)
    y = np.array(ys, dtype=np.float64)
    slope, intercept = np.polyfit(x, y, 1)

    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 0.0 if ss_tot == 0 else float(1 - ss_res / ss_tot)

    # A trend only "counts" as a real direction if it explains a reasonable
    # share of the variance; otherwise we call it flat/noisy rather than
    # overclaiming a pattern from scatter.
    if r_squared < 0.15:
        direction = "flat_or_noisy"
    elif slope > 0:
        direction = "increasing"
    else:
        direction = "decreasing"

    return {
        "field": field,
        "direction": direction,
        "slope_per_day": round(float(slope), 4),
        "r_squared": round(r_squared, 3),
        "n_points": len(xs),
        "mean": round(float(np.mean(y)), 2),
    }


TRACKED_NUMERIC_FIELDS = ["total_sleep_minutes", "steps", "weight_kg", "hydration_level"]

MOOD_SCORE_MAP = {"great": 5, "good": 4, "okay": 3, "low": 2, "bad": 1}


def compute_summary(logs: list[dict]) -> dict:
    """Aggregate averages + trends across a window of logs."""
    if not logs:
        return {"n_days_logged": 0, "trends": {}, "averages": {}, "wellness_score": None}

    trends = {field: compute_trend(logs, field) for field in TRACKED_NUMERIC_FIELDS}

    averages = {}
    for field in TRACKED_NUMERIC_FIELDS:
        vals = [l[field] for l in logs if l.get(field) is not None]
        averages[field] = round(sum(vals) / len(vals), 2) if vals else None

    mood_scores = [MOOD_SCORE_MAP.get((l.get("mood") or "").lower()) for l in logs]
    mood_scores = [m for m in mood_scores if m is not None]
    avg_mood = sum(mood_scores) / len(mood_scores) if mood_scores else None

    return {
        "n_days_logged": len(logs),
        "trends": trends,
        "averages": averages,
        "avg_mood_score": round(avg_mood, 2) if avg_mood is not None else None,
        "wellness_score": compute_wellness_score(averages, avg_mood),
    }


def compute_wellness_score(averages: dict, avg_mood_score: float | None) -> float | None:
    """0-100 composite score. Simple weighted normalization — deliberately
    transparent/explainable (each component's contribution is inspectable)
    rather than an opaque single ML model, since users/reviewers should be
    able to see *why* the score is what it is."""
    components = []

    sleep_min = averages.get("total_sleep_minutes")
    if sleep_min is not None:
        # 7-9h (420-540 min) treated as ideal; score tapers off outside that band
        ideal_low, ideal_high = 420, 540
        if ideal_low <= sleep_min <= ideal_high:
            components.append(100.0)
        else:
            distance = min(abs(sleep_min - ideal_low), abs(sleep_min - ideal_high))
            components.append(max(0.0, 100.0 - distance / 3))

    steps = averages.get("steps")
    if steps is not None:
        components.append(min(100.0, (steps / 10000) * 100))

    hydration = averages.get("hydration_level")
    if hydration is not None:
        components.append(min(100.0, (hydration / 3.0) * 100))  # assume 3L target

    if avg_mood_score is not None:
        components.append((avg_mood_score / 5.0) * 100)

    if not components:
        return None
    return round(sum(components) / len(components), 1)


def detect_notable_patterns(logs: list[dict]) -> list[str]:
    """Human-readable flags for anything worth surfacing in a report or
    feeding into the memory-consolidation prompt as a hint."""
    if len(logs) < 3:
        return []
    notes = []
    summary = compute_summary(logs)
    for field, trend in summary["trends"].items():
        if trend["direction"] in ("increasing", "decreasing") and trend["r_squared"] >= 0.3:
            label = field.replace("_", " ")
            notes.append(
                f"{label} is {trend['direction']} at ~{abs(trend['slope_per_day']):.2f}/day "
                f"(R²={trend['r_squared']}, n={trend['n_points']})"
            )
    return notes
