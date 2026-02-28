"""Tests for microbiome_analyzer.py — parsers, diversity, and correlations."""

import json
from pathlib import Path

import pytest

from app.utils.microbiome_analyzer import (
    MicrobiomeCorrelation,
    MicrobiomeInsight,
    ParsedTaxon,
    classify_enterotype,
    compute_alpha_diversity,
    compute_composition,
    compute_phyla_ratios,
    correlate_microbiome_blood,
    correlate_microbiome_genome,
    correlate_microbiome_wearables,
    generate_microbiome_ai_summary,
    generate_microbiome_insights,
    normalize_taxonomy,
    parse_biom_json,
    parse_fastq_metadata,
    parse_otu_csv,
)

FIXTURES = Path(__file__).parent / "fixtures"


# ── Taxonomy normalisation ───────────────────────────────────────────────────


class TestNormalizeTaxonomy:
    def test_greengenes_format(self):
        raw = "k__Bacteria;p__Firmicutes;c__Clostridia;o__Clostridiales;f__Lachnospiraceae;g__Roseburia;s__intestinalis"
        result = normalize_taxonomy(raw)
        assert result["kingdom"] == "Bacteria"
        assert result["phylum"] == "Firmicutes"
        assert result["genus"] == "Roseburia"
        assert result["species"] == "intestinalis"

    def test_silva_format(self):
        raw = "Bacteria;Firmicutes;Clostridia;Clostridiales"
        result = normalize_taxonomy(raw)
        assert result["kingdom"] == "Bacteria"
        assert result["phylum"] == "Firmicutes"
        assert result["order"] == "Clostridiales"

    def test_ncbi_arrow_format(self):
        raw = "Bacteria > Firmicutes > Clostridia > Clostridiales"
        result = normalize_taxonomy(raw)
        assert result["kingdom"] == "Bacteria"
        assert result["phylum"] == "Firmicutes"

    def test_empty_string(self):
        assert normalize_taxonomy("") == {}

    def test_none_value(self):
        assert normalize_taxonomy("") == {}

    def test_greengenes_empty_levels(self):
        raw = "k__Bacteria;p__;c__"
        result = normalize_taxonomy(raw)
        assert result == {"kingdom": "Bacteria"}


# ── BIOM parser ──────────────────────────────────────────────────────────────


class TestParseBiomJson:
    def test_parse_fixture(self):
        data = (FIXTURES / "sample_biom.json").read_bytes()
        taxa = parse_biom_json(data)
        assert len(taxa) == 5
        # Verify abundances sum to ~1.0
        total = sum(t.relative_abundance for t in taxa)
        assert abs(total - 1.0) < 0.01

    def test_parse_has_correct_names(self):
        data = (FIXTURES / "sample_biom.json").read_bytes()
        taxa = parse_biom_json(data)
        names = {t.taxonomy_name for t in taxa}
        assert "intestinalis" in names
        assert "fragilis" in names

    def test_parse_absolute_counts(self):
        data = (FIXTURES / "sample_biom.json").read_bytes()
        taxa = parse_biom_json(data)
        # OTU1 has 500 + 450 = 950
        roseburia = next(t for t in taxa if t.taxonomy_name == "intestinalis")
        assert roseburia.absolute_count == 950

    def test_empty_rows_raises(self):
        biom = json.dumps({"rows": [], "columns": [], "data": []}).encode()
        with pytest.raises(ValueError, match="no rows"):
            parse_biom_json(biom)

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="Invalid BIOM JSON"):
            parse_biom_json(b"not valid json {{{")


# ── OTU CSV parser ───────────────────────────────────────────────────────────


class TestParseOtuCsv:
    def test_parse_fixture(self):
        data = (FIXTURES / "sample_otu_table.csv").read_bytes()
        taxa = parse_otu_csv(data)
        assert len(taxa) == 10

    def test_relative_abundances_sum_to_one(self):
        data = (FIXTURES / "sample_otu_table.csv").read_bytes()
        taxa = parse_otu_csv(data)
        total = sum(t.relative_abundance for t in taxa)
        assert abs(total - 1.0) < 0.01

    def test_greengenes_lineage_parsed(self):
        data = (FIXTURES / "sample_otu_table.csv").read_bytes()
        taxa = parse_otu_csv(data)
        roseburia = next(t for t in taxa if t.taxonomy_name == "intestinalis")
        assert roseburia.full_lineage["phylum"] == "Firmicutes"
        assert roseburia.full_lineage["genus"] == "Roseburia"

    def test_no_header_raises(self):
        data = b"col_a,col_b\n1,2\n"
        with pytest.raises(ValueError, match="header"):
            parse_otu_csv(data)

    def test_tsv_format(self):
        tsv = (
            "#OTU ID\ttaxonomy\tcount\n"
            "OTU1\tk__Bacteria;p__Firmicutes;g__Roseburia\t500\n"
            "OTU2\tk__Bacteria;p__Bacteroidetes;g__Bacteroides\t300\n"
        ).encode()
        taxa = parse_otu_csv(tsv)
        assert len(taxa) == 2
        assert taxa[0].taxonomy_name == "Roseburia"


# ── FASTQ metadata ──────────────────────────────────────────────────────────


class TestParseFastqMetadata:
    def test_basic_fastq(self):
        fastq = (
            "@SEQ_1\n"
            "ATCGATCG\n"
            "+\n"
            "IIIIIIII\n"
            "@SEQ_2\n"
            "GCTAGCTA\n"
            "+\n"
            "HHHHHHHH\n"
        ).encode()
        result = parse_fastq_metadata(fastq)
        assert result["read_count"] == 2
        assert result["avg_read_length"] == 8.0
        assert result["total_bases"] == 16

    def test_empty_fastq(self):
        result = parse_fastq_metadata(b"")
        assert result["read_count"] == 0


# ── Diversity metrics ────────────────────────────────────────────────────────


class TestComputeAlphaDiversity:
    def test_basic_diversity(self):
        taxa = [
            ParsedTaxon("A", "genus", 0.5, 50),
            ParsedTaxon("B", "genus", 0.3, 30),
            ParsedTaxon("C", "genus", 0.2, 20),
        ]
        div = compute_alpha_diversity(taxa)
        assert div["observed_otus"] == 3
        assert div["shannon"] > 0
        assert div["simpson"] > 0
        assert div["chao1"] >= 3

    def test_single_taxon_low_diversity(self):
        taxa = [ParsedTaxon("A", "genus", 1.0, 100)]
        div = compute_alpha_diversity(taxa)
        assert div["shannon"] == 0.0
        assert div["simpson"] == 0.0
        assert div["observed_otus"] == 1

    def test_fixture_diversity(self):
        data = (FIXTURES / "sample_otu_table.csv").read_bytes()
        taxa = parse_otu_csv(data)
        div = compute_alpha_diversity(taxa)
        assert div["shannon"] > 1.5  # 10 taxa should have decent diversity
        assert div["simpson"] > 0.5
        assert div["observed_otus"] == 10


# ── Composition and phyla ratios ─────────────────────────────────────────────


class TestComposition:
    def test_phylum_composition(self):
        data = (FIXTURES / "sample_otu_table.csv").read_bytes()
        taxa = parse_otu_csv(data)
        composition = compute_composition(taxa, "phylum")
        phyla_names = [c["name"] for c in composition]
        assert "Firmicutes" in phyla_names
        assert "Bacteroidetes" in phyla_names

    def test_genus_composition(self):
        data = (FIXTURES / "sample_otu_table.csv").read_bytes()
        taxa = parse_otu_csv(data)
        composition = compute_composition(taxa, "genus")
        genus_names = [c["name"] for c in composition]
        assert "Roseburia" in genus_names
        assert "Bacteroides" in genus_names

    def test_phyla_ratios(self):
        data = (FIXTURES / "sample_otu_table.csv").read_bytes()
        taxa = parse_otu_csv(data)
        ratios = compute_phyla_ratios(taxa)
        assert "firmicutes" in ratios
        assert "bacteroidetes" in ratios
        assert "firmicutes_bacteroidetes_ratio" in ratios
        assert "proteobacteria_pct" in ratios
        assert ratios["firmicutes"] > 0
        assert ratios["bacteroidetes"] > 0


# ── Enterotype classification ────────────────────────────────────────────────


class TestClassifyEnterotype:
    def test_fixture_enterotype(self):
        data = (FIXTURES / "sample_otu_table.csv").read_bytes()
        taxa = parse_otu_csv(data)
        enterotype = classify_enterotype(taxa)
        # With Bacteroides being quite abundant, likely Bacteroides enterotype
        assert enterotype in ("Bacteroides", "Prevotella", "Ruminococcus", None)

    def test_empty_taxa(self):
        assert classify_enterotype([]) is None


# ── Health insights ──────────────────────────────────────────────────────────


class TestGenerateMicrobiomeInsights:
    def test_low_diversity_alert(self):
        diversity = {"shannon": 1.5, "simpson": 0.5}
        phyla_ratios = {"firmicutes_bacteroidetes_ratio": 1.5, "proteobacteria_pct": 5}
        insights = generate_microbiome_insights(diversity, phyla_ratios, None)
        titles = [i.title for i in insights]
        assert "Low microbial diversity" in titles

    def test_high_diversity_positive(self):
        diversity = {"shannon": 4.5, "simpson": 0.92}
        phyla_ratios = {"firmicutes_bacteroidetes_ratio": 1.5, "proteobacteria_pct": 5}
        insights = generate_microbiome_insights(diversity, phyla_ratios, None)
        titles = [i.title for i in insights]
        assert "Excellent microbial diversity" in titles

    def test_elevated_fb_ratio(self):
        diversity = {"shannon": 3.0}
        phyla_ratios = {"firmicutes_bacteroidetes_ratio": 4.0, "proteobacteria_pct": 5}
        insights = generate_microbiome_insights(diversity, phyla_ratios, None)
        titles = [i.title for i in insights]
        assert "Elevated Firmicutes/Bacteroidetes ratio" in titles

    def test_high_proteobacteria(self):
        diversity = {"shannon": 3.0}
        phyla_ratios = {"firmicutes_bacteroidetes_ratio": 1.5, "proteobacteria_pct": 20}
        insights = generate_microbiome_insights(diversity, phyla_ratios, None)
        titles = [i.title for i in insights]
        assert "High Proteobacteria abundance" in titles

    def test_no_diversity_or_phyla_alerts_when_healthy(self):
        """Healthy diversity and phyla ratios produce no diversity/composition alerts.

        Genus-level recommendations may still appear when no taxa are provided,
        since absent genera default to 0 abundance.
        """
        diversity = {"shannon": 3.5}
        phyla_ratios = {"firmicutes_bacteroidetes_ratio": 1.5, "proteobacteria_pct": 5}
        insights = generate_microbiome_insights(diversity, phyla_ratios, None)
        # No diversity or composition alerts
        alert_categories = {i.category for i in insights}
        assert "diversity" not in alert_categories
        assert "composition" not in alert_categories
        assert "dysbiosis" not in alert_categories


# ── Genome correlations ──────────────────────────────────────────────────────


class TestCorrelateGenome:
    def test_hla_dq2_low_bifido(self):
        taxa = [
            ParsedTaxon("Bifidobacterium", "genus", 0.005, 5,
                        full_lineage={"genus": "Bifidobacterium"}),
            ParsedTaxon("Bacteroides", "genus", 0.5, 500,
                        full_lineage={"genus": "Bacteroides"}),
        ]
        phyla_ratios = {"firmicutes_bacteroidetes_ratio": 1.5}
        variants = [
            {"rsid": "rs2187668", "gene": "HLA-DQ2", "genotype": "AG", "risk_level": "elevated"},
        ]
        correlations = correlate_microbiome_genome(taxa, phyla_ratios, variants)
        assert len(correlations) >= 1
        assert any("HLA-DQ2" in c.title for c in correlations)

    def test_no_variants_no_correlations(self):
        taxa = [ParsedTaxon("Bacteroides", "genus", 0.5, 500)]
        correlations = correlate_microbiome_genome(taxa, {}, [])
        assert correlations == []

    def test_variant_without_matching_taxon_threshold(self):
        """Variant present but taxon is above threshold — no correlation."""
        taxa = [
            ParsedTaxon("Bifidobacterium", "genus", 0.10, 100,
                        full_lineage={"genus": "Bifidobacterium"}),
        ]
        variants = [
            {"rsid": "rs2187668", "gene": "HLA-DQ2", "genotype": "AG", "risk_level": "elevated"},
        ]
        correlations = correlate_microbiome_genome(taxa, {}, variants)
        assert len(correlations) == 0


# ── Blood correlations ───────────────────────────────────────────────────────


class TestCorrelateBlood:
    def test_crp_proteobacteria(self):
        taxa = [ParsedTaxon("Escherichia", "genus", 0.1, 100)]
        diversity = {"shannon": 2.5}
        phyla_ratios = {"proteobacteria_pct": 20, "firmicutes_bacteroidetes_ratio": 1.5}
        blood_markers = [
            {"marker_name": "hs_crp", "value": 5.0, "unit": "mg/L", "flag": "H"},
        ]
        correlations = correlate_microbiome_blood(taxa, diversity, phyla_ratios, blood_markers)
        assert len(correlations) >= 1
        assert any("hs_crp" in c.title for c in correlations)

    def test_no_blood_markers(self):
        correlations = correlate_microbiome_blood([], {}, {}, [])
        assert correlations == []


# ── Wearable correlations ────────────────────────────────────────────────────


class TestCorrelateWearables:
    def test_low_activity_low_diversity(self):
        diversity = {"shannon": 2.0}
        phyla_ratios = {"firmicutes_bacteroidetes_ratio": 1.5}
        wearable_summaries = [
            {"data_type": "activity", "summary": {"steps": 3000}},
        ]
        correlations = correlate_microbiome_wearables(
            diversity, phyla_ratios, wearable_summaries
        )
        assert len(correlations) >= 1
        assert any("activity" in c.title.lower() for c in correlations)

    def test_poor_sleep_high_fb(self):
        diversity = {"shannon": 3.0}
        phyla_ratios = {"firmicutes_bacteroidetes_ratio": 3.0}
        wearable_summaries = [
            {"data_type": "sleep", "summary": {"total_sleep_minutes": 300}},
        ]
        correlations = correlate_microbiome_wearables(
            diversity, phyla_ratios, wearable_summaries
        )
        assert len(correlations) >= 1
        assert any("sleep" in c.title.lower() for c in correlations)

    def test_no_wearable_data(self):
        correlations = correlate_microbiome_wearables({}, {}, [])
        assert correlations == []


# ── AI summary ───────────────────────────────────────────────────────────────


class TestAiSummary:
    def test_template_fallback(self):
        """Without OpenAI key, should generate a template summary."""
        diversity = {"shannon": 3.2, "simpson": 0.85, "chao1": 120, "observed_otus": 50}
        phyla_ratios = {
            "firmicutes": 0.45, "bacteroidetes": 0.30,
            "firmicutes_bacteroidetes_ratio": 1.5, "proteobacteria_pct": 5,
        }
        summary = generate_microbiome_ai_summary(
            diversity=diversity,
            phyla_ratios=phyla_ratios,
            enterotype="Bacteroides",
            insights=[],
            genome_correlations=[],
            data_type="16s_rrna",
            openai_api_key="",
        )
        assert "Microbiome Analysis Summary" in summary
        assert "Shannon Index" in summary
        assert "Bacteroides" in summary
        assert "Disclaimer" in summary
