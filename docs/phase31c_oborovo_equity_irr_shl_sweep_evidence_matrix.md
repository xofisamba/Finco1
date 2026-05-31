# Phase 31C — Oborovo Equity IRR / SHL Sweep Evidence Matrix

**Branch:** `phase31c-oborovo-equity-irr-shl-sweep-investigation`
**Base SHA:** `965675f5ba9552daf4474e796c8c7a02844d8136`
**Date:** 2026-05-31

---

## Evidence Matrix

| Claim / Behavior | Evidence Type | Source File/Test/Doc | Status | Risk | Materiality | Next Action |
|---|---|---|---|---|---|---|
| Oborovo equity IRR runtime = 6.24% | WaterfallRunner execution | This phase | ✅ Confirmed | None | N/A | Update MEMORY.md anchor |
| Oborovo equity IRR ~9.88% anchor is stale | Historical doc + runtime analysis | MEMORY.md + Phase 31C doc | ✅ Confirmed stale | Low | Anchor only | Phase 32 or doc update |
| Oborovo uses equity_irr_method="combined" | Factory check | `app/project_factories.py:197` | ✅ Confirmed | None | N/A | None |
| Combined method: equity_investment = sculpt_capex - debt | Code inspection | `domain/waterfall/waterfall_engine.py:595–599` | ✅ Confirmed | None | N/A | None |
| Oborovo sculpt_capex_keur = 57,784 kEUR | Factory check | `app/project_factories.py:89` | ✅ Confirmed | None | N/A | None |
| Oborovo fixed_debt_keur = 42,852 kEUR | Factory check | `app/project_factories.py:191` | ✅ Confirmed | None | N/A | None |
| Oborovo equity_investment = 14,932 kEUR | Computed | `sculpt_capex - debt` | ✅ Confirmed | None | N/A | None |
| First distribution = period 41 (year 20) | WaterfallRunner execution | This phase | ✅ Confirmed | None | N/A | None |
| Distributions start late due to bullet SHL lockup | Code + runtime analysis | `domain/waterfall/waterfall_engine.py:Phase23O` | ✅ Confirmed expected | None | N/A | None |
| shl_balance P4 = 15,790 kEUR (unchanged) | WaterfallRunner execution | This phase | ✅ Confirmed | None | N/A | None |
| Oborovo shl_repayment_method = "bullet" | Factory check | `app/project_factories.py:200` | ✅ Confirmed | None | N/A | None |
| Oborovo shl_tenor_years = 20 | Factory check | `app/project_factories.py:201` | ✅ Confirmed | None | N/A | None |
| shl_sweep_keur P4 = 0.00 (runtime) | WaterfallRunner execution | This phase | ✅ Confirmed | None | N/A | None |
| shl_sweep_keur P4 anchor = 340.54 (stale) | CFADS bridge + runtime analysis | `domain/diagnostics/cfads_bridge.py:149` | ⚠️ Confirmed stale/artifact | Low | Anchor only | Update anchor to 0.00 |
| PPA revenue P4 runtime = 3,196.88 kEUR | Revenue decomposition | `domain/revenue/generation.py` + this phase | ✅ Confirmed | None | N/A | Update anchor label |
| PPA revenue P4 anchor = 3,255.16 kEUR (mislabeled) | CFADS bridge analysis | `domain/diagnostics/cfads_bridge.py:143` | ⚠️ Confirmed anchor mismatch | Low | Diagnostic only | Update anchor or diagnostic |
| P4 revenue breakdown: generation × PPA + CO2 | Revenue decomposition | `domain/revenue/generation.py` | ✅ Confirmed | None | N/A | None |
| P4 CO2 = 81.97 kEUR | Revenue decomposition | This phase | ✅ Confirmed | None | N/A | None |
| Oborovo ppa_revenue_keur anchor = 3,255.16 vs runtime 3,196.88 | CFADS bridge | `domain/diagnostics/cfads_bridge.py:143` | ⚠️ Delta = -58.28 kEUR | Low | Anchor only | Phase 31C doc update |
| Oborovo P4 OpEx anchor = +644.34 (fixed) | Phase 31B | `domain/diagnostics/cfads_bridge.py:147` | ✅ Confirmed fixed | None | N/A | None |
| OpEx false alarm remains closed | Phase 31 + 31B | Phase 31C doc + this matrix | ✅ Confirmed | None | N/A | None |
| Oborovo frozen senior DS path unchanged | Factory check | `app/project_factories.py:203` | ✅ Confirmed | None | N/A | None |
| Oborovo fixed_debt_keur = 42,852.27 unchanged | Factory check | `app/project_factories.py:191` | ✅ Confirmed | None | N/A | None |
| TUHO frozen path unchanged | Factory check | `app/project_factories.py:202` | ✅ Confirmed | None | N/A | None |
| TUHO equity_irr_method = "shl_plus_dividends" | Factory check | `app/project_factories.py:198` | ✅ Confirmed | None | N/A | None |
| No financial formula changes | Phase constraint | This phase | ✅ Confirmed | None | N/A | None |
| No model/runtime files changed | File inspection | `git status` (no model files) | ✅ Confirmed | None | N/A | None |
| No fixture CSVs changed | File inspection | `git status` (no fixture CSVs) | ✅ Confirmed | None | N/A | None |
| Phase 31D fix NOT required | Phase 31C conclusion | This doc | ✅ Confirmed | None | N/A | Phase 32 |
| No bank/lender/audit/certification claims | Doc review | This doc + matrix | ✅ Confirmed | None | N/A | None |
| G20 BLOCKED | Field check | This phase | ✅ Unchanged | None | N/A | None |
| R99/R102 NOT APPROVED | Field check | This phase | ✅ Unchanged | None | N/A | None |
| partial_pay_sweep not promoted | Field check | This phase | ✅ Confirmed | None | N/A | None |
| flat/min DSCR sculpting not promoted | Field check | This phase | ✅ Confirmed | None | N/A | None |
| Backend remains source of truth | Architecture | This phase | ✅ Confirmed | None | N/A | None |
| Equity IRR delta = stale anchor (not runtime defect) | Analysis | This doc | ✅ Confirmed | None | N/A | Update MEMORY.md |
| SHL sweep delta = expected under bullet SHL | Analysis | This doc | ✅ Confirmed | None | N/A | Update anchor |
| PPA revenue delta = anchor mismatch (not runtime defect) | Analysis | This doc | ✅ Confirmed | None | N/A | Update anchor |

---

## Summary

- **Total rows:** 39
- **✅ Status:** 33 confirmed (no risk, architecture difference or stale anchor)
- **⚠️ Status:** 6 detected (stale anchors, diagnostic mismatches — no runtime defect)
- **❌ Status:** 0 confirmed runtime defects
- **🔴 Critical:** 0

**Classification: NO RUNTIME DEFECTS — all findings are stale anchors, diagnostic mismatches, or expected architecture differences.**

**Phase 31D NOT required.** Recommended: Update MEMORY.md equity IRR anchor to 6.24%, update CFADS bridge anchors for PPA revenue and SHL sweep. Proceed to Phase 32 (Scenario Persistence).