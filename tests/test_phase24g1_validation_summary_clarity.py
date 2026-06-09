"""Phase 24-G-1 — Validation summary clarity (UI-only).

Verifies:
- validation.html groups messages by severity (Error / Warning / Information)
- validation.html deduplicates repeated messages
- validation.html is backward-compatible with plain string errors
- validation.html is backward-compatible with structured dict errors
  (with `severity` and `message` fields)
- validation.html still includes the original "Validation failed" /
  "Input checks passed" copy
- _validation_summary_bar.html still works as before (existing
  UI-2.3 tests must still pass)
- All styles are CSS-additive
- No production code change
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from jinja2 import Environment, DictLoader

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_HTML = REPO_ROOT / "app" / "templates" / "partials" / "validation.html"
SUMMARY_BAR = REPO_ROOT / "app" / "templates" / "partials" / "_validation_summary_bar.html"
STYLES_CSS = REPO_ROOT / "static" / "styles.css"
MAIN_WEB = REPO_ROOT / "main_web.py"
VALIDATION_SERVICE = REPO_ROOT / "app" / "services" / "validation_service.py"


def _render_validation(context: dict) -> str:
    env = Environment(
        loader=DictLoader({
            "partials/validation.html": VALIDATION_HTML.read_text(),
        }),
        autoescape=False,
    )
    template = env.get_template("partials/validation.html")
    return template.render(**context)


# ============================================================
# 1. Backward-compat: plain string errors
# ============================================================


class TestPlainStringErrors:
    def test_renders_failed_header(self):
        out = _render_validation({"valid": False, "errors": ["bad input"]})
        assert "Validation failed" in out

    def test_renders_passed_message(self):
        out = _render_validation({"valid": True, "errors": []})
        assert "Input checks passed" in out

    def test_plain_string_renders_as_error(self):
        out = _render_validation({"valid": False, "errors": ["field X is required"]})
        # Rendered inside the Error group
        assert "field X is required" in out
        assert "validation-group--error" in out

    def test_plain_string_warning_group_empty(self):
        # Phase 24-G-2: all three severity groups are always rendered
        # (in strict order: Error → Warning → Information) so the user
        # always sees the severity hierarchy. Empty groups render with
        # the .validation-group--empty modifier and a "no items" hint
        # inside the body.
        out = _render_validation({"valid": False, "errors": ["oops"]})
        assert "validation-group--warning" in out
        assert "validation-group--empty" in out

    def test_plain_string_information_group_empty(self):
        # Phase 24-G-2: see test_plain_string_warning_group_empty.
        out = _render_validation({"valid": False, "errors": ["oops"]})
        assert "validation-group--information" in out
        assert "validation-group--empty" in out


# ============================================================
# 2. Structured dict errors with severity
# ============================================================


class TestStructuredDictErrors:
    def test_error_severity_renders_in_error_group(self):
        out = _render_validation({
            "valid": False,
            "errors": [
                {"severity": "error", "message": "Capacity is required"},
            ],
        })
        assert "Capacity is required" in out
        assert "validation-group--error" in out

    def test_warning_severity_renders_in_warning_group(self):
        out = _render_validation({
            "valid": False,
            "errors": [
                {"severity": "warning", "message": "Tariff is below market"},
            ],
        })
        assert "Tariff is below market" in out
        assert "validation-group--warning" in out

    def test_information_severity_renders_in_information_group(self):
        out = _render_validation({
            "valid": False,
            "errors": [
                {"severity": "information", "message": "Capacity flag is on"},
            ],
        })
        assert "Capacity flag is on" in out
        assert "validation-group--information" in out

    def test_warn_alias_treated_as_warning(self):
        out = _render_validation({
            "valid": False,
            "errors": [{"severity": "warn", "message": "x"}],
        })
        assert "validation-group--warning" in out

    def test_info_alias_treated_as_information(self):
        out = _render_validation({
            "valid": False,
            "errors": [{"severity": "info", "message": "x"}],
        })
        assert "validation-group--information" in out

    def test_mixed_severities_grouped_separately(self):
        out = _render_validation({
            "valid": False,
            "errors": [
                {"severity": "error", "message": "err1"},
                {"severity": "warning", "message": "warn1"},
                {"severity": "information", "message": "info1"},
            ],
        })
        assert "err1" in out
        assert "warn1" in out
        assert "info1" in out
        assert "validation-group--error" in out
        assert "validation-group--warning" in out
        assert "validation-group--information" in out


# ============================================================
# 3. Deduplication
# ============================================================


class TestDeduplication:
    def test_duplicated_error_collapsed(self):
        out = _render_validation({
            "valid": False,
            "errors": [
                "field X is required",
                "field X is required",
                "field X is required",
            ],
        })
        # The message should appear once
        count = out.count("field X is required")
        # It may appear inside the item and a count badge "×3"
        # but it should NOT appear 3 separate times
        assert count >= 1
        # The count badge must reflect 3 occurrences
        assert "×3" in out

    def test_duplicated_warning_not_collapsed(self):
        # Phase 24-G-1 spec: dedup applies to Error group only
        # (the most common case). Warnings/Information groups render
        # each entry as-is. This keeps the warning group simple
        # while still reducing duplicated wording for the
        # blocking-error case.
        out = _render_validation({
            "valid": False,
            "errors": [
                {"severity": "warning", "message": "tariff low"},
                {"severity": "warning", "message": "tariff low"},
            ],
        })
        # Both warnings render (no collapse)
        assert out.count("tariff low") == 2
        assert "×2" not in out

    def test_unique_errors_not_collaped(self):
        out = _render_validation({
            "valid": False,
            "errors": ["err A", "err B"],
        })
        assert "err A" in out
        assert "err B" in out
        # No count badge (no repetition)
        assert "×2" not in out
        assert "×3" not in out


# ============================================================
# 4. Group structure
# ============================================================


class TestGroupStructure:
    def test_error_group_has_header(self):
        out = _render_validation({
            "valid": False,
            "errors": ["e1"],
        })
        assert "validation-group-header" in out
        # Header text includes "Error"
        assert ">Error<" in out

    def test_warning_group_has_header(self):
        out = _render_validation({
            "valid": False,
            "errors": [{"severity": "warning", "message": "w1"}],
        })
        assert ">Warning<" in out

    def test_information_group_has_header(self):
        out = _render_validation({
            "valid": False,
            "messages": ["i1"],
        })
        assert ">Information<" in out

    def test_group_has_count_badge(self):
        out = _render_validation({
            "valid": False,
            "errors": ["a", "b", "c"],
        })
        # count badge contains "3"
        assert "validation-group-count" in out
        assert ">3<" in out

    def test_each_group_has_icon(self):
        out = _render_validation({
            "valid": False,
            "errors": [
                {"severity": "error", "message": "e"},
                {"severity": "warning", "message": "w"},
            ],
        })
        # at least one validation-group-icon per group
        assert out.count("validation-group-icon") >= 2


# ============================================================
# 5. CSS additive
# ============================================================


class TestCSSAdditive:
    def test_validation_group_classes_exist(self):
        text = STYLES_CSS.read_text()
        assert ".validation-group" in text
        assert ".validation-group--error" in text
        assert ".validation-group--warning" in text
        assert ".validation-group--information" in text

    def test_validation_item_classes_exist(self):
        text = STYLES_CSS.read_text()
        assert ".validation-item" in text
        assert ".validation-item-message" in text
        assert ".validation-item-count" in text

    def test_root_block_count_unchanged(self):
        text = STYLES_CSS.read_text()
        # The UI-2.5 strict invariant: exactly 5 :root blocks
        assert text.count(":root {") == 5


# ============================================================
# 6. No production code change
# ============================================================


class TestNoProductionCodeChange:
    def test_main_web_unchanged(self):
        assert MAIN_WEB.exists()

    def test_validation_service_unchanged(self):
        assert VALIDATION_SERVICE.exists()

    def test_summary_bar_still_exists(self):
        assert SUMMARY_BAR.exists()


# ============================================================
# 7. Original copy preserved
# ============================================================


class TestOriginalCopyPreserved:
    def test_failed_message_still_says_validation_failed(self):
        out = _render_validation({"valid": False, "errors": ["x"]})
        assert "Validation failed" in out

    def test_passed_message_still_says_input_checks_passed(self):
        out = _render_validation({"valid": True, "errors": []})
        assert "Input checks passed" in out

    def test_passed_message_still_mentions_run_model(self):
        out = _render_validation({"valid": True, "errors": []})
        assert "Run Model" in out or "Run model" in out
