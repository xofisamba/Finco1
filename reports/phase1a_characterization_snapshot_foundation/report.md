# Phase 1A — Legacy Characterization Snapshot Foundation

**Date:** 2026-07-17  
**Branch:** `phase1a-characterization-snapshot-foundation`  
**Base commit:** `06ab2fd0` (squash merge of security hotfix PR #889)  
**Status:** Complete — awaiting review

---

## 1. Purpose

Phase 1A captures deterministic, normalized snapshots of the current legacy waterfall engine for four baseline projects.  These snapshots are the authoritative reference baseline against which the extracted financial engine (Phase 2+) will be compared.  No production code was changed.

---

## 2. Baseline Projects

| baseline_id | project_type_key | Technology | Frozen Fixture | Identity Guard |
|---|---|---|---|---|
| `tuho` | `TUHO` | Wind | ✓ `reports/phase7_tuho_senior_debt_sizing_extraction.csv` | `code == "TUHO-WIND-1"` |
| `oborovo` | `Oborovo` | Solar | ✓ `reports/phase23q_oborovo_senior_debt_sizing_extraction.csv` | `code == "OBOROVO-SOLAR-1"` |
| `generic_solar` | `Test 1` | Solar | ✗ (live sizing) | none |
| `generic_wind` | `Test 2` | Wind | ✗ (live sizing) | none |

---

## 3. Execution Paths

### Canonical run path (all four baselines)

```
python -m finco_parity.legacy_snapshot --baseline <id> --output <file>
```

Internal call chain:

```
legacy_snapshot.capture_snapshot(baseline_id)
  → app.ui_runner.run_demo_project(project_type)
    → FACTORY_MAP[project_type]()              # e.g. create_default_tuho_wind1()
    → WaterfallRunner.run(config)              # app/waterfall_runner.py:353
      → run_waterfall_v3_core(inputs)          # app/waterfall_core.py (uncached)
        → run_waterfall(inputs, periods)       # finco_core/waterfall/waterfall_engine.py
        → [TUHO/Oborovo: frozen DS fixture injected by identity guard]
  → domain.financial_statements.assembly.assemble_financial_statements(result)
  → finco_parity.normalization.normalize_snapshot(result, ...)
  → finco_parity.schema.validate_snapshot(snapshot)
```

### Identity guard (TUHO and Oborovo)

```python
# app/waterfall_core.py, ~line 760
is_tuho = (getattr(inputs.info, "code", "") == "TUHO-WIND-1")
is_oborovo = (getattr(inputs.info, "code", "") == "OBOROVO-SOLAR-1")
```

When `is_tuho` is True, the senior debt schedule is loaded from the frozen CSV fixture (`reports/phase7_tuho_senior_debt_sizing_extraction.csv`) instead of being sized live.  Same logic applies for Oborovo.  This guard ensures that TUHO and Oborovo snapshots are deterministic across runs regardless of live-sizing changes.

---

## 4. Authoritative Output Inventory

### 4.1 `period_grid` (per-period row)

Sourced from `waterfall_result.periods` (list of `WaterfallPeriod` in `finco_core/waterfall/waterfall_engine.py:48`).

| Field | WaterfallPeriod attr | Type | Notes |
|---|---|---|---|
| `period_index` | `period` | float | Fallback: list index |
| `year_index` | `year_index` | float | |
| `period_in_year` | `period_in_year` | float | |
| `start_date` | `start_date` | ISO-8601 str | |
| `end_date` | `end_date` | ISO-8601 str | |
| `is_operation` | `is_operation` | bool | |
| `is_construction` | `is_construction` | bool | |

### 4.2 `operating_schedules` (per-period series)

| Snapshot field | WaterfallPeriod attr |
|---|---|
| `production_mwh` | `generation_mwh` |
| `revenue_keur` | `revenue_keur` |
| `opex_keur` | `opex_keur` |
| `ebitda_keur` | `ebitda_keur` |
| `book_depreciation_keur` | `depreciation_keur` |
| `tax_depreciation_keur` | `tax_depreciation_audit_keur` |

### 4.3 `tax_and_cfads` (per-period series)

| Snapshot field | WaterfallPeriod attr | Notes |
|---|---|---|
| `taxable_income_keur` | `taxable_income_keur` | |
| `deductible_interest_keur` | `deductible_interest_keur` | |
| `disallowed_interest_keur` | `disallowed_interest_keur` | |
| `cash_tax_keur` | `tax_keur` | |
| `loss_carryforward_keur` | `loss_carryforward_keur` | |
| `fiscal_reintegration_keur` | `fiscal_reintegration_keur` | |
| `cfads_proxy_keur` | `cf_after_tax_keur` | **Ambiguous — see Section 5** |

### 4.4 `financing` (per-period series)

#### senior_debt

| Snapshot field | WaterfallPeriod attr | Notes |
|---|---|---|
| `closing_keur` | `senior_balance_keur` | Closing balance |
| `interest_keur` | `senior_interest_keur` | |
| `principal_keur` | `senior_principal_keur` | |
| `debt_service_keur` | `senior_ds_keur` | |
| `dscr` | `dscr` | |
| `dsra_keur` | `dsra_balance_keur` | |
| `llcr` | — | `UNAVAILABLE` — not computed in legacy engine |

#### shl

| Snapshot field | WaterfallPeriod attr |
|---|---|
| `opening_keur` | `shl_opening_keur` |
| `interest_keur` | `shl_interest_keur` |
| `principal_keur` | `shl_principal_keur` |
| `closing_keur` | `shl_balance_keur` |
| `pik_accrual_keur` | `shl_pik_accrual_keur` |

#### equity

| Snapshot field | WaterfallPeriod attr |
|---|---|
| `distributions_keur` | `distributions_keur` |
| `injections_keur` | `equity_injection_keur` |

### 4.5 `returns` (scalar aggregates from WaterfallResult)

| Snapshot field | WaterfallResult attr |
|---|---|
| `project_irr` | `project_irr` |
| `equity_irr` | `equity_irr` |
| `avg_dscr` | `avg_dscr` |
| `actual_avg_dscr` | `actual_avg_dscr` |
| `min_dscr` | `min_dscr` |
| `actual_min_dscr` | `actual_min_dscr` |
| `total_revenue_keur` | `total_revenue_keur` |
| `total_ebitda_keur` | `total_ebitda_keur` |
| `total_opex_keur` | `total_opex_keur` |
| `total_tax_keur` | `total_tax_keur` |
| `total_senior_ds_keur` | `total_senior_ds_keur` |
| `total_distributions_keur` | `total_distributions_keur` |
| `equity_irr_method` | `equity_irr_method` |

### 4.6 `financial_statements`

Sourced from `domain.financial_statements.assembly.assemble_financial_statements(waterfall_result)`.  Normalized via `normalize_value()` (recursive dataclass / dict traversal).  Set to `UNAVAILABLE` (None) if assembly raises or returns None.  Marked in `unavailable_sections` when absent.

---

## 5. CFADS Ambiguity

Multiple CFADS representations exist in the codebase.  The snapshot captures all available period-level cash-flow data without resolving the ambiguity.

| Representation | Source | Snapshot field |
|---|---|---|
| `cf_after_tax_keur` | `WaterfallPeriod.cf_after_tax_keur` | `tax_and_cfads.cfads_proxy_keur` |
| Sizing CFADS (EBITDA × (1−tax)) | Internal to debt-sculpting logic | Not directly on WaterfallPeriod |
| Fixture CFADS (TUHO/Oborovo) | Frozen CSV rows `cfads_keur` | Not extracted in Phase 1A |
| SHL-specific CFADS | EBITDA − senior_ds | Reconstructable from captured fields |

**Phase 1A decision:** Capture `cf_after_tax_keur` as `cfads_proxy_keur`.  Resolution of the correct CFADS definition is deferred to Phase 2+ when the extracted engine provides a single authoritative source.

---

## 6. Normalization Design Contract

- `None` is preserved as `None` and is distinct from `0.0`.
- `float('nan')` and `±inf` are converted to `None` (not serializable in standard JSON).
- `Decimal` is converted to `float` via `_safe_float()`.
- `datetime.date` and `datetime.datetime` are serialized as ISO-8601 `"YYYY-MM-DD"` strings.
- `enum.Enum` values are serialized as their `.value`.
- Dataclasses are serialized field-by-field (no `repr`, no memory addresses), keys sorted.
- Unsupported types raise `NormalizationError` rather than producing unstable `repr()` strings.
- No current timestamps, random IDs, or absolute repository paths in snapshot content.
- JSON is serialized with `sort_keys=True` at the outer layer for any remaining dict nodes.

---

## 7. Deliverables

| File | Description |
|---|---|
| `finco_parity/schema.py` | Versioned snapshot schema, `UNAVAILABLE` sentinel, `validate_snapshot()`, `build_empty_snapshot()` |
| `finco_parity/normalization.py` | Deterministic normalization layer, `normalize_snapshot()` public API |
| `finco_parity/legacy_snapshot.py` | CLI runner (`python -m finco_parity.legacy_snapshot`) |
| `finco_parity/baselines/__init__.py` | Package init for baselines subpackage |
| `finco_parity/baselines/manifest.json` | Machine-readable baseline manifest (4 projects) |
| `finco_parity/__init__.py` | Updated docstring documenting Phase 1A additions |
| `tests/test_phase1a_parity_schema_normalization.py` | 92 unit tests for schema and normalization |
| `tests/test_phase1a_parity_manifest.py` | Manifest structural and cross-reference tests |
| `tests/test_phase1a_parity_runner.py` | Runner CLI + end-to-end engine capture tests (67 tests) |
| `reports/phase1a_characterization_snapshot_foundation/report.md` | This report |

---

## 8. CLI Usage

```bash
# Single baseline
python -m finco_parity.legacy_snapshot --baseline tuho --output /tmp/tuho.json
python -m finco_parity.legacy_snapshot --baseline oborovo --output /tmp/oborovo.json --pretty
python -m finco_parity.legacy_snapshot --baseline generic_solar --output /tmp/solar.json

# All four baselines
python -m finco_parity.legacy_snapshot --all --output-dir /tmp/finco-snapshots

# With explicit git SHA
python -m finco_parity.legacy_snapshot --baseline tuho \
    --output /tmp/tuho.json \
    --commit-sha $(git rev-parse HEAD)
```

---

## 9. Test Results

```
tests/test_phase1a_parity_schema_normalization.py    92 passed
tests/test_phase1a_parity_manifest.py                31 passed
tests/test_phase1a_parity_runner.py                  67 passed
Total Phase 1A tests:                               190 passed
```

Full regression suite: no new failures introduced.  Pre-existing failure:  
`tests/test_auth_lite.py::TestRateLimiting::test_successful_login_clears_failed_attempts` — confirmed pre-existing on `main` before this branch.

---

## 10. Scope Constraints Honoured

- No changes to any financial formula
- No changes to tax logic, CFADS logic, debt sizing or sculpting, waterfall ordering
- No changes to TUHO or Oborovo results
- No changes to numerical parity targets or approved golden values
- No changes to project factories or templates
- No changes to Workbook V2 behavior or RuntimeResult semantics
- No changes to persistence, routes, or UI
- No creation of `financial_engine/` directory
- No removal of identity guards or frozen schedules
- No financial inconsistency resolved
- No scenario, export, BESS, multi-lender, or sponsor scope added
- PR is **Draft** — not merged
