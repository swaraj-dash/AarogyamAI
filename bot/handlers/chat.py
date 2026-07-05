import os
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
import google.generativeai as genai
import database as db
from services import ai_engine

UPLOAD_DIR = "uploads"

async def chat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unified conversational assistant for health, mental wellness, and image diagnostics."""
    user_id = update.effective_user.id
    if not db.user_exists(user_id):
        await update.message.reply_text("Please register first using /start.")
        return

    user = dict(db.get_user(user_id))
    
    # Check arguments or photo
    args = context.args
    message_text = " ".join(args) if args else ""
    
    photo_path = None
    if update.message.photo:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        os.makedirs(os.path.join(UPLOAD_DIR, "chat"), exist_ok=True)
        timestamp = int(datetime.now().timestamp())
        filename = f"{user_id}_{timestamp}_chat.jpg"
        photo_path = os.path.join(UPLOAD_DIR, "chat", filename)
        await file.download_to_drive(photo_path)

    # If no inputs at all, show help
    if not message_text and not photo_path:
        await update.message.reply_text(
            "💬 **AarogyamAI Health Companion** 💬\n\n"
            "Ask me anything about fitness, recipes, stress, or mental health.\n"
            "You can also attach pictures for analysis:\n"
            "💊 **Prescription check**: Send a photo of a prescription.\n"
            "🩺 **Skin check**: Send a photo of a skin condition or wound.\n\n"
            "Usage: `/chat [your question]`"
        )
        return

    await update.message.reply_text("💬 Thinking...")

    try:
        model = ai_engine.get_model()
        
        # Build prompt history/context
        system_instruction = (
            f"You are AarogyamAI health assistant. You act as a supportive mental coach (Sukoon Saathi), "
            f"nutritionist (Aahar Visheshagya), and health analyst. "
            f"The user is {user['name']}, goal is {user['health_goal']}, diet preference is {user['food_preference']}. "
            f"You must include a medical disclaimer advising consulting a real doctor for serious symptoms."
        )
        
        prompt_parts = [system_instruction]
        
        # If photo is present
        if photo_path:
            from PIL import Image
            img = Image.open(photo_path)
            prompt_parts.append(img)
            
            # Determine photo context if text is empty
            if not message_text:
                message_text = (
                    "Analyze this health-related image. If it is a prescription, extract medicine names, dosages, and instructions. "
                    "If it is a skin condition or wound, describe it neutrally, provide general first aid, and include a medical disclaimer."
                )
        
        prompt_parts.append(f"\nUser query: {message_text}")
        
        response = model.generate_content(prompt_parts)
        await update.message.reply_text(response.text, parse_mode="Markdown")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Chat failed to process: {e}")
        print(f"Error in chat_cmd: {e}")
