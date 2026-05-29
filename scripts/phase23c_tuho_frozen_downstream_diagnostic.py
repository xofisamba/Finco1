"""
Phase 23C: TUHO Frozen Schedule Downstream Diagnostic.

Diagnostic/validation only — no factory opt-in enabled, no SHL redesign.
Validates SHL/distribution behavior when frozen senior debt schedule is enabled.

Key insight from Phase 23A:
  - use_frozen_excel_senior_debt_schedule=True + use_senior_debt_sizing_engine=True
    causes waterfall_core to use canonical debt_service_capacity_keur_by_period
    from the CSV fixture as senior_ds_keur directly (DSCR becomes backward-computed).
  - This changes cash after senior debt, which affects SHL service timing.

Constraint:
  - TUHO factory opt-in is DIAGNOSTIC ONLY here — recommend but do not enable.
  - Oborovo: no frozen fixture exists — diagnostic only.
  - No distribution while SHL outstanding: the lock-up rule must be validated.
"""
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.project_factories import create_default_tuho_wind1 as create_default_tuho, create_default_oborovo
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
from app.ui_runner import _build_period_engine


def run_tuho_default():
    """Run TUHO with frozen schedule flags OFF (default behavior)."""
    tuho = create_default_tuho()
    engine = _build_period_engine(tuho)
    config = WaterfallRunConfig.from_inputs(tuho, engine)
    # Ensure frozen schedule OFF
    config = WaterfallRunConfig(
        use_senior_debt_sizing_engine=False,
        use_frozen_excel_senior_debt_schedule=False,
        rate_per_period=config.rate_per_period,
        tenor_periods=config.tenor_periods,
        target_dscr=config.target_dscr,
        lockup_dscr=config.lockup_dscr,
        tax_rate=config.tax_rate,
        dsra_months=config.dsra_months,
        shl_amount_keur=config.shl_amount_keur,
        shl_rate=config.shl_rate,
        shl_idc_keur=config.shl_idc_keur,
        shl_repayment_method=config.shl_repayment_method,
        shl_tenor_years=config.shl_tenor_years,
        shl_wht_rate=config.shl_wht_rate,
        equity_irr_method=config.equity_irr_method,
        share_capital_keur=config.share_capital_keur,
        sculpt_capex_keur=config.sculpt_capex_keur,
        debt_sizing_method=config.debt_sizing_method,
        dscr_schedule=config.dscr_schedule,
        tuho_cit_cash_tax_start_operating_index=getattr(
            config, 'tuho_cit_cash_tax_start_operating_index', None
        ),
    )
    runner = WaterfallRunner(tuho, engine)
    return runner.run(config)


def run_tuho_frozen():
    """Run TUHO with frozen schedule flags ON (canonical capacity used)."""
    tuho = create_default_tuho()
    engine = _build_period_engine(tuho)
    config = WaterfallRunConfig.from_inputs(tuho, engine)
    # Enable frozen schedule (both flags must be True per Phase 23A)
    config = WaterfallRunConfig(
        use_senior_debt_sizing_engine=True,
        use_frozen_excel_senior_debt_schedule=True,
        rate_per_period=config.rate_per_period,
        tenor_periods=config.tenor_periods,
        target_dscr=config.target_dscr,
        lockup_dscr=config.lockup_dscr,
        tax_rate=config.tax_rate,
        dsra_months=config.dsra_months,
        shl_amount_keur=config.shl_amount_keur,
        shl_rate=config.shl_rate,
        shl_idc_keur=config.shl_idc_keur,
        shl_repayment_method=config.shl_repayment_method,
        shl_tenor_years=config.shl_tenor_years,
        shl_wht_rate=config.shl_wht_rate,
        equity_irr_method=config.equity_irr_method,
        share_capital_keur=config.share_capital_keur,
        sculpt_capex_keur=config.sculpt_capex_keur,
        debt_sizing_method=config.debt_sizing_method,
        dscr_schedule=config.dscr_schedule,
        tuho_cit_cash_tax_start_operating_index=getattr(
            config, 'tuho_cit_cash_tax_start_operating_index', None
        ),
    )
    runner = WaterfallRunner(tuho, engine)
    return runner.run(config)


def run_oborovo_default():
    """Run Oborovo with frozen schedule flags OFF (default behavior)."""
    oborovo = create_default_oborovo()
    engine = _build_period_engine(oborovo)
    config = WaterfallRunConfig.from_inputs(oborovo, engine)
    config = WaterfallRunConfig(
        use_senior_debt_sizing_engine=False,
        use_frozen_excel_senior_debt_schedule=False,
        rate_per_period=config.rate_per_period,
        tenor_periods=config.tenor_periods,
        target_dscr=config.target_dscr,
        lockup_dscr=config.lockup_dscr,
        tax_rate=config.tax_rate,
        dsra_months=config.dsra_months,
        shl_amount_keur=config.shl_amount_keur,
        shl_rate=config.shl_rate,
        shl_idc_keur=config.shl_idc_keur,
        shl_repayment_method=config.shl_repayment_method,
        shl_tenor_years=config.shl_tenor_years,
        shl_wht_rate=config.shl_wht_rate,
        equity_irr_method=config.equity_irr_method,
        share_capital_keur=config.share_capital_keur,
        sculpt_capex_keur=config.sculpt_capex_keur,
        debt_sizing_method=config.debt_sizing_method,
        dscr_schedule=config.dscr_schedule,
        tuho_cit_cash_tax_start_operating_index=getattr(
            config, 'tuho_cit_cash_tax_start_operating_index', None
        ),
    )
    runner = WaterfallRunner(oborovo, engine)
    return runner.run(config)


def compare_periods(result_default, result_frozen, period_indices):
    """Print diagnostic table for specified period indices."""
    print(f"\n{'Idx':>4} {'Mode':>8} {'SeniorDS':>12} {'CFADS':>12} {'SHLInt':>10} {'SHLBal':>12} {'Dist':>10} {'DSCR':>8}")
    print("-" * 90)
    for idx in period_indices:
        p_def = result_default.periods[idx]
        p_frz = result_frozen.periods[idx]
        for label, p in [("DEFAULT", p_def), ("FROZEN", p_frz)]:
            print(
                f"{idx:>4} {label:>8} "
                f"{p.senior_ds_keur:>12.1f} "
                f"{p.cf_after_reserves_keur:>12.1f} "
                f"{p.shl_interest_keur:>10.1f} "
                f"{p.shl_balance_keur:>12.1f} "
                f"{p.distribution_keur:>10.1f} "
                f"{p.dscr:>8.4f}"
            )
        print()


def check_lockup(result):
    """Check if distribution is non-zero while SHL principal balance is positive."""
    issues = []
    for i, p in enumerate(result.periods):
        shl_outstanding = (
            getattr(p, 'shl_balance_keur', 0.0) > 0
            or getattr(p, 'shl_gross_accrued_interest_keur', 0.0) > 0
        )
        if shl_outstanding and getattr(p, 'distribution_keur', 0.0) > 0:
            issues.append((
                i,
                getattr(p, 'period', f"P{i}"),
                getattr(p, 'shl_balance_keur', 0.0),
                getattr(p, 'shl_gross_accrued_interest_keur', 0.0),
                getattr(p, 'distribution_keur', 0.0),
            ))
    return issues


def check_dist_leak(result):
    """Check for distribution leak: dist > 0 while SHL balance > 0."""
    leaks = []
    for i, p in enumerate(result.periods):
        shl_bal = getattr(p, 'shl_balance_keur', 0.0)
        dist = getattr(p, 'distribution_keur', 0.0)
        if shl_bal > 0 and dist > 0:
            leaks.append((i, getattr(p, 'period', f"P{i}"), shl_bal, dist))
    return leaks


def check_shl_negative(result):
    """Check for negative SHL closing balance."""
    issues = []
    for i, p in enumerate(result.periods):
        bal = getattr(p, 'shl_balance_keur', 0.0)
        if bal < 0:
            issues.append((i, getattr(p, 'period', f"P{i}"), bal))
    return issues


if __name__ == "__main__":
    print("=" * 90)
    print("Phase 23C — TUHO Frozen Schedule Downstream Diagnostic")
    print("=" * 90)

    # -------------------------------------------------------------------------
    # TUHO DEFAULT (frozen OFF)
    # -------------------------------------------------------------------------
    print("\n=== TUHO DEFAULT RUN (frozen schedule OFF) ===")
    try:
        result_default = run_tuho_default()
        print(f"Total periods: {len(result_default.periods)}")
        first_dist = next(
            (i for i, p in enumerate(result_default.periods)
             if getattr(p, 'distribution_keur', 0) > 0), None
        )
        print(f"First distribution period index: {first_dist}")
        print(f"_frozen_senior_ds_wired: {getattr(result_default, '_frozen_senior_ds_wired', 'N/A')}")
    except Exception as e:
        print(f"ERROR running TUHO default: {e}")
        import traceback; traceback.print_exc()
        result_default = None

    # -------------------------------------------------------------------------
    # TUHO FROZEN (frozen ON)
    # -------------------------------------------------------------------------
    print("\n=== TUHO FROZEN SCHEDULE RUN (frozen schedule ON) ===")
    try:
        result_frozen = run_tuho_frozen()
        print(f"Total periods: {len(result_frozen.periods)}")
        first_dist_frozen = next(
            (i for i, p in enumerate(result_frozen.periods)
             if getattr(p, 'distribution_keur', 0) > 0), None
        )
        print(f"First distribution period index: {first_dist_frozen}")
        print(f"_frozen_senior_ds_wired: {getattr(result_frozen, '_frozen_senior_ds_wired', 'N/A')}")
    except Exception as e:
        print(f"ERROR running TUHO frozen: {e}")
        import traceback; traceback.print_exc()
        result_frozen = None

    # -------------------------------------------------------------------------
    # OBOROVO DEFAULT
    # -------------------------------------------------------------------------
    print("\n=== OBOROVO DEFAULT RUN ===")
    try:
        result_oborovo = run_oborovo_default()
        print(f"Total periods: {len(result_oborovo.periods)}")
        first_dist_ob = next(
            (i for i, p in enumerate(result_oborovo.periods)
             if getattr(p, 'distribution_keur', 0) > 0), None
        )
        print(f"First distribution period index: {first_dist_ob}")
    except Exception as e:
        print(f"ERROR running Oborovo default: {e}")
        import traceback; traceback.print_exc()
        result_oborovo = None

    # -------------------------------------------------------------------------
    # TUHO COMPARISON
    # -------------------------------------------------------------------------
    if result_default and result_frozen:
        print("\n=== TUHO COMPARISON (P1, P2, P4, P6, P12) ===")
        compare_periods(result_default, result_frozen, [0, 1, 3, 5, 11])

        # Senior DS change check
        p4_def = result_default.periods[3].senior_ds_keur
        p4_frz = result_frozen.periods[3].senior_ds_keur
        print(f"\n=== SENIOR DS AT P4 (idx=3) ===")
        print(f"  DEFAULT: {p4_def:.1f} kEUR")
        print(f"  FROZEN:  {p4_frz:.1f} kEUR")
        print(f"  Changed: {abs(p4_def - p4_frz) > 0.01}")

        # Revenue unchanged check
        rev_def = result_default.periods[1].revenue_keur
        rev_frz = result_frozen.periods[1].revenue_keur
        print(f"\n=== REVENUE AT P2 (idx=1) ===")
        print(f"  DEFAULT: {rev_def:.1f} kEUR")
        print(f"  FROZEN:  {rev_frz:.1f} kEUR")
        print(f"  Unchanged: {abs(rev_def - rev_frz) < 0.01}")

        # OPEX unchanged check
        opx_def = result_default.periods[1].opex_keur
        opx_frz = result_frozen.periods[1].opex_keur
        print(f"\n=== OPEX AT P2 (idx=1) ===")
        print(f"  DEFAULT: {opx_def:.1f} kEUR")
        print(f"  FROZEN:  {opx_frz:.1f} kEUR")
        print(f"  Unchanged: {abs(opx_def - opx_frz) < 0.01}")

    # -------------------------------------------------------------------------
    # TUHO LOCKUP CHECKS
    # -------------------------------------------------------------------------
    if result_frozen:
        print("\n=== TUHO FROZEN: DISTRIBUTION LOCKUP CHECK ===")
        lockup_issues = check_lockup(result_frozen)
        print(f"Distribution while SHL outstanding: {len(lockup_issues)} issues")
        for issue in lockup_issues[:5]:
            print(f"  idx={issue[0]}, period={issue[1]}, shl_bal={issue[2]:.1f}, "
                  f"shl_accrued={issue[3]:.1f}, dist={issue[4]:.1f}")

        print("\n=== TUHO FROZEN: DISTRIBUTION LEAK CHECK ===")
        dist_leaks = check_dist_leak(result_frozen)
        print(f"Distribution leak (dist>0 while SHL bal>0): {len(dist_leaks)} issues")
        for leak in dist_leaks[:5]:
            print(f"  idx={leak[0]}, period={leak[1]}, shl_bal={leak[2]:.1f}, dist={leak[3]:.1f}")

        print("\n=== TUHO FROZEN: SHL NEGATIVE BALANCE CHECK ===")
        shl_neg = check_shl_negative(result_frozen)
        print(f"Negative SHL balance periods: {len(shl_neg)}")
        for n in shl_neg[:5]:
            print(f"  idx={n[0]}, period={n[1]}, shl_bal={n[2]:.1f}")

        print("\n=== TUHO FROZEN: FIRST DIST AFTER SHL CLEARED ===")
        first_dist_idx = next(
            (i for i, p in enumerate(result_frozen.periods)
             if getattr(p, 'distribution_keur', 0) > 0), None
        )
        if first_dist_idx is not None:
            all_cleared = all(
                getattr(result_frozen.periods[i], 'shl_balance_keur', 0) == 0
                for i in range(first_dist_idx)
            )
            print(f"First dist at idx={first_dist_idx}")
            print(f"All prior SHL balances = 0: {all_cleared}")
        else:
            print("No distributions found")

    # -------------------------------------------------------------------------
    # OBOROVO LEAK CHECK
    # -------------------------------------------------------------------------
    if result_oborovo:
        print("\n=== OBOROVO DEFAULT: DISTRIBUTION LEAK CHECK ===")
        dist_leaks_ob = check_dist_leak(result_oborovo)
        print(f"Distribution leak (dist>0 while SHL bal>0): {len(dist_leaks_ob)} issues")
        for leak in dist_leaks_ob[:5]:
            print(f"  idx={leak[0]}, period={leak[1]}, shl_bal={leak[2]:.1f}, dist={leak[3]:.1f}")

        print("\n=== OBOROVO DEFAULT: SHL NEGATIVE BALANCE CHECK ===")
        shl_neg_ob = check_shl_negative(result_oborovo)
        print(f"Negative SHL balance periods: {len(shl_neg_ob)}")
        for n in shl_neg_ob[:5]:
            print(f"  idx={n[0]}, period={n[1]}, shl_bal={n[2]:.1f}")

    print("\n" + "=" * 90)
    print("Phase 23C diagnostic complete.")
    print("=" * 90)