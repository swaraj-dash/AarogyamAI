import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

import database as db

st.set_page_config(page_title="Profile · AarogyamAI", page_icon="👤")

if "user_id" not in st.session_state:
    st.warning("Please log in from the main page first.")
    st.stop()

user_id = st.session_state["user_id"]
user = db.get_user(user_id)
st.title("Your profile")

st.write(f"**Name:** {user['name']}")
st.write(f"**Location:** {user['city']}, {user['location_state']}")
st.write(f"**Height:** {user['height_cm']} cm")

st.divider()
st.subheader("Update editable fields")

with st.form("profile_form"):
    goal = st.text_input("Health goal", value=user.get("health_goal", ""))
    diet_options = ["vegetarian", "non-vegetarian", "vegan"]
    current_diet = user.get("food_preference", "vegetarian")
    diet = st.selectbox(
        "Diet preference", diet_options,
        index=diet_options.index(current_diet) if current_diet in diet_options else 0,
    )
    weight = st.number_input("Current weight (kg)", value=float(user.get("current_weight_kg") or 0.0), step=0.1)
    submitted = st.form_submit_button("Save changes", type="primary")
    if submitted:
        db.update_user_field(user_id, "health_goal", goal)
        db.update_user_field(user_id, "food_preference", diet)
        if weight > 0:
            db.update_user_field(user_id, "current_weight_kg", weight)
        st.success("Profile updated.")
        st.rerun()
