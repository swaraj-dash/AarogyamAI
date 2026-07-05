from services import ai_engine, rag_engine

def get_master_model():
    return ai_engine.get_model()

def get_text_model():
    return ai_engine.get_text_model()

def get_vision_model():
    return ai_engine.get_vision_model()

def get_fitness_plan(user_profile):
    return ai_engine.get_fitness_plan(user_profile)

def get_environment_wellness_agent():
    return ai_engine.get_environment_wellness_agent()

def load_nutrient_data():
    return rag_engine.load_nutrient_data()

def generate_comprehensive_daily_analysis(user_profile, log_data, prev_day_images):
    return ai_engine.generate_comprehensive_daily_analysis(user_profile, log_data, prev_day_images)

def get_rag_recommendations(user_profile, lacking_nutrient):
    return rag_engine.get_rag_recommendations(user_profile, lacking_nutrient)