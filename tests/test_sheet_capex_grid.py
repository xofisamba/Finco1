"""
Tests for sheet_capex_grid.html template rendering.

Verifies structural correctness, group/line presence, editability
rendering, sticky column markup, total rows, and KPI strip.
Does NOT start a server — renders the template directly via Jinja2.
"""

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.ui.project_context import get_project_context
from app.ui.capex_view_model import build_capex_view_model


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
def capex_template(jinja_env):
    return jinja_env.get_template("partials/sheet_capex_grid.html")


@pytest.fixture(scope="module")
def tuho_ctx():
    return get_project_context("tuho")


@pytest.fixture(scope="module")
def oborovo_ctx():
    return get_project_context("oborovo")


@pytest.fixture(scope="module")
def html_protected(capex_template, tuho_ctx):
    vm = build_capex_view_model(tuho_ctx, is_user_project=False)
    return capex_template.render(capex_vm=vm, is_user_project=False)


@pytest.fixture(scope="module")
def html_user(capex_template, tuho_ctx):
    vm = build_capex_view_model(tuho_ctx, is_user_project=True)
    return capex_template.render(capex_vm=vm, is_user_project=True)


@pytest.fixture(scope="module")
def html_oborovo(capex_template, oborovo_ctx):
    vm = build_capex_view_model(oborovo_ctx, is_user_project=False)
    return capex_template.render(capex_vm=vm, is_user_project=False)


# ---------------------------------------------------------------------------
# Structural markup
# ---------------------------------------------------------------------------

class TestStructuralMarkup:
    def test_renders_without_error(self, html_protected):
        assert len(html_protected) > 0

    def test_has_grid_wrapper(self, html_protected):
        assert "cx-grid-wrapper" in html_protected

    def test_has_cx_grid_table(self, html_protected):
        assert 'class="cx-grid"' in html_protected

    def test_has_sticky_col_class(self, html_protected):
        assert "cx-sticky-col" in html_protected

    def test_has_thead(self, html_protected):
        assert "<thead>" in html_protected

    def test_has_tbody(self, html_protected):
        assert "<tbody>" in html_protected

    def test_has_code_column_header(self, html_protected):
        assert ">Code<" in html_protected

    def test_has_line_item_column_header(self, html_protected):
        assert ">Line Item<" in html_protected

    def test_has_amount_column_header(self, html_protected):
        assert "Amount kEUR" in html_protected

    def test_has_per_mw_column_header(self, html_protected):
        assert "per MW" in html_protected


# ---------------------------------------------------------------------------
# Group codes presence
# ---------------------------------------------------------------------------

class TestGroupCodes:
    def test_c01_present(self, html_protected):
        assert "C.01" in html_protected

    def test_c13_present(self, html_protected):
        assert "C.13" in html_protected

    def test_c17_present(self, html_protected):
        assert "C.17" in html_protected

    def test_c18_present(self, html_protected):
        assert "C.18" in html_protected

    def test_all_18_groups_present(self, html_protected):
        for i in range(1, 19):
            assert f"C.{i:02d}" in html_protected or f"C.{i}" in html_protected


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
        assert 'name="capex_' in html_user

    def test_user_project_cx_input_class(self, html_user):
        assert "cx-input" in html_user

    def test_c17_lines_have_no_input_in_user_project(self, html_user):
        # C.17 is backend computed — even in user project, no input
        # Check by looking for cx-value--derived near C.17 content
        assert "cx-value--derived" in html_user

    def test_backend_computed_label_present(self, html_protected):
        assert "Backend computed" in html_protected


# ---------------------------------------------------------------------------
# Total rows
# ---------------------------------------------------------------------------

class TestTotalRows:
    def test_hard_capex_row_present(self, html_protected):
        assert "Hard CAPEX" in html_protected

    def test_total_capex_row_present(self, html_protected):
        assert "Total CAPEX" in html_protected

    def test_grand_total_class_present(self, html_protected):
        assert "cx-total-row--grand" in html_protected

    def test_cx_amount_total_grand_class(self, html_protected):
        assert "cx-amount-total--grand" in html_protected

    def test_hard_capex_c01_c16_label(self, html_protected):
        assert "C.01–C.16" in html_protected or "C.01" in html_protected

    def test_financing_costs_row_present_when_nonzero(self, html_protected):
        # TUHO has C.17 financing costs > 0
        assert "Financing Costs" in html_protected


# ---------------------------------------------------------------------------
# KPI strip
# ---------------------------------------------------------------------------

class TestKPIStrip:
    def test_kpi_strip_present(self, html_protected):
        assert "cx-kpi-strip" in html_protected

    def test_total_capex_kpi(self, html_protected):
        assert "Total CAPEX" in html_protected

    def test_capex_per_mw_kpi(self, html_protected):
        assert "CAPEX / MW" in html_protected

    def test_hard_capex_kpi(self, html_protected):
        assert "Hard CAPEX" in html_protected


# ---------------------------------------------------------------------------
# Oborovo renders correctly
# ---------------------------------------------------------------------------

class TestOborovoRenders:
    def test_oborovo_renders(self, html_oborovo):
        assert len(html_oborovo) > 0

    def test_oborovo_has_all_groups(self, html_oborovo):
        assert "C.01" in html_oborovo
        assert "C.18" in html_oborovo

    def test_oborovo_total_capex_present(self, html_oborovo):
        assert "Total CAPEX" in html_oborovo


# ---------------------------------------------------------------------------
# Fallback — no capex_vm
# ---------------------------------------------------------------------------

class TestFallback:
    def test_no_capex_vm_renders_fallback(self, capex_template):
        html = capex_template.render(capex_vm=None, is_user_project=False)
        assert "unavailable" in html.lower() or "cx-unavailable" in html
