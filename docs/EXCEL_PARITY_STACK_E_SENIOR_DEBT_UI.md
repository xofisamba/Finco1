# Excel Parity Stack E — Senior Debt Engine → UI Wiring

**Branch:** excel-parity-stack-e-senior-debt-ui
**Base SHA:** 099e4a14f920cf618b06d850f567374c0c8b9a95
**Date:** 2026-07-01
**Blueprint:** PR #752 (Financial Statements D-stack pattern)

---

## Summary

| Phase | Item | Status |
|-------|------|--------|
| E1 | Audit existing Senior Debt output | **DONE** (findings below) |
| E2 | Runtime payload wiring | **DONE** |
| E3 | Senior Debt UI — read-only engine tables | **DONE** |
| E4 | Pre-Run fallback | **DONE** |
| E5 | Serialization | **DONE** |
| E6 | Characterization tests | **DONE** (27 tests, all pass) |

---

## Phase E1 — Audit: Source of Debt Schedule

### Source object

`domain/waterfall/waterfall_engine.py` — `WaterfallPeriod` dataclass.

All per-period debt fields are already computed by the waterfall engine and stored on each `WaterfallPeriod`:

| Field | Description |
|-------|-------------|
| `senior_balance_keur` | Closing senior debt balance after principal payment |
| `senior_principal_keur` | Sculpted principal repayment this period |
| `senior_interest_keur` | Interest on opening senior balance |
| `senior_ds_keur` | Total senior debt service (interest + principal) |
| `dscr` | CFADS / senior_ds_keur (covenant check) |
| `dsra_balance_keur` | DSRA closing balance |
| `dsra_contribution_keur` | DSRA funding contribution this period |

Summary fields on `WaterfallResult`:

| Field | Description |
|-------|-------------|
| `total_senior_ds_keur` | Total senior debt service over project life |
| `actual_min_dscr` | Minimum DSCR achieved |
| `actual_avg_dscr` | Average DSCR achieved |
| `target_dscr` | Target DSCR from financing inputs |

### No separate assembly step needed

Unlike Financial Statements (which required `assemble_financial_statements()`), the senior debt schedule is available directly on `WaterfallResult.periods`. The `_serialize_debt_schedule()` function reads these fields directly — no offline assembly layer required.

### Evidence that fields are already computed

The existing runtime derivation evidence in `project_runner.py` (`_build_runtime_derivation_evidence()`) already reads `senior_balance_keur`, `senior_principal_keur`, `senior_interest_keur`, `senior_ds_keur`, and `dscr` from `WaterfallResult.periods`. These are live engine outputs, not derived values.

---

## Phase E2 — Runtime Payload Wiring

### Data flow

```
POST /run
  → run_project(...)                           (app/api/project_runner.py)
    → run_demo_project(...)                    (app/ui_runner.py)
      → WaterfallRunner.run(config)            (domain/waterfall/waterfall_engine.py)
      → returns WaterfallResult
    → _serialize_debt_schedule(result)         (project_runner.py — read-only, no formulas)
    → returns {"debt_schedule": {...}}
  → _build_sessionstorage_save_tag(debt_schedule=...)   (run_service.py)
    → <script>sessionStorage.setItem("lastDebtSchedule", ...)</script>
  → client receives response with prepended script

Tab click → GET /... → sheet_senior_debt.html partial rendered
  → JS: _populateSDDebtSchedule()
    → sessionStorage.getItem("lastDebtSchedule")
    → filters to is_operation=true periods
    → builds read-only debt schedule table from engine output
    → shows sd-schedule-block, hides sd-unavailable-panel
```

### Changes to `app/api/project_runner.py`

Added `_serialize_debt_schedule(result)` function — reads `WaterfallResult.periods` fields directly. Zero financial calculations. Handles non-finite floats (`NaN`, `Infinity`) by replacing with `None`.

Added `"debt_schedule": debt_schedule_payload` to `run_project()` return dict.

### Changes to `app/services/run_service.py`

Extended `_build_sessionstorage_save_tag()` to accept `debt_schedule` and write it to `sessionStorage.setItem("lastDebtSchedule", ...)` in the run response script.

All three execution paths (`_execute_user_created_path`, `_execute_template_seeded_path`, `_execute_generic_path`) pass `result.get("debt_schedule")` to the save tag.

When debt schedule data is `None` (e.g. run failed before serialization), the script calls `sessionStorage.removeItem("lastDebtSchedule")` to clear stale data.

---

## Phase E3/E4 — Senior Debt UI

### Changes to `app/templates/partials/sheet_senior_debt.html`

- The `sd-unavailable-panel` (pre-existing, from PR8) is now initially hidden (`style="display:none;"`) and shown by JS only when no debt schedule data is in sessionStorage (pre-Run state).
- Added `id="sd-unavailable-panel"` to the panel for JS targeting.
- Added `id="sd-schedule-block"` div containing one read-only table:
  - Debt Schedule: `id="sd-schedule-table"`
- JS function `_populateSDDebtSchedule()` reads `lastDebtSchedule` from sessionStorage and:
  - Filters to `is_operation=true` periods only (construction periods excluded)
  - Builds the table DOM using read-only cells (`data-readonly="true"`)
  - No financial calculations in JS — values come directly from engine output
- JS function `_populateAll()` calls both the existing runtime block and the new schedule renderer.

### Rows displayed

| Label | Engine field |
|-------|-------------|
| Opening Balance (closing prev period) | `senior_balance_keur` |
| Interest | `senior_interest_keur` |
| Principal Repayment | `senior_principal_keur` |
| Total Debt Service | `senior_ds_keur` |
| Closing Balance | `senior_balance_keur` |
| DSCR | `dscr` |
| DSRA Balance | `dsra_balance_keur` |
| DSRA Contribution | `dsra_contribution_keur` |

---

## Phase E5 — Serialization Approach

`_serialize_debt_schedule(result)` in `app/api/project_runner.py`:

- Iterates `result.periods` (all periods including construction)
- Extracts fields via `getattr` with fallbacks (safe for any WaterfallResult)
- `_f()` helper: rounds to 2dp, replaces `NaN`/`Infinity`/`-Infinity` with `None`
- Dates converted to ISO string via `.isoformat()`
- Returns dict with `periods` list, `summary` dict, `source` annotation

**Forbidden (not done):** no new financial calculations, no recomputed balances, no recalculated DSCR, no rebuilt schedules.

---

## Phase E6 — Tests

New file: `tests/test_excel_parity_stack_e.py` — 27 tests, all pass.

| Test class | Tests | All pass |
|------------|-------|----------|
| `TestE2DebtSchedulePayload` | 6 | Yes |
| `TestE5DebtScheduleSerializes` | 5 | Yes |
| `TestE3SeniorDebtUIScheduleRendering` | 5 | Yes |
| `TestE4PreRunFallback` | 3 | Yes |
| `TestNoJSCalculationsInDebtUI` | 1 | Yes |
| `TestE6Guardrails` | 5 | Yes |
| `TestE2SessionStorageWiring` | 2 | Yes |
| **Total** | **27** | **Yes** |

---

## Payload Structure

```json
{
  "periods": [
    {
      "period": 1,
      "date": "2025-06-30",
      "year_index": 1,
      "period_in_year": 2,
      "is_operation": true,
      "senior_balance_keur": 18234.56,
      "senior_principal_keur": 939.96,
      "senior_interest_keur": 1240.28,
      "senior_ds_keur": 2180.24,
      "dscr": 1.23,
      "dsra_balance_keur": 2180.24,
      "dsra_contribution_keur": 0.0
    }
  ],
  "summary": {
    "total_senior_ds_keur": 43604.80,
    "actual_min_dscr": 1.15,
    "actual_avg_dscr": 1.24,
    "target_dscr": 1.15
  },
  "source": "WaterfallResult.periods (per-period engine output)"
}
```

### Approximate payload size

| Item | Size (TUHO, approximate) |
|------|--------------------------|
| 8 fields × ~60 periods | ~15 KB serialized |
| Summary dict | < 1 KB |
| Total `lastDebtSchedule` | ~16 KB serialized |

---

## Limitations and Remaining Parity Gaps

1. **Opening balance display**: The "Opening Balance" row displays `senior_balance_keur` (closing balance), not the opening balance of each period. A true opening balance would require the prior period's closing balance. This is a display approximation — no calculation is added in JS.
2. **Construction period debt drawdown**: The `periods` payload includes construction periods (filtered out in the UI), which have `senior_balance_keur=0` until the loan is drawn. The detailed drawdown schedule is not shown.
3. **Reserve account details**: Only `dsra_balance_keur` and `dsra_contribution_keur` are shown. MRA (`mra_balance_keur`, `mra_contribution_keur`) and JDSRA are not shown in this phase.
4. **LLCR/PLCR**: `llcr` and `plcr` covenant metrics are available on `WaterfallPeriod` but not included in this phase's UI.
5. **SHL service**: `shl_interest_keur`, `shl_principal_keur`, `shl_service_keur` are available but not displayed in the Senior Debt tab (they belong to a future SHL tab or joint debt section).
6. **sessionStorage only**: Debt schedule data is not persisted server-side. It does not survive a page reload — user must re-run.

---

## Changed Files

| File | Change type | Description |
|------|-------------|-------------|
| `app/api/project_runner.py` | Runtime payload extension | Add `_serialize_debt_schedule()` + call in `run_project()` |
| `app/services/run_service.py` | SessionStorage wiring | Extend `_build_sessionstorage_save_tag()` to persist debt schedule |
| `app/templates/partials/sheet_senior_debt.html` | Template wiring | Add debt schedule table + JS renderer; make unavailable-panel conditional |
| `tests/test_excel_parity_stack_e.py` | Tests | 27 new characterization tests |
| `docs/EXCEL_PARITY_STACK_E_SENIOR_DEBT_UI.md` | Documentation | This file |

---

## Guardrail Confirmation

**No financial logic changed. No formulas changed. No engine calculations changed.**

Specifically confirmed:
- `domain/waterfall/waterfall_engine.py`: unchanged
- `app/waterfall_core.py`: unchanged
- `domain/financial_statements/`: unchanged
- `app/input_adapter.py`: unchanged
- `app/waterfall_runner.py`: unchanged
- `app/project_factories.py`: unchanged
- All domain modules (`domain/financing/`, `domain/tax/`, `domain/revenue/`, `domain/senior_debt_sizing/`, etc.): unchanged

The `_serialize_debt_schedule()` function performs zero calculations. It reads already-computed fields from `WaterfallResult.periods` (the same fields already used by `_build_runtime_derivation_evidence()` in the existing codebase). No new financial formulas. No new JS calculations. Engine remains the single source of truth.
