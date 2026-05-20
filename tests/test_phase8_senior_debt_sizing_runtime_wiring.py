"""tests/test_phase8_senior_debt_sizing_runtime_wiring.py

Phase 8: Senior Debt Sizing Canonical Wiring — Runtime Tests.

Tests verify:
1. Flag=False (default): legacy waterfall unchanged.
2. Flag=True: canonical result attached; no runtime debt override.
3. No drift in key metrics between flag=False and flag=True.
4. R99/R102 not promoted in result attributes.
5. TUHO and Oborovo combinations runnable.

R99/R102: BLOCKED — this module does not compute distribution gates.
"""

import pytest
from dataclasses import replace

from app.project_factories import create_default_tuho_wind1, create_default_oborovo
from app.waterfall_runner import WaterfallRunConfig
from app.ui_runner import _build_period_engine


def _run_tuho(flag_value, shl=False, dep=False):
    project = create_default_tuho_wind1()
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    config = replace(config, use_senior_debt_sizing_engine=flag_value)
    if shl:
        config = replace(config, use_shl_canonical_engine=True, shl_amount_keur=32704.0)
    if dep:
        config = replace(config, use_depreciation_canonical_engine=True)
    from app.waterfall_runner import WaterfallRunner
    return WaterfallRunner(project, engine).run(config)


def _run_oborovo(flag_value, shl=False):
    project = create_default_oborovo()
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    config = replace(config, use_senior_debt_sizing_engine=flag_value)
    if shl:
        config = replace(config, use_shl_canonical_engine=True, shl_amount_keur=14621.0)
    from app.waterfall_runner import WaterfallRunner
    return WaterfallRunner(project, engine).run(config)


def _metrics(result):
    op_periods = [p for p in result.periods if getattr(p, "is_operation", False)]
    dscrs = [
        getattr(p, "dscr", 0.0)
        for p in op_periods
        if hasattr(p, "dscr") and getattr(p, "dscr", 0) not in (0.0, float("inf"))
    ]
    return {
        "total_senior_ds_keur": result.total_senior_ds_keur,
        "avg_dscr": sum(dscrs) / len(dscrs) if dscrs else 0.0,
        "min_dscr": min(dscrs) if dscrs else 0.0,
        "equity_irr": result.equity_irr,
        "project_irr": result.project_irr,
        "total_distribution_keur": result.total_distribution_keur,
    }


def _canonical_attached(result):
    return (
        hasattr(result, "_canonical_senior_debt_sizing")
        and result._canonical_senior_debt_sizing is not None
    )


def _r99_not_promoted(result):
    return not hasattr(result, "r99_audit") or result.r99_audit is None


def _r102_not_promoted(result):
    return not hasattr(result, "r102_audit") or result.r102_audit is None


class TestTohoSeniorDebtSizingFlagCombinations:
    """TUHO-WIND-1 flag combinations."""

    @pytest.mark.parametrize("shl", [False, True], ids=["shl_off", "shl_on"])
    @pytest.mark.parametrize("dep", [False, True], ids=["dep_off", "dep_on"])
    def test_tuho_no_drift(self, shl, dep):
        """Flag=False and Flag=True produce same metrics (no drift)."""
        r_off = _run_tuho(False, shl=shl, dep=dep)
        r_on  = _run_tuho(True,  shl=shl, dep=dep)

        m_off = _metrics(r_off)
        m_on  = _metrics(r_on)

        assert abs(m_off["total_senior_ds_keur"] - m_on["total_senior_ds_keur"]) <= 1.0, \
            f"Senior DS drift: {m_off['total_senior_ds_keur']} vs {m_on['total_senior_ds_keur']}"
        assert abs(m_off["avg_dscr"] - m_on["avg_dscr"]) <= 0.005, \
            f"Avg DSCR drift: {m_off['avg_dscr']:.4f} vs {m_on['avg_dscr']:.4f}"
        assert abs(m_off["equity_irr"] - m_on["equity_irr"]) <= 0.001, \
            f"Equity IRR drift: {m_off['equity_irr']:.4f} vs {m_on['equity_irr']:.4f}"

    @pytest.mark.parametrize("shl", [False, True])
    @pytest.mark.parametrize("dep", [False, True])
    def test_tuho_canonical_attached_when_flag_true(self, shl, dep):
        """Canonical result attached when flag=True."""
        r_on = _run_tuho(True, shl=shl, dep=dep)
        assert _canonical_attached(r_on), \
            "_canonical_senior_debt_sizing not attached with flag=True"

    @pytest.mark.parametrize("shl", [False, True])
    @pytest.mark.parametrize("dep", [False, True])
    def test_tuho_canonical_not_attached_when_flag_false(self, shl, dep):
        """Canonical result NOT attached when flag=False."""
        r_off = _run_tuho(False, shl=shl, dep=dep)
        assert not _canonical_attached(r_off), \
            "_canonical_senior_debt_sizing attached with flag=False"

    @pytest.mark.parametrize("shl", [False, True])
    @pytest.mark.parametrize("dep", [False, True])
    def test_tuho_r99_not_promoted(self, shl, dep):
        """R99 not in result attributes."""
        r_on = _run_tuho(True, shl=shl, dep=dep)
        assert _r99_not_promoted(r_on), "R99 found in result (should be BLOCKED)"

    @pytest.mark.parametrize("shl", [False, True])
    @pytest.mark.parametrize("dep", [False, True])
    def test_tuho_r102_not_promoted(self, shl, dep):
        """R102 not in result attributes."""
        r_on = _run_tuho(True, shl=shl, dep=dep)
        assert _r102_not_promoted(r_on), "R102 found in result (should be BLOCKED)"

    def test_tuho_all_combinations_runnable(self):
        """All TUHO combinations runnable (smoke test)."""
        for shl in [False, True]:
            for dep in [False, True]:
                r = _run_tuho(True, shl=shl, dep=dep)
                assert r is not None


class TestOborovoSeniorDebtSizingFlagCombinations:
    """OBOROVO-SOLAR-1 flag combinations."""

    @pytest.mark.parametrize("shl", [False, True], ids=["shl_off", "shl_on"])
    def test_oborovo_no_drift(self, shl):
        """Flag=False and Flag=True produce same metrics (no drift)."""
        r_off = _run_oborovo(False, shl=shl)
        r_on  = _run_oborovo(True,  shl=shl)

        m_off = _metrics(r_off)
        m_on  = _metrics(r_on)

        assert abs(m_off["total_senior_ds_keur"] - m_on["total_senior_ds_keur"]) <= 1.0
        assert abs(m_off["avg_dscr"] - m_on["avg_dscr"]) <= 0.005
        assert abs(m_off["equity_irr"] - m_on["equity_irr"]) <= 0.001

    @pytest.mark.parametrize("shl", [False, True])
    def test_oborovo_canonical_attached_when_flag_true(self, shl):
        """Canonical result attached when flag=True."""
        r_on = _run_oborovo(True, shl=shl)
        assert _canonical_attached(r_on)

    @pytest.mark.parametrize("shl", [False, True])
    def test_oborovo_canonical_not_attached_when_flag_false(self, shl):
        """Canonical result NOT attached when flag=False."""
        r_off = _run_oborovo(False, shl=shl)
        assert not _canonical_attached(r_off)

    @pytest.mark.parametrize("shl", [False, True])
    def test_oborovo_r99_not_promoted(self, shl):
        """R99 not in result attributes."""
        r_on = _run_oborovo(True, shl=shl)
        assert _r99_not_promoted(r_on)

    @pytest.mark.parametrize("shl", [False, True])
    def test_oborovo_r102_not_promoted(self, shl):
        """R102 not in result attributes."""
        r_on = _run_oborovo(True, shl=shl)
        assert _r102_not_promoted(r_on)

    def test_oborovo_all_combinations_runnable(self):
        """All Oborovo combinations runnable (smoke test)."""
        for shl in [False, True]:
            r = _run_oborovo(True, shl=shl)
            assert r is not None


class TestCanonicalSeniorDebtSizingResult:
    """Unit tests for CanonicalSeniorDebtSizingResult."""

    def test_result_fields_accessible(self):
        """Result fields are accessible and have correct types."""
        from domain.senior_debt_sizing.canonical_wiring import (
            compute_canonical_senior_debt_sizing,
            CanonicalSeniorDebtSizingResult,
        )
        result = compute_canonical_senior_debt_sizing(
            project_name="TUHO",
            sizing_cfads_keur_by_period=(1000.0, 1000.0, 1000.0, 1000.0),
            target_dscr_by_period=(1.20, 1.20, 1.41, 1.41),
        )
        assert isinstance(result, CanonicalSeniorDebtSizingResult)
        assert result.total_debt_service_capacity_keur > 0
        assert result.annuity_keur > 0
        assert len(result.debt_service_capacity_keur_by_period) == 4
        assert result.source == "canonical_senior_debt_sizing_engine"

    def test_derivation_proxy_function(self):
        """derive_sizing_cfads_from_ebitda produces correct proxy values."""
        from domain.senior_debt_sizing.canonical_wiring import (
            derive_sizing_cfads_from_ebitda,
        )
        result = derive_sizing_cfads_from_ebitda(
            ebitda_schedule=(1000.0, 1100.0, 1200.0),
            tax_rate=0.10,
        )
        assert result == (900.0, 990.0, 1080.0)  # ebitda * (1 - tax)

    def test_build_with_explicit_sizing_cfads(self):
        """build_canonical_senior_debt_sizing_from_inputs with explicit sizing CFADS."""
        from domain.senior_debt_sizing.canonical_wiring import (
            build_canonical_senior_debt_sizing_from_inputs,
        )
        explicit = (900.0, 990.0, 1080.0)
        result = build_canonical_senior_debt_sizing_from_inputs(
            project_name="TUHO",
            project_code="TUHO-WIND-1",
            ebitda_schedule=(1000.0, 1100.0, 1200.0),
            tax_rate=0.10,
            dscr_schedule=(1.20, 1.20, 1.41),
            use_explicit_sizing_cfads=True,
            explicit_sizing_cfads=explicit,
        )
        assert "Explicit" in result.notes
        assert result.sizing_cfads_keur_by_period == explicit

    def test_build_without_explicit_sizing_cfads_uses_proxy(self):
        """build_canonical_senior_debt_sizing_from_inputs uses proxy when no explicit values."""
        from domain.senior_debt_sizing.canonical_wiring import (
            build_canonical_senior_debt_sizing_from_inputs,
        )
        result = build_canonical_senior_debt_sizing_from_inputs(
            project_name="TUHO",
            project_code="TUHO-WIND-1",
            ebitda_schedule=(1000.0, 1100.0, 1200.0),
            tax_rate=0.10,
            dscr_schedule=(1.20, 1.20, 1.41),
            use_explicit_sizing_cfads=False,
            explicit_sizing_cfads=None,
        )
        assert "LEGACY PROXY" in result.notes
        assert result.sizing_cfads_keur_by_period == (900.0, 990.0, 1080.0)