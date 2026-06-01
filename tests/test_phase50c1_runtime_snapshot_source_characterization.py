"""Phase 50C-1 — Runtime Snapshot Source Resolver Characterization Tests.

Characterization only. _resolve_runtime_snapshot_source stays in main_web.py.
No production behavior changes.
"""
from pathlib import Path
import re
from unittest.mock import MagicMock, patch

import pytest

BASE_SHA = "dd6124814ccdcd9a36486c3909acd91f9446dca3"
MAIN_WEB = Path("main_web.py")
SCENARIO_SERVICE = Path("app/services/scenario_state_service.py")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: main_web imports cleanly
# ─────────────────────────────────────────────────────────────────────────────
def test_main_web_imports_cleanly():
    import main_web
    assert hasattr(main_web, 'app')


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: _resolve_runtime_snapshot_source exists in main_web.py
# ─────────────────────────────────────────────────────────────────────────────
def test_resolve_runtime_snapshot_source_exists():
    text = MAIN_WEB.read_text()
    assert "def _resolve_runtime_snapshot_source" in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: scenario_state_service does NOT yet own the resolver
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_service_exists_no_resolver():
    assert SCENARIO_SERVICE.exists()
    text = SCENARIO_SERVICE.read_text()
    assert "def resolve_runtime_snapshot" not in text
    assert "def _resolve_runtime_snapshot_source" not in text


# ─────────────────────────────────────────────────────────────────────────────
# Helper: build mock objects
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
    ws = MagicMock()
    ws.active_scenario_id = active_scenario_id
    ws.saved_snapshot = saved_snapshot
    return ws


# ─────────────────────────────────────────────────────────────────────────────
# Branch A1: saved_state + active_scenario_id + scenario_record None
# ─────────────────────────────────────────────────────────────────────────────
def test_branch_a1_scenario_unavailable():
    from main_web import _resolve_runtime_snapshot_source

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id="scen-999", saved_snapshot={"cap": 100})

    with patch('main_web.resolve_active_scenario_runtime_snapshot') as mock_resolve:
        mock_resolve.return_value = (None, None, None)
        snapshot, scenario_record, warning, effective_origin = _resolve_runtime_snapshot_source(
            user, project, workspace, "saved_state"
        )

    assert scenario_record is None
    assert effective_origin == "workspace_base", f"Expected workspace_base, got {effective_origin}"
    assert "unavailable" in warning.lower()
    # Verify content (setdefault adds 5 fields to every snapshot)
    assert snapshot.get("cap") == 100
    assert snapshot.get("project_name") == "Test Project"


# ─────────────────────────────────────────────────────────────────────────────
# Branch A2: saved_state + active_scenario_id + scenario_record found + resolved_snapshot exists
# ─────────────────────────────────────────────────────────────────────────────
def test_branch_a2_resolved_snapshot_exists():
    from main_web import _resolve_runtime_snapshot_source

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id="scen-123", saved_snapshot={"old": "value"})

    mock_scenario = MagicMock()
    mock_resolved = {"capacity_mw": 72, "tariff_eur_mwh": 60}

    with patch('main_web.resolve_active_scenario_runtime_snapshot') as mock_resolve:
        mock_resolve.return_value = (mock_scenario, mock_resolved, None)
        snapshot, scenario_record, warning, effective_origin = _resolve_runtime_snapshot_source(
            user, project, workspace, "saved_state"
        )

    assert scenario_record is mock_scenario
    assert effective_origin == "saved_state"
    assert warning is None
    assert snapshot.get("capacity_mw") == 72
    assert snapshot.get("tariff_eur_mwh") == 60
    assert snapshot.get("project_name") == "Test Project"
    assert snapshot.get("project_type") == "Wind"


# ─────────────────────────────────────────────────────────────────────────────
# Branch A3: saved_state + active_scenario_id + scenario_record found + resolved_snapshot None
# ─────────────────────────────────────────────────────────────────────────────
def test_branch_a3_resolved_snapshot_none():
    from main_web import _resolve_runtime_snapshot_source

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id="scen-456", saved_snapshot={"saved": "snapshot"})

    mock_scenario = MagicMock()

    with patch('main_web.resolve_active_scenario_runtime_snapshot') as mock_resolve:
        mock_resolve.return_value = (mock_scenario, None, None)
        snapshot, scenario_record, warning, effective_origin = _resolve_runtime_snapshot_source(
            user, project, workspace, "saved_state"
        )

    assert scenario_record is mock_scenario
    assert effective_origin == "saved_state"
    # Falls to saved_snapshot (not baseline) in A3 when resolved_snapshot is None
    assert snapshot.get("saved") == "snapshot"
    assert snapshot.get("project_name") == "Test Project"


# ─────────────────────────────────────────────────────────────────────────────
# Branch A3 fallback: saved_state + active_scenario_id + no saved_snapshot → baseline
# ─────────────────────────────────────────────────────────────────────────────
def test_branch_a3_fallback_to_baseline():
    from main_web import _resolve_runtime_snapshot_source

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id="scen-789", saved_snapshot=None)

    mock_scenario = MagicMock()

    with patch('main_web.resolve_active_scenario_runtime_snapshot') as mock_resolve:
        mock_resolve.return_value = (mock_scenario, None, None)
        snapshot, scenario_record, warning, effective_origin = _resolve_runtime_snapshot_source(
            user, project, workspace, "saved_state"
        )

    assert scenario_record is mock_scenario
    assert effective_origin == "saved_state"
    assert snapshot.get("capacity_mw") == 35
    assert snapshot.get("tariff_eur_mwh") == 55


# ─────────────────────────────────────────────────────────────────────────────
# Branch C: saved_state + NO active_scenario_id + saved_snapshot exists
# ─────────────────────────────────────────────────────────────────────────────
def test_branch_c_saved_state_no_active_scenario():
    from main_web import _resolve_runtime_snapshot_source

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id=None, saved_snapshot={"p50_hours": 2500})

    snapshot, scenario_record, warning, effective_origin = _resolve_runtime_snapshot_source(
        user, project, workspace, "saved_state"
    )

    assert scenario_record is None
    assert effective_origin == "saved_state"
    assert warning is None
    assert snapshot.get("p50_hours") == 2500
    assert snapshot.get("project_name") == "Test Project"


# ─────────────────────────────────────────────────────────────────────────────
# Branch C: saved_state + no active_scenario_id + no saved_snapshot + baseline
# Note: "empty" means source={} before setdefault; after setdefault dict always has 5 fields
# ─────────────────────────────────────────────────────────────────────────────
def test_branch_c_no_snapshots_has_setdefault_fields():
    from main_web import _resolve_runtime_snapshot_source

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=False)
    workspace = make_mock_workspace(active_scenario_id=None, saved_snapshot=None)

    snapshot, scenario_record, warning, effective_origin = _resolve_runtime_snapshot_source(
        user, project, workspace, "saved_state"
    )

    assert scenario_record is None
    assert effective_origin == "saved_state"
    assert warning is None
    # setdefault always adds these fields even when source is {}
    assert snapshot.get("project_name") == "Test Project"
    assert snapshot.get("project_type") == "Wind"
    assert snapshot.get("project_origin") == "saved_state"
    assert snapshot.get("template_source") == "tuho"
    assert snapshot.get("active_project") == "tuho"
    # No user-provided keys
    assert "capacity_mw" not in snapshot


# ─────────────────────────────────────────────────────────────────────────────
# Branch B1: user_created + saved_state + saved_snapshot (NO active_scenario_id → A skipped)
# ─────────────────────────────────────────────────────────────────────────────
def test_branch_b1_user_created_saved_state():
    from main_web import _resolve_runtime_snapshot_source

    user = make_mock_user()
    project = make_mock_project(project_origin="user_created", has_baseline=True)
    # No active_scenario_id → Branch A is skipped, Branch B fires
    workspace = make_mock_workspace(active_scenario_id=None, saved_snapshot={"user": "snap"})

    snapshot, scenario_record, warning, effective_origin = _resolve_runtime_snapshot_source(
        user, project, workspace, "saved_state"
    )

    assert scenario_record is None
    assert effective_origin == "saved_state"
    assert warning is None
    assert snapshot.get("user") == "snap"
    assert snapshot.get("project_origin") == "user_created"


# ─────────────────────────────────────────────────────────────────────────────
# Branch B2: user_created + NOT saved_state + baseline_snapshot
# ─────────────────────────────────────────────────────────────────────────────
def test_branch_b2_user_created_not_saved_state():
    from main_web import _resolve_runtime_snapshot_source

    user = make_mock_user()
    project = make_mock_project(project_origin="user_created", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id=None, saved_snapshot=None)

    snapshot, scenario_record, warning, effective_origin = _resolve_runtime_snapshot_source(
        user, project, workspace, "workspace_base"
    )

    assert scenario_record is None
    assert effective_origin == "workspace_base"
    assert warning is None
    # B2 fallback: baseline_snapshot OR saved_snapshot
    assert snapshot.get("capacity_mw") == 35
    assert snapshot.get("tariff_eur_mwh") == 55


# ─────────────────────────────────────────────────────────────────────────────
# Branch B2: user_created + saved_state but no saved_snapshot → baseline first
# ─────────────────────────────────────────────────────────────────────────────
def test_branch_b2_user_created_saved_state_no_snapshot():
    from main_web import _resolve_runtime_snapshot_source

    user = make_mock_user()
    project = make_mock_project(project_origin="user_created", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id=None, saved_snapshot=None)

    # B1 condition fails (no saved_snapshot), B2 uses baseline
    snapshot, scenario_record, warning, effective_origin = _resolve_runtime_snapshot_source(
        user, project, workspace, "saved_state"
    )

    assert scenario_record is None
    assert effective_origin == "saved_state"
    assert snapshot.get("capacity_mw") == 35
    assert snapshot.get("tariff_eur_mwh") == 55


# ─────────────────────────────────────────────────────────────────────────────
# Branch B: fallback order is baseline FIRST, not saved_snapshot first
# ─────────────────────────────────────────────────────────────────────────────
def test_branch_b_fallback_order_user_created():
    from main_web import _resolve_runtime_snapshot_source

    user = make_mock_user()
    project = make_mock_project(project_origin="user_created", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id=None, saved_snapshot=None)

    snapshot, scenario_record, warning, effective_origin = _resolve_runtime_snapshot_source(
        user, project, workspace, "saved_state"
    )

    # B2: baseline_snapshot OR saved_snapshot (baseline first!)
    assert snapshot.get("capacity_mw") == 35
    assert snapshot.get("tariff_eur_mwh") == 55


# ─────────────────────────────────────────────────────────────────────────────
# Branch C: workspace_base
# ─────────────────────────────────────────────────────────────────────────────
def test_branch_workspace_base():
    from main_web import _resolve_runtime_snapshot_source

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id=None, saved_snapshot={"ws": "snap"})

    snapshot, scenario_record, warning, effective_origin = _resolve_runtime_snapshot_source(
        user, project, workspace, "workspace_base"
    )

    assert scenario_record is None
    assert effective_origin == "workspace_base"
    assert snapshot.get("ws") == "snap"


# ─────────────────────────────────────────────────────────────────────────────
# Branch: factory_base_runtime
# ─────────────────────────────────────────────────────────────────────────────
def test_branch_factory_base_runtime():
    from main_web import _resolve_runtime_snapshot_source

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=False)
    workspace = make_mock_workspace(active_scenario_id=None, saved_snapshot=None)

    snapshot, scenario_record, warning, effective_origin = _resolve_runtime_snapshot_source(
        user, project, workspace, "factory_base_runtime"
    )

    assert scenario_record is None
    assert effective_origin == "factory_base_runtime"
    # setdefault fields present
    assert snapshot.get("project_name") == "Test Project"
    assert "capacity_mw" not in snapshot


# ─────────────────────────────────────────────────────────────────────────────
# Branch: preview_only
# ─────────────────────────────────────────────────────────────────────────────
def test_branch_preview_only():
    from main_web import _resolve_runtime_snapshot_source

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id=None, saved_snapshot={"preview": True})

    snapshot, scenario_record, warning, effective_origin = _resolve_runtime_snapshot_source(
        user, project, workspace, "preview_only"
    )

    assert scenario_record is None
    assert effective_origin == "preview_only"
    assert snapshot.get("preview") is True


# ─────────────────────────────────────────────────────────────────────────────
# Snapshot post-processing: all 5 setdefault fields always applied
# ─────────────────────────────────────────────────────────────────────────────
def test_snapshot_post_processing_applies():
    from main_web import _resolve_runtime_snapshot_source

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id=None, saved_snapshot={"some_key": "value"})

    snapshot, scenario_record, warning, effective_origin = _resolve_runtime_snapshot_source(
        user, project, workspace, "workspace_base"
    )

    assert snapshot.get("project_name") == "Test Project"
    assert snapshot.get("project_type") == "Wind"
    assert snapshot.get("project_origin") == "saved_state"
    assert snapshot.get("template_source") == "tuho"
    assert snapshot.get("active_project") == "tuho"


# ─────────────────────────────────────────────────────────────────────────────
# Repository helper called ONLY for saved_state + active_scenario_id (Branch A)
# ─────────────────────────────────────────────────────────────────────────────
def test_repository_call_only_in_branch_a():
    from main_web import _resolve_runtime_snapshot_source

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=False)
    workspace_no_snap = make_mock_workspace(active_scenario_id=None, saved_snapshot=None)

    with patch('main_web.resolve_active_scenario_runtime_snapshot') as mock_resolve:
        _resolve_runtime_snapshot_source(user, project, workspace_no_snap, "saved_state")
        mock_resolve.assert_not_called()

    project_uc = make_mock_project(project_origin="user_created", has_baseline=False)
    workspace_uc = make_mock_workspace(active_scenario_id=None, saved_snapshot=None)
    with patch('main_web.resolve_active_scenario_runtime_snapshot') as mock_resolve:
        _resolve_runtime_snapshot_source(user, project_uc, workspace_uc, "saved_state")
        mock_resolve.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# scenario_record is None for all non-A branches
# ─────────────────────────────────────────────────────────────────────────────
def test_scenario_record_none_when_not_resolved():
    from main_web import _resolve_runtime_snapshot_source

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id=None, saved_snapshot={"snap": True})

    for origin in ["saved_state", "workspace_base", "factory_base_runtime", "preview_only"]:
        _, scenario_record, _, _ = _resolve_runtime_snapshot_source(
            user, project, workspace, origin
        )
        assert scenario_record is None, f"origin={origin} should have scenario_record=None"


# ─────────────────────────────────────────────────────────────────────────────
# user_created branch fires first (Branch B takes priority over Branch A for user_created projects)
# ─────────────────────────────────────────────────────────────────────────────
def test_user_created_priority_over_branch_a():
    """
    For user_created projects, Branch B fires regardless of runtime_origin.
    Branch A (saved_state+active_scenario_id) is checked first BUT user_created
    branch comes after A in elif chain, and since A requires runtime_origin==saved_state
    AND active_scenario_id, the combination of user_created + active_scenario_id
    DOES reach Branch A (not B) because the if/elif chain checks runtime_origin first.

    Actually — let me verify: when project_origin=user_created AND runtime_origin=saved_state
    AND active_scenario_id is set → Branch A fires (A is checked first in if/elif chain)

    Correction from original test: user_created priority only means B fires for user_created
    when runtime_origin != 'saved_state' OR when saved_state but no active_scenario_id.
    When saved_state + active_scenario_id + user_created → Branch A fires.
    """
    from main_web import _resolve_runtime_snapshot_source

    user = make_mock_user()
    project_uc = make_mock_project(project_origin="user_created", has_baseline=True)
    # user_created + saved_state + active_scenario_id → Branch A fires (B is elif after A)
    workspace = make_mock_workspace(active_scenario_id="scen-active", saved_snapshot={"snap": "value"})

    with patch('main_web.resolve_active_scenario_runtime_snapshot') as mock_resolve:
        mock_resolve.return_value = (MagicMock(), {"user_key": "from_resolver"}, None)
        snapshot, scenario_record, warning, effective_origin = _resolve_runtime_snapshot_source(
            user, project_uc, workspace, "saved_state"
        )
        # Branch A fires for user_created when runtime_origin=saved_state AND active_scenario_id set
        mock_resolve.assert_called_once()
        assert scenario_record is not None
        assert snapshot.get("user_key") == "from_resolver"


# ─────────────────────────────────────────────────────────────────────────────
# effective_runtime_origin override only in A1 (scenario unavailable)
# ─────────────────────────────────────────────────────────────────────────────
def test_effective_origin_override_only_in_scenario_unavailable():
    from main_web import _resolve_runtime_snapshot_source

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id="scen-bad", saved_snapshot={"snap": True})

    # A1: scenario unavailable → override to workspace_base
    with patch('main_web.resolve_active_scenario_runtime_snapshot') as mock_resolve:
        mock_resolve.return_value = (None, None, None)
        _, _, _, effective_origin = _resolve_runtime_snapshot_source(
            user, project, workspace, "saved_state"
        )
    assert effective_origin == "workspace_base", "Only A1 should override effective_origin"

    # A2: resolved_snapshot exists → should NOT override
    mock_scenario = MagicMock()
    with patch('main_web.resolve_active_scenario_runtime_snapshot') as mock_resolve:
        mock_resolve.return_value = (mock_scenario, {"key": "val"}, None)
        _, _, _, effective_origin = _resolve_runtime_snapshot_source(
            user, project, workspace, "saved_state"
        )
    assert effective_origin == "saved_state"

    # B1: should NOT override
    project_uc = make_mock_project(project_origin="user_created", has_baseline=True)
    workspace_uc = make_mock_workspace(active_scenario_id=None, saved_snapshot={"snap": "val"})
    _, _, _, effective_origin = _resolve_runtime_snapshot_source(
        user, project_uc, workspace_uc, "saved_state"
    )
    assert effective_origin == "saved_state"


# ─────────────────────────────────────────────────────────────────────────────
# Resolver remains in main_web.py
# ─────────────────────────────────────────────────────────────────────────────
def test_resolver_remains_in_main_web():
    text = MAIN_WEB.read_text()
    assert "def _resolve_runtime_snapshot_source" in text
    assert "resolve_active_scenario_runtime_snapshot" in text
    assert "effective_origin = runtime_origin" in text
    assert "workspace_base" in text


# ─────────────────────────────────────────────────────────────────────────────
# Routes unchanged by this phase
# ─────────────────────────────────────────────────────────────────────────────
def test_routes_unchanged():
    text = MAIN_WEB.read_text()
    run_start = text.find('@app.post("/run")')
    run_end = text.find('\n@', run_start + 1)
    run_section = text[run_start:run_end]
    assert "_resolve_runtime_snapshot_source" in run_section
    assert "runtime_guard_for_snapshot" in run_section
    dl_start = text.find('@app.post("/download")')
    dl_end = text.find('@app.get("/download")', dl_start)
    dl_section = text[dl_start:dl_end]
    assert "_resolve_runtime_snapshot_source" in dl_section


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
# Warning from resolver forwarded as-is
# ─────────────────────────────────────────────────────────────────────────────
def test_warning_from_resolver_forwarded():
    from main_web import _resolve_runtime_snapshot_source

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=False)
    workspace = make_mock_workspace(active_scenario_id="scen-warning", saved_snapshot={"snap": True})
    mock_scenario = MagicMock()
    custom_warning = "Scenario locked by another user"

    with patch('main_web.resolve_active_scenario_runtime_snapshot') as mock_resolve:
        mock_resolve.return_value = (mock_scenario, None, custom_warning)
        _, _, warning, effective_origin = _resolve_runtime_snapshot_source(
            user, project, workspace, "saved_state"
        )

    assert warning == custom_warning
    assert effective_origin == "saved_state"


# ─────────────────────────────────────────────────────────────────────────────
# A1 fallback warning when resolver returns None
# ─────────────────────────────────────────────────────────────────────────────
def test_a1_fallback_warning_when_resolver_returns_none():
    from main_web import _resolve_runtime_snapshot_source

    user = make_mock_user()
    project = make_mock_project(project_origin="saved_state", has_baseline=True)
    workspace = make_mock_workspace(active_scenario_id="scen-gone", saved_snapshot={"fallback": True})

    with patch('main_web.resolve_active_scenario_runtime_snapshot') as mock_resolve:
        mock_resolve.return_value = (None, None, None)
        _, _, warning, effective_origin = _resolve_runtime_snapshot_source(
            user, project, workspace, "saved_state"
        )

    assert effective_origin == "workspace_base"
    assert "unavailable" in warning.lower()