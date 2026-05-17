# Phase 6 Tax Bridge Runtime Flag Design

## Purpose

This document designs the runtime-safe path for promoting the financial statements tax bridge into a default-off runtime tax source.

This is design-only. It does not add flags, change runtime formulas, accept R99/R102 as a runtime source, enable SHL FCF waterfall, or change project factories.

## Context

Financial statements Stage 2-4 now provide:

- offline P&L assembly
- audit tax bridge exposure
- Balance Sheet assembly
- PF Cash Waterfall assembly
- human-readable Excel audit export

The remaining calibration issue is tax ownership. Current runtime tax and cash-tax behavior is not fully Excel-equivalent. Prior diagnostics showed Excel-style annual H2 cash-tax timing explains most of the R67 gap, while tax-basis differences remain.

R99/R102 should not be accepted as a runtime source until the tax bridge owns accrued CIT and cash CIT timing with tested parity.

## Runtime Flag Design

Recommended flag:

`use_tax_bridge_engine: bool = False`

Recommended location:

- `ProjectInfo`, only in the future implementation branch.
- Default `False` for every project.
- No factory should globally opt in.
- Tests may clone project inputs and toggle the flag explicitly.

Flag behavior:

- `False`: legacy runtime tax behavior remains bit-identical.
- `True`: runtime tax fields used by cashflow should be sourced from the tax bridge engine for supported projects only.
- Unsupported project or missing required tax config raises a clear `ValueError`.
- Any material bridge validation failure should fail closed rather than silently falling back to legacy tax.

The flag should control only tax source selection. It must not control revenue, OPEX, senior debt, SHL, construction, R99/R102 source acceptance, or distributions except through the deliberate downstream tax cashflow effect.

## Source-of-Truth Migration

When `use_tax_bridge_engine=True`, the future runtime path should migrate these fields to tax bridge ownership:

- accrued CIT
- cash CIT timing
- loss carry-forward opening and closing balances
- loss used in each period
- fiscal reintegration
- tax depreciation where the tax bridge has a validated tax-basis schedule
- taxable income before losses
- taxable profit after losses

The following remain unchanged:

- revenue
- OPEX
- senior debt schedule and interest logic
- SHL balance and repayment logic
- construction diagnostics/capitalization
- sponsor waterfall
- R99/R102 source acceptance
- distributions, except downstream effects from changed cash tax

R99/R102 must remain diagnostic-only until the tax bridge and PF cash waterfall bridge prove that the new cash tax source reconciles R69/R84/R99/R102.

## Runtime Tax Bridge Algorithm

The implementation should calculate tax period-by-period from audited inputs:

1. Book depreciation
   - Use P&L/statements depreciation for accounting presentation only.
   - Keep it separate from tax depreciation.

2. Tax depreciation
   - Use a project-specific tax depreciation schedule or asset tax-basis schedule.
   - Include only validated tax basis components.
   - Do not infer IDC/fees tax basis unless mapped by evidence.

3. Non-deductible depreciation and fiscal reintegration
   - Compute fiscal reintegration as explicit add-backs to taxable income.
   - Include non-deductible depreciation only if supported by the project tax config.

4. Taxable income before losses
   - Start from EBT after senior/SHL interest.
   - Add fiscal reintegration.
   - Apply tax depreciation treatment consistent with the Excel tax basis.

5. Five-year loss carry-forward
   - Track loss vintages with expiry metadata.
   - Use oldest eligible losses first.
   - Do not use expired losses.
   - Expose opening loss pool, used loss, generated loss, expired loss, and closing loss pool.

6. Taxable profit
   - `taxable_profit = max(0, taxable_income_before_losses - loss_used)`

7. CIT accrual
   - `cit_accrual = taxable_profit * tax_rate`
   - Croatia template starts at 18%.

8. Annual H2 cash-tax payment timing
   - H1 cash tax: 0.
   - H2 cash tax: current H2 CIT accrual plus previous H1 CIT accrual, using Excel cashflow sign convention.
   - This timing should be the initial runtime cash-tax mode for TUHO.

9. Tax payable balance
   - Track accrued CIT not yet paid if needed for Balance Sheet audit.
   - Do not use it for runtime cash unless the flag is enabled and tests prove the schedule.

## Circularity Policy

The safe runtime sequence should be explicit:

1. Build operating periods, revenue, and OPEX.
2. Calculate senior debt interest and principal using the selected senior debt configuration.
3. Calculate SHL interest accrual for tax deductibility, but do not run SHL FCF waterfall.
4. Build P&L/EBT inputs needed by the tax bridge.
5. Run tax bridge for accrued CIT and cash CIT.
6. Feed cash CIT into CFADS/R69 diagnostics or runtime cashflow only when the tax bridge flag is on.
7. Keep R99/R102 source acceptance disabled.
8. Keep SHL FCF waterfall disabled unless a later branch explicitly combines validated R99/R102 with the SHL flag.

Circularity risks:

- tax bridge needs EBT
- EBT needs senior and SHL interest
- senior sculpting may use cash tax/CFADS
- R99/R102 needs cash tax
- SHL FCF waterfall needs R99/R102

Recommended mitigation:

- Do not combine tax bridge runtime, formula-based senior sculpting, R99 acceptance, and SHL FCF waterfall in one branch.
- For the first implementation, use already-stabilized senior debt behavior as input and test only tax source replacement.
- If debt sculpting needs tax-inclusive CFADS later, solve it in a separate staged branch with explicit iteration or fixture-backed schedules.

## TUHO Acceptance Gates

Minimum acceptance tests for `phase6-tax-bridge-runtime-flag`:

- flag defaults to `False`
- flag-off TUHO outputs are bit-identical to legacy
- unsupported projects fail closed when flag-on without config
- accrued CIT total matches Excel within agreed tolerance
- cash CIT/R67 total matches Excel within agreed tolerance
- per-period cash tax matches material Excel periods within tolerance
- H1 cash tax is zero under annual H2 timing
- H2 cash tax equals current plus previous half-year CIT accrual
- loss carry-forward opening, used, and closing balances are exposed
- R69/R84/R99/R102 impact is measured but not accepted as runtime source
- distributions change only through deliberate tax cashflow impact
- no revenue/OPEX/senior/SHL/construction drift except tax-driven downstream values

Suggested tolerances:

- accrued CIT total: within 0.5% or tighter if Excel basis is fully mapped
- R67 cash tax total: within 0.5% after tax basis mapping
- material per-period R67: within 2% until tax basis is fully proven
- no tolerance for flag-off drift

## Oborovo Strategy

Recommended initial policy:

- Block Oborovo runtime opt-in until Oborovo tax basis fixtures and Excel references are available.
- Keep Oborovo diagnostic-only in the first implementation branch.
- Add Oborovo support only after a separate parity fixture proves accrued CIT, cash CIT timing, depreciation, and loss carry-forward behavior.

This avoids applying TUHO-specific tax assumptions to another project silently.

## Excel Audit Export Interaction

The Excel audit export should eventually show tax modes side by side:

- legacy runtime tax
- flag-off tax bridge diagnostics
- flag-on tax bridge runtime values
- Excel reference values where fixtures exist
- deltas by period and total

Recommended additions after runtime implementation:

- Summary: tax mode and flag state
- P&L: accrued CIT source label
- PF Cash Waterfall: cash tax source label
- Source Mapping: runtime source vs diagnostic source status
- Known Gaps: remaining tax basis unmapped rows

The export should not itself decide runtime tax source. It should only report the selected runtime state and diagnostics.

## Implementation Plan

Stage A: flag and config only

- Add `use_tax_bridge_engine=False`.
- Add tax bridge runtime config data structures.
- Add unsupported project guard.
- Prove no default behavior change.

Stage B: TUHO tax bridge runtime behind flag

- Implement TUHO tax basis inputs and annual H2 cash-tax timing.
- Source accrued CIT and cash CIT from the bridge only when flag-on.
- Preserve all other model logic.

Stage C: fixture-backed TUHO tests

- Add Excel fixture totals and selected periods.
- Assert accrued CIT, R67 cash tax, loss carry-forward, and downstream cashflow deltas.
- Keep R99/R102 source acceptance disabled.

Stage D: Oborovo diagnostic

- Add Oborovo tax bridge diagnostics if fixtures are available.
- Keep runtime opt-in blocked unless parity is proven.

Stage E: later R99 source work

- Only after tax bridge and PF cash waterfall reconcile R69/R84/R99/R102 should a separate branch consider R99/R102 runtime source flagging.

## Hard Rejection List For Implementation

A future implementation branch must not include:

- R99/R102 source acceptance
- SHL FCF opt-in
- global project factory opt-in
- senior debt formula changes
- OPEX changes
- revenue changes
- construction changes
- sponsor waterfall changes
- UI/cache/persistence changes
- multi-project tax assumptions without fixtures

## Risks

- Tax-basis mapping can be overfit to TUHO if not represented as explicit project config.
- Tax cash timing affects CFADS, so senior sculpting and R99 bridges can move downstream.
- Loss carry-forward expiry rules need clear vintage tracking.
- SHL interest deductibility may depend on Excel-specific accounting/tax treatment.
- Oborovo may use different assumptions and should not inherit TUHO defaults.
- Accepting R99/R102 before tax parity would bury the remaining R67 mismatch inside SHL/distribution outputs.

## Key Design Decisions

- Keep legacy runtime tax as default.
- Add `use_tax_bridge_engine` only in the implementation branch, not here.
- Make TUHO the first supported runtime opt-in candidate.
- Block Oborovo until fixture-backed tax parity exists.
- Keep R99/R102 audit-only until tax and PF cash waterfall reconciliation are proven.
- Use annual H2 cash-tax timing as the first runtime cash-tax mode because diagnostics already show it explains most of R67.

## Recommended Next Branch

`phase6-tax-bridge-runtime-flag`
