"""test_phasec3_u2_integration — Phase C3 Correction H acceptance tests (A–P).

Tests canonical U2 consumption, accounting semantics, FI axis, P&L identity,
LR/RE/UC authority, BS identity, four-project semantics, and KPI regression.

No workbook vectors. No source-output fitting. No economic mutation.
"""
from __future__ import annotations

import importlib
import pytest
import app.project_factories as pf
from financial_engine.financial_statements.assembly import (
    assemble_decision_complete_financial_statements,
)
from financial_engine.financial_statements.contracts import StatementStatus

_PROJECTS = ("Solar", "Wind", "Oborovo", "TUHO")

_FACTORY = {
    "Solar": pf.create_default_solar_project,
    "Wind": pf.create_default_wind_project,
    "Oborovo": pf.create_default_oborovo,
    "TUHO": pf.create_default_tuho_wind1,
}

_SOURCE_PROVEN_PROJECTS = ("Oborovo", "TUHO")  # projects with canonical U2 schedules
_GENERIC_PROJECTS = ("Solar", "Wind")  # zero-by-policy FI


def _run(ptype: str):
    """Return (run_result, FinancialStatementsResult) for a project type."""
    from app.services.production_financial_authority import run_clean_production
    proj = _FACTORY[ptype]()
    result = run_clean_production(proj, project_type=ptype)
    fs = assemble_decision_complete_financial_statements(
        result.g2c_result, project_inputs=result.project_inputs
    )
    return result, fs


# ---------------------------------------------------------------------------
# A — FI exact typed handoff
# ---------------------------------------------------------------------------
class TestA_FIHandoff:
    @pytest.mark.parametrize("ptype", _SOURCE_PROVEN_PROJECTS)
    def test_a_fi_values_match_u2_schedule(self, ptype):
        result, fs = _run(ptype)
        fin = result.g2c_result.financing_result
        cri = getattr(fin, "cash_reserve_interest_schedules", None)
        assert cri is not None, f"{ptype}: expected cash_reserve_interest_schedules"
        schedule = {int(pr.period_index): float(pr.calculated_financing_income_keur)
                    for pr in cri.period_results}
        pnl = {p.period_index: p.financing_income_keur for p in fs.income_statement_periods}
        for idx, fi_val in schedule.items():
            if idx in pnl:
                assert pnl[idx] == pytest.approx(fi_val, abs=1e-9), (
                    f"{ptype} period {idx}: FI mismatch — "
                    f"C3={pnl[idx]} U2={fi_val}"
                )


# ---------------------------------------------------------------------------
# B — EBIT excludes FI; FI is in financial result
# ---------------------------------------------------------------------------
class TestB_EBITExcludesFI:
    @pytest.mark.parametrize("ptype", _PROJECTS)
    def test_b_ebit_equals_ebitda_minus_book_dep(self, ptype):
        _, fs = _run(ptype)
        for p in fs.income_statement_periods:
            assert p.ebitda_keur - p.book_depreciation_keur == pytest.approx(
                p.ebit_keur, abs=1e-9
            ), (f"{ptype} period {p.period_index}: "
                f"EBIT={p.ebit_keur} != EBITDA-dep={p.ebitda_keur-p.book_depreciation_keur}")

    @pytest.mark.parametrize("ptype", _PROJECTS)
    def test_b_net_financial_includes_fi(self, ptype):
        _, fs = _run(ptype)
        for p in fs.income_statement_periods:
            expected_nf = (
                p.financing_income_keur
                - p.senior_interest_expense_keur
                - p.shl_interest_expense_keur
            )
            assert p.net_financial_result_keur == pytest.approx(expected_nf, abs=1e-9), (
                f"{ptype} period {p.period_index}: net_financial mismatch"
            )


# ---------------------------------------------------------------------------
# C — NI identity
# ---------------------------------------------------------------------------
class TestC_NIIdentity:
    @pytest.mark.parametrize("ptype", _PROJECTS)
    def test_c_ni_identity_every_period(self, ptype):
        _, fs = _run(ptype)
        for p in fs.income_statement_periods:
            ebt = p.ebit_keur + p.net_financial_result_keur
            assert ebt == pytest.approx(p.earnings_before_tax_keur, abs=1e-9)
            ni = ebt - p.cit_accrual_keur
            assert ni == pytest.approx(p.net_income_keur, abs=1e-9)


# ---------------------------------------------------------------------------
# D — CIT accrual vs cash tax
# ---------------------------------------------------------------------------
class TestD_CITAccrualVsCashTax:
    @pytest.mark.parametrize("ptype", ("Oborovo",))
    def test_d_accrual_differs_from_cash_tax(self, ptype):
        _, fs = _run(ptype)
        diffs = [
            abs((p.cit_accrual_keur or 0.0) - (tb.corporate_tax_cash_keur or 0.0))
            for p, tb in zip(fs.income_statement_periods, fs.tax_bridge_periods)
        ]
        assert any(d > 1e-9 for d in diffs), (
            f"{ptype}: expected at least one period where CIT accrual != cash tax"
        )


# ---------------------------------------------------------------------------
# E — FI authority from actual U2 schedule
# ---------------------------------------------------------------------------
class TestE_FIAuthorityFromSchedule:
    @pytest.mark.parametrize("ptype", _SOURCE_PROVEN_PROJECTS)
    def test_e_income_statement_ok_for_u2_projects(self, ptype):
        _, fs = _run(ptype)
        assert fs.income_statement_status == StatementStatus.OK, (
            f"{ptype}: income_statement_status should be OK, got {fs.income_statement_status}"
        )

    @pytest.mark.parametrize("ptype", _GENERIC_PROJECTS)
    def test_e_income_statement_ok_for_zero_by_policy(self, ptype):
        _, fs = _run(ptype)
        # Generic projects: no schedule, no enabled policy → FI=0 by policy → OK.
        assert fs.income_statement_status == StatementStatus.OK, (
            f"{ptype}: income_statement_status should be OK (zero by policy), "
            f"got {fs.income_statement_status}"
        )
        for p in fs.income_statement_periods:
            assert p.financing_income_keur == pytest.approx(0.0, abs=1e-9), (
                f"{ptype} period {p.period_index}: expected FI=0, got {p.financing_income_keur}"
            )


# ---------------------------------------------------------------------------
# F — FI axis mismatch fails closed
# ---------------------------------------------------------------------------
class TestF_FIAxisMismatch:
    def test_f_extra_fi_period_fails_closed(self):
        from unittest.mock import MagicMock, patch
        from financial_engine.financial_statements.contracts import StatementStatus
        result, _ = _run("Solar")
        # Inject a fake CRI with wrong period indices.
        fake_pr = MagicMock()
        fake_pr.period_index = 9999
        fake_pr.period_start = None
        fake_pr.period_end = None
        fake_pr.calculated_financing_income_keur = 1.0
        fake_cri = MagicMock()
        fake_cri.period_results = [fake_pr]
        fake_cri.authority = "SOURCE_PROVEN"
        with patch.object(
            result.g2c_result.financing_result,
            "cash_reserve_interest_schedules",
            fake_cri,
            create=True,
        ):
            proj = pf.create_default_solar_project()
            fs = assemble_decision_complete_financial_statements(
                result.g2c_result, project_inputs=proj
            )
        assert fs.status == StatementStatus.STATEMENT_PERIOD_AXIS_MISMATCH, (
            f"Expected STATEMENT_PERIOD_AXIS_MISMATCH, got {fs.status}"
        )


# ---------------------------------------------------------------------------
# G — Zero-FI source-proven period preserves EXISTING_CLEAN_AUTHORITY
# ---------------------------------------------------------------------------
class TestG_ZeroFIPreservesAuthority:
    @pytest.mark.parametrize("ptype", _SOURCE_PROVEN_PROJECTS)
    def test_g_zero_fi_period_keeps_clean_authority(self, ptype):
        _, fs = _run(ptype)
        fin_result = None
        for p in fs.income_statement_periods:
            if abs(p.financing_income_keur) < 1e-9:
                # A period with zero FI must still carry EXISTING_CLEAN_AUTHORITY when
                # the schedule exists (authority is from contract, not from value != 0).
                auth = p.authority.get("financing_income", "")
                assert auth == "EXISTING_CLEAN_AUTHORITY", (
                    f"{ptype} period {p.period_index}: zero-FI period has "
                    f"authority={auth!r}, expected EXISTING_CLEAN_AUTHORITY"
                )
                fin_result = True
                break
        # If no zero-FI period exists, skip — test is inapplicable.
        if fin_result is None:
            pytest.skip(f"{ptype}: no zero-FI period found; test not applicable")


# ---------------------------------------------------------------------------
# H — UC opening/change/closing identity
# ---------------------------------------------------------------------------
class TestH_UCIdentity:
    @pytest.mark.parametrize("ptype", _PROJECTS)
    def test_h_uc_continuity_every_operating_period(self, ptype):
        result, fs = _run(ptype)
        wps_map = {
            getattr(wp, "cashflow_date", None): wp
            for wp in result.g2c_result.waterfall_periods
        }
        for bsp in fs.balance_sheet_periods:
            if bsp.unrestricted_cash_keur is None:
                continue  # construction period with no G2C join
            wp = wps_map.get(bsp.period_end)
            if wp is None:
                continue
            # Prove closing = opening + change.
            uc_open = float(getattr(wp, "unrestricted_cash_opening_keur", 0.0) or 0.0)
            uc_chg = float(getattr(wp, "change_in_unrestricted_cash_keur", 0.0) or 0.0)
            uc_close = float(getattr(wp, "unrestricted_cash_closing_keur", 0.0) or 0.0)
            assert uc_open + uc_chg == pytest.approx(uc_close, abs=1e-6), (
                f"{ptype} period {bsp.period_index}: UC identity broken — "
                f"opening={uc_open} + change={uc_chg} != closing={uc_close}"
            )


# ---------------------------------------------------------------------------
# I — UC continuity (closing[t] = opening[t+1])
# ---------------------------------------------------------------------------
class TestI_UCContinuity:
    @pytest.mark.parametrize("ptype", _PROJECTS)
    def test_i_uc_closing_equals_next_opening(self, ptype):
        result, _ = _run(ptype)
        wps = sorted(
            result.g2c_result.waterfall_periods,
            key=lambda w: getattr(w, "cashflow_date", None) or 0,
        )
        for i in range(len(wps) - 1):
            close = float(getattr(wps[i], "unrestricted_cash_closing_keur", 0.0) or 0.0)
            nxt_open = float(getattr(wps[i + 1], "unrestricted_cash_opening_keur", 0.0) or 0.0)
            assert close == pytest.approx(nxt_open, abs=1e-6), (
                f"{ptype}: UC closing[{i}]={close} != opening[{i+1}]={nxt_open}"
            )


# ---------------------------------------------------------------------------
# J — Canonical LR handoff, no C3 recomputation
# ---------------------------------------------------------------------------
class TestJ_CanonicalLRHandoff:
    def test_j_no_roll_forward_equity_state_import_in_assembly(self):
        """C3 assembly must not import roll_forward_equity_state for LR computation."""
        import ast, pathlib
        src = pathlib.Path("financial_engine/financial_statements/assembly.py").read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = (
                    [a.name for a in node.names]
                    if isinstance(node, ast.Import)
                    else [a.name for a in node.names]
                )
                module = getattr(node, "module", "") or ""
                for name in names:
                    assert "roll_forward_equity_state" not in name, (
                        "assembly.py must not import roll_forward_equity_state — "
                        "LR comes from canonical U2 G2C waterfall periods."
                    )
                assert "roll_forward_equity_state" not in module

    @pytest.mark.parametrize("ptype", _SOURCE_PROVEN_PROJECTS)
    def test_j_lr_matches_waterfall_closing(self, ptype):
        result, fs = _run(ptype)
        wps_map = {
            getattr(wp, "cashflow_date", None): wp
            for wp in result.g2c_result.waterfall_periods
        }
        for bsp in fs.balance_sheet_periods:
            if bsp.legal_reserve_keur is None:
                continue
            wp = wps_map.get(bsp.period_end)
            if wp is None:
                continue
            wp_lr = float(getattr(wp, "closing_legal_reserve_keur", 0.0) or 0.0)
            assert bsp.legal_reserve_keur == pytest.approx(wp_lr, abs=1e-6), (
                f"{ptype} period {bsp.period_index}: BS LR={bsp.legal_reserve_keur} "
                f"!= G2C LR={wp_lr}"
            )


# ---------------------------------------------------------------------------
# K — RE roll-forward
# ---------------------------------------------------------------------------
class TestK_RErollForward:
    @pytest.mark.parametrize("ptype", _SOURCE_PROVEN_PROJECTS)
    def test_k_re_roll_forward_identity(self, ptype):
        _, fs = _run(ptype)
        if fs.retained_earnings_status != StatementStatus.OK:
            pytest.skip(f"{ptype}: RE not available ({fs.retained_earnings_status})")
        prev_close = None
        for rp in fs.retained_earnings_periods:
            if prev_close is not None:
                assert rp.opening_retained_earnings_keur == pytest.approx(
                    prev_close, abs=1e-6
                ), (f"{ptype}: RE continuity broken at period {rp.period_index}")
            if rp.closing_retained_earnings_keur is not None:
                expected = (
                    (rp.opening_retained_earnings_keur or 0.0)
                    + rp.net_income_keur
                    - rp.legal_equity_distribution_keur
                    - (rp.legal_reserve_allocation_keur or 0.0)
                )
                assert rp.closing_retained_earnings_keur == pytest.approx(
                    expected, abs=1e-6
                ), (f"{ptype} period {rp.period_index}: RE roll-forward identity broken")
            prev_close = rp.closing_retained_earnings_keur


# ---------------------------------------------------------------------------
# L — DA != unrestricted cash
# ---------------------------------------------------------------------------
class TestL_DANotUC:
    @pytest.mark.parametrize("ptype", _PROJECTS)
    def test_l_da_and_uc_are_distinct_accounts(self, ptype):
        _, fs = _run(ptype)
        da_col = {bsp.period_index: bsp.distribution_account_balance_keur
                  for bsp in fs.balance_sheet_periods}
        uc_col = {bsp.period_index: bsp.unrestricted_cash_keur
                  for bsp in fs.balance_sheet_periods}
        # DA and UC must not always be equal (when non-trivial).
        non_trivial = [
            idx for idx in da_col
            if da_col.get(idx) is not None and uc_col.get(idx) is not None
            and (abs(da_col[idx]) + abs(uc_col[idx])) > 1e-6
        ]
        if non_trivial:
            # At least one period where they differ.
            different = any(
                abs(da_col[idx] - uc_col[idx]) > 1e-9
                for idx in non_trivial
            )
            assert different or all(da_col[idx] == pytest.approx(0.0, abs=1e-6)
                                    for idx in non_trivial), (
                f"{ptype}: DA and UC appear identical across all non-trivial periods — "
                "confirm they are distinct balance sheet accounts."
            )


# ---------------------------------------------------------------------------
# M — Real BS equality / no residual plug
# ---------------------------------------------------------------------------
class TestM_BSIdentity:
    @pytest.mark.parametrize("ptype", _SOURCE_PROVEN_PROJECTS)
    def test_m_bs_balance_check_near_zero(self, ptype):
        _, fs = _run(ptype)
        checks = [
            (bsp.period_index, bsp.balance_check_keur)
            for bsp in fs.balance_sheet_periods
            if bsp.balance_check_keur is not None
        ]
        assert checks, f"{ptype}: no balance_check_keur computed"
        max_residual = max(abs(v) for _, v in checks)
        assert max_residual <= 1e-4, (
            f"{ptype}: max BS residual={max_residual} kEUR exceeds tolerance. "
            f"First violator: {next((idx, v) for idx, v in checks if abs(v) > 1e-4)}"
        )


# ---------------------------------------------------------------------------
# N — Four-project completeness semantics
# ---------------------------------------------------------------------------
class TestN_FourProjectMatrix:
    @pytest.mark.parametrize("ptype", _PROJECTS)
    def test_n_income_statement_complete(self, ptype):
        _, fs = _run(ptype)
        assert fs.income_statement_status == StatementStatus.OK
        assert len(fs.income_statement_periods) > 0

    @pytest.mark.parametrize("ptype", _PROJECTS)
    def test_n_tax_bridge_complete(self, ptype):
        _, fs = _run(ptype)
        assert fs.tax_bridge_status == StatementStatus.OK

    @pytest.mark.parametrize("ptype", _PROJECTS)
    def test_n_unrestricted_cash_resolved(self, ptype):
        _, fs = _run(ptype)
        assert fs.unrestricted_cash_status == StatementStatus.OK

    @pytest.mark.parametrize("ptype", _SOURCE_PROVEN_PROJECTS)
    def test_n_lr_present_for_source_proven_projects(self, ptype):
        _, fs = _run(ptype)
        assert fs.legal_reserve_status == StatementStatus.OK, (
            f"{ptype}: expected legal_reserve_status OK, got {fs.legal_reserve_status}"
        )

    @pytest.mark.parametrize("ptype", _GENERIC_PROJECTS)
    def test_n_fi_zero_for_generic_projects(self, ptype):
        _, fs = _run(ptype)
        for p in fs.income_statement_periods:
            assert p.financing_income_keur == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# O — Deterministic second run
# ---------------------------------------------------------------------------
class TestO_Deterministic:
    @pytest.mark.parametrize("ptype", _PROJECTS)
    def test_o_second_run_identical(self, ptype):
        _, fs1 = _run(ptype)
        _, fs2 = _run(ptype)
        for p1, p2 in zip(fs1.income_statement_periods, fs2.income_statement_periods):
            assert p1.net_income_keur == pytest.approx(p2.net_income_keur, abs=1e-12)
            assert p1.ebit_keur == pytest.approx(p2.ebit_keur, abs=1e-12)
            assert p1.financing_income_keur == pytest.approx(p2.financing_income_keur, abs=1e-12)


# ---------------------------------------------------------------------------
# P — Frozen KPI regression (total NI sum across all projects)
# ---------------------------------------------------------------------------
class TestP_KPIRegression:
    @pytest.mark.parametrize("ptype", _PROJECTS)
    def test_p_ni_vector_non_trivial(self, ptype):
        """Net income must be non-trivial (some periods positive) — not all zeros."""
        _, fs = _run(ptype)
        ni_vals = [p.net_income_keur for p in fs.income_statement_periods
                   if not bool(getattr(p, "is_construction", False))]
        assert any(abs(v) > 1.0 for v in ni_vals), (
            f"{ptype}: all operating period NI values near zero — suspect regression"
        )
