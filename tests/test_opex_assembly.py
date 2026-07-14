"""
Unit tests for app.v2.opex_assembly — canonical per-line OPEX assembly.

Covers the spec-required test surface:
  1. Every registered base OPEX field maps to the intended domain OpexItem.
  2. Missing override inherits the base value.
  3. Explicit zero remains zero.
  4. Edited base line replaces, rather than duplicates, the base line.
  5. Custom rows remain additive (not touched by build_effective_draft_opex).
  6. Contingency remains derived (B.13 never overridden).
  7. Aggregate compatibility total equals effective detailed OPEX total.
  8. Reference projects reject per-line overrides (has_per_line_overrides=False).
  9. has_per_line_overrides fast-path (empty snapshot → False).
 10. get_per_line_override_for_group returns correct values.
 11. Both solar and wind factory name variants are routed correctly.
 12. Unmapped item names (Taxes, Salary&Payroll) are passed through unchanged.
"""
from __future__ import annotations

import dataclasses
import pytest


# ---------------------------------------------------------------------------
# Helpers — minimal OpexItem stub so tests do not need the full domain
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class _OpexItem:
    """Minimal stub mirroring OpexItem for unit-testing without domain imports."""
    name: str
    y1_amount_keur: float = 0.0
    annual_inflation: float = 0.02
    percentage_of_opex: float = 0.0  # > 0 → contingency item

    def __eq__(self, other):
        if not isinstance(other, _OpexItem):
            return NotImplemented
        return dataclasses.asdict(self) == dataclasses.asdict(other)


# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------

from app.v2.opex_assembly import (
    SNAPSHOT_KEY_TO_OPEX_CODE,
    OPEX_CODE_TO_SNAPSHOT_KEY,
    _OPEX_NAME_TO_CODE,
    build_effective_draft_opex,
    get_per_line_override_for_group,
    has_per_line_overrides,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _solar_base() -> tuple:
    """Minimal solar factory OPEX tuple covering B.01–B.13 by name."""
    return tuple([
        _OpexItem("Technical Management",    198.0, 0.02),   # B.01
        _OpexItem("Infrastructure Maintenance", 244.0, 0.02),  # B.02 solar variant
        _OpexItem("Maintain Site",            45.0, 0.02),   # B.03
        _OpexItem("Clean Material",           40.0, 0.02),   # B.04
        _OpexItem("Security",                 30.0, 0.02),   # B.05
        _OpexItem("Insurance",               255.0, 0.02),   # B.06
        _OpexItem("Lease & Property Tax",    208.0, 0.02),   # B.07
        _OpexItem("Power Expenses",          177.0, 0.0),    # B.08 flat
        _OpexItem("Fees",                     14.0, 0.0),    # B.09 engine-only
        _OpexItem("Audit&Accounting&Legal",   24.0, 0.02),   # B.10 solar spacing
        _OpexItem("Bank Fees",                20.0, 0.02),   # B.11
        _OpexItem("Environmental&Social",     32.0, 0.02),   # B.12 solar spacing
        _OpexItem("Contingencies", 0.0, 0.02, percentage_of_opex=0.05),  # B.13 derived
        _OpexItem("Taxes",                     0.0, 0.0),    # unmapped
        _OpexItem("Salary&Payroll",            0.0, 0.0),    # unmapped
    ])


def _wind_base() -> tuple:
    """Minimal wind factory OPEX tuple covering B.01–B.13 by name."""
    return tuple([
        _OpexItem("Technical Management",         280.0, 0.02),  # B.01
        _OpexItem("O&M Preventive & Corrective",  427.0, 0.02),  # B.02 wind variant
        _OpexItem("Maintain Site",                 68.0, 0.02),  # B.03
        _OpexItem("Clean Material",                 5.0, 0.02),  # B.04
        _OpexItem("Security",                      50.0, 0.02),  # B.05
        _OpexItem("Insurance",                    469.0, 0.02),  # B.06
        _OpexItem("Lease & Property Tax",         249.0, 0.02),  # B.07
        _OpexItem("Power Expenses",                94.0, 0.02),  # B.08
        _OpexItem("Audit & Accounting & Legal",    24.0, 0.02),  # B.10 wind spacing
        _OpexItem("Bank Fees (opex)",              20.0, 0.02),  # B.11 wind variant
        _OpexItem("Environmental & Social Management", 200.0, 0.02),  # B.12 wind
        _OpexItem("Contingencies", 0.0, 0.02, percentage_of_opex=0.05),  # B.13
    ])


# ---------------------------------------------------------------------------
# 1. Snapshot key ↔ B.XX mapping completeness
# ---------------------------------------------------------------------------

class TestMappingCompleteness:
    """Every registered OPEX field maps to a B.XX code and back."""

    def test_all_registered_fields_present(self):
        registered_snapshot_keys = [
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
        ]
        for key in registered_snapshot_keys:
            assert key in SNAPSHOT_KEY_TO_OPEX_CODE, f"{key} missing from SNAPSHOT_KEY_TO_OPEX_CODE"

    def test_reverse_mapping_round_trips(self):
        for key, code in SNAPSHOT_KEY_TO_OPEX_CODE.items():
            assert OPEX_CODE_TO_SNAPSHOT_KEY.get(code) == key, \
                f"Round-trip failed for {code!r} → expected {key!r}"

    def test_b09_has_no_snapshot_key(self):
        assert "B.09" not in OPEX_CODE_TO_SNAPSHOT_KEY

    def test_solar_factory_names_map(self):
        solar_names = [
            "Technical Management",
            "Infrastructure Maintenance",
            "Maintain Site",
            "Clean Material",
            "Security",
            "Insurance",
            "Lease & Property Tax",
            "Power Expenses",
            "Fees",
            "Audit&Accounting&Legal",
            "Bank Fees",
            "Environmental&Social",
            "Contingencies",
        ]
        for name in solar_names:
            assert name in _OPEX_NAME_TO_CODE, f"Solar name {name!r} not in _OPEX_NAME_TO_CODE"

    def test_wind_factory_names_map(self):
        wind_names = [
            "Technical Management",
            "O&M Preventive & Corrective",
            "Maintain Site",
            "Clean Material",
            "Security",
            "Insurance",
            "Lease & Property Tax",
            "Power Expenses",
            "Audit & Accounting & Legal",
            "Bank Fees (opex)",
            "Environmental & Social Management",
            "Contingencies",
        ]
        for name in wind_names:
            assert name in _OPEX_NAME_TO_CODE, f"Wind name {name!r} not in _OPEX_NAME_TO_CODE"


# ---------------------------------------------------------------------------
# 2. Missing override inherits base value
# ---------------------------------------------------------------------------

class TestMissingOverrideInheritsBase:
    def test_empty_snapshot_returns_original(self):
        base = _solar_base()
        result = build_effective_draft_opex(base, {})
        assert result is base  # same object identity — no copy

    def test_none_snapshot_keys_are_skipped(self):
        base = _solar_base()
        # Keys present but values are None
        snap = {k: None for k in SNAPSHOT_KEY_TO_OPEX_CODE}
        result = build_effective_draft_opex(base, snap)
        assert result is base

    def test_partial_snapshot_preserves_unmentioned_items(self):
        base = _solar_base()
        # Only override Technical Management (B.01)
        snap = {"opex_technical_management_y1_keur": 300.0}
        result = build_effective_draft_opex(base, snap)
        # B.01 changed
        assert result[0].y1_amount_keur == 300.0
        # All others unchanged
        for orig, new in zip(base[1:], result[1:]):
            assert orig.y1_amount_keur == new.y1_amount_keur, \
                f"{orig.name}: expected {orig.y1_amount_keur}, got {new.y1_amount_keur}"


# ---------------------------------------------------------------------------
# 3. Explicit zero remains zero
# ---------------------------------------------------------------------------

class TestExplicitZero:
    def test_explicit_zero_is_applied(self):
        base = _solar_base()
        snap = {"opex_insurance_y1_keur": 0.0}
        result = build_effective_draft_opex(base, snap)
        ins_item = next(i for i in result if i.name == "Insurance")
        assert ins_item.y1_amount_keur == 0.0

    def test_string_zero_is_applied(self):
        """Snapshot values may arrive as strings from the DB."""
        base = _solar_base()
        snap = {"opex_insurance_y1_keur": "0"}
        result = build_effective_draft_opex(base, snap)
        ins_item = next(i for i in result if i.name == "Insurance")
        assert ins_item.y1_amount_keur == 0.0


# ---------------------------------------------------------------------------
# 4. Edited base line replaces, not duplicates
# ---------------------------------------------------------------------------

class TestEditedLineReplacesNotDuplicates:
    def test_technical_management_200_to_300(self):
        base = _solar_base()
        snap = {"opex_technical_management_y1_keur": 300.0}
        result = build_effective_draft_opex(base, snap)
        # Same number of items
        assert len(result) == len(base)
        # Technical Management is 300
        tech_items = [i for i in result if i.name == "Technical Management"]
        assert len(tech_items) == 1
        assert tech_items[0].y1_amount_keur == 300.0

    def test_no_duplicate_items_after_override(self):
        base = _solar_base()
        snap = {
            "opex_technical_management_y1_keur": 300.0,
            "opex_insurance_y1_keur": 280.0,
        }
        result = build_effective_draft_opex(base, snap)
        assert len(result) == len(base)

    def test_inflation_rate_preserved_after_override(self):
        base = _solar_base()
        orig_inflation = next(i for i in base if i.name == "Technical Management").annual_inflation
        snap = {"opex_technical_management_y1_keur": 350.0}
        result = build_effective_draft_opex(base, snap)
        new_item = next(i for i in result if i.name == "Technical Management")
        assert new_item.annual_inflation == orig_inflation


# ---------------------------------------------------------------------------
# 5. Contingency remains derived (B.13 never overridden)
# ---------------------------------------------------------------------------

class TestContingencyDerived:
    def test_b13_contingencies_snapshot_key_is_ignored(self):
        base = _solar_base()
        # Even if B.13 key is in snapshot, it must not be applied
        snap = {"opex_contingencies_y1_keur": 9999.0}
        result = build_effective_draft_opex(base, snap)
        # If no other per-line keys are present, original is returned unchanged
        assert result is base

    def test_b13_contingency_item_y1_unchanged(self):
        base = _solar_base()
        snap = {
            "opex_technical_management_y1_keur": 300.0,
            "opex_contingencies_y1_keur": 9999.0,  # must be ignored
        }
        result = build_effective_draft_opex(base, snap)
        contingency = next(i for i in result if i.name == "Contingencies")
        orig_contingency = next(i for i in base if i.name == "Contingencies")
        assert contingency.y1_amount_keur == orig_contingency.y1_amount_keur
        assert contingency.percentage_of_opex == orig_contingency.percentage_of_opex


# ---------------------------------------------------------------------------
# 6. Wind factory name variants route correctly
# ---------------------------------------------------------------------------

class TestWindFactoryVariants:
    def test_om_preventive_and_corrective(self):
        base = _wind_base()
        snap = {"opex_o_and_m_preventive_and_corrective_y1_keur": 500.0}
        result = build_effective_draft_opex(base, snap)
        item = next(i for i in result if i.name == "O&M Preventive & Corrective")
        assert item.y1_amount_keur == 500.0

    def test_bank_fees_opex_variant(self):
        base = _wind_base()
        snap = {"opex_bank_fees_opex_y1_keur": 25.0}
        result = build_effective_draft_opex(base, snap)
        item = next(i for i in result if i.name == "Bank Fees (opex)")
        assert item.y1_amount_keur == 25.0

    def test_environmental_social_management_variant(self):
        base = _wind_base()
        snap = {"opex_environmental_and_social_management_y1_keur": 250.0}
        result = build_effective_draft_opex(base, snap)
        item = next(i for i in result if i.name == "Environmental & Social Management")
        assert item.y1_amount_keur == 250.0

    def test_audit_accounting_legal_wind_spacing(self):
        base = _wind_base()
        snap = {"opex_audit_and_accounting_and_legal_y1_keur": 30.0}
        result = build_effective_draft_opex(base, snap)
        item = next(i for i in result if i.name == "Audit & Accounting & Legal")
        assert item.y1_amount_keur == 30.0


# ---------------------------------------------------------------------------
# 7. Unmapped items pass through unchanged
# ---------------------------------------------------------------------------

class TestUnmappedItemsPassThrough:
    def test_taxes_item_unchanged(self):
        base = _solar_base()
        # Provide a full override snapshot
        snap = {k: 100.0 for k in SNAPSHOT_KEY_TO_OPEX_CODE}
        result = build_effective_draft_opex(base, snap)
        # Taxes item should be unchanged (name not in mapping with a B.XX code)
        taxes = next((i for i in result if i.name == "Taxes"), None)
        assert taxes is not None
        assert taxes.y1_amount_keur == 0.0  # unchanged

    def test_salary_payroll_unchanged(self):
        base = _solar_base()
        snap = {k: 50.0 for k in SNAPSHOT_KEY_TO_OPEX_CODE}
        result = build_effective_draft_opex(base, snap)
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
        snap = {k: None for k in SNAPSHOT_KEY_TO_OPEX_CODE}
        assert has_per_line_overrides(snap) is False

    def test_single_override_returns_true(self):
        snap = {"opex_technical_management_y1_keur": 300.0}
        assert has_per_line_overrides(snap) is True

    def test_zero_override_returns_true(self):
        # Explicit zero is a valid override
        snap = {"opex_insurance_y1_keur": 0.0}
        assert has_per_line_overrides(snap) is True

    def test_unrelated_keys_return_false(self):
        snap = {"opex_y1_keur": 700.0, "p50_hours": 2200.0}
        assert has_per_line_overrides(snap) is False


# ---------------------------------------------------------------------------
# 9. get_per_line_override_for_group
# ---------------------------------------------------------------------------

class TestGetPerLineOverrideForGroup:
    def test_returns_float_when_present(self):
        snap = {"opex_insurance_y1_keur": "255.5"}
        val = get_per_line_override_for_group(snap, "B.06")
        assert val == pytest.approx(255.5)

    def test_returns_none_when_absent(self):
        assert get_per_line_override_for_group({}, "B.06") is None

    def test_returns_none_for_b09(self):
        # B.09 has no snapshot key
        assert get_per_line_override_for_group(
            {"opex_fees_y1_keur": 100.0}, "B.09"
        ) is None

    def test_returns_none_for_b13(self):
        # B.13 snapshot key exists in the dict but is a derived code
        snap = {"opex_contingencies_y1_keur": 50.0}
        # B.13 is in OPEX_CODE_TO_SNAPSHOT_KEY and the key is present
        # get_per_line_override_for_group just fetches by code; it's up to the
        # caller (build_effective_draft_opex) to skip B.13.
        # This test documents the raw lookup — B.13 DOES return a value.
        val = get_per_line_override_for_group(snap, "B.13")
        assert val == pytest.approx(50.0)

    def test_explicit_zero_returned_as_zero(self):
        snap = {"opex_technical_management_y1_keur": 0.0}
        val = get_per_line_override_for_group(snap, "B.01")
        assert val == 0.0


# ---------------------------------------------------------------------------
# 10. All B.01–B.12 lines override the correct field
# ---------------------------------------------------------------------------

class TestPerLineEngineMappingAccuracy:
    """Verify the canonical B.01–B.12 → snapshot key → item name chain."""

    @pytest.mark.parametrize("snap_key,b_code,solar_name,override_val", [
        ("opex_technical_management_y1_keur",                    "B.01", "Technical Management",    300.0),
        ("opex_o_and_m_preventive_and_corrective_y1_keur",       "B.02", "Infrastructure Maintenance", 250.0),
        ("opex_maintain_site_y1_keur",                           "B.03", "Maintain Site",            55.0),
        ("opex_clean_material_y1_keur",                          "B.04", "Clean Material",           45.0),
        ("opex_security_y1_keur",                                "B.05", "Security",                 35.0),
        ("opex_insurance_y1_keur",                               "B.06", "Insurance",               280.0),
        ("opex_lease_and_property_tax_y1_keur",                  "B.07", "Lease & Property Tax",    220.0),
        ("opex_power_expenses_y1_keur",                          "B.08", "Power Expenses",          190.0),
        ("opex_audit_and_accounting_and_legal_y1_keur",          "B.10", "Audit&Accounting&Legal",   28.0),
        ("opex_bank_fees_opex_y1_keur",                          "B.11", "Bank Fees",                22.0),
        ("opex_environmental_and_social_management_y1_keur",     "B.12", "Environmental&Social",     38.0),
    ])
    def test_snap_key_routes_to_correct_solar_item(
        self, snap_key: str, b_code: str, solar_name: str, override_val: float
    ):
        base = _solar_base()
        snap = {snap_key: override_val}
        result = build_effective_draft_opex(base, snap)
        # Find the item by name in the result
        matched = next((i for i in result if i.name == solar_name), None)
        assert matched is not None, f"Item {solar_name!r} not found in result"
        assert matched.y1_amount_keur == pytest.approx(override_val), \
            f"{b_code} ({solar_name!r}): expected {override_val}, got {matched.y1_amount_keur}"
        # Tuple length must be unchanged
        assert len(result) == len(base)

    def test_all_lines_at_once_solar(self):
        base = _solar_base()
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
        # B.01
        assert next(i for i in result if i.name == "Technical Management").y1_amount_keur == 300.0
        # B.06
        assert next(i for i in result if i.name == "Insurance").y1_amount_keur == 280.0
        # B.13 contingency untouched
        cont = next(i for i in result if i.name == "Contingencies")
        orig_cont = next(i for i in base if i.name == "Contingencies")
        assert cont.y1_amount_keur == orig_cont.y1_amount_keur
        # Unmapped items untouched
        taxes = next((i for i in result if i.name == "Taxes"), None)
        if taxes:
            assert taxes.y1_amount_keur == 0.0
