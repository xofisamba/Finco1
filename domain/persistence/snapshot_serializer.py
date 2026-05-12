"""Snapshot serialization helpers.

Provides deterministic JSON serialization and deserialization for all
snapshot types.  All serialised output uses sorted keys and a JSON-default
handler for datetime / UUID so that the same object always produces the
same bytes (deterministic round-trip).
"""
from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from domain.persistence.snapshot_base import SCHEMA_VERSION, SnapshotID
from domain.persistence.project_snapshot import ProjectSnapshot
from domain.persistence.scenario_snapshot import ScenarioSnapshot, InputSnapshot, ResultSnapshot
from domain.persistence.sponsor_snapshot import SponsorSnapshot


def _json_default(obj: Any) -> Any:
    """JSON default handler for non-standard types during dumps."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "__dataclass_fields__"):
        return {k: getattr(obj, k) for k in obj.__dataclass_fields__}
    if isinstance(obj, (set, frozenset)):
        return sorted(obj, key=repr)
    raise TypeError(f"Unsupported type for JSON serialization: {type(obj).__name__}")


class SnapshotSerializer:
    """Deterministic serializer/deserializer for all snapshot types.

    Guarantees:
    - Round-trip: deserialize(serialize(obj)) == obj
    - Deterministic: serialize(obj) is the same bytes every time
    - NaN/Inf rejection at construction time (already enforced by snapshot types)
    """

    @staticmethod
    def serialize(obj: ProjectSnapshot | ScenarioSnapshot | InputSnapshot |
                  ResultSnapshot | SponsorSnapshot) -> str:
        """Serialize a snapshot to a deterministic JSON string."""
        return json.dumps(
            obj.to_dict(),
            sort_keys=True,
            default=_json_default,
        )

    @staticmethod
    def deserialize_project(data: str | dict) -> ProjectSnapshot:
        """Reconstruct a ProjectSnapshot from JSON string or dict."""
        d = json.loads(data) if isinstance(data, str) else data
        return ProjectSnapshot.from_dict(d)

    @staticmethod
    def deserialize_scenario(data: str | dict) -> ScenarioSnapshot:
        """Reconstruct a ScenarioSnapshot from JSON string or dict."""
        d = json.loads(data) if isinstance(data, str) else data
        return ScenarioSnapshot.from_dict(d)

    @staticmethod
    def deserialize_input(data: str | dict) -> InputSnapshot:
        """Reconstruct an InputSnapshot from JSON string or dict."""
        d = json.loads(data) if isinstance(data, str) else data
        return InputSnapshot.from_dict(d)

    @staticmethod
    def deserialize_result(data: str | dict) -> ResultSnapshot:
        """Reconstruct a ResultSnapshot from JSON string or dict."""
        d = json.loads(data) if isinstance(data, str) else data
        return ResultSnapshot.from_dict(d)

    @staticmethod
    def deserialize_sponsor(data: str | dict) -> SponsorSnapshot:
        """Reconstruct a SponsorSnapshot from JSON string or dict."""
        d = json.loads(data) if isinstance(data, str) else data
        return SponsorSnapshot.from_dict(d)

    @staticmethod
    def compute_hash(obj: ProjectSnapshot | ScenarioSnapshot |
                     InputSnapshot | ResultSnapshot | SponsorSnapshot) -> str:
        """Compute a SHA-256 hex hash of a snapshot's canonical JSON representation.

        This can be used as a content-addressable key for deduplication or
        cache invalidation.
        """
        canonical = json.dumps(obj.to_dict(), sort_keys=True, default=_json_default)
        return hashlib.sha256(canonical.encode()).hexdigest()

    @staticmethod
    def serialize_to_dict(
        obj: ProjectSnapshot | ScenarioSnapshot | InputSnapshot |
        ResultSnapshot | SponsorSnapshot
    ) -> dict:
        """Serialize a snapshot to a dict with deterministic key ordering."""
        return json.loads(json.dumps(obj.to_dict(), sort_keys=True, default=_json_default))
