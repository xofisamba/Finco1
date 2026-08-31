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
    AccountingPolicyAuthority,
    BalanceSheetPeriod,
    BookCapitalizationTreatment,
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


def _axis_checked(name: str, period_indices, values, expected_indices):
    """Correction C §16: single dedicated axis-validation helper.

    Runs the canonical PR-F1 map_period_vector authority (exact expected
    indices + parallel-vector length enforcement) and converts ONLY the
    known canonical axis error codes (AXIS_* / PERIOD_VECTOR_*) into the
    internal _AxisMismatch signal. Any other ValueError is an unexpected
    defect and propagates unchanged."""
    from finco_core.engine.period_engine import map_period_vector
    try:
        return map_period_vector(
            period_indices, values, label=name, expected_indices=expected_indices
        )
    except ValueError as exc:
        msg = str(exc)
        if msg.startswith(("AXIS_PERIOD_", "PERIOD_VECTOR_")):
            raise _AxisMismatch(msg) from exc
        raise


def _map_opening_re_label(apc) -> str:
    """Map apc.opening_re_authority to the correct LineAuthority string."""
    auth = getattr(apc, "opening_re_authority", None)
    if auth is None:
        return LineAuthority.UNRESOLVED.value
    auth_val = getattr(auth, "value", str(auth))
    if auth_val == "SOURCE_PROVEN":
        return LineAuthority.SOURCE_PROVEN_CONFIGURATION.value
    elif auth_val == "USER_CONFIGURED":
        return LineAuthority.SOURCE_PROVEN_CONFIGURATION.value  # best available
    elif auth_val == "GENERIC_FINCO_POLICY":
        return LineAuthority.GENERIC_FINCO_ACCOUNTING_POLICY.value
    else:
        return LineAuthority.UNRESOLVED.value


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
    # Correction C §16: the public exception contract is NARROW — only
    # _TypedUnavailable and _AxisMismatch become typed fail-closed results.
    # Unexpected generic ValueError must propagate (no broad masking).


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

    # Validation pass: each consumed vector must match its canonical axis
    # exactly (indices AND length) — _axis_checked raises _AxisMismatch
    # otherwise and lets unexpected ValueErrors propagate.
    _axis_checked(
        "operating", op.period_indices, op.revenue_keur, contract.full_axis)
    _axis_checked(
        "tax", tax.period_indices, tax.taxable_profit_keur, contract.full_axis)
    _axis_checked(
        "shl", shl.period_indices, shl.shl_gross_interest_keur, contract.full_axis)
    # Correction D: remove self-authorization fallback.  The only valid
    # source for senior_expected is the independently-derived axis contract
    # (PR-F1 authority).  Falling back to tuple(senior.period_indices) would
    # validate the senior result against ITSELF — any axis defect in the
    # solver output would pass silently.  When contract.senior_axis is None
    # the project has no senior debt; the solver result must also be empty.
    if contract.senior_axis is None:
        if tuple(senior.period_indices):
            raise _AxisMismatch(
                "senior_axis absent from axis contract but senior result "
                f"carries {len(senior.period_indices)} period(s); axis "
                "contract must be rebuilt to include the senior policy."
            )
        senior_expected: tuple = ()
    else:
        senior_expected = contract.senior_axis
    _axis_checked(
        "senior", senior.period_indices, senior.senior_interest_keur,
        senior_expected)
    if dsra is not None:
        _axis_checked(
            "dsra",
            [pr.period_index for pr in dsra.period_results],
            [pr.closing_balance_keur for pr in dsra.period_results],
            contract.full_axis)

    # Position maps for O(1) access (validated above).
    op_pos = {i: pos for pos, i in enumerate(op.period_indices)}
    tax_pos = {i: pos for pos, i in enumerate(tax.period_indices)}
    shl_pos = {i: pos for pos, i in enumerate(shl.period_indices)}
    senior_pos = {i: pos for pos, i in enumerate(senior.period_indices)}
    dsra_pos: dict[int, int] = {}
    if dsra is not None:
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
        _axis_checked(
            label,
            senior.period_indices if label.startswith("senior") else (
                shl.period_indices if label.startswith("shl") else tax.period_indices),
            vec,
            senior_expected
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

    # Correction E: accounting provenance from typed config supplied by the
    # project factory.  Assembly never reads project identity (code, name,
    # country+code combination, or any whitelist) to derive accounting
    # behaviour.  When no config is provided the generic/unavailable defaults
    # apply — no implicit activation of source-proven policies.
    from financial_engine.financial_statements.contracts import (
        AccountingPolicyConfig as _APC,
    )
    _raw_apc = getattr(project_inputs, "accounting_policy_config", None) if project_inputs is not None else None
    _apc: _APC = _raw_apc if isinstance(_raw_apc, _APC) else _APC()

    # SHL construction accounting authority comes from typed config.
    if treatment_value == "expense_to_pnl":
        _shl_accounting_authority = _apc.shl_construction_accounting_authority
        if _shl_accounting_authority == AccountingPolicyAuthority.UNRESOLVED:
            _shl_accounting_authority = AccountingPolicyAuthority.GENERIC_FINCO_POLICY
    elif treatment_value is None:
        _shl_accounting_authority = AccountingPolicyAuthority.UNRESOLVED
    else:
        _shl_accounting_authority = AccountingPolicyAuthority.GENERIC_FINCO_POLICY

    _legal_reserve_authority = _apc.legal_reserve_authority
    _book_cap_authority = _apc.book_capitalization_authority
    _opening_re_pol_authority = _apc.opening_re_authority
    # Cash interest income has no clean authority regardless of project.
    _cash_interest_authority = AccountingPolicyAuthority.UNRESOLVED

    # GFA component classification: from typed config when present, otherwise generic.
    _book_cap_components = _apc.book_capitalization_components or {
        "hard_capex": BookCapitalizationTreatment.CAPITALIZE_FIXED_ASSET.value,
        "shl_construction_interest": BookCapitalizationTreatment.EXPENSE_PNL.value,
    }
    # Legal reserve: explicit typed activation only (§18 Correction E).
    _lr_policy = _apc.legal_reserve_policy
    # Correction C §4-§6 (Option B — operating-only RE schedule): the COD
    # opening RE is derived from the AUTHORITATIVE construction P&L
    # (pre-construction opening RE = 0 for a newly incorporated SPV whose
    # complete construction P&L starts at the first model period) and the
    # RE roll-forward begins ONLY at the first operating period. The same
    # construction loss is therefore counted exactly once — never seeded
    # into the opening AND re-applied during construction (Blocker C1).
    if treatment_value == "expense_to_pnl":
        opening_re_authority = True
        opening_re_status = StatementStatus.OK
    else:
        opening_re_authority = False
        opening_re_status = (
            StatementStatus.OPENING_EQUITY_ACCOUNTING_AUTHORITY_UNAVAILABLE
        )
    if not opening_re_authority:
        unavailable["opening_retained_earnings"] = (
            "OPENING_EQUITY_ACCOUNTING_AUTHORITY_UNAVAILABLE: the typed SHL "
            "construction accounting treatment is not EXPENSE_TO_PNL; no causal "
            "construction-P&L authority to derive opening RE."
        )
    # Correction D §11-§16: book GFA from causal construction financing
    # components.  ConstructionFinancingResult exposes per-period hard capex
    # and IDC/fee vectors for projects that ran a senior-debt construction
    # financing computation (Oborovo/TUHO).  Solar/Wind have
    # ConstructionFinancingResult=None so their GFA remains unavailable.
    # SHL construction PIK is EXCLUDED from GFA (it is expensed to P&L
    # under the EXPENSE_TO_PNL policy and never capitalized).  DSRA and
    # working capital are separate balance sheet accounts — not GFA.
    cfin = getattr(fin, "construction_financing", None)
    gfa_keur: float | None = None
    gfa_report: dict = {}
    _gfa_unavailable_msg: str | None = None
    if cfin is not None:
        _gfa_hard = sum(cfin.hard_capex_uses_keur)
        # Correction E §9-§10: use capitalized IDC (senior_idc_capitalized_uses_keur),
        # NOT raw accrual (senior_idc_accrual_keur).  Terminal raw IDC that is not a
        # capitalized project use is excluded from GFA.
        _gfa_idc_raw = sum(cfin.senior_idc_accrual_keur)
        _cap_idc_vec = cfin.senior_idc_capitalized_uses_keur
        _gfa_idc = sum(_cap_idc_vec) if _cap_idc_vec else _gfa_idc_raw
        _gfa_idc_terminal = _gfa_idc_raw - _gfa_idc
        _gfa_commit = sum(cfin.senior_commitment_fee_accrual_keur)
        _gfa_struct = sum(cfin.structuring_fee_keur)
        _gfa_vat_idc = float(cfin.vat_idc_keur or 0.0)
        _gfa_vat_commit = float(cfin.vat_commitment_fee_keur or 0.0)
        _total_cap_fin = float(getattr(cfin, "total_capitalized_financing_keur", 0.0) or 0.0)
        gfa_keur = (
            _gfa_hard + _gfa_idc + _gfa_commit
            + _gfa_struct + _gfa_vat_idc + _gfa_vat_commit
        )
        gfa_report = {
            "hard_capex_keur": _gfa_hard,
            "senior_idc_keur": _gfa_idc,
            "senior_idc_raw_keur": _gfa_idc_raw,
            "senior_idc_terminal_excluded_keur": _gfa_idc_terminal,
            "senior_commitment_fees_keur": _gfa_commit,
            "structuring_fee_keur": _gfa_struct,
            "vat_idc_keur": _gfa_vat_idc,
            "vat_commitment_fee_keur": _gfa_vat_commit,
            "total_capitalized_financing_keur": _total_cap_fin,
            "shl_construction_pik_excluded_keur": float(
                cfin.shl_construction_pik_keur or 0.0),
            "total_book_gfa_keur": gfa_keur,
        }
        # Correction F §21-§24: check if depreciation basis (from capex scalars)
        # is consistent with GFA (from construction_financing engine).
        # Gap applies only when capex scalars are 0 (not provided/calibrated) but
        # cfin computes non-zero financing costs — indicating the dep basis is
        # incomplete (TUHO case). When capex scalars are non-zero they are the
        # authoritative calibrated source; no gap flag in that case.
        _cap_inputs = getattr(project_inputs, "capex", None)
        _cap_financing_in_gfa = _gfa_idc + _gfa_commit + _gfa_struct + _gfa_vat_idc + _gfa_vat_commit
        _cap_financing_in_dep_basis = (
            float(getattr(_cap_inputs, "idc_keur", 0) or 0)
            + float(getattr(_cap_inputs, "commitment_fees_keur", 0) or 0)
            + float(getattr(_cap_inputs, "bank_fees_keur", 0) or 0)
            + float(getattr(_cap_inputs, "vat_costs_keur", 0) or 0)
        ) if _cap_inputs is not None else 0.0
        # Gap fires only when capex scalars are 0 but cfin has non-zero fin costs.
        _dep_basis_gap = (
            _cap_financing_in_dep_basis < 0.01
            and _cap_financing_in_gfa > 0.01
        )
        if _dep_basis_gap:
            gfa_report["candidate_book_gfa_keur"] = gfa_keur
            gfa_keur = None
            _gfa_unavailable_msg = (
                "BOOK_DEPRECIABLE_ASSET_BASIS_UPSTREAM_REQUIRED: GFA financing costs "
                "from construction_financing engine differ from "
                "capex.book_depreciable_capex_items() depreciation basis; upstream "
                "canonical BookDepreciableAssetBasis prerequisite required."
            )

    construction_ni_sum = 0.0
    cod_opening_re: float | None = None
    # Collect operating period data for post-loop RE/legal-reserve build.
    _op_re_inputs: list = []
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

        # Fixed assets: accumulated BOOK depreciation roll-forward is causal.
        # GFA is computed from ConstructionFinancingResult when available
        # (source-proven projects with a senior construction financing run);
        # NFA = GFA − cumulative book depreciation (no disposals during ops).
        cumulative_book_dep += book_dep
        _nfa = (gfa_keur - cumulative_book_dep) if gfa_keur is not None else None
        fa_periods.append(FixedAssetRollForwardPeriod(
            period_index=int(idx),
            period_end=getattr(mp, "period_end", None),
            book_depreciation_keur=book_dep,
            accumulated_book_depreciation_keur=cumulative_book_dep,
            gross_fixed_assets_keur=gfa_keur,
            accumulated_depreciation_on_disposals_keur=0.0,
            net_fixed_assets_keur=_nfa,
        ))

        # Retained earnings (Correction C §4-§6, Option B): construction
        # periods accumulate the COD opening balance (NI counted ONCE);
        # the RE roll-forward schedule is emitted for OPERATING periods
        # only, starting at the COD opening. Collect inputs for the
        # post-loop legal-reserve roll-forward (Correction D §19-§23).
        legal_dist = float(getattr(wp, "legal_equity_distribution_keur", 0.0) or 0.0)
        is_construction_period = bool(getattr(mp, "is_construction", False))
        if is_construction_period:
            if opening_re_authority:
                construction_ni_sum += net_income
        else:
            _op_re_inputs.append(
                (int(idx), net_income, legal_dist, getattr(mp, "period_end", None))
            )

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
            gross_fixed_assets_keur=gfa_keur,
            accumulated_book_depreciation_keur=cumulative_book_dep,
            share_capital_keur=cumulative_share_capital,
            share_premium_keur=cumulative_share_premium,
            retained_earnings_keur=None,
            balance_check_keur=None,
        ))

    # Correction D §19-§23: legal-reserve roll-forward using the existing
    # Correction E §18: legal reserve requires EXPLICIT typed activation via
    # LegalReservePolicy(enabled=True) in AccountingPolicyConfig.  A scalar
    # TaxParams.legal_reserve_cap default is not sufficient — it may reflect a
    # compatibility default rather than a proven source accounting policy.
    # The kernel: transfer = min(NI, cap − opening_reserve) when NI > 0 and
    # reserve < cap; otherwise 0.  RE closing = opening + NI − dist − transfer.
    cod_opening_re = construction_ni_sum if opening_re_authority else None
    _lr_computed = False
    _lr_results_by_idx: dict = {}
    _lr_closing_by_idx: dict = {}
    if _op_re_inputs and _lr_policy is not None and _lr_policy.enabled:
        _fin_pol = getattr(project_inputs, "financing", None) if project_inputs is not None else None
        _sc_keur = float(getattr(_fin_pol, "share_capital_keur", 0.0) or 0.0)
        _lr_cap = _lr_policy.cap_fraction
        from financial_engine.tax.interest_limitation import (
            EquityStatePeriodInput as _EquityInput,
            roll_forward_equity_state as _roll_equity,
        )
        _eq_inputs = tuple(
            _EquityInput(
                period_index=pidx,
                net_income_keur=ni,
                gross_dividends_keur=ld,
            )
            for pidx, ni, ld, _pend in _op_re_inputs
        )
        _lr_results_all = _roll_equity(
            _eq_inputs,
            share_capital_keur=_sc_keur,
            legal_reserve_cap_fraction=_lr_cap,
            opening_legal_reserve_keur=0.0,
            opening_retained_earnings_keur=cod_opening_re or 0.0,
        )
        _lr_results_by_idx = {r.period_index: r for r in _lr_results_all}
        _lr_closing_by_idx = {
            r.period_index: r.closing_legal_reserve_keur for r in _lr_results_all
        }
        _lr_computed = True

    # Build retained-earnings periods post-loop so legal-reserve transfers
    # can be included in the sequential opening → closing roll-forward.
    _re_open = cod_opening_re
    for _pidx, _ni, _ld, _pend in _op_re_inputs:
        _lrt = 0.0
        if _lr_computed and _pidx in _lr_results_by_idx:
            _lrt = float(_lr_results_by_idx[_pidx].legal_reserve_transfer_keur)
        _re_close = (
            None if _re_open is None
            else _re_open + _ni - _ld - _lrt
        )
        re_periods.append(RetainedEarningsPeriod(
            period_index=_pidx,
            period_end=_pend,
            opening_retained_earnings_keur=_re_open,
            net_income_keur=_ni,
            legal_equity_distribution_keur=_ld,
            legal_reserve_allocation_keur=_lrt if _lr_computed else None,
            closing_retained_earnings_keur=_re_close,
        ))
        if _re_open is not None:
            _re_open = _re_close

    # Status codes for newly resolved items.
    _fixed_asset_status = (
        StatementStatus.OK if gfa_keur is not None
        else StatementStatus.BOOK_CAPITALIZATION_BASIS_UNAVAILABLE
    )
    _legal_reserve_status = (
        StatementStatus.OK if _lr_computed
        else StatementStatus.LEGAL_RESERVE_AUTHORITY_UNAVAILABLE
    )

    if non_finite:
        overall = StatementStatus.NON_FINITE_RESULT
    else:
        # Honest partial availability: unrestricted cash and complete balance
        # sheet remain unavailable; P&L financing income (interest on cash/
        # reserves) is an upstream engine gap — it cannot be added to C3 P&L
        # without corresponding tax/CFADS effects.
        overall = StatementStatus.UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE

    if gfa_keur is None and _gfa_unavailable_msg is None:
        _gfa_unavailable_msg = (
            "BOOK_CAPITALIZATION_BASIS_UNAVAILABLE: ConstructionFinancingResult "
            "not available for this project; only accumulated book depreciation is "
            "causal."
        )
    unavailable.update({
        "balance_sheet": (
            "UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE: closing unrestricted "
            "cash requires a causal unrestricted-cash roll-forward that the "
            "clean runtime does not yet provide; no residual-cash insert applied."
        ),
        **({"gross_fixed_assets": _gfa_unavailable_msg} if gfa_keur is None else {}),
        **({} if _lr_computed else {
            "legal_reserve": (
                "LEGAL_RESERVE_AUTHORITY_UNAVAILABLE: LegalReservePolicy not "
                "set in AccountingPolicyConfig or not enabled."
            )
        }),
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
        "income_statement": (
            "FINANCING_INCOME_AUTHORITY_UNAVAILABLE: interest on unrestricted "
            "cash / reserve balances has no clean authority; the P&L exposes "
            "all known lines but is not a complete financing result."
        ),
        "unrestricted_cash": (
            "UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE: no causal "
            "unrestricted-cash roll-forward (§22-§24 source audit pending); "
            "closing cash is never solved as a Balance Sheet residual."
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
        fixed_asset_status=_fixed_asset_status,
        fixed_asset_periods=tuple(fa_periods),
        # Correction C §9-§10: full RE roll-forward consumes Net Income,
        # whose authority is incomplete (financing income) — the roll-forward
        # arithmetic is exposed but the status stays truthful, and it is
        # separate from opening-RE / legal-reserve / unrestricted-cash status.
        retained_earnings_status=(
            StatementStatus.FINANCING_INCOME_AUTHORITY_UNAVAILABLE
            if opening_re_authority else opening_re_status
        ),
        retained_earnings_periods=tuple(re_periods),
        opening_retained_earnings_status=opening_re_status,
        cod_opening_retained_earnings_keur=cod_opening_re,
        legal_reserve_status=_legal_reserve_status,
        unrestricted_cash_status=(
            StatementStatus.UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE
        ),
        balance_sheet_status=StatementStatus.UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE,
        balance_sheet_periods=tuple(bs_periods),
        accounting_policies=AccountingPolicies(
            shl_construction_accounting_authority=_shl_accounting_authority,
            legal_reserve_authority=_legal_reserve_authority,
            book_capitalization_authority=_book_cap_authority,
            opening_re_authority=_opening_re_pol_authority,
            cash_interest_income_authority=_cash_interest_authority,
            book_capitalization_components=_book_cap_components,
            provenance={
                "baseline": "clean-engine results only (no legacy statement modules)",
                "axis": "model.periods; G2C joined by cashflow_date == period_end",
                "provenance_mechanism": "AccountingPolicyConfig (typed input from factory)",
                "this_project_source_proven": (
                    _book_cap_authority == AccountingPolicyAuthority.SOURCE_PROVEN
                ),
                "gfa_computed": gfa_keur is not None,
                "gfa_report": gfa_report,
                "legal_reserve_computed": _lr_computed,
                "legal_reserve_closing_by_period": _lr_closing_by_idx,
            },
        ),
        unavailable_reasons=unavailable,
        authority_labels={
            "pnl": LineAuthority.EXISTING_CLEAN_AUTHORITY.value,
            "tax_bridge": LineAuthority.EXISTING_CLEAN_AUTHORITY.value,
            "pf_cash_waterfall": LineAuthority.EXISTING_CLEAN_AUTHORITY.value,
            "accumulated_book_depreciation": (
                LineAuthority.DERIVED_ACCOUNTING_ROLL_FORWARD.value),
            "retained_earnings_movements": (
                LineAuthority.DERIVED_ACCOUNTING_ROLL_FORWARD.value),
            "gross_fixed_assets": (
                LineAuthority.EXISTING_CLEAN_AUTHORITY.value if gfa_keur is not None
                else LineAuthority.UNRESOLVED.value
            ),
            "unrestricted_cash": LineAuthority.UNRESOLVED.value,
            "opening_retained_earnings": (
                _map_opening_re_label(_apc)
                if opening_re_authority else LineAuthority.UNRESOLVED.value
            ),
            "legal_reserve": (
                LineAuthority.DERIVED_ACCOUNTING_ROLL_FORWARD.value if _lr_computed
                else LineAuthority.UNRESOLVED.value
            ),
        },
    )
