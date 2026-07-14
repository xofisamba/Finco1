"""
Unit tests for app.v2.opex_assembly — canonical per-line OPEX assembly.

Uses real domain OpexItem instances from finco_core.inputs._models and real
project factory tuples so the tests exercise the actual production type.

Covers:
  1. Snapshot key ↔ B.XX mapping completeness.
  2. Missing override inherits base value.
  3. Explicit zero remains zero.
  4. Edited base line replaces, not duplicates.
  5. Contingency (B.13) remains derived — never overridden.
  6. Wind factory name variants route correctly.
  7. Unmapped items (Taxes, Salary&Payroll) pass through unchanged.
  8. has_per_line_overrides fast-paths.
  9. get_per_line_override_for_group returns correct values.
 10. All B.01–B.12 lines override the correct field (solar factory).
 11. Integration: Technical Management 200 → 300 through real Oborovo base.
 12. Integration: build_projectinputs_from_snapshot applies per-line overrides.
"""
from __future__ import annotations

import dataclasses
import pytest

from finco_core.inputs._models import OpexItem

from app.v2.opex_assembly import (
    SNAPSHOT_KEY_TO_OPEX_CODE,
    OPEX_CODE_TO_SNAPSHOT_KEY,
    _OPEX_NAME_TO_CODE,
    build_effective_draft_opex,
    get_per_line_override_for_group,
    has_per_line_overrides,
)


# ---------------------------------------------------------------------------
# Fixtures using real factory OpexItem tuples
# ---------------------------------------------------------------------------

def _oborovo_opex() -> tuple:
    from app.project_factories import create_default_oborovo
    return create_default_oborovo().opex


def _tuho_opex() -> tuple:
    from app.project_factories import create_default_tuho_wind1
    return create_default_tuho_wind1().opex


def _generic_solar_opex() -> tuple:
    from app.project_factories import create_default_solar_project
    return create_default_solar_project().opex


def _generic_wind_opex() -> tuple:
    from app.project_factories import create_default_wind_project
    return create_default_wind_project().opex


def _make_solar_base() -> tuple:
    """Minimal real-OpexItem tuple covering B.01–B.13 with Oborovo names."""
    return tuple([
        OpexItem("Technical Management",    198.0, 0.02),
        OpexItem("Infrastructure Maintenance", 244.0, 0.02),
        OpexItem("Maintain Site",            45.0, 0.02),
        OpexItem("Clean Material",           40.0, 0.02),
        OpexItem("Security",                 30.0, 0.02),
        OpexItem("Insurance",               255.0, 0.02),
        OpexItem("Lease & Property Tax",    208.0, 0.02),
        OpexItem("Power Expenses",          177.0, 0.0),
        OpexItem("Fees",                     14.0, 0.0),
        OpexItem("Audit&Accounting&Legal",   24.0, 0.02),
        OpexItem("Bank Fees",                20.0, 0.02),
        OpexItem("Environmental&Social",     32.0, 0.02),
        OpexItem("Contingencies", 0.0, 0.02, percentage_of_opex=0.05),
        OpexItem("Taxes",                     0.0, 0.0),
        OpexItem("Salary&Payroll",            0.0, 0.0),
    ])


def _make_wind_base() -> tuple:
    """Minimal real-OpexItem tuple covering B.01–B.13 with TUHO names."""
    return tuple([
        OpexItem("Technical Management",         280.0, 0.02),
        OpexItem("O&M Preventive & Corrective",  427.0, 0.02),
        OpexItem("Maintain Site",                 68.0, 0.02),
        OpexItem("Clean Material",                 5.0, 0.02),
        OpexItem("Security",                      50.0, 0.02),
        OpexItem("Insurance",                    469.0, 0.02),
        OpexItem("Lease & Property Tax",         249.0, 0.02),
        OpexItem("Power Expenses",                94.0, 0.02),
        OpexItem("Audit & Accounting & Legal",    24.0, 0.02),
        OpexItem("Bank Fees (opex)",              20.0, 0.02),
        OpexItem("Environmental & Social Management", 200.0, 0.02),
        OpexItem("Contingencies", 0.0, 0.02, percentage_of_opex=0.05),
    ])


# ---------------------------------------------------------------------------
# 1. Snapshot key ↔ B.XX mapping completeness
# ---------------------------------------------------------------------------

class TestMappingCompleteness:
    def test_all_registered_fields_present(self):
        for key in [
            "opex_technical_management_y1_keur",
            "opex_o_and_m_preventive_and_corrective_y1_keur",
            "opex_maintain_site_y1_keur",
            "opex_clean_material_y1_keur",
            "opex_security_y1_keur",
            "opex_insurance_y1_keur",
            "opex_lease_and_property_tax_y1_keur",
            "opex_power_expenses_y1_keur",
            "opex_audit_and_accounting_and_legal_y1_keur",
            "opex_bank_fees_opex_y1_keur",
            "opex_environmental_and_social_management_y1_keur",
            "opex_contingencies_y1_keur",
        ]:
            assert key in SNAPSHOT_KEY_TO_OPEX_CODE, f"{key} missing"

    def test_reverse_mapping_round_trips(self):
        for key, code in SNAPSHOT_KEY_TO_OPEX_CODE.items():
            assert OPEX_CODE_TO_SNAPSHOT_KEY.get(code) == key

    def test_b09_has_no_snapshot_key(self):
        assert "B.09" not in OPEX_CODE_TO_SNAPSHOT_KEY

    def test_solar_factory_names_map(self):
        for name in [
            "Technical Management", "Infrastructure Maintenance", "Maintain Site",
            "Clean Material", "Security", "Insurance", "Lease & Property Tax",
            "Power Expenses", "Fees", "Audit&Accounting&Legal", "Bank Fees",
            "Environmental&Social", "Contingencies",
        ]:
            assert name in _OPEX_NAME_TO_CODE, f"Solar name {name!r} not in mapping"

    def test_wind_factory_names_map(self):
        for name in [
            "Technical Management", "O&M Preventive & Corrective", "Maintain Site",
            "Clean Material", "Security", "Insurance", "Lease & Property Tax",
            "Power Expenses", "Audit & Accounting & Legal", "Bank Fees (opex)",
            "Environmental & Social Management", "Contingencies",
        ]:
            assert name in _OPEX_NAME_TO_CODE, f"Wind name {name!r} not in mapping"

    def test_generic_solar_factory_names_map(self):
        """Generic solar factory uses simplified names — must all be mapped."""
        for name in ["Technical Management", "Insurance", "Maintenance", "Lease & Tax"]:
            assert name in _OPEX_NAME_TO_CODE, f"Generic solar name {name!r} not in mapping"


# ---------------------------------------------------------------------------
# 2. Missing override inherits base value
# ---------------------------------------------------------------------------

class TestMissingOverrideInheritsBase:
    def test_empty_snapshot_returns_original(self):
        base = _make_solar_base()
        assert build_effective_draft_opex(base, {}) is base

    def test_none_snapshot_keys_are_skipped(self):
        base = _make_solar_base()
        result = build_effective_draft_opex(base, {k: None for k in SNAPSHOT_KEY_TO_OPEX_CODE})
        assert result is base

    def test_partial_snapshot_preserves_unmentioned_items(self):
        base = _make_solar_base()
        result = build_effective_draft_opex(base, {"opex_technical_management_y1_keur": 300.0})
        assert result[0].y1_amount_keur == 300.0
        for orig, new in zip(base[1:], result[1:]):
            assert orig.y1_amount_keur == new.y1_amount_keur

    def test_empty_string_snapshot_value_treated_as_missing(self):
        base = _make_solar_base()
        result = build_effective_draft_opex(base, {"opex_insurance_y1_keur": ""})
        assert result is base


# ---------------------------------------------------------------------------
# 3. Explicit zero remains zero
# ---------------------------------------------------------------------------

class TestExplicitZero:
    def test_explicit_zero_float_is_applied(self):
        base = _make_solar_base()
        result = build_effective_draft_opex(base, {"opex_insurance_y1_keur": 0.0})
        ins = next(i for i in result if i.name == "Insurance")
        assert ins.y1_amount_keur == 0.0

    def test_string_zero_is_applied(self):
        base = _make_solar_base()
        result = build_effective_draft_opex(base, {"opex_insurance_y1_keur": "0"})
        ins = next(i for i in result if i.name == "Insurance")
        assert ins.y1_amount_keur == 0.0


# ---------------------------------------------------------------------------
# 4. Edited base line replaces, not duplicates
# ---------------------------------------------------------------------------

class TestEditedLineReplacesNotDuplicates:
    def test_technical_management_200_to_300(self):
        base = _make_solar_base()
        result = build_effective_draft_opex(base, {"opex_technical_management_y1_keur": 300.0})
        assert len(result) == len(base)
        items = [i for i in result if i.name == "Technical Management"]
        assert len(items) == 1
        assert items[0].y1_amount_keur == 300.0

    def test_no_duplicate_items_after_multi_override(self):
        base = _make_solar_base()
        result = build_effective_draft_opex(base, {
            "opex_technical_management_y1_keur": 300.0,
            "opex_insurance_y1_keur": 280.0,
        })
        assert len(result) == len(base)

    def test_inflation_rate_preserved_after_override(self):
        base = _make_solar_base()
        orig = next(i for i in base if i.name == "Technical Management")
        result = build_effective_draft_opex(base, {"opex_technical_management_y1_keur": 350.0})
        new_item = next(i for i in result if i.name == "Technical Management")
        assert new_item.annual_inflation == orig.annual_inflation

    def test_step_changes_preserved_after_override(self):
        """step_changes from the base must survive the y1_amount_keur replacement."""
        step = ((3, 420.0),)
        base = (
            OpexItem("Technical Management", 200.0, 0.02, step_changes=step),
            OpexItem("Contingencies", 0.0, 0.0, percentage_of_opex=0.05),
        )
        result = build_effective_draft_opex(base, {"opex_technical_management_y1_keur": 300.0})
        new_item = next(i for i in result if i.name == "Technical Management")
        assert new_item.y1_amount_keur == 300.0
        assert new_item.step_changes == step


# ---------------------------------------------------------------------------
# 5. Contingency (B.13) remains derived — never overridden
# ---------------------------------------------------------------------------

class TestContingencyDerived:
    def test_b13_only_snapshot_returns_original(self):
        base = _make_solar_base()
        result = build_effective_draft_opex(base, {"opex_contingencies_y1_keur": 9999.0})
        assert result is base

    def test_b13_item_unchanged_even_when_other_lines_override(self):
        base = _make_solar_base()
        result = build_effective_draft_opex(base, {
            "opex_technical_management_y1_keur": 300.0,
            "opex_contingencies_y1_keur": 9999.0,
        })
        cont = next(i for i in result if i.name == "Contingencies")
        orig = next(i for i in base if i.name == "Contingencies")
        assert cont.y1_amount_keur == orig.y1_amount_keur
        assert cont.percentage_of_opex == orig.percentage_of_opex


# ---------------------------------------------------------------------------
# 6. Wind factory name variants route correctly
# ---------------------------------------------------------------------------

class TestWindFactoryVariants:
    def test_om_preventive_and_corrective(self):
        base = _make_wind_base()
        result = build_effective_draft_opex(base, {"opex_o_and_m_preventive_and_corrective_y1_keur": 500.0})
        item = next(i for i in result if i.name == "O&M Preventive & Corrective")
        assert item.y1_amount_keur == 500.0

    def test_bank_fees_opex_variant(self):
        base = _make_wind_base()
        result = build_effective_draft_opex(base, {"opex_bank_fees_opex_y1_keur": 25.0})
        item = next(i for i in result if i.name == "Bank Fees (opex)")
        assert item.y1_amount_keur == 25.0

    def test_environmental_social_management_variant(self):
        base = _make_wind_base()
        result = build_effective_draft_opex(base, {"opex_environmental_and_social_management_y1_keur": 250.0})
        item = next(i for i in result if i.name == "Environmental & Social Management")
        assert item.y1_amount_keur == 250.0

    def test_audit_accounting_legal_wind_spacing(self):
        base = _make_wind_base()
        result = build_effective_draft_opex(base, {"opex_audit_and_accounting_and_legal_y1_keur": 30.0})
        item = next(i for i in result if i.name == "Audit & Accounting & Legal")
        assert item.y1_amount_keur == 30.0

    def test_real_tuho_opex_technical_management_override(self):
        base = _tuho_opex()
        orig = next(i for i in base if i.name == "Technical Management")
        result = build_effective_draft_opex(base, {"opex_technical_management_y1_keur": orig.y1_amount_keur + 100.0})
        new_item = next(i for i in result if i.name == "Technical Management")
        assert new_item.y1_amount_keur == orig.y1_amount_keur + 100.0
        # step_changes preserved
        assert new_item.step_changes == orig.step_changes


# ---------------------------------------------------------------------------
# 7. Unmapped items pass through unchanged
# ---------------------------------------------------------------------------

class TestUnmappedItemsPassThrough:
    def test_taxes_item_unchanged(self):
        base = _make_solar_base()
        result = build_effective_draft_opex(base, {k: 100.0 for k in SNAPSHOT_KEY_TO_OPEX_CODE})
        taxes = next((i for i in result if i.name == "Taxes"), None)
        assert taxes is not None
        assert taxes.y1_amount_keur == 0.0

    def test_salary_payroll_unchanged(self):
        base = _make_solar_base()
        result = build_effective_draft_opex(base, {k: 50.0 for k in SNAPSHOT_KEY_TO_OPEX_CODE})
        salary = next((i for i in result if i.name == "Salary&Payroll"), None)
        assert salary is not None
        assert salary.y1_amount_keur == 0.0


# ---------------------------------------------------------------------------
# 8. has_per_line_overrides
# ---------------------------------------------------------------------------

class TestHasPerLineOverrides:
    def test_empty_snapshot_returns_false(self):
        assert has_per_line_overrides({}) is False

    def test_none_values_return_false(self):
        assert has_per_line_overrides({k: None for k in SNAPSHOT_KEY_TO_OPEX_CODE}) is False

    def test_single_override_returns_true(self):
        assert has_per_line_overrides({"opex_technical_management_y1_keur": 300.0}) is True

    def test_zero_override_returns_true(self):
        assert has_per_line_overrides({"opex_insurance_y1_keur": 0.0}) is True

    def test_unrelated_keys_return_false(self):
        assert has_per_line_overrides({"opex_y1_keur": 700.0, "p50_hours": 2200.0}) is False


# ---------------------------------------------------------------------------
# 9. get_per_line_override_for_group
# ---------------------------------------------------------------------------

class TestGetPerLineOverrideForGroup:
    def test_returns_float_when_present(self):
        val = get_per_line_override_for_group({"opex_insurance_y1_keur": "255.5"}, "B.06")
        assert val == pytest.approx(255.5)

    def test_returns_none_when_absent(self):
        assert get_per_line_override_for_group({}, "B.06") is None

    def test_returns_none_for_b09(self):
        assert get_per_line_override_for_group({"opex_fees_y1_keur": 100.0}, "B.09") is None

    def test_explicit_zero_returned_as_zero(self):
        val = get_per_line_override_for_group({"opex_technical_management_y1_keur": 0.0}, "B.01")
        assert val == 0.0

    def test_empty_string_returns_none(self):
        val = get_per_line_override_for_group({"opex_insurance_y1_keur": ""}, "B.06")
        assert val is None


# ---------------------------------------------------------------------------
# 10. All B.01–B.12 lines override the correct field (solar base)
# ---------------------------------------------------------------------------

class TestPerLineEngineMappingAccuracy:
    @pytest.mark.parametrize("snap_key,solar_name,override_val", [
        ("opex_technical_management_y1_keur",                "Technical Management",     300.0),
        ("opex_o_and_m_preventive_and_corrective_y1_keur",   "Infrastructure Maintenance", 250.0),
        ("opex_maintain_site_y1_keur",                       "Maintain Site",             55.0),
        ("opex_clean_material_y1_keur",                      "Clean Material",            45.0),
        ("opex_security_y1_keur",                            "Security",                  35.0),
        ("opex_insurance_y1_keur",                           "Insurance",                280.0),
        ("opex_lease_and_property_tax_y1_keur",              "Lease & Property Tax",     220.0),
        ("opex_power_expenses_y1_keur",                      "Power Expenses",           190.0),
        ("opex_audit_and_accounting_and_legal_y1_keur",      "Audit&Accounting&Legal",    28.0),
        ("opex_bank_fees_opex_y1_keur",                      "Bank Fees",                 22.0),
        ("opex_environmental_and_social_management_y1_keur", "Environmental&Social",      38.0),
    ])
    def test_snap_key_routes_to_correct_solar_item(self, snap_key, solar_name, override_val):
        base = _make_solar_base()
        result = build_effective_draft_opex(base, {snap_key: override_val})
        matched = next((i for i in result if i.name == solar_name), None)
        assert matched is not None, f"Item {solar_name!r} not found"
        assert matched.y1_amount_keur == pytest.approx(override_val)
        assert len(result) == len(base)

    def test_all_lines_at_once_solar(self):
        base = _make_solar_base()
        snap = {
            "opex_technical_management_y1_keur":                   300.0,
            "opex_o_and_m_preventive_and_corrective_y1_keur":      250.0,
            "opex_maintain_site_y1_keur":                           55.0,
            "opex_clean_material_y1_keur":                          45.0,
            "opex_security_y1_keur":                                35.0,
            "opex_insurance_y1_keur":                              280.0,
            "opex_lease_and_property_tax_y1_keur":                 220.0,
            "opex_power_expenses_y1_keur":                         190.0,
            "opex_audit_and_accounting_and_legal_y1_keur":          28.0,
            "opex_bank_fees_opex_y1_keur":                          22.0,
            "opex_environmental_and_social_management_y1_keur":     38.0,
        }
        result = build_effective_draft_opex(base, snap)
        assert len(result) == len(base)
        assert next(i for i in result if i.name == "Technical Management").y1_amount_keur == 300.0
        assert next(i for i in result if i.name == "Insurance").y1_amount_keur == 280.0
        cont = next(i for i in result if i.name == "Contingencies")
        assert cont.y1_amount_keur == next(i for i in base if i.name == "Contingencies").y1_amount_keur


# ---------------------------------------------------------------------------
# 11. Integration: Technical Management 200 → 300 via real Oborovo base
# ---------------------------------------------------------------------------

class TestIntegrationOborovoTechnicalManagement:
    """End-to-end: edit Technical Management on a real Oborovo OPEX tuple."""

    def test_technical_management_override_persists_in_opex_tuple(self):
        base = _oborovo_opex()
        orig_tm = next(i for i in base if i.name == "Technical Management")
        new_val = orig_tm.y1_amount_keur + 100.0

        result = build_effective_draft_opex(base, {"opex_technical_management_y1_keur": new_val})

        new_tm = next(i for i in result if i.name == "Technical Management")
        assert new_tm.y1_amount_keur == pytest.approx(new_val)

    def test_group_subtotal_reflects_override(self):
        """Sum of all non-contingency items increases by the override delta."""
        base = _oborovo_opex()
        orig_tm = next(i for i in base if i.name == "Technical Management")
        delta = 100.0
        new_val = orig_tm.y1_amount_keur + delta

        result = build_effective_draft_opex(base, {"opex_technical_management_y1_keur": new_val})

        base_total = sum(i.y1_amount_keur for i in base if i.percentage_of_opex == 0.0)
        result_total = sum(i.y1_amount_keur for i in result if i.percentage_of_opex == 0.0)
        assert result_total == pytest.approx(base_total + delta)

    def test_step_changes_from_oborovo_base_are_preserved(self):
        base = _oborovo_opex()
        orig_tm = next(i for i in base if i.name == "Technical Management")
        result = build_effective_draft_opex(base, {"opex_technical_management_y1_keur": 300.0})
        new_tm = next(i for i in result if i.name == "Technical Management")
        assert new_tm.step_changes == orig_tm.step_changes
        assert new_tm.annual_inflation == orig_tm.annual_inflation

    def test_other_lines_unchanged_in_oborovo(self):
        base = _oborovo_opex()
        result = build_effective_draft_opex(base, {"opex_technical_management_y1_keur": 300.0})
        for orig, new in zip(base, result):
            if orig.name == "Technical Management":
                continue
            assert orig.y1_amount_keur == new.y1_amount_keur, \
                f"{orig.name}: expected {orig.y1_amount_keur}, got {new.y1_amount_keur}"


# ---------------------------------------------------------------------------
# 12. Integration: build_projectinputs_from_snapshot applies per-line overrides
# ---------------------------------------------------------------------------

class TestIntegrationBuildProjectInputsFromSnapshot:
    """Verify the full adapter path from snapshot → ProjectInputs.opex."""

    def _minimal_oborovo_snapshot(self, **overrides) -> dict:
        return {
            "template_source": "oborovo",
            "project_type": "Solar",
            "project_name": "Test Solar",
            "country_market": "HR",
            "capacity_mw": 50.0,
            "cod_date": "2026-01-01",
            "construction_months": 12,
            "horizon_years": 20,
            "tariff_eur_mwh": 65.0,
            "ppa_term_years": 20,
            "p50_hours": 1400.0,
            "opex_y1_keur": 1200.0,
            "total_capex_keur": 40000.0,
            "gearing_pct": "",
            "interest_rate_pct": 0.055,
            "tenor_years": 15,
            "target_dscr": 1.20,
            **overrides,
        }

    def test_no_per_line_overrides_returns_base_opex(self):
        from app.input_adapter import build_projectinputs_from_snapshot
        snap = self._minimal_oborovo_snapshot()
        pi = build_projectinputs_from_snapshot(snap)
        # Without overrides, opex is the (scaled) Oborovo base
        assert pi.opex is not None
        assert len(pi.opex) > 0

    def test_technical_management_override_reaches_engine(self):
        from app.input_adapter import build_projectinputs_from_snapshot
        from app.project_factories import create_default_oborovo
        base_tm = next(i for i in create_default_oborovo().opex if i.name == "Technical Management")
        new_val = base_tm.y1_amount_keur + 100.0

        snap = self._minimal_oborovo_snapshot(
            opex_technical_management_y1_keur=new_val,
        )
        pi = build_projectinputs_from_snapshot(snap)
        result_tm = next(i for i in pi.opex if i.name == "Technical Management")
        assert result_tm.y1_amount_keur == pytest.approx(new_val)

    def test_contingency_not_overridden_through_adapter(self):
        from app.input_adapter import build_projectinputs_from_snapshot
        snap = self._minimal_oborovo_snapshot(
            opex_contingencies_y1_keur=99999.0,
            opex_technical_management_y1_keur=300.0,
        )
        pi = build_projectinputs_from_snapshot(snap)
        cont = next((i for i in pi.opex if i.name == "Contingencies"), None)
        if cont is not None:
            assert cont.y1_amount_keur != 99999.0
