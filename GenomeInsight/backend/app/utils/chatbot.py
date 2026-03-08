"""LangChain-powered health AI chatbot.

Uses OpenAI GPT-4o via LangChain to provide conversational health insights
based on the user's genomic, blood, wearable, and microbiome data.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are GenomeInsight AI, a knowledgeable health and genomics assistant. You help \
users understand their health data including genomic variants, blood biomarkers, \
epigenetic age, microbiome composition, wearable metrics, and healthspan reports.

Guidelines:
- Always clarify you are an AI assistant, NOT a medical professional.
- Never provide medical diagnoses or prescribe treatments.
- Encourage users to consult healthcare providers for medical decisions.
- Reference the user's actual data when available (provided in context).
- Explain complex genomic/health concepts in accessible language.
- Be empathetic and supportive about health concerns.
- If asked about data you don't have, say so clearly.

The user's health context is provided below. Use it to personalize responses.

{user_context}
"""


@dataclass
class ChatResponse:
    content: str
    tokens_used: int
    model: str


def _build_user_context(user_id: str) -> str:
    """Gather the user's latest health data for chatbot context."""
    from app.extensions import db

    sections = []

    # Latest InnerAge
    try:
        from app.models.healthspan import InnerAgeResult
        ia = (
            InnerAgeResult.query.filter_by(user_id=user_id)
            .order_by(InnerAgeResult.calculated_at.desc())
            .first()
        )
        if ia:
            sections.append(
                f"**InnerAge**: Biological age {ia.biological_age:.1f} vs "
                f"chronological {ia.chronological_age:.1f} (delta {ia.age_delta:+.1f}). "
                f"Model: {ia.model_type}."
            )
    except Exception:
        pass

    # Latest blood results
    try:
        from app.models.blood import BloodResult, BloodUpload
        upload = (
            BloodUpload.query.filter_by(user_id=user_id)
            .order_by(BloodUpload.test_date.desc())
            .first()
        )
        if upload:
            results = BloodResult.query.filter_by(upload_id=upload.id).all()
            markers = [f"{r.marker_display_name}: {r.value} {r.unit}" for r in results[:15]]
            if markers:
                sections.append(
                    f"**Latest Blood Panel** ({upload.test_date.isoformat()}):\n"
                    + "\n".join(f"  - {m}" for m in markers)
                )
    except Exception:
        pass

    # Biomarker zones
    try:
        from app.models.healthspan import BiomarkerZone
        zones = BiomarkerZone.query.filter_by(user_id=user_id).all()
        if zones:
            zone_lines = []
            for z in zones[:10]:
                zone_lines.append(
                    f"  - {z.marker_display_name}: optimal [{z.optimal_low}-{z.optimal_high}] "
                    f"{z.unit}, current={z.current_value}, status={z.zone_status}"
                )
            sections.append("**Optimized Zones**:\n" + "\n".join(zone_lines))
    except Exception:
        pass

    # Genome variants (top risk)
    try:
        from app.models.genome import GenomeAnalysis, GenomeUpload, Variant
        g_upload = (
            GenomeUpload.query.filter_by(user_id=user_id)
            .order_by(GenomeUpload.uploaded_at.desc())
            .first()
        )
        if g_upload:
            analysis = GenomeAnalysis.query.filter_by(
                upload_id=g_upload.id, status="complete"
            ).first()
            if analysis:
                variants = Variant.query.filter_by(analysis_id=analysis.id).limit(10).all()
                if variants:
                    v_lines = [
                        f"  - {v.rsid or v.gene}: {v.genotype} (significance={v.clinical_significance})"
                        for v in variants
                    ]
                    sections.append("**Key Genomic Variants**:\n" + "\n".join(v_lines))
    except Exception:
        pass

    # Microbiome diversity
    try:
        from app.models.microbiome import MicrobiomeAnalysis, MicrobiomeUpload
        m_upload = (
            MicrobiomeUpload.query.filter_by(user_id=user_id)
            .order_by(MicrobiomeUpload.id.desc())
            .first()
        )
        if m_upload:
            m_analysis = MicrobiomeAnalysis.query.filter_by(
                upload_id=m_upload.id, status="complete"
            ).first()
            if m_analysis:
                sections.append(
                    f"**Microbiome**: Shannon diversity={m_analysis.shannon_diversity:.2f}, "
                    f"Simpson={m_analysis.simpson_index:.2f}, "
                    f"species count={m_analysis.total_species_count}."
                )
    except Exception:
        pass

    # Latest healthspan report summary
    try:
        from app.models.healthspan import HealthspanReport
        report = (
            HealthspanReport.query.filter_by(user_id=user_id)
            .order_by(HealthspanReport.generated_at.desc())
            .first()
        )
        if report:
            sections.append(
                f"**Latest Healthspan Report** ({report.period_start} to {report.period_end}):\n"
                f"  Overall={report.overall_score}, Sleep={report.sleep_score}, "
                f"Activity={report.activity_score}, Stress={report.stress_score}"
            )
    except Exception:
        pass

    if not sections:
        return "No health data available yet for this user."

    return "\n\n".join(sections)


def get_chat_response(
    user_id: str,
    message: str,
    conversation_history: list[dict] | None = None,
    model: str = "gpt-4o",
) -> ChatResponse:
    """Generate a chatbot response using LangChain + OpenAI.

    Args:
        user_id: The authenticated user's ID.
        message: The user's message.
        conversation_history: List of {"role": "user"|"assistant", "content": "..."} dicts.
        model: OpenAI model to use.

    Returns:
        ChatResponse with content, tokens, and model used.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return ChatResponse(
            content="AI chatbot is not configured. Please set the OPENAI_API_KEY.",
            tokens_used=0,
            model=model,
        )

    # Build context
    user_context = _build_user_context(user_id)

    # Build messages
    messages = [SystemMessage(content=SYSTEM_PROMPT.format(user_context=user_context))]

    if conversation_history:
        for msg in conversation_history[-20:]:  # Keep last 20 messages for context
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=message))

    # Call LLM
    llm = ChatOpenAI(
        model=model,
        temperature=0.7,
        max_tokens=1024,
        api_key=api_key,
    )

    try:
        response = llm.invoke(messages)
        tokens = response.usage_metadata.get("total_tokens", 0) if response.usage_metadata else 0
        return ChatResponse(
            content=response.content,
            tokens_used=tokens,
            model=model,
        )
    except Exception as e:
        logger.exception("Chatbot LLM call failed for user %s", user_id)
        return ChatResponse(
            content=f"I'm sorry, I encountered an error processing your request. Please try again later.",
            tokens_used=0,
            model=model,
        )
