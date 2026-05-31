# Phase 34 — Generic Project Path Validation Boundary / Reference Plan

**Branch:** `phase34-generic-project-path-validation-boundary`
**Base SHA:** `844c2d2e554f0ae53b636c2980713f8be552b966` (after PR #346 Phase 35)
**Date:** 2026-05-31
**Status:** Diagnostic / validation-boundary / planning — no runtime formula changes

---

## 1. Scope & Objective

Close the generic project path validation question by documenting the current validation boundary and defining the reference plan required for future generic path validation.

This phase is **diagnostic and planning only** — it does not implement full generic validation, does not claim generic path is validated, and does not change any financial formulas.

---

## 2. Phase 35 Recap

Phase 35 Pilot RC Closeout confirmed the validated scope:

| Scope | Status |
|-------|--------|
| TUHO frozen template | ✅ Included in Pilot RC |
| Oborovo frozen template | ✅ Included in Pilot RC |
| Generic solar/wind | ❌ **Explicitly excluded** from Pilot RC validated scope |

The Pilot RC scope matrix states: "Generic solar/wind — ❌ Excluded — Unvalidated — exploratory only. Do not use for external decisions."

Phase 34's job is to **document and close** this boundary, not to promote generic path.

---

## 3. Inspected Files

| File | Purpose |
|------|---------|
| `app/project_factories.py:460–560` | `create_default_solar_project()`, `create_default_wind_project()` |
| `app/ui/project_context.py:2335–2365` | `_build_generic_wind_context()`, `_build_generic_solar_context()`, `_CONTEXTS` |
| `app/ui/project_context.py:2420–2435` | Generic project resolution |
| `main_web.py:190–191` | Project selector with warning labels |
| `docs/phase28_generic_project_path_validation.md` | Phase 28 findings |
| `docs/phase35_pilot_release_candidate_closeout.md` | Pilot RC scope |
| `docs/pilot_rc_scope_matrix.md` | Exclusion confirmation |
| `tests/test_phase28_generic_project_path_validation.py` | Phase 28 tests |

---

## 4. Current Generic Project Behavior

### 4.1 Generic Solar PV

| Property | Value |
|---------|-------|
| Code | `SOLAR-001` (via `create_default_solar_project`) |
| Technology | Solar PV |
| Capacity | 50 MW |
| COD | 2031-01-01 |
| Horizon | 25 years |
| Construction | 12 months |
| CAPEX (indicative) | ~33,000 kEUR (modules 20k + inverters 3k + civil 5k + grid 2k + soft 3k + IDC 500 + fees 200) |
| PPA tariff | 55.0 EUR/MWh |
| OPEX (Y1) | ~380 kEUR (TechMgmt 150 + Insurance 100 + Maintenance 80 + Lease&Tax 50) |
| CO2 enabled | No |
| SHL amount | 5,000 kEUR |
| SHL rate | 8% |
| Senior tenor | 15 years |
| Target DSCR | 1.20x |
| Lockup DSCR | 1.10x |
| Gearing | 75% |
| Debt sizing method | `DSCR_SCULPT` — **live sculpting, not frozen** |
| Frozen Excel fixture | **None** — no frozen senior debt schedule |
| Validation status | ❌ **Unvalidated** — no Excel reference |
| User-facing warning | "⚠️ Unvalidated · Derived path" (main_web.py:191) |

### 4.2 Generic Wind

| Property | Value |
|---------|-------|
| Code | `WIND-001` (via `create_default_wind_project`) |
| Technology | Wind |
| Capacity | 50 MW |
| COD | 2031-07-01 |
| Horizon | 25 years |
| Construction | 18 months |
| CAPEX (indicative) | ~43,000 kEUR (turbines 30k + civil 6k + grid 3k + soft 4k + IDC 500 + fees 200) |
| PPA tariff | 55.0 EUR/MWh |
| OPEX (Y1) | ~430 kEUR (TechMgmt 170 + Insurance 120 + Maintenance 95 + Lease&Tax 50) |
| CO2 enabled | No |
| SHL amount | 5,000 kEUR |
| SHL rate | 8% |
| Senior tenor | 15 years |
| Target DSCR | 1.20x |
| Lockup DSCR | 1.10x |
| Gearing | 75% |
| Debt sizing method | `DSCR_SCULPT` — **live sculpting, not frozen** |
| Frozen Excel fixture | **None** — no frozen senior debt schedule |
| Validation status | ❌ **Unvalidated** — no Excel reference |
| User-facing warning | "⚠️ Unvalidated · Derived path" (main_web.py:190) |

---

## 5. Validation Boundary

### 5.1 What Is NOT Validated

The following are **not validated** for generic solar/wind:

- Revenue outputs (no Excel reference to compare against)
- OPEX outputs (no Excel reference)
- CAPEX structure (round numbers, not calibrated)
- Senior debt amount (live DSCR sculpting, no frozen fixture)
- DSCR trajectory (live sculpting, no frozen reference)
- SHL treatment (live path, no reference)
- Project IRR (not calibrated against Excel)
- Equity IRR (not calibrated against Excel)
- Period-level schedule comparisons
- Tax/loss carryforward treatment
- CO2 treatment (generic wind CO2 not validated)

### 5.2 Why Full Validation Is Not Possible Yet

1. **No Excel reference model exists** for generic solar or generic wind
2. **Live sculpting path** (DSCR_SCULPT) is used instead of frozen-path — no ground truth fixture
3. **Indicative-only inputs** (round numbers like 50 MW, 55 EUR/MWh) — not from a real project
4. **No CO2 calibration** for generic wind (CO2 disabled for both generic templates)

### 5.3 What Would Be Required for Validation

| Requirement | Generic Solar | Generic Wind |
|-------------|---------------|--------------|
| Excel reference model | Required | Required |
| Input mapping | PPA tariff, capacity, capex breakdown, opex schedule | PPA tariff, capacity, wind hours, capex breakdown, opex schedule |
| Revenue parity | vs Excel revenue schedule | vs Excel revenue schedule |
| OPEX parity | vs Excel OPEX schedule | vs Excel OPEX schedule |
| CAPEX parity | vs Excel CAPEX schedule | vs Excel CAPEX schedule |
| Senior debt amount | vs Excel debt amount | vs Excel debt amount |
| DSCR trajectory parity | vs Excel DSCR schedule | vs Excel DSCR schedule |
| Live sculpting validation | Confirm live sculpt gives same result as frozen if same inputs | Same |
| SHL/distribution treatment | vs Excel SHL schedule | vs Excel SHL schedule |
| Project IRR parity | vs Excel IRR | vs Excel IRR |
| Equity IRR parity | vs Excel equity IRR | vs Excel equity IRR |
| Period-level export/audit | Required | Required |

---

## 6. UI Warning Status Review

### 6.1 Current Warning Labels

**main_web.py:190–191:**
```python
{"value": "generic_wind", "label": "Blank / Generic Wind ⚠️ Unvalidated · Derived path", ...}
{"value": "generic_solar", "label": "Blank / Generic Solar ⚠️ Unvalidated · Derived path", ...}
```

**Status:** ✅ Warning is strong and explicit. "⚠️ Unvalidated · Derived path" clearly communicates non-validated status.

### 6.2 Phase 28 Finding

Phase 28 confirmed generic projects "run without crashing" but are "unvalidated/exploratory" — this is unchanged.

**No wording corrections needed** — existing warnings are already strong enough.

---

## 7. Pilot RC Boundary Preservation

Phase 35 confirmed generic path is **excluded** from Pilot RC validated scope. Phase 34 confirms:

- Generic path is **not promoted** to validated status
- TUHO/Oborovo frozen paths remain the only validated paths
- Generic path outputs must not be presented as bankable/lender-ready
- G20/R99/R102 status applies to TUHO/Oborovo only (generic path G20 = BLOCKED by default, R99/R102 = NOT APPROVED)

**Validation boundary is intact.**

---

## 8. Future Validation Phases

### 8.1 Phase 34A (Future) — Generic Solar Excel Reference Model
- Acquire or build Excel reference model for generic solar
- Map inputs and run period-level comparison
- Establish tolerance bands
- Document sign-off steps

### 8.2 Phase 34B (Future) — Generic Wind Excel Reference Model
- Acquire or build Excel reference model for generic wind
- Map inputs and run period-level comparison
- Validate CO2 treatment if applicable
- Document sign-off steps

### 8.3 Phase 34C (Future) — Generic Path Live Sculpting Validation
- Compare live sculpting outputs against frozen path for same inputs
- Confirm DSCR_SCULPT equivalence with frozen when inputs are equal

---

## 9. Guardrails

- ✅ Do NOT claim generic project path is validated
- ✅ Do NOT claim generic outputs are Excel-validated
- ✅ Do NOT claim generic outputs are bankable/lender-ready
- ✅ Do NOT change financial formulas
- ✅ Do NOT change runtime calculations
- ✅ Do NOT change senior debt sizing logic
- ✅ Do NOT promote live sculpting
- ✅ Do NOT promote generic path from exploratory/unvalidated
- ✅ Do NOT change TUHO/Oborovo frozen path
- ✅ Do NOT change project factories (wording-only, no calculation changes)
- ✅ Do NOT change fixture CSVs
- ✅ Do NOT change Revenue/OPEX/CAPEX/Tax formulas
- ✅ Do NOT change SHL/distribution logic
- ✅ Do NOT add JS financial calculations
- ✅ Do NOT implement construction IDC runtime
- ✅ Do NOT wire M1-M18 IDC
- ✅ Do NOT wire C.16 Project Rights
- ✅ Do NOT implement multi-user/RBAC/SSO
- ✅ Do NOT claim SaaS-ready or enterprise-ready
- ✅ G20 BLOCKED (unchanged)
- ✅ R99/R102 NOT APPROVED (unchanged)
- ✅ partial_pay_sweep not promoted
- ✅ flat/min DSCR sculpting not promoted
- ✅ Backend remains source of truth
- ✅ No lender/bank/audit/SaaS/certification claims

---

## 10. Manifest Decision

**JSON manifest skipped.** This doc and the requirements matrix provide sufficient traceability. The manifest would add maintenance burden without corresponding benefit.

---

## 11. Phase 34 Finding

**Classification: VALIDATION BOUNDARY DOCUMENTED — NO CHANGES TO RUNTIME**

The generic path validation boundary is now clearly documented:
- Generic solar and generic wind are **unvalidated** — no Excel reference exists
- Live DSCR sculpting is used (not frozen path) — no ground truth fixture
- Strong UI warnings already in place ("⚠️ Unvalidated · Derived path")
- Pilot RC scope is **not diluted** — TUHO/Oborovo remain the only validated paths
- Future validation requires Excel reference models for both generic solar and generic wind

**Phase 34D fix: NOT REQUIRED** — diagnostic/planning only, no runtime changes.