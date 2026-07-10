"""
Tests for Workbook V2 registry — app/workbook/.

Validates:
1. WorkbookSpec structure (sheets, sections, fields)
2. Stable field IDs — no duplicates
3. Snapshot key coverage — all legacy keys present in registry
4. Lookup helpers — field(), sheet(), field_by_snapshot_key()
5. Bidirectional maps
"""
from __future__ import annotations

import pytest

from app.workbook import WORKBOOK
from app.workbook.specs import FieldType, WorkbookSpec


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXPECTED_SHEETS = {"project_setup", "capex", "opex", "revenue", "debt"}

# Snapshot keys that MUST exist in the registry (drawn from _collect_form_snapshot)
REQUIRED_SNAPSHOT_KEYS = {
    "capacity_mw",
    "p50_hours",
    "cod_date",
    "construction_months",
    "horizon_years",
    "tariff_eur_mwh",
    "ppa_term_years",
    "capex_epc_contract_keur",
    "capex_grid_connection_keur",
    "capex_contingencies_keur",
    "opex_technical_management_y1_keur",
    "opex_insurance_y1_keur",
    "opex_contingencies_y1_keur",
    "rev_ppa_base_tariff",
    "rev_ppa_index",
    "rev_ppa_term_years",
    "rev_co2_enabled",
    "gearing_pct",
    "target_dscr",
    "interest_rate_pct",
    "tenor_years",
}

# Semantic IDs that must exist
REQUIRED_FIELD_IDS = {
    "project_setup.technical.capacity_mw",
    "project_setup.technical.p50_hours",
    "capex.C.epc_contract",
    "capex.F.idc",
    "opex.lines.technical_management",
    "revenue.ppa.base_tariff",
    "debt.senior.gearing_pct",
    "debt.senior.tenor_years",
}


# ---------------------------------------------------------------------------
# Structure tests
# ---------------------------------------------------------------------------

class TestWorkbookSpecStructure:
    def test_is_workbook_spec(self):
        assert isinstance(WORKBOOK, WorkbookSpec)

    def test_version_is_set(self):
        assert WORKBOOK.version == "2.0.0"

    def test_expected_sheets_present(self):
        actual = {s.sheet_id for s in WORKBOOK.sheets}
        assert EXPECTED_SHEETS.issubset(actual)

    def test_each_sheet_has_sections(self):
        for sheet in WORKBOOK.sheets:
            assert len(sheet.sections) >= 1, f"Sheet '{sheet.sheet_id}' has no sections"

    def test_each_section_has_fields(self):
        for sheet in WORKBOOK.sheets:
            for section in sheet.sections:
                assert len(section.fields) >= 1, (
                    f"Section '{section.section_id}' in sheet '{sheet.sheet_id}' has no fields"
                )

    def test_total_field_count(self):
        # Minimum sanity check — we have at least 40 fields registered
        assert len(WORKBOOK.all_fields()) >= 40

    def test_sheet_all_fields_returns_all(self):
        for sheet in WORKBOOK.sheets:
            section_total = sum(len(s.fields) for s in sheet.sections)
            assert len(sheet.all_fields()) == section_total


# ---------------------------------------------------------------------------
# Uniqueness tests
# ---------------------------------------------------------------------------

class TestFieldUniqueness:
    def test_field_ids_are_unique(self):
        ids = [f.field_id for f in WORKBOOK.all_fields()]
        assert len(ids) == len(set(ids)), "Duplicate field_id in registry"

    def test_snapshot_keys_are_unique(self):
        keys = [f.snapshot_key for f in WORKBOOK.all_fields()]
        assert len(keys) == len(set(keys)), "Duplicate snapshot_key in registry"

    def test_sheet_ids_are_unique(self):
        ids = [s.sheet_id for s in WORKBOOK.sheets]
        assert len(ids) == len(set(ids))

    def test_section_ids_unique_within_sheet(self):
        for sheet in WORKBOOK.sheets:
            ids = [s.section_id for s in sheet.sections]
            assert len(ids) == len(set(ids)), f"Duplicate section_id in sheet '{sheet.sheet_id}'"


# ---------------------------------------------------------------------------
# Coverage tests
# ---------------------------------------------------------------------------

class TestSnapshotKeyCoverage:
    def test_required_snapshot_keys_present(self):
        registered = {f.snapshot_key for f in WORKBOOK.all_fields()}
        missing = REQUIRED_SNAPSHOT_KEYS - registered
        assert not missing, f"Required snapshot keys missing from registry: {sorted(missing)}"

    def test_required_field_ids_present(self):
        registered = {f.field_id for f in WORKBOOK.all_fields()}
        missing = REQUIRED_FIELD_IDS - registered
        assert not missing, f"Required field IDs missing from registry: {sorted(missing)}"


# ---------------------------------------------------------------------------
# Lookup helper tests
# ---------------------------------------------------------------------------

class TestLookupHelpers:
    def test_sheet_lookup_by_id(self):
        sheet = WORKBOOK.sheet("project_setup")
        assert sheet.sheet_id == "project_setup"

    def test_sheet_lookup_raises_for_unknown(self):
        with pytest.raises(KeyError):
            WORKBOOK.sheet("nonexistent_sheet")

    def test_field_lookup_by_id(self):
        f = WORKBOOK.field("project_setup.technical.capacity_mw")
        assert f.snapshot_key == "capacity_mw"
        assert f.field_type == FieldType.MW

    def test_field_lookup_raises_for_unknown(self):
        with pytest.raises(KeyError):
            WORKBOOK.field("does.not.exist")

    def test_field_by_snapshot_key(self):
        f = WORKBOOK.field_by_snapshot_key("rev_ppa_base_tariff")
        assert f.field_id == "revenue.ppa.base_tariff"

    def test_field_by_snapshot_key_raises_for_unknown(self):
        with pytest.raises(KeyError):
            WORKBOOK.field_by_snapshot_key("nonexistent_key")


# ---------------------------------------------------------------------------
# Bidirectional map tests
# ---------------------------------------------------------------------------

class TestBidirectionalMaps:
    def test_snapshot_to_field_id_map_roundtrip(self):
        m = WORKBOOK.snapshot_key_to_field_id()
        assert m["capacity_mw"] == "project_setup.technical.capacity_mw"
        assert m["gearing_pct"] == "debt.senior.gearing_pct"
        assert m["rev_ppa_base_tariff"] == "revenue.ppa.base_tariff"

    def test_field_id_to_snapshot_key_map_roundtrip(self):
        m = WORKBOOK.field_id_to_snapshot_key()
        assert m["project_setup.technical.capacity_mw"] == "capacity_mw"
        assert m["capex.C.epc_contract"] == "capex_epc_contract_keur"
        assert m["opex.lines.technical_management"] == "opex_technical_management_y1_keur"

    def test_maps_are_inverse_of_each_other(self):
        fwd = WORKBOOK.snapshot_key_to_field_id()
        rev = WORKBOOK.field_id_to_snapshot_key()
        # For every snapshot_key → field_id mapping, the reverse must hold
        for snap_key, field_id in fwd.items():
            assert rev[field_id] == snap_key, (
                f"Map inversion failed: {snap_key} → {field_id} but reverse gives {rev.get(field_id)}"
            )

    def test_map_length_matches_field_count(self):
        total = len(WORKBOOK.all_fields())
        assert len(WORKBOOK.snapshot_key_to_field_id()) == total
        assert len(WORKBOOK.field_id_to_snapshot_key()) == total


# ---------------------------------------------------------------------------
# Field metadata tests
# ---------------------------------------------------------------------------

class TestFieldMetadata:
    def test_capacity_mw_is_required(self):
        f = WORKBOOK.field("project_setup.technical.capacity_mw")
        assert f.required is True

    def test_capacity_mw_has_unit(self):
        f = WORKBOOK.field("project_setup.technical.capacity_mw")
        assert f.unit == "MW"

    def test_ppa_base_tariff_type(self):
        f = WORKBOOK.field("revenue.ppa.base_tariff")
        assert f.field_type == FieldType.FLOAT

    def test_capex_fields_are_keur_type(self):
        capex_sheet = WORKBOOK.sheet("capex")
        for f in capex_sheet.all_fields():
            if f.field_id != "capex.summary.total":
                assert f.field_type == FieldType.KEUR, (
                    f"Expected KEUR for {f.field_id}, got {f.field_type}"
                )

    def test_summary_fields_not_editable(self):
        for sheet in WORKBOOK.sheets:
            for f in sheet.all_fields():
                if "summary" in f.section_id and f.section_id == "summary":
                    assert f.editable is False, (
                        f"Summary field '{f.field_id}' should not be editable"
                    )

    def test_project_type_has_options(self):
        f = WORKBOOK.field("project_setup.identity.project_type")
        assert len(f.options) >= 3
        assert "wind_onshore" in f.options
        assert "solar_pv" in f.options

    def test_sheet_ids_consistent(self):
        for sheet in WORKBOOK.sheets:
            for section in sheet.sections:
                assert section.sheet_id == sheet.sheet_id
                for f in section.fields:
                    assert f.sheet_id == sheet.sheet_id, (
                        f"Field '{f.field_id}' has sheet_id='{f.sheet_id}' but is in sheet '{sheet.sheet_id}'"
                    )

    def test_section_ids_consistent(self):
        for sheet in WORKBOOK.sheets:
            for section in sheet.sections:
                for f in section.fields:
                    assert f.section_id == section.section_id, (
                        f"Field '{f.field_id}' has section_id='{f.section_id}' but is in section '{section.section_id}'"
                    )
