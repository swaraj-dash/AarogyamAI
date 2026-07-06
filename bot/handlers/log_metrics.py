import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
import database as db
import config

# Logging states
SLEEP, STEPS, MOOD, STRESS, HYDRATION, WEIGHT, TASKS, FOCUS, SELFIE, POSTURE = range(10)

# UPLOAD DIR
UPLOAD_DIR = config.UPLOAD_DIR

async def start_log(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Initiates the daily log process."""
    user_id = update.effective_user.id
    if not db.user_exists(user_id):
        await update.message.reply_text("Please register first using /start before logging.")
        return ConversationHandler.END

    # Initialize log session in user_data
    context.user_data['daily_log'] = {
        'user_id': user_id,
        'log_date': datetime.now().strftime('%Y-%m-%d'),
        'total_sleep_minutes': 480, # default 8 hours
        'steps': 5000,
        'mood': '😐 Neutral',
        'weight_kg': 70.0,
        'selfie_path': None,
        'posture_pic_path': None,
        'travel_info': {'km': 0, 'mode': 'None', 'location_changed': False, 'new_city': None, 'new_state': None},
        'hydration_level': 2.0,
        'stress_level': 'Mild',
        'menstrual_cycle_day': None,
        'task_completion': 'A Few',
        'focus_level': 'Medium',
        'food_entries': [],
        'exercise_entries': []
    }

    # Fetch last recorded weight to pre-fill
    user = db.get_user(user_id)
    # Note: Streamlit onboarding saved weight inside user info if available, or logs
    # SQLite schema doesn't have weight directly on user, but we can default to 70
    
    await update.message.reply_text(
        "Let's log your day! 📅\n"
        "How many hours of sleep did you get last night? (e.g. 7.5)"
    )
    return SLEEP

async def get_sleep(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores sleep and asks for steps."""
    try:
        hours = float(update.message.text.strip())
        context.user_data['daily_log']['total_sleep_minutes'] = int(hours * 60)
    except ValueError:
        await update.message.reply_text("Please enter a valid number of sleep hours (e.g., 7 or 8.5).")
        return SLEEP

    await update.message.reply_text("How many steps did you walk today? (e.g., 8500)")
    return STEPS

async def get_steps(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores steps and asks for mood."""
    try:
        steps = int(update.message.text.strip())
        context.user_data['daily_log']['steps'] = steps
    except ValueError:
        await update.message.reply_text("Please enter a valid step count number.")
        return STEPS

    reply_keyboard = [
        ["🤩 Ecstatic", "😁 Great", "🙂 Happy"],
        ["😊 Okay", "😐 Neutral", "😟 Anxious"],
        ["😞 Sad", "😭 Awful"]
    ]
    await update.message.reply_text(
        "How is your mood today?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return MOOD

async def get_mood(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores mood and asks for stress level."""
    context.user_data['daily_log']['mood'] = update.message.text
    
    reply_keyboard = [["Low", "Mild", "High"]]
    await update.message.reply_text(
        "What is your stress level today?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return STRESS

async def get_stress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores stress level and asks for hydration."""
    context.user_data['daily_log']['stress_level'] = update.message.text
    
    reply_keyboard = [
        ["1.0L", "1.5L", "2.0L"],
        ["2.5L", "3.0L", "3.5L", "4.0L"]
    ]
    await update.message.reply_text(
        "How much water did you drink today?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return HYDRATION

async def get_hydration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores hydration and asks for weight."""
    text = update.message.text.strip().replace("L", "")
    try:
        liters = float(text)
        context.user_data['daily_log']['hydration_level'] = liters
    except ValueError:
        await update.message.reply_text("Please select a water amount or type a number in liters (e.g. 2.5).")
        return HYDRATION

    await update.message.reply_text(
        "What is your current weight in kg? (e.g. 68.4)",
        reply_markup=ReplyKeyboardRemove()
    )
    return WEIGHT

async def get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores weight and asks for task completion."""
    try:
        weight = float(update.message.text.strip())
        context.user_data['daily_log']['weight_kg'] = weight
    except ValueError:
        await update.message.reply_text("Please enter a valid weight number in kg.")
        return WEIGHT

    reply_keyboard = [["None", "A Few", "Majority", "All"]]
    await update.message.reply_text(
        "How many of your daily tasks did you complete?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return TASKS

async def get_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores tasks and asks for focus level."""
    context.user_data['daily_log']['task_completion'] = update.message.text
    
    reply_keyboard = [["Low", "Medium", "High"]]
    await update.message.reply_text(
        "What was your focus level today?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return FOCUS

async def get_focus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores focus level and asks for a selfie photo."""
    context.user_data['daily_log']['focus_level'] = update.message.text
    
    await update.message.reply_text(
        "Almost done! 📸\n"
        "Send a selfie for comparative skin clarity/tiredness analysis, or send /skip to skip.",
        reply_markup=ReplyKeyboardRemove()
    )
    return SELFIE

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE, subdir: str) -> str:
    """Helper to download and save an image from Telegram."""
    photo = update.message.photo[-1]
    file = await photo.get_file()
    
    os.makedirs(os.path.join(UPLOAD_DIR, subdir), exist_ok=True)
    timestamp = int(datetime.now().timestamp())
    filename = f"{update.effective_user.id}_{timestamp}_{subdir}.jpg"
    file_path = os.path.join(UPLOAD_DIR, subdir, filename)
    
    await file.download_to_drive(file_path)
    return file_path

async def get_selfie(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores selfie path and asks for posture photo."""
    if update.message.photo:
        file_path = await handle_image(update, context, "profile")
        context.user_data['daily_log']['selfie_path'] = file_path
        await update.message.reply_text("Selfie saved successfully!")
    elif update.message.text == "/skip":
        await update.message.reply_text("Selfie skipped.")
    else:
        await update.message.reply_text("Please upload a photo, or send /skip to skip.")
        return SELFIE

    await update.message.reply_text(
        "Now send a side-profile posture photo for posture feedback, or send /skip to skip."
    )
    return POSTURE

async def get_posture(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores posture path and completes metrics logging."""
    if update.message.photo:
        file_path = await handle_image(update, context, "profile")
        context.user_data['daily_log']['posture_pic_path'] = file_path
        await update.message.reply_text("Posture photo saved successfully!")
    elif update.message.text == "/skip":
        await update.message.reply_text("Posture photo skipped.")
    else:
        await update.message.reply_text("Please upload a photo, or send /skip to skip.")
        return POSTURE

    # Let's save the progress
    # We keep the logging session open in user_data so they can add food/exercises
    await update.message.reply_text(
        "✅ Daily metrics saved!\n\n"
        "To make your report useful, you should log your meals and exercises:\n"
        "🍽️ Send any food image or type what you ate to log a meal.\n"
        "🏋️ Send /workout to generate a plan and mark exercises completed.\n"
        "🚀 Send /submit when you are ready to generate your daily PDF wellness report!"
    )
    return ConversationHandler.END

async def cancel_log(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the daily log conversation."""
    context.user_data.pop('daily_log', None)
    await update.message.reply_text(
        "Daily logging cancelled. Your progress has been discarded.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def get_log_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("log", start_log)],
        states={
            SLEEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_sleep)],
            STEPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_steps)],
            MOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mood)],
            STRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_stress)],
            HYDRATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_hydration)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight)],
            TASKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tasks)],
            FOCUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_focus)],
            SELFIE: [
                MessageHandler(filters.PHOTO, get_selfie),
                CommandHandler("skip", get_selfie)
            ],
            POSTURE: [
                MessageHandler(filters.PHOTO, get_posture),
                CommandHandler("skip", get_posture)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_log)],
    )
