"""
Tests for sheet_opex_grid.html template rendering.

Verifies structural correctness, group/line presence, editability
rendering, sticky column markup, total rows, KPI strip, and year columns.
Does NOT start a server — renders the template directly via Jinja2.
"""

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.ui.project_context import get_project_context
from app.ui.opex_view_model import build_opex_view_model


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def jinja_env():
    return Environment(
        loader=FileSystemLoader("app/templates"),
        autoescape=select_autoescape(["html"]),
    )


@pytest.fixture(scope="module")
def opex_template(jinja_env):
    return jinja_env.get_template("partials/sheet_opex_grid.html")


@pytest.fixture(scope="module")
def tuho_ctx():
    return get_project_context("tuho")


@pytest.fixture(scope="module")
def oborovo_ctx():
    return get_project_context("oborovo")


@pytest.fixture(scope="module")
def html_protected(opex_template, tuho_ctx):
    vm = build_opex_view_model(tuho_ctx, is_user_project=False)
    return opex_template.render(opex_vm=vm, is_user_project=False)


@pytest.fixture(scope="module")
def html_user(opex_template, tuho_ctx):
    vm = build_opex_view_model(tuho_ctx, is_user_project=True)
    return opex_template.render(opex_vm=vm, is_user_project=True)


@pytest.fixture(scope="module")
def html_oborovo(opex_template, oborovo_ctx):
    vm = build_opex_view_model(oborovo_ctx, is_user_project=False)
    return opex_template.render(opex_vm=vm, is_user_project=False)


@pytest.fixture(scope="module")
def html_10yr(opex_template, tuho_ctx):
    vm = build_opex_view_model(tuho_ctx, is_user_project=False, display_years=10)
    return opex_template.render(opex_vm=vm, is_user_project=False)


# ---------------------------------------------------------------------------
# Structural markup
# ---------------------------------------------------------------------------

class TestStructuralMarkup:
    def test_renders_without_error(self, html_protected):
        assert len(html_protected) > 0

    def test_has_grid_wrapper(self, html_protected):
        assert "ox-grid-wrapper" in html_protected

    def test_has_ox_grid_table(self, html_protected):
        assert 'class="ox-grid"' in html_protected

    def test_has_sticky_col_class(self, html_protected):
        assert "ox-sticky-col" in html_protected

    def test_has_thead(self, html_protected):
        assert "<thead>" in html_protected

    def test_has_tbody(self, html_protected):
        assert "<tbody>" in html_protected

    def test_has_code_column_header(self, html_protected):
        assert ">Code<" in html_protected

    def test_has_line_item_column_header(self, html_protected):
        assert ">Line Item<" in html_protected

    def test_has_budget_column_header(self, html_protected):
        assert "Budget kEUR" in html_protected

    def test_has_infl_column_header(self, html_protected):
        assert "Infl %" in html_protected

    def test_has_wht_column_header(self, html_protected):
        assert ">WHT<" in html_protected

    def test_has_y1_column_header(self, html_protected):
        assert ">Y1<" in html_protected


# ---------------------------------------------------------------------------
# Group codes presence
# ---------------------------------------------------------------------------

class TestGroupCodes:
    def test_b01_present(self, html_protected):
        assert "B.01" in html_protected

    def test_b07_present(self, html_protected):
        assert "B.07" in html_protected

    def test_b13_present(self, html_protected):
        assert "B.13" in html_protected

    def test_all_13_groups_present(self, html_protected):
        for i in range(1, 14):
            code = f"B.{i:02d}"
            assert code in html_protected or f"B.{i}" in html_protected, f"{code} missing"


# ---------------------------------------------------------------------------
# Year columns
# ---------------------------------------------------------------------------

class TestYearColumns:
    def test_y2_header_present_default_30yr(self, html_protected):
        assert ">Y2<" in html_protected

    def test_y30_header_present_default_30yr(self, html_protected):
        assert ">Y30<" in html_protected

    def test_y31_not_present_default_30yr(self, html_protected):
        assert ">Y31<" not in html_protected

    def test_10yr_has_y10(self, html_10yr):
        assert ">Y10<" in html_10yr

    def test_10yr_no_y11(self, html_10yr):
        assert ">Y11<" not in html_10yr

    def test_derived_year_header_class(self, html_protected):
        assert "ox-col-year--derived" in html_protected


# ---------------------------------------------------------------------------
# Readonly vs editable rendering
# ---------------------------------------------------------------------------

class TestEditabilityRendering:
    def test_protected_has_readonly_notice(self, html_protected):
        assert "Protected original" in html_protected

    def test_protected_no_editable_inputs(self, html_protected):
        assert 'type="number"' not in html_protected

    def test_user_project_no_readonly_notice(self, html_user):
        assert "Protected original" not in html_user

    def test_user_project_has_number_inputs(self, html_user):
        assert 'type="number"' in html_user

    def test_user_project_input_name_prefix(self, html_user):
        assert 'name="opex_' in html_user

    def test_user_project_ox_input_class(self, html_user):
        assert "ox-input" in html_user

    def test_b13_lines_have_no_input_in_user_project(self, html_user):
        # B.13 is derived — even in user project, no editable input
        assert "ox-value--derived" in html_user


# ---------------------------------------------------------------------------
# Total rows
# ---------------------------------------------------------------------------

class TestTotalRows:
    def test_total_excl_contingency_row(self, html_protected):
        assert "Total OPEX excl. Contingency" in html_protected

    def test_contingency_row_present(self, html_protected):
        assert "Contingency" in html_protected

    def test_grand_total_class_present(self, html_protected):
        assert "ox-total-row--grand" in html_protected

    def test_total_opex_grand_label(self, html_protected):
        assert "Total OPEX" in html_protected

    def test_ox_amount_total_grand_class(self, html_protected):
        assert "ox-amount-total--grand" in html_protected


# ---------------------------------------------------------------------------
# KPI strip
# ---------------------------------------------------------------------------

class TestKPIStrip:
    def test_kpi_strip_present(self, html_protected):
        assert "ox-kpi-strip" in html_protected

    def test_total_opex_y1_kpi(self, html_protected):
        assert "Total OPEX Y1" in html_protected

    def test_final_year_kpi(self, html_protected):
        assert "Year 30 Total" in html_protected

    def test_opex_per_mw_kpi(self, html_protected):
        assert "OPEX / MW" in html_protected

    def test_contingency_rate_kpi(self, html_protected):
        assert "Contingency" in html_protected


# ---------------------------------------------------------------------------
# Oborovo renders correctly
# ---------------------------------------------------------------------------

class TestOborovoRenders:
    def test_oborovo_renders(self, html_oborovo):
        assert len(html_oborovo) > 0

    def test_oborovo_has_b01(self, html_oborovo):
        assert "B.01" in html_oborovo

    def test_oborovo_has_b13(self, html_oborovo):
        assert "B.13" in html_oborovo

    def test_oborovo_total_opex_present(self, html_oborovo):
        assert "Total OPEX" in html_oborovo


# ---------------------------------------------------------------------------
# Fallback — no opex_vm
# ---------------------------------------------------------------------------

class TestFallback:
    def test_no_opex_vm_renders_fallback(self, opex_template):
        html = opex_template.render(opex_vm=None, is_user_project=False)
        assert "unavailable" in html.lower() or "ox-unavailable" in html
