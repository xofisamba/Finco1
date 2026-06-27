"""Inputs C1 Migration: markup-contract test.

Asserts the production Inputs sheet (`sheet_inputs.html` ->
`partials/inputs_section.html`, rendered standalone via a sample
`project_ctx`) emits a valid, internally-consistent C1 `data-fc-*`
markup contract:

  - the grid root carries `data-fc-grid="inputs"`
  - the wrapper carries `data-fc-scroll-container="true"`
  - every addressable Inputs cell has a unique `data-fc-addr`
  - every addressable cell has `data-fc-kind` and `data-fc-editable`
  - editable cells match the existing editable-vs-calculated
    convention already present in the template (no new editability
    introduced, no existing editability removed)
  - addresses are deterministic, derived from stable section/field
    keys, never display text

This is a static (HTML-string) test, mirroring
tests/test_capex_c1_markup_contract.py and
tests/test_opex_c1_markup_contract.py. Production-route browser
coverage lives in tests/test_inputs_c1_migration_browser.py.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_TEMPLATES = REPO_ROOT / "app" / "templates"

CELL_RE = re.compile(
    r'<span class="inp-cell"[^>]*data-fc-cell="true"[^>]*>', re.IGNORECASE
)
ATTR_RE = re.compile(r'(data-fc-[a-z]+)="([^"]*)"')
HAS_INPUT_RE = re.compile(r'<input\b')


class _Ctx(dict):
    def __getattr__(self, key):
        return self.get(key)


SAMPLE_PROJECT_CTX = _Ctx(
    name="Test Inputs Project",
    technology="Solar",
    country_iso="HR",
    capacity_mw=50.0,
    code="oborovo-001",
    template_source=None,
    financial_close="2026-01-01",
    cod_date="2027-01-01",
    construction_months=12,
    horizon_years=25,
    period_frequency="Quarterly",
    operating_hours_p50=1400,
    plant_availability=0.98,
    grid_availability=0.99,
    pv_degradation=0.005,
    ppa_tariff_eur_mwh=60.0,
    ppa_term_years=15,
    ppa_index_pct=0.02,
    co2_enabled=False,
    co2_price_eur_mwh=0.0,
    total_capex_keur=50000.0,
    senior_debt_keur=35000.0,
    idc_keur=500.0,
    bank_fees_keur=300.0,
    opex_y1_total_keur=1000.0,
    opex_contingency_pct=0.06,
    gearing_pct=0.70,
    target_dscr=1.30,
    interest_rate_pct=0.05,
    senior_tenor_years=15,
    shl_amount_keur=2000.0,
    cit_rate_pct=0.18,
    loss_carryforward_years=5,
    g20_status=None,
    r99_r102_status=None,
)


def _render_sheet_inputs(is_user_project, audit_mode=True):
    # NOTE: audit_mode=False hits a pre-existing (pre-C1, unrelated)
    # Jinja escaping bug in the `tax_rows_normal` list-literal branch
    # of inputs_section.html (confirmed present on unmodified `main`
    # via `git stash`) that double-escapes the rendered Markup list
    # items. Not touched by this migration; tests render with
    # audit_mode=True, the unaffected branch, to assert the C1
    # contract itself.
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    env = Environment(
        loader=FileSystemLoader(str(APP_TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )
    tmpl = env.get_template("partials/sheet_inputs.html")
    return tmpl.render(
        project_ctx=SAMPLE_PROJECT_CTX,
        is_user_project=is_user_project,
        audit_mode=audit_mode,
        is_exploratory_project=False,
    )


def _fc_cells(html):
    cells = []
    for match in CELL_RE.finditer(html):
        tag = match.group(0)
        attrs = dict(ATTR_RE.findall(tag))
        cells.append(attrs)
    return cells


@pytest.fixture(scope="module")
def inputs_html_user_project():
    return _render_sheet_inputs(is_user_project=True)


@pytest.fixture(scope="module")
def inputs_html_readonly():
    return _render_sheet_inputs(is_user_project=False)


class TestInputsMarkupContract:
    def test_grid_root_present(self, inputs_html_user_project):
        assert 'data-fc-grid="inputs"' in inputs_html_user_project

    def test_scroll_container_present(self, inputs_html_user_project):
        assert 'data-fc-scroll-container="true"' in inputs_html_user_project

    def test_fc_cells_exist(self, inputs_html_user_project):
        cells = _fc_cells(inputs_html_user_project)
        assert len(cells) > 0

    def test_every_fc_cell_has_addr_kind_and_editable(self, inputs_html_user_project):
        cells = _fc_cells(inputs_html_user_project)
        for attrs in cells:
            assert attrs.get("data-fc-addr"), attrs
            assert attrs.get("data-fc-kind") == "text", attrs
            assert attrs.get("data-fc-editable") in ("true", "false"), attrs

    def test_no_duplicate_addresses(self, inputs_html_user_project):
        cells = _fc_cells(inputs_html_user_project)
        addrs = [attrs["data-fc-addr"] for attrs in cells]
        assert len(addrs) == len(set(addrs)), "duplicate data-fc-addr values found"

    def test_addresses_are_deterministic_not_display_text(self, inputs_html_user_project):
        cells = _fc_cells(inputs_html_user_project)
        for attrs in cells:
            addr = attrs["data-fc-addr"]
            assert addr.startswith("inputs!"), addr
            assert " " not in addr, addr

    def test_known_address_examples_present(self, inputs_html_user_project):
        cells = _fc_cells(inputs_html_user_project)
        addrs = {attrs["data-fc-addr"] for attrs in cells}
        for expected in (
            "inputs!identity.project_name",
            "inputs!technical.capacity_mw",
            "inputs!schedule.cod_date",
            "inputs!revenue.price",
            "inputs!debt.senior_debt",
            "inputs!tax.cit_rate",
        ):
            assert expected in addrs, f"{expected} missing from {sorted(addrs)}"

    def test_editable_cells_match_existing_convention(self, inputs_html_user_project):
        """Cross-check: a cell is data-fc-editable="true" iff it
        contains a real <input> (the pre-existing editable-vs-readonly
        convention), confirming the migration did not change which
        fields are editable."""
        cells_with_html = []
        for match in CELL_RE.finditer(inputs_html_user_project):
            start = match.end()
            end = inputs_html_user_project.find("</span>", start)
            inner = inputs_html_user_project[start:end]
            attrs = dict(ATTR_RE.findall(match.group(0)))
            cells_with_html.append((attrs, inner))
        assert cells_with_html
        for attrs, inner in cells_with_html:
            has_input = bool(HAS_INPUT_RE.search(inner))
            editable = attrs.get("data-fc-editable") == "true"
            assert has_input == editable, (attrs, inner[:120])

    def test_calculated_cells_are_non_editable(self, inputs_html_user_project):
        cells = _fc_cells(inputs_html_user_project)
        addrs = {a["data-fc-addr"]: a for a in cells}
        for addr in ("inputs!debt.senior_debt", "inputs!capex.idc", "inputs!capex.bank_fees", "inputs!debt.shl_amount"):
            assert addrs[addr]["data-fc-editable"] == "false", addr

    def test_deterministic_ordering_across_renders(self):
        html_a = _render_sheet_inputs(is_user_project=True)
        html_b = _render_sheet_inputs(is_user_project=True)
        addrs_a = [a["data-fc-addr"] for a in _fc_cells(html_a)]
        addrs_b = [a["data-fc-addr"] for a in _fc_cells(html_b)]
        assert addrs_a == addrs_b

    def test_readonly_mode_grid_root_present(self, inputs_html_readonly):
        assert 'data-fc-grid="inputs"' in inputs_html_readonly

    def test_readonly_mode_all_cells_non_editable(self, inputs_html_readonly):
        """In is_user_project=False mode, `editable=is_user_project`
        flips every Identity/Technical/Revenue/etc field to False —
        confirms the C1 contract correctly mirrors the pre-existing
        is_user_project gating, not a new editability decision."""
        cells = _fc_cells(inputs_html_readonly)
        assert cells
        for attrs in cells:
            assert attrs.get("data-fc-editable") == "false", attrs
