# MVP G3 — Engine Freeze Candidate Handoff

**Status**: DRAFT — Awaiting independent Fable review before G4 runtime promotion
**Date**: 2026-08-17
**Branch**: `mvp-g3-synthetic-anti-overfit`
**PR**: #938 (DRAFT — do NOT merge)

---

## Purpose

This document is the handoff to an independent Fable (Anthropic) review of the MVP
financial engine ahead of production runtime promotion (G4).

G3 proves the engine is **generic**: the full sponsor-return waterfall depends only on typed
`ProjectInputs` contracts and not on project name, code, origin, or any hard-wired per-project
dispatch logic.  A third entirely fictional project (Synthetic Project C, 75 MW Solar, Spain)
is run end-to-end through the same production code path as G2A/G2B/G2C.

---

## Cumulative Test Chain

| Generation | Test File | Scope |
|---|---|---|
| G0 | `test_mvp_g0_generic_clean_engine_enablement.py` | Clean engine foundation |
| G1 | `test_mvp_g1_workflow_authority.py`, `test_mvp_g1_governance_methodology_lock.py` | Workflow authority, methodology lock |
| G2A | `test_mvp_g2a_financing_stack.py` | Financing stack (Solar 33 MW, Wind 43 MW) |
| G2B | `test_mvp_g2b_sponsor_returns.py` | Sponsor return metrics |
| G2C | `test_mvp_g2c_shareholder_waterfall.py` | Shareholder waterfall |
| DSRF | `test_mvp_dsrf_reserve_support.py` | DSRF reserve support (G2C extension) |
| **G3** | **`test_mvp_g3_synthetic_anti_overfit.py`** | **Synthetic anti-overfit (this PR)** |

---

## G2A Fingerprints (must remain stable)

| Project | Total Uses (kEUR) | Senior (kEUR) | Derived SHL (kEUR) |
|---|---|---|---|
| Solar | 33 000 | 24 750 | 7 750 |
| Wind | 43 000 | 32 250 | 10 250 |

Any change to production financial logic that shifts these values requires explicit re-authorization.

---

## Synthetic Project C — Design Assumptions

All parameters below are **design inputs**.  The engine derives Senior commitment, SHL
residual, and all financial schedules from them.  No value was chosen by inspecting a
downstream result.

| Parameter | Value | Differs from G2A/G2B how |
|---|---|---|
| Capacity | 75 MW | vs 33/43 MW |
| Horizon | 25yr | vs 20yr |
| Construction | 18 months | vs generic |
| SHL repayment | CASH_SWEEP | vs BULLET |
| Senior day count | ACT_365 | vs ACT_360 |
| DSCR target | 1.25× | vs 1.20× |
| Senior tenor | 12yr | same |
| All-in rate | 6.00% | design assumption |
| Gearing limit | 0.72 (senior only) | vs generic |
| SHL rate | 8.5% | design assumption |
| CAPEX | 41 000 kEUR | fictional |
| Share capital | 800 kEUR | fictional |

**Derived results** (engine output, not inputs):

| Output | Value |
|---|---|
| Senior commitment | 29 520 kEUR (gearing-binding) |
| Derived SHL principal | 10 680 kEUR |
| SHL adapter handshake | configured = derived ✓ |
| Senior period range | 2..25 (24 semi-annual periods = 12yr) |
| SHL maturity period | 52 (last operating period; operating axis: 2..52) |
| Operating period count | 51 semi-annual |

**SHL adapter handshake**: `clean_shl_principal_keur=10_680` is a required adapter input
to the CASH_SWEEP SHL scheduler.  The G3 test suite (TestJ) asserts at runtime that
`fr.derived_shl_cash_principal_keur == proj.financing.clean_shl_principal_keur`.

---

## G3 Test Coverage — Tests A through P

| Test Class | Vacuous? | Coverage |
|---|---|---|
| Governance | No | Fixture has no factory imports, forbidden tokens, or identity dispatch |
| A — Determinism | No | Period-by-period: all material vectors identical on repeated calls |
| B — Identity invariance | No | Full financial vector comparison (not only XIRR) under name/company/code changes |
| C — Complete chain | No | All material vectors populated and finite |
| D — Bank/base separation | No | P90→P50 mutation changes bank CFADS and senior (DSCR binding variant) |
| E — Price causality | No | −10% PPA → revenue ↓, EBITDA ↓, bank CFADS ↓, economics ↓ |
| F — OPEX causality | No | +10% OPEX → EBITDA ↓, base CFADS ↓, bank CFADS ↓, distributions ↓ |
| G — DSCR causal | No | gearing=0.85 DSCR-binding; higher DSCR target → strictly lower senior |
| H — Tax causal | No | 20%→35% rate: cash tax ↑ (strictly), CFADS ↓, distributions ↓ |
| I — SHL deductibility | No | FULLY_DEDUCTIBLE vs FULLY_NON_DEDUCTIBLE: tax ↓, bank CFADS ↑, senior ↑; delta ≠ SHL principal |
| J — Financing closure | No | Uses=Sources; SHL adapter handshake; gearing-binding baseline; all 4 metrics finite |
| K — CASH_SWEEP portability | No | Per-period discipline; causal to available cash |
| L — Construction funding | No | Per-period `ConstructionFundingPeriod` reconciliation; zero cumulative gap |
| M — DA telescoping | No | Period-level: available=opening+inflow; closing=available−release; cumulative identity |
| N — Period axis | No | Senior 2..25 (≠ 31); SHL maturity 52 in axis (≠ 33); within_senior_maturity transitions at 25 |
| O — No source dispatch | No | Oborovo/TUHO code/name spoofing yields identical vectors |
| P — G2C stop boundaries | No | Three sub-causes asserted and documented; J-DSRA always False confirmed |

**Total passing: see CI run for exact count (≈ 70+ CURRENT_BLOCKING tests)**

---

## Active Governance Stop-Boundaries (G2C, current main authority)

**G2C_RESERVE_GATE_NOT_CAUSALLY_CLOSED** — three sub-causes:

### Sub-cause 1: CASH_DSRA draw/replenishment not fully causal
`senior_dsra_closing` is static / target-based.  The draw and replenishment mechanics
do not reflect a period-level causal cash flow trace from production evidence.
In SYNTH-C (DSRE=NONE), all DSRA balances are zero — this is the safe baseline.

### Sub-cause 2: J-DSRA not modelled
`gate_component_j_dsra_underfunded` is always `False` because J-DSRA is not
implemented.  The gate therefore omits one of the source-proven gate components.
Tested in TestP and confirmed present.

### Sub-cause 3: period_index <= senior_last_period_index as proxy
The `within_senior_maturity` flag is computed from `period_index <= senior_last_period_index`,
which may diverge from the source G4 <= B11 logic if the period axis shifts.

---

## Fable Review — Classification Requested

For each G2C stop-boundary sub-cause, the Fable reviewer should classify:

- **MUST_CLOSE_BEFORE_G4**: G4 runtime promotion is blocked until this is resolved.
- **ACCEPTED_MVP_LIMITATION**: Known limitation; acceptable for MVP scope; post-MVP roadmap.

The G3 team does not pre-decide this classification.  All three sub-causes are currently
annotated as known limitations, not blockers, pending the review decision.

---

## G4 Definition (reference)

G4 = actual user Run path → clean engine → persisted clean `RuntimeResult` → provenance/audit trail.

G4 does NOT require resolution of the C3B3 adapter seams (those are separate from the
runtime promotion path).  G4 requires:
- The clean engine code path is wired to the user-facing Run action
- `RuntimeResult` is persisted with a full provenance record
- The G3 test suite passes on the wired runtime

---

## Stop Condition

Keep PR #938 DRAFT.  Do NOT mark Ready.  Do NOT merge.  Do NOT start G4.

Independent Fable review of this document and the G3 test suite is required before proceeding.
