# Phase 7F - TUHO Manual Excel Mapping

**Date:** 2026-05-14
**Branch:** `phase7f-tuho-distribution-calibration`
**Status:** PR B2 working note

This note records the current authoritative Excel row mapping for TUHO SHL
calibration. Older notes that treated R102 as the SHL outflow are superseded.

## Authoritative Row Mapping

| Excel row | Meaning | Total (kEUR) | Calibration use |
| --- | --- | ---: | --- |
| R99 | Pre-SHL cash pool / FCF for SHL input | approx 234,745 | Cash available before SHL service |
| R102 | FCF for SHL waterfall input / cash available | approx 234,745 | Same cash pool as R99; not SHL outflow |
| R104 | Net SHL cash outflow | approx -82,486 | SHL service after waterfall |
| R106 | FCF for dividends / gross dividends | approx 152,259 | Cash after SHL before final dividend adjustment |
| R119 | Net Dividends | approx 151,709 | Official calibration target |

## SHL Mechanics

Excel uses a continuous cash-interest-first SHL waterfall:

```text
gross_interest = opening_shl_balance * shl_rate_per_period
cash_interest = min(fcf_for_shl, gross_interest)
pik_interest = max(0, gross_interest - cash_interest)
remaining_cash = fcf_for_shl - cash_interest
principal = min(remaining_cash, opening_shl_balance + pik_interest)
closing_balance = opening_shl_balance + pik_interest - principal
residual_cash = remaining_cash - principal
```

The principal cap includes current-period PIK:

```text
principal <= opening_shl_balance + current_period_pik
```

## PR B2 Input Decision

For PR B2, the accepted Python proxy for Excel R99/R102 is:

```text
fcf_for_shl = cf_after_tax_keur - senior_ds_keur
```

This proxy is known to differ from Excel R99/R102 by roughly +6%, but a new
R99 engine is deferred. PR B2 must not introduce tax, revenue, OPEX, or R99
engine changes.

## PIK Total

The previous documentation value of 14,596 kEUR for total PIK is unverified and
must not be used as a hard acceptance target. Claude flagged that Excel DS R125
PIK may be closer to approx 11,027 kEUR. Until directly verified from Excel, the
PIK total remains an audit note only.

## Calibration Targets

| Metric | Excel target / band |
| --- | ---: |
| Net Dividends, R119 | approx 151,709 kEUR |
| Net SHL outflow, R104 | approx 82,486 kEUR |
| SHL peak balance | approx 43,731 kEUR |
| First distribution | around Excel period 36 |

## Guardrails

- Do not replace the official R119 target with Python interim output.
- Do not use R102 as SHL outflow; R104 is the SHL outflow row.
- Do not use the unverified PIK total as an acceptance target.
- Do not implement R99, tax, revenue, OPEX, or construction IDC changes in PR B2.
