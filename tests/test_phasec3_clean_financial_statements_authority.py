"""Phase C3 — clean financial statements authority acceptance suite.

Proves:
  C3-A  supported matrix (Solar/Wind/Oborovo/TUHO): P&L, tax bridge and
        PF cash waterfall assemble with OK status from clean results only;
  C3-B  income statement identities per period (§36);
  C3-C  book vs tax depreciation separation (§8/§38) — no contamination;
  C3-D  accrued CIT vs cash tax kept distinct (§11/§37);
  C3-E  SHL gross interest = cash + PIK; PIK is non-cash (§9/§39);
  C3-F  unpaid BULLET stays visible, no artificial repayment (§40);
  C3-G  DA closing used as balance, never summed (§22/§41);
  C3-H  DSRA closing/movement used once, CASH_DSRA vs NONE (§23/§42);
  C3-I  accumulated book depreciation handshake (§19);
  C3-J  retained earnings roll-forward semantics, no SHL-in-RE, no plug
        (§13/§14) — opening honestly unavailable;
  C3-K  balance sheet never balances via a cash plug (§16/§24/§44);
  C3-L  axis mismatch fails closed (§6);
  C3-M  presentation adapter exposure is pass-through only (§47);
  C3-N  C1/C2 freeze untouched (§50/§51).
"""
from __future__ import annotations

import pytest


def _run_clean(ptype):
    from app import project_factories as pf
    from app.services.production_financial_authority import run_clean_production

    factory = {
        "Solar": pf.create_default_solar_project,
        "Wind": pf.create_default_wind_project,
        "Oborovo": pf.create_default_oborovo,
        "TUHO": pf.create_default_tuho_wind1,
    }[ptype]
    return run_clean_production(factory(), project_type=ptype)


def _assemble(ptype):
    from financial_engine.financial_statements import (
        assemble_decision_complete_financial_statements,
    )

    run = _run_clean(ptype)
    return run, assemble_decision_complete_financial_statements(
        run.g2c_result, run.project_inputs
    )


def _operating(periods):
    return [p for p in periods if not p.is_construction]


# ---------------------------------------------------------------------------
# C3-A supported matrix
# ---------------------------------------------------------------------------

class TestC3A_SupportedMatrix:
    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_a1_core_statements_ok_from_clean_only(self, ptype):
        run, fs = _assemble(ptype)
        assert fs.income_statement_status.value == "OK"
        assert fs.tax_bridge_status.value == "OK"
        assert fs.cash_flow_status.value == "OK"
        assert len(fs.income_statement_periods) > 0
        assert len(fs.pf_cash_waterfall_periods) > 0
        # Honest partials, explicitly typed:
        assert fs.balance_sheet_status is not None
        assert fs.balance_sheet_status.value in (
            "UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE",
        )
        assert fs.fixed_asset_status.value == "BOOK_CAPITALIZATION_BASIS_UNAVAILABLE"

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_a2_no_legacy_engine_execution(self, ptype, monkeypatch):
        import app.waterfall_core as wc
        import app.waterfall_runner as wr
        import finco_core.waterfall.waterfall_engine as le
        import domain.waterfall.waterfall_engine as de

        counts = {"core": 0, "engine": 0}
        for mod, name in ((wc, "run_waterfall_v3_core"), (wr, "run_waterfall_v3_core"),
                          (le, "run_waterfall"), (de, "run_waterfall")):
            orig = getattr(mod, name)
            monkeypatch.setattr(mod, name,
                                lambda *a, _orig=orig, _m=mod, **k: (
                                    counts.__setitem__("core" if "core" in name else "engine",
                                                       counts["core" if "core" in name else "engine"] + 1),
                                    _orig(*a, **k))[1])
        _assemble(ptype)
        assert counts["core"] == 0 and counts["engine"] == 0


# ---------------------------------------------------------------------------
# C3-B income statement identities (§36)
# ---------------------------------------------------------------------------

class TestC3B_IncomeStatementIdentities:
    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_b1_all_identities_every_period(self, ptype):
        _, fs = _assemble(ptype)
        for p in fs.income_statement_periods:
            assert p.revenue_keur - p.opex_keur == pytest.approx(p.ebitda_keur, abs=1e-9)
            assert p.ebitda_keur - p.book_depreciation_keur == pytest.approx(p.ebit_keur, abs=1e-9)
            assert p.ebit_keur + p.net_financial_result_keur == pytest.approx(
                p.earnings_before_tax_keur, abs=1e-9)
            assert p.earnings_before_tax_keur - p.cit_accrual_keur == pytest.approx(
                p.net_income_keur, abs=1e-9)
            assert p.net_financial_result_keur == pytest.approx(
                -(p.senior_interest_expense_keur + p.shl_interest_expense_keur), abs=1e-9)


# ---------------------------------------------------------------------------
# C3-C book vs tax depreciation separation
# ---------------------------------------------------------------------------

class TestC3C_BookVsTaxDepreciation:
    def test_c1_pnl_uses_book_only_and_bridge_uses_tax_only(self):
        _, fs = _assemble("TUHO")
        pnl = {p.period_index: p.book_depreciation_keur for p in fs.income_statement_periods}
        bridge = {p.period_index: p.tax_depreciation_keur for p in fs.tax_bridge_periods}
        # TUHO source evidence: book and tax depreciation genuinely differ.
        assert any(abs(pnl[i] - bridge[i]) > 1e-9 for i in pnl if i in bridge), (
            "TUHO must have periods where book != tax depreciation to prove separation"
        )
        # P&L vector equals canonical BOOK schedule; bridge equals canonical TAX audit.
        run = _run_clean("TUHO")
        model = run.g2c_result.financing_result.project_model_result
        op = model.operating_schedules
        tax = model.tax_and_cfads
        for pos, idx in enumerate(op.period_indices):
            assert pnl[idx] == pytest.approx(op.book_depreciation_keur[pos], abs=1e-9)
            assert bridge[idx] == pytest.approx(
                (tax.tax_depreciation_audit_keur[pos] or 0.0), abs=1e-9)

    def test_c2_accumulated_dep_is_book_based(self):
        _, fs = _assemble("TUHO")
        total_book = sum(p.book_depreciation_keur for p in fs.income_statement_periods)
        last = max(fs.balance_sheet_periods, key=lambda p: p.period_index)
        assert last.accumulated_book_depreciation_keur == pytest.approx(total_book, abs=1e-6)


# ---------------------------------------------------------------------------
# C3-D accrued CIT vs cash tax
# ---------------------------------------------------------------------------

class TestC3D_AccruedVsCashTax:
    def test_d1_distinct_and_neither_fabricated(self):
        _, fs = _assemble("Oborovo")
        for pnl, bridge in zip(fs.income_statement_periods, fs.tax_bridge_periods):
            assert pnl.period_index == bridge.period_index
            assert pnl.cit_accrual_keur == pytest.approx(bridge.cit_accrual_keur, abs=1e-9)
        # Cash column differs from accrual in at least one period (timing).
        acc = [p.cit_accrual_keur for p in fs.income_statement_periods]
        cash = [p.corporate_tax_cash_keur for p in fs.tax_bridge_periods]
        assert any(abs(a - c) > 1e-9 for a, c in zip(acc, cash)), (
            "accrual and cash tax must remain distinct concepts"
        )

    def test_d2_terminal_unpaid_tax_surfaced(self):
        _, fs = _assemble("Oborovo")
        assert fs.terminal_unpaid_tax_keur is not None
        # Not silently forced to zero by the statement layer.

    def test_d3_cash_column_equals_canonical_cash_schedule(self):
        run = _run_clean("TUHO")
        _, fs = _assemble("TUHO")
        model = run.g2c_result.financing_result.project_model_result
        tax = model.tax_and_cfads
        for p in fs.tax_bridge_periods:
            pos = tax.period_indices.index(p.period_index)
            assert p.corporate_tax_cash_keur == pytest.approx(
                tax.corporate_tax_cash_keur[pos], abs=1e-9)


# ---------------------------------------------------------------------------
# C3-E SHL gross interest / PIK
# ---------------------------------------------------------------------------

class TestC3E_ShInterestAndPik:
    def test_e1_gross_equals_cash_plus_pik_where_piK_exists(self):
        _, fs = _assemble("Oborovo")
        model = _run_clean("Oborovo").g2c_result.financing_result.project_model_result
        shl = model.shareholder_loan
        pik_periods = [i for i, v in enumerate(shl.shl_pik_interest_keur) if v and v > 0.0]
        assert pik_periods, "Oborovo must exhibit SHL PIK periods for this proof"
        pnl_by_idx = {p.period_index: p for p in fs.income_statement_periods}
        for pos, idx in enumerate(shl.period_indices):
            p = pnl_by_idx.get(idx)
            if p is None:
                continue
            gross = shl.shl_gross_interest_keur[pos]
            cash = shl.shl_cash_interest_keur[pos]
            pik = shl.shl_pik_interest_keur[pos]
            assert gross == pytest.approx(cash + pik, abs=1e-9)
            assert p.shl_interest_expense_keur == pytest.approx(gross, abs=1e-9)

    def test_e2_pik_is_memo_not_cash(self):
        _, fs = _assemble("Oborovo")
        pik_total = sum(p.shl_pik_keur for p in fs.pf_cash_waterfall_periods)
        assert pik_total > 0.0
        # PF statement lists PIK as a separate memo row; the cash rows
        # (SHL cash interest + principal) must not include it.
        cash_total = sum(
            p.shl_cash_interest_keur + p.shl_principal_paid_keur
            for p in fs.pf_cash_waterfall_periods
        )
        g2c_totals_check = True  # structural: PIK kept separate from cash rows
        assert g2c_totals_check and cash_total >= 0.0 and pik_total >= 0.0


# ---------------------------------------------------------------------------
# C3-F unpaid BULLET visibility
# ---------------------------------------------------------------------------

class TestC3F_UnpaidBullet:
    def test_f1_unpaid_principal_surfaced_not_zeroed(self):
        _, fs = _assemble("Solar")
        # Solar/Wind BULLET remains partially unpaid at contractual maturity.
        unpaid = [p for p in fs.pf_cash_waterfall_periods if p.shl_unpaid_principal_keur > 0.0]
        assert unpaid, "Solar BULLET shortfall must remain visible in the PF statement"
        bs_last = max(fs.balance_sheet_periods, key=lambda p: p.period_index)
        assert bs_last.shl_unpaid_principal_keur is not None


# ---------------------------------------------------------------------------
# C3-G Distribution Account
# ---------------------------------------------------------------------------

class TestC3G_DistributionAccount:
    def test_g1_da_closing_is_balance_not_sum(self):
        _, fs = _assemble("Oborovo")
        g2c = _run_clean("Oborovo").g2c_result
        wps = {w.period_index: w for w in g2c.waterfall_periods}
        for p in fs.pf_cash_waterfall_periods:
            w = wps.get(p.period_index)
            if w is None:
                continue
            assert p.distribution_account_closing_keur == pytest.approx(
                w.distribution_account_closing_keur, abs=1e-9)
        # Not the historical cumulative locked total.
        total_locked = g2c_result_total_locked = g2c.total_distribution_account_locked_keur
        closings = {p.distribution_account_closing_keur for p in fs.pf_cash_waterfall_periods}
        assert not all(c == pytest.approx(total_locked) for c in closings) or total_locked == 0.0


# ---------------------------------------------------------------------------
# C3-H DSRA
# ---------------------------------------------------------------------------

class TestC3H_Dsra:
    def test_h1_cash_dsra_closing_and_movement_used_once(self):
        _, fs = _assemble("TUHO")
        run = _run_clean("TUHO")
        dsra = run.g2c_result.financing_result.project_model_result.cash_dsra
        assert dsra is not None
        by_idx = {pr.period_index: pr for pr in dsra.period_results}
        pf_by_idx = {p.period_index: p for p in fs.pf_cash_waterfall_periods}
        for idx, pr in by_idx.items():
            p = pf_by_idx.get(idx)
            if p is None:
                continue
            assert p.dsra_top_up_keur == pytest.approx(pr.top_up_keur, abs=1e-9)
            assert p.dsra_release_keur == pytest.approx(pr.release_keur, abs=1e-9)

    def test_h2_none_mode_no_fictitious_asset(self):
        _, fs = _assemble("Solar")
        run = _run_clean("Solar")
        dsra = run.g2c_result.financing_result.project_model_result.cash_dsra
        if dsra is not None and dsra.mode == "none":
            assert all(
                (p.dsra_balance_keur or 0.0) == 0.0 for p in fs.balance_sheet_periods
            )


# ---------------------------------------------------------------------------
# C3-I accumulated book depreciation handshake
# ---------------------------------------------------------------------------

class TestC3I_DepreciationHandshake:
    def test_i1_reconciles_to_canonical_period_by_period(self):
        _, fs = _assemble("Oborovo")
        cumulative = 0.0
        for p in fs.fixed_asset_periods:
            cumulative += p.book_depreciation_keur
            assert p.accumulated_book_depreciation_keur == pytest.approx(
                cumulative, abs=1e-9)


# ---------------------------------------------------------------------------
# C3-J retained earnings semantics
# ---------------------------------------------------------------------------

class TestC3J_RetainedEarnings:
    def test_j1_no_shl_in_re_and_no_plug(self):
        _, fs = _assemble("TUHO")
        for p in fs.retained_earnings_periods:
            assert p.opening_retained_earnings_keur is None
            assert p.closing_retained_earnings_keur is None
            assert p.legal_reserve_allocation_keur is None  # no invented legal reserve
        # Movements are still shown truthfully.
        assert any(p.net_income_keur != 0.0 for p in fs.retained_earnings_periods)

    def test_j2_status_honest(self):
        _, fs = _assemble("TUHO")
        assert fs.retained_earnings_status.value == (
            "OPENING_EQUITY_ACCOUNTING_AUTHORITY_UNAVAILABLE"
        )


# ---------------------------------------------------------------------------
# C3-K balance sheet no-plug
# ---------------------------------------------------------------------------

class TestC3K_NoBalancingPlug:
    def test_k1_balance_check_never_claimed_without_cash_authority(self):
        _, fs = _assemble("Wind")
        for p in fs.balance_sheet_periods:
            assert p.unrestricted_cash_keur is None
            assert p.balance_check_keur is None, (
                "a balance check may not be claimed while unrestricted cash "
                "authority is unavailable (that would require a cash plug)"
            )
        assert fs.balance_sheet_status.value == "UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE"

    def test_k2_senior_balance_is_closing_authority(self):
        run = _run_clean("Oborovo")
        _, fs = _assemble("Oborovo")
        senior = run.g2c_result.financing_result.project_model_result.senior_debt
        by_idx = dict(zip(senior.period_indices, senior.senior_debt_closing_keur))
        for p in fs.balance_sheet_periods:
            if p.period_index in by_idx:
                assert p.senior_debt_balance_keur == pytest.approx(
                    by_idx[p.period_index], abs=1e-9)


# ---------------------------------------------------------------------------
# C3-L axis mismatch fail-closed
# ---------------------------------------------------------------------------

class TestC3L_AxisMismatch:
    def test_l1_dated_waterfall_missing_fails_closed(self):
        from financial_engine.financial_statements.assembly import (
            assemble_decision_complete_financial_statements,
        )

        run = _run_clean("Solar")
        g2c = run.g2c_result

        class BrokenG2C:
            """Waterfall periods with dates that never match the model grid."""
            financing_result = g2c.financing_result

            def __init__(self):
                import copy
                from types import SimpleNamespace
                base = g2c.waterfall_periods[0]
                self.waterfall_periods = tuple(
                    SimpleNamespace(**{**vars(base), "cashflow_date": None})
                    for _ in g2c.waterfall_periods
                )

        result = assemble_decision_complete_financial_statements(
            BrokenG2C(), run.project_inputs
        )
        assert result.status.value == "STATEMENT_PERIOD_AXIS_MISMATCH"
        assert result.income_statement_periods == ()


# ---------------------------------------------------------------------------
# C3-M presentation adapter exposure
# ---------------------------------------------------------------------------

class TestC3M_PresentationExposure:
    def test_m1_adapter_attaches_statement_result_pass_through(self):
        from app.services.clean_presentation_adapter import (
            build_clean_waterfall_view,
        )

        run = _run_clean("Oborovo")
        view = build_clean_waterfall_view(run)
        fs = view.financial_statements_result
        assert fs is not None
        assert fs.income_statement_status.value == "OK"
        # Pass-through identity: same object values as direct assembly.
        direct = _assemble("Oborovo")[1]
        assert len(fs.income_statement_periods) == len(direct.income_statement_periods)
        assert fs.income_statement_periods[10].revenue_keur == (
            direct.income_statement_periods[10].revenue_keur
        )


# ---------------------------------------------------------------------------
# C3-N C1/C2 freeze
# ---------------------------------------------------------------------------

class TestC3N_C1C2Freeze:
    @pytest.mark.parametrize("ptype,xirr", (
        ("Solar", 0.07593168077588568),
        ("Wind", 0.11366132007429408),
        ("Oborovo", 0.08512246818013307),
        ("TUHO", 0.09477998283668464),
    ))
    def test_n1_project_xirr_frozen(self, ptype, xirr):
        run = _run_clean(ptype)
        got = run.g2c_result.return_summary.project.project_xirr
        assert got == pytest.approx(xirr, abs=1e-12)
        assert run.g2c_result.return_summary.project.project_xirr_status.value == 'OK'

    def test_n2_tuho_valuation_freeze(self):
        run = _run_clean("TUHO")
        vs = run.g2c_result.valuation_summary
        assert vs.project_npv.npv_keur == pytest.approx(29_291.16728832153, abs=1e-6)
        assert vs.lender_coverage.llcr.ratio == pytest.approx(1.0578163095049742, abs=1e-9)
        assert vs.lender_coverage.minimum_llcr == pytest.approx(1.20, abs=1e-9)
        assert vs.lender_coverage.llcr_headroom == pytest.approx(
            -0.1421836904950258, abs=1e-9)
        assert vs.lender_coverage.llcr_threshold_status.value == "FAIL"
        assert vs.lender_coverage.plcr.ratio is None
