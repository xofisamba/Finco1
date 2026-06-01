# Phase 50C-3 — Runtime Guard Wrapper

## Base SHA
`9925bc2d2af1378fb44da7471eed95e58d29e066` (after PR #374 merge)

## Head SHA
`TODO — fill after commit`

## Objective
Add a thin `check_runtime_allowed()` wrapper around `runtime_guard_for_snapshot` in `app/services/scenario_state_service.py` and wire `main_web.py` to use the wrapper at all call sites, preserving behavior exactly.

This is a **narrow behavior-preserving production refactor**. No route orchestration changes.

---

## What Changed

### `app/services/scenario_state_service.py`
- Added `check_runtime_allowed()` — thin wrapper around `runtime_guard_for_snapshot`
- Added `runtime_guard_for_snapshot` import from `app.persistence.repository`

### `app/services/__init__.py`
- Exports `check_runtime_allowed`

### `main_web.py`
- All 6 call sites of `runtime_guard_for_snapshot(...)` replaced with `check_runtime_allowed(...)`
- Removed `runtime_guard_for_snapshot` from repository import line
- Added `check_runtime_allowed` to `scenario_state_service` import

---

## Service API Summary

```python
def check_runtime_allowed(workspace_state, snapshot) -> tuple[bool, str, str]:
    """
    Thin wrapper around repository.runtime_guard_for_snapshot.
    Returns exactly the same tuple.

    Returns
    -------
    tuple[bool, str, str]
        (allow_run, runtime_origin, guard_message)
    """
```

---

## Affected Routes

| Route | Method | Call Site | Behavior |
|-------|--------|-----------|----------|
| `/run` | POST | Line ~1451 | Blocked if `allow_run=False` ✅ |
| `/compare` | POST | Line ~1541 | Blocked if `allow_run=False` ✅ |
| `/download` | POST | Line ~2041 | Blocked if `allow_run=False` ✅ |
| `/download` | POST | Line ~2056 | `check_runtime_allowed(...)[1]` used for origin check ✅ |
| `/run` | GET (internal) | Line ~3157 | `allow_run, runtime_origin, guard_message` ✅ |

All 6 call sites now use `check_runtime_allowed`, which delegates to `runtime_guard_for_snapshot`. The tuple unpacking `(allow_run, runtime_origin, guard_message)` is unchanged.

---

## Guard Behavior Preservation

| Behavior | Status |
|----------|--------|
| `allow_run=False` blocks `/run` | ✅ |
| `allow_run=False` blocks `/compare` | ✅ |
| `allow_run=False` blocks `POST /download` | ✅ |
| `runtime_origin` values unchanged | ✅ |
| `guard_message` returned to UI | ✅ |
| `allow_run` check uses `[0]` index | ✅ unchanged |
| `runtime_origin` check uses `[1]` index at line 2056 | ✅ |

---

## Dirty/Stale Behavior Preservation

`runtime_guard_for_snapshot` logic is unchanged — it still checks `workspace_state.dirty` and `workspace_state.last_runtime_snapshot_id`. The wrapper does not modify this behavior.

---

## What Did NOT Move

| Item | Status |
|------|--------|
| `/run` orchestration | Not changed ✅ |
| `/compare` orchestration | Not changed ✅ |
| `POST /download` orchestration | Not changed ✅ |
| `_resolve_runtime_snapshot_source` | Still thin wrapper in main_web.py ✅ |
| `resolve_runtime_snapshot` | Still in scenario_state_service ✅ |
| Form parsing | Not changed ✅ |
| Persistence calls | Not changed ✅ |

---

## Tests

| File | Tests | Status |
|------|-------|--------|
| `tests/test_phase50c3_runtime_guard_wrapper.py` | 21 | ✅ 21/21 |
| `tests/test_phase50c2_runtime_snapshot_resolver_extraction.py` | 33 | ✅ 33/33 |
| `tests/test_phase50c1_runtime_snapshot_source_characterization.py` | 28 | ✅ 28/28 |
| `tests/test_phase50b_scenario_state_helper_extraction.py` | 25 | ✅ 25/25 |
| **Total** | **107** | ✅ **107/107** |

---

## Guardrails Preserved

- ✅ No financial formula changes
- ✅ No runtime calculations changed
- ✅ No model outputs changed
- ✅ No route behavior changed
- ✅ No export behavior changed
- ✅ No fixture CSVs changed
- ✅ No schema/migrations
- ✅ No JS financial calculations
- ✅ G20 BLOCKED · R99/R102 NOT APPROVED
- ✅ partial_pay_sweep not promoted · flat/min DSCR not promoted
- ✅ Backend remains source of truth
- ✅ main_web.py has 0 direct `record_export` calls

---

## Recommended Next Phase

**Phase 50C-4 — Extract `_project_workspace_from_request` helper**

This is the next function called at the top of `/run`, `/compare`, and `POST /download` before the runtime guard check. It handles project/workspace resolution from the current request. Extracting it would further thin the route orchestration without changing any behavior.