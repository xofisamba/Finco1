"""Phase 57F — UI-3.2 next-grid readiness plan tests.

This test file is a docs/report-only test. It does not modify
runtime code, templates, or CSS. It pins:

* The 57F docs/report files exist.
* They reference the correct current main SHA.
* The 57F plan does NOT implement a runtime grid migration.
* The 57F plan recommends NOT migrating a second grid
  overnight.
* The 57F plan recommends a DRAFT-only, no-auto-merge
  policy for UI-3.2.
* The 57F plan identifies the likely next candidate
  (OPEX summary) but defers the actual migration.
* The 57F plan requires visual review, fix-A-style
  regression tests, and 57pre allowlist updates.
* No runtime / model / persistence / CSS / JS / schema /
  formula changes were introduced in 57F.
"""

import json
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs" / "phase57f_ui3_2_next_grid_readiness_plan.md"
REPORT = REPO_ROOT / "reports" / "phase57f_ui3_2_next_grid_readiness_plan.json"
RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"


# ============================================================
# 1. Files exist
# ============================================================


class TestFilesExist:
    def test_docs_file_exists(self):
        assert DOCS.exists(), f"57F doc file missing: {DOCS}"

    def test_report_file_exists(self):
        assert REPORT.exists(), f"57F report file missing: {REPORT}"

    def test_doc_minimum_size(self):
        size = DOCS.stat().st_size
        assert size > 6000, (
            f"57F doc is suspiciously small ({size} bytes)."
        )

    def test_report_is_valid_json(self):
        with open(REPORT) as f:
            data = json.load(f)
        assert "phase" in data
        assert data["phase"] == "57F"


# ============================================================
# 2. SHA references
# ============================================================


class TestShaReferences:
    def test_doc_references_current_main_sha(self):
        text = DOCS.read_text()
        assert "9f194ed7bbaa792049573f72bb6699ba25fb701d" in text

    def test_doc_references_rc1_frozen_sha(self):
        text = DOCS.read_text()
        assert RC1_SHA in text

    def test_doc_references_57a_merge_sha(self):
        text = DOCS.read_text()
        assert "b173355b" in text

    def test_report_references_current_main_sha(self):
        data = json.loads(REPORT.read_text())
        assert data["base_sha_start"] == (
            "9f194ed7bbaa792049573f72bb6699ba25fb701d"
        )

    def test_report_references_rc1_frozen_sha(self):
        data = json.loads(REPORT.read_text())
        assert data["rc1_frozen_sha"] == RC1_SHA


# ============================================================
# 3. No runtime migration in 57F
# ============================================================


class TestNoRuntimeMigrationIn57F:
    def test_report_says_no_runtime_migration(self):
        data = json.loads(REPORT.read_text())
        assert data["runtime_migration_in_this_phase"] is False

    def test_doc_says_57f_is_plan_only(self):
        text = DOCS.read_text()
        assert "plan only" in text.lower() or (
            "this is a plan" in text.lower()
        )

    def test_doc_says_do_not_migrate_overnight(self):
        text = DOCS.read_text()
        assert "do not migrate" in text.lower() or (
            "do NOT migrate" in text
        )


# ============================================================
# 4. Recommendation
# ============================================================


class TestRecommendation:
    def test_report_recommends_draft_only(self):
        data = json.loads(REPORT.read_text())
        rec = data["recommendation"]
        assert rec["ui_3_2_should_be_draft_only"] is True
        assert rec["ui_3_2_should_not_auto_merge"] is True

    def test_report_identifies_next_candidate(self):
        data = json.loads(REPORT.read_text())
        rec = data["recommendation"]
        assert "sheet_opex" in rec["likely_next_candidate"]

    def test_doc_lists_candidate_sheets(self):
        text = DOCS.read_text()
        for s in [
            "sheet_opex",
            "sheet_revenue",
            "sheet_capex_detail",
            "sheet_senior_debt",
            "sheet_shl",
            "sheet_tax",
        ]:
            assert s in text, f"57F doc must list {s!r} as a candidate."

    def test_doc_recommends_waiting_for_visual_review(self):
        text = DOCS.read_text()
        assert "visual review" in text.lower()
        # Should explicitly recommend waiting
        m = re.search(
            r"wait[^\n]{0,200}visual[^\n]{0,200}", text, re.IGNORECASE
        )
        assert m is not None, (
            "57F doc must recommend waiting for user visual review."
        )


# ============================================================
# 5. UI-3.2 requirements
# ============================================================


class TestUI32Requirements:
    def test_report_has_required_tests(self):
        data = json.loads(REPORT.read_text())
        reqs = data["ui_3_2_requirements"]["required_tests"]
        assert len(reqs) >= 5
        # Pin Fix A mirror
        assert any("financing" in t for t in reqs)
        # Pin Fix C mirror
        assert any("escaped" in t for t in reqs)
        # Pin 56H-1 regression
        assert any("56h1" in t.lower() for t in reqs)
        # Pin 57pre allowlist update
        assert any("57pre" in t.lower() for t in reqs)

    def test_report_has_visual_review_checklist(self):
        data = json.loads(REPORT.read_text())
        checklist = data["ui_3_2_requirements"]["visual_review_checklist"]
        assert len(checklist) >= 8

    def test_report_has_rollback_plan(self):
        data = json.loads(REPORT.read_text())
        plan = data["ui_3_2_requirements"]["rollback_plan"]
        assert len(plan) >= 1
        # Must mention git revert or force-push
        assert any("revert" in p.lower() or "force" in p.lower() for p in plan)

    def test_report_waits_for_validation_bar_fix(self):
        data = json.loads(REPORT.read_text())
        wait = data["ui_3_2_requirements"]["wait_for_validation_bar_fix"]
        assert wait["wait"] is True

    def test_report_forbidden_files_excludes_runtime(self):
        data = json.loads(REPORT.read_text())
        forbidden = data["ui_3_2_requirements"]["forbidden_files"]
        for f in [
            "main_web.py",
            "app/waterfall_core.py",
            "app/persistence/*",
            "app/services/*",
            "static/app.js",
        ]:
            assert any(f in ff for ff in forbidden), (
                f"Forbidden file {f!r} must be in the UI-3.2 "
                f"forbidden list."
            )


# ============================================================
# 6. 57A lessons applied
# ============================================================


class Test57ALessonsApplied:
    def test_doc_mentions_57a_fixes(self):
        text = DOCS.read_text()
        for fix in ["Fix A", "Fix B", "Fix C", "Fix D"]:
            assert fix in text, (
                f"57F doc must mention 57A {fix}."
            )

    def test_doc_uses_57a_review_to_justify_no_auto_merge(self):
        text = DOCS.read_text().lower()
        # The 57A experience (4 fixes) should be cited
        # as a reason not to auto-merge UI-3.2.
        assert "57a" in text and "fix" in text
        # Should mention review explicitly
        assert "review" in text


# ============================================================
# 7. Hard no-go
# ============================================================


class TestHardNoGoScope:
    @pytest.mark.parametrize(
        "forbidden_change",
        [
            "waterfall_core",
            "project_factories",
            "persistence",
            "main_web.py",
            "static/app.js",
            "static/styles.css",
            "schema",
            "fixture",
            "tailwind",
            "alpine",
            "react",
            "vue",
            "svelte",
        ],
    )
    def test_doc_mentions_forbidden_change(self, forbidden_change):
        text = DOCS.read_text().lower()
        assert forbidden_change.lower() in text

    def test_doc_says_rc1_untouched(self):
        text = DOCS.read_text()
        m = re.search(r"rc1[^\n]{0,200}", text, re.IGNORECASE)
        assert m is not None
        ctx = m.group(0).lower()
        assert "untouched" in ctx or "frozen" in ctx


# ============================================================
# 8. Diff scope
# ============================================================


class Test57FIsDocsOnly:
    def test_57f_diff_only_in_docs_reports_tests(self):
        r = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("Not on 57F branch or no diff")
        # Skip if we are not on a 57F branch. The test
        # asserts that the diff vs main is only
        # docs/reports/tests files — which is only
        # meaningful while 57F is the unmerged branch.
        # A follow-up branch (e.g. 57A-8) may
        # legitimately modify runtime files; this is
        # not 57F's concern.
        r_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r_branch.returncode == 0:
            branch = r_branch.stdout.strip()
            if branch == "main":
                pytest.skip(
                    "On main branch; 57F has been merged. "
                    "This test is only meaningful on the "
                    "57F unmerged branch."
                )
            if "57f" not in branch.lower():
                pytest.skip(
                    f"Not on a 57F branch (current: "
                    f"{branch!r}). This test is only "
                    f"meaningful on the 57F unmerged "
                    f"branch."
                )
        changed = set(r.stdout.strip().split("\n"))
        for c in changed:
            assert (
                c.startswith("docs/")
                or c.startswith("reports/")
                or c.startswith("tests/")
            ), (
                f"57F diff file {c!r} is outside docs/reports/tests."
            )

    def test_no_template_files_in_57f_diff(self):
        # Skip if we are not on a 57F branch. The test
        # asserts that no app/templates/ file is in the
        # diff vs main, which is only meaningful while
        # 57F is the unmerged branch. A follow-up branch
        # (e.g. 57A-8) may legitimately modify template
        # files; this is not 57F's concern.
        r_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r_branch.returncode == 0:
            branch = r_branch.stdout.strip()
            if branch == "main":
                pytest.skip(
                    "On main branch; 57F has been merged. "
                    "This test is only meaningful on the "
                    "57F unmerged branch."
                )
            if "57f" not in branch.lower():
                pytest.skip(
                    f"Not on a 57F branch (current: "
                    f"{branch!r}). This test is only "
                    f"meaningful on the 57F unmerged "
                    f"branch."
                )
        r = subprocess.run(
            ["git", "diff", "main", "--name-only", "--",
             "app/templates/"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return
        pytest.fail(
            f"57F must not modify any app/templates/ file. "
            f"Found: {r.stdout.strip()!r}."
        )

    def test_no_css_files_in_57f_diff(self):
        # Skip if we are not on a 57F branch. The test
        # asserts that static CSS/JS is unchanged vs
        # main, which is only meaningful while 57F is
        # the unmerged branch. A follow-up branch
        # (e.g. 57A-8) may legitimately modify these
        # files; this is not 57F's concern.
        r_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r_branch.returncode == 0:
            branch = r_branch.stdout.strip()
            if branch == "main":
                pytest.skip(
                    "On main branch; 57F has been merged. "
                    "This test is only meaningful on the "
                    "57F unmerged branch."
                )
            if "57f" not in branch.lower():
                pytest.skip(
                    f"Not on a 57F branch (current: "
                    f"{branch!r}). This test is only "
                    f"meaningful on the 57F unmerged "
                    f"branch."
                )
        r = subprocess.run(
            ["git", "diff", "main", "--name-only", "--",
             "static/styles.css", "static/app.js"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return
        pytest.fail(
            f"57F must not modify static CSS/JS. "
            f"Found: {r.stdout.strip()!r}."
        )


# ============================================================
# 9. Rc1 untouched
# ============================================================


class TestRc1Untouched:
    def test_rc1_sha_constant_stable(self):
        assert RC1_SHA == "b425a0708719eaa5e1d922b1008e5609758e0ad4"

    def test_rc1_still_in_git_history(self):
        r = subprocess.run(
            ["git", "rev-parse", RC1_SHA],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0
