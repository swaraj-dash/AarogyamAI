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

    # Initialize chat history if not present
    if 'chat_history' not in context.user_data:
        context.user_data['chat_history'] = []

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
        
        system_instruction = (
            f"You are AarogyamAI health assistant. You act as a supportive mental coach (Sukoon Saathi), "
            f"nutritionist (Aahar Visheshagya), and health analyst. "
            f"The user is {user['name']}, goal is {user['health_goal']}, diet preference is {user['food_preference']}. "
            f"You must include a medical disclaimer advising consulting a real doctor for serious symptoms."
        )
        
        # If photo is present, handle as one-off multimodal analysis
        if photo_path:
            from PIL import Image
            img = Image.open(photo_path)
            prompt_parts = [system_instruction, img]
            
            # Determine photo context if text is empty
            if not message_text:
                message_text = (
                    "Analyze this health-related image. If it is a prescription, extract medicine names, dosages, and instructions. "
                    "If it is a skin condition or wound, describe it neutrally, provide general first aid, and include a medical disclaimer."
                )
            prompt_parts.append(f"\nUser query: {message_text}")
            
            response = model.generate_content(prompt_parts)
            await update.message.reply_text(response.text, parse_mode="Markdown")
        else:
            # Persistent text chat using Gemini start_chat
            # Format history for start_chat
            gemini_history = []
            for msg in context.user_data['chat_history']:
                gemini_history.append(
                    genai.types.Content(
                        role=msg['role'],
                        parts=[genai.types.Part.from_text(text=msg['parts'][0])]
                    )
                )
                
            chat = model.start_chat(history=gemini_history)
            
            # Prepend system instruction to prompt if it's the first message
            if not context.user_data['chat_history']:
                full_message = f"{system_instruction}\n\nUser: {message_text}"
            else:
                full_message = message_text
                
            response = chat.send_message(full_message)
            
            # Save history to session state
            context.user_data['chat_history'].append({"role": "user", "parts": [message_text]})
            context.user_data['chat_history'].append({"role": "model", "parts": [response.text]})
            
            # Keep history limited to the last 10 exchanges (20 messages)
            if len(context.user_data['chat_history']) > 20:
                context.user_data['chat_history'] = context.user_data['chat_history'][-20:]
                
            await update.message.reply_text(response.text, parse_mode="Markdown")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Chat failed to process: {e}")
        print(f"Error in chat_cmd: {e}")
