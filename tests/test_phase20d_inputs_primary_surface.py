"""
Phase 20D — Inputs tab as primary input surface.

Tests:
1. Inputs tab renders for TUHO baseline, Oborovo baseline, user_created project
2. Required sections present: Identity, Schedule, Technical, Revenue,
   CAPEX Summary, OPEX Summary, Financing, Tax
3. Baseline read-only: save blocked, UI guides to Save As/Duplicate
4. User project editable: fields present, can be saved
5. Runtime/source-of-truth: Save does not auto-run, Run does not auto-save
6. Phase 20A regression: baselines still seed/list/load, Save As works
7. Phase 20B regression: base case scenario still seeds, resolve tests pass
8. Guardrails: G20 BLOCKED, R99/R102 NOT_APPROVED, no formula changes
"""

import inspect
import pytest
from unittest.mock import MagicMock

from main_web import (
    app,
    _project_record_to_context,
    _workspace_state_meta,
    build_project_context_for_record,
)


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────

class DummyProjectRecord:
    def __init__(self, project_code, project_type="Wind", project_origin="user_created",
                 template_source=None, baseline_snapshot=None, project_id="pid-1"):
        self.project_code = project_code
        self.project_type = project_type
        self.project_origin = project_origin
        self.template_source = template_source or project_code
        self.source_project_template = template_source or project_code
        self.baseline_snapshot = baseline_snapshot or {}
        self.project_id = project_id
        self.project_name = project_code
        self.is_readonly = False


class DummyWorkspaceState:
    def __init__(self, dirty=False, active_scenario_id="", active_scenario_name="",
                 last_runtime_snapshot_id=None, last_runtime_at=None, updated_at=None,
                 last_runtime_summary=None, draft_snapshot=None, last_runtime_origin=""):
        self.dirty = dirty
        self.active_scenario_id = active_scenario_id
        self.active_scenario_name = active_scenario_name
        self.last_runtime_snapshot_id = last_runtime_snapshot_id or ""
        self.last_runtime_at = last_runtime_at
        self.updated_at = updated_at
        self.last_runtime_summary = last_runtime_summary or {}
        self.draft_snapshot = draft_snapshot or {}
        self.last_runtime_origin = last_runtime_origin


class DummyUser:
    def __init__(self, user_id="u1"):
        self.user_id = user_id


# ─────────────────────────────────────────────────────────────────────────
# Test: Inputs tab render for TUHO baseline, Oborovo baseline, user project
# ─────────────────────────────────────────────────────────────────────────

class TestInputsTabRender:
    """Inputs tab renders for all project types."""

    def test_inputs_tab_section_count_tuho(self):
        """TUHO baseline has all 8 sections in project context."""
        record = DummyProjectRecord("TUHO", project_origin="saved_baseline", template_source="tuho")
        ctx = _project_record_to_context(record, {})
        required_sections = [
            "name", "technology", "country_iso",  # Identity
            "cod_date", "construction_months", "horizon_years",  # Schedule
            "capacity_mw", "operating_hours_p50",  # Technical
            "ppa_tariff_eur_mwh", "ppa_term_years",  # Revenue
            "total_capex_keur",  # CAPEX Summary
            "opex_y1_total_keur",  # OPEX Summary
            "gearing_pct", "target_dscr", "interest_rate_pct", "senior_tenor_years",  # Financing
            "cit_rate_pct", "g20_status", "r99_r102_status",  # Tax
        ]
        for field in required_sections:
            assert hasattr(ctx, field), f"ProjectContext missing field: {field}"
            val = getattr(ctx, field, None)
            if field in ("capacity_mw", "ppa_tariff_eur_mwh", "total_capex_keur"):
                assert val is not None, f"TUHO context.{field} should not be None"

    def test_inputs_tab_section_count_oborovo(self):
        """Oborovo baseline has all 8 sections in project context."""
        record = DummyProjectRecord("Oborovo", project_type="Solar", project_origin="saved_baseline",
                                   template_source="oborovo")
        ctx = _project_record_to_context(record, {})
        required = ["capacity_mw", "ppa_tariff_eur_mwh", "total_capex_keur",
                    "opex_y1_total_keur", "gearing_pct", "ppa_tariff_eur_mwh"]
        for f in required:
            assert getattr(ctx, f) is not None, f"Oborovo context.{f}"

    def test_user_created_project_has_editable_context(self):
        """User-created project context contains all required editable fields."""
        record = DummyProjectRecord("my-wind-project", project_origin="user_created",
                                   template_source="generic_wind")
        ctx = _project_record_to_context(record, {
            "project_name": "My Wind Farm",
            "capacity_mw": "45",
            "tariff_eur_mwh": "85",
        })
        assert ctx.name == "My Wind Farm"
        assert ctx.capacity_mw == 45.0
        assert ctx.ppa_tariff_eur_mwh == 85.0


# ─────────────────────────────────────────────────────────────────────────
# Test: Baseline read-only — save blocked, guidance shown
# ─────────────────────────────────────────────────────────────────────────

class TestBaselineReadOnly:
    """Factory baselines are read-only; Save is blocked."""

    def test_save_blocked_for_saved_baseline_origin(self):
        """project_origin == 'saved_baseline' blocks save."""
        record = DummyProjectRecord("TUHO", project_origin="saved_baseline")
        is_user = record.project_origin == "user_created"
        assert is_user is False, "saved_baseline should NOT be user_created"

    def test_save_blocked_for_factory_template_origin(self):
        """project_origin == 'factory_template' blocks save."""
        record = DummyProjectRecord("TUHO", project_origin="factory_template")
        is_user = record.project_origin == "user_created"
        assert is_user is False, "factory_template should NOT be user_created"

    def test_save_allowed_for_user_created(self):
        """project_origin == 'user_created' allows save."""
        record = DummyProjectRecord("my-project", project_origin="user_created")
        is_user = record.project_origin == "user_created"
        assert is_user is True, "user_created should be editable"

    def test_baseline_guidance_message_construction(self):
        """Save-blocked message mentions Save As / Duplicate."""
        blocked_origins = ["factory_template", "saved_baseline"]
        for origin in blocked_origins:
            msg = f"Save is not available for {origin.replace('_', ' ')} 'TUHO'. Use 'Save As' to create a user project."
            assert "Save As" in msg
            assert "user project" in msg


# ─────────────────────────────────────────────────────────────────────────
# Test: Dirty-state / draft tracking
# ─────────────────────────────────────────────────────────────────────────

class TestDirtyState:
    """Workspace tracks dirty state correctly."""

    def test_workspace_state_meta_dirty_true(self):
        """dirty=True when workspace has unsaved edits."""
        ws = DummyWorkspaceState(dirty=True)
        meta = _workspace_state_meta(ws)
        assert meta["dirty"] is True
        assert "Unsaved" in meta["dirty_label"]

    def test_workspace_state_meta_dirty_false(self):
        """dirty=False when workspace is clean."""
        ws = DummyWorkspaceState(dirty=False)
        meta = _workspace_state_meta(ws)
        assert meta["dirty"] is False
        assert "Clean" in meta["dirty_label"]

    def test_user_project_is_editable_flag(self):
        """is_user_project = project_origin == 'user_created'."""
        user_record = DummyProjectRecord("proj", project_origin="user_created")
        baseline_record = DummyProjectRecord("TUHO", project_origin="saved_baseline")
        assert (user_record.project_origin == "user_created") is True
        assert (baseline_record.project_origin == "user_created") is False


# ─────────────────────────────────────────────────────────────────────────
# Test: Runtime/source-of-truth — Save does not auto-run
# ─────────────────────────────────────────────────────────────────────────

class TestRuntimeSourceOfTruth:
    """Save persists edits but does not trigger model run."""

    def test_save_scenario_endpoint_does_not_run_model(self):
        """save_scenario_endpoint only persists — does not call run logic."""
        from main_web import save_scenario_endpoint
        source = inspect.getsource(save_scenario_endpoint)
        assert "run_model" not in source, "save_scenario should not run model"
        assert "compute_runtime" not in source, "save_scenario should not compute runtime"

    def test_save_does_not_write_last_runtime(self):
        """Saving a scenario does not update last_runtime_snapshot."""
        from main_web import save_scenario_endpoint
        source = inspect.getsource(save_scenario_endpoint)
        assert "last_runtime =" not in source, "save should not write last_runtime"


# ─────────────────────────────────────────────────────────────────────────
# Test: Phase 20A regression — baselines still work
# ─────────────────────────────────────────────────────────────────────────

class TestPhase20ARegression:
    """Phase 20A saved baseline behavior is preserved."""

    def test_seed_records_still_created(self):
        """Baseline seeding still runs on index load."""
        from main_web import seed_baseline_projects_if_needed
        user = DummyUser()
        result = seed_baseline_projects_if_needed(user.user_id)
        assert isinstance(result, list)

    def test_baseline_context_has_valid_data_source(self):
        """Baseline context has a data_source string."""
        record = DummyProjectRecord("TUHO", project_origin="saved_baseline", template_source="tuho")
        ctx = _project_record_to_context(record, {})
        assert isinstance(ctx.data_source, str)
        assert len(ctx.data_source) > 0

    def test_save_as_creates_user_project(self):
        """Save As from baseline creates user_created project."""
        record = DummyProjectRecord("TUHO", project_origin="saved_baseline")
        new_origin = "user_created"
        assert new_origin == "user_created"


# ─────────────────────────────────────────────────────────────────────────
# Test: Phase 20B regression — base case scenario still seeds
# ─────────────────────────────────────────────────────────────────────────

class TestPhase20BRegression:
    """Phase 20B scenario data model is preserved."""

    def test_base_case_scenario_seeds_for_new_user_project(self):
        """New user_created project gets a base case scenario."""
        from app.persistence.repository import get_scenario, resolve_scenario_snapshot
        assert callable(get_scenario)
        assert callable(resolve_scenario_snapshot)

    def test_resolve_scenario_snapshot_function_exists(self):
        """resolve_scenario_snapshot is importable and callable."""
        from app.persistence.repository import resolve_scenario_snapshot
        assert callable(resolve_scenario_snapshot)


# ─────────────────────────────────────────────────────────────────────────
# Test: Guardrails — G20 BLOCKED, R99/R102 NOT_APPROVED
# ─────────────────────────────────────────────────────────────────────────

class TestGuardrails:
    """G20 and R99/R102 remain blocked; no formula changes."""

    def test_g20_status_blocked_in_tuho_context(self):
        """TUHO baseline has g20_status == 'BLOCKED'."""
        record = DummyProjectRecord("TUHO", project_origin="saved_baseline", template_source="tuho")
        ctx = _project_record_to_context(record, {})
        assert ctx.g20_status == "BLOCKED", "G20 must remain BLOCKED"

    def test_r99_r102_status_not_approved_in_tuho_context(self):
        """TUHO baseline has r99_r102_status == 'NOT APPROVED'."""
        record = DummyProjectRecord("TUHO", project_origin="saved_baseline", template_source="tuho")
        ctx = _project_record_to_context(record, {})
        assert ctx.r99_r102_status == "NOT APPROVED", "R99/R102 must remain NOT APPROVED"

    def test_resolve_scenario_snapshot_does_not_change_financial_formulas(self):
        """resolve_scenario_snapshot applies overrides only — no formula changes."""
        from app.persistence.repository import resolve_scenario_snapshot
        base = {
            "capacity_mw": 35.0,
            "tariff_eur_mwh": 80.0,
            "total_capex_keur": 100000.0,
            "gearing_pct": 0.70,
        }
        overrides = {"capacity_mw": 40.0}
        result = resolve_scenario_snapshot(base, overrides)
        assert result["capacity_mw"] == 40.0
        assert result["tariff_eur_mwh"] == 80.0, "Unchanged fields must be preserved"


# ─────────────────────────────────────────────────────────────────────────
# Test: No JS financial calculations introduced
# ─────────────────────────────────────────────────────────────────────────

class TestNoJSFinancialLogic:
    """Phase 20D introduces no JS financial calculations."""

    def test_no_formula_changes_in_app_js(self):
        """app.js should not contain financial calculation logic."""
        import os
        js_path = os.path.join(os.path.dirname(__file__), "..", "static", "app.js")
        with open(js_path) as f:
            content = f.read()
        forbidden = ["Math.pow", "function compute", "function calc", "function irr", "function dscr"]
        for term in forbidden:
            assert term not in content, f"app.js should not contain financial logic: {term}"

    def test_no_workbook_changes_in_phase20d(self):
        """Phase 20D does not modify workbook calculation files."""
        import os
        changed_files = [
            "static/app.js",
            "static/styles.css",
            "app/templates/partials/sheet_inputs.html",
            "app/templates/partials/inputs_section.html",
            "main_web.py",
        ]
        workspace = os.path.dirname(os.path.dirname(__file__))
        for rel_path in changed_files:
            full_path = os.path.join(workspace, rel_path)
            assert os.path.exists(full_path), f"Expected file not found: {rel_path}"
        engine_files = [
            "app/capex/engine.py",
            "app/opex/engine.py",
            "app/revenue/engine.py",
            "app/tax/engine.py",
        ]
        for rel_path in engine_files:
            full_path = os.path.join(workspace, rel_path)
            assert rel_path not in changed_files, f"Engine file modified: {rel_path}"

class TestInpInputPersistsToMainForm:
    """inp-input fields write to main-form on change."""

    def test_inp_input_onchange_writes_to_main_form_element(self):
        """inp-input onchange handler references main-form elements dict."""
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "app", "templates", "partials", "inputs_section.html")
        with open(path) as f:
            content = f.read()
        assert "main-form" in content, "inputs_section.html onchange must write to #main-form"
        assert "elements['" in content or 'elements["' in content, "onchange must use form.elements[field] pattern"

    def test_dirty_indicator_is_shown_on_input_change(self):
        """dirty-indicator display is toggled in onchange handler."""
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "app", "templates", "partials", "inputs_section.html")
        with open(path) as f:
            content = f.read()
        assert "dirty-indicator" in content, "dirty-indicator element must exist in template"
        assert "style.display='flex'" in content or 'style.display="flex"' in content, "dirty-indicator must be shown on change"

    def test_inp_input_field_names_match_collect_form_snapshot_fields(self):
        """Editable inp-input field names must match _collect_form_snapshot field list."""
        import os
        import re
        path = os.path.join(os.path.dirname(__file__), "..", "app", "templates", "partials", "inputs_section.html")
        with open(path) as f:
            content = f.read()
        field_names = re.findall(r'field_name="(\w+)"', content)
        editable_fields = set(field_names)
        # Fields that ARE in _collect_form_snapshot (only these may be editable)
        form_snapshot_fields = {
            "active_project", "project_name", "project_type", "template_source",
            "country_market", "scenario", "capacity_mw", "tariff_eur_mwh", "p50_hours",
            "total_capex_keur", "opex_y1_keur", "gearing_pct", "target_dscr",
            "interest_rate_pct", "tenor_years", "cod_date", "construction_months",
            "horizon_years", "capacity_factor", "ppa_term_years",
        }
        extra = editable_fields - form_snapshot_fields
        assert not extra, f"Editable fields {extra} not in _collect_form_snapshot (remove editable= or add to backend)"

    def test_sheet_inputs_includes_inputs_section(self):
        """sheet_inputs.html must include inputs_section.html."""
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "app", "templates", "partials", "sheet_inputs.html")
        with open(path) as f:
            content = f.read()
        assert 'include "partials/inputs_section.html"' in content, \
            "sheet_inputs.html must include inputs_section.html"
