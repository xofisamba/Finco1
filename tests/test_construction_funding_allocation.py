import pytest

from domain.construction.config import FundingSourceCaps
from domain.construction.funding_allocation import allocate_source_waterfall


def test_source_waterfall_allocates_equity_shl_junior_then_senior():
    entries = allocate_source_waterfall(
        (60.0, 80.0, 100.0),
        FundingSourceCaps(
            equity_shares_keur=50.0,
            shl_keur=75.0,
            junior_keur=25.0,
            senior_debt_keur=90.0,
        ),
    )

    assert [entry.equity_draw_keur for entry in entries] == pytest.approx((50.0, 0.0, 0.0))
    assert [entry.shl_draw_keur for entry in entries] == pytest.approx((10.0, 65.0, 0.0))
    assert [entry.junior_draw_keur for entry in entries] == pytest.approx((0.0, 15.0, 10.0))
    assert [entry.senior_draw_keur for entry in entries] == pytest.approx((0.0, 0.0, 90.0))
    assert entries[-1].cumulative_senior_keur == pytest.approx(90.0)


def test_waterfall_monthly_funding_equals_monthly_uses():
    monthly_uses = (10.0, 20.0, 30.0)
    entries = allocate_source_waterfall(monthly_uses, FundingSourceCaps(5.0, 25.0, 0.0, 30.0))

    for entry in entries:
        monthly_funding = (
            entry.equity_draw_keur
            + entry.shl_draw_keur
            + entry.junior_draw_keur
            + entry.senior_draw_keur
        )
        assert monthly_funding == pytest.approx(entry.monthly_uses_keur)


def test_source_caps_insufficient_raises_clear_error():
    with pytest.raises(ValueError, match="do not cover"):
        allocate_source_waterfall((100.0,), FundingSourceCaps(10.0, 10.0, 0.0, 10.0))


def test_negative_source_caps_raise_clear_error():
    with pytest.raises(ValueError, match="cannot be negative"):
        allocate_source_waterfall((100.0,), FundingSourceCaps(10.0, -1.0, 0.0, 100.0))


def test_no_negative_draws_and_caps_never_exceeded():
    caps = FundingSourceCaps(50.0, 75.0, 0.0, 125.0)
    entries = allocate_source_waterfall((20.0, 60.0, 70.0, 100.0), caps)

    for entry in entries:
        assert entry.equity_draw_keur >= 0.0
        assert entry.shl_draw_keur >= 0.0
        assert entry.junior_draw_keur >= 0.0
        assert entry.senior_draw_keur >= 0.0
        assert entry.cumulative_equity_keur <= caps.equity_shares_keur
        assert entry.cumulative_shl_keur <= caps.shl_keur
        assert entry.cumulative_senior_keur <= caps.senior_debt_keur
