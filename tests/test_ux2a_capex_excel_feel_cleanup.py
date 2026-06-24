"""UX-2A: CAPEX Excel-feel cleanup.

Pins the UI-placement requirements from the UX-2A task:

  A. Add Line actions live per-category (in each category's
     section band), not in a single top toolbar.
  B/D. The CAPEX column key / status legend / column groups /
     deferred-note / sources-and-uses governance copy is
     collapsed by default inside a "CAPEX Sheet Guide"
     <details> element.
  C. The CAPEX grid (lig_render output) renders before the
     guide / governance copy, not after it.

No runtime/formula/persistence/export logic is touched by
this phase; these tests are presentation-only.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_TEMPLATES = REPO_ROOT / "app" / "templates"
SHEET_CAPEX = APP_TEMPLATES / "partials" / "sheet_capex.html"


@pytest.fixture(scope="module")
def sheet_html_text() -> str:
    return SHEET_CAPEX.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def env():
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    return Environment(
        loader=FileSystemLoader(str(APP_TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )


def _build_production_ctx():
    import os
    import sys
    import tempfile

    for k in list(sys.modules):
        if k.startswith("app."):
            del sys.modules[k]

    os.environ.setdefault("FINCO_SECRET_KEY", "ux2a-test")
    os.environ.setdefault("FINCO_COOKIE_SECURE", "false")
    tmpdir = tempfile.mkdtemp(prefix="finco1-ux2a-")
    db_path = Path(tmpdir) / "finco1.db"
    os.environ["FINCO_DB_URL"] = f"sqlite:///{db_path}"

    from app.ui.project_context import _build_capex_detail_items
    from domain.inputs import CapexStructure, CapexItem

    capex = CapexStructure(
        production_units=CapexItem(name="Production Unit", amount_keur=0.0),
        epc_contract=CapexItem(name="EPC Contract", amount_keur=52800.0),
        epc_other=CapexItem(name="EPC Other", amount_keur=0.0),
        grid_connection=CapexItem(name="Grid Connection", amount_keur=0.0),
        project_rights=CapexItem(name="Project Rights", amount_keur=0.0),
        project_acquisition=CapexItem(name="Project Acquisition", amount_keur=0.0),
        ops_prep=CapexItem(name="Operations Prep", amount_keur=0.0),
        construction_mgmt_a=CapexItem(name="Construction Mgmt A", amount_keur=0.0),
        construction_mgmt_b=CapexItem(name="Construction Mgmt B", amount_keur=0.0),
        commissioning=CapexItem(name="Commissioning", amount_keur=0.0),
        audit_legal=CapexItem(name="Audit & Legal", amount_keur=0.0),
        lease_tax=CapexItem(name="Lease & Tax", amount_keur=0.0),
        insurances=CapexItem(name="Insurances", amount_keur=0.0),
        contingencies=CapexItem(name="Contingencies", amount_keur=0.0),
        taxes=CapexItem(name="Import Taxes", amount_keur=0.0),
    )
    result = _build_capex_detail_items(capex, construction_months=18)
    return {
        "name": "TUHO Test",
        "data_source": "User Project",
        "capacity_mw": 50.0,
        "total_capex_keur": 52800.0,
        "capex_items": [],
        "capex_detail_items": result["categories"],
        "construction_months": 18,
        "grand_total_keur": result["grand_total_keur"],
        "hard_capex_total_keur": result["hard_capex_total_keur"],
        "financing_total_keur": result["financing_total_keur"],
    }


@pytest.fixture(scope="module")
def production_ctx():
    return _build_production_ctx()


@pytest.fixture(scope="module")
def rendered_html(env, production_ctx):
    tmpl = env.get_template("partials/sheet_capex.html")
    return tmpl.render(project_ctx=production_ctx, is_user_project=True)


class TestAddLineRelocatedPerCategory:
    def test_old_top_toolbar_removed(self, sheet_html_text):
        assert 'id="capex-add-line-toolbar"' not in sheet_html_text
        assert 'class="capex-add-line-toolbar"' not in sheet_html_text
        assert 'data-capex-add-line-copy="true"' not in sheet_html_text

    def test_add_line_buttons_render_inline_per_category(self, rendered_html):
        for n in range(1, 17):
            code = f"C.{n:02d}"
            assert f'data-capex-add-line-btn="{code}"' in rendered_html

    def test_financing_categories_have_no_add_line_button(self, rendered_html):
        assert 'data-capex-add-line-btn="C.17"' not in rendered_html
        assert 'data-capex-add-line-btn="C.18"' not in rendered_html


class TestCapexSheetGuideCollapsedByDefault:
    def test_guide_details_present(self, sheet_html_text):
        assert 'data-capex-sheet-guide="true"' in sheet_html_text

    def test_guide_defaults_collapsed(self, sheet_html_text):
        import re
        match = re.search(
            r"<details[^>]*data-capex-sheet-guide=\"true\"[^>]*>",
            sheet_html_text,
        )
        assert match is not None, "CAPEX Sheet Guide <details> tag not found"
        tag = match.group(0)
        assert "open" not in tag, (
            f"CAPEX Sheet Guide must default to collapsed (no 'open' "
            f"attribute), got: {tag!r}"
        )


class TestGridIsPrimaryFocus:
    def test_grid_renders_before_guide(self, sheet_html_text):
        grid_pos = sheet_html_text.find("lig_render(")
        guide_pos = sheet_html_text.find('data-capex-sheet-guide="true"')
        assert grid_pos != -1, "lig_render call not found"
        assert guide_pos != -1, "CAPEX Sheet Guide not found"
        assert grid_pos < guide_pos, (
            "The CAPEX grid must render before the explanatory Guide "
            "section so the working grid is the primary focus."
        )


class TestExistingFunctionalityUnaffected:
    def test_lig_wrapper_present(self, rendered_html):
        assert "lig-wrapper" in rendered_html
        assert "lig-capex-pilot" in rendered_html

    def test_subtotal_and_total_rows_present(self, rendered_html):
        assert "fc-subtotal-row" in rendered_html
        assert "fc-total-row" in rendered_html

    def test_amount_inputs_still_editable_for_user_project(self, rendered_html):
        assert 'class="lig-input fc-input-native"' in rendered_html
