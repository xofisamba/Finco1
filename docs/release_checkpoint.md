# Release Checkpoint

## v1.4.1-advisory-ready-screening
**Date:** 2026-05-07
**Branch:** `main` (HEAD: `e079c21` → now updated)
**Hotfix branch:** `hotfix/v1_4_1_advisory_ready` → merged to main

---

### What's New in v1.4.1

| Component | Status |
|-----------|--------|
| Wind profile plumbing fixed | ✅ Wind → wind_croatia_ibl |
| WIND_TURBINES asset class | ✅ Added to BankableAssetClass |
| Excel profile selection threaded | ✅ project_type passed explicitly |
| map_capex_line_item_to_basis updated | ✅ Solar→SOLAR_MODULES, Wind→WIND_TURBINES |
| DSCR tolerance documentation corrected | ✅ Policy tolerance, not cache collision |
| False-green test removed | ✅ test_advanced_capex_changes_taxable_income → meaningful invariant |
| HTMX foundation docs | ✅ docs/htmx_foundation_scope.md |

---

### Advisory Readiness

| Use Case | Status | Notes |
|----------|--------|-------|
| Internal advisory | ✅ GO | With known caveats |
| Controlled B2B pilot | ✅ GO | TUHO CO2 + Oborovo OpEx caveats apply |
| Investor-grade review | ⬜ Not yet | TUHO CO2 + Oborovo OpEx fixes needed |
| HTMX production | ⬜ Not yet | Auth + persistence required first |

---

### Known Calibration Caveats

| Issue | Impact | Fix Owner |
|-------|--------|-----------|
| TUHO CO2 revenue missing | Y1 revenue -611 kEUR (-12.5%) | Model fix |
| Oborovo OpEx duplication | Y1 OpEx +660 kEUR too high | Model fix |

**Do NOT mask these with DSCR tolerance — they are model bugs.**

---

### Bankable Runtime Active

| Component | Status |
|-----------|--------|
| `depreciation_bankable.py` | ✅ Runtime-active |
| `generate_tax_and_book_schedule()` | ✅ Tax/book schedules |
| `build_bankable_waterfall_schedule()` | ✅ Runtime bridge |
| `FULL_YEAR` convention | ✅ Explicitly forced in runtime |
| Day fraction application | ✅ Single point in `waterfall_core` |
| Legacy fallback | ✅ Preserved (no `advanced_capex_line_items`) |
| Excel Depreciation Assumptions | ✅ Solar + Wind profiles |
| Tax Depreciation sheet | ✅ Per-asset-class annual |
| Book Depreciation sheet | ✅ Per-asset-class annual |

---

### Test Status

| Suite | Result |
|-------|--------|
| `test_depreciation_wiring.py` | 10 passed ✅ |
| `test_bankable_depreciation.py` | 26 passed ✅ |
| `test_excel_depreciation_disclosure.py` | 13 passed ✅ |
| `test_golden_values.py` | 36 passed ✅ |
| Full suite | **1216+ passed, 1 xfailed** ✅ |

---

### DSCR Tolerance — Updated

**±0.15 is a defensive policy tolerance** for future model improvements.
**NOT caused by runtime nondeterminism.**

| Concern | Explanation |
|---------|-------------|
| Runtime nondeterminism | None — model is deterministic |
| Cache collisions | Golden tests run via API layer, not Streamlit |
| Deliberate model improvements | May shift DSCR — policy tolerance covers this |
| TUHO CO2 / Oborovo OpEx | Model bugs — fix separately, not masked |

---

### Previous Checkpoints

- [v1.4-bankable-runtime-active](./release_checkpoint_v1.4.md)