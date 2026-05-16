from datetime import date

import pytest

from domain.construction.config import FundingSourceCaps
from domain.construction.funding_allocation import allocate_source_waterfall
from domain.construction.idc_calculator import (
    compute_full_source_elapsed_compound_idc,
    compute_senior_monthly_cumulative_idc,
)


def test_shl_full_source_elapsed_compound_formula():
    idc = compute_full_source_elapsed_compound_idc(
        source_draw_keur=1000.0,
        annual_rate=0.08,
        investment_date=date(2029, 1, 1),
        cod_date=date(2030, 1, 1),
    )

    assert idc == pytest.approx(80.0)


def test_shl_full_source_elapsed_compound_rejects_bad_dates():
    with pytest.raises(ValueError, match="before investment_date"):
        compute_full_source_elapsed_compound_idc(
            source_draw_keur=1000.0,
            annual_rate=0.08,
            investment_date=date(2029, 1, 1),
            cod_date=date(2028, 1, 1),
        )


def test_senior_monthly_cumulative_idc_formula_uses_prior_balance():
    entries = allocate_source_waterfall((100.0, 100.0, 100.0), FundingSourceCaps(0.0, 0.0, 0.0, 300.0))

    idc = compute_senior_monthly_cumulative_idc(
        entries,
        senior_interest_rate=0.12,
        monthly_interest_period_fractions=(1 / 12, 1 / 12, 1 / 12),
    )

    assert idc == pytest.approx((0.0, 1.0, 2.0))


def test_senior_monthly_cumulative_idc_supports_base_rates():
    entries = allocate_source_waterfall((100.0, 100.0), FundingSourceCaps(0.0, 0.0, 0.0, 200.0))

    idc = compute_senior_monthly_cumulative_idc(
        entries,
        senior_interest_rate=0.12,
        monthly_base_rates=(0.0, 0.12),
        monthly_interest_period_fractions=(1 / 12, 1 / 12),
    )

    assert idc == pytest.approx((0.0, 2.0))


def test_senior_monthly_cumulative_idc_validates_lengths():
    entries = allocate_source_waterfall((100.0, 100.0), FundingSourceCaps(0.0, 0.0, 0.0, 200.0))

    with pytest.raises(ValueError, match="length"):
        compute_senior_monthly_cumulative_idc(
            entries,
            senior_interest_rate=0.12,
            monthly_interest_period_fractions=(1 / 12,),
        )
