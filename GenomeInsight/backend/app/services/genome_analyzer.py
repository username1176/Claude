"""Genome analysis engine.

Orchestrates: VCF parsing → external API annotation → risk scoring →
recommendation generation.  Each stage is broken into testable functions
that the Celery task composes into a pipeline.
"""

from __future__ import annotations

import io
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

# ── Data structures ──────────────────────────────────────────────────────────


@dataclass
class ParsedVariant:
    """A single variant extracted from a VCF file."""

    chromosome: str
    position: int
    rsid: str | None
    ref_allele: str
    alt_allele: str
    genotype: str
    quality: float | None = None


@dataclass
class AnnotationResult:
    """Aggregated annotations for one variant from one or more sources."""

    source: str
    gene_symbol: str | None = None
    consequence: str | None = None
    clinical_significance: str | None = None
    condition_name: str | None = None
    trait_association: str | None = None
    risk_allele: str | None = None
    odds_ratio: float | None = None
    p_value: float | None = None
    pubmed_ids: str | None = None
    source_record_id: str | None = None


@dataclass
class RiskCategory:
    """Scored risk for a single health category."""

    category: str
    label: str  # human-readable
    score: float  # 1-10
    level: str  # low / average / elevated / high
    key_variants: list[dict] = field(default_factory=list)
    summary: str = ""


@dataclass
class Recommendation:
    """A single actionable recommendation."""

    category: str  # diet / exercise / supplement / lifestyle / pharmacogenomic
    title: str
    body: str
    evidence_rsids: str  # comma-separated
    evidence_sources: str  # JSON array
    confidence: str  # low / medium / high
    priority: int  # 1 = highest


# ── VCF Parsing ──────────────────────────────────────────────────────────────

# Well-known genotype encodings
_GT_MAP = {"0/0": "ref/ref", "0/1": "ref/alt", "1/0": "ref/alt", "1/1": "alt/alt"}


def parse_vcf(vcf_bytes: bytes) -> list[ParsedVariant]:
    """Parse a VCF file from raw bytes and return structured variants.

    Handles standard VCF 4.x format as produced by 23andMe, AncestryDNA,
    and clinical sequencing pipelines.  Skips header lines (##) and parses
    the data lines (#CHROM ...).
    """
    variants: list[ParsedVariant] = []
    text = vcf_bytes.decode("utf-8", errors="replace")

    header_cols: list[str] = []
    sample_idx: int | None = None

    for line in io.StringIO(text):
        line = line.strip()
        if not line:
            continue

        # Meta-information lines
        if line.startswith("##"):
            continue

        # Column header line
        if line.startswith("#CHROM") or line.startswith("#chrom"):
            header_cols = line.lstrip("#").split("\t")
            # Find the first sample column (after FORMAT)
            if "FORMAT" in header_cols:
                sample_idx = header_cols.index("FORMAT") + 1
            continue

        parts = line.split("\t")
        if len(parts) < 8:
            continue

        chrom = parts[0]
        try:
            pos = int(parts[1])
        except ValueError:
            continue
        raw_id = parts[2]
        ref = parts[3]
        alt = parts[4]

        # Quality (column 5)
        try:
            qual = float(parts[5]) if parts[5] != "." else None
        except ValueError:
            qual = None

        # rsID
        rsid = raw_id if raw_id.startswith("rs") else None

        # Genotype from sample column
        genotype = "."
        if sample_idx is not None and len(parts) > sample_idx:
            fmt_fields = parts[header_cols.index("FORMAT")].split(":") if "FORMAT" in header_cols else []
            sample_fields = parts[sample_idx].split(":")
            if fmt_fields and fmt_fields[0] == "GT" and sample_fields:
                gt_raw = sample_fields[0].replace("|", "/")
                genotype = gt_raw
        elif len(parts) >= 10:
            # Fallback: assume columns 8=FORMAT, 9=SAMPLE
            fmt = parts[8].split(":")
            sample = parts[9].split(":")
            if fmt and fmt[0] == "GT" and sample:
                genotype = sample[0].replace("|", "/")

        # Handle multi-allelic ALTs — split and create one variant per ALT
        for alt_allele in alt.split(","):
            alt_allele = alt_allele.strip()
            if alt_allele in (".", ""):
                continue
            variants.append(
                ParsedVariant(
                    chromosome=chrom,
                    position=pos,
                    rsid=rsid,
                    ref_allele=ref,
                    alt_allele=alt_allele,
                    genotype=genotype,
                    quality=qual,
                )
            )

    logger.info("Parsed %d variants from VCF", len(variants))
    return variants


def detect_genome_build(vcf_bytes: bytes) -> str:
    """Detect genome build (GRCh37 / GRCh38) from VCF header lines."""
    header = vcf_bytes[:8192].decode("utf-8", errors="replace")
    for line in header.split("\n"):
        lower = line.lower()
        if "grch38" in lower or "hg38" in lower:
            return "GRCh38"
        if "grch37" in lower or "hg19" in lower:
            return "GRCh37"
    # Default assumption for consumer genotyping services
    return "GRCh37"


# ── External API Clients ─────────────────────────────────────────────────────

# Shared HTTP client config
_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
_RETRY_STATUSES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3


def _request_with_retry(
    client: httpx.Client,
    method: str,
    url: str,
    **kwargs,
) -> httpx.Response | None:
    """HTTP request with exponential backoff on transient failures."""
    for attempt in range(_MAX_RETRIES):
        try:
            resp = client.request(method, url, **kwargs)
            if resp.status_code not in _RETRY_STATUSES:
                return resp
            logger.warning(
                "API %s %s returned %d (attempt %d/%d)",
                method, url, resp.status_code, attempt + 1, _MAX_RETRIES,
            )
        except httpx.TransportError as exc:
            logger.warning(
                "API %s %s transport error: %s (attempt %d/%d)",
                method, url, exc, attempt + 1, _MAX_RETRIES,
            )
        if attempt < _MAX_RETRIES - 1:
            time.sleep(2 ** attempt)  # 1s, 2s, 4s
    return None


# ── Ensembl VEP ──────────────────────────────────────────────────────────────


def query_ensembl_vep(
    variants: list[ParsedVariant],
    client: httpx.Client,
    genome_build: str = "GRCh37",
) -> dict[str, list[AnnotationResult]]:
    """Query Ensembl VEP for variant consequences.

    Batches variants in groups of 200 (Ensembl's limit) using the POST
    endpoint.

    Returns:
        Mapping of "chrom:pos:ref:alt" → list of AnnotationResult.

    Example single-variant GET (for reference):
        GET https://rest.ensembl.org/vep/human/region/1:230710048:230710048/C
            ?content-type=application/json
    """
    base_url = (
        "https://rest.ensembl.org"
        if genome_build == "GRCh38"
        else "https://grch37.rest.ensembl.org"
    )
    endpoint = f"{base_url}/vep/human/region"
    results: dict[str, list[AnnotationResult]] = {}

    # Build VEP input strings: "chrom pos pos allele_string strand"
    vep_inputs: list[tuple[str, str]] = []
    for v in variants:
        key = f"{v.chromosome}:{v.position}:{v.ref_allele}:{v.alt_allele}"
        vep_str = f"{v.chromosome} {v.position} {v.position} {v.ref_allele}/{v.alt_allele} 1"
        vep_inputs.append((key, vep_str))

    # Batch in groups of 200
    batch_size = 200
    for i in range(0, len(vep_inputs), batch_size):
        batch = vep_inputs[i : i + batch_size]
        payload = {"variants": [vep_str for _, vep_str in batch]}
        key_lookup = {vep_str: key for key, vep_str in batch}

        resp = _request_with_retry(
            client,
            "POST",
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        if resp is None or resp.status_code != 200:
            logger.error("Ensembl VEP batch %d failed", i // batch_size)
            continue

        try:
            data = resp.json()
        except Exception:
            continue

        for entry in data:
            # Reconstruct the key from the input field
            input_str = entry.get("input", "")
            key = key_lookup.get(input_str, input_str)

            for tc in entry.get("transcript_consequences", []):
                annotation = AnnotationResult(
                    source="ensembl",
                    gene_symbol=tc.get("gene_symbol"),
                    consequence=", ".join(tc.get("consequence_terms", [])),
                    clinical_significance=None,
                )
                # SIFT / PolyPhen predictions
                sift = tc.get("sift_prediction")
                polyphen = tc.get("polyphen_prediction")
                if sift or polyphen:
                    parts = []
                    if sift:
                        parts.append(f"SIFT: {sift}")
                    if polyphen:
                        parts.append(f"PolyPhen: {polyphen}")
                    annotation.trait_association = "; ".join(parts)

                results.setdefault(key, []).append(annotation)

    logger.info("Ensembl VEP annotated %d variant keys", len(results))
    return results


# ── ClinVar via NCBI E-Utilities ─────────────────────────────────────────────


def query_clinvar(
    rsids: list[str],
    client: httpx.Client,
    ncbi_api_key: str = "",
) -> dict[str, list[AnnotationResult]]:
    """Query ClinVar for clinical significance of rsIDs.

    Uses NCBI E-Utilities:
        1. esearch to find ClinVar UIDs for each rsID
        2. esummary to get clinical details

    Example:
        GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi
            ?db=clinvar&term=rs1801133&retmode=json
        GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi
            ?db=clinvar&id=38153&retmode=json
    """
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    results: dict[str, list[AnnotationResult]] = {}
    params_base = {}
    if ncbi_api_key:
        params_base["api_key"] = ncbi_api_key

    for rsid in rsids:
        # Step 1: search ClinVar for this rsID
        search_params = {
            **params_base,
            "db": "clinvar",
            "term": f"{rsid}[variant name]",
            "retmode": "json",
            "retmax": "5",
        }
        resp = _request_with_retry(client, "GET", f"{base}/esearch.fcgi", params=search_params)
        if resp is None or resp.status_code != 200:
            continue

        try:
            search_data = resp.json()
        except Exception:
            continue

        uid_list = search_data.get("esearchresult", {}).get("idlist", [])
        if not uid_list:
            continue

        # Step 2: fetch summary for each UID
        summary_params = {
            **params_base,
            "db": "clinvar",
            "id": ",".join(uid_list),
            "retmode": "json",
        }
        resp = _request_with_retry(client, "GET", f"{base}/esummary.fcgi", params=summary_params)
        if resp is None or resp.status_code != 200:
            continue

        try:
            summary_data = resp.json()
        except Exception:
            continue

        for uid in uid_list:
            entry = summary_data.get("result", {}).get(uid, {})
            if not entry or isinstance(entry, list):
                continue

            # Extract clinical significance
            clin_sig = entry.get("clinical_significance", {})
            if isinstance(clin_sig, dict):
                significance = clin_sig.get("description", "")
            else:
                significance = str(clin_sig) if clin_sig else ""

            # Extract condition/trait
            trait_set = entry.get("trait_set", [])
            conditions = []
            if isinstance(trait_set, list):
                for trait in trait_set:
                    name = trait.get("trait_name", "") if isinstance(trait, dict) else ""
                    if name:
                        conditions.append(name)

            genes = entry.get("genes", [])
            gene_symbol = None
            if isinstance(genes, list) and genes:
                gene_symbol = genes[0].get("symbol") if isinstance(genes[0], dict) else None

            annotation = AnnotationResult(
                source="clinvar",
                gene_symbol=gene_symbol,
                clinical_significance=significance,
                condition_name="; ".join(conditions) if conditions else None,
                source_record_id=str(uid),
            )
            results.setdefault(rsid, []).append(annotation)

        # Rate limit: NCBI allows 3 req/s without key, 10/s with key
        time.sleep(0.15 if ncbi_api_key else 0.4)

    logger.info("ClinVar annotated %d rsIDs", len(results))
    return results


# ── GWAS Catalog ─────────────────────────────────────────────────────────────


def query_gwas_catalog(
    rsids: list[str],
    client: httpx.Client,
) -> dict[str, list[AnnotationResult]]:
    """Query NHGRI-EBI GWAS Catalog for trait associations.

    Example:
        GET https://www.ebi.ac.uk/gwas/rest/api/singleNucleotidePolymorphisms/
            rs1801133/associations
    """
    base = "https://www.ebi.ac.uk/gwas/rest/api/singleNucleotidePolymorphisms"
    results: dict[str, list[AnnotationResult]] = {}

    for rsid in rsids:
        url = f"{base}/{rsid}/associations"
        resp = _request_with_retry(client, "GET", url)
        if resp is None or resp.status_code != 200:
            continue

        try:
            data = resp.json()
        except Exception:
            continue

        associations = data.get("_embedded", {}).get("associations", [])
        for assoc in associations:
            # Odds ratio / beta
            or_val = assoc.get("orPerCopyNum")
            odds_ratio = float(or_val) if or_val else None

            p_val_mantissa = assoc.get("pvalueMantissa")
            p_val_exponent = assoc.get("pvalueExponent")
            p_value = None
            if p_val_mantissa is not None and p_val_exponent is not None:
                try:
                    p_value = float(p_val_mantissa) * (10 ** int(p_val_exponent))
                except (ValueError, TypeError):
                    pass

            # Filter to genome-wide significant only
            if p_value is not None and p_value > 5e-8:
                continue

            # Risk allele
            risk_alleles = assoc.get("riskAlleles", [])
            risk_allele = None
            if risk_alleles and isinstance(risk_alleles[0], dict):
                risk_allele = risk_alleles[0].get("riskAlleleName", "")
                if "-" in (risk_allele or ""):
                    risk_allele = risk_allele.split("-")[-1]

            # Trait name
            ef_traits = assoc.get("efoTraits", [])
            trait_name = None
            if ef_traits and isinstance(ef_traits[0], dict):
                trait_name = ef_traits[0].get("trait")

            annotation = AnnotationResult(
                source="gwas_catalog",
                trait_association=trait_name,
                risk_allele=risk_allele,
                odds_ratio=odds_ratio,
                p_value=p_value,
            )
            results.setdefault(rsid, []).append(annotation)

        time.sleep(0.2)  # Be a good API citizen

    logger.info("GWAS Catalog annotated %d rsIDs", len(results))
    return results


# ── NCBI Gene Info ───────────────────────────────────────────────────────────


def query_ncbi_gene(
    gene_symbols: list[str],
    client: httpx.Client,
    ncbi_api_key: str = "",
) -> dict[str, str]:
    """Fetch gene summary descriptions from NCBI Gene database.

    Example:
        GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi
            ?db=gene&term=CYP1A2[sym]+AND+human[orgn]&retmode=json
        GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi
            ?db=gene&id=1544&retmode=json
    """
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    summaries: dict[str, str] = {}
    params_base = {}
    if ncbi_api_key:
        params_base["api_key"] = ncbi_api_key

    for symbol in gene_symbols[:50]:  # Limit to avoid excessive calls
        search_params = {
            **params_base,
            "db": "gene",
            "term": f"{symbol}[sym] AND human[orgn]",
            "retmode": "json",
            "retmax": "1",
        }
        resp = _request_with_retry(client, "GET", f"{base}/esearch.fcgi", params=search_params)
        if resp is None or resp.status_code != 200:
            continue

        try:
            ids = resp.json().get("esearchresult", {}).get("idlist", [])
        except Exception:
            continue

        if not ids:
            continue

        summary_params = {
            **params_base,
            "db": "gene",
            "id": ids[0],
            "retmode": "json",
        }
        resp = _request_with_retry(client, "GET", f"{base}/esummary.fcgi", params=summary_params)
        if resp is None or resp.status_code != 200:
            continue

        try:
            entry = resp.json().get("result", {}).get(ids[0], {})
            desc = entry.get("summary", "")
            if desc:
                summaries[symbol] = desc
        except Exception:
            continue

        time.sleep(0.15 if ncbi_api_key else 0.4)

    logger.info("NCBI Gene fetched summaries for %d genes", len(summaries))
    return summaries


# ── Risk Scoring ─────────────────────────────────────────────────────────────

# Maps rsIDs to risk categories with base weights.
# In production, this would be a much larger curated database.
VARIANT_CATEGORY_MAP: dict[str, list[dict]] = {
    # Cardiovascular
    "rs10757274": [{"category": "cardiovascular", "weight": 1.3, "note": "9p21.3 CAD risk locus"}],
    "rs4420638": [{"category": "cardiovascular", "weight": 1.2, "note": "APOE region, lipid metabolism"}],
    "rs429358": [
        {"category": "cardiovascular", "weight": 1.4, "note": "APOE ε4 allele"},
        {"category": "neurological", "weight": 1.6, "note": "APOE ε4 Alzheimer risk"},
    ],
    "rs7412": [{"category": "cardiovascular", "weight": 0.8, "note": "APOE ε2 — protective"}],
    # Metabolic / Diabetes
    "rs7903146": [{"category": "metabolic", "weight": 1.4, "note": "TCF7L2 — strongest T2D risk"}],
    "rs13266634": [{"category": "metabolic", "weight": 1.1, "note": "SLC30A8 zinc transporter"}],
    "rs9939609": [{"category": "metabolic", "weight": 1.2, "note": "FTO obesity risk"}],
    # Pharmacogenomic
    "rs762551": [{"category": "pharmacogenomic", "weight": 1.0, "note": "CYP1A2 caffeine metabolism"}],
    "rs1065852": [{"category": "pharmacogenomic", "weight": 1.0, "note": "CYP2D6 drug metabolism"}],
    "rs4244285": [{"category": "pharmacogenomic", "weight": 1.0, "note": "CYP2C19 clopidogrel response"}],
    # Nutritional
    "rs1801133": [{"category": "nutritional", "weight": 1.3, "note": "MTHFR C677T folate metabolism"}],
    "rs174546": [{"category": "nutritional", "weight": 1.1, "note": "FADS1 omega-3 conversion"}],
    "rs4988235": [{"category": "nutritional", "weight": 1.0, "note": "LCT lactose tolerance"}],
    "rs602662": [{"category": "nutritional", "weight": 1.0, "note": "FUT2 vitamin B12 absorption"}],
    # Inflammatory
    "rs1800795": [{"category": "inflammatory", "weight": 1.2, "note": "IL-6 promoter"}],
    "rs1800629": [{"category": "inflammatory", "weight": 1.2, "note": "TNF-α promoter"}],
    # Neurological
    "rs6265": [{"category": "neurological", "weight": 1.1, "note": "BDNF Val66Met"}],
    "rs4680": [{"category": "neurological", "weight": 1.0, "note": "COMT Val158Met — stress response"}],
    # Sleep / Circadian
    "rs1801260": [{"category": "sleep", "weight": 1.0, "note": "CLOCK gene — circadian rhythm"}],
    "rs73598374": [{"category": "sleep", "weight": 1.0, "note": "ADA — deep sleep"}],
    # Caffeine
    "rs5751876": [{"category": "pharmacogenomic", "weight": 1.0, "note": "ADORA2A caffeine sensitivity"}],
}

CATEGORY_LABELS = {
    "cardiovascular": "Cardiovascular Health",
    "metabolic": "Metabolic / Diabetes Risk",
    "pharmacogenomic": "Pharmacogenomics (Drug Response)",
    "nutritional": "Nutritional Metabolism",
    "inflammatory": "Inflammation & Immune",
    "neurological": "Neurological & Cognitive",
    "sleep": "Sleep & Circadian Rhythm",
}


def _score_to_level(score: float) -> str:
    if score <= 3.0:
        return "low"
    if score <= 5.0:
        return "average"
    if score <= 7.0:
        return "elevated"
    return "high"


def score_risks(
    variants: list[ParsedVariant],
    annotations: dict[str, list[AnnotationResult]],
) -> list[RiskCategory]:
    """Compute per-category risk scores from parsed variants and annotations.

    Scoring heuristic:
    - Base score 3.0 per category (population average).
    - Bump up/down based on variant weights, genotype (homozygous = 2×),
      and clinical significance from ClinVar/GWAS.
    """
    category_scores: dict[str, float] = {}
    category_variants: dict[str, list[dict]] = {}

    for v in variants:
        if not v.rsid:
            continue

        mappings = VARIANT_CATEGORY_MAP.get(v.rsid, [])
        # Also consider ClinVar pathogenic variants
        variant_annotations = annotations.get(v.rsid, [])
        for ann in variant_annotations:
            if ann.source == "clinvar" and ann.clinical_significance:
                sig_lower = ann.clinical_significance.lower()
                if "pathogenic" in sig_lower:
                    for mapping in mappings:
                        mapping = {**mapping, "weight": mapping["weight"] * 1.5}

        for mapping in mappings:
            cat = mapping["category"]
            weight = mapping["weight"]

            # Homozygous alt = stronger effect
            gt_multiplier = 1.0
            if v.genotype in ("1/1",):
                gt_multiplier = 1.5
            elif v.genotype in ("0/1", "1/0"):
                gt_multiplier = 1.0
            elif v.genotype in ("0/0",):
                gt_multiplier = 0.0  # Reference homozygous — no risk contribution

            contribution = weight * gt_multiplier

            category_scores.setdefault(cat, 3.0)  # Base score
            category_scores[cat] += contribution

            if gt_multiplier > 0:
                category_variants.setdefault(cat, []).append(
                    {
                        "rsid": v.rsid,
                        "genotype": v.genotype,
                        "note": mapping["note"],
                        "contribution": round(contribution, 2),
                    }
                )

    # Clamp scores to 1–10
    risk_categories = []
    for cat, raw_score in category_scores.items():
        score = max(1.0, min(10.0, raw_score))
        risk_categories.append(
            RiskCategory(
                category=cat,
                label=CATEGORY_LABELS.get(cat, cat.title()),
                score=round(score, 1),
                level=_score_to_level(score),
                key_variants=category_variants.get(cat, []),
            )
        )

    risk_categories.sort(key=lambda r: r.score, reverse=True)
    logger.info("Scored %d risk categories", len(risk_categories))
    return risk_categories


# ── Recommendation Engine ────────────────────────────────────────────────────

# Curated recommendation rules: rsID → recommendation template.
# Each rule fires when the variant is present with a non-reference genotype.
RECOMMENDATION_RULES: list[dict] = [
    {
        "rsids": ["rs762551"],
        "genotypes_trigger": ["0/1", "1/0", "1/1"],
        "category": "lifestyle",
        "title": "Reduce caffeine intake",
        "body": (
            "Your CYP1A2 variant (rs762551) indicates slow caffeine metabolism. "
            "Slow metabolizers have higher circulating caffeine levels, which is "
            "associated with increased cardiovascular risk with high intake. "
            "Consider limiting coffee to 1-2 cups per day and avoiding caffeine "
            "after noon."
        ),
        "confidence": "high",
        "priority": 2,
    },
    {
        "rsids": ["rs1801133"],
        "genotypes_trigger": ["0/1", "1/0", "1/1"],
        "category": "supplement",
        "title": "Consider methylfolate supplementation",
        "body": (
            "Your MTHFR C677T variant (rs1801133) reduces conversion of folic "
            "acid to its active form (methylfolate) by ~30-70%. Consider a "
            "methylfolate supplement (400-800 mcg/day) and increasing dietary "
            "folate from leafy greens, legumes, and fortified foods."
        ),
        "confidence": "high",
        "priority": 2,
    },
    {
        "rsids": ["rs174546"],
        "genotypes_trigger": ["0/1", "1/0", "1/1"],
        "category": "supplement",
        "title": "Consider omega-3 (EPA/DHA) supplementation",
        "body": (
            "Your FADS1 variant (rs174546) suggests reduced ability to convert "
            "plant-based ALA to EPA and DHA. Direct sources of omega-3 — fatty "
            "fish (salmon, sardines) 2-3 times per week or a fish oil supplement "
            "(1-2g EPA+DHA daily) — may be particularly beneficial for you."
        ),
        "confidence": "medium",
        "priority": 3,
    },
    {
        "rsids": ["rs429358"],
        "genotypes_trigger": ["0/1", "1/0", "1/1"],
        "category": "diet",
        "title": "Adopt a Mediterranean-style diet",
        "body": (
            "As an APOE ε4 carrier (rs429358), you may be more sensitive to "
            "dietary saturated fat. A Mediterranean diet rich in olive oil, "
            "vegetables, fish, and whole grains has shown particular benefits "
            "for APOE ε4 carriers in reducing cardiovascular and cognitive risk."
        ),
        "confidence": "high",
        "priority": 1,
    },
    {
        "rsids": ["rs9939609"],
        "genotypes_trigger": ["0/1", "1/0", "1/1"],
        "category": "exercise",
        "title": "Prioritize regular physical activity",
        "body": (
            "Your FTO variant (rs9939609) is associated with increased appetite "
            "and higher BMI risk. Research shows that regular exercise (150+ "
            "minutes moderate activity per week) can significantly offset FTO-"
            "related weight gain. Resistance training is particularly effective."
        ),
        "confidence": "high",
        "priority": 2,
    },
    {
        "rsids": ["rs7903146"],
        "genotypes_trigger": ["0/1", "1/0", "1/1"],
        "category": "diet",
        "title": "Increase dietary fiber for blood sugar management",
        "body": (
            "Your TCF7L2 variant (rs7903146) is one of the strongest genetic "
            "risk factors for type 2 diabetes. Prioritize high-fiber foods "
            "(30+ g/day from vegetables, legumes, whole grains), limit refined "
            "carbohydrates, and monitor blood glucose periodically."
        ),
        "confidence": "high",
        "priority": 1,
    },
    {
        "rsids": ["rs4988235"],
        "genotypes_trigger": ["1/1"],
        "category": "diet",
        "title": "You likely tolerate lactose well",
        "body": (
            "Your LCT variant (rs4988235) is associated with lactase persistence "
            "— you likely produce lactase into adulthood and can digest dairy "
            "without issues. Dairy can be a good source of calcium and protein."
        ),
        "confidence": "high",
        "priority": 8,
    },
    {
        "rsids": ["rs1800795", "rs1800629"],
        "genotypes_trigger": ["0/1", "1/0", "1/1"],
        "category": "lifestyle",
        "title": "Focus on anti-inflammatory lifestyle practices",
        "body": (
            "Your IL-6 and/or TNF-α variants suggest a tendency toward elevated "
            "inflammatory markers. Anti-inflammatory strategies include: omega-3 "
            "fatty acids, turmeric/curcumin, regular moderate exercise, stress "
            "management (meditation, yoga), and adequate sleep (7-9 hours)."
        ),
        "confidence": "medium",
        "priority": 3,
    },
    {
        "rsids": ["rs4680"],
        "genotypes_trigger": ["0/1", "1/0", "1/1"],
        "category": "lifestyle",
        "title": "Manage stress with structured practices",
        "body": (
            "Your COMT Val158Met variant (rs4680) affects dopamine metabolism in "
            "the prefrontal cortex. Depending on your genotype, you may benefit "
            "from structured stress management — consider 10-15 minutes of daily "
            "meditation, regular exercise, and ensuring adequate magnesium intake."
        ),
        "confidence": "medium",
        "priority": 4,
    },
    {
        "rsids": ["rs1801260", "rs73598374"],
        "genotypes_trigger": ["0/1", "1/0", "1/1"],
        "category": "lifestyle",
        "title": "Optimize your sleep environment and schedule",
        "body": (
            "Variants in your circadian rhythm genes (CLOCK, ADA) may affect "
            "sleep quality. Maintain a consistent sleep schedule, limit blue "
            "light 1 hour before bed, keep your bedroom cool (65-68°F / 18-20°C), "
            "and consider morning sunlight exposure to anchor your circadian clock."
        ),
        "confidence": "medium",
        "priority": 5,
    },
]


def generate_recommendations(
    variants: list[ParsedVariant],
) -> list[Recommendation]:
    """Generate actionable health recommendations based on detected variants."""
    # Build lookup: rsid → ParsedVariant
    rsid_to_variant: dict[str, ParsedVariant] = {}
    for v in variants:
        if v.rsid:
            rsid_to_variant[v.rsid] = v

    recommendations: list[Recommendation] = []
    seen_titles: set[str] = set()

    for rule in RECOMMENDATION_RULES:
        triggered_rsids = []
        for rsid in rule["rsids"]:
            v = rsid_to_variant.get(rsid)
            if v and v.genotype in rule["genotypes_trigger"]:
                triggered_rsids.append(rsid)

        if not triggered_rsids:
            continue

        # Avoid duplicate recommendations
        if rule["title"] in seen_titles:
            continue
        seen_titles.add(rule["title"])

        recommendations.append(
            Recommendation(
                category=rule["category"],
                title=rule["title"],
                body=rule["body"],
                evidence_rsids=",".join(triggered_rsids),
                evidence_sources=json.dumps(
                    [{"source": "curated_rules", "rsids": triggered_rsids}]
                ),
                confidence=rule["confidence"],
                priority=rule["priority"],
            )
        )

    recommendations.sort(key=lambda r: r.priority)
    logger.info("Generated %d recommendations", len(recommendations))
    return recommendations
