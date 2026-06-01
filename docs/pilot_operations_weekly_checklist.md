# FincoGPT — Pilot Operations Weekly Checklist

**Branch:** `phase43-pilot-ongoing-operations-issue-triage`
**Base SHA:** `07506503e0602e6a8d4bd940be56001b6201906a`
**Date:** 2026-06-01

Complete this checklist every Monday (or start of each operational week).

---

## Environment Health

| Check | Status | Notes |
|-------|--------|-------|
| `FINCO_APP_MODE=pilot` configured | PASS | Required for pilot mode |
| Python 3.10+ running | PASS | |
| Dependencies installed from `constraints.txt` | PASS | No unexpected changes |
| `.env` contains real secrets (no placeholder/dev) | PASS | |
| No unexpected logs or errors in recent sessions | PASS | Review log output |
| Disk space sufficient for backup and scenarios | PASS | |

---

## /readyz

| Check | Status | Notes |
|-------|--------|-------|
| `GET /readyz` returns 200 | PASS | |
| Response: `"status": "ready"` | PASS | |
| Response: `"model": true` | PASS | |
| Response: `"db": true` | PASS | |
| Response: `"workspace": true` | PASS | |
| Latency < 5 seconds | PASS | |
| `/readyz` called before first session of week | PASS | |

---

## Backup / Auto-Backup

| Check | Status | Notes |
|-------|--------|-------|
| APScheduler auto-backup running | PASS | Check logs |
| Backup files exist and readable | PASS | Confirm auto-backup created file |
| Restore endpoint functional: `POST /admin/restore/{id}` | PASS | Test with a known backup if possible |
| Manual backup executed before first run this week | PASS | |
| Backup directory has no corruption | PASS | Files readable |

---

## Scenario / Version Hygiene

| Check | Status | Notes |
|-------|--------|-------|
| Old/unused scenarios identified | PASS | |
| Unused scenarios archived or deleted | PASS | Reduces DB clutter |
| Named scenarios have descriptive names | PASS | |
| TUHO and Oborovo baseline scenarios confirmed saved | PASS | |
| Scenario version history accessible | PASS | |

---

## Export Hygiene

| Check | Status | Notes |
|-------|--------|-------|
| No stale exports in active use | PASS | |
| Exports use timestamped filenames | PASS | |
| User reminded: re-run after input changes before export | PASS | |
| Parity workbooks accessible for TUHO and Oborovo | PASS | |
| No exports generated from stale runs | PASS | |

---

## Issue Log Review

| Check | Status | Notes |
|-------|--------|-------|
| No open blocker issues | PASS | |
| No open major issues | PASS | |
| P42-CLR-001 (Oborovo equity IRR label) still accepted/known limitation | PASS | No change; documented in Phase 31C |
| Any new issues filed this week routed to triage board | PASS | |
| Triage SLA met for all open issues | PASS | |

---

## Generic Boundary Review

| Check | Status | Notes |
|-------|--------|-------|
| TUHO and Oborovo are the only projects used for pilot decisions | PASS | |
| No generic solar/wind outputs used for financial decisions | PASS | |
| Exploratory warning displayed when generic project selected | PASS | |
| Generic boundary documented and communicated to pilot user | PASS | |

---

## Non-Claims Review

| Check | Status | Notes |
|-------|--------|-------|
| No external claims made this week (bank/lender/audit/certification/SaaS) | PASS | |
| Pilot remains internal — not represented as approved financial product | PASS | |
| User briefed on non-claims if any ambiguity arose | PASS | |
| Non-claims documented in scope confirmation note | PASS | |

---

## User Support Check

| Check | Status | Notes |
|-------|--------|-------|
| Pilot user has no active blockers | PASS | |
| How-to questions resolved or routed | PASS | |
| Environment or config issues resolved | PASS | |
| Pilot user understands stale-output boundary | PASS | |
| Pilot user knows how to file issue via intake template | PASS | |

---

## Continuation / Pause Decision

| Criterion | Status |
|-----------|--------|
| `/readyz` green | ✅ PASS |
| No open blocker issues | ✅ PASS |
| TUHO/Oborovo runs functional | ✅ PASS |
| Backup/auto-backup operational | ✅ PASS |
| No generic path misuse for decisions | ✅ PASS |
| No external claims made | ✅ PASS |
| No security/config concerns | ✅ PASS |

**Weekly Decision: CONTINUE / PAUSE**

- **CONTINUE:** All checks PASS — pilot continues normally
- **PAUSE:** Any BLOCKED item — see `docs/pilot_pause_escalation_policy.md`

---

## Notes for This Week

_(Fill in any observations, issues, or follow-ups)_

- Date: _______________
- Operator: _______________
- Status: CONTINUE / PAUSE
- Notes: _______________