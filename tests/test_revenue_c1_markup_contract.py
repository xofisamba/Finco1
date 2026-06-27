"""Revenue C1 Migration: markup-contract test.

Asserts the production Revenue sheet (`sheet_revenue.html`, rendered
standalone via a sample `project_ctx`) emits a valid,
internally-consistent C1 `data-fc-*` markup contract:

  - the grid root carries `data-fc-grid="revenue"`
  - the wrapper carries `data-fc-scroll-container="true"`
  - every addressable Revenue cell has a unique `data-fc-addr`
  - every addressable cell has `data-fc-kind` and `data-fc-editable`
  - editable cells match the existing has-a-real-`<input>` convention
  - `co2_enabled` is always non-editable (no <input> ever renders for it)
  - addresses are deterministic, derived from stable `item.code` /
    summary keys, never display text

This is a static (HTML-string) test, mirroring
tests/test_inputs_c1_markup_contract.py,
tests/test_capex_c1_markup_contract.py, and
tests/test_opex_c1_markup_contract.py. Production-route browser
coverage lives in tests/test_revenue_c1_migration_browser.py.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_TEMPLATES = REPO_ROOT / "app" / "templates"

CELL_RE = re.compile(r'<td[^>]*data-fc-cell="true"[^>]*>', re.IGNORECASE)
ATTR_RE = re.compile(r'(data-fc-[a-z]+)="([^"]*)"')
HAS_INPUT_RE = re.compile(r'<input\b')


class _Ctx(dict):
    def __getattr__(self, key):
        return self.get(key)


REVENUE_ITEMS = (
    {"code": "capacity_mw", "name": "Installed Capacity", "value": 50.0,
     "unit": "MW", "group": "Production", "editable": False, "hint": "Set via inputs tab"},
    {"code": "operating_hours_p50", "name": "P50 Hours / Year", "value": 1400,
     "unit": "h/yr", "group": "Production", "editable": False, "hint": "Set via inputs tab"},
    {"code": "plant_availability", "name": "Plant Availability", "value": 0.98,
     "unit": "%", "group": "Production", "editable": False, "hint": "Set via inputs tab"},
    {"code": "grid_availability", "name": "Grid Availability", "value": 0.99,
     "unit": "%", "group": "Production", "editable": False, "hint": "Set via inputs tab"},
    {"code": "pv_degradation", "name": "PV Degradation", "value": 0.005,
     "unit": "%/yr", "group": "Production", "editable": False, "hint": "Set via inputs tab"},
    {"code": "ppa_base_tariff", "name": "Base Tariff (PPA)", "value": 60.0,
     "unit": "EUR/MWh", "group": "PPA / Tariff", "editable": True, "hint": ""},
    {"code": "ppa_index", "name": "Tariff Escalation", "value": 0.02,
     "unit": "%/yr", "group": "PPA / Tariff", "editable": False, "hint": "Set via inputs tab"},
    {"code": "ppa_term_years", "name": "PPA Term", "value": 15,
     "unit": "years", "group": "PPA / Tariff", "editable": False, "hint": "Set via inputs tab"},
    {"code": "ppa_production_share", "name": "PPA Production Share", "value": 1.0,
     "unit": "%", "group": "PPA / Tariff", "editable": False, "hint": "Set via inputs tab"},
    {"code": "balancing_cost", "name": "Balancing Cost", "value": 0.0,
     "unit": "EUR/MWh", "group": "Market / Merchant", "editable": False, "hint": "Set via inputs tab"},
    {"code": "first_merchant_period", "name": "First Merchant Period", "value": -1,
     "unit": "period index", "group": "Market / Merchant", "editable": False, "hint": "Set via inputs tab"},
    {"code": "co2_enabled", "name": "CO2 Certificates Enabled", "value": 0.0,
     "unit": "flag", "group": "CO2 / Certificates", "editable": False, "hint": "Set via inputs tab"},
    {"code": "co2_price", "name": "CO2 Price (Y1)", "value": 0.0,
     "unit": "EUR/MWh", "group": "CO2 / Certificates", "editable": False, "hint": "Set via inputs tab"},
)


SAMPLE_PROJECT_CTX = _Ctx(
    name="Test Revenue Project",
    revenue_items=REVENUE_ITEMS,
    ppa_tariff_eur_mwh=60.0,
    ppa_index_pct=0.02,
    ppa_term_years=15,
    co2_enabled=False,
    co2_price_eur_mwh=0.0,
    operating_hours_p50=1400,
    capacity_mw=50.0,
    plant_availability=0.98,
)


def _render_sheet_revenue(is_user_project):
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    env = Environment(
        loader=FileSystemLoader(str(APP_TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )
    tmpl = env.get_template("partials/sheet_revenue.html")
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


def _fc_cells_with_html(html):
    cells_with_html = []
    for match in CELL_RE.finditer(html):
        start = match.end()
        end = html.find("</td>", start)
        inner = html[start:end]
        attrs = dict(ATTR_RE.findall(match.group(0)))
        cells_with_html.append((attrs, inner))
    return cells_with_html


@pytest.fixture(scope="module")
def revenue_html_user_project():
    return _render_sheet_revenue(is_user_project=True)


@pytest.fixture(scope="module")
def revenue_html_readonly():
    return _render_sheet_revenue(is_user_project=False)


class TestRevenueMarkupContract:
    def test_grid_root_present(self, revenue_html_user_project):
        assert 'data-fc-grid="revenue"' in revenue_html_user_project

    def test_scroll_container_present(self, revenue_html_user_project):
        assert 'data-fc-scroll-container="true"' in revenue_html_user_project

    def test_fc_cells_exist(self, revenue_html_user_project):
        cells = _fc_cells(revenue_html_user_project)
        assert len(cells) > 0

    def test_every_fc_cell_has_addr_kind_and_editable(self, revenue_html_user_project):
        cells = _fc_cells(revenue_html_user_project)
        for attrs in cells:
            assert attrs.get("data-fc-addr"), attrs
            assert attrs.get("data-fc-kind") == "text", attrs
            assert attrs.get("data-fc-editable") in ("true", "false"), attrs

    def test_no_duplicate_addresses(self, revenue_html_user_project):
        cells = _fc_cells(revenue_html_user_project)
        addrs = [attrs["data-fc-addr"] for attrs in cells]
        assert len(addrs) == len(set(addrs)), "duplicate data-fc-addr values found"

    def test_addresses_are_deterministic_not_display_text(self, revenue_html_user_project):
        cells = _fc_cells(revenue_html_user_project)
        for attrs in cells:
            addr = attrs["data-fc-addr"]
            assert addr.startswith("revenue!"), addr
            assert " " not in addr, addr

    def test_known_address_examples_present(self, revenue_html_user_project):
        cells = _fc_cells(revenue_html_user_project)
        addrs = {attrs["data-fc-addr"] for attrs in cells}
        for expected in (
            "revenue!capacity_mw",
            "revenue!ppa_base_tariff",
            "revenue!balancing_cost",
            "revenue!co2_enabled",
            "revenue!co2_price",
            "revenue!summary.tariff_y1",
            "revenue!summary.ppa_revenue_y1",
            "revenue!summary.total_revenue_y1",
        ):
            assert expected in addrs, f"{expected} missing from {sorted(addrs)}"

    def test_editable_cells_match_existing_convention(self, revenue_html_user_project):
        """A cell is data-fc-editable="true" iff it contains a real
        <input> (the pre-existing editable-vs-readonly convention)."""
        cells_with_html = _fc_cells_with_html(revenue_html_user_project)
        assert cells_with_html
        for attrs, inner in cells_with_html:
            has_input = bool(HAS_INPUT_RE.search(inner))
            editable = attrs.get("data-fc-editable") == "true"
            assert has_input == editable, (attrs, inner[:160])

    def test_co2_enabled_always_non_editable(self, revenue_html_user_project):
        cells = _fc_cells(revenue_html_user_project)
        addrs = {a["data-fc-addr"]: a for a in cells}
        assert addrs["revenue!co2_enabled"]["data-fc-editable"] == "false"

    def test_calculated_summary_cells_are_non_editable(self, revenue_html_user_project):
        cells = _fc_cells(revenue_html_user_project)
        addrs = {a["data-fc-addr"]: a for a in cells}
        for addr in (
            "revenue!summary.tariff_y1",
            "revenue!summary.ppa_revenue_y1",
            "revenue!summary.total_revenue_y1",
        ):
            assert addrs[addr]["data-fc-editable"] == "false", addr

    def test_deterministic_ordering_across_renders(self):
        html_a = _render_sheet_revenue(is_user_project=True)
        html_b = _render_sheet_revenue(is_user_project=True)
        addrs_a = [a["data-fc-addr"] for a in _fc_cells(html_a)]
        addrs_b = [a["data-fc-addr"] for a in _fc_cells(html_b)]
        assert addrs_a == addrs_b

    def test_readonly_mode_grid_root_present(self, revenue_html_readonly):
        assert 'data-fc-grid="revenue"' in revenue_html_readonly

    def test_readonly_mode_all_cells_non_editable(self, revenue_html_readonly):
        cells = _fc_cells(revenue_html_readonly)
        assert cells
        for attrs in cells:
            assert attrs.get("data-fc-editable") == "false", attrs
