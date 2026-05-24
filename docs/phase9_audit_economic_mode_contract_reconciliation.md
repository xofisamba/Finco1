# Phase 9 Audit Economic Mode Contract Reconciliation

## Outcome

Conclusion reached: **A — no current runtime contradiction exists**.

There was a historical contradiction: `audit_economic_mode` was once described as
comparison-only while a runtime wiring path used it as if it were routable. The
current codebase no longer does that. The contract is now split explicitly:

- `audit_economic_mode`: audit / reconciliation visibility only, never runtime-authoritative
- `runtime_economic_mode`: explicit pre-G20 runtime staging for DistributionAccount wiring only

This branch does not change financial formulas. It documents the current contract
and adds tests that prove the authority boundary remains intact.

## What `audit_economic_mode` Means

`audit_economic_mode` enables economic gate evaluation for audit and comparison
purposes. It is intended for:

- dual-run validation
- reconciliation traces
- audit visibility

It is not intended for:

- direct runtime distribution routing
- sponsor runtime promotion
- SHL runtime promotion
- G20 approval
- R99 / R102 approval

When `audit_economic_mode=True`, the result may be inspected, compared, exported,
or documented. It must not silently become runtime authority.

## What Is Audit-Only

The following outputs remain audit-only when driven by `audit_economic_mode`:

- DistributionAccount gate pass/fail comparisons
- economic-mode dual-run traces
- audit candidate distribution values
- blocked-reason and warning outputs

These help reviewers understand what would happen under economic gate evaluation,
but they do not replace runtime-authoritative cashflow outputs.

## What Is Runtime-Authoritative

Runtime-authoritative values remain backend runtime results from the governed
waterfall path, unless an explicit staging flag is enabled where documented.

In the current contract:

- default governed runtime remains authoritative
- workbook/export layers remain descriptive, not calculation authority
- persistence remains metadata/snapshot storage, not calculation authority
- dual-run validation remains observational, not routable

## Runtime-Safe Staging

`runtime_economic_mode` exists for one narrow case:

- explicit DistributionAccount runtime staging behind `use_distributionaccount_runtime_wiring=True`

That staging mode is still:

- default-off
- pre-G20
- TUHO-only
- Oborovo-guarded
- not a promotion of R99 or R102

The distinction is important:

- `audit_economic_mode` may evaluate gates, but may not route runtime outputs
- `runtime_economic_mode` may evaluate the same gates for explicitly staged routing

## Current Code Contract

### DistributionAccount gate layer

`domain/distribution_account/gates.py` treats gate activation as:

`audit_economic_mode or runtime_economic_mode`

That means both modes can evaluate gates. The authority distinction is not in the
gate math; it is in the routing contract.

### Runtime wiring layer

`app/waterfall_core.py` uses:

- `runtime_economic_mode=True` in `_apply_distributionaccount_runtime_wiring`
- `audit_economic_mode=True` in dual-run comparison construction

That is the key protection. Runtime wiring no longer uses audit mode.

### Dual-run validation layer

Dual-run validation remains comparison-only. Enabling dual-run adds audit traces
without mutating the authoritative runtime distribution path.

## Governance Interaction

This branch does not relax any governance boundary.

- `G20` remains `BLOCKED`
- `R99` remains `NOT APPROVED`
- `R102` remains `NOT APPROVED`

Accepted conventions and audit traces remain explanatory only. They are not
approval semantics and not runtime promotion semantics.

## Answers to the Branch Questions

### 1. What is `audit_economic_mode` supposed to mean?

Audit-only gate evaluation for reconciliation and comparison.

### 2. Which outputs are audit-only?

Economic-mode DistributionAccount comparison outputs, warnings, gate traces, and
dual-run review surfaces.

### 3. Which outputs, if any, are runtime-authoritative?

Only the normal runtime waterfall outputs, plus the explicitly staged
DistributionAccount path when `use_distributionaccount_runtime_wiring=True`
activates `runtime_economic_mode`.

### 4. Are any audit-only outputs currently being consumed by runtime paths?

No current contradiction was found. The runtime wiring path uses
`runtime_economic_mode`, not `audit_economic_mode`.

### 5. If yes, what should happen?

Not applicable in the current codebase. The historical contradiction was already
resolved by splitting the modes.

### 6. How do G20, R99, and R102 gates interact with `audit_economic_mode`?

`audit_economic_mode` may expose how R99/R102 gates would evaluate under economic
logic, but that does not approve them or promote them into the governed runtime.
G20 remains blocked, and R99/R102 remain not approved.

## Why This Is Not Documentation-Only

This branch adds tests that prove:

- audit-only values do not silently route into runtime-authoritative outputs
- dual-run audit visibility does not mutate runtime results
- runtime-sensitive flags remain explicit and default-off
- default runtime outputs remain unchanged when audit mode is not active

## Scope Guardrails

Confirmed unchanged in this branch:

- no runtime/model formulas changed
- no workbook calculations changed
- no replay engine behavior added
- no persistence authority promotion occurred
- no workbook/export layer became calculation authority

## Follow-Up Risk

The authority boundary is currently explicit but still relies on naming discipline
and routing discipline around DistributionAccount wiring. Any future work that
adds new runtime staging flags should preserve the same split:

- evaluation mode
- routing permission

That remains the clean pattern going forward.
