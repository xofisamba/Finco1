import pytest

from domain.construction import compute_construction_schedule
from domain.construction.templates.tuho import (
    TUHO_MONTHLY_USES_KEUR,
    build_tuho_construction_config,
)


def test_tuho_construction_schedule_bridge_matches_discovery_targets():
    config = build_tuho_construction_config()
    result = compute_construction_schedule(config)

    assert config.construction_months == 18
    assert len(TUHO_MONTHLY_USES_KEUR) == 18
    assert result.total_uses_keur == pytest.approx(72994.450, abs=0.01)
    assert result.total_equity_draw_keur == pytest.approx(500.000, abs=0.001)
    assert result.total_shl_draw_keur == pytest.approx(29135.176, abs=0.001)
    assert result.total_junior_draw_keur == pytest.approx(0.000, abs=0.001)
    assert result.total_senior_draw_keur == pytest.approx(43359.274, abs=0.001)
    assert result.total_shl_idc_keur == pytest.approx(3568.688, abs=0.01)
    assert result.opening_shl_balance_keur == pytest.approx(32703.864, abs=0.01)
    assert result.total_senior_idc_keur == pytest.approx(1519.564, abs=0.01)
    assert result.uses_funding_delta_keur == pytest.approx(0.0, abs=0.01)


def test_tuho_funding_sequence_matches_source_waterfall_discovery():
    result = compute_construction_schedule(build_tuho_construction_config())

    month_1 = result.monthly_entry(1)
    month_2 = result.monthly_entry(2)
    month_3 = result.monthly_entry(3)
    month_4 = result.monthly_entry(4)

    assert month_1.equity_draw_keur == pytest.approx(500.0)
    assert month_1.shl_draw_keur == pytest.approx(23726.729)
    assert month_1.senior_draw_keur == pytest.approx(0.0)
    assert month_2.shl_draw_keur == pytest.approx(2785.808)
    assert month_3.shl_draw_keur == pytest.approx(2622.639, abs=0.001)
    assert month_3.senior_draw_keur == pytest.approx(181.235, abs=0.001)
    assert month_4.shl_draw_keur == pytest.approx(0.0)
    assert month_4.senior_draw_keur == pytest.approx(2804.725, abs=0.001)
