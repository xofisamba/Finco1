# Excel Parity Stack M — Equity IRR / SHL Timing Calibration

**Branch:** `excel-parity-stack-m-equity-irr-shl`
**Base:** `main` (after Stack L squash-merge `3bb014c2`)
**Golden Excel reference:** TUHO `20260330_TUHO_BP_2.xlsm` — Golden equity IRR: 11.61%

---

## M1 — Root Cause Analysis

### Configuration

TUHO uses:
- `equity_irr_method = "shl_plus_dividends"` (line 418, `app/project_factories.py`)
- `shl_repayment_method = "pik_then_sweep"`
- `shl_amount = 29,135 kEUR`, `share_capital = 500 kEUR`
- `financial_close = 2029-07-01`

**Equity CF definition (`shl_plus_dividends`):**
- Initial outflow: `−(shl_amount + share_capital) = −29,635 kEUR` at t0
- While SHL outstanding: `equity_cf = shi` (cash SHL interest swept per period)
- After SHL repaid: `equity_cf = dist` (distributions to equity)

**XIRR:** Custom Newton-Raphson in `domain/returns/xirr.py`, 365-day year fractions — consistent with Excel XIRR.

---

### Root Cause A — Disbursement Period Zero Equity CF (PRIMARY, ~25 bps)

**Location:** `domain/waterfall/waterfall_engine.py` line 803 and lines 863–867.

The first operating period is flagged as the "disbursement period":
```python
is_shl_disbursement_period = (op_period_counter == 1 and shl_repayment_method == "pik_then_sweep")
```

During this period:
```python
elif is_shl_disbursement_period:
    shi = 0.0; shp = 0.0; shl_pik = 0.0
    # shl_balance stays unchanged
```

`shi = 0` causes `equity_cf_for_period = shi = 0` for P2 (2030-06-30).

**Excel golden behavior:**
Excel P1 (2030-06-30) equity cash flow = **953.8 kEUR** — the FCF available for SHL service:
`EBITDA − Senior DS − Cash Tax ≈ _cf_for_shl`.

**Root cause:** The `shl_plus_dividends` equity CF formula uses `shi` (swept cash interest),
which is zero during the disbursement period. The FCF that IS available (`_cf_for_shl = 953.8 kEUR`)
is not captured in the equity CF stream, even though Excel records it.

---

### Root Cause B — SHL Principal Repayment Timing (SECONDARY, ~21 bps, Stack N scope)

- Model first SHL principal repayment: P30 (2044-06-30)
- Excel first SHL principal repayment: ~P24 (2041-ish, per gap register)
- Delta: ~6 semiannual periods

During SHL-outstanding periods, `equity_cf = shi ≈ 1,000 kEUR/period`.
Once SHL repaid, `equity_cf = dist ≈ 6,000–8,000 kEUR/period`.
6 extra periods in the low-CF regime suppresses IRR by ~21 bps.

Root Cause B involves the `pik_then_sweep` waterfall domain logic (when SHL principal
repayment begins) — outside Stack M scope. Recommended: `excel-parity-stack-n-shl-principal`.

---

### Root Cause C — SHL Balance Accumulation (informational)

SHL balance grows in PIK mode because `_cf_for_shl < shl_balance × shl_rate` for most early periods. This is correct behavior for a PIK instrument. The balance grows to ~34,611 kEUR before principal repayment begins. No change required.

---

### Period-by-Period Evidence (first 5 operating periods)

| Period | Date | Model equity CF | Excel equity CF | Delta |
|--------|------|-----------------|-----------------|-------|
| P2 | 2030-06-30 | **0.0** kEUR | **953.8** kEUR | −953.8 |
| P3 | 2030-12-31 | 1,099.0 | ~969.6 | +129.4 |
| P4 | 2031-06-30 | 1,093.5 | ~966.1 | +127.4 |
| P5 | 2031-12-31 | 1,111.6 | ~983.0 | +128.6 |
| P6 | 2032-06-30 | 1,109.3 | ~980.8 | +128.5 |

The P2 miss (−953.8 kEUR one period after t0) dominates IRR impact.
P3+ model SHI is slightly higher than Excel (~130 kEUR/period extra) which partially offsets.

---

## M2 — Implementation

**File changed:** `domain/waterfall/waterfall_engine.py`

**Change location:** Per-period equity CF accumulation block (~line 1160–1168).

**Before:**
```python
elif equity_irr_method == "shl_plus_dividends":
    if shl_balance > 0:
        equity_cf_for_period = shi  # Net interest ONLY - no principal in equity CF
    else:
        equity_cf_for_period = dist
```

**After:**
```python
elif equity_irr_method == "shl_plus_dividends":
    if shl_balance > 0:
        # Disbursement period: shi=0 by design (SHL just drawn, no interest sweep).
        # Excel records FCF-available (_cf_for_shl) as the P1 equity cash flow.
        # Use _cf_for_shl to match Excel golden methodology for parity.
        if is_shl_disbursement_period:
            equity_cf_for_period = max(0.0, _cf_for_shl)
        else:
            equity_cf_for_period = shi  # Net interest ONLY - no principal in equity CF
    else:
        equity_cf_for_period = dist
```

**What is NOT changed:**
- `_cf_for_shl` computation — unchanged (already computed before equity CF section)
- `shi`, `shp`, `shl_pik`, `shl_balance` for the disbursement period — unchanged
- The disbursement period exemption itself — still applies to SHL accounting
- All per-period DSCR, CFADS, tax, distributions — unchanged
- All debt sizing and sculpting — unchanged
- Project IRR — unchanged
- Sponsor engine — unchanged
- Oborovo / other projects — unchanged (guard: only `shl_plus_dividends` + `is_shl_disbursement_period`)

---

## M3 — Regression Results

```
pytest tests/test_phase51f_parallel_work_guardrails.py
      tests/test_excel_parity_stack_k.py
      tests/test_excel_parity_stack_l.py
      tests/test_excel_parity_stack_m.py
      -q
```

**Result:** 98 passed, 0 failed.

| Output | Pre-Stack-M | Post-Stack-M | Change |
|--------|------------|--------------|--------|
| TUHO equity IRR | 11.15% | **11.40%** | +25 bps ✓ |
| TUHO project IRR | 9.41% | 9.41% | unchanged ✓ |
| TUHO avg DSCR | 1.379 | 1.379 | unchanged ✓ |
| TUHO total senior DS | 65,826 kEUR | 65,826 kEUR | unchanged ✓ |
| TUHO total tax | unchanged | unchanged | ✓ |
| Oborovo equity IRR | 6.24% | 6.24% | unchanged ✓ |
| Oborovo project IRR | 8.09% | 8.09% | unchanged ✓ |

---

## M4 — Golden Validation

### TUHO

| Metric | Pre-Stack-M | Post-Stack-M | Golden Excel | Remaining Delta | Status |
|--------|------------|--------------|--------------|-----------------|--------|
| Equity IRR | 11.15% | **11.40%** | 11.61% | **−21 bps** | Improved (±30 bps) |
| Project IRR | 9.41% | 9.41% | 9.47% | −6 bps | PASS (±10 bps) |

Stack M closes 25 of 46 bps (54%). Remaining 21 bps from SHL principal timing (Root Cause B).

### Oborovo

| Metric | Pre-Stack-M | Post-Stack-M | Status |
|--------|------------|--------------|--------|
| Equity IRR | 6.24% | 6.24% | Unchanged — Oborovo DSCR/IRR gaps are merchant-curve scope |

---

## Remaining Gaps

| Gap ID | Metric | Delta | Root Cause | Recommended PR |
|--------|--------|-------|------------|----------------|
| G-EIRR-PRINCIPAL | TUHO equity IRR | −21 bps | SHL principal repayment starts P30 (model) vs P24 (Excel) — 6 extra periods at SHI~1,000 vs dist~7,000 | `excel-parity-stack-n-shl-principal` |
| G-OBR-EIRR | Oborovo equity IRR | −436 bps | Merchant price curve mismatch (factory SHA-locked) | `excel-parity-stack-o-oborovo-merchant-curve` |

---

## Guardrail Confirmation

- No debt sizing changes
- No DSCR changes
- No project cash-flow changes (EBITDA, revenue, OPEX, CAPEX unchanged)
- No tax changes
- No sponsor engine changes
- No distribution logic changes
- No sculpting changes
- No merchant curve changes
- No UI / serialization / export changes
- Only: `equity_cf_for_period` for the single disbursement period in `shl_plus_dividends` method
