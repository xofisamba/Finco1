"""app.v2.output_metric_projection — Single presentation contract for KPI display.

OutputMetricProjection is the canonical way to pass a financial KPI from the
authoritative RuntimeResult to a template.  It carries the raw value alongside
the display string so templates never need to reformat and tests can assert
the raw value without parsing display strings.

No financial arithmetic is performed here.  All values originate from the
persisted RuntimeResult.  The builder functions are pure presentation formatters.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


# Sentinel: value was not produced by this engine run / schema version
NOT_AVAILABLE = "—"


class MetricAvailability(str, Enum):
    AVAILABLE = "available"
    NOT_AVAILABLE = "not_available"   # not in runtime_summary schema version
    RUN_REQUIRED = "run_required"     # no RuntimeResult exists
    STALE = "stale"                   # result exists but inputs changed


@dataclass(frozen=True)
class OutputMetricProjection:
    """Immutable presentation bundle for one financial KPI.

    Attributes
    ----------
    key : str
        Canonical identifier, e.g. ``"project_irr"``.
    label : str
        Human-readable label, e.g. ``"Project IRR"``.
    raw_value : float | None
        The authoritative raw value from RuntimeResult, or None when unavailable.
        Never computed or modified here.
    display_value : str
        Pre-formatted string for template rendering.  Either a human-friendly
        formatted number (``"8.50%"``) or the NOT_AVAILABLE sentinel (``"—"``).
        Never ``"NOT_AVAILABLE"`` — that sentinel must not reach templates.
    unit : str
        Unit label for axis/tooltip use, e.g. ``"%"``, ``"x"``, ``"kEUR"``.
        Empty string when not applicable.
    availability : MetricAvailability
        Whether the value is meaningful for the current model state.
    source : str
        Provenance tag — ``"runtime_summary"`` or ``"debt_schedule.summary"``.
    scenario_id : str | None
        Scenario this projection belongs to, or None for the active scenario.
    run_timestamp : str | None
        ISO-8601 timestamp of the run that produced this value, or None.
    freshness : str
        ``"current"`` | ``"stale"`` | ``"not_run"`` — mirrors model state
        in a template-friendly string.
    """

    key: str
    label: str
    raw_value: Optional[float]
    display_value: str                  # "8.50%" | "1.45x" | "—"
    unit: str                           # "%" | "x" | "kEUR" | ""
    availability: MetricAvailability
    source: str                         # "runtime_summary" | "debt_schedule.summary"
    scenario_id: Optional[str] = None
    run_timestamp: Optional[str] = None
    freshness: str = "not_run"          # "current" | "stale" | "not_run"

    @property
    def is_available(self) -> bool:
        return self.availability == MetricAvailability.AVAILABLE

    @property
    def is_stale(self) -> bool:
        return self.freshness == "stale"

    @property
    def css_freshness_class(self) -> str:
        """CSS modifier class for freshness indicator."""
        return {
            "current": "v2-kpi-tile--current",
            "stale":   "v2-kpi-tile--stale",
            "not_run": "v2-kpi-tile--notrun",
        }.get(self.freshness, "v2-kpi-tile--notrun")


# ── Builder helpers ──────────────────────────────────────────────────────── #

def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
        if f != f or abs(f) == float("inf"):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _fmt_pct(v: Any) -> str:
    """Format raw decimal fraction as percentage string."""
    f = _safe_float(v)
    if f is None:
        return NOT_AVAILABLE
    return f"{f * 100:.2f}%"


def _fmt_ratio(v: Any) -> str:
    """Format raw float as 'X.XXx' coverage ratio."""
    f = _safe_float(v)
    if f is None:
        return NOT_AVAILABLE
    return f"{f:.2f}x"


def _fmt_keur(v: Any) -> str:
    """Format raw float as thousands-separated kEUR string."""
    f = _safe_float(v)
    if f is None:
        return NOT_AVAILABLE
    return f"{f:,.0f} kEUR"


def _resolve_display(raw_str: Any, key: str,
                     pct_keys: set, ratio_keys: set, keur_keys: set) -> tuple[Optional[float], str]:
    """Resolve a raw_str from runtime_summary into (raw_float, display_str).

    runtime_summary values may already be formatted strings (legacy) or raw
    floats (new schema).  This handles both.
    """
    if raw_str is None or raw_str == "" or raw_str == "NOT_AVAILABLE":
        return None, NOT_AVAILABLE
    if isinstance(raw_str, str):
        # Already formatted — extract numeric for raw_value best-effort
        cleaned = raw_str.replace("%", "").replace("x", "").replace(",", "").replace(" kEUR", "").strip()
        try:
            raw = float(cleaned)
        except ValueError:
            raw = None
        display = raw_str if raw_str else NOT_AVAILABLE
        return raw, display
    # Numeric
    f = _safe_float(raw_str)
    if f is None:
        return None, NOT_AVAILABLE
    if key in pct_keys:
        return f, _fmt_pct(raw_str)
    if key in ratio_keys:
        return f, _fmt_ratio(raw_str)
    if key in keur_keys:
        return f, _fmt_keur(raw_str)
    return f, str(f)


_PCT_KEYS   = frozenset({"project_irr", "equity_irr"})
_RATIO_KEYS = frozenset({"avg_dscr", "min_dscr", "min_llcr", "target_dscr", "plcr"})
_KEUR_KEYS  = frozenset({"total_capex_keur", "senior_debt_keur",
                          "total_revenue_keur", "total_ebitda_keur",
                          "total_cfads_keur", "equity_npv_keur"})

_KPI_CATALOG = [
    ("project_irr",       "Project IRR",        "%",    "runtime_summary"),
    ("equity_irr",        "Equity IRR",          "%",    "runtime_summary"),
    ("avg_dscr",          "Avg DSCR",            "x",    "runtime_summary"),
    ("min_dscr",          "Min DSCR",            "x",    "runtime_summary"),
    ("min_llcr",          "Min LLCR",            "x",    "debt_schedule.summary"),
    ("target_dscr",       "Target DSCR",         "x",    "debt_schedule.summary"),
    ("total_capex_keur",  "Total CAPEX",         "kEUR", "runtime_summary"),
    ("senior_debt_keur",  "Senior Debt",         "kEUR", "runtime_summary"),
    ("total_revenue_keur","Total Revenue",        "kEUR", "runtime_summary"),
    ("total_ebitda_keur", "Total EBITDA",        "kEUR", "runtime_summary"),
    ("total_cfads_keur",  "Total CFADS",         "kEUR", "runtime_summary"),
    ("equity_npv_keur",   "Equity NPV",          "kEUR", "runtime_summary"),
]


def build_output_metric_projection(
    key: str,
    raw_value_from_summary: Any,
    *,
    freshness: str = "not_run",
    scenario_id: Optional[str] = None,
    run_timestamp: Optional[str] = None,
) -> OutputMetricProjection:
    """Build a single OutputMetricProjection from a runtime_summary or debt_schedule value."""
    catalog_entry = next((c for c in _KPI_CATALOG if c[0] == key), None)
    label = catalog_entry[1] if catalog_entry else key
    unit  = catalog_entry[2] if catalog_entry else ""
    source = catalog_entry[3] if catalog_entry else "runtime_summary"

    raw_float, display = _resolve_display(
        raw_value_from_summary, key, _PCT_KEYS, _RATIO_KEYS, _KEUR_KEYS
    )

    if display == NOT_AVAILABLE:
        if freshness == "not_run":
            avail = MetricAvailability.RUN_REQUIRED
        elif freshness == "stale":
            avail = MetricAvailability.STALE
        else:
            avail = MetricAvailability.NOT_AVAILABLE
    else:
        avail = MetricAvailability.AVAILABLE

    return OutputMetricProjection(
        key=key,
        label=label,
        raw_value=raw_float,
        display_value=display,
        unit=unit,
        availability=avail,
        source=source,
        scenario_id=scenario_id,
        run_timestamp=run_timestamp,
        freshness=freshness,
    )


def build_overview_metric_projections(
    runtime_summary: dict,
    debt_summary: dict,
    *,
    freshness: str = "not_run",
    scenario_id: Optional[str] = None,
    run_timestamp: Optional[str] = None,
) -> dict[str, OutputMetricProjection]:
    """Build all KPI projections for the Overview sheet.

    Returns a dict keyed by metric key for easy template access.
    All values sourced from already-persisted RuntimeResult — no arithmetic.
    """
    projections: dict[str, OutputMetricProjection] = {}
    rs_keys = {c[0] for c in _KPI_CATALOG if c[3] == "runtime_summary"}
    ds_keys = {c[0] for c in _KPI_CATALOG if c[3] == "debt_schedule.summary"}

    for key in rs_keys:
        val = runtime_summary.get(key)
        projections[key] = build_output_metric_projection(
            key, val,
            freshness=freshness,
            scenario_id=scenario_id,
            run_timestamp=run_timestamp,
        )

    # debt_schedule.summary keys
    projections["min_llcr"] = build_output_metric_projection(
        "min_llcr", debt_summary.get("min_llcr"),
        freshness=freshness, scenario_id=scenario_id, run_timestamp=run_timestamp,
    )
    projections["target_dscr"] = build_output_metric_projection(
        "target_dscr", debt_summary.get("target_dscr"),
        freshness=freshness, scenario_id=scenario_id, run_timestamp=run_timestamp,
    )
    return projections
