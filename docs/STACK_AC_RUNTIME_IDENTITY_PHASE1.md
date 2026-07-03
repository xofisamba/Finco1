# Stack AC — Runtime Identity Elimination Phase 1

**Branch**: `stack-ac-runtime-identity-phase1`  
**Depends on**: Stack AB (merged PR #778)  
**Status**: Implementation complete; PR open, do not merge

---

## Objective

Eliminate the highest-priority identity-dispatch finding from Stack AB:  
the frozen senior DS fixture was loaded by matching `inputs.info.code` against
hardcoded string literals (`'TUHO-WIND-1'`, `'OBR-001'`).  
After AC, fixture loading is controlled by `FinancingParams.frozen_senior_ds_fixture_path`
— a capability flag set by the project factory, not derived from the project name or code.

**Observable result**: renaming TUHO-WIND-1 to any other name/code now produces
identical `actual_avg_dscr`, `equity_irr`, and `total_distribution_keur`.

---

## AB Finding (Before Stack AC)

`waterfall_core.py` lines 425–428 (TUHO fixture) and 514–517 (Oborovo fixture):

```python
# Before AC — identity dispatch on project code
use_fixture = (
    use_frozen_excel_senior_debt_schedule
    and getattr(inputs.info, 'code', '') == 'TUHO-WIND-1'  # ← identity dispatch
)
use_oborovo_fixture = (
    use_frozen_excel_senior_debt_schedule
    and getattr(inputs.info, 'code', '') == 'OBR-001'       # ← identity dispatch
)
```

**Concrete impact**: renaming TUHO from `TUHO-WIND-1` to `WPA-001` changed
`actual_avg_dscr` from **1.3786** (fixture-backed) to **1.5004** (ebitda-derived).
The `_frozen_senior_ds_wired` audit flag was `False` on the renamed project.

---

## Solution

### 1. New field: `FinancingParams.frozen_senior_ds_fixture_path`

Added to `domain/inputs.py`:

```python
# Stack AC: fixture path for frozen senior DS schedule.
# When set, the frozen DS loader reads from this path (relative to repo root)
# instead of dispatching on project code. None = no fixture.
frozen_senior_ds_fixture_path: str | None = None
```

Default is `None` — generic projects get no fixture without explicit configuration.

### 2. Factory wiring: TUHO and Oborovo

`app/project_factories.py` now sets the path in `FinancingParams`:

```python
# TUHO
frozen_senior_ds_fixture_path="reports/phase7_tuho_senior_debt_sizing_extraction.csv"

# Oborovo  
frozen_senior_ds_fixture_path="reports/phase23q_oborovo_senior_debt_sizing_extraction.csv"
```

### 3. Dispatch change in `waterfall_core.py`

```python
# After AC — capability-driven dispatch on configured path
_configured_fixture_path = getattr(inputs.financing, 'frozen_senior_ds_fixture_path', None)

use_fixture = (
    use_frozen_excel_senior_debt_schedule
    and _configured_fixture_path is not None
    and 'phase7_tuho' in _configured_fixture_path
)

use_oborovo_fixture = (
    use_frozen_excel_senior_debt_schedule
    and _configured_fixture_path is not None
    and 'phase23q_oborovo' in _configured_fixture_path
)
```

The CSV path is also read from `_configured_fixture_path` rather than hardcoded:

```python
csv_path = Path(__file__).resolve().parents[1] / _configured_fixture_path
```

---

## Files Changed

| File | Change |
|------|--------|
| `domain/inputs.py` | Added `frozen_senior_ds_fixture_path: str \| None = None` to `FinancingParams` |
| `app/project_factories.py` | Set `frozen_senior_ds_fixture_path` in TUHO and Oborovo `FinancingParams` |
| `app/waterfall_core.py` | Replaced code-based dispatch with path-based dispatch in Phase 23D/23Q blocks |
| `tests/test_stack_ab_engine_architecture_cleanup.py` | Converted xfail to passing test; updated "documented finding" test to document the fix |
| `tests/test_stack_ac_runtime_identity_phase1.py` | New — 21 tests across AC1–AC4 |
| `docs/STACK_AC_RUNTIME_IDENTITY_PHASE1.md` | This file |

---

## Test Results

### AB tests (22 passing, 0 xfail)

The previously xfailed test `test_tuho_full_output_identical_after_rename_xfail` was
converted to `test_tuho_full_output_identical_after_rename` and now passes.

The `test_frozen_ds_identity_dispatch_is_documented_ab_finding` test was renamed to
`test_frozen_ds_fixture_path_is_config_driven` and now asserts the fix instead of the bug.

### AC tests (21 passing)

| Class | Tests | Covers |
|-------|-------|--------|
| `TestFrozenDSFixturePathCapabilityDriven` | 5 | Fixture path field, factory wiring, default None |
| `TestRenameInvariance` | 5 | Rename → identical DSCR/IRR/distributions for TUHO and Oborovo |
| `TestGoldenRegression` | 7 | Parity targets unchanged vs Stack AB baseline |
| `TestArchitectureInvariants` | 4 | Field presence, source code dispatch pattern |

### Golden regression (unchanged)

| KPI | Target | Tolerance |
|-----|--------|-----------|
| TUHO equity IRR | 11.32% | ±0.05% |
| TUHO actual_avg_dscr | 1.3786 | ±0.001 |
| TUHO total_tax_keur | 45,835 | ±500 |
| TUHO total_distribution_keur | 165,471 | ±200 |
| Oborovo equity IRR | 10.54% | ±0.05% |
| Oborovo actual_avg_dscr | 1.179 | ±0.005 |
| Oborovo total_tax_keur | 8,874 | ±100 |

---

## Scope

### In scope
- Frozen senior DS fixture path: moved from hardcoded code dispatch to config field
- Factory wiring for TUHO and Oborovo
- Test coverage: rename invariance, golden regression, architecture invariants

### Explicitly out of scope (unchanged)
- Tax bridge mathematics and bridge constants (`TUHO_BOOK_TOTAL`, `TUHO_TAX_TOTAL`)
- Core identity guards at lines 115/117/119 (protect hardcoded bridge constants; tracked for Stack AD)
- `is_tuho` / `is_oborovo` flags at lines 776/1274 (DA wiring; tracked for Stack AE/AF)
- Depreciation, LCF, ATAD, SHL, debt sizing, IRR, UI, exports

---

## Remaining Identity Dispatch (Post-AC)

### Core guards (intentional — protect hardcoded constants)

| Line | Guard | Protected value | Fix in |
|------|-------|-----------------|--------|
| 115 | `code != "TUHO-WIND-1"` for tax bridge | `TUHO_BOOK_TOTAL=72,993.7` hardcoded | Stack AD |
| 117 | `code != "TUHO-WIND-1"` for SHL gross accrued | TUHO-specific R27 fixture | Stack AD |
| 119 | `code != "TUHO-WIND-1"` for SHL repayment alignment | TUHO-specific timing | Stack AD |
| 140 | `code != "TUHO-WIND-1"` (bridge inner guard) | same as 115 | Stack AD |
| 159 | `code != "TUHO-WIND-1"` (SHL inner guard) | same as 117 | Stack AD |

### DA wiring (lower priority)

| Line | Pattern | Fix in |
|------|---------|--------|
| 776 | `is_tuho = (code == "TUHO-WIND-1")` | Stack AE |
| 1274 | `is_tuho = (code == "TUHO-WIND-1")` | Stack AE |

---

## Architecture Principle Enforced

> **Capability flags live in config. Project code/name is display metadata only.**

Before AC: 3 identity dispatch points in frozen DS (TUHO path, Oborovo path, two `code ==` guards).  
After AC: 0 identity dispatch points in frozen DS. The fixture path in `FinancingParams` is the
single capability gate. The project code is no longer consulted during financial computation
for the frozen DS path.
