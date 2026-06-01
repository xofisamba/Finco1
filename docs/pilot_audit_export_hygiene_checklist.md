# FincoGPT — Pilot Audit / Export Hygiene Checklist

**Branch:** `phase44-pilot-audit-trail-export-hygiene`
**Base SHA:** `28afc581900bb5025d509a626de8d8369664d41f`
**Date:** 2026-06-01

Use this checklist before generating any export or sharing model outputs.

---

## Project / Scope Confirmation

| Check | Status | Notes |
|-------|--------|-------|
| Project is TUHO or Oborovo (validated path) | PASS | Generic is exploratory only |
| Pilot user briefed on validated vs exploratory scope | PASS | |
| Scope confirmation note shared with pilot user | PASS | |

---

## Draft vs Saved vs Runtime State

| Check | Status | Notes |
|-------|--------|-------|
| Saved scenario exists before any input change | PASS | Named snapshot — recoverable baseline |
| Draft edits are distinguishable from last clean run | PASS | Runtime summary shows last clean run, not current draft |
| Pilot user understands: draft ≠ last run ≠ export | PASS | |
| Scenario history accessible to verify baseline | PASS | |

---

## Last Clean Backend Run

| Check | Status | Notes |
|-------|--------|-------|
| Runtime summary shows last clean run timestamp | PASS | |
| Export lineage panel shows runtime snapshot ID | PASS | |
| No inputs changed since last clean run | PASS | If changed: re-run before export |
| `/readyz` green before run | PASS | |

---

## Export Artefact Purpose

| Check | Status | Notes |
|-------|--------|-------|
| Export is for internal review / evidence only | PASS | |
| Export does not represent bank/lender/audit approval | PASS | Non-claims enforced |
| Generic project export not used for financial decisions | PASS | Generic = exploratory only |
| Timestamp on export filename | PASS | |
| Export generated after last clean run | PASS | |

---

## Audit / Reconciliation Interpretation

| Check | Status | Notes |
|-------|--------|-------|
| Audit/Parity tab understood as internal review evidence | PASS | Not certified external audit |
| Pilot user has read `docs/pilot_scope_confirmation_note.md` | PASS | |
| "Internal review, not external audit" language acknowledged | PASS | |
| TUHO/Oborovo rows distinguished from generic rows | PASS | |

---

## Generic Exclusion

| Check | Status | Notes |
|-------|--------|-------|
| No generic solar/wind outputs used for financial decisions | PASS | |
| Exploratory warning displayed for generic project | PASS | |
| Generic boundary documented and communicated | PASS | |

---

## Stale Export Risk

| Check | Status | Notes |
|-------|--------|-------|
| No export shared from before last input change | PASS | |
| Re-run performed after any input change | PASS | |
| Export filename includes run timestamp | PASS | |
| No stale exports remain in active use or shared | PASS | |

---

## Non-Claims

| Check | Status | Notes |
|-------|--------|-------|
| No bank/lender approval claimed | PASS | |
| No external audit/certification claimed | PASS | |
| No SaaS/enterprise readiness claimed | PASS | |
| Pilot scope limitations communicated to any external recipients | PASS | |

---

## Issue Routing

| Check | Status | Notes |
|-------|--------|-------|
| Issue intake template accessible | PASS | `docs/pilot_issue_intake_template.md` |
| Stale export or draft-run confusion routed as clarification | PASS | |
| Generic path misuse routed as pause trigger | PASS | |

---

## Overall Hygiene Status

| Area | Status |
|------|--------|
| Project/scope confirmation | ✅ PASS |
| Draft/saved/runtime distinction | ✅ PASS |
| Last clean run boundary | ✅ PASS |
| Export artefact purpose | ✅ PASS |
| Audit/reconciliation interpretation | ✅ PASS |
| Generic exclusion | ✅ PASS |
| Stale export risk | ✅ PASS |
| Non-claims | ✅ PASS |
| Issue routing | ✅ PASS |

**Overall: PASS — Export hygiene confirmed.**

---

## Notes

_(Fill in any observations or follow-ups)_

- Date: _______________
- Operator: _______________
- Notes: _______________