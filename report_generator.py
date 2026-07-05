import os
from fpdf import FPDF
from fpdf.errors import FPDFException
from PIL import Image

def sanitize_text(text):
    if not isinstance(text, str):
        text = str(text)
    return text.encode('latin-1', 'replace').decode('latin-1')

class PDF(FPDF):
    def header(self):
        try: self.add_font('DejaVu', 'B', 'assets/DejaVuSans-Bold.ttf', uni=True)
        except RuntimeError: pass
        try: self.add_font('DejaVu', '', 'assets/DejaVuSans.ttf', uni=True)
        except RuntimeError: pass
        try: self.add_font('DejaVu', 'I', 'assets/DejaVuSans-Oblique.ttf', uni=True)
        except RuntimeError: pass
        self.set_fill_color(240, 240, 240); self.rect(0, 0, 210, 10, 'F')
        self.set_font('DejaVu', 'B', 16); self.set_text_color(50, 50, 50)
        self.cell(0, 10, 'Aarogyam AI - Daily Wellness Report', 0, 1, 'C')

    def footer(self):
        self.set_y(-15)
        self.set_font('DejaVu', 'I', 8); self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def section_title(self, title):
        self.ln(5)
        self.set_x(self.l_margin)
        self.set_font('DejaVu', 'B', 14); self.set_text_color(0, 70, 100)
        self.cell(0, 10, sanitize_text(title), 'B', 1, 'L'); self.ln(4)

    def section_body(self, text, is_list=False):
        self.set_x(self.l_margin)
        self.set_font('DejaVu', '', 11); self.set_text_color(0, 0, 0)
        if is_list:
            items = []
            if isinstance(text, str):
                cleaned_text = text.strip("[]'\" ").replace("'", "").replace('"', '')
                items = [item.strip() for item in cleaned_text.split(',')]
            elif isinstance(text, list):
                items = text
            for item in items:
                self.set_x(self.l_margin)
                if isinstance(item, str) and item.strip():
                    self.multi_cell(0, 6, f"• {sanitize_text(item).strip()}")
        else:
            self.multi_cell(0, 6, sanitize_text(text))
        self.ln(3)

def draw_steps_bar(pdf, steps, goal):
    pdf.ln(2)
    pdf.set_x(pdf.l_margin)
    pdf.set_font('DejaVu', 'B', 10); pdf.cell(0, 8, "Daily Step Progress:", 0, 1)
    bar_width = 100; bar_height = 8;
    pdf.set_fill_color(220, 220, 220); pdf.rect(x=pdf.get_x(), y=pdf.get_y(), w=bar_width, h=bar_height, style='F')
    progress_width = min((steps / goal) * bar_width, bar_width)
    bar_color = (76, 175, 80) if steps >= goal else (239, 83, 80)
    pdf.set_fill_color(bar_color[0], bar_color[1], bar_color[2]); pdf.rect(x=pdf.get_x(), y=pdf.get_y(), w=progress_width, h=bar_height, style='F')
    pdf.set_x(pdf.get_x() + bar_width + 5)
    pdf.set_font('DejaVu', 'B', 11); pdf.cell(0, bar_height, f'{steps} / {goal} steps', 0, 1)

def generate_daily_report(user_profile, log_data, full_analysis, recommendations):
    report_dir = "generated_reports"; os.makedirs(report_dir, exist_ok=True)
    log_date_str = log_data['log_details']['log_date']
    user_id = user_profile['user_id']
    file_path = os.path.join(report_dir, f"report_{user_id}_{log_date_str}.pdf")

    pdf = PDF()
    pdf.add_page()
    
    if "error" not in full_analysis:
        score_data = full_analysis.get("wellness_score", {})
        score = score_data.get("score", "N/A")
        pdf.set_font('DejaVu', 'B', 24); pdf.set_text_color(76, 175, 80)
        pdf.cell(40, 20, sanitize_text(score), 1, 0, 'C')
        pdf.set_x(55)
        pdf.set_font('DejaVu', '', 10); pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(0, 5, sanitize_text(score_data.get("justification", "Analysis of your daily inputs.")))
    else:
        pdf.set_font('DejaVu', 'B', 16); pdf.set_text_color(200, 0, 0)
        pdf.cell(0, 10, "Analysis Failed", 0, 1)

    pdf.ln(8)
    pdf.set_font('DejaVu', '', 11)
    pdf.cell(0, 8, f"Report for: {user_profile['name']} on {log_date_str}", 0, 1)
    
    if "error" in full_analysis:
        pdf.section_title("Error Details")
        pdf.section_body(full_analysis["error"])
    else:
        nutri_analysis = full_analysis.get("nutrition_analysis", {})
        summary_data = nutri_analysis.get("final_summary", {})

        pdf.section_title("AI-Powered Insights")
        pdf.set_font('DejaVu', 'B', 11); pdf.cell(0, 8, "Physical Activity:", 0, 1)
        pdf.section_body(full_analysis.get('physical_activity_analysis', 'Not available.'))
        pdf.set_font('DejaVu', 'B', 11); pdf.cell(0, 8, "Mental Clarity:", 0, 1)
        pdf.section_body(full_analysis.get('mental_clarity_analysis', 'Not available.'))

        daily_img_analysis = full_analysis.get("daily_image_analysis", {})
        comp_analysis = full_analysis.get("comparative_analysis", {})
        pdf.set_font('DejaVu', 'B', 11); pdf.cell(0, 8, "Daily Image Analysis:", 0, 1)
        pdf.section_body(f"Selfie: {daily_img_analysis.get('selfie_analysis', 'Not available.')}")
        pdf.section_body(f"Posture: {daily_img_analysis.get('posture_analysis', 'Not available.')}")
        pdf.set_font('DejaVu', 'B', 11); pdf.cell(0, 8, "Comparative Analysis:", 0, 1)
        pdf.section_body(f"Selfie Comparison: {comp_analysis.get('selfie_feedback', 'Not available.')}")
        pdf.section_body(f"Posture Comparison: {comp_analysis.get('posture_feedback', 'Not available.')}")

        pdf.section_title("Today's Metrics")
        metrics = { "Weight": f"{log_data['log_details']['weight_kg']} kg", "Sleep": f"{log_data['log_details']['total_sleep_minutes'] // 60}h {log_data['log_details']['total_sleep_minutes'] % 60}m", "Water Intake": f"{log_data['log_details']['hydration_level']} Liters", "Mood": f"{log_data['log_details']['mood']}", "Stress Level": f"{log_data['log_details']['stress_level']}", }
        for key, value in metrics.items():
            pdf.set_x(pdf.l_margin)
            pdf.set_font('DejaVu', 'B', 10); pdf.cell(40, 8, key, 1)
            pdf.set_font('DejaVu', '', 10); pdf.cell(0, 8, f" {value}", 1, 1)
        draw_steps_bar(pdf, log_data['log_details']['steps'], 10000)
        
        pdf.add_page()
        pdf.section_title("Nutritional Breakdown")
        for meal, log_entry in zip(nutri_analysis.get("meal_analyses", []), log_data["food_entries"]):
            if pdf.get_y() > 220: pdf.add_page()
            
            pdf.set_font('DejaVu', 'B', 12); pdf.cell(0, 10, f"- {meal.get('meal_type', 'Meal')}", 0, 1)
            
            start_y = pdf.get_y()
            pdf.set_font('DejaVu', '', 10); pdf.multi_cell(115, 6, f"User's Note: {sanitize_text(log_entry['description'])}")
            text_end_y = pdf.get_y()
            
            image_end_y = start_y
            img_path = log_entry['food_image_path']
            image_width_on_pdf = 70
            if img_path and os.path.exists(img_path):
                try: 
                    with Image.open(img_path) as img:
                        w, h = img.size
                        aspect_ratio = h / w
                        rendered_height = image_width_on_pdf * aspect_ratio
                    pdf.image(img_path, x=130, y=start_y, w=image_width_on_pdf)
                    image_end_y = start_y + rendered_height
                except Exception as e: print(f"Error embedding image {img_path}: {e}")
            
            pdf.set_y(max(text_end_y, image_end_y) + 3)

            table_data = meal.get('nutrition_table', [])
            if not table_data:
                pdf.section_body("Nutritional data for this meal could not be generated.")
            else:
                headers = list(table_data[0].keys())
                col_widths = {'component': 50, 'calories': 22, 'protein_g': 22, 'carbs_g': 22, 'fats_g': 20, 'vitamins_minerals': 40}
                pdf.set_font('DejaVu', 'B', 8); pdf.set_fill_color(224, 235, 255)
                for header in headers:
                    if header in col_widths: pdf.cell(col_widths[header], 7, sanitize_text(header.replace('_g','(g)').title()), 1, 0, 'C', True)
                pdf.ln()
                pdf.set_font('DejaVu', '', 8)
                for row in table_data:
                    for header in headers:
                        if header in col_widths: pdf.cell(col_widths[header], 7, sanitize_text(row.get(header, 'N/A')), 1)
                    pdf.ln()
            pdf.ln(8)
            
        pdf.add_page()
        pdf.section_title("AI Summary & Recommendations")
        pdf.set_font('DejaVu', 'B', 11); pdf.cell(0, 8, "Overall Summary:", 0, 1)
        pdf.section_body(summary_data.get('summary', 'N/A'))
        
        pdf.set_font('DejaVu', 'B', 11); pdf.cell(0, 8, "Positives:", 0, 1)
        pdf.set_x(pdf.l_margin)
        pdf.section_body(summary_data.get('positives', []), is_list=True)
        
        pdf.set_font('DejaVu', 'B', 11); pdf.cell(0, 8, "Areas for Improvement:", 0, 1)
        pdf.set_x(pdf.l_margin)
        pdf.section_body(summary_data.get('improvements', []), is_list=True)

        pdf.set_font('DejaVu', 'B', 11); pdf.cell(0, 8, "Personalized Food Recommendations:", 0, 1)
        pdf.section_body(recommendations)
    
    try:
        print(f"DEBUG: Attempting to save PDF to: {file_path}")
        pdf.output(file_path)
        print("DEBUG: PDF file saved successfully.")
        return file_path
    except Exception as e:
        print("\n--- CRITICAL ERROR ---")
        print("Failed to save the PDF file to disk.")
        print(f"Error: {e}")
        print("This is likely a file permissions issue or directory missing.")
        print("---------------------\n")
        return None