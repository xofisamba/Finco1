"""
Tests for Inputs Control Tower — capex_vm / opex_vm integration in inputs_section.html.

PR E scope: verifies that inputs_section.html uses capex_vm and opex_vm to render
richer CAPEX/OPEX summary rows when those view models are present in context.
Does NOT start a server — renders the template directly via Jinja2.
"""

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.ui.project_context import get_project_context
from app.ui.capex_view_model import build_capex_view_model
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
def inputs_template(jinja_env):
    return jinja_env.get_template("partials/inputs_section.html")


@pytest.fixture(scope="module")
def tuho_ctx():
    return get_project_context("tuho")


@pytest.fixture(scope="module")
def oborovo_ctx():
    return get_project_context("oborovo")


def _render(template, ctx, is_user_project=False, capex_vm=None, opex_vm=None):
    return template.render(
        project_ctx=ctx,
        is_user_project=is_user_project,
        capex_vm=capex_vm,
        opex_vm=opex_vm,
        is_exploratory_project=False,
        audit_mode=False,
    )


@pytest.fixture(scope="module")
def tuho_capex_vm(tuho_ctx):
    return build_capex_view_model(tuho_ctx, is_user_project=False)


@pytest.fixture(scope="module")
def tuho_opex_vm(tuho_ctx):
    return build_opex_view_model(tuho_ctx, is_user_project=False)


@pytest.fixture(scope="module")
def html_with_vms(inputs_template, tuho_ctx, tuho_capex_vm, tuho_opex_vm):
    return _render(inputs_template, tuho_ctx,
                   capex_vm=tuho_capex_vm, opex_vm=tuho_opex_vm)


@pytest.fixture(scope="module")
def html_without_vms(inputs_template, tuho_ctx):
    return _render(inputs_template, tuho_ctx, capex_vm=None, opex_vm=None)


@pytest.fixture(scope="module")
def html_user(inputs_template, tuho_ctx, tuho_capex_vm, tuho_opex_vm):
    return _render(inputs_template, tuho_ctx, is_user_project=True,
                   capex_vm=tuho_capex_vm, opex_vm=tuho_opex_vm)


@pytest.fixture(scope="module")
def html_oborovo(inputs_template, oborovo_ctx):
    ovm = build_opex_view_model(oborovo_ctx, is_user_project=False)
    cvm = build_capex_view_model(oborovo_ctx, is_user_project=False)
    return _render(inputs_template, oborovo_ctx, capex_vm=cvm, opex_vm=ovm)


# ---------------------------------------------------------------------------
# Structural / baseline
# ---------------------------------------------------------------------------

class TestBaselineRenders:
    def test_renders_without_error_with_vms(self, html_with_vms):
        assert len(html_with_vms) > 0

    def test_renders_without_error_without_vms(self, html_without_vms):
        assert len(html_without_vms) > 0

    def test_identity_section_present(self, html_with_vms):
        assert "Identity" in html_with_vms

    def test_schedule_section_present(self, html_with_vms):
        assert "Schedule" in html_with_vms

    def test_technical_section_present(self, html_with_vms):
        assert "Technical" in html_with_vms

    def test_revenue_section_present(self, html_with_vms):
        assert "Revenue" in html_with_vms

    def test_debt_section_present(self, html_with_vms):
        assert "Debt" in html_with_vms

    def test_tax_section_present(self, html_with_vms):
        assert "Tax" in html_with_vms


# ---------------------------------------------------------------------------
# CAPEX Summary — with capex_vm
# ---------------------------------------------------------------------------

class TestCapexSummaryWithVM:
    def test_hard_capex_row_present(self, html_with_vms):
        assert "Hard CAPEX" in html_with_vms

    def test_hard_capex_c01_c16_label(self, html_with_vms):
        assert "C.01" in html_with_vms

    def test_total_capex_row_present(self, html_with_vms):
        assert "Total CAPEX" in html_with_vms

    def test_capex_per_mw_row_present(self, html_with_vms):
        assert "CAPEX / MW" in html_with_vms

    def test_financing_costs_row_present_when_nonzero(self, html_with_vms):
        # TUHO has C.17 financing costs > 0
        assert "Financing Costs" in html_with_vms

    def test_capex_detail_note_references_capex_tab(self, html_with_vms):
        assert "CAPEX tab" in html_with_vms

    def test_capex_section_note_mentions_c01_c18(self, html_with_vms):
        assert "C.01" in html_with_vms and "C.18" in html_with_vms


# ---------------------------------------------------------------------------
# CAPEX Summary — without capex_vm (fallback)
# ---------------------------------------------------------------------------

class TestCapexSummaryFallback:
    def test_total_capex_still_shown_without_vm(self, html_without_vms):
        assert "Total CAPEX" in html_without_vms

    def test_hard_capex_not_shown_without_vm(self, html_without_vms):
        assert "Hard CAPEX" not in html_without_vms

    def test_capex_per_mw_not_shown_without_vm(self, html_without_vms):
        assert "CAPEX / MW" not in html_without_vms


# ---------------------------------------------------------------------------
# OPEX Summary — with opex_vm
# ---------------------------------------------------------------------------

class TestOpexSummaryWithVM:
    def test_total_opex_y1_row_present(self, html_with_vms):
        assert "Total OPEX Y1" in html_with_vms

    def test_contingency_rate_row_present(self, html_with_vms):
        assert "Contingency Rate" in html_with_vms

    def test_contingency_y1_row_present(self, html_with_vms):
        assert "Contingency Y1" in html_with_vms

    def test_opex_per_mw_row_present(self, html_with_vms):
        assert "OPEX / MW" in html_with_vms

    def test_opex_per_mwh_row_present(self, html_with_vms):
        assert "OPEX / MWh" in html_with_vms

    def test_opex_detail_note_references_opex_tab(self, html_with_vms):
        assert "OPEX tab" in html_with_vms

    def test_opex_section_note_mentions_b01_b13(self, html_with_vms):
        assert "B.01" in html_with_vms and "B.13" in html_with_vms


# ---------------------------------------------------------------------------
# OPEX Summary — without opex_vm (fallback)
# ---------------------------------------------------------------------------

class TestOpexSummaryFallback:
    def test_opex_total_still_shown_without_vm(self, html_without_vms):
        assert "OPEX" in html_without_vms

    def test_opex_per_mw_not_shown_without_vm(self, html_without_vms):
        assert "OPEX / MW" not in html_without_vms

    def test_contingency_y1_not_shown_without_vm(self, html_without_vms):
        assert "Contingency Y1" not in html_without_vms


# ---------------------------------------------------------------------------
# Editability in user project
# ---------------------------------------------------------------------------

class TestEditabilityUserProject:
    def test_total_capex_editable_in_user_project(self, html_user):
        # Total CAPEX input should be present
        assert 'name="total_capex_keur"' in html_user

    def test_opex_y1_editable_in_user_project(self, html_user):
        assert 'name="opex_y1_keur"' in html_user

    def test_hard_capex_not_editable(self, html_user):
        # Hard CAPEX is always calculated — no editable input for it
        assert 'name="hard_capex' not in html_user

    def test_no_readonly_notice_for_user_project(self, html_user):
        assert "Protected original" not in html_user


# ---------------------------------------------------------------------------
# Protected project
# ---------------------------------------------------------------------------

class TestProtectedProject:
    def test_readonly_notice_present(self, html_with_vms):
        assert "Protected original" in html_with_vms

    def test_no_editable_total_capex_input_in_protected(self, html_with_vms):
        # Protected projects should NOT have an editable <input> for Total CAPEX.
        # The field_name appears in data-field-name/data-fc-addr attrs but NOT in
        # an <input name="..."> element when is_user_project=False.
        assert 'type="number" name="total_capex_keur"' not in html_with_vms and \
               'type="text" name="total_capex_keur"' not in html_with_vms

    def test_no_editable_opex_input_in_protected(self, html_with_vms):
        assert 'name="opex_y1_keur"' not in html_with_vms


# ---------------------------------------------------------------------------
# Oborovo renders
# ---------------------------------------------------------------------------

class TestOborovoRenders:
    def test_oborovo_renders_without_error(self, html_oborovo):
        assert len(html_oborovo) > 0

    def test_oborovo_has_capex_summary(self, html_oborovo):
        assert "Hard CAPEX" in html_oborovo

    def test_oborovo_has_opex_summary(self, html_oborovo):
        assert "Total OPEX Y1" in html_oborovo

    def test_oborovo_total_capex_present(self, html_oborovo):
        assert "Total CAPEX" in html_oborovo
