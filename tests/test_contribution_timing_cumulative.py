"""Verify contribution_timing cumulative fraction semantics directly.

Asserts that LP 8000 × (0.50, 1.00, 1.00) = (4000, 8000, 8000)
and GP 2000 × (1.00, 1.00, 1.00) = (2000, 2000, 2000).
"""
from app.sponsor_runner import SponsorRunConfig, _build_investor_registry, _build_contributions


def test_contribution_timing_cumulative_fractions():
    config = SponsorRunConfig(
        ownership_percentages={"LP-1": 0.80, "GP-1": 0.20},
        committed_capital_keur={"LP-1": 8000.0, "GP-1": 2000.0},
        hurdle_rate_pa=0.08,
        compounding_convention="SEMIANNUAL",
        gp_promote_share=0.20,
        available_cash_by_period=(1000.0, 1000.0, 1000.0),
        num_periods=3,
        contribution_timing=(
            ("LP-1", (0.50, 1.00, 1.00)),
            ("GP-1", (1.00, 1.00, 1.00)),
        ),
    )
    registry = _build_investor_registry(config)
    contributions = _build_contributions(config, registry)

    assert contributions["LP-1"] == (4000.0, 8000.0, 8000.0)
    assert contributions["GP-1"] == (2000.0, 2000.0, 2000.0)