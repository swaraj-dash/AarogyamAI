import json
import os
from datetime import datetime, timedelta

import database as db
import config
from embeddings import DeterministicHashEmbedder
from llm_client import FakeLLMClient
from services.report_generator import sanitize_text, build_report_pdf
from services.memory_service import SemanticMemory
from services import report_service


def test_sanitize_text_replaces_known_emoji_with_label():
    result = sanitize_text("Great job! 🎉 Keep it up 💪")
    assert "🎉" not in result
    assert "[celebrate]" in result
    assert "[strength]" in result


def test_sanitize_text_marks_unknown_emoji_instead_of_dropping():
    result = sanitize_text("Unusual emoji here 🦄")
    assert "🦄" not in result
    assert "[icon]" in result


def test_sanitize_text_handles_empty_string():
    assert sanitize_text("") == ""
    assert sanitize_text(None) == ""


def test_build_report_pdf_creates_file(tmp_path, sample_user):
    user = db.get_user(sample_user)
    summary = {"n_days_logged": 5, "wellness_score": 78.5,
               "averages": {"steps": 8000, "total_sleep_minutes": 420}}
    filepath = build_report_pdf(
        user=user, start_date="2026-06-01", end_date="2026-06-07",
        summary=summary, notable_patterns=["steps increasing 🔥"],
        semantic_memories=[{"fact": "Sleep drops on weekends", "category": "sleep"}],
        narrative="You're doing great! 🎉 Keep up the good work 💪.",
        output_dir=str(tmp_path),
    )
    assert os.path.exists(filepath)
    assert os.path.getsize(filepath) > 0


def test_generate_report_end_to_end(sample_user, monkeypatch):
    monkeypatch.setattr(config, "REPORT_DIR", str(config.BASE_DIR) + "/generated_reports")
    today = datetime.now().date()
    for d in range(1, 8):
        db.add_daily_log({
            "user_id": sample_user,
            "log_date": (today - timedelta(days=d)).isoformat(),
            "total_sleep_minutes": 400 + d * 5, "steps": 7000 + d * 200,
            "mood": "good", "weight_kg": 60.0,
        })

    llm = FakeLLMClient(default_response="You've been making steady progress this week!")
    sm = SemanticMemory(llm=llm, embedder=DeterministicHashEmbedder(dim=64))

    result = report_service.generate_report(
        sample_user,
        (today - timedelta(days=7)).isoformat(),
        today.isoformat(),
        llm=llm, semantic_memory=sm,
    )
    assert os.path.exists(result["filepath"])
    assert result["summary"]["n_days_logged"] == 7
    assert "steady progress" in result["narrative"]

    reports = db.get_db_connection().execute(
        "SELECT * FROM reports WHERE user_id = ?", (sample_user,)
    ).fetchall()
    assert len(reports) == 1
