import streamlit as st
from PIL import Image
import ai_utils
import google.generativeai as genai

st.set_page_config(page_title="Sehat Darpan", page_icon="🩺")
st.title("🩺 Sehat Darpan (AI-Powered)")

if 'user_info' not in st.session_state or not st.session_state.user_info:
    st.error("Please log in from the main page to use this feature.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["🔬 Analyze Skin/Wound Image", "💊 Analyze Prescription", "💬 Chat with Assistant"])

with tab1:
    st.header("Skin or Wound Image Analysis")
    st.write("Upload a clear picture of a skin condition, mole, or minor wound.")
    uploaded_image = st.file_uploader("Choose an image...", type=["jpg", "png", "jpeg"], key="skin_image")
    st.error("**Disclaimer:** This is an AI-powered tool and NOT a substitute for professional medical advice. Always consult a qualified doctor.")
    if uploaded_image:
        image = Image.open(uploaded_image)
        st.image(image, caption="Uploaded Image", use_column_width=True)
        if st.button("Analyze Image"):
            with st.spinner("AI is analyzing..."):
                vision_model = ai_utils.get_vision_model()
                prompt = """Analyze the image of a skin condition. Describe visual characteristics (color, shape, texture) neutrally. List possible general categories (e.g., 'Inflammatory reaction'). Provide safe, general first-aid advice (e.g., 'Keep clean'). Conclude with a strong disclaimer to consult a healthcare professional for a diagnosis."""
                response = vision_model.generate_content([prompt, image])
                st.success("Analysis Complete"); st.markdown(response.text)

with tab2:
    st.header("Prescription Analysis")
    st.write("Upload a clear image of a doctor's prescription.")
    uploaded_prescription = st.file_uploader("Choose an image...", type=["jpg", "png", "jpeg"], key="prescription_image")
    if uploaded_prescription:
        image = Image.open(uploaded_prescription)
        st.image(image, caption="Uploaded Prescription", use_column_width=True)
        if st.button("Analyze Prescription"):
            with st.spinner("AI is reading..."):
                vision_model = ai_utils.get_vision_model()
                prompt = """Extract medicine names, dosages, frequencies, and duration from the prescription. Summarize any other instructions. If any part is unclear, state that it is illegible. Conclude by advising the user to confirm with their doctor or pharmacist."""
                response = vision_model.generate_content([prompt, image])
                st.success("Analysis Complete"); st.markdown(response.text)

with tab3:
    st.header("Chat with your AI Health Assistant")
    st.info("You can ask general health and wellness questions. This is not a doctor.")
    
    try:
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
        if "sehat_chat" not in st.session_state:
            st.session_state.sehat_chat = model.start_chat(history=[
                {"role": "user", "parts": ["You are a helpful and cautious AI health assistant. Your name is Sehat Darpan. You provide general health information but you MUST always remind the user that you are not a doctor and they should consult a professional for medical advice. Start the conversation by introducing yourself."]},
                {"role": "model", "parts": ["Hello! I am Sehat Darpan, your AI health assistant. I can provide general information on wellness topics. Please remember, I am not a substitute for a real doctor. How can I help you today?"]}
            ])
    except Exception as e:
        st.error(f"Failed to initialize chat: {e}"); st.stop()

    for message in st.session_state.sehat_chat.history:
        role = "assistant" if message.role == "model" else message.role
        with st.chat_message(role):
            st.markdown(message.parts[0].text)

    if prompt := st.chat_input("Ask a health question..."):
        with st.chat_message("user"): st.markdown(prompt)
        with st.spinner("Thinking..."):
            response = st.session_state.sehat_chat.send_message(prompt)
            with st.chat_message("assistant"): st.markdown(response.text)
