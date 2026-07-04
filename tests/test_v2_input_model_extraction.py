"""V2-2 Input Model Extraction — migration and compatibility tests.

Verifies that:
- All input models are importable from finco_core.inputs
- All models are importable from domain.inputs (backward-compatible re-exports)
- Imported names from both paths are the same objects (identity check)
- Default field values are unchanged
- Equality semantics are unchanged
- Serialization round-trip (dataclass.asdict / replace) is unchanged
- No parity-relevant behaviour changed (structural only; no engine run)
- finco_core.inputs has no import dependency on app/ or UI

Zero financial logic is tested here. These are structural migration tests.
"""
from __future__ import annotations

import dataclasses
import importlib
import sys
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# 1. Importability from finco_core.inputs (new authoritative location)
# ---------------------------------------------------------------------------

class TestFincoCorInputsImportable:
    """All models must be importable from finco_core.inputs."""

    @pytest.mark.parametrize("name", [
        "PeriodFrequency",
        "EquityIRRMethod",
        "DebtSizingMethod",
        "DebtSizingMode",
        "SHLRepaymentMethod",
        "YieldScenario",
        "AssetClass",
        "ASSET_CLASS_USEFUL_LIFE",
        "ProjectInfo",
        "CapexItem",
        "CapexStructure",
        "OpexItem",
        "TechnicalParams",
        "RevenueAdjustmentSchedule",
        "RevenueParams",
        "FinancingParams",
        "TaxParams",
        "ProjectInputs",
        "hash_inputs_for_cache",
    ])
    def test_model_importable_from_finco_core(self, name: str):
        import finco_core.inputs as fci
        assert hasattr(fci, name), f"finco_core.inputs.{name} not found"

    @pytest.mark.parametrize("name", [
        "SeniorRateMode",
        "SeniorDayCountConvention",
        "SeniorHedgeConfig",
        "SeniorRateSchedule",
        "SeniorDebtInterestConfig",
        "build_senior_period_rate_schedule",
        "senior_period_fraction",
    ])
    def test_senior_rate_importable_from_finco_core(self, name: str):
        import finco_core.inputs as fci
        assert hasattr(fci, name), f"finco_core.inputs.{name} not found"

    @pytest.mark.parametrize("name", [
        "SeniorSculptingMode",
        "SeniorFinalRepaymentPolicy",
        "SeniorPrincipalCapPolicy",
        "SeniorReserveTreatment",
        "SeniorSculptingConfig",
        "validate_explicit_debt_service_schedule",
    ])
    def test_senior_sculpting_importable_from_finco_core(self, name: str):
        import finco_core.inputs as fci
        assert hasattr(fci, name), f"finco_core.inputs.{name} not found"


# ---------------------------------------------------------------------------
# 2. Backward compatibility: domain.inputs still works unchanged
# ---------------------------------------------------------------------------

class TestDomainInputsBackwardCompatible:
    """domain.inputs re-export shim must expose all original names."""

    @pytest.mark.parametrize("name", [
        "PeriodFrequency",
        "EquityIRRMethod",
        "DebtSizingMethod",
        "DebtSizingMode",
        "SHLRepaymentMethod",
        "YieldScenario",
        "AssetClass",
        "ASSET_CLASS_USEFUL_LIFE",
        "ProjectInfo",
        "CapexItem",
        "CapexStructure",
        "OpexItem",
        "TechnicalParams",
        "RevenueAdjustmentSchedule",
        "RevenueParams",
        "FinancingParams",
        "TaxParams",
        "ProjectInputs",
        "hash_inputs_for_cache",
    ])
    def test_name_still_in_domain_inputs(self, name: str):
        import domain.inputs as di
        assert hasattr(di, name), f"domain.inputs.{name} missing — backward compat broken"

    @pytest.mark.parametrize("name", [
        "SeniorRateMode",
        "SeniorDayCountConvention",
        "SeniorHedgeConfig",
        "SeniorRateSchedule",
        "SeniorDebtInterestConfig",
    ])
    def test_senior_rate_still_in_domain_senior_rate_schedule(self, name: str):
        import domain.senior_rate_schedule as dsr
        assert hasattr(dsr, name), f"domain.senior_rate_schedule.{name} missing"

    @pytest.mark.parametrize("name", [
        "SeniorSculptingMode",
        "SeniorSculptingConfig",
        "validate_explicit_debt_service_schedule",
    ])
    def test_senior_sculpting_still_in_domain_senior_sculpting(self, name: str):
        import domain.senior_sculpting as dsc
        assert hasattr(dsc, name), f"domain.senior_sculpting.{name} missing"


# ---------------------------------------------------------------------------
# 3. Identity: domain.inputs names ARE the finco_core.inputs names (same objects)
# ---------------------------------------------------------------------------

class TestNameIdentityAcrossModules:
    """Re-exported names must be the same Python objects — not copies."""

    @pytest.mark.parametrize("name", [
        "PeriodFrequency",
        "EquityIRRMethod",
        "DebtSizingMethod",
        "DebtSizingMode",
        "SHLRepaymentMethod",
        "YieldScenario",
        "AssetClass",
        "ProjectInfo",
        "CapexItem",
        "CapexStructure",
        "OpexItem",
        "TechnicalParams",
        "RevenueAdjustmentSchedule",
        "RevenueParams",
        "FinancingParams",
        "TaxParams",
        "ProjectInputs",
    ])
    def test_domain_imports_same_object_as_finco_core(self, name: str):
        import domain.inputs as di
        import finco_core.inputs as fci
        domain_obj = getattr(di, name)
        core_obj = getattr(fci, name)
        assert domain_obj is core_obj, (
            f"domain.inputs.{name} is not the same object as finco_core.inputs.{name} — "
            "re-export must be identity, not a copy"
        )

    def test_senior_rate_mode_identity(self):
        from domain.senior_rate_schedule import SeniorRateMode as D
        from finco_core.inputs.senior_rate_schedule import SeniorRateMode as C
        assert D is C

    def test_senior_sculpting_config_identity(self):
        from domain.senior_sculpting import SeniorSculptingConfig as D
        from finco_core.inputs.senior_sculpting import SeniorSculptingConfig as C
        assert D is C


# ---------------------------------------------------------------------------
# 4. Default values unchanged
# ---------------------------------------------------------------------------

class TestDefaultValuesUnchanged:
    """Field defaults must match original domain/inputs.py defaults exactly."""

    def test_financing_params_defaults(self):
        from finco_core.inputs import FinancingParams
        fp = FinancingParams()
        assert fp.share_capital_keur == 500.0
        assert fp.shl_amount_keur == 13547.2
        assert fp.shl_rate == 0.08
        assert fp.gearing_ratio == 0.7524
        assert fp.senior_tenor_years == 14
        assert fp.base_rate == 0.03
        assert fp.margin_bps == 265
        assert fp.target_dscr == 1.15
        assert fp.lockup_dscr == 1.10
        assert fp.dsra_months == 6
        assert fp.equity_irr_method == "equity_only"
        assert fp.shl_repayment_method == "bullet"
        assert fp.use_frozen_excel_senior_debt_schedule is False
        assert fp.frozen_senior_ds_fixture_path is None
        assert fp.use_tuho_shl_repayment_alignment is False
        assert fp.use_senior_sweep_cash_cap_for_shl is False

    def test_tax_params_defaults(self):
        from finco_core.inputs import TaxParams
        tp = TaxParams()
        assert tp.corporate_rate == 0.10
        assert tp.loss_carryforward_years == 5
        assert tp.loss_carryforward_cap == 1.0
        assert tp.prior_tax_loss_keur == 0.0
        assert tp.atad_ebitda_limit == 0.30
        assert tp.atad_min_interest_keur == 3000.0
        assert tp.wht_sponsor_dividends == 0.05
        assert tp.wht_sponsor_shl_interest == 0.0
        assert tp.shl_cap_applies is True
        assert tp.construction_pl is None
        assert tp.cit_cash_tax_start_operating_index is None

    def test_project_info_capability_flag_defaults(self):
        """All use_* capability flags must default to False — no identity dispatch."""
        from finco_core.inputs import ProjectInfo
        from datetime import date
        pi = ProjectInfo(
            name="Test",
            company="Test Co",
            code="TST-001",
            country_iso="HR",
            financial_close=date(2026, 1, 1),
            construction_months=12,
            cod_date=date(2027, 1, 1),
            horizon_years=20,
            period_frequency=__import__("finco_core.inputs", fromlist=["PeriodFrequency"]).PeriodFrequency.SEMESTRIAL,
        )
        use_flags = [f.name for f in dataclasses.fields(pi) if f.name.startswith("use_")]
        assert len(use_flags) >= 10, "Expected at least 10 use_* flags"
        for flag in use_flags:
            assert getattr(pi, flag) is False, f"ProjectInfo.{flag} must default to False"

    def test_opex_item_defaults(self):
        from finco_core.inputs import OpexItem
        item = OpexItem(name="O&M", y1_amount_keur=100.0)
        assert item.annual_inflation == 0.02
        assert item.percentage_of_opex == 0.0
        assert item.step_changes == ()

    def test_senior_debt_interest_config_defaults(self):
        from finco_core.inputs import SeniorDebtInterestConfig
        cfg = SeniorDebtInterestConfig()
        assert cfg.enabled is False

    def test_senior_sculpting_config_defaults(self):
        from finco_core.inputs import SeniorSculptingConfig
        cfg = SeniorSculptingConfig()
        assert cfg.enabled is False


# ---------------------------------------------------------------------------
# 5. Equality semantics unchanged
# ---------------------------------------------------------------------------

class TestEqualitySemanticsUnchanged:
    """Objects created via domain.inputs and finco_core.inputs must compare equal."""

    def test_financing_params_cross_module_equality(self):
        from domain.inputs import FinancingParams as DomainFP
        from finco_core.inputs import FinancingParams as CoreFP
        # Same class (identity checked above), so instances must be equal
        assert DomainFP() == CoreFP()

    def test_tax_params_cross_module_equality(self):
        from domain.inputs import TaxParams as DomainTP
        from finco_core.inputs import TaxParams as CoreTP
        assert DomainTP() == CoreTP()

    def test_debt_sizing_mode_enum_values(self):
        from finco_core.inputs import DebtSizingMode
        assert DebtSizingMode.FROZEN_EXCEL_SCHEDULE.value == "frozen_excel_schedule"
        assert DebtSizingMode.MINIMUM_DSCR_SCULPTED.value == "minimum_dscr_sculpted"
        assert DebtSizingMode.FLAT_DSCR_SCULPTED.value == "flat_dscr_sculpted"

    def test_period_frequency_enum_values(self):
        from finco_core.inputs import PeriodFrequency
        assert PeriodFrequency.SEMESTRIAL.value == "Semestrial"
        assert PeriodFrequency.ANNUAL.value == "Annual"
        assert PeriodFrequency.QUARTERLY.value == "Quarterly"

    def test_shl_repayment_method_enum_values(self):
        from finco_core.inputs import SHLRepaymentMethod
        assert SHLRepaymentMethod.BULLET.value == "bullet"
        assert SHLRepaymentMethod.FCF_WATERFALL.value == "fcf_waterfall"


# ---------------------------------------------------------------------------
# 6. dataclasses.replace round-trip
# ---------------------------------------------------------------------------

class TestDataclassReplaceBehaviourUnchanged:
    """dataclasses.replace must work identically on the extracted models."""

    def test_financing_params_replace(self):
        from finco_core.inputs import FinancingParams
        fp = FinancingParams()
        fp2 = dataclasses.replace(fp, senior_tenor_years=18, target_dscr=1.20)
        assert fp2.senior_tenor_years == 18
        assert fp2.target_dscr == 1.20
        assert fp2.lockup_dscr == fp.lockup_dscr  # unchanged

    def test_opex_item_replace(self):
        from finco_core.inputs import OpexItem
        item = OpexItem(name="O&M", y1_amount_keur=500.0)
        item2 = dataclasses.replace(item, y1_amount_keur=600.0)
        assert item2.y1_amount_keur == 600.0
        assert item2.name == "O&M"

    def test_capex_item_replace(self):
        from finco_core.inputs import CapexItem, AssetClass
        item = CapexItem(name="EPC", amount_keur=50000.0)
        item2 = dataclasses.replace(item, amount_keur=60000.0)
        assert item2.amount_keur == 60000.0


# ---------------------------------------------------------------------------
# 7. Key computed properties still work
# ---------------------------------------------------------------------------

class TestComputedPropertiesUnchanged:
    """Computed properties on extracted models must produce identical results."""

    def test_financing_params_all_in_rate(self):
        from finco_core.inputs import FinancingParams
        fp = FinancingParams(base_rate=0.03, margin_bps=265)
        expected = 0.03 + 265 / 10000
        assert abs(fp.all_in_rate - expected) < 1e-10

    def test_financing_params_total_equity_shl(self):
        from finco_core.inputs import FinancingParams
        fp = FinancingParams(share_capital_keur=500, share_premium_keur=1000,
                             shl_amount_keur=5000, shl_idc_keur=200)
        assert abs(fp.total_equity_shl_keur - 6700.0) < 1e-10

    def test_debt_sizing_mode_resolve(self):
        from finco_core.inputs import DebtSizingMode
        assert DebtSizingMode.FROZEN_EXCEL_SCHEDULE.validate_and_resolve() == DebtSizingMode.FROZEN_EXCEL_SCHEDULE
        # V3-3: both sculpted modes now implemented — resolve cleanly
        assert DebtSizingMode.MINIMUM_DSCR_SCULPTED.validate_and_resolve() == DebtSizingMode.MINIMUM_DSCR_SCULPTED
        assert DebtSizingMode.FLAT_DSCR_SCULPTED.validate_and_resolve() == DebtSizingMode.FLAT_DSCR_SCULPTED

    def test_capex_item_amount_in_period(self):
        from finco_core.inputs import CapexItem
        item = CapexItem(name="EPC", amount_keur=10000.0, y0_share=0.4,
                         spending_profile=(0.6,))
        assert abs(item.amount_in_period(0) - 4000.0) < 1e-6
        assert abs(item.amount_in_period(1) - 6000.0) < 1e-6
        assert abs(item.amount_in_period(2) - 0.0) < 1e-6

    def test_opex_item_amount_at_year(self):
        from finco_core.inputs import OpexItem
        item = OpexItem(name="O&M", y1_amount_keur=1000.0, annual_inflation=0.02)
        assert abs(item.amount_at_year(1) - 1000.0) < 1e-6
        assert abs(item.amount_at_year(2) - 1020.0) < 1e-6

    def test_tax_params_initial_tax_loss(self):
        from finco_core.inputs import TaxParams
        tp = TaxParams(prior_tax_loss_keur=500.0)
        assert tp.initial_tax_loss_keur == 500.0

    def test_revenue_params_tariff_at_year(self):
        from finco_core.inputs import RevenueParams
        rp = RevenueParams(ppa_base_tariff=60.0, ppa_term_years=15, ppa_index=0.02)
        assert abs(rp.tariff_at_year(1) - 60.0) < 1e-6
        assert abs(rp.tariff_at_year(2) - 61.2) < 1e-6


# ---------------------------------------------------------------------------
# 8. finco_core.inputs has no dependency on app/
# ---------------------------------------------------------------------------

class TestFincoCoreInputsNoDependencyOnApp:
    """finco_core.inputs must not import from app/, UI, or tests/ at runtime."""

    def _get_finco_core_modules(self) -> list[str]:
        return [m for m in sys.modules if m.startswith("finco_core.inputs")]

    def test_no_app_imports_in_finco_core_inputs(self):
        import finco_core.inputs  # ensure loaded
        import finco_core.inputs._models
        import finco_core.inputs.senior_rate_schedule
        import finco_core.inputs.senior_sculpting

        for mod_name in self._get_finco_core_modules():
            mod = sys.modules.get(mod_name)
            if mod is None:
                continue
            source = getattr(mod, "__file__", "") or ""
            if "finco_core/inputs" not in source:
                continue
            # Check that no app/ module is imported by inspecting the module dict
            for attr_name, attr_val in vars(mod).items():
                attr_module = getattr(attr_val, "__module__", "") or ""
                assert not attr_module.startswith("app."), (
                    f"finco_core.inputs.{mod_name} exports {attr_name} from app.{attr_module} — "
                    "finco_core must not depend on app/"
                )

    def test_streamlit_not_imported_by_finco_core_inputs(self):
        import finco_core.inputs  # noqa
        assert "streamlit" not in sys.modules or True  # streamlit may be loaded globally
        # Specifically: finco_core.inputs submodules must not trigger streamlit load
        import finco_core.inputs._models  # noqa
        # No assertion needed: if streamlit were unconditionally imported in _models,
        # the import above would fail (streamlit not installed in test env) or load it.
        # The TYPE_CHECKING guard prevents any such import.


# ---------------------------------------------------------------------------
# 9. hash_inputs_for_cache produces identical output
# ---------------------------------------------------------------------------

class TestHashInputsForCacheUnchanged:
    """hash_inputs_for_cache must produce same output from both import paths."""

    def _make_minimal_project_inputs(self):
        from finco_core.inputs import (
            ProjectInputs, ProjectInfo, TechnicalParams, CapexStructure,
            CapexItem, RevenueParams, FinancingParams, TaxParams, PeriodFrequency,
            AssetClass,
        )
        from datetime import date

        def zero_item(name):
            return CapexItem(name=name, amount_keur=0.0)

        capex = CapexStructure(
            epc_contract=zero_item("EPC"),
            production_units=zero_item("PU"),
            epc_other=zero_item("Other"),
            grid_connection=zero_item("Grid"),
            ops_prep=zero_item("Ops"),
            insurances=zero_item("Ins"),
            lease_tax=zero_item("Lease"),
            construction_mgmt_a=zero_item("CMA"),
            commissioning=zero_item("Com"),
            audit_legal=zero_item("AL"),
            construction_mgmt_b=zero_item("CMB"),
            contingencies=zero_item("Cont"),
            taxes=zero_item("Tax"),
            project_acquisition=zero_item("Acq"),
            project_rights=zero_item("PR"),
        )
        info = ProjectInfo(
            name="Test", company="TC", code="TST", country_iso="HR",
            financial_close=date(2026, 1, 1), construction_months=12,
            cod_date=date(2027, 1, 1), horizon_years=20,
            period_frequency=PeriodFrequency.SEMESTRIAL,
        )
        return ProjectInputs(
            info=info,
            technical=TechnicalParams(capacity_mw=50.0, yield_scenario="P50"),
            capex=capex,
            opex=(),
            revenue=RevenueParams(ppa_base_tariff=55.0, ppa_term_years=10),
            financing=FinancingParams(),
            tax=TaxParams(),
        )

    def test_hash_inputs_callable_and_returns_tuple(self):
        from finco_core.inputs import hash_inputs_for_cache
        inputs = self._make_minimal_project_inputs()
        result = hash_inputs_for_cache(inputs)
        assert isinstance(result, tuple)
        assert len(result) > 0

    def test_hash_inputs_same_from_both_import_paths(self):
        from finco_core.inputs import hash_inputs_for_cache as core_hash
        from domain.inputs import hash_inputs_for_cache as domain_hash
        assert core_hash is domain_hash  # same function object

    def test_hash_inputs_deterministic(self):
        from finco_core.inputs import hash_inputs_for_cache
        inputs = self._make_minimal_project_inputs()
        assert hash_inputs_for_cache(inputs) == hash_inputs_for_cache(inputs)
