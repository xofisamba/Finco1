"""Phase 6F-B — Equity Injection schema foundation.

Immutable dataclass for sponsor equity injection events.
Audit-friendly, deterministic, no waterfall mutation.

Future Phase 7 sponsor economics will use this schema for capital account evolution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EquityInjection:
    """Single equity injection event from sponsor into a project entity.

    Immutable. Validated on construction. Designed for audit trail and
    future sponsor capital account integration.

    Parameters
    ----------
    period_index : int
        Semiannual period index (0-based) when the injection occurs.
        Must be >= 0.
    amount_keur : float
        Equity amount in thousands of EUR. Must be >= 0.
    investor_id : str
        Non-empty sponsor/investor identifier (e.g., "SPONSOR-1", "EQUITY-CO-1").
    target_entity : str
        Non-empty target entity code (e.g., "SPV-1", "HOLDCO", "PORTFOLIO").
    purpose : str
        Non-empty reason/purpose for the injection
        (e.g., "equityContribution", "topUp", "reganEquity", "deferredEquity").
    notes : str, optional
        Free-form audit notes.
    metadata : dict, optional
        Arbitrary key-value pairs for future extension. Stored as frozen tuple
        of sorted (key, value) items. Keys and values must be JSON-serializable.

    Audit fields
    ------------
    audit_note : str
        Fixed string confirming this is an audit-only artifact.
        Included automatically; do not override.
    """
    period_index: int
    amount_keur: float
    investor_id: str
    target_entity: str
    purpose: str
    notes: str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        if self.period_index < 0:
            raise ValueError(
                f"period_index must be >= 0, got {self.period_index}"
            )
        if self.amount_keur < 0.0:
            raise ValueError(
                f"amount_keur must be >= 0.0, got {self.amount_keur}"
            )
        if not self.investor_id or not self.investor_id.strip():
            raise ValueError(
                f"investor_id must be a non-empty string, got {self.investor_id!r}"
            )
        if not self.target_entity or not self.target_entity.strip():
            raise ValueError(
                f"target_entity must be a non-empty string, got {self.target_entity!r}"
            )
        if not self.purpose or not self.purpose.strip():
            raise ValueError(
                f"purpose must be a non-empty string, got {self.purpose!r}"
            )
        if self.notes is not None and not isinstance(self.notes, str):
            raise TypeError(
                f"notes must be str or None, got {type(self.notes).__name__}"
            )
        if self.metadata is not None:
            if not isinstance(self.metadata, dict):
                raise TypeError(
                    f"metadata must be dict or None, got {type(self.metadata).__name__}"
                )
            for k, v in self.metadata.items():
                if not isinstance(k, str):
                    raise TypeError(
                        f"metadata keys must be str, got {type(k).__name__}"
                    )
                try:
                    _ = __import__('json').dumps(v)
                except TypeError:
                    raise TypeError(
                        f"metadata values must be JSON-serializable, "
                        f"key {k!r} value type {type(v).__name__} is not"
                    )

    @property
    def audit_note(self) -> str:
        return (
            "AUDIT-ONLY: Equity injection records are read-only governance artifacts. "
            "They do not modify model outputs or trigger any distribution or payment."
        )

    @property
    def frozen_metadata(self) -> tuple[tuple[str, Any], ...]:
        """Return metadata as a frozen sorted tuple of (key, value) items.

        Returns empty tuple if metadata is None.
        """
        if self.metadata is None:
            return ()
        return tuple(sorted(self.metadata.items()))

    def with_metadata(self, **kwargs: Any) -> EquityInjection:
        """Return a new EquityInjection with additional metadata merged in.

        Existing metadata is preserved; new keys override if duplicate.
        Does not mutate the original.
        """
        merged = dict(self.metadata or {})
        merged.update(kwargs)
        return EquityInjection(
            period_index=self.period_index,
            amount_keur=self.amount_keur,
            investor_id=self.investor_id,
            target_entity=self.target_entity,
            purpose=self.purpose,
            notes=self.notes,
            metadata=merged,
        )