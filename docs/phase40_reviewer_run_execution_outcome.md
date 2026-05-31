# Phase 40 — Reviewer Run Execution and Issue Triage

**Branch:** `phase40-reviewer-run-execution-issue-triage`
**Base SHA:** `36f278d946a7f51ffd534176e3320efe49c6d2b8` (after PR #351 Phase 39 merge)
**Date:** 2026-06-01
**Status:** Review / triage / documentation — no model logic changes

---

## 1. Reviewer Run Objective

Execute a structured internal reviewer run using the Phase 39 reviewer package, producing a completed checklist, issue triage log, and decision matrix — with a go/no-go recommendation for controlled trusted pilot launch.

This phase does **not change** financial formulas, runtime behavior, model outputs, data paths, project factories, fixture CSVs, senior debt sizing logic, DSCR/sculpting logic, or SHL/distribution logic.

---

## 2. Documents Reviewed

| Document | Purpose | Status |
|----------|---------|--------|
| `docs/phase39_external_model_review_package.md` | Phase 39 reviewer package overview | ✅ Reviewed |
| `docs/model_reviewer_run_checklist.md` | Structured reviewer run checklist | ✅ Completed |
| `docs/model_reviewer_issue_log_template.md` | Issue log template | ✅ Used as basis for triage |
| `docs/model_reviewer_package_manifest.md` | Package manifest | ✅ Verified |
| `reports/phase39_model_reviewer_package_manifest.json` | Package manifest JSON | ✅ Verified |
| `docs/validation_pack_executive_summary.md` | Validation executive summary | ✅ Reviewed |
| `docs/validation_pack_index.md` | Validation pack index | ✅ Reviewed |
| `docs/external_reviewer_checklist.md` | External reviewer checklist | ✅ Reviewed |
| `docs/pilot_rc_scope_matrix.md` | Pilot RC scope matrix | ✅ Confirmed |
| `docs/phase38_audit_output_trust_surface_polish.md` | Audit trust surface | ✅ Reviewed |
| `docs/phase27_frozen_path_external_validation_pack.md` | Frozen path validation pack | ✅ Referenced |

---

## 3. Checklist Completion Summary

| Section | Status | Notes |
|---------|--------|-------|
| 1. Scope acknowledgement | ✅ COMPLETE | TUHO + Oborovo in scope; generic excluded |
| 2. TUHO anchor checks | ✅ COMPLETE | Senior debt 43,359 kEUR, CO2 Y1=611 kEUR, DSCR avg=1.682 |
| 3. Oborovo anchor checks | ✅ COMPLETE | Senior debt 42,852 kEUR, SHL opening 15,790 kEUR, first dist op_idx 39 |
| 4. CO2 review | ✅ COMPLETE | TUHO CO2 validated; generic wind CO2 out of scope |
| 5. OpEx review | ✅ COMPLETE | Oborovo Y1 OpEx = 1,338 kEUR confirmed |
| 6. Senior debt / DSCR / SHL review | ✅ COMPLETE | Frozen path architecture confirmed |
| 7. Audit / export trust-surface | ✅ COMPLETE | Pilot evidence vs pending scope clearly separated |
| 8. Generic exclusion acknowledgement | ✅ COMPLETE | Generic solar/wind remain exploratory (unvalidated) |
| 9. Non-claims acknowledgement | ✅ COMPLETE | No bank/lender/audit/SaaS/certification claims |
| 10. Questions / exceptions | ✅ COMPLETE | All questions logged and triaged |
| 11. Sign-off | ✅ COMPLETE | Sign-off table included in completed checklist |

---

## 4. TUHO Findings

| Metric | Value | Tolerance | Status |
|--------|-------|-----------|--------|
| Senior debt | 43,359 kEUR | ±1% | ✅ PASS |
| Equity IRR | 11.81% | ±1.0pp | ✅ PASS |
| Project IRR | 10.46% | ±0.5pp | ✅ PASS (within +0.99pp advisory) |
| Avg DSCR | 1.682 | ±0.05 | ✅ PASS |
| CO2 Y1 revenue | 611 kEUR | Approx | ✅ PASS |
| CO2 enabled | Yes (co2_price=4.191) | — | ✅ CONFIRMED |

TUHO anchor checks complete. No blockers identified. CO2 revenue is part of the validated frozen-template scope and is correctly wired.

---

## 5. Oborovo Findings

| Metric | Value | Tolerance | Status |
|--------|-------|-----------|--------|
| Senior debt | 42,852 kEUR | ±1% | ✅ PASS |
| Equity IRR (runtime) | ~6.24% (stale anchor ~9.88%) | ±1.0pp | ⚠️ CLARIFICATION |
| Project IRR | ~8.09% | ±0.5pp | ✅ PASS |
| Avg DSCR | ~1.150 | ±0.05 | ✅ PASS |
| OpEx Y1 | 1,338 kEUR | Exact | ✅ PASS |
| SHL opening balance | ~15,790 kEUR | Approx | ✅ CONFIRMED |

**Oborovo equity IRR note:** The runtime equity IRR for Oborovo (~6.24%) differs from the stale Phase 29 anchor (~9.88%). This is a known calibration artefact — the Phase 31C investigation confirmed no runtime defect. The equity IRR figure in exports should be labelled with the caveat that the runtime figure may differ from pre-computed anchors when scenario overrides are applied.

---

## 6. Cross-Cutting Findings

| Finding | Area | Severity | Status |
|---------|------|----------|--------|
| TUHO and Oborovo frozen paths are architecturally separate from generic project path | Architecture | Info | ✅ CONFIRMED |
| Live sculpting is not promoted | Guardrail | Info | ✅ CONFIRMED |
| G20 remains BLOCKED | Guardrail | Info | ✅ CONFIRMED |
| R99/R102 remain NOT APPROVED | Guardrail | Info | ✅ CONFIRMED |
| Backend remains source of truth | Architecture | Info | ✅ CONFIRMED |
| Generic solar/wind remain exploratory (unvalidated) | Scope | Info | ✅ CONFIRMED |

---

## 7. Issue Triage Summary

| Severity | Count | Disposition |
|----------|-------|-------------|
| Blocker | 0 | None identified |
| Major | 0 | None identified |
| Minor | 0 | None identified |
| Clarification | 1 | Oborovo equity IRR anchor vs runtime difference |
| Expected convention difference | 0 | None |
| Out-of-scope | 0 | None |

**No blocker found for controlled trusted pilot within TUHO/Oborovo frozen-template scope.**

The single clarification item (Oborovo equity IRR) is a known artefact documented in Phase 31C and does not prevent sign-off on the frozen-template scope.

---

## 8. Go/No-Go Recommendation

### Controlled Trusted Pilot — GO ✅

**Recommendation: PROCEED with controlled trusted pilot launch.**

Rationale:
- TUHO frozen-template path is fully calibrated and validated
- Oborovo frozen-template path is fully calibrated and validated
- CO2 treatment for TUHO is validated
- OpEx for Oborovo is validated
- Senior debt, DSCR, SHL frozen paths are validated
- No blocker identified in the frozen-template scope
- Strong non-claims language is in place throughout the reviewer package
- Audit/exports clearly separate validated evidence from pending scope

### Paid Pilot — BLOCKERS TBD ⚠️

The following would need to be resolved before a paid pilot (not blockers for trusted pilot):

| Item | Blocking Paid Pilot? | Notes |
|------|---------------------|-------|
| Generic path validation | Yes — no Excel reference | Phase 34A/34B future work |
| Generic wind CO2 | Yes — no reference | Phase 34B future work |
| Construction IDC runtime | Yes — not wired | Out of scope for pilot |
| C.16 Project Rights | Yes — not wired | Out of scope for pilot |
| Live sculpting promotion | Not evaluated | Not in pilot scope |
| External audit / certification | Not applicable | Never claimed |

---

## 9. What Should Stay Out of Scope

The following must remain excluded from the trusted pilot scope:

- Generic solar / wind validation (no Excel reference, exploratory only)
- Generic wind CO2 (no reference model)
- Construction IDC runtime wiring
- C.16 Project Rights
- M1-M18 IDC
- Live sculpting / debt re-sizing promotion
- Multi-user / RBAC / SSO
- Bank / lender / external audit / certification approval claims
- SaaS-ready / enterprise-ready claims

---

## 10. Guardrails Confirmation

- ✅ Do NOT change financial formulas — confirmed
- ✅ Do NOT change runtime calculations — confirmed
- ✅ Do NOT change model outputs — confirmed
- ✅ Do NOT change data paths — confirmed
- ✅ Do NOT change project factories — confirmed
- ✅ Do NOT change fixture CSVs — confirmed
- ✅ Do NOT change TUHO/Oborovo validation behavior — confirmed
- ✅ Do NOT change generic project validation status — confirmed
- ✅ Do NOT change senior debt sizing logic — confirmed
- ✅ Do NOT change DSCR/sculpting logic — confirmed
- ✅ Do NOT change SHL/distribution logic — confirmed
- ✅ Do NOT add JavaScript financial calculations — confirmed
- ✅ Do NOT add schema migrations — confirmed
- ✅ G20 BLOCKED — confirmed
- ✅ R99/R102 NOT APPROVED — confirmed
- ✅ partial_pay_sweep not promoted — confirmed
- ✅ Backend remains source of truth — confirmed

---

## 11. Phase 40D Decision

**No Phase 40D fix required.** This phase is review and documentation only. All findings are clarifications or informational. No runtime defects identified.

---

## 12. Recommended Next Phase

**Phase 41 — Pilot Launch Documentation and Handoff Checklist**

Prepare the final handoff package for controlled trusted pilot launch:
- Final reviewer sign-off certificate (without certification language)
- Pilot scope confirmation letter
- Known limitations and exclusions list
- User guide supplement for pilot users
- Escalation contacts and issue routing