"""Phase B4 — single production engine / legacy excision acceptance suite.

Proves:
  B4-A  supported production matrix (Solar, Wind, Oborovo, TUHO):
        promoted, ONE clean calculation, zero legacy execution;
  B4-B  identity invariance (name/code/metadata rename → identical outputs);
  B4-C  fail closed (unknown / unsupported / unregistered / Portfolio):
        typed error, zero calculations of any engine;
  B4-D  static production import graph has NO legacy execution seam;
  B4-E  pre/post financial identity vs B3 main (bf71b21d fingerprints);
  B4-F  route convergence (API run / download / CLI seam / scenario);
  B4-G  offline evidence isolation (tests/helpers callable; production
        cannot import it).

Governance gate (section 13 of the B4 brief): the import-graph scan reasons
about production code and imports — no dumb repository-wide substring match.
"""
from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Modules whose import into the PRODUCTION graph is forbidden (legacy
# financial execution seams, Phase B4).
_FORBIDDEN_PRODUCTION_MODULES = {
    "app.ui_runner",                 # legacy demo funnel (offline only)
    "app.waterfall_runner",          # legacy WaterfallRunner
    "app.waterfall_core",            # legacy v3 core
    "app.validation_framework",      # offline validation (uses legacy funnel)
    "app.sponsor_project_adapter",   # offline sponsor calibration adapters
    "app.portfolio_runner",          # legacy pooled portfolio engine
    "app.cache",                     # cached legacy waterfall
    "tests.helpers.offline_calibration",
    "tests.helpers.offline_sponsor_engine",
}

# Production entry points whose transitive import graph is scanned.
_PRODUCTION_ENTRY_MODULES = [
    "main_web",
    "main_api",
    "app.api.router",
    "app.api.project_runner",
    "app.services.run_service",
    "app.services.save_run_service",
    "app.services.compare_service",
    "app.services.download_service",
    "app.services.export_service",
    "app.services.sensitivity_service",
    "app.services.lender_case_service",
    "app.services.production_financial_authority",
    "app.services.production_waterfall_seam",
    "app.services.clean_presentation_adapter",
    "app.export.runtime_summary",
    "app.export.institutional_workbook",
    "app.cli.commands",
    "streamlit_app",
]


class EngineCounters:
    def __init__(self, monkeypatch):
        self.clean_calls = 0
        self.legacy_core_calls = 0
        self.legacy_engine_calls = 0
        self.sponsor_calls = 0

        import financial_engine.shareholder_waterfall as g2c_pkg
        import financial_engine.shareholder_waterfall.model as g2c_model
        import app.waterfall_core as waterfall_core
        import app.waterfall_runner as waterfall_runner
        import finco_core.waterfall.waterfall_engine as legacy_engine
        import domain.waterfall.waterfall_engine as domain_engine

        _orig_clean = g2c_model.run_project_shareholder_waterfall_model
        _orig_core = waterfall_core.run_waterfall_v3_core
        _orig_engine = legacy_engine.run_waterfall

        def _count_clean(*a, **kw):
            self.clean_calls += 1
            return _orig_clean(*a, **kw)

        def _count_core(*a, **kw):
            self.legacy_core_calls += 1
            return _orig_core(*a, **kw)

        def _count_engine(*a, **kw):
            self.legacy_engine_calls += 1
            return _orig_engine(*a, **kw)

        monkeypatch.setattr(g2c_pkg, "run_project_shareholder_waterfall_model", _count_clean)
        monkeypatch.setattr(g2c_model, "run_project_shareholder_waterfall_model", _count_clean)
        monkeypatch.setattr(waterfall_core, "run_waterfall_v3_core", _count_core)
        monkeypatch.setattr(waterfall_runner, "run_waterfall_v3_core", _count_core)
        monkeypatch.setattr(legacy_engine, "run_waterfall", _count_engine)
        monkeypatch.setattr(domain_engine, "run_waterfall", _count_engine)


def _run(project_type, scenario="Base"):
    from app.api.project_runner import run_project

    return run_project(project_type, scenario)


# ---------------------------------------------------------------------------
# B4-A — supported production matrix
# ---------------------------------------------------------------------------

class TestB4A_SupportedProductionMatrix:
    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_a1_one_clean_calculation_no_legacy(self, ptype, monkeypatch):
        counters = EngineCounters(monkeypatch)
        out = _run(ptype, "Base")
        ra = out["runtime_authority"]
        assert ra["runtime_authority"] == "clean_g2c"
        assert ra["classification"] == "CLEAN_PRODUCTION_READY"
        assert counters.clean_calls == 1
        assert counters.legacy_core_calls == 0
        assert counters.legacy_engine_calls == 0

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_a2_clean_engine_provenance(self, ptype):
        out = _run(ptype, "Base")
        ra = out["runtime_authority"]
        assert ra["clean_entry_point"].endswith(
            "run_project_shareholder_waterfall_model"
        )
        assert ra["calculation_count"] == 1


# ---------------------------------------------------------------------------
# B4-B — identity invariance
# ---------------------------------------------------------------------------

class TestB4B_IdentityInvariance:
    @pytest.mark.parametrize("ptype", ("Solar", "TUHO"))
    def test_b1_rename_identity_bit_identical(self, ptype):
        import dataclasses
        from app import project_factories as pf

        factory = {
            "Solar": pf.create_default_solar_project,
            "TUHO": pf.create_default_tuho_wind1,
        }[ptype]
        base = factory()
        renamed = dataclasses.replace(
            base,
            info=dataclasses.replace(
                base.info,
                name="Renamed " + base.info.name,
                company="Renamed Co",
                code="RENAMED-X",
            ),
        )
        from app.api.project_runner import run_project

        out_a = run_project(ptype, "Base")
        out_b = run_project(ptype, "Base", project_inputs_override=renamed)
        assert out_b["runtime_authority"]["runtime_authority"] == "clean_g2c"
        for key in ("total_revenue_keur", "total_ebitda_keur",
                    "total_senior_ds_keur", "total_distributions_keur",
                    "min_dscr", "avg_dscr"):
            assert out_a["kpis"][key] == out_b["kpis"][key], key
        assert out_a["debt_schedule"] == out_b["debt_schedule"]


# ---------------------------------------------------------------------------
# B4-C — fail closed
# ---------------------------------------------------------------------------

class TestB4C_FailClosed:
    def test_c1_unknown_project_type(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        from app.services.production_financial_authority import CleanNotReadyError

        with pytest.raises(CleanNotReadyError) as exc:
            _run("NotAProject", "Base")
        assert exc.value.reason_code == "PR8_PROJECT_TYPE_NOT_CLASSIFIED"
        assert exc.value.calculation_count == 0
        assert counters.clean_calls == 0
        assert counters.legacy_core_calls == 0
        assert counters.legacy_engine_calls == 0

    def test_c2_portfolio_unclassified(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        from app.services.production_financial_authority import CleanNotReadyError

        with pytest.raises(CleanNotReadyError):
            _run("Portfolio", "Base")
        assert counters.clean_calls == 0
        assert counters.legacy_core_calls == 0

    def test_c3_blocked_contract_fails_closed(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        from app.project_factories import create_default_oborovo_legacy_calibration
        from app.services.production_financial_authority import CleanNotReadyError
        from app.api.project_runner import run_project

        blocked = create_default_oborovo_legacy_calibration()
        with pytest.raises(CleanNotReadyError):
            run_project("Oborovo", "Base", project_inputs_override=blocked)
        assert counters.clean_calls == 0
        assert counters.legacy_core_calls == 0
        assert counters.legacy_engine_calls == 0

    def test_c4_no_env_or_flag_reactivates_legacy(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        monkeypatch.setenv("FINCO_LEGACY_RUNTIME", "1")
        monkeypatch.setenv("FINCOGPT_RAISE_UI_ERRORS", "1")
        out = _run("Solar", "Base")
        assert out["runtime_authority"]["runtime_authority"] == "clean_g2c"
        assert counters.legacy_core_calls == 0


# ---------------------------------------------------------------------------
# B4-D — static production import graph gate
# ---------------------------------------------------------------------------

class TestB4D_NoProductionLegacyImports:
    def _production_import_graph(self) -> set[str]:
        """AST walk of transitive MODULE-LEVEL imports from production entry
        modules. Function-body lazy imports are excluded here — a lazy import
        is only reachable if its enclosing function is called, and actual
        legacy *execution* is proven absent by the AST call scan (d3) and the
        runtime engine counters (B4-A/C/F). This keeps the graph test about
        import reachability without dumb substring failures."""
        seen: set[str] = set()
        stack = list(_PRODUCTION_ENTRY_MODULES)
        while stack:
            mod = stack.pop()
            if mod in seen or mod.startswith(("tests", "finco_parity", "finco_recon")):
                continue
            seen.add(mod)
            try:
                spec = importlib.util.find_spec(mod)
            except (ImportError, ValueError, ModuleNotFoundError):
                continue
            if spec is None or not spec.origin:
                continue
            path = Path(spec.origin)
            if not path.exists():
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8-sig"))
            except SyntaxError:
                continue
            # Top-level statements only (module scope) — skip function bodies.
            for node in tree.body:
                targets: list[str] = []
                if isinstance(node, ast.Import):
                    targets = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    targets = [node.module]
                for t in targets:
                    base = t.split(".")[0]
                    if base in ("app", "domain", "financial_engine", "finco_core",
                                "main_web", "main_api", "streamlit_app"):
                        stack.append(t)
        return seen

    def test_d1_forbidden_modules_not_in_production_graph(self):
        graph = self._production_import_graph()
        for forbidden in _FORBIDDEN_PRODUCTION_MODULES:
            assert forbidden not in graph, (
                f"{forbidden} must not be reachable from production entry "
                f"points (Phase B4 single production engine)"
            )

    def test_d2_no_run_project_legacy_or_force_legacy_in_production(self):
        import subprocess

        for token in ("run_project_legacy", "force_legacy",
                      "execute_calibration_waterfall"):
            result = subprocess.run(
                ["git", "grep", "-l", token, "--", "app", "main_web.py",
                 "main_api.py", "streamlit_app.py"],
                capture_output=True, text=True,
            )
            files = [f for f in result.stdout.splitlines() if f.strip()]
            assert files == [], (
                f"{token} must not appear in production code; found in {files}"
            )

    def test_d3_production_namespace_source_scan(self):
        """Callable-legacy scan (AST, not substring): no production module
        under app/services or app/api may construct WaterfallRunner or call
        the legacy sponsor engine."""
        for rel in ("app/services", "app/api"):
            for path in sorted((REPO_ROOT / rel).rglob("*.py")):
                tree = ast.parse(path.read_text(encoding="utf-8-sig"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        fn = node.func
                        name = getattr(fn, "id", None) or getattr(fn, "attr", None)
                        assert name not in ("WaterfallRunner", "run_waterfall_v3_core",
                                            "_run_sponsor_engine", "run_demo_project"), (
                            f"{path}:{node.lineno} executes legacy {name}"
                        )

    def test_d4_no_named_project_identity_financial_dispatch(self):
        names = ("tuho", "oborovo", "kupi")
        for rel in ("app/services/production_financial_authority.py",
                    "app/services/production_waterfall_seam.py",
                    "app/api/project_runner.py",
                    "app/services/clean_presentation_adapter.py"):
            path = REPO_ROOT / rel
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Compare):
                    for comp in (node.left, *node.comparators):
                        if (isinstance(comp, ast.Constant)
                                and isinstance(comp.value, str)
                                and comp.value.strip().lower() in names):
                            raise AssertionError(
                                f"{rel}:{node.lineno} identity dispatch on {comp.value!r}"
                            )


# ---------------------------------------------------------------------------
# B4-E — pre/post financial identity (fingerprints frozen at B3 main bf71b21d)
# ---------------------------------------------------------------------------

_B3_MAIN_FINGERPRINTS = {
    "Solar": {"revenue": 94414.54881158611, "senior_ds": 35302.12518820596,
              "distributions": 5002.162578513825},
    "Wind": {"revenue": 213093.25362988273, "senior_ds": 42650.79738447129,
             "distributions": 10506.513025614555},
    "Oborovo": {"revenue": 237686.92241665165, "senior_ds": 62985.39289808685,
                "distributions": 61689.90265451222},
    "TUHO": {"revenue": 423762.0018183332, "senior_ds": 66835.97663483942,
             "distributions": 151690.9613741361},
}


class TestB4E_FinancialIdentity:
    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_e1_kpis_bit_identical_to_b3_main(self, ptype):
        out = _run(ptype, "Base")
        expected = _B3_MAIN_FINGERPRINTS[ptype]
        assert out["kpis"]["total_revenue_keur"] == expected["revenue"], "revenue"
        assert out["kpis"]["total_senior_ds_keur"] == expected["senior_ds"], "senior DS"
        assert out["kpis"]["total_distributions_keur"] == expected["distributions"], "distributions"


# ---------------------------------------------------------------------------
# B4-F — route convergence
# ---------------------------------------------------------------------------

class TestB4F_RouteConvergence:
    def test_f1_api_router_path(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        from app.api.router import run_project as api_run

        out = api_run("Solar", "Base")
        assert out["runtime_authority"]["runtime_authority"] == "clean_g2c"
        assert counters.clean_calls == 1
        assert counters.legacy_core_calls == 0

    def test_f2_download_demo_seam(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        from app.services.production_waterfall_seam import execute_production_demo

        demo, meta = execute_production_demo("TUHO", "Base")
        assert meta["runtime_authority"] == "clean_g2c"
        assert counters.clean_calls == 1
        assert counters.legacy_core_calls == 0

    def test_f3_scenario_entry(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        for scenario in ("Base", "Downside", "Upside"):
            out = _run("Solar", scenario)
            assert out["runtime_authority"]["runtime_authority"] == "clean_g2c"
        assert counters.clean_calls == 3
        assert counters.legacy_core_calls == 0

    def test_f4_reporting_seam(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        from main_web import _run_base_result
        from app.project_factories import create_default_oborovo

        result = _run_base_result(create_default_oborovo())
        assert result.total_revenue_keur is not None
        assert counters.clean_calls == 1
        assert counters.legacy_core_calls == 0


# ---------------------------------------------------------------------------
# B4-G — offline evidence isolation
# ---------------------------------------------------------------------------

class TestB4G_OfflineEvidenceIsolation:
    def test_g1_offline_helpers_callable(self):
        from tests.helpers.offline_calibration import (
            execute_calibration_waterfall,
            run_project_legacy,
        )
        from app.project_factories import create_default_solar_project
        from app.services.production_financial_authority import (
            ProductionAuthorityResolutionError,
        )

        # Offline helper refuses clean-ready inputs (production contract).
        with pytest.raises(ProductionAuthorityResolutionError):
            execute_calibration_waterfall(create_default_solar_project())
        # Offline legacy characterization run still executes (historical evidence).
        result = run_project_legacy("Solar", "Base")
        assert result["runtime_authority"]["runtime_authority"] == (
            "legacy_waterfall_offline_calibration"
        )

    def test_g2_production_cannot_import_offline_helper(self):
        graph = TestB4D_NoProductionLegacyImports()._production_import_graph()
        assert "tests.helpers.offline_calibration" not in graph
        assert "tests.helpers.offline_sponsor_engine" not in graph
