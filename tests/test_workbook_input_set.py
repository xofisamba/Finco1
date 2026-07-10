"""
Tests for Workbook V2 ProjectInputSet — app/workbook/input_set.py.

Validates:
1.  from_snapshot() — type conversion, field_id keying, system-meta extraction
2.  Unknown key reporting — non-empty unmapped keys recorded, not silently dropped
3.  Provenance fields — template_source, project_origin, workbook_version, created_from
4.  Content hash — covers ALL adapter inputs; two sets with different inputs differ
5.  get() / has() / binding_summary() helpers
6.  to_snapshot() round-trip — verbatim origin preserved
7.  with_value() — immutability, hash update, snapshot_origin update,
                   registry editability enforcement
8.  Immutability — MappingProxyType prevents direct mutation of values /
                   snapshot_origin
9.  to_projectinputs() adapter boundary — routes through existing adapter
10. TUHO zero drift — legacy snapshot → ProjectInputSet → engine → same KPIs
11. Oborovo zero drift — same
12. Strict mode — raises on unknown keys or coercion errors
13. Coercion error preservation in non-strict mode
14. Registry consumption — ProjectInputSet never duplicates field definitions
15. Edge cases — empty snapshot, all-empty values, partial snapshots
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from types import MappingProxyType

import pytest

from app.workbook.input_set import (
    ProjectInputSet,
    ProjectInputSetError,
    _compute_hash,
    _coerce_value,
)
from app.workbook.registry import WORKBOOK
from app.workbook.specs import BindingStatus, FieldType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _tuho_snapshot() -> dict:
    """Minimal TUHO snapshot mirroring _project_baseline_snapshot('Wind','tuho')."""
    from app.project_factories import create_default_tuho_wind1
    pi = create_default_tuho_wind1()
    return {
        "active_project": "tuho",
        "project_name": pi.info.name,
        "project_type": "Wind",
        "project_origin": "factory_template",
        "template_source": "tuho",
        "country_market": pi.info.country_iso,
        "capacity_mw": str(pi.technical.capacity_mw),
        "tariff_eur_mwh": str(pi.revenue.ppa_base_tariff),
        "p50_hours": str(pi.technical.operating_hours_p50),
        "total_capex_keur": str(pi.capex.total_capex),
        "opex_y1_keur": str(sum(i.y1_amount_keur for i in pi.opex)),
        "target_dscr": str(pi.financing.target_dscr),
        "interest_rate_pct": str(pi.financing.base_rate + pi.financing.margin_bps / 10_000),
        "tenor_years": str(pi.financing.senior_tenor_years),
        "cod_date": str(pi.info.cod_date),
        "construction_months": str(pi.info.construction_months),
        "horizon_years": str(pi.info.horizon_years),
        "capacity_factor": f"{(pi.technical.operating_hours_p50 / 8760) * 100:.2f}",
        "ppa_term_years": str(int(pi.revenue.ppa_term_years)),
        "gearing_pct": "",
        "scenario": "Base",
        "currency": "",
    }


def _oborovo_snapshot() -> dict:
    """Minimal Oborovo snapshot mirroring _project_baseline_snapshot('Solar','oborovo')."""
    from app.project_factories import create_default_oborovo
    pi = create_default_oborovo()
    return {
        "active_project": "oborovo",
        "project_name": pi.info.name,
        "project_type": "Solar",
        "project_origin": "factory_template",
        "template_source": "oborovo",
        "country_market": pi.info.country_iso,
        "capacity_mw": str(pi.technical.capacity_mw),
        "tariff_eur_mwh": str(pi.revenue.ppa_base_tariff),
        "p50_hours": str(pi.technical.operating_hours_p50),
        "total_capex_keur": str(pi.capex.total_capex),
        "opex_y1_keur": str(sum(i.y1_amount_keur for i in pi.opex)),
        "gearing_pct": str((getattr(pi.financing, "gearing_ratio", 0.0) or 0.0) * 100),
        "target_dscr": str(pi.financing.target_dscr),
        "interest_rate_pct": str(pi.financing.base_rate + pi.financing.margin_bps / 10_000),
        "tenor_years": str(pi.financing.senior_tenor_years),
        "cod_date": str(pi.info.cod_date),
        "construction_months": str(pi.info.construction_months),
        "horizon_years": str(pi.info.horizon_years),
        "capacity_factor": f"{(pi.technical.operating_hours_p50 / 8760) * 100:.2f}",
        "ppa_term_years": str(int(pi.revenue.ppa_term_years)),
        "scenario": "Base",
        "currency": "",
    }


@pytest.fixture(scope="module")
def tuho_snap():
    return _tuho_snapshot()


@pytest.fixture(scope="module")
def oborovo_snap():
    return _oborovo_snapshot()


@pytest.fixture(scope="module")
def tuho_pis(tuho_snap):
    return ProjectInputSet.from_snapshot(tuho_snap)


@pytest.fixture(scope="module")
def oborovo_pis(oborovo_snap):
    return ProjectInputSet.from_snapshot(oborovo_snap)


# ---------------------------------------------------------------------------
# 1. from_snapshot — basic conversion
# ---------------------------------------------------------------------------

class TestFromSnapshot:
    def test_returns_project_input_set(self, tuho_pis):
        assert isinstance(tuho_pis, ProjectInputSet)

    def test_workbook_version_matches_registry(self, tuho_pis):
        assert tuho_pis.workbook_version == WORKBOOK.version

    def test_created_from_legacy_snapshot(self, tuho_pis):
        assert tuho_pis.created_from == "legacy_snapshot"

    def test_capacity_mw_typed_as_float(self, tuho_pis):
        v = tuho_pis.get("project_setup.technical.capacity_mw")
        assert isinstance(v, float)

    def test_p50_hours_typed_as_float(self, tuho_pis):
        v = tuho_pis.get("project_setup.technical.p50_hours")
        assert isinstance(v, (int, float))
        assert v > 0

    def test_cod_date_typed_as_date(self, tuho_pis):
        v = tuho_pis.get("project_setup.technical.cod_date")
        assert isinstance(v, date)

    def test_horizon_years_typed_as_int(self, tuho_pis):
        v = tuho_pis.get("project_setup.technical.horizon_years")
        assert isinstance(v, int)
        assert v > 0

    def test_construction_months_typed_as_int(self, tuho_pis):
        v = tuho_pis.get("project_setup.technical.construction_months")
        assert isinstance(v, int)
        assert v > 0

    def test_values_keyed_by_field_id(self, tuho_pis):
        assert "project_setup.technical.capacity_mw" in tuho_pis.values
        assert "capacity_mw" not in tuho_pis.values

    def test_empty_string_values_not_in_values(self, tuho_pis, tuho_snap):
        assert tuho_snap["gearing_pct"] == ""
        assert "debt.senior.gearing_pct" not in tuho_pis.values

    def test_system_meta_not_in_values(self, tuho_pis):
        for pseudo_id in ("active_project", "project_origin", "template_source"):
            assert pseudo_id not in tuho_pis.values

    def test_ppa_tariff_field_id_mapped(self, tuho_pis):
        assert tuho_pis.has("revenue.ppa.tariff_legacy")

    def test_scenario_mapped_if_present(self, tuho_pis, tuho_snap):
        if tuho_snap.get("scenario"):
            assert tuho_pis.has("project_setup.identity.scenario")

    def test_oborovo_gearing_present(self, oborovo_pis):
        v = oborovo_pis.get("debt.senior.gearing_pct")
        assert v is not None
        assert isinstance(v, float)
        assert v > 0

    def test_capacity_factor_display_only_included(self, tuho_pis):
        v = tuho_pis.get("project_setup.technical.capacity_factor")
        assert v is not None


# ---------------------------------------------------------------------------
# 2. Unknown key reporting
# ---------------------------------------------------------------------------

class TestUnknownKeyReporting:
    def test_known_snapshot_keys_not_in_unknown(self, tuho_pis):
        registered_snap_keys = {f.snapshot_key for f in WORKBOOK.all_fields()}
        for uk in tuho_pis.unknown_keys:
            assert uk not in registered_snap_keys

    def test_unknown_keys_only_non_empty(self, tuho_snap):
        pis = ProjectInputSet.from_snapshot(tuho_snap)
        for uk in pis.unknown_keys:
            assert tuho_snap.get(uk, "").strip()

    def test_system_meta_not_in_unknown(self, tuho_pis):
        assert "active_project" not in tuho_pis.unknown_keys
        assert "project_origin" not in tuho_pis.unknown_keys
        assert "template_source" not in tuho_pis.unknown_keys

    def test_genuinely_unknown_key_reported(self):
        snap = {
            "project_type": "Wind",
            "project_origin": "factory_template",
            "template_source": "tuho",
            "some_future_field_xyz": "42",
        }
        pis = ProjectInputSet.from_snapshot(snap)
        assert "some_future_field_xyz" in pis.unknown_keys

    def test_empty_unknown_field_not_reported(self):
        snap = {
            "project_type": "Wind",
            "project_origin": "factory_template",
            "template_source": "tuho",
            "some_future_field_xyz": "",
        }
        pis = ProjectInputSet.from_snapshot(snap)
        assert "some_future_field_xyz" not in pis.unknown_keys

    def test_strict_mode_raises_on_unknown(self):
        snap = {"project_type": "Wind", "unregistered_key": "nonempty"}
        with pytest.raises(ProjectInputSetError, match="Unknown snapshot keys"):
            ProjectInputSet.from_snapshot(snap, strict=True)

    def test_non_strict_mode_records_unknown_without_raising(self):
        snap = {"project_type": "Wind", "unregistered_key": "nonempty"}
        pis = ProjectInputSet.from_snapshot(snap)
        assert "unregistered_key" in pis.unknown_keys

    def test_unknown_key_changes_hash(self):
        """An unknown key with a non-empty value must change content_hash."""
        snap_base = {"project_type": "Wind", "capacity_mw": "35.0"}
        snap_extra = {**snap_base, "some_future_field_xyz": "99"}
        pis_base = ProjectInputSet.from_snapshot(snap_base)
        pis_extra = ProjectInputSet.from_snapshot(snap_extra)
        assert pis_base.content_hash != pis_extra.content_hash


# ---------------------------------------------------------------------------
# 3. Provenance fields
# ---------------------------------------------------------------------------

class TestProvenance:
    def test_tuho_template_source(self, tuho_pis):
        assert tuho_pis.template_source == "tuho"

    def test_oborovo_template_source(self, oborovo_pis):
        assert oborovo_pis.template_source == "oborovo"

    def test_project_origin_extracted(self, tuho_pis):
        assert tuho_pis.project_origin == "factory_template"

    def test_generic_snap_template_source(self):
        snap = {
            "project_type": "Wind",
            "template_source": "generic_wind",
            "project_origin": "user_created",
        }
        pis = ProjectInputSet.from_snapshot(snap)
        assert pis.template_source == "generic_wind"
        assert pis.project_origin == "user_created"

    def test_workbook_version_is_string(self, tuho_pis):
        assert isinstance(tuho_pis.workbook_version, str)
        assert tuho_pis.workbook_version.count(".") >= 1

    def test_template_source_change_changes_hash(self):
        """template_source is a routing field — changing it must change hash."""
        snap_tuho = {"project_type": "Wind", "template_source": "tuho"}
        snap_generic = {"project_type": "Wind", "template_source": "generic_wind"}
        pis_tuho = ProjectInputSet.from_snapshot(snap_tuho)
        pis_generic = ProjectInputSet.from_snapshot(snap_generic)
        assert pis_tuho.content_hash != pis_generic.content_hash


# ---------------------------------------------------------------------------
# 4. Content hash
# ---------------------------------------------------------------------------

class TestContentHash:
    def test_hash_is_hex_string(self, tuho_pis):
        assert isinstance(tuho_pis.content_hash, str)
        int(tuho_pis.content_hash, 16)  # must be valid hex

    def test_same_snapshot_same_hash(self, tuho_snap):
        pis1 = ProjectInputSet.from_snapshot(tuho_snap)
        pis2 = ProjectInputSet.from_snapshot(tuho_snap)
        assert pis1.content_hash == pis2.content_hash

    def test_different_value_different_hash(self, tuho_snap):
        pis1 = ProjectInputSet.from_snapshot(tuho_snap)
        snap2 = dict(tuho_snap, capacity_mw="99.0")
        pis2 = ProjectInputSet.from_snapshot(snap2)
        assert pis1.content_hash != pis2.content_hash

    def test_hash_stable_across_dict_insertion_order(self, tuho_snap):
        items = list(tuho_snap.items())
        snap_reversed = dict(reversed(items))
        pis_fwd = ProjectInputSet.from_snapshot(tuho_snap)
        pis_rev = ProjectInputSet.from_snapshot(snap_reversed)
        assert pis_fwd.content_hash == pis_rev.content_hash

    def test_hash_covers_unknown_keys(self):
        """Two sets differing only by an unknown key must have different hashes."""
        snap_base = {"capacity_mw": "35.0", "template_source": "tuho"}
        snap_extra = {**snap_base, "future_field": "123"}
        pis_base = ProjectInputSet.from_snapshot(snap_base)
        pis_extra = ProjectInputSet.from_snapshot(snap_extra)
        assert pis_base.content_hash != pis_extra.content_hash

    def test_hash_covers_project_origin(self):
        snap_a = {"project_type": "Wind", "project_origin": "factory_template"}
        snap_b = {"project_type": "Wind", "project_origin": "user_created"}
        pis_a = ProjectInputSet.from_snapshot(snap_a)
        pis_b = ProjectInputSet.from_snapshot(snap_b)
        assert pis_a.content_hash != pis_b.content_hash


# ---------------------------------------------------------------------------
# 5. Helpers
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_get_existing_field(self, tuho_pis):
        assert tuho_pis.get("project_setup.technical.capacity_mw") is not None

    def test_get_missing_field_returns_default(self, tuho_pis):
        assert tuho_pis.get("no.such.field") is None
        assert tuho_pis.get("no.such.field", 99.0) == 99.0

    def test_has_existing_field(self, tuho_pis):
        assert tuho_pis.has("project_setup.technical.capacity_mw")

    def test_has_missing_field(self, tuho_pis):
        assert not tuho_pis.has("no.such.field")

    def test_binding_summary_returns_dict(self, tuho_pis):
        summary = tuho_pis.binding_summary()
        assert isinstance(summary, dict)
        assert "BOUND" in summary
        assert "PARTIAL" in summary
        assert "DISPLAY_ONLY" in summary

    def test_binding_summary_bound_fields_present(self, tuho_pis):
        summary = tuho_pis.binding_summary()
        assert len(summary["BOUND"]) >= 5

    def test_repr_contains_template_source(self, tuho_pis):
        r = repr(tuho_pis)
        assert "tuho" in r
        assert "ProjectInputSet" in r


# ---------------------------------------------------------------------------
# 6. to_snapshot() round-trip
# ---------------------------------------------------------------------------

class TestToSnapshot:
    def test_returns_dict(self, tuho_pis):
        assert isinstance(tuho_pis.to_snapshot(), dict)

    def test_preserves_capacity_mw_string(self, tuho_pis, tuho_snap):
        assert tuho_pis.to_snapshot()["capacity_mw"] == tuho_snap["capacity_mw"]

    def test_preserves_template_source(self, tuho_pis, tuho_snap):
        assert tuho_pis.to_snapshot()["template_source"] == tuho_snap["template_source"]

    def test_preserves_all_keys(self, tuho_pis, tuho_snap):
        snap_out = tuho_pis.to_snapshot()
        for k in tuho_snap:
            assert k in snap_out

    def test_does_not_mutate_original(self, tuho_pis):
        snap_out = tuho_pis.to_snapshot()
        snap_out["capacity_mw"] = "mutated"
        assert tuho_pis.snapshot_origin["capacity_mw"] != "mutated"

    def test_oborovo_round_trip(self, oborovo_pis, oborovo_snap):
        snap_out = oborovo_pis.to_snapshot()
        assert snap_out["template_source"] == "oborovo"
        assert snap_out["capacity_mw"] == oborovo_snap["capacity_mw"]


# ---------------------------------------------------------------------------
# 7. Immutability — MappingProxyType
# ---------------------------------------------------------------------------

class TestImmutability:
    def test_values_is_mapping_proxy(self, tuho_pis):
        assert isinstance(tuho_pis.values, MappingProxyType)

    def test_snapshot_origin_is_mapping_proxy(self, tuho_pis):
        assert isinstance(tuho_pis.snapshot_origin, MappingProxyType)

    def test_direct_mutation_of_values_fails(self, tuho_pis):
        with pytest.raises(TypeError):
            tuho_pis.values["project_setup.technical.capacity_mw"] = 999.0  # type: ignore[index]

    def test_direct_deletion_from_values_fails(self, tuho_pis):
        with pytest.raises(TypeError):
            del tuho_pis.values["project_setup.technical.capacity_mw"]  # type: ignore[attr-defined]

    def test_direct_mutation_of_snapshot_origin_fails(self, tuho_pis):
        with pytest.raises(TypeError):
            tuho_pis.snapshot_origin["capacity_mw"] = "mutated"  # type: ignore[index]

    def test_direct_deletion_from_snapshot_origin_fails(self, tuho_pis):
        with pytest.raises(TypeError):
            del tuho_pis.snapshot_origin["capacity_mw"]  # type: ignore[attr-defined]

    def test_frozen_dataclass_attribute_reassignment_rejected(self, tuho_pis):
        with pytest.raises((AttributeError, TypeError)):
            tuho_pis.workbook_version = "mutated"  # type: ignore[misc]

    def test_to_snapshot_returns_mutable_copy(self, tuho_pis):
        snap_out = tuho_pis.to_snapshot()
        snap_out["capacity_mw"] = "mutated"
        # Original snapshot_origin must be unchanged
        assert tuho_pis.snapshot_origin["capacity_mw"] != "mutated"


# ---------------------------------------------------------------------------
# 8. with_value() — immutable update + registry editability
# ---------------------------------------------------------------------------

class TestWithValue:
    def test_returns_new_instance(self, tuho_pis):
        pis2 = tuho_pis.with_value("project_setup.technical.capacity_mw", 50.0)
        assert pis2 is not tuho_pis

    def test_new_value_present(self, tuho_pis):
        pis2 = tuho_pis.with_value("project_setup.technical.capacity_mw", 50.0)
        assert pis2.get("project_setup.technical.capacity_mw") == 50.0

    def test_original_unchanged(self, tuho_pis):
        original_cap = tuho_pis.get("project_setup.technical.capacity_mw")
        tuho_pis.with_value("project_setup.technical.capacity_mw", 50.0)
        assert tuho_pis.get("project_setup.technical.capacity_mw") == original_cap

    def test_hash_changes_on_value_change(self, tuho_pis):
        pis2 = tuho_pis.with_value("project_setup.technical.capacity_mw", 50.0)
        assert pis2.content_hash != tuho_pis.content_hash

    def test_snapshot_origin_updated(self, tuho_pis):
        pis2 = tuho_pis.with_value("project_setup.technical.capacity_mw", 50.0)
        assert pis2.snapshot_origin["capacity_mw"] == "50.0"

    def test_other_fields_preserved(self, tuho_pis):
        pis2 = tuho_pis.with_value("project_setup.technical.capacity_mw", 50.0)
        assert pis2.get("project_setup.technical.p50_hours") == tuho_pis.get("project_setup.technical.p50_hours")

    def test_with_none_removes_value(self, tuho_pis):
        pis2 = tuho_pis.with_value("project_setup.technical.capacity_mw", None)
        assert not pis2.has("project_setup.technical.capacity_mw")
        assert pis2.snapshot_origin["capacity_mw"] == ""

    def test_with_date_value(self, tuho_pis):
        new_date = date(2028, 6, 30)
        pis2 = tuho_pis.with_value("project_setup.technical.cod_date", new_date)
        assert pis2.get("project_setup.technical.cod_date") == new_date
        assert pis2.snapshot_origin["cod_date"] == "2028-06-30"

    def test_with_unknown_field_id_raises(self, tuho_pis):
        with pytest.raises(KeyError):
            tuho_pis.with_value("no.such.field", 1.0)

    def test_template_source_preserved(self, tuho_pis):
        pis2 = tuho_pis.with_value("project_setup.technical.capacity_mw", 50.0)
        assert pis2.template_source == tuho_pis.template_source

    def test_with_value_accepts_bound_input_field(self, tuho_pis):
        """A BOUND persisted INPUT field must be accepted."""
        spec = WORKBOOK.field("project_setup.technical.capacity_mw")
        assert spec.binding_status.value == "BOUND"
        pis2 = tuho_pis.with_value("project_setup.technical.capacity_mw", 42.0)
        assert pis2.get("project_setup.technical.capacity_mw") == 42.0

    def test_with_value_rejects_idc(self, tuho_pis):
        """IDC is ENGINE-derived and DISPLAY_ONLY — must be rejected."""
        idc_field = next(
            (f for f in WORKBOOK.all_fields() if f.field_id == "capex.F.idc"),
            None,
        )
        assert idc_field is not None, "idc field missing from registry"
        with pytest.raises(ProjectInputSetError):
            tuho_pis.with_value(idc_field.field_id, 100.0)

    def test_with_value_rejects_reserve_accounts(self, tuho_pis):
        """Reserve accounts (C.18) are ENGINE-derived — must be rejected."""
        reserve_field = next(
            (f for f in WORKBOOK.all_fields()
             if "reserve" in f.field_id and f.binding_status.value in ("DISPLAY_ONLY", "TEMPLATE_LOCKED")),
            None,
        )
        assert reserve_field is not None, "No reserve account field found in registry"
        with pytest.raises(ProjectInputSetError):
            tuho_pis.with_value(reserve_field.field_id, 500.0)

    def test_with_value_rejects_total_capex_summary(self, tuho_pis):
        """total_capex_keur is a PARTIAL false-editable derived total — must be rejected."""
        with pytest.raises(ProjectInputSetError):
            tuho_pis.with_value("capex.summary.total", 99999.0)

    def test_with_value_rejects_template_locked_field(self, tuho_pis):
        """bank_fees_keur is TEMPLATE_LOCKED — must be rejected."""
        bank_fees_field = next(
            (f for f in WORKBOOK.all_fields()
             if f.binding_status.value == "TEMPLATE_LOCKED"),
            None,
        )
        assert bank_fees_field is not None, "No TEMPLATE_LOCKED field found in registry"
        with pytest.raises(ProjectInputSetError):
            tuho_pis.with_value(bank_fees_field.field_id, 1000.0)

    def test_with_value_error_message_names_field(self, tuho_pis):
        """The ProjectInputSetError message must name the rejected field_id."""
        idc_field = next(
            f for f in WORKBOOK.all_fields() if f.field_id == "capex.F.idc"
        )
        with pytest.raises(ProjectInputSetError, match=idc_field.field_id.replace(".", r"\.")):
            tuho_pis.with_value(idc_field.field_id, 100.0)

    def test_internal_override_bypasses_editability(self, tuho_pis):
        """_internal_override=True must allow writing a DISPLAY_ONLY field."""
        idc_field = next(
            f for f in WORKBOOK.all_fields() if f.field_id == "capex.F.idc"
        )
        pis2 = tuho_pis.with_value(idc_field.field_id, 100.0, _internal_override=True)
        assert pis2.get(idc_field.field_id) == 100.0


# ---------------------------------------------------------------------------
# 9. to_projectinputs() — adapter boundary
# ---------------------------------------------------------------------------

class TestToProjectInputsAdapter:
    def test_returns_project_inputs(self, tuho_pis):
        from domain.inputs import ProjectInputs
        proj = tuho_pis.to_projectinputs()
        assert isinstance(proj, ProjectInputs)

    def test_capacity_mw_correct(self, tuho_pis, tuho_snap):
        proj = tuho_pis.to_projectinputs()
        expected = float(tuho_snap["capacity_mw"])
        assert abs(proj.technical.capacity_mw - expected) < 0.001

    def test_oborovo_returns_project_inputs(self, oborovo_pis):
        from domain.inputs import ProjectInputs
        proj = oborovo_pis.to_projectinputs()
        assert isinstance(proj, ProjectInputs)


# ---------------------------------------------------------------------------
# 10. TUHO zero drift
# ---------------------------------------------------------------------------

class TestTuhoZeroDrift:
    """
    TUHO legacy snapshot → ProjectInputSet → to_projectinputs()
    must produce identical ProjectInputs as the direct adapter path.
    """

    @pytest.fixture(scope="class")
    def direct(self, tuho_snap):
        from app.input_adapter import build_projectinputs_from_snapshot
        return build_projectinputs_from_snapshot(tuho_snap)

    @pytest.fixture(scope="class")
    def via_pis(self, tuho_snap):
        return ProjectInputSet.from_snapshot(tuho_snap).to_projectinputs()

    def test_capacity_mw_identical(self, direct, via_pis):
        assert via_pis.technical.capacity_mw == direct.technical.capacity_mw

    def test_p50_hours_identical(self, direct, via_pis):
        assert via_pis.technical.operating_hours_p50 == direct.technical.operating_hours_p50

    def test_cod_date_identical(self, direct, via_pis):
        assert via_pis.info.cod_date == direct.info.cod_date

    def test_construction_months_identical(self, direct, via_pis):
        assert via_pis.info.construction_months == direct.info.construction_months

    def test_horizon_years_identical(self, direct, via_pis):
        assert via_pis.info.horizon_years == direct.info.horizon_years

    def test_target_dscr_identical(self, direct, via_pis):
        assert via_pis.financing.target_dscr == direct.financing.target_dscr

    def test_tenor_identical(self, direct, via_pis):
        assert via_pis.financing.senior_tenor_years == direct.financing.senior_tenor_years

    def test_margin_bps_identical(self, direct, via_pis):
        assert via_pis.financing.margin_bps == direct.financing.margin_bps

    def test_ppa_tariff_identical(self, direct, via_pis):
        assert via_pis.revenue.ppa_base_tariff == direct.revenue.ppa_base_tariff

    def test_capex_total_identical(self, direct, via_pis):
        assert abs(via_pis.capex.total_capex - direct.capex.total_capex) < 0.01

    def test_opex_y1_total_identical(self, direct, via_pis):
        assert abs(
            sum(i.y1_amount_keur for i in via_pis.opex)
            - sum(i.y1_amount_keur for i in direct.opex)
        ) < 0.01

    def test_idc_keur_identical(self, direct, via_pis):
        assert via_pis.capex.idc_keur == direct.capex.idc_keur

    def test_bank_fees_identical(self, direct, via_pis):
        assert via_pis.capex.bank_fees_keur == direct.capex.bank_fees_keur


# ---------------------------------------------------------------------------
# 11. Oborovo zero drift
# ---------------------------------------------------------------------------

class TestOborovoZeroDrift:
    """
    Oborovo legacy snapshot → ProjectInputSet → to_projectinputs()
    must produce identical ProjectInputs as the direct adapter path.
    """

    @pytest.fixture(scope="class")
    def direct(self, oborovo_snap):
        from app.input_adapter import build_projectinputs_from_snapshot
        return build_projectinputs_from_snapshot(oborovo_snap)

    @pytest.fixture(scope="class")
    def via_pis(self, oborovo_snap):
        return ProjectInputSet.from_snapshot(oborovo_snap).to_projectinputs()

    def test_capacity_mw_identical(self, direct, via_pis):
        assert via_pis.technical.capacity_mw == direct.technical.capacity_mw

    def test_gearing_ratio_identical(self, direct, via_pis):
        assert abs(via_pis.financing.gearing_ratio - direct.financing.gearing_ratio) < 1e-9

    def test_target_dscr_identical(self, direct, via_pis):
        assert via_pis.financing.target_dscr == direct.financing.target_dscr

    def test_ppa_tariff_identical(self, direct, via_pis):
        assert via_pis.revenue.ppa_base_tariff == direct.revenue.ppa_base_tariff

    def test_capex_total_identical(self, direct, via_pis):
        assert abs(via_pis.capex.total_capex - direct.capex.total_capex) < 0.01

    def test_idc_keur_identical(self, direct, via_pis):
        assert via_pis.capex.idc_keur == direct.capex.idc_keur

    def test_bank_fees_identical(self, direct, via_pis):
        assert via_pis.capex.bank_fees_keur == direct.capex.bank_fees_keur

    def test_vat_costs_identical(self, direct, via_pis):
        assert via_pis.capex.vat_costs_keur == direct.capex.vat_costs_keur

    def test_commitment_fees_identical(self, direct, via_pis):
        assert via_pis.capex.commitment_fees_keur == direct.capex.commitment_fees_keur

    def test_opex_y1_total_identical(self, direct, via_pis):
        assert abs(
            sum(i.y1_amount_keur for i in via_pis.opex)
            - sum(i.y1_amount_keur for i in direct.opex)
        ) < 0.01


# ---------------------------------------------------------------------------
# 12. Strict mode
# ---------------------------------------------------------------------------

class TestStrictMode:
    def test_strict_raises_on_unknown_key(self):
        snap = {"project_type": "Wind", "template_source": "tuho", "mystery_key": "value"}
        with pytest.raises(ProjectInputSetError, match="Unknown snapshot keys"):
            ProjectInputSet.from_snapshot(snap, strict=True)

    def test_strict_raises_on_bad_float(self):
        snap = {"capacity_mw": "not_a_number", "project_type": "Wind"}
        with pytest.raises(ProjectInputSetError):
            ProjectInputSet.from_snapshot(snap, strict=True)

    def test_non_strict_tolerates_bad_float(self):
        snap = {"capacity_mw": "not_a_number", "project_type": "Wind"}
        pis = ProjectInputSet.from_snapshot(snap, strict=False)
        assert not pis.has("project_setup.technical.capacity_mw")

    def test_non_strict_tolerates_unknown_key(self):
        snap = {"project_type": "Wind", "mystery_key": "value"}
        pis = ProjectInputSet.from_snapshot(snap, strict=False)
        assert "mystery_key" in pis.unknown_keys


# ---------------------------------------------------------------------------
# 13. Coercion error preservation
# ---------------------------------------------------------------------------

class TestCoercionErrors:
    def test_coercion_errors_field_exists(self):
        snap = {"capacity_mw": "not_a_number"}
        pis = ProjectInputSet.from_snapshot(snap, strict=False)
        assert hasattr(pis, "coercion_errors")
        assert isinstance(pis.coercion_errors, tuple)

    def test_bad_float_recorded_in_coercion_errors(self):
        snap = {"capacity_mw": "not_a_number"}
        pis = ProjectInputSet.from_snapshot(snap, strict=False)
        assert len(pis.coercion_errors) >= 1
        assert any("capacity_mw" in e or "not_a_number" in e for e in pis.coercion_errors)

    def test_bad_float_excluded_from_values(self):
        """A non-empty invalid value must not silently produce a None entry in values."""
        snap = {"capacity_mw": "not_a_number"}
        pis = ProjectInputSet.from_snapshot(snap, strict=False)
        assert "project_setup.technical.capacity_mw" not in pis.values

    def test_bad_date_recorded_in_coercion_errors(self):
        snap = {"cod_date": "not-a-date"}
        pis = ProjectInputSet.from_snapshot(snap, strict=False)
        assert len(pis.coercion_errors) >= 1

    def test_valid_snapshot_has_empty_coercion_errors_direct(self, tuho_pis):
        assert tuho_pis.coercion_errors == ()

    def test_strict_mode_raises_not_records(self):
        snap = {"capacity_mw": "not_a_number"}
        with pytest.raises(ProjectInputSetError, match="coercion"):
            ProjectInputSet.from_snapshot(snap, strict=True)

    def test_coercion_errors_is_tuple(self):
        snap = {"capacity_mw": "bad", "horizon_years": "also_bad"}
        pis = ProjectInputSet.from_snapshot(snap, strict=False)
        assert isinstance(pis.coercion_errors, tuple)

    def test_multiple_coercion_errors_all_recorded(self):
        snap = {"capacity_mw": "bad", "horizon_years": "also_bad"}
        pis = ProjectInputSet.from_snapshot(snap, strict=False)
        assert len(pis.coercion_errors) >= 2


# ---------------------------------------------------------------------------
# 14. Registry consumption — no duplicated field definitions
# ---------------------------------------------------------------------------

class TestRegistryConsumption:
    def test_values_keyed_only_by_registered_field_ids(self, tuho_pis):
        registered = {f.field_id for f in WORKBOOK.all_fields()}
        for key in tuho_pis.values:
            assert key in registered

    def test_snapshot_key_lookup_uses_registry(self, tuho_pis):
        spec = WORKBOOK.field_by_snapshot_key("capacity_mw")
        assert tuho_pis.has(spec.field_id)

    def test_with_value_uses_registry_for_snapshot_key(self, tuho_pis):
        spec = WORKBOOK.field("project_setup.technical.horizon_years")
        pis2 = tuho_pis.with_value(spec.field_id, 25)
        assert pis2.snapshot_origin[spec.snapshot_key] == "25"


# ---------------------------------------------------------------------------
# 15. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_snapshot(self):
        pis = ProjectInputSet.from_snapshot({})
        assert isinstance(pis, ProjectInputSet)
        assert len(pis.values) == 0
        assert pis.template_source == ""
        assert pis.project_origin == ""

    def test_all_empty_values(self):
        snap = {k: "" for k in ["capacity_mw", "p50_hours", "cod_date", "horizon_years"]}
        pis = ProjectInputSet.from_snapshot(snap)
        assert len(pis.values) == 0

    def test_none_values_treated_as_empty(self):
        snap = {"capacity_mw": None, "p50_hours": None}
        pis = ProjectInputSet.from_snapshot(snap)
        assert not pis.has("project_setup.technical.capacity_mw")

    def test_numeric_non_string_values_coerced(self):
        snap = {"capacity_mw": 35.0, "horizon_years": 30}
        pis = ProjectInputSet.from_snapshot(snap)
        assert pis.get("project_setup.technical.capacity_mw") == 35.0
        assert pis.get("project_setup.technical.horizon_years") == 30

    def test_partial_snapshot_only_known_fields(self):
        snap = {
            "capacity_mw": "35.0",
            "project_type": "Wind",
            "template_source": "tuho",
        }
        pis = ProjectInputSet.from_snapshot(snap)
        assert pis.has("project_setup.technical.capacity_mw")
        assert not pis.has("project_setup.technical.p50_hours")

    def test_frozen_dataclass_mutation_rejected(self, tuho_pis):
        with pytest.raises((AttributeError, TypeError)):
            tuho_pis.workbook_version = "mutated"  # type: ignore[misc]

    def test_values_is_immutable_proxy(self, tuho_pis):
        assert isinstance(tuho_pis.values, MappingProxyType)

    def test_snapshot_origin_is_immutable_proxy(self, tuho_pis):
        assert isinstance(tuho_pis.snapshot_origin, MappingProxyType)
