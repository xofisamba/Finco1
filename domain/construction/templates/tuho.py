"""TUHO offline construction funding template."""

from __future__ import annotations

from datetime import date

from domain.construction.config import CapexProfileType, ConstructionConfig, FundingSourceCaps


TUHO_MONTHLY_USES_KEUR = (
    24226.729,
    2785.808,
    2803.874,
    2804.725,
    2816.833,
    2831.107,
    2820.167,
    2835.312,
    2848.618,
    2852.397,
    2875.373,
    2884.804,
    2902.406,
    2911.087,
    2929.689,
    2943.438,
    2950.982,
    2971.101,
)


def build_tuho_construction_config() -> ConstructionConfig:
    """Build the TUHO construction bridge template from the Excel discovery."""

    senior_fractions = tuple(1.0 / 12.0 for _ in TUHO_MONTHLY_USES_KEUR)
    return ConstructionConfig(
        project_code="TUHO-WIND-1",
        construction_start_date=date(2028, 6, 30),
        cod_date=date(2029, 12, 30),
        construction_months=18,
        total_uses_keur=72994.450,
        profile_type=CapexProfileType.CUSTOM,
        monthly_uses_keur=TUHO_MONTHLY_USES_KEUR,
        funding_caps=FundingSourceCaps(
            equity_shares_keur=500.000,
            shl_keur=29135.176,
            junior_keur=0.000,
            senior_debt_keur=43359.274,
        ),
        shl_interest_rate=0.08,
        shl_investment_date=date(2028, 6, 30),
        shl_day_count_denominator=365.0,
        # Excel base-rate rows and exact day-count treatment remain unresolved.
        # This effective rate calibrates the monthly cumulative-balance method to
        # the discovered TUHO senior IDC target without changing runtime logic.
        senior_interest_rate=0.060454449320244484,
        senior_interest_period_fractions=senior_fractions,
        senior_idc_target_keur=1519.564,
        senior_idc_notes=(
            "Effective senior construction rate calibrated to Excel IDC!D57 "
            "because base-rate row inputs are not yet modeled."
        ),
    )


__all__ = ["TUHO_MONTHLY_USES_KEUR", "build_tuho_construction_config"]
