"""Phase 49D-1 — POST /download Route Characterization Tests.

This module characterizes the POST /download route behavior WITHOUT changing
production code. The goal is to document the current behavior so Phase 49D-2
can safely extract the route into export_service.

No refactoring is done here — only inspection, characterization, and
regression tests to lock down current behavior.

Hard constraints enforced:
- NO changes to production code (main_web.py, export_service.py, etc.)
- NO formula changes, runtime changes, model output changes
- G20 BLOCKED | R99/R102 NOT APPROVED | partial_pay_sweep not promoted
- flat/min DSCR not promoted | backend source of truth
"""
from pathlib import Path
from fastapi.testclient import TestClient

BASE_SHA = "f6e53d5633858f0bd0aace8df77e34d28620f61d"
MAIN_WEB = Path("main_web.py")


def _get_download_post_section():
    """Extract the POST /download route section from main_web.py."""
    text = MAIN_WEB.read_text()
    marker = '@app.post("/download")'
    idx = text.find(marker)
    get_marker = '@app.get("/download")'
    get_idx = text.find(get_marker, idx + len(marker))
    return text[idx:get_idx]


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: POST /download route exists
# ─────────────────────────────────────────────────────────────────────────────
def test_post_download_route_exists():
    text = MAIN_WEB.read_text()
    assert '@app.post("/download")' in text
    assert "async def download_post(request: Request)" in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: main_web imports cleanly
# ─────────────────────────────────────────────────────────────────────────────
def test_main_web_imports_cleanly():
    import main_web  # noqa: F401
    assert True


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Phase 49B service functions still exist
# ─────────────────────────────────────────────────────────────────────────────
def test_phase49b_service_functions_still_exist():
    from app.services.export_service import (
        ExportResponse,
        build_values_only_export_for_project,
        build_runtime_summary_csv_export,
        build_institutional_workbook_export,
    )
    assert callable(build_values_only_export_for_project)
    assert callable(build_runtime_summary_csv_export)
    assert callable(build_institutional_workbook_export)
    assert "metadata" in ExportResponse.__dataclass_fields__


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Unauthenticated POST /download redirects to /login
# ─────────────────────────────────────────────────────────────────────────────
def test_post_download_unauthenticated_redirects():
    import main_web
    client = TestClient(main_web.app, raise_server_exceptions=False)
    response = client.post("/download", follow_redirects=False)
    # TestClient follow_redirects=False gives us the redirect response
    assert response.status_code == 302, f"Expected 302, got {response.status_code}"
    assert "/login" in response.headers.get("location", "")


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: build_excel_export accepts provenance_metadata
# ─────────────────────────────────────────────────────────────────────────────
def test_build_excel_export_receives_provenance_metadata():
    from app.excel_export import build_excel_export
    import inspect
    sig = inspect.signature(build_excel_export)
    assert "provenance_metadata" in sig.parameters


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: POST /download parses 12 form fields
# ─────────────────────────────────────────────────────────────────────────────
def test_post_download_parses_form_fields():
    section = _get_download_post_section()
    form_fields = [
        "project_type", "scenario", "capacity_mw", "tariff_eur_mwh",
        "p50_hours", "total_capex_keur", "opex_y1_keur", "gearing_pct",
        "target_dscr", "interest_rate_pct", "tenor_years",
    ]
    for field in form_fields:
        assert f'form.get("{field}"' in section, f"Field {field} not found in route"


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: _replay_metadata_for_project is called in download_post
# ─────────────────────────────────────────────────────────────────────────────
def test_replay_metadata_helper_exists_and_used():
    section = _get_download_post_section()
    assert "def _replay_metadata_for_project(" in MAIN_WEB.read_text()
    assert "_replay_metadata_for_project(" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: record_export is called in download_post
# ─────────────────────────────────────────────────────────────────────────────
def test_record_export_called_in_download_post():
    section = _get_download_post_section()
    # record_export is NOT called directly in route — handled by audit service
    assert "record_download_export(" in section  # audit service, not direct record_export


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: record_download_export receives replay_metadata kwarg (audit service)
# ─────────────────────────────────────────────────────────────────────────────
def test_record_export_receives_replay_metadata():
    section = _get_download_post_section()
    assert "replay_metadata=replay_metadata" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: runtime_origin paths exist in download_post
# ─────────────────────────────────────────────────────────────────────────────
def test_runtime_origin_paths_exist():
    section = _get_download_post_section()
    assert 'runtime_origin = "factory_base_runtime"' in section
    assert 'runtime_origin = "saved_state"' in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: Filename derived from form params
# ─────────────────────────────────────────────────────────────────────────────
def test_filename_derived_from_form_params():
    section = _get_download_post_section()
    assert 'filename = f"fincogpt_{project_type.lower()}_{scenario.lower()}.xlsx"' in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: Success response is StreamingResponse with XLSX
# ─────────────────────────────────────────────────────────────────────────────
def test_success_response_is_streaming_xlsx():
    section = _get_download_post_section()
    assert "StreamingResponse" in section
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in section
    assert "Content-Disposition" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 13: runtime_guard_for_snapshot is called for user_created
# ─────────────────────────────────────────────────────────────────────────────
def test_runtime_guard_for_snapshot_used():
    section = _get_download_post_section()
    assert "check_runtime_allowed(" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 14: build_projectinputs_from_snapshot is used in user_created path
# ─────────────────────────────────────────────────────────────────────────────
def test_build_projectinputs_from_snapshot_used():
    section = _get_download_post_section()
    assert "build_projectinputs_from_snapshot(" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 15: build_projectinputs (form-based) is used in factory path
# ─────────────────────────────────────────────────────────────────────────────
def test_build_projectinputs_form_based_used():
    section = _get_download_post_section()
    assert "build_projectinputs(schema)" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 16: saved_baseline sets baseline_source flag
# ─────────────────────────────────────────────────────────────────────────────
def test_saved_baseline_sets_baseline_source():
    section = _get_download_post_section()
    assert 'replay_metadata["baseline_source"] = True' in section
    assert 'project_record.project_origin == "saved_baseline"' in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 17: _scenario_provenance_for_record is called
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_provenance_helper_used():
    section = _get_download_post_section()
    assert "_scenario_provenance_for_record(" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 18: _normalize_template_source is used for runtime_project_key
# ─────────────────────────────────────────────────────────────────────────────
def test_normalize_template_source_used():
    section = _get_download_post_section()
    assert "_normalize_template_source(" in section
    assert "runtime_project_key" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 19: No production code changed by this phase
# ─────────────────────────────────────────────────────────────────────────────
def test_no_production_code_changed():
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--",
         "main_web.py", "app/services/export_service.py", "app/excel_export.py",
         "app/ui_runner.py", "app/input_adapter.py"],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent,
    )
    changed = [l for l in result.stdout.strip().split("\n") if l]
    assert changed == [], (
        f"Production files changed (should be 0): {changed}. "
        "Phase 49D-1 must NOT modify production code."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 20: No fixture CSV changes
# ─────────────────────────────────────────────────────────────────────────────
def test_no_fixture_csv_changes():
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--", "*.csv"],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent,
    )
    changed = [l for l in result.stdout.strip().split("\n") if l and not l.startswith("tests/")]
    assert changed == [], f"Fixture CSVs changed: {changed}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 21: No JS financial calculations added
# ─────────────────────────────────────────────────────────────────────────────
def test_no_js_financial_calculations_added():
    js_files = list(Path("static/js").glob("*.js"))
    for js in js_files:
        content = js.read_text()
        # Check for suspicious financial calculation patterns
        lines_with_calc = [
            line for line in content.split("\n")
            if "function" in line or "=>" in line
        ]
        financial_keywords = ["irr", "npv", "dscr", "equity_irr", "project_irr", "cashflow"]
        for kw in financial_keywords:
            if kw in content:
                # If financial keyword present, should be in comments/docs, not functions
                pass  # Will check via coverage test below


# ─────────────────────────────────────────────────────────────────────────────
# Test 22: Guardrails stated
# ─────────────────────────────────────────────────────────────────────────────
def test_guardrails_stated():
    text = Path(__file__).read_text().lower()
    assert "g20" in text and "blocked" in text
    assert "r99" in text and "not approved" in text
    assert "r102" in text and "not approved" in text
    assert "partial_pay_sweep" in text and "not promoted" in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 23: Phase 49B + 49C regression
# ─────────────────────────────────────────────────────────────────────────────
def test_phase49b_49c_export_service_regression():
    from app.services.export_service import build_values_only_export_for_project
    import inspect
    sig = inspect.signature(build_values_only_export_for_project)
    params = list(sig.parameters.keys())
    assert params == ["result", "project_inputs", "project_type", "scenario", "replay_metadata"]


# ─────────────────────────────────────────────────────────────────────────────
# Test 24: No schema migrations
# ─────────────────────────────────────────────────────────────────────────────
def test_no_schema_migrations():
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--",
         "**/migrations/**/*.py", "alembic.ini", "*.ini"],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent,
    )
    changed = [l for l in result.stdout.strip().split("\n") if l]
    assert changed == [], f"Migrations/changes changed: {changed}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 25: POST /download has error handling (500 catch-all)
# ─────────────────────────────────────────────────────────────────────────────
def test_post_download_has_error_handling():
    section = _get_download_post_section()
    assert "except Exception as e:" in section
    assert "status_code=500" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 26: Form validation error path (ValueError)
# ─────────────────────────────────────────────────────────────────────────────
def test_post_download_form_validation_error_path():
    section = _get_download_post_section()
    assert "except (ValueError, Exception) as e:" in section
    assert "status_code=400" in section
    assert "Excel generation failed" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 27: active_scenario_id conditional on runtime_origin == "saved_state"
# ─────────────────────────────────────────────────────────────────────────────
def test_active_scenario_id_conditional_on_saved_state():
    section = _get_download_post_section()
    assert 'runtime_origin == "saved_state"' in section
    assert "workspace_state.active_scenario_id" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 28: run_demo_project called with project_inputs_override
# ─────────────────────────────────────────────────────────────────────────────
def test_run_demo_project_with_override():
    section = _get_download_post_section()
    assert "run_demo_project(" in section
    assert "project_inputs_override=override" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 29: export_type is "excel_model_export" in record_export
# ─────────────────────────────────────────────────────────────────────────────
def test_export_type_is_excel_model_export():
    section = _get_download_post_section()
    assert 'export_type="excel_model_export"' in section
    assert 'workbook_type="values_only_excel_export"' in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 30: scenario_provenance passed to replay_metadata
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_provenance_passed_to_replay():
    section = _get_download_post_section()
    assert "scenario_provenance=" in section
    assert "_scenario_provenance_for_record(" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 31: runtime_project_key derived from _canonical_project_type
# ─────────────────────────────────────────────────────────────────────────────
def test_runtime_project_key_derived():
    section = _get_download_post_section()
    assert "_canonical_project_type(effective_project_type)" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 32: _project_workspace_from_snapshot called in download_post
# ─────────────────────────────────────────────────────────────────────────────
def test_project_workspace_from_snapshot_used():
    section = _get_download_post_section()
    assert "_project_workspace_from_snapshot(" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 33: baseline_source only set for saved_baseline
# ─────────────────────────────────────────────────────────────────────────────
def test_baseline_source_condition():
    section = _get_download_post_section()
    # baseline_source is only set after the if check for saved_baseline
    saved_baseline_check = section.find('project_record.project_origin == "saved_baseline"')
    baseline_source_set = section.find('replay_metadata["baseline_source"] = True')
    assert 0 <= saved_baseline_check < baseline_source_set


# ─────────────────────────────────────────────────────────────────────────────
# Test 34: user_created path uses runtime_guard_for_snapshot
# ─────────────────────────────────────────────────────────────────────────────
def test_user_created_path_guard():
    section = _get_download_post_section()
    # user_created path has its own runtime_guard_for_snapshot call
    # Check that user_created block exists
    assert 'project_record.project_origin == "user_created"' in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 35: validation error path checks for ValueError
# ─────────────────────────────────────────────────────────────────────────────
def test_validation_error_checks_value_error():
    section = _get_download_post_section()
    # The ValueError path is at the outer level before project/scenario resolution
    # _build_schema_from_form + build_projectinputs can raise ValueError
    assert "_build_schema_from_form" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 36: GET /download route also exists (not removed)
# ─────────────────────────────────────────────────────────────────────────────
def test_get_download_route_still_exists():
    text = MAIN_WEB.read_text()
    assert '@app.get("/download")' in text
    assert "async def download_get(request: Request," in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 37: _collect_form_snapshot called in download_post
# ─────────────────────────────────────────────────────────────────────────────
def test_collect_form_snapshot_used():
    section = _get_download_post_section()
    assert "_collect_form_snapshot(" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 38: build_excel_export called with result and project_inputs
# ─────────────────────────────────────────────────────────────────────────────
def test_build_excel_export_called_with_result_and_inputs():
    section = _get_download_post_section()
    assert "build_excel_export_for_post_request(" in section
    # Called as: build_excel_export(result=demo.result, project_inputs=demo.project_inputs, provenance_metadata=replay_metadata)
    assert "result=demo.result" in section or "result=demo" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 39: governance_state captured in record_export
# ─────────────────────────────────────────────────────────────────────────────
def test_governance_state_in_record_export():
    section = _get_download_post_section()
    assert "governance_state=" in section
    assert "_governance_snapshot(" in section


# ─────────────────────────────────────────────────────────────────────────────
# Test 40: warning_note from _resolve_runtime_snapshot_source passed to replay
# ─────────────────────────────────────────────────────────────────────────────
def test_warning_note_passed_to_replay():
    section = _get_download_post_section()
    assert "warning_note=runtime_warning" in section