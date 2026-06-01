# FincoGPT Validation Pack - Index

This index helps reviewers navigate the complete validation evidence package for the TUHO and Oborovo frozen-template financial model path.

---

## Document Map

### Entry Point

| Document | Purpose |
|----------|---------|
| `validation_pack_executive_summary.md` | **Start here** - one-page overview of validated scope, anchors, residuals, non-claims |
| `phase39_external_model_review_package.md` | Structured reviewer-run protocol for scoped independent review |
| `model_reviewer_package_manifest.md` | Reviewer package reading order, artifact map, and exclusions |

### Core Validation Documents

| Document | Purpose | Phase |
|----------|---------|-------|
| `phase27_frozen_path_external_validation_pack.md` | Full narrative validation pack | Phase 27 |
| `phase27_validation_evidence_matrix.md` | Dense evidence table - all claims with sources | Phase 27 |
| `phase23u_full_excel_parity_pack.md` | TUHO + Oborovo parity tables, residual classification | Phase 23U |
| `phase23t_senior_debt_amount_dscr_residual_bridge.md` | Senior debt amount bridge and DS residual analysis | Phase 23T |

### Oborovo SHL and Distribution Documents

| Document | Purpose | Phase |
|----------|---------|-------|
| `phase23k_oborovo_shl_opening_balance_bridge.md` | Oborovo SHL opening balance diagnostic | Phase 23K |
| `phase23l_oborovo_shl_amount_factory_correction.md` | Oborovo SHL amount correction (13,547 -> 14,621 kEUR) | Phase 23L |
| `phase23o_oborovo_distribution_lockup_policy_parity.md` | Distribution lock-up policy fix | Phase 23O |
| `phase23p_oborovo_post_lockup_parity_snapshot.md` | Post-lockup parity confirmation | Phase 23P |
| `phase23h_oborovo_shl_distribution_lockup_fix.md` | SHL/distribution lock-up guard | Phase 23H |

### TUHO Documents

| Document | Purpose | Phase |
|----------|---------|-------|
| `phase23f_tuho_frozen_factory_opt_in_candidate.md` | TUHO frozen factory opt-in candidate | Phase 23F |
| `phase23s_combined_tuho_oborovo_frozen_senior_ds_regression_snapshot.md` | Combined regression snapshot | Phase 23S |
| `phase23q_oborovo_frozen_senior_ds_fixture_extraction.md` | Oborovo senior DS fixture extraction | Phase 23Q |

### Pilot and Operational Documents

| Document | Purpose | Phase |
|----------|---------|-------|
| `pilot_user_guide.md` | Non-technical user guide - quick start, validated scope, non-claims | Phase 25B |
| `deployment_runbook.md` | Operational runbook - install, env vars, health, backup | Phase 26D |
| `phase24_closeout_pilot_readiness_review.md` | Pilot readiness review closeout | Phase 24 |
| `phase25b_onboarding_help_demo_mode.md` | Onboarding/help implementation doc | Phase 25B |
| `model_reviewer_run_checklist.md` | Reviewer-run execution checklist | Phase 39 |
| `model_reviewer_issue_log_template.md` | Reviewer question and exception log template | Phase 39 |

### Tests Supporting Validation

| Test File | What It Covers |
|-----------|---------------|
| `tests/test_phase27_frozen_path_external_validation_pack.py` | Phase 27 pack completeness and non-overclaiming |
| `tests/test_phase23u_full_excel_parity_pack.py` | TUHO + Oborovo DS fixture parity, DSCR trajectory |
| `tests/test_phase23t_senior_debt_amount_dscr_residual_bridge.py` | Senior debt amount bridge, DS residual |
| `tests/test_phase23o_oborovo_distribution_lockup_policy_parity.py` | Distribution lock-up policy |
| `tests/test_phase23h_oborovo_shl_distribution_lockup_fix.py` | SHL/distribution lock-up guard |
| `tests/test_shl_waterfall_priority.py` | SHL waterfall priority |
| `tests/test_tuho_shl_calibration.py` | TUHO SHL calibration |

---

## Document Reading Paths

### For a quick review (30 minutes)
1. `validation_pack_executive_summary.md` <- START
2. `validation_pack_index.md` <- YOU ARE HERE
3. `phase27_frozen_path_external_validation_pack.md` (Section 1-6)
4. `external_reviewer_checklist.md` (sign off)

### For a thorough review (2-3 hours)
1. `validation_pack_executive_summary.md` <- START
2. `validation_pack_index.md` <- YOU ARE HERE
3. `phase27_frozen_path_external_validation_pack.md` (full)
4. `phase27_validation_evidence_matrix.md` (cross-reference with pack)
5. `phase23u_full_excel_parity_pack.md` (parity tables)
6. `phase23t_senior_debt_amount_dscr_residual_bridge.md` (residuals)
7. `phase23o_oborovo_distribution_lockup_policy_parity.md` (lock-up)
8. `external_reviewer_checklist.md` (sign off)

### For technical model review
1. `phase27_frozen_path_external_validation_pack.md` Section: Evidence Table
2. `phase27_validation_evidence_matrix.md`
3. Source test files (`tests/test_phase23u_*.py`)
4. `phase23f_tuho_frozen_factory_opt_in_candidate.md`
5. `phase23l_oborovo_shl_amount_factory_correction.md`

---

## What Is Not Included in This Pack

| Item | Reason |
|------|--------|
| PDF version | Markdown is PDF-ready but not auto-generated; generate PDF from markdown if required |
| Generic project validation | No Excel reference for generic path |
| Construction IDC runtime | M1-M18 not wired; C.16 Project Rights not wired |
| Sculpting solver | Not promoted; frozen-template path only |
| Multi-user / RBAC | Not implemented; single-user internal pilot mode |
| Bank/lender/audit certification | Internal pilot tooling only |

---

---

## Pilot Launch Documentation (Phase 41)

- [Phase 41 Pilot Launch Overview](phase41_pilot_launch_documentation_handoff.md) — trusted pilot GO, launch scope, guardrails
- [Pilot Launch Handoff Checklist](pilot_launch_handoff_checklist.md) — pre-launch operator sign-off
- [Pilot Scope Confirmation Note](pilot_scope_confirmation_note.md) — shareable note for pilot users
- [Pilot Issue Intake Template](pilot_issue_intake_template.md) — issue reporting form
- [Phase 41 Launch Readiness Matrix](phase41_pilot_launch_readiness_matrix.md) — all launch areas status

*Generated: Phase 41. For internal pilot review navigation.*
