# Phase 43 — Pilot Operations Decision Matrix

**Branch:** `phase43-pilot-ongoing-operations-issue-triage`
**Base SHA:** `07506503e0602e6a8d4bd940be56001b6201906a`
**Date:** 2026-06-01

---

## Decision Matrix

| Area | Operating Rule | Evidence | Check Cadence | Pause Trigger | Owner Action |
|------|---------------|---------|--------------|---------------|-------------|
| /readyz | Must return green before each session | `/readyz` returns 200, model/db/workspace ready | Before each session | `/readyz` returns red or incomplete | Do not proceed; check logs |
| backup/auto-backup | APScheduler must run; manual backup before first run | APScheduler log; manual backup 200 | Daily (auto); per session (manual) | No backup in 24h; restore fails | Alert operator; do not run without backup |
| scenario versioning | Named scenario saved before any input change | Scenario list in UI | Before any run | No baseline scenario saved before run | Remind pilot user; enforce in process |
| stale-output boundary | Re-run after any input change before export | UI warning active | Every export | Stale export used for decision | Re-run immediately; log incident |
| export hygiene | Timestamp filenames; no stale exports in use | Export files with timestamps | Every export | Export from old run shared/external | Re-run; verify; do not share |
| TUHO run | Senior debt 43,359 kEUR; equity IRR ~11.81%; CO2 Y1=611 kEUR | Phase 29C/Phase 40 validation | Per TUHO run | Outputs outside tolerance | Pause; review; document |
| Oborovo run | Senior debt 42,852 kEUR; SHL opening 15,790 kEUR; Y1 OpEx=1,338 kEUR | Phase 31C/Phase 40 validation | Per Oborovo run | Outputs outside tolerance | Pause; review; document |
| generic exclusion | Generic solar/wind NOT validated — exploratory only | `docs/pilot_scope_confirmation_note.md` | Ongoing | Generic used for financial decision | Pause; re-brief user; document |
| issue intake | All issues filed via `docs/pilot_issue_intake_template.md` | Filled template per issue | Per issue | None — process only | Route to triage board |
| issue triage cadence | Severity SLA: blocker 1h, major 4h, minor 1d, clarification 3d | Phase 43 triage SLA table | Daily review | SLA breach | Escalate to sign-off team |
| non-claims | No bank/lender/audit/certification/SaaS/enterprise claims | `docs/pilot_scope_confirmation_note.md` | Ongoing | Claim made externally | Immediate correction; log |
| G20 gate | G20 BLOCKED — not changed, not promoted | `docs/phase41_pilot_launch_readiness_matrix.md` | Ongoing | Attempt to enable G20 | Alert; block; document |
| R99 gate | R99 NOT APPROVED — not changed, not promoted | `docs/phase41_pilot_launch_readiness_matrix.md` | Ongoing | Attempt to enable R99 | Alert; block; document |
| R102 gate | R102 NOT APPROVED — not changed, not promoted | `docs/phase41_pilot_launch_readiness_matrix.md` | Ongoing | Attempt to enable R102 | Alert; block; document |
| partial_pay_sweep | Not promoted — frozen path only | Phase 31C / PR #276 | Ongoing | Attempt to activate | Alert; block; document |
| flat/min DSCR sculpting | Not promoted — frozen path only | Phase 31C / PR #276 | Ongoing | Attempt to activate | Alert; block; document |
| paid pilot blockers | Generic solar/wind, generic wind CO2, IDC, C.16, M1-M18 unresolved | Phase 40/42 issue logs | Ongoing | Attempt to use for paid/generic | Defer; document; route to Phase 34 scope |

---

## Pause Triggers Summary

| Trigger | Severity | Immediate Action |
|---------|----------|-----------------|
| `/readyz` red | BLOCKER | Stop — do not run model |
| No backup in 24h | BLOCKER | Manual backup required |
| Generic outputs used for financial decision | BLOCKER | Pause; log; re-brief user |
| External claim (bank/lender/audit/SaaS) | BLOCKER | Correct immediately; log |
| TUHO/Oborovo outputs outside tolerance | MAJOR | Pause; review; document |
| Stale export used for decision | MAJOR | Re-run; fresh export; log |
| Config/environment change | MAJOR | Review; test; approve before continuing |
| SLA breach (blocker >1h, major >4h) | MAJOR | Escalate to sign-off team |

---

## Owner Actions Reference

| Area | Primary Owner | Backup Owner |
|------|---------------|--------------|
| /readyz | Operator | Technical reviewer |
| Backup/restore | Operator | Technical reviewer |
| TUHO/Oborovo runs | Pilot user | Operator |
| Generic exclusion | Operator | Pilot user |
| Issue intake/triage | Triage owner | Sign-off team |
| Non-claims | Operator | Sign-off team |
| Gates (G20/R99/R102) | Technical reviewer | Sign-off team |
| Paid pilot blockers | Sign-off team | Phase 34 owner |

---

## Guardrails Status

| Gate | Status |
|------|--------|
| G20 | BLOCKED — never enable |
| R99 | NOT APPROVED — never enable |
| R102 | NOT APPROVED — never enable |
| partial_pay_sweep | Not promoted — frozen path only |
| flat/min DSCR sculpting | Not promoted — frozen path only |
| Backend source of truth | Confirmed — JS is display-only |
| No formula changes | Confirmed |
| No JS financial calculations | Confirmed |