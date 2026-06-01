# Phase 49A — God Module Mapping / Safe Extraction Plan

**Repo:** xofisamba/Finco1
**Base branch:** main
**Base SHA:** 926317cb4b61015bf8e8e2693161cdcc22d46b0a
**Branch:** phase49a-god-module-mapping-safe-extraction-plan

## Objective

Map the god-module / route-layer complexity (especially `main_web.py`) and produce a **safe extraction plan** for moving logic out of large modules **without changing runtime behavior**. This is an architecture-mapping and test-coverage-planning phase only. No production refactor, no formula changes, no runtime behavior changes, no gate promotions.

## No-Behavior-Change Statement

Phase 49A changes **documentation, reports, and tests only**. It makes **no financial formula changes, no runtime calculation changes, no model output changes, no data-path changes, no project-factory changes, no fixture-CSV changes, and no JavaScript changes.** TUHO/Oborovo validation behavior and generic-project validation status are unchanged. The runtime engine (`app/waterfall_core.py`) is untouched.

## Module Size / Responsibility Summary

| Module | Lines | Role | God-module? |
|---|---|---|---|
| `main_web.py` | 3,367 | FastAPI route orchestration hotspot (34 routes, 45 module functions, 43 private helpers, 24 imports) | **Yes — primary** |
| `app/persistence/repository.py` | 2,042 | persistence/repository operations | Yes — secondary (out of scope this phase) |
| `app/input_forms.py` | 396 | form rendering | borderline |
| `app/cache.py` | 229 | caching | no |
| `app/ui/components.py` | 106 | UI component helpers | no |

`main_web.py` is the clear primary god-module and route/orchestration hotspot: it mixes HTTP routing, HTMX/template rendering, form snapshot collection, scenario state transitions, model-run orchestration, export/download orchestration, validation/audit context building, persistence calls, auth/session concerns, and operational endpoints in one 3,367-line module.

## main_web.py Route Inventory (34 routes)

**Auth/session:** `GET /login`, `POST /login`, `POST /logout`
**Operational:** `GET /public-health`, `GET /readyz`, `GET /health`
**Core workspace:** `GET /`, `POST /validate`, `POST /run`, `POST /compare`
**Export/download:** `POST /download`, `GET /download`, `GET /exports/runtime-summary.csv`, `GET /exports/institutional-workbook.xlsx`
**Projects:** `GET /projects/new`, `GET /projects/browse`, `POST /projects/create`, `POST /projects/{project_code}/save-as`
**Scenarios:** `GET /scenarios`, `POST /scenarios/state/draft`, `POST /scenarios/state/discard`, `GET /scenarios/history`, `GET /scenarios/compare`, `POST /scenarios/save`, `GET /scenarios/{id}/load`, `POST /scenarios/{id}/duplicate`, `POST /scenarios/add`, `POST /scenarios/{id}/select`, `POST /scenarios/{id}/update-overrides`, `POST /scenarios/{id}/rename`, `POST /scenarios/{id}/archive`
**Runs:** `GET /runs`, `POST /save-run`, `GET /run/{run_id}`

## Responsibilities by Category

| Category | Where it lives today | Extractable to |
|---|---|---|
| Route HTTP handling | main_web route fns | stays (thin routers) |
| HTMX response/template rendering | inline in routes + context helpers | template context builder |
| Form snapshot collection | `_collect_form_snapshot` + ~14 scenario helpers | input-snapshot collector |
| Scenario draft/save/load/discard | scenario routes + helpers | scenario state service |
| Model run orchestration | `POST /run`, `_resolve_runtime_snapshot_source`, guard helpers | run orchestration service |
| Export/download orchestration | `POST/GET /download`, `/exports/*`, `_build_export_lineage_ui_context` | **export_service (first)** |
| Validation/audit context building | `POST /validate` + ~10 context helpers | validation/audit context builder |
| Persistence/repository calls | ~5 persistence helpers + inline | already partly in repository.py |
| Auth/session | login/logout + `get_current_user` | auth/session helpers |
| Operational endpoints | health/readyz | ops helpers |

## Top God-Module Risks

1. **Change-amplification:** any route edit risks unrelated behavior because helpers are shared and stateful context-building is inline.
2. **Test surface concentration:** a single module backs 34 routes; hard to test orchestration in isolation.
3. **Onboarding cost:** 3,367 lines mixing 10 responsibility categories.
4. **Hidden coupling:** export, run, and scenario orchestration share helper functions and form-snapshot shapes.
5. **Behavior-preservation risk during refactor:** because formulas/runtime must not change, extractions must be pure call-site moves with response-parity tests.

## Safe Extraction Order

1. **export_service** (first — lowest risk; export is leaf-like, already partly packaged in `app/export/*`, and Phases 47-48 give existing tests to anchor parity).
2. template context builder (read-mostly, high reuse).
3. validation/audit context builder.
4. input-snapshot collector.
5. scenario state service.
6. run orchestration service (highest risk — touches runtime; do last, behind strong parity tests).
7. auth/session + ops helpers (small, can be opportunistic).

## Test Coverage Required Before Each Extraction

- **Before export_service:** response status, filename, content-type, and Export_Metadata/Workbook_Index sheet presence (Phases 47-48) for `POST/GET /download` and `/exports/*`.
- **Before context builders:** golden HTML/context snapshots for `GET /` and `POST /validate`.
- **Before scenario service:** state-transition tests (draft→save→load→discard) asserting persistence rows and response.
- **Before run orchestration:** full run-output parity (DSCR 1.451/1.15, distribution lock-up) before and after — MD5/value-pinned.

## Recommended Next Phase

**Phase 49B — Extract `export_service`** from `main_web.py` into `app/services/export_service.py`, keeping route signatures and responses unchanged, workbook writers unchanged except call sites, and preserving Phase 47-48 export metadata/index behavior, with the response/metadata tests above added first.

## Guardrails

G20 remains BLOCKED. R99/R102 remain NOT APPROVED. `partial_pay_sweep` remains not promoted. flat/min DSCR sculpting remains not promoted. Backend remains source of truth. No JS financial calculations. No schema migrations. Generic solar/wind remains unvalidated. No bank/lender/external-audit/certification/SaaS/enterprise claims. Validated scope remains TUHO/Oborovo frozen-template paths only.
