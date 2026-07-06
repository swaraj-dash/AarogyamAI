import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db
from services import ai_engine
from bot.handlers.log_food import ensure_daily_log_initialized
import config

UPLOAD_DIR = config.UPLOAD_DIR

# --- WORKOUT HANDLER (URJA PATH) ---

async def workout_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates today's personalized workout and shows it with interactive toggle buttons."""
    user_id = update.effective_user.id
    if not db.user_exists(user_id):
        await update.message.reply_text("Please register first using /start.")
        return

    user = dict(db.get_user(user_id))
    
    await update.message.reply_text("🏋️ Generating your personalized fitness plan for today...")
    
    try:
        plan = ai_engine.get_fitness_plan(user)
        # Store plan in user_data to reference indexes
        context.user_data['temp_workout_plan'] = plan
        context.user_data['completed_workout_indexes'] = set()
        
        await send_workout_menu(update.message.reply_text, plan, set())
    except Exception as e:
        await update.message.reply_text(f"Failed to generate workout plan: {e}")

async def send_workout_menu(reply_func, plan, completed_indexes):
    """Helper to format and send the workout list with toggle buttons."""
    text = "🏋️ **Today's Custom Fitness Plan** 🏋️\n\nCheck off the activities you complete. They will be added to your daily log!\n\n"
    
    keyboard = []
    for idx, item in enumerate(plan):
        activity = item['activity']
        duration = item['duration_or_sets']
        
        is_done = idx in completed_indexes
        status_emoji = "✅" if is_done else "⬜"
        
        text += f"{idx+1}. {status_emoji} **{activity}** ({duration})\n"
        
        # Add button to toggle this specific exercise
        keyboard.append([
            InlineKeyboardButton(
                f"{status_emoji} {activity[:25]}...", 
                callback_data=f"toggleworkout_{idx}"
            )
        ])
        
    # Add final action buttons
    keyboard.append([
        InlineKeyboardButton("Save Completed Workouts 💾", callback_data="save_workouts")
    ])
    
    await reply_func(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def workout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback for toggling workout exercises."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    plan = context.user_data.get('temp_workout_plan')
    completed_indexes = context.user_data.get('completed_workout_indexes', set())
    
    if not plan:
        await query.edit_message_text("Session expired. Please run /workout again.")
        return
        
    if data.startswith("toggleworkout_"):
        idx = int(data.split("_")[1])
        if idx in completed_indexes:
            completed_indexes.remove(idx)
        else:
            completed_indexes.add(idx)
            
        context.user_data['completed_workout_indexes'] = completed_indexes
        
        # Edit the message with updated checks
        text = "🏋️ **Today's Custom Fitness Plan** 🏋️\n\nCheck off the activities you complete. They will be added to your daily log!\n\n"
        keyboard = []
        for i, item in enumerate(plan):
            activity = item['activity']
            duration = item['duration_or_sets']
            is_done = i in completed_indexes
            status_emoji = "✅" if is_done else "⬜"
            
            text += f"{i+1}. {status_emoji} **{activity}** ({duration})\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"{status_emoji} {activity[:25]}...", 
                    callback_data=f"toggleworkout_{i}"
                )
            ])
            
        keyboard.append([
            InlineKeyboardButton("Save Completed Workouts 💾", callback_data="save_workouts")
        ])
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        
    elif data == "save_workouts":
        if not completed_indexes:
            await query.edit_message_text("No exercises selected to save. Run /workout again if you wish to check them off.")
            return
            
        ensure_daily_log_initialized(user_id, context)
        
        # Add to daily log
        completed_activities = []
        for idx in completed_indexes:
            item = plan[idx]
            exercise_entry = {
                'exercise_type': 'AI Workout Recommendation',
                'details': item['activity'],
                'duration_minutes': 20 # standard estimate
            }
            context.user_data['daily_log']['exercise_entries'].append(exercise_entry)
            completed_activities.append(item['activity'])
            
        # Clean up temp state
        context.user_data.pop('temp_workout_plan', None)
        context.user_data.pop('completed_workout_indexes', None)
        
        saved_list = "\n".join([f"• {act}" for act in completed_activities])
        await query.edit_message_text(
            f"✅ Saved the following completed exercises to today's log:\n\n{saved_list}\n\n"
            f"They will be included in your daily PDF report. Use /submit when done for the day!"
        )


# --- ECO ALTERNATIVE HANDLER (SHUDDH VIKALP) ---

async def alternative_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finds eco-friendly and healthy alternatives for items."""
    user_id = update.effective_user.id
    if not db.user_exists(user_id):
        await update.message.reply_text("Please register first using /start.")
        return

    # Check for text description in the arguments
    args = context.args
    item_description = " ".join(args) if args else ""
    
    # Check if a photo is attached
    photo_path = None
    if update.message.photo:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        os.makedirs(os.path.join(UPLOAD_DIR, "tools"), exist_ok=True)
        timestamp = int(datetime.now().timestamp())
        filename = f"{user_id}_{timestamp}_alternative.jpg"
        photo_path = os.path.join(UPLOAD_DIR, "tools", filename)
        await file.download_to_drive(photo_path)

    if not item_description and not photo_path:
        await update.message.reply_text(
            "Please describe an item or attach an image.\n"
            "Usage: `/alternative [item description]` (with optional photo)\n"
            "Example: `/alternative plastic lunch box`"
        )
        return

    await update.message.reply_text("🔍 Searching for sustainable, healthy alternatives. Please wait...")

    try:
        agent = ai_engine.get_environment_wellness_agent()
        query = ""
        
        if item_description:
            query = f"Find healthy and eco-friendly alternatives for a {item_description}. Provide 2-3 options with brief descriptions and why they are better. If possible, provide links to buy them in India."
        elif photo_path:
            # Use Gemini Vision to describe the image, then search alternatives
            from PIL import Image
            img = Image.open(photo_path)
            vision_model = ai_engine.get_vision_model()
            image_desc_response = vision_model.generate_content(["Describe the main object in this image in a few words.", img])
            detected_item = image_desc_response.text.strip()
            
            await update.message.reply_text(f"Detected item in image: **{detected_item}**")
            query = f"Find healthy and eco-friendly alternatives for a {detected_item}. Provide 2-3 options with brief descriptions and why they are better. If possible, provide links to buy them in India."

        response = agent.run(query)
        await update.message.reply_text(response, parse_mode="Markdown")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to find alternatives: {e}")
