"""Phase A3 - Lifecycle clarity.

Read-only UX/state labelling only:
- no runtime behavior changes
- no model changes
- no formula changes
- no persistence/export/schema changes
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest import mock

from app.api.project_runner import run_project
from app.ui.runtime_summary import runtime_summary_to_dict
from tests.test_phase21_template_render import make_project_ctx, make_scenario_records


def _render(name: str, ctx: dict) -> str:
    import main_web

    template = main_web.templates.env.get_template(name)
    return template.render(ctx)


def _workspace_state(*, dirty: bool, active_scenario_name: str = "Base Case", runtime_origin: str = "saved_state"):
    return SimpleNamespace(
        active_scenario_name=active_scenario_name,
        active_scenario_id="sc_test_001",
        dirty=dirty,
        last_runtime_origin=runtime_origin,
        last_runtime_snapshot_id="snap_test_12345678",
        updated_at=datetime(2026, 6, 7, 10, 15, 0),
        last_runtime_at=datetime(2026, 6, 7, 9, 45, 0),
    )


def _workspace_state_meta(*, dirty: bool, runtime_label: str = "Runtime bound to saved scenario snapshot") -> dict:
    return {
        "dirty": dirty,
        "dirty_label": "Unsaved edits" if dirty else "Clean saved state",
        "active_scenario_id": "sc_test_001",
        "active_scenario_name": "Base Case",
        "last_runtime_origin": "saved_state",
        "last_runtime_origin_label": (
            f"{runtime_label} (older than current draft)" if dirty else runtime_label
        ),
        "last_runtime_snapshot_id": "snap_test_12345678",
    }


def _runtime_summary_stub(*, scenario_name: str = "Base Case") -> SimpleNamespace:
    return SimpleNamespace(
        project_name="TUHO Wind 1",
        active_scenario_name=scenario_name,
    )


def _export_lineage_ui(*, dirty: bool) -> dict:
    action_note = (
        "Unsaved draft edits are active. Exports remain descriptive only, and runtime-backed artifacts stay tied to the last clean backend snapshot until you save and run again."
        if dirty
        else "Draft and saved state are aligned. Runtime-backed exports reflect the last clean backend snapshot shown in the runtime summary."
    )
    return {
        "recent_exports": [],
        "current_context": {
            "project_label": "TUHO Wind 1",
            "project_code": "TUHO",
            "active_scenario_name": "Base Case",
            "active_scenario_id": "sc_test_001",
            "scenario_revision": "2026-06-07 10:15",
            "runtime_snapshot_id": "snap_test_12345678",
            "runtime_origin_label": "Runtime bound to saved scenario snapshot",
            "runtime_generated_at": "2026-06-07 09:45",
            "dirty_label": "Unsaved edits" if dirty else "Clean saved state",
            "action_note": action_note,
        },
    }


def _workspace_shell_context(*, is_user_project: bool, dirty: bool) -> dict:
    return {
        "project_ctx": make_project_ctx(data_source="User Project" if is_user_project else "Factory Reference"),
        "workspace_state": _workspace_state(dirty=dirty),
        "export_lineage_ui": _export_lineage_ui(dirty=dirty),
        "runtime_summary": _runtime_summary_stub(),
        "project_record": mock.MagicMock(
            project_code="tuho",
            project_name="TUHO Wind 1",
            project_type="Wind",
            project_origin="user_created" if is_user_project else "tuho",
            baseline_snapshot=None,
        ),
        "scenario_records": make_scenario_records(),
        "scenario_history": [],
        "export_records": [],
        "compare_result": None,
        "workspace_message": None,
        "workspace_state_meta": _workspace_state_meta(dirty=dirty),
        "scenario_summary_cards": [],
        "validation_errors": [],
        "success_message": None,
        "user": mock.MagicMock(user_id="test_user", username="tester"),
        "form_data": {
            "template_source": "" if is_user_project else "tuho",
            "project_origin": "user_created" if is_user_project else "tuho",
            "project_name": "TUHO Wind 1",
        },
        "active_project_code": "tuho",
        "is_user_project": is_user_project,
        "base_case_record": make_scenario_records()[0],
        "non_base_scenarios": [],
        "scenario_editable_fields": [],
        "factory_template_projects": [],
        "user_project_records": [],
        "baseline_project_records": [],
        "new_project_template_options": [],
        "project_types": [],
    }


class TestLifecycleClarityRendering:
    def test_runtime_summary_source_label_renders_from_backend_summary(self):
        result = run_project("TUHO", "Base")
        summary = runtime_summary_to_dict(result, "tuho", "TUHO Wind 1")
        html = _render(
            "partials/runtime_summary.html",
            {
                "runtime_summary": summary,
                "workspace_state": _workspace_state(dirty=True),
                "messages": [],
            },
        )

        assert "Runtime summary reflects the last completed run." in html
        assert "Only backend-authoritative runtime results are shown here for the project and scenario named above." in html
        assert "Unsaved changes may require Save/Run before outputs are current." in html

    def test_workspace_shell_renders_user_created_project_runtime_and_export_copy(self):
        html = _render("partials/workspace_shell.html", _workspace_shell_context(is_user_project=True, dirty=True))

        assert "Lifecycle Clarity" in html
        assert "User-created project" in html
        assert "Runtime summary reflects the last completed run." in html
        assert "Export workbook is generated from backend-authoritative saved/run state." in html
        assert "Export is an audit output, not a free-form Excel model." in html
        assert "Unsaved changes may require Save/Run before outputs are current." in html

    def test_workspace_shell_renders_factory_reference_label_and_read_only_copy(self):
        html = _render("partials/workspace_shell.html", _workspace_shell_context(is_user_project=False, dirty=False))

        assert "Factory template" in html
        assert "Factory reference" in html
        assert "Factory references are read-only. Duplicate or Save As before editing controlled assumptions." in html

    def test_lifecycle_copy_does_not_introduce_fake_runtime_id_or_export_timestamp(self):
        html = _render("partials/workspace_shell.html", _workspace_shell_context(is_user_project=True, dirty=False))

        assert "Runtime ID" not in html
        assert "Export timestamp" not in html
        assert "free-form Excel model" in html

    def test_existing_validation_and_runtime_boundary_copy_remains_visible(self):
        html = _render("partials/workspace_shell.html", _workspace_shell_context(is_user_project=True, dirty=True))

        assert "Review boundary:" in html
        assert "Runtime cards and exported outputs reflect the last clean backend run" in html
        assert "Governance Status" in html
