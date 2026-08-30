"""financial_engine.financial_statements.assembly — Phase C3 statement assembly.

Clean sources → statement assembly → presentation. STRICTLY DOWNSTREAM:
consumes only already-authoritative clean-engine results attached to the
G2C result; performs roll-forwards and identity checks; never recomputes
tax, debt, SHL or distributions; never feeds back into the engine.

Canonical axis: the model period grid (model.periods). G2C waterfall
periods live on their own 1-based construction+operating axis and are
joined by cashflow_date == period_end (date join, validated — mismatch
fails closed with STATEMENT_PERIOD_AXIS_MISMATCH).

Axis validation contract (Correction A): every consumed schedule axis
(tax, Senior, SHL, DSRA) must be a duplicate-free, gap-free contiguous run
of model period indices; schedules may END early (SHL ends at payoff,
Senior at maturity) — later model periods carry the terminal balance
forward causally. Gaps, duplicates, extra indices or a wrong start fail
closed. No decorative governance flags.

PF cash boundaries (Correction A):
  fcf_banks_keur        = canonical Base CFADS (TaxAndCfadsSchedules.cfads_keur)
  post_senior_cash_keur = G2C signed_post_senior_keur (DIFFERENT R84-style
                          boundary) — exposed as separate lines; identity
                          fcf_banks − senior_debt_service = post_senior_cash
                          proved per period by the C3 suite.
  Construction financing cash rows come from the typed
  ConstructionFundingResult authority joined on the construction axis's
  OWN canonical dates — never silently zeroed; an unmapped construction
  date fails closed.
"""
from __future__ import annotations

from datetime import date

from financial_engine.financial_statements.contracts import (
    AccountingPolicies,
    BalanceSheetPeriod,
    FixedAssetRollForwardPeriod,
    FinancialStatementsResult,
    IncomeStatementPeriod,
    LineAuthority,
    PFCashWaterfallPeriod,
    RetainedEarningsPeriod,
    StatementStatus,
    TaxBridgePeriod,
)

_TOLERANCE_KEUR = 1e-6


def _at(vector, position: int):
    try:
        value = vector[position]
    except (IndexError, TypeError, KeyError):
        return None
    return None if value is None else float(value)


def _is_finite(value) -> bool:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return False
    return f == f and abs(f) != float("inf")


class _AxisMismatch(ValueError):
    def __init__(self, detail: str):
        super().__init__(f"STATEMENT_PERIOD_AXIS_MISMATCH: {detail}")
        self.detail = detail


class _TypedUnavailable(ValueError):
    """Internal fail-closed signal carrying its own statement status."""

    def __init__(self, status, detail: str):
        super().__init__(f"{status.value}: {detail}")
        self.status = status
        self.detail = detail


def _expected_axis_contract(model_periods, project_inputs):
    """Build the PR-F1 CanonicalAxisContract from the canonical model periods
    and the production Senior policy (Correction B §5-§6: reuse the existing
    axis authority; never self-author a weaker C3 axis definition)."""
    from finco_core.engine.axis_contract import CanonicalAxisContract
    from financial_engine.senior_debt.project_adapter import (
        build_senior_debt_contract_from_project_inputs,
    )
    try:
        senior_policy, _ = build_senior_debt_contract_from_project_inputs(
            project_inputs, tuple(model_periods)
        )
    except Exception as exc:
        raise _AxisMismatch(
            f"senior policy reconstruction failed: {type(exc).__name__}: {exc}"
        ) from exc
    return CanonicalAxisContract.from_periods_and_policy(
        tuple(model_periods), senior_policy
    )


def _mapped_axis(name: str, period_indices, values, expected_indices) -> dict[int, float]:
    """Map an axis-aligned vector through the canonical PR-F1
    map_period_vector authority (exact expected indices + parallel-vector
    length enforcement). _AxisMismatch conversion happens at the caller."""
    from finco_core.engine.period_engine import map_period_vector
    return map_period_vector(
        period_indices, values, label=name, expected_indices=expected_indices
    )


def _fail_closed(status: StatementStatus, detail: str) -> FinancialStatementsResult:
    return FinancialStatementsResult(
        status=status,
        project_inputs_summary={},
        income_statement_status=status,
        income_statement_periods=(),
        tax_bridge_status=status,
        tax_bridge_periods=(),
        terminal_unpaid_tax_keur=None,
        cash_flow_status=status,
        pf_cash_waterfall_periods=(),
        fixed_asset_status=status,
        fixed_asset_periods=(),
        retained_earnings_status=status,
        retained_earnings_periods=(),
        balance_sheet_status=status,
        balance_sheet_periods=(),
        accounting_policies=AccountingPolicies(),
        unavailable_reasons={"detail": detail},
    )


def assemble_decision_complete_financial_statements(
    g2c_result,
    project_inputs=None,
) -> FinancialStatementsResult:
    """Public entry — converts internal _AxisMismatch into a typed
    STATEMENT_PERIOD_AXIS_MISMATCH result (fail closed, nothing zeroed)."""
    try:
        return _assemble_statements_checked(g2c_result, project_inputs)
    except _TypedUnavailable as exc:
        return _fail_closed(exc.status, exc.detail)
    except _AxisMismatch as exc:
        return _fail_closed(StatementStatus.STATEMENT_PERIOD_AXIS_MISMATCH, exc.detail)
    except ValueError as exc:
        # Raw AXIS_* errors from the canonical map_period_vector authority
        # are converted to the same typed fail-closed result.
        return _fail_closed(StatementStatus.STATEMENT_PERIOD_AXIS_MISMATCH, str(exc))


def _assemble_statements_checked(g2c_result, project_inputs):
    fin = g2c_result.financing_result
    model = fin.project_model_result
    op = model.operating_schedules
    tax = model.tax_and_cfads
    senior = model.senior_debt
    shl = model.shareholder_loan
    dsra = getattr(model, "cash_dsra", None)
    wps = g2c_result.waterfall_periods

    # B1 fix: blocker-reasons registry initialized before any branch can
    # write to it (construction-None previously wrote before init).
    unavailable: dict[str, str] = {}

    model_periods = list(model.periods)
    model_indices = [p.period_index for p in model_periods]

    # Correction B §5-§7: exact canonical axes from the PR-F1 authority plus
    # parallel-vector length enforcement through map_period_vector. No
    # weaker independent C3 axis definition, no raw dict(zip(...)).
    contract = _expected_axis_contract(model_periods, project_inputs)
    from finco_core.engine.period_engine import map_period_vector

    # Validation pass: each consumed vector must match its canonical axis
    # exactly (indices AND length) — map_period_vector raises otherwise.
    map_period_vector(
        op.period_indices, op.revenue_keur,
        label="operating", expected_indices=contract.full_axis)
    map_period_vector(
        tax.period_indices, tax.taxable_profit_keur,
        label="tax", expected_indices=contract.full_axis)
    map_period_vector(
        shl.period_indices, shl.shl_gross_interest_keur,
        label="shl", expected_indices=contract.full_axis)
    senior_expected = contract.senior_axis or tuple(senior.period_indices)
    map_period_vector(
        senior.period_indices, senior.senior_interest_keur,
        label="senior", expected_indices=senior_expected)
    if dsra is not None:
        map_period_vector(
            [pr.period_index for pr in dsra.period_results],
            [pr.closing_balance_keur for pr in dsra.period_results],
            label="dsra", expected_indices=contract.full_axis)

    # Position maps for O(1) access (validated above).
    op_pos = {i: pos for pos, i in enumerate(op.period_indices)}
    tax_pos = {i: pos for pos, i in enumerate(tax.period_indices)}
    shl_pos = {i: pos for pos, i in enumerate(shl.period_indices)}
    senior_pos = {i: pos for pos, i in enumerate(senior.period_indices)}
    dsra_pos: dict[int, int] = {}
    if dsra is not None:
        map_period_vector(
            [pr.period_index for pr in dsra.period_results],
            [pr.closing_balance_keur for pr in dsra.period_results],
            label="dsra", expected_indices=contract.full_axis)
        dsra_pos = {pr.period_index: pos for pos, pr in enumerate(dsra.period_results)}

    for label, vec in (
        ("senior.principal", senior.senior_principal_keur),
        ("senior.ds", senior.senior_debt_service_keur),
        ("senior.closing", senior.senior_debt_closing_keur),
        ("shl.principal", shl.shl_principal_keur),
        ("shl.closing", shl.shl_closing_keur),
        ("tax.cit_accrual", tax.tax_keur),
        ("tax.cash", tax.corporate_tax_cash_keur),
    ):
        map_period_vector(
            senior.period_indices if label.startswith("senior") else (
                shl.period_indices if label.startswith("shl") else tax.period_indices),
            vec, label=label, expected_indices=(
                contract.senior_axis or tuple(senior.period_indices))
            if label.startswith("senior") else contract.full_axis)

    # G2C waterfall date join with duplicate/missing detection.
    wp_by_date: dict = {}
    for w in wps:
        d = getattr(w, "cashflow_date", None)
        if d is None:
            raise _AxisMismatch("G2C waterfall period without a cashflow date")
        if d in wp_by_date:
            raise _AxisMismatch(f"G2C waterfall has a duplicate cashflow date: {d}")
        wp_by_date[d] = w
    # Every OPERATING model period must have a dated G2C counterpart.
    # Construction stubs without a G2C event are allowed: their cash
    # movements are covered by the construction funding authority (joined
    # on construction's own dates below), not by the operating waterfall.
    unmatched_operating = [
        p.period_index for p in model_periods
        if getattr(p, "is_operation", False)
        and getattr(p, "period_end", None) not in wp_by_date
    ]
    if unmatched_operating:
        raise _AxisMismatch(
            "operating model periods without a dated G2C waterfall "
            f"counterpart: {unmatched_operating[:10]}"
        )

    # Phase C3 Correction A: construction financing is exposed at its OWN
    # native grain as a separate statement section (typed
    # ConstructionFundingResult authority, pass-through — no re-allocation
    # onto the model grid, no silent zeroing). Operating PF rows carry no
    # construction fields; the construction section carries all
    # construction uses/sources. PF cash is therefore complete: the
    # operating waterfall AND the construction section are both
    # authoritative.
    construction_rows: list = []
    construction_grain = "native_construction_axis"
    non_construction_fc_row = None
    funding_audit: dict = {}
    cfr = getattr(fin, "construction_funding", None)
    if cfr is None:
        # B1: truthful typed fail-closed result — no NameError, no silent
        # None, no fabricated zero construction cash.
        raise _TypedUnavailable(
            StatementStatus.PF_CASH_CONSTRUCTION_AUTHORITY_UNAVAILABLE,
            "no construction funding authority is attached to this run; "
            "the PF statement cannot claim a complete sources/uses bridge "
            "without it.",
        )
    from financial_engine.financial_statements.contracts import (
        ConstructionFundingStatementRow,
    )
    for cp in getattr(cfr, "periods", ()) or ():
        construction_rows.append(ConstructionFundingStatementRow(
            funding_period_index=cp.period_index,
            period_start=getattr(cp, "period_start", None),
            period_end=getattr(cp, "period_end", None),
            cashflow_date=getattr(cp, "cashflow_date", None),
            project_cash_uses_keur=float(getattr(cp, "project_cash_uses_keur", 0.0) or 0.0),
            senior_draw_keur=float(getattr(cp, "senior_draw_keur", 0.0) or 0.0),
            junior_or_other_funding_draw_keur=float(
                getattr(cp, "junior_or_other_main_funding_draw_keur", 0.0) or 0.0),
            share_capital_draw_keur=float(getattr(cp, "share_capital_draw_keur", 0.0) or 0.0),
            share_premium_draw_keur=float(getattr(cp, "share_premium_draw_keur", 0.0) or 0.0),
            other_committed_equity_draw_keur=float(
                getattr(cp, "other_committed_equity_draw_keur", 0.0) or 0.0),
            additional_equity_draw_keur=float(
                getattr(cp, "additional_equity_draw_keur", 0.0) or 0.0),
            shl_cash_draw_keur=float(getattr(cp, "shl_cash_draw_keur", 0.0) or 0.0),
            total_sponsor_cash_draw_keur=float(
                getattr(cp, "total_sponsor_cash_draw_keur", 0.0) or 0.0),
            total_sources_keur=float(getattr(cp, "total_sources_keur", 0.0) or 0.0),
            sources_uses_difference_keur=float(
                getattr(cp, "sources_uses_difference_keur", 0.0) or 0.0),
        ))

    # Correction B §10/§12: non-construction FC/COD funding use exposed
    # exactly once as a funding movement; funding audit identity proven:
    #   construction uses + FC/COD uses == total_audit_uses
    #   construction sources + FC/COD sources == total_audit_sources
    #   total residual ≈ 0
    non_construction_fc_row = None
    total_constr_uses = sum(r.project_cash_uses_keur for r in construction_rows)
    total_constr_sources = sum(r.total_sources_keur for r in construction_rows)
    ncu = getattr(cfr, "non_construction_fc_use", None) if cfr is not None else None
    if ncu is not None:
        from financial_engine.financial_statements.contracts import (
            NonConstructionFcFundingStatementRow,
        )
        non_construction_fc_row = NonConstructionFcFundingStatementRow(
            kind="FC_COD",
            policy=ncu.policy,
            uses_keur=ncu.uses_keur,
            senior_draw_keur=ncu.senior_draw_keur,
            shl_draw_keur=ncu.shl_draw_keur,
            junior_draw_keur=ncu.junior_draw_keur,
            share_capital_draw_keur=ncu.share_capital_draw_keur,
            share_premium_draw_keur=ncu.share_premium_draw_keur,
            other_committed_equity_draw_keur=ncu.other_committed_equity_draw_keur,
            additional_equity_draw_keur=ncu.additional_equity_draw_keur,
            total_sources_keur=ncu.total_sources_keur,
        )
    funding_audit = {
        "construction_uses_keur": total_constr_uses,
        "construction_sources_keur": total_constr_sources,
        "non_construction_fc_uses_keur": getattr(ncu, "uses_keur", 0.0) or 0.0,
        "non_construction_fc_sources_keur": getattr(ncu, "total_sources_keur", 0.0) or 0.0,
        "total_audit_uses_keur": getattr(cfr, "total_audit_uses_keur", None)
        if cfr is not None else None,
        "total_audit_sources_keur": getattr(cfr, "total_audit_sources_keur", None)
        if cfr is not None else None,
        "total_audit_residual_keur": getattr(cfr, "total_audit_residual_keur", None)
        if cfr is not None else None,
    }

    pnl_periods: list[IncomeStatementPeriod] = []
    tax_periods: list[TaxBridgePeriod] = []
    pf_periods: list[PFCashWaterfallPeriod] = []
    fa_periods: list[FixedAssetRollForwardPeriod] = []
    re_periods: list[RetainedEarningsPeriod] = []
    bs_periods: list[BalanceSheetPeriod] = []

    cumulative_book_dep = 0.0
    cumulative_share_capital = 0.0
    cumulative_share_premium = 0.0
    non_finite = False

    # Correction B §18: causal opening retained earnings at COD from typed
    # construction accounting. Construction-period NI is complete when the
    # typed SHL construction accounting is EXPENSE_TO_PNL (source-proven
    # for TUHO/Oborovo): NI = -SHL gross interest (EBITDA/book dep zero
    # rows, CIT accrual 0 on the construction loss).
    tax_pol = getattr(project_inputs, "tax", None) if project_inputs is not None else None
    treatment_value = getattr(
        getattr(tax_pol, "shl_construction_accounting", None), "value", None)
    if treatment_value == "expense_to_pnl":
        opening_re_at_cod = -sum(
            (float(g) if g is not None else 0.0)
            for g, mp in zip(shl.shl_gross_interest_keur, model.periods)
            if getattr(mp, "is_construction", False)
        )
        opening_re_status = StatementStatus.OK
    else:
        opening_re_at_cod = None
        opening_re_status = (
            StatementStatus.OPENING_EQUITY_ACCOUNTING_AUTHORITY_UNAVAILABLE
        )
    unavailable["opening_retained_earnings"] = (
        "SOURCE_PROVEN (typed EXPENSE_TO_PNL): construction SHL gross "
        "interest expensed through P&L creates the pre-COD retained loss."
        if opening_re_at_cod is not None else
        "OPENING_EQUITY_ACCOUNTING_AUTHORITY_UNAVAILABLE: the typed SHL "
        "construction accounting treatment is not EXPENSE_TO_PNL; no causal "
        "construction-P&L authority to derive opening RE."
    )
    opening_re = opening_re_at_cod
    dsra_by_idx = (
        {pr.period_index: pr for pr in dsra.period_results} if dsra is not None else {}
    )

    for mp in model_periods:
        idx = mp.period_index
        oi = op_pos.get(idx)
        ti = tax_pos.get(idx)
        si = senior_pos.get(idx)
        shi = shl_pos.get(idx)
        wp = wp_by_date.get(getattr(mp, "period_end", None))
        dpr = dsra_by_idx.get(idx)

        revenue = float(getattr(mp, "revenue_keur", 0.0) or 0.0)
        opex = float(getattr(mp, "opex_keur", 0.0) or 0.0)
        ebitda = float(getattr(mp, "ebitda_keur", 0.0) or 0.0)
        book_dep = float(getattr(mp, "book_depreciation_keur", 0.0) or 0.0)
        ebit = float(getattr(mp, "ebit_keur", 0.0) or 0.0)

        senior_int = _at(senior.senior_interest_keur, si) if si is not None else 0.0
        senior_int = senior_int or 0.0
        # P&L SHL interest = gross accrued (cash + PIK) — never cash-only.
        shl_gross = _at(shl.shl_gross_interest_keur, shi) if shi is not None else 0.0
        shl_gross = shl_gross or 0.0
        net_financial = -(senior_int + shl_gross)
        ebt = ebit + net_financial
        cit_accrual = _at(tax.tax_keur, ti) if ti is not None else 0.0
        cit_accrual = cit_accrual or 0.0
        net_income = ebt - cit_accrual

        for v in (revenue, opex, ebitda, book_dep, ebit, senior_int, shl_gross,
                  ebt, cit_accrual, net_income):
            if not _is_finite(v):
                non_finite = True

        pnl_periods.append(IncomeStatementPeriod(
            period_index=int(idx),
            period_start=getattr(mp, "period_start", None),
            period_end=getattr(mp, "period_end", None),
            is_construction=bool(getattr(mp, "is_construction", False)),
            revenue_keur=revenue,
            opex_keur=opex,
            ebitda_keur=ebitda,
            book_depreciation_keur=book_dep,
            ebit_keur=ebit,
            senior_interest_expense_keur=senior_int,
            shl_interest_expense_keur=shl_gross,
            net_financial_result_keur=net_financial,
            earnings_before_tax_keur=ebt,
            cit_accrual_keur=cit_accrual,
            net_income_keur=net_income,
            authority={
                "revenue": LineAuthority.EXISTING_CLEAN_AUTHORITY.value,
                "opex": LineAuthority.EXISTING_CLEAN_AUTHORITY.value,
                "ebitda": LineAuthority.EXISTING_CLEAN_AUTHORITY.value,
                "book_depreciation": LineAuthority.EXISTING_CLEAN_AUTHORITY.value,
                "senior_interest": LineAuthority.EXISTING_CLEAN_AUTHORITY.value,
                "shl_interest": LineAuthority.EXISTING_CLEAN_AUTHORITY.value,
                "cit_accrual": LineAuthority.EXISTING_CLEAN_AUTHORITY.value,
                "ebit_ebt_net_income": LineAuthority.DERIVED_ACCOUNTING_ROLL_FORWARD.value,
            },
        ))

        tax_periods.append(TaxBridgePeriod(
            period_index=int(idx),
            taxable_income_before_losses_keur=_at(tax.taxable_income_before_losses_audit_keur, ti),
            taxable_profit_after_losses_keur=_at(tax.taxable_profit_after_losses_audit_keur, ti),
            fiscal_reintegration_keur=_at(tax.fiscal_reintegration_audit_keur, ti),
            tax_loss_opening_keur=_at(tax.tax_loss_opening_audit_keur, ti),
            tax_loss_used_keur=_at(tax.tax_loss_used_audit_keur, ti),
            tax_loss_closing_keur=_at(tax.tax_loss_closing_audit_keur, ti),
            tax_depreciation_keur=_at(tax.tax_depreciation_audit_keur, ti),
            cit_accrual_keur=_at(tax.cit_accrual_audit_keur, ti),
            cash_tax_current_period_keur=_at(tax.cash_tax_current_period_audit_keur, ti),
            corporate_tax_cash_keur=_at(tax.corporate_tax_cash_keur, ti),
            cash_tax_bridge_reconciliation_keur=_at(tax.cash_tax_bridge_reconciliation_keur, ti),
        ))

        wp = wp if wp is not None else type("EmptyWp", (), {})()  # attribute-safe empty
        # Correction A — PF cash boundaries:
        #   fcf_banks_keur        = canonical Base CFADS (tax vector);
        #   post_senior_cash_keur = G2C signed_post_senior_keur (R84-style
        #                           post-Senior boundary) — a DIFFERENT
        #                           concept, never used as FCF Banks.
        base_cfads = _at(tax.cfads_keur, ti) or 0.0
        post_senior = float(getattr(wp, "signed_post_senior_keur", 0.0) or 0.0)
        senior_ds = _at(senior.senior_debt_service_keur, si) or 0.0
        pf_periods.append(PFCashWaterfallPeriod(
            period_index=int(idx),
            cashflow_date=getattr(mp, "period_end", None),
            is_construction=bool(getattr(mp, "is_construction", False)),
            revenue_cash_keur=revenue,
            opex_cash_keur=opex,
            ebitda_keur=ebitda,
            cash_tax_keur=_at(tax.corporate_tax_cash_keur, ti) or 0.0,
            fcf_banks_keur=base_cfads,
            senior_debt_service_keur=senior_ds,
            post_senior_cash_keur=post_senior,
            senior_cash_interest_keur=senior_int,
            senior_principal_keur=_at(senior.senior_principal_keur, si) or 0.0,
            dsra_top_up_keur=float(getattr(wp, "dsra_top_up_keur", 0.0) or 0.0),
            dsra_draw_keur=float(getattr(wp, "dsra_draw_keur", 0.0) or 0.0),
            dsra_release_keur=float(getattr(wp, "dsra_release_keur", 0.0) or 0.0),
            distribution_account_inflow_keur=float(
                getattr(wp, "distribution_account_inflow_keur", 0.0) or 0.0),
            distribution_account_release_keur=float(
                getattr(wp, "distribution_account_release_keur", 0.0) or 0.0),
            distribution_account_closing_keur=float(
                getattr(wp, "distribution_account_closing_keur", 0.0) or 0.0),
            shl_cash_interest_keur=float(getattr(wp, "shl_cash_interest_receipt_keur", 0.0) or 0.0),
            shl_pik_keur=float(getattr(wp, "shl_pik_keur", 0.0) or 0.0),
            shl_principal_paid_keur=float(
                getattr(wp, "actual_shl_principal_paid_keur", 0.0) or 0.0),
            shl_unpaid_principal_keur=float(
                getattr(wp, "unpaid_shl_principal_keur", 0.0) or 0.0),
            legal_equity_distribution_keur=float(
                getattr(wp, "legal_equity_distribution_keur", 0.0) or 0.0),
        ))

        # Fixed assets: accumulated BOOK depreciation roll-forward is causal;
        # gross/NFA basis requires a book-capitalization authority that clean
        # results do not expose — truthfully unavailable.
        cumulative_book_dep += book_dep
        fa_periods.append(FixedAssetRollForwardPeriod(
            period_index=int(idx),
            period_end=getattr(mp, "period_end", None),
            book_depreciation_keur=book_dep,
            accumulated_book_depreciation_keur=cumulative_book_dep,
            gross_fixed_assets_keur=None,
            accumulated_depreciation_on_disposals_keur=0.0,
            net_fixed_assets_keur=None,
        ))

        # Retained earnings (Correction B §18): opening RE at COD is derived
        # causally from construction-period NI when the typed SHL
        # construction accounting is EXPENSE_TO_PNL (construction NI =
        # -SHL gross interest; EBITDA/book dep are zero rows, CIT accrual 0
        # on the loss). SHL is debt — never deducted from RE as principal.
        # Legal reserve stays UNRESOLVED (no generic authority).
        legal_dist = float(getattr(wp, "legal_equity_distribution_keur", 0.0) or 0.0)
        re_periods.append(RetainedEarningsPeriod(
            period_index=int(idx),
            period_end=getattr(mp, "period_end", None),
            opening_retained_earnings_keur=opening_re,
            net_income_keur=net_income,
            legal_equity_distribution_keur=legal_dist,
            legal_reserve_allocation_keur=None,
            closing_retained_earnings_keur=(
                None if opening_re is None
                else opening_re + net_income - legal_dist),
        ))
        if opening_re is not None:
            opening_re = opening_re + net_income - legal_dist

        # Balance sheet presentation: balances are clean closing authority;
        # unrestricted cash / gross FA / equity accounts are truthfully
        # unavailable → balance_check NOT claimed (no residual-cash insert).
        cumulative_share_capital += float(
            getattr(wp, "share_capital_contribution_keur", 0.0) or 0.0)
        cumulative_share_premium += float(
            getattr(wp, "share_premium_contribution_keur", 0.0) or 0.0)
        dsra_close = (
            float(dpr.closing_balance_keur) if dpr is not None else None
        )
        bs_periods.append(BalanceSheetPeriod(
            period_index=int(idx),
            period_end=getattr(mp, "period_end", None),
            senior_debt_balance_keur=_at(senior.senior_debt_closing_keur, si),
            shl_balance_keur=(
                float(getattr(wp, "actual_shl_closing_balance_keur", 0.0) or 0.0)
                if wp is not None else None
            ),
            shl_unpaid_principal_keur=(
                float(getattr(wp, "unpaid_shl_principal_keur", 0.0) or 0.0)
                if wp is not None else None
            ),
            distribution_account_balance_keur=(
                float(getattr(wp, "distribution_account_closing_keur", 0.0) or 0.0)
                if wp is not None else None
            ),
            dsra_balance_keur=dsra_close,
            unrestricted_cash_keur=None,
            gross_fixed_assets_keur=None,
            accumulated_book_depreciation_keur=cumulative_book_dep,
            share_capital_keur=cumulative_share_capital,
            share_premium_keur=cumulative_share_premium,
            retained_earnings_keur=None,
            balance_check_keur=None,
        ))

    if non_finite:
        overall = StatementStatus.NON_FINITE_RESULT
    else:
        # Honest partial availability (Correction B): PF cash is OK (the
        # construction bridge is mapped); P&L financing income and the
        # balance sheet remain honestly unavailable.
        overall = StatementStatus.UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE

    unavailable.update({
        "balance_sheet": (
            "UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE: closing unrestricted "
            "cash requires a causal unrestricted-cash roll-forward that the "
            "clean runtime does not yet provide; no residual-cash insert applied."
        ),
        "gross_fixed_assets": (
            "BOOK_CAPITALIZATION_BASIS_UNAVAILABLE: the book fixed-asset "
            "capitalization basis is not exposed on clean results; only the "
            "accumulated book depreciation roll-forward is causal."
        ),
        "opening_retained_earnings": (
            "OPENING_EQUITY_ACCOUNTING_AUTHORITY_UNAVAILABLE: construction-"
            "period equity accounting authority is not yet typed; the "
            "operating-period NI/distribution movements are shown with an "
            "explicitly unavailable opening."
        ),
        "tax_payable": (
            "TAX_PAYABLE_AUTHORITY_UNAVAILABLE: a CIT payable roll-forward "
            "is not part of the clean tax timing contract; terminal unpaid "
            "tax is surfaced directly."
        ),
        "financing_income": (
            "FINANCING_INCOME_AUTHORITY_UNAVAILABLE: interest on unrestricted "
            "cash / reserve balances has no clean authority; the P&L exposes "
            "all known lines but is not a complete financing result."
        ),
    })

    return FinancialStatementsResult(
        status=overall,
        project_inputs_summary={
            "model_period_count": len(model_periods),
            "waterfall_period_count": len(wps),
            "g2c_dscr_authority": senior.binding_constraint,
            "construction_rows_mapped": len(construction_rows),
        },
        # Correction A: financing income (interest on unrestricted cash /
        # reserve balances) has no clean authority — the P&L exposes all
        # known lines but is NOT a complete financing result.
        income_statement_status=StatementStatus.FINANCING_INCOME_AUTHORITY_UNAVAILABLE,
        income_statement_periods=tuple(pnl_periods),
        tax_bridge_status=StatementStatus.OK,
        tax_bridge_periods=tuple(tax_periods),
        terminal_unpaid_tax_keur=float(getattr(tax, "terminal_unpaid_tax_keur", 0.0) or 0.0),
        cash_flow_status=StatementStatus.OK,
        pf_cash_waterfall_periods=tuple(pf_periods),
        construction_funding_rows=tuple(construction_rows),
        construction_funding_grain=construction_grain,
        non_construction_fc_row=non_construction_fc_row,
        funding_audit=funding_audit,
        fixed_asset_status=StatementStatus.BOOK_CAPITALIZATION_BASIS_UNAVAILABLE,
        fixed_asset_periods=tuple(fa_periods),
        retained_earnings_status=opening_re_status,
        retained_earnings_periods=tuple(re_periods),
        balance_sheet_status=StatementStatus.UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE,
        balance_sheet_periods=tuple(bs_periods),
        accounting_policies=AccountingPolicies(provenance={
            "baseline": "clean-engine results only (no legacy statement modules)",
            "axis": "model.periods; G2C joined by cashflow_date == period_end",
        }),
        unavailable_reasons=unavailable,
        authority_labels={
            "pnl": LineAuthority.EXISTING_CLEAN_AUTHORITY.value,
            "tax_bridge": LineAuthority.EXISTING_CLEAN_AUTHORITY.value,
            "pf_cash_waterfall": LineAuthority.EXISTING_CLEAN_AUTHORITY.value,
            "accumulated_book_depreciation": (
                LineAuthority.DERIVED_ACCOUNTING_ROLL_FORWARD.value),
            "retained_earnings_movements": (
                LineAuthority.DERIVED_ACCOUNTING_ROLL_FORWARD.value),
            "gross_fixed_assets": LineAuthority.UNRESOLVED.value,
            "unrestricted_cash": LineAuthority.UNRESOLVED.value,
            "opening_retained_earnings": LineAuthority.UNRESOLVED.value,
        },
    )
