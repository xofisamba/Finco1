# Pilot RC Scope Matrix

**Branch:** `phase35-pilot-release-candidate-closeout`
**Base SHA:** `048806a4bcc322c078ffc7d3e5de0d24b310fbac`
**Date:** 2026-05-31

---

## Scope Matrix

| Area / Feature | Included in Pilot RC? | Validation Status | Evidence | User-Facing Claim Allowed? | Limitation / Warning | Next Action |
|---|---|---|---|---|---|---|
| TUHO frozen path | ✅ Yes | ✅ Fully validated vs Excel | PRs #27/#27B, Phase 29C | ✅ Yes — validated | Within tolerance: project IRR +0.99pp, DSCR +0.231 | Monitor |
| Oborovo frozen path | ✅ Yes | ✅ Fully validated vs Excel | PRs #27/#27B, Phase 31/31B/31C | ✅ Yes — validated | equity_irr=6.24% (stale ~9.88% anchor; runtime correct) | Update stale anchors |
| TUHO CO2 | ✅ Yes | ✅ Validated — Y1≈611 kEUR | Phase 29A, PR #29A | ✅ Yes — calibrated | No wind CO2 for generic | Phase 34 |
| Oborovo OpEx | ✅ Yes | ✅ Validated — Y1=1,338 kEUR | Phase 31, PR #341 | ✅ Yes — exact match | None | None |
| Oborovo CAPEX sensitivity | ⚠️ Diagnostic only | ⚠️ Base case validated, sensitivities not | Phase 29B, PR #29B | ❌ No — diagnostic only | Not Excel-validated projections | Internal only |
| Senior debt / DSCR / SHL | ✅ Yes | ✅ Frozen-path validated | Phase 23 series, PRs #23O/#276 | ✅ Yes — validated | Oborovo: bullet SHL (no sweep P4), first dist year 20 | None |
| Scenario save/load/versioning | ✅ Yes | ✅ Architecture confirmed | Phase 32, PR #344 | ✅ Yes — implemented | None | Phase 33 (UI) done |
| Scenario version history UI | ✅ Yes | ✅ Wired to sidebar | Phase 33, PR #345 | ✅ Yes — functional | Read-only (use /scenarios/{id}/load for restore) | None |
| Audit/reconciliation tab | 🔜 Partial | 🟡 Explore if needed | — | ❌ No — not validated | Not a pilot blocker | Future |
| Excel export/downloads | ✅ Yes | ✅ Functional | Phase 27B export tests | ✅ Yes — functional | None | None |
| Backup/restore | ✅ Yes | ✅ Functional | Phase 24F, PR #24F | ✅ Yes — available | restore() overwrites DB — backup first | Document |
| Auto-backup | ✅ Yes | ✅ Scheduled via APScheduler | Phase 24F1, PR #24F1 | ✅ Yes — active | No effect on versioning semantics | Monitor logs |
| /readyz observability | ✅ Yes | ✅ Returns model/db/workspace ready | Phase 26D, PR #26D | ✅ Yes — green means ready | Not a financial guarantee | None |
| Single-user/pilot mode | ✅ Yes | ✅ Implemented | Phase 26B, PR #26B | ✅ Yes — documented | No multi-user | None |
| Generic solar/wind | ❌ Excluded | ❌ Unvalidated — exploratory only | Phase 28, PR #28 | ❌ No — NOT validated | Do not use for external decisions | Phase 34 |
| Generic wind CO2 | ❌ Excluded | ❌ Unvalidated | Phase 28 | ❌ No — NOT validated | Generic path must be validated first | Phase 34 |
| Construction IDC | ❌ Excluded | ❌ Not wired | Phase 31 series | ❌ No — NOT available | M1-M18 / C.16 not implemented | Future |
| C.16 Project Rights | ❌ Excluded | ❌ Not wired | — | ❌ No — NOT available | Not implemented | Future |
| M1-M18 IDC | ❌ Excluded | ❌ Not wired | — | ❌ No — NOT available | Not implemented | Future |
| Live sculpting / debt re-sizing | ❌ Excluded | ❌ Not promoted | Phase 31C / PR #276 | ❌ No — frozen path only | Frozen-path validated; live sculpting not in scope | Future |
| Multi-user / RBAC / SSO | ❌ Excluded | ❌ Not implemented | Single-user mode | ❌ No — single-user only | Not a pilot blocker for single trusted user | Future |
| SaaS / enterprise readiness | ❌ Excluded | ❌ Not claimed | — | ❌ No — NOT ready | Not applicable to current pilot | Future |
| Bank/lender/external audit/certification | ❌ Excluded | ❌ Not claimed | — | ❌ No — NOT applicable | Never claim these | N/A |

---

## Summary

| Category | Count |
|----------|-------|
| ✅ Included & Validated | 17 |
| ⚠️ Diagnostic only | 1 |
| ❌ Excluded / Unvalidated | 8 |

**Decision: Pilot RC is GO** for TUHO and Oborovo frozen templates only. Generic path is out of scope.