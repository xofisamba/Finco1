from datetime import date

import pytest

from domain.construction.capex_schedule import build_monthly_uses, validate_monthly_uses_total
from domain.construction.config import CapexProfileType, ConstructionConfig, FundingSourceCaps


def config(**kwargs):
    defaults = {
        "project_code": "TEST",
        "construction_start_date": date(2028, 1, 1),
        "cod_date": date(2029, 1, 1),
        "construction_months": 4,
        "total_uses_keur": 400.0,
        "profile_type": CapexProfileType.LINEAR,
        "funding_caps": FundingSourceCaps(100.0, 100.0, 0.0, 200.0),
        "senior_interest_period_fractions": (1 / 12, 1 / 12, 1 / 12, 1 / 12),
    }
    defaults.update(kwargs)
    return ConstructionConfig(**defaults)


def test_linear_schedule_sums_correctly():
    monthly = build_monthly_uses(config())

    assert monthly == pytest.approx((100.0, 100.0, 100.0, 100.0))
    assert sum(monthly) == pytest.approx(400.0)


def test_custom_schedule_length_validation():
    with pytest.raises(ValueError, match="length"):
        build_monthly_uses(
            config(
                profile_type=CapexProfileType.CUSTOM,
                monthly_uses_keur=(100.0, 100.0),
            )
        )


def test_custom_schedule_rejects_negative_uses():
    with pytest.raises(ValueError, match="cannot be negative"):
        build_monthly_uses(
            config(
                profile_type=CapexProfileType.CUSTOM,
                monthly_uses_keur=(100.0, -1.0, 100.0, 201.0),
            )
        )


def test_validate_monthly_uses_total_reports_delta():
    delta = validate_monthly_uses_total((100.0, 200.0), 300.0)

    assert delta == 0.0


def test_validate_monthly_uses_total_raises_when_outside_tolerance():
    with pytest.raises(ValueError, match="Monthly construction uses"):
        validate_monthly_uses_total((100.0, 200.0), 310.0)
