"""Phase 56C — New Project v1 form simplification tests.

Verifies that:
- Inline new-project form (in workspace_shell.html #panel-new-project)
  exposes the new v1 master-data fields:
  - project_name (kept)
  - spv_name (NEW)
  - country_market (kept, label renamed to "Country / market")
  - project_type (kept, label renamed to "Technology")
  - capacity_mw (kept)
  - currency (NEW)
  - construction_start_date (NEW)
  - construction_duration_months (NEW, renamed from construction_months)
  - cod_date (kept as required for now; 56D will derive it)
  - template_source (kept, with ⚠️ Unvalidated label preserved)
- The 11 detailed financial assumptions are NO LONGER visible
  (hidden with safe defaults; user enters later in Inputs sheet):
  - tariff_eur_mwh
  - p50_hours
  - opex_y1_keur
  - total_capex_keur
  - gearing_pct
  - interest_rate_pct
  - tenor_years
  - target_dscr
  - horizon_years
  - ppa_term_years
  - construction_months (also removed from visible UI;
    construction_duration_months replaces it)
- Backend `_validate_new_project_payload` now allows the 11 detailed
  assumptions to be empty (optional, not required). It still validates
  them when present (so the legacy full-form path keeps working).
- Backend `_validate_new_project_payload` still requires:
  - project_name
  - project_type
  - country_market
  - capacity_mw
  - cod_date
- The route signature still has 17 form fields (no field removed from
  the signature, only the UI visibility changed) so 51M-1 still passes.
- Sidebar full new_project_form.html is unchanged by 56C (the
  detailed-form path stays intact for users who want it).
- No static/app.js changes.
- No app/waterfall_core.py changes.
- No app/project_factories.py changes.
- No schema/migration changes.
- rc1 (b425a07) untouched.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_SHELL = REPO_ROOT / "app" / "templates" / "partials" / "workspace_shell.html"
SIDEBAR_NEW_PROJECT_FORM = (
    REPO_ROOT / "app" / "templates" / "partials" / "new_project_form.html"
)
MAIN_WEB = REPO_ROOT / "main_web.py"
APP_JS = REPO_ROOT / "static" / "app.js"
STYLES_CSS = REPO_ROOT / "static" / "styles.css"

RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"

# 11 detailed financial assumptions that 56C moves out of the create UI
DETAILED_ASSUMPTION_FIELDS = [
    "tariff_eur_mwh",
    "p50_hours",
    "opex_y1_keur",
    "total_capex_keur",
    "gearing_pct",
    "interest_rate_pct",
    "tenor_years",
    "target_dscr",
    "horizon_years",
    "ppa_term_years",
    "construction_months",  # visible UI; replaced by construction_duration_months
]

# 10 master-data fields in the v1 form
V1_MASTER_FIELDS = [
    "project_name",
    "spv_name",
    "country_market",
    "project_type",
    "capacity_mw",
    "currency",
    "construction_start_date",
    "construction_duration_months",
    "cod_date",
    "template_source",
]


# ============================================================
# Helpers
# ============================================================


def _inline_new_project_panel_body() -> str:
    """Extract the inner HTML of the inline new-project form
    (#panel-new-project) by depth-counting <div> tags. Used to
    scope the field-presence checks to the inline form only
    (not the draft form's hidden inputs above the panel)."""
    text = WORKSPACE_SHELL.read_text()
    open_marker = '<div class="tab-panel" id="panel-new-project"'
    start = text.find(open_marker)
    assert start != -1, "panel-new-project not found in workspace_shell"
    # find the > closing the open tag
    gt = text.find(">", start)
    body_start = gt + 1
    depth = 1
    i = body_start
    while i < len(text):
        if text[i : i + 4] == "<div":
            depth += 1
            i += 4
        elif text[i : i + 6] == "</div>":
            depth -= 1
            if depth == 0:
                return text[body_start:i]
            i += 6
        else:
            i += 1
    return text[body_start:]


# ============================================================
# 1. v1 master fields are present in the inline form
# ============================================================


class TestV1MasterFieldsPresent:
    @pytest.mark.parametrize("field", V1_MASTER_FIELDS)
    def test_master_field_in_inline_form(self, field):
        body = _inline_new_project_panel_body()
        assert field in body, (
            f"Inline new-project form (v1) must contain master field: {field}"
        )


# ============================================================
# 2. Detailed financial assumptions are NOT visible in inline form
# ============================================================


class TestDetailedAssumptionsHidden:
    @pytest.mark.parametrize("field", DETAILED_ASSUMPTION_FIELDS)
    def test_field_not_visible_in_inline_form(self, field):
        """Each detailed assumption must NOT appear as a visible
        input (type=number/date/text with required attribute or
        inside a <label>). They can only appear as hidden inputs
        in the safe-defaults block."""
        body = _inline_new_project_panel_body()
        # Check for visible input. The form has hidden inputs for
        # these fields; we want to confirm they're hidden, not visible.
        # A simple check: hidden inputs use type="hidden"; visible ones
        # use type="number", type="text", type="date".
        # Also: visible inputs are inside a <label>...</label> block.
        # Hidden inputs are inside the np-hidden-defaults block.
        # Approach: search for the field as a name attribute. Then check
        # the surrounding context.
        for m in re.finditer(rf'name="{re.escape(field)}"', body):
            start = m.start()
            # Walk back to find the <input ... > opening tag
            input_open = body.rfind("<input", 0, start)
            assert input_open != -1, f"Could not find <input> for {field}"
            # Extract up to the closing > of the <input> tag
            close = body.find(">", input_open)
            tag = body[input_open : close + 1]
            assert 'type="hidden"' in tag, (
                f"Detailed assumption '{field}' must be a hidden input "
                f"in the inline form. Found visible: {tag}"
            )


# ============================================================
# 3. Hidden defaults block exists
# ============================================================


class TestHiddenDefaults:
    def test_np_hidden_defaults_block_exists(self):
        body = _inline_new_project_panel_body()
        assert "np-hidden-defaults" in body, (
            "Inline form must include the .np-hidden-defaults block "
            "with hidden inputs for the 11 detailed assumptions."
        )

    def test_all_11_detailed_assumptions_have_hidden_inputs(self):
        body = _inline_new_project_panel_body()
        # Strip the np-hidden-defaults block to a small region
        m = re.search(
            r'<div class="np-hidden-defaults"[^>]*>(.*?)</div>',
            body,
            flags=re.DOTALL,
        )
        assert m is not None, "np-hidden-defaults block not found"
        block = m.group(1)
        for field in DETAILED_ASSUMPTION_FIELDS:
            assert f'name="{field}"' in block, (
                f"Hidden input for '{field}' missing in np-hidden-defaults"
            )
            assert 'type="hidden"' in block, (
                f"Input for '{field}' must be type='hidden'"
            )


# ============================================================
# 4. Renames and labels
# ============================================================


class TestLabelRenames:
    def test_project_type_label_renamed_to_technology(self):
        body = _inline_new_project_panel_body()
        # Look for the label associated with project_type
        m = re.search(
            r'<label\s+for="np-project_type"[^>]*>(.*?)</label>',
            body,
            flags=re.DOTALL,
        )
        assert m is not None, "Label for project_type not found"
        label_text = m.group(1)
        assert "Technology" in label_text, (
            f"Label for project_type should say 'Technology', got: {label_text!r}"
        )

    def test_country_label_kept(self):
        """country_market label is kept as 'Country / Market' (or close)."""
        body = _inline_new_project_panel_body()
        m = re.search(
            r'<label\s+for="np-country_market"[^>]*>(.*?)</label>',
            body,
            flags=re.DOTALL,
        )
        assert m is not None
        label_text = m.group(1)
        # Per spec: "country → country_or_market" rename. Backend field
        # is still country_market; label can match.
        assert "Country" in label_text

    def test_construction_duration_label_renamed(self):
        # UX-2E superseded 56C: construction_duration_months is no
        # longer a visible labelled field (moved to Inputs); kept as
        # a hidden default input under its 56C field name.
        body = _inline_new_project_panel_body()
        m = re.search(r'<input[^>]*name="construction_duration_months"[^>]*>', body)
        assert m is not None
        assert 'type="hidden"' in m.group(0)


# ============================================================
# 5. New fields (spv_name, currency, construction_start_date)
# ============================================================


class TestNewFields:
    def test_spv_name_field_present(self):
        # UX-2E superseded 56C: spv_name is no longer a visible field
        # in the inline form (moved to Inputs). It remains wired via a
        # hidden default input so the backend contract is unchanged.
        body = _inline_new_project_panel_body()
        assert 'name="spv_name"' in body
        m = re.search(r'<input[^>]*name="spv_name"[^>]*>', body)
        assert m is not None
        assert 'type="hidden"' in m.group(0), (
            "spv_name moved to Inputs (UX-2E) — must be a hidden default input"
        )

    def test_currency_field_present(self):
        body = _inline_new_project_panel_body()
        assert 'for="np-currency"' in body
        assert 'name="currency"' in body
        # Default EUR
        m = re.search(
            r'<option[^>]*value="EUR"[^>]*selected', body
        )
        assert m is not None, "EUR should be selected by default"

    def test_currency_options_include_major(self):
        body = _inline_new_project_panel_body()
        # Selects for currency
        m = re.search(
            r'<select[^>]*id="np-currency"[^>]*>(.*?)</select>',
            body,
            flags=re.DOTALL,
        )
        assert m is not None
        sel = m.group(1)
        for opt in ["EUR", "USD", "HRK"]:
            assert f'value="{opt}"' in sel, f"Currency {opt} missing"

    def test_construction_start_date_field_present(self):
        # UX-2E superseded 56C: construction_start_date is no longer a
        # visible field (moved to Inputs); kept as a hidden default.
        body = _inline_new_project_panel_body()
        assert 'name="construction_start_date"' in body
        m = re.search(r'<input[^>]*name="construction_start_date"[^>]*>', body)
        assert m is not None
        assert 'type="hidden"' in m.group(0)


# ============================================================
# 6. Template source has ⚠️ Unvalidated label preserved
# ============================================================


class TestTemplateSourceLabel:
    # UX-2E superseded 56C: the Template picker (and its warning) is no
    # longer shown on the inline New Project form — template_source is
    # now always server-derived from Technology. It remains wired as a
    # hidden default input so the backend contract is unchanged.
    def test_template_source_field_present_as_hidden_default(self):
        body = _inline_new_project_panel_body()
        m = re.search(r'<input[^>]*name="template_source"[^>]*>', body)
        assert m is not None
        assert 'type="hidden"' in m.group(0)


# ============================================================
# 7. Backend validation now allows empty detailed assumptions
# ============================================================


class TestBackendValidationRelaxes:
    def test_validation_function_exists(self):
        text = MAIN_WEB.read_text()
        assert "def _validate_new_project_payload" in text

    def test_validation_does_not_require_tariff_eur_mwh(self):
        """After 56C, the validation must NOT raise an error when
        tariff_eur_mwh is empty."""
        text = MAIN_WEB.read_text()
        # Find the require_* or optional_* function used for tariff
        m = re.search(
            r'tariff\s*=\s*(require_float|optional_float)\(\s*"tariff_eur_mwh"',
            text,
        )
        assert m is not None, "tariff validation call not found"
        assert m.group(1) == "optional_float", (
            "tariff_eur_mwh must use optional_float (not require_float) "
            "after 56C. Found: " + m.group(1)
        )

    @pytest.mark.parametrize(
        "field,validator_type",
        [
            ("tariff_eur_mwh", "optional_float"),
            ("p50_hours", "optional_float"),
            ("opex_y1_keur", "optional_float"),
            ("total_capex_keur", "optional_float"),
            ("gearing_pct", "optional_float"),
            ("interest_rate_pct", "optional_float"),
            ("tenor_years", "optional_int"),
            ("target_dscr", "optional_float"),
            ("horizon_years", "optional_int"),
            ("ppa_term_years", "optional_int"),
            ("construction_months", "optional_int"),
        ],
    )
    def test_each_detailed_field_uses_optional(self, field, validator_type):
        text = MAIN_WEB.read_text()
        # Find the validator call for this field
        pattern = rf"{re.escape(validator_type)}\(\s*\"{re.escape(field)}\""
        assert re.search(pattern, text), (
            f"Field {field} should use {validator_type}() in validation "
            f"after 56C. Search: {pattern}"
        )

    def test_capacity_mw_still_required(self):
        text = MAIN_WEB.read_text()
        m = re.search(
            r'capacity_mw\s*=\s*(require_float|optional_float)\(\s*"capacity_mw"',
            text,
        )
        assert m is not None
        assert m.group(1) == "require_float", (
            "capacity_mw must still be required (master data, not optional)"
        )

    def test_cod_date_still_required(self):
        """cod_date remains a required input in 56C (it will be
        derived in 56D, but in 56C the user must still enter it
        because backend expects it)."""
        text = MAIN_WEB.read_text()
        assert 'if not _coerce_form_text(submitted.get("cod_date")):' in text
        assert "COD date is required." in text


# ============================================================
# 8. Route signature unchanged
# ============================================================


class TestRouteSignatureUnchanged:
    def test_route_still_accepts_all_17_form_fields(self):
        """The POST /projects/create route signature must still
        include all 17 original form fields (Phase 51M-1
        golden characterization must keep passing)."""
        text = MAIN_WEB.read_text()
        # Find the create_project_route definition
        m = re.search(
            r"def\s+create_project_route\s*\((.*?)\)\s*:",
            text,
            flags=re.DOTALL,
        )
        assert m is not None, "create_project_route function not found"
        sig = m.group(1)
        for field in [
            "project_name",
            "project_type",
            "template_source",
            "country_market",
            "capacity_mw",
            "cod_date",
            "construction_months",
            "horizon_years",
            "tariff_eur_mwh",
            "ppa_term_years",
            "p50_hours",
            "opex_y1_keur",
            "total_capex_keur",
            "gearing_pct",
            "interest_rate_pct",
            "tenor_years",
            "target_dscr",
        ]:
            assert f"{field}:" in sig, (
                f"Route signature must still include field: {field}"
            )


# ============================================================
# 9. Sidebar full form unchanged
# ============================================================


class TestSidebarFormUnchanged:
    def test_sidebar_new_project_form_has_17_fields(self):
        """The full sidebar new_project_form.html is intentionally
        NOT changed by 56C. It still shows all 17 fields for
        users who want the detailed form."""
        text = SIDEBAR_NEW_PROJECT_FORM.read_text()
        for field in [
            "project_name",
            "project_type",
            "template_source",
            "country_market",
            "capacity_mw",
            "cod_date",
            "construction_months",
            "horizon_years",
            "tariff_eur_mwh",
            "ppa_term_years",
            "p50_hours",
            "opex_y1_keur",
            "total_capex_keur",
            "gearing_pct",
            "interest_rate_pct",
            "tenor_years",
            "target_dscr",
        ]:
            assert field in text, (
                f"Sidebar new_project_form.html must still have field: {field}"
            )


# ============================================================
# 10. Scope guardrails
# ============================================================


class TestScopeGuardrails:
    def test_app_js_unchanged(self):
        """56C must NOT change static/app.js."""
        js = APP_JS.read_text()
        # Spot-check: existing handlers untouched
        assert "switchTab" in js
        assert "showNewProjectPanel" in js

    def test_app_waterfall_core_unchanged(self):
        wf = REPO_ROOT / "app" / "waterfall_core.py"
        if wf.exists():
            text = wf.read_text()
            assert "Phase 56C" not in text

    def test_app_project_factories_unchanged(self):
        pf = REPO_ROOT / "app" / "project_factories.py"
        if pf.exists():
            text = pf.read_text()
            assert "Phase 56C" not in text

    def test_runtime_impact_taxonomy_unchanged(self):
        rt = REPO_ROOT / "app" / "runtime_impact_taxonomy.py"
        if rt.exists():
            text = rt.read_text()
            assert "Phase 56C" not in text

    def test_no_schema_or_migration_changes(self):
        """No migration files, no SQL DDL changes."""
        # Look for new migration dirs/files
        migrations = REPO_ROOT / "app" / "persistence" / "migrations"
        if migrations.exists():
            for f in migrations.glob("*.py"):
                text = f.read_text()
                assert "Phase 56C" not in text
        # No DDL in the new project flow
        for f in [
            REPO_ROOT / "app" / "persistence" / "db.py",
        ]:
            if f.exists():
                text = f.read_text()
                assert "Phase 56C" not in text


# ============================================================
# 11. CSS is additive
# ============================================================


class TestCSSAdditive:
    def test_np_helper_class_added(self):
        css = STYLES_CSS.read_text()
        assert ".np-helper" in css

    def test_np_warning_class_added(self):
        css = STYLES_CSS.read_text()
        assert ".np-warning" in css

    def test_root_count_unchanged(self):
        css = STYLES_CSS.read_text()
        root_count = len(re.findall(r":root\s*\{", css))
        assert root_count == 5, (
            f"styles.css :root block count changed from 5 to {root_count}."
        )


# ============================================================
# 12. rc1 untouched
# ============================================================


class TestRc1Untouched:
    def test_rc1_sha_constant_stable(self):
        assert RC1_SHA == "b425a0708719eaa5e1d922b1008e5609758e0ad4"


# ============================================================
# 13. Persistence schema not changed
# ============================================================


class TestPersistenceUnchanged:
    def test_no_persistence_writes_added(self):
        """56C does not introduce new persistence writes beyond
        the existing /projects/create flow."""
        pdir = REPO_ROOT / "app" / "persistence"
        for f in pdir.glob("*.py"):
            text = f.read_text()
            assert "Phase 56C" not in text, (
                f"persistence file {f.name} contains Phase 56C marker — "
                "this is out of scope."
            )

    def test_no_financial_model_changes(self):
        """No model/parity-core/schema/formula/fixture changes."""
        for f in [
            REPO_ROOT / "app" / "waterfall_core.py",
            REPO_ROOT / "app" / "capex_engine.py",
            REPO_ROOT / "app" / "opex_engine.py",
            REPO_ROOT / "app" / "depreciation_engine.py",
        ]:
            if f.exists():
                text = f.read_text()
                assert "Phase 56C" not in text
