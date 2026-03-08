"""Tests for ML analyzer (InnerAge, optimized zones, predictions)."""

import json
import pytest

from app import create_app
from app.extensions import db as _db


@pytest.fixture()
def app():
    flask_app = create_app("testing")
    with flask_app.app_context():
        _db.create_all()
    yield flask_app
    with flask_app.app_context():
        _db.session.remove()
        _db.drop_all()


class TestPhenoAge:
    """Test the PhenoAge biological age calculation."""

    def test_calculate_phenoage_basic(self, app):
        from app.utils.ml_analyzer import calculate_phenoage

        with app.app_context():
            biomarkers = {
                "albumin": 4.5,
                "creatinine": 0.9,
                "glucose": 90,
                "crp": 0.5,
                "lymphocyte_pct": 30,
                "mcv": 90,
                "rdw": 13,
                "alkaline_phosphatase": 60,
                "white_blood_cells": 6.0,
            }
            result = calculate_phenoage(biomarkers, chronological_age=40)
            assert isinstance(result, dict)
            assert "phenoage" in result
            assert isinstance(result["phenoage"], float)
            assert 20 < result["phenoage"] < 80

    def test_calculate_phenoage_missing_markers(self, app):
        from app.utils.ml_analyzer import calculate_phenoage

        with app.app_context():
            biomarkers = {"albumin": 4.5, "creatinine": 0.9}
            result = calculate_phenoage(biomarkers, chronological_age=40)
            assert result is not None  # Should handle gracefully


class TestOptimizedZones:
    """Test optimized biomarker zone computation."""

    def test_compute_zones_basic(self, app):
        from app.utils.ml_analyzer import compute_optimized_zone

        with app.app_context():
            result = compute_optimized_zone(
                marker_name="total_cholesterol",
                current_value=200,
                age=45,
                sex="male",
            )
            assert isinstance(result, dict)
            assert "optimal_low" in result
            assert "optimal_high" in result
            assert "zone_status" in result
            assert result["zone_status"] in ("optimal", "at_risk", "out_of_range")

    def test_compute_zones_unknown_marker(self, app):
        from app.utils.ml_analyzer import compute_optimized_zone

        with app.app_context():
            result = compute_optimized_zone(
                marker_name="nonexistent_marker",
                current_value=50,
                age=30,
                sex="female",
            )
            # Should return a default zone without error
            assert isinstance(result, dict)


class TestInnerAge:
    """Test ensemble InnerAge calculation."""

    def test_calculate_inner_age(self, app):
        from app.utils.ml_analyzer import calculate_inner_age

        with app.app_context():
            result = calculate_inner_age(
                chronological_age=45,
                blood_biomarkers={
                    "albumin": 4.5, "creatinine": 0.9, "glucose": 90,
                    "crp": 0.5, "lymphocyte_pct": 30, "mcv": 90,
                    "rdw": 13, "alkaline_phosphatase": 60,
                    "white_blood_cells": 6.0,
                },
            )
            assert isinstance(result, dict)
            assert "biological_age" in result
            assert "model_type" in result
            assert 20 < result["biological_age"] < 80


class TestPredictTrend:
    """Test biomarker trend prediction with fallback cascade."""

    def test_predict_linear_fallback(self, app):
        from app.utils.ml_analyzer import predict_biomarker_trend

        with app.app_context():
            # Few data points → should fall back to linear regression
            history = [
                {"date": "2024-01-01", "value": 200},
                {"date": "2024-04-01", "value": 195},
                {"date": "2024-07-01", "value": 190},
            ]
            result = predict_biomarker_trend("total_cholesterol", history)
            assert isinstance(result, dict)
            assert "model_type" in result
            assert "trend_direction" in result
            assert result["trend_direction"] in ("improving", "stable", "declining")
            assert "forecast" in result
