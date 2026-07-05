# Aarogyam AI 🌱 — AI-Powered Telegram Health & Wellness Companion

Aarogyam AI is a state-of-the-art, AI-powered personal health companion built directly inside Telegram. It uses a multi-model multimodal AI pipeline powered by Google Gemini 2.0 Flash and a semantic RAG recommendation engine to help users track metrics, analyze food photos for nutrition, compare physical changes day-over-day, and generate comprehensive PDF wellness reports.

---

## 🚀 Key Features

*   **Zero-Setup User Onboarding**: Dynamic chat conversation collects user demographics, fitness goals, and medical history, saving directly to a local SQLite/PostgreSQL database linked to the user's unique Telegram ID.
*   **Multimodal Food Log Analysis**: Upload a photo of any meal (or type a description) → Aarogyam AI identifies dishes, estimates portion sizes, calculates calories and macronutrients, and updates daily logs.
*   **Tap-to-Log Metric Tracking**: Inline keyboards let users quickly log mood, stress, steps, water intake, sleep, and weight.
*   **Visual Comparative Analysis**: Compare selfie check-ins and posture photos day-over-day to track skin clarity, fatigue, and posture improvements using Gemini Vision.
*   **Context-Aware Health Chat (`/chat`)**: A unified health assistant that answers wellness questions, summarizes medicine prescriptions, and diagnoses skin/wound issues with medical disclaimers.
*   **Regional RAG Recommendations**: Retrieval-Augmented Generation parses a dataset of Indian regional meals to suggest state-specific, diet-compliant foods tailored to the user's identified nutritional deficiencies.
*   **Tangible PDF Reports**: At the end of the day, Aarogyam AI compiles all daily metrics, food analysis tables, images, and recommendations into a professionally formatted PDF and delivers it directly in chat.

---

## 🛠️ System Architecture

```
                       📱 Telegram Chat Client
                                  │
                                  ▼
                     🤖 Telegram Bot (polling)
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
  🧠 Service Layer       📂 Database Layer         📊 PDF Generator
   - Gemini 2.0 Flash     - SQLite / Postgres       - fpdf2 Report Engine
   - Regional RAG (CSV)   - User Profiles & Logs
```

---

## 🚦 Getting Started

### 1. Prerequisites
*   Python 3.10+
*   Google Gemini API Key (get one from [Google AI Studio](https://aistudio.google.com/))
*   Telegram Bot Token (get one by messaging [@BotFather](https://t.me/BotFather) on Telegram)

### 2. Installation
Clone this repository and install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Configuration
Create a `.env` file in the root directory and add your keys:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
GOOGLE_API_KEY=your_google_api_key_here
DATABASE_PATH=aarogyam.db
```

### 4. Run the Bot
Start the polling server:
```bash
python bot/main.py
```

Now, open Telegram, search for your bot, and send `/start` to begin onboarding!

---

## 💬 Bot Commands Reference

*   `/start` - Register and build your health profile.
*   `/log` - Interactively track today's metrics (sleep, steps, mood, stress, water, weight, photos).
*   `/meal [description]` - Upload a photo of food or type what you ate to log a meal.
*   `/exercise [type] [duration_mins] [details]` - Log a workout session.
*   `/submit` - Submit today's log, run AI diagnostics, and get your PDF report.
*   `/report` - Retrieve your latest generated PDF wellness report.
*   `/workout` - Generate today's personalized workout checklist with toggleable completion buttons.
*   `/alternative [item]` - Search for healthy, eco-friendly alternatives (optionally attach a photo).
*   `/chat [message]` - Ask health questions, send prescription photos, or analyze skin/wounds.
*   `/profile` - View your active profile and edit goals.
*   `/help` - Show command reference.
