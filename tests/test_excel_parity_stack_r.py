"""Stack R: Factory Configuration Fidelity — fresh-run = saved-run equivalence.

Root cause confirmed in DD validation (R3):
  _execute_template_seeded_path() rebuilt ProjectInputs from
  create_default_wind_project() (generic) using only ~11 scalar values,
  silently losing ~20+ calibrated fields: SHL configuration,
  equity_irr_method, market_prices_curve, CO2 schedule, tax params,
  frozen DS schedule, detailed CAPEX/OPEX structure, etc.

Fix (Stack R):
  build_projectinputs_seeded() in input_adapter.py starts from the
  project-specific factory (create_default_tuho_wind1 / create_default_oborovo)
  and applies only the schema's non-None scalar overrides on top.
  _get_seed_base_inputs() in run_service.py selects the correct base
  for runtime_seed == "tuho" / "oborovo".

No engine changes. No parity numbers move.
"""
from __future__ import annotations
import os
import sys
import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.project_factories import create_default_tuho_wind1, create_default_oborovo
from app.input_adapter import build_projectinputs_seeded
from app.input_schema import ProjectInputsSchema, DebtInput, RevenueInput, CapexInput, OpexInput
from app.ui_runner import run_demo_project


# ── Shared helpers ──────────────────────────────────────────────────────────

def _seeded_run(project_key: str, schema: ProjectInputsSchema):
    """Simulate the Stack R fresh-path: seeded factory base + schema overrides."""
    if project_key == "TUHO":
        base = create_default_tuho_wind1()
    else:
        base = create_default_oborovo()
    pi = build_projectinputs_seeded(schema, base)
    return run_demo_project(project_key, project_inputs_override=pi)


# ── Module-scoped fixtures ──────────────────────────────────────────────────

@pytest.fixture(scope="module")
def tuho_factory():
    """Direct factory run — the authoritative reference for TUHO."""
    return run_demo_project("TUHO")


@pytest.fixture(scope="module")
def oborovo_factory():
    """Direct factory run — the authoritative reference for Oborovo."""
    return run_demo_project("Oborovo")


@pytest.fixture(scope="module")
def tuho_seeded():
    """Stack R fresh-path with no scalar overrides — must match factory."""
    schema = ProjectInputsSchema(project_type="Wind", scenario="Base")
    return _seeded_run("TUHO", schema)


@pytest.fixture(scope="module")
def oborovo_seeded():
    """Stack R fresh-path with no scalar overrides — must match factory."""
    schema = ProjectInputsSchema(project_type="Solar", scenario="Base")
    return _seeded_run("Oborovo", schema)


# ── R1: TUHO — ProjectInputs field parity (calibrated config preserved) ────

class TestTUHOConfigPreserved:
    """Fresh-path TUHO ProjectInputs must retain all calibrated fields."""

    def test_equity_irr_method(self, tuho_seeded, tuho_factory):
        assert tuho_seeded.project_inputs.financing.equity_irr_method == \
               tuho_factory.project_inputs.financing.equity_irr_method

    def test_shl_repayment_method(self, tuho_seeded, tuho_factory):
        assert tuho_seeded.project_inputs.financing.shl_repayment_method == \
               tuho_factory.project_inputs.financing.shl_repayment_method == "pik_then_sweep"

    def test_debt_sizing_method(self, tuho_seeded, tuho_factory):
        assert tuho_seeded.project_inputs.financing.debt_sizing_method == \
               tuho_factory.project_inputs.financing.debt_sizing_method == "fixed"

    def test_use_frozen_excel_senior_debt_schedule(self, tuho_seeded, tuho_factory):
        assert tuho_seeded.project_inputs.financing.use_frozen_excel_senior_debt_schedule is True
        assert tuho_factory.project_inputs.financing.use_frozen_excel_senior_debt_schedule is True

    def test_shl_amount_keur(self, tuho_seeded, tuho_factory):
        assert abs(tuho_seeded.project_inputs.financing.shl_amount_keur -
                   tuho_factory.project_inputs.financing.shl_amount_keur) < 1.0

    def test_shl_rate(self, tuho_seeded, tuho_factory):
        assert abs(tuho_seeded.project_inputs.financing.shl_rate -
                   tuho_factory.project_inputs.financing.shl_rate) < 0.0001

    def test_prior_tax_loss_keur(self, tuho_seeded, tuho_factory):
        assert abs(tuho_seeded.project_inputs.tax.prior_tax_loss_keur -
                   tuho_factory.project_inputs.tax.prior_tax_loss_keur) < 1.0

    def test_corporate_rate(self, tuho_seeded, tuho_factory):
        assert abs(tuho_seeded.project_inputs.tax.corporate_rate -
                   tuho_factory.project_inputs.tax.corporate_rate) < 0.001

    def test_market_prices_curve_preserved(self, tuho_seeded, tuho_factory):
        assert tuho_seeded.project_inputs.revenue.market_prices_curve == \
               tuho_factory.project_inputs.revenue.market_prices_curve

    def test_dscr_schedule_preserved(self, tuho_seeded, tuho_factory):
        assert tuho_seeded.project_inputs.financing.dscr_schedule == \
               tuho_factory.project_inputs.financing.dscr_schedule

    def test_capex_idc_preserved(self, tuho_seeded, tuho_factory):
        """IDC must come from factory (1519.56 kEUR), not zeroed by generic path."""
        assert abs(tuho_seeded.project_inputs.capex.idc_keur -
                   tuho_factory.project_inputs.capex.idc_keur) < 1.0
        assert tuho_seeded.project_inputs.capex.idc_keur > 1000.0  # generic zeroes this


# ── R2: Oborovo — ProjectInputs field parity ────────────────────────────────

class TestOborovoConfigPreserved:
    """Fresh-path Oborovo ProjectInputs must retain all calibrated fields."""

    def test_equity_irr_method(self, oborovo_seeded, oborovo_factory):
        assert oborovo_seeded.project_inputs.financing.equity_irr_method == \
               oborovo_factory.project_inputs.financing.equity_irr_method == "shl_plus_dividends"

    def test_use_frozen_excel_senior_debt_schedule(self, oborovo_seeded, oborovo_factory):
        assert oborovo_seeded.project_inputs.financing.use_frozen_excel_senior_debt_schedule is True
        assert oborovo_factory.project_inputs.financing.use_frozen_excel_senior_debt_schedule is True

    def test_co2_enabled(self, oborovo_seeded, oborovo_factory):
        assert oborovo_seeded.project_inputs.revenue.co2_enabled is True
        assert oborovo_factory.project_inputs.revenue.co2_enabled is True

    def test_market_prices_curve_preserved(self, oborovo_seeded, oborovo_factory):
        assert oborovo_seeded.project_inputs.revenue.market_prices_curve == \
               oborovo_factory.project_inputs.revenue.market_prices_curve

    def test_corporate_rate(self, oborovo_seeded, oborovo_factory):
        assert abs(oborovo_seeded.project_inputs.tax.corporate_rate -
                   oborovo_factory.project_inputs.tax.corporate_rate) < 0.001

    def test_shl_amount_keur(self, oborovo_seeded, oborovo_factory):
        assert abs(oborovo_seeded.project_inputs.financing.shl_amount_keur -
                   oborovo_factory.project_inputs.financing.shl_amount_keur) < 1.0

    def test_fixed_debt_keur_preserved(self, oborovo_seeded, oborovo_factory):
        assert abs(oborovo_seeded.project_inputs.financing.fixed_debt_keur -
                   oborovo_factory.project_inputs.financing.fixed_debt_keur) < 1.0

    def test_co2_sales_schedule_preserved(self, oborovo_seeded, oborovo_factory):
        factory_co2 = oborovo_factory.project_inputs.revenue.co2_sales_schedule
        seeded_co2 = oborovo_seeded.project_inputs.revenue.co2_sales_schedule
        assert seeded_co2 == factory_co2


# ── R3: KPI equivalence — fresh path == factory path ────────────────────────

class TestTUHOKPIEquivalence:
    """TUHO fresh-path KPIs must be bit-identical to factory-path KPIs."""

    def test_equity_irr_exact(self, tuho_seeded, tuho_factory):
        assert abs(tuho_seeded.result.equity_irr - tuho_factory.result.equity_irr) < 1e-9, (
            f"equity_irr: seeded={tuho_seeded.result.equity_irr:.6f} "
            f"factory={tuho_factory.result.equity_irr:.6f}"
        )

    def test_project_irr_exact(self, tuho_seeded, tuho_factory):
        assert abs(tuho_seeded.result.project_irr - tuho_factory.result.project_irr) < 1e-9

    def test_avg_dscr_exact(self, tuho_seeded, tuho_factory):
        assert abs(tuho_seeded.result.actual_avg_dscr - tuho_factory.result.actual_avg_dscr) < 1e-9

    def test_senior_debt_exact(self, tuho_seeded, tuho_factory):
        assert abs(tuho_seeded.result.sculpting_result.debt_keur -
                   tuho_factory.result.sculpting_result.debt_keur) < 0.01

    def test_shl_opening_balance_exact(self, tuho_seeded, tuho_factory):
        seeded_shl = tuho_seeded.result.periods[0].shl_balance_keur
        factory_shl = tuho_factory.result.periods[0].shl_balance_keur
        assert abs(seeded_shl - factory_shl) < 0.01, (
            f"SHL opening: seeded={seeded_shl:.1f} factory={factory_shl:.1f}"
        )

    def test_total_distributions_exact(self, tuho_seeded, tuho_factory):
        assert abs(tuho_seeded.result.total_distribution_keur -
                   tuho_factory.result.total_distribution_keur) < 0.01

    def test_total_tax_exact(self, tuho_seeded, tuho_factory):
        assert abs(tuho_seeded.result.total_tax_keur -
                   tuho_factory.result.total_tax_keur) < 0.01


class TestOborovoKPIEquivalence:
    """Oborovo fresh-path KPIs must be bit-identical to factory-path KPIs."""

    def test_equity_irr_exact(self, oborovo_seeded, oborovo_factory):
        assert abs(oborovo_seeded.result.equity_irr - oborovo_factory.result.equity_irr) < 1e-9, (
            f"equity_irr: seeded={oborovo_seeded.result.equity_irr:.6f} "
            f"factory={oborovo_factory.result.equity_irr:.6f}"
        )

    def test_project_irr_exact(self, oborovo_seeded, oborovo_factory):
        assert abs(oborovo_seeded.result.project_irr - oborovo_factory.result.project_irr) < 1e-9

    def test_avg_dscr_exact(self, oborovo_seeded, oborovo_factory):
        assert abs(oborovo_seeded.result.actual_avg_dscr -
                   oborovo_factory.result.actual_avg_dscr) < 1e-9

    def test_senior_debt_exact(self, oborovo_seeded, oborovo_factory):
        assert abs(oborovo_seeded.result.sculpting_result.debt_keur -
                   oborovo_factory.result.sculpting_result.debt_keur) < 0.01

    def test_total_distributions_exact(self, oborovo_seeded, oborovo_factory):
        assert abs(oborovo_seeded.result.total_distribution_keur -
                   oborovo_factory.result.total_distribution_keur) < 0.01

    def test_total_tax_exact(self, oborovo_seeded, oborovo_factory):
        assert abs(oborovo_seeded.result.total_tax_keur -
                   oborovo_factory.result.total_tax_keur) < 0.01


# ── R4: Calibrated fields survive — explicit named verification ──────────────

class TestCalibratedFieldSurvival:
    """Named-field regression: every field from the Stack R scope must survive."""

    def test_tuho_equity_irr_method_value(self, tuho_seeded):
        assert tuho_seeded.project_inputs.financing.equity_irr_method == "shl_plus_dividends"

    def test_tuho_shl_repayment_method_value(self, tuho_seeded):
        assert tuho_seeded.project_inputs.financing.shl_repayment_method == "pik_then_sweep"

    def test_tuho_use_frozen_excel_senior_debt_schedule_value(self, tuho_seeded):
        assert tuho_seeded.project_inputs.financing.use_frozen_excel_senior_debt_schedule is True

    def test_tuho_prior_tax_loss_keur_value(self, tuho_seeded):
        assert abs(tuho_seeded.project_inputs.tax.prior_tax_loss_keur - 25000.0) < 1.0

    def test_tuho_market_prices_curve_length(self, tuho_seeded):
        curve = tuho_seeded.project_inputs.revenue.market_prices_curve
        assert curve is not None and len(curve) == 30

    def test_tuho_tax_rate(self, tuho_seeded):
        assert abs(tuho_seeded.project_inputs.tax.corporate_rate - 0.18) < 0.001

    def test_tuho_shl_amount_keur_value(self, tuho_seeded):
        assert abs(tuho_seeded.project_inputs.financing.shl_amount_keur - 29135.0) < 1.0

    def test_tuho_shl_rate_value(self, tuho_seeded):
        assert abs(tuho_seeded.project_inputs.financing.shl_rate - 0.0793) < 0.0001

    def test_oborovo_equity_irr_method_value(self, oborovo_seeded):
        assert oborovo_seeded.project_inputs.financing.equity_irr_method == "shl_plus_dividends"

    def test_oborovo_use_frozen_excel_senior_debt_schedule_value(self, oborovo_seeded):
        assert oborovo_seeded.project_inputs.financing.use_frozen_excel_senior_debt_schedule is True

    def test_oborovo_co2_enabled_value(self, oborovo_seeded):
        assert oborovo_seeded.project_inputs.revenue.co2_enabled is True

    def test_oborovo_market_prices_curve_length(self, oborovo_seeded):
        curve = oborovo_seeded.project_inputs.revenue.market_prices_curve
        assert curve is not None and len(curve) > 0

    def test_oborovo_corporate_rate(self, oborovo_seeded):
        assert abs(oborovo_seeded.project_inputs.tax.corporate_rate - 0.10) < 0.001


# ── R5: Scalar overrides still work ─────────────────────────────────────────

class TestScalarOverridesWork:
    """User-editable scalars must still propagate correctly on the seeded path."""

    def test_capacity_override_tuho(self):
        schema = ProjectInputsSchema(project_type="Wind", scenario="Base", capacity_mw=40.0)
        result = _seeded_run("TUHO", schema)
        assert abs(result.project_inputs.technical.capacity_mw - 40.0) < 0.01

    def test_tariff_override_tuho(self):
        schema = ProjectInputsSchema(
            project_type="Wind", scenario="Base",
            revenue=RevenueInput(tariff_eur_mwh=70.0),
        )
        result = _seeded_run("TUHO", schema)
        assert abs(result.project_inputs.revenue.ppa_base_tariff - 70.0) < 0.01

    def test_tenor_override_tuho(self):
        schema = ProjectInputsSchema(
            project_type="Wind", scenario="Base",
            debt=DebtInput(tenor_years=12),
        )
        result = _seeded_run("TUHO", schema)
        assert result.project_inputs.financing.senior_tenor_years == 12

    def test_capacity_override_oborovo(self):
        schema = ProjectInputsSchema(project_type="Solar", scenario="Base", capacity_mw=80.0)
        result = _seeded_run("Oborovo", schema)
        assert abs(result.project_inputs.technical.capacity_mw - 80.0) < 0.01

    def test_tariff_override_oborovo(self):
        schema = ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            revenue=RevenueInput(tariff_eur_mwh=55.0),
        )
        result = _seeded_run("Oborovo", schema)
        assert abs(result.project_inputs.revenue.ppa_base_tariff - 55.0) < 0.01

    def test_opex_override_replaces_items(self):
        """When opex_y1_keur is supplied, OPEX is replaced with the single scalar line."""
        schema = ProjectInputsSchema(
            project_type="Wind", scenario="Base",
            opex=OpexInput(opex_y1_keur=2500.0),
        )
        result = _seeded_run("TUHO", schema)
        total_opex = sum(item.y1_amount_keur for item in result.project_inputs.opex)
        assert abs(total_opex - 2500.0) < 1.0

    def test_capex_override_resizes_epc(self):
        """When total_capex_keur is supplied, financial sub-fields are zeroed and EPC resized."""
        schema = ProjectInputsSchema(
            project_type="Wind", scenario="Base",
            capex=CapexInput(total_capex_keur=60000.0),
        )
        result = _seeded_run("TUHO", schema)
        assert abs(result.project_inputs.capex.total_capex - 60000.0) < 100.0
        # financial sub-fields are zeroed when capex total is overridden
        assert result.project_inputs.capex.idc_keur == 0.0

    def test_calibrated_fields_survive_alongside_scalar_override(self):
        """Overriding capacity must not disturb SHL config or equity_irr_method."""
        schema = ProjectInputsSchema(project_type="Wind", scenario="Base", capacity_mw=40.0)
        result = _seeded_run("TUHO", schema)
        assert result.project_inputs.financing.equity_irr_method == "shl_plus_dividends"
        assert result.project_inputs.financing.shl_repayment_method == "pik_then_sweep"
        assert result.project_inputs.financing.use_frozen_excel_senior_debt_schedule is True


# ── R6: All Stack K–Q parity tests remain green ─────────────────────────────

class TestGoldenParityUnchanged:
    """Core parity KPIs must be exactly unchanged from Stack Q baseline."""

    @pytest.fixture(scope="class")
    def tuho(self, tuho_factory):
        return tuho_factory.result

    @pytest.fixture(scope="class")
    def oborovo(self, oborovo_factory):
        return oborovo_factory.result

    def test_tuho_equity_irr(self, tuho):
        assert abs(tuho.equity_irr - 0.1159) < 0.0005

    def test_tuho_project_irr(self, tuho):
        assert abs(tuho.project_irr - 0.0941) < 0.0005

    def test_tuho_avg_dscr(self, tuho):
        assert abs(tuho.actual_avg_dscr - 1.3786) < 0.001

    def test_tuho_senior_debt(self, tuho):
        assert abs(tuho.sculpting_result.debt_keur - 43359.0) < 1.0

    def test_oborovo_equity_irr(self, oborovo):
        assert abs(oborovo.equity_irr - 0.1066) < 0.0005

    def test_oborovo_project_irr(self, oborovo):
        assert abs(oborovo.project_irr - 0.0809) < 0.0005

    def test_oborovo_avg_dscr(self, oborovo):
        assert abs(oborovo.actual_avg_dscr - 1.179) < 0.005

    def test_oborovo_senior_debt(self, oborovo):
        assert abs(oborovo.sculpting_result.debt_keur - 42852.0) < 5.0
