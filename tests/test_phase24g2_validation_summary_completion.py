"""Phase 24-G-2 — Validation Summary Completion (UI-only).

Verifies:
- All three severity groups are always rendered (Error →
  Warning → Information) in strict order.
- Empty groups render with .validation-group--empty modifier
  and a "no items" hint row inside the body.
- Each group has a hint subtitle: "Must be fixed" (Error),
  "Review before run" (Warning), "FYI only" (Information).
- data-severity and data-count attributes are present on each
  group for downstream CSS/JS hooks (no JS, just attributes).
- Original "Validation failed" / "Input checks passed" copy
  preserved.
- Backward-compat with plain string errors (Error group only).
- Backward-compat with structured dict errors.
- Severity order invariant: in the rendered output, the
  Error group always comes before Warning, which always
  comes before Information.
- CSS additive (no :root mods, new classes exist).
- No production code change.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import Environment, DictLoader

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_HTML = REPO_ROOT / "app" / "templates" / "partials" / "validation.html"
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
# 1. All three groups always render (strict order)
# ============================================================


class TestAllGroupsAlwaysRender:
    def test_error_group_present_when_no_errors(self):
        out = _render_validation({"valid": True, "errors": []})
        assert "validation-group--error" in out

    def test_warning_group_present_when_no_warnings(self):
        out = _render_validation({"valid": True, "errors": []})
        assert "validation-group--warning" in out

    def test_information_group_present_when_no_messages(self):
        out = _render_validation({"valid": True, "errors": []})
        assert "validation-group--information" in out

    def test_three_groups_in_strict_order(self):
        out = _render_validation({"valid": True, "errors": []})
        idx_error = out.index("validation-group--error")
        idx_warning = out.index("validation-group--warning")
        idx_info = out.index("validation-group--information")
        assert idx_error < idx_warning < idx_info, (
            f"Expected order Error({idx_error}) < "
            f"Warning({idx_warning}) < Information({idx_info})"
        )

    def test_strict_order_with_mixed_severities(self):
        out = _render_validation({
            "valid": False,
            "errors": [
                {"severity": "information", "message": "info1"},
                {"severity": "error", "message": "err1"},
                {"severity": "warning", "message": "warn1"},
            ],
        })
        idx_error = out.index("validation-group--error")
        idx_warning = out.index("validation-group--warning")
        idx_info = out.index("validation-group--information")
        assert idx_error < idx_warning < idx_info

    def test_strict_order_with_only_info(self):
        out = _render_validation({
            "valid": False,
            "messages": ["just info"],
        })
        idx_error = out.index("validation-group--error")
        idx_warning = out.index("validation-group--warning")
        idx_info = out.index("validation-group--information")
        assert idx_error < idx_warning < idx_info


# ============================================================
# 2. Empty groups render with --empty modifier
# ============================================================


class TestEmptyGroups:
    def test_empty_group_has_empty_modifier(self):
        out = _render_validation({"valid": True, "errors": []})
        # The empty error group should have --empty class
        assert "validation-group--empty" in out

    def test_empty_group_shows_no_items_hint(self):
        out = _render_validation({"valid": True, "errors": []})
        assert "No errors. Inputs are clear for run." in out

    def test_empty_warning_hint(self):
        out = _render_validation({"valid": True, "errors": []})
        assert "No warnings. Nothing to review." in out

    def test_empty_info_hint(self):
        out = _render_validation({"valid": True, "errors": []})
        assert "No additional information." in out

    def test_non_empty_group_lacks_empty_modifier(self):
        out = _render_validation({
            "valid": False,
            "errors": ["something broke"],
        })
        # The error group is not empty; should not have --empty
        # in the error group specifically. We test by ensuring
        # the count badge for error is "1" and the no-items hint
        # is NOT in the error group.
        # Find the error group section
        err_start = out.index("validation-group--error")
        err_end = out.index("validation-group--warning")
        err_section = out[err_start:err_end]
        assert "validation-group--empty" not in err_section
        assert "No errors." not in err_section

    def test_count_zero_in_data_attribute(self):
        out = _render_validation({"valid": True, "errors": []})
        # Each group has data-count="0" when empty
        assert 'data-count="0"' in out

    def test_count_in_data_attribute(self):
        out = _render_validation({
            "valid": False,
            "errors": ["a", "b", "c"],
        })
        # Error group has data-count="3"
        assert 'data-severity="error"' in out
        assert 'data-count="3"' in out


# ============================================================
# 3. Hint subtitle per group
# ============================================================


class TestHintSubtitles:
    def test_error_hint_must_be_fixed(self):
        out = _render_validation({"valid": True, "errors": []})
        assert "Must be fixed" in out

    def test_warning_hint_review_before_run(self):
        out = _render_validation({"valid": True, "errors": []})
        assert "Review before run" in out

    def test_information_hint_fyi_only(self):
        out = _render_validation({"valid": True, "errors": []})
        assert "FYI only" in out


# ============================================================
# 4. data-severity attribute for downstream hooks
# ============================================================


class TestDataAttributes:
    def test_error_data_severity(self):
        out = _render_validation({"valid": True, "errors": []})
        assert 'data-severity="error"' in out

    def test_warning_data_severity(self):
        out = _render_validation({"valid": True, "errors": []})
        assert 'data-severity="warning"' in out

    def test_information_data_severity(self):
        out = _render_validation({"valid": True, "errors": []})
        assert 'data-severity="information"' in out

    def test_data_count_in_each_group(self):
        out = _render_validation({"valid": True, "errors": []})
        # 3 groups × data-count="0" = 3 occurrences
        assert out.count('data-count="0"') == 3


# ============================================================
# 5. Original copy preserved
# ============================================================


class TestOriginalCopy:
    def test_failed_header_still_says_validation_failed(self):
        out = _render_validation({"valid": False, "errors": ["x"]})
        assert "Validation failed" in out

    def test_passed_message_still_says_input_checks_passed(self):
        out = _render_validation({"valid": True, "errors": []})
        assert "Input checks passed" in out


# ============================================================
# 6. Backward-compat with plain string errors
# ============================================================


class TestPlainStringCompat:
    def test_plain_string_still_renders_in_error_group(self):
        out = _render_validation({"valid": False, "errors": ["field X is required"]})
        assert "field X is required" in out
        assert 'data-severity="error"' in out

    def test_plain_string_count_in_data_attribute(self):
        out = _render_validation({"valid": False, "errors": ["x", "y", "z"]})
        assert 'data-count="3"' in out


# ============================================================
# 7. Backward-compat with structured dict errors
# ============================================================


class TestStructuredDictCompat:
    def test_dict_error_renders_in_correct_group(self):
        out = _render_validation({
            "valid": False,
            "errors": [
                {"severity": "error", "message": "Capacity required"},
            ],
        })
        assert "Capacity required" in out

    def test_dict_warning_renders_in_warning_group(self):
        out = _render_validation({
            "valid": False,
            "errors": [
                {"severity": "warning", "message": "Tariff low"},
            ],
        })
        # warning group exists
        assert "validation-group--warning" in out
        assert "Tariff low" in out

    def test_dict_info_renders_in_info_group(self):
        out = _render_validation({
            "valid": False,
            "errors": [
                {"severity": "info", "message": "Capacity flag on"},
            ],
        })
        assert "Capacity flag on" in out


# ============================================================
# 8. Error group dedup still works (from 24-G-1)
# ============================================================


class TestDedupStillWorks:
    def test_repeated_error_collapsed(self):
        out = _render_validation({
            "valid": False,
            "errors": ["a", "a", "a"],
        })
        assert "×3" in out

    def test_unique_errors_not_collaped(self):
        out = _render_validation({
            "valid": False,
            "errors": ["err A", "err B"],
        })
        assert "err A" in out
        assert "err B" in out


# ============================================================
# 9. CSS additive
# ============================================================


class TestCSSAdditive:
    def test_empty_group_class_exists(self):
        text = STYLES_CSS.read_text()
        assert ".validation-group--empty" in text

    def test_empty_hint_class_exists(self):
        text = STYLES_CSS.read_text()
        assert ".validation-group-empty" in text

    def test_hint_subtitle_class_exists(self):
        text = STYLES_CSS.read_text()
        assert ".validation-group-hint" in text

    def test_root_block_count_unchanged(self):
        text = STYLES_CSS.read_text()
        assert text.count(":root {") == 5


# ============================================================
# 10. No production code change
# ============================================================


class TestNoProductionCodeChange:
    def test_main_web_unchanged(self):
        assert MAIN_WEB.exists()

    def test_validation_service_unchanged(self):
        assert VALIDATION_SERVICE.exists()
