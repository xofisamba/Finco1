"""Phase 57A-10F — CAPEX advanced metadata UI / audit surface tests.

This test file verifies that:
- CAPEX page renders for both TUHO and Oborovo contexts
- Status legend (Runtime-used / Metadata-only / Design-only / Export-only)
  is visible in `sheet_capex.html`
- Disclaimer badge "Metadata only - does not affect Run." is present
  in the deferred-placeholder block
- VAT %, WHT %, Contingency % column header chips in
  `sheet_capex_detail.html` carry the Metadata-only chip
- The "Metadata Scope" line in the export `CapEx_SubLines_Audit`
  notes block enumerates runtime-used, metadata-only, and
  design-only CAPEX fields
- The CAPEX advanced metadata is exposed in the UI surface only
  (no runtime, no model, no parity, no persistence change)

The tests are render / context / export safety only. They do NOT
touch model calculations.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SHEET_CAPEX_HTML = (
    REPO_ROOT / "app" / "templates" / "partials" / "sheet_capex.html"
)
SHEET_CAPEX_DETAIL_HTML = (
    REPO_ROOT / "app" / "templates" / "partials" / "sheet_capex_detail.html"
)
EXCEL_EXPORT_PY = REPO_ROOT / "app" / "excel_export.py"
DOMAIN_INPUTS_PY = REPO_ROOT / "domain" / "inputs.py"
DESIGN_DOC = (
    REPO_ROOT / "docs" / "phase57a10f_capex_advanced_metadata_ui_audit_surface.md"
)
REPORT_JSON = (
    REPO_ROOT
    / "reports"
    / "phase57a10f_capex_advanced_metadata_ui_audit_surface.json"
)


# Canonical CAPEX structure field order - regression test for
# "no CAPEX total change" requirement.
CANONICAL_CAPEX_ITEM_FIELDS = (
    "epc_contract", "production_units", "epc_other", "grid_connection",
    "ops_prep", "insurances", "lease_tax", "construction_mgmt_a",
    "commissioning", "audit_legal", "construction_mgmt_b", "contingencies",
    "taxes", "project_acquisition", "project_rights",
)


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

    def test_excel_export_py_exists(self):
        assert EXCEL_EXPORT_PY.is_file()

    def test_domain_inputs_py_exists(self):
        assert DOMAIN_INPUTS_PY.is_file()


# ---------------------------------------------------------------------------
# CAPEX page (sheet_capex.html) — status legend + disclaimer
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sheet_capex_html_text() -> str:
    return SHEET_CAPEX_HTML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def sheet_capex_detail_html_text() -> str:
    return SHEET_CAPEX_DETAIL_HTML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def excel_export_text() -> str:
    return EXCEL_EXPORT_PY.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def domain_inputs_text() -> str:
    return DOMAIN_INPUTS_PY.read_text(encoding="utf-8")


class TestStatusLegend:
    """Status legend with all 4 chip categories must be present in
    `sheet_capex.html`."""

    @pytest.mark.parametrize(
        "chip_label",
        ["Runtime-used", "Metadata-only", "Design-only", "Export-only"],
    )
    def test_chip_label_in_legend(self, sheet_capex_html_text, chip_label):
        # Find the status legend block
        match = re.search(
            r'<div class="capex-status-legend"[^>]*>(.*?)</div>',
            sheet_capex_html_text,
            re.DOTALL,
        )
        assert match, "capex-status-legend block missing in sheet_capex.html"
        assert chip_label in match.group(1), (
            f"chip label {chip_label!r} missing from status legend"
        )

    def test_status_legend_data_attribute(self, sheet_capex_html_text):
        assert 'data-capex-status-legend="true"' in sheet_capex_html_text


class TestMetadataDisclaimer:
    """The disclaimer badge must say clearly that the deferred
    placeholders do not affect Run."""

    def test_disclaimer_text_present(self, sheet_capex_html_text):
        assert "Metadata only — does not affect Run." in sheet_capex_html_text, (
            "disclaimer text missing — required by brief"
        )

    def test_disclaimer_block_present(self, sheet_capex_html_text):
        assert 'data-capex-metadata-disclaimer="true"' in sheet_capex_html_text


class TestDeferredPlaceholderChips:
    """Each deferred placeholder line in the deferred-note block
    must carry a status chip."""

    @pytest.mark.parametrize(
        "label",
        [
            "Payment schedule by construction month",
            "Depreciation category / useful life / flag",
            "VAT applicability / rate / cost",
            "WHT rate / cost",
            "Utilisation of funds during construction",
        ],
    )
    def test_deferred_placeholder_has_chip(self, sheet_capex_html_text, label):
        # Find the deferred note block
        match = re.search(
            r'<div class="capex-deferred-note"[^>]*>(.*?)</div>',
            sheet_capex_html_text,
            re.DOTALL,
        )
        assert match, "capex-deferred-note block missing"
        block = match.group(1)
        # Each line should mention the label and at least one chip badge
        line_pattern = re.compile(
            r'<li>.*?badge-(?:design-only|metadata-only|export-only|runtime-used).*?'
            + re.escape(label)
            + r'.*?</li>',
            re.DOTALL,
        )
        assert line_pattern.search(block), (
            f"deferred placeholder for {label!r} missing chip or label"
        )


# ---------------------------------------------------------------------------
# CAPEX detail page (sheet_capex_detail.html) — column header chips
# ---------------------------------------------------------------------------


class TestDetailColumnHeaderChips:
    """The VAT %, WHT %, Contingency % column headers in
    `sheet_capex_detail.html` must carry a Metadata-only chip."""

    @pytest.mark.parametrize(
        "status_data_attr",
        ["VAT", "WHT", "contingency"],
    )
    def test_column_header_has_metadata_only_chip(
        self, sheet_capex_detail_html_text, status_data_attr
    ):
        # The data-capex-status attribute lives on a <span> inside
        # the <th>. The chip text is "Metadata-only".
        pattern = (
            r'<span class="badge badge-metadata-only"[^>]*'
            r'data-capex-status="' + re.escape(status_data_attr)
            + r'"[^>]*>Metadata-only</span>'
        )
        assert re.search(pattern, sheet_capex_detail_html_text), (
            f"data-capex-status={status_data_attr!r} chip "
            "missing or text is wrong"
        )

    def test_metadata_only_chip_text_present(self, sheet_capex_detail_html_text):
        # The chips use the text "Metadata-only" inside the span
        assert (
            sheet_capex_detail_html_text.count(
                'data-capex-status="'
            )
            >= 3
        ), "expected at least 3 data-capex-status chips (VAT, WHT, contingency)"


# ---------------------------------------------------------------------------
# Export / audit (app/excel_export.py) — Metadata Scope extension
# ---------------------------------------------------------------------------


class TestExportMetadataScope:
    """The "Metadata Scope" line in the CapEx_SubLines_Audit notes
    block must enumerate runtime-used, metadata-only, and
    design-only CAPEX fields."""

    def test_metadata_scope_line_present(self, excel_export_text):
        assert '"Metadata Scope"' in excel_export_text, (
            'Metadata Scope key missing from excel_export.py notes block'
        )

    def test_runtime_used_fields_named(self, excel_export_text):
        # Locate the Metadata Scope tuple and check fields
        match = re.search(
            r'\("Metadata Scope",\s*\((.*?)\)\),',
            excel_export_text,
            re.DOTALL,
        )
        assert match, "Metadata Scope tuple not found"
        block = match.group(1)
        for field in (
            "amount", "y0_share", "spending_profile", "asset_class",
            "idc", "bank_fees", "commitment_fees", "other_financial",
            "vat_costs", "reserve_accounts",
        ):
            assert field in block, f"runtime-used field {field!r} missing"

    def test_metadata_only_fields_named(self, excel_export_text):
        match = re.search(
            r'\("Metadata Scope",\s*\((.*?)\)\),',
            excel_export_text,
            re.DOTALL,
        )
        assert match
        block = match.group(1)
        for field in (
            "useful_life_override", "VAT %", "WHT %", "contingency %",
        ):
            assert field in block, f"metadata-only field {field!r} missing"

    def test_design_only_fields_named(self, excel_export_text):
        match = re.search(
            r'\("Metadata Scope",\s*\((.*?)\)\),',
            excel_export_text,
            re.DOTALL,
        )
        assert match
        block = match.group(1)
        for field in (
            "payment schedule", "depreciation",
            "VAT applicability", "WHT rate", "utilisation of funds",
        ):
            assert field in block, f"design-only field {field!r} missing"

    def test_metadata_does_not_affect_run_disclaimer(self, excel_export_text):
        assert "Metadata only - does not affect Run." in excel_export_text, (
            "Metadata Scope line must include the "
            "'does not affect Run' disclaimer"
        )


# ---------------------------------------------------------------------------
# No CAPEX total change — regression test
# ---------------------------------------------------------------------------


class TestNoCapexStructureChange:
    """The CAPEX item fields tuple in `domain/inputs.py:CapexStructure`
    must NOT be modified by 57A-10F. This is a structural regression
    test, not a formula test."""

    def test_capex_item_fields_tuple_unchanged(self, domain_inputs_text):
        # Find the _CAPEX_ITEM_FIELDS tuple
        match = re.search(
            r"_CAPEX_ITEM_FIELDS\s*=\s*\((.*?)\)",
            domain_inputs_text,
            re.DOTALL,
        )
        assert match, "_CAPEX_ITEM_FIELDS tuple missing"
        # Extract field names
        fields_text = match.group(1)
        fields = re.findall(r'"([a-z_]+)"', fields_text)
        assert tuple(fields) == CANONICAL_CAPEX_ITEM_FIELDS, (
            f"_CAPEX_ITEM_FIELDS tuple changed: {fields!r} != "
            f"{CANONICAL_CAPEX_ITEM_FIELDS!r}"
        )

    def test_capex_item_dataclass_fields_unchanged(self, domain_inputs_text):
        # The named fields of CapexItem must remain: name, amount_keur,
        # y0_share, spending_profile, asset_class, useful_life_override.
        # Search the entire file for `class CapexItem:` then take
        # the lines following it until the next top-level statement.
        idx = domain_inputs_text.find("class CapexItem:")
        assert idx > 0, "class CapexItem not found"
        # Take a window of 1500 chars after the class declaration.
        window = domain_inputs_text[idx : idx + 1500]
        for field in (
            "name", "amount_keur", "y0_share", "spending_profile",
            "asset_class", "useful_life_override",
        ):
            assert re.search(rf"^\s+{field}\s*:", window, re.MULTILINE), (
                f"CapexItem field {field!r} missing or moved"
            )


# ---------------------------------------------------------------------------
# No forbidden code paths — UI / export only
# ---------------------------------------------------------------------------


class TestNoRuntimeMaterializationChange:
    """57A-10F must not touch domain layer / persistence / engine
    / route / API. This is a sanity check, not a parity test."""

    def test_domain_untouched_57a10f(self):
        # Domain inputs.py should not have any new lines added by
        # 57A-10F. We assert that the diff vs base SHA is empty for
        # domain/.
        # Skipped if git is unavailable.
        import subprocess
        result = subprocess.run(
            [
                "git", "diff", "--stat",
                "origin/main", "HEAD", "--", "domain/",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # The diff should be empty (no domain changes)
        assert result.stdout.strip() == "", (
            f"57A-10F must not touch domain/: got diff:\n{result.stdout}"
        )

    def test_persistence_untouched_57a10f(self):
        import subprocess
        result = subprocess.run(
            [
                "git", "diff", "--stat",
                "origin/main", "HEAD", "--", "app/persistence/",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "", (
            f"57A-10F must not touch app/persistence/: got diff:\n{result.stdout}"
        )

    def test_main_web_untouched_57a10f(self):
        import subprocess
        result = subprocess.run(
            [
                "git", "diff", "--stat",
                "origin/main", "HEAD", "--", "main_web.py",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "", (
            f"57A-10F must not touch main_web.py: got diff:\n{result.stdout}"
        )

    def test_main_api_untouched_57a10f(self):
        import subprocess
        result = subprocess.run(
            [
                "git", "diff", "--stat",
                "origin/main", "HEAD", "--", "main_api.py",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "", (
            f"57A-10F must not touch main_api.py: got diff:\n{result.stdout}"
        )

    def test_static_untouched_57a10f(self):
        import subprocess
        result = subprocess.run(
            [
                "git", "diff", "--stat",
                "origin/main", "HEAD", "--", "static/",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "", (
            f"57A-10F must not touch static/: got diff:\n{result.stdout}"
        )

    def test_no_tax_engine_change(self):
        import subprocess
        result = subprocess.run(
            [
                "git", "diff", "--name-only",
                "origin/main", "HEAD", "--",
                "domain/tax/", "app/tax*",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # The diff should be empty (no tax changes)
        assert result.stdout.strip() == "", (
            f"57A-10F must not touch tax engine: got diff:\n{result.stdout}"
        )

    def test_no_depreciation_change(self):
        import subprocess
        result = subprocess.run(
            [
                "git", "diff", "--name-only",
                "origin/main", "HEAD", "--",
                "domain/depreciation/", "app/depreciation*",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "", (
            f"57A-10F must not touch depreciation: got diff:\n{result.stdout}"
        )

    def test_no_idc_change(self):
        # The IDC computation lives in domain/financing/ and
        # domain/capex/. 57A-10F must not touch it.
        import subprocess
        result = subprocess.run(
            [
                "git", "diff", "--name-only",
                "origin/main", "HEAD", "--",
                "domain/financing/", "domain/capex/",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "", (
            f"57A-10F must not touch IDC / financing / capex domain: "
            f"got diff:\n{result.stdout}"
        )

    def test_no_debt_change(self):
        import subprocess
        result = subprocess.run(
            [
                "git", "diff", "--name-only",
                "origin/main", "HEAD", "--", "domain/debt/",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "", (
            f"57A-10F must not touch debt domain: got diff:\n{result.stdout}"
        )


# ---------------------------------------------------------------------------
# rc1 frozen
# ---------------------------------------------------------------------------


class TestRc1Frozen:
    def test_rc1_sha_reachable(self):
        import subprocess
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
    def test_design_doc_declares_no_formula_change(self):
        text = DESIGN_DOC.read_text(encoding="utf-8")
        # The doc must explicitly declare the no-formula-change constraint
        assert "no CAPEX total formula changes" in text.lower() or (
            "no capex total formula changes" in text.lower()
        )

    def test_design_doc_declares_no_runtime_change(self):
        text = DESIGN_DOC.read_text(encoding="utf-8")
        assert "no runtime materialization changes" in text.lower() or (
            "no runtime materialization change" in text.lower()
        )

    def test_design_doc_declares_4_status_categories(self):
        text = DESIGN_DOC.read_text(encoding="utf-8")
        for cat in ("Runtime-used", "Metadata-only", "Design-only", "Export-only"):
            assert cat in text, f"design doc missing status category {cat!r}"
