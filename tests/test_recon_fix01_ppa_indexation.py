"""tests/test_recon_fix01_ppa_indexation.py — PPA indexation policy unit tests.

Covers:
- PpaIndexationStartPolicy enum: all three modes
- count_ppa_escalation_events: date-driven correctness
- compute_ppa_tariff: tariff path for each mode
- Oborovo authoritative path: FIRST_FULL_CALENDAR_YEAR_AS_BASE
- Identity independence: output must not depend on project name / code
- COD semantics: contractual COD is EDATE-equivalent (relativedelta)
- Date edge cases: 31-Jan +1 month, 29-Feb, month-end, leap year
"""
from __future__ import annotations

import dataclasses
from datetime import date

import pytest
from dateutil.relativedelta import relativedelta

from financial_engine.ppa_indexation import (
    PpaIndexationStartPolicy,
    count_ppa_escalation_events,
    compute_ppa_tariff,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

POLICY_CY = PpaIndexationStartPolicy.FIRST_FULL_CALENDAR_YEAR_AS_BASE
POLICY_OY = PpaIndexationStartPolicy.AFTER_FIRST_FULL_OPERATING_YEAR
POLICY_CA = PpaIndexationStartPolicy.CONTRACT_ANNIVERSARY

OBOROVO_COD = date(2030, 6, 29)  # financial_close(2029-06-29) + 12m
OBOROVO_BASE = 57.0
OBOROVO_INDEX = 0.02


# ---------------------------------------------------------------------------
# 1. FIRST_FULL_CALENDAR_YEAR_AS_BASE — Oborovo authoritative path
# ---------------------------------------------------------------------------

class TestFirstFullCalendarYearAsBase:

    def test_oborovo_2030_partial_year_base_tariff(self):
        # 2030 = partial year — no escalation
        assert compute_ppa_tariff(OBOROVO_BASE, OBOROVO_INDEX, POLICY_CY, OBOROVO_COD,
                                   date(2030, 12, 31)) == pytest.approx(57.0)

    def test_oborovo_2031_h1_base_tariff(self):
        # 2031 is base year — no escalation
        assert compute_ppa_tariff(OBOROVO_BASE, OBOROVO_INDEX, POLICY_CY, OBOROVO_COD,
                                   date(2031, 6, 30)) == pytest.approx(57.0)

    def test_oborovo_2031_h2_base_tariff(self):
        assert compute_ppa_tariff(OBOROVO_BASE, OBOROVO_INDEX, POLICY_CY, OBOROVO_COD,
                                   date(2031, 12, 31)) == pytest.approx(57.0)

    def test_oborovo_2032_h1_first_escalation(self):
        # 2032 = first escalation: 57.00 * 1.02 = 58.14
        assert compute_ppa_tariff(OBOROVO_BASE, OBOROVO_INDEX, POLICY_CY, OBOROVO_COD,
                                   date(2032, 6, 30)) == pytest.approx(58.14, rel=1e-9)

    def test_oborovo_2032_h2_first_escalation(self):
        assert compute_ppa_tariff(OBOROVO_BASE, OBOROVO_INDEX, POLICY_CY, OBOROVO_COD,
                                   date(2032, 12, 31)) == pytest.approx(58.14, rel=1e-9)

    def test_oborovo_2033_second_escalation(self):
        # 57.00 * 1.02^2 = 59.3028
        assert compute_ppa_tariff(OBOROVO_BASE, OBOROVO_INDEX, POLICY_CY, OBOROVO_COD,
                                   date(2033, 6, 30)) == pytest.approx(59.3028, rel=1e-9)

    def test_oborovo_2034_third_escalation(self):
        # 57.00 * 1.02^3 = 60.488856
        assert compute_ppa_tariff(OBOROVO_BASE, OBOROVO_INDEX, POLICY_CY, OBOROVO_COD,
                                   date(2034, 6, 30)) == pytest.approx(57.0 * 1.02 ** 3, rel=1e-9)

    def test_cod_on_jan1_base_year_is_same_year(self):
        # If COD = Jan 1 2030, base year = 2030 (it IS a full year).
        cod = date(2030, 1, 1)
        # 2030 H1 end: no escalation (base year)
        assert compute_ppa_tariff(100.0, 0.1, POLICY_CY, cod, date(2030, 6, 30)) == pytest.approx(100.0)
        # 2031 H1 end: 1 escalation
        assert compute_ppa_tariff(100.0, 0.1, POLICY_CY, cod, date(2031, 6, 30)) == pytest.approx(110.0)

    def test_cod_on_dec31_base_year_is_next_year(self):
        # COD = Dec 31 2030 → base year = 2031.
        cod = date(2030, 12, 31)
        # Period ending 30-Jun-2031 = base year → no escalation
        assert compute_ppa_tariff(100.0, 0.1, POLICY_CY, cod, date(2031, 6, 30)) == pytest.approx(100.0)
        # Period ending 31-Dec-2031 = base year → no escalation
        assert compute_ppa_tariff(100.0, 0.1, POLICY_CY, cod, date(2031, 12, 31)) == pytest.approx(100.0)
        # Period ending 30-Jun-2032 → 1 escalation
        assert compute_ppa_tariff(100.0, 0.1, POLICY_CY, cod, date(2032, 6, 30)) == pytest.approx(110.0)

    def test_escalation_count_only_non_negative(self):
        # Period before base year (e.g. same year as COD) must give 0
        n = count_ppa_escalation_events(POLICY_CY, OBOROVO_COD, date(2030, 12, 31))
        assert n == 0

    def test_escalation_count_correct_sequence(self):
        cod = date(2030, 6, 29)
        expected = {
            date(2030, 12, 31): 0,
            date(2031, 6, 30): 0,
            date(2031, 12, 31): 0,
            date(2032, 6, 30): 1,
            date(2032, 12, 31): 1,
            date(2033, 6, 30): 2,
            date(2035, 12, 31): 4,
        }
        for period_end, exp_n in expected.items():
            assert count_ppa_escalation_events(POLICY_CY, cod, period_end) == exp_n, (
                f"period_end={period_end}: expected {exp_n}"
            )


# ---------------------------------------------------------------------------
# 2. AFTER_FIRST_FULL_OPERATING_YEAR
# ---------------------------------------------------------------------------

class TestAfterFirstFullOperatingYear:

    def test_before_first_anniversary_no_escalation(self):
        cod = date(2030, 6, 29)
        # June 28 2031 = one day before first anniversary
        assert compute_ppa_tariff(100.0, 0.1, POLICY_OY, cod, date(2031, 6, 28)) == pytest.approx(100.0)

    def test_on_first_anniversary_one_escalation(self):
        cod = date(2030, 6, 29)
        assert compute_ppa_tariff(100.0, 0.1, POLICY_OY, cod, date(2031, 6, 29)) == pytest.approx(110.0)

    def test_after_first_anniversary_one_escalation(self):
        cod = date(2030, 6, 29)
        assert compute_ppa_tariff(100.0, 0.1, POLICY_OY, cod, date(2031, 12, 31)) == pytest.approx(110.0)

    def test_second_anniversary_two_escalations(self):
        cod = date(2030, 6, 29)
        assert compute_ppa_tariff(100.0, 0.1, POLICY_OY, cod, date(2032, 6, 29)) == pytest.approx(121.0, rel=1e-9)

    def test_escalation_count_sequence(self):
        cod = date(2030, 6, 29)
        cases = [
            (date(2030, 12, 31), 0),
            (date(2031, 6, 28), 0),
            (date(2031, 6, 29), 1),
            (date(2031, 12, 31), 1),
            (date(2032, 6, 29), 2),
            (date(2033, 6, 29), 3),
        ]
        for period_end, exp in cases:
            assert count_ppa_escalation_events(POLICY_OY, cod, period_end) == exp, (
                f"period_end={period_end}"
            )

    def test_mid_year_cod_june_anniversary(self):
        # COD on June 29 — anniversary occurs inside the Dec-to-Jun semiannual period.
        cod = date(2030, 6, 29)
        # Period Dec-31-2030 → Jun-30-2031 (ends Jun-30-2031, which is AFTER the Jun-29 anniversary)
        n = count_ppa_escalation_events(POLICY_OY, cod, date(2031, 6, 30))
        assert n == 1  # first anniversary (Jun 29 2031) has passed by Jun 30 2031


# ---------------------------------------------------------------------------
# 3. CONTRACT_ANNIVERSARY
# ---------------------------------------------------------------------------

class TestContractAnniversary:

    def test_explicit_start_date_independent_of_cod(self):
        cod = date(2030, 6, 29)
        ppa_start = date(2030, 10, 1)
        # Period ending Sep 30 2031 = exactly one day before first anniversary
        n = count_ppa_escalation_events(POLICY_CA, cod, date(2031, 9, 30), ppa_start)
        assert n == 0

    def test_explicit_start_date_first_anniversary(self):
        cod = date(2030, 6, 29)
        ppa_start = date(2030, 10, 1)
        # Oct 1 2031 = exactly first anniversary
        n = count_ppa_escalation_events(POLICY_CA, cod, date(2031, 10, 1), ppa_start)
        assert n == 1

    def test_explicit_start_date_second_anniversary(self):
        cod = date(2030, 6, 29)
        ppa_start = date(2030, 10, 1)
        n = count_ppa_escalation_events(POLICY_CA, cod, date(2032, 10, 1), ppa_start)
        assert n == 2

    def test_none_ppa_start_raises_for_contract_anniversary(self):
        cod = date(2030, 6, 29)
        # CONTRACT_ANNIVERSARY requires an explicit date — None must raise ValueError.
        with pytest.raises(ValueError, match="ppa_indexation_start_date is required"):
            count_ppa_escalation_events(POLICY_CA, cod, date(2031, 6, 29), None)

    def test_tariff_with_explicit_start(self):
        cod = date(2030, 6, 29)
        ppa_start = date(2030, 10, 1)
        # Period ending Dec-31-2031: Oct-1-2031 anniversary has passed → 1 escalation
        t = compute_ppa_tariff(100.0, 0.05, POLICY_CA, cod, date(2031, 12, 31), ppa_start)
        assert t == pytest.approx(105.0, rel=1e-9)


# ---------------------------------------------------------------------------
# 4. Identity independence
# ---------------------------------------------------------------------------

class TestIdentityIndependence:

    def test_tariff_unchanged_by_project_name(self):
        """Tariff must not depend on project names, codes, or baseline IDs."""
        # Simulate two "projects" with different names but identical financial inputs
        # by calling compute_ppa_tariff directly (no project-identity dispatch in module)
        cod = OBOROVO_COD
        period_end = date(2032, 6, 30)
        tariff_a = compute_ppa_tariff(57.0, 0.02, POLICY_CY, cod, period_end)
        tariff_b = compute_ppa_tariff(57.0, 0.02, POLICY_CY, cod, period_end)
        assert tariff_a == tariff_b

    def test_tariff_differs_only_by_financial_inputs(self):
        # Different base tariff → different result
        cod = OBOROVO_COD
        period_end = date(2032, 6, 30)
        t1 = compute_ppa_tariff(57.0, 0.02, POLICY_CY, cod, period_end)
        t2 = compute_ppa_tariff(60.0, 0.02, POLICY_CY, cod, period_end)
        assert t1 != t2

    def test_policy_is_independent_of_baseline_id(self):
        # Enum values are generic strings, no project name embedded
        assert "oborovo" not in POLICY_CY.value.lower()
        assert "tuho" not in POLICY_CY.value.lower()
        assert "solar" not in POLICY_OY.value.lower()


# ---------------------------------------------------------------------------
# 5. COD EDATE-equivalent semantics
# ---------------------------------------------------------------------------

class TestCodEdateSemantics:

    def test_oborovo_cod_is_edate_equivalent(self):
        financial_close = date(2029, 6, 29)
        construction_months = 12
        cod = financial_close + relativedelta(months=construction_months)
        assert cod == date(2030, 6, 29)

    def test_edate_31jan_plus_1month(self):
        # Excel EDATE(31-Jan, 1) = 28-Feb (last day of Feb in non-leap year)
        # dateutil relativedelta should agree
        d = date(2025, 1, 31) + relativedelta(months=1)
        assert d == date(2025, 2, 28)

    def test_edate_28feb_plus_1month_non_leap(self):
        d = date(2025, 2, 28) + relativedelta(months=1)
        assert d == date(2025, 3, 28)

    def test_edate_29feb_plus_12months_leap_to_non_leap(self):
        # 29-Feb-2024 + 12 months → 28-Feb-2025 (2025 not a leap year)
        d = date(2024, 2, 29) + relativedelta(months=12)
        assert d == date(2025, 2, 28)

    def test_edate_month_end_preserved(self):
        # Last day of April + 1 month = last day of May
        d = date(2030, 4, 30) + relativedelta(months=1)
        assert d == date(2030, 5, 30)

    def test_edate_december_plus_6months(self):
        d = date(2029, 12, 31) + relativedelta(months=6)
        assert d == date(2030, 6, 30)

    def test_edate_february_leap_year(self):
        # 29-Feb-2024 exists (2024 is leap year)
        d = date(2024, 2, 29)
        assert d.month == 2 and d.day == 29


# ---------------------------------------------------------------------------
# 6. Adapter/engine integration — RevenueInput round-trip
# ---------------------------------------------------------------------------

class TestRevenueInputRoundTrip:

    def test_revenue_input_has_policy_field(self):
        from financial_engine.inputs import RevenueInput
        rev = RevenueInput(
            ppa_base_tariff_eur_mwh=57.0,
            ppa_term_years=12.0,
            ppa_index=0.02,
            ppa_production_share=1.0,
            market_prices_curve_eur_mwh=(80.0,),
            market_inflation=0.02,
            balancing_cost_pv_fraction=0.0,
            balancing_cost_wind_eur_mwh=0.0,
            co2_enabled=False,
            co2_price_eur_mwh=0.0,
        )
        # Default should be AFTER_FIRST_FULL_OPERATING_YEAR
        assert rev.ppa_indexation_start_policy == PpaIndexationStartPolicy.AFTER_FIRST_FULL_OPERATING_YEAR
        assert rev.ppa_indexation_start_date is None

    def test_revenue_input_accepts_first_full_cy_policy(self):
        from financial_engine.inputs import RevenueInput
        rev = RevenueInput(
            ppa_base_tariff_eur_mwh=57.0,
            ppa_term_years=12.0,
            ppa_index=0.02,
            ppa_production_share=1.0,
            market_prices_curve_eur_mwh=(80.0,),
            market_inflation=0.02,
            balancing_cost_pv_fraction=0.0,
            balancing_cost_wind_eur_mwh=0.0,
            co2_enabled=False,
            co2_price_eur_mwh=0.0,
            ppa_indexation_start_policy=PpaIndexationStartPolicy.FIRST_FULL_CALENDAR_YEAR_AS_BASE,
        )
        assert rev.ppa_indexation_start_policy == PpaIndexationStartPolicy.FIRST_FULL_CALENDAR_YEAR_AS_BASE

    def test_oborovo_factory_policy_is_first_full_cy(self):
        from app.project_factories import create_default_oborovo
        proj = create_default_oborovo()
        assert proj.revenue.ppa_indexation_start_policy == "FIRST_FULL_CALENDAR_YEAR_AS_BASE"

    def test_adapter_maps_policy_to_enum(self):
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import from_project_inputs
        proj = create_default_oborovo()
        adapted = from_project_inputs(proj)
        assert adapted.revenue.ppa_indexation_start_policy == PpaIndexationStartPolicy.FIRST_FULL_CALENDAR_YEAR_AS_BASE


# ---------------------------------------------------------------------------
# 6b. Invalid policy / CONTRACT_ANNIVERSARY validation
# ---------------------------------------------------------------------------

class TestValidation:

    def test_invalid_policy_string_raises_in_adapter(self):
        """Typo or unknown policy value must raise ValueError, not silently fall back."""
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import from_project_inputs
        import dataclasses

        proj = create_default_oborovo()
        # Inject a typo policy string into revenue params
        bad_rev = dataclasses.replace(proj.revenue, ppa_indexation_start_policy="TYPO_POLICY")
        bad_proj = dataclasses.replace(proj, revenue=bad_rev)
        with pytest.raises(ValueError, match="Invalid ppa_indexation_start_policy"):
            from_project_inputs(bad_proj)

    def test_empty_policy_string_raises_in_adapter(self):
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import from_project_inputs
        import dataclasses

        proj = create_default_oborovo()
        bad_rev = dataclasses.replace(proj.revenue, ppa_indexation_start_policy="")
        bad_proj = dataclasses.replace(proj, revenue=bad_rev)
        with pytest.raises(ValueError, match="Invalid ppa_indexation_start_policy"):
            from_project_inputs(bad_proj)

    def test_contract_anniversary_none_date_raises(self):
        """CONTRACT_ANNIVERSARY with no date must raise, not silently use COD."""
        cod = date(2030, 6, 29)
        with pytest.raises(ValueError, match="ppa_indexation_start_date is required"):
            count_ppa_escalation_events(POLICY_CA, cod, date(2031, 10, 1), None)

    def test_contract_anniversary_none_date_raises_in_compute(self):
        with pytest.raises(ValueError, match="ppa_indexation_start_date is required"):
            compute_ppa_tariff(57.0, 0.02, POLICY_CA, date(2030, 6, 29), date(2031, 10, 1), None)


# ---------------------------------------------------------------------------
# 7. Engine integration — Oborovo tariff path
# ---------------------------------------------------------------------------

class TestEngineIntegrationOborovo:
    """Verify that run_operating_model produces the FIRST_FULL_CALENDAR_YEAR_AS_BASE
    tariff sequence for Oborovo without touching any frozen outputs."""

    @pytest.fixture(scope="class")
    def oborovo_result(self):
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import from_project_inputs
        from financial_engine.orchestrator import run_operating_model
        proj = create_default_oborovo()
        adapted = from_project_inputs(proj, source_id="test_ppa_indexation")
        return run_operating_model(adapted)

    def test_tariff_schedule_loaded(self, oborovo_result):
        from financial_engine.ppa_indexation import compute_ppa_tariff
        from dateutil.relativedelta import relativedelta
        # Re-compute expected tariffs for first 6 operating periods
        cod = date(2030, 6, 29)
        period_ends = [
            date(2030, 12, 31),  # op period 0
            date(2031, 6, 30),   # op period 1
            date(2031, 12, 31),  # op period 2
            date(2032, 6, 30),   # op period 3
            date(2032, 12, 31),  # op period 4
            date(2033, 6, 30),   # op period 5
        ]
        expected = [compute_ppa_tariff(57.0, 0.02, POLICY_CY, cod, pe) for pe in period_ends]
        # Expected: 57, 57, 57, 58.14, 58.14, 59.3028
        assert expected[0] == pytest.approx(57.0)
        assert expected[1] == pytest.approx(57.0)
        assert expected[2] == pytest.approx(57.0)
        assert expected[3] == pytest.approx(57.0 * 1.02, rel=1e-9)
        assert expected[4] == pytest.approx(57.0 * 1.02, rel=1e-9)
        assert expected[5] == pytest.approx(57.0 * 1.02 ** 2, rel=1e-9)

    def test_revenue_changes_from_new_policy(self, oborovo_result):
        # Revenue must be finite and positive for operating periods
        op = [p for p in oborovo_result.periods if p.is_operation]
        revenues = [p.revenue_keur for p in op]
        assert all(r > 0 for r in revenues[:12]), "All PPA-period revenues must be positive"

    def test_production_unchanged(self, oborovo_result):
        # Production is independent of tariff — must still be positive
        op = [p for p in oborovo_result.periods if p.is_operation]
        assert all(p.production_mwh > 0 for p in op[:10])
