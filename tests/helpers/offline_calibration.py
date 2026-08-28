"""tests.helpers.offline_calibration — OFFLINE_VALIDATION_ONLY (Phase B4).

Historical calibration/characterization execution relocated OUT of the
production app surface in Phase B4. This module is the one sanctioned home
for legacy financial execution used by historical parity /
characterization tests:

  - run_project_legacy(): the pre-B4 legacy run payload (legacy waterfall +
    legacy sponsor engine + FS assembly) for characterization suites;
  - execute_calibration_waterfall(): the pre-B4 explicit calibration seam.

Contract (statically proven by tests/test_phaseb4_single_production_engine.py):
  - NO production module (app/, main_web, main_api, domain routes, CLI,
    Streamlit) imports this module or anything that executes the legacy
    waterfall;
  - production financial execution is exclusively the clean authority
    (app.services.production_financial_authority.run_clean_production).
"""
from __future__ import annotations

from app.ui_runner import run_demo_project  # OFFLINE legacy funnel


def run_project_legacy(project_type: str, scenario: str, period_view: str = "Semiannual",
                       project_inputs_override=None, use_dualrun_validation: bool = False):
    """Pre-B4 legacy characterization run (OFFLINE_VALIDATION_ONLY).

    Reproduces the historical run_project payload shape: legacy waterfall via
    the legacy demo funnel + legacy sponsor engine + legacy FS assembly.
    Read-only presentation serializers are imported from production (pure
    functions, no engine execution).
    """
    from app import project_factories as _pf
    from app.api.project_runner import (
        _serialize_debt_schedule,
        _serialize_distribution_schedule,
        _serialize_sponsor_schedule,
        _serialize_tax_schedule,
        _build_runtime_derivation_evidence,
        _sanitize_df,
    )
    from app.output_tables import (
        aggregate_period_table_annual,
        build_debt_table,
        build_revenue_table,
        build_returns_table,
        build_waterfall_table,
    )
    from domain.financial_statements import assemble_financial_statements
    from tests.helpers.offline_sponsor_engine import _run_sponsor_engine

    calibration_factory = {
        "Oborovo": _pf.create_default_oborovo_legacy_calibration,
    }.get(project_type)
    if project_inputs_override is None and calibration_factory is not None:
        project_inputs_override = calibration_factory()

    demo = run_demo_project(
        project_type, scenario,
        project_inputs_override=project_inputs_override,
        use_dualrun_validation=use_dualrun_validation,
        legacy_calibration=True,
    )
    result = demo.result
    if result is None:
        return {
            "project_type": project_type,
            "scenario": scenario,
            "period_view": period_view,
            "integration_status": getattr(demo, "integration_status", "full"),
            "integration_note": getattr(demo, "integration_note", None),
            "messages": getattr(demo, "messages", []),
            "debt_schedule": None,
            "tax_schedule": None,
            "distribution_schedule": None,
            "kpis": {},
            "financial_statements": None,
            "sponsor_schedule": None,
            "tables": {},
        }

    wf = build_waterfall_table(result)
    rev = build_revenue_table(result)
    debt = build_debt_table(result)
    returns = build_returns_table(result)
    if period_view == "Annual":
        wf = aggregate_period_table_annual(wf)
        rev = aggregate_period_table_annual(rev)
        debt = aggregate_period_table_annual(debt)
    wf = _sanitize_df(wf)
    rev = _sanitize_df(rev)
    debt = _sanitize_df(debt)
    returns = _sanitize_df(returns)

    financial_statements_payload = None
    try:
        fs = assemble_financial_statements(result)
        from app.api.project_runner import _serialize_financial_statements
        financial_statements_payload = _serialize_financial_statements(fs)
    except Exception:
        financial_statements_payload = None

    sponsor_schedule_payload = None
    try:
        sponsor_result = _run_sponsor_engine(result, demo.project_inputs, project_type)
        if sponsor_result is not None:
            sponsor_schedule_payload = _serialize_sponsor_schedule(*sponsor_result)
    except Exception:
        sponsor_schedule_payload = None

    return {
        "project_type": project_type,
        "scenario": scenario,
        "period_view": period_view,
        "integration_status": getattr(demo, "integration_status", "full"),
        "integration_note": getattr(demo, "integration_note", None),
        "messages": getattr(demo, "messages", []),
        "debt_schedule": _serialize_debt_schedule(result),
        "tax_schedule": _serialize_tax_schedule(result),
        "distribution_schedule": _serialize_distribution_schedule(result),
        "kpis": {
            "total_capex_keur": getattr(getattr(demo, "project_inputs", None), "capex", None).total_capex
            if getattr(getattr(demo, "project_inputs", None), "capex", None) is not None else None,
            "total_revenue_keur": result.total_revenue_keur,
            "total_ebitda_keur": result.total_ebitda_keur,
            "total_opex_keur": getattr(result, "total_opex_keur", None),
            "total_distributions_keur": getattr(result, "total_distribution_keur", None),
            "project_irr": result.project_irr,
            "equity_irr": result.equity_irr,
            "sponsor_irr": getattr(result, "sponsor_irr", None),
            "project_npv_keur": getattr(result, "project_npv", None),
            "equity_npv_keur": getattr(result, "equity_npv", None),
            "total_senior_ds_keur": getattr(result, "total_senior_ds_keur", None),
            "total_shl_service_keur": getattr(result, "total_shl_service_keur", None),
            "total_tax_keur": getattr(result, "total_tax_keur", None),
            "target_dscr": getattr(result, "target_dscr", None),
            "min_dscr": result.actual_min_dscr,
            "avg_dscr": result.actual_avg_dscr,
            "min_llcr": getattr(result, "min_llcr", None),
            "periods_in_lockup": getattr(result, "periods_in_lockup", None),
        },
        "dualrun_validation": getattr(result, "_dualrun_validation", None),
        "derivation_evidence": _build_runtime_derivation_evidence(result, demo.project_inputs),
        "financial_statements": financial_statements_payload,
        "sponsor_schedule": sponsor_schedule_payload,
        "tables": {
            "waterfall": wf.to_dict(orient="records"),
            "revenue": rev.to_dict(orient="records"),
            "debt": debt.to_dict(orient="records"),
            "returns": returns.to_dict(orient="records"),
        },
        # Offline lineage: explicitly NOT a production authority result.
        "runtime_authority": {
            "classification": "LEGACY_CALIBRATION_ONLY",
            "reason_code": "PHASE_B4_OFFLINE_CALIBRATION_HELPER",
            "detail": (
                "Historical legacy characterization run executed by the "
                "offline calibration helper (tests/helpers); not a "
                "production financial authority result."
            ),
            "runtime_authority": "legacy_waterfall_offline_calibration",
            "calculation_count": 1,
        },
    }


def execute_calibration_waterfall(
    project_inputs,
    *,
    project_type: str = "",
    scenario: str = "Base",
):
    """Pre-B4 explicit calibration seam (OFFLINE_VALIDATION_ONLY).

    Executes the legacy waterfall for a NON-promoted ProjectInputs snapshot.
    Refuses promoted (clean-ready) inputs — production execution for those
    is exclusively the clean authority.
    """
    from app.services.production_waterfall_seam import classify_or_fail
    from app.services.production_financial_authority import (
        ProductionAuthorityResolutionError,
    )

    decision = classify_or_fail(project_inputs)
    if decision.promoted:
        raise ProductionAuthorityResolutionError(
            reason_code="PR8_CALIBRATION_SEAM_REFUSED_CLEAN_READY_PROJECT",
            detail=(
                "offline execute_calibration_waterfall() is for explicitly "
                "blocked projects only. This project is CLEAN_PRODUCTION_READY "
                "— production execution is the clean authority."
            ),
        )

    effective_inputs = project_inputs
    if scenario != "Base":
        from app.scenario_manager import ScenarioManager

        mgr = ScenarioManager((project_type or "").lower())
        effective_inputs = mgr.apply_overrides(project_inputs, scenario)

    from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
    from finco_core.engine.period_engine import PeriodEngine

    engine = PeriodEngine(
        financial_close=effective_inputs.info.financial_close,
        construction_months=effective_inputs.info.construction_months,
        horizon_years=effective_inputs.info.horizon_years,
        ppa_years=effective_inputs.revenue.ppa_term_years,
        frequency=effective_inputs.info.period_frequency,
        cod_date=effective_inputs.info.cod_date,
        period_axis_convention=getattr(
            effective_inputs.info.period_axis_convention,
            "value",
            effective_inputs.info.period_axis_convention,
        ),
    )
    config = WaterfallRunConfig.from_inputs(effective_inputs, engine)
    result = WaterfallRunner(effective_inputs, engine).run(config)
    return decision, effective_inputs, result
