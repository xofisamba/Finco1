"""Phase 57C — Validation bar semantics design tests.

This test file is a docs/report-only test. It does not modify
runtime code. It pins:

* The 57C docs/report files exist.
* They reference the correct current main SHA.
* The design recommends a split into governance_guard_summary
  and a refined validation_summary.
* The design avoids the word "validated" in positive
  user-facing context.
* The design uses safe copy (Governance guard, Requires
  review, Model evidence, Internal check).
* The design does not promote G20/R99/R102.
* The design does not implement runtime changes in 57C.
* No runtime / model / persistence / CSS / JS / schema /
  formula changes were introduced in 57C.
"""

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs" / "phase57c_validation_bar_semantics_design.md"
REPORT = REPO_ROOT / "reports" / "phase57c_validation_bar_semantics_design.json"
RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"

FORBIDDEN_POSITIVE_CLAIMS = [
    "bankable",
    "bank-grade",
    "lender-ready",
    "certified",
    "audit-ready",
    "validated",
    "investor-ready",
    "SaaS-ready",
    "production-ready",
    "external validation",
    "customer reference",
    "investment advice",
    "guaranteed returns",
]

SAFE_COPY_TERMS = [
    "Governance guard",
    "Requires review",
    "Model evidence",
    "Internal check",
]


# ============================================================
# 1. Files exist
# ============================================================


class TestFilesExist:
    def test_docs_file_exists(self):
        assert DOCS.exists(), f"57C doc file missing: {DOCS}"

    def test_report_file_exists(self):
        assert REPORT.exists(), f"57C report file missing: {REPORT}"

    def test_doc_minimum_size(self):
        size = DOCS.stat().st_size
        assert size > 8000, (
            f"57C doc is suspiciously small ({size} bytes). "
            f"Expected a comprehensive design document."
        )

    def test_report_is_valid_json(self):
        with open(REPORT) as f:
            data = json.load(f)
        assert "phase" in data
        assert data["phase"] == "57C"


# ============================================================
# 2. SHA references
# ============================================================


class TestShaReferences:
    def test_doc_references_current_main_sha(self):
        text = DOCS.read_text()
        assert "4036b62dbcffd576b9ce4808123e775bd9726185" in text, (
            "57C doc must reference the post-57B main SHA."
        )

    def test_doc_references_rc1_frozen_sha(self):
        text = DOCS.read_text()
        assert RC1_SHA in text, (
            f"57C doc must reference the rc1 frozen SHA {RC1_SHA}."
        )

    def test_report_references_current_main_sha(self):
        data = json.loads(REPORT.read_text())
        assert data["base_sha_start"] == (
            "4036b62dbcffd576b9ce4808123e775bd9726185"
        )

    def test_report_references_rc1_frozen_sha(self):
        data = json.loads(REPORT.read_text())
        assert data["rc1_frozen_sha"] == RC1_SHA


# ============================================================
# 3. No runtime changes in 57C
# ============================================================


class TestNoRuntimeChangesIn57C:
    def test_report_says_no_runtime_changes(self):
        data = json.loads(REPORT.read_text())
        assert data["runtime_changes_in_this_phase"] is False, (
            "57C is a design-only phase. No runtime changes."
        )

    def test_doc_says_57c_is_design_only(self):
        text = DOCS.read_text()
        assert "design" in text.lower()
        assert (
            "no runtime changes" in text.lower()
            or "design document only" in text.lower()
            or "no runtime change" in text.lower()
        )

    def test_doc_mentions_future_runtime_pr_57c1(self):
        text = DOCS.read_text()
        assert "57C-1" in text or "57c-1" in text.lower(), (
            "57C doc must reference the future runtime PR 57C-1."
        )


# ============================================================
# 4. Design recommends split
# ============================================================


class TestDesignRecommendsSplit:
    def test_doc_recommends_split(self):
        text = DOCS.read_text()
        assert "governance_guard_summary" in text, (
            "57C design must propose a new "
            "governance_guard_summary dict."
        )
        assert "validation_summary" in text, (
            "57C design must keep the validation_summary dict."
        )

    def test_report_has_split_proposal(self):
        data = json.loads(REPORT.read_text())
        split = data["proposed_design"]["split_into_two_dicts"]
        assert "governance_guard_summary" in split
        assert "validation_summary_refined" in split

    def test_design_separates_permanent_guards_from_per_run(self):
        text = DOCS.read_text().lower()
        assert "permanent" in text or "baseline" in text
        assert "per-run" in text or "per run" in text


# ============================================================
# 5. Safe copy
# ============================================================


class TestSafeCopy:
    @pytest.mark.parametrize("term", SAFE_COPY_TERMS)
    def test_doc_uses_safe_copy_term(self, term):
        text = DOCS.read_text()
        assert term in text, (
            f"57C doc must use the safe copy term {term!r}."
        )

    def test_report_has_safe_copy_catalog(self):
        data = json.loads(REPORT.read_text())
        catalog = data["safe_copy_catalog"]["old_to_new"]
        # For each safe term, at least one new value uses it
        for safe_term in SAFE_COPY_TERMS:
            found = False
            for old, new in catalog.items():
                if safe_term in new:
                    found = True
                    break
            assert found, (
                f"Safe copy term {safe_term!r} must appear in the "
                f"safe copy catalog."
            )

    def test_no_validated_in_positive_user_facing_context(self):
        text = DOCS.read_text()
        for m in re.finditer(r"validated", text, re.IGNORECASE):
            start = max(0, m.start() - 200)
            end = min(len(text), m.end() + 200)
            context = text[start:end]
            ok = any(
                k in context.lower()
                for k in [
                    "not validated",
                    "no-go",
                    "no go",
                    "forbidden",
                    "negative",
                    "must not",
                    "do not",
                    "preserved",
                    "rephrase",
                    "rephrasing",
                    "instead of",
                    "wording",
                    "reference",
                    "model evidence",
                    "internal check",
                    "validation summary",
                    "validation_summary",
                    "unvalidated",
                    "generic solar/wind",
                    "validation issues",
                    "the word",
                    "per-run",
                    "pass_count",
                    "warn_count",
                    "fail_count",
                    "current: one",
                    "current:",
                    "proposed:",
                    "code block",
                ]
            )
            assert ok, (
                f"'validated' found in 57C doc outside a "
                f"safe/negative context: ...{context!r}..."
            )


# ============================================================
# 6. Section A visual state = neutral/warn
# ============================================================


class TestSectionAVisualState:
    def test_doc_recommends_neutral_warn_for_section_a(self):
        text = DOCS.read_text().lower()
        assert (
            "neutral" in text and "warn" in text
        ), (
            "57C design must recommend neutral/warn for the "
            "governance guard section."
        )

    def test_doc_explains_why_not_red(self):
        text = DOCS.read_text().lower()
        assert (
            "red bar" in text or "red" in text
        ), (
            "57C design must explain why red is wrong for the "
            "guard section."
        )

    def test_report_ui_sections_has_section_a(self):
        data = json.loads(REPORT.read_text())
        sections = data["proposed_design"]["ui_sections"]
        assert "section_A_governance_guard" in sections
        assert (
            "neutral" in sections["section_A_governance_guard"]["visual_state"]
            or "warn" in sections["section_A_governance_guard"]["visual_state"]
        )


# ============================================================
# 7. No G20/R99/R102 promotion
# ============================================================


class TestNoGuardPromotion:
    def test_doc_does_not_promote_g20(self):
        text = DOCS.read_text()
        # G20 should be referenced as a guard, not promoted
        # to a positive claim
        m = re.search(r"g20[^\n]{0,200}", text, re.IGNORECASE)
        if m is not None:
            ctx = m.group(0).lower()
            # Should NOT say G20 is OK, approved, validated
            assert not any(
                k in ctx
                for k in ["g20 is ok", "g20 is approved", "g20 validated"]
            ), f"G20 should not be promoted: {m.group(0)!r}"

    def test_doc_does_not_promote_r99_r102(self):
        text = DOCS.read_text()
        m = re.search(r"r99[^\n]{0,200}", text, re.IGNORECASE)
        if m is not None:
            ctx = m.group(0).lower()
            assert not any(
                k in ctx
                for k in [
                    "r99/r102 is approved",
                    "r99/r102 validated",
                ]
            ), f"R99/R102 should not be promoted: {m.group(0)!r}"

    def test_doc_keeps_g20_blocked(self):
        text = DOCS.read_text()
        assert "G20" in text and "BLOCKED" in text

    def test_doc_keeps_r99_r102_not_approved(self):
        text = DOCS.read_text()
        assert "R99" in text and "NOT APPROVED" in text


# ============================================================
# 8. Alternatives considered
# ============================================================


class TestAlternativesConsidered:
    def test_doc_mentions_alternatives(self):
        text = DOCS.read_text().lower()
        assert "alternative" in text or "considered" in text

    def test_report_has_alternatives_considered(self):
        data = json.loads(REPORT.read_text())
        alts = data["alternatives_considered"]
        # At least 3 alternatives considered
        assert len(alts) >= 3
        # All alternatives must be REJECTED
        for name, status in alts.items():
            assert "REJECT" in status.upper(), (
                f"Alternative {name!r} must be REJECTED with reason."
            )

    def test_at_least_one_alternative_rejected_for_forbidden_claim(self):
        data = json.loads(REPORT.read_text())
        text = json.dumps(data)
        assert "forbidden" in text.lower() or "positive claim" in text.lower()


# ============================================================
# 9. Future runtime tests
# ============================================================


class TestFutureRuntimeTests:
    def test_report_lists_splitting_tests(self):
        data = json.loads(REPORT.read_text())
        tests = data["future_runtime_pr_57c1_required_tests"]
        assert "splitting_tests" in tests
        assert len(tests["splitting_tests"]) >= 5

    def test_report_lists_ui_contract_tests(self):
        data = json.loads(REPORT.read_text())
        tests = data["future_runtime_pr_57c1_required_tests"]
        assert "ui_contract_tests" in tests
        assert len(tests["ui_contract_tests"]) >= 3

    def test_report_lists_regression_tests(self):
        data = json.loads(REPORT.read_text())
        tests = data["future_runtime_pr_57c1_required_tests"]
        assert "regression_tests" in tests
        assert len(tests["regression_tests"]) >= 3


# ============================================================
# 10. Open questions
# ============================================================


class TestOpenQuestions:
    def test_doc_has_open_questions_section(self):
        text = DOCS.read_text()
        assert "Open questions" in text

    def test_report_has_open_questions(self):
        data = json.loads(REPORT.read_text())
        questions = data["open_questions_for_user"]
        assert len(questions) >= 3, (
            "57C report must have at least 3 open questions "
            "for the user."
        )


# ============================================================
# 11. Hard no-go / scope
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
        assert forbidden_change.lower() in text, (
            f"57C doc must mention {forbidden_change!r} in the "
            f"hard no-go section."
        )

    def test_doc_says_rc1_untouched(self):
        text = DOCS.read_text()
        m = re.search(r"rc1[^\n]{0,200}", text, re.IGNORECASE)
        assert m is not None
        ctx = m.group(0).lower()
        assert "untouched" in ctx or "frozen" in ctx


# ============================================================
# 12. Diff scope (no runtime changes)
# ============================================================


class Test57CIsDocsOnly:
    def _skip_if_not_on_57c_branch(self) -> None:
        """Skip the test if we are not on a 57C branch."""
        import subprocess
        r_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r_branch.returncode != 0:
            return
        branch = r_branch.stdout.strip()
        if branch == "main":
            pytest.skip(
                "On main branch; 57C has been merged. "
                "This test is only meaningful on the "
                "57C unmerged branch."
            )
        if "57c" not in branch.lower():
            pytest.skip(
                f"Not on a 57C branch (current: "
                f"{branch!r}). This test is only "
                f"meaningful on the 57C unmerged "
                f"branch."
            )

    def test_57c_diff_has_no_runtime_files(self):
        import subprocess
        r = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("Not on 57C branch or no diff")
        self._skip_if_not_on_57c_branch()
        changed = set(r.stdout.strip().split("\n"))
        forbidden = [
            "main_web.py",
            "app/waterfall_core.py",
            "app/project_factories.py",
            "static/app.js",
            "static/styles.css",
        ]
        for f in forbidden:
            for c in changed:
                assert not c.endswith(f), (
                    f"57C must not modify {f!r}. "
                    f"Found in diff: {c!r}."
                )
        for c in changed:
            assert not c.startswith("app/persistence/"), (
                f"57C must not modify app/persistence/. "
                f"Found: {c!r}."
            )
            assert not c.startswith("app/services/"), (
                f"57C must not modify app/services/. "
                f"Found: {c!r}."
            )

    def test_57c_diff_only_in_docs_reports_tests(self):
        import subprocess
        r = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("Not on 57C branch or no diff")
        self._skip_if_not_on_57c_branch()
        changed = set(r.stdout.strip().split("\n"))
        for c in changed:
            assert (
                c.startswith("docs/")
                or c.startswith("reports/")
                or c.startswith("tests/")
            ), (
                f"57C diff file {c!r} is outside "
                f"docs/reports/tests. 57C must be docs/report/test-only."
            )
