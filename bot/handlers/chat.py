"""
Free-text chat — every non-command message from a registered user is routed
through agents.orchestrator.handle_message, which classifies intent,
retrieves episodic + semantic memory, dispatches to the right specialist
node, and persists the exchange to working memory (chat_messages).

This is the direct replacement for v1's chat.py, which held history only
in `context.user_data['chat_history']` — process memory, gone on restart,
invisible to the Streamlit side. Here the bot is just a thin transport:
all state lives in the DB via the memory system, so the same conversation
context is available whether the next message comes through Telegram or
the Streamlit chat page.
"""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

import database as db
from agents.orchestrator import handle_message


async def chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not db.user_exists(user_id):
        await update.message.reply_text("Please run /start first to set up your profile.")
        return

    await update.message.chat.send_action("typing")
    result = handle_message(user_id, update.message.text)
    await update.message.reply_text(result.get("response", "Sorry, I didn't catch that."))


def build_message_handler() -> MessageHandler:
    return MessageHandler(filters.TEXT & ~filters.COMMAND, chat_message)
