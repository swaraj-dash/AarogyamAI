import streamlit as st
import google.generativeai as genai
from google.api_core.client_options import ClientOptions
import os
import pandas as pd
from PIL import Image
import json
import requests
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# --- MODEL CONFIGURATION ---
MASTER_ANALYSIS_MODEL_NAME = "gemini-1.5-flash-latest" 
TEXT_MODEL_NAME = "gemini-1.5-flash-latest"

# This configuration works both locally and on Streamlit Cloud
api_key=st.secrets.get("GOOGLE_API_KEY")
if api_key:
    genai.configure(
        api_key=api_key,
        transport="rest",
        client_options=ClientOptions(
            api_endpoint=os.getenv("GOOGLE_API_ENDPOINT"),
        ),
    )

def get_master_model():
    return genai.GenerativeModel(MASTER_ANALYSIS_MODEL_NAME)

def get_text_model():
    return genai.GenerativeModel(TEXT_MODEL_NAME)

@st.cache_data
def load_nutrient_data():
    """Loads the nutrient CSV into a pandas DataFrame."""
    try:
        df = pd.read_csv("rag_data/india_state_meal_nutrient_recs.csv")
        df.columns = df.columns.str.lower().str.strip()
        return df
    except FileNotFoundError:
        # This will show an error on the Streamlit app if the file is missing
        st.error("RAG data file not found. Please make sure 'rag_data/india_state_meal_nutrient_recs.csv' exists in your GitHub repository.")
        return None

def generate_comprehensive_daily_analysis(user_profile, log_data, prev_day_images):
    master_model = get_master_model()
    
    prompt_parts = [
        "You are a world-class holistic wellness AI. Your task is to analyze a user's complete daily log and generate a structured JSON output.",
        f"\n**User Profile:**\n- Health Goal: {user_profile['health_goal']}\n- Food Preference: {user_profile['food_preference']}\n",
        f"\n**User's Daily Log Data:**\n- Sleep: {log_data['log_details']['total_sleep_minutes']} minutes\n- Steps: {log_data['log_details']['steps']}\n- Mood: {log_data['log_details']['mood']}\n- Stress: {log_data['log_details']['stress_level']}\n- Focus: {log_data['log_details']['focus_level']}\n- Task Completion: {log_data['log_details']['task_completion']}\n"
    ]

    has_today_selfie = log_data['log_details'].get('selfie_path') and os.path.exists(log_data['log_details']['selfie_path'])
    has_yesterday_selfie = prev_day_images and prev_day_images.get('selfie_path') and os.path.exists(prev_day_images['selfie_path'])
    has_today_posture = log_data['log_details'].get('posture_pic_path') and os.path.exists(log_data['log_details']['posture_pic_path'])
    has_yesterday_posture = prev_day_images and prev_day_images.get('posture_pic_path') and os.path.exists(prev_day_images['posture_pic_path'])

    prompt_parts.append("\n**IMAGES FOR ANALYSIS:**")
    if has_today_selfie:
        try: prompt_parts.extend(["\nToday's Selfie:", Image.open(log_data['log_details']['selfie_path'])])
        except Exception: pass
    if has_yesterday_selfie:
        try: prompt_parts.extend(["Yesterday's Selfie:", Image.open(prev_day_images['selfie_path'])])
        except Exception: pass
    if has_today_posture:
        try: prompt_parts.extend(["Today's Posture Photo:", Image.open(log_data['log_details']['posture_pic_path'])])
        except Exception: pass
    if has_yesterday_posture:
        try: prompt_parts.extend(["Yesterday's Posture Photo:", Image.open(prev_day_images['posture_pic_path'])])
        except Exception: pass

    prompt_parts.append("\n**MEALS FOR ANALYSIS:**")
    for i, food in enumerate(log_data['food_entries']):
        prompt_parts.append(f"\n- MEAL #{i+1}: {food['meal_type']} (User's Note: {food['description']})")
        if food['food_image_path'] and os.path.exists(food['food_image_path']):
            try: prompt_parts.append(Image.open(food['food_image_path']))
            except Exception: pass
    
    selfie_comp_instruction = "State that a comparison could not be made."
    if has_today_selfie and has_yesterday_selfie: selfie_comp_instruction = "Analyze the selfie comparison for facial features like skin clarity and tiredness."
    elif has_today_selfie and not has_yesterday_selfie: selfie_comp_instruction = "State that yesterday's selfie was not provided for a comparison."
    elif not has_today_selfie: selfie_comp_instruction = "State that a selfie was not provided today for analysis."

    posture_comp_instruction = "State that a comparison could not be made."
    if has_today_posture and has_yesterday_posture: posture_comp_instruction = "Analyze the posture comparison for slouching or improvements."
    elif has_today_posture and not has_yesterday_posture: posture_comp_instruction = "State that yesterday's posture photo was not provided for a comparison."
    elif not has_today_posture: posture_comp_instruction = "State that a posture photo was not provided today for analysis."

    prompt_parts.append(f"""
        **FINAL TASK: Generate a single JSON object with the exact structure below.**
        - Be conservative and realistic with nutritional estimates based on standard Indian portions.
        - All summaries must be concise (1-2 sentences).
        - Positives/Improvements lists must have max 3 points.
        {{
          "wellness_score": {{"score": "A score from 1-100 summarizing the day's overall wellness.", "justification": "A brief explanation for the score."}},
          "physical_activity_analysis": "A one-sentence encouraging comment on the user's steps and exercise.",
          "mental_clarity_analysis": "An empathetic summary of the user's mood, stress, focus, and sleep.",
          "daily_image_analysis": {{
            "selfie_analysis": "{'Provide a brief, one-sentence analysis of the selfie for today.' if has_today_selfie else 'Not available.'}",
            "posture_analysis": "{'Provide a brief, one-sentence analysis of the posture photo for today.' if has_today_posture else 'Not available.'}"
          }},
          "comparative_analysis": {{
            "selfie_feedback": "{selfie_comp_instruction}",
            "posture_feedback": "{posture_comp_instruction}"
          }},
          "nutrition_analysis": {{
            "meal_analyses": [
              {{
                "meal_type": "Breakfast",
                "nutrition_table": [
                  {{"component": "Item Name", "calories": 150, "protein_g": 5, "carbs_g": 25, "fats_g": 5, "vitamins_minerals": "Key nutrients like Iron, Vitamin C"}}
                ]
              }}
            ],
            "final_summary": {{
              "summary": "A professional summary of the entire day's diet (max 2 sentences).",
              "positives": "A list of max 3 positive points.",
              "improvements": "A list of max 3 actionable improvement points.",
              "lacking_nutrient": "The single most lacking nutrient from this list: [Protein, Fiber, Iron, Calcium, Vitamins, Healthy Fats]."
            }}
          }}
        }}
    """)
    
    try:
        response = get_master_model().generate_content(prompt_parts, request_options={"timeout": 120})
        json_text = response.text.strip().replace("```json", "").replace("```", "")
        full_analysis = json.loads(json_text)
    except Exception as e:
        print(f"MASTER AI CALL FAILED: {e}")
        return {"error": f"The main AI analysis failed. Error: {e}"}
    return full_analysis

def get_rag_recommendations(user_profile, lacking_nutrient):
    if not lacking_nutrient:
        return "No specific nutrient deficiency was identified today, great job!"

    text_model = get_text_model()
    recommendations = ""
    
    try:
        general_prompt = f"Provide a short, bulleted list of general food sources for a person lacking in {lacking_nutrient}. The user's food preference is {user_profile['food_preference']}, so only suggest suitable items."
        recommendations = "General Recommendations:\n" + text_model.generate_content(general_prompt).text + "\n\n"

        # --- DEPLOYMENT CHECK ---
        # This check disables the local-only feature when deployed to the cloud.
        if 'STREAMLIT_SERVER_RUNNING_ON_CLOUD' in os.environ:
            recommendations += "State-Specific Recommendations:\n(This feature uses a local AI model and is available when running the app on a personal computer.)"
            return recommendations

        # --- If running locally, proceed with Ollama RAG ---
        state = user_profile['location_state']
        preference = 'Veg' if user_profile['food_preference'] == 'Vegetarian' else 'Non-Veg'
        
        df = load_nutrient_data()
        if df is None:
            raise FileNotFoundError("Nutrient data CSV could not be loaded.")

        results = df[
            (df['state'].str.lower() == state.lower()) &
            (df['preference'].str.contains(preference, case=False, na=False)) &
            (
                (df['primary nutrient'].str.lower() == lacking_nutrient.lower()) |
                (df['secondary nutrient'].str.lower() == lacking_nutrient.lower()) |
                (df['tertiary nutrient'].str.lower() == lacking_nutrient.lower()) |
                (df['quaternary nutrient'].str.lower() == lacking_nutrient.lower())
            )
        ]
        retrieved_dishes = results[['dish name', 'meal type', 'description']].head(3)

        if retrieved_dishes.empty:
            return recommendations + f"State-Specific Recommendations:\nNo specific {lacking_nutrient}-rich dishes found for {state} in the database."

        ollama_llm = Ollama(model="llama3")
        
        prompt_template = PromptTemplate(
            input_variables=["state", "nutrient", "retrieved_data"],
            template="""
You are a helpful nutrition assistant. A user from {state} is looking for dishes rich in {nutrient}.
Based on the following data, please provide a friendly recommendation for 1-2 dishes. For each dish, briefly explain why it's a good choice based on the provided description.

Retrieved dishes:
{retrieved_data}

Your response:
"""
        )
        chain = LLMChain(llm=ollama_llm, prompt=prompt_template)
        response = chain.run(state=state, nutrient=lacking_nutrient, retrieved_data=retrieved_dishes.to_string(index=False))
        recommendations += "State-Specific Recommendations:\n" + response

    except Exception as e:
        print(f"RAG CHAIN FAILED: {e}")
        error_message = f"Could not generate state-specific recommendations. The local AI server may not be running. Error: {e}"
        recommendations += f"\n{error_message}"
        
    return recommendations