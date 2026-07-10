"""
Workbook V2 — structural spec dataclasses.

Hierarchy: WorkbookSpec → SheetSpec → SectionSpec → FieldSpec

FieldSpec is the single source of truth for a workable field:
  - stable semantic ID (e.g. "technical.capacity_mw")
  - legacy snapshot key (form field name used today)
  - display metadata
  - type / validation hints

Nothing here touches the engine, the DB, or the web layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class FieldType(str, Enum):
    FLOAT = "float"
    INT = "int"
    TEXT = "text"
    DATE = "date"
    SELECT = "select"
    BOOL = "bool"
    KEUR = "keur"       # monetary amount in kEUR
    PCT = "pct"         # percentage (0–100 stored, 0.0–1.0 domain)
    BPS = "bps"         # basis points
    YEARS = "years"     # integer duration in years
    MONTHS = "months"   # integer duration in months
    MWH = "mwh"         # energy-specific numeric
    MW = "mw"           # power capacity


class FieldSection(str, Enum):
    """Which part of a sheet a field belongs to."""
    INPUTS = "inputs"
    OUTPUTS = "outputs"
    ASSUMPTIONS = "assumptions"


@dataclass(frozen=True)
class FieldSpec:
    """Descriptor for a single workbook field."""

    # Stable semantic identifier — never changes once shipped
    field_id: str                  # e.g. "technical.capacity_mw"

    # Human-readable label (used in UI and Excel headers)
    label: str

    # Legacy snapshot key in `_collect_form_snapshot()` / HTML form `name`
    snapshot_key: str              # e.g. "capacity_mw"

    # Data type
    field_type: FieldType

    # Which sheet this field belongs to (redundant with SheetSpec but useful for lookups)
    sheet_id: str                  # e.g. "project_setup"

    # Which section within the sheet
    section_id: str                # e.g. "technical"

    # Optional unit label for display
    unit: Optional[str] = None

    # Tooltip / description shown in UI
    description: Optional[str] = None

    # Whether this field is editable by the user (vs read-only computed)
    editable: bool = True

    # Whether this field is required for a valid model run
    required: bool = False

    # For SELECT fields: valid option values
    options: tuple[str, ...] = field(default_factory=tuple)

    # Min / max for numeric validation (None = unconstrained)
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    # Decimal places for display
    decimals: Optional[int] = None

    # Order within section (lower = first)
    order: int = 0


@dataclass(frozen=True)
class SectionSpec:
    """A named group of fields within a sheet."""
    section_id: str         # e.g. "technical"
    label: str              # e.g. "Technical Parameters"
    sheet_id: str
    order: int = 0
    fields: tuple[FieldSpec, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SheetSpec:
    """One workbook tab / sheet."""
    sheet_id: str           # e.g. "project_setup"
    label: str              # e.g. "Project Setup"
    icon: Optional[str] = None
    order: int = 0
    sections: tuple[SectionSpec, ...] = field(default_factory=tuple)

    def all_fields(self) -> tuple[FieldSpec, ...]:
        return tuple(f for s in self.sections for f in s.fields)


@dataclass(frozen=True)
class WorkbookSpec:
    """Root registry object for the entire workbook."""
    version: str            # e.g. "2.0.0"
    sheets: tuple[SheetSpec, ...] = field(default_factory=tuple)

    # ------------------------------------------------------------------ #
    # Lookup helpers                                                       #
    # ------------------------------------------------------------------ #

    def sheet(self, sheet_id: str) -> SheetSpec:
        for s in self.sheets:
            if s.sheet_id == sheet_id:
                return s
        raise KeyError(f"No sheet '{sheet_id}' in WorkbookSpec")

    def field(self, field_id: str) -> FieldSpec:
        for s in self.sheets:
            for f in s.all_fields():
                if f.field_id == field_id:
                    return f
        raise KeyError(f"No field '{field_id}' in WorkbookSpec")

    def field_by_snapshot_key(self, snapshot_key: str) -> FieldSpec:
        for s in self.sheets:
            for f in s.all_fields():
                if f.snapshot_key == snapshot_key:
                    return f
        raise KeyError(f"No field with snapshot_key='{snapshot_key}' in WorkbookSpec")

    def all_fields(self) -> tuple[FieldSpec, ...]:
        return tuple(f for s in self.sheets for f in s.all_fields())

    def snapshot_key_to_field_id(self) -> dict[str, str]:
        """Map legacy snapshot keys → semantic field IDs."""
        return {f.snapshot_key: f.field_id for f in self.all_fields()}

    def field_id_to_snapshot_key(self) -> dict[str, str]:
        """Map semantic field IDs → legacy snapshot keys."""
        return {f.field_id: f.snapshot_key for f in self.all_fields()}
