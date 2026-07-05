import os
import pandas as pd
import google.generativeai as genai
import config
from services import ai_engine

def load_nutrient_data():
    """Loads the nutrient CSV into a pandas DataFrame."""
    try:
        df = pd.read_csv("rag_data/india_state_meal_nutrient_recs.csv")
        df.columns = df.columns.str.lower().str.strip()
        return df
    except FileNotFoundError:
        print("WARNING: rag_data/india_state_meal_nutrient_recs.csv not found.")
        return None

def get_rag_recommendations(user_profile, lacking_nutrient):
    """Retrieves state-specific Indian dishes rich in the lacking nutrient and uses Gemini to suggest them."""
    if not lacking_nutrient:
        return "No specific nutrient deficiency was identified today, great job!"

    text_model = ai_engine.get_text_model()
    
    # 1. Generate general recommendations
    try:
        general_prompt = (
            f"Provide a short, bulleted list of general food sources for a person lacking in {lacking_nutrient}. "
            f"The user's food preference is {user_profile['food_preference']}, so only suggest suitable items."
        )
        general_recommendations = "General Recommendations:\n" + text_model.generate_content(general_prompt).text + "\n\n"
    except Exception as e:
        print(f"General recommendations failed: {e}")
        general_recommendations = f"General Recommendations: (Failed to generate: {e})\n\n"

    # 2. Retrieve state-specific meals from CSV
    state = user_profile.get('location_state', 'Maharashtra')
    preference = 'Veg' if user_profile.get('food_preference') == 'Vegetarian' else 'Non-Veg'
    
    df = load_nutrient_data()
    if df is None:
        return general_recommendations + "State-Specific Recommendations:\n(Nutrient database not available to generate regional recommendations.)"

    try:
        # Filter data
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
            # Try relaxing state filter just to match dishes from any state
            results_any_state = df[
                (df['preference'].str.contains(preference, case=False, na=False)) &
                (
                    (df['primary nutrient'].str.lower() == lacking_nutrient.lower()) |
                    (df['secondary nutrient'].str.lower() == lacking_nutrient.lower()) |
                    (df['tertiary nutrient'].str.lower() == lacking_nutrient.lower()) |
                    (df['quaternary nutrient'].str.lower() == lacking_nutrient.lower())
                )
            ]
            retrieved_dishes = results_any_state[['dish name', 'meal type', 'description']].head(3)
            
            if retrieved_dishes.empty:
                return general_recommendations + f"State-Specific Recommendations:\nNo Indian dishes rich in {lacking_nutrient} found in our database."

        # Generate recommendation using Gemini instead of Ollama for production compatibility
        prompt = f"""
        You are a helpful nutrition assistant. A user from {state} is looking for dishes rich in {lacking_nutrient}.
        Based on the following retrieved Indian dishes, please provide a friendly recommendation for 1-2 dishes.
        For each dish, briefly explain why it's a good choice based on the description and nutrient content.
        
        Retrieved dishes:
        {retrieved_dishes.to_string(index=False)}
        
        Provide a concise response.
        """
        response = text_model.generate_content(prompt)
        return general_recommendations + "Regional Recommendations:\n" + response.text
    except Exception as e:
        print(f"RAG recommendation generation failed: {e}")
        return general_recommendations + f"Regional Recommendations:\nCould not generate state-specific advice. (Error: {e})"
