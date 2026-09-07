"""
app.v2.scenario_kpi_projection — thin authoritative KPI formatter for Scenario Compare
and Sensitivity output surfaces.

Authority contract:
  Every scalar displayed in Scenario Compare or Sensitivity is sourced exclusively
  from an authoritative RuntimeResult / run_project() kpis dict.  This module
  formats those raw floats into display strings using the same rules as
  OverviewProjection, and produces nothing else.

No financial computation. No interpolation. No independent calculation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

_NA = "—"

# KPI display order and metadata
KPI_CATALOG: list[dict] = [
    {"key": "project_irr",       "label": "Project IRR",   "fmt": "pct"},
    {"key": "equity_irr",        "label": "Equity IRR",    "fmt": "pct"},
    {"key": "min_dscr",          "label": "Min DSCR",      "fmt": "ratio"},
    {"key": "avg_dscr",          "label": "Avg DSCR",      "fmt": "ratio"},
    {"key": "min_llcr",          "label": "Min LLCR",      "fmt": "ratio"},
    {"key": "senior_debt_keur",  "label": "Senior Debt",   "fmt": "keur"},
    {"key": "total_capex_keur",  "label": "Total CAPEX",   "fmt": "keur"},
    {"key": "total_revenue_keur","label": "Total Revenue", "fmt": "keur"},
    {"key": "total_ebitda_keur", "label": "Total EBITDA",  "fmt": "keur"},
    {"key": "total_cfads_keur",  "label": "Total CFADS",   "fmt": "keur"},
]


def _fmt(v: Any, fmt: str) -> str:
    if v is None or v == "" or v == _NA:
        return _NA
    try:
        f = float(v)
        if f != f or abs(f) == float("inf"):
            return _NA
        if fmt == "pct":
            return f"{f * 100:.2f}%"
        if fmt == "ratio":
            return f"{f:.2f}x"
        if fmt == "keur":
            return f"{f:,.0f} kEUR"
        return str(v)
    except (TypeError, ValueError):
        return str(v)


def _raw(v: Any, fmt: str) -> Optional[float]:
    """Return raw float for delta arithmetic, or None if unavailable."""
    if v is None or v == "" or v == _NA:
        return None
    try:
        f = float(v)
        if f != f or abs(f) == float("inf"):
            return None
        return f
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class ScenarioKpiRow:
    """One KPI row across N scenarios for the compare table."""
    key: str
    label: str
    fmt: str
    values: list[str]      # formatted display strings, one per scenario
    deltas: list[str]      # delta vs first scenario ("—" for base, "+1.23%" etc.)
    raw_values: list[Optional[float]]


@dataclass(frozen=True)
class ScenarioProjection:
    """Formatted KPI output for one scenario (for compare or sensitivity)."""
    scenario_id: Optional[str]
    scenario_name: str
    state: str             # "CLEAN" | "STALE" | "NOT_RUN"
    ran_at: str
    kpis: dict[str, str]          # key → formatted display string
    kpis_raw: dict[str, Optional[float]]  # key → raw float (None if unavailable)


def build_scenario_projection(
    scenario_name: str,
    runtime_summary: Optional[dict],
    ran_at: Optional[str],
    is_stale: bool,
) -> ScenarioProjection:
    """Build a ScenarioProjection from a persisted runtime_summary dict.

    runtime_summary must be the raw engine kpis dict (raw floats).
    No financial computation performed here — only formatting.
    """
    rs = runtime_summary or {}
    if not rs:
        state = "NOT_RUN"
    elif is_stale:
        state = "STALE"
    else:
        state = "CLEAN"

    kpis: dict[str, str] = {}
    kpis_raw: dict[str, Optional[float]] = {}
    for item in KPI_CATALOG:
        v = rs.get(item["key"])
        kpis[item["key"]] = _fmt(v, item["fmt"])
        kpis_raw[item["key"]] = _raw(v, item["fmt"])

    return ScenarioProjection(
        scenario_id=None,
        scenario_name=scenario_name,
        state=state,
        ran_at=(ran_at or "")[:16].replace("T", " "),
        kpis=kpis,
        kpis_raw=kpis_raw,
    )


def build_compare_rows(projections: list[ScenarioProjection]) -> list[ScenarioKpiRow]:
    """Build KPI comparison rows from a list of ScenarioProjection objects.

    Deltas are presentation arithmetic only: (value_i - value_0) formatted.
    Never used to construct a new financial output.
    """
    rows: list[ScenarioKpiRow] = []
    for item in KPI_CATALOG:
        key = item["key"]
        fmt = item["fmt"]
        vals = [p.kpis.get(key, _NA) for p in projections]
        raw_vals = [p.kpis_raw.get(key) for p in projections]
        base_raw = raw_vals[0] if raw_vals else None

        deltas: list[str] = []
        for i, rv in enumerate(raw_vals):
            if i == 0:
                deltas.append("—")
            elif rv is None or base_raw is None:
                deltas.append(_NA)
            else:
                d = rv - base_raw
                if fmt == "pct":
                    deltas.append(f"{d * 100:+.2f}%")
                elif fmt == "ratio":
                    deltas.append(f"{d:+.2f}x")
                elif fmt == "keur":
                    deltas.append(f"{d:+,.0f} kEUR")
                else:
                    deltas.append(f"{d:+.2f}")

        rows.append(ScenarioKpiRow(
            key=key,
            label=item["label"],
            fmt=fmt,
            values=vals,
            deltas=deltas,
            raw_values=raw_vals,
        ))
    return rows
