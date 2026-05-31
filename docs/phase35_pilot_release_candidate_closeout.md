# Phase 35 — Pilot Release Candidate Closeout

**Branch:** `phase35-pilot-release-candidate-closeout`
**Base SHA:** `048806a4bcc322c078ffc7d3e5de0d24b310fbac` (after PR #345 Phase 33)
**Date:** 2026-05-31
**Status:** Release / readiness / documentation — no runtime formula changes

---

## 1. Release Candidate Overview

**Name:** Trusted Pilot Release Candidate 1.0
**Base SHA:** `048806a4bcc322c078ffc7d3e5de0d24b310fbac`
**Type:** Trusted Pilot — Single-user operational posture

This document constitutes the formal closeout package for the Trusted Pilot Release Candidate. It defines exactly what is included, validated, diagnostic-only, and excluded from the pilot scope.

---

## 2. Phase Series Recap (Pilot-Applicable)

| Phase | Finding | Status |
|-------|---------|--------|
| Phase 27 | Frozen-path validation pack and stakeholder-ready package | ✅ Merged |
| Phase 27B | Validation pack export/presentation | ✅ Merged |
| Phase 28 | Generic project path = unvalidated/exploratory | ✅ Merged |
| Phase 29A | TUHO CO2 revenue deep-dive, Y1=611 kEUR | ✅ Merged |
| Phase 29B | Oborovo CAPEX sensitivity = diagnostic-only | ✅ Merged |
| Phase 29C | Post-validation closeout and Claude review prep | ✅ Merged |
| Phase 31 | Oborovo OpEx gap = false alarm, Y1=1,338 kEUR ✅ | ✅ Merged |
| Phase 31B | CFADS bridge anchor sign fixed | ✅ Merged |
| Phase 31C | Oborovo equity IRR/PPA/SHL = stale anchors / expected architecture | ✅ Merged |
| Phase 32 | Scenario persistence/versioning already exists | ✅ Merged |
| Phase 33 | Scenario version history UI wired to sidebar | ✅ Merged |

---

## 3. Validated Pilot Scope

### 3.1 TUHO Frozen Template Path — ✅ VALIDATED
- **Senior debt:** 43,359 kEUR ✅ (exact match Excel)
- **Equity IRR:** 11.81% vs Excel 11.61% ✅ (within ±1.0pp)
- **Project IRR:** 10.46% vs Excel 9.47% ⚠️ (+0.99pp, noted)
- **Avg DSCR:** 1.682 vs Excel 1.451 ⚠️ (+0.231, noted)
- **CO2 revenue:** Y1=611 kEUR ✅ calibrated
- **SHL:** Pik_then_sweep, rate=7.93%, opening=32,704 kEUR ✅

### 3.2 Oborovo Frozen Template Path — ✅ VALIDATED
- **Senior debt:** 42,852 kEUR ✅ (within ±1% Excel)
- **Project IRR:** 8.09% vs Excel 7.96% ✅ (within ±0.5pp)
- **Avg DSCR:** 1.150 vs Excel 1.147 ✅ (within ±0.05)
- **OpEx:** Y1=1,338 kEUR ✅ (matches Excel, false alarm resolved)
- **CO2:** treated as per Excel
- **Equity IRR:** 6.24% (runtime) — stale anchor ~9.88% from pre-Phase 23O era; runtime is correct under current definitions

### 3.3 TUHO CO2 Revenue — ✅ VALIDATED
- `co2_enabled=True`, `co2_price=4.191 EUR/MWh`
- Y1 CO2 revenue ≈ 611 kEUR ✅
- CO2 revenue correctly flows through to equity IRR

### 3.4 Oborovo OpEx — ✅ VALIDATED
- Y1 OpEx = 1,338 kEUR ✅ (confirmed exact match Excel)
- No double-counting in sub-line items

### 3.5 Senior Debt / SHL / Distribution Lock-up — ✅ VALIDATED
- Oborovo 20-year bullet SHL: `shl_balance=15,790 kEUR` unchanged in P4 ✅
- Distribution correctly blocked while `shl_balance > 0` ✅ (Phase 23O)
- First distribution at period 41 (year 20) ✅
- TUHO SHL pik_then_sweep: correctly sweeps excess CF ✅

### 3.6 Scenario Persistence/Versioning — ✅ VALIDATED (Phase 32/33)
- Stable `scenario_id` (UUID hex, immutable) ✅
- `created_at` / `updated_at` timestamps ✅
- Named scenario snapshots ✅
- Non-destructive saves (INSERT-only) ✅
- Draft/saved/runtime distinction ✅
- Scenario version history UI in sidebar ✅

---

## 4. Diagnostic-Only Scope

### 4.1 Oborovo CAPEX Sensitivity
- **Status:** Diagnostic-only — not Excel-validated beyond base case
- Base case Oborovo CAPEX is validated; sensitivity scenarios are for internal exploration only
- Do NOT use CAPEX sensitivity outputs as validated financial projections

### 4.2 Oborovo Equity IRR Runtime Value (6.24%)
- Runtime equity IRR = 6.24% is **correct under current definitions**
- ~9.88% anchor in older documentation is **stale** (pre-Phase 23O)
- Classification: expected under bullet SHL architecture + combined equity method
- Not a defect — architecture difference, not runtime error

### 4.3 Oborovo SHL Sweep at P4
- `shl_sweep_keur = 0.00` at P4 is **correct** for bullet SHL
- 340.54 anchor in CFADS bridge is an **Excel artifact** (mislabeled row)
- Classification: expected under bullet SHL architecture

---

## 5. Excluded / Unvalidated Scope

The following are **NOT included** in the Trusted Pilot RC and must not be relied upon:

| Feature | Reason |
|---------|--------|
| Generic solar/wind | Unvalidated — exploratory only (Phase 28) |
| Generic wind CO2 | Unvalidated |
| Construction IDC / M1-M18 runtime | Not wired — C.16 not implemented |
| Live sculpting / debt re-sizing | Not promoted — frozen path validated only |
| C.16 Project Rights | Not wired |
| Multi-user auth / RBAC | Not implemented — single-user pilot mode |
| SSO/OAuth/SAML | Not implemented |
| Multi-tenancy | Not implemented |
| Billing / subscription | Not implemented |
| Enterprise audit logs | Not implemented |
| SaaS-ready / enterprise-ready | Not claimed — and not true |
| Bank/lender/external audit/certification | Not claimed — and not true |

---

## 6. Technical Readiness

### 6.1 Model Layer
- **Backend authoritative:** ✅ All financial calculations run in Python backend
- **No JS financial calculations:** ✅ No client-side financial logic
- **No formula changes in this RC:** ✅ Frozen-path formulas are locked

### 6.2 Persistence Layer
- **SQLite local:** ✅
- **Scenario versioning:** ✅ (Phase 32/33)
- **Auto-backup:** ✅ (APScheduler, Phase 24F1)
- **Backup/restore:** ✅ (Phase 24F)

### 6.3 Observability
- **`/readyz` endpoint:** ✅ Exposes model_ready, db_ready, workspace_ready
- **Auto-backup scheduling:** ✅

### 6.4 Security
- **Single-user mode:** ✅ `FINCO_APP_MODE=pilot`
- **No multi-user auth:** N/A for pilot
- **RBAC:** Not implemented (out of scope)

---

## 7. User Workflow Readiness

### 7.1 Allowed Workflows
- Create and run TUHO frozen template ✅
- Create and run Oborovo frozen template ✅
- Save scenario snapshots ✅
- Load and inspect saved scenarios ✅
- View scenario version history ✅
- Compare two scenarios ✅
- Export model outputs ✅
- Take and restore backups ✅

### 7.2 Restricted Workflows
- Generic solar/wind: exploratory only — do not present as validated
- CAPEX sensitivity: diagnostic only — do not present as validated projections
- Live sculpting: not promoted — frozen path only
- Multi-user collaboration: not available

---

## 8. Data Safety / Backup Posture

- **Local SQLite DB:** `data/finco_runs.db`
- **Auto-backup:** Configured via `schedule_backup()` in `app/persistence/backup_restore.py`
- **Recommendation:** Take a manual backup before any restore operation
- **Restore dangerous:** `restore(backup_path)` overwrites live DB — document this

---

## 9. Go / No-Go Checklist

Before giving access to an external trusted pilot user, confirm:

- [ ] TUHO frozen template runs and produces expected debt/IRR/DSCR outputs
- [ ] Oborovo frozen template runs and produces expected debt/IRR/DSCR outputs
- [ ] Scenario can be saved and re-loaded with correct inputs
- [ ] Scenario version history UI is visible in sidebar
- [ ] Backup has been taken and is accessible
- [ ] `/readyz` returns all green
- [ ] Pilot user has read the limitations section
- [ ] Pilot user understands generic solar/wind is unvalidated
- [ ] Pilot user understands CAPEX sensitivity is diagnostic only
- [ ] Pilot user understands G20/R99/R102 status
- [ ] Pilot user is not given bank/lender/audit/certification claims

---

## 10. Recommended Pilot Usage Rules

1. **Use TUHO and Oborovo frozen templates only** for validated financial modeling
2. **Do not use generic solar/wind** for external financial decisions
3. **Do not claim bank/lender/external audit/certification** status
4. **Always re-run after draft edits** before relying on exports
5. **Use Save before Run** to create versioned snapshots
6. **Take manual backup** before any restore operation
7. **Check `/readyz`** before starting a session
8. **Monitor auto-backup** logs to confirm backups are running

---

## 11. Recommended Next Phases

| Phase | Priority | Description |
|-------|----------|-------------|
| Phase 34 | 🔜 | Generic Project Path Full Validation |
| Phase 36 | 🔜 | Pilot User Onboarding Guide |
| Phase 37 | 🔜 | Excel Export Audit Trail Enhancement |

---

## 12. Guardrails

- ✅ No financial formula changes
- ✅ No runtime calculations
- ✅ No model output changes
- ✅ No project factory changes
- ✅ No fixture CSVs changed
- ✅ No TUHO/Oborovo validation behavior changes
- ✅ No senior debt sizing logic changes
- ✅ No DSCR/sculpting logic changes
- ✅ No SHL/distribution logic changes
- ✅ No Revenue/OPEX/CAPEX/Tax formula changes
- ✅ No JS financial calculations added
- ✅ No schema migrations
- ✅ No new endpoints
- ✅ G20 BLOCKED (unchanged)
- ✅ R99/R102 NOT APPROVED (unchanged)
- ✅ partial_pay_sweep not promoted
- ✅ flat/min DSCR sculpting not promoted
- ✅ Backend remains source of truth
- ✅ No lender/bank/audit/SaaS/certification claims

---

## 13. Manifest Decision

**JSON manifest skipped.** Closeout doc and scope matrix provide sufficient traceability. JSON manifest would add maintenance burden without corresponding benefit at this stage. Decision documented here.

**Phase 35D fix: NOT REQUIRED** — release/documentation only.