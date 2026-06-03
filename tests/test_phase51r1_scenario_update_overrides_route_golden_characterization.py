"""Phase 51R-1 — POST /scenarios/{scenario_id}/update-overrides route
golden characterization.

Characterization-only. No production code changes. No extraction.

The route patches overrides for a non-base scenario. Expects JSON
body with field overrides. Risk: MEDIUM/state-sensitive.

Key state-sensitive behaviors:

1. POST /scenarios/{scenario_id}/update-overrides exists.
2. Auth check via get_current_user(request). Unauth -> 302 /login.
3. Path parameter scenario_id.
4. Body: JSON dict via await request.json().
5. Scenario lookup: get_scenario(scenario_id, user.user_id).
6. 404 if scenario not found.
7. 400 if record.is_base_case (cannot override Base Case via this endpoint).
8. update_scenario_overrides(user.user_id, scenario_id, overrides) -> updated.
9. 500 if update returns None.
10. Workspace re-render via templates.TemplateResponse (NOT _render_scenario_workspace).
11. HX-Trigger: "overridesUpdated" (unique to this route).
12. partial template: "partials/scenario_tab.html" (NOT full workspace).
13. No HTMX-Redirect.
14. Forbidden side effects absent.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_WEB = REPO_ROOT / "main_web.py"


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


# ─────────────────────────────────────────────────────────────────────────────
# 1. Route existence and size
# ─────────────────────────────────────────────────────────────────────────────


class TestRouteExistence:
    def test_route_exists(self):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        assert body
        assert "async def update_overrides_endpoint(" in body

    def test_route_size_is_characteristic(self):
        """Pre-extraction: 25 non-blank (Phase 51I hotspot estimate)."""
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        non_blank = [l for l in body.splitlines() if l.strip()]
        assert 20 <= len(non_blank) <= 35, (
            f"/scenarios/{{scenario_id}}/update-overrides is {len(non_blank)} non-blank lines; "
            f"expected 20-35 (pre-extraction characteristic)"
        )

    def test_no_execute_pattern_yet(self):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        clean = _strip_docstrings_and_comments(body)
        assert "execute_scenario_update_overrides_route(" not in clean
        text = _read(MAIN_WEB)
        assert "class ScenarioUpdateOverridesRouteDeps" not in text


# ─────────────────────────────────────────────────────────────────────────────
# 2. Auth/session behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestAuthenticationBehavior:
    def test_route_uses_get_current_user(self):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        assert "get_current_user(request)" in body

    def test_unauth_returns_302_to_login(self):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        assert "RedirectResponse(url=\"/login\", status_code=302)" in body


# ─────────────────────────────────────────────────────────────────────────────
# 3. Path parameter behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestPathParameterBehavior:
    def test_scenario_id_in_path(self):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        assert "@app.post(\"/scenarios/{scenario_id}/update-overrides\")" in body

    def test_scenario_id_in_signature(self):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        assert "scenario_id: str" in body


# ─────────────────────────────────────────────────────────────────────────────
# 4. JSON body input
# ─────────────────────────────────────────────────────────────────────────────


class TestJsonBodyInput:
    def test_uses_await_request_json(self):
        """The route uses await request.json() (NOT await request.form())."""
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        clean = _strip_docstrings_and_comments(body)
        assert "await request.json()" in clean
        assert "await request.form()" not in clean

    def test_overrides_dict(self):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        clean = _strip_docstrings_and_comments(body)
        assert "body if isinstance(body, dict) else {}" in clean
        # overrides variable
        assert "overrides" in clean


# ─────────────────────────────────────────────────────────────────────────────
# 5. Scenario lookup and gates
# ─────────────────────────────────────────────────────────────────────────────


class TestScenarioLookupAndGates:
    def test_get_scenario_called(self):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        clean = _strip_docstrings_and_comments(body)
        assert "get_scenario(scenario_id, user.user_id)" in clean

    def test_404_on_not_found(self):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        clean = _strip_docstrings_and_comments(body)
        assert "if record is None:" in clean
        assert "Scenario not found" in clean
        assert "status_code=404" in clean

    def test_400_on_base_case(self):
        """Quirk: 400 if record.is_base_case (cannot override Base Case)."""
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        clean = _strip_docstrings_and_comments(body)
        assert "if record.is_base_case:" in clean
        assert "Cannot override Base Case via this endpoint" in clean
        assert "status_code=400" in clean


# ─────────────────────────────────────────────────────────────────────────────
# 6. update_scenario_overrides call
# ─────────────────────────────────────────────────────────────────────────────


class TestUpdateOverridesCall:
    def test_update_scenario_overrides_called(self):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        clean = _strip_docstrings_and_comments(body)
        assert "update_scenario_overrides(user.user_id, scenario_id, overrides)" in clean

    def test_500_on_failure(self):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        clean = _strip_docstrings_and_comments(body)
        assert "if updated is None:" in clean
        assert "Failed to update overrides" in clean
        assert "status_code=500" in clean


# ─────────────────────────────────────────────────────────────────────────────
# 7. Response behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestResponseBehavior:
    def test_uses_templates_TemplateResponse(self):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        clean = _strip_docstrings_and_comments(body)
        assert "templates.TemplateResponse(" in clean

    def test_template_name_scenario_tab(self):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        assert 'name="partials/scenario_tab.html"' in body

    def test_context_uses_build_scenario_tab_context(self):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        assert "_build_scenario_tab_context(" in body

    def test_uses_get_workspace_state(self):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        clean = _strip_docstrings_and_comments(body)
        assert "get_workspace_state(user.user_id, record.project_id)" in clean

    def test_uses_get_project_record(self):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        clean = _strip_docstrings_and_comments(body)
        assert "get_project_record(user_id=user.user_id, project_code=record.project_code)" in clean

    def test_uses_list_scenarios(self):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        clean = _strip_docstrings_and_comments(body)
        assert "list_scenarios(user.user_id, project_id=record.project_id, include_archived=False, limit=12)" in clean


# ─────────────────────────────────────────────────────────────────────────────
# 8. HTMX headers
# ─────────────────────────────────────────────────────────────────────────────


class TestHtmxHeaders:
    def test_hx_trigger_overrides_updated(self):
        """Quirk: this route emits HX-Trigger 'overridesUpdated'."""
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        assert '"HX-Trigger": "overridesUpdated"' in body

    def test_no_hx_redirect(self):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        clean = _strip_docstrings_and_comments(body)
        assert "HX-Redirect" not in clean


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
        "rename_scenario",
        "archive_scenario",
        "create_scenario",
        "db.add",
        "db.commit",
        "db.flush",
        "session.add",
        "session.commit",
    ])
    def test_forbidden_absent(self, forbidden):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        clean = _strip_docstrings_and_comments(body)
        assert forbidden not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 10. Intended side effects
# ─────────────────────────────────────────────────────────────────────────────


class TestIntendedSideEffects:
    def test_update_scenario_overrides_called_once(self):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        clean = _strip_docstrings_and_comments(body)
        assert clean.count("update_scenario_overrides(") == 1

    def test_get_scenario_called_once(self):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        clean = _strip_docstrings_and_comments(body)
        assert clean.count("get_scenario(") == 1


# ─────────────────────────────────────────────────────────────────────────────
# 11. Behavior quirks
# ─────────────────────────────────────────────────────────────────────────────


class TestBehaviorQuirks:
    def test_q1_uses_request_json(self):
        """Quirk 1: body is JSON (not form)."""
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        assert "await request.json()" in body
        assert "await request.form()" not in body

    def test_q2_overrides_dict_typecheck(self):
        """Quirk 2: overrides = body if isinstance(body, dict) else {}."""
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        assert "body if isinstance(body, dict) else {}" in body

    def test_q3_is_base_case_gate(self):
        """Quirk 3: 400 if record.is_base_case (cannot override Base Case)."""
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        assert "if record.is_base_case:" in body

    def test_q4_500_on_update_failure(self):
        """Quirk 4: 500 if update_scenario_overrides returns None."""
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        assert "if updated is None:" in body
        assert "status_code=500" in body

    def test_q5_partial_template_render(self):
        """Quirk 5: uses partials/scenario_tab.html (NOT full workspace)."""
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        assert 'name="partials/scenario_tab.html"' in body
        # NOT _render_scenario_workspace
        clean = _strip_docstrings_and_comments(body)
        assert "_render_scenario_workspace" not in clean

    def test_q6_hx_trigger_overrides_updated(self):
        """Quirk 6: HX-Trigger 'overridesUpdated' (unique to this route)."""
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        assert '"HX-Trigger": "overridesUpdated"' in body

    def test_q7_no_hx_redirect(self):
        """Quirk 7: no HX-Redirect (uses HX-Trigger instead)."""
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        clean = _strip_docstrings_and_comments(body)
        assert "HX-Redirect" not in clean

    def test_q8_uses_build_scenario_tab_context(self):
        """Quirk 8: uses _build_scenario_tab_context (NOT _render_scenario_workspace)."""
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        assert "_build_scenario_tab_context(" in body

    def test_q9_positional_get_scenario(self):
        """Quirk 9: get_scenario(scenario_id, user.user_id) (positional)."""
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        assert "get_scenario(scenario_id, user.user_id)" in body

    def test_q10_get_project_record_keyword(self):
        """Quirk 10: get_project_record(user_id=..., project_code=...) (KEYWORD args)."""
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        assert "get_project_record(user_id=user.user_id, project_code=record.project_code)" in body


# ─────────────────────────────────────────────────────────────────────────────
# 12. Recommended extraction boundary
# ─────────────────────────────────────────────────────────────────────────────


class TestExtractionBoundaryRecommendation:
    def test_recommended_module_name(self):
        path = REPO_ROOT / "app" / "services" / "scenario_update_overrides_service.py"
        assert not path.exists(), (
            f"{path} must NOT exist before Phase 51R-2"
        )
