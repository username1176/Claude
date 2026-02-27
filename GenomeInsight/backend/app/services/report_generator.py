"""AI-driven natural language report generation.

Uses OpenAI's API to turn structured analysis data into a readable health
report.  Falls back to a deterministic template-based report when the
OpenAI key is not configured or the API call fails.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import httpx

from app.services.genome_analyzer import Recommendation, RiskCategory

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "⚠️ IMPORTANT DISCLAIMER: This report is for informational and educational "
    "purposes only. It is NOT medical advice and should NOT be used to diagnose, "
    "treat, or prevent any disease. Genetic associations represent statistical "
    "probabilities, not certainties. Always consult a qualified healthcare "
    "provider before making health decisions based on genetic information."
)


# ── OpenAI integration ───────────────────────────────────────────────────────


def _build_prompt(
    risk_categories: list[RiskCategory],
    recommendations: list[Recommendation],
    variant_count: int,
    annotated_count: int,
) -> str:
    """Build the system + user prompt for the AI model."""

    # Summarize risks
    risk_lines = []
    for rc in risk_categories:
        variant_summaries = "; ".join(
            f"{v['rsid']} ({v['note']})" for v in rc.key_variants[:5]
        )
        risk_lines.append(
            f"- {rc.label}: score {rc.score}/10 ({rc.level}). "
            f"Key variants: {variant_summaries or 'none identified'}"
        )

    # Summarize recommendations
    rec_lines = []
    for rec in recommendations:
        rec_lines.append(
            f"- [{rec.category.upper()}] {rec.title} "
            f"(confidence: {rec.confidence}, evidence: {rec.evidence_rsids})"
        )

    prompt = f"""You are a genetics-literate health communicator writing a personalized
genome analysis report. Write in a warm, clear, accessible tone. Use plain
language and explain technical terms when needed.

IMPORTANT RULES:
1. ONLY reference genetic variants (rsIDs) that appear in the data below.
   Do NOT invent or hallucinate any rsID, gene name, or association.
2. Every health claim must be grounded in the data provided.
3. Include the disclaimer at the end EXACTLY as provided.
4. Use sections with clear headings.
5. Be balanced — mention both risk factors AND protective factors.

ANALYSIS DATA:
- Total variants analyzed: {variant_count}
- Variants with clinical/research annotations: {annotated_count}

RISK CATEGORIES:
{chr(10).join(risk_lines) if risk_lines else "No significant risk categories identified."}

RECOMMENDATIONS:
{chr(10).join(rec_lines) if rec_lines else "No specific recommendations at this time."}

Write the report with these sections:
1. Executive Summary (2-3 sentences)
2. Genetic Risk Overview (brief paragraph per category)
3. Personalized Recommendations (actionable advice)
4. Lifestyle Tweaks (small daily changes)
5. What This Means For You (encouraging, balanced closing)

End with this exact disclaimer:
{DISCLAIMER}"""

    return prompt


def generate_report_openai(
    risk_categories: list[RiskCategory],
    recommendations: list[Recommendation],
    variant_count: int,
    annotated_count: int,
    openai_api_key: str,
) -> str:
    """Call OpenAI API to generate a natural language report.

    Uses gpt-4o with low temperature for factual output.
    """
    prompt = _build_prompt(risk_categories, recommendations, variant_count, annotated_count)

    try:
        with httpx.Client(timeout=httpx.Timeout(connect=10, read=120, write=10, pool=10)) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o",
                    "temperature": 0.3,
                    "max_tokens": 4000,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a professional health report writer "
                                "specializing in consumer genomics. You write "
                                "clear, evidence-based reports that are informative "
                                "but never alarmist."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            report = data["choices"][0]["message"]["content"]

            # Ensure disclaimer is present (model may paraphrase it)
            if "IMPORTANT DISCLAIMER" not in report:
                report += f"\n\n{DISCLAIMER}"

            logger.info("AI report generated via OpenAI (%d chars)", len(report))
            return report

    except Exception as exc:
        logger.warning("OpenAI report generation failed: %s — falling back to template", exc)
        return generate_report_template(
            risk_categories, recommendations, variant_count, annotated_count
        )


# ── Template-based fallback ──────────────────────────────────────────────────


def generate_report_template(
    risk_categories: list[RiskCategory],
    recommendations: list[Recommendation],
    variant_count: int,
    annotated_count: int,
) -> str:
    """Generate a structured report without external AI.

    Used as a fallback when OpenAI is unavailable or unconfigured.
    """
    now = datetime.now(timezone.utc).strftime("%B %d, %Y")
    sections: list[str] = []

    # Header
    sections.append("# GenomeInsight Personal Genome Report")
    sections.append(f"*Generated on {now}*\n")

    # Executive Summary
    sections.append("## Executive Summary\n")
    top_risks = [rc for rc in risk_categories if rc.level in ("elevated", "high")]
    if top_risks:
        risk_names = ", ".join(rc.label for rc in top_risks[:3])
        sections.append(
            f"Your genome analysis examined {variant_count:,} genetic variants, of "
            f"which {annotated_count:,} had known clinical or research associations. "
            f"Areas warranting attention include: **{risk_names}**. "
            f"See below for detailed findings and actionable recommendations."
        )
    else:
        sections.append(
            f"Your genome analysis examined {variant_count:,} genetic variants, of "
            f"which {annotated_count:,} had known clinical or research associations. "
            f"No significantly elevated risk areas were identified. See below for "
            f"detailed findings and personalized lifestyle suggestions."
        )

    # Risk Overview
    sections.append("\n## Genetic Risk Overview\n")
    if risk_categories:
        for rc in risk_categories:
            emoji = {"low": "🟢", "average": "🟡", "elevated": "🟠", "high": "🔴"}.get(
                rc.level, "⚪"
            )
            sections.append(f"### {emoji} {rc.label} — {rc.level.title()} ({rc.score}/10)\n")
            if rc.key_variants:
                for kv in rc.key_variants[:5]:
                    sections.append(f"- **{kv['rsid']}** ({kv['genotype']}): {kv['note']}")
                sections.append("")
    else:
        sections.append("No risk categories scored above baseline.\n")

    # Recommendations
    sections.append("## Personalized Recommendations\n")
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            sections.append(f"### {i}. {rec.title}\n")
            sections.append(f"**Category:** {rec.category.title()} | "
                          f"**Confidence:** {rec.confidence.title()}\n")
            sections.append(rec.body)
            sections.append(f"\n*Evidence: {rec.evidence_rsids}*\n")
    else:
        sections.append(
            "No specific genetic-based recommendations identified. Continue "
            "following general healthy lifestyle guidelines.\n"
        )

    # Lifestyle Tweaks
    sections.append("## Lifestyle Tweaks\n")
    tweaks = [
        "**Morning sunlight**: Get 10-15 minutes of natural light within an hour of waking to regulate your circadian clock.",
        "**Move regularly**: Aim for at least 150 minutes of moderate activity per week — walking counts.",
        "**Hydrate mindfully**: Drink water throughout the day; consider limiting caffeine if recommended above.",
        "**Sleep consistency**: Keep a regular sleep-wake schedule, even on weekends.",
        "**Stress check-ins**: Take 5 minutes twice daily to practice deep breathing or mindfulness.",
    ]
    for tweak in tweaks:
        sections.append(f"- {tweak}")
    sections.append("")

    # Closing
    sections.append("## What This Means For You\n")
    sections.append(
        "Genetics is only one piece of the health puzzle. Lifestyle, environment, "
        "diet, stress, and social connections all play major roles. Use these "
        "insights as a starting point for informed conversations with your "
        "healthcare provider — not as a diagnosis. Small, consistent changes "
        "often have the greatest long-term impact on health."
    )

    # Disclaimer
    sections.append(f"\n---\n\n{DISCLAIMER}")

    report = "\n".join(sections)
    logger.info("Template report generated (%d chars)", len(report))
    return report


# ── Public API ───────────────────────────────────────────────────────────────


def generate_report(
    risk_categories: list[RiskCategory],
    recommendations: list[Recommendation],
    variant_count: int,
    annotated_count: int,
    openai_api_key: str = "",
) -> str:
    """Generate a human-readable genome analysis report.

    Uses OpenAI when an API key is provided; otherwise falls back to the
    template-based generator.
    """
    if openai_api_key:
        return generate_report_openai(
            risk_categories, recommendations,
            variant_count, annotated_count,
            openai_api_key,
        )
    return generate_report_template(
        risk_categories, recommendations,
        variant_count, annotated_count,
    )
