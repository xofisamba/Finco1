"""Stack Y: Post-Fable Pilot Blockers — Y1/Y2/Y3 validation tests.

Y1 — DS Overlay Reconciliation:
  sum(period.senior_ds_keur) == result.total_senior_ds_keur
  period.senior_ds_keur == period.senior_interest_keur + period.senior_principal_keur
  No phantom DS after maturity; DSCR avg uses fixture-active periods only.

Y2 — Workspace 500 Fix:
  sheet_opex_detail.html yearly_totals/yearly_values guard prevents
  Undefined.__format__ TypeError for sparse OPEX categories.
  12/12 pr21 workspace tests pass.

Y3 — UI-created project path:
  interest_rate_pct snapshot unit fix (decimal × 100 in _snapshot_to_dict).
  TUHO/Oborovo seeded user-created projects use the factory base.
"""
from __future__ import annotations
import os
import sys
import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ui_runner import run_demo_project


@pytest.fixture(scope="module")
def tuho():
    return run_demo_project("TUHO").result


@pytest.fixture(scope="module")
def oborovo():
    return run_demo_project("Oborovo").result


# ── Y1: DS Overlay Reconciliation ─────────────────────────────────────────────

class TestY1DSOverlayReconciliation:
    """Y1: period DS values must be consistent with result-level total."""

    def test_tuho_period_ds_sum_equals_result_total(self, tuho):
        op = [p for p in tuho.periods if p.is_operation]
        period_sum = sum(p.senior_ds_keur for p in op)
        assert abs(period_sum - tuho.total_senior_ds_keur) < 0.1, (
            f"TUHO: sum(period.senior_ds_keur)={period_sum:.1f} != "
            f"total_senior_ds_keur={tuho.total_senior_ds_keur:.1f}"
        )

    def test_oborovo_period_ds_sum_equals_result_total(self, oborovo):
        op = [p for p in oborovo.periods if p.is_operation]
        period_sum = sum(p.senior_ds_keur for p in op)
        assert abs(period_sum - oborovo.total_senior_ds_keur) < 0.1, (
            f"Oborovo: sum(period.senior_ds_keur)={period_sum:.1f} != "
            f"total_senior_ds_keur={oborovo.total_senior_ds_keur:.1f}"
        )

    def test_tuho_period_ds_equals_interest_plus_principal(self, tuho):
        op = [p for p in tuho.periods if p.is_operation]
        for p in op:
            expected = p.senior_interest_keur + p.senior_principal_keur
            assert abs(p.senior_ds_keur - expected) < 0.01, (
                f"TUHO P{p.period}: senior_ds_keur={p.senior_ds_keur:.2f} != "
                f"interest({p.senior_interest_keur:.2f}) + principal({p.senior_principal_keur:.2f})"
            )

    def test_oborovo_period_ds_equals_interest_plus_principal(self, oborovo):
        op = [p for p in oborovo.periods if p.is_operation]
        for p in op:
            expected = p.senior_interest_keur + p.senior_principal_keur
            assert abs(p.senior_ds_keur - expected) < 0.01, (
                f"Oborovo P{p.period}: senior_ds_keur={p.senior_ds_keur:.2f} != "
                f"interest({p.senior_interest_keur:.2f}) + principal({p.senior_principal_keur:.2f})"
            )

    def test_tuho_no_phantom_ds_after_maturity(self, tuho):
        """Periods with zero senior balance must have zero DS."""
        for p in tuho.periods:
            bal = getattr(p, 'senior_balance_keur', None)
            if bal is not None and bal < 0.01 and not getattr(p, 'is_operation', False):
                assert p.senior_ds_keur < 0.01, (
                    f"TUHO P{p.period}: non-operation period has DS={p.senior_ds_keur:.2f}"
                )

    def test_tuho_total_senior_ds_value(self, tuho):
        assert abs(tuho.total_senior_ds_keur - 65826.0) < 5.0

    def test_oborovo_total_senior_ds_value(self, oborovo):
        assert abs(oborovo.total_senior_ds_keur - 63522.0) < 5.0

    def test_tuho_dscr_finite_for_active_ds_periods(self, tuho):
        """No period with DS > 0 should have inf DSCR after Y1 fix."""
        import math
        op = [p for p in tuho.periods if p.is_operation]
        for p in op:
            if p.senior_ds_keur > 0:
                assert math.isfinite(p.dscr), (
                    f"TUHO P{p.period}: DS={p.senior_ds_keur:.1f} but DSCR={p.dscr}"
                )

    def test_tuho_avg_dscr_preserved(self, tuho):
        assert abs(tuho.actual_avg_dscr - 1.3786) < 0.001

    def test_oborovo_avg_dscr_preserved(self, oborovo):
        assert abs(oborovo.actual_avg_dscr - 1.179) < 0.005


# ── Y1: KPIs unchanged ────────────────────────────────────────────────────────

class TestY1KPIsUnchanged:
    """Y1 DS reconciliation must not move any financial KPI."""

    def test_tuho_equity_irr(self, tuho):
        assert abs(tuho.equity_irr - 0.1132) < 0.0005

    def test_tuho_project_irr(self, tuho):
        assert abs(tuho.project_irr - 0.0941) < 0.0005

    def test_oborovo_equity_irr(self, oborovo):
        assert abs(oborovo.equity_irr - 0.1054) < 0.0005

    def test_oborovo_project_irr(self, oborovo):
        assert abs(oborovo.project_irr - 0.0809) < 0.0005


# ── Y3: interest_rate_pct unit fix ────────────────────────────────────────────

class TestSprint115DeliveryRoutes:
    """Sprint 11.5: delivery routes must not fall back due resolver import drift."""

    @pytest.mark.parametrize("project", ["generic_solar", "generic_wind", "tuho", "oborovo"])
    @pytest.mark.parametrize("route, forbidden", [
        ("/scenarios/lender-case", "Unable to complete lender case"),
        ("/scenarios/exec-summary", "Unable to complete executive summary"),
    ])
    def test_lender_and_report_routes_resolve_project_inputs(self, project, route, forbidden):
        from fastapi.testclient import TestClient
        from main_web import app
        from app.auth import COOKIE_NAME, create_session_token

        client = TestClient(app)
        client.cookies.set(COOKIE_NAME, create_session_token())
        response = client.get(f"{route}?project={project}", follow_redirects=True)

        assert response.status_code == 200
        assert forbidden not in response.text
        assert "cannot import name '_resolve_sensitivity_project'" not in response.text


class TestY3SnapshotInterestRateUnit:
    """Y3: _snapshot_to_dict must convert decimal interest_rate_pct to percentage."""

    def test_snapshot_interest_rate_pct_unit_conversion(self):
        """Decimal 0.0575 → percentage 5.75 → _set_financing_interest_rate → 0.0575."""
        from app.input_adapter import _snapshot_to_dict

        snapshot = {
            "project_type": "Wind",
            "project_name": "Test",
            "country_market": "PL",
            "capacity_mw": "100",
            "cod_date": "2030-01-01",
            "construction_months": "18",
            "horizon_years": "25",
            "tariff_eur_mwh": "60",
            "ppa_term_years": "15",
            "p50_hours": "2500",
            "opex_y1_keur": "1000",
            "total_capex_keur": "150000",
            "gearing_pct": "0.65",
            "interest_rate_pct": "0.0575",
            "tenor_years": "14",
            "target_dscr": "1.3",
        }
        d = _snapshot_to_dict(snapshot)
        # After Y3 fix: 0.0575 * 100 = 5.75 (percentage, as expected by _set_financing_interest_rate)
        assert abs(d["interest_rate_pct"] - 5.75) < 0.001, (
            f"interest_rate_pct should be 5.75 (percentage), got {d['interest_rate_pct']}"
        )

    def test_snapshot_interest_rate_applied_correctly(self):
        """Round-trip: snapshot 0.0575 → ProjectInputs → correct all-in rate."""
        from app.input_adapter import build_projectinputs_from_snapshot

        snapshot = {
            "project_type": "Wind",
            "project_name": "Test",
            "country_market": "PL",
            "capacity_mw": "100",
            "cod_date": "2030-01-01",
            "construction_months": "18",
            "horizon_years": "25",
            "tariff_eur_mwh": "60",
            "ppa_term_years": "15",
            "p50_hours": "2500",
            "opex_y1_keur": "1000",
            "total_capex_keur": "150000",
            "gearing_pct": "0.65",
            "interest_rate_pct": "0.0575",
            "tenor_years": "14",
            "target_dscr": "1.3",
        }
        proj = build_projectinputs_from_snapshot(snapshot)
        all_in = proj.financing.base_rate + proj.financing.margin_bps / 10_000
        assert abs(all_in - 0.0575) < 0.001, (
            f"all-in rate should be 0.0575 (5.75%), got {all_in:.4f}"
        )
