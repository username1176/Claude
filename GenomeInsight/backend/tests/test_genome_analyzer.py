"""Tests for the genome analyzer: VCF parsing, risk scoring, recommendations."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.services.genome_analyzer import (
    AnnotationResult,
    ParsedVariant,
    detect_genome_build,
    generate_recommendations,
    parse_vcf,
    score_risks,
)

FIXTURES = Path(__file__).parent / "fixtures"


# ── VCF Parsing ──────────────────────────────────────────────────────────────


def test_parse_vcf_sample_file():
    vcf_bytes = (FIXTURES / "sample.vcf").read_bytes()
    variants = parse_vcf(vcf_bytes)

    assert len(variants) == 11

    # Check a specific variant
    rs1801133 = [v for v in variants if v.rsid == "rs1801133"]
    assert len(rs1801133) == 1
    v = rs1801133[0]
    assert v.chromosome == "1"
    assert v.position == 230710048
    assert v.ref_allele == "C"
    assert v.alt_allele == "T"
    assert v.genotype == "0/1"
    assert v.quality == 99.0


def test_parse_vcf_extracts_all_rsids():
    vcf_bytes = (FIXTURES / "sample.vcf").read_bytes()
    variants = parse_vcf(vcf_bytes)
    rsids = {v.rsid for v in variants if v.rsid}

    expected = {
        "rs1801133", "rs762551", "rs174546", "rs9939609",
        "rs7903146", "rs429358", "rs4988235", "rs1800795",
        "rs4680", "rs10757274", "rs1800629",
    }
    assert rsids == expected


def test_parse_vcf_handles_homozygous():
    vcf_bytes = (FIXTURES / "sample.vcf").read_bytes()
    variants = parse_vcf(vcf_bytes)
    rs174546 = [v for v in variants if v.rsid == "rs174546"][0]
    assert rs174546.genotype == "1/1"


def test_parse_vcf_empty_returns_empty():
    vcf_bytes = b"##fileformat=VCFv4.1\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
    variants = parse_vcf(vcf_bytes)
    assert variants == []


def test_parse_vcf_skips_malformed_lines():
    vcf_bytes = (
        b"##fileformat=VCFv4.1\n"
        b"#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\n"
        b"1\tnot_a_number\trs123\tA\tT\t99\tPASS\t.\tGT\t0/1\n"
        b"1\t100\trs456\tA\tG\t99\tPASS\t.\tGT\t0/1\n"
    )
    variants = parse_vcf(vcf_bytes)
    assert len(variants) == 1
    assert variants[0].rsid == "rs456"


def test_parse_vcf_handles_multiallelic():
    vcf_bytes = (
        b"##fileformat=VCFv4.1\n"
        b"#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\n"
        b"1\t100\trs789\tA\tG,T\t99\tPASS\t.\tGT\t0/1\n"
    )
    variants = parse_vcf(vcf_bytes)
    assert len(variants) == 2
    assert variants[0].alt_allele == "G"
    assert variants[1].alt_allele == "T"


# ── Genome Build Detection ──────────────────────────────────────────────────


def test_detect_grch37():
    vcf = b"##fileformat=VCFv4.1\n##reference=GRCh37\n"
    assert detect_genome_build(vcf) == "GRCh37"


def test_detect_grch38():
    vcf = b"##fileformat=VCFv4.1\n##reference=GRCh38\n"
    assert detect_genome_build(vcf) == "GRCh38"


def test_detect_hg19():
    vcf = b"##fileformat=VCFv4.1\n##assembly=hg19\n"
    assert detect_genome_build(vcf) == "GRCh37"


def test_detect_default():
    vcf = b"##fileformat=VCFv4.1\n"
    assert detect_genome_build(vcf) == "GRCh37"


# ── Risk Scoring ─────────────────────────────────────────────────────────────


def _make_variants() -> list[ParsedVariant]:
    return [
        ParsedVariant("1", 230710048, "rs1801133", "C", "T", "0/1", 99.0),
        ParsedVariant("10", 94781859, "rs762551", "A", "C", "0/1", 99.0),
        ParsedVariant("16", 53820527, "rs9939609", "T", "A", "0/1", 99.0),
        ParsedVariant("9", 22125503, "rs10757274", "G", "A", "1/1", 99.0),
        ParsedVariant("19", 45411941, "rs429358", "T", "C", "0/1", 99.0),
        ParsedVariant("6", 31543031, "rs1800629", "G", "A", "0/0", 99.0),  # ref/ref — no contribution
    ]


def test_score_risks_produces_categories():
    variants = _make_variants()
    categories = score_risks(variants, {})

    cat_names = {rc.category for rc in categories}
    assert "cardiovascular" in cat_names
    assert "nutritional" in cat_names
    assert "pharmacogenomic" in cat_names


def test_score_risks_homozygous_scores_higher():
    het = [ParsedVariant("9", 22125503, "rs10757274", "G", "A", "0/1")]
    hom = [ParsedVariant("9", 22125503, "rs10757274", "G", "A", "1/1")]

    het_scores = score_risks(het, {})
    hom_scores = score_risks(hom, {})

    het_cardio = next((r for r in het_scores if r.category == "cardiovascular"), None)
    hom_cardio = next((r for r in hom_scores if r.category == "cardiovascular"), None)
    assert het_cardio is not None and hom_cardio is not None
    assert hom_cardio.score > het_cardio.score


def test_score_risks_reference_genotype_no_contribution():
    variants = [ParsedVariant("6", 31543031, "rs1800629", "G", "A", "0/0")]
    categories = score_risks(variants, {})
    # 0/0 genotype should not contribute — no category created or base score only
    inflammatory = [r for r in categories if r.category == "inflammatory"]
    # Either no category at all, or score is at baseline (3.0)
    if inflammatory:
        assert inflammatory[0].score == 3.0


def test_score_risks_level_mapping():
    from app.services.genome_analyzer import _score_to_level

    assert _score_to_level(2.0) == "low"
    assert _score_to_level(3.5) == "average"
    assert _score_to_level(6.0) == "elevated"
    assert _score_to_level(8.0) == "high"


# ── Recommendations ──────────────────────────────────────────────────────────


def test_generate_recommendations_fires_matching_rules():
    variants = _make_variants()
    recs = generate_recommendations(variants)

    titles = {r.title for r in recs}
    assert "Reduce caffeine intake" in titles
    assert "Consider methylfolate supplementation" in titles
    assert "Prioritize regular physical activity" in titles
    assert "Adopt a Mediterranean-style diet" in titles


def test_generate_recommendations_respects_genotype():
    # rs1800629 is 0/0 in our fixture — the anti-inflammatory rule requires non-ref
    variants = [ParsedVariant("6", 31543031, "rs1800629", "G", "A", "0/0")]
    recs = generate_recommendations(variants)
    titles = {r.title for r in recs}
    # Should NOT fire — only has ref genotype
    assert "Focus on anti-inflammatory lifestyle practices" not in titles


def test_generate_recommendations_priority_order():
    variants = _make_variants()
    recs = generate_recommendations(variants)
    priorities = [r.priority for r in recs]
    assert priorities == sorted(priorities)


def test_generate_recommendations_no_duplicates():
    variants = _make_variants()
    recs = generate_recommendations(variants)
    titles = [r.title for r in recs]
    assert len(titles) == len(set(titles))
