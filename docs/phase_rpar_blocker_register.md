# R-PAR / R-Series Blocker Register (Post-C9 / Post-C10-Readiness)

> Type: REPORT ONLY, DOCS ONLY
> Status: DRAFT
> Date: 2026-06-09
> Base SHA: `72f3ab6` (post-#557, post-C10-readiness design)
> Branch: `rpar-blocker-register`
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

A consolidated, machine-readable register of all known **R-series
parity and audit blockers** plus related model/UX/governance blockers
that affect the path from current main to TUHO controlled promotion
(C10), and from pilot to paid product to enterprise.

This is the single source of truth for "what blocks what" across
the C-series, the depreciation series, the F-series, the parity
suite, and the trust layer.

This document is **report-only**. It does not implement, plan, or
commit to any resolution.

---

## 1. Sources

The register is built from the following primary sources (consumed,
not modified):

- `docs/phase_c1_construction_idc_design_gate.md` — R-PAR-1..5 origin
- `docs/phase_c9_closure_review_c1_c9.md` — C1-C9 closure blockers
- `docs/phase_rpar2_decision_discovery.md` — R-PAR-2 options
- `docs/phase_c10_readiness_design.md` — C10 blockers
- `docs/phase_pilot_readiness_gap_analysis.md` — pilot gap inventory
- `docs/phase6_*_r67_*.md` — R67 cash-tax bridge
- `docs/phase7f_tuho_r99_formula_bridge.md` — R99 audit chain
- `docs/phase9_shl_r102_runtime_wiring.md` — R102 SHL wiring
- `docs/phase20n_revenue_opex_parity_discovery.md` — OPEX parity
- `docs/phase31c_oborovo_equity_irr_shl_sweep_evidence_matrix.md` — Oborovo SHL
- `docs/phase_depreciation_*` — depreciation series
- `docs/phase23k_*.md` — Oborovo SHL opening balance bridge
- `docs/phase_f2*.md` — generic wind/solar inventory
- `MEMORY.md` — operational notes and parity gap inventory
- Full parity test suite (1681 pass / 88 fail at #557)

---

## 2. Status legend

- **OPEN** — blocker identified, no resolution path yet
- **DISCOVERY** — options defined, no decision made
- **DESIGN** — resolution path designed, not implemented
- **PARTIAL** — partial implementation, partial green
- **CLOSED** — resolved and validated
- **DEFERRED** — formally accepted as a known gap, no action planned

## 3. Severity legend

- **Critical** — unknown or fast-moving; must address immediately
- **High** — known, blocks pilot/paid/enterprise, no clear mitigation
- **Medium** — known, on the path, mitigable
- **Low** — known, documented, not on the critical path

## 4. The register

### B-R-PAR-1 — SHL IDC convention choice

- **ID:** R-PAR-1
- **Title:** SHL IDC convention (PIK vs cash-pay)
- **Status:** CLOSED (resolved in C2)
- **Severity:** High (was) / Resolved
- **Owner module:** `domain/construction/` SHL accrual path
- **Blocks:** Construction-bridge promotion of `shl_idc_keur`
- **Allowed next action:** Reference C2 design for SHL convention
- **Forbidden next action:** Reopen the convention question
- **Resolution path:** C2 design doc (`docs/phase_c2_*.md`); PIK is
  the chosen convention; preserved by `policy='replaced'` in
  POLICY_TABLE.

### B-R-PAR-2 — Senior IDC effective-rate caveat

- **ID:** R-PAR-2
- **Title:** Senior IDC effective-rate caveat
- **Status:** DISCOVERY (PR #556)
- **Severity:** High
- **Owner module:** `app/services/opening_balance_bridge.py` +
  `app/services/construction_runtime_seam.py` guard
- **Blocks:** Promotion of `senior_idc_keur` and
  `senior_opening_balance_keur`
- **Allowed next action:** Make a governance decision (option A
  model base-rate, B freeze/accept, C defer)
- **Forbidden next action:** Promote any senior IDC field into the
  runtime waterfall
- **Resolution path:** Pick A/B/C in PR #556 thread; record in
  governance memo; propagate to R-PAR-5 parity and C10 readiness
- **Default if no decision:** Option C (defer) — guard remains
  fail-closed

### B-R-PAR-3 — Construction-period CAPEX timing convention

- **ID:** R-PAR-3
- **Title:** Construction-period CAPEX timing (pre-COD lump vs
  drawdown profile)
- **Status:** CLOSED (resolved in C-series, design only)
- **Severity:** Medium
- **Owner module:** `domain/construction/` drawdown logic
- **Blocks:** None currently (no promotion path requests this yet)
- **Allowed next action:** Reference C-series design
- **Forbidden next action:** Re-introduce a pre-COD lump-sum
  default at runtime
- **Resolution path:** C1 design gate (`docs/phase_c1_*.md`)

### B-R-PAR-4 — Opening balance at COD convention

- **ID:** R-PAR-4
- **Title:** Opening balance at COD convention
- **Status:** CLOSED (resolved in C2 / C7)
- **Severity:** Medium
- **Owner module:** `app/services/opening_balance_bridge.py`
- **Blocks:** None currently
- **Allowed next action:** Reference C7 implementation
- **Forbidden next action:** Mix senior and SHL opening-balance
  conventions
- **Resolution path:** C7 implementation (PR #549, offline only)

### B-R-PAR-5 — `equity_total_keur` derived-field parity

- **ID:** R-PAR-5
- **Title:** Equity total derived-field parity
- **Status:** OPEN
- **Severity:** High
- **Owner module:** `app/services/opening_balance_bridge.py` +
  `app/services/construction_runtime_seam.py` derived-field guard
- **Blocks:** C10 promotion (one of 4 allowed fields)
- **Allowed next action:** Reclassify to `retained` or `frozen`
  if parity cannot be made green; or fix parity for TUHO and
  demonstrate `parity_ok=True` for the test case
- **Forbidden next action:** Promote `equity_total_keur` to runtime
  without a green parity test
- **Resolution path:** Either (a) parity fix in bridge or (b)
  reclassify field in C7 POLICY_TABLE — both options are docs/tests
  only at this stage; no implementation yet

### B-R67 — Cash-tax bridge residual (TUHO)

- **ID:** R67
- **Title:** R67 cash-tax bridge residual
- **Status:** OPEN (pre-existing, documented)
- **Severity:** Medium
- **Owner module:** `app/services/tax_bridge.py` interest-limitation
  consumer
- **Blocks:** Tax-cash parity for TUHO within ±0.5pp
- **Allowed next action:** Phase 6 / Phase 7 diagnostic reviews;
  document as known residual
- **Forbidden next action:** Rewrite tax-bridge core logic to
  silence the residual
- **Resolution path:** Sprint 24-B (R67 closure) — diagnostic
  first, fix only if root cause is structural

### B-R84 — R84 audit chain component

- **ID:** R84
- **Title:** R84 audit-chain component
- **Status:** OPEN (pre-existing)
- **Severity:** Medium
- **Owner module:** Audit-export service
- **Blocks:** R99 audit chain closure
- **Allowed next action:** Documentation + audit-export refactor
- **Forbidden next action:** Skip the audit chain
- **Resolution path:** Sprint 24-C (audit chain) — full chain
  R84 → R98 → R99 → R102

### B-R98 — R98 audit chain component

- **ID:** R98
- **Title:** R98 audit-chain component
- **Status:** OPEN
- **Severity:** Medium
- **Owner module:** Audit-export service
- **Blocks:** R99 audit chain closure
- **Allowed next action:** Per B-R84
- **Forbidden next action:** Per B-R84
- **Resolution path:** Per B-R84

### B-R99 — R99 audit chain closure

- **ID:** R99
- **Title:** R99 audit chain closure
- **Status:** OPEN (pre-existing)
- **Severity:** High
- **Owner module:** Audit-export service
- **Blocks:** Pilot signoff, paid-tier claim scope
- **Allowed next action:** Sprint 24-C (audit chain closure)
- **Forbidden next action:** Claim audit-readiness without
  green chain
- **Resolution path:** Close R84 + R98 + R99 + R102 in sequence

### B-R102 — R102 SHL runtime wiring

- **ID:** R102
- **Title:** R102 SHL runtime wiring
- **Status:** OPEN (pre-existing)
- **Severity:** High
- **Owner module:** `app/waterfall_runner.py` SHL path
- **Blocks:** R99 audit chain, SHL runtime promotion
- **Allowed next action:** Phase 9 / Phase 20R / Phase 20S follow-up
- **Forbidden next action:** Wire SHL runtime change outside of an
  approved sprint
- **Resolution path:** Sprint 24-C (audit chain) — sequential

### B-DEBT — Debt sculpting parity (TUHO and Oborovo)

- **ID:** DEBT-SCULPT
- **Title:** Debt sculpting parity (TUHO and Oborovo)
- **Status:** OPEN (pre-existing)
- **Severity:** Medium
- **Owner module:** `app/waterfall_runner.py` senior DSCR sculpting
- **Blocks:** Live sculpting / debt re-sizing
- **Allowed next action:** Sprint 24-D (debt sculpt)
- **Forbidden next action:** Promote live sculpting without
  parity green
- **Resolution path:** Sprint 24-D

### B-DEP — Depreciation shadow (Oborovo)

- **ID:** DEP-SHADOW
- **Title:** Depreciation shadow validation (Oborovo)
- **Status:** OPEN (pre-existing)
- **Severity:** Medium
- **Owner module:** `app/export/calibration_reconciliation.py`
- **Blocks:** Oborovo depreciation parity
- **Allowed next action:** Sprint 24-E (D4 closure)
- **Forbidden next action:** Promote depreciation runtime change
  without parity green
- **Resolution path:** Sprint 24-E

### B-OB-SHL — Oborovo SHL opening-balance bridge test isolation

- **ID:** OB-SHL-OB
- **Title:** Oborovo SHL opening balance bridge test isolation
- **Status:** OPEN (pre-existing, test-only)
- **Severity:** Low
- **Owner module:** `tests/test_phase23k_*.py`
- **Blocks:** Test cleanliness, not product
- **Allowed next action:** Test refactor (Phase 23K follow-up)
- **Forbidden next action:** Skip the test
- **Resolution path:** On-call

### B-OB-DIST — Oborovo distribution lockup policy residual

- **ID:** OB-DIST-LOCKUP
- **Title:** Oborovo distribution lockup policy residual
- **Status:** OPEN (pre-existing)
- **Severity:** Medium
- **Owner module:** `app/services/distribution_lockup.py`
- **Blocks:** Oborovo distribution parity
- **Allowed next action:** Sprint 24-F (lockup policy)
- **Forbidden next action:** Change lockup policy without parity
  green
- **Resolution path:** Sprint 24-F

### B-OB-SNAP — Oborovo pre/post-correction parity snapshots (N, P)

- **ID:** OB-SNAP
- **Title:** Oborovo pre/post-correction parity snapshots
- **Status:** OPEN (pre-existing, snapshots only)
- **Severity:** Low
- **Owner module:** `tests/test_phase23{n,p}_*.py`
- **Blocks:** Test cleanup
- **Allowed next action:** On-call
- **Forbidden next action:** Delete failing snapshots
- **Resolution path:** On-call

### B-OPEX — Oborovo OpEx line-item visibility

- **ID:** OPEX-VIS
- **Title:** Oborovo OpEx line-item visibility
- **Status:** PARTIAL (Y1=1,338 kEUR validated; sub-lines still
  mapping)
- **Severity:** Medium
- **Owner module:** `app/ui/project_context.py` OPEX grid
- **Blocks:** Pilot confidence in OPEX parity
- **Allowed next action:** Phase 20O / Phase 20U sub-line work
- **Forbidden next action:** Hide OPEX sub-lines from the pilot
  surface
- **Resolution path:** Sprint 25-B (OPEX visibility)

### B-CAPEX2 — CAPEX 2.0 continuation

- **ID:** CAPEX-2.0
- **Title:** CAPEX 2.0 continuation (post 57A-10H)
- **Status:** OPEN
- **Severity:** Medium
- **Owner module:** `app/ui/project_context.py` CAPEX surface
- **Blocks:** Pilot UI confidence for non-trivial CAPEX
- **Allowed next action:** Phase 58+ continuation
- **Forbidden next action:** Touch 57A-10F/G/H in this stack
- **Resolution path:** Sprint 25-C (CAPEX 2.0)

### B-CONST-IDC — Construction IDC M1–M18 / C.16 Project Rights

- **ID:** CONST-IDC
- **Title:** Construction IDC M1–M18 / C.16 Project Rights
- **Status:** OPEN (long-term, explicitly excluded from pilot)
- **Severity:** High
- **Owner module:** C-series continuation (C11+)
- **Blocks:** Full construction-period parity, C16 Project Rights
  modelling
- **Allowed next action:** C11+ design phases
- **Forbidden next action:** Promote in this stack
- **Resolution path:** Long-term roadmap, post-C10

### B-REPLAY — Replay-engine behavior

- **ID:** REPLAY
- **Title:** Replay-engine behavior (snapshot store + replay)
- **Status:** OPEN (design only)
- **Severity:** Medium
- **Owner module:** Runtime snapshot store
- **Blocks:** Enterprise audit replay
- **Allowed next action:** Design + characterization
- **Forbidden next action:** Wire replay in this stack
- **Resolution path:** Post-C10, separate track

### B-MULTI-USER — Multi-user / RBAC / SSO

- **ID:** MULTI-USER
- **Title:** Multi-user / RBAC / SSO
- **Status:** OPEN (explicitly out of pilot scope)
- **Severity:** High (for enterprise)
- **Owner module:** Auth surface
- **Blocks:** Enterprise / paid external use
- **Allowed next action:** Strategic roadmap
- **Forbidden next action:** Promote multi-user in this stack
- **Resolution path:** Pre-enterprise, separate track

### B-SIGNOFF — Approval / signoff orchestration

- **ID:** SIGNOFF
- **Title:** Approval / signoff orchestration
- **Status:** OPEN
- **Severity:** High (for enterprise)
- **Owner module:** Workflow surface
- **Blocks:** Enterprise / paid external use
- **Allowed next action:** Design + characterization
- **Forbidden next action:** Wire signoff in this stack
- **Resolution path:** Pre-enterprise, separate track

### B-CERT — Bank / lender / external audit certification

- **ID:** CERT
- **Title:** Bank / lender / external audit certification
- **Status:** OUT OF SCOPE (claim not made)
- **Severity:** Critical
- **Owner module:** External partner
- **Blocks:** None internally
- **Allowed next action:** Engage external partner (post pilot)
- **Forbidden next action:** Claim certification in this stack
- **Resolution path:** External, no internal sprint

### B-COMMERCIAL — Commercial packaging (pricing, claim scope, SLA)

- **ID:** COMMERCIAL
- **Title:** Commercial packaging
- **Status:** OPEN
- **Severity:** High (for paid)
- **Owner module:** Product / commercial
- **Blocks:** Paid external use
- **Allowed next action:** Product workstream
- **Forbidden next action:** Ship commercial without packaging
- **Resolution path:** Pre-paid, separate track

### B-F3 — Generic wind/solar external validation

- **ID:** F3
- **Title:** Generic wind/solar for external decisions
- **Status:** OPEN
- **Severity:** High (for paid/enterprise)
- **Owner module:** `domain/generic/` + F-series tests
- **Blocks:** Generic-path external use
- **Allowed next action:** Sprint 25-A (F3)
- **Forbidden next action:** Use generic path for external decisions
- **Resolution path:** Sprint 25-A

---

## 5. Counts by status

| Status | Count |
|---|---|
| CLOSED | 4 (R-PAR-1, R-PAR-3, R-PAR-4) |
| DISCOVERY | 1 (R-PAR-2) |
| PARTIAL | 1 (OPEX) |
| OPEN | 13 |
| OUT OF SCOPE | 1 (CERT) |
| DESIGN | 0 (none currently in design) |
| DEFERRED | 0 |
| **Total** | **20** |

## 6. Counts by severity

| Severity | Count |
|---|---|
| Critical | 1 (CERT) |
| High | 8 (R-PAR-2, R-PAR-5, R99, R102, C10-impl, CONST-IDC, MULTI-USER, SIGNOFF, COMMERCIAL, F3) |
| Medium | 9 (R67, R84, R98, DEBT, DEP, OB-DIST, OPEX, CAPEX-2.0, REPLAY) |
| Low | 2 (OB-SHL, OB-SNAP) |

(Note: severity counts include the cert out-of-scope blocker; if
excluded, total is 19.)

## 7. What this document does NOT do

- No implementation
- No flag flip
- No promotion
- No governance decision
- No resolution path commitment
- No test impact (this is a report-only PR)

The machine-readable companion is
`reports/phase_rpar_blocker_register.json`.

---

## 8. Test footprint

This PR introduces shape-only characterization tests that assert
the document and JSON report exist, contain the required top-level
keys, and that the registered count (≥ 20) is preserved. They do
not assert content beyond shape.
