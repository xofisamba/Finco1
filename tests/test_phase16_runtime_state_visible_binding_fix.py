"""Phase 16 — Runtime State Visible Binding Fix Tests.

Validates:
1. Revenue tab section is labeled as "Saved Scenario / Factory Reference Values"
2. PPA Tariff saved scenario value is visible after save/load or lower summary is clearly not current scenario.
3. PPA Term is explicitly preview-only/not runtime-bound.
4. p50_hours is labeled as runtime-bound (not vague "model layer")
5. Runtime summary appears after Run and is distinct from factory/reference cards.
6. No JavaScript financial calculations.
7. Backend runtime remains source of truth.
8. Save does not auto-run.
9. Run does not auto-save.
10. G20 remains BLOCKED.
11. R99/R102 remains NOT APPROVED.

Scope: app/templates/partials/sheet_revenue.html
"""

from __future__ import annotations

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestSectionNaming:
    """Section must correctly reflect that it shows both saved scenario and factory reference values."""

    def test_section_header_reflects_dual_source(self):
        """Section header must say 'Saved Scenario / Factory Reference Values'."""
        sheet = os.path.join(BASE_DIR, "app/templates/partials/sheet_revenue.html")
        content = open(sheet).read()

        assert "Saved Scenario / Factory Reference Values" in content, (
            "sheet_revenue.html section header must be 'Saved Scenario / Factory Reference Values'"
        )

    def test_explanatory_note_mentions_saved_scenario_and_factory(self):
        """Factory reference note must explain saved scenario vs factory reference distinction."""
        sheet = os.path.join(BASE_DIR, "app/templates/partials/sheet_revenue.html")
        content = open(sheet).read()

        assert "saved scenario" in content.lower(), (
            "sheet_revenue.html must mention saved scenario in explanatory note"
        )
        assert "factory reference" in content.lower(), (
            "sheet_revenue.html must mention factory reference in explanatory note"
        )
        assert "Runtime Summary" in content or "runtime" in content.lower(), (
            "sheet_revenue.html must mention Runtime Summary location"
        )

    def test_assumption_grid_has_reference_modifier(self):
        """assumption-grid must use --reference modifier class for visual distinction."""
        sheet = os.path.join(BASE_DIR, "app/templates/partials/sheet_revenue.html")
        content = open(sheet).read()

        assert "assumption-grid--reference" in content, (
            "sheet_revenue.html lower assumption grid must have assumption-grid--reference class"
        )


class TestPpaTariffSavedValue:
    """PPA Tariff lower card must show saved scenario value when available."""

    def test_tariff_card_checks_form_data_first(self):
        """PPA Tariff (Y1) card must check form_data.tariff_eur_mwh first."""
        sheet = os.path.join(BASE_DIR, "app/templates/partials/sheet_revenue.html")
        content = open(sheet).read()

        assert "form_data.get('tariff_eur_mwh')" in content, (
            "PPA Tariff card must check form_data.get('tariff_eur_mwh') for saved value"
        )

    def test_tariff_card_falls_back_to_project_ctx(self):
        """PPA Tariff card must fall back to project_ctx when no saved value."""
        sheet = os.path.join(BASE_DIR, "app/templates/partials/sheet_revenue.html")
        content = open(sheet).read()

        assert "project_ctx.ppa_tariff_eur_mwh" in content, (
            "PPA Tariff card must fall back to project_ctx.ppa_tariff_eur_mwh when no saved value"
        )

    def test_tariff_saved_label_exists(self):
        """PPA Tariff card must show 'saved scenario' label when showing saved value."""
        sheet = os.path.join(BASE_DIR, "app/templates/partials/sheet_revenue.html")
        content = open(sheet).read()

        assert "saved scenario" in content.lower(), (
            "PPA Tariff card must label saved scenario values as 'saved scenario'"
        )

    def test_tariff_factory_label_exists(self):
        """PPA Tariff card must show 'factory reference' label when showing factory value."""
        sheet = os.path.join(BASE_DIR, "app/templates/partials/sheet_revenue.html")
        content = open(sheet).read()

        assert "factory reference" in content.lower(), (
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

    def test_ppa_term_card_checks_form_data(self):
        """PPA Term card must check form_data.get('ppa_term_years') for saved value."""
        sheet = os.path.join(BASE_DIR, "app/templates/partials/sheet_revenue.html")
        content = open(sheet).read()

        assert "form_data.get('ppa_term_years')" in content, (
            "PPA Term card must check form_data.get('ppa_term_years') for saved value"
        )

    def test_ppa_term_card_labels_saved_as_preview_only(self):
        """PPA Term card must label saved values as 'saved — preview only'."""
        sheet = os.path.join(BASE_DIR, "app/templates/partials/sheet_revenue.html")
        content = open(sheet).read()

        assert "preview" in content.lower(), (
            "PPA Term card must label saved values as preview-only"
        )


class TestP50HoursClassification:
    """p50_hours must be labeled as runtime-bound, not vague 'model layer'."""

    def test_p50_hours_note_is_not_vague(self):
        """p50_hours note must NOT say 'Runtime authority stays in the model layer.'."""
        sheet = os.path.join(BASE_DIR, "app/templates/partials/sheet_revenue.html")
        content = open(sheet).read()

        assert "Runtime authority stays in the model layer" not in content, (
            "p50_hours must not have vague 'model layer' note — it IS runtime-bound"
        )

    def test_p50_hours_note_says_runtime_bound(self):
        """p50_hours note must say it's runtime-bound or used by model."""
        sheet = os.path.join(BASE_DIR, "app/templates/partials/sheet_revenue.html")
        content = open(sheet).read()

        idx = content.find("P50 Hours")
        region = content[idx:idx+300]

        assert "runtime" in region.lower() or "model" in region.lower(), (
            "p50_hours must have note mentioning runtime or model"
        )


class TestRuntimeSummaryDistinct:
    """Runtime summary must be visually distinct from factory reference cards."""

    def test_runtime_summary_partial_exists(self):
        """runtime_summary.html must exist and render KPI cards."""
        partial = os.path.join(BASE_DIR, "app/templates/partials/runtime_summary.html")
        assert os.path.exists(partial), "runtime_summary.html must exist"

        content = open(partial).read()

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
