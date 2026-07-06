from telegram import Update
from telegram.ext import ContextTypes
import database as db
from services import analytics_service

async def weekly_report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a 7-day wellness progress review to the user."""
    user_id = update.effective_user.id
    if not db.user_exists(user_id):
        await update.message.reply_text("Please register first using /start.")
        return

    await update.message.reply_text("📊 Compiling your 7-Day Weekly Progress Review...")
    report_text = analytics_service.analyze_user_progress(user_id, days=7)
    await update.message.reply_text(report_text, parse_mode="Markdown")

async def monthly_report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a 30-day wellness progress review to the user."""
    user_id = update.effective_user.id
    if not db.user_exists(user_id):
        await update.message.reply_text("Please register first using /start.")
        return

    await update.message.reply_text("📊 Compiling your 30-Day Monthly Progress Review...")
    report_text = analytics_service.analyze_user_progress(user_id, days=30)
    await update.message.reply_text(report_text, parse_mode="Markdown")

async def yearly_report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a 365-day wellness progress review to the user."""
    user_id = update.effective_user.id
    if not db.user_exists(user_id):
        await update.message.reply_text("Please register first using /start.")
        return

    await update.message.reply_text("📊 Compiling your 365-Day Annual Progress Review...")
    report_text = analytics_service.analyze_user_progress(user_id, days=365)
    await update.message.reply_text(report_text, parse_mode="Markdown")
