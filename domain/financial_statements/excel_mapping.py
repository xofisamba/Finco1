"""Excel row mappings for the offline P&L assembly."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExcelRowMapping:
    row_code: str
    row_number: int
    label: str
    field_name: str
    source_owner: str
    sign_convention: str
    notes: str = ""


PNL_ROW_MAPPINGS: tuple[ExcelRowMapping, ...] = (
    ExcelRowMapping("R8", 8, "Revenues", "revenues_keur", "WaterfallPeriod.revenue_keur", "positive income"),
    ExcelRowMapping("R10", 10, "Operating expenses", "operating_expenses_keur", "WaterfallPeriod.opex_keur", "negative expense"),
    ExcelRowMapping("R11", 11, "Local tax", "local_tax_keur", "placeholder", "negative expense", "Not exposed in runtime P&L source yet."),
    ExcelRowMapping("R12", 12, "WHT on interests", "wht_on_interests_keur", "placeholder", "negative expense", "Not exposed in runtime P&L source yet."),
    ExcelRowMapping("R13", 13, "Depreciation", "depreciation_keur", "WaterfallPeriod.tax_depreciation_audit_keur", "negative expense"),
    ExcelRowMapping("R14", 14, "Total expenses", "total_expenses_keur", "assembled", "negative expense subtotal"),
    ExcelRowMapping("R16", 16, "EBIT", "ebit_keur", "assembled", "positive or negative result"),
    ExcelRowMapping("R19", 19, "Interests from reserve accounts", "interest_from_reserve_accounts_keur", "placeholder", "positive income"),
    ExcelRowMapping("R20", 20, "Interests from cash", "interest_from_cash_keur", "placeholder", "positive income"),
    ExcelRowMapping("R21", 21, "WHT on financing revenues", "wht_on_financing_revenues_keur", "placeholder", "negative expense"),
    ExcelRowMapping("R24", 24, "Senior interests", "senior_interest_expense_keur", "WaterfallPeriod.senior_interest_keur", "negative expense"),
    ExcelRowMapping("R25", 25, "Refinancing interest", "refinancing_interest_keur", "placeholder", "negative expense"),
    ExcelRowMapping("R26", 26, "Junior interest", "junior_interest_keur", "placeholder", "negative expense"),
    ExcelRowMapping("R27", 27, "SHL interest", "shl_interest_expense_keur", "WaterfallPeriod.shl_interest_keur", "negative expense"),
    ExcelRowMapping("R28", 28, "Interests on cash", "interest_on_cash_keur", "placeholder", "positive income"),
    ExcelRowMapping("R30", 30, "Financial earnings", "financial_earnings_keur", "assembled", "positive or negative subtotal"),
    ExcelRowMapping("R32", 32, "EBT", "earnings_before_tax_keur", "assembled", "positive or negative result"),
    ExcelRowMapping("R34", 34, "Fiscal reintegration", "fiscal_reintegration_keur", "WaterfallPeriod.fiscal_reintegration_audit_keur", "positive taxable add-back"),
    ExcelRowMapping("R35", 35, "Taxable income", "taxable_income_before_losses_keur", "WaterfallPeriod.taxable_income_before_losses_audit_keur", "positive or zero audit value"),
    ExcelRowMapping("R36", 36, "Losses N-1", "losses_n_1_keur", "WaterfallPeriod.tax_loss_opening_audit_keur", "negative balance presentation"),
    ExcelRowMapping("R37", 37, "Allocated losses", "allocated_losses_keur", "WaterfallPeriod.tax_loss_used_audit_keur", "positive loss utilization"),
    ExcelRowMapping("R38", 38, "Losses N", "losses_n_keur", "WaterfallPeriod.tax_loss_closing_audit_keur", "negative balance presentation"),
    ExcelRowMapping("R39", 39, "Carriable losses", "carriable_losses_keur", "WaterfallPeriod.tax_loss_closing_audit_keur", "negative balance presentation"),
    ExcelRowMapping("R41", 41, "Taxable profit N", "taxable_profit_after_losses_keur", "WaterfallPeriod.taxable_profit_after_losses_audit_keur", "positive taxable profit"),
    ExcelRowMapping("R43", 43, "CIT accrual", "cit_accrual_keur", "WaterfallPeriod.cit_accrual_audit_keur", "negative expense presentation"),
    ExcelRowMapping("R44", 44, "Cash tax diagnostic", "cash_tax_excel_style_h2_diagnostic_keur", "WaterfallPeriod.cash_tax_excel_style_h2_diagnostic_keur", "negative cash outflow diagnostic"),
    ExcelRowMapping("R46", 46, "Net income", "net_income_keur", "assembled", "positive or negative result"),
    ExcelRowMapping("R48", 48, "Legal reserve", "legal_reserve_keur", "placeholder", "negative appropriation"),
    ExcelRowMapping("R49", 49, "Retained earnings", "retained_earnings_keur", "assembled", "cumulative balance"),
    ExcelRowMapping("R50", 50, "Net dividends", "net_dividends_keur", "WaterfallPeriod.distribution_keur", "negative distribution presentation"),
)

PNL_ROW_BY_CODE = {mapping.row_code: mapping for mapping in PNL_ROW_MAPPINGS}
PNL_ROW_BY_FIELD = {mapping.field_name: mapping for mapping in PNL_ROW_MAPPINGS}
