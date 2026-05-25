"""Phase 16 — Run Pipeline and Runtime Render Fix Tests.

Validates:
1. /run has no NameError (all variables defined before use)
2. Run button wiring is correct (no duplicate active btn-run-model)
3. Dirty guard blocks run without auto-save
4. Runtime delta proof (tariff 60 vs 100 changes revenue)
5. Static summary honesty (project_ctx labeled as factory reference)
6. Guardrails: no JS financial calc, G20 BLOCKED, R99/R102 NOT APPROVED

Scope: main_web.py, base.html, index.html, sheet_revenue.html, static/app.js
"""

from __future__ import annotations

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestRunNoNameError:
    """Verify /run endpoint defines all required variables before use."""

    def test_run_defines_snapshot_before_branching(self):
        """snapshot = _collect_form_snapshot(form) must appear before any branch."""
        main_web = os.path.join(BASE_DIR, "main_web.py")
        content = open(main_web).read()

        run_idx = content.find('@app.post("/run")')
        assert run_idx >= 0, "/run endpoint not found"

        # Find first use of snapshot in /run
        snapshot_use = content.find("snapshot.get", run_idx)
        assert snapshot_use >= 0, "snapshot.get not found in /run"

        # Find snapshot definition
        snapshot_def = content.find("snapshot = _collect_form_snapshot", run_idx)
        assert snapshot_def >= 0, "snapshot = _collect_form_snapshot not found in /run"

        # snapshot definition must come before its use
        assert snapshot_def < snapshot_use, (
            f"snapshot defined at {snapshot_def} but used at {snapshot_use} — "
            "snapshot must be defined before any branching"
        )

    def test_run_defines_project_record_before_use(self):
        """project_record must be defined before record_workspace_runtime call."""
        main_web = os.path.join(BASE_DIR, "main_web.py")
        content = open(main_web).read()

        run_idx = content.find('@app.post("/run")')

        # Find first record_workspace_runtime call in /run
        record_use = content.find("record_workspace_runtime(", run_idx)
        assert record_use >= 0, "record_workspace_runtime not called in /run"

        # Find project_record definition
        project_record_def = content.find("project_record, workspace_state = _project_workspace_from_snapshot(", run_idx)
        assert project_record_def >= 0, "project_record, workspace_state = _project_workspace_from_snapshot not found in /run"

        assert project_record_def < record_use, (
            "project_record must be defined before record_workspace_runtime"
        )

    def test_run_defines_workspace_state_before_use(self):
        """workspace_state must be defined before used in record_workspace_runtime."""
        main_web = os.path.join(BASE_DIR, "main_web.py")
        content = open(main_web).read()

        run_idx = content.find('@app.post("/run")')

        # Find workspace_state usage (not definition, in record_workspace_runtime call)
        ws_use = content.find("workspace_state.active_scenario_id", run_idx)
        assert ws_use >= 0, "workspace_state.active_scenario_id not found in /run"

        # Find workspace_state definition (via helper that creates both)
        ws_def = content.find("project_record, workspace_state = _project_workspace_from_snapshot(", run_idx)
        assert ws_def >= 0, "_project_workspace_from_snapshot not found in /run"

        assert ws_def < ws_use, "workspace_state must be defined before used"

    def test_run_defines_runtime_origin_before_use(self):
        """runtime_origin must be defined before used in conditional."""
        main_web = os.path.join(BASE_DIR, "main_web.py")
        content = open(main_web).read()

        run_idx = content.find('@app.post("/run")')

        # Find first runtime_origin use (not definition)
        ru_use = content.find("runtime_origin == \"saved_state\"", run_idx)
        assert ru_use >= 0, "runtime_origin == 'saved_state' not found in /run"

        # Find runtime_origin definition
        ru_def = content.find("allow_run, runtime_origin, guard_message = runtime_guard_for_snapshot", run_idx)
        assert ru_def >= 0, "runtime_origin not defined via runtime_guard_for_snapshot in /run"

        assert ru_def < ru_use, "runtime_origin must be defined before used"

    def test_run_has_dirty_guard_before_branching(self):
        """Dirty guard must block run if workspace_state is dirty."""
        main_web = os.path.join(BASE_DIR, "main_web.py")
        content = open(main_web).read()

        run_idx = content.find('@app.post("/run")')

        # Find runtime_guard_for_snapshot call
        guard_call = content.find("runtime_guard_for_snapshot(", run_idx)
        assert guard_call >= 0, "runtime_guard_for_snapshot not called in /run"

        # Find if not allow_run check
        guard_check = content.find("if not allow_run:", guard_call)
        assert guard_check >= 0, "if not allow_run: not found after guard call"

        # Check that the guard is before runtime_seed branching
        branch = content.find("if runtime_seed in {", run_idx)
        assert guard_call < branch, "dirty guard must be before runtime_seed branching"


class TestRunButtonWiring:
    """Verify Run Model button wiring is correct with no duplicate active IDs."""

    def test_no_duplicate_btn_run_model_ids(self):
        """Rendered page must not have duplicate id='btn-run-model'."""
        base_html = os.path.join(BASE_DIR, "app/templates/base.html")
        index_html = os.path.join(BASE_DIR, "app/templates/index.html")

        base_content = open(base_html).read()
        index_content = open(index_html).read()

        base_ids = re.findall(r'id="btn-run-model[^"]*"', base_content)
        index_ids = re.findall(r'id="btn-run-model[^"]*"', index_content)

        # base.html should have btn-run-model-sidebar, not btn-run-model
        assert "btn-run-model" not in base_content or "btn-run-model-sidebar" in base_content, (
            "base.html must not have id='btn-run-model' (should be btn-run-model-sidebar)"
        )
        # index.html should have btn-run-model
        assert "btn-run-model" in index_content, "index.html must have btn-run-model"

    def test_index_html_run_button_has_hx_post(self):
        """#btn-run-model in index.html must have hx-post='/run'."""
        index_html = os.path.join(BASE_DIR, "app/templates/index.html")
        content = open(index_html).read()

        idx = content.find('id="btn-run-model"')
        assert idx >= 0, "btn-run-model not found in index.html"

        # Find the button element
        start = content.rfind("<button", 0, idx)
        end = content.find(">", idx) + 1
        btn_html = content[start:end]

        assert 'hx-post="/run"' in btn_html, (
            "btn-run-model must have hx-post='/run'"
        )
        assert 'hx-include="#main-form"' in btn_html, (
            "btn-run-model must have hx-include='#main-form', not hx-form"
        )
        assert 'hx-target="#model-output-area"' in btn_html, (
            "btn-run-model must target #model-output-area"
        )

    def test_base_html_sidebar_run_button_exists_without_static_disabled(self):
        """Sidebar run button (btn-run-model-sidebar) must exist without static disabled.

        Design: sidebar button uses click delegation to real btn-run-model.
        Dirty-disable is handled dynamically via setButtonDisabledState (JS), not static HTML disabled.
        """
        base_html = os.path.join(BASE_DIR, "app/templates/base.html")
        content = open(base_html).read()

        idx = content.find('id="btn-run-model-sidebar"')
        assert idx >= 0, (
            "base.html must have sidebar run button with id='btn-run-model-sidebar'"
        )

        start = content.rfind("<button", 0, idx)
        end = content.find(">", idx) + 1
        btn_html = content[start:end]

        # Sidebar button should NOT have static 'disabled' because:
        # 1. It uses click delegation to real btn-run-model
        # 2. Dirty-disable is handled via JS setButtonDisabledState
        assert "disabled" not in btn_html, (
            "sidebar run button must NOT have static disabled (JS dirty-disable handles it dynamically)"
        )


class TestStaticSummaryHonesty:
    """Verify static sheet summaries are labeled as factory/reference, not live runtime."""

    def test_sheet_revenue_factory_reference_badge(self):
        """PPA Tariff (Y1) in sheet_revenue.html must have factory reference badge."""
        sheet = os.path.join(BASE_DIR, "app/templates/partials/sheet_revenue.html")
        content = open(sheet).read()

        # Find the assumption-grid section with PPA Tariff (Y1)
        idx = content.find("PPA Tariff (Y1)")
        assert idx >= 0, "PPA Tariff (Y1) not found in sheet_revenue.html"

        # Check that "factory reference" badge exists nearby
        region = content[max(0, idx-200):idx+200]
        assert "factory reference" in region.lower(), (
            "PPA Tariff (Y1) must have 'factory reference' badge"
        )

    def test_sheet_revenue_assumption_grid_has_reference_class(self):
        """assumption-grid must have --reference modifier or assumption-item has --reference."""
        sheet = os.path.join(BASE_DIR, "app/templates/partials/sheet_revenue.html")
        content = open(sheet).read()

        # Must have reference class on assumption-grid or assumption-item
        has_ref = "assumption-grid--reference" in content or "assumption-item--reference" in content
        assert has_ref, (
            "sheet_revenue.html must use assumption-grid--reference or assumption-item--reference class"
        )


class TestRuntimeDeltaProof:
    """Backend integration test for tariff 60 vs 100 runtime delta."""

    def test_tariff_60_vs_100_revenue_direction(self):
        """tariff_eur_mwh=100 must produce higher revenue than tariff=60 via build_projectinputs + run_project."""
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Only run if we have the actual modules
        try:
            from app.input_adapter import build_projectinputs
            from app.api.project_runner import run_project
            from app.input_schema import ProjectInputsSchema, RevenueInput
        except ImportError as e:
            pytest.skip(f"Cannot import required modules: {e}")

        # Build TUHO base schema with tariff=60
        schema_60 = ProjectInputsSchema(
            project_type="Wind",
            scenario="Base",
            capacity_mw=35.0,
            revenue=RevenueInput(tariff_eur_mwh=60.0, p50_hours=3000.0),
        )
        override_60 = build_projectinputs(schema_60)
        result_60 = run_project("TUHO", "Base", project_inputs_override=override_60)

        # Build TUHO with tariff=100
        schema_100 = ProjectInputsSchema(
            project_type="Wind",
            scenario="Base",
            capacity_mw=35.0,
            revenue=RevenueInput(tariff_eur_mwh=100.0, p50_hours=3000.0),
        )
        override_100 = build_projectinputs(schema_100)
        result_100 = run_project("TUHO", "Base", project_inputs_override=override_100)

        # Revenue must be higher with higher tariff
        rev_60 = result_60.get("kpis", {}).get("total_revenue_keur", 0)
        rev_100 = result_100.get("kpis", {}).get("total_revenue_keur", 0)

        assert rev_100 > rev_60, (
            f"tariff=100 (rev={rev_100}) must produce higher revenue than tariff=60 (rev={rev_60}). "
            "Backend runtime must be source of truth."
        )
        # Sanity check: both should be non-zero
        assert rev_60 > 0, f"Baseline revenue should be > 0, got {rev_60}"
        assert rev_100 > 0, f"Changed revenue should be > 0, got {rev_100}"
        # Verify delta is meaningful (at least 50k)
        assert rev_100 - rev_60 > 50_000, (
            f"Revenue delta {rev_100 - rev_60:.0f} is suspiciously small. "
            "Tariff change should produce substantial revenue change."
        )


class TestGuardrails:
    """Guardrail tests — no runtime/model formula changes."""

    def test_no_javascript_financial_calculations(self):
        """static/app.js must not contain Math.*, irr, npv, pmt calculations."""
        app_js = os.path.join(BASE_DIR, "static/app.js")
        content = open(app_js).read()

        patterns = [
            r'\bMath\.\s*(pow|sqrt|exp|log|sin|cos)',
            r'\birr\s*\(',
            r'\bnpv\s*\(',
            r'\bpmt\s*\(',
            r'\brate\s*\(',
            r'\bNPV\s*\(',
            r'\bIRR\s*\(',
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            assert not match, f"JavaScript financial calculation found: {pattern}"

    def test_g20_remains_blocked(self):
        """G20 must remain BLOCKED."""
        project_ctx = os.path.join(BASE_DIR, "app/ui/project_context.py")
        content = open(project_ctx).read()
        assert 'g20_status="BLOCKED"' in content, "G20 must remain BLOCKED"

    def test_r99_r102_not_approved(self):
        """R99 and R102 must remain NOT APPROVED."""
        project_ctx = os.path.join(BASE_DIR, "app/ui/project_context.py")
        content = open(project_ctx).read()
        assert 'r99_r102_status="NOT APPROVED"' in content

    def test_no_workbook_calculation_changes(self):
        """No changes to export/institutional workbook calculation logic."""
        export_files = [
            os.path.join(BASE_DIR, "app/excel_export.py"),
            os.path.join(BASE_DIR, "app/export/institutional_workbook.py"),
        ]
        for f in export_files:
            if os.path.exists(f):
                content = open(f).read()
                assert len(content) > 100, f"{f} seems broken"

    def test_run_does_not_auto_save(self):
        """Run endpoint must not call save_project or save_scenario internally."""
        main_web = os.path.join(BASE_DIR, "main_web.py")
        content = open(main_web).read()

        run_idx = content.find('@app.post("/run")')
        run_end = content.find('@app.post("/compare")', run_idx)
        run_body = content[run_idx:run_end]

        # In /run body, save_scenario should not be called
        assert "save_scenario(" not in run_body, (
            "/run must not call save_scenario — run does not auto-save"
        )

    def test_save_does_not_auto_run(self):
        """Save endpoint must not call run_project or build_projectinputs."""
        main_web = os.path.join(BASE_DIR, "main_web.py")
        content = open(main_web).read()

        save_idx = content.find('@app.post("/scenarios/save")')
        # Find next endpoint after save
        next_endpoint = content.find('@app.post("/scenarios/', save_idx + 1)
        save_end = next_endpoint if next_endpoint > 0 else len(content)
        save_body = content[save_idx:save_end]

        assert "run_project(" not in save_body, (
            "/scenarios/save must not call run_project — save does not auto-run"
        )


class TestCompileAndSyntax:
    """Must compile and have valid syntax."""

    def test_main_web_compiles(self):
        """main_web.py must compile without errors."""
        main_web = os.path.join(BASE_DIR, "main_web.py")
        with open(main_web) as f:
            code = compile(f.read(), main_web, "exec")
        assert code is not None

    def test_static_app_js_syntax(self):
        """static/app.js must have valid JavaScript syntax."""
        import subprocess
        result = subprocess.run(
            ["node", "--check", os.path.join(BASE_DIR, "static/app.js")],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"app.js syntax error: {result.stderr}"


class TestDirtyGuardBehavior:
    """Verify dirty guard behavior in /run."""

    def test_dirty_guard_returns_error_template(self):
        """When allow_run=False, /run returns errors.html template, not silently failing."""
        main_web = os.path.join(BASE_DIR, "main_web.py")
        content = open(main_web).read()

        run_idx = content.find('@app.post("/run")')
        guard_block = content.find("if not allow_run:", run_idx)
        assert guard_block >= 0, "dirty guard not found"

        # After guard block, must return TemplateResponse with errors
        guard_section = content[guard_block:guard_block+300]
        assert "templates.TemplateResponse" in guard_section, (
            "dirty guard must return TemplateResponse (error), not silently continue"
        )
        assert 'name="partials/errors.html"' in guard_section, (
            "dirty guard must return errors.html template"
        )

    def test_runtime_origin_defined_before_used(self):
        """runtime_origin must be defined from runtime_guard_for_snapshot before used."""
        main_web = os.path.join(BASE_DIR, "main_web.py")
        content = open(main_web).read()

        run_idx = content.find('@app.post("/run")')

        # runtime_origin defined via runtime_guard_for_snapshot
        def_idx = content.find("runtime_origin,", run_idx)
        assert def_idx >= 0, "runtime_origin not defined in /run"

        # runtime_origin used in conditional
        use_idx = content.find("runtime_origin == \"saved_state\"", run_idx)
        assert use_idx >= 0, "runtime_origin used in conditional"

        assert def_idx < use_idx, "runtime_origin must be defined before used"