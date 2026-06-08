"""Phase 57A-10H - CAPEX UX Polish / Visual Review Cleanup tests.

This test file verifies that:
- Status legend (Phase 57A-10F) remains visible and uses
  consistent compact wording
- Metadata-only disclaimer remains visible and is **shortened
  to a single sentence** (no duplicate disclaimer body)
- Column groups guide (Phase 57A-10G) remains visible via
  `data-capex-column-groups="true"` (legacy attribute for
  backward compatibility)
- New unified "CAPEX column key" panel is present with two
  sections (status + groups) and 8 total entries
- Softened palette: detail grid group headers use lighter
  background hex codes; the "meta" group is no longer pure green
- All 57A-10F and 57A-10G surfaces are preserved
- No template syntax error (no UndefinedError / NameError /
  AttributeError)
- No CAPEX total change (no `_CAPEX_ITEM_FIELDS` tuple change,
  no `CapexItem` dataclass field change)
- No forbidden-path changes (no domain / persistence / main_web /
  main_api / static / tax / depreciation / debt changes)
- No `app/excel_export.py` changes
- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` is reachable

The tests are render / context / safety only. They do NOT touch
model calculations.
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
    REPO_ROOT
    / "docs"
    / "phase57a10h_capex_ux_polish_visual_review_cleanup.md"
)
REPORT_JSON = (
    REPO_ROOT
    / "reports"
    / "phase57a10h_capex_ux_polish_visual_review_cleanup.json"
)


# Softened palette (post-57A-10H) for detail group headers.
SOFTENED_PALETTE = {
    "core": "#e6eff7",
    "costing": "#ece4f4",
    "tax": "#f5e7da",
    "meta": "#e4ede6",
    "schedule": "#f4eed4",
}


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
# 57A-10F and 57A-10G surfaces preserved
# ---------------------------------------------------------------------------


class TestPhase10FAnd10GSurfacesPreserved:
    """The surfaces added by 57A-10F and 57A-10G must still be
    present and the data attributes that mark them must still
    exist (for test backward compatibility)."""

    def test_status_legend_visible(self, sheet_capex_html_text):
        assert 'data-capex-status-legend="true"' in sheet_capex_html_text

    def test_metadata_disclaimer_visible(self, sheet_capex_html_text):
        assert 'data-capex-metadata-disclaimer="true"' in sheet_capex_html_text

    def test_column_groups_data_attr_visible(
        self, sheet_capex_html_text
    ):
        # Legacy attribute from 57A-10G; preserved for test
        # backward compatibility. The new "column key" panel
        # also carries this attribute.
        assert 'data-capex-column-groups="true"' in sheet_capex_html_text

    def test_deferred_block_visible(self, sheet_capex_html_text):
        assert 'data-capex-deferred="true"' in sheet_capex_html_text

    def test_sources_uses_bridge_visible(self, sheet_capex_html_text):
        assert 'data-capex-su-bridge="true"' in sheet_capex_html_text

    def test_status_chips_on_detail_grid_preserved(
        self, sheet_capex_detail_html_text
    ):
        for attr in ("contingency", "VAT", "WHT"):
            pattern = (
                r'<span class="badge badge-metadata-only"[^>]*'
                r'data-capex-status="' + re.escape(attr)
                + r'"[^>]*>Metadata-only</span>'
            )
            assert re.search(pattern, sheet_capex_detail_html_text), (
                f"status chip for {attr!r} missing"
            )

    def test_column_group_header_row_preserved(
        self, sheet_capex_detail_html_text
    ):
        assert 'data-capex-column-groups="true"' in sheet_capex_detail_html_text
        assert 'fc-grid-header--groups' in sheet_capex_detail_html_text


# ---------------------------------------------------------------------------
# New unified "CAPEX column key" panel
# ---------------------------------------------------------------------------


class TestUnifiedColumnKeyPanel:
    """The new unified panel must have two sections (status +
    groups) and carry the legacy data-capex-column-groups attribute
    for backward compatibility."""

    def test_column_key_panel_present(self, sheet_capex_html_text):
        assert 'data-capex-column-key="true"' in sheet_capex_html_text

    def test_column_key_has_status_section(self, sheet_capex_html_text):
        assert (
            'data-capex-column-key-section="status"'
            in sheet_capex_html_text
        )

    def test_column_key_has_groups_section(self, sheet_capex_html_text):
        assert (
            'data-capex-column-key-section="groups"'
            in sheet_capex_html_text
        )

    def test_column_key_status_section_has_4_entries(
        self, sheet_capex_html_text
    ):
        match = re.search(
            r'data-capex-column-key-section="status"[^>]*>(.*?)'
            r'</div>\s*<div class="capex-column-key__section"',
            sheet_capex_html_text,
            re.DOTALL,
        )
        assert match, "status section block not found"
        block = match.group(1)
        li_count = len(re.findall(r'<li>', block))
        assert li_count == 4, (
            f"expected 4 status entries, got {li_count}"
        )

    def test_column_key_groups_section_has_4_entries(
        self, sheet_capex_html_text
    ):
        match = re.search(
            r'data-capex-column-key-section="groups"[^>]*>(.*?)'
            r'</div>\s*</div>',
            sheet_capex_html_text,
            re.DOTALL,
        )
        assert match, "groups section block not found"
        block = match.group(1)
        li_count = len(re.findall(r'<li\b', block))
        assert li_count == 4, (
            f"expected 4 group entries, got {li_count}"
        )

    @pytest.mark.parametrize(
        "chip_text",
        ["Runtime-used", "Metadata-only", "Design-only", "Export-only"],
    )
    def test_column_key_status_chip_present(
        self, sheet_capex_html_text, chip_text
    ):
        # Find the status section block and check the chip text
        match = re.search(
            r'data-capex-column-key-section="status"[^>]*>(.*?)'
            r'</div>\s*<div class="capex-column-key__section"',
            sheet_capex_html_text,
            re.DOTALL,
        )
        assert match
        block = match.group(1)
        assert chip_text in block, (
            f"status chip {chip_text!r} missing from column key panel"
        )

    @pytest.mark.parametrize(
        "group_name",
        ["core", "costing", "tax", "schedule"],
    )
    def test_column_key_group_present(
        self, sheet_capex_html_text, group_name
    ):
        match = re.search(
            r'data-capex-column-key-section="groups"[^>]*>(.*?)'
            r'</div>\s*</div>',
            sheet_capex_html_text,
            re.DOTALL,
        )
        assert match
        block = match.group(1)
        assert f'data-capex-group="{group_name}"' in block, (
            f"group {group_name!r} missing from column key panel"
        )

    def test_column_key_panel_carries_legacy_groups_attr(
        self, sheet_capex_html_text
    ):
        # The new column-key panel must also carry the legacy
        # data-capex-column-groups attribute for test backward
        # compatibility with 57A-10G.
        match = re.search(
            r'<div[^>]*class="capex-column-key"[^>]*>',
            sheet_capex_html_text,
        )
        assert match
        tag = match.group(0)
        assert 'data-capex-column-groups="true"' in tag, (
            "column key panel missing legacy data-capex-column-groups attr"
        )


# ---------------------------------------------------------------------------
# Disclaimer shortening
# ---------------------------------------------------------------------------


class TestDisclaimerShortened:
    """The deferred-note disclaimer must be a single short
    sentence. The old meta-narration ('The columns below are
    placeholders for now; detailed logic will be wired in a
    follow-up phase that does not change financial outputs') must
    be removed."""

    def test_old_meta_narration_removed(self, sheet_capex_html_text):
        # The old wording must be gone
        assert (
            "detailed logic will be wired in a follow-up phase"
            not in sheet_capex_html_text
        ), (
            "old meta-narration 'detailed logic will be wired' "
            "still present in sheet_capex.html"
        )

    def test_disclaimer_single_sentence(self, sheet_capex_html_text):
        # Find the disclaimer block
        match = re.search(
            r'<p class="capex-metadata-disclaimer"[^>]*>(.*?)</p>',
            sheet_capex_html_text,
            re.DOTALL,
        )
        assert match
        block = match.group(1)
        # Strip HTML tags
        text = re.sub(r'<[^>]+>', '', block).strip()
        # Should end with a single period
        assert text.endswith("calculations."), (
            f"disclaimer should end with 'calculations.', got: {text!r}"
        )
        # Should not contain "not yet wired" twice
        assert text.count("not yet wired") <= 0, (
            "disclaimer body still contains 'not yet wired' duplicate"
        )

    def test_disclaimer_badge_present(self, sheet_capex_html_text):
        # The badge is still there
        assert (
            "Metadata only — does not affect Run." in sheet_capex_html_text
        )


# ---------------------------------------------------------------------------
# Softened palette (detail grid)
# ---------------------------------------------------------------------------


class TestSoftenedPalette:
    """The detail grid group headers must use the softened palette."""

    @pytest.mark.parametrize(
        "group,hex_code", list(SOFTENED_PALETTE.items())
    )
    def test_softened_hex_present(
        self, sheet_capex_detail_html_text, group, hex_code
    ):
        pattern = (
            r'\.fc-capex-group-header\[data-capex-group="' + group
            + r'"\]\s*\{\s*background:\s*' + re.escape(hex_code)
        )
        assert re.search(pattern, sheet_capex_detail_html_text), (
            f"softened palette hex {hex_code!r} for group {group!r} "
            "missing from detail grid CSS"
        )

    def test_meta_no_longer_pure_green(
        self, sheet_capex_detail_html_text
    ):
        # The old meta group hex #eefbf0 was a saturated green
        assert "#eefbf0" not in sheet_capex_detail_html_text, (
            "old green meta palette still present"
        )


# ---------------------------------------------------------------------------
# Template syntax safety
# ---------------------------------------------------------------------------


class TestTemplateSyntaxSafety:
    """Templates must have no Jinja syntax errors."""

    def test_sheet_capex_html_parses(self, sheet_capex_html_text):
        from jinja2 import Environment
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
# No CAPEX total change
# ---------------------------------------------------------------------------


class TestNoCapexStructureChange:
    """The CAPEX item fields tuple in `domain/inputs.py:CapexStructure`
    must NOT be modified."""

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
    """57A-10H must not touch domain layer / persistence / engine /
    route / API / static. This is a sanity check, not a parity test."""

    FORBIDDEN = (
        "domain/",
        "app/persistence/",
        "main_web.py",
        "main_api.py",
        "static/",
        "app/excel_export.py",
    )

    @pytest.mark.parametrize("path", FORBIDDEN)
    def test_path_untouched(self, path):
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
            f"57A-10H must not touch {path}: got diff:\n{result.stdout}"
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
            f"57A-10H must not touch {path}: got diff:\n{result.stdout}"
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
    def test_design_doc_declares_no_new_concepts(self):
        text = DESIGN_DOC.read_text(encoding="utf-8")
        assert "no new concepts" in text.lower()

    def test_design_doc_declares_no_new_columns(self):
        text = DESIGN_DOC.read_text(encoding="utf-8")
        assert "no new columns" in text.lower()

    def test_design_doc_declares_no_taxonomy_changes(self):
        text = DESIGN_DOC.read_text(encoding="utf-8")
        assert "no status taxonomy changes" in text.lower()
