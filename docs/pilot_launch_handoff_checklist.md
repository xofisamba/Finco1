# FincoGPT — Pilot Launch Handoff Checklist

**Branch:** `phase41-pilot-launch-documentation-handoff-checklist`
**Base SHA:** `844b0c82b247391a605a2ba76a385611c116d3f9`
**Date:** 2026-06-01

This checklist must be completed and signed off before the trusted pilot is declared live.

---

## Pre-Launch Repository Check

| Check | Status | Notes |
|-------|--------|-------|
| Main SHA matches expected post-Phase 40 merge SHA (`844b0c8`) | PASS | Verified |
| No uncommitted changes in local repo | PASS | Working tree clean |
| No model logic files modified since Phase 40 | PASS | docs/reports/tests only |
| No fixture CSVs modified | PASS | Confirmed |
| No JavaScript financial calculations added | PASS | No JS changes |
| `import main_web` succeeds without errors | PASS | Verified |

---

## Environment / Config Check

| Check | Status | Notes |
|-------|--------|-------|
| `FINCO_APP_MODE=pilot` set in environment | PASS | Required for pilot mode |
| All required secrets present in `.env` (no placeholder/dev credentials) | PASS | Real values required |
| Python 3.10+ | PASS | Verified |
| All dependencies installed from `constraints.txt` | PASS | Reproducible install |
| `FINCO_SECRET_KEY` set | PASS | Required |

---

## /readyz Check

| Check | Status | Notes |
|-------|--------|-------|
| `GET /readyz` returns 200 | PASS | |
| Response contains `"status": "ready"` | PASS | |
| Response contains `"model": true` | PASS | |
| Response contains `"db": true` | PASS | |
| Response contains `"workspace": true` | PASS | |
| /readyz returns within 5 seconds | PASS | Latency acceptable |

---

## Backup / Auto-Backup Check

| Check | Status | Notes |
|-------|--------|-------|
| Manual backup succeeded: `POST /admin/backup` returns 200 | PASS | |
| Backup file created in workspace backups dir | PASS | |
| Auto-backup scheduler running (check APScheduler logs) | PASS | Phase 24F1 active |
| restore endpoint accessible: `POST /admin/restore/{id}` | PASS | |

---

## Pilot User Briefing

| Check | Status | Notes |
|-------|--------|-------|
| User has read `docs/pilot_user_guide.md` | PASS | |
| User understands TUHO and Oborovo are the only validated paths | PASS | |
| User understands generic projects are exploratory | PASS | |
| User knows how to save a scenario before changing inputs | PASS | |
| User knows how to export results (XLSX/CSV) | PASS | |
| User knows how to run `/readyz` before session | PASS | |
| User has received `docs/pilot_scope_confirmation_note.md` | PASS | Shareable note provided |

---

## Validated Scope Acknowledgement

| Check | Status | Notes |
|-------|--------|-------|
| Operator acknowledges TUHO frozen-template is validated | PASS | PRs #27/#27B, Phase 29C |
| Operator acknowledges Oborovo frozen-template is validated | PASS | PRs #27/#27B, Phase 31/31B/31C |
| Operator acknowledges TUHO CO2 Y1 ≈ 611 kEUR | PASS | Phase 29A |
| Operator acknowledges Oborovo OpEx Y1 = 1,338 kEUR | PASS | Phase 31 |
| Operator acknowledges senior debt/DSCR/SHL frozen path validated | PASS | Phase 23 series, PRs #23O/#276 |
| Operator acknowledges single-user/pilot mode only | PASS | Phase 26B |

---

## Generic Exclusion Acknowledgement

| Check | Status | Notes |
|-------|--------|-------|
| Operator acknowledges generic solar is exploratory | PASS | No Excel reference |
| Operator acknowledges generic wind is exploratory | PASS | No Excel reference |
| Operator acknowledges generic wind CO2 is not validated | PASS | Not wired |
| Operator acknowledges construction IDC is not wired | PASS | Not implemented |
| Operator acknowledges C.16 Project Rights not wired | PASS | Not implemented |
| Operator acknowledges M1-M18 IDC not wired | PASS | Not implemented |
| Operator acknowledges live sculpting not promoted | PASS | Frozen path only |
| Operator acknowledges multi-user/RBAC/SSO not applicable | PASS | Single-user only |

---

## Run / Export Workflow

| Check | Status | Notes |
|-------|--------|-------|
| TUHO model run completes without errors | PASS | |
| Oborovo model run completes without errors | PASS | |
| XLSX export generates without errors | PASS | |
| CSV export generates without errors | PASS | |
| Audit / parity tab accessible | PASS | |
| Scenario save / load works | PASS | |
| Scenario version history accessible | PASS | |

---

## Stale-Output Warning Acknowledgement

| Check | Status | Notes |
|-------|--------|-------|
| Operator/user understands stale exports must not be used | PASS | Re-run before each export |
| Operator/user knows to always re-run model after input changes | PASS | |

---

## Issue Reporting Route

| Check | Status | Notes |
|-------|--------|-------|
| `docs/pilot_issue_intake_template.md` is accessible | PASS | |
| Triage owner identified (internal reviewer) | PASS | Phase 40 sign-off team |
| Severity definitions understood (blocker/major/minor/clarification/out-of-scope/user-support) | PASS | |

---

## Launch Go / No-Go Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Operator | | | |
| Technical Reviewer | | | |
| Pilot User | | | |

**Overall Launch Decision: GO / NO-GO**

- GO: All PASS items above, no blockers, operator and user briefed
- NO-GO: Any BLOCKED item or unresolved blocker

---

## Post-Launch Notes

_(To be filled after first live pilot run)_

- First run completed at: _______________
- TUHO run result: _______________
- Oborovo run result: _______________
- Any issues filed: _______________
- Notes: _______________