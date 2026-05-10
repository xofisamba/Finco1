"""Tests for Phase 5A cash ledger inputs."""
from __future__ import annotations

import pytest

from domain.portfolio.cash_ledger.inputs import (
    CashMovementType,
    CashMovement,
)


class TestCashMovementType:
    def test_all_required_values_present(self):
        required = {
            "OPENING_CASH",
            "OPERATING_CASHFLOW",
            "SENIOR_DEBT_SERVICE",
            "TAX",
            "DSRF_DRAW",
            "DSRF_REPAYMENT",
            "DSRF_INTEREST",
            "DSRF_COMMITMENT_FEE",
            "SHL_INTEREST",
            "SHL_PRINCIPAL",
            "EQUITY_DISTRIBUTION",
            "HOLDCO_OPEX",
            "HOLDCO_TAX",
            "SPONSOR_DISTRIBUTION",
            "RETAINED_CASH",
            "OTHER",
        }
        actual = {m.value for m in CashMovementType}
        assert required == actual, f"Missing values: {required - actual}"


class TestCashMovement:
    def test_valid_movement_positive_amount(self):
        m = CashMovement(
            period=0,
            entity_code="SOLAR-1",
            movement_type=CashMovementType.EQUITY_DISTRIBUTION,
            amount_keur=1000.0,
            description="Test distribution",
        )
        assert m.period == 0
        assert m.entity_code == "SOLAR-1"
        assert m.amount_keur == 1000.0
        assert m.description == "Test distribution"

    def test_valid_movement_negative_amount(self):
        m = CashMovement(
            period=1,
            entity_code="HOLDCO",
            movement_type=CashMovementType.SPONSOR_DISTRIBUTION,
            amount_keur=-500.0,
        )
        assert m.amount_keur == -500.0

    def test_valid_movement_zero_amount(self):
        m = CashMovement(
            period=0,
            entity_code="SOLAR-1",
            movement_type=CashMovementType.RETAINED_CASH,
            amount_keur=0.0,
        )
        assert m.amount_keur == 0.0

    def test_period_negative_rejected(self):
        with pytest.raises(ValueError, match="period must be >= 0"):
            CashMovement(
                period=-1,
                entity_code="SOLAR-1",
                movement_type=CashMovementType.OTHER,
                amount_keur=100.0,
            )

    def test_empty_entity_code_rejected(self):
        with pytest.raises(ValueError, match="entity_code is required"):
            CashMovement(
                period=0,
                entity_code="",
                movement_type=CashMovementType.OTHER,
                amount_keur=100.0,
            )

    def test_whitespace_entity_code_rejected(self):
        with pytest.raises(ValueError, match="entity_code is required"):
            CashMovement(
                period=0,
                entity_code="   ",
                movement_type=CashMovementType.OTHER,
                amount_keur=100.0,
            )

    def test_movement_type_is_required(self):
        m = CashMovement(
            period=0,
            entity_code="SOLAR-1",
            movement_type=CashMovementType.OPENING_CASH,
            amount_keur=100.0,
        )
        assert isinstance(m.movement_type, CashMovementType)

    def test_movement_type_none_rejected(self):
        with pytest.raises(ValueError, match="movement_type must be a CashMovementType"):
            CashMovement(
                period=0,
                entity_code="SOLAR-1",
                movement_type=None,  # type: ignore
                amount_keur=100.0,
            )

    def test_movement_type_string_rejected(self):
        with pytest.raises(ValueError, match="movement_type must be a CashMovementType"):
            CashMovement(
                period=0,
                entity_code="SOLAR-1",
                movement_type="OPERATING_CASHFLOW",  # type: ignore
                amount_keur=100.0,
            )

    def test_movement_type_bool_rejected(self):
        with pytest.raises(ValueError, match="movement_type must be a CashMovementType"):
            CashMovement(
                period=0,
                entity_code="SOLAR-1",
                movement_type=True,  # type: ignore
                amount_keur=100.0,
            )
