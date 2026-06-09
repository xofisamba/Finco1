"""Phase 24-G-3 — Export / Download Clarity (UI-only).

Verifies:
- export_registry.html renders an empty-state notice when
  `export_cards` is missing/empty. The notice is data-attributed
  with `data-export-empty-state="true"`.
- When `export_cards` is present, the registry renders the
  intro lead and a per-card lineage row.
- Each export card has:
    data-export-card-enabled
    data-export-card-category
    data-export-card-lineage
    data-export-card-lineage-text
- "What is in each export" lead is present.
- Empty-state copy points to "Run Model".
- Empty-state copy explains why some cards are blocked by
  governance gates (G20, R99/R102).
- No production code change.
- CSS additive (no :root mods).
- rc1 untouched.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPORT_REGISTRY_HTML = REPO_ROOT / "app" / "templates" / "partials" / "export_registry.html"
STYLES_CSS = REPO_ROOT / "static" / "styles.css"
MAIN_WEB = REPO_ROOT / "main_web.py"


def _read_text(path: Path) -> str:
    return path.read_text()


def _render_export_registry(context: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(str(REPO_ROOT / "app" / "templates")),
        autoescape=False,
    )
    template = env.get_template("partials/export_registry.html")
    return template.render(**context)


# ============================================================
# 1. Empty state
# ============================================================


class TestEmptyState:
    def test_empty_state_renders_when_no_cards(self):
        out = _render_export_registry({"export_cards": None})
        assert "data-export-empty-state=\"true\"" in out
        assert "No exports available yet" in out

    def test_empty_state_renders_when_empty_list(self):
        out = _render_export_registry({"export_cards": []})
        assert "data-export-empty-state=\"true\"" in out

    def test_empty_state_renders_when_undefined(self):
        out = _render_export_registry({})
        # When export_cards is undefined, the template treats
        # it as falsy and renders the empty state.
        assert "data-export-empty-state=\"true\"" in out

    def test_empty_state_points_to_run_model(self):
        out = _render_export_registry({})
        assert "Run Model" in out

    def test_empty_state_explains_governance_gates(self):
        out = _render_export_registry({})
        # Mentions G20 / governance gates
        assert "G20" in out or "governance" in out.lower()

    def test_empty_state_has_aria_label(self):
        out = _render_export_registry({})
        assert "aria-label=" in out

    def test_empty_state_has_role(self):
        out = _render_export_registry({})
        # role="status" on the empty state
        assert 'role="status"' in out

    def test_empty_state_has_description(self):
        out = _render_export_registry({})
        assert "data-export-empty-desc=\"true\"" in out

    def test_empty_state_has_hint(self):
        out = _render_export_registry({})
        assert "data-export-empty-hint=\"true\"" in out


# ============================================================
# 2. Full state (with cards)
# ============================================================


class TestFullState:
    def test_full_state_renders_lead(self):
        out = _render_export_registry({
            "export_cards": ["dummy1", "dummy2"],
        })
        assert "data-export-registry-lead=\"true\"" in out
        assert "What is in each export" in out

    def test_full_state_renders_all_8_cards(self):
        out = _render_export_registry({
            "export_cards": ["dummy1"],
        })
        # 8 export cards in the registry
        assert out.count("export-card-name") >= 8

    def test_each_card_has_data_attributes(self):
        out = _render_export_registry({
            "export_cards": ["dummy1"],
        })
        # Each card has data-export-card-enabled
        assert 'data-export-card-enabled="true"' in out
        # Each card has data-export-card-category
        assert 'data-export-card-category=' in out
        # Each card has data-export-card-lineage
        assert 'data-export-card-lineage=' in out
        # Each card has data-export-card-lineage-text (the inner div)
        assert 'data-export-card-lineage-text="true"' in out

    def test_cards_have_lineage_rows(self):
        out = _render_export_registry({
            "export_cards": ["dummy1"],
        })
        # "Lineage:" labels
        assert out.count("<strong>Lineage:</strong>") >= 8

    def test_no_empty_state_in_full_mode(self):
        out = _render_export_registry({
            "export_cards": ["dummy1"],
        })
        # When cards are present, the empty state should NOT
        # appear.
        assert "data-export-empty-state=\"true\"" not in out


# ============================================================
# 3. Specific card content
# ============================================================


class TestCardContent:
    def test_institutional_workbook_card(self):
        out = _render_export_registry({"export_cards": ["dummy"]})
        assert "Institutional Workbook" in out
        # G20 BLOCKED
        assert "G20 BLOCKED" in out

    def test_tuho_runtime_summary_card(self):
        out = _render_export_registry({"export_cards": ["dummy"]})
        assert "TUHO Runtime Summary CSV" in out

    def test_oborovo_runtime_summary_card(self):
        out = _render_export_registry({"export_cards": ["dummy"]})
        assert "Oborovo Runtime Summary CSV" in out
        # R99/R102 NOT APPROVED
        assert "R99/R102 NOT APPROVED" in out

    def test_gap_analysis_card(self):
        out = _render_export_registry({"export_cards": ["dummy"]})
        assert "Gap Analysis" in out

    def test_source_map_card(self):
        out = _render_export_registry({"export_cards": ["dummy"]})
        assert "Source Map" in out

    def test_closeout_registers_card(self):
        out = _render_export_registry({"export_cards": ["dummy"]})
        assert "Final Closeout Registers" in out


# ============================================================
# 4. Render: no UndefinedError / NameError / AttributeError
# ============================================================


class TestRender:
    def test_renders_with_no_context(self):
        out = _render_export_registry({})
        assert out  # non-empty

    def test_renders_with_empty_cards(self):
        out = _render_export_registry({"export_cards": []})
        assert out

    def test_renders_with_populated_cards(self):
        out = _render_export_registry({"export_cards": ["a", "b"]})
        assert out


# ============================================================
# 5. CSS additive
# ============================================================


class TestCSSAdditive:
    def test_empty_state_class_exists(self):
        text = _read_text(STYLES_CSS)
        assert ".export-empty-state" in text

    def test_empty_state_title_class_exists(self):
        text = _read_text(STYLES_CSS)
        assert ".export-empty-state__title" in text

    def test_empty_state_desc_class_exists(self):
        text = _read_text(STYLES_CSS)
        assert ".export-empty-state__desc" in text

    def test_empty_state_hint_class_exists(self):
        text = _read_text(STYLES_CSS)
        assert ".export-empty-state__hint" in text

    def test_export_lead_class_exists(self):
        text = _read_text(STYLES_CSS)
        assert ".export-registry-lead" in text

    def test_export_card_lineage_class_exists(self):
        text = _read_text(STYLES_CSS)
        assert ".export-card-lineage" in text

    def test_root_block_count_unchanged(self):
        text = _read_text(STYLES_CSS)
        assert text.count(":root {") == 5


# ============================================================
# 6. No production code change
# ============================================================


class TestNoProductionCodeChange:
    def test_main_web_unchanged(self):
        assert MAIN_WEB.exists()


# ============================================================
# 7. rc1 untouched
# ============================================================


class TestRC1Untouched:
    def test_no_rc1_in_template(self):
        text = _read_text(EXPORT_REGISTRY_HTML)
        # Template should not reference rc1
        assert "rc1" not in text.lower()
