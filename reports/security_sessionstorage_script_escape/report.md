# Security Fix Report — sessionStorage Script Escape

**Date:** 2026-07-17  
**Branch:** `sec/sessionstorage-script-escape`  
**Category:** Stored XSS / script-element termination  
**Severity:** High

---

## Vulnerability

Any user-controlled string (project name, scenario name) that contained `</script>` was
embedded verbatim into `<script>` text via `json.dumps`.  The HTML parser treats
`</script>` as closing the current script element regardless of JavaScript string syntax,
so a project named `x</script><script>alert(1)</script>` would execute arbitrary JS on
every page load that replays sessionStorage.

Two call sites were affected:

| File | Function | Payload |
|---|---|---|
| `app/workbook/runtime_result.py` | `to_sessionstorage_script()` | All 5 schedule payloads + runtime_summary |
| `app/services/run_service.py` | `_build_sessionstorage_save_tag()` | Same 6 payloads + `applyWorkspaceStateMeta` dict |

---

## Fix

### New utility: `app/utils/script_json.py`

Single-source-of-truth HTML-script-safe JSON serializer.

```
dumps_for_script(value) = re.sub(_UNSAFE_RE, _replace, json.dumps(value))
```

Escapes 5 characters that allow script-element breakout:

| Char | Escape | Reason |
|---|---|---|
| `<` | `<` | Prevents `</script>` from forming |
| `>` | `>` | Belt-and-suspenders |
| `&` | `&` | Prevents HTML entity injection |
| U+2028 | ` ` | JS line terminator |
| U+2029 | ` ` | JS paragraph terminator |

Output is valid JSON; `json.loads(dumps_for_script(v)) == v` for all JSON-safe values.

### `app/workbook/runtime_result.py`

Added `_dumps_script_safe()` (thaws `MappingProxyType` then calls `dumps_for_script`).
`to_sessionstorage_script()` now uses `json.dumps(_dumps_script_safe(payload))` everywhere
instead of `json.dumps(_dumps(payload))`.

### `app/services/run_service.py`

`_build_sessionstorage_save_tag()` uses `json.dumps(_dumps_for_script(payload))` for all
6 schedule/summary payloads. The `applyWorkspaceStateMeta` call uses
`_dumps_for_script({...})` directly (not double-serialized, matching original call shape).

---

## Tests

### New: `tests/test_security_script_json.py` — 57 tests

- **Section A** — core escaping contract (10 tests)
- **Section B** — round-trip for 20+ value types (parametrized)
- **Section C** — output parseable by `json.loads`
- **Section D** — `json_options` pass-through
- **Section E** — no double-encoding (HTML entities must not appear)
- **Section F** — emitter tests via `RuntimeResult.to_sessionstorage_script()`
- **Section G** — emitter tests via `_build_sessionstorage_save_tag()`

### Modified: `tests/test_workbook_v2_output_surface_browser.py`

Added `test_xss_marker_undefined_after_hydration`: injects XSS payload into the DB,
loads the V2 workbook page, and asserts:
- `window.__fincoXssMarker` is `None` (payload did not execute)
- Page source does not contain literal attacker string
- sessionStorage round-trip recovers original string faithfully

### Results

```
tests/test_security_script_json.py          57 passed
tests/test_workbook_v2_output_surface_browser.py  29 passed (28 existing + 1 new)
Full regression (213 tests)                213 passed, 6 pre-existing failures
                                           (test_phase_p2fix1_default_route_rewiring.py,
                                            confirmed on main before this branch)
```

---

## Scope Constraints Honoured

- No changes to `financial_engine/`
- No changes to financial formulas, waterfall orchestration, or ProjectModelResult
- No changes to RuntimeResult payload meaning or field names
- No persistence schema changes
- No parity targets, frozen fixtures, or golden values touched
- No roadmap phases started (Scenarios, Export, multi-lender, etc.)
