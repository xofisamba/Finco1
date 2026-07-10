"""
Workbook V2 — ProjectInputSet: canonical editable model.

Architecture position:

  Legacy snapshot dict (string values from DB / form)
      ↓
  ProjectInputSet.from_snapshot()        ← registry-aware conversion
      ↓
  ProjectInputSet                        ← values by semantic field_id,
      │                                    typed, hashed, provenance retained
      │
      ├─ .get(field_id)                  ← V2 code reads here
      ├─ .with_value(field_id, value)    ← V2 edit operations return new instance
      ├─ .to_snapshot()                  ← round-trip back to legacy format
      └─ .to_projectinputs()             ← routes to existing adapter (zero drift)
              ↓
          build_projectinputs_from_snapshot()   ← unchanged
              ↓
          ProjectInputs (frozen domain dataclass)
              ↓
          WaterfallRunner.run()

Design invariants:
- ProjectInputSet is immutable (frozen dataclass).
- Values are stored by semantic field_id (from WORKBOOK registry), not by
  legacy snapshot key — V2 code never hard-codes snapshot key strings.
- The legacy snapshot_origin is preserved verbatim so to_projectinputs() can
  route through the existing adapter without any re-encoding risk.
- Unknown snapshot keys (non-empty values with no registry mapping, excluding
  known system-meta keys) are recorded in unknown_keys rather than silently
  dropped. Callers can inspect and decide how to handle them.
- Content hash is deterministic: same typed values → same hash regardless of
  insertion order.
- No dependency on request.form, Jinja, ProjectContext, active tabs, or
  sessionStorage.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Any, Optional

from app.workbook.registry import WORKBOOK
from app.workbook.specs import BindingStatus, FieldSpec, FieldType, WorkbookSpec

if TYPE_CHECKING:
    from domain.inputs import ProjectInputs


# ---------------------------------------------------------------------------
# System-metadata keys present in legacy snapshots that are NOT workbook
# field definitions.  These are extracted as provenance attributes and
# excluded from the unknown_keys report.
# ---------------------------------------------------------------------------

_SYSTEM_META_KEYS: frozenset[str] = frozenset({
    "active_project",
    "project_origin",
    "template_source",
})


class ProjectInputSetError(ValueError):
    """Raised when a ProjectInputSet cannot be built from a snapshot."""


# ---------------------------------------------------------------------------
# Type conversion
# ---------------------------------------------------------------------------

def _coerce_value(raw: str, spec: FieldSpec) -> Any:
    """
    Convert a raw string snapshot value to a typed Python value.

    Returns None if raw is empty/whitespace.
    Raises ProjectInputSetError on conversion failures.
    """
    stripped = str(raw).strip()
    if not stripped:
        return None
    try:
        if spec.field_type in (
            FieldType.FLOAT, FieldType.MW, FieldType.MWH,
            FieldType.KEUR, FieldType.PCT,
        ):
            return float(stripped)
        if spec.field_type in (FieldType.INT, FieldType.YEARS, FieldType.MONTHS):
            return int(float(stripped))
        if spec.field_type == FieldType.DATE:
            return date.fromisoformat(stripped)
        if spec.field_type == FieldType.BOOL:
            return stripped.lower() in ("true", "1", "yes", "on")
        # TEXT, SELECT, BPS — keep as string
        return stripped
    except (ValueError, TypeError) as exc:
        raise ProjectInputSetError(
            f"Cannot coerce snapshot key '{spec.snapshot_key}' value {raw!r} "
            f"to {spec.field_type.value}: {exc}"
        ) from exc


def _encode_for_hash(value: Any) -> str:
    """Stable string encoding for a typed value used in content hash."""
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        # Round-trip via repr to avoid floating-point formatting variance.
        return repr(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _compute_hash(workbook_version: str, values: dict[str, Any]) -> str:
    """
    Deterministic SHA-256 hash over (workbook_version, sorted field_id→value).

    Only non-None values are included so that absent snapshot keys do not
    affect the hash of projects that do have them.
    """
    payload = {
        "_workbook_version": workbook_version,
        **{k: _encode_for_hash(v) for k, v in sorted(values.items()) if v is not None},
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# ProjectInputSet
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProjectInputSet:
    """
    Canonical editable model for Workbook V2.

    Stores field values indexed by semantic field_id (from the WORKBOOK
    registry).  The original legacy snapshot is retained verbatim so that
    the existing engine adapter path can be used without re-encoding.

    Attributes
    ----------
    workbook_version : str
        Version of the WORKBOOK registry this set was validated against.
        Stored so future migration code can detect stale sets.

    values : dict[str, Any]
        Typed field values keyed by semantic field_id.  Only fields with a
        non-empty snapshot value are present; absent fields are not in the
        dict (use .get(field_id) to read with a default).

    snapshot_origin : dict[str, str]
        Verbatim legacy snapshot (string values, as stored in the DB).
        Used by to_projectinputs() so the existing adapter runs unchanged.

    template_source : str
        Routing key extracted from snapshot_origin["template_source"].
        Values: "tuho" | "oborovo" | "generic_wind" | "generic_solar" | "".

    project_origin : str
        Provenance label from snapshot_origin["project_origin"].
        Values: "factory_template" | "user_created" | "".

    unknown_keys : tuple[str, ...]
        Snapshot keys that had a non-empty value but no registry mapping
        and are not known system-meta keys.  These are recorded rather than
        silently dropped.  Empty tuple when all keys are accounted for.

    content_hash : str
        Deterministic SHA-256 (first 16 hex chars) over workbook_version
        and the sorted non-None values dict.  Changes when any field value
        changes; stable across dict insertion order.

    created_from : str
        How this instance was constructed.
        Values: "legacy_snapshot" | "v2_direct".
    """

    workbook_version: str
    values: dict[str, Any]
    snapshot_origin: dict[str, str]
    template_source: str
    project_origin: str
    unknown_keys: tuple[str, ...]
    content_hash: str
    created_from: str

    # ------------------------------------------------------------------ #
    # Construction                                                         #
    # ------------------------------------------------------------------ #

    @classmethod
    def from_snapshot(
        cls,
        snapshot: dict[str, Any],
        *,
        workbook: WorkbookSpec = WORKBOOK,
        strict: bool = False,
    ) -> "ProjectInputSet":
        """
        Build a ProjectInputSet from a legacy snapshot dict.

        Parameters
        ----------
        snapshot : dict
            Flat dict of string values as returned by _collect_form_snapshot()
            or loaded from the DB.  Values may be strings, ints, floats, or
            None; all are coerced to strings for the snapshot_origin copy
            and then type-converted via the registry.
        workbook : WorkbookSpec
            Registry to use for field_id mapping and type coercion.
            Defaults to the singleton WORKBOOK (v2.0.0).
        strict : bool
            If True, raise ProjectInputSetError when unknown_keys is non-empty.
            Default False (record unknowns, do not raise).

        Returns
        -------
        ProjectInputSet
        """
        # Normalise all values to str for the verbatim origin copy.
        snapshot_origin: dict[str, str] = {
            k: (str(v) if v is not None else "")
            for k, v in snapshot.items()
        }

        # Extract system-meta provenance fields.
        template_source = str(snapshot.get("template_source") or "").strip().lower()
        project_origin = str(snapshot.get("project_origin") or "").strip()

        # Build bidirectional lookup from registry.
        snap_to_spec: dict[str, FieldSpec] = {
            f.snapshot_key: f for f in workbook.all_fields()
        }

        values: dict[str, Any] = {}
        unknown_keys: list[str] = []
        coerce_errors: list[str] = []

        for key, raw in snapshot.items():
            raw_str = str(raw).strip() if raw is not None else ""

            if key in _SYSTEM_META_KEYS:
                # System provenance — not a workbook field, already captured above.
                continue

            if key in snap_to_spec:
                spec = snap_to_spec[key]
                if raw_str:
                    try:
                        typed = _coerce_value(raw_str, spec)
                        if typed is not None:
                            values[spec.field_id] = typed
                    except ProjectInputSetError as exc:
                        coerce_errors.append(str(exc))
                # Empty strings: field absent from values (not a None entry).
            else:
                # Key has no registry mapping.
                if raw_str:
                    unknown_keys.append(key)

        if coerce_errors and strict:
            raise ProjectInputSetError(
                "Type coercion errors during from_snapshot:\n"
                + "\n".join(f"  • {e}" for e in coerce_errors)
            )

        if unknown_keys and strict:
            raise ProjectInputSetError(
                "Unknown snapshot keys with non-empty values "
                "(no registry mapping): " + ", ".join(sorted(unknown_keys))
            )

        content_hash = _compute_hash(workbook.version, values)

        return cls(
            workbook_version=workbook.version,
            values=values,
            snapshot_origin=snapshot_origin,
            template_source=template_source,
            project_origin=project_origin,
            unknown_keys=tuple(sorted(unknown_keys)),
            content_hash=content_hash,
            created_from="legacy_snapshot",
        )

    # ------------------------------------------------------------------ #
    # Field access                                                         #
    # ------------------------------------------------------------------ #

    def get(self, field_id: str, default: Any = None) -> Any:
        """Return the typed value for a semantic field_id, or default."""
        return self.values.get(field_id, default)

    def has(self, field_id: str) -> bool:
        """Return True if this field has a non-empty value."""
        return field_id in self.values

    # ------------------------------------------------------------------ #
    # Immutable update                                                     #
    # ------------------------------------------------------------------ #

    def with_value(
        self,
        field_id: str,
        value: Any,
        *,
        workbook: WorkbookSpec = WORKBOOK,
    ) -> "ProjectInputSet":
        """
        Return a new ProjectInputSet with one field value replaced.

        Updates both values (typed) and snapshot_origin (string) for the
        affected field.  Recomputes the content hash.

        Parameters
        ----------
        field_id : str
            Semantic field ID from the registry (e.g. "technical.capacity_mw").
        value : Any
            Typed Python value to set.  Pass None to remove the field.
        workbook : WorkbookSpec
            Registry used to resolve snapshot_key for the field.

        Raises
        ------
        KeyError
            If field_id is not registered in the workbook.
        """
        spec = workbook.field(field_id)

        new_values = dict(self.values)
        new_origin = dict(self.snapshot_origin)

        if value is None:
            new_values.pop(field_id, None)
            new_origin[spec.snapshot_key] = ""
        else:
            new_values[field_id] = value
            # Encode back to string for the snapshot origin.
            if isinstance(value, date):
                new_origin[spec.snapshot_key] = value.isoformat()
            elif isinstance(value, bool):
                new_origin[spec.snapshot_key] = "true" if value else "false"
            else:
                new_origin[spec.snapshot_key] = str(value)

        new_hash = _compute_hash(self.workbook_version, new_values)

        return ProjectInputSet(
            workbook_version=self.workbook_version,
            values=new_values,
            snapshot_origin=new_origin,
            template_source=self.template_source,
            project_origin=self.project_origin,
            unknown_keys=self.unknown_keys,
            content_hash=new_hash,
            created_from=self.created_from,
        )

    # ------------------------------------------------------------------ #
    # Serialization / round-trip                                           #
    # ------------------------------------------------------------------ #

    def to_snapshot(self) -> dict[str, str]:
        """
        Return a copy of the verbatim legacy snapshot dict.

        This is the round-trip path back to the format expected by the DB
        and by build_projectinputs_from_snapshot().
        """
        return dict(self.snapshot_origin)

    # ------------------------------------------------------------------ #
    # Adapter boundary → existing engine path                             #
    # ------------------------------------------------------------------ #

    def to_projectinputs(self) -> "ProjectInputs":
        """
        Produce a domain ProjectInputs from this ProjectInputSet.

        Routes through the existing build_projectinputs_from_snapshot()
        adapter using snapshot_origin verbatim — this is the zero-drift
        guarantee for TUHO and Oborovo: the same code path that runs today
        is used unchanged.

        Note: snapshot_origin must contain the required fields for
        build_projectinputs_from_snapshot (project_type, capacity_mw, etc.).
        Factory-template snapshots that have not been populated from user
        input will raise SnapshotInputError.
        """
        from app.input_adapter import build_projectinputs_from_snapshot
        return build_projectinputs_from_snapshot(self.snapshot_origin)

    # ------------------------------------------------------------------ #
    # Diagnostics                                                          #
    # ------------------------------------------------------------------ #

    def binding_summary(self, *, workbook: WorkbookSpec = WORKBOOK) -> dict[str, list[str]]:
        """
        Return a dict grouping registered field_ids by binding status.

        Useful for diagnostics: shows which BOUND/PARTIAL/DISPLAY_ONLY fields
        have values in this ProjectInputSet.
        """
        from app.workbook.specs import BindingStatus
        result: dict[str, list[str]] = {s.value: [] for s in BindingStatus}
        for f in workbook.all_fields():
            if f.field_id in self.values:
                result[f.binding_status.value].append(f.field_id)
        return result

    def __repr__(self) -> str:
        n = len(self.values)
        unk = f", {len(self.unknown_keys)} unknown" if self.unknown_keys else ""
        return (
            f"ProjectInputSet(workbook_version={self.workbook_version!r}, "
            f"template_source={self.template_source!r}, "
            f"fields={n}{unk}, hash={self.content_hash[:8]})"
        )
