# Aarogyam AI - Complete Project Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Project Structure](#project-structure)
3. [Core Features & Functionality](#core-features--functionality)
4. [Technical Implementation Details](#technical-implementation-details)
5. [AI Models & APIs Used](#ai-models--apis-used)
6. [Database Schema](#database-schema)
7. [How to Run the Project](#how-to-run-the-project)
8. [File-by-File Explanation](#file-by-file-explanation)

---

## Project Overview

**Aarogyam AI** is a comprehensive, AI-powered health and wellness application built with Streamlit. It provides personalized insights and guidance across multiple dimensions of health including mental wellness, physical fitness, nutrition, and lifestyle. The application leverages advanced AI models from Google (Gemini), local AI models via Ollama (Llama 3), and various machine learning techniques to deliver a holistic wellness experience.

### Key Objectives:
- Centralized platform for logging health and wellness metrics
- AI-powered personalized insights based on user data
- Mental wellness support through chatbots
- Nutrition analysis and recommendations
- Fitness planning and tracking
- Eco-friendly product alternatives
- Downloadable PDF wellness reports

---

## Project Structure

```
aarogyamai/
├── app.py                          # Main Streamlit application entry point
├── ai_utils.py                     # AI model configurations and utility functions
├── database.py                     # SQLite database management
├── report_generator.py             # PDF report generation module
├── requirements.txt                # Python dependencies
├── README.md                       # Project overview and specifications
├── .gitignore                      # Git ignore rules
├── assets/                         # Font files for PDF generation
│   ├── DejaVuSans.ttf
│   ├── DejaVuSans-Bold.ttf
│   └── DejaVuSans-Oblique.ttf
├── pages/                          # Streamlit multi-page app pages
│   ├── 1_🧠_Sukoon_Saathi.py      # Mental wellness chatbot
│   ├── 2_🩺_Sehat_Darpan.py       # Health image analysis & assistant
│   ├── 3_🏋️‍♀️_Urja_Path.py         # Personalized workout plans
│   ├── 4_🌿_Shuddh_Vikalp.py      # Eco-friendly alternatives
│   ├── 5_👩‍⚕️_Aahar_Visheshagya.py # Nutritionist chatbot
│   └── 6_⚙️_Profile.py           # User profile & reports
├── rag_data/                       # RAG system data
│   └── india_state_meal_nutrient_recs.csv
├── faiss_index/                    # FAISS vector database
│   ├── index.faiss
│   └── index.pkl
├── uploads/                        # User uploaded images
│   ├── food/
│   └── profile/
└── generated_reports/              # Generated PDF reports
```

---

## Core Features & Functionality

### 1. User Authentication & Onboarding
- **Signup System**: Creates a detailed wellness profile including:
  - Personal info (name, DOB, gender, height, weight)
  - Location (state, city)
  - Food preferences (Vegetarian/Veg+Non-Veg)
  - Health goals (Weight Loss, Weight Gain, etc.)
  - Medical history (conditions, medications, allergies)
  - Family medical history
- **Login System**: 5-digit unique user ID authentication
- **Profile Management**: Users can view and edit their profile

### 2. Daily Logging System
Users can log their daily activities including:
- **Food Diary**: 
  - Meal type (Breakfast, Lunch, Dinner, Snack)
  - Photo uploads of food
  - Text descriptions
- **Exercise Diary**:
  - Exercise type (Gym, Yoga, Sports, etc.)
  - Duration in minutes
  - Details and sets/reps
- **Other Metrics**:
  - Sleep hours
  - Step count
  - Mood tracking
  - Stress level
  - Focus level
  - Water intake
  - Weight
  - Task completion
  - Travel information

### 3. AI-Powered Analysis (Master AI)
The app uses **Gemini 1.5 Flash** to analyze:
- **Wellness Score**: 1-100 score with justification
- **Physical Activity Analysis**: Feedback on steps and exercise
- **Mental Clarity Analysis**: Summary of mood, stress, focus, sleep
- **Nutritional Analysis**: 
  - Per-meal breakdown with calorie/macronutrient estimates
  - Overall diet summary
  - Positives and improvement areas
- **Image Analysis**:
  - Selfie analysis for skin clarity, tiredness
  - Posture photo analysis
- **Comparative Analysis**: Compare today's images with yesterday's

### 4. RAG-Powered Recommendations
- Uses **FAISS** vector database for similarity search
- Integrates with **Ollama (Llama 3)** for generating contextual recommendations
- Provides state-specific meal recommendations based on nutritional deficiencies
- Considers user's food preferences and location

### 5. PDF Report Generation
- Comprehensive daily wellness report
- Includes:
  - Wellness score
  - AI insights
  - Metrics table
  - Nutritional breakdown with images
  - Personalized recommendations
- Custom fonts (DejaVu Sans) for professional appearance

### 6. Sukoon Saathi (Mental Wellness Coach)
- AI chatbot using **Gemini 1.0 Pro**
- Compassionate mental wellness support
- Safe space for users to talk and reflect
- Session-based conversation history

### 7. Sehat Darpan (Health Mirror)
- **Skin/Wound Analysis**: Upload images for AI analysis
- **Prescription Analysis**: Read and summarize prescriptions
- **Health Chat Assistant**: General health Q&A

### 8. Urja Path (Energy Path)
- Generates personalized daily workout plans
- Considers user's health goals and preferences
- Integrates with daily log

### 9. Shuddh Vikalp (Pure Alternative)
- Suggests healthy, eco-friendly alternatives
- Uses web search agent (Tavily API)
- Image-based or text-based queries

### 10. Aahar Visheshagya (Nutritionist Coach)
- Expert nutrition chatbot using **Gemini 1.5 Flash**
- Diet plan advice
- Healthy recipes
- Nutrition education

---

## Technical Implementation Details

### Frontend Framework
- **Streamlit**: Python-based web framework for rapid UI development
- Multi-page application architecture
- Session state management for user data

### Backend & Database
- **SQLite**: Lightweight SQL database for data persistence
- Tables: users, daily_logs, food_entries, exercise_entries, reports

### AI/ML Integration
- **Google Gemini Models**:
  - `gemini-1.5-flash-latest`: Main analysis model
  - `gemini-1.0-pro`: Mental wellness chatbot
  - Vision capabilities for image analysis
- **Ollama (Llama 3)**: Local LLM for RAG recommendations
- **FAISS**: Vector database for semantic search
- **LangChain**: Framework for building LLM chains and agents

### PDF Generation
- **FPDF2**: Python library for PDF creation
- Custom fonts embedded (DejaVu Sans family)
- Image embedding support
- Professional formatting with headers, footers, tables

---

## AI Models & APIs Used

| Feature | Model/Technology | Purpose |
|---------|-----------------|---------|
| Master Analysis | Gemini 1.5 Flash | Comprehensive daily log analysis |
| Mental Wellness | Gemini 1.0 Pro | Sukoon Saathi chatbot |
| Nutrition Coach | Gemini 1.5 Flash | Aahar Visheshagya chatbot |
| Health Assistant | Gemini 1.5 Flash | Sehat Darpan chatbot |
| Vision Analysis | Gemini Vision | Skin, prescription, food image analysis |
| RAG Recommendations | Ollama (Llama 3) | State-specific meal suggestions |
| Vector Search | FAISS | Semantic search in nutrient database |
| Web Search | Tavily API | Shuddh Vikalp alternatives search |

---

## Database Schema

### Users Table
```
sql
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    dob TEXT NOT NULL,
    height_cm REAL NOT NULL,
    gender TEXT NOT NULL,
    location_state TEXT NOT NULL,
    city TEXT NOT NULL,
    food_preference TEXT NOT NULL,
    health_goal TEXT NOT NULL,
    preferred_exercise TEXT,
    medical_conditions TEXT,
    medications TEXT,
    allergies TEXT,
    surgical_history TEXT,
    family_history TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Daily Logs Table
```
sql
CREATE TABLE daily_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    log_date TEXT NOT NULL,
    total_sleep_minutes INTEGER,
    steps INTEGER,
    mood TEXT,
    weight_kg REAL,
    selfie_path TEXT,
    posture_pic_path TEXT,
    travel_info TEXT,
    hydration_level REAL,
    stress_level TEXT,
    menstrual_cycle_day INTEGER,
    task_completion TEXT,
    focus_level TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
)
```

### Food Entries Table
```
sql
CREATE TABLE food_entries (
    food_id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_id INTEGER NOT NULL,
    meal_type TEXT NOT NULL,
    food_image_path TEXT,
    description TEXT,
    FOREIGN KEY (log_id) REFERENCES daily_logs(log_id) ON DELETE CASCADE
)
```

### Exercise Entries Table
```
sql
CREATE TABLE exercise_entries (
    exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_id INTEGER NOT NULL,
    exercise_type TEXT NOT NULL,
    details TEXT,
    duration_minutes INTEGER,
    FOREIGN KEY (log_id) REFERENCES daily_logs(log_id) ON DELETE CASCADE
)
```

---

## File-by-File Explanation

### app.py (Main Application)
**Purpose**: Main Streamlit entry point handling routing, authentication, and daily logging

**Key Functions**:
- `signup_page()`: User registration with comprehensive wellness profile
- `login_page()`: User authentication using 5-digit ID
- `main_app()`: Daily log entry interface with food, exercise, and metrics
- `save_uploaded_file()`: Process and save uploaded images
- `reset_daily_log_forms()`: Clear form data after submission

**Session State Management**:
- `logged_in`: Boolean for authentication status
- `user_info`: Dictionary containing user profile data
- `page`: Current page/route
- `food_entries`: List of food log entries
- `exercise_entries`: List of exercise log entries
- `report_path`: Path to generated PDF

---

### ai_utils.py (AI Utilities)
**Purpose**: Central configuration for all AI models and utility functions

**Key Components**:

1. **Model Configuration**:
   - `MASTER_ANALYSIS_MODEL_NAME`: "gemini-1.5-flash-latest"
   - `TEXT_MODEL_NAME`: "gemini-1.5-flash-latest"
   - API key configuration via Streamlit secrets

2. **Functions**:
   - `get_master_model()`: Returns configured Gemini model for analysis
   - `get_text_model()`: Returns text generation model
   - `get_vision_model()`: Returns vision-capable model
   - `load_nutrient_data()`: Loads RAG CSV data into pandas DataFrame

3. **generate_comprehensive_daily_analysis()**:
   - Takes user profile, log data, and previous day images
   - Constructs multimodal prompt with text and images
   - Requests structured JSON output with wellness score, nutrition analysis, etc.
   - Handles image comparison between days

4. **get_rag_recommendations(user_profile, lacking_nutrient)**:
   - Generates general food recommendations
   - Loads state-specific nutrient data
   - Filters by state, food preference, and deficient nutrient
   - Uses Ollama (Llama 3) via LangChain to generate contextual recommendations
   - Returns both general and state-specific advice

5. **get_environment_wellness_agent()**:
   - Creates LangChain agent for web search
   - Uses Tavily API for finding eco-friendly alternatives

---

### database.py (Database Management)
**Purpose**: SQLite database operations for all data persistence

**Key Functions**:

1. `create_tables()`: Initializes all database tables
2. `generate_unique_user_id()`: Creates 5-digit unique ID
3. `add_user(user_data)`: Creates new user profile
4. `get_user(user_id)`: Retrieves user by ID
5. `update_user_profile()`: Updates user information
6. `update_user_location()`: Updates city/state
7. `add_daily_log(log_data)`: Saves complete daily log with food/exercise entries
8. `get_full_daily_log(log_id)`: Retrieves complete log with all entries
9. `get_previous_day_image_paths()`: Fetches images for comparison

---

### report_generator.py (PDF Generation)
**Purpose**: Creates professional PDF wellness reports

**Key Components**:

1. **PDF Class** (extends FPDF):
   - Custom header with logo and title
   - Footer with page numbers
   - `section_title()`: Formatted section headers
   - `section_body()`: Content with list support
   - `draw_steps_bar()`: Visual step progress bar

2. **generate_daily_report()**:
   - Takes user profile, log data, AI analysis, and recommendations
   - Generates multi-page professional report
   - Embeds food images
   - Creates nutrition tables
   - Formats AI summaries and recommendations

3. **Special Features**:
   - Unicode font support (DejaVu Sans)
   - Image aspect ratio preservation
   - Automatic page breaks
   - Error handling for image embedding

---

### pages/1_🧠_Sukoon_Saathi.py
**Purpose**: Mental wellness chatbot

**Features**:
- Uses Gemini 1.0 Pro
- Session-based chat history
- Compassionate AI persona
- Requires user login

---

### pages/2_🩺_Sehat_Darpan.py
**Purpose**: Health image analysis and Q&A

**Tabs**:
1. **Skin Analysis**: Upload skin/wound images for AI analysis
2. **Prescription Reader**: Extract medicine details from prescription images
3. **Health Chat**: General health questions answered by AI

**Features**:
- Uses Gemini Vision for image analysis
- Medical disclaimers
- Structured responses for prescriptions

---

### pages/3_🏋️‍♀️_Urja_Path.py
**Purpose**: Personalized workout plan generation

**Features**:
- Generates daily workout based on user goals and preferences
- Interactive checkboxes for completion tracking
- Integrates completed exercises to daily log

---

### pages/4_🌿_Shuddh_Vikalp.py
**Purpose**: Eco-friendly alternatives finder

**Features**:
- Image or text-based queries
- Uses Tavily API via LangChain agent
- Searches for healthy and sustainable alternatives
- Provides links for purchasing in India

---

### pages/5_👩‍⚕️_Aahar_Visheshagya.py
**Purpose**: Nutritionist chatbot

**Features**:
- Expert nutrition advice
- Diet plan recommendations
- Healthy recipe suggestions
- Gemini 1.5 Flash powered

---

### pages/6_⚙️_Profile.py
**Purpose**: User profile management and report downloads

**Features**:
- Display current profile information
- Edit profile form with validation
- List of generated PDF reports
- Download past reports

---

## How to Run the Project

### Prerequisites
1. Python 3.8+
2. API Keys (in `.streamlit/secrets.toml`):
   - `GOOGLE_API_KEY`: For Gemini models
   - `TAVILY_API_KEY`: For web search (Shuddh Vikalp)

### Installation Steps

1. **Clone the repository**
2. **Install dependencies**:
   
```
bash
   pip install -r requirements.txt
   
```
3. **Configure secrets**:
   Create `.streamlit/secrets.toml`:
   
```
toml
   GOOGLE_API_KEY = "your-api-key-here"
   TAVILY_API_KEY = "your-tavily-key-here"
   
```
4. **Run the application**:
   
```
bash
   streamlit run app.py
   
```

### For Local RAG (Optional)
- Install and run Ollama with Llama 3
- The app will automatically detect local availability

---

## Dependencies

| Package | Purpose |
|---------|---------|
| streamlit | Web UI framework |
| google-generativeai | Gemini AI models |
| langchain | LLM orchestration |
| langchain-community | LangChain integrations |
| langchain-ollama | Ollama local models |
| langchain-google-genai | Google GenAI integration |
| pandas | Data handling |
| fpdf2 | PDF generation |
| pillow | Image processing |
| faiss-cpu | Vector database |
| python-dotenv | Environment variables |

---

## Conclusion

Aarogyam AI represents a comprehensive approach to personal wellness management, combining multiple AI technologies to provide personalized, actionable insights. The application demonstrates advanced integration of:
- Multimodal AI for analyzing text, images, and structured data
- Retrieval-Augmented Generation for domain-specific recommendations
- Agentic AI for web search and real-time information
- Professional PDF reporting for tangible outputs

This project serves as a foundation for building sophisticated health and wellness applications with modern AI capabilities.
