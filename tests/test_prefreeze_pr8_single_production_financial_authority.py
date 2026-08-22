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

    def test_c2_tuho_legacy_run_is_explicitly_classified_not_silent(self):
        out = _run_project("TUHO", "Base")
        ra = out["runtime_authority"]
        assert ra["runtime_authority"] == "legacy_waterfall_calibration"
        assert ra["reason_code"] == "PR8_BLOCKED_BY_TYPED_TUHO_TAX_RUNTIME_GAP"

    def test_c3_oborovo_legacy_run_is_explicitly_classified(self):
        out = _run_project("Oborovo", "Base")
        ra = out["runtime_authority"]
        assert ra["runtime_authority"] == "legacy_waterfall_calibration"
        assert ra["reason_code"] == "PR8_G2A_FINANCING_CONTRACT_FIELDS_NOT_TYPED"


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
    def test_h1_institutional_workbook_one_legacy_run(self, monkeypatch):
        counters = EngineCounters(monkeypatch)
        from app.export.institutional_workbook import _build_export_bundle

        bundle = _build_export_bundle("tuho")
        assert bundle.project_key == "tuho"
        assert counters.legacy_core_calls == 1, (
            "institutional workbook must run the legacy engine exactly once "
            "(previously two independent full runs)"
        )
        assert counters.clean_calls == 0


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
    def test_k1_tuho_clean_route_fails_closed_typed(self):
        from app.project_factories import create_default_tuho_wind1
        from app.services.production_financial_authority import (
            CleanProductionRunUnavailable,
            classify_production_authority,
            run_clean_production,
        )

        decision = classify_production_authority(create_default_tuho_wind1())
        assert decision.classification.value == "BLOCKED_BY_DEFERRED_TAX_CAPABILITY"
        assert decision.reason_code == "PR8_BLOCKED_BY_TYPED_TUHO_TAX_RUNTIME_GAP"
        with pytest.raises(CleanProductionRunUnavailable, match="PR8_"):
            run_clean_production(create_default_tuho_wind1(), "Base")

    def test_k2_oborovo_first_blocker_is_exact(self):
        from app.project_factories import create_default_oborovo
        from app.services.production_financial_authority import (
            classify_production_authority,
        )

        decision = classify_production_authority(create_default_oborovo())
        assert decision.classification.value == "BLOCKED_BY_TYPED_INPUT_GAP"
        assert decision.reason_code == "PR8_G2A_FINANCING_CONTRACT_FIELDS_NOT_TYPED"

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
        from app.project_factories import create_default_tuho_wind1
        from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
        from finco_core.engine.period_engine import PeriodEngine

        project = create_default_tuho_wind1()
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
