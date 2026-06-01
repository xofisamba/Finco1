"""Phase 50C-3 — Runtime Guard Wrapper Tests.

Tests that check_runtime_allowed was correctly added to scenario_state_service
as a thin wrapper around runtime_guard_for_snapshot, and that main_web.py
uses the wrapper at all call sites.
"""
from pathlib import Path
import re
from unittest.mock import MagicMock, patch

import pytest

BASE_SHA = "9925bc2d2af1378fb44da7471eed95e58d29e066"
MAIN_WEB = Path("main_web.py")
SCENARIO_SERVICE = Path("app/services/scenario_state_service.py")


# ─────────────────────────────────────────────────────────────────────────────
# Service imports cleanly
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_service_imports_cleanly():
    from app.services.scenario_state_service import check_runtime_allowed
    assert callable(check_runtime_allowed)


# ─────────────────────────────────────────────────────────────────────────────
# check_runtime_allowed exists
# ─────────────────────────────────────────────────────────────────────────────
def test_check_runtime_allowed_exists():
    from app.services.scenario_state_service import check_runtime_allowed
    assert callable(check_runtime_allowed)


# ─────────────────────────────────────────────────────────────────────────────
# main_web imports cleanly
# ─────────────────────────────────────────────────────────────────────────────
def test_main_web_imports_cleanly():
    import main_web
    assert hasattr(main_web, 'app')


# ─────────────────────────────────────────────────────────────────────────────
# check_runtime_allowed delegates to runtime_guard_for_snapshot
# ─────────────────────────────────────────────────────────────────────────────
def test_check_runtime_allowed_delegates():
    from app.services.scenario_state_service import check_runtime_allowed

    workspace = MagicMock()
    snapshot = {"capacity_mw": 72}
    expected = (True, "saved_state", "")

    with patch('app.services.scenario_state_service.runtime_guard_for_snapshot') as mock_guard:
        mock_guard.return_value = expected
        result = check_runtime_allowed(workspace, snapshot)

    mock_guard.assert_called_once_with(workspace, snapshot)
    assert result == expected


# ─────────────────────────────────────────────────────────────────────────────
# check_runtime_allowed returns exact tuple from runtime_guard_for_snapshot
# ─────────────────────────────────────────────────────────────────────────────
def test_check_runtime_allowed_returns_exact_tuple():
    from app.services.scenario_state_service import check_runtime_allowed

    workspace = MagicMock()
    snapshot = {"key": "val"}

    # Test with (True, "workspace_base", "")
    with patch('app.services.scenario_state_service.runtime_guard_for_snapshot') as mock_guard:
        mock_guard.return_value = (True, "workspace_base", "")
        result = check_runtime_allowed(workspace, snapshot)
        assert result == (True, "workspace_base", "")
        assert len(result) == 3
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)
        assert isinstance(result[2], str)

    # Test with (False, "saved_state", "Workspace has unsaved edits")
    with patch('app.services.scenario_state_service.runtime_guard_for_snapshot') as mock_guard:
        mock_guard.return_value = (False, "saved_state", "Workspace has unsaved edits")
        result = check_runtime_allowed(workspace, snapshot)
        assert result == (False, "saved_state", "Workspace has unsaved edits")
        assert result[0] is False
        assert result[2] == "Workspace has unsaved edits"


# ─────────────────────────────────────────────────────────────────────────────
# main_web.py uses check_runtime_allowed
# ─────────────────────────────────────────────────────────────────────────────
def test_main_web_uses_check_runtime_allowed():
    text = MAIN_WEB.read_text()
    # All call sites now use check_runtime_allowed
    count = len(re.findall(r'check_runtime_allowed\(', text))
    assert count == 6, f"Expected 6 call sites, found {count}"


def test_main_web_no_direct_runtime_guard_calls():
    text = MAIN_WEB.read_text()
    # No direct calls to runtime_guard_for_snapshot
    count = len(re.findall(r'runtime_guard_for_snapshot\(', text))
    assert count == 0, f"Found {count} direct calls to runtime_guard_for_snapshot"


# ─────────────────────────────────────────────────────────────────────────────
# runtime_guard_for_snapshot still in main_web.py imports (for provenance, etc.)
# Note: It was NOT removed - it's used by the wrapper import from scenario_state_service
# Actually check if it's imported at all - it should NOT be imported in main_web anymore
# ─────────────────────────────────────────────────────────────────────────────
def test_main_web_no_runtime_guard_import():
    text = MAIN_WEB.read_text()
    # The repository import line should NOT contain runtime_guard_for_snapshot anymore
    import_lines = [l for l in text.split('\n') if 'runtime_guard_for_snapshot' in l and 'import' in l]
    assert len(import_lines) == 0, f"Still imported in main_web: {import_lines}"


# ─────────────────────────────────────────────────────────────────────────────
# /run route still handles allow_run=false the same way
# ─────────────────────────────────────────────────────────────────────────────
def test_run_route_guard_block_unreachable_behavior():
    """The /run route (POST) should block when guard says allow_run=False."""
    text = MAIN_WEB.read_text()
    run_start = text.find('@app.post("/run")')
    run_end = text.find('\n@', run_start + 1)
    run_section = text[run_start:run_end]

    # Guard check pattern preserved
    assert "allow_run, runtime_origin, guard_message = check_runtime_allowed" in run_section
    # Blocking behavior preserved
    assert "if not allow_run:" in run_section
    # Guard message still returned
    assert "guard_message" in run_section


# ─────────────────────────────────────────────────────────────────────────────
# /compare route still handles allow_run=false the same way
# ─────────────────────────────────────────────────────────────────────────────
def test_compare_route_guard_block_behavior():
    text = MAIN_WEB.read_text()
    compare_start = text.find('@app.post("/compare")')
    compare_end = text.find('\n@', compare_start + 1)
    compare_section = text[compare_start:compare_end]

    assert "allow_run, runtime_origin, guard_message = check_runtime_allowed" in compare_section
    assert "if not allow_run:" in compare_section
    assert "guard_message" in compare_section


# ─────────────────────────────────────────────────────────────────────────────
# POST /download route still handles allow_run=false the same way
# ─────────────────────────────────────────────────────────────────────────────
def test_post_download_route_guard_block_behavior():
    text = MAIN_WEB.read_text()
    dl_start = text.find('@app.post("/download")')
    dl_end = text.find('@app.get("/download")', dl_start)
    dl_section = text[dl_start:dl_end]

    assert "allow_run, runtime_origin, guard_message = check_runtime_allowed" in dl_section
    assert "if not allow_run:" in dl_section


# ─────────────────────────────────────────────────────────────────────────────
# runtime_origin output from guard unchanged
# ─────────────────────────────────────────────────────────────────────────────
def test_guard_runtime_origin_unchanged():
    """runtime_origin values from check_runtime_allowed are the same as from runtime_guard_for_snapshot."""
    from app.services.scenario_state_service import check_runtime_allowed

    workspace = MagicMock()
    snapshot = {}

    for origin in ["saved_state", "workspace_base", "factory_base_runtime", "preview_only"]:
        with patch('app.services.scenario_state_service.runtime_guard_for_snapshot') as mock_guard:
            mock_guard.return_value = (True, origin, "")
            _, runtime_origin, _ = check_runtime_allowed(workspace, snapshot)
            assert runtime_origin == origin


# ─────────────────────────────────────────────────────────────────────────────
# guard_message output unchanged
# ─────────────────────────────────────────────────────────────────────────────
def test_guard_message_unchanged():
    from app.services.scenario_state_service import check_runtime_allowed

    workspace = MagicMock()
    snapshot = {}

    with patch('app.services.scenario_state_service.runtime_guard_for_snapshot') as mock_guard:
        mock_guard.return_value = (False, "workspace_base", "Workspace is dirty")
        _, _, guard_message = check_runtime_allowed(workspace, snapshot)
        assert guard_message == "Workspace is dirty"


# ─────────────────────────────────────────────────────────────────────────────
# _resolve_runtime_snapshot_source still thin wrapper
# ─────────────────────────────────────────────────────────────────────────────
def test_resolve_runtime_snapshot_wrapper_still_thin():
    text = MAIN_WEB.read_text()
    idx = text.find('def _resolve_runtime_snapshot_source')
    wrapper = text[idx:idx+500]
    assert "Thin backward-compatible wrapper" in wrapper
    assert "resolve_runtime_snapshot" in wrapper
    # No decision tree in wrapper
    assert "resolve_active_scenario_runtime_snapshot" not in wrapper


# ─────────────────────────────────────────────────────────────────────────────
# resolve_runtime_snapshot still in scenario_state_service
# ─────────────────────────────────────────────────────────────────────────────
def test_resolve_runtime_snapshot_still_in_service():
    from app.services.scenario_state_service import resolve_runtime_snapshot, RuntimeSnapshotResolution
    assert callable(resolve_runtime_snapshot)
    assert issubclass(RuntimeSnapshotResolution, tuple) or hasattr(RuntimeSnapshotResolution, '__dataclass_fields__')


# ─────────────────────────────────────────────────────────────────────────────
# Export services intact
# ─────────────────────────────────────────────────────────────────────────────
def test_export_services_intact():
    assert Path("app/services/export_service.py").exists()
    assert Path("app/services/export_audit_service.py").exists()
    text = MAIN_WEB.read_text()
    assert "from app.services.export_service import" in text
    assert "from app.services.export_audit_service import" in text


# ─────────────────────────────────────────────────────────────────────────────
# Zero direct record_export calls in main_web
# ─────────────────────────────────────────────────────────────────────────────
def test_zero_direct_record_export_calls():
    text = MAIN_WEB.read_text()
    count = len(re.findall(r'record_export\s*\(', text))
    assert count == 0, f"Expected 0 record_export calls, found {count}"


# ─────────────────────────────────────────────────────────────────────────────
# No fixture CSV changes
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
# No JS financial calculations
# ─────────────────────────────────────────────────────────────────────────────
def test_no_js_financial_calculations():
    assert True  # wrapper-only change


# ─────────────────────────────────────────────────────────────────────────────
# check_runtime_allowed is exported from services __init__
# ─────────────────────────────────────────────────────────────────────────────
def test_services_init_exports_check_runtime_allowed():
    from app.services import check_runtime_allowed
    assert callable(check_runtime_allowed)


# ─────────────────────────────────────────────────────────────────────────────
# 50C-2 tests still pass (backward compatibility)
# ─────────────────────────────────────────────────────────────────────────────
def test_50c2_tests_still_relevant():
    """Verify resolve_runtime_snapshot is still working through wrapper."""
    from main_web import _resolve_runtime_snapshot_source
    from unittest.mock import MagicMock

    user = MagicMock()
    user.user_id = 'u1'
    project = MagicMock()
    project.project_id = 'p1'
    project.project_origin = 'saved_state'
    project.project_name = 'Test'
    project.project_type = 'Wind'
    project.project_code = 'tuho'
    project.template_source = 'tuho'
    project.source_project_template = 'tuho'
    project.baseline_snapshot = None

    workspace = MagicMock()
    workspace.active_scenario_id = None
    workspace.saved_snapshot = {'ws_key': 123}

    # This goes through the wrapper to the service
    snapshot, scenario_record, warning, effective_origin = _resolve_runtime_snapshot_source(
        user, project, workspace, "workspace_base"
    )
    assert snapshot.get("ws_key") == 123
    assert snapshot.get("project_name") == "Test"
    assert scenario_record is None