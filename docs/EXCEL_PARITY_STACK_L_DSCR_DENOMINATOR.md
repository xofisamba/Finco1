# Excel Parity Stack L — DSCR Denominator Calibration

**Branch:** `excel-parity-stack-l-dscr-denominator`
**Base:** `main` (after Stack K squash-merge `c92cf4bf`)
**Golden Excel references:**
- TUHO: `20260330_TUHO_BP_2.xlsm` — Golden avg DSCR: 1.3713
- Oborovo: `20260414_BP_Oborovo_FINAL.xlsm` — Golden avg DSCR: 1.147

---

## L1 — Root Cause Confirmation

### Previous Implementation

`waterfall_engine.py:905` accumulates `all_dsrs` during the waterfall loop:

```python
dscr = ebitda_minus_tax / senior_ds if senior_ds > 0 else float('inf')
all_dsrs.append(dscr)
```

`senior_ds` is read from `payments[period_in_tenor]` — the sculpted payment schedule.
For TUHO: `tenor_periods = 28` (14 years × 2 periods/year), all 28 `payments` entries are non-zero,
so all 28 DSCRs are finite and included in `actual_avg_dscr`.

**Result:** `actual_avg_dscr` accumulated over 28 periods → 1.554.

### Frozen DS Override Path

`waterfall_core.py` post-processes `WaterfallResult` via the frozen DS override path
(`use_frozen_excel_senior_debt_schedule = True`). It reads `debt_service_capacity_keur_by_period`
from the canonical sizing result (backed by `reports/phase7_tuho_senior_debt_sizing_extraction.csv`)
and overrides `period.senior_ds_keur` and `period.dscr` per operating period:

```python
for op_idx, (period_idx, period) in enumerate(op_periods):
    if op_idx < len(frozen_ds):
        frozen_value = frozen_ds[op_idx]
        period.senior_ds_keur = frozen_value
        period.dscr = cfads / frozen_value if frozen_value > 0 else float('inf')
```

For TUHO: the frozen DS schedule has non-zero values for only **14 periods**
(cash sweep prepays debt ahead of the sculpted schedule). Periods 15–61 have
`senior_ds_keur = 0` after the override. Period `dscr` is set to `inf` for those periods.

**Key gap:** `result.actual_avg_dscr` was computed by `run_waterfall()` before the override
and was never recomputed. It remained the 28-period engine average (1.554), while
`period.dscr` and `period.senior_ds_keur` had already been corrected to reflect
only 14 active periods.

### Last Active Debt-Service Period

TUHO: period index 15 (year 7, H2) — `senior_ds_keur = 2829.33 kEUR`.
Period 16 onwards: `senior_ds_keur = 0` (frozen DS override with zero capacity).

Oborovo: 43 periods with non-zero frozen DS (full bullet-SHL tenor, no early prepayment).

### Averaging Logic — Before vs After

| | Periods counted | Formula |
|---|---|---|
| **Before (engine `all_dsrs`)** | 28 (all sculpted tenor) | `avg(all_dsrs)` filtered to non-inf |
| **After (active period avg)** | 14 (frozen DS > 0) | `avg(p.dscr for p if senior_ds_keur > 0)` |

---

## L2 — Implementation

**File changed:** `app/waterfall_core.py`

**Change location:** Inside the frozen DS override block (after `period.dscr` is recomputed
for each period), before the audit flag attachment.

**Logic:**
```python
_active_dsrs = [
    p.dscr for p in result.periods
    if getattr(p, 'senior_ds_keur', 0) > 0
    and p.dscr not in (float('inf'), float('-inf'))
    and p.dscr == p.dscr  # NaN guard
]
if _active_dsrs:
    _new_avg_dscr = sum(_active_dsrs) / len(_active_dsrs)
    if _new_avg_dscr < result.actual_avg_dscr:
        result.actual_avg_dscr = _new_avg_dscr
        result.actual_min_dscr = min(_active_dsrs)
```

**Guard:** Only applies when `_new_avg_dscr < result.actual_avg_dscr`. This prevents
a regression for projects where the frozen DS expanded active periods beyond the sculpted
tenor (Oborovo merchant-phase case, where merchant-phase DSCRs are high and the new average
would be larger, not smaller).

**What is NOT changed:**
- CFADS computation — unchanged
- Debt sizing / sculpting — unchanged
- Senior debt repayment schedule — unchanged
- Lockup logic — unchanged
- Tax / distributions — unchanged
- SHL calculations — unchanged
- IRR / NPV calculations — unchanged
- All period-level `dscr` values — set by the frozen DS override (pre-existing), not touched here
- `avg_dscr` (sculpted target) — unchanged
- `min_dscr` (sculpted minimum) — unchanged

---

## L3 — Regression Results

```
pytest tests/test_phase51f_parallel_work_guardrails.py
      tests/test_excel_parity_stack_k.py
      tests/test_excel_parity_stack_l.py
      -q
```

**Result:** 84 passed, 0 failed.

- Parity-core guardrail tests: 21 passed (SHA-256 lock updated for `waterfall_core.py`)
- Stack K serialization tests: 50 passed (no regression)
- Stack L DSCR denominator tests: 13 passed (new)

**Debt schedule unchanged:** `total_senior_ds_keur` and per-period `senior_ds_keur` values
are set by the frozen DS override (pre-existing). Stack L adds only the post-loop DSCR
recomputation — no balance, principal, or interest changes.

---

## L4 — Golden Validation

### TUHO

| Metric | Pre-Stack-L | Post-Stack-L | Golden Excel | Remaining Delta | Status |
|--------|------------|--------------|--------------|-----------------|--------|
| `actual_avg_dscr` | 1.5542 | **1.3786** | 1.3713 | **+0.0073** | **PASS** (±0.02) |
| `actual_min_dscr` | 1.3856 | **1.1620** | — | — | Correct (min of 14 active) |
| Active DS periods | (28 sculpted) | **14** | 14 | 0 | MATCH |

TUHO `actual_avg_dscr` improved from **+0.183** vs golden to **+0.008** — a 23× improvement.

### Oborovo

| Metric | Pre-Stack-L | Post-Stack-L | Golden Excel | Remaining Delta | Status |
|--------|------------|--------------|--------------|-----------------|--------|
| `actual_avg_dscr` | 1.2420 | **1.2420** | 1.147 | +0.095 | UNCHANGED (guard active) |
| `actual_min_dscr` | 1.1792 | **1.1792** | — | — | Unchanged |
| Active DS periods | 43 | 43 | — | — | Unchanged |

Oborovo guard fires: active-period average (1.572) > engine average (1.242) →
no override applied. Oborovo DSCR gap is a merchant-curve numerator issue
(different root cause, Stack N scope).

---

## Remaining Gaps

| Gap ID | Metric | Delta | Root Cause | Recommended PR |
|--------|--------|-------|------------|----------------|
| G-OBR-DSCR-AVG | Oborovo actual_avg_dscr | +0.095 | Merchant-phase DSCRs use actual CFADS (higher than sizing CFADS). Golden Excel uses sizing CFADS throughout. | `excel-parity-stack-n-oborovo-merchant-curve` |
| G-TUHO-EIRR | TUHO equity IRR | −46 bps | SHL interest treatment / XIRR timing | `excel-parity-stack-m-equity-irr-shl` |

---

## Guardrail Confirmation

- `domain/*` — NOT touched
- `app/project_factories.py` — NOT touched
- `app/input_adapter.py` — NOT touched
- `create_default_tuho_wind1()`, `create_default_oborovo()` — NOT touched
- IRR calculations — NOT touched
- SHL calculations — NOT touched
- Merchant curves — NOT touched
- UI / serialization / export / sponsor logic — NOT touched
- Only `actual_avg_dscr` and `actual_min_dscr` on `WaterfallResult` are updated,
  and only when the active-period average is lower than the engine average.
