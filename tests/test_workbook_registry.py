"""
Tests for Workbook V2 registry — app/workbook/.

Validates:
1. WorkbookSpec structure (sheets, sections, fields)
2. Field ID and snapshot key uniqueness
3. Snapshot key coverage — all required legacy keys present
4. Lookup helpers — field(), sheet(), field_by_snapshot_key()
5. Bidirectional maps
6. Canonical contract invariants:
   - Editable fields have persistence metadata and valid binding status
   - Runtime-only fields are never editable
   - C.17 and C.18 fields are always read-only
   - Derived/summary fields are always read-only
   - C.13 Contingencies (CAPEX) always read-only
   - OPEX contingencies always read-only
   - Scenario-enabled fields have a valid scenario policy
   - Every field has an explicit binding status
   - DISPLAY_ONLY / TEMPLATE_LOCKED fields are never editable
7. Excel mappings present on CAPEX C-code fields
8. Deterministic registry serialization
"""
from __future__ import annotations

import pytest

from app.workbook import WORKBOOK
from app.workbook.specs import (
    BindingStatus,
    FieldKind,
    FieldType,
    ScenarioPolicy,
    SourceOfTruth,
    WorkbookSpec,
)


# ---------------------------------------------------------------------------
# Test fixtures / constants
# ---------------------------------------------------------------------------

EXPECTED_SHEETS = {"project_setup", "capex", "opex", "revenue", "debt"}

# Snapshot keys that must be present in the registry (drawn from _collect_form_snapshot)
REQUIRED_SNAPSHOT_KEYS = {
    "capacity_mw", "p50_hours", "cod_date", "construction_months", "horizon_years",
    "tariff_eur_mwh", "ppa_term_years",
    "capex_epc_contract_keur", "capex_grid_connection_keur", "capex_contingencies_keur",
    "opex_technical_management_y1_keur", "opex_insurance_y1_keur", "opex_contingencies_y1_keur",
    "rev_ppa_base_tariff", "rev_ppa_index", "rev_ppa_term_years",
    "rev_co2_enabled", "rev_co2_price",
    "gearing_pct", "target_dscr", "interest_rate_pct", "tenor_years",
    "total_capex_keur", "opex_y1_keur",
}

# Semantic IDs that must exist
REQUIRED_FIELD_IDS = {
    "project_setup.technical.capacity_mw",
    "project_setup.technical.p50_hours",
    "capex.C.epc_contract",
    "capex.F.idc",
    "capex.F.bank_fees",
    "capex.F.commitment_fees",
    "capex.R.reserve_accounts",
    "capex.C.contingencies",
    "capex.summary.total",
    "opex.lines.technical_management",
    "opex.lines.contingencies",
    "opex.summary.total_y1",
    "revenue.ppa.base_tariff",
    "debt.senior.gearing_pct",
    "debt.senior.tenor_years",
}

# C.17 section fields — must all be non-editable
C17_FIELD_IDS = {
    "capex.F.idc",
    "capex.F.bank_fees",
    "capex.F.commitment_fees",
    "capex.F.other_financial",
    "capex.F.vat_costs",
}

# C.18 section fields — must all be non-editable
C18_FIELD_IDS = {"capex.R.reserve_accounts"}

# Derived summary totals — must all be non-editable
SUMMARY_TOTAL_FIELD_IDS = {"capex.summary.total", "opex.summary.total_y1"}

# Fields that must have DISPLAY_ONLY or TEMPLATE_LOCKED binding status — must be non-editable
DISPLAY_OR_LOCKED_BINDING = {BindingStatus.DISPLAY_ONLY, BindingStatus.TEMPLATE_LOCKED}


# ---------------------------------------------------------------------------
# 1. Structure
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
        assert len(WORKBOOK.all_fields()) >= 50

    def test_sheet_all_fields_returns_all(self):
        for sheet in WORKBOOK.sheets:
            section_total = sum(len(s.fields) for s in sheet.sections)
            assert len(sheet.all_fields()) == section_total

    def test_capex_has_c17_section(self):
        capex = WORKBOOK.sheet("capex")
        section_ids = {s.section_id for s in capex.sections}
        assert "F" in section_ids, "C.17 (financing) section 'F' missing from capex sheet"

    def test_capex_has_c18_section(self):
        capex = WORKBOOK.sheet("capex")
        section_ids = {s.section_id for s in capex.sections}
        assert "R" in section_ids, "C.18 (reserve accounts) section 'R' missing from capex sheet"


# ---------------------------------------------------------------------------
# 2. Uniqueness
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
# 3. Snapshot key coverage
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
# 4. Lookup helpers
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
# 5. Bidirectional maps
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
        for snap_key, field_id in fwd.items():
            assert rev[field_id] == snap_key, (
                f"Map inversion failed: {snap_key} → {field_id} but reverse gives {rev.get(field_id)}"
            )

    def test_map_length_matches_field_count(self):
        total = len(WORKBOOK.all_fields())
        assert len(WORKBOOK.snapshot_key_to_field_id()) == total
        assert len(WORKBOOK.field_id_to_snapshot_key()) == total


# ---------------------------------------------------------------------------
# 6a. Editable field contract invariants
# ---------------------------------------------------------------------------

class TestEditableFieldInvariants:
    """Editable fields cannot have contradictory binding or persistence metadata."""

    def test_editable_fields_not_display_only(self):
        """An editable field cannot have binding_status DISPLAY_ONLY."""
        violations = [
            f.field_id for f in WORKBOOK.editable_fields()
            if f.binding_status == BindingStatus.DISPLAY_ONLY
        ]
        assert not violations, (
            f"Editable fields with DISPLAY_ONLY binding (forbidden): {violations}"
        )

    def test_editable_fields_not_unsupported(self):
        """An editable field cannot have binding_status UNSUPPORTED."""
        violations = [
            f.field_id for f in WORKBOOK.editable_fields()
            if f.binding_status == BindingStatus.UNSUPPORTED
        ]
        assert not violations, (
            f"Editable fields with UNSUPPORTED binding (forbidden): {violations}"
        )

    def test_editable_fields_not_template_locked(self):
        """An editable field cannot have binding_status TEMPLATE_LOCKED."""
        violations = [
            f.field_id for f in WORKBOOK.editable_fields()
            if f.binding_status == BindingStatus.TEMPLATE_LOCKED
        ]
        assert not violations, (
            f"Editable fields with TEMPLATE_LOCKED binding (forbidden): {violations}"
        )

    def test_editable_fields_have_persisted_or_partial(self):
        """
        Every editable field must be either persisted (persisted=True) or
        explicitly classified as PARTIAL — allowing workspace-draft fields.
        DISPLAY_ONLY non-persisted editable fields are forbidden.
        """
        violations = [
            f.field_id for f in WORKBOOK.editable_fields()
            if not f.persisted and f.binding_status == BindingStatus.BOUND
        ]
        assert not violations, (
            f"BOUND editable fields with persisted=False (impossible path): {violations}"
        )

    def test_editable_fields_have_explicit_kind(self):
        """All editable fields must have kind INPUT (never DERIVED_DISPLAY, TEMPLATE_INPUT, etc.)."""
        violations = [
            f.field_id for f in WORKBOOK.editable_fields()
            if f.kind != FieldKind.INPUT
        ]
        assert not violations, (
            f"Editable fields with non-INPUT kind (forbidden): {violations}"
        )


# ---------------------------------------------------------------------------
# 6b. Runtime-only invariant
# ---------------------------------------------------------------------------

class TestRuntimeOnlyInvariants:
    def test_runtime_only_fields_are_never_editable(self):
        violations = [
            f.field_id for f in WORKBOOK.all_fields()
            if f.runtime_only and f.editable
        ]
        assert not violations, (
            f"runtime_only=True fields that are editable (forbidden): {violations}"
        )

    def test_runtime_only_fields_are_never_persisted(self):
        violations = [
            f.field_id for f in WORKBOOK.all_fields()
            if f.runtime_only and f.persisted
        ]
        assert not violations, (
            f"runtime_only=True fields with persisted=True (contradiction): {violations}"
        )


# ---------------------------------------------------------------------------
# 6c. C.17 and C.18 invariants
# ---------------------------------------------------------------------------

class TestC17C18Invariants:
    def test_c17_fields_are_read_only(self):
        """All C.17 financing-cost fields must be non-editable."""
        for fid in C17_FIELD_IDS:
            f = WORKBOOK.field(fid)
            assert not f.editable, f"C.17 field '{fid}' must not be editable"

    def test_c18_fields_are_read_only(self):
        """All C.18 reserve-account fields must be non-editable."""
        for fid in C18_FIELD_IDS:
            f = WORKBOOK.field(fid)
            assert not f.editable, f"C.18 field '{fid}' must not be editable"

    def test_c17_fields_not_bound(self):
        """C.17 fields are never BOUND — they are DISPLAY_ONLY or TEMPLATE_LOCKED."""
        for fid in C17_FIELD_IDS:
            f = WORKBOOK.field(fid)
            assert f.binding_status in DISPLAY_OR_LOCKED_BINDING, (
                f"C.17 field '{fid}' has unexpected binding_status={f.binding_status}"
            )

    def test_c18_field_is_display_only(self):
        f = WORKBOOK.field("capex.R.reserve_accounts")
        assert f.binding_status == BindingStatus.DISPLAY_ONLY

    def test_idc_source_is_engine(self):
        """IDC is engine-computed, not user-entered or template-locked."""
        f = WORKBOOK.field("capex.F.idc")
        assert f.source_of_truth == SourceOfTruth.ENGINE
        assert f.kind == FieldKind.DERIVED_DISPLAY

    def test_bank_fees_source_is_template(self):
        """Bank fees are Excel/template anchors, not user-entered."""
        f = WORKBOOK.field("capex.F.bank_fees")
        assert f.source_of_truth == SourceOfTruth.TEMPLATE
        assert f.kind == FieldKind.TEMPLATE_INPUT

    def test_c17_section_has_no_scenario_override(self):
        """C.17 fields cannot be scenario-overridden."""
        for fid in C17_FIELD_IDS:
            f = WORKBOOK.field(fid)
            assert f.scenario_policy == ScenarioPolicy.NOT_ALLOWED, (
                f"C.17 field '{fid}' must have scenario_policy=NOT_ALLOWED"
            )


# ---------------------------------------------------------------------------
# 6d. Derived summary totals
# ---------------------------------------------------------------------------

class TestDerivedSummaryTotals:
    def test_capex_summary_total_not_editable(self):
        f = WORKBOOK.field("capex.summary.total")
        assert not f.editable

    def test_opex_summary_total_not_editable(self):
        f = WORKBOOK.field("opex.summary.total_y1")
        assert not f.editable

    def test_capex_summary_total_has_dependencies(self):
        f = WORKBOOK.field("capex.summary.total")
        assert len(f.dependencies) >= 5, "capex.summary.total should list its component dependencies"

    def test_opex_summary_total_has_dependencies(self):
        f = WORKBOOK.field("opex.summary.total_y1")
        assert len(f.dependencies) >= 5

    def test_summary_fields_are_derived_display(self):
        for fid in SUMMARY_TOTAL_FIELD_IDS:
            f = WORKBOOK.field(fid)
            assert f.kind == FieldKind.DERIVED_DISPLAY, (
                f"Summary field '{fid}' must have kind=DERIVED_DISPLAY, got {f.kind}"
            )

    def test_capex_contingencies_not_editable(self):
        """C.13 is always formula-derived — never editable."""
        f = WORKBOOK.field("capex.C.contingencies")
        assert not f.editable
        assert f.binding_status == BindingStatus.DISPLAY_ONLY
        assert f.kind == FieldKind.DERIVED_DISPLAY

    def test_opex_contingencies_not_editable(self):
        """OPEX contingencies are always formula-derived — never editable."""
        f = WORKBOOK.field("opex.lines.contingencies")
        assert not f.editable
        assert f.binding_status == BindingStatus.DISPLAY_ONLY
        assert f.kind == FieldKind.DERIVED_DISPLAY


# ---------------------------------------------------------------------------
# 6e. Scenario policy
# ---------------------------------------------------------------------------

class TestScenarioPolicy:
    def test_every_field_has_scenario_policy(self):
        """All fields must have an explicit ScenarioPolicy value."""
        violations = [
            f.field_id for f in WORKBOOK.all_fields()
            if f.scenario_policy not in list(ScenarioPolicy)
        ]
        assert not violations, f"Fields with invalid scenario_policy: {violations}"

    def test_derived_display_fields_have_not_allowed_policy(self):
        """Derived/display fields cannot be scenario-overridden."""
        violations = [
            f.field_id for f in WORKBOOK.all_fields()
            if f.kind == FieldKind.DERIVED_DISPLAY
            and f.scenario_policy != ScenarioPolicy.NOT_ALLOWED
        ]
        assert not violations, (
            f"DERIVED_DISPLAY fields with scenario override (forbidden): {violations}"
        )

    def test_override_fields_are_editable_or_partial(self):
        """Only editable or PARTIAL-bound fields should allow scenario override."""
        violations = [
            f.field_id for f in WORKBOOK.all_fields()
            if f.scenario_policy == ScenarioPolicy.OVERRIDE
            and f.binding_status == BindingStatus.DISPLAY_ONLY
        ]
        assert not violations, (
            f"DISPLAY_ONLY fields with scenario OVERRIDE (forbidden): {violations}"
        )

    def test_technical_params_allow_override(self):
        assert WORKBOOK.field("project_setup.technical.capacity_mw").scenario_policy == ScenarioPolicy.OVERRIDE
        assert WORKBOOK.field("project_setup.technical.p50_hours").scenario_policy == ScenarioPolicy.OVERRIDE

    def test_revenue_params_allow_override(self):
        assert WORKBOOK.field("revenue.ppa.base_tariff").scenario_policy == ScenarioPolicy.OVERRIDE

    def test_identity_fields_not_overridable(self):
        assert WORKBOOK.field("project_setup.identity.project_name").scenario_policy == ScenarioPolicy.NOT_ALLOWED
        assert WORKBOOK.field("project_setup.technical.cod_date").scenario_policy == ScenarioPolicy.NOT_ALLOWED


# ---------------------------------------------------------------------------
# 6f. Binding status completeness
# ---------------------------------------------------------------------------

class TestBindingStatusCompleteness:
    def test_every_field_has_binding_status(self):
        violations = [
            f.field_id for f in WORKBOOK.all_fields()
            if f.binding_status not in list(BindingStatus)
        ]
        assert not violations, f"Fields with invalid binding_status: {violations}"

    def test_display_only_fields_are_not_editable(self):
        violations = [
            f.field_id for f in WORKBOOK.fields_by_binding_status(BindingStatus.DISPLAY_ONLY)
            if f.editable
        ]
        assert not violations, f"DISPLAY_ONLY fields that are editable (forbidden): {violations}"

    def test_template_locked_fields_are_not_editable(self):
        violations = [
            f.field_id for f in WORKBOOK.fields_by_binding_status(BindingStatus.TEMPLATE_LOCKED)
            if f.editable
        ]
        assert not violations, f"TEMPLATE_LOCKED fields that are editable (forbidden): {violations}"

    def test_false_editable_surface_classified_as_partial(self):
        """
        Known false-editable fields in the HTML must be PARTIAL, not BOUND.
        These are fields that appear editable in the UI but whose values do not
        reach the engine as primary inputs.
        """
        expected_partial = {
            "capex.summary.total",        # inputs_section shows as editable; engine derives from lines
            "opex.summary.total_y1",      # inputs_section shows as editable; engine derives from lines
            "revenue.ppa.tariff_legacy",  # legacy key; superseded by rev_ppa_base_tariff
            "revenue.ppa.ppa_term_legacy",# legacy key; superseded by rev_ppa_term_years
        }
        for fid in expected_partial:
            f = WORKBOOK.field(fid)
            assert f.binding_status == BindingStatus.PARTIAL, (
                f"False-editable field '{fid}' must be PARTIAL, got {f.binding_status}"
            )

    def test_capacity_factor_is_display_only(self):
        """capacity_factor is shown as calculated in the UI; must not be BOUND or editable."""
        f = WORKBOOK.field("project_setup.technical.capacity_factor")
        assert f.binding_status == BindingStatus.DISPLAY_ONLY
        assert not f.editable

    def test_capacity_factor_has_dependencies(self):
        f = WORKBOOK.field("project_setup.technical.capacity_factor")
        assert "project_setup.technical.capacity_mw" in f.dependencies
        assert "project_setup.technical.p50_hours" in f.dependencies

    def test_bound_fields_have_engine_path_or_explicit_exception(self):
        """
        BOUND fields should have an engine_path OR be covered by a known exception
        (fields where the adapter does the translation without a 1:1 dotted path).
        """
        known_no_path = {
            "project_setup.identity.country_market",  # mapped via string lookup, not dotted path
        }
        violations = [
            f.field_id for f in WORKBOOK.fields_by_binding_status(BindingStatus.BOUND)
            if f.engine_path is None and f.field_id not in known_no_path
        ]
        assert not violations, (
            f"BOUND fields with no engine_path and no known exception: {violations}"
        )


# ---------------------------------------------------------------------------
# 7. Excel mappings
# ---------------------------------------------------------------------------

class TestExcelMappings:
    def test_capex_c_code_fields_have_tuho_mapping(self):
        """All C.01–C.16 CAPEX input fields must have an Excel TUHO C-code mapping."""
        capex_c_inputs = [
            f for f in WORKBOOK.sheet("capex").all_fields()
            if f.section_id in ("C", "D") and f.kind == FieldKind.INPUT
        ]
        assert len(capex_c_inputs) >= 10, "Expected at least 10 editable CAPEX line items"
        violations = [f.field_id for f in capex_c_inputs if not f.excel_tuho]
        assert not violations, f"CAPEX input fields missing excel_tuho mapping: {violations}"

    def test_capex_c_code_fields_have_oborovo_mapping(self):
        capex_c_inputs = [
            f for f in WORKBOOK.sheet("capex").all_fields()
            if f.section_id in ("C", "D") and f.kind == FieldKind.INPUT
        ]
        violations = [f.field_id for f in capex_c_inputs if not f.excel_oborovo]
        assert not violations, f"CAPEX input fields missing excel_oborovo mapping: {violations}"

    def test_c17_fields_have_excel_mappings(self):
        for fid in C17_FIELD_IDS:
            f = WORKBOOK.field(fid)
            assert f.excel_tuho, f"C.17 field '{fid}' missing excel_tuho"
            assert f.excel_oborovo, f"C.17 field '{fid}' missing excel_oborovo"

    def test_c18_field_has_excel_mapping(self):
        f = WORKBOOK.field("capex.R.reserve_accounts")
        assert f.excel_tuho
        assert f.excel_oborovo

    def test_excel_tuho_mapping_not_empty_string(self):
        violations = [
            f.field_id for f in WORKBOOK.all_fields()
            if f.excel_tuho is not None and f.excel_tuho.strip() == ""
        ]
        assert not violations, f"Fields with empty excel_tuho string: {violations}"

    def test_excel_oborovo_mapping_not_empty_string(self):
        violations = [
            f.field_id for f in WORKBOOK.all_fields()
            if f.excel_oborovo is not None and f.excel_oborovo.strip() == ""
        ]
        assert not violations, f"Fields with empty excel_oborovo string: {violations}"


# ---------------------------------------------------------------------------
# 8. Registry serialization determinism
# ---------------------------------------------------------------------------

class TestDeterministicSerialization:
    def test_all_fields_order_is_stable(self):
        """Calling all_fields() twice returns fields in the same order."""
        run1 = [f.field_id for f in WORKBOOK.all_fields()]
        run2 = [f.field_id for f in WORKBOOK.all_fields()]
        assert run1 == run2

    def test_snapshot_key_map_is_stable(self):
        m1 = WORKBOOK.snapshot_key_to_field_id()
        m2 = WORKBOOK.snapshot_key_to_field_id()
        assert m1 == m2

    def test_field_ids_are_stable_strings(self):
        """All field_ids must be non-empty strings."""
        violations = [
            f.field_id for f in WORKBOOK.all_fields()
            if not isinstance(f.field_id, str) or not f.field_id.strip()
        ]
        assert not violations

    def test_snapshot_keys_are_stable_strings(self):
        violations = [
            f.snapshot_key for f in WORKBOOK.all_fields()
            if not isinstance(f.snapshot_key, str) or not f.snapshot_key.strip()
        ]
        assert not violations

    def test_workbook_spec_is_frozen(self):
        """WorkbookSpec is a frozen dataclass — mutations must fail."""
        with pytest.raises((AttributeError, TypeError)):
            WORKBOOK.version = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 9. Field metadata consistency
# ---------------------------------------------------------------------------

class TestFieldMetadataConsistency:
    def test_sheet_ids_consistent(self):
        for sheet in WORKBOOK.sheets:
            for section in sheet.sections:
                assert section.sheet_id == sheet.sheet_id
                for f in section.fields:
                    assert f.sheet_id == sheet.sheet_id, (
                        f"Field '{f.field_id}' has sheet_id='{f.sheet_id}' "
                        f"but is in sheet '{sheet.sheet_id}'"
                    )

    def test_section_ids_consistent(self):
        for sheet in WORKBOOK.sheets:
            for section in sheet.sections:
                for f in section.fields:
                    assert f.section_id == section.section_id, (
                        f"Field '{f.field_id}' has section_id='{f.section_id}' "
                        f"but is in section '{section.section_id}'"
                    )

    def test_capacity_mw_contract(self):
        f = WORKBOOK.field("project_setup.technical.capacity_mw")
        assert f.required is True
        assert f.unit == "MW"
        assert f.field_type == FieldType.MW
        assert f.kind == FieldKind.INPUT
        assert f.persisted is True
        assert f.engine_path == "technical.capacity_mw"
        assert f.binding_status == BindingStatus.BOUND
        assert f.scenario_policy == ScenarioPolicy.OVERRIDE

    def test_ppa_base_tariff_contract(self):
        f = WORKBOOK.field("revenue.ppa.base_tariff")
        assert f.field_type == FieldType.FLOAT
        assert f.kind == FieldKind.INPUT
        assert f.engine_path == "revenue.ppa_base_tariff"
        assert f.binding_status == BindingStatus.BOUND

    def test_capex_input_fields_are_keur_type(self):
        capex_sheet = WORKBOOK.sheet("capex")
        for f in capex_sheet.all_fields():
            if f.kind == FieldKind.INPUT:
                assert f.field_type == FieldType.KEUR, (
                    f"Expected KEUR for editable CAPEX field {f.field_id}, got {f.field_type}"
                )

    def test_project_type_has_options(self):
        f = WORKBOOK.field("project_setup.identity.project_type")
        assert len(f.options) >= 3
        assert "wind_onshore" in f.options
        assert "solar_pv" in f.options

    def test_idc_engine_path(self):
        f = WORKBOOK.field("capex.F.idc")
        assert f.engine_path == "capex.idc_keur"

    def test_interest_rate_engine_path(self):
        """interest_rate_pct is stored as % but drives financing.margin_bps via input_adapter."""
        f = WORKBOOK.field("debt.senior.interest_rate_pct")
        assert f.engine_path == "financing.margin_bps"

    def test_dependency_field_ids_exist_in_registry(self):
        """All dependency field_ids in FieldSpec.dependencies must be registered."""
        registered = {f.field_id for f in WORKBOOK.all_fields()}
        for f in WORKBOOK.all_fields():
            for dep in f.dependencies:
                assert dep in registered, (
                    f"Field '{f.field_id}' lists dependency '{dep}' which is not in the registry"
                )
