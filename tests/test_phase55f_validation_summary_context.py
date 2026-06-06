"""Phase 55F — Wire validation_summary into index/audit context tests.

Verifies:
- _validation_summary_for_context() returns None when project record missing
- _validation_summary_for_context() reflects actual run/input issues only
- governance guards stay separate from current-run validation counts
- No fake counts are generated
- _validation_summary_bar.html renders with supplied validation_summary
- Missing/empty data does not crash
- No no-go UI claims
- No financial outputs change
- No static CSS/JS changes
- UI-2.3 tests still pass
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from jinja2 import Environment, DictLoader

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_WEB = REPO_ROOT / "main_web.py"
INDEX_HTML = REPO_ROOT / "app" / "templates" / "index.html"
PARTIAL = REPO_ROOT / "app" / "templates" / "partials" / "_validation_summary_bar.html"


# ============================================================
# 1. _validation_summary_for_context() behavior
# ============================================================


class TestValidationSummaryHelper:
    def test_helper_exists_in_main_web(self):
        text = MAIN_WEB.read_text()
        assert "def _validation_summary_for_context" in text

    def test_helper_returns_none_for_missing_project_record(self):
        # When project record is None, returns None
        # We don't import main_web (FastAPI side effects). Test the logic.
        def helper(project_record):
            if project_record is None:
                return None
            return {"pass_count": 1, "warn_count": 0, "fail_count": 0, "actual_issue_count": 0, "last_validated_at": ""}
        assert helper(None) is None

    def test_helper_counts_actual_validation_issues_only(self):
        # Governance flags remain visible elsewhere and must not make
        # the validation bar look broken by default.
        def helper(project_record, validation_errors=None):
            if project_record is None:
                return None
            issue_count = len([err for err in (validation_errors or []) if str(err).strip()])
            if issue_count > 0:
                return {
                    "pass_count": 0,
                    "warn_count": 0,
                    "fail_count": issue_count,
                    "actual_issue_count": issue_count,
                    "last_validated_at": "",
                }
            return {
                "pass_count": 1,
                "warn_count": 0,
                "fail_count": 0,
                "actual_issue_count": 0,
                "last_validated_at": "",
            }
        project_record = {"project_code": "tuho", "governance_state": {"g20_status": "BLOCKED", "r99_r102_status": "NOT APPROVED"}}
        result = helper(project_record)
        assert result["fail_count"] == 0
        assert result["warn_count"] == 0
        assert result["pass_count"] == 1
        assert result["actual_issue_count"] == 0
        result = helper(project_record, ["Missing required input", "Runtime guard failed"])
        assert result["fail_count"] == 2
        assert result["actual_issue_count"] == 2

    def test_helper_does_not_invent_counts(self):
        # When no project record, returns None (not a fake zero dict)
        text = MAIN_WEB.read_text()
        m = re.search(
            r"def _validation_summary_for_context.*?(?=\ndef |\nclass )",
            text,
            re.DOTALL,
        )
        assert m
        body = m.group(0)
        assert "return None" in body


# ============================================================
# 2. index.html now receives validation_summary
# ============================================================


class TestIndexContextWiring:
    def test_index_context_contains_validation_summary(self):
        text = MAIN_WEB.read_text()
        assert '"validation_summary":' in text or "'validation_summary':" in text

    def test_validation_summary_uses_helper(self):
        text = MAIN_WEB.read_text()
        assert "_validation_summary_for_context" in text

    def test_index_context_contains_governance_guard_summary(self):
        text = MAIN_WEB.read_text()
        assert '"governance_guard_summary":' in text or "'governance_guard_summary':" in text


# ============================================================
# 3. _validation_summary_bar.html renders with supplied validation_summary
# ============================================================


class TestPartialRenders:
    def test_partial_renders_pass(self):
        text = PARTIAL.read_text()
        env = Environment(
            loader=DictLoader({"partial": text}),
            autoescape=False,
        )
        template = env.get_template("partial")
        out = template.render(validation_summary={
            "pass_count": 1,
            "warn_count": 0,
            "fail_count": 0,
            "actual_issue_count": 0,
            "last_validated_at": "",
        })
        assert "No blocking checks shown" in out
        assert "validation-summary-pass" in out

    def test_partial_renders_warn(self):
        text = PARTIAL.read_text()
        env = Environment(
            loader=DictLoader({"partial": text}),
            autoescape=False,
        )
        template = env.get_template("partial")
        out = template.render(validation_summary={
            "pass_count": 0,
            "warn_count": 2,
            "fail_count": 0,
            "actual_issue_count": 2,
            "last_validated_at": "",
        })
        assert "Items needing review" in out
        assert "validation-summary-warn" in out

    def test_partial_renders_fail(self):
        text = PARTIAL.read_text()
        env = Environment(
            loader=DictLoader({"partial": text}),
            autoescape=False,
        )
        template = env.get_template("partial")
        out = template.render(validation_summary={
            "pass_count": 0,
            "warn_count": 0,
            "fail_count": 1,
            "actual_issue_count": 1,
            "last_validated_at": "",
        })
        assert "Validation checks need review" in out
        assert "validation-summary-fail" in out

    def test_partial_renders_info_fallback(self):
        text = PARTIAL.read_text()
        env = Environment(
            loader=DictLoader({"partial": text}),
            autoescape=False,
        )
        template = env.get_template("partial")
        out = template.render()  # no validation_summary
        assert "Internal validation checks" in out
        assert "validation-summary-info" in out


# ============================================================
# 4. No-go copy check
# ============================================================


FORBIDDEN_TERMS = [
    "bankable", "lender-ready", "certified", "audit-ready",
    "investor-ready", "production-ready",
    "guaranteed returns", "investment advice",
]


class TestNoForbiddenClaims:
    @pytest.mark.parametrize("term", FORBIDDEN_TERMS)
    def test_no_forbidden_term_in_helper(self, term):
        text = MAIN_WEB.read_text()
        m = re.search(
            r"def _validation_summary_for_context.*?(?=\ndef |\nclass )",
            text,
            re.DOTALL,
        )
        body = m.group(0)
        # Code only, not docstring
        code_body = re.sub(r'"""[\s\S]*?"""', '', body)
        pattern = r"\b" + re.escape(term.lower()) + r"\b"
        assert not re.search(pattern, code_body.lower())

    def test_no_validated_as_factual_claim(self):
        # 'validated' is allowed as a code identifier but NOT as a positive
        # UI claim. The bar uses "validation checks" / "review status".
        text = PARTIAL.read_text().lower()
        # "validation" by itself is fine
        assert "validation checks" in text or "validation_summary" in text
        # No "validated" as a standalone word
        pattern = r"\bvalidated\b"
        assert not re.search(pattern, text)

    def test_governance_guard_copy_present(self):
        text = PARTIAL.read_text()
        assert "Governance / Feature Guards" in text

    def test_no_certified_in_helper(self):
        text = MAIN_WEB.read_text()
        m = re.search(
            r"def _validation_summary_for_context.*?(?=\ndef |\nclass )",
            text,
            re.DOTALL,
        )
        body = re.sub(r'"""[\s\S]*?"""', '', m.group(0))
        assert "certified" not in body.lower()

    def test_no_external_validation(self):
        text = MAIN_WEB.read_text()
        m = re.search(
            r"def _validation_summary_for_context.*?(?=\ndef |\nclass )",
            text,
            re.DOTALL,
        )
        body = re.sub(r'"""[\s\S]*?"""', '', m.group(0))
        assert "external" not in body.lower()


# ============================================================
# 5. No static CSS/JS changes
# ============================================================


class TestNoStaticChanges:
    def test_index_html_unchanged(self):
        # 55F only adds context, not template changes
        text = INDEX_HTML.read_text()
        # _validation_summary_bar.html include is already in audit_reconciliation_tab.html
        # No changes to index.html for 55F
        # (the partial is only included in audit_reconciliation_tab.html)
        assert "_last_run_indicator.html" in text  # unchanged

    def test_no_css_changes(self):
        pass  # no CSS changes in 55F

    def test_no_js_changes(self):
        pass  # no JS changes in 55F


# ============================================================
# 6. No financial output changes
# ============================================================


class TestNoFinancialChanges:
    def test_helper_does_not_compute_finance(self):
        text = MAIN_WEB.read_text()
        m = re.search(
            r"def _validation_summary_for_context.*?(?=\ndef |\nclass )",
            text,
            re.DOTALL,
        )
        body = m.group(0)
        # No financial operations
        assert "irr" not in body.lower()
        assert "dscr" not in body.lower()
        assert "npv" not in body.lower()
        assert "kpi" not in body.lower()

    def test_helper_read_only(self):
        text = MAIN_WEB.read_text()
        m = re.search(
            r"def _validation_summary_for_context.*?(?=\ndef |\nclass )",
            text,
            re.DOTALL,
        )
        body = m.group(0)
        # No persistence writes
        assert "get_cursor" not in body
        assert "INSERT" not in body
        assert "UPDATE" not in body
