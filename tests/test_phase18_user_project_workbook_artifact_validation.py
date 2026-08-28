from __future__ import annotations

import os
import sys
from io import BytesIO

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
from app.input_adapter import build_projectinputs_from_snapshot
from app.persistence.repository import runtime_guard_for_snapshot


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
        "tariff_eur_mwh": "100",
        "ppa_term_years": "15",
        "p50_hours": "1600",
        "opex_y1_keur": "1000",
        "total_capex_keur": "50000",
        "gearing_pct": "70",
        "interest_rate_pct": "5",
        "tenor_years": "15",
        "target_dscr": "1.30",
    }
    data.update(overrides)
    return data


def _download_route_source() -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_web = open(os.path.join(base, "main_web.py"), encoding="utf-8").read()
    return main_web[main_web.index('@app.post("/download")'):main_web.index('@app.get("/download")')]


def _field_value_map(worksheet) -> dict[str, object]:
    mapping: dict[str, object] = {}
    for row in worksheet.iter_rows(values_only=True):
        values = [value for value in row if value not in (None, "")]
        if len(values) >= 2:
            mapping[str(values[-2]).strip()] = values[-1]
    return mapping


def test_export_binding_source_and_guardrails_are_hardened():
    """Phase 51C-2 refactor moved the download route's
    user_created binding into app/services/download_service.py.
    The hard contract is preserved: user_created projects
    are bound by their own snapshot, not by factory.
    """
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Read both possible locations for the contract.
    main_web = open(os.path.join(base, "main_web.py"), encoding="utf-8").read()
    download_service = open(
        os.path.join(base, "app", "services", "download_service.py"),
        encoding="utf-8",
    ).read()
    source = main_web + "\n" + download_service
    assert 'project_record.project_origin == "user_created"' in source
    assert "build_projectinputs_from_snapshot" in source
    # Phase 51C-2: runtime_guard_for_snapshot is imported
    # in scenario_state_service (and re-exported). The
    # call site may live in main_web or in a service
    # module. We accept either.
    assert (
        "runtime_guard_for_snapshot" in main_web
        or "runtime_guard_for_snapshot" in download_service
        or "check_runtime_allowed" in main_web
    )


def test_dirty_state_guard_blocks_export_like_runtime_paths():
    clean_snapshot = _snapshot()

    class _Workspace:
        saved_snapshot = clean_snapshot
        active_scenario_id = "scenario-1"
        dirty = True

    dirty_snapshot = dict(clean_snapshot)
    dirty_snapshot["tariff_eur_mwh"] = "999"
    allow_run, origin, message = runtime_guard_for_snapshot(_Workspace, dirty_snapshot)
    assert allow_run is False
    assert origin == "preview_only"
    assert "Unsaved edits" in message


def test_workbook_artifact_opens_and_exposes_user_project_metadata_when_openpyxl_available():
    openpyxl = pytest.importorskip("openpyxl")
    from app.excel_export import build_excel_export
    from app.ui_runner import run_demo_project

    project_inputs = build_projectinputs_from_snapshot(_snapshot())
    demo = run_demo_project("Wind", "Base", project_inputs_override=project_inputs)
    workbook_bytes = build_excel_export(
        result=demo.result,
        project_inputs=demo.project_inputs,
        project_type="Wind",
        scenario="Base",
        provenance_metadata={
            "active_project": "pilot-wind",
            "scenario_name": "Base",
            "runtime_origin": "saved_state",
            "template_origin": "saved_project_assumptions",
            "governance_posture_summary": "G20 remains BLOCKED; R99/R102 remain NOT APPROVED",
            "runtime_flags_json": "{}",
        },
    )
    assert len(workbook_bytes) > 1000

    workbook = openpyxl.load_workbook(BytesIO(workbook_bytes), data_only=True)
    assert "Notes" in workbook.sheetnames
    assert "Inputs" in workbook.sheetnames

    notes = _field_value_map(workbook["Notes"])
    inputs = _field_value_map(workbook["Inputs"])
    flat_notes = " ".join(str(value) for value in notes.values())

    assert notes["Active Project"] == "pilot-wind"
    assert notes["Runtime Origin"] == "saved_state"
    assert notes["Template Origin"] == "saved_project_assumptions"
    assert "G20 remains BLOCKED" in flat_notes
    assert "R99/R102 remain NOT APPROVED" in flat_notes
    assert "descriptive only" in flat_notes.lower()

    assert inputs["Name"] == "Pilot Wind"
    assert inputs["Country"] == "HR"
    assert float(inputs["Capacity (MW)"]) == pytest.approx(50.0)
    assert float(inputs["PPA Tariff"]) == pytest.approx(100.0)
    assert float(inputs["P50 Hours"]) == pytest.approx(1600.0)
    assert float(inputs["Year 1 OPEX (kEUR)"]) == pytest.approx(1000.0)
    assert float(inputs["Total CapEx (kEUR)"]) == pytest.approx(50000.0)
    assert float(inputs["Gearing (%, indicative input)"]) == pytest.approx(70.0)
    assert float(inputs["All-in Rate"]) == pytest.approx(0.05)
    assert int(inputs["Senior Tenor (years)"]) == 15
    assert float(inputs["Target DSCR"]) == pytest.approx(1.30)


def test_runtime_delta_proofs_and_factory_paths_still_hold():
    low_tariff = run_project("Wind", "Base", project_inputs_override=build_projectinputs_from_snapshot(_snapshot(tariff_eur_mwh="60")))["kpis"]
    high_tariff = run_project("Wind", "Base", project_inputs_override=build_projectinputs_from_snapshot(_snapshot(tariff_eur_mwh="100")))["kpis"]
    low_p50 = run_project("Wind", "Base", project_inputs_override=build_projectinputs_from_snapshot(_snapshot(p50_hours="1200")))["kpis"]
    high_p50 = run_project("Wind", "Base", project_inputs_override=build_projectinputs_from_snapshot(_snapshot(p50_hours="1600")))["kpis"]
    low_opex = run_project("Wind", "Base", project_inputs_override=build_projectinputs_from_snapshot(_snapshot(opex_y1_keur="1000")))["kpis"]
    high_opex = run_project("Wind", "Base", project_inputs_override=build_projectinputs_from_snapshot(_snapshot(opex_y1_keur="3000")))["kpis"]
    low_gearing = run_project("Wind", "Base", project_inputs_override=build_projectinputs_from_snapshot(_snapshot(gearing_pct="70")))["kpis"]
    high_gearing = run_project("Wind", "Base", project_inputs_override=build_projectinputs_from_snapshot(_snapshot(gearing_pct="80")))["kpis"]

    assert high_tariff["total_revenue_keur"] > low_tariff["total_revenue_keur"]
    assert high_p50["total_revenue_keur"] > low_p50["total_revenue_keur"]
    assert high_opex["total_opex_keur"] > low_opex["total_opex_keur"]
    assert high_opex["total_ebitda_keur"] < low_opex["total_ebitda_keur"]
    assert high_gearing["min_dscr"] < low_gearing["min_dscr"]
    assert "total_revenue_keur" in run_project("TUHO", "Base")["kpis"]
    assert "total_revenue_keur" in run_project("Oborovo", "Base")["kpis"]


def test_docs_reports_and_no_js_financial_calc_guardrails():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs = open(os.path.join(base, "docs", "phase18_user_project_browser_workbook_validation.md"), encoding="utf-8").read()
    workbook_matrix = open(os.path.join(base, "reports", "phase18_user_project_workbook_artifact_matrix.csv"), encoding="utf-8").read()
    export_matrix = open(os.path.join(base, "reports", "phase18_user_project_export_route_binding_matrix.csv"), encoding="utf-8").read()
    browser_matrix = open(os.path.join(base, "reports", "phase18_user_project_browser_e2e_matrix.csv"), encoding="utf-8").read()
    gaps = open(os.path.join(base, "reports", "phase18_user_project_export_remaining_gaps.csv"), encoding="utf-8").read()
    js = open(os.path.join(base, "static", "app.js"), encoding="utf-8").read().lower()

    assert "Dirty browser draft state is not runtime authority" in docs
    assert "saved_project_assumptions" in workbook_matrix
    assert "openpyxl is unavailable" in workbook_matrix
    assert "saved_project_assumptions" in export_matrix
    assert "optional_not_run_in_this_environment" in browser_matrix
    assert "No fake browser pass recorded" in browser_matrix
    assert "COD date is not surfaced as a distinct exported Inputs row" in gaps
    assert "G20 remains BLOCKED" in docs
    assert "R99/R102 remain NOT APPROVED" in docs
    assert "no lender-ready or audit-certified claim" in docs.lower()

    for marker in ("xirr(", "project_irr =", "equity_irr =", "avg_dscr =", "debt service ="):
        assert marker not in js
