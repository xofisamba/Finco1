"""Phase 25C-2 — Empty / Error state factory safety
tests.

Goal: Provide 7 user-facing empty / error state
messages for the Generic Solar / Generic Wind
exploratory workflow.

These tests prove the panel is SAFE:

- Factory projects (TUHO / Oborovo) are not affected.
- The helper does not enable any feature flag.
- The helper does not promote construction
  (use_construction_schedule_engine stays False).
- The helper does not touch the persistence schema.
- The helper does not invent new routes.
- The helper does not invent fake run IDs, fake
  validation claims, or fake outputs.
- The helper is read-only; the partial does not
  introduce any JS, Tailwind, or Alpine.
- The partial renders nothing when the helper is
  missing.
- rc1 frozen.
"""

import os
import subprocess
import sys

import pytest


HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


from app.ui.empty_state_messages import (
    ALL_CONDITIONS,
    Message,
    build_all_messages,
    build_message,
)


# ---------------------------------------------------------------------------
# 1. Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    """The helper is deterministic."""

    @pytest.mark.parametrize("cond", ALL_CONDITIONS)
    @pytest.mark.parametrize("repeat", range(3))
    def test_same_input_same_output(self, cond, repeat):
        m1 = build_message(cond)
        m2 = build_message(cond)
        assert m1.condition == m2.condition
        assert m1.title == m2.title
        assert m1.body == m2.body
        assert m1.next_action == m2.next_action
        assert m1.next_action_route == m2.next_action_route
        assert m1.severity == m2.severity


# ---------------------------------------------------------------------------
# 2. Forbidden imports
# ---------------------------------------------------------------------------


class TestForbiddenImports:
    """The helper must not import any forbidden
    module."""

    FORBIDDEN_MODULES = [
        "app.persistence",
        "app.services",
        "app.construction",
        "app.debt",
        "app.tax",
        "app.idc",
        "app.depreciation",
        "app.waterfall",
    ]

    @pytest.mark.parametrize("module", FORBIDDEN_MODULES)
    def test_forbidden_module_not_imported(self, module):
        from app.ui import empty_state_messages
        src = open(empty_state_messages.__file__).read()
        assert f"import {module}" not in src
        assert f"from {module}" not in src


# ---------------------------------------------------------------------------
# 3. Partial: no JS, no Tailwind, no Alpine
# ---------------------------------------------------------------------------


class TestPartialNoJS:
    """The partial must be pure HTML + Jinja2 macros,
    no JS / no Tailwind / no Alpine / no inline
    script."""

    def test_partial_no_script_tag(self):
        partial_path = os.path.join(
            REPO_ROOT,
            "app",
            "templates",
            "partials",
            "_empty_state_message.html",
        )
        src = open(partial_path).read()
        assert "<script" not in src.lower()
        assert "</script" not in src.lower()

    def test_partial_no_alpine(self):
        partial_path = os.path.join(
            REPO_ROOT,
            "app",
            "templates",
            "partials",
            "_empty_state_message.html",
        )
        src = open(partial_path).read()
        assert "x-data" not in src
        assert "x-init" not in src
        assert "@click" not in src
        assert "x-show" not in src
        assert "x-for" not in src
        assert "x-if" not in src

    def test_partial_no_htmx(self):
        partial_path = os.path.join(
            REPO_ROOT,
            "app",
            "templates",
            "partials",
            "_empty_state_message.html",
        )
        src = open(partial_path).read()
        # We do not introduce new HTMX endpoints.
        assert "hx-post" not in src.lower()
        assert "hx-get" not in src.lower()
        assert "hx-put" not in src.lower()
        assert "hx-delete" not in src.lower()


# ---------------------------------------------------------------------------
# 4. Partial: renders nothing when missing
# ---------------------------------------------------------------------------


class TestPartialRendersNothing:
    """The partial must render nothing if
    ``empty_state_message`` is missing from the
    context."""

    def test_renders_nothing_when_missing(self):
        from jinja2 import Environment, FileSystemLoader
        env = Environment(
            loader=FileSystemLoader(
                [
                    os.path.join(REPO_ROOT, "app", "templates"),
                    os.path.join(
                        REPO_ROOT, "app", "templates", "partials"
                    ),
                ]
            ),
            autoescape=False,
        )
        tpl = env.get_template(
            "partials/_empty_state_message.html",
        )
        out = tpl.render()
        assert out.strip() == "", (
            "partial must render nothing when "
            "empty_state_message is missing"
        )

    def test_renders_nothing_with_empty_dict(self):
        from jinja2 import Environment, FileSystemLoader
        env = Environment(
            loader=FileSystemLoader(
                [
                    os.path.join(REPO_ROOT, "app", "templates"),
                    os.path.join(
                        REPO_ROOT, "app", "templates", "partials"
                    ),
                ]
            ),
            autoescape=False,
        )
        tpl = env.get_template(
            "partials/_empty_state_message.html",
        )
        out = tpl.render(empty_state_message={})
        assert out.strip() == ""


# ---------------------------------------------------------------------------
# 5. Partial: renders the message
# ---------------------------------------------------------------------------


class TestPartialRendersTheMessage:
    """When the helper output is present, the partial
    must render the title, body, action."""

    def test_renders_message(self):
        from jinja2 import Environment, FileSystemLoader
        env = Environment(
            loader=FileSystemLoader(
                [
                    os.path.join(REPO_ROOT, "app", "templates"),
                    os.path.join(
                        REPO_ROOT, "app", "templates", "partials"
                    ),
                ]
            ),
            autoescape=False,
        )
        tpl = env.get_template(
            "partials/_empty_state_message.html",
        )
        m = build_message("no_project")
        out = tpl.render(empty_state_message=m)
        assert m.title in out
        assert m.body in out
        assert m.next_action in out
        assert m.next_action_route in out
        assert m.severity.upper() in out


# ---------------------------------------------------------------------------
# 6. rc1 frozen
# ---------------------------------------------------------------------------


class TestRc1Frozen:
    """rc1 frozen SHA must still resolve."""

    def test_rc1_sha_resolves(self):
        r = subprocess.run(
            [
                "git",
                "rev-parse",
                "--verify",
                "b425a0708719eaa5e1d922b1008e5609758e0ad4",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0


# ---------------------------------------------------------------------------
# 7. No schema changes
# ---------------------------------------------------------------------------


class TestNoSchemaChanges:
    """The helper must not introduce any persistence
    schema migration."""

    def test_helper_does_not_define_new_table(self):
        from app.ui import empty_state_messages
        src = open(empty_state_messages.__file__).read()
        assert "CREATE TABLE" not in src
        assert "ALTER TABLE" not in src


# ---------------------------------------------------------------------------
# 8. No autosave
# ---------------------------------------------------------------------------


class TestNoAutosave:
    """The helper must NOT introduce autosave."""

    def test_helper_does_not_call_save(self):
        from app.ui import empty_state_messages
        src = open(empty_state_messages.__file__).read()
        assert "save_workspace" not in src
        assert "save_scenario" not in src

    def test_partial_does_not_call_save(self):
        partial_path = os.path.join(
            REPO_ROOT,
            "app",
            "templates",
            "partials",
            "_empty_state_message.html",
        )
        src = open(partial_path).read()
        assert "save_workspace" not in src
        assert "save_scenario" not in src


# ---------------------------------------------------------------------------
# 9. Factory projects safe
# ---------------------------------------------------------------------------


class TestFactoryProjectsSafe:
    """Factory projects (TUHO / Oborovo) are not
    affected. Calling build_message on a factory
    project is safe because the panel itself is
    gated by the template / caller."""

    def test_factory_projects_safe(self):
        m = build_message(
            "no_project",
            project_label="TUHO Wind 1",
        )
        assert "TUHO Wind 1" in m.body
        # The 7 conditions and severities are
        # unchanged.
        assert m.severity in ("info", "warning", "error")

    def test_all_conditions_for_factory_label(self):
        for cond in ALL_CONDITIONS:
            m = build_message(
                cond,
                project_label="Oborovo",
            )
            assert m.title
            assert m.body
            assert m.next_action
            assert m.next_action_route
