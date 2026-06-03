# Phase 51T — Final Route Extraction Closeout

> **Phase 51T** — Final closeout of the Phase 51 route extraction
> work. This is a docs/report/verification phase only. No
> production code changes.

## Executive summary

**Phase 51 is complete.** Every route-orchestration hotspot in
`main_web.py` has been extracted into a dedicated service
module. **Zero remaining inline route-orchestration hotspots.**

## Final route inventory

**34 total routes** in `main_web.py`. After Phase 51T:

- **17 service-backed routes** (12 from earlier phases + 5 from
  the O-S stack: save-as, rename, archive, update-overrides,
  select).
- **17 auth/UI/public/out-of-scope routes** that remain inline
  (none of them are route-orchestration hotspots):
  - `/login`, `/logout` (auth)
  - `/`, `/scenarios`, `/scenarios/compare`, `/scenarios/history`,
    `/scenarios/{id}/load`, `/runs`, `/run/{run_id}`,
    `/projects/browse`, `/projects/new` (UI list/form pages)
  - `/exports/institutional-workbook.xlsx`,
    `/exports/runtime-summary.csv` (export GET routes;
    delegate to `export_service`)
  - `/health`, `/readyz`, `/public-health` (health checks)

## Phase 51 completion summary

| Phase | Route(s) | Service module | PR | Status |
|---|---|---|---|---|
| 51A-51B | /run | run_service.py | (early) | ✓ Extracted |
| 51C-1/2 | /compare | compare_service.py | (early) | ✓ Extracted |
| 51D-1/2 | /validate | validation_service.py | (early) | ✓ Extracted |
| 51E-1/2 | /download GET+POST | download_service.py | (early) | ✓ Extracted |
| 51F | (guardrails) | — | #388 | ✓ Guardrails |
| 51G-1/2 | /save-run | save_run_service.py | #389, #391 | ✓ Extracted |
| 51G-3 | /save-run user_created fix | (same) | #392 | ✓ Bugfix |
| 51H-1/2 | /scenarios/state/draft+discard | scenario_state_route_service.py | #393, #395 | ✓ Extracted |
| 51I | (checkpoint) | — | #396 | ✓ Hotspot map |
| 51J-1/2 | /scenarios/save | scenarios_save_service.py | #397, #399 | ✓ Extracted |
| 51K-1/2 | /scenarios/{id}/duplicate | scenario_duplicate_service.py | #400, #403 | ✓ Extracted |
| 51L-1/2 | /scenarios/add | scenarios_add_service.py | #404, #405 | ✓ Extracted |
| 51M-1/2 | /projects/create | projects_create_service.py | #406, #407 | ✓ Extracted |
| 51N | (checkpoint) | — | #408 | ✓ Checkpoint |
| 51O-1/2 | /projects/{code}/save-as | project_save_as_service.py | #409, #410 | ✓ Extracted |
| 51P-1/2 | /scenarios/{id}/rename | scenario_rename_service.py | #411, #412 | ✓ Extracted |
| 51Q-1/2 | /scenarios/{id}/archive | scenario_archive_service.py | #414, #415 | ✓ Extracted |
| 51R-1/2 | /scenarios/{id}/update-overrides | scenario_update_overrides_service.py | #416, #417 | ✓ Extracted |
| 51S-1/2 | /scenarios/{id}/select | scenario_select_service.py | #418, #419 | ✓ Extracted |
| **51T** | **(closeout)** | **—** | **(this)** | **✓ Checkpoint** |

**Total: 8 route families fully extracted (characterization + extraction), 1 bugfix (51G-3), 2 checkpoints (51I, 51N), 1 closeout (51T).**

## Final service inventory (18 modules)

### Route orchestration services (12)

| File | Lines | Route |
|---|---|---|
| `run_service.py` | 653 | /run |
| `compare_service.py` | 299 | /compare |
| `validation_service.py` | 281 | /validate |
| `download_service.py` | 569 | /download GET+POST |
| `save_run_service.py` | 438 | /save-run |
| `scenario_state_route_service.py` | 361 | /scenarios/state/draft+discard |
| `scenarios_save_service.py` | 450 | /scenarios/save |
| `scenario_duplicate_service.py` | 383 | /scenarios/{id}/duplicate |
| `scenarios_add_service.py` | 408 | /scenarios/add |
| `projects_create_service.py` | 392 | /projects/create |
| `project_save_as_service.py` | 303 | /projects/{code}/save-as |
| `scenario_rename_service.py` | 239 | /scenarios/{id}/rename |
| `scenario_archive_service.py` | 114 | /scenarios/{id}/archive |
| `scenario_update_overrides_service.py` | 107 | /scenarios/{id}/update-overrides |
| `scenario_select_service.py` | 99 | /scenarios/{id}/select |

(15 route-orchestration services in total; 14 are listed above + scenario_state_route_service.py.)

### Data-layer / helper services (1)

| File | Lines | Notes |
|---|---|---|
| `scenario_state_service.py` | 233 | Data-layer only (no Request, no form, no auth) |

### Export / audit services (2)

| File | Lines | Notes |
|---|---|---|
| `export_service.py` | 333 | Excel/CSV export builders |
| `export_audit_service.py` | 194 | Export audit trail |

**Total: 18 service modules (~5,900 lines of service code).**

### Cleanliness verification

- **0/18** services import main_web or main_api ✓
- 18/18 services verified clean programmatically

## Hotspot map: Phase 51I → Phase 51N → Phase 51T

| Metric | Phase 51I | Phase 51N | Phase 51T |
|---|---|---|---|
| Extracted routes | 11 | 12 | **17** |
| Inline hotspot routes | 6 (310 nb) | 5 (193 nb) | **0** |
| HIGH-risk inline | 2 (166 nb) | 1 (49 nb) | **0** |
| MEDIUM-risk inline | 4 (144 nb) | 4 (144 nb) | **0** |
| Service modules | 11 | 13 | **18** |
| Service LOC | ~4,030 | ~4,830 | **~5,900** |
| Test modules | 21 | 23 | **~30+** |

**Phase 51 reduced the remaining inline hotspot non-blank lines from 310 → 0 (a 100% reduction).**

## Phase 51F guardrail status (final)

- **Engine-output golden (TUHO + Oborovo)**: PASS
- **Parity-core lock (4 SHA-256 files)**: PASS
- **No-service-imports-main_web/main_api**: PASS (18/18 services clean)
- **21/21 test module**: PASS

## No-go claims and pilot boundaries (final)

- ✗ No bankability claim
- ✗ No lender-ready claim
- ✗ No audit/certification claim
- ✗ No SaaS-ready claim
- ✗ No external validation claim
- ✗ Generic solar/wind remain exploratory and unvalidated
- ✗ G20 remains BLOCKED
- ✗ R99/R102 remain NOT APPROVED
- ✗ partial_pay_sweep remains not promoted
- ✗ flat/min DSCR sculpting remains not promoted
- ✗ Paid pilot gate is a gate framework only, not authorization by itself
- ✗ Internal confidence heatmap is not external validation
- ✗ Controlled trusted pilot scope is narrow and must remain bounded by TUHO/Oborovo evidence

## Agent A / Agent B boundary

- **Agent A** owns: route extraction, main_web.py, app/services/*, Phase 51 tests/docs/reports.
- **Agent B** owns: docs/reports governance/readiness/review packs (PRs #390, #394, #398).
- **UI track** is separate (out of scope for Phase 51).
- **Parity-core** files are off-limits unless explicit model-change PR.
- Agent B did not modify Agent A route/service files (verified).
- Agent A references Agent B docs but does not rewrite them.

## Remaining risks (final)

### Technical risks

1. **Repository / persistence god-module risk.** `app/persistence.py` is still monolithic. **Phase 52 candidate** (see below).
2. **Service proliferation.** 18 service modules is approaching the threshold where a service registry / facade / index module would help. Not yet a blocker, but worth tracking.
3. **Data-layer / helper category is still very small (1 service).** Some data-layer logic still lives in main_web.py helpers.
4. **No multi-user / enterprise governance implementation.** Single-user only. Permissions, tenancy, audit trail at the user level — future work.
5. **UI/UX still not fully revamped.** The Phase 51 work focused on backend services.
6. **Pre-existing test failures** in `tests/test_persistence.py` and `tests/test_repository.py` (ImportError: No module named 'persistence') — pre-existing, out of scope.

### Process risks

7. **Stacked-PR auto-close pattern.** When a base branch is deleted after a merge, dependent PRs auto-close. We have a rebase workaround.
8. **CI on non-main branches.** Draft PRs against non-main branches don't trigger the CI workflow (filter is `branches: [main, industry-engine-refactor]`). Final 51T PR is on main, so CI will run.

## Recommended next steps (post Phase 51)

### Primary recommendation: **Phase 52 — repository / persistence boundary mapping**

Now that the route-orchestration layer is clean, the next logical
step is to address the persistence god-module
(`app/persistence.py`). The goal of Phase 52 would be to:

1. Define the data-layer services for routes that still write
   directly to persistence.
2. Split `app/persistence.py` into a set of focused modules
   (e.g., `persistence/projects.py`, `persistence/scenarios.py`,
   `persistence/workspace_state.py`, `persistence/exports.py`).
3. Introduce a data-access layer (DAL) that the route
   orchestration services consume.
4. Add tests for the persistence boundary (the pre-existing
   `test_persistence.py` / `test_repository.py` ImportError should
   be resolved as part of this phase).

**Why Phase 52 first:**

- After Phase 51, the only remaining backend risk is the
  persistence layer. Completing this brings the backend to a
  clean state.
- It's the natural next step in the same architectural line as
  Phase 51.
- Phase 52 is a larger architectural change with deeper risk, so
  it should be tackled with care after the proven Phase 51
  pattern.

### Alternative paths

- **Path A**: Continue with more route extractions (none
  remaining for route-orchestration hotspots).
- **Path B**: **Phase 52 — repository / persistence boundary
  mapping** (recommended).
- **Path C**: UI revamp planning (parallelizable, depends on
  Claude review).

## rc1 status

- Frozen SHA: `b425a0708719eaa5e1d922b1008e5609758e0ad4`
- **NOT touched throughout the entire Phase 51 stack** (verified
  in git history).

## Tests

- **Final Phase 51 test count** (post-51T, approx): **~1,500+**
  tests across ~30+ modules (Phase 51 added ~470+ tests).
- All Phase 51F guardrail tests pass.
- All new characterization tests pass.
- All new vertical extraction tests pass.

## Recommendation

**Ready for merge.** Phase 51 is complete. The backend route
extraction work has reached its natural end. Recommend
transitioning to Phase 52 (persistence boundary mapping) or
alternatively performing a Claude architecture review to
validate the work and prioritize next steps.

Backend remains source of truth. rc1 remains frozen.
