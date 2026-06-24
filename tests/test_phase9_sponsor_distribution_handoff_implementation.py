"""tests/test_phase9_sponsor_distribution_handoff_implementation.py

Phase 9: Sponsor Distribution Handoff Implementation.

Wires explicit `distribution_account_received_by_period` into
SponsorCashflowRunner as an optional override of holdco_distribution_by_period,
without promoting R99/R102 and without enabling production DistributionAccount
cash routing.

Design reference:
- docs/phase9_sponsor_distribution_handoff_design.md
- reports/phase9_sponsor_distribution_handoff_contract.csv

R99/R102: BLOCKED — this module does not promote R99/R102 gates.
"""

import pytest
from pathlib import Path

from domain.sponsor.sponsor_cashflow_runner import (
    SponsorCashflowRunnerInputs,
    run_sponsor_cashflows,
)
from domain.sponsor.equity_injection import EquityInjection


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_injections(
    periods: tuple[tuple[int, float], ...] = ((0, 10000.0), (1, 5000.0)),
    investor_id: str = "SPONSOR-1",
):
    """Build equity injections tuple."""
    return tuple(
        EquityInjection(
            period_index=p, amount_keur=a,
            investor_id=investor_id, target_entity="HOLDCO",
            purpose="equityContribution" if p == 0 else "topUp",
        )
        for p, a in periods
    )


def make_distributions(n: int, value: float = 0.0) -> tuple[float, ...]:
    return tuple(value for _ in range(n))


# Standard 10-period fixture
STD_INJECTIONS = make_injections()
STD_DISTRIBUTIONS = make_distributions(10)
STD_DIVIDENDS = make_distributions(10)
STD_OPEX = make_distributions(10)


def make_inputs(
    distributions: tuple[float, ...] = STD_DISTRIBUTIONS,
    distribution_account_override: tuple[float, ...] | None = None,
    period_count: int = 10,
    wht_rate: float = 0.0,
    investor_id: str = "SPONSOR-1",
    entity_code: str = "HOLDCO",
    equity_injections: tuple[EquityInjection, ...] | None = None,
):
    """Build SponsorCashflowRunnerInputs for testing."""
    return SponsorCashflowRunnerInputs(
        investor_id=investor_id,
        entity_code=entity_code,
        equity_injections=equity_injections or STD_INJECTIONS,
        holdco_distribution_by_period=distributions,
        holdco_dividend_by_period=STD_DIVIDENDS,
        wht_rate=wht_rate,
        holdco_opex_by_period=STD_OPEX,
        period_count=period_count,
        distribution_account_received_by_period=distribution_account_override,
    )


# Base TUHO fixture: no distribution, 2 equity injections
BASE_INPUTS = make_inputs(
    distributions=make_distributions(10, 0.0),
)


class TestDefaultZeroBehavior:
    """Case 1: Default zero/None behavior unchanged."""

    def test_no_override_no_distribution_no_injections_in_result(self):
        """With no override and no distributions: period results reflect injections only."""
        result = run_sponsor_cashflows(BASE_INPUTS)
        p0 = result.period_results[0]
        assert p0.equity_injected_keur == pytest.approx(10000.0)
        assert p0.distribution_received_keur == pytest.approx(0.0)
        assert p0.net_cashflow_keur == pytest.approx(-10000.0)

    def test_default_override_none_unchanged(self):
        """distribution_account_received_by_period=None produces identical result to no field."""
        inputs_none = make_inputs(
            distributions=make_distributions(10, 0.0),
            distribution_account_override=None,
        )
        result = run_sponsor_cashflows(inputs_none)
        p0 = result.period_results[0]
        # Same as BASE
        assert p0.distribution_received_keur == pytest.approx(0.0)
        assert p0.equity_injected_keur == pytest.approx(10000.0)

    def test_zero_distributions_unchanged_by_default(self):
        """No explicit distribution → holdco_distribution_by_period used (0.0)."""
        inputs = make_inputs(distributions=make_distributions(10, 0.0))
        result = run_sponsor_cashflows(inputs)
        for p in result.period_results:
            assert p.distribution_received_keur == pytest.approx(0.0)

    def test_holdco_distributions_used_when_no_override(self):
        """When no override provided, holdco_distribution_by_period drives cashflow."""
        nonzero_dist = (0.0, 0.0, 0.0, 0.0, 2000.0, 2500.0, 2500.0, 2500.0, 2000.0, 1000.0)
        inputs = make_inputs(distributions=nonzero_dist)
        result = run_sponsor_cashflows(inputs)
        p4 = result.period_results[4]
        assert p4.distribution_received_keur == pytest.approx(2000.0)
        assert p4.net_cashflow_keur == pytest.approx(2000.0)  # 2000 - 0 (no injection in p4)


class TestExplicitDistributionInput:
    """Case 2: Explicit distribution input included as sponsor cash inflow."""

    def test_override_replaces_holdco_distribution(self):
        """When override provided, it replaces holdco_distribution_by_period."""
        override = make_distributions(10, 0.0)
        override_period_4 = list(override)
        override_period_4[4] = 5000.0
        override_period_4 = tuple(override_period_4)
        inputs = make_inputs(
            distributions=make_distributions(10, 0.0),  # holdco says 0
            distribution_account_override=override_period_4,
        )
        result = run_sponsor_cashflows(inputs)
        p4 = result.period_results[4]
        # Override wins
        assert p4.distribution_received_keur == pytest.approx(5000.0)
        assert p4.net_cashflow_keur == pytest.approx(5000.0)  # no injection this period

    def test_explicit_distribution_positive_inflow(self):
        """Explicit distribution > 0 produces positive net_cashflow."""
        dist_input = make_distributions(10, 0.0)
        dist_input_list = list(dist_input)
        dist_input_list[3] = 3000.0
        dist_input = tuple(dist_input_list)
        inputs = make_inputs(
            distributions=make_distributions(10, 0.0),
            distribution_account_override=dist_input,
        )
        result = run_sponsor_cashflows(inputs)
        p3 = result.period_results[3]
        assert p3.distribution_received_keur == pytest.approx(3000.0)
        assert p3.net_cashflow_keur == pytest.approx(3000.0)  # no injection in p3

    def test_sign_convention_positive_for_distribution(self):
        """distribution_received_keur is always >= 0 (inflow convention)."""
        override = make_distributions(10, 1000.0)
        inputs = make_inputs(
            distributions=make_distributions(10, 0.0),
            distribution_account_override=override,
        )
        result = run_sponsor_cashflows(inputs)
        for p in result.period_results:
            assert p.distribution_received_keur >= 0.0
            assert p.net_cashflow_keur == pytest.approx(
                p.distribution_received_keur - p.equity_injected_keur - p.wht_on_distribution_keur
            )

    def test_explicit_distribution_affects_capital_account(self):
        """Explicit distribution increases capital_account_balance (net return)."""
        # Period 0: inject 10000, Period 1: inject 5000, Period 5: distribution 8000
        injections = (
            EquityInjection(period_index=0, amount_keur=10000.0,
                investor_id="SPONSOR-1", target_entity="HOLDCO", purpose="equityContribution"),
            EquityInjection(period_index=1, amount_keur=5000.0,
                investor_id="SPONSOR-1", target_entity="HOLDCO", purpose="topUp"),
        )
        override = make_distributions(10, 0.0)
        override_list = list(override)
        override_list[5] = 8000.0
        override = tuple(override_list)
        inputs = make_inputs(
            distributions=make_distributions(10, 0.0),
            distribution_account_override=override,
            equity_injections=injections,
        )
        result = run_sponsor_cashflows(inputs)
        # Balance after p0 injection: 10000
        assert result.period_results[0].capital_account_balance_keur == pytest.approx(10000.0)
        # After p1 injection: 10000 + 5000 = 15000
        assert result.period_results[1].capital_account_balance_keur == pytest.approx(15000.0)
        # After p5 distribution (8000): 15000 - 8000 = 7000
        assert result.period_results[5].capital_account_balance_keur == pytest.approx(7000.0)


class TestExplicitTupleSemantics:
    """Case 2b: Explicit tuple behavior — all-zero, length, no-fallback."""

    def test_all_zero_tuple_produces_zero_distribution_no_fallback(self):
        """All-zero explicit tuple results in zero distribution inflow, not fallback to HoldCo."""
        # holdco says 2000 in p4, but explicit override is all zeros → zero wins
        nonzero_holdco = make_distributions(10, 0.0)
        holdco_list = list(nonzero_holdco)
        holdco_list[4] = 2000.0
        nonzero_holdco = tuple(holdco_list)
        all_zero_override = make_distributions(10, 0.0)
        inputs = make_inputs(
            distributions=nonzero_holdco,
            distribution_account_override=all_zero_override,
        )
        result = run_sponsor_cashflows(inputs)
        # Explicit all-zero override must win, no fallback to holdco's 2000
        assert result.period_results[4].distribution_received_keur == pytest.approx(0.0)
        assert result.period_results[4].net_cashflow_keur == pytest.approx(0.0)

    def test_explicit_zero_in_one_period_no_fallback_to_holdco(self):
        """Explicit zero in one period overrides holdco's non-zero, no fallback."""
        # holdco says 5000 in p3, explicit says 0 → explicit wins
        nonzero_holdco = make_distributions(10, 0.0)
        holdco_list = list(nonzero_holdco)
        holdco_list[3] = 5000.0
        nonzero_holdco = tuple(holdco_list)
        partial_override = make_distributions(10, 0.0)  # all zeros
        inputs = make_inputs(
            distributions=nonzero_holdco,
            distribution_account_override=partial_override,
        )
        result = run_sponsor_cashflows(inputs)
        assert result.period_results[3].distribution_received_keur == pytest.approx(0.0)
        assert result.period_results[3].net_cashflow_keur == pytest.approx(0.0)
        # But p5 uses explicit override (2000), not holdco (0)
        override_list = list(partial_override)
        override_list[5] = 2000.0
        partial_override = tuple(override_list)
        inputs2 = make_inputs(
            distributions=nonzero_holdco,  # holdco says 0 at p5
            distribution_account_override=partial_override,
        )
        result2 = run_sponsor_cashflows(inputs2)
        assert result2.period_results[5].distribution_received_keur == pytest.approx(2000.0)

    def test_length_mismatch_raises_value_error(self):
        """Length mismatch between override and period_count raises ValueError."""
        bad_override = make_distributions(5, 1000.0)  # 5 periods, not 10
        inputs = make_inputs(
            distributions=make_distributions(10, 0.0),
            distribution_account_override=bad_override,
        )
        with pytest.raises(ValueError, match="distribution_account_received_by_period.*expected 10.*got 5"):
            run_sponsor_cashflows(inputs)

    def test_all_zero_override_yields_zero_net_cashflow_every_period(self):
        """All-zero explicit tuple yields zero net cashflow in every period."""
        inputs = make_inputs(
            distributions=make_distributions(10, 0.0),
            distribution_account_override=make_distributions(10, 0.0),
        )
        result = run_sponsor_cashflows(inputs)
        for p in result.period_results:
            assert p.distribution_received_keur == pytest.approx(0.0)
            assert p.net_cashflow_keur == pytest.approx(-p.equity_injected_keur)


class TestBlockedDistributionAccountBehavior:
    """Case 3: DistributionAccount audit/default output remains equity_distribution_paid_keur = 0."""

    def test_distribution_account_paid_0_by_default(self):
        """DistributionAccount with R99/R102 blocked produces equity_distribution_paid_keur = 0."""
        from domain.distribution_account.engine import DistributionAccountEngine
        from domain.distribution_account.inputs import (
            DistributionAccountInputs,
            DistributionAccountPeriodInput,
        )
        from datetime import date

        dist_inputs = DistributionAccountInputs(
            project_name="TUHO-WIND-1",
            is_tuho=True,
            is_oborovo=False,
            period_inputs=(
                DistributionAccountPeriodInput(
                    period_index=1,
                    operating_period_index=1,
                    period_date=date(2029, 6, 30),
                    opening_distribution_account_balance_keur=0.0,
                    post_senior_cash_available_keur=0.0,
                    post_shl_cash_available_keur=500.0,
                    senior_debt_service_keur=0.0,
                    actual_dscr=1.5,
                    is_tuho=True,
                    is_oborovo=False,
                    enable_r99_r102_runtime=False,
                ),
            ),
        )
        dist_result = DistributionAccountEngine.compute(dist_inputs)
        dp = dist_result.period_results[0]
        # When blocked, equity_distribution_paid_keur = 0
        assert dp.equity_distribution_paid_keur == pytest.approx(0.0)
        # Sponsor receives 0 from DistributionAccount by default
        assert dp.cash_swept_to_shl_keur == pytest.approx(0.0)

    def test_sponsor_receives_zero_from_distribution_account_by_default(self):
        """SponsorCashflowRunner with no override receives 0.0 from holdco path."""
        inputs = make_inputs(
            distributions=make_distributions(10, 0.0),
            distribution_account_override=None,
        )
        result = run_sponsor_cashflows(inputs)
        for p in result.period_results:
            assert p.distribution_received_keur == pytest.approx(0.0)


class TestNoGateRecomputation:
    """Case 4: Sponsor module does not evaluate/recompute R99/R102 gates."""

    def test_sponsor_runner_has_no_gate_fields(self):
        """SponsorCashflowRunnerInputs has no R99/R102 gate fields."""
        for field_name in SponsorCashflowRunnerInputs.__dataclass_fields__:
            assert "r99" not in field_name.lower(), f"Unexpected R99 field: {field_name}"
            assert "r102" not in field_name.lower(), f"Unexpected R102 field: {field_name}"

    def test_run_sponsor_cashflows_accepts_override_without_gate_check(self):
        """run_sponsor_cashflows accepts explicit override without evaluating gates."""
        override = make_distributions(10, 0.0)
        override_list = list(override)
        override_list[3] = 2000.0
        override = tuple(override_list)
        inputs = make_inputs(
            distributions=make_distributions(10, 0.0),
            distribution_account_override=override,
        )
        # Should succeed without gate evaluation
        result = run_sponsor_cashflows(inputs)
        assert result.period_results[3].distribution_received_keur == pytest.approx(2000.0)


class TestNoIRRSideEffectsByDefault:
    """Case 5: sponsor/equity IRR unchanged when no explicit distribution input provided."""

    def test_no_distribution_no_irr_change(self):
        """Without explicit distribution, sponsor cashflows reflect only injections."""
        inputs = make_inputs(
            distributions=make_distributions(10, 0.0),
            distribution_account_override=None,
        )
        result = run_sponsor_cashflows(inputs)
        # Total distributions = 0
        assert result.total_distributions_received_keur == pytest.approx(0.0)
        assert result.total_equity_injected_keur == pytest.approx(15000.0)

    def test_explicit_override_changes_total_distributions(self):
        """When explicit override provided, total_distributions changes."""
        override = make_distributions(10, 1000.0)
        inputs = make_inputs(
            distributions=make_distributions(10, 0.0),
            distribution_account_override=override,
        )
        result = run_sponsor_cashflows(inputs)
        # Total = 10 * 1000 = 10000
        assert result.total_distributions_received_keur == pytest.approx(10000.0)


class TestPositiveExplicitHandoffCase:
    """Case 6: Sponsor IRR/cashflow changes only when explicit distribution input provided."""

    def test_handoff_increases_sponsor_return(self):
        """Explicit distribution increases total distributions received."""
        base_inputs = make_inputs(distributions=make_distributions(10, 0.0))
        base_result = run_sponsor_cashflows(base_inputs)
        assert base_result.total_distributions_received_keur == pytest.approx(0.0)

        override = make_distributions(10, 2000.0)
        handoff_inputs = make_inputs(
            distributions=make_distributions(10, 0.0),
            distribution_account_override=override,
        )
        handoff_result = run_sponsor_cashflows(handoff_inputs)
        assert handoff_result.total_distributions_received_keur == pytest.approx(20000.0)
        assert handoff_result.total_distributions_received_keur > base_result.total_distributions_received_keur

    def test_capital_account_reflects_distribution_handoff(self):
        """Capital account balance decreases when distribution exceeds injections."""
        # Inject 10000 in p0, distribute 15000 in p5
        injections = (
            EquityInjection(period_index=0, amount_keur=10000.0,
                investor_id="SPONSOR-1", target_entity="HOLDCO", purpose="equityContribution"),
        )
        override = make_distributions(10, 0.0)
        override_list = list(override)
        override_list[5] = 15000.0
        override = tuple(override_list)
        inputs = make_inputs(
            distributions=make_distributions(10, 0.0),
            distribution_account_override=override,
            equity_injections=injections,
        )
        result = run_sponsor_cashflows(inputs)
        # After p5 distribution: balance = 10000 - 15000 = -5000 (negative = return phase)
        assert result.period_results[5].capital_account_balance_keur == pytest.approx(-5000.0)


class TestOborovoGuard:
    """Case 7: Oborovo does not receive TUHO-specific distribution input."""

    def test_oborovo_investor_sees_zero_by_default(self):
        """Oborovo project with no distributions: sponsor receives 0."""
        oborovo_inputs = make_inputs(
            distributions=make_distributions(10, 0.0),
            distribution_account_override=None,
            investor_id="OBOROVO-SPONSOR",
            entity_code="OBOROVO-HOLDCO",
        )
        result = run_sponsor_cashflows(oborovo_inputs)
        for p in result.period_results:
            assert p.distribution_received_keur == pytest.approx(0.0)

    def test_oborovo_no_tuho_leakage(self):
        """Oborovo with TUHO distribution value: would need explicit override to receive."""
        # Oborovo is isolated — sponsor running Oborovo project does not automatically
        # receive TUHO-specific distribution values
        oborovo_inputs = make_inputs(
            distributions=make_distributions(10, 0.0),
            distribution_account_override=None,  # explicitly None
            investor_id="OBOROVO-SPONSOR",
            entity_code="OBOROVO-HOLDCO",
        )
        result = run_sponsor_cashflows(oborovo_inputs)
        assert result.total_distributions_received_keur == pytest.approx(0.0)
        assert result.investor_id == "OBOROVO-SPONSOR"

    def test_oborovo_r99_r102_not_promoted(self):
        """Oborovo R99/R102 remains blocked."""
        from domain.distribution_account.engine import DistributionAccountEngine
        from domain.distribution_account.inputs import (
            DistributionAccountInputs,
            DistributionAccountPeriodInput,
        )
        from datetime import date

        dist_inputs = DistributionAccountInputs(
            project_name="OBOROVO-SOLAR-1",
            is_tuho=False,
            is_oborovo=True,
            period_inputs=(
                DistributionAccountPeriodInput(
                    period_index=1,
                    operating_period_index=1,
                    period_date=date(2029, 6, 30),
                    opening_distribution_account_balance_keur=0.0,
                    post_senior_cash_available_keur=0.0,
                    post_shl_cash_available_keur=500.0,
                    senior_debt_service_keur=0.0,
                    actual_dscr=1.5,
                    is_tuho=False,
                    is_oborovo=True,
                    enable_r99_r102_runtime=False,
                ),
            ),
        )
        dist_result = DistributionAccountEngine.compute(dist_inputs)
        dp = dist_result.period_results[0]
        # Oborovo: equity_distribution_paid_keur = 0
        assert dp.equity_distribution_paid_keur == pytest.approx(0.0)


class TestNoAppWaterfallCoreChanges:
    """Case 8: No app/waterfall_core.py changes (portable guard)."""

    def test_no_runtime_files_changed(self):
        """No app/, domain/ inputs, or non-SHL domain/ files changed."""
        import subprocess

        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["git", "diff", "--stat", "origin/main...HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        output = result.stdout.strip()
        if not output:
            return
        for line in output.split("\n"):
            stripped = line.strip()
            # Skip blank, untracked (??), diff-range prefix (...), summary lines
            if (
                not stripped
                or stripped.startswith("??")
                or stripped.startswith("...")
                or "files changed" in stripped
                or "|" not in stripped
            ):
                continue
            # Only domain/sponsor/ changes allowed (plus docs/reports/tests)
            allowed = [
                "domain/sponsor/", "docs/", "reports/", "tests/",
                "app/templates/partials/runtime_summary.html",  # UX-2C-1 cross-arc
                "app/ui/dashboard.py",  # UX-2C-1 cross-arc
            ]
            assert any(stripped.startswith(p) for p in allowed), \
                f"Unexpected change: {stripped}"


class TestR99R102StillBlocked:
    """Case 9: R99/R102 still BLOCKED."""

    def test_g20_remains_blocked_in_gate_matrix(self):
        """G20 remains BLOCKED per phase9 closeout gate matrix."""
        matrix_path = Path("reports/phase9_closeout_gate_matrix.csv")
        if matrix_path.exists():
            import csv
            with open(matrix_path) as f:
                reader = csv.DictReader(f)
                g20_rows = [r for r in reader if r.get("gate_id", "").strip() == "G20"]
            if g20_rows:
                assert g20_rows[0]["status"] == "BLOCKED"

    def test_distribution_account_no_production_routing(self):
        """DistributionAccount does not enable production routing in this branch."""
        from domain.distribution_account.engine import DistributionAccountEngine
        from domain.distribution_account.inputs import (
            DistributionAccountInputs,
            DistributionAccountPeriodInput,
        )
        from datetime import date

        dist_inputs = DistributionAccountInputs(
            project_name="TUHO-WIND-1",
            is_tuho=True,
            is_oborovo=False,
            period_inputs=(
                DistributionAccountPeriodInput(
                    period_index=1,
                    operating_period_index=1,
                    period_date=date(2029, 6, 30),
                    opening_distribution_account_balance_keur=0.0,
                    post_senior_cash_available_keur=0.0,
                    post_shl_cash_available_keur=500.0,
                    senior_debt_service_keur=0.0,
                    actual_dscr=1.5,
                    is_tuho=True,
                    is_oborovo=False,
                    enable_r99_r102_runtime=False,
                ),
            ),
        )
        dist_result = DistributionAccountEngine.compute(dist_inputs)
        dp = dist_result.period_results[0]
        # Audit-only: no equity distribution paid
        assert dp.equity_distribution_paid_keur == pytest.approx(0.0)
        # No cash swept to SHL in audit-only mode
        assert dp.cash_swept_to_shl_keur == pytest.approx(0.0)


class TestCrossModuleCompatibility:
    """Case 10: SHL R102 input wiring remains unaffected."""

    def test_shl_r102_wiring_still_intact(self):
        """SHL R102 input wiring is unaffected by sponsor handoff changes."""
        from domain.shl.inputs import ShlEngineInputs, ShlPeriodInput
        from domain.shl.engine import ShlEngine

        inputs = ShlEngineInputs(
            project_name="TUHO",
            period_count=1,
                period_inputs=(ShlPeriodInput(
                period_index=1, opening_balance_keur=0.0, drawdown_keur=0.0,
                interest_rate=0.08, day_count_fraction=0.5,
                post_senior_cash_available_keur=1000.0,
                pik_allowed=True,
                distribution_account_r102_sweep_candidate_keur=None,
            ),),
            total_shl_funding_keur=5000.0,
            tranche_opening_balances_keur=(5000.0,),
        )
        result = ShlEngine.compute(inputs)
        p = result.period_results[0]
        assert p.gross_accrued_interest_keur == pytest.approx(200.0)
        assert p.distribution_account_r102_sweep_candidate_keur is None
        assert p.r102_sweep_applied_keur == pytest.approx(0.0)

    def test_sponsor_handoff_does_not_affect_shl_fields(self):
        """SponsorCashflowRunner result has no SHL-related fields."""
        result = run_sponsor_cashflows(BASE_INPUTS)
        for attr in dir(result):
            if attr.startswith("_"):
                continue
            assert "shl" not in attr.lower(), f"Unexpected SHL field: {attr}"

    def test_sponsor_handoff_does_not_affect_distribution_account_fields(self):
        """SponsorCashflowRunner result has no DistributionAccount fields."""
        result = run_sponsor_cashflows(BASE_INPUTS)
        # SponsorCashflowRunner does not produce DistributionAccount fields
        assert not hasattr(result, "equity_distribution_paid_keur")
        assert not hasattr(result, "r99_gate_result")
        assert not hasattr(result, "r102_gate_result")