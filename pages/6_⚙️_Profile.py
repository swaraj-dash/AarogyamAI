import streamlit as st
import database as db
import json
from datetime import datetime
import os
st.set_page_config(page_title="Profile & Settings", page_icon="⚙️")
st.title("⚙️ Your Profile and Reports")

if 'user_info' not in st.session_state or not st.session_state.user_info:
    st.error("Please log in from the main page to view your profile.")
    st.stop()

user_info = st.session_state.user_info

st.subheader("Current Profile Details")
# Display a neat table of the user's current info
profile_data = {
    "Name": user_info['name'],
    "Date of Birth": user_info['dob'],
    "Gender": user_info['gender'],
    "Height": f"{user_info['height_cm']:.2f} cm",
    "City": user_info['city'],
    "State": user_info['location_state'],
    "Food Preference": user_info['food_preference'],
    "Main Goal": user_info['health_goal'],
    "Preferred Exercises": ", ".join(json.loads(user_info.get('preferred_exercise', '[]')))
}
st.table(profile_data)

st.subheader("Edit Your Profile")
with st.expander("Click here to modify your profile details"):
    with st.form("edit_profile_form"):
        st.write("Update your information below and click save.")
        
        # Pre-fill form with existing data
        name = st.text_input("Full Name", value=user_info['name'])
        dob_val = datetime.strptime(user_info['dob'], '%Y-%m-%d').date()
        dob = st.date_input("Date of Birth", value=dob_val)
        
        gender_options = ["Male", "Female", "Other", "Prefer not to say"]
        gender = st.selectbox("Gender", gender_options, index=gender_options.index(user_info['gender']))
        
        height_cm = st.number_input("Height (cm)", value=float(user_info['height_cm']))
        city = st.text_input("City", value=user_info['city'])
        state = st.text_input("State", value=user_info['location_state'])
        
        pref_options = ["Vegetarian", "Vegetarian + Non-Veg"]
        food_preference = st.radio("Food Preference", pref_options, index=pref_options.index(user_info['food_preference']))
        
        goal_options = ["Weight Loss", "Weight Gain", "Maintain Weight", "Improve Fitness", "Manage Stress"]
        health_goal = st.selectbox("Primary Health Goal", goal_options, index=goal_options.index(user_info['health_goal']))

        exercise_options = ["Yoga", "Home Workouts", "Gym", "Sports", "Zumba", "Running/Jogging", "None"]
        preferred_exercise = st.multiselect("Preferred Daily Exercise", exercise_options, default=json.loads(user_info.get('preferred_exercise', '[]')))

        submitted = st.form_submit_button("Save Changes")
        if submitted:
            updated_data = {
                'name': name, 'dob': str(dob), 'height_cm': height_cm, 'gender': gender,
                'location_state': state, 'city': city, 'food_preference': food_preference,
                'health_goal': health_goal, 'preferred_exercise': preferred_exercise
            }
            db.update_user_profile(user_info['user_id'], updated_data)
            st.session_state.user_info = dict(db.get_user(user_info['user_id']))
            st.success("Profile updated successfully!")
            st.rerun()

st.markdown("---")
st.subheader("📄 Your Generated Reports")
st.write("Download your past daily reports here.")
reports = [f for f in os.listdir("generated_reports") if f.startswith(f"report_{user_info['user_id']}_") and f.endswith(".pdf")]
if not reports:
    st.info("No reports generated yet. Submit a daily log to create your first report!")
else:
    for report_file in sorted(reports, reverse=True):
        file_path = os.path.join("generated_reports", report_file)
        with open(file_path, "rb") as f:
            st.download_button(
                label=f"Download Report for {report_file.split('_')[-1].replace('.pdf','')}",
                data=f,
                file_name=report_file,
                mime="application/pdf"
            )
