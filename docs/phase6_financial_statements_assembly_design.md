# Phase 6 — Financial Statements Assembly Layer + PF Cash Waterfall Design

**Branch:** phase6-financial-statements-module-design
**Base:** main
**Status:** Design only. Docs-only PR. No runtime change.

---

## 0. Response to Prior Holistic Review Findings

This design **directly responds** to risks raised in the prior holistic review and Phase 7K/7L/7M reviews:

| Prior finding | Phase 6 response |
|---|---|
| "`waterfall_engine.py` is becoming a complexity risk (1,251 LOC, +50 per flag)" | Assembly layer is **strictly downstream**. Adds zero engine branches. New audit fields done in Phase 7 (C1d) are not extended; they are **consumed** here. |
| "R99/R102 cannot be solved cleanly inside waterfall audit fields alone" | Tax bridge module owns the upstream calculations (taxable income, loss carry-forward, accrued vs cash CIT). Once stable, the runtime cash R99 source pulls from there in Stage 5 — not from `waterfall_engine`. |
| "Tax-basis visibility gaps remain (depreciation, fiscal reintegration, SHL deduction)" | New `tax_bridge.py` formalizes the book→tax bridge. Excel evidence (Dep R31 "Unlevered Depreciation") confirms TUHO has explicit book/tax depreciation separation that current Python lacks. |
| "SHL mechanics fixture-validated but runtime R99 source blocked" | Stage 5 (R99 runtime source) becomes a **downstream consumer of tax_bridge cash CIT**, not a new waterfall_engine branch. The blocking dependency is the tax bridge — not more audit fields. |
| "Next architectural step should avoid adding more ad-hoc fields to waterfall_engine.py" | All new logic lives in `domain/financial_statements/`. Zero new fields on `WaterfallPeriod`. Zero new flags on `ProjectInfo` in Stage 2-3. Flags appear only when runtime migration begins (Stage 4+). |

**Core principle:** this module is an **ASSEMBLY/RECONCILIATION layer**, not a duplicate calculation engine. It pulls already-computed outputs from existing domain modules and organizes them into Excel-parallel statements. New calculation logic is limited to roll-forward state (retained earnings, accumulated depreciation, loss carry-forward presentation, distribution account balance, cash balance).

---

## 1. Excel Logical Statement Reconstruction

### 1.1 Sheet topology (TUHO and Oborovo are identical)

```
Inputs / Scenarios / Macro / Flags
            │
            ▼
   CapEx ── IDC ──┐
            │     │
            ▼     ▼
            Dep ──┤
                  │
   OpEx ────────► CF (PF Cash Waterfall) ◄── DS (Senior + SHL)
                  │
                  ▼
   P&L ◄─── reads CF (R67 cash CIT), DS (interest, principal), Dep
            │
            ▼
            BS ◄── reads P&L (net income), CF (reserves, distrib account, dividends), DS (debt balances)
            │
            ▼
            Eq (Sponsor)
            │
            ▼
   Outputs / FID deck / Cash@Risk
```

Sheets feed each other in a specific order:
1. **CapEx + IDC** produce gross fixed asset value and construction-period interest
2. **Dep** schedule produces both book depreciation (P&L R13) and tax depreciation ("Unlevered Depreciation" R31) — distinct
3. **OpEx** schedule produces total operating expenses (P&L R10, CF R38)
4. **DS** schedule produces senior debt service (P&L R24, CF R63+R70) and SHL ledger (P&L R27, CF R102/R104)
5. **CF** assembles the operating cash waterfall: revenues − OPEX − cash interest − cash CIT → FCF Banks (R69) → senior DS → DSRA → R84 → SHL waterfall → R104 → R106 dividends → R119
6. **P&L** reads from Dep (R13), DS (R24, R27), CF (R67 cash CIT timing) and computes EBT → fiscal reintegration → taxable income → loss roll → CIT → NI
7. **BS** mirrors balance items: gross/net fixed assets from CapEx+Dep, DSRA/distribution account/cash from CF, senior/SHL/junior debt from DS, share capital/legal reserve/retained earnings from accumulation

**Critical:** The CF sheet does NOT consume P&L accrued CIT. It uses **its own cash CIT** (R67) computed with H2 timing. The two CITs (accrued P&L R44 ≠ cash CF R67) differ per-period and only reconcile at end-of-horizon totals.

### 1.2 Logical P&L (TUHO at op_idx=0; verbatim Excel rows)

```
R8   Total Revenues                = 4,061.0   (= CF R20)
R10  Operating expenses            =  -990.8   (= CF R38; positive in Excel sign)
R11  Local Tax                     =     0.0
R12  Withholding Tax on Interests  =     0.0
R13  Depreciation (book)           = -1,845.4  (FROM Dep R30)
R14  Total Expenses                = -2,836.3  (R10+R11+R12+R13)
R16  EBIT                          =  1,224.7  (R8 + R14)

R19  Interests from Reserve Accts  =     0.0
R20  Interests from Cash           =     0.0
R21  Withholding Tax (fin rev)     =     0.0

R24  Senior Interests              = -1,297.1  (FROM DS senior schedule)
R25  Senior Refinancing Interest   =     0.0
R26  Junior Interest               =     0.0
R27  Shareholder Loan Interests    = -1,297.4  (FROM SHL ledger, GROSS)
R28  Interests on Cash             =     0.0
R30  Financial Earnings            = -2,594.5  (R19+R20+R21+R24+R25+R26+R27+R28)

R32  Earnings before tax           = -1,369.7  (R16 + R30)

R34  Fiscal Reintegration          =     0.0   (thin-cap addback; zero in loss yrs)
R35  Taxable Income                = -1,369.7  (R32 + R34)
R36  Losses N-1                    = -3,568.7  (carried in; = construction SHL IDC)
R37  Allocated losses              =     0.0   (none used; current period is loss)
R38  Losses N (cumulative)         = -3,568.7  (R36 - R37 + min(0, R35))
R39  Carriable losses              = -3,568.7  (R38 capped at 5y rolling rule)
R41  Taxable Profit N              = -1,369.7  (R35 - R37)
R43  Corporate Income Tax          =     0.0   (max(0, R41) * rate)
R44  Corporate Income Tax (P&L)    =     0.0   (= R43, accrual basis)
R46  Net Income                    = -1,369.7  (R32 - R44)
R48  Legal reserve                 =     0.0   (NI<0 → no reserve)
R49  Retained Earnings (period)    = -1,369.7  (R46 - R48 - R50)
R50  Net Dividends                 =     0.0   (FROM CF R119)
R52  Balance check                 =     0.0   (R46 - R48 - R49 - R50 = 0)
```

### 1.3 Logical Balance Sheet (TUHO at op_idx=0, EoP)

```
ASSETS
R8   Gross Fixed Assets            = 72,993.7  (FROM CapEx total, set at COD)
R9   Accumulated Depreciation      =  1,845.4  (= sum of P&L R13 to date)
R10  Total Fixed Assets (net)      = 71,148.3  (R8 - R9)
R12  DSRA                          =      0.0  (FROM CF DSRA balance)
R13  J-DSRA                        =      0.0
R14  Distribution Account          =      0.0  (FROM CF R100 cumulative carryforward)
R15  Cash                          =      0.0  (residual / retained cash)
R17  Total Assets                  = 71,148.3

LIABILITIES + EQUITY
R21  Capital at Financial close    =    500.0  (constant)
R22  Legal Reserve                 =      0.0
R23  Retained Earnings (cumulative)= -4,938.4  (= construction-period loss + period 0 NI = -3,568.7 + -1,369.7)
R24  Shareholder Loan              = 33,047.5  (FROM SHL ledger closing)
R25  Akuo Carbon Fund              =      0.0
R26  Senior Debt                   = 42,539.3  (FROM senior schedule closing)
R27  Refinancing                   =      0.0
R29  Short term loan               =      0.0
R31  Total Liabilities + Equity    = 71,148.3
R33  Balance check                 =      0.0  ✓
```

### 1.4 Logical PF Cash Waterfall (TUHO whole-horizon totals)

```
R20  Operating Revenues            =  423,787.5  (FROM revenue engine)
R38  OPEX                          =  -84,674.8  (FROM opex engine)
R40  EBITDA                        =  339,112.7  (R20 + R38)

R63  Senior cash interest          =  -22,822.8  (FROM senior schedule, cash portion)
R67  Cash CIT                      =  -38,240.9  (FROM tax bridge cash timing — NOT P&L R44)
R69  FCF Banks                     =  300,926.8  (R20 + R38 + R63 + R66 + R67 + first-period init)
R70  Senior Debt Service           =  -66,181.3  (FROM senior schedule total)

R75-R82 DSRA movements             =        0.0  (zero for TUHO)
R84  FCF Junior                    =  234,745.4  (R69 + R70 + DSRA + other)
R85  Junior debt service           =        0.0
R96  Other cash adjustments        =        0.0
R98  Distribution Account pre-lockup= 234,745.4  (R84 + R85 + R96 + R100[t-1])

R99  FCF for SHL (post-lockup)     =  234,745.4  (if lockup OK then R98 else 0)
R100 Carryforward held in account  =        0.0  (R98 - R99)
R102 FCF for SHL input             =  234,745.4  (= R99 strictly)

R104 Net SHL outflow               =  -82,486.0  (cash interest + principal from SHL waterfall)
R106 FCF for dividends             =  152,259.4  (R99 + R104)
R119 Net Dividends                 =  151,709.4  (after WHT)
```

### 1.5 Tax bridge logic (book → tax)

Excel evidence at TUHO Dep R31 explicitly distinguishes:
- **R30 Depreciation** (book, P&L) = 1,845.44 at op_idx=0
- **R31 Unlevered Depreciation** (tax basis) = 1,752.76 at op_idx=0
- **Difference = 92.68 kEUR** (≈5% of book) — this is the IDC + financial-cost portion that is NOT tax-deductible as depreciation

Per-period bridge:
```
Step 1: P&L EBT = EBIT + Financial Earnings
Step 2: tax_depreciation = book_depreciation - non_deductible_depreciation
Step 3: EBT_tax_basis = EBT + (book_depreciation - tax_depreciation)
        (positive adjustment because book had MORE expense than tax)
Step 4: Fiscal Reintegration (R34) = thin-cap non-deductible SHL interest addback
        + other regime-specific addbacks
Step 5: Taxable Income (R35) = EBT_tax_basis + Fiscal Reintegration
Step 6: Loss Carry-forward roll (5y rolling buckets for Croatia)
   Open losses N-1 = R36
   Used this period = R37 = min(positive Taxable Income, sum of buckets within 5y)
   Closing losses N = R38 = R36 - R37 + max(0, -Taxable Income)
   Carriable (after 5y dropoff) = R39
Step 7: Taxable Profit N (R41) = max(0, Taxable Income - Used losses)
Step 8: CIT accrued (R44) = R41 * tax_rate (Croatia: 18%)
Step 9: Cash CIT (R67) = R44 shifted to H2 of following year
        (Empirically: TUHO first cash CIT appears col 33 = 2042-12-31 = H2)
```

**Empirical confirmation:**
- Initial loss carry-forward (R36 at op_idx=0) = **-3,568.69 kEUR**
- This equals **TUHO construction-period SHL IDC** exactly
- Confirming hypothesis: construction-period accumulated loss = capitalized SHL interest

This is the kind of upstream relationship that audit-only fields in `waterfall_engine.py` cannot capture cleanly. The tax bridge formalizes it.

### 1.6 Distribution account flow (audit verified)

```
For each operating period t:
    R98[t] = R84[t] + R85[t] + R96[t] + R100[t-1]
    
    lockup_test = (DSCR[t] < lockup_DSCR) OR
                  (year[t] < min_distribution_year) OR
                  (R98[t] < 0) OR
                  (DSRA_end[t] < DSRA_target)
    
    R99[t] = 0 if lockup_test else R98[t]
    R100[t] = R98[t] - R99[t]    # held in distribution account
    R102[t] = R99[t]              # input to SHL waterfall (strict identity)
```

The distribution-account is a **financial-engineering construct**, not an accounting one. It holds blocked cash from periods where dividend lockup conditions are unmet, releasing it later. It does NOT appear on P&L; it appears as **BS R14 Distribution Account** balance.

### 1.7 Circularity risks identified

| Potential circularity | Resolution |
|---|---|
| P&L needs CIT → tax bridge needs EBT → EBT needs financing exp → senior interest from sculpting → sculpting needs DSCR → DSCR needs cash CFADS → cash CFADS needs cash CIT | Cash CIT for sculpting uses a SIMPLIFIED estimate (current `tax_engine` behavior). Statement layer's tax_bridge computes the EXACT accrued CIT for P&L purposes. The two values may differ — that's a known and acceptable diagnostic gap until Stage 5. |
| Net income → retained earnings (BS) → equity → indebtedness ratio → thin-cap test → fiscal reintegration → taxable income → CIT → NI | Thin-cap is computed against **prior period** equity / EBITDA, breaking the same-period circularity. Excel does this. Engine must do the same. |
| Distribution account balance → BS R14 → balance check needs cash → cash residual depends on R119 → R119 depends on SHL waterfall → SHL waterfall depends on R102 = R99 → R99 depends on R98 → R98 needs prior R100 | Resolved by SEQUENTIAL period processing (no within-period circularity). Each period's R100[t] is consumed by next period's R98[t+1]. |

---

## 2. Excel-to-Engine Mapping Matrix

For every important Excel row family:

| Sheet:Row | Label | Owner module | SoT type | Phase 7 status |
|---|---|---|---|---|
| **P&L** | | | | |
| P&L R8 | Total Revenues | `revenue` | runtime SoT | done |
| P&L R10 | OPEX | `opex` | runtime SoT | done (line-item engine) |
| P&L R11 | Local Tax | `tax/atad_engine` (?) | runtime SoT | partially handled |
| P&L R12 | WHT on Interests | `waterfall_engine` shl_wht_rate | runtime SoT | yes |
| P&L R13 | Depreciation (book) | `app/depreciation_engine` | runtime SoT | yes (needs migration to domain) |
| P&L R14 | Total Expenses | `financial_statements/pnl` | derived | new |
| P&L R16 | EBIT | `financial_statements/pnl` | derived | new |
| P&L R19-R21 | Interest income | `waterfall_engine` (reserves) | runtime SoT | partial |
| P&L R24 | Senior Interest | `financing/sculpting_iterative` | runtime SoT | done |
| P&L R25 | Senior Refi Interest | (none) | future | not modeled |
| P&L R26 | Junior Interest | (none) | future | not modeled |
| P&L R27 | SHL Interest (gross) | `shl_engine` / `shl_fcf_waterfall` | runtime SoT | done |
| P&L R30 | Financial Earnings | `financial_statements/pnl` | derived | new |
| P&L R32 | EBT | `financial_statements/pnl` | derived | new |
| P&L R34 | Fiscal Reintegration | `tax/reintegration` (exists, partial) | runtime SoT | needs formalization |
| P&L R35 | Taxable Income | `financial_statements/tax_bridge` | derived | new |
| P&L R36 | Losses N-1 | `financial_statements/tax_bridge` (carry-fwd) | runtime SoT | new (replaces flat `prior_tax_loss_keur`) |
| P&L R37 | Allocated losses | `financial_statements/tax_bridge` | derived | new |
| P&L R38 | Losses N | `financial_statements/tax_bridge` | derived | new |
| P&L R39 | Carriable losses | `financial_statements/tax_bridge` | derived (5y cap) | new |
| P&L R41 | Taxable Profit N | `financial_statements/tax_bridge` | derived | new |
| P&L R44 | CIT (accrued) | `financial_statements/tax_bridge` | runtime SoT in Stage 4 | replaces current tax engine accrual |
| P&L R46 | Net Income | `financial_statements/pnl` | derived | new |
| P&L R48 | Legal reserve | `financial_statements/pnl` | derived (jurisdiction rule) | new |
| P&L R49 | Retained Earnings (delta) | `financial_statements/pnl` | derived | new |
| P&L R50 | Net Dividends | (mirror of CF R119) | derived | new |
| **BS** | | | | |
| BS R8 | Gross Fixed Assets | `capex_engine` / `construction` | runtime SoT | done |
| BS R9 | Accumulated Depreciation | `financial_statements/balance_sheet` (cumulative) | derived | new |
| BS R10 | Net Fixed Assets | `financial_statements/balance_sheet` | derived | new |
| BS R12 | DSRA | `waterfall/dsra_engine` | runtime SoT | done |
| BS R13 | J-DSRA | `waterfall/dsra_engine` (junior) | runtime SoT | done |
| BS R14 | Distribution Account | `distribution_account/engine` | runtime SoT in Stage 5 | C1d audit field exists |
| BS R15 | Cash | `financial_statements/balance_sheet` (residual) | derived | new |
| BS R21 | Share Capital | `inputs` constant | runtime SoT | trivial |
| BS R22 | Legal Reserve | `financial_statements/balance_sheet` (cumulative) | derived | new |
| BS R23 | Retained Earnings (cum) | `financial_statements/balance_sheet` (cumulative) | derived | new |
| BS R24 | SHL balance | `shl_engine` / `shl_fcf_waterfall` closing | runtime SoT | done |
| BS R26 | Senior Debt | `financing/sculpting_iterative` closing | runtime SoT | done |
| BS R33 | Balance check | `financial_statements/balance_sheet` invariant | derived (asserted) | new |
| **CF** | | | | |
| CF R20 | Operating Revenues | `revenue` | runtime SoT | done |
| CF R38 | OPEX | `opex` | runtime SoT | done |
| CF R40 | EBITDA | `waterfall_engine` | runtime SoT | done |
| CF R63 | Senior cash interest | `financing/sculpting_iterative` (cash portion) | runtime SoT | done |
| CF R66 | Other minor revenue | (none) | future | not modeled |
| CF R67 | **Cash CIT** | `financial_statements/tax_bridge` (Stage 4) | runtime SoT in Stage 4 | currently `tax_engine` H2-only |
| CF R69 | FCF Banks | C1d audit field on `WaterfallPeriod` | derived | done (C1d) |
| CF R70 | Senior DS | `financing/sculpting_iterative` total | runtime SoT | done |
| CF R75-R82 | DSRA movements | `waterfall/dsra_engine` | runtime SoT | done |
| CF R84 | FCF Junior | C1d audit field | derived | done (C1d) |
| CF R85 | Junior DS | (none) | future | not modeled |
| CF R96 | Other adjustments | (none) | future | not modeled |
| CF R98 | Distribution Acct (pre-lockup) | C1d audit field; Stage 5 owner = `distribution_account/engine` | derived | C1d audit |
| CF R99 | FCF for SHL (post-lockup) | Stage 5 owner = `distribution_account/engine` | runtime SoT in Stage 5 | currently fixture (Phase 7L) |
| CF R100 | Carryforward held | `distribution_account/engine` (Stage 5) | derived | C1d audit |
| CF R102 | FCF for SHL input | = R99 (Phase 7L) | runtime SoT | fixture-backed |
| CF R104 | Net SHL outflow | `shl_fcf_waterfall` (Phase 7L) | runtime SoT | done |
| CF R106 | FCF for dividends | `waterfall_engine` | runtime SoT | done |
| CF R119 | Net Dividends | `waterfall_engine` (final) | runtime SoT | done |
| **DS** | | | | |
| DS senior schedule | Senior int + principal | `financing/sculpting_iterative` | runtime SoT | done |
| DS SHL ledger | Opening/cash int/PIK/prin | `shl_engine` / `shl_fcf_waterfall` | runtime SoT | done |
| **Dep** | | | | |
| Dep R30 | Book depreciation total | `depreciation_engine` | runtime SoT | done |
| Dep R31 | Unlevered (tax) deprec | `tax_bridge` | runtime SoT in Stage 4 | NOT currently modeled |
| **CapEx** | | | | |
| CapEx total | Gross asset value | `capex_engine` / `construction` | runtime SoT | done |
| **IDC** | | | | |
| IDC SHL | Construction SHL IDC | `construction/idc_calculator` | runtime SoT | done |
| IDC Senior | Construction Senior IDC | `construction/idc_calculator` | runtime SoT | done |

**Summary:** 18 new derived rows and 5 new runtime SoT items (carry-forward, distribution account, tax bridge), plus 36 existing runtime SoT items consumed without modification.

---

## 3. Module Architecture

### 3.1 Package structure

```
domain/financial_statements/
  __init__.py
  result.py                  # FinancialStatementsResult + per-period dataclasses
  inputs.py                  # FinancialStatementsConfig (accounting standard, currency, year-end)
  excel_mapping.py           # Excel row constants + per-row label/source metadata
  assembly.py                # Top-level: takes WaterfallResult + auxiliary, returns FinancialStatementsResult
  pnl.py                     # P&L assembly (R8-R50)
  balance_sheet.py           # BS assembly + balance check invariant
  pf_cash_waterfall.py       # CF reconstruction (R20-R119) — consumes C1d audit fields
  tax_bridge.py              # Book→tax bridge, loss carry-forward roll, accrued CIT
  retained_earnings.py       # RE roll-forward (period NI - dividends declared)
  reconciliation.py          # Excel parity diff calculator
  templates/
    __init__.py
    croatia.py               # Croatia: CIT 18%, 5y carry-fwd, thin-cap, H2 cash, legal reserve 5%
    # future: france.py, italy.py, etc.
  tests/
    test_assembly_runtime_safety.py     # asserts WaterfallResult bit-identical pre/post import
    test_tuho_pnl_parity.py             # ±0.5 kEUR per row
    test_oborovo_pnl_parity.py
    test_tuho_balance_check.py          # BS R33 ≤ 0.01 kEUR
    test_tax_bridge_loss_carryforward.py
    test_pf_cash_waterfall_audit_field_consistency.py
```

### 3.2 Layering

```
EXISTING RUNTIME ENGINES (untouched)
  ├─ revenue/         → revenue per period
  ├─ opex/            → OPEX per period
  ├─ construction/    → gross fixed assets, IDC, opening balances (diagnostic)
  ├─ depreciation*    → book depreciation per period       
  ├─ financing/       → senior debt schedule (interest, principal, balance)
  ├─ tax/             → CIT (existing, may be partially superseded in Stage 4)
  ├─ waterfall/       → orchestrator producing WaterfallResult with C1d audit fields
  ├─ shl_fcf_waterfall→ SHL cash mechanics (Phase 7L)
  └─ distribution_account → R98/R99/R100 (Phase 7M target for runtime)
                           │
                           ▼
                    WaterfallResult (existing schema; UNCHANGED)
                           │
                           ▼
              ╔═══════════════════════════════╗
              ║  domain/financial_statements/  ║   ◄── NEW LAYER
              ║  (ASSEMBLY, not calculation)   ║
              ╚═══════════════════════════════╝
                           │
                ┌──────────┼──────────┬──────────┐
                ▼          ▼          ▼          ▼
              P&L         BS    PF Cash WF   Tax Bridge
                           │
                           ▼
                    reporting/  (Excel export, PDF, FID deck)
```

### 3.3 Strict assembly contract

**The Financial Statements layer is forbidden from:**
- Modifying `WaterfallResult` or any upstream dataclass
- Importing from `app/`
- Re-computing values that exist in upstream results (must consume, not duplicate)
- Adding fields to `WaterfallPeriod` or `ProjectInfo`
- Introducing new ProjectInfo flags in Stages 1-3

**The Financial Statements layer is permitted to:**
- Read any field on `WaterfallResult` or any upstream result
- Compute roll-forward state internally (RE, accumulated dep, loss carry-fwd buckets, distribution account balance, cash balance)
- Produce a new `FinancialStatementsResult` containing per-period and annual rollups
- Expose Excel-mapped audit data for reconciliation tests
- Add Stage 4+ flags (`use_tax_bridge_engine`) ONLY when runtime migration begins

---

## 4. Source Ownership Decisions

| Line item | Source owner | SoT classification |
|---|---|---|
| Revenue components | `revenue` engine | runtime SoT |
| OPEX line items | `opex` engine | runtime SoT |
| Book depreciation | `depreciation_engine` (today in app/, migrate to domain) | runtime SoT |
| Tax depreciation | `tax_bridge` (Stage 4) | NEW runtime SoT |
| Senior interest (P&L + CF) | `financing/sculpting_iterative` | runtime SoT |
| Senior principal | `financing/sculpting_iterative` | runtime SoT |
| Senior balance (BS) | `financing/sculpting_iterative` closing | runtime SoT |
| SHL gross interest (P&L) | `shl_engine` / `shl_fcf_waterfall` | runtime SoT |
| SHL cash interest (CF) | `shl_engine` / `shl_fcf_waterfall` | runtime SoT |
| SHL PIK | `shl_engine` / `shl_fcf_waterfall` | runtime SoT |
| SHL balance (BS) | `shl_engine` / `shl_fcf_waterfall` closing | runtime SoT |
| Fiscal reintegration | `tax/reintegration` (formalize per regime) | runtime SoT |
| Loss carry-forward roll | `tax_bridge` (Stage 4) | NEW runtime SoT |
| Accrued CIT | `tax_bridge` (Stage 4) | NEW runtime SoT |
| Cash CIT timing | `tax_bridge` (Stage 4) | NEW runtime SoT (replaces tax_engine H2 logic) |
| EBIT, EBT, NI | `financial_statements/pnl` | derived |
| Retained Earnings (cum) | `financial_statements/retained_earnings` | derived |
| Accumulated Depreciation | `financial_statements/balance_sheet` | derived |
| Net Fixed Assets | `financial_statements/balance_sheet` | derived |
| Distribution Account (R98) | C1d audit / `distribution_account` engine (Stage 5) | audit → runtime SoT |
| R99/R100/R102 | `distribution_account` engine (Stage 5) | audit → runtime SoT |
| R104, R106, R119 | `waterfall_engine` (existing) | runtime SoT |
| Cash balance (BS) | `financial_statements/balance_sheet` (residual) | derived |
| Balance check | `financial_statements/balance_sheet` invariant | derived (asserted ≤ 0.01) |

---

## 5. P&L Schema

```python
@dataclass(frozen=True)
class PnLPeriodResult:
    period_index: int
    date: date
    year_index: int
    period_in_year: int
    
    # Operating (from revenue + opex engines)
    revenue_total_keur: float                 # R8
    revenue_breakdown: dict[str, float]       # ppa/merchant/co2/balancing
    opex_keur: float                          # R10 (positive = expense)
    local_tax_keur: float                     # R11
    wht_on_interest_keur: float               # R12
    depreciation_book_keur: float             # R13 (from depreciation_engine)
    total_expenses_keur: float                # R14 = R10+R11+R12+R13
    ebit_keur: float                          # R16 = R8 - R14
    
    # Financing (from senior + SHL engines)
    interest_income_keur: float               # R19+R20-R21
    senior_interest_expense_keur: float       # R24
    senior_refi_interest_expense_keur: float  # R25
    junior_interest_expense_keur: float       # R26
    shl_interest_expense_keur: float          # R27 GROSS
    other_interest_expense_keur: float        # R28
    financial_earnings_keur: float            # R30
    
    # Pre-tax
    ebt_keur: float                           # R32 = R16 + R30
    
    # Tax bridge (from tax_bridge module)
    fiscal_reintegration_keur: float          # R34
    taxable_income_keur: float                # R35 = R32 + R34
    loss_brought_forward_keur: float          # R36
    loss_used_keur: float                     # R37
    loss_closing_keur: float                  # R38
    loss_carriable_keur: float                # R39 (5y cap applied)
    taxable_profit_keur: float                # R41 = max(0, R35 - R37)
    cit_accrued_keur: float                   # R43 = R44 (positive = expense)
    
    # Bottom line
    net_income_keur: float                    # R46 = R32 - R44
    legal_reserve_movement_keur: float        # R48 (jurisdiction rule)
    dividend_declared_keur: float             # R50 (mirror of CF R119 for this period)
    retained_earnings_movement_keur: float    # R49 = R46 - R48 - R50

@dataclass(frozen=True)
class PnLAnnualResult:
    year: int
    # Same fields as PnLPeriodResult but summed for H1+H2
    # Used for Excel-style annual reporting
```

---

## 6. Balance Sheet Schema

```python
@dataclass(frozen=True)
class BalanceSheetPeriodResult:
    period_index: int
    date: date
    is_period_end: bool                       # True for EoP, mirrors BS R2
    
    # Assets
    gross_fixed_assets_keur: float            # R8 (constant from COD; capex closing)
    accumulated_depreciation_keur: float      # R9 (cumulative book depreciation to date)
    net_fixed_assets_keur: float              # R10 = R8 - R9
    dsra_balance_keur: float                  # R12 (from dsra_engine)
    jdsra_balance_keur: float                 # R13
    distribution_account_keur: float          # R14 (cumulative R100; C1d audit)
    cash_keur: float                          # R15 (residual)
    total_assets_keur: float                  # R17 = R10 + R12 + R13 + R14 + R15
    
    # Liabilities + Equity
    share_capital_keur: float                 # R21 (constant)
    legal_reserve_keur: float                 # R22 (cumulative)
    retained_earnings_cumulative_keur: float  # R23 (cumulative NI - dividends declared)
    shl_balance_keur: float                   # R24 (from SHL ledger closing)
    junior_balance_keur: float                # R25
    senior_balance_keur: float                # R26 (from senior schedule closing)
    refinancing_keur: float                   # R27
    short_term_loan_keur: float               # R29
    total_liabilities_equity_keur: float      # R31
    
    # Invariant
    balance_check_keur: float                 # R33 = R17 - R31 (assert ≤ 0.01 abs)
```

---

## 7. PF Cash Waterfall Schema

```python
@dataclass(frozen=True)
class PFCashWaterfallPeriodResult:
    period_index: int
    date: date
    
    # Operating cash (CF R20-R40)
    revenue_cash_keur: float                  # R20
    co2_cash_keur: float                      # R36 (subset of R20 for visibility)
    opex_cash_keur: float                     # R38
    ebitda_cash_keur: float                   # R40
    
    # Cash interest + tax (CF R63-R67)
    senior_cash_interest_keur: float          # R63
    interest_on_cash_keur: float              # R66
    cash_cit_keur: float                      # R67 (from tax_bridge in Stage 4)
    
    # FCF Banks (R69)
    fcf_banks_keur: float                     # R69 (consumed from C1d audit field)
    
    # Senior + reserves (R70-R82)
    senior_total_ds_keur: float               # R70 (interest + principal)
    dsra_funding_keur: float                  # R75
    dsra_release_keur: float                  # R76
    jdsra_funding_keur: float                 # R83
    
    # FCF Junior + adjustments (R84-R96)
    fcf_junior_keur: float                    # R84 (C1d audit)
    junior_ds_keur: float                     # R85
    other_cash_keur: float                    # R96
    
    # Distribution Account waterfall (R98-R102)
    distribution_account_pre_lockup_keur: float   # R98 (C1d audit)
    lockup_applied: bool
    lockup_reason: str | None
    fcf_for_shl_keur: float                   # R99 (C1d audit)
    carryforward_to_next_period_keur: float   # R100 (C1d audit)
    fcf_for_shl_input_keur: float             # R102 = R99 (strict identity)
    
    # SHL waterfall (R104)
    shl_cash_interest_keur: float
    shl_pik_keur: float
    shl_principal_keur: float
    net_shl_cash_outflow_keur: float          # R104
    
    # Dividends (R106-R119)
    fcf_for_dividends_keur: float             # R106
    wht_on_dividends_keur: float
    net_dividends_keur: float                 # R119
    
    # Audit identities (asserted)
    cf_r99_equals_r102: bool                  # invariant
    cf_r98_equals_r84_plus_prior_r100: bool   # invariant
```

---

## 8. Tax Bridge Schema

```python
@dataclass(frozen=True)
class TaxBridgePeriodResult:
    period_index: int
    year_index: int
    period_in_year: int
    
    # Book side (from upstream)
    ebt_keur: float                           # P&L R32
    book_depreciation_keur: float             # P&L R13 (Dep R30)
    
    # Tax basis adjustments
    non_deductible_depreciation_keur: float   # = book - tax depreciation
    tax_depreciation_keur: float              # Dep R31 (Unlevered)
    ebt_tax_basis_keur: float                 # = EBT + non_deductible_depreciation
    
    # Reintegration (from tax/reintegration)
    thin_cap_disallowed_shl_interest_keur: float    # R59 thin-cap excess
    other_reintegration_keur: float
    fiscal_reintegration_total_keur: float    # R34
    
    # Taxable income
    taxable_income_keur: float                # R35
    
    # Loss carry-forward (Croatia: 5y rolling)
    loss_buckets_keur: tuple[tuple[int, float], ...]   # [(year_created, amount_remaining)]
    loss_brought_forward_keur: float          # R36 (sum of buckets)
    loss_used_this_period_keur: float         # R37 (FIFO; oldest bucket consumed first)
    losses_dropping_off_5y_keur: float        # losses older than 5y → expire
    loss_closing_keur: float                  # R38
    carriable_losses_keur: float              # R39 (= R38 minus expired)
    
    # CIT
    taxable_profit_keur: float                # R41 = max(0, R35 - R37)
    cit_rate: float                           # 0.18 for Croatia
    cit_accrued_keur: float                   # R44
    
    # Cash timing (Stage 4)
    cit_cash_this_period_keur: float          # CF R67 (H2-of-year-following timing)
    cit_payable_balance_keur: float           # accrued - paid (BS implicit)
```

---

## 9. Runtime Integration Strategy

### Phased migration

```
Stage 1 (THIS PR): docs-only design
            │
            ▼
Stage 2: offline P&L generator
            ├─ tax_bridge.py computes Excel-parity tax rows AUDIT-ONLY
            ├─ pnl.py assembles P&L from runtime + tax_bridge
            ├─ no flags, no runtime change
            └─ acceptance: TUHO P&L rows within ±0.5 kEUR
            │
            ▼
Stage 3: BS + PF Cash Waterfall assembly + Excel export
            ├─ balance_sheet.py with R33 invariant
            ├─ pf_cash_waterfall.py reconstructs CF sheet from C1d audit fields
            ├─ reporting/excel exports P&L, BS, CF sheets in TUHO/Oborovo layout
            └─ acceptance: BS balance check ≤ 0.01, CF rows match Excel ±0.5
            │
            ▼
Stage 4: tax_bridge BECOMES runtime source
            ├─ flag use_tax_bridge_engine: bool = False
            ├─ when on: tax_bridge replaces current tax engine accrued CIT
            ├─ when on: rolling 5y loss carry-forward replaces flat prior_tax_loss_keur
            ├─ when on: cash CIT R67 driven by tax_bridge timing
            └─ acceptance: TUHO/Oborovo total cash CIT within ±0.5 kEUR of Excel; runtime distribution gap closes by additional ~0.5 percentage points
            │
            ▼
Stage 5: R99 runtime source from distribution_account engine
            ├─ flag use_r99_runtime_source: bool = False
            ├─ when on: distribution_account/engine.py computes R98→R99→R100 from upstream
            ├─ when on: shl_fcf_waterfall consumes computed R99 instead of fixture
            └─ acceptance: computed R99 within ±2 kEUR per period of Phase 7L fixture
            │
            ▼
Stage 6 (FUTURE): factory opt-in
            ├─ TUHO factory: use_tax_bridge_engine=True, use_r99_runtime_source=True
            ├─ Oborovo: opt in only after independent Excel reconciliation
            └─ acceptance: TUHO distribution within ±0.5% of Excel R119
```

### Why this order

1. **Stage 2 produces a working P&L that mirrors Excel structurally** without touching runtime — proves the assembly contract.
2. **Stage 3 closes the auditability loop** by mirroring all three statement sheets — bankers can read the output as a standard model.
3. **Stage 4 closes the cash CIT timing residual** explicitly identified as a remaining gap in Phase 7K/7L reviews.
4. **Stage 5 closes the R99 fixture dependency** that Phase 7L explicitly left as future work.
5. **Stage 6 ships the calibration** with a fully-aligned engine, not a manually-tuned one.

Each stage is **independently revertible** and **default-off**.

---

## 10. Risks

### Risk 1 — Overfitting TUHO/Oborovo (both Croatian)

Both reference projects use Croatian tax regime (CIT 18%, 5y carry-forward, thin-cap on indebtedness ratio). A French or Italian project will need its own template.

**Mitigation:** `templates/` folder per regime; core `tax_bridge.py` is regime-agnostic. Croatia template ships first; pattern proven before adding France/Italy.

### Risk 2 — Circularity (book→tax→cash→DSCR→sculpting→...)

Tax bridge needs EBT, EBT needs senior interest, senior interest needs sculpting, sculpting needs DSCR, DSCR needs cash CFADS, cash CFADS needs cash CIT, cash CIT needs accrued CIT (back to tax bridge).

**Mitigation:** sculpting consumes a SIMPLE cash CIT estimate (current `tax_engine` behavior). Tax bridge produces EXACT accrued CIT for statements only, until Stage 5 when the simplified estimate is replaced with bridge output. Thin-cap test uses prior-period equity/EBITDA — no same-period circularity.

### Risk 3 — Duplicated logic between `reporting/financial_statements.py` and new module

A `reporting/financial_statements.py` file already exists with "Income Statement / Balance Sheet / Cash Flow Statement" docstring. Risk of duplication.

**Mitigation:** assess existing file's scope. If it's a partial bank-format report, **subsume it into the new module** rather than maintaining two parallel reporters. Migration is a Stage 2 task.

### Risk 4 — Tax basis ≠ book basis (depreciation)

Excel Dep R30 ≠ R31 by ~92.68 kEUR/period in TUHO. Python currently has only one depreciation. Tax bridge must distinguish.

**Mitigation:** explicit `tax_depreciation_keur` field on `TaxBridgePeriodResult`. Default initially equals book depreciation; Stage 4 wires the real tax depreciation from Dep R31-equivalent calculation. Croatian rule for IDC capitalization (R31 lower than R30 because IDC is NOT tax-deductible as depreciation in early periods) is country-specific — encoded in `templates/croatia.py`.

### Risk 5 — Audit complexity

Excel export with P&L, BS, CF — each must reconcile. If any drifts, the whole export looks suspect.

**Mitigation:** `reconciliation.py` produces explicit per-row delta table; CI asserts max delta < 0.5 kEUR per row across full horizon. Phase 7 calibration discipline holds.

### Risk 6 — Multi-lender readiness

Excel has single senior + single SHL. Future multi-tranche senior (commercial + ECA + multilateral) splits P&L R24 into multiple interest lines, BS R26 into multiple debt lines, CF R63 into multiple cash interest lines.

**Mitigation:** data model uses `dict` for `interest_breakdown` and `debt_breakdown`; future multi-lender additions are additive without schema break.

### Risk 7 — Performance

Stages 2-3 add ~30-60 periods of statement assembly per run. For Monte Carlo (10k runs), additive cost is non-trivial.

**Mitigation:** assembly is opt-in via `compute_statements: bool = True` parameter on `WaterfallRunner.run()`. Off for portfolio batch / sensitivity runs. On for single-project audit runs.

### Risk 8 — Sponsor layer compatibility

`domain/sponsor/` already has 4,616 LOC of IRR/XIRR/preferred return logic. Statements module must not conflict with sponsor-side computation of dividend allocation.

**Mitigation:** sponsor module continues to own multi-investor allocation. Statements module mirrors `R119 Net Dividends` (project-level total) on P&L R50; sponsor allocation downstream is independent.

### Risk 9 — SaaS reporting implications

Bankable users will request: PDF audit pack, Excel export matching Excel layout, query historical runs, version control on inputs. Statements module is the foundation for all of this.

**Mitigation:** `excel_mapping.py` is the integration point — exporters consume row labels and values from this module, not raw `WaterfallResult`. Audit trail (per-period source-of-truth labels) ships in Stage 2.

---

## 11. Implementation Roadmap

| Stage | Branch | Scope | Acceptance | Estimated effort |
|---|---|---|---|---|
| **1** | `phase6-financial-statements-module-design` | ✓ this PR (docs-only) | n/a | done |
| **2** | `phase6-financial-statements-offline-pnl` | P&L + tax_bridge (audit) | TUHO P&L ±0.5 kEUR per row; Oborovo same; runtime unchanged | 1 PR |
| **3** | `phase6-financial-statements-balance-sheet-and-cf` | BS + PF cash waterfall + Excel export | BS R33 ≤ 0.01; CF rows ±0.5; export structurally matches Excel | 1 PR |
| **4** | `phase6-tax-bridge-runtime-flag` | `use_tax_bridge_engine` flag | Default off; flag-on TUHO closes cash CIT timing gap; distribution drift ≤ 0.5% | 1-2 PRs |
| **5** | `phase6-r99-runtime-source-flag` | `use_r99_runtime_source` flag | Default off; flag-on computed R99 within ±2 kEUR of fixture | 1 PR |
| **6** | `phase6-tuho-factory-opt-in` | TUHO opts into Stage 4+5 flags | TUHO distribution ±0.5% of Excel R119 | 1 PR |

Total: ~6 PRs over the next 2-4 months at current cadence.

---

## 12. Recommended Next Implementation Branch

**Branch:** `phase6-financial-statements-offline-pnl`

**Scope:** Stage 2 only — offline P&L generator + tax bridge audit. No flags, no runtime change.

**Files to add:**
- `domain/financial_statements/__init__.py`
- `domain/financial_statements/result.py` (PnL/BS/CF/TaxBridge per-period + annual + aggregate)
- `domain/financial_statements/inputs.py` (FinancialStatementsConfig)
- `domain/financial_statements/excel_mapping.py` (row constants per Excel sheet)
- `domain/financial_statements/assembly.py` (top-level entry)
- `domain/financial_statements/pnl.py`
- `domain/financial_statements/tax_bridge.py`
- `domain/financial_statements/retained_earnings.py`
- `domain/financial_statements/templates/__init__.py`
- `domain/financial_statements/templates/croatia.py`
- `tests/test_financial_statements_assembly_runtime_safety.py`
- `tests/test_financial_statements_tuho_pnl_parity.py`
- `tests/test_financial_statements_oborovo_pnl_parity.py`
- `tests/test_financial_statements_tax_bridge_loss_carryforward.py`

**Files explicitly NOT to touch:**
- `app/project_factories.py`
- `domain/waterfall/waterfall_engine.py` (NO new fields)
- `domain/inputs.py` (NO new flags in Stage 2)
- `domain/tax/*` (read from; do not modify; Stage 4 modifies)
- `domain/shl_fcf_waterfall.py`
- `domain/revenue/*`
- `domain/opex/*`
- `domain/construction/*`
- `domain/distribution_account/*`
- UI / persistence / cache

**Hard acceptance gates for Stage 2 PR:**
1. TUHO P&L rows R8-R50 within ±0.5 kEUR per period vs Excel reference
2. Oborovo P&L rows within ±0.5 kEUR per period vs Excel reference
3. `WaterfallResult` for TUHO and Oborovo bit-identical before/after `from domain.financial_statements import ...`
4. No new flags on `ProjectInfo`
5. No imports from `app/` in `domain/financial_statements/`
6. All 168+ existing regression tests continue to pass
7. New tests: ≥ 15 covering P&L assembly, loss carry-forward roll, runtime safety
8. Croatia template encodes: CIT 18%, 5y rolling carry-fwd, thin-cap test on indebtedness ratio, H2 cash payment

---

## Appendix A — Decision Summary by Question

| Question | Answer |
|---|---|
| 1. Excel reconstruction | P&L, BS, PF cash waterfall, tax bridge fully mapped; circularity risks identified and resolved by sequential period processing |
| 2. Sheet interaction mapping | CapEx+IDC→Dep→P&L; OpEx→P&L+CF; DS→P&L+CF; CF (R67 cash CIT)→P&L; P&L NI→BS RE; CF balances→BS |
| 3. Module architecture | `domain/financial_statements/` with assembly/pnl/balance_sheet/pf_cash_waterfall/tax_bridge submodules; templates/croatia.py |
| 4. Source ownership | 36 runtime SoT items (consumed unchanged) + 5 NEW runtime SoT (tax bridge, loss carry-fwd, accrued/cash CIT, R99 in Stage 5) + 18 derived rows |
| 5. P&L design | PnLPeriodResult with Excel-row-mapped fields; assembly from upstream |
| 6. BS design | BalanceSheetPeriodResult with balance_check_keur ≤ 0.01 invariant |
| 7. PF Cash Waterfall design | PFCashWaterfallPeriodResult reconstructing R20-R119 from C1d audit fields and upstream |
| 8. Tax bridge design | Book→tax depreciation distinction; rolling 5y loss buckets (FIFO); thin-cap reintegration; H2 cash timing |
| 9. Runtime integration | Strictly downstream in Stages 1-3; runtime SoT migration in Stage 4-5 behind default-off flags |
| 10. Excel mapping matrix | Full matrix in Section 2 |
| 11. Risks | 9 risks identified; templates folder + strict layering + opt-in flags mitigate |
| 12. Implementation phases | 6 stages, ~6 PRs, 2-4 months |

## Appendix B — Empirical Excel evidence

| Observation | Source |
|---|---|
| TUHO sheet structure: P&L, BS, CF, DS, Dep, OpEx, CapEx, IDC | Direct openpyxl inspection of `20260330_TUHO_BP.xlsm` |
| Oborovo identical sheet structure | Direct openpyxl inspection of `20260414_BP_Oborovo_Sensitivity_FINAL_for_PPT.xlsm` |
| Initial loss carry-forward R36 op_idx=0 = -3,568.69 kEUR | Matches TUHO construction SHL IDC exactly |
| Cash CIT R67 first non-zero col 33 (2042-12-31) | H2 timing confirmed empirically |
| Book vs tax depreciation: R30=1,845.44 vs R31=1,752.76 at op_idx=0 | Tax basis distinction is structural in Excel |
| BS R33 balance check = 0 every period | Excel enforces accounting integrity per period |
| R99 = R102 across all periods | Confirmed in Phase 7F (R99/R102 share identical values) |
| Cumulative R100 contributes to BS R14 Distribution Account | Carryforward flow from CF feeds BS |

## Appendix C — Hard rejection compliance

This PR introduces:
- ✓ Zero runtime formula changes
- ✓ Zero waterfall behavior changes
- ✓ Zero tax formula changes
- ✓ Zero SHL/R99 opt-ins
- ✓ Zero project factory changes
- ✓ Zero UI/cache changes
- ✓ One file added: `docs/phase6_financial_statements_assembly_design.md`

