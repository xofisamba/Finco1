"""Project-level snapshot schema.

An ProjectSnapshot is an immutable, frozen snapshot of project metadata.
It does NOT contain scenario data — that lives in ScenarioSnapshot.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from domain.persistence.snapshot_base import (
    SCHEMA_VERSION,
    SnapshotID,
    validate_schema_version,
    validate_timestamp,
    validate_uuid,
    reject_nan_inf_float,
    frozen_get_fields,
    to_primitive,
)


TECHNOLOGY_TYPES = frozenset({
    "solar", "wind", "bess", "hybrid", "agri",
})
"""Allowed technology_type values."""


@dataclass(frozen=True)
class ProjectSnapshot:
    """Immutable snapshot of a project's metadata.

    Lifecycle: created when a project is first saved;
    updated atomically when project metadata changes.

    The snapshot carries its own schema_version so future readers
    can evolve the schema while remaining backward-compatible.
    """

    # Identity
    id: SnapshotID
    """Globally unique project snapshot identifier."""

    # Core fields
    name: str
    technology_type: str
    description: str

    # Audit
    created_at: datetime
    updated_at: datetime
    schema_version: int = field(default=SCHEMA_VERSION, repr=False)

    # Optional
    owner_id: Optional[str] = None

    def __post_init__(self):
        # schema_version
        validate_schema_version(self.schema_version, field_name="schema_version")

        # Timestamps must be timezone-aware UTC
        validate_timestamp(self.created_at, field_name="created_at")
        validate_timestamp(self.updated_at, field_name="updated_at")

        # Technology type
        if self.technology_type not in TECHNOLOGY_TYPES:
            raise ValueError(
                f"technology_type must be one of {sorted(TECHNOLOGY_TYPES)}, "
                f"got {self.technology_type!r}"
            )

        # Non-empty name
        if not self.name or not self.name.strip():
            raise ValueError("name must be non-empty")

        # Immutable: __setattr__ is blocked by frozen=True
        # Dataclass-level __post_init__ is called before frozen locks, so
        # we raise in the body; but frozen dataclass raises on any assignment.
        # The checks above are read-only — safe to run here.
        object.__setattr__(self, "_checked", True)

    # ------------------------------------------------------------------ #
    # Factories
    # ------------------------------------------------------------------ #

    @classmethod
    def create(
        cls,
        *,
        name: str,
        technology_type: str,
        description: str = "",
        owner_id: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> ProjectSnapshot:
        """Create a new ProjectSnapshot with a freshly generated ID."""
        ts = now or datetime.now(timezone.utc)
        return cls(
            id=SnapshotID.generate(),
            name=name,
            technology_type=technology_type,
            description=description,
            created_at=ts,
            updated_at=ts,
            schema_version=SCHEMA_VERSION,
            owner_id=owner_id,
        )

    @classmethod
    def from_dict(cls, data: dict) -> ProjectSnapshot:
        """Reconstruct a ProjectSnapshot from a validated dict (e.g. from JSON)."""
        try:
            validate_schema_version(data.get("schema_version"), field_name="schema_version")
        except ValueError as exc:
            from domain.persistence.snapshot_store import SchemaVersionMismatchError
            raise SchemaVersionMismatchError(str(exc)) from exc
        return cls(
            id=SnapshotID(value=data["id"]),
            name=data["name"],
            technology_type=data["technology_type"],
            description=data.get("description", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            schema_version=data["schema_version"],
            owner_id=data.get("owner_id"),
        )

    # ------------------------------------------------------------------ #
    # Serialisation
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dict (deterministic key order)."""
        return {
            "id": str(self.id),
            "name": self.name,
            "technology_type": self.technology_type,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "schema_version": self.schema_version,
            "owner_id": self.owner_id,
        }

    def to_json(self) -> str:
        """Serialize to a JSON string (deterministic key order)."""
        import json
        return json.dumps(self.to_dict(), sort_keys=True, default=str)

    # ------------------------------------------------------------------ #
    # Equality / hash
    # ------------------------------------------------------------------ #

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProjectSnapshot):
            return NotImplemented
        return self.to_dict() == other.to_dict()

    def __hash__(self) -> int:
        return hash((str(self.id), self.name, self.technology_type, self.created_at.isoformat()))
