"""Export/Audit C1 Migration: markup-contract test.

Asserts the production Export ("Downloads & Audit Artefacts",
`panel-downloads` in `workspace_shell.html`) and Audit/Reference
(`panel-audit`, via `_audit_governance_relocated.html`) surfaces emit
a valid, internally-consistent C1 `data-fc-*` markup contract:

  - the export grid root carries `data-fc-grid="export"`
  - the audit grid root carries `data-fc-grid="audit"`
  - both wrappers carry `data-fc-scroll-container="true"`
  - every addressable cell has a unique `data-fc-addr`
  - every addressable cell has `data-fc-kind` and `data-fc-editable`
  - every cell is `data-fc-editable="false"` (these are downloads,
    status displays, and lineage metadata -- never editable)
  - addresses are deterministic, never derived from display text
  - the download `<a>` elements keep their real `href` and are not
    wrapped by an intercepting element

This is a static (HTML-string) test, mirroring
tests/test_senior_debt_c1_markup_contract.py. Production-route browser
coverage (including click-still-works verification) lives in
tests/test_export_audit_c1_migration_browser.py.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_TEMPLATES = REPO_ROOT / "app" / "templates"

CELL_RE = re.compile(r'<[a-zA-Z]+[^>]*data-fc-cell="true"[^>]*>', re.IGNORECASE)
ATTR_RE = re.compile(r'(data-fc-[a-z]+)="([^"]*)"')


class _Ctx(dict):
    def __getattr__(self, key):
        return self.get(key)


SAMPLE_PROJECT_RECORD = _Ctx(project_code="tuho")

SAMPLE_EXPORT_LINEAGE_UI = _Ctx(
    current_context=_Ctx(
        project_label="TUHO Wind",
        project_code="TUHO",
        active_scenario_name="Workspace Base",
        active_scenario_id="not_applicable",
        scenario_revision="2026-06-01 10:00",
        runtime_snapshot_id="snap-001",
        runtime_origin_label="Last clean backend run",
        runtime_generated_at="2026-06-01 10:05",
        action_note="Draft and saved state are aligned.",
    )
)


def _render_downloads_panel(export_lineage_ui=SAMPLE_EXPORT_LINEAGE_UI, project_record=SAMPLE_PROJECT_RECORD):
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    env = Environment(
        loader=FileSystemLoader(str(APP_TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )
    src = (APP_TEMPLATES / "partials" / "workspace_shell.html").read_text()
    start = src.index('<!-- ----------------------------------------------- DOWNLOADS -- -->')
    end = src.index('<!-- ----------------------------------------------- COMPARE -- -->')
    snippet = src[start:end]
    tmpl = env.from_string(snippet)
    return tmpl.render(export_lineage_ui=export_lineage_ui, project_record=project_record)


def _render_audit_governance():
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    env = Environment(
        loader=FileSystemLoader(str(APP_TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )
    tmpl = env.get_template("partials/_audit_governance_relocated.html")
    return tmpl.render(export_lineage_ui=SAMPLE_EXPORT_LINEAGE_UI, is_user_project=True)


def _fc_cells(html):
    cells = []
    for match in CELL_RE.finditer(html):
        tag = match.group(0)
        attrs = dict(ATTR_RE.findall(tag))
        cells.append(attrs)
    return cells


@pytest.fixture(scope="module")
def downloads_html():
    return _render_downloads_panel()


@pytest.fixture(scope="module")
def audit_html():
    return _render_audit_governance()


class TestExportMarkupContract:
    def test_grid_root_present(self, downloads_html):
        assert 'data-fc-grid="export"' in downloads_html

    def test_scroll_container_present(self, downloads_html):
        assert 'data-fc-scroll-container="true"' in downloads_html

    def test_fc_cells_exist(self, downloads_html):
        cells = _fc_cells(downloads_html)
        assert len(cells) > 0

    def test_every_fc_cell_has_addr_kind_and_editable(self, downloads_html):
        cells = _fc_cells(downloads_html)
        for attrs in cells:
            assert attrs.get("data-fc-addr"), attrs
            assert attrs.get("data-fc-kind") == "text", attrs
            assert attrs.get("data-fc-editable") == "false", attrs

    def test_no_duplicate_addresses(self, downloads_html):
        cells = _fc_cells(downloads_html)
        addrs = [attrs["data-fc-addr"] for attrs in cells]
        assert len(addrs) == len(set(addrs)), "duplicate data-fc-addr values found"

    def test_addresses_are_deterministic_not_display_text(self, downloads_html):
        cells = _fc_cells(downloads_html)
        for attrs in cells:
            addr = attrs["data-fc-addr"]
            assert addr.startswith("export!"), addr
            assert " " not in addr, addr

    def test_known_address_examples_present(self, downloads_html):
        cells = _fc_cells(downloads_html)
        addrs = {attrs["data-fc-addr"] for attrs in cells}
        for expected in (
            "export!current_context.project",
            "export!current_context.scenario",
            "export!workbook_download.values_only",
            "export!workbook_download.runtime_summary_csv",
            "export!workbook_download.institutional_workbook",
        ):
            assert expected in addrs, f"{expected} missing from {sorted(addrs)}"

    def test_download_links_keep_real_href(self, downloads_html):
        assert '<a href="/download" class="download-item"' in downloads_html
        assert "/exports/runtime-summary.csv?project=tuho" in downloads_html
        assert "/exports/institutional-workbook.xlsx?project=tuho" in downloads_html

    def test_download_links_are_not_wrapped(self, downloads_html):
        """The data-fc-* attributes are added directly onto the
        existing <a class="download-item"> elements, never onto a
        new wrapping element placed in front of them."""
        assert re.search(
            r'<a href="/download" class="download-item" data-fc-row="true" data-fc-cell="true"',
            downloads_html,
        )

    def test_deterministic_ordering_across_renders(self):
        html_a = _render_downloads_panel()
        html_b = _render_downloads_panel()
        addrs_a = [a["data-fc-addr"] for a in _fc_cells(html_a)]
        addrs_b = [a["data-fc-addr"] for a in _fc_cells(html_b)]
        assert addrs_a == addrs_b


class TestAuditMarkupContract:
    def test_grid_root_present(self, audit_html):
        assert 'data-fc-grid="audit"' in audit_html

    def test_scroll_container_present(self, audit_html):
        assert 'data-fc-scroll-container="true"' in audit_html

    def test_fc_cells_exist(self, audit_html):
        cells = _fc_cells(audit_html)
        assert len(cells) > 0

    def test_every_fc_cell_has_addr_kind_and_editable(self, audit_html):
        cells = _fc_cells(audit_html)
        for attrs in cells:
            assert attrs.get("data-fc-addr"), attrs
            assert attrs.get("data-fc-kind") == "text", attrs
            assert attrs.get("data-fc-editable") == "false", attrs

    def test_no_duplicate_addresses(self, audit_html):
        cells = _fc_cells(audit_html)
        addrs = [attrs["data-fc-addr"] for attrs in cells]
        assert len(addrs) == len(set(addrs)), "duplicate data-fc-addr values found"

    def test_addresses_are_deterministic_not_display_text(self, audit_html):
        cells = _fc_cells(audit_html)
        for attrs in cells:
            addr = attrs["data-fc-addr"]
            assert addr.startswith("audit!"), addr
            assert " " not in addr, addr

    def test_known_address_examples_present(self, audit_html):
        cells = _fc_cells(audit_html)
        addrs = {attrs["data-fc-addr"] for attrs in cells}
        for expected in (
            "audit!current_context.project",
            "audit!current_context.scenario",
            "audit!governance_status.g20_gate",
            "audit!governance_status.r99_r102_promotion",
            "audit!reference_evidence.senior_debt",
            "audit!reference_evidence.tax_cfads",
        ):
            assert expected in addrs, f"{expected} missing from {sorted(addrs)}"

    def test_deterministic_ordering_across_renders(self):
        html_a = _render_audit_governance()
        html_b = _render_audit_governance()
        addrs_a = [a["data-fc-addr"] for a in _fc_cells(html_a)]
        addrs_b = [a["data-fc-addr"] for a in _fc_cells(html_b)]
        assert addrs_a == addrs_b
