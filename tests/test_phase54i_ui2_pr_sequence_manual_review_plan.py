"""Phase 54I — UI-2 PR sequence and manual review plan guardrails.

Verifies:
- 6 UI-2 PRs in sequence
- All 6 marked draft-only + auto-merge NO
- Per-PR expected files
- Per-PR tests required
- Per-PR no-go copy checks
- Stack policy: draft-only stacking allowed
- Manual review policy
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "phase54i_ui2_pr_sequence_manual_review_plan.md"
JSON_RPT = REPO_ROOT / "reports" / "phase54i_ui2_pr_sequence_manual_review_plan.json"


class TestDeliverablesExist:
    def test_doc_exists(self):
        assert DOC.exists()

    def test_json_report_exists(self):
        assert JSON_RPT.exists()

    def test_phase_field_is_54i(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["phase"] == "54I"

    def test_recommended_next_step_is_54j(self):
        data = json.loads(JSON_RPT.read_text())
        assert "54J" in data["recommended_next_step"]


class TestUI2Sequence:
    EXPECTED = ["UI-2.1", "UI-2.2", "UI-2.3", "UI-2.4", "UI-2.5", "UI-2.6"]

    @pytest.mark.parametrize("pr", EXPECTED)
    def test_pr_in_sequence(self, pr):
        data = json.loads(JSON_RPT.read_text())
        ids = [s["id"] for s in data["ui2_sequence"]]
        assert pr in ids

    @pytest.mark.parametrize("pr", EXPECTED)
    def test_pr_auto_merge_false(self, pr):
        data = json.loads(JSON_RPT.read_text())
        seq = {s["id"]: s for s in data["ui2_sequence"]}
        assert seq[pr]["auto_merge"] is False

    @pytest.mark.parametrize("pr", EXPECTED)
    def test_pr_draft_only(self, pr):
        data = json.loads(JSON_RPT.read_text())
        seq = {s["id"]: s for s in data["ui2_sequence"]}
        assert seq[pr]["draft_only"] is True

    @pytest.mark.parametrize("pr", EXPECTED)
    def test_pr_stackable(self, pr):
        data = json.loads(JSON_RPT.read_text())
        seq = {s["id"]: s for s in data["ui2_sequence"]}
        assert seq[pr]["stackable"] is True


class TestExpectedChangedFiles:
    @pytest.mark.parametrize("pr", ["UI-2.1", "UI-2.2", "UI-2.3", "UI-2.4", "UI-2.6"])
    def test_pr_has_expected_files(self, pr):
        data = json.loads(JSON_RPT.read_text())
        files = data["expected_changed_files"][pr]
        assert len(files) >= 1

    def test_ui25_no_new_files(self):
        # UI-2.5 reuses existing macro
        data = json.loads(JSON_RPT.read_text())
        files = data["expected_changed_files"]["UI-2.5"]
        assert any("index.html" in f for f in files)


class TestTestsRequired:
    @pytest.mark.parametrize("pr", ["UI-2.1", "UI-2.2", "UI-2.3", "UI-2.4", "UI-2.5", "UI-2.6"])
    def test_pr_has_tests_required(self, pr):
        data = json.loads(JSON_RPT.read_text())
        tests = data["tests_required"][pr]
        assert len(tests) >= 1
        assert "no-go copy tests" in tests or "no-go copy" in str(tests)

    @pytest.mark.parametrize("pr", ["UI-2.1", "UI-2.2", "UI-2.3", "UI-2.4", "UI-2.5", "UI-2.6"])
    def test_pr_has_visual_review(self, pr):
        data = json.loads(JSON_RPT.read_text())
        tests = data["tests_required"][pr]
        assert any("visual review" in t for t in tests)


class TestStackPolicy:
    def test_draft_only_stacking_allowed(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["stack_policy"]["draft_only_stacking_allowed"] is True

    def test_one_ready_at_a_time(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["stack_policy"]["only_one_ready_at_a_time"] is True

    def test_never_auto_merge(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["stack_policy"]["never_auto_merge"] is True


class TestManualReviewPolicy:
    def test_required_items(self):
        data = json.loads(JSON_RPT.read_text())
        required = data["manual_review_policy"]["required_for_each_pr"]
        for item in [
            "user review of the diff",
            "user review of rendered HTML",
            "confirmation that no-go copy checks pass",
            "confirmation that rollback plan is feasible",
            "sign-off before merge"
        ]:
            assert any(item in r for r in required)


class TestNoGoChecks:
    def test_ui21_real_time_forbidden(self):
        data = json.loads(JSON_RPT.read_text())
        checks = " ".join(data["no_go_checks_required"]["UI-2.1"])
        assert "real-time" in checks or "live" in checks

    def test_ui24_lender_grade_forbidden(self):
        data = json.loads(JSON_RPT.read_text())
        checks = data["no_go_checks_required"]["UI-2.4"]
        # UI-2.4 has a list of checks
        checks_text = " ".join(checks) if isinstance(checks, list) else checks
        assert "lender-grade" in checks_text or "trusted template" in checks_text

    def test_ui26_real_time_forbidden(self):
        data = json.loads(JSON_RPT.read_text())
        checks = " ".join(data["no_go_checks_required"]["UI-2.6"])
        assert "Real-time" in checks or "Live" in checks
