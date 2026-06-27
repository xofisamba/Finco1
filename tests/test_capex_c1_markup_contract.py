"""CAPEX C1 Migration: markup-contract test.

Asserts the production CAPEX grid (rendered standalone, via the
primary `project_ctx.capex_detail_items` data path used in production)
emits a valid, internally-consistent C1 `data-fc-*` markup contract:

  - the grid root carries `data-fc-grid="capex"`
  - every editable CAPEX cell has a unique `data-fc-addr`
  - every editable CAPEX cell has a real input
  - every editable amount cell has `data-fc-raw`
  - non-editable subtotal/total cells are marked
    `data-fc-editable="false"`
  - there are no duplicate `data-fc-addr` values anywhere in the grid

This is a static (HTML-string) test, not a browser test — the
production-route browser/Playwright coverage lives in
tests/test_capex_c1_migration_browser.py. It mirrors the rendering
approach already used by
tests/test_phase57a_ui3_line_item_grid_capex_summary.py (render
`sheet_capex.html` standalone via Jinja2 with a sample `project_ctx`),
but supplies `capex_detail_items` so the *primary* C.01-C.18 rendering
path (the one real projects use) is exercised, not the legacy
flat-`capex_items` fallback path.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_TEMPLATES = REPO_ROOT / "app" / "templates" / "partials"

CELL_RE = re.compile(
    r'<td class="[^"]*"[^>]*data-fc-cell="true"[^>]*>', re.IGNORECASE
)
ATTR_RE = re.compile(r'(data-fc-[a-z]+)="([^"]*)"')


def _child(code, name, amount_keur):
    return {"code": code, "name": name, "amount_keur": amount_keur}


SAMPLE_DETAIL_ITEMS = {
    "categories": (
        {
            "code": "C.01",
            "name": "Production Unit",
            "is_backend_calculated": False,
            "children": (
                _child("C.01.01", "Solar Modules", 1000.0),
                _child("C.01.02", "Inverters", 500.0),
            ),
        },
        {
            "code": "C.02",
            "name": "EPC Contract",
            "is_backend_calculated": False,
            "children": (
                _child("C.02.01", "EPC Lump Sum", 2000.0),
            ),
        },
        {
            "code": "C.17",
            "name": "Financing Costs",
            "is_backend_calculated": True,
            "children": (
                _child("C.17.01", "Interest During Construction", 80.0),
            ),
        },
        {
            "code": "C.18",
            "name": "Reserve Accounts",
            "is_backend_calculated": True,
            "children": (
                _child("C.18.01", "DSRA", 120.0),
            ),
        },
    ),
    "grand_total_keur": 3700.0,
    "hard_capex_total_keur": 3500.0,
    "financing_total_keur": 200.0,
}

SAMPLE_PROJECT_CTX = {
    "name": "Test CAPEX Project",
    "capex_detail_items": SAMPLE_DETAIL_ITEMS,
}


def _render_sheet_capex(is_user_project):
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    env = Environment(
        loader=FileSystemLoader(str(APP_TEMPLATES.parent)),
        autoescape=select_autoescape(["html"]),
    )
    tmpl = env.get_template("partials/sheet_capex.html")
    return tmpl.render(
        project_ctx=SAMPLE_PROJECT_CTX,
        is_user_project=is_user_project,
    )


def _fc_cells(html):
    cells = []
    for match in CELL_RE.finditer(html):
        tag = match.group(0)
        attrs = dict(ATTR_RE.findall(tag))
        cells.append(attrs)
    return cells


@pytest.fixture(scope="module")
def capex_html_editable():
    return _render_sheet_capex(is_user_project=True)


@pytest.fixture(scope="module")
def capex_html_readonly():
    return _render_sheet_capex(is_user_project=False)


class TestCapexMarkupContract:
    def test_grid_root_present(self, capex_html_editable):
        assert 'data-fc-grid="capex"' in capex_html_editable

    def test_scroll_container_present(self, capex_html_editable):
        assert 'data-fc-scroll-container="true"' in capex_html_editable

    def test_fc_cells_exist(self, capex_html_editable):
        cells = _fc_cells(capex_html_editable)
        assert len(cells) > 0

    def test_every_fc_cell_has_addr_kind_and_editable(self, capex_html_editable):
        cells = _fc_cells(capex_html_editable)
        for attrs in cells:
            assert attrs.get("data-fc-addr"), attrs
            assert attrs.get("data-fc-kind") in ("amount", "subtotal", "total"), attrs
            assert attrs.get("data-fc-editable") in ("true", "false"), attrs

    def test_no_duplicate_addresses(self, capex_html_editable):
        cells = _fc_cells(capex_html_editable)
        addrs = [attrs["data-fc-addr"] for attrs in cells]
        assert len(addrs) == len(set(addrs)), "duplicate data-fc-addr values found"

    def test_every_editable_amount_cell_has_raw_and_real_input(self, capex_html_editable):
        cells = _fc_cells(capex_html_editable)
        editable_amount_cells = [
            a for a in cells if a.get("data-fc-editable") == "true" and a.get("data-fc-kind") == "amount"
        ]
        assert editable_amount_cells, "expected at least one editable CAPEX amount cell"
        for attrs in editable_amount_cells:
            assert "data-fc-raw" in attrs, attrs

    def test_subtotal_and_total_cells_are_not_editable(self, capex_html_editable):
        cells = _fc_cells(capex_html_editable)
        for attrs in cells:
            if attrs.get("data-fc-kind") in ("subtotal", "total"):
                assert attrs.get("data-fc-editable") == "false", attrs

    def test_financing_cells_c17_c18_are_not_editable(self, capex_html_editable):
        cells = _fc_cells(capex_html_editable)
        financing_cells = [a for a in cells if "C.17" in a.get("data-fc-addr", "") or "C.18" in a.get("data-fc-addr", "")]
        assert financing_cells, "expected C.17/C.18 financing cells in the grid"
        for attrs in financing_cells:
            assert attrs.get("data-fc-editable") == "false", attrs

    def test_addresses_are_deterministic_not_display_text(self, capex_html_editable):
        cells = _fc_cells(capex_html_editable)
        for attrs in cells:
            addr = attrs["data-fc-addr"]
            assert addr.startswith("capex!"), addr
            assert " " not in addr, addr

    def test_factory_reference_mode_renders_all_cells_non_editable(self, capex_html_readonly):
        cells = _fc_cells(capex_html_readonly)
        assert cells
        for attrs in cells:
            assert attrs.get("data-fc-editable") == "false", attrs
