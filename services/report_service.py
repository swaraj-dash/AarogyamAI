import os
import report_generator

def generate_daily_report(user_profile, log_data, full_analysis, recommendations):
    """Generates the daily PDF report and returns the absolute path to it."""
    # Ensure generated_reports directory exists
    os.makedirs("generated_reports", exist_ok=True)
    return report_generator.generate_daily_report(user_profile, log_data, full_analysis, recommendations)
