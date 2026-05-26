from __future__ import annotations

import os
import sys
import uuid

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.project_runner import run_project
from app.input_adapter import build_projectinputs_from_snapshot
from app.persistence.repository import (
    bind_workspace_to_scenario,
    create_project_record,
    discard_workspace_draft,
    get_project_by_code,
    list_project_records,
    runtime_guard_for_snapshot,
    save_scenario,
    save_workspace_state,
)
from app.ui.project_context import build_project_context_for_record


@pytest.fixture
def isolated_db():
    import app.persistence.db as db_mod

    old_path = os.environ.get("FINCO_DB_PATH")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_file = os.path.join(base_dir, f"phase17d_{uuid.uuid4().hex[:8]}.db")
    os.environ["FINCO_DB_PATH"] = db_file
    db_mod.DB_PATH = db_file

    yield db_file

    if os.path.exists(db_file):
        os.remove(db_file)
    if old_path:
        os.environ["FINCO_DB_PATH"] = old_path
        db_mod.DB_PATH = old_path
    else:
        os.environ.pop("FINCO_DB_PATH", None)


def _snapshot(**overrides):
    data = {
        "active_project": "pilot-wind",
        "project_name": "Pilot Wind",
        "project_type": "Wind",
        "project_origin": "user_created",
        "template_source": "generic_wind",
        "country_market": "Croatia",
        "scenario": "Base",
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
    key = "Solar" if snapshot["project_type"] == "Solar" else "Wind"
    return run_project(key, "Base", project_inputs_override=build_projectinputs_from_snapshot(snapshot))


def test_user_project_save_load_revert_and_runtime_workflow(isolated_db):
    user_id = f"u{uuid.uuid4().hex[:8]}"
    baseline = _snapshot()
    project = create_project_record(
        user_id=user_id,
        project_code="pilot-wind",
        project_name="Pilot Wind",
        project_type="Wind",
        project_origin="user_created",
        template_source="generic_wind",
        baseline_snapshot=baseline,
        governance_state={"G20": "BLOCKED", "R99/R102": "NOT APPROVED"},
    )

    assert any(item.project_code == "pilot-wind" for item in list_project_records(user_id=user_id))
    reloaded = get_project_by_code(user_id, "pilot-wind")
    assert reloaded is not None
    assert reloaded.baseline_snapshot["tariff_eur_mwh"] == "60"

    context = build_project_context_for_record(
        project_code=project.project_code,
        project_name=project.project_name,
        project_type=project.project_type,
        project_origin=project.project_origin,
        template_source=project.template_source,
        baseline_snapshot=project.baseline_snapshot,
    )
    assert context.name == "Pilot Wind"
    assert context.capacity_mw == 50
    assert context.ppa_tariff_eur_mwh == 60
    assert "runtime built from saved project assumptions" in context.data_source.lower()

    scenario = save_scenario(
        user_id=user_id,
        project_id=project.project_id,
        scenario_name="Pilot Wind Base",
        project_code=project.project_code,
        source_project_template=project.template_source,
        snapshot=baseline,
        governance_state={"G20": "BLOCKED", "R99/R102": "NOT APPROVED"},
    )
    workspace = bind_workspace_to_scenario(
        user_id,
        project.project_id,
        project.project_code,
        scenario,
        governance_state={"G20": "BLOCKED", "R99/R102": "NOT APPROVED"},
    )
    allow_run, origin, message = runtime_guard_for_snapshot(workspace, baseline)
    assert allow_run is True
    assert origin == "saved_state"
    assert message == ""
    assert _run(workspace.saved_snapshot)["kpis"]["total_revenue_keur"] > 0

    dirty_snapshot = dict(baseline)
    dirty_snapshot["tariff_eur_mwh"] = "999"
    dirty_workspace = save_workspace_state(
        user_id=user_id,
        project_id=project.project_id,
        project_code=project.project_code,
        active_scenario_id=scenario.scenario_id,
        active_scenario_name=scenario.scenario_name,
        draft_snapshot=dirty_snapshot,
        saved_snapshot=baseline,
        dirty=True,
    )
    allow_run, origin, message = runtime_guard_for_snapshot(dirty_workspace, dirty_snapshot)
    assert allow_run is False
    assert origin == "preview_only"
    assert "Unsaved edits" in message

    reverted = discard_workspace_draft(user_id, project.project_id)
    assert reverted is not None
    assert reverted.draft_snapshot == baseline
    allow_run, origin, _ = runtime_guard_for_snapshot(reverted, reverted.draft_snapshot)
    assert allow_run is True
    assert origin == "saved_state"
    assert _run(reverted.saved_snapshot)["kpis"]["total_revenue_keur"] > 0


def test_route_level_runtime_delta_proof_from_saved_snapshots():
    low_tariff = _run(_snapshot(tariff_eur_mwh="60"))["kpis"]
    high_tariff = _run(_snapshot(tariff_eur_mwh="100"))["kpis"]
    low_p50 = _run(_snapshot(p50_hours="1200"))["kpis"]
    high_p50 = _run(_snapshot(p50_hours="1600"))["kpis"]
    low_opex = _run(_snapshot(opex_y1_keur="1000"))["kpis"]
    high_opex = _run(_snapshot(opex_y1_keur="3000"))["kpis"]
    gearing_70 = _run(_snapshot(gearing_pct="70"))["kpis"]
    gearing_80 = _run(_snapshot(gearing_pct="80"))["kpis"]

    assert high_tariff["total_revenue_keur"] > low_tariff["total_revenue_keur"]
    assert high_p50["total_revenue_keur"] > low_p50["total_revenue_keur"]
    assert high_opex["total_opex_keur"] > low_opex["total_opex_keur"]
    assert high_opex["total_ebitda_keur"] < low_opex["total_ebitda_keur"]
    assert gearing_80["min_dscr"] < gearing_70["min_dscr"]


def test_export_generation_for_user_project_when_workbook_dependency_available():
    pytest.importorskip("openpyxl")
    from app.excel_export import build_excel_export
    from app.ui_runner import run_demo_project

    project_inputs = build_projectinputs_from_snapshot(_snapshot())
    demo = run_demo_project("Wind", "Base", project_inputs_override=project_inputs)
    workbook_bytes = build_excel_export(
        result=demo.result,
        project_inputs=demo.project_inputs,
        provenance_metadata={"project_code": "pilot-wind", "source": "saved_project_assumptions"},
    )
    assert len(workbook_bytes) > 1000


def test_compare_and_export_routes_are_user_project_bound_by_source():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_web = open(os.path.join(base, "main_web.py"), encoding="utf-8").read()
    compare = main_web[main_web.index('@app.post("/compare")'):main_web.index('@app.post("/download")')]
    download = main_web[main_web.index('@app.post("/download")'):main_web.index('@app.post("/projects/create")')]

    for section in (compare, download):
        assert 'project_record.project_origin == "user_created"' in section
        assert "runtime_guard_for_snapshot" in section
        assert "_clean_user_project_runtime_snapshot" in section
        assert "build_projectinputs_from_snapshot" in section

    assert compare.index('project_record.project_origin == "user_created"') < compare.index('runtime_seed == "tuho"')
    assert download.index('project_record.project_origin == "user_created"') < download.index('runtime_seed == "tuho"')


def test_ui_disclosure_no_stale_phase17c_template_seeded_language():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for relative in (
        "app/templates/partials/project_selector.html",
        "app/templates/partials/scenario_workspace.html",
        "app/templates/partials/new_project_form.html",
        "app/templates/partials/new_project_result.html",
    ):
        text = open(os.path.join(base, relative), encoding="utf-8").read()
        assert "template-seeded defaults until Phase 17C" not in text
        assert "Runtime remains template-seeded" not in text
    assert "Runtime built from saved project assumptions" in open(
        os.path.join(base, "app/templates/partials/project_selector.html"), encoding="utf-8"
    ).read()


def test_factory_templates_guardrails_and_no_js_financial_calculations():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs = open(os.path.join(base, "docs", "phase17_user_project_e2e_runtime_export_validation.md"), encoding="utf-8").read()
    js = open(os.path.join(base, "static", "app.js"), encoding="utf-8").read().lower()

    assert "total_revenue_keur" in run_project("TUHO", "Base")["kpis"]
    assert "total_revenue_keur" in run_project("Oborovo", "Base")["kpis"]
    assert "G20 remains BLOCKED" in docs
    assert "R99/R102 remain NOT APPROVED" in docs
    assert "Save does not auto-run" in docs
    assert "Run does not auto-save" in docs

    for marker in ("xirr(", "project_irr =", "equity_irr =", "avg_dscr =", "debt service ="):
        assert marker not in js
