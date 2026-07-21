"""
finco_parity.comparison — Structural and numeric comparison of legacy-engine snapshots.

Compares a *current* snapshot dict against a *baseline* snapshot dict and
classifies all differences.  The comparison is purely structural — it never
runs the engine, reads files, or touches the manifest.

Classification hierarchy (most-severe wins per path, but all are reported):
  IDENTICAL           — no differences
  SCHEMA_DRIFT        — schema_version changed
  PROVENANCE_DRIFT    — any baseline identity / capture provenance field changed
  STRUCTURAL_DRIFT    — key added/removed, list length changed, type changed
                        (exception: int vs float with equal value → IDENTICAL)
  AVAILABILITY_DRIFT  — populated↔None transition or unavailable_fields change
  VALUE_DRIFT         — comparable numeric/string/bool value changed

All differences are accumulated; the first difference does not suppress the rest.

Tolerance
---------
Default tolerance is zero.  An optional Tolerance object may be supplied for
diagnostic use only.  The baseline CI guardrail always uses zero tolerance.
No tolerance configuration is stored in production code.

Import boundary
---------------
This module may only import from:
  - Python standard library
  - finco_parity.*
It must NOT import from app.*, domain.*, finco_core.*, main_web, main_api.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DriftKind(str, Enum):
    IDENTICAL = "IDENTICAL"
    SCHEMA_DRIFT = "SCHEMA_DRIFT"
    PROVENANCE_DRIFT = "PROVENANCE_DRIFT"
    STRUCTURAL_DRIFT = "STRUCTURAL_DRIFT"
    AVAILABILITY_DRIFT = "AVAILABILITY_DRIFT"
    VALUE_DRIFT = "VALUE_DRIFT"


# Severity order (higher index = more severe).  Used to pick the overall status.
_SEVERITY = [
    DriftKind.IDENTICAL,
    DriftKind.VALUE_DRIFT,
    DriftKind.AVAILABILITY_DRIFT,
    DriftKind.STRUCTURAL_DRIFT,
    DriftKind.PROVENANCE_DRIFT,
    DriftKind.SCHEMA_DRIFT,
]
_SEVERITY_RANK = {k: i for i, k in enumerate(_SEVERITY)}


@dataclass
class Difference:
    kind: DriftKind
    path: str
    baseline_value: Any
    current_value: Any
    absolute_delta: float | None = None
    relative_delta: float | None = None

    def to_dict(self) -> dict:
        d: dict = {
            "kind": self.kind.value,
            "path": self.path,
            "baseline_value": self.baseline_value,
            "current_value": self.current_value,
        }
        if self.absolute_delta is not None:
            d["absolute_delta"] = self.absolute_delta
        if self.relative_delta is not None:
            d["relative_delta"] = self.relative_delta
        return d


@dataclass
class ComparisonResult:
    baseline_id: str
    status: DriftKind
    differences: list[Difference] = field(default_factory=list)

    def is_identical(self) -> bool:
        return self.status == DriftKind.IDENTICAL

    def to_dict(self) -> dict:
        return {
            "baseline_id": self.baseline_id,
            "status": self.status.value,
            "difference_count": len(self.differences),
            "differences": [d.to_dict() for d in self.differences],
        }


@dataclass
class Tolerance:
    """Optional diagnostic tolerance.  Default is zero (exact)."""
    absolute: float = 0.0
    relative: float = 0.0


_ZERO_TOLERANCE = Tolerance()

# Top-level provenance fields — changes here are PROVENANCE_DRIFT.
_PROVENANCE_KEYS = frozenset({
    "baseline_id",
    "engine_designation",
    "baseline_commit_sha",
    "run_path_id",
    "input_source_id",
})


def compare_snapshots(
    baseline: dict[str, Any],
    current: dict[str, Any],
    baseline_id: str = "",
    tolerance: Tolerance | None = None,
) -> ComparisonResult:
    """Compare *current* against *baseline* and return a ComparisonResult.

    Args:
        baseline: The committed baseline snapshot dict.
        current:  The freshly captured snapshot dict.
        baseline_id: Label for the result (uses baseline["baseline_id"] if empty).
        tolerance: Optional diagnostic tolerance.  Pass None or Tolerance() for
                   exact (zero-tolerance) comparison.

    Returns:
        ComparisonResult with all detected differences, sorted by path.
    """
    if not baseline_id:
        baseline_id = baseline.get("baseline_id", "")

    tol = tolerance if tolerance is not None else _ZERO_TOLERANCE
    diffs: list[Difference] = []

    _compare_values(baseline, current, "", diffs, tol)

    diffs.sort(key=lambda d: (d.path, d.kind.value))

    if not diffs:
        status = DriftKind.IDENTICAL
    else:
        status = max(diffs, key=lambda d: _SEVERITY_RANK[d.kind]).kind

    return ComparisonResult(
        baseline_id=baseline_id,
        status=status,
        differences=diffs,
    )


# ---------------------------------------------------------------------------
# Internal recursive comparison
# ---------------------------------------------------------------------------

def _compare_values(
    baseline: Any,
    current: Any,
    path: str,
    diffs: list[Difference],
    tol: Tolerance,
) -> None:
    kind = _classify_path(path)

    # Schema drift — schema_version changed.
    if path == "schema_version":
        if baseline != current:
            diffs.append(Difference(
                kind=DriftKind.SCHEMA_DRIFT,
                path=path,
                baseline_value=baseline,
                current_value=current,
            ))
        return

    # Provenance drift.
    if kind == DriftKind.PROVENANCE_DRIFT:
        if baseline != current:
            diffs.append(Difference(
                kind=DriftKind.PROVENANCE_DRIFT,
                path=path,
                baseline_value=baseline,
                current_value=current,
            ))
        return

    # unavailable_fields and unavailable_sections — availability drift.
    if path in ("unavailable_fields", "unavailable_sections"):
        if baseline != current:
            diffs.append(Difference(
                kind=DriftKind.AVAILABILITY_DRIFT,
                path=path,
                baseline_value=baseline,
                current_value=current,
            ))
        return

    # Both None — identical.
    if baseline is None and current is None:
        return

    # None ↔ non-None — availability drift.
    if baseline is None or current is None:
        diffs.append(Difference(
            kind=DriftKind.AVAILABILITY_DRIFT,
            path=path,
            baseline_value=baseline,
            current_value=current,
        ))
        return

    # Type mismatch — exact types required, with one narrow exception.
    # bool must be checked before int because bool is a subclass of int in Python.
    # True vs 1 → STRUCTURAL_DRIFT; 1 vs 1 → IDENTICAL.
    # Narrow numeric exception: int vs float with equal values → IDENTICAL.
    # Rationale: 0 vs 0.0 and 1 vs 1.0 carry no financial distinction; preserving 158
    # fake STRUCTURAL_DRIFT records for representation noise is rejected per governance review.
    # bool is explicitly excluded (True vs 1 must remain STRUCTURAL_DRIFT).
    b_type = type(baseline)
    c_type = type(current)
    if b_type != c_type:
        _both_numeric = (
            isinstance(baseline, (int, float)) and not isinstance(baseline, bool)
            and isinstance(current, (int, float)) and not isinstance(current, bool)
        )
        if _both_numeric and float(baseline) == float(current):
            pass  # numerically equal int/float — treat as IDENTICAL, no diff
        else:
            diffs.append(Difference(
                kind=DriftKind.STRUCTURAL_DRIFT,
                path=path,
                baseline_value=baseline,
                current_value=current,
            ))
            return

    # Dict comparison.
    if isinstance(baseline, dict):
        if not isinstance(current, dict):
            diffs.append(Difference(
                kind=DriftKind.STRUCTURAL_DRIFT,
                path=path,
                baseline_value=type(baseline).__name__,
                current_value=type(current).__name__,
            ))
            return
        b_keys = set(baseline.keys())
        c_keys = set(current.keys())
        for k in sorted(b_keys - c_keys):
            child_path = f"{path}.{k}" if path else k
            diffs.append(Difference(
                kind=DriftKind.STRUCTURAL_DRIFT,
                path=child_path,
                baseline_value=baseline[k],
                current_value="<missing>",
            ))
        for k in sorted(c_keys - b_keys):
            child_path = f"{path}.{k}" if path else k
            diffs.append(Difference(
                kind=DriftKind.STRUCTURAL_DRIFT,
                path=child_path,
                baseline_value="<missing>",
                current_value=current[k],
            ))
        for k in sorted(b_keys & c_keys):
            child_path = f"{path}.{k}" if path else k
            _compare_values(baseline[k], current[k], child_path, diffs, tol)
        return

    # List comparison.
    if isinstance(baseline, list):
        if not isinstance(current, list):
            diffs.append(Difference(
                kind=DriftKind.STRUCTURAL_DRIFT,
                path=path,
                baseline_value=type(baseline).__name__,
                current_value=type(current).__name__,
            ))
            return
        if len(baseline) != len(current):
            diffs.append(Difference(
                kind=DriftKind.STRUCTURAL_DRIFT,
                path=path,
                baseline_value=len(baseline),
                current_value=len(current),
            ))
            return
        for i, (bv, cv) in enumerate(zip(baseline, current)):
            _compare_values(bv, cv, f"{path}[{i}]", diffs, tol)
        return

    # Numeric comparison (bool already dispatched above via type mismatch or dict/list).
    if (
        isinstance(baseline, (int, float))
        and isinstance(current, (int, float))
        and not isinstance(baseline, bool)
        and not isinstance(current, bool)
    ):
        if math.isnan(baseline) or math.isnan(current):
            diffs.append(Difference(
                kind=DriftKind.VALUE_DRIFT,
                path=path,
                baseline_value=baseline,
                current_value=current,
            ))
            return
        abs_delta = current - baseline
        if abs(abs_delta) == 0.0:
            return
        # Check within tolerance.
        if abs(abs_delta) <= tol.absolute:
            return
        rel_delta: float | None = None
        if baseline != 0:
            rel_delta = abs_delta / abs(baseline)
            if tol.relative > 0 and abs(rel_delta) <= tol.relative:
                return
        diffs.append(Difference(
            kind=DriftKind.VALUE_DRIFT,
            path=path,
            baseline_value=baseline,
            current_value=current,
            absolute_delta=abs_delta,
            relative_delta=rel_delta,
        ))
        return

    # Scalar comparison (str, bool, etc.).
    if baseline != current:
        diffs.append(Difference(
            kind=DriftKind.VALUE_DRIFT,
            path=path,
            baseline_value=baseline,
            current_value=current,
        ))


def _classify_path(path: str) -> DriftKind:
    """Return the appropriate DriftKind for top-level provenance fields."""
    top = path.split(".")[0].split("[")[0]
    if top in _PROVENANCE_KEYS:
        return DriftKind.PROVENANCE_DRIFT
    return DriftKind.VALUE_DRIFT


# ---------------------------------------------------------------------------
# Human-readable formatter
# ---------------------------------------------------------------------------

def format_comparison_report(result: ComparisonResult, max_diffs: int = 50) -> str:
    """Return a human-readable text report of *result*.

    Differences are sorted deterministically by JSON path.
    Output is bounded by *max_diffs* to keep CI logs readable.
    No ANSI escape codes are used.
    The formatter does not interpret whether a financial change is good or bad.
    """
    lines: list[str] = [
        f"Baseline: {result.baseline_id}",
        f"Status:   {result.status.value}",
        f"Differences: {len(result.differences)}",
    ]
    if not result.differences:
        return "\n".join(lines)

    lines.append("")
    for i, diff in enumerate(result.differences[:max_diffs], 1):
        lines.append(f"{i}. {diff.path}")
        lines.append(f"   kind:     {diff.kind.value}")
        lines.append(f"   baseline: {diff.baseline_value!r}")
        lines.append(f"   current:  {diff.current_value!r}")
        if diff.absolute_delta is not None:
            lines.append(f"   absolute delta: {diff.absolute_delta}")
        if diff.relative_delta is not None:
            lines.append(f"   relative delta: {diff.relative_delta:.6%}")
        lines.append("")

    if len(result.differences) > max_diffs:
        lines.append(
            f"... {len(result.differences) - max_diffs} additional differences not shown."
        )

    return "\n".join(lines)
