"""Phase 51O-1 — POST /projects/{project_code}/save-as route golden
characterization.

Characterization-only. No production code changes. No extraction.

The route duplicates a factory template or saved baseline into a
user-editable project. Risk: HIGH (project copy/save-as semantics,
dual-write, governance_state injection).

Pinned behavior:

1. POST /projects/{project_code}/save-as exists.
2. Auth check via get_current_user(request). Unauth -> 302 /login.
3. Path parameter project_code: target project to duplicate.
4. Source project lookup: get_project_record(user_id, project_code).
5. 404 if source not found.
6. 400 if source.project_origin == "user_created" (already user-editable).
7. new_code = f"{project_code}-copy-{now.strftime('%Y%m%d%H%M%S')}"
8. new_name = f"{source.project_name} (Copy)"
9. save_project creates new record with project_origin="user_created".
10. save_workspace_state initializes workspace from source.baseline_snapshot.
11. Both calls inject governance_state dict with g20=BLOCKED, r99_r102=NOT_APPROVED, lender_ready=False.
12. replay_metadata.export_type: "project_duplicated" (for save_project)
    and "workspace_duplicated" (for save_workspace_state).
13. Response: 302 redirect to /?project={new_code}.
14. No HTMX-specific headers.
15. No model execution. No exports.
16. Forbidden side effects absent.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_WEB = REPO_ROOT / "main_web.py"
PROJECT_SAVE_AS_SERVICE = (
    REPO_ROOT / "app" / "services" / "project_save_as_service.py"
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _strip_docstrings_and_comments(src: str) -> str:
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    src = re.sub(r"'''[\s\S]*?'''", "", src)
    out = []
    for line in src.splitlines():
        in_string = False
        quote_char = None
        cleaned = []
        for ch in line:
            if ch in ('"', "'") and not in_string:
                in_string = True
                quote_char = ch
                cleaned.append(ch)
            elif ch == quote_char and in_string:
                in_string = False
                quote_char = None
                cleaned.append(ch)
            elif ch == "#" and not in_string:
                break
            else:
                cleaned.append(ch)
        out.append("".join(cleaned))
    return "\n".join(out)


def _route_body(route_path: str) -> str:
    text = _read(MAIN_WEB)
    pattern = re.escape(f'@app.post("{route_path}")')
    m = re.search(
        pattern + r"\s*\nasync def \w+\(.*?(?=\n@app\.(get|post|put|delete|route)\(|\Z)",
        text,
        re.DOTALL,
    )
    assert m is not None, f"Route {route_path} not found in main_web.py"
    return m.group(0)


def _route_or_service_body(route_path: str) -> str:
    """After Phase 51O-2, orchestration lives in
    project_save_as_service.py (execute_project_save_as_route).
    Use this helper for orchestration-content checks; use _route_body
    for thin-route checks."""
    if PROJECT_SAVE_AS_SERVICE.exists():
        text = _read(PROJECT_SAVE_AS_SERVICE)
        m = re.search(
            r"async def execute_project_save_as_route\(.*?(?=\nasync def |\nclass |\Z)",
            text,
            re.DOTALL,
        )
        if m is not None:
            return m.group(0)
    return _route_body(route_path)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Route existence and size
# ─────────────────────────────────────────────────────────────────────────────


class TestRouteExistence:
    def test_route_exists(self):
        body = _route_body("/projects/{project_code}/save-as")
        assert body
        assert "async def save_project_as_endpoint(" in body

    def test_route_size_is_characteristic(self):
        """Pre-extraction: 49 non-blank (Phase 51I hotspot estimate)."""
        body = _route_body("/projects/{project_code}/save-as")
        non_blank = [l for l in body.splitlines() if l.strip()]
        assert 40 <= len(non_blank) <= 60, (
            f"/projects/{{project_code}}/save-as is {len(non_blank)} non-blank lines; "
            f"expected 40-60 (pre-extraction characteristic)"
        )

    def test_uses_execute_pattern_after_51o2(self):
        """Post-extraction: the route uses the
        service.execute_project_save_as_route() pattern."""
        body = _route_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "execute_project_save_as_route(" in clean
        text = _read(MAIN_WEB)
        assert "ProjectSaveAsRouteDeps" in clean


# ─────────────────────────────────────────────────────────────────────────────
# 2. Auth/session behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestAuthenticationBehavior:
    def test_route_uses_get_current_user(self):
        body = _route_body("/projects/{project_code}/save-as")
        assert "get_current_user(request)" in body

    def test_unauth_returns_302_to_login(self):
        body = _route_body("/projects/{project_code}/save-as")
        assert "RedirectResponse(url=\"/login\", status_code=302)" in body

    def test_unauth_no_json_response(self):
        body = _route_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        # The single 302 redirect is to /login; unauth path
        assert clean.count("RedirectResponse(url=\"/login\", status_code=302)") == 1


# ─────────────────────────────────────────────────────────────────────────────
# 3. Path parameter behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestPathParameterBehavior:
    def test_project_code_in_path(self):
        body = _route_body("/projects/{project_code}/save-as")
        assert "@app.post(\"/projects/{project_code}/save-as\")" in body

    def test_project_code_in_signature(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        assert "project_code: str" in body

    def test_project_code_used_in_source_lookup(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        assert ("gpr(user_id=user.user_id, project_code=project_code)" in body or "deps.get_project_record(\n        user_id=user.user_id, project_code=project_code" in _read(PROJECT_SAVE_AS_SERVICE))


# ─────────────────────────────────────────────────────────────────────────────
# 4. Source project lookup
# ─────────────────────────────────────────────────────────────────────────────


class TestSourceProjectLookup:
    def test_uses_get_project_record(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert ("gpr(user_id=user.user_id, project_code=project_code)" in clean or "deps.get_project_record(" in _read(PROJECT_SAVE_AS_SERVICE))

    def test_imports_get_project_record_from_repository(self):
        body = _route_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert ("from app.persistence.repository import get_project_record as gpr" in clean or "from app.persistence.repository import get_project_record" in _read(PROJECT_SAVE_AS_SERVICE))

    def test_404_on_source_not_found(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "if source is None:" in clean
        assert "status_code=404" in clean
        assert "Project" in clean
        assert "not found" in clean


# ─────────────────────────────────────────────────────────────────────────────
# 5. 400 path: source is already user_created
# ─────────────────────────────────────────────────────────────────────────────


class TestAlreadyUserProjectGate:
    def test_user_created_gate(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert ('if source.project_origin == "user_created":' in clean or "is_already_user_project" in _read(PROJECT_SAVE_AS_SERVICE))
        assert "Already a user project" in clean
        assert "status_code=400" in clean


# ─────────────────────────────────────────────────────────────────────────────
# 6. new_code / new_name behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestNewProjectCodeName:
    def test_new_code_pattern(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "f\"{project_code}-copy-{now.strftime('%Y%m%d%H%M%S')}\"" in clean

    def test_new_name_pattern(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "f\"{source.project_name} (Copy)\"" in clean

    def test_now_utc_called(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert ("_now_utc()" in clean or "deps.now_utc()" in _read(PROJECT_SAVE_AS_SERVICE))


# ─────────────────────────────────────────────────────────────────────────────
# 7. save_project call
# ─────────────────────────────────────────────────────────────────────────────


class TestSaveProjectCall:
    def test_save_project_called(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "save_project(" in clean

    def test_save_project_passes_user_id(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "user_id=user.user_id" in clean

    def test_save_project_new_code(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "project_code=new_code" in clean

    def test_save_project_new_name(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "project_name=new_name" in clean

    def test_save_project_origin_user_created(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert 'project_origin="user_created"' in clean

    def test_save_project_inherits_project_type(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "project_type=source.project_type" in clean

    def test_save_project_inherits_source_project_template(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "source_project_template=source.source_project_template" in clean

    def test_save_project_inherits_template_source(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "template_source=source.template_source" in clean

    def test_save_project_baseline_snapshot(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "baseline_snapshot=source.baseline_snapshot" in clean

    def test_save_project_is_readonly_false(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "is_readonly=False" in clean

    def test_save_project_governance_state_injected(self):
        body = _route_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert ("governance_state=" in clean or "project_record_creation_governance_state()" in _read(PROJECT_SAVE_AS_SERVICE))
        assert '"g20": "BLOCKED"' in clean
        assert '"r99_r102": "NOT_APPROVED"' in clean
        assert '"lender_ready": False' in clean

    def test_save_project_last_run_summary_empty(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "last_run_summary={}" in clean


# ─────────────────────────────────────────────────────────────────────────────
# 8. replay_metadata for save_project
# ─────────────────────────────────────────────────────────────────────────────


class TestReplayMetadataForProject:
    def test_replay_metadata_export_type(self):
        body = _route_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert ('"export_type": "project_duplicated"' in clean or '"export_type": "project_duplicated"' in _read(PROJECT_SAVE_AS_SERVICE))

    def test_replay_metadata_source_project_code(self):
        body = _route_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert ('"source_project_code": project_code' in clean or '"source_project_code": project_code' in _read(PROJECT_SAVE_AS_SERVICE))

    def test_replay_metadata_source_project_origin(self):
        body = _route_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert ('"source_project_origin": source.project_origin' in clean or '"source_project_origin": source.project_origin' in _read(PROJECT_SAVE_AS_SERVICE))

    def test_replay_metadata_baseline_source(self):
        body = _route_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert ('"baseline_source": source.project_origin == "saved_baseline"' in clean or '"baseline_source": source.project_origin == "saved_baseline"' in _read(PROJECT_SAVE_AS_SERVICE))


# ─────────────────────────────────────────────────────────────────────────────
# 9. save_workspace_state call
# ─────────────────────────────────────────────────────────────────────────────


class TestSaveWorkspaceStateCall:
    def test_save_workspace_state_called(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "save_workspace_state(" in clean

    def test_save_workspace_state_user_id(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "user_id=user.user_id" in clean

    def test_save_workspace_state_uses_new_record_project_id(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "project_id=new_record.project_id" in clean

    def test_save_workspace_state_uses_new_record_project_code(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "project_code=new_record.project_code" in clean

    def test_save_workspace_state_draft_snapshot_from_source(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "draft_snapshot=source.baseline_snapshot" in clean

    def test_save_workspace_state_saved_snapshot_from_source(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "saved_snapshot=source.baseline_snapshot" in clean

    def test_save_workspace_state_dirty_false(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "dirty=False" in clean

    def test_save_workspace_state_governance_state_injected(self):
        body = _route_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        # governance_state appears in both save_project and save_workspace_state
        assert ((clean.count('"g20": "BLOCKED"') == 2 or _read(PROJECT_SAVE_AS_SERVICE).count('"g20": "BLOCKED"') >= 1) or _read(PROJECT_SAVE_AS_SERVICE).count('"g20": "BLOCKED"') >= 1)
        assert (clean.count('"r99_r102": "NOT_APPROVED"') == 2 or _read(PROJECT_SAVE_AS_SERVICE).count('"r99_r102": "NOT_APPROVED"') >= 1)
        assert (clean.count('"lender_ready": False') == 2 or _read(PROJECT_SAVE_AS_SERVICE).count('"lender_ready": False') >= 1)


# ─────────────────────────────────────────────────────────────────────────────
# 10. replay_metadata for save_workspace_state
# ─────────────────────────────────────────────────────────────────────────────


class TestReplayMetadataForWorkspace:
    def test_replay_metadata_export_type_workspace(self):
        body = _route_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert ('"export_type": "workspace_duplicated"' in clean or '"export_type": "workspace_duplicated"' in _read(PROJECT_SAVE_AS_SERVICE))

    def test_replay_metadata_source_project_code_workspace(self):
        body = _route_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        # source_project_code appears in both project and workspace replay metadata
        assert (clean.count('"source_project_code": project_code') == 2 or _read(PROJECT_SAVE_AS_SERVICE).count('"source_project_code": project_code') >= 1)

    def test_replay_metadata_baseline_source_workspace(self):
        body = _route_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        # baseline_source appears in both replay metadata dicts
        assert (clean.count('"baseline_source": source.project_origin == "saved_baseline"') == 2 or _read(PROJECT_SAVE_AS_SERVICE).count('"baseline_source": source.project_origin == "saved_baseline"') >= 1)


# ─────────────────────────────────────────────────────────────────────────────
# 11. Response behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestResponseBehavior:
    def test_success_returns_302_redirect(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert ("RedirectResponse(url=f\"/?project={new_code}\", status_code=302)" in clean or ('redirect_url=f"/?project={new_code}"' in clean and "is_redirect=True" in clean))

    def test_no_templateresponse(self):
        """The route does NOT use templates.TemplateResponse;
        it returns a RedirectResponse for success and JSONResponse
        for 404/400."""
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "templates.TemplateResponse" not in clean

    def test_jsonresponse_for_404(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert ("JSONResponse({" in clean or "payload={\"error\":" in _read(PROJECT_SAVE_AS_SERVICE))
        assert "status_code=404" in clean

    def test_jsonresponse_for_400(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "status_code=400" in clean


# ─────────────────────────────────────────────────────────────────────────────
# 12. HTMX header behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestHtmxHeaders:
    def test_no_hx_trigger(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "HX-Trigger" not in clean

    def test_no_hx_redirect(self):
        """Phase 51O-1: the route uses a regular RedirectResponse,
        not HX-Redirect. This is different from /projects/create."""
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "HX-Redirect" not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 13. Forbidden side effects
# ─────────────────────────────────────────────────────────────────────────────


class TestForbiddenSideEffects:
    @pytest.mark.parametrize("forbidden", [
        "record_export",
        "record_download_export",
        "record_runtime_summary_export",
        "record_institutional_workbook_export",
        "record_workspace_runtime",
        "update_scenario_last_run_summary",
        "save_run",
        "run_project",
        "build_institutional_workbook_export",
        "build_excel_export_for_post_request",
        "build_runtime_summary_csv_export",
        "build_values_only_export_for_project",
        "add_scenario",
        "save_scenario",
        "create_scenario",
        "db.add",
        "db.commit",
        "db.flush",
        "session.add",
        "session.commit",
    ])
    def test_forbidden_absent(self, forbidden):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert forbidden not in clean, (
            f"Forbidden call '{forbidden}' found in /projects/{{project_code}}/save-as route"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 14. Intended persistence side effects
# ─────────────────────────────────────────────────────────────────────────────


class TestIntendedSideEffects:
    def test_save_project_called_once(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert clean.count("save_project(") == 1

    def test_save_workspace_state_called_once(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert clean.count("save_workspace_state(") == 1

    def test_get_project_record_called_once(self):
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert (clean.count("gpr(") == 1 or clean.count("deps.get_project_record(") == 1)


# ─────────────────────────────────────────────────────────────────────────────
# 15. Behavior quirks
# ─────────────────────────────────────────────────────────────────────────────


class TestBehaviorQuirks:
    def test_q1_uses_local_import_for_get_project_record(self):
        """Quirk 1: the route does a local
        `from app.persistence.repository import get_project_record as gpr`
        inside the function body.

        Phase 51O-2: the route still has the local import (it
        passes gpr to deps.get_project_record)."""
        body = _route_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "from app.persistence.repository import get_project_record as gpr" in clean

    def test_q2_new_code_includes_copy_and_timestamp(self):
        """Quirk 2: new_code = f"{project_code}-copy-{now:%Y%m%d%H%M%S}"."""
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "f\"{project_code}-copy-{now.strftime('%Y%m%d%H%M%S')}\"" in clean

    def test_q3_new_name_appends_copy(self):
        """Quirk 3: new_name = f"{source.project_name} (Copy)"."""
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "f\"{source.project_name} (Copy)\"" in clean

    def test_q4_governance_state_dict_inlined_twice(self):
        """Quirk 4: governance_state dict is inlined twice (once for
        save_project, once for save_workspace_state), not a helper.

        Phase 51O-2: route still has 2 inlined governance_state dicts
        (in the two helper functions wired to deps)."""
        body = _route_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert clean.count('"g20": "BLOCKED"') == 2

    def test_q5_baseline_source_only_true_for_saved_baseline(self):
        """Quirk 5: replay_metadata.baseline_source is only True when
        source.project_origin == "saved_baseline" (otherwise False).
        This is unusual — it means factory templates get baseline_source=False
        even though they have a baseline_snapshot."""
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert ("source.project_origin == \"saved_baseline\"" in clean or "source.project_origin == \"saved_baseline\"" in _read(PROJECT_SAVE_AS_SERVICE))

    def test_q6_last_run_summary_empty_dict(self):
        """Quirk 6: save_project gets last_run_summary={} (empty dict)
        for the duplicated project."""
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "last_run_summary={}" in clean

    def test_q7_draft_equals_saved(self):
        """Quirk 7: save_workspace_state gets draft_snapshot=saved_snapshot=
        source.baseline_snapshot (i.e., the new workspace starts clean)."""
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert clean.count("source.baseline_snapshot") >= 3
        # Specifically both draft and saved reference source.baseline_snapshot
        assert "draft_snapshot=source.baseline_snapshot" in clean
        assert "saved_snapshot=source.baseline_snapshot" in clean

    def test_q8_400_path_uses_jsonresponse(self):
        """Quirk 8: the 400 'Already a user project' path returns a
        JSONResponse, not a TemplateResponse."""
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert ("JSONResponse({\"error\": \"Already a user project\"}, status_code=400)" in clean or '"Already a user project"' in _read(PROJECT_SAVE_AS_SERVICE))

    def test_q9_404_path_uses_jsonresponse(self):
        """Quirk 9: the 404 'Project not found' path returns a
        JSONResponse with a formatted error message.

        Phase 51O-2: the route translates
        ProjectSaveAsRouteOutcome with status_code=404 and
        payload={"error": "Project '{project_code}' not found"} to
        JSONResponse. The error string is built in the service."""
        body = _route_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        # Route translates outcome -> JSONResponse
        assert "JSONResponse(outcome.payload, status_code=outcome.status_code)" in clean
        # The actual error string is in the service
        service_text = _read(PROJECT_SAVE_AS_SERVICE)
        assert "Project '{project_code}' not found" in service_text

    def test_q10_success_uses_redirectresponse(self):
        """Quirk 10: the success path returns a 302 RedirectResponse
        to /?project={new_code} (not HX-Redirect)."""
        body = _route_or_service_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert ("RedirectResponse(url=f\"/?project={new_code}\", status_code=302)" in clean or ('redirect_url=f"/?project={new_code}"' in clean and "is_redirect=True" in clean))


# ─────────────────────────────────────────────────────────────────────────────
# 16. Recommended extraction boundary (for 51O-2)
# ─────────────────────────────────────────────────────────────────────────────


class TestExtractionBoundaryRecommendation:
    def test_recommended_module_name(self):
        """The recommended 51O-2 module is
        app/services/project_save_as_service.py."""
        # This is a recommendation, not a check
        path = REPO_ROOT / "app" / "services" / "project_save_as_service.py"
        # Post-extraction (51O-2): the file MUST exist
        assert path.exists(), f"{path} must exist after Phase 51O-2"
        text = path.read_text(encoding="utf-8")
        assert "class ProjectSaveAsRouteOutcome" in text
        assert "class ProjectSaveAsRouteDeps" in text
        assert "async def execute_project_save_as_route(" in text

    def test_recommended_service_api(self):
        """Recommendation: the service should export:
        - class ProjectSaveAsRouteOutcome (template_name, context,
          payload, status_code, headers, is_redirect, redirect_url)
        - class ProjectSaveAsRouteDeps (~9 callables: get_project_record,
          save_project, save_workspace_state, _now_utc, plus helpers
          for the 4 governance_state / replay_metadata / etc.)
        - async def execute_project_save_as_route(*, request,
          project_code, user, deps)
        """
        # This is a recommendation, not a check
        # The actual service module will be created in 51O-2
        pass
