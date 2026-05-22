"""Phase 9 — DistributionAccount dual-run validation integration tests.

AUDIT-ONLY — no runtime routing.
DA remains non-authoritative.
Tests TUHO + Oborovo with runtime flag OFF/ON.
"""

import pytest
from app.api.project_runner import run_project


class TestDualRunValidationFlag:
    """use_dualrun_validation flag must be propagated correctly."""

    def test_flag_off_returns_no_dualrun(self):
        r = run_project("TUHO", "Base", use_dualrun_validation=False)
        assert r.get("dualrun_validation") is None

    def test_flag_on_returns_dualrun(self):
        r = run_project("TUHO", "Base", use_dualrun_validation=True)
        assert r["dualrun_validation"] is not None

    def test_flag_on_oborovo_returns_dualrun(self):
        r = run_project("Oborovo", "Base", use_dualrun_validation=True)
        assert r["dualrun_validation"] is not None


class TestDualRunTUHOValidation:
    """TUHO dual-run validation results."""

    def test_phase_c_ready(self):
        r = run_project("TUHO", "Base", use_dualrun_validation=True)
        d = r["dualrun_validation"]
        assert d.phase_c_ready is True

    def test_runtime_unchanged(self):
        r = run_project("TUHO", "Base", use_dualrun_validation=True)
        d = r["dualrun_validation"]
        assert d.runtime_unchanged is True

    def test_sponsor_unchanged(self):
        r = run_project("TUHO", "Base", use_dualrun_validation=True)
        d = r["dualrun_validation"]
        assert d.sponsor_unchanged is True

    def test_shl_unchanged(self):
        r = run_project("TUHO", "Base", use_dualrun_validation=True)
        d = r["dualrun_validation"]
        assert d.shl_unchanged is True

    def test_r99_r102_still_blocked(self):
        r = run_project("TUHO", "Base", use_dualrun_validation=True)
        d = r["dualrun_validation"]
        assert d.r99_r102_still_blocked is True

    def test_no_blocking_periods(self):
        r = run_project("TUHO", "Base", use_dualrun_validation=True)
        d = r["dualrun_validation"]
        assert d.blocking_periods == 0

    def test_no_unexpected_diff_periods(self):
        r = run_project("TUHO", "Base", use_dualrun_validation=True)
        d = r["dualrun_validation"]
        assert d.unexpected_diff_periods == 0

    def test_runtime_distribution_total_reasonable(self):
        r = run_project("TUHO", "Base", use_dualrun_validation=True)
        d = r["dualrun_validation"]
        # TUHO total distributions ~174M
        assert 150_000 < d.total_runtime_distribution_keur < 200_000

    def test_all_invariants_held(self):
        r = run_project("TUHO", "Base", use_dualrun_validation=True)
        d = r["dualrun_validation"]
        assert d.all_invariants_held is True

    def test_economic_mode_produces_more_identical(self):
        r = run_project("TUHO", "Base", use_dualrun_validation=True)
        d = r["dualrun_validation"]
        # Economic mode should have >= identical periods vs governed
        assert d.identical_economic_periods >= d.identical_periods

    def test_governed_mode_da_zero(self):
        # In governed mode, DA is blocked by R99/R102 — distributions = 0
        r = run_project("TUHO", "Base", use_dualrun_validation=True)
        d = r["dualrun_validation"]
        assert d.total_da_governed_paid_keur == 0.0


class TestDualRunOborovoValidation:
    """Oborovo dual-run validation results."""

    def test_phase_c_ready(self):
        r = run_project("Oborovo", "Base", use_dualrun_validation=True)
        d = r["dualrun_validation"]
        assert d.phase_c_ready is True

    def test_runtime_unchanged(self):
        r = run_project("Oborovo", "Base", use_dualrun_validation=True)
        d = r["dualrun_validation"]
        assert d.runtime_unchanged is True

    def test_no_blocking_periods(self):
        r = run_project("Oborovo", "Base", use_dualrun_validation=True)
        d = r["dualrun_validation"]
        assert d.blocking_periods == 0

    def test_no_unexpected_diff_periods(self):
        r = run_project("Oborovo", "Base", use_dualrun_validation=True)
        d = r["dualrun_validation"]
        assert d.unexpected_diff_periods == 0

    def test_runtime_distribution_total_reasonable(self):
        r = run_project("Oborovo", "Base", use_dualrun_validation=True)
        d = r["dualrun_validation"]
        # Oborovo total distributions ~105M
        assert 90_000 < d.total_runtime_distribution_keur < 120_000

    def test_economic_mode_produces_more_identical(self):
        r = run_project("Oborovo", "Base", use_dualrun_validation=True)
        d = r["dualrun_validation"]
        assert d.identical_economic_periods >= d.identical_periods

    def test_governed_mode_da_zero(self):
        # In governed mode, DA is blocked by R99/R102 — distributions = 0
        r = run_project("Oborovo", "Base", use_dualrun_validation=True)
        d = r["dualrun_validation"]
        assert d.total_da_governed_paid_keur == 0.0


class TestDualRunResultStructure:
    """DualRunResult must have all required fields."""

    def test_tuho_result_has_all_fields(self):
        r = run_project("TUHO", "Base", use_dualrun_validation=True)
        d = r["dualrun_validation"]
        assert hasattr(d, "period_results")
        assert hasattr(d, "total_runtime_distribution_keur")
        assert hasattr(d, "total_da_governed_paid_keur")
        assert hasattr(d, "total_da_economic_paid_keur")
        assert hasattr(d, "identical_periods")
        assert hasattr(d, "rounding_periods")
        assert hasattr(d, "expected_gate_diff_periods")
        assert hasattr(d, "unexpected_diff_periods")
        assert hasattr(d, "blocking_periods")
        assert hasattr(d, "phase_c_ready")

    def test_period_results_are_tuple(self):
        r = run_project("TUHO", "Base", use_dualrun_validation=True)
        d = r["dualrun_validation"]
        assert isinstance(d.period_results, tuple)
        assert len(d.period_results) > 0

    def test_period_result_has_classification(self):
        r = run_project("TUHO", "Base", use_dualrun_validation=True)
        d = r["dualrun_validation"]
        for pr in d.period_results:
            assert pr.classification in (
                "IDENTICAL", "ROUNDING", "EXPECTED_GATE_DIFFERENCE", "UNEXPECTED", "BLOCKING"
            )


class TestDualRunKpisUnaffected:
    """KPIs must be identical regardless of use_dualrun_validation flag."""

    def test_tuho_irr_unchanged_by_flag(self):
        r_on = run_project("TUHO", "Base", use_dualrun_validation=True)
        r_off = run_project("TUHO", "Base", use_dualrun_validation=False)
        assert r_on["kpis"]["project_irr"] == r_off["kpis"]["project_irr"]
        assert r_on["kpis"]["equity_irr"] == r_off["kpis"]["equity_irr"]

    def test_oborovo_irr_unchanged_by_flag(self):
        r_on = run_project("Oborovo", "Base", use_dualrun_validation=True)
        r_off = run_project("Oborovo", "Base", use_dualrun_validation=False)
        assert r_on["kpis"]["project_irr"] == r_off["kpis"]["project_irr"]
        assert r_on["kpis"]["equity_irr"] == r_off["kpis"]["equity_irr"]


class TestDualRunRuntimeAuthoritative:
    """Runtime must remain authoritative in this branch."""

    def test_runtime_authoritative_true_in_all_periods(self):
        r = run_project("TUHO", "Base", use_dualrun_validation=True)
        d = r["dualrun_validation"]
        for pr in d.period_results:
            assert pr.runtime_authoritative is True

    def test_all_gate_diffs_are_expected(self):
        # All non-identical governed periods must be EXPECTED_GATE_DIFFERENCE
        r = run_project("TUHO", "Base", use_dualrun_validation=True)
        d = r["dualrun_validation"]
        for pr in d.period_results:
            if pr.classification not in ("IDENTICAL", "ROUNDING"):
                assert pr.classification == "EXPECTED_GATE_DIFFERENCE"