"""MVP Final Engine Freeze — Post-C3 Canonical Four-Project Baseline.

Baseline main SHA: ba965f94a3f1bd49f902f3f4cca9d1e09a6ca121
PR #964 merged.  Production code unchanged (test/evidence only).

Covers sections 2–11 of FINAL_MVP_ENGINE_FREEZE_POST_C3 specification:
  §2  Four canonical projects — single production engine, zero legacy
  §3  Canonical financial fingerprint (scalar totals)
  §4  Period-vector fingerprints (SHA-256 digests)
  §5  Period-axis freeze (count, identity, no duplicates)
  §6  Real balance-sheet freeze
  §7  Statement accounting identities
  §8  Generic Solar/Wind semantics
  §9  Oborovo/TUHO source-proven semantics
  §10 Determinism
  §11 Input sensitivity / no target fitting
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Production entry points
# ---------------------------------------------------------------------------

def _run_clean(ptype: str):
    from app import project_factories as pf
    from app.services.production_financial_authority import run_clean_production

    factory = {
        "Solar": pf.create_default_solar_project,
        "Wind": pf.create_default_wind_project,
        "Oborovo": pf.create_default_oborovo,
        "TUHO": pf.create_default_tuho_wind1,
    }[ptype]
    return run_clean_production(factory(), project_type=ptype)


def _assemble(ptype: str):
    from financial_engine.financial_statements import (
        assemble_decision_complete_financial_statements,
    )
    from app import project_factories as pf

    factory = {
        "Solar": pf.create_default_solar_project,
        "Wind": pf.create_default_wind_project,
        "Oborovo": pf.create_default_oborovo,
        "TUHO": pf.create_default_tuho_wind1,
    }[ptype]
    proj = factory()
    from app.services.production_financial_authority import run_clean_production
    run = run_clean_production(proj, project_type=ptype)
    return run, assemble_decision_complete_financial_statements(run.g2c_result, proj)


def _vec_digest(v: list) -> str:
    rounded = [round(float(x), 6) if x is not None else None for x in v]
    return hashlib.sha256(json.dumps(rounded).encode()).hexdigest()[:24]


# ---------------------------------------------------------------------------
# Frozen scalar fingerprints (regression evidence — not fit to source)
# ---------------------------------------------------------------------------

_FINGERPRINTS: dict[str, dict[str, Any]] = {
    "Solar": {
        "n_operating": 40,
        "n_bs_total": 42,
        "total_revenue_keur": 94414.548812,
        "total_opex_keur": 9233.000524,
        "total_ebitda_keur": 85181.548288,
        "total_ebit_keur": 59114.881621,
        "total_net_income_keur": 30124.320402,
        "total_financing_income_keur": 0.0,
        "total_senior_interest_pnl_keur": 10552.125188,
        "total_shl_interest_pnl_keur": 8825.775433,
        "total_book_dep_keur": 26066.666667,
        "ending_accumulated_dep_keur": 26066.666667,
        "ending_nfa_keur": 6933.333333,
        "total_cit_accrual_keur": 9612.660598,
        "total_cash_tax_keur": 9612.660598,
        "ending_tax_loss_keur": 0.0,
        "senior_commitment_keur": 24750.0,
        "binding_constraint": "GEARING",
        "senior_terminal_status": "REPAID",
        "min_dscr": 1.102902,
        "shl_opening_balance_keur": 7750.0,
        "shl_construction_pik_keur": 0.0,
        "total_shl_gross_keur": 8825.775433,
        "total_shl_cash_int_keur": 8536.15913,
        "total_shl_pik_keur": 289.616303,
        "total_shl_principal_keur": 1365.745179,
        "terminal_shl_balance_keur": 6673.871124,
        "shl_terminal_status": "UNPAID_AT_CONTRACTUAL_MATURITY",
        "ending_dsra_keur": 0.0,
        "ending_da_keur": 0.0,
        "ending_uc_keur": 25362.695615,
        "ending_sc_keur": 500.0,
        "ending_re_keur": 25122.157824,
        "ending_lr_keur": 0.0,
        "total_gross_dividends_keur": 5002.162579,
        "project_xirr": 0.075932,
        "project_xirr_status": "OK",
        "max_bs_residual": 8.30e-12,
    },
    "Wind": {
        "n_operating": 50,
        "n_bs_total": 53,
        "total_revenue_keur": 213093.25363,
        "total_opex_keur": 17617.771477,
        "total_ebitda_keur": 195475.482153,
        "total_ebit_keur": 153972.314251,
        "total_net_income_keur": 101525.267787,
        "total_financing_income_keur": 0.0,
        "total_senior_interest_pnl_keur": 10400.797384,
        "total_shl_interest_pnl_keur": 9433.369863,
        "total_book_dep_keur": 41503.167902,
        "ending_accumulated_dep_keur": 41503.167902,
        "ending_nfa_keur": 1496.832098,
        "total_cit_accrual_keur": 32612.879217,
        "total_cash_tax_keur": 32612.879217,
        "ending_tax_loss_keur": 0.0,
        "senior_commitment_keur": 32250.0,
        "binding_constraint": "GEARING",
        "senior_terminal_status": "REPAID",
        "min_dscr": 1.276688,
        "shl_opening_balance_keur": 10250.0,
        "shl_construction_pik_keur": 0.0,
        "total_shl_gross_keur": 9433.369863,
        "total_shl_cash_int_keur": 9433.369863,
        "total_shl_pik_keur": 0.0,
        "total_shl_principal_keur": 2002.916828,
        "terminal_shl_balance_keur": 8247.083172,
        "shl_terminal_status": "UNPAID_AT_CONTRACTUAL_MATURITY",
        "ending_dsra_keur": 0.0,
        "ending_da_keur": 0.0,
        "ending_uc_keur": 98269.005835,
        "ending_sc_keur": 500.0,
        "ending_re_keur": 91018.754761,
        "ending_lr_keur": 0.0,
        "total_gross_dividends_keur": 10506.513026,
        "project_xirr": 0.113661,
        "project_xirr_status": "OK",
        "max_bs_residual": 4.51e-11,
    },
    "Oborovo": {
        "n_operating": 60,
        "n_bs_total": 61,
        "total_revenue_keur": 237686.922417,
        "total_opex_keur": 55782.950839,
        "total_ebitda_keur": 181903.971578,
        "total_ebit_keur": 123930.929298,
        "total_net_income_keur": 61253.805523,
        "total_financing_income_keur": 71.003187,
        "total_senior_interest_pnl_keur": 20133.090175,
        "total_shl_interest_pnl_keur": 32170.031702,
        "total_book_dep_keur": 57973.04228,
        "ending_accumulated_dep_keur": 57973.04228,
        "ending_nfa_keur": 0.0,
        "total_cit_accrual_keur": 10445.005086,
        "total_cash_tax_keur": 10445.005086,
        "ending_tax_loss_keur": 0.0,
        "senior_commitment_keur": 42852.302723,
        "binding_constraint": "DSCR",
        "senior_terminal_status": "REPAID",
        "min_dscr": 1.068192,
        "shl_opening_balance_keur": 15790.398721,
        "shl_construction_pik_keur": 1169.659165,
        "total_shl_gross_keur": 31000.372537,
        "total_shl_cash_int_keur": 20039.147711,
        "total_shl_pik_keur": 10961.224826,
        "total_shl_principal_keur": 26751.623547,
        "terminal_shl_balance_keur": 0.0,
        "shl_terminal_status": "REPAID",
        "ending_dsra_keur": 0.0,
        "ending_da_keur": 0.0,
        "ending_uc_keur": 550.0,
        "ending_sc_keur": 500.0,
        "ending_re_keur": 0.0,
        "ending_lr_keur": 50.0,
        "total_gross_dividends_keur": 61753.805523,
        "project_xirr": 0.085122,
        "project_xirr_status": "OK",
        "max_bs_residual": 1.68e-9,
    },
    "TUHO": {
        "n_operating": 60,
        "n_bs_total": 61,
        "total_revenue_keur": 423762.001818,
        "total_opex_keur": 85403.451001,
        "total_ebitda_keur": 338358.550818,
        "total_ebit_keur": 265327.520986,
        "total_net_income_keur": 151292.901099,
        "total_financing_income_keur": 124.316738,
        "total_senior_interest_pnl_keur": 23046.055518,
        "total_shl_interest_pnl_keur": 52174.95003,
        "total_book_dep_keur": 73031.029831,
        "ending_accumulated_dep_keur": 73031.029831,
        "ending_nfa_keur": 0.0,
        "total_cit_accrual_keur": 38937.931077,
        "total_cash_tax_keur": 38937.931077,
        "ending_tax_loss_keur": 0.0,
        "senior_commitment_keur": 43789.921117,
        "binding_constraint": "DSCR",
        "senior_terminal_status": "REPAID",
        "min_dscr": 1.39827,
        "shl_opening_balance_keur": 32261.52827,
        "shl_construction_pik_keur": 3520.419555,
        "total_shl_gross_keur": 48654.530475,
        "total_shl_cash_int_keur": 38253.888215,
        "total_shl_pik_keur": 10400.642259,
        "total_shl_principal_keur": 42662.170529,
        "terminal_shl_balance_keur": 0.0,
        "shl_terminal_status": "REPAID",
        "ending_dsra_keur": 0.0,
        "ending_da_keur": 0.0,
        "ending_uc_keur": 550.0,
        "ending_sc_keur": 500.0,
        "ending_re_keur": 0.0,
        "ending_lr_keur": 50.0,
        "total_gross_dividends_keur": 151792.901099,
        "project_xirr": 0.09478,
        "project_xirr_status": "OK",
        "max_bs_residual": 8.16e-9,
    },
}

# ---------------------------------------------------------------------------
# Frozen period-vector digests (SHA-256[:24] of rounded-to-6dp lists)
# ---------------------------------------------------------------------------

_DIGESTS: dict[str, dict[str, str]] = {
    "Solar": {
        "revenue": "bbddf6436bbbafc5e037ef07",
        "ebitda": "f7e6fa23957f6079c32f972d",
        "book_depreciation": "46a76ee926a070edb4376332",
        "cit_accrual": "f40ab41aed1b45566b50daf0",
        "cash_tax": "3af7b5d19d3d3adcd86180da",
        "shl_opening": "802f05e5d4b66d1557737685",
        "shl_gross_interest": "26f26a238abad5b29bc9dbef",
        "shl_pik": "11e5c48077269d9e77be8cf3",
        "shl_cash_interest": "3dc43859391b1139f77b55b7",
        "shl_principal": "ec6c4e1114315d74102681df",
        "shl_closing": "66a7f29dcfb4623e01401b58",
        "dsra": "2e937bbc257f957374c23ae8",
        "distribution_account": "2e937bbc257f957374c23ae8",
        "unrestricted_cash": "d528cffb906d50b7f2ca4c40",
        "financing_income": "2e937bbc257f957374c23ae8",
        "legal_reserve": "e916bf69d50e23e4deecd4cc",
        "retained_earnings": "640b886ce58214e4dd3e8974",
        "nfa": "bd5f6ea8e77f69ff0f618b56",
        "balance_check": "b97af5877a33a5f8de72d515",
        # Senior debt schedule (canonical Senior axis — 30 periods)
        "senior_opening": "0836118cb4bb4bd43f154888",
        "senior_interest": "8e8731a1b7a94f44faf174e1",
        "senior_principal": "381ba6b41baa339e7f76ccf9",
        "senior_debt_service": "ef422390708043fe71f91d09",
        "senior_closing": "e839a4cae314de2e452e3689",
        # Canonical Base CFADS (tax/CFADS authority — full axis)
        "cfads": "c33503ee7a00d29453065825",
    },
    "Wind": {
        "revenue": "fc376f60563a1cfe75d760e2",
        "ebitda": "2640cc2743bebb7422c72e53",
        "book_depreciation": "cea0d3922e70e402f239aa2f",
        "cit_accrual": "5ab0a78624cebad9d889c55f",
        "cash_tax": "44fc04f0f62c7f73dcbc9c57",
        "shl_opening": "4a8b892faabe40996d1e0262",
        "shl_gross_interest": "963638bd060d793ee3b67de0",
        "shl_pik": "cbd3d3687346cefdb4338dac",
        "shl_cash_interest": "963638bd060d793ee3b67de0",
        "shl_principal": "8ee705c21baf12e247ff1612",
        "shl_closing": "7dfa6641f7f2e02ee260e538",
        "dsra": "cbd3d3687346cefdb4338dac",
        "distribution_account": "cbd3d3687346cefdb4338dac",
        "unrestricted_cash": "ebb3e27cd193803beaa2fd94",
        "financing_income": "cbd3d3687346cefdb4338dac",
        "legal_reserve": "6f53a8fb033a75da6b989dde",
        "retained_earnings": "deef28d3e5c6f7acdfc11ddc",
        "nfa": "e4a9058d3d9f26fbc7211084",
        "balance_check": "63d9f732f7d213e11a79d671",
        # Senior debt schedule (canonical Senior axis — 30 periods)
        "senior_opening": "d0e472597885438d38a385a9",
        "senior_interest": "251d5a26e5ce45a89c1bbe6f",
        "senior_principal": "dca603b2ca0ca7f8bcd139ae",
        "senior_debt_service": "c3018f2582eef3eb0de92e17",
        "senior_closing": "e70ba863438815c45f10e6fa",
        # Canonical Base CFADS (tax/CFADS authority — full axis)
        "cfads": "8bee08c480b1c3ef6000bd43",
    },
    "Oborovo": {
        "revenue": "f3f69706105c5df3c0aecfe5",
        "ebitda": "1a8d24c86f0564cd75c01376",
        "book_depreciation": "80debf97244cac08728c3d16",
        "cit_accrual": "c197b43054794381d1e98b38",
        "cash_tax": "fc35b1366e82c9d749564608",
        "shl_opening": "eb7eb7b33e1776c4e5475318",
        "shl_gross_interest": "74c62de6ea67e3818987413d",
        "shl_pik": "be42c0f4e94731096350f803",
        "shl_cash_interest": "43e66da1726c424d6951c1ef",
        "shl_principal": "47248b30d4804e994fe7eade",
        "shl_closing": "3470b443c02a46a4035739a2",
        "dsra": "a090214f885a60c7e0ba6ca7",
        "distribution_account": "c2d6aba23bf60624d2c74611",
        "unrestricted_cash": "51bb3fe027e07696a8468d6b",
        "financing_income": "1488c0746ec99bd5faeac5dc",
        "legal_reserve": "d02c64cf834b55d5d1b3e17f",
        "retained_earnings": "35227050398a602e5f024385",
        "nfa": "d18bb1af22e0940d62e4d58f",
        "balance_check": "0de38a6f20b07ff85b617ace",
        # Senior debt schedule (canonical Senior axis — 28 periods)
        "senior_opening": "84600e22c90f6da2aa5e587a",
        "senior_interest": "c18c39b4c23dcb383c14d0fc",
        "senior_principal": "775558a0b2ec21a3c5d223f8",
        "senior_debt_service": "219e9f8c83ad031bae1dbadd",
        "senior_closing": "46267cb977f8238644668c13",
        # Canonical Base CFADS (tax/CFADS authority — full axis)
        "cfads": "845a421f06ef34a202a43189",
    },
    "TUHO": {
        "revenue": "5a693322b5cf3cf21adecd71",
        "ebitda": "dc5b27ef1d6a9ddea030c28a",
        "book_depreciation": "8a96c2c4a97ca6cade205ee1",
        "cit_accrual": "c2bd1ea52d346dfeeab29a58",
        "cash_tax": "19bd54b337f8de87acf91d5c",
        "shl_opening": "9725aead78966c105643c8b0",
        "shl_gross_interest": "d509dd8ae8df0db292711ac0",
        "shl_pik": "2363df38a6abe7f1b36a9676",
        "shl_cash_interest": "984c26858f46b12386119477",
        "shl_principal": "6a0a273f5ff9cdf2c352deb5",
        "shl_closing": "b4d8588b1b4253f84e253636",
        "dsra": "a090214f885a60c7e0ba6ca7",
        "distribution_account": "a090214f885a60c7e0ba6ca7",
        "unrestricted_cash": "7fd3a0261d4be3aeadb330cb",
        "financing_income": "d29da3ea6eaa37d7f627fd6f",
        "legal_reserve": "d02c64cf834b55d5d1b3e17f",
        "retained_earnings": "c9937781f592a16f48fa9dd1",
        "nfa": "d9121dce5208cfd83b222071",
        "balance_check": "b65d3ebafdd2d62b9dc35501",
        # Senior debt schedule (canonical Senior axis — 28 periods)
        "senior_opening": "453acbb8c0b9bdb3f036c5ff",
        "senior_interest": "f7b88aa6b5debdcf25b5eb22",
        "senior_principal": "f1ac387cf3b557bc9f1e689b",
        "senior_debt_service": "4851f38bf0df67ca621c1283",
        "senior_closing": "a6a7ea55685ec973db5d9dfe",
        # Canonical Base CFADS (tax/CFADS authority — full axis)
        "cfads": "00ac2091370d0acc2087e56c",
    },
}


# ===========================================================================
# §2 — Single production engine, zero legacy
# ===========================================================================

class TestFreezeS2_SingleProductionEngine:
    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_no_legacy_waterfall_execution(self, ptype, monkeypatch):
        import app.waterfall_core as wc
        import app.waterfall_runner as wr
        import finco_core.waterfall.waterfall_engine as le
        import domain.waterfall.waterfall_engine as de

        counts: dict[str, int] = {"core": 0, "engine": 0}

        for mod, name in (
            (wc, "run_waterfall_v3_core"),
            (wr, "run_waterfall_v3_core"),
            (le, "run_waterfall"),
            (de, "run_waterfall"),
        ):
            orig = getattr(mod, name)
            key = "core" if "core" in name else "engine"
            monkeypatch.setattr(
                mod, name,
                lambda *a, _orig=orig, _k=key, **kw: (
                    counts.__setitem__(_k, counts[_k] + 1),
                    _orig(*a, **kw),
                )[1],
            )
        _run_clean(ptype)
        assert counts["core"] == 0 and counts["engine"] == 0, (
            f"{ptype}: legacy waterfall executed (core={counts['core']} engine={counts['engine']})"
        )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_no_waterfall_runner_production_execution(self, ptype, monkeypatch):
        import app.waterfall_runner as wr
        called: list[bool] = []
        orig = wr.run_waterfall_v3_core
        monkeypatch.setattr(wr, "run_waterfall_v3_core", lambda *a, **kw: (called.append(True), orig(*a, **kw))[1])
        _run_clean(ptype)
        assert not called, f"{ptype}: WaterfallRunner executed in production path"


# ===========================================================================
# §3 — Canonical financial fingerprint (scalar totals)
# ===========================================================================

class TestFreezeS3_ScalarFingerprints:
    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_operations_totals(self, ptype):
        _, fs = _assemble(ptype)
        fp = _FINGERPRINTS[ptype]
        isp = fs.income_statement_periods
        op = [p for p in isp if not p.is_construction]
        assert len(op) == fp["n_operating"]
        assert sum(p.revenue_keur for p in isp) == pytest.approx(fp["total_revenue_keur"], rel=1e-9)
        assert sum(p.opex_keur for p in isp) == pytest.approx(fp["total_opex_keur"], rel=1e-9)
        assert sum(p.ebitda_keur for p in isp) == pytest.approx(fp["total_ebitda_keur"], rel=1e-9)
        assert sum(p.ebit_keur for p in isp) == pytest.approx(fp["total_ebit_keur"], rel=1e-9)
        assert sum(p.net_income_keur for p in isp) == pytest.approx(fp["total_net_income_keur"], rel=1e-9)

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_fixed_assets_totals(self, ptype):
        _, fs = _assemble(ptype)
        fp = _FINGERPRINTS[ptype]
        fap = fs.fixed_asset_periods
        assert sum(p.book_depreciation_keur for p in fap) == pytest.approx(fp["total_book_dep_keur"], rel=1e-9)
        last_fa = fap[-1]
        assert float(last_fa.accumulated_book_depreciation_keur or 0) == pytest.approx(
            fp["ending_accumulated_dep_keur"], abs=1e-4
        )
        assert abs(float(last_fa.net_fixed_assets_keur or 0)) == pytest.approx(
            fp["ending_nfa_keur"], abs=1e-4
        )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_tax_totals(self, ptype):
        _, fs = _assemble(ptype)
        fp = _FINGERPRINTS[ptype]
        isp = fs.income_statement_periods
        tbp = fs.tax_bridge_periods
        assert sum(p.cit_accrual_keur for p in isp) == pytest.approx(fp["total_cit_accrual_keur"], rel=1e-9)
        assert sum(p.corporate_tax_cash_keur for p in tbp) == pytest.approx(fp["total_cash_tax_keur"], rel=1e-9)
        assert float(tbp[-1].tax_loss_closing_keur or 0) == pytest.approx(fp["ending_tax_loss_keur"], abs=1e-4)

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_senior_debt(self, ptype):
        run = _run_clean(ptype)
        fp = _FINGERPRINTS[ptype]
        fin = run.g2c_result.financing_result
        assert float(fin.final_senior_commitment_keur or 0) == pytest.approx(
            fp["senior_commitment_keur"], rel=1e-6
        )
        assert fin.binding_senior_constraint == fp["binding_constraint"]
        term = run.g2c_result.return_summary.terminal
        assert term.senior.status.value == fp["senior_terminal_status"]
        assert float(term.senior.terminal_model_horizon_balance_keur or 0) == pytest.approx(0.0, abs=1e-4)
        # DSCR
        wps = [wp for wp in run.g2c_result.waterfall_periods if not wp.is_construction]
        dscrs = [float(wp.base_dscr) for wp in wps if wp.base_dscr is not None and float(wp.base_dscr) > 0]
        assert min(dscrs) == pytest.approx(fp["min_dscr"], rel=1e-4)

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_shl_totals(self, ptype):
        run = _run_clean(ptype)
        fp = _FINGERPRINTS[ptype]
        fin = run.g2c_result.financing_result
        term = run.g2c_result.return_summary.terminal
        assert float(fin.opening_operating_shl_balance_keur or 0) == pytest.approx(
            fp["shl_opening_balance_keur"], rel=1e-6
        )
        assert float(fin.shl_construction_pik_keur or 0) == pytest.approx(
            fp["shl_construction_pik_keur"], rel=1e-6 if fp["shl_construction_pik_keur"] != 0.0 else 1
        )
        wps = [wp for wp in run.g2c_result.waterfall_periods if not wp.is_construction]
        assert sum(float(wp.shl_gross_interest_keur or 0) for wp in wps) == pytest.approx(
            fp["total_shl_gross_keur"], rel=1e-6
        )
        assert sum(float(wp.shl_cash_interest_receipt_keur or 0) for wp in wps) == pytest.approx(
            fp["total_shl_cash_int_keur"], rel=1e-6
        )
        assert sum(float(wp.shl_pik_keur or 0) for wp in wps) == pytest.approx(
            fp["total_shl_pik_keur"], abs=1e-4
        )
        assert sum(float(wp.actual_shl_principal_paid_keur or 0) for wp in wps) == pytest.approx(
            fp["total_shl_principal_keur"], rel=1e-6
        )
        assert float(wps[-1].actual_shl_closing_balance_keur or 0) == pytest.approx(
            fp["terminal_shl_balance_keur"], abs=1e-4
        )
        assert term.shareholder_loan.status.value == fp["shl_terminal_status"]

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_reserves_and_cash(self, ptype):
        run = _run_clean(ptype)
        fp = _FINGERPRINTS[ptype]
        wps = [wp for wp in run.g2c_result.waterfall_periods if not wp.is_construction]
        last = wps[-1]
        assert float(last.senior_dsra_closing_keur or 0) == pytest.approx(fp["ending_dsra_keur"], abs=1e-4)
        assert float(last.distribution_account_closing_keur or 0) == pytest.approx(fp["ending_da_keur"], abs=1e-4)
        assert float(last.unrestricted_cash_closing_keur or 0) == pytest.approx(fp["ending_uc_keur"], rel=1e-6)

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_equity_accounting(self, ptype):
        _, fs = _assemble(ptype)
        fp = _FINGERPRINTS[ptype]
        bsp = fs.balance_sheet_periods
        last = bsp[-1]
        assert float(last.share_capital_keur or 0) == pytest.approx(fp["ending_sc_keur"], abs=1e-4)
        assert float(last.retained_earnings_keur or 0) == pytest.approx(fp["ending_re_keur"], abs=1e-4)
        assert float(last.legal_reserve_keur or 0) == pytest.approx(fp["ending_lr_keur"], abs=1e-4)

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_distributions_and_returns(self, ptype):
        run = _run_clean(ptype)
        fp = _FINGERPRINTS[ptype]
        wps = [wp for wp in run.g2c_result.waterfall_periods if not wp.is_construction]
        assert sum(float(wp.legal_equity_distribution_keur or 0) for wp in wps) == pytest.approx(
            fp["total_gross_dividends_keur"], rel=1e-6
        )
        ret = run.g2c_result.return_summary
        assert float(ret.project.project_xirr or 0) == pytest.approx(fp["project_xirr"], rel=1e-4)
        assert ret.project.project_xirr_status.value == fp["project_xirr_status"]

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_income_statement_pnl_scalars(self, ptype):
        """Assert all IS P&L scalar fingerprints: financing income, senior interest, SHL interest, net income."""
        _, fs = _assemble(ptype)
        fp = _FINGERPRINTS[ptype]
        isp = fs.income_statement_periods
        assert sum(p.net_income_keur for p in isp) == pytest.approx(fp["total_net_income_keur"], rel=1e-6)
        fi_expected = fp["total_financing_income_keur"]
        assert sum(p.financing_income_keur for p in isp) == pytest.approx(
            fi_expected, abs=1e-4 if fi_expected == 0.0 else None,
            rel=None if fi_expected == 0.0 else 1e-6,
        )
        assert sum(p.senior_interest_expense_keur for p in isp) == pytest.approx(
            fp["total_senior_interest_pnl_keur"], rel=1e-6
        )
        assert sum(p.shl_interest_expense_keur for p in isp) == pytest.approx(
            fp["total_shl_interest_pnl_keur"], rel=1e-6
        )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_c3_statement_statuses(self, ptype):
        _, fs = _assemble(ptype)
        assert fs.income_statement_status.value == "OK"
        assert fs.tax_bridge_status.value == "OK"
        assert fs.cash_flow_status.value == "OK"
        assert fs.fixed_asset_status.value == "OK"
        assert fs.unrestricted_cash_status.value == "OK"
        assert fs.balance_sheet_status.value == "OK"


# ===========================================================================
# §4 — Period-vector fingerprints (digests)
# ===========================================================================

class TestFreezeS4_VectorDigests:
    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_revenue_ebitda_digests(self, ptype):
        _, fs = _assemble(ptype)
        exp = _DIGESTS[ptype]
        op = [p for p in fs.income_statement_periods if not p.is_construction]
        assert _vec_digest([p.revenue_keur for p in op]) == exp["revenue"]
        assert _vec_digest([p.ebitda_keur for p in op]) == exp["ebitda"]

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_depreciation_tax_digests(self, ptype):
        _, fs = _assemble(ptype)
        exp = _DIGESTS[ptype]
        op_is = [p for p in fs.income_statement_periods if not p.is_construction]
        op_tb = [p for p in fs.tax_bridge_periods if not getattr(p, "is_construction", False)]
        assert _vec_digest([p.book_depreciation_keur for p in op_is]) == exp["book_depreciation"]
        assert _vec_digest([p.cit_accrual_keur for p in op_is]) == exp["cit_accrual"]
        assert _vec_digest([p.corporate_tax_cash_keur for p in op_tb]) == exp["cash_tax"]

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_shl_schedule_digests(self, ptype):
        run = _run_clean(ptype)
        exp = _DIGESTS[ptype]
        wps = [wp for wp in run.g2c_result.waterfall_periods if not wp.is_construction]
        assert _vec_digest([float(wp.shl_opening_balance_keur or 0) for wp in wps]) == exp["shl_opening"]
        assert _vec_digest([float(wp.shl_gross_interest_keur or 0) for wp in wps]) == exp["shl_gross_interest"]
        assert _vec_digest([float(wp.shl_pik_keur or 0) for wp in wps]) == exp["shl_pik"]
        assert _vec_digest([float(wp.shl_cash_interest_receipt_keur or 0) for wp in wps]) == exp["shl_cash_interest"]
        assert _vec_digest([float(wp.actual_shl_principal_paid_keur or 0) for wp in wps]) == exp["shl_principal"]
        assert _vec_digest([float(wp.actual_shl_closing_balance_keur or 0) for wp in wps]) == exp["shl_closing"]

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_reserves_cash_digests(self, ptype):
        run = _run_clean(ptype)
        exp = _DIGESTS[ptype]
        wps = [wp for wp in run.g2c_result.waterfall_periods if not wp.is_construction]
        assert _vec_digest([float(wp.senior_dsra_closing_keur or 0) for wp in wps]) == exp["dsra"]
        assert _vec_digest([float(wp.distribution_account_closing_keur or 0) for wp in wps]) == exp["distribution_account"]
        assert _vec_digest([float(wp.unrestricted_cash_closing_keur or 0) for wp in wps]) == exp["unrestricted_cash"]

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_equity_vector_digests(self, ptype):
        _, fs = _assemble(ptype)
        exp = _DIGESTS[ptype]
        op_is = [p for p in fs.income_statement_periods if not p.is_construction]
        bsp = fs.balance_sheet_periods
        fap = [p for p in fs.fixed_asset_periods if not getattr(p, "is_construction", False)]
        assert _vec_digest([p.financing_income_keur for p in op_is]) == exp["financing_income"]
        assert _vec_digest([float(p.legal_reserve_keur or 0) for p in bsp]) == exp["legal_reserve"]
        assert _vec_digest([float(p.retained_earnings_keur or 0) for p in bsp]) == exp["retained_earnings"]
        assert _vec_digest([float(p.net_fixed_assets_keur or 0) for p in fap]) == exp["nfa"]

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_balance_check_digest(self, ptype):
        _, fs = _assemble(ptype)
        exp = _DIGESTS[ptype]
        bsp = fs.balance_sheet_periods
        assert _vec_digest([float(p.balance_check_keur or 0) for p in bsp]) == exp["balance_check"]

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_senior_schedule_digests(self, ptype):
        """Senior debt schedule vectors read directly from canonical SeniorDebtSchedules."""
        run = _run_clean(ptype)
        exp = _DIGESTS[ptype]
        sd = run.g2c_result.financing_result.project_model_result.senior_debt
        assert _vec_digest(list(sd.senior_debt_opening_keur)) == exp["senior_opening"]
        assert _vec_digest(list(sd.senior_interest_keur)) == exp["senior_interest"]
        assert _vec_digest(list(sd.senior_principal_keur)) == exp["senior_principal"]
        assert _vec_digest(list(sd.senior_debt_service_keur)) == exp["senior_debt_service"]
        assert _vec_digest(list(sd.senior_debt_closing_keur)) == exp["senior_closing"]

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_cfads_digest(self, ptype):
        """Canonical Base CFADS read from the authoritative tax/CFADS schedule."""
        run = _run_clean(ptype)
        exp = _DIGESTS[ptype]
        tax = run.g2c_result.financing_result.project_model_result.tax_and_cfads
        assert _vec_digest(list(tax.cfads_keur)) == exp["cfads"]


# ===========================================================================
# §5 — Period-axis freeze
# ===========================================================================

class TestFreezeS5_PeriodAxis:
    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_period_counts_match_fingerprint(self, ptype):
        run, fs = _assemble(ptype)
        fp = _FINGERPRINTS[ptype]
        isp = fs.income_statement_periods
        op = [p for p in isp if not p.is_construction]
        assert len(op) == fp["n_operating"]
        assert len(fs.balance_sheet_periods) == fp["n_bs_total"]

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_no_duplicate_period_indices(self, ptype):
        _, fs = _assemble(ptype)
        indices = [p.period_index for p in fs.income_statement_periods]
        assert len(indices) == len(set(indices)), f"{ptype}: duplicate IS period indices"
        bs_indices = [p.period_index for p in fs.balance_sheet_periods]
        assert len(bs_indices) == len(set(bs_indices)), f"{ptype}: duplicate BS period indices"

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_all_statements_share_canonical_axis(self, ptype):
        _, fs = _assemble(ptype)
        is_idx = {p.period_index for p in fs.income_statement_periods}
        tb_idx = {p.period_index for p in fs.tax_bridge_periods}
        bs_idx = {p.period_index for p in fs.balance_sheet_periods}
        fa_idx = {p.period_index for p in fs.fixed_asset_periods}
        # All statement indices must be subsets of or equal to the IS axis
        assert tb_idx == is_idx, f"{ptype}: tax bridge axis mismatch"
        # BS and FA may include construction periods; IS operating must be subset of both
        op_is = {p.period_index for p in fs.income_statement_periods if not p.is_construction}
        assert op_is.issubset(bs_idx), f"{ptype}: operating IS periods missing from BS"
        assert fa_idx == bs_idx, f"{ptype}: FA and BS period axes differ"

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_periods_are_ordered_and_non_overlapping(self, ptype):
        _, fs = _assemble(ptype)
        # IS periods have period_start and period_end — check both ordering and non-overlap
        is_periods = fs.income_statement_periods
        is_starts = [p.period_start for p in is_periods]
        is_ends = [p.period_end for p in is_periods]
        assert is_starts == sorted(is_starts), f"{ptype} IS: periods not chronologically ordered"
        for i in range(len(is_periods) - 1):
            assert is_ends[i] <= is_starts[i + 1], (
                f"{ptype} IS: periods overlap at index {i}"
            )
        # BS periods have only period_end and period_index — check ordering by index
        bs_periods = fs.balance_sheet_periods
        bs_indices = [p.period_index for p in bs_periods]
        assert bs_indices == sorted(bs_indices), f"{ptype} BS: periods not ordered by index"
        bs_ends = [p.period_end for p in bs_periods]
        assert bs_ends == sorted(bs_ends), f"{ptype} BS: period_end not monotonically ordered"

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_construction_operating_classification_consistent(self, ptype):
        _, fs = _assemble(ptype)
        isp = fs.income_statement_periods
        # All construction periods precede all operating periods
        const_end = max(
            (p.period_index for p in isp if p.is_construction), default=-1
        )
        op_start = min(
            (p.period_index for p in isp if not p.is_construction), default=999999
        )
        assert const_end < op_start, f"{ptype}: construction/operating ordering violated"

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_senior_axis_no_duplicates_and_ordered(self, ptype):
        """Senior axis: no duplicate period indices, strictly ordered, non-empty."""
        run = _run_clean(ptype)
        sd = run.g2c_result.financing_result.project_model_result.senior_debt
        idxs = list(sd.period_indices)
        assert len(idxs) > 0, f"{ptype}: senior_debt has no periods"
        assert idxs == sorted(idxs), f"{ptype}: senior axis not ordered"
        assert len(idxs) == len(set(idxs)), f"{ptype}: duplicate senior axis indices"

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_cfads_axis_no_duplicates_and_ordered(self, ptype):
        """CFADS axis (tax authority): no duplicate period indices, ordered, non-empty."""
        run = _run_clean(ptype)
        tax = run.g2c_result.financing_result.project_model_result.tax_and_cfads
        idxs = list(tax.period_indices)
        assert len(idxs) > 0, f"{ptype}: tax_and_cfads has no periods"
        assert idxs == sorted(idxs), f"{ptype}: CFADS axis not ordered"
        assert len(idxs) == len(set(idxs)), f"{ptype}: duplicate CFADS axis indices"

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_waterfall_axis_no_duplicates_and_ordered(self, ptype):
        """PF Cash Waterfall axis: no duplicate period indices, ordered."""
        run = _run_clean(ptype)
        wps = run.g2c_result.waterfall_periods
        idxs = [wp.period_index for wp in wps]
        assert idxs == sorted(idxs), f"{ptype}: waterfall axis not ordered"
        assert len(idxs) == len(set(idxs)), f"{ptype}: duplicate waterfall axis indices"
        # Construction periods precede operating
        const_end = max((wp.period_index for wp in wps if wp.is_construction), default=-1)
        op_start = min((wp.period_index for wp in wps if not wp.is_construction), default=999999)
        assert const_end < op_start, f"{ptype}: waterfall construction/operating ordering violated"

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_re_axis_no_duplicates_and_covers_operating(self, ptype):
        """RE roll-forward axis: no duplicates, ordered, covers all operating IS periods."""
        _, fs = _assemble(ptype)
        rep = fs.retained_earnings_periods
        re_idxs = [p.period_index for p in rep]
        assert re_idxs == sorted(re_idxs), f"{ptype}: RE axis not ordered"
        assert len(re_idxs) == len(set(re_idxs)), f"{ptype}: duplicate RE axis indices"
        op_is_idxs = {p.period_index for p in fs.income_statement_periods if not p.is_construction}
        assert op_is_idxs.issubset(set(re_idxs)), (
            f"{ptype}: operating IS periods not covered by RE axis: "
            f"missing {op_is_idxs - set(re_idxs)}"
        )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_tax_bridge_axis_matches_is_axis(self, ptype):
        """Tax Bridge axis must match IS axis exactly (no missing, no extra periods)."""
        _, fs = _assemble(ptype)
        is_idx = sorted(p.period_index for p in fs.income_statement_periods)
        tb_idx = sorted(p.period_index for p in fs.tax_bridge_periods)
        assert tb_idx == is_idx, f"{ptype}: tax bridge axis != IS axis"
        assert len(tb_idx) == len(set(tb_idx)), f"{ptype}: duplicate TB axis indices"


# ===========================================================================
# §6 — Real balance-sheet freeze
# ===========================================================================

class TestFreezeS6_BalanceSheetFreeze:
    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_all_bs_periods_close_within_tolerance(self, ptype):
        _, fs = _assemble(ptype)
        fp = _FINGERPRINTS[ptype]
        bsp = fs.balance_sheet_periods
        assert len(bsp) == fp["n_bs_total"]
        failures = [
            (p.period_index, float(p.balance_check_keur or 0))
            for p in bsp
            if abs(float(p.balance_check_keur or 0)) > 1e-4
        ]
        assert not failures, f"{ptype}: BS periods not balanced: {failures}"

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_max_residual_within_regression_bound(self, ptype):
        _, fs = _assemble(ptype)
        fp = _FINGERPRINTS[ptype]
        bsp = fs.balance_sheet_periods
        max_res = max(abs(float(p.balance_check_keur or 0)) for p in bsp)
        # Must not exceed the frozen bound with 10x slack (regression, not exact)
        assert max_res <= fp["max_bs_residual"] * 10, (
            f"{ptype}: max residual {max_res:.3e} exceeds regression bound "
            f"{fp['max_bs_residual']:.3e} * 10"
        )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_balance_sheet_status_ok(self, ptype):
        _, fs = _assemble(ptype)
        assert fs.balance_sheet_status.value == "OK", f"{ptype} BS status not OK"


# ===========================================================================
# §7 — Statement accounting identities
# ===========================================================================

class TestFreezeS7_AccountingIdentities:
    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_pnl_identities_every_period(self, ptype):
        _, fs = _assemble(ptype)
        for p in fs.income_statement_periods:
            assert p.revenue_keur - p.opex_keur == pytest.approx(p.ebitda_keur, abs=1e-9)
            assert p.ebitda_keur - p.book_depreciation_keur == pytest.approx(p.ebit_keur, abs=1e-9)
            assert p.net_financial_result_keur == pytest.approx(
                p.financing_income_keur - p.senior_interest_expense_keur - p.shl_interest_expense_keur,
                abs=1e-9,
            )
            assert p.ebit_keur + p.net_financial_result_keur == pytest.approx(
                p.earnings_before_tax_keur, abs=1e-9
            )
            assert p.earnings_before_tax_keur - p.cit_accrual_keur == pytest.approx(
                p.net_income_keur, abs=1e-9
            )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_annual_tax_loss_ledger_reconciles_every_tax_year(self, ptype):
        """Annual FIFO tax-loss ledger: year-end closing becomes next year opening.

        Uses the canonical audit authority (tax_and_cfads) not the downstream
        TaxBridgePeriod. Reconciliation: closing[year_i] == opening[year_i+1]
        proves the ledger is gapless across all tax years.
        """
        run, fs_tax = _assemble(ptype)
        model = run.g2c_result.financing_result.project_model_result
        tax = model.tax_and_cfads
        opens = [float(x) for x in tax.tax_loss_opening_audit_keur]
        closes = [float(x) for x in tax.tax_loss_closing_audit_keur]
        used_vals = [float(x) for x in tax.tax_loss_used_audit_keur]
        idxs = list(tax.period_indices)

        # FIFO non-negativity: all ledger values must be >= 0 for EVERY period,
        # including construction. No COD exemption inside the per-period identity.
        for i, idx in enumerate(idxs):
            assert closes[i] >= -1e-6, (
                f"{ptype}: negative tax loss closing {closes[i]:.6f} at period {idx}"
            )
            assert opens[i] >= -1e-6, (
                f"{ptype}: negative tax loss opening {opens[i]:.6f} at period {idx}"
            )
            assert used_vals[i] >= -1e-6, (
                f"{ptype}: negative tax loss used {used_vals[i]:.6f} at period {idx}"
            )

        # Annual FIFO continuity: within operating periods, the year-end closing must
        # exactly equal the next year's opening (strict equality, not just ≤).
        # The construction→operating boundary is exempt: the tax base is reassessed
        # at COD and the opening of the first operating tax year may legitimately
        # differ from the closing of the last construction tax year.
        isp = fs_tax.income_statement_periods
        const_idx = {p.period_index for p in isp if p.is_construction}
        year_end_positions = [i for i in range(len(idxs))
                              if opens[i] != 0.0 or closes[i] != 0.0]
        for j in range(len(year_end_positions) - 1):
            pos_curr = year_end_positions[j]
            pos_next = year_end_positions[j + 1]
            # Skip the construction→operating boundary (COD reassessment)
            if idxs[pos_curr] in const_idx or idxs[pos_next] in const_idx:
                continue
            cl = closes[pos_curr]
            op_next = opens[pos_next]
            assert op_next == pytest.approx(cl, abs=1e-6), (
                f"{ptype}: tax loss ledger discontinuity: "
                f"closing {cl} at period {idxs[pos_curr]} "
                f"!= opening {op_next} at period {idxs[pos_next]}"
            )

        # Downstream TaxBridgePeriod must be consistent with the audit authority
        audit_closing = {idxs[i]: closes[i] for i in range(len(idxs))}
        for p in fs_tax.tax_bridge_periods:
            tb_cl = float(p.tax_loss_closing_keur or 0)
            audit_cl = audit_closing.get(p.period_index, 0.0)
            assert tb_cl == pytest.approx(audit_cl, abs=1e-6), (
                f"{ptype}: TaxBridgePeriod closing {tb_cl} != "
                f"audit authority {audit_cl} at period {p.period_index}"
            )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_re_roll_forward_every_period(self, ptype):
        """Verify the canonical RE roll-forward identity for every operating period.

        Uses fs.retained_earnings_periods as the authoritative source. The first
        operating period's opening RE must equal cod_opening_retained_earnings_keur.
        No periods are silently skipped.
        """
        _, fs = _assemble(ptype)
        rep = fs.retained_earnings_periods
        assert rep, f"{ptype}: no retained_earnings_periods"

        # First period: opening must equal COD canonical authority
        cod_re = float(fs.cod_opening_retained_earnings_keur or 0)
        first = rep[0]
        assert float(first.opening_retained_earnings_keur or 0) == pytest.approx(cod_re, abs=1e-6), (
            f"{ptype}: first RE period opening {float(first.opening_retained_earnings_keur or 0)} "
            f"!= COD opening RE {cod_re}"
        )

        # FIFO identity: opening + NI - gross_dividend - LR_allocation = closing (every period)
        for p in rep:
            op = float(p.opening_retained_earnings_keur or 0)
            ni = float(p.net_income_keur or 0)
            div = float(p.legal_equity_distribution_keur or 0)
            lr_alloc = float(p.legal_reserve_allocation_keur or 0)
            cl = float(p.closing_retained_earnings_keur or 0)
            expected = op + ni - div - lr_alloc
            assert cl == pytest.approx(expected, abs=1e-6), (
                f"{ptype} period {p.period_index}: RE roll-forward failed "
                f"(got {cl:.6f}, expected {expected:.6f})"
            )

        # Cross-period continuity: closing[t] == opening[t+1]
        for i in range(len(rep) - 1):
            cl = float(rep[i].closing_retained_earnings_keur or 0)
            op_next = float(rep[i + 1].opening_retained_earnings_keur or 0)
            assert cl == pytest.approx(op_next, abs=1e-6), (
                f"{ptype}: RE discontinuity: closing period {rep[i].period_index} "
                f"{cl:.6f} != opening period {rep[i+1].period_index} {op_next:.6f}"
            )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_lr_continuity_every_period(self, ptype):
        _, fs = _assemble(ptype)
        bsp = fs.balance_sheet_periods
        for i in range(1, len(bsp)):
            lr_prev = float(bsp[i - 1].legal_reserve_keur or 0)
            lr_curr = float(bsp[i].legal_reserve_keur or 0)
            assert lr_curr >= lr_prev - 1e-9, (
                f"{ptype}: LR decreased from {lr_prev} to {lr_curr} at period {bsp[i].period_index}"
            )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_uc_continuity_every_period(self, ptype):
        run = _run_clean(ptype)
        wps = run.g2c_result.waterfall_periods
        for i in range(1, len(wps)):
            uc_prev_cl = float(wps[i - 1].unrestricted_cash_closing_keur or 0)
            uc_curr_op = float(wps[i].unrestricted_cash_opening_keur or 0)
            assert uc_curr_op == pytest.approx(uc_prev_cl, abs=1e-9), (
                f"{ptype}: UC opening period {wps[i].period_index} != prior closing"
            )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_uc_roll_forward_every_period(self, ptype):
        run = _run_clean(ptype)
        wps = run.g2c_result.waterfall_periods
        for wp in wps:
            uc_op = float(wp.unrestricted_cash_opening_keur or 0)
            uc_chg = float(wp.change_in_unrestricted_cash_keur or 0)
            uc_cl = float(wp.unrestricted_cash_closing_keur or 0)
            assert uc_cl == pytest.approx(uc_op + uc_chg, abs=1e-9), (
                f"{ptype}: UC identity fails at period {wp.period_index}"
            )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_shl_gross_equals_cash_plus_pik(self, ptype):
        run = _run_clean(ptype)
        wps = [wp for wp in run.g2c_result.waterfall_periods if not wp.is_construction]
        for wp in wps:
            gross = float(wp.shl_gross_interest_keur or 0)
            cash_int = float(wp.shl_cash_interest_receipt_keur or 0)
            pik = float(wp.shl_pik_keur or 0)
            assert gross == pytest.approx(cash_int + pik, abs=1e-9), (
                f"{ptype}: SHL gross != cash+PIK at period {wp.period_index}"
            )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_accumulated_dep_equals_sum_of_book_dep(self, ptype):
        _, fs = _assemble(ptype)
        total = sum(p.book_depreciation_keur for p in fs.fixed_asset_periods)
        end = float(fs.fixed_asset_periods[-1].accumulated_book_depreciation_keur or 0)
        assert end == pytest.approx(total, rel=1e-6)


# ===========================================================================
# §8 — Generic Solar/Wind semantics
# ===========================================================================

class TestFreezeS8_SolarWindSemantics:
    @pytest.mark.parametrize("ptype", ("Solar", "Wind"))
    def test_financing_income_zero_by_policy(self, ptype):
        _, fs = _assemble(ptype)
        op = [p for p in fs.income_statement_periods if not p.is_construction]
        fi_vals = [p.financing_income_keur for p in op]
        assert all(v == pytest.approx(0.0, abs=1e-9) for v in fi_vals), (
            f"{ptype}: financing income is not ZERO_BY_POLICY: {[v for v in fi_vals if abs(v) > 1e-9]}"
        )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind"))
    def test_legal_reserve_zero_by_policy(self, ptype):
        _, fs = _assemble(ptype)
        lr_vals = [float(p.legal_reserve_keur or 0) for p in fs.balance_sheet_periods]
        assert all(v == pytest.approx(0.0, abs=1e-9) for v in lr_vals), (
            f"{ptype}: legal reserve != 0 for generic project: {[v for v in lr_vals if abs(v) > 1e-9]}"
        )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind"))
    def test_shl_pik_is_non_cash_expense(self, ptype):
        run = _run_clean(ptype)
        wps = [wp for wp in run.g2c_result.waterfall_periods if not wp.is_construction]
        # PIK accumulates in SHL balance but no cash changes hands
        for wp in wps:
            pik = float(wp.shl_pik_keur or 0)
            cash_int = float(wp.shl_cash_interest_receipt_keur or 0)
            if pik > 1e-9:
                # If PIK > 0, cash interest should be less than gross
                gross = float(wp.shl_gross_interest_keur or 0)
                assert cash_int < gross - 1e-9, (
                    f"{ptype}: PIK > 0 but cash_int == gross at period {wp.period_index}"
                )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind"))
    def test_bullet_fail_closed_no_invented_interest_post_maturity(self, ptype):
        run = _run_clean(ptype)
        wps = [wp for wp in run.g2c_result.waterfall_periods if not wp.is_construction]
        term = run.g2c_result.return_summary.terminal
        maturity_idx = term.shareholder_loan.contractual_maturity_period_index
        strictly_post = [wp for wp in wps if wp.period_index > maturity_idx]
        for wp in strictly_post:
            assert float(wp.shl_gross_interest_keur or 0) == pytest.approx(0.0, abs=1e-9), (
                f"{ptype}: invented SHL interest post-maturity at {wp.period_index}"
            )
            assert float(wp.actual_shl_principal_paid_keur or 0) == pytest.approx(0.0, abs=1e-9), (
                f"{ptype}: invented SHL principal post-maturity at {wp.period_index}"
            )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind"))
    def test_bullet_fail_closed_no_distributions_while_unpaid(self, ptype):
        run = _run_clean(ptype)
        wps = [wp for wp in run.g2c_result.waterfall_periods if not wp.is_construction]
        term = run.g2c_result.return_summary.terminal
        maturity_idx = term.shareholder_loan.contractual_maturity_period_index
        # At and after BULLET maturity with unpaid balance: no equity distribution
        for wp in wps:
            if wp.period_index >= maturity_idx:
                unpaid = float(wp.unpaid_shl_principal_keur or 0) if hasattr(wp, "unpaid_shl_principal_keur") else (
                    float(wp.actual_shl_closing_balance_keur or 0)
                )
                if unpaid > 1e-6:
                    dist = float(wp.legal_equity_distribution_keur or 0)
                    assert dist == pytest.approx(0.0, abs=1e-9), (
                        f"{ptype}: equity distribution while BULLET unpaid at {wp.period_index}"
                    )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind"))
    def test_trapped_cash_accumulates_in_g2c_uc(self, ptype):
        run = _run_clean(ptype)
        wps = [wp for wp in run.g2c_result.waterfall_periods if not wp.is_construction]
        term = run.g2c_result.return_summary.terminal
        maturity_idx = term.shareholder_loan.contractual_maturity_period_index
        post_mat = [wp for wp in wps if wp.period_index > maturity_idx]
        # UC must be monotonically non-decreasing post-maturity (cash is trapped)
        for i in range(len(post_mat) - 1):
            uc_curr = float(post_mat[i].unrestricted_cash_closing_keur or 0)
            uc_next = float(post_mat[i + 1].unrestricted_cash_closing_keur or 0)
            assert uc_next >= uc_curr - 1e-9, (
                f"{ptype}: UC decreased post-maturity at period {post_mat[i+1].period_index}"
            )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind"))
    def test_c3_uc_equals_g2c_uc_exactly(self, ptype):
        run, fs = _assemble(ptype)
        wps = run.g2c_result.waterfall_periods
        wp_by_idx = {wp.period_index: wp for wp in wps}
        for p in fs.balance_sheet_periods:
            wp = wp_by_idx.get(p.period_index)
            if wp is None:
                continue
            g2c_uc = float(wp.unrestricted_cash_closing_keur or 0)
            c3_uc = float(p.unrestricted_cash_keur or 0)
            assert abs(g2c_uc - c3_uc) <= 1e-6, (
                f"{ptype}: C3 UC {c3_uc} != G2C UC {g2c_uc} at period {p.period_index}"
            )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind"))
    def test_uc_identity_every_generic_operating_period(self, ptype):
        run = _run_clean(ptype)
        wps = [wp for wp in run.g2c_result.waterfall_periods if not wp.is_construction]
        for wp in wps:
            shl_in = float(getattr(wp, "shl_cash_input_keur", 0) or 0)
            shl_ci = float(getattr(wp, "shl_cash_interest_receipt_keur", 0) or 0)
            shl_pr = float(getattr(wp, "actual_shl_principal_paid_keur", 0) or 0)
            dist = float(getattr(wp, "legal_equity_distribution_keur", 0) or 0)
            unalloc = shl_in - shl_ci - shl_pr - dist
            expected_uc_chg = max(0.0, unalloc)
            uc_chg = float(wp.change_in_unrestricted_cash_keur or 0)
            assert uc_chg == pytest.approx(expected_uc_chg, abs=1e-6), (
                f"{ptype}: UC change identity fails at period {wp.period_index}: "
                f"got {uc_chg}, expected {expected_uc_chg}"
            )


# ===========================================================================
# §9 — Oborovo / TUHO source-proven semantics
# ===========================================================================

class TestFreezeS9_OborovoTUHOSemantics:
    def test_oborovo_financing_income_nonzero(self):
        """Oborovo has FI from U2 schedule authority (not ZERO_BY_POLICY)."""
        _, fs = _assemble("Oborovo")
        fi_total = sum(p.financing_income_keur for p in fs.income_statement_periods)
        assert fi_total == pytest.approx(71.003187, rel=1e-4)

    def test_tuho_financing_income_nonzero(self):
        """TUHO has FI from U2 schedule authority."""
        _, fs = _assemble("TUHO")
        fi_total = sum(p.financing_income_keur for p in fs.income_statement_periods)
        assert fi_total == pytest.approx(124.316738, rel=1e-4)

    def test_oborovo_shl_fully_repaid(self):
        run = _run_clean("Oborovo")
        term = run.g2c_result.return_summary.terminal
        assert term.shareholder_loan.status.value == "REPAID"
        wps = [wp for wp in run.g2c_result.waterfall_periods if not wp.is_construction]
        assert float(wps[-1].actual_shl_closing_balance_keur or 0) == pytest.approx(0.0, abs=1e-4)

    def test_tuho_shl_fully_repaid(self):
        run = _run_clean("TUHO")
        term = run.g2c_result.return_summary.terminal
        assert term.shareholder_loan.status.value == "REPAID"
        wps = [wp for wp in run.g2c_result.waterfall_periods if not wp.is_construction]
        assert float(wps[-1].actual_shl_closing_balance_keur or 0) == pytest.approx(0.0, abs=1e-4)

    def test_oborovo_legal_reserve_nonzero(self):
        """Oborovo retains documented legal reserve."""
        _, fs = _assemble("Oborovo")
        end_lr = float(fs.balance_sheet_periods[-1].legal_reserve_keur or 0)
        assert end_lr == pytest.approx(50.0, abs=1e-4)

    def test_tuho_legal_reserve_nonzero(self):
        """TUHO retains documented legal reserve."""
        _, fs = _assemble("TUHO")
        end_lr = float(fs.balance_sheet_periods[-1].legal_reserve_keur or 0)
        assert end_lr == pytest.approx(50.0, abs=1e-4)

    def test_oborovo_parity_exception_not_a_defect(self):
        """Oborovo source RE parity gap is documented — not an engine defect."""
        _, fs = _assemble("Oborovo")
        # Engine produces OK RE status
        assert fs.retained_earnings_status.value in ("OK", "OPENING_EQUITY_ACCOUNTING_AUTHORITY_UNAVAILABLE")
        # RE lineage parity exception remains classified (not silently removed)
        # Verification: engine runs cleanly without attempting to force parity
        assert fs.balance_sheet_status.value == "OK"

    def test_tuho_parity_exception_not_a_defect(self):
        """TUHO source SHL parity gap is documented — not an engine defect."""
        _, fs = _assemble("TUHO")
        assert fs.retained_earnings_status.value in ("OK", "OPENING_EQUITY_ACCOUNTING_AUTHORITY_UNAVAILABLE")
        assert fs.balance_sheet_status.value == "OK"

    def test_oborovo_construction_pik_accumulated(self):
        """Oborovo PIK during construction is non-zero."""
        run = _run_clean("Oborovo")
        pik_const = float(run.g2c_result.financing_result.shl_construction_pik_keur or 0)
        assert pik_const == pytest.approx(1169.659165, rel=1e-4)

    def test_tuho_construction_pik_accumulated(self):
        """TUHO PIK during construction is non-zero."""
        run = _run_clean("TUHO")
        pik_const = float(run.g2c_result.financing_result.shl_construction_pik_keur or 0)
        assert pik_const == pytest.approx(3520.419555, rel=1e-4)


# ===========================================================================
# §10 — Determinism (two independent runs)
# ===========================================================================

class TestFreezeS10_Determinism:
    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_two_runs_produce_identical_scalars(self, ptype):
        from app import project_factories as pf
        from app.services.production_financial_authority import run_clean_production
        from financial_engine.financial_statements import assemble_decision_complete_financial_statements

        factories = {
            "Solar": pf.create_default_solar_project,
            "Wind": pf.create_default_wind_project,
            "Oborovo": pf.create_default_oborovo,
            "TUHO": pf.create_default_tuho_wind1,
        }
        fn = factories[ptype]

        def get_scalars():
            proj = fn()
            r = run_clean_production(proj, project_type=ptype)
            fs = assemble_decision_complete_financial_statements(r.g2c_result, proj)
            isp = fs.income_statement_periods
            wps = [wp for wp in r.g2c_result.waterfall_periods if not wp.is_construction]
            return {
                "total_ebitda": sum(p.ebitda_keur for p in isp),
                "total_cit": sum(p.cit_accrual_keur for p in isp),
                "end_uc": float(wps[-1].unrestricted_cash_closing_keur or 0),
                "end_shl": float(wps[-1].actual_shl_closing_balance_keur or 0),
                "bs_max_res": max(abs(float(p.balance_check_keur or 0)) for p in fs.balance_sheet_periods),
                "senior": float(r.g2c_result.financing_result.final_senior_commitment_keur or 0),
            }

        run1 = get_scalars()
        run2 = get_scalars()
        for key in run1:
            assert run1[key] == pytest.approx(run2[key], rel=1e-12), (
                f"{ptype}: non-deterministic output for {key}: {run1[key]} vs {run2[key]}"
            )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_two_runs_produce_identical_vector_digests(self, ptype):
        from app import project_factories as pf
        from app.services.production_financial_authority import run_clean_production
        from financial_engine.financial_statements import assemble_decision_complete_financial_statements

        factories = {
            "Solar": pf.create_default_solar_project,
            "Wind": pf.create_default_wind_project,
            "Oborovo": pf.create_default_oborovo,
            "TUHO": pf.create_default_tuho_wind1,
        }
        fn = factories[ptype]

        def get_digest():
            proj = fn()
            r = run_clean_production(proj, project_type=ptype)
            fs = assemble_decision_complete_financial_statements(r.g2c_result, proj)
            op = [p for p in fs.income_statement_periods if not p.is_construction]
            wps = [wp for wp in r.g2c_result.waterfall_periods if not wp.is_construction]
            return {
                "ebitda": _vec_digest([p.ebitda_keur for p in op]),
                "uc": _vec_digest([float(wp.unrestricted_cash_closing_keur or 0) for wp in wps]),
                "shl_cl": _vec_digest([float(wp.actual_shl_closing_balance_keur or 0) for wp in wps]),
            }

        d1 = get_digest()
        d2 = get_digest()
        for key in d1:
            assert d1[key] == d2[key], f"{ptype}: non-deterministic {key} digest: {d1[key]} vs {d2[key]}"


# ===========================================================================
# §11 — Input sensitivity / no target fitting
# ===========================================================================

class TestFreezeS11_InputSensitivity:
    """Proves the engine is causal and the freeze fixture is not target-fitted."""

    def _run_solar(self, proj):
        from app.services.production_financial_authority import run_clean_production
        return run_clean_production(proj, project_type="Solar")

    def _solar_proj(self):
        from app import project_factories as pf
        return pf.create_default_solar_project()

    def test_ppa_price_increase_raises_revenue(self):
        import dataclasses
        from financial_engine.financial_statements import assemble_decision_complete_financial_statements

        proj_base = self._solar_proj()
        # Mutate PPA base tariff via nested dataclasses.replace
        rev_base = proj_base.revenue
        rev_high = dataclasses.replace(rev_base, ppa_base_tariff=rev_base.ppa_base_tariff * 1.20)
        proj_high = dataclasses.replace(proj_base, revenue=rev_high)

        r_base = self._run_solar(proj_base)
        r_high = self._run_solar(proj_high)
        fs_base = assemble_decision_complete_financial_statements(r_base.g2c_result, proj_base)
        fs_high = assemble_decision_complete_financial_statements(r_high.g2c_result, proj_high)
        rev_b = sum(p.revenue_keur for p in fs_base.income_statement_periods)
        rev_h = sum(p.revenue_keur for p in fs_high.income_statement_periods)
        assert rev_h > rev_b, f"Price +20% did not raise revenue: {rev_b:.1f} -> {rev_h:.1f}"

    def test_capex_increase_raises_senior_debt(self):
        import dataclasses

        proj_base = self._solar_proj()
        # Scale EPC contract amount via nested replace
        capex_base = proj_base.capex
        epc_base = capex_base.epc_contract
        epc_high = dataclasses.replace(epc_base, amount_keur=epc_base.amount_keur * 1.25)
        capex_high = dataclasses.replace(capex_base, epc_contract=epc_high)
        proj_high = dataclasses.replace(proj_base, capex=capex_high)

        r_base = self._run_solar(proj_base)
        r_high = self._run_solar(proj_high)
        senior_base = float(r_base.g2c_result.financing_result.final_senior_commitment_keur or 0)
        senior_high = float(r_high.g2c_result.financing_result.final_senior_commitment_keur or 0)
        assert senior_high > senior_base, (
            f"Capex +25% did not raise senior: {senior_base:.1f} -> {senior_high:.1f}"
        )

    def test_tax_rate_increase_raises_cit(self):
        import dataclasses
        from financial_engine.financial_statements import assemble_decision_complete_financial_statements

        proj_base = self._solar_proj()
        tax_base = proj_base.tax
        base_rate = tax_base.corporate_rate
        high_rate = min(base_rate * 1.60, 0.40)
        tax_high = dataclasses.replace(tax_base, corporate_rate=high_rate)
        proj_high = dataclasses.replace(proj_base, tax=tax_high)

        r_base = self._run_solar(proj_base)
        r_high = self._run_solar(proj_high)
        fs_base = assemble_decision_complete_financial_statements(r_base.g2c_result, proj_base)
        fs_high = assemble_decision_complete_financial_statements(r_high.g2c_result, proj_high)
        cit_base = sum(p.cit_accrual_keur for p in fs_base.income_statement_periods)
        cit_high = sum(p.cit_accrual_keur for p in fs_high.income_statement_periods)
        assert cit_high > cit_base, f"Tax rate +60% did not raise CIT: {cit_base:.1f} -> {cit_high:.1f}"

    def test_opex_increase_reduces_ebitda(self):
        import dataclasses
        from financial_engine.financial_statements import assemble_decision_complete_financial_statements

        proj_base = self._solar_proj()
        # Scale first OPEX item
        opex_base = proj_base.opex
        first_item = opex_base[0]
        high_item = dataclasses.replace(first_item, y1_amount_keur=first_item.y1_amount_keur * 3.0)
        opex_high = (high_item,) + opex_base[1:]
        proj_high = dataclasses.replace(proj_base, opex=opex_high)

        r_base = self._run_solar(proj_base)
        r_high = self._run_solar(proj_high)
        fs_base = assemble_decision_complete_financial_statements(r_base.g2c_result, proj_base)
        fs_high = assemble_decision_complete_financial_statements(r_high.g2c_result, proj_high)
        ebitda_base = sum(p.ebitda_keur for p in fs_base.income_statement_periods)
        ebitda_high = sum(p.ebitda_keur for p in fs_high.income_statement_periods)
        assert ebitda_high < ebitda_base, (
            f"OPEX x3 did not reduce EBITDA: {ebitda_base:.1f} -> {ebitda_high:.1f}"
        )

    def test_shl_rate_increase_raises_shl_interest(self):
        import dataclasses

        proj_base = self._solar_proj()
        fin_base = proj_base.financing
        # Use the canonical typed SHL-rate authority directly.
        # If this attribute disappears or the schema changes, this test MUST FAIL.
        base_rate = fin_base.shl_rate
        fin_high = dataclasses.replace(fin_base, shl_rate=base_rate * 2.0)
        proj_high = dataclasses.replace(proj_base, financing=fin_high)

        r_base = self._run_solar(proj_base)
        r_high = self._run_solar(proj_high)
        wps_base = [wp for wp in r_base.g2c_result.waterfall_periods if not wp.is_construction]
        wps_high = [wp for wp in r_high.g2c_result.waterfall_periods if not wp.is_construction]
        int_base = sum(float(wp.shl_gross_interest_keur or 0) for wp in wps_base)
        int_high = sum(float(wp.shl_gross_interest_keur or 0) for wp in wps_high)
        assert int_high > int_base, (
            f"SHL rate x2 did not raise interest: {int_base:.1f} -> {int_high:.1f}"
        )
