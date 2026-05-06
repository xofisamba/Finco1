# Release Checkpoints

## v1.2.1-api-hardening (2026-05-07)

### What Changed
- `RunRequest.inputs` typed as `Optional[ProjectInputsSchema]` — full nested schema visible in Swagger
- `/validate` endpoint performs real business-rule validation (no waterfall execution)
- `ValidateResponse` includes `warnings` field alongside `errors`
- Business rules: CAPEX floor, gearing max/min, DSCR floor, interest rate bounds, tariff/degradation sanity
- `scenario` field simplified: plain `str = "Base"` (no `__setattr__` hack, no `model_validator`)

### OpenAPI Improvements
- Nested `revenue`, `capex`, `opex`, `debt` objects visible in Swagger
- Field descriptions shown in Swagger UI

### Tests
- 1107 passed, 1 xfailed
- New: `tests/test_custom_input_directionality.py` (4 directionality tests)
- API tests: `tests/test_api.py` (23 tests)

### Files Changed
- `app/api/router.py` — `/validate` business validation
- `app/api/schemas.py` — `RunRequest.inputs: Optional[ProjectInputsSchema]`
- `app/input_schema.py` — `scenario` simplified, `warnings` added to `ValidateResponse`
- `tests/test_api.py`, `tests/test_custom_input_directionality.py`
- `docs/known_limitations.md`, `docs/model_status.md`

### Backward Compatibility
✅ All existing API requests unchanged — old callers work without modification

---

## v1.2-custom-input-schema (2026-05-05)
- JSON custom input via `POST /run { inputs: {...} }`
- `POST /validate` structural validation
- CLI: `python -m app.cli.main run --project Solar --scenario Base --input custom_solar.json`
