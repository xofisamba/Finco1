# Phase 8: Senior Debt Sizing — Canonical Wiring

## Status

**R99/R102: BLOCKED** — ovaj dokument opisuje wiring bez efekta na distribution gateove.

## Cilj

Wire-ati `SeniorDebtSizingEngine` u runtime waterfall iza `use_senior_debt_sizing_engine: bool = False` flega.

## Arhitektura

### Ključno načelo: actual_cfads ≠ sizing_cfads

```
sizing_cfads (Macro!R50)           actual_cfads (CF!R69)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   ━━━━━━━━━━━━━━━━━━━━━━━
eksplicitni sizing input             izračunati CFADS
za debt capacity computation         iz waterfall modela
```

- **sizing_cfads** — hardcoded-style Excel baza za debt capacity (Macro!R50)
- **actual_cfads** — stvarni CFADS iz full modela (CF!R69)

`SeniorDebtSizingEngine` koristi `sizing_cfads` (NIJE `actual_cfads`) za debt capacity komputaciju.

### DSCR target governance

DSCR target je **konfigurabilan input**, nije hardkodirana vrijednost:

- **TUHO**: DS!R19 dual-DSCR — PPA 1.20 / Merchant 1.41
- **Oborovo**: `FinancingParams.dscr_schedule`

## Flag semantika

| Flag | Ponašanje |
|------|-----------|
| `use_senior_debt_sizing_engine=False` (default) | Legacy waterfall nepromijenjen |
| `use_senior_debt_sizing_engine=True` | Canonical engine komputira sizing result i attach-a kao `_canonical_senior_debt_sizing` audit attribute |

## Nova datoteka

### `domain/senior_debt_sizing/canonical_wiring.py`

Adapter koji spaja `SeniorDebtSizingEngine` u runtime waterfall.

**Funkcije:**

- `compute_canonical_senior_debt_sizing()` — canonical entry point
- `derive_sizing_cfads_from_ebitda()` — proxy za legacy `cfads_for_sculpt` derivation
- `build_canonical_senior_debt_sizing_from_inputs()` — glavni wiring helper

**`CanonicalSeniorDebtSizingResult` attributes:**

| Attribute | Opis |
|-----------|------|
| `sizing_cfads_keur_by_period` | Eksplicitni sizing CFADS per semiannual period |
| `target_dscr_by_period` | Per-period DSCR targets |
| `debt_service_capacity_keur_by_period` | sizing_cfads / target_dscr per period |
| `total_debt_service_capacity_keur` | Zbroj svih per-period kapaciteta |
| `annuity_keur` | Implikantna fiksna anuiteta (total / period_count) — za referencu, NE runtime override |
| `source` | `"canonical_senior_debt_sizing_engine"` |

## Runtime wiring

### `domain/inputs.py`

```python
use_senior_debt_sizing_engine: bool = False  # ProjectInfo
```

### `app/waterfall_runner.py`

```python
use_senior_debt_sizing_engine: bool = False  # WaterfallRunConfig
```

Dodano u `cache_key()`, `from_inputs()`, i `run()` metode.

### `app/waterfall_core.py`

```python
if use_senior_debt_sizing_engine:
    from domain.senior_debt_sizing.canonical_wiring import (
        build_canonical_senior_debt_sizing_from_inputs,
    )
    sizing_result = build_canonical_senior_debt_sizing_from_inputs(
        project_name=...,
        project_code=...,
        ebitda_schedule=tuple(ebitda_schedule),
        tax_rate=inputs.tax.corporate_rate,
        dscr_schedule=tuple(dscr_schedule[:len(ebitda_schedule)]),
        use_explicit_sizing_cfads=False,  # Dok Macro!R50 nije wire-an
    )
    result._canonical_senior_debt_sizing = sizing_result
```

## Što NIJE uključeno u ovu fazu

- ❌ Runtime debt override (`fixed_debt_keur` wiring) — future phase
- ❌ R99/R102 promotion — BLOCKED
- ❌ Macro!R50 eksplicitne vrijednosti — koristi se proxy derivation (ebitda × (1 − tax))

## Validation

```bash
cd finco1_pr
python scripts/phase8_senior_debt_sizing_validation_runner.py
```

Očekivani rezultat: **0 FAILURES** — flag nema utjecaja na existing runtime (validation-only wiring).

## Testovi

`tests/test_phase8_senior_debt_sizing_runtime_wiring.py`

- TUHO flag combinations: (False, True) × SHL × Depreciation
- Oborovo flag combinations: (False, True) × SHL
- R99/R102 not promoted check
- Canonical result attached check