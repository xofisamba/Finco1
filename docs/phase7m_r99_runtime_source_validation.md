# Phase 7M R99 Runtime Source Validation

## Purpose

Phase 7L proved that the SHL `fcf_waterfall` mechanics work when fed an Excel-backed R99/R102 cash schedule. Phase 7M checks whether any current Python runtime field can safely replace that fixture-backed R99/R102 source.

This branch is diagnostic only. It does not enable SHL FCF waterfall globally, does not change project factories, and does not rewrite R99/R102 runtime logic.

## Source Of Truth

The Excel R99/R102 source is the TUHO fixture row:

`CF.free_cash_flow_for_distribution_keur`

from:

`tests/fixtures/excel_tuho_full_model_extract.json`

Fixture horizon: 60 Excel operating periods  
Excel R99/R102 total: 234,745.4 kEUR

## Candidate Sources Tested

The bridge compares Excel R99/R102 against these current Python runtime candidates:

- C1d `r99_fcf_for_distribution_keur`
- C1d `r102_fcf_for_shl_keur`
- C1d `fcf_for_shl_keur`
- C1d `r98_distribution_account_keur`
- C1d `r84_fcf_junior_keur`
- `cf_after_tax_keur`
- `cf_after_tax_keur - senior_ds_keur`
- `cf_after_reserves_keur`

The bridge was run on the default TUHO runtime and on the Phase 7K explicit senior DS fixture harness. The explicit senior DS harness is useful because it isolates the remaining R99/R102 question from known senior debt service timing differences.

## Candidate Ranking

Default TUHO runtime:

| Candidate | Python total | Delta vs Excel | MAE | Max abs period delta | Accepted? |
| --- | ---: | ---: | ---: | ---: | --- |
| C1d R99/R102 audit, R98, R84, `cf_after_tax - senior_ds` | 252,412.6 | +17,667.2 | 426.4 | 1,588.9 | No |
| `cf_after_reserves` | 212,977.7 | -21,767.8 | 950.1 | 2,740.6 | No |
| `cf_after_tax`, R69 | 318,239.0 | +83,493.5 | 1,421.1 | 2,933.2 | No |
| Distribution | 173,516.2 | -61,229.3 | 1,603.5 | 6,585.9 | No |

Explicit senior DS harness:

| Candidate | Python total | Delta vs Excel | MAE | Max abs period delta | Accepted? |
| --- | ---: | ---: | ---: | ---: | --- |
| C1d R99/R102 audit, R98, R84, `cf_after_tax - senior_ds` | 252,140.1 | +17,394.7 | 360.1 | 1,588.9 | No |
| `cf_after_reserves` | 212,930.8 | -21,814.6 | 940.1 | 2,382.1 | No |

Best candidate: explicit senior DS harness with the C1d R99/R102 audit family.

Even the best candidate fails the acceptance gate. Total delta is about +17.4m kEUR, or +7.4% of the Excel R99/R102 total. Only 41 of 60 material periods are within the loose diagnostic period tolerance of max(100 kEUR, 2% of Excel R99/R102).

## Selected Period Bridge

Default runtime:

| op_idx | Date | Excel R99/R102 | C1d R99 audit | `cf_after_tax - senior_ds` | `cf_after_reserves` | Delta vs best |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 2030-06-30 | 953.8 | 1,081.1 | 1,081.1 | 1,081.1 | +127.3 |
| 1 | 2030-12-31 | 969.6 | 1,099.0 | 1,099.0 | 0.0 | +129.4 |
| 2 | 2031-06-30 | 967.0 | 1,093.5 | 1,093.5 | 0.0 | +126.5 |
| 3 | 2031-12-31 | 983.0 | 1,111.6 | 1,111.6 | 0.0 | +128.6 |
| 28 | 2044-06-30 | 6,191.8 | 6,187.8 | 6,187.8 | 4,688.3 | -4.0 |
| 32 | 2046-06-30 | 6,422.3 | 6,419.5 | 6,419.5 | 5,639.8 | -2.8 |
| 35 | 2047-12-31 | 5,050.2 | 5,690.8 | 5,690.8 | 5,571.6 | +640.6 |
| 36 | 2048-06-30 | 6,765.1 | 6,735.9 | 6,735.9 | 6,735.9 | -29.2 |
| 37 | 2048-12-31 | 5,028.2 | 5,797.4 | 5,797.4 | 5,797.4 | +769.2 |
| 57 | 2058-12-31 | 5,373.4 | 6,960.7 | 6,960.7 | 6,960.7 | +1,587.2 |
| 58 | 2059-06-30 | 8,264.4 | 8,114.1 | 8,114.1 | 8,114.1 | -150.3 |
| 59 | 2059-12-31 | 5,401.6 | 6,977.7 | 6,977.7 | 6,977.7 | +1,576.1 |

With the explicit senior DS harness, op_idx 0 improves to near parity because senior debt service is fixture-aligned:

| op_idx | Date | Excel R99/R102 | Explicit senior C1d R99 | Senior DS | Delta |
| ---: | --- | ---: | ---: | ---: | ---: |
| 0 | 2030-06-30 | 953.8 | 953.8 | 2,116.4 | +0.0 |
| 28 | 2044-06-30 | 6,191.8 | 6,187.8 | 0.0 | -4.0 |
| 35 | 2047-12-31 | 5,050.2 | 5,690.8 | 0.0 | +640.6 |
| 59 | 2059-12-31 | 5,401.6 | 6,977.7 | 0.0 | +1,576.1 |

## Rejected Candidates

`cf_after_tax - senior_ds` remains rejected.

It is numerically identical to the C1d R99/R102 audit family in the current TUHO setup because DSRA, junior debt, reserve sweep, and carry-forward are effectively zero in the current Python reconstruction. That means it inherits the same total gap:

- Default runtime delta: +17,667.2 kEUR
- Explicit senior DS harness delta: +17,394.7 kEUR

`cf_after_reserves` is also rejected. It is especially wrong around op_idx 24-27 because it is a post-SHL/post-reserve runtime cash concept, not the pre-SHL Excel R99/R102 source.

`cf_after_tax` and R69 are rejected because they omit senior debt service.

Distribution is rejected because it is downstream of SHL behavior and cannot be used as an upstream SHL input.

## Likely Source Of Remaining Difference

The remaining mismatch is not primarily senior debt after applying the explicit senior DS fixture. The senior fixture improves early periods, including op_idx 0, but the full-horizon R99/R102 gap remains about +17.4m kEUR.

The visible pattern is:

- H1 post-senior periods are close or slightly low.
- H2 post-senior periods are materially high, especially after 2050.
- Large H2 deltas are around +1.5m to +1.6m kEUR.
- The gap follows a timing/source pattern consistent with tax and distribution-account/carry-forward mechanics, not with SHL mechanics.
- `cf_after_reserves` shows that post-SHL runtime cash is not a valid upstream R99/R102 source.

Likely missing components:

1. Excel R99/R100/R102 distribution-account timing that is not represented by current Python audit fields.
2. Cash-tax timing/source differences after senior debt is repaid.
3. Possible period timing or carry-forward treatment in H2 periods.

The current Python fields expose the gap but do not eliminate it.

## Acceptance Result

No candidate is accepted.

Acceptance rule used for this validation:

- Total delta within 1% of Excel R99/R102 total.
- Material periods within max(100 kEUR, 2% of Excel period value).

Best candidate fails:

- Total delta: +17,394.7 kEUR
- Total percentage delta: +7.4%
- Material periods within tolerance: 41 / 60
- Maximum single-period delta: 1,588.9 kEUR

## Runtime Safety

No runtime source is wired into SHL FCF waterfall in this branch.

`use_shl_fcf_waterfall_engine` remains default `False`. Project factories remain flag-off. Missing R99/R102 source continues to fail closed, with no fallback to `cf_after_tax - senior_ds`.

## Recommendation

Do not enable SHL `fcf_waterfall` from runtime cash sources yet.

Recommended next branch:

`phase7m-r99-distribution-account-source-bridge`

Suggested scope:

- Extract Excel R98/R100/R102 distribution-account formulas and period timing.
- Add diagnostic-only Python fields for any missing carry-forward/tax timing components.
- Keep SHL FCF waterfall fixture-backed only.
- Accept a runtime R99/R102 source only if the source passes the period and total gates.
