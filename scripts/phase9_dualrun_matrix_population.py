"""scripts/phase9_dualrun_matrix_population.py

Populate phase9_distributionaccount_dualrun_matrix.csv with real per-period
comparison data across all supported TUHO and Oborovo flag combinations.

VALIDATION ONLY — no runtime routing.
Runtime authority remains WaterfallEngine.distribution_keur throughout.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.project_factories import create_default_tuho_wind1, create_default_oborovo
from app.waterfall_core import run_waterfall_v3_core
from app.ui_runner import _build_period_engine as build_period_engine


@dataclass(frozen=True)
class FlagCombo:
    """One combination of runtime flags."""
    shl: bool
    dep: bool
    tax_bridge: bool
    co2_rev: bool
    co2_cit: bool
    label: str
    valid_for: frozenset[str]
    phase_c_supported: bool  # False = excluded from Phase C readiness evidence


ALL_COMBOS = [
    # Supported combos (phase_c_supported=True)
    FlagCombo(False, False, False, False, False, "baseline",               frozenset({"TUHO-WIND-1", "OBOROVO-SOLAR-1"}), True),
    FlagCombo(True,  False, False, False, False, "shl_canonical",          frozenset({"TUHO-WIND-1", "OBOROVO-SOLAR-1"}), True),
    FlagCombo(False, True,  False, False, False, "deprec_canonical",        frozenset({"TUHO-WIND-1"}), True),
    FlagCombo(True,  True,  False, False, False, "shl+deprec",             frozenset({"TUHO-WIND-1"}), True),
    FlagCombo(False, False, False, True,  False, "co2_revenue_bridge",      frozenset({"TUHO-WIND-1"}), True),
    FlagCombo(False, False, False, False, True,  "co2_cit_bridge",          frozenset({"TUHO-WIND-1"}), True),
    FlagCombo(True,  False, False, True,  False, "shl+co2_revenue",         frozenset({"TUHO-WIND-1"}), True),
    FlagCombo(False, True,  False, True,  False, "deprec+co2_revenue",      frozenset({"TUHO-WIND-1"}), True),
    FlagCombo(True,  False, False, False, False, "oborovo_shl",             frozenset({"OBOROVO-SOLAR-1"}), True),
    # Unsupported combos (phase_c_supported=False) — cash-source mismatch in tax_bridge path
    FlagCombo(False, True,  True,  False, False, "tax_bridge",              frozenset({"TUHO-WIND-1"}), False),
    FlagCombo(True,  True,  True,  False, False, "shl+deprec+tax_bridge",  frozenset({"TUHO-WIND-1"}), False),
    # co2_revenue+cit is mutually exclusive in waterfall engine — always raises, never runs
    FlagCombo(False, False, False, True,  True,  "co2_revenue+cit",         frozenset({"TUHO-WIND-1"}), False),
]

CSV_PATH = Path(__file__).parent.parent / "reports" / "phase9_distributionaccount_dualrun_matrix.csv"
CSV_COLUMNS = [
    "project", "flag_combo", "period", "operating_period_index",
    "runtime_distribution_keur",
    "da_governed_paid_distribution_keur", "da_economic_paid_distribution_keur",
    "delta_keur", "delta_economic_keur", "delta_pct", "delta_economic_pct",
    "classification", "classification_economic",
    "gates_passed", "economic_gates_evaluated", "runtime_authoritative",
    "r99_blocked", "r102_blocked", "dscr_passed", "lockup_passed", "oborovo_passed",
    "blocked_reason", "validation_error", "notes",
    "supported_for_phase_c",
]


@dataclass
class DualRunMatrixRow:
    project: str
    flag_combo: str
    period: int
    operating_period_index: int
    runtime_distribution_keur: float
    da_governed_paid_distribution_keur: float
    da_economic_paid_distribution_keur: float
    delta_keur: float
    delta_economic_keur: float
    delta_pct: float
    delta_economic_pct: float
    classification: str
    classification_economic: str
    gates_passed: bool
    economic_gates_evaluated: bool
    runtime_authoritative: bool
    r99_blocked: bool
    r102_blocked: bool
    dscr_passed: bool
    lockup_passed: bool
    oborovo_passed: bool
    blocked_reason: str
    validation_error: Optional[str]
    notes: str
    supported_for_phase_c: bool

    def to_csv_row(self) -> list:
        return [
            self.project,
            self.flag_combo,
            self.period,
            self.operating_period_index,
            f"{self.runtime_distribution_keur:.2f}",
            f"{self.da_governed_paid_distribution_keur:.2f}",
            f"{self.da_economic_paid_distribution_keur:.2f}",
            f"{self.delta_keur:.2f}",
            f"{self.delta_economic_keur:.2f}",
            f"{self.delta_pct:.4f}",
            f"{self.delta_economic_pct:.4f}",
            self.classification,
            self.classification_economic,
            str(self.gates_passed),
            str(self.economic_gates_evaluated),
            str(self.runtime_authoritative),
            str(self.r99_blocked),
            str(self.r102_blocked),
            str(self.dscr_passed),
            str(self.lockup_passed),
            str(self.oborovo_passed),
            self.blocked_reason,
            self.validation_error or "",
            self.notes,
            str(self.supported_for_phase_c),
        ]


def _run_waterfall_with_combo(inputs, engine, combo: FlagCombo):
    """Run waterfall core directly for a given flag combo (bypasses WaterfallRunConfig)."""
    return run_waterfall_v3_core(
        inputs=inputs,
        engine=engine,
        rate_per_period=0.0,       # unused when fixed_debt_keur / fixed_ds_keur set
        tenor_periods=0,            # unused
        target_dscr=1.15,
        lockup_dscr=1.10,
        tax_rate=0.10,
        dsra_months=6,
        shl_amount=0.0,
        shl_rate=0.0,
        shl_idc_keur=0.0,
        shl_repayment_method="bullet",
        shl_tenor_years=0,
        shl_wht_rate=0.0,
        discount_rate_project=0.0641,
        discount_rate_equity=0.0965,
        fixed_debt_keur=None,
        fixed_ds_keur=None,
        rate_schedule=None,
        senior_sculpting_config=None,
        equity_irr_method="equity_only",
        share_capital_keur=0.0,
        sculpt_capex_keur=0.0,
        debt_sizing_method="dscr_sculpt",
        dscr_schedule=None,
        advanced_opex_line_items=None,
        advanced_capex_line_items=None,
        advanced_capex_depreciation_schedule=None,
        use_senior_sweep_cash_cap_for_shl=False,
        use_tuho_r99_input_engine=False,
        use_shl_fcf_waterfall_engine=False,
        use_tax_bridge_engine=combo.tax_bridge,
        use_shl_gross_accrued_for_pnl=False,
        shl_fcf_waterfall_cash_schedule_keur=(),
        shl_fcf_waterfall_minimum_cash_retained_keur=0.0,
        tuho_cit_cash_tax_start_operating_index=None,
        use_shl_canonical_engine=combo.shl,
        use_depreciation_canonical_engine=combo.dep,
        use_senior_debt_sizing_engine=False,
        use_co2_revenue_bridge=combo.co2_rev,
        use_co2_cit_bridge=combo.co2_cit,
        use_dualrun_validation=True,
    )


def _extract_matrix_rows(result, project: str, combo: FlagCombo) -> list[DualRunMatrixRow]:
    dual = getattr(result, "_dualrun_validation", None)
    if dual is None:
        return [DualRunMatrixRow(
            project=project, flag_combo=combo.label,
            period=0, operating_period_index=0,
            runtime_distribution_keur=0.0,
            da_governed_paid_distribution_keur=0.0,
            da_economic_paid_distribution_keur=0.0,
            delta_keur=0.0, delta_economic_keur=0.0, delta_pct=0.0, delta_economic_pct=0.0,
            classification="NO_DUALRUN_RESULT",
            classification_economic="NO_ECONOMIC_RESULT",
            gates_passed=False, economic_gates_evaluated=False, runtime_authoritative=True,
            r99_blocked=False, r102_blocked=False, dscr_passed=False,
            lockup_passed=False, oborovo_passed=False,
            blocked_reason="", validation_error="NO_DUALRUN_RESULT", notes="",
            supported_for_phase_c=combo.phase_c_supported,
        )]
    if isinstance(dual, Exception):
        return [DualRunMatrixRow(
            project=project, flag_combo=combo.label,
            period=0, operating_period_index=0,
            runtime_distribution_keur=0.0,
            da_governed_paid_distribution_keur=0.0,
            da_economic_paid_distribution_keur=0.0,
            delta_keur=0.0, delta_economic_keur=0.0, delta_pct=0.0, delta_economic_pct=0.0,
            classification="DUALRUN_EXCEPTION",
            classification_economic="DUALRUN_EXCEPTION",
            gates_passed=False, economic_gates_evaluated=False, runtime_authoritative=True,
            r99_blocked=False, r102_blocked=False, dscr_passed=False,
            lockup_passed=False, oborovo_passed=False,
            blocked_reason="",
            validation_error=f"Exception: {type(dual).__name__}: {str(dual)}",
            notes="",
            supported_for_phase_c=combo.phase_c_supported,
        )]
    return [DualRunMatrixRow(
        project=project,
        flag_combo=combo.label,
        period=pr.period_index,
        operating_period_index=pr.operating_period_index,
        runtime_distribution_keur=pr.runtime_distribution_keur,
        da_governed_paid_distribution_keur=pr.da_governed_paid_distribution_keur,
        da_economic_paid_distribution_keur=pr.da_economic_paid_distribution_keur,
        delta_keur=pr.delta_keur,
        delta_economic_keur=pr.delta_economic_keur,
        delta_pct=pr.delta_pct,
        delta_economic_pct=pr.delta_economic_pct,
        classification=pr.classification,
        classification_economic=pr.classification_economic,
        gates_passed=pr.gates_passed,
        economic_gates_evaluated=pr.economic_gates_evaluated,
        runtime_authoritative=pr.runtime_authoritative,
        r99_blocked=pr.r99_blocked,
        r102_blocked=pr.r102_blocked,
        dscr_passed=pr.dscr_passed,
        lockup_passed=pr.lockup_passed,
        oborovo_passed=pr.oborovo_passed,
        blocked_reason=pr.blocked_reason,
        validation_error=None,
        notes=pr.notes,
        supported_for_phase_c=combo.phase_c_supported,
    ) for pr in dual.period_results]


def _summarize_combo(result, project: str, combo: FlagCombo) -> dict:
    dual = getattr(result, "_dualrun_validation", None)
    if dual is None or isinstance(dual, Exception):
        return dict(
            project=project, flag_combo=combo.label,
            total_runtime=0.0, total_da_governed=0.0, total_da_economic=0.0,
            identical=0, identical_economic=0,
            rounding=0, rounding_economic=0,
            expected_gate_diff=0, unexpected=0, blocking=0,
            phase_c_ready=False,
            phase_c_supported=combo.phase_c_supported,
            validation_error=str(type(dual).__name__ if isinstance(dual, Exception) else "NO_RESULT"),
        )
    # Phase C readiness: requires supported combo + no blocking/unexpected + positive evidence
    has_positive_evidence = (dual.identical_economic_periods + dual.rounding_economic_periods) > 0
    has_no_blocking = (dual.blocking_periods == 0)
    has_no_unexpected = (dual.unexpected_diff_periods == 0)
    computed_phase_c_ready = (
        combo.phase_c_supported
        and has_no_blocking
        and has_no_unexpected
        and has_positive_evidence
    )
    return dict(
        project=project, flag_combo=combo.label,
        total_runtime=dual.total_runtime_distribution_keur,
        total_da_governed=dual.total_da_governed_paid_keur,
        total_da_economic=dual.total_da_economic_paid_keur,
        identical=dual.identical_periods,
        identical_economic=dual.identical_economic_periods,
        rounding=dual.rounding_periods,
        rounding_economic=dual.rounding_economic_periods,
        expected_gate_diff=dual.expected_gate_diff_periods,
        unexpected=dual.unexpected_diff_periods,
        blocking=dual.blocking_periods,
        phase_c_ready=computed_phase_c_ready,
        phase_c_supported=combo.phase_c_supported,
        validation_error=None,
    )


def run_matrix_population():
    all_rows: list[DualRunMatrixRow] = []
    summary_rows: list[dict] = []

    print("=== TUHO-WIND-1 Dual-Run Matrix ===")
    inputs_tuho = create_default_tuho_wind1()
    engine_tuho = build_period_engine(inputs_tuho)

    for combo in ALL_COMBOS:
        if "TUHO-WIND-1" not in combo.valid_for:
            continue
        try:
            result = _run_waterfall_with_combo(inputs_tuho, engine_tuho, combo)
            rows = _extract_matrix_rows(result, "TUHO-WIND-1", combo)
            all_rows.extend(rows)
            summary = _summarize_combo(result, "TUHO-WIND-1", combo)
            summary_rows.append(summary)
            dual = getattr(result, "_dualrun_validation", None)
            print(f"  {combo.label}: {len(rows)} periods | "
                  f"IDENT={summary['identical']} ROUND={summary['rounding']} "
                  f"EXP={summary['expected_gate_diff']} UNEXP={summary['unexpected']} "
                  f"BLOCK={summary['blocking']} phase_c_ready={summary['phase_c_ready']}"
                  + (f" ERR={summary['validation_error']}" if summary['validation_error'] else ""))
        except Exception as e:
            summary_rows.append(dict(
                project="TUHO-WIND-1", flag_combo=combo.label,
                total_runtime=0.0, total_da_governed=0.0, total_da_economic=0.0,
                identical=0, identical_economic=0,
                rounding=0, rounding_economic=0, expected_gate_diff=0, unexpected=0, blocking=0,
                phase_c_ready=False,
                phase_c_supported=combo.phase_c_supported,
                validation_error=f"{type(e).__name__}: {e}",
            ))
            print(f"  {combo.label}: EXCEPTION — {e}")

    print("\n=== OBOROVO-SOLAR-1 Dual-Run Matrix ===")
    inputs_oborovo = create_default_oborovo()
    engine_oborovo = build_period_engine(inputs_oborovo)

    oborovo_combos = [c for c in ALL_COMBOS if "OBOROVO-SOLAR-1" in c.valid_for and not c.co2_rev and not c.co2_cit and not c.tax_bridge]
    for combo in oborovo_combos:
        try:
            result = _run_waterfall_with_combo(inputs_oborovo, engine_oborovo, combo)
            rows = _extract_matrix_rows(result, "OBOROVO-SOLAR-1", combo)
            all_rows.extend(rows)
            summary = _summarize_combo(result, "OBOROVO-SOLAR-1", combo)
            summary_rows.append(summary)
            print(f"  {combo.label}: {len(rows)} periods | "
                  f"IDENT={summary['identical']} ROUND={summary['rounding']} "
                  f"EXP={summary['expected_gate_diff']} UNEXP={summary['unexpected']} "
                  f"BLOCK={summary['blocking']} phase_c_ready={summary['phase_c_ready']}"
                  + (f" ERR={summary['validation_error']}" if summary['validation_error'] else ""))
        except Exception as e:
            summary_rows.append(dict(
                project="OBOROVO-SOLAR-1", flag_combo=combo.label,
                total_runtime=0.0, total_da_governed=0.0, total_da_economic=0.0,
                identical=0, identical_economic=0,
                rounding=0, rounding_economic=0, expected_gate_diff=0, unexpected=0, blocking=0,
                phase_c_ready=False,
                phase_c_supported=combo.phase_c_supported,
                validation_error=f"{type(e).__name__}: {e}",
            ))
            print(f"  {combo.label}: EXCEPTION — {e}")
        except Exception as e:
            summary_rows.append(dict(
                project="TUHO-WIND-1", flag_combo=combo.label,
                total_runtime=0.0, total_da_governed=0.0, total_da_economic=0.0,
                identical=0, identical_economic=0,
                rounding=0, rounding_economic=0, expected_gate_diff=0, unexpected=0, blocking=0,
                phase_c_ready=False,
                phase_c_supported=combo.phase_c_supported,
                validation_error=f"{type(e).__name__}: {e}",
            ))
            print(f"  {combo.label}: EXCEPTION — {e}")

    # Write main matrix CSV
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_COLUMNS)
        for row in all_rows:
            writer.writerow(row.to_csv_row())

    # Write summary CSV
    summary_path = CSV_PATH.with_name("phase9_distributionaccount_dualrun_summary.csv")
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "project", "flag_combo",
            "total_runtime", "total_da_governed", "total_da_economic",
            "identical", "identical_economic",
            "rounding", "rounding_economic",
            "expected_gate_diff", "unexpected", "blocking",
            "phase_c_ready", "phase_c_supported", "validation_error",
        ])
        writer.writeheader()
        for sr in summary_rows:
            writer.writerow({k: str(v) for k, v in sr.items()})

    data_rows = [r for r in all_rows if r.classification not in ("NO_DUALRUN_RESULT", "DUALRUN_EXCEPTION")]
    blocking_total = sum(1 for r in data_rows if r.classification == "BLOCKING")
    unexpected_total = sum(1 for r in data_rows if r.classification == "UNEXPECTED")
    ready_combos = sum(1 for s in summary_rows if s.get("phase_c_ready") and s.get("validation_error") is None)

    print(f"\n=== Matrix Population Summary ===")
    print(f"Matrix CSV: {CSV_PATH}")
    print(f"Data rows: {len(data_rows)}  BLOCKING: {blocking_total}  UNEXPECTED: {unexpected_total}")
    print(f"Phase-C-ready combos: {ready_combos}/{len(summary_rows)}")
    print(f"Summary CSV: {summary_path}")

    return all_rows, summary_rows


if __name__ == "__main__":
    rows, summary = run_matrix_population()