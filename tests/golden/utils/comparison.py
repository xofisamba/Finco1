"""Tuple comparison helpers for golden validation.

Generic, reusable utilities with no business logic.
No external services, no UI, no Excel formatting dependency.
"""
from __future__ import annotations

import math
from typing import Any, Literal

ToleranceSpec = dict[str, Any]  # {"type": "pct"|"abs"|"rel"|"bps", "value": float}


def compare_values(
    actual: float,
    golden: float,
    *,
    abs_tol: float | None = None,
    rel_tol: float | None = None,
    bps_tol: float | None = None,
    pct_tol: float | None = None,
) -> dict[str, Any]:
    """Compare two scalar values with tolerance.

    Returns dict with:
        pass: bool
        delta: float (actual - golden)
        tolerance_used: float (in same unit as delta)
        tolerance_type: str

    Raises ValueError if no tolerance is provided.
    """
    if all(t is None for t in [abs_tol, rel_tol, bps_tol, pct_tol]):
        raise ValueError("At least one tolerance must be provided")

    delta = actual - golden

    if not math.isfinite(actual) or not math.isfinite(golden):
        # NaN/Inf comparisons fail immediately — no tolerance can save them
        return {
            "pass": False,
            "delta": delta,
            "tolerance_used": 0.0,
            "tolerance_type": "none",
            "message": f"non-finite value: actual={actual}, golden={golden}",
        }

    if pct_tol is not None:
        tolerance_used = abs(pct_tol * golden)
        tolerance_type = "pct"
    elif bps_tol is not None:
        tolerance_used = bps_tol / 10000  # bps → fraction
        tolerance_type = "bps"
    elif rel_tol is not None:
        tolerance_used = abs(rel_tol * golden)
        tolerance_type = "rel"
    else:
        tolerance_used = abs_tol
        tolerance_type = "abs"

    if tolerance_type in ("rel", "pct", "bps"):
        if abs(golden) < 1e-12:
            # Near-zero golden: fall back to abs tolerance
            tolerance_used = abs_tol if abs_tol is not None else 1e-9
            tolerance_type = "abs"

    passed = abs(delta) <= tolerance_used + 1e-18  # small epsilon for fp drift

    return {
        "pass": passed,
        "delta": delta,
        "tolerance_used": tolerance_used,
        "tolerance_type": tolerance_type,
    }


def compare_series(
    actual: tuple[float, ...],
    golden: tuple[float, ...],
    *,
    abs_tol: float | None = None,
    rel_tol: float | None = None,
    pct_tol: float | None = None,
) -> dict[str, Any]:
    """Compare two period-indexed tuples element-by-element.

    Returns dict with:
        pass: bool
        period_count_match: bool
        period_deltas: tuple[float, ...]
        failures: list of (period_index, delta) where tolerance exceeded

    Period count mismatch is a fatal failure — period deltas not computed.
    """
    period_count_match = len(actual) == len(golden)

    if not period_count_match:
        return {
            "pass": False,
            "period_count_match": False,
            "period_deltas": (),
            "failures": [("PERIOD_COUNT_MISMATCH", len(actual), len(golden))],
            "message": f"period count mismatch: actual={len(actual)}, golden={len(golden)}",
        }

    deltas = tuple(actual[i] - golden[i] for i in range(len(golden)))
    failures = []

    for i, delta in enumerate(deltas):
        cmp = compare_values(actual[i], golden[i], abs_tol=abs_tol, rel_tol=rel_tol, pct_tol=pct_tol)
        if not cmp["pass"]:
            failures.append((i, delta))

    passed = len(failures) == 0

    return {
        "pass": passed,
        "period_count_match": True,
        "period_deltas": deltas,
        "failures": failures,
    }


def assert_all_close(
    actual_dict: dict[str, float],
    golden_dict: dict[str, dict],
    *,
    report: bool = False,
) -> dict[str, Any]:
    """Assert all scalars in actual_dict are within tolerance of golden_dict.

    Parameters
    ----------
    actual_dict : dict[str, float]
        Actual metric values, e.g. {"equity_irr_30y": 0.11615}
    golden_dict : dict[str, dict]
        Golden values with tolerance, e.g.:
        {"equity_irr_30y": {"value": 0.1161, "tolerance": {"type": "bps", "value": 10}}}
    report : bool
        If True, prints full delta table on any failure.

    Returns dict with:
        passed: bool
        results: list of per-metric dicts
        failures: list of failed metric names

    Raises AssertionError if any metric fails and report=False.
    """
    results = []
    failures = []

    for metric_name, golden_spec in golden_dict.items():
        actual = actual_dict.get(metric_name)
        if actual is None:
            results.append({
                "metric": metric_name,
                "status": "MISSING",
                "message": f"metric {metric_name!r} not found in actual_dict",
            })
            failures.append(metric_name)
            continue

        tol_spec = golden_spec.get("tolerance", {})
        tol_type = tol_spec.get("type", "abs")
        tol_value = tol_spec.get("value", 1e-9)

        cmp = compare_values(
            actual,
            golden_spec["value"],
            **{tol_type + "_tol": tol_value},
        )

        status = "PASS" if cmp["pass"] else "FAIL"
        results.append({
            "metric": metric_name,
            "status": status,
            "actual": actual,
            "golden": golden_spec["value"],
            "delta": cmp["delta"],
            "tolerance_type": tol_type,
            "tolerance_value": tol_value,
            "tolerance_used": cmp["tolerance_used"],
        })

        if not cmp["pass"]:
            failures.append(metric_name)

    if report and failures:
        _print_delta_table(results, failures)

    passed = len(failures) == 0

    if not passed and not report:
        raise AssertionError(
            f"Golden validation failed for: {failures}. "
            "Set report=True or call with report=True for details."
        )

    return {"passed": passed, "results": results, "failures": failures}


def _print_delta_table(results: list[dict], failures: list[str]) -> None:
    """Print a formatted delta table to stdout."""
    print("\n=== Golden Validation Delta Report ===")
    print(f"{'Metric':<30} {'Actual':>12} {'Golden':>12} {'Delta':>12} {'Tol':>10} {'Status':>6}")
    print("-" * 88)
    for r in results:
        delta_str = f"{r['delta']:.6f}" if r['status'] != "MISSING" else "N/A"
        tol_str = f"±{r.get('tolerance_value', 0):.6f}" if r['status'] != "MISSING" else "N/A"
        actual_str = f"{r['actual']:.6f}" if r['status'] != "MISSING" else "N/A"
        golden_str = f"{r['golden']:.6f}" if r['status'] != "MISSING" else "N/A"
        status_marker = "⚠️  " if r['metric'] in failures else "   "
        print(f"{status_marker}{r['metric']:<30} {actual_str:>12} {golden_str:>12} {delta_str:>12} {tol_str:>10} {r['status']:>6}")
    print("=" * 88)


def compare_with_spec(
    actual: float,
    golden: float,
    tol_spec: ToleranceSpec,
) -> dict[str, Any]:
    """Compare actual to golden using a tolerance spec dict.

    tol_spec: {"type": "pct"|"abs"|"rel"|"bps", "value": float}
    """
    tol_type = tol_spec.get("type", "abs")
    tol_value = tol_spec.get("value", 1e-9)
    return compare_values(actual, golden, **{tol_type + "_tol": tol_value})