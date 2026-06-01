# FincoGPT — Pilot Pause and Escalation Policy

**Branch:** `phase43-pilot-ongoing-operations-issue-triage`
**Base SHA:** `07506503e0602e6a8d4bd940be56001b6201906a`
**Date:** 2026-06-01

---

## When to Pause Pilot Use

Pause pilot use immediately if any of the following are observed. Do not continue until the issue is investigated and resolved.

### 1. Operational Blockers

| Trigger | Description |
|---------|-------------|
| `/readyz` returns red | Model, DB, or workspace not ready |
| APScheduler backup failure | No successful backup in >24h and no manual backup |
| Database corruption suspected | Restore endpoint returns error |
| Security breach suspected | Unauthorized access or config change |

### 2. Model Discrepancy

| Trigger | Description |
|---------|-------------|
| TUHO/Oborovo outputs outside tolerance | Senior debt, equity IRR, DSCR materially outside validated range |
| Runtime exception on known-validated project | Model fails on TUHO/Oborovo without clear input change |
| Unexpected NaN or infinity in outputs | Numerical instability detected |

### 3. Stale / Export Misuse

| Trigger | Description |
|---------|-------------|
| Stale export used for external decision | Export from old run used without re-run |
| Re-run skipped before export | Input changed but model not re-run before exporting |
| Export shared externally without re-run | Stale outputs shared outside team |

### 4. Generic Path Misuse

| Trigger | Description |
|---------|-------------|
| Generic solar outputs used for financial decision | Exploratory outputs treated as validated |
| Generic wind outputs used for financial decision | Exploratory outputs treated as validated |
| Generic outputs represented as validated | Claims of Excel parity on non-validated path |
| Generic CO2 revenue used in decision | Not wired/validated — cannot be used |

### 5. External Claims

| Trigger | Description |
|---------|-------------|
| Pilot outputs represented as bank approval | Claims of lender or financing approval |
| Pilot outputs represented as certified audit | Claims of external certification |
| Pilot represented as SaaS-ready or enterprise | Claims beyond internal pilot scope |

### 6. Configuration / Environment

| Trigger | Description |
|---------|-------------|
| `FINCO_APP_MODE` changed without review | Environment change may affect model behavior |
| Secrets rotated without backup | Configuration change without recovery plan |
| Upgrade performed during active pilot | Version change without test validation |

---

## Who Decides to Resume

| Scenario | Decision Maker |
|----------|---------------|
| Operational blocker | Operator + technical reviewer |
| Model discrepancy | Technical reviewer + sign-off team |
| Stale/export misuse | Operator |
| Generic path misuse | Operator + pilot user |
| External claims | Operator + sign-off team |
| Config/environment | Technical reviewer |

---

## What Evidence Is Required to Resume

Before resuming after a pause, the following must be confirmed:

### Operational Resume

- ✅ `/readyz` returns green with model/db/workspace ready
- ✅ Backup verified functional (manual backup executed)
- ✅ No further log errors

### Model Discrepancy Resume

- ✅ Root cause identified and documented
- ✅ Fix applied (if applicable) or confirmed as known limitation
- ✅ Test run completed on TUHO/Oborovo — outputs within tolerance
- ✅ Phase 43 issue log updated with findings

### Stale / Export Misuse Resume

- ✅ Re-run completed on all affected scenarios
- ✅ Fresh exports generated and verified
- ✅ Pilot user re-briefed on stale-output boundary
- ✅ No stale exports remain in active use

### Generic Path Misuse Resume

- ✅ Generic outputs identified and segregated
- ✅ No financial decisions made from generic outputs
- ✅ Pilot user re-briefed on generic exclusion
- ✅ Scope confirmation note acknowledged

### External Claims Resume

- ✅ Claim corrected or retracted
- ✅ All recipients notified of pilot scope limitation
- ✅ Non-claims briefing completed
- ✅ No further claims made

### Config / Environment Resume

- ✅ Configuration change reviewed by technical reviewer
- ✅ `/readyz` confirmed green
- ✅ Manual backup executed
- ✅ Test run on TUHO completed without error

---

## Escalation Path

1. **Pilot user or operator detects issue** → pauses pilot immediately
2. **Operator files issue via `docs/pilot_issue_intake_template.md`** → marks as PAUSE
3. **Triage owner assesses within 1h** → determines root cause and required evidence
4. **Fix or mitigation applied** → documented in issue log
5. **Resume evidence submitted** → reviewed by decision maker
6. **Pilot resumed** → logged in weekly checklist

---

## Generic Solar/Wind and Pilot Conclusions

**Critical rule:** Generic solar or wind outputs used for external financial decisions invalidate the pilot conclusions for that use case.

If a pilot user or anyone else relies on generic solar/wind outputs to make a financial decision:
- The decision is **not supported** by the pilot
- Pilot conclusions for validated paths (TUHO/Oborovo) remain valid
- The generic path misuse must be documented and acknowledged

This is a **pause trigger** — see above.

---

## Document History

| Date | Event |
|------|-------|
| 2026-06-01 | Policy created (Phase 43) |
| | |