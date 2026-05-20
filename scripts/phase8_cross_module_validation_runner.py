"""scripts/phase8_cross_module_validation_runner.py

Cross-module runtime validation for Phase 8.
Tests all supported combinations of canonical runtime flags for TUHO and Oborovo.
VALIDATION ONLY — no new runtime promotion.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Literal

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.project_factories import create_default_tuho_wind1, create_default_oborovo
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from app.ui_runner import _build_period_engine as build_period_engine
from dataclasses import replace


@dataclass(frozen=True)
class FlagCombo:
    shl: bool
    dep: bool
    tax_bridge: bool
    label: str


ALL_COMBOS = [
    FlagCombo(shl=False, dep=False, tax_bridge=False, label="SHL=OFF Dep=OFF TaxBridge=OFF"),
    FlagCombo(shl=True,  dep=False, tax_bridge=False, label="SHL=ON  Dep=OFF TaxBridge=OFF"),
    FlagCombo(shl=False, dep=True,  tax_bridge=False, label="SHL=OFF Dep=ON  TaxBridge=OFF"),
    FlagCombo(shl=True,  dep=True,  tax_bridge=False, label="SHL=ON  Dep=ON  TaxBridge=OFF"),
    FlagCombo(shl=False, dep=True,  tax_bridge=True,  label="SHL=OFF Dep=ON  TaxBridge=ON"),
    FlagCombo(shl=True,  dep=True,  tax_bridge=True,  label="SHL=ON  Dep=ON  TaxBridge=ON"),
]

# TaxBridge only valid for TUHO-WIND-1
TUHO_COMBOS = ALL_COMBOS  # all 6
OBOROVO_COMBOS = [c for c in ALL_COMBOS if not c.tax_bridge]  # 4 combos (skip TaxBridge)


@dataclass
class ValidationMetrics:
    project: str
    shl_flag: bool
    dep_flag: bool
    tax_bridge_flag: bool
    total_senior_ds_keur: float
    total_debt_service_keur: float
    avg_dscr: float
    min_dscr: float
    equity_irr: float
    project_irr: float
    total_shl_balance_keur: float
    depreciation_keur_total: float
    tax_depreciation_audit_keur_total: float
    total_distributions_keur: float
    r99_exposed: bool
    r102_exposed: bool


def _build_config(project, shl: bool, dep: bool, tax_bridge: bool):
    engine = build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    config = replace(config, use_shl_canonical_engine=shl)
    config = replace(config, use_depreciation_canonical_engine=dep)
    config = replace(config, use_tax_bridge_engine=tax_bridge)
    return WaterfallRunner(project, engine).run(config)


def _extract_metrics(result, project_code: str) -> ValidationMetrics:
    periods = result.periods
    op_periods = [p for p in periods if getattr(p, 'is_operation', False)]

    total_ds = sum(getattr(p, "senior_ds_keur", 0.0) for p in periods)
    dscrs = [getattr(p, "dscr", 0.0) for p in op_periods if hasattr(p, "dscr") and getattr(p, "dscr", 0) > 0]
    avg_dscr = sum(d for d in dscrs if not (d == float("inf") or d != d)) / len([d for d in dscrs if not (d == float("inf") or d != d)]) if dscrs and any(not (d == float("inf") or d != d) for d in dscrs) else 0.0  # filter NaN+inf
    min_dscr = min(dscrs) if dscrs else 0.0

    dep_total = sum(getattr(p, 'depreciation_keur', 0.0) for p in periods)
    tax_dep_total = sum(getattr(p, 'tax_depreciation_audit_keur', 0.0) for p in periods)
    dist_total = sum(getattr(p, 'distribution_keur', 0.0) for p in periods)

    shl_balance = result.total_shl_balance_keur if hasattr(result, 'total_shl_balance_keur') else 0.0

    r99_exposed = hasattr(result, 'r99_audit_rows') or hasattr(result, 'r99')
    r102_exposed = hasattr(result, 'r102_audit_rows') or hasattr(result, 'r102')

    return ValidationMetrics(
        project=project_code,
        shl_flag=getattr(result, 'use_shl_canonical_engine', False),
        dep_flag=getattr(result, 'use_depreciation_canonical_engine', False),
        tax_bridge_flag=getattr(result, 'use_tax_bridge_engine', False),
        total_senior_ds_keur=result.total_senior_ds_keur,
        total_debt_service_keur=total_ds,
        avg_dscr=avg_dscr,
        min_dscr=min_dscr,
        equity_irr=result.equity_irr,
        project_irr=result.project_irr,
        total_shl_balance_keur=shl_balance,
        depreciation_keur_total=dep_total,
        tax_depreciation_audit_keur_total=tax_dep_total,
        total_distributions_keur=dist_total,
        r99_exposed=r99_exposed,
        r102_exposed=r102_exposed,
    )


def run_validation():
    results: list[ValidationMetrics] = []

    print("=== TUHO-WIND-1 Validation ===")
    project = create_default_tuho_wind1()
    for combo in TUHO_COMBOS:
        try:
            result = _build_config(project, combo.shl, combo.dep, combo.tax_bridge)
            m = _extract_metrics(result, "TUHO-WIND-1")
            m = ValidationMetrics(
                project="TUHO-WIND-1",
                shl_flag=combo.shl,
                dep_flag=combo.dep,
                tax_bridge_flag=combo.tax_bridge,
                total_senior_ds_keur=m.total_senior_ds_keur,
                total_debt_service_keur=m.total_debt_service_keur,
                avg_dscr=m.avg_dscr,
                min_dscr=m.min_dscr,
                equity_irr=m.equity_irr,
                project_irr=m.project_irr,
                total_shl_balance_keur=m.total_shl_balance_keur,
                depreciation_keur_total=m.depreciation_keur_total,
                tax_depreciation_audit_keur_total=m.tax_depreciation_audit_keur_total,
                total_distributions_keur=m.total_distributions_keur,
                r99_exposed=m.r99_exposed,
                r102_exposed=m.r102_exposed,
            )
            results.append(m)
            print(f"  {combo.label}: DS={m.total_senior_ds_keur:.0f}k EUR | "
                  f"avgDSCR={m.avg_dscr:.3f} | "
                  f"IRR={m.equity_irr:.4f} | "
                  f"R99={m.r99_exposed} R102={m.r102_exposed}")
        except Exception as e:
            print(f"  {combo.label}: ERROR — {e}")

    print("\n=== OBOROVO-SOLAR-1 Validation ===")
    project = create_default_oborovo()
    for combo in OBOROVO_COMBOS:
        try:
            result = _build_config(project, combo.shl, combo.dep, combo.tax_bridge)
            m = _extract_metrics(result, "OBOROVO-SOLAR-1")
            m = ValidationMetrics(
                project="OBOROVO-SOLAR-1",
                shl_flag=combo.shl,
                dep_flag=combo.dep,
                tax_bridge_flag=combo.tax_bridge,
                total_senior_ds_keur=m.total_senior_ds_keur,
                total_debt_service_keur=m.total_debt_service_keur,
                avg_dscr=m.avg_dscr,
                min_dscr=m.min_dscr,
                equity_irr=m.equity_irr,
                project_irr=m.project_irr,
                total_shl_balance_keur=m.total_shl_balance_keur,
                depreciation_keur_total=m.depreciation_keur_total,
                tax_depreciation_audit_keur_total=m.tax_depreciation_audit_keur_total,
                total_distributions_keur=m.total_distributions_keur,
                r99_exposed=m.r99_exposed,
                r102_exposed=m.r102_exposed,
            )
            results.append(m)
            print(f"  {combo.label}: DS={m.total_senior_ds_keur:.0f}k EUR | "
                  f"avgDSCR={m.avg_dscr:.3f} | "
                  f"IRR={m.equity_irr:.4f} | "
                  f"R99={m.r99_exposed} R102={m.r102_exposed}")
        except Exception as e:
            print(f"  {combo.label}: ERROR — {e}")

    return results


def write_csv(results: list[ValidationMetrics], path: Path):
    baseline_tuho = next(r for r in results if r.project == "TUHO-WIND-1" and not r.shl_flag and not r.dep_flag and not r.tax_bridge_flag)
    baseline_oboro = next(r for r in results if r.project == "OBOROVO-SOLAR-1" and not r.shl_flag and not r.dep_flag and not r.tax_bridge_flag)

    METRICS = [
        ("total_senior_ds_keur", "Senior Debt (kEUR)", True),
        ("total_debt_service_keur", "Total Debt Service (kEUR)", True),
        ("avg_dscr", "Avg DSCR", True),
        ("min_dscr", "Min DSCR", True),
        ("equity_irr", "Equity IRR", True),
        ("project_irr", "Project IRR", True),
        ("total_shl_balance_keur", "SHL Balance (kEUR)", True),
        ("depreciation_keur_total", "Book Depreciation (kEUR)", False),
        ("tax_depreciation_audit_keur_total", "Tax Depreciation (kEUR)", False),
        ("total_distributions_keur", "Distributions (kEUR)", True),
    ]

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "project", "shl_flag", "depreciation_flag", "tax_bridge_flag",
            "metric", "baseline_value", "test_value", "delta",
            "expected_to_change", "status", "notes"
        ])

        for r in results:
            baseline = baseline_tuho if r.project == "TUHO-WIND-1" else baseline_oboro
            for attr, name, expect_unchanged in METRICS:
                val = getattr(r, attr)
                base_val = getattr(baseline, attr)
                delta = val - base_val

                expected = "no" if expect_unchanged else "yes"
                if expect_unchanged:
                    status = "PASS" if abs(delta) <= 0.001 else "FAIL"
                else:
                    status = "N/A"

                notes = ""
                if attr == "depreciation_keur_total" and r.dep_flag:
                    notes = "canonical depreciation active"
                elif attr == "tax_depreciation_audit_keur_total" and (r.dep_flag or r.tax_bridge_flag):
                    notes = "tax bridge/depr canonical active"
                elif attr == "total_shl_balance_keur" and r.shl_flag:
                    notes = "canonical SHL active"

                writer.writerow([
                    r.project, r.shl_flag, r.dep_flag, r.tax_bridge_flag,
                    name, f"{base_val:.4f}", f"{val:.4f}", f"{delta:.6f}",
                    expected, status, notes
                ])

        # R99/R102 rows
        for r in results:
            for field_name, label in [("r99_exposed", "R99 Exposed"), ("r102_exposed", "R102 Exposed")]:
                val = getattr(r, field_name)
                writer.writerow([
                    r.project, r.shl_flag, r.dep_flag, r.tax_bridge_flag,
                    label, "False", str(val), "N/A",
                    "no", "PASS" if not val else "FAIL",
                    "R99/R102 must remain BLOCKED"
                ])


if __name__ == "__main__":
    results = run_validation()

    csv_path = Path(__file__).parent.parent / "reports" / "phase8_cross_module_validation_matrix.csv"
    csv_path.parent.mkdir(exist_ok=True)
    write_csv(results, csv_path)
    print(f"\nCSV written to {csv_path}")

    print("\n=== R99/R102 BLOCKED CHECK ===")
    for r in results:
        for field_name, label in [("r99_exposed", "R99"), ("r102_exposed", "R102")]:
            val = getattr(r, field_name)
            status = "BLOCKED ✓" if not val else "FAIL ✗"
            print(f"  {r.project} {r.shl_flag}/{r.dep_flag}/{r.tax_bridge_flag} {label}: {status}")

    print("\n=== DRIFT SUMMARY ===")
    baseline_tuho = next(x for x in results if x.project == "TUHO-WIND-1" and not x.shl_flag and not x.dep_flag and not x.tax_bridge_flag)
    for r in results:
        if r.project == "TUHO-WIND-1":
            baseline = baseline_tuho
        else:
            continue
        ds_drift = abs(r.total_senior_ds_keur - baseline.total_senior_ds_keur)
        irr_drift = abs(r.equity_irr - baseline.equity_irr)
        dist_drift = abs(r.total_distributions_keur - baseline.total_distributions_keur)
        print(f"  {r.shl_flag}/{r.dep_flag}/{r.tax_bridge_flag}: "
              f"DS_drift={ds_drift:.2f}k EUR | IRR_drift={irr_drift:.5f}pp | "
              f"Dist_drift={dist_drift:.2f}k EUR")
