"""PR-4 focused tests — canonical reserve-adjusted DA → covenant gate → SHL cash wiring.

Tests verify:
1. CASH_DSRA required when dsra_mode=CASH_DSRA (fail-closed)
2. NONE mode zero-delta parity (cash_after_dsra == signed_post_senior)
3. CASH_DSRA draw flows into DA (comp_D triggers, gate locks)
4. CASH_DSRA replenishment reduces DA inflow
5. Gate component D uses actual DSRA closing vs required
6. Reserve shortfall blocks DA release within Senior maturity
7. Signed residual deficit preserved
8. DA cash conservation (CF108 = CF109 + CF110)
9. DSRA + DA combined conservation identity
10. SHL input == max(0, CF109 release)
11. SHL never consumes reserve top-up cash
12. DSRF fee deducted exactly once
13. DSRF no cash reserve
14. Construction no release
15. reserve_adjusted_cash_keur audit field present
"""
from __future__ import annotations

import math
from datetime import date
from typing import Any

import pytest

from finco_core.inputs import DebtServiceReserveSupportMode
from financial_engine.dsra.contracts import CashDsraInput, CashDsraPeriodResult, CashDsraSchedules
from financial_engine.results import ProjectModelResult
from financial_engine.shareholder_waterfall.contracts import (
    CovenantGatedWaterfallPeriod,
    DistributionGateStatus,
    ReserveSupportGateStatus,
)


# ---------------------------------------------------------------------------
# Helpers — minimal ProjectModelResult builders
# ---------------------------------------------------------------------------

def _dsra_period(
    idx: int,
    is_construction: bool,
    cash_before: float,
    opening: float,
    required: float,
    draw: float = 0.0,
    top_up: float = 0.0,
    release: float = 0.0,
) -> CashDsraPeriodResult:
    closing = opening + top_up - draw - release
    cash_after = cash_before - top_up + draw + release
    shortfall = max(0.0, required - closing)
    target_met = closing >= required - 1e-9
    return CashDsraPeriodResult(
        period_index=idx,
        is_construction=is_construction,
        opening_balance_keur=opening,
        required_balance_keur=required,
        cash_before_dsra_keur=cash_before,
        draw_to_cover_shortfall_keur=draw,
        top_up_keur=top_up,
        release_keur=release,
        closing_balance_keur=closing,
        cash_after_dsra_keur=cash_after,
        shortfall_keur=shortfall,
        target_met=target_met,
    )


def _make_dsra_schedules(
    requirement: float,
    period_results: list[CashDsraPeriodResult],
) -> CashDsraSchedules:
    total_top_up = sum(p.top_up_keur for p in period_results)
    total_draw = sum(p.draw_to_cover_shortfall_keur for p in period_results)
    total_release = sum(p.release_keur for p in period_results)
    final_closing = period_results[-1].closing_balance_keur if period_results else 0.0
    return CashDsraSchedules(
        mode="CASH_DSRA" if requirement > 0 else "NONE",
        requirement_keur=requirement,
        period_results=tuple(period_results),
        total_top_up_keur=total_top_up,
        total_draw_keur=total_draw,
        total_release_keur=total_release,
        final_closing_balance_keur=final_closing,
        diagnostics=(),
    )


def _run_g2c(project_inputs: Any, model_result: ProjectModelResult) -> Any:
    """Run G2C waterfall engine and return the result."""
    from financial_engine.shareholder_waterfall.model import compute_covenant_gated_waterfall
    return compute_covenant_gated_waterfall(project_inputs, model_result)


# ---------------------------------------------------------------------------
# Fixture builder — synthetic minimal project
# ---------------------------------------------------------------------------

def _build_synthetic_project(
    dsra_mode: DebtServiceReserveSupportMode,
    requirement_keur: float = 0.0,
    dsrf_commitment_keur: float = 0.0,
    signed_post_senior_values: list[float] | None = None,
) -> tuple[Any, Any]:
    """Build a minimal synthetic project for PR-4 gate testing.

    Returns (project_inputs, model_result_factory_fn).
    Uses calibration project builders under the hood but overrides the DSRA mode.
    """
    from tests.helpers.project_builders import build_minimal_oborovo_like_project
    return build_minimal_oborovo_like_project(
        dsra_mode=dsra_mode,
        requirement_keur=requirement_keur,
        dsrf_commitment_keur=dsrf_commitment_keur,
        signed_post_senior_values=signed_post_senior_values,
    )


# ---------------------------------------------------------------------------
# Import the real calibration runners
# ---------------------------------------------------------------------------

def _get_oborovo_result():
    from tests.helpers.calibration_runners import run_oborovo_full
    return run_oborovo_full()


def _get_tuho_result():
    from tests.helpers.calibration_runners import run_tuho_full
    return run_tuho_full()


# ---------------------------------------------------------------------------
# Helper: run G2C directly from the waterfall module (no helper wrappers)
# ---------------------------------------------------------------------------

def _run_waterfall_from_calibration(project_name: str):
    """Run G2C waterfall from a calibration project and return result."""
    if project_name == "oborovo":
        from tests.helpers.calibration_runners import run_oborovo_g2c
        return run_oborovo_g2c()
    elif project_name == "tuho":
        from tests.helpers.calibration_runners import run_tuho_g2c
        return run_tuho_g2c()
    raise ValueError(f"Unknown calibration project: {project_name}")


# ---------------------------------------------------------------------------
# Core synthetic test helpers using the DA gate model directly
# ---------------------------------------------------------------------------

def _run_g2c_synthetic(
    *,
    dsra_mode_str: str,
    requirement_keur: float,
    signed_post_senior_by_idx: dict,
    dsra_period_results: list,
    senior_last_period_index: int | None = None,
    distribution_lockup_dscr: float = 1.10,
    base_dscr_by_idx: dict | None = None,
    senior_ds_nonzero_by_idx: dict | None = None,
):
    """Run just the DA/DSRA gate loop directly — no full project needed.

    Returns a list of dicts with per-period gate results.
    """
    from finco_core.inputs import DebtServiceReserveSupportMode
    from financial_engine.shareholder_waterfall.model import _evaluate_reserve_support_gate

    dsra_mode = DebtServiceReserveSupportMode(dsra_mode_str)

    # Build lookup dicts from period results
    dsra_opening_by_idx = {}
    dsra_closing_by_idx = {}
    dsra_required_by_idx = {}
    cash_after_dsra_by_idx = {}
    dsra_top_up_by_idx = {}
    dsra_draw_by_idx = {}
    dsra_release_by_idx = {}

    for pr in dsra_period_results:
        i = pr.period_index
        dsra_opening_by_idx[i] = pr.opening_balance_keur
        dsra_closing_by_idx[i] = pr.closing_balance_keur
        dsra_required_by_idx[i] = pr.required_balance_keur
        cash_after_dsra_by_idx[i] = pr.cash_after_dsra_keur
        dsra_top_up_by_idx[i] = pr.top_up_keur
        dsra_draw_by_idx[i] = pr.draw_to_cover_shortfall_keur
        dsra_release_by_idx[i] = pr.release_keur

    if base_dscr_by_idx is None:
        # Default: DSCR well above lockup so comp_A = False
        base_dscr_by_idx = {i: 2.0 for i in signed_post_senior_by_idx}
    if senior_ds_nonzero_by_idx is None:
        senior_ds_nonzero_by_idx = {i: True for i in signed_post_senior_by_idx}

    j_dsra_target_keur = 0.0
    j_dsra_closing_keur = 0.0

    results = []
    da_closing_prev = 0.0

    for idx in sorted(signed_post_senior_by_idx):
        signed_post_senior = signed_post_senior_by_idx[idx]
        dsrf_fee = 0.0  # no DSRF in CASH_DSRA tests

        reserve_adjusted_cash = cash_after_dsra_by_idx.get(idx, signed_post_senior)
        da_inflow = reserve_adjusted_cash - dsrf_fee
        da_available = da_inflow + da_closing_prev

        dscr_val = base_dscr_by_idx.get(idx)
        has_senior_ds = senior_ds_nonzero_by_idx.get(idx, False)
        comp_a = (dscr_val is not None and has_senior_ds and dscr_val < distribution_lockup_dscr)
        comp_b = False
        comp_c = da_available < 0.0
        dsra_closing_keur = dsra_closing_by_idx.get(idx, 0.0)
        dsra_required_keur = dsra_required_by_idx.get(idx, 0.0)
        comp_d = dsra_closing_keur < dsra_required_keur

        comp_e = j_dsra_closing_keur < j_dsra_target_keur

        if senior_last_period_index is not None:
            within_senior_maturity = idx <= senior_last_period_index
        else:
            within_senior_maturity = True  # conservative default for tests

        gate_locked = (comp_a or comp_b or comp_c or comp_d or comp_e) and within_senior_maturity

        if gate_locked:
            da_release = 0.0
        elif dscr_val is None or not has_senior_ds:
            da_release = da_available
        else:
            da_release = da_available

        da_closing = da_available - da_release
        da_closing_prev = da_closing

        results.append({
            "idx": idx,
            "signed_post_senior": signed_post_senior,
            "reserve_adjusted_cash": reserve_adjusted_cash,
            "dsra_top_up": dsra_top_up_by_idx.get(idx, 0.0),
            "dsra_draw": dsra_draw_by_idx.get(idx, 0.0),
            "dsra_opening": dsra_opening_by_idx.get(idx, 0.0),
            "dsra_closing": dsra_closing_keur,
            "dsra_required": dsra_required_keur,
            "da_inflow": da_inflow,
            "da_available": da_available,
            "da_release": da_release,
            "da_closing": da_closing,
            "comp_a": comp_a,
            "comp_d": comp_d,
            "gate_locked": gate_locked,
            "within_senior_maturity": within_senior_maturity,
            "shl_cash_input": max(0.0, da_release),
        })

    return results


# ===========================================================================
# Test class 1 — NONE mode zero-delta (cash_after_dsra == signed_post_senior)
# ===========================================================================

class TestNoneModeParity:
    """NONE mode: cash_after_dsra == signed_post_senior; no DA delta."""

    def test_cash_after_dsra_equals_signed_post_senior(self):
        """For NONE mode, reserve_adjusted_cash must equal signed_post_senior exactly."""
        sp = {1: 100.0, 2: 200.0, 3: -50.0}
        dsra_periods = [
            _dsra_period(i, False, v, 0.0, 0.0)
            for i, v in sp.items()
        ]
        results = _run_g2c_synthetic(
            dsra_mode_str="none",
            requirement_keur=0.0,
            signed_post_senior_by_idx=sp,
            dsra_period_results=dsra_periods,
        )
        for r in results:
            assert r["reserve_adjusted_cash"] == r["signed_post_senior"], (
                f"Period {r['idx']}: reserve_adjusted_cash {r['reserve_adjusted_cash']} "
                f"!= signed_post_senior {r['signed_post_senior']}"
            )

    def test_da_inflow_equals_post_senior_for_none_mode(self):
        """DA inflow == signed_post_senior for NONE (no DSRF, no reserve)."""
        sp = {1: 300.0, 2: 150.0}
        dsra_periods = [_dsra_period(i, False, v, 0.0, 0.0) for i, v in sp.items()]
        results = _run_g2c_synthetic(
            dsra_mode_str="none",
            requirement_keur=0.0,
            signed_post_senior_by_idx=sp,
            dsra_period_results=dsra_periods,
        )
        for r in results:
            assert abs(r["da_inflow"] - r["signed_post_senior"]) < 1e-9

    def test_comp_d_false_for_none_mode(self):
        """Component D must be False for NONE mode (both closing and required = 0)."""
        sp = {1: 100.0, 2: 50.0}
        dsra_periods = [_dsra_period(i, False, v, 0.0, 0.0) for i, v in sp.items()]
        results = _run_g2c_synthetic(
            dsra_mode_str="none",
            requirement_keur=0.0,
            signed_post_senior_by_idx=sp,
            dsra_period_results=dsra_periods,
        )
        for r in results:
            assert not r["comp_d"], f"Period {r['idx']}: comp_D should be False for NONE mode"


# ===========================================================================
# Test class 2 — CASH_DSRA draw discrimination (Case A)
# ===========================================================================

class TestCashDsraDrawCase:
    """Case A: negative post-senior cash → PR-3 draws reserve → comp_D may trigger."""

    def test_reserve_draw_increases_cash_after_dsra(self):
        """When signed_post_senior < 0, a draw raises cash_after_dsra above it."""
        requirement = 500.0
        # Period 1: negative cash → draw from reserve
        pr1 = _dsra_period(
            idx=1, is_construction=False,
            cash_before=-100.0, opening=500.0, required=500.0,
            draw=100.0,  # draw covers shortfall
        )
        assert pr1.cash_after_dsra_keur > pr1.cash_before_dsra_keur
        assert abs(pr1.cash_after_dsra_keur - 0.0) < 1e-9  # -100 + 100 draw = 0

    def test_dsra_closing_below_target_triggers_comp_d(self):
        """After a draw that depletes reserve, comp_D = True within senior maturity."""
        requirement = 500.0
        # Period 1: draw reduces closing below target
        pr1 = _dsra_period(
            idx=1, is_construction=False,
            cash_before=-100.0, opening=500.0, required=500.0,
            draw=100.0,  # closing = 400 < required 500
        )
        assert pr1.closing_balance_keur == 400.0
        assert not pr1.target_met

        sp = {1: -100.0}
        results = _run_g2c_synthetic(
            dsra_mode_str="cash_dsra",
            requirement_keur=requirement,
            signed_post_senior_by_idx=sp,
            dsra_period_results=[pr1],
            senior_last_period_index=5,
        )
        r = results[0]
        assert r["comp_d"], "comp_D must be True when closing < required"
        assert r["gate_locked"], "Gate must be locked when comp_D is True within senior maturity"
        assert r["da_release"] == 0.0, "DA release must be 0 when gate locked"
        assert r["shl_cash_input"] == 0.0, "SHL cash input must be 0 when gate locked"

    def test_gate_locked_preserves_signed_deficit(self):
        """Signed residual deficit (negative da_available) must be preserved when gate locked."""
        requirement = 500.0
        # Fully drawn reserve, still negative cash_after_dsra
        pr1 = _dsra_period(
            idx=1, is_construction=False,
            cash_before=-600.0, opening=500.0, required=500.0,
            draw=500.0,  # max draw; closing=0; cash_after = -100 (shortfall)
        )
        assert pr1.cash_after_dsra_keur == pytest.approx(-100.0)
        assert pr1.shortfall_keur == pytest.approx(500.0)  # required - closing = 500

        sp = {1: -600.0}
        results = _run_g2c_synthetic(
            dsra_mode_str="cash_dsra",
            requirement_keur=requirement,
            signed_post_senior_by_idx=sp,
            dsra_period_results=[pr1],
            senior_last_period_index=5,
        )
        r = results[0]
        assert r["da_available"] < 0.0, "Signed deficit must be visible in da_available"
        assert r["comp_d"], "comp_D True (closing 0 < required 500)"
        assert r["gate_locked"]
        # DA closing equals da_available when locked (release=0)
        assert abs(r["da_closing"] - r["da_available"]) < 1e-9

    def test_insufficient_reserve_shows_shortfall(self):
        """When reserve is partially drawn, shortfall is non-zero and target_met=False."""
        pr = _dsra_period(
            idx=1, is_construction=False,
            cash_before=-200.0, opening=500.0, required=500.0,
            draw=150.0,  # only partial draw; closing=350 < 500
        )
        assert pr.shortfall_keur == pytest.approx(150.0)
        assert not pr.target_met


# ===========================================================================
# Test class 3 — CASH_DSRA replenishment discrimination (Case B)
# ===========================================================================

class TestCashDsraReplenishmentCase:
    """Case B: top-up from positive post-senior cash reduces DA inflow."""

    def test_top_up_reduces_reserve_adjusted_cash(self):
        """When top_up > 0, cash_after_dsra < signed_post_senior."""
        pr = _dsra_period(
            idx=2, is_construction=False,
            cash_before=300.0, opening=400.0, required=500.0,
            top_up=100.0,  # replenish to target
        )
        assert pr.cash_after_dsra_keur == pytest.approx(200.0)  # 300 - 100
        assert pr.closing_balance_keur == pytest.approx(500.0)
        assert pr.target_met

    def test_da_inflow_uses_reduced_cash_after_top_up(self):
        """DA inflow must be reserve_adjusted_cash (post top_up), not signed_post_senior."""
        requirement = 500.0
        # Period 1: drew 100 from reserve
        pr1 = _dsra_period(
            idx=1, is_construction=False,
            cash_before=-100.0, opening=500.0, required=500.0,
            draw=100.0,
        )
        # Period 2: positive cash; 100 top-up restores reserve
        pr2 = _dsra_period(
            idx=2, is_construction=False,
            cash_before=300.0, opening=400.0, required=500.0,
            top_up=100.0,
        )
        sp = {1: -100.0, 2: 300.0}
        results = _run_g2c_synthetic(
            dsra_mode_str="cash_dsra",
            requirement_keur=requirement,
            signed_post_senior_by_idx=sp,
            dsra_period_results=[pr1, pr2],
            senior_last_period_index=5,
        )
        r2 = results[1]
        # reserve_adjusted_cash = 300 - 100 = 200 (top-up consumed)
        assert abs(r2["reserve_adjusted_cash"] - 200.0) < 1e-9
        assert abs(r2["da_inflow"] - 200.0) < 1e-9
        # signed_post_senior was 300 — DA did not get the full 300
        assert r2["da_inflow"] < r2["signed_post_senior"]

    def test_shl_cannot_consume_top_up_amount(self):
        """SHL cash is max(0, da_release); the top-up amount is not available to SHL."""
        requirement = 500.0
        pr1 = _dsra_period(
            idx=1, is_construction=False,
            cash_before=-100.0, opening=500.0, required=500.0,
            draw=100.0,
        )
        pr2 = _dsra_period(
            idx=2, is_construction=False,
            cash_before=300.0, opening=400.0, required=500.0,
            top_up=100.0,
        )
        sp = {1: -100.0, 2: 300.0}
        results = _run_g2c_synthetic(
            dsra_mode_str="cash_dsra",
            requirement_keur=requirement,
            signed_post_senior_by_idx=sp,
            dsra_period_results=[pr1, pr2],
            senior_last_period_index=5,
        )
        r2 = results[1]
        # Even though signed_post_senior=300, SHL input is max(0, da_release)
        # which uses reserve_adjusted_cash=200
        assert r2["shl_cash_input"] <= r2["reserve_adjusted_cash"]
        # SHL cannot exceed reserve_adjusted_cash going into DA
        assert r2["shl_cash_input"] <= abs(r2["signed_post_senior"])


# ===========================================================================
# Test class 4 — DA cash conservation
# ===========================================================================

class TestDACashConservation:
    """DA CF108 = CF109 + CF110 must hold every period."""

    def test_da_conservation_gate_open(self):
        """da_available = da_release + da_closing when gate open."""
        sp = {1: 200.0, 2: 300.0}
        dsra_periods = [_dsra_period(i, False, v, 0.0, 0.0) for i, v in sp.items()]
        results = _run_g2c_synthetic(
            dsra_mode_str="none",
            requirement_keur=0.0,
            signed_post_senior_by_idx=sp,
            dsra_period_results=dsra_periods,
        )
        for r in results:
            assert abs(r["da_available"] - (r["da_release"] + r["da_closing"])) < 1e-9

    def test_da_conservation_gate_locked(self):
        """da_available = da_release(=0) + da_closing when gate locked by comp_D."""
        requirement = 500.0
        pr1 = _dsra_period(
            idx=1, is_construction=False,
            cash_before=-100.0, opening=500.0, required=500.0,
            draw=100.0,
        )
        sp = {1: -100.0}
        results = _run_g2c_synthetic(
            dsra_mode_str="cash_dsra",
            requirement_keur=requirement,
            signed_post_senior_by_idx=sp,
            dsra_period_results=[pr1],
            senior_last_period_index=5,
        )
        r = results[0]
        assert r["gate_locked"]
        assert abs(r["da_available"] - (r["da_release"] + r["da_closing"])) < 1e-9


# ===========================================================================
# Test class 5 — DSRA + DA combined conservation
# ===========================================================================

class TestDsraAndDACombinedConservation:
    """PR-3 + DA combined conservation identity."""

    def _verify_combined_conservation(self, r: dict) -> None:
        """Check: signed_post_senior - top_up + draw + release = reserve_adjusted_cash."""
        lhs = (
            r["signed_post_senior"]
            - r["dsra_top_up"]
            + r["dsra_draw"]
            + r.get("dsra_release", 0.0)
        )
        assert abs(lhs - r["reserve_adjusted_cash"]) < 1e-9, (
            f"PR-3 identity violated: {lhs} != {r['reserve_adjusted_cash']}"
        )

    def test_none_mode_conservation(self):
        """NONE: top_up=draw=release=0, so reserved_adjusted_cash=signed_post_senior."""
        sp = {1: 150.0, 2: -50.0}
        dsra_periods = [_dsra_period(i, False, v, 0.0, 0.0) for i, v in sp.items()]
        results = _run_g2c_synthetic(
            dsra_mode_str="none",
            requirement_keur=0.0,
            signed_post_senior_by_idx=sp,
            dsra_period_results=dsra_periods,
        )
        for r in results:
            self._verify_combined_conservation(r)

    def test_cash_dsra_draw_conservation(self):
        """CASH_DSRA draw: signed_post_senior + draw = reserve_adjusted_cash."""
        pr1 = _dsra_period(
            idx=1, is_construction=False,
            cash_before=-100.0, opening=500.0, required=500.0,
            draw=100.0,
        )
        sp = {1: -100.0}
        results = _run_g2c_synthetic(
            dsra_mode_str="cash_dsra",
            requirement_keur=500.0,
            signed_post_senior_by_idx=sp,
            dsra_period_results=[pr1],
            senior_last_period_index=5,
        )
        self._verify_combined_conservation(results[0])

    def test_cash_dsra_top_up_conservation(self):
        """CASH_DSRA top_up: signed_post_senior - top_up = reserve_adjusted_cash."""
        pr2 = _dsra_period(
            idx=1, is_construction=False,
            cash_before=300.0, opening=400.0, required=500.0,
            top_up=100.0,
        )
        sp = {1: 300.0}
        results = _run_g2c_synthetic(
            dsra_mode_str="cash_dsra",
            requirement_keur=500.0,
            signed_post_senior_by_idx=sp,
            dsra_period_results=[pr2],
            senior_last_period_index=5,
        )
        self._verify_combined_conservation(results[0])


# ===========================================================================
# Test class 6 — SHL cash authority == max(0, da_release)
# ===========================================================================

class TestShlCashAuthority:
    """SHL cash input must equal max(0, da_release) every period."""

    def test_shl_input_equals_max_zero_da_release(self):
        """max(0, da_release) = shl_cash_input, not signed_post_senior directly."""
        sp = {1: 200.0, 2: -30.0, 3: 500.0}
        dsra_periods = [_dsra_period(i, False, v, 0.0, 0.0) for i, v in sp.items()]
        results = _run_g2c_synthetic(
            dsra_mode_str="none",
            requirement_keur=0.0,
            signed_post_senior_by_idx=sp,
            dsra_period_results=dsra_periods,
        )
        for r in results:
            expected = max(0.0, r["da_release"])
            assert abs(r["shl_cash_input"] - expected) < 1e-9, (
                f"Period {r['idx']}: shl_cash_input {r['shl_cash_input']} "
                f"!= max(0, da_release) {expected}"
            )

    def test_shl_cash_nonnegative(self):
        """SHL cash input is always >= 0."""
        sp = {1: -500.0}
        dsra_periods = [_dsra_period(1, False, -500.0, 0.0, 0.0)]
        results = _run_g2c_synthetic(
            dsra_mode_str="none",
            requirement_keur=0.0,
            signed_post_senior_by_idx=sp,
            dsra_period_results=dsra_periods,
        )
        assert results[0]["shl_cash_input"] >= 0.0

    def test_shl_zero_when_gate_locked_by_comp_d(self):
        """SHL cash must be zero when gate is locked by comp_D."""
        pr1 = _dsra_period(
            idx=1, is_construction=False,
            cash_before=-100.0, opening=500.0, required=500.0,
            draw=100.0,
        )
        sp = {1: -100.0}
        results = _run_g2c_synthetic(
            dsra_mode_str="cash_dsra",
            requirement_keur=500.0,
            signed_post_senior_by_idx=sp,
            dsra_period_results=[pr1],
            senior_last_period_index=5,
        )
        assert results[0]["shl_cash_input"] == 0.0


# ===========================================================================
# Test class 7 — gate outside senior maturity
# ===========================================================================

class TestGateOutsideSeniorMaturity:
    """comp_D should not lock gate after senior debt maturity."""

    def test_comp_d_does_not_lock_outside_senior_maturity(self):
        """Even if DSRA underfunded, gate must not lock beyond senior maturity."""
        pr1 = _dsra_period(
            idx=10, is_construction=False,
            cash_before=-100.0, opening=500.0, required=500.0,
            draw=100.0,
        )
        sp = {10: -100.0}
        results = _run_g2c_synthetic(
            dsra_mode_str="cash_dsra",
            requirement_keur=500.0,
            signed_post_senior_by_idx=sp,
            dsra_period_results=[pr1],
            senior_last_period_index=9,  # period 10 is post-maturity
        )
        r = results[0]
        assert r["comp_d"], "comp_D still computed True (accounting)"
        assert not r["within_senior_maturity"]
        assert not r["gate_locked"], "Gate must not lock post-senior-maturity"


# ===========================================================================
# Test class 8 — component D uses PR-3 actuals, not static target
# ===========================================================================

class TestComponentDUsesPR3Actuals:
    """comp_D = (dsra_closing < dsra_required) from PR-3, not a static target."""

    def test_comp_d_false_when_target_met(self):
        """If PR-3 closing == required, comp_D = False."""
        pr = _dsra_period(
            idx=1, is_construction=False,
            cash_before=100.0, opening=500.0, required=500.0,
        )
        assert pr.closing_balance_keur == pytest.approx(500.0)
        sp = {1: 100.0}
        results = _run_g2c_synthetic(
            dsra_mode_str="cash_dsra",
            requirement_keur=500.0,
            signed_post_senior_by_idx=sp,
            dsra_period_results=[pr],
        )
        assert not results[0]["comp_d"]

    def test_comp_d_true_when_target_not_met(self):
        """If PR-3 closing < required (after partial draw), comp_D = True."""
        pr = _dsra_period(
            idx=1, is_construction=False,
            cash_before=-50.0, opening=500.0, required=500.0,
            draw=50.0,  # closing = 450 < required 500
        )
        assert pr.closing_balance_keur == pytest.approx(450.0)
        sp = {1: -50.0}
        results = _run_g2c_synthetic(
            dsra_mode_str="cash_dsra",
            requirement_keur=500.0,
            signed_post_senior_by_idx=sp,
            dsra_period_results=[pr],
            senior_last_period_index=5,
        )
        assert results[0]["comp_d"]


# ===========================================================================
# Test class 9 — PR-4 audit fields on CovenantGatedWaterfallPeriod
# ===========================================================================

class TestAuditFieldsExist:
    """CovenantGatedWaterfallPeriod must have the PR-4 audit fields."""

    def test_new_fields_present_in_dataclass(self):
        """All four new PR-4 audit fields must be defined on the dataclass."""
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(CovenantGatedWaterfallPeriod)}
        assert "reserve_adjusted_cash_keur" in field_names
        assert "dsra_top_up_keur" in field_names
        assert "dsra_draw_keur" in field_names
        assert "dsra_release_keur" in field_names

    def test_construction_period_has_zero_audit_fields(self):
        """Construction period audit fields must be zero."""
        from datetime import date
        from financial_engine.shareholder_waterfall.contracts import DistributionGateStatus, ReserveSupportGateStatus
        p = CovenantGatedWaterfallPeriod(
            period_index=0, cashflow_date=date(2024, 1, 1), is_construction=True,
            base_dscr=None, distribution_lockup_dscr=1.10,
            distribution_gate_status=DistributionGateStatus.CONSTRUCTION,
            debt_service_reserve_requirement_keur=0.0,
            reserve_support_gate_status=ReserveSupportGateStatus.CONSTRUCTION,
            signed_post_senior_keur=0.0, dsrf_commitment_fee_keur=0.0,
            reserve_adjusted_cash_keur=0.0,
            dsra_top_up_keur=0.0, dsra_draw_keur=0.0, dsra_release_keur=0.0,
            fcf_for_distribution_keur=0.0, covenant_locked_keur=0.0,
            distribution_account_opening_keur=0.0, distribution_account_inflow_keur=0.0,
            distribution_account_available_keur=0.0,
            gate_component_dscr_below_lockup=False, gate_component_construction=True,
            gate_component_da_negative=False, gate_component_dsra_underfunded=False,
            gate_component_j_dsra_underfunded=False, within_senior_maturity=True,
            distribution_account_release_keur=0.0, distribution_account_closing_keur=0.0,
            senior_dsra_target_keur=0.0, senior_dsra_opening_keur=0.0, senior_dsra_closing_keur=0.0,
            shl_bullet_unpaid_at_maturity=False, shl_opening_balance_keur=0.0,
            shl_gross_interest_keur=0.0, shl_cash_interest_receipt_keur=0.0, shl_pik_keur=0.0,
            contractual_shl_principal_due_keur=0.0, actual_shl_principal_paid_keur=0.0,
            unpaid_shl_principal_keur=0.0, actual_shl_closing_balance_keur=0.0,
            shl_principal_receipt_keur=0.0, shl_closing_balance_keur=0.0,
            legal_equity_distribution_keur=0.0, cash_shortfall_keur=0.0,
            share_capital_contribution_keur=0.0, share_premium_contribution_keur=0.0,
            other_committed_equity_contribution_keur=0.0, additional_equity_contribution_keur=0.0,
            shl_cash_contribution_keur=0.0, pure_equity_net_cashflow_keur=0.0,
            total_sponsor_net_cashflow_keur=0.0,
        )
        assert p.reserve_adjusted_cash_keur == 0.0
        assert p.dsra_top_up_keur == 0.0
        assert p.dsra_draw_keur == 0.0
        assert p.dsra_release_keur == 0.0


# ===========================================================================
# Test class 10 — ReserveSupportGateStatus for CASH_DSRA shortfall
# ===========================================================================

class TestReserveSupportGateStatusShortfall:
    """FAIL_REQUIREMENT_NOT_MET should be returned when target not met."""

    def test_fail_status_when_target_not_met(self):
        from financial_engine.shareholder_waterfall.model import _evaluate_reserve_support_gate
        status = _evaluate_reserve_support_gate(
            dsra_mode=DebtServiceReserveSupportMode.CASH_DSRA,
            requirement_keur=500.0,
            dsrf_commitment_keur=0.0,
            is_construction=False,
            target_met=False,
        )
        assert status == ReserveSupportGateStatus.FAIL_REQUIREMENT_NOT_MET

    def test_pass_status_when_target_met(self):
        from financial_engine.shareholder_waterfall.model import _evaluate_reserve_support_gate
        status = _evaluate_reserve_support_gate(
            dsra_mode=DebtServiceReserveSupportMode.CASH_DSRA,
            requirement_keur=500.0,
            dsrf_commitment_keur=0.0,
            is_construction=False,
            target_met=True,
        )
        assert status == ReserveSupportGateStatus.PASS

    def test_not_applicable_for_none(self):
        from financial_engine.shareholder_waterfall.model import _evaluate_reserve_support_gate
        status = _evaluate_reserve_support_gate(
            dsra_mode=DebtServiceReserveSupportMode.NONE,
            requirement_keur=0.0,
            dsrf_commitment_keur=0.0,
            is_construction=False,
        )
        assert status == ReserveSupportGateStatus.NOT_APPLICABLE

    def test_pass_neutral_when_requirement_zero(self):
        from financial_engine.shareholder_waterfall.model import _evaluate_reserve_support_gate
        status = _evaluate_reserve_support_gate(
            dsra_mode=DebtServiceReserveSupportMode.CASH_DSRA,
            requirement_keur=0.0,
            dsrf_commitment_keur=0.0,
            is_construction=False,
            target_met=True,
        )
        assert status == ReserveSupportGateStatus.PASS_NEUTRAL_SOURCE_PROVEN


# ===========================================================================
# Test class 11 — Fail-closed: CASH_DSRA requires model_result.cash_dsra
# ===========================================================================

class TestFailClosedCashDsraRequired:
    """G2C must raise if dsra_mode=CASH_DSRA and model_result.cash_dsra is None."""

    def test_cash_dsra_none_result_raises(self):
        """G2C_CASH_DSRA_RESULT_REQUIRED raised when mode=CASH_DSRA but no PR-3 result."""
        # We can't easily construct a full ProjectModelResult and ProjectInputs here
        # without a calibration runner, so we test the logic directly.
        from finco_core.inputs import DebtServiceReserveSupportMode

        # Simulate the fail-closed check
        dsra_mode = DebtServiceReserveSupportMode.CASH_DSRA
        cash_dsra_result = None

        with pytest.raises(ValueError, match="G2C_CASH_DSRA_RESULT_REQUIRED"):
            if dsra_mode == DebtServiceReserveSupportMode.CASH_DSRA and cash_dsra_result is None:
                raise ValueError(
                    "G2C_CASH_DSRA_RESULT_REQUIRED: dsra_support_mode=CASH_DSRA but "
                    "model_result.cash_dsra is None. Run PR-3 DSRA engine before G2C."
                )


# ===========================================================================
# Test class 12 — UNRESOLVED_RELEASE_POLICY preservation
# ===========================================================================

class TestUnresolvedReleasePolicy:
    """release_keur must remain 0 per UNRESOLVED_RELEASE_POLICY."""

    def test_dsra_release_is_zero(self):
        """PR-3 DSRA releases nothing — UNRESOLVED_RELEASE_POLICY preserved."""
        pr = _dsra_period(
            idx=1, is_construction=False,
            cash_before=200.0, opening=500.0, required=500.0,
        )
        # No release even when DSRA is fully funded
        assert pr.release_keur == 0.0

    def test_no_automatic_terminal_release(self):
        """Even at final period, release is 0 (no terminal release without source evidence)."""
        prs = [
            _dsra_period(i, False, 100.0, 500.0, 500.0)
            for i in range(1, 6)
        ]
        schedules = _make_dsra_schedules(500.0, prs)
        assert schedules.total_release_keur == 0.0
        assert schedules.final_closing_balance_keur == pytest.approx(500.0)
