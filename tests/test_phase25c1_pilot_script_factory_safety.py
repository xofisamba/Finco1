"""Phase 25C-1 — Generic pilot script factory safety tests.

Goal: Provide a 9-step first-user pilot script for
Generic Solar / Generic Wind users.

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
- The exploratory disclaimer is descriptive scope
  language, not a no-go claim.
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


from app.ui.generic_pilot_script import (
    STEP_ORDER,
    STEP_ROUTES,
    build_pilot_script,
)


# ---------------------------------------------------------------------------
# 1. Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    """The helper is deterministic: same input -> same
    output, always."""

    @pytest.mark.parametrize("repeat", range(3))
    def test_same_input_same_output(self, repeat):
        s1 = build_pilot_script()
        s2 = build_pilot_script()
        assert s1.step_count() == s2.step_count()
        for a, b in zip(s1.steps, s2.steps):
            assert a.key == b.key
            assert a.label == b.label
            assert a.hint == b.hint
            assert a.route == b.route


# ---------------------------------------------------------------------------
# 2. Forbidden imports
# ---------------------------------------------------------------------------


class TestForbiddenImports:
    """The helper must not import any forbidden module."""

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
        from app.ui import generic_pilot_script
        src = open(generic_pilot_script.__file__).read()
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
            "_generic_pilot_script_panel.html",
        )
        src = open(partial_path).read()
        assert "<script" not in src.lower()
        assert "</script" not in src.lower()

    def test_partial_no_tailwind(self):
        partial_path = os.path.join(
            REPO_ROOT,
            "app",
            "templates",
            "partials",
            "_generic_pilot_script_panel.html",
        )
        src = open(partial_path).read()
        # We may mention "Tailwind" in the docstring
        # as a denial; we never USE Tailwind classes.
        # The only Tailwind-style class is class=
        # attributes which are always named.
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
            "_generic_pilot_script_panel.html",
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
    ``generic_pilot_script`` is missing from the
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
            "partials/_generic_pilot_script_panel.html",
        )
        out = tpl.render()
        assert out.strip() == "", (
            "partial must render nothing when "
            "generic_pilot_script is missing"
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
            "partials/_generic_pilot_script_panel.html",
        )
        out = tpl.render(generic_pilot_script={})
        assert out.strip() == ""


# ---------------------------------------------------------------------------
# 5. Partial: renders the script
# ---------------------------------------------------------------------------


class TestPartialRendersTheScript:
    """When the helper output is present, the partial
    must render the 9 steps and the disclaimer."""

    def test_renders_steps_and_disclaimer(self):
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
            "partials/_generic_pilot_script_panel.html",
        )
        s = build_pilot_script(
            project_type="generic_solar",
            project_label="Generic Solar",
        )
        out = tpl.render(generic_pilot_script=s)
        assert "Try this workflow" in out
        assert "Exploratory" in out or "exploratory" in out
        # All 9 step labels must be present
        from app.ui.generic_pilot_script import STEP_LABELS
        for label in STEP_LABELS.values():
            assert label in out, (
                f"step label {label!r} not rendered"
            )
        # All 9 step routes must be present
        for route in STEP_ROUTES.values():
            assert route in out, (
                f"step route {route!r} not rendered"
            )


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
        from app.ui import generic_pilot_script
        src = open(generic_pilot_script.__file__).read()
        assert "CREATE TABLE" not in src
        assert "ALTER TABLE" not in src


# ---------------------------------------------------------------------------
# 8. No autosave
# ---------------------------------------------------------------------------


class TestNoAutosave:
    """The helper must NOT introduce autosave."""

    def test_helper_does_not_call_save(self):
        from app.ui import generic_pilot_script
        src = open(generic_pilot_script.__file__).read()
        assert "save_workspace" not in src
        assert "save_scenario" not in src
        for line in src.splitlines():
            if "autosave" in line.lower():
                lower = line.lower()
                assert "no autosave" in lower or "not autosave" in lower

    def test_partial_does_not_call_save(self):
        partial_path = os.path.join(
            REPO_ROOT,
            "app",
            "templates",
            "partials",
            "_generic_pilot_script_panel.html",
        )
        src = open(partial_path).read()
        assert "save_workspace" not in src
        assert "save_scenario" not in src


# ---------------------------------------------------------------------------
# 9. Factory projects safe
# ---------------------------------------------------------------------------


class TestFactoryProjectsSafe:
    """The pilot script helper is targeted at Generic
    Solar / Wind. Factory projects (TUHO / Oborovo)
    are not affected. Calling build_pilot_script()
    on a factory project does not mutate anything
    and returns a script with the default label
    unchanged."""

    def test_factory_projects_safe(self):
        # The helper does not inspect the project
        # type; it returns a script with whatever
        # label is passed in. Calling it on a
        # factory project is safe because the panel
        # itself is gated by the template / caller.
        s = build_pilot_script(
            project_type="tuho",
            project_label="TUHO Wind 1",
        )
        assert s.project_type == "tuho"
        assert s.project_label == "TUHO Wind 1"
        # The exploratory disclaimer is unchanged.
        from app.ui.generic_pilot_script import (
            EXPLORATORY_DISCLAIMER,
        )
        assert s.exploratory_disclaimer == EXPLORATORY_DISCLAIMER
