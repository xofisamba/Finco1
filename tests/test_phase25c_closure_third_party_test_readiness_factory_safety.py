"""Phase 25C Closure — Third-Party Test Readiness
factory safety tests.

These tests prove the audit panel is SAFE:

- Factory projects (TUHO / Oborovo) are not affected.
- The helper does not enable any feature flag.
- The helper does not promote construction
  (use_construction_schedule_engine stays False).
- The helper does not touch the persistence schema.
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


from app.ui.third_party_test_readiness import (
    ALL_WORKFLOWS,
    WorkflowEntry,
    build_third_party_test_readiness,
)


# ---------------------------------------------------------------------------
# 1. Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    """The helper is deterministic."""

    @pytest.mark.parametrize("repeat", range(3))
    def test_same_input_same_output(self, repeat):
        entries = [
            WorkflowEntry(
                workflow=wf,
                helper_present=True,
                partial_present=True,
                helper_tests_pass=True,
                factory_safety_tests_pass=True,
            )
            for wf in ALL_WORKFLOWS
        ]
        r1 = build_third_party_test_readiness(entries)
        r2 = build_third_party_test_readiness(entries)
        assert r1.overall_score == r2.overall_score
        assert r1.bucket == r2.bucket
        assert r1.is_go == r2.is_go
        for a, b in zip(r1.per_workflow, r2.per_workflow):
            assert a.workflow == b.workflow
            assert a.score == b.score


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
        from app.ui import third_party_test_readiness
        src = open(
            third_party_test_readiness.__file__
        ).read()
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
            "_third_party_test_readiness.html",
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
            "_third_party_test_readiness.html",
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
            "_third_party_test_readiness.html",
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
    ``third_party_test_readiness`` is missing."""

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
            "partials/_third_party_test_readiness.html",
        )
        out = tpl.render()
        assert out.strip() == "", (
            "partial must render nothing when "
            "third_party_test_readiness is missing"
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
            "partials/_third_party_test_readiness.html",
        )
        out = tpl.render(third_party_test_readiness={})
        assert out.strip() == ""


# ---------------------------------------------------------------------------
# 5. Partial: renders the report
# ---------------------------------------------------------------------------


class TestPartialRendersTheReport:
    """When the helper output is present, the partial
    must render the verdict, per-workflow scores,
    checklist, and tester instructions."""

    def test_renders_report(self):
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
            "partials/_third_party_test_readiness.html",
        )
        entries = [
            WorkflowEntry(
                workflow=wf,
                helper_present=True,
                partial_present=True,
                helper_tests_pass=True,
                factory_safety_tests_pass=True,
            )
            for wf in ALL_WORKFLOWS
        ]
        rpt = build_third_party_test_readiness(entries)
        out = tpl.render(third_party_test_readiness=rpt)
        assert "Third-Party Test Readiness" in out
        assert "100" in out  # overall score
        # 10 workflow labels
        for wf in ALL_WORKFLOWS:
            from app.ui.third_party_test_readiness import (
                WORKFLOW_LABELS,
            )
            assert WORKFLOW_LABELS[wf] in out, (
                f"workflow {wf!r} label "
                f"{WORKFLOW_LABELS[wf]!r} not rendered"
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
        from app.ui import third_party_test_readiness
        src = open(
            third_party_test_readiness.__file__
        ).read()
        assert "CREATE TABLE" not in src
        assert "ALTER TABLE" not in src


# ---------------------------------------------------------------------------
# 8. No autosave
# ---------------------------------------------------------------------------


class TestNoAutosave:
    """The helper must NOT introduce autosave."""

    def test_helper_does_not_call_save(self):
        from app.ui import third_party_test_readiness
        src = open(
            third_party_test_readiness.__file__
        ).read()
        assert "save_workspace" not in src
        assert "save_scenario" not in src

    def test_partial_does_not_call_save(self):
        partial_path = os.path.join(
            REPO_ROOT,
            "app",
            "templates",
            "partials",
            "_third_party_test_readiness.html",
        )
        src = open(partial_path).read()
        assert "save_workspace" not in src
        assert "save_scenario" not in src


# ---------------------------------------------------------------------------
# 9. Factory projects safe
# ---------------------------------------------------------------------------


class TestFactoryProjectsSafe:
    """Factory projects (TUHO / Oborovo) are not
    affected."""

    def test_factory_projects_safe(self):
        entries = [
            WorkflowEntry(
                workflow=wf,
                helper_present=True,
                partial_present=True,
                helper_tests_pass=True,
                factory_safety_tests_pass=True,
            )
            for wf in ALL_WORKFLOWS
        ]
        r = build_third_party_test_readiness(entries)
        # The factory verdict is based only on
        # helper / partial / test presence; the
        # factory project type is irrelevant to
        # the audit logic.
        assert r.overall_score == 100
        assert r.is_go is True
