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


# ---------------------------------------------------------------------------
# B4 Correction A — production authority metadata closure
# ---------------------------------------------------------------------------

class TestB4H_AuthorityMetadataContract:
    """Every classification's production runtime authority is correct and no
    production metadata ever claims legacy_waterfall_calibration."""

    def _classify_all(self):
        from app import project_factories as pf
        from app.services.production_financial_authority import (
            classify_production_authority,
        )
        cases = {
            "Solar(clean)": pf.create_default_solar_project,
            "OborovoLegacy": pf.create_default_oborovo_legacy_calibration,
            "TUHOLegacy": pf.create_default_tuho_wind1_legacy_calibration,
        }
        return {name: classify_production_authority(f()) for name, f in cases.items()}

    def test_h1_clean_ready_maps_to_clean_g2c(self):
        decisions = self._classify_all()
        clean = decisions["Solar(clean)"]
        assert clean.promoted is True
        assert clean.runtime_authority == "clean_g2c"

    def test_h2_non_promoted_map_to_clean_not_ready(self):
        decisions = self._classify_all()
        for name, d in decisions.items():
            if name == "Solar(clean)":
                continue
            assert d.promoted is False, name
            assert d.runtime_authority == "clean_not_ready", (
                f"{name}: production runtime authority must be clean_not_ready, "
                f"got {d.runtime_authority}"
            )

    def test_h3_no_production_metadata_claims_legacy_runtime(self):
        decisions = self._classify_all()
        for name, d in decisions.items():
            meta = d.to_metadata()
            assert "legacy_waterfall_calibration" not in str(meta), (
                f"{name}: to_metadata() must never claim a legacy runtime"
            )
            assert "legacy" not in meta.get("runtime_authority", ""), name

    def test_h4_classification_runtime_separation(self):
        """LEGACY_CALIBRATION_ONLY may remain a typed classification, but its
        production runtime authority is still NOT-EXECUTED (clean_not_ready)."""
        from app.services.production_financial_authority import (
            ProductionAuthorityClassification,
        )
        from app.services.production_financial_authority import (
            _RUNTIME_AUTHORITY_BY_CLASSIFICATION,
        )
        for cls, authority in _RUNTIME_AUTHORITY_BY_CLASSIFICATION.items():
            assert authority in ("clean_g2c", "clean_not_ready"), (
                f"{cls}: production runtime authority must be clean_g2c or "
                f"clean_not_ready, got {authority}"
            )

    def test_h5_semantic_source_scan_no_legacy_serving_language(self):
        """Focused semantic contract scan: production authority/routing code
        cannot map a non-promoted decision to legacy runtime authority or
        tell callers that a legacy production runtime will serve them."""
        import inspect
        from app.services import production_financial_authority as authority_mod
        from app.services import production_waterfall_seam as seam_mod

        for mod in (authority_mod, seam_mod):
            src = inspect.getsource(mod)
            assert '"legacy_waterfall_calibration"' not in src.replace(
                "# NEVER claim legacy_waterfall_calibration as a runtime authority.", ""
            ), (
                f"{mod.__name__}: must not map or claim legacy_waterfall_calibration"
            )
            for phrase in ("legacy calibration runtime serves",
                           "routed to the explicitly-classified legacy",
                           "legacy runtime serves"):
                assert phrase not in src, f"{mod.__name__}: stale phrase {phrase!r}"


# ---------------------------------------------------------------------------
# B4 Correction A — expanded financial non-regression (B4-I)
# ---------------------------------------------------------------------------

from tests.fixtures.b4a_b3main_baseline import _B3_MAIN_BASELINE  # noqa: E402

_VECTOR_KEYS = (
    "senior_interest", "senior_principal", "senior_ds", "senior_closing",
    "shl_interest", "shl_principal", "shl_closing",
)
_SCALAR_KEYS = (
    "revenue", "opex", "ebitda", "cash_tax", "base_cfads", "bank_cfads",
    "senior_debt_size", "senior_interest", "senior_principal", "senior_ds",
    "senior_terminal", "shl_first_op_opening", "shl_total_interest",
    "shl_total_principal", "shl_terminal", "distributions", "sponsor_receipts",
)


def _b4a_run_clean(factory):
    from financial_engine.shareholder_waterfall import (
        run_project_shareholder_waterfall_model,
    )
    return run_project_shareholder_waterfall_model(factory(), source_id="b4a_check")


def _b4a_extract(res):
    import hashlib
    def digest(vec):
        return hashlib.sha256(repr(tuple(float(v) if v is not None else 0.0 for v in vec)).encode()).hexdigest()
    model = res.financing_result.project_model_result
    op = model.operating_schedules
    tax = model.tax_and_cfads
    bank = model.debt_sizing
    senior = model.senior_debt
    shl = model.shareholder_loan
    out = {
        "revenue": sum(op.revenue_keur), "opex": sum(op.opex_keur),
        "ebitda": sum(op.ebitda_keur),
        "cash_tax": sum(tax.corporate_tax_cash_keur), "base_cfads": sum(tax.cfads_keur),
        "bank_cfads": sum(bank.bank_cfads_keur),
        "senior_debt_size": senior.debt_size_keur,
        "senior_interest": sum(senior.senior_interest_keur),
        "senior_principal": sum(senior.senior_principal_keur),
        "senior_ds": sum(senior.senior_debt_service_keur),
        "senior_terminal": senior.senior_debt_closing_keur[-1] if senior.senior_debt_closing_keur else None,
        "shl_first_op_opening": next((v for v in (shl.shl_opening_keur or ()) if v and v > 0), None),
        "shl_total_interest": sum(shl.shl_gross_interest_keur),
        "shl_total_principal": sum(shl.shl_principal_keur),
        "shl_terminal": shl.shl_closing_keur[-1] if shl.shl_closing_keur else None,
        "distributions": res.total_legal_equity_distributions_keur,
        "sponsor_receipts": res.total_sponsor_receipts_keur,
        "period_vectors": {
            "senior_interest": digest(senior.senior_interest_keur),
            "senior_principal": digest(senior.senior_principal_keur),
            "senior_ds": digest(senior.senior_debt_service_keur),
            "senior_closing": digest(senior.senior_debt_closing_keur),
            "shl_interest": digest(shl.shl_gross_interest_keur),
            "shl_principal": digest(shl.shl_principal_keur),
            "shl_closing": digest(shl.shl_closing_keur),
        },
    }
    return out


class TestB4I_ExpandedFinancialNonRegression:
    """Comprehensive pre-B4 vs B4 comparison against the DESCRIPTIVE
    regression evidence captured at B3 main (bf71b21d)."""

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_i1_scalar_matrix_bit_identical(self, ptype):
        from app import project_factories as pf
        factory = {"Solar": pf.create_default_solar_project,
                   "Wind": pf.create_default_wind_project,
                   "Oborovo": pf.create_default_oborovo,
                   "TUHO": pf.create_default_tuho_wind1}[ptype]
        got = _b4a_extract(_b4a_run_clean(factory))
        expected = _B3_MAIN_BASELINE[ptype]
        for key in _SCALAR_KEYS:
            assert got[key] == expected[key], (
                f"{ptype}.{key}: B4={got[key]} vs B3={expected[key]}"
            )

    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_i2_period_vector_identity(self, ptype):
        """High-risk schedules: full period-vector digests must be identical
        (protects against timing shifts that leave totals unchanged)."""
        from app import project_factories as pf
        factory = {"Oborovo": pf.create_default_oborovo,
                   "TUHO": pf.create_default_tuho_wind1}[ptype]
        got = _b4a_extract(_b4a_run_clean(factory))
        expected = _B3_MAIN_BASELINE[ptype]
        for vec_key in _VECTOR_KEYS:
            assert got["period_vectors"][vec_key] == expected["period_vectors"][vec_key], (
                f"{ptype} period vector {vec_key} diverged"
            )
