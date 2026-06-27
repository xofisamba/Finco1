"""OPEX C1 Migration: markup-contract test.

Asserts the production OPEX detail grid (`sheet_opex_detail.html`,
rendered standalone via the real `project_ctx.opex_detail_items` data
path) emits a valid, internally-consistent C1 `data-fc-*` markup
contract:

  - the grid root carries `data-fc-grid="opex"`
  - the scroll wrapper carries `data-fc-scroll-container="true"`
  - every addressable OPEX cell has a unique `data-fc-addr`
  - every addressable cell has `data-fc-kind` and `data-fc-editable`
  - amount/subtotal cells carry `data-fc-raw`
  - addresses are deterministic, derived from `cat.code`/`child.code`,
    never from display text
  - ALL cells are `data-fc-editable="false"` — the real production
    OPEX grid has zero real `<input>` elements today (every cell is a
    read-only `<span title="Line editing deferred">`, in both the
    is_user_project=True and False branches), so this migration adds
    the C1 markup contract without adding new editability. See
    docs/OPEX_C1_MIGRATION_NOTE.md for the full rationale.

This is a static (HTML-string) test, mirroring
tests/test_capex_c1_markup_contract.py. Production-route browser
coverage lives in tests/test_opex_c1_migration_browser.py.
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


def _child(code, name, budget=10.0, inflation_pct=2.0, wht_rate=0.0, n_years=8):
    return {
        "code": code,
        "name": name,
        "budget_y1_keur": budget,
        "inflation_pct": inflation_pct,
        "wth_rate": wht_rate,
        "source": "factory",
        "notes": "",
        "yearly_values": [round(budget * (1 + inflation_pct / 100.0) ** y, 2) for y in range(n_years)],
        "active_flags": [1] * n_years,
    }


SAMPLE_OPEX_DETAIL_ITEMS = (
    {
        "code": "B.01",
        "name": "Technical Management",
        "inflation_pct": 2.0,
        "wth_rate": 0.0,
        "source": "factory",
        "is_contingency": False,
        "contingency_pct": 0.0,
        "children": (
            _child("B.01.01", "Asset Management Contract", budget=60.0),
            _child("B.01.02", "O&M Contract", budget=120.0),
        ),
        "yearly_totals": [180.0] * 8,
    },
    {
        "code": "B.04",
        "name": "Insurance",
        "inflation_pct": 1.5,
        "wth_rate": 0.0,
        "source": "factory",
        "is_contingency": False,
        "contingency_pct": 0.0,
        "children": (
            _child("B.04.01", "Property Insurance", budget=40.0),
        ),
        "yearly_totals": [40.0] * 8,
    },
    {
        "code": "B.13",
        "name": "Contingency",
        "inflation_pct": 0.0,
        "wth_rate": 0.0,
        "source": "factory",
        "is_contingency": True,
        "contingency_pct": 6.0,
        "children": (
            _child("B.13.01", "Contingency Reserve", budget=0.0),
        ),
        "yearly_totals": [13.2] * 8,
    },
)

SAMPLE_PROJECT_CTX = {
    "name": "Test OPEX Project",
    "opex_detail_items": SAMPLE_OPEX_DETAIL_ITEMS,
    "opex_items": (),
    "opex_y1_total_keur": 220.0,
    "opex_contingency_method": "percentage_of_opex",
    "opex_contingency_pct": 6.0,
    "horizon_years": 8,
}


def _render_sheet_opex_detail(is_user_project):
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    env = Environment(
        loader=FileSystemLoader(str(APP_TEMPLATES.parent)),
        autoescape=select_autoescape(["html"]),
    )
    tmpl = env.get_template("partials/sheet_opex_detail.html")
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
def opex_html_user_project():
    return _render_sheet_opex_detail(is_user_project=True)


@pytest.fixture(scope="module")
def opex_html_readonly():
    return _render_sheet_opex_detail(is_user_project=False)


class TestOpexMarkupContract:
    def test_grid_root_present(self, opex_html_user_project):
        assert 'data-fc-grid="opex"' in opex_html_user_project

    def test_scroll_container_present(self, opex_html_user_project):
        assert 'data-fc-scroll-container="true"' in opex_html_user_project

    def test_fc_cells_exist(self, opex_html_user_project):
        cells = _fc_cells(opex_html_user_project)
        assert len(cells) > 0

    def test_every_fc_cell_has_addr_kind_and_editable(self, opex_html_user_project):
        cells = _fc_cells(opex_html_user_project)
        for attrs in cells:
            assert attrs.get("data-fc-addr"), attrs
            assert attrs.get("data-fc-kind") in ("amount", "subtotal"), attrs
            assert attrs.get("data-fc-editable") in ("true", "false"), attrs

    def test_no_duplicate_addresses(self, opex_html_user_project):
        cells = _fc_cells(opex_html_user_project)
        addrs = [attrs["data-fc-addr"] for attrs in cells]
        assert len(addrs) == len(set(addrs)), "duplicate data-fc-addr values found"

    def test_amount_and_subtotal_cells_have_raw(self, opex_html_user_project):
        cells = _fc_cells(opex_html_user_project)
        assert cells
        for attrs in cells:
            assert "data-fc-raw" in attrs, attrs

    def test_all_cells_are_non_editable(self, opex_html_user_project):
        """Real production OPEX cells have zero <input> elements today
        (line editing is explicitly deferred) — the migration must not
        introduce new editability, only the C1 markup contract."""
        cells = _fc_cells(opex_html_user_project)
        assert cells
        for attrs in cells:
            assert attrs.get("data-fc-editable") == "false", attrs

    def test_addresses_are_deterministic_not_display_text(self, opex_html_user_project):
        cells = _fc_cells(opex_html_user_project)
        for attrs in cells:
            addr = attrs["data-fc-addr"]
            assert addr.startswith("opex!"), addr
            assert " " not in addr, addr
            assert "Insurance" not in addr
            assert "Technical Management" not in addr

    def test_category_subtotal_addresses_use_cat_code(self, opex_html_user_project):
        cells = _fc_cells(opex_html_user_project)
        subtotal_addrs = [a["data-fc-addr"] for a in cells if a.get("data-fc-kind") == "subtotal"]
        assert subtotal_addrs
        assert any(addr.startswith("opex!B.01.") for addr in subtotal_addrs)
        assert any(addr.startswith("opex!B.04.") for addr in subtotal_addrs)
        assert all(addr.endswith(".subtotal") for addr in subtotal_addrs)

    def test_child_amount_addresses_use_child_code(self, opex_html_user_project):
        cells = _fc_cells(opex_html_user_project)
        addrs = [a["data-fc-addr"] for a in cells if a.get("data-fc-kind") == "amount"]
        assert any(addr.startswith("opex!B.01.01.") for addr in addrs)
        assert any(addr == "opex!B.01.01.budget" for addr in addrs)
        assert any(addr == "opex!B.01.01.Y1" for addr in addrs)

    def test_deterministic_ordering_across_renders(self):
        html_a = _render_sheet_opex_detail(is_user_project=True)
        html_b = _render_sheet_opex_detail(is_user_project=True)
        addrs_a = [a["data-fc-addr"] for a in _fc_cells(html_a)]
        addrs_b = [a["data-fc-addr"] for a in _fc_cells(html_b)]
        assert addrs_a == addrs_b

    def test_non_user_project_mode_renders_all_cells_non_editable(self, opex_html_readonly):
        cells = _fc_cells(opex_html_readonly)
        assert cells
        for attrs in cells:
            assert attrs.get("data-fc-editable") == "false", attrs
