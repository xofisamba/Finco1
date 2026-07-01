"""Thin wrapper around run_demo_project for API use."""
from app.ui_runner import run_demo_project
from app.output_tables import build_waterfall_table, build_revenue_table, build_debt_table, build_returns_table, aggregate_period_table_annual


def _period_label(period) -> str:
    """Build a human-readable period label from the backend period object."""
    year_index = getattr(period, "year_index", None)
    period_in_year = getattr(period, "period_in_year", None)
    period_number = getattr(period, "period", None)

    if year_index is not None and period_in_year is not None:
        return f"Y{int(year_index)}-H{int(period_in_year)}"
    if period_number is not None:
        return f"P{int(period_number)}"
    return "Selected period"


def _build_runtime_derivation_evidence(result, project_inputs=None):
    """Return read-only derivation evidence sourced from WaterfallResult."""
    operation_periods = [
        period
        for period in getattr(result, "periods", [])
        if getattr(period, "is_operation", False)
    ]
    dscr_periods = [
        period
        for period in getattr(result, "periods", [])
        if getattr(period, "is_operation", False) and float(getattr(period, "senior_ds_keur", 0.0) or 0.0) > 0.0
    ]
    if not operation_periods:
        return {}

    operation_period_count = len(operation_periods)
    representative_operation_period = min(operation_periods, key=lambda period: getattr(period, "period", 0))
    total_cfads = sum(float(getattr(period, "cf_after_tax_keur", 0.0) or 0.0) for period in dscr_periods)
    total_senior_ds = sum(float(getattr(period, "senior_ds_keur", 0.0) or 0.0) for period in dscr_periods)

    capex = getattr(project_inputs, "capex", None)
    capex_items_attr = getattr(capex, "capex_items", None)
    capex_items = capex_items_attr() if callable(capex_items_attr) else ()

    evidence = {
        "senior_debt": {},
        "capex": {
            "display_value_keur": getattr(capex, "total_capex", None),
            "summary_method": (
                "CAPEX Total is sourced from the authoritative CAPEX structure used by the backend run. "
                "When upstream user sub-line materialization or scenario overrides are present, this displayed total "
                "reflects that authoritative structure."
            ),
            "authoritative_source": "CapexStructure.total_capex",
            "category_count": len(capex_items),
            "hierarchy_source": "CapexStructure named fields surfaced through capex.capex_items().",
            "audit_source": "ProjectInputs.capex.total_capex and ProjectInputs.capex.capex_items()",
        },
        "revenue": {
            "display_value_keur": getattr(result, "total_revenue_keur", None),
            "summary_method": "Total revenue from backend operating periods.",
            "period_formula": "Revenue_t = WaterfallPeriod.revenue_keur",
            "period_count": operation_period_count,
            "sample_period_label": _period_label(representative_operation_period),
            "sample_generation_mwh": getattr(representative_operation_period, "generation_mwh", None),
            "sample_revenue_keur": getattr(representative_operation_period, "revenue_keur", None),
            "audit_source": "WaterfallResult.total_revenue_keur and WaterfallResult.periods[].revenue_keur, generation_mwh",
        },
        "ebitda": {
            "display_value_keur": getattr(result, "total_ebitda_keur", None),
            "summary_method": "Total EBITDA from backend operating periods.",
            "period_formula": "EBITDA_t = Revenue_t - OPEX_t",
            "period_count": operation_period_count,
            "sample_period_label": _period_label(representative_operation_period),
            "sample_revenue_keur": getattr(representative_operation_period, "revenue_keur", None),
            "sample_opex_keur": getattr(representative_operation_period, "opex_keur", None),
            "sample_ebitda_keur": getattr(representative_operation_period, "ebitda_keur", None),
            "audit_source": "WaterfallResult.total_ebitda_keur and WaterfallResult.periods[].revenue_keur, opex_keur, ebitda_keur",
        },
        "opex": {
            "display_value_keur": getattr(result, "total_opex_keur", None),
            "summary_method": "Total OPEX from backend operating periods.",
            "period_formula": "OPEX_t = WaterfallPeriod.opex_keur",
            "period_count": operation_period_count,
            "sample_period_label": _period_label(representative_operation_period),
            "sample_opex_keur": getattr(representative_operation_period, "opex_keur", None),
            "audit_source": "WaterfallResult.total_opex_keur and WaterfallResult.periods[].opex_keur",
        },
    }

    sample_senior_balance = getattr(representative_operation_period, "senior_balance_keur", None)
    sample_senior_principal = getattr(representative_operation_period, "senior_principal_keur", None)
    sample_senior_interest = getattr(representative_operation_period, "senior_interest_keur", None)
    sample_senior_ds = getattr(representative_operation_period, "senior_ds_keur", None)
    if sample_senior_balance is not None and sample_senior_principal is not None:
        evidence["senior_debt"] = {
            "display_value_keur": float(sample_senior_balance or 0.0) + float(sample_senior_principal or 0.0),
            "summary_method": (
                "Opening senior debt amount from backend operating-period debt schedule evidence. "
                "The displayed amount is anchored to the first operating-period senior balance and principal repayment fields."
            ),
            "period_count": operation_period_count,
            "sample_period_label": _period_label(representative_operation_period),
            "sample_senior_interest_keur": sample_senior_interest,
            "sample_senior_principal_keur": sample_senior_principal,
            "sample_senior_debt_service_keur": sample_senior_ds,
            "audit_source": (
                "WaterfallResult.periods[].senior_balance_keur, senior_principal_keur, "
                "senior_interest_keur, senior_ds_keur"
            ),
        }
    if not dscr_periods:
        return evidence

    representative_dscr_period = min(dscr_periods, key=lambda period: getattr(period, "period", 0))
    evidence.update({
        "dscr": {
            "display_value": getattr(result, "actual_avg_dscr", None),
            "summary_method": "Average of operating-period DSCR values with positive senior debt service.",
            "period_formula": "DSCR_t = CFADS_t / Senior Debt Service_t",
            "period_count": len(dscr_periods),
            "total_cfads_keur": total_cfads,
            "total_senior_debt_service_keur": total_senior_ds,
            "sample_period_label": _period_label(representative_dscr_period),
            "sample_cfads_keur": getattr(representative_dscr_period, "cf_after_tax_keur", None),
            "sample_senior_debt_service_keur": getattr(representative_dscr_period, "senior_ds_keur", None),
            "sample_dscr": getattr(representative_dscr_period, "dscr", None),
            "audit_source": "WaterfallResult.periods[].cf_after_tax_keur, senior_ds_keur, dscr",
        },
        "cfads": {
            "display_value_keur": total_cfads,
            "summary_method": "Total CFADS across operating periods with positive senior debt service.",
            "period_formula": "CFADS_t = WaterfallPeriod.cf_after_tax_keur",
            "period_count": len(dscr_periods),
            "sample_period_label": _period_label(representative_dscr_period),
            "sample_ebitda_keur": getattr(representative_dscr_period, "ebitda_keur", None),
            "sample_tax_keur": getattr(representative_dscr_period, "tax_keur", None),
            "sample_cfads_keur": getattr(representative_dscr_period, "cf_after_tax_keur", None),
            "audit_source": "WaterfallResult.periods[].cf_after_tax_keur (supporting fields shown: ebitda_keur, tax_keur)",
        },
    })
    return evidence


def _sanitize_df(df):
    """Replace inf/nan floats in a DataFrame with None for JSON safety.

    Uses astype(object).replace() rather than map() because pandas map()
    silently drops inf values without actually replacing them when the
    dtype is float64.
    """
    return df.astype(object).replace({float('inf'): None, float('-inf'): None, float('nan'): None})


def run_project(project_type: str, scenario: str, period_view: str = "Semiannual",
               project_inputs_override=None, use_dualrun_validation: bool = False):
    demo = run_demo_project(project_type, scenario,
                            project_inputs_override=project_inputs_override,
                            use_dualrun_validation=use_dualrun_validation)
    result = demo.result

    # Build tables
    wf = build_waterfall_table(result)
    rev = build_revenue_table(result)
    debt = build_debt_table(result)
    returns = build_returns_table(result)

    if period_view == "Annual":
        wf = aggregate_period_table_annual(wf)
        rev = aggregate_period_table_annual(rev)
        debt = aggregate_period_table_annual(debt)

    # Sanitize inf/nan (e.g. DSCR col has inf when debt is fully repaid)
    wf = _sanitize_df(wf)
    rev = _sanitize_df(rev)
    debt = _sanitize_df(debt)
    returns = _sanitize_df(returns)

    # Phase D1: assemble financial statements from the already-computed waterfall result.
    # assemble_financial_statements() is an offline assembly step — no new financial
    # calculations are performed here; it reads from WaterfallResult.periods fields that
    # run_waterfall() already computed. waterfall_core.py does NOT import this module
    # (separation of concerns verified by test_excel_parity_characterization.py C8).
    financial_statements_payload = None
    try:
        from domain.financial_statements import assemble_financial_statements
        fs = assemble_financial_statements(result)
        financial_statements_payload = _serialize_financial_statements(fs)
    except Exception:
        # FS assembly failure must never break the run path; degrade gracefully.
        financial_statements_payload = None

    # Phase E2: assemble senior debt schedule from the already-computed waterfall result.
    # _serialize_debt_schedule() reads per-period fields already computed by the waterfall
    # engine. No new financial calculations are performed here.
    debt_schedule_payload = None
    try:
        debt_schedule_payload = _serialize_debt_schedule(result)
    except Exception:
        # Debt schedule serialization failure must never break the run path.
        debt_schedule_payload = None

    # Phase F2: assemble tax schedule from the already-computed waterfall result.
    # _serialize_tax_schedule() reads per-period fields already computed by the waterfall
    # engine. No new financial calculations are performed here.
    tax_schedule_payload = None
    try:
        tax_schedule_payload = _serialize_tax_schedule(result)
    except Exception:
        # Tax schedule serialization failure must never break the run path.
        tax_schedule_payload = None

    # Phase G1: assemble distribution schedule from the already-computed waterfall result.
    # _serialize_distribution_schedule() reads per-period fields already computed by the
    # waterfall engine. No new financial calculations are performed here.
    distribution_schedule_payload = None
    try:
        distribution_schedule_payload = _serialize_distribution_schedule(result)
    except Exception:
        # Distribution schedule serialization failure must never break the run path.
        distribution_schedule_payload = None

    # Phase H2: call the Sponsor engine AFTER the waterfall completes.
    # project_runner.py calls the Sponsor engine's public interface — standard dependency
    # direction (runner calls engine). Neither engine is modified. No circular imports.
    # _serialize_sponsor_schedule() reads from SponsorCashflowResult / SponsorIrrResult /
    # SponsorMoicResult — no new sponsor economics are computed here.
    sponsor_schedule_payload = None
    try:
        sponsor_result = _run_sponsor_engine(result, demo.project_inputs, project_type)
        if sponsor_result is not None:
            sponsor_schedule_payload = _serialize_sponsor_schedule(*sponsor_result)
    except Exception:
        # Sponsor engine failure must never break the run path; degrade gracefully.
        sponsor_schedule_payload = None

    return {
        "project_type": project_type,
        "scenario": scenario,
        "period_view": period_view,
        "integration_status": getattr(demo, 'integration_status', 'full'),
        "integration_note": getattr(demo, 'integration_note', None),
        "messages": getattr(demo, 'messages', []),
        "debt_schedule": debt_schedule_payload,
        "tax_schedule": tax_schedule_payload,
        "distribution_schedule": distribution_schedule_payload,
        "kpis": {
            "total_capex_keur": getattr(getattr(demo, "project_inputs", None), "capex", None).total_capex if getattr(getattr(demo, "project_inputs", None), "capex", None) is not None else None,
            "total_revenue_keur": result.total_revenue_keur,
            "total_ebitda_keur": result.total_ebitda_keur,
            "total_opex_keur": getattr(result, 'total_opex_keur', None),
            "total_distributions_keur": getattr(result, 'total_distribution_keur', None),
            "project_irr": result.project_irr,
            "equity_irr": result.equity_irr,
            "min_dscr": result.actual_min_dscr,
            "avg_dscr": result.actual_avg_dscr,
        },
        "dualrun_validation": getattr(result, '_dualrun_validation', None),
        "derivation_evidence": _build_runtime_derivation_evidence(result, demo.project_inputs),
        "financial_statements": financial_statements_payload,
        "sponsor_schedule": sponsor_schedule_payload,
        "tables": {
            "waterfall": wf.to_dict(orient="records"),
            "revenue": rev.to_dict(orient="records"),
            "debt": debt.to_dict(orient="records"),
            "returns": returns.to_dict(orient="records"),
        }
    }


def _serialize_financial_statements(fs) -> dict:
    """Serialize FinancialStatementsResult to a JSON-safe dict for sessionStorage.

    Phase D1: read-only serialization of already-assembled engine output.
    No financial calculations are performed here.

    Structure returned:
      {
        "pnl": {"periods": [...], "row_labels": {...}},
        "balance_sheet": {"periods": [...]},
        "pf_cash_waterfall": {"periods": [...]},
      }
    """
    def _fmt_date(d):
        return d.isoformat() if d else None

    def _f(v):
        """Round to 2dp for display; handle non-finite values."""
        try:
            f = float(v)
            if f != f or abs(f) == float("inf"):
                return None
            return round(f, 2)
        except (TypeError, ValueError):
            return None

    # P&L periods — subset of fields for UI display
    pnl_periods = []
    for p in fs.pnl.periods:
        pnl_periods.append({
            "period": p.period,
            "date": _fmt_date(p.date),
            "year_index": p.year_index,
            "period_in_year": p.period_in_year,
            "revenues_keur": _f(p.revenues_keur),
            "operating_expenses_keur": _f(p.operating_expenses_keur),
            "depreciation_keur": _f(p.depreciation_keur),
            "ebit_keur": _f(p.ebit_keur),
            "senior_interest_expense_keur": _f(p.senior_interest_expense_keur),
            "shl_interest_expense_keur": _f(p.shl_interest_expense_keur),
            "earnings_before_tax_keur": _f(p.earnings_before_tax_keur),
            "cit_accrual_keur": _f(p.cit_accrual_keur),
            "net_income_keur": _f(p.net_income_keur),
            "retained_earnings_keur": _f(p.retained_earnings_keur),
            "net_dividends_keur": _f(p.net_dividends_keur),
        })

    # Balance sheet periods
    bs_periods = []
    for p in fs.balance_sheet.periods:
        bs_periods.append({
            "period_index": p.period_index,
            "date": _fmt_date(p.date),
            "net_fixed_assets_keur": _f(p.net_fixed_assets_keur),
            "dsra_balance_keur": _f(p.dsra_balance_keur),
            "cash_keur": _f(p.cash_keur),
            "total_assets_keur": _f(p.total_assets_keur),
            "share_capital_keur": _f(p.share_capital_keur),
            "retained_earnings_keur": _f(p.retained_earnings_keur),
            "shl_balance_keur": _f(p.shl_balance_keur),
            "senior_balance_keur": _f(p.senior_balance_keur),
            "total_liabilities_equity_keur": _f(p.total_liabilities_equity_keur),
            "balance_check_keur": _f(p.balance_check_keur),
        })

    # PF Cash Waterfall periods
    pf_periods = []
    for p in fs.pf_cash_waterfall.periods:
        pf_periods.append({
            "period_index": p.period_index,
            "date": _fmt_date(p.date),
            "revenue_cash_keur": _f(p.revenue_cash_keur),
            "opex_cash_keur": _f(p.opex_cash_keur),
            "ebitda_cash_keur": _f(p.ebitda_cash_keur),
            "cash_tax_keur": _f(p.cash_tax_keur),
            "fcf_banks_keur": _f(p.fcf_banks_keur),
            "senior_total_ds_keur": _f(p.senior_total_ds_keur),
            "dsra_funding_keur": _f(p.dsra_funding_keur),
            "dsra_release_keur": _f(p.dsra_release_keur),
            "fcf_junior_keur": _f(p.fcf_junior_keur),
            "fcf_for_distribution_keur": _f(p.fcf_for_distribution_keur),
            "net_dividends_keur": _f(p.net_dividends_keur),
        })

    return {
        "pnl": {"periods": pnl_periods},
        "balance_sheet": {"periods": bs_periods},
        "pf_cash_waterfall": {"periods": pf_periods},
        "source": "assemble_financial_statements(WaterfallResult)",
    }


def _serialize_debt_schedule(result) -> dict:
    """Serialize the senior debt schedule from WaterfallResult to a JSON-safe dict.

    Phase E2/E5: read-only serialization of already-computed engine output.
    No financial calculations are performed here — only reads fields already
    set by the waterfall engine on each WaterfallPeriod.

    Structure returned:
      {
        "periods": [
          {
            "period": int,
            "date": str (ISO),
            "year_index": int,
            "period_in_year": int,
            "is_operation": bool,
            "senior_balance_keur": float | None,
            "senior_principal_keur": float | None,
            "senior_interest_keur": float | None,
            "senior_ds_keur": float | None,
            "dscr": float | None,
            "dsra_balance_keur": float | None,
            "dsra_contribution_keur": float | None,
          },
          ...
        ],
        "summary": {
          "total_senior_ds_keur": float | None,
          "actual_min_dscr": float | None,
          "actual_avg_dscr": float | None,
          "target_dscr": float | None,
        },
        "source": "WaterfallResult.periods (per-period engine output)",
      }
    """
    def _fmt_date(d):
        return d.isoformat() if d else None

    def _f(v):
        """Round to 2dp for display; handle non-finite values."""
        try:
            f = float(v)
            if f != f or abs(f) == float("inf"):
                return None
            return round(f, 2)
        except (TypeError, ValueError):
            return None

    periods_out = []
    for p in getattr(result, "periods", []):
        periods_out.append({
            "period": getattr(p, "period", None),
            "date": _fmt_date(getattr(p, "date", None)),
            "year_index": getattr(p, "year_index", None),
            "period_in_year": getattr(p, "period_in_year", None),
            "is_operation": bool(getattr(p, "is_operation", False)),
            "senior_balance_keur": _f(getattr(p, "senior_balance_keur", None)),
            "senior_principal_keur": _f(getattr(p, "senior_principal_keur", None)),
            "senior_interest_keur": _f(getattr(p, "senior_interest_keur", None)),
            "senior_ds_keur": _f(getattr(p, "senior_ds_keur", None)),
            "dscr": _f(getattr(p, "dscr", None)),
            "dsra_balance_keur": _f(getattr(p, "dsra_balance_keur", None)),
            "dsra_contribution_keur": _f(getattr(p, "dsra_contribution_keur", None)),
        })

    return {
        "periods": periods_out,
        "summary": {
            "total_senior_ds_keur": _f(getattr(result, "total_senior_ds_keur", None)),
            "actual_min_dscr": _f(getattr(result, "actual_min_dscr", None)),
            "actual_avg_dscr": _f(getattr(result, "actual_avg_dscr", None)),
            "target_dscr": _f(getattr(result, "target_dscr", None)),
        },
        "source": "WaterfallResult.periods (per-period engine output)",
    }


def _serialize_tax_schedule(result) -> dict:
    """Serialize the tax schedule from WaterfallResult to a JSON-safe dict.

    Phase F2: read-only serialization of already-computed engine output.
    No financial calculations are performed here — only reads fields already
    set by the waterfall engine on each WaterfallPeriod.

    Structure returned:
      {
        "periods": [
          {
            "period": int,
            "date": str (ISO),
            "year_index": int,
            "period_in_year": int,
            "is_operation": bool,
            "taxable_profit_keur": float | None,
            "tax_keur": float | None,
            "cf_after_tax_keur": float | None,
            "corporate_tax_cash_keur": float | None,
            "tax_depreciation_audit_keur": float | None,
            "taxable_income_before_losses_audit_keur": float | None,
            "tax_loss_opening_audit_keur": float | None,
            "tax_loss_used_audit_keur": float | None,
            "tax_loss_closing_audit_keur": float | None,
            "taxable_profit_after_losses_audit_keur": float | None,
            "cit_accrual_audit_keur": float | None,
            "cash_tax_current_period_audit_keur": float | None,
          },
          ...
        ],
        "summary": {
          "total_tax_keur": float | None,
        },
        "source": "WaterfallResult.periods (per-period engine output)",
      }
    """
    def _fmt_date(d):
        return d.isoformat() if d else None

    def _f(v):
        """Round to 2dp for display; handle non-finite values."""
        try:
            f = float(v)
            if f != f or abs(f) == float("inf"):
                return None
            return round(f, 2)
        except (TypeError, ValueError):
            return None

    periods_out = []
    for p in getattr(result, "periods", []):
        periods_out.append({
            "period": getattr(p, "period", None),
            "date": _fmt_date(getattr(p, "date", None)),
            "year_index": getattr(p, "year_index", None),
            "period_in_year": getattr(p, "period_in_year", None),
            "is_operation": bool(getattr(p, "is_operation", False)),
            "taxable_profit_keur": _f(getattr(p, "taxable_profit_keur", None)),
            "tax_keur": _f(getattr(p, "tax_keur", None)),
            "cf_after_tax_keur": _f(getattr(p, "cf_after_tax_keur", None)),
            "corporate_tax_cash_keur": _f(getattr(p, "corporate_tax_cash_keur", None)),
            "tax_depreciation_audit_keur": _f(getattr(p, "tax_depreciation_audit_keur", None)),
            "taxable_income_before_losses_audit_keur": _f(getattr(p, "taxable_income_before_losses_audit_keur", None)),
            "tax_loss_opening_audit_keur": _f(getattr(p, "tax_loss_opening_audit_keur", None)),
            "tax_loss_used_audit_keur": _f(getattr(p, "tax_loss_used_audit_keur", None)),
            "tax_loss_closing_audit_keur": _f(getattr(p, "tax_loss_closing_audit_keur", None)),
            "taxable_profit_after_losses_audit_keur": _f(getattr(p, "taxable_profit_after_losses_audit_keur", None)),
            "cit_accrual_audit_keur": _f(getattr(p, "cit_accrual_audit_keur", None)),
            "cash_tax_current_period_audit_keur": _f(getattr(p, "cash_tax_current_period_audit_keur", None)),
        })

    return {
        "periods": periods_out,
        "summary": {
            "total_tax_keur": _f(getattr(result, "total_tax_keur", None)),
        },
        "source": "WaterfallResult.periods (per-period engine output)",
    }


def _serialize_distribution_schedule(result) -> dict:
    """Serialize the distribution schedule from WaterfallResult to a JSON-safe dict.

    Phase G1: read-only serialization of already-computed engine output.
    No financial calculations are performed here — only reads fields already
    set by the waterfall engine on each WaterfallPeriod.

    Structure returned:
      {
        "periods": [...],
        "summary": {...},
        "source": "WaterfallResult.periods (per-period engine output)",
      }
    """
    def _fmt_date(d):
        return d.isoformat() if d else None

    def _f(v):
        """Round to 2dp for display; handle non-finite values."""
        try:
            f = float(v)
            if f != f or abs(f) == float("inf"):
                return None
            return round(f, 2)
        except (TypeError, ValueError):
            return None

    periods_out = []
    for p in getattr(result, "periods", []):
        periods_out.append({
            "period": getattr(p, "period", None),
            "date": _fmt_date(getattr(p, "date", None)),
            "year_index": getattr(p, "year_index", None),
            "period_in_year": getattr(p, "period_in_year", None),
            "is_operation": bool(getattr(p, "is_operation", False)),
            "distribution_keur": _f(getattr(p, "distribution_keur", None)),
            "cash_sweep_keur": _f(getattr(p, "cash_sweep_keur", None)),
            "cum_distribution_keur": _f(getattr(p, "cum_distribution_keur", None)),
            "lockup_active": bool(getattr(p, "lockup_active", False)),
            "cf_after_reserves_keur": _f(getattr(p, "cf_after_reserves_keur", None)),
            "dsra_balance_keur": _f(getattr(p, "dsra_balance_keur", None)),
            "dsra_contribution_keur": _f(getattr(p, "dsra_contribution_keur", None)),
            "mra_balance_keur": _f(getattr(p, "mra_balance_keur", None)),
            "mra_contribution_keur": _f(getattr(p, "mra_contribution_keur", None)),
            "legacy_distribution_keur": _f(getattr(p, "legacy_distribution_keur", None)),
            "da_paid_distribution_keur": _f(getattr(p, "da_paid_distribution_keur", None)),
            "distribution_source": getattr(p, "distribution_source", "") or "",
            "distribution_wiring_delta_keur": _f(getattr(p, "distribution_wiring_delta_keur", None)),
        })

    return {
        "periods": periods_out,
        "summary": {
            "total_distribution_keur": _f(getattr(result, "total_distribution_keur", None)),
            "legacy_distribution_keur": _f(getattr(result, "legacy_distribution_keur", None)),
            "da_paid_distribution_keur": _f(getattr(result, "da_paid_distribution_keur", None)),
            "distribution_source": getattr(result, "distribution_source", "") or "",
            "distribution_wiring_delta_keur": _f(getattr(result, "distribution_wiring_delta_keur", None)),
        },
        "source": "WaterfallResult.periods (per-period engine output)",
    }


# ── Phase H2: Sponsor engine bridge ──────────────────────────────────────────

# Capital structure constants per project type.
# These mirror the constants in app/sponsor_project_adapter.py.
_SPONSOR_CAPITAL_STRUCTURES = {
    "TUHO": {
        "lp_commitment_keur": 400.0,
        "gp_commitment_keur": 100.0,
        "ownership": {"LP-1": 0.80, "GP-1": 0.20},
        "hurdle_rate_pa": 0.08,
        "gp_promote_share": 0.20,
        "compounding_convention": "SEMIANNUAL",
    },
    "Oborovo": {
        "lp_commitment_keur": 400.0,
        "gp_commitment_keur": 100.0,
        "ownership": {"LP-1": 0.80, "GP-1": 0.20},
        "hurdle_rate_pa": 0.08,
        "gp_promote_share": 0.20,
        "compounding_convention": "SEMIANNUAL",
    },
}


def _run_sponsor_engine(waterfall_result, project_inputs, project_type: str):
    """Call the Sponsor engine after the waterfall completes.

    Phase H2: This is a thin bridge that calls the Sponsor engine's public interface
    from project_runner. No engine internals are modified. No circular imports.
    Only wired for projects with a known capital structure (TUHO, Oborovo).

    Returns (cashflow_result, irr_result, moic_result) tuple, or None if not wired.
    """
    cap_struct = _SPONSOR_CAPITAL_STRUCTURES.get(project_type)
    if cap_struct is None:
        return None

    from app.sponsor_runner import SponsorRunConfig, run_sponsor_waterfall
    from domain.sponsor.sponsor_cashflow_runner import (
        SponsorCashflowRunnerInputs,
        run_sponsor_cashflows,
    )
    from domain.sponsor.sponsor_irr_runner import (
        SponsorIrrRunnerInputs,
        SponsorMoicRunnerInputs,
        run_sponsor_irr,
        run_sponsor_moic,
    )
    from domain.sponsor.equity_injection import EquityInjection

    # Extract SPV distributions from the completed waterfall result.
    # WaterfallResult.periods[].distribution_keur is the per-period equity distribution.
    spv_distributions = tuple(
        float(getattr(p, "distribution_keur", 0.0) or 0.0)
        for p in getattr(waterfall_result, "periods", [])
    )
    num_periods = len(spv_distributions)
    if num_periods == 0:
        return None

    # Build equity injections from capital structure.
    # Total equity = lp + gp, injected at period 0.
    total_equity = cap_struct["lp_commitment_keur"] + cap_struct["gp_commitment_keur"]
    equity_injections = (
        EquityInjection(
            period_index=0,
            amount_keur=total_equity,
            investor_id="SPONSOR-1",
            target_entity="SPV",
            purpose="equityContribution",
        ),
    )

    # Build SponsorCashflowRunnerInputs.
    # holdco_dividend_by_period and holdco_opex_by_period are set to zero
    # (we are at SPV level, not HoldCo; the cashflow is the SPV distribution).
    cashflow_inputs = SponsorCashflowRunnerInputs(
        investor_id="SPONSOR-1",
        entity_code="SPV",
        equity_injections=equity_injections,
        holdco_distribution_by_period=spv_distributions,
        holdco_dividend_by_period=tuple(0.0 for _ in range(num_periods)),
        wht_rate=0.0,
        holdco_opex_by_period=tuple(0.0 for _ in range(num_periods)),
        period_count=num_periods,
    )

    cashflow_result = run_sponsor_cashflows(cashflow_inputs)

    # Compute IRR and MOIC from the cashflow result.
    irr_result = run_sponsor_irr(SponsorIrrRunnerInputs(sponsor_result=cashflow_result))
    moic_result = run_sponsor_moic(SponsorMoicRunnerInputs(sponsor_result=cashflow_result))

    return cashflow_result, irr_result, moic_result


def _serialize_sponsor_schedule(cashflow_result, irr_result, moic_result) -> dict:
    """Serialize sponsor engine results to a JSON-safe dict for sessionStorage.

    Phase H2: read-only serialization of already-computed engine output.
    No sponsor economic calculations are performed here — only reads fields
    from SponsorCashflowResult, SponsorIrrResult, SponsorMoicResult.

    Structure returned:
      {
        "periods": [
          {
            "period_index": int,
            "equity_injected_keur": float | None,
            "distribution_received_keur": float | None,
            "wht_on_distribution_keur": float | None,
            "net_cashflow_keur": float | None,
            "capital_account_balance_keur": float | None,
          },
          ...
        ],
        "summary": {
          "total_equity_injected_keur": float | None,
          "total_distributions_received_keur": float | None,
          "total_wht_keur": float | None,
          "total_net_cashflow_keur": float | None,
          "gross_sponsor_return_multiple": float | None,
          "gross_sponsor_irr": float | None,
          "gross_sponsor_moic": float | None,
          "xirr_converged": bool,
          "investor_id": str,
          "entity_code": str,
        },
        "source": "SponsorCashflowRunner + SponsorIrrRunner + SponsorMoicRunner",
      }
    """
    def _f(v):
        """Round to 2dp for display; handle non-finite values."""
        try:
            f = float(v)
            if f != f or abs(f) == float("inf"):
                return None
            return round(f, 2)
        except (TypeError, ValueError):
            return None

    periods_out = []
    for p in getattr(cashflow_result, "period_results", []):
        periods_out.append({
            "period_index": getattr(p, "period_index", None),
            "equity_injected_keur": _f(getattr(p, "equity_injected_keur", None)),
            "distribution_received_keur": _f(getattr(p, "distribution_received_keur", None)),
            "wht_on_distribution_keur": _f(getattr(p, "wht_on_distribution_keur", None)),
            "net_cashflow_keur": _f(getattr(p, "net_cashflow_keur", None)),
            "capital_account_balance_keur": _f(getattr(p, "capital_account_balance_keur", None)),
        })

    # IRR from SponsorIrrResult
    gross_irr = getattr(irr_result, "gross_sponsor_irr", None)
    xirr_converged = bool(getattr(irr_result, "xirr_converged", False))

    # MOIC from SponsorMoicResult
    gross_moic = getattr(moic_result, "gross_sponsor_moic", None)

    return {
        "periods": periods_out,
        "summary": {
            "total_equity_injected_keur": _f(getattr(cashflow_result, "total_equity_injected_keur", None)),
            "total_distributions_received_keur": _f(getattr(cashflow_result, "total_distributions_received_keur", None)),
            "total_wht_keur": _f(getattr(cashflow_result, "total_wht_keur", None)),
            "total_net_cashflow_keur": _f(getattr(cashflow_result, "total_net_cashflow_keur", None)),
            "gross_sponsor_return_multiple": _f(getattr(cashflow_result, "gross_sponsor_return_multiple", None)),
            "gross_sponsor_irr": _f(gross_irr),
            "gross_sponsor_moic": _f(gross_moic),
            "xirr_converged": xirr_converged,
            "investor_id": getattr(cashflow_result, "investor_id", ""),
            "entity_code": getattr(cashflow_result, "entity_code", ""),
        },
        "source": "SponsorCashflowRunner + SponsorIrrRunner + SponsorMoicRunner",
    }
