# Phase 51C-1 — /compare route behavior matrix

This matrix pins the current behavior of `POST /compare` (as of base
SHA `5423483`) for the purposes of Phase 51C-2 extraction. Every row
is a path that the route can take, with the current behavior, the
extraction risk, and the current test coverage.

## Paths

| # | Path | Trigger / input | Project source | Scenarios executed | Helpers used | Model execution expected | Persistence side effects | Expected template / status | Key context fields | Extraction risk | Current test coverage |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Auth redirect** | No session cookie | any | none | `get_current_user` | none | none | `RedirectResponse("/login", 302)` | n/a | none | `test_htmx_internal_demo.py::test_login_required` (covers all routes, not just /compare) |
| 2 | **Runtime guard block** | `check_runtime_allowed(workspace, snapshot)` returns `(False, _, msg)` | any | none | `check_runtime_allowed` | none | none | `partials/errors.html` / 200 | `{errors: [msg]}` | low | `test_phase50c3_runtime_guard_wrapper.py::test_compare_route_guard_block_behavior` |
| 3 | **Invalid project_type** | `effective_project_type not in PROJECT_TYPES` | any | none | `PROJECT_TYPES` (constant) | none | none | `partials/errors.html` / 200 | `{errors: [f"project_type must be one of {PROJECT_TYPES}"]}` | low | `test_htmx_internal_demo.py::test_compare_invalid_project_returns_error` |
| 4 | **SnapshotInputError on user_created** | `project_record.project_origin == "user_created"` AND `build_projectinputs_from_snapshot(runtime_snapshot)` raises `SnapshotInputError` | user_created | none | `build_projectinputs_from_snapshot` | none | none | `partials/errors.html` / 200 | `{errors: [str(e)]}` | **high** — `runtime_snapshot` not defined in /compare (NameError latent bug) | xfail — pre-existing latent bug, see `test_compare_user_created_raises_nameerror` |
| 5 | **Schema build ValueError on template-seeded** | `project_record.project_origin != "user_created"` AND `_build_schema_from_form` / `build_projectinputs` raises | template-seeded | none | `_build_schema_from_form`, `build_projectinputs` | none | none | `partials/errors.html` / 200 | `{errors: [f"Invalid input: {str(e)}"]}` | medium — bare `except Exception` swallows real bugs | `test_htmx_internal_demo.py::test_compare_invalid_gearing_returns_error_not_defaults`, `test_compare_negative_capex_returns_error` |
| 6 | **Generic template-seeded (Wind) success** | `effective_project_type in PROJECT_TYPES` AND `runtime_seed not in {"tuho", "oborovo"}` AND no exceptions | template-seeded (generic wind) | Base, Downside, Upside | `_normalize_template_source`, `_canonical_project_type`, `_build_schema_from_form`, `build_projectinputs`, `run_project` | 3× `run_project("Wind", sc, override)` | none | `partials/comparison.html` / 200 | `{project_type, scenarios, results: {Base: {...}, Downside: {...}, Upside: {...}}}` | medium | `test_htmx_internal_demo.py::test_compare_uses_custom_inputs` |
| 7 | **Generic template-seeded (Solar) success** | Same as #6 but `effective_project_type == "Solar"` | template-seeded (generic solar) | Base, Downside, Upside | same as #6 | 3× `run_project("Solar", sc, override)` | none | `partials/comparison.html` / 200 | same as #6 | medium | `test_htmx_internal_demo.py::test_compare_solar_returns_comparison` |
| 8 | **TUHO template-seeded success** | `runtime_seed == "tuho"` AND no exceptions | tuho (template-seeded) | Base, Downside, Upside | same as #6, plus `_normalize_template_source` returning "tuho" | 3× `run_project("TUHO", sc, override)` | none | `partials/comparison.html` / 200 | same as #6 | medium | xfail — no dedicated TUHO compare test exists; behavior covered indirectly by /run tests + `test_phase20g_scenario_compare_history` |
| 9 | **Oborovo template-seeded success** | `runtime_seed == "oborovo"` AND no exceptions | oborovo (template-seeded) | Base, Downside, Upside | same as #6, plus `_normalize_template_source` returning "oborovo" | 3× `run_project("Oborovo", sc, override)` | none | `partials/comparison.html` / 200 | same as #6 | medium | xfail — no dedicated Oborovo compare test exists |
| 10 | **Saved state + active scenario** | `runtime_snapshot` resolved AND `runtime_origin == "saved_state"` AND `workspace_state.active_scenario_id` | any (with saved scenario) | Base, Downside, Upside | `resolve_runtime_snapshot_source` (NOT called in /compare — would be needed for proper snapshot resolution; this path is bypassed and falls into schema-from-form) | 3× `run_project(...)` | none | `partials/comparison.html` / 200 | same as #6 | **high** — /compare does not resolve runtime_snapshot at all, so "saved state" path silently uses form values | xfail — current behavior is a silent bug; documented in `phase51c1_compare_route_golden_characterization.md` |
| 11 | **Per-scenario model error (loop continues)** | One of `run_project(...)` raises an exception | any | 2 successful + 1 with `{"error": str(e)}` | `run_project` | partial (1/3 raises) | none | `partials/comparison.html` / 200 | `results: {Base: {...}, Downside: {"error": ...}, Upside: {...}}` | medium — soft-error semantics must be preserved | xfail — no test for "one scenario raises, others succeed" |
| 12 | **All three scenarios error** | All `run_project(...)` raise | any | 0 successful + 3 with `{"error": ...}` | `run_project` | none (all 3 fail) | none | `partials/comparison.html` / 200 | `results: {Base: {"error": ...}, Downside: {"error": ...}, Upside: {"error": ...}}` | low | xfail — no test for "all scenarios fail" |
| 13 | **Empty form fields** | All 10 numeric fields are empty strings | any | depends on project type | `_build_schema_from_form` with empty inputs | depends (usually errors out) | none | `partials/errors.html` / 200 OR `partials/comparison.html` / 200 (if schema is permissive) | depends | low | xfail — empty form behavior is implicit, not pinned |
| 14 | **Multi-scenario selected (not supported)** | n/a — /compare always iterates the hard-coded `SCENARIOS` list | n/a | n/a | n/a | n/a | n/a | n/a | n/a | none | n/a — by design, /compare has no scenario-selector UI |
| 15 | **Persistence side-effect path** | n/a | n/a | n/a | n/a | n/a | **none — /compare is read-only** | n/a | n/a | none | confirmed: `grep -rn "record_compare" app/` returns no matches |

## Summary of paths characterized

- **Fully characterized in tests today:** 1, 2, 3, 5, 6, 7 (6 paths)
- **Characterized in code + documented, xfail for tests:** 4, 8, 9, 10, 11, 12, 13 (7 paths)
- **Not applicable by design:** 14, 15 (2 paths)

## Extraction risk summary

| Risk | Affected paths | Severity |
|---|---|---|
| `runtime_snapshot` NameError latent bug | 4 (and possibly 10) | **high** |
| Saved-state path silently uses form values | 10 | **high** |
| Soft-error semantics (`{"error": str(e)}` per scenario) lost | 11, 12 | medium |
| Per-scenario exception handling changes | 11, 12 | medium |
| `_build_schema_from_form` arg order changed | 5, 6, 7, 8, 9 | medium |
| Bare `except Exception` swallows real bugs | 5 | low (pre-existing) |
| Template context key shape changes | 6, 7, 8, 9, 11, 12 | medium |

## Current test coverage by path

| Path | Test file | Test name |
|---|---|---|
| 1 (auth) | `tests/test_htmx_internal_demo.py` | `test_login_required` (covers all routes) |
| 2 (runtime guard) | `tests/test_phase50c3_runtime_guard_wrapper.py` | `test_compare_route_guard_block_behavior` |
| 3 (invalid project) | `tests/test_htmx_internal_demo.py` | `test_compare_invalid_project_returns_error` |
| 4 (user_created SnapshotInputError) | xfail — latent bug, would NameError before SnapshotInputError | n/a |
| 5 (schema ValueError) | `tests/test_htmx_internal_demo.py` | `test_compare_invalid_gearing_returns_error_not_defaults`, `test_compare_negative_capex_returns_error` |
| 6 (generic wind) | `tests/test_htmx_internal_demo.py` | `test_compare_uses_custom_inputs` |
| 7 (generic solar) | `tests/test_htmx_internal_demo.py` | `test_compare_solar_returns_comparison` |
| 8 (tuho compare) | xfail — no dedicated test | n/a |
| 9 (oborovo compare) | xfail — no dedicated test | n/a |
| 10 (saved state) | xfail — silently bypassed by current code | n/a |
| 11 (one scenario errors) | xfail — no test | n/a |
| 12 (all scenarios error) | xfail — no test | n/a |
| 13 (empty form) | xfail — implicit | n/a |

## Recommendations for Phase 51C-2

1. Add `resolve_runtime_snapshot_source` to the deps bundle and call
   it after `check_runtime_allowed` (mirroring /run). This **fixes
   the latent bug** at the same time as the extraction. Pin the new
   behavior in the Phase 51C-2 test suite.
2. Add tests for paths 8, 9, 11, 12, 13 in Phase 51C-2 (TUHO/Oborovo
   compare, per-scenario soft error, empty form).
3. Replace the bare `except Exception` with `(ValueError,
   SnapshotInputError, TypeError, KeyError)` — more honest about
   what we catch.
4. Pin `SCENARIOS` and `PROJECT_TYPES` as deps (move from global
   constants to deps bundle) so the service is self-contained.
5. Document the "no persistence side effects" property as a pinned
   invariant in the Phase 51C-2 test suite (so a future
   `record_compare_run` would have to be added deliberately with
   its own test).
