"""G3B KUPI blind run diagnostic.

PHASE C — BLIND RUN RULE:
  Run the clean KUPI model BEFORE writing any assertion that pins source output targets.
  Do not tune KUPI inputs after seeing Senior/tax/SHL/IRR except when a source input
  mapping is independently proven wrong.

Run this with:
  python -m tests.diagnostics.kupi_blind_run
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from financial_engine.shareholder_waterfall import run_project_shareholder_waterfall_model
from tests.helpers.g3b_kupi_project import (
    create_kupi_project,
    create_kupi_project_source_effective_co2,
    _KUPI_TOTAL_USES_KEUR,
    _KUPI_SHL_PRINCIPAL_KEUR,
)


def _run(proj):
    return run_project_shareholder_waterfall_model(proj)


def _safe_sum(v):
    try:
        return sum(v)
    except Exception:
        return None


def _safe_len(v):
    try:
        return len(v)
    except Exception:
        return None


def main():
    print("=" * 70)
    print("G3B KUPI BLIND RUN DIAGNOSTIC")
    print("Workbook SHA-256: 111178fb21109f55df45c0cc1ea108104ac8b6ed60f010ba75b6c498795f5954")
    print("=" * 70)

    # ── Run A: Literal CO2-off ─────────────────────────────────────────────
    print("\n[RUN A] Literal CO2-off (Inputs!D121=FALSE)")
    proj_a = create_kupi_project()
    result_a = _run(proj_a)
    fr_a = result_a.financing_result
    pmr_a = fr_a.project_model_result

    print("\n── Period Axis ──────────────────────────────────────────────────")
    try:
        shl_a = pmr_a.shareholder_loan
        op_periods = list(shl_a.period_indices)
        print(f"  Operating period indices: {op_periods[0]}..{op_periods[-1]}")
        print(f"  Operating period count:   {len(op_periods)}")
    except Exception as e:
        print(f"  Period axis error: {e}")

    try:
        cf_a = pmr_a.construction_funding
        con_periods = [p.period_index for p in cf_a.periods]
        print(f"  Construction period indices: {con_periods}")
    except Exception as e:
        print(f"  Construction period info: {e}")

    print("\n── Total Uses / G2A ─────────────────────────────────────────────")
    try:
        uses = fr_a.project_uses.total_project_uses_keur
        senior = fr_a.final_senior_commitment_keur
        derived_shl = fr_a.derived_shl_cash_principal_keur
        print(f"  Total Uses (Finco):          {uses:>14.6f} kEUR")
        print(f"  Source authority:            {_KUPI_TOTAL_USES_KEUR:>14.6f} kEUR")
        print(f"  Δ Uses:                      {uses - _KUPI_TOTAL_USES_KEUR:>+14.6f} kEUR")
        print(f"  Senior (Finco):              {senior:>14.6f} kEUR")
        print(f"  Source authority:                147150.442310 kEUR")
        print(f"  Δ Senior:                    {senior - 147150.442310339:>+14.6f} kEUR")
        print(f"  Derived SHL (Finco):         {derived_shl:>14.6f} kEUR")
        print(f"  Configured SHL:              {_KUPI_SHL_PRINCIPAL_KEUR:>14.6f} kEUR")
        print(f"  Δ SHL (handshake):           {derived_shl - _KUPI_SHL_PRINCIPAL_KEUR:>+14.6f} kEUR")
        residual = uses - senior - proj_a.financing.share_capital_keur
        print(f"  G2A residual identity check: {residual:>14.6f} kEUR  (= Uses - Senior - Capital)")
    except Exception as e:
        print(f"  G2A error: {e}")

    print("\n── Production ───────────────────────────────────────────────────")
    try:
        ops = pmr_a.operating_schedules
        prod = ops.production_mwh
        print(f"  P50 production Y1 (kWh→MWh): {prod[0]:>12.4f} MWh")
        print(f"  Source check: 144MW×3535h/2 = {144 * 3535 / 2:>12.1f} MWh per semi-annual")
        print(f"  Δ Y1 production:             {prod[0] - (144 * 3535 / 2):>+12.1f} MWh")
    except Exception as e:
        print(f"  Production error: {e}")

    print("\n── Revenue ──────────────────────────────────────────────────────")
    try:
        rev = ops.revenue_keur
        print(f"  Revenue Y1 (kEUR):           {rev[0]:>14.4f}")
        print(f"  Revenue Y2 (kEUR):           {rev[1]:>14.4f}")
        print(f"  Revenue Y3 (kEUR):           {rev[2]:>14.4f}")
        print(f"  Total revenue (kEUR):        {sum(rev):>14.4f}")
    except Exception as e:
        print(f"  Revenue error: {e}")

    print("\n── OPEX / EBITDA ────────────────────────────────────────────────")
    try:
        opex = ops.opex_keur
        ebitda = ops.ebitda_keur
        print(f"  OPEX Y1 (kEUR):              {opex[0]:>14.4f}")
        print(f"  OPEX total (kEUR):           {sum(opex):>14.4f}")
        print(f"  EBITDA Y1 (kEUR):            {ebitda[0]:>14.4f}")
        print(f"  EBITDA total (kEUR):         {sum(ebitda):>14.4f}")
    except Exception as e:
        print(f"  OPEX/EBITDA error: {e}")

    print("\n── Tax ──────────────────────────────────────────────────────────")
    try:
        tc = pmr_a.tax_and_cfads
        cash_tax = tc.corporate_tax_cash_keur
        total_tax = sum(cash_tax)
        print(f"  Cash tax total (Finco):      {total_tax:>14.4f} kEUR")
        print(f"  Source authority:                95291.964024 kEUR")
        print(f"  Δ Cash tax:                  {total_tax - 95291.964024:>+14.4f} kEUR")
        print(f"  Classification: CLEAN_POLICY_VS_WORKBOOK_COMPATIBILITY")
    except Exception as e:
        print(f"  Tax error: {e}")

    print("\n── Base CFADS ───────────────────────────────────────────────────")
    try:
        psc = pmr_a.post_senior_cash
        base_cfads = psc.base_cfads_keur
        print(f"  Base CFADS Y1 (kEUR):        {base_cfads[0]:>14.4f}")
        print(f"  Source CF!H69:                    13218.427445 kEUR")
        print(f"  Base CFADS Y2 (kEUR):        {base_cfads[1]:>14.4f}")
        print(f"  Source CF!I69:                    13002.909606 kEUR")
    except Exception as e:
        print(f"  Base CFADS error: {e}")

    print("\n── Bank CFADS ───────────────────────────────────────────────────")
    try:
        ds = pmr_a.debt_sizing
        bank_cfads = ds.bank_cfads_keur
        # Find operating periods (skip construction)
        op_bank = [v for v in bank_cfads if v > 0]
        print(f"  Bank CFADS Y1 (kEUR):        {op_bank[0]:>14.4f}  (source: 11064.982)")
        print(f"  Bank CFADS Y2 (kEUR):        {op_bank[1]:>14.4f}  (source: 10884.575)")
        print(f"  Bank CFADS Y3 (kEUR):        {op_bank[2]:>14.4f}  (source: 11191.311)")
        print(f"  Binding constraint:          {pmr_a.senior_debt.binding_constraint}")
    except Exception as e:
        print(f"  Bank CFADS error: {e}")

    print("\n── Senior Debt Schedule ─────────────────────────────────────────")
    try:
        sd = pmr_a.senior_debt
        print(f"  Binding constraint:          {sd.binding_constraint}")
        senior_periods = list(sd.period_indices)
        print(f"  Senior period range:         {senior_periods[0]}..{senior_periods[-1]}")
        total_interest = _safe_sum(sd.interest_keur)
        total_principal = _safe_sum(sd.principal_keur)
        print(f"  Total senior principal (Finco): {total_principal:>12.6f} kEUR")
        print(f"  Source DS!D49:                    147150.442310 kEUR")
        print(f"  Δ Principal:                 {total_principal - 147150.442310339:>+12.6f} kEUR")
        print(f"  Total senior interest (Finco):  {total_interest:>12.6f} kEUR")
        print(f"  Source DS!D50:                     78848.801061 kEUR")
        print(f"  Δ Interest:                  {total_interest - 78848.801061344:>+12.6f} kEUR")
    except Exception as e:
        print(f"  Senior schedule error: {e}")

    print("\n── Base DSCR ────────────────────────────────────────────────────")
    try:
        dscr_vals = [wp.senior_dscr_base for wp in result_a.waterfall_periods if hasattr(wp, 'senior_dscr_base') and wp.senior_dscr_base is not None]
        if dscr_vals:
            avg_dscr = sum(dscr_vals) / len(dscr_vals)
            min_dscr = min(dscr_vals)
            print(f"  Avg Base DSCR (Finco):       {avg_dscr:>12.6f}x  (source: 1.859036x)")
            print(f"  Min Base DSCR (Finco):       {min_dscr:>12.6f}x  (source: 1.689000x)")
        else:
            print("  DSCR values not found on waterfall_periods")
    except Exception as e:
        print(f"  DSCR error: {e}")

    print("\n── SHL ──────────────────────────────────────────────────────────")
    try:
        shl = pmr_a.shareholder_loan
        # Construction PIK
        if hasattr(fr_a, 'shl_construction_pik_keur'):
            pik = fr_a.shl_construction_pik_keur
        else:
            pik = None
        print(f"  Construction PIK (Finco):    {pik if pik is not None else 'N/A':>14}  kEUR")
        print(f"  Source IDC!D51 (compound):        11340.658479 kEUR")
        print(f"  Simple counterfactual (dcf=2):    10904.479307 kEUR")
        print(f"  Gap (KUPI_SHL_CONSTRUCTION_COMPOUNDING_GAP): 436.179 kEUR")
        total_shl_principal = _safe_sum(shl.shl_principal_keur)
        total_shl_interest = _safe_sum(shl.shl_interest_cash_keur if hasattr(shl, 'shl_interest_cash_keur') else shl.shl_interest_keur)
        print(f"  Total SHL principal repaid (Finco): {total_shl_principal:>12.4f} kEUR")
        print(f"  Source DS!D124:                    79493.654145 kEUR")
        print(f"  Total SHL interest (Finco):  {total_shl_interest:>14.4f} kEUR")
        print(f"  Source DS!D122:                    48681.151164 kEUR")
        # SHL opening at first op period
        op_idx = list(shl.period_indices).index(2) if 2 in list(shl.period_indices) else 0
        shl_opening_idx = list(shl.period_indices).index(2) if 2 in list(shl.period_indices) else 0
        print(f"  SHL opening at period 2:     {shl.shl_opening_keur[shl_opening_idx]:>14.6f} kEUR")
        print(f"  Source first op opening:          79493.654145 kEUR")
    except Exception as e:
        print(f"  SHL error: {e}")

    print("\n── Sponsor Returns ──────────────────────────────────────────────")
    try:
        print(f"  pure_equity_xirr:            {result_a.pure_equity_xirr:.6%}")
        print(f"  total_sponsor_xirr:          {result_a.total_sponsor_xirr:.6%}")
        print(f"  pure_equity_moic:            {result_a.pure_equity_moic:.4f}x")
        print(f"  total_sponsor_moic:          {result_a.total_sponsor_moic:.4f}x")
        print(f"  Source Equity IRR:                17.136129%")
        print(f"  Source Gross Sponsor XIRR:        16.987158%")
        print(f"  Note: KUPI_SPONSOR_CONTRIBUTION_TIMING_POLICY_GAP applies —")
        print(f"        compare definitions before judging parity.")
    except Exception as e:
        print(f"  Returns error: {e}")

    print("\n── Run B: Source-effective CO2 diagnostic ───────────────────────")
    try:
        proj_b = create_kupi_project_source_effective_co2()
        result_b = _run(proj_b)
        fr_b = result_b.financing_result
        pmr_b = fr_b.project_model_result
        rev_a = sum(pmr_a.operating_schedules.revenue_keur)
        rev_b = sum(pmr_b.operating_schedules.revenue_keur)
        print(f"  Total revenue Run A (CO2-off): {rev_a:>12.4f} kEUR")
        print(f"  Total revenue Run B (CO2-on):  {rev_b:>12.4f} kEUR")
        print(f"  CO2 revenue bridge:            {rev_b - rev_a:>+12.4f} kEUR")
        print(f"  Source CO2 Y1 (CF!H35):            1075.477 kEUR")
        print(f"  Classification: SQ-02 SOURCE_INPUT_INCONSISTENCY bridge")
    except Exception as e:
        print(f"  Run B error: {e}")

    print("\n── Identity Invariance Check ────────────────────────────────────")
    try:
        proj_renamed = create_kupi_project(
            name="XYZ Arbitrary Wind LLC",
            company="Fictional BA SPV",
            code="FAKE99",
        )
        result_r = _run(proj_renamed)
        fr_r = result_r.financing_result
        senior_r = fr_r.final_senior_commitment_keur
        senior_a = fr_a.final_senior_commitment_keur
        identical = abs(senior_r - senior_a) < 1e-6
        print(f"  Senior (original):            {senior_a:.6f} kEUR")
        print(f"  Senior (renamed):             {senior_r:.6f} kEUR")
        print(f"  Identity invariant:           {'PASS' if identical else 'FAIL'}")
    except Exception as e:
        print(f"  Identity check error: {e}")

    print("\n" + "=" * 70)
    print("BLIND RUN COMPLETE — results above are pre-assertion evidence.")
    print("Do not tune KUPI inputs to match source anchors without proven input error.")
    print("=" * 70)


if __name__ == "__main__":
    main()
