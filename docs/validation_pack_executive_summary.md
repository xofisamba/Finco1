# FincoGPT Validation Pack - Executive Summary

> **How to read this pack:** This document is the entry point for any reviewer.  
> Start here, then use the **Validation Pack Index** (`validation_pack_index.md`) to navigate supporting evidence.  
> The **External Reviewer Checklist** (`external_reviewer_checklist.md`) provides a section-by-section sign-off guide.  
> **This is not a bank approval, lender approval, certified audit, or SaaS-ready product claim.**

---

## What Is FincoGPT?

FincoGPT is an internal pilot tool for structured financial modelling of renewable energy projects (wind and solar).  
All calculations are performed by a Python backend engine. Browser-side JS is display-only.

---

## Validated Scope

| Project | Type | Capacity | Status |
|---------|------|----------|--------|
| **TUHO Wind** | Frozen-template | 72 MW (Croatia) | [Reference] Frozen-template parity evidence against Excel |
| **Oborovo Solar** | Frozen-template | 53.63 MW (Croatia) | [Reference] Frozen-template parity evidence against Excel |
| Generic / new projects | Any | Any | [Warning] **Not validated** - review independently |

TUHO and Oborovo are frozen-template paths where the senior debt service schedule is fixture-backed from validated Excel workbooks. Their outputs are considered reliable within documented tolerances.

---

## Key Validation Anchors

### TUHO Wind

| Metric | Value | Status |
|--------|-------|--------|
| Senior debt amount | 43,359.0 kEUR | [Reference] Exact match vs Excel parity evidence |
| Senior DS fixture parity | op_idx 0-13, diff < 0.5 kEUR | [Reference] Frozen-template parity evidence |
| DSCR trajectory | 1.16-1.46x (target 1.20x) | [Info] Expected inflation - frozen DS path |
| Equity IRR (with CO2) | 11.81% vs Excel 11.61% | [Reference] Within +/-1.0 pp of Excel parity evidence |
| CO2 revenue (Y1) | ~611 kEUR | [Reference] Calibrated against frozen-template parity evidence |

### Oborovo Solar

| Metric | Value | Status |
|--------|-------|--------|
| Senior debt amount | 42,852.27 kEUR | [Reference] (+0.27 kEUR rounding) vs Excel parity evidence |
| Senior DS fixture parity | op_idx 0-26, diff ~0 | [Reference] Frozen-template parity evidence |
| op_idx 27 residual | +16.84 kEUR | [Reference] Within 20 kEUR tolerance of Excel parity evidence |
| SHL opening balance | ~15,790 kEUR (14,621 + 1,169 IDC) | [Reference] Frozen-template parity evidence |
| First valid distribution | op_idx 39 / 2050-06-30 | [Reference] After SHL cleared at op_idx 38 in parity evidence |
| DSCR trajectory | 1.15-2.37x (target 1.15/1.35x) | [Info] Expected inflation - frozen DS path |

---

## Residuals and Materiality

| Item | Value | Classification |
|------|-------|---------------|
| TUHO op_idx 12 DS residual | +0.07 kEUR | Low - fixture 4dp rounding |
| Oborovo op_idx 27 DS residual | +16.84 kEUR | Low - within 20 kEUR tolerance |
| TUHO DSCR above target | 1.16-1.46x vs 1.20x | Expected - frozen DS path |
| Oborovo DSCR above target (late) | 1.9-2.4x vs 1.35x | Expected - frozen DS path |

All residuals are classified as **expected under the frozen senior debt service path**, not as runtime defects.

---

## Not Validated

The following are explicitly **not validated** by this pack:

- Generic or new-project paths (no Excel reference)
- Construction IDC runtime (M1-M18, C.16 Project Rights) - not wired
- Live sculpting solver - not promoted (partial_pay_sweep not approved; flat/min DSCR not approved)
- Multi-user, RBAC, SSO, OAuth/SAML
- SaaS-ready or multi-tenant deployment

---

## Non-Claims

FincoGPT and this validation pack are explicitly **NOT**:

| Claim | Status |
|-------|--------|
| Bank / lender approval | [Not included] Not provided |
| Credit analysis | [Not included] Not provided |
| Certified external audit | [Not included] Not provided |
| SaaS-ready / multi-tenant | [Not included] Not implemented |
| Live sculpting solver | [Not included] Frozen fixture-backed schedule |
| Multi-user with RBAC | [Not included] Single-user internal pilot mode |

---

## How to Review This Pack

1. **Read this executive summary** (you are here)
2. **Review the Validation Pack Index** to understand the document structure
3. **Use the Phase 39 reviewer package** for scope, workflow, and issue logging
4. **Use the External Reviewer Checklist** to work through TUHO and Oborovo checks
5. **Cross-reference with the Evidence Matrix** for source-document links
6. **Sign off** using the reviewer sign-off section (informal, non-certification)

---

## Recommended External Review Steps

1. Confirm TUHO senior debt fixture = 43,359.0 kEUR vs Excel
2. Confirm Oborovo senior debt fixture = 42,852.27 kEUR vs Excel
3. Verify DS fixture parity (TUHO: 0-13, Oborovo: 0-27)
4. Review Oborovo op_idx 27 residual (+16.84 kEUR) - within tolerance
5. Verify Oborovo SHL opening = ~15,790 kEUR
6. Verify distribution lock-up policy (no distributions while SHL outstanding)
7. Verify first valid distribution at op_idx 39 (2050-06-30)
8. Confirm DSCR trajectory classification (frozen DS path inflation)
9. Acknowledge generic path is unvalidated
10. Sign the reviewer checklist

---

*Generated: Phase 27B. For internal pilot review only - not for external distribution or certification claim.*
