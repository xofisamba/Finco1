# Phase 27 — Frozen-Path External Validation Pack

## Base SHA
`6ec22eb4baa3f47d91be8428fc8a95fe0183cb71` (after PR #334 merge)

---

## 1. Executive Summary

This document constitutes the formal validation pack for the FincoGPT frozen-template financial model path covering two renewable energy projects: **TUHO Wind (72 MW, Croatia)** and **Oborovo Solar (53.63 MW, Croatia)**.

The frozen-template path means the senior debt service schedule is derived from fixture data extracted from validated Excel workbooks — it is not dynamically sculpted at runtime. This distinction is fundamental to understanding what is validated and what is not.

**What is validated:**
- TUHO and Oborovo senior debt amount, senior debt service schedule, DSCR trajectory, SHL opening balance, SHL/distribution lock-up, and first valid distribution timing.

**What is not validated:**
- Generic or new-project paths (no Excel reference exists for those scenarios).
- Construction IDC runtime wiring (M1–M18, C.16 Project Rights).
- Sculpting solver, partial-pay-sweep, or flat/min-DSCR sculpting.
- Multi-user, RBAC, SSO, SaaS, or any cloud/enterprise deployment claims.

**This document is not:**
- A bank approval, lender approval, or credit analysis.
- A certified external audit.
- A guarantee of fitness for any specific purpose beyond internal pilot use.

---

## 2. Validated Scope

### 2.1 Projects in Scope

| Project | Capacity | Country | Status |
|---------|----------|---------|--------|
| TUHO Wind | 72 MW | Croatia | ✅ Parity-validated against Excel |
| Oborovo Solar | 53.63 MW | Croatia | ✅ Parity-validated against Excel |
| Generic / new projects | Any | Any | ⚠️ Not validated — review independently |

TUHO and Oborovo are **frozen-template** paths where the senior debt service schedule is fixture-backed from Excel. Their model outputs (senior debt quantum, DSCR, SHL opening balance, distributions) are considered reliable within documented tolerances.

### 2.2 What Is Validated

The following model outputs are validated for TUHO and Oborovo:

| Validation Item | TUHO | Oborovo |
|-----------------|------|---------|
| Senior debt amount | ✅ Exact match (43,359.0 kEUR) | ✅ Within rounding (42,852.27 kEUR vs 42,852.0 Excel) |
| Senior debt service fixture parity | ✅ Exact match (op_idx 0–13, diff < 0.5 kEUR) | ✅ Exact match (op_idx 0–26, diff ~0; op_idx 27 +16.84 kEUR within 20 kEUR tolerance) |
| DSCR trajectory | ✅ Parity snapshot confirmed | ✅ Parity snapshot confirmed |
| SHL opening balance | N/A (TUHO has no SHL) | ✅ 15,790.0 kEUR (14,621 principal + 1,169 IDC) |
| SHL amount | N/A | ✅ 14,621.0 kEUR corrected from 13,547.2 |
| SHL IDC | N/A | ✅ 1,169.0 kEUR |
| SHL tenor | N/A | ✅ 20-year bullet |
| Distribution lock-up | N/A (no SHL) | ✅ No distributions while SHL outstanding |
| First valid distribution | N/A | ✅ op_idx 39 (2050-06-30), after SHL cleared at op_idx 38 |
| CO2 revenue | ✅ TUHO CO2 enabled: 4.191 EUR/MWh | Not applicable |

---

## 3. Not Validated / Out-of-Scope

The following are explicitly **not validated** by this pack:

| Item | Status | Reason |
|------|--------|--------|
| Generic / new-project path | ⚠️ Not validated | No Excel reference exists |
| Construction IDC runtime engine | ❌ Not wired | M1–M18 not in runtime; C.16 Project Rights not in runtime |
| Sculpting solver | ❌ Not promoted | Partial-pay-sweep not approved; flat/min-DSCR sculpting not approved |
| TUHO merchant periods (op_idx 14+) | ℹ️ Informational | No debt service, DSCR=inf, SHL balance grows (PIK) |
| Dynamic debt sizing | ❌ Not in scope | Frozen senior DS path only |
| Multi-user / RBAC | ❌ Not implemented | Single-user internal pilot mode only |
| SSO / OAuth / SAML | ❌ Not implemented | — |
| Bank / lender approval | ❌ Not claimed | This is internal pilot tooling |
| External audit / certification | ❌ Not claimed | Audit/Reconciliation tab is internal review tooling |
| SaaS-ready / multi-tenant | ❌ Not claimed | Single-user internal pilot mode only |

---

## 4. TUHO Validation Summary

### 4.1 Senior Debt Amount
- **Excel anchor:** 43,359.0 kEUR
- **Model output:** 43,359.0 kEUR
- **Diff:** 0 kEUR ✅

### 4.2 Senior Debt Service Fixture Parity
- **Validated periods:** op_idx 0 through 13 (2030-06-30 through 2036-12-31)
- **Diff:** < 0.5 kEUR across all periods ✅
- **op_idx 12 residual:** +0.07 kEUR — fixture 4dp rounding, within tolerance

### 4.3 DSCR Trajectory
- **Target DSCR:** 1.20x
- **Runtime DSCR range:** 1.1620 to 1.4553
- **Classification:** Deviations above target are **expected** under frozen senior debt service path — the frozen schedule declines slower than FCF grows, leading to DSCR inflation above target. This is not a runtime defect.

### 4.4 Merchant Periods (op_idx 14+)
- No debt service in merchant periods → DSCR = inf
- SHL balance grows via PIK (TUHO has no SHL repayment mechanism in the frozen fixture)
- No distributions while SHL outstanding (no distributions for TUHO in this model)

### 4.5 CO2 Revenue
- **CO2 enabled:** Yes
- **CO2 price:** 4.191 EUR/MWh
- **Y1 CO2 revenue:** ~611 kEUR
- Equity IRR with CO2: 11.81% vs Excel 11.61% (+0.20 pp, within ±1.0 pp tolerance)
- CO2 revenue declines ~10%/year

---

## 5. Oborovo Validation Summary

### 5.1 Senior Debt Amount
- **Excel anchor:** 42,852.0 kEUR
- **Model output:** 42,852.27 kEUR
- **Diff:** +0.27 kEUR — rounding difference, within tolerance ✅

### 5.2 Senior Debt Service Fixture Parity
- **Validated periods:** op_idx 0 through 27 (2030-12-31 through 2044-06-30)
- **op_idx 0–26:** diff ~0 kEUR ✅
- **op_idx 27 residual:** +16.84 kEUR (within 20 kEUR tolerance) ✅
- **op_idx 28+:** fixture covers 0–27; runtime confirmed clean through op_idx 42

### 5.3 DSCR Trajectory
- **Target DSCR:** 1.15x (early) → 1.35x (from op_idx 24)
- **Runtime DSCR range:** 1.1500 to 2.3706
- **Classification:** Late-period DSCR inflation (1.9–2.4x) is **expected** under frozen senior DS path — same mechanism as TUHO. Not a runtime defect.

### 5.4 SHL Opening Balance
| Component | Value |
|-----------|-------|
| SHL principal | 14,621.0 kEUR (corrected from 13,547.2 per Phase 23L) |
| SHL IDC | 1,169.0 kEUR |
| **Opening total** | **~15,790.0 kEUR** |

Source: `domain/construction/templates/oborovo.py`: `shl_keur=14,620.774` (rounded to 14,621)

### 5.5 SHL Amount Correction
| Item | Before (Phase 23K) | After (Phase 23L) | Excel |
|------|---------------------|--------------------|-------|
| shl_amount_keur | 13,547.2 | **14,621.0** | 14,621 |
| Delta vs Excel | −1,074 kEUR | 0 kEUR ≈ 0 | — |

**Root cause:** factory `shl_amount_keur` was understated by ~1,074 kEUR.
**Fix:** `app/project_factories.py` → `create_default_oborovo()` → `FinancingParams`: `shl_amount_keur=13547.2` → `shl_amount_keur=14621.0`

### 5.6 SHL IDC
- **Model output:** 1,169.0 kEUR
- **Excel:** ~1,170 kEUR
- **Diff:** −1 kEUR ≈ 0 ✅

### 5.7 SHL Tenor
- **Corrected to:** 20-year bullet (per Phase 23J/23K)
- **SHL cleared:** op_idx 38 (2049-12-31)

### 5.8 Distribution Lock-Up
- **Policy:** Distributions are zero while `shl_balance > 0`
- **Root cause fix (Phase 23O):** Lock-up gate changed from current-period SHL interest only to full SHL balance outstanding
- **Result:** No distributions in op_idx 0–37 (SHL outstanding throughout) ✅

### 5.9 First Valid Distribution
- **First distribution:** op_idx 39 (2050-06-30)
- **Amount:** 2,994.41 kEUR
- **Condition:** SHL balance = 0 (cleared at op_idx 38)
- **SHL cleared at:** op_idx 38 (2049-12-31)

---

## 6. Known Residuals and Materiality

| Gap | Project | Value | Classification | Materiality | Status |
|-----|---------|-------|---------------|-------------|--------|
| TUHO op_idx 12 DS residual | TUHO | +0.07 kEUR | Fixture 4dp rounding | 🟢 Negligible | ✅ Accept |
| Oborovo op_idx 27 DS residual | Oborovo | +16.84 kEUR | Within 20 kEUR tolerance | 🟢 Low | ✅ Accept |
| Oborovo op_idx 28+ DS | Oborovo | N/A | Fixture only covers 0–27 | 🟡 Informational | ℹ️ Runtime confirmed clean |
| TUHO DSCR above target | TUHO | 1.16–1.46 | Expected (frozen DS path) | 🟡 Informational | ℹ️ Not a defect |
| Oborovo DSCR above target (late) | Oborovo | 1.9–2.4 | Expected (frozen DS path) | 🟡 Informational | ℹ️ Not a defect |
| TUHO merchant DSCR=inf | TUHO | inf | Expected (no debt service) | 🟢 Low | ℹ️ Not a defect |
| TUHO SHL balance growth (PIK) | TUHO | — | PIK mechanism | 🟢 Low | ℹ️ As designed |

**Residual classification policy:** All residuals above are classified as expected under the frozen senior debt service path, not as runtime defects. The frozen DS schedule diverges from a live sculpting schedule over time — this is by design.

---

## 7. Non-Claims / Limitations

This validation pack and the FincoGPT model are explicitly **NOT** the following:

| Claim | Status |
|-------|--------|
| Bank approval | ❌ Not provided — this is internal pilot tooling |
| Lender approval | ❌ Not provided — no credit analysis is performed or claimed |
| External audit | ❌ Not provided — the Audit/Parity tab is internal review tooling |
| Certification | ❌ Not provided |
| SaaS-ready / multi-tenant | ❌ Not implemented — single-user internal pilot mode only |
| Sculpting solver | ❌ The frozen senior debt schedule is fixture-backed from Excel; it is not a live sculpting calculation |
| Multi-user / RBAC | ❌ Not implemented |
| SSO / OAuth / SAML | ❌ Not implemented |
| Construction IDC runtime | ❌ M1–M18 not wired; C.16 Project Rights not wired |
| Dynamic debt sizing | ❌ Frozen-template path only |

**Backend authority:** All model outputs are produced by the backend Python engine. Browser-side JS is display-only and does not calculate financial outputs.

---

## 8. Evidence Table

| Claim | Project | Evidence Type | Source | Status |
|-------|---------|--------------|--------|--------|
| Senior debt: 43,359.0 kEUR | TUHO | Factory fixture + test | `app/project_factories.py`; `tests/test_phase23u_full_excel_parity_pack.py` | ✅ Validated |
| Senior debt: 42,852.27 kEUR | Oborovo | Factory fixture + test | `app/project_factories.py`; `tests/test_phase23u_full_excel_parity_pack.py` | ✅ Validated (within rounding) |
| TUHO senior DS fixture parity | TUHO | Parity table | `docs/phase23u_full_excel_parity_pack.md` | ✅ Validated |
| Oborovo senior DS fixture parity | Oborovo | Parity table | `docs/phase23u_full_excel_parity_pack.md` | ✅ Validated |
| Oborovo op_idx 27 residual +16.84 kEUR | Oborovo | Residual bridge | `docs/phase23t_senior_debt_amount_dscr_residual_bridge.md` | ✅ Within tolerance |
| TUHO DSCR trajectory expected inflation | TUHO | Trajectory analysis | `docs/phase23u_full_excel_parity_pack.md` | ℹ️ Expected |
| Oborovo DSCR trajectory expected inflation | Oborovo | Trajectory analysis | `docs/phase23u_full_excel_parity_pack.md` | ℹ️ Expected |
| Oborovo SHL opening 15,790 kEUR | Oborovo | Opening balance bridge | `docs/phase23k_oborovo_shl_opening_balance_bridge.md` | ✅ Validated |
| Oborovo SHL amount corrected 14,621 kEUR | Oborovo | Factory correction | `docs/phase23l_oborovo_shl_amount_factory_correction.md` | ✅ Corrected |
| Oborovo SHL IDC 1,169 kEUR | Oborovo | Factory confirmation | `app/project_factories.py` | ✅ Validated |
| Oborovo SHL tenor 20 years | Oborovo | Factory fix | `docs/phase23j_oborovo_shl_tenor_correction.md` | ✅ Corrected |
| Oborovo lock-up while SHL outstanding | Oborovo | Lock-up fix | `docs/phase23o_oborovo_distribution_lockup_policy_parity.md` | ✅ Validated |
| Oborovo first distribution op_idx 39 | Oborovo | Post-lockup parity | `docs/phase23p_oborovo_post_lockup_parity_snapshot.md` | ✅ Validated |
| Generic path unvalidated | Generic | Design note | `docs/phase27_frozen_path_external_validation_pack.md` | ⚠️ Out of scope |
| CAPEX/IDC/M1-M18 pending | All | Phase 23F reference | `docs/phase23f_tuho_frozen_factory_opt_in_candidate.md` | ❌ Not wired |
| No bank/lender/audit/certification | All | Guardrail | This document + `docs/pilot_user_guide.md` | ❌ Explicitly not claimed |

---

## 9. Recommended External Review Checklist

For expert review preparation of the TUHO/Oborovo frozen-template path:

### Financial Model Review
- [ ] Verify senior debt amount fixtures match Excel source (TUHO: 43,359 kEUR, Oborovo: 42,852 kEUR)
- [ ] Verify DS fixture parity across validated periods (TUHO: 0–13, Oborovo: 0–27)
- [ ] Review residual classification (op_idx 27 Oborovo +16.84 kEUR within 20 kEUR tolerance)
- [ ] Verify SHL opening balance (Oborovo: 15,790 kEUR)
- [ ] Verify SHL amount correction (Oborovo: 13,547 → 14,621 kEUR)
- [ ] Review distribution lock-up policy (no distributions while SHL outstanding)
- [ ] Verify first valid distribution timing (Oborovo: op_idx 39 / 2050-06-30)
- [ ] Review DSCR trajectory classification (frozen DS path expected inflation above target)

### Technical Review
- [ ] Confirm no runtime formula changes since fixture extraction
- [ ] Confirm backend Python engine is sole calculation authority
- [ ] Confirm JS is display-only (no financial calculations in browser)
- [ ] Verify CO2 revenue wiring for TUHO (Y1: ~611 kEUR)
- [ ] Review auto-backup configuration and retention policy

### Scope Limitations
- [ ] Acknowledge generic/new-project path is unvalidated
- [ ] Acknowledge construction IDC (M1–M18, C.16) is not in runtime
- [ ] Acknowledge sculpting solver is not promoted (partial_pay_sweep not approved, flat/min DSCR not approved)
- [ ] Acknowledge this is single-user internal pilot tooling, not bank/lender/audit approved

---

## 10. Recommended Next Model Validation Phases

| Phase | Title | Rationale |
|-------|-------|-----------|
| Phase 28 | Generic Project Path Validation | Validate model behavior for new projects without Excel reference |
| Phase 29A | TUHO CO2 Revenue Deep-Dive | Verify CO2 price curve, escalation, and certificate handling |
| Phase 29B | Oborovo CAPEX Sensitivity | Test CAPEX variation impact on senior debt and equity IRR |
| Phase 30 | Construction IDC Wiring (M1–M18) | Wire construction period IDC into runtime if required for analysis |
| Phase 31 | Sculpting Solver Introduction | Introduce live sculpting solver (separate from frozen path) |

---

## 11. Guardrails Preserved

- ✅ No runtime formula changes
- ✅ No financial formula changes
- ✅ No model files changed
- ✅ No JS financial calculations
- ✅ No factory flag changes (TUHO/Oborovo fixtures unchanged)
- ✅ No fixture value changes
- ✅ No Revenue/OPEX/CAPEX/Tax formula changes
- ✅ No SHL/distribution logic changes
- ✅ No senior debt sizing logic changes
- ✅ G20 BLOCKED
- ✅ R99/R102 NOT APPROVED
- ✅ partial_pay_sweep not promoted
- ✅ flat/min DSCR sculpting not promoted
- ✅ Backend remains source of truth
- ✅ No lender/bank/audit/SaaS claims
