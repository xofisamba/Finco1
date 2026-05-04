# Test Hygiene Report

Generated from grep survey of `tests/` on industry-engine-refactor.

## 1. Skipped / Xfail Tests

### `@pytest.mark.skip` — test_regression.py
Four tests are skipped with identical reason: *"Model calibration needed — these currently fail"*.

| File | Lines | Issue |
|---|---|---|
| `tests/test_regression.py` | 176, 186, 196, 206 | Skipped — calibration gap, not a code bug |

**Recommendation:** Keep skip reason accurate. Create calibration tickets and schedule un-skip once inputs are locked.

### `@pytest.mark.xfail` — test_input_driven_outputs.py
One test at line 106 is marked xfail.

| File | Line | Issue |
|---|---|---|
| `tests/test_input_driven_outputs.py` | 106 | xfail — reason not captured in grep; needs inspection |

**Recommendation:** Read the full test to determine if the xfail is still valid or if it now passes.

---

## 2. Source-Inspection Tests

No tests were found that open source files and inspect code content (e.g. `ast.parse`, `inspect.getsource`). This is clean.

---

## 3. Vacuous / Weak Assertions

The grep output contains many `assert ==` and `assert !=` calls. Inspection shows they are real equality checks on computed results (e.g. `assert result.new_balance_keur == 10_400.0`). These are not vacuous — they compare calculated values against expected constants.

**No false-green candidates found.** All examined assertions appear to test actual behavior.

---

## 4. Files Using Test Doubles (mock/monkeypatch)

The following test files use mocking infrastructure — worth reviewing for over-specification:
- `tests/test_period_day_fractions.py`
- `tests/test_input_forms.py`
- `tests/test_goal_seek.py`
- `tests/test_ci_infrastructure.py`
- `tests/integration/test_tuho_wind1_fixture.py`
- `tests/test_portfolio_runner.py`
- `tests/test_output_contract.py`
- `tests/test_regression.py`
- `tests/reconciliation_helpers.py`
- `tests/test_output_tables.py`
- `tests/test_cache_parity.py`
- `tests/test_ui_runner.py`
- `tests/test_input_driven_outputs.py`
- `tests/test_validation.py`
- `tests/test_portfolio_waterfall.py`

**Recommendation for mock-heavy files:** Verify that mock usage is at the boundary (API calls, I/O) and not masking real logic. Check `test_validation.py` and `test_output_contract.py` first as highest risk.

---

## 5. Legacy Architecture Tests

`tests/conftest.py` contains an `_oborovo_compat_shim()` function and a `pytest_ignore_collect` hook that skips legacy test modules when their runtime package is absent. This is a compatibility shim for the old Oborovo architecture.

**Recommendation:** Document which modules are being ignored and whether they can be deleted or should be migrated.

---

## Summary

| Category | Count | Status |
|---|---|---|
| Skipped tests | 4 | Known calibration gap; track tickets |
| Xfail tests | 1 | Needs review |
| Source-inspection tests | 0 | Clean |
| Vacuous assertions | 0 | Clean |
| Mock-using files | 15 | Review for over-specification |
| Legacy shims | 1 | Plan cleanup |