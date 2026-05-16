# Phase 7I Construction Runtime Flag

This branch adds a default-off runtime flag for construction schedule
diagnostics:

```text
ProjectInfo.use_construction_schedule_engine = False
```

The flag is intentionally diagnostic-only in this PR.

## Behavior

When the flag is `False`, existing runtime behavior is unchanged.

When the flag is `True`, the runtime builds a construction schedule diagnostic
from `domain.construction.runtime_adapter` and attaches it to the waterfall
result as:

```text
result.construction_schedule_diagnostic
```

No construction value is routed into senior debt sizing, SHL opening balance,
CAPEX, revenue, OPEX, tax, R99, distributions, or operating SHL mechanics.

## Supported Projects

Supported project codes:

- `TUHO-WIND-1`
- `Oborovo` / `OBR-001`

Unsupported project codes raise a clear `ValueError` when the flag is enabled.

## Double-Counting Rules

The adapter enforces the current safety stance through diagnostic notes:

- existing manual project inputs remain authoritative for runtime balances,
- computed SHL IDC is not added on top of manual `shl_idc_keur`,
- computed senior IDC is not added on top of manual senior debt or CAPEX inputs,
- computed opening SHL and senior balances are audit outputs only.

This is especially important for Oborovo, where the legacy runtime has
`shl_idc_keur=0` while the offline construction engine computes SHL IDC of
approximately 1,169.662 kEUR. That mismatch is reported diagnostically and is
not silently routed into cash flows.

## Manual Override Precedence

Manual/project factory inputs keep precedence in runtime calculations. The
construction diagnostic reports manual-vs-computed mismatches, but does not
replace those values.

## Known Limitations

Senior IDC parity currently uses template-level effective senior construction
rates because the Excel base-rate rows and exact construction day-count details
are not yet fully modeled. This limitation remains isolated to diagnostics.

## Future Runtime Work

A later implementation may deliberately replace selected opening construction
balances, but only after explicit tests define:

- which manual fields are replaced,
- which manual IDC inputs are disabled,
- how senior IDC is treated,
- how Oborovo's SHL IDC mismatch is resolved,
- and how double-counting is prevented.
