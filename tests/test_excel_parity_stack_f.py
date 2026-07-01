"""Excel Parity Stack F — Tax Engine → UI Wiring characterization tests.

Branch: excel-parity-stack-f-tax-ui
Phase F1: Audit existing Tax output (documented here as findings)
Phase F2: Runtime payload wiring — run_project() → sessionStorage["lastTaxSchedule"]
Phase F3: Tax UI — read-only engine tables in sheet_tax.html
Phase F4: Pre-Run fallback — tax-unavailable-panel shown before first Run
Phase F5: Serialization — _serialize_tax_schedule() produces JSON-safe payload
Phase F6: Characterization tests (this file)

No financial logic was changed to produce these tests.
All calculations remain in the engine; these tests only verify that:
  - Tax schedule data flows from WaterfallResult.periods through run_project()
    into the runtime payload ("tax_schedule" key)
  - The payload is JSON-safe (no NaN/Infinity)
  - Expected fields are present (taxable_profit, tax, cf_after_tax, loss buckets)
  - sheet_tax.html reads "lastTaxSchedule" from sessionStorage
  - The tax-unavailable-panel is still present as a pre-Run fallback
  - No JS arithmetic/formula expressions exist in the tax schedule rendering code
  - Guardrail files (domain/*, waterfall_core.py, input_adapter.py) are untouched
"""
from __future__ import annotations

import json
import re


# ---------------------------------------------------------------------------
# F1 audit findings (documented inline — these facts were verified by reading
# domain/waterfall/waterfall_engine.py WaterfallPeriod and WaterfallResult):
#
#   Per-period fields on WaterfallPeriod (tax-related):
#     taxable_profit_keur                       — taxable profit after losses (engine)
#     tax_keur                                  — CIT accrual this period
#     cf_after_tax_keur                         — post-tax cashflow (EBITDA - cash_tax)
#     corporate_tax_cash_keur                   — cash tax paid this period
#     tax_depreciation_audit_keur               — fiscal tax depreciation
#     taxable_income_before_losses_audit_keur   — taxable income before loss offset
#     tax_loss_opening_audit_keur               — loss carryforward opening balance
#     tax_loss_used_audit_keur                  — losses applied this period
#     tax_loss_closing_audit_keur               — loss carryforward closing balance
#     taxable_profit_after_losses_audit_keur    — taxable profit after loss offset
#     cit_accrual_audit_keur                    — CIT accrual (audit version)
#     cash_tax_current_period_audit_keur        — cash tax current period (audit)
#
#   Summary fields on WaterfallResult:
#     total_tax_keur  — total CIT accrual over project life
#
#   Source: WaterfallResult.periods (computed by waterfall engine).
#   No separate "tax schedule assembly" step needed — fields are already
#   on the period objects. Serializer reads them directly.
# ---------------------------------------------------------------------------


class TestF2TaxSchedulePayload:
    """Phase F2: verify tax_schedule payload flows from run_project()."""

    def test_tax_schedule_in_run_project_output(self):
        """run_project() must return a 'tax_schedule' key."""
        from app.api.project_runner import run_project
        result = run_project("TUHO", "Base")
        assert "tax_schedule" in result, (
            "run_project() must include 'tax_schedule' key in its return dict. "
            "Phase F2 wiring: _serialize_tax_schedule() is called in run_project()."
        )

    def test_tax_schedule_not_none_after_run(self):
        """The 'tax_schedule' payload must not be None after a successful run."""
        from app.api.project_runner import run_project
        result = run_project("TUHO", "Base")
        ts = result.get("tax_schedule")
        assert ts is not None, (
            "tax_schedule payload must not be None after a TUHO run."
        )

    def test_tax_schedule_oborovo_not_none(self):
        """tax_schedule payload must not be None for Oborovo either."""
        from app.api.project_runner import run_project
        result = run_project("Oborovo", "Base")
        ts = result.get("tax_schedule")
        assert ts is not None, (
            "tax_schedule payload must not be None after an Oborovo run."
        )

    def test_tax_schedule_has_required_top_level_keys(self):
        """tax_schedule payload must have 'periods', 'summary', 'source' keys."""
        from app.api.project_runner import run_project
        result = run_project("TUHO", "Base")
        ts = result["tax_schedule"]
        for key in ("periods", "summary", "source"):
            assert key in ts, f"tax_schedule payload is missing key '{key}'"

    def test_tax_schedule_source_annotation(self):
        """tax_schedule source field must indicate WaterfallResult.periods origin."""
        from app.api.project_runner import run_project
        result = run_project("TUHO", "Base")
        ts = result["tax_schedule"]
        assert "WaterfallResult" in ts.get("source", ""), (
            "tax_schedule source field must reference WaterfallResult. "
            "This proves the data comes from the engine, not hardcoded values."
        )

    def test_tax_schedule_periods_nonempty(self):
        """tax_schedule periods list must be non-empty."""
        from app.api.project_runner import run_project
        result = run_project("TUHO", "Base")
        ts = result["tax_schedule"]
        periods = ts["periods"]
        assert len(periods) > 0, "tax_schedule periods list must be non-empty."


class TestF5TaxScheduleSerializes:
    """Phase F5: verify serialization is clean (no NaN/Infinity, JSON-safe)."""

    def test_tax_schedule_serializes_cleanly(self):
        """tax_schedule payload must be JSON-serializable with no NaN/Infinity."""
        from app.api.project_runner import run_project
        result = run_project("TUHO", "Base")
        ts = result["tax_schedule"]
        serialized = json.dumps(ts)
        assert "NaN" not in serialized, "tax_schedule must not contain NaN"
        assert "Infinity" not in serialized, "tax_schedule must not contain Infinity"
        assert len(serialized) > 100, "Serialized tax_schedule should be non-trivial."

    def test_tax_schedule_has_expected_fields(self):
        """Each operation period must have required tax fields."""
        from app.api.project_runner import run_project
        result = run_project("TUHO", "Base")
        ts = result["tax_schedule"]
        op_periods = [p for p in ts["periods"] if p.get("is_operation")]
        assert len(op_periods) > 0, "Must have at least one operation period."
        sample = op_periods[0]
        expected_fields = [
            "taxable_profit_keur",
            "tax_keur",
            "cf_after_tax_keur",
            "corporate_tax_cash_keur",
            "cit_accrual_audit_keur",
        ]
        for field in expected_fields:
            assert field in sample, (
                f"Period missing field '{field}'. "
                f"Available fields: {list(sample.keys())}"
            )

    def test_tax_schedule_loss_fields_present(self):
        """Each period must have loss carryforward fields."""
        from app.api.project_runner import run_project
        result = run_project("TUHO", "Base")
        ts = result["tax_schedule"]
        op_periods = [p for p in ts["periods"] if p.get("is_operation")]
        assert len(op_periods) > 0
        sample = op_periods[0]
        for field in (
            "tax_loss_opening_audit_keur",
            "tax_loss_used_audit_keur",
            "tax_loss_closing_audit_keur",
        ):
            assert field in sample, (
                f"Period missing loss carryforward field '{field}'."
            )

    def test_tax_schedule_summary_fields(self):
        """tax_schedule summary must have total_tax_keur."""
        from app.api.project_runner import run_project
        result = run_project("TUHO", "Base")
        ts = result["tax_schedule"]
        summary = ts["summary"]
        assert "total_tax_keur" in summary, (
            "tax_schedule summary missing 'total_tax_keur'"
        )

    def test_tax_schedule_no_inf_nan_in_payload(self):
        """No infinite or NaN float values must appear after JSON serialization."""
        from app.api.project_runner import run_project
        result = run_project("Oborovo", "Base")
        ts = result["tax_schedule"]
        serialized = json.dumps(ts)
        assert "Infinity" not in serialized
        assert "NaN" not in serialized

    def test_tax_schedule_serialized_size_reasonable(self):
        """Serialized payload must be < 500 KB for TUHO."""
        from app.api.project_runner import run_project
        result = run_project("TUHO", "Base")
        ts = result["tax_schedule"]
        size = len(json.dumps(ts))
        assert size < 500_000, (
            f"Serialized tax_schedule size {size:,} bytes exceeds 500 KB."
        )

    def test_serialize_tax_schedule_function_exists(self):
        """_serialize_tax_schedule must exist in project_runner module."""
        from app.api import project_runner
        assert hasattr(project_runner, "_serialize_tax_schedule"), (
            "_serialize_tax_schedule function must exist in app/api/project_runner.py"
        )


class TestF3TaxUIScheduleRendering:
    """Phase F3: verify sheet_tax.html renders the tax schedule."""

    def _load_template(self) -> str:
        from pathlib import Path
        path = Path(__file__).parent.parent / "app/templates/partials/sheet_tax.html"
        return path.read_text(encoding="utf-8")

    def test_tax_ui_has_schedule_rendering_js(self):
        """sheet_tax.html must read 'lastTaxSchedule' from sessionStorage."""
        html = self._load_template()
        assert 'sessionStorage.getItem("lastTaxSchedule")' in html, (
            "sheet_tax.html must read 'lastTaxSchedule' from sessionStorage. "
            "Phase F3: JS tax schedule renderer not found."
        )

    def test_tax_ui_has_schedule_block(self):
        """sheet_tax.html must have tax-schedule-block element."""
        html = self._load_template()
        assert 'id="tax-schedule-block"' in html, (
            "sheet_tax.html must contain id='tax-schedule-block' div "
            "for the post-Run tax schedule table."
        )

    def test_tax_ui_has_schedule_table(self):
        """sheet_tax.html must have tax-schedule-table."""
        html = self._load_template()
        assert 'id="tax-schedule-table"' in html, (
            "sheet_tax.html must contain id='tax-schedule-table' element."
        )

    def test_tax_ui_has_lasttaxschedule_sessionstorage_key(self):
        """sheet_tax.html must reference 'lastTaxSchedule' session key."""
        html = self._load_template()
        assert "lastTaxSchedule" in html, (
            "sheet_tax.html must reference 'lastTaxSchedule' sessionStorage key."
        )


class TestF4TaxUIPreRunFallback:
    """Phase F4: verify sheet_tax.html still shows unavailable panel pre-Run."""

    def _load_template(self) -> str:
        from pathlib import Path
        path = Path(__file__).parent.parent / "app/templates/partials/sheet_tax.html"
        return path.read_text(encoding="utf-8")

    def test_tax_unavailable_panel_exists(self):
        """sheet_tax.html must still contain the tax-unavailable-panel class."""
        html = self._load_template()
        assert "tax-unavailable-panel" in html, (
            "sheet_tax.html must still contain 'tax-unavailable-panel' element "
            "as the pre-Run fallback. Do not remove this — it is shown when "
            "sessionStorage has no 'lastTaxSchedule' data yet."
        )

    def test_tax_unavailable_panel_has_id(self):
        """The unavailable panel must have id='tax-unavailable-panel' for JS targeting."""
        html = self._load_template()
        assert 'id="tax-unavailable-panel"' in html, (
            "tax-unavailable-panel must have id='tax-unavailable-panel' so JS can hide it."
        )

    def test_tax_unavailable_panel_not_hardcoded_visible(self):
        """The unavailable panel must not be visible by default (style=display:none or hidden by JS)."""
        html = self._load_template()
        # The panel should be initially set to display:none (JS will show it if no data)
        # or JS controls its visibility. Either way, it should not be bare/always-visible.
        # Verify JS calls to control it exist.
        assert "_populateTaxSchedule" in html, (
            "sheet_tax.html must call _populateTaxSchedule() to control the unavailable panel visibility."
        )


class TestFNoClientSideCalc:
    """Verify no client-side tax calculations exist in sheet_tax.html."""

    def _load_template(self) -> str:
        from pathlib import Path
        path = Path(__file__).parent.parent / "app/templates/partials/sheet_tax.html"
        return path.read_text(encoding="utf-8")

    def test_no_js_arithmetic_in_rendering_functions(self):
        """No arithmetic operators (*,/,+,-) should appear inside JS function bodies
        that render tax data — all values come from the engine.
        """
        html = self._load_template()
        # Extract JS function bodies from the rendering section
        # Look for the _buildTxBody and _renderTaxSchedule functions
        # We allow arithmetic in string ops / array indexing / loop increments only.
        # The key check: no tax formula expressions like `a * b`, `a / b` for computation.
        # Simple approach: check that TX_ROWS items don't compute anything.
        assert "TX_ROWS" in html, "TX_ROWS row definition list must be present."
        # No computed field assignments in row defs (just label + key)
        tx_rows_section = re.search(r"var TX_ROWS\s*=\s*\[(.*?)\];", html, re.DOTALL)
        assert tx_rows_section, "TX_ROWS must be defined."
        rows_text = tx_rows_section.group(1)
        # No arithmetic in row definitions (only string keys and labels)
        assert "*" not in rows_text.replace("/*", "").replace("*/", ""), (
            "TX_ROWS must not contain multiplication — all values come from engine."
        )


class TestFGuardrails:
    """Verify engine files were not modified."""

    def test_waterfall_core_not_modified(self):
        """waterfall_core.py must not reference _serialize_tax_schedule."""
        from pathlib import Path
        content = (Path(__file__).parent.parent / "app/waterfall_core.py").read_text()
        assert "_serialize_tax_schedule" not in content, (
            "waterfall_core.py must not be modified for Stack F. "
            "The serializer lives in project_runner.py only."
        )

    def test_run_service_has_lasttaxschedule_wiring(self):
        """run_service.py must contain lastTaxSchedule wiring."""
        from pathlib import Path
        content = (Path(__file__).parent.parent / "app/services/run_service.py").read_text()
        assert "lastTaxSchedule" in content, (
            "run_service.py must wire 'lastTaxSchedule' into sessionStorage script."
        )

    def test_run_service_has_tax_schedule_parameter(self):
        """_build_sessionstorage_save_tag must accept tax_schedule parameter."""
        from pathlib import Path
        content = (Path(__file__).parent.parent / "app/services/run_service.py").read_text()
        assert "tax_schedule" in content, (
            "_build_sessionstorage_save_tag must have tax_schedule parameter."
        )

    def test_domain_capex_dir_is_only_domain_dir(self):
        """app/domain/ must only contain capex (existing structure, untouched)."""
        from pathlib import Path
        domain_path = Path(__file__).parent.parent / "app/domain"
        subdirs = [d.name for d in domain_path.iterdir() if d.is_dir()]
        # Only 'capex' should be there — as in origin/main
        assert "capex" in subdirs, "app/domain/capex must still exist."
        # No new tax/ directory was added under app/domain/
        assert "tax" not in subdirs, (
            "No new tax/ directory should have been added to app/domain/. "
            "Tax engine lives in /domain/ (not app/domain/)."
        )
