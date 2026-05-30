# Phase 24 Closeout / Pilot Readiness Review

## Base SHA
`91fec0c6f714af46c0e58a1dedd1a2f0500b515d` (after PR #326 merge)

## PR #299 Status
`draft=True`, `state=open`, `merged=False` — superseded.

---

## Phase 24 Merged PRs

| PR | Phase | SHA | Description |
|----|-------|-----|-------------|
| #321 | 24A — Runtime Impact Taxonomy | `8ced91b` | Canonical 4-state taxonomy: Drives model / Display only / Pending / Needs review |
| #322 | 24B — Scenario State Banner | `6f21145` | Documents and tests existing banner + validation bar behavior |
| #323 | 24C — Debt / DSCR / SHL UI | `cf9e6e2` | New debt/DSCR/SHL panel partial |
| #324 | 24C.1 — Frozen-vs-Derived Warning | `187e410` | Warning banner + generic project ⚠️ labels |
| #325 | 24F — SQLite Backup/Restore | `3870ef7` | Backup/restore module with safety protections |
| #326 | 24E — Audit / Reconciliation Tab | `91fec0c` | Audit tab covering all model areas |

---

## What Phase 24 Achieved

### UI Transparency
- **Runtime Impact taxonomy**: standardized labels across all UI surfaces
- **Scenario state banner**: clear saved/unsaved/stale state for users
- **Debt/DSCR/SHL panel**: visible frozen senior DS status, DSCR, SHL, distribution lock-up
- **Audit tab**: single view of parity status across Revenue/OPEX/CAPEX/Debt/SHL/Validation
- **Frozen-vs-derived warning**: users cannot confuse fixture-backed frozen path with derived/sculpting path

### Pilot-Safety
- **SQLite backup/restore**: data-loss protection before broader pilot use
- **Generic project labeling**: ⚠️ Unvalidated · Derived path warning on generic templates
- **No bank/lender/external audit claims**: explicit disclaimers in audit tab and all PRs

### Technical Quality
- **No runtime formula changes** across all Phase 24 PRs
- **No JS financial calculations** added
- **Full regression suite green**: 182+ tests passing
- **CI green** on all post-merge runs

---

## What UI/Pilot-Safety Risks Were Reduced

| Risk | Mitigation |
|------|-----------|
| User confusion about frozen vs derived debt path | Phase 24C.1 warning banner + generic labels |
| No data backup before pilot use | Phase 24F backup_restore module |
| Users misinterpreting DSCR deviations as defects | Phase 24E audit tab classifies as "expected under frozen DS path" |
| Generic projects assumed to be validated | Phase 24C.1 ⚠️ labels + Phase 24E audit tab "Needs Review" |
| No clear validation state for scenario runs | Phase 24B documents existing PASS/WARN/FAIL states |
| No audit trail for parity status | Phase 24E audit tab provides single source of truth |

---

## Current App Maturity After Phase 24

### ✅ Achieved: Internal Demo / Internal Working Product

| Dimension | Status |
|-----------|--------|
| TUHO/Oborovo frozen-template parity | ✅ Calibrated, fixture-backed, documented |
| UI transparency | ✅ Runtime Impact taxonomy, banner, audit tab |
| Data safety | ✅ SQLite backup/restore |
| Guardrails | ✅ G20 blocked, R99/R102 not approved, no JS calcs |
| Test coverage | ✅ 182+ tests passing |

### ⚠️ Remaining Before Trusted Pilot

| Blocker | Severity | Notes |
|---------|----------|-------|
| Generic project path unvalidated | 🟡 Medium | Labeled ⚠️ but not validated vs Excel |
| CAPEX per-line runtime not exposed | 🟡 Medium | Display/schema only |
| No user authentication/authorization | 🟡 Medium | Single-user pilot assumed |
| No audit log / replay | 🟡 Low | Phase 23 replay_metadata exists but not UI-exposed |
| No workspace-level access control | 🟡 Low | Single-user assumption |

### 🔴 Remaining Before Paid Pilot / B2B SaaS

| Blocker | Severity | Notes |
|---------|----------|-------|
| No multi-user / tenant isolation | 🔴 High | Single-user assumption throughout |
| No role-based access control | 🔴 High | No admin/viewer/editor roles |
| No data residency / GDPR compliance | 🔴 High | DB may contain EU personal data |
| No audit log UI | 🔴 Medium | Replay metadata exists but not surfaced |
| No formal model approval workflow | 🔴 Medium | No lender/bank approval workflow |
| CAPEX per-line runtime not wired | 🔴 Medium | Phase 21 display/schema only |

---

## Recommended Next Phase

**Phase 26A — Security / Dependency Quick Wins**

Before Phase 24D Shared LineItemGrid, security and dependency hardening is more important for pilot readiness:

| Priority | Item | Reason |
|----------|------|--------|
| P0 | Pin Python dependencies (`requirements.txt` / `pyproject.toml`) | Reproducibility + security |
| P0 | Add `.gitignore` / `.env.example` hygiene | Prevent credential leaks |
| P1 | Add `SECRET_KEY` / `FINCO_SECRET_KEY` validation on startup | Fail fast on misconfiguration |
| P1 | Add auth middleware on all API routes | Prevent unauthenticated access |
| P2 | Rate limiting on API routes | Prevent abuse |
| P2 | Add ` helmets` / security headers | Standard hardening |

**Rationale**: Shared LineItemGrid is useful but refactor-oriented. Security/dependency/config hardening is more important for pilot-readiness and cannot be retrofitted easily.

---

## Explicit Maturity Classification

**Current maturity: Internal Working Product** (not yet Trusted Pilot)

Phase 24 achieved internal working product status for TUHO/Oborovo frozen-template path. The generic project path is honestly labeled as unvalidated. The app is not ready for paid pilot or B2B SaaS without multi-user support, RBAC, and data residency compliance.

---

## Explicit Non-Claims

This closeout does NOT represent:
- Bank approval or lender approval
- External model audit or certified audit
- Credit committee approval
- SaaS/audit certification

---

## Guardrails

- ✅ No runtime formula changes
- ✅ No JS financial calculations
- ✅ G20 BLOCKED
- ✅ R99/R102 NOT APPROVED
- ✅ PR #299 remains draft / not merged / superseded
- ✅ Backend remains source of truth
