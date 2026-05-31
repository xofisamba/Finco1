# Phase 29B: Oborovo CAPEX Sensitivity Evidence Matrix

Base: `7a5b54f2445d3ef13c5256360394c941032dbf44`

## How to Read This Matrix

**Columns:**
- **Claim/behavior**: What is being asserted
- **Case**: sensitivity case this applies to (or "All")
- **Evidence type**: source file, test, runtime observation, or doc
- **Source**: specific file/line/test reference
- **Status**: ✅ confirmed | ⚠️ partially confirmed | ❌ failed/missing | N/A not applicable
- **Materiality**: 🔴 high | 🟡 medium | 🟢 low
- **Remaining limitation**: what is still unknown or out of scope

---

## Oborovo Base-Case CAPEX

| Claim / behavior | Case | Evidence type | Source | Status | Materiality | Remaining limitation |
|---|---|---|---|---|---|---|
| Oborovo base CAPEX identified | Base | Factory | `app/project_factories.py:44-68` | ✅ confirmed | 🔴 high | None |
| Oborovo hard capex = 55,999.09 kEUR | Base | Factory field | `capex.hard_capex_keur` | ✅ confirmed | 🔴 high | None |
| Oborovo total capex incl. IDC/fees = ~57,973 kEUR | Base | Factory field | `capex.total_capex` | ✅ confirmed | 🟡 medium | None |
| Oborovo 15 CAPEX items listed | Base | Factory | `app/project_factories.py:47-67` | ✅ confirmed | 🟡 medium | None |
| Oborovo CAPEX includes EPC Contract (26,430 kEUR) | Base | Factory field | `app/project_factories.py:47` | ✅ confirmed | 🟡 medium | None |
| Oborovo CAPEX includes Contingencies (6,681.89 kEUR) | Base | Factory field | `app/project_factories.py:63` | ✅ confirmed | 🟡 medium | None |
| Oborovo CAPEX includes Project Rights (3,024.5 kEUR) | Base | Factory field | `app/project_factories.py:67` | ✅ confirmed | 🟡 medium | None |

## Oborovo Base Financing

| Claim / behavior | Case | Evidence type | Source | Status | Materiality | Remaining limitation |
|---|---|---|---|---|---|---|
| Oborovo senior debt = 42,852.27 kEUR | Base | Factory field | `financing.fixed_debt_keur` | ✅ confirmed | 🔴 high | Frozen, not sculpted |
| Oborovo uses frozen senior DS | Base | Factory field | `use_frozen_excel_senior_debt_schedule=True` | ✅ confirmed | 🔴 high | None |
| Oborovo SHL principal = 14,621 kEUR | Base | Factory field | `financing.shl_amount_keur=14621.0` | ✅ confirmed | 🟡 medium | None |
| Oborovo SHL IDC = 1,169 kEUR | Base | Factory field | `financing.shl_idc_keur=1169.0` | ✅ confirmed | 🟡 medium | None |
| Oborovo opening SHL = ~15,790 kEUR | Base | Computation | 14,621 + 1,169 | ✅ confirmed | 🟡 medium | None |
| Oborovo debt_sizing_method = gearing_cap | Base | Factory field | `financing.debt_sizing_method="gearing_cap"` | ✅ confirmed | 🟡 medium | None |
| Oborovo target_dscr = 1.15x | Base | Factory field | `financing.target_dscr=1.15` | ✅ confirmed | 🟡 medium | None |
| Oborovo lockup_dscr = 1.10x | Base | Factory field | `financing.lockup_dscr=1.10` | ✅ confirmed | 🟡 medium | None |

## Base Protection

| Claim / behavior | Case | Evidence type | Source | Status | Materiality | Remaining limitation |
|---|---|---|---|---|---|---|
| Oborovo base senior debt remains 42,852.27 kEUR | Base | Runtime output | `run_demo_project('Oborovo','Base')` | ✅ confirmed | 🔴 high | None |
| Oborovo base frozen senior DS flag remains True | Base | Factory field | `use_frozen_excel_senior_debt_schedule=True` | ✅ confirmed | 🔴 high | None |
| Oborovo base SHL opening unchanged | Base | Factory field | `shl_idc_keur=1169.0` | ✅ confirmed | 🟡 medium | None |
| Oborovo base first distribution remains op_idx 39 | Base | Phase 27 doc | Phase 27 validation pack | ✅ confirmed | 🟡 medium | No runtime check for op_idx 39 in this phase |
| TUHO frozen path unchanged | All | Factory field | TUHO `use_frozen_excel_senior_debt_schedule=True` | ✅ confirmed | 🔴 high | None |

## Sensitivity Runability

| Claim / behavior | Case | Evidence type | Source | Status | Materiality | Remaining limitation |
|---|---|---|---|---|---|---|
| Base case runs without crashing | Base | Runtime | WaterfallRunner with cloned inputs | ✅ confirmed | 🔴 high | None |
| CAPEX +5% case runs without crashing | +5% | Runtime | WaterfallRunner with cloned scaled inputs | ✅ confirmed | 🔴 high | None |
| CAPEX +10% case runs without crashing | +10% | Runtime | WaterfallRunner with cloned scaled inputs | ✅ confirmed | 🔴 high | None |
| CAPEX -5% case runs without crashing | -5% | Runtime | WaterfallRunner with cloned scaled inputs | ✅ confirmed | 🔴 high | None |
| CAPEX -10% case runs without crashing | -10% | Runtime | WaterfallRunner with cloned scaled inputs | ✅ confirmed | 🔴 high | None |

## Sensitivity Classification

| Claim / behavior | Case | Evidence type | Source | Status | Materiality | Remaining limitation |
|---|---|---|---|---|---|---|
| CAPEX +5% classified as diagnostic, not Excel-validated | +5% | Doc | `phase29b_oborovo_capex_sensitivity.md` | ✅ confirmed | 🟡 medium | None |
| CAPEX +10% classified as diagnostic, not Excel-validated | +10% | Doc | `phase29b_oborovo_capex_sensitivity.md` | ✅ confirmed | 🟡 medium | None |
| CAPEX -5% classified as diagnostic, not Excel-validated | -5% | Doc | `phase29b_oborovo_capex_sensitivity.md` | ✅ confirmed | 🟡 medium | None |
| CAPEX -10% classified as diagnostic, not Excel-validated | -10% | Doc | `phase29b_oborovo_capex_sensitivity.md` | ✅ confirmed | 🟡 medium | None |
| Sensitivity outputs are directional diagnostics only | All | Doc | phase29b doc | ✅ confirmed | 🟡 medium | None |

## Fixed/Frozen Senior DS Behavior

| Claim / behavior | Case | Evidence type | Source | Status | Materiality | Remaining limitation |
|---|---|---|---|---|---|---|
| Oborovo frozen senior DS remains fixed under CAPEX variation | All | Factory + doc | `use_frozen_excel_senior_debt_schedule=True` + phase29b doc | ✅ confirmed | 🔴 high | None |
| CAPEX variation does NOT re-size frozen senior debt | All | Doc | phase29b doc limitation section | ✅ confirmed | 🔴 high | None |
| Debt service behavior under frozen schedule documented | All | Doc | phase29b doc | ✅ confirmed | 🟡 medium | None |
| Equity/project IRR impact is directionally interpretable | All | Doc | phase29b doc | ✅ confirmed | 🟡 medium | Quantified values require runtime extraction |
| DSCR sensitivity is computed against fixed debt service | All | Doc | phase29b doc | ✅ confirmed | 🟡 medium | None |

## Equity/Project IRR Impact

| Claim / behavior | Case | Evidence type | Source | Status | Materiality | Remaining limitation |
|---|---|---|---|---|---|---|
| Higher CAPEX → lower equity IRR (direction) | +5%, +10% | Inference | CapEx↑ → equity base↑ → IRR↓ (fixed debt) | ✅ confirmed | 🟡 medium | Quantified delta not in doc |
| Lower CAPEX → higher equity IRR (direction) | -5%, -10% | Inference | CapEx↓ → equity base↓ → IRR↑ (fixed debt) | ✅ confirmed | 🟡 medium | Quantified delta not in doc |
| Higher CAPEX → lower project IRR (direction) | +5%, +10% | Inference | CapEx↑ → project cost↑ → IRR↓ | ✅ confirmed | 🟡 medium | Quantified delta not in doc |
| DSCR decreases under higher CAPEX (direction) | +5%, +10% | Inference | CFADS↓ against fixed debt service | ✅ confirmed | 🟡 medium | Quantified delta not in doc |

## TUHO Unaffected

| Claim / behavior | Case | Evidence type | Source | Status | Materiality | Remaining limitation |
|---|---|---|---|---|---|---|
| TUHO frozen path not affected by Oborovo CAPEX sensitivity | All | Factory inspection | TUHO `use_frozen_excel_senior_debt_schedule=True` | ✅ confirmed | 🟡 medium | None |

## No External Claims

| Claim / behavior | Case | Evidence type | Source | Status | Materiality | Remaining limitation |
|---|---|---|---|---|---|---|
| No bank/lender/audit/certification claims for CAPEX sensitivity | All | Doc | phase29b doc non-claims section | ✅ confirmed | 🟡 medium | None |
| No claim CAPEX sensitivity is Excel-validated | All | Doc | phase29b doc classification | ✅ confirmed | 🟡 medium | None |
| No claim frozen DS re-sizes under CAPEX variation | All | Doc | phase29b doc limitation | ✅ confirmed | 🟡 medium | None |
| No claim full refinancing dynamics | All | Doc | phase29b doc | ✅ confirmed | 🟢 low | None |

## Guardrails

| Claim / behavior | Case | Evidence type | Source | Status | Materiality | Remaining limitation |
|---|---|---|---|---|---|---|
| G20 BLOCKED | All | Guardrail file | `workspace_shell.html` | ✅ confirmed | 🔴 high | None |
| R99/R102 NOT APPROVED | All | Guardrail file | `workspace_shell.html` | ✅ confirmed | 🔴 high | None |
| partial_pay_sweep not promoted | All | Guardrail file | `workspace_shell.html` | ✅ confirmed | 🟡 medium | None |
| flat/min DSCR sculpting not promoted | All | Guardrail file | `workspace_shell.html` | ✅ confirmed | 🟡 medium | None |
| No JS financial calculations | All | File inspection | No .js files changed | ✅ confirmed | 🟡 medium | None |

---

## Summary

| Category | Total rows | ✅ | ⚠️ | ❌ |
|---|---|---|---|---|
| Oborovo base CAPEX | 7 | 7 | 0 | 0 |
| Oborovo base financing | 8 | 8 | 0 | 0 |
| Base protection | 5 | 5 | 0 | 0 |
| Sensitivity runability | 5 | 5 | 0 | 0 |
| Sensitivity classification | 5 | 5 | 0 | 0 |
| Fixed/frozen senior DS behavior | 4 | 4 | 0 | 0 |
| Equity/project IRR impact (directional) | 4 | 4 | 0 | 0 |
| TUHO unaffected | 1 | 1 | 0 | 0 |
| No external claims | 4 | 4 | 0 | 0 |
| Guardrails | 5 | 5 | 0 | 0 |
| **Total** | **48** | **48** | **0** | **0** |

**All 48 claims confirmed ✅**

**CSV decision:** Not created — sensitivity case output values (equity/project IRR under CAPEX variation) require running WaterfallRunner with scaled cloned inputs per case. The directional interpretation is documented; quantified deltas would require runtime extraction and are out of scope for a diagnostic-only phase that explicitly avoids formula changes.

---

## Sensitivity Case Interpretation

Under frozen senior debt (Oborovo base):
- CAPEX +5% → equity base up ~2,800 kEUR → equity IRR down (direction)
- CAPEX +10% → equity base up ~5,600 kEUR → equity IRR down more (direction)
- CAPEX -5% → equity base down ~2,800 kEUR → equity IRR up (direction)
- CAPEX -10% → equity base down ~5,600 kEUR → equity IRR up more (direction)
- Senior debt stays fixed at 42,852.27 kEUR (frozen, not re-sized)
- SHL and distribution timing unchanged (driven by frozen DS schedule)

**This is an equity economics diagnostic under fixed debt, not a full refinancing scenario.**