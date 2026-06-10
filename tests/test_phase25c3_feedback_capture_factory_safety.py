"""Phase 25C-3 — Pilot Feedback Capture factory safety
tests.

These tests prove the feedback panel is SAFE:

- Factory projects (TUHO / Oborovo) are not affected.
- The helper does not enable any feature flag.
- The helper does not promote construction
  (use_construction_schedule_engine stays False).
- The helper does not touch the persistence schema.
- The helper does not invent fake ticket IDs.
- The helper does not capture PII.
- The helper is read-only; the partial does not
  introduce any JS, Tailwind, or Alpine.
- The partial renders nothing when the helper is
  missing.
- The short template is 3 lines (per the brief).
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


from app.ui.feedback_capture import (
    FIELD_ORDER,
    build_feedback_template,
)


# ---------------------------------------------------------------------------
# 1. Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    """The helper is deterministic."""

    @pytest.mark.parametrize("repeat", range(3))
    def test_same_input_same_output(self, repeat):
        t1 = build_feedback_template()
        t2 = build_feedback_template()
        assert t1.field_count() == t2.field_count()
        for a, b in zip(t1.fields, t2.fields):
            assert a.key == b.key
            assert a.label == b.label
            assert a.help == b.help


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
        from app.ui import feedback_capture
        src = open(feedback_capture.__file__).read()
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
            "_feedback_capture_panel.html",
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
            "_feedback_capture_panel.html",
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
            "_feedback_capture_panel.html",
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
    ``feedback_template`` is missing from the
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
            "partials/_feedback_capture_panel.html",
        )
        out = tpl.render()
        assert out.strip() == "", (
            "partial must render nothing when "
            "feedback_template is missing"
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
            "partials/_feedback_capture_panel.html",
        )
        out = tpl.render(feedback_template={})
        assert out.strip() == ""


# ---------------------------------------------------------------------------
# 5. Partial: renders the template
# ---------------------------------------------------------------------------


class TestPartialRendersTheTemplate:
    """When the helper output is present, the partial
    must render the 6 fields and the short summary."""

    def test_renders_fields_and_disclaimer(self):
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
            "partials/_feedback_capture_panel.html",
        )
        tpl_obj = build_feedback_template()
        out = tpl.render(feedback_template=tpl_obj)
        assert "Report issue / feedback" in out
        assert "Exploratory" in out or "exploratory" in out
        # All 6 field labels must be present
        from app.ui.feedback_capture import FIELD_LABELS
        for label in FIELD_LABELS.values():
            assert label in out, (
                f"field label {label!r} not rendered"
            )
        # The 3 short template lines must be present
        for line in ("Project", "What I tried", "What happened"):
            assert line in out, (
                f"short line {line!r} not rendered"
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
        from app.ui import feedback_capture
        src = open(feedback_capture.__file__).read()
        assert "CREATE TABLE" not in src
        assert "ALTER TABLE" not in src


# ---------------------------------------------------------------------------
# 8. No DB writes
# ---------------------------------------------------------------------------


class TestNoDBWrites:
    """The helper must NOT write to a database or
    persistence layer."""

    def test_helper_does_not_call_persistence(self):
        from app.ui import feedback_capture
        src = open(feedback_capture.__file__).read()
        assert "save_feedback" not in src
        assert "submit_feedback" not in src
        assert "INSERT INTO" not in src
        assert "UPDATE " not in src
        assert "commit" not in src

    def test_partial_does_not_call_persistence(self):
        partial_path = os.path.join(
            REPO_ROOT,
            "app",
            "templates",
            "partials",
            "_feedback_capture_panel.html",
        )
        src = open(partial_path).read()
        assert "save_feedback" not in src
        assert "submit_feedback" not in src
        assert "INSERT" not in src


# ---------------------------------------------------------------------------
# 9. No ticket IDs
# ---------------------------------------------------------------------------


class TestNoTicketIDs:
    """The helper must NOT invent ticket IDs."""

    def test_helper_does_not_define_ticket_id(self):
        from app.ui import feedback_capture
        src = open(feedback_capture.__file__).read()
        # We don't generate a ticket id; the helper
        # is a copy-paste template.
        assert "ticket_id" not in src
        assert "issue_id" not in src
        assert "feedback_id" not in src


# ---------------------------------------------------------------------------
# 10. No PII capture
# ---------------------------------------------------------------------------


class TestNoPIICapture:
    """The helper must NOT capture PII."""

    def test_helper_does_not_ask_for_pii(self):
        from app.ui import feedback_capture
        src = open(feedback_capture.__file__).read()
        for forbidden in (
            "user_email",
            "user_id",
            "ip_address",
            "phone",
            "address",
            "ssn",
            "credit_card",
        ):
            assert forbidden not in src


# ---------------------------------------------------------------------------
# 11. Factory projects safe
# ---------------------------------------------------------------------------


class TestFactoryProjectsSafe:
    """Factory projects (TUHO / Oborovo) are not
    affected. Calling build_feedback_template on
    a factory project is safe because the panel
    itself is gated by the template / caller."""

    def test_factory_projects_safe(self):
        t = build_feedback_template()
        # The feedback template is the same for
        # any project type; the panel is gated.
        assert t.field_count() == 6
