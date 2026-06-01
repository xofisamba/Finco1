# Phase 49A — Extraction Dependency Matrix

**Base SHA:** 926317cb4b61015bf8e8e2693161cdcc22d46b0a

Each row is a candidate extraction out of `main_web.py`. No extraction is performed in Phase 49A; this is the plan and risk assessment only.

| Candidate extraction | Current source (module/functions) | Proposed target | Dependencies | Side effects | Existing tests | Missing tests | Risk | Recommended phase | Safe? |
|---|---|---|---|---|---|---|---|---|---|
| **Export/download service** | `main_web.py`: `POST /download`, `GET /download`, `GET /exports/runtime-summary.csv`, `GET /exports/institutional-workbook.xlsx`, `_build_export_lineage_ui_context`; uses `app/excel_export.py`, `app/export/*` | `app/services/export_service.py` | build_projectinputs, snapshot collector, `app/export/*` writers, auth | Excel bytes, file download, response headers | Phase 47/48 export tests (metadata/index) | response status/filename/content-type unit tests around the service | **Low** | **49B (first)** | **Yes** |
| Template context builder | `main_web.py`: `_project_record_to_context`, `_build_export_lineage_ui_context`, `_normalize_template_source`, `_project_identity_from_template_source`, ~10 context helpers | `app/services/context_builder.py` | project record, workspace state, lineage | none (read-mostly) | none direct | golden context snapshots for `GET /`, `POST /validate` | Low-Med | 49C | Conditional |
| Validation/audit context builder | `main_web.py`: `POST /validate` body + audit/validation helpers | `app/services/validation_context.py` | runtime result, taxonomy, audit tab data | none (read-mostly) | partial (audit-tab phase tests) | validation-context unit tests | Med | 49D | Conditional |
| Input form snapshot collector | `main_web.py`: `_collect_form_snapshot`, `_default_workspace_snapshot`, `_project_baseline_snapshot` | `app/services/snapshot_collector.py` | form shape, schema builder | snapshot dict shape (shared by run+export) | indirect via run/export | snapshot-shape unit tests (shared contract) | Med | 49E | Conditional |
| Scenario state service | `main_web.py`: `/scenarios/*` routes + `_governance_snapshot` + draft/save/load/discard helpers | `app/services/scenario_service.py` | repository, snapshot collector, workspace state | DB writes, scenario rows | scenario versioning/history phase tests | state-transition tests (draft→save→load→discard) asserting rows | Med-High | 49F | Conditional |
| Run orchestration service | `main_web.py`: `POST /run`, `_resolve_runtime_snapshot_source`, `runtime_guard_for_snapshot` call sites, `POST /compare` | `app/services/run_service.py` | waterfall_core, build_projectinputs(_from_snapshot), guards, fixtures | **touches runtime path** (call sites only) | run/parity phase tests | full run-output parity (DSCR 1.451/1.15, lock-up) before/after | **High** | 49G (last) | Conditional |
| Auth/session helpers | `main_web.py`: `/login`, `/logout`, `get_current_user`, session cookie handling | `app/services/auth_session.py` (or extend `app/auth.py`) | itsdangerous serializer, config | session cookie | auth/pilot-mode phase tests | session round-trip unit tests | Low-Med | 49H | Conditional |
| Backup/readyz operations | `main_web.py`: `GET /readyz`, `GET /health`, `GET /public-health`; uses `app/persistence/backup_restore.py`, `app/observability.py` | `app/services/ops_endpoints.py` | observability, backup module | none | observability/backup phase tests | readyz/health response unit tests | Low | 49H | Yes |
| UI component helpers | `app/ui/components.py`, `_user_project_selector_items` | keep in `app/ui/components.py` (consolidate) | none | none | none | component render tests | Low | opportunistic | Yes |

## Notes

- **export_service is the only row rated unambiguously Safe=Yes for a first real extraction** because it is leaf-like, already partly packaged under `app/export/*`, and anchored by existing Phase 47/48 tests.
- **run orchestration is High risk** because, although the extraction would move only call sites (not formulas), it sits on the runtime path; it must come last and behind full output-parity tests (DSCR 1.451 TUHO / 1.15 Oborovo, distribution lock-up).
- Backup/readyz ops is also low-risk and could be bundled opportunistically, but export_service remains the recommended first.

## Guardrails

G20 BLOCKED; R99/R102 NOT APPROVED; `partial_pay_sweep` not promoted; flat/min DSCR sculpting not promoted; backend source of truth. No behavior, formula, runtime, model-output, data-path, factory, or fixture-CSV changes in Phase 49A.
