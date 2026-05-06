# Custom Input Schema — Phase Plan

## Recommended Branch Name
`feature/custom-input-schema`

## Schema Scope
Define `ProjectInputsSchema` (Pydantic model) covering:
- `project_type`: str (Solar, Wind, BESS, etc.)
- `capacity_mw`: float
- `tariff_eur_mwh`: float  
- `p50_hours`: float
- `degradation_pct`: float
- `opex_setup`: dict|None
- `capex_setup`: dict|None
- `debt_setup`: dict|None
- `scenario`: str (Base, Downside, Upside)

## API Contract Evolution
- POST /api/v1/run currently accepts `project_type` + `scenario` (hardcoded defaults)
- After: POST /api/v1/run accepts full `ProjectInputsSchema` body
- Backward compatibility: if body is string project_type, fall back to defaults
- Add `POST /api/v1/validate` endpoint for input validation without execution

## CLI Contract Evolution
- Add `--input path/to/project.json` flag
- `python -m app.cli run --project Solar --scenario Base --input custom_project.json`
- Support YAML alias: `--input project.yaml`
- Error on missing required fields with clear message

## Validation Strategy
- Use Pydantic for API request validation
- Reuse same schema for CLI (parse JSON/YAML → Pydantic model)
- Fail fast on invalid inputs with field-level error messages
- Do not call waterfall engine for invalid schema

## Backward Compatibility
- Default project still uses `build_*_defaults()` functions
- CLI without `--input` uses existing behavior (demo flow)
- API without custom body uses existing defaults
- **No breaking changes to existing API contract**

## Migration Risks
1. **Schema drift** — if waterfall engine changes its input format, schema and engine get out of sync
   - Mitigation: keep schema minimal; let engine handle complex internals
2. **Hardcoded demo coupling** — `run_demo_project()` currently always builds defaults internally
   - Mitigation: extract defaults builder; schema just replaces that layer
3. **CLI interface growth** — `--input` adds new surface area
   - Mitigation: design CLI as thin wrapper; core logic stays in run_demo_project()

## Phased Rollout Recommendation
1. Define `ProjectInputsSchema` in `app/schemas.py` — pure data, no business logic
2. Wire schema into API runner (`app/api/project_runner.py`) — validate then call run_demo_project()
3. Add CLI `--input` flag parsing + YAML/JSON reading
4. Add `/api/v1/validate` endpoint
5. (Future) Replace `build_*_defaults()` with schema-driven construction

## Implementation Order
1. `app/schemas.py` — define ProjectInputsSchema
2. `app/api/project_runner.py` — validate with schema, pass to run_demo_project
3. `app/cli/commands.py` — add `--input` flag, parse file, pass as dict
4. `docs/` — update API contract and CLI usage docs
5. Tests — add schema validation tests, CLI file input tests