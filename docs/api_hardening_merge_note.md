# API Hardening Merge Note

## What Changed
- `RunRequest.inputs` typed as `ProjectInputsSchema` (not `dict`) — OpenAPI now shows full nested schema
- `/validate` endpoint performs real business-rule validation (no waterfall execution)
- `ValidateResponse` now includes `warnings` field alongside `errors`
- Business rules enforced: CAPEX floor, gearing max, DSCR floor, interest rate bounds, tariff/degradation sanity

## Backward Compatibility
- All existing API requests continue to work unchanged
- `scenario` defaults to `"Base"` when not specified in inputs
- Old `POST /run` with just `project_type` + `scenario` unchanged

## New Validation Behavior
| Condition | Response |
|---|---|
| `total_capex_keur` ≤ ~10,000 kEUR | `valid=false`, error |
| `gearing_pct` > 95% | `valid=false`, error |
| `gearing_pct` > 85% | `valid=true`, warning |
| `interest_rate_pct` < 2% | warning |
| `target_dscr` < 1.0 | `valid=false`, error |
| Tariff < 10 or > 300 EUR/MWh | warning |
| Degradation > 1.5%/yr | warning |

## OpenAPI Improvements
- Swagger UI now shows `ProjectInputsSchema` full tree
- Nested `revenue`, `capex`, `opex`, `debt` objects visible
- Field descriptions shown in Swagger

## Known Limitations
- YAML custom input not yet supported (JSON only)
- `project_name` in JSON parsed but not propagated to `ProjectInfo.name`
- `/validate` is structural + business-rule only — does not guarantee financial feasibility

## Why Safe to Merge
- All 27 API + directionality tests pass
- Full suite: 1107+ tests pass
- No waterfall logic changed
- No depreciation/runtime changes
- Backward compatible with all existing callers