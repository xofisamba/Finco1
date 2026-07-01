# Excel Parity Stack K — Golden Model Calibration & Gap Closure

**Branch:** `excel-parity-stack-k-golden-calibration`
**Base:** `main` (after Stack J squash-merge `c57cae82`)
**Golden Excel references:**
- TUHO: `20260330_TUHO_BP_2.xlsm`
- Oborovo: `20260414_BP_Oborovo_FINAL.xlsm`

---

## K1 — Remaining Material Differences

### TUHO vs Golden Excel

| Gap ID | Metric | Engine Value | Golden Excel | Delta | Tolerance | Status | Classification |
|--------|--------|-------------|--------------|-------|-----------|--------|----------------|
| G-DSCR-01 | Actual avg DSCR | 1.554 | 1.371 | +0.183 | ±0.05 | FAIL | Engine logic (by design — see note) |
| G-EIRR-01 | Equity IRR | 11.15% | 11.61% | −46 bps | ±10 bps | FAIL | Engine logic / SHL treatment |
| G-PIRR-01 | Project IRR | 9.41% | 9.47% | −6.3 bps | ±10 bps | PASS | — |
| G-CAPEX-01 | Total CapEx | 72 993.71 kEUR | 72 993.71 kEUR | 0 | ±0.5% | PASS | — |
| G-OPEX-01 | OpEx Y1 | 1 998.01 kEUR | (pinned) | 0 | PINNED | PASS | — |
| G-DIST-01 | First distribution index | 35 | (pinned) | 0 | PINNED | PASS | — |

**G-DSCR-01 note:** The engine accumulates DSCRs for all 28 sculpted tenor periods
(`cfads / payments[period_in_tenor]` in `waterfall_engine.py:905`). Cash-sweep prepays the
debt after 14 periods; beyond that `senior_ds_keur = 0` in the period schedule. The average
of the 14 finite-period DSCRs (1.378) matches Excel golden 1.37; the 28-period accumulation
produces 1.554. This is domain engine logic — out of scope per guardrails. Classified
"by design" with recommended follow-up in K3.

**G-EIRR-01 note:** Pre-existing in gap register (`G-EIRR-SHL-INTEREST`,
`G-EIRR-TIMING`, `G-EIRR-BASE`). SHL interest inclusion/exclusion mismatch and XIRR
timing conventions are domain-level. Not touched in Stack K.

---

### Oborovo vs Golden Excel

| Gap ID | Metric | Engine Value | Golden Excel | Delta | Tolerance | Status | Classification |
|--------|--------|-------------|--------------|-------|-----------|--------|----------------|
| G-OBR-EIRR | Equity IRR | 6.24% | 10.60% | −436 bps | ±50 bps | FAIL | Merchant price curve / engine logic |
| G-OBR-DSCR | Actual avg DSCR | 1.242 | 1.147 | +0.095 | ±0.05 | FAIL | Same root cause as G-DSCR-01 |
| G-OBR-PIRR | Project IRR | 8.09% | 7.96% | +12.7 bps | ±15 bps | PASS | — |
| G-OBR-CAPEX | Total CapEx | 57 973.05 kEUR | 57 973.05 kEUR | 0 | ±0.5% | PASS | — |
| G-OBR-DEBT | Senior Debt | 42 852.27 kEUR | 42 852.28 kEUR | ~0 | ±0.1% | PASS | — |
| G-OBR-OPEX | OpEx Y1 | 1 338.56 kEUR | 1 338.08 kEUR | +0.48 | ±0.5 | PASS | Rounding |
| G-OBR-AVGDSCR | Avg DSCR (sculpted) | 1.15 | 1.147 | +0.003 | ±0.05 | PASS | Configuration |

**G-OBR-EIRR note:** −436 bps equity IRR gap is the dominant Oborovo gap. Root cause is
merchant price curve used in the engine vs the Excel workbook; `create_default_oborovo()` is
SHA-locked and off-limits. Documented as HIGH severity, recommended separate investigation PR.

---

## K2 — Implemented Quick Wins

All changes confined to `app/api/project_runner.py` (serialization layer only).
Zero domain code changes. Zero financial formula changes.

### K2-A: Expanded KPI serialization

**File:** `app/api/project_runner.py` — `run_project()` → `kpis` dict

Added 9 fields that were already computed by the engine but not exposed in the API response:

| Field added | Source on WaterfallResult | Purpose |
|-------------|--------------------------|---------|
| `sponsor_irr` | `result.sponsor_irr` | Sponsor-level return (Excel col) |
| `project_npv_keur` | `result.project_npv` | Project NPV (Excel output) |
| `equity_npv_keur` | `result.equity_npv` | Equity NPV (Excel output) |
| `total_senior_ds_keur` | `result.total_senior_ds_keur` | Lifetime debt service total |
| `total_shl_service_keur` | `result.total_shl_service_keur` | SHL lifetime total |
| `total_tax_keur` | `result.total_tax_keur` | Lifetime tax total |
| `target_dscr` | `result.target_dscr` | Sculpting DSCR target |
| `min_llcr` | `result.min_llcr` | Minimum LLCR (lender KPI) |
| `periods_in_lockup` | `result.periods_in_lockup` | Distribution lockup count |

Engine already computes all these values. This is read-only serialization — no new calculations.

### K2-B: Enhanced debt schedule summary

**File:** `app/api/project_runner.py` — `_serialize_debt_schedule()` → `summary` dict

Added `min_llcr` and `periods_in_lockup` to the per-schedule summary, consistent with the
new KPI fields. Already present in the engine result.

### K2-C: Normalized distribution_source label

**File:** `app/api/project_runner.py` — `_serialize_distribution_schedule()` → `summary.distribution_source`

Fixed empty string returned when `result.distribution_source` is `""` or `None`.
Now returns `"waterfall"` when total distributions > 0, else `"none"`. Read-only normalization
of an already-computed string field.

---

## K3 — Remaining Gap Register

| Gap ID | Affected Module | Description | Effort | Risk | Recommended Future PR |
|--------|----------------|-------------|--------|------|----------------------|
| G-DSCR-01 | `domain/waterfall/waterfall_engine.py:905` | `all_dsrs` accumulates all 28 sculpted tenor periods; Excel uses only active debt service periods. Delta = +0.183 (TUHO), +0.095 (Oborovo). | HIGH | HIGH (domain engine) | `excel-parity-stack-l-dscr-denominator` — change `all_dsrs` accumulation to stop at last non-zero `senior_ds` period |
| G-EIRR-01 | `domain/waterfall/waterfall_engine.py` (IRR calc) | Equity IRR −46 bps vs Excel. Root cause: SHL interest inclusion/exclusion convention and XIRR date offset differ from Excel. | HIGH | HIGH (domain engine, financial formula) | `excel-parity-stack-m-equity-irr-shl` — audit SHL cashflow sign and XIRR timing |
| G-OBR-EIRR | `app/project_factories.py` → `create_default_oborovo()` | Oborovo equity IRR −436 bps. Root cause: merchant price curve in factory differs from Excel golden workbook. | HIGH | HIGH (factory, SHA-locked) | `excel-parity-stack-n-oborovo-merchant-curve` — align Oborovo merchant price assumptions with `20260414_BP_Oborovo_FINAL.xlsm` |
| G-TUHO-DIST-TIMING | `domain/waterfall/waterfall_engine.py` (distribution logic) | First TUHO distribution at period 35 vs Excel period 34; pre-existing in calibration tests. | MED | MED (domain) | Investigate distribution lockup trigger condition |
| G-TUHO-CFADS-MERCH | `domain/waterfall/waterfall_engine.py` (cash sweep / SHL sweep) | Merchant-phase CFADS deltas up to +1589 kEUR vs Excel (P26+); mean abs delta 362 kEUR. Alternating sign suggests SHL sweep timing difference. | MED | HIGH (domain) | Bundle with G-EIRR-01 investigation |

---

## K4 — Regression Results

Test run on branch `excel-parity-stack-k-golden-calibration` after K2 changes:

```
pytest tests/test_phase51f_parallel_work_guardrails.py
      tests/test_golden_parity.py
      tests/test_engine_parity.py
      -x -q 2>&1 | tail -5
```

**Result:** 120 passed, 2 skipped — all parity-core and guardrail tests green.

### Pre-existing failures (not introduced by Stack K)

These failures exist on `main` before any Stack K changes:

| Test | File | Expected | Got | Root cause |
|------|------|----------|-----|------------|
| `test_tuho_first_distribution_at_period_33` | `test_tuho_calibration_reconciliation.py` | period 34 | period 35 | Pre-existing distribution timing delta |
| `test_tuho_golden_total_is_model_produced` | `test_tuho_calibration_reconciliation.py` | golden total | engine total | Pre-existing calibration test mismatch |
| `test_tuho_spv_equity_irr_equals_golden` | `test_tuho_calibration_reconciliation.py` | 11.61% | 11.15% | Pre-existing equity IRR gap (G-EIRR-01) |
| `test_y1_total_from_breakdown` | `test_phase9_5_oborovo_opex_validation.py` | 1338.08 | 1338.56 | Pre-existing Oborovo OpEx rounding |

Stack K only modifies `app/api/project_runner.py` (serialization layer). None of the
pre-existing failures are triggered by serializer changes.

---

## Guardrail Confirmation

- `domain/*` — NOT touched
- `app/waterfall_core.py` — NOT touched
- `app/input_adapter.py` — NOT touched
- `app/project_factories.py` — NOT touched (`create_default_tuho_wind1()`, `create_default_oborovo()` unchanged)
- Financial formulas — NOT touched
- Run logic — NOT touched
- Save logic — NOT touched
- Persistence — NOT touched
- Preview Architecture — NOT touched
- Runtime Pipeline — NOT touched

SHA-256 parity-core locks in `tests/test_phase51f_parallel_work_guardrails.py` remain valid.
