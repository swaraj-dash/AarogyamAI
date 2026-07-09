"""
/profile — view profile; /setgoal, /setdiet, /setweight — quick single-field
edits without re-running the whole onboarding flow (a real usability gap in
v1, which had no update path for a changed health goal or diet at all).
"""
from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

import database as db


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("Please run /start first to set up your profile.")
        return

    lines = [
        f"Name: {user['name']}", f"Location: {user['city']}, {user['location_state']}",
        f"Diet: {user['food_preference']}", f"Goal: {user['health_goal']}",
        f"Preferred exercise: {user.get('preferred_exercise') or '-'}",
        f"Current weight: {user.get('current_weight_kg') or '-'} kg",
    ]
    await update.message.reply_text(
        "\n".join(lines) + "\n\nUse /setgoal, /setdiet, or /setweight to update these."
    )


async def set_goal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not db.user_exists(user_id):
        await update.message.reply_text("Please run /start first.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /setgoal <your new health goal>")
        return
    goal = " ".join(context.args)
    db.update_user_field(user_id, "health_goal", goal)
    await update.message.reply_text(f"Updated your goal to: {goal}")


async def set_diet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not db.user_exists(user_id):
        await update.message.reply_text("Please run /start first.")
        return
    if not context.args or context.args[0].lower() not in ("vegetarian", "non-vegetarian", "vegan"):
        await update.message.reply_text("Usage: /setdiet <vegetarian|non-vegetarian|vegan>")
        return
    diet = context.args[0].lower()
    db.update_user_field(user_id, "food_preference", diet)
    await update.message.reply_text(f"Updated your diet preference to: {diet}")


async def set_weight_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not db.user_exists(user_id):
        await update.message.reply_text("Please run /start first.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /setweight <kg>")
        return
    try:
        weight = float(context.args[0])
    except ValueError:
        await update.message.reply_text("Please send weight as a number, e.g. /setweight 62.5")
        return
    db.update_user_field(user_id, "current_weight_kg", weight)
    await update.message.reply_text(f"Updated your weight to: {weight} kg")


def build_handlers() -> list:
    return [
        CommandHandler("profile", profile_command),
        CommandHandler("setgoal", set_goal_command),
        CommandHandler("setdiet", set_diet_command),
        CommandHandler("setweight", set_weight_command),
    ]
