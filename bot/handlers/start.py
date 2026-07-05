import json
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
import database as db

# Conversation states
NAME, DOB, GENDER, HEIGHT, WEIGHT, STATE, CITY, FOOD, GOAL = range(9)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and asks for the user's name."""
    user_id = update.effective_user.id
    
    if db.user_exists(user_id):
        user = db.get_user(user_id)
        await update.message.reply_text(
            f"Welcome back to AarogyamAI, {user['name']}! 🌱\n\n"
            "Here's what you can do:\n"
            "📝 /log - Log your health metrics & food for today\n"
            "👤 /profile - View and edit your health profile\n"
            "🏋️ /workout - Get today's custom fitness routine\n"
            "📄 /report - Generate your daily PDF wellness report\n"
            "🌿 /alternative - Find eco-friendly alternatives for items\n"
            "💬 /help - Show available commands"
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Welcome to AarogyamAI! 🌱\n"
        "I will be your personal health & wellness companion.\n"
        "Let's create your wellness profile. What is your Full Name?"
    )
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the name and asks for the Date of Birth."""
    context.user_data['name'] = update.message.text
    await update.message.reply_text(
        f"Nice to meet you, {update.message.text}!\n"
        "What is your Date of Birth? (Please use YYYY-MM-DD format, e.g., 1995-08-15)"
    )
    return DOB

async def get_dob(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores DOB and asks for Gender."""
    dob_text = update.message.text.strip()
    # Simple check for format
    try:
        from datetime import datetime
        datetime.strptime(dob_text, "%Y-%m-%d")
        context.user_data['dob'] = dob_text
    except ValueError:
        await update.message.reply_text("Invalid date format. Please send DOB in YYYY-MM-DD format.")
        return DOB

    reply_keyboard = [["Male", "Female"], ["Other", "Prefer not to say"]]
    await update.message.reply_text(
        "What is your Gender?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return GENDER

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores Gender and asks for Height."""
    context.user_data['gender'] = update.message.text
    await update.message.reply_text(
        "What is your height in cm? (e.g. 175)",
        reply_markup=ReplyKeyboardRemove()
    )
    return HEIGHT

async def get_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores Height and asks for Weight."""
    try:
        height = float(update.message.text.strip())
        context.user_data['height_cm'] = height
    except ValueError:
        await update.message.reply_text("Please enter a valid height number in cm.")
        return HEIGHT

    await update.message.reply_text("What is your current weight in kg? (e.g. 70.5)")
    return WEIGHT

async def get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores Weight and asks for Location State."""
    try:
        weight = float(update.message.text.strip())
        context.user_data['current_weight'] = weight
    except ValueError:
        await update.message.reply_text("Please enter a valid weight number in kg.")
        return WEIGHT

    await update.message.reply_text("Which State do you live in? (e.g., Maharashtra)")
    return STATE

async def get_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores State and asks for City."""
    context.user_data['location_state'] = update.message.text.strip()
    await update.message.reply_text("Which City do you live in? (e.g., Mumbai)")
    return CITY

async def get_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores City and asks for Food Preference."""
    context.user_data['city'] = update.message.text.strip()
    
    reply_keyboard = [["Vegetarian", "Vegetarian + Non-Veg"]]
    await update.message.reply_text(
        "What is your Food Preference?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return FOOD

async def get_food(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores Food Preference and asks for Health Goal."""
    context.user_data['food_preference'] = update.message.text
    
    reply_keyboard = [
        ["Weight Loss", "Weight Gain"],
        ["Maintain Weight", "Improve Fitness"],
        ["Manage Stress"]
    ]
    await update.message.reply_text(
        "What is your Primary Health Goal?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return GOAL

async def get_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores Health Goal, saves user profile, and ends conversation."""
    context.user_data['health_goal'] = update.message.text
    user_id = update.effective_user.id
    
    # Save user to DB
    user_data = {
        'name': context.user_data['name'],
        'dob': context.user_data['dob'],
        'height_cm': context.user_data['height_cm'],
        'gender': context.user_data['gender'],
        'location_state': context.user_data['location_state'],
        'city': context.user_data['city'],
        'food_preference': context.user_data['food_preference'],
        'health_goal': context.user_data['health_goal'],
        'preferred_exercise': [], # Optional list starts empty
        'medical_conditions': 'NA',
        'medications': 'NA',
        'allergies': 'NA',
        'surgical_history': 'NA',
        'family_history': 'NA'
    }
    
    db.add_user(user_data, user_id=user_id)
    
    await update.message.reply_text(
        "🎉 Wellness profile created successfully!\n\n"
        "You can now track your metrics daily. Try these commands:\n"
        "📝 /log - Start logging today's activities & food\n"
        "🏋️ /workout - Generate a custom workout plan\n"
        "📄 /report - Get your daily PDF health insights\n"
        "👤 /profile - View your profile details",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Clean up user_data state
    for k in ['name', 'dob', 'gender', 'height_cm', 'current_weight', 'location_state', 'city', 'food_preference', 'health_goal']:
        context.user_data.pop(k, None)
        
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text(
        "Profile onboarding cancelled. You can register anytime using /start.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def get_start_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            DOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_dob)],
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_height)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight)],
            STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_state)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_city)],
            FOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_food)],
            GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_goal)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
