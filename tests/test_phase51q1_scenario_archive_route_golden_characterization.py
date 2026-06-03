"""Phase 51Q-1 — POST /scenarios/{scenario_id}/archive route golden
characterization.

Characterization-only. No production code changes. No extraction.

The route soft-archives a saved scenario, then re-renders the
full scenario workspace context. Risk: MEDIUM.
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
        body = _route_body("/scenarios/{scenario_id}/archive")
        assert body
        assert "async def archive_scenario_endpoint(" in body

    def test_route_size_is_characteristic(self):
        """Pre-extraction: 47 non-blank (Phase 51I hotspot estimate)."""
        body = _route_body("/scenarios/{scenario_id}/archive")
        non_blank = [l for l in body.splitlines() if l.strip()]
        assert 40 <= len(non_blank) <= 55, (
            f"/scenarios/{{scenario_id}}/archive is {len(non_blank)} non-blank lines; "
            f"expected 40-55 (pre-extraction characteristic)"
        )

    def test_no_execute_pattern_yet(self):
        body = _route_body("/scenarios/{scenario_id}/archive")
        clean = _strip_docstrings_and_comments(body)
        assert "execute_scenario_archive_route(" not in clean
        text = _read(MAIN_WEB)
        assert "class ScenarioArchiveRouteDeps" not in text


# ─────────────────────────────────────────────────────────────────────────────
# 2. Auth/session behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestAuthenticationBehavior:
    def test_route_uses_get_current_user(self):
        body = _route_body("/scenarios/{scenario_id}/archive")
        assert "get_current_user(request)" in body

    def test_unauth_returns_302_to_login(self):
        body = _route_body("/scenarios/{scenario_id}/archive")
        assert "RedirectResponse(url=\"/login\", status_code=302)" in body


# ─────────────────────────────────────────────────────────────────────────────
# 3. Path parameter behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestPathParameterBehavior:
    def test_scenario_id_in_path(self):
        body = _route_body("/scenarios/{scenario_id}/archive")
        assert "@app.post(\"/scenarios/{scenario_id}/archive\")" in body

    def test_scenario_id_in_signature(self):
        body = _route_body("/scenarios/{scenario_id}/archive")
        assert "scenario_id: str" in body


# ─────────────────────────────────────────────────────────────────────────────
# 4. Scenario lookup and 404
# ─────────────────────────────────────────────────────────────────────────────


class TestScenarioLookup:
    def test_get_scenario_called(self):
        body = _route_body("/scenarios/{scenario_id}/archive")
        clean = _strip_docstrings_and_comments(body)
        assert "get_scenario(scenario_id, user.user_id)" in clean

    def test_404_on_not_found(self):
        body = _route_body("/scenarios/{scenario_id}/archive")
        clean = _strip_docstrings_and_comments(body)
        assert "if record is None:" in clean
        assert "Scenario not found" in clean
        assert "status_code=404" in clean


# ─────────────────────────────────────────────────────────────────────────────
# 5. Archive side effect
# ─────────────────────────────────────────────────────────────────────────────


class TestArchiveSideEffect:
    def test_archive_scenario_called(self):
        body = _route_body("/scenarios/{scenario_id}/archive")
        clean = _strip_docstrings_and_comments(body)
        assert "archive_scenario(user.user_id, scenario_id)" in clean

    def test_archive_scenario_no_new_name_arg(self):
        """Quirk: archive_scenario takes only user_id and scenario_id (no name)."""
        body = _route_body("/scenarios/{scenario_id}/archive")
        assert "archive_scenario(user.user_id, scenario_id)" in body
        # No third arg
        assert "archive_scenario(user.user_id, scenario_id, " not in body


# ─────────────────────────────────────────────────────────────────────────────
# 6. Workspace re-render (same as rename)
# ─────────────────────────────────────────────────────────────────────────────


class TestWorkspaceReRender:
    def test_get_project_by_code(self):
        body = _route_body("/scenarios/{scenario_id}/archive")
        clean = _strip_docstrings_and_comments(body)
        assert "get_project_by_code(user.user_id, record.project_code)" in clean

    def test_list_scenarios_include_archived_false_limit_12(self):
        body = _route_body("/scenarios/{scenario_id}/archive")
        clean = _strip_docstrings_and_comments(body)
        assert "include_archived=False" in clean
        assert "limit=12" in clean

    def test_get_scenario_history_limit_20(self):
        body = _route_body("/scenarios/{scenario_id}/archive")
        clean = _strip_docstrings_and_comments(body)
        assert "limit=20" in clean

    def test_list_exports_limit_8(self):
        body = _route_body("/scenarios/{scenario_id}/archive")
        clean = _strip_docstrings_and_comments(body)
        assert "limit=8" in clean

    def test_build_export_lineage_limit_8(self):
        body = _route_body("/scenarios/{scenario_id}/archive")
        clean = _strip_docstrings_and_comments(body)
        assert "build_export_lineage(user.user_id, project_id=record.project_id, limit=8)" in clean

    def test_get_workspace_state(self):
        body = _route_body("/scenarios/{scenario_id}/archive")
        clean = _strip_docstrings_and_comments(body)
        assert "get_workspace_state(user.user_id, record.project_id)" in clean

    def test_scenario_summary_cards_built(self):
        body = _route_body("/scenarios/{scenario_id}/archive")
        assert "scenario_summary_cards" in body
        assert "project_irr" in body
        assert "equity_irr" in body
        assert "avg_dscr" in body
        assert "export_count" in body


# ─────────────────────────────────────────────────────────────────────────────
# 7. Response behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestResponseBehavior:
    def test_uses_render_scenario_workspace(self):
        body = _route_body("/scenarios/{scenario_id}/archive")
        assert "_render_scenario_workspace(" in body

    def test_message_archived(self):
        body = _route_body("/scenarios/{scenario_id}/archive")
        assert "Archived" in body
        assert "record.scenario_name" in body


# ─────────────────────────────────────────────────────────────────────────────
# 8. Forbidden side effects
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
        "rename_scenario",
        "db.add",
        "db.commit",
        "db.flush",
        "session.add",
        "session.commit",
    ])
    def test_forbidden_absent(self, forbidden):
        body = _route_body("/scenarios/{scenario_id}/archive")
        clean = _strip_docstrings_and_comments(body)
        assert forbidden not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 9. Intended side effects
# ─────────────────────────────────────────────────────────────────────────────


class TestIntendedSideEffects:
    def test_archive_scenario_called_once(self):
        body = _route_body("/scenarios/{scenario_id}/archive")
        clean = _strip_docstrings_and_comments(body)
        assert clean.count("archive_scenario(") == 1

    def test_get_scenario_called_once(self):
        body = _route_body("/scenarios/{scenario_id}/archive")
        clean = _strip_docstrings_and_comments(body)
        assert clean.count("get_scenario(") == 1


# ─────────────────────────────────────────────────────────────────────────────
# 10. Behavior quirks
# ─────────────────────────────────────────────────────────────────────────────


class TestBehaviorQuirks:
    def test_q1_soft_archive(self):
        """Quirk 1: this is a SOFT archive (no delete)."""
        body = _route_body("/scenarios/{scenario_id}/archive")
        assert "archive_scenario" in body
        # No delete
        assert "delete" not in body.lower() or "delete_scenario" not in body

    def test_q2_workspace_full_rerender(self):
        """Quirk 2: after archive, the entire workspace is re-rendered."""
        body = _route_body("/scenarios/{scenario_id}/archive")
        assert "_render_scenario_workspace(" in body

    def test_q3_include_archived_false(self):
        """Quirk 3: list_scenarios called with include_archived=False (archived scenario won't show)."""
        body = _route_body("/scenarios/{scenario_id}/archive")
        assert "include_archived=False" in body

    def test_q4_scenario_summary_cards_loop(self):
        """Quirk 4: scenario_summary_cards built by iterating scenarios."""
        body = _route_body("/scenarios/{scenario_id}/archive")
        assert "for item in scenarios:" in body

    def test_q5_export_count_aggregation(self):
        """Quirk 5: export_count aggregated from export_lineage."""
        body = _route_body("/scenarios/{scenario_id}/archive")
        assert "for entry in export_lineage:" in body

    def test_q6_message_uses_scenario_name(self):
        """Quirk 6: success message uses record.scenario_name."""
        body = _route_body("/scenarios/{scenario_id}/archive")
        assert "Archived {record.scenario_name}" in body

    def test_q7_no_htmx_headers(self):
        """Quirk 7: no HTMX-specific headers."""
        body = _route_body("/scenarios/{scenario_id}/archive")
        clean = _strip_docstrings_and_comments(body)
        assert "HX-Trigger" not in clean
        assert "HX-Redirect" not in clean

    def test_q8_no_form_input(self):
        """Quirk 8: no form input is read (archive takes no body)."""
        body = _route_body("/scenarios/{scenario_id}/archive")
        clean = _strip_docstrings_and_comments(body)
        assert "await request.form()" not in clean

    def test_q9_positional_get_scenario(self):
        """Quirk 9: get_scenario(scenario_id, user.user_id) (positional)."""
        body = _route_body("/scenarios/{scenario_id}/archive")
        assert "get_scenario(scenario_id, user.user_id)" in body

    def test_q10_archive_scenario_takes_no_name(self):
        """Quirk 10: archive_scenario(user.user_id, scenario_id) - no name arg."""
        body = _route_body("/scenarios/{scenario_id}/archive")
        assert "archive_scenario(user.user_id, scenario_id)" in body


# ─────────────────────────────────────────────────────────────────────────────
# 11. Recommended extraction boundary
# ─────────────────────────────────────────────────────────────────────────────


class TestExtractionBoundaryRecommendation:
    def test_recommended_module_name(self):
        path = REPO_ROOT / "app" / "services" / "scenario_archive_service.py"
        assert not path.exists(), (
            f"{path} must NOT exist before Phase 51Q-2"
        )
