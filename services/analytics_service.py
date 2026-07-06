import os
from datetime import datetime, timedelta
import database as db
from services import ai_engine

def analyze_user_progress(user_id, days=7):
    """Aggregates user log statistics over a date range and queries Gemini for a progress review."""
    user = db.get_user(user_id)
    if not user:
        return "User not found."

    user_profile = dict(user)
    
    # Calculate date range
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    # Fetch logs
    logs = db.get_logs_in_range(user_id, start_date, end_date)
    if not logs:
        return f"No logs found in the last {days} days. Please use /log daily to track your metrics!"

    total_logs = len(logs)
    
    # Aggregate metrics
    total_steps = 0
    total_sleep_mins = 0
    total_water = 0
    total_exercise_mins = 0
    
    weights = []
    moods = []
    stresses = []
    focus_levels = []
    
    for log in logs:
        details = log['log_details']
        
        # steps
        total_steps += details.get('steps') or 0
        # sleep
        total_sleep_mins += details.get('total_sleep_minutes') or 0
        # water
        total_water += details.get('hydration_level') or 0
        # weight
        if details.get('weight_kg'):
            weights.append(details['weight_kg'])
        # mood
        if details.get('mood'):
            moods.append(details['mood'])
        # stress
        if details.get('stress_level'):
            stresses.append(details['stress_level'])
        # focus
        if details.get('focus_level'):
            focus_levels.append(details['focus_level'])
            
        # exercises
        for ex in log['exercise_entries']:
            total_exercise_mins += ex.get('duration_minutes') or 0
            
    # Calculate averages
    avg_steps = int(total_steps / total_logs)
    avg_sleep_hours = (total_sleep_mins / total_logs) / 60
    avg_water = total_water / total_logs
    
    # Weight changes
    weight_change_str = "No weight updates logged."
    if weights:
        start_w = weights[0]
        end_w = weights[-1]
        diff_w = end_w - start_w
        if diff_w > 0:
            weight_change_str = f"Increased by {diff_w:.1f} kg (from {start_w:.1f} kg to {end_w:.1f} kg)"
        elif diff_w < 0:
            weight_change_str = f"Decreased by {abs(diff_w):.1f} kg (from {start_w:.1f} kg to {end_w:.1f} kg)"
        else:
            weight_change_str = f"Stable at {end_w:.1f} kg"
            
    # Formulate statistics text
    stats_summary = (
        f"--- Wellness Statistics over the last {days} days ---\n"
        f"📝 Days Logged: {total_logs}/{days}\n"
        f"🏃 Average Daily Steps: {avg_steps} steps\n"
        f"😴 Average Daily Sleep: {avg_sleep_hours:.1f} hours\n"
        f"💧 Average Daily Hydration: {avg_water:.1f} Liters\n"
        f"🏋️ Total Exercise Time: {total_exercise_mins} minutes\n"
        f"⚖️ Weight Progression: {weight_change_str}\n"
        f"🧠 Mood Logs: {', '.join(moods[-5:]) if moods else 'None'}\n"
        f"🧘 Stress Levels: {', '.join(stresses[-5:]) if stresses else 'None'}\n"
    )

    # Ask Gemini 2.0 Flash to synthesize a progress evaluation
    model = ai_engine.get_model()
    
    prompt = f"""
    You are a professional clinical wellness advisor. Analyze the following progress metrics of a user and write a high-fidelity wellness evaluation report.
    
    User Profile:
    - Name: {user_profile['name']}
    - Primary Health Goal: {user_profile['health_goal']}
    - Food Preference: {user_profile['food_preference']}
    - Existing Medical Conditions: {user_profile.get('medical_conditions', 'None')}
    
    Progress Summary ({days} days):
    {stats_summary}
    
    Write a structured report containing:
    1. **Overview & Consistency**: How consistent is the user with logging?
    2. **Metrics Evaluation**: Are sleep, steps, hydration, and exercise aligned with their health goal ({user_profile['health_goal']})?
    3. **Progress Direction**: Are they improving, regression, or plateauing? Specifically mention weight changes or mental indicators (mood/stress).
    4. **Recommendations & Tips**: Provide 3 clear, actionable adjustments they should make next week to speed up progress.
    
    Format the output using neat Markdown styling suitable for Telegram messages. Keep it professional, encouraging, and clear.
    """
    
    try:
        response = model.generate_content(prompt)
        report_text = f"📊 **{days}-Day Wellness Progress Report** 📊\n\n{stats_summary}\n{response.text}"
        return report_text
    except Exception as e:
        print(f"Failed to generate progress report via Gemini: {e}")
        return (
            f"📊 **{days}-Day Wellness Progress Report** 📊\n\n"
            f"{stats_summary}\n"
            f"❌ Could not generate AI progress review: {e}"
        )
