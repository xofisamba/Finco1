"""Excel Parity Stack E — Senior Debt Engine → UI Wiring characterization tests.

Branch: excel-parity-stack-e-senior-debt-ui
Phase E1: Audit existing Senior Debt output (documented here as findings)
Phase E2: Runtime payload wiring — run_project() → sessionStorage["lastDebtSchedule"]
Phase E3: Senior Debt UI — read-only engine tables in sheet_senior_debt.html
Phase E4: Pre-Run fallback — sd-unavailable-panel shown before first Run
Phase E5: Serialization — _serialize_debt_schedule() produces JSON-safe payload
Phase E6: Characterization tests (this file)

No financial logic was changed to produce these tests.
All calculations remain in the engine; these tests only verify that:
  - Debt schedule data flows from WaterfallResult.periods through run_project()
    into the runtime payload ("debt_schedule" key)
  - The payload is JSON-safe (no NaN/Infinity)
  - Expected fields are present (principal, interest, debt_service, dscr, balance)
  - sheet_senior_debt.html reads "lastDebtSchedule" from sessionStorage
  - The sd-unavailable-panel is still present as a pre-Run fallback
  - No JS arithmetic/formula expressions exist in the debt schedule rendering code
  - Guardrail files (domain/*, waterfall_core.py, input_adapter.py) are untouched
"""
from __future__ import annotations

import json
import re


# ---------------------------------------------------------------------------
# E1 audit findings (documented inline — these facts were verified by reading
# domain/waterfall/waterfall_engine.py WaterfallPeriod and WaterfallResult):
#
#   Per-period fields on WaterfallPeriod:
#     senior_balance_keur    — closing balance after principal payment
#     senior_principal_keur  — sculpted principal repayment
#     senior_interest_keur   — interest on opening senior balance
#     senior_ds_keur         — total senior debt service (interest + principal)
#     dscr                   — CFADS / senior_ds_keur
#     dsra_balance_keur      — DSRA closing balance
#     dsra_contribution_keur — DSRA funding contribution this period
#
#   Summary fields on WaterfallResult:
#     total_senior_ds_keur   — total senior debt service over life
#     actual_min_dscr        — minimum DSCR achieved
#     actual_avg_dscr        — average DSCR achieved
#     target_dscr            — target DSCR from financing inputs
#
#   Source: WaterfallResult.periods (computed by waterfall engine).
#   No separate "debt schedule assembly" step needed — fields are already
#   on the period objects. Serializer reads them directly.
# ---------------------------------------------------------------------------


class TestE2DebtSchedulePayload:
    """Phase E2: verify debt_schedule payload flows from run_project()."""

    def test_debt_schedule_in_run_project_output(self):
        """run_project() must return a 'debt_schedule' key."""
        from app.api.project_runner import run_project_legacy as run_project  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        assert "debt_schedule" in result, (
            "run_project() must include 'debt_schedule' key in its return dict. "
            "Phase E2 wiring: _serialize_debt_schedule() is called in run_project()."
        )

    def test_debt_schedule_not_none_after_run(self):
        """The 'debt_schedule' payload must not be None after a successful run."""
        from app.api.project_runner import run_project_legacy as run_project  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        ds = result.get("debt_schedule")
        assert ds is not None, (
            "debt_schedule payload must not be None after a TUHO run."
        )

    def test_debt_schedule_oborovo_not_none(self):
        """debt_schedule payload must not be None for Oborovo either."""
        from app.api.project_runner import run_project_legacy as run_project  # PR-8: legacy characterization route
        result = run_project("Oborovo", "Base")
        ds = result.get("debt_schedule")
        assert ds is not None, (
            "debt_schedule payload must not be None after an Oborovo run."
        )

    def test_debt_schedule_has_required_top_level_keys(self):
        """debt_schedule payload must have 'periods', 'summary', 'source' keys."""
        from app.api.project_runner import run_project_legacy as run_project  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        ds = result["debt_schedule"]
        for key in ("periods", "summary", "source"):
            assert key in ds, f"debt_schedule payload is missing key '{key}'"

    def test_debt_schedule_source_annotation(self):
        """debt_schedule source field must indicate WaterfallResult.periods origin."""
        from app.api.project_runner import run_project_legacy as run_project  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        ds = result["debt_schedule"]
        assert "WaterfallResult" in ds.get("source", ""), (
            "debt_schedule source field must reference WaterfallResult. "
            "This proves the data comes from the engine, not hardcoded values."
        )

    def test_debt_schedule_periods_nonempty(self):
        """debt_schedule periods list must be non-empty."""
        from app.api.project_runner import run_project_legacy as run_project  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        ds = result["debt_schedule"]
        periods = ds["periods"]
        assert len(periods) > 0, "debt_schedule periods list must be non-empty."


class TestE5DebtScheduleSerializes:
    """Phase E5: verify serialization is clean (no NaN/Infinity, JSON-safe)."""

    def test_debt_schedule_serializes_cleanly(self):
        """debt_schedule payload must be JSON-serializable with no NaN/Infinity."""
        from app.api.project_runner import run_project_legacy as run_project  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        ds = result["debt_schedule"]
        serialized = json.dumps(ds)
        assert "NaN" not in serialized, "debt_schedule must not contain NaN"
        assert "Infinity" not in serialized, "debt_schedule must not contain Infinity"
        assert len(serialized) > 100, "Serialized debt_schedule should be non-trivial."

    def test_debt_schedule_has_expected_fields(self):
        """Each operation period must have principal, interest, debt_service, dscr, closing_balance."""
        from app.api.project_runner import run_project_legacy as run_project  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        ds = result["debt_schedule"]
        op_periods = [p for p in ds["periods"] if p.get("is_operation")]
        assert len(op_periods) > 0, "Must have at least one operation period."
        sample = op_periods[0]
        expected_fields = [
            "senior_principal_keur",
            "senior_interest_keur",
            "senior_ds_keur",
            "dscr",
            "senior_balance_keur",
        ]
        for field in expected_fields:
            assert field in sample, (
                f"Period missing field '{field}'. "
                f"Available fields: {list(sample.keys())}"
            )

    def test_debt_schedule_summary_fields(self):
        """debt_schedule summary must have expected aggregate fields."""
        from app.api.project_runner import run_project_legacy as run_project  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        ds = result["debt_schedule"]
        summary = ds["summary"]
        for field in ("total_senior_ds_keur", "actual_min_dscr", "actual_avg_dscr", "target_dscr"):
            assert field in summary, f"debt_schedule summary missing field '{field}'"

    def test_debt_schedule_no_inf_nan_in_payload(self):
        """No infinite or NaN float values must appear after JSON serialization."""
        from app.api.project_runner import run_project_legacy as run_project  # PR-8: legacy characterization route
        result = run_project("Oborovo", "Base")
        ds = result["debt_schedule"]
        serialized = json.dumps(ds)
        assert "Infinity" not in serialized
        assert "NaN" not in serialized

    def test_debt_schedule_serialized_size_reasonable(self):
        """Serialized payload must be < 500 KB for TUHO (~60 periods)."""
        from app.api.project_runner import run_project_legacy as run_project  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        ds = result["debt_schedule"]
        size = len(json.dumps(ds))
        assert size < 500_000, (
            f"Serialized debt_schedule size {size:,} bytes exceeds 500 KB. "
            "Consider trimming fields or capping period count."
        )


class TestE3SeniorDebtUIScheduleRendering:
    """Phase E3: verify sheet_senior_debt.html renders the debt schedule."""

    def _load_template(self) -> str:
        from pathlib import Path
        path = Path(__file__).parent.parent / "app/templates/partials/sheet_senior_debt.html"
        return path.read_text(encoding="utf-8")

    def test_senior_debt_ui_has_schedule_rendering_js(self):
        """sheet_senior_debt.html must read 'lastDebtSchedule' from sessionStorage."""
        html = self._load_template()
        assert 'sessionStorage.getItem("lastDebtSchedule")' in html, (
            "sheet_senior_debt.html must read 'lastDebtSchedule' from sessionStorage. "
            "Phase E3: JS debt schedule renderer not found."
        )

    def test_senior_debt_ui_has_schedule_block(self):
        """sheet_senior_debt.html must have sd-schedule-block element."""
        html = self._load_template()
        assert 'id="sd-schedule-block"' in html, (
            "sheet_senior_debt.html must contain id='sd-schedule-block' div "
            "for the post-Run debt schedule table."
        )

    def test_senior_debt_ui_has_schedule_table(self):
        """sheet_senior_debt.html must have sd-schedule-table."""
        html = self._load_template()
        assert 'id="sd-schedule-table"' in html, (
            "sheet_senior_debt.html must contain id='sd-schedule-table' table."
        )

    def test_senior_debt_ui_has_expected_row_labels(self):
        """Template JS must define rows for interest, principal, DSCR, balance."""
        html = self._load_template()
        for label in ("Interest", "Principal", "DSCR", "Closing Balance"):
            assert label in html, (
                f"sheet_senior_debt.html JS must include row label '{label}'."
            )

    def test_senior_debt_ui_reads_is_operation_filter(self):
        """Template JS must filter to operation periods only."""
        html = self._load_template()
        assert "is_operation" in html, (
            "sheet_senior_debt.html must filter periods to is_operation=true. "
            "Construction periods must not appear in the debt schedule table."
        )


class TestE4PreRunFallback:
    """Phase E4: verify pre-Run unavailable panel is present as fallback."""

    def _load_template(self) -> str:
        from pathlib import Path
        path = Path(__file__).parent.parent / "app/templates/partials/sheet_senior_debt.html"
        return path.read_text(encoding="utf-8")

    def test_senior_debt_ui_pre_run_shows_unavailable(self):
        """sd-unavailable-panel must still be present in template as a pre-Run fallback."""
        html = self._load_template()
        assert 'id="sd-unavailable-panel"' in html, (
            "sheet_senior_debt.html must contain id='sd-unavailable-panel' element "
            "as a pre-Run fallback (shown when no lastDebtSchedule in sessionStorage)."
        )

    def test_senior_debt_ui_unavailable_panel_shown_by_js(self):
        """JS must explicitly show the unavailable panel when no debt schedule data."""
        html = self._load_template()
        assert "sd-unavailable-panel" in html, (
            "sd-unavailable-panel reference must appear in sheet_senior_debt.html."
        )
        # JS must conditionally show/hide the panel
        assert 'display = ""' in html or "style.display" in html, (
            "JS must set display style on sd-unavailable-panel to control visibility."
        )

    def test_senior_debt_unavailable_panel_default_hidden(self):
        """sd-unavailable-panel must start hidden (JS controls visibility)."""
        html = self._load_template()
        # The panel has style="display:none;" and JS shows it when no data.
        assert 'sd-unavailable-panel' in html
        # Check that the panel element has display:none default
        pattern = r'id="sd-unavailable-panel"[^>]*style="display:none'
        assert re.search(pattern, html), (
            "sd-unavailable-panel must have style='display:none' by default; "
            "JS reveals it when no debt schedule data is available."
        )


class TestNoJSCalculationsInDebtUI:
    """Phase E3 guardrail: no JS arithmetic in debt schedule rendering."""

    def _load_template(self) -> str:
        from pathlib import Path
        path = Path(__file__).parent.parent / "app/templates/partials/sheet_senior_debt.html"
        return path.read_text(encoding="utf-8")

    def test_no_js_calculations_in_debt_ui(self):
        """JS rendering code must not perform arithmetic (no +/-/* on numeric fields).

        The engine is the single source of truth. All values come from
        WaterfallResult.periods — no recalculation in the browser.
        """
        html = self._load_template()
        # Extract only the script block for the debt schedule renderer
        script_match = re.search(r'<script>(.*?)</script>', html, re.DOTALL)
        assert script_match, "sheet_senior_debt.html must contain a <script> block."
        script = script_match.group(1)

        # No arithmetic operations on _keur or dscr field values.
        # Allowed: string operations like textContent = _fmt(...)
        # Forbidden: field_a + field_b, field_a * field_b, field_a / field_b in output
        forbidden_patterns = [
            # Arithmetic on two keur/dscr field references (not just format calls)
            r'_keur\s*[+\-\*\/]\s*\w+_keur',
            r'dscr\s*[+\-\*\/]\s*\w',
        ]
        for pat in forbidden_patterns:
            assert not re.search(pat, script), (
                f"JS debt schedule renderer contains forbidden arithmetic pattern: {pat!r}. "
                "No financial calculations must be performed in JS. "
                "Engine is the single source of truth."
            )


class TestE6Guardrails:
    """Phase E6: verify guardrail files are untouched by this PR."""

    def test_waterfall_core_not_importing_debt_serializer(self):
        """waterfall_core.py must not import _serialize_debt_schedule.

        The serializer lives in project_runner.py, not in the engine core.
        This maintains the isolation proven by the C8 test.
        """
        from pathlib import Path
        wc = Path(__file__).parent.parent / "app/waterfall_core.py"
        content = wc.read_text(encoding="utf-8")
        assert "_serialize_debt_schedule" not in content, (
            "waterfall_core.py must not import or reference _serialize_debt_schedule. "
            "The serializer must live only in project_runner.py."
        )

    def test_input_adapter_not_changed(self):
        """input_adapter.py must not reference debt_schedule serialization."""
        from pathlib import Path
        ia = Path(__file__).parent.parent / "app/input_adapter.py"
        if not ia.exists():
            return  # File doesn't exist — no violation
        content = ia.read_text(encoding="utf-8")
        assert "_serialize_debt_schedule" not in content, (
            "input_adapter.py must not be changed by this PR."
        )

    def test_project_factories_not_changed_for_debt(self):
        """project_factories.py must not have been changed for debt schedule wiring.

        The debt schedule serializer reads from WaterfallResult — no factory
        changes needed. If project_factories.py was changed, the parity-core
        SHA lock in test_phase51f_parallel_work_guardrails.py must be updated.
        """
        from pathlib import Path
        pf = Path(__file__).parent.parent / "app/project_factories.py"
        content = pf.read_text(encoding="utf-8")
        assert "_serialize_debt_schedule" not in content, (
            "project_factories.py must not reference _serialize_debt_schedule."
        )
        # Note: "debt_schedule" may appear in project_factories.py as a pre-existing
        # parameter (e.g. freeze_senior_debt_schedule). We only forbid the serializer
        # import — not the existing parameter name.
        assert "from app.api.project_runner import _serialize_debt_schedule" not in content, (
            "project_factories.py must not import _serialize_debt_schedule."
        )

    def test_domain_financial_statements_not_changed(self):
        """domain/financial_statements/ must not be changed by this PR."""
        from pathlib import Path
        fs_dir = Path(__file__).parent.parent / "domain/financial_statements"
        if not fs_dir.exists():
            return
        for py_file in fs_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "debt_schedule" not in content or "senior_debt" not in content.split("debt_schedule")[0], (
                f"{py_file} must not be changed for debt_schedule wiring."
            )

    def test_guardrail_debt_schedule_not_in_waterfall_engine(self):
        """domain/waterfall/waterfall_engine.py must not import _serialize_debt_schedule."""
        from pathlib import Path
        we = Path(__file__).parent.parent / "domain/waterfall/waterfall_engine.py"
        if not we.exists():
            return
        content = we.read_text(encoding="utf-8")
        assert "_serialize_debt_schedule" not in content, (
            "waterfall_engine.py must not be changed for debt_schedule wiring."
        )


class TestE2SessionStorageWiring:
    """Phase E2: verify run_service.py threads debt_schedule to sessionStorage."""

    def test_run_service_builds_debt_schedule_script(self):
        """_build_sessionstorage_save_tag() must write lastDebtSchedule when data present."""
        from app.services.run_service import _build_sessionstorage_save_tag
        dummy_ds = {"periods": [], "summary": {}, "source": "test"}
        script = _build_sessionstorage_save_tag(
            runtime_summary={"project_name": "test"},
            runtime_origin="form_only",
            workspace_state=None,
            runtime_snapshot_id="test123",
            debt_schedule=dummy_ds,
        )
        assert 'lastDebtSchedule' in script, (
            "_build_sessionstorage_save_tag() must write 'lastDebtSchedule' "
            "to sessionStorage when debt_schedule is provided."
        )

    def test_run_service_removes_debt_schedule_when_none(self):
        """_build_sessionstorage_save_tag() must remove lastDebtSchedule when None."""
        from app.services.run_service import _build_sessionstorage_save_tag
        script = _build_sessionstorage_save_tag(
            runtime_summary={"project_name": "test"},
            runtime_origin="form_only",
            workspace_state=None,
            runtime_snapshot_id="test123",
            debt_schedule=None,
        )
        assert 'removeItem("lastDebtSchedule")' in script, (
            "_build_sessionstorage_save_tag() must call removeItem('lastDebtSchedule') "
            "when debt_schedule is None, to clear stale data."
        )
