# v1.3 Bankable Framework Checkpoint

**Date:** 2026-05-07
**Branch:** `main` (merged from `feature/bankable-depreciation`)

---

## Framework Status

| Component | Status | Location |
|-----------|--------|----------|
| `depreciation_bankable.py` | ✅ Present, not runtime-active | `app/` |
| `depreciation_engine.py` | ✅ Present, active runtime path | `app/` |
| `DepreciationProfile` | ✅ Defined (solar_croatia_ibl, wind_croatia_ibl) | `depreciation_bankable.py` |
| `AssetClass` enum | ✅ 7 classes defined | `depreciation_bankable.py` |
| `generate_tax_and_book_schedule()` | ✅ Returns (tax, book) schedules | `depreciation_bankable.py` |
| `to_waterfall_depreciation_schedule()` | ✅ Bridge to WaterfallRunConfig | `depreciation_bankable.py` |
| `build_bankable_waterfall_schedule()` | ✅ One-step bridge | `depreciation_bankable.py` |

---

## Runtime Status

**NOT YET ACTIVE** — Runtime still uses `depreciation_engine.generate_schedule()`.

The bankable framework is introduced as a framework-only layer. Runtime activation deferred to `feature/bankable-runtime-wiring` sprint.

---

## Tests (This Merge)

| Suite | Result |
|-------|--------|
| `test_bankable_depreciation.py` | 26 passed ✅ |
| `test_depreciation_engine.py` | 18 passed ✅ |
| `test_depreciation_wiring.py` | 4 passed ✅ |
| Full suite (main) | 1194 passed, 1 xfailed ✅ |

---

## Known Limitations

1. **Inverter 25y in runtime** — current runtime groups inverters under GENERATION at 25y; bankable framework would map inverter keyword to 10y tax life
2. **Day-fraction double-application risk** — must resolve before runtime activation
3. **No mid-year convention** — bankable framework supports it but runtime doesn't apply it
4. **No Excel tax/book export** — deferred to future sprint

---

## Next Sprint Goals

1. **Runtime wiring** (`feature/bankable-runtime-wiring`): Replace `generate_schedule()` with `build_bankable_waterfall_schedule()`
2. **Day-fraction fix**: Single authoritative application point, regression tests
3. **Behavioral tests**: Inverter 10y effect, contingency allocation basis, COD year correct
4. **Excel disclosure roadmap**: Document future tax/book export structure
