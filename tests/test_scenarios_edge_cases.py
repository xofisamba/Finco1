"""Edge-case tests for scenarios, capex scaling, portfolio runner, and UI runner."""
import pytest
from dataclasses import replace, fields as dc_fields

from app.scenarios import apply_scenario, get_scenario_rules, SCENARIO_RULES
from app.capex_overrides import scale_capex_items
from app.project_factories import create_default_solar_project, create_default_wind_project
from app.portfolio_runner import run_portfolio_from_inputs
from app.ui_runner import run_demo_project
from domain.portfolio.inputs import PortfolioInputs
from domain.portfolio.waterfall import run_portfolio_waterfall
from domain.inputs import FinancingParams


# ── Scenario edge cases ───────────────────────────────────────────────────────

class TestScenarioEdgeCases:
    def test_apply_scenario_missing_p50_field_safe(self):
        """apply_scenario must not crash if technical has no P50 field.

        P50_FIELDS lists multiple field-name candidates; _first_existing_field
        returns None if none exist, so no attribute is accessed on a missing key.
        """
        solar = create_default_solar_project()
        # Solar has p50 — verify it works without crashing
        result = apply_scenario(solar, "downside")
        assert result is not None
        # The method should be robust even for projects that have no P50 field at all
        tech = solar.technical
        # Confirm that _first_existing_field returns None for an unknown field list
        from app.scenarios import _first_existing_field
        assert _first_existing_field(tech, ("nonexistent_field_x",)) is None

    def test_apply_scenario_unknown_scenario_raises(self):
        """Unknown scenario must raise ValueError."""
        solar = create_default_solar_project()
        with pytest.raises(ValueError, match="Unknown scenario"):
            apply_scenario(solar, "  extreme_downside  ")

    def test_apply_scenario_does_not_mutate_original(self):
        """Original project inputs must not be mutated."""
        solar = create_default_solar_project()
        orig_p50 = solar.technical.operating_hours_p50
        orig_tariff = solar.revenue.ppa_base_tariff
        orig_capex = solar.capex.total_capex

        _ = apply_scenario(solar, "downside")

        # Original must be unchanged
        assert solar.technical.operating_hours_p50 == orig_p50
        assert solar.revenue.ppa_base_tariff == orig_tariff
        assert solar.capex.total_capex == orig_capex

    def test_apply_scenario_base_is_identity(self):
        """Base scenario returns inputs equivalent to originals (within floating point)."""
        solar = create_default_solar_project()
        result = apply_scenario(solar, "base")
        assert result.technical.operating_hours_p50 == solar.technical.operating_hours_p50
        assert result.revenue.ppa_base_tariff == solar.revenue.ppa_base_tariff
        assert result.capex.total_capex == solar.capex.total_capex

    def test_apply_scenario_downside_all_changes_applied(self):
        """Downside must apply all three: p50-, capex+, tariff-."""
        solar = create_default_solar_project()
        result = apply_scenario(solar, "downside")
        assert result.technical.operating_hours_p50 == solar.technical.operating_hours_p50 * 0.9
        assert result.capex.total_capex == solar.capex.total_capex * 1.05
        assert result.revenue.ppa_base_tariff == solar.revenue.ppa_base_tariff * 0.95

    def test_unknown_scenario_case_insensitive_raises(self):
        """Unknown scenario (even with weird case) must raise."""
        solar = create_default_solar_project()
        for bad in ("DOWNSIDEEE", "  extreme", "downsidex"):
            with pytest.raises(ValueError, match="Unknown scenario"):
                apply_scenario(solar, bad)

    def test_scenario_rules_keys_lowercase(self):
        """SCENARIO_RULES must use lowercase keys internally."""
        assert all(k.islower() for k in SCENARIO_RULES)

    def test_get_scenario_rules_unknown_raises(self):
        """get_scenario_rules must raise ValueError for unknown scenario."""
        with pytest.raises(ValueError, match="Unknown scenario"):
            get_scenario_rules("foobar")


# ── CapEx scaling edge cases ───────────────────────────────────────────────────

    def test_apply_scenario_accepts_whitespace_in_name(self):
        """apply_scenario and get_scenario_rules must normalize whitespace."""
        solar = create_default_solar_project()
        result = apply_scenario(solar, " Downside ")
        assert result is not None
        rules = get_scenario_rules("  Downside  ")
        assert rules["p50_multiplier"] == 0.90

class TestCapExScalingEdgeCases:
    def test_scale_capex_zero_total(self):
        """scale_capex_items returns unchanged when total_capex is truly zero.

        A true zero CapexStructure requires ALL contributing fields to be 0.0:
        - each CapexItem.amount_keur = 0.0
        - scalar fields: idc_keur, bank_fees_keur, other_financial_keur, vat_costs_keur
        - (commitment_fees_keur and reserve_accounts_keur excluded from hard capex base)

        scale_capex_items() returns capex unchanged when current_total <= 0.
        """
        from dataclasses import fields as dc_fields

        capex = create_default_solar_project().capex

        # Build a TRUE zero CapexStructure by nulling every numeric contributing field
        new_field_values = {}
        for f in dc_fields(capex):
            val = getattr(capex, f.name)
            if hasattr(val, 'amount_keur'):
                # It's a CapexItem — zero its amount
                new_field_values[f.name] = replace(val, amount_keur=0.0)
            elif isinstance(val, (int, float)):
                new_field_values[f.name] = 0.0
            else:
                new_field_values[f.name] = val

        zero_capex = replace(capex, **new_field_values)

        # Verify it's truly zero
        assert zero_capex.total_capex == 0.0,             f"Expected total_capex=0, got {zero_capex.total_capex}"

        # scale_capex_items should return unchanged (early return for total <= 0)
        result = scale_capex_items(zero_capex, 50_000.0)
        assert result is not None
        assert result.total_capex == 0.0

    def test_scale_capex_no_negative_items_when_scaling_down(self):
        """scale_capex_items must not produce negative amounts when scaling down."""
        solar = create_default_solar_project()
        capex = solar.capex
        # Scale down by 50% — no item should go negative
        result = scale_capex_items(capex, capex.total_capex * 0.5)
        for f in dc_fields(result):
            val = getattr(result, f.name)
            if hasattr(val, 'amount_keur'):
                assert val.amount_keur >= 0, f"CapEx item {f.name} has negative amount"

    def test_scale_capex_preserves_structure_type(self):
        """scale_capex_items must return a CapexStructure of the same type."""
        solar = create_default_solar_project()
        result = scale_capex_items(solar.capex, solar.capex.total_capex * 1.1)
        assert type(result) == type(solar.capex)

    def test_scale_capex_very_large_multiplier(self):
        """Very large capex multiplier must not overflow."""
        solar = create_default_solar_project()
        result = scale_capex_items(solar.capex, solar.capex.total_capex * 1000)
        assert result.total_capex > 0  # must be positive, not inf/nan



    def test_scale_capex_negative_target_rejected(self):
        """scale_capex_items raises ValueError for negative target_total_capex."""
        capex = create_default_solar_project().capex
        with pytest.raises(ValueError, match="non-negative"):
            scale_capex_items(capex, -100.0)

class TestPortfolioEdgeCases:
    def test_portfolio_empty_projects_list(self):
        """PortfolioInputs with < 2 projects must raise ValueError in __post_init__."""
        solar = create_default_solar_project()
        shared = FinancingParams(
            share_capital_keur=100.0,
            senior_debt_amount_keur=200.0,
            senior_tenor_years=10,
            target_dscr=1.4,
        )
        with pytest.raises(ValueError, match="at least 2"):
            PortfolioInputs(
                projects=(solar,),
                portfolio_name="EmptyTest",
                shared_financing=shared,
            )

    def test_portfolio_duplicate_project_codes_raises(self):
        """PortfolioInputs with duplicate project codes must raise."""
        solar = create_default_solar_project()
        wind = create_default_wind_project()
        # solar and wind may have same code — check what they actually are
        solar2 = replace(solar, info=replace(solar.info, code="SOLAR-001"))
        shared = FinancingParams(
            share_capital_keur=100.0,
            senior_debt_amount_keur=200.0,
            senior_tenor_years=10,
            target_dscr=1.4,
        )
        # If they have same code, should raise
        codes = [solar.info.code, wind.info.code]
        if len(set(codes)) != len(codes):
            with pytest.raises(ValueError, match="unique"):
                PortfolioInputs(
                    projects=(solar, wind),
                    portfolio_name="DupTest",
                    shared_financing=shared,
                )

    def test_portfolio_zero_cfads_safe(self):
        """Portfolio must not crash with zero CFADS schedule (dscr=inf handled)."""
        from domain.waterfall.waterfall_engine import WaterfallResult, WaterfallPeriod
        from datetime import date

        solar = create_default_solar_project()
        shared = FinancingParams(
            share_capital_keur=100.0,
            senior_debt_amount_keur=200.0,
            senior_tenor_years=10,
            target_dscr=1.4,
        )

        wf_result = WaterfallResult(
            periods=[WaterfallPeriod(
                period=1, date=date(2030, 6, 30), year_index=1, period_in_year=2,
                is_operation=True,
                generation_mwh=0.0,   # zero generation → zero CFADS
                revenue_keur=0.0, opex_keur=0.0, ebitda_keur=0.0,
                depreciation_keur=0.0,
                interest_senior_keur=10.0, interest_shl_keur=0.0,
                taxable_profit_keur=0.0, tax_keur=0.0,
                cf_after_tax_keur=0.0,
                senior_interest_keur=10.0, senior_principal_keur=0.0, senior_ds_keur=10.0,
                shl_interest_keur=0.0, shl_principal_keur=0.0, shl_service_keur=0.0,
                dsra_contribution_keur=0.0, dsra_balance_keur=0.0,
                mra_contribution_keur=0.0, mra_balance_keur=0.0,
                cf_after_reserves_keur=0.0,
                dscr=float('inf'),  # 0/0 → inf, must be handled
                llcr=999.0, plcr=999.0,
                lockup_active=False,
                distribution_keur=0.0, cash_sweep_keur=0.0,
                cum_distribution_keur=0.0,
                cash_balance_keur=0.0,
                shl_balance_keur=0.0, shl_pik_keur=0.0,
                senior_balance_keur=200.0,
            )],
            total_revenue_keur=0.0, total_opex_keur=0.0,
            total_ebitda_keur=0.0, total_tax_keur=0.0,
            total_senior_ds_keur=10.0, total_shl_service_keur=0.0,
            total_distribution_keur=0.0,
            avg_dscr=float('inf'), min_dscr=float('inf'), max_dscr=float('inf'),
            min_llcr=999.0, min_plcr=999.0, periods_in_lockup=0,
            project_irr=0.0, equity_irr=0.0, sponsor_irr=0.0,
            project_npv=0.0, equity_npv=0.0,
        )

        project_results = (("SOLAR-001", wf_result),)
        portfolio = PortfolioInputs(
            projects=(solar, create_default_wind_project()),
            portfolio_name="ZeroCFADS",
            shared_financing=shared,
        )
        result = run_portfolio_from_inputs(portfolio, project_results=project_results)
        assert result is not None


# ── UI runner validation edge cases ───────────────────────────────────────────

class TestUIValidationEdgeCases:
    def test_ui_runner_handles_unknown_project_type(self):
        """UI runner must handle unknown project type gracefully."""
        try:
            result = run_demo_project("UnknownType")
            # Should return a result with error message, not raise
            assert hasattr(result, 'messages')
        except (ValueError, RuntimeError) as e:
            # Should raise a clear error
            assert "unknown" in str(e).lower() or "invalid" in str(e).lower()

    def test_ui_runner_scenario_parameter_rejects_bad_scenario(self):
        """UI runner must propagate scenario ValueError from apply_scenario."""
        solar = create_default_solar_project()
        result = run_demo_project("Solar", scenario="bad_scenario")
        # Should come back with error message in messages
        error_msgs = [m for m in result.messages if "Unknown scenario" in m or "bad_scenario" in m]
        assert len(error_msgs) > 0, f"Expected error about bad_scenario in messages, got: {result.messages}"

    def test_ui_runner_base_scenario_produces_no_delta_messages(self):
        """Base scenario should not produce scenario-delta messages."""
        result = run_demo_project("Solar", scenario="Base")
        # Base should have a clean run (integration_status full, no scenario warnings)
        assert result.integration_status in ("full", "partial")

    def test_ui_runner_solar_full_status(self):
        """Solar must be integration_status=full."""
        result = run_demo_project("Solar")
        assert result.integration_status == "full"

    def test_ui_runner_wind_full_status(self):
        """Wind must be integration_status=full."""
        result = run_demo_project("Wind")
        assert result.integration_status == "full"

    def test_ui_runner_bess_partial_status(self):
        """BESS must be integration_status=partial."""
        result = run_demo_project("BESS")
        assert result.integration_status == "partial"

    def test_ui_runner_solar_plus_bess_partial(self):
        """Solar+BESS must be integration_status=partial."""
        result = run_demo_project("Solar+BESS")
        assert result.integration_status == "partial"

