# pages/3_🏋️‍♀️_Urja_Path.py

import streamlit as st
import ai_utils
import json

st.set_page_config(page_title="Urja Path", page_icon="🏋️‍♀️")

st.title("🏋️‍♀️ Urja Path")
st.write("Get a personalized daily workout plan based on your goals.")

if 'user_info' not in st.session_state or not st.session_state.user_info:
    st.error("Please log in from the main page to get your fitness plan.")
    st.stop()

user = st.session_state.user_info

st.info(f"""
**Your Profile:**
- **Goal:** {user.get('health_goal')}
- **Preferences:** {', '.join(json.loads(user.get('preferred_exercise', '[]')))}
""")

if 'fitness_plan' not in st.session_state:
    st.session_state.fitness_plan = None

if st.button("Generate Today's Workout Plan"):
    with st.spinner("Creating a personalized plan for you..."):
        st.session_state.fitness_plan = ai_utils.get_fitness_plan(user)

if st.session_state.fitness_plan:
    st.header("Today's Plan")
    st.write("Check off the exercises as you complete them. This will be automatically added to your daily log!")
    
    completed_exercises = []
    
    for i, item in enumerate(st.session_state.fitness_plan):
        activity = item.get('activity', 'N/A')
        duration = item.get('duration_or_sets', 'N/A')
        
        col1, col2 = st.columns([1, 4])
        is_done = col1.checkbox("", key=f"ex_{i}")
        col2.metric(label=activity, value=duration)
        
        if is_done:
            completed_exercises.append({
                'type': "AI Recommended",
                'details': activity,
                'duration_minutes': 30 # Placeholder, more complex parsing would be needed for exact time
            })

    if st.button("Add Completed to Daily Log"):
        # This demonstrates how to link back to the main app's state.
        # In a real app, you'd want a more robust state management.
        if 'exercise_entries' not in st.session_state:
            st.session_state.exercise_entries = []
        
        st.session_state.exercise_entries.extend(completed_exercises)
        st.success(f"Added {len(completed_exercises)} completed exercises to your daily log on the main page.")
        st.info("Go to the 'Your Daily Log' page to see them added. You can fill out the rest of your log and submit.")