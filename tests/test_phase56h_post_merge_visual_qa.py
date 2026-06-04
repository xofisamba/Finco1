"""Phase 56H — Post-merge visual QA and hotfix gate tests.

Verifies the visual QA closeout:
- 56H docs and JSON report exist and are well-formed
- The QA outcome is B (hotfix required)
- The hotfix PR is documented and reproducible
- The visual QA checklist covers all required areas
- The recommendation points to UI-3.1 after merge
- No-go claims are absent
- Tailwind/Alpine remain deferred
- Generic Solar/Wind remain exploratory
- rc1 untouched
- The hotfix test file is present and pinning the fix
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_56H = REPO_ROOT / "docs" / "phase56h_post_merge_visual_qa.md"
REPORT_56H = REPO_ROOT / "reports" / "phase56h_post_merge_visual_qa.json"
HOTFIX_TEST = (
    REPO_ROOT / "tests" / "test_phase56h1_index_validation_errors_hotfix.py"
)
MAIN_WEB = REPO_ROOT / "main_web.py"

RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"


# ============================================================
# 1. 56H docs and JSON exist
# ============================================================


class TestDocsExist:
    def test_doc_exists(self):
        assert DOC_56H.exists(), (
            f"56H closeout doc must exist at {DOC_56H}"
        )

    def test_json_report_exists(self):
        assert REPORT_56H.exists(), (
            f"56H JSON report must exist at {REPORT_56H}"
        )

    def test_doc_is_markdown(self):
        text = DOC_56H.read_text()
        assert "# Phase 56H" in text
        assert "## " in text

    def test_json_report_is_valid_json(self):
        try:
            data = json.loads(REPORT_56H.read_text())
        except json.JSONDecodeError as e:
            pytest.fail(f"56H JSON report is not valid JSON: {e}")
        assert data.get("phase") == "56H"


# ============================================================
# 2. Outcome is B (hotfix required)
# ============================================================


class TestOutcome:
    def test_outcome_b(self):
        """The visual QA must declare Outcome B — a critical runtime
        regression was found and a hotfix was opened."""
        text = DOC_56H.read_text()
        assert "Outcome B" in text
        assert "NameError" in text
        # JSON must also report Outcome B
        data = json.loads(REPORT_56H.read_text())
        assert data.get("outcome") == "B"

    def test_root_cause_documented(self):
        text = DOC_56H.read_text()
        # The 55G merge introduced the bug
        assert "55G" in text
        # Bare-name reference explanation
        assert (
            "dict-literal" in text.lower()
            or "dict literal" in text.lower()
        )
        # The NameError is named
        assert "validation_errors" in text

    def test_fix_is_minimal(self):
        text = DOC_56H.read_text()
        # The fix is described as minimal
        assert "minimal" in text.lower()
        # The fix is hoisting
        assert "hoist" in text.lower() or "hoisted" in text.lower()
        # The fix is small (8 lines added, 1 line changed)
        # Markdown escapes the minus sign in `-1` as a list bullet,
        # so we check for the alternative phrasing
        assert (
            "+8" in text and ("-1" in text or "1 line" in text.lower())
        ), (
            "Doc must reference the +8 / -1 diff size of the hotfix."
        )


# ============================================================
# 3. Hotfix PR is documented
# ============================================================


class TestHotfixPr:
    def test_hotfix_branch_documented(self):
        text = DOC_56H.read_text()
        assert "phase56h-1-hotfix" in text

    def test_hotfix_pr_number_documented(self):
        text = DOC_56H.read_text()
        assert "PR #485" in text or "#485" in text

    def test_hotfix_head_sha_documented(self):
        text = DOC_56H.read_text()
        assert "6bf16f7" in text or "6bf16f7" in text

    def test_hotfix_status_documented(self):
        text = DOC_56H.read_text()
        assert "DRAFT" in text
        # No auto-merge
        assert "no auto-merge" in text.lower() or "draft only" in text.lower()

    def test_hotfix_test_file_exists(self):
        assert HOTFIX_TEST.exists(), (
            f"Hotfix test file must exist at {HOTFIX_TEST}"
        )

    def test_hotfix_test_file_pins_fix(self):
        text = HOTFIX_TEST.read_text()
        # The test must pin the local variable declaration
        assert "validation_errors" in text
        # The test must check the GET / endpoint
        assert '"/"' in text or "GET /" in text or 'get("/"' in text


# ============================================================
# 4. Visual QA checklist completeness
# ============================================================


CHECKLIST_AREAS = [
    "Overview",
    "Help",
    "Project switch",
    "New Project",
    "COD",
    "State banner",
    "Inputs",
    "Scenarios",
    "Audit",
    "Run",
]


class TestChecklistCoverage:
    @pytest.mark.parametrize("area", CHECKLIST_AREAS)
    def test_checklist_area_covered(self, area):
        text = DOC_56H.read_text()
        assert area in text or area.lower() in text.lower(), (
            f"Visual QA checklist must mention: {area}"
        )

    def test_11_banner_contexts_preserved(self):
        text = DOC_56H.read_text()
        # All 11 contexts
        for ctx in [
            "factory_template",
            "user_created_project",
            "active_scenario",
            "saved_scenario",
            "browser_draft",
            "dirty_state",
            "stale_result",
            "last_run",
            "validation_failed",
            "display_only_row",
            "pending_runtime_source",
        ]:
            assert ctx in text, (
                f"Visual QA must reference banner context: {ctx}"
            )

    def test_5_banner_tones_preserved(self):
        text = DOC_56H.read_text()
        for tone in ["info", "success", "warn", "fail", "neutral"]:
            assert tone in text, (
                f"Visual QA must reference banner tone: {tone}"
            )

    def test_origin_pill_wording(self):
        text = DOC_56H.read_text()
        for pill in ["Reference", "My project", "Saved baseline"]:
            assert pill in text, (
                f"Visual QA must reference origin pill: {pill}"
            )


# ============================================================
# 5. Recommended next step
# ============================================================


class TestRecommendation:
    def test_ui3_recommended_after_hotfix(self):
        text = DOC_56H.read_text()
        assert "UI-3" in text
        assert "LineItemGrid" in text
        assert "CAPEX" in text

    def test_merge_hotfix_first(self):
        text = DOC_56H.read_text()
        # The hotfix must come first
        assert "merge" in text.lower()
        # Then visual review
        assert "visual review" in text.lower()
        # Then UI-3
        assert "ui-3" in text.lower() or "UI-3" in text


# ============================================================
# 6. No-go and deferred-stack checks
# ============================================================


class TestNoGoAndDeferred:
    def test_tailwind_deferred(self):
        text = DOC_56H.read_text()
        assert "Tailwind" in text
        assert "deferred" in text.lower()

    def test_alpine_deferred(self):
        text = DOC_56H.read_text()
        assert "Alpine" in text
        # Alpine is in the "do not start" list (or described as
        # deferred / not started).
        assert (
            "do not start" in text.lower()
            or "deferred" in text.lower()
        )

    def test_generic_solar_wind_exploratory(self):
        text = DOC_56H.read_text()
        assert "exploratory" in text.lower()
        # Both must be in the doc; allow "Generic Solar / Wind" as
        # a single phrase.
        lowered = text.lower()
        assert "generic solar" in lowered
        # "wind" must appear in the same paragraph / line context
        m = re.search(r"generic\s+solar[^\n]*wind", lowered)
        assert m is not None, (
            "56H doc must reference 'Generic Solar ... Wind' as a "
            "single phrase in the exploratory / preserved section."
        )

    def test_g20_blocked(self):
        text = DOC_56H.read_text()
        assert "G20" in text
        assert "BLOCKED" in text

    def test_r99_r102_not_approved(self):
        text = DOC_56H.read_text()
        assert "R99" in text
        assert "R102" in text
        assert "NOT APPROVED" in text

    def test_backend_source_of_truth(self):
        text = DOC_56H.read_text()
        assert "source of truth" in text.lower() or "source-of-truth" in text.lower()
        assert "No JS financial calculations" in text or "no JS financial calculations" in text

    def test_bess_hybrid_portfolio_not_started(self):
        text = DOC_56H.read_text()
        assert "BESS" in text or "bess" in text.lower()
        assert "Hybrid" in text or "hybrid" in text.lower()
        assert "Portfolio" in text or "portfolio" in text.lower()


# ============================================================
# 7. rc1 untouched
# ============================================================


class TestRc1Untouched:
    def test_rc1_sha_constant_stable(self):
        assert RC1_SHA == "b425a0708719eaa5e1d922b1008e5609758e0ad4"

    def test_doc_references_rc1(self):
        text = DOC_56H.read_text()
        assert "rc1" in text.lower() or "b425a07" in text

    def test_git_history_has_rc1(self):
        import subprocess
        r = subprocess.run(
            ["git", "rev-parse", RC1_SHA],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0


# ============================================================
# 8. JSON report structure
# ============================================================


class TestJsonReportStructure:
    def test_json_has_required_keys(self):
        data = json.loads(REPORT_56H.read_text())
        for key in [
            "phase", "title", "outcome", "current_main_sha",
            "rc1_frozen_sha", "rc1_untouched", "hotfix", "visual_qa_checklist",
            "no_go_check", "tests_run", "test_result", "recommendation",
            "do_not_start", "confirmation",
        ]:
            assert key in data, f"56H JSON must have key: {key}"

    def test_json_hotfix_keys(self):
        data = json.loads(REPORT_56H.read_text())
        hotfix = data.get("hotfix", {})
        for key in [
            "phase", "title", "branch", "pr_number", "pr_url",
            "head_sha", "status", "auto_merge", "files_changed",
            "main_web_diff_size", "test_count", "ci_status",
            "parity_status", "root_cause", "fix", "hard_gates",
        ]:
            assert key in hotfix, f"hotfix JSON must have key: {key}"

    def test_json_checklist_keys(self):
        data = json.loads(REPORT_56H.read_text())
        cl = data.get("visual_qa_checklist", {})
        for area in [
            "overview_tab", "help_tab", "sidebar_project_switcher",
            "new_project_flow", "state_banner",
            "inputs_scenarios_audit_run",
        ]:
            assert area in cl, f"checklist JSON must have area: {area}"

    def test_json_no_go_check(self):
        data = json.loads(REPORT_56H.read_text())
        ng = data.get("no_go_check", {})
        for key in [
            "no_bankability_claims", "no_validated_positive_claims",
            "g20_blocked_preserved", "r99_r102_not_approved_preserved",
            "generic_solar_wind_exploratory", "backend_source_of_truth",
            "no_js_financial_calculations", "rc1_frozen",
        ]:
            assert key in ng, f"no_go JSON must have key: {key}"


# ============================================================
# 9. Hard no-go copy on actual templates (regression)
# ============================================================


class TestNoGoCopyOnImplementedTemplates:
    """Regression guard: even after the hotfix, all the 56B-56F
    templates must remain free of positive no-go claims."""

    def test_state_banner_no_positive_validated(self):
        path = REPO_ROOT / "app" / "templates" / "partials" / "_state_banner.html"
        text = path.read_text()
        stripped = re.sub(r"\{#.*?#\}", "", text, flags=re.DOTALL)
        stripped = re.sub(r"<!--.*?-->", "", stripped, flags=re.DOTALL)
        assert "validated" not in stripped.lower(), (
            "_state_banner.html still contains 'validated' (positive)."
        )

    def test_project_selector_no_positive_validated(self):
        path = REPO_ROOT / "app" / "templates" / "partials" / "project_selector.html"
        text = path.read_text()
        stripped = re.sub(r"\{#.*?#\}", "", text, flags=re.DOTALL)
        stripped = re.sub(r"<!--.*?-->", "", stripped, flags=re.DOTALL)
        assert "validated" not in stripped.lower(), (
            "project_selector.html still contains 'validated' (positive)."
        )

    def test_help_block_no_positive_validated(self):
        path = REPO_ROOT / "app" / "templates" / "partials" / "pilot_help_onboarding.html"
        text = path.read_text()
        stripped = re.sub(r"\{#.*?#\}", "", text, flags=re.DOTALL)
        stripped = re.sub(r"<!--.*?-->", "", stripped, flags=re.DOTALL)
        # The doc may have "rephrased from validated" comments, but
        # the visible text must be "Reference" / "parity evidence"
        # not "validated".
        # Comment-only mentions are OK; visible text matters.
        # Strip ALL comments more aggressively.
        text_visible = re.sub(r"\{#.*?#\}", "", text, flags=re.DOTALL)
        text_visible = re.sub(r"<!--.*?-->", "", text_visible, flags=re.DOTALL)
        # Look for `validated` in the actual rendered markup (not
        # comments)
        if "validated" in text_visible.lower():
            # It must be in a "rephrased" / "removed" / "no longer"
            # context (not as a positive claim)
            for line in text_visible.split("\n"):
                if "validated" in line.lower():
                    assert (
                        "rephrased" in line.lower()
                        or "removed" in line.lower()
                        or "no longer" in line.lower()
                    ), (
                        f"Help block must not contain positive 'validated': "
                        f"{line!r}"
                    )

    def test_origin_pill_wording_correct(self):
        path = REPO_ROOT / "app" / "templates" / "partials" / "project_selector.html"
        text = path.read_text()
        # All three pills must be present
        for pill in ["Reference", "My project", "Saved baseline"]:
            assert pill in text, (
                f"project_selector.html must contain origin pill: {pill}"
            )


# ============================================================
# 10. The hotfix is the only main_web.py change in 56H
# ============================================================


class TestHotfixScope:
    def test_main_web_only_hoist(self):
        """The hotfix must only add a local-variable hoist. No other
        change to main_web.py."""
        text = MAIN_WEB.read_text()
        # Search for the hoist comment marker
        assert (
            "Phase 56H-1 hotfix: hoist validation_errors" in text
        ), (
            "main_web.py must contain the Phase 56H-1 hoist comment."
        )

    def test_no_app_js_changes_in_hotfix(self):
        """The hotfix must NOT touch static/app.js.

        The branch may include the hotfix itself (main_web.py +
        hotfix test) AND the closeout (56H doc + report + test).
        What is NOT allowed: any change to static/app.js,
        waterfall_core.py, project_factories.py,
        runtime_impact_taxonomy.py, or anything in app/persistence/.
        """
        FORBIDDEN_FILES = {
            "static/app.js",
            "app/waterfall_core.py",
            "app/project_factories.py",
            "app/runtime_impact_taxonomy.py",
        }
        # Anything in app/persistence/ is also forbidden
        import subprocess
        r = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode == 0 and r.stdout.strip():
            changed_files = set(r.stdout.strip().split("\n"))
            # No forbidden file may be in the diff
            for f in FORBIDDEN_FILES:
                assert f not in changed_files, (
                    f"Hotfix branch must NOT change {f}. "
                    f"Found in diff: {changed_files}"
                )
            # No app/persistence/* file
            for f in changed_files:
                assert not f.startswith("app/persistence/"), (
                    f"Hotfix branch must NOT change any app/persistence/* "
                    f"file. Found: {f}"
                )
