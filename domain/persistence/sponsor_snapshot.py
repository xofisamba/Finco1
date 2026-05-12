"""Sponsor / waterfall snapshot schema.

A SponsorSnapshot is an immutable, frozen snapshot capturing the full
sponsor waterfall state: investor registry, capital stack, and the
multi-investor waterfall result (from Phase 7D).

This snapshot is serialised alongside ScenarioSnapshot so that sponsor
state survives save/load cycles without coupling to the ORM layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from domain.persistence.snapshot_base import (
    SCHEMA_VERSION,
    SnapshotID,
    validate_schema_version,
    validate_timestamp,
    reject_nan_inf_container,
)


@dataclass(frozen=True)
class InvestorRegistrySnapshot:
    """Immutable snapshot of the investor registry (roles, ownership, committed capital)."""
    schema_version: int
    entries_json: list[dict]   # [{investor_id, role, ownership_pct, committed_capital_keur}, ...]
    total_ownership_pct: float
    total_committed_keur: float
    created_at: datetime

    def __post_init__(self):
        validate_schema_version(self.schema_version, field_name="schema_version")
        validate_timestamp(self.created_at, field_name="created_at")
        if not isinstance(self.entries_json, list):
            raise TypeError(f"entries_json must be list, got {type(self.entries_json).__name__}")
        for i, entry in enumerate(self.entries_json):
            if not isinstance(entry, dict):
                raise TypeError(f"entries_json[{i}] must be dict, got {type(entry).__name__}")

    @classmethod
    def create(cls, *, entries_json: list[dict], total_ownership_pct: float,
               total_committed_keur: float,
               now: Optional[datetime] = None) -> InvestorRegistrySnapshot:
        reject_nan_inf_container(entries_json)
        return cls(
            schema_version=SCHEMA_VERSION,
            entries_json=entries_json,
            total_ownership_pct=float(total_ownership_pct),
            total_committed_keur=float(total_committed_keur),
            created_at=now or datetime.now(timezone.utc),
        )

    @classmethod
    def from_dict(cls, data: dict) -> InvestorRegistrySnapshot:
        validate_schema_version(data.get("schema_version"), field_name="schema_version")
        return cls(
            schema_version=data["schema_version"],
            entries_json=data["entries_json"],
            total_ownership_pct=data["total_ownership_pct"],
            total_committed_keur=data["total_committed_keur"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "entries_json": self.entries_json,
            "total_ownership_pct": self.total_ownership_pct,
            "total_committed_keur": self.total_committed_keur,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class CapitalStackSnapshot:
    """Immutable snapshot of the capital stack (contributions by investor by period)."""
    schema_version: int
    total_committed_keur: float
    total_contributed_by_period_keur: list[float]
    investor_ids: list[str]
    created_at: datetime

    def __post_init__(self):
        validate_schema_version(self.schema_version, field_name="schema_version")
        validate_timestamp(self.created_at, field_name="created_at")
        if not isinstance(self.total_contributed_by_period_keur, (list, tuple)):
            raise TypeError(f"total_contributed_by_period_keur must be list, got {type(self.total_contributed_by_period_keur).__name__}")
        if not isinstance(self.investor_ids, (list, tuple)):
            raise TypeError(f"investor_ids must be list, got {type(self.investor_ids).__name__}")

    @classmethod
    def create(
        cls,
        *,
        total_committed_keur: float,
        total_contributed_by_period_keur: list[float],
        investor_ids: list[str],
        now: Optional[datetime] = None,
    ) -> CapitalStackSnapshot:
        reject_nan_inf_container(total_contributed_by_period_keur)
        return cls(
            schema_version=SCHEMA_VERSION,
            total_committed_keur=float(total_committed_keur),
            total_contributed_by_period_keur=[float(x) for x in total_contributed_by_period_keur],
            investor_ids=list(investor_ids),
            created_at=now or datetime.now(timezone.utc),
        )

    @classmethod
    def from_dict(cls, data: dict) -> CapitalStackSnapshot:
        validate_schema_version(data.get("schema_version"), field_name="schema_version")
        return cls(
            schema_version=data["schema_version"],
            total_committed_keur=data["total_committed_keur"],
            total_contributed_by_period_keur=data["total_contributed_by_period_keur"],
            investor_ids=data["investor_ids"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "total_committed_keur": self.total_committed_keur,
            "total_contributed_by_period_keur": self.total_contributed_by_period_keur,
            "investor_ids": self.investor_ids,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class SponsorSnapshot:
    """Immutable snapshot of the full sponsor / waterfall state for a scenario.

    This captures Phase 7D multi-investor waterfall outputs and is designed
    to be stored alongside ScenarioSnapshot so that sponsor state survives
    save/load round-trips.
    """
    schema_version: int
    investor_registry: InvestorRegistrySnapshot
    capital_stack: CapitalStackSnapshot
    waterfall_result_json: dict       # Serialised MultiInvestorWaterfallResult
    created_at: datetime

    def __post_init__(self):
        validate_schema_version(self.schema_version, field_name="schema_version")
        validate_timestamp(self.created_at, field_name="created_at")
        if not isinstance(self.investor_registry, InvestorRegistrySnapshot):
            raise TypeError("investor_registry must be InvestorRegistrySnapshot")
        if not isinstance(self.capital_stack, CapitalStackSnapshot):
            raise TypeError("capital_stack must be CapitalStackSnapshot")
        if not isinstance(self.waterfall_result_json, dict):
            raise TypeError(f"waterfall_result_json must be dict, got {type(self.waterfall_result_json).__name__}")

    @classmethod
    def create(
        cls,
        *,
        investor_registry: InvestorRegistrySnapshot,
        capital_stack: CapitalStackSnapshot,
        waterfall_result_json: dict,
        now: Optional[datetime] = None,
    ) -> SponsorSnapshot:
        reject_nan_inf_container(waterfall_result_json)
        return cls(
            schema_version=SCHEMA_VERSION,
            investor_registry=investor_registry,
            capital_stack=capital_stack,
            waterfall_result_json=waterfall_result_json,
            created_at=now or datetime.now(timezone.utc),
        )

    @classmethod
    def from_dict(cls, data: dict) -> SponsorSnapshot:
        validate_schema_version(data.get("schema_version"), field_name="schema_version")
        return cls(
            schema_version=data["schema_version"],
            investor_registry=InvestorRegistrySnapshot.from_dict(data["investor_registry"]),
            capital_stack=CapitalStackSnapshot.from_dict(data["capital_stack"]),
            waterfall_result_json=data["waterfall_result_json"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "investor_registry": self.investor_registry.to_dict(),
            "capital_stack": self.capital_stack.to_dict(),
            "waterfall_result_json": self.waterfall_result_json,
            "created_at": self.created_at.isoformat(),
        }
