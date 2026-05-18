# Phase 6 — TUHO Excel-compatible CIT cash timing trigger

## Branch
`phase6-cit-h2-annual-trigger`

## Goal
Address the R67 years 1–12 mismatch between Python (flag ON) and Excel by suppressing cash tax / R67 diagnostic before the Excel-supported start period.

## Evidence

| Observation | Value |
|---|---|
| Excel R67 first non-zero period | operating_index 25 (year 13 H2) |
| Excel R67 years 1–12 | 0.0 (all 24 H1/H2 periods) |
| Python flag ON years 1–12 before fix | -2,312.9 kEUR |
| Python flag ON years 13–30 | -43,512.4 kEUR |
| Python flag ON R67 total | -45,825.2 kEUR |
| Excel R67 target total | -38,240.9 kEUR |
| **Years 1–12 mismatch** | **-2,312.9 kEUR** |
| **Years 13–30 residual** | **-5,271.4 kEUR** |

**Evidence quality: Medium.** No direct Excel formula showing a formal holiday or exemption. Most consistent explanation: Excel applies an early-operating-period CIT suppression. Neutral framing: "Excel-compatible CIT cash timing start-period rule" rather than "tax holiday."

## Implementation

### Parameter
`TaxParams.cit_cash_tax_start_operating_index: int | None = None`

- TUHO default factory: `cit_cash_tax_start_operating_index=25`
- Oborovo: `None` (unchanged)
- Flag OFF: `None` (no suppression)

### Mechanism
In `_apply_tuho_tax_bridge_runtime_cash_tax`, when `cit_cash_tax_start_operating_index` is set and `operating_index < cit_cash_tax_start_operating_index`:
- `corporate_tax_cash_keur = 0` (H2 cash tax suppressed)
- `r67_excel_style_cash_tax_diagnostic_keur = 0` (R67 diagnostic suppressed)
- Tax accrual fields (`tax_keur`, `cit_accrual_audit_keur`, `taxable_profit_keur`) remain populated for audit visibility

## R67 Before/After

### Years 1–12 (operating_index 0–23)
| | kEUR |
|---|---:|
| Before fix | -2,312.9 |
| After fix | 0.0 |

### Years 13–30 (operating_index 24–59)
| | kEUR |
|---|---:|
| Python flag ON (unchanged) | -43,512.4 |
| Excel target | -38,240.9 |
| **Residual** | **-5,271.4** |

### Total
| | kEUR |
|---|---:|
| Before fix | -45,825.2 |
| After fix | -43,512.4 |
| Excel target | -38,240.9 |
| **Total residual** | **-5,271.4** |

Years 1–12 gap fully resolved. Remaining ~5,271 kEUR residual in years 13–30 is a **separate calibration item**.

## What Was NOT Changed
- Flag OFF behavior: bit-identical
- Oborovo: unchanged, flag-on still guarded with ValueError
- R99/R102: remain audit-only; not promoted to runtime source
- SHL FCF: not enabled
- Factory opt-in: `use_tax_bridge_engine=False` by default
- Tax accrual fields: preserved for audit visibility during suppression window

## Recommended Next Branch
`phase6-r67-yrs13to30-residual` — investigate the separate ~5,271 kEUR residual in years 13–30.
