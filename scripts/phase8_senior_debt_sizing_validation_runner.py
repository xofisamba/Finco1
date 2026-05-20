"""scripts/phase8_senior_debt_sizing_validation_runner.py
Phase 8: Senior Debt Sizing Canonical Wiring — Validation Runner.

Runs TUHO and Oborovo with use_senior_debt_sizing_engine=False and =True
and compares all key metrics to confirm no drift.

Validation only — no runtime promotion.
"""

import csv
import sys
from dataclasses import replace
from app.project_factories import create_default_tuho_wind1, create_default_oborovo
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from app.ui_runner import _build_period_engine


def _run(project, flag_value):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    config = replace(config, use_senior_debt_sizing_engine=flag_value)
    return WaterfallRunner(project, engine).run(config)


def _metrics(result):
    op_periods = [p for p in result.periods if getattr(p, "is_operation", False)]
    dscrs = [getattr(p, "dscr", 0.0) for p in op_periods
             if hasattr(p, "dscr") and not (getattr(p, "dscr", 0) in (0.0, float("inf")))]
    return {
        "total_senior_ds_keur": result.total_senior_ds_keur,
        "avg_dscr": sum(dscrs) / len(dscrs) if dscrs else 0.0,
        "min_dscr": min(dscrs) if dscrs else 0.0,
        "equity_irr": result.equity_irr,
        "project_irr": result.project_irr,
        "total_distribution_keur": result.total_distribution_keur,
    }


def _canonical_result(result):
    if hasattr(result, "_canonical_senior_debt_sizing") and result._canonical_senior_debt_sizing is not None:
        cs = result._canonical_senior_debt_sizing
        return {
            "total_ds_capacity_keur": cs.total_debt_service_capacity_keur,
            "annuity_keur": cs.annuity_keur,
            "sizing_cfads_source": cs.notes,
        }
    return None


def run_comparison(project_name, project_fn):
    print(f"\n{'='*60}")
    print(f"  {project_name}")
    print(f"{'='*60}")

    result_off = _run(project_fn(), False)
    result_on  = _run(project_fn(), True)

    m_off = _metrics(result_off)
    m_on  = _metrics(result_on)
    canon = _canonical_result(result_on)

    print(f"\n  Flag=False (baseline) | Flag=True (canonical wiring)")
    print(f"  {'Metric':<30} {'Baseline':>12} {'Canonical':>12} {'Delta':>10}")
    print(f"  {'-'*66}")

    comparisons = [
        ("Senior Debt (kEUR)",         m_off["total_senior_ds_keur"],   m_on["total_senior_ds_keur"],   1.0),
        ("Avg DSCR",                   m_off["avg_dscr"],               m_on["avg_dscr"],               0.001),
        ("Min DSCR",                   m_off["min_dscr"],               m_on["min_dscr"],               0.001),
        ("Equity IRR",                 m_off["equity_irr"]*100,         m_on["equity_irr"]*100,         0.01),
        ("Project IRR",                m_off["project_irr"]*100,        m_on["project_irr"]*100,        0.01),
        ("Total Distributions (kEUR)", m_off["total_distribution_keur"],m_on["total_distribution_keur"],1.0),
    ]

    rows = []
    for label, v_off, v_on, tol in comparisons:
        delta = v_on - v_off
        status = "PASS" if abs(delta) <= tol else "FAIL"
        print(f"  {label:<30} {v_off:>12.4f} {v_on:>12.4f} {delta:>+10.4f}  {status}")
        rows.append({
            "project": project_name,
            "metric": label,
            "flag_false_value": round(v_off, 4),
            "flag_true_value": round(v_on, 4),
            "delta": round(delta, 4),
            "expected_to_change": "no",
            "status": status,
            "notes": "",
        })

    if canon:
        print(f"\n  Canonical Senior Debt Sizing Result (flag=True):")
        print(f"    Total DS Capacity: {canon['total_ds_capacity_keur']:.2f} kEUR")
        print(f"    Annuity (reference): {canon['annuity_keur']:.2f} kEUR/period")
        print(f"    Sizing CFADS source: {canon['sizing_cfads_source'][:60]}...")
        rows.append({
            "project": project_name,
            "metric": "Canonical Total DS Capacity (kEUR)",
            "flag_false_value": "",
            "flag_true_value": round(canon["total_ds_capacity_keur"], 2),
            "delta": "",
            "expected_to_change": "n/a",
            "status": "INFO",
            "notes": canon["sizing_cfads_source"],
        })
        rows.append({
            "project": project_name,
            "metric": "Canonical Annuity (kEUR/period)",
            "flag_false_value": "",
            "flag_true_value": round(canon["annuity_keur"], 2),
            "delta": "",
            "expected_to_change": "n/a",
            "status": "INFO",
            "notes": "Reference only — not a runtime override",
        })
    else:
        print(f"\n  Canonical Senior Debt Sizing: NOT ATTACHED (flag=True but result is None)")
        rows.append({
            "project": project_name,
            "metric": "Canonical Wiring Attached",
            "flag_false_value": "n/a",
            "flag_true_value": "None",
            "delta": "",
            "expected_to_change": "n/a",
            "status": "FAIL",
            "notes": "_canonical_senior_debt_sizing not attached",
        })

    # R99/R102 check
    r99_on = hasattr(result_on, "r99_audit") and result_on.r99_audit is not None
    r102_on = hasattr(result_on, "r102_audit") and result_on.r102_audit is not None
    r99_status = "FAIL" if r99_on else "PASS"
    r102_status = "FAIL" if r102_on else "PASS"
    print(f"\n  R99/R102 BLOCKED check:")
    print(f"    R99 audit exposed: {r99_on} — {r99_status}")
    print(f"    R102 audit exposed: {r102_on} — {r102_status}")
    rows.append({
        "project": project_name,
        "metric": "R99 Not Promoted",
        "flag_false_value": "n/a",
        "flag_true_value": "n/a",
        "delta": "",
        "expected_to_change": "no",
        "status": r99_status,
        "notes": "R99 not in result attributes",
    })
    rows.append({
        "project": project_name,
        "metric": "R102 Not Promoted",
        "flag_false_value": "n/a",
        "flag_true_value": "n/a",
        "delta": "",
        "expected_to_change": "no",
        "status": r102_status,
        "notes": "R102 not in result attributes",
    })

    return rows


def main():
    print("Phase 8: Senior Debt Sizing Canonical Wiring — Validation")
    print("=" * 60)
    print("Flag semantics:")
    print("  use_senior_debt_sizing_engine=False → legacy waterfall unchanged")
    print("  use_senior_debt_sizing_engine=True  → canonical engine computes")
    print("    sizing_cfads (proxy from ebitda * (1-tax)) + dscr_schedule")
    print("    Result attached as _canonical_senior_debt_sizing audit attribute")
    print("  NOTE: real Macro!R50 values not yet wired — using proxy CFADS")
    print("  NOTE: no runtime debt override yet — validation/audit only")

    all_rows = []
    all_rows.extend(run_comparison("TUHO-WIND-1", create_default_tuho_wind1))
    all_rows.extend(run_comparison("OBOROVO-SOLAR-1", create_default_oborovo))

    # Summary
    print(f"\n{'='*60}")
    print("  DRIFT SUMMARY")
    print(f"{'='*60}")
    failures = [r for r in all_rows if r["status"] == "FAIL"]
    if failures:
        print(f"  {len(failures)} FAILURES:")
        for f in failures:
            print(f"    {f['project']} | {f['metric']} | delta={f['delta']}")
    else:
        print("  All checks PASSED")

    # Write CSV
    csv_path = "reports/phase8_senior_debt_sizing_flag_comparison.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "project", "metric", "flag_false_value", "flag_true_value",
            "delta", "expected_to_change", "status", "notes"
        ])
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\n  CSV written: {csv_path}")

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())