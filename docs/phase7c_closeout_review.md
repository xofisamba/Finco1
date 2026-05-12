# Phase 7C Closeout Review

**Phase:** 7C — Waterfall Foundation (Tier Schema, Preferred Return, Runner, Capital Account Annotation, Audit Export, Golden Validation)
**Status:** ✅ Complete — merged to `main`
**Date:** 2026-05-12
**Test Suite:** 2819 passed | 1 skipped | 1 xfailed | 0 failed

---

## 1. Phase 7C Components Completed

| Sub-phase | Module | File | PR |
|-----------|--------|------|-----|
| 7C-1 | Sponsor waterfall tier schema | `domain/sponsor/sponsor_waterfall_tier.py` | #50 |
| 7C-2 | Preferred return calculator | `domain/sponsor/preferred_return_calculator.py` | #47 |
| 7C-3 | Waterfall allocation runner | `domain/sponsor/waterfall_runner.py` + `waterfall_allocation_result.py` | #51 |
| 7C-4 | Capital account tier annotation | `domain/sponsor/capital_account_tier_annotation.py` | #52 |
| 7C-5 | Audit Excel waterfall sheets | `app/sponsor_waterfall_excel_export.py` | #53 |
| 7C-6 | Golden validation + edge cases | `tests/test_waterfall_golden_validation.py` | #54 |

---

## 2. Waterfall Tier Schema Summary

**File:** `domain/sponsor/sponsor_waterfall_tier.py`

### TierType Enum
Five tier types covering the full distribution waterfall:

| TierType | Description | Allocation Logic |
|----------|-------------|-----------------|
| `RETURN_OF_CAPITAL` | Repays invested capital | Proportional by share until fully repaid |
| `PREFERRED_RETURN` | Pays accrued preferred return | Proportional by share up to unpaid balance |
| `GP_CATCH_UP` | 100% to GP until threshold | 100% of available to GP until GP has received threshold amount |
| `PROMOTE` | Promote split above preferred | Proportional by `SponsorShare` percentages |
| `RESIDUAL` | Residual distributions | Proportional by `SponsorShare` percentages |

### CompoundingConvention Enum
Three conventions for preferred return accrual:

| Convention | Formula |
|-----------|---------|
| `ANNUAL` | Full hurdle applied at odd period indices (annual boundaries). Even periods = 0. |
| `SIMPLE` | `opening_invested * hurdle_rate * accrual_periods` — no compounding |
| `SEMIANNUAL` | `opening_invested * ((1 + hurdle_rate)^accrual_periods - 1)` |

### SponsorShare
```
sponsor_code: str
allocation_percentage: float  # e.g. 0.80 for 80%
```

### SponsorWaterfallTier (frozen)
```
tier_index: int          # Determines tier ordering (lower = earlier in waterfall)
tier_type: TierType
sponsor_shares: tuple[SponsorShare, ...]
hurdle_rate_pa: float | None
compounding_convention: CompoundingConvention | None
description: str
```

**Key design decisions:**
- Tier ordering via `tier_index` (sorted ascending at construction)
- `hurdle_rate_pa` and `compounding_convention` are optional — only required for `PREFERRED_RETURN` tiers
- All structures are frozen/immutable
- `sponsor_shares` is a tuple (immutable list of shares)

---

## 3. Preferred Return Calculator Summary

**File:** `domain/sponsor/preferred_return_calculator.py`

### `PreferredReturnCalculatorInputs` (frozen)
```
tier: SponsorWaterfallTier          # Must be PREFERRED_RETURN tier
cumulative_invested_by_period: tuple[float, ...]  # Tuple (not list) for immutability
distributions_by_period: tuple[float, ...]
num_periods: int
```

**Input validation:**
- `cumulative_invested_by_period` and `distributions_by_period` are normalized to tuples in `__post_init__`
- `cumulative_invested_by_period` must be non-decreasing (enforced)
- All values must be finite (NaN/Inf rejected)

### `calculate_preferred_return()` → `PreferredReturnResult`

**Accrual logic:**
- `opening_invested_capital_keur[p] = cumulative_invested_by_period[p-1]` (or `[0]` for p=0)
- `invested_delta[p] = cumulative_invested[p] - cumulative_invested[p-1]` (or `[0]` for p=0)
- Accrual base is opening invested, not cumulative

**Hurdle satisfaction:**
- `hurdle_satisfied = True` when `cumulative_accrued_pref >= cumulative_invested * hurdle_rate`
- Once `True`, stays `True` for all remaining periods

**ANNUAL convention specifics:**
- Odd period indices (1, 3, 5...): full accrual `opening_invested * hurdle_rate`
- Even period indices (0, 2, 4...): 0 accrual (first half of year — no accrual yet)
- Annual boundary accrual happens at odd periods only

### `PreferredReturnAccrualEntry` (per-period, frozen)
```
period_index, opening_invested_capital_keur, invested_capital_delta_keur,
hurdle_rate_pa, compounding_convention, accrual_periods,
accrued_pref_keur, cumulative_accrued_pref_keur,
cumulative_distributions_keur, unpaid_pref_balance_keur, hurdle_satisfied
```

### `PreferredReturnResult` (frozen)
```
sponsor_code, hurdle_rate_pa, compounding_convention,
entries: tuple[PreferredReturnAccrualEntry, ...],
total_accrued_pref_keur, total_unpaid_pref_keur, all_periods_hurdle_satisfied
```

---

## 4. Waterfall Runner Summary

**Files:** `domain/sponsor/waterfall_runner.py` + `domain/sponsor/waterfall_allocation_result.py`

### `WaterfallRunnerInputs` (frozen)
```
tiers: tuple[SponsorWaterfallTier, ...]
available_cash_by_period: tuple[float, ...]
pref_result: PreferredReturnResult | None   # Optional preferred return data
cumulative_invested_by_period: tuple[float, ...]
num_periods: int
```

### `run_waterfall()` → `WaterfallAllocationResult`

Pure function. No mutation of inputs. Deterministic.

**Tier ordering:** tiers are sorted by `tier_index` at construction — the caller is responsible for assigning correct indices.

**Per-period allocation cascade:**
1. `RETURN_OF_CAPITAL`: repay invested capital. `remaining_roc = max(0, cumulative_invested - total_already_repaid)`. Allocate `min(available, remaining_roc)` proportional by share.
2. `PREFERRED_RETURN`: allocate `min(available, unpaid_pref_balance)` from `pref_result.entry_for(p)`.
3. `GP_CATCH_UP`: allocate 100% to GP until `cumulative_gp_received >= cumulative_invested_by_period[-1]`.
4. `PROMOTE`: allocate 100% of remaining proportional by `SponsorShare`.
5. `RESIDUAL`: allocate 100% of remaining proportional by `SponsorShare`.

**Cumulative tracking across periods:**
- `cumulative_repaid_roc`: per-sponsor dict, updated after ROC tier
- `cumulative_gp_received`: per-sponsor dict, updated after GP_CATCH_UP tier
- `cumulative_distributions`: per-sponsor dict, updated after each tier's allocation — used to populate `PeriodWaterfallResult.cumulative_distributions_by_sponsor_keur`

### Result Structures

**`TierAllocationEntry` (frozen):**
```
tier_index, tier_type, available_cash_before_tier_keur,
allocated_amount_keur, allocated_per_sponsor_keur,
remaining_cash_after_tier_keur
```

**`PeriodWaterfallResult` (frozen):**
```
period_index, available_cash_keur, tier_entries,
total_allocated_keur, total_remaining_cash_keur,
cumulative_distributions_by_sponsor_keur  # ← cumulative across ALL periods up to and including this one
```

**`WaterfallAllocationResult` (frozen):**
```
investor_id, period_results, total_allocated_keur,
total_distributions_by_sponsor_keur
```

**Cash conservation:** enforced in `PeriodWaterfallResult.__post_init__`:
```
available_cash_keur == sum(e.allocated_amount_keur for e in tier_entries) + total_remaining_cash_keur
```

---

## 5. Capital Account Tier Annotation Summary

**File:** `domain/sponsor/capital_account_tier_annotation.py`

### Design

Extends `CapitalAccountEntry` with optional tier-level metadata. Existing `SponsorCapitalAccount` and `CapitalAccountEntry` are **unchanged**.

### New Types

**`TierAnnotation` (frozen):**
```
tier_index: int | None
tier_type: TierType | None
sponsor_code: str | None
allocated_amount_keur: float | None
source_note: str
```
- `TierAnnotation.empty()` — null object pattern
- `is_empty` property — True when no tier info

**`TierAnnotatedCapitalAccountEntry` (frozen):**
```
entry: CapitalAccountEntry
annotation: TierAnnotation
audit_note: str
```
- `is_tier_annotated` — True when annotation is non-empty

**`TierAnnotatedSponsorCapitalAccount` (frozen):**
Same shape as `SponsorCapitalAccount` but with `TierAnnotatedCapitalAccountEntry` entries.

### `from_waterfall_allocation_result()`

Pure converter — does **not** mutate `WaterfallAllocationResult`.

- One `TierAnnotatedCapitalAccountEntry` per (period, tier) allocation for the given sponsor
- `entry.source = "distribution_from_holdco"` (valid `CapitalAccountEntry` source)
- `annotation.source_note` carries precise tier type: `preferred_return_allocation`, `gp_catch_up_allocation`, `promote_split`, `residual_split`
- Running balances are computed as negative cumulative distributions (return phase)
- Entries sorted by (period_index, tier_index)

---

## 6. Audit Excel Waterfall Sheets Summary

**File:** `app/sponsor_waterfall_excel_export.py`

### Three New Optional Sheets

All sheets follow the same pattern: audit note in row 1, headers in row 2, data from row 3. Values-only, no formulas.

| Sheet | Source | Created when |
|-------|--------|--------------|
| `Sponsor Waterfall Allocation` | `WaterfallAllocationResult` | `sponsor_waterfall_result` provided |
| `Preferred Return Accrual` | `PreferredReturnResult` | `sponsor_preferred_return_result` provided |
| `Tier Capital Account` | `tuple[TierAnnotatedSponsorCapitalAccount, ...]` | `tier_annotated_capital_accounts` provided |

### Integration with `build_excel_export()`

Three new optional parameters added (backward-compatible):
```python
sponsor_waterfall_result: WaterfallAllocationResult | None
sponsor_preferred_return_result: PreferredReturnResult | None
tier_annotated_capital_accounts: tuple[TierAnnotatedSponsorCapitalAccount, ...] | None
```

### Key Design Decisions

- All values pre-computed in domain layer — no recalculation in export
- `cumdist_*` columns collect the full union of sponsor codes across ALL periods (fixes missing sponsor columns when a sponsor appears only in early periods)
- Sheets are idempotent — existing sheets are not removed or overwritten
- Audit note: `"AUDIT-ONLY: sponsor waterfall audit sheet — read-only export artifact, not a distribution commitment or financial advice."`

---

## 7. Golden Validation and Edge-Case Coverage

**File:** `tests/test_waterfall_golden_validation.py`

**29 tests across 10 required validation areas:**

| # | Area | Tests |
|---|------|-------|
| 1 | Preferred return annual compounding | ANNUAL: odd periods accrue, even = 0; ANNUAL vs SIMPLE different |
| 2 | Return-of-capital exhaustion | Partial repayment; full repayment + excess rolls |
| 3 | Partial preferred return payment | min(available, unpaid_balance) |
| 4 | GP catch-up allocation | With sufficient cash; excess rolls to PROMOTE; threshold over multiple periods |
| 5 | Promote split allocation | 80/20 split; per-sponsor sum = total |
| 6 | Residual allocation | 80/20 split |
| 7 | Full tier cascade cash conservation | Per-period and aggregate |
| 8 | Tier-annotated capital account | Distributions match waterfall; tier metadata preserved; no mutation |
| 9 | Excel audit sheet reconciliation | Row counts; totals match domain; no mutation |
| 10 | Deterministic repeated-run equality | Identical outputs on rerun |

**Additional edge cases covered:**
- Zero-distribution periods
- Distributions exceeding contributed capital
- Multi-sponsor splits (2 and 3 sponsors)
- No GP catch-up cash available

**Test suite total:** 2819 passed | 1 skipped | 1 xfailed | 0 failed

---

## 8. Remaining Known Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Single-sponsor preferred return | `PreferredReturnResult` uses single `sponsor_code` | Phase 7D multi-investor support |
| `SponsorCapitalAccount` unchanged | Existing capital account has no tier annotations | Use `TierAnnotatedSponsorCapitalAccount` for waterfall-linked entries |
| No `distribution_by_period` in waterfall | Distributions are not tracked per-period in `WaterfallAllocationResult` | Available via `cumulative_distributions_by_sponsor_keur` difference |
| GP catch-up threshold = last period's cumulative invested | Does not support per-investor different thresholds | Phase 7D multi-investor capital stack |
| Tier ordering by `tier_index` | Caller must assign correct indices | Enforced at construction; duplicates rejected |
| No validation of tier ordering completeness | A gap in tier indices does not error | Caller responsible for contiguous 0-N indices |
| ANNUAL convention accrues at odd periods only | 8% hurdle → 800/10k per year, not 1600 | Documented; tests verify expected behavior |
| No support for mid-period capital injections in preferred return | `invested_capital_delta` computed as period-over-period difference | Works correctly for lump-sum at period 0 |

---

## 9. Phase 7D Readiness Assessment

### ✅ Ready For Phase 7D

1. **Tier schema is stable** — all five tier types implemented and tested
2. **Preferred return engine is isolated** — `calculate_preferred_return()` is a pure function with clear inputs/outputs
3. **Waterfall runner is pure and deterministic** — no side effects, no mutation, deterministic rerun equivalence
4. **Capital account annotation layer exists** — `from_waterfall_allocation_result()` can be extended for multi-sponsor
5. **Audit export layer is wired** — three new optional params in `build_excel_export()` are backward-compatible
6. **Golden validation is comprehensive** — 29 tests covering all key behaviors and edge cases
7. **No breaking changes to existing APIs** — all existing tests pass

### Phase 7D Likely Requirements (Not Implemented)

Based on the current architecture, Phase 7D (multi-investor capital stack) will need to extend:

| Area | Extension Needed |
|------|-----------------|
| `SponsorWaterfallTier` | Multiple sponsor shares already supported — no schema change needed |
| `PreferredReturnCalculatorInputs` | Currently single `sponsor_code` in result — needs per-sponsor accrual |
| `PreferredReturnResult` | Currently one sponsor per result — needs tuple of results or per-sponsor structure |
| `from_waterfall_allocation_result()` | Currently single `sponsor_code` filter — needs to generate entries for all sponsors |
| `TierAnnotatedSponsorCapitalAccount` | Already accepts tuple of accounts — should work for multi-sponsor |
| Waterfall audit sheets | May need per-sponsor sheets or combined view |

---

## 10. Recommended Phase 7D Implementation Order

Given the current architecture, the following order minimizes risk and maximizes reuse:

### Step 1: Per-Sponsor Preferred Return Results
- Extend `PreferredReturnCalculatorInputs` or create `PreferredReturnCalculatorMultiSponsorInputs`
- Compute preferred return accrual per sponsor (currently single-sponsor only)
- Keep `calculate_preferred_return()` pure and deterministic

### Step 2: Multi-Sponsor Waterfall Runner Extension
- Extend `WaterfallRunnerInputs` to accept per-sponsor preferred return results
- Extend `from_waterfall_allocation_result()` to generate annotated capital account entries for all sponsors
- Verify `TierAnnotatedSponsorCapitalAccount` handles multi-sponsor tuples correctly

### Step 3: Multi-Sponsor Excel Audit Sheets
- Extend `build_waterfall_allocation_table()` to include per-sponsor columns for all sponsors
- Extend `build_tier_capital_account_table()` for multi-sponsor annotated accounts
- Add per-sponsor waterfall allocation sheets if needed

### Step 4: Validation Suite Expansion
- Add golden tests for multi-sponsor tier cascade
- Add tests for per-sponsor preferred return reconciliation
- Add tests for cross-sponsor distribution fairness

### Step 5: Integration with Existing Financial Model
- Wire Phase 7D results into the Streamlit UI
- Connect to existing sponsor cashflow and IRR runners
- Ensure existing calibration targets still pass

---

## Quick Reference: Module Map

```
domain/sponsor/
├── sponsor_waterfall_tier.py          # TierType, CompoundingConvention, SponsorShare, SponsorWaterfallTier
├── preferred_return_calculator.py      # PreferredReturnCalculatorInputs, calculate_preferred_return()
├── preferred_return_result.py         # PreferredReturnAccrualEntry, PreferredReturnResult
├── waterfall_runner.py                # WaterfallRunnerInputs, run_waterfall()
├── waterfall_allocation_result.py     # TierAllocationEntry, PeriodWaterfallResult, WaterfallAllocationResult
└── capital_account_tier_annotation.py # TierAnnotation, TierAnnotatedCapitalAccountEntry,
                                         # TierAnnotatedSponsorCapitalAccount, from_waterfall_allocation_result()

app/
└── sponsor_waterfall_excel_export.py  # write_sponsor_waterfall_audit_sheets(),
                                        # build_waterfall_allocation_table(),
                                        # build_preferred_return_table(),
                                        # build_tier_capital_account_table()

tests/
├── test_waterfall_golden_validation.py # 29 golden tests (Phase 7C-6)
└── [all existing tests]               # 2819 total passed
```
