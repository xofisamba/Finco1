# Canonical Formula Registry

> **Stack W** — Documentation-only. No engine code changes.
>
> This registry documents every major computation in the financial waterfall engine.
> All formulas are verified against source code. Line numbers are approximate (file state at commit `c02e1ee`).

---

## Table of Contents

| ID | Name | Section |
|----|------|---------|
| [F001](#f001--revenue-per-period) | Revenue per period | Revenue / EBITDA |
| [F002](#f002--ebitda-per-period) | EBITDA per period | Revenue / EBITDA |
| [F003](#f003--sculpted-debt-sizing-closed-form) | Sculpted debt sizing (closed-form) | Senior Debt |
| [F004](#f004--senior-interest-per-period) | Senior interest per period | Senior Debt |
| [F005](#f005--senior-principal-per-period) | Senior principal per period | Senior Debt |
| [F006](#f006--dscr) | DSCR | Senior Debt |
| [F007](#f007--cfads-proxy-for-sculpting) | CFADS proxy for sculpting | Senior Debt |
| [F008](#f008--gearing-cap) | Gearing cap | Senior Debt |
| [F009](#f009--cash-sweep) | Cash sweep | Senior Debt |
| [F010](#f010--taxable-income-before-losses) | Taxable income before losses | Tax |
| [F011](#f011--atad-interest-limitation) | ATAD interest limitation | Tax |
| [F012](#f012--loss-carryforward-usage) | Loss carryforward usage | Tax |
| [F013](#f013--taxable-income-after-losses) | Taxable income after losses | Tax |
| [F014](#f014--cit-accrual) | CIT accrual | Tax |
| [F015](#f015--h1-cit-cash-settlement-stack-t2) | H1 CIT cash settlement | Tax |
| [F016](#f016--two-pass-shl-deduction-stack-t1) | Two-pass SHL deduction | Tax |
| [F020](#f020--shl-gross-interest) | SHL gross interest | SHL |
| [F021](#f021--shl-net-interest-after-wht) | SHL net interest (after WHT) | SHL |
| [F022](#f022--shl-cash-interest-paid) | SHL cash interest paid | SHL |
| [F023](#f023--shl-principal-sweep) | SHL principal sweep | SHL |
| [F024](#f024--shl-pik-addition) | SHL PIK addition | SHL |
| [F025](#f025--shl-closing-balance) | SHL closing balance | SHL |
| [F030](#f030--dsra-rolling-target) | DSRA rolling target | DSRA |
| [F031](#f031--dsra-contribution-per-period) | DSRA contribution per period | DSRA |
| [F032](#f032--dsra-initial-balance-at-financial-close) | DSRA initial balance at FC | DSRA |
| [F040](#f040--cf-after-tax) | CF after tax | Distributions / IRR |
| [F041](#f041--cf-after-debt-service) | CF after debt service | Distributions / IRR |
| [F042](#f042--cf-after-reserves) | CF after reserves | Distributions / IRR |
| [F043](#f043--equity-irr-shl_plus_dividends-method) | Equity IRR (shl_plus_dividends) | Distributions / IRR |
| [F044](#f044--project-irr-unlevered) | Project IRR (unlevered) | Distributions / IRR |
| [F050](#f050--fiscal-reintegration) | Fiscal reintegration | Fiscal Reintegration |
| [F051](#f051--prior-tax-loss-initialisation) | Prior tax loss initialisation | Fiscal Reintegration |

---

## Revenue / EBITDA

### F001 — Revenue per period

| Field | Value |
|-------|-------|
| **ID** | F001 |
| **Module** | `domain/waterfall/waterfall_engine.py` |
| **Function** | `run_waterfall()` / `cached_run_waterfall()` |
| **Line (approx)** | ~680, ~1453 |
| **Inputs** | `generation_mwh` (MWh), `price` (€/MWh) — resolved upstream via `full_revenue_schedule()` |
| **Outputs** | `revenue_keur` |
| **Dependencies** | External: `domain.revenue.generation.full_revenue_schedule()` |
| **Excel Equivalent** | `= generation_mwh × price_eur_per_mwh / 1000` |
| **Validation Status** | ✅ Validated — revenue schedule passed in as pre-built `list[float]` |

**Notes:** Revenue is computed outside the waterfall loop by `full_revenue_schedule()` and passed in as `revenue_schedule`. Inside the loop the value is read at `rev = revenue_schedule[i]` (line ~680). The `cached_run_waterfall` wrapper shows the construction explicitly (line ~1453).

---

### F002 — EBITDA per period

| Field | Value |
|-------|-------|
| **ID** | F002 |
| **Module** | `domain/waterfall/waterfall_engine.py` |
| **Function** | `compute_ebitda_schedule()` |
| **Line (approx)** | ~194 |
| **Inputs** | `revenue_keur`, `opex_keur` |
| **Outputs** | `ebitda_keur` |
| **Dependencies** | F001 |
| **Excel Equivalent** | `= MAX(0, Revenue - OPEX)` |
| **Validation Status** | ✅ Validated — floored at 0 to prevent negative EBITDA distorting sculpting |

**Notes:** `ebitda = max(0, rev - opex)` (line ~194). The `max(0, …)` floor is intentional: EBITDA should not go negative from OPEX alone because the model does not currently model distress or negative trading. OPEX in the semi-annual model is half the annual value.

---

## Senior Debt

### F003 — Sculpted debt sizing (closed-form)

| Field | Value |
|-------|-------|
| **ID** | F003 |
| **Module** | `domain/financing/sculpting_iterative.py` |
| **Function** | `closed_form_sculpt()` |
| **Line (approx)** | ~403–506 |
| **Inputs** | `cfads_schedule` (= EBITDA × (1 − tax_rate)), `rate_schedule`, `tenor_periods`, `target_dscr`, `dscr_schedule` (optional per-period) |
| **Outputs** | `debt_keur`, `balance_schedule`, `interest_schedule`, `principal_schedule`, `payment_schedule` |
| **Dependencies** | F007 (CFADS proxy), F008 (gearing cap) |
| **Excel Equivalent** | Backward/forward pass PV annuity: `debt_bal[t] = (debt_bal[t+1] + allowable_ds[t]) / (1 + r[t])` |
| **Validation Status** | ✅ Validated — Stack K golden calibration, Stack Q DSCR reconciliation |

**Notes — algorithm:**
1. **Backward pass** (line ~451–456): `debt_bal[t] = (debt_bal[t+1] + CFADS[t]/DSCR_target[t]) / (1 + r[t])`, with `debt_bal[N] = 0`.
2. **Forward pass** (line ~467–491): `interest[t] = balance[t] × r[t]`; `principal[t] = allowable_ds[t] − interest[t]`.
3. Initial debt = `min(debt_bal[0], gearing_cap)`. If gearing is binding, all balances and DS are scaled proportionally.

---

### F004 — Senior interest per period

| Field | Value |
|-------|-------|
| **ID** | F004 |
| **Module** | `domain/financing/sculpting_iterative.py` |
| **Function** | `closed_form_sculpt()` forward pass |
| **Line (approx)** | ~477 |
| **Inputs** | `senior_balance_opening_keur`, `rate_per_period` |
| **Outputs** | `senior_interest_keur` (`si`) |
| **Dependencies** | F003 |
| **Excel Equivalent** | `= opening_balance × rate_per_period` |
| **Validation Status** | ✅ Validated — Stack S debt service export reconciliation |

**Notes:** `interest = balance * rates[t]` (line ~477). `rate_per_period` is the semi-annual rate (e.g., `0.02825` for 5.65% annual). The rate may vary per period when a Euribor curve `rate_schedule` is provided.

---

### F005 — Senior principal per period

| Field | Value |
|-------|-------|
| **ID** | F005 |
| **Module** | `domain/financing/sculpting_iterative.py` / `domain/waterfall/waterfall_engine.py` |
| **Function** | `closed_form_sculpt()` / `run_waterfall()` |
| **Line (approx)** | ~478, ~701 |
| **Inputs** | `allowable_ds_keur`, `senior_interest_keur`, `opening_balance_keur` |
| **Outputs** | `senior_principal_keur` (`sp`) |
| **Dependencies** | F003, F004 |
| **Excel Equivalent** | `= MAX(0, MIN(allowable_ds − interest, balance))` |
| **Validation Status** | ✅ Validated — Stack S |

**Notes:** `principal = allowable_ds[t] - interest` clipped to `[0, balance]` (line ~481). In the waterfall loop, the last tenor period is a balloon: `sp = opening_balance` (line ~696, full payoff). For `fixed_ds_keur` amortisation: `sp = max(0, fixed_ds - si)` capped at balance.

---

### F006 — DSCR

| Field | Value |
|-------|-------|
| **ID** | F006 |
| **Module** | `domain/waterfall/waterfall_engine.py` |
| **Function** | `run_waterfall()` |
| **Line (approx)** | ~992 |
| **Inputs** | `ebitda_keur`, `tax_this_period_keur`, `senior_ds_keur` |
| **Outputs** | `dscr` |
| **Dependencies** | F002, F014, F015 |
| **Excel Equivalent** | `= (EBITDA − CashTax) / SeniorDS` |
| **Validation Status** | ✅ Validated — Stack L DSCR denominator, Stack Q |

**Notes:** `dscr = (ebitda - tax_this_period) / senior_ds` (line ~992). CFADS = EBITDA − cash tax (measured *before* debt service and DSRA movements). `dscr = inf` when `senior_ds = 0` (post-tenor). Lockup triggers when `dscr < lockup_dscr` (default 1.10).

---

### F007 — CFADS proxy for sculpting

| Field | Value |
|-------|-------|
| **ID** | F007 |
| **Module** | `domain/waterfall/waterfall_engine.py` |
| **Function** | `run_waterfall()` |
| **Line (approx)** | ~389–393 |
| **Inputs** | `ebitda_keur`, `tax_rate` |
| **Outputs** | `cfads_for_sculpt` (per-period list) |
| **Dependencies** | F002 |
| **Excel Equivalent** | `= MAX(0, EBITDA × (1 − tax_rate))` |
| **Validation Status** | ✅ Validated — used internally for sculpting only, not exposed in WaterfallPeriod |

**Notes:** `cfads_for_sculpt[t] = max(0, ebitda[t] * (1 - tax_rate))` (line ~390–392). This is a pre-sculpt approximation: actual tax depends on interest deductions that are not yet known at sculpting time. The after-tax DSCR from sculpting is therefore approximate; the real DSCR in the waterfall loop uses actual computed tax (F006).

---

### F008 — Gearing cap

| Field | Value |
|-------|-------|
| **ID** | F008 |
| **Module** | `domain/waterfall/waterfall_engine.py` |
| **Function** | `run_waterfall()` |
| **Line (approx)** | ~407–425 |
| **Inputs** | `sculpt_capex_keur`, `idc_keur`, `gearing_ratio` |
| **Outputs** | `gearing_cap_keur` |
| **Dependencies** | — |
| **Excel Equivalent** | `= (sculpt_capex − IDC) × gearing_ratio` |
| **Validation Status** | ✅ Validated — Stack R factory configuration fidelity |

**Notes:**
- `sizing_base_for_gearing = sculpt_capex_keur - idc_keur` when both > 0 (line ~413).
- `gearing_cap_keur = sizing_base_for_gearing × gearing_ratio` (line ~417).
- Debt sizing method `"dscr_sculpt"` (default): `debt = min(dscr_debt, gearing_cap)`.
- Debt sizing method `"gearing_cap"`: `debt = max(dscr_debt, gearing_cap)` (gearing wins).

---

### F009 — Cash sweep

| Field | Value |
|-------|-------|
| **ID** | F009 |
| **Module** | `domain/financing/sculpting_iterative.py` |
| **Function** | `cash_sweep()` |
| **Line (approx)** | ~513–544 |
| **Inputs** | `cf_after_reserves_keur`, `senior_debt_balance_keur`, `sweep_dscr` (1.35), `actual_dscr`, `sweep_pct` (1.0) |
| **Outputs** | `(distribution_keur, sweep_amount_keur)` |
| **Dependencies** | F006, F042 |
| **Excel Equivalent** | `= IF(dscr > 1.35, MIN(cf_after_reserves, senior_balance), 0)` |
| **Validation Status** | ✅ Validated — Stack N SHL principal |

**Notes:** Activates when `actual_dscr > sweep_dscr` (1.35) and `senior_balance > 0`. `sweep = min(cf_after_reserves × sweep_pct, senior_balance)`; `distribution = max(0, cf_after_reserves − sweep)`.

---

## Tax

### F010 — Taxable income before losses

| Field | Value |
|-------|-------|
| **ID** | F010 |
| **Module** | `domain/waterfall/tax_engine.py` |
| **Function** | `compute_period_tax()` |
| **Line (approx)** | ~85–92 |
| **Inputs** | `ebitda_keur`, `co2_revenue_keur`, `depreciation_keur`, `deductible_interest_keur`, `disallowed_interest_keur`, `fiscal_reintegration_keur` |
| **Outputs** | `taxable_income_before_losses_keur` |
| **Dependencies** | F002, F011, F050 |
| **Excel Equivalent** | `= MAX(0, EBITDA + CO2Bridge − Depreciation − DeductibleInterest + DisallowedInterest + FiscalReintegration)` |
| **Validation Status** | ✅ Validated — Stack T tax engine accuracy |

**Notes:** `taxable_before_losses = ebitda + co2_revenue - depreciation - deductible_interest + disallowed_interest + fiscal_reintegration` (lines ~85–92). The result is floored at 0 before returning in `taxable_income_before_losses_keur` (line ~112). CO2 revenue (`co2_revenue_keur`) is the Phase 9 CIT bridge — adds CO2 income to taxable base without double-counting it in EBITDA.

---

### F011 — ATAD interest limitation

| Field | Value |
|-------|-------|
| **ID** | F011 |
| **Module** | `domain/waterfall/tax_engine.py` |
| **Function** | `compute_period_tax()` |
| **Line (approx)** | ~69–81 |
| **Inputs** | `total_interest_keur` (= senior + SHL), `ebitda_keur`, `atad_ebitda_limit` (0.30), `atad_min_threshold_keur` (3,000) |
| **Outputs** | `deductible_interest_keur`, `disallowed_interest_keur` |
| **Dependencies** | F004, F020 |
| **Excel Equivalent** | `deductible_limit = MAX(EBITDA × 30%, 3000)` then `deductible = MIN(total_interest, deductible_limit)` |
| **Validation Status** | ✅ Validated — Stack T |

**Notes:**
```
ebitda_limit      = ebitda × atad_ebitda_limit        # 30% of EBITDA
deductible_limit  = max(ebitda_limit, 3000)           # minimum safe harbour
deductible        = min(total_interest, deductible_limit)
disallowed        = max(0, total_interest - deductible_limit)
```
When `total_interest ≤ deductible_limit`, `disallowed = 0` and full interest is deductible.

---

### F012 — Loss carryforward usage

| Field | Value |
|-------|-------|
| **ID** | F012 |
| **Module** | `domain/waterfall/tax_engine.py` |
| **Function** | `compute_period_tax()` |
| **Line (approx)** | ~95–97 |
| **Inputs** | `taxable_before_losses_keur`, `loss_carryforward_keur`, `loss_carryforward_cap` (1.0) |
| **Outputs** | `loss_carryforward_applied_keur`, `loss_carryforward_remaining_keur` |
| **Dependencies** | F010 |
| **Excel Equivalent** | `= MIN(loss_opening, MAX(0, taxable_before_losses × cap))` |
| **Validation Status** | ✅ Validated — Stack T |

**Notes:**
```
max_offset = taxable_before_losses × loss_carryforward_cap   # cap at 100% by default
loss_used  = min(loss_carryforward, max(0, max_offset))
remaining  = max(0, loss_carryforward - loss_used)
```
`loss_carryforward_cap = 1.0` (100%) — ATAD does not cap loss usage in the Croatian model.

---

### F013 — Taxable income after losses

| Field | Value |
|-------|-------|
| **ID** | F013 |
| **Module** | `domain/waterfall/tax_engine.py` |
| **Function** | `compute_period_tax()` |
| **Line (approx)** | ~100 |
| **Inputs** | `taxable_before_losses_keur`, `loss_carryforward_applied_keur` |
| **Outputs** | `taxable_income_keur` |
| **Dependencies** | F010, F012 |
| **Excel Equivalent** | `= MAX(0, taxable_before_losses − loss_used)` |
| **Validation Status** | ✅ Validated — Stack T |

**Notes:** `taxable_income = max(0, taxable_before_losses - loss_used)` (line ~100).

---

### F014 — CIT accrual

| Field | Value |
|-------|-------|
| **ID** | F014 |
| **Module** | `domain/waterfall/tax_engine.py` |
| **Function** | `compute_period_tax()` |
| **Line (approx)** | ~103 |
| **Inputs** | `taxable_income_keur`, `tax_rate` |
| **Outputs** | `tax_keur` (CIT accrual — not yet cash) |
| **Dependencies** | F013 |
| **Excel Equivalent** | `= taxable_income × tax_rate` |
| **Validation Status** | ✅ Validated — Stack T |

**Notes:** `tax_keur = taxable_income × tax_rate` (line ~103). This is the *accrual*. Cash timing is handled by F015 — tax is only paid in H2 (second period of each fiscal year).

---

### F015 — H1 CIT cash settlement (Stack T2)

| Field | Value |
|-------|-------|
| **ID** | F015 |
| **Module** | `domain/waterfall/waterfall_engine.py` |
| **Function** | `run_waterfall()` |
| **Line (approx)** | ~908–915 |
| **Inputs** | `_h1_cit_accrual_keur` (carried from H1), `tax_keur` (H2 accrual), `is_tax_period` (True in H2) |
| **Outputs** | `tax_this_period_keur` (cash tax paid this period) |
| **Dependencies** | F014 |
| **Excel Equivalent** | H2: `= H1_accrual + H2_accrual`; H1: `= 0` |
| **Validation Status** | ✅ Validated — Stack T2 parity tests |

**Notes:** Pre-T2, only H2 tax was paid (H1 accrual evaporated). Post-T2:
```
H1: tax_this_period = 0; carry _h1_cit_accrual = H1_tax
H2: tax_this_period = _h1_cit_accrual + H2_tax; reset _h1_cit_accrual = 0
```
`r67_excel_style_cash_tax_diagnostic = -(previous_tax + current_tax)` in H2 (audit-only field matching Excel CF row 67).

---

### F016 — SHL deduction two-pass (Stack T1)

| Field | Value |
|-------|-------|
| **ID** | F016 |
| **Module** | `domain/waterfall/waterfall_engine.py` |
| **Function** | `run_waterfall()` |
| **Line (approx)** | ~761–966 |
| **Inputs** | Pass 1: `shl_interest_keur = 0`; Pass 2: `shl_interest_keur = shi` (real) |
| **Outputs** | Final `tax_keur`, `taxable_profit_keur` |
| **Dependencies** | F010–F014, F022 |
| **Excel Equivalent** | Single-pass (Excel has no circular dependency — SHL interest is a known input) |
| **Validation Status** | ✅ Validated — Stack T1 two-pass tests |

**Notes:** The circular dependency `tax → cf_after_tax → cf_for_shl → shi → tax` is resolved with two passes:
1. **Pass 1** (~line 762): `compute_period_tax(shl_interest_keur=0)` → provisional tax → `_cf_after_tax_p1` → SHL block → real `shi`.
2. **Pass 2** (~line 885): `compute_period_tax(shl_interest_keur=shi)` → final tax → update `prior_tax_loss`.
3. **SHL re-pass** (~line 936): recompute `shp`/`shl_balance` using `cf_after_tax` from Pass 2 (not Pass 1). A guard raises `RuntimeError` if `shi` changes between passes (would require three-pass iteration).

---

## SHL (Shareholder Loan)

### F020 — SHL gross interest

| Field | Value |
|-------|-------|
| **ID** | F020 |
| **Module** | `domain/waterfall/shl_engine.py` |
| **Function** | `compute_shl_period_v3()` |
| **Line (approx)** | ~115 |
| **Inputs** | `shl_balance_keur`, `shl_rate_per_period` |
| **Outputs** | `gross_interest_keur` |
| **Dependencies** | F025 (prior balance) |
| **Excel Equivalent** | `= shl_balance × rate_per_period` |
| **Validation Status** | ✅ Validated — Stack M equity IRR SHL |

**Notes:** `gross_interest = shl_balance × shl_rate_per_period` (line ~115). `shl_rate_per_period` = annual rate × `day_fraction` (0.5 for semi-annual). Gross interest accrues on the *opening* balance. WHT is applied to cash interest only — not to PIK (F024).

---

### F021 — SHL net interest (after WHT)

| Field | Value |
|-------|-------|
| **ID** | F021 |
| **Module** | `domain/waterfall/shl_engine.py` |
| **Function** | `compute_shl_period_v3()` |
| **Line (approx)** | ~117 |
| **Inputs** | `gross_interest_keur`, `wht_rate` |
| **Outputs** | `net_interest_keur` |
| **Dependencies** | F020 |
| **Excel Equivalent** | `= gross_interest × (1 − wht_rate)` |
| **Validation Status** | ✅ Validated — Stack M |

**Notes:** `net_interest = gross_interest × (1 - wht_rate)` (line ~117). `net_interest` is what the investor *receives* in cash. WHT paid to the tax authority = `interest_paid × wht_rate / (1 − wht_rate)` (gross-up formula, line ~126).

---

### F022 — SHL cash interest paid

| Field | Value |
|-------|-------|
| **ID** | F022 |
| **Module** | `domain/waterfall/shl_engine.py` |
| **Function** | `compute_shl_period_v3()` — varies by method |
| **Line (approx)** | ~122, ~146, ~189, ~203 |
| **Inputs** | `net_interest_keur`, `cf_available_keur`, method |
| **Outputs** | `interest_paid_keur` (`shi`) |
| **Dependencies** | F021, F040 |
| **Excel Equivalent** | `= MIN(net_interest, MAX(0, cf_available))` |
| **Validation Status** | ✅ Validated — Stack M, Stack N |

**Notes — by method:**
- `bullet`: `interest_paid = min(max(0, cf_available), net_interest)` — pay if CF allows.
- `cash_sweep`: `interest_paid = min(net_interest, available_cash)`.
- `pik_then_sweep` (PIK phase): `interest_paid = min(max(0, cf_available), net_interest)`.
- `pik_then_sweep` (SWEEP phase): `interest_paid = min(net_interest, cf_available)`.
- `partial_pay_sweep`: `interest_paid = min(available, net_interest)`.
- `pik`: `interest_paid = 0` (all interest capitalised).
- `accrued`: `interest_paid = 0` (deferred, no PIK).

---

### F023 — SHL principal (sweep)

| Field | Value |
|-------|-------|
| **ID** | F023 |
| **Module** | `domain/waterfall/shl_engine.py` |
| **Function** | `compute_shl_period_v3()` |
| **Line (approx)** | ~147–148, ~205–206, ~228 |
| **Inputs** | `cf_available_keur`, `interest_paid_keur`, `shl_balance_keur` |
| **Outputs** | `principal_keur` (`shp`) |
| **Dependencies** | F022 |
| **Excel Equivalent** | `= MIN(MAX(0, cf_available − interest_paid), shl_balance)` |
| **Validation Status** | ✅ Validated — Stack N SHL principal |

**Notes — by method:**
- `cash_sweep` / `pik_then_sweep` SWEEP: `remaining = max(0, cf_available - interest_paid)`; `principal = min(remaining, shl_balance)`.
- `partial_pay_sweep`: `principal = min(remaining_after_interest, shl_balance + pik)` — net of PIK capitalisation.
- `bullet`: `principal = shl_balance` on `is_final_period` only, else `0`.
- `pik` / `accrued`: `principal = 0`.

---

### F024 — SHL PIK addition

| Field | Value |
|-------|-------|
| **ID** | F024 |
| **Module** | `domain/waterfall/shl_engine.py` |
| **Function** | `compute_shl_period_v3()` |
| **Line (approx)** | ~124, ~150, ~165, ~191, ~204, ~225 |
| **Inputs** | `gross_interest_keur`, `interest_paid_keur` |
| **Outputs** | `pik_addition_keur` |
| **Dependencies** | F020, F022 |
| **Excel Equivalent** | `= gross_interest − interest_paid_cash` |
| **Validation Status** | ✅ Validated — v3 Blueprint S1-2 fix |

**Notes:** `pik = gross_interest - interest_paid` (not `net_interest - interest_paid`). This is the key v3 fix: WHT is on *cash* interest only, not on capitalised interest. Using gross ensures the SHL balance grows correctly when WHT rate > 0.

---

### F025 — SHL closing balance

| Field | Value |
|-------|-------|
| **ID** | F025 |
| **Module** | `domain/waterfall/shl_engine.py` |
| **Function** | `compute_shl_period_v3()` |
| **Line (approx)** | ~133, ~153, ~173, ~208, ~229 |
| **Inputs** | `shl_balance_opening_keur`, `principal_keur`, `pik_addition_keur` |
| **Outputs** | `new_balance_keur` |
| **Dependencies** | F023, F024 |
| **Excel Equivalent** | `= MAX(0, opening − principal + PIK)` |
| **Validation Status** | ✅ Validated — Stack N |

**Notes:** `new_balance = max(0, shl_balance - principal + pik)` for sweep methods. For `pik`: `new_balance = shl_balance + pik`. Opening balance at FC = `shl_amount + shl_idc_keur` (line ~578 in waterfall engine).

---

## DSRA

### F030 — DSRA rolling target

| Field | Value |
|-------|-------|
| **ID** | F030 |
| **Module** | `domain/financing/sculpting_iterative.py` |
| **Function** | `dsra_rolling_target()` |
| **Line (approx)** | ~551–570 |
| **Inputs** | `future_payments` (from current period), `dsra_months` (6), `periods_per_year` (2) |
| **Outputs** | `dsra_target_keur` |
| **Dependencies** | F003 |
| **Excel Equivalent** | `= SUM(next_N_periods_of_DS)` where N = dsra_months × periods_per_year / 12 |
| **Validation Status** | ✅ Validated |

**Notes:** `periods_needed = max(1, dsra_months × periods_per_year // 12)` = 1 for 6-month, semi-annual. `dsra_target = sum(future_payments[:periods_needed])` — i.e., one forward period of debt service. Target decreases as debt declines.

---

### F031 — DSRA contribution per period

| Field | Value |
|-------|-------|
| **ID** | F031 |
| **Module** | `domain/financing/sculpting_iterative.py` |
| **Function** | `dsra_update()` |
| **Line (approx)** | ~573–601 |
| **Inputs** | `prior_balance_keur`, `target_keur`, `available_cash_keur`, `withdrawal_needed_keur` |
| **Outputs** | `(new_balance_keur, contribution_keur, withdrawal_keur)` |
| **Dependencies** | F030 |
| **Excel Equivalent** | `= MAX(0, MIN(target − balance_after_withdrawal, available_cash))` |
| **Validation Status** | ✅ Validated |

**Notes:**
```
withdrawal          = min(withdrawal_needed, prior_balance)
balance_post_draw   = prior_balance − withdrawal
gap                 = max(0, target − balance_post_draw)
contribution        = min(gap, available_cash)
new_balance         = balance_post_draw + contribution
```
`cf_after_reserves = cf_after_ds + dsra_withdrawal − dsra_contribution` (line ~987 waterfall engine).

---

### F032 — DSRA initial balance at Financial Close

| Field | Value |
|-------|-------|
| **ID** | F032 |
| **Module** | `domain/waterfall/waterfall_engine.py` |
| **Function** | `run_waterfall()` |
| **Line (approx)** | ~577 |
| **Inputs** | `dsra_months` (6), `sculpt_result.payment_schedule[0]`, `periods_per_year` (2) |
| **Outputs** | `dsra_balance` (initial, funded from equity at FC) |
| **Dependencies** | F003 |
| **Excel Equivalent** | `= (dsra_months / 12) × (first_period_DS × 2)` |
| **Validation Status** | ✅ Validated — Blueprint S1-5 v3 fix |

**Notes:** `dsra_balance = (dsra_months / 12) × (payment_schedule[0] × 2)` (line ~577). For 6-month DSRA with semi-annual model, this simplifies to `payment_schedule[0]` (one period). Funded from equity at FC — not from operating cash flows.

---

## Distributions / IRR

### F040 — CF after tax

| Field | Value |
|-------|-------|
| **ID** | F040 |
| **Module** | `domain/waterfall/waterfall_engine.py` |
| **Function** | `run_waterfall()` |
| **Line (approx)** | ~922 |
| **Inputs** | `ebitda_keur`, `tax_this_period_keur` |
| **Outputs** | `cf_after_tax_keur` |
| **Dependencies** | F002, F015 |
| **Excel Equivalent** | `= EBITDA − CashTaxThisPeriod` |
| **Validation Status** | ✅ Validated |

**Notes:** `cf_after_tax = ebitda - tax_this_period` (line ~922). Uses *cash* tax (`tax_this_period`) not accrual (`tax`). In H1: `tax_this_period = 0` so `cf_after_tax = ebitda`. No depreciation deducted here — depreciation is a non-cash item that reduces taxable income but not cash flow.

---

### F041 — CF after debt service

| Field | Value |
|-------|-------|
| **ID** | F041 |
| **Module** | `domain/waterfall/waterfall_engine.py` |
| **Function** | `run_waterfall()` |
| **Line (approx)** | ~969 |
| **Inputs** | `cf_after_tax_keur`, `senior_ds_keur`, `shl_interest_paid_keur` (`shi`) |
| **Outputs** | `cf_after_ds_keur` |
| **Dependencies** | F040, F004, F005, F022 |
| **Excel Equivalent** | `= CF_after_tax − SeniorDS − SHL_interest` |
| **Validation Status** | ✅ Validated |

**Notes:** `cf_after_ds = cf_after_tax - senior_ds - shi` (line ~969). SHL *principal* repayment (`shp`) is a balance-sheet movement — it reduces SHL balance but does not flow through the CF waterfall here (principal reduces `shl_balance`, not `cf_after_ds`).

---

### F042 — CF after reserves

| Field | Value |
|-------|-------|
| **ID** | F042 |
| **Module** | `domain/waterfall/waterfall_engine.py` |
| **Function** | `run_waterfall()` |
| **Line (approx)** | ~987 |
| **Inputs** | `cf_after_ds_keur`, `dsra_withdrawal_keur`, `dsra_contribution_keur` |
| **Outputs** | `cf_after_reserves_keur` |
| **Dependencies** | F041, F031 |
| **Excel Equivalent** | `= CF_after_DS + DSRA_withdrawal − DSRA_contribution` |
| **Validation Status** | ✅ Validated |

**Notes:** `cf_after_reserves = cf_after_ds + dsra_withdrawal - dsra_contrib` (line ~987). DSRA withdrawal is positive (cash in); contribution is negative (cash out). This is the distributable cash before lockup and distribution logic.

---

### F043 — Equity IRR (shl_plus_dividends method)

| Field | Value |
|-------|-------|
| **ID** | F043 |
| **Module** | `domain/waterfall/waterfall_engine.py` |
| **Function** | `run_waterfall()` |
| **Line (approx)** | ~609–611, ~1249–1267 |
| **Inputs** | `shl_amount_keur`, `share_capital_keur`, `shl_interest_paid_per_period` (`shi`), `distributions_per_period` (`dist`) |
| **Outputs** | `equity_irr` |
| **Dependencies** | F022, F042 |
| **Excel Equivalent** | `= XIRR({−(SHL + share_capital), shi_1, …, dist_n}, {FC_date, …, end_date})` |
| **Validation Status** | ✅ Validated — Stack M equity IRR SHL |

**Notes:** For `equity_irr_method = "shl_plus_dividends"`:
- Initial outflow: `equity_investment = shl_amount + share_capital_keur`.
- Per period (SHL outstanding): `equity_cf = shi` (net interest only — no principal).
- Per period (SHL repaid): `equity_cf = dist` (dividends).
- Special case for disbursement period (Y1-H1): `equity_cf = max(0, _cf_for_shl)` to match Excel golden methodology.
- IRR computed via `xirr()` (XIRR algorithm) with `guess=0.10`.

---

### F044 — Project IRR (unlevered)

| Field | Value |
|-------|-------|
| **ID** | F044 |
| **Module** | `domain/waterfall/waterfall_engine.py` |
| **Function** | `run_waterfall()` |
| **Line (approx)** | ~1243–1245 |
| **Inputs** | `ebitda_keur`, `depreciation_keur`, `tax_rate` |
| **Outputs** | `project_irr` |
| **Dependencies** | F002 |
| **Excel Equivalent** | `= XIRR({−total_capex, (EBITDA − unlev_tax)_1, …}, dates)` |
| **Validation Status** | ✅ Validated |

**Notes:** Unlevered tax = `tax_rate × max(0, ebitda - dep)` — financing-independent, so project IRR is not distorted by interest deductions. `project_cfs[0] = -total_capex`; subsequent: `ebitda - unlev_tax`.

---

## Fiscal Reintegration

### F050 — Fiscal reintegration

| Field | Value |
|-------|-------|
| **ID** | F050 |
| **Module** | `domain/waterfall/waterfall_engine.py` |
| **Function** | `run_waterfall()` |
| **Line (approx)** | ~736–741 |
| **Inputs** | `idc_keur`, `bank_fees_keur`, `commitment_fees_keur` |
| **Outputs** | `fiscal_reintegration_keur` (non-zero only in first operation period) |
| **Dependencies** | — |
| **Excel Equivalent** | `= IDC + bank_fees + commitment_fees` (applied once in Y1) |
| **Validation Status** | ✅ Validated — Stack T |

**Notes:** Construction-period financial costs capitalised as IDC are *reintegrated* (added back) to taxable income in the first year of operation under Croatian tax law. Applied once:
```python
if not fiscal_reintegration_applied:       # first op period
    fiscal_reintegration = idc + bank_fees + commitment_fees
    fiscal_reintegration_applied = True
else:
    fiscal_reintegration = 0.0
```
This increases taxable income in Y1 but is then offset by the prior tax loss (F051).

---

### F051 — Prior tax loss initialisation

| Field | Value |
|-------|-------|
| **ID** | F051 |
| **Module** | `domain/waterfall/waterfall_engine.py` |
| **Function** | `run_waterfall()` |
| **Line (approx)** | ~583–588 |
| **Inputs** | `prior_tax_loss_keur` (explicit input) or `idc_keur + bank_fees_keur + commitment_fees_keur` (fallback) |
| **Outputs** | `prior_tax_loss` (loss carryforward opening balance) |
| **Dependencies** | F050 |
| **Excel Equivalent** | `= prior_tax_loss_keur` (from inputs sheet) |
| **Validation Status** | ✅ Validated |

**Notes:**
```python
if prior_tax_loss_keur > 0:
    prior_tax_loss = prior_tax_loss_keur          # explicit from inputs
else:
    prior_tax_loss = idc + bank_fees + commitment_fees  # conservative fallback
```
The opening loss carryforward offsets the fiscal reintegration add-back in Y1, preventing a spike in Year 1 tax. After each period, `prior_tax_loss` is updated from `tax_result.loss_carryforward_remaining_keur` (F012).

---

## Appendix A — Waterfall Cascade Order

The per-period computation order in `run_waterfall()` is:

```
1. Revenue / EBITDA                                (F001, F002)
2. Senior debt service lookup (from balance schedule)  (F004, F005)
3. Fiscal reintegration flag                       (F050)
4. Pass 1 tax (shl_interest = 0)                  (F010–F014)
5. CF available for SHL — provisional              (F040 provisional)
6. PIK switch trigger                              —
7. SHL computation                                 (F020–F025)
8. Pass 2 tax (real shl_interest)                  (F010–F014)
9. H1/H2 cash settlement                          (F015)
10. CF after tax — final                           (F040)
11. SHL re-pass (update shp/balance)               (F016)
12. CF after debt service                          (F041)
13. DSRA rolling target + update                   (F030, F031)
14. CF after reserves                              (F042)
15. DSCR                                           (F006)
16. Lockup check                                   —
17. Distribution / cash sweep                      (F009, F042)
18. Running senior balance update                  —
19. LLCR / PLCR                                    —
20. WaterfallPeriod record                         —
```

---

## Appendix B — SHL Repayment Methods

| Method | Interest | Principal | PIK | Trigger |
|--------|----------|-----------|-----|---------|
| `bullet` | Cash if CF allows, else PIK | At maturity only | Gross shortfall | `is_final_period` |
| `cash_sweep` | Cash first | Sweep residual | Gross shortfall | Every period |
| `pik` | 0 (all PIK) | 0 | Full gross interest | Always |
| `accrued` | 0 | 0 | 0 (deferred) | Never |
| `pik_then_sweep` | Partial cash in PIK phase; full net in SWEEP | 0 in PIK; sweep in SWEEP | Gross shortfall | `pik_switch_triggered` = CF > annual SHL interest |
| `partial_pay_sweep` | Partial cash every period | Sweep residual | Gross shortfall | Every period (no threshold) |
| `fcf_waterfall` | From FCF waterfall schedule | From FCF waterfall schedule | Computed externally | External schedule |

---

## Appendix C — Key Constants & Defaults

| Parameter | Default | Source |
|-----------|---------|--------|
| `target_dscr` | 1.15 | `run_waterfall()` signature |
| `lockup_dscr` | 1.10 | `run_waterfall()` signature |
| `sweep_dscr_threshold` | 1.35 | `run_waterfall()` line ~1007 |
| `tax_rate` | 0.10 | `run_waterfall()` signature |
| `dsra_months` | 6 | `run_waterfall()` signature |
| `atad_ebitda_limit` | 0.30 | `compute_period_tax()` signature |
| `atad_min_threshold_keur` | 3,000 | `compute_period_tax()` signature |
| `loss_carryforward_cap` | 1.0 | `run_waterfall()` line ~591 |
| `day_fraction` | 0.5 | Period attribute (semi-annual) |
| `discount_rate_project` | 6.41% | `run_waterfall()` signature |
| `discount_rate_equity` | 9.65% | `run_waterfall()` signature |
| `gearing_ratio` | 0.80 | `run_waterfall()` signature |

---

*Registry created: Stack W. Source commit: `c02e1ee`. Formulas verified against source files as of that commit.*
