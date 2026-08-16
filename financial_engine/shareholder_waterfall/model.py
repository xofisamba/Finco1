"""MVP G2C — Covenant-Gated Shareholder Waterfall model.

Extends G2B with a DSCR distribution lockup gate sourced from
extracted fixture Inputs!D223 (senior_lockup_dscr = 1.10).

Source-proven waterfall ordering:
  1. signed_post_senior = R84 (pre-gate junior FCF from clean engine)
  2. Distribution Account roll-forward (CF108):
       da_available[t] = signed_post_senior[t] + da_closing[t-1]
  3. CF109 5-component gate applied → fcf_for_distribution = R109
       gate active only within senior maturity (G4 <= B11)
       LOCKED:  fcf_for_distribution = 0, da_closing = da_available (accumulated)
       OPEN:    fcf_for_distribution = da_available, da_closing = 0
  4. SHL cash service drawn from fcf_for_distribution (R112 = R109)
       via project-owned compute_shareholder_loan_schedules()
  5. legal_equity_distribution = max(0, fcf_for_distribution - SHL_service) = R116

MANUAL_WORKBOOK_SOURCE_EVIDENCE:
  Workbook: 20260414_BP_Oborovo_Sensitivity_FINAL_for_PPT.xlsm
  SHA-256: 15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920
  CF!G108 = =SUM(G94,G95,G106)+F110
  CF!G109 = =IF(AND(OR(G$138<$B$109,G$4=0,G108<0,G91<G86,G105<G100),G$4<=$B$11),0,G108)
  CF!G110 = G108-G109
  $B$11 = Senior Debt Maturity years = 14
  $B$109 = distribution_lockup_dscr = 1.10

Gate components (CF109 source-proven):
  A: G$138 < $B$109  — DSCR below lockup threshold
  B: G$4 = 0         — construction period
  C: G108 < 0        — DA available negative
  D: G91 < G86       — Senior DSRA ending < target (Oborovo: both=0 → False)
  E: G105 < G100     — J-DSRA ending < target (NOT_APPLICABLE: both=0 → False)
  Gate = OR(A,B,C,D,E) AND within_senior_maturity (G4 <= B11)

SHL POLICY AUTHORITY:
  G2C does NOT hardcode a repayment mode or day-count convention.

DEDUCTIBLE SHL COVENANT FEEDBACK:
  If SHL interest is tax-deductible and the gate locks in any period,
  the resulting PIK accumulation would increase future SHL gross interest,
  affecting taxable income → CFADS → DSCR → gate — a feedback loop not
  yet closed in G2C. Status: G2C_DEDUCTIBLE_SHL_COVENANT_FEEDBACK_NOT_YET_CLOSED.

BULLET FAIL-CLOSED:
  If BULLET balloon > available FCF at maturity, unpaid principal remains.
  Subsequent periods: gross=0, PIK=0, principal=0 (no terms; not invented).
  Equity distribution = 0 in all periods after unresolved BULLET.
  Return metrics = None with UNPAID_SHL_AT_CONTRACTUAL_MATURITY status.

Source map:
  R84  → signed_post_senior (pre-DSRA, pre-gate)
  R109 → fcf_for_distribution (gate output)
  R112 → SHL service input (= R109 per source formula CF112=H109)
  R116 → legal_equity_distribution_keur
"""
from __future__ import annotations

import dataclasses
from datetime import date

from finco_core.inputs import DebtServiceReserveSupportMode, ProjectInputs, SponsorFundingMode
from finco_core.inputs._models import ShlInterestDeductibilityMode

from financial_engine.adapters.project_inputs import (
    _build_shareholder_loan_model_input_from_project_inputs,
)
from financial_engine.financing.contracts import (
    ConstructionFundingPeriod,
    ProjectFinancingResult,
)
from financial_engine.financing.project import run_project_financing_model
from financial_engine.financing.dsrf import compute_dsrf_fee_schedule
from financial_engine.results import ProjectModelResult
from financial_engine.shl.production import compute_shareholder_loan_schedules
from financial_engine.shareholder_waterfall.contracts import (
    CovenantGatedWaterfallPeriod,
    CovenantGatedWaterfallResult,
    DistributionGateStatus,
    ReserveSupportGateStatus,
)
from financial_engine.sponsor_returns.contracts import ReturnMetricStatus
from financial_engine.sponsor_returns.model import compute_gated_sponsor_return_metrics

_G2C_DA_STATUS_CAUSAL = "G2C_DISTRIBUTION_ACCOUNT_CAUSAL_CF108_CF109_CF110_SOURCE_PROVEN"
_G2C_DEDUCTIBLE_FEEDBACK_STATUS = "G2C_DEDUCTIBLE_SHL_COVENANT_FEEDBACK_NOT_YET_CLOSED"
_DSRF_NO_DRAW_STATUS = "DSRF_AVAILABLE_SUPPORT_ONLY_NO_DRAW_ENGINE"
_G2C_RESERVE_GATE_STATUS = "G2C_RESERVE_GATE_NOT_CAUSALLY_CLOSED"


def _evaluate_reserve_support_gate(
    dsra_mode: "DebtServiceReserveSupportMode",
    requirement_keur: float,
    dsrf_commitment_keur: float,
    is_construction: bool,
) -> ReserveSupportGateStatus:
    """Evaluate reserve support gate for one period.

    NONE   → NOT_APPLICABLE (requirement = 0, no block)
    CASH_DSRA → PASS_NEUTRAL_SOURCE_PROVEN if req=0, else PASS (initial reserve assumed funded)
    DSRF   → DSRF_AVAILABLE_SUPPORT_ONLY_NO_DRAW_ENGINE (no draw engine modeled)

    G2C_RESERVE_GATE_NOT_CAUSALLY_CLOSED: gate status is informational only.
    CF108 not extracted; reserve gate does not block fcf_for_distribution in G2C.
    """
    from finco_core.inputs import DebtServiceReserveSupportMode
    if is_construction:
        return ReserveSupportGateStatus.CONSTRUCTION
    if dsra_mode == DebtServiceReserveSupportMode.NONE:
        return ReserveSupportGateStatus.NOT_APPLICABLE
    if dsra_mode == DebtServiceReserveSupportMode.DSRF:
        return ReserveSupportGateStatus.DSRF_AVAILABLE_SUPPORT_ONLY_NO_DRAW_ENGINE
    # CASH_DSRA
    if requirement_keur <= 0.0:
        return ReserveSupportGateStatus.PASS_NEUTRAL_SOURCE_PROVEN
    return ReserveSupportGateStatus.PASS


def _add_months(d: date, months: int) -> date:
    import calendar
    month = d.month + months
    year = d.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _construction_period_date(financial_close: date, period_index: int) -> date:
    return _add_months(financial_close, period_index - 1)


def run_project_shareholder_waterfall_model(
    project_inputs: ProjectInputs,
    *,
    source_id: str = "",
    baseline_commit_sha: str = "",
) -> CovenantGatedWaterfallResult:
    """Compute G2C covenant-gated shareholder waterfall from G2A financing results.

    Adds DSCR distribution lockup gate (project_inputs.financing.lockup_dscr) on top
    of the G2B SHL-gated distribution mechanics.

    Source-proven ordering: gate is UPSTREAM of SHL service.
    DA roll-forward per CF108/CF109/CF110 source formulas.
    BULLET fail-closed: equity=0, metrics=None after underfunded maturity balloon.
    """
    financing: ProjectFinancingResult = run_project_financing_model(
        project_inputs,
        source_id=source_id,
        baseline_commit_sha=baseline_commit_sha,
    )

    model_result: ProjectModelResult = financing.project_model_result  # type: ignore[assignment]
    fin = project_inputs.financing
    info = project_inputs.info
    tax = project_inputs.tax

    distribution_lockup_dscr: float = fin.lockup_dscr
    financial_close: date = info.financial_close

    # Reserve support gate inputs
    from finco_core.inputs import DebtServiceReserveSupportMode
    dsra_mode = fin.dsra_support_mode
    reserve_requirement_keur: float = getattr(fin, "debt_service_reserve_requirement_keur", 0.0) or 0.0
    dsrf_commitment_keur: float = getattr(fin, "dsrf_commitment_keur", 0.0) or 0.0

    # ── Build lookup maps ─────────────────────────────────────────────────────
    construction_periods_by_index: dict[int, ConstructionFundingPeriod] = {
        p.period_index: p for p in financing.construction_funding.periods
    }

    if model_result.post_senior_cash is None:
        raise ValueError("G2C requires post_senior_cash; clean engine did not produce it")

    signed_post_senior_by_idx: dict[int, float] = dict(
        zip(
            model_result.post_senior_cash.period_indices,
            model_result.post_senior_cash.cash_after_senior_before_reserves_keur,
        )
    )

    # DSCR lookup — None where no Senior DS
    base_dscr_by_idx: dict[int, float | None] = {}
    senior_ds_nonzero_by_idx: dict[int, bool] = {}
    senior_last_period_index: int | None = None
    if model_result.senior_debt is not None:
        sd = model_result.senior_debt
        ds_arr = sd.senior_debt_service_keur
        for idx, dscr, ds in zip(sd.period_indices, sd.base_dscr, ds_arr):
            base_dscr_by_idx[idx] = dscr
            senior_ds_nonzero_by_idx[idx] = ds > 0.0
        nonzero_ds = [i for i, ds in zip(sd.period_indices, ds_arr) if ds > 0.0]
        if nonzero_ds:
            senior_last_period_index = max(nonzero_ds)

    period_date_by_idx: dict[int, date] = {
        p.period_index: p.period_end for p in model_result.periods
    }
    period_start_by_idx: dict[int, date] = {
        p.period_index: p.period_start for p in model_result.periods
    }

    # ── DSRF commitment fee schedule ──────────────────────────────────────────
    from finco_core.inputs import DsrfCommitmentFeeTreatment
    _fee_treatment = getattr(fin, "dsrf_fee_treatment", DsrfCommitmentFeeTreatment.POST_SENIOR_CASH)
    if _fee_treatment != DsrfCommitmentFeeTreatment.POST_SENIOR_CASH:
        raise ValueError(
            f"G2C_UNSUPPORTED_DSRF_FEE_TREATMENT: {_fee_treatment!r}. "
            "Only POST_SENIOR_CASH (EXPLICIT_GENERIC_MVP_POLICY) is source-proven. "
            "No other DSRF fee treatment is implemented."
        )
    dsrf_fee_by_idx: dict[int, float] = {}
    if dsra_mode == DebtServiceReserveSupportMode.DSRF:
        dsrf_req = getattr(fin, "debt_service_reserve_requirement_keur", 0.0) or 0.0
        if dsrf_req > 0.0 and fin.dsrf_commitment_keur < dsrf_req:
            raise ValueError(
                f"G2C_DSRF_COMMITMENT_BELOW_REQUIRED_RESERVE: "
                f"commitment={fin.dsrf_commitment_keur} < required={dsrf_req}"
            )
        if fin.dsrf_commitment_keur > 0 and fin.dsrf_commitment_fee_rate_pa > 0.0:
            op_indices = [p.period_index for p in model_result.periods if p.is_operation]
            op_starts = [period_start_by_idx[i] for i in op_indices]
            op_ends = [period_date_by_idx[i] for i in op_indices]
            dsrf_schedule = compute_dsrf_fee_schedule(
                op_indices, op_starts, op_ends,
                fin.dsrf_commitment_keur,
                fin.dsrf_commitment_fee_rate_pa,
                senior_last_period_index=senior_last_period_index if fin.dsrf_fee_expires_at_senior_maturity else None,
                day_count_convention=fin.dsrf_day_count,
            )
            dsrf_fee_by_idx = dict(zip(dsrf_schedule.period_indices, dsrf_schedule.dsrf_commitment_fee_keur))

    # ── Senior DSRA causal roll-forward ──────────────────────────────────────
    # MANUAL_WORKBOOK_SOURCE_EVIDENCE:
    #   CF86: Senior DSRA target (Oborovo: 0 — no DSRA required)
    #   CF92: Senior DSRA ending balance
    # For CASH_DSRA: target = reserve_requirement_keur, funded at construction.
    # Oborovo: NONE mode → target=0, all balances=0.
    # Gate component D: dsra_ending < dsra_target (False when both=0).
    dsra_target_keur = reserve_requirement_keur if dsra_mode == DebtServiceReserveSupportMode.CASH_DSRA else 0.0
    # CASH_DSRA: assume fully funded from construction (no draw engine modeled).
    # Opening of first operating period = target. Closing = opening (static, no draws).
    dsra_opening: float = dsra_target_keur  # first period
    dsra_opening_by_idx: dict[int, float] = {}
    dsra_closing_by_idx: dict[int, float] = {}
    prev_dsra_closing: float = dsra_target_keur
    for period in model_result.periods:
        if not period.is_operation:
            continue
        idx = period.period_index
        _opening = prev_dsra_closing
        # No draw engine: DSRA balance stays at target (or 0 for NONE/DSRF)
        _closing = dsra_target_keur
        dsra_opening_by_idx[idx] = _opening
        dsra_closing_by_idx[idx] = _closing
        prev_dsra_closing = _closing

    # J-DSRA: NOT_APPLICABLE for no-junior-debt projects.
    # Gate component E = False (both ending and target = 0).
    j_dsra_target_keur = 0.0
    j_dsra_closing_keur = 0.0

    # ── Phase 1: DA roll-forward + CF109 5-component gate ────────────────────
    # CF108: da_available[t] = signed_post_senior[t] + da_closing[t-1]
    # CF109: IF(AND(OR(A,B,C,D,E), within_senior_maturity), 0, da_available)
    # CF110: da_closing[t] = da_available[t] - release[t]
    #
    # Note: signed_post_senior here corresponds to G94 (FCF for junior debt),
    # plus G95 (junior DS = 0) plus G106 (J-DSRA movement = 0).
    # For no-junior-debt projects: G94 = signed_post_senior directly.

    gate_info_by_idx: dict[int, tuple] = {}
    da_info_by_idx: dict[int, tuple] = {}  # idx → (opening, inflow, available, release, closing, booleans...)
    gated_cash_all_periods: list[float] = []

    da_closing_prev: float = 0.0  # DA closing of prior period (F110 in first op period = 0)

    for period in model_result.periods:
        idx = period.period_index
        if period.is_construction:
            gated_cash_all_periods.append(0.0)
            continue

        if idx not in signed_post_senior_by_idx:
            raise ValueError(
                f"G2C: operating period {idx} absent from post_senior_cash schedule"
            )
        signed_post_senior = signed_post_senior_by_idx[idx]
        dsrf_fee = dsrf_fee_by_idx.get(idx, 0.0)
        # Inflow to DA = post-senior cash net of DSRF fee
        da_inflow = signed_post_senior - dsrf_fee

        # CF108: DA available = inflow + prior closing
        da_available = da_inflow + da_closing_prev

        # Gate components (CF109 source-proven)
        dscr_val = base_dscr_by_idx.get(idx)
        has_senior_ds = senior_ds_nonzero_by_idx.get(idx, False)
        comp_a = (dscr_val is not None and has_senior_ds and dscr_val < distribution_lockup_dscr)
        comp_b = False  # operating period, not construction
        comp_c = da_available < 0.0
        dsra_ending = dsra_closing_by_idx.get(idx, 0.0)
        comp_d = dsra_ending < dsra_target_keur  # False when both=0 (Oborovo)
        comp_e = j_dsra_closing_keur < j_dsra_target_keur  # False always (no J-DSRA)

        # within_senior_maturity: gate active only if we're within senior debt term
        # Source: G$4 <= $B$11 ($B$11 = Senior Debt Maturity years)
        # We use period index <= senior_last_period_index as proxy
        if senior_last_period_index is not None:
            within_senior_maturity = idx <= senior_last_period_index
        else:
            within_senior_maturity = False

        gate_locked = (comp_a or comp_b or comp_c or comp_d or comp_e) and within_senior_maturity

        # CF109: release
        if gate_locked:
            da_release = 0.0
            gate_status = DistributionGateStatus.LOCKED_DSCR_BELOW_LOCKUP
        elif dscr_val is None or not has_senior_ds:
            # No DSCR available: gate open (no debt to covenant)
            da_release = max(0.0, da_available)
            gate_status = DistributionGateStatus.DSCR_UNAVAILABLE_GATE_OPEN
        else:
            da_release = max(0.0, da_available)
            gate_status = DistributionGateStatus.OPEN

        # CF110 = CF108 - CF109: DA closing balance
        # Invariant: da_available = da_release + da_closing always holds.
        # When gate open and da_available > 0: release = available, closing = 0
        # When gate open and da_available < 0: release = 0, closing = available (negative shortfall)
        # When gate locked: release = 0, closing = da_available (accumulated in DA)
        da_closing = da_available - da_release
        fcf_for_distribution = da_release  # = max(0, da_available) when open, 0 when locked
        # covenant_locked: per-period legacy view (positive locked cash this period)
        covenant_locked = max(0.0, da_available) if gate_locked else 0.0
        cash_shortfall = max(0.0, -(signed_post_senior - dsrf_fee))

        gate_info_by_idx[idx] = (gate_status, fcf_for_distribution, covenant_locked, dsrf_fee, signed_post_senior, cash_shortfall)
        da_info_by_idx[idx] = (
            da_closing_prev,   # opening
            da_inflow,         # inflow (net of DSRF fee)
            da_available,      # available (CF108)
            da_release,        # release (CF109)
            da_closing,        # closing (CF110)
            comp_a, comp_b, comp_c, comp_d, comp_e,
            within_senior_maturity,
        )
        gated_cash_all_periods.append(fcf_for_distribution)
        da_closing_prev = da_closing

    # ── Phase 2: SHL schedule using project-owned policy ─────────────────────
    shl_opening_by_idx: dict[int, float] = {}
    shl_gross_by_idx: dict[int, float] = {}
    shl_cash_int_by_idx: dict[int, float] = {}
    shl_pik_by_idx: dict[int, float] = {}
    shl_principal_by_idx: dict[int, float] = {}
    shl_closing_by_idx: dict[int, float] = {}

    has_shl = financing.derived_shl_cash_principal_keur > 0.0
    shl_maturity_idx: int | None = None
    if has_shl:
        shl_model_input = _build_shareholder_loan_model_input_from_project_inputs(
            project_inputs,
            model_result.periods,
            senior_debt_maturity_period_index=senior_last_period_index,
        )
        if shl_model_input is not None:
            if abs(shl_model_input.initial_principal_keur - financing.derived_shl_cash_principal_keur) > 1e-4:
                shl_model_input = dataclasses.replace(
                    shl_model_input,
                    initial_principal_keur=financing.derived_shl_cash_principal_keur,
                )
            shl_maturity_idx = shl_model_input.maturity_period_index

            gated_shl_schedule = compute_shareholder_loan_schedules(
                model_result.periods,
                shl_model_input,
                gated_cash_all_periods,
                diagnostics=None,
            )
            shl_opening_by_idx = dict(zip(gated_shl_schedule.period_indices, gated_shl_schedule.shl_opening_keur))
            shl_gross_by_idx = dict(zip(gated_shl_schedule.period_indices, gated_shl_schedule.shl_gross_interest_keur))
            shl_cash_int_by_idx = dict(zip(gated_shl_schedule.period_indices, gated_shl_schedule.shl_cash_interest_keur))
            shl_pik_by_idx = dict(zip(gated_shl_schedule.period_indices, gated_shl_schedule.shl_pik_interest_keur))
            shl_principal_by_idx = dict(zip(gated_shl_schedule.period_indices, gated_shl_schedule.shl_principal_keur))
            shl_closing_by_idx = dict(zip(gated_shl_schedule.period_indices, gated_shl_schedule.shl_closing_keur))

    # ── Phase 3: Deductible SHL feedback check ───────────────────────────────
    shl_deductible = (
        getattr(tax, "shl_interest_deductibility", ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE)
        != ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE
    )
    gate_locks_any = any(
        info[0] == DistributionGateStatus.LOCKED_DSCR_BELOW_LOCKUP
        for info in gate_info_by_idx.values()
    )
    shl_pik_differs_from_g2a = has_shl and gate_locks_any and any(
        shl_pik_by_idx.get(idx, 0.0) > 0.0 for idx in gate_info_by_idx
    )
    deductible_feedback_active = shl_deductible and shl_pik_differs_from_g2a

    # ── Phase 4: Assemble per-period records ──────────────────────────────────
    waterfall_periods: list[CovenantGatedWaterfallPeriod] = []

    # --- Construction periods ---
    for k in sorted(construction_periods_by_index.keys()):
        cp = construction_periods_by_index[k]
        cf_date = _construction_period_date(financial_close, k)

        share_cap = cp.share_capital_draw_keur
        share_prem = cp.share_premium_draw_keur
        other_committed = cp.other_committed_equity_draw_keur
        add_eq = cp.additional_equity_draw_keur
        shl_draw = cp.shl_cash_draw_keur

        pure_equity_net = -(share_cap + share_prem + other_committed + add_eq)
        total_sponsor_net = pure_equity_net - shl_draw

        waterfall_periods.append(CovenantGatedWaterfallPeriod(
            period_index=k,
            cashflow_date=cf_date,
            is_construction=True,
            base_dscr=None,
            distribution_lockup_dscr=distribution_lockup_dscr,
            distribution_gate_status=DistributionGateStatus.CONSTRUCTION,
            debt_service_reserve_requirement_keur=reserve_requirement_keur,
            reserve_support_gate_status=ReserveSupportGateStatus.CONSTRUCTION,
            signed_post_senior_keur=0.0,
            dsrf_commitment_fee_keur=0.0,
            fcf_for_distribution_keur=0.0,
            covenant_locked_keur=0.0,
            # DA fields: zero during construction
            distribution_account_opening_keur=0.0,
            distribution_account_inflow_keur=0.0,
            distribution_account_available_keur=0.0,
            gate_component_dscr_below_lockup=False,
            gate_component_construction=True,
            gate_component_da_negative=False,
            gate_component_dsra_underfunded=False,
            gate_component_j_dsra_underfunded=False,
            within_senior_maturity=True,
            distribution_account_release_keur=0.0,
            distribution_account_closing_keur=0.0,
            # DSRA: zero during construction
            senior_dsra_target_keur=dsra_target_keur,
            senior_dsra_opening_keur=0.0,
            senior_dsra_closing_keur=0.0,
            # BULLET: not applicable during construction
            shl_bullet_unpaid_at_maturity=False,
            shl_opening_balance_keur=0.0,
            shl_gross_interest_keur=0.0,
            shl_cash_interest_receipt_keur=0.0,
            shl_pik_keur=0.0,
            contractual_shl_principal_due_keur=0.0,
            actual_shl_principal_paid_keur=0.0,
            unpaid_shl_principal_keur=0.0,
            actual_shl_closing_balance_keur=0.0,
            shl_principal_receipt_keur=0.0,
            shl_closing_balance_keur=0.0,
            legal_equity_distribution_keur=0.0,
            cash_shortfall_keur=0.0,
            share_capital_contribution_keur=share_cap,
            share_premium_contribution_keur=share_prem,
            other_committed_equity_contribution_keur=other_committed,
            additional_equity_contribution_keur=add_eq,
            shl_cash_contribution_keur=shl_draw,
            pure_equity_net_cashflow_keur=pure_equity_net,
            total_sponsor_net_cashflow_keur=total_sponsor_net,
        ))

    # --- Operating periods ---
    # actual_shl_carry: causal closing balance to override contractual scheduler
    actual_shl_carry: float | None = None
    # bullet_unpaid_active: once True, equity=0 and post-maturity SHL terms = 0
    bullet_unpaid_active: bool = False

    for period in model_result.periods:
        if not period.is_operation:
            continue
        idx = period.period_index
        cf_date = period_date_by_idx[idx]

        gate_status, fcf_for_distribution, covenant_locked, dsrf_fee, signed_post_senior, cash_shortfall = gate_info_by_idx[idx]

        (
            da_opening, da_inflow, da_available, da_release, da_closing,
            comp_a, comp_b, comp_c, comp_d, comp_e, within_sm,
        ) = da_info_by_idx[idx]

        # BULLET post-maturity: once balloon was underfunded, no SHL terms exist.
        # Do NOT read from contractual scheduler — it shows 0 post-maturity which is
        # consistent but we track via actual_shl_carry for causal opening.
        is_post_maturity = bullet_unpaid_active

        # SHL opening: use actual carry-forward if available (causal), else contractual.
        if actual_shl_carry is not None:
            shl_opening = actual_shl_carry
        else:
            shl_opening = shl_opening_by_idx.get(idx, 0.0)

        if is_post_maturity:
            # Post-maturity with unpaid BULLET: no terms (do not invent default interest).
            shl_gross = 0.0
            actual_shl_cash_int = 0.0
            shl_pik = 0.0
            contractual_shl_principal = 0.0
            actual_shl_principal = 0.0
        else:
            shl_gross = shl_gross_by_idx.get(idx, 0.0)
            actual_shl_cash_int = shl_cash_int_by_idx.get(idx, 0.0)
            shl_pik = shl_pik_by_idx.get(idx, 0.0)
            contractual_shl_principal = shl_principal_by_idx.get(idx, 0.0)
            actual_shl_principal = min(
                contractual_shl_principal,
                max(0.0, fcf_for_distribution - actual_shl_cash_int),
            )

        unpaid_shl_principal = contractual_shl_principal - actual_shl_principal if not is_post_maturity else 0.0
        actual_shl_closing = max(0.0, shl_opening + shl_pik - actual_shl_principal)

        # Detect underfunded BULLET at its contractual maturity period
        at_maturity = (shl_maturity_idx is not None and idx == shl_maturity_idx)
        if at_maturity and has_shl and unpaid_shl_principal > 1e-6:
            bullet_unpaid_active = True

        if has_shl:
            actual_shl_carry = actual_shl_closing

        shl_bullet_flag = bullet_unpaid_active

        # BULLET fail-closed: block equity distributions after unresolved BULLET
        if bullet_unpaid_active and not at_maturity:
            distribution = 0.0
        else:
            shl_service_actual = actual_shl_cash_int + actual_shl_principal
            distribution = max(0.0, fcf_for_distribution - shl_service_actual)

        pure_equity_net = distribution
        total_sponsor_net = pure_equity_net + actual_shl_cash_int + actual_shl_principal

        dsra_op = dsra_opening_by_idx.get(idx, 0.0)
        dsra_cl = dsra_closing_by_idx.get(idx, 0.0)

        waterfall_periods.append(CovenantGatedWaterfallPeriod(
            period_index=idx,
            cashflow_date=cf_date,
            is_construction=False,
            base_dscr=base_dscr_by_idx.get(idx),
            distribution_lockup_dscr=distribution_lockup_dscr,
            distribution_gate_status=gate_status,
            debt_service_reserve_requirement_keur=reserve_requirement_keur,
            reserve_support_gate_status=_evaluate_reserve_support_gate(
                dsra_mode, reserve_requirement_keur, dsrf_commitment_keur, is_construction=False,
            ),
            signed_post_senior_keur=signed_post_senior,
            dsrf_commitment_fee_keur=dsrf_fee,
            fcf_for_distribution_keur=fcf_for_distribution,
            covenant_locked_keur=covenant_locked,
            distribution_account_opening_keur=da_opening,
            distribution_account_inflow_keur=da_inflow,
            distribution_account_available_keur=da_available,
            gate_component_dscr_below_lockup=comp_a,
            gate_component_construction=comp_b,
            gate_component_da_negative=comp_c,
            gate_component_dsra_underfunded=comp_d,
            gate_component_j_dsra_underfunded=comp_e,
            within_senior_maturity=within_sm,
            distribution_account_release_keur=da_release,
            distribution_account_closing_keur=da_closing,
            senior_dsra_target_keur=dsra_target_keur,
            senior_dsra_opening_keur=dsra_op,
            senior_dsra_closing_keur=dsra_cl,
            shl_bullet_unpaid_at_maturity=shl_bullet_flag,
            shl_opening_balance_keur=shl_opening,
            shl_gross_interest_keur=shl_gross,
            shl_cash_interest_receipt_keur=actual_shl_cash_int,
            shl_pik_keur=shl_pik,
            contractual_shl_principal_due_keur=contractual_shl_principal,
            actual_shl_principal_paid_keur=actual_shl_principal,
            unpaid_shl_principal_keur=unpaid_shl_principal,
            actual_shl_closing_balance_keur=actual_shl_closing,
            shl_principal_receipt_keur=actual_shl_principal,
            shl_closing_balance_keur=actual_shl_closing,
            legal_equity_distribution_keur=distribution,
            cash_shortfall_keur=cash_shortfall,
            share_capital_contribution_keur=0.0,
            share_premium_contribution_keur=0.0,
            other_committed_equity_contribution_keur=0.0,
            additional_equity_contribution_keur=0.0,
            shl_cash_contribution_keur=0.0,
            pure_equity_net_cashflow_keur=pure_equity_net,
            total_sponsor_net_cashflow_keur=total_sponsor_net,
        ))

    # ── Aggregate totals ──────────────────────────────────────────────────────
    total_sc = sum(p.share_capital_contribution_keur for p in waterfall_periods)
    total_sp = sum(p.share_premium_contribution_keur for p in waterfall_periods)
    total_oce = sum(p.other_committed_equity_contribution_keur for p in waterfall_periods)
    total_ae = sum(p.additional_equity_contribution_keur for p in waterfall_periods)
    total_le = total_sc + total_sp + total_oce + total_ae
    total_shl_contrib = sum(p.shl_cash_contribution_keur for p in waterfall_periods)
    total_sponsor_contrib = total_le + total_shl_contrib

    total_shl_int_recd = sum(p.shl_cash_interest_receipt_keur for p in waterfall_periods)
    total_shl_prin_recd = sum(p.shl_principal_receipt_keur for p in waterfall_periods)
    total_distributions = sum(p.legal_equity_distribution_keur for p in waterfall_periods)
    total_covenant_locked = sum(p.covenant_locked_keur for p in waterfall_periods)
    total_sponsor_receipts = total_distributions + total_shl_int_recd + total_shl_prin_recd
    total_dsrf_fee = sum(p.dsrf_commitment_fee_keur for p in waterfall_periods)
    # Sum of positive DA closings = total locked cash in DA (shortfall negatives excluded)
    total_da_locked = sum(
        max(0.0, p.distribution_account_closing_keur)
        for p in waterfall_periods if not p.is_construction
    )

    # Gate summary
    operating_with_ds = [
        p for p in waterfall_periods
        if not p.is_construction and p.distribution_gate_status != DistributionGateStatus.DSCR_UNAVAILABLE_GATE_OPEN
    ]
    periods_locked = sum(
        1 for p in waterfall_periods
        if p.distribution_gate_status == DistributionGateStatus.LOCKED_DSCR_BELOW_LOCKUP
    )
    periods_with_ds = len(operating_with_ds)

    # ── Return metrics — delegated to G2B authority ───────────────────────────
    pe_cfs = [p.pure_equity_net_cashflow_keur for p in waterfall_periods]
    pe_dates = [p.cashflow_date for p in waterfall_periods]
    ts_cfs = [p.total_sponsor_net_cashflow_keur for p in waterfall_periods]

    (
        pe_xirr, pe_xirr_status,
        pe_moic, pe_moic_status,
        ts_xirr, ts_xirr_status,
        ts_moic, ts_moic_status,
    ) = compute_gated_sponsor_return_metrics(
        cashflow_dates=pe_dates,
        pure_equity_cashflows=pe_cfs,
        total_sponsor_cashflows=ts_cfs,
        total_legal_equity_contributed_keur=total_le,
        total_sponsor_contributed_keur=total_sponsor_contrib,
    )

    # BULLET fail-close: unpaid SHL at contractual maturity → metrics are unreliable.
    # Subsequent periods have no SHL terms, meaning distributions are understated.
    if bullet_unpaid_active:
        _bu = ReturnMetricStatus.UNPAID_SHL_AT_CONTRACTUAL_MATURITY
        pe_xirr = None; pe_xirr_status = _bu
        pe_moic = None; pe_moic_status = _bu
        ts_xirr = None; ts_xirr_status = _bu
        ts_moic = None; ts_moic_status = _bu

    # Deductible feedback fail-closed (compounded on top of bullet if both active)
    if deductible_feedback_active and not bullet_unpaid_active:
        _fb = ReturnMetricStatus.UPSTREAM_FINANCIAL_FEEDBACK_NOT_CLOSED
        pe_xirr = None; pe_xirr_status = _fb
        pe_moic = None; pe_moic_status = _fb
        ts_xirr = None; ts_xirr_status = _fb
        ts_moic = None; ts_moic_status = _fb
    elif bullet_unpaid_active:
        # BULLET fail-closed: unpaid SHL at contractual maturity → metrics unreliable
        _bm = ReturnMetricStatus.UNPAID_SHL_AT_CONTRACTUAL_MATURITY
        pe_xirr = None
        pe_xirr_status = _bm
        pe_moic = None
        pe_moic_status = _bm
        ts_xirr = None
        ts_xirr_status = _bm
        ts_moic = None
        ts_moic_status = _bm

    return CovenantGatedWaterfallResult(
        financing_result=financing,
        distribution_lockup_dscr=distribution_lockup_dscr,
        waterfall_periods=tuple(waterfall_periods),
        total_share_capital_contributed_keur=total_sc,
        total_share_premium_contributed_keur=total_sp,
        total_other_committed_equity_contributed_keur=total_oce,
        total_additional_equity_contributed_keur=total_ae,
        total_legal_equity_contributed_keur=total_le,
        total_shl_cash_contributed_keur=total_shl_contrib,
        total_sponsor_contributed_keur=total_sponsor_contrib,
        total_shl_cash_interest_received_keur=total_shl_int_recd,
        total_shl_principal_received_keur=total_shl_prin_recd,
        total_legal_equity_distributions_keur=total_distributions,
        total_covenant_locked_keur=total_covenant_locked,
        total_sponsor_receipts_keur=total_sponsor_receipts,
        pure_equity_xirr=pe_xirr,
        pure_equity_xirr_status=pe_xirr_status,
        pure_equity_moic=pe_moic,
        pure_equity_moic_status=pe_moic_status,
        total_sponsor_xirr=ts_xirr,
        total_sponsor_xirr_status=ts_xirr_status,
        total_sponsor_moic=ts_moic,
        total_sponsor_moic_status=ts_moic_status,
        periods_locked_by_dscr=periods_locked,
        total_periods_with_senior_ds=periods_with_ds,
        total_dsrf_commitment_fee_keur=total_dsrf_fee,
        total_distribution_account_locked_keur=total_da_locked,
        distribution_account_status=_G2C_DA_STATUS_CAUSAL,
        shl_bullet_unpaid_at_maturity=bullet_unpaid_active,
        reserve_support_gate_status_summary=_G2C_RESERVE_GATE_STATUS,
        deductible_shl_covenant_feedback_status=(
            _G2C_DEDUCTIBLE_FEEDBACK_STATUS if deductible_feedback_active else None
        ),
    )
