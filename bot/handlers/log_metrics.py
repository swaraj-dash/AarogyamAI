"""
/log conversation — records today's sleep, steps, mood, weight, hydration,
stress. Uses get_or_create_daily_log + update_daily_log_fields (incremental
patch) rather than v1's pattern of requiring the whole day's data at once,
so partial logging (e.g. just steps, forgot sleep) doesn't force overwriting
other fields with blanks.
"""
from __future__ import annotations

from datetime import date

from telegram import Update
from telegram.ext import (
    CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters,
)

import database as db

SLEEP, STEPS, MOOD, WEIGHT, HYDRATION, STRESS = range(6)

MOOD_OPTIONS = {"great", "good", "okay", "low", "bad"}
STRESS_OPTIONS = {"low", "medium", "high"}


def _require_registered(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not db.user_exists(update.effective_user.id):
            await update.message.reply_text("Please run /start first to set up your profile.")
            return ConversationHandler.END
        return await func(update, context)
    return wrapper


@_require_registered
async def log_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["log_date"] = date.today().isoformat()
    await update.message.reply_text("How many hours did you sleep last night? (e.g. 7.5)")
    return SLEEP


async def sleep_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        hours = float(update.message.text.strip())
        context.user_data["log_hours_sleep"] = hours
    except ValueError:
        await update.message.reply_text("Please send a number of hours, e.g. 7.5")
        return SLEEP
    await update.message.reply_text("How many steps did you take today?")
    return STEPS


async def steps_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["log_steps"] = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Please send a whole number, e.g. 8000")
        return STEPS
    await update.message.reply_text(f"How's your mood today? ({'/'.join(MOOD_OPTIONS)})")
    return MOOD


async def mood_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    mood = update.message.text.strip().lower()
    if mood not in MOOD_OPTIONS:
        await update.message.reply_text(f"Please pick one of: {', '.join(MOOD_OPTIONS)}")
        return MOOD
    context.user_data["log_mood"] = mood
    await update.message.reply_text("Current weight in kg? (or send 'skip')")
    return WEIGHT


async def weight_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    if text != "skip":
        try:
            context.user_data["log_weight"] = float(text)
        except ValueError:
            await update.message.reply_text("Please send weight as a number, or 'skip'")
            return WEIGHT
    await update.message.reply_text("Litres of water so far today?")
    return HYDRATION


async def hydration_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["log_hydration"] = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Please send a number, e.g. 2.0")
        return HYDRATION
    await update.message.reply_text(f"Stress level today? ({'/'.join(STRESS_OPTIONS)})")
    return STRESS


async def stress_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    stress = update.message.text.strip().lower()
    if stress not in STRESS_OPTIONS:
        await update.message.reply_text(f"Please pick one of: {', '.join(STRESS_OPTIONS)}")
        return STRESS

    user_id = update.effective_user.id
    log_id = db.get_or_create_daily_log(user_id, context.user_data["log_date"])
    db.update_daily_log_fields(log_id, {
        "total_sleep_minutes": int(context.user_data["log_hours_sleep"] * 60),
        "steps": context.user_data["log_steps"],
        "mood": context.user_data["log_mood"],
        "weight_kg": context.user_data.get("log_weight"),
        "hydration_level": context.user_data["log_hydration"],
        "stress_level": stress,
    })

    await update.message.reply_text(
        "Logged for today! Use /logfood to add meals, or /chat to talk about how you're doing."
    )
    for key in ("log_date", "log_hours_sleep", "log_steps", "log_mood", "log_weight", "log_hydration"):
        context.user_data.pop(key, None)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Logging cancelled.")
    return ConversationHandler.END


def build_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("log", log_start)],
        states={
            SLEEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, sleep_step)],
            STEPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, steps_step)],
            MOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, mood_step)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight_step)],
            HYDRATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, hydration_step)],
            STRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, stress_step)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
