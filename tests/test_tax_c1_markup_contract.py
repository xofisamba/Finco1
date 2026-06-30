"""Tax C1 Migration: markup-contract test.

Asserts the production Tax sheet (`app/templates/partials/sheet_tax.html`,
rendered standalone via a sample `project_ctx`) emits a valid,
internally-consistent C1 `data-fc-*` markup contract:

  - the grid root carries `data-fc-grid="tax"`
  - the wrapper carries `data-fc-scroll-container="true"`
  - every addressable cell has a unique `data-fc-addr`
  - every addressable cell has `data-fc-kind` and `data-fc-editable`
  - every cell is non-editable (the production Tax sheet has no
    `<input>` anywhere -- it is entirely calculated/static display)
  - addresses are deterministic, never derived from display text
  - `audit_mode=False` renders without leaking escaped HTML markup
    as visible text (a direct regression check tied to the
    `inputs_section.html` Tax Summary escaping bug investigated for
    this migration -- see docs/TAX_C1_MIGRATION_NOTE.md; that bug
    lives in a different file and is confirmed NOT present here)

This is a static (HTML-string) test, mirroring
tests/test_senior_debt_c1_markup_contract.py /
tests/test_revenue_c1_markup_contract.py. Production-route browser
coverage lives in tests/test_tax_c1_migration_browser.py.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_TEMPLATES = REPO_ROOT / "app" / "templates"

CELL_RE = re.compile(r'<(?:td|span|div)[^>]*data-fc-cell="true"[^>]*>', re.IGNORECASE)
ATTR_RE = re.compile(r'(data-fc-[a-z]+)="([^"]*)"')


class _Ctx(dict):
    def __getattr__(self, key):
        return self.get(key)


SAMPLE_PROJECT_CTX = _Ctx(
    name="Test Tax Project",
    cit_rate_pct=0.19,
    loss_carryforward_years=10,
)


def _render_sheet_tax(project_ctx=SAMPLE_PROJECT_CTX, audit_mode=True):
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    env = Environment(
        loader=FileSystemLoader(str(APP_TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )
    tmpl = env.get_template("partials/sheet_tax.html")
    return tmpl.render(project_ctx=project_ctx, audit_mode=audit_mode)


def _fc_cells(html):
    cells = []
    for match in CELL_RE.finditer(html):
        tag = match.group(0)
        attrs = dict(ATTR_RE.findall(tag))
        cells.append(attrs)
    return cells


@pytest.fixture(scope="module")
def tax_html_audit():
    return _render_sheet_tax(audit_mode=True)


@pytest.fixture(scope="module")
def tax_html_normal():
    return _render_sheet_tax(audit_mode=False)


class TestTaxMarkupContract:
    def test_grid_root_present(self, tax_html_audit):
        assert 'data-fc-grid="tax"' in tax_html_audit

    def test_scroll_container_present(self, tax_html_audit):
        assert 'data-fc-scroll-container="true"' in tax_html_audit

    def test_fc_cells_exist(self, tax_html_audit):
        cells = _fc_cells(tax_html_audit)
        assert len(cells) > 0

    def test_every_fc_cell_has_addr_kind_and_editable(self, tax_html_audit):
        cells = _fc_cells(tax_html_audit)
        for attrs in cells:
            assert attrs.get("data-fc-addr"), attrs
            assert attrs.get("data-fc-kind") == "text", attrs
            assert attrs.get("data-fc-editable") in ("true", "false"), attrs

    def test_no_duplicate_addresses(self, tax_html_audit):
        cells = _fc_cells(tax_html_audit)
        addrs = [attrs["data-fc-addr"] for attrs in cells]
        assert len(addrs) == len(set(addrs)), "duplicate data-fc-addr values found"

    def test_addresses_are_deterministic_not_display_text(self, tax_html_audit):
        cells = _fc_cells(tax_html_audit)
        for attrs in cells:
            addr = attrs["data-fc-addr"]
            assert addr.startswith("tax!"), addr
            assert " " not in addr, addr

    def test_known_address_examples_present(self, tax_html_audit):
        # Product Gap PR9: the "Convention" badge (a static "AUDIT-ONLY"
        # literal with no real binding) and the audit-only G20/R99/R102
        # governance cells (internal jargon, not user-facing tax data)
        # were removed from the Tax sheet as part of the UX-honesty
        # cleanup -- see docs/PRODUCT_GAP_PR9_TAX_REALITY_CHECK.md.
        # Only the two real project-assumption cells remain.
        cells = _fc_cells(tax_html_audit)
        addrs = {attrs["data-fc-addr"] for attrs in cells}
        for expected in (
            "tax!cit_rate",
            "tax!loss_carryforward",
        ):
            assert expected in addrs, f"{expected} missing from {sorted(addrs)}"
        for removed in ("tax!convention", "tax!g20_status", "tax!r99_r102_status"):
            assert removed not in addrs, f"{removed} should have been removed by PR9"

    def test_all_cells_are_non_editable(self, tax_html_audit):
        """The production Tax sheet has no <input> anywhere -- every
        field is calculated/static display. The C1 migration must not
        introduce editability where none existed before."""
        cells = _fc_cells(tax_html_audit)
        for attrs in cells:
            assert attrs["data-fc-editable"] == "false", attrs

    def test_no_real_input_elements_anywhere(self, tax_html_audit):
        assert "<input" not in tax_html_audit

    def test_audit_only_fields_absent_in_both_modes(self, tax_html_audit, tax_html_normal):
        """Product Gap PR9: the G20/R99/R102 audit-only governance
        cells were removed from the Tax sheet entirely (internal
        jargon, not real tax data) -- they no longer appear in either
        audit_mode=True or audit_mode=False rendering."""
        for html in (tax_html_audit, tax_html_normal):
            cells = _fc_cells(html)
            addrs = {a["data-fc-addr"] for a in cells}
            assert "tax!g20_status" not in addrs
            assert "tax!r99_r102_status" not in addrs
            # the always-present real assumption fields remain
            assert "tax!cit_rate" in addrs
            assert "tax!loss_carryforward" in addrs

    def test_deterministic_ordering_across_renders(self):
        html_a = _render_sheet_tax()
        html_b = _render_sheet_tax()
        addrs_a = [a["data-fc-addr"] for a in _fc_cells(html_a)]
        addrs_b = [a["data-fc-addr"] for a in _fc_cells(html_b)]
        assert addrs_a == addrs_b

    def test_audit_mode_false_renders_without_jinja_errors(self, tax_html_normal):
        """sheet_tax.html does not hit the audit_mode=False
        tax_rows_normal list-literal escaping bug documented in
        docs/INPUTS_C1_MIGRATION_NOTE.md -- that bug lives in
        inputs_section.html's distinct Tax Summary card, a different
        file entirely. This is a direct regression check that no
        escaped HTML markup leaks as visible text in this template's
        audit_mode=False rendering."""
        assert "&lt;" not in tax_html_normal
        assert "&amp;lt;" not in tax_html_normal
        assert "&#39;data-fc" not in tax_html_normal

    def test_raw_values_match_project_ctx(self, tax_html_audit):
        cells = _fc_cells(tax_html_audit)
        addrs = {a["data-fc-addr"]: a for a in cells}
        assert addrs["tax!cit_rate"]["data-fc-raw"] == "0.19"
        assert addrs["tax!loss_carryforward"]["data-fc-raw"] == "10"
