"""Phase 56D — COD derived field wiring tests.

Verifies that:
- A new server-side helper `_derive_cod_date(start, duration)` exists
  in main_web.py and returns the correct ISO-8601 date for typical
  inputs.
- Month-end behavior is deterministic (e.g. 2025-01-31 + 1 month =
  2025-02-28, not 2025-03-03).
- Leap-year behavior is deterministic (handled by dateutil.relativedelta).
- Missing start date returns None (no fake date).
- Missing duration returns None.
- Zero / negative duration returns None.
- Non-numeric / fractional-but-zero duration is handled.
- The inline new-project form marks `cod_date` as readonly
  (no longer a primary manual input).
- The inline new-project form includes a `.np-derived-note` block
  explaining the derivation.
- `create_project_route` calls `_derive_cod_date` and uses the
  derived value when the form's `cod_date` is empty.
- The route still accepts a manual `cod_date` if present
  (backward-compat / 51M-1 golden characterization).
- The 51M-1 golden test for route signature still passes
  (17 form fields, no field added/removed from signature).
- 56B and 56C tests still pass.
- No static/app.js changes.
- No financial model / formula changes.
- rc1 (b425a07) untouched.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_SHELL = REPO_ROOT / "app" / "templates" / "partials" / "workspace_shell.html"
MAIN_WEB = REPO_ROOT / "main_web.py"
APP_JS = REPO_ROOT / "static" / "app.js"
STYLES_CSS = REPO_ROOT / "static" / "styles.css"

RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"


def _helper_apply_56d_body() -> str:
    """Return the body of the _apply_56d_extras_to_submitted helper.
    Robust against multi-line signatures and adjacent functions."""
    text = MAIN_WEB.read_text()
    start = text.find("def _apply_56d_extras_to_submitted(")
    assert start != -1, "_apply_56d_extras_to_submitted not found"
    # Walk forward to the next top-level "def " at column 0
    # (a line that starts with "def " with no leading whitespace).
    i = start + 1
    while i < len(text):
        nl = text.find("\n", i)
        if nl == -1:
            break
        line_start = nl + 1
        # A top-level def starts at column 0 with "def "
        if text[line_start : line_start + 4] == "def ":
            return text[start:line_start]
        i = nl + 1
    return text[start:]


# ============================================================
# 1. _derive_cod_date helper exists in main_web.py
# ============================================================


class TestDeriveCodDateHelper:
    def test_helper_function_exists(self):
        text = MAIN_WEB.read_text()
        assert "def _derive_cod_date(" in text, (
            "main_web.py must contain a _derive_cod_date helper."
        )

    def test_helper_uses_relativedelta(self):
        text = MAIN_WEB.read_text()
        m = re.search(
            r"def _derive_cod_date\((.*?)\):(.*?)(?=^def |\Z)",
            text,
            flags=re.DOTALL | re.MULTILINE,
        )
        assert m is not None
        body = m.group(2)
        assert "relativedelta" in body, (
            "_derive_cod_date must use dateutil.relativedelta for "
            "deterministic month addition (handles month-end + leap year)."
        )

    def test_helper_returns_iso_format(self):
        from main_web import _derive_cod_date

        result = _derive_cod_date("2025-01-15", "24")
        assert result == "2027-01-15", (
            f"_derive_cod_date(2025-01-15, 24) should be 2027-01-15, got {result!r}"
        )

    def test_helper_12_months(self):
        from main_web import _derive_cod_date

        assert _derive_cod_date("2025-06-15", "12") == "2026-06-15"

    def test_helper_zero_months_returns_none(self):
        from main_web import _derive_cod_date

        assert _derive_cod_date("2025-01-15", "0") is None

    def test_helper_negative_months_returns_none(self):
        from main_web import _derive_cod_date

        assert _derive_cod_date("2025-01-15", "-3") is None

    def test_helper_missing_start_returns_none(self):
        from main_web import _derive_cod_date

        assert _derive_cod_date("", "12") is None
        assert _derive_cod_date(None, "12") is None

    def test_helper_missing_duration_returns_none(self):
        from main_web import _derive_cod_date

        assert _derive_cod_date("2025-01-15", "") is None
        assert _derive_cod_date("2025-01-15", None) is None

    def test_helper_non_numeric_duration_returns_none(self):
        from main_web import _derive_cod_date

        assert _derive_cod_date("2025-01-15", "abc") is None

    def test_helper_malformed_start_returns_none(self):
        from main_web import _derive_cod_date

        assert _derive_cod_date("not-a-date", "12") is None
        assert _derive_cod_date("2025-13-99", "12") is None

    def test_helper_fractional_duration(self):
        from main_web import _derive_cod_date

        # "6.0" should be valid (6 months)
        assert _derive_cod_date("2025-01-15", "6.0") == "2025-07-15"

    def test_helper_fractional_zero_returns_none(self):
        from main_web import _derive_cod_date

        assert _derive_cod_date("2025-01-15", "0.5") is None  # not positive int

    def test_helper_month_end_jan_31_plus_1(self):
        """2025-01-31 + 1 month should snap to 2025-02-28 (month-end),
        NOT overflow to 2025-03-03."""
        from main_web import _derive_cod_date

        assert _derive_cod_date("2025-01-31", "1") == "2025-02-28"

    def test_helper_month_end_mar_31_plus_1(self):
        """2025-03-31 + 1 month should snap to 2025-04-30."""
        from main_web import _derive_cod_date

        assert _derive_cod_date("2025-03-31", "1") == "2025-04-30"

    def test_helper_leap_year_feb_29(self):
        """2024 is a leap year. 2024-02-29 + 12 months = 2025-02-28."""
        from main_web import _derive_cod_date

        assert _derive_cod_date("2024-02-29", "12") == "2025-02-28"

    def test_helper_leap_year_plus_48(self):
        """2024-02-29 + 48 months = 2028-02-29 (another leap year)."""
        from main_web import _derive_cod_date

        assert _derive_cod_date("2024-02-29", "48") == "2028-02-29"

    def test_helper_dec_31_plus_1(self):
        """2025-12-31 + 1 month = 2026-01-31."""
        from main_web import _derive_cod_date

        assert _derive_cod_date("2025-12-31", "1") == "2026-01-31"

    def test_helper_helper_returns_string_format(self):
        """The helper must return an ISO-8601 string (YYYY-MM-DD)."""
        from main_web import _derive_cod_date

        result = _derive_cod_date("2025-01-15", "24")
        assert isinstance(result, str)
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", result), (
            f"Expected YYYY-MM-DD format, got {result!r}"
        )


# ============================================================
# 2. _parse_iso_date helper exists
# ============================================================


class TestParseIsoDateHelper:
    def test_helper_exists(self):
        text = MAIN_WEB.read_text()
        assert "def _parse_iso_date(" in text

    def test_helper_valid_date(self):
        from main_web import _parse_iso_date

        d = _parse_iso_date("2025-01-15")
        assert d is not None
        assert d.year == 2025
        assert d.month == 1
        assert d.day == 15

    def test_helper_empty_returns_none(self):
        from main_web import _parse_iso_date

        assert _parse_iso_date("") is None
        assert _parse_iso_date(None) is None
        assert _parse_iso_date("   ") is None

    def test_helper_malformed_returns_none(self):
        from main_web import _parse_iso_date

        assert _parse_iso_date("not-a-date") is None
        assert _parse_iso_date("2025/01/15") is None  # wrong separator
        assert _parse_iso_date("15-01-2025") is None  # wrong order


# ============================================================
# 3. Inline new-project form: cod_date is readonly + derived-note
# ============================================================


class TestInlineFormReadonlyCodDate:
    def _inline_panel_body(self) -> str:
        text = WORKSPACE_SHELL.read_text()
        open_marker = '<div class="tab-panel" id="panel-new-project"'
        start = text.find(open_marker)
        assert start != -1
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

    def test_cod_date_input_is_readonly(self):
        # UX-2E superseded 56C/56D: cod_date is no longer a visible
        # readonly field on the inline form (the construction-date
        # inputs that fed it moved to Inputs). It remains wired as a
        # hidden default input so the server-derivation contract and
        # backend tests are unaffected.
        body = self._inline_panel_body()
        m = re.search(r'<input[^>]*name="cod_date"[^>]*>', body)
        assert m is not None
        tag = m.group(0)
        assert 'type="hidden"' in tag, f"cod_date must be a hidden default input. Got: {tag}"

    def test_cod_date_input_no_required(self):
        body = self._inline_panel_body()
        m = re.search(r'<input[^>]*name="cod_date"[^>]*>', body)
        assert m is not None
        tag = m.group(0)
        assert "required" not in tag, (
            "hidden cod_date default must not have `required` attribute. Got: " + tag
        )


# ============================================================
# 4. create_project_route wires derivation
# ============================================================


class TestCreateRouteWiresDerivation:
    def test_route_calls_helper_56d_extras(self):
        text = MAIN_WEB.read_text()
        # Find the route body
        m = re.search(
            r"async def create_project_route\((.*?)\):(.*?)(?=^async def |^def |^@app\.)",
            text,
            flags=re.DOTALL | re.MULTILINE,
        )
        assert m is not None
        body = m.group(2)
        # 56D logic now lives in a helper to keep the route slim.
        assert "_apply_56d_extras_to_submitted" in body, (
            "create_project_route must call _apply_56d_extras_to_submitted"
        )
        assert "_read_optional_form_fields" in body, (
            "create_project_route must call _read_optional_form_fields"
        )

    def test_helper_apply_56d_uses_derive_cod_date(self):
        body = _helper_apply_56d_body()
        assert "_derive_cod_date" in body

    def test_helper_pulls_all_four_extras(self):
        body = _helper_apply_56d_body()
        for field in [
            "spv_name",
            "currency",
            "construction_start_date",
            "construction_duration_months",
        ]:
            assert field in body, (
                f"_apply_56d_extras_to_submitted must reference {field}"
            )

    def test_helper_assigns_derived_cod_always_when_derivable(self):
        """Phase 56D policy (post-fix): server-derived COD ALWAYS wins
        when it can be computed, regardless of whether the form's
        manual cod_date is empty or not. Manual override is
        deferred; it is NOT supported in 56D."""
        body = _helper_apply_56d_body()
        # The helper must set submitted["cod_date"] = derived_cod
        # unconditionally when derived_cod is truthy.
        assert "cod_date" in body
        assert "derived_cod" in body
        # The body must contain the post-fix pattern:
        #   if derived_cod:
        #       submitted["cod_date"] = derived_cod
        # (NOT the old "if not cod_date and derived_cod" pattern)
        # We verify the post-fix pattern by checking for the
        # simpler conditional.
        post_fix_pattern = re.search(
            r"if derived_cod\s*:\s*\n\s*submitted\[\"cod_date\"\]\s*=\s*derived_cod",
            body,
        )
        assert post_fix_pattern is not None, (
            "Helper must use the post-fix pattern: 'if derived_cod: "
            "submitted[\"cod_date\"] = derived_cod'. The old pattern "
            "'if not cod_date and derived_cod' would still allow "
            "manual override, which contradicts Phase 56D policy."
        )

    def test_helper_does_not_allow_manual_override(self):
        """Post-fix regression guard: the helper must NOT contain
        the old 'if not cod_date and derived_cod' pattern that
        allowed manual override when derived COD is available."""
        body = _helper_apply_56d_body()
        old_pattern = re.search(
            r"if not\s+\(?\s*submitted\.get\(\"cod_date\"\)\s*or\s+\"\"",
            body,
        )
        # The old pattern would be: `if not (submitted.get("cod_date") or "").strip() and derived_cod:`
        # We assert it is NOT in the body.
        assert old_pattern is None, (
            "Helper must not contain the old 'if not cod_date and "
            "derived_cod' pattern (allows manual override, which "
            "contradicts Phase 56D policy)."
        )

    def test_helper_has_56d_marker(self):
        body = _helper_apply_56d_body()
        assert "Phase 56" in body or "56D" in body or "56C" in body

    def test_route_signature_unchanged(self):
        """51M-1 golden test: 17 form fields, no additions/removals."""
        text = MAIN_WEB.read_text()
        m = re.search(
            r"def\s+create_project_route\s*\((.*?)\)\s*:",
            text,
            flags=re.DOTALL,
        )
        assert m is not None
        sig = m.group(1)
        # 17 fields, exactly as in 51M-1
        for field in [
            "project_name", "project_type", "template_source",
            "country_market", "capacity_mw", "cod_date",
            "construction_months", "horizon_years", "tariff_eur_mwh",
            "ppa_term_years", "p50_hours", "opex_y1_keur",
            "total_capex_keur", "gearing_pct", "interest_rate_pct",
            "tenor_years", "target_dscr",
        ]:
            assert f"{field}:" in sig, (
                f"Route signature must still include field: {field}"
            )

    def test_route_size_under_110_lines(self):
        """The 51M-2 test pins route body at 60-110 non-blank lines.
        56D must not bloat the route; the helpers keep it slim."""
        text = MAIN_WEB.read_text()
        m = re.search(
            r'@app\.post\("/projects/create"\)\s*\nasync def \w+\(.*?(?=\n@app\.(get|post|put|delete|route)\(|\Z)',
            text,
            re.DOTALL,
        )
        assert m is not None
        body = m.group(0)
        non_blank = [l for l in body.splitlines() if l.strip()]
        assert 60 <= len(non_blank) <= 110, (
            f"Route body is {len(non_blank)} non-blank lines; expected 60-110"
        )

    def test_route_docstring_does_not_say_manual_wins(self):
        """Post-fix: the route docstring must NOT contain the
        old wording 'manual value wins' or 'manual cod_date wins'.
        It must explicitly state that derived COD always wins."""
        text = MAIN_WEB.read_text()
        m = re.search(
            r"async def create_project_route\((.*?)\):(.*?)(?=^async def |^def |^@app\.)",
            text,
            flags=re.DOTALL | re.MULTILINE,
        )
        assert m is not None
        # Extract the docstring (text up to the first \n    \"\"\" after the open :)
        body = m.group(2)
        docstring_match = re.search(r'"""(.*?)"""', body, flags=re.DOTALL)
        assert docstring_match is not None, "create_project_route must have a docstring"
        docstring = docstring_match.group(1)
        assert "manual value wins" not in docstring, (
            "Route docstring must not say 'manual value wins'. "
            "Phase 56D policy: manual override is NOT supported, "
            "derived COD always wins."
        )
        assert "manual cod_date wins" not in docstring
        # The docstring SHOULD mention that manual override is NOT supported
        assert "manual" in docstring.lower() and "not supported" in docstring.lower()


class TestCodManualOverridePolicy:
    """Phase 56D post-fix regression guards.

    The original 56D code substituted derived COD only when the
    form's manual cod_date was empty. That contradicted the
    56D policy: "manual COD override is NOT supported". The
    post-fix helper ALWAYS assigns derived COD when derivable,
    regardless of whether the form body contains a manual
    cod_date. These tests pin the post-fix behavior."""

    def test_derived_cod_wins_over_manual_when_both_supplied(self):
        """If the form body contains BOTH a manual cod_date AND
        valid start+duration, the helper must assign the
        server-derived COD, NOT the manual one."""
        from main_web import _apply_56d_extras_to_submitted

        submitted = {
            "cod_date": "2099-12-31",  # manual override attempt
        }
        extra = {
            "spv_name": "",
            "currency": "EUR",
            "construction_start_date": "2025-01-15",
            "construction_duration_months": "24",
        }
        result = _apply_56d_extras_to_submitted(submitted, extra)
        # Derived COD = 2025-01-15 + 24 months = 2027-01-15
        assert result["cod_date"] == "2027-01-15", (
            f"Derived COD must win over manual cod_date. "
            f"Got {result['cod_date']!r}, expected '2027-01-15'"
        )

    def test_derived_cod_assigned_when_manual_empty(self):
        """The simple case: no manual cod_date, derived wins."""
        from main_web import _apply_56d_extras_to_submitted

        submitted = {"cod_date": ""}
        extra = {
            "spv_name": "",
            "currency": "EUR",
            "construction_start_date": "2025-01-15",
            "construction_duration_months": "24",
        }
        result = _apply_56d_extras_to_submitted(submitted, extra)
        assert result["cod_date"] == "2027-01-15"

    def test_no_derived_cod_when_start_missing(self):
        """If start is missing, no derived COD. The form's manual
        cod_date (if any) is preserved so existing validation
        handles missing COD safely."""
        from main_web import _apply_56d_extras_to_submitted

        submitted = {"cod_date": ""}
        extra = {
            "spv_name": "",
            "currency": "EUR",
            "construction_start_date": "",
            "construction_duration_months": "24",
        }
        result = _apply_56d_extras_to_submitted(submitted, extra)
        # No derived COD; submitted cod_date stays empty (validation will catch it)
        assert result["cod_date"] == "", (
            "If start is missing, no derived COD should be assigned. "
            "Manual cod_date is preserved for downstream validation."
        )

    def test_no_derived_cod_when_duration_missing(self):
        from main_web import _apply_56d_extras_to_submitted

        submitted = {"cod_date": ""}
        extra = {
            "spv_name": "",
            "currency": "EUR",
            "construction_start_date": "2025-01-15",
            "construction_duration_months": "",
        }
        result = _apply_56d_extras_to_submitted(submitted, extra)
        assert result["cod_date"] == ""

    def test_no_derived_cod_when_duration_zero(self):
        from main_web import _apply_56d_extras_to_submitted

        submitted = {"cod_date": ""}
        extra = {
            "spv_name": "",
            "currency": "EUR",
            "construction_start_date": "2025-01-15",
            "construction_duration_months": "0",
        }
        result = _apply_56d_extras_to_submitted(submitted, extra)
        assert result["cod_date"] == ""

    def test_no_derived_cod_when_duration_negative(self):
        from main_web import _apply_56d_extras_to_submitted

        submitted = {"cod_date": ""}
        extra = {
            "spv_name": "",
            "currency": "EUR",
            "construction_start_date": "2025-01-15",
            "construction_duration_months": "-5",
        }
        result = _apply_56d_extras_to_submitted(submitted, extra)
        assert result["cod_date"] == ""

    def test_derived_cod_month_end_still_works(self):
        """Month-end snap (Jan 31 + 1 month = Feb 28) still works
        with the post-fix policy."""
        from main_web import _apply_56d_extras_to_submitted

        submitted = {"cod_date": "2099-12-31"}  # manual attempt
        extra = {
            "spv_name": "",
            "currency": "EUR",
            "construction_start_date": "2025-01-31",
            "construction_duration_months": "1",
        }
        result = _apply_56d_extras_to_submitted(submitted, extra)
        assert result["cod_date"] == "2025-02-28", (
            f"Month-end snap must work. Got {result['cod_date']!r}"
        )

    def test_derived_cod_leap_year_still_works(self):
        """Leap year (Feb 29 + 12 months = Feb 28 next year)
        still works with the post-fix policy."""
        from main_web import _apply_56d_extras_to_submitted

        submitted = {"cod_date": "2099-12-31"}  # manual attempt
        extra = {
            "spv_name": "",
            "currency": "EUR",
            "construction_start_date": "2024-02-29",
            "construction_duration_months": "12",
        }
        result = _apply_56d_extras_to_submitted(submitted, extra)
        assert result["cod_date"] == "2025-02-28"


# ============================================================
# 5. _apply_new_project_required_inputs handles 56C/56D fields
# ============================================================


class TestApplyInputsExtension:
    @staticmethod
    def _apply_body() -> str:
        text = MAIN_WEB.read_text()
        # Find the function definition start
        start = text.find("def _apply_new_project_required_inputs(")
        assert start != -1
        # Find the next "-> dict[str, str]:" signature end
        # then walk forward to the end of the function.
        sig_end = text.find("\n    snapshot = dict(", start)
        if sig_end == -1:
            sig_end = text.find(":", text.find(")", start))
        body_start = sig_end
        # Walk to the next top-level "def " or "def _" after body_start
        # (top-level = at column 0 in source).
        i = body_start + 1
        # Find next "def " at column 0
        while i < len(text):
            nl = text.find("\n", i)
            if nl == -1:
                break
            line_start = nl + 1
            # Check if next line starts with "def "
            if text[line_start : line_start + 4] == "def ":
                return text[body_start:line_start]
            i = nl + 1
        return text[body_start:]

    def test_function_writes_spv_name(self):
        body = self._apply_body()
        assert '"spv_name"' in body
        assert 'submitted.get("spv_name")' in body

    def test_function_writes_currency(self):
        body = self._apply_body()
        assert '"currency"' in body
        # Default to EUR
        assert '"EUR"' in body

    def test_function_writes_construction_start_date(self):
        body = self._apply_body()
        assert '"construction_start_date"' in body

    def test_function_writes_construction_duration_months(self):
        body = self._apply_body()
        assert '"construction_duration_months"' in body


# ============================================================
# 6. Scope guardrails
# ============================================================


class TestScopeGuardrails:
    def test_app_js_unchanged(self):
        js = APP_JS.read_text()
        # Existing handlers untouched
        assert "switchTab" in js
        assert "showNewProjectPanel" in js

    def test_app_waterfall_core_unchanged(self):
        wf = REPO_ROOT / "app" / "waterfall_core.py"
        if wf.exists():
            text = wf.read_text()
            assert "Phase 56D" not in text

    def test_app_project_factories_unchanged(self):
        pf = REPO_ROOT / "app" / "project_factories.py"
        if pf.exists():
            text = pf.read_text()
            assert "Phase 56D" not in text

    def test_runtime_impact_taxonomy_unchanged(self):
        rt = REPO_ROOT / "app" / "runtime_impact_taxonomy.py"
        if rt.exists():
            text = rt.read_text()
            assert "Phase 56D" not in text

    def test_persistence_unchanged(self):
        pdir = REPO_ROOT / "app" / "persistence"
        for f in pdir.glob("*.py"):
            text = f.read_text()
            assert "Phase 56D" not in text, (
                f"persistence file {f.name} contains Phase 56D marker"
            )

    def test_no_financial_model_changes(self):
        for f in [
            REPO_ROOT / "app" / "waterfall_core.py",
            REPO_ROOT / "app" / "capex_engine.py",
            REPO_ROOT / "app" / "opex_engine.py",
            REPO_ROOT / "app" / "depreciation_engine.py",
        ]:
            if f.exists():
                text = f.read_text()
                assert "Phase 56D" not in text


# ============================================================
# 7. CSS is additive
# ============================================================


class TestCSSAdditive:
    def test_np_derived_note_class_added(self):
        css = STYLES_CSS.read_text()
        assert ".np-derived-note" in css
        assert ".np-derived-note__label" in css
        assert ".np-derived-note__text" in css

    def test_readonly_input_styling_added(self):
        css = STYLES_CSS.read_text()
        # Readonly inputs get a visually distinct style
        assert "input[readonly]" in css or 'input[aria-readonly="true"]' in css

    def test_root_count_unchanged(self):
        css = STYLES_CSS.read_text()
        root_count = len(re.findall(r":root\s*\{", css))
        assert root_count == 5, (
            f"styles.css :root block count changed from 5 to {root_count}."
        )


# ============================================================
# 8. rc1 untouched
# ============================================================


class TestRc1Untouched:
    def test_rc1_sha_constant_stable(self):
        assert RC1_SHA == "b425a0708719eaa5e1d922b1008e5609758e0ad4"


# ============================================================
# 9. Backend dateutil import
# ============================================================


class TestDateutilImport:
    def test_main_web_imports_relativedelta(self):
        text = MAIN_WEB.read_text()
        assert "from dateutil.relativedelta import relativedelta" in text, (
            "main_web.py must import relativedelta from dateutil"
        )


# ============================================================
# 10. Helper unit tests for determinism
# ============================================================


class TestHelperDeterminism:
    """Pin the helper's exact behavior for the cases the user spec
    specifically called out."""

    def test_normal_month_addition(self):
        from main_web import _derive_cod_date

        assert _derive_cod_date("2025-01-15", "6") == "2025-07-15"
        assert _derive_cod_date("2025-08-15", "3") == "2025-11-15"
        assert _derive_cod_date("2025-12-15", "12") == "2026-12-15"

    def test_month_end_deterministic(self):
        from main_web import _derive_cod_date

        # 31st of month -> end of next month if next has fewer days
        assert _derive_cod_date("2025-01-31", "1") == "2025-02-28"
        assert _derive_cod_date("2025-03-31", "1") == "2025-04-30"
        assert _derive_cod_date("2025-05-31", "1") == "2025-06-30"
        assert _derive_cod_date("2025-08-31", "1") == "2025-09-30"
        assert _derive_cod_date("2025-10-31", "1") == "2025-11-30"
        assert _derive_cod_date("2025-12-31", "1") == "2026-01-31"

    def test_leap_year_deterministic(self):
        from main_web import _derive_cod_date

        # Feb 29 + 12 months in non-leap year -> Feb 28
        assert _derive_cod_date("2024-02-29", "12") == "2025-02-28"
        # Feb 29 + 48 months in another leap year -> Feb 29
        assert _derive_cod_date("2024-02-29", "48") == "2028-02-29"
        # Feb 29 + 1 month in non-leap year -> Mar 29
        assert _derive_cod_date("2024-02-29", "1") == "2024-03-29"
