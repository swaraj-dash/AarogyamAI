import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db
import config

UPLOAD_DIR = config.UPLOAD_DIR

def ensure_daily_log_initialized(user_id, context):
    """Ensures there is an active daily log session in context.user_data."""
    if 'daily_log' not in context.user_data or context.user_data['daily_log'] is None:
        context.user_data['daily_log'] = {
            'user_id': user_id,
            'log_date': datetime.now().strftime('%Y-%m-%d'),
            'total_sleep_minutes': 480, # 8 hours default
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

async def log_meal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles logging a meal via /meal command."""
    user_id = update.effective_user.id
    if not db.user_exists(user_id):
        await update.message.reply_text("Please register first using /start.")
        return

    ensure_daily_log_initialized(user_id, context)
    
    # Check if they passed arguments with the command
    args = context.args
    description = " ".join(args) if args else ""
    
    # Check if a photo is attached
    photo_path = None
    if update.message.photo:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        os.makedirs(os.path.join(UPLOAD_DIR, "food"), exist_ok=True)
        timestamp = int(datetime.now().timestamp())
        filename = f"{user_id}_{timestamp}_food.jpg"
        photo_path = os.path.join(UPLOAD_DIR, "food", filename)
        await file.download_to_drive(photo_path)
    
    # Store temporary state to gather meal type
    context.user_data['temp_meal'] = {
        'description': description,
        'food_image_path': photo_path
    }
    
    # Show inline keyboard to select meal type
    keyboard = [
        [
            InlineKeyboardButton("Breakfast 🍳", callback_data="meal_Breakfast"),
            InlineKeyboardButton("Lunch 🍱", callback_data="meal_Lunch"),
        ],
        [
            InlineKeyboardButton("Dinner 🍽️", callback_data="meal_Dinner"),
            InlineKeyboardButton("Snack 🍎", callback_data="meal_Snack"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "What type of meal is this?",
        reply_markup=reply_markup
    )

async def meal_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback query handler for meal type selection."""
    query = update.callback_query
    await query.answer()
    
    meal_type = query.data.split("_")[1]
    temp_meal = context.user_data.get('temp_meal')
    
    if not temp_meal:
        await query.edit_message_text("Session expired. Please try logging the meal again using /meal.")
        return

    # Initialize log session if needed
    ensure_daily_log_initialized(update.effective_user.id, context)
    
    # Add food entry
    food_entry = {
        'meal_type': meal_type,
        'food_image_path': temp_meal['food_image_path'],
        'description': temp_meal['description'] or "Logged via Telegram"
    }
    context.user_data['daily_log']['food_entries'].append(food_entry)
    context.user_data.pop('temp_meal', None)
    
    msg = f"Logged {meal_type} successfully! 🍲\n"
    if food_entry['description']:
        msg += f"Details: {food_entry['description']}\n"
    if food_entry['food_image_path']:
        msg += "Image uploaded."
        
    msg += "\n\nAdd more meals with `/meal [description]` or generate your report with /submit."
    await query.edit_message_text(msg)

async def log_exercise_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles logging an exercise via /exercise command."""
    user_id = update.effective_user.id
    if not db.user_exists(user_id):
        await update.message.reply_text("Please register first using /start.")
        return

    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            "Please specify exercise details.\n"
            "Usage: `/exercise [type] [duration_mins] [optional_details]`\n"
            "Example: `/exercise Gym 45 Weight lifting - chest and triceps`"
        )
        return

    ex_type = args[0]
    try:
        duration = int(args[1])
        details = " ".join(args[2:]) if len(args) > 2 else "Logged via Telegram"
    except ValueError:
        await update.message.reply_text("Please enter a valid number for duration in minutes.")
        return

    ensure_daily_log_initialized(user_id, context)
    
    # Add exercise entry
    exercise_entry = {
        'exercise_type': ex_type,
        'details': details,
        'duration_minutes': duration
    }
    context.user_data['daily_log']['exercise_entries'].append(exercise_entry)
    
    await update.message.reply_text(
        f"Logged exercise successfully! 🏋️\n"
        f"- Type: {ex_type}\n"
        f"- Duration: {duration} mins\n"
        f"- Details: {details}\n\n"
        f"You can add more or submit the daily log with /submit."
    )
