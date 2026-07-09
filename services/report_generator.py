"""
PDF report generation.

Fixes vs v1:
- v1 silently stripped any character fpdf's default font couldn't encode
  (i.e. all emoji), which meant recommendation text like "Great job! 🎉
  Keep it up 💪" quietly turned into "Great job!  Keep it up " with the
  emphasis gone. Here, EMOJI_TEXT_MAP substitutes a bracketed plain-text
  label ("[celebrate]", "[strength]") instead of deleting the character —
  the information the emoji was carrying survives even though the PDF
  renderer can't draw the glyph.
- Adds a "What we've learned about you" section sourced directly from
  SemanticMemory — the report now visibly reflects the persistent memory
  layer instead of being a snapshot of one date range with no continuity.
"""
from __future__ import annotations

import os
import re
from datetime import datetime

from fpdf import FPDF
from fpdf.enums import XPos, YPos

EMOJI_TEXT_MAP = {
    "🎉": "[celebrate]", "💪": "[strength]", "🔥": "[streak]", "😊": "[happy]",
    "😴": "[sleepy]", "🥗": "[healthy-meal]", "⚠️": "[warning]", "✅": "[done]",
    "📈": "[trending-up]", "📉": "[trending-down]", "💧": "[hydration]",
    "🏃": "[activity]", "❤️": "[heart]", "🧘": "[mindfulness]",
}

_EMOJI_PATTERN = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F0FF]"
)


def sanitize_text(text: str) -> str:
    if not text:
        return ""
    for emoji, label in EMOJI_TEXT_MAP.items():
        text = text.replace(emoji, label)
    # any remaining unmapped emoji: mark rather than silently vanish
    text = _EMOJI_PATTERN.sub("[icon]", text)
    return text.encode("latin-1", "replace").decode("latin-1")


class HealthReportPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(30, 100, 70)
        self.cell(0, 10, "AarogyamAI Health Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.set_font("Helvetica", "", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, datetime.now().strftime("Generated on %d %b %Y"),
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def section_title(self, title: str):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(20, 60, 100)
        self.ln(3)
        self.cell(0, 8, sanitize_text(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(20, 60, 100)
        self.line(self.get_x(), self.get_y(), self.get_x() + 190, self.get_y())
        self.ln(2)

    def body_text(self, text: str):
        self.set_font("Helvetica", "", 11)
        self.set_text_color(20, 20, 20)
        self.set_x(self.l_margin)
        self.multi_cell(0, 6, sanitize_text(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def bullet_list(self, items: list[str]):
        self.set_font("Helvetica", "", 11)
        self.set_text_color(20, 20, 20)
        for item in items:
            # Reset to the left margin before every bullet: multi_cell's
            # cursor does not reliably return to the left margin after a
            # preceding bare cell() call in this fpdf2 version — without
            # this reset, the second bullet inherits the first one's
            # end-of-line x position, drifts past the right margin, and
            # fpdf2 raises "Not enough horizontal space to render a single
            # character". Caught by this project's own PDF tests, not
            # hypothetical.
            self.set_x(self.l_margin)
            self.cell(6, 6, "-")
            self.multi_cell(0, 6, sanitize_text(item), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def metric_row(self, label: str, value: str):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 11)
        self.cell(60, 7, sanitize_text(label))
        self.set_font("Helvetica", "", 11)
        self.cell(0, 7, sanitize_text(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def build_report_pdf(
    user: dict,
    start_date: str,
    end_date: str,
    summary: dict,
    notable_patterns: list[str],
    semantic_memories: list[dict],
    narrative: str,
    output_dir: str,
) -> str:
    pdf = HealthReportPDF()
    pdf.add_page()

    pdf.section_title("Overview")
    pdf.metric_row("Name:", user.get("name", "-"))
    pdf.metric_row("Report Period:", f"{start_date} to {end_date}")
    pdf.metric_row("Days Logged:", str(summary.get("n_days_logged", 0)))
    if summary.get("wellness_score") is not None:
        pdf.metric_row("Wellness Score:", f"{summary['wellness_score']}/100")

    pdf.section_title("Averages")
    for field, val in (summary.get("averages") or {}).items():
        if val is not None:
            pdf.metric_row(field.replace("_", " ").title() + ":", str(val))

    pdf.section_title("Notable Patterns This Period")
    pdf.bullet_list(notable_patterns) if notable_patterns else pdf.body_text(
        "No statistically notable trends yet — keep logging for more signal."
    )

    pdf.section_title("What We've Learned About You")
    if semantic_memories:
        pdf.bullet_list([m["fact"] for m in semantic_memories])
    else:
        pdf.body_text(
            "No long-term patterns established yet. These accumulate the more "
            "consistently you log — check back after a couple of weeks."
        )

    pdf.section_title("AI-Generated Insights")
    pdf.body_text(narrative or "No narrative summary available for this period.")

    os.makedirs(output_dir, exist_ok=True)
    filename = f"report_{user.get('user_id')}_{start_date}_to_{end_date}.pdf"
    filepath = os.path.join(output_dir, filename)
    pdf.output(filepath)
    return filepath
