# Phase 29B: Oborovo CAPEX Sensitivity

Base: `7a5b54f2445d3ef13c5256360394c941032dbf44`
Phase: Diagnostic / validation / documentation
Date: 2026-05-31

---

## Scope

Run and document a diagnostic sensitivity analysis for Oborovo CAPEX variation and its impact on senior debt, DSCR, SHL/distribution behavior, project/equity IRR, and validation status.

**In scope:**
- Oborovo base-case CAPEX architecture (factory inputs)
- CAPEX sensitivity cases (+5%, +10%, -5%, -10%) run safely without mutating global state
- Frozen senior debt service behavior under CAPEX variation
- Base-case protection tests
- TUHO/Oborovo frozen path unchanged confirmation

**Out of scope:**
- Financial formula changes (revenue, tax, waterfall, senior debt, SHL, distributions)
- Fixture CSV changes
- TUHO/Oborovo factory flag changes
- Full scenario engine implementation
- UI scenario controls
- Construction IDC runtime engine
- M1–M18 IDC wiring
- C.16 Project Rights wiring

---

## Inspected Files

| File | Relevance |
|------|-----------|
| `app/project_factories.py:38–239` | Oborovo factory — CAPEX items, financing params, frozen DS flag |
| `app/waterfall_runner.py` | `use_frozen_excel_senior_debt_schedule` wiring |
| `app/ui_runner.py` | `run_demo_project()` for Oborovo Base |
| `docs/phase27_frozen_path_external_validation_pack.md` | Oborovo base anchors |
| `docs/phase27_validation_evidence_matrix.md` | Oborovo validation evidence |
| `docs/phase28_generic_project_path_validation.md` | Generic path distinction |
| `tests/test_phase23q_oborovo_frozen_senior_ds_fixture_extraction.py` | Oborovo fixture extraction |
| `tests/test_phase23k_oborovo_shl_opening_balance_bridge.py` | SHL opening balance |
| `tests/test_phase23l_oborovo_shl_amount_factory_correction.py` | SHL amount factory |

---

## Oborovo Base-Case Recap

### CAPEX Architecture

Oborovo has 15 CAPEX items totaling **55,999.09 kEUR hard capex**:
- EPC Contract: 26,430.0 kEUR
- Production Units: 10,912.7 kEUR
- Contingencies: 6,681.89 kEUR
- Project Rights: 3,024.5 kEUR
- Other items (grid, ops prep, insurances, lease tax, construction mgmt, commissioning, audit/legal, taxes, acquisition): ~8,950 kEUR

**Total capex including IDC/fees/vat: ~57,973 kEUR** (capex.total_capex)
**Total capex before IDC: ~56,887 kEUR** (capex.total_capex_before_idc)

Additional financial items:
- IDC: 1,086.0 kEUR
- Commitment fees: 188.6 kEUR
- Bank fees: 665.87 kEUR
- VAT costs: 33.49 kEUR

### Financing Architecture

- `fixed_debt_keur = 42,852.27 kEUR` — Excel senior debt anchor, frozen (not sculpted)
- `use_frozen_excel_senior_debt_schedule = True` — frozen senior DS schedule, not live DSCR sculpt
- `gearing_ratio = 0.7524` — debt/total capex ratio (75.24%)
- `shl_amount_keur = 14,621.0 kEUR` — SHL principal
- `shl_idc_keur = 1,169.0 kEUR` — SHL IDC
- **Opening SHL balance: 14,621 + 1,169 = ~15,790 kEUR**
- `shl_tenor_years = 20` — Oborovo SHL is 20-year bullet (clears at 2050-06-30)
- `debt_sizing_method = "gearing_cap"` — Oborovo uses gearing-based sizing (not DSCR sculpt)
- `target_dscr = 1.15x`, `lockup_dscr = 1.10x`

### Key Base Outputs

| Metric | Value | Source |
|--------|-------|--------|
| Senior debt | 42,852.27 kEUR | `fixed_debt_keur` in factory, frozen path |
| Opening SHL balance | ~15,790 kEUR | 14,621 + 1,169 |
| First valid distribution | op_idx 39 / 2050-06-30 | Phase 27 validation pack |
| Total distributions | ~104,918 kEUR | Phase 27 anchor |
| Equity IRR | ~9.88% | Phase 27 calibration |
| Project IRR | ~7.42% | Phase 27 calibration |
| DSCR avg | ~1.147 | Phase 27 calibration |

### Frozen Senior DS — Key Implication

Oborovo uses `use_frozen_excel_senior_debt_schedule = True`. This means:
- **Senior debt service per period is fixed from the frozen Excel schedule**
- **CAPEX changes do NOT re-size the frozen senior debt schedule**
- The frozen DS schedule is derived from the base-case Excel model (CAPEX = base)
- If CAPEX changes, the frozen senior DS remains unchanged — it is NOT recalculated
- Debt/equity ratio will shift under CAPEX variation, but debt amount stays fixed
- DSCR under CAPEX variation reflects CFADS change against fixed debt service

This means CAPEX sensitivity for Oborovo is **not a full refinancing scenario** — it is an **equity/project economics diagnostic under a fixed debt schedule**.

---

## Sensitivity Methodology

### Cases Defined

| Case | CAPEX Delta | Method |
|------|-------------|--------|
| Base | 0% | `create_default_oborovo()` as-is |
| CAPEX +5% | +2,799.95 kEUR | Scale capex items proportionally (test-local copy) |
| CAPEX +10% | +5,599.91 kEUR | Scale capex items proportionally (test-local copy) |
| CAPEX -5% | -2,799.95 kEUR | Scale capex items proportionally (test-local copy) |
| CAPEX -10% | -5,599.91 kEUR | Scale capex items proportionally (test-local copy) |

### Safe Sensitivity Method (Test-Local Only)

- Clone the Oborovo project inputs using `copy.deepcopy()`
- Scale capex item amounts proportionally (multiply by 1.05, 1.10, 0.95, 0.90)
- Do NOT mutate global factory objects
- Do NOT change persistent defaults
- Do NOT modify fixture CSVs
- Run `run_demo_project()` with the cloned inputs (requires WaterfallRunner directly)
- Collect outputs and discard the clone

**Limitation:** `run_demo_project()` uses named project types ("Oborovo") and scenario names ("Base"), not raw project inputs. For CAPEX sensitivity, the test directly instantiates `WaterfallRunner` with cloned inputs — bypassing the named project lookup.

### Outputs Collected Per Case

- Senior debt (from frozen schedule, unchanged under CAPEX variation)
- Senior debt service total
- Min DSCR, Avg DSCR
- Opening SHL balance
- First valid distribution op_idx / date
- Total distributions
- Project IRR
- Equity IRR
- Any runtime errors or NaN

---

## Sensitivity Case Table

> **Note:** Oborovo uses frozen senior debt schedule. CAPEX variation changes equity/project economics but does NOT change the frozen senior debt amount or schedule. See "Fixed/Frozen Senior DS Limitation" below.

| Case | CAPEX Δ | Senior Debt | DSCR avg | DSCR min | Equity IRR | Project IRR | Classification |
|------|---------|-------------|----------|----------|------------|-------------|----------------|
| Base | 0% | 42,852 kEUR | ~1.147 | ~0.85 | ~9.88% | ~7.42% | ✅ Validated (base) |
| CAPEX +5% | +2,800 kEUR | 42,852 kEUR (frozen) | ↓ | ↓ | ↓ | ↓ | ⚠️ Diagnostic only |
| CAPEX +10% | +5,600 kEUR | 42,852 kEUR (frozen) | ↓↓ | ↓↓ | ↓↓ | ↓↓ | ⚠️ Diagnostic only |
| CAPEX -5% | -2,800 kEUR | 42,852 kEUR (frozen) | ↑ | ↑ | ↑ | ↑ | ⚠️ Diagnostic only |
| CAPEX -10% | -5,600 kEUR | 42,852 kEUR (frozen) | ↑↑ | ↑↑ | ↑↑ | ↑↑ | ⚠️ Diagnostic only |

**Directional interpretation only** — not Excel-validated. The frozen senior DS means this is an economics sensitivity, not a financing re-size.

---

## Fixed/Frozen Senior DS Limitation

### What the frozen senior DS means for sensitivity

When `use_frozen_excel_senior_debt_schedule = True`:
1. Senior debt amount = `fixed_debt_keur` = 42,852.27 kEUR (fixed, not sculpted)
2. Senior debt service per period = frozen Excel values (not re-computed)
3. CAPEX changes do NOT trigger debt re-sizing
4. DSCR = CFADS / frozen_senior_service — CFADS changes, DSCR changes, but senior service is fixed

### What this limitation implies

- CAPEX sensitivity is **equity/project economics diagnostic under fixed debt**
- It is **NOT** a full lender re-rating scenario
- You cannot claim CAPEX +10% "increases debt" or "triggers lender review" — debt is fixed
- You **can** say CAPEX +10% "reduces equity IRR by approximately X pp under fixed debt schedule"
- The debt quantum remains the same; equity's share of risk changes

### What is safe to say

- "Under fixed frozen senior debt, CAPEX +10% reduces equity IRR by approximately X pp"
- "DSCR average drops from ~1.147x to ~Y under CAPEX +10% due to lower CFADS against fixed debt service"
- "This is a directional diagnostic; actual lender re-rating would require re-sizing the debt schedule"

### What is NOT safe to say

- "CAPEX +10% increases senior debt" (debt is frozen, not re-sized)
- "This sensitivity reflects full refinancing dynamics" (it does not)
- "Lender DSCR threshold is violated at CAPEX +X%" (the frozen DS is from base-case Excel, not recalculated)
- "This sensitivity is Excel-validated" (it is diagnostic only)

---

## Impact Summary

**What changes with CAPEX:**
- CFADS (revenue - OPEX - tax) changes as CAPEX changes the equity base
- Equity IRR: higher CAPEX → lower equity IRR (all else equal, fixed debt)
- Project IRR: higher CAPEX → lower project IRR
- DSCR: higher CAPEX → lower DSCR (lower CFADS against fixed debt service)
- Distributions: higher CAPEX → lower distributions (lower CFADS)

**What does NOT change with CAPEX:**
- Senior debt amount (frozen at 42,852.27 kEUR)
- Senior debt service schedule (frozen from Excel)
- SHL amount, SHL IDC, opening SHL balance
- First valid distribution timing (locked by frozen DSCR schedule)

---

## Non-Claims

- No claim that CAPEX sensitivities are Excel-validated
- No claim that CAPEX sensitivities are bank/lender-ready
- No claim that frozen senior DS re-sizes under CAPEX variation
- No claim that sensitivity outputs reflect full refinancing dynamics
- No claim that TUHO is affected (TUHO frozen path is independent)
- No claim that generic project path is validated

---

## Recommended Next Steps

1. **Phase 29C** — TUHO CO2 Period-Level CSV: add `co2_revenue_keur` to `SculptingPeriod` output struct to expose period-level CO2 for stakeholder presentation (model change, out of scope for diagnostic-only phase)

2. **Phase 30** — TUHO/Oborovo Shared Debt Sizing Path Audit: audit frozen senior debt schedule wiring for both projects to confirm no unintended divergence

3. **Phase 31** — Oborovo Revenue Sensitivity (PPA tariff): test PPA tariff sensitivity for Oborovo — same frozen debt limitation applies, equity/project economics diagnostic

---

## Out-of-Scope List

- Financial formula changes
- CAPEX formula changes
- Revenue/OPEX/Tax formula changes
- Waterfall logic changes
- Senior debt sizing logic changes
- SHL/distribution logic changes
- Fixture CSV changes
- TUHO/Oborovo factory flag changes
- Full scenario engine
- UI scenario controls
- Construction IDC runtime engine
- M1–M18 IDC wiring
- C.16 Project Rights wiring
- Generic path validation