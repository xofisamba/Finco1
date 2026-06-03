"""Phase 51S-1 — POST /scenarios/{scenario_id}/select route golden
characterization.

Characterization-only. No production code changes. No extraction.

The route sets the active scenario for the current workspace.
Risk: MEDIUM/LOW.
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
        body = _route_body("/scenarios/{scenario_id}/select")
        assert body
        assert "async def select_scenario_endpoint(" in body

    def test_route_size_is_characteristic(self):
        """Pre-extraction: 21 non-blank (Phase 51I hotspot estimate)."""
        body = _route_body("/scenarios/{scenario_id}/select")
        non_blank = [l for l in body.splitlines() if l.strip()]
        assert 18 <= len(non_blank) <= 30, (
            f"/scenarios/{{scenario_id}}/select is {len(non_blank)} non-blank lines; "
            f"expected 18-30 (pre-extraction characteristic)"
        )

    def test_no_execute_pattern_yet(self):
        body = _route_body("/scenarios/{scenario_id}/select")
        clean = _strip_docstrings_and_comments(body)
        assert "execute_scenario_select_route(" not in clean
        text = _read(MAIN_WEB)
        assert "class ScenarioSelectRouteDeps" not in text


# ─────────────────────────────────────────────────────────────────────────────
# 2. Auth/session behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestAuthenticationBehavior:
    def test_route_uses_get_current_user(self):
        body = _route_body("/scenarios/{scenario_id}/select")
        assert "get_current_user(request)" in body

    def test_unauth_returns_302_to_login(self):
        body = _route_body("/scenarios/{scenario_id}/select")
        assert "RedirectResponse(url=\"/login\", status_code=302)" in body


# ─────────────────────────────────────────────────────────────────────────────
# 3. Path parameter behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestPathParameterBehavior:
    def test_scenario_id_in_path(self):
        body = _route_body("/scenarios/{scenario_id}/select")
        assert "@app.post(\"/scenarios/{scenario_id}/select\")" in body

    def test_scenario_id_in_signature(self):
        body = _route_body("/scenarios/{scenario_id}/select")
        assert "scenario_id: str" in body


# ─────────────────────────────────────────────────────────────────────────────
# 4. Scenario lookup
# ─────────────────────────────────────────────────────────────────────────────


class TestScenarioLookup:
    def test_get_scenario_called(self):
        body = _route_body("/scenarios/{scenario_id}/select")
        clean = _strip_docstrings_and_comments(body)
        assert "get_scenario(scenario_id, user.user_id)" in clean

    def test_404_on_not_found(self):
        body = _route_body("/scenarios/{scenario_id}/select")
        clean = _strip_docstrings_and_comments(body)
        assert "if record is None:" in clean
        assert "Scenario not found" in clean
        assert "status_code=404" in clean


# ─────────────────────────────────────────────────────────────────────────────
# 5. select_scenario call
# ─────────────────────────────────────────────────────────────────────────────


class TestSelectScenarioCall:
    def test_select_scenario_called(self):
        body = _route_body("/scenarios/{scenario_id}/select")
        clean = _strip_docstrings_and_comments(body)
        assert "select_scenario(user.user_id, record.project_id, scenario_id)" in clean

    def test_500_on_failure(self):
        body = _route_body("/scenarios/{scenario_id}/select")
        clean = _strip_docstrings_and_comments(body)
        assert "if not ok:" in clean
        assert "Failed to select scenario" in clean
        assert "status_code=500" in clean


# ─────────────────────────────────────────────────────────────────────────────
# 6. Response behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestResponseBehavior:
    def test_uses_templates_TemplateResponse(self):
        body = _route_body("/scenarios/{scenario_id}/select")
        clean = _strip_docstrings_and_comments(body)
        assert "templates.TemplateResponse(" in clean

    def test_template_name_scenario_tab(self):
        body = _route_body("/scenarios/{scenario_id}/select")
        assert 'name="partials/scenario_tab.html"' in body

    def test_context_uses_build_scenario_tab_context(self):
        body = _route_body("/scenarios/{scenario_id}/select")
        assert "_build_scenario_tab_context(" in body


# ─────────────────────────────────────────────────────────────────────────────
# 7. HTMX headers
# ─────────────────────────────────────────────────────────────────────────────


class TestHtmxHeaders:
    def test_hx_trigger_scenario_selected(self):
        """Quirk: HX-Trigger 'scenarioSelected:{"scenario_id": "..."}' (JSON in header)."""
        body = _route_body("/scenarios/{scenario_id}/select")
        assert "scenarioSelected:" in body
        assert "HX-Trigger" in body

    def test_no_hx_redirect(self):
        body = _route_body("/scenarios/{scenario_id}/select")
        clean = _strip_docstrings_and_comments(body)
        assert "HX-Redirect" not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 8. Workspace state lookup
# ─────────────────────────────────────────────────────────────────────────────


class TestWorkspaceStateLookup:
    def test_get_workspace_state(self):
        body = _route_body("/scenarios/{scenario_id}/select")
        clean = _strip_docstrings_and_comments(body)
        assert "get_workspace_state(user.user_id, record.project_id)" in clean

    def test_get_project_record(self):
        body = _route_body("/scenarios/{scenario_id}/select")
        clean = _strip_docstrings_and_comments(body)
        assert "get_project_record(user_id=user.user_id, project_code=record.project_code)" in clean

    def test_list_scenarios(self):
        body = _route_body("/scenarios/{scenario_id}/select")
        clean = _strip_docstrings_and_comments(body)
        assert "list_scenarios(user.user_id, project_id=record.project_id, include_archived=False, limit=12)" in clean


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
        "update_scenario_overrides",
        "create_scenario",
        "db.add",
        "db.commit",
        "db.flush",
        "session.add",
        "session.commit",
    ])
    def test_forbidden_absent(self, forbidden):
        body = _route_body("/scenarios/{scenario_id}/select")
        clean = _strip_docstrings_and_comments(body)
        assert forbidden not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 10. Intended side effects
# ─────────────────────────────────────────────────────────────────────────────


class TestIntendedSideEffects:
    def test_select_scenario_called_once(self):
        body = _route_body("/scenarios/{scenario_id}/select")
        clean = _strip_docstrings_and_comments(body)
        assert clean.count("select_scenario(") == 1

    def test_get_scenario_called_once(self):
        body = _route_body("/scenarios/{scenario_id}/select")
        clean = _strip_docstrings_and_comments(body)
        assert clean.count("get_scenario(") == 1


# ─────────────────────────────────────────────────────────────────────────────
# 11. Behavior quirks
# ─────────────────────────────────────────────────────────────────────────────


class TestBehaviorQuirks:
    def test_q1_select_scenario_takes_project_id(self):
        """Quirk 1: select_scenario takes (user_id, project_id, scenario_id) — NOT scenario_id first."""
        body = _route_body("/scenarios/{scenario_id}/select")
        assert "select_scenario(user.user_id, record.project_id, scenario_id)" in body

    def test_q2_returns_bool(self):
        """Quirk 2: select_scenario returns a bool (not the record)."""
        body = _route_body("/scenarios/{scenario_id}/select")
        assert "if not ok:" in body

    def test_q3_500_on_failure(self):
        """Quirk 3: 500 if select_scenario returns False."""
        body = _route_body("/scenarios/{scenario_id}/select")
        assert "if not ok:" in body
        assert "status_code=500" in body

    def test_q4_partial_template_render(self):
        """Quirk 4: uses partials/scenario_tab.html (NOT full workspace)."""
        body = _route_body("/scenarios/{scenario_id}/select")
        assert 'name="partials/scenario_tab.html"' in body
        clean = _strip_docstrings_and_comments(body)
        assert "_render_scenario_workspace" not in clean

    def test_q5_hx_trigger_with_json_payload(self):
        """Quirk 5: HX-Trigger 'scenarioSelected:{"scenario_id": "..."}' (JSON in header)."""
        body = _route_body("/scenarios/{scenario_id}/select")
        assert "scenarioSelected:" in body
        assert "scenario_id" in body
        # The f-string with JSON
        assert '\\"scenario_id\\"' in body or "{\"scenario_id\":" in body

    def test_q6_uses_build_scenario_tab_context(self):
        """Quirk 6: uses _build_scenario_tab_context (NOT _render_scenario_workspace)."""
        body = _route_body("/scenarios/{scenario_id}/select")
        assert "_build_scenario_tab_context(" in body

    def test_q7_no_hx_redirect(self):
        """Quirk 7: no HX-Redirect (uses HX-Trigger instead)."""
        body = _route_body("/scenarios/{scenario_id}/select")
        clean = _strip_docstrings_and_comments(body)
        assert "HX-Redirect" not in clean

    def test_q8_positional_get_scenario(self):
        """Quirk 8: get_scenario(scenario_id, user.user_id) (positional)."""
        body = _route_body("/scenarios/{scenario_id}/select")
        assert "get_scenario(scenario_id, user.user_id)" in body

    def test_q9_get_project_record_keyword(self):
        """Quirk 9: get_project_record(user_id=..., project_code=...) (KEYWORD args)."""
        body = _route_body("/scenarios/{scenario_id}/select")
        assert "get_project_record(user_id=user.user_id, project_code=record.project_code)" in body

    def test_q10_no_form_no_json(self):
        """Quirk 10: no form input, no JSON body."""
        body = _route_body("/scenarios/{scenario_id}/select")
        clean = _strip_docstrings_and_comments(body)
        assert "await request.form()" not in clean
        assert "await request.json()" not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 12. Recommended extraction boundary
# ─────────────────────────────────────────────────────────────────────────────


class TestExtractionBoundaryRecommendation:
    def test_recommended_module_name(self):
        path = REPO_ROOT / "app" / "services" / "scenario_select_service.py"
        assert not path.exists(), (
            f"{path} must NOT exist before Phase 51S-2"
        )
