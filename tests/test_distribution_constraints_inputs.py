"""Phase 5D.1 tests for distribution constraint inputs."""
from __future__ import annotations

import pytest

from domain.portfolio.distribution_constraints.inputs import (
    DistributionBlockReason,
    DistributionConstraintConfig,
)


class TestDistributionBlockReason:
    def test_all_values_present(self):
        expected = {
            "NONE", "NEGATIVE_CASH", "MINIMUM_CASH_RESERVE",
            "DSRF_REPAYMENT", "SHL_PRINCIPAL_REPAYMENT",
            "HOLDCO_RESTRICTION", "TAX_RESTRICTION",
            "MANUAL_LOCKUP", "OTHER",
        }
        assert set(e.value for e in DistributionBlockReason) == expected

    def test_is_string_enum(self):
        assert isinstance(DistributionBlockReason.NONE, str)


class TestDistributionConstraintConfig:
    def test_defaults_are_disabled(self):
        cfg = DistributionConstraintConfig()
        assert cfg.enabled is False
        assert cfg.minimum_cash_reserve_keur == 0.0
        assert cfg.allow_negative_cash is False
        assert cfg.manual_lockup_periods == ()

    def test_valid_config_with_all_fields(self):
        cfg = DistributionConstraintConfig(
            enabled=True,
            minimum_cash_reserve_keur=100.0,
            allow_negative_cash=True,
            manual_lockup_periods=(0, 3, 5),
        )
        assert cfg.enabled is True
        assert cfg.minimum_cash_reserve_keur == 100.0
        assert cfg.allow_negative_cash is True
        assert cfg.manual_lockup_periods == (0, 3, 5)

    def test_negative_minimum_reserve_rejected(self):
        with pytest.raises(ValueError, match="minimum_cash_reserve_keur must be >= 0"):
            DistributionConstraintConfig(minimum_cash_reserve_keur=-10.0)

    def test_negative_lockup_period_rejected(self):
        with pytest.raises(ValueError, match="manual_lockup_periods must all be >= 0"):
            DistributionConstraintConfig(manual_lockup_periods=(0, -1, 2))

    def test_zero_minimum_reserve_allowed(self):
        cfg = DistributionConstraintConfig(minimum_cash_reserve_keur=0.0)
        assert cfg.minimum_cash_reserve_keur == 0.0

    def test_empty_lockup_allowed(self):
        cfg = DistributionConstraintConfig(manual_lockup_periods=())
        assert cfg.manual_lockup_periods == ()

    def test_single_lockup_period_allowed(self):
        cfg = DistributionConstraintConfig(manual_lockup_periods=(0,))
        assert cfg.manual_lockup_periods == (0,)