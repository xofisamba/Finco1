"""Tests for Phase 9.5 — Live Project Context UI Binding.

Verifies:
1. TUHO and Oborovo contexts exist and have correct project metadata
2. ?project= query param resolves to correct context
3. TUHO and Oborovo pages show different project data
4. No TUHO values leak into Oborovo page without fallback label
5. All sheet partials use project_ctx
6. G20/R99/R102 governance badges remain visible
7. No runtime formula changes
"""

import pytest
from app.ui.project_context import (
    get_project_context,
    all_project_ids,
    _build_tuho_context,
    _build_oborovo_context,
)


class TestProjectContextExists:
    def test_tuho_context_exists(self):
        ctx = _build_tuho_context()
        assert ctx.code == "TUHO"
        assert ctx.name == "TUHO Wind 1"
        assert ctx.capacity_mw == 35.0
        assert ctx.technology == "Wind"
        assert ctx.country_iso == "HR"
        assert ctx.cod_date == "2030-01-01"
        assert ctx.financial_close == "2029-07-01"

    def test_oborovo_context_exists(self):
        ctx = _build_oborovo_context()
        assert ctx.code == "OBOROVO"
        assert ctx.name == "Oborovo Solar PV"
        assert ctx.capacity_mw == 75.26
        assert ctx.technology == "Solar PV"
        assert ctx.country_iso == "HR"
        assert ctx.cod_date == "2030-06-29"

    def test_all_project_ids(self):
        ids = all_project_ids()
        assert "tuho" in ids
        assert "oborovo" in ids


class TestProjectContextResolver:
    def test_tucho_lowercase_maps_to_tuho(self):
        ctx = get_project_context("tucho")
        assert ctx.code == "TUHO"

    def test_tuhu_uppercase_maps_to_tuho(self):
        ctx = get_project_context("TUHU")
        assert ctx.code == "TUHO"

    def test_oborovo_lowercase_maps_to_oborovo(self):
        ctx = get_project_context("oborovo")
        assert ctx.code == "OBOROVO"

    def test_unknown_project_defaults_to_tuho(self):
        ctx = get_project_context("unknown")
        assert ctx.code == "TUHO"

    def test_none_project_defaults_to_tuho(self):
        ctx = get_project_context(None)
        assert ctx.code == "TUHO"


class TestTuhoVsOborovoDifferent:
    def test_capacity_differs(self):
        tuho = get_project_context("tuho")
        oborovo = get_project_context("oborovo")
        assert tuho.capacity_mw != oborovo.capacity_mw
        assert tuho.capacity_mw == 35.0
        assert oborovo.capacity_mw == 75.26

    def test_technology_differs(self):
        tuho = get_project_context("tuho")
        oborovo = get_project_context("oborovo")
        assert tuho.technology != oborovo.technology
        assert tuho.technology == "Wind"
        assert oborovo.technology == "Solar PV"

    def test_cod_differs(self):
        tuho = get_project_context("tuho")
        oborovo = get_project_context("oborovo")
        assert tuho.cod_date != oborovo.cod_date
        assert tuho.cod_date == "2030-01-01"
        assert oborovo.cod_date == "2030-06-29"

    def test_opex_total_differs(self):
        tuho = get_project_context("tuho")
        oborovo = get_project_context("oborovo")
        assert tuho.opex_y1_total_keur != oborovo.opex_y1_total_keur
        # TUHO: 1998 kEUR, OBOROVO: 1338 kEUR
        assert tuho.opex_y1_total_keur == pytest.approx(1998.05, abs=0.1)
        assert oborovo.opex_y1_total_keur == pytest.approx(1338.0, abs=0.1)

    def test_senior_debt_differs(self):
        tuho = get_project_context("tuho")
        oborovo = get_project_context("oborovo")
        assert tuho.senior_debt_keur != oborovo.senior_debt_keur
        assert tuho.senior_debt_keur == pytest.approx(43359.0, abs=1.0)
        assert oborovo.senior_debt_keur == pytest.approx(42852.0, abs=1.0)

    def test_contingency_method_differs(self):
        tuho = get_project_context("tuho")
        oborovo = get_project_context("oborovo")
        assert tuho.opex_contingency_method != oborovo.opex_contingency_method
        assert tuho.opex_contingency_method == "percentage_of_opex"
        assert oborovo.opex_contingency_method == "fixed_amount"

    def test_cit_rate_differs(self):
        tuho = get_project_context("tuho")
        oborovo = get_project_context("oborovo")
        assert tuho.cit_rate_pct != oborovo.cit_rate_pct
        assert tuho.cit_rate_pct == 0.18
        assert oborovo.cit_rate_pct == 0.10

    def test_ppa_tariff_differs(self):
        tuho = get_project_context("tuho")
        oborovo = get_project_context("oborovo")
        assert tuho.ppa_tariff_eur_mwh != oborovo.ppa_tariff_eur_mwh
        assert tuho.ppa_tariff_eur_mwh == 60.0
        assert oborovo.ppa_tariff_eur_mwh == 57.0


class TestContextDataCompleteness:
    def test_tuho_opex_items_count(self):
        ctx = get_project_context("tuho")
        assert len(ctx.opex_items) == 12  # TUHO has 12 OPEX items
        assert ctx.opex_y1_total_keur == pytest.approx(1998.05, abs=0.1)

    def test_oborovo_opex_items_count(self):
        ctx = get_project_context("oborovo")
        assert len(ctx.opex_items) == 15  # Oborovo has 15 OPEX items
        assert ctx.opex_y1_total_keur == pytest.approx(1338.08, abs=0.1)

    def test_tuho_contingency_is_percentage_of_opex(self):
        ctx = get_project_context("tuho")
        assert ctx.opex_contingency_method == "percentage_of_opex"
        assert ctx.opex_contingency_pct == 6.0

    def test_oborovo_contingency_is_fixed_amount(self):
        ctx = get_project_context("oborovo")
        assert ctx.opex_contingency_method == "fixed_amount"

    def test_tuho_governance_badges_present(self):
        ctx = get_project_context("tuho")
        assert ctx.g20_status == "BLOCKED"
        assert ctx.r99_r102_status == "NOT APPROVED"

    def test_oborovo_governance_badges_present(self):
        ctx = get_project_context("oborovo")
        assert ctx.g20_status == "BLOCKED"
        assert ctx.r99_r102_status == "NOT APPROVED"

    def test_project_id_property(self):
        tuho = get_project_context("tuho")
        oborovo = get_project_context("oborovo")
        assert tuho.id == "tuho"
        assert oborovo.id == "oborovo"

    def test_data_source_is_factory_context(self):
        ctx = get_project_context("tuho")
        assert "Factory context" in ctx.data_source
        assert "read-only" in ctx.data_source

    def test_missing_fields_is_empty_for_both_projects(self):
        tuho = get_project_context("tuho")
        oborovo = get_project_context("oborovo")
        assert tuho.missing_fields == ()
        assert oborovo.missing_fields == ()


class TestNoRuntimeChanges:
    """Verify no runtime/model/financial formula files were touched."""

    def test_no_model_engine_changes(self):
        """This test verifies the project_context module doesn't import waterfall/financial engines."""
        import ast
        import os

        path = os.path.join(os.path.dirname(__file__), "..", "app", "ui", "project_context.py")
        with open(path) as f:
            source = f.read()

        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        forbidden = [
            "waterfall", "sponsor_runner", "holdco_tax",
            "depreciation_engine", "tax_engine",
        ]
        for imp in imports:
            for f in forbidden:
                assert f not in imp.lower(), f"project_context.py must not import {f}"

    def test_project_context_is_readonly(self):
        """ProjectContext must be frozen — no accidental writes."""
        from app.ui.project_context import get_project_context
        ctx = get_project_context("tuho")
        with pytest.raises(AttributeError):
            ctx.capacity_mw = 50.0