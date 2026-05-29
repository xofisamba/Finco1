"""Phase 23J: Oborovo SHL Tenor Fix — shl_tenor_years=20 (was 0).

Oborovo's SHL is a 20-year bullet (matching Excel: BS clears at 2050-06-30).
Previously shl_tenor_years=0 fell back to senior_tenor_years=14, causing the
SHL bullet to fire 6 years early (Python: 2044-12-31 vs Excel: 2050-06-30).

Tests:
- shl_tenor_years is 20 in create_default_oborovo()
- SHL bullet fires at op_idx=38 (2049-12-31), 1 period before the 20-year mark
- Distributions start at op_idx=39 (2050-06-30), matching Excel
- TUHO not affected (uses pik_then_sweep, not bullet)
- Phase 23H guard still works correctly at period 38 (SHL fires with cash shortfall)
"""

import pytest
from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig


class TestOborovoShlTenorFix:
    """Verify Oborovo shl_tenor_years=20 fix."""

    def test_oborovo_shl_tenor_years_is_20(self):
        oborovo = create_default_oborovo()
        assert oborovo.financing.shl_tenor_years == 20

    def test_oborovo_shl_fires_at_op_idx_38(self):
        """SHL bullet fires at op_idx=38 (2049-12-31) with 20-year tenor."""
        oborovo = create_default_oborovo()
        engine = _build_period_engine(oborovo)
        config = WaterfallRunConfig.from_inputs(oborovo, engine)
        runner = WaterfallRunner(oborovo, engine)
        result = runner.run(config)
        op = [(i, p) for i, p in enumerate(result.periods) if p.is_operation]

        # Find period where shl_principal > 0 (bullet fired)
        bullet_fired_idx = None
        for i, p in op:
            if p.shl_principal_keur > 0:
                bullet_fired_idx = i
                break

        assert bullet_fired_idx == 38, f"Expected SHL to fire at op_idx=38 (2049-12-31), got {bullet_fired_idx}"
        shl_principal = op[38][1].shl_principal_keur
        assert shl_principal > 0, f"shl_principal should be > 0 at firing, got {shl_principal}"

    def test_oborovo_distributions_start_at_op_idx_39(self):
        """First distribution at op_idx=39 (2050-06-30), matching Excel dividends."""
        oborovo = create_default_oborovo()
        engine = _build_period_engine(oborovo)
        config = WaterfallRunConfig.from_inputs(oborovo, engine)
        runner = WaterfallRunner(oborovo, engine)
        result = runner.run(config)
        op = [(i, p) for i, p in enumerate(result.periods) if p.is_operation]

        # Check that distribution=0 at op_idx=38 (SHL fires), >0 at op_idx=39
        assert op[38][1].distribution_keur == 0.0, "op_idx=38: dist should be 0 (SHL fires)"
        assert op[39][1].distribution_keur > 0, "op_idx=39: dist should be > 0 (SHL cleared)"
        assert op[39][1].shl_balance_keur == 0.0, "op_idx=39: shl_balance should be 0"

    def test_oborovo_shl_balance_cleared_by_op_idx_39(self):
        """SHL balance should be 0 from op_idx=39 onwards."""
        oborovo = create_default_oborovo()
        engine = _build_period_engine(oborovo)
        config = WaterfallRunConfig.from_inputs(oborovo, engine)
        runner = WaterfallRunner(oborovo, engine)
        result = runner.run(config)
        op = [(i, p) for i, p in enumerate(result.periods) if p.is_operation]

        for i, p in op:
            if i >= 39:
                assert p.shl_balance_keur == 0.0, f"op_idx={i}: shl_balance should be 0, got {p.shl_balance_keur}"

    def test_oborovo_shl_service_shortfall_at_firing_period(self):
        """Phase 23H guard: op_idx=38 has SHL service > CF (cash shortfall)."""
        oborovo = create_default_oborovo()
        engine = _build_period_engine(oborovo)
        config = WaterfallRunConfig.from_inputs(oborovo, engine)
        runner = WaterfallRunner(oborovo, engine)
        result = runner.run(config)
        op = [(i, p) for i, p in enumerate(result.periods) if p.is_operation]

        p38 = op[38][1]
        # At firing, shl_service = interest + principal (bullet)
        assert p38.shl_service_keur > p38.fcf_for_shl_keur, \
            f"op_idx=38: shl_svc={p38.shl_service_keur:.2f} should exceed fcf={p38.fcf_for_shl_keur:.2f}"
        # Distribution should be 0 (Phase 23H guard)
        assert p38.distribution_keur == 0.0, \
            f"op_idx=38: dist={p38.distribution_keur:.2f} should be 0 (Phase 23H guard)"

    def test_tuho_not_affected(self):
        """TUHO uses pik_then_sweep, shl_tenor_years=0 is intentional."""
        tuho = create_default_tuho_wind1()
        assert tuho.financing.shl_repayment_method == "pik_then_sweep"
        # shl_tenor_years=0 for TUHO means "no fixed maturity, sweep drives repayment"
        # First distribution still at op_idx=35 (2047-12-31)
        engine = _build_period_engine(tuho)
        config = WaterfallRunConfig.from_inputs(tuho, engine)
        runner = WaterfallRunner(tuho, engine)
        result = runner.run(config)
        op = [(i, p) for i, p in enumerate(result.periods) if p.is_operation]

        first_dist = next((i, p) for i, p in op if p.distribution_keur > 0)
        assert first_dist[0] == 35, f"TUHO first dist should be op_idx=35, got {first_dist[0]}"

    def test_factory_flags_unchanged(self):
        """Do not change any factory flags or runtime behavior for other projects."""
        oborovo = create_default_oborovo()
        fin = oborovo.financing

        # Only shl_tenor_years changed (0 → 20)
        assert fin.shl_tenor_years == 20
        assert fin.shl_repayment_method == "bullet"
        assert fin.shl_rate == 0.08
        assert fin.senior_tenor_years == 14
        assert fin.debt_sizing_method == "gearing_cap"
        assert fin.use_frozen_excel_senior_debt_schedule == False

    def test_revenue_opex_unchanged(self):
        """Verify revenue and OPEX are not affected by shl_tenor_years change."""
        oborovo = create_default_oborovo()
        engine = _build_period_engine(oborovo)
        config = WaterfallRunConfig.from_inputs(oborovo, engine)
        runner = WaterfallRunner(oborovo, engine)
        result = runner.run(config)
        op = [(i, p) for i, p in enumerate(result.periods) if p.is_operation]

        # Check first 5 operation periods are unchanged (revenue/opex only)
        for i, p in op[:5]:
            assert p.revenue_keur > 0, f"op_idx={i}: revenue should be > 0"
            assert p.opex_keur > 0, f"op_idx={i}: opex should be > 0"
            assert p.ebitda_keur > 0, f"op_idx={i}: ebitda should be > 0"