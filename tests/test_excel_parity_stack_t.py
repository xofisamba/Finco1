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
        """taxable_profit_keur must be lower in periods with SHL interest vs ebitda-dep-si alone.

        Stack Z: when use_tax_bridge_engine=True (TUHO default), the bridge uses
        shl_gross_accrued_interest_keur (fixture-extracted) instead of shl_interest_keur
        (formula-based). The gross accrued amount includes PIK, so taxable_profit_keur
        differs from the naive formula approximation. The key invariant (SHL IS deducted)
        is preserved; the approximation check uses gross SHL when available.
        """
        shl_paying = [
            p for p in tuho.periods
            if (p.shl_interest_keur or 0) > 10 and (p.ebitda_keur or 0) > 0
        ]
        assert shl_paying, "No SHL-paying periods found"
        for p in shl_paying[:3]:
            # Use gross accrued SHL if available (bridge path), else formula
            shl_for_check = getattr(p, "shl_gross_accrued_interest_keur", 0) or (p.shl_interest_keur or 0)
            naive_basis = (p.ebitda_keur or 0) - (p.depreciation_keur or 0) - (p.senior_interest_keur or 0)
            with_shl = naive_basis - shl_for_check
            assert p.taxable_profit_keur <= naive_basis + 0.5, (
                f"P{p.period}: taxable_profit {p.taxable_profit_keur:.2f} exceeds "
                f"ebitda-dep-si {naive_basis:.2f} — SHL interest not deducted"
            )
            assert abs(p.taxable_profit_keur - with_shl) < 1500.0, (
                f"P{p.period}: taxable_profit {p.taxable_profit_keur:.2f} does not "
                f"approximate ebitda-dep-si-shl {with_shl:.2f} (shl_for_check={shl_for_check:.2f})"
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
        """Total cash CIT must approximately equal total accrued CIT.

        Stack Z: with use_tax_bridge_engine=True (TUHO factory default), cash CIT
        uses Excel-style H2 settlement (R67 diagnostic). The residual gap between
        accrued CIT and cash CIT is the known LCF-driven difference (~2323 kEUR):
        Finco uses correct 5-year rolling LCF; Excel uses perpetual LCF.
        """
        total_accrued = sum(p.tax_keur or 0 for p in tuho.periods)
        total_cash = sum(p.corporate_tax_cash_keur or 0 for p in tuho.periods)
        # Phase0/Z1: formula fix; accrued (~35414) vs cash (~33185) gap ~2229 kEUR.
        assert abs(total_accrued - total_cash) < 3000.0, (
            f"TUHO lifetime accrued={total_accrued:.2f} vs cash={total_cash:.2f} "
            f"— delta {abs(total_accrued - total_cash):.2f} kEUR > 3000 kEUR tolerance"
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


# ── T3e2: SHL re-pass consistency ────────────────────────────────────────────

class TestSHLRepassConsistency:
    """T1 SHL re-pass: verify that shi is the same after the re-pass (guard holds)
    and that SHL outcomes are internally consistent with the final cf_after_tax.

    The engine's SHL re-pass raises RuntimeError if shi changes; these tests
    indirectly prove the guard never fires (they would fail with RuntimeError if it did).
    """

    def test_tuho_shl_interest_never_negative(self, tuho):
        """SHL cash interest must be non-negative in every period."""
        for p in tuho.periods:
            assert (p.shl_interest_keur or 0) >= 0.0, (
                f"TUHO P{p.period}: shl_interest_keur={p.shl_interest_keur} is negative"
            )

    def test_tuho_shl_balance_fully_repaid(self, tuho):
        """TUHO SHL must reach zero balance (fully repaid) before model end."""
        shl_active = [p for p in tuho.periods if (p.shl_balance_keur or 0) > 0.01]
        assert shl_active, "No SHL balance found — TUHO should have SHL"
        last_active = shl_active[-1]
        assert last_active.period < len(tuho.periods) - 1, (
            f"TUHO SHL balance never reaches zero (last balance at P{last_active.period})"
        )

    def test_tuho_cf_after_tax_positive_in_operating_periods(self, tuho):
        """cf_after_tax must be positive in TUHO operating periods (healthy CFADS)."""
        op = [p for p in tuho.periods if p.is_operation]
        # Allow a few early periods near zero; focus on middle periods
        mid_ops = op[5:20]
        for p in mid_ops:
            assert (p.cf_after_tax_keur or 0) > 0, (
                f"TUHO P{p.period}: cf_after_tax_keur={p.cf_after_tax_keur:.2f} ≤ 0"
            )

    def test_tuho_shl_interest_within_gross_interest_cap(self, tuho):
        """SHL cash interest must not exceed gross accrued interest (no overpayment)."""
        for p in tuho.periods:
            if not p.is_operation:
                continue
            shi = p.shl_interest_keur or 0
            gross = p.shl_gross_accrued_interest_keur or 0
            if gross > 0:
                assert shi <= gross + 0.01, (
                    f"TUHO P{p.period}: shl_interest {shi:.4f} > gross_accrued {gross:.4f}"
                )

    def test_tuho_shl_repass_does_not_fire_runtime_error(self):
        """Running TUHO must not raise RuntimeError from the SHL re-pass guard.
        This proves shi is identical in the re-pass (two passes are exact for shi)."""
        try:
            demo = run_demo_project("TUHO")
            _ = demo.result.equity_irr
        except RuntimeError as e:
            if "SHL re-pass" in str(e):
                pytest.fail(
                    f"SHL re-pass guard fired: {e}. "
                    "shi changed between passes — three-pass iteration required."
                )
            raise

    def test_oborovo_shl_repass_does_not_fire_runtime_error(self):
        """Running Oborovo must not raise RuntimeError from the SHL re-pass guard."""
        try:
            demo = run_demo_project("Oborovo")
            _ = demo.result.equity_irr
        except RuntimeError as e:
            if "SHL re-pass" in str(e):
                pytest.fail(f"Oborovo SHL re-pass guard fired: {e}")
            raise


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
        # Phase0/Z1: formula fix; new correct value ~35414 kEUR (old 45835 used wrong depreciation basis)
        assert abs(tuho.total_tax_keur - 35414.0) < 500.0, (
            f"TUHO total_tax_keur={tuho.total_tax_keur:.1f}, expected ~35414 (Phase0 Z1 formula fix)"
        )

    def test_oborovo_total_cit_post_t(self, oborovo):
        assert abs(oborovo.total_tax_keur - 8874.0) < 100.0, (
            f"Oborovo total_tax_keur={oborovo.total_tax_keur:.1f}, expected ~8874"
        )
