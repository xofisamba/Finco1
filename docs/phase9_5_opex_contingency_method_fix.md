# Phase 9.5 — OPEX Contingency Method Fix

## Issue: Incorrect Double Inflation on OPEX Contingency

### Problem

The original TUHO OPEX template modeled contingency as a `PCT_OF_SELECTED_GROUPS` item with `budget_keur = 6.0` and `inflation_rate = 0.0`. The engine then applied the `PCT_OF_SELECTED_GROUPS` basis correctly in isolation, but the **intent was ambiguous**: was the 6% applied to the inflated or non-inflated base?

More critically, the modeling convention was not formally captured in the schema. There was no `contingency_method` field — only `contingency_pct` on `OpexGroup` (never set in the TUHO template — it was always 0.0). The contingency item used `PCT_OF_SELECTED_GROUPS` with `budget_keur = 6.0`, which the engine treated as applying inflation separately to the item's computed base *after* the percentage was taken.

**The actual bug**: When underlying OPEX inflates (2%/yr), the contingency should grow only because the base grows — it should not have a separate inflation rate applied. The engine code had no way to express this distinction; every `PCT_OF_SELECTED_GROUPS` item used the group or item's inflation rate for escalation, effectively double-escalating the contingency.

### Correct Modeling Treatment

Contingency can be modeled in two ways:

#### 1. Fixed Amount + Inflation
- Entered as a fixed kEUR amount
- Escalates by its own inflation rate
- **Use case**: when contingency has a contractually fixed escalation clause independent of other OPEX

#### 2. Percentage of Other OPEX (correct for TUHO)
- `contingency[t] = contingency_pct × sum(non-contingency OPEX[t])`
- **No separate contingency inflation** — inflation flows indirectly through the underlying OPEX lines
- **No circular reference** — the contingency group itself is excluded from the base
- This is the standard industry approach for project finance OPEX contingency reserves

### Formula

```
Let S[t] = sum(non-contingency groups, year t)
Let p  = contingency_pct / 100
Let C[t] = contingency amount for year t

Fixed Amount:
  C[t] = base_contingency × (1 + contingency_inflation)^t

Percentage of OPEX:
  C[t] = p × S[t]
  S[t] = sum(group_totals[g][t] for g in all_groups if g is not contingency_group)
```

### TUHO Template Impact

| Field | Before | After |
|-------|--------|-------|
| `OpexGroup.contingency_pct` | 0.0 (never set) | 6.0 |
| `OpexGroup.contingency_method` | not defined | `PERCENTAGE_OF_OPEX` |
| `OpexItem.B.13.1.basis` | `PCT_OF_SELECTED_GROUPS` | unchanged |
| `OpexItem.B.13.1.budget_keur` | 6.0 | unchanged |
| `OpexItem.B.13.1.inflation_rate` | 0.0 | unchanged |

**Y1 OPEX total unchanged**: 1,998.05 kEUR (B.01–B.13 sum verified against Excel)

**Y2 contingency difference (illustrative)**:
- Old (would compound contingency itself by 2%): 113.10 × 1.02 = 115.36 kEUR
- New (only base inflated by 2%): 114.90 kEUR
- Delta: ~0.46 kEUR/yr — small because TUHO has 0% inflation on B.02 and B.09, and most other groups inflate at 2%

### Backward Compatibility

- `OpexContingencyMethod.FIXED_AMOUNT` is the default on `OpexGroup`, preserving existing behavior for any template that doesn't set `contingency_method`
- The engine's second pass still handles non-contingency `PCT_OF_SELECTED_GROUPS` items exactly as before
- Only the behavior of groups with `contingency_method == PERCENTAGE_OF_OPEX` changes

### Files Changed

| File | Change |
|------|--------|
| `domain/opex/line_items.py` | Added `OpexContingencyMethod` enum; added `contingency_method` field to `OpexGroup`; added `is_contingency_group()` helper |
| `domain/opex/result.py` | Added `contingency_method`, `contingency_pct`, `contingency_base_keur` to `OpexGroupAnnualResult` |
| `domain/opex/engine.py` | New branch for `PERCENTAGE_OF_OPEX` method: computes `pct × sum(other groups)`, excludes self, zero separate inflation |
| `domain/opex/templates/tuho.py` | Set `contingency_pct=6.0` and `contingency_method=PERCENTAGE_OF_OPEX` on B.13 |
| `tests/test_opex_contingency_method.py` | **New** — 12 tests covering both methods, TUHO parity, result schema |
| `tests/test_tuho_opex_template_mapping.py` | Updated `test_b13_equals_six_percent...` to assert `contingency_pct=6.0` and `method=PERCENTAGE_OF_OPEX` |
| `app/templates/partials/sheet_opex.html` | Added Contingency Method card, updated inflation assumption label |
| `static/styles.css` | Added `.method-badge`, `.method-note`, `.no-inflation` styles |

### What Did NOT Change

- No changes to revenue, SHL, senior debt, tax, waterfall, `DistributionAccount`, `Sponsor`, construction, or CAPEX
- No changes to `OpexItem` dataclass fields
- No G20 approval or R99/R102 promotion
- No scalar plugs or convention overrides

### UI Behavior

The OPEX tab now shows:
- **Method badge**: `% of other OPEX` (highlighted in primary blue)
- **Explanatory note**: "% of OPEX mode does not apply separate inflation; inflation comes through the underlying OPEX lines."
- **Inflation assumption label**: updated from "6% annually" to "6% of other OPEX — no separate contingency inflation"

The "Fixed amount + inflation" method is shown in the hidden `.method-fixed` div for future use when live editing is implemented.

### Test Coverage

| Test | Coverage |
|------|----------|
| `test_contingency_excludes_itself_from_base` | Contingency group never in base |
| `test_contingency_equals_pct_of_non_contingency_opex` | Correct formula |
| `test_no_separate_contingency_inflation` | inflation_rate=0.0 on contingency item |
| `test_percentage_mode_contingency_grows_indirectly_via_underlying_opex` | Grows only because base inflates |
| `test_fixed_and_percentage_produce_different_results_when_inflation_exists` | Methods diverge |
| `test_tuho_contingency_y1_matches_excel_parity` | 113.10 kEUR ✓ |
| `test_tuho_contingency_uses_percentage_of_opex_at_6_percent` | Template assertions |
| `test_result_exposes_contingency_method_pct_and_base` | Result schema |

### Verification

```bash
# All OPEX tests pass
.venv/bin/python -m pytest tests/test_opex_contingency_method.py -v
# 12 passed

# TUHO template + engine tests
.venv/bin/python -m pytest tests/test_opex_line_item_engine.py tests/test_tuho_opex_template_mapping.py tests/test_opex_contingency_method.py -v
# 30 passed
```