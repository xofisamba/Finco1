"""Phase A0 metadata surface audit documentation locks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "docs" / "phase_a0_metadata_surface_audit.md"
REPORT_PATH = REPO_ROOT / "reports" / "phase_a0_metadata_surface_audit.json"


@pytest.fixture(scope="module")
def doc_text() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def report() -> dict:
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


class TestFilesExist:
    def test_doc_exists(self):
        assert DOC_PATH.is_file()

    def test_report_exists(self):
        assert REPORT_PATH.is_file()


class TestAuditScope:
    def test_report_is_analysis_only(self, report):
        assert report["type"] == "analysis_only_docs_report_test"
        assert report["status"] == "analysis_only"

    @pytest.mark.parametrize(
        "boundary",
        [
            "no_runtime_changes",
            "no_ui_changes",
            "no_model_changes",
            "no_persistence_changes",
            "no_export_changes",
            "no_schema_changes",
            "no_formula_changes",
            "no_frontend_financial_calculation",
        ],
    )
    def test_boundaries_are_pinned(self, report, boundary):
        assert boundary in report["boundaries"]


class TestReadinessMatrix:
    def test_priority_metrics_covered(self, report):
        metrics = {item["metric"] for item in report["priority_metrics"]}
        assert metrics == {
            "Revenue",
            "EBITDA",
            "OPEX",
            "CAPEX Total",
            "Senior Debt",
            "DSCR",
            "CFADS",
            "Tax",
            "Distributions",
            "Sponsor returns",
        }

    def test_classifications_cover_ready_partial_and_not_ready(self, report):
        classes = {item["derivation_ready"] for item in report["priority_metrics"]}
        assert classes == {"READY", "PARTIAL", "NOT_READY"}

    def test_low_risk_bucket_contains_ebitda_and_existing_a1(self, report):
        low_risk = set(report["low_risk_derivations"])
        assert "EBITDA" in low_risk
        assert "DSCR_existing_A1" in low_risk
        assert "CFADS_existing_A1" in low_risk

    def test_high_risk_bucket_avoids_distribution_and_sponsor(self, report):
        high_risk = set(report["high_risk_derivations"])
        assert "Distributions" in high_risk
        assert "Sponsor returns" in high_risk


class TestRecommendedSequence:
    def test_sequence_starts_with_ebitda_and_revenue(self, report):
        sequence = report["recommended_a2_sequence"]
        assert sequence[0]["phase"] == "A2-1"
        assert sequence[0]["metric"] == "EBITDA"
        assert sequence[1]["phase"] == "A2-2"
        assert sequence[1]["metric"] == "Revenue"

    def test_metrics_to_avoid_for_now_are_explicit(self, report, doc_text):
        assert report["metrics_to_avoid_for_now"] == [
            "Distributions",
            "Sponsor returns",
        ]
        assert "metrics to avoid for now" in doc_text.lower()


class TestSourcePolicy:
    def test_source_hierarchy_is_documented(self, report, doc_text):
        assert report["source_hierarchy"] == [
            "runtime_result",
            "output_table_builders",
            "audit_and_export_evidence",
            "persistence_only_for_baseline_non_runtime_metrics",
        ]
        assert "source hierarchy for future derivations" in doc_text.lower()

    def test_frontend_calculation_is_rejected(self, report, doc_text):
        assert report["frontend_calculation_policy"] == "rejected"
        assert "must not" in doc_text.lower()
        assert "calculate financial values in javascript" in doc_text.lower()


class TestMetricDetails:
    def test_dscr_and_cfads_are_ready(self, report):
        lookup = {item["metric"]: item for item in report["priority_metrics"]}
        assert lookup["DSCR"]["derivation_ready"] == "READY"
        assert lookup["CFADS"]["derivation_ready"] == "READY"

    def test_capex_and_senior_debt_are_partial(self, report):
        lookup = {item["metric"]: item for item in report["priority_metrics"]}
        assert lookup["CAPEX Total"]["derivation_ready"] == "PARTIAL"
        assert lookup["Senior Debt"]["derivation_ready"] == "PARTIAL"

    def test_revenue_missing_components_are_honest(self, report):
        lookup = {item["metric"]: item for item in report["priority_metrics"]}
        missing = set(lookup["Revenue"]["missing_components"])
        assert "ppa_vs_merchant_split" in missing
        assert "co2_and_balancing_split" in missing

    def test_sponsor_returns_not_ready(self, report):
        lookup = {item["metric"]: item for item in report["priority_metrics"]}
        sponsor = lookup["Sponsor returns"]
        assert sponsor["derivation_ready"] == "NOT_READY"
        assert sponsor["risk_level"] == "high"


class TestContextKeysAndRc1:
    def test_future_context_keys_documented(self, report):
        keys = report["additional_read_only_context_keys"]
        assert "Revenue" in keys
        assert "EBITDA" in keys
        assert "CAPEX Total" in keys
        assert "Senior Debt" in keys
        assert "Tax" in keys

    def test_rc1_sha_pinned(self, report):
        assert report["rc1_frozen_sha"] == "b425a0708719eaa5e1d922b1008e5609758e0ad4"

    def test_recommendation_is_pass(self, report):
        assert report["recommendation"] == "PASS"
