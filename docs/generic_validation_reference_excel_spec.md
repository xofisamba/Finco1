# Generic Validation Reference Excel Specification

**Status:** Draft for modeler review  
**Audience:** External financial modeler building reference Excel workbooks for Generic Solar and Generic Wind templates  
**Use case:** External validation reference for the Finco1 Generic Validation Pack (G1)  
**Document version:** 0.1 (2026-06-18)

---

## 1. Purpose

The reference Excel workbooks produced under this specification will be used **only** as an external validation reference for the Generic Solar and Generic Wind templates inside the Finco1 model. They are not customer deliverables, not sales collateral, and not a replacement for the runtime model. They are an **independent hand-calculation**, written in plain Excel formulas, against which Finco1's runtime output will be compared cell-by-cell.

The modeler should approach this as an auditor would: build the model from first principles using the input assumptions listed below, expose every intermediate calculation as a visible formula, and avoid any closed-form shortcuts that cannot be traced back to a formula.

---

## 2. Required Workbook Tabs

The workbook must contain the following 10 tabs in this order. Tab names must match exactly (case-sensitive, no spaces other than shown).

| # | Tab Name | Purpose |
|---|---|---|
| 1 | `Inputs` | All driver values, scenario controls, and global assumptions |
| 2 | `CapEx` | Capital expenditure schedule and total |
| 3 | `IDC` | Interest during construction, debt drawdown schedule |
| 4 | `OpEx` | Operating cost ladder (Y1 base + inflation) |
| 5 | `Revenue` | PPA revenue, merchant revenue, market price curve |
| 6 | `Debt Service` | Sculpted debt schedule, interest, principal, balance |
| 7 | `P&L` | Profit and loss: Revenue, EBITDA, EBIT, Tax |
| 8 | `Cash Flow` | Free cash flow, CFADS, IRR computations |
| 9 | `Equity` | Equity cash flows, SHL schedule, Equity IRR |
| 10 | `Summary` | One-page KPI summary mirroring Finco1 dashboard output |

Each tab must use a consistent grid layout. Suggested conventions:
- Column A: row labels
- Column B: units (kEUR, EUR/MWh, %, etc.)
- Columns C onward: period-by-period values (semiannual periods)
- Rows below data: subtotals, totals, and named output cells

---

## 3. Exact Input Assumptions

### 3.1 Generic Solar Inputs

| Group | Field | Value | Unit |
|---|---|---|---|
| **Project** | Project name | "Generic Solar PV" | string |
| | Company | "SolarCo" | string |
| | Code | "SOLAR-001" | string |
| | Country | "DE" | ISO |
| | Financial close | 2030-01-01 | date |
| | COD date | 2031-01-01 | date |
| | Construction period | 12 | months |
| | Horizon | 25 | years |
| | Period frequency | Semiannual | enum |
| **Technical** | Capacity | 50 | MW |
| | Yield scenario | P_50 | enum |
| | Operating hours P50 | 1500 | hrs/yr |
| | Operating hours P90 10y | 1400 | hrs/yr |
| | PV degradation | 0.4% | /yr |
| | Plant availability | 99% | ratio |
| | Grid availability | 99% | ratio |
| **CapEx** | Solar Modules | 20,000 | kEUR |
| | Inverters | 3,000 | kEUR |
| | Civil Works | 5,000 | kEUR |
| | Grid Connection | 2,000 | kEUR |
| | Soft Costs | 3,000 | kEUR |
| | Total hard capex | 33,000 | kEUR |
| | IDC | 0 | kEUR |
| | Bank fees | 0 | kEUR |
| **CapEx Spending Profile** | Modules | 50% in Y0, 50% in Y1-H1 | shares |
| | Inverters | 50% in Y0, 50% in Y1-H1 | shares |
| | Civil Works | 30% in Y0, 40% in Y1-H1, 30% in Y1-H2 | shares |
| | Grid Connection | 50% in Y0, 50% in Y1-H1 | shares |
| | Soft Costs | 100% in Y0 | shares |
| **OpEx (Y1)** | Technical Management | 150 | kEUR |
| | Insurance | 100 | kEUR |
| | Maintenance | 80 | kEUR |
| | Lease & Tax | 50 | kEUR |
| | Total Y1 OPEX | 380 | kEUR |
| | Annual inflation | 2% | ratio |
| **Revenue** | PPA base tariff | 55 | EUR/MWh |
| | PPA term | 10 | years |
| | PPA indexation | 2% | /yr |
| | Market scenario | Central | enum |
| | Market price Y1 | 60 | EUR/MWh |
| | Market price Y2 | 61 | EUR/MWh |
| | Market price escalation | 2% | /yr |
| | CO2 enabled | No | boolean |
| **Financing** | Share capital | 500 | kEUR |
| | Share premium | 0 | kEUR |
| | SHL amount | 5,000 | kEUR |
| | SHL rate | 8% | /yr |
| | Gearing ratio (target) | 75% | ratio |
| | Senior tenor | 15 | years |
| | Base rate | 3% | /yr |
| | Margin | 250 | bps |
| | Floating share | 30% | ratio |
| | Fixed share | 70% | ratio |
| | Hedge coverage | 80% | ratio |
| | Target DSCR | 1.20 | ratio |
| | Lockup DSCR | 1.10 | ratio |
| | DSRA months | 6 | months |
| | Debt sizing method | DSCR_SCULPT | enum |
| | Equity IRR method | EQUITY_ONLY | enum |
| **Tax** | Corporate tax rate | 25% | ratio |
| | Loss carryforward | 5 | years |
| | ATAD EBITDA limit | 30% | ratio |
| | ATAD min interest | 3,000 | kEUR |

### 3.2 Generic Wind Inputs

Same structure as Solar, with these substitutions:

| Group | Field | Value | Unit |
|---|---|---|---|
| **Project** | Project name | "Generic Wind Farm" | string |
| | Company | "WindCo" | string |
| | Code | "WIND-001" | string |
| | Construction period | 18 | months |
| | COD date | 2031-07-01 | date |
| **Technical** | Operating hours P50 | 3,000 | hrs/yr |
| | Operating hours P90 10y | 2,700 | hrs/yr |
| | PV degradation | 0% | /yr |
| **CapEx** | Wind Turbines | 30,000 | kEUR |
| | Civil Works | 6,000 | kEUR |
| | Grid Connection | 3,000 | kEUR |
| | Soft Costs | 4,000 | kEUR |
| | Total hard capex | 43,000 | kEUR |
| **CapEx Spending Profile** | Turbines | 40% in Y0, 60% in Y1-H1 | shares |
| | Civil Works | 30% in Y0, 40% in Y1-H1, 30% in Y1-H2 | shares |
| | Grid Connection | 50% in Y0, 50% in Y1-H1 | shares |
| | Soft Costs | 100% in Y0 | shares |
| **OpEx (Y1)** | Technical Management | 200 | kEUR |
| | Insurance | 150 | kEUR |
| | Maintenance | 120 | kEUR |
| | Lease & Tax | 80 | kEUR |
| | Total Y1 OPEX | 550 | kEUR |
| **Revenue** | PPA base tariff | 60 | EUR/MWh |
| | PPA term | 12 | years |
| | PPA indexation | 2% | /yr |
| | Market price Y1 | 65 | EUR/MWh |
| | Market price escalation | 2% | /yr |
| | Wind balancing cost | 8 | EUR/MWh |
| | CO2 enabled | Yes | boolean |
| | CO2 price | 5 | EUR/MWh |

---

## 4. Required Output Cells

The following 15 output cells must be exposed on the `Summary` tab. They are the Tier-1 anchor set for the Generic Validation Pack.

### 4.1 Amounts (kEUR)

| # | Cell Name | Sheet | Cell Ref (suggested) | Finco Source |
|---|---|---|---|---|
| 1 | `total_revenue_keur` | Summary | `C5` | `result.total_revenue_keur` |
| 2 | `total_opex_keur` | Summary | `C6` | `result.total_opex_keur` |
| 3 | `total_ebitda_keur` | Summary | `C7` | `result.total_ebitda_keur` |
| 4 | `total_capex_keur` | Summary | `C8` | `project_inputs.capex.total_capex` |
| 5 | `idc_keur` | Summary | `C9` | `capex.idc_keur` |
| 6 | `bank_fees_keur` | Summary | `C10` | `capex.bank_fees_keur` |
| 7 | `senior_debt_keur` | Summary | `C11` | `result.sculpting_result.debt_keur` |
| 8 | `senior_debt_service_p1_keur` | Summary | `C12` | `result.periods[first_op].senior_ds_keur` |
| 9 | `senior_debt_service_p2_keur` | Summary | `C13` | `result.periods[first_op+1].senior_ds_keur` |
| 10 | `senior_debt_service_p3_keur` | Summary | `C14` | `result.periods[first_op+2].senior_ds_keur` |

### 4.2 Ratios

| # | Cell Name | Sheet | Cell Ref (suggested) | Finco Source |
|---|---|---|---|---|
| 11 | `avg_dscr` | Summary | `C15` | `result.actual_avg_dscr` |
| 12 | `min_dscr` | Summary | `C16` | `result.actual_min_dscr` |
| 13 | `project_irr` | Summary | `C17` | `result.project_irr` |
| 14 | `equity_irr` | Summary | `C18` | `result.equity_irr` |
| 15 | `realized_gearing` | Summary | `C19` | derived ratio (see §5.9) |

All 15 cells must contain live formulas (not hardcoded values).

---

## 5. Required Formulas (Plain-English Specification)

### 5.1 Generation and Revenue

**Generation per period (MWh)**:
```
generation_period = capacity_mw × operating_hours_p50 / 2 × (1 - pv_degradation)^year
```

Where:
- `year` is the operating year number (1-based)
- The `/2` reflects semiannual periods (50% of annual generation each half)
- For Wind: `pv_degradation = 0`, so `(1 - 0)^year = 1` (no degradation)
- For Solar: `pv_degradation = 0.004`, so Y5 generation = Y1 generation × 0.984

**PPA tariff at year**:
```
ppa_tariff_year = ppa_base_tariff × (1 + ppa_index)^(year - 1)
```

**PPA revenue per period** (in PPA window, year ≤ ppa_term_years):
```
ppa_revenue = generation_period × ppa_tariff_year / 1000   [kEUR]
```

The `/1000` converts EUR to kEUR (since generation is in MWh and tariff in EUR/MWh, product is in EUR; divide by 1000 for kEUR).

**Merchant revenue per period** (post-PPA, year > ppa_term_years):
```
merchant_revenue = generation_period × market_price_year / 1000
```

For Wind, subtract balancing cost and add CO2 revenue:
```
wind_revenue = (generation × market_price - generation × balancing_cost + generation × co2_price) / 1000
```

### 5.2 OPEX Inflation

**OPEX per period**:
```
opex_period = sum(opex_y1_amount_keur × (1 + annual_inflation)^(year - 1) for each opex item)
```

### 5.3 EBITDA

```
ebitda_period = revenue_period - opex_period
```

### 5.4 CFADS (Cash Flow Available for Debt Service)

```
cfads_period = ebitda_period - tax_period
```

Where `tax_period` is computed using the loss-carryforward mechanism described in §5.10.

### 5.5 DSCR

```
dscr_period = cfads_period / senior_ds_period
```

Where `senior_ds_period = senior_interest_period + senior_principal_period`.

**Min DSCR** = MIN over all operating periods where senior_ds > 0.
**Avg DSCR** = AVERAGE over all operating periods where senior_ds > 0.

### 5.6 DSCR Debt Sculpting

The senior debt amount is sized so that the resulting DSCR schedule's average (over operating periods with positive debt service) equals the target DSCR. The standard iterative approach:

1. Start with a candidate debt amount (e.g. gearing × total_capex).
2. Build the sculpting schedule: for each period, set senior_ds = cfads / target_dscr.
3. Track senior_balance forward: opening balance + drawdowns - principal repayments.
4. Recompute interest = balance × rate per period.
5. Adjust debt amount and iterate until convergence (typically <20 iterations).

**Important**: The modeler may use any equivalent iterative solver (Excel Solver, Goal Seek, manual bisection) but the final senior_debt amount must equal what the iterative DSCR-sculpt formula yields. Do NOT cap the result at gearing × capex unless the spec explicitly requires it.

### 5.6a Gearing Cap Binding: Rescale Convention (G1E)

For Generic Solar and Generic Wind, the gearing cap (`gearing_ratio × sizing_base`) is *below* the uncapped DSCR-sized debt amount, so the gearing cap binds:

```
dscr_debt        = NPV of debt-service capacity, uncapped (Section 5.6, step 2-5)
gearing_cap_keur = gearing_ratio × sizing_base_keur
senior_debt      = MIN(dscr_debt, gearing_cap_keur)     # gearing wins here
```

When `senior_debt < dscr_debt`, there are two structurally different ways to absorb the shortfall, and they produce different debt-service *shapes* (not different total principal — both repay exactly `senior_debt`):

- **Truncate-tenor convention (legacy bootstrap convention, deprecated by this revision)**: keep the original per-period debt-service-capacity row (`cfads_sizing / target_dscr`) unchanged, and let the smaller principal amortize faster. `senior_ds_period = MIN(capacity_period, opening_balance + interest_period)`. The realized DSCR stays exactly at `target_dscr` while debt is outstanding, then the debt pays off early (well before the stated senior tenor) and DSCR becomes undefined/`n/a` for the remaining tenor periods.
- **Schedule-rescale convention (runtime/production convention, now authoritative — see Section 6 rationale)**: scale the entire per-period debt-service-capacity row by `scale = senior_debt / dscr_debt` and amortize over the **full original tenor**:
  ```
  scale                  = MIN(1, senior_debt / dscr_debt)
  capacity_period_scaled = capacity_period × scale
  senior_ds_period       = MIN(capacity_period_scaled, opening_balance + interest_period)
  ```
  Because the schedule is rescaled instead of truncated, the realized DSCR is **flat at `target_dscr / scale`** (higher than `target_dscr`, since `scale < 1`) across the *entire* stated senior tenor, and debt is never paid off early.

`scale = 1` (no rescale, identical to the truncate convention) whenever the gearing cap does not bind. The rescale step only changes anything when `senior_debt < dscr_debt`.

**Required reference workbook formulas** (Debt Service tab):
```
C17 (Schedule rescale factor) = IF(C14 > 0, MIN(1, C16 / C14), 1)
E18:AH18 (Rescaled debt service capacity) = E13:AH13 × $C$17   [period columns, mirrors row 13's range]
E22:AH22 (Senior debt service) = MIN(E18:AH18, E20:AH20 + E21:AH21)   [was MIN(E13:AH13, ...) under the legacy truncate convention]
```
Row 13 (the uncapped capacity used to size `C14` via NPV) is left unchanged, to avoid a circular reference between the sizing NPV and the rescale factor that depends on the sizing result.

### 5.7 Senior Debt Service

For each operating period:
```
senior_interest_period = senior_balance_opening × (base_rate + margin_bps/10000)
senior_principal_period = senior_ds_period - senior_interest_period
senior_balance_closing = senior_balance_opening - senior_principal_period
```

The first three operating periods' senior_ds are the cells `senior_debt_service_p1_keur`, `_p2_keur`, `_p3_keur`.

### 5.8 Project IRR

Use Excel `XIRR`:
```
project_irr = XIRR(project_cashflow_series, project_date_series)
```

Where `project_cashflow_series` is the unlevered project cash flow (negative during construction, positive during operations, includes terminal value if any).

**Cash flow timing**: each period corresponds to a date 6 months apart (semiannual). Financial close 2030-01-01, COD 2031-01-01 (Solar) or 2031-07-01 (Wind), operating periods from COD onwards.

### 5.9 Realized Gearing

Derived ratio, not a runtime output:
```
realized_gearing_pct = (senior_debt_keur / total_capex_keur) × 100
```

### 5.10 Tax (Loss Carryforward)

```
taxable_profit_period = ebitda_period - depreciation_period - interest_period
if taxable_profit_period > 0:
    tax_period = taxable_profit_period × corporate_tax_rate
else:
    # apply loss carryforward
    loss_used = min(abs(taxable_profit_period), accumulated_loss_pool)
    accumulated_loss_pool -= loss_used
    tax_period = max(0, taxable_profit_period + loss_used) × corporate_tax_rate
```

**Depreciation** for the simplified model: straight-line over 20 years on hard capex basis.
```
annual_depreciation = total_hard_capex / 20
```

For semiannual periods, halve the annual figure.

**Important**: This is a simplified single-entity tax model. The modeler may use a more sophisticated depreciation schedule if documented in the workbook metadata, but the final corporate tax cash flow should match what the simplified formula yields within ±0.5% relative.

### 5.11 Equity IRR

```
equity_irr = XIRR(equity_cashflow_series, equity_date_series)
```

Where `equity_cashflow_series` includes:
- Initial equity investment (negative)
- SHL drawdowns and repayments (if applicable)
- Distributions to equity (positive)
- Terminal equity value (if any)

**Distributions** = operating cash flow after all debt service, taxes, and reserves.

---

## 6. Required Model Conventions

| # | Convention | Required |
|---|---|---|
| 1 | Currency unit | **kEUR** (thousand EUR) for all amounts |
| 2 | Period frequency | **Semiannual** (2 periods per year) |
| 3 | Date format | YYYY-MM-DD or DD/MM/YYYY (be consistent) |
| 4 | Decimal precision | 0 decimals on kEUR amounts, 4 decimals on ratios, 6 decimals on IRRs |
| 5 | No circular macros | All references via cell formulas only |
| 6 | No external workbook links | All data must be in this workbook |
| 7 | Formulas visible | All calculation cells must show formulas, not just values |
| 8 | Workbook recalculated | Save with `Ctrl+Alt+F9` forced recalc before submission |
| 9 | No hidden hardcoded outputs | Every "output" cell must be a formula |
| 10 | No VBA dependency | No macros required for the model to compute |
| 11 | No protected formula cells | Cells may be unprotected or password-free reviewable |
| 12 | Sheet protection | Recommended: protect all cells except Inputs (so reviewers can run sensitivities) |
| 13 | Named ranges | Use named ranges for clarity (e.g. `ppa_tariff`, `capacity_mw`) |
| 14 | Negative numbers | Show as `(123)` or `-123` (be consistent) |
| 15 | Color coding | Optional but recommended: blue for inputs, black for formulas |
| 16 | Gearing-cap-binding convention | **Schedule-rescale convention** (Section 5.6a) is authoritative whenever `senior_debt < dscr_debt`. Do NOT use the truncate-tenor convention. |

### 6.1 Why the Rescale Convention Is Authoritative for Generic Bootstrap Validation (G1E)

When Generic Solar/Wind's gearing cap binds, `domain/waterfall/waterfall_engine.py`'s `run_waterfall()` (the shared production sculpting/amortization engine) always rescales the debt-service-capacity schedule across the full senior tenor rather than truncating it (see the `scale = sizing_debt / dscr_debt` block). This is not a Generic-specific choice — it is shared engine behavior also exercised by the TUHO and Oborovo bootstrap projects, whose anchor parity already depends on it. Changing the engine to match the bootstrap workbooks' legacy truncate-tenor convention would risk regressing TUHO/Oborovo parity (out of scope and explicitly forbidden), whereas revising the two Generic reference workbooks to mirror the engine's convention is local, low-risk, and brings the *reference* in line with the one convention the runtime actually implements everywhere. The reference workbooks were a bootstrap stand-in built ahead of the engine's debt-sizing logic being finalized; this revision retires the bootstrap-era convention in favor of the now-confirmed production behavior.

### 6.2 Anchor Tolerance Rationale for Automated Parity Tests (G1B-ANCHOR-PARITY-TESTS)

`tests/test_g1b_generic_anchor_parity.py` compares `app.project_factories.create_default_solar_project()` / `create_default_wind_project()` runtime output against the G1E-recalculated golden fixtures. Two tolerance tiers are used, deliberately:

* **Tight tolerances** (`total_capex_keur`, `total_revenue_keur`, `total_opex_keur`, `total_ebitda_keur`, `idc_keur`, `bank_fees_keur`, `senior_debt_keur`, `realized_gearing`) reuse the near-Excel-grade tolerances already defined in the golden fixtures' own `initial_tolerances` block, because the runtime already agrees with the workbook on these to well under 0.2% in practice.
* **Wide, documented tolerances** (`avg_dscr`, `min_dscr`, `senior_debt_service_p1/p2/p3_keur`, `project_irr`, `equity_irr`) reflect a known, pre-existing methodology gap between the runtime's debt-sizing proxy (`max(0, ebitda * (1 - tax_rate))` used when computing the uncapped `dscr_debt` sizing capacity) and the Excel workbook's own sizing proxy (`MAX(0, EBITDA - Depreciation) * tax_rate`), which do not net out depreciation the same way. This gap predates G1E, is not introduced or fixed by it, and is out of scope for runtime/domain/factory code changes. The wide tolerances pin *current* runtime behavior (with headroom) so unrelated regressions are still caught, without asserting an Excel-grade match the runtime does not yet deliver.

**Project IRR specifically**: per the Generic bootstrap workbook's `Cash Flow` tab, Project IRR's cash-flow row (`C12 = CapEx + CFADS`) never includes senior debt service directly — but CFADS's tax line (`P&L!C15`, via `Pre-tax profit = EBITDA - Depreciation - Interest expense (actual)`) nets out the *actual* interest expense from the real debt schedule (`'Debt Service'!C21`). This means the workbook's nominally "unlevered" Project IRR is not fully debt-independent: any change to the debt-service schedule shape moves Project IRR by a few tenths of a percentage point through the interest tax shield, even though IRR's own cash-flow row is otherwise unlevered. This is a pre-existing bootstrap-workbook simplification (confirmed during G1E), not a defect introduced by the rescale-convention revision, and is out of scope to fix here — the test's absolute tolerance for `project_irr` is set wide enough to accommodate it.

---

## 7. Required Extraction Metadata

The modeler must deliver the workbook along with the following metadata (either as workbook properties or a companion `.md` file).

```yaml
workbook_name: "GenericSolar_BP_20260618.xlsx"
template: "Generic Solar"   # or "Generic Wind"
author: "Modeler Name"
organisation: "Modeler Org"
date_created: "YYYY-MM-DD"
version: "1.0"
finco_spec_version: "0.1"
finco_commit_at_creation: "<git SHA>"

deviations_from_spec: []   # list any deviations with rationale
known_limitations: []      # list any model limitations (e.g. simplified depreciation)
recalculation_method: "Excel Ctrl+Alt+F9"
rounding_convention: "0dp on kEUR, 4dp on ratios, 6dp on IRRs"

contact:
  email: "modeler@example.com"
  slack: "@modeler"
```

If a deviation is unavoidable (e.g. the modeler needs to use a slightly different depreciation schedule), it MUST be documented in `deviations_from_spec`. Finco will then either:
- Accept the deviation and adjust tolerances accordingly, OR
- Request a corrected workbook.

---

## 8. Validation Tolerance Expectations

The Finco comparison will use the following tolerances for the Tier-1 anchor set:

| Metric Class | Tolerance | Example |
|---|---|---|
| Amounts (kEUR) | **±0.5% relative**, min ±1.0 absolute | revenue 100,000 ± 500 kEUR |
| IDC | **±1.0% relative** | IDC 1,200 ± 12 kEUR |
| Bank fees | **±0.5% relative** | fees 500 ± 2.5 kEUR |
| Senior debt | **±0.5% relative** | debt 22,500 ± 112 kEUR |
| Period debt service | **±0.5% relative** | service 1,000 ± 5 kEUR |
| Project IRR | **±5 basis points absolute** | IRR 9.21% ± 0.05% |
| Equity IRR | **±5 basis points absolute** | IRR 14.20% ± 0.05% |
| Avg DSCR | **±0.01 absolute** | DSCR 1.66 ± 0.01 |
| Min DSCR | **±0.01 absolute** | DSCR 1.45 ± 0.01 |
| Realized gearing | **±0.5 percentage points absolute** | gearing 75% ± 0.5pp |

If a deliverable falls outside these tolerances, Finco will:
1. Re-run the comparison with relaxed tolerances to confirm intent
2. Document the divergence in `reports/validation_variance_log.jsonl`
3. Decide whether to:
   - Accept the divergence as a known model difference (e.g. rounding convention)
   - Investigate the Finco runtime for a bug
   - Investigate the reference Excel for an error
   - Adjust tolerances if both sides are correct

---

## 9. Open Questions for Modeler

Please confirm or clarify the following before commencing work:

1. **Depreciation schedule**: Is straight-line over 20 years acceptable? If not, what asset-class-specific depreciation schedule should be used (especially for Solar Modules vs Inverters)?

2. **IDC with `idc_keur = 0`**: With no IDC input, the spec implies construction-period interest is computed separately by the Excel model or is implicitly zero. Should the Excel model compute IDC from a drawdown × rate formula, or accept `idc_keur = 0` as the literal answer?

3. **Senior debt sizing iteration**: The spec requires DSCR_SCULPT with iterative convergence. Should the Excel model use Excel Solver, manual iteration, or an alternative closed-form approximation? Any choice is acceptable as long as the converged `senior_debt_keur` is reproducible.

4. **Tax loss carryforward period**: The spec says 5 years. After 5 years, unused losses expire. Confirm this convention.

5. **SHL mechanics**: Shareholder loan at 8% — is this interest paid in cash (cash interest) or PIK (capitalized)? Finco defaults to PIK. Confirm.

6. **DSRA mechanics**: 6 months of debt service held in reserve. Is DSRA funded at financial close from equity, or built up over time from operating cash flow?

7. **Distribution waterfall**: After debt service + tax + reserve funding, all remaining cash flows to equity. Is this a 100% cash sweep, or is there a distribution cap (e.g. 80% sweep + 20% retained)?

8. **Terminal value**: Is there a terminal value at end of horizon (e.g. salvage value of equipment), or is the horizon truly 25 years with no terminal cash flow?

9. **Working capital**: Is there a working capital line (receivables, payables), or is the model on a cash basis with no working capital adjustments?

10. **Construction draw schedule**: 12-month construction for Solar means 2 semiannual periods (Y0-H2 + Y1-H1). The 18-month Wind construction means 3 semiannual periods. Confirm semiannual periods are correct.

11. **COD timing**: Solar COD = 2031-01-01 (after 12 months construction starting 2030-01-01). Wind COD = 2031-07-01 (after 18 months). Confirm.

12. **Generation profile**: Is generation flat within each year (50% in H1, 50% in H2), or does the modeler want a more realistic monthly profile aggregated to semiannual?

---

## 10. Next Phase

Once the modeler delivers both reference workbooks (Solar + Wind), the Finco team will execute **G1A-EXTRACTOR**:

1. Author `scripts/extract_generic_golden.py` (an openpyxl-based extractor)
2. Run extractor against both workbooks to produce:
   - `tests/fixtures/excel_golden_generic_solar.json` (16 anchors + tolerances)
   - `tests/fixtures/excel_golden_generic_wind.json` (16 anchors + tolerances)
   - `tests/fixtures/excel_reference/generic_solar_manifest.json` (provenance, SHA256)
   - `tests/fixtures/excel_reference/generic_wind_manifest.json`
3. Hand off to G1B (parity tests)

The extractor script will:
- Read the workbook via openpyxl
- For each anchor cell, extract the formula text and the cached value
- Compare cached value against runtime output
- Produce the golden fixture JSON in the same format as `tests/fixtures/excel_golden_tuho.json`
- Compute SHA256 of the workbook for the manifest

**Estimated effort**: 24h external modeler (this spec) + 40h engineer (extractor + manifest) = 64h.

**Stop gate**: Both workbooks received, both pass formula-visibility + no-VBA + no-external-link checks, both have signed metadata files. Then G1A-EXTRACTOR begins.

---

## Appendix A — Sample Output Cell Layout (Summary Tab)

```
Row 1:  GENERIC SOLAR — BANK CASE
Row 2:  Source: Finco1 Generic Solar factory + External Reference Excel
Row 3:
Row 4:  KPI                          Unit        Value
Row 5:  Total Revenue                kEUR        =SUM(Revenue!H:H)
Row 6:  Total OPEX                   kEUR        =SUM(OpEx!H:H)
Row 7:  Total EBITDA                 kEUR        =SUM(P&L!H:H)
Row 8:  Total CAPEX                  kEUR        =CapEx!C141
Row 9:  IDC                          kEUR        =IDC!D45
Row 10: Bank fees                    kEUR        =IDC!D46
Row 11: Senior Debt                  kEUR        =Debt Service!D5
Row 12: Senior Debt Service P1       kEUR        =Debt Service!H12
Row 13: Senior Debt Service P2       kEUR        =Debt Service!I12
Row 14: Senior Debt Service P3       kEUR        =Debt Service!J12
Row 15: Avg DSCR                     x           =AVERAGE(Debt Service!DSCR_col)
Row 16: Min DSCR                     x           =MIN(Debt Service!DSCR_col)
Row 17: Project IRR                  %           =XIRR(Cash Flow!H:H, Cash Flow!dates)
Row 18: Equity IRR                   %           =XIRR(Equity!H:H, Equity!dates)
Row 19: Realized Gearing             %           =(C11/C8)*100
```

The modeler may use any cell layout as long as the 15 named cells exist and contain the specified formulas.

---

## Appendix B — Cell Reference Convention

When extracting values, the Finco extractor will use cell references like `Summary!C5` (sheet + cell). The modeler should:

- Use sheet names exactly as specified in §2
- Place each of the 15 outputs on a known cell on the Summary tab
- Document any deviations in the metadata

If the modeler needs to reorganize the Summary tab, the cell refs in §4 may change; this is acceptable as long as the new layout is documented in the workbook metadata.

---

## Appendix C — Tolerance Calculation Examples

| Anchor | Excel Value | Tolerance | Finco Pass Range |
|---|---|---|---|
| Total revenue 100,000 kEUR | 100,000 | ±0.5% | [99,500, 100,500] |
| Senior debt 22,500 kEUR | 22,500 | ±0.5% | [22,388, 22,613] |
| IDC 1,200 kEUR | 1,200 | ±1.0% | [1,188, 1,212] |
| Project IRR 9.21% | 0.0921 | ±5bps | [0.0916, 0.0926] |
| Avg DSCR 1.66 | 1.66 | ±0.01 | [1.65, 1.67] |
| Realized gearing 75% | 75.0 | ±0.5pp | [74.5, 75.5] |

---

**End of specification.**