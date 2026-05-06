# Main Post-Merge Status Report

**Date:** 2026-05-06
**Branch:** `main` (post-merge)

---

## 1. Merged Branches & Commits

| Branch | Last Commit | Merge Strategy |
|--------|-------------|----------------|
| `post-rc1-structure-roadmap` | `721b1dc` — feat(regression): lock Advanced OPEX+Scenario scaling tests, add merge_readiness.md, validation confidence note | Fast-forward to `main` |
| `feature/cli-runner` | `d0f9b56` — revert: accidentally committed regression tests to CLI branch — belongs to post-rc1 | ort (recursive) merge to `main` |
| `feature/api-wrapper` | `7a47e4c` — fix(api): propagate demo.messages/integration_status/integration_note, add integration_note schema field, 16 tests | ort (recursive) merge to `main` |

### Commit Log (merge order)

```
b425a07 → 721b1dc  (post-rc1-structure-roadmap fast-forward)
721b1dc + b425a07 → 721b1dc  (feature/cli-runner ort merge)
[+ d0f9b56]
721b1dc + d0f9b56 → [merge commit]  (feature/api-wrapper ort merge)
[+ 7a47e4c]
```

---

## 2. Final Architecture

**Stack:** Streamlit (primary demo UI) + CLI runner + FastAPI wrapper

```
┌─────────────────────────────────────────────────────────────────┐
│                      FincoGPT Model                            │
│  run_demo_project() / run_project()                            │
│  ├── domain/factories.py  (demo project inputs)               │
│  ├── app/scenario_manager.py  (Base/Downside/Upside)          │
│  ├── app/capex_engine.py  (CapexLineItem schedule)           │
│  ├── app/opex_engine.py  (Advanced OPEX line-item engine)    │
│  ├── app/waterfall_core.py  (DSCR sculpting, XIRR)           │
│  └── app/waterfall_runner.py  (orchestration)                │
└─────────────────────────────────────────────────────────────────┘
          │                  │                    │
          ▼                  ▼                    ▼
   Streamlit App       CLI Runner          FastAPI /api/v1/run
   (app/ui/)          (app/cli/)          (main_api.py)
```

### New Modules Added

| Module | Purpose |
|--------|---------|
| `app/scenario_manager.py` | `ScenarioManager` + `Scenario` dataclass; active engine for all Solar/Wind scenarios |
| `app/capex_engine.py` | `CapexLineItem` + `generate_capex_schedule()` for per-period CAPEX draw matrix |
| `app/opex_engine.py` | Advanced OPEX with line-item granularity, inflation, scenario scaling |
| `app/cli/` | Click-based CLI: `run --project Solar --scenario Base --json FILE` and `--output FILE.xlsx` |
| `app/api/` | FastAPI router + `run_project()` wrapper + Pydantic schemas |

---

## 3. Test Results

```
pytest tests/ -x -q
1057 passed, 1 xfailed, 131 warnings in 23.74s
```

All tests pass post-merge. No regressions introduced by any merge.

### Branch Pre-Merge Test Status

| Branch | Key Test File | Result |
|--------|--------------|--------|
| `post-rc1-structure-roadmap` | `tests/test_opex_scenario_scaling.py` | 8 passed |
| `feature/cli-runner` | `tests/test_cli.py` | 5 passed |
| `feature/api-wrapper` | `tests/test_api.py` | 16 passed |

---

## 4. Smoke Tests

### CLI Smoke
```
python3 -m app.cli run --project Solar --scenario Base --json /tmp/out.json
→ Success: IRR=10.40%, minDSCR=1.442x

python3 -m app.cli run --project Wind --scenario Downside --output /tmp/out.xlsx
→ Success: IRR=13.34%, minDSCR=1.906x
```

### API Smoke (direct `run_project()` call)
```
run_project('Solar', 'Base')
→ project_irr: 0.1040
→ integration_status: 'full'
→ integration_note: None  (set to None when fully integrated — non-null indicates partial integration)
→ messages: []
→ messages is list: True
→ Downside IRR (0.0812) < Base IRR (0.1040): True ✓
```

---

## 5. Supported Flows

| Interface | Projects | Scenarios | Output |
|-----------|----------|-----------|--------|
| **Streamlit UI** | Solar, Wind, BESS, Solar+BESS, Wind+BESS, Portfolio | Base/Downside/Upside (Solar+Wind); Base only (BESS/Hybrid/Portfolio) | In-app KPIs, tables, charts, Excel export |
| **CLI** | Solar, Wind, BESS, Solar+BESS, Wind+BESS, Portfolio | Base/Downside/Upside | JSON file, XLSX file |
| **FastAPI** | Solar, Wind | Base/Downside/Upside | JSON HTTP response |

### CLI Usage
```bash
# JSON output
python3 -m app.cli run --project Solar --scenario Base --json /tmp/out.json

# Excel output
python3 -m app.cli run --project Wind --scenario Downside --output /tmp/out.xlsx
```

### API Usage
```bash
curl -X POST http://localhost:8000/api/v1/run \
  -H "Content-Type: application/json" \
  -d '{"project_type": "Solar", "scenario": "Base"}'
```

---

## 6. Known Limitations

### High Priority
| Issue | Description |
|-------|-------------|
| **CAPEX depreciation gap** | `CapexLineItem` matrix overrides total CAPEX in waterfall but depreciation still uses legacy `CapexItem` asset-class breakdown. Full per-asset-class depreciation from CapexLineItems not yet implemented. |

### Medium Priority
| Issue | Description |
|-------|-------------|
| **BESS partial** | BESS revenue-only warnings shown (`W_ZERO_GENERATION`, `W_DSCR_BELOW_TARGET`). Full BESS cost structure and hybrid optimisation pending. Scenario selector blocked for BESS types (always Base). |
| **Portfolio experimental** | Portfolio project IRR calculated but not independently validated. Sponsor IRR shows "⏳ Placeholder". Do not use for investment decisions. |

### Lower Priority
| Issue | Description |
|-------|-------------|
| OPEX does not respond to DSCR sculpting | Fixed OPEX — does not adjust when debt sculpted |
| No holding company layer | Distributions go SPV → equity directly; no intermediate hold-co |
| No Excel formula export | Values only; no formulas written to export workbook |
| `integration_note` is `null` for fully-integrated flows | cosmetic: schema has field, runtime returns `null` when full integration achieved |

### rc1 Frozen
`rc1` branch is frozen — no further commits to rc1. All active development on `main`.

---

## 7. Next Roadmap

### Phase: Custom Input Schema
- [x] Define `ProjectInputsSchema` Pydantic model for API request validation
- [x] Add CLI `--input` flag accepting a JSON project inputs file
- [x] Wire custom inputs through `run_demo_project()` / `run_project()`
- [ ] Deprecate hardcoded factory project types in favor of custom input flow

### v1.2-custom-input-foundation (merged)

**Merged:** `feature/custom-input-schema` → `main` (fast-forward, 2026-05-06)

**Features:**
- `ProjectInputsSchema` (Pydantic DTO) — minimal input validation for Solar/Wind
- API POST `/run` accepts optional `inputs` dict
- API POST `/validate` endpoint
- CLI `--input JSON` flag
- `examples/custom_solar.json`, `examples/custom_wind.json`

**Known limitations:**
- YAML input not yet supported
- `project_name` not propagated to project info
- CAPEX depreciation gap remains (see `docs/capex_depreciation_phase_plan.md`)
- BESS/Portfolio custom inputs not supported via API
- CAPEX total must exceed ~10,000 kEUR (fixed other capex)

**Status:** frozen for short stabilization

### Phase: HTMX Frontend (post-custom-inputs)
- [ ] Replace Streamlit with lightweight HTMX + server-side rendering
- [ ] Keep `waterfall_core`, `capex_engine`, `opex_engine`, `scenario_manager` as pure business logic
- [ ] Stateless request/response — no session state server-side

### Unscheduled
- BESS full cost + hybrid optimisation
- Sponsor IRR portfolio aggregation
- Holding company layer
- Multi-currency / FX conversion
- Debt-sculpting-aware OPEX

---

## Freeze Status
**main:** short stabilization freeze (bugfix/docs/smoke-test fixes only)
**forbidden:** CAPEX depreciation, HTMX, BESS, Portfolio, Sponsor IRR, FX

---

## 8. Rollback Guidance

If issues are discovered post-merge:

### To roll back to pre-merge main state
```bash
cd /root/.openclaw/workspace/finco1_new
git checkout main
git reset --hard b425a07   # pre-merge commit hash
git push --force origin main
```

### To remove individual merged branches after rollback
```bash
git push origin --delete post-rc1-structure-roadmap
git push origin --delete feature/cli-runner
git push origin --delete feature/api-wrapper
```

### Branch protection note
`rc1` is frozen and should not be force-reset. If rc1 needs a hotfix, create a `rc1-hotfix` branch from rc1, apply the fix, then merge back to main.

---

## 9. Documentation Updated

| File | Change |
|------|--------|
| `docs/api_contract.md` | Added `inputs` dict, `/validate` endpoint, project_type mismatch guard |
| `docs/cli_usage.md` | Added `--input FILE` flag, custom input examples |
| `docs/known_limitations.md` | Added YAML/JSON note, project_name propagation gap |
| `docs/main_post_merge_status.md` | Added v1.2 section + Freeze Status |
| `docs/release_checkpoint.md` | v1.2 checkpoint |
| `docs/capex_depreciation_phase_plan.md` | New — CAPEX depreciation design & phase plan |

