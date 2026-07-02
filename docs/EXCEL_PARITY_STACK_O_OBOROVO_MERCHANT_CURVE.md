# Excel Parity Stack O — Oborovo Merchant Curve Calibration

**Branch:** `excel-parity-stack-o-oborovo-merchant-curve`
**Base:** `main` (after Stack N squash-merge `cbbefd83`)
**Golden Excel reference:** Oborovo `20260414_BP_Oborovo_FINAL.xlsm` — Golden equity IRR: 10.60%

---

## O1 — Root Cause Analysis

### Merchant Curve Status (Pre-existing fix, PASS)

The AFRY Central Q1 2026 merchant price curve was calibrated in a prior phase.
The current `create_default_oborovo()` factory already embeds the correct AFRY values:

| Period | Values (EUR/MWh, nominal) |
|--------|--------------------------|
| Y1–Y12 | 0 (unused during PPA) |
| Y13–Y21 | 73.50, 75.12, 75.83, 76.04, 74.11, 75.79, 77.48, 79.16, 80.86 |
| Y22–Y30 | 82.57, 84.78, 86.51, 88.22, 90.47, 92.20, 93.63, 95.01, 95.89, 97.22 |

**Evidence that merchant curve is calibrated:**

| Metric | Pre-Stack-O | Golden Excel | Delta | Status |
|--------|------------|--------------|-------|--------|
| Project IRR | 8.09% | 7.96% | +13 bps | **PASS** (±15 bps) |
| Total Revenue | 238,735 kEUR | — | — | calibrated |

Project IRR is financing-independent (unlevered). Since it matches golden within ±15 bps, the EBITDA / merchant revenue is correctly calibrated.

---

### Root Cause: Wrong Equity IRR Method (PRIMARY, −436 bps)

**Location:** `app/project_factories.py`, `create_default_oborovo()`, line ~197.

**Pre-Stack-O:**
```python
equity_irr_method="combined"
```

**What "combined" computes:**
- Equity investment = `sculpt_capex - senior_debt` = 57,973 − 42,852 = **15,121 kEUR** (includes SHL amount)
- Equity CFs = distributions only (starting at P41, year 21, after SHL bullet repaid at Y20)

**Problem:** For 20 years (Y1–Y20), equity investor receives SHL interest (~580–600 kEUR/period = ~1,160 kEUR/year) but these are NOT counted in the equity IRR stream under `combined`. The model ignores 20 years of SHL cash flows to the investor.

**Golden Excel methodology:**
The Golden Excel computes equity IRR from the perspective of the SHL+share_capital investor:
- Investment at t0 = SHL + share capital = 13,547.2 + 500 = **14,047.2 kEUR**
- CFs while SHL outstanding = SHL cash interest (`shi`) each period
- CFs after SHL repaid = distributions (`dist`)

This is exactly the `shl_plus_dividends` method.

**Confirmation:**

| Method | Equity IRR | vs Golden 10.60% |
|--------|-----------|-----------------|
| `combined` (pre-Stack-O) | 6.24% | −436 bps ✗ |
| `shl_plus_dividends` (Stack O) | **10.66%** | **+6 bps** ✓ |

---

### DSCR Gap (Remaining, not addressed in Stack O)

Oborovo avg DSCR = 1.242 vs golden 1.147 (+0.095).

Root cause (from Stack L investigation): Merchant-phase DSCR numerator uses actual CFADS from the model, while the Golden Excel uses sizing CFADS throughout. Since Oborovo uses `gearing_cap` debt sizing (not DSCR sculpting), the CFADS in merchant periods is computed from actual merchant revenues (slightly different basis from the Excel sizing model's CFADS).

This is a DSCR numerator methodology gap (not a merchant price gap). It is NOT addressed in Stack O. Recommended: `excel-parity-stack-p-oborovo-dscr-cfads`.

---

## O2 — Implementation

**File changed:** `app/project_factories.py`

**Change:**

```python
# Before
equity_irr_method="combined",  # Oborovo uses combined SHL+equity method

# After
equity_irr_method="shl_plus_dividends",  # Stack O: Golden Excel equity IRR = SHL interest while SHL outstanding + dividends after
```

**What is NOT changed:**
- Merchant price curve — already calibrated (AFRY Central), unchanged
- PPA tariff, escalation, term — unchanged
- CO2 revenue — unchanged
- Debt sizing, sculpting — unchanged
- Senior debt schedule — unchanged
- SHL amount, rate, tenor — unchanged
- Tax engine — unchanged
- Distribution engine — unchanged
- Sponsor engine — unchanged
- DSCR methodology — unchanged
- Waterfall engine — unchanged
- UI, serialization, export — unchanged
- TUHO factory — unchanged

**SHA-256 update in `tests/test_phase51f_parallel_work_guardrails.py`:**
Updated `PARITY_CORE_FILES["app/project_factories.py"]` from Stack J hash to Stack O hash.

---

## O3 — Regression Results

```
pytest tests/test_phase51f_parallel_work_guardrails.py
      tests/test_excel_parity_stack_k.py
      tests/test_excel_parity_stack_l.py
      tests/test_excel_parity_stack_m.py
      tests/test_excel_parity_stack_n.py
      tests/test_excel_parity_stack_o.py
      -q
```

**Result:** 124 passed, 0 failed.

| Output | Pre-Stack-O | Post-Stack-O | Change |
|--------|------------|--------------|--------|
| Oborovo equity IRR | 6.24% | **10.66%** | +442 bps ✓ |
| Oborovo project IRR | 8.09% | 8.09% | unchanged ✓ |
| Oborovo avg DSCR | 1.242 | 1.242 | unchanged ✓ |
| Oborovo total revenue | 238,735 kEUR | 238,735 kEUR | unchanged ✓ |
| Oborovo total senior DS | 63,522 kEUR | 63,522 kEUR | unchanged ✓ |
| TUHO equity IRR | 11.59% | 11.59% | unchanged ✓ |
| TUHO project IRR | 9.41% | 9.41% | unchanged ✓ |
| TUHO avg DSCR | 1.3786 | 1.3786 | unchanged ✓ |

---

## O4 — Golden Validation

### TUHO (no regression)

| Metric | Post-Stack-O | Golden Excel | Delta | Status |
|--------|-------------|--------------|-------|--------|
| Equity IRR | 11.59% | 11.61% | −2 bps | **PASS** (±10 bps) |
| Project IRR | 9.41% | 9.47% | −6 bps | **PASS** (±10 bps) |
| Avg DSCR | 1.3786 | 1.3713 | +7 bps | **PASS** (±0.02) |

### Oborovo

| Metric | Pre-Stack-O | Post-Stack-O | Golden Excel | Delta | Status |
|--------|------------|--------------|--------------|-------|--------|
| Equity IRR | 6.24% | **10.66%** | 10.60% | **+6 bps** | **PASS** (±10 bps) |
| Project IRR | 8.09% | 8.09% | 7.96% | +13 bps | **PASS** (±15 bps) |
| Avg DSCR | 1.242 | 1.242 | 1.147 | +0.095 | See gap register |

---

## Remaining Gaps

| Gap ID | Metric | Delta | Root Cause | Recommended PR |
|--------|--------|-------|------------|----------------|
| G-OBR-DSCR-AVG | Oborovo actual_avg_dscr | +0.095 | Merchant-phase DSCR uses actual CFADS; Golden Excel uses sizing CFADS. Gearing-cap sizing creates different CFADS basis from DSCR-sculpted models. | `excel-parity-stack-p-oborovo-dscr-cfads` |

---

## Guardrail Confirmation

- No waterfall methodology changes
- No debt sizing changes
- No SHL engine changes
- No tax changes
- No sponsor engine changes
- No distribution logic changes
- No merchant curve changes (already calibrated)
- No UI / serialization / export changes
- No TUHO changes
- Only: `equity_irr_method` input in `create_default_oborovo()` changed from `"combined"` to `"shl_plus_dividends"`
