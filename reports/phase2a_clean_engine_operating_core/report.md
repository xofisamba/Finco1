# Phase 2A Clean Engine — Operating Core Report

## Scope Statement

Phase 2A does not implement a complete financial engine. It establishes the clean immutable contracts and reconciles only the operating core through EBITDA and book/tax depreciation.

An OPERATING_CORE_V1 PASS is not evidence of tax, CFADS, debt, waterfall, financial-statement or returns parity.

---

## What Phase 2A Delivers

| Scope item | Status |
|---|---|
| `financial_engine/` package | Implemented |
| Immutable input contracts (`OperatingModelInput` hierarchy) | Implemented |
| Input validation (CAL, TECH, REV, OPEX, DEP codes) | Implemented |
| Input fingerprint / provenance | Implemented |
| Generic `ProjectInputs` → `OperatingModelInput` adapter | Implemented |
| Period grid (all semiannual periods via `PeriodEngine`) | Implemented |
| Production schedule (via `finco_core.revenue.generation`) | Implemented |
| Revenue schedule (via `finco_core.revenue.generation`) | Implemented |
| OPEX schedule (via `finco_core.opex.projections`) | Implemented |
| EBITDA = revenue − OPEX | Implemented |
| Book depreciation (via `finco_core.debt.depreciation_schedule`) | Implemented |
| Tax depreciation (equal to book in Phase 2A operating core) | Implemented |
| `FinancialEngineCandidateProvider` (Phase 1C protocol) | Implemented |
| `ComparisonProfile.OPERATING_CORE_V1` projection | Implemented |
| OPERATING_CORE_V1 CLI (`check_financial_engine_operating_core`) | Implemented |
| GitHub Actions CI enforcement | Implemented |

## What Phase 2A Does NOT Deliver

- Tax calculations, ATAD corrections, loss-carryforward
- CFADS, debt service, senior debt sizing
- SHL interest / repayment
- DSRA reserve mechanics
- Waterfall distributions
- Financial statements (P&L, balance sheet, cash flow)
- IRR, MOIC, LLCR, equity returns

---

## Baselines and Parity Results

Engine designation: `clean_operating_core_v0`

| Baseline | OPERATING_CORE_V1 | Differences |
|---|---|---|
| tuho | IDENTICAL | 0 |
| oborovo | IDENTICAL | 0 |
| generic_solar | IDENTICAL | 0 |
| generic_wind | IDENTICAL | 0 |

Parity gate covers:
- `period_grid`: `period_index`, `date`, `year_index`, `period_in_year`, `is_operation`, `is_construction`, `start_date`
- `operating_schedules`: `production_mwh`, `revenue_keur`, `opex_keur`, `ebitda_keur`, `book_depreciation_keur`, `tax_depreciation_keur`

Zero differences across all six schedule fields for all four baselines.

---

## Depreciation Implementation

Book and tax depreciation use `finco_core.debt.depreciation_schedule.build_depreciation_schedule` and `depreciation_per_period` — the same generic straight-line, day-fraction-based formula as the legacy `waterfall_core.py` path:

```
annual_dep = item.amount_keur / useful_life_years
dep_per_period = annual_dep * period.day_fraction
```

Useful lives come from `ASSET_CLASS_USEFUL_LIFE` in `finco_core.inputs`. No project-code dispatch, no fixture reads, no TUHO/Oborovo names inside `financial_engine`.

---

## Production Isolation

The `financial_engine` package:
- Does not import: `app`, `main_web`, `main_api`, `finco_parity`, `persistence`, `fastapi`, `jinja2`, `requests`, `openpyxl`, `pandas`
- Does not contain forbidden identifiers (TUHO, Oborovo, project-specific names, file I/O patterns)
- Does not call: `run_waterfall`, `run_waterfall_v3_core`, `WaterfallRunner`
- Is not accessible through any production route

The following production files are confirmed unchanged:
- `app/waterfall_core.py`
- `app/waterfall_runner.py`
- `finco_core/waterfall/waterfall_engine.py`

---

## Test Coverage

| Test module | Count |
|---|---|
| `test_phase2a_engine_inputs.py` (inputs, adapter, validation, fingerprint) | 37 |
| `test_phase2a_orchestrator.py` (parity, period-grid, negative ULP, immutability) | 46 |
| `test_phase2a_production_isolation.py` (import guards, identifier guards, isolation) | 12 |
| **Total** | **95** |

Negative tests confirm one-ULP changes in any of the six schedule fields produce PAYLOAD_DRIFT.

---

## Architecture Decisions

**Why `build_depreciation_schedule` + `depreciation_per_period` instead of `DepreciationEngine`?**

`build_depreciation_schedule` is the generic identity-blind leaf that the legacy `waterfall_core.py` also calls. Using it produces bitwise-identical values without copying expected outputs or introducing project-code dispatch.

**Why book = tax depreciation?**

In the Phase 2A operating core, the baseline `book_depreciation_keur` and `tax_depreciation_keur` arrays are bitwise identical. Canonical ATAD-adjusted tax depreciation is out of Phase 2A scope; Phase 2B will diverge book from tax when tax calculations are implemented.

**Why `FinancialEngineCandidateProvider` uses Phase 1C orchestration?**

The Phase 1C `_run_candidate_with_context` provides manifest integrity checks, environment verification, live-legacy re-run, and identity/schema validation in the correct order. The Phase 2A CLI is a thin wrapper that supplies the provider and profile, not a reimplementation.
