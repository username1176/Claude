"""Epigenetics analysis pipeline.

Handles:
 1. Parsing BED and CSV (methylation beta-value) files.
 2. Region annotation (feature type, nearest gene).
 3. Querying ENCODE REST API for overlapping experiments.
 4. Querying Roadmap Epigenomics for ChromHMM states.
 5. Cross-referencing with user genome variants.
 6. Generating AI insight summaries.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field

import httpx

logger = logging.getLogger(__name__)

# ── Data classes ──────────────────────────────────────────────────────────────


@dataclass
class ParsedRegion:
    """A genomic region parsed from a BED or methylation CSV file."""

    chromosome: str
    start_pos: int
    end_pos: int
    name: str = ""
    methylation_beta: float | None = None  # 0.0 – 1.0 (methylation only)
    histone_mark: str | None = None  # e.g. H3K27ac (BED histone only)
    signal_value: float | None = None  # Peak score / signal (BED only)


@dataclass
class RegionAnnotation:
    """Annotation computed for a parsed region."""

    feature_type: str = ""  # promoter / enhancer / gene_body / intergenic
    nearest_gene: str = ""
    encode_experiments: list[dict] = field(default_factory=list)
    roadmap_state: str = ""
    roadmap_detail: dict = field(default_factory=dict)
    interpretation: str = ""


@dataclass
class GenomeEpigeneticOverlay:
    """Cross-reference between a genome variant and epigenetic context."""

    variant_rsid: str
    gene: str
    variant_risk: str
    region_coords: str
    feature_type: str
    methylation_beta: float | None
    histone_mark: str | None
    interpretation: str
    adjusted_risk_modifier: float = 1.0


# ── Well-known gene promoter regions (GRCh38) ────────────────────────────────

_GENE_PROMOTERS: dict[str, tuple[str, int, int]] = {
    "MTHFR": ("chr1", 11785723, 11806920),
    "BRCA1": ("chr17", 43044295, 43170245),
    "BRCA2": ("chr13", 32315474, 32400266),
    "APOE": ("chr19", 44905754, 44909393),
    "TP53": ("chr17", 7668402, 7687550),
    "CYP1A2": ("chr15", 74748843, 74756607),
    "CYP2D6": ("chr22", 42126499, 42130865),
    "CYP2C19": ("chr10", 94762681, 94855547),
    "TCF7L2": ("chr10", 112950053, 113167678),
    "FTO": ("chr16", 53703963, 54121941),
    "BDNF": ("chr11", 27654893, 27722058),
    "HFE": ("chr6", 26087281, 26098343),
    "COMT": ("chr22", 19929262, 19957498),
    "VKORC1": ("chr16", 31096068, 31100211),
    "IL6": ("chr7", 22725889, 22732002),
    "TNF": ("chr6", 31575565, 31578336),
    "PCSK9": ("chr1", 55039548, 55064852),
    "LDLR": ("chr19", 11089362, 11133820),
}

# Promoter = ±2 kb around gene start for overlap checks
_PROMOTER_WINDOW = 2000

# ── BED parser ────────────────────────────────────────────────────────────────


def parse_bed(data: bytes, assay_type: str | None = None) -> list[ParsedRegion]:
    """Parse a BED-format file into regions.

    Supports BED3 through BED6+. If assay_type indicates a histone mark
    (e.g. H3K27ac), sets ``histone_mark`` on each region.
    """
    regions: list[ParsedRegion] = []
    text = data.decode("utf-8", errors="replace")

    for lineno, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("track") or line.startswith("browser"):
            continue

        parts = line.split("\t")
        if len(parts) < 3:
            logger.debug("BED line %d: fewer than 3 columns, skipping", lineno)
            continue

        chrom = parts[0]
        try:
            start = int(parts[1])
            end = int(parts[2])
        except ValueError:
            logger.debug("BED line %d: non-integer coordinates, skipping", lineno)
            continue

        if end <= start:
            continue

        name = parts[3] if len(parts) > 3 else ""
        score = None
        if len(parts) > 4:
            try:
                score = float(parts[4])
            except ValueError:
                pass

        region = ParsedRegion(
            chromosome=chrom,
            start_pos=start,
            end_pos=end,
            name=name,
            signal_value=score,
        )

        # Assign histone mark from assay_type or from name field
        if assay_type and assay_type.startswith("H3"):
            region.histone_mark = assay_type
        elif name and re.match(r"^H3K\d+", name, re.IGNORECASE):
            region.histone_mark = name

        regions.append(region)

    logger.info("Parsed %d regions from BED file", len(regions))
    return regions


# ── Methylation CSV parser ────────────────────────────────────────────────────

# Column header aliases for methylation CSVs
_METH_CHROM_ALIASES = {"chr", "chrom", "chromosome", "#chr"}
_METH_START_ALIASES = {"start", "pos", "position", "start_pos", "chromstart"}
_METH_END_ALIASES = {"end", "end_pos", "chromend"}
_METH_BETA_ALIASES = {"beta", "beta_value", "methylation", "meth", "avg_beta"}
_METH_GENE_ALIASES = {"gene", "gene_symbol", "nearest_gene", "gene_name"}


def _find_col(headers: list[str], aliases: set[str]) -> int | None:
    for i, h in enumerate(headers):
        if h.lower().strip() in aliases:
            return i
    return None


def parse_methylation_csv(data: bytes) -> list[ParsedRegion]:
    """Parse a CSV with methylation beta values into regions.

    Expected columns (flexible header names):
      chromosome, start, end (optional), beta_value, gene (optional)
    """
    text = data.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))

    # Find header row
    headers: list[str] = []
    for row in reader:
        if any(h.lower().strip() in _METH_CHROM_ALIASES for h in row):
            headers = row
            break
    if not headers:
        raise ValueError(
            "Could not find header row. Expected columns: chr, start, beta_value"
        )

    col_chrom = _find_col(headers, _METH_CHROM_ALIASES)
    col_start = _find_col(headers, _METH_START_ALIASES)
    col_end = _find_col(headers, _METH_END_ALIASES)
    col_beta = _find_col(headers, _METH_BETA_ALIASES)
    col_gene = _find_col(headers, _METH_GENE_ALIASES)

    if col_chrom is None or col_start is None or col_beta is None:
        raise ValueError(
            "Methylation CSV must have at minimum: chr, start/pos, and beta columns."
        )

    regions: list[ParsedRegion] = []
    for row in reader:
        if not row or len(row) <= max(col_chrom, col_start, col_beta):
            continue

        chrom = row[col_chrom].strip()
        if not chrom:
            continue

        try:
            start = int(row[col_start].strip())
        except ValueError:
            continue

        end = start + 1
        if col_end is not None and col_end < len(row):
            try:
                end = int(row[col_end].strip())
            except ValueError:
                end = start + 1

        try:
            beta = float(row[col_beta].strip())
        except ValueError:
            continue

        gene = ""
        if col_gene is not None and col_gene < len(row):
            gene = row[col_gene].strip()

        region = ParsedRegion(
            chromosome=chrom,
            start_pos=start,
            end_pos=end,
            name=gene,
            methylation_beta=beta,
        )
        regions.append(region)

    logger.info("Parsed %d regions from methylation CSV", len(regions))
    return regions


# ── Feature-type annotation ───────────────────────────────────────────────────


def annotate_feature_type(region: ParsedRegion) -> tuple[str, str]:
    """Determine feature type and nearest gene for a region.

    Uses a built-in promoter lookup table.  Returns (feature_type, gene).
    """
    for gene, (chrom, gstart, gend) in _GENE_PROMOTERS.items():
        if region.chromosome != chrom:
            continue

        promoter_start = gstart - _PROMOTER_WINDOW
        promoter_end = gstart + _PROMOTER_WINDOW

        # Check overlap
        if region.start_pos < gend and region.end_pos > gstart:
            # Overlaps gene body — is it near the promoter?
            if region.start_pos < promoter_end and region.end_pos > promoter_start:
                return "promoter", gene
            return "gene_body", gene

        # Near the gene (within 10 kb)
        if abs(region.start_pos - gstart) < 10000 or abs(region.end_pos - gend) < 10000:
            return "enhancer", gene

    # Gene from name field
    if region.name and re.match(r"^[A-Z][A-Z0-9]+$", region.name):
        return "intergenic", region.name

    return "intergenic", ""


# ── ENCODE REST API client ────────────────────────────────────────────────────

ENCODE_BASE = "https://www.encodeproject.org"


def query_encode(
    regions: list[ParsedRegion],
    client: httpx.Client,
    assay_type: str | None = None,
    max_results: int = 50,
) -> dict[str, list[dict]]:
    """Query ENCODE for experiments relevant to the uploaded regions.

    Groups regions by chromosome and queries for matching experiments.
    Returns dict keyed by "chrom:start-end" with lists of experiment metadata.
    """
    results: dict[str, list[dict]] = {}

    # Deduplicate chromosomes for a broad experiment search
    chromosomes = {r.chromosome.replace("chr", "") for r in regions}

    assay_filter = assay_type or "WGBS"
    if assay_type and assay_type.startswith("H3"):
        assay_filter = "Histone ChIP-seq"

    try:
        resp = client.get(
            f"{ENCODE_BASE}/search/",
            params={
                "type": "Experiment",
                "assay_title": assay_filter,
                "status": "released",
                "assembly": "GRCh38",
                "format": "json",
                "limit": min(max_results, 25),
                "field": "accession",
                "field": "biosample_ontology.term_name",
                "field": "target.label",
                "field": "assay_title",
                "field": "description",
            },
            headers={"Accept": "application/json"},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except (httpx.HTTPError, Exception) as exc:
        logger.warning("ENCODE search failed: %s", exc)
        return results

    experiments = data.get("@graph", [])
    if not experiments:
        return results

    # Map experiments to each region (simplified: associate all matching
    # experiments since ENCODE search is assay-level, not coordinate-level)
    exp_summaries = []
    for exp in experiments[:10]:
        exp_summaries.append({
            "accession": exp.get("accession", ""),
            "assay": exp.get("assay_title", ""),
            "biosample": (
                exp.get("biosample_ontology", {}).get("term_name", "")
            ),
            "target": exp.get("target", {}).get("label", "") if isinstance(exp.get("target"), dict) else "",
            "description": exp.get("description", "")[:200],
        })

    for region in regions:
        key = f"{region.chromosome}:{region.start_pos}-{region.end_pos}"
        results[key] = exp_summaries

    return results


# ── Roadmap Epigenomics ChromHMM lookup ───────────────────────────────────────

# Tissue-to-Roadmap epigenome ID mapping (most commonly used)
_TISSUE_EPIGENOME_MAP = {
    "blood": "E062",  # Primary mononuclear cells from peripheral blood
    "pbmc": "E062",
    "monocyte": "E029",
    "t_cell": "E034",
    "b_cell": "E032",
    "liver": "E066",
    "brain": "E067",  # Brain angular gyrus
    "adipose": "E063",
    "lung": "E096",
    "saliva": "E062",  # Approximate with blood
}

# ChromHMM 15-state model mnemonics → human-readable labels
CHROMHMM_STATES = {
    "TssA": "Active TSS (promoter)",
    "TssAFlnk": "Flanking Active TSS",
    "TxFlnk": "Transcription at gene 5'/3'",
    "Tx": "Strong transcription",
    "TxWk": "Weak transcription",
    "EnhG": "Genic enhancer",
    "Enh": "Enhancer",
    "ZNF/Rpts": "ZNF genes & repeats",
    "Het": "Heterochromatin",
    "TssBiv": "Bivalent/Poised TSS",
    "BivFlnk": "Flanking Bivalent TSS/Enhancer",
    "EnhBiv": "Bivalent Enhancer",
    "ReprPC": "Repressed PolyComb",
    "ReprPCWk": "Weak Repressed PolyComb",
    "Quies": "Quiescent/Low",
}


def query_roadmap_chromhmm(
    regions: list[ParsedRegion],
    tissue_type: str | None = None,
) -> dict[str, dict]:
    """Look up Roadmap Epigenomics ChromHMM states for regions.

    Uses a rule-based approach mapping feature type and signal data
    to ChromHMM states, since the actual Roadmap bulk files require
    pre-download and indexing. Returns dict keyed by region coord string.

    In production, this would load pre-indexed ChromHMM BED files and
    use interval trees for intersection.
    """
    epigenome_id = _TISSUE_EPIGENOME_MAP.get(
        (tissue_type or "blood").lower(), "E062"
    )

    results: dict[str, dict] = {}

    for region in regions:
        key = f"{region.chromosome}:{region.start_pos}-{region.end_pos}"
        feature, gene = annotate_feature_type(region)

        # Infer ChromHMM state from the feature type and signal data
        state = _infer_chromhmm_state(region, feature)
        label = CHROMHMM_STATES.get(state, state)

        results[key] = {
            "epigenome_id": epigenome_id,
            "state": state,
            "state_label": label,
            "feature_type": feature,
            "nearest_gene": gene,
        }

    return results


def _infer_chromhmm_state(region: ParsedRegion, feature_type: str) -> str:
    """Infer likely ChromHMM state from available region data."""
    # Methylation-based inference
    if region.methylation_beta is not None:
        beta = region.methylation_beta
        if feature_type == "promoter":
            if beta < 0.3:
                return "TssA"  # Low methylation → active promoter
            elif beta > 0.7:
                return "ReprPC"  # High methylation → repressed
            else:
                return "TssBiv"  # Intermediate → bivalent
        elif feature_type == "enhancer":
            if beta < 0.3:
                return "Enh"
            elif beta > 0.7:
                return "ReprPCWk"
            else:
                return "EnhBiv"
        elif feature_type == "gene_body":
            if beta > 0.5:
                return "Tx"  # Gene body methylation → active transcription
            else:
                return "TxWk"
        return "Quies"

    # Histone mark-based inference
    if region.histone_mark:
        mark = region.histone_mark.upper()
        signal = region.signal_value or 0

        if "H3K27AC" in mark:
            if feature_type == "promoter":
                return "TssA" if signal > 5 else "TssAFlnk"
            return "Enh" if signal > 5 else "EnhG"
        elif "H3K4ME3" in mark:
            return "TssA" if feature_type == "promoter" else "TxFlnk"
        elif "H3K4ME1" in mark:
            return "Enh" if signal > 5 else "EnhBiv"
        elif "H3K27ME3" in mark:
            return "ReprPC"
        elif "H3K36ME3" in mark:
            return "Tx"
        elif "H3K9ME3" in mark:
            return "Het"

    return "Quies"


# ── Genome–epigenetics cross-reference ────────────────────────────────────────

# Map rsIDs to genes for overlay matching
_RSID_GENE_MAP: dict[str, str] = {
    "rs1801133": "MTHFR",
    "rs1801131": "MTHFR",
    "rs429358": "APOE",
    "rs7412": "APOE",
    "rs7903146": "TCF7L2",
    "rs9939609": "FTO",
    "rs762551": "CYP1A2",
    "rs1065852": "CYP2D6",
    "rs4244285": "CYP2C19",
    "rs6265": "BDNF",
    "rs4680": "COMT",
    "rs1800562": "HFE",
    "rs1799945": "HFE",
    "rs1800629": "TNF",
    "rs1800795": "IL6",
    "rs10757274": "CDKN2B-AS1",
    "rs174546": "FADS1",
    "rs4988235": "LCT",
}


def cross_reference_genome(
    regions: list[ParsedRegion],
    region_annotations: dict[str, dict],  # keyed by coord string
    user_variants: list[dict],  # [{rsid, gene, genotype, risk_level}, ...]
) -> list[GenomeEpigeneticOverlay]:
    """Cross-reference user genome variants with epigenetic regions.

    For each variant whose gene overlaps an epigenetic region, produce
    an overlay insight explaining the combined interpretation.
    """
    overlays: list[GenomeEpigeneticOverlay] = []

    # Build gene → region index
    gene_to_regions: dict[str, list[tuple[ParsedRegion, dict]]] = {}
    for region in regions:
        key = f"{region.chromosome}:{region.start_pos}-{region.end_pos}"
        ann = region_annotations.get(key, {})
        gene = ann.get("nearest_gene", "") or region.name
        if gene:
            gene_to_regions.setdefault(gene.upper(), []).append((region, ann))

    for variant in user_variants:
        rsid = variant.get("rsid", "")
        gene = variant.get("gene", "") or _RSID_GENE_MAP.get(rsid, "")
        if not gene:
            continue

        matching = gene_to_regions.get(gene.upper(), [])
        if not matching:
            continue

        risk_level = variant.get("risk_level", "unknown")
        genotype = variant.get("genotype", "")

        for region, ann in matching:
            feature = ann.get("feature_type", "intergenic")
            coord = f"{region.chromosome}:{region.start_pos}-{region.end_pos}"

            interpretation, modifier = _build_overlay_interpretation(
                gene=gene,
                rsid=rsid,
                genotype=genotype,
                risk_level=risk_level,
                feature_type=feature,
                methylation_beta=region.methylation_beta,
                histone_mark=region.histone_mark,
                signal_value=region.signal_value,
                chromhmm_state=ann.get("state", ""),
            )

            overlays.append(GenomeEpigeneticOverlay(
                variant_rsid=rsid,
                gene=gene,
                variant_risk=risk_level,
                region_coords=coord,
                feature_type=feature,
                methylation_beta=region.methylation_beta,
                histone_mark=region.histone_mark,
                interpretation=interpretation,
                adjusted_risk_modifier=modifier,
            ))

    return overlays


def _build_overlay_interpretation(
    gene: str,
    rsid: str,
    genotype: str,
    risk_level: str,
    feature_type: str,
    methylation_beta: float | None,
    histone_mark: str | None,
    signal_value: float | None,
    chromhmm_state: str,
) -> tuple[str, float]:
    """Generate interpretation text and risk modifier for a genome-epigenetic overlay."""
    modifier = 1.0
    parts: list[str] = []

    if methylation_beta is not None:
        if feature_type == "promoter":
            if methylation_beta > 0.7:
                parts.append(
                    f"High methylation (beta={methylation_beta:.2f}) at the "
                    f"{gene} promoter may reduce expression of this gene."
                )
                if risk_level in ("elevated", "high"):
                    parts.append(
                        "This epigenetic silencing could attenuate the effect "
                        f"of your {rsid} risk variant."
                    )
                    modifier = 0.85
                else:
                    modifier = 1.05
            elif methylation_beta < 0.3:
                parts.append(
                    f"Low methylation (beta={methylation_beta:.2f}) at the "
                    f"{gene} promoter suggests this gene is actively expressed."
                )
                if risk_level in ("elevated", "high"):
                    parts.append(
                        f"Active expression combined with your {rsid} risk variant "
                        "may amplify the genetic effect."
                    )
                    modifier = 1.15
            else:
                parts.append(
                    f"Intermediate methylation (beta={methylation_beta:.2f}) at the "
                    f"{gene} promoter — expression state is ambiguous."
                )
                modifier = 1.0

        elif feature_type == "gene_body" and methylation_beta > 0.5:
            parts.append(
                f"Gene body methylation (beta={methylation_beta:.2f}) at {gene} "
                "is associated with active transcription."
            )

    if histone_mark:
        mark = histone_mark.upper()
        if "H3K27AC" in mark and feature_type in ("promoter", "enhancer"):
            parts.append(
                f"Active histone mark {histone_mark} detected at this "
                f"{feature_type} region of {gene}, indicating active regulation."
            )
            if risk_level in ("elevated", "high"):
                modifier = max(modifier, 1.15)
        elif "H3K27ME3" in mark:
            parts.append(
                f"Repressive histone mark {histone_mark} at {gene} suggests "
                "this region is silenced."
            )
            if risk_level in ("elevated", "high"):
                modifier = min(modifier, 0.85)

    if chromhmm_state:
        state_label = CHROMHMM_STATES.get(chromhmm_state, chromhmm_state)
        parts.append(f"ChromHMM state: {state_label}.")

    if not parts:
        parts.append(
            f"Epigenetic data overlaps the {gene} locus at this {feature_type} "
            f"region. Your variant {rsid} ({genotype}) is in this context."
        )

    # Round modifier
    modifier = round(modifier, 2)

    return " ".join(parts), modifier


# ── AI summary generation ─────────────────────────────────────────────────────


def generate_epigenetics_ai_summary(
    region_count: int,
    annotated_count: int,
    global_methylation_avg: float | None,
    overlays: list[GenomeEpigeneticOverlay],
    data_type: str,
    openai_api_key: str = "",
) -> str:
    """Generate a natural-language summary of epigenetic findings.

    Uses OpenAI if a key is provided; otherwise falls back to a
    template-based summary.
    """
    if openai_api_key:
        return _generate_ai_summary(
            region_count, annotated_count, global_methylation_avg,
            overlays, data_type, openai_api_key,
        )
    return _generate_template_summary(
        region_count, annotated_count, global_methylation_avg,
        overlays, data_type,
    )


def _generate_template_summary(
    region_count: int,
    annotated_count: int,
    global_methylation_avg: float | None,
    overlays: list[GenomeEpigeneticOverlay],
    data_type: str,
) -> str:
    """Template-based fallback summary."""
    sections: list[str] = []

    sections.append("## Epigenetic Analysis Summary\n")
    sections.append(
        f"Analyzed **{region_count}** genomic regions from your "
        f"{data_type} data, of which **{annotated_count}** were annotated "
        "with reference epigenomic data.\n"
    )

    if global_methylation_avg is not None:
        avg = global_methylation_avg
        sections.append(
            f"**Global methylation average**: {avg:.3f} "
            f"({'hypomethylated' if avg < 0.4 else 'normal' if avg < 0.6 else 'hypermethylated'}).\n"
        )

    if overlays:
        sections.append("### Genome–Epigenetics Cross-Reference\n")
        for ov in overlays[:10]:
            sections.append(
                f"- **{ov.gene}** ({ov.variant_rsid}): {ov.interpretation} "
                f"[Risk modifier: {ov.adjusted_risk_modifier:.2f}]\n"
            )

    sections.append(
        "\n---\n"
        "*Disclaimer: Epigenetic annotations are based on population reference "
        "maps and may not reflect your individual tissue-specific state. "
        "This analysis is for informational purposes only and is NOT medical advice.*"
    )

    return "\n".join(sections)


def _generate_ai_summary(
    region_count: int,
    annotated_count: int,
    global_methylation_avg: float | None,
    overlays: list[GenomeEpigeneticOverlay],
    data_type: str,
    openai_api_key: str,
) -> str:
    """Generate summary via OpenAI API."""
    overlay_text = ""
    if overlays:
        overlay_lines = []
        for ov in overlays[:8]:
            overlay_lines.append(
                f"- Gene: {ov.gene}, Variant: {ov.variant_rsid}, "
                f"Feature: {ov.feature_type}, "
                f"Methylation beta: {ov.methylation_beta}, "
                f"Histone: {ov.histone_mark}, "
                f"Risk modifier: {ov.adjusted_risk_modifier:.2f}"
            )
        overlay_text = "\n".join(overlay_lines)

    prompt = (
        f"Summarize this epigenetic analysis for a health-conscious user.\n\n"
        f"Data type: {data_type}\n"
        f"Total regions analyzed: {region_count}\n"
        f"Annotated regions: {annotated_count}\n"
        f"Global methylation average: {global_methylation_avg or 'N/A'}\n\n"
        f"Genome-epigenetic overlays:\n{overlay_text or 'None found'}\n\n"
        "Write 3-4 paragraphs explaining what these epigenetic patterns mean "
        "for the user's health, how they interact with their genome variants, "
        "and what lifestyle factors might influence them. Include a disclaimer "
        "that this is informational only and not medical advice."
    )

    try:
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a genetics-literate health communicator. "
                            "Explain epigenetic findings clearly. Always include "
                            "a medical disclaimer."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 2000,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.warning("OpenAI call failed, falling back to template: %s", exc)
        return _generate_template_summary(
            region_count, annotated_count, global_methylation_avg,
            overlays, data_type,
        )


# ── Convenience: full annotation pipeline ─────────────────────────────────────


def annotate_regions(
    regions: list[ParsedRegion],
    client: httpx.Client | None = None,
    assay_type: str | None = None,
    tissue_type: str | None = None,
) -> dict[str, dict]:
    """Run the full annotation pipeline on parsed regions.

    Returns dict keyed by "chrom:start-end" → annotation dict.
    """
    annotations: dict[str, dict] = {}

    # 1. Feature type + nearest gene
    for region in regions:
        key = f"{region.chromosome}:{region.start_pos}-{region.end_pos}"
        feature, gene = annotate_feature_type(region)
        annotations[key] = {
            "feature_type": feature,
            "nearest_gene": gene,
            "encode_experiments": [],
            "roadmap": {},
        }

    # 2. ENCODE query
    if client:
        encode_results = query_encode(regions, client, assay_type)
        for key, exps in encode_results.items():
            if key in annotations:
                annotations[key]["encode_experiments"] = exps

    # 3. Roadmap ChromHMM
    roadmap_results = query_roadmap_chromhmm(regions, tissue_type)
    for key, state_info in roadmap_results.items():
        if key in annotations:
            annotations[key]["roadmap"] = state_info
            # Merge feature/gene from roadmap if we didn't have it
            if not annotations[key]["nearest_gene"] and state_info.get("nearest_gene"):
                annotations[key]["nearest_gene"] = state_info["nearest_gene"]
            if state_info.get("feature_type") and annotations[key]["feature_type"] == "intergenic":
                annotations[key]["feature_type"] = state_info["feature_type"]
            annotations[key]["state"] = state_info.get("state", "")

    return annotations
