# Phase S1-C Implementation Report — Factory vs Resolver Unification

**Status**: DRAFT, awaiting review
**Date**: 2026-06-17
**Branch**: `phase/s1c-unify-generic-factory-resolver`
**Base**: `main` @ `9fc58a5` (post S1-A)

## Summary

Phase S1-C eliminates the Generic factory-direct vs resolver
divergence by zeroing the Generic factory financial CAPEX
sub-fields (`idc_keur`, `bank_fees_keur`, etc.). The resolver
function `_zero_financial_capex_subfields` is retained as a
defensive no-op.

TUHO and Oborovo factories are unchanged. Their frozen
Excel-derived `idc_keur/bank_fees_keur` values are preserved.

## Empirical results

### Generic Solar before vs after S1-C

| Metric | Pre-S1-C Factory | Post-S1-C Factory | Pre-S1-C Resolver | Post-S1-C Resolver |
| --- | ---: | ---: | ---: | ---: |
| `idc_keur` | 500.00 | **0.00** | 0.00 | 0.00 |
| `bank_fees_keur` | 200.00 | **0.00** | 0.00 | 0.00 |
| `total_capex` | 30,700.00 | **30,000.00** | 30,000.00 | 30,000.00 |
| `debt_keur` | 22,650.00 | **22,500.00** | 22,500.00 | 22,500.00 |
| `project_irr` | 0.0896 | **0.0921** | 0.0921 | 0.0921 |
| `equity_irr` | 0.1311 | **0.1420** | 0.1420 | 0.1420 |

### Generic Wind before vs after S1-C

| Metric | Pre-S1-C Factory | Post-S1-C Factory | Pre-S1-C Resolver | Post-S1-C Resolver |
| --- | ---: | ---: | ---: | ---: |
| `idc_keur` | 800.00 | **0.00** | 0.00 | 0.00 |
| `bank_fees_keur` | 300.00 | **0.00** | 0.00 | 0.00 |
| `total_capex` | 40,100.00 | **39,000.00** | 39,000.00 | 39,000.00 |
| `debt_keur` | 29,550.00 | **29,250.00** | 29,250.00 | 29,250.00 |

### TUHO/Oborovo parity preserved

| Project | `debt_keur` (Pre) | `debt_keur` (Post) | Delta |
| --- | ---: | ---: | ---: |
| TUHO | 43,359.00 | 43,359.00 | 0 |
| Oborovo | 42,852.27 | 42,852.27 | 0 |

## Engine and factory MD5

| File | MD5 (Pre-S1-C) | MD5 (Post-S1-C) | Status |
| --- | --- | --- | --- |
| `app/waterfall_core.py` | `6bf49f33...` | `6bf49f33...` | UNCHANGED |
| `app/project_factories.py` | `3350c93a...` | `cf73065b...` | INTENTIONALLY CHANGED |

## Test results

### New S1-C tests
- `tests/test_phase_s1c_factory_resolver_consistency.py`: **26/26 PASS**
- 5 tests on factory defaults zeroing
- 4 tests on factory-direct ≡ resolver
- 8 tests on TUHO/Oborovo parity preservation
- 5 tests on MD5 invariants (engine unchanged, factory updated)
- 3 tests on export consistency (post S1-A)
- 1 test on scenario matrix consistency

### Existing tests
- Phase 51F parity guardrails: **21/21 PASS**
- Phase 23s combined frozen-schedule parity: **9/9 PASS**
- Phase 23a frozen schedule runtime wiring: **16/16 PASS**
- Phase S1-A export tests: **20/20 PASS**
- Phase 1 generic sculpt unify: **42/42 PASS**
- Generic Solar/Wind runtime: 7/7 PASS
- Generic full flow integration: 7/7 PASS
- BESS factory: 14/14 PASS
- BESS hybrid full flow: 12/12 PASS
- Financial formulas: 18/18 PASS
- Excel export: PASS
- Cache parity: PASS
- Construction runtime adapter / flag: PASS

### Pre-existing rot (not S1-C regressions)
- `test_depreciation_canonical_wiring.py::test_oborovo_equity_irr_within_tolerance_dep_canonical`: fails on main
- `test_phase20o_debt_sizing_modes.py::test_oborovo_default_outputs_unchanged_*` (3 tests): fail on main
- `test_phase23d_prep_tuho_fixture_backed_frozen_senior_ds.py::test_oborovo_frozen_fixture_still_unavailable_and_off`: fails on main
- `test_phase10_institutional_workbook_skeleton.py::test_docs_keep_runtime_scope_and_governance_constraints`: fails on main (doc guard)
- `test_phase14_export_lineage_ui.py::test_export_lineage_panel_and_download_semantics_are_visible`: fails on main (template guard)

All pre-existing rot confirmed against main `9fc58a5`. None are
S1-C regressions.

## Files

| File | Change |
| --- | --- |
| `app/project_factories.py` | +5 / -5 |
| `tests/test_phase_s1c_factory_resolver_consistency.py` | NEW, 360 lines, 26 tests |
| `tests/test_phase51f_parallel_work_guardrails.py` | +1 / -1 (factory MD5 baseline) |
| `tests/test_phase_s1a_export_runtime_senior_debt.py` | +18 / -1 (factory MD5 baseline) |
| `docs/phase_s1c_factory_resolver_unification.md` | NEW |
| `reports/phase_s1c_factory_resolver_unification.md` | NEW |

Total: 6 files, +~420 / -8

## Constraints preserved (all pinned by tests)

- ✅ rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` untouched
- ✅ Engine MD5 `6bf49f33efc989736c17cea0cb9b7723` UNCHANGED
- ✅ TUHO debt_keur `43,359.00` (frozen)
- ✅ Oborovo debt_keur `42,852.27` (frozen)
- ✅ No financial formula / debt / DSCR sculpt / tax / IDC / construction / sponsor changes
- ✅ No persistence schema migration
- ✅ No R99 / R102 / G20 work
- ✅ `_zero_financial_capex_subfields` retained as defensive no-op

## Generic exploratory output changes (intentional)

This is **not an engine formula change**. The runtime sculpt
formula is unchanged.

It **IS a Generic runtime output change**. Generic exploratory
defaults (factory outputs) now match what the user sees after
form submission (resolver outputs). This is the goal of S1-C.

Generic Solar factory-direct `debt_keur` changes from
**22,650 → 22,500** (-150 kEUR).
Generic Solar factory-direct `project_irr` changes from
**0.0896 → 0.0921**.
Generic Solar factory-direct `equity_irr` changes from
**0.1311 → 0.1420**.

Generic Wind factory-direct `debt_keur` changes from
**29,550 → 29,250** (-300 kEUR).

These changes are the result of removing the 500/200 (Solar)
or 800/300 (Wind) financial cost sub-fields from the factory
defaults. The runtime no longer applies gearing-cap reductions
on those sub-fields because they are zero.

TUHO and Oborovo are unchanged (their factories still have
frozen Excel-derived values; their `fixed_debt_keur` overrides
override the runtime sculpt).

## Stop-after-report

DRAFT only. Do NOT mark ready, do NOT merge. Awaiting user
review and explicit go-ahead.

Next step options after approval:
- S1-D: documentation update (no risk, ~1h)
- Pause and review the arc