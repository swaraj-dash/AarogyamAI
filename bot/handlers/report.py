"""
/report — generates and sends a PDF via report_service (analytics +
semantic memory + LLM narrative, see services/report_service.py).

/analytics — a quick in-chat text summary for people who don't need the
full PDF right now.
"""
from __future__ import annotations

from datetime import date, timedelta

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

import database as db
from services import analytics_service, report_service
from services.memory_service import EpisodicMemory


def _parse_days_arg(args: list[str], default_days: int = 7) -> int:
    if args:
        try:
            return max(1, int(args[0]))
        except ValueError:
            pass
    return default_days


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not db.user_exists(user_id):
        await update.message.reply_text("Please run /start first to set up your profile.")
        return

    days = _parse_days_arg(context.args, default_days=7)
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    await update.message.reply_text(f"Generating your {days}-day report...")
    try:
        result = report_service.generate_report(user_id, start_date.isoformat(), end_date.isoformat())
    except Exception as e:
        await update.message.reply_text(f"Couldn't generate the report: {e}")
        return

    with open(result["filepath"], "rb") as f:
        await update.message.reply_document(document=f, filename="AarogyamAI_Report.pdf")


async def analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not db.user_exists(user_id):
        await update.message.reply_text("Please run /start first to set up your profile.")
        return

    days = _parse_days_arg(context.args, default_days=14)
    logs = EpisodicMemory.get_recent_logs(user_id, days)
    summary = analytics_service.compute_summary(logs)
    patterns = analytics_service.detect_notable_patterns(logs)

    if summary["n_days_logged"] == 0:
        await update.message.reply_text("No logs found in that window yet — try /log first.")
        return

    lines = [f"Last {days} days ({summary['n_days_logged']} days logged):"]
    if summary.get("wellness_score") is not None:
        lines.append(f"Wellness score: {summary['wellness_score']}/100")
    for field, val in summary["averages"].items():
        if val is not None:
            lines.append(f"  avg {field.replace('_', ' ')}: {val}")
    if patterns:
        lines.append("\nNotable patterns:")
        lines.extend(f"  - {p}" for p in patterns)

    await update.message.reply_text("\n".join(lines))


def build_handlers() -> list:
    return [
        CommandHandler("report", report_command),
        CommandHandler("analytics", analytics_command),
    ]
