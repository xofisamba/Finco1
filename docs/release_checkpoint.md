# Release Checkpoint

## v1.4-bankable-runtime-active
**Date:** 2026-05-07
**Branch:** `main` (HEAD: `1cab0fe`)

---

### What Is Active

| Component | Status |
|-----------|--------|
| Bankable depreciation framework | ✅ Runtime-active |
| `depreciation_bankable.py` | ✅ Present and wired |
| `generate_tax_and_book_schedule()` | ✅ Tax/book schedules |
| `build_bankable_waterfall_schedule()` | ✅ Runtime bridge |
| `FULL_YEAR` convention | ✅ Explicitly forced in runtime |
| Day fraction application | ✅ Single point in `waterfall_core` |
| Legacy fallback | ✅ Preserved (no `advanced_capex_line_items`) |

---

### Runtime Flow

```
advanced_capex_line_items
  → ui_runner.py: build_bankable_waterfall_schedule(FULL_YEAR)
  → generate_tax_and_book_schedule(FULL_YEAR) → [1.0]*20 day fractions
  → returns ANNUAL depreciation amounts
  → WaterfallDepreciationSchedule(total_by_period=[annual])
  → WaterfallRunConfig
  → waterfall_core: dep = annual_dep * p.day_fraction (ONCE)
```

---

### Known Limitations

- ❌ No Excel tax/book depreciation sheets yet
- ❌ No external tax advisor sign-off
- ❌ No mid-year/COD-month convention
- ❌ No audited jurisdiction source tables
- ❌ HTMX prototype not production-ready
- ❌ TUHO CO2 revenue missing (611 kEUR Y1)
- ❌ Oborovo OpEx duplication (660 kEUR Y1)
- ❌ Streamlit cache collision risk (DSCR ±0.15 tolerance)

---

### Test Status

| Suite | Result |
|-------|--------|
| `test_depreciation_wiring.py` | 9 passed ✅ |
| `test_bankable_depreciation.py` | 26 passed ✅ |
| `test_golden_values.py` | 36 passed ✅ |
| Full suite | 1203 passed, 1 xfailed ✅ |

---

### Next Sprint Goals

1. Excel tax/book depreciation disclosure sheets
2. TUHO CO2 revenue fix
3. Oborovo OpEx duplication fix
4. HTMX production preparation
