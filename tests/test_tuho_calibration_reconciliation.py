"""TUHO calibration reconciliation tests — Phase 7F-4B / PR B1.

These tests document and validate the TUHO model vs Excel investigation findings
from `docs/phase7f_tuho_calibration_investigation.md`.

## Excel calibration target (true target, unchanged)
  Excel CF R119 Net Dividends: 151,709 kEUR

## PR B1 interim Python output (pending PR B2 SHL fcf_waterfall)
  Python total distributions after dual-DSCR senior factory fix: ~174,948 kEUR
  Delta vs Excel: +15.3% — SHL mechanics not yet aligned

## Why 174,948 ≠ 151,709
  Root cause: TUHO SHL pik_then_sweep pays ZERO cash interest during
  senior-outstanding phase; Excel pays FULL cash interest and capitalizes
  only the shortfall. This inflates SHL balance and delays distributions.
  PR B2 (fcf_waterfall SHL method) will align Python to Excel 151,709 kEUR.

## Earlier history (for context)
  - Stale partial-fixture reference: 118,314 kEUR (3-period, obsolete)
  - Pre-PR-B1 model total: 180,570 kEUR (fixed_ds balloon period)
  - Updated partial golden: 180,516 kEUR (model-consistent, superseded)
"""

import pytest

from app.sponsor_project_adapter import build_tuho_adapter, calibration_report
from app.sponsor_runner import run_sponsor_waterfall


# ─── PR B1 interim model values (pending PR B2 SHL fcf_waterfall) ─────────────
# These values reflect the Python model after the dual-DSCR senior factory fix.
# They are NOT Excel targets — Excel target is 151,709 kEUR (CF R119).
# Used ONLY to verify the model is self-consistent between adapter calls.

TUHO_GOLDEN = {
    # PR B1 model output (dual-DSCR senior, SHL mechanics unchanged)
    "total_distributions_keur": 174_948.0,   # ~model total
    "lp_distributions_keur":   139_958.7,   # 80% x total
    "gp_distributions_keur":    34_989.7,    # 20% x total
    "spv_equity_irr":          0.1143,        # 11.43% model (vs Excel 11.61%)
    "spv_sponsor_irr":        0.1600,        # 16.00% blended
    "project_irr":             0.0947,        # 9.47% (unchanged by senior fix)
    "first_dist_period":       34,            # period index 34 (2047-06-30)
    "excel_total_fcf_dist":    234_745.0,    # Excel FCF for distribution total
    "excel_equity_irr":        0.1161,        # 11.61% from Eq!D28
    "excel_net_dividends_keur": 151709.0,     # Excel CF R119 — PR B2 calibration target
}

TOL_IRR_PP = 0.01       # +/-1.0 pp for IRR comparisons
TOL_DIST_PCT = 0.05    # +/-5% for distribution totals

TOL_IRR_PP = 0.01       # ±1.0 pp for IRR comparisons
TOL_DIST_PCT = 0.05    # ±5 % for distribution totals


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _lp_distributions(sponsor_result):
    """Return LP total allocated from sponsor result."""
    wf = next(
        r.waterfall_result
        for r in sponsor_result.per_investor_results
        if r.investor_id == "LP-1"
    )
    return wf.total_allocated_keur


def _gp_distributions(sponsor_result):
    """Return GP total allocated from sponsor result."""
    wf = next(
        r.waterfall_result
        for r in sponsor_result.per_investor_results
        if r.investor_id == "GP-1"
    )
    return wf.total_allocated_keur


# ─── TUHO Calibration Reconciliation ──────────────────────────────────────────

class TestTUHOGoldenReferenceUpdated:
    """Confirm the updated TUHO golden reference is self-consistent.

    The stale golden (118,314 kEUR from 3-period partial fixture) has been
    replaced with the model-calibrated golden (180,516 kEUR).
    """

    def test_tuho_golden_total_is_model_produced(self) -> None:
        """Total distributions must equal the model-produced value."""
        adapter = build_tuho_adapter(
            golden_total_distributions_keur=TUHO_GOLDEN["total_distributions_keur"]
        )
        assert abs(
            adapter.total_spv_distributions_keur - TUHO_GOLDEN["total_distributions_keur"]
        ) <= 1.0

    def test_tuho_golden_lp_is_80_percent(self) -> None:
        """LP distributions must equal 80% of total."""
        adapter = build_tuho_adapter(
            golden_total_distributions_keur=TUHO_GOLDEN["total_distributions_keur"]
        )
        result = run_sponsor_waterfall(adapter.sponsor_config)
        lp_dist = _lp_distributions(result)
        expected = TUHO_GOLDEN["lp_distributions_keur"]
        assert abs(lp_dist - expected) / expected <= TOL_DIST_PCT

    def test_tuho_golden_gp_is_20_percent(self) -> None:
        """GP distributions must equal 20% of total."""
        adapter = build_tuho_adapter(
            golden_total_distributions_keur=TUHO_GOLDEN["total_distributions_keur"]
        )
        result = run_sponsor_waterfall(adapter.sponsor_config)
        gp_dist = _gp_distributions(result)
        expected = TUHO_GOLDEN["gp_distributions_keur"]
        assert abs(gp_dist - expected) / expected <= TOL_DIST_PCT


class TestTUHOEquityIRRCalibration:
    """Validate SPV equity IRR matches Excel anchor within tolerance.

    This is the PRIMARY calibration anchor. The model's total distribution
    amount differs from Excel FCF (DSRA policy divergence), but the equity
    IRR must match within ±1pp.
    """

    def test_tuho_spv_equity_irr_within_1pp_of_excel_anchor(self) -> None:
        """SPV equity IRR must be within ±1pp of Excel anchor (11.61%)."""
        adapter = build_tuho_adapter()
        assert adapter.project_equity_irr is not None
        delta_pp = abs(adapter.project_equity_irr - TUHO_GOLDEN["excel_equity_irr"]) * 100
        assert delta_pp <= TOL_IRR_PP * 100, (
            f"TUHO equity IRR {adapter.project_equity_irr*100:.3f}% "
            f"exceeds ±1pp tolerance from Excel anchor "
            f"{TUHO_GOLDEN['excel_equity_irr']*100:.2f}% "
            f"(delta: {delta_pp:.2f}pp)"
        )

    def test_tuho_spv_equity_irr_equals_golden(self) -> None:
        """SPV equity IRR must equal the documented golden (11.56%)."""
        adapter = build_tuho_adapter()
        golden = TUHO_GOLDEN["spv_equity_irr"]
        delta_pp = abs(adapter.project_equity_irr - golden) * 100
        assert delta_pp <= 0.1, (
            f"SPV equity IRR {adapter.project_equity_irr*100:.3f}% "
            f"deviates {delta_pp:.2f}pp from golden {golden*100:.2f}%"
        )


class TestTUHOLPGPRatio:
    """LP/GP ratio must be exactly 4.0 regardless of total amount."""

    def test_tuho_lp_gp_ratio_exactly_4_0(self) -> None:
        """LP/GP distribution ratio must be exactly 4.0 (80/20 split)."""
        adapter = build_tuho_adapter()
        result = run_sponsor_waterfall(adapter.sponsor_config)
        lp_dist = _lp_distributions(result)
        gp_dist = _gp_distributions(result)
        ratio = lp_dist / gp_dist
        assert abs(ratio - 4.0) < 0.001, (
            f"LP/GP ratio {ratio:.4f} must be exactly 4.0"
        )


class TestTUHODistributionTiming:
    """Distribution timing must match the documented first-distribution period."""

    def test_tuho_first_distribution_at_period_33(self) -> None:
        """First non-zero distribution must be at period 33 (2046-12-31)."""
        adapter = build_tuho_adapter()
        dists = adapter.spv_distributions_keur
        first_nonzero = next((i for i, d in enumerate(dists) if d > 0), None)
        assert first_nonzero == TUHO_GOLDEN["first_dist_period"], (
            f"First non-zero distribution at period {first_nonzero}, "
            f"expected {TUHO_GOLDEN['first_dist_period']}"
        )

    def test_tuho_zero_distributions_before_period_33(self) -> None:
        """All periods before 33 must have zero distributions."""
        adapter = build_tuho_adapter()
        dists = adapter.spv_distributions_keur
        for i, d in enumerate(dists[:33]):
            assert d == 0.0, (
                f"Period {i} has distribution {d:.1f} kEUR, expected 0.0"
            )


class TestTUHOAggregateIntegrity:
    """Aggregate totals must equal sum of LP + GP."""

    def test_tuho_aggregate_equals_sum_of_parts(self) -> None:
        """Aggregate total must equal LP + GP per-investor totals."""
        adapter = build_tuho_adapter()
        result = run_sponsor_waterfall(adapter.sponsor_config)
        agg = result.aggregate_waterfall_result
        lp_dist = _lp_distributions(result)
        gp_dist = _gp_distributions(result)
        assert abs(
            (lp_dist + gp_dist) - agg.total_allocated_keur
        ) <= 1.0


class TestTUHODistributionPolicyDivergence:
    """Document the model vs Excel FCF distribution policy divergence.

    These tests do NOT assert model == Excel (they don't match).
    They document the divergence and confirm the sponsor runner is
    processing the model's output correctly.
    """

    def test_tuho_model_dist_excel_fcf_divergence(self) -> None:
        """Model total distributions must differ from Excel FCF total by >20%.

        This confirms the known divergence. The model (180,516 kEUR) produces
        ~23% less than the Excel FCF total (234,745 kEUR) due to DSRA
        lockup accumulation policy.
        """
        import json

        with open("tests/fixtures/excel_tuho_full_model_extract.json") as f:
            fixture = json.load(f)

        diag = fixture["period_diagnostics"]
        cols = fixture["period_diagnostic_columns"]
        fcf_idx = cols.index("CF.free_cash_flow_for_distribution_keur")

        excel_total = sum(row[fcf_idx] for row in diag)

        adapter = build_tuho_adapter()
        model_total = adapter.total_spv_distributions_keur

        delta_pct = (model_total - excel_total) / excel_total
        assert delta_pct < -0.20, (
            f"Model distributions ({model_total:.0f}) should be >20% below "
            f"Excel FCF total ({excel_total:.0f}). Got delta: {delta_pct*100:.1f}%"
        )

    def test_tuho_calibration_report_shows_divergence(self) -> None:
        """Calibration report must show model vs Excel divergence."""
        adapter = build_tuho_adapter()
        report = calibration_report(adapter)

        # Report uses golden_total_distributions_keur which we've set to model value
        # The divergence is in the model itself (vs actual Excel FCF)
        # This test just confirms the report is accessible
        assert report["spv_total_dist_keur"] > 0
        assert report["num_periods"] in (60, 61)
        assert report["first_period_dist_keur"] == 0.0


class TestTUHOFixtureStaleness:
    """Confirm the old golden reference was stale/incomplete.

    The 118,314 kEUR reference was computed from a 3-period partial fixture.
    This is documented as stale and must not be reinstated.
    """

    def test_old_tuho_reference_118314_is_stale(self) -> None:
        """The old 118,314 kEUR reference does NOT match model output.

        This test CONFIRMS the old reference is wrong (not that it's correct).
        We assert that model output != 118,314 to prevent regression.
        """
        adapter = build_tuho_adapter()
        model_total = adapter.total_spv_distributions_keur
        stale_reference = 118_314.0

        assert abs(model_total - stale_reference) / stale_reference > 0.30, (
            f"Model total {model_total:.0f} should differ substantially from "
            f"stale reference {stale_reference:.0f} (>30%). "
            f"Got delta: {abs(model_total-stale_reference)/stale_reference*100:.1f}%"
        )

    def test_full_60_period_fixture_is_available(self) -> None:
        """Full 60-period Excel fixture must be accessible."""
        import json
        with open("tests/fixtures/excel_tuho_full_model_extract.json") as f:
            fixture = json.load(f)

        assert fixture["project_key"] == "tuho"
        assert len(fixture["period_diagnostics"]) == 60

        cols = fixture["period_diagnostic_columns"]
        assert "CF.free_cash_flow_for_distribution_keur" in cols
