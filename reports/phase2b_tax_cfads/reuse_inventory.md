# Phase 2B — Reuse Inventory

Base SHA: `f42c0056115daf9d3b1c58d34ced9bb4948c644d`

---

## Required Schedules

| Schedule | Production Owner | Candidate Reusable Leaf | Reused Directly | Reason if Not |
|---|---|---|---|---|
| Vintage FIFO LCF | `finco_core.tax.loss_carryforward` | `compute_loss_carryforward_schedule(inputs, config)` | Yes | Full 5-yr × 2-period/yr FIFO with expiry-before-use flag |
| ATAD (annual threshold) | `finco_core.tax.atad_engine` | `atad_adjustment_v3(...)` / `atad_schedule_v3(...)` | Yes | Correct annual-threshold ATAD; H1/H2 accumulation |
| SPV tax runner | `finco_core.tax.engine_runner` | `run_spv_tax_engine(inputs)` | No | No ATAD or thin-cap wired; Phase 2B extends the contract |
| Canonical CFADS | Does not exist | — | No | No canonical function exists; Phase 2B defines `CFADS = EBITDA − cash_tax_paid` |
| Fiscal reintegration (R34 chain) | `finco_core.tax.interest_limitation` | `compute_interest_limitation_schedule(...)` | Yes | Pure; covers the R34/R54 chain |
| Tax depreciation schedule | `finco_core.tax.templates` | `build_tax_depreciation_schedule(...)` | Yes | Already reused in Phase 2A for book dep; same leaves |
| Progressive CIT | `finco_core.tax.templates` | `calculate_progressive_cit(taxable_profit, template)` | Yes | Pure rate-tier engine |
| LCF build (template helper) | `finco_core.tax.templates` | `build_tax_loss_carryforward_schedule(...)` | Yes | Helper used by runner; now paired with vintage ledger |
| Period grid | Already reused in Phase 2A | `PeriodEngine(...).periods()` | Yes | — |

---

## Modules Not Reused in Phase 2B

| Module | Reason |
|---|---|
| `finco_core.tax.engine.apply_loss_carryforward` | Naive year-list aggregation without vintage expiry; superseded by `loss_carryforward.py` |
| `finco_core.tax.engine.loss_carryforward_simple` | Simplified; no expiry tracking |
| `finco_core.tax.reintegration.fiscal_reintegration` | Hardcoded 3% IDC / 2% fee heuristics; not calibrated to actual IDC schedule |
| `finco_core.tax.tax_params.TaxParams` | Embeds ATAD with per-period threshold (incorrect); Phase 2B uses `atad_engine.py` |
| `finco_core.tax.holdco_*.py` | HoldCo layer; out of Phase 2B SPV scope |
| `finco_core.waterfall.cash_flow.cfads` | Post-DSRA CFADS (post-debt-service); not the canonical pre-DS definition |
| `app.waterfall_core` (sizing_cfads) | TUHO/Oborovo fixture reads; identity-aware; not used |

---

## CFADS — No Existing Canonical Function

Three distinct CFADS-like quantities exist in the codebase, none of which matches Phase 2B canonical CFADS:

| Location | Definition | Phase 2B Applicable? |
|---|---|---|
| `finco_core/waterfall/waterfall_engine.py` (sculpting proxy) | `max(0, ebitda × (1 − tax_rate))` | No — scalar proxy for debt sizing only |
| `finco_core/waterfall/waterfall_engine.py` (DSCR line) | `ebitda − tax_this_period` | Closest, but no cash-tax timing |
| `finco_core/waterfall/cash_flow.py` | `cf_after_reserves` (post-DSRA) | No — post-debt-service measure |

Phase 2B defines canonical CFADS as `EBITDA − cash_tax_paid` (H2 trigger, zero in H1 where tax is not yet crystallised). This is a new output computed in `financial_engine/cfads.py`.

---

## Baseline Snapshot Schema — `tax_and_cfads` Section

Fields that appear in the Phase 1 snapshots. Phase 2B must populate all required fields with zero-difference parity.

| Field | Type | Notes |
|---|---|---|
| `taxable_profit_keur` | float per period | Pre-ATAD, pre-LCF EBITDA − tax_dep − interest |
| `taxable_income_before_losses_audit_keur` | float per period | After ATAD / interest limitation |
| `taxable_profit_after_losses_audit_keur` | float per period | After vintage FIFO LCF |
| `tax_keur` | float per period | CIT accrual (rate × positive taxable profit) |
| `corporate_tax_cash_keur` | float per period | Cash tax paid (H2 trigger) |
| `cit_accrual_audit_keur` | float per period | Audit cross-check of CIT accrual |
| `tax_loss_opening_audit_keur` | float per period | Opening LCF pool before application |
| `tax_loss_closing_audit_keur` | float per period | Closing LCF pool after application |
| `tax_loss_used_audit_keur` | float per period | LCF consumed this period |
| `fiscal_reintegration_audit_keur` | float per period | Fiscal reintegration addback |
| `tax_depreciation_audit_keur` | float per period | Tax depreciation (audit trail) |
| `cf_after_tax_keur` | float per period | EBITDA − accrual tax (non-cash adjusted) |
| `cash_tax_current_period_audit_keur` | float per period | Cash tax this period (audit) |
| `cash_tax_bridge_reconciliation_keur` | float per period | Accrual-to-cash bridge |
| `fcf_for_shl_keur` | float per period | Out of Phase 2B scope → 0 |
| `r69_fcf_banks_keur` | float per period | Out of Phase 2B scope → 0 |
| `r84_fcf_junior_keur` | float per period | Out of Phase 2B scope → 0 |
| `r99_fcf_for_distribution_keur` | float per period | Out of Phase 2B scope → 0 |
| `r102_fcf_for_shl_keur` | float per period | Out of Phase 2B scope → 0 |

---

## `financial_engine/` — Current State

| File | Phase 2A Status | Phase 2B Action |
|---|---|---|
| `inputs.py` | `OperatingModelInput` — no tax inputs | Add `TaxCalculationInput` section |
| `results.py` | `ProjectModelResult` — `unavailable_sections` includes `"tax_and_cfads"` | Add `TaxAndCfadsSchedules` section; remove from unavailable |
| `policies/tax.py` | Structural stub (`policy_id`, `corporate_rate`, `loss_carryforward_years`, `tax_depreciation_basis`, `atad_applies`) | Replace with full `TaxPolicy` contract |
| `orchestrator.py` | `run_operating_model()` — no tax | Add `run_tax_cfads_model()` |
| `cfads.py` | Does not exist | Create: `calculate_canonical_cfads()` |
| `tax/` | Does not exist | Create: `models.py`, `atad.py`, `loss_ledger.py`, `engine.py` |
| `adapters/project_inputs.py` | Maps to `OperatingModelInput` | Extend for unambiguous tax inputs only |

---

## Limitations

This inventory covers Phase 2B: tax (SPV CIT, ATAD, LCF) and canonical CFADS only.
Debt service, SHL, DSRA, distributions, financial statements and returns are out of scope.
