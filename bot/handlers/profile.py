import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db

async def view_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the user's profile details."""
    user_id = update.effective_user.id
    if not db.user_exists(user_id):
        await update.message.reply_text("Please register first using /start.")
        return

    user = dict(db.get_user(user_id))
    
    preferred_ex = json.loads(user.get('preferred_exercise', '[]'))
    preferred_ex_str = ", ".join(preferred_ex) if preferred_ex else "None set"
    
    profile_text = (
        f"⚙️ **Your AarogyamAI Profile** ⚙️\n\n"
        f"👤 **Name**: {user['name']}\n"
        f"📅 **DOB**: {user['dob']}\n"
        f"🚻 **Gender**: {user['gender']}\n"
        f"📏 **Height**: {user['height_cm']:.1f} cm\n"
        f"📍 **Location**: {user['city']}, {user['location_state']}\n"
        f"🥦 **Food Preference**: {user['food_preference']}\n"
        f"🎯 **Primary Goal**: {user['health_goal']}\n"
        f"🏋️ **Preferred Exercises**: {preferred_ex_str}\n\n"
        f"Medical details: {user.get('medical_conditions', 'None')}\n"
        f"Allergies: {user.get('allergies', 'None')}"
    )

    # Inline options for editing
    keyboard = [
        [
            InlineKeyboardButton("Change Goal 🎯", callback_data="edit_goal"),
            InlineKeyboardButton("Change Preference 🥦", callback_data="edit_food"),
        ],
        [
            InlineKeyboardButton("Change Location 📍", callback_data="edit_location")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        profile_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def profile_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles inline edit button actions from the profile menu."""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    user_id = update.effective_user.id
    
    if action == "edit_goal":
        keyboard = [
            [
                InlineKeyboardButton("Weight Loss 📉", callback_data="setgoal_Weight Loss"),
                InlineKeyboardButton("Weight Gain 📈", callback_data="setgoal_Weight Gain")
            ],
            [
                InlineKeyboardButton("Maintain Weight ⚖️", callback_data="setgoal_Maintain Weight"),
                InlineKeyboardButton("Improve Fitness 💪", callback_data="setgoal_Improve Fitness")
            ],
            [
                InlineKeyboardButton("Manage Stress 🧘", callback_data="setgoal_Manage Stress")
            ]
        ]
        await query.edit_message_text(
            "Select your new Primary Health Goal:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    elif action == "edit_food":
        keyboard = [
            [InlineKeyboardButton("Vegetarian 🥦", callback_data="setfood_Vegetarian")],
            [InlineKeyboardButton("Vegetarian + Non-Veg 🍗", callback_data="setfood_Vegetarian + Non-Veg")]
        ]
        await query.edit_message_text(
            "Select your Food Preference:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    elif action == "edit_location":
        await query.edit_message_text(
            "To update location, please send the new state and city using the `/location [State] [City]` command.\n"
            "Example: `/location Maharashtra Mumbai`"
        )

async def set_goal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the updated health goal."""
    query = update.callback_query
    await query.answer()
    
    new_goal = query.data.split("_")[1]
    user_id = update.effective_user.id
    
    user = dict(db.get_user(user_id))
    user['health_goal'] = new_goal
    user['preferred_exercise'] = json.loads(user.get('preferred_exercise', '[]'))
    
    db.update_user_profile(user_id, user)
    await query.edit_message_text(f"🎯 Primary goal updated to: **{new_goal}**!\nCheck /profile to see changes.")

async def set_food_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the updated food preference."""
    query = update.callback_query
    await query.answer()
    
    new_pref = query.data.split("_")[1]
    user_id = update.effective_user.id
    
    user = dict(db.get_user(user_id))
    user['food_preference'] = new_pref
    user['preferred_exercise'] = json.loads(user.get('preferred_exercise', '[]'))
    
    db.update_user_profile(user_id, user)
    await query.edit_message_text(f"🥦 Food preference updated to: **{new_pref}**!\nCheck /profile to see changes.")

async def update_location_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to update location: /location [State] [City]."""
    user_id = update.effective_user.id
    if not db.user_exists(user_id):
        await update.message.reply_text("Please register first using /start.")
        return

    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            "Please specify both State and City.\n"
            "Usage: `/location [State] [City]`\n"
            "Example: `/location Karnataka Bengaluru`"
        )
        return

    state = args[0]
    city = " ".join(args[1:])
    
    db.update_user_location(user_id, city, state)
    await update.message.reply_text(f"📍 Location updated to **{city}, {state}**!")
