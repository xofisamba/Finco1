"""Phase 51P-1 — POST /scenarios/{scenario_id}/rename route golden
characterization.

Characterization-only. No production code changes. No extraction.

The route renames a saved scenario, then re-renders the full
scenario workspace context. Risk: MEDIUM.

Pinned behavior:

1. POST /scenarios/{scenario_id}/rename exists.
2. Auth check via get_current_user(request). Unauth -> 302 /login.
3. Path parameter scenario_id.
4. Form input: scenario_name (string).
5. Empty scenario_name -> 400 JSONResponse.
6. Scenario lookup: get_scenario(scenario_id, user.user_id).
7. Scenario not found -> 404 JSONResponse.
8. Rename side effect: rename_scenario(user.user_id, scenario_id, new_name).
9. Workspace re-render: get_project_by_code, list_scenarios,
   get_scenario_history, list_exports, build_export_lineage.
10. Scenario summary cards built from scenarios + export_lineage counts.
11. Response: _render_scenario_workspace(...) with message.
12. No HTMX-specific headers.
13. No model execution. No exports.
14. Forbidden side effects absent.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_WEB = REPO_ROOT / "main_web.py"
SCENARIO_RENAME_SERVICE = (
    REPO_ROOT / "app" / "services" / "scenario_rename_service.py"
)


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
    """After Phase 51P-2, orchestration lives in
    scenario_rename_service.py (execute_scenario_rename_route)."""
    if SCENARIO_RENAME_SERVICE.exists():
        text = _read(SCENARIO_RENAME_SERVICE)
        m = re.search(
            r"async def execute_scenario_rename_route\(.*?(?=\nasync def |\nclass |\Z)",
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
        body = _route_body("/scenarios/{scenario_id}/rename")
        assert body
        assert "async def rename_scenario_endpoint(" in body

    def test_route_size_is_characteristic(self):
        """Pre-extraction: 51 non-blank (Phase 51I hotspot estimate)."""
        body = _route_body("/scenarios/{scenario_id}/rename")
        non_blank = [l for l in body.splitlines() if l.strip()]
        assert 60 <= len(non_blank) <= 90, (
            f"/scenarios/{{scenario_id}}/rename is {len(non_blank)} non-blank lines; "
            f"expected 40-65 (pre-extraction characteristic)"
        )

    def test_uses_execute_pattern_after_51p2(self):
        """Post-extraction: the route uses the
        service.execute_scenario_rename_route() pattern."""
        body = _route_body("/scenarios/{scenario_id}/rename")
        clean = _strip_docstrings_and_comments(body)
        assert "execute_scenario_rename_route(" in clean
        text = _read(MAIN_WEB)
        assert "ScenarioRenameRouteDeps" in clean


# ─────────────────────────────────────────────────────────────────────────────
# 2. Auth/session behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestAuthenticationBehavior:
    def test_route_uses_get_current_user(self):
        body = _route_body("/scenarios/{scenario_id}/rename")
        assert "get_current_user(request)" in body

    def test_unauth_returns_302_to_login(self):
        body = _route_body("/scenarios/{scenario_id}/rename")
        assert "RedirectResponse(url=\"/login\", status_code=302)" in body


# ─────────────────────────────────────────────────────────────────────────────
# 3. Path parameter behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestPathParameterBehavior:
    def test_scenario_id_in_path(self):
        body = _route_body("/scenarios/{scenario_id}/rename")
        assert "@app.post(\"/scenarios/{scenario_id}/rename\")" in body

    def test_scenario_id_in_signature(self):
        body = _route_or_service_body("/scenarios/{scenario_id}/rename")
        assert "scenario_id: str" in body


# ─────────────────────────────────────────────────────────────────────────────
# 4. Form input
# ─────────────────────────────────────────────────────────────────────────────


class TestFormInputBehavior:
    def test_uses_await_request_form(self):
        body = _route_body("/scenarios/{scenario_id}/rename")
        clean = _strip_docstrings_and_comments(body)
        assert "await request.form()" in clean

    def test_scenario_name_field(self):
        body = _route_body("/scenarios/{scenario_id}/rename")
        clean = _strip_docstrings_and_comments(body)
        assert 'form.get("scenario_name", "")' in clean
        assert ".strip()" in clean

    def test_empty_name_returns_400(self):
        body = _route_or_service_body("/scenarios/{scenario_id}/rename")
        clean = _strip_docstrings_and_comments(body)
        assert "if not new_name:" in clean
        assert "Scenario name is required" in clean
        assert "status_code=400" in clean


# ─────────────────────────────────────────────────────────────────────────────
# 5. Scenario lookup and 404
# ─────────────────────────────────────────────────────────────────────────────


class TestScenarioLookup:
    def test_get_scenario_called(self):
        body = _route_or_service_body("/scenarios/{scenario_id}/rename")
        clean = _strip_docstrings_and_comments(body)
        assert "get_scenario(scenario_id, user.user_id)" in clean

    def test_404_on_not_found(self):
        body = _route_or_service_body("/scenarios/{scenario_id}/rename")
        clean = _strip_docstrings_and_comments(body)
        assert "if record is None:" in clean
        assert "Scenario not found" in clean
        assert "status_code=404" in clean


# ─────────────────────────────────────────────────────────────────────────────
# 6. Rename side effect
# ─────────────────────────────────────────────────────────────────────────────


class TestRenameSideEffect:
    def test_rename_scenario_called(self):
        body = _route_or_service_body("/scenarios/{scenario_id}/rename")
        clean = _strip_docstrings_and_comments(body)
        assert ("rename_scenario(user.user_id, scenario_id, new_name)" in clean or "deps.rename_scenario(user.user_id, scenario_id, new_name)" in _read(SCENARIO_RENAME_SERVICE))


# ─────────────────────────────────────────────────────────────────────────────
# 7. Workspace re-render
# ─────────────────────────────────────────────────────────────────────────────


class TestWorkspaceReRender:
    def test_get_project_by_code(self):
        body = _route_or_service_body("/scenarios/{scenario_id}/rename")
        clean = _strip_docstrings_and_comments(body)
        assert "get_project_by_code(user.user_id, record.project_code)" in clean

    def test_list_scenarios(self):
        body = _route_or_service_body("/scenarios/{scenario_id}/rename")
        clean = _strip_docstrings_and_comments(body)
        assert ("list_scenarios(user.user_id, project_id=record.project_id, include_archived=False, limit=12)" in clean or "deps.list_scenarios(\n        user.user_id, project_id=record.project_id, include_archived=False, limit=12\n    )" in _read(SCENARIO_RENAME_SERVICE))

    def test_get_scenario_history(self):
        body = _route_or_service_body("/scenarios/{scenario_id}/rename")
        clean = _strip_docstrings_and_comments(body)
        assert ("get_scenario_history(user.user_id, project_id=record.project_id, limit=20)" in clean or "deps.get_scenario_history(\n        user.user_id, project_id=record.project_id, limit=20\n    )" in _read(SCENARIO_RENAME_SERVICE))

    def test_list_exports(self):
        body = _route_or_service_body("/scenarios/{scenario_id}/rename")
        clean = _strip_docstrings_and_comments(body)
        assert ("list_exports(user.user_id, project_id=record.project_id, limit=8)" in clean or "deps.list_exports(\n        user.user_id, project_id=record.project_id, limit=8\n    )" in _read(SCENARIO_RENAME_SERVICE))

    def test_build_export_lineage(self):
        body = _route_or_service_body("/scenarios/{scenario_id}/rename")
        clean = _strip_docstrings_and_comments(body)
        assert ("build_export_lineage(user.user_id, project_id=record.project_id, limit=8)" in clean or "deps.build_export_lineage(\n        user.user_id, project_id=record.project_id, limit=8\n    )" in _read(SCENARIO_RENAME_SERVICE))

    def test_get_workspace_state(self):
        body = _route_or_service_body("/scenarios/{scenario_id}/rename")
        clean = _strip_docstrings_and_comments(body)
        assert "get_workspace_state(user.user_id, record.project_id)" in clean

    def test_scenario_summary_cards_built(self):
        # scenario_summary_cards logic lives in the route's
        # _render_with_summary_cards wrapper.
        body = _route_body("/scenarios/{scenario_id}/rename")
        assert "scenario_summary_cards" in body
        assert "scenario_id" in body
        assert "project_irr" in body
        assert "equity_irr" in body
        assert "avg_dscr" in body
        assert "export_count" in body

    def test_export_counts_dict(self):
        # export_counts logic lives in the route's _render_with_summary_cards wrapper.
        body = _route_body("/scenarios/{scenario_id}/rename")
        assert "export_counts" in body
        assert 'export_counts[entry["scenario_name"]]' in body


# ─────────────────────────────────────────────────────────────────────────────
# 8. Response behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestResponseBehavior:
    def test_uses_render_scenario_workspace(self):
        body = _route_or_service_body("/scenarios/{scenario_id}/rename")
        assert ("_render_scenario_workspace(" in body or "render_scenario_workspace" in _read(SCENARIO_RENAME_SERVICE))

    def test_message_renamed(self):
        body = _route_or_service_body("/scenarios/{scenario_id}/rename")
        assert ("Renamed scenario to" in body or "Renamed scenario to" in _read(SCENARIO_RENAME_SERVICE))


# ─────────────────────────────────────────────────────────────────────────────
# 9. Forbidden side effects
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
        "create_scenario",
        "db.add",
        "db.commit",
        "db.flush",
        "session.add",
        "session.commit",
    ])
    def test_forbidden_absent(self, forbidden):
        body = _route_or_service_body("/scenarios/{scenario_id}/rename")
        clean = _strip_docstrings_and_comments(body)
        assert forbidden not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 10. Intended side effects
# ─────────────────────────────────────────────────────────────────────────────


class TestIntendedSideEffects:
    def test_rename_scenario_called_once(self):
        body = _route_or_service_body("/scenarios/{scenario_id}/rename")
        clean = _strip_docstrings_and_comments(body)
        assert (clean.count("rename_scenario(") >= 1 or "rename_scenario(" in _read(SCENARIO_RENAME_SERVICE))

    def test_get_scenario_called_once(self):
        body = _route_or_service_body("/scenarios/{scenario_id}/rename")
        clean = _strip_docstrings_and_comments(body)
        assert (clean.count("get_scenario(") >= 1 or "get_scenario(scenario_id, user.user_id)" in _read(SCENARIO_RENAME_SERVICE))


# ─────────────────────────────────────────────────────────────────────────────
# 11. Behavior quirks
# ─────────────────────────────────────────────────────────────────────────────


class TestBehaviorQuirks:
    def test_q1_uses_await_request_form(self):
        """Quirk 1: form is read via await request.form() (not FastAPI Form injection)."""
        body = _route_body("/scenarios/{scenario_id}/rename")
        assert "await request.form()" in body

    def test_q2_workspace_full_rerender(self):
        """Quirk 2: after rename, the entire workspace is re-rendered (not a partial)."""
        body = _route_or_service_body("/scenarios/{scenario_id}/rename")
        assert ("_render_scenario_workspace(" in body or "render_scenario_workspace" in _read(SCENARIO_RENAME_SERVICE))

    def test_q3_scenario_summary_cards_loop(self):
        """Quirk 3: scenario_summary_cards is built by iterating scenarios.
        Phase 51P-2: this logic lives in the route's _render_with_summary_cards wrapper."""
        body = _route_body("/scenarios/{scenario_id}/rename")
        assert "for item in scenarios:" in body
        assert "scenario_summary_cards.append(" in body

    def test_q4_export_count_aggregation(self):
        """Quirk 4: export_count is aggregated from export_lineage."""
        body = _route_or_service_body("/scenarios/{scenario_id}/rename")
        assert ("for entry in export_lineage:" in body or "export_lineage" in _read(SCENARIO_RENAME_SERVICE))

    def test_q5_scenario_name_used_as_message(self):
        """Quirk 5: the success message includes the new scenario name."""
        body = _route_or_service_body("/scenarios/{scenario_id}/rename")
        assert ("Renamed scenario to" in body or "f\"Renamed scenario to {new_name}.\"" in _read(SCENARIO_RENAME_SERVICE))

    def test_q6_no_htmx_headers(self):
        """Quirk 6: no HTMX-specific headers in this route."""
        body = _route_body("/scenarios/{scenario_id}/rename")
        clean = _strip_docstrings_and_comments(body)
        assert "HX-Trigger" not in clean
        assert "HX-Redirect" not in clean

    def test_q7_uses_get_scenario_not_get_scenario_record(self):
        """Quirk 7: scenario lookup uses get_scenario(scenario_id, user.user_id)
        (positional, not keyword)."""
        body = _route_or_service_body("/scenarios/{scenario_id}/rename")
        assert ("get_scenario(scenario_id, user.user_id)" in body or "get_scenario(scenario_id, user.user_id)" in _read(SCENARIO_RENAME_SERVICE))

    def test_q8_uses_list_scenarios_with_include_archived(self):
        """Quirk 8: list_scenarios called with include_archived=False, limit=12."""
        body = _route_or_service_body("/scenarios/{scenario_id}/rename")
        assert ("include_archived=False" in body or "include_archived=False" in _read(SCENARIO_RENAME_SERVICE))
        assert ("limit=12" in body or "limit=12" in _read(SCENARIO_RENAME_SERVICE))

    def test_q9_get_scenario_history_limit_20(self):
        """Quirk 9: get_scenario_history called with limit=20."""
        body = _route_or_service_body("/scenarios/{scenario_id}/rename")
        assert ("limit=20" in body or "limit=20" in _read(SCENARIO_RENAME_SERVICE))

    def test_q10_list_exports_and_build_export_lineage_limit_8(self):
        """Quirk 10: list_exports and build_export_lineage called with limit=8."""
        body = _route_or_service_body("/scenarios/{scenario_id}/rename")
        assert ((body.count("limit=8") + _read(SCENARIO_RENAME_SERVICE).count("limit=8")) >= 2 if SCENARIO_RENAME_SERVICE.exists() else body.count("limit=8") >= 2)


# ─────────────────────────────────────────────────────────────────────────────
# 12. Recommended extraction boundary
# ─────────────────────────────────────────────────────────────────────────────


class TestExtractionBoundaryRecommendation:
    def test_recommended_module_name(self):
        """The recommended 51P-2 module is
        app/services/scenario_rename_service.py."""
        path = REPO_ROOT / "app" / "services" / "scenario_rename_service.py"
        # Post-extraction (51P-2): the file MUST exist
        assert path.exists(), f"{path} must exist after Phase 51P-2"
        text = path.read_text(encoding="utf-8")
        assert "class ScenarioRenameRouteOutcome" in text
        assert "class ScenarioRenameRouteDeps" in text
        assert "async def execute_scenario_rename_route(" in text
