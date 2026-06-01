"""Phase 50C-2 — Runtime Snapshot Resolver Extraction Tests.

Tests that resolve_runtime_snapshot was correctly extracted from main_web.py
into scenario_state_service.py, and that the wrapper in main_web.py delegates
to the service correctly.

These tests verify:
1. Service function and dataclass exist
2. Wrapper exists in main_web.py and delegates to service
3. All branch behavior is preserved (same as Phase 50C-1 characterization)
4. No production behavior changes
"""
from pathlib import Path
import re
from unittest.mock import MagicMock, patch

import pytest

BASE_SHA = "af2729c03e7265ff74eb98ce658d5edf44d44452"
MAIN_WEB = Path("main_web.py")
SCENARIO_SERVICE = Path("app/services/scenario_state_service.py")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def make_mock_user(user_id="user-123"):
    u = MagicMock()
    u.user_id = user_id
    return u


def make_mock_project(project_origin="saved_state", has_baseline=False, project_id="proj-456"):
    p = MagicMock()
    p.project_id = project_id
    p.project_origin = project_origin
    p.project_name = "Test Project"
    p.project_type = "Wind"
    p.project_code = "tuho"
    p.template_source = "tuho"
    p.source_project_template = "tuho"
    p.baseline_snapshot = {"capacity_mw": 35, "tariff_eur_mwh": 55} if has_baseline else None
    return p


def make_mock_workspace(active_scenario_id=None, saved_snapshot=None):
    """Return a real dict-like object or None (not MagicMock for saved_snapshot).

    MagicMock causes dict() to fail because MagicMock is iterable-like but not actually iterable.
    Use a real object that properly returns None for saved_snapshot when intended.
    """
    if saved_snapshot is None and active_scenario_id is None:
        # Return a minimal mock that returns None for both attributes (acts falsy)
        ws = MagicMock()
        ws.active_scenario_id = active_scenario_id
        ws.saved_snapshot = saved_snapshot  # None
        return ws
    ws = MagicMock()
    ws.active_scenario_id = active_scenario_id
    ws.saved_snapshot = saved_snapshot
    return ws


# ─────────────────────────────────────────────────────────────────────────────
# Service imports cleanly
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_service_imports_cleanly():
    from app.services.scenario_state_service import resolve_runtime_snapshot, RuntimeSnapshotResolution
    assert callable(resolve_runtime_snapshot)
    assert issubclass(RuntimeSnapshotResolution, tuple) or hasattr(RuntimeSnapshotResolution, "__dataclass_fields__") or hasattr(RuntimeSnapshotResolution, '__dataclass_fields__')


# ─────────────────────────────────────────────────────────────────────────────
# RuntimeSnapshotResolution dataclass
# ─────────────────────────────────────────────────────────────────────────────
def test_runtime_snapshot_resolution_is_frozen_dataclass():
    from app.services.scenario_state_service import RuntimeSnapshotResolution
    from dataclasses import is_dataclass
    assert is_dataclass(RuntimeSnapshotResolution)
    # frozen=True (immutable)
    assert getattr(RuntimeSnapshotResolution, '__dataclass_params__', {}).frozen is True


def test_runtime_snapshot_resolution_fields():
    from app.services.scenario_state_service import RuntimeSnapshotResolution
    fields = RuntimeSnapshotResolution.__dataclass_fields__
    assert "snapshot" in fields
    assert "scenario_record" in fields
    assert "warning" in fields
    assert "effective_runtime_origin" in fields


# ─────────────────────────────────────────────────────────────────────────────
# resolve_runtime_snapshot exists and returns RuntimeSnapshotResolution
# ─────────────────────────────────────────────────────────────────────────────
def test_resolve_runtime_snapshot_exists():
    from app.services.scenario_state_service import resolve_runtime_snapshot
    assert callable(resolve_runtime_snapshot)


def test_resolve_runtime_snapshot_returns_dataclass():
    from app.services.scenario_state_service import resolve_runtime_snapshot
    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=False)
    workspace = make_mock_workspace(active_scenario_id=None, saved_snapshot=None)

    result = resolve_runtime_snapshot(
        user=user, project_record=project,
        workspace_state=workspace, runtime_origin="workspace_base"
    )
    assert hasattr(result, 'snapshot')
    assert hasattr(result, 'scenario_record')
    assert hasattr(result, 'warning')
    assert hasattr(result, 'effective_runtime_origin')


# ─────────────────────────────────────────────────────────────────────────────
# main_web imports cleanly
# ─────────────────────────────────────────────────────────────────────────────
def test_main_web_imports_cleanly():
    import main_web
    assert hasattr(main_web, 'app')


# ─────────────────────────────────────────────────────────────────────────────
# _resolve_runtime_snapshot_source exists in main_web.py as wrapper
# ─────────────────────────────────────────────────────────────────────────────
def test_wrapper_exists_in_main_web():
    text = MAIN_WEB.read_text()
    assert "def _resolve_runtime_snapshot_source" in text


def test_wrapper_contains_delegate_comment():
    text = MAIN_WEB.read_text()
    assert "Thin backward-compatible wrapper" in text
    assert "resolve_runtime_snapshot" in text


# ─────────────────────────────────────────────────────────────────────────────
# Wrapper delegates to service (thin wrapper behavior)
# ─────────────────────────────────────────────────────────────────────────────
def test_wrapper_delegates_to_service():
    from main_web import _resolve_runtime_snapshot_source
    from app.services.scenario_state_service import resolve_runtime_snapshot as service_fn

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id=None, saved_snapshot={"ws_key": 999})

    wrapper_result = _resolve_runtime_snapshot_source(
        user, project, workspace, "workspace_base"
    )
    service_result = service_fn(
        user=user, project_record=project,
        workspace_state=workspace, runtime_origin="workspace_base"
    )

    # Both return same 4-element tuple shape
    assert len(wrapper_result) == 4
    # Values should match (service_result is RuntimeSnapshotResolution)
    assert wrapper_result[0] == service_result.snapshot
    assert wrapper_result[1] == service_result.scenario_record
    assert wrapper_result[2] == service_result.warning
    assert wrapper_result[3] == service_result.effective_runtime_origin


def test_wrapper_preserves_tuple_return_shape():
    from main_web import _resolve_runtime_snapshot_source
    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=False)
    workspace = make_mock_workspace(active_scenario_id=None, saved_snapshot=None)

    result = _resolve_runtime_snapshot_source(
        user, project, workspace, "factory_base_runtime"
    )
    assert isinstance(result, tuple)
    assert len(result) == 4
    snapshot, scenario_record, warning, effective_origin = result
    assert isinstance(snapshot, dict)
    assert warning is None
    assert effective_origin == "factory_base_runtime"


# ─────────────────────────────────────────────────────────────────────────────
# Branch A1: saved_state + active_scenario_id + scenario unavailable
# ─────────────────────────────────────────────────────────────────────────────
def test_branch_a1_scenario_unavailable_via_service():
    from app.services.scenario_state_service import resolve_runtime_snapshot

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id="scen-999", saved_snapshot={"cap": 100})

    with patch('app.services.scenario_state_service.resolve_active_scenario_runtime_snapshot') as mock_resolve:
        mock_resolve.return_value = (None, None, None)
        result = resolve_runtime_snapshot(
            user=user, project_record=project,
            workspace_state=workspace, runtime_origin="saved_state"
        )

    assert result.scenario_record is None
    assert result.effective_runtime_origin == "workspace_base"  # KEY: override preserved
    assert "unavailable" in result.warning.lower()
    assert result.snapshot.get("cap") == 100
    assert result.snapshot.get("project_name") == "Test Project"


def test_branch_a1_override_preserved():
    """effective_runtime_origin changes from saved_state → workspace_base in A1 only."""
    from main_web import _resolve_runtime_snapshot_source

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id="scen-bad", saved_snapshot={"key": True})

    # A1: scenario unavailable
    with patch('app.services.scenario_state_service.resolve_active_scenario_runtime_snapshot') as mock_resolve:
        mock_resolve.return_value = (None, None, None)
        _, _, _, effective_origin = _resolve_runtime_snapshot_source(
            user, project, workspace, "saved_state"
        )
    assert effective_origin == "workspace_base"


# ─────────────────────────────────────────────────────────────────────────────
# Branch A2: saved_state + active_scenario_id + resolved_snapshot exists
# ─────────────────────────────────────────────────────────────────────────────
def test_branch_a2_resolved_snapshot_exists():
    from app.services.scenario_state_service import resolve_runtime_snapshot

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id="scen-123", saved_snapshot={"old": "value"})

    mock_scenario = MagicMock()

    with patch('app.services.scenario_state_service.resolve_active_scenario_runtime_snapshot') as mock_resolve:
        mock_resolve.return_value = (mock_scenario, {"capacity_mw": 72, "tariff_eur_mwh": 60}, None)
        result = resolve_runtime_snapshot(
            user=user, project_record=project,
            workspace_state=workspace, runtime_origin="saved_state"
        )

    assert result.scenario_record is mock_scenario
    assert result.effective_runtime_origin == "saved_state"
    assert result.warning is None
    assert result.snapshot.get("capacity_mw") == 72
    assert result.snapshot.get("tariff_eur_mwh") == 60
    assert result.snapshot.get("project_name") == "Test Project"


# ─────────────────────────────────────────────────────────────────────────────
# Branch A3: saved_state + active_scenario_id + scenario found but resolved_snapshot=None
# ─────────────────────────────────────────────────────────────────────────────
def test_branch_a3_resolved_snapshot_none_uses_saved_snapshot():
    from app.services.scenario_state_service import resolve_runtime_snapshot

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id="scen-456", saved_snapshot={"saved": "snapshot"})

    mock_scenario = MagicMock()

    with patch('app.services.scenario_state_service.resolve_active_scenario_runtime_snapshot') as mock_resolve:
        mock_resolve.return_value = (mock_scenario, None, None)
        result = resolve_runtime_snapshot(
            user=user, project_record=project,
            workspace_state=workspace, runtime_origin="saved_state"
        )

    assert result.scenario_record is mock_scenario
    assert result.effective_runtime_origin == "saved_state"
    assert result.snapshot.get("saved") == "snapshot"


def test_branch_a3_resolved_snapshot_none_no_saved_snapshot_uses_baseline():
    from app.services.scenario_state_service import resolve_runtime_snapshot

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id="scen-789", saved_snapshot=None)

    mock_scenario = MagicMock()

    with patch('app.services.scenario_state_service.resolve_active_scenario_runtime_snapshot') as mock_resolve:
        mock_resolve.return_value = (mock_scenario, None, None)
        result = resolve_runtime_snapshot(
            user=user, project_record=project,
            workspace_state=workspace, runtime_origin="saved_state"
        )

    assert result.scenario_record is mock_scenario
    assert result.effective_runtime_origin == "saved_state"
    assert result.snapshot.get("capacity_mw") == 35
    assert result.snapshot.get("tariff_eur_mwh") == 55


# ─────────────────────────────────────────────────────────────────────────────
# Branch B: user_created behavior (fires regardless of runtime_origin)
# ─────────────────────────────────────────────────────────────────────────────
def test_branch_b1_user_created_saved_state():
    from app.services.scenario_state_service import resolve_runtime_snapshot

    user = make_mock_user()
    project = make_mock_project(project_origin="user_created", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id=None, saved_snapshot={"user": "snap"})

    result = resolve_runtime_snapshot(
        user=user, project_record=project,
        workspace_state=workspace, runtime_origin="saved_state"
    )

    assert result.scenario_record is None
    assert result.effective_runtime_origin == "saved_state"
    assert result.snapshot.get("user") == "snap"


def test_branch_b2_user_created_not_saved_state():
    from app.services.scenario_state_service import resolve_runtime_snapshot

    user = make_mock_user()
    project = make_mock_project(project_origin="user_created", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id=None, saved_snapshot=None)

    result = resolve_runtime_snapshot(
        user=user, project_record=project,
        workspace_state=workspace, runtime_origin="workspace_base"
    )

    assert result.scenario_record is None
    assert result.effective_runtime_origin == "workspace_base"
    # B2 fallback: baseline first
    assert result.snapshot.get("capacity_mw") == 35


def test_branch_b_fires_regardless_of_runtime_origin():
    """user_created branch fires for any runtime_origin value."""
    from app.services.scenario_state_service import resolve_runtime_snapshot

    user = make_mock_user()
    project = make_mock_project(project_origin="user_created", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id=None, saved_snapshot=None)

    for origin in ["saved_state", "workspace_base", "factory_base_runtime", "preview_only"]:
        result = resolve_runtime_snapshot(
            user=user, project_record=project,
            workspace_state=workspace, runtime_origin=origin
        )
        # Should never reach Branch A (which would call resolve_active_scenario_runtime_snapshot)
        # For user_created, we should get scenario_record=None (not a MagicMock from A branch)
        assert result.scenario_record is None, f"origin={origin} should be Branch B"


# ─────────────────────────────────────────────────────────────────────────────
# Branch C: fallback
# ─────────────────────────────────────────────────────────────────────────────
def test_branch_c_saved_state_no_active_scenario():
    from app.services.scenario_state_service import resolve_runtime_snapshot

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id=None, saved_snapshot={"p50_hours": 2500})

    result = resolve_runtime_snapshot(
        user=user, project_record=project,
        workspace_state=workspace, runtime_origin="saved_state"
    )

    assert result.scenario_record is None
    assert result.effective_runtime_origin == "saved_state"
    assert result.snapshot.get("p50_hours") == 2500


def test_branch_c_no_snapshots_has_setdefault_fields():
    from app.services.scenario_state_service import resolve_runtime_snapshot

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=False)
    workspace = make_mock_workspace(active_scenario_id=None, saved_snapshot=None)

    result = resolve_runtime_snapshot(
        user=user, project_record=project,
        workspace_state=workspace, runtime_origin="saved_state"
    )

    assert result.scenario_record is None
    assert result.effective_runtime_origin == "saved_state"
    assert result.snapshot.get("project_name") == "Test Project"
    assert result.snapshot.get("project_type") == "Wind"
    assert result.snapshot.get("project_origin") == "saved_state"
    assert result.snapshot.get("template_source") == "tuho"
    assert result.snapshot.get("active_project") == "tuho"


def test_branch_workspace_base():
    from app.services.scenario_state_service import resolve_runtime_snapshot

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id=None, saved_snapshot={"ws": "snap"})

    result = resolve_runtime_snapshot(
        user=user, project_record=project,
        workspace_state=workspace, runtime_origin="workspace_base"
    )

    assert result.effective_runtime_origin == "workspace_base"
    assert result.snapshot.get("ws") == "snap"


# ─────────────────────────────────────────────────────────────────────────────
# Repository call only in Branch A
# ─────────────────────────────────────────────────────────────────────────────
def test_repository_call_only_in_branch_a():
    from app.services.scenario_state_service import resolve_runtime_snapshot

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=False)
    workspace = make_mock_workspace(active_scenario_id=None, saved_snapshot=None)

    # Branch C: should NOT call repository
    with patch('app.services.scenario_state_service.resolve_active_scenario_runtime_snapshot') as mock_resolve:
        resolve_runtime_snapshot(
            user=user, project_record=project,
            workspace_state=workspace, runtime_origin="saved_state"
        )
        mock_resolve.assert_not_called()

    # Branch B: should NOT call repository
    project_uc = make_mock_project(project_origin="user_created", has_baseline=False)
    workspace_uc = make_mock_workspace(active_scenario_id=None, saved_snapshot=None)
    with patch('app.services.scenario_state_service.resolve_active_scenario_runtime_snapshot') as mock_resolve:
        resolve_runtime_snapshot(
            user=user, project_record=project_uc,
            workspace_state=workspace_uc, runtime_origin="saved_state"
        )
        mock_resolve.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# All 5 setdefault fields always applied
# ─────────────────────────────────────────────────────────────────────────────
def test_all_five_setdefault_fields_added():
    from app.services.scenario_state_service import resolve_runtime_snapshot

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=False)
    workspace = make_mock_workspace(active_scenario_id=None, saved_snapshot=None)

    result = resolve_runtime_snapshot(
        user=user, project_record=project,
        workspace_state=workspace, runtime_origin="workspace_base"
    )

    assert "project_name" in result.snapshot
    assert "project_type" in result.snapshot
    assert "project_origin" in result.snapshot
    assert "template_source" in result.snapshot
    assert "active_project" in result.snapshot


# ─────────────────────────────────────────────────────────────────────────────
# scenario_record returned only in Branch A
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_record_none_for_non_a_branches():
    from app.services.scenario_state_service import resolve_runtime_snapshot

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id=None, saved_snapshot={"key": True})

    for origin in ["saved_state", "workspace_base", "factory_base_runtime", "preview_only"]:
        result = resolve_runtime_snapshot(
            user=user, project_record=project,
            workspace_state=workspace, runtime_origin=origin
        )
        assert result.scenario_record is None, f"origin={origin} should give scenario_record=None"


# ─────────────────────────────────────────────────────────────────────────────
# Warning behavior preserved
# ─────────────────────────────────────────────────────────────────────────────
def test_warning_from_resolver_forwarded():
    from app.services.scenario_state_service import resolve_runtime_snapshot

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=False)
    workspace = make_mock_workspace(active_scenario_id="scen-warning", saved_snapshot={"snap": True})
    mock_scenario = MagicMock()
    custom_warning = "Scenario locked by another user"

    with patch('app.services.scenario_state_service.resolve_active_scenario_runtime_snapshot') as mock_resolve:
        mock_resolve.return_value = (mock_scenario, None, custom_warning)
        result = resolve_runtime_snapshot(
            user=user, project_record=project,
            workspace_state=workspace, runtime_origin="saved_state"
        )

    assert result.warning == custom_warning
    assert result.effective_runtime_origin == "saved_state"


def test_a1_fallback_warning_when_resolver_returns_none():
    from app.services.scenario_state_service import resolve_runtime_snapshot

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id="scen-gone", saved_snapshot={"fallback": True})

    with patch('app.services.scenario_state_service.resolve_active_scenario_runtime_snapshot') as mock_resolve:
        mock_resolve.return_value = (None, None, None)
        result = resolve_runtime_snapshot(
            user=user, project_record=project,
            workspace_state=workspace, runtime_origin="saved_state"
        )

    assert result.effective_runtime_origin == "workspace_base"
    assert "unavailable" in result.warning.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Routes unchanged — call sites still use wrapper (thin wrapper in main_web.py)
# ─────────────────────────────────────────────────────────────────────────────
def test_run_route_still_uses_resolver_wrapper():
    text = MAIN_WEB.read_text()
    run_start = text.find('@app.post("/run")')
    run_end = text.find('\n@', run_start + 1)
    run_section = text[run_start:run_end]
    assert "_resolve_runtime_snapshot_source" in run_section
    assert "runtime_guard_for_snapshot" in run_section


def test_post_download_route_still_uses_resolver_wrapper():
    text = MAIN_WEB.read_text()
    dl_start = text.find('@app.post("/download")')
    dl_end = text.find('@app.get("/download")', dl_start)
    dl_section = text[dl_start:dl_end]
    assert "_resolve_runtime_snapshot_source" in dl_section


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
# resolve_active_scenario_runtime_snapshot no longer imported in main_web.py
# ─────────────────────────────────────────────────────────────────────────────
def test_resolver_no_longer_imported_in_main_web():
    text = MAIN_WEB.read_text()
    # Should NOT appear as an import
    lines_with_import = [l for l in text.split('\n') if 'resolve_active_scenario_runtime_snapshot' in l and 'import' in l]
    assert len(lines_with_import) == 0, f"Still imported in main_web: {lines_with_import}"


# ─────────────────────────────────────────────────────────────────────────────
# Service __init__.py exports RuntimeSnapshotResolution and resolve_runtime_snapshot
# ─────────────────────────────────────────────────────────────────────────────
def test_services_init_exports_resolver():
    from app.services import resolve_runtime_snapshot, RuntimeSnapshotResolution
    assert callable(resolve_runtime_snapshot)
    assert issubclass(RuntimeSnapshotResolution, tuple) or hasattr(RuntimeSnapshotResolution, "__dataclass_fields__")