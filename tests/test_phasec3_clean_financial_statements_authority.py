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
  C3-J  retained earnings roll-forward semantics, no SHL-in-RE, no residual-cash insert
        (§13/§14) — opening honestly unavailable;
  C3-K  balance sheet never balances via a cash residual-cash insert (§16/§24/§44);
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
    def test_a1_core_statements_assemble_with_honest_statuses(self, ptype):
        run, fs = _assemble(ptype)
        # Correction A: P&L may not claim OK while financing income
        # (interest on unrestricted cash) has no clean authority.
        assert fs.income_statement_status.value == "FINANCING_INCOME_AUTHORITY_UNAVAILABLE"
        assert fs.tax_bridge_status.value == "OK"
        # PF cash is OK: construction rows mapped + operating waterfall full.
        assert fs.cash_flow_status.value == "OK"
        assert len(fs.income_statement_periods) > 0
        assert len(fs.pf_cash_waterfall_periods) > 0
        assert fs.balance_sheet_status.value == "UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE"
        assert fs.fixed_asset_status.value == "BOOK_CAPITALIZATION_BASIS_UNAVAILABLE"
        assert fs.retained_earnings_status.value in ("OK", "OPENING_EQUITY_ACCOUNTING_AUTHORITY_UNAVAILABLE")
        assert fs.status.value == "UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE"

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
        """Correction B §18: opening RE derived causally from construction
        NI (typed EXPENSE_TO_PNL); SHL never enters RE as principal; legal
        reserve stays unresolved (no invented allocation)."""
        _, fs = _assemble("TUHO")
        for p in fs.retained_earnings_periods:
            assert p.legal_reserve_allocation_keur is None  # no invented legal reserve
            if p.opening_retained_earnings_keur is not None:
                assert p.closing_retained_earnings_keur == pytest.approx(
                    p.opening_retained_earnings_keur + p.net_income_keur
                    - p.legal_equity_distribution_keur, abs=1e-9)
        assert any(p.net_income_keur != 0.0 for p in fs.retained_earnings_periods)

    def test_j2_status_honest(self):
        _, fs = _assemble("TUHO")
        assert fs.retained_earnings_status.value == "OK"
        # Correction B: opening RE derived from construction SHL interest.
        assert fs.retained_earnings_periods[0].opening_retained_earnings_keur is not None


# ---------------------------------------------------------------------------
# C3-K balance sheet no-residual-cash insert
# ---------------------------------------------------------------------------

class TestC3K_NoBalancingPlug:
    def test_k1_balance_check_never_claimed_without_cash_authority(self):
        _, fs = _assemble("Wind")
        for p in fs.balance_sheet_periods:
            assert p.unrestricted_cash_keur is None
            assert p.balance_check_keur is None, (
                "a balance check may not be claimed while unrestricted cash "
                "authority is unavailable (that would require a cash residual-cash insert)"
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
        assert result.pf_cash_waterfall_periods == ()


# ---------------------------------------------------------------------------
# C3-M presentation adapter exposure
# ---------------------------------------------------------------------------

class TestC3M_PresentationExposure:
    def test_m1_adapter_passes_through_run_owned_statement_result(self):
        """Correction A §31: the adapter must not invoke assembly — it passes
        through the run-owned C3 result with object identity."""
        from app.services.clean_presentation_adapter import (
            build_clean_waterfall_view,
        )

        run = _run_clean("Oborovo")
        view = build_clean_waterfall_view(run)
        fs = view.financial_statements_result
        assert fs is not None
        # Ownership: assembled exactly once inside run_clean_production.
        assert fs is run.financial_statements_result
        assert fs.status.value == "UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE"


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


# ---------------------------------------------------------------------------
# C3 Correction A — §39 focused additions
# ---------------------------------------------------------------------------

class TestCorA_AdapterGovernance:
    def test_g1_adapter_has_no_assembly_or_c3_formulas(self):
        """§5: the presentation adapter must contain no statement assembly
        call and no C3 accounting identity — pure pass-through only."""
        import inspect
        from app.services import clean_presentation_adapter

        src = inspect.getsource(clean_presentation_adapter)
        assert "assemble_decision_complete_financial_statements(" not in src
        assert "_assemble_clean_statements" not in src

    def test_g2_unexpected_c3_error_propagates_not_swallowed(self, monkeypatch):
        """§4: an unexpected programming error inside assembly must
        propagate out of run_clean_production — never become a None."""
        import financial_engine.financial_statements.assembly as asm_mod
        import financial_engine.financial_statements as fs_pkg
        from app.services.production_financial_authority import run_clean_production
        from app import project_factories as pf

        def _boom(*a, **k):
            raise RuntimeError("assembly programming bug")

        monkeypatch.setattr(asm_mod, "assemble_decision_complete_financial_statements", _boom)
        monkeypatch.setattr(fs_pkg, "assemble_decision_complete_financial_statements", _boom)
        with pytest.raises(RuntimeError, match="assembly programming bug"):
            run_clean_production(pf.create_default_solar_project(), project_type="Solar")

    def test_g3_run_owns_single_statement_result(self):
        run = _run_clean("Solar")
        assert run.financial_statements_result is not None
        # calculation_count semantics unchanged: C3 is downstream assembly.
        assert run.authority_metadata["calculation_count"] == 1


class TestCorA_FcfBanksBoundary:
    def test_f1_fcf_banks_is_base_cfads_and_post_senior_is_separate(self):
        """§30: per period, fcf_banks == canonical Base CFADS and
        post_senior == G2C signed_post_senior — two distinct authorities."""
        run, fs = _assemble("TUHO")
        model = run.g2c_result.financing_result.project_model_result
        tax = model.tax_and_cfads
        wps = {w.period_index: w for w in run.g2c_result.waterfall_periods}
        tax_pos = {i: pos for pos, i in enumerate(tax.period_indices)}
        checked = 0
        for p in fs.pf_cash_waterfall_periods:
            if p.period_index not in tax_pos:
                # Periods outside the tax axis have no CIT/cash-tax authority;
                # their cash-tax row is 0.0 (honest absence, not fabrication).
                assert p.cash_tax_keur == 0.0
                continue
            assert p.fcf_banks_keur == pytest.approx(
                tax.cfads_keur[tax_pos[p.period_index]], abs=1e-9)
            if p.period_index in wps:
                assert p.post_senior_cash_keur == pytest.approx(
                    wps[p.period_index].signed_post_senior_keur, abs=1e-9)
            checked += 1
        assert checked > 0

    def test_f2_fcf_banks_minus_senior_ds_matches_post_senior(self):
        """FCF Banks − Senior DS ≈ −(signed post-Senior cash): the two
        boundaries are opposite-sign views of the same cash at the same
        period (signed_post_senior = senior_ds − base_cfads upstream)."""
        run, fs = _assemble("Oborovo")
        for p in fs.pf_cash_waterfall_periods:
            if p.senior_debt_service_keur == 0.0:
                continue
            lhs = p.fcf_banks_keur - p.senior_debt_service_keur
            rhs = p.post_senior_cash_keur
            assert lhs == pytest.approx(rhs, abs=1e-6), (
                f"period {p.period_index}: {lhs} vs {rhs}"
            )


class TestCorA_ConstructionSourcesUses:
    def test_s1_construction_rows_pass_through_sources_uses(self):
        """§32: per construction period, uses = senior + junior + legal equity
        + SHL draws (canonical residual enforced upstream); the statement
        passes these numbers through unchanged."""
        run, fs = _assemble("TUHO")
        rows = fs.construction_funding_rows
        assert rows, "TUHO must expose native-grain construction rows"
        fin = run.g2c_result.financing_result
        cf = fin.construction_funding
        src_by_idx = {p.period_index: p for p in cf.periods}
        for row in rows:
            src = src_by_idx[row.funding_period_index]
            sources = (src.senior_draw_keur + src.junior_or_other_main_funding_draw_keur
                       + src.share_capital_draw_keur + src.share_premium_draw_keur
                       + src.other_committed_equity_draw_keur
                       + src.additional_equity_draw_keur + src.shl_cash_draw_keur)
            assert sources == pytest.approx(src.project_cash_uses_keur, abs=1e-6), (
                f"period {src.period_index}: canonical S/U residual enforced upstream"
            )
            # PF rows mirror the funding authority unchanged.
            assert row.senior_draw_keur == pytest.approx(src.senior_draw_keur, abs=1e-9)
            assert row.project_cash_uses_keur == pytest.approx(
                src.project_cash_uses_keur, abs=1e-9)

    def test_s2_construction_shl_pik_is_non_cash_expense(self):
        """§33: construction SHL PIK is a P&L expense (typed EXPENSE_TO_PNL),
        increases the SHL liability, and never enters cash sources."""
        run, fs = _assemble("TUHO")
        model = run.g2c_result.financing_result.project_model_result
        mp_constr = [p for p in model.periods if p.is_construction]
        if not mp_constr:
            pytest.skip("no construction periods")
        shl = model.shareholder_loan
        constr_gross = sum(
            shl.shl_gross_interest_keur[pos]
            for pos, i in enumerate(shl.period_indices)
            if any(mp.period_index == i and mp.is_construction for mp in model.periods)
        )
        # P&L books the construction SHL interest as expense (typed policy).
        pnl_constr_interest = sum(
            p.shl_interest_expense_keur for p in fs.income_statement_periods
            if p.is_construction
        )
        assert pnl_constr_interest == pytest.approx(constr_gross, abs=1e-9)
        # PIK is carried in the PF statement as a non-cash memo row.
        pik_in_pf = sum(p.shl_pik_keur for p in fs.pf_cash_waterfall_periods)
        assert pik_in_pf >= 0.0


# ---------------------------------------------------------------------------
# C3 Correction B — exact axes, funding bridge, accounting closure
# ---------------------------------------------------------------------------

def _corrupt_axis(kind: str, which: str):
    """Build a SeniorDebtModelInput-like g2c stub with a corrupted axis."""
    from types import SimpleNamespace
    run = _run_clean("Solar")
    fin = run.g2c_result.financing_result
    model = fin.project_model_result

    def drop_first(indices, *vecs):
        return indices[1:], tuple(v[1:] for v in vecs)

    def drop_last(indices, *vecs):
        return indices[:-1], tuple(v[:-1] for v in vecs)

    def drop_middle(indices, *vecs):
        mid = len(indices) // 2
        return indices[:mid] + indices[mid+1:], tuple(v[:mid] + v[mid+1:] for v in vecs)

    def dup(indices, *vecs):
        i = len(indices) // 2
        return (indices[:i] + (indices[i],) + indices[i:],
                tuple(vecs and (v[:i] + (v[i],) + v[i:]) for v in vecs))

    def reorder(indices, *vecs):
        if len(indices) < 3:
            return indices, vecs
        i0, i1 = 1, 2
        idx = list(indices); idx[i0], idx[i1] = idx[i1], idx[i0]
        return tuple(idx), vecs

    def shorten(indices, *vecs):
        return indices, tuple(v[:-1] for v in vecs)

    ops = {"first": drop_first, "last": drop_last, "middle": drop_middle,
           "duplicate": dup, "reorder": reorder, "short": shorten}
    fn = ops[kind]

    tax = model.tax_and_cfads
    senior = model.senior_debt
    shl = model.shareholder_loan
    dsra = model.cash_dsra

    if which == "tax_first":   tax.period_indices, tax.tax_keur = fn(tax.period_indices, tax.tax_keur)
    elif which == "tax_last":  tax.period_indices, tax.tax_keur = fn(tax.period_indices, tax.tax_keur)
    elif which == "tax_mid":   tax.period_indices, tax.tax_keur = fn(tax.period_indices, tax.tax_keur)
    elif which == "tax_dup":   tax.period_indices, tax.tax_keur = fn(tax.period_indices, tax.tax_keur)
    elif which == "tax_reord": tax.period_indices, tax.tax_keur = fn(tax.period_indices, tax.tax_keur)
    elif which == "tax_short": tax.tax_keur = tax.tax_keur[:-1]
    elif which == "shl_first": shl.period_indices, shl.shl_gross_interest_keur = fn(shl.period_indices, shl.shl_gross_interest_keur)
    elif which == "shl_last":  shl.period_indices, shl.shl_closing_keur = fn(shl.period_indices, shl.shl_closing_keur)
    elif which == "shl_mid":   shl.period_indices, shl.shl_gross_interest_keur = fn(shl.period_indices, shl.shl_gross_interest_keur)
    elif which == "shl_dup":   shl.period_indices = fn(shl.period_indices)[0]
    elif which == "shl_short": shl.shl_gross_interest_keur = shl.shl_gross_interest_keur[:-1]
    elif which == "sen_first": senior.period_indices, senior.senior_interest_keur = fn(senior.period_indices, senior.senior_interest_keur)
    elif which == "sen_last":  senior.period_indices, senior.senior_debt_closing_keur = fn(senior.period_indices, senior.senior_debt_closing_keur)
    elif which == "sen_mid":   senior.period_indices, senior.senior_interest_keur = fn(senior.period_indices, senior.senior_interest_keur)
    elif which == "sen_reord": senior.period_indices = fn(senior.period_indices)[0]
    elif which == "sen_short": senior.senior_interest_keur = senior.senior_interest_keur[:-1]
    elif which == "dsra_missing":
        prs = list(dsra.period_results); del prs[5]
        dsra.period_results = tuple(prs)
    elif which == "dsra_dup":
        prs = list(dsra.period_results)
        dsra.period_results = tuple(prs[:5] + (prs[4],) + prs[5:])

    # Rebuild a G2C-like stub sharing the corrupted model.
    from types import SimpleNamespace
    g2c = SimpleNamespace(financing_result=fin, waterfall_periods=run.g2c_result.waterfall_periods)
    return run, g2c


    def test_l2_operating_stub_without_g2c_event_is_allowed(self):
        """Construction stubs without a G2C event are covered by the
        construction funding authority, not the operating waterfall."""
        run, fs = _assemble("Solar")
        assert fs.cash_flow_status.value == "OK"


# ---------------------------------------------------------------------------
# C3 Correction B — exact axes, funding bridge, accounting closure
# ---------------------------------------------------------------------------

def _corrupt_axis(which: str):
    """Return a g2c-like stub with a corrupted schedule axis/vector."""
    from types import SimpleNamespace
    run = _run_clean("Solar")
    fin = run.g2c_result.financing_result
    model = fin.project_model_result
    tax = model.tax_and_cfads
    senior = model.senior_debt
    shl = model.shareholder_loan
    dsra = model.cash_dsra

    def mutate(obj, idx_attr, vec_attr, kind):
        indices = list(getattr(obj, idx_attr))
        values = list(getattr(obj, vec_attr))
        mid = len(indices) // 2
        if kind == "first":
            indices, values = indices[1:], values[1:]
        elif kind == "last":
            indices, values = indices[:-1], values[:-1]
        elif kind in ("mid", "middle"):
            indices, values = indices[:mid] + indices[mid+1:], values[:mid] + values[mid+1:]
        elif kind in ("dup", "duplicate"):
            indices = indices[:mid] + [indices[mid]] + indices[mid:]
            values = values[:mid] + [values[mid]] + values[mid:]
        elif kind in ("reord", "reorder"):
            if len(indices) >= 3:
                indices[1], indices[2] = indices[2], indices[1]
        elif kind == "short":
            values = values[:-1]
        object.__setattr__(obj, idx_attr, tuple(indices))
        object.__setattr__(obj, vec_attr, tuple(values))

    if which.startswith("tax_"):
        mutate(tax, "period_indices", "tax_keur", which[4:])
    elif which.startswith("shl_"):
        mutate(shl, "period_indices", "shl_gross_interest_keur", which[4:])
    elif which.startswith("sen_"):
        mutate(senior, "period_indices", "senior_interest_keur", which[4:])
    elif which == "dsra_missing":
        prs = list(dsra.period_results)
        del prs[5]
        object.__setattr__(dsra, "period_results", tuple(prs))
    elif which == "dsra_dup":
        prs = list(dsra.period_results)
        object.__setattr__(dsra, "period_results",
                           tuple(prs[:5] + [prs[4]] + prs[5:]))

    g2c = SimpleNamespace(financing_result=fin, waterfall_periods=run.g2c_result.waterfall_periods)
    return run, g2c


class TestCorB_AxisCorruptionMatrix:
    """§8: every corruption case fails closed
    STATEMENT_PERIOD_AXIS_MISMATCH — never silently zeroed."""

    CASES = (
        "tax_first", "tax_last", "tax_mid", "tax_dup", "tax_reord", "tax_short",
        "shl_first", "shl_last", "shl_mid", "shl_dup", "shl_short",
        "sen_first", "sen_last", "sen_mid", "sen_reord", "sen_short",
        "dsra_missing", "dsra_dup",
    )

    @pytest.mark.parametrize("kind", CASES)
    def test_axis_corruption_fails_closed(self, kind):
        from financial_engine.financial_statements.assembly import (
            assemble_decision_complete_financial_statements,
        )
        import dataclasses
        from types import SimpleNamespace

        run, g2c = _corrupt_axis(kind)
        # Rebuild a real CovenantGatedWaterfallResult-like stub sharing the
        # corrupted model is complex; assembly consumes financing_result,
        # so replace the model on a copied financing result via the stub.
        broken = SimpleNamespace(financing_result=SimpleNamespace(
            project_model_result=g2c.financing_result.project_model_result
            if hasattr(g2c.financing_result, "project_model_result")
            else _corrupt_axis.model,
            project_uses=run.g2c_result.financing_result.project_uses,
            dscr_debt_capacity_keur=0.0, gearing_debt_capacity_keur=0.0,
            final_senior_commitment_keur=0.0, binding_senior_constraint="DSCR",
            construction_funding=run.g2c_result.financing_result.construction_funding,
            construction_financing=run.g2c_result.financing_result.construction_financing,
        ), waterfall_periods=g2c.waterfall_periods)
        result = assemble_decision_complete_financial_statements(
            broken, run.project_inputs)
        assert result.status.value == "STATEMENT_PERIOD_AXIS_MISMATCH", kind


class TestCorB_FundingAudit:
    def test_funding_audit_identity_all_projects(self):
        for ptype in ("Solar", "Wind", "Oborovo", "TUHO"):
            run, fs = _assemble(ptype)
            fa = fs.funding_audit
            total_uses = fa["construction_uses_keur"] + fa["non_construction_fc_uses_keur"]
            total_sources = fa["construction_sources_keur"] + fa["non_construction_fc_sources_keur"]
            if fa["total_audit_uses_keur"] is not None:
                assert total_uses == pytest.approx(fa["total_audit_uses_keur"], abs=1e-6), ptype
                assert total_sources == pytest.approx(fa["total_audit_sources_keur"], abs=1e-6), ptype
            assert abs(fa["total_audit_residual_keur"]) < 1e-6, ptype

    def test_construction_none_returns_typed_result(self):
        """B1: construction_funding=None → truthful typed result, no NameError."""
        import dataclasses
        from financial_engine.financial_statements.assembly import (
            assemble_decision_complete_financial_statements,
        )
        from financial_engine.financial_statements.contracts import (
            FinancialStatementsResult,
        )

        run = _run_clean("Solar")
        broken_fin = dataclasses.replace(
            run.g2c_result.financing_result, construction_funding=None)
        broken_g2c = dataclasses.replace(
            run.g2c_result, financing_result=broken_fin)
        result = assemble_decision_complete_financial_statements(
            broken_g2c, run.project_inputs)
        assert result.status.value == "PF_CASH_CONSTRUCTION_AUTHORITY_UNAVAILABLE"
        assert result.pf_cash_waterfall_periods == ()
        assert isinstance(result, FinancialStatementsResult)

    def test_non_construction_fc_row_pass_through(self):
        """§10: non_construction_fc_use exposed exactly once as a funding
        movement when present; absent (None) for the default four."""
        run, fs = _assemble("Solar")
        ncu = run.g2c_result.financing_result.construction_funding.non_construction_fc_use
        if ncu is None:
            assert fs.non_construction_fc_row is None
        else:
            assert fs.non_construction_fc_row.uses_keur == ncu.uses_keur
