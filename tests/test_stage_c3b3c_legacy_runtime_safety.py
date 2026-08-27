"""C3B3C legacy production-path runtime safety tests.

Verifies that the typed SHL interest deductibility policy (C3B3C) does not
introduce any crash or financial drift in the existing production runtime.

Formal verdict: C3B3C_BLOCKED_RUNTIME_WIRING
The shl_interest_deductibility field on TaxParams stores source metadata only.
The legacy waterfall runtime (WaterfallRunner -> run_waterfall_v3_core ->
run_waterfall) does NOT receive shl_interest_deductibility — it preserves
prior SHL-fully-deductible behavior for all projects.

SUBJECT_TO_LIMITATIONS guard: cached_run_waterfall reads shl_interest_deductibility
from inputs.tax. The _resolve_shl_deductibility_for_legacy_runtime() function
maps SUBJECT_TO_LIMITATIONS -> None, preventing a NotImplementedError crash.
SOURCE_POLICY_CAPTURED_RUNTIME_NOT_PROMOTED applies to TUHO.

EBT_POSITIVE gate: tax_loss_utilisation_gate=EBT_POSITIVE is stored as source
metadata for Oborovo and TUHO. The legacy engine does not execute EBT_POSITIVE
logic — it uses TAXABLE_INCOME_POSITIVE behavior unchanged.
SOURCE_POLICY_CAPTURED_RUNTIME_NOT_PROMOTED applies.
"""
from __future__ import annotations

import pytest

from app.project_factories import (
    create_default_oborovo_legacy_calibration,
    create_default_tuho_wind1_legacy_calibration,
)
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from finco_core.inputs._models import ShlInterestDeductibilityMode
from finco_core.waterfall.waterfall_engine import _resolve_shl_deductibility_for_legacy_runtime


# ── Runtime boundary helper ──────────────────────────────────────────────────

class TestRuntimeSupportBoundary:
    """_resolve_shl_deductibility_for_legacy_runtime() correctness."""

    def test_fully_deductible_passes_through(self):
        mode = ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE
        assert _resolve_shl_deductibility_for_legacy_runtime(mode) is mode

    def test_fully_non_deductible_passes_through(self):
        mode = ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE
        assert _resolve_shl_deductibility_for_legacy_runtime(mode) is mode

    def test_custom_deductible_percentage_passes_through(self):
        mode = ShlInterestDeductibilityMode.CUSTOM_DEDUCTIBLE_PERCENTAGE
        assert _resolve_shl_deductibility_for_legacy_runtime(mode) is mode

    def test_subject_to_limitations_mapped_to_none(self):
        # SUBJECT_TO_LIMITATIONS has no legacy implementation.
        # SOURCE_POLICY_CAPTURED_RUNTIME_NOT_PROMOTED.
        mode = ShlInterestDeductibilityMode.SUBJECT_TO_LIMITATIONS
        assert _resolve_shl_deductibility_for_legacy_runtime(mode) is None

    def test_none_passes_through(self):
        assert _resolve_shl_deductibility_for_legacy_runtime(None) is None

    def test_legacy_runtime_supported_property_correct(self):
        assert ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE.legacy_runtime_supported is True
        assert ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE.legacy_runtime_supported is True
        assert ShlInterestDeductibilityMode.CUSTOM_DEDUCTIBLE_PERCENTAGE.legacy_runtime_supported is True
        assert ShlInterestDeductibilityMode.SUBJECT_TO_LIMITATIONS.legacy_runtime_supported is False


# ── TUHO production-path regression ─────────────────────────────────────────

def _run_via_waterfall_runner(project):
    """Production path: WaterfallRunner -> run_waterfall_v3_core -> run_waterfall.

    shl_interest_deductibility is NOT passed through this path; legacy SHL-fully-
    deductible behavior is preserved regardless of TaxParams.shl_interest_deductibility.
    """
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


class TestTuhoLegacyProductionPath:
    """TUHO (SUBJECT_TO_LIMITATIONS) must not crash and must not drift financially.

    C3B3C adds source metadata (shl_interest_deductibility=SUBJECT_TO_LIMITATIONS,
    thin_cap_enabled=True) but does NOT promote it to the legacy runtime.
    SOURCE_POLICY_CAPTURED_RUNTIME_NOT_PROMOTED.
    """

    @pytest.fixture(scope="class")
    def tuho_result(self):
        return _run_via_waterfall_runner(
            create_default_tuho_wind1_legacy_calibration()
        )

    def test_tuho_production_path_does_not_crash(self, tuho_result):
        assert tuho_result is not None

    def test_tuho_source_policy_is_subject_to_limitations(self):
        # Source metadata — not a runtime assertion.
        p = create_default_tuho_wind1_legacy_calibration()
        assert p.tax.shl_interest_deductibility == ShlInterestDeductibilityMode.SUBJECT_TO_LIMITATIONS
        assert p.tax.thin_cap_enabled is True

    def test_tuho_total_tax_keur(self, tuho_result):
        # WaterfallResult.total_tax_keur is the cash-tax total (fixture R44),
        # not the separate CIT-accrual total (fixture R43).
        assert tuho_result.total_tax_keur == pytest.approx(36994.270322, rel=1e-5)

    def test_tuho_total_senior_ds_keur(self, tuho_result):
        assert tuho_result.total_senior_ds_keur == pytest.approx(65826.38828, rel=1e-5)

    def test_tuho_total_distribution_keur(self, tuho_result):
        assert tuho_result.total_distribution_keur == pytest.approx(165423.195150, rel=1e-5)

    def test_tuho_total_shl_service_keur(self, tuho_result):
        assert tuho_result.total_shl_service_keur == pytest.approx(75439.179012, rel=1e-5)

    def test_tuho_project_irr(self, tuho_result):
        assert tuho_result.project_irr == pytest.approx(0.094393, rel=1e-3)

    def test_tuho_equity_irr(self, tuho_result):
        assert tuho_result.equity_irr == pytest.approx(0.1132, rel=1e-3)


# ── Oborovo production-path regression ──────────────────────────────────────

class TestOborovoLegacyProductionPath:
    """Oborovo (FULLY_NON_DEDUCTIBLE) must not crash and must not drift financially.

    Note: The legacy waterfall engine via run_waterfall_v3_core does NOT pass
    shl_interest_deductibility. So Oborovo's FULLY_NON_DEDUCTIBLE policy is stored
    as source metadata only — the legacy runtime uses SHL-fully-deductible behavior.
    SOURCE_POLICY_CAPTURED_RUNTIME_NOT_PROMOTED for the SHL deductibility effect.

    The financial outputs below match the pre-C3B3C baseline exactly, confirming
    no unintended active-runtime drift was introduced by adding typed source metadata.
    """

    @pytest.fixture(scope="class")
    def oborovo_result(self):
        return _run_via_waterfall_runner(create_default_oborovo_legacy_calibration())

    def test_oborovo_production_path_does_not_crash(self, oborovo_result):
        assert oborovo_result is not None

    def test_oborovo_source_policy_is_fully_non_deductible(self):
        p = create_default_oborovo_legacy_calibration()
        assert p.tax.shl_interest_deductibility == ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE
        assert p.tax.foreign_shl_interest_cap_enabled is True

    def test_oborovo_total_tax_keur(self, oborovo_result):
        assert oborovo_result.total_tax_keur == pytest.approx(8490.320140, rel=1e-5)

    def test_oborovo_total_senior_ds_keur(self, oborovo_result):
        assert oborovo_result.total_senior_ds_keur == pytest.approx(63191.174225, rel=1e-5)

    def test_oborovo_total_distribution_keur(self, oborovo_result):
        assert oborovo_result.total_distribution_keur == pytest.approx(64006.489082, rel=1e-5)

    def test_oborovo_total_shl_service_keur(self, oborovo_result):
        assert oborovo_result.total_shl_service_keur == pytest.approx(37678.310203, rel=1e-5)

    def test_oborovo_project_irr(self, oborovo_result):
        assert oborovo_result.project_irr == pytest.approx(0.07973, rel=1e-3)

    def test_oborovo_equity_irr(self, oborovo_result):
        assert oborovo_result.equity_irr == pytest.approx(0.103484, rel=1e-3)
