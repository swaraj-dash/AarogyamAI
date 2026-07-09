"""
/start onboarding conversation.

Collects the profile fields needed for personalization (health goal, diet,
state/city for RAG regional matching, medical context) and creates the
user row. Kept as a straightforward linear ConversationHandler — the same
approach as v1, since this part of v1 wasn't actually broken.
"""
from __future__ import annotations

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters,
)

import database as db

(NAME, DOB, HEIGHT, GENDER, STATE, CITY, FOOD_PREF, HEALTH_GOAL,
 EXERCISE_PREF, MEDICAL, DONE) = range(11)

GENDER_KEYBOARD = ReplyKeyboardMarkup([["Male", "Female", "Other"]], one_time_keyboard=True, resize_keyboard=True)
FOOD_PREF_KEYBOARD = ReplyKeyboardMarkup(
    [["Vegetarian", "Non-vegetarian", "Vegan"]], one_time_keyboard=True, resize_keyboard=True
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if db.user_exists(user_id):
        await update.message.reply_text(
            "Welcome back! Use /chat to talk to me, /log to record today, or /report for a summary."
        )
        return ConversationHandler.END

    context.user_data["onboarding"] = {}
    await update.message.reply_text(
        "Welcome to AarogyamAI! Let's set up your profile.\nWhat's your name?",
        reply_markup=ReplyKeyboardRemove(),
    )
    return NAME


async def name_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["onboarding"]["name"] = update.message.text.strip()
    await update.message.reply_text("Date of birth? (YYYY-MM-DD)")
    return DOB


async def dob_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["onboarding"]["dob"] = update.message.text.strip()
    await update.message.reply_text("Height in cm?")
    return HEIGHT


async def height_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["onboarding"]["height_cm"] = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Please send height as a number, e.g. 170")
        return HEIGHT
    await update.message.reply_text("Gender?", reply_markup=GENDER_KEYBOARD)
    return GENDER


async def gender_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["onboarding"]["gender"] = update.message.text.strip()
    await update.message.reply_text("Which state do you live in?", reply_markup=ReplyKeyboardRemove())
    return STATE


async def state_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["onboarding"]["location_state"] = update.message.text.strip()
    await update.message.reply_text("Which city?")
    return CITY


async def city_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["onboarding"]["city"] = update.message.text.strip()
    await update.message.reply_text("Dietary preference?", reply_markup=FOOD_PREF_KEYBOARD)
    return FOOD_PREF


async def food_pref_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["onboarding"]["food_preference"] = update.message.text.strip().lower()
    await update.message.reply_text(
        "What's your main health goal? (e.g. lose weight, build strength, improve energy)",
        reply_markup=ReplyKeyboardRemove(),
    )
    return HEALTH_GOAL


async def health_goal_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["onboarding"]["health_goal"] = update.message.text.strip()
    await update.message.reply_text("Preferred type of exercise? (or 'none')")
    return EXERCISE_PREF


async def exercise_pref_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["onboarding"]["preferred_exercise"] = update.message.text.strip()
    await update.message.reply_text(
        "Any medical conditions, medications, or allergies I should know about? (or 'none')"
    )
    return MEDICAL


async def medical_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["onboarding"]["medical_conditions"] = update.message.text.strip()
    onboarding = context.user_data["onboarding"]

    user_id = db.add_user(onboarding, user_id=update.effective_user.id)
    await update.message.reply_text(
        f"You're all set, {onboarding['name']}! Your AarogyamAI ID is {user_id} "
        "(use this to log in on the web dashboard too).\n\n"
        "Try /log to record today, /chat to talk to me, or /report for a summary."
    )
    context.user_data.pop("onboarding", None)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("onboarding", None)
    await update.message.reply_text("Setup cancelled. Send /start to try again.",
                                     reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def build_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name_step)],
            DOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, dob_step)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, height_step)],
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, gender_step)],
            STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, state_step)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, city_step)],
            FOOD_PREF: [MessageHandler(filters.TEXT & ~filters.COMMAND, food_pref_step)],
            HEALTH_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, health_goal_step)],
            EXERCISE_PREF: [MessageHandler(filters.TEXT & ~filters.COMMAND, exercise_pref_step)],
            MEDICAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, medical_step)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
