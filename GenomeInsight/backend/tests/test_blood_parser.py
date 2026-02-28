"""Tests for the blood test parsing utilities."""

from pathlib import Path

from app.utils.blood_parser import (
    MarkerDelta,
    ParsedMarker,
    compute_deltas,
    cross_reference_genome,
    parse_blood_file,
    parse_csv,
    _normalise_marker,
    _parse_ref_range,
    _compute_flag,
)

FIXTURES = Path(__file__).parent / "fixtures"


# ── Marker normalisation ────────────────────────────────────────────────────


class TestNormaliseMarker:
    def test_exact_match(self):
        result = _normalise_marker("total cholesterol")
        assert result == ("TOTAL_CHOLESTEROL", "Total Cholesterol", "mg/dL")

    def test_case_insensitive(self):
        result = _normalise_marker("HDL Cholesterol")
        assert result is not None
        assert result[0] == "HDL"

    def test_parenthetical_stripped(self):
        result = _normalise_marker("Glucose (mg/dL)")
        assert result is not None
        assert result[0] == "GLUCOSE"

    def test_unknown_marker(self):
        result = _normalise_marker("some_random_marker_xyz")
        assert result is None

    def test_alias_variants(self):
        for alias in ("hba1c", "a1c", "hemoglobin a1c", "glycated hemoglobin"):
            result = _normalise_marker(alias)
            assert result is not None
            assert result[0] == "HBA1C", f"Failed for alias '{alias}'"


# ── Reference range parsing ─────────────────────────────────────────────────


class TestParseRefRange:
    def test_range_with_dash(self):
        assert _parse_ref_range("70 - 100") == (70.0, 100.0)

    def test_range_no_spaces(self):
        assert _parse_ref_range("70-100") == (70.0, 100.0)

    def test_less_than(self):
        assert _parse_ref_range("<200") == (None, 200.0)

    def test_greater_than(self):
        assert _parse_ref_range(">40") == (40.0, None)

    def test_empty_string(self):
        assert _parse_ref_range("") == (None, None)

    def test_dash_only(self):
        assert _parse_ref_range("-") == (None, None)

    def test_range_with_to(self):
        assert _parse_ref_range("70 to 100") == (70.0, 100.0)


# ── Flag computation ────────────────────────────────────────────────────────


class TestComputeFlag:
    def test_normal(self):
        assert _compute_flag(95, 70, 100) == "N"

    def test_low(self):
        assert _compute_flag(65, 70, 100) == "L"

    def test_high(self):
        assert _compute_flag(105, 70, 100) == "H"

    def test_no_ref(self):
        assert _compute_flag(95, None, None) == "N"


# ── CSV parsing ─────────────────────────────────────────────────────────────


class TestParseCSV:
    def test_sample_csv(self):
        csv_bytes = (FIXTURES / "sample_blood.csv").read_bytes()
        markers = parse_csv(csv_bytes)
        assert len(markers) == 19

        names = {m.marker_name for m in markers}
        assert "TOTAL_CHOLESTEROL" in names
        assert "HDL" in names
        assert "GLUCOSE" in names
        assert "HBA1C" in names
        assert "HOMOCYSTEINE" in names

    def test_cholesterol_flagged_high(self):
        csv_bytes = (FIXTURES / "sample_blood.csv").read_bytes()
        markers = parse_csv(csv_bytes)
        chol = next(m for m in markers if m.marker_name == "TOTAL_CHOLESTEROL")
        assert chol.value == 210.0
        assert chol.flag == "H"  # 210 > 200

    def test_ldl_flagged_high(self):
        csv_bytes = (FIXTURES / "sample_blood.csv").read_bytes()
        markers = parse_csv(csv_bytes)
        ldl = next(m for m in markers if m.marker_name == "LDL")
        assert ldl.value == 130.0
        assert ldl.flag == "H"  # 130 > 100

    def test_glucose_normal(self):
        csv_bytes = (FIXTURES / "sample_blood.csv").read_bytes()
        markers = parse_csv(csv_bytes)
        glu = next(m for m in markers if m.marker_name == "GLUCOSE")
        assert glu.value == 95.0
        assert glu.flag == "N"

    def test_reference_ranges_populated(self):
        csv_bytes = (FIXTURES / "sample_blood.csv").read_bytes()
        markers = parse_csv(csv_bytes)
        for m in markers:
            assert m.reference_low is not None or m.reference_high is not None, (
                f"Missing ref range for {m.marker_name}"
            )

    def test_empty_csv(self):
        markers = parse_csv(b"")
        assert markers == []

    def test_header_only_csv(self):
        markers = parse_csv(b"Test,Value,Unit\n")
        assert markers == []

    def test_minimal_csv(self):
        csv_data = b"marker,value\nGlucose,95\n"
        markers = parse_csv(csv_data)
        assert len(markers) == 1
        assert markers[0].marker_name == "GLUCOSE"
        assert markers[0].value == 95.0


# ── parse_blood_file dispatcher ─────────────────────────────────────────────


class TestParseBloodFile:
    def test_csv_dispatch(self):
        csv_bytes = (FIXTURES / "sample_blood.csv").read_bytes()
        markers = parse_blood_file(csv_bytes, "csv")
        assert len(markers) == 19

    def test_unknown_type(self):
        markers = parse_blood_file(b"data", "docx")
        assert markers == []


# ── Delta computation ───────────────────────────────────────────────────────


class TestComputeDeltas:
    def test_basic_deltas(self):
        prev = [
            {"marker_name": "LDL", "marker_display_name": "LDL Cholesterol",
             "value": 130.0, "unit": "mg/dL", "flag": "H",
             "reference_low": 0.0, "reference_high": 100.0},
            {"marker_name": "GLUCOSE", "marker_display_name": "Glucose",
             "value": 95.0, "unit": "mg/dL", "flag": "N",
             "reference_low": 70.0, "reference_high": 100.0},
        ]
        curr = [
            {"marker_name": "LDL", "marker_display_name": "LDL Cholesterol",
             "value": 110.0, "unit": "mg/dL", "flag": "H",
             "reference_low": 0.0, "reference_high": 100.0},
            {"marker_name": "GLUCOSE", "marker_display_name": "Glucose",
             "value": 88.0, "unit": "mg/dL", "flag": "N",
             "reference_low": 70.0, "reference_high": 100.0},
        ]
        deltas = compute_deltas(prev, curr)
        assert len(deltas) == 2

        ldl_delta = next(d for d in deltas if d.marker_name == "LDL")
        assert ldl_delta.direction == "decreased"
        assert ldl_delta.absolute_change == -20.0
        assert ldl_delta.improved is True  # Moved closer to midpoint of 0-100

    def test_no_shared_markers(self):
        prev = [{"marker_name": "A", "marker_display_name": "A",
                 "value": 1.0, "unit": "x", "flag": "N",
                 "reference_low": None, "reference_high": None}]
        curr = [{"marker_name": "B", "marker_display_name": "B",
                 "value": 2.0, "unit": "x", "flag": "N",
                 "reference_low": None, "reference_high": None}]
        deltas = compute_deltas(prev, curr)
        assert deltas == []

    def test_unchanged_marker(self):
        data = [{"marker_name": "TSH", "marker_display_name": "TSH",
                 "value": 2.0, "unit": "mIU/L", "flag": "N",
                 "reference_low": 0.4, "reference_high": 4.0}]
        deltas = compute_deltas(data, data)
        assert len(deltas) == 1
        assert deltas[0].direction == "unchanged"

    def test_full_csv_deltas(self):
        prev_bytes = (FIXTURES / "sample_blood.csv").read_bytes()
        curr_bytes = (FIXTURES / "sample_blood_followup.csv").read_bytes()
        prev_markers = parse_csv(prev_bytes)
        curr_markers = parse_csv(curr_bytes)

        prev_dicts = [
            {"marker_name": m.marker_name, "marker_display_name": m.marker_display_name,
             "value": m.value, "unit": m.unit, "flag": m.flag,
             "reference_low": m.reference_low, "reference_high": m.reference_high}
            for m in prev_markers
        ]
        curr_dicts = [
            {"marker_name": m.marker_name, "marker_display_name": m.marker_display_name,
             "value": m.value, "unit": m.unit, "flag": m.flag,
             "reference_low": m.reference_low, "reference_high": m.reference_high}
            for m in curr_markers
        ]

        deltas = compute_deltas(prev_dicts, curr_dicts)
        assert len(deltas) > 0

        # Cholesterol should have decreased: 210 → 195
        chol = next(d for d in deltas if d.marker_name == "TOTAL_CHOLESTEROL")
        assert chol.direction == "decreased"
        assert chol.improved is True


# ── Genome cross-referencing ────────────────────────────────────────────────


class TestCrossReferenceGenome:
    def test_apoe_ldl_insight(self):
        markers = [
            {"marker_name": "LDL", "marker_display_name": "LDL Cholesterol",
             "value": 150.0, "unit": "mg/dL", "flag": "H",
             "reference_low": 0.0, "reference_high": 100.0},
        ]
        insights = cross_reference_genome(markers, {"rs429358"})
        assert len(insights) >= 1
        ldl_insight = next(i for i in insights if i.marker_name == "LDL")
        assert "APOE" in ldl_insight.insight
        assert ldl_insight.priority <= 2  # Flagged marker = high priority

    def test_tcf7l2_glucose_insight(self):
        markers = [
            {"marker_name": "GLUCOSE", "marker_display_name": "Glucose (Fasting)",
             "value": 105.0, "unit": "mg/dL", "flag": "H",
             "reference_low": 70.0, "reference_high": 100.0},
        ]
        insights = cross_reference_genome(markers, {"rs7903146"})
        assert len(insights) >= 1
        glu = next(i for i in insights if i.marker_name == "GLUCOSE")
        assert "TCF7L2" in glu.insight
        assert "diabetes" in glu.insight.lower()

    def test_no_matching_rsids(self):
        markers = [
            {"marker_name": "LDL", "marker_display_name": "LDL",
             "value": 90.0, "unit": "mg/dL", "flag": "N"},
        ]
        insights = cross_reference_genome(markers, {"rs99999999"})
        assert insights == []

    def test_no_matching_markers(self):
        markers = [
            {"marker_name": "SOME_RANDOM", "marker_display_name": "Random",
             "value": 5.0, "unit": "x", "flag": "N"},
        ]
        insights = cross_reference_genome(markers, {"rs429358"})
        assert insights == []

    def test_mthfr_homocysteine_insight(self):
        markers = [
            {"marker_name": "HOMOCYSTEINE", "marker_display_name": "Homocysteine",
             "value": 18.0, "unit": "umol/L", "flag": "H",
             "reference_low": 5.0, "reference_high": 15.0},
        ]
        insights = cross_reference_genome(markers, {"rs1801133"})
        assert len(insights) >= 1
        homo = next(i for i in insights if i.marker_name == "HOMOCYSTEINE")
        assert "MTHFR" in homo.insight

    def test_trend_aware_insight(self):
        markers = [
            {"marker_name": "LDL", "marker_display_name": "LDL Cholesterol",
             "value": 110.0, "unit": "mg/dL", "flag": "H",
             "reference_low": 0.0, "reference_high": 100.0},
        ]
        deltas = [
            MarkerDelta(
                marker_name="LDL", marker_display_name="LDL Cholesterol",
                previous_value=130.0, current_value=110.0,
                unit="mg/dL", absolute_change=-20.0, percent_change=-15.4,
                direction="decreased", previous_flag="H", current_flag="H",
                improved=True, reference_low=0.0, reference_high=100.0,
            ),
        ]
        insights = cross_reference_genome(markers, {"rs429358"}, deltas=deltas)
        ldl_insight = next(i for i in insights if i.marker_name == "LDL")
        assert "decreased" in ldl_insight.insight
        assert "positive trend" in ldl_insight.insight
