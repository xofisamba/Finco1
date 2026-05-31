# Phase 31 — Oborovo OpEx Gap Evidence Matrix

**Branch:** `phase31-oborovo-opex-gap-deep-dive`
**Base SHA:** `2c33411e12f7bfec72224727ce1111de5b7fc91b`
**Date:** 2026-05-31

---

## Evidence Matrix

| Claim / Behavior | Evidence Type | Source File/Test/Doc | Status | Risk | Materiality | Next Action |
|---|---|---|---|---|---|---|
| Oborovo OpEx source identified | Runtime verification | `app/project_factories.py:38–120` | ✅ Confirmed | None | N/A | None |
| Oborovo Y1 OpEx = 1,338 kEUR (runtime) | WaterfallRunner execution | `tests/test_phase7f_oborovo_opex_fix.py` | ✅ Confirmed — 1,338.56 kEUR | None | N/A | None |
| Oborovo uses legacy simple OpexItem path | Code inspection | `app/waterfall_core.py:177–191` | ✅ Confirmed | None | N/A | None |
| use_opex_line_item_engine = False for Oborovo | Factory check | `app/project_factories.py:422` | ✅ Confirmed | None | N/A | None |
| B.01 representation = single parent item (198 kEUR) | Factory + template | `app/project_factories.py:103` + `domain/opex/templates/oborovo.py` | ✅ Confirmed — template not wired | None | N/A | None |
| B.02 step Y2→185.64 implemented correctly | Factory + runtime test | `app/project_factories.py:105` + `tests/test_phase20u_b_oborovo_b02_opex_step_change.py` | ✅ Confirmed | None | N/A | None |
| B.12 step Y3→12.4848 implemented correctly | Factory | `app/project_factories.py:116` | ✅ Confirmed | None | N/A | None |
| Parent/sub-item double-count risk | Template wiring analysis | `domain/opex/templates/oborovo.py` + `app/waterfall_core.py:177–191` | ✅ Confirmed excluded — template not wired | None | N/A | None |
| Runtime source = domain.opex.projections | Code inspection | `app/waterfall_core.py:191` | ✅ Confirmed | None | N/A | None |
| Oborovo detailed template exists but not wired | Code + runtime test | `domain/opex/templates/oborovo.py` | ✅ Confirmed — design doc only | None | N/A | None |
| TUHO OpEx path unaffected | Regression tests | `tests/test_opex.py` + `tests/test_phase29a_tuho_co2_revenue_deep_dive.py` | ✅ Confirmed — TUHO Y1=1,998 kEUR | None | N/A | None |
| TUHO frozen senior DS path unaffected | Factory check | `app/project_factories.py:202` | ✅ Confirmed — use_frozen_excel_senior_debt_schedule=True | None | N/A | None |
| Oborovo frozen debt path unchanged | Factory check | `app/project_factories.py:422` | ✅ Confirmed — use_frozen_excel_senior_debt_schedule=True, fixed_debt_keur=42,852.27 | None | N/A | None |
| Oborovo SHL opening unchanged | Factory check | `app/project_factories.py:424–425` | ✅ Confirmed — shl_amount=14,621, shl_idc=1,169 | None | N/A | None |
| No financial formula changes | Phase constraint | This doc + phase brief | ✅ Confirmed | None | N/A | None |
| No model/runtime files changed | File inspection | `git status` (no model files touched) | ✅ Confirmed | None | N/A | None |
| No fixture CSVs changed | File inspection | `git status` (no fixture CSVs touched) | ✅ Confirmed | None | N/A | None |
| CFADS bridge anchor has sign error | Data inspection | `domain/diagnostics/cfads_bridge.py:148` | ⚠️ Confirmed — `-644.34` is dash-typo | Low | Data quality only; no runtime impact | Phase 31B fix |
| ppa_revenue_keur P4 has -58.28 delta | Runtime measurement | This phase | ⚠️ Detected — unrelated to OpEx | Medium | Separate issue | Phase 31C |
| shl_sweep_keur P4 has -340.54 delta | Runtime measurement | This phase | ⚠️ Detected — lockup timing | Medium | Separate issue | Phase 31C |
| No bank/lender/audit/certification claims | Doc review | This doc + all phase docs | ✅ Confirmed | None | N/A | None |
| G20 BLOCKED | Field check | `app/guardrails.py` | ✅ Unchanged | None | N/A | None |
| R99/R102 NOT APPROVED | Field check | `app/guardrails.py` | ✅ Unchanged | None | N/A | None |
| partial_pay_sweep not promoted | Field check | This phase | ✅ Confirmed | None | N/A | None |
| flat/min DSCR sculpting not promoted | Field check | This phase | ✅ Confirmed | None | N/A | None |
| Backend remains source of truth | Architecture | `app/waterfall_core.py` | ✅ Confirmed | None | N/A | None |
| phase31b_fix not merged yet | PR state | PR #299 still draft | ✅ Confirmed — superseded | None | N/A | None |
| Oborovo equity IRR = 6.24% vs MEMORY ~9.88% | Runtime measurement | WaterfallRunner result | ⚠️ Delta detected — unrelated to OpEx (OpEx is correct) | Medium | Separate issue from OpEx | Phase 31C |
| Generic path not promoted | Phase constraint | This phase | ✅ Confirmed | None | N/A | None |
| Oborovo template is design doc, not runtime | Code inspection | `domain/opex/templates/oborovo.py` + `app/waterfall_core.py:177` | ✅ Confirmed | None | N/A | None |
| TUHO template is design doc, not wired to Oborovo | Code inspection | `domain/opex/templates/tuho.py` + `domain/opex/runtime_adapter.py` | ✅ Confirmed | None | N/A | None |
| Phase 20U-B B.02 step fix is correct | Regression test | `tests/test_phase20u_b_oborovo_b02_opex_step_change.py` | ✅ Confirmed | None | N/A | None |
| Phase 7F investigation (no fix needed) is correct | Regression test | `tests/test_phase7f_oborovo_opex_fix.py` | ✅ Confirmed | None | N/A | None |
| Phase 9.5 validation (Y1=1,338) is correct | Regression test | `tests/test_phase9_5_oborovo_opex_validation.py` | ✅ Confirmed | None | N/A | None |

---

## Summary

- **Total rows:** 35
- **✅ Status:** 30 confirmed (no risk, no action needed)
- **⚠️ Status:** 5 detected (data quality / separate issues)
- **❌ Status:** 0 confirmed defects
- **🔴 Critical:** 0

**Classification: FALSE ALARM — Oborovo OpEx is correct at 1,338 kEUR Y1. No runtime bug found.**

**Separate findings (not OpEx):**
1. CFADS bridge anchor sign error (`-644.34` should be `+644.34`) — Phase 31B fix
2. Oborovo equity IRR delta (6.24% vs ~9.88%) — Phase 31C investigation
3. SHL sweep timing — Phase 31C investigation
4. PPA revenue small gap (-58.28 kEUR) — Phase 31C investigation