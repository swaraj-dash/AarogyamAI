import sqlite3
import random
import time
from datetime import datetime, timedelta
import json
import os
import config

def get_db_connection():
    """Establishes a connection to the database with a timeout and enables foreign keys support."""
    conn = sqlite3.connect(config.DATABASE_PATH, timeout=20.0)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    """Creates all necessary tables if they don't exist."""
    conn = get_db_connection()
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
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
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_logs (
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
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS food_entries (
            food_id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_id INTEGER NOT NULL,
            meal_type TEXT NOT NULL,
            food_image_path TEXT,
            description TEXT,
            FOREIGN KEY (log_id) REFERENCES daily_logs(log_id) ON DELETE CASCADE
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS exercise_entries (
            exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_id INTEGER NOT NULL,
            exercise_type TEXT NOT NULL,
            details TEXT,
            duration_minutes INTEGER,
            FOREIGN KEY (log_id) REFERENCES daily_logs(log_id) ON DELETE CASCADE
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            report_type TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            file_path TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    conn.commit()
    conn.close()

def generate_unique_user_id():
    """Generates a unique 5-digit user ID."""
    conn = get_db_connection()
    c = conn.cursor()
    while True:
        ts_part = str(int(time.time() * 1000))[-3:]
        rand_part = str(random.randint(10, 99))
        user_id = int(ts_part + rand_part)
        c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if c.fetchone() is None:
            conn.close()
            return user_id

def add_user(user_data, user_id=None):
    """Adds a new user to the database."""
    conn = get_db_connection()
    c = conn.cursor()
    if user_id is None:
        user_id = generate_unique_user_id()
    c.execute('''
        INSERT INTO users (user_id, name, dob, height_cm, gender, location_state, city, food_preference,
                         health_goal, preferred_exercise, medical_conditions, 
                         medications, allergies, surgical_history, family_history)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, user_data['name'], user_data['dob'], user_data['height_cm'],
          user_data['gender'], user_data['location_state'], user_data['city'], user_data['food_preference'],
          user_data['health_goal'], json.dumps(user_data['preferred_exercise']), 
          user_data['medical_conditions'], user_data['medications'], 
          user_data['allergies'], user_data['surgical_history'],
          user_data['family_history']))
    conn.commit()
    conn.close()
    return user_id

def get_user(user_id):
    """Retrieves a user's data by their user_id."""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return user if user else None

def update_user_profile(user_id, user_data):
    """Updates a user's profile information."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE users SET
        name = ?, dob = ?, height_cm = ?, gender = ?, location_state = ?, city = ?, 
        food_preference = ?, health_goal = ?, preferred_exercise = ?
        WHERE user_id = ?
    ''', (
        user_data['name'], user_data['dob'], user_data['height_cm'], user_data['gender'],
        user_data['location_state'], user_data['city'], user_data['food_preference'],
        user_data['health_goal'], json.dumps(user_data['preferred_exercise']), user_id
    ))
    conn.commit()
    conn.close()

def update_user_location(user_id, new_city, new_state):
    """Updates only the user's location."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET city = ?, location_state = ? WHERE user_id = ?", (new_city, new_state, user_id))
    conn.commit()
    conn.close()

def add_daily_log(log_data):
    """Adds a full daily log entry, replacing any existing entry for the same user and date."""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if a log for this date and user already exists
    c.execute("SELECT log_id FROM daily_logs WHERE user_id = ? AND log_date = ?", 
              (log_data['user_id'], log_data['log_date']))
    existing = c.fetchone()
    if existing:
        # Cascade delete is enabled, so this automatically removes associated food_entries and exercise_entries
        c.execute("DELETE FROM daily_logs WHERE log_id = ?", (existing['log_id'],))
        
    c.execute('''
        INSERT INTO daily_logs (user_id, log_date, total_sleep_minutes, steps, mood, weight_kg,
                                selfie_path, posture_pic_path, travel_info, hydration_level,
                                stress_level, menstrual_cycle_day, task_completion, focus_level)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (log_data['user_id'], log_data['log_date'], log_data['total_sleep_minutes'], 
          log_data['steps'], log_data['mood'], log_data['weight_kg'], log_data['selfie_path'],
          log_data['posture_pic_path'], json.dumps(log_data['travel_info']), 
          log_data['hydration_level'], log_data['stress_level'], 
          log_data.get('menstrual_cycle_day'), log_data['task_completion'], log_data['focus_level']))
    log_id = c.lastrowid
    for food in log_data['food_entries']:
        c.execute('INSERT INTO food_entries (log_id, meal_type, food_image_path, description) VALUES (?, ?, ?, ?)',
                  (log_id, food['meal_type'], food['food_image_path'], food['description']))
    for exercise in log_data['exercise_entries']:
        c.execute('INSERT INTO exercise_entries (log_id, exercise_type, details, duration_minutes) VALUES (?, ?, ?, ?)',
                  (log_id, exercise['exercise_type'], exercise['details'], exercise['duration_minutes']))
    conn.commit()
    conn.close()
    return log_id

def get_full_daily_log(log_id):
    """Retrieves a full daily log with associated food and exercise."""
    conn = get_db_connection()
    log = conn.execute("SELECT * FROM daily_logs WHERE log_id = ?", (log_id,)).fetchone()
    if not log:
        conn.close()
        return None
    foods = conn.execute("SELECT * FROM food_entries WHERE log_id = ?", (log_id,)).fetchall()
    exercises = conn.execute("SELECT * FROM exercise_entries WHERE log_id = ?", (log_id,)).fetchall()
    conn.close()
    return {
        "log_details": dict(log),
        "food_entries": [dict(f) for f in foods],
        "exercise_entries": [dict(e) for e in exercises]
    }

def get_previous_day_image_paths(user_id, current_log_date):
    """Fetches image paths from the log of the previous day."""
    conn = get_db_connection()
    try:
        current_date = datetime.strptime(current_log_date, '%Y-%m-%d').date()
        previous_date = current_date - timedelta(days=1)
        previous_date_str = previous_date.strftime('%Y-%m-%d')
        
        c = conn.cursor()
        c.execute(
            "SELECT selfie_path, posture_pic_path FROM daily_logs WHERE user_id = ? AND log_date = ?",
            (user_id, previous_date_str)
        )
        paths = c.fetchone()
        conn.close()
        return dict(paths) if paths else None
    except Exception as e:
        print(f"Error fetching previous day's images: {e}")
        conn.close()
        return None

def user_exists(user_id):
    """Checks if a user exists in the database by their user_id."""
    conn = get_db_connection()
    user = conn.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return user is not None
