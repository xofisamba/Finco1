# Phase 34 — Generic Validation Requirements Matrix

**Branch:** `phase34-generic-project-path-validation-boundary`
**Base SHA:** `844c2d2e554f0ae53b636c2980713f8be552b966`
**Date:** 2026-05-31

---

## Generic Validation Requirements Matrix

| Requirement | Generic Solar | Generic Wind | Current Status | Evidence | Required for Validation? | Next Action |
|---|---|---|---|---|---|---|
| Excel/reference model | Required | Required | ❌ Not available | No Excel reference found in repo | Yes — **blocking** | Acquire/build Excel reference model |
| Input mapping (PPA tariff, capacity) | Required | Required | 🟡 Indicative only — 55 EUR/MWh, 50 MW | `create_default_solar_project()` / `create_default_wind_project()` | Yes — **blocking** | Map real project inputs from reference model |
| Revenue parity | vs Excel revenue schedule | vs Excel revenue schedule | ❌ Not validated | No Excel reference | Yes | Requires Excel reference first |
| OPEX parity | vs Excel OPEX schedule | vs Excel OPEX schedule | ❌ Not validated | No Excel reference | Yes | Requires Excel reference first |
| CAPEX parity | vs Excel CAPEX schedule | vs Excel CAPEX schedule | ❌ Not validated | Round numbers (33k/43k kEUR) — no reference | Yes | Requires Excel reference first |
| Senior debt amount parity | vs Excel debt amount | vs Excel debt amount | ❌ Not validated | Live DSCR_SCULPT, no frozen fixture | Yes | Requires Excel reference first |
| DSCR trajectory parity | vs Excel DSCR schedule | vs Excel DSCR schedule | ❌ Not validated | Live sculpting, no reference | Yes | Requires Excel reference first |
| Live sculpting validation | Confirm live sculpt = frozen if same inputs | Same | ❌ Not validated | No frozen fixture for generic path | Yes | Phase 34C future work |
| SHL/distribution treatment | vs Excel SHL schedule | vs Excel SHL schedule | ❌ Not validated | Live SHL path, no reference | Yes | Requires Excel reference first |
| Project IRR parity | vs Excel IRR | vs Excel IRR | ❌ Not validated | Not calibrated | Yes | Requires Excel reference first |
| Equity IRR parity | vs Excel equity IRR | vs Excel equity IRR | ❌ Not validated | Not calibrated | Yes | Requires Excel reference first |
| Period-level export/audit | Full period schedule required | Full period schedule required | ❌ Not validated | No reference to compare | Yes | Requires Excel reference first |
| CO2 treatment | N/A (CO2 disabled) | Not validated | ❌ Not validated | `co2_enabled=False` for generic wind | Yes (wind only) | Phase 34B future work |
| Warning labels | "⚠️ Unvalidated · Derived path" | "⚠️ Unvalidated · Derived path" | ✅ Warning strong | main_web.py:190–191 | N/A (warning already strong) | Monitor, no change needed |
| Pilot RC exclusion | ❌ Excluded from Pilot RC validated scope | ❌ Excluded from Pilot RC validated scope | ✅ Confirmed | Phase 35 closeout, pilot_rc_scope_matrix.md | N/A | Maintain exclusion |
| G20 status | BLOCKED (default) | BLOCKED (default) | ✅ Applied | Factory defaults | N/A | Maintain BLOCKED |
| R99/R102 status | NOT APPROVED (default) | NOT APPROVED (default) | ✅ Applied | Factory defaults | N/A | Maintain NOT APPROVED |
| Frozen path comparison | N/A for generic (no frozen) | N/A for generic (no frozen) | ✅ Correctly absent | Generic uses live DSCR_SCULPT | N/A | N/A |
| UI warning language | "⚠️ Unvalidated · Derived path" | "⚠️ Unvalidated · Derived path" | ✅ Sufficient | main_web.py:190–191 | N/A | No change needed |

---

## Summary

| Category | Count |
|----------|-------|
| Required for validation (blocking) | 13 |
| Not applicable / warning already sufficient | 5 |

**Decision: Generic path validation is blocked until Excel reference models are acquired for both generic solar and generic wind.**

---

## Pilot RC Boundary Confirmation

The Pilot RC validated scope remains **TUHO and Oborovo frozen templates only**. Generic solar and generic wind are:

- ✅ Explicitly excluded from Pilot RC validated scope (Phase 35 scope matrix)
- ✅ Marked with strong UI warnings ("⚠️ Unvalidated · Derived path")
- ✅ Using live sculpting path (not frozen) — correct architectural decision
- ❌ Not claiming any validation
- ❌ Not claiming bankable/lender-ready status

**Pilot RC boundary is preserved.**

---

## Phase 34D Decision

**No Phase 34D fix required.** This phase is diagnostic/planning only. No runtime changes were made or are needed. The validation boundary is clearly documented and the Pilot RC scope is not diluted.