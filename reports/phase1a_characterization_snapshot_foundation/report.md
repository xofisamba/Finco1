# Phase 1A — Legacy Characterization Snapshot Foundation (Amended)

**Date:** 2026-07-17  
**Branch:** `phase1a-characterization-snapshot-foundation`  
**Base commit:** `06ab2fd0` (squash merge of security hotfix PR #889)  
**Previous head:** `e20c8fca` (initial Phase 1A + docs restore)  
**Status:** Amendment complete — awaiting review

---

## 1. Purpose

Phase 1A captures deterministic, normalized snapshots of the current legacy waterfall engine for four baseline projects.  These snapshots are the authoritative reference baseline against which the extracted financial engine (Phase 2+) will be compared.  No production code was changed.

---

## 2. Baseline Projects

| baseline_id | project_type_key | project_code | Technology | capacity_mw | horizon_years | Frozen Fixture |
|---|---|---|---|---|---|---|
| `tuho` | `TUHO` | `TUHO-WIND-1` | Wind | 35.0 | 30 | ✓ (capability flag) |
| `oborovo` | `Oborovo` | `OBR-001` | Solar | 75.26 | 30 | ✓ (capability flag) |
| `generic_solar` | `Test 1` | `TEST-SOLAR-1` | Solar | 50.0 | 20 | ✗ (live sizing) |
| `generic_wind` | `Test 2` | `TEST-WIND-1` | Wind | 40.0 | 25 | ✗ (live sizing) |

**Key correction from initial submission:** Oborovo project code is `OBR-001`, not `OBOROVO-SOLAR-1`.  Generic Solar is `TEST-SOLAR-1`; Generic Wind is `TEST-WIND-1`.

---

## 3. Fixture Selection Mechanism

Fixture selection is **capability-driven** via `FinancingParams` fields set in each factory function.  There is no project-code guard in `waterfall_core.py` that selects the fixture.

**TUHO** (`create_default_tuho_wind1`):
```python
use_frozen_excel_senior_debt_schedule=True   # Phase 23F
frozen_senior_ds_fixture_path="reports/phase7_tuho_senior_debt_sizing_extraction.csv"
use_senior_debt_sizing_engine=True           # Phase 23F canonical sizing path
```

**Oborovo** (`create_default_oborovo`):
```python
use_frozen_excel_senior_debt_schedule=True   # Phase 23R
frozen_senior_ds_fixture_path="reports/phase23q_oborovo_senior_debt_sizing_extraction.csv"
use_senior_debt_sizing_engine=True           # Phase 23R
```

**Generic Solar / Generic Wind**: no frozen fixture; senior debt is sized live by the sculpting engine on every run.

---

## 4. Production Run Path vs. Offline Capture Path

### 4.1 Full production Run path

```
HTTP POST /run
→ app.services.run_service.execute_run_route
  → user-created path / TUHO-Oborovo template path / generic path
  → deps.run_project
  → app.api.project_runner.run_project
    → app.ui_runner.run_demo_project
      → FACTORY_MAP[project_type]()                  # factory → ProjectInputs
      → WaterfallRunner.run(config)                   # app/waterfall_runner.py:353
        → run_waterfall_v3_core(inputs)               # app/waterfall_core.py
          → capability-driven fixture injection        # use_frozen_excel_senior_debt_schedule
          → run_waterfall(inputs, periods)             # finco_core/waterfall/waterfall_engine.py
          → WaterfallResult
      → project_runner serializers:
          _serialize_debt_schedule(result)
          _serialize_tax_schedule(result)
          _serialize_distribution_schedule(result)
          _serialize_sponsor_schedule(...)
      → assemble_financial_statements(waterfall_result)
      → RuntimeResult.to_sessionstorage_script()
      → persistence (SQLite)
      → Workbook V2 hydration / projection engine
```

### 4.2 Legacy calculation capture path (this PR)

```
python -m finco_parity.legacy_snapshot --baseline <id>
→ finco_parity.legacy_snapshot.capture_snapshot(baseline_id)
  → app.ui_runner.run_demo_project(project_type)
    → factory → WaterfallRunner → run_waterfall_v3_core → WaterfallResult
  → domain.financial_statements.assembly.assemble_financial_statements(result)
  → finco_parity.normalization.normalize_snapshot(result, ...)
  → finco_parity.schema.validate_snapshot(snapshot)
  → JSON write (allow_nan=False)
```

**What this runner executes:** factory → WaterfallRunner → core engine → financial statement assembly.

**What this runner does NOT execute:** `run_project` post-engine serializers, persistence, sessionStorage script, Workbook V2 hydration, runtime projection engine.

These terms are used consistently throughout this report:
- **Production Run path**: the full HTTP → serializers → persistence → Workbook path
- **Legacy calculation capture path**: the offline factory → WaterfallRunner → engine path

---

## 5. WaterfallResult.periods — Operation-Only Axis

`WaterfallResult.periods` contains **operation-only periods**.  The legacy engine (`run_waterfall_v3_core`) passes only operation periods into `run_waterfall()`.  There is no construction-period axis in the WaterfallResult.

The period grid in the snapshot therefore reflects only the operation-period axis.  Upstream `PeriodEngine` produces a full calendar (including construction), but that data does not flow into `WaterfallResult.periods`.

---

## 6. Authoritative Output Inventory

### 6.1 period_grid

| Snapshot field | WaterfallPeriod attr | Status |
|---|---|---|
| `period_index` | `period` (int) | Captured |
| `date` | `date` (datetime.date) | Captured |
| `year_index` | `year_index` (int) | Captured |
| `period_in_year` | `period_in_year` (int) | Captured |
| `is_operation` | `is_operation` (bool) | Captured |
| `start_date` | — | **Unavailable** — only period-end date stored |
| `is_construction` | — | **Unavailable** — operation-only period axis |

### 6.2 operating_schedules

| Snapshot field | WaterfallPeriod attr | Status |
|---|---|---|
| `production_mwh` | `generation_mwh` | Captured |
| `revenue_keur` | `revenue_keur` | Captured |
| `opex_keur` | `opex_keur` | Captured |
| `ebitda_keur` | `ebitda_keur` | Captured |
| `book_depreciation_keur` | `depreciation_keur` | Captured |
| `tax_depreciation_keur` | `tax_depreciation_audit_keur` | Captured |

### 6.3 tax_and_cfads

#### Tax accrual vs cash-tax distinction

| Snapshot field | WaterfallPeriod attr | Classification |
|---|---|---|
| `taxable_profit_keur` | `taxable_profit_keur` | Taxable income before LCF |
| `taxable_income_before_losses_audit_keur` | `taxable_income_before_losses_audit_keur` | Audit alias for pre-LCF |
| `taxable_profit_after_losses_audit_keur` | `taxable_profit_after_losses_audit_keur` | Taxable income after LCF |
| `cit_accrual_audit_keur` | `cit_accrual_audit_keur` | **Tax accrual (P&L expense)** |
| `cash_tax_current_period_audit_keur` | `cash_tax_current_period_audit_keur` | **Current-period cash CIT** |
| `corporate_tax_cash_keur` | `corporate_tax_cash_keur` | Primary cash tax field |
| `tax_keur` | `tax_keur` | Legacy combined field — **ambiguous; do not classify as authoritative cash tax** |
| `cash_tax_bridge_reconciliation_keur` | `cash_tax_bridge_reconciliation_keur` | Diagnostic bridge (not primary) |
| `tax_loss_opening_audit_keur` | `tax_loss_opening_audit_keur` | LCF opening balance |
| `tax_loss_used_audit_keur` | `tax_loss_used_audit_keur` | LCF used this period |
| `tax_loss_closing_audit_keur` | `tax_loss_closing_audit_keur` | LCF closing balance |
| `tax_depreciation_audit_keur` | `tax_depreciation_audit_keur` | Tax depreciation |
| `fiscal_reintegration_audit_keur` | `fiscal_reintegration_audit_keur` | Fiscal reintegration |

Fields NOT on WaterfallPeriod (not captured):
- `deductible_interest_keur` — not a WaterfallPeriod attribute
- `disallowed_interest_keur` — not a WaterfallPeriod attribute

#### CFADS variants (all captured; canonical owner unresolved — Phase 1B)

| Snapshot field | WaterfallPeriod attr | Description |
|---|---|---|
| `cf_after_tax_keur` | `cf_after_tax_keur` | CF after tax, before senior DS |
| `r69_fcf_banks_keur` | `r69_fcf_banks_keur` | FCF to banks (pre-DS, post-tax) |
| `r84_fcf_junior_keur` | `r84_fcf_junior_keur` | FCF after senior DS |
| `r99_fcf_for_distribution_keur` | `r99_fcf_for_distribution_keur` | FCF for distribution (post-DA) |
| `r102_fcf_for_shl_keur` | `r102_fcf_for_shl_keur` | FCF for SHL service |
| `fcf_for_shl_keur` | `fcf_for_shl_keur` | SHL FCF (waterfall approach) |

### 6.4 financing — senior_debt

| Snapshot field | WaterfallPeriod attr | Status |
|---|---|---|
| `opening_keur` | — | **Unavailable** — reconstructed field, not native |
| `drawdown_keur` | — | **Unavailable** — not a native WaterfallPeriod attribute |
| `closing_keur` | `senior_balance_keur` | Captured |
| `interest_keur` | `senior_interest_keur` | Captured |
| `principal_keur` | `senior_principal_keur` | Captured |
| `debt_service_keur` | `senior_ds_keur` | Captured |
| `dscr` | `dscr` | Captured |
| `llcr` | `llcr` | **Captured** (real WaterfallPeriod attribute) |
| `plcr` | `plcr` | Captured |
| `dsra_balance_keur` | `dsra_balance_keur` | Captured |
| `dsra_contribution_keur` | `dsra_contribution_keur` | Captured |
| `cash_sweep_keur` | `cash_sweep_keur` | Captured |

### 6.5 financing — shl

| Snapshot field | WaterfallPeriod attr | Status |
|---|---|---|
| `opening_keur` | — | **Unavailable** — not a native attribute |
| `interest_keur` | `shl_interest_keur` | Captured |
| `principal_keur` | `shl_principal_keur` | Captured |
| `service_keur` | `shl_service_keur` | Captured |
| `closing_keur` | `shl_balance_keur` | Captured |
| `pik_keur` | `shl_pik_keur` | Captured |
| `gross_accrued_interest_keur` | `shl_gross_accrued_interest_keur` | Captured |

Note: `shl_pik_accrual_keur` does not exist; correct attribute is `shl_pik_keur`.

### 6.6 financing — equity

| Snapshot field | WaterfallPeriod attr | Status |
|---|---|---|
| `distribution_keur` | `distribution_keur` | **Captured** (singular, not `distributions_keur`) |
| `injections_keur` | — | **Unavailable** — not a native WaterfallPeriod attribute |
| `cf_after_reserves_keur` | `cf_after_reserves_keur` | Captured |
| `lockup_active` | `lockup_active` | Captured |

### 6.7 returns (WaterfallResult aggregates)

| Snapshot field | WaterfallResult attr | Status |
|---|---|---|
| `project_irr` | `project_irr` | Captured |
| `equity_irr` | `equity_irr` | Captured |
| `sponsor_irr` | `sponsor_irr` | Captured |
| `project_npv` | `project_npv` | Captured |
| `equity_npv` | `equity_npv` | Captured |
| `avg_dscr` | `avg_dscr` | Captured |
| `min_dscr` | `min_dscr` | Captured |
| `actual_avg_dscr` | `actual_avg_dscr` | Captured |
| `actual_min_dscr` | `actual_min_dscr` | Captured |
| `min_llcr` | `min_llcr` | Captured |
| `min_plcr` | `min_plcr` | Captured |
| `periods_in_lockup` | `periods_in_lockup` | Captured |
| `total_revenue_keur` | `total_revenue_keur` | Captured |
| `total_opex_keur` | `total_opex_keur` | Captured |
| `total_ebitda_keur` | `total_ebitda_keur` | Captured |
| `total_tax_keur` | `total_tax_keur` | Captured |
| `total_senior_ds_keur` | `total_senior_ds_keur` | Captured |
| `total_shl_service_keur` | `total_shl_service_keur` | Captured |
| `total_distribution_keur` | `total_distribution_keur` | **Captured** (singular, not `total_distributions_keur`) |
| `equity_irr_method` | `equity_irr_method` | Captured |

---

## 7. CFADS Ambiguity

Multiple CFADS representations exist.  The snapshot captures all available period-level variants without resolving the canonical owner.  Resolution is deferred to Phase 1B.

| Field | Source | Snapshot location |
|---|---|---|
| `cf_after_tax_keur` | WaterfallPeriod — CF after tax, before senior DS | `tax_and_cfads.cf_after_tax_keur` |
| `r69_fcf_banks_keur` | Audit waterfall: FCF to banks | `tax_and_cfads.r69_fcf_banks_keur` |
| `r84_fcf_junior_keur` | Audit waterfall: FCF after senior DS | `tax_and_cfads.r84_fcf_junior_keur` |
| `r99_fcf_for_distribution_keur` | Distribution account output | `tax_and_cfads.r99_fcf_for_distribution_keur` |
| `r102_fcf_for_shl_keur` | SHL FCF (audit) | `tax_and_cfads.r102_fcf_for_shl_keur` |
| `fcf_for_shl_keur` | SHL FCF (waterfall approach) | `tax_and_cfads.fcf_for_shl_keur` |
| Fixture sizing CFADS | Frozen CSV rows (TUHO/Oborovo) | Not extracted in Phase 1A |

**The snapshot does not claim to have resolved the canonical CFADS owner.**

---

## 8. Explicitly Unavailable Fields

Fields explicitly marked unavailable with `[None] * n_periods` or `None`:

| Field | Reason |
|---|---|
| `period_grid[*].start_date` | Only period-end `date` is stored on WaterfallPeriod |
| `period_grid[*].is_construction` | operation-only period axis; no construction periods |
| `financing.senior_debt.opening_keur` | Not a native WaterfallPeriod attribute |
| `financing.senior_debt.drawdown_keur` | Not a native WaterfallPeriod attribute |
| `financing.shl.opening_keur` | `shl_opening_keur` does not exist on WaterfallPeriod |
| `financing.equity.injections_keur` | `equity_injection_keur` does not exist on WaterfallPeriod |
| `financial_statements` | Marked `UNAVAILABLE` when assembly fails |

Non-finite engine outputs (e.g., `inf` LLCR/PLCR for zero-debt periods) are also converted to `None` with a warning recorded in `snapshot.warnings`.

---

## 9. Normalization Design Contract

- `None` is preserved as `None` and is distinct from `0.0`.
- NaN and `±inf` from the engine are converted to `UNAVAILABLE` (None) with a warning logged in `snapshot.warnings`.
- `Decimal` is converted to `float` via `float()`. Precision is limited to IEEE-754 double (~15-16 significant digits).
- `datetime.date` / `datetime.datetime` → ISO-8601 `"YYYY-MM-DD"`.
- `enum.Enum` → `.value`.
- Dataclasses → field-by-field dict, keys sorted.
- Unsupported types raise `NormalizationError`.
- JSON serialized with `allow_nan=False` (enforces no non-finite values in output).
- `sort_keys=True` at the JSON layer.
- No timestamps, random IDs, absolute paths, or memory addresses in output.
- Attribute typos are detectable: `_get_float_series()` records a warning and returns `[None]*n` when an attribute is missing, rather than raising silently; real-value tests then catch accidental all-None schedules.

---

## 10. Schema Validation (Amendment 4)

`validate_snapshot()` now checks:

1. Top-level type and required keys
2. Required provenance values are non-empty strings
3. `schema_version` matches `SCHEMA_VERSION`
4. `period_grid`: list, each row is a dict with `period_index`, unique, sorted
5. `operating_schedules`: required keys present; series lengths match `n_periods`
6. `financing.senior_debt`: required keys; series lengths match `n_periods`
7. `returns`: required keys including `total_distribution_keur`
8. `warnings` and `unavailable_sections` are lists
9. No non-finite floats in any section (recursive check)
10. Duplicate period indices raise `SnapshotValidationError`
11. Unsorted period indices raise `SnapshotValidationError`

---

## 11. Determinism Results

All four baselines pass double-run comparison (identical canonical JSON for same SHA):

| baseline_id | Deterministic? | Notes |
|---|---|---|
| `tuho` | ✓ | Frozen senior DS fixture ensures deterministic debt schedule |
| `oborovo` | ✓ | Frozen senior DS fixture ensures deterministic debt schedule |
| `generic_solar` | ✓ | Live-sized; engine is deterministic for identical inputs |
| `generic_wind` | ✓ | Live-sized; engine is deterministic for identical inputs |

Test evidence: `TestDeterminism::test_two_runs_identical[tuho/oborovo/generic_solar/generic_wind]` — all 4 pass.

---

## 12. Deliverables

| File | Change |
|---|---|
| `finco_parity/schema.py` | New — versioned schema, `UNAVAILABLE`, `validate_snapshot()` with nested/alignment/nonfinite checks |
| `finco_parity/normalization.py` | New — corrected field mappings, strict `_safe_float`, inf→warning, `normalize_snapshot()` |
| `finco_parity/legacy_snapshot.py` | New — CLI runner; removed unused `run_project` import; `allow_nan=False` |
| `finco_parity/baselines/__init__.py` | New — package init |
| `finco_parity/baselines/manifest.json` | New — corrected: OBR-001, TEST-SOLAR-1/WIND-1, capability-flag fixture, null identity_guard |
| `finco_parity/__init__.py` | Updated — Phase 1A boundary documented |
| `tests/test_phase1a_parity_schema_normalization.py` | New — 137 unit tests |
| `tests/test_phase1a_parity_manifest.py` | New — manifest tests with factory cross-references |
| `tests/test_phase1a_parity_runner.py` | New — 166 tests including real-value, alignment, determinism, import boundary, immutability |
| `reports/phase1a_characterization_snapshot_foundation/report.md` | Updated — this report |

**No `docs/model_mapping/` files remain in the diff** (restored to base `06ab2fd0`).

---

## 13. Test Results

```
tests/test_phase1a_parity_schema_normalization.py    137 passed
tests/test_phase1a_parity_manifest.py                 39 passed
tests/test_phase1a_parity_runner.py                  166 passed (+ additional sections)
tests/test_security_script_json.py                    57 passed (no regression)
Phase 1A total:                                      342 passed
```

Pre-existing failure (confirmed on `main` before this branch):
`tests/test_auth_lite.py::TestRateLimiting::test_successful_login_clears_failed_attempts`

---

## 14. Production Code Changes

**None.** No changes to:
- Financial formulas
- Tax logic, CFADS logic, debt sizing, waterfall ordering
- TUHO or Oborovo results
- Numerical parity targets or approved golden values
- Project factories or templates
- Workbook V2 behavior or RuntimeResult semantics
- Persistence, routes, or UI
- Identity guards or frozen schedules

`docs/model_mapping/` files restored to base commit — absent from PR diff.

---

## 15. Phase 1B Boundary (Unresolved Decisions)

The following are explicitly out of scope for Phase 1A and deferred to Phase 1B:

1. **Canonical CFADS selection** — which of the six CFADS variants is the authoritative one for comparison purposes
2. **Tax field authority** — whether `tax_keur`, `corporate_tax_cash_keur`, or `cash_tax_current_period_audit_keur` is the primary cash tax for parity
3. **Opening senior debt and drawdown** — reconstruction formula not yet documented or tested; currently marked unavailable
4. **SHL opening balance** — source (project inputs vs. reconstructed) not yet traced; currently marked unavailable
5. **Equity injection series** — not a native WaterfallPeriod attribute; source not identified
6. **Construction period axis** — upstream PeriodEngine calendar not yet captured in snapshot
7. **Financial statements — raw vs. display** — assemble_financial_statements() output captured, but run_project serializer display-rounding not captured
8. **Fixture sizing CFADS** — frozen CSV CFADS rows not yet extracted into snapshot
9. **Tolerance layer** — Phase 1B defines numeric equivalence thresholds for engine comparison
10. **Extracted engine comparison** — Phase 2+ work begins after Phase 1A baseline is approved
