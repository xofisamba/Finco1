import pytest

from domain.construction import compute_construction_schedule
from domain.construction.templates.oborovo import (
    OBOROVO_MONTHLY_USES_KEUR,
    build_oborovo_construction_config,
)


def test_oborovo_construction_schedule_bridge_matches_discovery_targets():
    config = build_oborovo_construction_config()
    result = compute_construction_schedule(config)

    assert config.construction_months == 12
    assert len(OBOROVO_MONTHLY_USES_KEUR) == 12
    assert result.total_uses_keur == pytest.approx(57973.041, abs=0.01)
    assert result.total_equity_draw_keur == pytest.approx(500.000, abs=0.001)
    assert result.total_shl_draw_keur == pytest.approx(14620.774, abs=0.001)
    assert result.total_junior_draw_keur == pytest.approx(0.000, abs=0.001)
    assert result.total_senior_draw_keur == pytest.approx(42852.267, abs=0.001)
    assert result.total_shl_idc_keur == pytest.approx(1169.662, abs=0.01)
    assert result.opening_shl_balance_keur == pytest.approx(15790.436, abs=0.01)
    assert result.total_senior_idc_keur == pytest.approx(1086.032, abs=0.01)
    assert result.uses_funding_delta_keur == pytest.approx(0.0, abs=0.01)


def test_oborovo_funding_sequence_matches_source_waterfall_discovery():
    result = compute_construction_schedule(build_oborovo_construction_config())

    month_1 = result.monthly_entry(1)
    month_2 = result.monthly_entry(2)

    assert month_1.equity_draw_keur == pytest.approx(500.0)
    assert month_1.shl_draw_keur == pytest.approx(14620.774)
    assert month_1.senior_draw_keur == pytest.approx(1384.663, abs=0.001)
    assert month_2.shl_draw_keur == pytest.approx(0.0)
    assert month_2.senior_draw_keur == pytest.approx(3671.747, abs=0.001)
