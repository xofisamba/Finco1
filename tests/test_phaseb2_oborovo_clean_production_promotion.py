from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.project_factories import (
    create_default_oborovo,
    create_default_oborovo_legacy_calibration,
    create_default_tuho_wind1,
)
from app.services.production_financial_authority import (
    ProductionAuthorityClassification,
    classify_production_authority,
)
from financial_engine.construction.adapter import (
    build_construction_runtime_config,
    resolve_capex_amounts_from_capex_structure,
)
from financial_engine.financing.project import run_project_financing_model
from finco_core.construction import (
    FundingShortfallError,
    compute_vat_schedule,
    run_stage_b2,
    vat_monthly_uses,
)
from finco_core.inputs import (
    ConstructionCapexTimingInput,
    ConstructionFinancingInput,
    ConstructionPeriodSpec,
    ConstructionSeniorPricingInput,
    ConstructionVatFacilityInput,
    GearingBasisMode,
    SponsorFundingMode,
    VatFacilityCommitmentMode,
    project_inputs_from_dict,
    project_inputs_to_dict,
)
from finco_core.inputs.senior_rate_schedule import (
    SeniorDayCountConvention,
    SeniorRateMode,
)


@pytest.fixture(scope="module")
def oborovo_financing():
    return run_project_financing_model(
        create_default_oborovo(), source_id="phase_b2_acceptance"
    )


def test_oborovo_promotes_naturally_from_typed_inputs():
    project = create_default_oborovo()
    decision = classify_production_authority(project)

    assert decision.classification is ProductionAuthorityClassification.CLEAN_PRODUCTION_READY
    assert project.financing.sponsor_funding_mode is SponsorFundingMode.SHARE_CAPITAL_THEN_SHL
    assert project.financing.gearing_basis_mode is GearingBasisMode.TOTAL_PROJECT_USES
    assert project.financing.use_frozen_excel_senior_debt_schedule is False
    assert project.financing.frozen_senior_ds_fixture_path is None
    assert project.financing.construction_financing.enabled is True
    assert project.financing.construction_financing.vat_facility.enabled is True
    vat_items = project.financing.construction_financing.capex_items
    assert {item.code for item in vat_items if item.vat_rate == 0.17} == {
        "epc_contract",
        "epc_other",
        "grid_connection",
        "ops_prep",
        "audit_legal",
        "insurances",
        "lease_tax",
        "construction_mgmt_a",
        "contingencies",
        "project_rights",
        "commissioning",
        "project_acquisition",
    }
    assert {item.code for item in vat_items if item.vat_rate == 0.0} == {
        "production_units"
    }


def test_clean_snapshot_has_no_manual_derived_construction_cost_authority():
    project = create_default_oborovo()
    assert {
        project.capex.idc_keur,
        project.capex.commitment_fees_keur,
        project.capex.bank_fees_keur,
        project.capex.vat_costs_keur,
        project.capex.vat_facility_idc_keur,
        project.capex.vat_facility_commitment_fee_keur,
        project.financing.shl_idc_keur,
    } == {0.0}


def test_sponsor_funding_and_total_uses_gearing_identity(oborovo_financing):
    result = oborovo_financing
    assert result.binding_senior_constraint == "DSCR"
    assert result.gearing_basis_keur == pytest.approx(
        result.project_uses.total_project_uses_keur, abs=1e-9
    )
    assert result.final_senior_commitment_keur + result.share_capital_keur + result.derived_shl_cash_principal_keur == pytest.approx(
        result.project_uses.total_project_uses_keur, abs=1e-7
    )
    assert result.gearing_debt_capacity_keur > result.final_senior_commitment_keur


def test_oborovo_typed_construction_and_vat_audit(oborovo_financing):
    result = oborovo_financing
    construction = result.construction_financing

    assert construction.authority == "PR9_TYPED_CONSTRUCTION_FINANCING_IDC_AUTHORITY"
    assert construction.vat_authority == "TYPED_CONSTRUCTION_VAT_FACILITY_AUTHORITY"
    assert construction.vat_commitment_mode == "DERIVED_PEAK_REQUIREMENT"
    assert construction.vat_effective_commitment_keur == pytest.approx(
        construction.vat_peak_requirement_keur, abs=1e-9
    )
    assert construction.vat_peak_requirement_period == 6
    assert sum(construction.vat_payable_keur) == pytest.approx(7664.685535, abs=1e-9)
    assert construction.final_total_project_uses_keur == pytest.approx(57973.042280034315, abs=1e-6)
    assert construction.final_senior_commitment_keur == pytest.approx(42852.302723344226, abs=1e-6)
    assert sum(construction.senior_idc_accrual_keur) == pytest.approx(1086.0191130858313, abs=1e-6)
    assert sum(construction.senior_commitment_fee_accrual_keur) == pytest.approx(188.56540868282153, abs=1e-6)
    assert sum(construction.structuring_fee_keur) == pytest.approx(477.302687, abs=1e-9)
    assert construction.vat_idc_keur == pytest.approx(208.44761845456716, abs=1e-9)
    assert construction.vat_commitment_fee_keur == pytest.approx(13.6219528108125, abs=1e-9)
    assert max(construction.vat_requirement_keur) == pytest.approx(4877.989945, abs=1e-9)
    assert construction.vat_requirement_keur[-1] == pytest.approx(0.0, abs=1e-9)
    assert construction.maximum_period_residual_keur == pytest.approx(0.0, abs=1e-9)
    assert construction.maximum_cumulative_residual_keur == pytest.approx(0.0, abs=1e-9)
    assert construction.stage_b2_iterations == 7


def test_typed_date_derived_shl_construction_dcf_is_source_one():
    financing = create_default_oborovo().financing
    periods = (
        financing.construction_financing.periods
        + financing.construction_financing.shl_accrual_tail_periods
    )
    actual_days = sum((period.end_date - period.start_date).days + 1 for period in periods)

    assert actual_days == 365
    assert actual_days / 365.0 == pytest.approx(
        financing.shl_construction_day_count_fraction, abs=1e-12
    )


def _periods(n: int, *, vat_active: bool) -> tuple[ConstructionPeriodSpec, ...]:
    rows = []
    y, m = 2035, 1
    for _ in range(n):
        if m == 12:
            next_y, next_m = y + 1, 1
        else:
            next_y, next_m = y, m + 1
        next_start = date(next_y, next_m, 1)
        rows.append(ConstructionPeriodSpec(
            start_date=date(y, m, 1),
            end_date=next_start - timedelta(days=1),
            vat_facility_active=vat_active,
        ))
        y, m = next_y, next_m
    return tuple(rows)


def _synthetic_vat_result(
    *,
    n: int,
    vat_rate: float,
    facility_rate: float,
    fee_rate: float = 0.0,
    enabled: bool = True,
    reimbursement_lag: int = 2,
    taxable_amount: float = 1_000.0,
    exempt_amount: float = 250.0,
    exempt_vat_rate: float = 0.0,
    taxable_weights: tuple[float, ...] | None = None,
    commitment_mode: VatFacilityCommitmentMode = (
        VatFacilityCommitmentMode.DERIVED_PEAK_REQUIREMENT
    ),
    fixed_commitment_keur: float | None = None,
):
    construction_periods = _periods(n, vat_active=enabled)
    facility_periods = _periods(n + reimbursement_lag, vat_active=enabled)
    taxable_weights = taxable_weights or (1 / n,) * n
    input_contract = ConstructionFinancingInput(
        enabled=True,
        periods=construction_periods,
        capex_items=(
            ConstructionCapexTimingInput("taxable", "Taxable", taxable_weights, vat_rate),
            ConstructionCapexTimingInput("exempt", "Exempt", (1 / n,) * n, exempt_vat_rate),
        ),
        senior_pricing=ConstructionSeniorPricingInput(
            mode=SeniorRateMode.FLAT_ALL_IN,
            flat_all_in_rate=0.0,
            day_count=SeniorDayCountConvention.ACT_360,
        ),
        vat_facility=ConstructionVatFacilityInput(
            enabled=enabled,
            commitment_mode=commitment_mode,
            fixed_commitment_keur=fixed_commitment_keur if enabled else None,
            interest_rate=facility_rate if enabled else 0.0,
            commitment_fee_rate=fee_rate if enabled else 0.0,
            periods=facility_periods if enabled else (),
            reimbursement_lag_periods=reimbursement_lag,
            commitment_fee_active_periods=n if enabled else 0,
            financing_cost_payment_weights=(
                (1.0,) + (0.0,) * (n - 1) if enabled else ()
            ),
        ),
    )
    config = build_construction_runtime_config(
        input_contract,
        senior_commitment_keur=2_000.0,
        equity_available_keur=0.0,
        shl_available_keur=0.0,
        capex_amounts_keur={"taxable": taxable_amount, "exempt": exempt_amount},
    )
    return run_stage_b2(config)


def test_generic_vat_synthetic_a_is_causal_and_rate_directional():
    zero = _synthetic_vat_result(n=6, vat_rate=0.0, facility_rate=0.05)
    base = _synthetic_vat_result(n=6, vat_rate=0.10, facility_rate=0.05)
    higher_vat = _synthetic_vat_result(n=6, vat_rate=0.20, facility_rate=0.05)
    higher_rate = _synthetic_vat_result(n=6, vat_rate=0.10, facility_rate=0.08)

    assert max(zero.vat_schedule, key=lambda row: row.vat_requirement_keur).vat_requirement_keur == 0.0
    assert max(higher_vat.vat_schedule, key=lambda row: row.vat_requirement_keur).vat_requirement_keur > max(base.vat_schedule, key=lambda row: row.vat_requirement_keur).vat_requirement_keur
    assert higher_rate.capitalized_financing_costs.vat_idc_keur > base.capitalized_financing_costs.vat_idc_keur


def test_generic_vat_synthetic_b_multiple_classes_and_commitment_fee():
    result = _synthetic_vat_result(n=4, vat_rate=0.17, facility_rate=0.04, fee_rate=0.01)
    assert len(result.vat_schedule) == 6
    assert result.capitalized_financing_costs.vat_idc_keur > 0.0
    assert result.capitalized_financing_costs.vat_commitment_fee_keur > 0.0
    assert result.vat_schedule[-1].vat_requirement_keur == pytest.approx(0.0, abs=1e-9)


def test_disabled_vat_facility_has_zero_financing_cost():
    result = _synthetic_vat_result(
        n=5, vat_rate=0.17, facility_rate=0.0, enabled=False
    )
    assert sum(result.vat_payable_keur) > 0.0
    assert all(row.vat_requirement_keur == 0.0 for row in result.vat_schedule)
    assert result.capitalized_financing_costs.vat_idc_keur == 0.0
    assert result.capitalized_financing_costs.vat_commitment_fee_keur == 0.0


def test_typed_vat_contract_fails_closed_on_ambiguous_authority():
    with pytest.raises(ValueError, match="PR9_DISABLED_VAT_FACILITY_MUST_BE_NEUTRAL"):
        ConstructionVatFacilityInput(
            enabled=False,
            periods=_periods(1, vat_active=False),
        )
    with pytest.raises(ValueError, match="PR9_INVALID_PROVENANCE"):
        ConstructionCapexTimingInput(
            "taxable", "Taxable", (1.0,), 0.17,
            vat_classification="UNVERIFIED",
        )


def test_typed_vat_contract_rejects_truncated_reimbursement_tail():
    construction_periods = _periods(2, vat_active=True)
    with pytest.raises(
        ValueError, match="PR9_VAT_HORIZON_TRUNCATES_REIMBURSEMENT_TAIL"
    ):
        ConstructionFinancingInput(
            enabled=True,
            periods=construction_periods,
            capex_items=(
                ConstructionCapexTimingInput(
                    "taxable", "Taxable", (0.5, 0.5), 0.17
                ),
            ),
            senior_pricing=ConstructionSeniorPricingInput(
                mode=SeniorRateMode.FLAT_ALL_IN,
                flat_all_in_rate=0.0,
            ),
            vat_facility=ConstructionVatFacilityInput(
                enabled=True,
                periods=_periods(3, vat_active=True),
                reimbursement_lag_periods=2,
                financing_cost_payment_weights=(1.0, 0.0),
            ),
        )


def test_oborovo_vat_commitment_is_derived_from_item_payment_timing():
    project = create_default_oborovo()
    construction = project.financing.construction_financing
    facility = construction.vat_facility
    assert facility.commitment_mode is VatFacilityCommitmentMode.DERIVED_PEAK_REQUIREMENT
    assert facility.fixed_commitment_keur is None

    capex_amounts = resolve_capex_amounts_from_capex_structure(
        construction.capex_items, project.capex
    )

    def vat_schedule(contract):
        config = build_construction_runtime_config(
            contract,
            senior_commitment_keur=100_000.0,
            equity_available_keur=0.0,
            shl_available_keur=0.0,
            capex_amounts_keur=capex_amounts,
        )
        payable = vat_monthly_uses(config.capex_schedule)
        return payable, compute_vat_schedule(
            payable,
            reimbursement_lag_periods=facility.reimbursement_lag_periods,
            horizon_periods=len(facility.periods),
        )

    base_payable, base_schedule = vat_schedule(construction)
    items = list(construction.capex_items)
    epc_index = next(i for i, item in enumerate(items) if item.code == "epc_contract")
    items[epc_index] = replace(
        items[epc_index], payment_weights=(1.0,) + (0.0,) * 11
    )
    mutated_construction = replace(construction, capex_items=tuple(items))
    mutated_payable, mutated_schedule = vat_schedule(mutated_construction)

    assert mutated_payable != base_payable
    assert max(row.vat_requirement_keur for row in mutated_schedule) != pytest.approx(
        max(row.vat_requirement_keur for row in base_schedule), abs=1e-9
    )


def test_generic_vat_applicability_amount_timing_and_lag_are_causal():
    base = _synthetic_vat_result(n=4, vat_rate=0.17, facility_rate=0.05)
    taxable_exempt = _synthetic_vat_result(
        n=4, vat_rate=0.0, facility_rate=0.05
    )
    formerly_exempt_taxable = _synthetic_vat_result(
        n=4, vat_rate=0.17, exempt_vat_rate=0.17, facility_rate=0.05
    )
    larger = _synthetic_vat_result(
        n=4, vat_rate=0.17, taxable_amount=1_500.0, facility_rate=0.05
    )
    front_loaded = _synthetic_vat_result(
        n=4,
        vat_rate=0.17,
        facility_rate=0.05,
        taxable_weights=(1.0, 0.0, 0.0, 0.0),
    )
    back_loaded = _synthetic_vat_result(
        n=4,
        vat_rate=0.17,
        facility_rate=0.05,
        taxable_weights=(0.0, 0.0, 0.0, 1.0),
    )
    longer_lag = _synthetic_vat_result(
        n=4, vat_rate=0.17, facility_rate=0.05, reimbursement_lag=3
    )

    peak = lambda result: max(row.vat_requirement_keur for row in result.vat_schedule)
    assert peak(taxable_exempt) < peak(base)
    assert peak(formerly_exempt_taxable) > peak(base)
    assert peak(larger) > peak(base)
    assert tuple(row.vat_requirement_keur for row in front_loaded.vat_schedule) != (
        tuple(row.vat_requirement_keur for row in back_loaded.vat_schedule)
    )
    assert peak(longer_lag) >= peak(base)


def test_generic_fixed_vat_commitment_capacity_and_fee_semantics():
    derived = _synthetic_vat_result(
        n=4, vat_rate=0.17, facility_rate=0.04, fee_rate=0.01
    )
    peak = max(row.vat_requirement_keur for row in derived.vat_schedule)
    exact = _synthetic_vat_result(
        n=4,
        vat_rate=0.17,
        facility_rate=0.04,
        fee_rate=0.01,
        commitment_mode=VatFacilityCommitmentMode.FIXED_COMMITMENT,
        fixed_commitment_keur=peak,
    )
    above = _synthetic_vat_result(
        n=4,
        vat_rate=0.17,
        facility_rate=0.04,
        fee_rate=0.01,
        commitment_mode=VatFacilityCommitmentMode.FIXED_COMMITMENT,
        fixed_commitment_keur=peak + 100.0,
    )
    assert tuple(row.vat_requirement_keur for row in exact.vat_schedule) == pytest.approx(
        tuple(row.vat_requirement_keur for row in derived.vat_schedule)
    )
    assert above.capitalized_financing_costs.vat_commitment_fee_keur > (
        exact.capitalized_financing_costs.vat_commitment_fee_keur
    )
    with pytest.raises(FundingShortfallError, match="VAT facility commitment breached"):
        _synthetic_vat_result(
            n=4,
            vat_rate=0.17,
            facility_rate=0.04,
            commitment_mode=VatFacilityCommitmentMode.FIXED_COMMITMENT,
            fixed_commitment_keur=peak - 1.0,
        )


def test_fixed_debt_anchor_is_not_clean_sizing_authority():
    project = create_default_oborovo()
    base = run_project_financing_model(project, source_id="phase_b2_fixed_debt_base")
    mutated = run_project_financing_model(
        replace(project, financing=replace(project.financing, fixed_debt_keur=1.0)),
        source_id="phase_b2_fixed_debt_mutation",
    )
    assert mutated.final_senior_commitment_keur == pytest.approx(
        base.final_senior_commitment_keur, abs=1e-6
    )


def test_project_identity_does_not_change_classification_or_clean_financing():
    project = create_default_oborovo()
    renamed = replace(
        project,
        info=replace(project.info, name="Identity Neutral", code="NEUTRAL", company="Other"),
    )
    assert classify_production_authority(renamed).classification is ProductionAuthorityClassification.CLEAN_PRODUCTION_READY
    result = run_project_financing_model(renamed, source_id="phase_b2_identity_mutation")
    assert result.final_senior_commitment_keur == pytest.approx(42852.302723344226, abs=1e-6)


def test_clean_production_does_not_read_frozen_senior_fixture(monkeypatch):
    import builtins
    from app.api.project_runner import run_project

    original = Path.open
    original_builtin_open = builtins.open

    def is_forbidden_report(path) -> bool:
        normalized = str(path).replace("\\", "/").lower()
        in_reports = normalized.startswith("reports/") or "/reports/" in normalized
        return in_reports and normalized.endswith((".csv", ".xlsx", ".xlsm"))

    def guarded_open(path, *args, **kwargs):
        if is_forbidden_report(path):
            raise AssertionError("clean Oborovo attempted to read a report/workbook fixture")
        return original(path, *args, **kwargs)

    def guarded_builtin_open(path, *args, **kwargs):
        if is_forbidden_report(path):
            raise AssertionError("clean Oborovo attempted to read a report/workbook fixture")
        return original_builtin_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    monkeypatch.setattr(builtins, "open", guarded_builtin_open)
    payload = run_project("Oborovo", "Base")
    assert payload["runtime_authority"]["runtime_authority"] == "clean_g2c"
    assert payload["runtime_authority"]["calculation_count"] == 1
    assert payload["runtime_authority"]["construction_authority"] == (
        "PR9_TYPED_CONSTRUCTION_FINANCING_IDC_AUTHORITY"
    )
    assert payload["runtime_authority"]["vat_facility_authority"] == (
        "TYPED_CONSTRUCTION_VAT_FACILITY_AUTHORITY"
    )
    assert payload["runtime_authority"]["vat_facility_commitment_mode"] == (
        "DERIVED_PEAK_REQUIREMENT"
    )
    assert payload["runtime_authority"]["vat_effective_commitment_keur"] == (
        pytest.approx(4_877.989945, abs=1e-9)
    )


def test_production_executes_one_clean_g2c_and_zero_legacy(monkeypatch):
    from app.api import project_runner
    from financial_engine import shareholder_waterfall

    counts = {"clean": 0, "legacy": 0}
    real_clean = shareholder_waterfall.run_project_shareholder_waterfall_model

    def counted_clean(*args, **kwargs):
        counts["clean"] += 1
        return real_clean(*args, **kwargs)

    def forbidden_legacy(*args, **kwargs):
        counts["legacy"] += 1
        raise AssertionError("production Oborovo reached the legacy engine")

    monkeypatch.setattr(
        shareholder_waterfall, "run_project_shareholder_waterfall_model", counted_clean
    )
    monkeypatch.setattr(project_runner, "run_demo_project", forbidden_legacy)
    project_runner.run_project("Oborovo", "Base")
    assert counts == {"clean": 1, "legacy": 0}


def test_explicit_legacy_executes_one_legacy_and_zero_clean(monkeypatch):
    from app.api import project_runner
    from financial_engine import shareholder_waterfall

    counts = {"clean": 0, "legacy": 0}
    real_legacy = project_runner.run_demo_project

    def forbidden_clean(*args, **kwargs):
        counts["clean"] += 1
        raise AssertionError("explicit calibration reached clean G2C")

    def counted_legacy(*args, **kwargs):
        counts["legacy"] += 1
        return real_legacy(*args, **kwargs)

    monkeypatch.setattr(
        shareholder_waterfall, "run_project_shareholder_waterfall_model", forbidden_clean
    )
    monkeypatch.setattr(project_runner, "run_demo_project", counted_legacy)
    payload = project_runner.run_project_legacy("Oborovo", "Base")
    assert payload["kpis"]["total_capex_keur"] == pytest.approx(57973.0535)
    assert counts == {"clean": 0, "legacy": 1}


def test_bank_route_uses_same_clean_authority():
    from app.api.project_runner import run_project

    payload = run_project("Oborovo", "Bank")
    assert payload["runtime_authority"]["runtime_authority"] == "clean_g2c"
    assert payload["runtime_authority"]["calculation_count"] == 1
    assert payload["scenario"] == "Bank"


def test_legacy_overlay_and_tuho_boundary_remain_explicit():
    from app.project_factories import create_default_tuho_wind1_legacy_calibration

    legacy = create_default_oborovo_legacy_calibration()
    assert legacy.financing.use_frozen_excel_senior_debt_schedule is True
    assert legacy.financing.construction_financing is None
    assert classify_production_authority(legacy).classification is ProductionAuthorityClassification.BLOCKED_BY_TYPED_INPUT_GAP
    assert classify_production_authority(create_default_tuho_wind1()).promoted is True
    assert (
        classify_production_authority(create_default_tuho_wind1_legacy_calibration())
        .promoted
        is False
    )


def test_explicit_legacy_oborovo_kpi_fingerprint_is_unchanged():
    from app.api.project_runner import run_project_legacy

    assert run_project_legacy("Oborovo", "Base")["kpis"] == {
        "project_irr": 0.07972911653802585,
        "project_npv_keur": 10963.574072962754,
        "equity_irr": 0.1034836905052773,
        "equity_npv_keur": 1356.7295285305872,
        "sponsor_irr": 0.0974108183775152,
        "min_dscr": 1.15,
        "avg_dscr": 1.1785714285714286,
        "target_dscr": 1.15,
        "min_llcr": 1.2590820909738514,
        "periods_in_lockup": 0,
        "total_revenue_keur": 238438.1775880854,
        "total_opex_keur": 55782.95083863444,
        "total_ebitda_keur": 182655.226749451,
        "total_tax_keur": 8490.320139957446,
        "total_senior_ds_keur": 63191.17422465547,
        "total_shl_service_keur": 37678.310202739725,
        "total_distributions_keur": 64006.489082030435,
        "total_capex_keur": 57973.0535,
    }


def test_tuho_production_is_clean_with_zero_legacy_calculations(monkeypatch):
    from app.api import project_runner
    from financial_engine import shareholder_waterfall

    calls = {"clean": 0, "legacy": 0}
    real_clean = shareholder_waterfall.run_project_shareholder_waterfall_model

    def clean(*args, **kwargs):
        calls["clean"] += 1
        return real_clean(*args, **kwargs)

    def legacy(*args, **kwargs):
        calls["legacy"] += 1

    monkeypatch.setattr(
        shareholder_waterfall, "run_project_shareholder_waterfall_model", clean
    )
    monkeypatch.setattr(project_runner, "run_demo_project", legacy)
    payload = project_runner.run_project("TUHO", "Base")
    assert payload["runtime_authority"]["runtime_authority"] == "clean_g2c"
    assert payload["runtime_authority"]["calculation_count"] == 1
    assert calls == {"clean": 1, "legacy": 0}


def test_typed_vat_contract_round_trips_without_output_authority():
    project = create_default_oborovo()
    restored = project_inputs_from_dict(project_inputs_to_dict(project))
    assert restored.financing.construction_financing == project.financing.construction_financing
    assert restored.capex.vat_facility_idc_keur == 0.0
    assert restored.capex.vat_facility_commitment_fee_keur == 0.0


def test_vat_commitment_modes_round_trip_and_legacy_payload_fails_closed():
    project = create_default_oborovo()
    construction = project.financing.construction_financing

    derived_payload = project_inputs_to_dict(project)
    derived = project_inputs_from_dict(derived_payload)
    assert (
        derived.financing.construction_financing.vat_facility.commitment_mode
        is VatFacilityCommitmentMode.DERIVED_PEAK_REQUIREMENT
    )

    fixed_facility = replace(
        construction.vat_facility,
        commitment_mode=VatFacilityCommitmentMode.FIXED_COMMITMENT,
        fixed_commitment_keur=6_000.0,
    )
    fixed_project = replace(
        project,
        financing=replace(
            project.financing,
            construction_financing=replace(
                construction, vat_facility=fixed_facility
            ),
        ),
    )
    fixed = project_inputs_from_dict(project_inputs_to_dict(fixed_project))
    assert fixed.financing.construction_financing.vat_facility == fixed_facility

    inactive_periods = tuple(
        replace(period, vat_facility_active=False)
        for period in construction.periods
    )
    disabled_construction = replace(
        construction,
        periods=inactive_periods,
        vat_facility=ConstructionVatFacilityInput(),
    )
    disabled_project = replace(
        project,
        financing=replace(
            project.financing, construction_financing=disabled_construction
        ),
    )
    disabled = project_inputs_from_dict(project_inputs_to_dict(disabled_project))
    assert disabled.financing.construction_financing.vat_facility.enabled is False

    ambiguous_payload = project_inputs_to_dict(project)
    vat_payload = ambiguous_payload["financing"]["construction_financing"]["vat_facility"]
    vat_payload.pop("commitment_mode")
    vat_payload["commitment_keur"] = 4_877.989945
    with pytest.raises(
        ValueError, match="PR9_LEGACY_VAT_COMMITMENT_AUTHORITY_AMBIGUOUS"
    ):
        project_inputs_from_dict(ambiguous_payload)


def test_clean_oborovo_factory_has_no_derived_peak_commitment_literal():
    factory_text = (
        Path(__file__).resolve().parents[1] / "app" / "project_factories.py"
    ).read_text(encoding="utf-8")
    assert "4_877.989945" not in factory_text


def test_production_modules_do_not_import_source_parity_or_fixture_outputs():
    root = Path(__file__).resolve().parents[1]
    production_files = (
        root / "financial_engine" / "construction" / "adapter.py",
        root / "financial_engine" / "financing" / "project.py",
        root / "finco_core" / "construction" / "stage_b2.py",
    )
    text = "\n".join(path.read_text(encoding="utf-8") for path in production_files)
    assert "domain.construction.source_parity" not in text
    assert "phase23q_oborovo_senior_debt_sizing_extraction.csv" not in text
    for forbidden in ("approved_delta", "expected_delta", "balancing_plug", "target_fitting"):
        assert forbidden not in text
