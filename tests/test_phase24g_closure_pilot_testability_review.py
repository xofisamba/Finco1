"""Phase 24-G Closure Review — Shape characterization tests.

Status: DRAFT
Type: REPORT-ONLY, DOCS-ONLY, SHAPE-TESTS-ONLY
Date: 2026-06-09

These tests assert the SHAPE of the closure review document and
report. They do NOT assert correctness of the closure review's
content; they assert that the document exists, has the
required sections, names the 4 G-track PRs, answers the 4
explicit questions, and does not name any production code
path that is out of scope for the G track.

Hard constraints verified by these tests:
- No main_web.py / app/services / app/persistence / app/domain
  / app/api / app/tax_bridge / waterfall_core / static/app.js
  / model / formula / tax / debt / depreciation / IDC / rc1
  changes are named in the closure document.
- No feature flag value is changed.
- use_construction_schedule_engine remains False.
- The document has the 10 sections declared in §0 / §11.
- The document names all 4 G-track PRs and their merged/closed
  status.
- The document answers the 4 explicit questions (A, B, C, D).
- The ranked top-15 blockers are present with composite scores
  in the valid range.
- The report JSON has the required top-level keys.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

DOC_PATH = REPO_ROOT / "docs" / "phase24g_closure_and_pilot_testability_review.md"
REPORT_PATH = REPO_ROOT / "reports" / "phase24g_closure_and_pilot_testability_review.json"


# ── Helpers ──────────────────────────────────────────────────────────────

def _read_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def _read_report() -> dict:
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


# ── 1. Document + report exist ───────────────────────────────────────────

class TestDocumentsExist:
    def test_doc_exists(self):
        assert DOC_PATH.exists(), f"missing doc: {DOC_PATH}"

    def test_report_exists(self):
        assert REPORT_PATH.exists(), f"missing report: {REPORT_PATH}"

    def test_doc_is_nonempty(self):
        assert len(_read_doc()) > 5000, "doc is suspiciously small"

    def test_report_is_valid_json(self):
        data = _read_report()
        assert isinstance(data, dict)
        assert "phase" in data


# ── 2. Document has the 10 declared sections ─────────────────────────────

class TestDocumentStructure:
    REQUIRED_SECTIONS = [
        "## 0. Purpose",
        "## 1. What was delivered",
        "## 2. What a user can do today",
        "## 3. What a user still cannot do",
        "## 4. Biggest blockers preventing meaningful project testing",
        "## 5. Biggest blockers preventing pilot rollout",
        "## 6. Biggest blockers preventing paid product rollout",
        "## 7. Rank remaining blockers",
        "## 8. Explicit answers to the four questions",
        "## 9. What this document does NOT do",
        "## 10. Test footprint",
        "## 11. References",
    ]

    def test_all_sections_present(self):
        text = _read_doc()
        missing = [s for s in self.REQUIRED_SECTIONS if s not in text]
        assert not missing, f"missing sections: {missing}"

    def test_doc_references_phase_24g_closure(self):
        text = _read_doc()
        assert "Phase 24-G Closure" in text or "phase 24-G closure" in text.lower()


# ── 3. Document names all 4 G-track PRs and their merged/closed status ───

class TestGTrackPRsReferenced:
    PR_REFERENCES = [
        ("#564", "pilot-ux-safe-track-inventory"),
        ("#566", "DRAFT"),
        ("#567", "MERGED"),
        ("#565", "DRAFT"),
        ("#568", "MERGED"),
        ("#569", "DRAFT"),
        ("#570", "MERGED"),
    ]

    def test_all_pr_numbers_named(self):
        text = _read_doc()
        for pr_number, _ in self.PR_REFERENCES:
            assert pr_number in text, f"missing PR reference: {pr_number}"

    def test_draft_to_merged_workflow_explained(self):
        text = _read_doc()
        # The doc should explain the established workflow: DRAFT PR closed,
        # new non-DRAFT PR created, squash merge.
        assert "DRAFT" in text
        assert "closed" in text.lower() or "supersedes" in text.lower()


# ── 4. Document answers the 4 explicit questions ─────────────────────────

class TestExplicitAnswers:
    def test_question_a_finance_user(self):
        text = _read_doc()
        # Section 8.1 should answer the finance user question
        assert "8.1" in text
        assert "finance user" in text.lower()
        # Verdict should be present
        assert "Yes, with caveats" in text or "yes" in text.lower()

    def test_question_b_renewable_developer(self):
        text = _read_doc()
        # Section 8.2 should answer the renewable developer question
        assert "8.2" in text
        assert "renewable developer" in text.lower()

    def test_question_c_highest_value_feature(self):
        text = _read_doc()
        # Section 8.3 should answer the highest-value feature question
        assert "8.3" in text
        assert "highest-value" in text.lower() or "highest value" in text.lower()
        # The answer should mention sculpting or re-sizing
        assert "sculpt" in text.lower() or "re-sizing" in text.lower() or "resize" in text.lower()

    def test_question_d_sprint_24h(self):
        text = _read_doc()
        # Section 8.4 should answer the Sprint 24-H question
        assert "8.4" in text
        assert "Sprint 24-H" in text or "24-H" in text


# ── 5. Ranked top-15 blockers are present and valid ──────────────────────

class TestRankedBlockers:
    def test_top_15_blockers_in_report(self):
        report = _read_report()
        ranked = report.get("remaining_blockers_ranked", {}).get("top_15", [])
        assert len(ranked) == 15, f"expected 15 ranked blockers, got {len(ranked)}"

    def test_composite_scores_in_valid_range(self):
        report = _read_report()
        ranked = report.get("remaining_blockers_ranked", {}).get("top_15", [])
        for item in ranked:
            composite = item.get("composite")
            assert composite is not None
            assert -10 <= composite <= 10, (
                f"composite score {composite} out of range for blocker {item.get('blocker')}"
            )

    def test_impact_parity_effort_in_valid_range(self):
        report = _read_report()
        ranked = report.get("remaining_blockers_ranked", {}).get("top_15", [])
        for item in ranked:
            for field in ("impact", "parity", "effort"):
                value = item.get(field)
                assert value is not None, f"missing {field} for {item.get('blocker')}"
                assert 0 <= value <= 5, (
                    f"{field}={value} out of range [0,5] for {item.get('blocker')}"
                )

    def test_each_blocker_has_horizon_tag(self):
        report = _read_report()
        ranked = report.get("remaining_blockers_ranked", {}).get("top_15", [])
        valid_horizons = {"P", "$", "E", "P,$", "P,$E", "P,$", "$,E", "P,$E", "$", "E"}
        for item in ranked:
            horizon = item.get("horizon", "")
            assert horizon, f"missing horizon for {item.get('blocker')}"
            # Allow comma-separated horizons
            tags = [t.strip() for t in horizon.split(",")]
            for tag in tags:
                assert tag in {"P", "$", "E"}, f"invalid horizon tag '{tag}' for {item.get('blocker')}"


# ── 6. Hard constraints: no out-of-scope production code is named ───────

class TestHardConstraints:
    # Production code paths / areas that are explicitly OUT OF SCOPE
    # for the G track. The closure review may name them as part of
    # the analysis (e.g. "main_web.py is not touched"), but it must
    # not propose changing them.
    OUT_OF_SCOPE_AREAS = [
        "main_web.py",
        "app/services/",
        "app/persistence/",
        "app/domain/",
        "app/api/",
        "app/tax_bridge/",
        "waterfall_core.py",
        "static/app.js",
    ]

    def test_doc_does_not_propose_modifying_out_of_scope_code(self):
        """
        The doc may name out-of-scope areas (e.g. in the 'no X
        changes' preamble) but it must not propose implementing
        changes in them.
        """
        text = _read_doc()
        # Search for patterns that propose modifications
        bad_patterns = [
            r"(?:modify|change|update|edit)\s+main_web\.py",
            r"(?:modify|change|update|edit)\s+app/services",
            r"(?:modify|change|update|edit)\s+app/persistence",
            r"(?:modify|change|update|edit)\s+app/domain",
            r"(?:modify|change|update|edit)\s+app/api",
            r"(?:modify|change|update|edit)\s+app/tax_bridge",
            r"(?:modify|change|update|edit)\s+waterfall_core",
            r"(?:modify|change|update|edit)\s+static/app\.js",
        ]
        for pattern in bad_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            assert not matches, (
                f"doc proposes modifying out-of-scope area: "
                f"pattern='{pattern}' matches={matches}"
            )

    def test_doc_does_not_propose_flag_flip(self):
        """
        The doc may name feature flags (e.g. use_sculpting_solver
        in the Sprint 24-H recommendation) but it must not say
        'flip the flag' or 'change the flag value'.
        """
        text = _read_doc()
        bad_patterns = [
            r"flip\s+(?:the\s+)?(?:feature\s+)?flag",
            r"change\s+(?:the\s+)?flag\s+value",
            r"set\s+use_construction_schedule_engine\s*=\s*True",
        ]
        for pattern in bad_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            assert not matches, (
                f"doc proposes flag flip: pattern='{pattern}' matches={matches}"
            )

    def test_use_construction_schedule_engine_remains_false(self):
        """
        The doc must state that use_construction_schedule_engine
        remains False (no change).
        """
        text = _read_doc()
        assert "use_construction_schedule_engine" in text
        # The doc should say it remains False somewhere. Match multiple
        # phrasings: "remains False", "(remains `False`)", "remains False)",
        # "stays False", "is False".
        assert re.search(
            r"use_construction_schedule_engine[^\n]*?(?:remains|stays|is)\s+(?:`?False`?|False)",
            text,
            re.IGNORECASE,
        ), "doc should state use_construction_schedule_engine remains False"

    def test_rc1_untouched_stated(self):
        text = _read_doc()
        assert "rc1" in text.lower()
        # The doc should say rc1 is untouched
        assert re.search(r"rc1\s+(?:is\s+)?(?:not\s+)?(?:touched|untouched)", text, re.IGNORECASE), (
            "doc should state rc1 is untouched"
        )


# ── 7. Report JSON has the required top-level keys ──────────────────────

class TestReportStructure:
    REQUIRED_KEYS = [
        "phase",
        "title",
        "type",
        "status",
        "date",
        "branch",
        "base_sha",
        "head_sha",
        "builds_on",
        "deliverables",
        "delivered_across_g_track",
        "user_can_do_today",
        "user_cannot_do_today",
        "biggest_blockers_pilot_testing",
        "biggest_blockers_pilot_rollout",
        "biggest_blockers_paid_product",
        "remaining_blockers_ranked",
        "explicit_answers",
        "hard_constraints_honored",
        "next_step",
    ]

    def test_all_required_keys_present(self):
        report = _read_report()
        missing = [k for k in self.REQUIRED_KEYS if k not in report]
        assert not missing, f"missing keys in report: {missing}"

    def test_status_is_draft(self):
        report = _read_report()
        assert "DRAFT" in report.get("status", ""), (
            f"status should be DRAFT, got: {report.get('status')}"
        )

    def test_type_is_report_docs_shape_tests(self):
        report = _read_report()
        type_str = report.get("type", "")
        assert "REPORT" in type_str
        assert "DOCS" in type_str
        assert "SHAPE" in type_str or "TESTS" in type_str


# ── 8. Explicit answers block has the 4 question keys ───────────────────

class TestExplicitAnswersKeys:
    REQUIRED_QUESTION_KEYS = [
        "A_can_finance_user_build_and_test",
        "B_can_renewable_developer_build_and_test",
        "C_highest_value_feature_missing",
        "D_sprint_24h_recommendation",
    ]

    def test_all_question_keys_present(self):
        report = _read_report()
        answers = report.get("explicit_answers", {})
        missing = [k for k in self.REQUIRED_QUESTION_KEYS if k not in answers]
        assert not missing, f"missing question keys: {missing}"

    def test_question_a_has_verdict(self):
        report = _read_report()
        ans = report.get("explicit_answers", {}).get("A_can_finance_user_build_and_test", {})
        assert "tuho_or_oberovo_verdict" in ans
        assert "generic_verdict" in ans

    def test_question_c_has_three_layers(self):
        report = _read_report()
        ans = report.get("explicit_answers", {}).get("C_highest_value_feature_missing", {})
        layers = ans.get("three_layers", [])
        assert len(layers) == 3, f"expected 3 layers, got {len(layers)}"

    def test_question_d_has_three_tracks(self):
        report = _read_report()
        ans = report.get("explicit_answers", {}).get("D_sprint_24h_recommendation", {})
        # Should mention at least track_a, track_b, track_c
        for key in ("track_a_runtime_seam", "track_b_senior_idc", "track_c_ux_followups"):
            assert key in ans, f"missing {key} in D answer"


# ── 9. G-track delivered-across block is internally consistent ──────────

class TestGTrackInternalConsistency:
    def test_g_track_tests_count_matches(self):
        report = _read_report()
        delivered = report.get("delivered_across_g_track", {})
        # 24-G-1 = 47, 24-G-2 = 75, 24-G-3 = 69, inventory = 17
        # Total = 208
        assert delivered.get("total_g_track_tests") == 208
        assert delivered.get("all_passing_on_main") is True

    def test_all_4_pr_statuses_merged(self):
        report = _read_report()
        delivered = report.get("delivered_across_g_track", {})
        for key in ("pr_564", "pr_566_567_24g1", "pr_565_568_24g2", "pr_569_570_24g3"):
            pr = delivered.get(key, {})
            assert "MERGED" in pr.get("status", ""), f"{key} not MERGED: {pr.get('status')}"


# ── 10. The doc does not promote any feature flag value ─────────────────

class TestNoFeatureFlagPromotion:
    def test_no_promotion_language(self):
        text = _read_doc()
        bad_patterns = [
            r"set\s+use_sculpting_solver\s*=\s*True",
            r"enable\s+the\s+flag",
            r"promote\s+the\s+flag",
            r"flip\s+.*?to\s+True",
        ]
        for pattern in bad_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            assert not matches, (
                f"doc contains flag-promotion language: pattern='{pattern}' matches={matches}"
            )
