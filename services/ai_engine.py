import os
import json
from PIL import Image
import io
import google.generativeai as genai
from google.api_core.client_options import ClientOptions
import config

# Configure the Gemini API
if config.GOOGLE_API_KEY:
    genai.configure(api_key=config.GOOGLE_API_KEY)

MODEL_NAME = "gemini-2.0-flash"

def get_model(name=MODEL_NAME):
    return genai.GenerativeModel(name)

def get_text_model():
    return get_model()

def get_vision_model():
    return get_model()

class SearchAgentWrapper:
    """Wrapper that mimics a LangChain search agent for Shuddh Vikalp."""
    def run(self, query: str) -> str:
        # Enable search grounding if Tavily isn't available, or use Gemini's built-in search capabilities!
        # Gemini 2.0 Flash supports search grounding natively.
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            tools=[{"google_search": {}}]  # Enable Google Search grounding
        )
        try:
            response = model.generate_content(query)
            # Check if there are grounding metadata sources
            sources = []
            metadata = response.candidates[0].grounding_metadata if response.candidates else None
            if metadata and metadata.grounding_chunks:
                for chunk in metadata.grounding_chunks:
                    if chunk.web:
                        sources.append(f"- [{chunk.web.title}]({chunk.web.uri})")
            
            answer = response.text
            if sources:
                answer += "\n\n**Sources:**\n" + "\n".join(set(sources))
            return answer
        except Exception as e:
            # Fallback to normal text generation if search grounding fails
            print(f"Grounding search failed, falling back to standard generation: {e}")
            fallback_model = get_model()
            response = fallback_model.generate_content(query)
            return response.text

def get_environment_wellness_agent():
    return SearchAgentWrapper()

def get_fitness_plan(user_profile):
    """Generates a structured daily workout plan based on user goals and preferences."""
    model = get_model()
    
    prompt = f"""
    You are an expert fitness coach. Generate a personalized daily workout plan for a user with the following profile:
    - Primary Health Goal: {user_profile.get('health_goal')}
    - Preferred Daily Exercises: {user_profile.get('preferred_exercise')}
    - Existing Medical Conditions: {user_profile.get('medical_conditions', 'None')}
    - Gender: {user_profile.get('gender')}
    
    Provide the response as a valid JSON array of objects. Each object must have exactly two fields:
    1. "activity": A string describing the exercise name and instruction (e.g. "Warm-up: Dynamic stretches", "Walking on Treadmill").
    2. "duration_or_sets": A string describing the duration or sets/reps (e.g. "10 minutes", "3 sets of 12 reps").
    
    Return ONLY the raw JSON array. Do not include markdown code block formatting (like ```json).
    """
    
    try:
        response = model.generate_content(prompt)
        content = response.text.strip()
        # Clean any markdown if the model included it
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        print(f"Failed to generate fitness plan: {e}")
        # Return a safe fallback workout plan
        return [
            {"activity": "Warm-up: Light stretching & joint rotation", "duration_or_sets": "5-10 minutes"},
            {"activity": "Brisk walking or light jogging", "duration_or_sets": "20-30 minutes"},
            {"activity": "Bodyweight Squats", "duration_or_sets": "3 sets of 10 reps"},
            {"activity": "Push-ups (knee push-ups if needed)", "duration_or_sets": "3 sets of 8 reps"},
            {"activity": "Plank hold", "duration_or_sets": "3 sets of 30 seconds"},
            {"activity": "Cool-down: Full-body static stretches", "duration_or_sets": "5 minutes"}
        ]

def generate_comprehensive_daily_analysis(user_profile, log_data, prev_day_images):
    """Analyzes user daily log, food photos, selfie, posture, and returns structured analysis."""
    master_model = get_model()
    
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
        
        Response JSON format:
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
        
        Return ONLY the raw JSON string. Do not wrap in markdown tags.
    """)
    
    try:
        response = master_model.generate_content(prompt_parts)
        content = response.text.strip()
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        print(f"MASTER AI CALL FAILED: {e}")
        return {"error": f"The main AI analysis failed. Error: {e}"}
