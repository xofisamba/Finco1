"""Snapshot capture and validation context for golden validation.

Generic, reusable utilities with no business logic.
"""
from __future__ import annotations

import datetime
import hashlib
import os
import sys
from typing import Any

# Import comparison utilities (generic, no business logic)
try:
    from tests.golden.utils.comparison import compare_with_spec
except ImportError:
    # Allow running without full golden package (standalone test)
    compare_with_spec = None  # type: ignore


class SnapshotContext:
    """Context manager for capturing and validating validation snapshots.

    Usage:
        with SnapshotContext(fixture_name="oborovo", model_version="main@abc123") as ctx:
            ctx.capture("total_capex_keur", result.total_capex_keur)
            ctx.capture("equity_irr_30y", result.equity_irr_30y)
            ctx.capture("debt_service_schedule_keur", result.debt_service_schedule)
        # on __exit__: report printed, failures raise if not suppressed

    Attributes
    ----------
    fixture_name : str
        Name of the golden fixture (e.g., "oborovo", "tuho")
    model_version : str
        Git ref of the model used (e.g., "main@9f2c570")
    captures : dict[str, Any]
        All captured values during the context
    failures : list[dict]
        Metrics that failed validation
    """

    def __init__(
        self,
        fixture_name: str,
        model_version: str | None = None,
        run_timestamp: datetime.datetime | None = None,
        suppress_failures: bool = False,
        raise_on_failures: bool = True,
    ):
        self.fixture_name = fixture_name
        self.model_version = model_version or self._get_git_sha()
        self.run_timestamp = run_timestamp or datetime.datetime.now(datetime.timezone.utc)
        self.suppress_failures = suppress_failures
        self.raise_on_failures = raise_on_failures
        self.captures: dict[str, Any] = {}
        self.failures: list[dict] = []

    @staticmethod
    def _get_git_sha() -> str:
        """Return current git SHA or 'unknown'."""
        try:
            import subprocess
            sha = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            return f"local@{sha}"
        except Exception:
            return "unknown"

    def capture(self, name: str, value: Any) -> None:
        """Capture a named value for validation."""
        self.captures[name] = value

    def capture_scalar(self, name: str, value: float, tol_spec: dict[str, float]) -> None:
        """Capture a scalar value with its tolerance spec.

        tol_spec: {"type": "pct"|"abs"|"rel"|"bps", "value": float}
        """
        self.captures[name] = {
            "type": "scalar",
            "value": value,
            "tolerance": tol_spec,
        }

    def capture_series(self, name: str, values: tuple[float, ...] | list[float], tol_spec: dict[str, float]) -> None:
        """Capture a period-indexed series with its tolerance spec."""
        if isinstance(values, list):
            values = tuple(values)
        self.captures[name] = {
            "type": "series",
            "values": values,
            "tolerance": tol_spec,
        }

    def validate_scalar(
        self,
        name: str,
        golden_value: float,
        tol_type: str = "pct",
        tol_value: float = 0.005,
    ) -> dict[str, Any]:
        """Validate a captured scalar against a golden value.

        Returns comparison result dict. Stores failures in self.failures.
        """
        actual = self.captures.get(name)
        if actual is None:
            result = {
                "metric": name,
                "status": "MISSING",
                "message": f"metric {name!r} not captured",
            }
            self.failures.append(result)
            return result

        from tests.golden.utils.comparison import compare_values
        cmp = compare_values(actual, golden_value, **{tol_type + "_tol": tol_value})

        result = {
            "metric": name,
            "status": "PASS" if cmp["pass"] else "FAIL",
            "actual": actual,
            "golden": golden_value,
            "delta": cmp["delta"],
            "tolerance_type": tol_type,
            "tolerance_value": tol_value,
        }
        if not cmp["pass"]:
            self.failures.append(result)

        return result

    def validate_series(
        self,
        name: str,
        golden_values: tuple[float, ...],
        tol_type: str = "pct",
        tol_value: float = 0.005,
    ) -> dict[str, Any]:
        """Validate a captured series against golden values.

        Returns comparison result dict. Stores failures in self.failures.
        """
        actual = self.captures.get(name)
        if actual is None:
            result = {
                "metric": name,
                "status": "MISSING",
                "message": f"metric {name!r} not captured",
            }
            self.failures.append(result)
            return result

        if isinstance(actual, list):
            actual = tuple(actual)

        from tests.golden.utils.comparison import compare_series
        cmp = compare_series(actual, golden_values, **{tol_type + "_tol": tol_value})

        result = {
            "metric": name,
            "status": "PASS" if cmp["pass"] else "FAIL",
            "period_count_match": cmp["period_count_match"],
            "failure_count": len(cmp["failures"]),
            "failures_detail": cmp["failures"],
        }
        if not cmp["pass"]:
            self.failures.append(result)

        return result

    def report(self) -> dict[str, Any]:
        """Return the validation report as a dict."""
        summary = {
            "fixture": self.fixture_name,
            "model_version": self.model_version,
            "run_timestamp": self.run_timestamp.isoformat(),
            "total_captures": len(self.captures),
            "passed": len(self.failures) == 0,
            "failure_count": len(self.failures),
        }

        return {
            "summary": summary,
            "captures": self.captures,
            "failures": self.failures,
        }

    def print_report(self, verbose: bool = True) -> None:
        """Print validation report to stdout."""
        rep = self.report()
        summary = rep["summary"]

        print(f"\n=== Golden Validation Report: {self.fixture_name} ===")
        print(f"Model version : {summary['model_version']}")
        print(f"Run timestamp : {summary['run_timestamp']}")
        print(f"Captures      : {summary['total_captures']}")
        print(f"Result        : {'✅ ALL PASS' if summary['passed'] else '❌ FAILURES PRESENT'}")
        print(f"Failures      : {summary['failure_count']}")

        if verbose and self.failures:
            print("\n--- Failure Details ---")
            for f in self.failures:
                print(f"  {f['metric']}: {f.get('status')} — {f.get('message', '')}")

        print("=" * (48 + len(self.fixture_name)))

    def __enter__(self) -> SnapshotContext:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            # Exception propagating — do not suppress or raise
            return

        if self.failures and not self.suppress_failures:
            self.print_report()
            if self.raise_on_failures:
                failed_metrics = [f["metric"] for f in self.failures]
                raise AssertionError(
                    f"Golden validation failed for metrics: {failed_metrics}"
                )

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable dict of the snapshot state."""
        return self.report()