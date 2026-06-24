"""Phase 57A-10G - CAPEX Advanced Column Groups tests.

This test file verifies that:
- The CAPEX detail grid (`sheet_capex_detail.html`) carries a
  new top-of-thead row with 6 column-group header cells, with
  colspans summing to 29 (5 + 2 + 2 + 1 + 18 + 1) and the
  correct `data-capex-group` attribute on each
- The CAPEX single sheet (`sheet_capex.html`) carries a
  `data-capex-column-groups` semantic guide panel with 4 group
  entries (Core, Costing, Tax, Schedule)
- The status chips from Phase 57A-10F (Cont. %, VAT %, WHT %)
  remain visible
- The metadata-only disclaimer from Phase 57A-10F remains visible
- The templates have no Jinja syntax errors that would surface as
  UndefinedError / NameError / AttributeError at render time
- No CAPEX total change (no `_CAPEX_ITEM_FIELDS` tuple change,
  no `CapexItem` dataclass field change)
- No forbidden-path changes (no domain / persistence / main_web /
  main_api / static / tax / depreciation / debt changes)
- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` is reachable

The tests are render / context / export safety only. They do NOT
touch model calculations.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SHEET_CAPEX_HTML = (
    REPO_ROOT / "app" / "templates" / "partials" / "sheet_capex.html"
)
SHEET_CAPEX_DETAIL_HTML = (
    REPO_ROOT / "app" / "templates" / "partials" / "sheet_capex_detail.html"
)
DOMAIN_INPUTS_PY = REPO_ROOT / "domain" / "inputs.py"
DESIGN_DOC = (
    REPO_ROOT / "docs" / "phase57a10g_capex_advanced_column_groups.md"
)
REPORT_JSON = (
    REPO_ROOT
    / "reports"
    / "phase57a10g_capex_advanced_column_groups.json"
)


# Canonical column-group mapping for the CAPEX detail grid.
CANONICAL_GROUPS = (
    ("core", 5),
    ("costing", 2),
    ("tax", 2),
    ("meta", 1),       # Status
    ("schedule", 18),
    ("meta", 1),       # Notes
)
TOTAL_COLSPAN = sum(colspan for _, colspan in CANONICAL_GROUPS)
# Total CAPEX detail grid columns (1..29).
TOTAL_COLUMNS = 29
EXPECTED_GROUP_NAMES = ("core", "costing", "tax", "meta", "schedule")
EXPECTED_PANEL_GROUPS = ("core", "costing", "tax", "schedule")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sheet_capex_html_text() -> str:
    return SHEET_CAPEX_HTML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def sheet_capex_detail_html_text() -> str:
    return SHEET_CAPEX_DETAIL_HTML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def domain_inputs_text() -> str:
    return DOMAIN_INPUTS_PY.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------


class TestFilesExist:
    def test_design_doc_exists(self):
        assert DESIGN_DOC.is_file(), f"missing design doc: {DESIGN_DOC}"

    def test_report_json_exists(self):
        assert REPORT_JSON.is_file(), f"missing report: {REPORT_JSON}"

    def test_sheet_capex_html_exists(self):
        assert SHEET_CAPEX_HTML.is_file()

    def test_sheet_capex_detail_html_exists(self):
        assert SHEET_CAPEX_DETAIL_HTML.is_file()


# ---------------------------------------------------------------------------
# CAPEX detail grid: column group headers
# ---------------------------------------------------------------------------


class TestDetailGridGroupHeaders:
    """The detail grid thead row 0 must contain 6 group header cells
    with the correct colspan and data-capex-group attributes."""

    def _find_groups_row(self, text: str) -> str:
        """Return the <tr class="fc-grid-header--groups" ...> block."""
        match = re.search(
            r'<tr class="fc-grid-header fc-grid-header--groups"[^>]*'
            r'data-capex-column-groups="true"[^>]*>(.*?)</tr>',
            text,
            re.DOTALL,
        )
        assert match, (
            "groups row not found - check that "
            '<tr class="fc-grid-header fc-grid-header--groups" '
            'data-capex-column-groups="true"> is present in <thead>'
        )
        return match.group(1)

    def test_groups_row_present(self, sheet_capex_detail_html_text):
        self._find_groups_row(sheet_capex_detail_html_text)

    def test_groups_row_in_thead(self, sheet_capex_detail_html_text):
        # The groups row must be inside <thead>
        thead_match = re.search(
            r'<thead>(.*?)</thead>',
            sheet_capex_detail_html_text,
            re.DOTALL,
        )
        assert thead_match, "<thead> not found in sheet_capex_detail.html"
        thead_text = thead_match.group(1)
        # The groups row should be the FIRST <tr> in thead
        first_tr = re.search(r'<tr[^>]*>', thead_text)
        assert first_tr, "no <tr> in <thead>"
        assert "fc-grid-header--groups" in first_tr.group(0), (
            "groups row is not the first row in <thead>"
        )

    @pytest.mark.parametrize(
        "group_name,expected_colspan",
        CANONICAL_GROUPS,
    )
    def test_group_header_cell(
        self, sheet_capex_detail_html_text, group_name, expected_colspan
    ):
        row = self._find_groups_row(sheet_capex_detail_html_text)
        # Each group header cell:
        # <th class="fc-th fc-capex-group-header"
        #     data-capex-group="<name>" colspan="<n>" scope="colgroup">
        cell_pattern = re.compile(
            r'<th[^>]*class="fc-th fc-capex-group-header"[^>]*'
            r'data-capex-group="' + re.escape(group_name) + r'"[^>]*'
            r'colspan="' + str(expected_colspan) + r'"[^>]*'
            r'scope="colgroup"',
            re.DOTALL,
        )
        # `meta` appears twice (Status + Notes), so use search
        assert cell_pattern.search(row), (
            f"group header cell for {group_name!r} colspan={expected_colspan} "
            "not found in groups row"
        )

    def test_colspan_total_is_29(self, sheet_capex_detail_html_text):
        row = self._find_groups_row(sheet_capex_detail_html_text)
        colspans = [int(c) for c in re.findall(r'colspan="(\d+)"', row)]
        assert sum(colspans) == TOTAL_COLUMNS, (
            f"sum of colspans = {sum(colspans)}, "
            f"expected {TOTAL_COLUMNS}"
        )

    def test_six_group_header_cells(self, sheet_capex_detail_html_text):
        row = self._find_groups_row(sheet_capex_detail_html_text)
        cells = re.findall(
            r'<th[^>]*class="fc-th fc-capex-group-header"',
            row,
        )
        assert len(cells) == len(CANONICAL_GROUPS), (
            f"expected {len(CANONICAL_GROUPS)} group header cells, "
            f"got {len(cells)}"
        )

    @pytest.mark.parametrize("group_name", EXPECTED_GROUP_NAMES)
    def test_group_name_present(self, sheet_capex_detail_html_text, group_name):
        row = self._find_groups_row(sheet_capex_detail_html_text)
        assert f'data-capex-group="{group_name}"' in row, (
            f"group name {group_name!r} missing from groups row"
        )

    def test_data_capex_column_groups_attribute(
        self, sheet_capex_detail_html_text
    ):
        assert 'data-capex-column-groups="true"' in sheet_capex_detail_html_text


# ---------------------------------------------------------------------------
# CAPEX detail grid: existing 57A-10F surfaces still visible
# ---------------------------------------------------------------------------


class TestExistingSurfacesPreserved:
    """Phase 57A-10F status chips and disclaimer must remain visible."""

    @pytest.mark.parametrize(
        "status_data_attr,chip_text",
        [("contingency", "Cont.<br/>%"),
         ("VAT", "VAT<br/>%"),
         ("WHT", "WHT<br/>%")],
    )
    def test_status_chip_still_present(
        self, sheet_capex_detail_html_text, status_data_attr, chip_text
    ):
        # The chip pattern is unchanged from 57A-10F
        pattern = (
            r'<span class="badge badge-metadata-only"[^>]*'
            r'data-capex-status="' + re.escape(status_data_attr)
            + r'"[^>]*>Metadata-only</span>'
        )
        assert re.search(pattern, sheet_capex_detail_html_text), (
            f"status chip for {status_data_attr!r} missing - "
            "Phase 57A-10F surface not preserved"
        )

    def test_existing_legend_block_preserved(
        self, sheet_capex_detail_html_text
    ):
        # sheet_capex_detail.html does not carry the legend; it's
        # only in sheet_capex.html. But the per-column chips
        # remain. This test ensures the existing thead is intact.
        thead_match = re.search(
            r'<thead>(.*?)</thead>',
            sheet_capex_detail_html_text,
            re.DOTALL,
        )
        assert thead_match
        thead_text = thead_match.group(1)
        # The original row 1 (fc-grid-header) with the per-column
        # headers (Line Item, Code, Excel kEUR, App kEUR, Delta
        # kEUR, Per MW, Status, M1..M18, Notes) must still be
        # present
        for header in (
            "Line Item", "Code", "Excel<br/>kEUR", "App<br/>kEUR",
            "Delta<br/>kEUR", "Per<br/>MW", "Status", "Notes",
        ):
            assert header in thead_text, (
                f"existing header {header!r} missing from thead"
            )


# ---------------------------------------------------------------------------
# CAPEX single sheet: column groups semantic guide panel
# ---------------------------------------------------------------------------


class TestSingleSheetGroupsPanel:
    """The single sheet must carry a column-groups semantic guide
    panel above the workbook grid."""

    def test_data_capex_column_groups_panel_present(
        self, sheet_capex_html_text
    ):
        assert 'data-capex-column-groups="true"' in sheet_capex_html_text

    def test_panel_class_present(self, sheet_capex_html_text):
        # Phase 57A-10H renamed the class to "capex-column-key"
        # but kept the data attribute. Accept either form.
        assert (
            'class="capex-column-groups"' in sheet_capex_html_text
            or 'class="capex-column-key"' in sheet_capex_html_text
        )

    @pytest.mark.parametrize("group_name", EXPECTED_PANEL_GROUPS)
    def test_panel_li_entry(
        self, sheet_capex_html_text, group_name
    ):
        pattern = (
            r'<li[^>]*data-capex-group="' + re.escape(group_name) + r'"'
        )
        assert re.search(pattern, sheet_capex_html_text), (
            f"panel <li> entry for {group_name!r} missing"
        )

    def test_panel_has_four_entries(self, sheet_capex_html_text):
        # Phase 57A-10H unified the "column groups" panel under
        # the new class "capex-column-key" with the "groups"
        # section. UX-2A moved this panel inside the collapsed-
        # by-default "CAPEX Sheet Guide" <details> block, so it
        # no longer immediately precedes the Workbook grid comment;
        # locate it by its own groups-section / chips wrapper
        # instead. Fall back to the legacy "capex-column-groups"
        # panel if the new one is not present.
        match = re.search(
            r'data-capex-column-key-section="groups">'
            r'(.*?)</div>\s*</div>',
            sheet_capex_html_text,
            re.DOTALL,
        )
        if not match:
            # Fall back to legacy panel (pre-57A-10H layout).
            match = re.search(
                r'<div class="capex-column-groups"[^>]*data-capex-column-groups="true"[^>]*>'
                r'(.*?)<p class="capex-column-groups__hint"',
                sheet_capex_html_text,
                re.DOTALL,
            )
        assert match, (
            "column-groups block not found (looked for new "
            "capex-column-key panel and legacy capex-column-groups panel)"
        )
        block = match.group(1)
        li_count = len(re.findall(r'<li[^>]*data-capex-group=', block))
        assert li_count == 4, (
            f"expected 4 <li data-capex-group=...> entries, got {li_count}"
        )

    def test_panel_chips_present(self, sheet_capex_html_text):
        # The panel must carry Runtime-used and Metadata-only chips
        assert 'badge-runtime-used' in sheet_capex_html_text
        assert 'badge-metadata-only' in sheet_capex_html_text

    def test_existing_57a10f_legend_still_present(
        self, sheet_capex_html_text
    ):
        # Status legend from 57A-10F must remain
        assert 'data-capex-status-legend="true"' in sheet_capex_html_text
        # Disclaimer must remain
        assert 'data-capex-metadata-disclaimer="true"' in sheet_capex_html_text


# ---------------------------------------------------------------------------
# Template syntax safety
# ---------------------------------------------------------------------------


class TestTemplateSyntaxSafety:
    """Templates must have no Jinja syntax errors that would surface
    as UndefinedError / NameError / AttributeError at render time.
    We do a static parse via Jinja2 Environment."""

    def test_sheet_capex_html_parses(self, sheet_capex_html_text):
        from jinja2 import Environment, meta
        env = Environment()
        try:
            env.parse(sheet_capex_html_text)
        except Exception as e:
            pytest.fail(
                f"sheet_capex.html Jinja parse error: {e}"
            )

    def test_sheet_capex_detail_html_parses(
        self, sheet_capex_detail_html_text
    ):
        from jinja2 import Environment
        env = Environment()
        try:
            env.parse(sheet_capex_detail_html_text)
        except Exception as e:
            pytest.fail(
                f"sheet_capex_detail.html Jinja parse error: {e}"
            )


# ---------------------------------------------------------------------------
# No CAPEX total change (regression test for 57A-10F invariant)
# ---------------------------------------------------------------------------


class TestNoCapexStructureChange:
    """The CAPEX item fields tuple in `domain/inputs.py:CapexStructure`
    must NOT be modified by 57A-10G. This is a structural regression
    test, not a formula test."""

    CANONICAL_CAPEX_ITEM_FIELDS = (
        "epc_contract", "production_units", "epc_other", "grid_connection",
        "ops_prep", "insurances", "lease_tax", "construction_mgmt_a",
        "commissioning", "audit_legal", "construction_mgmt_b",
        "contingencies", "taxes", "project_acquisition", "project_rights",
    )

    def test_capex_item_fields_tuple_unchanged(self, domain_inputs_text):
        match = re.search(
            r"_CAPEX_ITEM_FIELDS\s*=\s*\((.*?)\)",
            domain_inputs_text,
            re.DOTALL,
        )
        assert match, "_CAPEX_ITEM_FIELDS tuple missing"
        fields_text = match.group(1)
        fields = re.findall(r'"([a-z_]+)"', fields_text)
        assert tuple(fields) == self.CANONICAL_CAPEX_ITEM_FIELDS, (
            f"_CAPEX_ITEM_FIELDS tuple changed: {fields!r}"
        )

    def test_capex_item_dataclass_fields_unchanged(self, domain_inputs_text):
        idx = domain_inputs_text.find("class CapexItem:")
        assert idx > 0, "class CapexItem not found"
        window = domain_inputs_text[idx : idx + 1500]
        for field in (
            "name", "amount_keur", "y0_share", "spending_profile",
            "asset_class", "useful_life_override",
        ):
            assert re.search(rf"^\s+{field}\s*:", window, re.MULTILINE), (
                f"CapexItem field {field!r} missing or moved"
            )


# ---------------------------------------------------------------------------
# No forbidden-path changes
# ---------------------------------------------------------------------------


class TestNoForbiddenPathChanges:
    """57A-10G must not touch domain layer / persistence / engine /
    route / API / static. This is a sanity check, not a parity test."""

    FORBIDDEN = (
        "domain/",
        "app/persistence/",
        "main_web.py",
        "main_api.py",
        "static/",
    )

    @pytest.mark.parametrize("path", FORBIDDEN)
    def test_path_untouched(self, path):
        result = subprocess.run(
            [
                "git", "diff", "--name-only",
                "origin/main", "HEAD", "--", path,
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        changed = {
            f.strip() for f in result.stdout.strip().split("\n") if f.strip()
        }
        # UX-2A (later phase) legitimately adds CSS for the relocated
        # per-category Add Line button and the collapsed CAPEX Sheet
        # Guide. 57A-10G's own scope is unaffected.
        allowed = {"static/styles.css"} if path == "static/" else set()
        unexpected = changed - allowed
        assert not unexpected, (
            f"57A-10G must not touch {path}: got diff:\n{unexpected}"
        )

    @pytest.mark.parametrize(
        "path",
        [
            "domain/tax/",
            "domain/depreciation/",
            "domain/debt/",
            "domain/financing/",
            "domain/capex/",
        ],
    )
    def test_tax_depreciation_debt_untouched(self, path):
        result = subprocess.run(
            [
                "git", "diff", "--stat",
                "origin/main", "HEAD", "--", path,
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "", (
            f"57A-10G must not touch {path}: got diff:\n{result.stdout}"
        )

    def test_app_excel_export_untouched(self):
        result = subprocess.run(
            [
                "git", "diff", "--stat",
                "origin/main", "HEAD", "--", "app/excel_export.py",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "", (
            f"57A-10G must not touch app/excel_export.py: "
            f"got diff:\n{result.stdout}"
        )


# ---------------------------------------------------------------------------
# rc1 frozen
# ---------------------------------------------------------------------------


class TestRc1Frozen:
    def test_rc1_sha_reachable(self):
        result = subprocess.run(
            ["git", "cat-file", "-e", "b425a0708719eaa5e1d922b1008e5609758e0ad4"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, "rc1 SHA not reachable on origin/main"


# ---------------------------------------------------------------------------
# Documented scope
# ---------------------------------------------------------------------------


class TestDocumentedScope:
    def test_design_doc_declares_ui_only(self):
        text = DESIGN_DOC.read_text(encoding="utf-8")
        assert "no runtime" in text.lower() or "ui only" in text.lower()

    def test_design_doc_declares_4_groups(self):
        text = DESIGN_DOC.read_text(encoding="utf-8")
        for grp in ("Core", "Costing", "Tax", "Schedule"):
            assert grp in text, f"design doc missing group {grp!r}"

    def test_design_doc_declares_no_persistence(self):
        text = DESIGN_DOC.read_text(encoding="utf-8")
        assert "no persistence" in text.lower() or (
            "no persistence / schema changes" in text.lower()
        )
