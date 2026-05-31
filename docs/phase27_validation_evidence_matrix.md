# Phase 27 — Validation Evidence Matrix

## Purpose

This matrix maps each validated claim to its evidence source, status, materiality, and remaining limitations. It is the machine-readable/dense-summary complement to the narrative validation pack (`phase27_frozen_path_external_validation_pack.md`).

---

## Evidence Matrix

| Claim | Project | Evidence Type | Source Document/Test | Status | Materiality | Remaining Limitation |
|-------|---------|--------------|----------------------|--------|------------|---------------------|
| Senior debt amount: 43,359.0 kEUR | TUHO | Factory fixture + test | `app/project_factories.py` → `create_default_tuho_wind1()`; `tests/test_phase23u_full_excel_parity_pack.py` | ✅ Validated | Negligible (0 kEUR diff) | None |
| Senior debt amount: 42,852.27 kEUR | Oborovo | Factory fixture + test | `app/project_factories.py` → `create_default_oborovo()`; `tests/test_phase23u_full_excel_parity_pack.py` | ✅ Validated (within rounding) | Low (+0.27 kEUR vs Excel 42,852.0) | Rounding difference |
| TUHO senior DS fixture parity (op_idx 0–13) | TUHO | Parity table | `docs/phase23u_full_excel_parity_pack.md` Table: TUHO Parity | ✅ Validated | Negligible (diff < 0.5 kEUR) | op_idx 12 +0.07 kEUR fixture rounding |
| TUHO selected senior DS parity | TUHO | Parity table | `docs/phase23u_full_excel_parity_pack.md` | ✅ Validated | Negligible | — |
| Oborovo senior DS fixture parity (op_idx 0–26) | Oborovo | Parity table | `docs/phase23u_full_excel_parity_pack.md` Table: Oborovo Parity | ✅ Validated | Negligible (diff ~0) | None |
| Oborovo op_idx 27 residual +16.84 kEUR | Oborovo | Residual bridge | `docs/phase23t_senior_debt_amount_dscr_residual_bridge.md`; `docs/phase23u_full_excel_parity_pack.md` | ✅ Within 20 kEUR tolerance | Low (within tolerance) | Classification: rounding/mapping |
| DSCR deviations above target: expected under frozen DS path | TUHO | Trajectory analysis | `docs/phase23u_full_excel_parity_pack.md` § Residual Classification | ℹ️ Expected | Informational | Not a runtime defect |
| DSCR deviations above target: expected under frozen DS path | Oborovo | Trajectory analysis | `docs/phase23u_full_excel_parity_pack.md` § Residual Classification | ℹ️ Expected | Informational | Not a runtime defect |
| Oborovo SHL opening balance: ~15,790.0 kEUR | Oborovo | Opening balance bridge | `docs/phase23k_oborovo_shl_opening_balance_bridge.md` | ✅ Validated | Negligible (−1 kEUR vs Excel 15,791) | None |
| Oborovo SHL amount corrected: 14,621.0 kEUR | Oborovo | Factory correction | `docs/phase23l_oborovo_shl_amount_factory_correction.md` | ✅ Corrected | N/A (was a defect, now fixed) | Was understated by ~1,074 kEUR |
| Oborovo SHL IDC: 1,169.0 kEUR | Oborovo | Factory confirmation | `app/project_factories.py` → `create_default_oborovo()`; `docs/phase23l_oborovo_shl_amount_factory_correction.md` | ✅ Validated | Negligible (−1 kEUR vs Excel ~1,170) | None |
| Oborovo shl_tenor_years corrected to 20 | Oborovo | Factory fix | `docs/phase23j_oborovo_shl_tenor_correction.md`; `docs/phase23l_oborovo_shl_amount_factory_correction.md` | ✅ Corrected | N/A (was 0, now 20-year bullet) | Was 0 before Phase 23J |
| Oborovo distribution lock-up while SHL outstanding | Oborovo | Lock-up fix | `docs/phase23o_oborovo_distribution_lockup_policy_parity.md`; `docs/phase23p_oborovo_post_lockup_parity_snapshot.md` | ✅ Validated | N/A (policy fix) | Was allowing early distributions |
| Oborovo first valid distribution: op_idx 39 (2050-06-30) | Oborovo | Post-lockup parity | `docs/phase23p_oborovo_post_lockup_parity_snapshot.md`; `docs/phase23u_full_excel_parity_pack.md` | ✅ Validated | N/A | None |
| TUHO CO2 enabled, price 4.191 EUR/MWh, Y1 ~611 kEUR | TUHO | Phase 21 calibration | `docs/phase21_tuho_calibration_reference.md`; `tests/test_phase23u_full_excel_parity_pack.py` | ✅ Calibrated | N/A | CO2 price declines ~10%/year |
| TUHO equity IRR with CO2: 11.81% vs Excel 11.61% | TUHO | Phase 21 calibration | `tests/test_tuho_shl_calibration.py` | ✅ Within ±1.0 pp | Low (+0.20 pp) | None |
| Generic project path: unvalidated | Generic | Design note | `docs/phase27_frozen_path_external_validation_pack.md`; `docs/pilot_user_guide.md` | ⚠️ Out of scope | N/A | No Excel reference for generic path |
| CAPEX / C.16 Project Rights / M1–M18 IDC: not in runtime | All | Phase 23F reference | `docs/phase23f_tuho_frozen_factory_opt_in_candidate.md`; `app/project_factories.py` | ❌ Not wired | N/A | Not required for frozen-template path |
| Sculpting solver not promoted | All | Guardrail | `app/templates/partials/workspace_shell.html`; `docs/phase27_frozen_path_external_validation_pack.md` | ❌ Not approved | N/A | partial_pay_sweep not approved; flat/min DSCR not approved |
| No bank/lender/audit/certification claim | All | Guardrail | `docs/phase27_frozen_path_external_validation_pack.md` §7; `docs/pilot_user_guide.md` | ❌ Explicitly not claimed | N/A | Internal pilot tooling only |
| No SaaS-ready / multi-tenant claim | All | Guardrail | `docs/deployment_runbook.md`; `docs/phase27_frozen_path_external_validation_pack.md` | ❌ Not claimed | N/A | Single-user internal pilot mode |
| Backend remains sole calculation authority | All | Architecture | `app/templates/partials/workspace_shell.html`; `docs/phase27_frozen_path_external_validation_pack.md` | ✅ Confirmed | N/A | JS is display-only |
| Auto-backup: 10 max, 24h interval, manual/pre-restore not pruned | All | Phase 24F.1 | `docs/phase24f1_auto_backup_scheduling.md`; `app/persistence/backup_restore.py` | ✅ Configured | N/A | No enterprise DR or cloud/offsite |
| /readyz health endpoint: lightweight, no model run | All | Phase 26D | `main_web.py`; `app/observability.py`; `docs/deployment_runbook.md` | ✅ Implemented | N/A | No model run triggered |

---

## Materiality Scale

| Symbol | Meaning |
|--------|---------|
| ✅ Validated | Within tolerance; no action required |
| 🟢 Low | Small residual; acceptable; documented |
| 🟡 Informational | Expected behavior under frozen DS path; not a defect |
| ❌ Not wired / Not validated | Out of scope or pending; not a runtime defect |

---

## Out-of-Scope Claims (Not Validated in This Pack)

| Item | Reason |
|------|--------|
| Generic/new-project path | No Excel reference exists |
| Construction IDC (M1–M18, C.16) | Not wired into runtime |
| Dynamic sculpting solver | Frozen-template path only |
| Multi-user / RBAC | Not implemented |
| SSO / OAuth / SAML | Not implemented |
| Bank/lender/audit/certification | Internal pilot tooling only |
| SaaS-ready / multi-tenant | Not implemented |
