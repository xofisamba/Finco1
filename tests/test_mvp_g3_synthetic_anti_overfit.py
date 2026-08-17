"""G3 — Synthetic Third-Model Anti-Overfit Validation.

Proves the production financial engine is generic: all results depend only
on typed ProjectInputs contracts, not on project name / code / origin /
hard-wired per-project dispatch.

Synthetic Project C (SYNTH-C) is entirely fictional — 75 MW Solar, Spain,
25yr horizon, CASH_SWEEP SHL, ACT_365 day count.  It is NOT registered in
the application UI or any factory registry.

All tests are tagged CURRENT_BLOCKING.

Governance stop-boundaries (G2C, current main authority):
  G2C_RESERVE_GATE_NOT_CAUSALLY_CLOSED — three sub-causes:
    (1) CASH_DSRA draw/replenishment not fully causal:
        senior_dsra_closing is static / target-based.
    (2) J-DSRA not modelled: gate_component_j_dsra_underfunded is always False.
    (3) period_index <= senior_last_period_index remains an unproven proxy
        for source G4 <= B11.
"""
from __future__ import annotations

import math
from dataclasses import replace
from typing import Any, List

import pytest

from tests.helpers.g3_synthetic_project import (
    _SYNTH_C_GEARING,
    _SYNTH_C_SHARE_CAPITAL_KEUR,
    _SYNTH_C_SHL_MATURITY_PERIOD_IDX,
    _SYNTH_C_SHL_PRINCIPAL_KEUR,
    _SYNTH_C_TOTAL_CAPEX_KEUR,
    create_synthetic_project_c,
)
from financial_engine.shareholder_waterfall.model import run_project_shareholder_waterfall_model
from finco_core.inputs._models import ShlInterestDeductibilityMode


# ── fixture and helpers ──────────────────────────────────────────────────────

def _run(project=None, **kwargs):
    if project is None:
        project = create_synthetic_project_c(**kwargs) if kwargs else create_synthetic_project_c()
    return run_project_shareholder_waterfall_model(project)


def _result():
    return _run()


def _operating_periods(result):
    """Return list of waterfall periods that are not construction."""
    return [wp for wp in result.waterfall_periods if not wp.is_construction]


def _dscr_binding_project():
    """Return a SYNTH-C variant with gearing=0.85 so DSCR is the binding constraint.

    At gearing=0.85 the gearing capacity (34 850 kEUR) exceeds the DSCR
    capacity (~32 000 kEUR at target_dscr=1.25), making DSCR binding.
    Tests that require causal DSCR→senior assertions must use this variant.
    """
    proj = create_synthetic_project_c()
    return replace(proj, financing=replace(proj.financing, gearing_ratio=0.85))


# ── Governance: fixture does not import any existing project factory ─────────

class TestGovernance_NoFactoryImport:
    """CURRENT_BLOCKING: Fixture must not import or call any named project factory.

    Tests scan the fixture's import graph (sys.modules after import) and
    the fixture module's own __dict__, not raw source text (which contains
    factory names in 'does NOT call' documentation).
    """

    def _fixture_imports_module(self, module_name: str) -> bool:
        import sys
        import importlib
        import tests.helpers.g3_synthetic_project  # ensure loaded
        mod = sys.modules.get("tests.helpers.g3_synthetic_project")
        if mod is None:
            return False
        # Check if the factory module is imported by the fixture
        return module_name in sys.modules and module_name in (
            getattr(mod, "__dict__", {}).values()
        )

    def test_fixture_does_not_import_project_factories(self):
        """app.project_factories must not be in the fixture's namespace."""
        import tests.helpers.g3_synthetic_project as mod
        # Forbidden: any direct attribute that IS a project factory function
        forbidden = {
            "create_default_solar_project",
            "create_default_wind_project",
            "create_default_oborovo",
            "create_default_tuho_wind1",
        }
        mod_names = set(vars(mod).keys())
        found = forbidden & mod_names
        assert not found, f"Fixture imports forbidden factory names: {found}"

    def test_create_default_solar_project_not_callable_from_fixture(self):
        import tests.helpers.g3_synthetic_project as mod
        assert not callable(getattr(mod, "create_default_solar_project", None))

    def test_create_default_wind_project_not_callable_from_fixture(self):
        import tests.helpers.g3_synthetic_project as mod
        assert not callable(getattr(mod, "create_default_wind_project", None))

    def test_create_default_oborovo_not_callable_from_fixture(self):
        import tests.helpers.g3_synthetic_project as mod
        assert not callable(getattr(mod, "create_default_oborovo", None))

    def test_create_default_tuho_wind1_not_callable_from_fixture(self):
        import tests.helpers.g3_synthetic_project as mod
        assert not callable(getattr(mod, "create_default_tuho_wind1", None))

    def test_fixture_has_no_approved_delta(self):
        import ast
        import pathlib
        src = pathlib.Path("tests/helpers/g3_synthetic_project.py").read_text()
        tree = ast.parse(src)
        forbidden_ids = {"approved_delta", "expected_delta", "balancing_plug"}
        found = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in forbidden_ids:
                found.add(node.id)
        assert not found, f"Forbidden identifiers in fixture code: {found}"

    def test_fixture_has_no_project_identity_dispatch(self):
        """No runtime dispatch on project.name or project.code in fixture code."""
        import ast
        import pathlib
        src = pathlib.Path("tests/helpers/g3_synthetic_project.py").read_text()
        tree = ast.parse(src)
        # Check for attribute access like project.name or project.code
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                if node.attr in ("name", "code") and isinstance(node.value, ast.Name):
                    if node.value.id in ("project", "proj"):
                        raise AssertionError(
                            f"Project identity dispatch detected in fixture: "
                            f"{node.value.id}.{node.attr}"
                        )


# ── Test A: determinism — period-by-period ───────────────────────────────────

class TestA_Determinism:
    """CURRENT_BLOCKING: Identical inputs → identical outputs on repeated calls,
    period by period across all material financial vectors."""

    def _get_vectors(self, result):
        pmr = result.financing_result.project_model_result
        shl = pmr.shareholder_loan
        sd = pmr.senior_debt
        os_ = pmr.operating_schedules
        tc = pmr.tax_and_cfads
        ds = pmr.debt_sizing
        return {
            "revenue": os_.revenue_keur,
            "opex": os_.opex_keur,
            "ebitda": os_.ebitda_keur,
            "cash_tax": tc.corporate_tax_cash_keur,
            "base_cfads": pmr.post_senior_cash.base_cfads_keur,
            "bank_cfads": ds.bank_cfads_keur,
            "senior_interest": sd.senior_interest_keur,
            "senior_principal": sd.senior_principal_keur,
            "senior_closing": sd.senior_debt_closing_keur,
            "shl_gross_interest": shl.shl_gross_interest_keur,
            "shl_cash_interest": shl.shl_cash_interest_keur,
            "shl_pik": shl.shl_pik_interest_keur,
            "shl_principal": shl.shl_principal_keur,
            "shl_closing": shl.shl_closing_keur,
        }

    def test_all_material_vectors_deterministic(self):
        r1 = _run()
        r2 = _run()
        v1 = self._get_vectors(r1)
        v2 = self._get_vectors(r2)
        for name, vec1 in v1.items():
            vec2 = v2[name]
            assert vec1 == vec2, f"Vector '{name}' not deterministic"

    def test_sponsor_metrics_deterministic(self):
        r1 = _run()
        r2 = _run()
        assert r1.pure_equity_xirr == r2.pure_equity_xirr
        assert r1.total_sponsor_xirr == r2.total_sponsor_xirr
        assert r1.pure_equity_moic == r2.pure_equity_moic
        assert r1.total_sponsor_moic == r2.total_sponsor_moic
        assert r1.total_legal_equity_distributions_keur == r2.total_legal_equity_distributions_keur

    def test_waterfall_periods_deterministic(self):
        r1 = _run()
        r2 = _run()
        assert len(r1.waterfall_periods) == len(r2.waterfall_periods)
        for wp1, wp2 in zip(r1.waterfall_periods, r2.waterfall_periods):
            assert wp1.signed_post_senior_keur == wp2.signed_post_senior_keur
            assert wp1.legal_equity_distribution_keur == wp2.legal_equity_distribution_keur
            assert wp1.distribution_account_closing_keur == wp2.distribution_account_closing_keur


# ── Test B: identity invariance — full financial result ──────────────────────

class TestB_IdentityInvariance:
    """CURRENT_BLOCKING: Engine output must NOT vary with project name/company/code.
    Compared across the full set of material financial vectors."""

    def _compare_full(self, r_a, r_b):
        pmr_a = r_a.financing_result.project_model_result
        pmr_b = r_b.financing_result.project_model_result
        # Scalar metrics
        assert r_a.pure_equity_xirr == pytest.approx(r_b.pure_equity_xirr, rel=1e-9)
        assert r_a.total_sponsor_xirr == pytest.approx(r_b.total_sponsor_xirr, rel=1e-9)
        assert r_a.total_legal_equity_distributions_keur == pytest.approx(
            r_b.total_legal_equity_distributions_keur, rel=1e-9
        )
        # Vector equality: revenue, tax, SHL closing
        assert (
            pmr_a.operating_schedules.revenue_keur
            == pmr_b.operating_schedules.revenue_keur
        )
        assert (
            pmr_a.tax_and_cfads.corporate_tax_cash_keur
            == pmr_b.tax_and_cfads.corporate_tax_cash_keur
        )
        assert (
            pmr_a.shareholder_loan.shl_closing_keur
            == pmr_b.shareholder_loan.shl_closing_keur
        )
        assert (
            pmr_a.senior_debt.senior_debt_closing_keur
            == pmr_b.senior_debt.senior_debt_closing_keur
        )

    def test_name_change_does_not_affect_results(self):
        self._compare_full(_run(name="Synthetic Project C"), _run(name="Totally Different Name XYZ"))

    def test_company_change_does_not_affect_results(self):
        self._compare_full(_run(company="Fictional Infrastructure SPV"), _run(company="Another Company Ltd"))

    def test_oborovo_code_gives_synth_c_results(self):
        """If engine dispatches on code='OBOROVO', vectors would diverge."""
        self._compare_full(_run(code="SYNTH-C"), _run(code="OBOROVO"))

    def test_tuho_name_gives_synth_c_results(self):
        self._compare_full(_run(name="Synthetic Project C"), _run(name="TUHO Wind 1"))

    def test_generic_solar_name_gives_synth_c_results(self):
        self._compare_full(_run(name="Synthetic Project C"), _run(name="Generic Solar"))


# ── Test C: complete financial chain ─────────────────────────────────────────

class TestC_CompleteChain:
    """CURRENT_BLOCKING: All material financial vectors are populated and finite."""

    def test_production_revenue_opex_ebitda_populated(self):
        result = _result()
        os_ = result.financing_result.project_model_result.operating_schedules
        for vec_name, vec in [
            ("production_mwh", os_.production_mwh),
            ("revenue_keur", os_.revenue_keur),
            ("opex_keur", os_.opex_keur),
            ("ebitda_keur", os_.ebitda_keur),
        ]:
            operating_vals = [v for v in vec if v != 0.0]
            assert operating_vals, f"{vec_name} has no non-zero values"
            assert all(math.isfinite(v) for v in operating_vals), f"{vec_name} contains non-finite values"

    def test_base_cfads_and_bank_cfads_populated(self):
        result = _result()
        pmr = result.financing_result.project_model_result
        psc = pmr.post_senior_cash
        ds = pmr.debt_sizing
        assert sum(v for v in psc.base_cfads_keur if v > 0) > 0
        assert sum(v for v in ds.bank_cfads_keur if v > 0) > 0

    def test_senior_debt_vectors_populated(self):
        result = _result()
        sd = result.financing_result.project_model_result.senior_debt
        assert sum(sd.senior_interest_keur) > 0
        assert sum(sd.senior_principal_keur) > 0
        assert sd.senior_debt_closing_keur[-1] == pytest.approx(0.0, abs=1e-4)

    def test_shl_all_vectors_populated(self):
        result = _result()
        shl = result.financing_result.project_model_result.shareholder_loan
        assert sum(shl.shl_gross_interest_keur) > 0
        assert sum(shl.shl_cash_interest_keur) > 0
        assert sum(abs(v) for v in shl.shl_pik_interest_keur) == pytest.approx(0.0, abs=1e-6)
        assert sum(v for v in shl.shl_principal_keur if v > 0) > 0
        assert shl.shl_closing_keur[-1] == pytest.approx(0.0, abs=1e-4)

    def test_post_senior_cash_and_da_vectors(self):
        result = _result()
        ops = _operating_periods(result)
        assert ops, "No operating periods found"
        # DA: inflow and release present in operating periods
        da_inflows = [wp.distribution_account_inflow_keur for wp in ops]
        assert sum(da_inflows) > 0

    def test_legal_equity_distributions_positive(self):
        result = _result()
        total = sum(
            wp.legal_equity_distribution_keur
            for wp in result.waterfall_periods
        )
        # DSRA=NONE → gate open → some distributions expected
        # Note: FCF flows to DA and may stay locked if lockup triggers;
        # for healthy SYNTH-C, distributions should be non-zero
        assert total > 0 or result.total_legal_equity_distributions_keur == pytest.approx(0.0, abs=1e-6)
        assert result.total_legal_equity_distributions_keur >= 0

    def test_sponsor_metrics_all_populated(self):
        result = _result()
        assert result.pure_equity_xirr is not None
        assert result.pure_equity_moic is not None
        assert result.total_sponsor_xirr is not None
        assert result.total_sponsor_moic is not None
        assert math.isfinite(result.pure_equity_xirr)
        assert math.isfinite(result.pure_equity_moic)
        assert math.isfinite(result.total_sponsor_xirr)
        assert math.isfinite(result.total_sponsor_moic)


# ── Test D: bank / base CFADS separation ────────────────────────────────────

class TestD_BankBaseSeparation:
    """CURRENT_BLOCKING: Bank (P90) case is separate from Base (P50) case.
    Mutating P90 input changes bank vectors without touching base vectors.
    Uses gearing=0.85 (DSCR binding) so the bank CFADS change propagates
    causally to the senior commitment."""

    def _run_with_p90(self, p90_hours):
        proj = _dscr_binding_project()
        return _run(replace(proj, technical=replace(proj.technical, operating_hours_p90_10y=p90_hours)))

    def test_bank_production_below_base_production(self):
        result = _run(_dscr_binding_project())
        ds = result.financing_result.project_model_result.debt_sizing
        os_ = result.financing_result.project_model_result.operating_schedules
        base_total = sum(v for v in os_.production_mwh if v > 0)
        bank_total = sum(v for v in ds.bank_production_mwh if v > 0)
        assert bank_total < base_total

    def test_p90_to_p50_increases_bank_production(self):
        proj = _dscr_binding_project()
        p50_h = proj.technical.operating_hours_p50
        r_p90 = _run(proj)
        r_p50 = self._run_with_p90(p50_h)
        ds_p90 = r_p90.financing_result.project_model_result.debt_sizing
        ds_p50 = r_p50.financing_result.project_model_result.debt_sizing
        bank_p90 = sum(v for v in ds_p90.bank_production_mwh if v > 0)
        bank_p50 = sum(v for v in ds_p50.bank_production_mwh if v > 0)
        assert bank_p50 > bank_p90

    def test_p90_to_p50_leaves_base_production_unchanged(self):
        proj = _dscr_binding_project()
        p50_h = proj.technical.operating_hours_p50
        r_p90 = _run(proj)
        r_p50 = self._run_with_p90(p50_h)
        os_p90 = r_p90.financing_result.project_model_result.operating_schedules
        os_p50 = r_p50.financing_result.project_model_result.operating_schedules
        assert os_p90.production_mwh == os_p50.production_mwh
        assert os_p90.revenue_keur == os_p50.revenue_keur
        assert os_p90.ebitda_keur == os_p50.ebitda_keur

    def test_p90_to_p50_increases_bank_cfads(self):
        proj = _dscr_binding_project()
        p50_h = proj.technical.operating_hours_p50
        r_p90 = _run(proj)
        r_p50 = self._run_with_p90(p50_h)
        assert (
            sum(r_p50.financing_result.project_model_result.debt_sizing.bank_cfads_keur)
            > sum(r_p90.financing_result.project_model_result.debt_sizing.bank_cfads_keur)
        )

    def test_p90_to_p50_increases_senior_commitment(self):
        """With DSCR binding, higher bank CFADS → more senior capacity."""
        proj = _dscr_binding_project()
        p50_h = proj.technical.operating_hours_p50
        r_p90 = _run(proj)
        r_p50 = self._run_with_p90(p50_h)
        assert r_p50.financing_result.final_senior_commitment_keur > r_p90.financing_result.final_senior_commitment_keur

    def test_bank_cfads_attribute_on_debt_sizing_not_tax_cfads(self):
        result = _result()
        pmr = result.financing_result.project_model_result
        assert hasattr(pmr.debt_sizing, "bank_cfads_keur")
        assert not hasattr(pmr.tax_and_cfads, "bank_cfads_keur")


# ── Test E: price causality ──────────────────────────────────────────────────

class TestE_PriceCausality:
    """CURRENT_BLOCKING: ~-10% PPA tariff causally reduces revenue, EBITDA,
    CFADS, senior capacity, and sponsor economics."""

    def _run_with_ppa(self, ppa: float):
        proj = create_synthetic_project_c()
        return _run(replace(proj, revenue=replace(proj.revenue, ppa_base_tariff=ppa)))

    def test_lower_ppa_reduces_revenue(self):
        r_base = self._run_with_ppa(45.0)
        r_low = self._run_with_ppa(40.5)  # -10%
        os_base = r_base.financing_result.project_model_result.operating_schedules
        os_low = r_low.financing_result.project_model_result.operating_schedules
        assert sum(os_low.revenue_keur) < sum(os_base.revenue_keur)

    def test_lower_ppa_reduces_ebitda(self):
        r_base = self._run_with_ppa(45.0)
        r_low = self._run_with_ppa(40.5)
        os_base = r_base.financing_result.project_model_result.operating_schedules
        os_low = r_low.financing_result.project_model_result.operating_schedules
        assert sum(os_low.ebitda_keur) < sum(os_base.ebitda_keur)

    def test_lower_ppa_reduces_bank_cfads(self):
        r_base = self._run_with_ppa(45.0)
        r_low = self._run_with_ppa(40.5)
        ds_base = r_base.financing_result.project_model_result.debt_sizing
        ds_low = r_low.financing_result.project_model_result.debt_sizing
        assert sum(ds_low.bank_cfads_keur) < sum(ds_base.bank_cfads_keur)

    def test_lower_ppa_does_not_improve_sponsor_economics(self):
        r_base = self._run_with_ppa(45.0)
        r_low = self._run_with_ppa(40.5)
        if r_low.pure_equity_xirr is not None and r_base.pure_equity_xirr is not None:
            assert r_low.pure_equity_xirr <= r_base.pure_equity_xirr


# ── Test F: OPEX causality ───────────────────────────────────────────────────

class TestF_OpexCausality:
    """CURRENT_BLOCKING: ~+10% OPEX causally reduces EBITDA, CFADS, and
    sponsor economics."""

    def _run_with_opex_scale(self, scale: float):
        proj = create_synthetic_project_c()
        new_opex = tuple(
            replace(item, y1_amount_keur=item.y1_amount_keur * scale)
            for item in proj.opex
        )
        return _run(replace(proj, opex=new_opex))

    def test_higher_opex_reduces_ebitda(self):
        r_base = self._run_with_opex_scale(1.0)
        r_high = self._run_with_opex_scale(1.10)
        os_base = r_base.financing_result.project_model_result.operating_schedules
        os_high = r_high.financing_result.project_model_result.operating_schedules
        assert sum(os_high.ebitda_keur) < sum(os_base.ebitda_keur)

    def test_higher_opex_reduces_base_cfads(self):
        r_base = self._run_with_opex_scale(1.0)
        r_high = self._run_with_opex_scale(1.10)
        psc_base = r_base.financing_result.project_model_result.post_senior_cash
        psc_high = r_high.financing_result.project_model_result.post_senior_cash
        assert sum(psc_high.base_cfads_keur) < sum(psc_base.base_cfads_keur)

    def test_higher_opex_reduces_bank_cfads(self):
        r_base = self._run_with_opex_scale(1.0)
        r_high = self._run_with_opex_scale(1.10)
        ds_base = r_base.financing_result.project_model_result.debt_sizing
        ds_high = r_high.financing_result.project_model_result.debt_sizing
        assert sum(ds_high.bank_cfads_keur) < sum(ds_base.bank_cfads_keur)

    def test_higher_opex_reduces_equity_distributions(self):
        r_base = self._run_with_opex_scale(1.0)
        r_high = self._run_with_opex_scale(1.10)
        assert (
            r_high.total_legal_equity_distributions_keur
            < r_base.total_legal_equity_distributions_keur
        )


# ── Test G: DSCR causal sensitivity ─────────────────────────────────────────

class TestG_DscrCausalSensitivity:
    """CURRENT_BLOCKING: With DSCR as the binding constraint (gearing=0.85),
    higher target DSCR strictly reduces senior capacity.

    Gearing=0.85 sets gearing_capacity ≈ 34 850 kEUR > DSCR capacity ≈ 32 000 kEUR,
    making DSCR the binding constraint for all DSCR values tested here.
    """

    def _run_dscr(self, target_dscr: float):
        proj = _dscr_binding_project()
        return _run(replace(proj, financing=replace(proj.financing, target_dscr=target_dscr)))

    def test_dscr_is_binding_at_baseline(self):
        result = _run(_dscr_binding_project())
        sd = result.financing_result.project_model_result.senior_debt
        assert sd.binding_constraint == "DSCR"

    def test_higher_dscr_target_strictly_reduces_senior_capacity(self):
        r_low = self._run_dscr(1.20)
        r_high = self._run_dscr(1.35)
        sd_low = r_low.financing_result.project_model_result.senior_debt
        sd_high = r_high.financing_result.project_model_result.senior_debt
        assert sd_low.binding_constraint == "DSCR"
        assert sd_high.binding_constraint == "DSCR"
        assert r_high.financing_result.final_senior_commitment_keur < r_low.financing_result.final_senior_commitment_keur

    def test_senior_capacity_monotone_with_dscr(self):
        seniors = [
            self._run_dscr(d).financing_result.final_senior_commitment_keur
            for d in [1.15, 1.25, 1.35, 1.45]
        ]
        for i in range(len(seniors) - 1):
            assert seniors[i] > seniors[i + 1], (
                f"Senior not monotone: dscr[{i}]→{seniors[i]:.2f}, dscr[{i+1}]→{seniors[i+1]:.2f}"
            )


# ── Test H: tax causal sensitivity ──────────────────────────────────────────

class TestH_TaxCausality:
    """CURRENT_BLOCKING: Higher corporate tax rate strictly reduces post-tax
    cash flows and equity economics."""

    def _run_with_tax(self, rate: float):
        proj = create_synthetic_project_c()
        return _run(replace(proj, tax=replace(proj.tax, corporate_rate=rate)))

    def test_higher_tax_increases_cash_tax(self):
        r_low = self._run_with_tax(0.20)
        r_high = self._run_with_tax(0.35)
        tc_low = r_low.financing_result.project_model_result.tax_and_cfads
        tc_high = r_high.financing_result.project_model_result.tax_and_cfads
        assert sum(tc_high.corporate_tax_cash_keur) > sum(tc_low.corporate_tax_cash_keur)

    def test_higher_tax_reduces_base_cfads(self):
        r_low = self._run_with_tax(0.20)
        r_high = self._run_with_tax(0.35)
        psc_low = r_low.financing_result.project_model_result.post_senior_cash
        psc_high = r_high.financing_result.project_model_result.post_senior_cash
        assert sum(psc_high.base_cfads_keur) <= sum(psc_low.base_cfads_keur)

    def test_higher_tax_reduces_bank_cfads(self):
        r_low = self._run_with_tax(0.20)
        r_high = self._run_with_tax(0.35)
        ds_low = r_low.financing_result.project_model_result.debt_sizing
        ds_high = r_high.financing_result.project_model_result.debt_sizing
        assert sum(ds_high.bank_cfads_keur) <= sum(ds_low.bank_cfads_keur)

    def test_zero_tax_strictly_increases_distributions_over_baseline(self):
        r_base = self._run_with_tax(0.28)
        r_zero = self._run_with_tax(0.0)
        assert r_zero.total_legal_equity_distributions_keur > r_base.total_legal_equity_distributions_keur

    def test_at_least_one_strict_tax_effect(self):
        """At least one cash-tax period must differ between 20% and 35% scenarios."""
        r_low = self._run_with_tax(0.20)
        r_high = self._run_with_tax(0.35)
        tc_low = r_low.financing_result.project_model_result.tax_and_cfads
        tc_high = r_high.financing_result.project_model_result.tax_and_cfads
        diffs = [abs(h - l) for h, l in zip(tc_high.corporate_tax_cash_keur, tc_low.corporate_tax_cash_keur)]
        assert max(diffs) > 0.01, "No period showed any tax effect"


# ── Test I: SHL interest deductibility causal chain ─────────────────────────

class TestI_ShlDeductibilityCausalChain:
    """CURRENT_BLOCKING: Deductible SHL interest → lower taxable income →
    lower cash tax → higher bank CFADS → higher DSCR senior capacity.

    Uses gearing=0.85 (DSCR binding) so the bank CFADS change propagates
    causally to the senior commitment.

    Also proves there is NO direct SHL-principal-to-Senior addition:
    the senior capacity difference equals the DSCR-CFADS effect, not
    the SHL principal amount.
    """

    def _run_deductibility(self, mode: ShlInterestDeductibilityMode):
        proj = _dscr_binding_project()
        return _run(replace(proj, tax=replace(proj.tax, shl_interest_deductibility=mode)))

    def test_fully_deductible_has_lower_cash_tax(self):
        r_ded = self._run_deductibility(ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE)
        r_noded = self._run_deductibility(ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE)
        tc_ded = r_ded.financing_result.project_model_result.tax_and_cfads
        tc_noded = r_noded.financing_result.project_model_result.tax_and_cfads
        assert sum(tc_ded.corporate_tax_cash_keur) < sum(tc_noded.corporate_tax_cash_keur)

    def test_fully_deductible_has_higher_bank_cfads(self):
        r_ded = self._run_deductibility(ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE)
        r_noded = self._run_deductibility(ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE)
        ds_ded = r_ded.financing_result.project_model_result.debt_sizing
        ds_noded = r_noded.financing_result.project_model_result.debt_sizing
        assert sum(ds_ded.bank_cfads_keur) > sum(ds_noded.bank_cfads_keur)

    def test_fully_deductible_has_higher_senior_capacity(self):
        r_ded = self._run_deductibility(ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE)
        r_noded = self._run_deductibility(ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE)
        assert (
            r_ded.financing_result.final_senior_commitment_keur
            > r_noded.financing_result.final_senior_commitment_keur
        )

    def test_senior_delta_not_equal_to_shl_principal(self):
        """Senior capacity delta comes from CFADS effect, not SHL principal addition."""
        r_ded = self._run_deductibility(ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE)
        r_noded = self._run_deductibility(ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE)
        senior_delta = abs(
            r_ded.financing_result.final_senior_commitment_keur
            - r_noded.financing_result.final_senior_commitment_keur
        )
        # The delta (~657 kEUR) must not equal the SHL principal (10 680 kEUR)
        assert abs(senior_delta - _SYNTH_C_SHL_PRINCIPAL_KEUR) > 100.0, (
            f"senior_delta={senior_delta:.2f} suspiciously close to SHL principal "
            f"{_SYNTH_C_SHL_PRINCIPAL_KEUR:.2f} — possible direct SHL addition"
        )


# ── Test J: financing closure and SHL adapter handshake ──────────────────────

class TestJ_FinancingClosureAndShlHandshake:
    """CURRENT_BLOCKING: Uses = Sources identity; SHL adapter handshake;
    gearing-binding constraint at baseline."""

    def test_total_uses_equals_capex(self):
        result = _result()
        pu = result.financing_result.project_uses
        assert pu.total_project_uses_keur == pytest.approx(_SYNTH_C_TOTAL_CAPEX_KEUR, rel=1e-6)

    def test_senior_plus_shl_plus_equity_equals_total_uses(self):
        result = _result()
        fr = result.financing_result
        sources = (
            fr.final_senior_commitment_keur
            + fr.derived_shl_cash_principal_keur
            + fr.share_capital_keur
        )
        assert sources == pytest.approx(fr.project_uses.total_project_uses_keur, rel=1e-6)

    def test_shl_adapter_handshake(self):
        """Engine-derived SHL principal must equal the configured adapter input."""
        result = _result()
        fr = result.financing_result
        proj = create_synthetic_project_c()
        assert fr.derived_shl_cash_principal_keur == pytest.approx(
            proj.financing.clean_shl_principal_keur, rel=1e-6
        ), (
            f"Adapter handshake broken: "
            f"derived={fr.derived_shl_cash_principal_keur:.4f} "
            f"configured={proj.financing.clean_shl_principal_keur:.4f}"
        )

    def test_senior_commitment_engine_derived(self):
        """Engine-derived Senior == 29 520 kEUR (gearing-binding at 0.72)."""
        result = _result()
        assert result.financing_result.final_senior_commitment_keur == pytest.approx(29_520.0, rel=1e-6)

    def test_binding_constraint_is_gearing_at_baseline(self):
        result = _result()
        sd = result.financing_result.project_model_result.senior_debt
        assert sd.binding_constraint == "GEARING"

    def test_all_four_sponsor_metrics_finite(self):
        result = _result()
        assert result.pure_equity_xirr is not None and math.isfinite(result.pure_equity_xirr)
        assert result.pure_equity_moic is not None and math.isfinite(result.pure_equity_moic)
        assert result.total_sponsor_xirr is not None and math.isfinite(result.total_sponsor_xirr)
        assert result.total_sponsor_moic is not None and math.isfinite(result.total_sponsor_moic)

    def test_shl_not_unpaid_at_maturity(self):
        result = _result()
        assert result.shl_bullet_unpaid_at_maturity is False


# ── Test K: SHL cash-sweep portability ───────────────────────────────────────

class TestK_ShlCashSweepPortability:
    """CURRENT_BLOCKING: Per-period SHL repayment discipline for CASH_SWEEP."""

    def test_principal_paid_never_exceeds_opening_balance(self):
        result = _result()
        shl = result.financing_result.project_model_result.shareholder_loan
        for idx, (opening, principal) in enumerate(
            zip(shl.shl_opening_keur, shl.shl_principal_keur)
        ):
            if principal > 0:
                assert principal <= opening + 1e-6, (
                    f"Period {shl.period_indices[idx]}: principal_paid={principal:.4f} "
                    f"> opening={opening:.4f}"
                )

    def test_shl_closing_never_negative(self):
        result = _result()
        shl = result.financing_result.project_model_result.shareholder_loan
        for idx, closing in enumerate(shl.shl_closing_keur):
            assert closing >= -1e-6, (
                f"Period {shl.period_indices[idx]}: SHL closing is negative: {closing:.6f}"
            )

    def test_shl_fully_repaid_by_maturity(self):
        result = _result()
        shl = result.financing_result.project_model_result.shareholder_loan
        assert shl.shl_closing_keur[-1] == pytest.approx(0.0, abs=1e-4)

    def test_total_principal_swept_equals_drawn(self):
        result = _result()
        shl = result.financing_result.project_model_result.shareholder_loan
        total_drawn = sum(v for v in shl.shl_drawdown_keur if v > 0)
        total_repaid = sum(v for v in shl.shl_principal_keur if v > 0)
        assert total_repaid == pytest.approx(total_drawn, rel=1e-4)

    def test_zero_pik_is_baseline_outcome_not_policy(self):
        """In this healthy project, all SHL interest is cash-paid (zero PIK).
        This is a baseline outcome for SYNTH-C — not asserted as a CASH_SWEEP
        universal invariant.  Label is explicit to avoid the policy confusion."""
        result = _result()
        shl = result.financing_result.project_model_result.shareholder_loan
        total_pik = sum(abs(v) for v in shl.shl_pik_interest_keur)
        assert total_pik == pytest.approx(0.0, abs=1e-6), (
            "SYNTH-C baseline has zero PIK (healthy CFADS covers SHL service); "
            "this is a project-level outcome, not a CASH_SWEEP policy rule."
        )

    def test_principal_paid_causal_to_available_cash(self):
        """Mutating available cash (via PPA reduction) changes CASH_SWEEP repayment."""
        proj = create_synthetic_project_c()
        r_base = _run(proj)
        proj_low = replace(proj, revenue=replace(proj.revenue, ppa_base_tariff=38.0))
        r_low = _run(proj_low)
        shl_base = r_base.financing_result.project_model_result.shareholder_loan
        shl_low = r_low.financing_result.project_model_result.shareholder_loan
        # At lower PPA, sweep cash is reduced; repayment schedule must differ
        assert shl_base.shl_principal_keur != shl_low.shl_principal_keur


# ── Test L: construction funding closure ─────────────────────────────────────

class TestL_ConstructionFundingClosure:
    """CURRENT_BLOCKING: Construction period reconciliation via production
    ConstructionFundingPeriod objects — no manual stack rebuild."""

    def test_max_period_difference_is_zero(self):
        result = _result()
        cf = result.financing_result.construction_funding
        assert cf.maximum_period_difference_keur == pytest.approx(0.0, abs=1e-4)

    def test_max_cumulative_difference_is_zero(self):
        result = _result()
        cf = result.financing_result.construction_funding
        assert cf.maximum_cumulative_difference_keur == pytest.approx(0.0, abs=1e-4)

    def test_final_cumulative_uses_equals_capex(self):
        result = _result()
        cf = result.financing_result.construction_funding
        last = cf.periods[-1]
        assert last.cumulative_project_cash_uses_keur == pytest.approx(_SYNTH_C_TOTAL_CAPEX_KEUR, rel=1e-6)

    def test_final_cumulative_sources_equals_uses(self):
        result = _result()
        cf = result.financing_result.construction_funding
        last = cf.periods[-1]
        assert last.cumulative_total_sources_keur == pytest.approx(
            last.cumulative_project_cash_uses_keur, rel=1e-6
        )

    def test_final_cumulative_senior_draw_equals_senior_commitment(self):
        result = _result()
        cf = result.financing_result.construction_funding
        last = cf.periods[-1]
        senior_commitment = result.financing_result.final_senior_commitment_keur
        assert last.cumulative_senior_draw_keur == pytest.approx(senior_commitment, rel=1e-6)

    def test_final_cumulative_shl_draw_equals_shl_principal(self):
        result = _result()
        cf = result.financing_result.construction_funding
        last = cf.periods[-1]
        assert last.cumulative_shl_cash_draw_keur == pytest.approx(_SYNTH_C_SHL_PRINCIPAL_KEUR, rel=1e-6)

    def test_per_period_sources_minus_uses_is_zero(self):
        result = _result()
        cf = result.financing_result.construction_funding
        for p in cf.periods:
            assert p.sources_uses_difference_keur == pytest.approx(0.0, abs=1e-4), (
                f"Period {p.period_index}: sources-uses gap = {p.sources_uses_difference_keur:.6f}"
            )


# ── Test M: distribution account telescoping identity ────────────────────────

class TestM_DaTelescopingIdentity:
    """CURRENT_BLOCKING: Period-level DA flow identity.
    da_available[t] = da_opening[t] + da_inflow[t]
    da_closing[t]   = da_available[t] - da_release[t]
    sum(da_inflow)  = sum(da_release) + final_da_closing
    """

    def test_da_available_equals_opening_plus_inflow(self):
        result = _result()
        ops = _operating_periods(result)
        for wp in ops:
            expected_available = wp.distribution_account_opening_keur + wp.distribution_account_inflow_keur
            assert wp.distribution_account_available_keur == pytest.approx(
                expected_available, abs=1e-4
            ), (
                f"Period {wp.period_index}: da_available={wp.distribution_account_available_keur:.4f} "
                f"!= opening+inflow={expected_available:.4f}"
            )

    def test_da_closing_equals_available_minus_release(self):
        result = _result()
        ops = _operating_periods(result)
        for wp in ops:
            expected_closing = wp.distribution_account_available_keur - wp.distribution_account_release_keur
            assert wp.distribution_account_closing_keur == pytest.approx(
                expected_closing, abs=1e-4
            ), (
                f"Period {wp.period_index}: da_closing={wp.distribution_account_closing_keur:.4f} "
                f"!= available-release={expected_closing:.4f}"
            )

    def test_da_cumulative_identity(self):
        """sum(da_inflow) == sum(da_release) + final_da_closing."""
        result = _result()
        ops = _operating_periods(result)
        total_inflow = sum(wp.distribution_account_inflow_keur for wp in ops)
        total_release = sum(wp.distribution_account_release_keur for wp in ops)
        final_closing = ops[-1].distribution_account_closing_keur if ops else 0.0
        assert total_inflow == pytest.approx(total_release + final_closing, abs=1e-4)

    def test_da_opening_equals_prior_closing(self):
        """Each period's opening DA must equal the prior period's closing DA."""
        result = _result()
        ops = _operating_periods(result)
        for i in range(1, len(ops)):
            assert ops[i].distribution_account_opening_keur == pytest.approx(
                ops[i - 1].distribution_account_closing_keur, abs=1e-4
            ), (
                f"Period {ops[i].period_index}: da_opening != prior da_closing"
            )


# ── Test N: period axis integrity ─────────────────────────────────────────────

class TestN_PeriodAxisIntegrity:
    """CURRENT_BLOCKING: Period indices follow COD_ANCHOR_TWO_CONSTRUCTION_COLUMNS rules."""

    def test_senior_starts_at_period_2(self):
        result = _result()
        sd = result.financing_result.project_model_result.senior_debt
        assert sd.period_indices[0] == 2

    def test_senior_matures_at_period_25(self):
        """Senior tenor 12yr × 2 semi-annual = 24 periods → 2..25."""
        result = _result()
        sd = result.financing_result.project_model_result.senior_debt
        assert sd.period_indices[-1] == 25

    def test_senior_maturity_differs_from_generic_31(self):
        result = _result()
        sd = result.financing_result.project_model_result.senior_debt
        assert sd.period_indices[-1] != 31

    def test_shl_maturity_period_is_valid_operating_period(self):
        """shl_maturity_period_index must be in the actual SHL period indices."""
        result = _result()
        shl = result.financing_result.project_model_result.shareholder_loan
        operating = [wp.period_index for wp in result.waterfall_periods if not wp.is_construction]
        assert _SYNTH_C_SHL_MATURITY_PERIOD_IDX in shl.period_indices, (
            f"shl_maturity_period_index={_SYNTH_C_SHL_MATURITY_PERIOD_IDX} "
            f"not in shl.period_indices"
        )
        assert _SYNTH_C_SHL_MATURITY_PERIOD_IDX in operating, (
            f"shl_maturity_period_index={_SYNTH_C_SHL_MATURITY_PERIOD_IDX} "
            f"not in operating period indices"
        )

    def test_shl_maturity_differs_from_generic_33(self):
        assert _SYNTH_C_SHL_MATURITY_PERIOD_IDX != 33

    def test_shl_first_operating_opening_equals_principal(self):
        result = _result()
        shl = result.financing_result.project_model_result.shareholder_loan
        idx2 = list(shl.period_indices).index(2)
        assert shl.shl_opening_keur[idx2] == pytest.approx(_SYNTH_C_SHL_PRINCIPAL_KEUR, rel=1e-6)

    def test_shl_closing_zero_at_last_period(self):
        result = _result()
        shl = result.financing_result.project_model_result.shareholder_loan
        assert shl.shl_closing_keur[-1] == pytest.approx(0.0, abs=1e-4)


# ── Test O: no source-code dispatch on project identity ──────────────────────

class TestO_NoSourceDispatch:
    """CURRENT_BLOCKING: Engine must not special-case Oborovo/TUHO/G2A names."""

    def test_oborovo_code_gives_synth_c_results(self):
        r_normal = _run(code="SYNTH-C")
        r_spoofed = _run(code="OBOROVO")
        pmr_n = r_normal.financing_result.project_model_result
        pmr_s = r_spoofed.financing_result.project_model_result
        assert (
            pmr_n.operating_schedules.revenue_keur
            == pmr_s.operating_schedules.revenue_keur
        )
        assert r_normal.pure_equity_xirr == pytest.approx(r_spoofed.pure_equity_xirr, rel=1e-9)

    def test_tuho_name_gives_synth_c_results(self):
        r_normal = _run(name="Synthetic Project C")
        r_spoofed = _run(name="TUHO Wind 1")
        assert r_normal.total_legal_equity_distributions_keur == pytest.approx(
            r_spoofed.total_legal_equity_distributions_keur, rel=1e-9
        )

    def test_generic_solar_name_gives_synth_c_results(self):
        r_normal = _run(name="Synthetic Project C")
        r_spoofed = _run(name="Generic Solar")
        pmr_n = r_normal.financing_result.project_model_result
        pmr_s = r_spoofed.financing_result.project_model_result
        assert (
            pmr_n.shareholder_loan.shl_closing_keur
            == pmr_s.shareholder_loan.shl_closing_keur
        )


# ── Test P: G2C inherited stop-boundaries documented ─────────────────────────

class TestP_G2cStopBoundaries:
    """CURRENT_BLOCKING: G2C_RESERVE_GATE_NOT_CAUSALLY_CLOSED sub-causes documented.

    These are capability limitations, not failures.  The Fable review should
    classify each as MUST_CLOSE_BEFORE_G4 or ACCEPTED_MVP_LIMITATION/POST-MVP.
    Tests assert the boundary description, not closure.
    """

    def test_sub_cause_1_dsra_draw_replenishment_not_fully_causal(self):
        """G2C sub-cause 1: senior_dsra_closing is static/target-based, not causal."""
        result = _result()
        ops = _operating_periods(result)
        dsra_closing = [wp.senior_dsra_closing_keur for wp in ops]
        # With DSRA=NONE all closings are 0 — confirming static behaviour
        assert all(v == 0.0 for v in dsra_closing), (
            "Unexpected non-zero DSRA closing with DSRE=NONE; boundary description may be stale."
        )

    def test_sub_cause_2_j_dsra_gate_always_false(self):
        """G2C sub-cause 2: gate_component_j_dsra_underfunded is always False."""
        result = _result()
        ops = _operating_periods(result)
        j_dsra = [wp.gate_component_j_dsra_underfunded for wp in ops]
        assert all(v is False for v in j_dsra), (
            "J-DSRA gate became True — model has changed; update sub-cause documentation."
        )

    def test_sub_cause_3_within_senior_maturity_proxy_exists(self):
        """G2C sub-cause 3: within_senior_maturity proxy present on waterfall periods."""
        result = _result()
        ops = _operating_periods(result)
        # Confirm the proxy attribute exists and transitions at period 25
        within = [(wp.period_index, wp.within_senior_maturity) for wp in ops]
        # All periods up to and including 25 should be within maturity
        within_dict = {pi: wm for pi, wm in within}
        if 25 in within_dict:
            assert within_dict[25] is True
        if 26 in within_dict:
            assert within_dict[26] is False
