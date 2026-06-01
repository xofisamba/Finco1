# Phase 49D-1 — POST /download Behavior Matrix

**Branch:** `phase49d1-characterize-post-download-before-extraction`
**Base SHA:** `f6e53d5633858f0bd0aace8df77e34d28620f61d`
**Route:** `POST /download`

---

## Behavior Matrix

| Path | Trigger | Helpers Used | Expected Status | Filename | Content-Type | Provenance | record_export | Extraction Risk | Test Coverage |
|------|---------|-------------|-----------------|----------|-------------|------------|---------------|-----------------|---------------|
| **A: user_created** | `project_record.project_origin == "user_created"` | `runtime_guard_for_snapshot`, `_resolve_runtime_snapshot_source`, `build_projectinputs_from_snapshot`, `_canonical_project_type` | 200 or 400 (if guard blocked) | `fincogpt_{type}_{scenario}.xlsx` | `application/vnd.openxmlformats...sheet` | Full `replay_metadata` with `runtime_origin=factory_base_runtime`, `template_origin_override=saved_project_assumptions` | Yes, with `scenario_id` from `workspace_state.active_scenario_id` if `saved_state` | **HIGH** — complex snapshot resolution, conditional override | ⚠️ Needs path-specific test |
| **B: saved_state** | `runtime_guard_for_snapshot(...) [1] == "saved_state"` and `active_scenario_id` | `_resolve_runtime_snapshot_source`, `build_projectinputs_from_snapshot`, `_normalize_template_source` | 200 | `fincogpt_{type}_{scenario}.xlsx` | `application/vnd.openxmlformats...sheet` | `runtime_origin=saved_state`, `scenario_id=workspace_state.active_scenario_id`, `active_scenario_name=workspace_state.active_scenario_name` | Yes, with `scenario_id` and `active_scenario_id`/`active_scenario_name` | **HIGH** — multiple conditional overrides | ⚠️ Needs path-specific test |
| **C: saved_baseline** | `project_record.project_origin == "saved_baseline"` (post-bytes check) | Same as Path D + `build_excel_export` | 200 | `fincogpt_{type}_{scenario}.xlsx` | `application/vnd.openxmlformats...sheet` | Same as Path D + `replay_metadata["baseline_source"] = True` added after Excel build | Yes, with `baseline_source=True` in `replay_metadata` | **MEDIUM** — post-generation side effect on metadata | ⚠️ Needs path-specific test |
| **D: factory_base_runtime** | Default fallback (no other path matches) | `build_projectinputs(schema)`, `_normalize_template_source` | 200 | `fincogpt_{type}_{scenario}.xlsx` | `application/vnd.openxmlformats...sheet` | `runtime_origin=factory_base_runtime`, minimal provenance fields | Yes, standard fields | **MEDIUM** — simpler path but `runtime_project_key` derivation is non-trivial | ✅ Basic test possible |
| **E: validation error** | `build_projectinputs(schema)` raises `ValueError` | `_build_schema_from_form`, `build_projectinputs` | 400 | N/A | `text/html` | None | No | **LOW** — simple error path | ⚠️ Basic test |
| **F: runtime guard blocked** | `runtime_guard_for_snapshot` returns `allow_run=False` | `runtime_guard_for_snapshot` | 400 | N/A | `text/html` | None | No | **LOW** — simple 400 return | ⚠️ Needs mock |
| **G: unauthenticated** | No valid session (no `user`) | `get_current_user` | 302 → `/login` | N/A | N/A (redirect) | None | No | **LOW** — auth is simple redirect | ✅ Easy to test |
| **H: unsupported scenario/non-Base** | `scenario` param not "Base" but Path D taken | Same as Path D | 200 | `fincogpt_{type}_{scenario}.xlsx` | `application/vnd.openxmlformats...sheet` | Scenario passed through `scenario` param | Yes, `scenario_name=active_scenario_record.scenario_name if active_scenario_record else scenario` | **LOW** — scenario param flows through to filename and `scenario_name` | ⚠️ No explicit validation of scenario value |
| **I: generic project warning** | `effective_project_type` not Solar/Wind (Path A only) | `_canonical_project_type` | 200 (warning in `runtime_warning`) | `fincogpt_{type}_{scenario}.xlsx` | `application/vnd.openxmlformats...sheet` | `warning_note` from `_resolve_runtime_snapshot_source` | Yes | **LOW** — warning flows through to provenance | ⚠️ Needs edge case input |
| **J: unexpected exception** | Any `Exception` in outer try block | Various | 500 | N/A | `text/html` | None | No | **LOW** — error handling | ⚠️ Hard to test |

---

## Key Observations

### Provenance Field Conditionally Populated

| Field | When Populated |
|-------|---------------|
| `scenario_id` | Only when `runtime_origin == "saved_state"` |
| `active_scenario_id` | Only when `runtime_origin == "saved_state"` |
| `active_scenario_name` | Only when `runtime_origin == "saved_state"` |
| `template_origin_override` | Only when `project_origin == "user_created"` (`"saved_project_assumptions"`) |
| `baseline_source` | Only when `project_origin == "saved_baseline"` (post-generation) |
| `scenario_provenance` | Always, via `_scenario_provenance_for_record()` |
| `warning_note` | From `_resolve_runtime_snapshot_source()` result |

### `runtime_origin` Values by Path

| Path | `runtime_origin` value |
|------|------------------------|
| A (user_created) | `"factory_base_runtime"` (passed in, even though origin name is user_created) |
| B (saved_state) | `"saved_state"` |
| C (saved_baseline) | Path D value (factory_base_runtime) |
| D (factory_base_runtime) | `"factory_base_runtime"` |

### filename is always `fincogpt_{project_type.lower()}_{scenario.lower()}.xlsx`
Regardless of path — derived from form params, not runtime.

---

## Extraction Readiness Assessment

| Criterion | Status | Notes |
|-----------|--------|-------|
| All paths documented | ✅ | A-J documented |
| Helper function signatures known | ✅ | 10 helper functions identified |
| Provenance field conditions mapped | ✅ | All conditional fields mapped |
| record_export conditions mapped | ✅ | Always on success, fields vary by path |
| Response types mapped | ✅ | 200/302/400/500 mapped |
| **Ready for extraction** | ⚠️ **PARTIAL** | Path B and C need more detailed characterization of `active_scenario_record` lifecycle |

---

## Guardrails Status

| Guardrail | Status |
|-----------|--------|
| No formula changes | ✅ No production code changed |
| No runtime changes | ✅ |
| No model output changes | ✅ |
| G20 BLOCKED | ✅ |
| R99 NOT APPROVED | ✅ |
| R102 NOT APPROVED | ✅ |
| partial_pay_sweep not promoted | ✅ |
| flat/min DSCR sculpting not promoted | ✅ |
| Backend source of truth | ✅ |
| No JS financial calculations | ✅ |
| No fixture CSVs changed | ✅ |
| No schema migrations | ✅ |