"""PR-3 tests — Canonical CASH_DSRA roll-forward module.

Closes P1-1: DSRA_NOT_IMPLEMENTED_IN_CLEAN_ENGINE.

Governance:
- No project-name/code dispatch.
- No output fitting.
- No frozen DSRA schedules.
- Target authority: FinancingParams.debt_service_reserve_requirement_keur (static scalar).
- Release: UNRESOLVED_RELEASE_POLICY — release_keur=0, balance retained.
- COD handshake: opening at first operating period = requirement_keur.
- SHL input cash: unchanged in PR-3 (cash_available_for_shl_before_reserves_keur preserved).
- Senior debt: unchanged by DSRA (downstream of Senior DS).
"""
import pytest
from dataclasses import dataclass

from finco_core.inputs import DebtServiceReserveSupportMode
from financial_engine.dsra import CashDsraInput, CashDsraPeriodResult, CashDsraSchedules, run_cash_dsra_model
from financial_engine.results import PostSeniorCashSchedules


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _Period:
    period_index: int
    is_construction: bool


def _psc(cash_after_senior: tuple, period_indices: tuple | None = None) -> PostSeniorCashSchedules:
    n = len(cash_after_senior)
    indices = period_indices if period_indices is not None else tuple(range(n))
    return PostSeniorCashSchedules(
        period_indices=indices,
        base_cfads_keur=tuple(0.0 for _ in range(n)),
        senior_debt_service_keur=tuple(0.0 for _ in range(n)),
        cash_after_senior_before_reserves_keur=cash_after_senior,
        cash_available_for_shl_before_reserves_keur=tuple(max(0.0, c) for c in cash_after_senior),
    )


def _periods(*pairs) -> tuple:
    return tuple(_Period(idx, is_constr) for idx, is_constr in pairs)


# ---------------------------------------------------------------------------
# 1. NONE — neutral pass-through
# ---------------------------------------------------------------------------

class TestNoneMode:
    def test_none_mode_all_movements_zero(self):
        periods = _periods((0, True), (1, False), (2, False))
        psc = _psc((100.0, 300.0, -50.0))
        result = run_cash_dsra_model(psc, CashDsraInput(mode=DebtServiceReserveSupportMode.NONE), periods)
        assert result.mode == "none"
        assert result.total_top_up_keur == 0.0
        assert result.total_draw_keur == 0.0
        assert result.total_release_keur == 0.0
        for pr in result.period_results:
            assert pr.top_up_keur == 0.0
            assert pr.draw_to_cover_shortfall_keur == 0.0
            assert pr.release_keur == 0.0
            assert pr.opening_balance_keur == 0.0
            assert pr.closing_balance_keur == 0.0
            assert pr.target_met is True

    def test_none_mode_cash_pass_through(self):
        periods = _periods((0, True), (1, False), (2, False))
        psc = _psc((100.0, 300.0, -50.0))
        result = run_cash_dsra_model(psc, CashDsraInput(mode=DebtServiceReserveSupportMode.NONE), periods)
        for pr, expected in zip(result.period_results, (100.0, 300.0, -50.0)):
            assert pr.cash_after_dsra_keur == pr.cash_before_dsra_keur == expected

    def test_none_mode_none_input_treated_as_none(self):
        periods = _periods((0, True), (1, False))
        psc = _psc((0.0, 200.0))
        result = run_cash_dsra_model(psc, None, periods)
        assert result.mode == "none"
        assert all(pr.cash_after_dsra_keur == pr.cash_before_dsra_keur for pr in result.period_results)

    def test_none_mode_diagnostic(self):
        periods = _periods((0, False),)
        psc = _psc((100.0,))
        result = run_cash_dsra_model(psc, CashDsraInput(mode=DebtServiceReserveSupportMode.NONE), periods)
        assert any("NONE" in d for d in result.diagnostics)


# ---------------------------------------------------------------------------
# 2. NONE + positive requirement — fail closed
# ---------------------------------------------------------------------------

class TestNoneModeValidation:
    def test_none_positive_requirement_raises(self):
        periods = _periods((0, False),)
        psc = _psc((500.0,))
        with pytest.raises(ValueError, match="CASH_DSRA_NONE_MODE_WITH_POSITIVE_REQUIREMENT"):
            run_cash_dsra_model(
                psc,
                CashDsraInput(mode=DebtServiceReserveSupportMode.NONE, requirement_keur=100.0),
                periods,
            )

    def test_none_zero_requirement_ok(self):
        periods = _periods((0, False),)
        psc = _psc((500.0,))
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.NONE, requirement_keur=0.0), periods
        )
        assert result.mode == "none"


# ---------------------------------------------------------------------------
# 3. CASH_DSRA — COD funding / opening handshake
# ---------------------------------------------------------------------------

class TestCashDsraCodHandshake:
    def test_first_operating_period_opening_equals_requirement(self):
        req = 500.0
        periods = _periods((0, True), (1, False), (2, False))
        psc = _psc((0.0, 1000.0, 800.0))
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.CASH_DSRA, requirement_keur=req), periods
        )
        first_op = result.period_results[1]
        assert first_op.opening_balance_keur == req

    def test_construction_periods_opening_zero(self):
        req = 500.0
        periods = _periods((0, True), (1, True), (2, False))
        psc = _psc((0.0, 0.0, 600.0))
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.CASH_DSRA, requirement_keur=req), periods
        )
        for pr in result.period_results[:2]:
            assert pr.is_construction is True
            assert pr.opening_balance_keur == 0.0
            assert pr.closing_balance_keur == 0.0
            assert pr.top_up_keur == 0.0

    def test_cod_handshake_diagnostic_present(self):
        req = 300.0
        periods = _periods((0, True), (1, False))
        psc = _psc((0.0, 500.0))
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.CASH_DSRA, requirement_keur=req), periods
        )
        assert any("COD_FUNDING_HANDSHAKE" in d for d in result.diagnostics)
        assert any(str(int(req)) in d for d in result.diagnostics)


# ---------------------------------------------------------------------------
# 4. CASH_DSRA — top-up
# ---------------------------------------------------------------------------

class TestCashDsraTopUp:
    def test_top_up_when_below_target_and_positive_cash(self):
        req = 500.0
        # Opening will be req=500 (COD). Cash is 1000 — but opening==target, no top-up needed.
        # Use a scenario where opening falls below target due to a draw in prior period.
        # Simulate: period 1 = COD (opening=500=target, cash=300→no movement)
        #           period 2 = cash=-100→draw=100, closing=400
        #           period 3 = cash=200→top_up=min(500-400, 200)=100
        periods = _periods((0, True), (1, False), (2, False), (3, False))
        psc = _psc((0.0, 300.0, -100.0, 200.0))
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.CASH_DSRA, requirement_keur=req), periods
        )
        p3 = result.period_results[3]
        assert p3.top_up_keur == 100.0
        assert p3.cash_after_dsra_keur == 200.0 - 100.0

    def test_top_up_capped_at_available_cash(self):
        req = 500.0
        # After a draw, opening=400, target=500, cash_before=50
        # top_up = min(500-400, 50) = 50
        periods = _periods((0, True), (1, False), (2, False), (3, False))
        psc = _psc((0.0, 300.0, -100.0, 50.0))
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.CASH_DSRA, requirement_keur=req), periods
        )
        p3 = result.period_results[3]
        assert p3.top_up_keur == 50.0
        assert p3.cash_after_dsra_keur == 0.0


# ---------------------------------------------------------------------------
# 5. CASH_DSRA — fully funded neutral period
# ---------------------------------------------------------------------------

class TestCashDsraFullyFunded:
    def test_no_top_up_when_at_target(self):
        req = 500.0
        periods = _periods((0, True), (1, False), (2, False))
        psc = _psc((0.0, 800.0, 600.0))
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.CASH_DSRA, requirement_keur=req), periods
        )
        # Period 1: opening=500=target → top_up=0; closing=500
        p1 = result.period_results[1]
        assert p1.top_up_keur == 0.0
        assert p1.closing_balance_keur == 500.0
        assert p1.cash_after_dsra_keur == 800.0
        # Period 2: opening=500=target → top_up=0
        p2 = result.period_results[2]
        assert p2.top_up_keur == 0.0
        assert p2.cash_after_dsra_keur == 600.0


# ---------------------------------------------------------------------------
# 6. CASH_DSRA — draw / shortfall
# ---------------------------------------------------------------------------

class TestCashDsraDraw:
    def test_draw_when_negative_cash(self):
        req = 500.0
        periods = _periods((0, True), (1, False))
        psc = _psc((0.0, -100.0))
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.CASH_DSRA, requirement_keur=req), periods
        )
        p1 = result.period_results[1]
        assert p1.draw_to_cover_shortfall_keur == 100.0
        assert p1.top_up_keur == 0.0
        assert p1.closing_balance_keur == 400.0
        assert p1.cash_after_dsra_keur == 0.0

    def test_draw_capped_at_opening_balance(self):
        req = 500.0
        periods = _periods((0, True), (1, False))
        psc = _psc((0.0, -700.0))  # more negative than opening
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.CASH_DSRA, requirement_keur=req), periods
        )
        p1 = result.period_results[1]
        # draw capped at opening=500
        assert p1.draw_to_cover_shortfall_keur == 500.0
        assert p1.closing_balance_keur == 0.0
        # cash_after = -700 + 500 = -200 (still negative — reserve exhausted)
        assert abs(p1.cash_after_dsra_keur - (-200.0)) < 1e-9

    def test_no_draw_when_reserve_empty(self):
        req = 0.0
        periods = _periods((0, True), (1, False))
        psc = _psc((0.0, -200.0))
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.CASH_DSRA, requirement_keur=req), periods
        )
        p1 = result.period_results[1]
        assert p1.draw_to_cover_shortfall_keur == 0.0
        assert p1.cash_after_dsra_keur == -200.0


# ---------------------------------------------------------------------------
# 7. Release semantics — UNRESOLVED_RELEASE_POLICY
# ---------------------------------------------------------------------------

class TestReleasePolicy:
    def test_release_always_zero(self):
        req = 500.0
        periods = _periods((0, True), (1, False), (2, False), (3, False))
        psc = _psc((0.0, 500.0, 500.0, 500.0))
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.CASH_DSRA, requirement_keur=req), periods
        )
        assert result.total_release_keur == 0.0
        for pr in result.period_results:
            assert pr.release_keur == 0.0

    def test_unresolved_release_diagnostic(self):
        req = 500.0
        periods = _periods((0, False),)
        psc = _psc((200.0,))
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.CASH_DSRA, requirement_keur=req), periods
        )
        assert any("UNRESOLVED_RELEASE_POLICY" in d for d in result.diagnostics)


# ---------------------------------------------------------------------------
# 8. Insufficient reserve
# ---------------------------------------------------------------------------

class TestInsufficientReserve:
    def test_shortfall_exposed_when_balance_below_target(self):
        req = 500.0
        periods = _periods((0, True), (1, False))
        psc = _psc((0.0, -700.0))  # draws more than reserve
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.CASH_DSRA, requirement_keur=req), periods
        )
        p1 = result.period_results[1]
        assert p1.shortfall_keur > 0.0
        assert p1.target_met is False


# ---------------------------------------------------------------------------
# 9. Cash conservation
# ---------------------------------------------------------------------------

class TestCashConservation:
    def test_cash_conservation_all_periods(self):
        req = 400.0
        periods = _periods((0, True), (1, False), (2, False), (3, False))
        psc = _psc((0.0, 600.0, -150.0, 300.0))
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.CASH_DSRA, requirement_keur=req), periods
        )
        for pr in result.period_results:
            lhs = pr.cash_before_dsra_keur - pr.top_up_keur + pr.draw_to_cover_shortfall_keur + pr.release_keur
            assert abs(lhs - pr.cash_after_dsra_keur) < 1e-9, (
                f"Cash conservation violated at period {pr.period_index}: "
                f"{lhs} != {pr.cash_after_dsra_keur}"
            )


# ---------------------------------------------------------------------------
# 10. Balance conservation
# ---------------------------------------------------------------------------

class TestBalanceConservation:
    def test_balance_conservation_all_periods(self):
        req = 400.0
        periods = _periods((0, True), (1, False), (2, False), (3, False))
        psc = _psc((0.0, 600.0, -150.0, 300.0))
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.CASH_DSRA, requirement_keur=req), periods
        )
        for pr in result.period_results:
            lhs = pr.opening_balance_keur + pr.top_up_keur - pr.draw_to_cover_shortfall_keur - pr.release_keur
            assert abs(lhs - pr.closing_balance_keur) < 1e-9, (
                f"Balance conservation violated at period {pr.period_index}: "
                f"{lhs} != {pr.closing_balance_keur}"
            )

    def test_consecutive_opening_equals_prior_closing(self):
        req = 300.0
        periods = _periods((0, True), (1, False), (2, False), (3, False))
        psc = _psc((0.0, 500.0, -50.0, 200.0))
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.CASH_DSRA, requirement_keur=req), periods
        )
        op_periods = [pr for pr in result.period_results if not pr.is_construction]
        for i in range(1, len(op_periods)):
            assert abs(op_periods[i].opening_balance_keur - op_periods[i - 1].closing_balance_keur) < 1e-9


# ---------------------------------------------------------------------------
# 11. Negative signed post-Senior cash
# ---------------------------------------------------------------------------

class TestNegativeCash:
    def test_negative_cash_with_empty_reserve(self):
        req = 0.0
        periods = _periods((0, False),)
        psc = _psc((-300.0,))
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.CASH_DSRA, requirement_keur=req), periods
        )
        pr = result.period_results[0]
        assert pr.cash_after_dsra_keur == -300.0
        assert pr.draw_to_cover_shortfall_keur == 0.0

    def test_negative_cash_partially_covered_by_reserve(self):
        req = 200.0
        periods = _periods((0, True), (1, False))
        psc = _psc((0.0, -150.0))
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.CASH_DSRA, requirement_keur=req), periods
        )
        pr = result.period_results[1]
        assert pr.draw_to_cover_shortfall_keur == 150.0
        assert pr.cash_after_dsra_keur == 0.0
        assert pr.closing_balance_keur == 50.0


# ---------------------------------------------------------------------------
# 12. Construction periods
# ---------------------------------------------------------------------------

class TestConstructionPeriods:
    def test_construction_periods_all_zero_movements(self):
        req = 500.0
        periods = _periods((0, True), (1, True), (2, False))
        psc = _psc((100.0, 200.0, 300.0))
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.CASH_DSRA, requirement_keur=req), periods
        )
        for pr in result.period_results[:2]:
            assert pr.top_up_keur == 0.0
            assert pr.draw_to_cover_shortfall_keur == 0.0
            assert pr.closing_balance_keur == 0.0
            assert pr.cash_after_dsra_keur == pr.cash_before_dsra_keur

    def test_first_operating_period_opening_after_construction(self):
        req = 500.0
        periods = _periods((0, True), (1, True), (2, False))
        psc = _psc((0.0, 0.0, 800.0))
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.CASH_DSRA, requirement_keur=req), periods
        )
        op = result.period_results[2]
        assert op.opening_balance_keur == req


# ---------------------------------------------------------------------------
# 13. No project identity dispatch
# ---------------------------------------------------------------------------

class TestNoProjectIdentityDispatch:
    def test_same_typed_inputs_same_result_regardless_of_caller(self):
        """Two callers with identical CashDsraInput + PostSeniorCashSchedules → identical result."""
        req = 300.0
        periods = _periods((0, True), (1, False), (2, False))
        psc = _psc((0.0, 400.0, 200.0))
        dsra_input = CashDsraInput(mode=DebtServiceReserveSupportMode.CASH_DSRA, requirement_keur=req)
        r1 = run_cash_dsra_model(psc, dsra_input, periods)
        r2 = run_cash_dsra_model(psc, dsra_input, periods)
        assert r1 == r2

    def test_renamed_project_same_result(self):
        """Project name does not enter CashDsraInput; result is identical."""
        req = 400.0
        periods = _periods((0, True), (1, False))
        psc = _psc((0.0, 600.0))
        dsra_input = CashDsraInput(mode=DebtServiceReserveSupportMode.CASH_DSRA, requirement_keur=req)
        # Run twice — name is nowhere in the input
        r_alpha = run_cash_dsra_model(psc, dsra_input, periods)
        r_beta = run_cash_dsra_model(psc, dsra_input, periods)
        for pa, pb in zip(r_alpha.period_results, r_beta.period_results):
            assert pa.cash_after_dsra_keur == pb.cash_after_dsra_keur
            assert pa.closing_balance_keur == pb.closing_balance_keur


# ---------------------------------------------------------------------------
# 14. DSRF mode — pass-through (no draw engine)
# ---------------------------------------------------------------------------

class TestDsrfMode:
    def test_dsrf_neutral_pass_through(self):
        periods = _periods((0, True), (1, False), (2, False))
        psc = _psc((0.0, 300.0, -100.0))
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.DSRF, requirement_keur=0.0), periods
        )
        assert result.mode == "dsrf"
        assert result.total_top_up_keur == 0.0
        assert result.total_draw_keur == 0.0
        for pr in result.period_results:
            assert pr.cash_after_dsra_keur == pr.cash_before_dsra_keur
            assert pr.draw_to_cover_shortfall_keur == 0.0

    def test_dsrf_diagnostic_present(self):
        periods = _periods((0, False),)
        psc = _psc((200.0,))
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.DSRF, requirement_keur=0.0), periods
        )
        assert any("DSRF" in d for d in result.diagnostics)
        assert any("no DSRA draw engine" in d.lower() or "NOT_APPLICABLE" in d for d in result.diagnostics)


# ---------------------------------------------------------------------------
# 15. Clean runtime instrumentation — orchestrator wires DSRA
# ---------------------------------------------------------------------------

def _make_clean_senior_debt_inputs():
    """Build a SeniorDebtModelInput via the adapter from the default solar factory."""
    from app.project_factories import create_default_solar_project
    from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
    project = create_default_solar_project()
    return build_senior_debt_model_input_from_project_inputs(project)


class TestCleanRuntimeInstrumentation:
    def test_project_model_result_has_cash_dsra_field(self):
        """ProjectModelResult carries cash_dsra field after PR-3."""
        from financial_engine.results import ProjectModelResult
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(ProjectModelResult)}
        assert "cash_dsra" in field_names

    def test_run_senior_debt_model_populates_cash_dsra(self):
        """Adapter-built SeniorDebtModelInput produces result.cash_dsra (NONE neutral)."""
        from financial_engine.orchestrator import run_senior_debt_model
        inputs = _make_clean_senior_debt_inputs()
        result = run_senior_debt_model(inputs)
        assert result.cash_dsra is not None
        assert result.cash_dsra.mode == "none"

    def test_none_dsra_does_not_change_senior_debt(self):
        """NONE dsra leaves all Senior debt schedules unchanged vs no dsra supplied."""
        from financial_engine.orchestrator import run_senior_debt_model
        from financial_engine.dsra.contracts import CashDsraInput
        from dataclasses import replace
        inputs = _make_clean_senior_debt_inputs()
        result_no_dsra = run_senior_debt_model(replace(inputs, dsra=None))
        result_with_none = run_senior_debt_model(
            replace(inputs, dsra=CashDsraInput(mode=DebtServiceReserveSupportMode.NONE))
        )
        assert result_no_dsra.senior_debt.debt_size_keur == result_with_none.senior_debt.debt_size_keur
        assert (
            result_no_dsra.post_senior_cash.cash_after_senior_before_reserves_keur
            == result_with_none.post_senior_cash.cash_after_senior_before_reserves_keur
        )

    def test_none_dsra_does_not_change_shl_input_cash(self):
        """NONE dsra leaves cash_available_for_shl_before_reserves_keur unchanged."""
        from financial_engine.orchestrator import run_senior_debt_model
        from financial_engine.dsra.contracts import CashDsraInput
        from dataclasses import replace
        inputs = _make_clean_senior_debt_inputs()
        result_no_dsra = run_senior_debt_model(replace(inputs, dsra=None))
        result_with_none = run_senior_debt_model(
            replace(inputs, dsra=CashDsraInput(mode=DebtServiceReserveSupportMode.NONE))
        )
        assert (
            result_no_dsra.post_senior_cash.cash_available_for_shl_before_reserves_keur
            == result_with_none.post_senior_cash.cash_available_for_shl_before_reserves_keur
        )


# ---------------------------------------------------------------------------
# 16. TUHO / Oborovo / KUPI classification (neutral by typed input)
# ---------------------------------------------------------------------------

class TestCalibrationProjectClassification:
    """All calibration projects have requirement_keur=0 → CASH_DSRA_NEUTRAL_BY_TYPED_INPUT."""

    def _run_project_dsra(self, project_name_label: str, requirement: float):
        """Typed inputs only — no project-name dispatch."""
        req = requirement
        periods = _periods((0, True), (1, False), (2, False))
        psc = _psc((0.0, 500.0, 400.0))
        dsra_input = CashDsraInput(
            mode=DebtServiceReserveSupportMode.CASH_DSRA if req > 0 else DebtServiceReserveSupportMode.NONE,
            requirement_keur=req,
        )
        return run_cash_dsra_model(psc, dsra_input, periods)

    def test_tuho_neutral(self):
        result = self._run_project_dsra("TUHO", requirement=0.0)
        assert result.mode == "none"
        assert result.total_top_up_keur == 0.0
        assert all(pr.cash_after_dsra_keur == pr.cash_before_dsra_keur for pr in result.period_results)

    def test_oborovo_neutral(self):
        result = self._run_project_dsra("OBOROVO", requirement=0.0)
        assert result.mode == "none"
        assert result.total_top_up_keur == 0.0

    def test_kupi_neutral(self):
        result = self._run_project_dsra("KUPI", requirement=0.0)
        assert result.mode == "none"
        assert result.total_top_up_keur == 0.0

    def test_neutral_classification_label(self):
        """CASH_DSRA_NEUTRAL_BY_TYPED_INPUT: requirement=0 → NONE mode."""
        result = self._run_project_dsra("any", requirement=0.0)
        assert result.requirement_keur == 0.0
        assert result.total_top_up_keur == 0.0
        assert result.total_draw_keur == 0.0


# ---------------------------------------------------------------------------
# 17. Aggregate totals
# ---------------------------------------------------------------------------

class TestAggregateTotals:
    def test_total_top_up_sum(self):
        req = 500.0
        # Period 1: opening=500, target=500, no top-up
        # Period 2: cash=-200 → draw=200, closing=300
        # Period 3: cash=100 → top-up=min(200, 100)=100, closing=400
        # Period 4: cash=200 → top-up=min(100, 200)=100, closing=500
        periods = _periods((0, True), (1, False), (2, False), (3, False), (4, False))
        psc = _psc((0.0, 600.0, -200.0, 100.0, 200.0))
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.CASH_DSRA, requirement_keur=req), periods
        )
        expected_top_up = sum(pr.top_up_keur for pr in result.period_results)
        assert abs(result.total_top_up_keur - expected_top_up) < 1e-9

    def test_total_draw_sum(self):
        req = 500.0
        periods = _periods((0, True), (1, False), (2, False), (3, False))
        psc = _psc((0.0, 600.0, -100.0, -150.0))
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.CASH_DSRA, requirement_keur=req), periods
        )
        expected_draw = sum(pr.draw_to_cover_shortfall_keur for pr in result.period_results)
        assert abs(result.total_draw_keur - expected_draw) < 1e-9

    def test_final_closing_matches_last_period(self):
        req = 300.0
        periods = _periods((0, True), (1, False), (2, False))
        psc = _psc((0.0, 400.0, -50.0))
        result = run_cash_dsra_model(
            psc, CashDsraInput(mode=DebtServiceReserveSupportMode.CASH_DSRA, requirement_keur=req), periods
        )
        assert result.final_closing_balance_keur == result.period_results[-1].closing_balance_keur
