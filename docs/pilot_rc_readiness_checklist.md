# Pilot RC Readiness Checklist

**Branch:** `phase35-pilot-release-candidate-closeout`
**Base SHA:** `048806a4bcc322c078ffc7d3e5de0d24b310fbac`
**Date:** 2026-05-31

---

## Pre-Flight Checklist

Complete all items before giving pilot access to an external user.

---

### Model Validation

| # | Check Item | Expected | Pass/Fail | Notes |
|---|-----------|----------|-----------|-------|
| 1 | TUHO frozen template runs end-to-end | Debt=43,359kEUR, IRR≈11.81%, DSCR≈1.45 | _____ | |
| 2 | Oborovo frozen template runs end-to-end | Debt=42,852kEUR, IRR≈6.24%, DSCR≈1.15 | _____ | |
| 3 | TUHO CO2 revenue appears in output | Y1 CO2 ≈ 611 kEUR | _____ | |
| 4 | Oborovo OpEx matches Excel | Y1 OpEx = 1,338 kEUR | _____ | |
| 5 | Oborovo distribution starts at year 20 | Period 41, bullet SHL lockup | _____ | |
| 6 | TUHO SHL sweep works | PIK+sweep excess CF | _____ | |
| 7 | No runtime exceptions in model run | Clean output, no errors | _____ | |

---

### Project Scope

| # | Check Item | Pass/Fail |
|---|-----------|-----------|
| 8 | TUHO and Oborovo templates accessible | _____ |
| 9 | Generic solar/wind templates NOT promoted | _____ |
| 10 | TUHO CO2 field wired and visible | _____ |

---

### User Workflow

| # | Check Item | Pass/Fail |
|---|-----------|-----------|
| 11 | User can create a new scenario | _____ |
| 12 | User can save a scenario | _____ |
| 13 | User can load a saved scenario | _____ |
| 14 | User can view scenario version history in sidebar | _____ |
| 15 | User sees stale-runtime warning when draft unsaved | _____ |
| 16 | Draft edits do not affect Run until saved | _____ |

---

### Scenario Save/Load/Versioning

| # | Check Item | Pass/Fail |
|---|-----------|-----------|
| 17 | save_scenario() creates new row (not overwriting) | _____ |
| 18 | Previous versions remain accessible after Save | _____ |
| 19 | active_scenario_id correctly updated after Select | _____ |
| 20 | scenario_history shows updated_at ordering | _____ |

---

### Run/Export Workflow

| # | Check Item | Pass/Fail |
|---|-----------|-----------|
| 21 | Run Model produces expected outputs | _____ |
| 22 | Excel export generates correct file | _____ |
| 23 | last_run_summary stored after run | _____ |
| 24 | Runtime output correct despite draft edits | _____ |

---

### Backup/Restore

| # | Check Item | Pass/Fail |
|---|-----------|-----------|
| 25 | Manual backup can be triggered | _____ |
| 26 | Backup file created in data/ directory | _____ |
| 27 | Restore dangerous — documentation confirmed | _____ |
| 28 | Auto-backup schedule is active | _____ |
| 29 | Auto-backup does not affect versioning semantics | _____ |

---

### Deployment / Readiness Endpoint

| # | Check Item | Pass/Fail |
|---|-----------|-----------|
| 30 | `/readyz` returns model_ready: true | _____ |
| 31 | `/readyz` returns db_ready: true | _____ |
| 32 | `/readyz` returns workspace_ready: true | _____ |
| 33 | Startup completes without errors | _____ |

---

### Security / App Mode

| # | Check Item | Pass/Fail |
|---|-----------|-----------|
| 34 | `FINCO_APP_MODE=pilot` is documented | _____ |
| 35 | Single-user mode is default | _____ |
| 36 | No multi-user auth implemented (expected) | _____ |
| 37 | No RBAC implemented (expected) | _____ |

---

### Limitations and Non-Claims

| # | Check Item | Pass/Fail |
|---|-----------|-----------|
| 38 | Pilot user briefed: G20 status is BLOCKED | _____ |
| 39 | Pilot user briefed: R99/R102 status is NOT APPROVED | _____ |
| 40 | Pilot user briefed: no bank/lender/audit/certification claims | _____ |
| 41 | Pilot user understands generic solar/wind is unvalidated | _____ |
| 42 | Pilot user understands CAPEX sensitivity is diagnostic only | _____ |
| 43 | Pilot user understands equity IRR ~6.24% for Oborovo (not ~9.88%) | _____ |
| 44 | Pilot user briefed: do not rely on generic project outputs | _____ |

---

### Known Exclusions

| # | Check Item | Pass/Fail |
|---|-----------|-----------|
| 45 | Construction IDC not wired — pilot user understands | _____ |
| 46 | M1-M18 not wired — pilot user understands | _____ |
| 47 | C.16 Project Rights not wired — pilot user understands | _____ |
| 48 | Live sculpting not promoted — pilot user understands | _____ |
| 49 | Multi-user/RBAC/SSO not implemented — expected | _____ |
| 50 | SaaS/enterprise not ready — expected | _____ |

---

### Pilot Support Process

| # | Check Item | Pass/Fail |
|---|-----------|-----------|
| 51 | Backup strategy documented and tested | _____ |
| 52 | Restore procedure documented (dangerous — backup first) | _____ |
| 53 | Issue escalation path known | _____ |

---

### Go / No-Go Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Model Owner | | | |
| Pilot Lead | | | |
| Technical Review | | | |

**Decision: GO / NO-GO**

Notes: