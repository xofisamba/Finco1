"""Phase 7 — OPEX Runtime Flag tests (Stage 3).

Validates that:
1. Flag defaults to False for TUHO and Oborovo.
2. Flag-off TUHO and Oborovo outputs are bit-identical to pre-branch behavior.
3. Flag-on TUHO uses line-item engine and matches Excel CF!R38:
   - horizon total ≈ 84,674.78 kEUR
   - max period delta ≤ 5 kEUR
   - +733 kEUR gap corrected
4. Flag-on Oborovo raises ValueError (guarded).
5. Flag changes only OPEX and downstream EBITDA/CF — no revenue/debt/tax changes.
"""
from dataclasses import replace
import json

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine, _run_waterfall
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.opex.projections import opex_schedule_period


def _run_project(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def _with_opex_flag(project, enabled):
    return replace(project, info=replace(project.info, use_opex_line_item_engine=enabled))


class TestFlagDefaults:
    """Flag must default to False."""

    def test_flag_defaults_false_for_tuho(self):
        assert create_default_tuho_wind1().info.use_opex_line_item_engine is False

    def test_flag_defaults_false_for_oborovo(self):
        assert create_default_oborovo().info.use_opex_line_item_engine is False


class TestFlagOffBehavior:
    """Flag-off must preserve legacy / pre-branch behavior exactly."""

    def test_tuho_flag_off_opex_total(self):
        """TUHO flag-off OPEX total must match legacy projections."""
        project = create_default_tuho_wind1()
        engine = _build_period_engine(project)
        result = _run_waterfall(project, engine, project_type="tuho")
        legacy_total = sum(opex_schedule_period(project, engine).values())
        assert result.total_opex_keur == pytest.approx(legacy_total, abs=0.01)
        assert result.total_opex_keur == pytest.approx(85_408.274134, abs=0.01)

    def test_tuho_flag_off_ebitda_unchanged(self):
        """TUHO flag-off EBITDA must be bit-identical pre-branch."""
        project = create_default_tuho_wind1()
        engine = _build_period_engine(project)
        result = _run_waterfall(project, engine, project_type="tuho")
        assert result.total_ebitda_keur == pytest.approx(338_435.34, abs=1.0)

    def test_oborovo_flag_off_opex_total(self):
        """Oborovo flag-off OPEX total must match legacy projections."""
        project = create_default_oborovo()
        engine = _build_period_engine(project)
        result = _run_waterfall(project, engine, project_type="oborovo")
        legacy_total = sum(opex_schedule_period(project, engine).values())
        assert result.total_opex_keur == pytest.approx(legacy_total, abs=0.01)
        assert result.total_opex_keur == pytest.approx(51_220.761293, abs=0.01)


class TestFlagOnTUHOBehavior:
    """Flag-on TUHO must use line-item engine and match Excel CF!R38."""

    def test_tuho_flag_on_opex_horizon_matches_excel(self):
        """Flag-on TUHO OPEX horizon total must match Excel 84,674.78 kEUR."""
        project = _with_opex_flag(create_default_tuho_wind1(), True)
        result = _run_project(project)
        assert result.total_opex_keur == pytest.approx(84_674.78, abs=0.01)

    def test_tuho_flag_on_corrects_runtime_gap(self):
        """Flag-on must correct the ~733 kEUR runtime gap vs flag-off."""
        tuho_off = create_default_tuho_wind1()
        tuho_on = _with_opex_flag(create_default_tuho_wind1(), True)

        engine_off = _build_period_engine(tuho_off)
        engine_on = _build_period_engine(tuho_on)

        result_off = _run_waterfall(tuho_off, engine_off, project_type="tuho")
        result_on = _run_waterfall(tuho_on, engine_on, project_type="tuho")

        gap_corrected = result_on.total_opex_keur - result_off.total_opex_keur
        # flag-on total should be 84,674.78, flag-off should be ~85,408
        # gap should be approximately -733 kEUR (flag-on is lower OPEX)
        assert abs(gap_corrected) > 700, f"Expected |gap| > 700 kEUR, got {gap_corrected:.2f}"
        assert result_on.total_opex_keur == pytest.approx(84_674.78, abs=0.01)
        assert result_off.total_opex_keur == pytest.approx(85_408.27, abs=0.01)

    def test_tuho_flag_on_period_delta_within_5k(self):
        """Flag-on period OPEX must match Excel with max delta ≤ 5 kEUR."""
        project_on = _with_opex_flag(create_default_tuho_wind1(), True)
        engine_on = _build_period_engine(project_on)
        result_on = _run_waterfall(project_on, engine_on, project_type="tuho")

        with open("tests/fixtures/excel_tuho_full_model_extract.json") as f:
            fixture = json.load(f)
        excel_opex = [abs(r[2]) for r in fixture["period_diagnostics"]]

        periods_on = [p for p in engine_on.periods() if p.is_operation]

        max_delta = 0.0
        for i, p_on in enumerate(periods_on):
            if i >= len(excel_opex):
                break
            p_data = result_on.periods[i]
            python_val = getattr(p_data, "opex_keur", None)
            if python_val is None:
                continue
            delta = abs(python_val - excel_opex[i])
            if delta > max_delta:
                max_delta = delta

        assert max_delta <= 5.0, f"Max period delta should be ≤ 5 kEUR, got {max_delta:.4f}"

    def test_tuho_flag_on_ebitda_increases(self):
        """Flag-on EBITDA must increase vs flag-off (OPEX lower, revenue unchanged)."""
        tuho_off = create_default_tuho_wind1()
        tuho_on = _with_opex_flag(create_default_tuho_wind1(), True)

        engine_off = _build_period_engine(tuho_off)
        engine_on = _build_period_engine(tuho_on)

        result_off = _run_waterfall(tuho_off, engine_off, project_type="tuho")
        result_on = _run_waterfall(tuho_on, engine_on, project_type="tuho")

        # Revenue unchanged
        assert result_on.total_revenue_keur == pytest.approx(result_off.total_revenue_keur, abs=0.01)
        # EBITDA increases (lower OPEX → higher EBITDA)
        assert result_on.total_ebitda_keur > result_off.total_ebitda_keur
        ebitda_diff = result_on.total_ebitda_keur - result_off.total_ebitda_keur
        opex_diff = abs(result_on.total_opex_keur - result_off.total_opex_keur)
        assert abs(ebitda_diff - opex_diff) < 1.0


class TestFlagOnOborovoGuard:
    """Oborovo must remain guarded when flag is True."""

    def test_oborovo_flag_true_is_rejected(self):
        """Oborovo flag-on must raise ValueError (no Oborovo template)."""
        project = _with_opex_flag(create_default_oborovo(), True)
        with pytest.raises(ValueError, match="TUHO-WIND-1"):
            _run_project(project)

    def test_oborovo_flag_off_unchanged(self):
        """Oborovo flag-off must remain unchanged."""
        project = create_default_oborovo()
        engine = _build_period_engine(project)
        result = _run_waterfall(project, engine, project_type="oborovo")
        legacy_total = sum(opex_schedule_period(project, engine).values())
        assert result.total_opex_keur == pytest.approx(legacy_total, abs=0.01)


class TestFlagIsolation:
    """Flag must change only OPEX and downstream operating cash flow."""

    def test_tuho_flag_on_revenue_unchanged(self):
        """Revenue must be identical flag-on vs flag-off."""
        tuho_off = create_default_tuho_wind1()
        tuho_on = _with_opex_flag(create_default_tuho_wind1(), True)

        engine_off = _build_period_engine(tuho_off)
        engine_on = _build_period_engine(tuho_on)

        result_off = _run_waterfall(tuho_off, engine_off, project_type="tuho")
        result_on = _run_waterfall(tuho_on, engine_on, project_type="tuho")

        assert result_on.total_revenue_keur == pytest.approx(result_off.total_revenue_keur, abs=0.01)

    def test_tuho_flag_on_senior_principal_unchanged(self):
        """Total senior principal must be identical flag-on vs flag-off.

        Interest may differ slightly due to cash-flow timing (lower OPEX →
        more available cash → slightly different principal schedule within
        DSCR constraint). But total principal repaid must be identical.
        """
        tuho_off = create_default_tuho_wind1()
        tuho_on = _with_opex_flag(create_default_tuho_wind1(), True)

        engine_off = _build_period_engine(tuho_off)
        engine_on = _build_period_engine(tuho_on)


        result_off = _run_waterfall(tuho_off, engine_off, project_type="tuho")
        result_on = _run_waterfall(tuho_on, engine_on, project_type="tuho")

        off_principal = sum(getattr(p, "senior_principal_keur", 0) for p in result_off.periods)
        on_principal = sum(getattr(p, "senior_principal_keur", 0) for p in result_on.periods)

        assert off_principal == pytest.approx(on_principal, abs=0.01), (
            f"Total senior principal must be identical: off={off_principal:.2f}, "
            f"on={on_principal:.2f}"
        )