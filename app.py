import streamlit as st
from datetime import datetime
import database as db
import ai_utils
import report_generator
import os
from PIL import Image

# --- CONFIG & INITIALIZATION ---
st.set_page_config(page_title="Aarogyam AI", page_icon="🌿", layout="wide")
db.create_tables()
UPLOAD_DIR = "uploads"
os.makedirs(os.path.join(UPLOAD_DIR, "food"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "profile"), exist_ok=True)

# --- SESSION STATE INITIALIZATION---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_info' not in st.session_state: st.session_state.user_info = None
if 'page' not in st.session_state: st.session_state.page = "Login"
if 'food_entries' not in st.session_state: st.session_state.food_entries = []
if 'exercise_entries' not in st.session_state: st.session_state.exercise_entries = []
if 'report_path' not in st.session_state: st.session_state.report_path = None

# --- HELPER FUNCTIONS ---
def save_uploaded_file(uploaded_file, subdir=""):
    if uploaded_file is not None:
        try:
            img = Image.open(uploaded_file)
            max_size = (512, 512)
            img.thumbnail(max_size)
            timestamp = int(datetime.now().timestamp())
            sanitized_name = "".join(c for c in uploaded_file.name if c.isalnum() or c in ('.', '_')).rstrip()
            filename = f"{st.session_state.user_info['user_id']}_{timestamp}_{sanitized_name}.jpg"
            target_dir = os.path.join(UPLOAD_DIR, subdir)
            file_path = os.path.join(target_dir, filename)
            img.convert("RGB").save(file_path, "JPEG", quality=85)
            return file_path
        except Exception as e:
            st.error(f"Error processing image: {e}")
            return None
    return None

def reset_daily_log_forms():
    st.session_state.food_entries = []
    st.session_state.exercise_entries = []
    st.session_state.report_path = None

# --- AUTHENTICATION & ONBOARDING PAGES ---
def signup_page():
    st.title("Join Aarogyam AI 🌱")
    if 'signup_success' not in st.session_state: st.session_state.signup_success = False

    if st.session_state.signup_success:
        st.success("Your profile has been created successfully!")
        st.balloons()
        st.info(f"🎉 Your unique 5-digit Login ID is: **{st.session_state.new_user_id}**. Please save it securely.")
        if st.button("Proceed to Login"):
            st.session_state.page = "Login"; st.session_state.signup_success = False; st.rerun()
        return

    st.write("Let's get to know you better to create your wellness profile.")
    with st.form("signup_form"):
        st.subheader("Personal Information")
        name = st.text_input("Full Name *")
        dob = st.date_input("Date of Birth *", min_value=datetime(1920, 1, 1), max_value=datetime.now())
        gender = st.selectbox("Gender *", ["Male", "Female", "Other", "Prefer not to say"])
        
        col1, col2 = st.columns(2)
        with col1:
            height_unit = st.radio("Height Unit", ["cm", "inches"]); height = st.number_input("Height *", 1.0)
            location_state = st.text_input("Location (State) *", help="e.g., Maharashtra"); city = st.text_input("City *", help="e.g., Mumbai")
        with col2:
            current_weight = st.number_input("Current Weight (kg) *", 1.0)
            food_preference = st.radio("Food Preference *", ["Vegetarian", "Vegetarian + Non-Veg"])
            health_goal = st.selectbox("Primary Health Goal *", ["Weight Loss", "Weight Gain", "Maintain Weight", "Improve Fitness", "Manage Stress"])
        
        st.subheader("Wellness Profile")
        exercise_options = ["Yoga", "Home Workouts", "Gym", "Sports", "Zumba", "Running/Jogging", "None"]
        preferred_exercise = st.multiselect("Preferred Daily Exercise", exercise_options)
        
        st.info("Please enter 'NA' if a field is not applicable for the optional fields below.")
        medical_conditions = st.text_area("Existing Medical Conditions"); medications = st.text_area("Current Medications & Dosage")
        allergies = st.text_input("Allergies"); surgical_history = st.text_area("Surgical History")
        family_history = st.text_area("Family Medical History")
        
        submitted = st.form_submit_button("Create My Profile")
        if submitted:
            if not all([name, dob, gender, height, location_state, city, current_weight, health_goal, food_preference]):
                st.error("Please fill in all the required fields marked with *.")
            else:
                height_cm = height if height_unit == "cm" else height * 2.54
                user_data = { 'name': name, 'dob': str(dob), 'height_cm': height_cm, 'gender': gender, 'location_state': location_state, 'city': city, 'food_preference': food_preference, 'health_goal': health_goal, 'preferred_exercise': preferred_exercise, 'medical_conditions': medical_conditions or 'NA', 'medications': medications or 'NA', 'allergies': allergies or 'NA', 'surgical_history': surgical_history or 'NA', 'family_history': family_history or 'NA' }
                user_id = db.add_user(user_data)
                st.session_state.signup_success = True; st.session_state.new_user_id = user_id; st.rerun()

    if st.button("Back to Login"):
        st.session_state.page = "Login"; st.session_state.signup_success = False; st.rerun()

def login_page():
    st.title("Welcome back to Aarogyam AI 🌿")
    with st.form("login_form"):
        user_id_input = st.text_input("Enter your 5-digit User ID")
        submitted = st.form_submit_button("Login")
        if submitted:
            try:
                user_id = int(user_id_input)
                user = db.get_user(user_id)
                if user:
                    st.session_state.logged_in = True; st.session_state.user_info = dict(user); st.rerun()
                else: st.error("Invalid User ID. Please try again or sign up.")
            except (ValueError, TypeError): st.error("Please enter a valid 5-digit number for the User ID.")
    if st.button("New User? Sign Up Here"):
        st.session_state.page = "Sign Up"; st.rerun()

def main_app():
    st.sidebar.title(f"Welcome, {st.session_state.user_info['name'].split()[0]}!")
    st.sidebar.write(f"User ID: {st.session_state.user_info['user_id']}")
    st.sidebar.markdown("---")

    if st.session_state.report_path:
        st.title("✅ Daily Log Submitted")
        st.success("Your wellness report has been generated successfully!")
        with open(st.session_state.report_path, "rb") as file:
            st.download_button(label="Download Your Daily Report (PDF)", data=file, file_name=os.path.basename(st.session_state.report_path), mime="application/pdf")
        if st.button("Log Another Day"):
            reset_daily_log_forms(); st.rerun()
        return

    st.title("📅 Your Daily Log")
    log_date = st.date_input("Select the date you want to log:", datetime.now(), max_value=datetime.now(), format="YYYY-MM-DD")
    
    st.subheader("🥗 Food Diary")
    for i, food in enumerate(st.session_state.food_entries):
        st.markdown(f"**Meal #{i+1}**")
        cols = st.columns([2, 3, 4, 1])
        food['meal_type'] = cols[0].selectbox("Meal Type", ["Breakfast", "Lunch", "Dinner", "Snack"], key=f"food_type_{i}")
        food['image'] = cols[1].file_uploader("Upload photo", type=['jpg', 'png', 'jpeg'], key=f"food_img_{i}")
        food['description'] = cols[2].text_area("What did you eat?", key=f"food_desc_{i}")
        if cols[3].button(f"🗑️", key=f"del_food_{i}", help="Delete this meal entry"):
            st.session_state.food_entries.pop(i); st.rerun()
    if st.button("➕ Add Another Meal"):
        st.session_state.food_entries.append({'meal_type': "Snack", 'image': None, 'description': ""}); st.rerun()
    st.markdown("---")

    st.subheader("🏋️‍♀️ Exercise Diary")
    for i, ex in enumerate(st.session_state.exercise_entries):
        st.markdown(f"**Exercise #{i+1}**")
        cols = st.columns([2, 4, 2, 1])
        options = ["Gym", "Yoga", "Sports", "Home Workout", "Running", "Cycling", "Other"]
        choice = cols[0].selectbox("Type", options, key=f"ex_type_{i}")
        if choice == "Other": ex['exercise_type'] = cols[0].text_input("Specify", key=f"ex_other_{i}") or "Other"
        else: ex['exercise_type'] = choice
        ex['details'] = cols[1].text_input("Details (e.g., Bench Press, 3 sets)", key=f"ex_details_{i}")
        ex['duration_minutes'] = cols[2].number_input("Duration (min)", 0, 300, 30, key=f"ex_dura_{i}")
        if cols[3].button(f"🗑️", key=f"del_ex_{i}", help="Delete this exercise entry"):
            st.session_state.exercise_entries.pop(i); st.rerun()
    if st.button("➕ Add Another Exercise"):
        st.session_state.exercise_entries.append({'exercise_type': "Gym", 'details': "", 'duration_minutes': 30}); st.rerun()
    st.markdown("---")

    with st.form("daily_log_static_form"):
        st.subheader("📝 Other Daily Metrics")
        col1, col2 = st.columns(2)
        with col1:
            sleep_hours = st.number_input("Hours of sleep", 0.0, 24.0, 7.5, 0.5); steps = st.number_input("Step Count", 0, 50000, 5000, 100)
            mood = st.select_slider("Your Mood", ["😭 Awful", "😞 Sad", "😟 Anxious", "😐 Neutral", "😊 Okay", "🙂 Happy", "😁 Great", "🤩 Ecstatic"], value="😊 Okay")
            stress_level = st.radio("Stress Level", ["Low", "Mild", "High"], horizontal=True)
        with col2:
            weight = st.number_input("Weight (kg)", 0.0, 300.0, 70.0, 0.1); water_liters = st.number_input("Water (Liters)", 0.0, 10.0, 2.0, 0.25)
            task_completion = st.radio("Tasks Completed", ["None", "A Few", "Majority", "All"], horizontal=True)
            focus_level = st.radio("Focus Level", ["Low", "Medium", "High"], horizontal=True)
        
        with st.expander("✈️ Log Your Travel (Optional)"):
            km_traveled = st.number_input("Kilometers traveled", 0, 10000); transport_mode = st.selectbox("Mode of transport", ["None", "Car", "Bike", "Bus", "Train", "Flight"])
            city_changed = st.checkbox("Did you change your city today?")
            new_city, new_state = (st.text_input("New City"), st.text_input("New State")) if city_changed else (None, None)
        
        st.subheader("📸 Check-ins")
        selfie = st.file_uploader("Upload a selfie for comparative analysis"); posture_pic = st.file_uploader("Upload a side-profile posture photo")

        submitted = st.form_submit_button("Log My Day & Generate Final Report")

    if submitted:
        with st.spinner("Processing images and performing AI analysis... This may take a moment."):
            try:
                if city_changed and new_city and new_state:
                    db.update_user_location(st.session_state.user_info['user_id'], new_city, new_state)
                    st.session_state.user_info = dict(db.get_user(st.session_state.user_info['user_id']))

                selfie_path = save_uploaded_file(selfie, "profile")
                posture_pic_path = save_uploaded_file(posture_pic, "profile")
                food_entries_data = [{'meal_type': f['meal_type'], 'food_image_path': save_uploaded_file(f['image'], "food"), 'description': f['description']} for f in st.session_state.food_entries]
                travel_data = {'km': km_traveled, 'mode': transport_mode, 'location_changed': city_changed, 'new_city': new_city, 'new_state': new_state}
                log_data_payload = { 'user_id': st.session_state.user_info['user_id'], 'log_date': log_date.strftime('%Y-%m-%d'), 'total_sleep_minutes': int(sleep_hours * 60), 'steps': steps, 'mood': mood, 'weight_kg': weight, 'selfie_path': selfie_path, 'posture_pic_path': posture_pic_path, 'travel_info': travel_data, 'hydration_level': water_liters, 'stress_level': stress_level, 'menstrual_cycle_day': None, 'task_completion': task_completion, 'focus_level': focus_level, 'food_entries': food_entries_data, 'exercise_entries': st.session_state.exercise_entries }
                
                log_id = db.add_daily_log(log_data_payload)
                full_log_data = db.get_full_daily_log(log_id)
                prev_day_images = db.get_previous_day_image_paths(st.session_state.user_info['user_id'], log_date.strftime('%Y-%m-%d'))
                
                full_analysis = ai_utils.generate_comprehensive_daily_analysis(st.session_state.user_info, full_log_data, prev_day_images)
                
                recommendations = "Could not be generated due to a prior error."
                if "error" not in full_analysis:
                    lacking_nutrient = full_analysis.get("nutrition_analysis", {}).get("final_summary", {}).get("lacking_nutrient", "")
                    recommendations = ai_utils.get_rag_recommendations(st.session_state.user_info, lacking_nutrient)

                report_path = report_generator.generate_daily_report(st.session_state.user_info, full_log_data, full_analysis, recommendations)
                
                if report_path:
                    st.session_state.report_path = report_path
                    st.rerun()
                else:
                    st.error("Failed to generate and save the report. Please check the terminal for a critical error message.")

            except Exception as e:
                st.error("A critical error occurred. Check the terminal for details.")
                st.exception(e)

    if st.sidebar.button("Logout"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

if not st.session_state.logged_in:
    if st.session_state.page == "Sign Up":
        signup_page()
    else:
        login_page()
else:
    main_app()