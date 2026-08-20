# Pre-freeze PR-6: Typed SHL Repayment Policy Authority

## Decision

The clean production authority for operating Shareholder Loan (SHL) principal
repayment is:

`FinancingParams.clean_shl_repayment_method`
-> `financial_engine.adapters.project_inputs`
-> `ShareholderLoanModelInput.repayment_mode`
-> `compute_shareholder_loan_schedules`
-> the G2C shareholder waterfall.

The ProjectInputs field is typed as `SHLRepaymentMethod`. The adapter maps only
typed, explicitly supported values to the small clean `ShlRepaymentMode` enum.
Unknown values and unsupported combinations fail closed. Project identity is
not a repayment-policy input.

The supported clean ProjectInputs policies are:

| Policy | Meaning |
|---|---|
| `BULLET` | No principal before maturity; actual payment remains bounded by cash and unpaid principal remains visible. |
| `CASH_SWEEP` | Cash pays gross interest first; the residual pays principal after the typed eligibility start. |

`PARTIAL_PAY_SWEEP` remains an explicit deserialization compatibility alias for
already-persisted projects and maps to `CASH_SWEEP`; canonical factories no
longer emit it. `EXPLICIT_SCHEDULE` remains a valid lower-level generic engine
capability, but is not promoted to ProjectInputs by this phase.

## Orthogonal Authorities

| Concern | Clean authority | PR-6 disposition |
|---|---|---|
| Construction funding | G2A project-uses funding result | Unchanged. |
| Construction interest | `ShlConstructionInterestMethod` | `SIMPLE` and `COMPOUND_PERIODIC` remain separate from repayment mode. |
| Operating accrual | rate plus typed day-count convention | Unchanged. |
| Cash versus PIK | natural SHL kernel, based on cash actually available | Unchanged. |
| Principal mechanism | typed `SHLRepaymentMethod` -> `ShlRepaymentMode` | Canonicalized. |
| Principal eligibility | `shl_principal_eligibility_start_period` | Separate typed integer policy; no source period is hardcoded in the engine. |
| Maturity | `shl_maturity_period_index` | Separate typed integer policy; invalid grids fail closed. |
| Cash available to SHL | PR-4 G2C chain: Base CFADS -> Senior -> DSRA -> DA -> `max(0, DA release)` | Frozen and consumed unchanged. |

## Authority Inventory

| Location | Current semantics and consumer | Status |
|---|---|---|
| `domain.inputs.SHLRepaymentMethod` / `finco_core.inputs.SHLRepaymentMethod` | Broad historical enum shared by persisted ProjectInputs. | Typed boundary retained; clean adapter accepts only the canonical subset and the one persisted alias. |
| `FinancingParams.shl_repayment_method` | String consumed by the legacy waterfall and export compatibility surfaces. | Legacy-only, quarantined; never a clean fallback. |
| `FinancingParams.clean_shl_repayment_method` | Explicit clean ProjectInputs repayment authority. | Canonical typed input. |
| `ShareholderLoanModelInput.repayment_mode` | Engine-facing immutable policy. | Canonical clean runtime contract. |
| `ShlRepaymentMode` | `BULLET`, `CASH_SWEEP`, `EXPLICIT_SCHEDULE`. | Small clean enum retained. |
| `compute_shl_waterfall_period` | Natural interest-first cash waterfall. | Arithmetic authority; unchanged. |
| `compute_shareholder_loan_schedules` | Applies eligibility and maturity over the period grid. | Production schedule authority; unchanged. |
| G2C shareholder waterfall | Supplies post-Senior/DSRA/DA cash and reports actual payment/unpaid balance. | Final clean cash authority; unchanged. |
| `finco_core.waterfall.shl_engine`, `finco_core.shl`, FCF paths | Historical string modes and source-alignment behavior. | Legacy-only; not required by clean runtime. |
| `WaterfallRunConfig.shl_repayment_method` | Typed wrapper that ultimately feeds the legacy waterfall. | Legacy runtime contract, not clean authority. |

## Legacy Flag Inventory

| Field / name | Classification | Reason |
|---|---|---|
| `use_shl_fcf_waterfall_engine` | Legacy-only / quarantined | Selects a historical FCF path; PR-4 DA release remains clean cash authority. |
| `use_tuho_shl_repayment_alignment` | Legacy-only / quarantined | Project-specific alignment used by the old waterfall. |
| `tuho_shl_principal_eligibility_start_period` | Legacy-only / quarantined | Replaced in clean code by generic `shl_principal_eligibility_start_period`. |
| `pik_then_sweep` | Historical description alias | Source behavior is the natural `CASH_SWEEP` kernel; not a distinct clean mode. |
| `partial_pay_sweep` | Persisted compatibility alias | Partial cash interest and PIK are outcomes of available cash, not a principal mode. |
| `fcf_waterfall` | Legacy path name | Conflates cash source and repayment mechanism; not promoted. |
| `pik` / `accrued` | Legacy interest-settlement descriptions | Not accepted as clean principal-repayment modes. |
| `shl_fcf_waterfall_cash_schedule_keur` | Legacy source-vector input | Forbidden as clean production authority; source vectors remain validation-only. |

No category-B legacy flag above is required by the clean production path. Broad
legacy deletion is intentionally deferred; this phase does not expand into the
later legacy-retirement work.

## Source-first Workbook Evidence

The extractor `finco_recon/derive_prefreeze_pr6_shl_repayment_truth.py` verifies
the authoritative workbook SHA-256 values before reading formulas and emits the
validation-only lock at
`tests/fixtures/prefreeze_pr6_shl_repayment_source_lock.json`. Production code
does not load this fixture.

| Project | Source cells / formulas | Typed classification | Eligibility / maturity | Construction classification |
|---|---|---|---|---|
| TUHO | Aggregate SHL: DS rows 120/122/124/125/126; cash: CF row 102 (`CF!H102=H99`); principal examples `DS!AF124=AF137+AF148+AF159`. | `CASH_SWEEP` | DS25 / DS36 | `SOURCE_IDC_HANDOFF_UNPROMOTED`; no construction-policy promotion in PR-6. |
| Oborovo | Aggregate SHL: DS rows 123/125/127/128/129; cash: CF row 112 (`CF!H112=H109`); principal examples `DS!AF127=AF140+AF151+AF162`. | `CASH_SWEEP` | DS25 / DS40 | `SIMPLE_DCF_1_SOURCE_PROVEN`. |
| KUPI | Aggregate SHL: DS rows 120/122/124/125/126; cash: CF row 102 (`CF!H102=H99`); principal examples `DS!H124=H137+H148+H159`. | `CASH_SWEEP` | DS1 / DS20 | `COMPOUND_PERIODIC_SOURCE_PROVEN`. |

For all three sources, cash services interest before principal, interest
shortfall capitalizes as PIK, and surplus after interest sweeps principal only
when eligible. The operating rule is therefore one generic `CASH_SWEEP`, even
though historical Python labels differed. Construction compounding remains a
separate policy.

The source-cash oracle compares opening, gross interest, cash interest, PIK,
principal, and closing balance period by period. Source vectors are evidence
only and never production inputs.

Measured maximum absolute source-oracle deltas are:

| Project | Maximum absolute delta | First divergence above `1e-9` |
|---|---:|---|
| TUHO | `9.094947017729282e-13` kEUR | None |
| Oborovo | `2.2737367544323206e-13` kEUR | None |
| KUPI | `7.275957614183426e-12` kEUR | None |

## Behavioral Contract

For `CASH_SWEEP`:

```text
gross_interest = opening * rate * DCF
cash_interest = min(cash_available, gross_interest)
PIK = gross_interest - cash_interest
remaining_cash = cash_available - cash_interest
principal = min(remaining_cash, opening + PIK)  # when eligible
closing = opening + draw + PIK - principal
```

Before `repayment_start_period_index`, cash interest may be paid but principal
is zero. At and after eligibility, the sweep is bounded by both remaining cash
and outstanding SHL. There is no forced terminal repayment, top-up, balancing
plug, source-output replay, or target fitting.

For `BULLET`, contractual principal is due only at maturity. The G2C actual cash
payment remains bounded by cash available after interest; insufficient cash is
reported as unpaid principal and a remaining balance rather than manufactured
cash.

## Validation and Open Boundaries

- Unknown serialized enum values fail during deserialization.
- Untyped strings and unsupported typed values fail in the clean adapter.
- Repayment start or maturity outside the period grid fails closed.
- Maturity before repayment start fails closed.
- Negative or over-balance explicit principal fails in the lower-level engine.
- Unsupported operating draws and missing explicit schedules remain covered by
  the existing SHL engine tests.
- Renaming a project cannot alter typed SHL outputs.
- A real Generic Solar production mutation proves `BULLET` versus `CASH_SWEEP`
  changes principal timing while rate, Senior, DSRA, DA, and zero-tax upstream
  cash are identical.

The full deductible-SHL tax/covenant fixed point remains explicitly open as
`G2C_DEDUCTIBLE_SHL_COVENANT_FEEDBACK_NOT_YET_CLOSED`. TUHO clean construction
authority is also not promoted in this phase. PR-6 does not start Bank Case
methodology work, DSRA changes, distribution changes, or PR-7.

## Before/After Calibration Lock

A detached worktree at exact post-PR-5 main
`e8f051ca5b25a0001917e87b47c9f90aa30770e1` was compared with the PR-6 working
tree using identical inputs and source IDs. The complete serialized result
hash, not only selected KPIs, is identical for each case:

| Case / path | Base result SHA-256 | PR-6 result SHA-256 | Delta |
|---|---|---|---:|
| TUHO legacy production | `5f956ed927df29466574530b122eecee8cdb17f1f3dd3ef1605705feda828a62` | same | 0 |
| Oborovo clean Senior/SHL production | `44f99e5a47bddedd77bd8e3d2e419505f3847e76d498116c4e63706d181bb628` | same | 0 |
| KUPI clean G2C production | `6caa93854d569fa44c7d57b206121f18854113e6729c377ffcf8889f9754b29f` | same | 0 |

The exact selected values also remained unchanged:

| Metric | TUHO | Oborovo | KUPI |
|---|---:|---:|---:|
| Construction SHL principal (kEUR) | Legacy contract unchanged | `14620.773894815633` | `79579.65938620616` |
| Construction PIK (kEUR) | Legacy contract unchanged | `1169.6619115852507` | `13242.055321864716` |
| First operating opening SHL (kEUR) | Legacy contract unchanged | `15790.435806400883` | `92821.71470807088` |
| Gross operating interest (kEUR) | Legacy contract unchanged | `30934.403664410678` | `62988.64053223288` |
| Cash operating interest (kEUR) | Legacy contract unchanged | `20011.356550426342` | `62988.64053223288` |
| Operating PIK (kEUR) | Legacy contract unchanged | `10923.047113984334` | `0.0` |
| Principal repaid (kEUR) | Legacy contract unchanged | `26713.482920385213` | `92821.71470807091` |
| Final closing SHL (kEUR) | Legacy contract unchanged | `0.0` | `0.0` |
| Senior authority / service measure (kEUR) | `65826.38828020643` | `42852.30326225287` | `135723.77859068173` |
| Base CFADS / cash measure (kEUR) | `305476.7854442677` | `171466.06772202402` | `929027.8813073058` |
| Bank CFADS (kEUR) | Legacy contract unchanged | `141761.64252202827` | Full-result hash unchanged |
| DSCR | `1.3785647255425093` | `1.2425786293568173` | Full-result hash unchanged |
| Sponsor return | `0.11320018084982914` | Full-result hash unchanged | `0.1532556141898339` |

Because all complete-result hashes match, Senior, tax/CFADS, DSCR, SHL
receipts, and Sponsor-return deltas are exactly zero. The typed migration is an
authority correction, not recalibration.

## Classification

`TYPED_SHL_REPAYMENT_POLICY_AUTHORITY_ESTABLISHED`
