"""Tests for epigenetics analysis utilities."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.utils.epigenetics_analyzer import (
    GenomeEpigeneticOverlay,
    ParsedRegion,
    annotate_feature_type,
    annotate_regions,
    cross_reference_genome,
    generate_epigenetics_ai_summary,
    parse_bed,
    parse_methylation_csv,
    query_encode,
    query_roadmap_chromhmm,
)


# ── BED parsing ──────────────────────────────────────────────────────────────


class TestParseBed:
    def test_basic_bed3(self):
        data = b"chr1\t100\t200\nchr2\t300\t400\n"
        regions = parse_bed(data)
        assert len(regions) == 2
        assert regions[0].chromosome == "chr1"
        assert regions[0].start_pos == 100
        assert regions[0].end_pos == 200

    def test_bed6_with_name_and_score(self):
        data = b"chr1\t100\t200\tpeak1\t45.5\t+\n"
        regions = parse_bed(data)
        assert len(regions) == 1
        assert regions[0].name == "peak1"
        assert regions[0].signal_value == 45.5

    def test_histone_assay_type(self):
        data = b"chr1\t100\t200\tpeak1\t10\n"
        regions = parse_bed(data, assay_type="H3K27ac")
        assert regions[0].histone_mark == "H3K27ac"

    def test_histone_from_name_field(self):
        data = b"chr1\t100\t200\tH3K4me3_peak\t10\n"
        regions = parse_bed(data)
        assert regions[0].histone_mark == "H3K4me3_peak"

    def test_skips_header_lines(self):
        data = b"track name=test\nbrowser position chr1:100-200\n#comment\nchr1\t100\t200\n"
        regions = parse_bed(data)
        assert len(regions) == 1

    def test_skips_malformed_lines(self):
        data = b"chr1\t100\t200\nchr2\tnotanumber\t400\nchr3\t500\t600\n"
        regions = parse_bed(data)
        assert len(regions) == 2

    def test_skips_end_before_start(self):
        data = b"chr1\t200\t100\nchr1\t100\t200\n"
        regions = parse_bed(data)
        assert len(regions) == 1

    def test_empty_file(self):
        data = b""
        regions = parse_bed(data)
        assert len(regions) == 0


# ── Methylation CSV parsing ──────────────────────────────────────────────────


class TestParseMethylationCsv:
    def test_basic_csv(self):
        data = b"chr,start,end,beta_value\nchr1,1000,1001,0.85\nchr2,2000,2001,0.12\n"
        regions = parse_methylation_csv(data)
        assert len(regions) == 2
        assert regions[0].methylation_beta == 0.85
        assert regions[1].methylation_beta == 0.12

    def test_flexible_headers(self):
        data = b"chromosome,position,methylation,gene_symbol\nchr7,100000,0.55,MTHFR\n"
        regions = parse_methylation_csv(data)
        assert len(regions) == 1
        assert regions[0].chromosome == "chr7"
        assert regions[0].methylation_beta == 0.55
        assert regions[0].name == "MTHFR"

    def test_no_end_column(self):
        data = b"chr,start,beta\nchr1,5000,0.3\n"
        regions = parse_methylation_csv(data)
        assert len(regions) == 1
        assert regions[0].end_pos == 5001  # start + 1

    def test_missing_header_raises(self):
        data = b"col1,col2,col3\nfoo,bar,baz\n"
        with pytest.raises(ValueError, match="Could not find header row"):
            parse_methylation_csv(data)

    def test_missing_required_columns_raises(self):
        data = b"chr,something_else\nchr1,foo\n"
        with pytest.raises(ValueError, match="must have at minimum"):
            parse_methylation_csv(data)

    def test_skips_bad_values(self):
        data = b"chr,start,beta\nchr1,1000,0.5\nchr1,bad,0.3\nchr1,2000,notafloat\n"
        regions = parse_methylation_csv(data)
        assert len(regions) == 1
        assert regions[0].start_pos == 1000


# ── Feature type annotation ──────────────────────────────────────────────────


class TestAnnotateFeatureType:
    def test_promoter_region(self):
        # MTHFR is at chr1:11785723-11806920; test a region near the start
        region = ParsedRegion("chr1", 11785000, 11786000)
        feature, gene = annotate_feature_type(region)
        assert feature == "promoter"
        assert gene == "MTHFR"

    def test_gene_body_region(self):
        # Inside MTHFR but not near promoter
        region = ParsedRegion("chr1", 11795000, 11800000)
        feature, gene = annotate_feature_type(region)
        assert feature == "gene_body"
        assert gene == "MTHFR"

    def test_enhancer_region(self):
        # Near MTHFR but not overlapping
        region = ParsedRegion("chr1", 11780000, 11781000)
        feature, gene = annotate_feature_type(region)
        assert feature == "enhancer"
        assert gene == "MTHFR"

    def test_intergenic_unknown(self):
        region = ParsedRegion("chr5", 1, 100)
        feature, gene = annotate_feature_type(region)
        assert feature == "intergenic"

    def test_gene_from_name_field(self):
        region = ParsedRegion("chr5", 1, 100, name="TP53")
        feature, gene = annotate_feature_type(region)
        # TP53 is in our lookup on chr17, so chr5 won't match it
        # But the name field should be used
        assert gene == "TP53"


# ── Roadmap ChromHMM ─────────────────────────────────────────────────────────


class TestQueryRoadmapChromhmm:
    def test_methylated_promoter_returns_reprpc(self):
        regions = [ParsedRegion("chr1", 11785000, 11786000, methylation_beta=0.9)]
        results = query_roadmap_chromhmm(regions, tissue_type="blood")
        key = "chr1:11785000-11786000"
        assert key in results
        assert results[key]["state"] == "ReprPC"

    def test_unmethylated_promoter_returns_tssa(self):
        regions = [ParsedRegion("chr1", 11785000, 11786000, methylation_beta=0.1)]
        results = query_roadmap_chromhmm(regions, tissue_type="blood")
        key = "chr1:11785000-11786000"
        assert results[key]["state"] == "TssA"

    def test_h3k27ac_at_promoter(self):
        regions = [ParsedRegion("chr1", 11785000, 11786000, histone_mark="H3K27ac", signal_value=10)]
        results = query_roadmap_chromhmm(regions, tissue_type="blood")
        key = "chr1:11785000-11786000"
        assert results[key]["state"] == "TssA"

    def test_h3k27me3_returns_reprpc(self):
        regions = [ParsedRegion("chr5", 1, 100, histone_mark="H3K27me3", signal_value=10)]
        results = query_roadmap_chromhmm(regions)
        key = "chr5:1-100"
        assert results[key]["state"] == "ReprPC"

    def test_default_tissue_maps_to_e062(self):
        regions = [ParsedRegion("chr1", 1, 100, methylation_beta=0.5)]
        results = query_roadmap_chromhmm(regions)
        key = "chr1:1-100"
        assert results[key]["epigenome_id"] == "E062"


# ── ENCODE query ─────────────────────────────────────────────────────────────


class TestQueryEncode:
    def test_returns_empty_on_http_error(self):
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("Connection refused")
        regions = [ParsedRegion("chr1", 100, 200)]
        results = query_encode(regions, mock_client)
        assert results == {}

    def test_parses_experiment_results(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "@graph": [
                {
                    "accession": "ENCSR000AKA",
                    "assay_title": "WGBS",
                    "biosample_ontology": {"term_name": "K562"},
                    "target": {"label": ""},
                    "description": "Whole genome bisulfite sequencing on K562",
                },
            ]
        }
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp

        regions = [ParsedRegion("chr1", 100, 200)]
        results = query_encode(regions, mock_client)
        assert len(results) == 1
        key = "chr1:100-200"
        assert results[key][0]["accession"] == "ENCSR000AKA"


# ── Genome cross-reference ───────────────────────────────────────────────────


class TestCrossReferenceGenome:
    def test_matching_gene_produces_overlay(self):
        regions = [ParsedRegion("chr1", 11785000, 11786000, methylation_beta=0.9)]
        annotations = {
            "chr1:11785000-11786000": {
                "feature_type": "promoter",
                "nearest_gene": "MTHFR",
                "state": "ReprPC",
            }
        }
        variants = [
            {"rsid": "rs1801133", "gene": "MTHFR", "genotype": "T/T", "risk_level": "elevated"},
        ]
        overlays = cross_reference_genome(regions, annotations, variants)
        assert len(overlays) == 1
        ov = overlays[0]
        assert ov.gene == "MTHFR"
        assert ov.variant_rsid == "rs1801133"
        assert ov.adjusted_risk_modifier < 1.0  # Silencing attenuates risk
        assert "methylation" in ov.interpretation.lower()

    def test_no_matching_gene_returns_empty(self):
        regions = [ParsedRegion("chr5", 1, 100)]
        annotations = {"chr5:1-100": {"feature_type": "intergenic", "nearest_gene": ""}}
        variants = [{"rsid": "rs1801133", "gene": "MTHFR", "genotype": "C/T", "risk_level": "low"}]
        overlays = cross_reference_genome(regions, annotations, variants)
        assert len(overlays) == 0

    def test_rsid_gene_map_lookup(self):
        """When variant has no gene field, fall back to _RSID_GENE_MAP."""
        regions = [ParsedRegion("chr19", 44905754, 44906000, methylation_beta=0.2)]
        annotations = {
            "chr19:44905754-44906000": {
                "feature_type": "promoter",
                "nearest_gene": "APOE",
                "state": "TssA",
            }
        }
        variants = [{"rsid": "rs429358", "gene": "", "genotype": "C/C", "risk_level": "high"}]
        overlays = cross_reference_genome(regions, annotations, variants)
        assert len(overlays) == 1
        assert overlays[0].gene == "APOE"

    def test_active_enhancer_amplifies_risk(self):
        regions = [ParsedRegion("chr1", 11780000, 11781000, histone_mark="H3K27ac", signal_value=15)]
        annotations = {
            "chr1:11780000-11781000": {
                "feature_type": "enhancer",
                "nearest_gene": "MTHFR",
                "state": "Enh",
            }
        }
        variants = [
            {"rsid": "rs1801133", "gene": "MTHFR", "genotype": "T/T", "risk_level": "elevated"},
        ]
        overlays = cross_reference_genome(regions, annotations, variants)
        assert len(overlays) == 1
        assert overlays[0].adjusted_risk_modifier >= 1.15


# ── AI summary generation ────────────────────────────────────────────────────


class TestGenerateAiSummary:
    def test_template_fallback(self):
        """Without OpenAI key, should produce a template summary."""
        overlays = [
            GenomeEpigeneticOverlay(
                variant_rsid="rs1801133",
                gene="MTHFR",
                variant_risk="elevated",
                region_coords="chr1:11785000-11786000",
                feature_type="promoter",
                methylation_beta=0.9,
                histone_mark=None,
                interpretation="High methylation at MTHFR promoter.",
                adjusted_risk_modifier=0.85,
            ),
        ]
        summary = generate_epigenetics_ai_summary(
            region_count=100,
            annotated_count=50,
            global_methylation_avg=0.55,
            overlays=overlays,
            data_type="methylation",
            openai_api_key="",
        )
        assert "Epigenetic Analysis Summary" in summary
        assert "100" in summary
        assert "MTHFR" in summary
        assert "Disclaimer" in summary or "disclaimer" in summary

    def test_empty_overlays_still_produces_summary(self):
        summary = generate_epigenetics_ai_summary(
            region_count=10,
            annotated_count=5,
            global_methylation_avg=None,
            overlays=[],
            data_type="histone",
        )
        assert "10" in summary
        assert "histone" in summary


# ── Full annotation pipeline ─────────────────────────────────────────────────


class TestAnnotateRegions:
    def test_annotates_without_http_client(self):
        regions = [
            ParsedRegion("chr1", 11785000, 11786000, methylation_beta=0.9),
            ParsedRegion("chr5", 1, 100, methylation_beta=0.2),
        ]
        annotations = annotate_regions(regions, client=None, tissue_type="blood")
        assert len(annotations) == 2

        key1 = "chr1:11785000-11786000"
        assert annotations[key1]["feature_type"] == "promoter"
        assert annotations[key1]["nearest_gene"] == "MTHFR"
        assert "roadmap" in annotations[key1]

    def test_includes_roadmap_state(self):
        regions = [ParsedRegion("chr1", 11785000, 11786000, methylation_beta=0.1)]
        annotations = annotate_regions(regions)
        key = "chr1:11785000-11786000"
        assert annotations[key]["roadmap"]["state"] == "TssA"
