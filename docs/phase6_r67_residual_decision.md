# Phase 6 — R67 Residual Decision Memo

## Branch
`phase6-r67-residual-decision`

## Status
**Decision / documentation only — no production code changes, no bridge implemented.**

---

## Executive Summary

| Metric | Value |
|--------|------:|
| Observed R67 residual (yr13–30, Python cash tax − Excel) | **+5,271 kEUR** |
| Yr13–20 residual | **+5,697 kEUR** (Python overpays) |
| Yr21–30 residual | **−425 kEUR** (Python underpays) |
| Material identified structural driver | **Useful-life policy/input mismatch** |
| Depreciation standalone CIT impact | **−2,783 kEUR** (opposite sign to total residual) |
| Remaining unallocated | **≈+8,055 kEUR** after depreciation estimate |

**Sign convention:** Positive residual = Python cash tax > Excel. Negative standalone impact = driver partially offsets Python overpayment.

**Recommendation: Provisional acceptance. No bridge. R99 BLOCKED. External/Claude review required before Phase 6 closure.**

---

## R35 / R67 Final Status

### R35 (Taxable Income)
- **Formula:** `R35 = R32 + R34 = R16 + R30 + (−R54)`
- **Components:** EBIT (R16) + Financial Earnings (R30) − Fiscal Reintegration (R54)
- **For TUHO yr13–30:** R54 = 0 → `R35 = EBIT + Financial Earnings`
- **Loss rows R36–R39** do NOT affect R35; they only reduce R41 (Taxable Profit)
- **Source:** Excel P&L sheet rows 13–54, confirmed by formula inspection

### R67 (Corporate Income Tax Cash Outflow)
- **Convention:** `R43/R67 = 18% × annual (H1_R41 + H2_R41)`, with cash tax outflow in H2
- **Timing:** resolved for years 1–12 in prior work

---

## Phase 6 Evidence Summary

| PR | Branch | Key Finding |
|----|--------|-------------|
| #71 | `phase6-cit-h2-annual-trigger` | R43/R67 timing: H2 holds annual cash tax for years 1–12 |
| #75 | `phase6-y13-30-residual-attribution-per-driver` | First-pass attribution: 1,295 kEUR explained, 3,977 kEUR unattributed |
| #76 | `phase6-tax-bridge-counterfactual-attribution` | No-ATAD counterfactual formula does not reproduce Excel R35; formula gap 6,155 kEUR |
| #77 | `phase6-r35-formula-inspection` | **R35 = EBIT + Financial Earnings. NO ATAD.** R36–R39 do not affect R35 |
| #78 | `phase6-dep-r30-excel-crosscheck` | **Excel Dep R30 = 0 for yr21–30** due to 20-year useful life exhaustion |
| — | `phase6-r67-yrs13to30-residual` | 54 tests pass; residual confirmed in Python model |
| — | `phase6-excel-interest-dep-extraction` | Excel data extraction for TUHO yr13–30 |

---

**The +5,271 kEUR R67 residual remains open from a final calibration perspective. This memo does not claim full mathematical closure. It documents the evidence and recommends against a TUHO-specific depreciation bridge before external review.**

---

## Residual Source Decomposition

### Identified Structural Drivers

| Driver | Est. CIT Impact (kEUR) | Direction | Confidence |
|--------|-----------------------:|-----------|------------|
| Useful-life mismatch (Excel 20yr vs Python 30yr) | −2,783 net | Opposite sign to total residual | High (direct extraction) |
| SHL interest (Python fixture vs Excel) | −2,209 | Python SHL lower → underpays tax | Medium (counterfactual) |
| Senior interest delta | −2,023 | Python senior slightly higher → overpays | Medium (counterfactual) |
| EBITDA delta (CF vs P&L) | −1,754 | Python EBITDA higher → overpays | Medium (counterfactual) |
| Loss carryforward (yr13 only) | −2,043 | Excel consumes construction-period losses in yr13 → underpays | High (formula confirmed) |
| Other / interactions | — | Not fully attributed | — |

**⚠️ Driver impacts are not directly additive.** They have mixed signs and interact through the loss carryforward engine. The table shows approximate standalone CIT impacts, not a closed attribution waterfall.

### Useful-Life Profile Detail

Excel Inputs!D358–D379 specifies **20-year useful life** for the main TUHO CAPEX categories (Production Unit/turbines, EPC Contract, Grid connection, Project Rights, and most other main CAPEX items). IDCs / Commitment Fees / Bank Fees use 12-year useful life. Python currently uses a **30-year straight-line** assumption.

This is a **useful-life policy/input mismatch**, not Excel-side accelerated depreciation. Assets are fully depreciated after the explicit 20-year useful life, which is why Excel Dep R30 = 0 for yr21–30.

| Period | Excel Dep R30 | Python book_dep | Delta (Excel−Python) | Annual CIT Impact |
|--------|-------------:|---------------:|----------------------:|-------------------:|
| Yr13–20 | 28,336 kEUR | 19,465 kEUR | **+8,871 kEUR** | **+1,597 kEUR** (Python underpays) |
| Yr21–30 | 0 kEUR | 24,331 kEUR | **−24,331 kEUR** | **−4,380 kEUR** (Python overpays) |
| **Net** | **28,336 kEUR** | **43,796 kEUR** | **−15,460 kEUR** | **−2,783 kEUR** |

Excel 20-year useful life is a project-specific input from the TUHO workbook. Python's 30-year assumption is a canonical modelling choice that diverges from TUHO inputs.

---

## Long-Term Architecture Note

The preferred long-term solution is **not** a TUHO-only depreciation plug. It is a domain/depreciation module with **per-category useful_life_years sourced from project inputs**, allowing each CAPEX category to carry its own useful life from the Inputs sheet. This would eliminate the mismatch for TUHO without requiring project-specific code.

---

## Recommendation

**No bridge. No final acceptance. R99 BLOCKED. External/Claude review required before Phase 6 closure.**

1. Do **not** implement a TUHO-only depreciation bridge — Excel's 20-year useful life schedule is itself a project-specific input; bridging to it would flip the yr21–30 gap
2. Keep Python's 30-year straight-line as canonical for now
3. Document the 20-year vs 30-year useful-life mismatch as a project-specific input divergence
4. Keep R99/R102 BLOCKED
5. Proceed to external/Claude review, then tax validation pack if review agrees with this provisional decision

### Rationale

- The residual is **not** fully explained by the useful-life mismatch — depreciation alone has a net standalone impact (−2,783 kEUR) opposite in sign to the total residual (+5,271 kEUR)
- Remaining unallocated ≈+8,055 kEUR requires external review before any final acceptance
- A bridge to Excel's 20-year schedule would flip the yr21–30 gap from −425 to large positive — not clearly an improvement
- A "keep Python canonical" stance is defensible: the model has a coherent 30-year straight-line policy; Excel's 20-year useful life is a project-specific input divergence
- This is a **provisional decision**, not a final closure — external review must confirm before Phase 6 is considered complete

---

## R99/R102 Status

**BLOCKED / audit-only.**

R99/R102 must not be promoted while the residual remains in provisional-acceptance state:
- No runtime-source promotion
- No SHL FCF opt-in
- No R99 design until validation pack/external review confirms this provisional decision

External review must confirm the residual is acceptable before Phase 6 closure and R99 promotion.

---

## Whether External Review Can Proceed

**External/Claude review can proceed specifically to validate this provisional residual decision and decide whether Phase 6 can move to the tax validation pack.**

This memo does not imply Phase 6 is already externally approved. Reviewers should assess whether the +5,271 kEUR residual is acceptable given the documented useful-life mismatch and whether a configurable per-category depreciation architecture or accept-as-is is the right path.

---

## Recommended Next Branch

| Priority | Branch | Goal |
|----------|--------|------|
| **P1** | **`phase6-tax-validation-pack`** | Compile all Phase 6 evidence into a formal package for bankability / external review. Include: R35 formula, useful-life profiles, residual amount, Python policy rationale, and any known mitigations. |
| Contingent | **`phase6-depreciation-per-category-useful-life`** | Implement domain/depreciation module with per-category useful_life_years sourced from project inputs — the preferred long-term architecture, not a TUHO-only plug. |
| Contingent | **`phase6-r99-runtime-source-promotion-design`** | After validation pack and external review clearance, design R99 runtime-source promotion including guardrails and override mechanisms. |

---

## Validation
- Tests: 54/54 passed (4 suites)
- Production code: NO changes
- Default behavior: NO CHANGE
- R99/R102: BLOCKED