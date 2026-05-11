"""Diff and report formatting for golden validation.

Generic, reusable utilities with no business logic.
No dependence on UI/export formatting.
"""
from __future__ import annotations

from typing import Any


class DiffFormatter:
    """Formats a single metric diff for human-readable output.

    Static methods — no instance state.
    """

    @staticmethod
    def format(
        metric: str,
        *,
        actual: float | None = None,
        golden: float | None = None,
        delta: float | None = None,
        abs_tol: float | None = None,
        rel_tol: float | None = None,
        pct_tol: float | None = None,
        bps_tol: float | None = None,
        status: str = "UNKNOWN",
    ) -> str:
        """Format a single metric diff as a readable string.

        Returns a single-line human-readable string.
        """
        if actual is not None and golden is not None:
            delta = actual - golden

        # Format values
        if golden is not None:
            if abs(golden) >= 1.0:
                actual_str = f"{actual:.4f}" if actual is not None else "N/A"
                golden_str = f"{golden:.4f}"
                delta_str = f"{delta:+.6f}" if delta is not None else "N/A"
            else:
                actual_str = f"{actual:.6f}" if actual is not None else "N/A"
                golden_str = f"{golden:.6f}"
                delta_str = f"{delta:+.8f}" if delta is not None else "N/A"
        else:
            actual_str = str(actual)
            golden_str = "N/A"
            delta_str = str(delta) if delta is not None else "N/A"

        # Format tolerance
        tol_str = DiffFormatter._format_tolerance(abs_tol, rel_tol, pct_tol, bps_tol)

        # Format status
        status_icon = {"PASS": "✅", "FAIL": "❌", "UNKNOWN": "❓"}.get(status, f"[{status}]")

        return (
            f"{status_icon} {metric}: {actual_str} vs {golden_str} "
            f"| delta {delta_str} | tol: {tol_str}"
        )

    @staticmethod
    def _format_tolerance(
        abs_tol: float | None,
        rel_tol: float | None,
        pct_tol: float | None,
        bps_tol: float | None,
    ) -> str:
        if bps_tol is not None:
            return f"±{bps_tol:.0f} bps"
        if pct_tol is not None:
            return f"±{pct_tol*100:.2f}%"
        if rel_tol is not None:
            return f"±{rel_tol:.2e}"
        if abs_tol is not None:
            return f"±{abs_tol:.6f}"
        return "±?"

    @staticmethod
    def format_series_diff(
        metric: str,
        *,
        actual: tuple[float, ...],
        golden: tuple[float, ...],
        failures: list[tuple[int, float]] | None = None,
        per_period_tol: float | None = None,
        period_fmt: str = "period",
    ) -> str:
        """Format a period-series diff as a readable multi-line string.

        Returns a string with a header line and per-period failure lines.
        """
        lines = []
        lines.append(f"Series: {metric} ({len(actual)} periods)")
        lines.append(f"  Golden periods : {len(golden)}")
        lines.append(f"  Actual periods : {len(actual)}")

        if len(actual) != len(golden):
            lines.append(f"  ❌ PERIOD COUNT MISMATCH")
            return "\n".join(lines)

        if per_period_tol is not None:
            lines.append(f"  Per-period tol: ±{per_period_tol:.6f}")

        if failures:
            lines.append(f"  ❌ {len(failures)} period(s) exceeded tolerance:")
            for idx, delta in failures:
                lines.append(f"    {period_fmt}[{idx}]: actual={actual[idx]:.4f}, golden={golden[idx]:.4f}, delta={delta:+.4f}")
        else:
            lines.append(f"  ✅ All {len(actual)} periods within tolerance")

        return "\n".join(lines)


class ReportFormatter:
    """Formats full golden validation reports for human-readable output.

    Static methods — no instance state.
    """

    @staticmethod
    def format_report(report: dict[str, Any]) -> str:
        """Format a full validation report dict as a readable multi-line string.

        report: as returned by SnapshotContext.report()
        """
        lines = []
        summary = report.get("summary", {})

        lines.append("")
        lines.append("═" * 56)
        lines.append("  GOLDEN VALIDATION REPORT")
        lines.append("═" * 56)
        lines.append(f"  Fixture       : {summary.get('fixture', 'N/A')}")
        lines.append(f"  Model version : {summary.get('model_version', 'N/A')}")
        lines.append(f"  Run timestamp  : {summary.get('run_timestamp', 'N/A')}")
        lines.append(f"  Captures      : {summary.get('total_captures', 0)}")
        lines.append(f"  Result         : {'✅ PASS' if summary.get('passed') else '❌ FAIL'}")
        lines.append(f"  Failures       : {summary.get('failure_count', 0)}")
        lines.append("─" * 56)

        failures = report.get("failures", [])
        if failures:
            lines.append("  FAILURE DETAILS")
            lines.append("─" * 56)
            for f in failures:
                metric = f.get("metric", "?")
                status = f.get("status", "?")
                lines.append(f"  {metric}: {status}")
                for k, v in f.items():
                    if k not in ("metric", "status"):
                        lines.append(f"    {k}: {v}")
            lines.append("─" * 56)

        lines.append("═" * 56)
        return "\n".join(lines)

    @staticmethod
    def format_summary_line(
        fixture: str,
        total: int,
        passed: int,
        failed: int,
    ) -> str:
        """Format a one-line summary."""
        emoji = "✅" if failed == 0 else "❌"
        return f"{emoji} {fixture}: {passed}/{total} passed" + (f", {failed} failed" if failed else "")

    @staticmethod
    def format_table(
        headers: list[str],
        rows: list[list[str]],
        column_widths: list[int] | None = None,
    ) -> str:
        """Format a simple text table.

        headers: list of column header strings
        rows: list of rows (each row is list of str)
        column_widths: optional list of column widths; auto-computed if None
        """
        if not rows:
            return ""

        if column_widths is None:
            col_count = len(headers)
            col_widths = [max(len(str(headers[i])), max(len(str(r[i])) for r in rows)) for i in range(col_count)]
        else:
            col_widths = column_widths

        def fmt_row(row: list[str]) -> str:
            return "  ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(row)))

        lines = []
        lines.append(fmt_row(headers))
        lines.append("  ".join("-" * w for w in col_widths))
        for row in rows:
            lines.append(fmt_row(row))

        return "\n".join(lines)