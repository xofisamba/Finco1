"""finco_recon.catalog — Line item catalog for the Oborovo reconciliation workbook."""
from __future__ import annotations

from dataclasses import dataclass

CLASSIFICATIONS = (
    "MATCH",
    "PYTHON BUG",
    "EXCEL BUG",
    "POLICY DIFFERENCE",
    "UNRESOLVED SOURCE",
    "TIMING / ROUNDING",
    "OUT OF CLEAN ENGINE SCOPE",
)


@dataclass(frozen=True)
class LineItem:
    code: str               # e.g. "CF.01"
    section: str            # e.g. "CFADS", "OPEX"
    name: str               # human-readable label
    unit: str               # "kEUR", "MWh", "%", "x", "MW", etc.
    excel_field: str | None         # attribute name on ExcelData (None = not in Excel fixture)
    engine_field: str | None        # attribute name on EngineData (None = not in engine)
    in_clean_engine: bool = True    # False → OUT OF CLEAN ENGINE SCOPE
    default_classification: str = "MATCH"


# ---------------------------------------------------------------------------
# CATALOG
# ---------------------------------------------------------------------------
CATALOG: list[LineItem] = [
    # TIMELINE
    LineItem("TL.01", "TIMELINE", "Period index",          "index", None, "period_index"),
    LineItem("TL.02", "TIMELINE", "Period end date",       "date",  None, "period_end"),
    LineItem("TL.03", "TIMELINE", "Days in period",        "days",  None, "days_in_period"),
    LineItem("TL.04", "TIMELINE", "Day fraction",          "frac",  None, "day_fraction"),
    LineItem("TL.05", "TIMELINE", "Is operation",          "flag",  None, "is_operation"),

    # PRODUCTION
    LineItem("PR.01", "PRODUCTION", "Net production (engine)",   "MWh", None,              "production_mwh"),
    LineItem("PR.02", "PRODUCTION", "Net production (Excel)",    "MWh", None,              None,
             in_clean_engine=False, default_classification="UNRESOLVED SOURCE"),

    # REVENUE
    LineItem("RV.01", "REVENUE", "Operating revenues (CF)",  "kEUR", "revenue_keur",    "revenue_keur"),
    LineItem("RV.02", "REVENUE", "Total revenues (P&L)",     "kEUR", "pl_revenue_keur", "revenue_keur"),

    # OPEX
    LineItem("OP.00", "OPEX", "Total OPEX",                  "kEUR", "opex_keur",       "opex_keur"),
    LineItem("OP.01", "OPEX", "B.01 Technical Management",   "kEUR", None,              "opex_b01_keur"),
    LineItem("OP.02", "OPEX", "B.02 Infrastructure Maint.",  "kEUR", None,              "opex_b02_keur"),
    LineItem("OP.03", "OPEX", "B.03 Maintain Site",          "kEUR", None,              "opex_b03_keur"),
    LineItem("OP.04", "OPEX", "B.04 Clean Material",         "kEUR", None,              "opex_b04_keur"),
    LineItem("OP.05", "OPEX", "B.05 Security",               "kEUR", None,              "opex_b05_keur"),
    LineItem("OP.06", "OPEX", "B.06 Insurance",              "kEUR", None,              "opex_b06_keur"),
    LineItem("OP.07", "OPEX", "B.07 Lease & Property Tax",   "kEUR", None,              "opex_b07_keur"),
    LineItem("OP.08", "OPEX", "B.08 Power Expenses",         "kEUR", None,              "opex_b08_keur"),
    LineItem("OP.09", "OPEX", "B.09 Fees",                   "kEUR", None,              "opex_b09_keur"),
    LineItem("OP.10", "OPEX", "B.10 Audit & Accounting",     "kEUR", None,              "opex_b10_keur"),
    LineItem("OP.11", "OPEX", "B.11 Bank Fees",              "kEUR", None,              "opex_b11_keur"),
    LineItem("OP.12", "OPEX", "B.12 Environmental & Social", "kEUR", None,              "opex_b12_keur"),
    LineItem("OP.13", "OPEX", "B.13 Contingencies",          "kEUR", None,              "opex_b13_keur"),
    LineItem("OP.14", "OPEX", "B.14 Taxes",                  "kEUR", None,              "opex_b14_keur"),
    LineItem("OP.15", "OPEX", "B.15 Salary & Payroll",       "kEUR", None,              "opex_b15_keur"),

    # EBITDA
    LineItem("EB.01", "EBITDA", "EBITDA",                    "kEUR", "ebitda_keur",     "ebitda_keur"),

    # CAPEX (scalar, not per-period)
    LineItem("CA.00", "CAPEX", "Total Hard CAPEX",           "kEUR", None,              None),
    LineItem("CA.01", "CAPEX", "C.01 EPC Contract",          "kEUR", None,              None),
    LineItem("CA.02", "CAPEX", "C.02 Production Units",      "kEUR", None,              None),
    LineItem("CA.03", "CAPEX", "C.03 Other EPC",             "kEUR", None,              None),
    LineItem("CA.04", "CAPEX", "C.04 Grid Connection",       "kEUR", None,              None),
    LineItem("CA.05", "CAPEX", "C.05 Operations Prep.",      "kEUR", None,              None),
    LineItem("CA.06", "CAPEX", "C.06 Insurances",            "kEUR", None,              None),
    LineItem("CA.07", "CAPEX", "C.07 Lease & Property Tax",  "kEUR", None,              None),
    LineItem("CA.08", "CAPEX", "C.08 Construction Mgmt A",   "kEUR", None,              None),
    LineItem("CA.09", "CAPEX", "C.09 Commissioning",         "kEUR", None,              None),
    LineItem("CA.10", "CAPEX", "C.10 Audit & Legal",         "kEUR", None,              None),
    LineItem("CA.11", "CAPEX", "C.11 Construction Mgmt B",   "kEUR", None,              None),
    LineItem("CA.12", "CAPEX", "C.12 Contingencies",         "kEUR", None,              None),
    LineItem("CA.13", "CAPEX", "C.13 Taxes & Duties",        "kEUR", None,              None),
    LineItem("CA.14", "CAPEX", "C.14 Project Acquisition",   "kEUR", None,              None),
    LineItem("CA.15", "CAPEX", "C.15 Project Rights",        "kEUR", None,              None),
    LineItem("CA.16", "CAPEX", "IDC (Bank interest)",        "kEUR", None,              None),
    LineItem("CA.17", "CAPEX", "SHL IDC capitalised",        "kEUR", None,              None,
             in_clean_engine=False, default_classification="OUT OF CLEAN ENGINE SCOPE"),

    # DEPRECIATION
    LineItem("DP.01", "DEPRECIATION", "Book depreciation",           "kEUR", "depreciation_keur", "book_depreciation_keur"),
    LineItem("DP.02", "DEPRECIATION", "Tax depreciation (Python)",   "kEUR", None,                "tax_depreciation_keur"),
    LineItem("DP.03", "DEPRECIATION", "Cumulated depreciation (Excel)", "kEUR", None,             None,
             in_clean_engine=False, default_classification="UNRESOLVED SOURCE"),

    # TAX
    LineItem("TX.01", "TAX", "Taxable profit (EBITDA basis)",  "kEUR", None,                    "taxable_profit_keur"),
    LineItem("TX.02", "TAX", "P&L taxable income (Excel)",     "kEUR", "taxable_income_keur",   "taxable_profit_keur"),
    LineItem("TX.03", "TAX", "Tax loss opening",               "kEUR", None,                    "tax_loss_opening_keur"),
    LineItem("TX.04", "TAX", "Tax loss used",                  "kEUR", None,                    "tax_loss_used_keur"),
    LineItem("TX.05", "TAX", "Tax loss closing",               "kEUR", None,                    "tax_loss_closing_keur"),
    LineItem("TX.06", "TAX", "CIT accrual (P&L)",              "kEUR", "pl_cit_keur",           "tax_keur"),
    LineItem("TX.07", "TAX", "Cash tax paid",                  "kEUR", "cash_tax_keur",         "corporate_tax_cash_keur"),

    # CFADS
    LineItem("CF.01", "CFADS", "CFADS (free cash flow for banks)", "kEUR", "cfads_keur",              "cfads_keur"),
    LineItem("CF.02", "CFADS", "Earnings before tax (Excel P&L)",  "kEUR", "earnings_before_tax_keur", None,
             in_clean_engine=False, default_classification="OUT OF CLEAN ENGINE SCOPE"),

    # SENIOR DEBT
    LineItem("SD.01", "SENIOR_DEBT", "Opening senior debt",     "kEUR", None,                   "sd_opening_keur"),
    LineItem("SD.02", "SENIOR_DEBT", "Senior interest (DS)",    "kEUR", "senior_interest_keur", "sd_interest_keur"),
    LineItem("SD.03", "SENIOR_DEBT", "Senior principal",        "kEUR", "senior_principal_keur","sd_principal_keur"),
    LineItem("SD.04", "SENIOR_DEBT", "Senior debt service",     "kEUR", "senior_ds_keur",       "sd_ds_keur"),
    LineItem("SD.05", "SENIOR_DEBT", "Closing senior debt",     "kEUR", None,                   "sd_closing_keur"),
    LineItem("SD.06", "SENIOR_DEBT", "DSCR (period average)",   "x",    "avg_dscr",             "sd_dscr"),
    LineItem("SD.07", "SENIOR_DEBT", "Senior interest (P&L)",   "kEUR", "pl_senior_interest_keur", "sd_interest_keur"),

    # SHL
    LineItem("SH.01", "SHL", "Opening SHL",      "kEUR", None,              None,
             in_clean_engine=False, default_classification="OUT OF CLEAN ENGINE SCOPE"),
    LineItem("SH.02", "SHL", "SHL gross interest","kEUR", "shl_interest_keur", None,
             in_clean_engine=False, default_classification="OUT OF CLEAN ENGINE SCOPE"),
    LineItem("SH.03", "SHL", "Closing SHL",       "kEUR", None,              None,
             in_clean_engine=False, default_classification="OUT OF CLEAN ENGINE SCOPE"),

    # CASH FLOW
    LineItem("FC.01", "CASHFLOW", "Free cash flow for distribution", "kEUR", "free_cash_flow_keur", None,
             in_clean_engine=False, default_classification="OUT OF CLEAN ENGINE SCOPE"),
    LineItem("FC.02", "CASHFLOW", "Net dividends (Excel P&L)",       "kEUR", "net_dividends_keur",  None,
             in_clean_engine=False, default_classification="OUT OF CLEAN ENGINE SCOPE"),
    LineItem("FC.03", "CASHFLOW", "DSRA contribution",               "kEUR", None,                  None,
             in_clean_engine=False, default_classification="OUT OF CLEAN ENGINE SCOPE"),
]


def get_catalog_by_section() -> dict[str, list[LineItem]]:
    result: dict[str, list[LineItem]] = {}
    for item in CATALOG:
        result.setdefault(item.section, []).append(item)
    return result


def get_item(code: str) -> LineItem | None:
    for item in CATALOG:
        if item.code == code:
            return item
    return None
