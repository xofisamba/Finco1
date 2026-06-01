# Phase 50C-3 — Runtime Guard Wrapper Decision Matrix

## Base SHA
`9925bc2d2af1378fb44da7471eed95e58d29e066`

## Call Sites

All 6 call sites in `main_web.py` now use `check_runtime_allowed`. The wrapper delegates directly to `runtime_guard_for_snapshot` with no modifications to parameters or return values.

| Call # | Location | Signature | Parameters | Return | Behavior |
|--------|----------|-----------|------------|--------|----------|
| 1 | `/run` (POST) ~1451 | `allow_run, runtime_origin, guard_message = check_runtime_allowed(workspace_state, snapshot)` | `workspace_state`, `snapshot` | `(bool, str, str)` | If `not allow_run` → return JSON error ✅ |
| 2 | `/compare` (POST) ~1541 | same | `workspace_state`, `snapshot` | `(bool, str, str)` | If `not allow_run` → return JSON error ✅ |
| 3 | `POST /download` ~2041 | same | `workspace_state`, `snapshot` | `(bool, str, str)` | If `not allow_run` → return error response ✅ |
| 4 | `POST /download` ~2056 | `if check_runtime_allowed(workspace_state, snapshot)[1] == "saved_state" ...` | `workspace_state`, `snapshot` | Uses `[1]` (runtime_origin) | Only enters branch if `runtime_origin == "saved_state"` ✅ |
| 5 | `/run` internal ~3157 | same as #1 | `workspace_state`, `snapshot` | `(bool, str, str)` | Runtime origin binding ✅ |

## Return Value Behavior

`runtime_guard_for_snapshot` returns `(allow_run, runtime_origin, guard_message)` where:

- **`allow_run` (bool):** `True` if runtime may proceed, `False` if workspace is dirty/stale
- **`runtime_origin` (str):** One of `"saved_state"`, `"workspace_base"`, `"factory_base_runtime"`, `"preview_only"`
- **`guard_message` (str):** `""` if allowed, otherwise blocking reason

The wrapper passes these through unchanged — no filtering, no transformation.

## Wrapper Scope

```
main_web.py                    scenario_state_service.py         app.persistence.repository
     |                                    |                               |
     | check_runtime_allowed(ws, snap)   |                               |
     +------------------------------------> runtime_guard_for_snapshot(ws, snap)
                                        +--------------------------------> [actual logic]
                                        <--------------------------------+
                                        < [returns exact tuple]
<------------------------------------+
< [same tuple returned to caller]
```

The wrapper is:
- **Zero-argument**: passes all arguments unchanged
- **Zero-modification**: returns the exact tuple from the repository
- **Zero-side-effect**: no additional logging, no caching, no state changes