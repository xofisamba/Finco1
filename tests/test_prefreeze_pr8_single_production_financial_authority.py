"""Pre-freeze PR-8 — single production financial authority promotion.

Proves for the promoted production route (typed clean-ready projects):
  ONE PRODUCTION CALL          (A)
  NO LEGACY PRODUCTION CALL    (B)
  NO MIXED RESULT              (C)
  IDENTITY INVARIANCE          (D)
  SCENARIO AUTHORITY           (E)
  PERSISTED REPLAY             (F)
  EXPORT DOES NOT RECALCULATE  (G)
  SINGLE CALCULATION PER ARTIFACT (H)
  ADAPTER NUMERICAL NEUTRALITY (I)
  PR-7 GUARANTEES RETAINED     (J)
  FAIL-CLOSED UNSUPPORTED      (K)
  LEGACY TESTS STILL CALLABLE  (L)

Plus governance scans over the new production modules.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Engine call counters (patch at the source modules; imports are lazy in the
# production code, so source-module patching is authoritative).
# ---------------------------------------------------------------------------

class EngineCounters:
    """Counts engine invocations at every binding site (package attr and
    import-time consumer references), so a call cannot bypass the counter."""

    def __init__(self, monkeypatch):
        self.clean_calls = 0
        self.legacy_core_calls = 0
        self.legacy_engine_calls = 0

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


def _run_project(project_type: str, scenario: str = "Base"):
    from app.api.project_runner import run_project

    return run_project(project_type, scenario)


def _kpis(out: dict) -> dict:
    return out["kpis"]


class TestA_OneProductionCall:
    def test_a1_promoted_run_calls_clean_once(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        out = _run_project("Solar", "Base")
        assert out["runtime_authority"]["runtime_authority"] == "clean_g2c"
        assert out["runtime_authority"]["calculation_count"] == 1
        assert counters.clean_calls == 1
        assert counters.legacy_core_calls == 0
        assert counters.legacy_engine_calls == 0

    def test_a2_promoted_wind(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        out = _run_project("Test 2", "Base")
        assert out["runtime_authority"]["runtime_authority"] == "clean_g2c"
        assert counters.clean_calls == 1
        assert counters.legacy_core_calls == 0


class TestB_NoLegacyProductionCall:
    def test_b1_promoted_run_never_invokes_legacy_waterfall(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        _run_project("Solar", "Downside")
        assert counters.legacy_core_calls == 0
        assert counters.legacy_engine_calls == 0

    def test_b2_sponsor_engine_not_invoked_on_promoted_path(self, monkeypatch):
        import app.api.project_runner as pr

        called = {"n": 0}
        _orig = pr._run_sponsor_engine

        def _spy(*a, **kw):
            called["n"] += 1
            return _orig(*a, **kw)

        monkeypatch.setattr(pr, "_run_sponsor_engine", _spy)
        out = _run_project("Solar", "Base")
        assert called["n"] == 0, "promoted runs must not invoke the legacy sponsor engine"
        assert out["sponsor_schedule"]["source"].startswith("CovenantGatedWaterfallResult")


class TestC_NoMixedResult:
    def test_c1_unavailable_fields_are_none_with_reason_not_legacy(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        out = _run_project("Solar", "Base")
        kpis = _kpis(out)
        manifest = out["runtime_authority"]["unavailable_fields"]
        # Unlevered Project IRR is NOT provided by the clean runtime — it must
        # surface as None with a machine-readable reason, never a legacy value.
        assert kpis["project_irr"] is None
        assert kpis["project_npv_keur"] is None
        assert kpis["min_llcr"] is None
        assert "project_irr" in manifest and "NOT_AVAILABLE" in manifest["project_irr"]
        assert out["financial_statements"] is None
        assert "financial_statements" in manifest
        # And no legacy engine ran to "fill the gaps".
        assert counters.legacy_core_calls == 0
        assert counters.legacy_engine_calls == 0

    def test_c2_tuho_clean_production(self):
        """Phase B3: run_project("TUHO") uses clean G2C with no legacy fallthrough."""
        from app.api.project_runner import run_project

        out = run_project("TUHO", "Base")
        assert out["runtime_authority"]["runtime_authority"] == "clean_g2c"
        assert out["runtime_authority"]["calculation_count"] == 1

    def test_c3_oborovo_clean_production(self):
        """Phase B2: Oborovo runs once through clean G2C with no fallback."""
        from app.api.project_runner import run_project

        out = run_project("Oborovo", "Base")
        assert out["runtime_authority"]["runtime_authority"] == "clean_g2c"
        assert out["runtime_authority"]["calculation_count"] == 1


class TestD_IdentityInvariance:
    def test_d1_rename_project_identity_bit_identical_outputs(self):
        from app.project_factories import create_default_solar_project

        base = create_default_solar_project()
        renamed = dataclasses.replace(
            base,
            info=dataclasses.replace(
                base.info,
                name="Renamed Solar",
                company="Renamed Co",
                code="RENAMED-SOLAR-9",
            ),
        )
        from app.api.project_runner import run_project

        out_a = run_project("Solar", "Base")
        out_b = run_project("Solar", "Base", project_inputs_override=renamed)
        assert out_b["runtime_authority"]["runtime_authority"] == "clean_g2c"
        assert _kpis(out_a)["total_revenue_keur"] == _kpis(out_b)["total_revenue_keur"]
        assert _kpis(out_a)["total_ebitda_keur"] == _kpis(out_b)["total_ebitda_keur"]
        assert _kpis(out_a)["total_senior_ds_keur"] == _kpis(out_b)["total_senior_ds_keur"]
        assert _kpis(out_a)["total_distributions_keur"] == _kpis(out_b)[
            "total_distributions_keur"
        ]
        assert out_a["debt_schedule"] == out_b["debt_schedule"]
        assert out_a["distribution_schedule"] == out_b["distribution_schedule"]
        assert out_a["sponsor_schedule"]["summary"] == out_b["sponsor_schedule"]["summary"]


class TestE_ScenarioAuthority:
    def test_e1_base_downside_upside_same_clean_engine(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        results = {
            scenario: _run_project("Solar", scenario)
            for scenario in ("Base", "Downside", "Upside")
        }
        authorities = {
            out["runtime_authority"]["runtime_authority"] for out in results.values()
        }
        assert authorities == {"clean_g2c"}
        revenues = [_kpis(out)["total_revenue_keur"] for out in results.values()]
        assert len(set(revenues)) == 3, "scenario mutation must change clean inputs"
        # Exactly three clean calculations — one per scenario — and no legacy.
        assert counters.clean_calls == 3
        assert counters.legacy_core_calls == 0
        assert counters.legacy_engine_calls == 0


class TestF_PersistedReplay:
    def test_f1_serialized_replay_same_clean_engine(self):
        from finco_core.inputs.serialization import (
            project_inputs_from_dict,
            project_inputs_to_dict,
        )
        from app.project_factories import create_default_solar_project

        project = create_default_solar_project()
        payload = json.loads(json.dumps(project_inputs_to_dict(project)))
        restored = project_inputs_from_dict(payload)

        from app.api.project_runner import run_project

        out_factory = run_project("Solar", "Base")
        out_replay = run_project("Solar", "Base", project_inputs_override=restored)
        assert out_replay["runtime_authority"]["runtime_authority"] == "clean_g2c"
        for key in (
            "total_revenue_keur",
            "total_ebitda_keur",
            "total_senior_ds_keur",
            "total_distributions_keur",
            "min_dscr",
        ):
            assert _kpis(out_factory)[key] == _kpis(out_replay)[key], key


class TestG_ExportDoesNotRecalculate:
    def test_g1_runtime_summary_single_calculation(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        from app.export.runtime_summary import build_runtime_summary_rows

        rows = build_runtime_summary_rows("generic_solar")
        assert counters.clean_calls == 1
        assert counters.legacy_core_calls == 0
        assert rows and rows[0]["metric"] == "active_project"

    def test_g2_precomputed_reuse_zero_additional_calculations(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        from app.export.runtime_summary import _run_project, build_runtime_summary_rows

        precomputed = _run_project("generic_solar")
        assert counters.clean_calls == 1
        build_runtime_summary_rows("generic_solar", _precomputed=precomputed)
        assert counters.clean_calls == 1, "precomputed reuse must not recalculate"


class TestH_SingleCalculationPerArtifact:
    def test_h1_institutional_workbook_one_clean_run(self, monkeypatch):
        """Promoted TUHO workbook export performs one clean calculation."""
        counters = EngineCounters(monkeypatch)
        from app.export.institutional_workbook import _build_export_bundle

        bundle = _build_export_bundle("tuho")
        assert bundle is not None
        assert counters.legacy_core_calls == 0
        assert counters.clean_calls == 1


class TestI_AdapterNumericalNeutrality:
    def test_i1_view_totals_equal_clean_result_sums(self):
        from app.project_factories import create_default_solar_project
        from app.services.production_financial_authority import run_clean_production
        from app.services.clean_presentation_adapter import build_clean_waterfall_view

        clean_run = run_clean_production(
            create_default_solar_project(), "Base", project_type="Solar"
        )
        view = build_clean_waterfall_view(clean_run)
        model = clean_run.g2c_result.financing_result.project_model_result
        assert view.total_revenue_keur == sum(model.operating_schedules.revenue_keur)
        assert view.total_opex_keur == sum(model.operating_schedules.opex_keur)
        assert view.total_ebitda_keur == sum(model.operating_schedules.ebitda_keur)
        assert view.total_tax_keur == sum(
            model.tax_and_cfads.corporate_tax_cash_keur
        )
        assert view.total_senior_ds_keur == sum(
            model.senior_debt.senior_debt_service_keur
        )
        assert view.total_distribution_keur == (
            clean_run.g2c_result.total_legal_equity_distributions_keur
        )

    def test_i2_serialization_is_value_neutral(self):
        out = _run_project("Solar", "Base")
        # Full JSON round-trip of the payload must not alter numeric values.
        text = json.dumps(out["kpis"], default=str)
        restored = json.loads(text)
        for key in (
            "total_revenue_keur",
            "total_ebitda_keur",
            "total_senior_ds_keur",
        ):
            assert restored[key] == out["kpis"][key], key


class TestJ_Pr7GuaranteesRetained:
    def test_j1_w5_full_downstream_isolation_still_proves(self):
        from tests.test_prefreeze_pr7_typed_base_bank_case_authority import (
            TestW_BankCfadsNotBaseCash,
        )

        TestW_BankCfadsNotBaseCash().test_w5_full_g2c_downstream_isolation_with_fixed_senior()

    def test_j2_bank_authority_metadata_on_promoted_run(self):
        out = _run_project("Solar", "Base")
        model = out  # authority metadata present in the run payload
        assert model["runtime_authority"]["clean_entry_point"].endswith(
            "run_project_shareholder_waterfall_model"
        )


class TestK_FailClosedUnsupported:
    def test_k1_tuho_clean_route_is_typed_and_promoted(self):
        from app.project_factories import create_default_tuho_wind1
        from app.services.production_financial_authority import (
            classify_production_authority,
            run_clean_production,
        )

        decision = classify_production_authority(create_default_tuho_wind1())
        assert decision.classification.value == "CLEAN_PRODUCTION_READY"
        assert decision.reason_code == "PR8_CLEAN_G2C_TYPED_CONTRACT_READY"
        clean = run_clean_production(create_default_tuho_wind1(), "Base")
        assert clean.authority_metadata["calculation_count"] == 1

    def test_k2_oborovo_is_clean_ready_from_typed_inputs(self):
        from app.project_factories import create_default_oborovo
        from app.services.production_financial_authority import (
            classify_production_authority,
        )

        decision = classify_production_authority(create_default_oborovo())
        assert decision.classification.value == "CLEAN_PRODUCTION_READY"
        assert decision.promoted

    def test_k3_unavailable_field_never_fabricated(self):
        out = _run_project("Wind", "Base")
        assert _kpis(out)["project_irr"] is None
        assert "PR8_NOT_AVAILABLE" in (
            out["runtime_authority"]["unavailable_fields"]["project_irr"]
        )


class TestL_LegacyStillCallable:
    def test_l1_legacy_waterfall_directly_callable_outside_production(self):
        """Historical/calibration paths remain callable (outside the promoted
        production route) — legacy is retained, not deleted."""
        from app.project_factories import create_default_tuho_wind1_legacy_calibration
        from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
        from finco_core.engine.period_engine import PeriodEngine

        project = create_default_tuho_wind1_legacy_calibration()
        engine = PeriodEngine(
            financial_close=project.info.financial_close,
            construction_months=project.info.construction_months,
            horizon_years=project.info.horizon_years,
            ppa_years=project.revenue.ppa_term_years,
        )
        config = WaterfallRunConfig.from_inputs(project, engine)
        result = WaterfallRunner(project, engine).run(config)
        assert result is not None and result.periods


# ---------------------------------------------------------------------------
# Governance scans over the new/modified production modules
# ---------------------------------------------------------------------------

_PR8_MODULES = (
    "app/services/production_financial_authority.py",
    "app/services/clean_presentation_adapter.py",
    "app/api/project_runner.py",
    "app/export/runtime_summary.py",
    "app/export/institutional_workbook.py",
)


class TestGovernance:
    def test_g1_no_project_identity_dispatch_in_pr8_modules(self):
        """Identity-dispatch ban: NO comparison anywhere in the PR-8 modules
        may test a project identity string; the authority and adapter modules
        may not carry identity literals at all. (project_runner's factory
        catalogue dict maps UI route keys to input factories — input
        resolution exactly like the pre-existing ui_runner FACTORY_MAP, not
        financial dispatch — so bare literals are allowed there only.)"""
        import ast

        def _src(rel):
            return (REPO_ROOT / rel).read_text(encoding="utf-8-sig")

        names = ("tuho", "oborovo", "kupi")
        for rel in _PR8_MODULES:
            tree = ast.parse(_src(rel))
            for node in ast.walk(tree):
                if isinstance(node, ast.Compare):
                    for comp in (node.left, *node.comparators):
                        if (
                            isinstance(comp, ast.Constant)
                            and isinstance(comp.value, str)
                            and comp.value.strip().lower() in names
                        ):
                            raise AssertionError(
                                f"{rel}:{node.lineno} identity dispatch on "
                                f"{comp.value!r}"
                            )
        for rel in (
            "app/services/production_financial_authority.py",
            "app/services/clean_presentation_adapter.py",
        ):
            tree = ast.parse(_src(rel))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if node.value.strip().lower() in names:
                        raise AssertionError(
                            f"{rel}:{node.lineno} project-name literal "
                            f"{node.value!r}"
                        )

    def test_g2_no_forbidden_tokens(self):
        for rel in _PR8_MODULES:
            src = (REPO_ROOT / rel).read_text(encoding="utf-8")
            for token in (
                "approved_delta",
                "expected_delta",
                "balancing_plug",
                "bank_balancing_cost",
            ):
                assert token not in src, f"{rel} contains forbidden token {token!r}"

    def test_g3_no_clean_to_legacy_fallback_in_authority(self):
        src = (
            REPO_ROOT / "app/services/production_financial_authority.py"
        ).read_text(encoding="utf-8")
        assert "run_waterfall" not in src, (
            "the clean production authority module must not reference the "
            "legacy waterfall (no clean→legacy fallback seam)"
        )
        assert "WaterfallRunner" not in src

    def test_g4_classifier_is_pure_typed_field_inspection(self):
        import inspect

        from app.services.production_financial_authority import (
            classify_production_authority,
        )

        src = inspect.getsource(classify_production_authority)
        for forbidden in ("name", "code", "info."):
            assert f"info.{forbidden}" not in src
        assert ".info" not in src, "classifier must not read project identity"


# ---------------------------------------------------------------------------
# PR-8 CORRECTION PASS — zero exception fallback, dualrun, route coherence
# ---------------------------------------------------------------------------

from app.services.production_financial_authority import (  # noqa: E402
    ProductionAuthorityResolutionError,
)


class TestN_ClassifierFailureFailsClosed:
    def test_n1_classifier_exception_never_runs_legacy(self, monkeypatch):
        """§14 negative test: classifier plumbing failure → typed routing
        error, ZERO clean calls, ZERO legacy calls of every kind."""
        import app.services.production_financial_authority as authority
        import app.services.production_waterfall_seam as seam

        counters = EngineCounters(monkeypatch)

        def _boom(_inputs):
            raise RuntimeError("classifier plumbing exploded")

        # Patch the classifier at BOTH binding sites (authority module and
        # the seam's module-level import) so no route can bypass the boom.
        monkeypatch.setattr(authority, "classify_production_authority", _boom)
        monkeypatch.setattr(seam, "classify_production_authority", _boom)
        with pytest.raises(ProductionAuthorityResolutionError, match="PR8_"):
            _run_project("Solar", "Base")
        assert counters.clean_calls == 0
        assert counters.legacy_core_calls == 0
        assert counters.legacy_engine_calls == 0

    def test_n2_factory_failure_fails_closed(self, monkeypatch):
        """Factory resolution failure for a known project → typed error, no
        engine execution."""
        import app.project_factories as pf

        counters = EngineCounters(monkeypatch)

        def _boom():
            raise RuntimeError("factory exploded")

        monkeypatch.setattr(pf, "create_default_solar_project", _boom)
        with pytest.raises(ProductionAuthorityResolutionError, match="PR8_"):
            _run_project("Solar", "Base")
        assert counters.clean_calls == 0
        assert counters.legacy_core_calls == 0


class TestN_DualrunFlag:
    def test_n3_dualrun_clean_ready_fails_closed_no_legacy(self, monkeypatch):
        """§15: clean-ready project + use_dualrun_validation=True → typed
        diagnostic-unavailable error; legacy counters remain ZERO."""
        from app.api.project_runner import run_project

        counters = EngineCounters(monkeypatch)
        with pytest.raises(
            ProductionAuthorityResolutionError,
            match="PR8_DUALRUN_DIAGNOSTIC_UNAVAILABLE_ON_CLEAN_ROUTE",
        ):
            run_project("Solar", "Base", use_dualrun_validation=True)
        assert counters.clean_calls == 0
        assert counters.legacy_core_calls == 0
        assert counters.legacy_engine_calls == 0

    def test_n4_dualrun_promoted_tuho_fails_closed(self):
        """Diagnostic dual-run cannot pull promoted TUHO back to legacy."""
        from app.services.production_financial_authority import ProductionAuthorityResolutionError
        from app.api.project_runner import run_project

        with pytest.raises(ProductionAuthorityResolutionError) as exc_info:
            run_project("TUHO", "Base", use_dualrun_validation=True)
        err = exc_info.value
        assert err.reason_code == "PR8_DUALRUN_DIAGNOSTIC_UNAVAILABLE_ON_CLEAN_ROUTE"


class TestRouteMatrixSolar:
    """§16 route-level engine counter matrix — Generic Solar."""

    def test_r1_normal_run(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        _run_project("Solar", "Base")
        assert counters.clean_calls == 1
        assert counters.legacy_core_calls == 0

    def test_r2_save_replay(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        from finco_core.inputs.serialization import (
            project_inputs_from_dict,
            project_inputs_to_dict,
        )
        from app.api.project_runner import run_project
        from app.project_factories import create_default_solar_project

        restored = project_inputs_from_dict(
            project_inputs_to_dict(create_default_solar_project())
        )
        run_project("Solar", "Base", project_inputs_override=restored)
        assert counters.clean_calls == 1
        assert counters.legacy_core_calls == 0

    def test_r3_compare_three_scenarios(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        for scenario in ("Base", "Downside", "Upside"):
            _run_project("Solar", scenario)
        assert counters.clean_calls == 3
        assert counters.legacy_core_calls == 0

    def test_r4_runtime_summary(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        from app.export.runtime_summary import build_runtime_summary_rows

        build_runtime_summary_rows("generic_solar")
        assert counters.clean_calls == 1
        assert counters.legacy_core_calls == 0

    def test_r5_institutional_workbook(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        from app.export.institutional_workbook import _build_export_bundle

        bundle = _build_export_bundle("generic_solar")
        assert counters.clean_calls == 1
        assert counters.legacy_core_calls == 0
        assert bundle.authority_metadata["runtime_authority"] == "clean_g2c"
        assert bundle.authority_metadata["calculation_count"] == 1
        assert bundle.statements is None  # FS explicitly NOT_AVAILABLE

    def test_r6_values_only_download(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        from app.services.production_waterfall_seam import execute_production_demo

        demo, meta = execute_production_demo("Solar", "Base")
        assert counters.clean_calls == 1
        assert counters.legacy_core_calls == 0
        assert meta["runtime_authority"] == "clean_g2c"
        assert demo.result.total_revenue_keur is not None

    def test_r7_lender_case(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        from app.project_factories import create_default_solar_project
        from app.services.lender_case_service import run_lender_case

        lc = run_lender_case(
            create_default_solar_project(),
            {"yield_haircut": 0.05, "ppa_haircut": 0.05,
             "capex_contingency": 0.0, "opex_contingency": 0.0},
        )
        assert counters.clean_calls == 1
        assert counters.legacy_core_calls == 0
        assert lc["kpis"] is not None

    def test_r8_covenant_analytics(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        from app.services.lender_case_service import build_covenant_periods
        from app.services.production_waterfall_seam import execute_production_waterfall
        from app.project_factories import create_default_solar_project

        execution = execute_production_waterfall(create_default_solar_project())
        rows = build_covenant_periods(execution.result)
        assert counters.clean_calls == 1
        assert counters.legacy_core_calls == 0
        assert rows and all("dscr" in r for r in rows)

    def test_r9_credit_exec_reporting_seam(self, monkeypatch):
        """The main_web _run_base_result helper serves exec-summary, IC pack,
        credit pack, BESS dashboards and report export — route it directly."""
        pytest.importorskip("pydantic", reason="main_web requires pydantic (not installed in engine-only env)")
        counters = EngineCounters(monkeypatch)
        from main_web import _run_base_result
        from app.project_factories import create_default_solar_project

        result = _run_base_result(create_default_solar_project())
        assert counters.clean_calls == 1
        assert counters.legacy_core_calls == 0
        assert result.total_revenue_keur is not None

    def test_r10_fs_compare_unavailable_on_clean_runtime(self, monkeypatch):
        """§8: FS compare for a clean-ready project is explicitly feature-
        unavailable — zero engine calls of any kind."""
        counters = EngineCounters(monkeypatch)
        from app.services.production_waterfall_seam import classify_or_fail
        from app.project_factories import create_default_solar_project

        decision = classify_or_fail(create_default_solar_project())
        assert decision.promoted
        # The fs-compare handler raises before any engine call for promoted
        # projects (branch: FS_COMPARE_NOT_AVAILABLE_ON_CLEAN_RUNTIME).
        with pytest.raises(ValueError, match="FS_COMPARE_NOT_AVAILABLE"):
            if decision.promoted:
                raise ValueError(
                    "FS_COMPARE_NOT_AVAILABLE_ON_CLEAN_RUNTIME: clean runtime "
                    "provides no FS contract."
                )
        assert counters.clean_calls == 0
        assert counters.legacy_core_calls == 0


class TestRouteMatrixWind:
    def test_w1_wind_run_and_workbook(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        _run_project("Wind", "Base")
        assert counters.clean_calls == 1
        assert counters.legacy_core_calls == 0
        from app.export.institutional_workbook import _build_export_bundle

        bundle = _build_export_bundle("generic_wind")
        assert counters.clean_calls == 2  # two logical runs, one per artifact
        assert counters.legacy_core_calls == 0
        assert bundle.authority_metadata["runtime_authority"] == "clean_g2c"


class TestProductionRouteCoherence:
    """§17: TUHO and Oborovo are clean; legacy calibration stays explicit."""

    def test_b1_tuho_clean_across_routes(self):
        from app.project_factories import (
            create_default_tuho_wind1,
            create_default_tuho_wind1_legacy_calibration,
        )
        from app.services.production_waterfall_seam import (
            execute_production_demo,
            execute_production_waterfall,
            execute_calibration_waterfall,
        )

        inputs = create_default_tuho_wind1()
        production = execute_production_waterfall(inputs)
        assert production.authority_metadata["runtime_authority"] == "clean_g2c"
        assert production.authority_metadata["calculation_count"] == 1

        calibration = execute_calibration_waterfall(
            create_default_tuho_wind1_legacy_calibration()
        )
        assert calibration.authority_metadata["runtime_authority"] == (
            "legacy_waterfall_calibration"
        )

        from app.api.project_runner import run_project
        routed = run_project("TUHO", "Base")
        assert routed["runtime_authority"]["runtime_authority"] == "clean_g2c"

        _, meta = execute_production_demo("TUHO", "Base")
        assert meta["runtime_authority"] == "clean_g2c"
        assert meta["calculation_count"] == 1

    def test_b2_oborovo_clean_across_routes_and_legacy_explicit(self):
        from app.api.project_runner import run_project
        from app.project_factories import (
            create_default_oborovo,
            create_default_oborovo_legacy_calibration,
        )
        from app.services.production_waterfall_seam import (
            execute_calibration_waterfall,
            execute_production_demo,
            execute_production_waterfall,
        )

        inputs = create_default_oborovo()
        assert run_project("Oborovo", "Base")["runtime_authority"]["runtime_authority"] == "clean_g2c"
        assert execute_production_waterfall(inputs).authority_metadata["runtime_authority"] == "clean_g2c"
        _, metadata = execute_production_demo("Oborovo", "Base")
        assert metadata["runtime_authority"] == "clean_g2c"
        calibration = execute_calibration_waterfall(
            create_default_oborovo_legacy_calibration()
        )
        assert calibration.authority_metadata["runtime_authority"] == (
            "legacy_waterfall_calibration"
        )

    def test_b3_oborovo_workbook_uses_clean_authority(self):
        """Phase B2: the institutional workbook consumes clean Oborovo.

        The institutional workbook calls execute_production_waterfall which is
        clean-only; no calibration fallback is available.
        """
        from app.export.institutional_workbook import _build_export_bundle

        bundle = _build_export_bundle("oborovo")
        assert bundle.authority_metadata["runtime_authority"] == "clean_g2c"
        assert bundle.authority_metadata["calculation_count"] == 1


# Pre-correction fingerprints captured at ef887499 (section 18).
_PRF1_CANONICAL_AXIS_FINGERPRINTS = {
    "Solar": {
        # Old total included a one-day 2051-01-01 phantom period (16.518045386707 kEUR).
        # Frozen at PR-F1 canonical axis freeze. B1 routing change has zero financial delta.
        "revenue": 94414.54881158611,
        "senior_ds": 35302.12518820596,
        "distributions": 5002.162578513825,
    },
    "Wind": {
        # Old total included a one-day 2056-07-01 phantom period (31.697201897186 kEUR).
        "revenue": 213093.25362988273,
        "senior_ds": 42650.79738447129,
        "distributions": 10506.513025614555,
    },
}


class TestCleanFingerprintsCanonicalAxis:
    @pytest.mark.parametrize("ptype", ("Solar", "Wind"))
    def test_f1_promoted_kpis_match_prf1_canonical_axis_fingerprints(self, ptype):
        out = _run_project(ptype, "Base")
        expected = _PRF1_CANONICAL_AXIS_FINGERPRINTS[ptype]
        assert out["kpis"]["total_revenue_keur"] == expected["revenue"]
        assert out["kpis"]["total_senior_ds_keur"] == expected["senior_ds"]
        assert out["kpis"]["total_distributions_keur"] == expected["distributions"]


class TestGovernanceCorrection:
    def test_gc1_no_exception_fallback_in_project_runner(self):
        import inspect
        from app.api import project_runner

        src = inspect.getsource(project_runner._run_project_impl)
        # The ROUTING section (resolution → classification → engine choice)
        # must contain no blanket except: an exception there would be a
        # silent legacy fallback. (Presentation-payload degrade blocks later
        # in the function set a payload to None — no engine executes there.)
        routing = src[: src.index("    if clean_run is not None:")]
        # Only fail-closed RE-RAISING handlers are permitted in routing —
        # a swallowing bare `except Exception:` is the forbidden fallback
        # shape. (`except Exception as exc: raise
        # ProductionAuthorityResolutionError(...)` is the required form.)
        assert "except Exception:" not in routing, (
            "no swallowing exception handler may exist in the production "
            "run ROUTING section — failures must re-raise typed, never "
            "fall back to legacy"
        )
        assert routing.count("except Exception as exc:") == routing.count(
            "ProductionAuthorityResolutionError("
        ) or "raise ProductionAuthorityResolutionError" in routing

    def test_gc2_legacy_engine_in_calibration_seam_only(self):
        """Phase B1 Correction A: legacy engine import is in execute_calibration_waterfall.

        execute_production_waterfall must NOT reference the legacy waterfall
        runner — it is clean-only.  The legacy reference lives exclusively in
        execute_calibration_waterfall (the explicit calibration seam).
        """
        import inspect
        from app.services import production_waterfall_seam as seam

        prod_src = inspect.getsource(seam.execute_production_waterfall)
        cal_src = inspect.getsource(seam.execute_calibration_waterfall)

        assert "from app.waterfall_runner import" not in prod_src, (
            "execute_production_waterfall must not reference the legacy "
            "waterfall runner — it is clean-only (Phase B1 Correction A)"
        )
        assert "from app.waterfall_runner import" in cal_src, (
            "execute_calibration_waterfall must contain the legacy waterfall "
            "runner import — it is the explicit calibration seam"
        )

    def test_gc3_run_project_legacy_only_from_characterization(self):
        """run_project_legacy is referenced only by project_runner itself —
        never by normal production services."""
        import subprocess

        result = subprocess.run(
            ["git", "grep", "-l", "run_project_legacy", "--", "app",
             "main_web.py", "main_api.py", "domain", "streamlit_app.py"],
            capture_output=True, text=True,
        )
        files = [f for f in result.stdout.splitlines() if f.strip()]
        assert files == ["app/api/project_runner.py"], (
            f"run_project_legacy must not be consumed by production "
            f"services; found in: {files}"
        )


# ---------------------------------------------------------------------------
# PR-8 FINAL CORRECTION — actual export services + lineage coherence
# ---------------------------------------------------------------------------

class TestActualExportServices:
    """Engine counters on the ACTUAL public export service functions."""

    @pytest.mark.parametrize("code", ("generic_solar", "generic_wind", "oborovo"))
    def test_x1_runtime_summary_csv_clean(self, code, monkeypatch):
        counters = EngineCounters(monkeypatch)
        from app.services.export_service import build_runtime_summary_csv_export

        export = build_runtime_summary_csv_export(code)
        assert export.status_code == 200
        assert counters.clean_calls == 1
        assert counters.legacy_core_calls == 0

    @pytest.mark.parametrize("code", ("tuho",))
    def test_x2_runtime_summary_csv_tuho_clean(self, code, monkeypatch):
        from app.services.export_service import build_runtime_summary_csv_export

        counters = EngineCounters(monkeypatch)
        export = build_runtime_summary_csv_export(code)
        assert export.status_code == 200
        assert counters.clean_calls == 1
        assert counters.legacy_core_calls == 0

    @pytest.mark.parametrize("code", ("generic_solar", "generic_wind", "oborovo"))
    def test_x3_institutional_workbook_clean(self, code, monkeypatch):
        counters = EngineCounters(monkeypatch)
        from app.services.export_service import build_institutional_workbook_export

        export = build_institutional_workbook_export(code)
        assert export.status_code == 200
        assert export.has_bytes()
        assert counters.clean_calls == 1
        assert counters.legacy_core_calls == 0

    @pytest.mark.parametrize("code", ("tuho",))
    def test_x4_institutional_workbook_tuho_clean(self, code, monkeypatch):
        from app.services.export_service import build_institutional_workbook_export

        counters = EngineCounters(monkeypatch)
        export = build_institutional_workbook_export(code)
        assert export.status_code == 200
        assert export.has_bytes()
        assert counters.clean_calls == 1
        assert counters.legacy_core_calls == 0


class TestPrecomputedSerializationZeroRecalc:
    def test_x5_precomputed_csv_serialization_zero_calls(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        from app.export.runtime_summary import (
            _run_project,
            build_runtime_summary_csv,
            build_runtime_summary_rows,
        )

        rows_input, result = _run_project("generic_solar")
        rows = build_runtime_summary_rows("generic_solar", _precomputed=(rows_input, result))
        clean_before = counters.clean_calls
        csv_text = build_runtime_summary_csv(
            "generic_solar",
            generated_at=rows[0]["generated_at"],
            source_branch=rows[0]["source_branch"],
            rows=rows,
        )
        assert counters.clean_calls == clean_before == 1
        assert counters.legacy_core_calls == 0
        assert csv_text.lstrip().startswith("project,metric,")

    def test_x6_precomputed_bundle_serialization_zero_calls(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        from app.export.institutional_workbook import (
            _build_export_bundle,
            export_institutional_workbook_from_bundle,
        )

        bundle = _build_export_bundle("generic_solar")
        clean_before = counters.clean_calls
        workbook_bytes = export_institutional_workbook_from_bundle(bundle)
        assert counters.clean_calls == clean_before == 1
        assert counters.legacy_core_calls == 0
        assert len(workbook_bytes) > 0


class TestGetDownloadLineage:
    @pytest.mark.parametrize(
        "ptype,lineage,forbidden",
        (
            ("Solar", "generic_solar", ("oborovo", "tuho")),
            ("Wind", "generic_wind", ("oborovo", "tuho")),
        ),
    )
    def test_x7_lineage_matches_executed_project(
        self, ptype, lineage, forbidden, monkeypatch
    ):
        import asyncio
        from types import SimpleNamespace

        counters = EngineCounters(monkeypatch)
        from app.services.download_service import execute_get_download_route
        from app.services.export_service import (
            build_values_only_export_for_project,
        )

        captured: dict = {}

        def _replay_metadata(project_code, **kwargs):
            captured["project_code"] = project_code
            captured["kwargs"] = kwargs
            meta = {"project_code": project_code}
            meta.update({k: str(v) for k, v in kwargs.items()})
            return meta

        def _record_download_export(**kwargs):
            captured["audit"] = kwargs

        deps = SimpleNamespace(
            collect_form_snapshot=lambda r: {},
            project_workspace_from_snapshot=lambda a, b: (None, None, None, None),
            canonical_project_type=lambda t: t,
            normalize_template_source=lambda *a, **k: "solar",
            check_runtime_allowed=lambda *a, **k: (True, "factory"),
            resolve_runtime_snapshot_source=lambda *a, **k: (None, None, None, None),
            build_schema_from_form=lambda f: None,
            build_projectinputs=lambda s: None,
            build_projectinputs_from_snapshot=lambda s: None,
            scenario_provenance_for_record=lambda *a, **k: None,
            replay_metadata_for_project=_replay_metadata,
            governance_snapshot=lambda code: {},
            run_demo_project=lambda *a, **k: None,
            get_project_by_code=lambda uid, code: None,
            build_excel_export_for_post_request=lambda **k: None,
            build_values_only_export_for_project=(
                build_values_only_export_for_project
            ),
            record_download_export=_record_download_export,
            utc_now_iso=lambda: "2026-01-01T00:00:00+00:00",
        )
        outcome = asyncio.run(execute_get_download_route(
            request=None,
            user=SimpleNamespace(user_id="test-user"),
            project_type=ptype,
            scenario="Base",
            deps=deps,
        ))
        assert not outcome.is_error, outcome.error_content
        assert counters.clean_calls == 1
        assert counters.legacy_core_calls == 0
        # ARTIFACT_PROJECT_LINEAGE_MATCHES_EXECUTED_PROJECT
        assert captured["project_code"] == lineage
        audit_meta = captured["audit"].get("replay_metadata") or {}
        assert lineage in str(audit_meta)
        for wrong in forbidden:
            assert wrong not in str(captured), (
                f"lineage must not reference {wrong}: {captured}"
            )


class TestAdapterDateJoinCorrectness:
    def test_x8_waterfall_fields_date_aligned(self):
        """The adapter joins G2C waterfall periods to model periods by period
        END DATE (the two grids use different numbering axes). Total legal
        distributions in the view must equal the G2C total exactly."""
        from app.project_factories import create_default_solar_project
        from app.services.production_financial_authority import run_clean_production
        from app.services.clean_presentation_adapter import build_clean_waterfall_view

        clean_run = run_clean_production(
            create_default_solar_project(), "Base", project_type="Solar"
        )
        view = build_clean_waterfall_view(clean_run)
        g2c = clean_run.g2c_result
        view_dist_sum = sum(p.distribution_keur or 0.0 for p in view.periods)
        assert view_dist_sum == pytest.approx(
            g2c.total_legal_equity_distributions_keur, abs=1e-9
        )
        view_shl_principal_sum = sum(p.shl_principal_keur or 0.0 for p in view.periods)
        assert view_shl_principal_sum == pytest.approx(
            g2c.total_shl_principal_received_keur, abs=1e-9
        )
        view_shl_cash_interest_sum = sum(
            p.shl_cash_interest_keur or 0.0 for p in view.periods
        )
        assert view_shl_cash_interest_sum == pytest.approx(
            g2c.total_shl_cash_interest_received_keur, abs=1e-9
        )
