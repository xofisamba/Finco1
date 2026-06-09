# Pilot-Readiness Gap Analysis (Post-C9 / Post-C10-Readiness)

> Type: REPORT ONLY, DOCS ONLY
> Status: DRAFT
> Date: 2026-06-09
> Base SHA: `72f3ab6` (post-#557, post-C10-readiness design)
> Branch: `pilot-readiness-gap-analysis`
> Hard constraints:
> - No code, no implementation
> - No runtime promotion
> - No waterfall routing
> - No flag flip
> - No senior IDC promotion
> - No Oborovo before TUHO
> - No persistence/schema changes
> - DRAFT until reviewed
> - rc1 untouched

---

## 0. Purpose

A consolidated pilot-readiness and product-readiness gap analysis
covering the current state of FincoGPT after the following
sprint chains:

- **Trust Layer A0–A3** — runtime authority, persistence, export
- **Depreciation D1–D3 + closure** — D-series + D1 redo + D2 redo +
  D3 redo + closure review
- **Generic F1–F2C** — generic solar/wind validation methodology +
  inventory + comparison matrix
- **CAPEX 57A-10F/G/H** — advanced metadata UI, column groups, UX
  polish
- **Construction C1–C9** — design gate, bridge design + offline impl,
  parity snapshot, engine comparison, runtime seam scaffolding
- **R-PAR-2 Decision Discovery** — three options defined, no decision
- **C10 Readiness Design** — TUHO controlled promotion gate (design
  only, no implementation)

This document is **report-only**. It does not implement, prioritize,
or commit to any next step. It is a structured inventory of
blockers against three product horizons:

1. **Pilot** — internal / guided pilot with trusted single user
2. **Paid product** — external paid use (SMB / boutique)
3. **Enterprise** — bank, fund, or audit-customer use

---

## 1. Scope & Method

### 1.1 Inputs

The following documents and artifacts were used to identify blockers
(consumed, not modified):

- `docs/phase14c_pilot_readiness_snapshot.md`
- `docs/pilot_rc_scope_matrix.md`
- `docs/phase_c9_closure_review_c1_c9.md`
- `docs/phase_rpar2_decision_discovery.md`
- `docs/phase_c10_readiness_design.md`
- `docs/phase20n_revenue_opex_parity_discovery.md`
- `MEMORY.md` parity gap inventory
- Full parity test suite (1671 pass / 88 fail baseline at #557)

### 1.2 Classification taxonomy

Each blocker is classified by **kind**:

- **architecture** — system-design or boundary issues
- **parity** — model output vs Excel evidence mismatch
- **UX** — user-facing product surface or workflow
- **governance** — controls, signoffs, audit, approval workflows
- **testing** — coverage, characterization, regression
- **commercial/product** — packaging, pricing, claims, support

### 1.3 Risk score

- **Low** — known, documented, not on the critical path
- **Medium** — known, on the path, mitigable
- **High** — known, blocks the horizon, no clear mitigations yet
- **Critical** — unknown or fast-moving; needs immediate attention

### 1.4 Effort estimate

- **S** — single sprint (≤ 2 weeks)
- **M** — multi-sprint (2–6 weeks)
- **L** — quarter-scale (≥ 6 weeks)
- **XL** — strategic (multiple quarters)

### 1.5 Scope horizons

- **P** — blocks **pilot** (internal trusted user)
- **$** — blocks **paid product** (external SMB)
- **E** — blocks **enterprise** (bank/fund/audit)
- Multiple tags mean the blocker affects multiple horizons.

---

## 2. Top 20 Pilot-Readiness Blockers

| # | Blocker | Kind | Risk | Effort | Horizon | Owner module | Sprint owner (suggested) | Recommended next sprint |
|---|---------|------|------|--------|---------|--------------|--------------------------|-------------------------|
| 1 | R-PAR-2 senior IDC effective-rate caveat | parity | High | M | P,$ | `waterfall_core.py` senior IDC accrual path | Modelling lead | Sprint 24-A (R-PAR-2) |
| 2 | R-PAR-5 `equity_total_keur` derived-field parity not green | parity | High | M | P,$ | `domain/construction` bridge + C7 policy | Bridge lead | Sprint 24-A (C10 promotion prep) |
| 3 | R67 cash-tax bridge residual (TUHO) | parity | Medium | M | P,$ | `tax_bridge/` interest-limitation consumer | Tax lead | Sprint 24-B (R67 closure) |
| 4 | R99 audit-chain (R84/R98/R99/R102) | testing | Medium | M | P,$ | `tests/test_tuho_r99_audit_fields.py` | Audit lead | Sprint 24-C (audit chain) |
| 5 | Debt sculpting parity (TUHO and Oborovo) | parity | Medium | M | P,$ | `waterfall_runner.py` senior DSCR sculpting | Debt lead | Sprint 24-D (debt sculpt) |
| 6 | Depreciation shadow (Oborovo) | parity | Medium | M | P | `app/export/calibration_reconciliation.py` | Depreciation lead | Sprint 24-E (D4 closure) |
| 7 | C10 implementation not started | architecture | High | L | P,$ | `app/services/construction_runtime_seam.py` | Runtime lead | Blocked on R-PAR-2 + governance |
| 8 | Generic wind/solar not validated for external claims | parity | High | L | P,$ | `domain/generic/` + `tests/test_f2*.py` | Validation lead | Sprint 25-A (F3 generic) |
| 9 | Live sculpting / debt re-sizing not promoted | architecture | High | L | P,$ | `waterfall_runner.py` debt-sizing modes | Runtime lead | Post-C10 |
| 10 | Construction IDC M1–M18 / C.16 Project Rights not implemented | architecture | High | XL | P,$ | C-series continuation (C11+) | Runtime lead | Long-term |
| 11 | Multi-user / RBAC / SSO not implemented | architecture | High | L | $,E | Auth surface, session isolation | Platform lead | Pre-enterprise |
| 12 | Bank/lender/external audit certification not in scope | governance | Critical | XL | E | Audit team | External partner | N/A — out of scope claim |
| 13 | Approval / signoff orchestration not wired | governance | High | M | $,E | Workflow surface, audit-export | Governance lead | Pre-enterprise |
| 14 | Replay-engine behavior not implemented | architecture | Medium | M | $,E | Runtime snapshot store + replay | Runtime lead | Post-C10 |
| 15 | R102 SHL runtime wiring not approved | testing | High | M | P,$ | Phase 9 + R102 path | Audit lead | Post-R99 closure |
| 16 | Generic wind CO2 path not validated | parity | Medium | S | P,$ | `domain/generic/wind/co2` | Validation lead | Sprint 25-A |
| 17 | Oborovo distribution lockup policy residual | parity | Medium | S | P | `app/services/distribution_lockup.py` | Bridge lead | Sprint 24-F |
| 18 | Oborovo SHL opening balance bridge test isolation | testing | Low | S | P | `tests/test_phase23k_*.py` | Test lead | On-call |
| 19 | Oborovo pre/post-correction parity snapshots (N, P) | testing | Low | S | P | `tests/test_phase23{n,p}_*.py` | Test lead | On-call |
| 20 | Auto-backup observability (logs only) | UX | Low | S | P | `phase 24F1` scheduler logs | Platform lead | On-call |

**Pilot-horizon focus (P):** blockers 1, 2, 3, 4, 5, 6, 7, 16, 17, 18, 19, 20.
**Pilot-priority critical path:** 1 → 2 → 7 (R-PAR-2 → R-PAR-5 → C10).

---

## 3. Top 10 Paid-Product Blockers

Sub-set of pilot blockers, plus the ones that specifically block
**paid external** use:

| # | Blocker | Kind | Risk | Effort | Pilot? | Enterprise? | Sprint owner (suggested) |
|---|---------|------|------|--------|--------|--------------|--------------------------|
| P1 | R-PAR-2 senior IDC | parity | High | M | yes | yes | Modelling lead |
| P2 | C10 not started | architecture | High | L | yes | yes | Runtime lead |
| P3 | Generic path not validated | parity | High | L | yes | yes | Validation lead |
| P4 | Multi-user / RBAC / SSO | architecture | High | L | — | yes | Platform lead |
| P5 | Audit-export package for paid tier | commercial | High | M | — | yes | Product lead |
| P6 | Commercial packaging (pricing, claim scope) | commercial | High | M | — | — | Product lead |
| P7 | Replay-engine behavior | architecture | Medium | M | — | yes | Runtime lead |
| P8 | Approval / signoff orchestration | governance | High | M | — | yes | Governance lead |
| P9 | External-model-review package for paid customers | governance | High | L | — | yes | Audit lead |
| P10 | SLA / support / on-call rotation | commercial | High | M | — | yes | Product lead |

**Paid-product critical path:** P1 → P2 → P5/P6 → P9.

---

## 4. Top 10 Enterprise Blockers

Sub-set of paid blockers, plus the ones that specifically block
**enterprise** use:

| # | Blocker | Kind | Risk | Effort | Paid? | Critical external? |
|---|---------|------|------|--------|-------|---------------------|
| E1 | Multi-user / RBAC / SSO | architecture | High | L | yes | required |
| E2 | Approval / signoff orchestration | governance | High | M | yes | required |
| E3 | Bank / lender / external audit certification | governance | Critical | XL | — | N/A — claim not made |
| E4 | Replay-engine behavior | architecture | Medium | M | yes | required |
| E5 | Audit-export package for regulated use | governance | High | M | yes | required |
| E6 | Live sculpting / debt re-sizing | architecture | High | L | yes | required |
| E7 | Generic wind/solar for enterprise (multi-project) | parity | High | L | yes | required |
| E8 | R99 / R102 audit chain closure | testing | High | M | yes | required |
| E9 | SLA, observability, on-call, escalation | commercial | High | M | yes | required |
| E10 | Enterprise billing / contract / data-residency | commercial | High | L | — | required |

**Enterprise critical path:** E1 + E2 + E5 + E9 (foundation) → E4 + E6 + E8 (audit + debt) → E7 (multi-project).

---

## 5. Cross-cutting risk summary

### 5.1 Parity debt (88 pre-existing test failures)

| Family | Test count | Severity | All pre-C9? |
|---|---|---|---|
| R-PAR-2 senior IDC | ~10 | High | yes |
| R-PAR-5 equity derived | ~5 | High | yes |
| R67 tax bridge | ~6 | Medium | yes |
| R99 audit chain | ~10 | High | yes |
| Debt sculpting | ~12 | Medium | yes |
| Depreciation | ~6 | Medium | yes |
| Oborovo SHL / distribution | ~10 | Medium | yes |
| Opex/runtime flag | ~6 | Medium | yes |
| CFADS / SHL waterfall | ~10 | Medium | yes |
| Other / misc | ~13 | Low–Med | yes |

All 88 are pre-existing at C9 baseline (`d55a900`); zero regressions
from C9 → #555 → #556 → #557.

### 5.2 Architectural gaps

- Layer 5 runtime seam is **scaffolded** but **not wired** into the
  waterfall. Promotion requires C10 implementation.
- Replay engine is **documented** in design docs but **not present**
  in runtime.
- Multi-user isolation is **explicitly out of scope** for pilot
  (single trusted user only).
- Construction IDC M1–M18 and C.16 Project Rights are
  **explicitly excluded** from pilot RC.

### 5.3 Governance gaps

- G20 remains BLOCKED.
- R99 / R102 NOT APPROVED.
- No audit team signoff recorded for pilot.
- No senior lender signoff recorded for TUHO or Oborovo.
- No external-model-review partner engaged.

### 5.4 Commercial / product gaps

- No pricing tier defined.
- No paid claim scope documented.
- No SLA, no support rotation, no escalation tree.
- No data-residency / region support documented.
- No enterprise contract template.

---

## 6. Recommended next sprint (preview — Step 4 will formalize)

The recommended next sprint is the **shortest path that closes the
most blockers without violating any hard rule**:

> **R-PAR-2 Decision Sprint (Sprint 24-A)**
>
> Goal: convert the R-PAR-2 OPEN status into a recorded governance
> decision (option A, B, or C), unblocking the C10 readiness gate and
> removing the #1 parity blocker.
>
> Scope:
> - Decision discovery (already done — PR #556)
> - Decision review by governance board
> - Decision recording (governance doc + memo)
> - Decision propagation to R-PAR-5 parity and C10 readiness
> - NO model change, NO formula change, NO runtime change
>
> Expected outcome: R-PAR-2 = CLOSED or FORMALLY DEFERRED with
> documented reason; C10 readiness PR unblocked.

A parallel low-risk docs/audit sprint is recommended alongside:
see Step 4 (Next Sprint Decision Matrix).

---

## 7. No-go list (preliminary — Step 4 will finalize)

The following are **not** appropriate as the next-sprint primary:

- C10 implementation — blocked on R-PAR-2 decision + governance
- Oborovo promotion — hard rule: Oborovo before TUHO forbidden
- Senior IDC runtime change — blocked on R-PAR-2 decision
- Live sculpting / debt re-sizing — blocked on C10 + governance
- Multi-user / RBAC — separate strategic track
- Bank / lender / external audit certification — out of scope claim
- Generic wind/solar for external decisions — needs F3+ validation
- Replay engine — separate strategic track

---

## 8. What this document does NOT do

- No implementation
- No flag flip
- No promotion
- No governance decision
- No next-sprint commitment
- No claim scope change
- No commercial commitment
- No test impact (this is a report-only PR)

The full no-go list, with reasoning and effort, is in
`reports/phase_pilot_readiness_gap_analysis.json` (machine-readable
companion).

---

## 9. Test footprint

This PR introduces a small characterization test that asserts the
document exists and lists ≥ 20 pilot blockers, ≥ 10 paid blockers,
≥ 10 enterprise blockers. It does not assert content; it asserts
shape.
