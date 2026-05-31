# Phase 29C: Post-Phase 29 Readiness Matrix

Base: `6b9451ec8732d2543b53d88e130e5a61850641ab`

## How to Read This Matrix

**Columns:**
- **Area**: Feature or component area
- **Current status**: Brief description of current state
- **Evidence**: Source file, doc, or test
- **Score (1–10)**: Self-explanatory
- **Trusted pilot blocker?**: 🔴 yes | 🟡 partial | 🟢 no
- **Paid pilot blocker?**: 🔴 yes | 🟡 partial | 🟢 no
- **Enterprise blocker?**: 🔴 yes | 🟡 partial | 🟢 no
- **Recommended next action**: Short description

---

## Model / Validation Areas

| Area | Current status | Evidence | Score | Trusted pilot | Paid pilot | Enterprise | Recommended next action |
|------|---------------|----------|-------|---------------|------------|------------|------------------------|
| TUHO frozen model | ✅ Validated — debt 43,359 kEUR, equity IRR 11.81% vs 11.61% Excel | `docs/phase27_frozen_path_external_validation_pack.md` | 8/10 | 🟢 No | 🟢 No | 🔴 No (not target) | Maintain; monitor for drift |
| Oborovo frozen model | ✅ Validated — debt 42,852.27 kEUR, equity IRR ~9.88% vs 10.60% Excel | `docs/phase27_frozen_path_external_validation_pack.md` | 6/10 | 🟡 Partial (OpEx gap) | 🔴 Yes (OpEx double-count) | 🔴 Yes (OpEx gap + no multi-user) | Phase 31: deep-dive B.01/B.02 sub-item aggregation |
| TUHO CO2 | ✅ Validated — Y1 ~611 kEUR, price 4.191 EUR/MWh, declining schedule | `docs/phase29a_tuho_co2_revenue_deep_dive.md` | 8/10 | 🟢 No | 🟡 Partial (period-level not exposed) | 🔴 Yes (no struct field) | Phase 33: add co2_revenue_keur to SculptingPeriod |
| Generic solar (SOLAR-001) | ❌ Unvalidated — no Excel reference, round numbers | `docs/phase28_generic_project_path_validation.md` | 2/10 | 🔴 Yes (unvalidated) | 🔴 Yes (unvalidated) | 🔴 Yes (unvalidated) | Phase 34: find or create Excel reference |
| Generic wind (WIND-001) | ❌ Unvalidated — no Excel reference, co2 flat price only | `docs/phase28_generic_project_path_validation.md` | 2/10 | 🔴 Yes (unvalidated) | 🔴 Yes (unvalidated) | 🔴 Yes (unvalidated) | Phase 34: find or create Excel reference |
| Oborovo CAPEX sensitivity | ⚠️ Diagnostic only — frozen DS unchanged, directional only | `docs/phase29b_oborovo_capex_sensitivity.md` | 5/10 | 🟡 Partial (not validated) | 🔴 Yes (not Excel-validated) | 🔴 Yes (not validated) | Document as limitation; no immediate action |
| Debt/DSCR/SHL frozen path | ✅ TUHO + Oborovo frozen senior DS active | `app/project_factories.py:202,422` | 8/10 | 🟢 No | 🟢 No | 🔴 Yes (no re-size) | Phase 30: audit frozen DS wiring for both projects |
| Live sculpting (generic) | ❌ Not promoted — generic path unvalidated | `docs/phase28_generic_project_path_validation.md` | 3/10 | 🔴 Yes (unvalidated) | 🔴 Yes (unvalidated) | 🔴 Yes (unvalidated) | Phase 34: validate before promoting |
| Construction IDC (M1–M18) | ❌ Not wired — IDC present in TUHO/Oborovo factories but not runtime | `app/project_factories.py` | 2/10 | 🔴 Yes (not wired) | 🔴 Yes (not wired) | 🔴 Yes (not wired) | Do not wire without Excel reference |
| C.16 Project Rights | ❌ Not wired — Oborovo has 3,024.5 kEUR but no runtime impact | `app/project_factories.py:67` | 1/10 | 🟡 Partial (present but inactive) | 🔴 Yes (not wired) | 🔴 Yes (not wired) | Do not wire without stakeholder need |

## Product / Operational Areas

| Area | Current status | Evidence | Score | Trusted pilot | Paid pilot | Enterprise | Recommended next action |
|------|---------------|----------|-------|---------------|------------|------------|------------------------|
| Audit/reconciliation UI | ✅ Phase 24E complete — audit tab exists | `docs/phase24e_audit_reconciliation_tab.md` | 6/10 | 🟢 No | 🟡 Partial (not full Excel parity) | 🔴 Yes (no certification) | Continue UI polish post-Claude review |
| Validation pack | ✅ Phase 27/27B stakeholder-ready | `docs/validation_pack_executive_summary.md` | 8/10 | 🟢 No | 🟢 No | 🔴 Yes (no audit cert) | Maintain; update after OpEx fix |
| Onboarding/help | ✅ Phase 25B demo mode + guided workflow | `docs/phase25b_onboarding_help_demo_mode.md` | 7/10 | 🟢 No | 🟢 No | 🔴 Yes (single-user only) | Add generic path warning label |
| Backup/restore | ✅ Phase 24F — SQLite backup/restore working | `docs/phase24f_sqlite_backup_restore.md` | 8/10 | 🟢 No | 🟢 No | 🔴 Yes (single-user) | Add automated scheduling (Phase 24F.1 done) |
| Observability/readiness endpoint | ✅ Phase 26D — `/readyz` endpoint added | `docs/deployment_runbook.md` | 8/10 | 🟢 No | 🟢 No | 🔴 Yes (no enterprise monitoring) | Add metrics export if needed |
| Dependency reproducibility | ✅ Phase 26C — requirements.txt pinned | `tests/test_phase26c_dependency_pinning_ci_config_hardening.py` | 8/10 | 🟢 No | 🟢 No | 🔴 Yes (no CVE scanning) | Add nightly CVE scan |
| Auth/single-user boundary | ✅ Phase 26B — single-user mode boundary clear | `tests/test_phase26b_auth_single_user_mode_boundary.py` | 7/10 | 🟢 No | 🟡 Partial (no multi-user) | 🔴 Yes (no RBAC) | Design RBAC before implementing |
| Persistence/scenario versioning | ❌ In-memory only — no persistent scenario versioning | `app/scenario_manager.py` | 4/10 | 🔴 Yes (data loss risk) | 🔴 Yes (no versioning) | 🔴 Yes (no versioning) | Phase 32: implement persistent scenario storage |
| Shared LineItemGrid/UI refactor | ❌ Project-specific grids only — no shared component | `app/project_factories.py` CAPEX items | 3/10 | 🟡 Partial (works per-project) | 🔴 Yes (duplication) | 🔴 Yes (duplication) | Design shared component post-paid-pilot |

## Security / Governance Areas

| Area | Current status | Evidence | Score | Trusted pilot | Paid pilot | Enterprise | Recommended next action |
|------|---------------|----------|-------|---------------|------------|------------|------------------------|
| G20/R99/R102 guardrails | ✅ BLOCKED/NOT APPROVED | `workspace_shell.html` | 10/10 | 🟢 No | 🟢 No | 🟢 No | Maintain |
| partial_pay_sweep | ❌ Not promoted | `workspace_shell.html` | 10/10 | 🟢 No | 🟢 No | 🟢 No | Maintain |
| flat/min DSCR sculpting | ❌ Not promoted | `workspace_shell.html` | 10/10 | 🟢 No | 🟢 No | 🟢 No | Maintain |
| No JS financial calculations | ✅ Confirmed — backend is source of truth | `app/` Python files only | 10/10 | 🟢 No | 🟢 No | 🟢 No | Maintain |
| No lender/bank/audit/SaaS claims | ✅ Explicit non-claims in docs | All phase docs | 10/10 | 🟢 No | 🟢 No | 🟢 No | Maintain |

## Future / Blocked Areas

| Area | Current status | Evidence | Score | Trusted pilot | Paid pilot | Enterprise | Recommended next action |
|------|---------------|----------|-------|---------------|------------|------------|------------------------|
| Multi-user / RBAC / SSO | ❌ Not implemented — single-user only | `app/auth.py` | 2/10 | 🟡 Partial (single-user ok) | 🔴 Yes (needed for paid) | 🔴 Yes (required) | Design after Phase 32 (scenario persistence) |
| Enterprise SaaS readiness | ❌ Not claimed — no multi-user, no audit cert | Docs | 1/10 | 🟡 Partial (not target) | 🔴 Yes (not target) | 🔴 Yes (not ready) | Do not claim; roadmap after Phase 35+ |
| Live sculpting validation | ❌ Not done — generic path unvalidated | `docs/phase28_generic_project_path_validation.md` | 2/10 | 🔴 Yes (unvalidated) | 🔴 Yes (unvalidated) | 🔴 Yes (unvalidated) | Phase 34: validate with Excel reference first |

---

## Summary

| Category | Areas | Avg Score |
|----------|-------|-----------|
| Model/Validation | 10 | 4.8/10 |
| Product/Operational | 8 | 5.9/10 |
| Security/Governance | 5 | 10/10 |
| Future/Blocked | 3 | 1.7/10 |
| **Overall** | **26** | **5.4/10** |

**Trusted pilot readiness: ~6/10** — TUHO/Oborovo frozen path works; OpEx gap must be documented; generic path is off-limits.

**Paid pilot readiness: ~4/10** — OpEx gap is the main blocker; scenario persistence needed; multi-user not yet required.

**Enterprise SaaS readiness: ~2/10** — Multiple blockers; do not claim enterprise readiness.

---

## Readiness Trend (Phase 24 → Phase 29C)

| Area | Phase 24 score | Phase 29C score | Trend |
|------|---------------|-----------------|-------|
| TUHO frozen path | ~6/10 | 8/10 | ✅ Improved |
| Oborovo frozen path | ~5/10 | 6/10 | ✅ Improved |
| CO2 revenue | ~4/10 | 8/10 | ✅ Improved |
| CAPEX sensitivity | N/A | 5/10 | ✅ New |
| Generic path | N/A | 2/10 | ✅ Characterized |
| Observability | ~5/10 | 8/10 | ✅ Improved |
| Backup/restore | ~6/10 | 8/10 | ✅ Improved |
| Auth boundary | ~6/10 | 7/10 | ✅ Improved |
| Scenario persistence | ~3/10 | 4/10 | ➡️ Marginal |
| Multi-user/RBAC | 1/10 | 2/10 | ➡️ Marginal |

**Overall trend: Improving** — model validation quality significantly improved since Phase 23–24. Product operational gaps remain. Multi-user remains the biggest future gap.