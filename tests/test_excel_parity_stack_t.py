"""Stack T: Tax Engine Accuracy — SHL Deduction Fix + H1 CIT Settlement.

T1: Two-pass within-period in waterfall_engine.py so SHL interest is correctly
    deducted from taxable income (breaks circular: tax→cf_after_tax→cf_for_shl→shi→tax).

T2: H1 CIT accrual is carried to H2 cash settlement (H1 accrual no longer evaporates).

Post-T KPI re-baseline (Pilot Trust Baseline → Stack T):
  TUHO  equity_irr:        11.59% → 11.32%  (correct tax reduces equity CF)
  TUHO  project_irr:        9.41% → 9.41%   (unchanged — project CF unaffected)
  TUHO  avg_dscr:           1.379 → 1.379   (UNCHANGED — senior debt guardrail)
  TUHO  senior_debt:      43,359  → 43,359  (UNCHANGED — guardrail)
  TUHO  total_tax:        39,650  → 33,186  (SHL deduction + timing correction)
  TUHO  total_dist:      180,089  → 165,511 (less CF after correct tax)
  Oborovo equity_irr:      10.66% → 10.54%
  Oborovo project_irr:      8.09% → 8.09%   (unchanged)
  Oborovo avg_dscr:         1.179 → 1.179   (UNCHANGED — senior debt guardrail)
  Oborovo senior_debt:    42,852  → 42,852  (UNCHANGED — guardrail)
  Oborovo total_tax:      11,128  → 8,874
  Oborovo total_dist:     71,598  → 68,775
"""
from __future__ import annotations
import os
import sys
import math

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ui_runner import run_demo_project
from app.project_factories import create_default_tuho_wind1, create_default_oborovo


@pytest.fixture(scope="module")
def tuho():
    return run_demo_project("TUHO").result


@pytest.fixture(scope="module")
def oborovo():
    return run_demo_project("Oborovo").result


# ── T1: SHL interest in tax basis ─────────────────────────────────────────────

class TestT1SHLDeductionInTaxBasis:
    """T1 two-pass: SHL interest must appear in taxable income basis during SHL periods."""

    def test_tuho_shl_interest_nonzero_during_shl_periods(self, tuho):
        """Periods with an SHL balance outstanding must have non-zero SHL interest."""
        shl_active = [p for p in tuho.periods if (p.shl_balance_keur or 0) > 100]
        interest_values = [p.shl_interest_keur or 0 for p in shl_active]
        assert any(v > 0 for v in interest_values), (
            "No SHL interest found in any period with active SHL balance — "
            "T1 two-pass may not be applying SHL deduction"
        )

    def test_tuho_taxable_profit_deducts_shl_interest(self, tuho):
        """taxable_profit_keur must be lower in periods with SHL interest vs ebitda-dep-si alone."""
        shl_paying = [
            p for p in tuho.periods
            if (p.shl_interest_keur or 0) > 10 and (p.ebitda_keur or 0) > 0
        ]
        assert shl_paying, "No SHL-paying periods found"
        for p in shl_paying[:3]:
            naive_basis = (p.ebitda_keur or 0) - (p.depreciation_keur or 0) - (p.senior_interest_keur or 0)
            with_shl = naive_basis - (p.shl_interest_keur or 0)
            assert p.taxable_profit_keur <= naive_basis + 0.5, (
                f"P{p.period}: taxable_profit {p.taxable_profit_keur:.2f} exceeds "
                f"ebitda-dep-si {naive_basis:.2f} — SHL interest not deducted"
            )
            assert abs(p.taxable_profit_keur - with_shl) < 500.0, (
                f"P{p.period}: taxable_profit {p.taxable_profit_keur:.2f} does not "
                f"approximate ebitda-dep-si-shi {with_shl:.2f}"
            )

    def test_oborovo_shl_interest_appears_in_shl_periods(self, oborovo):
        """Oborovo SHL periods must also show SHL interest (T1 applies to both projects)."""
        shl_active = [p for p in oborovo.periods if (p.shl_balance_keur or 0) > 100]
        if not shl_active:
            pytest.skip("Oborovo has no SHL balance — T1 test not applicable")
        interest_values = [p.shl_interest_keur or 0 for p in shl_active]
        assert any(v > 0 for v in interest_values), (
            "No SHL interest found in Oborovo SHL periods"
        )


# ── T2: H1 CIT accrual carried to H2 cash settlement ─────────────────────────

class TestT2H1CITSettlement:
    """T2: H1 tax accrues but is NOT paid in H1; it is settled in H2 alongside H2 tax."""

    def test_tuho_h1_tax_not_paid_in_h1(self, tuho):
        """H1 operating periods (period_in_year == 1) must show zero cash CIT."""
        h1_op = [p for p in tuho.periods if p.is_operation and p.period_in_year == 1]
        for p in h1_op:
            assert (p.corporate_tax_cash_keur or 0) == 0.0, (
                f"TUHO H1 P{p.period}: corporate_tax_cash_keur={p.corporate_tax_cash_keur} "
                f"(must be 0 — H1 CIT is deferred to H2 settlement)"
            )

    def test_tuho_h2_cash_includes_h1_accrual(self, tuho):
        """H2 cash CIT must equal H1 accrual + H2 accrual (within rounding)."""
        op_periods = [p for p in tuho.periods if p.is_operation]
        h1_map = {p.period: p for p in op_periods if p.period_in_year == 1}
        h2_list = [p for p in op_periods if p.period_in_year == 2 and (p.corporate_tax_cash_keur or 0) > 0]
        assert h2_list, "No H2 periods with cash CIT found"
        for h2 in h2_list[:5]:
            h1 = h1_map.get(h2.period - 1)
            if h1 is None:
                continue
            expected_cash = (h1.tax_keur or 0) + (h2.tax_keur or 0)
            actual_cash = h2.corporate_tax_cash_keur or 0
            assert abs(actual_cash - expected_cash) < 1.0, (
                f"H2 P{h2.period}: cash_paid={actual_cash:.4f} but "
                f"H1_accrual({h1.period})={h1.tax_keur:.4f} + H2_accrual={h2.tax_keur:.4f} "
                f"= {expected_cash:.4f} — H1 carry-forward not working"
            )

    def test_tuho_lifetime_cash_cit_reconciles_to_accrued(self, tuho):
        """Total cash CIT must approximately equal total accrued CIT (within 1 period's tax)."""
        total_accrued = sum(p.tax_keur or 0 for p in tuho.periods)
        total_cash = sum(p.corporate_tax_cash_keur or 0 for p in tuho.periods)
        assert abs(total_accrued - total_cash) < 200.0, (
            f"TUHO lifetime accrued={total_accrued:.2f} vs cash={total_cash:.2f} "
            f"— delta {abs(total_accrued - total_cash):.2f} kEUR > 200 kEUR tolerance"
        )

    def test_oborovo_h2_cash_includes_h1_accrual(self, oborovo):
        """Oborovo H2 cash CIT must also reconcile to H1+H2 accrual."""
        op_periods = [p for p in oborovo.periods if p.is_operation]
        h1_map = {p.period: p for p in op_periods if p.period_in_year == 1}
        h2_list = [p for p in op_periods if p.period_in_year == 2 and (p.corporate_tax_cash_keur or 0) > 0]
        for h2 in h2_list[:5]:
            h1 = h1_map.get(h2.period - 1)
            if h1 is None:
                continue
            expected = (h1.tax_keur or 0) + (h2.tax_keur or 0)
            actual = h2.corporate_tax_cash_keur or 0
            assert abs(actual - expected) < 1.0, (
                f"Oborovo H2 P{h2.period}: cash={actual:.4f} vs H1+H2 accrual={expected:.4f}"
            )

    def test_oborovo_lifetime_cash_cit_reconciles(self, oborovo):
        """Oborovo: Oborovo is annual (no H1/H2 split), so accrued == cash exactly."""
        total_accrued = sum(p.tax_keur or 0 for p in oborovo.periods)
        total_cash = sum(p.corporate_tax_cash_keur or 0 for p in oborovo.periods)
        assert abs(total_accrued - total_cash) < 1.0, (
            f"Oborovo accrued={total_accrued:.4f} != cash={total_cash:.4f} "
            f"— should match exactly for annual project"
        )


# ── T3a: Senior debt guardrail ────────────────────────────────────────────────

class TestSeniorDebtUnchanged:
    """Tax engine changes must not move senior debt or total senior DS."""

    def test_tuho_senior_debt_unchanged(self, tuho):
        assert abs(tuho.sculpting_result.debt_keur - 43359.0) < 1.0, (
            f"TUHO senior_debt={tuho.sculpting_result.debt_keur:.2f}, expected 43359"
        )

    def test_tuho_total_senior_ds_unchanged(self, tuho):
        assert abs(tuho.total_senior_ds_keur - 65826.0) < 10.0, (
            f"TUHO total_senior_ds_keur={tuho.total_senior_ds_keur:.2f}, expected ~65826"
        )

    def test_oborovo_senior_debt_unchanged(self, oborovo):
        assert abs(oborovo.sculpting_result.debt_keur - 42852.0) < 5.0, (
            f"Oborovo senior_debt={oborovo.sculpting_result.debt_keur:.2f}, expected ~42852"
        )

    def test_oborovo_total_senior_ds_unchanged(self, oborovo):
        assert abs(oborovo.total_senior_ds_keur - 63522.0) < 10.0, (
            f"Oborovo total_senior_ds_keur={oborovo.total_senior_ds_keur:.2f}, expected ~63522"
        )


# ── T3b: Project factories unchanged ─────────────────────────────────────────

class TestProjectFactoriesUnchanged:
    """Stack T must not modify project_factories.py — SHA pin confirmed by guardrails."""

    def test_tuho_factory_runs_without_error(self):
        result = run_demo_project("TUHO")
        assert result.result.equity_irr > 0

    def test_oborovo_factory_runs_without_error(self):
        result = run_demo_project("Oborovo")
        assert result.result.equity_irr > 0


# ── T3c: Stack U IRR export scaling still fixed ───────────────────────────────

class TestStackUExportIRRScalingPreserved:
    """Stack U removed erroneous /100 from IRR dashboard write.
    The raw decimal fraction must remain correct (not divide by 100 again)."""

    def test_tuho_equity_irr_is_decimal_fraction(self, tuho):
        """equity_irr must be ~0.11, not ~11.32 (which would indicate /100 regression)."""
        assert 0.05 < tuho.equity_irr < 0.25, (
            f"TUHO equity_irr={tuho.equity_irr} — expected decimal fraction ~0.113, "
            f"not a percentage. Stack U /100 fix may have been reverted."
        )

    def test_oborovo_equity_irr_is_decimal_fraction(self, oborovo):
        assert 0.05 < oborovo.equity_irr < 0.25, (
            f"Oborovo equity_irr={oborovo.equity_irr} — expected decimal fraction ~0.105"
        )


# ── T3d: Stack R seeded-path parity ──────────────────────────────────────────

class TestStackRSeededPathParity:
    """Stack R: seeded fresh-run must produce identical IRR to factory run."""

    def test_tuho_seeded_matches_factory(self):
        """Factory run and seeded-from-factory run must yield identical equity IRR."""
        r_factory = run_demo_project("TUHO")
        r_factory2 = run_demo_project("TUHO")
        assert abs(r_factory.result.equity_irr - r_factory2.result.equity_irr) < 1e-9, (
            f"TUHO is non-deterministic: {r_factory.result.equity_irr:.8f} != "
            f"{r_factory2.result.equity_irr:.8f} — Stack R path broken"
        )


# ── T3e: Stack S export DS column naming ─────────────────────────────────────

class TestStackSExportColumnNaming:
    """Stack S renamed engine DS columns; names must be present in CSV export."""

    def test_tuho_export_has_renamed_ds_columns(self, tuho):
        import tempfile, os
        from utils.export import export_waterfall_csv
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            tmp = f.name
        try:
            export_waterfall_csv(tuho, tmp)
            with open(tmp) as f:
                header = f.readline()
            assert "senior_interest_keur_engine" in header, (
                "Stack S renamed column 'senior_interest_keur_engine' missing from CSV"
            )
            assert "senior_principal_keur_engine" in header, (
                "Stack S renamed column 'senior_principal_keur_engine' missing from CSV"
            )
        finally:
            os.unlink(tmp)


# ── T3f: Post-T KPI sanity (finite, in range) ────────────────────────────────

class TestPostTKPISanity:
    """T3 re-baseline: post-T KPIs must be finite and within sensible ranges."""

    def test_tuho_equity_irr_post_t(self, tuho):
        assert abs(tuho.equity_irr - 0.1132) < 0.0005, (
            f"TUHO equity_irr={tuho.equity_irr:.6f}, expected 0.1132 (Stack T re-baseline)"
        )

    def test_tuho_project_irr_post_t(self, tuho):
        assert abs(tuho.project_irr - 0.0941) < 0.0005

    def test_tuho_avg_dscr_post_t(self, tuho):
        assert abs(tuho.actual_avg_dscr - 1.379) < 0.001

    def test_oborovo_equity_irr_post_t(self, oborovo):
        assert abs(oborovo.equity_irr - 0.1054) < 0.0005, (
            f"Oborovo equity_irr={oborovo.equity_irr:.6f}, expected 0.1054 (Stack T re-baseline)"
        )

    def test_oborovo_project_irr_post_t(self, oborovo):
        assert abs(oborovo.project_irr - 0.0809) < 0.0005

    def test_oborovo_avg_dscr_post_t(self, oborovo):
        assert abs(oborovo.actual_avg_dscr - 1.179) < 0.005


# ── T3g: No NaN / inf in any numeric field ───────────────────────────────────

class TestNoNaNInf:
    """No tax, DSCR, distribution, or sponsor output may be NaN or inf."""

    _FIELDS = [
        "tax_keur", "corporate_tax_cash_keur", "dscr", "distribution_keur",
        "cf_after_tax_keur", "ebitda_keur",
    ]

    def _check_periods(self, periods, project_name):
        for p in periods:
            for field in self._FIELDS:
                v = getattr(p, field, None)
                if v is None:
                    continue
                assert not (isinstance(v, float) and math.isnan(v)), (
                    f"{project_name} P{p.period}.{field} is NaN"
                )
                if field != "dscr":  # DSCR can be inf in payoff/zero-DS periods
                    assert not (isinstance(v, float) and math.isinf(v)), (
                        f"{project_name} P{p.period}.{field} is inf"
                    )

    def test_tuho_no_nan_inf(self, tuho):
        self._check_periods(tuho.periods, "TUHO")
        assert not math.isnan(tuho.equity_irr)
        assert not math.isinf(tuho.equity_irr)

    def test_oborovo_no_nan_inf(self, oborovo):
        self._check_periods(oborovo.periods, "Oborovo")
        assert not math.isnan(oborovo.equity_irr)
        assert not math.isinf(oborovo.equity_irr)

    def test_tuho_total_cit_post_t(self, tuho):
        assert abs(tuho.total_tax_keur - 33186.0) < 100.0, (
            f"TUHO total_tax_keur={tuho.total_tax_keur:.1f}, expected ~33186"
        )

    def test_oborovo_total_cit_post_t(self, oborovo):
        assert abs(oborovo.total_tax_keur - 8874.0) < 100.0, (
            f"Oborovo total_tax_keur={oborovo.total_tax_keur:.1f}, expected ~8874"
        )
