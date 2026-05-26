from __future__ import annotations

import os
import sys

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.project_runner import run_project
from app.input_adapter import SnapshotInputError, build_projectinputs_from_snapshot


def _snapshot(**overrides):
    data = {
        "active_project": "pilot-wind",
        "project_name": "Pilot Wind",
        "project_type": "Wind",
        "project_origin": "user_created",
        "template_source": "generic_wind",
        "country_market": "Croatia",
        "capacity_mw": "50",
        "cod_date": "2027-01-01",
        "construction_months": "12",
        "horizon_years": "25",
        "tariff_eur_mwh": "60",
        "ppa_term_years": "15",
        "p50_hours": "1200",
        "opex_y1_keur": "1000",
        "total_capex_keur": "50000",
        "gearing_pct": "70",
        "interest_rate_pct": "5",
        "tenor_years": "15",
        "target_dscr": "1.30",
    }
    data.update(overrides)
    return data


def _run(snapshot):
    project_type = "Solar" if snapshot["project_type"] == "Solar" else "Wind"
    return run_project(project_type, "Base", project_inputs_override=build_projectinputs_from_snapshot(snapshot))


def test_builder_exists_and_rejects_missing_required_fields():
    with pytest.raises(SnapshotInputError, match="tariff_eur_mwh"):
        build_projectinputs_from_snapshot(_snapshot(tariff_eur_mwh=""))


def test_builder_converts_and_maps_saved_snapshot_fields():
    project_inputs = build_projectinputs_from_snapshot(_snapshot())

    assert project_inputs.info.name == "Pilot Wind"
    assert project_inputs.info.code == "PILOT-WIND"
    assert project_inputs.info.country_iso == "HR"
    assert project_inputs.info.horizon_years == 25
    assert project_inputs.info.construction_months == 12
    assert project_inputs.technical.capacity_mw == 50
    assert project_inputs.technical.operating_hours_p50 == 1200
    assert project_inputs.revenue.ppa_base_tariff == 60
    assert project_inputs.revenue.ppa_term_years == 15
    assert sum(item.y1_amount_keur for item in project_inputs.opex) == 1000
    assert project_inputs.capex.total_capex == 50000
    assert project_inputs.financing.gearing_ratio == pytest.approx(0.70)
    assert project_inputs.financing.fixed_debt_keur == pytest.approx(35000)
    assert project_inputs.financing.margin_bps == 500
    assert project_inputs.financing.senior_tenor_years == 15
    assert project_inputs.financing.target_dscr == pytest.approx(1.30)


def test_user_project_runtime_uses_snapshot_inputs_not_factory_primary_source():
    from app.project_factories import create_default_tuho_wind1

    project_inputs = build_projectinputs_from_snapshot(
        _snapshot(template_source="tuho", project_name="User Project From TUHO", active_project="user-tuho")
    )

    assert project_inputs.info.name == "User Project From TUHO"
    assert project_inputs.info.code == "USER-TUHO"
    assert project_inputs.technical.capacity_mw == 50
    assert project_inputs.technical.capacity_mw != create_default_tuho_wind1().technical.capacity_mw


def test_tariff_and_p50_changes_increase_revenue():
    low_tariff = _run(_snapshot(tariff_eur_mwh="60"))["kpis"]
    high_tariff = _run(_snapshot(tariff_eur_mwh="100"))["kpis"]
    low_p50 = _run(_snapshot(p50_hours="1200"))["kpis"]
    high_p50 = _run(_snapshot(p50_hours="1600"))["kpis"]

    assert high_tariff["total_revenue_keur"] > low_tariff["total_revenue_keur"]
    assert high_p50["total_revenue_keur"] > low_p50["total_revenue_keur"]


def test_opex_and_gearing_changes_move_exposed_runtime_outputs():
    base_opex = _run(_snapshot(opex_y1_keur="1000"))["kpis"]
    high_opex = _run(_snapshot(opex_y1_keur="5000"))["kpis"]
    low_gearing = _run(_snapshot(gearing_pct="40"))["kpis"]
    high_gearing = _run(_snapshot(gearing_pct="70"))["kpis"]

    assert high_opex["total_ebitda_keur"] < base_opex["total_ebitda_keur"]
    assert low_gearing["min_dscr"] > high_gearing["min_dscr"]


def test_tuho_and_oborovo_factory_paths_still_run():
    assert "total_revenue_keur" in run_project("TUHO", "Base")["kpis"]
    assert "total_revenue_keur" in run_project("Oborovo", "Base")["kpis"]


def test_phase17c_docs_reports_and_guardrails():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs = open(os.path.join(base, "docs", "phase17_from_scratch_runtime_path.md"), encoding="utf-8").read()
    mapping = open(os.path.join(base, "reports", "phase17_from_scratch_runtime_input_mapping.csv"), encoding="utf-8").read()
    precedence = open(os.path.join(base, "reports", "phase17_from_scratch_runtime_source_precedence.csv"), encoding="utf-8").read()
    delta = open(os.path.join(base, "reports", "phase17_from_scratch_runtime_delta_proof.csv"), encoding="utf-8").read()
    gaps = open(os.path.join(base, "reports", "phase17_from_scratch_runtime_remaining_gaps.csv"), encoding="utf-8").read()
    selector = open(os.path.join(base, "app", "templates", "partials", "project_selector.html"), encoding="utf-8").read()
    workspace = open(os.path.join(base, "app", "templates", "partials", "scenario_workspace.html"), encoding="utf-8").read()
    js = open(os.path.join(base, "static", "app.js"), encoding="utf-8").read().lower()
    main_web = open(os.path.join(base, "main_web.py"), encoding="utf-8").read()

    assert "Phase 17C implements user-created project runtime from saved assumptions" in docs
    assert "clean saved scenario snapshot, then project baseline_snapshot" in docs
    assert "Unsaved dirty browser state is never runtime authority" in docs
    assert "No model formula changes were made" in docs
    assert "G20 remains BLOCKED" in docs
    assert "R99/R102 remain NOT APPROVED" in docs
    assert "capacity_mw" in mapping and "total_capex_keur" in mapping
    assert "clean_saved_scenario_snapshot" in precedence
    assert "tariff_delta" in delta and "opex_delta" in delta and "gearing_delta" in delta
    assert "system_default" in gaps
    assert "Runtime built from saved project assumptions" in selector
    assert "Runtime built from saved project assumptions" in workspace
    assert "runtime_guard_for_snapshot" in main_web
    assert "build_projectinputs_from_snapshot" in main_web

    for marker in ("xirr(", "project_irr =", "equity_irr =", "avg_dscr =", "debt service ="):
        assert marker not in js
