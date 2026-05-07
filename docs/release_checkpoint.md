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
---

## v1.5.0-htmx-internal-demo
**Date:** 2026-05-07
**Branch:** `main` (HEAD: `c38ac83`)
**Merge:** `feature/htmx-internal-demo` → main

### What's New

| Component | Status |
|-----------|--------|
| HTMX internal demo (`main_web.py`) | ✅ FastAPI + Jinja2 + HTMX |
| Custom inputs wired | ✅ `ProjectInputsSchema` → `build_projectinputs()` |
| Excel download | ✅ POST /download with form state |
| Compare scenarios | ✅ Base/Downside/Upside comparison |
| No silent fallback | ✅ Fail-fast on invalid inputs |
| Regression tests | ✅ 34 tests (test_htmx_internal_demo.py) |
| Depreciation disclosure sheets | ✅ In Excel export |
| Streamlit fallback preserved | ✅ Available on ports 8501-8503 |

### HTMX Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Main input form |
| POST | `/validate` | Form validation (partial) |
| POST | `/run` | Run model → KPI partial |
| POST | `/compare` | Compare Base/Downside/Upside |
| GET/POST | `/download` | Excel export (xlsx) |
| GET | `/health` | `{"status": "ok"}` |

### Deployment

- **Contabo private deployment**: `docs/contabo_private_deployment.md`
- **Internal demo only**: `python main_web.py` → http://localhost:8765
- **No auth / no persistence**: not for public access

### Known Limitations

| Item | Notes |
|------|-------|
| No auth | Single admin deploy only |
| No persistence | Excel on-demand, no server state |
| TUHO CO2 missing | 611 kEUR Y1 not in model |
| Oborovo OpEx duplication | +660 kEUR Y1 too high |

---

### Previous Checkpoints

- [v1.4.1-advisory-ready-screening](./release_checkpoint.md#v141-advisory-ready-screening)

