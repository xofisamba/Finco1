# Phase 29A: TUHO CO2 Evidence Matrix

Base: `a43820d16d7f86ed4eac9f898c1d7c99f9fb7ab1`

## How to Read This Matrix

**Columns:**
- **Claim/behavior**: What is being asserted
- **Evidence type**: source file, test, runtime observation, or doc
- **Source**: specific file/line/test reference
- **Status**: ✅ confirmed | ⚠️ partially confirmed | ❌ failed/missing | N/A not applicable
- **Materiality**: 🔴 high | 🟡 medium | 🟢 low
- **Remaining limitation**: what is still unknown or out of scope

---

## CO2 Input & Configuration

| Claim / behavior | Evidence type | Source | Status | Materiality | Remaining limitation |
|---|---|---|---|---|---|
| TUHO CO2 is enabled | Factory field | `app/project_factories.py:368` (`co2_enabled=True`) | ✅ confirmed | 🟡 medium | None |
| TUHO CO2 price source is identified | Factory + schedule | `app/project_factories.py:377-385` (semiannual schedule with 30 values) | ✅ confirmed | 🟡 medium | Price schedule is model-input, not live market |
| TUHO Y1 CO2 price = 4.191 EUR/MWh | Factory field | `app/project_factories.py:377` (`co2_certificate_price_eur_per_mwh=4.191063312`) | ✅ confirmed | 🟡 medium | None |
| TUHO CO2 price schedule declines over time | Semiannual schedule | `app/project_factories.py:378-391` (values from 4.191 → 0.7) | ✅ confirmed | 🟡 medium | Schedule is deterministic model input |
| CO2 sales schedule fallback is correct | Code path | `domain/revenue/generation.py:216-222` (priority: schedule → flat price → legacy) | ✅ confirmed | 🟢 low | None |
| Generic wind CO2 enabled | Factory field | `app/project_factories.py:559` (`co2_enabled=True`, flat price 5.0, no schedule) | ✅ confirmed | 🟡 medium | No CO2 sales schedule; flat price only |

## Production → CO2 Revenue Linkage

| Claim / behavior | Evidence type | Source | Status | Materiality | Remaining limitation |
|---|---|---|---|---|---|
| CO2 revenue = generation_mwh × price_EUR/MWh / 1000 | Function | `domain/revenue/generation.py:153` (`_certificate_revenue_keur`) | ✅ confirmed | 🔴 high | None |
| CO2 revenue is added (not subtracted) from net revenue | Code | `domain/revenue/generation.py:245-252` (energy - balancing + CO2) | ✅ confirmed | 🔴 high | None |
| CO2 revenue included in total revenue | Code | `domain/revenue/generation.py:253` (`revenue_keur = net_revenue_after_balancing_keur`) | ✅ confirmed | 🔴 high | None |
| CO2 added to EBITDA for CIT purposes (Phase 9 bridge) | Tax engine | `domain/waterfall/tax_engine.py:84-87` | ✅ confirmed | 🟡 medium | CIT treatment confirmed; no separate CO2 tax deduction |
| CO2 included in EBITDA for DSCR calculation | Code | `domain/waterfall/waterfall_engine.py:749-750` (EBITDA = ebitda + co2_cit_bridge) | ✅ confirmed | 🟡 medium | None |

## TUHO Anchors

| Claim / behavior | Evidence type | Source | Status | Materiality | Remaining limitation |
|---|---|---|---|---|---|
| TUHO Y1 CO2 revenue ≈ 611 kEUR | Computed + doc | Phase 27 pack + MEMORY.md Sprint 21 | ✅ confirmed | 🔴 high | Per-period split: H1 ~303 kEUR, H2 ~308 kEUR (generation varies) |
| TUHO equity IRR with CO2 ≈ 11.81% | Runtime output | `run_demo_project('TUHO','Base')` result | ✅ confirmed | 🔴 high | Excel reference 11.61%; delta +0.20pp within ±1.0pp tolerance |
| TUHO equity IRR without CO2 would be lower | Inference | MEMORY.md Sprint 21 (10.58% without CO2) | ✅ confirmed | 🟡 medium | IRR with/without CO2 differential documented |
| TUHO total revenue non-negative | Runtime output | `run_demo_project('TUHO','Base')` result.total_revenue_keur | ✅ confirmed | 🔴 high | None |
| TUHO CO2 revenue non-negative | Runtime computation | generation × price / 1000 (both positive inputs) | ✅ confirmed | 🟡 medium | Price schedule ensures positivity |
| TUHO CO2 revenue included only where intended (co2_enabled=True) | Factory + code | `app/project_factories.py:368` + `_certificate_revenue_keur(enabled=...)` | ✅ confirmed | 🟡 medium | None |

## TUHO vs Generic Wind

| Claim / behavior | Evidence type | Source | Status | Materiality | Remaining limitation |
|---|---|---|---|---|---|
| TUHO CO2 is validation target | Doc | `docs/phase29a_tuho_co2_revenue_deep_dive.md` | ✅ confirmed | 🟡 medium | Scope explicitly limited to TUHO |
| Generic wind CO2 is exploratory/unvalidated | Doc + factory | `docs/phase28_generic_project_path_validation.md` + factory line 559 | ✅ confirmed | 🟡 medium | No Excel reference, no schedule, no calibration anchor |
| TUHO CO2 does not validate generic wind | Doc | This matrix and Phase 28 docs | ✅ confirmed | 🟡 medium | Boundary maintained |

## No External Data / API

| Claim / behavior | Evidence type | Source | Status | Materiality | Remaining limitation |
|---|---|---|---|---|---|
| No live external CO2 API calls | Code inspection | All domain/revenue/*.py, domain/waterfall/*.py | ✅ confirmed | 🟡 medium | CO2 price is static model input |
| No CO2 market data source introduced | Code inspection | No external data sources found | ✅ confirmed | 🟢 low | None |
| CO2 price is model-input, not live market data | Code + doc | `app/project_factories.py:377` schedule + Phase 29A doc | ✅ confirmed | 🟡 medium | Schedule is deterministic |

## Non-Claims Confirmed

| Claim / behavior | Evidence type | Source | Status | Materiality | Remaining limitation |
|---|---|---|---|---|---|
| No bank/lender/audit/certification claim for TUHO CO2 | Doc | `docs/phase29a_tuho_co2_revenue_deep_dive.md` (non-claims section) | ✅ confirmed | 🟡 medium | None |
| No SaaS/enterprise claim for CO2 revenue | Doc | Phase 29A doc + guardrails | ✅ confirmed | 🟢 low | None |
| No lender-ready or certification claim | Doc | Phase 29A doc | ✅ confirmed | 🟢 low | None |

## Guardrails

| Claim / behavior | Evidence type | Source | Status | Materiality | Remaining limitation |
|---|---|---|---|---|---|
| G20 BLOCKED | Guardrail file | `app/templates/partials/workspace_shell.html` (G20 BLOCKED) | ✅ confirmed | 🔴 high | None |
| R99/R102 NOT APPROVED | Guardrail file | `app/templates/partials/workspace_shell.html` (R99/R102 NOT APPROVED) | ✅ confirmed | 🔴 high | None |
| partial_pay_sweep not promoted | Guardrail file | `app/templates/partials/workspace_shell.html` | ✅ confirmed | 🟡 medium | None |
| flat/min DSCR sculpting not promoted | Guardrail file | `app/templates/partials/workspace_shell.html` | ✅ confirmed | 🟡 medium | None |
| No JS financial calculations | Inspection | No .js files changed in this phase | ✅ confirmed | 🟡 medium | None |
| TUHO frozen path unchanged | Factory inspection | `app/project_factories.py:202` (`use_frozen_excel_senior_debt_schedule=True`) | ✅ confirmed | 🟡 medium | None |
| Oborovo frozen path unchanged | Factory inspection | `app/project_factories.py:422` (`use_frozen_excel_senior_debt_schedule=True`) | ✅ confirmed | 🟡 medium | None |

---

## Summary

| Category | Total rows | ✅ | ⚠️ | ❌ |
|---|---|---|---|---|
| CO2 input & configuration | 5 | 5 | 0 | 0 |
| Production → CO2 linkage | 5 | 5 | 0 | 0 |
| TUHO anchors | 6 | 6 | 0 | 0 |
| TUHO vs generic wind | 3 | 3 | 0 | 0 |
| No external data/API | 3 | 3 | 0 | 0 |
| Non-claims | 3 | 3 | 0 | 0 |
| Guardrails | 7 | 7 | 0 | 0 |
| **Total** | **32** | **32** | **0** | **0** |

**TUHO CO2 validation: ✅ Complete.**
**Generic wind CO2: ⚠️ Exploratory — confirmed unvalidated, no claim made.**

---

## Period-Level CO2 Decision

**CSV report not created** — reason: `result.periods` (top-level output) does not expose `co2_revenue_keur` as a named attribute per period. The CO2 computation is internal to `full_revenue_schedule()` and is aggregated into `revenue_keur` before the waterfall. Period-level CO2 would require adding `co2_revenue_keur` to the `SculptingPeriod` output struct — out of scope for this diagnostic phase.

Y1 CO2 anchor confirmed via:
1. Direct computation: `generation_mwh × 4.191 / 1000` for Y1-H1 and Y1-H2 → ~303 + ~308 = ~611 kEUR ✅
2. Phase 27 anchor reference: "CO2 Y1 approximately 611 kEUR" ✅
3. Runtime equity IRR with CO2 = 11.81% (confirmed via `run_demo_project`) ✅