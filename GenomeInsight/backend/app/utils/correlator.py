"""Unified cross-domain correlation engine.

Aggregates genome, epigenetics, microbiome, wearable, and blood data
into a single analysis pipeline, generating a ranked list of insights
with confidence scores and actionable recommendations.

The engine adds *inferred* microbiome-lifestyle correlations that go
beyond the individual per-domain analysers — for example, detecting
that a user's diet patterns (inferred from wearables + blood) may be
disrupting their gut microbiome, or that a genome variant interacts
with both an epigenetic marker and a microbial population.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import date

logger = logging.getLogger(__name__)


# ── Result types ─────────────────────────────────────────────────────────────


@dataclass
class CorrelationInsight:
    """A unified cross-domain insight with confidence ranking."""

    title: str
    body: str
    category: str  # genome, epigenetics, microbiome, wearable, blood, cross_domain
    confidence: str = "medium"  # low / medium / high
    priority: int = 50  # 0-100, higher = more important
    data_sources: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DomainSummary:
    """Summary of a single data domain for the unified report."""

    domain: str  # genome / epigenetics / microbiome / wearable / blood
    status: str  # available / unavailable / stale
    last_updated: str | None = None  # ISO date
    highlights: list[dict] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


@dataclass
class UnifiedAnalysisResult:
    """Complete result of a unified cross-domain analysis."""

    user_id: str
    analysis_date: str
    domains: list[DomainSummary] = field(default_factory=list)
    correlations: list[CorrelationInsight] = field(default_factory=list)
    ai_narrative: str = ""
    disclaimer: str = (
        "This unified analysis is for informational purposes only and is "
        "NOT medical advice. Cross-domain correlations are based on "
        "population-level research and may not apply to your individual "
        "situation. Microbiome analysis is an emerging science; results "
        "vary significantly by sampling method, timing, diet, and "
        "medication. A single sample provides a snapshot, not a definitive "
        "assessment. Consult a healthcare professional for medical decisions."
    )

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "analysis_date": self.analysis_date,
            "domains": [asdict(d) for d in self.domains],
            "correlations": [c.to_dict() for c in self.correlations],
            "ai_narrative": self.ai_narrative,
            "disclaimer": self.disclaimer,
        }


# ── Multi-domain interaction rules ──────────────────────────────────────────

# Rules that span 3+ domains — things the individual analysers miss.
# Each rule is a dict with:
#   conditions: list of domain checks that must all be True
#   insight_template: formatted string
#   category, confidence, priority, tags, recommendations

_MULTI_DOMAIN_RULES: list[dict] = [
    # ---- Genome + Microbiome + Blood (Lactose intolerance triad) ----
    {
        "id": "lactose_triad",
        "conditions": [
            {"domain": "genome", "check": "has_variant", "rsid": "rs4988235", "gene": "LCT/MCM6"},
            {"domain": "microbiome", "check": "genus_below", "genus": "lactobacillus", "threshold": 0.02},
            {"domain": "blood", "check": "marker_flagged", "marker_aliases": ["calcium", "ca"], "flag": "L"},
        ],
        "title": "Lactose intolerance triad: genome, gut bacteria, and calcium",
        "body": (
            "Your LCT/MCM6 variant ({genome_genotype}) predisposes to lactose "
            "intolerance. Combined with low Lactobacillus ({microbiome_abundance:.1%}) "
            "and low calcium ({blood_value} {blood_unit}), your dairy avoidance may be "
            "causing a nutritional gap. Lactobacillus species help digest residual "
            "lactose and support calcium absorption."
        ),
        "category": "cross_domain",
        "confidence": "high",
        "priority": 90,
        "tags": ["nutrition", "gut_health", "bone_health"],
        "recommendations": [
            "Consider calcium-fortified non-dairy alternatives",
            "Lactobacillus-specific probiotic supplementation",
            "Monitor bone density with your doctor",
        ],
    },
    # ---- Genome + Microbiome + Wearable (FTO obesity loop) ----
    {
        "id": "fto_obesity_loop",
        "conditions": [
            {"domain": "genome", "check": "has_variant", "rsid": "rs9939609", "gene": "FTO"},
            {"domain": "microbiome", "check": "ratio_above", "ratio": "firmicutes_bacteroidetes_ratio", "threshold": 3.0},
            {"domain": "wearable", "check": "metric_below", "data_type": "activity", "key": "steps", "threshold": 6000},
        ],
        "title": "FTO + elevated F/B ratio + low activity: metabolic risk loop",
        "body": (
            "Your FTO variant ({genome_genotype}) increases obesity risk. This is "
            "compounded by an elevated Firmicutes/Bacteroidetes ratio ({microbiome_fb:.1f}), "
            "which is linked to increased caloric extraction, and low daily activity "
            "({wearable_steps} steps). This triple interaction creates a reinforcing "
            "metabolic risk loop."
        ),
        "category": "cross_domain",
        "confidence": "high",
        "priority": 85,
        "tags": ["metabolism", "weight_management", "gut_health"],
        "recommendations": [
            "Increase daily steps to 8,000+",
            "Add high-fiber foods to shift F/B ratio",
            "Consider time-restricted eating (consult physician)",
        ],
    },
    # ---- Genome + Microbiome + Wearable (COMT stress-gut axis) ----
    {
        "id": "comt_stress_gut",
        "conditions": [
            {"domain": "genome", "check": "has_variant", "rsid": "rs4680", "gene": "COMT"},
            {"domain": "microbiome", "check": "diversity_below", "metric": "shannon", "threshold": 2.5},
            {"domain": "wearable", "check": "metric_above", "data_type": "stress", "key": "stress_score", "threshold": 65},
        ],
        "title": "COMT + low diversity + high stress: gut-brain axis concern",
        "body": (
            "Your COMT variant ({genome_genotype}) affects dopamine clearance and "
            "stress resilience. With low gut diversity (Shannon: {microbiome_shannon:.2f}) "
            "and elevated stress score ({wearable_stress}), the gut-brain axis may be "
            "under strain. Stress depletes beneficial gut bacteria, which further "
            "impairs neurotransmitter production in a vicious cycle."
        ),
        "category": "cross_domain",
        "confidence": "medium",
        "priority": 80,
        "tags": ["mental_health", "gut_brain_axis", "stress"],
        "recommendations": [
            "Stress reduction: meditation, breathwork, or vagal toning",
            "Psychobiotic supplementation (Lactobacillus rhamnosus, B. longum)",
            "Regular moderate exercise (30 min/day)",
        ],
    },
    # ---- Epigenetics + Microbiome + Blood (Inflammation cascade) ----
    {
        "id": "inflammation_cascade",
        "conditions": [
            {"domain": "epigenetics", "check": "has_overlay_gene", "gene": "TNF"},
            {"domain": "microbiome", "check": "ratio_above", "ratio": "proteobacteria_pct", "threshold": 15},
            {"domain": "blood", "check": "marker_above", "marker_aliases": ["hs_crp", "crp", "c_reactive_protein"], "threshold": 3.0},
        ],
        "title": "Epigenetic + microbiome + blood inflammation cascade",
        "body": (
            "Your epigenetic profile shows altered TNF regulation. Combined with "
            "high Proteobacteria ({microbiome_proteo:.1f}%) and elevated CRP "
            "({blood_value} {blood_unit}), this suggests a multi-layered inflammatory "
            "state involving gene regulation, gut dysbiosis, and systemic inflammation."
        ),
        "category": "cross_domain",
        "confidence": "medium",
        "priority": 88,
        "tags": ["inflammation", "immune", "gut_health"],
        "recommendations": [
            "Anti-inflammatory diet (Mediterranean pattern)",
            "Omega-3 supplementation (EPA/DHA)",
            "Discuss with physician if CRP remains elevated",
        ],
    },
    # ---- Microbiome + Wearable + Blood (Sugar-gut disruption) ----
    {
        "id": "sugar_gut_disruption",
        "conditions": [
            {"domain": "microbiome", "check": "genus_below", "genus": "bifidobacterium", "threshold": 0.02},
            {"domain": "blood", "check": "marker_above", "marker_aliases": ["hemoglobin_a1c", "hba1c", "a1c"], "threshold": 5.7},
            {"domain": "wearable", "check": "metric_below", "data_type": "activity", "key": "steps", "threshold": 5000},
        ],
        "title": "High sugar impact + depleted Bifidobacterium + low activity",
        "body": (
            "Your elevated HbA1c ({blood_value} {blood_unit}) suggests high sugar "
            "impact. This correlates with depleted Bifidobacterium "
            "({microbiome_abundance:.1%}) — these bacteria help regulate blood sugar "
            "through short-chain fatty acid production. Low activity ({wearable_steps} "
            "steps) further impairs glucose regulation."
        ),
        "category": "cross_domain",
        "confidence": "medium",
        "priority": 82,
        "tags": ["metabolism", "blood_sugar", "gut_health"],
        "recommendations": [
            "Increase prebiotic fiber (inulin, FOS) to support Bifidobacterium",
            "Post-meal walking (10-15 min) to improve glucose clearance",
            "Reduce refined carbohydrate intake",
        ],
    },
    # ---- Genome + Epigenetics + Microbiome (Crohn's risk) ----
    {
        "id": "crohns_risk_triad",
        "conditions": [
            {"domain": "genome", "check": "has_variant", "rsid": "rs2066844", "gene": "NOD2"},
            {"domain": "epigenetics", "check": "has_overlay_gene", "gene": "NOD2"},
            {"domain": "microbiome", "check": "genus_below", "genus": "faecalibacterium", "threshold": 0.03},
        ],
        "title": "NOD2 genetic + epigenetic changes + low Faecalibacterium",
        "body": (
            "Your NOD2 variant ({genome_genotype}) affects innate immune sensing "
            "of gut bacteria, and your epigenetic profile shows altered NOD2 "
            "regulation. Combined with low Faecalibacterium ({microbiome_abundance:.1%}), "
            "a key anti-inflammatory butyrate producer, this triad suggests "
            "heightened IBD susceptibility."
        ),
        "category": "cross_domain",
        "confidence": "medium",
        "priority": 85,
        "tags": ["immune", "gut_health", "ibd_risk"],
        "recommendations": [
            "Increase butyrate-producing foods (resistant starch, cooled rice)",
            "Discuss preventive monitoring with a gastroenterologist",
            "Anti-inflammatory diet with emphasis on soluble fiber",
        ],
    },
    # ---- Epigenetics + Microbiome + Blood (Gut-axis methylation) ----
    {
        "id": "gut_axis_methylation",
        "conditions": [
            {"domain": "epigenetics", "check": "has_overlay_gene", "gene": "SLC6A4"},
            {"domain": "microbiome", "check": "diversity_below", "metric": "shannon", "threshold": 3.0},
            {"domain": "blood", "check": "marker_flagged", "marker_aliases": ["vitamin_d", "25_oh_d", "vit_d"], "flag": "L"},
        ],
        "title": "Microbiome-gut axis: Epigenetic changes may explain impaired blood markers",
        "body": (
            "Your epigenetic profile shows altered SLC6A4 (serotonin transporter) "
            "regulation. With low gut diversity (Shannon: {microbiome_shannon:.2f}) and "
            "low Vitamin D ({blood_value} {blood_unit}), this suggests a gut-brain-immune "
            "axis disruption. ~95% of serotonin is produced in the gut, and its "
            "epigenetic regulation alongside reduced microbial diversity may impair "
            "nutrient absorption and immune modulation."
        ),
        "category": "cross_domain",
        "confidence": "medium",
        "priority": 82,
        "tags": ["gut_brain_axis", "epigenetics", "nutrient_absorption"],
        "recommendations": [
            "Discuss Vitamin D supplementation dosing with your physician",
            "Prebiotic fiber to support microbial diversity",
            "Sunlight exposure (15-20 min daily) for natural Vitamin D synthesis",
        ],
    },
    # ---- Genome + Microbiome + Epigenetics (MTHFR methylation-gut axis) ----
    {
        "id": "mthfr_gut_methylation",
        "conditions": [
            {"domain": "genome", "check": "has_variant", "rsid": "rs1801133", "gene": "MTHFR"},
            {"domain": "microbiome", "check": "genus_below", "genus": "bifidobacterium", "threshold": 0.03},
            {"domain": "epigenetics", "check": "has_overlay_gene", "gene": "MTHFR"},
        ],
        "title": "MTHFR variant + epigenetic change + low Bifidobacterium: folate-gut axis",
        "body": (
            "Your MTHFR variant ({genome_genotype}) reduces folate metabolism efficiency, "
            "and your epigenetic profile shows altered MTHFR regulation. Low "
            "Bifidobacterium ({microbiome_abundance:.1%}) compounds this, as these "
            "bacteria synthesize folate and B-vitamins in the gut. This triple "
            "interaction may impair methylation capacity system-wide."
        ),
        "category": "cross_domain",
        "confidence": "medium",
        "priority": 83,
        "tags": ["methylation", "folate", "gut_health"],
        "recommendations": [
            "Methylfolate (5-MTHF) supplementation — consult physician for dosing",
            "Increase Bifidobacterium via fermented foods or targeted probiotics",
            "Folate-rich foods: dark leafy greens, legumes, citrus",
        ],
    },
    # ---- Microbiome + Wearable (Sleep-gut cycle) ----
    {
        "id": "sleep_gut_cycle",
        "conditions": [
            {"domain": "microbiome", "check": "diversity_below", "metric": "shannon", "threshold": 3.0},
            {"domain": "wearable", "check": "metric_below", "data_type": "sleep", "key": "total_sleep_minutes", "threshold": 360},
            {"domain": "wearable", "check": "metric_below", "data_type": "hrv", "key": "avg_hrv_ms", "threshold": 30},
        ],
        "title": "Poor sleep + low HRV + low gut diversity: circadian-gut disruption",
        "body": (
            "Your sleep ({wearable_sleep} min), HRV ({wearable_hrv} ms), and gut "
            "diversity (Shannon: {microbiome_shannon:.2f}) are all below optimal "
            "levels. The gut microbiome follows circadian rhythms, and sleep "
            "disruption alters microbial composition. Low HRV indicates reduced "
            "vagal tone, weakening the gut-brain axis."
        ),
        "category": "cross_domain",
        "confidence": "medium",
        "priority": 75,
        "tags": ["sleep", "gut_brain_axis", "circadian"],
        "recommendations": [
            "Consistent sleep schedule (same wake time daily)",
            "Evening prebiotic-rich snack (banana, oats)",
            "Vagal toning exercises before bed (cold face wash, humming)",
        ],
    },
]

# ── Inferred lifestyle insights ─────────────────────────────────────────────
# These create microbiome-relevant insights from wearable + blood data
# even without direct microbiome sampling, using established research.

_INFERRED_MICROBIOME_RULES: list[dict] = [
    {
        "id": "high_sugar_disruption",
        "conditions": [
            {"domain": "blood", "check": "marker_above", "marker_aliases": ["hemoglobin_a1c", "hba1c", "a1c"], "threshold": 5.7},
            {"domain": "wearable", "check": "metric_below", "data_type": "activity", "key": "active_minutes", "threshold": 20},
        ],
        "title": "High sugar intake may disrupt microbiome—suggest alternatives",
        "body": (
            "Your HbA1c ({blood_value} {blood_unit}) and low activity "
            "({wearable_active_min} active minutes) suggest a high-sugar, "
            "sedentary pattern that can deplete beneficial Bifidobacterium and "
            "Lactobacillus while promoting Proteobacteria overgrowth. Even without "
            "a microbiome sample, research strongly links this pattern to gut dysbiosis."
        ),
        "category": "cross_domain",
        "confidence": "medium",
        "priority": 70,
        "tags": ["diet_inference", "gut_health", "metabolism"],
        "recommendations": [
            "Replace sugary snacks with prebiotic-rich alternatives (berries, nuts)",
            "Add 20+ minutes of walking after meals",
            "Consider uploading a microbiome sample to confirm gut status",
        ],
    },
    {
        "id": "stress_sleep_gut_inference",
        "conditions": [
            {"domain": "wearable", "check": "metric_above", "data_type": "stress", "key": "stress_score", "threshold": 65},
            {"domain": "wearable", "check": "metric_below", "data_type": "sleep", "key": "deep_sleep_minutes", "threshold": 45},
        ],
        "title": "Chronic stress + poor deep sleep may harm gut microbiome",
        "body": (
            "Your stress score ({wearable_stress}) and deep sleep "
            "({wearable_deep_sleep} min) indicate chronic stress with inadequate "
            "recovery. Research shows this pattern increases intestinal permeability "
            "('leaky gut'), reduces microbial diversity, and promotes inflammatory "
            "species. The gut-brain axis is bidirectional—improving either side "
            "helps the other."
        ),
        "category": "cross_domain",
        "confidence": "low",
        "priority": 60,
        "tags": ["stress", "sleep", "gut_brain_axis"],
        "recommendations": [
            "Evening wind-down routine: dim lights 1h before bed",
            "Fermented foods daily (yogurt, kefir, sauerkraut)",
            "Adaptogenic herbs (ashwagandha) — discuss with doctor",
        ],
    },
    {
        "id": "low_activity_fiber_inference",
        "conditions": [
            {"domain": "wearable", "check": "metric_below", "data_type": "activity", "key": "steps", "threshold": 4000},
            {"domain": "blood", "check": "marker_flagged", "marker_aliases": ["cholesterol_ldl", "ldl", "ldl_cholesterol"], "flag": "H"},
        ],
        "title": "Sedentary lifestyle + high LDL may indicate fiber-poor diet",
        "body": (
            "Very low activity ({wearable_steps} steps) combined with high LDL "
            "cholesterol ({blood_value} {blood_unit}) suggests a fiber-poor, "
            "sedentary pattern. Dietary fiber feeds beneficial gut bacteria that "
            "produce short-chain fatty acids, which help regulate cholesterol. "
            "This pattern likely reflects reduced microbial diversity."
        ),
        "category": "cross_domain",
        "confidence": "low",
        "priority": 55,
        "tags": ["diet_inference", "cardiovascular", "gut_health"],
        "recommendations": [
            "Add 25-30g fiber daily (whole grains, legumes, vegetables)",
            "Gradually increase daily walking to 7,000+ steps",
            "Consider a microbiome test to assess gut health",
        ],
    },
]


# ── Condition evaluators ────────────────────────────────────────────────────


def _check_condition(
    condition: dict,
    *,
    genome_variants: list[dict],
    blood_markers: list[dict],
    wearable_by_type: dict[str, dict],
    microbiome_profile: dict | None,
    epigenetic_overlays: list[dict],
) -> tuple[bool, dict]:
    """Evaluate a single condition, returning (matched, context_vars)."""
    domain = condition["domain"]
    check = condition["check"]
    ctx: dict = {}

    if domain == "genome":
        rsid_map = {v["rsid"]: v for v in genome_variants if v.get("rsid")}
        if check == "has_variant":
            variant = rsid_map.get(condition["rsid"])
            if variant:
                ctx["genome_genotype"] = variant.get("genotype", "?")
                ctx["genome_gene"] = condition.get("gene", "")
                return True, ctx
            return False, ctx

    elif domain == "blood":
        marker_map: dict[str, dict] = {}
        for m in blood_markers:
            name = m.get("marker_name", "").lower()
            marker_map[name] = m

        if check in ("marker_above", "marker_below", "marker_flagged"):
            marker = None
            for alias in condition.get("marker_aliases", []):
                if alias in marker_map:
                    marker = marker_map[alias]
                    break
            if not marker:
                return False, ctx

            ctx["blood_value"] = marker.get("value", 0)
            ctx["blood_unit"] = marker.get("unit", "")
            ctx["blood_flag"] = marker.get("flag", "")

            if check == "marker_above":
                return marker.get("value", 0) > condition["threshold"], ctx
            elif check == "marker_below":
                return marker.get("value", 0) < condition["threshold"], ctx
            elif check == "marker_flagged":
                return marker.get("flag", "") == condition.get("flag", "H"), ctx

    elif domain == "wearable":
        dt = condition.get("data_type", "")
        summary = wearable_by_type.get(dt, {})
        key = condition.get("key", "")
        value = summary.get(key)

        if value is None:
            return False, ctx

        # Store all potentially useful wearable context vars
        ctx[f"wearable_{key}"] = value
        ctx["wearable_steps"] = wearable_by_type.get("activity", {}).get("steps", 0)
        ctx["wearable_active_min"] = wearable_by_type.get("activity", {}).get("active_minutes", 0)
        ctx["wearable_sleep"] = wearable_by_type.get("sleep", {}).get("total_sleep_minutes", 0)
        ctx["wearable_deep_sleep"] = wearable_by_type.get("sleep", {}).get("deep_sleep_minutes", 0)
        ctx["wearable_stress"] = wearable_by_type.get("stress", {}).get("stress_score", 0)
        ctx["wearable_hrv"] = wearable_by_type.get("hrv", {}).get("avg_hrv_ms", 0)

        if check == "metric_below":
            return value < condition["threshold"], ctx
        elif check == "metric_above":
            return value > condition["threshold"], ctx

    elif domain == "microbiome":
        if not microbiome_profile:
            return False, ctx

        diversity = microbiome_profile.get("diversity", {})
        composition = microbiome_profile.get("composition", {})

        # Build genus map from composition data
        genera: dict[str, float] = {}
        for g in composition.get("genus", []):
            genera[g["name"].lower()] = g["abundance"]

        # Build phyla ratio map
        phyla_map: dict[str, float] = {}
        for p in composition.get("phylum", []):
            phyla_map[p["name"].lower()] = p["abundance"]

        firmicutes = phyla_map.get("firmicutes", 0)
        bacteroidetes = phyla_map.get("bacteroidetes", 0) or phyla_map.get("bacteroidota", 0)
        proteobacteria = phyla_map.get("proteobacteria", 0) or phyla_map.get("pseudomonadota", 0)
        fb_ratio = firmicutes / bacteroidetes if bacteroidetes > 0.001 else 0.0

        ctx["microbiome_shannon"] = diversity.get("shannon", 0)
        ctx["microbiome_fb"] = fb_ratio
        ctx["microbiome_proteo"] = proteobacteria * 100

        if check == "genus_below":
            genus_name = condition.get("genus", "").lower()
            abundance = genera.get(genus_name, 0)
            ctx["microbiome_abundance"] = abundance
            return abundance < condition["threshold"], ctx

        elif check == "diversity_below":
            metric = condition.get("metric", "shannon")
            value = diversity.get(metric, 0)
            return value < condition["threshold"], ctx

        elif check == "ratio_above":
            ratio_key = condition.get("ratio", "")
            if ratio_key == "firmicutes_bacteroidetes_ratio":
                return fb_ratio > condition["threshold"], ctx
            elif ratio_key == "proteobacteria_pct":
                return (proteobacteria * 100) > condition["threshold"], ctx

    elif domain == "epigenetics":
        if check == "has_overlay_gene":
            target_gene = condition.get("gene", "").lower()
            for overlay in epigenetic_overlays:
                if overlay.get("gene", "").lower() == target_gene:
                    return True, ctx
            return False, ctx

    return False, ctx


# ── Core correlation engine ─────────────────────────────────────────────────


def run_unified_correlation(
    user_variants: list[dict],
    blood_markers: list[dict],
    wearable_summaries: list[dict],
    microbiome_profile: dict | None = None,
    epigenetic_overlays: list[dict] | None = None,
) -> list[CorrelationInsight]:
    """Run all multi-domain and inferred-microbiome correlation rules.

    This supplements (does NOT replace) the per-domain analysers in
    ``wearable_client.py`` and ``microbiome_analyzer.py``.  It adds
    higher-order correlations that span 3+ domains.

    Args:
        user_variants: list of dicts with rsid, gene, genotype, risk_level
        blood_markers: list of dicts with marker_name, value, unit, flag
        wearable_summaries: list of dicts with data_type, summary, date
        microbiome_profile: optional dict with diversity, composition, enterotype
        epigenetic_overlays: optional list of overlay dicts with gene key

    Returns:
        Ranked list of CorrelationInsight objects.
    """
    if epigenetic_overlays is None:
        epigenetic_overlays = []

    # Build lookup for wearable summaries
    wearable_by_type: dict[str, dict] = {}
    for ws in wearable_summaries:
        dt = ws.get("data_type", "")
        if dt and ws.get("summary"):
            wearable_by_type[dt] = ws["summary"]

    all_rules = _MULTI_DOMAIN_RULES + _INFERRED_MICROBIOME_RULES
    insights: list[CorrelationInsight] = []

    for rule in all_rules:
        matched = True
        merged_ctx: dict = {}

        for condition in rule["conditions"]:
            ok, ctx = _check_condition(
                condition,
                genome_variants=user_variants,
                blood_markers=blood_markers,
                wearable_by_type=wearable_by_type,
                microbiome_profile=microbiome_profile,
                epigenetic_overlays=epigenetic_overlays,
            )
            if not ok:
                matched = False
                break
            merged_ctx.update(ctx)

        if not matched:
            continue

        # Format body with context
        try:
            body = rule["body"].format(**merged_ctx)
        except (KeyError, IndexError, ValueError):
            body = rule["body"]

        insights.append(CorrelationInsight(
            title=rule["title"],
            body=body,
            category=rule["category"],
            confidence=rule["confidence"],
            priority=rule["priority"],
            data_sources=[c["domain"] for c in rule["conditions"]],
            recommendations=rule.get("recommendations", []),
            tags=rule.get("tags", []),
        ))

    # Sort by priority descending
    insights.sort(key=lambda x: x.priority, reverse=True)
    return insights


# ── Domain summary builders ─────────────────────────────────────────────────


def build_genome_summary(user_variants: list[dict]) -> DomainSummary:
    """Build genome domain summary."""
    if not user_variants:
        return DomainSummary(domain="genome", status="unavailable")

    risk_counts = {"high": 0, "elevated": 0, "low": 0, "unknown": 0}
    for v in user_variants:
        risk = v.get("risk_level", "unknown")
        risk_counts[risk] = risk_counts.get(risk, 0) + 1

    highlights = []
    if risk_counts["high"] > 0:
        highlights.append({
            "label": "High-risk variants",
            "value": risk_counts["high"],
            "severity": "high",
        })
    if risk_counts["elevated"] > 0:
        highlights.append({
            "label": "Elevated-risk variants",
            "value": risk_counts["elevated"],
            "severity": "medium",
        })

    return DomainSummary(
        domain="genome",
        status="available",
        metrics={
            "total_variants": len(user_variants),
            "risk_distribution": risk_counts,
        },
        highlights=highlights,
    )


def build_blood_summary(blood_markers: list[dict]) -> DomainSummary:
    """Build blood domain summary."""
    if not blood_markers:
        return DomainSummary(domain="blood", status="unavailable")

    flagged_high = [m for m in blood_markers if m.get("flag") == "H"]
    flagged_low = [m for m in blood_markers if m.get("flag") == "L"]

    highlights = []
    for m in flagged_high:
        highlights.append({
            "label": m.get("marker_display_name", m.get("marker_name", "")),
            "value": f"{m.get('value', '')} {m.get('unit', '')}",
            "severity": "high",
            "flag": "H",
        })
    for m in flagged_low:
        highlights.append({
            "label": m.get("marker_display_name", m.get("marker_name", "")),
            "value": f"{m.get('value', '')} {m.get('unit', '')}",
            "severity": "medium",
            "flag": "L",
        })

    return DomainSummary(
        domain="blood",
        status="available",
        metrics={
            "total_markers": len(blood_markers),
            "flagged_high": len(flagged_high),
            "flagged_low": len(flagged_low),
            "normal": len(blood_markers) - len(flagged_high) - len(flagged_low),
        },
        highlights=highlights[:5],
    )


def build_wearable_summary(wearable_summaries: list[dict]) -> DomainSummary:
    """Build wearable domain summary."""
    if not wearable_summaries:
        return DomainSummary(domain="wearable", status="unavailable")

    latest_date = None
    metrics: dict = {}
    for ws in wearable_summaries:
        dt = ws.get("data_type", "")
        summary = ws.get("summary", {})
        if dt and summary:
            metrics[dt] = summary
            ws_date = ws.get("date")
            if ws_date and (latest_date is None or ws_date > latest_date):
                latest_date = ws_date

    highlights = []
    activity = metrics.get("activity", {})
    if activity.get("steps", 0) > 0:
        highlights.append({
            "label": "Steps",
            "value": activity["steps"],
            "severity": "low" if activity["steps"] >= 7000 else "medium",
        })

    sleep = metrics.get("sleep", {})
    total_sleep = sleep.get("total_sleep_minutes", 0)
    if total_sleep > 0:
        highlights.append({
            "label": "Sleep",
            "value": f"{total_sleep} min ({total_sleep / 60:.1f}h)",
            "severity": "low" if total_sleep >= 420 else "medium",
        })

    return DomainSummary(
        domain="wearable",
        status="available",
        last_updated=latest_date,
        metrics=metrics,
        highlights=highlights,
    )


def build_microbiome_summary(microbiome_profile: dict | None) -> DomainSummary:
    """Build microbiome domain summary."""
    if not microbiome_profile:
        return DomainSummary(domain="microbiome", status="unavailable")

    diversity = microbiome_profile.get("diversity", {})
    enterotype = microbiome_profile.get("enterotype")

    highlights = []
    shannon = diversity.get("shannon", 0)
    if shannon > 0:
        severity = "low" if shannon >= 3.0 else "high" if shannon < 2.5 else "medium"
        highlights.append({
            "label": "Shannon diversity",
            "value": round(shannon, 2),
            "severity": severity,
        })

    if enterotype:
        highlights.append({
            "label": "Enterotype",
            "value": enterotype,
            "severity": "low",
        })

    return DomainSummary(
        domain="microbiome",
        status="available",
        metrics={
            "diversity": diversity,
            "enterotype": enterotype,
        },
        highlights=highlights,
    )


def build_epigenetics_summary(epigenetic_overlays: list[dict]) -> DomainSummary:
    """Build epigenetics domain summary."""
    if not epigenetic_overlays:
        return DomainSummary(domain="epigenetics", status="unavailable")

    genes_affected = {o.get("gene", "") for o in epigenetic_overlays if o.get("gene")}
    highlights = []
    for gene in sorted(genes_affected)[:5]:
        highlights.append({"label": gene, "value": "epigenetic modification", "severity": "low"})

    return DomainSummary(
        domain="epigenetics",
        status="available",
        metrics={
            "overlay_count": len(epigenetic_overlays),
            "genes_affected": len(genes_affected),
        },
        highlights=highlights,
    )


# ── Full unified analysis ───────────────────────────────────────────────────


def run_full_unified_analysis(
    user_id: str,
    user_variants: list[dict],
    blood_markers: list[dict],
    wearable_summaries: list[dict],
    microbiome_profile: dict | None = None,
    epigenetic_overlays: list[dict] | None = None,
    existing_insights: list[dict] | None = None,
) -> UnifiedAnalysisResult:
    """Run a complete unified cross-domain analysis.

    Combines domain summaries with multi-domain correlations and
    existing per-domain insights into a single result.

    Args:
        user_id: User identifier.
        user_variants: Genome variants.
        blood_markers: Blood test results.
        wearable_summaries: Wearable data summaries.
        microbiome_profile: Microbiome analysis results.
        epigenetic_overlays: Epigenetic overlays.
        existing_insights: Pre-computed insights from per-domain analysers.

    Returns:
        UnifiedAnalysisResult with all domains and correlations.
    """
    if epigenetic_overlays is None:
        epigenetic_overlays = []
    if existing_insights is None:
        existing_insights = []

    # Build domain summaries
    domains = [
        build_genome_summary(user_variants),
        build_blood_summary(blood_markers),
        build_wearable_summary(wearable_summaries),
        build_microbiome_summary(microbiome_profile),
        build_epigenetics_summary(epigenetic_overlays),
    ]

    # Run multi-domain correlations
    correlations = run_unified_correlation(
        user_variants=user_variants,
        blood_markers=blood_markers,
        wearable_summaries=wearable_summaries,
        microbiome_profile=microbiome_profile,
        epigenetic_overlays=epigenetic_overlays,
    )

    # Merge existing per-domain insights as lower-priority correlations
    seen_titles = {c.title for c in correlations}
    for existing in existing_insights:
        title = existing.get("title", "")
        if title and title not in seen_titles:
            correlations.append(CorrelationInsight(
                title=title,
                body=existing.get("body", ""),
                category=existing.get("category", "daily"),
                confidence=existing.get("confidence", "medium"),
                priority=existing.get("priority", 40),
                data_sources=existing.get("data_sources", []),
                recommendations=existing.get("recommendations", []),
                tags=existing.get("tags", []),
            ))
            seen_titles.add(title)

    # Re-sort after merging
    correlations.sort(key=lambda x: x.priority, reverse=True)

    # Generate narrative
    narrative = _generate_unified_narrative(domains, correlations)

    return UnifiedAnalysisResult(
        user_id=user_id,
        analysis_date=date.today().isoformat(),
        domains=domains,
        correlations=correlations,
        ai_narrative=narrative,
    )


def _generate_unified_narrative(
    domains: list[DomainSummary],
    correlations: list[CorrelationInsight],
) -> str:
    """Generate a narrative summary of the unified analysis."""
    available = [d for d in domains if d.status == "available"]
    unavailable = [d for d in domains if d.status != "available"]

    lines = [
        "# Unified Health Analysis",
        "",
        f"**Data sources:** {len(available)} of {len(domains)} domains active "
        f"({', '.join(d.domain for d in available)})",
    ]

    if unavailable:
        lines.append(
            f"**Missing:** {', '.join(d.domain for d in unavailable)} — "
            "upload data for more comprehensive insights"
        )

    lines.append("")

    # Top correlations
    high_priority = [c for c in correlations if c.priority >= 75]
    if high_priority:
        lines.append("## Priority Findings")
        for c in high_priority[:5]:
            lines.append(f"\n### {c.title}")
            lines.append(c.body)
            if c.recommendations:
                lines.append("**Actions:** " + "; ".join(c.recommendations))
    elif correlations:
        lines.append("## Findings")
        for c in correlations[:3]:
            lines.append(f"\n### {c.title}")
            lines.append(c.body)
    else:
        lines.append("## Summary")
        lines.append(
            "No significant cross-domain correlations detected. "
            "Your health markers appear within expected ranges."
        )

    lines.append("")
    lines.append("---")
    lines.append(
        "*This analysis is for informational purposes only and is NOT "
        "medical advice. Consult a healthcare professional for medical decisions.*"
    )

    return "\n".join(lines)
