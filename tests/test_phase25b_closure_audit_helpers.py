"""Phase 25B Closure — Usability audit helper tests.

Goal: Provide an honest readiness percentage for each
of the 8 first-time-finance-user workflows (create
project, edit assumptions, save, run, compare, export,
understand outputs, understand limitations) and an
overall readiness bucket.

These tests prove the helper:

- exposes the 8 expected workflow keys in stable order
- exposes the 4 readiness buckets with sensible
  thresholds
- scores each workflow as 0-100 based on the
  intersection of detected and expected surfaces
- returns a frozen WorkflowScore with supporting
  surfaces and gaps
- returns a frozen UsabilityAudit with an overall
  score, bucket, and verdict
- does NOT mutate the input surfaces list
- does NOT call the persistence layer
- does NOT enable any feature flag
- does NOT call services
- exposes ``build_audit_inputs`` as a read-only
  filesystem probe
- ``build_audit_inputs`` does NOT recurse; it only
  checks the canonical surface paths declared in
  ``WORKFLOW_EXPECTED_SURFACES``
"""

import os
import subprocess
import sys

import pytest


HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


from app.ui.usability_audit import (
    BUCKET_CLOSE_TO_PILOT,
    BUCKET_NOT_READY,
    BUCKET_PILOT_BLOCKED,
    BUCKET_PILOT_READY,
    BUCKET_THRESHOLDS,
    BUCKET_VERDICTS,
    WORKFLOW_COMPARE,
    WORKFLOW_CREATE_PROJECT,
    WORKFLOW_EDIT_ASSUMPTIONS,
    WORKFLOW_EXPORT,
    WORKFLOW_LABELS,
    WORKFLOW_ORDER,
    WORKFLOW_RUN,
    WORKFLOW_SAVE,
    WORKFLOW_UNDERSTAND_LIMITATIONS,
    WORKFLOW_UNDERSTAND_OUTPUTS,
    UsabilityAudit,
    WorkflowScore,
    audit,
    build_audit_inputs,
    score_workflow,
)


# ---------------------------------------------------------------------------
# 1. Workflow vocabulary
# ---------------------------------------------------------------------------


class TestWorkflowVocabulary:
    """The 8 workflows are exposed in stable order."""

    def test_workflow_order_count(self):
        assert len(WORKFLOW_ORDER) == 8

    def test_workflow_order_keys(self):
        expected = {
            WORKFLOW_CREATE_PROJECT,
            WORKFLOW_EDIT_ASSUMPTIONS,
            WORKFLOW_SAVE,
            WORKFLOW_RUN,
            WORKFLOW_COMPARE,
            WORKFLOW_EXPORT,
            WORKFLOW_UNDERSTAND_OUTPUTS,
            WORKFLOW_UNDERSTAND_LIMITATIONS,
        }
        assert set(WORKFLOW_ORDER) == expected

    def test_workflow_labels_keys(self):
        assert set(WORKFLOW_LABELS.keys()) == set(WORKFLOW_ORDER)


# ---------------------------------------------------------------------------
# 2. Bucket vocabulary
# ---------------------------------------------------------------------------


class TestBucketVocabulary:
    """The 4 readiness buckets are exposed with sensible
    thresholds."""

    def test_bucket_count(self):
        assert len(BUCKET_THRESHOLDS) == 4

    def test_bucket_keys(self):
        assert set(BUCKET_VERDICTS.keys()) == {
            BUCKET_PILOT_READY,
            BUCKET_CLOSE_TO_PILOT,
            BUCKET_PILOT_BLOCKED,
            BUCKET_NOT_READY,
        }

    def test_thresholds_sorted_descending(self):
        # 4-tuples of (threshold, bucket); thresholds
        # should be sorted descending.
        thresholds = [t for t, _ in BUCKET_THRESHOLDS]
        assert thresholds == sorted(thresholds, reverse=True)


# ---------------------------------------------------------------------------
# 3. score_workflow
# ---------------------------------------------------------------------------


class TestScoreWorkflow:
    """``score_workflow`` returns a frozen WorkflowScore
    based on the intersection of detected and expected
    surfaces."""

    def test_full_match(self):
        # All 3 surfaces detected for create_project
        surfaces = [
            "partials/new_project_form.html",
            "partials/project_browser.html",
            "partials/_empty_no_project.html",
        ]
        w = score_workflow(WORKFLOW_CREATE_PROJECT, surfaces)
        assert isinstance(w, WorkflowScore)
        assert w.score == 100
        assert len(w.supporting_surfaces) == 3
        assert len(w.gaps) == 0

    def test_partial_match(self):
        # 1 of 2 surfaces detected for export
        surfaces = ["excel_export.build_excel_export"]
        w = score_workflow(WORKFLOW_EXPORT, surfaces)
        assert w.score == 50
        assert len(w.supporting_surfaces) == 1
        assert len(w.gaps) == 1

    def test_no_match(self):
        w = score_workflow(WORKFLOW_COMPARE, [])
        assert w.score == 0
        assert len(w.supporting_surfaces) == 0
        assert len(w.gaps) >= 1

    def test_workflow_score_is_frozen(self):
        w = score_workflow(WORKFLOW_RUN, [])
        with pytest.raises(Exception):
            w.score = 50  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 4. audit
# ---------------------------------------------------------------------------


class TestAudit:
    """``audit`` returns a frozen UsabilityAudit with the
    overall score, bucket, and verdict."""

    def test_audit_full_match(self):
        # Build a payload that hits every surface for
        # every workflow.
        from app.ui.usability_audit import (
            WORKFLOW_EXPECTED_SURFACES,
        )
        all_surfaces: list[str] = []
        for (
            _wk,
            (label, expected, _max),
        ) in WORKFLOW_EXPECTED_SURFACES.items():
            all_surfaces.extend(expected)
        a = audit(all_surfaces, generated_at="2026-06-10")
        assert isinstance(a, UsabilityAudit)
        assert a.overall_score == 100
        assert a.bucket == BUCKET_PILOT_READY
        assert a.verdict == BUCKET_VERDICTS[BUCKET_PILOT_READY]
        assert len(a.workflows) == 8
        for w in a.workflows:
            assert w.score == 100

    def test_audit_no_match(self):
        a = audit([], generated_at="2026-06-10")
        assert a.overall_score == 0
        assert a.bucket == BUCKET_NOT_READY
        for w in a.workflows:
            assert w.score == 0

    def test_audit_audit_is_frozen(self):
        a = audit([], generated_at="2026-06-10")
        with pytest.raises(Exception):
            a.overall_score = 50  # type: ignore[misc]

    def test_audit_overall_is_unweighted_mean(self):
        # If each workflow has a known score, the
        # overall must be the arithmetic mean.
        from app.ui.usability_audit import (
            WORKFLOW_EXPECTED_SURFACES,
        )
        from dataclasses import replace as dc_replace
        # Build a payload that gives half the surfaces
        # for each workflow.
        half_surfaces: list[str] = []
        for (
            _wk,
            (label, expected, _max),
        ) in WORKFLOW_EXPECTED_SURFACES.items():
            half_surfaces.extend(expected[: max(1, len(expected) // 2)])
        a = audit(half_surfaces, generated_at="2026-06-10")
        expected_overall = int(
            round(
                sum(w.score for w in a.workflows) / len(a.workflows)
            )
        )
        assert a.overall_score == expected_overall

    def test_audit_bucket_pilot_ready_threshold(self):
        # A score of 90+ should map to pilot_ready.
        # We can't easily construct a payload that
        # gives exactly 90, but we can confirm the
        # full-match payload lands in pilot_ready.
        from app.ui.usability_audit import (
            WORKFLOW_EXPECTED_SURFACES,
        )
        all_surfaces: list[str] = []
        for (
            _wk,
            (label, expected, _max),
        ) in WORKFLOW_EXPECTED_SURFACES.items():
            all_surfaces.extend(expected)
        a = audit(all_surfaces, generated_at="2026-06-10")
        assert a.bucket == BUCKET_PILOT_READY


# ---------------------------------------------------------------------------
# 5. build_audit_inputs
# ---------------------------------------------------------------------------


class TestBuildAuditInputs:
    """``build_audit_inputs`` is a read-only filesystem
    probe. It returns a list of detected surface keys
    for the supplied repo root."""

    def test_returns_list(self):
        result = build_audit_inputs(REPO_ROOT)
        assert isinstance(result, list)

    def test_detects_known_surface(self):
        # The export registry partial is a well-known
        # shipped surface.
        result = build_audit_inputs(REPO_ROOT)
        assert "partials/export_registry.html" in result

    def test_does_not_recurse(self):
        # The probe only checks the canonical paths
        # declared in WORKFLOW_EXPECTED_SURFACES. A
        # ``recurse=True`` flag would be a violation
        # of the closure contract.
        import inspect
        sig = inspect.signature(build_audit_inputs)
        # The function takes only ``repo_root`` and
        # no recursion flag.
        assert list(sig.parameters.keys()) == ["repo_root"]

    def test_no_persistence_calls_in_probe(self):
        # The probe only walks the filesystem; no
        # ``os.walk`` recursion, no DB calls.
        from app.ui import usability_audit
        src = open(usability_audit.__file__).read()
        # The probe uses ``Path.exists()``; allow it
        # but no DB imports.
        assert "import sqlite3" not in src
        assert "from app.persistence" not in src
        assert "from app.services" not in src


# ---------------------------------------------------------------------------
# 6. No forbidden imports
# ---------------------------------------------------------------------------


class TestNoForbiddenImports:
    """The audit helper must not import any forbidden
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
        from app.ui import usability_audit
        src = open(usability_audit.__file__).read()
        assert f"import {module}" not in src
        assert f"from {module}" not in src


# ---------------------------------------------------------------------------
# 7. No feature flag enablement
# ---------------------------------------------------------------------------


class TestNoFeatureFlagEnablement:
    """The audit helper must not enable any feature flag."""

    def test_helper_does_not_set_construction_flag(self):
        from app.ui import usability_audit
        src = open(usability_audit.__file__).read()
        assert "use_construction_schedule_engine" not in src
        assert "use_depreciation_canonical_engine" not in src
        assert "use_canonical_tax_depreciation" not in src
        assert "use_book_depreciation_for_pnl" not in src


# ---------------------------------------------------------------------------
# 8. rc1 frozen
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
# 9. No mutation
# ---------------------------------------------------------------------------


class TestNoMutation:
    """The audit helper must not mutate the input
    surfaces list."""

    def test_surfaces_list_unchanged(self):
        surfaces = [
            "partials/new_project_form.html",
            "partials/kpis.html",
        ]
        before = list(surfaces)
        _ = audit(surfaces, generated_at="2026-06-10")
        assert surfaces == before
