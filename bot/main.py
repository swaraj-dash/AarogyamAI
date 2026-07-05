import os
import sys
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    MessageHandler,
)

# Fix relative import paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import database as db
from bot.handlers import start, log_metrics, log_food, report, profile, tools, chat

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the help menu with all commands."""
    help_text = (
        "🌱 **AarogyamAI Bot Commands** 🌱\n\n"
        "🟢 **Onboarding & Setup**:\n"
        "/start - Register and create your health profile\n"
        "/profile - View and edit your health profile\n"
        "/location [State] [City] - Quick location update\n\n"
        "📝 **Daily Tracking**:\n"
        "/log - Record daily metrics (sleep, steps, mood, etc.)\n"
        "/meal [description] - Log a meal (attach photo for nutrition analysis!)\n"
        "/exercise [type] [duration_mins] [details] - Log physical activity\n"
        "/submit - Complete today's log & generate report\n\n"
        "📊 **Tools & Reports**:\n"
        "/report - Get your latest daily PDF wellness report\n"
        "/workout - Get a personalized daily fitness routine\n"
        "/alternative [item] - Find eco-friendly alternatives (optional photo)\n\n"
        "💬 **Interactive Coach**:\n"
        "/chat [question] - Talk about recipes, mental wellness, or upload diagnosis images"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dispatches callback query requests to their respective handlers."""
    query = update.callback_query
    data = query.data
    
    if data.startswith("meal_"):
        await log_food.meal_type_callback(update, context)
    elif data.startswith("toggleworkout_") or data == "save_workouts":
        await tools.workout_callback(update, context)
    elif data.startswith("edit_"):
        await profile.profile_edit_callback(update, context)
    elif data.startswith("setgoal_"):
        await profile.set_goal_callback(update, context)
    elif data.startswith("setfood_"):
        await profile.set_food_callback(update, context)

def main():
    """Initializes and runs the Telegram bot application."""
    print("Initializing AarogyamAI Database...")
    db.create_tables()
    
    token = config.TELEGRAM_BOT_TOKEN
    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN is not set in environment or .env. Exiting.")
        sys.exit(1)
        
    print("Building Telegram Bot Application...")
    app = ApplicationBuilder().token(token).build()
    
    # Register command and conversation handlers
    app.add_handler(start.get_start_handler())
    app.add_handler(log_metrics.get_log_handler())
    
    app.add_handler(CommandHandler("meal", log_food.log_meal_cmd))
    # Allow logging meal directly when photo is sent with caption /meal
    app.add_handler(MessageHandler(filters.Caption(["/meal"]), log_food.log_meal_cmd))
    
    app.add_handler(CommandHandler("exercise", log_food.log_exercise_cmd))
    app.add_handler(CommandHandler("submit", report.submit_daily_log))
    app.add_handler(CommandHandler("report", report.get_latest_report))
    app.add_handler(CommandHandler("profile", profile.view_profile))
    app.add_handler(CommandHandler("location", profile.update_location_cmd))
    app.add_handler(CommandHandler("workout", tools.workout_cmd))
    
    app.add_handler(CommandHandler("alternative", tools.alternative_cmd))
    # Allow finding alternative when photo is sent with caption /alternative
    app.add_handler(MessageHandler(filters.Caption(["/alternative"]), tools.alternative_cmd))
    
    app.add_handler(CommandHandler("chat", chat.chat_cmd))
    # Allow sending image with caption /chat
    app.add_handler(MessageHandler(filters.Caption(["/chat"]), chat.chat_cmd))
    
    app.add_handler(CommandHandler("help", help_cmd))
    
    # Callback query router
    app.add_handler(CallbackQueryHandler(callback_router))
    
    # Configure daily reminders at 8:00 PM local time
    import datetime
    if app.job_queue:
        app.job_queue.run_daily(
            send_daily_reminders,
            time=datetime.time(hour=20, minute=0, second=0)
        )
        print("Daily reminder job successfully scheduled at 8:00 PM local time.")
    else:
        print("WARNING: JobQueue is not available. Scheduled reminders will not run.")
    
    print("AarogyamAI Telegram Bot is starting. Listening for messages...")
    app.run_polling()

async def send_daily_reminders(context: ContextTypes.DEFAULT_TYPE):
    """Sends daily reminders to log metrics to all registered users."""
    print("Executing scheduled daily reminder job...")
    try:
        conn = db.get_db_connection()
        users = conn.execute("SELECT user_id, name FROM users").fetchall()
        conn.close()
        
        for u in users:
            try:
                user_id = u['user_id']
                first_name = u['name'].split()[0]
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"Good evening, {first_name}! 🌅\n\n"
                        "Don't forget to track your health today. Let's record your daily progress:\n"
                        "📝 Run /log to log sleep, steps, mood, and check-in photos.\n"
                        "🍲 Send /meal to log your breakfast, lunch, or dinner.\n"
                        "📄 Submit with /submit to receive your daily PDF analysis!"
                    )
                )
                print(f"Sent reminder successfully to user ID {user_id}")
            except Exception as ex:
                print(f"Failed to send reminder to user ID {user_id}: {ex}")
    except Exception as e:
        print(f"Failed to query database for reminders: {e}")

if __name__ == "__main__":
    main()
