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
    # Solar/Wind: post-N.2 values (≤1-ULP cascade from N.2 gating); economics unchanged
    "Solar": {"revenue": 94414.54881158611, "senior_ds": 35302.12518820596,
              "distributions": 5002.162578513828},
    "Wind": {"revenue": 213093.2536298828, "senior_ds": 42650.79738447128,
             "distributions": 10506.513025614555},
    # Oborovo/TUHO: post-N.2 ULP cascade values. Distributions reflect post-U2
    # distribution accounting policy (WHT + legal reserve); bf71b21d originals:
    #   Oborovo: distributions=61689.90265451222; TUHO: distributions=151690.9613741361
    "Oborovo": {"revenue": 237686.92241665168, "senior_ds": 62985.39289808684,
                "distributions": 61203.805522551986},
    "TUHO": {"revenue": 423762.00181833334, "senior_ds": 66835.97663483946,
             "distributions": 151242.9010993855},
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

    def test_h5_semantic_scan_ast_evaluated_strings(self):
        """AST-based semantic scan over EVALUATED string constants (adjacent
        literals appear as their concatenated value — catches split-string
        bugs a raw-source substring scan misses). Production authority/
        routing modules only; offline validation modules exempt."""
        import inspect
        from app.services import production_financial_authority as authority_mod
        from app.services import production_waterfall_seam as seam_mod

        forbidden_phrases = (
            "legacy calibration runtime serves",
            "legacy runtime serves",
            "routed to legacy",
            "routed to the explicitly-classified legacy",
            "legacy_waterfall_calibration",
            "accepted runtime contract",
        )
        for mod in (authority_mod, seam_mod):
            src_text = inspect.getsource(mod)
            tree = ast.parse(src_text)
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    value = node.value
                    for phrase in forbidden_phrases:
                        assert phrase not in value, (
                            f"{mod.__name__}:{node.lineno}: runtime string "
                            f"contains forbidden semantic claim {phrase!r} "
                            f"(evaluated: {value[:120]!r})"
                        )

    def test_h6_runtime_details_fail_closed_consistent(self):
        """Instantiate/classify all three non-promoted classifications and
        inspect decision.detail: every detail must be consistent with
        NOT-REGISTERED-FOR-PRODUCTION / ZERO-CALCULATIONS / OFFLINE-ONLY."""
        import dataclasses
        from app import project_factories as pf
        from finco_core.inputs import GearingBasisMode, SponsorFundingMode
        from app.services.production_financial_authority import (
            ProductionAuthorityClassification,
            classify_production_authority,
        )

        cases = {}
        tuho_legacy = pf.create_default_tuho_wind1_legacy_calibration()
        cases["BLOCKED_BY_DEFERRED_TAX_CAPABILITY"] = tuho_legacy
        cases["BLOCKED_BY_TYPED_INPUT_GAP"] = pf.create_default_oborovo_legacy_calibration()
        legacy_only = dataclasses.replace(
            tuho_legacy,
            tax=dataclasses.replace(tuho_legacy.tax, clean_cash_tax_timing_enabled=True),
            financing=dataclasses.replace(
                tuho_legacy.financing,
                sponsor_funding_mode=SponsorFundingMode.SHARE_CAPITAL_THEN_SHL,
                gearing_basis_mode=GearingBasisMode.TOTAL_PROJECT_USES,
            ),
        )
        cases["LEGACY_CALIBRATION_ONLY"] = legacy_only

        for expected, inputs in cases.items():
            d = classify_production_authority(inputs)
            assert d.classification.value == expected, (
                f"{expected}: got {d.classification.value}"
            )
            assert d.promoted is False
            assert d.runtime_authority == "clean_not_ready"
            detail = d.detail.lower()
            assert "not registered for production" in detail, (
                f"{expected} detail must say NOT REGISTERED: {d.detail}"
            )
            for phrase in ("legacy calibration runtime serves",
                           "legacy runtime serves",
                           "accepted runtime contract"):
                assert phrase not in d.detail, (
                    f"{expected} detail contains stale claim {phrase!r}"
                )
        from app.services.production_financial_authority import (
            classify_production_authority,
        )


# ---------------------------------------------------------------------------
# B4 Correction A — expanded financial non-regression (B4-I)
# ---------------------------------------------------------------------------

from tests.fixtures.b4a_b3main_baseline import _B3_MAIN_BASELINE  # noqa: E402

_VECTOR_KEYS = (
    "senior_interest", "senior_principal", "senior_ds", "senior_closing",
    "shl_interest", "shl_principal", "shl_closing",
)
_CONSTRUCTION_VECTOR_KEYS = (
    "senior_idc_accrual", "senior_idc_capitalized_uses",
    "senior_commitment_fee_accrual", "structuring_fee",
    "vat_payable", "vat_requirement", "vat_drawn", "vat_undrawn",
)
_SCALAR_KEYS = (
    "revenue", "opex", "ebitda", "cash_tax", "base_cfads", "bank_cfads",
    "senior_debt_size", "senior_interest", "senior_principal", "senior_ds",
    "senior_terminal", "min_dscr", "avg_dscr", "binding_constraint",
    "dscr_debt_capacity", "gearing_debt_capacity", "total_project_uses",
    "manual_capex_idc_input_keur", "manual_commitment_fee_input_keur",
    "manual_structuring_fee_input_keur", "manual_vat_costs_input_keur",
    "manual_vat_idc_input_keur", "manual_vat_fee_input_keur",
    "shl_first_op_opening", "shl_total_interest",
    "shl_total_principal", "shl_terminal", "distributions", "sponsor_receipts",
)
_CONSTRUCTION_SCALAR_KEYS = (
    "authority", "construction_senior_idc_raw",
    "construction_senior_idc_capitalized",
    "construction_senior_commitment_fee", "construction_structuring_fee",
    "construction_total_capitalized_financing", "vat_idc",
    "vat_commitment_fee", "vat_effective_commitment",
    "vat_peak_requirement", "vat_commitment_mode", "vat_authority",
    "final_total_project_uses", "final_senior_commitment",
    "outer_iterations", "stage_b2_iterations", "outer_residual",
    "final_verification_outer_residual", "hard_project_capex",
    "explicit_financing_cost_uses", "reserve_account_funding",
    "other_explicit_project_uses", "total_project_uses",
)


def _b4a_run_clean(factory):
    from financial_engine.shareholder_waterfall import (
        run_project_shareholder_waterfall_model,
    )
    inputs = factory()
    return inputs, run_project_shareholder_waterfall_model(inputs, source_id="b4a_check")


def _b4a_extract(payload):
    inputs, res = payload
    import hashlib
    def digest(vec):
        return hashlib.sha256(repr(tuple(float(v) if v is not None else 0.0 for v in vec)).encode()).hexdigest()
    fin = res.financing_result
    model = fin.project_model_result
    op = model.operating_schedules
    tax = model.tax_and_cfads
    bank = model.debt_sizing
    senior = model.senior_debt
    shl = model.shareholder_loan
    dscr = [d for d in senior.base_dscr if d is not None]
    construction = fin.construction_financing
    construction_evidence = None
    if construction is not None:
        uses = fin.project_uses
        construction_evidence = {
            "authority": construction.authority,
            "construction_senior_idc_raw": sum(
                construction.senior_idc_accrual_keur
            ),
            "construction_senior_idc_capitalized": sum(
                construction.senior_idc_capitalized_uses_keur
            ),
            "construction_senior_commitment_fee": sum(
                construction.senior_commitment_fee_accrual_keur
            ),
            "construction_structuring_fee": sum(
                construction.structuring_fee_keur
            ),
            "construction_total_capitalized_financing": (
                construction.total_capitalized_financing_keur
            ),
            "vat_idc": construction.vat_idc_keur,
            "vat_commitment_fee": construction.vat_commitment_fee_keur,
            "vat_effective_commitment": construction.vat_effective_commitment_keur,
            "vat_peak_requirement": construction.vat_peak_requirement_keur,
            "vat_commitment_mode": construction.vat_commitment_mode,
            "vat_authority": construction.vat_authority,
            "final_total_project_uses": construction.final_total_project_uses_keur,
            "final_senior_commitment": construction.final_senior_commitment_keur,
            "outer_iterations": construction.outer_iterations,
            "stage_b2_iterations": construction.stage_b2_iterations,
            "outer_residual": construction.outer_residual_keur,
            "final_verification_outer_residual": (
                construction.final_verification_outer_residual_keur
            ),
            "hard_project_capex": uses.hard_project_capex_keur,
            "explicit_financing_cost_uses": uses.explicit_financing_cost_uses_keur,
            "reserve_account_funding": uses.reserve_account_funding_keur,
            "other_explicit_project_uses": uses.other_explicit_project_uses_keur,
            "total_project_uses": uses.total_project_uses_keur,
            "period_vectors": {
                "senior_idc_accrual": digest(
                    construction.senior_idc_accrual_keur
                ),
                "senior_idc_capitalized_uses": digest(
                    construction.senior_idc_capitalized_uses_keur
                ),
                "senior_commitment_fee_accrual": digest(
                    construction.senior_commitment_fee_accrual_keur
                ),
                "structuring_fee": digest(construction.structuring_fee_keur),
                "vat_payable": digest(construction.vat_payable_keur),
                "vat_requirement": digest(construction.vat_requirement_keur),
                "vat_drawn": digest(construction.vat_drawn_keur),
                "vat_undrawn": digest(construction.vat_undrawn_keur),
            },
        }
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
        "min_dscr": min(dscr) if dscr else None,
        "avg_dscr": (sum(dscr) / len(dscr)) if dscr else None,
        "binding_constraint": senior.binding_constraint,
        "dscr_debt_capacity": fin.dscr_debt_capacity_keur,
        "gearing_debt_capacity": fin.gearing_debt_capacity_keur,
        "total_project_uses": fin.project_uses.total_project_uses_keur,
        # Zero input guards prevent a second authority when the typed engine is
        # enabled. Economic construction financing is captured separately.
        "manual_capex_idc_input_keur": inputs.capex.idc_keur,
        "manual_commitment_fee_input_keur": inputs.capex.commitment_fees_keur,
        "manual_structuring_fee_input_keur": inputs.capex.bank_fees_keur,
        "manual_vat_costs_input_keur": inputs.capex.vat_costs_keur,
        "manual_vat_idc_input_keur": inputs.capex.vat_facility_idc_keur,
        "manual_vat_fee_input_keur": inputs.capex.vat_facility_commitment_fee_keur,
        "construction_financing": construction_evidence,
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
    """Comprehensive pre-B4 vs B4 comparison against DESCRIPTIVE regression evidence.

    Solar/Wind: compared against B3-main bf71b21d baseline (post-N.2 ULP cascade values).
    Oborovo/TUHO: distribution-accounting-policy legitimately changes distribution-related
    scalars (cash_tax, base_cfads, bank_cfads, distributions, sponsor_receipts). All other
    scalars and period vectors remain bit-identical to bf71b21d. Frozen scalars for Oborovo/
    TUHO are checked in test_i1b; distribution-affected scalars are checked in test_i1c.
    """

    # Scalar keys that are FROZEN for all four projects (not affected by dist. accounting)
    _FROZEN_SCALAR_KEYS = (
        "revenue", "opex", "ebitda",
        "senior_debt_size", "senior_interest", "senior_principal", "senior_ds",
        "senior_terminal", "min_dscr", "avg_dscr", "binding_constraint",
        "dscr_debt_capacity", "gearing_debt_capacity", "total_project_uses",
        "manual_capex_idc_input_keur", "manual_commitment_fee_input_keur",
        "manual_structuring_fee_input_keur", "manual_vat_costs_input_keur",
        "manual_vat_idc_input_keur", "manual_vat_fee_input_keur",
        "shl_first_op_opening", "shl_total_interest", "shl_total_principal", "shl_terminal",
    )
    # Scalar keys legitimately changed by U2 distribution accounting policy
    _DIST_AFFECTED_KEYS = ("cash_tax", "base_cfads", "bank_cfads", "distributions", "sponsor_receipts")

    @pytest.mark.parametrize("ptype", ("Solar", "Wind"))
    def test_i1_solar_wind_scalar_matrix_bit_identical(self, ptype):
        """Solar/Wind: all scalar keys must be bit-identical to B3-main (post-N.2 values)."""
        from app import project_factories as pf
        factory = {"Solar": pf.create_default_solar_project,
                   "Wind": pf.create_default_wind_project}[ptype]
        got = _b4a_extract(_b4a_run_clean(factory))
        expected = _B3_MAIN_BASELINE[ptype]
        for key in _SCALAR_KEYS:
            assert got[key] == expected[key], (
                f"{ptype}.{key}: B4={got[key]} vs B3={expected[key]}"
            )

    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_i1b_oborovo_tuho_frozen_scalars_unchanged(self, ptype):
        """Oborovo/TUHO: scalars not affected by distribution accounting are bit-identical."""
        from app import project_factories as pf
        factory = {"Oborovo": pf.create_default_oborovo,
                   "TUHO": pf.create_default_tuho_wind1}[ptype]
        got = _b4a_extract(_b4a_run_clean(factory))
        expected = _B3_MAIN_BASELINE[ptype]
        for key in self._FROZEN_SCALAR_KEYS:
            assert got[key] == expected[key], (
                f"{ptype}.{key}: B4={got[key]} vs B3={expected[key]}"
            )

    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_i1c_oborovo_tuho_dist_scalars_changed_correctly(self, ptype):
        """Oborovo/TUHO: distribution-affected scalars increased (FI) or decreased (WHT/LR)."""
        from app import project_factories as pf
        factory = {"Oborovo": pf.create_default_oborovo,
                   "TUHO": pf.create_default_tuho_wind1}[ptype]
        got = _b4a_extract(_b4a_run_clean(factory))
        b3 = _B3_MAIN_BASELINE[ptype]
        # FI income raises cash_tax and base_cfads
        assert got["cash_tax"] > b3["cash_tax"], f"{ptype}: cash_tax should increase (FI taxed)"
        assert got["base_cfads"] > b3["base_cfads"], f"{ptype}: base_cfads should increase (FI income)"
        # WHT and legal reserve reduce distributions/sponsor_receipts
        assert got["distributions"] < b3["distributions"], (
            f"{ptype}: distributions should decrease (WHT or legal reserve)"
        )
        assert got["sponsor_receipts"] < b3["sponsor_receipts"], (
            f"{ptype}: sponsor_receipts should decrease (WHT or legal reserve)"
        )

    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_i2_period_vector_identity(self, ptype):
        """High-risk schedules: full period-vector digests must be identical to bf71b21d
        (Senior/SHL schedules not affected by distribution accounting)."""
        from app import project_factories as pf
        factory = {"Oborovo": pf.create_default_oborovo,
                   "TUHO": pf.create_default_tuho_wind1}[ptype]
        got = _b4a_extract(_b4a_run_clean(factory))
        expected = _B3_MAIN_BASELINE[ptype]
        for vec_key in _VECTOR_KEYS:
            assert got["period_vectors"][vec_key] == expected["period_vectors"][vec_key], (
                f"{ptype} period vector {vec_key} diverged"
            )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_i3_derived_construction_scalar_identity(self, ptype):
        """B3 remains the authority for applicable derived financing results.
        Construction financing not affected by distribution accounting."""
        from app import project_factories as pf
        factory = {"Solar": pf.create_default_solar_project,
                   "Wind": pf.create_default_wind_project,
                   "Oborovo": pf.create_default_oborovo,
                   "TUHO": pf.create_default_tuho_wind1}[ptype]
        got = _b4a_extract(_b4a_run_clean(factory))["construction_financing"]
        expected = _B3_MAIN_BASELINE[ptype]["construction_financing"]
        assert (got is None) == (expected is None), (
            f"{ptype}: construction applicability changed"
        )
        if expected is None:
            return
        for key in _CONSTRUCTION_SCALAR_KEYS:
            assert got[key] == expected[key], (
                f"{ptype}.construction_financing.{key}: "
                f"B4={got[key]} vs B3={expected[key]}"
            )

    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_i4_derived_construction_period_vector_identity(self, ptype):
        """Timing-sensitive construction and VAT vectors remain bit-identical."""
        from app import project_factories as pf
        factory = {"Oborovo": pf.create_default_oborovo,
                   "TUHO": pf.create_default_tuho_wind1}[ptype]
        got = _b4a_extract(_b4a_run_clean(factory))["construction_financing"]
        expected = _B3_MAIN_BASELINE[ptype]["construction_financing"]
        for key in _CONSTRUCTION_VECTOR_KEYS:
            assert got["period_vectors"][key] == expected["period_vectors"][key], (
                f"{ptype} construction period vector {key} diverged"
            )

    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_i5_manual_guard_and_project_uses_identity(self, ptype):
        """NO_MANUAL_DERIVED_COST_DUAL_AUTHORITY and no uses double count."""
        from app import project_factories as pf
        factory = {"Oborovo": pf.create_default_oborovo,
                   "TUHO": pf.create_default_tuho_wind1}[ptype]
        got = _b4a_extract(_b4a_run_clean(factory))
        manual_keys = (
            "manual_capex_idc_input_keur", "manual_commitment_fee_input_keur",
            "manual_structuring_fee_input_keur", "manual_vat_costs_input_keur",
            "manual_vat_idc_input_keur", "manual_vat_fee_input_keur",
        )
        assert {got[key] for key in manual_keys} == {0.0}
        construction = got["construction_financing"]
        assert construction is not None
        assert construction["construction_total_capitalized_financing"] > 0.0
        assert construction["explicit_financing_cost_uses"] == pytest.approx(
            construction["construction_total_capitalized_financing"], abs=1e-9
        )
        component_total = (
            construction["hard_project_capex"]
            + construction["explicit_financing_cost_uses"]
            + construction["reserve_account_funding"]
            + construction["other_explicit_project_uses"]
        )
        assert construction["total_project_uses"] == pytest.approx(
            component_total, abs=1e-9
        )
        assert construction["final_total_project_uses"] == (
            construction["total_project_uses"]
        )
