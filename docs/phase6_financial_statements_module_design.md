# Phase 6 — Financial Statements + PF Cash Waterfall Module Design

**Branch:** phase6-financial-statements-module-design
**Base:** main
**Status:** Design only. Docs-only PR. No runtime change.

---

## 0. Purpose

This document defines the architecture for a Financial Statements + Project Finance Cash Waterfall module grounded directly in the TUHO and Oborovo Excel models. The objective is **parity-grade reconstruction** of the Excel statement structure as a generic, reusable engine.

The module fills a gap that prior Phase 7 calibration work surfaced: residual R99/R102, tax timing, and depreciation/EBT differences cannot be cleanly explained through waterfall audit fields alone because they originate in **accounting and tax statement logic** that the codebase does not yet formalize.

---

## 1. Excel Logical Statement Reconstruction

### 1.1 Sheet inventory (TUHO and Oborovo, identical structure)

| Sheet | Role | Type |
|---|---|---|
| **P&L** | Profit & Loss statement | Accounting |
| **BS** | Balance Sheet | Accounting |
| **CF** | Project-finance operating cash waterfall (NOT statutory CF) | PF Cash Waterfall |
| **DS** | Debt Service schedule (senior + SHL) | Engine input/output |
| **Dep** | Depreciation schedule (book + tax) | Engine input/output |
| **OpEx** | OPEX line-item schedule | Engine input |
| **CapEx** | CAPEX schedule | Engine input |
| **IDC** | Interest During Construction calculation | Engine input/output |
| **Eq** | Equity / sponsor returns | Output |
| **Inputs/Scenarios/Macro/Flags** | Drivers, scenarios, switches | Inputs |
| **Outputs/FID deck/Cash@Risk** | Reporting overlays | Reporting |

The four statement-relevant sheets are **P&L, BS, CF, DS**. The Dep and IDC sheets feed both P&L (book/tax depreciation) and CF (cash interest/principal). OpEx and CapEx feed P&L and CF.

### 1.2 Reconstructed logical P&L (TUHO row map, op_idx 0)

```
R8   Total Revenues                      = 4,061.0
R10  Operating expenses (OPEX engine)    =  -990.8
R11  Local Tax                           =     0.0
R12  Withholding Tax on Interests        =     0.0
R13  Depreciation (book basis)           = -1,845.4
R14  Total Expenses (R10+R11+R12+R13)    = -2,836.3
R16  EBIT = R8 + R14                     =  1,224.7

R19  Interests from Reserve Accounts     =     0.0  (financing revenues)
R20  Interests from Cash                 =     0.0
R21  Withholding Tax on financing rev    =     0.0

R24  Senior Interests                    = -1,297.1
R25  Senior Refinancing Interest         =     0.0
R26  Junior Interest                     =     0.0
R27  Shareholder Loan Interests          = -1,297.4  (full gross, before reintegration)
R28  Interests on Cash                   =     0.0

R30  Financial Earnings (financ rev - exp) = -2,594.5
R32  Earnings before tax (EBT) = R16 + R30 = -1,369.7

R34  Fiscal Reintegration                =     0.0  (depends on thin-cap rules)
R35  Taxable Income = R32 + R34          = -1,369.7
R36  Losses N-1 (carried in)             = -3,568.7
R37  Allocated losses (used this period) =     0.0  (Y1 negative; nothing to use)
R38  Losses N (cumulative losses end)    = -3,568.7
R39  Carriable losses (capped if rule)   = -3,568.7
R41  Taxable Profit N (after losses)     = -1,369.7
R43  Corporate Income Tax (CIT)          =     0.0  (negative taxable → no tax)
R44  Corporate Income Tax (cash)         =     0.0
R46  Net Income = R32 - R44              = -1,369.7
R48  Legal reserve                       =     0.0  (NI<0)
R49  Retained Earnings (cumulative)      = -1,369.7
R50  Net Dividends                       =     0.0
```

**Key observations:**

1. **SHL interest is fully expensed at gross level** (R27 = -1,297.4 = full gross interest of 1,641 reduced for WHT-related items elsewhere; cross-checks with DS R63 + R125).
2. **Fiscal Reintegration** (R34) is where thin-capitalization rules ADD BACK non-deductible SHL interest to taxable income. In op_idx 0 it's zero because there's no profit to deduct against. Will become positive in profit years.
3. **Loss carry-forward** is a 5-year rolling mechanism per Croatian tax law (TUHO/Oborovo are CEE projects). Rows R36-R41 implement this.
4. **CIT** (R43-R44) is accrued ONLY on positive taxable profit AFTER loss allocation. Negative taxable income → CIT = 0.
5. **Dividends** (R50) is the link to PF cash waterfall — actual distribution comes from CF R119, but the dividend declaration shows up on P&L for retained-earnings tracking.

### 1.3 Reconstructed logical Balance Sheet (TUHO row map, op_idx 0)

```
ASSETS
R8   Gross Fixed Assets                 = 72,993.7  (CapEx total at COD)
R9   Accumulated Depreciation           =  1,845.4  (period contribution)
R10  Total Fixed Assets (net)           = 71,148.3  (R8 - R9 cumulative)
R12  DSRA                               =      0.0
R13  J-DSRA                             =      0.0
R14  Distribution Account               =      0.0
R15  Cash                               =      0.0
R17  Total Assets                       = 71,148.3

LIABILITIES + EQUITY
R21  Capital at Financial close         =    500.0
R22  Legal Reserve                      =      0.0
R23  Retained Earnings (cumulative)     = -4,938.4  (incl. construction-period loss)
R24  Shareholder Loan                   = 33,047.5  (incl. PIK accumulation)
R25  Akuo Carbon Fund / junior          =      0.0
R26  Senior Debt                        = 42,539.3  (after first principal repayment)
R29  Short term loan                    =      0.0
R31  Total Liabilities + Equity         = 71,148.3
R33  Balance check                      =      0.0  ✓ closes
```

**Key observations:**

1. **Balance Sheet closes period-by-period** — `R33 Balance check = 0` is the proof of accounting integrity.
2. **Retained Earnings carries cumulatively** from period to period. At op_idx 0 it already shows -4,938.4 which is the construction-period accumulated loss (mostly construction-period SHL interest + small construction depreciation that doesn't yet exist as P&L; this is implicit).
3. **DSRA, J-DSRA, Distribution Account, Cash** are all balance sheet items that move via the PF Cash Waterfall (CF sheet), NOT directly via P&L. They appear here because the BS must reconcile.
4. **Senior Debt and Shareholder Loan** are balance-side line items whose movements come from the DS sheet (period principal repayment + period PIK addition for SHL).

### 1.4 Reconstructed PF Cash Waterfall (TUHO CF sheet — KEY ROWS)

The CF sheet is **NOT** a classical statutory cash flow statement. It's an operating-cash priority waterfall.

```
TOP: Operating cash sources
R20  Operating Revenues                 = 4,061.0  (= P&L R8)
R36  CO2 / Carbon revenues              =   142.0  (subset of revenues)
R38  Operating Expenses                 =  -990.8  (= P&L R10)
R40  EBITDA = R20 + R38                 = 3,070.2

R63  Cash interests on senior debt      = -1,297.1
R66  Cash interests revenues / minor    =     0.0
R67  Corporate Income Tax (cash)        =     0.0  (NOT same as P&L R44 if timing differs)

R69  FCF Banks = SUM(R20, R38, R63, R66, R67) + B70*(year=0)
                                        = 1,773.0  (cash available for senior DS)

R70  Senior Debt Service (principal+int) = -2,116.4
R75-R90  DSRA / J-DSRA movements        =     0.0  (DSRA=0 for TUHO)

R84  FCF after senior + reserves         = -343.4 (= R69 + R70 + R82 reserve)
R85  Junior debt service                 =    0.0
R96  Other cash adjustments              =    0.0
R98  Distribution account (pre-lockup)   = R84 + R85 + R96 + R100[prev]

R99  FCF available for SHL / dividends   (after lockup gate)
                                         = if(lockup_met AND year>=N): R98, else: 0
R100 R98 - R99 (cash held in distrib account / forward)
R102 = R99  (FCF for SHL waterfall input — IDENTICAL to R99)

R104 Net SHL cash outflow                = -82,486 total
R106 FCF for dividends = R99 + R104      = 152,259 total (gross dividends before WHT)
R119 Net Dividends (after WHT)            = 151,709 total
```

**Critical insight:** R99 = R102 = "FCF available before SHL". This was confirmed empirically in Phase 7F. The PF cash waterfall has a single distinct "cash available for SHL waterfall" row that some models split into multiple labels for documentation but holds the same value.

### 1.5 Tax bridge logic (Dep + P&L R32→R44)

```
Step 1: Book depreciation (Dep sheet)
  - linear over 30 years on full Gross Fixed Assets
  - feeds P&L R13

Step 2: EBT = EBIT + Financial Earnings (P&L R32)

Step 3: Fiscal Reintegration (P&L R34)
  - Thin-cap rule: max SHL interest deductible = X% of EBITDA  (R56-R59)
  - Non-deductible SHL interest is ADDED BACK to taxable income
  - For TUHO/Oborovo this is mostly 0 in loss years, kicks in once profitable

Step 4: Taxable Income = EBT + Reintegration (R35)

Step 5: Loss carry-forward (R36-R41)
  - Croatian tax: 5-year rolling carry-forward
  - "Losses N-1" = brought-forward losses (opening)
  - "Allocated losses" = max(0, min(Losses_N-1, Taxable_Income_N))
  - "Losses N" = Losses_N-1 - Allocated + max(0, -Taxable_Income_N)
  - "Carriable losses" = Losses_N capped at 5-year rolling window

Step 6: Taxable Profit N (R41) = Taxable Income N - Allocated losses

Step 7: CIT = max(0, Taxable Profit N × CIT rate)
  - TUHO is Croatian → 18% (was 20% pre-2024)
  - Oborovo same regime

Step 8: Cash CIT timing (R67 in CF)
  - Croatia CIT: annual payment in H2 of following year
  - Excel R67 lags P&L R44 by approximately 12 months
  - Tax engine must distinguish ACCRUED CIT (P&L) from CASH CIT (CF)
```

This is precisely the **structural** gap that Phase 7 calibration could not close with audit fields alone. Python currently computes cash CIT correctly at the magnitude level (~±2.2% of Excel total) but with different per-period timing.

### 1.6 Distribution-account flow (CF R98, R99, R100)

```
R98 Distribution Account (pre-lockup, opening of waterfall):
   = R84 (FCF after senior) + R85 (junior DS) + R96 (other) + R100[t-1]
   where R100[t-1] = forward-carried amount from previous period

R99 Gate logic:
   if (DSCR < lockup_DSCR) OR
      (year < min_distribution_year) OR
      (R98 < 0) OR
      (DSRA_end < DSRA_target):
        R99 = 0
   else:
        R99 = R98

R100 = R98 - R99 (residual held in distribution account, carried forward)

R102 = R99  (input to SHL waterfall)
```

The distribution-account is a **financial-engineering construct**, not an accounting one. It's a virtual buffer that holds blocked cash from periods where dividend lockup conditions are unmet, and releases it later. It is NOT a tax-driven concept.

---

## 2. Excel-to-Engine Mapping Matrix

| Excel Sheet/Row | Meaning | Current Python source | Future engine owner | Source of truth |
|---|---|---|---|---|
| P&L R8 Revenues | Total operating revenue | `revenue_engine` | `revenue_engine` (kept) | Runtime |
| P&L R10 OPEX | Total operating expenses | `opex_engine` (line-item or legacy) | `opex_engine` (kept) | Runtime |
| P&L R13 Depreciation | Book depreciation expense | `app/depreciation_engine.py` | `domain/financial_statements/pnl.py` | Runtime — relocate to domain |
| P&L R24 Senior Interest | Senior interest expense (P&L) | `waterfall_engine.py` (sculpting) | `domain/financial_statements/pnl.py` (read from senior schedule) | Audit (derived from DS sheet) |
| P&L R27 SHL Interest | Full gross SHL interest | `shl_fcf_waterfall` or pik_then_sweep | `domain/financial_statements/pnl.py` (read from SHL ledger) | Audit (derived from SHL ledger) |
| P&L R32 EBT | Earnings before tax | not computed | `domain/financial_statements/pnl.py` | New (derived) |
| P&L R34 Fiscal Reintegration | Thin-cap reintegration | `domain/tax/reintegration.py` (partial) | `domain/tax/reintegration.py` (formalize) | Runtime — already domain |
| P&L R35 Taxable Income | After reintegration | not formalized | `domain/financial_statements/tax_bridge.py` | New |
| P&L R36-R41 Loss carry-fwd | Loss roll-forward (5y rolling) | `tax_engine` partial (`prior_tax_loss_keur`) | `domain/financial_statements/tax_bridge.py` | New — replaces flat `prior_tax_loss_keur` |
| P&L R44 CIT | Accrued CIT | `tax_engine` (annual) | `domain/financial_statements/tax_bridge.py` | Runtime — relocate accrued |
| P&L R46 Net Income | Final NI | not computed | `domain/financial_statements/pnl.py` | New (derived) |
| P&L R49 Retained Earnings | Cumulative RE | not computed | `domain/financial_statements/balance_sheet.py` | New (derived) |
| BS R8 Gross Fixed Assets | Capex closing | `construction_engine` outputs | `domain/financial_statements/balance_sheet.py` | Audit (derived from CapEx) |
| BS R10 Net Fixed Assets | After accumulated dep | not computed | `domain/financial_statements/balance_sheet.py` | New (derived) |
| BS R12-R14 Reserves/Distrib | DSRA, J-DSRA, Distrib Acct | `dsra_engine`, distribution_account | `domain/financial_statements/balance_sheet.py` (mirror) | Audit (mirror of CF) |
| BS R23 Retained Earnings | Cumulative RE | not computed | `domain/financial_statements/balance_sheet.py` | New (derived) |
| BS R24 SHL balance | SHL closing balance | `shl_engine` / `shl_fcf_waterfall` | `domain/financial_statements/balance_sheet.py` (mirror) | Audit (mirror) |
| BS R26 Senior Debt | Senior closing balance | sculpting engine | `domain/financial_statements/balance_sheet.py` (mirror) | Audit (mirror) |
| BS R33 Balance check | Assets - Liab = 0 | not enforced | `domain/financial_statements/balance_sheet.py` | New — invariant test |
| CF R20-R38 Revenue/OPEX | Cash side | runtime waterfall | unchanged | Runtime |
| CF R67 Cash CIT | Cash tax (H2 timing) | `tax_engine` (H2-only) | `domain/financial_statements/tax_bridge.py` | Runtime — formalize timing |
| CF R69 FCF Banks | Cash for senior DS | `waterfall_engine` (cf_after_tax) | unchanged (audit field added in C1d) | Runtime |
| CF R70 Senior DS | Total senior payment | `waterfall_engine` | unchanged | Runtime |
| CF R84 FCF Junior | After senior + reserves | `waterfall_engine` | unchanged (audit C1d) | Runtime |
| CF R98 Distribution Account | Pre-lockup | C1d audit field | `distribution_account/engine.py` (formalize) | Runtime when wired |
| CF R99 FCF for SHL | Post-lockup | C1d audit field | `distribution_account/engine.py` | Runtime (Phase 7M target) |
| CF R100 Carryforward | Held in distrib acct | C1d audit field | `distribution_account/engine.py` | Runtime when wired |
| CF R102 FCF for SHL | = R99 (input) | `shl_fcf_waterfall` (fixture-backed) | unchanged | Runtime (Phase 7M target) |
| CF R104 Net SHL outflow | After SHL waterfall | `shl_fcf_waterfall` (Phase 7L) | unchanged | Runtime |
| CF R106 FCF for dividends | After SHL | `waterfall_engine` | unchanged | Runtime |
| CF R119 Net Dividends | After WHT | `waterfall_engine` | unchanged | Runtime |
| DS Senior schedule | Period DS | sculpting engine | `domain/financial_statements/pnl.py` reads | Runtime |
| DS SHL ledger | Opening/cash int/PIK/principal | `shl_engine` / `shl_fcf_waterfall` | `domain/financial_statements/balance_sheet.py` reads | Runtime |
| Dep schedule | Book vs tax depreciation | `app/depreciation_engine.py` | `domain/financial_statements/pnl.py` reads | Runtime |
| IDC schedule | Interest During Construction | `construction/idc_calculator.py` | unchanged | Runtime |

---

## 3. Module Architecture

### 3.1 Package structure

```
domain/financial_statements/
  __init__.py
  pnl.py                  # P&L assembly from runtime outputs
  balance_sheet.py        # BS assembly + balance check
  pf_cash_waterfall.py    # CF sheet equivalent (audit-only reconciliation)
  tax_bridge.py           # Book-to-tax bridge + loss carry-forward
  result.py               # FinancialStatementsResult dataclass
  inputs.py               # FinancialStatementsConfig dataclass
  excel_mapping.py        # Excel row constants + label mapping for export
  templates/
    __init__.py
    croatia.py            # Croatian tax regime (CIT 18%, 5y carry-fwd, thin-cap, H2 cash)
    # future: france.py, italy.py, etc.
  tests/
    test_pnl_assembly.py
    test_balance_sheet_check.py
    test_tax_bridge_loss_carryforward.py
    test_pf_cash_waterfall_bridge.py
    test_excel_mapping_tuho.py
    test_excel_mapping_oborovo.py
```

### 3.2 Layering

```
runtime engines (revenue, opex, construction, waterfall, tax, distribution_account, shl_fcf_waterfall)
                 │
                 ▼
         WaterfallResult (existing, untouched)
                 │
                 ▼
   domain/financial_statements/  (NEW — pure projection)
                 │
                 ├── PnLResult
                 ├── BalanceSheetResult
                 ├── PFCashWaterfallResult (audit reconciliation to CF sheet)
                 └── TaxBridgeResult
                 │
                 ▼
              reporting/  (Excel export, PDF, FID deck)
```

**Critical rule:** the financial_statements module is **DOWNSTREAM** of runtime engines. It consumes their outputs (mostly via WaterfallResult) and reorganizes them into Excel-parallel sheets. It does NOT feed back into runtime.

### 3.3 Why this layering

Three reasons:

1. **No circularity risk.** Statements consume; engines produce. Always.
2. **Excel-parity validation is local.** Each statement module has fixture-backed Excel comparison tests; failures don't affect runtime.
3. **Reusable per country/regime.** Croatian template today, French/Italian/Spanish later. Templates encode tax rules; the engine is country-agnostic.

---

## 4. Data Model Proposals

### 4.1 P&L per period

```python
@dataclass(frozen=True)
class PnLPeriodResult:
    period_index: int
    date: date
    year_index: int
    period_in_year: int
    
    # Revenue side
    revenue_total_keur: float
    revenue_breakdown: dict[str, float]  # {"ppa": ..., "merchant": ..., "co2": ..., "balancing": ...}
    
    # Expense side
    opex_keur: float                     # P&L R10
    local_tax_keur: float                # R11
    wht_on_interest_keur: float          # R12
    depreciation_book_keur: float        # R13
    total_expenses_keur: float           # R14
    
    # Operating result
    ebit_keur: float                     # R16
    
    # Financing
    interest_income_keur: float          # R19 + R20 - R21 net
    senior_interest_expense_keur: float  # R24
    junior_interest_expense_keur: float  # R25 + R26
    shl_interest_expense_keur: float     # R27 gross (full)
    other_interest_expense_keur: float   # R28
    financial_earnings_keur: float       # R30
    
    # Pre-tax
    ebt_keur: float                      # R32
    
    # Tax bridge (linked to TaxBridgeResult per period)
    fiscal_reintegration_keur: float     # R34
    taxable_income_keur: float           # R35
    loss_brought_forward_keur: float     # R36
    loss_used_this_period_keur: float    # R37
    loss_closing_keur: float             # R38
    carriable_losses_keur: float         # R39 (after 5y cap)
    taxable_profit_keur: float           # R41
    cit_accrued_keur: float              # R43 = R44
    
    # Bottom line
    net_income_keur: float               # R46
    legal_reserve_movement_keur: float   # R48
    retained_earnings_movement_keur: float  # R49 contribution
    dividend_declared_keur: float        # R50 (from CF R119)
```

### 4.2 Balance Sheet per period

```python
@dataclass(frozen=True)
class BalanceSheetPeriodResult:
    period_index: int
    date: date
    
    # Assets
    gross_fixed_assets_keur: float       # BS R8
    accumulated_depreciation_keur: float # BS R9
    net_fixed_assets_keur: float         # BS R10
    dsra_balance_keur: float             # R12
    jdsra_balance_keur: float            # R13
    distribution_account_keur: float     # R14
    cash_keur: float                     # R15
    total_assets_keur: float             # R17
    
    # Liabilities + Equity
    share_capital_keur: float            # R21
    legal_reserve_keur: float            # R22
    retained_earnings_keur: float        # R23 cumulative
    shl_balance_keur: float              # R24
    junior_balance_keur: float           # R25
    senior_balance_keur: float           # R26
    refinancing_keur: float              # R27
    short_term_loan_keur: float          # R29
    total_liabilities_equity_keur: float # R31
    
    # Invariant
    balance_check_keur: float            # R33 = R17 - R31 (must be ~0)
```

### 4.3 PF Cash Waterfall per period (CF-sheet equivalent)

```python
@dataclass(frozen=True)
class PFCashWaterfallPeriodResult:
    period_index: int
    date: date
    
    # Operating cash side (CF R20-R40)
    revenue_cash_keur: float             # R20
    opex_cash_keur: float                # R38
    ebitda_cash_keur: float              # R40
    
    # Senior debt service (CF R63-R70)
    senior_cash_interest_keur: float     # R63
    cash_tax_keur: float                 # R67 (NOT P&L accrued CIT)
    fcf_banks_keur: float                # R69 (audit field already exists in C1d)
    senior_total_ds_keur: float          # R70
    
    # Reserves
    dsra_funding_keur: float             # R75-R82
    jdsra_funding_keur: float            # R83
    fcf_junior_keur: float               # R84 (C1d audit)
    
    # Junior + other
    junior_ds_keur: float                # R85
    other_cash_keur: float               # R96
    distribution_account_pre_lockup_keur: float  # R98 (C1d audit)
    
    # Distribution-account gate
    lockup_applied: bool
    lockup_reason: str | None
    fcf_for_shl_keur: float              # R99 = R102 (C1d audit)
    carryforward_to_next_period_keur: float  # R100 (C1d audit)
    
    # SHL waterfall (Phase 7L)
    shl_cash_interest_keur: float        # within R102 flow
    shl_pik_keur: float
    shl_principal_keur: float
    net_shl_cash_outflow_keur: float     # R104
    
    # Distributions
    fcf_for_dividends_keur: float        # R106
    net_dividends_keur: float            # R119
```

### 4.4 Tax bridge per period

```python
@dataclass(frozen=True)
class TaxBridgePeriodResult:
    period_index: int
    year_index: int
    period_in_year: int
    
    # Book side
    ebt_keur: float                        # from P&L R32
    book_depreciation_keur: float          # P&L R13
    
    # Reintegration (thin-cap and others)
    thin_cap_disallowed_shl_interest_keur: float  # R59
    other_reintegration_keur: float
    fiscal_reintegration_total_keur: float        # R34
    
    # Taxable income
    taxable_income_keur: float             # R35
    
    # Loss carry-forward (rolling 5y for Croatia)
    loss_brought_forward_keur: float       # R36 opening
    losses_5y_buckets_keur: tuple[float, ...]  # year-tagged losses
    loss_used_this_period_keur: float      # R37
    loss_closing_keur: float               # R38
    losses_dropping_off_keur: float        # losses older than 5y
    carriable_losses_keur: float           # R39
    taxable_profit_keur: float             # R41
    
    # Tax
    cit_rate: float                        # 0.18 for Croatia
    cit_accrued_keur: float                # R43 = R44 (P&L)
    cit_cash_this_period_keur: float       # CF R67 (timing-shifted)
```

### 4.5 Aggregate result

```python
@dataclass(frozen=True)
class FinancialStatementsResult:
    config: FinancialStatementsConfig
    pnl_periods: tuple[PnLPeriodResult, ...]
    balance_sheet_periods: tuple[BalanceSheetPeriodResult, ...]
    pf_cash_waterfall_periods: tuple[PFCashWaterfallPeriodResult, ...]
    tax_bridge_periods: tuple[TaxBridgePeriodResult, ...]
    
    # Annual rollups for export
    pnl_annual: tuple[PnLAnnualResult, ...]
    balance_sheet_annual: tuple[BalanceSheetAnnualResult, ...]
    pf_cash_waterfall_annual: tuple[PFCashWaterfallAnnualResult, ...]
    
    # Excel reconciliation
    excel_reconciliation: ExcelReconciliation  # PnL/BS/CF deltas vs reference fixture
    
    # Invariants
    balance_check_max_delta_keur: float
    fcf_waterfall_max_delta_keur: float
    
    @property
    def reconciles(self) -> bool:
        return (
            abs(self.balance_check_max_delta_keur) < 0.01 and
            abs(self.fcf_waterfall_max_delta_keur) < 0.01
        )
```

---

## 5. Source-of-Truth Policy

### 5.1 Runtime-produced (source of truth) — UNCHANGED

These are computed by runtime engines and consumed by financial_statements:

- Revenue (revenue engine)
- OPEX (opex engine)
- Construction CAPEX + IDC (construction engine)
- Senior debt schedule (sculpting engine)
- SHL ledger (pik_then_sweep or shl_fcf_waterfall)
- Cash tax timing (tax engine + new tax_bridge for Croatia regime)
- Distribution-account gating (Phase 7M target)
- Final distribution amounts (waterfall engine)

### 5.2 Statements-produced (derived) — NEW

These are computed by financial_statements from runtime outputs:

- P&L EBIT, EBT, Net Income (assembly)
- Retained Earnings (cumulative)
- Net Fixed Assets (gross − accumulated depreciation)
- Total Assets, Total Liabilities+Equity, Balance check
- Taxable Income, loss carry-forward roll, accrued CIT (becomes runtime when wired in Stage 4)
- Excel-row labeled reconciliation

### 5.3 The CIT exception (split source of truth)

CIT is the one place where the boundary blurs:
- **Accrued CIT** (P&L R44) is calculated in tax_bridge using book→tax bridge logic
- **Cash CIT** (CF R67) is what tax_engine outputs today

If the tax_bridge accrued CIT differs from what tax_engine produces, the **tax_bridge** value is more correct (matches Excel exactly) and should eventually replace tax_engine. This is the migration path proposed in Stage 5.

### 5.4 Phased ownership migration

| Item | Current owner | Stage 2 owner | Stage 5 owner |
|---|---|---|---|
| Book depreciation | `app/depreciation_engine.py` | `domain/financial_statements/pnl.py` reads | unchanged |
| Loss carry-forward | `tax_engine` flat `prior_tax_loss_keur` | `tax_bridge.py` rolling 5y (audit) | `tax_bridge.py` runtime |
| Thin-cap reintegration | `domain/tax/reintegration.py` (partial) | `tax_bridge.py` reads | unchanged |
| Accrued CIT | `tax_engine` | `tax_bridge.py` (audit) | `tax_bridge.py` runtime |
| Cash CIT timing | `tax_engine` | `tax_bridge.py` (audit) | `tax_bridge.py` runtime |
| R98 Distribution Account | C1d audit field | `distribution_account/engine.py` (audit) | runtime |
| R99 lockup gate | C1d audit field | `distribution_account/engine.py` | runtime (Phase 7M) |
| R100 carryforward | C1d audit field | `distribution_account/engine.py` | runtime |

---

## 6. Implementation Phases

### Stage 1 — Docs-only design (THIS PR)

- This document
- Excel row mapping matrix
- Architecture proposal
- No code changes

### Stage 2 — Offline statement generator

**Branch:** `phase6-financial-statements-offline-pnl`

- New module `domain/financial_statements/` skeleton
- `pnl.py`: assemble P&L from WaterfallResult + DS + Dep schedules
- `tax_bridge.py`: rolling 5y loss carry-forward, thin-cap reintegration audit
- Default-off behavior; no runtime change
- TUHO/Oborovo Excel fixture parity tests (±0.5 kEUR per row)
- Excel mapping module with row constants

**Scope:** P&L only. BS and PF Cash Waterfall come in Stage 3.

### Stage 3 — Balance Sheet + PF Cash Waterfall + Audit Excel export

**Branch:** `phase6-financial-statements-balance-sheet-and-cf`

- `balance_sheet.py`: BS assembly + balance check invariant
- `pf_cash_waterfall.py`: reconstruction of Excel CF sheet from existing audit fields
- `reporting/financial_statements.py`: Excel export with P&L, BS, CF tabs matching Excel layout
- Tests: balance check ≤ 0.01 kEUR per period; CF rows match Excel within tolerance

### Stage 4 — Tax bridge runtime integration

**Branch:** `phase6-financial-statements-tax-bridge-runtime`

- `tax_bridge.py` becomes runtime source for CIT accrued AND cash timing
- Flag `use_tax_bridge_engine: bool = False` (default off)
- Replaces flat `prior_tax_loss_keur` with rolling 5y carry-forward
- TUHO/Oborovo opt-in only after parity verified

**Acceptance:** TUHO total CIT within ±0.5 kEUR of Excel R44; TUHO cash CIT per period within ±0.1 kEUR of Excel R67.

### Stage 5 — R99/R102 source replacement

**Branch:** `phase6-r99-r102-runtime-source`

- Use `distribution_account/engine.py` (now feeding from tax_bridge cash CIT) as runtime cash source
- Feeds into `shl_fcf_waterfall` (Phase 7L) replacing fixture
- Flag `use_r99_runtime_source: bool = False`
- Acceptance: computed R99 within ±2 kEUR of fixture per period

### Stage 6 — Runtime adoption as source of truth

- TUHO factory opts into all bridges
- Oborovo opts in after independent Oborovo Excel reconciliation
- Old fields and flat parameters remain for backward compatibility
- Deprecation warnings on `prior_tax_loss_keur` and similar legacy fields

---

## 7. Tests Needed

### 7.1 P&L parity

```python
def test_tuho_pnl_ebit_matches_excel_per_period():
    """Each period's EBIT within ±0.5 kEUR of TUHO P&L R16."""

def test_tuho_pnl_ebt_matches_excel_per_period():
    """EBT within ±0.5 kEUR of R32."""

def test_tuho_pnl_net_income_matches_excel_per_period():
    """NI within ±0.5 kEUR of R46."""

def test_tuho_pnl_retained_earnings_cumulative_matches_excel():
    """Cumulative RE = sum of period NI; matches BS R23."""
```

### 7.2 Tax bridge

```python
def test_tuho_taxable_income_matches_excel():
    """R35 within ±0.5 kEUR."""

def test_tuho_loss_carry_forward_rolling_5y():
    """R36-R41 with 5-year buckets; carriable losses cap correctly."""

def test_tuho_thin_cap_reintegration_kicks_in_at_profit_year():
    """R34 = 0 in loss years; > 0 when EBITDA-positive thin-cap binds."""

def test_tuho_cit_cash_timing_h2_only():
    """CF R67 zero in H1 except for prior-year settlement; non-zero in H2."""
```

### 7.3 Balance sheet

```python
def test_tuho_balance_check_zero_every_period():
    """BS R33 == 0 within ±0.01 kEUR per period."""

def test_tuho_bs_net_fixed_assets_matches_depreciation_schedule():
    """R10 = R8 - cumulative depreciation."""

def test_tuho_bs_shl_balance_matches_shl_ledger():
    """BS R24 == SHL closing balance from DS sheet."""

def test_tuho_bs_senior_balance_matches_sculpting_output():
    """BS R26 == Senior closing balance from DS sheet."""
```

### 7.4 PF cash waterfall

```python
def test_tuho_cf_r69_matches_existing_audit_field():
    """PF cash waterfall R69 == WaterfallPeriod.r69_fcf_banks_keur (C1d field)."""

def test_tuho_cf_r99_matches_distribution_account_engine():
    """R99 from new engine == fixture value within ±2 kEUR."""

def test_tuho_cf_r119_matches_runtime_distribution():
    """CF R119 == sum(WaterfallResult.distributions)."""
```

### 7.5 Regression and isolation

```python
def test_financial_statements_module_does_not_change_runtime():
    """Assert TUHO/Oborovo WaterfallResult bit-identical before/after import."""

def test_financial_statements_default_off():
    """When use_tax_bridge_engine=False, runtime CIT unchanged."""

def test_oborovo_pnl_independent_of_tuho_template():
    """Oborovo P&L assembly uses Croatian template independently."""
```

---

## 8. Risks

### Risk 1 — Overfitting TUHO/Oborovo

Both reference models are Croatian renewables under the same tax regime. The Croatian template will be well-tested; other regimes (French TCFE, Italian IRES, Spanish IS) will need separate templates.

**Mitigation:** the `templates/` folder pattern; new templates inherit shared logic from `tax_bridge.py` and override country-specific rules. Don't bake Croatian assumptions into core engine.

### Risk 2 — Circularity between waterfall and statements

The most dangerous case: P&L needs accrued CIT → tax_bridge computes from EBT → EBT needs senior interest → senior interest comes from sculpting → sculpting (in some configs) consumes cash CFADS that depends on cash CIT → cash CIT computed from accrued CIT.

**Mitigation:** strict layering. Tax_bridge consumes runtime outputs only. If runtime sculpting needs a CIT estimate, it uses its own simplified estimate (current tax_engine behavior); the tax_bridge result is for STATEMENT purposes. The Stage 5 migration replaces this only when the parity is mathematically demonstrable.

### Risk 3 — Book vs tax basis

Excel uses linear book depreciation = linear tax depreciation in TUHO (both 30 years). Real Croatian projects might use accelerated tax depreciation. The `tax_bridge.py` must separate book_depreciation (P&L R13) from tax_depreciation (an intermediate variable used in taxable income).

**Mitigation:** explicit field separation in data model. Default both to "linear 30y" matching TUHO/Oborovo; allow override.

### Risk 4 — Performance

Adding a parallel statements layer adds work per waterfall run. For a 30-year semi-annual model (~60 periods), this is negligible. For 1000-project portfolios or Monte Carlo (10,000 runs × 60 periods), it could add 10-30% runtime.

**Mitigation:** statements layer is opt-in (`compute_statements: bool = True`); can be disabled for performance-critical batch runs. Default-on for single-project; default-off for portfolio.

### Risk 5 — Audit complexity

Excel exports with P&L, BS, CF, DS, Dep all need to reconcile. If any row drifts, the whole export looks suspect.

**Mitigation:** explicit reconciliation deltas in `FinancialStatementsResult.excel_reconciliation`. Test asserts max delta < 0.5 kEUR per row. Add CI check that runs full Excel-fixture comparison on every PR.

### Risk 6 — Multi-lender readiness

Current Excel has single senior + single SHL. Multi-tranche senior debt (commercial + ECA + multilateral) is not modeled. When introduced, P&L R24 splits into multiple interest lines, BS R26 splits into multiple debt lines, CF R63 splits.

**Mitigation:** data model already uses `dict` for revenue_breakdown; same pattern for `interest_breakdown` and `debt_breakdown` makes future multi-lender additive without breaking existing schema.

### Risk 7 — Future SaaS reporting and audit trail

Bankable users will ask "show me how this number was computed". The statements module is the natural home for this.

**Mitigation:** every `PnLPeriodResult`, `BalanceSheetPeriodResult`, `TaxBridgePeriodResult` should carry references (via period_index) back to the source `WaterfallPeriod`. Persistence layer should snapshot both.

---

## 9. Acceptance Criteria (Stage 2 onwards)

| Stage | Acceptance |
|---|---|
| 1 | Design doc approved; no runtime change. |
| 2 | TUHO P&L R8-R46 within ±0.5 kEUR per period vs Excel. Oborovo same. Runtime unchanged. |
| 3 | BS balance check ≤ 0.01 kEUR per period for TUHO and Oborovo. PF CF rows match Excel within ±0.5 kEUR. Excel export reproduces TUHO P&L/BS/CF tabs structurally. |
| 4 | TUHO total CIT within ±0.5 kEUR of Excel; per-period cash CIT within ±0.1 kEUR. Default-off; flag opt-in. |
| 5 | Runtime R99 within ±2 kEUR of fixture per period. Default-off; flag opt-in. |
| 6 | TUHO factory opts in to tax_bridge + R99 runtime source. Distribution within ±0.5% of Excel R119. |

---

## 10. Recommended Next Implementation Branch

**Branch:** `phase6-financial-statements-offline-pnl`

**Scope:** Stage 2 only — offline P&L generator + tax bridge audit.

**Files to add:**
- `domain/financial_statements/__init__.py`
- `domain/financial_statements/pnl.py`
- `domain/financial_statements/tax_bridge.py`
- `domain/financial_statements/result.py`
- `domain/financial_statements/inputs.py`
- `domain/financial_statements/excel_mapping.py`
- `domain/financial_statements/templates/__init__.py`
- `domain/financial_statements/templates/croatia.py`
- `tests/test_financial_statements_tuho_pnl_parity.py`
- `tests/test_financial_statements_oborovo_pnl_parity.py`
- `tests/test_financial_statements_tax_bridge_loss_carryforward.py`
- `tests/test_financial_statements_module_does_not_change_runtime.py`

**Files NOT to touch:**
- `app/project_factories.py`
- `domain/waterfall/*` 
- `domain/revenue/*`
- `domain/opex/*`
- `domain/tax/*` (read from, don't modify yet — Stage 4 modifies tax_engine)
- `domain/shl_fcf_waterfall.py`
- `domain/inputs.py` (no new flags yet; Stage 4 introduces `use_tax_bridge_engine`)
- UI/persistence/cache

**Acceptance gate:** TUHO and Oborovo P&L produces R8-R46 within ±0.5 kEUR of Excel per period. Runtime WaterfallResult bit-identical before/after import of new module.

---

## Appendix A — Decision Summary by Question

| Question | Answer |
|---|---|
| 1. Module architecture | `domain/financial_statements/` package with pnl/balance_sheet/pf_cash_waterfall/tax_bridge submodules; templates folder for country regimes |
| 2. P&L design | Per-period `PnLPeriodResult` with explicit Excel-row-mapped fields; assembly from runtime outputs |
| 3. Balance Sheet design | Per-period `BalanceSheetPeriodResult` with balance check invariant ≤ 0.01 kEUR |
| 4. PF Cash Waterfall design | Per-period `PFCashWaterfallPeriodResult` reproducing Excel CF rows R20-R119 |
| 5. Tax bridge design | `tax_bridge.py` with rolling 5y carry-forward, thin-cap reintegration, accrued vs cash CIT distinction; Croatian template first |
| 6. Links to existing engines | Statements module DOWNSTREAM only; consumes WaterfallResult; never feeds back |
| 7. Source-of-truth policy | Runtime engines produce; statements derive; CIT migration in Stage 5 with explicit parity gate |
| 8. Excel mapping | Full mapping matrix in Section 2; row constants in `excel_mapping.py` |
| 9. Implementation phases | 6 stages: docs → offline P&L → BS+CF+export → tax bridge runtime → R99 runtime → adoption |
| 10. Tests needed | TUHO/Oborovo P&L parity, balance check, tax bridge correctness, regression isolation |
| 11. Risks | 7 risks identified; templates folder mitigates regime overfitting; strict layering mitigates circularity |
| 12. Deliverable | This document |

## Appendix B — Excel CF row reconciliation (TUHO whole-horizon)

| Excel Row | Label | Total kEUR | Phase 7 status |
|---|---|---:|---|
| R20 | Operating Revenues | 423,787.5 | Runtime (revenue engine, ±0.013% match) |
| R38 | OPEX | -84,674.8 | Runtime (OPEX line-item, 4-decimal match when flag on) |
| R40 | EBITDA | 339,112.7 | Runtime (derived) |
| R63 | Senior cash interest | -22,822.8 | Runtime (sculpting) |
| R67 | Cash CIT | -38,240.9 | Runtime (tax engine; magnitude match, timing differs) |
| R69 | FCF Banks | 300,926.8 | Runtime + C1d audit field |
| R70 | Senior DS | -66,181.3 | Runtime (PR B1 dual-DSCR + Phase 7K sculpting) |
| R84 | FCF Junior | 234,745.4 | Runtime + C1d audit field |
| R98 | Distribution Account | 234,745.4 | C1d audit field; Phase 7M target for runtime |
| R99 | FCF for SHL (= R102) | 234,745.4 | C1d audit; Phase 7M target |
| R100 | Carryforward | 0.0 (full horizon) | C1d audit |
| R102 | FCF for SHL input | 234,745.4 | Phase 7L fixture-backed |
| R104 | Net SHL outflow | -82,486.0 | Phase 7L runtime (within ±2 kEUR of fixture) |
| R106 | FCF for dividends | 152,259.4 | Runtime |
| R119 | Net Dividends | 151,709.4 | Runtime (Phase 7L: 153,207, +0.99%) |

Phase 6 module formalizes the audit-only C1d fields into a coherent statement structure and provides the foundation for Phase 7M runtime R99 source.
