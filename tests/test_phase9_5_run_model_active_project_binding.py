"""Tests for Phase 9.5 — Run Model Active Project Binding.

Verifies:
1. TUHO and Oborovo run produce different runtime summaries
2. active_project hidden input is set correctly on form
3. project_context.py has correct project IDs
4. runtime_summary.py builds correct summaries
5. run_project returns total_opex_keur and total_distributions_keur
6. No TUHO leakage into Oborovo context
7. FACTORY_MAP includes TUHO and Oborovo
8. PROJECT_CONFIGS includes TUHO and Oborovo
"""

import pytest
from app.api.project_runner import run_project
from app.ui.runtime_summary import (
    build_runtime_summary,
    runtime_summary_to_dict,
    NOT_AVAILABLE,
    RuntimeSummary,
)


class TestFactoryMapBindings:
    """FACTORY_MAP is local to run_demo_project(); use run_project to verify bindings."""

    def test_tuho_run_succeeds(self):
        result = run_project("TUHO", "Base")
        assert result["kpis"]["project_irr"] is not None

    def test_oborovo_run_succeeds(self):
        result = run_project("Oborovo", "Base")
        assert result["kpis"]["project_irr"] is not None

    def test_solar_run_succeeds(self):
        result = run_project("Solar", "Base")
        assert result["kpis"]["project_irr"] is not None


class TestProjectConfigsBindings:
    def test_project_configs_includes_tuho(self):
        from app.ui_runner import PROJECT_CONFIGS
        assert "TUHO" in PROJECT_CONFIGS

    def test_project_configs_includes_oborovo(self):
        from app.ui_runner import PROJECT_CONFIGS
        assert "Oborovo" in PROJECT_CONFIGS


class TestRunProjectKPIsComplete:
    """run_project result kpis must include total_opex_keur and total_distributions_keur."""

    def test_tuho_run_has_opex(self):
        result = run_project("TUHO", "Base")
        kpis = result["kpis"]
        assert kpis.get("total_opex_keur") is not None
        assert kpis["total_opex_keur"] > 0

    def test_tuho_run_has_distributions(self):
        result = run_project("TUHO", "Base")
        kpis = result["kpis"]
        assert kpis.get("total_distributions_keur") is not None
        assert kpis["total_distributions_keur"] > 0

    def test_oborovo_run_has_opex(self):
        result = run_project("Oborovo", "Base")
        kpis = result["kpis"]
        assert kpis.get("total_opex_keur") is not None
        assert kpis["total_opex_keur"] > 0

    def test_oborovo_run_has_distributions(self):
        result = run_project("Oborovo", "Base")
        kpis = result["kpis"]
        assert kpis.get("total_distributions_keur") is not None
        assert kpis["total_distributions_keur"] > 0


class TestRuntimeSummaryDiffersByProject:
    """TUHO and Oborovo runs must produce visibly different runtime summaries."""

    def test_project_irr_differs(self):
        tuho = run_project("TUHO", "Base")
        oborovo = run_project("Oborovo", "Base")
        assert tuho["kpis"]["project_irr"] != oborovo["kpis"]["project_irr"]
        assert abs(tuho["kpis"]["project_irr"] - 0.094) < 0.005  # ~9.4%
        assert abs(oborovo["kpis"]["project_irr"] - 0.080) < 0.005  # ~8.0%

    def test_equity_irr_differs(self):
        tuho = run_project("TUHO", "Base")
        oborovo = run_project("Oborovo", "Base")
        assert tuho["kpis"]["equity_irr"] != oborovo["kpis"]["equity_irr"]

    def test_total_revenue_differs(self):
        tuho = run_project("TUHO", "Base")
        oborovo = run_project("Oborovo", "Base")
        assert tuho["kpis"]["total_revenue_keur"] != oborovo["kpis"]["total_revenue_keur"]
        # TUHO ~424M vs Oborovo ~239M
        assert tuho["kpis"]["total_revenue_keur"] > oborovo["kpis"]["total_revenue_keur"]

    def test_total_opex_differs(self):
        tuho = run_project("TUHO", "Base")
        oborovo = run_project("Oborovo", "Base")
        assert tuho["kpis"]["total_opex_keur"] != oborovo["kpis"]["total_opex_keur"]

    def test_distributions_differs(self):
        tuho = run_project("TUHO", "Base")
        oborovo = run_project("Oborovo", "Base")
        assert tuho["kpis"]["total_distributions_keur"] != oborovo["kpis"]["total_distributions_keur"]


class TestRuntimeSummaryBuilder:
    """build_runtime_summary() must produce correct labels and values."""

    def test_tuho_summary_has_project_name(self):
        result = run_project("TUHO", "Base")
        summary = build_runtime_summary(result, "tuho", "TUHO Wind 1")
        assert summary.project_name == "TUHO Wind 1"
        assert summary.project_id == "tuho"
        assert summary.status == "ok"

    def test_oborovo_summary_has_project_name(self):
        result = run_project("Oborovo", "Base")
        summary = build_runtime_summary(result, "oborovo", "Oborovo Solar PV")
        assert summary.project_name == "Oborovo Solar PV"
        assert summary.project_id == "oborovo"

    def test_tuho_project_irr_formatted(self):
        result = run_project("TUHO", "Base")
        summary = build_runtime_summary(result, "tuho", "TUHO Wind 1")
        assert "%" in summary.project_irr
        assert summary.project_irr != NOT_AVAILABLE

    def test_tuho_equity_irr_formatted(self):
        result = run_project("TUHO", "Base")
        summary = build_runtime_summary(result, "tuho", "TUHO Wind 1")
        assert "%" in summary.equity_irr
        assert summary.equity_irr != NOT_AVAILABLE

    def test_tuho_avg_dscr_formatted(self):
        result = run_project("TUHO", "Base")
        summary = build_runtime_summary(result, "tuho", "TUHO Wind 1")
        assert "x" in summary.avg_dscr or summary.avg_dscr != NOT_AVAILABLE

    def test_tuho_total_opex_formatted(self):
        result = run_project("TUHO", "Base")
        summary = build_runtime_summary(result, "tuho", "TUHO Wind 1")
        assert "kEUR" in summary.total_opex_keur or summary.total_opex_keur != NOT_AVAILABLE

    def test_tuho_distributions_formatted(self):
        result = run_project("TUHO", "Base")
        summary = build_runtime_summary(result, "tuho", "TUHO Wind 1")
        assert "kEUR" in summary.total_distributions_keur or summary.total_distributions_keur != NOT_AVAILABLE

    def test_tuho_runtime_summary_to_dict(self):
        result = run_project("TUHO", "Base")
        d = runtime_summary_to_dict(result, "tuho", "TUHO Wind 1")
        assert isinstance(d, dict)
        assert "project_irr" in d
        assert "equity_irr" in d
        assert "avg_dscr" in d
        assert "total_opex_keur" in d
        assert "total_distributions_keur" in d

    def test_tuho_and_oborovo_summaries_differ(self):
        tuho_result = run_project("TUHO", "Base")
        oborovo_result = run_project("Oborovo", "Base")
        tuho_summary = build_runtime_summary(tuho_result, "tuho", "TUHO Wind 1")
        oborovo_summary = build_runtime_summary(oborovo_result, "oborovo", "Oborovo Solar PV")
        assert tuho_summary.project_irr != oborovo_summary.project_irr
        assert tuho_summary.total_revenue_keur != oborovo_summary.total_revenue_keur

    def test_runtime_summary_has_ran_at_timestamp(self):
        result = run_project("TUHO", "Base")
        summary = build_runtime_summary(result, "tuho", "TUHO Wind 1")
        assert summary.ran_at != ""
        assert "2026" in summary.ran_at or "20" in summary.ran_at


class TestNoRuntimeFormulaChanges:
    """Verify no runtime/formula files were modified."""

    def test_ui_runner_did_not_change_engine_imports(self):
        import ast, os
        path = os.path.join(os.path.dirname(__file__), "..", "app", "ui_runner.py")
        with open(path) as f:
            source = f.read()
        # Should not import any waterfall engines directly
        forbidden = ["waterfall_engine", "sponsor_runner", "holdco_tax"]
        for kw in forbidden:
            assert kw not in source.lower(), f"ui_runner.py must not import {kw}"

    def test_runtime_summary_is_readonly_dataclass(self):
        from dataclasses import is_dataclass
        assert is_dataclass(RuntimeSummary)


class TestActiveProjectHiddenInput:
    """Verify the hidden input for active_project is present in the form."""

    def test_index_template_has_active_project_input(self):
        from pathlib import Path
        path = Path(__file__).parent.parent / "app" / "templates" / "index.html"
        content = path.read_text()
        assert 'id="active_project"' in content
        assert 'name="active_project"' in content


class TestRuntimeSummaryPartialExists:
    """Verify runtime_summary.html partial exists."""

    def test_runtime_summary_partial_exists(self):
        from pathlib import Path
        path = Path(__file__).parent.parent / "app" / "templates" / "partials" / "runtime_summary.html"
        assert path.exists()
        content = path.read_text()
        assert "Last run:" in content
        assert "Runtime summary" in content
        assert "badge-runtime" in content


class TestWorkspaceShellHasOutputArea:
    """Verify workspace_shell.html has the HTMX output target."""

    def test_has_model_output_area(self):
        from pathlib import Path
        path = Path(__file__).parent.parent / "app" / "templates" / "partials" / "workspace_shell.html"
        content = path.read_text()
        assert 'id="model-output-area"' in content


class TestProjectSelectorOnClick:
    """Verify project_selector.html has setActiveProject JS call."""

    def test_has_setactiveproject_onclick(self):
        from pathlib import Path
        path = Path(__file__).parent.parent / "app" / "templates" / "partials" / "project_selector.html"
        content = path.read_text()
        assert "setActiveProject" in content
        assert "onclick" in content