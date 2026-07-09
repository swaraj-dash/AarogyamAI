"""
/bmi — a deterministic, no-LLM utility command. Kept separate from the
agent graph deliberately: not everything needs an LLM in the loop, and a
BMI calculation should never be non-deterministic or cost a model call.
"""
from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

import database as db


def _bmi_category(bmi: float) -> str:
    if bmi < 18.5:
        return "underweight"
    if bmi < 25:
        return "normal weight"
    if bmi < 30:
        return "overweight"
    return "obese"


async def bmi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("Please run /start first to set up your profile.")
        return
    if not user.get("current_weight_kg"):
        await update.message.reply_text("I don't have a recent weight — log one with /log or /setweight.")
        return

    height_m = user["height_cm"] / 100
    bmi = user["current_weight_kg"] / (height_m ** 2)
    category = _bmi_category(bmi)
    await update.message.reply_text(f"BMI: {bmi:.1f} ({category})")


def build_handlers() -> list:
    return [CommandHandler("bmi", bmi_command)]
