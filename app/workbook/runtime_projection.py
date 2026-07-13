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


def classify_runtime_state(
    rr: Any,
    payload: Any,
    is_dirty: bool,
) -> RuntimeProjectionState:
    """Classify the runtime state for a single sheet payload.

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


def extract_periods(
    schedule: Optional[Dict],
    operational_only: bool = False,
) -> Optional[List[Dict]]:
    """Return the periods list from a thawed schedule dict.

    Returns None when schedule is None (no runtime / payload absent).
    Returns an empty list when the schedule has no periods.
    When operational_only=True, filters to is_operation=True entries.
    """
    if schedule is None:
        return None
    raw: List[Dict] = schedule.get("periods") or []
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
class DebtRuntimeProjection:
    state: RuntimeProjectionState
    schedule: Optional[Dict]
    operational_periods: Optional[List[Dict]]
    runtime_summary: Optional[Dict]


@dataclass(frozen=True)
class TaxRuntimeProjection:
    state: RuntimeProjectionState
    schedule: Optional[Dict]
    operational_periods: Optional[List[Dict]]
    runtime_summary: Optional[Dict]


@dataclass(frozen=True)
class FinancialStatementsProjection:
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

    # ── Debt projection ──────────────────────────────────────────────────── #
    debt_state = classify_runtime_state(rr, debt_schedule, is_dirty)
    debt_op_periods = extract_periods(debt_schedule, operational_only=True)
    debt = DebtRuntimeProjection(
        state=debt_state,
        schedule=debt_schedule,
        operational_periods=debt_op_periods,
        runtime_summary=runtime_summary,
    )

    # ── Tax projection ───────────────────────────────────────────────────── #
    tax_state = classify_runtime_state(rr, tax_schedule, is_dirty)
    tax_op_periods = extract_periods(tax_schedule, operational_only=True)
    tax = TaxRuntimeProjection(
        state=tax_state,
        schedule=tax_schedule,
        operational_periods=tax_op_periods,
        runtime_summary=runtime_summary,
    )

    # ── Financial Statements projection ──────────────────────────────────── #
    fs_state = classify_runtime_state(rr, fs_payload, is_dirty)
    pnl_periods    = fs_payload.get("pnl", {}).get("periods") if fs_payload else None
    bs_periods     = fs_payload.get("balance_sheet", {}).get("periods") if fs_payload else None
    pf_cf_periods  = fs_payload.get("pf_cash_waterfall", {}).get("periods") if fs_payload else None
    fs = FinancialStatementsProjection(
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
