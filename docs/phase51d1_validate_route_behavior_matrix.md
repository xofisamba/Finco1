# Phase 51D-1 — /validate route behavior matrix

## Base SHA

`d2130bfa3504b5c38ea1a182680a7da50871ad3e` (origin/main @ PR #382 merge,
Phase 51C-2 /compare extraction)

## Path inventory

The `/validate` route in `main_web.py` exposes the following behavior
paths. Each row describes: trigger/input, what the route does,
expected output, and the current characterization status.

| # | Path | Trigger / input | Project source | Helpers used | Validation expected | Template / status | Key context fields | Warnings / errors | Extraction risk | Test coverage (Phase 51D-1) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Unauthenticated | No `COOKIE_NAME` cookie | n/a | `get_current_user` → False | n/a (early redirect) | 302 redirect → `/login` | n/a | n/a | low (route-level only) | `test_validate_unauthenticated_redirects_to_login` (live) |
| 2 | Authenticated, valid Solar inputs | All 12 fields valid; `project_type="Solar"`, `scenario="Base"`, all 9 numerics in range | any (project_origin doesn't matter for validation) | `_collect_form_snapshot`, `_project_workspace_from_snapshot`, `check_runtime_allowed`, `_resolve_runtime_snapshot_source` (captured, unused), `_build_schema_from_form` | all three stages pass | `partials/validation.html`, status 200 | `valid=True`, `errors=[]`, `form_data={"project_type":"Solar","scenario":"Base"}` | none | medium (pin all 3 stage order, plus parity snapshot call) | `test_validate_valid_solar_inputs_returns_validation_template` (live), `test_validate_stage_a_passes_solar`, `test_validate_stage_b_passes_for_in_range_numerics`, `test_validate_stage_c_runs_only_when_no_prior_errors`, `test_validate_parity_runtime_snapshot_resolved_but_unused` (structural) |
| 3 | Authenticated, valid Wind inputs | All 12 fields valid; `project_type="Wind"`, `scenario="Base"`, all 9 numerics in range | any | (same as #2) | all three stages pass | `partials/validation.html`, status 200 | `valid=True`, `errors=[]`, `form_data={"project_type":"Wind","scenario":"Base"}` | none | low (mirrors Solar) | `test_validate_valid_wind_inputs_returns_validation_template` (live) |
| 4 | Authenticated, valid Downside scenario | `scenario="Downside"`, all else valid | any | (same as #2) | all three stages pass | `partials/validation.html`, status 200 | `valid=True`, `errors=[]`, `form_data={"project_type":"Solar","scenario":"Downside"}` | none | low | `test_validate_valid_downside_scenario_passes` (live) |
| 5 | Authenticated, valid Upside scenario | `scenario="Upside"`, all else valid | any | (same as #2) | all three stages pass | `partials/validation.html`, status 200 | `valid=True`, `errors=[]`, `form_data={"project_type":"Solar","scenario":"Upside"}` | none | low | `test_validate_valid_upside_scenario_passes` (live) |
| 6 | Invalid project_type | `project_type="Nuclear"` (not in `PROJECT_TYPES`) | any | (same as #2) | Stage A fails (project_type) | `partials/validation.html`, status 200 | `valid=False`, `errors=["project_type must be one of ['Solar', 'Wind']"]`, `form_data={...}` | one Stage A error | low (well-pinned) | `test_validate_invalid_project_type_returns_stage_a_error` (live) |
| 7 | Invalid scenario | `scenario="Extreme"` (not in `SCENARIOS`) | any | (same as #2) | Stage A fails (scenario) | `partials/validation.html`, status 200 | `valid=False`, `errors=["scenario must be one of ['Base', 'Downside', 'Upside']"]`, `form_data={...}` | one Stage A error | low | `test_validate_invalid_scenario_returns_stage_a_error` (live) |
| 8 | Both invalid | `project_type="Nuclear"`, `scenario="Extreme"` | any | (same as #2) | Stage A fails (both) | `partials/validation.html`, status 200 | `valid=False`, `errors=[project_type err, scenario err]`, `form_data={...}` | two Stage A errors (accumulated, not short-circuited) | low | `test_validate_both_invalid_accumulates_errors` (live + structural) |
| 9 | Non-numeric input | `capacity_mw="abc"` (cannot be parsed as float) | any | (same as #2) | Stage B fails (capacity_mw) | `partials/validation.html`, status 200 | `valid=False`, `errors=["capacity_mw must be a number"]`, `form_data={...}` | one Stage B error | low | `test_validate_non_numeric_capacity_mw_returns_stage_b_error` (live) |
| 10 | Negative input | `capacity_mw="-1"` | any | (same as #2) | Stage B fails (capacity_mw) | `partials/validation.html`, status 200 | `valid=False`, `errors=["capacity_mw must be non-negative"]`, `form_data={...}` | one Stage B error | low | `test_validate_negative_capacity_mw_returns_stage_b_error` (live) |
| 11 | Above-max input | `capacity_mw="99999"` (max is 2000) | any | (same as #2) | Stage B fails (capacity_mw) | `partials/validation.html`, status 200 | `valid=False`, `errors=["capacity_mw must be <= 2000.0"]`, `form_data={...}` | one Stage B error | low | `test_validate_above_max_capacity_mw_returns_stage_b_error` (live) |
| 12 | Empty numeric field | `capacity_mw=""` | any | (same as #2) | Stage B passes (empty → `(None, None)`), Stage C may run | `partials/validation.html`, status 200 | `valid=True` (if Stage C also passes) or `valid=False` (if Stage C fails), `form_data={...}` | Stage C result depends | low (preserved behavior: empty treated as optional) | `test_validate_empty_numeric_field_passes_stage_b` (live) |
| 13 | Schema build error | `scenario="Base"`, `capacity_mw="100"`, all else valid, but schema raises `ValueError` (e.g. Pydantic constraint) | any | (same as #2) | Stage C fails (schema) | `partials/validation.html`, status 200 | `valid=False`, `errors=[<ValueError str>]`, `form_data={...}` | one Stage C error | low (only runs when A/B pass) | `test_validate_schema_value_error_returns_stage_c_error` (live) |
| 14 | Runtime guard blocked | `check_runtime_allowed` returns `(False, _, "...")` | any | (same as #2) | n/a (early return) | `partials/errors.html`, status 200 | `errors=[guard_message]` | one guard message | low (early return) | `test_validate_runtime_guard_blocked_returns_errors_html` (live) |
| 15 | user_created project | `project_record.project_origin == "user_created"` (and `runtime_origin != "saved_state"`) | user_created | (same as #2) | `runtime_snapshot` resolved (and captured, unused) → A/B/C stages | (depends on form values) | (same as Solar/Wind cases) | (same as A/B/C cases) | low (parity call preserved) | `test_validate_user_created_project_resolves_runtime_snapshot` (structural) |
| 16 | saved_state + active_scenario | `runtime_origin == "saved_state" and workspace_state.active_scenario_id` | template-seeded | (same as #2) | `runtime_snapshot` resolved (and captured, unused) → A/B/C stages | (depends on form values) | (same as Solar/Wind cases) | (same as A/B/C cases) | low (parity call preserved) | `test_validate_saved_state_active_scenario_resolves_runtime_snapshot` (structural) |
| 17 | Template-seeded project (TUHO/Oborovo) | `project_record.template_source in {"tuho", "oborovo"}` (no special handling in /validate) | template-seeded | (same as #2) | form-value-driven, no template-seeded branching | (depends on form values) | (same as Solar/Wind cases) | (same as A/B/C cases) | low (no template-seeded branching) | `test_validate_tuho_template_seeded_path` (structural / live), `test_validate_oborovo_template_seeded_path` (structural / live) |
| 18 | All numerics at max boundary | `capacity_mw="2000"`, `tariff_eur_mwh="1000"`, etc. (all at exact max) | any | (same as #2) | all Stage B checks pass (max is `<= max_val` not `< max_val`) | `partials/validation.html`, status 200 | `valid=True` (assuming A and C also pass) | none | low (boundary condition) | `test_validate_max_boundary_numerics_pass` (live) |
| 19 | All numerics just above max | `capacity_mw="2000.01"`, etc. (just above max) | any | (same as #2) | Stage B fails (capacity_mw) | `partials/validation.html`, status 200 | `valid=False`, `errors=["capacity_mw must be <= 2000.0"]`, `form_data={...}` | one Stage B error | low | `test_validate_just_above_max_returns_error` (live) |
| 20 | Stage A error short-circuits Stage C | `project_type="Nuclear"`, `capacity_mw="-1"` (both invalid) | any | (same as #2) | Stage A fails (project_type), Stage B fails (capacity_mw), **Stage C does NOT run** (because `if not errors:` gate) | `partials/validation.html`, status 200 | `valid=False`, `errors=[project_type err, capacity_mw err]` (only 2 errors, no schema attempt) | two Stage A/B errors (Stage C skipped) | medium (gate behavior must be preserved) | `test_validate_stage_c_skipped_when_stage_a_or_b_has_errors` (structural / live) |
| 21 | Read-only invariant | (any path) | any | (n/a — no persistence helpers called) | n/a | n/a | n/a | n/a | low (no persistence today) | `test_validate_route_has_no_persistence_side_effects` (structural), `test_validate_service_does_not_define_persistence_helpers` (forward-looking for 51D-2) |

## Numeric field max values (pinned for Phase 51D-2)

| Field | Max value | Source |
|---|---|---|
| `capacity_mw` | 2000.0 | `numeric_checks` tuple at main_web.py:1478 |
| `tariff_eur_mwh` | 1000.0 | same |
| `p50_hours` | 10000.0 | same |
| `total_capex_keur` | 1_000_000.0 | same |
| `opex_y1_keur` | 500_000.0 | same |
| `gearing_pct` | 100.0 | same |
| `target_dscr` | 10.0 | same |
| `interest_rate_pct` | 30.0 | same |
| `tenor_years` | 50.0 | same |

These values are hard-coded in the current route. Phase 51D-2 may
either keep them hard-coded in `validation_service.py` (preserves
current behavior) or extract them to a deps field (refactor, out of
scope for behavior-preserving extraction). The proposed deps bundle
does NOT include them as a separate field; they stay inside the
service.

## Helpers used by the current /validate route (input to deps)

| Helper | Used by /validate? | Where defined | Notes |
|---|---|---|---|
| `get_current_user` | yes (auth) | main_web.py:199 | stays in main_web.py (route-owned) |
| `_collect_form_snapshot` | yes | main_web.py:265 | passed as dep |
| `_project_workspace_from_snapshot` | yes | main_web.py:986 | passed as dep |
| `check_runtime_allowed` | yes (imported) | app.services.scenario_state_service:165 | passed as dep |
| `_resolve_runtime_snapshot_source` | yes (captured, unused) | main_web.py:1005 | passed as dep (parity) |
| `_build_schema_from_form` | yes (Stage C) | main_web.py:1117 | passed as dep |
| `_validate_numeric_field` | yes (Stage B) | main_web.py:1196 | passed as dep (new vs. compare_service) |
| `PROJECT_TYPES` | yes (Stage A) | main_web.py:140 | passed as dep (list) |
| `SCENARIOS` | yes (Stage A) | main_web.py:139 | passed as dep (list) |
| `_canonical_project_type` | no | main_web.py:232 | NOT used by /validate; could be dropped from deps (YAGNI) or kept for parity |
| `_normalize_template_source` | no | main_web.py:236 | NOT used; could be dropped or kept |
| `SnapshotInputError` | no | app.input_adapter:30 | NOT used; could be dropped or kept |

## xfail / deferred paths

No paths are marked `xfail` in Phase 51D-1 — the characterization is
complete. All 21 paths above are either pinned as passing tests or
characterized structurally. The one **candidate-for-cleanup** is the
runtime-snapshot-resolved-but-unused call (rows 15, 16), but it is
NOT marked xfail because the current behavior (resolve + discard) is
preserved by Phase 51D-2.

## Test coverage summary

| Category | Count | Notes |
|---|---|---|
| Live integration tests (TestClient) | 13 | Rows 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 18, 19, 20 |
| Structural / unit tests (read source files) | 8 | Rows 2 (parity), 15, 16, 17 (TUHO), 17 (Oborovo), 21 (read-only) |
| Smoke import tests | 2 | `test_main_web_imports_cleanly`, forward-looking for 51D-2 |
| Regression tests (Phase 51A/B/C/51C-2) | 4 | All previous phase51 suites must still pass |
| **Total** | **~27 tests** | in `tests/test_phase51d1_validate_route_golden_characterization.py` |
