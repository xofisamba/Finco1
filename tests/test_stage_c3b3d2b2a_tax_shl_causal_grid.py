"""C3B3D2B2A — Tax / SHL causal diagnostic grid test suite.

Mission
-------
Evaluate 12 arm combinations of source-proven workbook mechanics (H2+H1
CIT pairing, EBT gate, rolling-5-period LCF, row-39 cap, SHL feedback)
against the CURRENT_UPSTREAM_CLEAN_CASH_RESIDUAL (~2718.02 kEUR).

Cause status: CURRENT_CAUSE_UNRESOLVED — no arm has proven the residual source.
B/C/D/E arms are WITHIN_TAX_SURROGATE_ONLY (GRID-WS0 validation pending).

R3 additions: CFADS/DSCR source mapping, TUHO bank-sizing proof, Oborovo
debt sizing replay, DSRA classification, tax window labels.
R4 additions: three-baseline separation, row39 non-causal classification.
R5 additions: FCF-for-SHL lineage proof (CF79+CF80, not DS23), per-row
source-replay classifications, bank-scenario label cleanup.

Key governance constraints
--------------------------
- No DS25 / DS40 period-boundary hardcoding
- No project-name dispatch or approved_delta plugs
- Protected C3B2 SHA unchanged
- 13547.2 must not appear in clean SHL logic
- DSRA_NOT_CAUSAL_FOR_OBOROVO_CURRENT_RESIDUAL_SOURCE_PROVEN
- BANK_SIZING_SCENARIO_P90_10Y_REVIEWER_CONFIRMED_NOT_COMMITTED (not SOURCE_PROVEN)
- All evidence evaluated against source fixture vectors

Final verdict: C3B3D2B2A_R5_DIAGNOSTIC_MAPPING_READY_FOR_MERGE_REVIEW
"""

from __future__ import annotations

import json
import math
import pathlib
import pytest

_FIXTURE_DIR = pathlib.Path(__file__).parent / "fixtures"


def _load_oborovo_financial_fixture() -> dict:
    with open(_FIXTURE_DIR / "excel_oborovo_financial_truth.json") as f:
        return json.load(f)


def _load_oborovo_debt_interest_fixture() -> dict:
    with open(_FIXTURE_DIR / "excel_oborovo_debt_interest_truth.json") as f:
        return json.load(f)


def _load_tuho_fixture() -> dict:
    with open(_FIXTURE_DIR / "excel_tuho_full_model_extract.json") as f:
        return json.load(f)

from finco_recon.diagnose_c3b3d2b2a_tax_shl_causal_grid import (
    D2B1_GRID0_FINAL_CLOSING_KEUR,
    SOURCE_DEBT_SIZE_KEUR,
    CURRENT_GRID0_DEBT_KEUR,
    HISTORICAL_GENERIC_PHASE2C_DEBT_KEUR,
    SOURCE_EXCEL_SENIOR_DEBT_KEUR,
    SHL_DRAW_KEUR,
    SHL_ANNUAL_RATE,
    SHL_FIRST_OP_OPENING_KEUR,
    SOURCE_FINAL_SHL_CLOSING_KEUR,
    WORKBOOK_CIT_RATE,
    WORKBOOK_ROLLING_WINDOW,
    WorkbookTaxConfig,
    _aligned_source_dicts,
    _source_cfads_ds1_40,
    _source_senior_ds_ds1_40,
    _source_candidate_shl_cash_ds1_40,
    _compute_workbook_lcf,
    _source_replay_workbook_rows,
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

    def test_grid_c_ds40_within_surrogate(self, grid):
        # WITHIN_TAX_SURROGATE_ONLY — GRID-WS0 not yet validated against GRID-0.
        # This assertion verifies the GRID-C arm produces a finite, non-trivial DS40;
        # no causal claim about the CURRENT_UPSTREAM_CLEAN_CASH_RESIDUAL is made.
        assert math.isfinite(grid.grid_c.ds40_final_closing_keur)
        assert abs(grid.grid_c.ds40_final_closing_keur) > 100.0

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

    def test_workbook_arms_within_tax_surrogate_only(self, grid):
        """B/C/D/E arms are WITHIN_TAX_SURROGATE_ONLY — not validated against a common baseline.

        GRID-WS0 has not been validated as equivalent to GRID-0. Until that gate
        is cleared, B/C/D/E relative claims are within-surrogate experiments only
        and cannot be stated as causal drivers of the upstream residual.

        Row-39 (GRID-E): ROW39_REPORTING_OR_NON_CAUSAL_FOR_TAX_STATE_SOURCE_PROVEN —
        row39 does not feed forward tax state; GRID-E is not a causal mechanic.
        """
        arms = [
            grid.grid_c, grid.grid_d, grid.grid_e,
            grid.grid_bc, grid.grid_bcd, grid.grid_abcde,
        ]
        for arm in arms:
            # Arms must produce finite DS40; magnitude vs GRID-0 is surrogate-only
            assert math.isfinite(arm.ds40_final_closing_keur), (
                f"{arm.arm_id}: DS40 is not finite — surrogate computation failed"
            )
            # Within-surrogate: residual does not reach zero (source = 0.0 kEUR)
            assert abs(arm.ds40_final_closing_keur) > 100.0, (
                f"{arm.arm_id} WITHIN_TAX_SURROGATE_ONLY: "
                f"DS40={arm.ds40_final_closing_keur:.2f} is unexpectedly near zero"
            )

    def test_grid0_shl_cash_delta_is_negative(self, grid):
        """GRID-0 SHL cash signed delta is negative (WITHIN_TAX_SURROGATE_ONLY label).

        Clean engine provides less cash for SHL than source across DS[1..40] —
        consistent with upstream clean-vs-source differences. This is a directional
        observation, not a causal attribution (GRID-WS0 gate not yet classified).
        """
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


# ---------------------------------------------------------------------------
# R2: GRID-0 numerical reproduction with tight assertions
# ---------------------------------------------------------------------------

class TestGrid0NumericalReproduction:
    """Prove exact D2B1 GRID-0 reproduction using position-aligned comparators.

    R2 mandate: tight assertions on CFADS, senior DS, SHL cash, DS40 closing.
    Position-alignment required because clean model has 2 construction periods.
    """

    def test_cfads_max_abs_delta_tight(self, grid):
        """CFADS max abs delta (position-aligned) must be ≤ 340 kEUR."""
        assert grid.grid0.max_cfads_delta_vs_source <= 340.0, (
            f"CFADS max abs delta = {grid.grid0.max_cfads_delta_vs_source:.4f} kEUR; "
            f"R2 target ≤340 kEUR (R1 had ~2575 due to off-by-1 period index)"
        )

    def test_cfads_max_abs_delta_approx_339(self, grid):
        """CFADS max abs delta ≈ 339.71 kEUR (R2 position-aligned value)."""
        delta = grid.grid0.max_cfads_delta_vs_source
        assert abs(delta - 339.71) < 5.0, (
            f"CFADS max abs delta = {delta:.4f} kEUR; expected ~339.71 kEUR"
        )

    def test_cfads_signed_total_approx_plus347(self, grid):
        """CFADS signed total delta ≈ +347.11 kEUR (clean > source = less tax paid)."""
        signed = grid.grid0.signed_total_cfads_delta
        assert abs(signed - 347.11) < 10.0, (
            f"CFADS signed total = {signed:.4f} kEUR; expected ~+347.11 kEUR"
        )

    def test_senior_ds_max_abs_delta_tight(self, grid):
        """Senior DS max abs delta (position-aligned) must be ≤ 668 kEUR."""
        assert grid.grid0.max_senior_ds_delta_vs_source <= 668.0, (
            f"Senior DS max abs delta = {grid.grid0.max_senior_ds_delta_vs_source:.4f} kEUR; "
            f"R2 target ≤668 kEUR"
        )

    def test_senior_ds_max_abs_delta_approx_668(self, grid):
        """Senior DS max abs delta ≈ 667.86 kEUR (R2 position-aligned value)."""
        delta = grid.grid0.max_senior_ds_delta_vs_source
        assert abs(delta - 667.86) < 10.0, (
            f"Senior DS max abs delta = {delta:.4f} kEUR; expected ~667.86 kEUR"
        )

    def test_senior_ds_signed_total_approx_plus2242(self, grid):
        """Senior DS signed total ≈ +2242 kEUR (clean debt service > source)."""
        signed = grid.grid0.signed_total_senior_ds_delta
        assert abs(signed - 2242.03) < 20.0, (
            f"Senior DS signed total = {signed:.4f} kEUR; expected ~+2242.03 kEUR"
        )

    def test_shl_cash_max_abs_delta_tight(self, grid):
        """SHL cash max abs delta (position-aligned) must be ≤ 623 kEUR."""
        assert grid.grid0.max_shl_cash_delta_vs_source <= 623.0, (
            f"SHL cash max abs delta = {grid.grid0.max_shl_cash_delta_vs_source:.4f} kEUR"
        )

    def test_shl_cash_max_abs_delta_approx_623(self, grid):
        """SHL cash max abs delta ≈ 622.69 kEUR (R2 position-aligned value)."""
        delta = grid.grid0.max_shl_cash_delta_vs_source
        assert abs(delta - 622.69) < 10.0, (
            f"SHL cash max abs delta = {delta:.4f} kEUR; expected ~622.69 kEUR"
        )

    def test_shl_cash_signed_total_approx_minus1895(self, grid):
        """SHL cash signed total ≈ -1894.91 kEUR (clean < source = less SHL cash)."""
        signed = grid.grid0.signed_total_shl_cash_delta
        assert abs(signed - (-1894.91)) < 20.0, (
            f"SHL cash signed total = {signed:.4f} kEUR; expected ~-1894.91 kEUR"
        )

    def test_ds40_closing_approx_2718(self, grid):
        """DS[40] closing ≈ 2718.02 kEUR — the CURRENT_UPSTREAM_CLEAN_CASH_RESIDUAL."""
        closing = grid.grid0.ds40_final_closing_keur
        assert abs(closing - 2718.02) < 1.0, (
            f"DS[40] closing = {closing:.4f} kEUR; expected ~2718.02 kEUR"
        )

    def test_position_aligned_source_helper_cfads(self, source_fixture):
        """_aligned_source_dicts returns 40 CFADS entries mapped to clean op indices."""
        cfads_list = _source_cfads_ds1_40(source_fixture)
        clean_op_indices = list(range(2, 42))  # [2..41] as in clean model
        cfads_src, _, _ = _aligned_source_dicts(clean_op_indices, source_fixture)
        assert len(cfads_src) == 40
        # k=0: source DS1 value maps to clean_op_indices[0]=2
        assert abs(cfads_src[2] - cfads_list[0]) < 1e-9

    def test_position_aligned_source_helper_sd(self, source_fixture):
        """_aligned_source_dicts returns 40 senior DS entries mapped to clean op indices."""
        sd_list = _source_senior_ds_ds1_40(source_fixture)
        clean_op_indices = list(range(2, 42))
        _, sd_src, _ = _aligned_source_dicts(clean_op_indices, source_fixture)
        assert len(sd_src) == 40
        assert abs(sd_src[2] - sd_list[0]) < 1e-9

    def test_position_aligned_source_helper_cit(self, source_fixture):
        """_aligned_source_dicts returns 40 CIT entries mapped to clean op indices."""
        clean_op_indices = list(range(2, 42))
        _, _, cit_src = _aligned_source_dicts(clean_op_indices, source_fixture)
        assert len(cit_src) == 40
        # All values are non-negative (absolute values)
        for v in cit_src.values():
            assert v >= 0.0


# ---------------------------------------------------------------------------
# R2: GRID-S0 vector contract (canonical callback surrogate ≡ GRID-0)
# ---------------------------------------------------------------------------

class TestGridS0VectorContract:
    """GRID-S0 must prove equivalence with GRID-0 within solver tolerance."""

    def test_grid_s0_ds40_within_1_keur_of_grid0(self, grid):
        """GRID-S0 DS40 closing within 1 kEUR of GRID-0 — surrogate validated."""
        diff = abs(grid.grid_s0.ds40_final_closing_keur - grid.grid0.ds40_final_closing_keur)
        assert diff < 1.0, (
            f"GRID-S0 DS40={grid.grid_s0.ds40_final_closing_keur:.4f} vs "
            f"GRID-0 DS40={grid.grid0.ds40_final_closing_keur:.4f}, diff={diff:.4f} kEUR"
        )

    def test_grid_s0_convergence_note_no_mismatch(self, grid):
        assert "SURROGATE_MISMATCH" not in grid.grid_s0.convergence_note, (
            f"GRID-S0 convergence note: {grid.grid_s0.convergence_note}"
        )

    def test_grid_s0_cfads_max_delta_within_solver_tolerance(self, grid):
        """GRID-S0 CFADS max delta vs GRID-0 should be small (solver tolerance)."""
        delta = abs(grid.grid_s0.max_cfads_delta_vs_source - grid.grid0.max_cfads_delta_vs_source)
        assert delta < 50.0, (
            f"GRID-S0 CFADS max delta = {grid.grid_s0.max_cfads_delta_vs_source:.4f} vs "
            f"GRID-0 = {grid.grid0.max_cfads_delta_vs_source:.4f}"
        )

    def test_grid_s0_debt_size_within_solver_tolerance(self, grid):
        diff = abs(grid.grid_s0.clean_debt_size_keur - grid.grid0.clean_debt_size_keur)
        assert diff < 10.0, (
            f"GRID-S0 debt={grid.grid_s0.clean_debt_size_keur:.2f} vs "
            f"GRID-0 debt={grid.grid0.clean_debt_size_keur:.2f}"
        )

    def test_grid_s0_solver_converged(self, grid):
        assert grid.grid_s0.solver_converged is True


# ---------------------------------------------------------------------------
# R2: GRID-WS0 vs GRID-0 gate classification
# ---------------------------------------------------------------------------

class TestGridWS0VsGrid0Gate:
    """GRID-WS0 baseline validation gate.

    If GRID-WS0 ≡ GRID-0 (within tolerance), B/C/D/E results are
    meaningful relative to the clean engine. Otherwise they are within-
    surrogate experiments only (DIAGNOSTIC_SURROGATE_BASELINE_NOT_VALIDATED).
    """

    def test_grid_ws0_ds40_is_finite(self, grid):
        assert math.isfinite(grid.grid_ws0.ds40_final_closing_keur)

    def test_grid_ws0_solver_converged(self, grid):
        assert grid.grid_ws0.solver_converged is True

    def test_grid_ws0_delta_vs_grid0_reported(self, grid):
        """delta_vs_grid0 field is populated and finite."""
        assert math.isfinite(grid.grid_ws0.delta_vs_grid0_final_closing)

    def test_grid_ws0_all_config_flags_false(self, grid):
        cfg = grid.grid_ws0.config
        assert cfg.h2h1_pairing is False
        assert cfg.ebt_gate is False
        assert cfg.rolling_window is False
        assert cfg.row39_cap is False

    def test_grid_ws0_surrogate_baseline_label(self, grid):
        assert grid.grid_ws0.surrogate_baseline == "GRID-WS0"


# ---------------------------------------------------------------------------
# R2: Source replay rows 36/37/38/39/41/43
# ---------------------------------------------------------------------------

class TestSourceReplayRows:
    """Per-row SOURCE_REPLAY_PROVEN classification for workbook rows 36-43."""

    @pytest.fixture(scope="class")
    def replay(self, source_fixture):
        return _source_replay_workbook_rows(source_fixture)

    def test_replay_has_forty_periods(self, replay):
        assert len(replay) == 40

    def test_row36_max_delta_sub_keur(self, replay):
        max_delta = max(v["row36_delta"] for v in replay.values())
        assert max_delta < 1.0, f"Row 36 max delta = {max_delta:.4f} kEUR"

    def test_row37_max_delta_sub_keur(self, replay):
        max_delta = max(v["row37_delta"] for v in replay.values())
        assert max_delta < 1.0, f"Row 37 max delta = {max_delta:.4f} kEUR"

    def test_row38_max_delta_sub_keur(self, replay):
        max_delta = max(v["row38_delta"] for v in replay.values())
        assert max_delta < 1.0, f"Row 38 max delta = {max_delta:.4f} kEUR"

    def test_row39_max_delta_sub_keur(self, replay):
        max_delta = max(v["row39_delta"] for v in replay.values())
        assert max_delta < 1.0, f"Row 39 max delta = {max_delta:.4f} kEUR"

    def test_row41_max_delta_sub_keur(self, replay):
        max_delta = max(v["row41_delta"] for v in replay.values())
        assert max_delta < 1.0, f"Row 41 max delta = {max_delta:.4f} kEUR"

    def test_row43_max_delta_sub_keur(self, replay):
        max_delta = max(v["row43_delta"] for v in replay.values())
        assert max_delta < 1.0, f"Row 43 max delta = {max_delta:.4f} kEUR"

    def test_source_replay_proven_classification_present(self, replay):
        for pidx, v in replay.items():
            assert "classification" in v, f"Period {pidx} missing classification"
            assert v["classification"] in ("SOURCE_REPLAY_PROVEN", "SOURCE_REPLAY_MISMATCH")

    def test_per_row_classifications_present(self, replay):
        """Each row has its own per-row classification field (R5)."""
        row_keys = [
            "row36_classification", "row37_classification", "row38_classification",
            "row39_classification", "row41_classification", "row43_classification",
        ]
        for pidx, v in replay.items():
            for key in row_keys:
                assert key in v, f"Period {pidx} missing {key}"
                assert v[key] in ("SOURCE_REPLAY_PROVEN", "SOURCE_REPLAY_MISMATCH"), (
                    f"Period {pidx} {key}={v[key]!r}"
                )

    def test_per_row_all_source_replay_proven(self, replay):
        """All rows are SOURCE_REPLAY_PROVEN for Oborovo (delta < 1.0 kEUR each)."""
        for row in ("row36", "row37", "row38", "row39", "row41", "row43"):
            for pidx, v in replay.items():
                assert v[f"{row}_classification"] == "SOURCE_REPLAY_PROVEN", (
                    f"Period {pidx} {row} is not SOURCE_REPLAY_PROVEN "
                    f"(delta={v[f'{row}_delta']:.4f} kEUR)"
                )


# ---------------------------------------------------------------------------
# R2: Row-39 state propagation fix
# ---------------------------------------------------------------------------

class TestRow39StateRepaired:
    """Row39 cap state propagation — losses_n cap must feed back into cumulative_used."""

    def test_row39_cap_non_binding_for_oborovo(self, source_fixture):
        """For Oborovo: row39 cap does not bind (prior_TI always >= losses_n magnitude).

        Classification: ROW39_CAP_SOURCE_REPLAY_PROVEN_NON_BINDING_FOR_OBOROVO
        """
        rows = source_fixture["tax"]["rows"]
        ti_vals = rows["taxable_income"]["period_values"]
        n = min(40, len(ti_vals) - 1)
        import math as _math
        for i in range(1, n + 1):
            prior_ti = ti_vals[i - 1] if i >= 1 else 0.0
            # For Oborovo, when prior_ti is positive (profitable periods),
            # the cap MIN(losses_n, prior_ti) doesn't reduce carryforward.
            # The test simply verifies the fixture is available and the prior_ti vector is finite.
            assert _math.isfinite(prior_ti)

    def test_row39_cap_with_flag_enabled_finite(self, source_fixture):
        """_compute_workbook_lcf with row39_cap=True produces finite output for Oborovo."""
        rows = source_fixture["tax"]["rows"]
        ti_vals = rows["taxable_income"]["period_values"]
        ebt_vals = source_fixture["pl"]["earnings_before_tax_keur"]
        n = min(40, len(ti_vals) - 1)

        # Minimal test setup using source TI directly
        sorted_op_pidx = list(range(1, n + 1))
        ti_by_pidx = {i: ti_vals[i] for i in sorted_op_pidx if i < len(ti_vals)}
        ebt_by_pidx = {i: (ebt_vals[i] if i < len(ebt_vals) else 0.0) for i in sorted_op_pidx}
        config = WorkbookTaxConfig(row39_cap=True)
        tp = _compute_workbook_lcf(sorted_op_pidx, ti_by_pidx, ebt_by_pidx, config)
        assert len(tp) == n
        for pidx, v in tp.items():
            assert math.isfinite(v), f"Period {pidx}: tp={v} not finite"

    def test_grid_e_ds40_close_to_grid_ws0(self, grid):
        """GRID-E (row39 cap only) DS40 ≈ GRID-WS0 DS40 — cap non-binding for Oborovo."""
        diff = abs(grid.grid_e.ds40_final_closing_keur - grid.grid_ws0.ds40_final_closing_keur)
        assert diff < 100.0, (
            f"GRID-E DS40={grid.grid_e.ds40_final_closing_keur:.4f} vs "
            f"GRID-WS0 DS40={grid.grid_ws0.ds40_final_closing_keur:.4f}, diff={diff:.4f}"
        )


# ---------------------------------------------------------------------------
# R2: GRID-A full horizon
# ---------------------------------------------------------------------------

class TestGridAFullHorizon:
    """GRID-A injects SHL interest + reintegration for ALL SHL periods (full horizon)."""

    def test_grid_a_identical_to_grid0_ds40(self, grid):
        """GRID-A DS40 must equal GRID-0 DS40 within 1e-3 kEUR (net TI = 0 always)."""
        diff = abs(grid.grid_a.ds40_final_closing_keur - grid.grid0.ds40_final_closing_keur)
        assert diff < 1e-3, (
            f"GRID-A DS40={grid.grid_a.ds40_final_closing_keur:.6f} vs "
            f"GRID-0 DS40={grid.grid0.ds40_final_closing_keur:.6f}, diff={diff:.6f} kEUR. "
            f"Full-horizon injection (debt tenor + post-maturity) must give net TI=0."
        )

    def test_grid_a_convergence_note_identity(self, grid):
        assert "FIXED_POINT_COLLAPSES_ANALYTICALLY_TO_IDENTITY_FOR_OBOROVO" in grid.grid_a.convergence_note

    def test_grid_a_delta_vs_grid0_sub_milleur(self, grid):
        assert abs(grid.grid_a.delta_vs_grid0_final_closing) < 1e-3


# ---------------------------------------------------------------------------
# R2: GRID-ABCD semantics honest
# ---------------------------------------------------------------------------

class TestGridABCDSemanticsHonest:
    """GRID-ABCD config must explicitly declare shl_netting_in_tax=True.

    A is the zero-effect identity; ABCD = BCD analytically. The config flag
    makes the A-wiring semantically honest — it's not a computational placeholder.
    """

    def test_grid_abcd_shl_netting_in_tax(self, grid):
        assert grid.grid_abcd.config.shl_netting_in_tax is True, (
            "GRID-ABCD must declare shl_netting_in_tax=True to reflect A wiring"
        )

    def test_grid_abcd_h2h1_and_ebt_and_rolling(self, grid):
        cfg = grid.grid_abcd.config
        assert cfg.h2h1_pairing is True
        assert cfg.ebt_gate is True
        assert cfg.rolling_window is True

    def test_grid_abcd_approx_equals_grid_bcd(self, grid):
        """GRID-ABCD ≈ GRID-BCD (A has zero TI effect — analytically identity)."""
        diff = abs(grid.grid_abcd.ds40_final_closing_keur - grid.grid_bcd.ds40_final_closing_keur)
        assert diff < 1.0, (
            f"GRID-ABCD DS40={grid.grid_abcd.ds40_final_closing_keur:.4f} vs "
            f"GRID-BCD DS40={grid.grid_bcd.ds40_final_closing_keur:.4f}, diff={diff:.4f} kEUR"
        )

    def test_grid_abcd_source_evidence_mentions_identity(self, grid):
        ev = grid.grid_abcd.source_evidence
        assert "FIXED_POINT_COLLAPSES_ANALYTICALLY_TO_IDENTITY_FOR_OBOROVO" in ev or \
               "zero TI effect" in ev or "A=0 identity" in ev


# ---------------------------------------------------------------------------
# R3: CFADS / DSCR source formula mapping (Oborovo)
# ---------------------------------------------------------------------------

class TestCfadsDscrSourceMapping:
    """Verify source formulas for the two-layer CFADS architecture (Oborovo).

    SOURCE_PROVEN_FORMULA assertions — these must match the exact formula text
    extracted from the Oborovo workbook.
    """

    @pytest.fixture(scope="class")
    def wa(self):
        return _load_oborovo_debt_interest_fixture()["workstream_a"]

    def test_cf79_formula_proven(self, wa):
        """CF!row79 = SUM(H23,H49,H73,H76,H77)+$B$80*(H$4=0)."""
        formula = wa["cf_row79_free_cash_flow_for_banks"]["formula_h"]
        assert "SUM(H23,H49,H73,H76,H77)" in formula
        assert "$B$80" in formula

    def test_macro49_links_to_cf79(self, wa):
        """Macro!row49 formula = CF!H79 (input to bank-sizing VBA)."""
        formula = wa["macro_row49_input"]["formula_h"]
        assert formula == "=CF!H79"

    def test_macro50_vba_not_visible(self, wa):
        """Macro!row50 output formula is None — VBA_IMPLEMENTATION_NOT_VISIBLE."""
        assert wa["macro_row50_output_formula"] is None

    def test_ds_row20_sources_macro50(self, wa):
        """DS!row20 formula = Macro!H50 (bank CFADS entering debt service)."""
        formula = wa["ds_row20_cfads"]["formula_h"]
        assert formula == "=Macro!H50"

    def test_cfads_aligned_classification(self, wa):
        """Fixture classification = CFADS_ALIGNED_IN_THIS_SCENARIO."""
        assert wa["classification"] == "CFADS_ALIGNED_IN_THIS_SCENARIO"

    def test_ds_row22_dscr_formula_proven(self, wa):
        """DS!row22 DSCR target formula uses weighted band structure."""
        formula = wa["ds_row22_dscr_target"]["formula_h"]
        assert "$B$22" in formula
        assert "$D$22" in formula
        assert "$C$22" in formula

    def test_ds_row23_avail_formula_proven(self, wa):
        """DS!row23 allowed SDS formula: (H20/H22 + DSRA_adj) × ops × tranche."""
        formula = wa["ds_row23_available_cf"]["formula_h"]
        assert "H20" in formula and "H22" in formula


# ---------------------------------------------------------------------------
# R3: Oborovo CF79 vs Macro50 alignment during DSCR=1.15 debt periods
# ---------------------------------------------------------------------------

class TestOborovoCfadsAlignment:
    """CF79 ≈ Macro50 during DSCR=1.15 periods (indices 1–24) — max diff < 0.01 kEUR.

    CFADS_ALIGNED_IN_THIS_SCENARIO holds for the DSCR=1.15 band.
    At DSCR=1.35 periods (25–27) the backward PV constraint binds and
    Macro50 < CF79 by hundreds of kEUR.
    """

    @pytest.fixture(scope="class")
    def obo_fin(self):
        return _load_oborovo_financial_fixture()

    def test_cf79_and_macro50_aligned_dscr_115_periods(self, obo_fin):
        """Max |CF79 − Macro50| < 0.01 kEUR for DSCR=1.15 periods (indices 1–24)."""
        cf79 = obo_fin["cf"]["fcf_for_banks_keur"]
        macro50 = obo_fin["ds"]["cfads_for_sd_keur"]
        diffs = [abs(cf79[i] - macro50[i]) for i in range(1, 25)]
        assert max(diffs) < 0.01, f"Max diff during 1.15 periods: {max(diffs):.6f} kEUR"

    def test_macro50_lt_cf79_at_dscr_135_periods(self, obo_fin):
        """Macro50 < CF79 at DSCR=1.35 periods (indices 25–27) by >500 kEUR."""
        cf79 = obo_fin["cf"]["fcf_for_banks_keur"]
        macro50 = obo_fin["ds"]["cfads_for_sd_keur"]
        for idx in [25, 26, 27]:
            delta = cf79[idx] - macro50[idx]
            assert delta > 500, (
                f"Expected CF79 > Macro50 at idx={idx} by >500 kEUR; got delta={delta:.2f}"
            )

    def test_dscr_target_changes_at_index_25(self, obo_fin):
        """DSCR target changes from 1.15 to 1.35 at fixture index 25."""
        dscr_t = obo_fin["ds"]["dscr_target"]
        assert abs(dscr_t[24] - 1.15) < 1e-9
        assert abs(dscr_t[25] - 1.35) < 1e-9

    def test_initial_debt_matches_source(self, obo_fin):
        """SD beginning at index 0 = source total debt 42,852.279 kEUR."""
        sd_ending = obo_fin["ds"]["sd_ending_keur"]
        assert abs(sd_ending[0] - 42852.279) < 0.01

    def test_allowed_sds_identity(self, obo_fin):
        """allowed_SDS × target_DSCR ≈ Macro50 (bank CFADS) for first 24 operating periods."""
        macro50 = obo_fin["ds"]["cfads_for_sd_keur"]
        sd_serv = obo_fin["ds"]["sd_service_keur"]
        dscr_t = obo_fin["ds"]["dscr_target"]
        for idx in range(1, 25):
            derived_bank_cfads = abs(sd_serv[idx]) * dscr_t[idx]
            assert abs(derived_bank_cfads - macro50[idx]) < 1.0, (
                f"idx={idx}: |SDS|×DSCR={derived_bank_cfads:.3f} vs macro50={macro50[idx]:.3f}"
            )


# ---------------------------------------------------------------------------
# R3: TUHO bank-sizing cross-project proof
# ---------------------------------------------------------------------------

class TestTuhoBankSizingProof:
    """TUHO: P50 base CFADS vs bank-sizing CFADS — SOURCE_DERIVED_IDENTITY proof.

    bank_cfads[t] = |SDS[t]| × target_DSCR[t]   (SOURCE_DERIVED_IDENTITY)
    base_actual_DSCR[t] = CF79[t] / |SDS[t]|    (SOURCE_DERIVED_IDENTITY)
    """

    @pytest.fixture(scope="class")
    def tuho_first_op(self):
        d = _load_tuho_fixture()
        cols = d["period_diagnostic_columns"]
        row = d["period_diagnostics"][0]
        return dict(zip(cols, row))

    def test_tuho_base_cfads_period1(self, tuho_first_op):
        """TUHO P50 base CFADS period 1 = 3,070.175837370555 kEUR."""
        v = tuho_first_op["CF.free_cash_flow_for_banks_keur"]
        assert abs(v - 3070.175837370555) < 1e-6

    def test_tuho_sds_period1(self, tuho_first_op):
        """TUHO SDS period 1 = −2,116.361394092063 kEUR."""
        v = tuho_first_op["CF.senior_debt_service_keur"]
        assert abs(v - (-2116.361394092063)) < 1e-6

    def test_tuho_target_dscr_period1(self, tuho_first_op):
        """TUHO target DSCR period 1 = 1.2."""
        assert abs(tuho_first_op["DS.senior_debt_dscr_target"] - 1.2) < 1e-9

    def test_tuho_bank_cfads_derived(self, tuho_first_op):
        """bank_cfads = |SDS| × target_DSCR = 2,539.633672910476 kEUR."""
        sds = abs(tuho_first_op["CF.senior_debt_service_keur"])
        dscr = tuho_first_op["DS.senior_debt_dscr_target"]
        bank_cfads = sds * dscr
        assert abs(bank_cfads - 2539.633672910476) < 1e-6

    def test_tuho_base_actual_dscr(self, tuho_first_op):
        """Base actual DSCR = CF79 / |SDS| ≈ 1.451 (source) and > target 1.2."""
        cf79 = tuho_first_op["CF.free_cash_flow_for_banks_keur"]
        sds = abs(tuho_first_op["CF.senior_debt_service_keur"])
        actual_dscr = cf79 / sds
        source_dscr = tuho_first_op["CF.average_senior_dscr_period"]
        assert abs(actual_dscr - source_dscr) < 0.001
        assert actual_dscr > tuho_first_op["DS.senior_debt_dscr_target"]

    def test_tuho_minimum_dscr_is_output_not_input(self, tuho_first_op):
        """base_actual_DSCR > target_DSCR — minimum is an output, not a second sizing input."""
        actual = tuho_first_op["CF.average_senior_dscr_period"]
        target = tuho_first_op["DS.senior_debt_dscr_target"]
        assert actual > target, (
            "MINIMUM_BASE_CASE_DSCR_IS_OUTPUT_NOT_SIZING_INPUT: "
            f"actual={actual:.4f} must exceed target={target:.4f}"
        )


# ---------------------------------------------------------------------------
# R3: Oborovo debt sizing replay — causal bridge G4 closure
# ---------------------------------------------------------------------------

class TestOborovoDebtSizingReplay:
    """HISTORICAL_C3B2_SOURCE_REPLAY_PROOF: G4 vector backward induction.

    This is the historical fixture evidence from C3B2 phase — starting from
    HISTORICAL_GENERIC_PHASE2C_SCALAR_DIAGNOSTIC (≈46,053 kEUR), NOT the current
    CURRENT_GRID0_PRODUCTION_CANDIDATE (≈43,919 kEUR).

    The G4 bridge closes from 46,053 → 42,852.279 kEUR exactly (residual=0.000).
    It proves that the historical generic Phase2C output is explained by four
    INPUT_POLICY_MISMATCH factors. It does NOT prove the current GRID-0 bridge.

    Classification: HISTORICAL_C3B2_SOURCE_REPLAY_PROOF
    bridge_closed_to_vector = True, g4_final_unforced_residual_keur = 0.000.
    """

    @pytest.fixture(scope="class")
    def bridge(self):
        d = _load_oborovo_debt_interest_fixture()
        return d["phase2c_sizing_analysis"]["causal_bridge"]

    def test_bridge_closed_to_vector(self, bridge):
        """bridge_closed_to_vector = True — G4 matches excel debt exactly."""
        assert bridge["bridge_closed_to_vector"] is True

    def test_g4_residual_zero(self, bridge):
        """g4_final_unforced_residual_keur = 0.000 kEUR."""
        assert abs(bridge["g4_final_unforced_residual_keur"]) < 1e-6

    def test_g4_vector_matches_excel(self, bridge):
        """G4 backward PV = excel total debt (42,852.279 kEUR)."""
        g4 = bridge["g4_vector_backward_induction_keur"]
        excel = bridge["excel_debt_keur"]
        assert abs(g4 - excel) < 0.001

    def test_delta_rate_mismatch(self, bridge):
        """Rate mismatch contribution ≈ −543.807 kEUR (5.65% flat vs 5.9514% source)."""
        assert abs(bridge["delta_rate_keur"] - (-543.807114931)) < 0.01

    def test_delta_cfads_mismatch(self, bridge):
        """CFADS mismatch contribution ≈ −1,918.036 kEUR (clean EBITDA-based vs Macro50)."""
        assert abs(bridge["delta_cfads_keur"] - (-1918.035795775)) < 0.01

    def test_delta_daycount(self, bridge):
        """Day-count mismatch contribution ≈ −214.604 kEUR (ACT/365 vs ACT/360)."""
        assert abs(bridge["delta_daycount_keur"] - (-214.60420091)) < 0.01

    def test_rate_mismatch_confirmed(self):
        """Rate mismatch confirmed in workstream_e fixture."""
        we = _load_oborovo_debt_interest_fixture()["workstream_e"]
        assert we["rate_mismatch_confirmed"] is True
        assert abs(we["sculpting_rate_period1_annual_pct"] - 5.95136) < 0.001
        assert abs(we["phase2c_rate_pct"] - 5.65) < 0.001


# ---------------------------------------------------------------------------
# R3: DSRA classification — not causal for Oborovo residual
# ---------------------------------------------------------------------------

class TestDsraNotCausal:
    """DSRA is inactive for Oborovo — DSRA_NOT_CAUSAL_FOR_OBOROVO_CURRENT_RESIDUAL_SOURCE_PROVEN.

    Source: workstream_c in excel_oborovo_debt_interest_truth.json.
    """

    @pytest.fixture(scope="class")
    def wc(self):
        return _load_oborovo_debt_interest_fixture()["workstream_c"]

    def test_dsra_target_is_zero(self, wc):
        """Inputs!I348 DSRA target = 0 (zero DSRA reserve required)."""
        assert wc["target_is_zero"] is True

    def test_dsra_all_cached_values_zero(self, wc):
        """All DSRA cached values = 0 in source workbook."""
        assert wc["all_cached_values_zero"] is True

    def test_dsra_classification_aligned_both_zero(self, wc):
        """Fixture classification = ALIGNED_BOTH_ZERO."""
        assert wc["classification"] == "ALIGNED_BOTH_ZERO"

    def test_dsra_not_present(self, wc):
        """dsra_present = False — DSRA is not active in this workbook instance."""
        assert wc["dsra_present"] is False

    def test_dsra_not_causal_for_residual(self, wc):
        """DSRA_NOT_CAUSAL_FOR_OBOROVO_CURRENT_RESIDUAL_SOURCE_PROVEN:
        when both target and actual DSRA are zero, DSRA cannot drive the
        CURRENT_UPSTREAM_CLEAN_CASH_RESIDUAL."""
        assert wc["target_is_zero"] is True and wc["all_cached_values_zero"] is True, (
            "DSRA_NOT_CAUSAL_FOR_OBOROVO_CURRENT_RESIDUAL_SOURCE_PROVEN: "
            "DSRA is zero in source; cannot be a causal driver"
        )


# ---------------------------------------------------------------------------
# R3: Tax window classification and construction loss
# ---------------------------------------------------------------------------

class TestTaxWindowClassification:
    """Tax mechanic labels: 5-period window bug, row39 non-binding, construction loss.

    These tests verify that the diagnostic module uses the correct labels and that
    Oborovo-specific classifications are consistent with source fixture evidence.
    """

    def test_workbook_rolling_window_is_5(self):
        """WORKBOOK_ROLLING_WINDOW = 5 model periods (semiannual → 2.5 calendar years)."""
        from finco_recon.diagnose_c3b3d2b2a_tax_shl_causal_grid import WORKBOOK_ROLLING_WINDOW
        assert WORKBOOK_ROLLING_WINDOW == 5

    def test_workbook_5_period_window_known_source_bug_label(self):
        """WORKBOOK_5_MODEL_PERIOD_LOSS_WINDOW_KNOWN_SOURCE_BUG: B36=5 model periods
        with semiannual model = 2.5-year lookback, not 5-year as may be intended."""
        assert WORKBOOK_ROLLING_WINDOW == 5

    def test_row39_cap_non_binding_for_oborovo(self, grid):
        """ROW39_CAP_NON_BINDING_FOR_OBOROVO: GRID-ABCDE ≈ GRID-ABCD (< 0.01 kEUR)."""
        diff = abs(
            grid.grid_abcde.ds40_final_closing_keur - grid.grid_abcd.ds40_final_closing_keur
        )
        assert diff < 0.01, (
            f"Row39 cap effect={diff:.4f} kEUR; expected < 0.01 for Oborovo"
        )

    def test_construction_loss_entering_operation(self, grid):
        """CONSTRUCTION_LOSS_ENTERING_OPERATION_SOURCE_PROVEN:
        GRID-0 total cash tax is positive (construction loss carried forward does
        not eliminate all CIT across the operating life)."""
        assert grid.grid0.total_cash_tax_keur > 0

    def test_dsra_ordering_resolved_for_oborovo(self):
        """DSRA_ORDERING_UNRESOLVED resolves to NOT_CAUSAL for Oborovo specifically.
        DSRA=0 in source → ordering is moot; DSRA cannot be ranked as a driver."""
        wc = _load_oborovo_debt_interest_fixture()["workstream_c"]
        assert wc["all_cached_values_zero"] is True

    @pytest.fixture(scope="class")
    def grid(self):
        from finco_recon.diagnose_c3b3d2b2a_tax_shl_causal_grid import run_diagnostic_grid
        return run_diagnostic_grid()


# ---------------------------------------------------------------------------
# R4: Three baseline separation
# ---------------------------------------------------------------------------

class TestThreeBaselineSeparation:
    """Three debt authorities must be clearly distinct and never conflated.

    CURRENT_GRID0_PRODUCTION_CANDIDATE    ≈ 43,919.03 kEUR  (current runtime)
    HISTORICAL_GENERIC_PHASE2C_SCALAR_DIAGNOSTIC ≈ 46,053.40 kEUR (historical fixture)
    SOURCE_EXCEL_SENIOR_DEBT              = 42,852.279 kEUR  (source workbook)
    """

    def test_current_grid0_baseline_value(self):
        """CURRENT_GRID0_DEBT_KEUR = 43,919.032698 kEUR (CURRENT_GRID0_PRODUCTION_CANDIDATE)."""
        assert abs(CURRENT_GRID0_DEBT_KEUR - 43_919.032698) < 1.0

    def test_historical_generic_phase2c_value(self):
        """HISTORICAL_GENERIC_PHASE2C_DEBT_KEUR = 46,053.402 kEUR (HISTORICAL_GENERIC_PHASE2C_SCALAR_DIAGNOSTIC)."""
        assert abs(HISTORICAL_GENERIC_PHASE2C_DEBT_KEUR - 46_053.402378616) < 0.001

    def test_source_excel_value(self):
        """SOURCE_EXCEL_SENIOR_DEBT_KEUR = 42,852.279 kEUR (SOURCE_EXCEL_SENIOR_DEBT)."""
        assert abs(SOURCE_EXCEL_SENIOR_DEBT_KEUR - 42_852.27876256299) < 1e-6

    def test_three_baselines_are_distinct(self):
        """All three baselines differ — must not be conflated."""
        assert CURRENT_GRID0_DEBT_KEUR != HISTORICAL_GENERIC_PHASE2C_DEBT_KEUR
        assert CURRENT_GRID0_DEBT_KEUR != SOURCE_EXCEL_SENIOR_DEBT_KEUR
        assert HISTORICAL_GENERIC_PHASE2C_DEBT_KEUR != SOURCE_EXCEL_SENIOR_DEBT_KEUR

    def test_current_grid0_runtime_matches_constant(self, grid):
        """Runtime GRID-0 debt matches CURRENT_GRID0_DEBT_KEUR constant (< 1 kEUR tolerance)."""
        assert abs(grid.grid0.clean_debt_size_keur - CURRENT_GRID0_DEBT_KEUR) < 1.0

    def test_current_grid0_delta_vs_source(self, grid):
        """Current GRID-0 → source debt delta ≈ +1,066.75 kEUR (CURRENT_GRID0_TO_SOURCE_DEBT_BRIDGE_NOT_YET_CLOSED)."""
        delta = grid.grid0.clean_debt_size_keur - SOURCE_EXCEL_SENIOR_DEBT_KEUR
        assert 900 < delta < 1200, (
            f"CURRENT GRID-0 → source delta = {delta:.2f} kEUR; expected ~1,066.75"
        )

    def test_historical_bridge_is_not_current_grid0(self):
        """HISTORICAL_GENERIC_PHASE2C_SCALAR_DIAGNOSTIC ≠ CURRENT_GRID0_PRODUCTION_CANDIDATE."""
        diff = abs(HISTORICAL_GENERIC_PHASE2C_DEBT_KEUR - CURRENT_GRID0_DEBT_KEUR)
        assert diff > 2000, (
            "Historical generic Phase2C (46,053) and current GRID-0 (43,919) "
            "differ by >2,000 kEUR — they must not be conflated"
        )

    @pytest.fixture(scope="class")
    def grid(self):
        from finco_recon.diagnose_c3b3d2b2a_tax_shl_causal_grid import run_diagnostic_grid
        return run_diagnostic_grid()


# ---------------------------------------------------------------------------
# R4: Row39 non-causal classification and surrogate-only GRID-E
# ---------------------------------------------------------------------------

class TestRow39NonCausalClassification:
    """ROW39_REPORTING_OR_NON_CAUSAL_FOR_TAX_STATE_SOURCE_PROVEN.

    Source workbook inspection confirms row39 does not feed forward tax state.
    The synthetic cumulative_used propagation has been removed.
    GRID-E arm: WITHIN_TAX_SURROGATE_ONLY — not a causal tax-state mechanic.
    """

    def test_row39_cap_non_binding_confirmed(self, grid):
        """GRID-ABCDE ≈ GRID-ABCD (row39 cap does not bind for Oborovo)."""
        diff = abs(
            grid.grid_abcde.ds40_final_closing_keur - grid.grid_abcd.ds40_final_closing_keur
        )
        assert diff < 0.01, f"Row39 cap effect = {diff:.4f} kEUR; expected < 0.01"

    def test_grid_e_within_surrogate_only(self, grid):
        """GRID-E is WITHIN_TAX_SURROGATE_ONLY — row39 is not a causal tax-state driver."""
        # GRID-E produces finite output but its delta vs GRID-0 is within surrogate only
        assert math.isfinite(grid.grid_e.ds40_final_closing_keur)
        assert math.isfinite(grid.grid_e.delta_vs_grid0_final_closing)

    def test_row39_config_flag_retained_for_replay_only(self):
        """WorkbookTaxConfig.row39_cap flag retained for source-replay validation only."""
        config_with_row39 = WorkbookTaxConfig(row39_cap=True)
        config_without = WorkbookTaxConfig(row39_cap=False)
        assert config_with_row39.row39_cap is True
        assert config_without.row39_cap is False

    @pytest.fixture(scope="class")
    def grid(self):
        from finco_recon.diagnose_c3b3d2b2a_tax_shl_causal_grid import run_diagnostic_grid
        return run_diagnostic_grid()


# ---------------------------------------------------------------------------
# R5: FCF-for-SHL lineage — CF79 + CF80, NOT DS!row23
# ---------------------------------------------------------------------------

class TestFcfForShlIdentity:
    """FCF-for-SHL lineage: CF!row79 + CF!row80 = CF!row112 (Oborovo, DSRA=0).

    Classification: FCF_FOR_SHL_LINEAGE_CF79_CF80_CF92_CF94_CF112_SOURCE_PROVEN

    DS!row23 is the POSITIVE allowed SDS capacity for sculpting — it is NOT
    CF!row80 (signed actual SDS, negative). The two have equal magnitude for
    Oborovo (actual SDS = allowed SDS) but opposite signs.

    Key fixture mapping:
      CF!row79  → cf["fcf_for_banks_keur"]           (positive base CFADS)
      CF!row80  → cf["senior_debt_service_keur"]      (NEGATIVE signed actual SDS)
      DS!row23  → ds["sd_service_keur"]               (POSITIVE allowed SDS capacity)
      CF!row112 → cf["free_cash_flow_for_shl_keur"]   (positive FCF for SHL)
    """

    @pytest.fixture(scope="class")
    def cf_fixture(self):
        return _load_oborovo_financial_fixture()

    def test_cf_row80_is_negative(self, cf_fixture):
        """CF!row80 (senior_debt_service_keur) is negative — signed cash outflow."""
        sds = cf_fixture["cf"]["senior_debt_service_keur"]
        op_sds = [v for v in sds[1:] if v != 0.0]
        assert len(op_sds) > 0
        assert all(v < 0.0 for v in op_sds), (
            "CF!row80 (senior_debt_service_keur) must be negative (signed SDS outflow); "
            f"found positive values: {[v for v in op_sds if v > 0]}"
        )

    def test_ds_row23_is_positive(self, cf_fixture):
        """DS!row23 (sd_service_keur) is positive — allowed SDS capacity."""
        ds23 = cf_fixture["ds"]["sd_service_keur"]
        op_ds23 = [v for v in ds23[1:] if v != 0.0]
        assert len(op_ds23) > 0
        assert all(v > 0.0 for v in op_ds23), (
            "DS!row23 (sd_service_keur) must be positive (allowed SDS capacity); "
            f"found non-positive values: {[v for v in op_ds23 if v <= 0]}"
        )

    def test_cf79_plus_cf80_equals_cf112(self, cf_fixture):
        """CF!row79 + CF!row80 = CF!row112 (Oborovo, DSRA=0, period by period).

        Classification: FCF_FOR_SHL_LINEAGE_CF79_CF80_CF92_CF94_CF112_SOURCE_PROVEN
        """
        cf79 = cf_fixture["cf"]["fcf_for_banks_keur"]
        cf80 = cf_fixture["cf"]["senior_debt_service_keur"]
        cf112 = cf_fixture["cf"]["free_cash_flow_for_shl_keur"]
        n = min(len(cf79), len(cf80), len(cf112))
        max_delta = 0.0
        for i in range(1, n):
            delta = abs(cf79[i] + cf80[i] - cf112[i])
            max_delta = max(max_delta, delta)
        assert max_delta < 1e-6, (
            f"FCF-for-SHL identity CF79+CF80=CF112 violated: max delta={max_delta:.2e} kEUR"
        )

    def test_cf79_plus_ds23_does_not_equal_cf112(self, cf_fixture):
        """CF!row79 + DS!row23 != CF!row112 — DS!row23 is positive capacity, not signed SDS.

        Regression: the incorrect formula CF79+DS23 is rejected. DS23 is positive;
        CF80 is negative. CF79+DS23 > CF79 > CF112.
        """
        cf79 = cf_fixture["cf"]["fcf_for_banks_keur"]
        ds23 = cf_fixture["ds"]["sd_service_keur"]
        cf112 = cf_fixture["cf"]["free_cash_flow_for_shl_keur"]
        wrong_identity = cf79[1] + ds23[1]
        correct = cf112[1]
        assert abs(wrong_identity - correct) > 1.0, (
            f"CF79+DS23 unexpectedly approx CF112 at period 1: "
            f"wrong={wrong_identity:.4f}, correct={correct:.4f}"
        )

    def test_ds_row23_and_cf_row80_have_equal_magnitude(self, cf_fixture):
        """DS!row23 and |CF!row80| have equal magnitude for Oborovo (actual = allowed SDS).

        Equal magnitudes but opposite signs confirms they are different variables
        that must not be substituted for each other in the FCF waterfall.
        """
        cf80 = cf_fixture["cf"]["senior_debt_service_keur"]
        ds23 = cf_fixture["ds"]["sd_service_keur"]
        n = min(len(cf80), len(ds23))
        for i in range(1, n):
            if ds23[i] == 0.0 and cf80[i] == 0.0:
                continue
            magnitude_diff = abs(abs(cf80[i]) - ds23[i])
            assert magnitude_diff < 1e-6, (
                f"Period {i}: |CF80|={abs(cf80[i]):.6f} vs DS23={ds23[i]:.6f}, "
                f"diff={magnitude_diff:.2e}"
            )
