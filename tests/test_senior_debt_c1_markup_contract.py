"""Senior Debt C1 Migration: markup-contract test.

Asserts the production Senior Debt sheet (`sheet_senior_debt.html`,
rendered standalone via a sample `project_ctx`) emits a valid,
internally-consistent C1 `data-fc-*` markup contract across its mixed
table (`editable-grid-table`) + non-table (`assumption-grid`) layout:

  - the grid root carries `data-fc-grid="seniordebt"`
  - the wrapper carries `data-fc-scroll-container="true"`
  - every addressable cell has a unique `data-fc-addr`
  - every addressable cell has `data-fc-kind` and `data-fc-editable`
  - the 4 draft-workspace inputs are always editable (no is_user_project
    gate exists on them in the production template)
  - the 5 assumption-grid summary fields are always non-editable and
    use distinct addresses (suffixed `_summary`) to avoid colliding
    with the editable draft-input addresses
  - addresses are deterministic, never derived from display text

This is a static (HTML-string) test, mirroring
tests/test_revenue_c1_markup_contract.py /
tests/test_inputs_c1_markup_contract.py. Production-route browser
coverage lives in tests/test_senior_debt_c1_migration_browser.py.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_TEMPLATES = REPO_ROOT / "app" / "templates"

CELL_RE = re.compile(r'<(?:td|span)[^>]*data-fc-cell="true"[^>]*>', re.IGNORECASE)
ATTR_RE = re.compile(r'(data-fc-[a-z]+)="([^"]*)"')


class _Ctx(dict):
    def __getattr__(self, key):
        return self.get(key)


SAMPLE_PROJECT_CTX = _Ctx(
    name="Test Senior Debt Project",
    senior_debt_keur=35000.0,
    senior_tenor_years=15,
    interest_rate_pct=0.05,
    target_dscr=1.30,
    gearing_pct=0.70,
)

SAMPLE_PROJECT_CTX_NO_GEARING = _Ctx(
    name="Test Senior Debt Project No Gearing",
    senior_debt_keur=35000.0,
    senior_tenor_years=15,
    interest_rate_pct=0.05,
    target_dscr=1.30,
    gearing_pct=None,
)


def _render_sheet_senior_debt(project_ctx=SAMPLE_PROJECT_CTX, is_user_project=True):
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    env = Environment(
        loader=FileSystemLoader(str(APP_TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )
    tmpl = env.get_template("partials/sheet_senior_debt.html")
    return tmpl.render(project_ctx=project_ctx, is_user_project=is_user_project)


def _fc_cells(html):
    cells = []
    for match in CELL_RE.finditer(html):
        tag = match.group(0)
        attrs = dict(ATTR_RE.findall(tag))
        cells.append(attrs)
    return cells


@pytest.fixture(scope="module")
def senior_debt_html():
    return _render_sheet_senior_debt()


@pytest.fixture(scope="module")
def senior_debt_html_no_gearing():
    return _render_sheet_senior_debt(project_ctx=SAMPLE_PROJECT_CTX_NO_GEARING)


class TestSeniorDebtMarkupContract:
    def test_grid_root_present(self, senior_debt_html):
        assert 'data-fc-grid="seniordebt"' in senior_debt_html

    def test_scroll_container_present(self, senior_debt_html):
        assert 'data-fc-scroll-container="true"' in senior_debt_html

    def test_fc_cells_exist(self, senior_debt_html):
        cells = _fc_cells(senior_debt_html)
        assert len(cells) > 0

    def test_every_fc_cell_has_addr_kind_and_editable(self, senior_debt_html):
        cells = _fc_cells(senior_debt_html)
        for attrs in cells:
            assert attrs.get("data-fc-addr"), attrs
            assert attrs.get("data-fc-kind") == "text", attrs
            assert attrs.get("data-fc-editable") in ("true", "false"), attrs

    def test_no_duplicate_addresses(self, senior_debt_html):
        cells = _fc_cells(senior_debt_html)
        addrs = [attrs["data-fc-addr"] for attrs in cells]
        assert len(addrs) == len(set(addrs)), "duplicate data-fc-addr values found"

    def test_addresses_are_deterministic_not_display_text(self, senior_debt_html):
        cells = _fc_cells(senior_debt_html)
        for attrs in cells:
            addr = attrs["data-fc-addr"]
            assert addr.startswith("seniordebt!"), addr
            assert " " not in addr, addr

    def test_known_address_examples_present(self, senior_debt_html):
        cells = _fc_cells(senior_debt_html)
        addrs = {attrs["data-fc-addr"] for attrs in cells}
        for expected in (
            "seniordebt!gearing_pct",
            "seniordebt!target_dscr",
            "seniordebt!interest_rate_pct",
            "seniordebt!tenor_years",
            "seniordebt!facility_amount",
            "seniordebt!tenor_summary",
            "seniordebt!interest_rate_summary",
            "seniordebt!target_dscr_summary",
            "seniordebt!gearing_pct_summary",
        ):
            assert expected in addrs, f"{expected} missing from {sorted(addrs)}"

    def test_draft_inputs_are_always_editable(self, senior_debt_html):
        cells = _fc_cells(senior_debt_html)
        addrs = {a["data-fc-addr"]: a for a in cells}
        for addr in (
            "seniordebt!gearing_pct",
            "seniordebt!target_dscr",
            "seniordebt!interest_rate_pct",
            "seniordebt!tenor_years",
        ):
            assert addrs[addr]["data-fc-editable"] == "true", addr

    def test_assumption_summary_cells_are_non_editable(self, senior_debt_html):
        cells = _fc_cells(senior_debt_html)
        addrs = {a["data-fc-addr"]: a for a in cells}
        for addr in (
            "seniordebt!facility_amount",
            "seniordebt!tenor_summary",
            "seniordebt!interest_rate_summary",
            "seniordebt!target_dscr_summary",
            "seniordebt!gearing_pct_summary",
        ):
            assert addrs[addr]["data-fc-editable"] == "false", addr

    def test_draft_input_raw_values_present(self, senior_debt_html):
        cells = _fc_cells(senior_debt_html)
        addrs = {a["data-fc-addr"]: a for a in cells}
        assert addrs["seniordebt!gearing_pct"]["data-fc-raw"] == "0.7"
        assert addrs["seniordebt!target_dscr"]["data-fc-raw"] == "1.3"
        assert addrs["seniordebt!interest_rate_pct"]["data-fc-raw"] == "0.05"
        assert addrs["seniordebt!tenor_years"]["data-fc-raw"] == "15"

    def test_summary_raw_values_match_project_ctx(self, senior_debt_html):
        cells = _fc_cells(senior_debt_html)
        addrs = {a["data-fc-addr"]: a for a in cells}
        assert addrs["seniordebt!facility_amount"]["data-fc-raw"] == "35000.0"
        assert addrs["seniordebt!tenor_summary"]["data-fc-raw"] == "15"
        assert addrs["seniordebt!interest_rate_summary"]["data-fc-raw"] == "0.05"
        assert addrs["seniordebt!target_dscr_summary"]["data-fc-raw"] == "1.3"
        assert addrs["seniordebt!gearing_pct_summary"]["data-fc-raw"] == "0.7"

    def test_deterministic_ordering_across_renders(self):
        html_a = _render_sheet_senior_debt()
        html_b = _render_sheet_senior_debt()
        addrs_a = [a["data-fc-addr"] for a in _fc_cells(html_a)]
        addrs_b = [a["data-fc-addr"] for a in _fc_cells(html_b)]
        assert addrs_a == addrs_b

    def test_no_gearing_omits_gearing_summary_cell(self, senior_debt_html_no_gearing):
        """The gearing_pct_summary cell only renders inside the
        pre-existing `{% if project_ctx.gearing_pct %}` conditional —
        confirms the C1 contract did not change that conditional."""
        cells = _fc_cells(senior_debt_html_no_gearing)
        addrs = {a["data-fc-addr"] for a in cells}
        assert "seniordebt!gearing_pct_summary" not in addrs
        # the other 4 draft inputs + 4 non-gearing summary cells still present
        assert "seniordebt!gearing_pct" in addrs
        assert "seniordebt!facility_amount" in addrs
