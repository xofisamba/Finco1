# Phase 50C-1 — Runtime Snapshot Decision Matrix

## Base SHA
`dd6124814ccdcd9a36486c3909acd91f9446dca3`

## Rows

### Row 1: saved_state + active_scenario_id + resolved_snapshot exists

| Column | Value |
|--------|-------|
| **branch** | A2 — `runtime_origin=="saved_state"` + `workspace_state.active_scenario_id` set + `scenario_record` found + `resolved_snapshot` exists |
| **inputs** | `runtime_origin="saved_state"`, `workspace_state.active_scenario_id` set, scenario exists in DB, `resolved_snapshot` not None |
| **repository helper called?** | Yes — `resolve_active_scenario_runtime_snapshot(user.user_id, project_record.project_id, workspace_state.active_scenario_id)` |
| **returned snapshot** | `dict(resolved_snapshot)` — clean scenario snapshot |
| **returned scenario_record** | `scenario_record` (ScenarioRecord from DB) |
| **warning** | `warning_from_resolver` (may be None) |
| **effective_runtime_origin** | `"saved_state"` (unchanged) |
| **caller impact** | Normal — snapshot from scenario DB, scenario_record bound, warning may be shown |
| **extraction risk** | MEDIUM — repository call must be importable in service |
| **test coverage** | Can test with mocks |

---

### Row 2: saved_state + active_scenario_id + scenario_record None

| Column | Value |
|--------|-------|
| **branch** | A1 — `runtime_origin=="saved_state"` + `active_scenario_id` set + scenario unavailable/invalid |
| **inputs** | `runtime_origin="saved_state"`, `workspace_state.active_scenario_id` set, scenario NOT found in DB |
| **repository helper called?** | Yes — `resolve_active_scenario_runtime_snapshot(...)` returns `(None, None, warning)` |
| **returned snapshot** | `workspace_state.saved_snapshot or project_record.baseline_snapshot or {}` |
| **returned scenario_record** | `None` |
| **warning** | `warning_from_resolver or "Selected saved scenario was unavailable, so runtime fell back to the last clean saved boundary."` |
| **effective_runtime_origin** | `"workspace_base"` — **OVERRIDDEN from input "saved_state"!** |
| **caller impact** | Caller receives workspace_base origin — may affect downstream path selection |
| **extraction risk** | HIGH — effective_runtime_origin override is subtle behavior change |
| **test coverage** | Can test with mock returning scenario_record=None |

---

### Row 3: saved_state + active_scenario_id + resolved_snapshot None + saved_snapshot exists

| Column | Value |
|--------|-------|
| **branch** | A3 — `scenario_record` found but `resolved_snapshot` is None |
| **inputs** | `runtime_origin="saved_state"`, `active_scenario_id` set, scenario in DB but has no resolved snapshot |
| **repository helper called?** | Yes — `resolve_active_scenario_runtime_snapshot(...)` returns `(scenario_record, None, warning)` |
| **returned snapshot** | `workspace_state.saved_snapshot` (baseline_snapshot not checked here) |
| **returned scenario_record** | `scenario_record` (from DB) |
| **warning** | `warning_from_resolver` (may be None) |
| **effective_runtime_origin** | `"saved_state"` (unchanged) |
| **caller impact** | scenario_record bound but snapshot from workspace saved_snapshot |
| **extraction risk** | MEDIUM — order of fallback: saved_snapshot only, not baseline_snapshot |
| **test coverage** | Can test with mock returning scenario_record with None resolved_snapshot |

---

### Row 4: saved_state + active_scenario_id + resolved_snapshot None + baseline_snapshot exists (no saved_snapshot)

| Column | Value |
|--------|-------|
| **branch** | A3 fallback — same as Row 3 but `workspace_state.saved_snapshot` is None/empty |
| **inputs** | `runtime_origin="saved_state"`, `active_scenario_id` set, scenario in DB, no resolved_snapshot, no saved_snapshot |
| **repository helper called?** | Yes |
| **returned snapshot** | `project_record.baseline_snapshot` |
| **returned scenario_record** | `scenario_record` |
| **warning** | `warning_from_resolver` (may be None) |
| **effective_runtime_origin** | `"saved_state"` |
| **caller impact** | scenario_record bound, snapshot from project baseline |
| **extraction risk** | MEDIUM |
| **test coverage** | Can test with mock |

---

### Row 5: saved_state + no active_scenario_id + saved_snapshot exists

| Column | Value |
|--------|-------|
| **branch** | C (else branch) — `runtime_origin=="saved_state"` but `workspace_state.active_scenario_id` is None/empty |
| **inputs** | `runtime_origin="saved_state"`, `workspace_state.active_scenario_id` is None/empty, `workspace_state.saved_snapshot` exists |
| **repository helper called?** | **No** — `active_scenario_id` is falsy so branch A not entered |
| **returned snapshot** | `workspace_state.saved_snapshot` |
| **returned scenario_record** | `None` |
| **warning** | `None` |
| **effective_runtime_origin** | `"saved_state"` (unchanged) |
| **caller impact** | No scenario binding, snapshot from saved_snapshot |
| **extraction risk** | LOW — falls to else branch |
| **test coverage** | Can test |

---

### Row 6: saved_state + no active_scenario_id + baseline_snapshot exists (no saved_snapshot)

| Column | Value |
|--------|-------|
| **branch** | C — `saved_state` but no active_scenario_id and no saved_snapshot |
| **inputs** | `runtime_origin="saved_state"`, no active_scenario_id, no saved_snapshot, project has baseline_snapshot |
| **repository helper called?** | No |
| **returned snapshot** | `{}` (empty dict — workspace_state.saved_snapshot is None, so or {} applies) |
| **returned scenario_record** | `None` |
| **warning** | `None` |
| **effective_runtime_origin** | `"saved_state"` |
| **caller impact** | Empty snapshot used (potential issue) |
| **extraction risk** | HIGH — empty snapshot when no snapshots exist is surprising behavior |
| **test coverage** | Can test with mocks |

---

### Row 7: saved_state + no active_scenario_id + no snapshots

| Column | Value |
|--------|-------|
| **branch** | C — same as Row 6 but no baseline_snapshot either |
| **inputs** | `runtime_origin="saved_state"`, no active_scenario_id, no saved_snapshot, no baseline_snapshot |
| **repository helper called?** | No |
| **returned snapshot** | `{}` (empty dict) |
| **returned scenario_record** | `None` |
| **warning** | `None` |
| **effective_runtime_origin** | `"saved_state"` |
| **caller impact** | Empty snapshot — route may handle gracefully or error |
| **extraction risk** | HIGH — callers must handle empty snapshot |
| **test coverage** | Can test with empty mocks |

---

### Row 8: user_created + saved_state + saved_snapshot exists

| Column | Value |
|--------|-------|
| **branch** | B1 — `project_origin=="user_created"` and `runtime_origin=="saved_state"` and `saved_snapshot` |
| **inputs** | `project_record.project_origin="user_created"`, `runtime_origin="saved_state"`, `workspace_state.saved_snapshot` exists |
| **repository helper called?** | No |
| **returned snapshot** | `workspace_state.saved_snapshot` |
| **returned scenario_record** | `None` |
| **warning** | `None` |
| **effective_runtime_origin** | `"saved_state"` (unchanged) |
| **caller impact** | user_created project with saved state — common path |
| **extraction risk** | MEDIUM — user_created path is distinct |
| **test coverage** | Can test with mock |

---

### Row 9: user_created + NOT saved_state + baseline_snapshot exists

| Column | Value |
|--------|-------|
| **branch** | B2 — `project_origin=="user_created"` but `runtime_origin!="saved_state"` |
| **inputs** | `project_record.project_origin="user_created"`, `runtime_origin` not "saved_state" (e.g. "workspace_base"), `project_record.baseline_snapshot` exists |
| **repository helper called?** | No |
| **returned snapshot** | `project_record.baseline_snapshot or workspace_state.saved_snapshot or {}` — baseline first |
| **returned scenario_record** | `None` |
| **warning** | `None` |
| **effective_runtime_origin** | `runtime_origin` (unchanged) |
| **caller impact** | user_created without saved_state — baseline used |
| **extraction risk** | MEDIUM — B2 fallback order differs from A |
| **test coverage** | Can test |

---

### Row 10: user_created + baseline_snapshot exists + no saved_snapshot

| Column | Value |
|--------|-------|
| **branch** | B2 — same as Row 9 but no saved_snapshot |
| **inputs** | `project_origin="user_created"`, no saved_snapshot, baseline exists |
| **repository helper called?** | No |
| **returned snapshot** | `project_record.baseline_snapshot` |
| **returned scenario_record** | `None` |
| **warning** | `None` |
| **effective_runtime_origin** | `runtime_origin` (unchanged) |
| **caller impact** | baseline_snapshot used |
| **extraction risk** | MEDIUM |
| **test coverage** | Can test |

---

### Row 11: user_created + no snapshots

| Column | Value |
|--------|-------|
| **branch** | B2 — `user_created` with no saved_snapshot and no baseline_snapshot |
| **inputs** | `project_origin="user_created"`, no saved_snapshot, no baseline_snapshot |
| **repository helper called?** | No |
| **returned snapshot** | `{}` (empty dict — both None → or {} applied) |
| **returned scenario_record** | `None` |
| **warning** | `None` |
| **effective_runtime_origin** | `runtime_origin` (unchanged) |
| **caller impact** | Empty snapshot — route must handle |
| **extraction risk** | HIGH — empty snapshot for user_created possible |
| **test coverage** | Can test with empty mocks |

---

### Row 12: factory_base_runtime

| Column | Value |
|--------|-------|
| **branch** | C — `runtime_origin=="factory_base_runtime"` — not saved_state, not user_created |
| **inputs** | `runtime_origin="factory_base_runtime"` |
| **repository helper called?** | No |
| **returned snapshot** | `workspace_state.saved_snapshot or {}` |
| **returned scenario_record** | `None` |
| **warning** | `None` |
| **effective_runtime_origin** | `"factory_base_runtime"` (unchanged) |
| **caller impact** | Factory path — form-driven behavior; this function not typically called for factory path |
| **extraction risk** | LOW — not the primary path for factory |
| **test coverage** | Can test |

---

### Row 13: workspace_base fallback

| Column | Value |
|--------|-------|
| **branch** | C — `runtime_origin=="workspace_base"` |
| **inputs** | `runtime_origin="workspace_base"` |
| **repository helper called?** | No |
| **returned snapshot** | `workspace_state.saved_snapshot or {}` |
| **returned scenario_record** | `None` |
| **warning** | `None` |
| **effective_runtime_origin** | `"workspace_base"` (unchanged) |
| **caller impact** | Workspace base path — clean fallback |
| **extraction risk** | LOW |
| **test coverage** | Can test |

---

### Row 14: unexpected/unknown runtime_origin

| Column | Value |
|--------|-------|
| **branch** | C — `runtime_origin` not matching any known value |
| **inputs** | `runtime_origin` value not in {saved_state, workspace_base, factory_base_runtime, preview_only, user_created} |
| **repository helper called?** | No |
| **returned snapshot** | `workspace_state.saved_snapshot or {}` |
| **returned scenario_record** | `None` |
| **warning** | `None` |
| **effective_runtime_origin** | unchanged (unknown value passed through) |
| **caller impact** | Falls to else branch — likely error state |
| **extraction risk** | LOW — gracefully falls through |
| **test coverage** | Can test with unknown value |

---

## Key Observations

1. **effective_runtime_origin override only happens in one case:** Branch A1 (scenario unavailable) overrides `"saved_state"` → `"workspace_base"`. This is the only case where input != output.

2. **Repository call only in branch A:** `resolve_active_scenario_runtime_snapshot` is only called when `runtime_origin=="saved_state" AND active_scenario_id` is set.

3. **user_created fires regardless of runtime_origin:** Branch B fires when `project_origin=="user_created"` regardless of what `runtime_origin` is. This means for user_created projects, the A branch (saved_state+active_scenario_id) is never reached because B fires first.

4. **Fallback order differs by branch:**
   - Branch A: `resolved_snapshot` OR `saved_snapshot` OR `baseline_snapshot`
   - Branch B2: `baseline_snapshot` OR `saved_snapshot` (baseline first!)
   - Branch C: `saved_snapshot` or `{}`

5. **Empty snapshot is a real possibility:** Rows 6, 7, 11 can return `{}` — callers must handle this gracefully.