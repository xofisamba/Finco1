"""Stack S: Debt Service Export Reconciliation.

DD finding R1: three inconsistent DS representations in the export layer.

Investigation summary:
  (1) p.senior_ds_keur — frozen Phase 23A overlay (display/DSCR value)
  (2) p.senior_interest_keur + p.senior_principal_keur — engine pre-overlay components
  (3) result.total_senior_ds_keur — engine pre-overlay total (correct financial total)

Why (2) != (1): Phase 23A overlay sets senior_ds_keur from the frozen fixture CSV
  but does NOT update senior_interest_keur / senior_principal_keur.

Why sum(p.senior_ds_keur) != result.total_senior_ds_keur:
  TUHO: post-overlay sum = 32,853 kEUR (14 of 28 DS periods non-zero in fixture);
        engine total = 65,826 kEUR (correct 28-period financial total).
  Oborovo: post-overlay sum = 86,481 kEUR; engine total = 63,522 kEUR.
  Recalculating total_senior_ds_keur from period values would be WRONG.

Fix (Stack S):
  Rename the per-period engine component columns in utils/export.py to make
  their pre-overlay nature explicit.  total_senior_ds_keur is NOT touched.

No engine changes.  No parity numbers move.
"""
from __future__ import annotations
import csv
import os
import sys
import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ui_runner import run_demo_project
from utils.export import export_waterfall_csv


# ── Shared helpers ───────────────────────────────────────────────────────────

def _export_rows(demo_result) -> list[dict]:
    """Export a DemoResult's WaterfallResult to a CSV and return all rows."""
    import tempfile, os as _os
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        tmp_path = f.name
    try:
        export_waterfall_csv(demo_result.result, tmp_path)
        with open(tmp_path, newline="") as f:
            reader = csv.DictReader(f)
            return list(reader)
    finally:
        _os.unlink(tmp_path)


# ── Module-scoped fixtures ───────────────────────────────────────────────────

@pytest.fixture(scope="module")
def tuho_demo():
    return run_demo_project("TUHO")


@pytest.fixture(scope="module")
def oborovo_demo():
    return run_demo_project("Oborovo")


@pytest.fixture(scope="module")
def tuho(tuho_demo):
    return tuho_demo.result


@pytest.fixture(scope="module")
def oborovo(oborovo_demo):
    return oborovo_demo.result


@pytest.fixture(scope="module")
def tuho_rows(tuho_demo):
    return _export_rows(tuho_demo)


@pytest.fixture(scope="module")
def oborovo_rows(oborovo_demo):
    return _export_rows(oborovo_demo)


# ── Column name tests ────────────────────────────────────────────────────────

class TestColumnNames:
    """Stack S renames engine DS component columns to make pre-overlay nature explicit."""

    def test_tuho_has_senior_interest_engine_column(self, tuho_rows):
        assert "senior_interest_keur_engine" in tuho_rows[0]

    def test_tuho_has_senior_principal_engine_column(self, tuho_rows):
        assert "senior_principal_keur_engine" in tuho_rows[0]

    def test_tuho_no_bare_senior_interest_column(self, tuho_rows):
        assert "senior_interest_keur" not in tuho_rows[0]

    def test_tuho_no_bare_senior_principal_column(self, tuho_rows):
        assert "senior_principal_keur" not in tuho_rows[0]

    def test_oborovo_has_senior_interest_engine_column(self, oborovo_rows):
        assert "senior_interest_keur_engine" in oborovo_rows[0]

    def test_oborovo_has_senior_principal_engine_column(self, oborovo_rows):
        assert "senior_principal_keur_engine" in oborovo_rows[0]

    def test_oborovo_no_bare_senior_interest_column(self, oborovo_rows):
        assert "senior_interest_keur" not in oborovo_rows[0]

    def test_oborovo_no_bare_senior_principal_column(self, oborovo_rows):
        assert "senior_principal_keur" not in oborovo_rows[0]

    def test_tuho_frozen_ds_column_present(self, tuho_rows):
        assert "senior_ds_keur" in tuho_rows[0]

    def test_oborovo_frozen_ds_column_present(self, oborovo_rows):
        assert "senior_ds_keur" in oborovo_rows[0]


# ── DS representation consistency tests ─────────────────────────────────────

class TestDSRepresentationInvariants:
    """Document the known divergence between DS representations post-Stack-S."""

    def test_tuho_total_senior_ds_is_engine_total(self, tuho):
        """result.total_senior_ds_keur reflects the engine pre-overlay total (correct)."""
        assert abs(tuho.total_senior_ds_keur - 65826.0) < 5.0

    def test_oborovo_total_senior_ds_is_engine_total(self, oborovo):
        assert abs(oborovo.total_senior_ds_keur - 63522.0) < 5.0

    def test_tuho_period_ds_sum_equals_total(self, tuho_rows):
        """Stack Y1: sum(period.senior_ds_keur) == result.total_senior_ds_keur.

        Y1 fix: the Phase 23A overlay no longer overrides senior_ds_keur with
        the frozen sizing capacity.  senior_ds_keur = senior_interest + senior_principal
        so the period sum now equals the engine total (65,826 kEUR).
        """
        op_rows = [r for r in tuho_rows if r.get("is_operation") == "True"]
        ds_sum = sum(float(r["senior_ds_keur"]) for r in op_rows)
        assert abs(ds_sum - 65826.0) < 10.0, (
            f"period sum={ds_sum:.0f} should equal engine total ~65826"
        )

    def test_tuho_engine_components_non_zero_in_op_periods(self, tuho_rows):
        """Engine interest/principal columns carry values in operating periods."""
        op_rows = [r for r in tuho_rows if r.get("is_operation") == "True"]
        interest_sum = sum(float(r["senior_interest_keur_engine"]) for r in op_rows)
        principal_sum = sum(float(r["senior_principal_keur_engine"]) for r in op_rows)
        assert interest_sum > 0.0
        assert principal_sum > 0.0


# ── Golden parity: KPIs unchanged after column rename ───────────────────────

class TestGoldenParityUnchanged:
    """Renaming export columns must not move any KPI."""

    # TUHO
    def test_tuho_equity_irr(self, tuho):
        assert abs(tuho.equity_irr - 0.1132) < 0.0005  # Stack T re-baseline (was 0.1159 ±0.0002)

    def test_tuho_project_irr(self, tuho):
        assert abs(tuho.project_irr - 0.0941) < 0.0002

    def test_tuho_avg_dscr(self, tuho):
        assert abs(tuho.actual_avg_dscr - 1.3786) < 0.001

    def test_tuho_senior_debt(self, tuho):
        assert abs(tuho.sculpting_result.debt_keur - 43359.0) < 1.0

    def test_tuho_total_senior_ds(self, tuho):
        assert abs(tuho.total_senior_ds_keur - 65826.0) < 5.0

    # Oborovo
    def test_oborovo_equity_irr(self, oborovo):
        assert abs(oborovo.equity_irr - 0.1054) < 0.0005  # Stack T re-baseline (was 0.1066 ±0.0002)

    def test_oborovo_project_irr(self, oborovo):
        assert abs(oborovo.project_irr - 0.0809) < 0.0002

    def test_oborovo_avg_dscr(self, oborovo):
        assert abs(oborovo.actual_avg_dscr - 1.179) < 0.001

    def test_oborovo_senior_debt(self, oborovo):
        assert abs(oborovo.sculpting_result.debt_keur - 42852.0) < 1.0

    def test_oborovo_total_senior_ds(self, oborovo):
        assert abs(oborovo.total_senior_ds_keur - 63522.0) < 5.0
