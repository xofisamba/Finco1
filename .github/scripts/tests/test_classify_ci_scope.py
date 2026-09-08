"""
Tests for .github/scripts/classify_ci_scope.py

Covers all 8 required cases from the CI routing cleanup spec plus
additional edge cases.  Run with:

    python3 -m pytest .github/scripts/tests/test_classify_ci_scope.py -v
"""
import sys
from pathlib import Path

# Make classifier importable without install
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from classify_ci_scope import classify, _classify_file  # noqa: E402


# ── _classify_file unit tests ─────────────────────────────────────────────────

class TestClassifyFile:
    def test_ui_template(self):
        assert _classify_file("app/templates/v2/partials/sheet_sensitivity.html") == "ui_only"

    def test_v2_router(self):
        assert _classify_file("app/v2/router.py") == "ui_only"

    def test_static(self):
        assert _classify_file("static/css/main.css") == "ui_only"

    def test_ui_test_file(self):
        assert _classify_file("tests/test_ui3b_browser_acceptance.py") == "ui_only"

    def test_htmx_test_file(self):
        assert _classify_file("tests/test_htmx_internal_demo.py") == "ui_only"

    def test_route_smoke_test(self):
        assert _classify_file("tests/test_phase57pre_route_render_smoke.py") == "ui_only"

    def test_financial_engine(self):
        assert _classify_file("financial_engine/core.py") == "frozen_authority"

    def test_finco_core(self):
        assert _classify_file("finco_core/inputs.py") == "frozen_authority"

    def test_app_api_project_runner(self):
        assert _classify_file("app/api/project_runner.py") == "frozen_authority"

    def test_app_services_production_authority(self):
        assert _classify_file("app/services/production_financial_authority.py") == "frozen_authority"

    def test_domain_file(self):
        assert _classify_file("domain/tax.py") == "frozen_authority"

    def test_app_persistence(self):
        assert _classify_file("app/persistence/repository.py") == "frozen_authority"

    def test_app_workbook(self):
        assert _classify_file("app/workbook/service.py") == "frozen_authority"

    def test_project_factories(self):
        assert _classify_file("app/project_factories.py") == "frozen_authority"

    def test_workflow_file(self):
        assert _classify_file(".github/workflows/ci.yml") == "workflow_only"

    def test_classifier_script(self):
        assert _classify_file(".github/scripts/classify_ci_scope.py") == "workflow_only"

    def test_docs_file(self):
        assert _classify_file("docs/architecture/MVP_ENGINE_FREEZE_POST_C3.md") == "docs_only"

    def test_root_readme(self):
        assert _classify_file("README.md") == "docs_only"

    def test_unknown_app_file(self):
        # Unrecognised app path → engine_sensitive (fail-safe)
        assert _classify_file("app/some_new_module.py") == "engine_sensitive"

    def test_unknown_root_file(self):
        assert _classify_file("some_random_file.py") == "engine_sensitive"

    def test_constraints_txt(self):
        # constraints.txt changes affect engine environment; classified as frozen_authority
        # (the outer classify() will map this to engine_sensitive=true)
        assert _classify_file("constraints.txt") in ("engine_sensitive", "frozen_authority")


# ── Required spec cases ───────────────────────────────────────────────────────

class TestRequiredCases:
    """The 8 required classification cases from the spec."""

    def test_case_a_ui_only(self):
        """CASE A: UI/template/test files → SAFE_UI_ONLY."""
        files = [
            "app/templates/v2/partials/sheet_sensitivity.html",
            "app/v2/router.py",
            "static/css/main.css",
            "tests/test_ui3b_scenario_sensitivity.py",
            "tests/test_ui3b_browser_acceptance.py",
        ]
        r = classify(files)
        assert r["ui_only"] == "true"
        assert r["engine_sensitive"] == "false"

    def test_case_b_financial_engine(self):
        """CASE B: financial_engine/ → ENGINE_SENSITIVE."""
        files = ["financial_engine/core.py"]
        r = classify(files)
        assert r["engine_sensitive"] == "true"
        assert r["ui_only"] == "false"

    def test_case_c_app_api_project_runner(self):
        """CASE C: app/api/project_runner.py → ENGINE_SENSITIVE."""
        files = ["app/api/project_runner.py"]
        r = classify(files)
        assert r["engine_sensitive"] == "true"
        assert r["ui_only"] == "false"

    def test_case_d_domain(self):
        """CASE D: domain/ → ENGINE_SENSITIVE."""
        files = ["domain/tax.py", "domain/debt.py"]
        r = classify(files)
        assert r["engine_sensitive"] == "true"
        assert r["ui_only"] == "false"

    def test_case_e_mixed_ui_plus_engine(self):
        """CASE E: mixed UI + engine file → ENGINE_SENSITIVE."""
        files = [
            "app/templates/v2/partials/sheet_sensitivity.html",
            "financial_engine/core.py",
        ]
        r = classify(files)
        assert r["engine_sensitive"] == "true"
        assert r["ui_only"] == "false"

    def test_case_f_docs_only(self):
        """CASE F: docs only → docs_only, no engine ring."""
        files = ["docs/architecture/MVP_ENGINE_FREEZE_POST_C3.md", "README.md"]
        r = classify(files)
        assert r["docs_only"] == "true"
        assert r["engine_sensitive"] == "false"
        assert r["ui_only"] == "false"

    def test_case_g_workflow_only(self):
        """CASE G: workflow YAML only → workflow_only."""
        files = [
            ".github/workflows/ci.yml",
            ".github/scripts/classify_ci_scope.py",
        ]
        r = classify(files)
        assert r["workflow_only"] == "true"
        assert r["engine_sensitive"] == "false"

    def test_case_h_unknown_file(self):
        """CASE H: unknown file → ENGINE_SENSITIVE (fail-safe)."""
        files = ["some_new_module_nobody_classified.py"]
        r = classify(files)
        assert r["engine_sensitive"] == "true"
        assert r["ui_only"] == "false"


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_diff(self):
        """Empty file list → workflow_only (safe)."""
        r = classify([])
        assert r["workflow_only"] == "true"
        assert r["engine_sensitive"] == "false"

    def test_ui_plus_docs(self):
        """UI + docs together → ui_only (all safe categories)."""
        files = [
            "app/templates/base.html",
            "docs/guide.md",
        ]
        r = classify(files)
        assert r["ui_only"] == "true"
        assert r["engine_sensitive"] == "false"

    def test_ui_plus_workflow(self):
        """UI + workflow files together → ui_only (all safe)."""
        files = [
            "app/v2/router.py",
            ".github/workflows/ci.yml",
        ]
        r = classify(files)
        assert r["ui_only"] == "true"
        assert r["engine_sensitive"] == "false"

    def test_finco_core_mixed_with_ui(self):
        """finco_core/ + UI file → ENGINE_SENSITIVE (not UI-only)."""
        files = [
            "finco_core/inputs.py",
            "app/templates/base.html",
        ]
        r = classify(files)
        assert r["engine_sensitive"] == "true"
        assert r["ui_only"] == "false"

    def test_app_persistence_not_ui(self):
        """app/persistence/ is engine-sensitive (not UI layer)."""
        files = ["app/persistence/scenarios_repository.py"]
        r = classify(files)
        assert r["engine_sensitive"] == "true"

    def test_app_services_not_ui(self):
        """app/services/ is engine-sensitive."""
        files = ["app/services/production_financial_authority.py"]
        r = classify(files)
        assert r["engine_sensitive"] == "true"

    def test_ui3b_pr_673_equivalent(self):
        """Simulate PR #973 (UI-3B Correction D) — must be ui_only."""
        files = [
            "app/templates/v2/partials/sheet_sensitivity.html",
            "app/v2/router.py",
            "app/v2/scenario_presentation.py",
            "app/templates/v2/partials/sheet_scenarios.html",
            "tests/test_ui3b_scenario_sensitivity.py",
            "tests/test_ui3b_completion.py",
            "tests/test_ui3b_browser_acceptance.py",
        ]
        r = classify(files)
        assert r["ui_only"] == "true", f"PR #973 should be ui_only; got: {r}"
        assert r["engine_sensitive"] == "false"

    def test_unknown_git_diff_error(self):
        """Sentinel from git failure → engine_sensitive."""
        r = classify(["UNKNOWN_GIT_DIFF_ERROR"])
        assert r["engine_sensitive"] == "true"

    def test_exact_output_keys(self):
        """All four output keys must always be present."""
        for files in [
            ["app/v2/router.py"],
            ["financial_engine/core.py"],
            ["docs/guide.md"],
            [".github/workflows/ci.yml"],
            [],
        ]:
            r = classify(files)
            assert set(r.keys()) >= {"ui_only", "docs_only", "workflow_only", "engine_sensitive"}

    def test_exactly_one_true_output(self):
        """Exactly one of the four scope outputs is 'true'."""
        test_cases = [
            ["app/v2/router.py"],
            ["financial_engine/core.py"],
            ["docs/guide.md"],
            [".github/workflows/ci.yml"],
        ]
        scope_keys = ["ui_only", "docs_only", "workflow_only", "engine_sensitive"]
        for files in test_cases:
            r = classify(files)
            true_count = sum(1 for k in scope_keys if r[k] == "true")
            assert true_count == 1, f"Expected exactly 1 true for {files}, got {r}"


# ── CLI smoke test ────────────────────────────────────────────────────────────

class TestCLI:
    def test_cli_files_arg(self, capsys):
        """--files mode produces parseable KEY=VALUE output."""
        import io, contextlib
        from classify_ci_scope import main
        from io import StringIO

        buf = StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(["--files", "app/v2/router.py", "app/templates/base.html"])
        assert code == 0
        output = buf.getvalue()
        pairs = dict(line.split("=", 1) for line in output.strip().splitlines() if "=" in line)
        assert pairs["ui_only"] == "true"
        assert pairs["engine_sensitive"] == "false"

    def test_cli_engine_sensitive(self, capsys):
        """Engine-sensitive file in --files mode → engine_sensitive=true."""
        from classify_ci_scope import main
        from io import StringIO
        import contextlib

        buf = StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(["--files", "financial_engine/engine.py"])
        assert code == 0
        output = buf.getvalue()
        pairs = dict(line.split("=", 1) for line in output.strip().splitlines() if "=" in line)
        assert pairs["engine_sensitive"] == "true"
        assert pairs["ui_only"] == "false"
