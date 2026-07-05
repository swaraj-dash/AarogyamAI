import os
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
import database as db
from services import ai_engine, rag_engine, report_service

async def submit_daily_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Submits the daily log, triggers AI analysis, generates PDF, and sends it to the user."""
    user_id = update.effective_user.id
    if not db.user_exists(user_id):
        await update.message.reply_text("Please register first using /start.")
        return

    daily_log = context.user_data.get('daily_log')
    if not daily_log or (not daily_log.get('food_entries') and not daily_log.get('exercise_entries')):
        # Check if they have metrics logged but no food/exercise
        if not daily_log:
            await update.message.reply_text(
                "You haven't logged anything today!\n"
                "Please run /log to record metrics or /meal to add a meal first."
            )
            return

    await update.message.reply_text(
        "🔄 Submitting your daily log and triggering AI analysis...\n"
        "This may take up to a minute as we analyze food images and compare selfies. Please wait."
    )

    try:
        user_profile = dict(db.get_user(user_id))
        
        # 1. Save log to database
        # Convert daily_log to match add_daily_log expected structure
        log_id = db.add_daily_log(daily_log)
        full_log_data = db.get_full_daily_log(log_id)
        
        # 2. Get previous day images
        prev_day_images = db.get_previous_day_image_paths(user_id, daily_log['log_date'])
        
        # 3. Generate analysis
        full_analysis = ai_engine.generate_comprehensive_daily_analysis(
            user_profile, full_log_data, prev_day_images
        )
        
        # 4. Get recommendations
        recommendations = "Could not generate recommendations."
        if "error" not in full_analysis:
            lacking_nutrient = full_analysis.get("nutrition_analysis", {}).get("final_summary", {}).get("lacking_nutrient", "")
            recommendations = rag_engine.get_rag_recommendations(user_profile, lacking_nutrient)
            
        # 5. Generate PDF report
        pdf_path = report_service.generate_daily_report(
            user_profile, full_log_data, full_analysis, recommendations
        )
        
        if pdf_path and os.path.exists(pdf_path):
            # Send PDF to user
            with open(pdf_path, 'rb') as pdf_file:
                await update.message.reply_document(
                    document=pdf_file,
                    filename=os.path.basename(pdf_path),
                    caption=f"🎉 Here is your Daily Wellness Report for {daily_log['log_date']}!"
                )
            # Clear log session
            context.user_data.pop('daily_log', None)
        else:
            await update.message.reply_text(
                "❌ Failed to generate the PDF report, but your log data has been saved to the database."
            )
            
    except Exception as e:
        await update.message.reply_text(f"❌ An error occurred during submission: {e}")
        print(f"Error in submit_daily_log: {e}")

async def get_latest_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the user's latest generated PDF report."""
    user_id = update.effective_user.id
    if not db.user_exists(user_id):
        await update.message.reply_text("Please register first using /start.")
        return

    # Check for active logs that need to be submitted first
    if 'daily_log' in context.user_data and context.user_data['daily_log']:
        await update.message.reply_text(
            "You have unsubmitted logs! Running /submit to finalize and generate your report..."
        )
        await submit_daily_log(update, context)
        return

    # Look for files in generated_reports
    report_dir = "generated_reports"
    if not os.path.exists(report_dir):
        await update.message.reply_text("You haven't generated any reports yet. Use /log to start.")
        return

    reports = [f for f in os.listdir(report_dir) if f.startswith(f"report_{user_id}_") and f.endswith(".pdf")]
    if not reports:
        await update.message.reply_text(
            "No wellness reports found. Submit your daily log using /log and /submit to generate one!"
        )
        return

    # Get the latest report by name (contains date sorting)
    latest_report = sorted(reports, reverse=True)[0]
    file_path = os.path.join(report_dir, latest_report)
    
    with open(file_path, 'rb') as f:
        await update.message.reply_document(
            document=f,
            filename=latest_report,
            caption="Here is your latest generated Daily Wellness Report! 📄"
        )
