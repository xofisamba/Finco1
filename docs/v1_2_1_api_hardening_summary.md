# v1.2.1 API Hardening — Merge Summary

## 1. What Changed

| Component | Change |
|---|---|
| OpenAPI schema | `RunRequest.inputs` typed as `ProjectInputsSchema` (not `dict`) — Swagger shows full nested tree |
| `/validate` | Now runs real business-rule validation — CAPEX floor, gearing, DSCR, interest rate, tariff/degradation sanity |
| `ValidateResponse` | New `warnings` field — distinguishes errors from warnings |
| `scenario` field | Simplified — `str = "Base"`, no `__setattr__` hack, no `model_validator` |
| API tests | 23 tests covering valid/invalid inputs, business rule enforcement |

## 2. Why Merge Is Safe

- **No waterfall changes** — only schema, validation, and API routing
- **No runtime changes** — no depreciation, no HTMX, no BESS
- **Backward compatible** — all existing API callers work unchanged
- **Branch purity verified** — zero depreciation_engine, waterfall_core, or waterfall_runner changes
- **Test suite clean** — 1107 passed, 1 xfailed (pre-existing)

## 3. Backward Compatibility Status

✅ **Fully compatible** — old requests like `POST /run { "project_type": "Solar", "scenario": "Base" }` work without any field changes.

The `inputs` field is optional. When absent, factory defaults are used exactly as before.

## 4. Known Limitations Still Remaining

- YAML custom input not yet supported (JSON only)
- `project_name` in JSON parsed but not propagated to `ProjectInfo.name`
- `/validate` is structural + business-rule only — does not guarantee financial feasibility
- No UI change (STREAMLIT_HTML still serves old layout)

## 5. Why HTMX Can Now Safely Begin After Depreciation Review

The API hardening work **stabilizes the contract** that the HTMX UI will consume:

1. **Typed schema** — HTMX partials can rely on `ProjectInputsSchema` structure
2. **Honest `/validate`** — HTMX form handlers can call `/validate` before waterfall execution
3. **No more schema churn** — `scenario` field is locked, `ProjectInputsSchema` is stable
4. **Separate depreciation branch** — once depreciation review is done and merged, HTMX can safely build on a stable foundation

**Sequence:** API hardening (NOW) → Depreciation review → Depreciation merge → HTMX phase

Do NOT start HTMX until depreciation branch is reviewed and merged, to avoid schema conflicts.
