# Phase 7F-5 PR A → Codex Handoff Package

## 1. Branch & Commit

- **Branch:** `phase7f-tuho-distribution-calibration`
- **Latest commit SHA:** `6a4cc10` (committed 2026-05-13)
- **Remote:** `origin/phase7f-tuho-distribution-calibration`
- **PR link:** https://github.com/xofisamba/Finco1/pull/new/phase7f-tuho-distribution-calibration

---

## 2. Files Changed in PR A

```
domain/inputs.py
  + use_senior_sweep_cash_cap_for_shl: bool = False  (FinancingParams)

app/cache.py
  + inputs.financing.use_senior_sweep_cash_cap_for_shl  (hash_inputs_for_cache)

domain/waterfall/waterfall_engine.py
  + use_senior_sweep_cash_cap_for_shl: bool = False  (run_waterfall signature)
  + disabled TUHO SHL cap block with pass + diagnostic comment (lines ~678-689)

app/waterfall_core.py
  + use_senior_sweep_cash_cap_for_shl param (run_waterfall_v3_core)
  + passes to run_waterfall()

app/waterfall_runner.py
  + use_senior_sweep_cash_cap_for_shl in WaterfallRunConfig
  + reads getattr(fin, "use_senior_sweep_cash_cap_for_shl", False) in from_inputs()
  + passes to run_waterfall_v3_core()

app/project_factories.py
  + use_senior_sweep_cash_cap_for_shl=True  (create_default_tuho_wind1)

tests/test_tuho_shl_calibration.py  (NEW)
  5 tests: (a) day_fraction, (b) SHL balance P28-P36, (c) first dist P36,
           (d) total dist vs R119, (e) Oborovo unchanged

docs/phase7f_prb_waterfall_reorder_analysis.md  (NEW)
  PR B analysis: waterfall ordering, exact code changes needed
```

---

## 3. Exact PR A Status

| Item | Status |
|---|---|
| Flag propagation complete | ✅ YES |
| Wrong remaining_senior_balance cap | ✅ DISABLED (`pass` + comment, no dead code) |
| TUHO flag `use_senior_sweep_cash_cap_for_shl` | ✅ `True` |
| Oborovo flag | ✅ `False` (default) |
| `test_tuho_shl_interest_rate_matches_day_fraction` | ✅ PASS |
| `test_oborovo_legacy_distribution_keur_unchanged` | ✅ PASS |
| TUHO SHL balance test | ❌ FAIL (expected, pre-fix) |
| TUHO first distribution test | ❌ FAIL (expected, pre-fix) |
| TUHO total dist test | ❌ FAIL (expected, pre-fix) |

---

## 4. Full Test Suite Summary

```
Total:   3053 passed | 7 failed | 2 skipped | 1 xfailed
Runtime: 71 seconds
```

### All 7 Failing Tests

**3 NEW (PR A, pre-fix baseline — expected to fail):**
1. `tests/test_tuho_shl_calibration.py::test_tuho_shl_balance_p28_to_p36_matches_excel`
2. `tests/test_tuho_shl_calibration.py::test_tuho_first_distribution_period_is_p36`
3. `tests/test_tuho_shl_calibration.py::test_tuho_total_distributions_vs_excel_r119`

**4 PRE-EXISTING (fixture gaps documented in KNOWN_DIVERGENCE_TUHO):**
4. `tests/test_full_horizon_sponsor_calibration.py::TestTUHOFullHorizonSponsor::test_tuho_spv_total_document_delta`
5. `tests/test_full_horizon_sponsor_calibration.py::TestTUHOFullHorizonSponsor::test_tuho_calibration_report`
6. `tests/test_full_horizon_sponsor_calibration.py::TestDeterministicReconciliation::test_tuho_adapter_reconciles_to_fixture`
7. `tests/test_tuho_calibration_reconciliation.py::TestTUHOGoldenReferenceUpdated::test_tuho_golden_total_is_model_produced`

### Checks Passed
- ✅ No new failures outside TUHO calibration tests
- ✅ Oborovo tests: all PASS (105 tests)
- ✅ Sponsor tests: all PASS
- ✅ Waterfall tests: all PASS
- ✅ App imports: OK (`from app.project_factories import create_default_oborovo, create_default_tuho_wind1`)

---

## 5. Baseline Calibration Numbers

### TUHO

| Metric | Python (current) | Excel | Gap |
|---|---|---|---|
| Total distributions | **180,570 kEUR** | **151,709 kEUR** (CF R119 sum) | +19.0% |
| First dist period | **index 33** (date ~2045-12-31) | **index 36** (date 2047-12-31) | Python 3 periods early |
| SHL P32 closing | **4,465 kEUR** | **20,699 kEUR** | -78.4% |
| SHL total service | 73,523 kEUR | — | — |
| Equity IRR | 6.72% | 11.61% | -4.89 pp |
| Sponsor IRR | 13.33% | — | — |

Excel fixture source: `tests/fixtures/excel_tuho_full_model_extract.json`
- SHL sheet columns: `['date', 'opening', 'closing', 'gross_interest', 'principal_flow', 'paid_net_interest', 'capitalized_interest', 'net_dividend']`
- net_dividend column (idx=7): first positive at index 36 (2047-12-31), total positive = 151,709 kEUR

### Oborovo

| Metric | Python (current) | Excel Golden | Gap |
|---|---|---|---|
| Total distributions | **104,699 kEUR** | **104,918 kEUR** | -0.2% |
| Excel net_dividend sum | — | **58,192 kEUR** (SHL sheet) | — |

Oborovo fixture source: `tests/fixtures/excel_oborovo_full_model_extract.json`
- net_dividend first positive: index 40 (2050-06-30)
- R109/R129 data: not available in current fixtures (CF sheet has only 4 columns: date, project_irr_cf, unlevered_project_irr_cf, fcf_for_banks)

---

## 6. Current Waterfall Ordering (from actual code)

File: `domain/waterfall/waterfall_engine.py`

```
Line  ~628:  senior_ds        ← computed from balance_schedule (EBITDA-scheduled DS)
Line  ~650:  _cf_for_shl     ← max(0.0, cf_after_tax - senior_ds - dsra_contrib)  [→ SHL]
Line  ~668:  [TUHO CAP DISABLED — pass statement]
Line  ~670:  compute_shl_period_v3(cf_after_senior_ds=_cf_for_shl, ...)  ← SHL CALL
Line  ~704:  shl_svc = shi + shp
Line  ~706:  cf_after_ds      ← cf_after_tax - senior_ds - shi  [YES, subtracts shi]
Line  ~728:  cf_after_reserves ← cf_after_ds + dsra_withdrawal - dsra_contrib
Line  ~733:  dscr             ← ebitda_minus_tax / senior_ds
Line  ~737:  lockup           ← dscr < lockup_dscr
Line  ~745:  sweep_dscr_threshold = 1.35  [HARDCODED]
Line  ~749:  remaining_senior_balance ← balance_schedule[period_in_tenor]
Line  ~756:  elif remaining_senior_balance > 0:
Line  ~758:      dist, sweep_amount = cash_sweep(cf_after_reserves, ...)  ← SENIOR SWEEP
Line  ~773:  dist = max(0, cf_after_reserves)  [senior repaid, SHL done]
Line  ~790:  distribution_keur ← dist  [ASSIGNED]
```

**Key:** `cf_after_reserves` (line ~728) is computed AFTER the SHL call (line ~670).
It already includes `-shi` (SHL interest paid). It does NOT include `-shp` (SHL principal).

---

## 7. ⚠️ Critical Cautions for Codex

### DO NOT use remaining_senior_balance as R99-equivalent cash
`remaining_senior_balance` is a **debt balance** (kEUR), not a cash-flow amount.
Using it as a cap causes it to go to 0 when senior debt is repaid (around index 27),
which **blocks SHL repayment** exactly when TUHO should enter the sweep phase.
This was the bug in the disabled code (PR A lines ~682-687).

### DO NOT move cf_after_reserves above the SHL call without understanding what it contains
`cf_after_reserves` is defined AFTER the SHL call in the current code.
It includes `-shi` (SHL interest paid), which means it is already reduced by SHL cost.
If moved before the SHL call, it would not yet be reduced by SHL, changing the semantics.

### If a pre-SHL cash basis is needed, define it explicitly
The correct R99-equivalent cash before SHL call is:
```
senior_scheduled_ds  = senior_ds  (already computed line ~628)
cf_for_shl_pre_sweep = max(0.0, cf_after_tax - senior_ds - dsra_contrib)  (already computed as _cf_for_shl)
senior_sweep_amount   = cash_sweep(...)  ← must be computed BEFORE SHL call
r99_equivalent_cf    = cf_for_shl_pre_sweep - senior_sweep_amount
```

---

## 8. PR B Objective

### Goal
Implement the TUHO SHL cash-cap using a **valid cash-flow R99-equivalent basis**,
computed **before** `compute_shl_period_v3` is called.

### Constraints
- Enable ONLY when `use_senior_sweep_cash_cap_for_shl=True` AND `shl_repayment_method == "pik_then_sweep"`
- Oborovo behavior: MUST be preserved (flag=False for Oborovo, no change)
- `day_fraction` logic: MUST be preserved (already correct, tested)
- Do NOT implement UI changes
- Do NOT implement Phase 8, Phase 10, or `cash_to_equity_keur` semantic bridge unless explicitly requested

### Exact Change Needed

**Location:** `domain/waterfall/waterfall_engine.py`, between lines ~728 (`cf_after_reserves = ...`) and ~737 (`lockup = ...`)

**New block to insert:**
```python
# ── Senior sweep (moved before SHL to enable R99-equivalent cap) ──
# Compute senior sweep amount early so it can be used as the R99-equivalent
# basis for TUHO SHL cash cap.
if remaining_senior_balance > 0 and dscr > sweep_dscr_threshold:
    senior_sweep_amount, _ = cash_sweep(
        cf_after_reserves=cf_after_reserves,
        senior_debt_balance=remaining_senior_balance,
        sweep_dscr=sweep_dscr_threshold,
        actual_dscr=dscr,
        sweep_pct=1.0,
    )
else:
    senior_sweep_amount = 0.0

# ── TUHO SHL cash-cap (Excel R99-equivalent) ──
# r99_equivalent_cf: cash that survives after senior scheduled DS and sweep.
# This is the Excel R99 / FCF for Distribution equivalent.
# TUHO uses this to prevent SHL from consuming cash that Excel would
# hold back as sculpted FCF for senior debt coverage.
if use_senior_sweep_cash_cap_for_shl and shl_repayment_method == "pik_then_sweep":
    r99_equivalent_cf = max(0.0, cf_after_reserves - senior_sweep_amount)
    raw_cf_for_shl = _cf_for_shl
    _cf_for_shl = min(max(0.0, raw_cf_for_shl), max(0.0, r99_equivalent_cf))
```

**In distribution section (lines ~758-768):** replace `cash_sweep()` call with reuse:
```python
dist = max(0.0, cf_after_reserves - senior_sweep_amount)
sweep_amount = senior_sweep_amount
```

Full analysis: `docs/phase7f_prb_waterfall_reorder_analysis.md`

---

## 9. Test Commands

```bash
# PR A new tests
pytest tests/test_tuho_shl_calibration.py -v

# Sponsor calibration tests
pytest tests/test_full_horizon_sponsor_calibration.py -v

# Full suite (71 seconds)
pytest -q

# Quick import check
python3 -c "from app.project_factories import create_default_oborovo, create_default_tuho_wind1; print('OK')"
```

---

## 10. Remaining TODOs

### PR A (this branch, committed)
- [x] Flag propagation
- [x] Wrong cap disabled
- [x] TUHO flag = True
- [x] Oborovo flag = False
- [x] day_fraction test passes
- [x] Oborovo unchanged test passes
- [x] Tests document calibration gap
- [x] Pushed to origin

### PR B (not started)
- [ ] Insert senior_sweep_amount computation before SHL call
- [ ] Re-enable TUHO SHL cap with valid r99_equivalent_cf
- [ ] Reuse senior_sweep_amount in distribution section (no double computation)
- [ ] Run `test_tuho_shl_calibration.py` — expect 4/5 to pass
- [ ] Run full suite — expect all non-TUHO tests to pass
- [ ] Verify TUHO SHL P32 closing within ±5% of 20,699 kEUR
- [ ] Verify TUHO first dist at index 35 (Excel P36)
- [ ] Verify TUHO total dist within ±10% of 151,709 kEUR
- [ ] Oborovo unchanged (flag=False)

### Future (not in scope)
- CIT reconciliation (blocked by SHL fix)
- Phase 8 / Phase 10
- `cash_to_equity_keur` semantic bridge
- UI changes
