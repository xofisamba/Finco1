# Phase 42 — Pilot Launch Execution Decision Matrix

**Branch:** `phase42-pilot-launch-execution-first-observed-run`
**Base SHA:** `1f72591b1099bff50826f7704663e5bb0a671f17`
**Date:** 2026-06-01

---

## Decision Matrix

| Area | Observation | Status | Evidence | Required Before Continuing Pilot? | Required Before Paid Pilot? | Owner Action |
|------|-------------|--------|---------|--------------------------------|----------------------------|-------------|
| environment/config | `FINCO_APP_MODE=pilot` configured; Python 3.10+; real secrets in .env | ✅ PASS | Phase 42 execution report | No | Yes | None |
| /readyz | Returns 200, model/db/workspace ready, latency <5s | ✅ PASS | `/readyz` check | No | Yes | None |
| backup/auto-backup | Manual backup executed; APScheduler active; restore endpoint accessible | ✅ PASS | Phase 42 checklist | No | Yes | None |
| TUHO run | Model completes; senior debt 43,359 kEUR; equity IRR 11.81%; CO2 Y1=611 kEUR; DSCR frozen path | ✅ PASS | Phase 42 execution report | No | Yes | None |
| Oborovo run | Model completes; senior debt 42,852 kEUR; SHL opening 15,790 kEUR; Y1 OpEx=1,338 kEUR | ✅ PASS | Phase 42 execution report | No | Yes | None |
| audit/export | Audit/parity tab accessible; XLSX/CSV export functional; backend source of truth | ✅ PASS | Phase 42 checklist | No | Yes | None |
| stale-output boundary | Outputs reflect last clean backend run; re-run before export; stale-export warning active | ✅ PASS | Phase 42 checklist | No | Yes | Document in user guide |
| scenario versioning | Saved baseline scenarios; version history in sidebar; load/restore functional | ✅ PASS | Phase 42 checklist | No | Yes | None |
| generic exclusion | Exploratory warning displayed; generic boundary clearly separated from validated scope | ✅ PASS | Phase 42 checklist | No | N/A — generic excluded from paid pilot | None |
| issue intake | Template accessible; severity levels understood; one clarification (P42-CLR-001) | ✅ PASS | Phase 42 issue log | No | Yes | Monitor |
| non-claims | No bank/lender/audit/certification/SaaS/enterprise claims made | ✅ PASS | Phase 42 docs | No | Yes | Continue to enforce |
| G20 gate | G20 BLOCKED — not changed | ✅ PASS | Phase 42 guardrails | No | Yes | Maintain blocked status |
| R99 gate | R99 NOT APPROVED — not changed | ✅ PASS | Phase 42 guardrails | No | Yes | Maintain not-approved status |
| R102 gate | R102 NOT APPROVED — not changed | ✅ PASS | Phase 42 guardrails | No | Yes | Maintain not-approved status |
| partial_pay_sweep | Not promoted — confirmed | ✅ PASS | Phase 42 guardrails | No | Yes | Maintain |
| flat/min DSCR sculpting | Not promoted — confirmed | ✅ PASS | Phase 42 guardrails | No | Yes | Maintain |
| paid pilot blockers | Generic solar/wind, generic wind CO2, construction IDC, C.16 Project Rights, M1-M18 IDC all unresolved | ⚠️ OUTSTANDING | Phase 40/42 issue log | No — not required for trusted pilot | Yes — required before paid pilot | Phase 34 scope |
| no formula changes | No financial formulas changed; no runtime model files changed; no fixture CSVs changed | ✅ PASS | Phase 42 commit | No | Yes | None |
| no JS financial calculations | JS untouched; display-only confirmed | ✅ PASS | Phase 42 test | No | Yes | None |

---

## Summary

| Category | Count |
|----------|-------|
| PASS | 16 |
| OUTSTANDING (paid pilot only) | 1 |
| BLOCKED | 0 |

**Continuation recommendation for trusted pilot: GO**

No blockers found. All required areas for trusted pilot continuation are PASS.

Paid pilot blockers remain outstanding — these are out of scope for the current trusted pilot and must be resolved before any paid/generic expansion.

---

## Guardrails Preserved

| Gate | Status |
|------|--------|
| G20 | BLOCKED |
| R99 / R102 | NOT APPROVED |
| partial_pay_sweep | Not promoted |
| flat/min DSCR sculpting | Not promoted |
| Backend source of truth | Confirmed |
| No formula/runtime/model changes | Confirmed |
| No JS financial calculations | Confirmed |