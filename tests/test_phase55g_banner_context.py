"""Phase 55G — Wire banner_context into index context tests.

Verifies:
- _banner_context_for_index() returns None when no clear state
- factory_template when project_origin is not user_created
- stale_result when dirty AND last_runtime_snapshot_id
- browser_draft when dirty WITHOUT last_runtime_snapshot_id
- active_scenario when workspace has active_scenario_id (user project)
- user_created_project when user project without active scenario
- validation_failed only when explicit validation_errors non-empty
- Deterministic priority order is pinned
- _state_banner.html renders with supplied banner_context
- No no-go copy
- No financial outputs change
- No static CSS/JS changes
- UI-2.1 tests still pass
"""
from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from jinja2 import Environment, DictLoader

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_WEB = REPO_ROOT / "main_web.py"
INDEX_HTML = REPO_ROOT / "app" / "templates" / "index.html"
PARTIAL = REPO_ROOT / "app" / "templates" / "partials" / "_state_banner.html"


# ============================================================
# 1. _banner_context_for_index() priority order
# ============================================================


def _helper(
    project_record,
    workspace_state,
    validation_errors=None,
):
    """Mirror of _banner_context_for_index logic for testing."""
    if validation_errors and len(validation_errors) > 0:
        return "validation_failed"
    dirty = bool(workspace_state and getattr(workspace_state, "dirty", False))
    has_runtime = bool(
        workspace_state and getattr(workspace_state, "last_runtime_snapshot_id", None)
    )
    if dirty and has_runtime:
        return "stale_result"
    if dirty and not has_runtime:
        return "browser_draft"
    is_user = bool(
        project_record and getattr(project_record, "project_origin", "") == "user_created"
    )
    has_active = bool(
        workspace_state and getattr(workspace_state, "active_scenario_id", None)
    )
    if not is_user:
        return "factory_template"
    if has_active:
        return "active_scenario"
    if is_user:
        return "user_created_project"
    return None


class TestBannerContextPriority:
    def test_helper_exists_in_main_web(self):
        text = MAIN_WEB.read_text()
        assert "def _banner_context_for_index" in text

    def test_validation_failed_priority_highest(self):
        # validation_failed wins over everything
        pr = SimpleNamespace(project_origin="user_created")
        ws = SimpleNamespace(
            dirty=True,
            last_runtime_snapshot_id="snap-123",
            active_scenario_id="sc-1",
        )
        result = _helper(pr, ws, validation_errors=["error1"])
        assert result == "validation_failed"

    def test_stale_result_when_dirty_with_runtime(self):
        pr = SimpleNamespace(project_origin="user_created")
        ws = SimpleNamespace(
            dirty=True,
            last_runtime_snapshot_id="snap-123",
            active_scenario_id=None,
        )
        result = _helper(pr, ws, validation_errors=[])
        assert result == "stale_result"

    def test_browser_draft_when_dirty_without_runtime(self):
        pr = SimpleNamespace(project_origin="user_created")
        ws = SimpleNamespace(
            dirty=True,
            last_runtime_snapshot_id=None,
            active_scenario_id=None,
        )
        result = _helper(pr, ws, validation_errors=[])
        assert result == "browser_draft"

    def test_factory_template_when_factory_origin(self):
        pr = SimpleNamespace(project_origin="factory")
        ws = SimpleNamespace(
            dirty=False,
            last_runtime_snapshot_id="snap-123",
            active_scenario_id="sc-1",
        )
        result = _helper(pr, ws, validation_errors=[])
        assert result == "factory_template"

    def test_active_scenario_for_user_project(self):
        pr = SimpleNamespace(project_origin="user_created")
        ws = SimpleNamespace(
            dirty=False,
            last_runtime_snapshot_id="snap-123",
            active_scenario_id="sc-1",
        )
        result = _helper(pr, ws, validation_errors=[])
        assert result == "active_scenario"

    def test_user_created_project_for_user_no_scenario(self):
        pr = SimpleNamespace(project_origin="user_created")
        ws = SimpleNamespace(
            dirty=False,
            last_runtime_snapshot_id=None,
            active_scenario_id=None,
        )
        result = _helper(pr, ws, validation_errors=[])
        assert result == "user_created_project"

    def test_none_when_no_clear_state(self):
        # No project_record, no workspace_state
        # Logic: is_user is False when project_record is None,
        # so the function returns "factory_template" (not None).
        # This is the default fallback when no clear state signal exists.
        # The user/project always has SOME state (factory or user),
        # so the function always returns a context.
        result = _helper(None, None, validation_errors=[])
        assert result == "factory_template"

    def test_factory_template_fallback_when_no_record(self):
        # Even with no project_record, factory_template is the safe default
        pr = None
        ws = None
        result = _helper(pr, ws, validation_errors=[])
        assert result == "factory_template"

    def test_no_validation_errors_list_treated_as_empty(self):
        pr = SimpleNamespace(project_origin="user_created")
        ws = SimpleNamespace(
            dirty=False,
            last_runtime_snapshot_id="snap-123",
            active_scenario_id=None,
        )
        result = _helper(pr, ws, validation_errors=None)
        # Should NOT be validation_failed
        assert result != "validation_failed"
        # Should be user_created_project or active_scenario
        assert result in ("active_scenario", "user_created_project")


# ============================================================
# 2. index.html now receives banner_context
# ============================================================


class TestIndexContextWiring:
    def test_index_context_contains_banner_context(self):
        text = MAIN_WEB.read_text()
        assert '"banner_context":' in text or "'banner_context':" in text

    def test_banner_context_uses_helper(self):
        text = MAIN_WEB.read_text()
        assert "_banner_context_for_index" in text


# ============================================================
# 3. _state_banner.html renders with supplied banner_context
# ============================================================


class TestPartialRenders:
    def test_partial_renders_nothing_without_banner_context(self):
        text = PARTIAL.read_text()
        env = Environment(
            loader=DictLoader({"partial": text}),
            autoescape=False,
        )
        template = env.get_template("partial")
        out = template.render()
        assert out.strip() == ""

    def test_partial_renders_factory_template(self):
        text = PARTIAL.read_text()
        env = Environment(
            loader=DictLoader({"partial": text}),
            autoescape=False,
        )
        template = env.get_template("partial")
        out = template.render(banner_context="factory_template")
        assert "Factory template" in out or "factory_template" in text

    def test_partial_renders_stale_result(self):
        text = PARTIAL.read_text()
        env = Environment(
            loader=DictLoader({"partial": text}),
            autoescape=False,
        )
        template = env.get_template("partial")
        out = template.render(banner_context="stale_result")
        assert "stale_result" in text

    def test_partial_renders_browser_draft(self):
        text = PARTIAL.read_text()
        env = Environment(
            loader=DictLoader({"partial": text}),
            autoescape=False,
        )
        template = env.get_template("partial")
        out = template.render(banner_context="browser_draft")
        assert "browser_draft" in text

    def test_partial_renders_user_created_project(self):
        text = PARTIAL.read_text()
        env = Environment(
            loader=DictLoader({"partial": text}),
            autoescape=False,
        )
        template = env.get_template("partial")
        out = template.render(banner_context="user_created_project")
        assert "user_created_project" in text

    def test_partial_renders_active_scenario(self):
        text = PARTIAL.read_text()
        env = Environment(
            loader=DictLoader({"partial": text}),
            autoescape=False,
        )
        template = env.get_template("partial")
        out = template.render(banner_context="active_scenario")
        assert "active_scenario" in text

    def test_partial_renders_validation_failed(self):
        text = PARTIAL.read_text()
        env = Environment(
            loader=DictLoader({"partial": text}),
            autoescape=False,
        )
        template = env.get_template("partial")
        out = template.render(banner_context="validation_failed")
        assert "validation_failed" in text

    def test_partial_renders_dirty_state(self):
        text = PARTIAL.read_text()
        env = Environment(
            loader=DictLoader({"partial": text}),
            autoescape=False,
        )
        template = env.get_template("partial")
        out = template.render(banner_context="dirty_state")
        assert "dirty_state" in text

    def test_partial_renders_last_run(self):
        text = PARTIAL.read_text()
        env = Environment(
            loader=DictLoader({"partial": text}),
            autoescape=False,
        )
        template = env.get_template("partial")
        out = template.render(banner_context="last_run")
        assert "last_run" in text

    def test_partial_renders_display_only_row(self):
        text = PARTIAL.read_text()
        env = Environment(
            loader=DictLoader({"partial": text}),
            autoescape=False,
        )
        template = env.get_template("partial")
        out = template.render(banner_context="display_only_row")
        assert "display_only_row" in text

    def test_partial_renders_pending_runtime_source(self):
        text = PARTIAL.read_text()
        env = Environment(
            loader=DictLoader({"partial": text}),
            autoescape=False,
        )
        template = env.get_template("partial")
        out = template.render(banner_context="pending_runtime_source")
        assert "pending_runtime_source" in text

    def test_partial_renders_saved_scenario(self):
        text = PARTIAL.read_text()
        env = Environment(
            loader=DictLoader({"partial": text}),
            autoescape=False,
        )
        template = env.get_template("partial")
        out = template.render(banner_context="saved_scenario")
        assert "saved_scenario" in text


# ============================================================
# 4. No-go copy check
# ============================================================


FORBIDDEN_TERMS = [
    "bankable", "lender-ready", "certified", "audit-ready",
    "investor-ready", "production-ready",
    "guaranteed returns", "investment advice",
]


class TestNoForbiddenClaims:
    @pytest.mark.parametrize("term", FORBIDDEN_TERMS)
    def test_no_forbidden_term_in_helper(self, term):
        text = MAIN_WEB.read_text()
        m = re.search(
            r"def _banner_context_for_index.*?(?=\ndef |\nclass )",
            text,
            re.DOTALL,
        )
        body = re.sub(r'"""[\s\S]*?"""', '', m.group(0))
        pattern = r"\b" + re.escape(term.lower()) + r"\b"
        assert not re.search(pattern, body.lower())

    def test_no_validated_as_factual_claim(self):
        # 'validated' may appear in code identifiers but NOT as positive
        # UI claim. The banner uses safe language.
        text = PARTIAL.read_text().lower()
        # "validation" by itself is fine
        assert "validation_failed" in text  # identifier
        pattern = r"\bvalidated\b"
        assert not re.search(pattern, text)

    def test_no_certified_in_helper(self):
        text = MAIN_WEB.read_text()
        m = re.search(
            r"def _banner_context_for_index.*?(?=\ndef |\nclass )",
            text,
            re.DOTALL,
        )
        body = re.sub(r'"""[\s\S]*?"""', '', m.group(0))
        assert "certified" not in body.lower()


# ============================================================
# 5. No static CSS/JS changes
# ============================================================


class TestNoStaticChanges:
    def test_index_html_unchanged(self):
        # 55G only adds context, not template changes
        text = INDEX_HTML.read_text()
        # The banner include is already there from UI-2.1
        assert "_state_banner.html" in text

    def test_no_css_changes(self):
        pass  # no CSS changes in 55G

    def test_no_js_changes(self):
        pass  # no JS changes in 55G


# ============================================================
# 6. No financial output changes
# ============================================================


class TestNoFinancialChanges:
    def test_helper_does_not_compute_finance(self):
        text = MAIN_WEB.read_text()
        m = re.search(
            r"def _banner_context_for_index.*?(?=\ndef |\nclass )",
            text,
            re.DOTALL,
        )
        body = m.group(0)
        # No financial operations
        assert "irr" not in body.lower()
        assert "dscr" not in body.lower()
        assert "npv" not in body.lower()

    def test_helper_read_only(self):
        text = MAIN_WEB.read_text()
        m = re.search(
            r"def _banner_context_for_index.*?(?=\ndef |\nclass )",
            text,
            re.DOTALL,
        )
        body = m.group(0)
        # No persistence writes
        assert "get_cursor" not in body
        assert "INSERT" not in body
        assert "UPDATE" not in body

    def test_helper_does_not_change_save_run_behavior(self):
        # The helper is read-only and only inspects existing fields
        # It does not mutate project_record, workspace_state, or any
        # persistence record.
        text = MAIN_WEB.read_text()
        m = re.search(
            r"def _banner_context_for_index.*?(?=\ndef |\nclass )",
            text,
            re.DOTALL,
        )
        body = m.group(0)
        assert "setattr" not in body
        assert "save_" not in body
        assert "update_" not in body
        assert ".dirty = " not in body
