"""
Report service — orchestration layer that ties analytics, semantic memory,
and the LLM together into the PDF built by report_generator.

v1 gap this closes: the v1 report was generated purely from the date-range
query, with no connection to anything the system had "learned" about the
user historically. Here, `generate_report()` explicitly pulls
SemanticMemory.retrieve_relevant() using the health goal as the query, so
the report's AI narrative is grounded in accumulated memory, not just the
rows in front of it — and the same memory context is exposed directly in
the PDF's "What We've Learned About You" section so the user can see the
system actually retained something between visits.
"""
from __future__ import annotations

import config
import database as db
from llm_client import LLMClient, get_llm
from services import analytics_service
from services.memory_service import EpisodicMemory, SemanticMemory
from services.report_generator import build_report_pdf


def generate_report(user_id: int, start_date: str, end_date: str,
                     llm: LLMClient = None, semantic_memory: SemanticMemory = None) -> dict:
    llm = llm or get_llm()
    semantic_memory = semantic_memory or SemanticMemory(llm=llm)

    user = db.get_user(user_id)
    if not user:
        raise ValueError(f"No such user: {user_id}")

    logs = db.get_logs_in_range(user_id, start_date, end_date)
    summary = analytics_service.compute_summary(logs)
    notable_patterns = analytics_service.detect_notable_patterns(logs)

    query = f"{user.get('health_goal', '')} patterns relevant to this reporting period"
    relevant_memories = semantic_memory.retrieve_relevant(user_id, query, top_k=5)

    digest = EpisodicMemory.summarize_for_prompt(logs)
    memory_context = SemanticMemory.format_for_prompt(relevant_memories)
    prompt = (
        f"Write a warm, specific, 3-4 sentence health narrative for {user.get('name')} "
        f"covering {start_date} to {end_date}. Ground it in the data below — cite actual "
        f"numbers where useful. Do not invent facts not present in the data.\n\n"
        f"Logs:\n{digest}\n\n"
        f"Established long-term patterns:\n{memory_context}\n\n"
        f"Notable patterns this period:\n{'; '.join(notable_patterns) or 'none detected'}\n\n"
        f"Health goal: {user.get('health_goal')}"
    )
    narrative = llm.generate_text(prompt)

    filepath = build_report_pdf(
        user=user, start_date=start_date, end_date=end_date, summary=summary,
        notable_patterns=notable_patterns, semantic_memories=relevant_memories,
        narrative=narrative, output_dir=config.REPORT_DIR,
    )
    db.add_report_record(user_id, "custom_range", start_date, end_date, filepath)

    return {
        "filepath": filepath, "summary": summary,
        "notable_patterns": notable_patterns, "narrative": narrative,
    }
