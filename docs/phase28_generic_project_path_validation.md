# Phase 28 — Generic Project Path Validation

## Base SHA
`ef5d479d3d9a4632a07a56050f9f53eebdfce138` (after PR #336 merge)

---

## 1. Scope and Objective

This phase inspects, characterizes, and validates the generic/new-project path behavior — without Excel reference files — as a diagnostic baseline for future validation work.

**What this phase is:**
- Diagnostic/validation/documentation first
- Internal consistency checks for generic projects
- Clear classification of what is safe to show vs what remains unvalidated

**What this phase is not:**
- Not a claim that generic path is Excel-validated
- Not a claim that generic path is bank/lender-ready
- Not a financial formula change
- Not a runtime behavior change

---

## 2. Inspected Files

| File | What was checked |
|---|---|
| `app/project_factories.py` | `create_default_solar_project()` and `create_default_wind_project()` factory functions, `use_frozen_excel_senior_debt_schedule`, `debt_sizing_method`, financing params |
| `app/api/project_runner.py` | `run_project()` — how projects are routed and executed |
| `app/ui_runner.py` | `run_demo_project()` — demo/path routing |
| `docs/pilot_user_guide.md` | Generic project warning language |
| `docs/validation_pack_executive_summary.md` | Validated scope boundary |
| `docs/phase27_frozen_path_external_validation_pack.md` | Non-claims and limitations |

---

## 3. Generic Project Architecture

### 3.1 Project Variants Identified

| Project | Code | Technology | Capacity | COD |
|---------|------|-------------|----------|-----|
| Generic Solar PV | `SOLAR-001` | Solar PV | 50 MW | 2031-01-01 |
| Generic Wind Farm | `WIND-001` | Wind | 50 MW | 2031-07-01 |

Both projects use `DebtSizingMethod.DSCR_SCULPT` — the live senior debt sizing engine, **not** the frozen Excel fixture path.

### 3.2 Senior Debt Sizing Path

| Property | Generic Solar | Generic Wind | TUHO | Oborovo |
|----------|---------------|--------------|------|---------|
| `use_frozen_excel_senior_debt_schedule` | `False` | `False` | `True` | `True` |
| `debt_sizing_method` | `dscr_sculpt` | `dscr_sculpt` | N/A (frozen) | N/A (frozen) |
| Senior debt amount | Computed live | Computed live | Fixture 43,359 kEUR | Fixture 42,852 kEUR |
| DSCR target | 1.20x | 1.20x | 1.20x | 1.15/1.35x |

**Key finding:** Generic projects do **not** use the TUHO/Oborovo frozen senior debt schedule. They use the live DSCR sculpting engine (`DebtSizingMethod.DSCR_SCULPT`). This is the correct design — generic path has no frozen Excel reference to draw from.

### 3.3 Generic Solar Diagnostic Table

| Property | Value |
|----------|-------|
| Code | `SOLAR-001` |
| Technology | Solar PV |
| Capacity | 50 MW |
| COD | 2031-01-01 |
| Horizon | 25 years |
| Construction | 12 months |
| CAPEX (indicative) | ~33,000 kEUR (modules 20k + inverters 3k + civil 5k + grid 2k + soft 3k) |
| PPA tariff | 55.0 EUR/MWh |
| OPEX (Y1) | ~380 kEUR (TechMgmt 150 + Insurance 100 + Maintenance 80 + Lease&Tax 50) |
| CO2 enabled | No |
| SHL amount | 5,000 kEUR |
| SHL rate | 8% |
| Senior tenor | 15 years |
| Target DSCR | 1.20x |
| Lockup DSCR | 1.10x |
| Gearing | 75% |
| Validation status | ⚠️ **Unvalidated** — no Excel reference |

### 3.4 Generic Wind Diagnostic Table

| Property | Value |
|----------|-------|
| Code | `WIND-001` |
| Technology | Wind |
| Capacity | 50 MW |
| COD | 2031-07-01 |
| Horizon | 25 years |
| Construction | 18 months |
| CAPEX (indicative) | ~43,000 kEUR (turbines 30k + civil 6k + grid 3k + soft 4k) |
| PPA tariff | 60.0 EUR/MWh |
| OPEX (Y1) | ~550 kEUR (TechMgmt 200 + Insurance 150 + Maintenance 120 + Lease&Tax 80) |
| CO2 enabled | Yes (price 5.0 EUR/MWh) |
| SHL amount | 6,000 kEUR |
| SHL rate | 8% |
| Senior tenor | 15 years |
| Target DSCR | 1.20x |
| Lockup DSCR | 1.10x |
| Gearing | 75% |
| Validation status | ⚠️ **Unvalidated** — no Excel reference |

---

## 4. Internal Consistency Results

### 4.1 What Works

- Both generic factories instantiate without error
- Financing params are coherent (target DSCR 1.20x, SHL amounts set, tenor 15 years)
- Revenue params are coherent (PPA tariff, term, index, market scenario)
- No NaN in factory construction
- `use_frozen_excel_senior_debt_schedule = False` — confirmed for both

### 4.2 Known Behaviors

- Generic path uses live DSCR sculpting engine — outputs depend on input assumptions
- No Excel reference exists to validate outputs against
- Outputs should be reviewed by an expert before drawing conclusions
- No bank/lender/audit/certification claim is made or can be made

---

## 5. What Is Safe to Say

| Claim | Safe? |
|-------|-------|
| Generic Solar/Wind projects run through the live DSCR sculpting engine | ✅ Yes |
| They do not use TUHO/Oborovo frozen senior debt fixtures | ✅ Yes |
| They are labeled unvalidated/exploratory in docs | ✅ Yes |
| Output headlines (revenue, OPEX, debt service, DSCR, distributions) are produced | ✅ Yes |
| DSCR sculpting target is 1.20x | ✅ Yes |
| No Excel reference exists for comparison | ✅ Yes |

---

## 6. What Is Not Safe to Say

| Claim | Why Not |
|-------|---------|
| Generic path is Excel-validated | ❌ No Excel reference exists |
| Generic path is bank/lender ready | ❌ No validation against financing documents |
| Generic path outputs are production-ready | ❌ Unvalidated — expert review required |
| Generic path is equivalent to TUHO/Oborovo frozen path | ❌ Different calculation path (live vs frozen) |
| Any specific IRR or debt quantum is correct | ❌ No reference to validate against |

---

## 7. TUHO/Oborovo Frozen Path Boundary Check

| Property | TUHO | Oborovo | Generic Solar | Generic Wind |
|----------|------|---------|---------------|--------------|
| `use_frozen_excel_senior_debt_schedule` | `True` | `True` | `False` | `False` |
| Frozen DS fixture used | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| Excel reference exists | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| Validation status | ✅ Validated | ✅ Validated | ⚠️ Unvalidated | ⚠️ Unvalidated |

**Confirmed:** TUHO and Oborovo remain in the frozen-template validated path. No factory flags were changed for them. Generic projects are clearly separated.

---

## 8. Known Limitations and Gap to Validation

| Limitation | Implication |
|------------|-------------|
| No Excel reference for generic projects | Cannot prove parity vs Excel |
| Live DSCR sculpting path vs frozen fixture path | Different calculation methodology — not comparable |
| Round-number CAPEX/OPEX in generic factories | Output magnitudes are illustrative, not calibrated |
| No CO2 certificate handling for generic solar | CO2 disabled for generic solar — only relevant for wind |
| SHL amount and tenor are placeholder | Financing structure not based on financing documents |

**Gap to validation:** To validate generic path, would need: (1) project-specific Excel model, (2) CAPEX/OPEX calibration against actual project costs, (3) financing document reference for debt structure.

---

## 9. Recommended Next Steps

| Step | Action |
|------|--------|
| 1 | Keep generic path labeled as unvalidated/exploratory in all docs |
| 2 | Do not promote generic path outputs as bank/lender-ready |
| 3 | If specific project is to be validated, obtain Excel reference and calibrate inputs |
| 4 | Consider Phase 29A (TUHO CO2 deep-dive) before further generic path work |
| 5 | Add explicit generic project warning to UI if not already present |

---

## 10. JSON Summary Decision

No `reports/phase28_generic_path_diagnostic_summary.json` is created in this phase.

**Rationale:** The diagnostic information is captured in this doc and the validation matrix. The factory outputs are already available in the codebase. A JSON layer would be redundant and would require running the full model to produce static values, which is outside the diagnostic scope of this phase.

---

## 11. Guardrails Preserved

- ✅ No financial formula changes
- ✅ No model files changed
- ✅ No fixture CSVs changed
- ✅ No TUHO/Oborovo factory flags changed
- ✅ `use_frozen_excel_senior_debt_schedule` remains `True` for TUHO/Oborovo
- ✅ Generic projects remain `False` for frozen DS fixture
- ✅ G20 BLOCKED
- ✅ R99/R102 NOT APPROVED
- ✅ partial_pay_sweep not promoted
- ✅ flat/min DSCR sculpting not promoted
- ✅ Backend remains source of truth
- ✅ No lender/bank/audit/SaaS/certification claims
