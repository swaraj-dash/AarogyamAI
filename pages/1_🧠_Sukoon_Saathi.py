# pages/1_🧠_Sukoon_Saathi.py

import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Sukoon Saathi", page_icon="🧠")

st.title("🧠 Sukoon Saathi")
st.write("Your confidential space to talk, reflect, and feel better.")

# Use session state for user info if logged in
if 'user_info' not in st.session_state or not st.session_state.user_info:
    st.error("Please log in from the main page to use the coach.")
    st.stop()
    
user_name = st.session_state.user_info.get("name", "there")

# Initialize the chat model
try:
    model = genai.GenerativeModel("gemini-1.0-pro")
    if "chat_session" not in st.session_state:
        # Start chat with a persona
        st.session_state.chat_session = model.start_chat(history=[
            {
                "role": "user",
                "parts": [f"Hello, my name is {user_name}. I want you to act as a compassionate and insightful mental wellness coach. Listen to my concerns, ask thoughtful questions, and help me reflect. Be supportive and non-judgmental."]
            },
            {
                "role": "model",
                "parts": [f"Of course, {user_name}. I'm here to listen. This is a safe space for you to share whatever is on your mind. How are you feeling today?"]
            }
        ])
except Exception as e:
    st.error(f"Failed to initialize the chat model. Have you set your API key? Error: {e}")
    st.stop()


# Display chat history
for message in st.session_state.chat_session.history:
    role = "user" if message.role == "user" else "assistant"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# Chat input
if prompt := st.chat_input("What's on your mind?"):
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.spinner("Thinking..."):
        try:
            response = st.session_state.chat_session.send_message(prompt)
            with st.chat_message("assistant"):
                st.markdown(response.text)
        except Exception as e:
            st.error(f"An error occurred: {e}")