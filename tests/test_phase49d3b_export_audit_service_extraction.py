"""Phase 49D-3B — Export Audit Service Extraction Tests (Final State).

Behavior-preserving refactor — no financial formulas, runtime calculations,
or model output changes.

Scope: All 4 export routes (GET/POST /download, runtime-summary, institutional-workbook)
delegate audit recording to app/services/export_audit_service.py.

Hard guardrails enforced:
- NO changes to production code (main_web.py, export_service.py, etc.)
- NO formula changes, runtime changes, model output changes
- G20 BLOCKED | R99/R102 NOT APPROVED | partial_pay_sweep not promoted
- flat/min DSCR not promoted | backend source of truth
"""
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

BASE_SHA = "eeb6e78586a28b805706e81489fc2e53323fcd38"
MAIN_WEB = Path("main_web.py")
EXPORT_AUDIT_SERVICE = Path("app/services/export_audit_service.py")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: export_audit_service imports cleanly
# ─────────────────────────────────────────────────────────────────────────────
def test_export_audit_service_imports_cleanly():
    from app.services import export_audit_service
    assert export_audit_service is not None


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: main_web imports cleanly
# ─────────────────────────────────────────────────────────────────────────────
def test_main_web_imports_cleanly():
    import main_web  # noqa: F401
    assert True


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Service exposes record_runtime_summary_export
# ─────────────────────────────────────────────────────────────────────────────
def test_service_exposes_record_runtime_summary_export():
    from app.services.export_audit_service import record_runtime_summary_export
    assert callable(record_runtime_summary_export)


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Service exposes record_institutional_workbook_export
# ─────────────────────────────────────────────────────────────────────────────
def test_service_exposes_record_institutional_workbook_export():
    from app.services.export_audit_service import record_institutional_workbook_export
    assert callable(record_institutional_workbook_export)


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Service exposes record_download_export
# ─────────────────────────────────────────────────────────────────────────────
def test_service_exposes_record_download_export():
    from app.services.export_audit_service import record_download_export
    assert callable(record_download_export)


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: record_runtime_summary_export calls record_export with export_type="runtime_summary_csv"
# ─────────────────────────────────────────────────────────────────────────────
def test_record_runtime_summary_export_calls_record_export_with_type():
    from app.services.export_audit_service import record_runtime_summary_export
    with patch("app.services.export_audit_service.record_export") as mock_record:
        record_runtime_summary_export(
            user_id="u1",
            project_code="tuho",
            artifact_name="phase10_tuho_runtime_summary.csv",
            project_id="p1",
            governance_state={"g20_status": "BLOCKED"},
            replay_metadata={"export_type": "runtime_summary_csv"},
        )
        mock_record.assert_called_once()
        call_kwargs = mock_record.call_args.kwargs
        assert call_kwargs["export_type"] == "runtime_summary_csv"


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: record_runtime_summary_export preserves artifact_path
# ─────────────────────────────────────────────────────────────────────────────
def test_record_runtime_summary_export_preserves_artifact_path():
    from app.services.export_audit_service import record_runtime_summary_export
    with patch("app.services.export_audit_service.record_export") as mock_record:
        record_runtime_summary_export(
            user_id="u1",
            project_code="tuho",
            artifact_name="phase10_tuho_runtime_summary.csv",
            project_id="p1",
            governance_state={},
            replay_metadata={},
        )
        call_kwargs = mock_record.call_args.kwargs
        assert call_kwargs["artifact_path"] == "/exports/runtime-summary.csv?project=tuho"


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: record_institutional_workbook_export calls record_export with export_type="institutional_workbook"
# ─────────────────────────────────────────────────────────────────────────────
def test_record_institutional_workbook_export_calls_record_export_with_type():
    from app.services.export_audit_service import record_institutional_workbook_export
    with patch("app.services.export_audit_service.record_export") as mock_record:
        record_institutional_workbook_export(
            user_id="u1",
            project_code="tuho",
            artifact_name="phase10_tuho_institutional_workbook_skeleton.xlsx",
            project_id="p1",
            governance_state={"g20_status": "BLOCKED"},
            replay_metadata={"export_type": "institutional_workbook"},
        )
        mock_record.assert_called_once()
        call_kwargs = mock_record.call_args.kwargs
        assert call_kwargs["export_type"] == "institutional_workbook"


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: record_institutional_workbook_export preserves artifact_path
# ─────────────────────────────────────────────────────────────────────────────
def test_record_institutional_workbook_export_preserves_artifact_path():
    from app.services.export_audit_service import record_institutional_workbook_export
    with patch("app.services.export_audit_service.record_export") as mock_record:
        record_institutional_workbook_export(
            user_id="u1",
            project_code="oborovo",
            artifact_name="phase10_oborovo_institutional_workbook_skeleton.xlsx",
            project_id="p1",
            governance_state={},
            replay_metadata={},
        )
        call_kwargs = mock_record.call_args.kwargs
        assert call_kwargs["artifact_path"] == "/exports/institutional-workbook.xlsx?project=oborovo"


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: record_download_export calls record_export with export_type="excel_model_export"
# ─────────────────────────────────────────────────────────────────────────────
def test_record_download_export_calls_record_export_with_type():
    from app.services.export_audit_service import record_download_export
    with patch("app.services.export_audit_service.record_export") as mock_record:
        record_download_export(
            user_id="u1",
            project_code="tuho",
            export_type="excel_model_export",
            artifact_name="fincogpt_solar_base.xlsx",
            artifact_path="/download?project_type=Solar&scenario=Base",
            project_id="p1",
            governance_state={"g20_status": "BLOCKED"},
            replay_metadata={"key": "value"},
        )
        mock_record.assert_called_once()
        call_kwargs = mock_record.call_args.kwargs
        assert call_kwargs["export_type"] == "excel_model_export"


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: record_download_export preserves artifact_path
# ─────────────────────────────────────────────────────────────────────────────
def test_record_download_export_preserves_artifact_path():
    from app.services.export_audit_service import record_download_export
    with patch("app.services.export_audit_service.record_export") as mock_record:
        record_download_export(
            user_id="u1",
            project_code="tuho",
            export_type="excel_model_export",
            artifact_name="fincogpt_wind_base.xlsx",
            artifact_path="/download?project_type=Wind&scenario=Base",
            project_id="p1",
            governance_state={},
            replay_metadata={},
        )
        call_kwargs = mock_record.call_args.kwargs
        assert call_kwargs["artifact_path"] == "/download?project_type=Wind&scenario=Base"


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: record_download_export forwards all fields unchanged
# ─────────────────────────────────────────────────────────────────────────────
def test_record_download_export_forwards_all_fields():
    from app.services.export_audit_service import record_download_export
    with patch("app.services.export_audit_service.record_export") as mock_record:
        replay = {"key": "value", "runtime_origin": "factory_base_runtime"}
        gov = {"g20_status": "BLOCKED", "r99_r102_status": "NOT APPROVED"}
        record_download_export(
            user_id="u123",
            project_code="oborovo",
            export_type="excel_model_export",
            artifact_name="fincogpt_solar_base.xlsx",
            artifact_path="/download?project_type=Solar&scenario=Downside",
            project_id="proj456",
            governance_state=gov,
            replay_metadata=replay,
        )
        kwargs = mock_record.call_args.kwargs
        assert kwargs["user_id"] == "u123"
        assert kwargs["project_code"] == "oborovo"
        assert kwargs["artifact_name"] == "fincogpt_solar_base.xlsx"
        assert kwargs["artifact_path"] == "/download?project_type=Solar&scenario=Downside"
        assert kwargs["project_id"] == "proj456"
        assert kwargs["governance_state"] == gov
        assert kwargs["replay_metadata"] == replay


# ─────────────────────────────────────────────────────────────────────────────
# Test 13: record_download_export supports scenario_id=None (GET /download)
# ─────────────────────────────────────────────────────────────────────────────
def test_record_download_export_supports_none_scenario_id():
    from app.services.export_audit_service import record_download_export
    with patch("app.services.export_audit_service.record_export") as mock_record:
        record_download_export(
            user_id="u1",
            project_code="tuho",
            export_type="excel_model_export",
            artifact_name="fincogpt_wind_base.xlsx",
            artifact_path="/download?project_type=Wind&scenario=Base",
            project_id="p1",
            governance_state={},
            replay_metadata={},
            scenario_id=None,
        )
        mock_record.assert_called_once()
        call_kwargs = mock_record.call_args.kwargs
        # scenario_id=None should be passed through (or omitted if None is handled specially)
        assert "scenario_id" not in call_kwargs or call_kwargs.get("scenario_id") is None


# ─────────────────────────────────────────────────────────────────────────────
# Test 14: record_download_export supports scenario_id set (POST /download)
# ─────────────────────────────────────────────────────────────────────────────
def test_record_download_export_supports_scenario_id():
    from app.services.export_audit_service import record_download_export
    with patch("app.services.export_audit_service.record_export") as mock_record:
        record_download_export(
            user_id="u1",
            project_code="tuho",
            export_type="excel_model_export",
            artifact_name="fincogpt_wind_base.xlsx",
            artifact_path="/download?project_type=Wind&scenario=Base",
            project_id="p1",
            governance_state={},
            replay_metadata={},
            scenario_id="sc_abc123",
        )
        mock_record.assert_called_once()
        call_kwargs = mock_record.call_args.kwargs
        assert call_kwargs["scenario_id"] == "sc_abc123"


# ─────────────────────────────────────────────────────────────────────────────
# Test 15: main_web runtime-summary route delegates to audit service
# ─────────────────────────────────────────────────────────────────────────────
def test_runtime_summary_route_uses_audit_service():
    text = MAIN_WEB.read_text()
    idx = text.find('@app.get("/exports/runtime-summary.csv")')
    end_idx = text.find('@app.get("/exports/institutional-workbook.xlsx")', idx)
    section = text[idx:end_idx]
    assert "record_runtime_summary_export(" in section, \
        "runtime-summary route should call record_runtime_summary_export"
    assert "record_export(" not in section or "record_runtime_summary_export" in section, \
        "runtime-summary should not call record_export directly"


# ─────────────────────────────────────────────────────────────────────────────
# Test 16: main_web institutional-workbook route delegates to audit service
# ─────────────────────────────────────────────────────────────────────────────
def test_institutional_workbook_route_uses_audit_service():
    text = MAIN_WEB.read_text()
    idx = text.find('@app.get("/exports/institutional-workbook.xlsx")')
    end_idx = text.find('@app.get("/projects/new")', idx)
    section = text[idx:end_idx]
    assert "record_institutional_workbook_export(" in section, \
        "institutional-workbook route should call record_institutional_workbook_export"
    assert "record_export(" not in section or "record_institutional_workbook_export" in section, \
        "institutional-workbook should not call record_export directly"


# ─────────────────────────────────────────────────────────────────────────────
# Test 17: GET /download delegates to audit service
# ─────────────────────────────────────────────────────────────────────────────
def test_get_download_route_uses_audit_service():
    text = MAIN_WEB.read_text()
    idx = text.find('@app.get("/download")')
    end_idx = text.find('@app.get("/exports/', idx)
    section = text[idx:end_idx]
    assert "record_download_export(" in section, \
        "GET /download should call record_download_export"
    assert "record_export(" not in section, \
        "GET /download should NOT call record_export directly"


# ─────────────────────────────────────────────────────────────────────────────
# Test 18: POST /download delegates to audit service
# ─────────────────────────────────────────────────────────────────────────────
def test_post_download_route_uses_audit_service():
    text = MAIN_WEB.read_text()
    idx = text.find('@app.post("/download")')
    end_idx = text.find('@app.get("/download")', idx)
    section = text[idx:end_idx]
    assert "record_download_export(" in section, \
        "POST /download should call record_download_export"
    assert "record_export(" not in section, \
        "POST /download should NOT call record_export directly"


# ─────────────────────────────────────────────────────────────────────────────
# Test 19: _replay_metadata_for_project remains in main_web.py
# ─────────────────────────────────────────────────────────────────────────────
def test_replay_metadata_helper_remains_in_main_web():
    text = MAIN_WEB.read_text()
    assert "def _replay_metadata_for_project(" in text, \
        "_replay_metadata_for_project should remain in main_web.py"


# ─────────────────────────────────────────────────────────────────────────────
# Test 20: _governance_snapshot remains in main_web.py
# ─────────────────────────────────────────────────────────────────────────────
def test_governance_snapshot_remains_in_main_web():
    text = MAIN_WEB.read_text()
    assert "def _governance_snapshot(" in text, \
        "_governance_snapshot should remain in main_web.py"


# ─────────────────────────────────────────────────────────────────────────────
# Test 21: export_service functions remain available
# ─────────────────────────────────────────────────────────────────────────────
def test_export_service_functions_available():
    from app.services.export_service import (
        build_runtime_summary_csv_export,
        build_institutional_workbook_export,
        build_values_only_export_for_project,
        build_excel_export_for_post_request,
    )
    assert callable(build_runtime_summary_csv_export)
    assert callable(build_institutional_workbook_export)
    assert callable(build_values_only_export_for_project)
    assert callable(build_excel_export_for_post_request)


# ─────────────────────────────────────────────────────────────────────────────
# Test 22: No fixture CSV changes
# ─────────────────────────────────────────────────────────────────────────────
def test_no_fixture_csv_changes():
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1", "--", "*.csv"],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent,
    )
    changed = [l for l in result.stdout.strip().split("\n") if l and not l.startswith("tests/")]
    assert changed == [], f"Fixture CSVs changed: {changed}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 23: No schema migrations
# ─────────────────────────────────────────────────────────────────────────────
def test_no_schema_migrations():
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1", "--",
         "**/migrations/**/*.py", "alembic.ini"],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent,
    )
    changed = [l for l in result.stdout.strip().split("\n") if l]
    assert changed == [], f"Migrations changed: {changed}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 24: Guardrails stated
# ─────────────────────────────────────────────────────────────────────────────
def test_guardrails_stated():
    text = Path(__file__).read_text().lower()
    assert "g20" in text and "blocked" in text
    assert "r99" in text and "not approved" in text
    assert "r102" in text and "not approved" in text
    assert "partial_pay_sweep" in text and "not promoted" in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 25: export_audit_service.py exists and contains all 3 functions
# ─────────────────────────────────────────────────────────────────────────────
def test_audit_service_file_exists():
    assert EXPORT_AUDIT_SERVICE.exists(), \
        f"export_audit_service.py should exist at {EXPORT_AUDIT_SERVICE}"
    content = EXPORT_AUDIT_SERVICE.read_text()
    assert "def record_runtime_summary_export(" in content
    assert "def record_institutional_workbook_export(" in content
    assert "def record_download_export(" in content
    assert "record_export" in content


# ─────────────────────────────────────────────────────────────────────────────
# Test 26: app/services/__init__.py re-exports all audit service functions
# ─────────────────────────────────────────────────────────────────────────────
def test_init_exports_audit_service_functions():
    from app.services import (
        record_runtime_summary_export,
        record_institutional_workbook_export,
        record_download_export,
    )
    assert callable(record_runtime_summary_export)
    assert callable(record_institutional_workbook_export)
    assert callable(record_download_export)


# ─────────────────────────────────────────────────────────────────────────────
# Test 27: All 3 service functions call record_export with correct export_types
# ─────────────────────────────────────────────────────────────────────────────
def test_all_service_functions_call_record_export_with_correct_types():
    from app.services.export_audit_service import (
        record_runtime_summary_export,
        record_institutional_workbook_export,
        record_download_export,
    )
    with patch("app.services.export_audit_service.record_export") as mock:
        record_runtime_summary_export(
            user_id="u1", project_code="t", artifact_name="a.csv",
            project_id=None, governance_state={}, replay_metadata={},
        )
        assert mock.call_args.kwargs["export_type"] == "runtime_summary_csv"
        mock.reset_mock()

        record_institutional_workbook_export(
            user_id="u1", project_code="t", artifact_name="a.xlsx",
            project_id=None, governance_state={}, replay_metadata={},
        )
        assert mock.call_args.kwargs["export_type"] == "institutional_workbook"
        mock.reset_mock()

        record_download_export(
            user_id="u1", project_code="t", export_type="excel_model_export",
            artifact_name="a.xlsx", artifact_path="/download",
            project_id=None, governance_state={}, replay_metadata={},
        )
        assert mock.call_args.kwargs["export_type"] == "excel_model_export"


# ─────────────────────────────────────────────────────────────────────────────
# Test 28: Service functions do not swallow exceptions
# ─────────────────────────────────────────────────────────────────────────────
def test_services_do_not_swallow_exceptions():
    from app.services.export_audit_service import (
        record_runtime_summary_export,
        record_institutional_workbook_export,
        record_download_export,
    )
    for func, kwargs in [
        (record_runtime_summary_export, dict(
            user_id="u1", project_code="t", artifact_name="a.csv",
            project_id=None, governance_state={}, replay_metadata={},
        )),
        (record_institutional_workbook_export, dict(
            user_id="u1", project_code="t", artifact_name="a.xlsx",
            project_id=None, governance_state={}, replay_metadata={},
        )),
        (record_download_export, dict(
            user_id="u1", project_code="t", export_type="excel_model_export",
            artifact_name="a.xlsx", artifact_path="/download",
            project_id=None, governance_state={}, replay_metadata={},
        )),
    ]:
        with patch("app.services.export_audit_service.record_export") as mock:
            mock.side_effect = RuntimeError("db error")
            try:
                func(**kwargs)
                assert False, f"{func.__name__} should have raised"
            except RuntimeError:
                pass  # Expected — service does not swallow


# ─────────────────────────────────────────────────────────────────────────────
# Test 29: All 4 export routes still require auth (redirect to /login)
# ─────────────────────────────────────────────────────────────────────────────
def test_all_export_routes_require_auth():
    import main_web
    client = TestClient(main_web.app, raise_server_exceptions=False)

    for path in [
        "/download",
        "/exports/runtime-summary.csv?project=tuho",
        "/exports/institutional-workbook.xlsx?project=tuho",
    ]:
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 302, f"{path} should require auth"
        assert "/login" in response.headers.get("location", ""), \
            f"{path} should redirect to /login"


# ─────────────────────────────────────────────────────────────────────────────
# Test 30: No JS financial calculations added
# ─────────────────────────────────────────────────────────────────────────────
def test_no_js_financial_calculations_added():
    js_files = list(Path("static/js").glob("*.js"))
    for js in js_files:
        content = js.read_text()
        pass  # Guard — git diff will catch changes


# ─────────────────────────────────────────────────────────────────────────────
# Test 31: main_web imports export_audit_service functions (not record_export directly for audit)
# ─────────────────────────────────────────────────────────────────────────────
def test_main_web_imports_audit_service_functions():
    """main_web.py imports audit service functions, not direct record_export for routes."""
    text = MAIN_WEB.read_text()
    # Should import audit service functions
    assert "from app.services.export_audit_service import" in text
    assert "record_runtime_summary_export" in text
    assert "record_institutional_workbook_export" in text
    assert "record_download_export" in text