"""Blood test result parsing from PDF and CSV files.

Extracts biomarker values, units, and reference ranges from common lab
report formats. Standardises marker names to a canonical dictionary
(e.g. "Total Cholesterol" → ``TOTAL_CHOLESTEROL``) so downstream trend
analysis and genome cross-referencing work consistently.

Supported inputs:
- **CSV**: Columns detected heuristically (marker, value, unit, ref range).
- **PDF**: Text extracted via PyPDF2; falls back to regex-based parsing
  when tabula-py is unavailable.
"""

from __future__ import annotations

import csv
import io
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ── Canonical marker definitions ────────────────────────────────────────────

@dataclass
class ParsedMarker:
    """A single biomarker parsed from a blood test report."""

    marker_name: str          # Canonical key, e.g. "TOTAL_CHOLESTEROL"
    marker_display_name: str  # Human-readable, e.g. "Total Cholesterol"
    value: float
    unit: str
    reference_low: float | None = None
    reference_high: float | None = None
    flag: str | None = None   # "L", "H", or "N"


# Maps common lab-report aliases (lowercased) → (canonical_key, display_name, default_unit)
MARKER_ALIASES: dict[str, tuple[str, str, str]] = {
    # Lipid panel
    "total cholesterol": ("TOTAL_CHOLESTEROL", "Total Cholesterol", "mg/dL"),
    "cholesterol": ("TOTAL_CHOLESTEROL", "Total Cholesterol", "mg/dL"),
    "cholesterol, total": ("TOTAL_CHOLESTEROL", "Total Cholesterol", "mg/dL"),
    "hdl": ("HDL", "HDL Cholesterol", "mg/dL"),
    "hdl cholesterol": ("HDL", "HDL Cholesterol", "mg/dL"),
    "hdl-c": ("HDL", "HDL Cholesterol", "mg/dL"),
    "hdl-cholesterol": ("HDL", "HDL Cholesterol", "mg/dL"),
    "ldl": ("LDL", "LDL Cholesterol", "mg/dL"),
    "ldl cholesterol": ("LDL", "LDL Cholesterol", "mg/dL"),
    "ldl-c": ("LDL", "LDL Cholesterol", "mg/dL"),
    "ldl-cholesterol": ("LDL", "LDL Cholesterol", "mg/dL"),
    "ldl cholesterol calc": ("LDL", "LDL Cholesterol", "mg/dL"),
    "triglycerides": ("TRIGLYCERIDES", "Triglycerides", "mg/dL"),
    "triglyceride": ("TRIGLYCERIDES", "Triglycerides", "mg/dL"),
    "vldl": ("VLDL", "VLDL Cholesterol", "mg/dL"),
    "vldl cholesterol": ("VLDL", "VLDL Cholesterol", "mg/dL"),
    # Glucose / diabetes
    "glucose": ("GLUCOSE", "Glucose (Fasting)", "mg/dL"),
    "glucose, fasting": ("GLUCOSE", "Glucose (Fasting)", "mg/dL"),
    "fasting glucose": ("GLUCOSE", "Glucose (Fasting)", "mg/dL"),
    "blood glucose": ("GLUCOSE", "Glucose (Fasting)", "mg/dL"),
    "hba1c": ("HBA1C", "HbA1c (Glycated Hemoglobin)", "%"),
    "a1c": ("HBA1C", "HbA1c (Glycated Hemoglobin)", "%"),
    "hemoglobin a1c": ("HBA1C", "HbA1c (Glycated Hemoglobin)", "%"),
    "glycated hemoglobin": ("HBA1C", "HbA1c (Glycated Hemoglobin)", "%"),
    # CBC
    "rbc": ("RBC", "Red Blood Cells", "million/uL"),
    "red blood cells": ("RBC", "Red Blood Cells", "million/uL"),
    "red blood cell count": ("RBC", "Red Blood Cells", "million/uL"),
    "wbc": ("WBC", "White Blood Cells", "thousand/uL"),
    "white blood cells": ("WBC", "White Blood Cells", "thousand/uL"),
    "white blood cell count": ("WBC", "White Blood Cells", "thousand/uL"),
    "hemoglobin": ("HEMOGLOBIN", "Hemoglobin", "g/dL"),
    "hgb": ("HEMOGLOBIN", "Hemoglobin", "g/dL"),
    "hematocrit": ("HEMATOCRIT", "Hematocrit", "%"),
    "hct": ("HEMATOCRIT", "Hematocrit", "%"),
    "platelets": ("PLATELETS", "Platelets", "thousand/uL"),
    "platelet count": ("PLATELETS", "Platelets", "thousand/uL"),
    "plt": ("PLATELETS", "Platelets", "thousand/uL"),
    # Metabolic panel
    "creatinine": ("CREATININE", "Creatinine", "mg/dL"),
    "bun": ("BUN", "Blood Urea Nitrogen", "mg/dL"),
    "blood urea nitrogen": ("BUN", "Blood Urea Nitrogen", "mg/dL"),
    "urea nitrogen": ("BUN", "Blood Urea Nitrogen", "mg/dL"),
    "sodium": ("SODIUM", "Sodium", "mEq/L"),
    "na": ("SODIUM", "Sodium", "mEq/L"),
    "potassium": ("POTASSIUM", "Potassium", "mEq/L"),
    "k": ("POTASSIUM", "Potassium", "mEq/L"),
    "calcium": ("CALCIUM", "Calcium", "mg/dL"),
    "ca": ("CALCIUM", "Calcium", "mg/dL"),
    "chloride": ("CHLORIDE", "Chloride", "mEq/L"),
    "cl": ("CHLORIDE", "Chloride", "mEq/L"),
    "co2": ("CO2", "Carbon Dioxide", "mEq/L"),
    "carbon dioxide": ("CO2", "Carbon Dioxide", "mEq/L"),
    "bicarbonate": ("CO2", "Carbon Dioxide", "mEq/L"),
    # Liver
    "alt": ("ALT", "ALT (Alanine Aminotransferase)", "U/L"),
    "sgpt": ("ALT", "ALT (Alanine Aminotransferase)", "U/L"),
    "alanine aminotransferase": ("ALT", "ALT (Alanine Aminotransferase)", "U/L"),
    "ast": ("AST", "AST (Aspartate Aminotransferase)", "U/L"),
    "sgot": ("AST", "AST (Aspartate Aminotransferase)", "U/L"),
    "aspartate aminotransferase": ("AST", "AST (Aspartate Aminotransferase)", "U/L"),
    "alkaline phosphatase": ("ALP", "Alkaline Phosphatase", "U/L"),
    "alp": ("ALP", "Alkaline Phosphatase", "U/L"),
    "bilirubin": ("BILIRUBIN", "Total Bilirubin", "mg/dL"),
    "total bilirubin": ("BILIRUBIN", "Total Bilirubin", "mg/dL"),
    "albumin": ("ALBUMIN", "Albumin", "g/dL"),
    "total protein": ("TOTAL_PROTEIN", "Total Protein", "g/dL"),
    # Thyroid
    "tsh": ("TSH", "Thyroid Stimulating Hormone", "mIU/L"),
    "thyroid stimulating hormone": ("TSH", "Thyroid Stimulating Hormone", "mIU/L"),
    "free t4": ("FREE_T4", "Free T4 (Thyroxine)", "ng/dL"),
    "ft4": ("FREE_T4", "Free T4 (Thyroxine)", "ng/dL"),
    "thyroxine, free": ("FREE_T4", "Free T4 (Thyroxine)", "ng/dL"),
    "free t3": ("FREE_T3", "Free T3 (Triiodothyronine)", "pg/mL"),
    "ft3": ("FREE_T3", "Free T3 (Triiodothyronine)", "pg/mL"),
    # Iron
    "iron": ("IRON", "Iron", "ug/dL"),
    "serum iron": ("IRON", "Iron", "ug/dL"),
    "ferritin": ("FERRITIN", "Ferritin", "ng/mL"),
    # Inflammation
    "crp": ("CRP", "C-Reactive Protein", "mg/L"),
    "c-reactive protein": ("CRP", "C-Reactive Protein", "mg/L"),
    "hs-crp": ("HS_CRP", "hs-CRP (High-Sensitivity)", "mg/L"),
    "high-sensitivity crp": ("HS_CRP", "hs-CRP (High-Sensitivity)", "mg/L"),
    "esr": ("ESR", "Erythrocyte Sedimentation Rate", "mm/hr"),
    "sed rate": ("ESR", "Erythrocyte Sedimentation Rate", "mm/hr"),
    # Vitamins
    "vitamin d": ("VITAMIN_D", "Vitamin D (25-OH)", "ng/mL"),
    "25-hydroxy vitamin d": ("VITAMIN_D", "Vitamin D (25-OH)", "ng/mL"),
    "vitamin b12": ("VITAMIN_B12", "Vitamin B12", "pg/mL"),
    "b12": ("VITAMIN_B12", "Vitamin B12", "pg/mL"),
    "folate": ("FOLATE", "Folate", "ng/mL"),
    "folic acid": ("FOLATE", "Folate", "ng/mL"),
    # Uric acid
    "uric acid": ("URIC_ACID", "Uric Acid", "mg/dL"),
    # Hormones
    "testosterone": ("TESTOSTERONE", "Testosterone", "ng/dL"),
    "total testosterone": ("TESTOSTERONE", "Testosterone", "ng/dL"),
    "insulin": ("INSULIN", "Insulin (Fasting)", "uIU/mL"),
    "fasting insulin": ("INSULIN", "Insulin (Fasting)", "uIU/mL"),
    # Kidney
    "egfr": ("EGFR", "eGFR", "mL/min/1.73m2"),
    "gfr": ("EGFR", "eGFR", "mL/min/1.73m2"),
    # Homocysteine
    "homocysteine": ("HOMOCYSTEINE", "Homocysteine", "umol/L"),
}

# Reference ranges for common markers (general adult ranges)
DEFAULT_REFERENCE_RANGES: dict[str, tuple[float, float]] = {
    "TOTAL_CHOLESTEROL": (125.0, 200.0),
    "HDL": (40.0, 60.0),
    "LDL": (0.0, 100.0),
    "TRIGLYCERIDES": (0.0, 150.0),
    "GLUCOSE": (70.0, 100.0),
    "HBA1C": (4.0, 5.7),
    "RBC": (4.0, 5.5),
    "WBC": (4.0, 11.0),
    "HEMOGLOBIN": (12.0, 17.0),
    "HEMATOCRIT": (36.0, 50.0),
    "PLATELETS": (150.0, 400.0),
    "CREATININE": (0.6, 1.2),
    "BUN": (7.0, 20.0),
    "SODIUM": (136.0, 145.0),
    "POTASSIUM": (3.5, 5.0),
    "CALCIUM": (8.5, 10.5),
    "ALT": (7.0, 56.0),
    "AST": (10.0, 40.0),
    "ALP": (44.0, 147.0),
    "BILIRUBIN": (0.1, 1.2),
    "ALBUMIN": (3.5, 5.5),
    "TOTAL_PROTEIN": (6.0, 8.3),
    "TSH": (0.4, 4.0),
    "FREE_T4": (0.8, 1.8),
    "IRON": (60.0, 170.0),
    "FERRITIN": (12.0, 300.0),
    "CRP": (0.0, 3.0),
    "HS_CRP": (0.0, 1.0),
    "VITAMIN_D": (30.0, 100.0),
    "VITAMIN_B12": (200.0, 900.0),
    "FOLATE": (2.7, 17.0),
    "URIC_ACID": (2.5, 7.0),
    "EGFR": (90.0, 120.0),
    "HOMOCYSTEINE": (5.0, 15.0),
}


def _normalise_marker(raw_name: str) -> tuple[str, str, str] | None:
    """Resolve a raw marker label to (canonical_key, display_name, unit).

    Returns ``None`` if the marker is unrecognised.
    """
    cleaned = raw_name.strip().lower()
    # Strip trailing parenthetical units — e.g. "HDL (mg/dL)"
    cleaned = re.sub(r"\s*\(.*?\)\s*$", "", cleaned)
    cleaned = cleaned.strip()
    return MARKER_ALIASES.get(cleaned)


def _compute_flag(value: float, ref_low: float | None, ref_high: float | None) -> str:
    """Return L / H / N based on reference range."""
    if ref_low is not None and value < ref_low:
        return "L"
    if ref_high is not None and value > ref_high:
        return "H"
    return "N"


def _parse_ref_range(raw: str) -> tuple[float | None, float | None]:
    """Extract (low, high) from reference-range strings like '70 - 100' or '<200'."""
    raw = raw.strip()
    if not raw or raw == "-":
        return None, None

    # "< 200" or "<200"
    m = re.match(r"^[<≤]\s*([\d.]+)$", raw)
    if m:
        return None, float(m.group(1))

    # "> 40" or ">40"
    m = re.match(r"^[>≥]\s*([\d.]+)$", raw)
    if m:
        return float(m.group(1)), None

    # "70 - 100" or "70-100" or "70 to 100"
    m = re.match(r"^([\d.]+)\s*[-–—]\s*([\d.]+)$", raw)
    if not m:
        m = re.match(r"^([\d.]+)\s+to\s+([\d.]+)$", raw, re.IGNORECASE)
    if m:
        return float(m.group(1)), float(m.group(2))

    return None, None


# ── CSV parsing ─────────────────────────────────────────────────────────────

# Expected CSV column aliases (lowered)
_NAME_COLS = {"marker", "test", "test name", "analyte", "component", "name", "biomarker"}
_VALUE_COLS = {"value", "result", "result value", "your value", "your result"}
_UNIT_COLS = {"unit", "units", "uom"}
_REF_COLS = {"reference", "ref range", "reference range", "reference interval", "normal range", "range"}
_FLAG_COLS = {"flag", "status", "indicator", "abnormal"}


def parse_csv(csv_bytes: bytes) -> list[ParsedMarker]:
    """Parse a CSV blood-test report.

    Detects column roles heuristically from header names. Supports both
    wide (one marker per column) and long (one marker per row) formats.
    """
    text = csv_bytes.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))

    rows = list(reader)
    if len(rows) < 2:
        logger.warning("CSV has fewer than 2 rows — nothing to parse")
        return []

    header = [c.strip().lower() for c in rows[0]]

    # Identify column indices
    name_idx = _find_col(header, _NAME_COLS)
    value_idx = _find_col(header, _VALUE_COLS)
    unit_idx = _find_col(header, _UNIT_COLS)
    ref_idx = _find_col(header, _REF_COLS)
    flag_idx = _find_col(header, _FLAG_COLS)

    # If no explicit name/value columns, try wide format:
    # row[0] = marker name, row[1] = value, etc.
    if name_idx is None and value_idx is None:
        if len(header) >= 2:
            name_idx, value_idx = 0, 1
            if len(header) >= 3:
                unit_idx = 2
            if len(header) >= 4:
                ref_idx = 3

    if name_idx is None or value_idx is None:
        logger.warning("Cannot determine CSV column layout")
        return []

    markers: list[ParsedMarker] = []

    for row in rows[1:]:
        if len(row) <= max(name_idx, value_idx):
            continue

        raw_name = row[name_idx].strip()
        raw_value = row[value_idx].strip()

        # Skip empty or non-numeric values
        try:
            value = float(re.sub(r"[<>≤≥]", "", raw_value))
        except (ValueError, TypeError):
            continue

        resolved = _normalise_marker(raw_name)
        if resolved is None:
            # Keep as-is with a sanitised key
            canonical = re.sub(r"[^A-Za-z0-9_]", "_", raw_name.upper())
            display = raw_name.title()
            unit = row[unit_idx].strip() if (unit_idx is not None and len(row) > unit_idx) else ""
        else:
            canonical, display, unit = resolved
            # Prefer unit from file if present
            if unit_idx is not None and len(row) > unit_idx and row[unit_idx].strip():
                unit = row[unit_idx].strip()

        # Reference range
        ref_low, ref_high = None, None
        if ref_idx is not None and len(row) > ref_idx:
            ref_low, ref_high = _parse_ref_range(row[ref_idx])
        if ref_low is None and ref_high is None:
            defaults = DEFAULT_REFERENCE_RANGES.get(canonical)
            if defaults:
                ref_low, ref_high = defaults

        # Flag
        flag: str | None = None
        if flag_idx is not None and len(row) > flag_idx:
            raw_flag = row[flag_idx].strip().upper()
            if raw_flag in ("L", "LOW"):
                flag = "L"
            elif raw_flag in ("H", "HIGH"):
                flag = "H"
            elif raw_flag in ("N", "NORMAL", ""):
                flag = "N"
        if flag is None:
            flag = _compute_flag(value, ref_low, ref_high)

        markers.append(ParsedMarker(
            marker_name=canonical,
            marker_display_name=display,
            value=value,
            unit=unit,
            reference_low=ref_low,
            reference_high=ref_high,
            flag=flag,
        ))

    logger.info("Parsed %d markers from CSV", len(markers))
    return markers


def _find_col(header: list[str], aliases: set[str]) -> int | None:
    for i, col in enumerate(header):
        if col in aliases:
            return i
    return None


# ── PDF parsing ─────────────────────────────────────────────────────────────

# Regex to extract "MarkerName  Value  Unit  RefRange" from typical lab PDFs.
# Matches lines like:
#   Total Cholesterol    210    mg/dL    <200
#   HDL Cholesterol      55     mg/dL    40 - 60
#   Glucose              95     mg/dL    70 - 100  N
_RESULT_LINE_RE = re.compile(
    r"^"
    r"(?P<name>[A-Za-z][A-Za-z0-9 /(),\-]+?)"     # marker name
    r"\s{2,}"                                       # gap (2+ spaces)
    r"(?P<value>[<>≤≥]?\s*[\d.]+)"                  # numeric value
    r"\s+"                                          # space
    r"(?P<unit>[A-Za-z/%][A-Za-z0-9/%.*² ]{0,20})"  # unit
    r"(?:\s{2,}(?P<ref>[<>≤≥\d.\- –—to]+))?"        # optional ref range
    r"(?:\s+(?P<flag>[LHN]))?"                       # optional flag
    r"\s*$",
    re.IGNORECASE,
)


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from a PDF. Uses PyPDF2."""
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        logger.error("PyPDF2 is not installed — cannot parse PDF blood reports")
        return ""

    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n".join(pages)


def parse_pdf(pdf_bytes: bytes) -> list[ParsedMarker]:
    """Parse a PDF blood-test report by extracting text and matching markers."""
    full_text = _extract_pdf_text(pdf_bytes)
    if not full_text:
        logger.warning("No text extracted from PDF")
        return []

    markers: list[ParsedMarker] = []
    seen_keys: set[str] = set()

    for line in full_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        m = _RESULT_LINE_RE.match(line)
        if not m:
            continue

        raw_name = m.group("name").strip()
        raw_value = m.group("value").strip()
        raw_unit = m.group("unit").strip()
        raw_ref = (m.group("ref") or "").strip()
        raw_flag = (m.group("flag") or "").strip().upper()

        try:
            value = float(re.sub(r"[<>≤≥]", "", raw_value))
        except (ValueError, TypeError):
            continue

        resolved = _normalise_marker(raw_name)
        if resolved is None:
            canonical = re.sub(r"[^A-Za-z0-9_]", "_", raw_name.upper())
            display = raw_name.title()
            unit = raw_unit
        else:
            canonical, display, unit = resolved
            if raw_unit:
                unit = raw_unit

        # Deduplicate (first occurrence wins)
        if canonical in seen_keys:
            continue
        seen_keys.add(canonical)

        ref_low, ref_high = _parse_ref_range(raw_ref)
        if ref_low is None and ref_high is None:
            defaults = DEFAULT_REFERENCE_RANGES.get(canonical)
            if defaults:
                ref_low, ref_high = defaults

        flag: str | None = None
        if raw_flag in ("L", "H", "N"):
            flag = raw_flag
        else:
            flag = _compute_flag(value, ref_low, ref_high)

        markers.append(ParsedMarker(
            marker_name=canonical,
            marker_display_name=display,
            value=value,
            unit=unit,
            reference_low=ref_low,
            reference_high=ref_high,
            flag=flag,
        ))

    logger.info("Parsed %d markers from PDF", len(markers))
    return markers


# ── Unified entry point ────────────────────────────────────────────────────

def parse_blood_file(file_bytes: bytes, file_type: str) -> list[ParsedMarker]:
    """Dispatch to the correct parser based on file type.

    Args:
        file_bytes: Raw file content.
        file_type: ``"csv"`` or ``"pdf"``.

    Returns:
        List of standardised ParsedMarker instances.
    """
    if file_type == "csv":
        return parse_csv(file_bytes)
    if file_type == "pdf":
        return parse_pdf(file_bytes)
    logger.warning("Unsupported blood file type: %s", file_type)
    return []


# ── Delta / change computation ──────────────────────────────────────────────

@dataclass
class MarkerDelta:
    """Change in a single biomarker between two uploads."""

    marker_name: str
    marker_display_name: str
    previous_value: float
    current_value: float
    unit: str
    absolute_change: float
    percent_change: float      # e.g. -10.5 means a 10.5% decrease
    direction: str             # "increased", "decreased", "unchanged"
    previous_flag: str | None
    current_flag: str | None
    improved: bool | None      # True if moved closer to normal range
    reference_low: float | None = None
    reference_high: float | None = None


def compute_deltas(
    previous_markers: list[dict],
    current_markers: list[dict],
) -> list[MarkerDelta]:
    """Compare two sets of blood results and compute per-marker deltas.

    Args:
        previous_markers: List of dicts with marker_name, value, unit, flag,
                          reference_low, reference_high, marker_display_name.
        current_markers: Same structure.

    Returns:
        Sorted list of MarkerDelta (largest absolute % change first).
    """
    prev_by_name: dict[str, dict] = {m["marker_name"]: m for m in previous_markers}
    curr_by_name: dict[str, dict] = {m["marker_name"]: m for m in current_markers}

    shared = set(prev_by_name) & set(curr_by_name)
    deltas: list[MarkerDelta] = []

    for name in shared:
        prev = prev_by_name[name]
        curr = curr_by_name[name]

        prev_val = prev["value"]
        curr_val = curr["value"]
        abs_change = curr_val - prev_val
        pct_change = (abs_change / prev_val * 100) if prev_val != 0 else 0.0

        if abs(pct_change) < 0.5:
            direction = "unchanged"
        elif abs_change > 0:
            direction = "increased"
        else:
            direction = "decreased"

        ref_low = curr.get("reference_low") or prev.get("reference_low")
        ref_high = curr.get("reference_high") or prev.get("reference_high")

        improved = _did_improve(prev_val, curr_val, ref_low, ref_high)

        deltas.append(MarkerDelta(
            marker_name=name,
            marker_display_name=curr.get("marker_display_name", name),
            previous_value=round(prev_val, 2),
            current_value=round(curr_val, 2),
            unit=curr.get("unit", prev.get("unit", "")),
            absolute_change=round(abs_change, 2),
            percent_change=round(pct_change, 1),
            direction=direction,
            previous_flag=prev.get("flag"),
            current_flag=curr.get("flag"),
            improved=improved,
            reference_low=ref_low,
            reference_high=ref_high,
        ))

    deltas.sort(key=lambda d: abs(d.percent_change), reverse=True)
    return deltas


def _did_improve(
    prev_val: float,
    curr_val: float,
    ref_low: float | None,
    ref_high: float | None,
) -> bool | None:
    """Determine if a marker value moved closer to the normal range."""
    if ref_low is None or ref_high is None:
        return None

    midpoint = (ref_low + ref_high) / 2
    prev_dist = abs(prev_val - midpoint)
    curr_dist = abs(curr_val - midpoint)

    if abs(prev_dist - curr_dist) < 0.01:
        return None
    return curr_dist < prev_dist


# ── Genome cross-referencing ────────────────────────────────────────────────

# Maps genome risk categories / rsIDs to the blood markers they affect.
# Used to generate personalised insights when blood data arrives.
GENOME_BLOOD_CROSS_REF: dict[str, dict] = {
    # APOE ε4 → lipid panel
    "rs429358": {
        "markers": ["LDL", "TOTAL_CHOLESTEROL", "HDL", "TRIGLYCERIDES"],
        "risk_category": "cardiovascular",
        "insight_template": (
            "As an APOE ε4 carrier, your {marker} level of {value} {unit} is "
            "particularly relevant. APOE ε4 is associated with higher LDL and "
            "cardiovascular risk. {trend_note}"
        ),
    },
    # TCF7L2 → glucose / HbA1c
    "rs7903146": {
        "markers": ["GLUCOSE", "HBA1C", "INSULIN", "TRIGLYCERIDES"],
        "risk_category": "metabolic",
        "insight_template": (
            "Your TCF7L2 variant (rs7903146) increases type-2 diabetes risk. "
            "Your {marker} of {value} {unit} {flag_note}. {trend_note}"
        ),
    },
    # MTHFR → homocysteine, folate, B12
    "rs1801133": {
        "markers": ["HOMOCYSTEINE", "FOLATE", "VITAMIN_B12"],
        "risk_category": "nutritional",
        "insight_template": (
            "Your MTHFR C677T variant (rs1801133) affects folate metabolism. "
            "Your {marker} of {value} {unit} {flag_note}. {trend_note}"
        ),
    },
    # FTO → metabolic markers
    "rs9939609": {
        "markers": ["GLUCOSE", "HBA1C", "TRIGLYCERIDES", "TOTAL_CHOLESTEROL"],
        "risk_category": "metabolic",
        "insight_template": (
            "Your FTO variant (rs9939609) is associated with obesity and "
            "metabolic risk. Your {marker} of {value} {unit} {flag_note}. "
            "{trend_note}"
        ),
    },
    # IL-6 → inflammatory markers
    "rs1800795": {
        "markers": ["CRP", "HS_CRP", "ESR"],
        "risk_category": "inflammatory",
        "insight_template": (
            "Your IL-6 promoter variant (rs1800795) may predispose to higher "
            "inflammation. Your {marker} of {value} {unit} {flag_note}. "
            "{trend_note}"
        ),
    },
    # TNF-α → inflammatory markers
    "rs1800629": {
        "markers": ["CRP", "HS_CRP", "ESR"],
        "risk_category": "inflammatory",
        "insight_template": (
            "Your TNF-α variant (rs1800629) is associated with inflammatory "
            "tendency. Your {marker} of {value} {unit} {flag_note}. "
            "{trend_note}"
        ),
    },
    # FADS1 → lipids, omega-3
    "rs174546": {
        "markers": ["TRIGLYCERIDES", "HDL", "LDL"],
        "risk_category": "nutritional",
        "insight_template": (
            "Your FADS1 variant (rs174546) affects fatty acid metabolism. "
            "Your {marker} of {value} {unit} {flag_note}. {trend_note}"
        ),
    },
}


@dataclass
class GenomeBloodInsight:
    """A single insight linking genome data to blood test results."""

    rsid: str
    risk_category: str
    marker_name: str
    marker_display_name: str
    value: float
    unit: str
    flag: str | None
    insight: str
    priority: int = 5  # 1 = highest


def cross_reference_genome(
    blood_markers: list[dict],
    user_rsids: set[str],
    deltas: list[MarkerDelta] | None = None,
) -> list[GenomeBloodInsight]:
    """Generate insights by cross-referencing user's genome variants with blood results.

    Args:
        blood_markers: Current blood results (list of dicts with marker_name, value, etc.).
        user_rsids: Set of rsIDs present in the user's genome (non-ref genotype).
        deltas: Optional change deltas for trend-aware insights.

    Returns:
        List of GenomeBloodInsight ordered by priority.
    """
    marker_by_name: dict[str, dict] = {m["marker_name"]: m for m in blood_markers}
    delta_by_name: dict[str, MarkerDelta] = {}
    if deltas:
        delta_by_name = {d.marker_name: d for d in deltas}

    insights: list[GenomeBloodInsight] = []

    for rsid in user_rsids:
        xref = GENOME_BLOOD_CROSS_REF.get(rsid)
        if not xref:
            continue

        for marker_key in xref["markers"]:
            marker = marker_by_name.get(marker_key)
            if not marker:
                continue

            value = marker["value"]
            unit = marker.get("unit", "")
            flag = marker.get("flag")

            # Build flag note
            if flag == "H":
                flag_note = "is above the normal range"
            elif flag == "L":
                flag_note = "is below the normal range"
            else:
                flag_note = "is within the normal range"

            # Build trend note from deltas
            trend_note = ""
            delta = delta_by_name.get(marker_key)
            if delta:
                if delta.direction == "decreased":
                    trend_note = (
                        f"It has decreased {abs(delta.percent_change):.1f}% since "
                        f"your previous test — "
                        + ("a positive trend." if delta.improved else "worth monitoring.")
                    )
                elif delta.direction == "increased":
                    trend_note = (
                        f"It has increased {abs(delta.percent_change):.1f}% since "
                        f"your previous test — "
                        + ("a positive trend." if delta.improved else "worth monitoring.")
                    )
                else:
                    trend_note = "It has remained stable since your previous test."

            insight_text = xref["insight_template"].format(
                marker=marker.get("marker_display_name", marker_key),
                value=value,
                unit=unit,
                flag_note=flag_note,
                trend_note=trend_note,
            )

            # Higher priority for flagged markers with genome risk
            priority = 5
            if flag in ("H", "L"):
                priority = 2
            if delta and delta.improved is False:
                priority = 1

            insights.append(GenomeBloodInsight(
                rsid=rsid,
                risk_category=xref["risk_category"],
                marker_name=marker_key,
                marker_display_name=marker.get("marker_display_name", marker_key),
                value=value,
                unit=unit,
                flag=flag,
                insight=insight_text,
                priority=priority,
            ))

    insights.sort(key=lambda i: i.priority)
    logger.info("Generated %d genome–blood cross-reference insights", len(insights))
    return insights
