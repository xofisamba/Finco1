# MVP G3 — Engine Freeze Candidate Handoff

**Status**: DRAFT — Awaiting independent Fable review before G4 runtime promotion  
**Date**: 2026-08-17  
**Branch**: `mvp-g3-synthetic-anti-overfit`

---

## Purpose

This document is the handoff to an independent Fable (Anthropic) review of the MVP financial engine
ahead of production runtime promotion (G4).

G3 proves the engine is **generic**: the full sponsor-return waterfall depends only on typed
`ProjectInputs` contracts and not on project name, code, origin, or any hard-wired per-project
dispatch logic.  A third, entirely fictional project (Synthetic Project C, 75 MW Solar, Spain)
was run end-to-end through the same production code path used by G2A/G2B/G2C.

---

## Cumulative Test Chain

| Generation | Test File | Scope |
|---|---|---|
| G0 | `test_mvp_g0_generic_clean_engine_enablement.py` | Clean engine foundation |
| G1 | `test_mvp_g1_workflow_authority.py`, `test_mvp_g1_governance_methodology_lock.py` | Workflow authority, methodology lock |
| G2A | `test_mvp_g2a_financing_stack.py` | Financing stack (Solar 33 MW, Wind 43 MW) |
| G2B | `test_mvp_g2b_sponsor_returns.py` | Sponsor return metrics |
| G2C | `test_mvp_g2c_shareholder_waterfall.py` | Shareholder waterfall |
| DSRF | `test_mvp_dsrf_reserve_support.py` | DSRF reserve support (G2C governance) |
| **G3** | **`test_mvp_g3_synthetic_anti_overfit.py`** | **Synthetic anti-overfit (this PR)** |

---

## Synthetic Project C — Design Rationale

Synthetic Project C is **entirely fictional** and structurally differentiated from all prior projects:

| Parameter | G2A Solar | G2A Wind | Synthetic Project C |
|---|---|---|---|
| Capacity | 33 MW | 43 MW | **75 MW** |
| Horizon | 20yr | 20yr | **25yr** |
| Construction | generic | generic | **18 months** |
| SHL repayment | BULLET | BULLET | **CASH_SWEEP** |
| Senior day count | ACT_360 | ACT_360 | **ACT_365** |
| Senior matures (period) | 31 | 31 | **25** |
| SHL end (period) | 33 | 33 | **~24 (fully swept)** |
| DSCR target | 1.20x | 1.20x | **1.25x** |
| Tax rate | 25% | 25% | **28%** |
| Country | generic | generic | **Spain (ES)** |

The project is NOT registered in the application UI and does NOT appear in any factory registry.

---

## G3 Test Coverage — Tests A through O

| Test Class | Coverage |
|---|---|
| A — Determinism | Same inputs → same outputs on repeated calls |
| B — Identity invariance | Output invariant under name/company/code changes |
| C — Senior debt structure | 29 520 kEUR, gearing-binding, periods 2..25 |
| D — SHL cash-sweep policy | Fully swept to 0, zero PIK, no bullet residual |
| E — Bank/base CFADS separation | Bank CFADS on `debt_sizing`, not `tax_and_cfads` |
| F — Price sensitivity | Higher PPA tariff → higher equity distributions |
| G — OPEX sensitivity | Higher OPEX → lower equity distributions |
| H — DSCR sensitivity | DSCR target changes senior commitment |
| I — Tax sensitivity | Higher corporate tax → lower equity distributions |
| J — SHL rate sensitivity | Higher SHL rate → higher interest, lower equity |
| K — Financing closure | Uses = Sources identity |
| L — No source dispatch | Oborovo/TUHO codes yield SYNTH-C results |
| M — Period axis integrity | COD_ANCHOR_TWO_CONSTRUCTION_COLUMNS rules |
| N — DSRF optional | DSRE=NONE baseline; G2C_RESERVE_GATE boundaries documented |
| O — Results integrity | All four metrics populated, coherent, SHL fully repaid |

**Total: 58 passing tests (CURRENT_BLOCKING)**

---

## Active Governance Stop-Boundaries

The following stop boundaries are inherited from G2C and remain in effect.
G4 runtime promotion requires explicit resolution of each:

### G2C_RESERVE_GATE_NOT_CAUSALLY_CLOSED (3 sub-causes)

1. **da_inflow identity unresolved**: The signed_post_senior → da_inflow → dsrf_fee causal chain
   for non-NONE DSRF support modes at period boundary transitions has not been verified with
   period-level audit evidence.

2. **CovenantGatePolicy unprovable**: The causal chain from bank CFADS → lockup → covenant gate
   cannot be proven closed without a period-level trace against committed source evidence.

3. **DSRF fee interaction unverified**: The interaction between DSRF commitment fee treatment and
   post-senior signed cash flow is documented as GENERIC MVP policy but not source-proven for
   any specific project configuration beyond DSRE=NONE.

### Additional Blocked Seams

- **OBOROVO_SHL_BALANCE_LINEAGE_UNRESOLVED**: Construction → operating SHL opening balance
  transition cannot be proven from committed source evidence.
- **TUHO_SHL_BALANCE_LINEAGE_UNRESOLVED**: Same boundary status as Oborovo.
- **C3B3D1_BLOCKED_PAYMENT_MODE_SEMANTICS**: `shl_pik_switch_period=0` has no proven mapping
  to `ShlInterestPaymentMode.CASH_PAID`; adapter deferred to C3B3D2.

---

## Governance Prohibitions (Finco1 CLAUDE.md + G-Series)

The following are permanently forbidden in production financial logic:

- `project.name` / `project.code` / `project.baseline` dispatch
- `approved_delta` / `expected_delta` / balancing plugs / target fitting
- Excel vectors as runtime inputs
- Hidden post-engine mutations
- Period-specific magic constants
- `create_default_oborovo` / `create_default_tuho_wind1` in any test that claims to be generic

---

## G2A Fingerprints (Must Remain Stable)

These are the authoritative calibration fingerprints from G2A.  Any change to production financial
logic that shifts these values requires explicit re-authorization:

| Project | Senior kEUR | SHL kEUR | Junior kEUR |
|---|---|---|---|
| Solar | 33 000 | 24 750 | 7 750 |
| Wind | 43 000 | 32 250 | 10 250 |

---

## Next Action (G4 — Runtime Promotion)

After Fable review confirms this document and the G3 test suite:

1. Wire `build_shl_schedule_policy_from_project_inputs` into the orchestrator (C3B3D2)
2. Resolve `C3B3D1_BLOCKED_PAYMENT_MODE_SEMANTICS` with authoritative source evidence
3. Close G2C_RESERVE_GATE_NOT_CAUSALLY_CLOSED sub-causes with period-level audit
4. Promote SHL canonical adapter to production runtime

**STOP CONDITION FOR THIS PR**: Keep DRAFT.  Do NOT mark Ready.  Do NOT merge.  Do NOT start G4.
