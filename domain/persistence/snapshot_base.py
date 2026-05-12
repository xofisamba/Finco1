"""Persistence snapshot base types and shared validation.

All snapshot dataclasses are frozen (immutable).  The persistence layer never
mutates domain results — snapshots are created from domain objects, not the
reverse.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

SCHEMA_VERSION = 1
"""Current schema version for all snapshot types."""


# ---------------------------------------------------------------------------
# Core metadata primitives
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SnapshotID:
    """A unique, non-empty snapshot identifier."""
    value: str

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("snapshot ID must be non-empty")
        # UUID-like validation: must be a valid hex string (allow any format)
        # We only require non-emptiness and no mutation, so asdict() is safe

    @classmethod
    def generate(cls) -> SnapshotID:
        """Generate a new unique snapshot ID."""
        return cls(value=str(uuid.uuid4()))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class SchemaVersioned:
    """Mixin for snapshot types that carry a schema version field."""
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self):
        if not isinstance(self.schema_version, int):
            raise TypeError(f"schema_version must be int, got {type(self.schema_version).__name__}")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"unknown schema_version {self.schema_version}; "
                f"only version {SCHEMA_VERSION} is supported"
            )


# ---------------------------------------------------------------------------
# Validation helpers (used by all snapshot types)
# ---------------------------------------------------------------------------

def validate_schema_version(version: int | None, *, field_name: str = "schema_version") -> int:
    """Require that schema_version is present and equals current version.

    Raises ValueError if missing or unsupported.
    Raises TypeError if not an int.
    """
    if not isinstance(version, int):
        raise TypeError(f"{field_name} must be int, got {type(version).__name__}")
    if version != SCHEMA_VERSION:
        raise ValueError(
            f"{field_name}={version} not supported; "
            f"only version {SCHEMA_VERSION} is valid"
        )
    return version


def validate_timestamp(ts: Any, *, field_name: str = "created_at") -> datetime:
    """Require that ts is a timezone-aware UTC datetime.

    Raises ValueError if missing, naive, or not a datetime.
    """
    if not isinstance(ts, datetime):
        raise TypeError(f"{field_name} must be datetime, got {type(ts).__name__}")
    if ts.tzinfo is None:
        raise ValueError(f"{field_name} must be timezone-aware (UTC); got naive datetime {ts!r}")
    if ts.tzinfo != timezone.utc:
        # Normalise to UTC
        ts = ts.astimezone(timezone.utc)
    return ts


def validate_uuid(value: Any, *, field_name: str) -> str:
    """Require that value is a non-empty UUID string."""
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be str, got {type(value).__name__}")
    if not value.strip():
        raise ValueError(f"{field_name} must be non-empty")
    return value


def validate_snapshot_id(value: Any, *, field_name: str = "id") -> SnapshotID:
    """Require that value is a SnapshotID or convertible to one."""
    if isinstance(value, SnapshotID):
        return value
    if isinstance(value, str):
        return SnapshotID(value=value)
    raise TypeError(f"{field_name} must be SnapshotID or str, got {type(value).__name__}")


def reject_nan_inf_float(value: Any, *, field_name: str) -> float:
    """Reject NaN or Inf floats.  Return the validated float."""
    if not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be float, got {type(value).__name__}")
    f = float(value)
    if math.isnan(f) or math.isinf(f):
        raise ValueError(f"{field_name} must not be NaN or Inf, got {value}")
    return f


def reject_nan_inf_container(data: Any, *, path: str = "") -> None:
    """Recursively reject NaN/Inf values inside containers (dict/list/tuple).

    Raises ValueError if any float inside is NaN or Inf.
    Raises TypeError if a non-serialisable container is encountered.
    """
    if isinstance(data, dict):
        for k, v in data.items():
            reject_nan_inf_container(v, path=f"{path}.{k}" if path else str(k))
    elif isinstance(data, (list, tuple)):
        for i, item in enumerate(data):
            reject_nan_inf_container(item, path=f"{path}[{i}]")
    elif isinstance(data, (int, str, bool, type(None))):
        pass  # primitives are safe
    elif isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            raise ValueError(f"NaN/Inf at {path or 'root'}: {data}")
    elif isinstance(data, datetime):
        pass  # datetimes are handled separately
    else:
        raise TypeError(f"Unsupported type at {path or 'root'}: {type(data).__name__}")


def frozen_get_fields(obj: Any) -> tuple[str, ...]:
    """Return dataclass field names for a frozen dataclass instance."""
    if hasattr(obj, "__dataclass_fields__"):
        return tuple(obj.__dataclass_fields__.keys())
    return ()


def to_primitive(value: Any) -> Any:
    """Convert a value to a JSON-safe primitive (or nested primitives).

    - datetime → ISO string
    - UUID → str
    - Frozen dataclass → dict (recursive)
    - tuple / list → list (recursive)
    - SnapshotID → str
    """
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, SnapshotID):
        return str(value.value)
    if hasattr(value, "__dataclass_fields__"):
        # Frozen dataclass — recurse on fields
        return {k: to_primitive(getattr(value, k)) for k in frozen_get_fields(value)}
    if isinstance(value, tuple):
        return [to_primitive(v) for v in value]
    if isinstance(value, list):
        return [to_primitive(v) for v in value]
    if isinstance(value, (int, str, bool, type(None))):
        return value
    if isinstance(value, float):
        return float(value)  # NaN/Inf already rejected earlier
    raise TypeError(f"to_primitive: unsupported type {type(value).__name__}")


def deterministic_dict(data: dict) -> dict:
    """Return a new dict with keys sorted deterministically (recursive)."""
    result: dict = {}
    for k in sorted(data.keys()):
        v = data[k]
        if isinstance(v, dict):
            result[k] = deterministic_dict(v)
        elif isinstance(v, (list, tuple)):
            result[k] = [deterministic_dict(i) if isinstance(i, dict) else i for i in v]
        else:
            result[k] = v
    return result
