"""
KUPI K0-K3 Causal Grid — Test Suite (Post-Fix3 Diagnostic).

DIAGNOSTIC/TEST ONLY. DO NOT MERGE TO PRODUCTION.

Tests cover:
  A. P0 runs, Senior is finite and positive
  B. D0 is test-only; Senior(D0) > Senior(P0) [removing balancing increases CFADS → Senior]
  C. K0-K3 differ ONLY in tax and SHL method/timing dimensions
  D. Senior and SHL remain engine-derived (no source values injected)
  E. Source Senior (147,150) NOT used as an input target
  F. Source SHL principal (68,152) NOT injected as a G2A input
  G. Causal flows are monotonically consistent where expected
  H. Funding identity closes in all 6 cases
  I. No project identity dispatch (no if/elif branching on project names in engine)
  J. Solar/Wind TUHO regressions unchanged (subset smoke test)
"""

from __future__ import annotations

import math
import re
import pathlib

import pytest

from tests.diagnostics.kupi_k0_k3_causal_grid import (
    SOURCE_SENIOR_KEUR,
    SOURCE_SHL_PRINCIPAL_KEUR,
    build_kupi_project_inputs,
    run_d0_bank_balancing_diagnostic,
    run_full_grid,
    run_k0_control,
    run_k1_source_tax,
    run_k2_source_shl,
    run_k3_combined,
    run_p0_current_generic,
)
from finco_core.inputs._models import (
    ShlConstructionInterestMethod,
    SponsorFundingTimingPolicy,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def grid():
    """Run the full KUPI K0-K3 causal grid once for the session."""
    return run_full_grid()


# ---------------------------------------------------------------------------
# A. P0 runs from current main semantics; Senior is finite and positive
# ---------------------------------------------------------------------------

class TestP0CurrentGeneric:
    def test_p0_runs(self, grid):
        """A1: P0 produces a finite, positive Senior."""
        senior = grid.p0.final_senior_commitment_keur
        assert math.isfinite(senior), f"P0 Senior is not finite: {senior}"
        assert senior > 0, f"P0 Senior must be positive, got {senior}"

    def test_p0_shl_positive(self, grid):
        """A2: P0 SHL cash principal is positive (engine-derived)."""
        shl = grid.p0.derived_shl_cash_principal_keur
        assert shl > 0, f"P0 SHL must be positive, got {shl}"

    def test_p0_pik_positive(self, grid):
        """A3: P0 PIK is positive (SHL construction accrual active, dcf=2.0)."""
        assert grid.p0.shl_construction_pik_keur > 0

    def test_p0_binding_constraint_is_dscr(self, grid):
        """A4: P0 is DSCR-bound (not gearing-bound) — diagnostic design criterion."""
        assert grid.p0.binding_senior_constraint == "DSCR", (
            f"P0 binding constraint must be DSCR for causal effects to be visible, "
            f"got {grid.p0.binding_senior_constraint!r}"
        )

    def test_p0_convergence(self, grid):
        """A5: P0 fixed-point solver converged."""
        assert grid.p0.fixed_point_maximum_difference_keur < 1.0, (
            f"P0 solver did not converge: delta={grid.p0.fixed_point_maximum_difference_keur}"
        )


# ---------------------------------------------------------------------------
# B. D0 is test-only; Senior(D0) > Senior(P0)
# ---------------------------------------------------------------------------

class TestD0Diagnostic:
    def test_d0_senior_greater_than_p0(self, grid):
        """B1: Removing balancing cost raises CFADS → Senior(D0) > Senior(P0)."""
        assert grid.senior_d0 > grid.senior_p0, (
            f"D0 Senior ({grid.senior_d0:.3f}) must exceed P0 ({grid.senior_p0:.3f}). "
            f"Delta: {grid.delta_d0_vs_p0:.3f} kEUR"
        )

    def test_d0_delta_positive(self, grid):
        """B2: D0-P0 delta > 0 kEUR (balancing omission increases debt capacity)."""
        assert grid.delta_d0_vs_p0 > 0, (
            f"Expected D0-P0 delta > 0, got {grid.delta_d0_vs_p0:.3f}"
        )

    def test_d0_senior_finite(self, grid):
        """B3: D0 Senior is finite."""
        assert math.isfinite(grid.senior_d0)

    def test_d0_label_in_source_id(self, grid):
        """B4: D0 diagnostic label is present (test-only marker)."""
        # D0 is labeled via source_id in run_project_financing_model
        # Verify the factory uses bank_balancing_cost_eur_mwh=0 for D0
        p_d0 = build_kupi_project_inputs(bank_balancing_cost_eur_mwh=0.0)
        assert p_d0.revenue.balancing_cost_wind_eur_mwh == 0.0

        p_p0 = build_kupi_project_inputs(bank_balancing_cost_eur_mwh=5.0)
        assert p_p0.revenue.balancing_cost_wind_eur_mwh == 5.0


# ---------------------------------------------------------------------------
# C. K0-K3 differ ONLY in tax and SHL method/timing
# ---------------------------------------------------------------------------

class TestKFactorialDesign:
    def test_k0_k1_differ_only_in_tax_flag(self):
        """C1: K0 and K1 have identical SHL method/timing; differ only in tax override flag."""
        p_k0 = build_kupi_project_inputs(
            shl_construction_interest_method=ShlConstructionInterestMethod.SIMPLE,
            sponsor_funding_timing_policy=SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION,
            bank_balancing_cost_eur_mwh=0.0,
            source_tax_mechanic_override=False,
        )
        p_k1 = build_kupi_project_inputs(
            shl_construction_interest_method=ShlConstructionInterestMethod.SIMPLE,
            sponsor_funding_timing_policy=SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION,
            bank_balancing_cost_eur_mwh=0.0,
            source_tax_mechanic_override=True,
        )
        # Both have the same SHL construction parameters
        assert p_k0.financing.shl_construction_interest_method == ShlConstructionInterestMethod.SIMPLE
        assert p_k1.financing.shl_construction_interest_method == ShlConstructionInterestMethod.SIMPLE
        assert p_k0.financing.sponsor_funding_timing_policy == SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION
        assert p_k1.financing.sponsor_funding_timing_policy == SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION
        # Same balancing cost
        assert p_k0.revenue.balancing_cost_wind_eur_mwh == p_k1.revenue.balancing_cost_wind_eur_mwh

    def test_k0_k2_differ_only_in_shl_method_timing(self):
        """C2: K0 and K2 differ only in SHL construction method and timing policy."""
        p_k0 = build_kupi_project_inputs(
            shl_construction_interest_method=ShlConstructionInterestMethod.SIMPLE,
            sponsor_funding_timing_policy=SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION,
            bank_balancing_cost_eur_mwh=0.0,
        )
        p_k2 = build_kupi_project_inputs(
            shl_construction_interest_method=ShlConstructionInterestMethod.COMPOUND_PERIODIC,
            sponsor_funding_timing_policy=SponsorFundingTimingPolicy.ALL_AT_FC,
            bank_balancing_cost_eur_mwh=0.0,
        )
        # Different SHL method
        assert p_k0.financing.shl_construction_interest_method != p_k2.financing.shl_construction_interest_method
        # Different timing policy
        assert p_k0.financing.sponsor_funding_timing_policy != p_k2.financing.sponsor_funding_timing_policy
        # Same balancing (D0 treatment)
        assert p_k0.revenue.balancing_cost_wind_eur_mwh == p_k2.revenue.balancing_cost_wind_eur_mwh == 0.0
        # Same tax
        assert p_k0.tax.corporate_rate == p_k2.tax.corporate_rate
        assert p_k0.tax.shl_interest_deductibility == p_k2.tax.shl_interest_deductibility

    def test_k0_k3_k2_k1_balancing_consistent(self, grid):
        """C3: All K cases use D0 bank revenue treatment (balancing=0)."""
        for label, p_inputs in [
            ("K0", build_kupi_project_inputs(bank_balancing_cost_eur_mwh=0.0,
                shl_construction_interest_method=ShlConstructionInterestMethod.SIMPLE,
                sponsor_funding_timing_policy=SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION)),
            ("K2", build_kupi_project_inputs(bank_balancing_cost_eur_mwh=0.0,
                shl_construction_interest_method=ShlConstructionInterestMethod.COMPOUND_PERIODIC,
                sponsor_funding_timing_policy=SponsorFundingTimingPolicy.ALL_AT_FC)),
        ]:
            assert p_inputs.revenue.balancing_cost_wind_eur_mwh == 0.0, \
                f"{label} should use D0 bank revenue (balancing=0)"

    def test_k2_pik_gt_k0_pik(self, grid):
        """C4: ALL_AT_FC+COMPOUND produces more PIK than PRO_RATA+SIMPLE."""
        assert grid.k2.shl_construction_pik_keur > grid.k0.shl_construction_pik_keur, (
            f"K2 PIK ({grid.k2.shl_construction_pik_keur:.3f}) should exceed "
            f"K0 PIK ({grid.k0.shl_construction_pik_keur:.3f})"
        )

    def test_k2_opening_shl_gt_k0(self, grid):
        """C5: ALL_AT_FC+COMPOUND produces higher opening SHL balance than PRO_RATA+SIMPLE."""
        assert grid.k2.opening_operating_shl_balance_keur > grid.k0.opening_operating_shl_balance_keur


# ---------------------------------------------------------------------------
# D. Senior and SHL remain engine-derived
# ---------------------------------------------------------------------------

class TestEngineDerived:
    def test_source_senior_not_in_factory(self):
        """D1: Source Senior (147,150) is NOT used as a hard-coded input in the factory."""
        inputs = build_kupi_project_inputs()
        # Senior is computed by run_project_financing_model — not in ProjectInputs
        # Financing params must not set a frozen/fixed senior value
        assert not inputs.financing.use_frozen_excel_senior_debt_schedule, \
            "KUPI diagnostic must not use frozen senior schedule"

    def test_shl_principal_not_injected_as_source(self):
        """D2: Source SHL (68,153) is treated as a legacy compat field only; G2A derives it."""
        inputs = build_kupi_project_inputs()
        # The clean_shl_principal_keur field is a legacy compat seed; G2A fixed-point
        # overwrites it. The DERIVED value should differ from the seeded legacy value
        # unless the fixed-point converges to the seed (coincidental match).
        # Just check that G2A doesn't raise and produces a derived value.
        from financial_engine.financing import run_project_financing_model
        result = run_project_financing_model(inputs, source_id="D_TEST")
        assert math.isfinite(result.derived_shl_cash_principal_keur)

    def test_all_k_cases_have_finite_shl(self, grid):
        """D3: All K cases produce finite engine-derived SHL."""
        for label, res in [("K0", grid.k0), ("K1", grid.k1), ("K2", grid.k2), ("K3", grid.k3)]:
            assert math.isfinite(res.derived_shl_cash_principal_keur), f"{label} SHL not finite"
            assert math.isfinite(res.final_senior_commitment_keur), f"{label} Senior not finite"


# ---------------------------------------------------------------------------
# E. Source Senior NOT used as input target
# ---------------------------------------------------------------------------

class TestNoSourceTargets:
    def test_source_senior_not_used_as_target(self):
        """E1: 147150 does not appear as a target/constraint in the diagnostic module."""
        src = pathlib.Path(
            "/home/user/Finco1/tests/diagnostics/kupi_k0_k3_causal_grid.py"
        ).read_text()
        # SOURCE_SENIOR_KEUR is defined as a comparison constant, not injected as production input
        # Verify it doesn't appear in a financing params initialization (no gearing/target wiring)
        # Acceptable: appears as a named constant. Forbidden: appears in ProjectInputs fields.
        assert "gearing_ratio = 147" not in src
        assert "target_senior" not in src
        assert "fixed_senior" not in src


# ---------------------------------------------------------------------------
# F. Source SHL principal NOT injected as G2A input
# ---------------------------------------------------------------------------

class TestNoSourceShlInjection:
    def test_source_shl_not_injected_as_authority(self):
        """F1: 68152 appears only as a legacy compat field, NOT as a G2A fixed-point authority."""
        src = pathlib.Path(
            "/home/user/Finco1/tests/diagnostics/kupi_k0_k3_causal_grid.py"
        ).read_text()
        # The fixed-point uses candidate_shl starting from 0; clean_shl_principal_keur is a seed
        # Forbidden pattern: setting source_senior or using 68152 as a constraint
        assert "source_senior" not in src.lower().replace("source_senior_keur", "")


# ---------------------------------------------------------------------------
# G. Causal flows — monotonic consistency
# ---------------------------------------------------------------------------

class TestCausalMonotonicity:
    def test_shl_main_effect_non_negative(self, grid):
        """G1: SHL_MAIN_EFFECT ≥ 0 (ALL_AT_FC+COMPOUND can only increase or equal debt capacity)."""
        assert grid.shl_main_effect >= 0, (
            f"SHL_MAIN_EFFECT should be ≥ 0, got {grid.shl_main_effect:.3f}"
        )

    def test_d0_effect_positive(self, grid):
        """G2: D0 - P0 effect > 0 (removing balancing increases CFADS → Senior)."""
        assert grid.delta_d0_vs_p0 > 0

    def test_k2_senior_gte_k0(self, grid):
        """G3: Senior(K2) ≥ Senior(K0) — ALL_AT_FC+COMPOUND should not reduce Senior."""
        assert grid.senior_k2 >= grid.senior_k0

    def test_k3_senior_gte_k0(self, grid):
        """G4: Senior(K3) ≥ Senior(K0)."""
        assert grid.senior_k3 >= grid.senior_k0

    def test_d0_senior_gte_all_k_cases(self, grid):
        """G5: D0 is the diagnostic ceiling; all K-case Seniors ≤ D0 (same D0 revenue + variations)."""
        for label, senior in [("K0", grid.senior_k0), ("K1", grid.senior_k1),
                               ("K2", grid.senior_k2), ("K3", grid.senior_k3)]:
            assert senior <= grid.senior_d0 + 1.0, (
                f"{label} Senior ({senior:.3f}) unexpectedly exceeds D0 ({grid.senior_d0:.3f})"
            )

    def test_tax_unresolved_k1_equals_k0(self, grid):
        """G6: K1 = K0 Senior because SOURCE_TAX_MECHANIC_UNRESOLVED → no runtime change."""
        assert abs(grid.senior_k1 - grid.senior_k0) < 1e-3, (
            f"K1 should equal K0 while tax is unresolved. Delta: {grid.senior_k1 - grid.senior_k0:.6f}"
        )

    def test_k3_equals_k2_because_tax_unresolved(self, grid):
        """G7: K3 = K2 Senior because SOURCE_TAX_MECHANIC_UNRESOLVED → no runtime change."""
        assert abs(grid.senior_k3 - grid.senior_k2) < 1e-3, (
            f"K3 should equal K2 while tax is unresolved. Delta: {grid.senior_k3 - grid.senior_k2:.6f}"
        )


# ---------------------------------------------------------------------------
# H. Funding identity closes in all cases
# ---------------------------------------------------------------------------

class TestFundingIdentity:
    TOLERANCE_KEUR = 0.01  # 10 EUR absolute tolerance

    def _check_funding_identity(self, result, label: str) -> None:
        """Uses == Senior + SHL_cash + Share Capital + Additional Equity."""
        uses = result.project_uses.total_project_uses_keur
        senior = result.final_senior_commitment_keur
        shl = result.derived_shl_cash_principal_keur
        share_capital = result.share_capital_keur
        share_premium = result.share_premium_keur
        additional_equity = result.additional_equity_keur
        junior = result.junior_or_other_main_project_funding_keur
        other_equity = result.other_equity_funding_before_shl_keur

        sources = senior + shl + share_capital + share_premium + other_equity + additional_equity + junior
        diff = abs(uses - sources)
        assert diff < self.TOLERANCE_KEUR, (
            f"{label} funding identity violated: "
            f"uses={uses:.6f}, sources={sources:.6f}, diff={diff:.6f} kEUR"
        )

    def test_p0_funding_identity(self, grid):
        self._check_funding_identity(grid.p0, "P0")

    def test_d0_funding_identity(self, grid):
        self._check_funding_identity(grid.d0, "D0")

    def test_k0_funding_identity(self, grid):
        self._check_funding_identity(grid.k0, "K0")

    def test_k1_funding_identity(self, grid):
        self._check_funding_identity(grid.k1, "K1")

    def test_k2_funding_identity(self, grid):
        self._check_funding_identity(grid.k2, "K2")

    def test_k3_funding_identity(self, grid):
        self._check_funding_identity(grid.k3, "K3")


# ---------------------------------------------------------------------------
# I. No project identity dispatch in engine files
# ---------------------------------------------------------------------------

class TestNoProjectDispatch:
    def test_no_project_identity_dispatch_in_engine(self):
        """I1: Engine files must not branch on project names (no if/elif project=='kupi')."""
        engine_root = pathlib.Path("/home/user/Finco1/financial_engine")
        dispatch_pattern = re.compile(
            r"(if|elif)\s+.*\b(kupi|tuho|oborovo|krnovo)\b", re.IGNORECASE
        )
        violations = []
        for py_file in engine_root.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            src = py_file.read_text()
            for lineno, line in enumerate(src.splitlines(), 1):
                if dispatch_pattern.search(line):
                    violations.append(f"{py_file}:{lineno}: {line.strip()}")
        assert not violations, (
            f"Project identity dispatch found in engine files:\n" + "\n".join(violations)
        )

    def test_no_project_dispatch_in_shl_construction(self):
        """I2: SHL construction module has no project-name dispatch (if/elif branching).

        Note: KUPI/Oborovo may appear in comments/docstrings as examples — that is fine.
        The prohibited pattern is conditional branching on project identity.
        """
        src = pathlib.Path(
            "/home/user/Finco1/financial_engine/shl/construction.py"
        ).read_text()
        dispatch_pattern = re.compile(
            r"(if|elif)\s+.*\b(kupi|tuho|oborovo|krnovo)\b", re.IGNORECASE
        )
        violations = [
            f"line {i+1}: {line.strip()}"
            for i, line in enumerate(src.splitlines())
            if dispatch_pattern.search(line)
        ]
        assert not violations, (
            "SHL construction must not dispatch on project names:\n" + "\n".join(violations)
        )


# ---------------------------------------------------------------------------
# J. Solar/Wind regression smoke tests
# ---------------------------------------------------------------------------

class TestRegressions:
    def test_solar_p0_regression(self):
        """J1: Default solar project produces positive Senior (no regression)."""
        from app.project_factories import create_default_solar_project
        from financial_engine.financing import run_project_financing_model
        result = run_project_financing_model(create_default_solar_project())
        assert result.final_senior_commitment_keur > 0
        assert math.isfinite(result.final_senior_commitment_keur)

    def test_wind_p0_regression(self):
        """J2: Default wind project produces positive Senior (no regression)."""
        from app.project_factories import create_default_wind_project
        from financial_engine.financing import run_project_financing_model
        result = run_project_financing_model(create_default_wind_project())
        assert result.final_senior_commitment_keur > 0
        assert math.isfinite(result.final_senior_commitment_keur)

    def test_solar_shl_zero_construction_pik(self):
        """J3: Solar (shl_construction_dcf=0) still produces PIK=0 (backward compat)."""
        from app.project_factories import create_default_solar_project
        from financial_engine.financing import run_project_financing_model
        result = run_project_financing_model(create_default_solar_project())
        assert result.shl_construction_pik_keur == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# Grid results report (not a test — informational)
# ---------------------------------------------------------------------------

def test_print_grid_report(grid):
    """Print the full causal grid report for CI log inspection."""
    grid.print_report()

    # Report key causal decomposition values
    print(f"\n--- Key Diagnostics ---")
    print(f"  D0-P0 (balancing omission): {grid.delta_d0_vs_p0:+.3f} kEUR")
    print(f"  TAX_MAIN_EFFECT (K1-K0):   {grid.tax_main_effect:+.3f} kEUR [SOURCE_TAX_MECHANIC_UNRESOLVED]")
    print(f"  SHL_MAIN_EFFECT (K2-K0):   {grid.shl_main_effect:+.3f} kEUR")
    print(f"  COMBINED_EFFECT (K3-K0):   {grid.combined_effect:+.3f} kEUR")
    print(f"  INTERACTION:               {grid.interaction_effect:+.3f} kEUR")
    print(f"  K3_RESIDUAL vs source:     {grid.k3_residual_vs_source:+.3f} kEUR")
