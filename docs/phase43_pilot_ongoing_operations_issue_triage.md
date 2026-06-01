# Phase 43 — Pilot Ongoing Operations and Issue Triage Cadence

**Branch:** `phase43-pilot-ongoing-operations-issue-triage`
**Base SHA:** `07506503e0602e6a8d4bd940be56001b6201906a` (after PR #354 Phase 42 merge)
**Date:** 2026-06-01
**Type / Scope:** Pilot operations, support workflow, issue triage, documentation — no model logic changes

---

## 1. Objective

Define and document the ongoing operating cadence for the controlled trusted pilot now that Phase 42 confirmed the first observed run GO decision.

This phase does **not change** financial formulas, runtime behavior, model outputs, data paths, project factories, fixture CSVs, or any JavaScript financial calculations.

**No formula changes: confirmed.** **No runtime changes: confirmed.** **No model file changes: confirmed.**

---

## 2. Operational Scope

The pilot operates within the following validated scope:

| Feature | Status |
|---------|--------|
| TUHO frozen-template path | ✅ Validated |
| Oborovo frozen-template path | ✅ Validated |
| TUHO CO2 revenue treatment | ✅ Validated |
| Oborovo OpEx | ✅ Validated |
| Senior debt / DSCR / SHL frozen path | ✅ Validated |
| Scenario / export / audit evidence | ✅ Validated |
| Backup / restore and auto-backup | ✅ Active |
| /readyz operational readiness | ✅ Active |
| Single-user / pilot mode | ✅ Active |

---

## 3. Validated Projects

| Project | Validation |
|---------|-----------|
| TUHO Wind (72 MW, Croatia) | ✅ Within tolerance — use for pilot runs |
| Oborovo Solar (53.63 MW, Croatia) | ✅ Within tolerance — use for pilot runs |
| Generic solar | ❌ **NOT validated** — unvalidated, exploratory only, no Excel reference |
| Generic wind | ❌ **NOT validated** — unvalidated, exploratory only, no Excel reference |

---

## 4. Daily / Weekly Pilot Cadence

### Daily (before each session)

| Check | Action |
|-------|--------|
| `/readyz` returns green | Proceed only if green |
| Backup log reviewed | Confirm auto-backup ran overnight |
| Stale-output warning confirmed | User reminded: re-run before export |

### Weekly (every Monday)

| Check | Action |
|-------|--------|
| Environment health | Review logs, confirm no errors |
| Backup verification | Confirm backup files exist and are restorable |
| Issue log review | Check for new issues since last review |
| Scenario hygiene | Confirm old/unused scenarios are archived |
| Export hygiene | Confirm no stale exports are in use |
| Generic boundary review | Confirm no generic path misuse |
| Non-claims review | Confirm no external claims made |
| User support check | Confirm pilot user has no blockers |

---

## 5. Issue Intake Workflow

1. **Pilot user encounters issue** → fills `docs/pilot_issue_intake_template.md`
2. **Operator routes to triage board** → `docs/pilot_issue_triage_board_template.md`
3. **Triage owner assigns severity and owner**
4. **SLA clock starts** (see below)
5. **Resolution or escalation** → logged in issue log

---

## 6. Severity Definitions and Triage SLA

| Severity | Definition | Response SLA | Resolution SLA |
|----------|------------|--------------|---------------|
| **blocker** | Model fails to run or produces invalid outputs | Immediate (within 1h) | Same day |
| **major** | Results are materially wrong vs validated Excel reference | Within 4h | 2 business days |
| **minor** | UI/UX issue,不影响计算 | Next business day | 2 weeks |
| **clarification** | Labelling, documentation, or naming inconsistency | 3 business days | Next sprint |
| **out-of-scope** | Generic path, future feature, not-yet-implemented | Log and defer | N/A |
| **user-support** | How-to, environment, config | Best effort | Per request |

---

## 7. Backup / Restore Checks

| Check | Frequency | Action if Failed |
|-------|-----------|------------------|
| Auto-backup scheduler running | Daily | Restart APScheduler; alert operator |
| Manual backup before first run | Per pilot session | Mandatory before first run of day |
| Backup files exist and readable | Weekly | Alert; do not proceed without confirmed backup |
| Restore endpoint functional | Weekly | Test with a known backup; alert if failed |

---

## 8. /readyz Check Cadence

- **Before each session:** `GET /readyz` must return `200` with `"status": "ready"` and all three `model/db/workspace: true`
- **After any configuration change:** run `/readyz` before continuing
- **If red:** do not run model; check logs; resolve before proceeding

---

## 9. Scenario / Export Hygiene

| Rule | Rationale |
|------|-----------|
| Save a named scenario before changing inputs | Preserves baseline |
| Re-run model after any input change before exporting | Outputs reflect last clean run |
| Never share stale exports | Stale exports may not reflect current inputs |
| Delete or archive unused scenarios monthly | Reduces DB clutter |
| Export to timestamped filenames | Avoids overwriting previous runs |

---

## 10. Escalation Path

1. **Pilot user** → files issue via `docs/pilot_issue_intake_template.md`
2. **Operator** → assigns to triage board, sets severity
3. **Triage owner** → monitors SLA, routes to fix or defers
4. **Blocker issues** → immediate notification to all stakeholders
5. **Pause decision** → see `docs/pilot_pause_escalation_policy.md`

---

## 11. Pilot Continuation Criteria

Pilot can continue if:
- ✅ `/readyz` returns green before each session
- ✅ No blocker-level issues open
- ✅ TUHO and Oborovo runs complete without error
- ✅ No generic path used for external decisions
- ✅ No external claims (bank/lender/audit/certification/SaaS) made
- ✅ Backup schedule running without failure
- ✅ Stale-export misuse has not occurred

---

## 12. Pilot Pause Criteria

Pause pilot use and investigate if:
- 🔴 `/readyz` returns red or incomplete response
- 🔴 Model produces results materially outside validated tolerance
- 🔴 Blocker-level issue filed
- 🔴 Stale exports used for external decisions
- 🔴 Generic solar/wind outputs used for any financial decision
- 🔴 Security or config breach suspected
- 🔴 Backup failure with no known recovery path

See `docs/pilot_pause_escalation_policy.md` for full policy.

---

## 13. Paid Pilot Blockers (Unchanged)

These must be resolved before any paid pilot or generic project expansion:

| Blocker | Status |
|---------|--------|
| Generic solar validation | Not resolved — requires Excel reference |
| Generic wind validation | Not resolved — requires Excel reference |
| Generic wind CO2 | Not resolved — not wired |
| Construction IDC | Not resolved — not wired |
| C.16 Project Rights | Not wired |
| M1-M18 IDC | Not wired |

---

## 14. Guardrails Confirmation

| Gate | Status |
|------|--------|
| G20 | BLOCKED — not changed |
| R99 | NOT APPROVED — not changed |
| R102 | NOT APPROVED — not changed |
| partial_pay_sweep | Not promoted — confirmed |
| flat/min DSCR sculpting | Not promoted — confirmed |
| Backend source of truth | Confirmed — JS is display-only |
| No formula changes | Confirmed — docs/reports/tests only |
| No JS financial calculations | Confirmed — JS untouched |

---

## 15. Recommended Next Phase

**Phase 44 — Pilot Audit Trail Polish and Export Hygiene Enforcement**

Strengthen the audit/export trust surface, formalize stale-export prevention, and confirm all operational controls are documented and active.

---

## 16. Changed Files

| File | Description |
|------|-------------|
| `docs/phase43_pilot_ongoing_operations_issue_triage.md` | This document — operations guide |
| `docs/pilot_issue_triage_board_template.md` | Kanban-style triage board |
| `docs/pilot_operations_weekly_checklist.md` | Weekly operations checklist |
| `docs/pilot_pause_escalation_policy.md` | Pause and escalation policy |
| `docs/phase43_pilot_operations_decision_matrix.md` | Decision matrix |
| `reports/phase43_pilot_operations_summary.json` | JSON summary |
| `tests/test_phase43_pilot_ongoing_operations_issue_triage.py` | Phase 43 tests |