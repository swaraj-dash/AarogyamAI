"""
/logfood — appends a single meal to today's log without touching anything
else that day (uses get_or_create_daily_log + add_food_entry_only).
Accepts either a photo (saved to disk, path stored) or a text description.
"""
from __future__ import annotations

import os
import uuid
from datetime import date

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters,
)

import config
import database as db

MEAL_TYPE, DESCRIPTION_OR_PHOTO = range(2)

MEAL_KEYBOARD = ReplyKeyboardMarkup(
    [["Breakfast", "Lunch"], ["Dinner", "Snack"]], one_time_keyboard=True, resize_keyboard=True
)


async def logfood_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not db.user_exists(update.effective_user.id):
        await update.message.reply_text("Please run /start first to set up your profile.")
        return ConversationHandler.END
    await update.message.reply_text("Which meal is this?", reply_markup=MEAL_KEYBOARD)
    return MEAL_TYPE


async def meal_type_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["food_meal_type"] = update.message.text.strip().lower()
    await update.message.reply_text(
        "Send a photo of the meal, or just describe it in text.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return DESCRIPTION_OR_PHOTO


async def description_or_photo_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    meal_type = context.user_data.pop("food_meal_type", "snack")
    log_id = db.get_or_create_daily_log(user_id, date.today().isoformat())

    if update.message.photo:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        os.makedirs(os.path.join(config.UPLOAD_DIR, "food"), exist_ok=True)
        filename = f"{user_id}_{uuid.uuid4().hex[:8]}.jpg"
        filepath = os.path.join(config.UPLOAD_DIR, "food", filename)
        await file.download_to_drive(filepath)
        description = (update.message.caption or "").strip() or None
        db.add_food_entry_only(log_id, meal_type, description=description, food_image_path=filepath)
    else:
        description = update.message.text.strip()
        db.add_food_entry_only(log_id, meal_type, description=description)

    await update.message.reply_text(f"Logged your {meal_type}. Send /logfood again for another meal.")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("food_meal_type", None)
    await update.message.reply_text("Food logging cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def build_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("logfood", logfood_start)],
        states={
            MEAL_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, meal_type_step)],
            DESCRIPTION_OR_PHOTO: [MessageHandler(
                (filters.TEXT | filters.PHOTO) & ~filters.COMMAND, description_or_photo_step
            )],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
