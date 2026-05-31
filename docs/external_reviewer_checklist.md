# FincoGPT Validation Pack - External Reviewer Checklist

> **Important:** This checklist is for internal pilot review only.  
> Signing this checklist does **not** constitute a bank approval, lender approval, certified audit, or any form of external certification.  
> It is an informal internal review sign-off.
> For a structured reviewer run, use this checklist together with
> `phase39_external_model_review_package.md`,
> `model_reviewer_run_checklist.md`, and
> `model_reviewer_issue_log_template.md`.

---

## Section A: Model Scope Confirmation

- [ ] Acknowledge TUHO Wind (72 MW, Croatia) is validated as frozen-template
- [ ] Acknowledge Oborovo Solar (53.63 MW, Croatia) is validated as frozen-template
- [ ] Acknowledge generic/new-project path is **not validated** - review independently
- [ ] Acknowledge FincoGPT is single-user internal pilot tooling; no multi-tenant or SaaS claim

---

## Section B: TUHO Frozen-Path Checks

- [ ] Senior debt amount = **43,359.0 kEUR** confirmed vs Excel source
- [ ] Senior DS fixture parity (op_idx 0-13): diff < 0.5 kEUR confirmed
- [ ] DSCR trajectory: 1.16-1.46x (target 1.20x) - inflation is **expected** under frozen DS path, not a defect
- [ ] Equity IRR with CO2: 11.81% vs Excel 11.61% (+0.20 pp, within +/-1.0 pp tolerance)
- [ ] CO2 Y1 revenue: ~611 kEUR confirmed
- [ ] No distributions while SHL outstanding (no SHL for TUHO in this model)
- [ ] TUHO merchant periods (op_idx 14+): no debt service, DSCR = inf - **expected**, not a defect

---

## Section C: Oborovo Frozen-Path Checks

- [ ] Senior debt amount = **42,852.27 kEUR** confirmed (+0.27 kEUR rounding vs Excel 42,852.0)
- [ ] Senior DS fixture parity (op_idx 0-26): diff ~0 confirmed
- [ ] op_idx 27 DS residual: **+16.84 kEUR** - within 20 kEUR tolerance [Validated]
- [ ] SHL opening balance: **~15,790 kEUR** (14,621 principal + 1,169 IDC) confirmed
- [ ] SHL amount corrected: **14,621.0 kEUR** (was 13,547.2 before Phase 23L correction)
- [ ] SHL IDC: **1,169.0 kEUR** confirmed
- [ ] SHL tenor: **20-year bullet** confirmed; cleared at op_idx 38 (2049-12-31)
- [ ] Distribution lock-up policy confirmed: **no distributions while SHL outstanding**
- [ ] First valid distribution: **op_idx 39 (2050-06-30)**, amount ~2,994 kEUR - after SHL cleared at op_idx 38

---

## Section D: Senior Debt Fixture Review

- [ ] TUHO senior debt schedule matches Excel fixture source
- [ ] Oborovo senior debt schedule matches Excel fixture source
- [ ] No runtime formula changes to senior debt service calculation since fixture extraction
- [ ] Senior debt service parity confirmed for all validated periods

---

## Section E: DSCR Trajectory Review

- [ ] TUHO DSCR 1.16-1.46x (above target 1.20x) is **expected** under frozen senior DS path - not a runtime defect
- [ ] Oborovo DSCR 1.15-2.37x (early vs target 1.15x, late vs target 1.35x) is **expected** under frozen senior DS path - not a runtime defect
- [ ] DSCR inflation mechanism: frozen DS schedule declines slower than FCF grows over time
- [ ] No corrective action required for DSCR inflation - this is by design

---

## Section F: SHL / Distribution Lock-Up Review

- [ ] Oborovo SHL distribution lock-up gate prevents distributions while SHL balance > 0
- [ ] SHL cleared at op_idx 38 (2049-12-31) - 20-year bullet confirmed
- [ ] First distribution at op_idx 39 (2050-06-30) confirmed - SHL was cleared in prior period
- [ ] No early distributions in op_idx 0-37 confirmed

---

## Section G: Residual / Materiality Review

- [ ] TUHO op_idx 12 DS residual (+0.07 kEUR): **negligible**, fixture 4dp rounding
- [ ] Oborovo op_idx 27 DS residual (+16.84 kEUR): **within 20 kEUR tolerance**, acceptable
- [ ] All residuals classified as expected under frozen DS path, not as runtime defects
- [ ] No residual exceeds stated tolerance thresholds

---

## Section H: Limitation and Non-Claim Review

- [ ] Generic/new-project path is **not validated** - no Excel reference exists
- [ ] Construction IDC (M1-M18) is **not wired** into runtime
- [ ] C.16 Project Rights is **not wired** into runtime
- [ ] Sculpting solver is **not promoted** (partial_pay_sweep not approved; flat/min DSCR not approved)
- [ ] Multi-user / RBAC: **not implemented**
- [ ] SSO / OAuth / SAML: **not implemented**
- [ ] Bank / lender approval: **not claimed** (internal pilot tooling only)
- [ ] Certified external audit: **not claimed** (internal review tooling only)
- [ ] SaaS-ready / multi-tenant: **not claimed**
- [ ] Backend remains sole calculation authority (JS is display-only)

---

## Section I: Recommended Questions for Reviewer

1. Do the TUHO senior debt and DSCR values align with your expectations based on the Excel source?
2. Is the Oborovo SHL opening balance of ~15,790 kEUR and the 20-year bullet structure consistent with the project financing term sheet?
3. Is the distribution lock-up policy (no distributions while SHL outstanding) consistent with the financing documents?
4. Is the DSCR inflation in later periods (frozen DS path) understood and acceptable for this analysis?
5. Are there any periods or metrics that require further investigation before reliance on model outputs?

---

## Section J: Reviewer Sign-Off

> **This sign-off is informal and non-certifying. It confirms that the reviewer has examined the documented validation evidence and acknowledges the scope and limitations.**

| Item | Response |
|------|---------|
| Reviewer name | |
| Review date | |
| Organisation / role | |
| I have read the Validation Pack Executive Summary | [ ] |
| I have reviewed the TUHO frozen-path validation evidence | [ ] |
| I have reviewed the Oborovo frozen-path validation evidence | [ ] |
| I understand the validated scope (TUHO + Oborovo frozen-template) | [ ] |
| I understand the out-of-scope items (generic path, IDC, sculpting) | [ ] |
| I understand this is not a bank/lender/audit certification | [ ] |
| Questions / concerns raised (if any) | |

---

*Generated: Phase 27B. Informal internal review checklist - not a certification or approval.*
