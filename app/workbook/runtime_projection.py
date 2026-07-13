"""
app.workbook.runtime_projection — unified persisted runtime projection layer.

Pure module: no FastAPI, no Jinja2, no database calls.
Accepts a RuntimeResult (or None) and workspace dirty flag; returns typed
projection bundles consumed by router adapters and OOB view helpers.

State machine (per sheet payload):
    NOT_RUN     — no RuntimeResult exists
    UNAVAILABLE — rr exists but this sheet's payload is absent  (beats STALE)
    STALE       — rr + payload + workspace dirty
    CLEAN       — rr + payload + workspace clean

Structural availability contract for debt/tax schedules:
    payload is None                       → UNAVAILABLE, periods=None
    payload is {}                         → UNAVAILABLE, periods=None
    payload exists but "periods" key absent → UNAVAILABLE, periods=None
    payload["periods"] is None            → UNAVAILABLE, periods=None
    payload["periods"] == []              → CLEAN or STALE, periods=[]
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Dict, List, Optional


# ── State enum ──────────────────────────────────────────────────────────── #

class RuntimeProjectionState(str, Enum):
    NOT_RUN     = "NOT_RUN"
    CLEAN       = "CLEAN"
    STALE       = "STALE"
    UNAVAILABLE = "UNAVAILABLE"


# ── Shared utilities ─────────────────────────────────────────────────────── #

def thaw_runtime_payload(obj: Any) -> Any:
    """Recursively convert MappingProxyType → plain dict for template rendering."""
    if isinstance(obj, MappingProxyType):
        return {k: thaw_runtime_payload(v) for k, v in obj.items()}
    if isinstance(obj, dict):
        return {k: thaw_runtime_payload(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [thaw_runtime_payload(i) for i in obj]
    return obj


def _schedule_has_valid_periods(schedule: Optional[Dict]) -> bool:
    """True iff schedule is a non-empty dict with a non-None 'periods' key."""
    if not schedule:
        return False
    if "periods" not in schedule:
        return False
    return schedule["periods"] is not None


def classify_runtime_state(
    rr: Any,
    payload: Any,
    is_dirty: bool,
) -> RuntimeProjectionState:
    """Classify state for FS-style payloads (top-level dict presence only).

    UNAVAILABLE takes precedence over STALE: if the run completed but the
    payload was not persisted, the bar must say "unavailable", not "stale".
    """
    if rr is None:
        return RuntimeProjectionState.NOT_RUN
    if not payload:
        return RuntimeProjectionState.UNAVAILABLE
    if is_dirty:
        return RuntimeProjectionState.STALE
    return RuntimeProjectionState.CLEAN


def classify_schedule_state(
    rr: Any,
    schedule: Optional[Dict],
    is_dirty: bool,
) -> RuntimeProjectionState:
    """Classify state for debt/tax schedule payloads with explicit periods-key check.

    All four structural-unavailability conditions map to UNAVAILABLE:
      - schedule is None
      - schedule is {} (empty, no "periods" key)
      - schedule has keys but "periods" is absent
      - schedule["periods"] is None

    Only schedule["periods"] == [] (present, non-None, but empty) is CLEAN/STALE.
    """
    if rr is None:
        return RuntimeProjectionState.NOT_RUN
    if not _schedule_has_valid_periods(schedule):
        return RuntimeProjectionState.UNAVAILABLE
    if is_dirty:
        return RuntimeProjectionState.STALE
    return RuntimeProjectionState.CLEAN


def extract_periods(
    schedule: Optional[Dict],
    operational_only: bool = False,
) -> Optional[List[Dict]]:
    """Return the periods list from a thawed schedule dict.

    Returns None for all structural-unavailability conditions:
      schedule is None, {}, missing 'periods' key, or periods is None.
    Returns [] when periods list is explicitly empty.
    When operational_only=True, filters to is_operation=True entries.
    """
    if not _schedule_has_valid_periods(schedule):
        return None
    raw: List[Dict] = schedule["periods"]  # type: ignore[index]
    if operational_only:
        return [p for p in raw if p.get("is_operation")]
    return raw


def project_period_labels(periods: Optional[List[Dict]]) -> List[str]:
    """Extract YYYY-MM display labels from period date fields."""
    if not periods:
        return []
    return [
        p.get("date", "")[:7] if p.get("date") else "—"
        for p in periods
    ]


def project_rows(
    row_defs: List[tuple],
    periods: Optional[List[Dict]],
) -> Optional[List[Dict]]:
    """Build presentation rows from payload periods.

    Returns None when periods is None (no runtime / statement unavailable).
    Returns [] when periods is [] (run produced zero periods).
    Values are preserved verbatim: None stays None, 0 stays 0.
    No arithmetic is performed.
    """
    if periods is None:
        return None
    return [
        {
            "key": key,
            "label": label,
            "is_total": is_total,
            "values": [p.get(key) for p in periods],
        }
        for key, label, is_total in row_defs
    ]


# ── Financial Statements row definitions ─────────────────────────────────── #
# (key, display_label, is_total)

FS_PNL_ROW_DEFS: List[tuple] = [
    ("revenues_keur",                "Revenues",             False),
    ("operating_expenses_keur",      "Operating Expenses",   False),
    ("depreciation_keur",            "Depreciation",         False),
    ("ebit_keur",                    "EBIT",                 True),
    ("senior_interest_expense_keur", "Senior Interest",      False),
    ("shl_interest_expense_keur",    "SHL Interest",         False),
    ("earnings_before_tax_keur",     "Earnings Before Tax",  True),
    ("cit_accrual_keur",             "CIT Accrual",          False),
    ("net_income_keur",              "Net Income",           True),
    ("retained_earnings_keur",       "Retained Earnings",    False),
    ("net_dividends_keur",           "Net Dividends",        False),
]

FS_PF_CF_ROW_DEFS: List[tuple] = [
    ("revenue_cash_keur",          "Revenue Cash",         False),
    ("opex_cash_keur",             "OPEX Cash",            False),
    ("ebitda_cash_keur",           "EBITDA Cash",          True),
    ("cash_tax_keur",              "Cash Tax",             False),
    ("fcf_banks_keur",             "FCF to Banks",         True),
    ("senior_total_ds_keur",       "Senior Total DS",      False),
    ("dsra_funding_keur",          "DSRA Funding",         False),
    ("dsra_release_keur",          "DSRA Release",         False),
    ("fcf_junior_keur",            "FCF Junior",           False),
    ("fcf_for_distribution_keur",  "FCF for Distribution", True),
    ("net_dividends_keur",         "Net Dividends",        False),
]

FS_BS_ROW_DEFS: List[tuple] = [
    ("net_fixed_assets_keur",          "Net Fixed Assets",           False),
    ("dsra_balance_keur",              "DSRA Balance",               False),
    ("cash_keur",                      "Cash",                       False),
    ("total_assets_keur",              "Total Assets",               True),
    ("share_capital_keur",             "Share Capital ★",       False),
    ("retained_earnings_keur",         "Retained Earnings",          False),
    ("shl_balance_keur",               "SHL Balance",                False),
    ("senior_balance_keur",            "Senior Balance",             False),
    ("total_liabilities_equity_keur",  "Total Liabilities + Equity", True),
    ("balance_check_keur",             "Balance Check",              False),
]


def fs_classify_statement(rr: Any, fs: Optional[Dict], statement_key: str) -> str:
    """Per-statement classification: NOT_RUN / PARTIAL / UNAVAILABLE."""
    if rr is None:
        return "NOT_RUN"
    if fs is None:
        return "UNAVAILABLE"
    if statement_key not in fs:
        return "UNAVAILABLE"
    if fs[statement_key].get("periods") is None:
        return "UNAVAILABLE"
    return "PARTIAL"


# ── Typed projection structs ──────────────────────────────────────────────── #

@dataclass(frozen=True)
class RuntimeProjectionMeta:
    """Identity and state metadata shared from the single RuntimeResult.

    snapshot_id, ran_at, and origin come from the persisted RuntimeResult and
    are identical across all three sheet projections built from the same rr.
    Only state and has_payload differ per sheet.
    """
    state: RuntimeProjectionState
    has_runtime: bool
    has_payload: bool
    is_dirty: bool
    snapshot_id: Optional[str]
    ran_at: Optional[str]
    origin: Optional[str]


@dataclass(frozen=True)
class DebtRuntimeProjection:
    meta: RuntimeProjectionMeta
    # Canonical field names
    source: Optional[Dict]          # thawed authoritative schedule payload
    periods: Optional[List[Dict]]   # all source periods in original order
    operational_periods: Optional[List[Dict]]
    summary: Optional[Dict]
    # Backward-compat aliases (same objects, no copy)
    state: RuntimeProjectionState
    schedule: Optional[Dict]        # alias for source
    runtime_summary: Optional[Dict] # alias for summary


@dataclass(frozen=True)
class TaxRuntimeProjection:
    meta: RuntimeProjectionMeta
    # Canonical field names
    source: Optional[Dict]
    periods: Optional[List[Dict]]
    operational_periods: Optional[List[Dict]]
    summary: Optional[Dict]
    # Backward-compat aliases
    state: RuntimeProjectionState
    schedule: Optional[Dict]
    runtime_summary: Optional[Dict]


@dataclass(frozen=True)
class FinancialStatementsProjection:
    meta: RuntimeProjectionMeta
    state: RuntimeProjectionState
    fs_available: bool
    pnl_rows: Optional[List[Dict]]
    bs_rows: Optional[List[Dict]]
    pf_cf_rows: Optional[List[Dict]]
    pnl_period_labels: List[str]
    bs_period_labels: List[str]
    pf_cf_period_labels: List[str]
    pnl_classification: str
    bs_classification: str
    pf_cf_classification: str
    runtime_summary: Optional[Dict]


@dataclass(frozen=True)
class WorkbookRuntimeProjection:
    debt: DebtRuntimeProjection
    tax: TaxRuntimeProjection
    fs: FinancialStatementsProjection


# ── Factory ───────────────────────────────────────────────────────────────── #

def build_runtime_projection_bundle(
    rr: Any,
    is_dirty: bool,
) -> WorkbookRuntimeProjection:
    """Build all three sheet projections from one RuntimeResult.

    Accepts rr=None (no runtime persisted yet) — all three sheets will be
    in NOT_RUN state.  All payload extraction and state classification is
    done here; router adapters and view helpers only read the bundle.

    No financial arithmetic is performed.  Period dicts are passed verbatim.
    """
    # ── Thaw payloads once ───────────────────────────────────────────────── #
    # Use getattr so the factory is robust to partial mocks in tests that only
    # set financial_statements on a MagicMock(spec=RuntimeResult).
    _debt_raw    = getattr(rr, "debt_schedule", None)    if rr else None
    _tax_raw     = getattr(rr, "tax_schedule", None)     if rr else None
    _fs_raw      = getattr(rr, "financial_statements", None) if rr else None
    _summary_raw = getattr(rr, "runtime_summary", None)  if rr else None

    debt_schedule   = thaw_runtime_payload(_debt_raw)    if _debt_raw    else None
    tax_schedule    = thaw_runtime_payload(_tax_raw)     if _tax_raw     else None
    fs_payload      = thaw_runtime_payload(_fs_raw)      if _fs_raw      else None
    runtime_summary = thaw_runtime_payload(_summary_raw) if _summary_raw else None

    # ── Shared rr identity (same across all three sheets) ────────────────── #
    _has_runtime = rr is not None
    _snapshot_id = str(getattr(rr, "snapshot_id", None)) if _has_runtime else None
    _ran_at      = str(getattr(rr, "ran_at", None))      if _has_runtime else None
    _origin      = str(getattr(rr, "origin", None))      if _has_runtime else None

    # ── Debt projection ──────────────────────────────────────────────────── #
    debt_state = classify_schedule_state(rr, debt_schedule, is_dirty)
    debt_periods    = extract_periods(debt_schedule, operational_only=False)
    debt_op_periods = extract_periods(debt_schedule, operational_only=True)
    debt_meta = RuntimeProjectionMeta(
        state=debt_state,
        has_runtime=_has_runtime,
        has_payload=debt_schedule is not None,
        is_dirty=is_dirty,
        snapshot_id=_snapshot_id,
        ran_at=_ran_at,
        origin=_origin,
    )
    debt = DebtRuntimeProjection(
        meta=debt_meta,
        source=debt_schedule,
        periods=debt_periods,
        operational_periods=debt_op_periods,
        summary=runtime_summary,
        state=debt_state,
        schedule=debt_schedule,
        runtime_summary=runtime_summary,
    )

    # ── Tax projection ───────────────────────────────────────────────────── #
    tax_state = classify_schedule_state(rr, tax_schedule, is_dirty)
    tax_periods    = extract_periods(tax_schedule, operational_only=False)
    tax_op_periods = extract_periods(tax_schedule, operational_only=True)
    tax_meta = RuntimeProjectionMeta(
        state=tax_state,
        has_runtime=_has_runtime,
        has_payload=tax_schedule is not None,
        is_dirty=is_dirty,
        snapshot_id=_snapshot_id,
        ran_at=_ran_at,
        origin=_origin,
    )
    tax = TaxRuntimeProjection(
        meta=tax_meta,
        source=tax_schedule,
        periods=tax_periods,
        operational_periods=tax_op_periods,
        summary=runtime_summary,
        state=tax_state,
        schedule=tax_schedule,
        runtime_summary=runtime_summary,
    )

    # ── Financial Statements projection ──────────────────────────────────── #
    fs_state = classify_runtime_state(rr, fs_payload, is_dirty)
    pnl_periods    = fs_payload.get("pnl", {}).get("periods") if fs_payload else None
    bs_periods     = fs_payload.get("balance_sheet", {}).get("periods") if fs_payload else None
    pf_cf_periods  = fs_payload.get("pf_cash_waterfall", {}).get("periods") if fs_payload else None
    fs_meta = RuntimeProjectionMeta(
        state=fs_state,
        has_runtime=_has_runtime,
        has_payload=fs_payload is not None,
        is_dirty=is_dirty,
        snapshot_id=_snapshot_id,
        ran_at=_ran_at,
        origin=_origin,
    )
    fs = FinancialStatementsProjection(
        meta=fs_meta,
        state=fs_state,
        fs_available=fs_payload is not None,
        pnl_rows=project_rows(FS_PNL_ROW_DEFS, pnl_periods),
        bs_rows=project_rows(FS_BS_ROW_DEFS, bs_periods),
        pf_cf_rows=project_rows(FS_PF_CF_ROW_DEFS, pf_cf_periods),
        pnl_period_labels=project_period_labels(pnl_periods),
        bs_period_labels=project_period_labels(bs_periods),
        pf_cf_period_labels=project_period_labels(pf_cf_periods),
        pnl_classification=fs_classify_statement(rr, fs_payload, "pnl"),
        bs_classification=fs_classify_statement(rr, fs_payload, "balance_sheet"),
        pf_cf_classification=fs_classify_statement(rr, fs_payload, "pf_cash_waterfall"),
        runtime_summary=runtime_summary,
    )

    return WorkbookRuntimeProjection(debt=debt, tax=tax, fs=fs)
