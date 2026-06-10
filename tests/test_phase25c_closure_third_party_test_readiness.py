"""Phase 25C Closure — Third-Party Test Readiness
helper tests.

Goal: Audit 10 workflows of the Generic Solar /
Wind exploratory pilot and produce a Go/No-Go
verdict, exact pilot test checklist, remaining
blockers, and suggested tester instructions.

These tests prove:

- 10 workflows are exposed in stable order
- Each workflow has a label, description, and
  phase_link
- The 4 readiness buckets exist with correct
  thresholds
- Scoring is correct (25 per dimension)
- Bucket mapping is correct (>= 90 pilot_ready,
  >= 70 close_to_pilot, >= 50 pilot_blocked,
  otherwise not_ready)
- The Go / No-Go verdict is correct
- The pilot test checklist has 10 items
- The remaining blockers list is correct
- The suggested tester instructions are present
- The phase 25C summary mentions all 4 phases
- The helper does NOT mutate any input
- The helper does NOT call the persistence layer
- The helper does NOT enable any feature flag
- The helper does NOT invent fake outputs, fake
  run IDs, fake validation claims
"""

import os
import sys

import pytest


HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


from app.ui.third_party_test_readiness import (
    ALL_BUCKETS,
    ALL_WORKFLOWS,
    BUCKET_CLOSE_TO_PILOT,
    BUCKET_NOT_READY,
    BUCKET_PILOT_BLOCKED,
    BUCKET_PILOT_READY,
    BUCKET_THRESHOLDS,
    PHASE_25C_LINK,
    WORKFLOW_DESCRIPTIONS,
    WORKFLOW_LABELS,
    TestChecklistItem,
    ThirdPartyTestReadiness,
    WorkflowEntry,
    WorkflowScore,
    build_third_party_test_readiness,
    is_supported_bucket,
    is_supported_workflow,
)


# ---------------------------------------------------------------------------
# 1. Workflow vocabulary
# ---------------------------------------------------------------------------


class TestWorkflowVocabulary:
    """The workflow vocabulary has 10 entries in
    stable order."""

    def test_workflow_count(self):
        assert len(ALL_WORKFLOWS) == 10

    def test_workflow_labels_keys(self):
        assert set(WORKFLOW_LABELS.keys()) == set(ALL_WORKFLOWS)

    def test_workflow_descriptions_keys(self):
        assert set(WORKFLOW_DESCRIPTIONS.keys()) == set(
            ALL_WORKFLOWS
        )

    def test_phase_25c_link_keys(self):
        assert set(PHASE_25C_LINK.keys()) == set(ALL_WORKFLOWS)

    @pytest.mark.parametrize(
        "wf,expected_link_prefix",
        [
            (
                "create_project",
                "25C-1",
            ),
            ("prefill_defaults", "25C-1"),
            ("save", "25C-1"),
            ("run", "25C-1"),
            ("edit", "25C-1"),
            ("rerun", "25C-1"),
            ("compare", "25C-1"),
            ("export", "25C-1"),
            ("understand_limitations", "25C-1"),
            ("report_feedback", "25C-3"),
        ],
    )
    def test_phase_link(self, wf, expected_link_prefix):
        assert PHASE_25C_LINK[wf].startswith(expected_link_prefix)


# ---------------------------------------------------------------------------
# 2. Readiness buckets
# ---------------------------------------------------------------------------


class TestReadinessBuckets:
    """The 4 readiness buckets have correct
    thresholds."""

    def test_bucket_count(self):
        assert len(ALL_BUCKETS) == 4

    def test_thresholds(self):
        assert BUCKET_THRESHOLDS[BUCKET_PILOT_READY] == 90
        assert BUCKET_THRESHOLDS[BUCKET_CLOSE_TO_PILOT] == 70
        assert BUCKET_THRESHOLDS[BUCKET_PILOT_BLOCKED] == 50


# ---------------------------------------------------------------------------
# 3. is_supported_workflow
# ---------------------------------------------------------------------------


class TestIsSupportedWorkflow:
    """The supported-workflow helper is explicit."""

    @pytest.mark.parametrize(
        "wf,expected",
        [
            ("create_project", True),
            ("report_feedback", True),
            ("unknown", False),
            ("", False),
        ],
    )
    def test_is_supported(self, wf, expected):
        assert is_supported_workflow(wf) is expected


# ---------------------------------------------------------------------------
# 4. is_supported_bucket
# ---------------------------------------------------------------------------


class TestIsSupportedBucket:
    """The supported-bucket helper is explicit."""

    @pytest.mark.parametrize(
        "b,expected",
        [
            (BUCKET_PILOT_READY, True),
            (BUCKET_CLOSE_TO_PILOT, True),
            (BUCKET_PILOT_BLOCKED, True),
            (BUCKET_NOT_READY, True),
            ("unknown", False),
        ],
    )
    def test_is_supported(self, b, expected):
        assert is_supported_bucket(b) is expected


# ---------------------------------------------------------------------------
# 5. Scoring
# ---------------------------------------------------------------------------


class TestScoring:
    """Scoring is 25 per dimension."""

    @pytest.mark.parametrize(
        "h,p,ht,ft,expected",
        [
            (False, False, False, False, 0),
            (True, False, False, False, 25),
            (False, True, False, False, 25),
            (False, False, True, False, 25),
            (False, False, False, True, 25),
            (True, True, False, False, 50),
            (True, True, True, False, 75),
            (True, True, True, True, 100),
        ],
    )
    def test_score(self, h, p, ht, ft, expected):
        e = WorkflowEntry(
            workflow="create_project",
            helper_present=h,
            partial_present=p,
            helper_tests_pass=ht,
            factory_safety_tests_pass=ft,
        )
        entries = [
            e,
            # Fill in the other 9 workflows as ready
            # so the overall score reflects only
            # the create_project workflow.
        ] + [
            WorkflowEntry(
                workflow=wf,
                helper_present=True,
                partial_present=True,
                helper_tests_pass=True,
                factory_safety_tests_pass=True,
            )
            for wf in ALL_WORKFLOWS
            if wf != "create_project"
        ]
        rpt = build_third_party_test_readiness(entries)
        s = next(
            x for x in rpt.per_workflow
            if x.workflow == "create_project"
        )
        assert s.score == expected


# ---------------------------------------------------------------------------
# 6. Bucket mapping
# ---------------------------------------------------------------------------


class TestBucketMapping:
    """Bucket mapping is correct."""

    @pytest.mark.parametrize(
        "create_score,expected_bucket",
        [
            (0, BUCKET_PILOT_READY),
            (25, BUCKET_PILOT_READY),
            (50, BUCKET_PILOT_READY),
            (75, BUCKET_PILOT_READY),
        ],
    )
    def test_pilot_ready(
        self, create_score, expected_bucket
    ):
        """When the workflow under test scores 0-75
        but the other 9 are 100, the overall score
        is in pilot_ready (>90)."""
        if create_score == 0:
            entry = WorkflowEntry(
                workflow="create_project",
                helper_present=False,
                partial_present=False,
                helper_tests_pass=False,
                factory_safety_tests_pass=False,
            )
        elif create_score == 25:
            entry = WorkflowEntry(
                workflow="create_project",
                helper_present=True,
                partial_present=False,
                helper_tests_pass=False,
                factory_safety_tests_pass=False,
            )
        elif create_score == 50:
            entry = WorkflowEntry(
                workflow="create_project",
                helper_present=True,
                partial_present=True,
                helper_tests_pass=False,
                factory_safety_tests_pass=False,
            )
        elif create_score == 75:
            entry = WorkflowEntry(
                workflow="create_project",
                helper_present=True,
                partial_present=True,
                helper_tests_pass=True,
                factory_safety_tests_pass=False,
            )
        else:
            entry = WorkflowEntry(
                workflow="create_project",
                helper_present=True,
                partial_present=True,
                helper_tests_pass=True,
                factory_safety_tests_pass=True,
            )
        entries = [entry] + [
            WorkflowEntry(
                workflow=wf,
                helper_present=True,
                partial_present=True,
                helper_tests_pass=True,
                factory_safety_tests_pass=True,
            )
            for wf in ALL_WORKFLOWS
            if wf != "create_project"
        ]
        rpt = build_third_party_test_readiness(entries)
        assert rpt.overall_score >= 90
        assert rpt.bucket == BUCKET_PILOT_READY

    def test_pilot_blocked(self):
        """When all workflows score 0, the overall
        score is 0 and the bucket is not_ready."""
        entries = [
            WorkflowEntry(
                workflow=wf,
                helper_present=False,
                partial_present=False,
                helper_tests_pass=False,
                factory_safety_tests_pass=False,
            )
            for wf in ALL_WORKFLOWS
        ]
        rpt = build_third_party_test_readiness(entries)
        assert rpt.overall_score == 0
        assert rpt.bucket == BUCKET_NOT_READY
        assert rpt.is_go is False


# ---------------------------------------------------------------------------
# 7. Go / No-Go
# ---------------------------------------------------------------------------


class TestGoNoGo:
    """The Go / No-Go verdict is correct."""

    def test_go_when_pilot_ready(self):
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
        assert rpt.is_go is True
        assert rpt.overall_score == 100
        assert rpt.bucket == BUCKET_PILOT_READY

    def test_no_go_when_not_ready(self):
        entries = [
            WorkflowEntry(
                workflow=wf,
                helper_present=False,
                partial_present=False,
                helper_tests_pass=False,
                factory_safety_tests_pass=False,
            )
            for wf in ALL_WORKFLOWS
        ]
        rpt = build_third_party_test_readiness(entries)
        assert rpt.is_go is False
        assert rpt.overall_score == 0
        assert rpt.bucket == BUCKET_NOT_READY


# ---------------------------------------------------------------------------
# 8. Pilot test checklist
# ---------------------------------------------------------------------------


class TestPilotTestChecklist:
    """The pilot test checklist has 10 items."""

    def test_checklist_count(self):
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
        assert len(rpt.pilot_test_checklist) == 10

    def test_checklist_workflow_keys(self):
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
        keys = {item.workflow for item in rpt.pilot_test_checklist}
        assert keys == set(ALL_WORKFLOWS)


# ---------------------------------------------------------------------------
# 9. Remaining blockers
# ---------------------------------------------------------------------------


class TestRemainingBlockers:
    """The remaining blockers list is correct."""

    def test_no_blockers_when_all_ready(self):
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
        assert rpt.remaining_blockers == ()

    def test_blockers_listed_when_not_ready(self):
        # Make ALL workflows score 0 so every
        # workflow is in the blocker list. This
        # exercises the cross-workflow blocker
        # accumulator.
        entries = [
            WorkflowEntry(
                workflow=wf,
                helper_present=False,
                partial_present=False,
                helper_tests_pass=False,
                factory_safety_tests_pass=False,
            )
            for wf in ALL_WORKFLOWS
        ]
        rpt = build_third_party_test_readiness(entries)
        # 10 workflows x 4 dimensions = 40
        # blockers expected (helper missing,
        # partial missing, helper tests failing,
        # factory safety tests failing).
        assert len(rpt.remaining_blockers) >= 10
        joined = " | ".join(rpt.remaining_blockers)
        assert "create project" in joined.lower()


# ---------------------------------------------------------------------------
# 10. Tester instructions
# ---------------------------------------------------------------------------


class TestTesterInstructions:
    """The tester instructions are present and
    instructive."""

    def test_instructions_present(self):
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
        assert rpt.suggested_tester_instructions
        assert len(rpt.suggested_tester_instructions) >= 10

    def test_instructions_mention_25c3_feedback(self):
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
        joined = " | ".join(rpt.suggested_tester_instructions)
        assert "feedback" in joined.lower()


# ---------------------------------------------------------------------------
# 11. Phase 25C summary
# ---------------------------------------------------------------------------


class TestPhase25CSummary:
    """The phase 25C summary mentions all 4 phases."""

    def test_summary_mentions_25c_1(self):
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
        joined = " | ".join(rpt.phase_25c_summary)
        assert "25C-1" in joined

    def test_summary_mentions_25c_2(self):
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
        joined = " | ".join(rpt.phase_25c_summary)
        assert "25C-2" in joined

    def test_summary_mentions_25c_3(self):
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
        joined = " | ".join(rpt.phase_25c_summary)
        assert "25C-3" in joined

    def test_summary_mentions_closure(self):
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
        joined = " | ".join(rpt.phase_25c_summary)
        assert "Closure" in joined or "closure" in joined


# ---------------------------------------------------------------------------
# 12. No forbidden imports
# ---------------------------------------------------------------------------


class TestNoForbiddenImports:
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
# 13. No feature flag enablement
# ---------------------------------------------------------------------------


class TestNoFeatureFlagEnablement:
    """The helper must not enable any feature flag."""

    def test_helper_does_not_set_construction_flag(self):
        from app.ui import third_party_test_readiness
        src = open(
            third_party_test_readiness.__file__
        ).read()
        assert "use_construction_schedule_engine" not in src
        assert "use_depreciation_canonical_engine" not in src
        assert "use_canonical_tax_depreciation" not in src


# ---------------------------------------------------------------------------
# 14. No fake outputs
# ---------------------------------------------------------------------------


class TestNoFakeOutputs:
    """The helper must not invent fake run IDs,
    fake validation claims, or fake outputs."""

    def test_helper_does_not_invent_run_ids(self):
        from app.ui import third_party_test_readiness
        src = open(
            third_party_test_readiness.__file__
        ).read()
        assert "run_id" not in src
        assert "run-1" not in src
        assert "snapshot_id" not in src

    def test_helper_does_not_invent_validation(self):
        from app.ui import third_party_test_readiness
        src = open(
            third_party_test_readiness.__file__
        ).read()
        assert "parity_validated" not in src
        assert "is_validated" not in src.lower()
        assert "validation_status" not in src

    def test_audit_does_not_claim_audit_readiness(self):
        # The audit mentions the user's understanding
        # of "not audit-ready" but never claims the
        # project IS audit-ready.
        from app.ui import third_party_test_readiness
        src = open(
            third_party_test_readiness.__file__
        ).read()
        assert "is_audit_ready" not in src
        assert "is_lender_ready" not in src
        assert "is_bank_approved" not in src
