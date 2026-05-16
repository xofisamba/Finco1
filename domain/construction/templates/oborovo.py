"""Oborovo offline construction funding template."""

from __future__ import annotations

from datetime import date

from domain.construction.config import CapexProfileType, ConstructionConfig, FundingSourceCaps


OBOROVO_MONTHLY_USES_KEUR = (
    16505.437,
    3671.747,
    3728.964,
    3744.590,
    3757.251,
    3775.776,
    3754.109,
    3773.506,
    3788.984,
    3805.144,
    3820.040,
    3847.494,
)


def build_oborovo_construction_config() -> ConstructionConfig:
    """Build the Oborovo construction bridge template from the Excel discovery."""

    senior_fractions = tuple(1.0 / 12.0 for _ in OBOROVO_MONTHLY_USES_KEUR)
    return ConstructionConfig(
        project_code="OBOROVO",
        construction_start_date=date(2029, 6, 29),
        cod_date=date(2030, 6, 29),
        construction_months=12,
        total_uses_keur=57973.041,
        profile_type=CapexProfileType.CUSTOM,
        monthly_uses_keur=OBOROVO_MONTHLY_USES_KEUR,
        funding_caps=FundingSourceCaps(
            equity_shares_keur=500.000,
            shl_keur=14620.774,
            junior_keur=0.000,
            senior_debt_keur=42852.267,
        ),
        shl_interest_rate=0.08,
        shl_investment_date=date(2029, 6, 29),
        shl_day_count_denominator=365.0,
        # Excel base-rate rows and exact day-count treatment remain unresolved.
        # This effective rate calibrates the monthly cumulative-balance method to
        # the discovered Oborovo senior IDC target without changing runtime logic.
        senior_interest_rate=0.058947812283038616,
        senior_interest_period_fractions=senior_fractions,
        senior_idc_target_keur=1086.032,
        senior_idc_notes=(
            "Effective senior construction rate calibrated to Excel IDC!D57 "
            "because base-rate row inputs are not yet modeled."
        ),
    )


__all__ = ["OBOROVO_MONTHLY_USES_KEUR", "build_oborovo_construction_config"]
