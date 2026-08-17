# MVP G3 + G3B — Engine Freeze Candidate Handoff

**Status**: DRAFT — Awaiting independent Fable review before G4 runtime promotion
**Date**: 2026-08-17
**Branch**: `mvp-g3-synthetic-anti-overfit`
**HEAD SHA**: `9b2dbb5` (updated post G3B source-exactness hardening)
**PR**: #938 (DRAFT — do NOT merge)

---

## Purpose

This document is the handoff to an independent Fable (Anthropic) review of the MVP
financial engine ahead of production runtime promotion (G4).

Two complementary validation layers are provided:

**G3 — Synthetic Project C** proves the engine is **generic**: the full sponsor-return
waterfall depends only on typed `ProjectInputs` contracts and not on project name, code,
origin, or any hard-wired per-project dispatch logic.

**G3B — KUPI (Real Out-of-Sample)** proves the engine produces plausible, source-traceable
results on a real 144 MW wind project in Bosnia & Herzegovina, using source-exact input
schedules and a two-stage engine-derived SHL handshake that eliminates source-output feedback.

---

## Cumulative Test Chain

| Generation | Test File | Scope | Count |
|---|---|---|---|
| G0 | `test_mvp_g0_generic_clean_engine_enablement.py` | Clean engine foundation | — |
| G1 | `test_mvp_g1_workflow_authority.py`, `test_mvp_g1_governance_methodology_lock.py` | Workflow authority, methodology lock | — |
| G2A | `test_mvp_g2a_financing_stack.py` | Financing stack (Solar 33 MW, Wind 43 MW) | — |
| G2B | `test_mvp_g2b_sponsor_returns.py` | Sponsor return metrics | — |
| G2C | `test_mvp_g2c_shareholder_waterfall.py` | Shareholder waterfall | — |
| DSRF | `test_mvp_dsrf_reserve_support.py` | DSRF reserve support (G2C extension) | — |
| **G3** | **`test_mvp_g3_synthetic_anti_overfit.py`** | **Synthetic anti-overfit (Tests A–P)** | **90** |
| **G3B** | **`test_mvp_g3b_kupi_anti_overfit.py`** | **KUPI real out-of-sample (Tests A–J)** | **33** |

**G3 + G3B focused validation total: 123 tests — all passing on exact HEAD.**

---

## G2A Fingerprints (must remain stable)

| Project | Total Uses (kEUR) | Senior (kEUR) | Derived SHL (kEUR) |
|---|---|---|---|
| Solar | 33 000 | 24 750 | 7 750 |
| Wind | 43 000 | 32 250 | 10 250 |

Any change to production financial logic that shifts these values requires explicit re-authorization.

---

## G3 — Synthetic Project C

### Design Assumptions

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

### G3 Test Coverage — Tests A through P

| Test Class | Coverage |
|---|---|
| Governance | Fixture has no factory imports, forbidden tokens, or identity dispatch |
| A — Determinism | Period-by-period: all material vectors identical on repeated calls |
| B — Identity invariance | Full financial vector comparison under name/company/code changes |
| C — Complete chain | All material vectors populated and finite |
| D — Bank/base separation | P90→P50 mutation changes bank CFADS and senior (DSCR binding) |
| E — Price causality | −10% PPA → revenue ↓, EBITDA ↓, bank CFADS ↓, economics ↓ |
| F — OPEX causality | +10% OPEX → EBITDA ↓, base CFADS ↓, bank CFADS ↓, distributions ↓ |
| G — DSCR causal | gearing=0.85 DSCR-binding; higher DSCR target → strictly lower senior |
| H — Tax causal | 20%→35% rate: cash tax ↑ (strictly), CFADS ↓, distributions ↓ |
| I — SHL deductibility | FULLY_DEDUCTIBLE vs FULLY_NON_DEDUCTIBLE: tax ↓, bank CFADS ↑, senior ↑ |
| J — Financing closure | Uses=Sources; SHL adapter handshake; gearing-binding; all 4 metrics finite |
| K — CASH_SWEEP portability | Per-period discipline; causal to available cash |
| L — Construction funding | Per-period `ConstructionFundingPeriod` reconciliation; zero cumulative gap |
| M — DA telescoping | Period-level: available=opening+inflow; closing=available−release |
| N — Period axis | Senior 2..25 (≠ 31); SHL maturity 52 in axis (≠ 33) |
| O — No source dispatch | Oborovo/TUHO code/name spoofing yields identical vectors |
| P — G2C stop boundaries | Three sub-causes asserted and documented; J-DSRA always False confirmed |

**Total: 90 passing.**

---

## G3B — KUPI Real Out-of-Sample Validation

### Project Identity

- **Project**: KUPI, 144 MW Wind, Bosnia & Herzegovina
- **Source workbook SHA-256**: `111178fb21109f55df45c0cc1ea108104ac8b6ed60f010ba75b6c498795f5954`
- **Fixture**: `tests/helpers/g3b_kupi_project.py` (test-only; not registered in engine)

### Key Engine Results

| Output | Value |
|---|---|
| Finco Total Uses | 215,803.438 kEUR (source: 264,850 kEUR — DSRF excluded from Uses) |
| Finco Final Senior | 135,707.583 kEUR |
| Source Senior | 147,150.442 kEUR |
| Engine-Derived SHL | 79,595.855 kEUR |
| Source SHL anchor | 68,152.996 kEUR (comparison only; NOT a model input) |
| Construction PIK (simple, dcf=2.0) | 12,735.337 kEUR |
| SHL Opening P2 | 92,331.192 kEUR |
| Binding constraint | DSCR |
| Fixed-point iterations | 10 |

### ENGINE_DERIVED_SHL_ADAPTER_HANDSHAKE_DIAGNOSTIC

Two-stage fixture:
- Stage 1: `run_project_financing_model(seed_proj)` with `clean_shl_principal_keur=1.0`
- Stage 2: `_build_kupi_project_inputs(..., clean_shl_principal_keur=fr_stage1.derived_shl_cash_principal_keur)`

Handshake proof: Senior with source-SHL input vs engine-SHL input → **delta = 0.0000000000 kEUR**.
The G2A fixed-point ignores `clean_shl_principal_keur` (overridden by `candidate_shl` starting at 0.0).

### Exact Source Input Schedules Used

| Schedule | Source cells | Values |
|---|---|---|
| Central price curve | Inputs!E106 | 31 annual values, 2030–2060 |
| MidLow price curve | Inputs!E109 × E111 | 31 annual values, 2030–2060 |
| CO2 price schedule | Inputs!E123:AH123 | 30 annual → 60 semi-annual values |
| O&M step schedule | Scenarios!E79:E108 | 6-step schedule |
| DSCR target schedule | DS!row19 | 24 × 1.50 + 4 × {1.757649, 1.757849} |

### G3B Test Coverage — Tests A through J

| Test Class | Coverage |
|---|---|
| A — Governance | No KUPI dispatch in engine; source SHL/Senior not in numeric inputs; AST scan |
| B — Period axis | 2 construction + 60 operating; senior 28 periods (14yr × 2) |
| C — G2A identity | Uses = Senior + SHL + Capital; engine-derived SHL used downstream |
| D — Identity invariance | Name/company/code changes yield identical financials |
| E — Bank/base separation | P90 < P50; balancing bridge +11,942 kEUR; residual +499 kEUR |
| F — SHL cash-sweep | Per-period principal ≤ cash_available; closes to zero at P61 |
| G — SHL compounding gap | Simple PIK documented; pure method delta on same-principal basis |
| H — CO2 bridge | Run B minus Run A ≈ 24,506 kEUR vs source 25,002 kEUR |
| I — DSCR revenue-mix | Explicit schedule reproduces DS!row19; generic formula gap documented |
| J — Sponsor returns compass | XIRR ranges plausible; not freeze evidence pending Senior correction |

**Total: 33 passing.**

---

## KUPI Capability-Gap Register

| # | Gap ID | Classification | Magnitude / Evidence |
|---|---|---|---|
| 1 | KUPI_BANK_CFADS_BALANCING_DEDUCTION_GAP | CLEAN_POLICY_VS_WORKBOOK_COMPATIBILITY | Removing 5 EUR/MWh balancing raises Senior 135,708 → 147,649 kEUR (+11,942 kEUR bridge). Source = 147,150 kEUR. |
| 2 | KUPI_SENIOR_GAP_RESIDUAL | OPEN_SMALL_RESIDUAL | +498.819 kEUR residual after balancing bridge; ~0.34% of source Senior. Do not tune. |
| 3 | KUPI_SHL_CONSTRUCTION_COMPOUNDING_GAP | CURRENT_FINCO_CAPABILITY_GAP | Pure method delta: **+436.179 kEUR** (source-principal basis) or **+509.413 kEUR** (Finco-principal basis). CROSS_BASIS_SHL_PIK_DIFFERENCE = +1,394.678 kEUR (combines different principals + method). Do NOT use +1,395 as method delta. |
| 4 | GENERIC_DYNAMIC_REVENUE_RATIO_DSCR_FORMULA_NOT_IMPLEMENTED | CURRENT_FINCO_CAPABILITY_GAP | DS!row13 = merchant_rev / total_rev (can exceed 100%: AF13 ≈ 1.031). KUPI DSCR result **reproduced** via explicit schedule → KUPI_PROJECT_DSCR_SCHEDULE_RESULT_REPRODUCED. Generic configurability gap, not KUPI schedule mismatch. |
| 5 | KUPI_SPONSOR_CONTRIBUTION_TIMING_POLICY_GAP | DEFINITION_OR_TIMING_DIFFERENCE | Source places full SHL+Capital at FC; engine distributes through construction. |
| 6 | KUPI_TAX_WORKBOOK_COMPATIBILITY_GAP | CLEAN_POLICY_VS_WORKBOOK_COMPATIBILITY | Standard Finco corporate tax vs source workbook treatment. |
| 7 | KUPI_VAT_FACILITY | UNSUPPORTED_INSTITUTIONAL_FEATURE | VAT financing facility not modelled. |
| 8 | G2C_RESERVE_GATE_NOT_CAUSALLY_CLOSED | See sub-causes below | Three sub-causes unchanged from G3. |

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

For the KUPI gap register, Fable should confirm the eight classifications above are
appropriate for the MVP freeze scope, particularly:
- Whether KUPI_SENIOR_GAP_RESIDUAL (+499 kEUR, ~0.34%) is acceptable as OPEN_SMALL_RESIDUAL.
- Whether GENERIC_DYNAMIC_REVENUE_RATIO_DSCR_FORMULA_NOT_IMPLEMENTED should be MUST_CLOSE_BEFORE_G4.

---

## G4 Definition (reference)

G4 = actual user Run path → clean engine → persisted clean `RuntimeResult` → provenance/audit trail.

G4 does NOT require resolution of the C3B3 adapter seams (those are separate from the
runtime promotion path).  G4 requires:
- The clean engine code path is wired to the user-facing Run action
- `RuntimeResult` is persisted with a full provenance record
- The G3 + G3B test suites pass on the wired runtime

---

## Stop Condition

Keep PR #938 DRAFT.  Do NOT mark Ready.  Do NOT merge.  Do NOT start G4.

Independent Fable review of this document and the G3 + G3B test suites is required before proceeding.
