"""Snapshot store — abstract save/load interface.

SnapshotStore defines the persistence-agnostic interface for saving and
loading snapshots.  Implementations (in-memory, file-based, future SQL/NoSQL)
must uphold:

- Append-only: existing snapshots are never mutated after creation
- Deterministic round-trip: load(save(x)) == x
- No mutation of source domain objects during save
- Schema version checked on every load

No actual database integration is included in this phase — only the
abstract interface and an in-memory implementation for testing.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from domain.persistence.project_snapshot import ProjectSnapshot
from domain.persistence.scenario_snapshot import ScenarioSnapshot
from domain.persistence.sponsor_snapshot import SponsorSnapshot
from domain.persistence.snapshot_base import SnapshotID


T = TypeVar("T", bound=Any)


class SnapshotNotFoundError(KeyError):
    """Raised when a requested snapshot ID does not exist in the store."""
    pass


class SchemaVersionMismatchError(ValueError):
    """Raised when a loaded snapshot has an unsupported schema version."""
    pass


class SnapshotCorruptedError(ValueError):
    """Raised when deserialization detects corruption (e.g., missing required fields)."""
    pass


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class SnapshotStore(ABC, Generic[T]):
    """Abstract snapshot store — defines the persistence interface.

    Type parameter T is the snapshot type (ProjectSnapshot, ScenarioSnapshot,
    SponsorSnapshot, etc.).

    Subclass invariants:
    - save() must NOT mutate the snapshot after storing it
    - load() must return an equivalent-but-not-same-object snapshot
    - delete() is not supported (append-only philosophy)
    """

    @abstractmethod
    def save(self, snapshot: T) -> None:
        """Persist a snapshot.

        The store may NOT mutate the snapshot object.
        If the snapshot's ID already exists, implementations should raise
        SnapshotCorruptedError or TypeError (append-only: no overwrite).
        """
        ...

    @abstractmethod
    def load(self, snapshot_id: SnapshotID | str) -> T:
        """Load a snapshot by ID.

        Raises SnapshotNotFoundError if the ID is not found.
        Raises SchemaVersionMismatchError if the schema version is unsupported.
        """
        ...

    @abstractmethod
    def exists(self, snapshot_id: SnapshotID | str) -> bool:
        """Return True if a snapshot with the given ID exists."""
        ...

    @abstractmethod
    def list_ids(self) -> list[str]:
        """Return all stored snapshot IDs, in insertion order (oldest first)."""
        ...

    def list_snapshots(self) -> list[T]:
        """Return all stored snapshots, in insertion order."""
        return [self.load(sid) for sid in self.list_ids()]


# ---------------------------------------------------------------------------
# In-memory implementation (for testing)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InMemorySnapshotStore(SnapshotStore[T]):
    """In-memory append-only snapshot store for testing and as a reference impl.

    Thread-unsafe.  Do not share across threads.

    Snapshots are stored in a frozendict-like structure (a plain dict of
    id -> snapshot, frozen at insertion time to enforce append-only).
    """
    _store: dict[str, T] = field(default_factory=dict, repr=False)

    def save(self, snapshot: T) -> None:
        sid = str(snapshot.id)
        if sid in self._store:
            raise SnapshotCorruptedError(
                f"Append-only: cannot overwrite existing snapshot {sid}"
            )
        # Store a fresh copy (not the original object) to prevent aliasing
        import copy
        stored = copy.deepcopy(snapshot)
        object.__setattr__(self, "_store", {**self._store, sid: stored})

    def load(self, snapshot_id: SnapshotID | str) -> T:
        sid = str(snapshot_id)
        if sid not in self._store:
            raise SnapshotNotFoundError(f"No snapshot found with id={sid}")
        snapshot = self._store[sid]
        # Validate schema version if the snapshot carries one
        if hasattr(snapshot, "schema_version"):
            from domain.persistence.snapshot_base import SCHEMA_VERSION
            if snapshot.schema_version != SCHEMA_VERSION:
                raise SchemaVersionMismatchError(
                    f"snapshot {sid} has schema_version={snapshot.schema_version}, "
                    f"but only version {SCHEMA_VERSION} is supported"
                )
        # Return a fresh deep copy so callers cannot mutate stored state
        import copy
        return copy.deepcopy(snapshot)

    def exists(self, snapshot_id: SnapshotID | str) -> bool:
        return str(snapshot_id) in self._store

    def list_ids(self) -> list[str]:
        return list(self._store.keys())

    def count(self) -> int:
        """Return the number of stored snapshots."""
        return len(self._store)


# ---------------------------------------------------------------------------
# Composite store for multi-snapshot scenarios
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MultiSnapshotStore:
    """Facade holding separate stores for each snapshot type.

    Provides a single entry point for the full snapshot family while
    keeping each store independent (useful for schema evolution — e.g.,
    migrating sponsor snapshots independently from scenario snapshots).
    """
    projects: InMemorySnapshotStore[ProjectSnapshot] = field(
        default_factory=InMemorySnapshotStore[ProjectSnapshot]
    )
    scenarios: InMemorySnapshotStore[ScenarioSnapshot] = field(
        default_factory=InMemorySnapshotStore[ScenarioSnapshot]
    )
    sponsors: InMemorySnapshotStore[SponsorSnapshot] = field(
        default_factory=InMemorySnapshotStore[SponsorSnapshot]
    )
