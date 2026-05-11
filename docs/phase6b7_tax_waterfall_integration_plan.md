# Phase 6B.7 — SPV Tax Engine → Waterfall Integration Architecture Plan

**Purpose:** Formal architecture/integration plan for wiring the Phase 6B.4 SPV tax engine (`SPVTaxResult`) into the waterfall and portfolio layers.
**Phase:** 6B.7 — architecture / documentation / planning only.
**Scope:** SPV tax wiring only. No HoldCo, no SHL tax, no WHT, no deferred tax, no sponsor waterfall.
**Status:** AUDIT-ONLY — SPV tax engine results are not yet wired into waterfall outputs or IRR metrics.

---

## 1. Current State

### 1.1 What Exists Today

| Component | Location | Status |
|---|---|---|
| Waterfall engine | `domain/waterfall/waterfall_engine.py` | Active, production |
| Waterfall tax calculation | `domain/waterfall/tax_engine.py` (`compute_period_tax`) | Active, simplified |
| SPV tax engine | `domain/tax/engine_runner.py` (`run_spv_tax_engine`) | Phase 6B.4, standalone, NOT wired |
| SPV tax inputs | `domain/tax/engine_inputs.py` (`SPVTaxEngineInputs`) | Phase 6B.4 |
| SPV tax results | `domain/tax/engine_result.py` (`SPVTaxResult`, `SPVTaxPeriodResult`) | Phase 6B.4 |
| Tax templates | `domain/tax/templates/` | Phase 6A, declarative schema |
| Tax depreciation schedules | `domain/tax/templates/schedules.py` | Phase 6B.2, standalone |
| Tax loss carryforward schedules | `domain/tax/templates/schedules.py` | Phase 6B.3, standalone |
| Tax audit export | `app/tax_excel_export.py` | Phase 6B.5, audit-only sheets |
| Tax UI | `app/tax_ui.py` | Phase 6B.5 |

### 1.2 Templates

- `HR_SIMPLE_2026` — Croatia flat 10% CIT, straight-line depreciation
- `ME_INFRA_2026` — Montenegro progressive 9%/15% CIT, capped 2.5%/yr infrastructure depreciation

Both are **illustrative only** — not for actual tax compliance.

### 1.3 Calculations

**Current waterfall tax** (`domain/waterfall/tax_engine.py`):
```
taxable_income = EBITDA - depreciation - senior_interest - SHL_interest + ATAD_addback + fiscal_reintegration - loss_carryforward
tax = taxable_income * tax_rate
```

**SPV tax engine** (`run_spv_tax_engine`):
```
taxable_income_before_losses = EBITDA - deductible_interest - tax_depreciation + non_deductible_addbacks
taxable_income_after_losses  = taxable_income_before_losses - loss_carryforward_applied
CIT = calculate_progressive_cit(taxable_income_after_losses, cit_tiers)
```

**Key difference:** SPV engine uses tax depreciation separately from book depreciation, creates timing differences, and supports progressive CIT tiers.

### 1.4 Schedules

- `TaxDepreciationSchedule` — tracks book dep vs tax dep per period, accumulates timing differences
- `TaxLossCarryforwardSchedule` — tracks loss generation, utilisation, and remaining pool
- Both are pure, immutable, standalone — not connected to waterfall

### 1.5 SPV Tax Engine

`run_spv_tax_engine(SPVTaxEngineInputs) → SPVTaxResult`

- Accepts: EBITDA, deductible interest, book depreciation, asset cost, resolved tax config
- Produces: per-period `SPVTaxPeriodResult` with full audit trail
- **NOT wired to waterfall** — results are computed but discarded in the current model run

### 1.6 Tax Audit Exports

`app/tax_excel_export.py` writes audit-only sheets (`Tax Summary`, `Tax_{entity}`) to the Excel workbook. These are for review only — they do not affect model outputs.

### 1.7 Explicit Non-Scope

The following are **NOT in scope** for Phase 6B.7 and remain future work:

- [ ] Waterfall wiring of `SPVTaxResult`
- [ ] ATAD interest limitation in SPV engine (noted as deferred)
- [ ] Deferred tax (DTA/DTL)
- [ ] Withholding tax (WHT) on SHL interest
- [ ] HoldCo tax engine
- [ ] Sponsor IRR / sponsor waterfall
- [ ] SHL tax deductibility
- [ ] Thin-cap / EBITDA limitations
- [ ] Multi-jurisdiction SPV consolidation

---

## 2. Current Waterfall Tax State

### 2.1 What the Waterfall Does Today

The waterfall (`run_waterfall`) performs a **simplified single-entity tax calculation**:

1. Computes `taxable_profit_keur` using `compute_period_tax` from `domain/waterfall/tax_engine.py`
2. Applies a **single flat tax rate** (`tax_rate` parameter, default 10%)
3. Applies **ATAD EBITDA limitation** and **fiscal reintegration** via `compute_period_tax`
4. Applies **loss carryforward** from construction-period costs (IDC, bank fees, commitment fees)
5. Tax is paid **semi-annually** (second period of each fiscal year)
6. Tax reduces `cf_after_tax_keur` before senior debt service

### 2.2 Where Existing Tax Assumptions Live

| Assumption | Location |
|---|---|
| Flat tax rate | `run_waterfall(tax_rate=0.10)` |
| ATAD settings | `compute_period_tax(atad_ebitda_limit=0.30, atad_min_threshold_keur=3000.0)` |
| Loss carryforward initialisation | `prior_tax_loss_keur = idc_keur + bank_fees_keur + commitment_fees_keur` |
| Tax payment timing | `is_tax_period = period.period_in_year == 2` |
| No progressive CIT | Uses single rate, not bracket-based |

### 2.3 What Is Still Hardcoded

- **Single tax rate** parameter — not from template
- **ATAD thresholds** — hardcoded numeric values, not from template
- **Loss carryforward initialisation** — construction-period rule embedded in waterfall
- **No progressive CIT** — no support for bracket-based CIT in waterfall
- **No separate book/tax depreciation** — uses single `depreciation_keur` input

### 2.4 Current Tax Semantics

```
EBITDA
  - depreciation_keur          (single figure — book OR tax dep)
  - senior_interest_keur
  - shl_interest_keur
  + ATAD_addback
  + fiscal_reintegration
  - loss_carryforward
  = taxable_profit_keur
  × tax_rate (flat)
  = tax_keur
```

**Problem:** This conflates book depreciation with tax depreciation. For projects with accelerated tax depreciation (e.g., ME infrastructure at 2.5% cap), the waterfall overstates taxable income in early years (book dep > tax dep) and understates it in later years.

---

## 3. Target SPV Tax Integration

### 3.1 Where SPVTaxResult Enters Waterfall

The waterfall will receive `SPVTaxEngineInputs` per SPV and produce `SPVTaxResult` per SPV. The integration point is **after EBITDA is known and before CFADS is computed**:

```
EBITDA (per SPV)
  → run_spv_tax_engine(SPVTaxEngineInputs) → SPVTaxResult
  → SPVTaxResult.cit_payable_keur → waterfall tax_keur input
  → cf_after_tax = EBITDA - tax_this_period
```

The waterfall continues to own CFADS computation, debt sculpting, and distribution logic.

### 3.2 How Tax Payable Eventually Becomes Cash Outflow

1. `SPVTaxResult.periods[p].cit_payable_keur` is the cash tax for period `p`
2. Tax is paid semi-annually: `tax_this_period = cit_payable if period_in_year == 2 else 0`
3. `cf_after_tax = EBITDA - tax_this_period`
4. CFADS for debt sculpting = `cf_after_tax`

**Cash timing:** Tax is a real cash outflow in the period it is paid. The SPV engine computes it in the period it accrues; payment occurs in the second half-year period.

### 3.3 Where Taxable Income Should Be Calculated

Taxable income is calculated **inside `run_spv_tax_engine`** using:

```
EBITDA
  - deductible_interest_keur          (from financing inputs, ATAD-limited)
  - tax_depreciation_keur              (from TaxDepreciationSchedule, NOT book dep)
  + non_deductible_addbacks_keur       (timing difference addback)
  - loss_used_keur                     (from TaxLossCarryforwardSchedule)
  = taxable_income_after_losses_keur

CIT = calculate_progressive_cit(taxable_income_after_losses, cit_tiers)
```

The waterfall does NOT recalculate taxable income — it only routes the result.

### 3.4 How Depreciation Timing Differences Remain Audit-Visible

The `TaxDepreciationSchedule` tracks:

- `book_depreciation_keur` — accounting depreciation (goes to P&L)
- `tax_depreciation_keur` — tax depreciation claimed (goes to tax return)
- `non_deductible_depreciation_keur` — current period timing difference (book > tax)
- `accumulated_non_deductible_depreciation_keur` — cumulative timing difference pool

This is exported to the **tax audit Excel sheets** for reviewer verification. The waterfall audit trail shows:
- Book depreciation (P&L impact)
- Tax depreciation (tax return basis)
- Timing difference movement period-by-period
- Accumulated pool balance

### 3.5 How Tax Loss Carryforward Interacts With Periods

`TaxLossCarryforwardSchedule` tracks:
- `taxable_income_before_losses_keur` — profit before loss offset
- `loss_used_keur` — losses utilised this period
- `taxable_income_after_losses_keur` — profit after loss offset
- `closing_loss_carryforward_keur` — pool balance for next period

The **loss pool is per SPV**, tracked across all operational periods. When the pool is exhausted, CIT is payable on full taxable income.

---

## 4. Separation of Concerns

### 4.1 Accounting Depreciation vs Tax Depreciation

| Concept | Used By | Definition |
|---|---|---|
| Book depreciation | P&L, financial statements | `book_depreciation_keur` — straight-line or asset-life schedule |
| Tax depreciation | Tax return, SPV engine | `tax_depreciation_keur` — based on `TaxDepreciationRule`, may be capped or accelerated |

**Rule:** Tax depreciation is NEVER greater than book depreciation for timing-difference assets. For non-deductible assets (`deductible=False`), tax depreciation = 0.

### 4.2 EBITDA vs Taxable Income

```
EBITDA
  = Revenue - OPEX (cash operating profit, no depreciation)

Taxable income
  = EBITDA
  - deductible_interest
  - tax_depreciation
  + non_deductible_addbacks
  - loss_carryforward_used
```

EBITDA ignores financing and depreciation. Taxable income deducts financing costs (interest) and uses tax depreciation rules.

### 4.3 Cash Tax vs Accounting Tax

| | Cash Tax | Accounting Tax |
|---|---|---|
| When paid | Semi-annual (period 2 of each FY) | Accrued per period |
| Basis | `cit_payable_keur` from SPV engine | Period CIT from P&L |
| Difference | Timing of payment | Deferred tax (future phase) |

**Current model:** Uses accounting tax (CIT accrued) for `cf_after_tax`. **Target:** Use cash tax paid.

### 4.4 SHL Interest vs SHL Principal

- **SHL interest** (`shi_keur`) — deductible financing cost, flows into taxable income
- **SHL principal** — not a P&L item; repayment reduces balance sheet, not taxable income
- SHL PIK (payment-in-kind) — not yet implemented; will need separate tax treatment

### 4.5 SPV Tax vs HoldCo Tax

| Entity | Tax Engine | CIT Basis |
|---|---|---|
| SPV | `run_spv_tax_engine` | SPV-level taxable income |
| HoldCo | Future `HoldCoTaxEngine` | Dividends received + SHL interest - costs |

**Separation:** SPV pays CIT on its own taxable income. HoldCo receives dividends (often 0% or exempted) and pays tax on other income. Intercompany flows must avoid double-taxation.

### 4.6 Tax Engine vs Waterfall Engine

| | Tax Engine | Waterfall Engine |
|---|---|---|
| Responsibility | Calculate CIT payable per period | Route cash after tax to debt and distributions |
| Inputs | EBITDA, interest, depreciation, tax config | CFADS, debt schedules |
| Outputs | `SPVTaxResult` (per period CIT) | `WaterfallResult` (distributions, debt balances) |
| Wired? | NO (current state) | YES (current state) |

**Integration rule:** Tax engine produces CIT; waterfall consumes CIT. Tax engine does NOT know about debt sizing or distribution constraints.

---

## 5. Future HoldCo / Intercompany Tax

*(Documenting forward-looking architecture — NOT in scope for Phase 6B.7)*

### 5.1 HoldCo Tax Engine

Future `HoldCoTaxEngine` will handle:
- Dividend income from SPVs (participation exemption or reduced rate)
- SHL interest income (gross or net of WHT)
- Deductible HoldCo operating costs
- Thin-cap limitations on intercompany debt

### 5.2 Withholding Tax

- **WHT on SHL interest** — currently `shl_wht_rate=0.0` in waterfall; future engine will apply per treaty rate
- **WHT on dividends** — future HoldCo engine applies per jurisdiction
- Source-country withholding vs residence-country relief (tax treaty analysis)

### 5.3 Dividend Upstream Taxation

- SPV → HoldCo dividends may attract WHT in source country
- Participation exemption in residence country (if applicable)
- Must not double-count: SPV CIT already paid, upstream should not be taxed again

### 5.4 SHL Deductibility

- SHL interest deductibility at HoldCo level subject to thin-cap rules
- EBITDA limitation at HoldCo level may restrict SHL interest deduction
- Future: separate deductibility check per entity

### 5.5 Thin-Cap / EBITDA Limitations

- ATAD rule: deductable interest ≤ 30% of EBITDA (or 3M EUR floor)
- Applied at SPV level in current `compute_period_tax`
- Future: apply at HoldCo level with group EBITDA

### 5.6 Multi-Jurisdiction Considerations

- SPV may be in Montenegro (ME), HoldCo in Croatia (HR) or Luxembourg
- Different CIT rates, WHT rates, CFC rules
- Transfer pricing for intercompany loans
- Tax treaty network affects effective tax rate

---

## 6. Tax Governance / Overrides

### 6.1 Template Ownership

| Template | Owner | Purpose |
|---|---|---|
| `HR_SIMPLE_2026` | Finance team | Croatia flat-rate illustrative |
| `ME_INFRA_2026` | Finance team | Montenegro progressive illustrative |

Templates are declarative data in `domain/tax/templates/registry.py`. They are **not code** — they can be updated by editing data, not Python.

### 6.2 User Overrides

`TaxTemplateOverride` enables per-project patches:

```python
TaxTemplateOverride(
    override_name="custom_cit_rate",
    field_path="cit_tiers.0.tax_rate",
    override_value=0.12,
    reason="Site-specific CIT rate negotiated with tax authority",
)
```

Overrides are resolved at `SPVTaxEngineInputs` construction time, producing `ResolvedTaxConfig`. The override does not mutate the template.

### 6.3 Country-Specific Assumptions

All templates must document:
- Which asset categories exist
- Depreciation caps and useful lives
- Loss carryforward rules and caps
- Any non-standard deductions or addbacks

Current templates are **illustrative only** — marked with `metadata: (("note", "illustrative only"),)`.

### 6.4 Legal Review Disclaimers

All tax calculations must carry a disclaimer:

> "Tax results are for financial modelling purposes only. Do not use for actual tax compliance. Consult qualified tax advisors for your jurisdiction."

### 6.5 Auditability Expectations

Every SPV tax calculation must produce an audit trail showing:
- Input values (EBITDA, interest, depreciation)
- Calculation steps (deductible amounts, addbacks, losses)
- Output (CIT payable, effective rate)
- Timing differences (depreciation schedule)
- Loss pool movement

This is provided by `SPVTaxResult` / `SPVTaxPeriodResult` and exported to `Tax_{entity}` audit sheet.

### 6.6 Future Tax-Role Concept

Future: introduce a `TaxRole` concept where different parties own different parts of the tax configuration:
- **Template owner** — defines jurisdiction defaults
- **Project finance team** — approves overrides
- **Legal counsel** — reviews treaty assumptions
- **Auditor** — reviews computed results vs templates

---

## 7. Integration Risks

### 7.1 HIGH Risks

| Risk | Description | Mitigation |
|---|---|---|
| **Double-counting tax** | SPV tax AND waterfall tax both applied to same CF | Ensure only one tax engine writes `tax_keur`; SPV engine replaces waterfall `compute_period_tax` |
| **Cashflow timing mismatch** | Tax accrued in period P, paid in period P+2; waterfall uses wrong period's tax | Explicit `is_tax_period` flag; SPV engine produces accrual, waterfall applies payment timing |
| **Mixing book/tax depreciation** | Waterfall uses book dep for EBITDA-to-CFADS; tax engine uses tax dep for CIT | Waterfall EBITDA already excludes dep; confirm EBITDA definition is consistent |

### 7.2 MEDIUM Risks

| Risk | Description | Mitigation |
|---|---|---|
| **Loss carryforward misuse** | Tax losses used in SPV engine vs waterfall engine separately | Single `TaxLossCarryforwardSchedule` per SPV; waterfall reads from SPV result, does not recompute |
| **Circular HoldCo/SPV calculations** | HoldCo tax depends on SPV dividends; SPV distribution depends on post-tax CF | Phased approach: SPV first, HoldCo later; no circular reference in Phase 6B |
| **Progressive CIT edge cases** | CIT tier crossover creates large effective rate changes | `calculate_progressive_cit` is tested; verify bracket boundaries with actual template values |
| **Excel/export confusion** | Tax audit sheets show SPV results but model still uses waterfall tax | Label audit sheets "AUDIT-ONLY: not wired to model outputs" until integration complete |

### 7.3 LOW Risks

| Risk | Description | Mitigation |
|---|---|---|
| **Accumulated timing difference tracking** | `accumulated_non_deductible_depreciation_keur` not currently in `SPVTaxPeriodResult` | Future extension to expose accumulated pool; currently tracked in `TaxDepreciationSchedule` |
| **ATAD not applied in SPV engine** | SPV engine notes ATAD as deferred | Document limitation; apply ATAD in future ATAD engine layer |

---

## 8. Preconditions Before Real Tax Wiring

### 8.1 Reconciliation Tests

- [ ] `test_spv_tax_engine_vs_waterfall_tax` — compare SPV engine output against current waterfall tax for a reference project
- [ ] `test_tax_depreciation_vs_book_depreciation` — verify timing difference values are correct
- [ ] `test_loss_carryforward_across_periods` — verify pool depletion and replenishment

### 8.2 SPV Tax Validation

- [ ] `test_progressive_cit_calculation` — verify CIT tiers are applied correctly at bracket boundaries
- [ ] `test_zero_taxable_income` — verify CIT=0 when taxable income ≤ 0
- [ ] `test_non_deductible_asset` — verify no tax dep claimed for `deductible=False` assets

### 8.3 Tax Audit Visibility

- [ ] All `SPVTaxPeriodResult` fields are exported to Excel
- [ ] `TaxDepreciationSchedule` is exportable per asset category
- [ ] `TaxLossCarryforwardSchedule` is exportable
- [ ] Audit sheets are clearly labelled AUDIT-ONLY until wired

### 8.4 HoldCo Separation

- [ ] SPV engine does not reference HoldCo inputs
- [ ] HoldCo tax engine can be implemented independently
- [ ] Interface between SPV and HoldCo is documented (dividends, SHL interest amounts)

### 8.5 Scenario Consistency

- [ ] SPV engine produces deterministic results (same inputs → same outputs)
- [ ] Tax results are consistent across all scenarios for the same project
- [ ] Tax inputs (template, overrides) are per-scenario configurable

### 8.6 Regression Suite Thresholds

- [ ] Existing waterfall tests pass with same debt sculpting, DSCR, distribution outputs
- [ ] No regression in `test_tax_ui`, `test_tax_excel_export`
- [ ] No regression in overall model IRR, NPV outputs (within 0.01pp tolerance)

---

## 9. Explicit Non-Scope

The following are **intentionally missing** after Phase 6B.7:

| Item | Reason |
|---|---|
| SPV tax → waterfall wiring | Phase 6B.8 |
| ATAD EBITDA limitation in SPV engine | Future ATAD engine layer |
| Deferred tax (DTA/DTL) | Future DTA/DTL engine layer |
| HoldCo tax engine | Phase 6C |
| Withholding tax on SHL interest | Future WHT engine layer |
| Withholding tax on dividends | Future HoldCo engine |
| Thin-cap / EBITDA at HoldCo level | Future thin-cap engine |
| Sponsor IRR / sponsor waterfall | Future Phase 6D |
| SHL tax deductibility at HoldCo | Future Phase 6C |
| Multi-jurisdiction SPV consolidation | Future Phase 6C |
| RC1 modification for tax wiring | Not needed for Phase 6B.7 |
| Distribution constraint changes | Not affected by SPV engine |

---

## Phase 6 Claude Review Checklist

### SPV Tax Engine Invariants

- [ ] `SPVTaxResult` is produced by `run_spv_tax_engine` with no side effects
- [ ] `cit_payable_keur >= 0` for all periods
- [ ] `taxable_income_after_losses_keur >= 0` for all periods (losses reduce to 0, not below)
- [ ] `effective_tax_rate` is in [0.0, 1.0] when `taxable_income_after_losses > 0`
- [ ] `closing_loss_carryforward_keur >= 0` (pool never negative)
- [ ] `non_deductible_depreciation_keur` is a period **delta** (book_dep - min(book_dep, tax_dep)), not accumulated pool

### Depreciation Timing Difference Checks

- [ ] For `deductible=True` assets: `tax_depreciation_keur <= book_depreciation_keur` in each period
- [ ] For `deductible=False` assets: `tax_depreciation_keur == 0` always
- [ ] `TaxDepreciationSchedule.periods` has one entry per model period
- [ ] `accumulated_non_deductible_depreciation_keur` at end of schedule equals sum of period deltas (fully recovered) or is positive (some unrecovered)

### Loss Carryforward Checks

- [ ] Loss is generated when `taxable_income_before_losses_keur < 0`
- [ ] Loss is used when prior period closing pool > 0 and current `taxable_income_before_losses > 0`
- [ ] `loss_used_keur <= opening_pool_balance`
- [ ] `closing_loss_carryforward_keur = opening_pool + generated - used`
- [ ] `loss_used_keur` capped by `loss_carryforward_cap` (% of profit)

### Progressive CIT Checks

- [ ] CIT tiers applied in order: lower bracket at lower rate, excess at higher rate
- [ ] `taxable_income_after_losses_keur == 0` → `cit_payable_keur == 0`
- [ ] Single-tier template produces flat-rate CIT
- [ ] Multi-tier template produces correct bracket calculation

### Export Consistency Checks

- [ ] `Tax Summary` sheet lists all SPV entities and years
- [ ] `Tax_{entity}` sheet has one row per period
- [ ] Column headers match `SPVTaxPeriodResult` field names
- [ ] AUDIT-ONLY disclaimer present on each tax sheet
- [ ] Excel file opens without errors after tax export

### Future HoldCo Tax Readiness

- [ ] SPV engine does not reference HoldCo inputs
- [ ] `SPVTaxResult.cit_payable_keur` is independently computable without HoldCo context
- [ ] Dividend upstream amount is separately passed to HoldCo engine (not derived from SPV result)
- [ ] SHL interest paid by SPV is visible as separate output (not baked into SPV CIT)

### Sponsor Waterfall Readiness Dependencies

- [ ] `distribution_keur` is computed after tax in the current waterfall
- [ ] SPV tax wiring will NOT change the distribution logic
- [ ] Sponsor IRR depends on `distribution_keur`, not directly on tax
- [ ] Tax changes affect sponsor IRR only through `cf_after_tax` → `distribution_keur`

---

*Document version: 2026-05-11 | Phase: 6B.7 | Status: Architecture only — NOT wired to model outputs*
