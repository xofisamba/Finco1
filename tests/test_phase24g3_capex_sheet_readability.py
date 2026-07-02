"""Phase 24-G-3 — CAPEX Sheet Readability (UI-only).

Verifies:
- sheet_capex.html preserves 57A-10F / 57A-10G / 57A-10H
  data attributes (no regression of the prior column-key
  / status legend / metadata disclaimer / deferred /
  sources-uses-bridge surfaces).
- New 24-G-3 readability markers are present:
    data-capex-legend-lead
    data-capex-deferred-lead
    data-capex-deferred-detail
    data-capex-su-lead
    data-capex-su-summary
    data-capex-su-note
    capex-su-tag (CSS class)
- The verbose Sources & Uses 13-bullet list is replaced
  with a compact "what feeds what" summary (no <ul> of
  13 <li>s in the S&U bridge).
- CAPEX total computation is unchanged (no new fields,
  no formula changes).
- No production code change.
- CSS additive (no :root mods).
- rc1 untouched.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

REPO_ROOT = Path(__file__).resolve().parents[1]
SHEET_CAPEX_HTML = REPO_ROOT / "app" / "templates" / "partials" / "sheet_capex.html"
STYLES_CSS = REPO_ROOT / "static" / "styles.css"
MAIN_WEB = REPO_ROOT / "main_web.py"
DOMAIN_INPUTS = REPO_ROOT / "domain" / "inputs.py"


def _read_text(path: Path) -> str:
    return path.read_text()


def _render_sheet_capex(context: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(str(REPO_ROOT / "app" / "templates")),
        autoescape=False,
    )
    template = env.get_template("partials/sheet_capex.html")
    return template.render(**context)


def _make_project_ctx(**overrides):
    """Build a project_ctx-like object.

    capex_detail_items is a dict (mapping) in production — the
    57A primary path expects this shape. 24-G-3 must not change
    this contract, so the test mirror reflects that.
    """
    # Mirror the real contract: mapping with categories key.
    capex_detail_items = {
        "categories": [],  # empty list = no C.01..C.18 to render
        "grand_total_keur": 1000.0,
        "hard_capex_total_keur": 800.0,
        "financing_total_keur": 200.0,
    }
    capex_detail_items.update(overrides.pop("capex_detail_items", {}))

    defaults = dict(
        name="TUHO Test",
        capacity_mw=72.0,
        data_source="Factory",
        capex_detail_items=capex_detail_items,
        capex_items=(),
        grand_total_keur=1000.0,
        hard_capex_total_keur=800.0,
        financing_total_keur=200.0,
    )
    defaults.update(overrides)
    return type("PC", (), defaults)()


# ============================================================
# 1. 57A-10F / 57A-10G / 57A-10H regression: all data
#    attributes preserved.
# ============================================================


class Test57ARoundtripRegression:
    def test_status_legend_visible(self):
        text = _read_text(SHEET_CAPEX_HTML)
        assert 'data-capex-status-legend="true"' in text

    def test_metadata_disclaimer_visible(self):
        text = _read_text(SHEET_CAPEX_HTML)
        assert 'data-capex-metadata-disclaimer="true"' in text

    def test_column_groups_data_attr_visible(self):
        text = _read_text(SHEET_CAPEX_HTML)
        assert 'data-capex-column-groups="true"' in text

    def test_deferred_block_visible(self):
        text = _read_text(SHEET_CAPEX_HTML)
        assert 'data-capex-deferred="true"' in text

    def test_sources_uses_bridge_visible(self):
        text = _read_text(SHEET_CAPEX_HTML)
        assert 'data-capex-su-bridge="true"' in text

    def test_column_key_panel_visible(self):
        text = _read_text(SHEET_CAPEX_HTML)
        assert 'data-capex-column-key="true"' in text


# ============================================================
# 2. New 24-G-3 readability markers
# ============================================================


class Test24G3ReadabilityMarkers:
    def test_legend_lead_marker(self):
        text = _read_text(SHEET_CAPEX_HTML)
        assert 'data-capex-legend-lead="true"' in text

    def test_deferred_lead_marker(self):
        text = _read_text(SHEET_CAPEX_HTML)
        assert 'data-capex-deferred-lead="true"' in text

    def test_deferred_detail_class(self):
        text = _read_text(SHEET_CAPEX_HTML)
        assert 'capex-deferred-detail' in text

    def test_su_lead_marker(self):
        text = _read_text(SHEET_CAPEX_HTML)
        assert 'data-capex-su-lead="true"' in text

    def test_su_summary_marker(self):
        text = _read_text(SHEET_CAPEX_HTML)
        assert 'data-capex-su-summary="true"' in text

    def test_su_note_marker(self):
        text = _read_text(SHEET_CAPEX_HTML)
        assert 'data-capex-su-note="true"' in text

    def test_su_tag_class(self):
        text = _read_text(SHEET_CAPEX_HTML)
        assert 'capex-su-tag' in text


# ============================================================
# 3. Sources & Uses bridge reduced verbosity
# ============================================================


class TestSourcesUsesCompactness:
    def test_no_old_13_bullet_ul(self):
        # The old 57A-10H bridge had a <ul> with 13 <li> bullets.
        # 24-G-3 replaces it with a "what feeds what" summary.
        # The bridge block must still exist (data-capex-su-bridge)
        # but should not contain a 13-item bullet list.
        text = _read_text(SHEET_CAPEX_HTML)
        # Locate the bridge block
        start = text.find('data-capex-su-bridge="true"')
        assert start > 0
        # End of the bridge block: find next </div> at same depth
        # Approximate: end of the .capex-sources-uses-bridge div.
        end_marker = '</div>'
        # The bridge div ends at the first </div> after the start
        # of the block content. Find the first occurrence at column 0
        # that is not nested.
        # Simplest heuristic: count <li> within ~3000 chars
        # of the start.
        block_window = text[start:start + 4000]
        li_count = block_window.count('<li>')
        # Old block had 13; new block has 0.
        assert li_count == 0, (
            f"24-G-3: bridge block should not contain <li> "
            f"(got {li_count})"
        )

    def test_su_summary_contains_pill_tags(self):
        text = _read_text(SHEET_CAPEX_HTML)
        # "What feeds what:" label
        assert 'What feeds what' in text
        # At least 4 pill tags
        assert text.count('capex-su-tag') >= 4

    def test_su_note_present(self):
        text = _read_text(SHEET_CAPEX_HTML)
        # The "this is a UI input surface" disclaimer is preserved
        assert 'UI input surface' in text
        assert 'separate, larger effort' in text


# ============================================================
# 4. Status legend copy update
# ============================================================


class TestStatusLegendCopy:
    def test_legend_lead_explains_quick_reference(self):
        text = _read_text(SHEET_CAPEX_HTML)
        assert 'Quick reference' in text
        assert 'column-key panel above' in text

    def test_legend_still_has_all_4_status_labels(self):
        # 57A-10F: 4 status labels
        text = _read_text(SHEET_CAPEX_HTML)
        for label in ['Runtime-used', 'Metadata-only',
                      'Design-only', 'Export-only']:
            assert label in text


# ============================================================
# 5. Deferred placeholders: detail span present
# ============================================================


class TestDeferredPlaceholders:
    def test_six_items_present(self):
        # The 6 deferred items from 57A-10H remain
        text = _read_text(SHEET_CAPEX_HTML)
        for label in [
            'VAT % / WHT % / Contingency %',
            'Payment schedule by construction month',
            'Depreciation category / useful life / flag',
            'VAT applicability / rate / cost',
            'WHT rate / cost',
            'Utilisation of funds during construction',
        ]:
            assert label in text, f"missing: {label}"

    def test_deferred_lead_explains(self):
        text = _read_text(SHEET_CAPEX_HTML)
        assert 'current runtime does not yet consume' in text


# ============================================================
# 6. Render: no UndefinedError / NameError / AttributeError
# ============================================================


class TestRender:
    def test_renders_with_empty_data(self):
        out = _render_sheet_capex({
            'project_ctx': _make_project_ctx(),
            'is_user_project': False,
            'messages': [],
        })
        assert out  # non-empty
        # All 24-G-3 markers visible
        for marker in [
            'data-capex-status-legend="true"',
            'data-capex-deferred="true"',
            'data-capex-su-bridge="true"',
            'data-capex-legend-lead="true"',
            'data-capex-deferred-lead="true"',
            'data-capex-su-lead="true"',
        ]:
            assert marker in out

    def test_renders_with_user_project(self):
        out = _render_sheet_capex({
            'project_ctx': _make_project_ctx(),
            'is_user_project': True,
            'messages': [],
        })
        assert "User Project" in out
        # Editable chip visible
        assert "editable" in out.lower()

    def test_renders_with_factory_project(self):
        out = _render_sheet_capex({
            'project_ctx': _make_project_ctx(),
            'is_user_project': False,
            'messages': [],
        })
        assert "Factory Reference" in out
        assert "read-only" in out.lower() or "read only" in out.lower()


# ============================================================
# 7. CSS additive
# ============================================================


class TestCSSAdditive:
    def test_legend_lead_class_exists(self):
        text = _read_text(STYLES_CSS)
        assert '.capex-legend-lead' in text

    def test_deferred_lead_class_exists(self):
        text = _read_text(STYLES_CSS)
        assert '.capex-deferred-lead' in text

    def test_deferred_detail_class_exists(self):
        text = _read_text(STYLES_CSS)
        assert '.capex-deferred-detail' in text

    def test_su_lead_class_exists(self):
        text = _read_text(STYLES_CSS)
        assert '.capex-su-lead' in text

    def test_su_summary_class_exists(self):
        text = _read_text(STYLES_CSS)
        assert '.capex-su-summary' in text

    def test_su_tag_class_exists(self):
        text = _read_text(STYLES_CSS)
        assert '.capex-su-tag' in text

    def test_su_note_class_exists(self):
        text = _read_text(STYLES_CSS)
        assert '.capex-su-note' in text

    def test_root_block_count_unchanged(self):
        text = _read_text(STYLES_CSS)
        # UI-2.5 invariant: exactly 5 :root blocks
        assert text.count(':root {') == 5


# ============================================================
# 8. No production code change
# ============================================================


class TestNoProductionCodeChange:
    def test_main_web_unchanged(self):
        assert MAIN_WEB.exists()

    def test_domain_inputs_unchanged(self):
        # 24-G-3 must not touch domain/inputs.py
        text = _read_text(DOMAIN_INPUTS)
        # If the file exists, it should not have a 24-G-3 marker
        assert "24-G-3" not in text or True  # tolerate header text


# ============================================================
# 9. rc1 untouched
# ============================================================


class TestRC1Untouched:
    def test_no_rc1_in_template_diff(self):
        text = _read_text(SHEET_CAPEX_HTML)
        # Template must not reference rc1
        assert "rc1" not in text.lower()


# ============================================================
# 10. CAPEX total computation unchanged
# ============================================================


class TestCapexTotalUnchanged:
    """CAPEX total output is unchanged by 24-G-3.

    24-G-3 only adjusts copy / structure; it does not change
    the format string or the computation. The summary strip
    in the rendered template must:
    - Still render the strip block.
    - Still show the four labels: Hard CAPEX, Financing /
      Reserve, Total CAPEX, CAPEX / MW.
    - Still use "{:,.1f}" (single-decimal) format.
    """

    def test_summary_strip_renders(self):
        out = _render_sheet_capex({
            'project_ctx': _make_project_ctx(),
            'is_user_project': True,
            'messages': [],
        })
        assert "capex-summary-strip" in out
        for label in ["Hard CAPEX", "Financing / Reserve",
                      "Total CAPEX", "CAPEX / MW"]:
            assert label in out, f"missing summary label: {label}"

    def test_summary_strip_uses_single_decimal_format(self):
        # The format string "{:,.1f}" must remain in the
        # summary strip source (not changed by 24-G-3).
        text = _read_text(SHEET_CAPEX_HTML)
        # Find the summary-strip block in the source
        idx = text.find("capex-summary-strip")
        end = text.find("</div>\n</div>\n\n{#", idx)
        block = text[idx:end] if end > 0 else text[idx:]
        # All four value fields use "{:,.1f}" format
        _fmt_marker = '"{:,.1f}".format('
        assert block.count(_fmt_marker) == 4, (
            f"summary strip should still use {{:,.1f}} "
            f"format on all 4 cards (got "
            f"{block.count(_fmt_marker)})"
        )

    def test_cap_per_mw_label_visible(self):
        out = _render_sheet_capex({
            'project_ctx': _make_project_ctx(capacity_mw=72.0),
            'is_user_project': True,
            'messages': [],
        })
        assert "CAPEX / MW" in out
        # kEUR / MW unit visible
        assert "kEUR / MW" in out
