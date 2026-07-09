import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

import database as db

st.set_page_config(page_title="Log Day · AarogyamAI", page_icon="📝")

if "user_id" not in st.session_state:
    st.warning("Please log in from the main page first.")
    st.stop()

user_id = st.session_state["user_id"]
st.title("Log today")

log_date = st.date_input("Date", value=date.today())

with st.form("daily_log_form"):
    col1, col2 = st.columns(2)
    with col1:
        sleep_hours = st.number_input("Hours of sleep", min_value=0.0, max_value=16.0, step=0.5, value=7.5)
        steps = st.number_input("Steps", min_value=0, step=500, value=6000)
        weight = st.number_input("Weight (kg)", min_value=0.0, step=0.1, value=0.0,
                                  help="Leave at 0 to skip")
    with col2:
        mood = st.selectbox("Mood", ["great", "good", "okay", "low", "bad"], index=1)
        hydration = st.number_input("Water (litres)", min_value=0.0, step=0.25, value=2.0)
        stress = st.selectbox("Stress level", ["low", "medium", "high"], index=0)

    submitted = st.form_submit_button("Save log", type="primary")
    if submitted:
        log_id = db.get_or_create_daily_log(user_id, log_date.isoformat())
        db.update_daily_log_fields(log_id, {
            "total_sleep_minutes": int(sleep_hours * 60),
            "steps": int(steps),
            "mood": mood,
            "weight_kg": weight if weight > 0 else None,
            "hydration_level": hydration,
            "stress_level": stress,
        })
        st.success(f"Saved your log for {log_date.isoformat()}.")

st.divider()
st.subheader("Add a meal")
with st.form("food_form"):
    meal_type = st.selectbox("Meal", ["breakfast", "lunch", "dinner", "snack"])
    description = st.text_input("What did you eat?")
    food_submitted = st.form_submit_button("Add meal")
    if food_submitted and description.strip():
        log_id = db.get_or_create_daily_log(user_id, log_date.isoformat())
        db.add_food_entry_only(log_id, meal_type, description=description.strip())
        st.success(f"Added {meal_type}: {description.strip()}")

st.divider()
st.subheader("Add exercise")
with st.form("exercise_form"):
    exercise_type = st.text_input("Exercise type (e.g. yoga, running, gym)")
    duration = st.number_input("Duration (minutes)", min_value=0, step=5, value=30)
    exercise_submitted = st.form_submit_button("Add exercise")
    if exercise_submitted and exercise_type.strip():
        log_id = db.get_or_create_daily_log(user_id, log_date.isoformat())
        db.add_exercise_entry_only(log_id, exercise_type.strip(), duration_minutes=int(duration))
        st.success(f"Added {exercise_type.strip()} ({duration} min)")
