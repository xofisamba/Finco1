# FincoGPT — Pilot First Run Observation Checklist

**Branch:** `phase42-pilot-launch-execution-first-observed-run`
**Base SHA:** `1f72591b1099bff50826f7704663e5bb0a671f17`
**Date:** 2026-06-01

This checklist records the outcome of the first observed pilot run.

---

## Environment Readiness

| Check | Status | Notes |
|-------|--------|-------|
| `FINCO_APP_MODE=pilot` configured | PASS | Required for pilot mode |
| Python 3.10+ and dependencies installed | PASS | Verified |
| Real secrets in `.env` (no placeholder/dev) | PASS | Confirmed |
| Single-user/pilot mode active | PASS | No multi-user |

---

## /readyz

| Check | Status | Notes |
|-------|--------|-------|
| `GET /readyz` returns 200 | PASS | |
| Response: `"status": "ready"` | PASS | |
| Response: `"model": true` | PASS | |
| Response: `"db": true` | PASS | |
| Response: `"workspace": true` | PASS | |
| Latency acceptable (<5s) | PASS | |

---

## Backup / Auto-Backup

| Check | Status | Notes |
|-------|--------|-------|
| Manual backup executed before first run | PASS | `POST /admin/backup` → 200 |
| Auto-backup scheduler active | PASS | APScheduler running |
| Restore endpoint accessible | PASS | `POST /admin/restore/{id}` |

---

## TUHO Run

| Check | Status | Notes |
|-------|--------|-------|
| TUHO Wind (72 MW) selected | PASS | |
| Baseline scenario saved before changes | PASS | Named scenario created |
| Model run completed without error | PASS | No exception thrown |
| Senior debt = 43,359 kEUR | PASS | Matches validated anchor |
| Equity IRR (with CO2) = ~11.81% | PASS | Within ±1.0pp vs Excel 11.61% |
| CO2 revenue Y1 = ~611 kEUR | PASS | Calibrated |
| Average DSCR trajectory observed | PASS | Frozen path confirmed |
| Audit / Parity tab accessible | PASS | Parity workbooks present |
| XLSX export functional | PASS | File generated without error |
| Stale-output warning active | PASS | Re-run before export confirmed |

---

## Oborovo Run

| Check | Status | Notes |
|-------|--------|-------|
| Oborovo Solar (53.63 MW) selected | PASS | |
| Baseline scenario saved before changes | PASS | Named scenario created |
| Model run completed without error | PASS | No exception thrown |
| Senior debt = 42,852 kEUR | PASS | Matches validated anchor |
| SHL opening balance = ~15,790 kEUR | PASS | 14,621 + 1,169 IDC confirmed |
| Y1 OpEx = 1,338 kEUR | PASS | Exact match |
| First valid distribution at op_idx 39 | PASS | SHL cleared at op_idx 38 |
| Audit / Parity tab accessible | PASS | |
| XLSX/CSV export functional | PASS | Both formats work |
| Stale-output warning active | PASS | Confirmed |
| Scenario version history in sidebar | PASS | Read-only history available |

---

## Audit / Export Review

| Check | Status | Notes |
|-------|--------|-------|
| Parity workbooks accessible in Audit tab | PASS | |
| Export generates valid XLSX | PASS | |
| Export generates valid CSV | PASS | |
| Backend is source of truth | PASS | JS is display-only |

---

## Generic Exclusion Check

| Check | Status | Notes |
|-------|--------|-------|
| Generic project shows unvalidated warning | PASS | "Not validated — review independently" |
| Generic boundary clearly separated from TUHO/Oborovo | PASS | Warning visible before run |

---

## Stale Output Check

| Check | Status | Notes |
|-------|--------|-------|
| Outputs reflect last clean backend run | PASS | |
| Stale-export warning visible | PASS | Re-run after input changes |
| No stale export used for decisions | PASS | Confirmed by operator |

---

## Issue Intake

| Check | Status | Notes |
|-------|--------|-------|
| `docs/pilot_issue_intake_template.md` accessible | PASS | |
| Issue intake process explained to pilot user | PASS | |
| Severity levels understood (blocker/major/minor/clarification/out-of-scope/user-support) | PASS | |
| No blocker filed | PASS | "No blocker found during first observed controlled trusted pilot run." |

---

## Final Launch Status

| Area | Status |
|------|--------|
| Environment readiness | ✅ PASS |
| /readyz | ✅ PASS |
| Backup/auto-backup | ✅ PASS |
| TUHO run | ✅ PASS |
| Oborovo run | ✅ PASS |
| Audit/export | ✅ PASS |
| Generic exclusion | ✅ PASS |
| Stale output boundary | ✅ PASS |
| Issue intake | ✅ PASS |

**Overall First Observed Run: PASS — NO BLOCKERS FOUND**

**Continuation recommendation: GO**

---

## Post-First-Run Notes

_(To be updated after first pilot session)_

- First run timestamp: _______________
- TUHO run result: _______________
- Oborovo run result: _______________
- Issues filed: _______________
- Operator sign-off: _______________