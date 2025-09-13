# pages/4_🌿_Shuddh_Vikalp.py

import streamlit as st
import ai_utils
from PIL import Image

st.set_page_config(page_title="Shuddh Vikalp", page_icon="🌿")
st.title("🌿 Shuddh Vikalp")
st.write("Find healthier, eco-friendly alternatives for your everyday items.")

if 'user_info' not in st.session_state or not st.session_state.user_info:
    st.error("Please log in from the main page to use this feature.")
    st.stop()

st.info("Upload a picture of an item (like a plastic bottle, a cleaning product, etc.) or just ask me for alternatives.")

# Initialize the agent
try:
    agent = ai_utils.get_environment_wellness_agent()
except Exception as e:
    st.error(f"Could not initialize the web search agent. Is your Tavily API key set in secrets.toml? Error: {e}")
    st.stop()


uploaded_image = st.file_uploader("Upload an item's image", type=["jpg", "png", "jpeg"])
item_description = st.text_input("Or describe the item you want an alternative for (e.g., 'plastic toothbrush')")

if st.button("Find Better Alternatives"):
    if not uploaded_image and not item_description:
        st.warning("Please upload an image or describe an item.")
    else:
        with st.spinner("Searching the web for sustainable alternatives..."):
            query = ""
            if item_description:
                query = f"Find healthy and eco-friendly alternatives for a {item_description}. Provide 2-3 options with brief descriptions and why they are better. If possible, provide links to buy them in India."
            
            # Note: LangChain agent with vision tools is more complex.
            # Here we simplify by describing the image to the text-based agent if one is uploaded.
            elif uploaded_image:
                st.image(uploaded_image)
                image = Image.open(uploaded_image)
                vision_model = ai_utils.get_vision_model()
                image_desc_response = vision_model.generate_content(["Describe the main object in this image in a few words.", image])
                image_desc = image_desc_response.text
                st.write(f"Detected item: **{image_desc.strip()}**")
                query = f"Find healthy and eco-friendly alternatives for a {image_desc}. Provide 2-3 options with brief descriptions and why they are better. If possible, search for links to buy them in India."

            try:
                # Run the agent
                response = agent.run(query)
                st.success("Here are some alternatives I found:")
                st.markdown(response)
            except Exception as e:
                st.error(f"An error occurred while running the agent: {e}")