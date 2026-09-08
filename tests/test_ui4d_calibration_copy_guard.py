"""UI-4D — Calibration-copy guard (Section 7).

Verifies:
- CAPEX factory/source sub-line notes are NOT rendered in the standard workbook.
- OPEX factory/source line notes are NOT rendered in the standard workbook.
- Custom user-added row notes ARE preserved in the CAPEX template.
- Excel/calibration comparison language is absent from standard workbook templates.
- The word "Reference" as part of product concept ("Reference Project") is NOT banned.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CAPEX_TMPL = REPO_ROOT / "app" / "templates" / "v2" / "partials" / "sheet_capex.html"
OPEX_TMPL = REPO_ROOT / "app" / "templates" / "v2" / "partials" / "sheet_opex.html"


# ---------------------------------------------------------------------------
# 1. Factory/source subline notes suppressed in CAPEX
# ---------------------------------------------------------------------------

class TestCapexCalibrationNotesSuppressed:
    def test_subline_row_does_not_render_line_notes(self):
        text = CAPEX_TMPL.read_text(encoding="utf-8")
        # The subline_row macro must not have {{ line.notes }} in its body
        # (calibration evidence must be suppressed in standard UI)
        subline_start = text.find("macro subline_row")
        subline_end = text.find("endmacro", subline_start)
        assert subline_start > 0, "subline_row macro not found in sheet_capex.html"
        subline_body = text[subline_start:subline_end]
        assert "line.notes" not in subline_body, (
            "subline_row must NOT render line.notes in standard product view. "
            "Calibration evidence is suppressed (future Audit UI will expose it)."
        )

    def test_custom_row_notes_preserved(self):
        text = CAPEX_TMPL.read_text(encoding="utf-8")
        # custom_row must still render notes for user-entered custom rows
        custom_start = text.find("macro custom_row")
        custom_end = text.find("endmacro", custom_start)
        assert custom_start > 0, "custom_row macro not found in sheet_capex.html"
        custom_body = text[custom_start:custom_end]
        assert "notes" in custom_body, (
            "custom_row must preserve user-entered notes field."
        )


# ---------------------------------------------------------------------------
# 2. Factory/source line notes suppressed in OPEX
# ---------------------------------------------------------------------------

class TestOpexCalibrationNotesSuppressed:
    def test_opex_line_row_does_not_render_notes(self):
        text = OPEX_TMPL.read_text(encoding="utf-8")
        line_row_start = text.find("macro opex_line_row")
        line_row_end = text.find("endmacro", line_row_start)
        assert line_row_start > 0, "opex_line_row macro not found in sheet_opex.html"
        line_row_body = text[line_row_start:line_row_end]
        assert "line.notes" not in line_row_body, (
            "opex_line_row must NOT render line.notes in standard product view."
        )

    def test_opex_custom_row_notes_preserved(self):
        text = OPEX_TMPL.read_text(encoding="utf-8")
        custom_start = text.find("macro opex_custom_row")
        custom_end = text.find("endmacro", custom_start)
        assert custom_start > 0, "opex_custom_row macro not found in sheet_opex.html"
        custom_body = text[custom_start:custom_end]
        assert "notes" in custom_body, (
            "opex_custom_row must preserve user-entered notes field."
        )


# ---------------------------------------------------------------------------
# 3. Excel/calibration language absent from standard workbook templates
# ---------------------------------------------------------------------------

CALIBRATION_PATTERNS = [
    r"Excel\s+reference",
    r"App\s+vs\s+Excel",
    r"no\s+app\s+field\s+maps",
    r"mapping\s+diff",
    r"calibration\s+reference",
]

WORKBOOK_TEMPLATES = list(
    (REPO_ROOT / "app" / "templates" / "v2" / "partials").glob("sheet_*.html")
)


class TestNoCalibrationLanguageInStandardUI:
    @pytest.mark.parametrize("template", WORKBOOK_TEMPLATES,
                             ids=[t.name for t in WORKBOOK_TEMPLATES])
    @pytest.mark.parametrize("pattern", CALIBRATION_PATTERNS,
                             ids=CALIBRATION_PATTERNS)
    def test_no_calibration_phrase(self, template, pattern):
        text = template.read_text(encoding="utf-8")
        # Strip Jinja comments — calibration evidence may still live in comments
        # for developer reference; only user-visible content is guarded.
        text_no_jinja_comments = re.sub(r"\{#.*?#\}", "", text, flags=re.DOTALL)
        assert not re.search(pattern, text_no_jinja_comments, re.IGNORECASE), (
            f"Calibration/development phrase {pattern!r} found in {template.name}. "
            "Standard workbook must not expose Excel reconciliation copy."
        )

    def test_reference_project_not_banned(self):
        # "Reference Project" is a legitimate product concept — must not be banned.
        text = CAPEX_TMPL.read_text(encoding="utf-8")
        assert "Reference project" in text or "reference" in text.lower(), (
            "'Reference project' is a product concept and must remain usable."
        )
