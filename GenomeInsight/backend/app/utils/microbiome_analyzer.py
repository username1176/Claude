"""Microbiome analysis pipeline.

Handles:
 1. Parsing BIOM (JSON), OTU CSV/TSV, and FASTQ files.
 2. Taxonomy normalisation (Greengenes, SILVA, NCBI formats).
 3. Alpha diversity metrics (Shannon, Simpson, Chao1, observed OTUs).
 4. Phyla ratio computation (Firmicutes/Bacteroidetes, Proteobacteria %).
 5. Enterotype classification.
 6. Health insight generation (rules-based).
 7. Cross-domain correlations (genome, epigenetics, blood, wearable).
 8. External API clients (NMDC, NCBI).
 9. AI summary generation (OpenAI with template fallback).
"""

from __future__ import annotations

import csv
import io
import json
import logging
import math
import re
from dataclasses import asdict, dataclass, field

import httpx

logger = logging.getLogger(__name__)


# ── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class ParsedTaxon:
    """A single taxon record parsed from a microbiome data file."""

    taxonomy_name: str
    taxonomy_level: str  # phylum / class / order / family / genus / species
    relative_abundance: float  # 0.0 – 1.0
    absolute_count: int = 0
    confidence: float | None = None
    taxonomy_id: str = ""  # NCBI taxid
    parent_taxon: str = ""
    full_lineage: dict = field(default_factory=dict)


@dataclass
class MicrobiomeInsight:
    """A health insight derived from microbiome analysis."""

    title: str
    body: str
    category: str  # composition / diversity / dysbiosis / recommendation
    confidence: str = "medium"  # low / medium / high
    data_sources: list[str] = field(default_factory=list)


@dataclass
class MicrobiomeCorrelation:
    """A cross-domain correlation between microbiome and another data layer."""

    title: str
    body: str
    confidence: str = "medium"
    data_sources: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


# ── Taxonomy normalisation ───────────────────────────────────────────────────

_TAXONOMY_LEVELS = ("kingdom", "phylum", "class", "order", "family", "genus", "species")

_GREENGENES_PREFIX = re.compile(r"^[kpcofgs]__")
_LEVEL_PREFIX_MAP = {
    "k": "kingdom", "p": "phylum", "c": "class", "o": "order",
    "f": "family", "g": "genus", "s": "species",
}


def normalize_taxonomy(raw: str) -> dict[str, str]:
    """Parse a taxonomy string into a structured dict.

    Supports:
      - Greengenes: "k__Bacteria;p__Firmicutes;c__Clostridia;..."
      - SILVA:      "Bacteria;Firmicutes;Clostridia;..."
      - NCBI:       "Bacteria > Firmicutes > Clostridia > ..."
    """
    result: dict[str, str] = {}

    if not raw or not raw.strip():
        return result

    raw = raw.strip().rstrip(";")

    # Detect separator
    if ">" in raw:
        parts = [p.strip() for p in raw.split(">")]
    else:
        parts = [p.strip() for p in raw.split(";")]

    # Detect Greengenes prefixes
    if parts and _GREENGENES_PREFIX.match(parts[0]):
        for part in parts:
            if "__" in part:
                prefix, name = part.split("__", 1)
                level = _LEVEL_PREFIX_MAP.get(prefix.strip().lower(), "")
                if level and name.strip():
                    result[level] = name.strip()
    else:
        # Positional assignment (SILVA / plain)
        for i, part in enumerate(parts):
            if i < len(_TAXONOMY_LEVELS) and part.strip():
                result[_TAXONOMY_LEVELS[i]] = part.strip()

    return result


def _deepest_level(lineage: dict[str, str]) -> tuple[str, str]:
    """Return the deepest (most specific) taxonomy level and name."""
    for level in reversed(_TAXONOMY_LEVELS):
        if level in lineage and lineage[level]:
            return level, lineage[level]
    return "kingdom", "Unknown"


# ── BIOM parser ──────────────────────────────────────────────────────────────


def parse_biom_json(data: bytes) -> list[ParsedTaxon]:
    """Parse a BIOM v1 (JSON) format OTU table.

    Expected structure:
      {"rows": [{"id": "OTU1", "metadata": {"taxonomy": [...]}}],
       "columns": [...],
       "data": [[row, col, count], ...]}
    """
    text = data.decode("utf-8", errors="replace")
    try:
        biom = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid BIOM JSON: {e}") from e

    rows = biom.get("rows", [])
    data_entries = biom.get("data", [])

    if not rows:
        raise ValueError("BIOM file contains no rows (OTUs).")

    # Sum counts per OTU across all samples
    otu_counts: dict[int, int] = {}
    for entry in data_entries:
        if len(entry) >= 3:
            row_idx, _col_idx, count = entry[0], entry[1], entry[2]
            otu_counts[row_idx] = otu_counts.get(row_idx, 0) + int(count)

    total_count = sum(otu_counts.values()) or 1

    taxa: list[ParsedTaxon] = []
    for i, row in enumerate(rows):
        metadata = row.get("metadata", {}) or {}
        taxonomy_raw = metadata.get("taxonomy", [])

        if isinstance(taxonomy_raw, list):
            lineage_str = ";".join(str(t) for t in taxonomy_raw)
        else:
            lineage_str = str(taxonomy_raw)

        lineage = normalize_taxonomy(lineage_str)
        level, name = _deepest_level(lineage)
        count = otu_counts.get(i, 0)

        taxa.append(ParsedTaxon(
            taxonomy_name=name,
            taxonomy_level=level,
            relative_abundance=count / total_count,
            absolute_count=count,
            full_lineage=lineage,
            parent_taxon=lineage.get(
                _TAXONOMY_LEVELS[max(0, _TAXONOMY_LEVELS.index(level) - 1)], ""
            ) if level != "kingdom" else "",
        ))

    logger.info("Parsed %d taxa from BIOM JSON", len(taxa))
    return taxa


# ── OTU CSV/TSV parser ───────────────────────────────────────────────────────

_OTU_ID_ALIASES = {"otu_id", "#otu id", "feature_id", "feature id", "taxon_id", "asv_id"}
_TAXONOMY_ALIASES = {"taxonomy", "lineage", "taxon", "classification", "taxon_name"}
_COUNT_ALIASES = {"count", "reads", "abundance", "total", "num_reads"}


def _find_col(headers: list[str], aliases: set[str]) -> int | None:
    for i, h in enumerate(headers):
        if h.lower().strip() in aliases:
            return i
    return None


def parse_otu_csv(data: bytes) -> list[ParsedTaxon]:
    """Parse a CSV/TSV OTU table with flexible headers.

    If no explicit count column is found, numeric columns are summed as
    sample counts (standard OTU table format where each sample is a column).
    """
    text = data.decode("utf-8", errors="replace")

    # Detect delimiter
    delimiter = "\t" if "\t" in text.split("\n")[0] else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)

    # Find header row
    headers: list[str] = []
    for row in reader:
        if any(h.lower().strip() in (_OTU_ID_ALIASES | _TAXONOMY_ALIASES) for h in row):
            headers = row
            break

    if not headers:
        raise ValueError(
            "Could not find header row. Expected columns like: "
            "#OTU ID, taxonomy, count (or sample columns)."
        )

    col_taxonomy = _find_col(headers, _TAXONOMY_ALIASES)
    col_count = _find_col(headers, _COUNT_ALIASES)
    col_otu_id = _find_col(headers, _OTU_ID_ALIASES)

    if col_taxonomy is None:
        raise ValueError("OTU table must have a taxonomy/lineage column.")

    # Identify numeric sample columns (if no explicit count column)
    sample_cols: list[int] = []
    if col_count is None:
        known_cols = {col_taxonomy, col_otu_id}
        for i, h in enumerate(headers):
            if i not in known_cols and h.lower().strip() not in _OTU_ID_ALIASES | _TAXONOMY_ALIASES:
                sample_cols.append(i)

    taxa: list[ParsedTaxon] = []
    raw_counts: list[tuple[ParsedTaxon, int]] = []

    for row in reader:
        if not row or len(row) <= col_taxonomy:
            continue

        taxonomy_str = row[col_taxonomy].strip()
        if not taxonomy_str:
            continue

        # Determine count
        count = 0
        if col_count is not None and col_count < len(row):
            try:
                count = int(float(row[col_count].strip()))
            except (ValueError, IndexError):
                pass
        elif sample_cols:
            for sc in sample_cols:
                if sc < len(row):
                    try:
                        count += int(float(row[sc].strip()))
                    except (ValueError, IndexError):
                        pass

        lineage = normalize_taxonomy(taxonomy_str)
        level, name = _deepest_level(lineage)

        taxon = ParsedTaxon(
            taxonomy_name=name,
            taxonomy_level=level,
            relative_abundance=0.0,  # computed after total is known
            absolute_count=count,
            full_lineage=lineage,
            parent_taxon=lineage.get(
                _TAXONOMY_LEVELS[max(0, _TAXONOMY_LEVELS.index(level) - 1)], ""
            ) if level != "kingdom" else "",
        )
        raw_counts.append((taxon, count))

    total = sum(c for _, c in raw_counts) or 1
    for taxon, count in raw_counts:
        taxon.relative_abundance = count / total
        taxa.append(taxon)

    logger.info("Parsed %d taxa from OTU CSV/TSV", len(taxa))
    return taxa


# ── FASTQ metadata extraction ────────────────────────────────────────────────


def parse_fastq_metadata(data: bytes) -> dict:
    """Extract basic stats from a FASTQ file.

    Full FASTQ analysis (assembly, binning) is too heavy for in-app
    processing. Returns metadata for display; recommend users pre-process
    via QIIME2 or MetaPhlAn.
    """
    text = data.decode("utf-8", errors="replace")
    lines = text.split("\n")

    read_count = 0
    total_length = 0
    total_quality = 0
    quality_bases = 0

    i = 0
    while i < len(lines) - 3:
        header = lines[i].strip()
        if not header.startswith("@"):
            i += 1
            continue

        sequence = lines[i + 1].strip()
        quality = lines[i + 3].strip()

        read_count += 1
        total_length += len(sequence)

        for ch in quality:
            total_quality += ord(ch) - 33  # Phred+33 encoding
            quality_bases += 1

        i += 4

    avg_length = total_length / read_count if read_count else 0
    avg_quality = total_quality / quality_bases if quality_bases else 0

    return {
        "read_count": read_count,
        "avg_read_length": round(avg_length, 1),
        "avg_quality_score": round(avg_quality, 1),
        "total_bases": total_length,
        "format": "FASTQ",
        "note": (
            "Raw FASTQ files provide limited analysis. For full microbiome "
            "profiling, pre-process with QIIME2 or MetaPhlAn and upload the "
            "resulting OTU table."
        ),
    }


# ── Diversity metrics ────────────────────────────────────────────────────────


def compute_alpha_diversity(taxa: list[ParsedTaxon]) -> dict:
    """Compute alpha diversity metrics from taxon abundances.

    Returns dict with: shannon, simpson, chao1, observed_otus.
    """
    abundances = [t.relative_abundance for t in taxa if t.relative_abundance > 0]
    counts = [t.absolute_count for t in taxa if t.absolute_count > 0]

    observed_otus = len(abundances)

    # Shannon index: H = -sum(p_i * ln(p_i))
    shannon = 0.0
    for p in abundances:
        if p > 0:
            shannon -= p * math.log(p)

    # Simpson index: D = 1 - sum(p_i^2)
    simpson = 1.0 - sum(p * p for p in abundances)

    # Chao1: S_chao1 = S_obs + (f1^2 / 2*f2)
    singletons = sum(1 for c in counts if c == 1)
    doubletons = sum(1 for c in counts if c == 2)
    if doubletons > 0:
        chao1 = observed_otus + (singletons ** 2) / (2 * doubletons)
    elif singletons > 0:
        chao1 = observed_otus + (singletons * (singletons - 1)) / 2
    else:
        chao1 = float(observed_otus)

    return {
        "shannon": round(shannon, 4),
        "simpson": round(simpson, 4),
        "chao1": round(chao1, 1),
        "observed_otus": observed_otus,
    }


# ── Composition and phyla ratios ─────────────────────────────────────────────


def compute_composition(taxa: list[ParsedTaxon], level: str = "phylum") -> list[dict]:
    """Aggregate taxa by a given taxonomy level and return sorted abundances."""
    aggregated: dict[str, float] = {}
    for taxon in taxa:
        name = taxon.full_lineage.get(level, "")
        if not name:
            if taxon.taxonomy_level == level:
                name = taxon.taxonomy_name
            else:
                name = "Unclassified"
        aggregated[name] = aggregated.get(name, 0) + taxon.relative_abundance

    return sorted(
        [{"name": k, "abundance": round(v, 6)} for k, v in aggregated.items()],
        key=lambda x: x["abundance"],
        reverse=True,
    )


def compute_phyla_ratios(taxa: list[ParsedTaxon]) -> dict:
    """Compute health-relevant phyla ratios."""
    phyla = compute_composition(taxa, "phylum")
    phyla_map = {p["name"].lower(): p["abundance"] for p in phyla}

    firmicutes = phyla_map.get("firmicutes", 0)
    bacteroidetes = phyla_map.get("bacteroidetes", 0) or phyla_map.get("bacteroidota", 0)
    proteobacteria = phyla_map.get("proteobacteria", 0) or phyla_map.get("pseudomonadota", 0)
    actinobacteria = phyla_map.get("actinobacteria", 0) or phyla_map.get("actinomycetota", 0)

    fb_ratio = firmicutes / bacteroidetes if bacteroidetes > 0.001 else 0.0

    return {
        "firmicutes": round(firmicutes, 4),
        "bacteroidetes": round(bacteroidetes, 4),
        "firmicutes_bacteroidetes_ratio": round(fb_ratio, 2),
        "proteobacteria_pct": round(proteobacteria * 100, 2),
        "actinobacteria_pct": round(actinobacteria * 100, 2),
    }


def classify_enterotype(taxa: list[ParsedTaxon]) -> str | None:
    """Classify enterotype based on dominant genus."""
    genera = compute_composition(taxa, "genus")
    if not genera:
        return None

    genus_map = {g["name"].lower(): g["abundance"] for g in genera}

    bacteroides = genus_map.get("bacteroides", 0)
    prevotella = genus_map.get("prevotella", 0)
    ruminococcus = genus_map.get("ruminococcus", 0)

    dominant = max(
        [("Bacteroides", bacteroides), ("Prevotella", prevotella),
         ("Ruminococcus", ruminococcus)],
        key=lambda x: x[1],
    )

    return dominant[0] if dominant[1] > 0.05 else None


# ── Health insights (rules-based) ────────────────────────────────────────────


def generate_microbiome_insights(
    diversity: dict,
    phyla_ratios: dict,
    enterotype: str | None,
    taxa: list[ParsedTaxon] | None = None,
) -> list[MicrobiomeInsight]:
    """Generate health insights from microbiome metrics."""
    insights: list[MicrobiomeInsight] = []
    genera = {}
    if taxa:
        for g in compute_composition(taxa, "genus"):
            genera[g["name"].lower()] = g["abundance"]

    # Diversity alerts
    shannon = diversity.get("shannon", 0)
    if shannon < 2.5:
        insights.append(MicrobiomeInsight(
            title="Low microbial diversity",
            body=(
                f"Your Shannon diversity index ({shannon:.2f}) is below the healthy "
                "threshold of 2.5. Low diversity is associated with metabolic syndrome, "
                "inflammatory bowel disease, and weakened immune function."
            ),
            category="diversity",
            confidence="high",
            data_sources=["microbiome:diversity"],
        ))
    elif shannon > 4.0:
        insights.append(MicrobiomeInsight(
            title="Excellent microbial diversity",
            body=(
                f"Your Shannon diversity index ({shannon:.2f}) indicates a rich, "
                "healthy microbial community. High diversity is associated with "
                "better metabolic health and immune resilience."
            ),
            category="diversity",
            confidence="high",
            data_sources=["microbiome:diversity"],
        ))

    # F/B ratio
    fb = phyla_ratios.get("firmicutes_bacteroidetes_ratio", 0)
    if fb > 3.0:
        insights.append(MicrobiomeInsight(
            title="Elevated Firmicutes/Bacteroidetes ratio",
            body=(
                f"Your F/B ratio of {fb:.1f} is above the typical range (1.0–2.5). "
                "Elevated ratios are linked to obesity risk and metabolic dysfunction. "
                "Consider increasing dietary fiber and fermented foods."
            ),
            category="composition",
            confidence="medium",
            data_sources=["microbiome:firmicutes_bacteroidetes_ratio"],
        ))

    # Proteobacteria
    proteo_pct = phyla_ratios.get("proteobacteria_pct", 0)
    if proteo_pct > 15:
        insights.append(MicrobiomeInsight(
            title="High Proteobacteria abundance",
            body=(
                f"Proteobacteria make up {proteo_pct:.1f}% of your microbiome. "
                "Levels above 15% may indicate gut dysbiosis and are associated "
                "with inflammation. Monitor diet and stress levels."
            ),
            category="dysbiosis",
            confidence="medium",
            data_sources=["microbiome:Proteobacteria"],
        ))

    # Genus-level recommendations
    bifido = genera.get("bifidobacterium", 0)
    if bifido < 0.02:
        insights.append(MicrobiomeInsight(
            title="Low Bifidobacterium abundance",
            body=(
                f"Bifidobacterium represents only {bifido * 100:.1f}% of your microbiome. "
                "Increase prebiotics (inulin, FOS) and consider probiotic-rich foods "
                "like yogurt and kefir to support Bifidobacterium growth."
            ),
            category="recommendation",
            confidence="medium",
            data_sources=["microbiome:Bifidobacterium"],
        ))

    akkermansia = genera.get("akkermansia", 0)
    if akkermansia < 0.01:
        insights.append(MicrobiomeInsight(
            title="Low Akkermansia muciniphila",
            body=(
                "Akkermansia is nearly absent from your microbiome. This bacterium "
                "supports gut barrier integrity and metabolic health. Consider "
                "polyphenol-rich foods (berries, green tea, dark chocolate) to "
                "encourage Akkermansia growth."
            ),
            category="recommendation",
            confidence="low",
            data_sources=["microbiome:Akkermansia"],
        ))

    faecali = genera.get("faecalibacterium", 0)
    if faecali < 0.03:
        insights.append(MicrobiomeInsight(
            title="Low Faecalibacterium prausnitzii",
            body=(
                f"Faecalibacterium represents only {faecali * 100:.1f}% of your "
                "microbiome. This key butyrate producer supports gut lining health. "
                "Add fermented foods daily and increase resistant starch intake "
                "(cooled rice, green bananas)."
            ),
            category="recommendation",
            confidence="medium",
            data_sources=["microbiome:Faecalibacterium"],
        ))

    return insights


# ── Genome cross-domain correlations ─────────────────────────────────────────

_GENOME_MICROBIOME_RULES: list[dict] = [
    {
        "rsid": "rs2187668",
        "gene": "HLA-DQ2",
        "taxon": "bifidobacterium",
        "threshold_low": 0.02,
        "insight": (
            "Your {gene} variant ({genotype}) combined with low Bifidobacterium "
            "({abundance:.1%}) suggests monitoring gluten sensitivity. HLA-DQ2 "
            "carriers with depleted Bifidobacterium may have increased celiac risk."
        ),
        "recommendations": ["Increase prebiotic fiber", "Consider Bifidobacterium supplementation"],
    },
    {
        "rsid": "rs601338",
        "gene": "FUT2",
        "taxon": "bifidobacterium",
        "threshold_low": 0.03,
        "insight": (
            "Your FUT2 non-secretor status ({genotype}) is associated with reduced "
            "Bifidobacterium colonisation ({abundance:.1%}). FUT2 non-secretors "
            "have altered gut mucin that affects Bifidobacterium adhesion."
        ),
        "recommendations": ["Targeted prebiotic supplementation (GOS, FOS)"],
    },
    {
        "rsid": "rs2066844",
        "gene": "NOD2",
        "taxon": "faecalibacterium",
        "threshold_low": 0.03,
        "insight": (
            "Your NOD2 variant ({genotype}) combined with low Faecalibacterium "
            "({abundance:.1%}) warrants attention. NOD2 mutations affect innate "
            "immune sensing of gut bacteria and are linked to Crohn's disease risk."
        ),
        "recommendations": ["Anti-inflammatory diet", "Increase butyrate-producing foods"],
    },
    {
        "rsid": "rs1800795",
        "gene": "IL6",
        "taxon": "proteobacteria_pct",
        "threshold_high": 15,
        "is_phyla_ratio": True,
        "insight": (
            "Your IL6 variant ({genotype}) affects inflammatory signaling. Combined "
            "with elevated Proteobacteria ({abundance:.1f}%), this suggests a "
            "pro-inflammatory gut environment."
        ),
        "recommendations": ["Anti-inflammatory foods (omega-3, turmeric)", "Stress reduction"],
    },
    {
        "rsid": "rs7903146",
        "gene": "TCF7L2",
        "taxon": "firmicutes_bacteroidetes_ratio",
        "threshold_high": 3.0,
        "is_phyla_ratio": True,
        "insight": (
            "Your TCF7L2 variant ({genotype}) increases T2D risk. Combined with an "
            "elevated F/B ratio ({abundance:.1f}), this suggests metabolic "
            "dysregulation that may benefit from dietary intervention."
        ),
        "recommendations": ["Increase fiber intake", "Regular physical activity", "Monitor HbA1c"],
    },
]


def correlate_microbiome_genome(
    taxa: list[ParsedTaxon],
    phyla_ratios: dict,
    user_variants: list[dict],
) -> list[MicrobiomeCorrelation]:
    """Correlate microbiome composition with genome variants."""
    correlations: list[MicrobiomeCorrelation] = []
    if not user_variants:
        return correlations

    rsid_map = {v["rsid"]: v for v in user_variants if v.get("rsid")}
    genera = {g["name"].lower(): g["abundance"] for g in compute_composition(taxa, "genus")}

    for rule in _GENOME_MICROBIOME_RULES:
        variant = rsid_map.get(rule["rsid"])
        if not variant:
            continue

        if rule.get("is_phyla_ratio"):
            value = phyla_ratios.get(rule["taxon"], 0)
            threshold_high = rule.get("threshold_high")
            if threshold_high is not None and value <= threshold_high:
                continue
        else:
            value = genera.get(rule["taxon"], 0)
            threshold_low = rule.get("threshold_low")
            if threshold_low is not None and value >= threshold_low:
                continue

        body = rule["insight"].format(
            gene=rule["gene"],
            genotype=variant.get("genotype", "?"),
            abundance=value,
        )
        correlations.append(MicrobiomeCorrelation(
            title=f"{rule['gene']} + {rule['taxon']}: action recommended",
            body=body,
            confidence="medium",
            data_sources=[f"genome:{rule['rsid']}", f"microbiome:{rule['taxon']}"],
            recommendations=rule.get("recommendations", []),
        ))

    return correlations


# ── Blood cross-domain correlations ──────────────────────────────────────────

_BLOOD_MICROBIOME_RULES: list[dict] = [
    {
        "marker": "hs_crp",
        "marker_aliases": {"hs_crp", "crp", "c_reactive_protein"},
        "threshold_high": 3.0,
        "taxon_key": "proteobacteria_pct",
        "taxon_threshold_high": 10,
        "is_phyla_ratio": True,
        "insight": (
            "Elevated hs-CRP ({value} {unit}) combined with high Proteobacteria "
            "({abundance:.1f}%) suggests systemic inflammation may be partly "
            "gut-driven."
        ),
    },
    {
        "marker": "hemoglobin_a1c",
        "marker_aliases": {"hemoglobin_a1c", "hba1c", "a1c"},
        "threshold_high": 5.7,
        "taxon_key": "firmicutes_bacteroidetes_ratio",
        "taxon_threshold_high": 2.5,
        "is_phyla_ratio": True,
        "insight": (
            "Elevated HbA1c ({value} {unit}) with a high F/B ratio ({abundance:.1f}) "
            "suggests metabolic dysregulation linked to gut composition imbalance."
        ),
    },
    {
        "marker": "vitamin_d",
        "marker_aliases": {"vitamin_d", "25_oh_vitamin_d", "vit_d"},
        "threshold_low": 20.0,
        "taxon_key": "lactobacillus",
        "taxon_threshold_low": 0.02,
        "is_phyla_ratio": False,
        "insight": (
            "Low vitamin D ({value} {unit}) with low Lactobacillus ({abundance:.1%}) "
            "may indicate impaired gut absorption. Vitamin D supports Lactobacillus "
            "colonisation."
        ),
    },
]


def correlate_microbiome_blood(
    taxa: list[ParsedTaxon],
    diversity: dict,
    phyla_ratios: dict,
    blood_markers: list[dict],
) -> list[MicrobiomeCorrelation]:
    """Correlate microbiome with blood markers."""
    correlations: list[MicrobiomeCorrelation] = []
    if not blood_markers:
        return correlations

    marker_map: dict[str, dict] = {}
    for m in blood_markers:
        name = m.get("marker_name", "").lower()
        marker_map[name] = m

    genera = {g["name"].lower(): g["abundance"] for g in compute_composition(taxa, "genus")}

    for rule in _BLOOD_MICROBIOME_RULES:
        # Find matching marker
        marker = None
        for alias in rule["marker_aliases"]:
            if alias in marker_map:
                marker = marker_map[alias]
                break
        if not marker:
            continue

        value = marker.get("value", 0)
        # Check blood threshold
        if "threshold_high" in rule and value < rule["threshold_high"]:
            continue
        if "threshold_low" in rule and value > rule["threshold_low"]:
            continue

        # Check microbiome threshold
        if rule.get("is_phyla_ratio"):
            abundance = phyla_ratios.get(rule["taxon_key"], 0)
            if "taxon_threshold_high" in rule and abundance < rule["taxon_threshold_high"]:
                continue
        else:
            abundance = genera.get(rule["taxon_key"], 0)
            if "taxon_threshold_low" in rule and abundance > rule["taxon_threshold_low"]:
                continue

        body = rule["insight"].format(
            value=value,
            unit=marker.get("unit", ""),
            abundance=abundance,
        )
        correlations.append(MicrobiomeCorrelation(
            title=f"{rule['marker']} + microbiome: correlation detected",
            body=body,
            confidence="medium",
            data_sources=[f"blood:{rule['marker']}", f"microbiome:{rule['taxon_key']}"],
        ))

    return correlations


# ── Wearable cross-domain correlations ───────────────────────────────────────


def correlate_microbiome_wearables(
    diversity: dict,
    phyla_ratios: dict,
    wearable_summaries: list[dict],
) -> list[MicrobiomeCorrelation]:
    """Correlate microbiome with wearable metrics."""
    correlations: list[MicrobiomeCorrelation] = []
    if not wearable_summaries:
        return correlations

    wearable_by_type = {}
    for ws in wearable_summaries:
        dt = ws.get("data_type", "")
        if dt and ws.get("summary"):
            wearable_by_type[dt] = ws["summary"]

    shannon = diversity.get("shannon", 0)
    fb_ratio = phyla_ratios.get("firmicutes_bacteroidetes_ratio", 0)

    # Low activity + low diversity
    activity = wearable_by_type.get("activity", {})
    steps = activity.get("steps", 0)
    if steps and steps < 5000 and shannon < 3.0:
        correlations.append(MicrobiomeCorrelation(
            title="Low activity correlates with reduced diversity",
            body=(
                f"Your average step count ({steps}) and Shannon diversity "
                f"({shannon:.2f}) are both below optimal levels. Regular physical "
                "activity is associated with increased microbial diversity."
            ),
            confidence="medium",
            data_sources=["wearable:activity", "microbiome:diversity"],
            recommendations=["Increase daily walking to 7,000+ steps"],
        ))

    # Poor sleep + elevated F/B ratio
    sleep = wearable_by_type.get("sleep", {})
    total_sleep = sleep.get("total_sleep_minutes", 0)
    if total_sleep and total_sleep < 360 and fb_ratio > 2.5:
        correlations.append(MicrobiomeCorrelation(
            title="Poor sleep linked to elevated F/B ratio",
            body=(
                f"Your sleep ({total_sleep} min) is below 6 hours and your "
                f"Firmicutes/Bacteroidetes ratio ({fb_ratio:.1f}) is elevated. "
                "Poor sleep disrupts gut microbiome composition and increases "
                "the Firmicutes/Bacteroidetes ratio."
            ),
            confidence="medium",
            data_sources=["wearable:sleep", "microbiome:firmicutes_bacteroidetes_ratio"],
            recommendations=["Prioritise 7-8 hours sleep", "Evening routine consistency"],
        ))

    # Low HRV + low diversity (gut-brain axis)
    hrv = wearable_by_type.get("hrv", {})
    avg_hrv = hrv.get("avg_hrv_ms", 0)
    if avg_hrv and avg_hrv < 30 and shannon < 3.0:
        correlations.append(MicrobiomeCorrelation(
            title="Low HRV and low diversity: gut-brain axis concern",
            body=(
                f"Your HRV ({avg_hrv} ms) and microbial diversity (Shannon: "
                f"{shannon:.2f}) are both low. The vagus nerve connects gut "
                "health to heart rate variability via the gut-brain axis."
            ),
            confidence="low",
            data_sources=["wearable:hrv", "microbiome:diversity"],
            recommendations=["Stress reduction techniques", "Prebiotic-rich diet"],
        ))

    return correlations


# ── External API clients ─────────────────────────────────────────────────────


def query_nmdc_biosamples(
    ecosystem_type: str = "Human",
    sample_type: str = "gut",
    client: httpx.Client | None = None,
    api_base: str = "https://api.microbiomedata.org",
) -> list[dict]:
    """Query NMDC for reference biosamples with similar ecosystem.

    Only sends ecosystem metadata — never user PII.
    """
    if client is None:
        try:
            client = httpx.Client(timeout=15)
        except Exception:
            return []

    try:
        params = {
            "filter": json.dumps({
                "ecosystem_category": "Host-associated",
                "ecosystem_type": ecosystem_type,
                "ecosystem_subtype": sample_type.capitalize(),
            }),
            "max_page_size": 10,
        }
        resp = client.get(f"{api_base}/nmdcschema/biosample_set", params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("resources", data.get("results", []))[:10]
    except Exception:
        logger.debug("NMDC query failed", exc_info=True)
        return []


def query_ncbi_taxonomy(
    taxon_name: str,
    ncbi_api_key: str = "",
    client: httpx.Client | None = None,
) -> dict:
    """Query NCBI eUtils for a taxon's taxonomy ID and info."""
    if client is None:
        try:
            client = httpx.Client(timeout=10)
        except Exception:
            return {}

    try:
        params = {
            "db": "taxonomy",
            "term": taxon_name,
            "retmode": "json",
        }
        if ncbi_api_key:
            params["api_key"] = ncbi_api_key

        resp = client.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()
        id_list = data.get("esearchresult", {}).get("idlist", [])
        return {"taxon_name": taxon_name, "ncbi_taxids": id_list}
    except Exception:
        logger.debug("NCBI taxonomy query failed for %s", taxon_name, exc_info=True)
        return {}


# ── AI summary generation ────────────────────────────────────────────────────


def generate_microbiome_ai_summary(
    diversity: dict,
    phyla_ratios: dict,
    enterotype: str | None,
    insights: list[MicrobiomeInsight],
    genome_correlations: list[MicrobiomeCorrelation],
    data_type: str = "16s_rrna",
    openai_api_key: str = "",
) -> str:
    """Generate a narrative summary of microbiome analysis.

    Falls back to a template when no OpenAI key is available.
    """
    if openai_api_key:
        try:
            return _generate_openai_summary(
                diversity, phyla_ratios, enterotype, insights,
                genome_correlations, openai_api_key,
            )
        except Exception:
            logger.warning("OpenAI summary failed, using template", exc_info=True)

    return _generate_template_summary(
        diversity, phyla_ratios, enterotype, insights,
        genome_correlations, data_type,
    )


def _generate_openai_summary(
    diversity: dict,
    phyla_ratios: dict,
    enterotype: str | None,
    insights: list[MicrobiomeInsight],
    genome_correlations: list[MicrobiomeCorrelation],
    api_key: str,
) -> str:
    """Generate summary using OpenAI API."""
    insight_text = "\n".join(f"- {i.title}: {i.body}" for i in insights)
    correlation_text = "\n".join(f"- {c.title}: {c.body}" for c in genome_correlations)

    prompt = (
        f"Summarise this microbiome analysis with health and lifestyle advice.\n\n"
        f"Diversity: Shannon={diversity.get('shannon')}, Simpson={diversity.get('simpson')}, "
        f"Chao1={diversity.get('chao1')}, Observed OTUs={diversity.get('observed_otus')}\n"
        f"Phyla ratios: F/B={phyla_ratios.get('firmicutes_bacteroidetes_ratio')}, "
        f"Proteobacteria={phyla_ratios.get('proteobacteria_pct')}%\n"
        f"Enterotype: {enterotype or 'undetermined'}\n\n"
        f"Key findings:\n{insight_text}\n\n"
        f"Genome correlations:\n{correlation_text}\n\n"
        "Provide a clear, actionable summary for a non-expert. "
        "Include dietary recommendations and lifestyle changes. "
        "End with a disclaimer that this is not medical advice."
    )

    client = httpx.Client(timeout=30)
    resp = client.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a microbiome health analyst."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 800,
            "temperature": 0.4,
        },
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _generate_template_summary(
    diversity: dict,
    phyla_ratios: dict,
    enterotype: str | None,
    insights: list[MicrobiomeInsight],
    genome_correlations: list[MicrobiomeCorrelation],
    data_type: str,
) -> str:
    """Generate a template-based summary (no AI dependency)."""
    lines = [
        "# Microbiome Analysis Summary",
        "",
        f"**Data type:** {data_type.replace('_', ' ').upper()}",
        f"**Enterotype:** {enterotype or 'Undetermined'}",
        "",
        "## Diversity Metrics",
        f"- Shannon Index: {diversity.get('shannon', 'N/A')}",
        f"- Simpson Index: {diversity.get('simpson', 'N/A')}",
        f"- Chao1 Estimator: {diversity.get('chao1', 'N/A')}",
        f"- Observed OTUs: {diversity.get('observed_otus', 'N/A')}",
        "",
        "## Composition Ratios",
        f"- Firmicutes: {phyla_ratios.get('firmicutes', 0) * 100:.1f}%",
        f"- Bacteroidetes: {phyla_ratios.get('bacteroidetes', 0) * 100:.1f}%",
        f"- F/B Ratio: {phyla_ratios.get('firmicutes_bacteroidetes_ratio', 0):.2f}",
        f"- Proteobacteria: {phyla_ratios.get('proteobacteria_pct', 0):.1f}%",
    ]

    if insights:
        lines.append("")
        lines.append("## Key Findings")
        for insight in insights:
            tag = insight.category.upper()
            lines.append(f"\n### [{tag}] {insight.title}")
            lines.append(insight.body)

    if genome_correlations:
        lines.append("")
        lines.append("## Genome-Microbiome Correlations")
        for corr in genome_correlations:
            lines.append(f"\n### {corr.title}")
            lines.append(corr.body)
            if corr.recommendations:
                lines.append("**Recommendations:** " + "; ".join(corr.recommendations))

    lines.append("")
    lines.append("---")
    lines.append(
        "*Disclaimer: This microbiome analysis is for informational purposes only "
        "and is NOT medical advice. Microbiome composition varies significantly "
        "between samples and over time. Consult a healthcare professional for "
        "medical decisions.*"
    )

    return "\n".join(lines)
