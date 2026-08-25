"""PR-7 Base/Bank Case authority — financial before/after baseline lock.

DIAGNOSTIC ONLY. Runs the five calibration projects (Generic Solar, Generic
Wind, Oborovo, TUHO, KUPI-P0) through their canonical clean-engine entry
points and prints a deterministic JSON summary of Base/Bank/Senior/downstream
vectors.

Purpose: authority consolidation must leave economics unchanged. Run this on
the verified base commit and on the PR-7 head; the two outputs must be
byte-identical. Any numerical divergence requires a causal source/policy
explanation before it may be accepted.

Usage:
    python -m tests.diagnostics.pr7_base_bank_case_baseline_lock
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any


def _vec_digest(values) -> dict[str, Any]:
    """Deterministic digest of a numeric vector (sum + sha256 of repr)."""
    vec = tuple(float(v) if v is not None else 0.0 for v in values)
    if not vec:
        return {"n": 0, "sum": 0.0, "sha256": hashlib.sha256(b"empty").hexdigest()}
    payload = repr(vec).encode("utf-8")
    return {
        "n": len(vec),
        "sum": sum(vec),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _summarize_senior_debt_model_result(result) -> dict[str, Any]:
    """Summarize a ProjectModelResult from run_senior_debt_model."""
    out: dict[str, Any] = {}

    op = result.operating_schedules
    tax = result.tax_and_cfads
    bank = result.debt_sizing
    senior = result.senior_debt
    psc = result.post_senior_cash
    shl = result.shareholder_loan

    out["base"] = {
        "production_mwh": _vec_digest(op.production_mwh),
        "revenue_keur": _vec_digest(op.revenue_keur),
        "opex_keur": _vec_digest(op.opex_keur),
        "ebitda_keur": _vec_digest(op.ebitda_keur),
        "cash_tax_keur": _vec_digest(tax.corporate_tax_cash_keur),
        "cfads_keur": _vec_digest(tax.cfads_keur),
    }
    out["bank"] = {
        "production_mwh": _vec_digest(bank.bank_production_mwh),
        "revenue_keur": _vec_digest(bank.bank_revenue_keur),
        "opex_keur": _vec_digest(bank.bank_opex_keur),
        "ebitda_keur": _vec_digest(bank.bank_ebitda_keur),
        "cash_tax_keur": _vec_digest(bank.bank_cash_tax_keur),
        "cfads_keur": _vec_digest(bank.bank_cfads_keur),
    }
    dscr_service = [
        d for d, s in zip(senior.base_dscr, senior.senior_debt_service_keur)
        if d is not None and s > 1e-9
    ]
    bank_dscr = [d for d in bank.bank_sizing_dscr if d is not None]
    out["senior"] = {
        "debt_size_keur": senior.debt_size_keur,
        "binding_constraint": senior.binding_constraint,
        "interest_keur": _vec_digest(senior.senior_interest_keur),
        "principal_keur": _vec_digest(senior.senior_principal_keur),
        "debt_service_keur": _vec_digest(senior.senior_debt_service_keur),
        "closing_last_keur": senior.senior_debt_closing_keur[-1],
        "base_dscr_min": min(dscr_service) if dscr_service else None,
        "bank_sizing_dscr_min": min(bank_dscr) if bank_dscr else None,
    }
    out["downstream"] = {
        "post_senior_cash_keur": _vec_digest(psc.cash_after_senior_before_reserves_keur),
        "cash_available_for_shl_keur": _vec_digest(
            psc.cash_available_for_shl_before_reserves_keur
        ),
    }
    dsra = getattr(result, "cash_dsra", None)
    if dsra is not None:
        out["downstream"]["cash_dsra_closing_keur"] = _vec_digest(
            getattr(dsra, "closing_balance_keur", ())
        )
    if shl is not None:
        out["downstream"]["shl"] = {
            "gross_interest_keur": _vec_digest(shl.shl_gross_interest_keur),
            "pik_keur": _vec_digest(shl.shl_pik_interest_keur)
            if hasattr(shl, "shl_pik_interest_keur") else None,
            "principal_keur": _vec_digest(shl.shl_principal_keur),
            "closing_last_keur": shl.shl_closing_keur[-1],
            "is_authoritative": shl.diagnostics.is_authoritative,
        }
    else:
        out["downstream"]["shl"] = "NOT_PRESENT_IN_CLEAN_RESULT"
    return out


def _summarize_financing_result(fin) -> dict[str, Any]:
    """Summarize a ProjectFinancingResult (G2A fixed point, KUPI path)."""
    result = fin.project_model_result
    out = _summarize_senior_debt_model_result(result)
    out["g2a"] = {
        "total_project_uses_keur": fin.project_uses.total_project_uses_keur,
        "dscr_debt_capacity_keur": fin.dscr_debt_capacity_keur,
        "gearing_debt_capacity_keur": fin.gearing_debt_capacity_keur,
        "final_senior_commitment_keur": fin.final_senior_commitment_keur,
        "binding_senior_constraint": fin.binding_senior_constraint,
        "derived_shl_cash_principal_keur": fin.derived_shl_cash_principal_keur,
        "shl_construction_pik_keur": fin.shl_construction_pik_keur,
        "opening_operating_shl_balance_keur": fin.opening_operating_shl_balance_keur,
        "fixed_point_iterations": fin.fixed_point_iteration_count,
    }
    return out


def _run_factory_project(factory_name: str):
    from app import project_factories
    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )
    from financial_engine.orchestrator import run_senior_debt_model

    project = getattr(project_factories, factory_name)()
    model = build_senior_debt_model_input_from_project_inputs(
        project, source_id="pr7-baseline-lock"
    )
    return run_senior_debt_model(model)


def _run_tuho_clean_case():
    """TUHO clean-engine Base/Bank run.

    TUHO has not opted into the clean cash-tax timing contract (its production
    financials run through the frozen-schedule legacy waterfall), so the full
    canonical adapter path fails closed on tax. The accepted TUHO representation
    inside the clean Base/Bank authority is the C3B3D2B3 fixture pattern:
    TUHO operating input + parity tax reference inputs + explicit bank case.
    This mirrors tests/test_stage_c3b3d2b3_debt_sizing_case_production.py.
    """
    from app.project_factories import create_default_tuho_wind1
    from finco_parity.tax_reference_inputs import (
        build_tax_policy,
        build_opening_loss_vintages,
    )
    from financial_engine.adapters.project_inputs import from_project_inputs
    from financial_engine.inputs import (
        DebtSizingCaseInput,
        SeniorDebtModelInput,
        TaxCalculationInput,
        YieldScenario,
    )
    from financial_engine.orchestrator import run_senior_debt_model
    from financial_engine.senior_debt.inputs import SeniorDebtInputs
    from financial_engine.senior_debt.policy import (
        DayCountConvention,
        SeniorDebtPolicy,
        SeniorDebtSizingMode,
    )

    base_op = from_project_inputs(create_default_tuho_wind1())
    from financial_engine.orchestrator import run_operating_model

    operating_indices = tuple(
        p.period_index for p in run_operating_model(base_op).periods if p.is_operation
    )
    tax_input = TaxCalculationInput(
        policy=build_tax_policy("tuho"),
        opening_loss_vintages=build_opening_loss_vintages("tuho"),
        period_interest=(),
        period_adjustments=(),
    )
    model = SeniorDebtModelInput(
        operating=base_op,
        tax=tax_input,
        senior_debt_policy=SeniorDebtPolicy(
            policy_id="pr7_tuho_baseline_lock",
            policy_version="1.0",
            sizing_mode=SeniorDebtSizingMode.DSCR_SCULPTED,
            target_dscr=1.2,
            maximum_gearing=None,
            annual_fixed_rate=0.05,
            periods_per_year=2,
            day_count_convention=DayCountConvention.ACT_365,
            repayment_start_period_index=operating_indices[0],
            maturity_period_index=operating_indices[-1],
            convergence_tolerance_keur=1.0,
            convergence_relative_tolerance=0.001,
            maximum_iterations=300,
            permit_terminal_balloon=True,
        ),
        senior_debt_inputs=SeniorDebtInputs(
            eligible_project_cost_keur=100_000.0,
            initial_debt_guess_keur=60_000.0,
            period_rates=(),
            explicit_principal_schedule=None,
        ),
        debt_sizing_case=DebtSizingCaseInput(
            production_yield_scenario=YieldScenario.P90_10Y,
            source_label="tuho_p90_10y_bank_case",
        ),
    )
    return run_senior_debt_model(model)


def run_baselines() -> dict[str, Any]:
    baselines: dict[str, Any] = {}
    for label, factory_name in (
        ("Generic Solar", "create_default_solar_project"),
        ("Generic Wind", "create_default_wind_project"),
        ("Oborovo", "create_default_oborovo"),
    ):
        baselines[label] = _summarize_senior_debt_model_result(
            _run_factory_project(factory_name)
        )
    baselines["TUHO"] = _summarize_senior_debt_model_result(_run_tuho_clean_case())

    from tests.diagnostics.kupi_k0_k3_causal_grid import run_p0_current_generic

    baselines["KUPI P0"] = _summarize_financing_result(run_p0_current_generic())
    return baselines


def _normalize(obj: Any) -> Any:
    """Make output stable for byte-comparison: sort dict keys, round nothing."""
    if isinstance(obj, dict):
        return {k: _normalize(obj[k]) for k in sorted(obj)}
    if isinstance(obj, (list, tuple)):
        return [_normalize(v) for v in obj]
    if isinstance(obj, float):
        if not math.isfinite(obj):
            return repr(obj)
        return obj
    return obj


def main() -> None:
    baselines = _normalize(run_baselines())
    print(json.dumps(baselines, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
