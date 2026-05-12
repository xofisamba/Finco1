"""Scenario-level snapshot schema.

A ScenarioSnapshot is an immutable, frozen snapshot of a single scenario —
project reference, name, parent link, plus the embedded input and result
snapshots (or references thereto).

Append-only philosophy: a ScenarioSnapshot, once created, is never mutated.
If inputs change, a new ScenarioSnapshot is created with a new id.
"""
from __future__ import annotations

import hashlib
import json as _json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from domain.persistence.snapshot_base import (
    SCHEMA_VERSION,
    SnapshotID,
    validate_schema_version,
    validate_timestamp,
    validate_uuid,
    reject_nan_inf_container,
    frozen_get_fields,
    to_primitive,
)


@dataclass(frozen=True)
class InputSnapshot:
    """Immutable snapshot of the structured inputs for one scenario.

    inputs_json is the canonical serialised form of the ProjectInputs
    dataclass tree.  It must NOT contain NaN or Inf.
    """
    schema_version: int
    inputs_hash: str      # SHA-256 hex of inputs_json (canonical, sorted keys)
    inputs_json: dict     # frozen inputs dict — NaN/Inf already rejected
    created_at: datetime

    def __post_init__(self):
        validate_schema_version(self.schema_version, field_name="schema_version")
        validate_timestamp(self.created_at, field_name="created_at")
        if not isinstance(self.inputs_hash, str) or not self.inputs_hash.strip():
            raise ValueError("inputs_hash must be a non-empty hex string")
        if len(self.inputs_hash) != 64:
            raise ValueError(f"inputs_hash must be 64-char SHA-256 hex, got {len(self.inputs_hash)}")
        if not isinstance(self.inputs_json, dict):
            raise TypeError(f"inputs_json must be dict, got {type(self.inputs_json).__name__}")
        # NaN/Inf already rejected at construction time

    @classmethod
    def create(
        cls,
        *,
        inputs_json: dict,
        now: Optional[datetime] = None,
    ) -> InputSnapshot:
        """Build an InputSnapshot with a computed SHA-256 hash."""
        reject_nan_inf_container(inputs_json)
        # Canonical JSON with sorted keys for determinism
        canonical = _json.dumps(inputs_json, sort_keys=True, default=str)
        inputs_hash = hashlib.sha256(canonical.encode()).hexdigest()
        return cls(
            schema_version=SCHEMA_VERSION,
            inputs_hash=inputs_hash,
            inputs_json=inputs_json,
            created_at=now or datetime.now(timezone.utc),
        )

    @classmethod
    def from_dict(cls, data: dict) -> InputSnapshot:
        validate_schema_version(data.get("schema_version"), field_name="schema_version")
        ts = datetime.fromisoformat(data["created_at"])
        validate_timestamp(ts, field_name="created_at")
        return cls(
            schema_version=data["schema_version"],
            inputs_hash=data["inputs_hash"],
            inputs_json=data["inputs_json"],
            created_at=ts,
        )

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "inputs_hash": self.inputs_hash,
            "inputs_json": self.inputs_json,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class ResultSnapshot:
    """Immutable snapshot of the computed waterfall result for one scenario.

    results_json is the canonical serialised form of the waterfall result.
    It must NOT contain NaN or Inf.
    """
    schema_version: int
    results_json: dict
    computed_at: datetime
    inputs_hash: str   # Must match the inputs_hash of the paired InputSnapshot
    created_at: datetime

    def __post_init__(self):
        validate_schema_version(self.schema_version, field_name="schema_version")
        validate_timestamp(self.computed_at, field_name="computed_at")
        validate_timestamp(self.created_at, field_name="created_at")
        if not isinstance(self.results_json, dict):
            raise TypeError(f"results_json must be dict, got {type(self.results_json).__name__}")
        if not isinstance(self.inputs_hash, str) or not self.inputs_hash.strip():
            raise ValueError("inputs_hash must be non-empty")
        if len(self.inputs_hash) != 64:
            raise ValueError(f"inputs_hash must be 64-char hex, got {len(self.inputs_hash)}")

    @classmethod
    def create(
        cls,
        *,
        results_json: dict,
        inputs_hash: str,
        now: Optional[datetime] = None,
    ) -> ResultSnapshot:
        """Build a ResultSnapshot with validated contents."""
        reject_nan_inf_container(results_json)
        return cls(
            schema_version=SCHEMA_VERSION,
            results_json=results_json,
            computed_at=now or datetime.now(timezone.utc),
            inputs_hash=inputs_hash,
            created_at=now or datetime.now(timezone.utc),
        )

    @classmethod
    def from_dict(cls, data: dict) -> ResultSnapshot:
        validate_schema_version(data.get("schema_version"), field_name="schema_version")
        return cls(
            schema_version=data["schema_version"],
            results_json=data["results_json"],
            computed_at=datetime.fromisoformat(data["computed_at"]),
            inputs_hash=data["inputs_hash"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "results_json": self.results_json,
            "computed_at": self.computed_at.isoformat(),
            "inputs_hash": self.inputs_hash,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class ScenarioSnapshot:
    """Immutable snapshot of a single scenario within a project.

    Contains references (by ID) to the parent project and optionally
    to a parent scenario (for scenario branching).

    The actual inputs and results are embedded as InputSnapshot /
    ResultSnapshot objects (append-only, never mutated).
    """

    id: SnapshotID
    project_id: SnapshotID
    name: str
    is_base_case: bool
    created_at: datetime
    schema_version: int = field(default=SCHEMA_VERSION, repr=False)

    description: str = ""
    parent_scenario_id: Optional[SnapshotID] = None
    input_snapshot: Optional[InputSnapshot] = None
    result_snapshot: Optional[ResultSnapshot] = None

    def __post_init__(self):
        validate_schema_version(self.schema_version, field_name="schema_version")
        validate_timestamp(self.created_at, field_name="created_at")
        if not self.name or not self.name.strip():
            raise ValueError("name must be non-empty")

    # ------------------------------------------------------------------ #
    # Factories
    # ------------------------------------------------------------------ #

    @classmethod
    def create(
        cls,
        *,
        project_id: str | SnapshotID,
        name: str,
        is_base_case: bool = False,
        description: str = "",
        parent_scenario_id: Optional[str | SnapshotID] = None,
        input_snapshot: Optional[InputSnapshot] = None,
        result_snapshot: Optional[ResultSnapshot] = None,
        now: Optional[datetime] = None,
    ) -> ScenarioSnapshot:
        """Create a new ScenarioSnapshot with a freshly generated ID."""
        ts = now or datetime.now(timezone.utc)
        pid = SnapshotID(value=project_id) if isinstance(project_id, str) else project_id
        parent = SnapshotID(value=parent_scenario_id) if isinstance(parent_scenario_id, str) else parent_scenario_id
        return cls(
            id=SnapshotID.generate(),
            project_id=pid,
            name=name,
            is_base_case=is_base_case,
            description=description,
            parent_scenario_id=parent,
            input_snapshot=input_snapshot,
            result_snapshot=result_snapshot,
            created_at=ts,
            schema_version=SCHEMA_VERSION,
        )

    @classmethod
    def from_dict(cls, data: dict) -> ScenarioSnapshot:
        validate_schema_version(data.get("schema_version"), field_name="schema_version")
        input_ss = None
        if data.get("input_snapshot"):
            input_ss = InputSnapshot.from_dict(data["input_snapshot"])
        result_ss = None
        if data.get("result_snapshot"):
            result_ss = ResultSnapshot.from_dict(data["result_snapshot"])
        parent = None
        if data.get("parent_scenario_id"):
            parent = SnapshotID(value=data["parent_scenario_id"])
        return cls(
            id=SnapshotID(value=data["id"]),
            project_id=SnapshotID(value=data["project_id"]),
            name=data["name"],
            is_base_case=data.get("is_base_case", False),
            description=data.get("description", ""),
            parent_scenario_id=parent,
            input_snapshot=input_ss,
            result_snapshot=result_ss,
            created_at=datetime.fromisoformat(data["created_at"]),
            schema_version=data["schema_version"],
        )

    # ------------------------------------------------------------------ #
    # Serialisation
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "name": self.name,
            "is_base_case": self.is_base_case,
            "description": self.description,
            "parent_scenario_id": str(self.parent_scenario_id) if self.parent_scenario_id else None,
            "input_snapshot": self.input_snapshot.to_dict() if self.input_snapshot else None,
            "result_snapshot": self.result_snapshot.to_dict() if self.result_snapshot else None,
            "created_at": self.created_at.isoformat(),
            "schema_version": self.schema_version,
        }

    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), sort_keys=True, default=str)

    # ------------------------------------------------------------------ #
    # Equality / hash
    # ------------------------------------------------------------------ #

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ScenarioSnapshot):
            return NotImplemented
        return self.to_dict() == other.to_dict()

    def __hash__(self) -> int:
        return hash(str(self.id))
