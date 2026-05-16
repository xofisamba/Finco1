from dataclasses import replace
from pathlib import Path

import pytest

from app.project_factories import (
    create_default_oborovo,
    create_default_solar_project,
    create_default_tuho_wind1,
)
from domain.construction.runtime_adapter import build_runtime_construction_schedule


def test_runtime_adapter_does_not_import_waterfall():
    source = Path("domain/construction/runtime_adapter.py").read_text(encoding="utf-8")

    assert "domain.waterfall" not in source


def test_tuho_runtime_adapter_matches_construction_bridge_targets():
    result = build_runtime_construction_schedule(create_default_tuho_wind1())

    assert result.project_code == "TUHO-WIND-1"
    assert result.construction_months == 18
    assert result.total_uses_keur == pytest.approx(72994.450, abs=0.01)
    assert result.equity_draw_keur == pytest.approx(500.000, abs=0.001)
    assert result.shl_principal_draw_keur == pytest.approx(29135.176, abs=0.001)
    assert result.junior_draw_keur == pytest.approx(0.000, abs=0.001)
    assert result.senior_principal_draw_keur == pytest.approx(43359.274, abs=0.001)
    assert result.shl_idc_keur == pytest.approx(3568.688, abs=0.01)
    assert result.opening_shl_balance_keur == pytest.approx(32703.864, abs=0.01)
    assert result.senior_idc_keur == pytest.approx(1519.564, abs=0.01)
    assert result.uses_funding_delta_keur == pytest.approx(0.0, abs=0.01)
    assert "diagnostic_only" in " ".join(result.validation_notes)


def test_oborovo_runtime_adapter_matches_construction_bridge_targets():
    result = build_runtime_construction_schedule(create_default_oborovo())

    assert result.project_code == "OBR-001"
    assert result.construction_months == 12
    assert result.total_uses_keur == pytest.approx(57973.041, abs=0.01)
    assert result.equity_draw_keur == pytest.approx(500.000, abs=0.001)
    assert result.shl_principal_draw_keur == pytest.approx(14620.774, abs=0.001)
    assert result.junior_draw_keur == pytest.approx(0.000, abs=0.001)
    assert result.senior_principal_draw_keur == pytest.approx(42852.267, abs=0.001)
    assert result.shl_idc_keur == pytest.approx(1169.662, abs=0.01)
    assert result.opening_shl_balance_keur == pytest.approx(15790.436, abs=0.01)
    assert result.senior_idc_keur == pytest.approx(1086.032, abs=0.01)
    assert result.uses_funding_delta_keur == pytest.approx(0.0, abs=0.01)
    assert any("shl_idc_keur differs" in note for note in result.validation_notes)


def test_runtime_adapter_rejects_unsupported_project():
    project = replace(
        create_default_solar_project(),
        info=replace(create_default_solar_project().info, use_construction_schedule_engine=True),
    )

    with pytest.raises(ValueError, match="only supported"):
        build_runtime_construction_schedule(project)
