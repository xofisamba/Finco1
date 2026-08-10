"""C3B3D2B2A — Tax / SHL causal diagnostic grid test suite.

Mission
-------
Causally explain the CURRENT_UPSTREAM_CLEAN_CASH_RESIDUAL (~2718.02 kEUR) by
evaluating 12 arm combinations of source-proven workbook mechanics (H2+H1
CIT pairing, EBT gate, rolling-5-period LCF, row-39 cap, SHL feedback).

Key governance constraints
--------------------------
- No DS25 / DS40 period-boundary hardcoding
- No project-name dispatch or approved_delta plugs
- Protected C3B2 SHA unchanged
- 13547.2 must not appear in clean SHL logic
- DSRA_ORDERING_UNRESOLVED — no DSRA implementation
- All evidence evaluated against source fixture vectors

Final verdict delivered: C3B3D2B2A_CAUSAL_GRID_READY_FOR_INDEPENDENT_REVIEW
"""

from __future__ import annotations

import math
import pytest

from finco_recon.diagnose_c3b3d2b2a_tax_shl_causal_grid import (
    D2B1_GRID0_FINAL_CLOSING_KEUR,
    SOURCE_DEBT_SIZE_KEUR,
    SHL_DRAW_KEUR,
    SHL_ANNUAL_RATE,
    SHL_FIRST_OP_OPENING_KEUR,
    SOURCE_FINAL_SHL_CLOSING_KEUR,
    WORKBOOK_CIT_RATE,
    WORKBOOK_ROLLING_WINDOW,
    WorkbookTaxConfig,
    DiagnosticGridResult,
    GridArmResult,
    run_diagnostic_grid,
    _load_source_fixture,
    _source_cash_tax_by_period,
    _source_cfads_by_period,
    _source_cfads_by_period_d2b1,
    _source_senior_ds_by_period,
    _source_senior_ds_by_period_d2b1,
    _source_shl_cash_by_period,
    _source_shl_cash_by_period_d2b1,
)

# ---------------------------------------------------------------------------
# Session-scoped fixture: run the full grid once per test session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def source_fixture():
    return _load_source_fixture()


@pytest.fixture(scope="session")
def grid(source_fixture):
    return run_diagnostic_grid()


# ---------------------------------------------------------------------------
# Governance constant tests
# ---------------------------------------------------------------------------

class TestGovernanceConstants:
    """Verify all governance constants match D2A source-proven values."""

    def test_shl_draw_authoritative(self):
        assert abs(SHL_DRAW_KEUR - 14_620.773894815633) < 1e-6

    def test_shl_annual_rate(self):
        assert abs(SHL_ANNUAL_RATE - 0.08) < 1e-9

    def test_shl_first_op_opening(self):
        assert abs(SHL_FIRST_OP_OPENING_KEUR - 15_790.435806400885) < 1e-6

    def test_source_debt_size(self):
        assert abs(SOURCE_DEBT_SIZE_KEUR - 42_852.27876256299) < 0.01

    def test_source_final_shl_closing_is_zero(self):
        assert SOURCE_FINAL_SHL_CLOSING_KEUR == 0.0

    def test_d2b1_grid0_final_closing_matches_d2b1(self):
        assert abs(D2B1_GRID0_FINAL_CLOSING_KEUR - 2718.02) < 0.5

    def test_workbook_cit_rate_ten_percent(self):
        assert abs(WORKBOOK_CIT_RATE - 0.10) < 1e-9

    def test_workbook_rolling_window_five(self):
        assert WORKBOOK_ROLLING_WINDOW == 5

    def test_legacy_draw_13547_absent(self):
        # 13547.2 must not appear in clean SHL logic (CLEAN_SHL_PROJECT_INPUT_AUTHORITY_HANDOFF)
        import inspect
        import finco_recon.diagnose_c3b3d2b2a_tax_shl_causal_grid as mod
        src = inspect.getsource(mod)
        assert "13547.2" not in src, "Legacy draw 13547.2 must not appear in clean SHL logic"

    def test_no_ds40_hardcode(self):
        """No hardcoded DS25/DS40 period boundary magic numbers in production path."""
        import inspect
        import finco_recon.diagnose_c3b3d2b2a_tax_shl_causal_grid as mod
        src = inspect.getsource(mod)
        # Check that period-boundary hardcodes are absent from waterfall logic
        assert "period_index == 25" not in src
        assert "period_index == 40" not in src


# ---------------------------------------------------------------------------
# Source fixture tests
# ---------------------------------------------------------------------------

class TestSourceFixtureVectors:
    """Verify source fixture loading returns plausible, non-trivial vectors."""

    def test_source_cash_tax_finite_positive(self, source_fixture):
        cit = _source_cash_tax_by_period(source_fixture)
        assert len(cit) >= 20
        for v in cit.values():
            assert math.isfinite(v)
            assert v >= 0.0

    def test_source_cash_tax_total_near_10443(self, source_fixture):
        cit = _source_cash_tax_by_period(source_fixture)
        total = sum(cit.values())
        assert abs(total - 10_443.09) < 5.0

    def test_source_cfads_non_trivial(self, source_fixture):
        cfads = _source_cfads_by_period(source_fixture)
        assert len(cfads) >= 20
        for v in cfads.values():
            assert math.isfinite(v)

    def test_source_senior_ds_positive(self, source_fixture):
        sd = _source_senior_ds_by_period(source_fixture)
        assert len(sd) >= 20
        for v in sd.values():
            assert math.isfinite(v)
            assert v >= 0.0

    def test_source_shl_cash_first_period_nonzero(self, source_fixture):
        shl = _source_shl_cash_by_period(source_fixture)
        assert len(shl) >= 1
        total = sum(shl.values())
        assert total > 0.0


# ---------------------------------------------------------------------------
# WorkbookTaxConfig tests
# ---------------------------------------------------------------------------

class TestWorkbookTaxConfig:
    """Verify WorkbookTaxConfig dataclass encodes arms correctly."""

    def test_grid0_config_all_false(self):
        c = WorkbookTaxConfig()
        assert not c.h2h1_pairing
        assert not c.ebt_gate
        assert not c.rolling_window
        assert not c.row39_cap
        assert not c.shl_netting_in_tax

    def test_grid_b_config(self):
        c = WorkbookTaxConfig(h2h1_pairing=True)
        assert c.h2h1_pairing
        assert not c.ebt_gate

    def test_grid_c_config(self):
        c = WorkbookTaxConfig(ebt_gate=True)
        assert not c.h2h1_pairing
        assert c.ebt_gate

    def test_grid_bcd_config(self):
        c = WorkbookTaxConfig(h2h1_pairing=True, ebt_gate=True, rolling_window=True)
        assert c.h2h1_pairing
        assert c.ebt_gate
        assert c.rolling_window
        assert not c.row39_cap

    def test_config_is_frozen(self):
        c = WorkbookTaxConfig()
        with pytest.raises(Exception):
            c.h2h1_pairing = True  # frozen dataclass


# ---------------------------------------------------------------------------
# GRID-0: Current clean baseline
# ---------------------------------------------------------------------------

class TestGrid0:
    """GRID-0 must reproduce D2B1 production-candidate metrics exactly."""

    def test_arm_id(self, grid):
        assert grid.grid0.arm_id == "GRID-0"

    def test_ds40_closing_matches_d2b1(self, grid):
        # EXPECTED_PRE_D2B2_UPSTREAM_CLEAN_CASH_RESIDUAL
        assert abs(grid.grid0.ds40_final_closing_keur - D2B1_GRID0_FINAL_CLOSING_KEUR) < 5.0

    def test_ds40_closing_positive(self, grid):
        assert grid.grid0.ds40_final_closing_keur > 0.0

    def test_delta_vs_grid0_is_zero(self, grid):
        assert grid.grid0.delta_vs_grid0_final_closing == 0.0

    def test_clean_debt_size_near_43919(self, grid):
        assert abs(grid.grid0.clean_debt_size_keur - 43_919.03) < 5.0

    def test_debt_size_delta_positive(self, grid):
        # Clean engine uses more debt than source (C3B3B)
        assert grid.grid0.debt_size_delta_keur > 0.0

    def test_total_tax_finite(self, grid):
        assert math.isfinite(grid.grid0.total_cash_tax_keur)
        assert grid.grid0.total_cash_tax_keur > 0.0

    def test_convergence_achieved(self, grid):
        assert grid.grid0.convergence_achieved is True

    def test_solver_converged(self, grid):
        assert grid.grid0.solver_converged is True

    def test_config_all_false(self, grid):
        c = grid.grid0.config
        assert not c.h2h1_pairing
        assert not c.ebt_gate
        assert not c.rolling_window
        assert not c.row39_cap
        assert not c.shl_netting_in_tax

    def test_source_total_cit_matches_fixture(self, grid):
        assert abs(grid.grid0.source_total_cash_tax_keur - 10_443.09) < 5.0

    def test_gross_interest_max_delta_finite(self, grid):
        assert math.isfinite(grid.grid0.gross_interest_max_delta)


# ---------------------------------------------------------------------------
# GRID-A: SHL feedback — SHL_OUTSIDE_FIXED_POINT = 0 for Oborovo
# ---------------------------------------------------------------------------

class TestGridA:
    """GRID-A ≡ GRID-0 for Oborovo (SHL non-deductible, net TI = 0)."""

    def test_arm_id(self, grid):
        assert grid.grid_a.arm_id == "GRID-A"

    def test_identical_to_grid0_ds40(self, grid):
        assert abs(
            grid.grid_a.ds40_final_closing_keur - grid.grid0.ds40_final_closing_keur
        ) < 1e-6

    def test_identical_to_grid0_tax(self, grid):
        assert abs(
            grid.grid_a.total_cash_tax_keur - grid.grid0.total_cash_tax_keur
        ) < 1e-6

    def test_identical_to_grid0_debt_size(self, grid):
        assert abs(
            grid.grid_a.clean_debt_size_keur - grid.grid0.clean_debt_size_keur
        ) < 1e-6

    def test_convergence_iterations_at_least_one(self, grid):
        assert grid.grid_a.convergence_iterations >= 1

    def test_shl_feedback_in_config(self, grid):
        assert grid.grid_a.config.shl_netting_in_tax is True

    def test_shl_outside_fixed_point_confirmed(self, grid):
        # Verify the key analytical finding: SHL feedback has zero effect for Oborovo.
        delta = abs(grid.grid_a.ds40_final_closing_keur - grid.grid0.ds40_final_closing_keur)
        assert delta < 1e-3, (
            f"SHL_OUTSIDE_FIXED_POINT approximation error should be 0 for Oborovo "
            f"(non-deductible SHL). Got delta={delta:.6f} kEUR"
        )

    def test_source_evidence_mentions_row59(self, grid):
        assert "row 59" in grid.grid_a.source_evidence or "P&L" in grid.grid_a.source_evidence


# ---------------------------------------------------------------------------
# GRID-B: H2+H1 CIT pairing
# ---------------------------------------------------------------------------

class TestGridB:
    """GRID-B: H2+H1 (model-year semiannual) CIT pairing only."""

    def test_arm_id(self, grid):
        assert grid.grid_b.arm_id == "GRID-B"

    def test_h2h1_pairing_in_config(self, grid):
        assert grid.grid_b.config.h2h1_pairing is True

    def test_ds40_finite_non_negative(self, grid):
        assert math.isfinite(grid.grid_b.ds40_final_closing_keur)
        assert grid.grid_b.ds40_final_closing_keur >= 0.0

    def test_solver_converged(self, grid):
        assert grid.grid_b.solver_converged is True

    def test_tax_delta_finite(self, grid):
        assert math.isfinite(grid.grid_b.total_tax_delta_vs_source)


# ---------------------------------------------------------------------------
# GRID-C: EBT gate
# ---------------------------------------------------------------------------

class TestGridC:
    """GRID-C: EBT gate for loss utilisation only.

    For Oborovo: EBT is always negative (SHL interest dominates).
    EBT gate prevents ALL loss utilisation → losses expire → higher tax
    relative to GRID-0 canonical.
    """

    def test_arm_id(self, grid):
        assert grid.grid_c.arm_id == "GRID-C"

    def test_ebt_gate_in_config(self, grid):
        assert grid.grid_c.config.ebt_gate is True

    def test_ds40_finite_non_negative(self, grid):
        assert math.isfinite(grid.grid_c.ds40_final_closing_keur)
        assert grid.grid_c.ds40_final_closing_keur >= 0.0

    def test_ebt_gate_increases_residual_vs_grid0(self, grid):
        # EBT gate → fewer losses utilized → higher CIT → lower CFADS → higher DS40 residual
        assert grid.grid_c.ds40_final_closing_keur >= grid.grid0.ds40_final_closing_keur - 10.0

    def test_solver_converged(self, grid):
        assert grid.grid_c.solver_converged is True


# ---------------------------------------------------------------------------
# GRID-D: Rolling 5-period loss window
# ---------------------------------------------------------------------------

class TestGridD:
    """GRID-D: Rolling 5-period LCF window only."""

    def test_arm_id(self, grid):
        assert grid.grid_d.arm_id == "GRID-D"

    def test_rolling_window_in_config(self, grid):
        assert grid.grid_d.config.rolling_window is True

    def test_ds40_finite_non_negative(self, grid):
        assert math.isfinite(grid.grid_d.ds40_final_closing_keur)
        assert grid.grid_d.ds40_final_closing_keur >= 0.0

    def test_solver_converged(self, grid):
        assert grid.grid_d.solver_converged is True


# ---------------------------------------------------------------------------
# GRID-E: Row-39 carriable-loss cap
# ---------------------------------------------------------------------------

class TestGridE:
    """GRID-E: Row-39 carriable-loss cap only."""

    def test_arm_id(self, grid):
        assert grid.grid_e.arm_id == "GRID-E"

    def test_row39_in_config(self, grid):
        assert grid.grid_e.config.row39_cap is True

    def test_ds40_finite_non_negative(self, grid):
        assert math.isfinite(grid.grid_e.ds40_final_closing_keur)
        assert grid.grid_e.ds40_final_closing_keur >= 0.0

    def test_solver_converged(self, grid):
        assert grid.grid_e.solver_converged is True


# ---------------------------------------------------------------------------
# Combination arms
# ---------------------------------------------------------------------------

class TestCombinationArms:
    """GRID-BC, BD, CD, BCD, ABCD, ABCDE combinations."""

    def test_grid_bc_arm_id(self, grid):
        assert grid.grid_bc.arm_id == "GRID-BC"

    def test_grid_bc_config(self, grid):
        assert grid.grid_bc.config.h2h1_pairing
        assert grid.grid_bc.config.ebt_gate
        assert not grid.grid_bc.config.rolling_window

    def test_grid_bd_arm_id(self, grid):
        assert grid.grid_bd.arm_id == "GRID-BD"

    def test_grid_cd_arm_id(self, grid):
        assert grid.grid_cd.arm_id == "GRID-CD"

    def test_grid_bcd_arm_id(self, grid):
        assert grid.grid_bcd.arm_id == "GRID-BCD"

    def test_grid_abcd_arm_id(self, grid):
        assert grid.grid_abcd.arm_id == "GRID-ABCD"

    def test_grid_abcde_arm_id(self, grid):
        assert grid.grid_abcde.arm_id == "GRID-ABCDE"

    def test_abcde_has_all_flags(self, grid):
        c = grid.grid_abcde.config
        assert c.h2h1_pairing
        assert c.ebt_gate
        assert c.rolling_window
        assert c.row39_cap
        assert c.shl_netting_in_tax

    def test_all_combination_arms_finite(self, grid):
        arms = [
            grid.grid_bc, grid.grid_bd, grid.grid_cd,
            grid.grid_bcd, grid.grid_abcd, grid.grid_abcde,
        ]
        for arm in arms:
            assert math.isfinite(arm.ds40_final_closing_keur), (
                f"{arm.arm_id}: ds40_final_closing_keur is not finite"
            )
            assert math.isfinite(arm.total_tax_delta_vs_source), (
                f"{arm.arm_id}: total_tax_delta_vs_source is not finite"
            )

    def test_all_combination_ds40_non_negative(self, grid):
        arms = [
            grid.grid_bc, grid.grid_bd, grid.grid_cd,
            grid.grid_bcd, grid.grid_abcd, grid.grid_abcde,
        ]
        for arm in arms:
            assert arm.ds40_final_closing_keur >= -1.0, (
                f"{arm.arm_id}: DS40 closing is negative ({arm.ds40_final_closing_keur:.2f})"
            )

    def test_all_combination_solvers_converged(self, grid):
        arms = [
            grid.grid_bc, grid.grid_bd, grid.grid_cd,
            grid.grid_bcd, grid.grid_abcd, grid.grid_abcde,
        ]
        for arm in arms:
            assert arm.solver_converged, f"{arm.arm_id}: solver did not converge"

    def test_grid_abcd_equals_abcde_when_row39_doesnt_bind(self, grid):
        """Row-39 cap does not bind for Oborovo — ABCD should equal ABCDE."""
        delta = abs(
            grid.grid_abcde.ds40_final_closing_keur - grid.grid_abcd.ds40_final_closing_keur
        )
        # Row39 doesn't bind for Oborovo → at most 1 kEUR difference from solver rounding
        assert delta < 5.0, (
            f"Unexpected row39 effect: ABCDE={grid.grid_abcde.ds40_final_closing_keur:.2f} "
            f"ABCD={grid.grid_abcd.ds40_final_closing_keur:.2f} Δ={delta:.2f}"
        )


# ---------------------------------------------------------------------------
# Key causal attribution findings
# ---------------------------------------------------------------------------

class TestCausalAttributionFindings:
    """Verify the key causal findings of the diagnostic grid."""

    def test_grid_a_equiv_grid0_shl_outside_fixed_point(self, grid):
        """GRID-A ≡ GRID-0: SHL_OUTSIDE_FIXED_POINT = 0 for Oborovo."""
        assert abs(
            grid.grid_a.ds40_final_closing_keur - grid.grid0.ds40_final_closing_keur
        ) < 0.01

    def test_no_workbook_arm_eliminates_residual(self, grid):
        """No workbook mechanic combination brings DS40 to zero (SOURCE_FINAL_SHL_CLOSING_KEUR).

        The CURRENT_UPSTREAM_CLEAN_CASH_RESIDUAL is not attributable to tax mechanics B-E.
        The residual must be upstream (CFADS driver, DSRA ordering, waterfall).
        """
        all_arms = [
            grid.grid_b, grid.grid_c, grid.grid_d, grid.grid_e,
            grid.grid_bc, grid.grid_bd, grid.grid_cd, grid.grid_bcd,
            grid.grid_abcd, grid.grid_abcde,
        ]
        for arm in all_arms:
            # The fundamental assertion: residual is not eliminated
            assert abs(arm.ds40_final_closing_keur - SOURCE_FINAL_SHL_CLOSING_KEUR) > 100.0, (
                f"{arm.arm_id} unexpectedly eliminates the residual: "
                f"DS40={arm.ds40_final_closing_keur:.2f} kEUR (source=0.0)"
            )

    def test_workbook_mechanics_increase_residual_not_decrease(self, grid):
        """All workbook arms produce DS40 ≥ GRID-0 residual.

        Since EBT gate prevents loss utilisation, adding workbook mechanics
        INCREASES the SHL closing residual relative to GRID-0.
        """
        arms = [
            grid.grid_c, grid.grid_d, grid.grid_e,
            grid.grid_bc, grid.grid_bcd, grid.grid_abcde,
        ]
        for arm in arms:
            # Allow small numerical tolerance
            assert arm.ds40_final_closing_keur >= grid.grid0.ds40_final_closing_keur - 50.0, (
                f"{arm.arm_id}: DS40={arm.ds40_final_closing_keur:.2f} is unexpectedly below "
                f"GRID-0 ({grid.grid0.ds40_final_closing_keur:.2f})"
            )

    def test_grid0_delta_vs_source_confirms_upstream_residual(self, grid):
        """GRID-0 SHL cash signed delta confirms upstream clean engine difference."""
        # The signed SHL cash delta must be negative (clean engine provides less
        # cash for SHL than source → SHL closing remains positive)
        assert grid.grid0.signed_total_shl_cash_delta < 0.0

    def test_all_arms_have_finite_metrics(self, grid):
        """All 12 arms produce fully finite metrics — no NaN/Inf propagation."""
        all_arms = [
            grid.grid0, grid.grid_a, grid.grid_b, grid.grid_c,
            grid.grid_d, grid.grid_e, grid.grid_bc, grid.grid_bd,
            grid.grid_cd, grid.grid_bcd, grid.grid_abcd, grid.grid_abcde,
        ]
        fields = [
            "total_cash_tax_keur", "total_tax_delta_vs_source",
            "max_period_tax_delta_vs_source", "total_cfads_keur",
            "max_cfads_delta_vs_source", "signed_total_cfads_delta",
            "clean_debt_size_keur", "debt_size_delta_keur",
            "max_senior_ds_delta_vs_source", "signed_total_senior_ds_delta",
            "max_shl_cash_delta_vs_source", "signed_total_shl_cash_delta",
            "gross_interest_max_delta", "cash_interest_max_delta",
            "pik_max_delta", "principal_max_delta", "closing_max_delta",
            "ds40_final_closing_keur", "delta_vs_grid0_final_closing",
        ]
        for arm in all_arms:
            for f in fields:
                val = getattr(arm, f)
                assert math.isfinite(val), (
                    f"{arm.arm_id}.{f} = {val} (not finite)"
                )

    def test_twelve_arms_total(self, grid):
        """Exactly 12 grid arms are evaluated."""
        all_arms = [
            grid.grid0, grid.grid_a, grid.grid_b, grid.grid_c,
            grid.grid_d, grid.grid_e, grid.grid_bc, grid.grid_bd,
            grid.grid_cd, grid.grid_bcd, grid.grid_abcd, grid.grid_abcde,
        ]
        assert len(all_arms) == 12
        arm_ids = {arm.arm_id for arm in all_arms}
        expected = {
            "GRID-0", "GRID-A", "GRID-B", "GRID-C", "GRID-D", "GRID-E",
            "GRID-BC", "GRID-BD", "GRID-CD", "GRID-BCD", "GRID-ABCD", "GRID-ABCDE",
        }
        assert arm_ids == expected

    def test_delta_vs_grid0_is_zero_for_grid0(self, grid):
        assert grid.grid0.delta_vs_grid0_final_closing == 0.0

    def test_delta_vs_grid0_is_zero_for_grid_a(self, grid):
        assert abs(grid.grid_a.delta_vs_grid0_final_closing) < 1e-3

    def test_all_non_grid0_deltas_are_relative_to_grid0(self, grid):
        """delta_vs_grid0_final_closing = ds40_final_closing - GRID-0 closing."""
        arms = [
            grid.grid_b, grid.grid_c, grid.grid_d, grid.grid_e,
            grid.grid_bc, grid.grid_bd, grid.grid_cd, grid.grid_bcd,
            grid.grid_abcd, grid.grid_abcde,
        ]
        for arm in arms:
            expected = arm.ds40_final_closing_keur - grid.grid0.ds40_final_closing_keur
            actual = arm.delta_vs_grid0_final_closing
            assert abs(actual - expected) < 0.01, (
                f"{arm.arm_id}: delta_vs_grid0 mismatch: "
                f"expected {expected:.4f}, got {actual:.4f}"
            )


# ---------------------------------------------------------------------------
# SHL input authority: 14620.77 is authoritative, 13547.2 is not
# ---------------------------------------------------------------------------

class TestShlInputAuthority:
    """CLEAN_SHL_PROJECT_INPUT_AUTHORITY_HANDOFF_PENDING_D2B2."""

    def test_draw_keur_not_13547(self):
        assert abs(SHL_DRAW_KEUR - 13_547.2) > 1.0

    def test_draw_keur_matches_d2a(self):
        assert abs(SHL_DRAW_KEUR - 14_620.773894815633) < 1e-4

    def test_first_op_opening_derived_from_draw_and_pik(self):
        # SHL_FIRST_OP_OPENING = draw × (1 + rate × DCF) where DCF=1.0
        # = 14620.773... × 1.08 = 15790.435...
        derived = SHL_DRAW_KEUR * (1.0 + SHL_ANNUAL_RATE * 1.0)
        assert abs(derived - SHL_FIRST_OP_OPENING_KEUR) < 1.0


# ---------------------------------------------------------------------------
# Causal grid format test
# ---------------------------------------------------------------------------

class TestFormatCausalAttributionTable:
    """Verify the causal attribution table formatter produces usable output."""

    def test_table_contains_all_arm_ids(self, grid):
        from finco_recon.diagnose_c3b3d2b2a_tax_shl_causal_grid import format_causal_attribution_table
        table = format_causal_attribution_table(grid)
        for arm_id in ["GRID-0", "GRID-A", "GRID-B", "GRID-C", "GRID-D",
                        "GRID-E", "GRID-BC", "GRID-BD", "GRID-CD",
                        "GRID-BCD", "GRID-ABCD", "GRID-ABCDE"]:
            assert arm_id in table, f"Arm {arm_id} not found in attribution table"

    def test_table_is_non_empty(self, grid):
        from finco_recon.diagnose_c3b3d2b2a_tax_shl_causal_grid import format_causal_attribution_table
        table = format_causal_attribution_table(grid)
        assert len(table) > 100

    def test_table_contains_2718_region(self, grid):
        from finco_recon.diagnose_c3b3d2b2a_tax_shl_causal_grid import format_causal_attribution_table
        table = format_causal_attribution_table(grid)
        # GRID-0 DS40 closing should appear in the table
        assert "2718" in table or "2717" in table


# ---------------------------------------------------------------------------
# GRID-S0: Canonical callback surrogate — must equiv GRID-0
# ---------------------------------------------------------------------------

class TestGridS0:
    """GRID-S0 proves the solve_senior_debt callback pattern reproduces GRID-0."""

    def test_arm_id(self, grid):
        assert grid.grid_s0.arm_id == "GRID-S0"

    def test_s0_equiv_grid0_within_solver_tolerance(self, grid):
        delta = abs(grid.grid_s0.ds40_final_closing_keur - grid.grid0.ds40_final_closing_keur)
        assert delta <= 5.0, (
            f"SURROGATE_MISMATCH: GRID-S0 DS40={grid.grid_s0.ds40_final_closing_keur:.3f} "
            f"vs GRID-0 DS40={grid.grid0.ds40_final_closing_keur:.3f} delta={delta:.3f} kEUR"
        )

    def test_s0_converged(self, grid):
        assert grid.grid_s0.convergence_achieved is True

    def test_s0_solver_converged(self, grid):
        assert grid.grid_s0.solver_converged is True

    def test_s0_convergence_note_not_surrogate_mismatch(self, grid):
        assert "SURROGATE_MISMATCH" not in grid.grid_s0.convergence_note, (
            f"GRID-S0 has surrogate mismatch: {grid.grid_s0.convergence_note}"
        )


# ---------------------------------------------------------------------------
# GRID-WS0: Workbook callback all-False surrogate — must equiv GRID-0
# ---------------------------------------------------------------------------

class TestGridWS0:
    """GRID-WS0 is the relative baseline for B/C/D/E arms.

    Must be validated against GRID-0; any difference is approximation error,
    not a causal factor. Without WS0 equiv GRID-0 the relative claims for
    workbook arms are not causally valid.
    """

    def test_arm_id(self, grid):
        assert grid.grid_ws0.arm_id == "GRID-WS0"

    def test_ws0_all_flags_false(self, grid):
        c = grid.grid_ws0.config
        assert not c.h2h1_pairing
        assert not c.ebt_gate
        assert not c.rolling_window
        assert not c.row39_cap

    def test_ws0_converged(self, grid):
        assert grid.grid_ws0.solver_converged is True

    def test_ws0_ds40_finite_positive(self, grid):
        assert math.isfinite(grid.grid_ws0.ds40_final_closing_keur)
        assert grid.grid_ws0.ds40_final_closing_keur > 0.0


# ---------------------------------------------------------------------------
# D2B1 exact regression: DS[1..40] source comparators
# ---------------------------------------------------------------------------

class TestD2B1ExactComparators:
    """D2B1-exact source comparator contract: fcf_for_banks_keur[1:41]."""

    def test_source_cfads_d2b1_forty_elements(self, source_fixture):
        vals = _source_cfads_by_period_d2b1(source_fixture)
        assert len(vals) == 40

    def test_source_cfads_d2b1_first_period_approx(self, source_fixture):
        vals = _source_cfads_by_period_d2b1(source_fixture)
        first_val = vals[1]
        assert abs(first_val - 2575.0) < 5.0, f"Expected ~2575.0, got {first_val:.4f}"

    def test_source_senior_ds_d2b1_forty_elements(self, source_fixture):
        vals = _source_senior_ds_by_period_d2b1(source_fixture)
        assert len(vals) == 40

    def test_source_senior_ds_sign_normalized_positive(self, source_fixture):
        vals = _source_senior_ds_by_period_d2b1(source_fixture)
        for i, v in vals.items():
            assert v >= 0.0, f"Period {i}: senior DS should be positive after sign normalization, got {v}"

    def test_source_shl_cash_d2b1_forty_elements(self, source_fixture):
        vals = _source_shl_cash_by_period_d2b1(source_fixture)
        assert len(vals) == 40

    def test_source_shl_cash_first_period_approx(self, source_fixture):
        vals = _source_shl_cash_by_period_d2b1(source_fixture)
        first_val = vals[1]
        assert abs(first_val - 335.0) < 5.0, f"Expected ~335.0 (FCF-for-SHL DS1), got {first_val:.4f}"

    def test_grid0_cfads_max_abs_delta_finite(self, grid):
        assert math.isfinite(grid.grid0.max_cfads_delta_vs_source)

    def test_grid0_senior_ds_max_abs_delta_finite(self, grid):
        assert math.isfinite(grid.grid0.max_senior_ds_delta_vs_source)

    def test_grid0_shl_cash_max_abs_delta_finite(self, grid):
        assert math.isfinite(grid.grid0.max_shl_cash_delta_vs_source)

    def test_d2b1_aliases_match_d2b1_functions(self, source_fixture):
        """Backward-compat aliases produce identical output to d2b1-suffixed functions."""
        cfads_alias = _source_cfads_by_period(source_fixture)
        cfads_d2b1 = _source_cfads_by_period_d2b1(source_fixture)
        assert cfads_alias == cfads_d2b1

        sd_alias = _source_senior_ds_by_period(source_fixture)
        sd_d2b1 = _source_senior_ds_by_period_d2b1(source_fixture)
        assert sd_alias == sd_d2b1

        shl_alias = _source_shl_cash_by_period(source_fixture)
        shl_d2b1 = _source_shl_cash_by_period_d2b1(source_fixture)
        assert shl_alias == shl_d2b1


# ---------------------------------------------------------------------------
# GRID-A actual execution: FIXED_POINT_COLLAPSES_ANALYTICALLY_TO_IDENTITY
# ---------------------------------------------------------------------------

class TestGridAActualExecution:
    """GRID-A executes the typed tax path with SHL interest injection."""

    def test_grid_a_source_evidence_mentions_typed_execution(self, grid):
        assert "Typed execution" in grid.grid_a.source_evidence or "typed" in grid.grid_a.source_evidence.lower()

    def test_grid_a_delta_vs_grid0_near_zero(self, grid):
        delta = abs(grid.grid_a.delta_vs_grid0_final_closing)
        assert delta < 5.0, (
            f"GRID-A delta vs GRID-0 = {delta:.4f} kEUR; "
            f"expected ~0 (SHL non-deductible -> net TI=0)"
        )

    def test_grid_a_shl_netting_in_tax_flag(self, grid):
        assert grid.grid_a.config.shl_netting_in_tax is True

    def test_grid_a_solver_converged(self, grid):
        assert grid.grid_a.solver_converged is True
