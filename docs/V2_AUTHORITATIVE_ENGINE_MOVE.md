# V2-4: Authoritative Engine Move

## What V2-4 Did

V2-4 reversed the shim direction for all major domain subpackages. Previously,
`finco_core.*` packages re-exported from `domain.*` (forward shims). After V2-4,
`finco_core.*` packages are the authoritative location; `domain.*` modules are
backward-compatibility shims that re-export from `finco_core.*`.

## Scope

| Metric | Value |
|--------|-------|
| Files copied to `finco_core/` | 76 |
| `domain/` shims created | 77 |
| Packages made authoritative | 8 |

Packages affected: `waterfall`, `tax`, `debt`, `depreciation`, `shl`, `sponsor`,
`engine`, `validation`.

## Import Chain

All `finco_core.*` `__init__.py` files now import from `finco_core.<pkg>.<submodule>`
directly. The individual submodule `.py` files still contain internal imports like
`from domain.X import Y`; those resolve cleanly because `domain.X` is a shim that
re-imports from `finco_core.X`, without creating circular imports (the shim
does not import from the subpackage `__init__`, only from the leaf submodule).

```
finco_core.tax              # imports from finco_core.tax.engine, etc.
  └─ finco_core/tax/engine.py        # may import from domain.tax.engine_inputs
       └─ domain/tax/engine_inputs.py  # shim → finco_core.tax.engine_inputs
            └─ finco_core/tax/engine_inputs.py  # authoritative leaf (no domain imports)
```

## Parity Guarantee

No logic was modified. Files were copied verbatim from `domain/` to `finco_core/`.
All execution paths traverse the same byte-identical code.

## Known Temporary Dependencies

Internal files under `finco_core/` still contain `from domain.X import Y` in their
bodies. These are resolved via the domain shim layer and are flagged for cleanup in
V2-5, which will update all internal `finco_core/` imports to use `finco_core.*`
paths directly.

## Excluded Symbols

- `PeriodFrequency`: already authoritative in `finco_core.inputs` (extracted V2-2).
- `SeniorDebtSizingPolicy`, `SeniorDebtDSCRPolicy`, `SizingMode`, `SeniorDebtSizingEngine`:
  not yet copied to `finco_core/debt/`; remain in `domain/senior_debt_sizing/` until V2-5.
- `BessParams`: still TYPE_CHECKING-only in `finco_core/inputs/_models.py` (V2-5 target).

## Next Step: V2-5

V2-5 will sweep all `finco_core/` leaf files and rewrite internal `from domain.X`
imports to `from finco_core.X`, completing the extraction and eliminating the
domain shim dependency for `finco_core` internal calls.
