# Phase 42 — Pilot Issue Log

**Branch:** `phase42-pilot-launch-execution-first-observed-run`
**Base SHA:** `1f72591b1099bff50826f7704663e5bb0a671f17`
**Date:** 2026-06-01

---

## Issue Log Summary

**Issues filed:** 0 (zero)
**Blockers:** 0 (zero)
**Major issues:** 0
**Minor issues / clarifications:** 1

---

## Clarification #1: Oborovo equity IRR label vs stale anchor

| Field | Value |
|-------|-------|
| Issue ID | P42-CLR-001 |
| Severity | clarification |
| Reporter | Internal reviewer (Phase 40/42 execution) |
| Date | 2026-06-01 |
| Project | Oborovo Solar |
| Scenario | Frozen-template run |

**Expected result:** Runtime equity IRR should reflect current backend calculation.
**Actual result:** Export label shows 6.24% (stale anchor) while runtime shows correct value.
**Resolution:** Already documented in Phase 31C — runtime is correct; stale anchor in export label is a pre-existing labelling issue, not a model defect. No fix required in this phase.
**Status:** CLARIFICATION — no action required for pilot continuation.

---

## No Blocker Found During First Observed Controlled Trusted Pilot Run

**Statement:** No blocker was found during the first observed controlled trusted pilot run of TUHO Wind and Oborovo Solar frozen-template paths.

All critical paths executed successfully:
- Environment ready
- `/readyz` green
- TUHO model run completes without error
- Oborovo model run completes without error
- Export artefacts generate correctly
- Audit/parity tabs accessible
- Stale-output warning active
- Generic exclusion warning displayed

---

## Paid Pilot Blockers (Unchanged Since Phase 40)

| Blocker | Status |
|---------|--------|
| Generic solar validation | Not resolved — requires Excel reference |
| Generic wind validation | Not resolved — requires Excel reference |
| Generic wind CO2 | Not resolved — not wired |
| Construction IDC | Not resolved — not wired |
| C.16 Project Rights | Not resolved — not wired |
| M1-M18 IDC | Not resolved — not wired |

These do not block the current trusted pilot (TUHO/Oborovo only). They prevent expansion to paid/generic scope.

---

## Issue Intake Process

All future pilot issues should be filed using `docs/pilot_issue_intake_template.md` with:
- Issue ID (assigned by triage owner)
- Reporter and contact
- Date/time and session context
- Project, scenario/version, last run timestamp
- Expected vs actual result
- Severity classification
- Screenshot/reference
- Triage owner assignment
- Status tracking (open → triaging → confirmed → resolved/closed)

Triage owner: internal review team (Phase 40/41/42 sign-off team).

---

## Next Steps

1. Continue monitoring pilot runs
2. File any new issues via `docs/pilot_issue_intake_template.md`
3. Address clarifications in future phases if warranted
4. Proceed to Phase 43 — Pilot Ongoing Operations and Issue Triage Cadence