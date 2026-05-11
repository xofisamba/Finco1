"""Phase 7A — Sponsor cashflow result schema.

Immutable, audit-safe result structures for sponsor-level cashflows.
Designed for future Sponsor IRR and multi-investor compatibility.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any

__all__ = [
    "SponsorCashflowPeriodResult",
    "SponsorCashflowResult",
]


# ── Validation helpers ────────────────────────────────────────────────────────

def _finite_non_negative(value: float, name: str) -> None:
    if not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be float, got {type(value).__name__}")
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"{name} must be finite, got {value}")
    if value < 0.0:
        raise ValueError(f"{name} must be non-negative, got {value}")


def _finite(value: float, name: str) -> None:
    if not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be float, got {type(value).__name__}")
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"{name} must be finite, got {value}")


def _non_empty_str(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string, got {value!r}")


def _to_tuple_str(value) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(str(v) for v in value)
    return (str(value),)


# ── SponsorCashflowPeriodResult ────────────────────────────────────────────────

@dataclass(frozen=True)
class SponsorCashflowPeriodResult:
    """Single period result for sponsor-level cashflows.

    All fields are audit-safe and immutable after construction.

    Attributes
    ----------
    period_index : int
        Semiannual period index (0-based). Must be >= 0.
    equity_injected_keur : float
        Equity injection amount in this period (cash outflow from sponsor).
        Must be >= 0.
    distribution_received_keur : float
        Distribution received by sponsor from HoldCo in this period
        (cash inflow to sponsor). Must be >= 0.
    wht_on_distribution_keur : float
        WHT withheld on the distribution (cash outflow). Must be >= 0.
    net_cashflow_keur : float
        Net sponsor cashflow = distribution_received - equity_injected - wht.
        Can be negative (net investment phase) or positive (net return phase).
    capital_account_balance_keur : float
        Cumulative capital account balance after this period's injection
        and distribution. Must be >= 0 (account never goes negative by construction).
    audit_note : str
        Fixed string confirming this is an audit-only artifact.
    notes : tuple[str, ...]
        Human-readable notes for this period (e.g., "first equity injection").
    """
    period_index: int
    equity_injected_keur: float
    distribution_received_keur: float
    wht_on_distribution_keur: float
    net_cashflow_keur: float
    capital_account_balance_keur: float
    audit_note: str = "AUDIT-ONLY: sponsor cashflow result — read-only governance artifact"
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if self.period_index < 0:
            raise ValueError(f"period_index must be >= 0, got {self.period_index}")
        for name, val in [
            ("equity_injected_keur", self.equity_injected_keur),
            ("distribution_received_keur", self.distribution_received_keur),
            ("wht_on_distribution_keur", self.wht_on_distribution_keur),
            ("capital_account_balance_keur", self.capital_account_balance_keur),
        ]:
            _finite_non_negative(val, name)
        _finite(self.net_cashflow_keur, "net_cashflow_keur")
        if not isinstance(self.notes, tuple):
            object.__setattr__(self, "notes", _to_tuple_str(self.notes))
        if not isinstance(self.audit_note, str):
            raise TypeError("audit_note must be str")


# ── SponsorCashflowResult ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class SponsorCashflowResult:
    """Complete sponsor cashflow result across all periods.

    Immutable. Deterministic. Audit-safe.

    Attributes
    ----------
    investor_id : str
        Sponsor/investor identifier (e.g., "SPONSOR-1", "EQUITY-CO-1").
    entity_code : str
        Target entity code (e.g., "HOLDCO", "PORTFOLIO").
    period_results : tuple[SponsorCashflowPeriodResult, ...]
        Per-period breakdown (ordered by period_index).
    total_equity_injected_keur : float
        Sum of all equity injections. Must be >= 0.
    total_distributions_received_keur : float
        Sum of all distributions received. Must be >= 0.
    total_wht_keur : float
        Sum of all WHT withheld. Must be >= 0.
    total_net_cashflow_keur : float
        Sum of all net cashflows (= total distributions - total equity - total WHT).
    gross_sponsor_return_multiple : float
        Placeholder for future MOIC: distributions / injections.
        None if no injections yet. Must be > 0 when computed.
    metadata : tuple[tuple[str, Any], ...]
        Key-value metadata as frozen sorted tuple.
        Values must be JSON-serializable (str, int, float, bool, None).
    notes : tuple[str, ...]
        Top-level audit notes.
    """
    investor_id: str
    entity_code: str
    period_results: tuple[SponsorCashflowPeriodResult, ...]
    total_equity_injected_keur: float
    total_distributions_received_keur: float
    total_wht_keur: float
    total_net_cashflow_keur: float
    gross_sponsor_return_multiple: float | None = None
    metadata: tuple[tuple[str, Any], ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def audit_note(self) -> str:
        return (
            "AUDIT-ONLY: sponsor cashflow result is a read-only governance artifact. "
            "It does not modify model outputs or trigger any distribution or payment."
        )

    @property
    def period_count(self) -> int:
        return len(self.period_results)

    @property
    def metadata_dict(self) -> dict[str, Any]:
        return dict(self.metadata)

    @property
    def equity_injections_by_period(self) -> tuple[float, ...]:
        return tuple(p.equity_injected_keur for p in self.period_results)

    @property
    def distributions_by_period(self) -> tuple[float, ...]:
        return tuple(p.distribution_received_keur for p in self.period_results)

    @property
    def net_cashflows_by_period(self) -> tuple[float, ...]:
        return tuple(p.net_cashflow_keur for p in self.period_results)

    @property
    def capital_account_by_period(self) -> tuple[float, ...]:
        return tuple(p.capital_account_balance_keur for p in self.period_results)

    def __post_init__(self):
        _non_empty_str(self.investor_id, "investor_id")
        _non_empty_str(self.entity_code, "entity_code")

        for name, val in [
            ("total_equity_injected_keur", self.total_equity_injected_keur),
            ("total_distributions_received_keur", self.total_distributions_received_keur),
            ("total_wht_keur", self.total_wht_keur),
        ]:
            _finite_non_negative(val, name)
        _finite(self.total_net_cashflow_keur, "total_net_cashflow_keur")

        if self.gross_sponsor_return_multiple is not None:
            _finite_non_negative(self.gross_sponsor_return_multiple, "gross_sponsor_return_multiple")

        # Reconcile totals with period_results (within 1e-6 tolerance)
        eps = 1e-6
        for total_name, period_attr, total_val in [
            ("total_equity_injected_keur", "equity_injected_keur", self.total_equity_injected_keur),
            ("total_distributions_received_keur", "distribution_received_keur", self.total_distributions_received_keur),
            ("total_wht_keur", "wht_on_distribution_keur", self.total_wht_keur),
            ("total_net_cashflow_keur", "net_cashflow_keur", self.total_net_cashflow_keur),
        ]:
            expected = sum(getattr(p, period_attr) for p in self.period_results)
            if abs(expected - total_val) > eps:
                raise ValueError(
                    f"{total_name} ({total_val}) does not reconcile with "
                    f"period_results sum ({expected:.6f}); diff={abs(expected - total_val):.2e}"
                )

        # Normalize metadata: dict -> sorted frozen tuple of (key, value)
        if isinstance(self.metadata, dict):
            items = tuple(sorted((str(k), _normalize_metadata_val(v)) for k, v in self.metadata.items()))
            object.__setattr__(self, "metadata", items)
        elif not isinstance(self.metadata, tuple):
            object.__setattr__(self, "metadata", tuple(self.metadata))

        # Normalize notes to tuple
        if not isinstance(self.notes, tuple):
            object.__setattr__(self, "notes", _to_tuple_str(self.notes))


def _normalize_metadata_val(v: Any) -> Any:
    """Normalize metadata value to a JSON-serializable immutable type."""
    if isinstance(v, (str, int, float, bool, type(None))):
        return v
    if isinstance(v, (list, tuple)):
        return tuple(_normalize_metadata_val(x) for x in v)
    if isinstance(v, dict):
        return {str(k): _normalize_metadata_val(val) for k, val in v.items()}
    return str(v)