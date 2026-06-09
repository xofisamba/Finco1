# Next Sprint Decision Matrix (Post-C9 / Post-C10-Readiness)

> Type: REPORT ONLY, DOCS ONLY
> Status: DRAFT
> Date: 2026-06-09
> Base SHA: `72f3ab6` (post-#557, post-C10-readiness design)
> Branch: `next-sprint-decision-matrix`
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

A structured comparison of seven candidate next-sprint options,
with product value, implementation risk, parity risk, expected
effort, dependency blockers, and recommended order. The document
ends with a single primary recommendation and a single parallel
low-risk docs/audit recommendation.

This is a **decision matrix**, not a decision. The actual
selection is left to the human owner (per the C-series rules: no
self-authorized promotion or implementation).

---

## 1. The seven candidates

| Code | Name | One-line |
|---|---|---|
| **A** | C10 TUHO controlled promotion | Wire the seam guard into the waterfall for the 4 allowed TUHO fields |
| **B** | R-PAR-2 senior IDC resolution | Convert R-PAR-2 from DISCOVERY to a recorded decision (A/B/C) |
| **C** | CAPEX 2.0 continuation | Phase 58+ continuation of CAPEX work post 57A-10H |
| **D** | OPEX line-item visibility | Phase 20O/20U sub-line work for OPEX grid |
| **E** | Depreciation enablement | Phase D4 / D5 to close depreciation shadow + promote |
| **F** | Generic Wind/Solar reference journey | F3+ external validation for generic path |
| **G** | Pilot UX hardening | Phase 60+ UX polish + reviewer productivity |

---

## 2. Comparison matrix

For each option, scoring is on:

- **Product value** (1–5): direct pilot/paid/enterprise unlock
- **Implementation risk** (1–5, 5 = highest risk)
- **Parity risk** (1–5, 5 = highest risk of breaking existing parity)
- **Effort** (S/M/L/XL)
- **Dependency blockers** (refer to `phase_rpar_blocker_register.md`)
- **Recommended order** (1 = first, 7 = last)

| Code | Product value | Impl. risk | Parity risk | Effort | Dependency blockers | Rec. order |
|---|---|---|---|---|---|---|
| A | 5 | 4 | 4 | L | R-PAR-2 (B), R-PAR-5, R99, governance approvals | 4 (post-B) |
| B | 5 | 1 | 0 | S | none (governance availability) | 1 (primary) |
| C | 2 | 2 | 1 | M | none | 6 (parallel) |
| D | 3 | 2 | 2 | M | partial (Phase 20O/20U ongoing) | 5 |
| E | 3 | 3 | 3 | M | R99, R102 audit chain | 7 |
| F | 4 | 3 | 4 | L | F-series inventory done; needs F3 design | 3 |
| G | 4 | 1 | 0 | M | none (UX-only) | 2 (parallel) |

---

## 3. Per-option detail

### A. C10 TUHO controlled promotion

- **Goal:** Wire the C9 seam guard into the waterfall for the 4
  allowed TUHO fields (`shl_idc_keur`, `shl_amount_keur`,
  `shl_opening_balance_keur`, `equity_total_keur`).
- **Product value:** 5/5 — closes the highest-priority pilot blocker
  chain (R-PAR-2 → R-PAR-5 → C10).
- **Implementation risk:** 4/5 — new runtime wiring; must not
  regress frozen path.
- **Parity risk:** 4/5 — promotion must land within ±1% per
  `phase_c10_readiness_design.md` parity table.
- **Effort:** L (multi-sprint, sequential).
- **Dependency blockers:** R-PAR-2 (B) must be CLOSED; R-PAR-5
  parity must be green; R99 audit chain closure; 4 required
  approvals.
- **Forbidden during:** pilot RC scope.
- **Hard rule:** No Oborovo before TUHO.

### B. R-PAR-2 senior IDC resolution

- **Goal:** Convert R-PAR-2 from DISCOVERY (PR #556) to a
  recorded governance decision (A model base-rate, B freeze/accept,
  C defer).
- **Product value:** 5/5 — unblocks option A and removes the #1
  parity blocker.
- **Implementation risk:** 1/5 — pure decision, no code.
- **Parity risk:** 0/5 — no model change.
- **Effort:** S (single sprint or sub-sprint).
- **Dependency blockers:** governance board availability; modelling
  lead review.
- **Forbidden during:** none (no hard rule violation).
- **Note:** Default is C (defer) if no decision lands.

### C. CAPEX 2.0 continuation

- **Goal:** Phase 58+ continuation of CAPEX UX work (post
  57A-10H closure). Adds cost/MW derived columns, contingency UX,
  VAT/WHT/depreciation-basis metadata visibility (per
  `phase57a10b/c/d_*_design.md`).
- **Product value:** 2/5 — incremental UX improvement.
- **Implementation risk:** 2/5 — UI layer only.
- **Parity risk:** 1/5 — no model impact.
- **Effort:** M (multi-sprint).
- **Dependency blockers:** none.
- **Forbidden during:** 57A-10F/G/H test isolation must hold.

### D. OPEX line-item visibility

- **Goal:** Phase 20O/20U sub-line work for OPEX grid; expose
  12 TUHO OPEX items + 15 Oborovo OPEX items at sub-line level.
- **Product value:** 3/5 — pilot confidence in OPEX parity.
- **Implementation risk:** 2/5 — UI + small grid wiring.
- **Parity risk:** 2/5 — must not change runtime OPEX values.
- **Effort:** M.
- **Dependency blockers:** Phase 20N discovery (already done).
- **Forbidden during:** must not hide sub-lines that the model
  already exposes.

### E. Depreciation enablement

- **Goal:** Phase D4 / D5 to close depreciation shadow validation
  (Oborovo) and promote depreciation into runtime.
- **Product value:** 3/5 — closes 6 pre-existing parity failures.
- **Implementation risk:** 3/5 — tax-accounting impact.
- **Parity risk:** 3/5 — depreciation must land within tolerance.
- **Effort:** M.
- **Dependency blockers:** R99 / R102 audit chain closure; tax
  model review.
- **Forbidden during:** Oborovo hard rule; must be TUHO-first.

### F. Generic Wind/Solar reference journey

- **Goal:** F3+ design and validation of generic wind/solar path
  for external decisions. Extends F1 (methodology) + F2-A/B/C
  (inventory + matrix) into a full validation journey.
- **Product value:** 4/5 — opens paid/enterprise for non-TUHO/
  Oborovo projects.
- **Implementation risk:** 3/5 — new domain modelling.
- **Parity risk:** 4/5 — generic path must be validated against
  Excel evidence.
- **Effort:** L.
- **Dependency blockers:** F1/F2-A/B/C already done; needs
  partner reference projects.
- **Forbidden during:** no external decisions on generic path
  until green.

### G. Pilot UX hardening

- **Goal:** Phase 60+ UX polish + reviewer productivity:
  inline help, error message catalog, keyboard shortcuts,
  scenario compare UX, audit-export ergonomics, dirty-state
  visibility, observability surface.
- **Product value:** 4/5 — pilot satisfaction, reviewer
  productivity.
- **Implementation risk:** 1/5 — UI only.
- **Parity risk:** 0/5 — no model impact.
- **Effort:** M.
- **Dependency blockers:** none.
- **Forbidden during:** none.

---

## 4. Final recommendation

### 4.1 Primary: **B. R-PAR-2 senior IDC resolution**

Rationale:

- It is the **highest-leverage sprint**: a single decision unblocks
  option A (C10 promotion), removes the #1 parity blocker, and
  closes the most-promoted blocker in the register.
- It is **lowest risk**: no code, no model, no parity impact.
- It is **fastest**: S effort, sub-sprint possible.
- It is **not blocked** by any open hard rule.
- It directly enables option A as the next primary sprint, with
  a clean handoff.

**Why not A directly?** A (C10 promotion) is blocked on B
(R-PAR-2 decision). Starting A without B would either fail the
guard or require a governance override — both forbidden.

**Why not E, F, or D?** All have higher implementation/parity
risk and depend on the audit chain or reference validation
that is itself blocked. They are real candidates for the
*next* sprint after B + A, not for *this* sprint.

### 4.2 Parallel low-risk: **G. Pilot UX hardening**

Rationale:

- Lowest implementation + parity risk.
- No hard-rule violation.
- Independent of the R-PAR-2 / C10 chain.
- Improves pilot satisfaction in the same window.
- Can run in parallel without blocking the primary.

### 4.3 Suggested sequencing (multi-sprint view)

| Sprint | Primary | Parallel |
|---|---|---|
| **Sprint 24-A** | **B** (R-PAR-2 decision) | **G** (Pilot UX hardening, part 1) |
| Sprint 24-B | R67 closure (R67 diagnostic + fix) | G (part 2) |
| Sprint 24-C | R99 / R102 audit chain closure | G (part 3) |
| Sprint 24-D | DEBT sculpting parity (TUHO) | F3 design start |
| Sprint 24-E | DEP shadow closure (Oborovo, after TUHO) | F3 validation start |
| Sprint 24-F | A (C10 promotion) — if R-PAR-2 = closed | OB-DIST-LOCKUP (Oborovo) |
| Sprint 25-A | F3 generic path validation | D (OPEX sub-lines) |
| Sprint 25-B | D (OPEX) | C (CAPEX 2.0) |
| Sprint 25-C | E (depreciation) | C (CAPEX 2.0 cont.) |

**Hard rule reminder:** A (C10 promotion) is TUHO-only. Oborovo
promotion is forbidden until TUHO reaches the same gate.

---

## 5. No-go list (final)

The following are **not** appropriate as the next-sprint primary
or parallel:

- ❌ **C10 implementation** — blocked on B (R-PAR-2 decision)
  and the 4 required approvals
- ❌ **Oborovo promotion** — hard rule: Oborovo before TUHO
  forbidden
- ❌ **Senior IDC runtime change** — blocked on B
- ❌ **Live sculpting / debt re-sizing** — blocked on C10 +
  governance
- ❌ **Multi-user / RBAC / SSO** — separate strategic track
- ❌ **Bank / lender / external audit certification** — out of
  scope claim, no internal sprint
- ❌ **Replay engine** — separate strategic track
- ❌ **Generic wind/solar for external decisions** — needs F3
  validation, not yet
- ❌ **CAPEX 2.0 as primary** — too incremental for the
  current pilot priority
- ❌ **Depreciation enablement as primary** — blocked on
  R99/R102 chain

---

## 6. What this document does NOT do

- No implementation
- No decision (the human picks)
- No flag flip
- No promotion
- No governance action
- No test impact (this is a report-only PR)
- No commitment to a specific sprint name/number

The machine-readable companion is
`reports/phase_next_sprint_decision_matrix.json`.

---

## 7. Test footprint

This PR introduces shape-only characterization tests that
assert the document exists, lists all 7 candidates (A–G),
has the comparison matrix, and the final recommendation is
one of {B, C, D, E, F, G} with a parallel recommendation
that is different from the primary.
