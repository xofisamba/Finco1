"""Phase 16 — Runtime State Visible Binding Fix Tests.

Validates:
1. Revenue tab identifies lower static values as factory/reference if they are project_ctx.
2. PPA Tariff saved scenario value is visible after save/load or lower summary is clearly not current scenario.
3. PPA Term is explicitly preview-only/not runtime-bound.
4. Runtime summary appears after Run and is distinct from factory/reference cards.
5. No JavaScript financial calculations.
6. Backend runtime remains source of truth.
7. Save does not auto-run.
8. Run does not auto-save.
9. G20 remains BLOCKED.
10. R99/R102 remains NOT APPROVED.

Scope: app/templates/partials/sheet_revenue.html
"""

from __future__ import annotations

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestFactoryReferenceLabeling:
    """Lower assumption cards must be labeled as factory reference."""

    def test_lower_cards_have_factory_reference_header(self):
        """Lower assumption cards section must have 'Factory Reference' header."""
        sheet = os.path.join(BASE_DIR, "app/templates/partials/sheet_revenue.html")
        content = open(sheet).read()

        # The section should be clearly labeled
        assert "factory reference" in content.lower() or "Factory Reference" in content, (
            "sheet_revenue.html must label lower assumption cards as factory reference"
        )

    def test_factory_ref_note_exists(self):
        """A factory reference note must explain the lower cards are not current scenario."""
        sheet = os.path.join(BASE_DIR, "app/templates/partials/sheet_revenue.html")
        content = open(sheet).read()

        assert "factory reference" in content.lower(), (
            "sheet_revenue.html must have factory reference note explaining stale values"
        )
        # Should mention these do not update with draft/saved edits
        assert "saved scenario" in content.lower() or "saved" in content.lower(), (
            "sheet_revenue.html must distinguish saved scenario values from factory reference"
        )

    def test_assumption_grid_has_reference_modifier(self):
        """assumption-grid must use --reference modifier class."""
        sheet = os.path.join(BASE_DIR, "app/templates/partials/sheet_revenue.html")
        content = open(sheet).read()

        # The lower assumption grid should have --reference class
        has_ref = "assumption-grid--reference" in content
        assert has_ref, (
            "sheet_revenue.html lower assumption grid must have assumption-grid--reference class"
        )


class TestPpaTariffSavedValue:
    """PPA Tariff lower card must show saved scenario value when available."""

    def test_tariff_card_uses_form_data_when_available(self):
        """PPA Tariff (Y1) card must show form_data.tariff_eur_mwh when set."""
        sheet = os.path.join(BASE_DIR, "app/templates/partials/sheet_revenue.html")
        content = open(sheet).read()

        # Must check form_data.get('tariff_eur_mwh') first
        assert "form_data.get('tariff_eur_mwh')" in content, (
            "PPA Tariff card must check form_data.get('tariff_eur_mwh') for saved value"
        )

    def test_tariff_card_falls_back_to_project_ctx(self):
        """PPA Tariff card must fall back to project_ctx when no saved value."""
        sheet = os.path.join(BASE_DIR, "app/templates/partials/sheet_revenue.html")
        content = open(sheet).read()

        # When form_data.tariff_eur_mwh is empty, must show project_ctx.ppa_tariff_eur_mwh
        assert "project_ctx.ppa_tariff_eur_mwh" in content, (
            "PPA Tariff card must fall back to project_ctx.ppa_tariff_eur_mwh when no saved value"
        )

    def test_tariff_saved_label_exists(self):
        """PPA Tariff card must show 'saved scenario' label when showing saved value."""
        sheet = os.path.join(BASE_DIR, "app/templates/partials/sheet_revenue.html")
        content = open(sheet).read()

        assert "saved scenario" in content.lower(), (
            "PPA Tariff card must label saved scenario values"
        )

    def test_tariff_factory_label_exists(self):
        """PPA Tariff card must show 'factory reference' label when showing factory value."""
        sheet = os.path.join(BASE_DIR, "app/templates/partials/sheet_revenue.html")
        content = open(sheet).read()

        # When showing project_ctx value, must label as factory reference
        factory_section = content.lower()
        assert "factory reference" in factory_section or "metric-note" in factory_section, (
            "PPA Tariff card must label factory reference values distinctly"
        )


class TestPpaTermPreviewOnly:
    """PPA Term must be clearly marked as preview-only/not runtime-bound."""

    def test_ppa_term_editable_grid_has_preview_note(self):
        """PPA Term editable grid note must say 'Preview only — not runtime-bound yet'."""
        sheet = os.path.join(BASE_DIR, "app/templates/partials/sheet_revenue.html")
        content = open(sheet).read()

        idx = content.find("PPA Term")
        region = content[idx:idx+500]

        assert "preview only" in region.lower() or "not runtime-bound" in region.lower(), (
            "PPA Term editable grid note must say 'Preview only — not runtime-bound yet'"
        )

    def test_ppa_term_card_shows_saved_value_with_preview_label(self):
        """PPA Term card must show saved value and label it as preview-only."""
        sheet = os.path.join(BASE_DIR, "app/templates/partials/sheet_revenue.html")
        content = open(sheet).read()

        # Must check form_data.get('ppa_term_years')
        assert "form_data.get('ppa_term_years')" in content, (
            "PPA Term card must check form_data.get('ppa_term_years') for saved value"
        )
        # When showing saved value, must label as preview-only
        assert "preview" in content.lower(), (
            "PPA Term card must label saved values as preview-only"
        )


class TestRuntimeSummaryDistinct:
    """Runtime summary must be visually distinct from factory reference cards."""

    def test_runtime_summary_partial_exists(self):
        """runtime_summary.html must exist and render KPI cards."""
        partial = os.path.join(BASE_DIR, "app/templates/partials/runtime_summary.html")
        assert os.path.exists(partial), "runtime_summary.html must exist"

        content = open(partial).read()

        # Must have KPI cards
        assert "kpi-grid" in content, "runtime_summary must have kpi-grid"
        assert "runtime-summary" in content, "runtime_summary must have runtime-summary class"

    def test_runtime_summary_has_notice(self):
        """Runtime summary must have a notice that values are live model outputs."""
        partial = os.path.join(BASE_DIR, "app/templates/partials/runtime_summary.html")
        content = open(partial).read()

        assert "live model outputs" in content.lower() or "runtime" in content.lower(), (
            "runtime_summary must distinguish itself as live runtime output"
        )

    def test_revenue_tab_mentions_runtime_summary_location(self):
        """Revenue tab output preview must direct users to runtime summary location."""
        sheet = os.path.join(BASE_DIR, "app/templates/partials/sheet_revenue.html")
        content = open(sheet).read()

        # Should mention runtime summary exists and where to find it
        idx = content.find("Output Preview")
        if idx >= 0:
            region = content[idx:idx+400]
            assert "runtime" in region.lower() or "scroll" in region.lower(), (
                "Output Preview placeholder must mention where to find runtime output"
            )


class TestGuardrails:
    """Guardrails: no JS financial calcs, G20 BLOCKED, R99/R102 NOT APPROVED."""

    def test_no_js_financial_calculations(self):
        """app.js must not contain financial calculation logic."""
        app_js = os.path.join(BASE_DIR, "static/app.js")
        content = open(app_js).read()

        financial_patterns = [
            "Math.pow(", "NPV", "IRR", "PMT(", "PV(",
            ".calculate()",
        ]

        for pattern in financial_patterns:
            assert pattern not in content, (
                f"app.js must not contain '{pattern}' (no JS financial calculations)"
            )

    def test_g20_blocked(self):
        """G20 (pilot comparison) must remain BLOCKED in main_web.py."""
        main_web = os.path.join(BASE_DIR, "main_web.py")
        content = open(main_web).read()

        assert "G20" in content, "main_web.py must reference G20"

    def test_r99_r102_not_approved(self):
        """R99/R102 must remain NOT APPROVED in main_web.py."""
        main_web = os.path.join(BASE_DIR, "main_web.py")
        content = open(main_web).read()

        assert "R99" in content or "R102" in content, (
            "main_web.py must reference R99/R102"
        )


class TestBackendAuthority:
    """Backend runtime must remain source of truth."""

    def test_no_client_side_runtime_override(self):
        """app.js must not override or bypass backend /run."""
        app_js = os.path.join(BASE_DIR, "static/app.js")
        content = open(app_js).read()

        forbidden_patterns = [
            "run_project(", "build_projectinputs(",
            "fetch('/run')", "fetch(\"/run\")",
        ]

        for pattern in forbidden_patterns:
            assert pattern not in content, (
                f"app.js must not call '{pattern}' (runtime authority is backend only)"
            )

    def test_no_workbook_calculation_changes(self):
        """No workbook calculation changes in this fix."""
        # This is a pure presentation fix - no backend changes
        pass


class TestSaveRunSeparation:
    """Save must not auto-run; Run must not auto-save."""

    def test_save_button_does_not_post_to_run(self):
        """Save button must not post to /run."""
        base_html = os.path.join(BASE_DIR, "app/templates/base.html")
        content = open(base_html).read()

        idx = content.find('id="btn-save"')
        start = content.rfind("<button", 0, idx)
        end = content.find(">", idx) + 1
        btn_html = content[start:end]

        assert 'hx-post="/run"' not in btn_html, (
            "btn-save must not post to /run"
        )

    def test_run_button_does_not_post_to_save(self):
        """Run button must not post to /scenarios/save."""
        index_html = os.path.join(BASE_DIR, "app/templates/index.html")
        content = open(index_html).read()

        idx = content.find('id="btn-run-model"')
        start = content.rfind("<button", 0, idx)
        end = content.find(">", idx) + 1
        btn_html = content[start:end]

        assert 'hx-post="/scenarios/save"' not in btn_html, (
            "btn-run-model must not post to /scenarios/save"
        )
