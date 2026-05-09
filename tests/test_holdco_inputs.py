"""Tests for HoldCo inputs — Phase 3A skeleton only.

No cash flow tests. No SHL. No tax template.
"""
from __future__ import annotations

import pytest

from domain.portfolio.holdco import (
    HoldCoInputs,
    HoldCoEntity,
    SPVOwnership,
    HoldCoOpexInputs,
)


class TestSPVOwnership:
    """SPVOwnership dataclass validation."""

    def test_valid_full_ownership(self):
        o = SPVOwnership(spv_code="OBOROVO", ownership_pct=1.0)
        assert o.spv_code == "OBOROVO"
        assert o.ownership_pct == 1.0

    def test_valid_partial_ownership(self):
        o = SPVOwnership(spv_code="TUHO", ownership_pct=0.8)
        assert o.spv_code == "TUHO"
        assert o.ownership_pct == 0.8

    def test_spv_code_required_empty_raises(self):
        with pytest.raises(ValueError, match="spv_code is required"):
            SPVOwnership(spv_code="", ownership_pct=1.0)

    def test_spv_code_required_whitespace_raises(self):
        with pytest.raises(ValueError, match="spv_code is required"):
            SPVOwnership(spv_code="   ", ownership_pct=1.0)

    def test_ownership_pct_zero_raises(self):
        with pytest.raises(ValueError, match="ownership_pct must be in"):
            SPVOwnership(spv_code="OBOROVO", ownership_pct=0.0)

    def test_ownership_pct_negative_raises(self):
        with pytest.raises(ValueError, match="ownership_pct must be in"):
            SPVOwnership(spv_code="OBOROVO", ownership_pct=-0.1)

    def test_ownership_pct_exceeds_one_raises(self):
        with pytest.raises(ValueError, match="ownership_pct must be in"):
            SPVOwnership(spv_code="OBOROVO", ownership_pct=1.1)


class TestHoldCoOpexInputs:
    """HoldCoOpexInputs validation."""

    def test_valid_zero_opex(self):
        o = HoldCoOpexInputs(annual_opex_keur=0.0)
        assert o.annual_opex_keur == 0.0
        assert o.currency == "EUR"

    def test_valid_positive_opex(self):
        o = HoldCoOpexInputs(annual_opex_keur=500.0, currency="USD")
        assert o.annual_opex_keur == 500.0
        assert o.currency == "USD"

    def test_negative_opex_raises(self):
        with pytest.raises(ValueError, match="annual_opex_keur must be >= 0"):
            HoldCoOpexInputs(annual_opex_keur=-10.0)


class TestHoldCoEntity:
    """HoldCoEntity validation."""

    def test_valid_entity(self):
        e = HoldCoEntity(name="HC TopCo", currency="EUR", tax_rate_pa=0.2)
        assert e.name == "HC TopCo"
        assert e.tax_rate_pa == 0.2

    def test_name_required_empty_raises(self):
        with pytest.raises(ValueError, match="HoldCo name is required"):
            HoldCoEntity(name="")

    def test_name_required_whitespace_raises(self):
        with pytest.raises(ValueError, match="HoldCo name is required"):
            HoldCoEntity(name="   ")

    def test_tax_rate_zero_valid(self):
        e = HoldCoEntity(name="HC", tax_rate_pa=0.0)
        assert e.tax_rate_pa == 0.0

    def test_tax_rate_negative_raises(self):
        with pytest.raises(ValueError, match="tax_rate_pa must be in"):
            HoldCoEntity(name="HC", tax_rate_pa=-0.1)

    def test_tax_rate_one_or_above_raises(self):
        with pytest.raises(ValueError, match="tax_rate_pa must be in"):
            HoldCoEntity(name="HC", tax_rate_pa=1.0)


class TestHoldCoInputs:
    """HoldCoInputs validation — full integration tests."""

    def test_valid_single_spv(self):
        inputs = HoldCoInputs(
            name="Test HoldCo",
            ownerships=[SPVOwnership(spv_code="OBOROVO", ownership_pct=1.0)],
        )
        assert inputs.name == "Test HoldCo"
        assert len(inputs.ownerships) == 1
        assert inputs.spv_codes == ["OBOROVO"]
        assert inputs.is_100_percent is True

    def test_valid_multiple_spvs(self):
        inputs = HoldCoInputs(
            name="Multi SPV HoldCo",
            ownerships=[
                SPVOwnership(spv_code="OBOROVO", ownership_pct=1.0),
                SPVOwnership(spv_code="TUHO", ownership_pct=0.9),
                SPVOwnership(spv_code="WIND-X", ownership_pct=0.75),
            ],
        )
        assert inputs.spv_codes == ["OBOROVO", "TUHO", "WIND-X"]
        assert inputs.is_100_percent is False

    def test_name_required_empty_raises(self):
        with pytest.raises(ValueError, match="HoldCoInputs.name is required"):
            HoldCoInputs(name="", ownerships=[SPVOwnership(spv_code="X", ownership_pct=1.0)])

    def test_name_required_whitespace_raises(self):
        with pytest.raises(ValueError, match="HoldCoInputs.name is required"):
            HoldCoInputs(name="   ", ownerships=[SPVOwnership(spv_code="X", ownership_pct=1.0)])

    def test_at_least_one_ownership_required(self):
        with pytest.raises(ValueError, match="at least one SPV ownership row"):
            HoldCoInputs(name="HC", ownerships=[])

    def test_duplicate_spv_code_raises(self):
        with pytest.raises(ValueError, match="Duplicate SPV code"):
            HoldCoInputs(
                name="HC",
                ownerships=[
                    SPVOwnership(spv_code="OBOROVO", ownership_pct=1.0),
                    SPVOwnership(spv_code="OBOROVO", ownership_pct=0.8),
                ],
            )

    def test_ownership_pct_zero_raises(self):
        with pytest.raises(ValueError, match="ownership_pct must be in"):
            SPVOwnership(spv_code="OBOROVO", ownership_pct=0.0)

    def test_ownership_pct_negative_raises(self):
        with pytest.raises(ValueError, match="ownership_pct must be in"):
            SPVOwnership(spv_code="OBOROVO", ownership_pct=-0.1)

    def test_ownership_pct_exceeds_one_raises(self):
        with pytest.raises(ValueError, match="ownership_pct must be in"):
            SPVOwnership(spv_code="OBOROVO", ownership_pct=1.1)

    def test_entity_auto_created_from_name(self):
        inputs = HoldCoInputs(
            name="Auto Entity HC",
            ownerships=[SPVOwnership(spv_code="X", ownership_pct=1.0)],
        )
        assert inputs.entity is not None
        assert inputs.entity.name == "Auto Entity HC"

    def test_entity_can_be_provided_explicitly(self):
        entity = HoldCoEntity(name="Explicit HC", tax_rate_pa=0.2)
        inputs = HoldCoInputs(
            name="Override Name",
            ownerships=[SPVOwnership(spv_code="X", ownership_pct=1.0)],
            entity=entity,
        )
        # Note: HoldCoInputs.__post_init__ creates default entity if None,
        # but we passed an explicit entity — name from HoldCoInputs takes precedence
        # entity name is stored separately
        assert inputs.entity is entity

    def test_spv_codes_property(self):
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[
                SPVOwnership(spv_code="A", ownership_pct=1.0),
                SPVOwnership(spv_code="B", ownership_pct=0.8),
            ],
        )
        assert inputs.spv_codes == ["A", "B"]

    def test_is_100_percent_true(self):
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[
                SPVOwnership(spv_code="A", ownership_pct=1.0),
                SPVOwnership(spv_code="B", ownership_pct=1.0),
            ],
        )
        assert inputs.is_100_percent is True

    def test_is_100_percent_false(self):
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[
                SPVOwnership(spv_code="A", ownership_pct=1.0),
                SPVOwnership(spv_code="B", ownership_pct=0.8),
            ],
        )
        assert inputs.is_100_percent is False

    def test_horizon_years_default(self):
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="X", ownership_pct=1.0)],
        )
        assert inputs.horizon_years == 25

    def test_horizon_years_custom(self):
        inputs = HoldCoInputs(
            name="HC",
            ownerships=[SPVOwnership(spv_code="X", ownership_pct=1.0)],
            horizon_years=20,
        )
        assert inputs.horizon_years == 20