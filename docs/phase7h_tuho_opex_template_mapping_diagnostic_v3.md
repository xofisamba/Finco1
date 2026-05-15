# Phase 7H O3a Diagnostic v3 — TUHO OPEX Template Mapping

## Engine Fixes Applied

### Fix A — EXPLICIT_SCHEDULE: no inflation
`_apply_inflation()` now returns `base` immediately for `OpexBasis.EXPLICIT_SCHEDULE` items.
Values in `explicit_schedule_keur` are used as-is, already final.

### Fix B — `inflation_start_exponent` field added to `OpexItem`
`inflation_start_exponent: int = 0` — default preserves existing behavior.
Exponent = `year_index - 1 + item.inflation_start_exponent`.
For B.07 items: set `inflation_start_exponent=1` (Excel uses `^year`, not `^(year-1)`).

### Fix C — `PCT_OF_SELECTED_GROUPS` added to `_compute_item_base` (pass1)
Added handling in pass1 `_compute_item_base`:
```python
if item.basis == OpexBasis.PCT_OF_SELECTED_GROUPS:
    selected_total = sum(group_totals[gc][y_idx] for gc in item.selected_group_codes if gc in group_totals)
    return selected_total * item.budget_keur / 100.0
```
For B.13 contingency: use `group.contingency_pct=0.0` — the pct item itself IS the contingency mechanism.
Do NOT add extra contingency from `group.contingency_pct` (would double-count).

---

## TUHO B.13 Contingency Verification

Confirmed: Excel B.13 Y1 = 113.10 = 6% × Σ(B.01:B.12 Y1 totals)

| Year | Σ(B.01–B.12) | 6% | Excel B.13 | Δ |
|------|-------------|-----|-----------|---|
| Y1 | 1,884.95 | 113.10 | 113.10 | 0.00 |
| Y2 | 1,914.94 | 114.90 | 114.90 | 0.00 |
| Y7 | 2,025.52 | 121.53 | 121.53 | 0.00 |
| Y10 | 2,056.72 | 123.40 | 123.40 | 0.00 |
| Y13 | 2,088.54 | 125.31 | 125.31 | 0.00 |
| Y20 | 2,243.40 | 134.60 | 134.60 | 0.00 |
| Y30 | 2,276.51 | 136.59 | 136.59 | 0.00 |

**B.13 = 6% × sum(B.01:B.12) confirmed exactly.**

---

## TUHO B.02.1 Explicit Schedule

Values from `Scenarios!I79:I108` (30 years):
```
Y1–Y2:   385.6
Y3–Y5:   465.6
Y6–Y10:  588.0
Y11–Y15: 628.0
Y16–Y20: 676.0
Y21–Y25: 756.0
Y26–Y30: 828.0
```
No inflation applied (already fully computed annual amounts).

---

## TUHO B.07 inflation_start_exponent=1

Excel B.07 Y1–Y3:
- Y1: 248.88 = 244 × 1.02^1 (not 244 × 1.02^0)
- Y2: 253.858 = 244 × 1.02^2
- Y3: 258.935 = 244 × 1.02^3

Confirmed: B.07 uses `^(year)` not `^(year-1)` — set `inflation_start_exponent=1`.

---

## Tests: 42 passed

```
tests/test_opex_line_item_engine.py: 42 passed
```

New tests added:
- `TestExplicitScheduleNoInflation`: 4 tests — explicit schedule ignores inflation, WTH still applies, manual override wins, inactive flag wins
- `TestInflationStartExponent`: 3 tests — default=0, start_exponent=1 shifts by one, step change resets from step year
- `TestContingencySelectedGroups`: 4 tests — pct item sole mechanism, no self-reference, changes with base, inactive base groups

---

## Engine Changes Summary

### `domain/opex/engine.py`
1. `_apply_inflation()`: added `if item.basis == OpexBasis.EXPLICIT_SCHEDULE: return base` (before step/inflation logic)
2. `_compute_item_base()`: added `PCT_OF_SELECTED_GROUPS` handling in pass1

### `domain/opex/line_items.py`
- Added `inflation_start_exponent: int = 0` to `OpexItem`

### `tests/test_opex_line_item_engine.py`
- Updated `make_item()` to accept `inflation_start_exponent`
- Updated `TestOpexContingency` tests to use `contingency_pct=0` (pct item is sole mechanism)
- Added `TestExplicitScheduleNoInflation` (4 tests), `TestInflationStartExponent` (3 tests), `TestContingencySelectedGroups` (4 tests)

---

## Next Steps (not in scope for offline engine fixes)

1. **Full TUHO template mapping**: Map all items (B.01–B.13) with correct codes, budgets, active flags, step changes
2. **B.01 Bazefield item**: Add missing item (budget=18 kEUR per Excel row)
3. **B.09 = 0**: Confirm B.09 should be zero (no telecom fees)
4. **B.11 Y20+**: B.11 drops to 0 at Y20 in Excel — check if this is active flags or explicit
5. **Re-run full parity**: After complete template, compare all 30 years vs Excel

---

## Runtime Behavior Confirmation

**No runtime changes.** The new OPEX engine is:
- NOT wired into `run_waterfall`
- NOT connected to existing TUHO factory runtime
- NOT affecting Oborovo, revenue, tax, SHL, senior debt, or any other model component

All 31 existing tests still pass (unchanged runtime behavior).