# Phase 41 — Pilot Launch Documentation and Handoff Checklist

**Branch:** `phase41-pilot-launch-documentation-handoff-checklist`
**Base SHA:** `844b0c82b247391a605a2ba76a385611c116d3f9` (after PR #352 Phase 40 merge)
**Date:** 2026-06-01
**Type / Scope:** Documentation, launch readiness, handoff — no model logic changes

---

## 1. Objective

Prepare the final controlled trusted pilot launch documentation and handoff checklist now that Phase 40 merged the **Trusted Pilot: GO** decision.

This phase does **not change** financial formulas, runtime behavior, model outputs, data paths, project factories, fixture CSVs, senior debt sizing logic, DSCR/sculpting logic, SHL/distribution logic, or any JavaScript financial calculations.

**No formula changes: confirmed.** **No runtime changes: confirmed.** **No model file changes: confirmed.**

---

## 2. Trusted Pilot GO Basis

Phase 40 reviewer run concluded:

- **Trusted Pilot: GO**
- No blocker found for controlled trusted pilot within TUHO/Oborovo frozen-template scope
- One clarification only: Oborovo equity IRR runtime vs stale anchor, already documented in Phase 31C
- Generic solar/wind remain exploratory and unvalidated
- Paid pilot blockers remain: generic validation, generic wind CO2, construction IDC, C.16 Project Rights, M1-M18 IDC

Evidence: `docs/phase40_reviewer_run_execution_outcome.md`, `reports/phase40_reviewer_run_summary.json`

---

## 3. Validated Launch Scope

The following are validated within documented tolerance and approved for pilot use:

| Feature | Validation Evidence |
|---------|---------------------|
| TUHO frozen-template path | PRs #27/#27B, Phase 29C |
| Oborovo frozen-template path | PRs #27/#27B, Phase 31/31B/31C |
| TUHO CO2 revenue treatment | Phase 29A, PR #29A — Y1 ≈ 611 kEUR |
| Oborovo OpEx | Phase 31, PR #341 — Y1 = 1,338 kEUR |
| Senior debt / DSCR / SHL frozen path | Phase 23 series, PRs #23O/#276 |
| Scenario / export / audit evidence | Phase 27B export tests |
| Backup / restore and auto-backup | Phase 24F, PR #24F / Phase 24F1, PR #24F1 |
| /readyz operational readiness | Phase 26D, PR #26D |
| Single-user / pilot mode | Phase 26B, PR #26B |

---

## 4. Excluded from Pilot Scope

The following are **not validated** and **not approved** for pilot use:

| Excluded Feature | Reason |
|-----------------|--------|
| Generic solar / wind validation | No Excel reference — exploratory only |
| Generic wind CO2 | Not validated |
| Construction IDC | Not wired |
| C.16 Project Rights | Not wired |
| M1-M18 IDC | Not wired |
| Live sculpting / debt re-sizing | Not promoted — frozen path only |
| Multi-user / RBAC / SSO | Single-user mode only |
| SaaS / enterprise readiness | Not claimed, not applicable |
| Bank / lender / external audit / certification approval | Not claimed, not applicable |

---

## 5. Operator Responsibilities

- Deploy using `FINCO_APP_MODE=pilot`
- Run `/readyz` before each session to confirm model, DB, and workspace are ready
- Perform a manual backup before first pilot run: `POST /admin/backup`
- Verify auto-backup scheduler is running (check logs)
- Brief pilot user on validated scope before first use
- Route any issues using `docs/pilot_issue_intake_template.md`
- Do not upgrade model version during active pilot without approval

---

## 6. User Responsibilities

- Use TUHO Wind or Oborovo Solar for validated results
- Generic / new projects are for exploration only — do not treat as validated
- Save a named scenario before changing inputs
- Export results after each successful run
- Report issues using the issue intake template with a screenshot and last run timestamp
- Do not refresh stale exports — always re-run before exporting

---

## 7. Expected Pilot Workflow

1. Operator deploys and runs `/readyz` — confirms green
2. Operator takes manual backup
3. Operator briefs pilot user on scope and limitations
4. Pilot user opens TUHO Wind or Oborovo Solar project
5. Pilot user reviews inputs and saves a baseline scenario
6. Pilot user adjusts inputs and runs the model
7. Pilot user reviews KPIs, DSCR trajectory, and distribution schedule
8. Pilot user exports results (XLSX or CSV)
9. Pilot user files issue if any discrepancy vs expected results

---

## 8. Issue Routing

All pilot issues go to `docs/pilot_issue_intake_template.md`.

Triage owner: internal reviewer (Phase 40 sign-off team).

| Severity | Definition | Response |
|----------|------------|----------|
| blocker | Prevents model from running | Immediate |
| major | Results in materially wrong outputs | Same day |
| minor | UI/UX issue,不影响计算 | Next sprint |
| clarification | Labelling or documentation gap | Next sprint |
| out-of-scope | Generic path / future feature | Log and defer |
| user-support | How-to, config, env | Best effort |

---

## 9. Backup / Restore Expectations

- **Auto-backup:** Runs on schedule via APScheduler (Phase 24F1). Check `/admin/backup` endpoint and logs.
- **Manual backup:** `POST /admin/backup` before first pilot run.
- **Restore:** `POST /admin/restore/{backup_id}` — overwrites current DB. Always backup before restoring.
- **Scope:** DB state only. Scenario versions are preserved via the versioning API.

---

## 10. /readyz Use

`GET /readyz` returns `{"status": "ready", "model": true, "db": true, "workspace": true}` when all three are available.

- Run before each session
- Green = safe to proceed
- Red = do not run model; check logs

---

## 11. Non-Claims (Must Never Be Made)

FincoGPT outputs must never be represented as:

- ✅ **Allowed:** Internal pilot evidence, parity-validated backend calculations within documented tolerance
- ❌ **Never claim:** Bank approval, lender approval, external audit certification, SaaS-ready, enterprise-ready, production-ready, compliant with any financial regulation

---

## 12. Guardrails

The following remain in their current state — do not promote, enable, or claim as validated:

| Gate | Status |
|------|--------|
| G20 | BLOCKED |
| R99 | NOT APPROVED |
| R102 | NOT APPROVED |
| partial_pay_sweep | Not promoted |
| flat / min DSCR sculpting | Not promoted |
| Backend source of truth | Confirmed |

---

## 13. Recommended Next Phase

**Phase 42 — Pilot Launch Execution**

Once Phase 41 docs are merged, proceed to:

1. Final pre-launch environment check
2. Pilot user onboarding session
3. First live model run under observation
4. Issue triage cadence establishment

Generic validation (Phase 34 scope) remains a prerequisite for paid pilot expansion.

---

## 14. Changed Files

| File | Description |
|------|-------------|
| `docs/phase41_pilot_launch_documentation_handoff.md` | This document — launch overview |
| `docs/pilot_launch_handoff_checklist.md` | Operator pre-launch checklist |
| `docs/pilot_scope_confirmation_note.md` | Shareable pilot scope note |
| `docs/pilot_issue_intake_template.md` | Issue intake form |
| `docs/phase41_pilot_launch_readiness_matrix.md` | Launch readiness matrix |
| `reports/phase41_pilot_launch_readiness_summary.json` | JSON summary |
| `docs/pilot_user_guide.md` | Navigation update |
| `docs/validation_pack_index.md` | Navigation update |
| `docs/deployment_runbook.md` | Navigation update |
| `tests/test_phase41_pilot_launch_documentation_handoff.py` | Phase 41 tests |