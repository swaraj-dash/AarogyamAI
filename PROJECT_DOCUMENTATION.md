# AarogyamAI — Exhaustive Technical Blueprint & Repository Mirror

> **Purpose**: This document serves as a **complete code-level mirror** of the AarogyamAI repository. Any AI or human reading this file should have the equivalent understanding of sitting inside the repository with every file open. Every architectural decision, algorithm, state machine, prompt template, exact code implementation, database query, callback protocol, error handling pattern, and configuration detail is documented here — nothing is summarized or omitted.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Complete Directory Tree](#2-complete-directory-tree)
3. [Architecture Diagram](#3-architecture-diagram)
4. [Dual-Interface System](#4-dual-interface-system)
5. [Configuration System](#5-configuration-system-configpy)
6. [Database Layer](#6-database-layer-databasepy)
7. [AI Engine](#7-ai-engine-servicesai_enginepy)
8. [RAG Engine](#8-rag-engine-servicesrag_enginepy)
9. [Analytics Service](#9-analytics-service-servicesanalytics_servicepy)
10. [Report Service](#10-report-service-servicesreport_servicepy)
11. [PDF Generator](#11-pdf-generator-report_generatorpy)
12. [Telegram Bot Entry Point](#12-telegram-bot-entry-point-botmainpy)
13. [Bot Handlers — Complete Reference](#13-bot-handlers--complete-reference)
14. [Streamlit Web Dashboard](#14-streamlit-web-dashboard)
15. [Legacy Bridge Module](#15-legacy-bridge-module-ai_utilspy)
16. [End-to-End Data Flow Walkthrough](#16-end-to-end-data-flow-walkthrough)
17. [Error Handling Patterns](#17-error-handling-patterns)
18. [Dependencies & Setup](#18-dependencies--setup)
19. [Git Configuration](#19-git-configuration)
20. [Known Limitations & Future Improvements](#20-known-limitations--future-improvements)

---

## 1. Project Overview

AarogyamAI is an AI-powered personal health and wellness companion with two interfaces:
- A **Telegram Bot** for mobile-first daily tracking
- A **Streamlit Web Dashboard** for visual analytics

**Core AI Pipeline**: Google Gemini 2.0 Flash (multimodal — text, images, search grounding)  
**Database**: SQLite (single file `aarogyam.db`, shared by both interfaces)  
**PDF Engine**: fpdf2 with DejaVuSans Unicode fonts  
**RAG System**: Pandas-based CSV filtering of Indian regional dishes + Gemini synthesis  
**Language**: Python 3.10+

---

## 2. Complete Directory Tree

```text
aarogyamai/
├── .streamlit/
│   └── secrets.toml                          # Streamlit Cloud secrets (gitignored)
├── assets/
│   ├── DejaVuSans.ttf                       # Regular Unicode font for PDF body text
│   ├── DejaVuSans-Bold.ttf                  # Bold variant for PDF headers
│   └── DejaVuSans-Oblique.ttf               # Italic variant for PDF footers/disclaimers
├── bot/
│   ├── __init__.py                          # Empty package marker
│   ├── main.py                              # Bot entry point: polling, handler registration, cron, callback router
│   └── handlers/
│       ├── __init__.py                      # Empty package marker
│       ├── start.py                         # 9-state ConversationHandler for /start onboarding
│       ├── log_metrics.py                   # 10-state ConversationHandler for /log daily metrics
│       ├── log_food.py                      # Stateless /meal and /exercise handlers
│       ├── chat.py                          # Persistent-memory /chat with image analysis
│       ├── report.py                        # /submit pipeline and /report latest fetch
│       ├── profile.py                       # /profile viewer with inline edit callbacks
│       ├── tools.py                         # /workout interactive toggles and /alternative eco-search
│       └── analytics.py                     # /weekly, /monthly, /yearly trend commands
├── services/
│   ├── __init__.py                          # Empty package marker
│   ├── ai_engine.py                         # Gemini SDK wrapper (text, vision, search grounding, JSON parsing)
│   ├── analytics_service.py                 # Time-series aggregation + Gemini progress synthesis
│   ├── rag_engine.py                        # CSV-based regional meal RAG + Gemini recipe generation
│   └── report_service.py                    # Thin facade ensuring directory exists before PDF generation
├── pages/                                   # Streamlit subpages (multi-page app)
│   ├── 1_🧠_Sukoon_Saathi.py               # Mental wellness chatbot (Gemini 1.0 Pro)
│   ├── 2_🩺_Sehat_Darpan.py                # Medical image analysis + health chat (3 tabs)
│   ├── 3_🏋️‍♀️_Urja_Path.py                  # AI workout plan generator with checkboxes
│   ├── 4_🌿_Shuddh_Vikalp.py               # Eco-friendly product alternatives search
│   ├── 5_👩‍⚕️_Aahar_Visheshagya.py           # AI nutritionist chatbot
│   └── 6_⚙️_Profile.py                      # Profile editor + report archive download
├── rag_data/
│   └── india_state_meal_nutrient_recs.csv   # 28-state Indian regional dish nutrient database
├── faiss_index/                             # Legacy FAISS vector index (unused in current code)
├── generated_reports/                       # Auto-created directory for PDF outputs (gitignored)
├── uploads/                                 # Auto-created directory for user photos (gitignored)
│   ├── chat/                                # /chat image uploads
│   ├── food/                                # /meal food photo uploads
│   ├── profile/                             # Selfies and posture photos
│   └── tools/                               # /alternative image uploads
├── app.py                                   # Streamlit main dashboard (login, signup, daily log form)
├── config.py                                # Centralized configuration with env/secrets fallback
├── database.py                              # SQLite schema builder and all CRUD operations
├── report_generator.py                      # FPDF2 subclass with progress bars, tables, image embedding
├── ai_utils.py                              # Legacy bridge: delegates to services/ai_engine and services/rag_engine
├── requirements.txt                         # Python dependencies
├── .env.example                             # Template for environment variables
├── .gitignore                               # Excludes venv, __pycache__, secrets, uploads, reports, db
├── README.md                                # GitHub-facing project overview
└── PROJECT_DOCUMENTATION.md                 # This file
```

---

## 3. Architecture Diagram

```mermaid
graph TD
    TelegramUser([Telegram User]) <-->|Commands, Photos, Callbacks| BotMain["bot/main.py"]
    WebUser([Browser User]) <-->|Forms, Sliders, Charts| StreamlitApp["app.py + pages/"]

    subgraph BotHandlers ["bot/handlers/"]
        BotMain -->|/start| StartH["start.py"]
        BotMain -->|/log| LogMetricsH["log_metrics.py"]
        BotMain -->|/meal, /exercise| LogFoodH["log_food.py"]
        BotMain -->|/chat| ChatH["chat.py"]
        BotMain -->|/workout, /alternative| ToolsH["tools.py"]
        BotMain -->|/submit, /report| ReportH["report.py"]
        BotMain -->|/weekly, /monthly, /yearly| AnalyticsH["analytics.py"]
        BotMain -->|/profile, /location| ProfileH["profile.py"]
    end

    subgraph CoreServices ["services/ + root modules"]
        StartH & LogMetricsH & LogFoodH & StreamlitApp -->|SQL CRUD| DB["database.py"]
        ChatH & LogFoodH & ToolsH & ReportH -->|LLM calls| AIEngine["services/ai_engine.py"]
        ReportH -->|Orchestrate| ReportSvc["services/report_service.py"]
        ReportSvc -->|Regional dishes| RAG["services/rag_engine.py"]
        ReportSvc -->|Layout PDF| PDFGen["report_generator.py"]
        AnalyticsH -->|Aggregate + Evaluate| AnalyticsSvc["services/analytics_service.py"]
    end

    subgraph Storage ["Data Layer"]
        DB <-->|Read/Write| SQLite[("aarogyam.db")]
        RAG <-->|pandas filter| CSV[("india_state_meal_nutrient_recs.csv")]
        AIEngine & RAG & AnalyticsSvc <-->|HTTPS| Gemini["Google Gemini 2.0 Flash API"]
        PDFGen -->|Write file| PDFDir["generated_reports/"]
    end
```

---

## 4. Dual-Interface System

| Aspect | Telegram Bot | Streamlit Web Dashboard |
|---|---|---|
| **Entry Point** | `python bot/main.py` | `streamlit run app.py` |
| **Interaction** | Conversational commands, inline buttons, photo uploads | Form inputs, sliders, file uploaders, charts |
| **Auth Model** | Telegram `user_id` (integer, auto from Telegram) | Manual 5-digit ID login (generated by `generate_unique_user_id()`) |
| **Session State** | `context.user_data` (per-user, in-memory, python-telegram-bot managed) | `st.session_state` (per-browser-tab, Streamlit managed) |
| **Database** | Reads/writes `aarogyam.db` via `database.py` | Reads/writes the same `aarogyam.db` via `database.py` |
| **Image Handling** | Telegram API downloads to `uploads/` subdirectories | PIL resize to 512×512, JPEG quality 85, saved to `uploads/` |
| **Secrets** | `.env` file via `python-dotenv` | `.env` or `.streamlit/secrets.toml` via `st.secrets` |
| **Features** | All 16 commands including analytics, chat, workout toggles | Daily log form, 6 subpages (chat, diagnosis, workout, alternatives, nutrition, profile) |

---

## 5. Configuration System (`config.py`)

**Full Source Code:**
```python
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def get_secret(key, default=None):
    """Gets a configuration secret from environment variables or Streamlit secrets."""
    val = os.getenv(key)
    if val is not None:
        return val
    # Fallback to Streamlit secrets if running inside Streamlit
    if 'streamlit' in sys.modules:
        try:
            import streamlit as st
            if key in st.secrets:
                return st.secrets[key]
        except Exception:
            pass
    return default

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Project root, absolute
default_db_path = os.path.join(BASE_DIR, "aarogyam.db")

TELEGRAM_BOT_TOKEN = get_secret("TELEGRAM_BOT_TOKEN")
GOOGLE_API_KEY = get_secret("GOOGLE_API_KEY")
DATABASE_PATH = get_secret("DATABASE_PATH", default_db_path)
TAVILY_API_KEY = get_secret("TAVILY_API_KEY")
DB_TYPE = get_secret("DB_TYPE", "sqlite")

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
REPORT_DIR = os.path.join(BASE_DIR, "generated_reports")

# Startup warnings
if not GOOGLE_API_KEY:
    print("WARNING: GOOGLE_API_KEY is not set. Gemini functions will fail.")
if not TELEGRAM_BOT_TOKEN:
    print("WARNING: TELEGRAM_BOT_TOKEN is not set. Telegram Bot will not start.")
```

### Design Decisions
- **`BASE_DIR` anchoring**: All file paths (database, uploads, reports, fonts, CSV) resolve relative to this absolute path, preventing SQLite database splitting when running from different working directories.
- **Priority chain**: `os.getenv()` → `st.secrets` → `default`. This allows the same codebase to work in local dev (`.env`), Streamlit Cloud (secrets panel), and Docker.
- **Lazy Streamlit import**: Only imports `streamlit` if it's already in `sys.modules`, avoiding import errors when running the Telegram bot standalone.

### `.env.example` Contents
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
GOOGLE_API_KEY=your_google_api_key_here
DATABASE_PATH=aarogyam.db
TAVILY_API_KEY=your_tavily_api_key_here
DB_TYPE=sqlite
DATABASE_URL=sqlite:///aarogyam.db
```

---

## 6. Database Layer (`database.py`)

### Connection Setup
```python
def get_db_connection():
    conn = sqlite3.connect(config.DATABASE_PATH, timeout=20.0)  # 20s lock timeout
    conn.execute("PRAGMA foreign_keys = ON")  # Enforce FK constraints
    conn.row_factory = sqlite3.Row  # Dict-style row access
    return conn
```

### Complete Schema (DDL)
```sql
CREATE TABLE IF NOT EXISTS users (
    user_id            INTEGER PRIMARY KEY,      -- Telegram user_id OR generated 5-digit
    name               TEXT NOT NULL,
    dob                TEXT NOT NULL,             -- YYYY-MM-DD
    height_cm          REAL NOT NULL,
    gender             TEXT NOT NULL,             -- Male | Female | Other | Prefer not to say
    location_state     TEXT NOT NULL,             -- Indian state name for RAG matching
    city               TEXT NOT NULL,
    food_preference    TEXT NOT NULL,             -- Vegetarian | Vegetarian + Non-Veg
    health_goal        TEXT NOT NULL,             -- Weight Loss | Weight Gain | Maintain Weight | Improve Fitness | Manage Stress
    preferred_exercise TEXT,                      -- JSON array string: ["Yoga", "Gym"]
    medical_conditions TEXT,
    medications        TEXT,
    allergies          TEXT,
    surgical_history   TEXT,
    family_history     TEXT,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_logs (
    log_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL,
    log_date            TEXT NOT NULL,             -- YYYY-MM-DD
    total_sleep_minutes INTEGER,
    steps               INTEGER,
    mood                TEXT,                      -- Emoji + label: "😊 Happy"
    weight_kg           REAL,
    selfie_path         TEXT,                      -- Absolute path to JPEG
    posture_pic_path    TEXT,                      -- Absolute path to JPEG
    travel_info         TEXT,                      -- JSON: {"km":0,"mode":"None","location_changed":false,...}
    hydration_level     REAL,                      -- Liters
    stress_level        TEXT,                      -- Low | Mild | High
    menstrual_cycle_day INTEGER,                   -- Optional
    task_completion     TEXT,                      -- None | A Few | Majority | All
    focus_level         TEXT,                      -- Low | Medium | High
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS food_entries (
    food_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    log_id          INTEGER NOT NULL,
    meal_type       TEXT NOT NULL,                 -- Breakfast | Lunch | Dinner | Snack
    food_image_path TEXT,
    description     TEXT,
    FOREIGN KEY (log_id) REFERENCES daily_logs(log_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS exercise_entries (
    exercise_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    log_id           INTEGER NOT NULL,
    exercise_type    TEXT NOT NULL,                -- Gym | Yoga | Running | AI Workout Recommendation
    details          TEXT,
    duration_minutes INTEGER,
    FOREIGN KEY (log_id) REFERENCES daily_logs(log_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reports (
    report_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    report_type TEXT NOT NULL,
    start_date  TEXT NOT NULL,
    end_date    TEXT NOT NULL,
    file_path   TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

### All CRUD Functions (Complete Implementation)

**`generate_unique_user_id()`** — For Streamlit web signup only:
```python
def generate_unique_user_id():
    conn = get_db_connection()
    c = conn.cursor()
    while True:
        ts_part = str(int(time.time() * 1000))[-3:]  # Last 3 digits of ms timestamp
        rand_part = str(random.randint(10, 99))       # 2 random digits
        user_id = int(ts_part + rand_part)             # 5-digit unique ID
        c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if c.fetchone() is None:
            conn.close()
            return user_id
```

**`add_user(user_data, user_id=None)`**:
- If `user_id` is `None` (Streamlit signup), generates one via `generate_unique_user_id()`
- If `user_id` is provided (Telegram), uses the Telegram user ID directly
- `preferred_exercise` is serialized via `json.dumps(list)`

**`add_daily_log(log_data) -> log_id`** — Critical overwrite behavior:
```python
# 1. Check if log exists for same user+date
c.execute("SELECT log_id FROM daily_logs WHERE user_id = ? AND log_date = ?", ...)
existing = c.fetchone()
if existing:
    # CASCADE DELETE: removes child food_entries and exercise_entries automatically
    c.execute("DELETE FROM daily_logs WHERE log_id = ?", (existing['log_id'],))

# 2. INSERT new log
c.execute('INSERT INTO daily_logs (...) VALUES (...)', ...)
log_id = c.lastrowid

# 3. INSERT child entries
for food in log_data['food_entries']:
    c.execute('INSERT INTO food_entries (log_id, meal_type, food_image_path, description) VALUES (?, ?, ?, ?)', ...)
for exercise in log_data['exercise_entries']:
    c.execute('INSERT INTO exercise_entries (log_id, exercise_type, details, duration_minutes) VALUES (?, ?, ?, ?)', ...)
```

**`get_full_daily_log(log_id) -> dict`**:
Returns `{"log_details": dict(Row), "food_entries": [dict(Row)], "exercise_entries": [dict(Row)]}`

**`get_logs_in_range(user_id, start_date, end_date) -> list[dict]`**:
```python
logs = conn.execute(
    "SELECT * FROM daily_logs WHERE user_id = ? AND log_date BETWEEN ? AND ? ORDER BY log_date ASC",
    (user_id, start_date, end_date)
).fetchall()
# For each log, also fetches food_entries and exercise_entries
```

**`get_previous_day_image_paths(user_id, current_log_date) -> dict|None`**:
```python
previous_date = datetime.strptime(current_log_date, '%Y-%m-%d').date() - timedelta(days=1)
c.execute("SELECT selfie_path, posture_pic_path FROM daily_logs WHERE user_id = ? AND log_date = ?",
          (user_id, previous_date.strftime('%Y-%m-%d')))
```
Returns `{"selfie_path": "...", "posture_pic_path": "..."}` or `None`.

---

## 7. AI Engine (`services/ai_engine.py`)

### Model Configuration
```python
MODEL_NAME = "gemini-2.0-flash"
genai.configure(api_key=config.GOOGLE_API_KEY)

def get_model(name=MODEL_NAME):
    return genai.GenerativeModel(name)
```
All three accessors (`get_model`, `get_text_model`, `get_vision_model`) return the same unified model. Gemini 2.0 Flash handles text, vision, and search natively.

### `SearchAgentWrapper` Class — Google Search Grounding
```python
class SearchAgentWrapper:
    def run(self, query: str) -> str:
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            tools=[{"google_search": {}}]  # Enable Google Search grounding
        )
        try:
            response = model.generate_content(query)
            sources = []
            metadata = response.candidates[0].grounding_metadata if response.candidates else None
            if metadata and metadata.grounding_chunks:
                for chunk in metadata.grounding_chunks:
                    if chunk.web:
                        sources.append(f"- [{chunk.web.title}]({chunk.web.uri})")
            answer = response.text
            if sources:
                answer += "\n\n**Sources:**\n" + "\n".join(set(sources))
            return answer
        except Exception as e:
            # Fallback to standard generation without search
            fallback_model = get_model()
            response = fallback_model.generate_content(query)
            return response.text
```

### `get_fitness_plan(user_profile) -> list[dict]`
**Exact Prompt:**
```
You are an expert fitness coach. Generate a personalized daily workout plan for a user with the following profile:
- Primary Health Goal: {user_profile.get('health_goal')}
- Preferred Daily Exercises: {user_profile.get('preferred_exercise')}
- Existing Medical Conditions: {user_profile.get('medical_conditions', 'None')}
- Gender: {user_profile.get('gender')}

Provide the response as a valid JSON array of objects. Each object must have exactly two fields:
1. "activity": A string describing the exercise name and instruction.
2. "duration_or_sets": A string describing the duration or sets/reps.

Return ONLY the raw JSON array. Do not include markdown code block formatting.
```

**Response parsing**: Strips `\`\`\`json` fences if present, parses via `json.loads()`. On failure, returns a hardcoded 6-exercise fallback plan.

### `generate_comprehensive_daily_analysis(user_profile, log_data, prev_day_images) -> dict`
This is the **most complex function** in the system. It builds a multimodal prompt:

1. **Text parts**: User profile (health_goal, food_preference), daily metrics (sleep, steps, mood, stress, focus, task_completion)
2. **Image parts**: Opens up to 4 images via `PIL.Image.open()`:
   - Today's selfie (if `selfie_path` exists and file exists on disk)
   - Yesterday's selfie (for day-over-day comparison)
   - Today's posture photo
   - Yesterday's posture photo
3. **Food entries**: For each meal, adds description text + food image
4. **Dynamic comparison instructions**: Based on which images are available:
   - Both selfies → "Analyze the selfie comparison for facial features like skin clarity and tiredness"
   - Only today → "State that yesterday's selfie was not provided for a comparison"
   - Neither → "State that a selfie was not provided today for analysis"

**Required Response JSON Schema:**
```json
{
  "wellness_score": {
    "score": "A score from 1-100",
    "justification": "Brief explanation"
  },
  "physical_activity_analysis": "One-sentence encouraging comment",
  "mental_clarity_analysis": "Empathetic summary of mood, stress, focus, sleep",
  "daily_image_analysis": {
    "selfie_analysis": "One-sentence analysis or 'Not available.'",
    "posture_analysis": "One-sentence analysis or 'Not available.'"
  },
  "comparative_analysis": {
    "selfie_feedback": "Day-over-day comparison or explanation of unavailability",
    "posture_feedback": "Day-over-day comparison or explanation of unavailability"
  },
  "nutrition_analysis": {
    "meal_analyses": [
      {
        "meal_type": "Breakfast",
        "nutrition_table": [
          {
            "component": "Item Name",
            "calories": 150,
            "protein_g": 5,
            "carbs_g": 25,
            "fats_g": 5,
            "vitamins_minerals": "Iron, Vitamin C"
          }
        ]
      }
    ],
    "final_summary": {
      "summary": "Professional 2-sentence diet summary",
      "positives": ["max 3 positive points"],
      "improvements": ["max 3 improvement points"],
      "lacking_nutrient": "One of: Protein | Fiber | Iron | Calcium | Vitamins | Healthy Fats"
    }
  }
}
```

**Constraints in prompt**: "Be conservative and realistic with nutritional estimates based on standard Indian portions. All summaries must be concise (1-2 sentences). Positives/Improvements lists must have max 3 points."

---

## 8. RAG Engine (`services/rag_engine.py`)

### CSV Structure
The file `rag_data/india_state_meal_nutrient_recs.csv` has columns: `state`, `dish name`, `meal type`, `description`, `preference`, `primary nutrient`, `secondary nutrient`, `tertiary nutrient`, `quaternary nutrient`.

### Algorithm: `get_rag_recommendations(user_profile, lacking_nutrient)`

**Step 1 — General recommendations via Gemini:**
```python
general_prompt = (
    f"Provide a short, bulleted list of general food sources for a person lacking in {lacking_nutrient}. "
    f"The user's food preference is {user_profile['food_preference']}, so only suggest suitable items."
)
```

**Step 2 — CSV-based retrieval with pandas:**
```python
df = pd.read_csv(csv_path)
df.columns = df.columns.str.lower().str.strip()

# Determine preference filter
preference = 'Veg' if user_profile.get('food_preference') == 'Vegetarian' else 'Non-Veg'

# Strict filter: match state + preference + any nutrient column
results = df[
    (df['state'].str.lower() == state.lower()) &
    (df['preference'].str.contains(preference, case=False, na=False)) &
    (
        (df['primary nutrient'].str.lower() == lacking_nutrient.lower()) |
        (df['secondary nutrient'].str.lower() == lacking_nutrient.lower()) |
        (df['tertiary nutrient'].str.lower() == lacking_nutrient.lower()) |
        (df['quaternary nutrient'].str.lower() == lacking_nutrient.lower())
    )
]
retrieved_dishes = results[['dish name', 'meal type', 'description']].head(3)

# Fallback: if no matches in user's state, relax state constraint
if retrieved_dishes.empty:
    results_any_state = df[... same filters but without state ...]
    retrieved_dishes = results_any_state[['dish name', 'meal type', 'description']].head(3)
```

**Step 3 — Gemini synthesis:**
```python
prompt = f"""
You are a helpful nutrition assistant. A user from {state} is looking for dishes rich in {lacking_nutrient}.
Based on the following retrieved Indian dishes, please provide a friendly recommendation for 1-2 dishes.
For each dish, briefly explain why it's a good choice.

Retrieved dishes:
{retrieved_dishes.to_string(index=False)}
"""
```

**Return format**: `"General Recommendations:\n...\n\nRegional Recommendations:\n..."`

---

## 9. Analytics Service (`services/analytics_service.py`)

### `analyze_user_progress(user_id, days=7) -> str`

**Step 1 — Date range:**
```python
end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
```

**Step 2 — Aggregate metrics across all logs:**
```python
for log in logs:
    total_steps += details.get('steps') or 0
    total_sleep_mins += details.get('total_sleep_minutes') or 0
    total_water += details.get('hydration_level') or 0
    if details.get('weight_kg'): weights.append(details['weight_kg'])
    if details.get('mood'): moods.append(details['mood'])
    if details.get('stress_level'): stresses.append(details['stress_level'])
    for ex in log['exercise_entries']:
        total_exercise_mins += ex.get('duration_minutes') or 0
```

**Step 3 — Compute averages:**
```python
avg_steps = int(total_steps / total_logs)
avg_sleep_hours = (total_sleep_mins / total_logs) / 60
avg_water = total_water / total_logs
```

**Step 4 — Weight trajectory:**
```python
diff_w = weights[-1] - weights[0]
# "Increased by X kg" / "Decreased by X kg" / "Stable at X kg"
```

**Step 5 — Gemini evaluation prompt:**
```
You are a professional clinical wellness advisor. Analyze the following progress metrics...

User Profile:
- Name: {name}, Goal: {goal}, Diet: {food_preference}, Conditions: {conditions}

Progress Summary ({days} days):
{stats_summary}  # Contains emoji-formatted averages

Write a structured report containing:
1. **Overview & Consistency**: How consistent is the user with logging?
2. **Metrics Evaluation**: Are sleep, steps, hydration, and exercise aligned with their goal?
3. **Progress Direction**: Are they improving, regressing, or plateauing?
4. **Recommendations & Tips**: 3 clear, actionable adjustments for next week.

Format using neat Markdown suitable for Telegram.
```

---

## 10. Report Service (`services/report_service.py`)

A thin 10-line facade:
```python
import os
import report_generator
import config

def generate_daily_report(user_profile, log_data, full_analysis, recommendations):
    os.makedirs(config.REPORT_DIR, exist_ok=True)
    return report_generator.generate_daily_report(user_profile, log_data, full_analysis, recommendations)
```
Its sole purpose is ensuring `generated_reports/` exists before delegating to the actual PDF engine.

---

## 11. PDF Generator (`report_generator.py`)

### Text Sanitization
```python
def sanitize_text(text):
    if not isinstance(text, str): text = str(text)
    # Keep all BMP characters (Hindi, accents, math symbols) but strip 4-byte emojis
    return "".join(c for c in text if ord(c) < 0xffff)
```

### FPDF2 Subclass
```python
class PDF(FPDF):
    def header(self):
        assets_dir = os.path.join(config.BASE_DIR, "assets")
        # Register fonts (try/except RuntimeError: pass to avoid re-registration on page 2+)
        try: self.add_font('DejaVu', 'B', os.path.join(assets_dir, 'DejaVuSans-Bold.ttf'), uni=True)
        except RuntimeError: pass
        # ... same for regular and italic ...
        # Header bar: light gray background rect + centered title
        self.set_fill_color(240, 240, 240)
        self.rect(0, 0, 210, 10, 'F')
        self.set_font('DejaVu', 'B', 16)
        self.cell(0, 10, 'Aarogyam AI - Daily Wellness Report', 0, 1, 'C')

    def footer(self):
        self.set_y(-15)
        self.set_font('DejaVu', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def section_title(self, title):
        self.set_font('DejaVu', 'B', 14); self.set_text_color(0, 70, 100)
        self.cell(0, 10, sanitize_text(title), 'B', 1, 'L')  # Bottom border

    def section_body(self, text, is_list=False):
        # If is_list: parses string "[item1, item2]" or list, renders with bullet points
        # Handles both str and list inputs
```

### Step Progress Bar
```python
def draw_steps_bar(pdf, steps, goal=10000):
    steps = max(0, int(steps or 0))  # None-safe
    bar_width = 100; bar_height = 8
    # Gray background
    pdf.set_fill_color(220, 220, 220)
    pdf.rect(x, y, bar_width, bar_height, style='F')
    # Colored progress (green if met, red if not)
    progress_width = min((steps / goal) * bar_width, bar_width)
    bar_color = (76, 175, 80) if steps >= goal else (239, 83, 80)
    pdf.rect(x, y, progress_width, bar_height, style='F')
    # Label: "8500 / 10000 steps"
    pdf.cell(0, bar_height, f'{steps} / {goal} steps', 0, 1)
```

### `generate_daily_report()` — PDF Layout (3 pages)

**Page 1:**
1. Wellness Score (large green number in a bordered cell + justification)
2. User name + date
3. AI-Powered Insights section: Physical Activity Analysis, Mental Clarity Analysis
4. Image Analysis: Selfie analysis, Posture analysis, Day-over-day comparisons
5. Today's Metrics table (Weight, Sleep, Water Intake, Mood, Stress Level — all null-safe)
6. Step Progress Bar (visual bar with green/red coloring)

**Page 2:**
1. Nutritional Breakdown: For each meal:
   - Meal type header (bold)
   - User's text description (multi_cell, 115px wide)
   - Food photo embedded at x=130 (if exists, with aspect ratio preservation)
   - Nutrition table with columns: Component, Calories, Protein(g), Carbs(g), Fats(g), Vitamins_Minerals
   - Column widths: `{'component': 50, 'calories': 22, 'protein_g': 22, 'carbs_g': 22, 'fats_g': 20, 'vitamins_minerals': 40}`
   - Auto page-break if `pdf.get_y() > 220`

**Page 3:**
1. AI Summary & Recommendations: Overall Summary, Positives (bullet list), Improvements (bullet list)
2. Personalized Food Recommendations (RAG output)

**File naming**: `report_{user_id}_{YYYY-MM-DD}.pdf` → saved in `config.REPORT_DIR`

---

## 12. Telegram Bot Entry Point (`bot/main.py`)

### Handler Registration Order
```python
app.add_handler(start.get_start_handler())                                    # ConversationHandler
app.add_handler(log_metrics.get_log_handler())                                # ConversationHandler
app.add_handler(CommandHandler("meal", log_food.log_meal_cmd))
app.add_handler(MessageHandler(filters.Caption(["/meal"]), log_food.log_meal_cmd))  # Photo + /meal caption
app.add_handler(CommandHandler("exercise", log_food.log_exercise_cmd))
app.add_handler(CommandHandler("submit", report.submit_daily_log))
app.add_handler(CommandHandler("report", report.get_latest_report))
app.add_handler(CommandHandler("weekly", analytics.weekly_report_cmd))
app.add_handler(CommandHandler("monthly", analytics.monthly_report_cmd))
app.add_handler(CommandHandler("yearly", analytics.yearly_report_cmd))
app.add_handler(CommandHandler("profile", profile.view_profile))
app.add_handler(CommandHandler("location", profile.update_location_cmd))
app.add_handler(CommandHandler("workout", tools.workout_cmd))
app.add_handler(CommandHandler("alternative", tools.alternative_cmd))
app.add_handler(MessageHandler(filters.Caption(["/alternative"]), tools.alternative_cmd))
app.add_handler(CommandHandler("chat", chat.chat_cmd))
app.add_handler(MessageHandler(filters.Caption(["/chat"]), chat.chat_cmd))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(CallbackQueryHandler(callback_router))  # Global callback dispatcher
```

### Callback Router — Prefix-Based Dispatch
```python
async def callback_router(update, context):
    data = query.data
    if data.startswith("meal_"):           → log_food.meal_type_callback()
    elif data.startswith("toggleworkout_") or data == "save_workouts":
                                           → tools.workout_callback()
    elif data.startswith("edit_"):         → profile.profile_edit_callback()
    elif data.startswith("setgoal_"):      → profile.set_goal_callback()
    elif data.startswith("setfood_"):      → profile.set_food_callback()
```

### Daily Reminder Cron Job
```python
app.job_queue.run_daily(
    send_daily_reminders,
    time=datetime.time(hour=20, minute=0, second=0)  # 8:00 PM local
)

async def send_daily_reminders(context):
    conn = db.get_db_connection()
    users = conn.execute("SELECT user_id, name FROM users").fetchall()
    conn.close()
    for u in users:
        try:
            await context.bot.send_message(
                chat_id=u['user_id'],
                text=f"Good evening, {u['name'].split()[0]}! 🌅\n\n..."
            )
        except Exception:
            pass  # Per-user exception handling so one blocked user doesn't halt all
```

---

## 13. Bot Handlers — Complete Reference

### 13.1 Onboarding (`start.py`) — 9-State Conversation

**States**: `NAME, DOB, GENDER, HEIGHT, WEIGHT, STATE, CITY, FOOD, GOAL = range(9)`

```mermaid
stateDiagram-v2
    [*] --> NAME : /start (new user)
    [*] --> END : /start (existing user → welcome back message)
    NAME --> DOB : stores text → asks DOB
    DOB --> GENDER : validates YYYY-MM-DD format
    DOB --> DOB : invalid format → re-prompt
    GENDER --> HEIGHT : ReplyKeyboard [Male, Female, Other, Prefer not to say]
    HEIGHT --> WEIGHT : validates float cm
    HEIGHT --> HEIGHT : non-numeric → re-prompt
    WEIGHT --> STATE : validates float kg
    WEIGHT --> WEIGHT : non-numeric → re-prompt
    STATE --> CITY : stores text
    CITY --> FOOD : stores text
    FOOD --> GOAL : ReplyKeyboard [Vegetarian, Vegetarian + Non-Veg]
    GOAL --> [*] : ReplyKeyboard [5 goals] → db.add_user() → profile saved → cleanup user_data
```

**User data saved to DB**:
```python
user_data = {
    'name': '...', 'dob': '...', 'height_cm': float, 'gender': '...',
    'location_state': '...', 'city': '...', 'food_preference': '...',
    'health_goal': '...', 'preferred_exercise': [],  # Empty list
    'medical_conditions': 'NA', 'medications': 'NA', 'allergies': 'NA',
    'surgical_history': 'NA', 'family_history': 'NA'
}
db.add_user(user_data, user_id=update.effective_user.id)
```

### 13.2 Daily Metrics (`log_metrics.py`) — 10-State Conversation

**States**: `SLEEP, STEPS, MOOD, STRESS, HYDRATION, WEIGHT, TASKS, FOCUS, SELFIE, POSTURE = range(10)`

**Default daily_log structure** (initialized on `/log`):
```python
context.user_data['daily_log'] = {
    'user_id': user_id,
    'log_date': datetime.now().strftime('%Y-%m-%d'),
    'total_sleep_minutes': 480,  # 8h default
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
```

**Flow**:
- SLEEP: asks hours (float), converts `int(hours * 60)` → minutes
- STEPS: asks integer count
- MOOD: ReplyKeyboard `[["🤩 Ecstatic", "😁 Great", "🙂 Happy"], ["😊 Okay", "😐 Neutral", "😟 Anxious"], ["😞 Sad", "😭 Awful"]]`
- STRESS: ReplyKeyboard `[["Low", "Mild", "High"]]`
- HYDRATION: ReplyKeyboard `[["1.0L", "1.5L", "2.0L"], ["2.5L", "3.0L", "3.5L", "4.0L"]]` — strips "L" suffix, parses float
- WEIGHT: asks float kg
- TASKS: ReplyKeyboard `[["None", "A Few", "Majority", "All"]]`
- FOCUS: ReplyKeyboard `[["Low", "Medium", "High"]]`
- SELFIE: accepts `filters.PHOTO` or `/skip` command
- POSTURE: accepts `filters.PHOTO` or `/skip` command

**Image handling helper**:
```python
async def handle_image(update, context, subdir):
    photo = update.message.photo[-1]  # Highest resolution
    file = await photo.get_file()
    filename = f"{user_id}_{timestamp}_{subdir}.jpg"
    file_path = os.path.join(UPLOAD_DIR, subdir, filename)
    await file.download_to_drive(file_path)
    return file_path
```

**After completion**: Daily log stays in `context.user_data['daily_log']` so user can add meals/exercises before `/submit`.

### 13.3 Food & Exercise Logging (`log_food.py`)

**`ensure_daily_log_initialized(user_id, context)`**: Creates the same default dict as log_metrics if `daily_log` is missing. This lets users `/meal` or `/exercise` without running `/log` first.

**`/meal [description]`** (+ optional photo):
1. Downloads photo if present → `uploads/food/{user_id}_{timestamp}_food.jpg`
2. Stores temp state: `context.user_data['temp_meal'] = {'description': ..., 'food_image_path': ...}`
3. Shows InlineKeyboard: `[["Breakfast 🍳", "Lunch 🍱"], ["Dinner 🍽️", "Snack 🍎"]]`
4. Callback `meal_{type}` → appends to `daily_log['food_entries']`

**`/exercise [type] [mins] [details]`**:
```python
args = context.args  # e.g., ["Gym", "45", "Chest", "day"]
ex_type = args[0]       # "Gym"
duration = int(args[1])  # 45
details = " ".join(args[2:])  # "Chest day"
```

### 13.4 Chat Handler (`chat.py`)

**Memory Architecture**:
- Storage: `context.user_data['chat_history']` — list of `{"role": "user"|"model", "parts": ["text"]}`
- Window: 20 messages max (10 exchanges). Trimmed: `chat_history = chat_history[-20:]`
- System instruction: prepended to first message only, not stored in history

**Text mode**: Uses `model.start_chat(history=gemini_history)` with `chat.send_message()`

**Image mode**: One-shot call via `model.generate_content([system_instruction, PIL_image, query])`:
- If no text provided with image, defaults to: "Analyze this health-related image. If it is a prescription, extract medicine names, dosages, and instructions. If it is a skin condition or wound, describe it neutrally, provide general first aid, and include a medical disclaimer."

### 13.5 Workout System (`tools.py`)

**Callback data protocol**:
| Data | Action |
|---|---|
| `toggleworkout_{i}` | XOR toggle index in `completed_workout_indexes` set |
| `save_workouts` | Iterate set, append each to `daily_log['exercise_entries']`, clean up |

Each toggled exercise gets default `duration_minutes=20`.

### 13.6 Eco Alternatives (`tools.py`)

**Image path**: If photo attached, uses Gemini Vision to describe the object first, then searches:
```python
image_desc_response = vision_model.generate_content(["Describe the main object in this image", img])
detected_item = image_desc_response.text.strip()
query = f"Find healthy and eco-friendly alternatives for a {detected_item}..."
response = SearchAgentWrapper().run(query)  # Google Search grounded
```

### 13.7 Report Submission (`report.py`)

**`/submit` pipeline** (5-step):
1. `db.add_daily_log(daily_log)` → saves to SQLite, returns `log_id`
2. `db.get_full_daily_log(log_id)` → retrieves complete log with food/exercise entries
3. `db.get_previous_day_image_paths(user_id, date)` → for selfie/posture comparison
4. `ai_engine.generate_comprehensive_daily_analysis(...)` → multimodal Gemini call
5. `rag_engine.get_rag_recommendations(...)` → if no error in analysis
6. `report_service.generate_daily_report(...)` → PDF generation
7. Send PDF via `update.message.reply_document()`

**`/report`**: Lists files matching `report_{user_id}_*.pdf` in `generated_reports/`, sorts reverse by filename, sends latest.

### 13.8 Profile Management (`profile.py`)

**`/profile`** displays profile card + 3 InlineKeyboard buttons:
- `edit_goal` → shows 5 goal buttons (`setgoal_Weight Loss`, etc.)
- `edit_food` → shows 2 diet buttons (`setfood_Vegetarian`, etc.)
- `edit_location` → prompts to use `/location State City`

**`/location State City`**: `args[0]` = state, `" ".join(args[1:])` = city → `db.update_user_location()`

### 13.9 Analytics (`analytics.py`)

Three thin wrappers calling `analytics_service.analyze_user_progress(user_id, days)`:
- `/weekly` → `days=7`
- `/monthly` → `days=30`
- `/yearly` → `days=365`

---

## 14. Streamlit Web Dashboard

### `app.py` — Main Entry Point (229 lines)

**Session State Keys**:
```python
st.session_state.logged_in = False
st.session_state.user_info = None  # dict(Row) after login
st.session_state.page = "Login"    # "Login" | "Sign Up"
st.session_state.food_entries = []
st.session_state.exercise_entries = []
st.session_state.report_path = None
```

**Auth Flow**: Login with 5-digit user ID → `db.get_user(user_id)`. Signup generates a random 5-digit ID via `generate_unique_user_id()`.

**Image Processing in Streamlit** (different from Telegram):
```python
def save_uploaded_file(uploaded_file, subdir):
    img = Image.open(uploaded_file)
    img.thumbnail((512, 512))  # Resize to max 512x512
    img.convert("RGB").save(file_path, "JPEG", quality=85)
```

**Daily Log Form** (main_app):
- Food Diary: Dynamic list with add/remove buttons, file uploaders, text areas
- Exercise Diary: Dynamic list with type selectbox, details input, duration slider
- Metrics Form: sleep, steps, mood (select_slider with 8 emoji options), stress, weight, water, task completion, focus, travel expander, selfie/posture uploaders
- On submit: same pipeline as Telegram's `/submit` (db.add_daily_log → AI analysis → RAG → PDF)

### Streamlit Subpages (6 pages)

| Page | File | Model Used | Description |
|---|---|---|---|
| 🧠 Sukoon Saathi | `1_🧠_Sukoon_Saathi.py` | `gemini-1.0-pro` | Mental wellness chatbot using `start_chat()` with compassionate coach persona |
| 🩺 Sehat Darpan | `2_🩺_Sehat_Darpan.py` | `gemini-1.5-flash-latest` | 3 tabs: Skin/wound image analysis, Prescription OCR, General health chat |
| 🏋️‍♀️ Urja Path | `3_🏋️‍♀️_Urja_Path.py` | via `ai_utils` | Workout plan generator with checkbox completion tracking |
| 🌿 Shuddh Vikalp | `4_🌿_Shuddh_Vikalp.py` | via `ai_utils` | Eco-friendly alternative finder (image or text input) |
| 👩‍⚕️ Aahar Visheshagya | `5_👩‍⚕️_Aahar_Visheshagya.py` | `gemini-1.5-flash-latest` | AI nutritionist chatbot with persistent `start_chat()` history |
| ⚙️ Profile | `6_⚙️_Profile.py` | N/A | Profile display/edit form + report download archive |

> **Note**: Some Streamlit pages use older model names (`gemini-1.0-pro`, `gemini-1.5-flash-latest`) while the Telegram bot uniformly uses `gemini-2.0-flash`. This is a legacy discrepancy.

---

## 15. Legacy Bridge Module (`ai_utils.py`)

A 25-line module that delegates all calls to the services layer:
```python
from services import ai_engine, rag_engine

def get_master_model():              return ai_engine.get_model()
def get_text_model():                return ai_engine.get_text_model()
def get_vision_model():              return ai_engine.get_vision_model()
def get_fitness_plan(user_profile):  return ai_engine.get_fitness_plan(user_profile)
def get_environment_wellness_agent():return ai_engine.get_environment_wellness_agent()
def load_nutrient_data():            return rag_engine.load_nutrient_data()
def generate_comprehensive_daily_analysis(user_profile, log_data, prev_day_images):
    return ai_engine.generate_comprehensive_daily_analysis(user_profile, log_data, prev_day_images)
def get_rag_recommendations(user_profile, lacking_nutrient):
    return rag_engine.get_rag_recommendations(user_profile, lacking_nutrient)
```
Exists so Streamlit pages (`app.py`, subpages) can call `ai_utils.get_vision_model()` without importing the services module directly. This preserves backward compatibility.

---

## 16. End-to-End Data Flow Walkthrough

### Scenario: User completes a full day via Telegram

```
1. User sends /start → start.py ConversationHandler
   - 9-step guided onboarding via ReplyKeyboards
   - db.add_user(user_data, user_id=telegram_id)
   - Profile stored in users table

2. User sends /log → log_metrics.py ConversationHandler
   - 10-step questionnaire (sleep → steps → mood → ... → posture)
   - Photos downloaded to uploads/profile/
   - Result stored in context.user_data['daily_log'] (not DB yet)

3. User sends /meal "Rajma chawal with salad" + food photo
   - Photo downloaded to uploads/food/{id}_{ts}_food.jpg
   - Shows meal type InlineKeyboard
   - User taps "Lunch" → callback meal_Lunch
   - Appended to context.user_data['daily_log']['food_entries']

4. User sends /workout → tools.py
   - ai_engine.get_fitness_plan(user) → Gemini JSON array
   - Rendered as InlineKeyboard with ⬜/✅ toggles
   - User toggles exercises, taps "Save Completed Workouts"
   - Appended to context.user_data['daily_log']['exercise_entries']

5. User sends /submit → report.py submit_daily_log()
   Step 5a: db.add_daily_log(daily_log)
     - DELETE existing log for same user+date (cascade removes food/exercise)
     - INSERT daily_logs row → get log_id
     - INSERT food_entries rows
     - INSERT exercise_entries rows
   
   Step 5b: db.get_full_daily_log(log_id)
     - Returns {log_details, food_entries, exercise_entries}
   
   Step 5c: db.get_previous_day_image_paths(user_id, date)
     - Query yesterday's selfie_path and posture_pic_path
   
   Step 5d: ai_engine.generate_comprehensive_daily_analysis(...)
     - Builds multimodal prompt with text + up to 6 images
     - Gemini returns structured JSON with wellness_score, nutrition_analysis, etc.
   
   Step 5e: rag_engine.get_rag_recommendations(...)
     - Takes lacking_nutrient from Gemini output
     - Filters CSV for regional dishes
     - Gemini synthesizes friendly recommendation text
   
   Step 5f: report_generator.generate_daily_report(...)
     - 3-page PDF with score, metrics table, nutrition breakdown, images, recommendations
     - Saved as generated_reports/report_{id}_{date}.pdf
   
   Step 5g: update.message.reply_document(pdf_file)
     - Sends PDF to user in Telegram chat
     - Clears context.user_data['daily_log']

6. User sends /weekly → analytics.py → analytics_service.py
   - Fetches all logs from last 7 days
   - Aggregates steps, sleep, water, weight, mood, stress, exercise
   - Sends statistics + user profile to Gemini for evaluation
   - Returns formatted Markdown report in chat
```

---

## 17. Error Handling Patterns

| Pattern | Where Used | Behavior |
|---|---|---|
| `try/except ValueError → re-prompt` | All numeric inputs in ConversationHandlers | Returns same state to ask again |
| `try/except RuntimeError: pass` | Font registration in PDF header | Silently skips already-registered fonts |
| `try/except Exception → print + fallback` | All Gemini API calls | Logs error, returns fallback data or error message |
| `if not db.user_exists(user_id)` | Every handler's first line | Returns "Please register using /start" |
| `os.makedirs(..., exist_ok=True)` | Before any file write | Creates directory trees safely |
| `if file_path and os.path.exists(file_path)` | Before image embedding in PDF and AI prompts | Skips missing images gracefully |
| Per-user `try/except` in reminder loop | `send_daily_reminders()` | One blocked user doesn't halt all reminders |
| `{"error": ...}` key in analysis dict | AI analysis return | Downstream code checks `"error" not in full_analysis` before using results |

---

## 18. Dependencies & Setup

### `requirements.txt`
```
streamlit
langchain>=0.2
langchain-google-genai
langchain-community
langchain-ollama
google-generativeai>=0.8.0
pandas
fpdf2
pillow
toml
faiss-cpu
python-dotenv
python-telegram-bot[ext]>=21.0
apscheduler
```

> **Note**: `langchain*`, `faiss-cpu`, and `langchain-ollama` are legacy dependencies from the original architecture. The current code uses `google-generativeai` directly. They remain in requirements.txt for backward compatibility with the Streamlit pages.

### Setup Steps
```bash
# 1. Clone repository
git clone https://github.com/swaraj-dash/AarogyamAI.git
cd AarogyamAI

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure secrets
cp .env.example .env
# Edit .env with your TELEGRAM_BOT_TOKEN and GOOGLE_API_KEY

# 5. Run Telegram Bot
python bot/main.py

# 6. (Optional) Run Streamlit Dashboard
streamlit run app.py
```

---

## 19. Git Configuration

### `.gitignore`
```gitignore
venv/
.venv/
__pycache__/
*.pyc
.streamlit/secrets.toml
generated_reports/
uploads/
aarogyam.db
```

These exclusions ensure that user data (database, photos, PDFs) and secrets never reach the repository.

---

## 20. Known Limitations & Future Improvements

| Area | Current State | Potential Improvement |
|---|---|---|
| **Database** | Single SQLite file, concurrent access via 20s timeout | Migrate to PostgreSQL for production multi-user |
| **Streamlit Models** | Some pages use `gemini-1.0-pro` / `gemini-1.5-flash-latest` | Unify all to `gemini-2.0-flash` |
| **Chat Memory** | In-memory only (`context.user_data`), lost on bot restart | Persist to database |
| **Image Storage** | Local filesystem | Migrate to cloud storage (S3/GCS) |
| **Authentication** | Telegram ID (no password) / 5-digit web ID (no password) | Add proper auth for Streamlit |
| **Legacy Dependencies** | `langchain*`, `faiss-cpu` in requirements.txt | Remove unused packages |
| **PDF Emojis** | Stripped by `sanitize_text()` BMP filter | Use emoji-capable font or render as images |
| **Reminder Timezone** | Uses server local time | Let users configure timezone |
| **Weight in User Table** | Not stored on user profile (only in daily_logs) | Add `current_weight` column to users |
| **Concurrent Writes** | SQLite file locking | Use WAL mode or PostgreSQL |
