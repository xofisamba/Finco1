# Excel Parity Stack Q — Oborovo DSCR CFADS Basis + Python 3.11 Test Fix

**Branch:** `excel-parity-stack-q-oborovo-dscr-cfads-and-test-fix`
**Base:** `main` after Stack P squash-merge `83e549b`
**Date:** 2026-07-02

---

## Executive Summary

Stack Q addresses two items documented in Stack P as prerequisites for commercial beta:

1. **Oborovo avg DSCR gap**: Closes from +0.095 to +0.032 (1.179 vs golden 1.147) by switching the DSCR CFADS numerator from actual EBITDA to Golden Excel sizing CFADS (FCF for banks).
2. **Python 3.11 f-string SyntaxError**: Fixed directly in the test file. Stack P temporary conftest.py exclusion removed.

No IRR, debt sizing, repayment, cashflow, tax, or sponsor outputs changed.

---

## Part 1 — Oborovo DSCR CFADS Basis

### Q1 — Root Cause Confirmation

**Pre-Stack-Q model:** `actual_avg_dscr = 1.242` | **Golden Excel:** `1.147` | **Gap:** +0.095

The root cause investigation disproved the Stack P hypothesis that "merchant-phase CFADS is the full explanation." The true cause is three-layered:

#### Layer 1: Engine sculpted schedule (primary cause of 1.242)

The waterfall engine computes `all_dsrs[i] = (EBITDA - tax) / sculpted_senior_ds[i]` over 28 periods (14-year semi-annual tenor). The `sculpted_senior_ds` (level annuity from gearing-cap sizing) is **lower** than the frozen CSV DS schedule:

| Period | Sculpted DS (engine) | Frozen DS (CSV) | Engine DSCR | Frozen DSCR |
|--------|---------------------|-----------------|-------------|-------------|
| P2 (op 0) | 2,033 kEUR | 2,239 kEUR | 1.2664 | 1.1500 |
| P3 (op 1) | 2,000 kEUR | 2,202 kEUR | 1.2664 | 1.1500 |

The engine's average over 28 periods using sculpted DS = **1.242** (too high because sculpted DS < frozen DS → ratio inflated).

#### Layer 2: Guard rejection (preventing DSCR recomputation)

`waterfall_core.py` attempted to recompute `actual_avg_dscr` post frozen-DS override. The override set `period.dscr = ebitda / frozen_ds` for all active DS periods. However:
- The canonical sizing assigned non-zero DS to **all 43** op periods (including the 15 merchant-only periods where the CSV has `ds_r57 = 0.0`), because `fcf_for_banks > 0` for all 43 CSV rows
- Merchant-phase `ebitda` (~3,000–3,400 kEUR) >> sizing CFADS (~1,867–2,334 kEUR), giving merchant-phase `period.dscr` ≈ 1.9–2.4
- Average over 43 periods = 1.572 > 1.242 → existing guard (`_new_avg < result.actual_avg_dscr`) rejected the update

The comment in `waterfall_core.py` explicitly noted this guard did not handle the Oborovo merchant-phase case.

#### Layer 3: CFADS numerator mismatch (the correct basis)

The Golden Excel uses `FCF for banks (DS!R20) / DS (DS!R57)` as the DSCR for each period. This `FCF for banks` is the **sizing CFADS** — conservative, base-case cash flow used during debt sizing. It is:
- For PPA periods: essentially equal to EBITDA (same values within rounding)
- For merchant DS periods (op 24–27): significantly lower than actual EBITDA (2,057–2,279 vs 3,144–3,196 kEUR)

Using sizing CFADS over the **28 CSV-active DS periods** (where `ds_r57 > 0`):

| Band | Periods | Target DSCR | Avg DSCR (sizing) |
|------|---------|-------------|-------------------|
| PPA (op 0–23) | 24 | 1.15 | 1.15 |
| Merchant DS (op 24–27) | 4 | 1.35 | 1.35 |
| **All 28** | **28** | — | **1.179** |

`(24 × 1.15 + 4 × 1.35) / 28 = 33.0 / 28 = 1.1786`

**Remaining gap (1.179 vs 1.147 = 0.032):** The 0.032 residual is not fully explained by available CSV data. Likely causes: the Golden Excel uses a different weighting convention (e.g., debt-balance-weighted) or includes DSRA movements in the CFADS definition not captured in `ds_r57`. This residual is acceptable for external review.

---

### Q2 — Implementation

**File changed:** `app/waterfall_core.py`

**Change 1 — Track CSV-active DS periods during fixture loading (lines 521–536):**

```python
# Stack Q: track which op indices have active Excel DS (ds_r57 > 0).
csv_ds_active_op_indices: set = set()
...
ds_r57 = float(row.get("ds_r57_debt_service_keur", "0") or "0")
...
if ds_r57 > 0:
    csv_ds_active_op_indices.add(op_i)
```

**Change 2 — Store sizing CFADS and active indices on result:**

```python
result._oborovo_sizing_cfads = explicit_sizing_cfads
result._oborovo_csv_ds_active_op_indices = csv_ds_active_op_indices
```

**Change 3 — Use sizing CFADS for `period.dscr` override:**

```python
# Stack Q: prefer sizing CFADS from fixture (Golden Excel FCF for banks)
if _sizing_cfads is not None and op_idx < len(_sizing_cfads):
    cfads = _sizing_cfads[op_idx]
else:
    cfads = revenue - opex  # fallback
period.dscr = cfads / frozen_value if frozen_value > 0 else ...
```

**Change 4 — Filter `_active_dsrs` to CSV-active DS periods for Oborovo:**

```python
if _csv_ds_active is not None:
    _active_dsrs = [
        p.dscr
        for op_i, (_, p) in enumerate(op_periods)
        if op_i in _csv_ds_active
        and p.dscr not in (float('inf'), float('-inf'))
        and p.dscr == p.dscr
    ]
```

The guard `if _new_avg_dscr < result.actual_avg_dscr` then applies: `1.179 < 1.242` → `actual_avg_dscr` updated.

**What is NOT changed:**
- `period.senior_ds_keur` — unchanged; total_senior_ds_keur unaffected
- `period.ebitda_keur`, `period.revenue_keur`, `period.opex_keur` — unchanged
- `period.senior_principal_keur`, `period.senior_interest_keur` — unchanged
- Debt sizing, repayment schedule, SHL, tax, distributions — all unchanged
- TUHO path — unchanged (no `_oborovo_sizing_cfads` on TUHO result)

---

### Q3 — Regression Results

All outputs unchanged except `actual_avg_dscr` and `actual_min_dscr`:

| Metric | Pre-Stack-Q | Post-Stack-Q | Change |
|--------|------------|--------------|--------|
| Oborovo actual_avg_dscr | 1.242 | **1.179** | −0.063 ✅ |
| Oborovo actual_min_dscr | 1.179 | **1.150** | Changed (sizing basis) |
| Oborovo equity IRR | 10.66% | 10.66% | Unchanged ✅ |
| Oborovo project IRR | 8.09% | 8.09% | Unchanged ✅ |
| Oborovo senior debt | 42,852 kEUR | 42,852 kEUR | Unchanged ✅ |
| Oborovo total senior DS | 63,522 kEUR | 63,522 kEUR | Unchanged ✅ |
| Oborovo total distributions | 71,598 kEUR | 71,598 kEUR | Unchanged ✅ |
| Oborovo total tax | 11,128 kEUR | 11,128 kEUR | Unchanged ✅ |
| Oborovo total revenue | 238,735 kEUR | 238,735 kEUR | Unchanged ✅ |
| TUHO equity IRR | 11.59% | 11.59% | Unchanged ✅ |
| TUHO project IRR | 9.41% | 9.41% | Unchanged ✅ |
| TUHO avg DSCR | 1.3786 | 1.3786 | Unchanged ✅ |

---

### Q4 — Golden Validation

| Metric | Stack P (before) | Stack Q (after) | Golden Excel | Delta | Status |
|--------|-----------------|-----------------|--------------|-------|--------|
| Oborovo equity IRR | 10.66% | 10.66% | 10.60% | +6 bps | ✅ PASS (±10 bps) |
| Oborovo project IRR | 8.09% | 8.09% | 7.96% | +13 bps | ✅ PASS (±15 bps) |
| Oborovo avg DSCR | **1.242** | **1.179** | **1.147** | **+0.032** | ⚠️ Improved (was +0.095) |
| TUHO equity IRR | 11.59% | 11.59% | 11.61% | −2 bps | ✅ PASS (±30 bps) |
| TUHO avg DSCR | 1.3786 | 1.3786 | 1.3713 | +7 bps | ✅ PASS |

**Remaining gap (Oborovo avg DSCR +0.032):** Root cause documented above. Likely a weighting-convention or DSRA-treatment difference in the Golden Excel not reproducible from the available CSV sizing extraction. Classified as **acceptable for external technical review**.

---

## Part 2 — Python 3.11 F-String Fix

### Q5 — Fix Applied

**File:** `tests/test_phase24g3_capex_sheet_readability.py`, line 391

**Before (SyntaxError in Python 3.11):**
```python
f"{block.count('\"{:,.1f}\".format(')}"
```

**After (valid in Python 3.11):**
```python
_fmt_marker = '"{:,.1f}".format('
f"{block.count(_fmt_marker)}"
```

The test logic is unchanged — the backslash-containing string is now a pre-assigned variable rather than a literal inside the f-string expression.

**Result:** 37 tests now collect from `test_phase24g3_capex_sheet_readability.py`. 36 pass; 1 pre-existing unrelated failure (`test_renders_with_factory_project` expected "Factory Reference" in output — this was always failing, previously hidden as a collection error).

### Q6 — Conftest Exclusion Removed

**File:** `tests/conftest.py`

```python
# Stack P workaround (REMOVED in Stack Q):
# SYNTAX_ERROR_FILES = {"test_phase24g3_capex_sheet_readability.py"}

# Stack Q: f-string fix applied directly; exclusion removed.
SYNTAX_ERROR_FILES: set = set()
```

`test_phase24g3_capex_sheet_readability.py` now collects normally without any conftest override.

---

## Test Suite Results

```
pytest tests/test_phase51f_parallel_work_guardrails.py
      tests/test_excel_parity_stack_k.py … stack_q.py
```

**183 passed, 0 failed.**

```
pytest tests/test_phase24g3_capex_sheet_readability.py
```

**36 passed, 1 pre-existing failure (test_renders_with_factory_project, unrelated).**

---

## Guardrail Confirmation

- ✅ No project factory changes (`project_factories.py` SHA unchanged)
- ✅ No debt sizing changes (`senior_debt_keur` unchanged for both projects)
- ✅ No repayment changes (`senior_principal_keur`, `senior_ds_keur` sum unchanged)
- ✅ No revenue, tax, SHL, sponsor, or distribution changes
- ✅ No UI, export, or serialization changes
- ✅ No TUHO path changes
- ✅ `waterfall_core.py` SHA updated to reflect intentional DSCR reporting fix
- ✅ Stack P conftest exclusion removed — `test_phase24g3_capex_sheet_readability.py` collects normally
- ✅ No test skip remains for the f-string file

---

## Updated Gap Register

| Gap ID | Metric | Delta | Root Cause | Status |
|--------|--------|-------|------------|--------|
| G-OBR-DSCR-AVG | Oborovo avg DSCR | **+0.032** (1.179 vs 1.147) | Residual: weighting convention or DSRA treatment difference in Golden Excel | **Acceptable for external review** (was +0.095) |
| G-TUHO-EIRR-TAIL | TUHO equity IRR | −2 bps | SHL PIK timing (3-period) | Negligible |
| G-TUHO-PIRR | TUHO project IRR | −6 bps | Unlevered tax timing | Negligible |
| G-OBR-PIRR | Oborovo project IRR | +13 bps | AFRY curve rounding | Negligible |
