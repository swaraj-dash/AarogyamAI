import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Aahar Visheshagya", page_icon="👩‍⚕️")
st.title("👩‍⚕️ Aahar Visheshagya (Nutritionist Coach)")

if 'user_info' not in st.session_state or not st.session_state.user_info:
    st.error("Please log in from the main page to use this feature.")
    st.stop()

user_name = st.session_state.user_info.get("name", "there")

st.info("Welcome! You can ask me anything about food, diet plans, healthy recipes, and nutrition.")

try:
    model = genai.GenerativeModel("gemini-1.5-flash-latest")
    if "nutrition_chat" not in st.session_state:
        st.session_state.nutrition_chat = model.start_chat(history=[
            {"role": "user", "parts": [f"You are an expert, friendly, and certified nutritionist AI named Aahar Visheshagya. Your goal is to help users with their diet and nutrition questions. You should provide clear, actionable advice. Start by introducing yourself to the user, whose name is {user_name}."]},
            {"role": "model", "parts": [f"Namaste, {user_name}! I am Aahar Visheshagya, your personal AI nutritionist. I'm here to help you understand your food better and guide you towards a healthier lifestyle. What's on your mind today?"]}
        ])
except Exception as e:
    st.error(f"Failed to initialize chat: {e}"); st.stop()

# Display chat history
for message in st.session_state.nutrition_chat.history:
    role = "assistant" if message.role == "model" else message.role
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# Chat input
if prompt := st.chat_input("Ask about nutrition..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.spinner("Thinking..."):
        response = st.session_state.nutrition_chat.send_message(prompt)
        with st.chat_message("assistant"):
            st.markdown(response.text)
