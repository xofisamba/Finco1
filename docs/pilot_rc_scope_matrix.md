# Pilot RC Scope Matrix

**Branch:** `phase35-pilot-release-candidate-closeout`
**Base SHA:** `048806a4bcc322c078ffc7d3e5de0d24b310fbac`
**Date:** 2026-05-31

---

## Scope Matrix

| Area / Feature | Included in Pilot RC? | Validation Status | Evidence | User-Facing Claim Allowed? | Limitation / Warning | Next Action |
|---|---|---|---|---|---|---|
| TUHO frozen path | [Included] Yes | [Validated] Fully validated vs Excel | PRs #27/#27B, Phase 29C | [Allowed] Yes - validated | Within tolerance: project IRR +0.99pp, DSCR +0.231 | Monitor |
| Oborovo frozen path | [Included] Yes | [Validated] Fully validated vs Excel | PRs #27/#27B, Phase 31/31B/31C | [Allowed] Yes - validated | equity_irr=6.24% (stale ~9.88% anchor; runtime correct) | Update stale anchors |
| TUHO CO2 | [Included] Yes | [Validated] Y1 about 611 kEUR | Phase 29A, PR #29A | [Allowed] Yes - calibrated | No wind CO2 for generic | Phase 34 |
| Oborovo OpEx | [Included] Yes | [Validated] Y1 = 1,338 kEUR | Phase 31, PR #341 | [Allowed] Yes - exact match | None | None |
| Oborovo CAPEX sensitivity | [Diagnostic] Only | [Partial] Base case validated, sensitivities not | Phase 29B, PR #29B | [Blocked] No - diagnostic only | Not Excel-validated projections | Internal only |
| Senior debt / DSCR / SHL | [Included] Yes | [Validated] Frozen-path validated | Phase 23 series, PRs #23O/#276 | [Allowed] Yes - validated | Oborovo: bullet SHL (no sweep P4), first dist year 20 | None |
| Scenario save/load/versioning | [Included] Yes | [Validated] Architecture confirmed | Phase 32, PR #344 | [Allowed] Yes - implemented | None | Phase 33 (UI) done |
| Scenario version history UI | [Included] Yes | [Validated] Wired to sidebar | Phase 33, PR #345 | [Allowed] Yes - functional | Read-only (use /scenarios/{id}/load for restore) | None |
| Audit/reconciliation tab | [Partial] Surface only | [Review] Explore if needed | - | [Blocked] No - not validated | Not a pilot blocker | Future |
| Excel export/downloads | [Included] Yes | [Validated] Functional | Phase 27B export tests | [Allowed] Yes - functional | None | None |
| Backup/restore | [Included] Yes | [Validated] Functional | Phase 24F, PR #24F | [Allowed] Yes - available | restore() overwrites DB - backup first | Document |
| Auto-backup | [Included] Yes | [Validated] Scheduled via APScheduler | Phase 24F1, PR #24F1 | [Allowed] Yes - active | No effect on versioning semantics | Monitor logs |
| /readyz observability | [Included] Yes | [Validated] Returns model/db/workspace ready | Phase 26D, PR #26D | [Allowed] Yes - green means ready | Not a financial guarantee | None |
| Single-user/pilot mode | [Included] Yes | [Validated] Implemented | Phase 26B, PR #26B | [Allowed] Yes - documented | No multi-user | None |
| Generic solar/wind | [Excluded] No | [Unvalidated] Exploratory only | Phase 28, PR #28 | [Blocked] No - NOT validated | Do not use for external decisions | Phase 34 |
| Generic wind CO2 | [Excluded] No | [Unvalidated] | Phase 28 | [Blocked] No - NOT validated | Generic path must be validated first | Phase 34 |
| Construction IDC | [Excluded] No | [Not wired] | Phase 31 series | [Blocked] No - NOT available | M1-M18 / C.16 not implemented | Future |
| C.16 Project Rights | [Excluded] No | [Not wired] | - | [Blocked] No - NOT available | Not implemented | Future |
| M1-M18 IDC | [Excluded] No | [Not wired] | - | [Blocked] No - NOT available | Not implemented | Future |
| Live sculpting / debt re-sizing | [Excluded] No | [Not promoted] | Phase 31C / PR #276 | [Blocked] No - frozen path only | Frozen-path validated; live sculpting not in scope | Future |
| Multi-user / RBAC / SSO | [Excluded] No | [Not implemented] | Single-user mode | [Blocked] No - single-user only | Not a pilot blocker for single trusted user | Future |
| SaaS / enterprise readiness | [Excluded] No | [Not claimed] | - | [Blocked] No - NOT ready | Not applicable to current pilot | Future |
| Bank/lender/external audit/certification | [Excluded] No | [Not claimed] | - | [Blocked] No - NOT applicable | Never claim these | N/A |

---

## Summary

| Category | Count |
|----------|-------|
| Included and validated | 17 |
| Diagnostic only | 1 |
| Excluded / unvalidated | 8 |

**Decision: Pilot RC is GO** for TUHO and Oborovo frozen templates only. Generic path is out of scope.
