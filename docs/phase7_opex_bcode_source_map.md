# Phase 7 — OPEX B-Code Source Mapping (Stage 1)

## Purpose

Audit-grade source mapping between TUHO Excel OpEx sheet B-codes and the Python OPEX line-item template (`domain/opex/templates/tuho.py`). Stage 1 of the OPEX Phase 7 workstream. No production runtime changes.

## Source Basis

- **Excel workbook:** `20260330_TUHO_BP.xlsm`
- **Excel sheet:** `OpEx`
- **Python template:** `domain/opex/templates/tuho.py`
- **Python offline engine:** `domain/opex/engine.py`

## The +733 kEUR RUNTIME_OPT_IN Gap — Not a Calibration Error

| Source | 30-Year Total |
|--------|--------------|
| Excel CF!R38 = OpEx!R105 incl. contingencies | 84,675 kEUR |
| Python offline OPEX engine | 84,674.78 kEUR |
| Python runtime (flag-off, `use_opex_line_item_engine=False`) | 83,942 kEUR |
| **Delta** | **+733 kEUR** |

**Conclusion:** The delta is NOT an OPEX calibration error. The Python offline engine matches Excel within ±0.01 kEUR per year. The 733 kEUR gap is a `RUNTIME_OPT_IN` gap — `use_opex_line_item_engine` is `False` by default in runtime, meaning the runtime cash flow uses the simplified (non-line-item) OPEX path, not the offline line-item engine.

**Therefore:**
- Do NOT recalibrate OPEX
- Do NOT change formulas
- Do NOT enable runtime in this branch
- This branch only maps B-codes and validates source ownership

## B-Code Hierarchy

### B.01 Technical Management
| B-Code | Name | Excel Row | Excel Base (kEUR/yr) | Inflation | Python Code | Basis |
|--------|------|----------|---------------------|-----------|------------|-------|
| B.01.1 | Asset Management Contract | OpEx | 138.0 | 2% | B.01.1 | FIXED_ANNUAL_KEUR |
| B.01.2 | Operation Management Contract | OpEx | 67.0 | 2% | B.01.2 | FIXED_ANNUAL_KEUR |
| B.01.3 | Performance monitoring | OpEx | 35.0 | 2% | B.01.3 | FIXED_ANNUAL_KEUR |
| B.01.4 | Technical Inspections | OpEx | 0.0 | 2% | B.01.4 | FIXED_ANNUAL_KEUR |
| B.01.5 | Meteorological / Weather | OpEx | 18.0 | 2% | B.01.5 | FIXED_ANNUAL_KEUR |
| B.01.9 | Bazefield / Onboarding | OpEx | 22.0 | 2% | B.01.6 | FIXED_ANNUAL_KEUR |

> Note: Python B.01.6 = "Bazefield" maps to Excel B.01.9. Code mismatch is structural.

### B.02 Infrastructure Maintenance
| B-Code | Name | Excel Row | Excel Base (kEUR/yr) | Inflation | Python Code | Basis |
|--------|------|----------|---------------------|-----------|------------|-------|
| B.02.1 | O&M Preventive & Corrective | OpEx | explicit | 0% | B.02.1 | EXPLICIT_SCHEDULE |
| B.02.2 | Minor Maintenance | OpEx | 27.0 | 0% | B.02.2 | FIXED_ANNUAL_KEUR |
| B.02.3 | HV Substation & O&M Building | OpEx | 0.0 | 0% | B.02.3 | FIXED_ANNUAL_KEUR |
| B.02.4 | HSE Prevention Plan | OpEx | 6.0 | 0% | B.02.4 | FIXED_ANNUAL_KEUR |
| B.02.5 | Met Station Maintenance | OpEx | 0.0 | 0% | B.02.5 | FIXED_ANNUAL_KEUR |
| B.02.6 | Blade Maintenance | OpEx | 0.0 | 0% | B.02.6 | FIXED_ANNUAL_KEUR |
| B.02.7 | Vehicle / Special Equipment | OpEx | 8.0 | 0% | B.02.7 | FIXED_ANNUAL_KEUR |
| B.02.8 | Others | OpEx | 0.0 | 0% | B.02.8 | FIXED_ANNUAL_KEUR |

> Note: B.02.1 is an explicit 30-year annual schedule (not inflated). B.02 group inflation = 0%.

### B.03 Maintain Site
| B-Code | Name | Excel Row | Excel Base (kEUR/yr) | Inflation | Python Code | Basis |
|--------|------|----------|---------------------|-----------|------------|-------|
| B.03.1 | Vegetation management | OpEx | 28.0 | 2% | B.03.1 | FIXED_ANNUAL_KEUR |
| B.03.2 | Repair roads | OpEx | 20.0 | 2% | B.03.2 | FIXED_ANNUAL_KEUR |
| B.03.3 | Pest control | OpEx | 10.0 | 2% | B.03.3 | FIXED_ANNUAL_KEUR |
| B.03.9 | Others / Inspections | OpEx | 10.0 | 2% | B.03.4 | FIXED_ANNUAL_KEUR |

### B.04 Clean Material
| B-Code | Name | Excel Row | Excel Base (kEUR/yr) | Inflation | Python Code | Basis |
|--------|------|----------|---------------------|-----------|------------|-------|
| B.04.2 | Subscription to water supply | OpEx | 1.0 | 2% | B.04.2 | FIXED_ANNUAL_KEUR |
| B.04.3 | Others | OpEx | 1.0 | 2% | B.04.3 | FIXED_ANNUAL_KEUR |

> Note: Python B.04.1 ("Clean panel/blades") has no Excel counterpart in the fixture (0 kEUR base, not in mapping).

### B.05 Security
| B-Code | Name | Excel Row | Excel Base (kEUR/yr) | Inflation | Python Code | Basis |
|--------|------|----------|---------------------|-----------|------------|-------|
| B.05.1 | Surveillance systems | OpEx | 30.0 | 2% | B.05.1 | FIXED_ANNUAL_KEUR |
| B.05.2 | Surveillance patrols | OpEx | 15.0 | 2% | B.05.2 | FIXED_ANNUAL_KEUR |

### B.06 Insurance
| B-Code | Name | Excel Row | Excel Base (kEUR/yr) | Inflation | Python Code | Basis |
|--------|------|----------|---------------------|-----------|------------|-------|
| B.06.1 | Operation All Risk w/ BI | OpEx | 400.0 | 2% | B.06.1 | FIXED_ANNUAL_KEUR |

### B.07 Lease & Property Tax
| B-Code | Name | Excel Row | Excel Base (kEUR/yr) | Inflation | Python Code | Basis |
|--------|------|----------|---------------------|-----------|------------|-------|
| B.07.1 | Land Leases | OpEx | 200.0 | 2% | B.07.1 | FIXED_ANNUAL_KEUR |
| B.07.4 | Property tax | OpEx | 48.88 | 2% | B.07.2 | FIXED_ANNUAL_KEUR |

### B.08 Power Expenses
| B-Code | Name | Excel Row | Excel Base (kEUR/yr) | Inflation | Python Code | Basis |
|--------|------|----------|---------------------|-----------|------------|-------|
| B.08.1 | Power consumption | OpEx | 50.0 | 2% | B.08.1 | FIXED_ANNUAL_KEUR |
| B.08.2 | Grid Usage fee | OpEx | 30.0 | 2% | B.08.2 | FIXED_ANNUAL_KEUR |

### B.09 Telecom Fees
| B-Code | Name | Excel Row | Excel Base (kEUR/yr) | Inflation | Python Code | Basis |
|--------|------|----------|---------------------|-----------|------------|-------|
| B.09 | (all items) | OpEx | 0.0 | 0% | B.09.1, B.09.2 | FIXED_ANNUAL_KEUR |

> Note: Both B.09 items are 0 kEUR in Excel and Python — zero line, structurally unmapped.

### B.10 Audit & Accounting & Legal
| B-Code | Name | Excel Row | Excel Base (kEUR/yr) | Inflation | Python Code | Basis |
|--------|------|----------|---------------------|-----------|------------|-------|
| B.10.1 | Auditors closing | OpEx | 8.0 | 2% | B.10.1 | FIXED_ANNUAL_KEUR |
| B.10.2 | Accounting closing | OpEx | 8.0 | 2% | B.10.2 | FIXED_ANNUAL_KEUR |
| B.10.3 | Legal closing | OpEx | 3.0 | 2% | B.10.3 | FIXED_ANNUAL_KEUR |

### B.11 Bank Fees
| B-Code | Name | Excel Row | Excel Base (kEUR/yr) | Inflation | Python Code | Basis |
|--------|------|----------|---------------------|-----------|------------|-------|
| B.11.1 | Agency Fee | OpEx | 20.0 | 2% | B.11.1 | FIXED_ANNUAL_KEUR + ACTIVE_FLAG |

> Active Y1-Y14 only (14 active flags, 16 inactive). Excel Y1-Y14 base = 20 kEUR.

### B.12 Environmental & Social Management
| B-Code | Name | Excel Row | Excel Base (kEUR/yr) | Inflation | Python Code | Basis |
|--------|------|----------|---------------------|-----------|------------|-------|
| B.12.1 | Mitigation measures | OpEx | 50.0 | 2% | B.12.1 | FIXED_ANNUAL_KEUR |
| B.12.3 | Fauna & Flora Monitoring | OpEx | 30.0 | 2% | B.12.3 | FIXED_ANNUAL_KEUR |

### B.13 Contingencies
| B-Code | Name | Excel Row | Excel Base (kEUR/yr) | Inflation | Python Code | Basis |
|--------|------|----------|---------------------|-----------|------------|-------|
| B.13 | Contingencies 6% | OpEx | 6% of B.01-B.12 | 0% | B.13.1 | PCT_OF_SELECTED_GROUPS |

> B.13 = 6% × sum(B.01:B.12) applied as contingency on top of selected groups. Does not self-reference. Total including contingencies: 84,674.78 kEUR (matches Excel).

### Groups C, D, E, F — Out of Scope
Groups C, D, E, F are zero in TUHO. Documented as zero/out-of-scope.

## Special Cases

### B.02.1 — Explicit Schedule
B.02.1 (O&M Preventive & Corrective) uses `EXPLICIT_SCHEDULE` basis with a 30-year explicit array. Not inflated. The explicit schedule is:
```
Year 1-2:   385.6 kEUR
Year 3-5:   465.6 kEUR
Year 6-10:  588.0 kEUR
Year 11-15: 628.0 kEUR
Year 16-20: 676.0 kEUR
Year 21-25: 756.0 kEUR
Year 26-30: 828.0 kEUR
```

### B.11 — Active Flag Y1-Y14 Only
B.11.1 Agency Fee is active only in years 1-14. The `active_flags` tuple is `(True,)*14 + (False,)*16`. Excel Y15-Y30 does not include this cost.

### B.13 — Contingency 6%
B.13 is computed as 6% of the sum of B.01-B.12 using `PCT_OF_SELECTED_GROUPS` basis. The selected groups tuple is `("B.01", ..., "B.12")`. B.13 does not include itself.

### Annual OpEx vs Semiannual CF Split
The Python OPEX engine computes on an annual basis. The runtime cash flow splits each year into two semiannual periods (H1, H2). The OPEX values are halved per half-year. This means:
- Annual total = 84,674.78 kEUR
- Semiannual per period (avg) = ~1,411 kEUR per period

## Confidence Taxonomy
- **EXACT:** Source matches exactly between Excel and Python (same row, same base amount)
- **APPROXIMATE:** Source matches with minor basis differences (inflation timing, rounding)
- **EXPLICIT_SCHEDULE:** Item uses explicit schedule basis rather than fixed annual
- **ACTIVE_FLAG:** Item active only in specific years (B.11.1)
- **CONTINGENCY_PCT:** Contingency item computed as percentage of other groups
- **ZERO_LINE:** Item is 0 kEUR in both Excel and Python
- **STRUCTURAL_ACCEPT:** Code-level differences accepted as structural (B.01.6 vs B.01.9)
- **PERIOD_SPLIT_PENDING:** Annual → semiannual split pending audit in Stage 2
- **UNMAPPED:** Item exists in Excel but has no Python counterpart

## Acceptance Criteria (Stage 2 — Semiannual Projection Audit)

Before advancing to Stage 2, the following must hold:

1. **Source map CSV exists** with all 13 B-groups (B.01-B.13) and all sub-items
2. **Zero unmapped non-zero items** — all items with base > 0 must have confidence ≠ UNMAPPED
3. **B.02.1** correctly classified as `EXPLICIT_SCHEDULE`
4. **B.11.1** correctly classified as `ACTIVE_FLAG` (Y1-Y14)
5. **B.13** correctly classified as `CONTINGENCY_PCT`
6. **Sum of non-contingency base amounts** approximately matches known Excel base total
7. **Horizon total including contingencies** is 84,674.78 kEUR (confirmed by offline engine)
8. **No production runtime changes** — engine remains offline-only
9. **All existing tests pass** — no regression in revenue, tax, waterfall, SHL

## R99/R102 BLOCKED

R99 (`r99_fcf_for_distribution_keur`) and R102 (`r102_fcf_for_shl_keur`) are audit-only fields. Not runtime drivers. Presented for visibility only. The Phase 6 R99/R102 blocks remain in effect.

## Hard Constraints (This Branch)

- No changes to `domain/opex/engine.py`
- No changes to `domain/opex/line_items.py`
- No changes to `domain/opex/runtime_adapter.py`
- No changes to `app/waterfall_core.py`
- No changes to `app/waterfall_runner.py`
- No changes to `app/project_factories.py`
- No flag changes
- No factory opt-in
- No R99/R102 changes
- No SHL FCF runtime source
- No tax/debt/revenue changes
- Oborovo is out of scope
- Default behavior must remain unchanged

## Recommended Next Branch

`phase7-opex-semiannual-projection-audit` — Stage 2 semiannual projection audit. Validates that the annual OPEX values are correctly split into H1/H2 semiannual periods for the runtime cash flow. Checks period-level OPEX values against the Excel OpEx sheet period split.