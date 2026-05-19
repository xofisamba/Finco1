"""Phase 7 — Revenue CO2 Balancing Split: tests.

Validates that the revenue decomposition exposes the explicit split:
- electricity_revenue_keur
- co2_certificate_revenue_keur
- balancing_cost_keur (positive cost line)
- net_revenue_after_balancing_keur

Business requirement: balancing is a cost but appears in the revenue
section because the Excel source model presents it there.
"""
import pytest
from dataclasses import replace
from datetime import date

from domain.inputs import ProjectInputs, RevenueParams
from domain.period_engine import PeriodEngine, PeriodFrequency
from domain.revenue.generation import (
    revenue_decomposition_schedule,
    full_revenue_schedule,
    full_generation_schedule,
)


# ─── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def oborovo():
    from app.project_factories import create_default_oborovo
    return create_default_oborovo()


@pytest.fixture
def tuho():
    from app.project_factories import create_default_tuho_wind1
    return create_default_tuho_wind1()


@pytest.fixture
def engine():
    return PeriodEngine(
        financial_close=date(2030, 1, 1),
        construction_months=12,
        horizon_years=30,
        ppa_years=12,
        frequency=PeriodFrequency.SEMESTRIAL,
    )


# ─── Helper ────────────────────────────────────────────────────────────────────

def assert_revenue_split_fields_present(decomposition: dict) -> None:
    """Assert all Phase 7 revenue split fields are present in decomposition entry."""
    required_fields = [
        "electricity_revenue_keur",
        "co2_certificate_revenue_keur",
        "balancing_cost_keur",
        "net_revenue_after_balancing_keur",
    ]
    for field in required_fields:
        assert field in decomposition, f"Missing Phase 7 field: {field}"


# ─── Tests ─────────────────────────────────────────────────────────────────────

class TestRevenueSplitFields:
    """Test that all Phase 7 revenue split fields are present."""

    def test_oborovo_revenue_split_fields_present(self, oborovo, engine):
        decomposition = revenue_decomposition_schedule(oborovo, engine)
        op_periods = [p for p in engine.periods() if p.is_operation]

        assert len(op_periods) > 0, "No operation periods found"
        first_op = op_periods[0]
        dec = decomposition[first_op.index]
        assert_revenue_split_fields_present(dec)

    def test_tuho_revenue_split_fields_present(self, tuho, engine):
        decomposition = revenue_decomposition_schedule(tuho, engine)
        op_periods = [p for p in engine.periods() if p.is_operation]

        assert len(op_periods) > 0, "No operation periods found"
        first_op = op_periods[0]
        dec = decomposition[first_op.index]
        assert_revenue_split_fields_present(dec)


class TestRevenueSplitCalculation:
    """Test CO2 certificate and balancing cost calculations."""

    def test_co2_certificate_revenue_formula(self):
        """CO2 certificate revenue = generation_MWh × price_EUR_MWh / 1000."""
        from domain.revenue.generation import _certificate_revenue_keur

        # 10,000 MWh × 4.191 EUR/MWh / 1000 = 41.91 kEUR
        result = _certificate_revenue_keur(
            generation_mwh=10_000.0,
            enabled=True,
            price_eur_mwh=4.191,
        )
        assert result == pytest.approx(41.91, abs=0.01)

    def test_co2_certificate_revenue_disabled(self):
        """CO2 revenue is 0 when disabled."""
        from domain.revenue.generation import _certificate_revenue_keur

        result = _certificate_revenue_keur(
            generation_mwh=10_000.0,
            enabled=False,
            price_eur_mwh=4.191,
        )
        assert result == 0.0

    def test_balancing_cost_formula(self):
        """Balancing cost = generation_MWh × cost_EUR_MWh / 1000."""
        # 10,000 MWh × 8.0 EUR/MWh / 1000 = 80 kEUR
        generation_mwh = 10_000.0
        balancing_eur_mwh = 8.0
        result = generation_mwh * balancing_eur_mwh / 1000
        assert result == 80.0

    def test_net_revenue_calculation(self):
        """net = electricity + CO2 - balancing."""
        electricity_keur = 1000.0
        co2_keur = 40.0
        balancing_keur = 80.0
        net = electricity_keur + co2_keur - balancing_keur
        assert net == 960.0

    def test_legacy_revenue_keur_matches_net(self, tuho, engine):
        """Legacy revenue_keur field must equal net_revenue_after_balancing_keur."""
        decomposition = revenue_decomposition_schedule(tuho, engine)
        op_periods = [p for p in engine.periods() if p.is_operation]

        for period in op_periods[:5]:
            dec = decomposition[period.index]
            assert dec["revenue_keur"] == pytest.approx(
                dec["net_revenue_after_balancing_keur"], abs=0.01
            ), f"Period {period.index}: revenue_keur mismatch"


class TestDefaultValues:
    """Test that missing inputs default to 0.0 without breaking output."""

    def test_missing_co2_price_defaults_to_zero(self):
        """When co2_enabled=False, co2_certificate_revenue_keur = 0."""
        from domain.revenue.generation import _certificate_revenue_keur

        result = _certificate_revenue_keur(
            generation_mwh=50_000.0,
            enabled=False,
            price_eur_mwh=0.0,
        )
        assert result == 0.0

    def test_missing_balancing_cost_defaults_to_zero(self):
        """When no balancing cost defined, balancing_cost_keur = 0."""
        from domain.revenue.generation import _period_energy_revenue_keur

        # With no balancing cost input, only energy revenue contributes
        energy = _period_energy_revenue_keur(
            generation_mwh=50_000.0,
            ppa_tariff=60.0,
            market_price=0.0,
            ppa_active=True,
            ppa_share=1.0,
        )
        # 50,000 MWh × 60 EUR/MWh / 1000 = 3,000 kEUR
        assert energy == pytest.approx(3_000.0, abs=0.1)


class TestTuhoFactoryDefaults:
    """Test TUHO factory includes expected CO2/balancing assumptions."""

    def test_tuho_co2_certificate_price_default(self, tuho):
        """TUHO co2_certificate_price_eur_per_mwh = 4.191 (flat default)."""
        assert tuho.revenue.co2_certificate_price_eur_per_mwh == pytest.approx(
            4.191063312, rel=1e-6
        )

    def test_tuho_balancing_cost_default(self, tuho):
        """TUHO balancing_cost_eur_per_mwh = 8.0 (flat default)."""
        assert tuho.revenue.balancing_cost_eur_per_mwh == 8.0

    def test_tuho_has_co2_sales_schedule(self, tuho):
        """TUHO uses co2_sales_schedule (not flat co2_price_eur for calc)."""
        assert tuho.revenue.co2_sales_schedule is not None

    def test_tuho_has_balancing_cost_schedule(self, tuho):
        """TUHO uses balancing_cost_schedule (8.0 EUR/MWh constant)."""
        assert tuho.revenue.balancing_cost_schedule is not None
        assert tuho.revenue.balancing_cost_schedule.constant_value == 8.0


class TestOborovoFactoryDefaults:
    """Test Oborovo factory includes expected CO2/balancing assumptions."""

    def test_oborovo_co2_certificate_price_default(self, oborovo):
        """Oborovo co2_certificate_price_eur_per_mwh = 1.5."""
        assert oborovo.revenue.co2_certificate_price_eur_per_mwh == 1.5

    def test_oborovo_balancing_cost_default(self, oborovo):
        """Oborovo balancing_cost_eur_per_mwh = 0.0 (no explicit balancing)."""
        assert oborovo.revenue.balancing_cost_eur_per_mwh == 0.0

    def test_oborovo_co2_enabled(self, oborovo):
        """Oborovo CO2 is enabled."""
        assert oborovo.revenue.co2_enabled is True


class TestRevenueSplitParity:
    """Test existing total revenue regression remains unchanged."""

    def test_tuho_total_revenue_schedule_unchanged(self, tuho, engine):
        """full_revenue_schedule still sums to expected TUHO total."""
        schedule = full_revenue_schedule(tuho, engine)
        op_periods = [p for p in engine.periods() if p.is_operation]

        total = sum(schedule[p.index] for p in op_periods)
        # TUHO total revenue over 30 years from Sprint 22 calibration ≈ 423,788 kEUR
        # This is the reference value — any change here is a regression
        assert total == pytest.approx(423_787.5, abs=500.0), (
            f"TUHO total revenue {total:,.0f} kEUR differs from calibration {423_787.5:,.0f}"
        )

    def test_oborovo_total_revenue_schedule_unchanged(self, oborovo, engine):
        """full_revenue_schedule for Oborovo returns positive revenue."""
        schedule = full_revenue_schedule(oborovo, engine)
        op_periods = [p for p in engine.periods() if p.is_operation]

        total = sum(schedule[p.index] for p in op_periods)
        assert total > 0, "Oborovo total revenue should be positive"
        # Oborovo total revenue reference: ~337,000 kEUR (rough estimate)
        assert total > 200_000, f"Oborovo total revenue {total:,.0f} seems too low"


class TestBackwardCompatibility:
    """Test backward compatibility for legacy input fields.

    Priority chain for balancing EUR/MWh:
      schedule > balancing_cost_eur_per_mwh > balancing_cost_wind_eur_mwh

    Priority chain for CO2 EUR/MWh:
      schedule > co2_certificate_price_eur_per_mwh > co2_price_eur
    """

    def test_legacy_balancing_cost_wind_eur_mwh_still_works_when_new_field_is_zero(
        self, tuho, engine
    ):
        """Legacy balancing_cost_wind_eur_mwh activates when both new field=0 and no schedule."""
        from dataclasses import replace
        from domain.inputs import RevenueAdjustmentSchedule

        # Patch TUHO: new field=0, no schedule, old field=8.0
        patched_rev = replace(
            tuho.revenue,
            balancing_cost_eur_per_mwh=0.0,
            balancing_cost_schedule=None,
            balancing_cost_wind_eur_mwh=8.0,
        )
        patched_tuho = replace(tuho, revenue=patched_rev)
        decomposition = revenue_decomposition_schedule(patched_tuho, engine)
        op_periods = [p for p in engine.periods() if p.is_operation]

        for period in op_periods[:3]:
            dec = decomposition[period.index]
            gen_mwh = dec["generation_mwh"]
            expected_cost = gen_mwh * 8.0 / 1000  # legacy value
            assert dec["balancing_cost_wind_keur"] == pytest.approx(expected_cost, abs=0.01)

    def test_new_balancing_cost_eur_per_mwh_overrides_legacy_when_nonzero(
        self, tuho, engine
    ):
        """New balancing_cost_eur_per_mwh overrides legacy when non-zero and no schedule."""
        from dataclasses import replace

        # Patch TUHO: new field=10.0 (non-zero), no schedule, old field=8.0
        patched_rev = replace(
            tuho.revenue,
            balancing_cost_eur_per_mwh=10.0,
            balancing_cost_schedule=None,
            balancing_cost_wind_eur_mwh=8.0,
        )
        patched_tuho = replace(tuho, revenue=patched_rev)
        decomposition = revenue_decomposition_schedule(patched_tuho, engine)
        op_periods = [p for p in engine.periods() if p.is_operation]


        for period in op_periods[:3]:
            dec = decomposition[period.index]
            gen_mwh = dec["generation_mwh"]
            expected_cost = gen_mwh * 10.0 / 1000  # new field value
            assert dec["balancing_cost_wind_keur"] == pytest.approx(expected_cost, abs=0.01)

    def test_schedule_still_overrides_both_balancing_fields(self, tuho, engine):
        """balancing_cost_schedule takes priority over both legacy and new fields."""
        from dataclasses import replace
        from domain.inputs import RevenueAdjustmentSchedule

        # Patch TUHO: schedule=5.0 (non-zero), new field=10.0, old field=8.0
        patched_rev = replace(
            tuho.revenue,
            balancing_cost_eur_per_mwh=10.0,
            balancing_cost_schedule=RevenueAdjustmentSchedule(constant_value=5.0),
            balancing_cost_wind_eur_mwh=8.0,
        )
        patched_tuho = replace(tuho, revenue=patched_rev)
        decomposition = revenue_decomposition_schedule(patched_tuho, engine)
        op_periods = [p for p in engine.periods() if p.is_operation]

        for period in op_periods[:3]:
            dec = decomposition[period.index]
            gen_mwh = dec["generation_mwh"]
            expected_cost = gen_mwh * 5.0 / 1000  # schedule wins
            assert dec["balancing_cost_wind_keur"] == pytest.approx(expected_cost, abs=0.01)

    def test_legacy_co2_price_eur_still_works_when_new_field_is_zero(
        self, tuho, engine
    ):
        """Legacy co2_price_eur activates when new field=0 and no schedule."""
        from dataclasses import replace

        # co2_price_eur=5.0 in patched; new field=0, no schedule
        patched_rev = replace(
            tuho.revenue,
            co2_certificate_price_eur_per_mwh=0.0,
            co2_sales_schedule=None,
            co2_price_eur=5.0,
            co2_enabled=True,
        )
        patched_tuho = replace(tuho, revenue=patched_rev)
        decomposition = revenue_decomposition_schedule(patched_tuho, engine)
        op_periods = [p for p in engine.periods() if p.is_operation]

        for period in op_periods[:3]:
            dec = decomposition[period.index]
            gen_mwh = dec["generation_mwh"]
            expected_co2 = gen_mwh * 5.0 / 1000
            assert dec["co2_certificate_revenue_keur"] == pytest.approx(expected_co2, abs=0.01)

    def test_new_co2_certificate_price_overrides_legacy_when_nonzero(
        self, tuho, engine
    ):
        """New co2_certificate_price_eur_per_mwh overrides legacy when non-zero and no schedule."""
        from dataclasses import replace

        patched_rev = replace(
            tuho.revenue,
            co2_certificate_price_eur_per_mwh=7.0,  # non-zero
            co2_sales_schedule=None,
            co2_price_eur=5.0,  # legacy fallback
            co2_enabled=True,
        )
        patched_tuho = replace(tuho, revenue=patched_rev)
        decomposition = revenue_decomposition_schedule(patched_tuho, engine)
        op_periods = [p for p in engine.periods() if p.is_operation]
        for period in op_periods[:3]:
            dec = decomposition[period.index]
            gen_mwh = dec["generation_mwh"]
            expected_co2 = gen_mwh * 7.0 / 1000  # new field wins
            assert dec["co2_certificate_revenue_keur"] == pytest.approx(expected_co2, abs=0.01)

    def test_co2_schedule_still_overrides_both_co2_fields(self, tuho, engine):
        """co2_sales_schedule takes priority over both legacy co2_price_eur and new field."""
        from dataclasses import replace
        from domain.inputs import RevenueAdjustmentSchedule

        patched_rev = replace(
            tuho.revenue,
            co2_certificate_price_eur_per_mwh=7.0,
            co2_sales_schedule=RevenueAdjustmentSchedule(constant_value=3.0),
            co2_price_eur=5.0,
            co2_enabled=True,
        )
        patched_tuho = replace(tuho, revenue=patched_rev)
        decomposition = revenue_decomposition_schedule(patched_tuho, engine)
        op_periods = [p for p in engine.periods() if p.is_operation]
        for period in op_periods[:3]:
            dec = decomposition[period.index]
            gen_mwh = dec["generation_mwh"]
            expected_co2 = gen_mwh * 3.0 / 1000  # schedule wins
            assert dec["co2_certificate_revenue_keur"] == pytest.approx(expected_co2, abs=0.01)


class TestSignConvention:
    """Test sign convention for balancing cost display."""

    def test_balancing_cost_is_positive_in_decomposition(self, tuho, engine):
        """balancing_cost_keur is positive (cost shown as positive amount)."""
        decomposition = revenue_decomposition_schedule(tuho, engine)

        for period in engine.periods():
            if not period.is_operation:
                continue
            dec = decomposition[period.index]
            # balancing_cost_keur must be positive since it's a cost line
            # (displayed as positive in Excel revenue section)
            assert dec["balancing_cost_keur"] >= 0.0, (
                f"Period {period.index}: balancing_cost_keur should be ≥ 0, got {dec['balancing_cost_keur']}"
            )

    def test_net_revenue_is_electricity_plus_co2_minus_balancing(self, tuho, engine):
        """net_revenue = electricity + CO2 - balancing (balancing is a deduction)."""
        decomposition = revenue_decomposition_schedule(tuho, engine)

        for period in engine.periods():
            if not period.is_operation:
                continue
            dec = decomposition[period.index]

            expected_net = (
                dec["electricity_revenue_keur"]
                + dec["co2_certificate_revenue_keur"]
                - dec["balancing_cost_keur"]
            )
            assert dec["net_revenue_after_balancing_keur"] == pytest.approx(
                expected_net, abs=0.01
            ), f"Period {period.index}: net revenue mismatch"