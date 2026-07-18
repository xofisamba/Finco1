# Phase 2A Clean Engine — Operating Core Report

## Scope Statement

Phase 2A does not implement a complete financial engine. It establishes the clean immutable contracts and reconciles only the operating core through EBITDA and book/tax depreciation.

An OPERATING_CORE_V1 PASS is not evidence of tax, CFADS, debt, waterfall, financial-statement or returns parity.

---

## Revision History

| Field | Value |
|---|---|
| Base SHA (main) | `f23030cf8fc28d2c17f49540af0b1dbfc38f3a7c` |
| Previous reviewed head | `a81f9bd59d6b88aa9d3125aeccd8c1fcaedc1c47` |
| Final corrected head | _populated after final push_ |

---

## What Phase 2A Delivers

| Scope item | Status |
|---|---|
| `financial_engine/` package | Implemented |
| Immutable input contracts (`OperatingModelInput` hierarchy) | Implemented |
| `DepreciationInput`: both fields required, no defaults | Implemented |
| `CapexItemForDep` with real DEP001–DEP004 validation | Implemented |
| Input validation (CAL, TECH, REV, OPEX, DEP codes) | Implemented |
| Input fingerprint / provenance | Implemented |
| Generic `ProjectInputs` → `OperatingModelInput` adapter | Implemented |
| Period grid (all semiannual periods via `PeriodEngine`) | Implemented |
| `OperatingPeriodResult.period_start: date` | Implemented |
| Production schedule (via `finco_core.revenue.generation`) | Implemented |
| Revenue schedule (via `finco_core.revenue.generation`) | Implemented |
| OPEX schedule (via `finco_core.opex.projections`) | Implemented |
| EBITDA = revenue − OPEX | Implemented |
| Book depreciation (via `finco_core.debt.depreciation_schedule`) | Implemented |
| Tax depreciation (equal to book in Phase 2A operating core) | Implemented |
| `FinancialEngineCandidateProvider` (Phase 1C protocol) | Implemented |
| `compare_candidate_provider()` public aggregate API | Implemented |
| `exit_code_for_aggregate()` centralized exit-code mapping | Implemented |
| `ComparisonProfile.OPERATING_CORE_V1` projection | Implemented |
| OPERATING_CORE_V1 CLI (`check_financial_engine_operating_core`) | Implemented |
| CLI: true thin wrapper; no private imports | Implemented |
| CLI: `ValueError` → exit 2 for unknown baselines | Implemented |
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

```
python -m finco_parity.check_financial_engine_operating_core --all --check

Phase 2A OPERATING_CORE_V1 parity check — engine: clean_operating_core_v0
Profile: operating-core-v1
Baselines: tuho, oborovo, generic_solar, generic_wind

  [tuho]          OPERATING_CORE_V1 PASS
  [oborovo]       OPERATING_CORE_V1 PASS
  [generic_solar] OPERATING_CORE_V1 PASS
  [generic_wind]  OPERATING_CORE_V1 PASS

Overall: PASS (4 baseline(s))
```

Selected: 4 | Passed: 4 | Failed: 0 | Differences: 0 for each baseline.

Parity gate covers:
- `period_grid`: `period_index`, `date`, `year_index`, `period_in_year`, `is_operation`, `is_construction`, `start_date`
- `operating_schedules`: `production_mwh`, `revenue_keur`, `opex_keur`, `ebitda_keur`, `book_depreciation_keur`, `tax_depreciation_keur`

Zero differences across all six schedule fields for all four baselines.

---

## Integration Test Results

| Test scenario | Result | Exit |
|---|---|---|
| Identity: wrong `baseline_commit_sha` | IDENTITY_MISMATCH | 7 |
| Identity: wrong `baseline_id` | IDENTITY_MISMATCH | 7 |
| Identity: wrong `input_source_id` | IDENTITY_MISMATCH | 7 |
| Schema: wrong `schema_version` | SCHEMA_MISMATCH | 7 |
| Schema: structurally invalid candidate (missing section) | SCHEMA_MISMATCH | 7 |
| Live legacy drift (monkeypatched) | LEGACY_DRIFT | 8 |
| Environment mismatch (monkeypatched) | ENVIRONMENT_MISMATCH | 5 |
| Manifest integrity failure (monkeypatched) | ManifestIntegrityError propagated; CLI exit | 4 |
| Unknown baseline via CLI ValueError | CLI ValueError caught | 2 |
| Unexpected RuntimeError | EXECUTION_ERROR; CLI exit | 1 |
| EXECUTION_ERROR + PAYLOAD_DRIFT mixed | EXECUTION_ERROR dominates | 1 |
| Mixed status order-independence (_build_aggregate reversed) | EXECUTION_ERROR stable | 1 |
| Provider call count before env check | 0 (not called) | — |
| Provider call count before legacy check | 0 (not called) | — |

---

## Depreciation Implementation

Book and tax depreciation use `finco_core.debt.depreciation_schedule.build_depreciation_schedule` and `depreciation_per_period` — the same generic straight-line, day-fraction-based formula as the legacy `waterfall_core.py` path:

```
annual_dep = item.amount_keur / useful_life_years
dep_per_period = annual_dep * period.day_fraction
```

Useful lives come from `ASSET_CLASS_USEFUL_LIFE` in `finco_core.inputs`. No project-code dispatch, no fixture reads.

`DepreciationInput` has no defaults — both `capex_items_for_depreciation` and `financial_cost_useful_life_years` are required. The adapter maps `inputs.financing.senior_tenor_years` explicitly with no fallback.

---

## Public Aggregate API

`compare_candidate_provider()` in `finco_parity.dual_run` is the primary public API:

1. Loads one `ValidatedManifestContext` (single manifest read).
2. Validates selected baseline IDs; raises `ValueError` for unknown IDs.
3. Preserves manifest order.
4. Calls the provider exactly once per baseline via `_run_candidate_with_context()`.
5. Selects `overall_status` using `_AGGREGATE_SEVERITY` ordering.
6. Returns `AggregateRunResult`.

`exit_code_for_aggregate()` in `finco_parity.dual_run` maps `overall_status` to CLI exit codes for all Phase 1C and Phase 2A CLIs.

The Phase 2A CLI (`check_financial_engine_operating_core`) is a thin wrapper — it imports only public APIs and does not call private orchestration functions.

---

## Production Isolation

The `financial_engine` package:
- Does not import: `app`, `main_web`, `main_api`, `finco_parity`, `persistence`, `fastapi`, `jinja2`, `requests`, `openpyxl`, `pandas`
- Does not contain forbidden identifiers
- Does not call: `run_waterfall`, `run_waterfall_v3_core`, `WaterfallRunner`
- Is not accessible through any production route

Protected files confirmed unchanged (zero diff against HEAD):
- `app/waterfall_core.py`, `app/waterfall_runner.py`
- `finco_core/waterfall/waterfall_engine.py`
- `app/`, `domain/`, `main_web.py`, `main_api.py`, `finco_core/waterfall/`

---

## Test Coverage

| Test module | Collected |
|---|---|
| `test_phase2a_engine_inputs.py` | 30 |
| `test_phase2a_orchestrator.py` | 58 |
| `test_phase2a_production_isolation.py` | 34 |
| **Total** | **122** |

All 122 tests pass.

---

## Architecture Decisions

**Why `build_depreciation_schedule` + `depreciation_per_period`?**

These are the generic identity-blind leaves that the legacy `waterfall_core.py` also calls. Using them produces bitwise-identical values without copying expected outputs or introducing project-code dispatch.

**Why book = tax depreciation?**

In the Phase 2A operating core, the baseline arrays are bitwise identical. ATAD-adjusted tax depreciation is out of Phase 2A scope; Phase 2B will diverge book from tax when tax calculations are implemented.

**Why `DepreciationInput` has no defaults?**

Making both fields required prevents silent use of a hardcoded fallback. The adapter always maps `inputs.financing.senior_tenor_years` explicitly; any missing attribute surfaces as `AttributeError` immediately rather than silently using a wrong value.

**Why `compare_candidate_provider()` is the public aggregate API?**

It centralizes manifest loading (once per run), baseline-ID validation, manifest-order preservation, and aggregate-status selection. The CLI is a thin wrapper that supplies the provider and profile, not a reimplementation.
