# C2-PR4: Dependency Graph Foundation — Implementation Note

## Scope

This PR adds a **dependency graph foundation** that maps dirty C1
cells/sheets to the coarse-grained model **output groups** they would
eventually affect, sitting on top of `FcLiveModel`'s deterministic
recalc-scheduler snapshot established in C2-PR3.

It implements **infrastructure only**:

1. A registry of grid/cell-address → output-group mappings.
2. A resolution API (`resolveCell`, `resolveSnapshot`,
   `getAffectedGroups`, `explain`).
3. Conservative, non-throwing handling of unknown/unmapped addresses.
4. A purely additive `affectedGroups` field on the snapshot returned
   by/emitted with `FcLiveModel.flushScheduledRecalc()`.

It does **not** implement, call, or scaffold: financial
recalculation, a formula engine, dependency *execution* (actually
running anything based on the graph), backend Run calls, Save
changes, persistence changes, export changes, UI updates, KPI
recomputation, or scenario recomputation.

## Ownership

`window.FcDependencyGraph` (`static/modelling/dependency-graph.js`)
is a new, standalone module — deliberately **not** folded into
`FcLiveModel`, unlike C2-PR3's scheduler-on-FcLiveModel decision.
Rationale: the scheduler in C2-PR3 extended *dirty-state ownership*
(a single source of truth FcLiveModel already owned). The dependency
graph is a different kind of thing — a static, stateless lookup table
with no notion of "current" anything; it never reads or writes dirty
state, never reads the DOM, and has no lifecycle (no `init()`, no
listeners). Putting it in its own file keeps that distinction
explicit and lets it be unit-tested (via `resolveCell`/`explain`)
completely independently of any live page/edit state. `FcLiveModel`
remains the sole owner of dirty state and scheduling; it merely
*consumes* `FcDependencyGraph` as a read-only annotator at the single
seam C2-PR3 already flagged as the future extension point
(`flushScheduledRecalc()`).

Script load order in `app/templates/base.html`:
`dependency-graph.js` loads **before** `live-model.js` (and well
before `app.js`), so `window.FcDependencyGraph` is always defined by
the time any flush occurs. If, for any reason, `FcDependencyGraph` is
absent (e.g. an isolated test fixture that only loads
`live-model.js`), `flushScheduledRecalc()` skips the annotation
entirely and returns the exact same snapshot shape C2-PR3 already
returned — confirmed by the guard `if (window.FcDependencyGraph &&
typeof window.FcDependencyGraph.resolveSnapshot === 'function')` in
`live-model.js`.

## Mapping philosophy

Coarse, conservative, per-grid wildcard rules are the default; a
handful of finer-grained rules are layered on top only where the
real-world effect of a specific field is obviously narrower or
broader than its grid's default. All grid ids and address shapes
below were confirmed by grepping the real production templates
(`app/templates/partials/*.html`), not invented:

- `capex` (`sheet_capex.html`, e.g. `capex!<code>.amount`)
- `opex` (`sheet_opex_detail.html`, e.g. `opex!<code>.Y<n>`,
  `opex!<code>.budget`)
- `inputs` (`sheet_inputs.html` via `inputs_section.html`'s
  `field_row()` macro, e.g. `inputs!technical.capacity_mw`,
  sections found: `identity`, `technical`, `capex`, `opex`,
  `revenue`, `debt`, `tax`, `schedule`)
- `revenue` (`sheet_revenue.html`, e.g.
  `revenue!summary.tariff_y1`, `revenue!<item.code>`)
- `seniordebt` (`sheet_senior_debt.html`, e.g.
  `seniordebt!gearing_pct`, `seniordebt!facility_amount`,
  `seniordebt!target_dscr`)
- `tax` (`sheet_tax.html`, e.g. `tax!cit_rate`, `tax!convention`)
- `export` (`workspace_shell.html`, e.g.
  `export!current_context.project`)
- `audit` (`_audit_governance_relocated.html`, e.g.
  `audit!governance_status.g20_gate`)
- `scenarios` (`scenario_matrix.html`)
- `scenario-inputs` (`scenario_tab.html`)
- `scenario-summary` (`_scenario_unified_entry.html`)
- `scenario-compare` (`scenario_compare.html`)

### Grid-level wildcard rule table

| Grid id | Affected groups | Rationale |
|---|---|---|
| `capex` | capex, senior-debt, overview-kpis | A CAPEX line item feeds total CAPEX, which feeds debt sizing and headline KPIs. Not revenue/opex/tax/scenarios. |
| `opex` | opex, tax, overview-kpis | OPEX is tax-deductible and feeds IRR/DSCR. |
| `inputs` | overview-kpis, revenue, opex, capex, senior-debt, tax | The generic top-level scalar Inputs grid is the seed-assumption surface for the whole model — broadest wildcard by design. Finer per-section rules (below) narrow this where the effect is obviously scoped. |
| `revenue` | revenue, tax, overview-kpis | Revenue is taxable and feeds IRR/DSCR. |
| `seniordebt` | senior-debt, overview-kpis | Facility/gearing/rate/tenor changes affect debt sizing and headline KPIs only — not revenue/opex/tax line items directly. |
| `tax` | tax, overview-kpis | Tax assumptions affect post-tax equity IRR. |
| `export` | export-audit | Read-mostly presentation surface over already-computed state; does not feed back into other groups. |
| `audit` | export-audit | Same reasoning as `export`. |
| `scenarios` | scenarios | Scenario matrix surface. |
| `scenario-inputs` | scenarios, overview-kpis | Editing a scenario's underlying inputs plausibly changes that scenario's computed KPIs too — conservative addition vs. the other three scenario grids. |
| `scenario-summary` | scenarios | Presentational summary of scenario outputs. |
| `scenario-compare` | scenarios | Presentational comparison of scenario outputs. |

### Fine-grained `inputs!<section>.<field>` rule table

Layered on top of the `inputs` wildcard above; matched first when the
section is recognised, otherwise falls back to the broad `inputs`
wildcard (not to `unknown` — `inputs` is itself a registered grid,
just with an unrecognised section name, e.g. a future new section).

| Inputs section | Affected groups | Rationale |
|---|---|---|
| `technical` | overview-kpis, revenue, capex, senior-debt | A capacity_mw-style input ripples into production (revenue), sizing (capex), and debt sizing/DSCR (senior-debt), plus headline KPIs. Conservatively excludes opex/tax. |
| `capex` | capex, senior-debt, overview-kpis | Same as the `capex` grid wildcard. |
| `opex` | opex, tax, overview-kpis | Same as the `opex` grid wildcard. |
| `revenue` | revenue, tax, overview-kpis | Same as the `revenue` grid wildcard. |
| `debt` | senior-debt, overview-kpis | Same as the `seniordebt` grid wildcard. |
| `tax` | tax, overview-kpis | Same as the `tax` grid wildcard. |
| `identity` | overview-kpis | Project name/identity fields are largely presentational. |
| `schedule` | overview-kpis, scenarios | Timing fields (e.g. COD date, construction months) can shift scenario comparisons. |

This is a judgement call, not a precise spec — the explicit design
goal is to be reasonably conservative (when in doubt, include
`overview-kpis` and the grid's own group) without claiming every edit
affects every group. A future PR with real formula-level dependency
information could narrow these.

## Unknown-address handling

`resolveCell(addr)` never throws, for any input (including
non-string, malformed strings with no `!`, or a well-formed
`gridId!key` address whose `gridId` has no registered rule). All such
cases resolve to the conservative fallback `["overview-kpis",
"unknown"]` — broad rather than narrow, per the task's explicit
preference. `explain(addr)` additionally reports `matched: false` and
a human-readable reason (e.g. `"Grid id \"foo\" is not registered in
the dependency graph; conservative fallback group set returned."`).

An `inputs!<unrecognised-section>.<field>` address is a special case:
it is **not** treated as fully unknown, because `inputs` itself is a
registered grid — it falls back to the broad `inputs` wildcard rather
than `["overview-kpis", "unknown"]`, since that is still a more
informative (and equally conservative-or-broader) answer than the
generic unknown fallback.

## Resolution API

- `resolveCell(addr)` → sorted array of group strings.
- `resolveSnapshot(snapshot)` → sorted array of group strings, the
  union over every `addr` in every `grid.addrs` in the
  `{grids: [{gridId, addrs}], projectDirty}` snapshot shape
  `FcLiveModel.getPendingRecalcSnapshot()` already produces.
- `getAffectedGroups(addrs)` → sorted array of group strings, the
  union over a flat list of addresses (used internally by
  `resolveSnapshot`, also exposed directly).
- `explain(addr)` → `{addr, matched, rule, affectedGroups, reason}`
  diagnostic object.

All four are pure functions of their input: no timestamps, no
session ids, no hidden global state read besides the static registry
tables. Two calls with the same logical input (even differently
ordered, e.g. two snapshots whose grids/addrs arrays list the same
dirty cells in a different order) always produce structurally equal,
sorted output.

## Scheduler integration — exact hook point

`FcLiveModel.flushScheduledRecalc()` (`static/modelling/live-model.js`)
gained exactly one additive block, immediately after building the
existing C2-PR3 snapshot and before emitting `recalc-flush-complete`:

```js
var snapshot = getPendingRecalcSnapshot();
if (window.FcDependencyGraph && typeof window.FcDependencyGraph.resolveSnapshot === 'function') {
  snapshot.affectedGroups = window.FcDependencyGraph.resolveSnapshot(snapshot);
}
_emit('recalc-flush-complete', { reason: reason, snapshot: snapshot });
return snapshot;
```

This is the only change to `live-model.js`. It:

- Adds a new `affectedGroups` field to the snapshot object — every
  pre-existing field (`grids`, `projectDirty`) is untouched, so every
  C2-PR3 test assertion against the snapshot shape continues to pass
  unmodified (confirmed by re-running
  `tests/test_c2_pr3_recalc_scheduler_browser.py` — all 10 tests
  still pass).
- Calls into `FcDependencyGraph.resolveSnapshot()` rather than
  duplicating any mapping logic inline in `live-model.js`.
- Performs no calculation, no network call, and no dirty-state
  mutation — `resolveSnapshot()` only reads the `addrs` arrays
  already present in the snapshot object it's handed.
- Degrades gracefully (no-op annotation) if `FcDependencyGraph` isn't
  loaded, so this module has no hard new dependency on
  `dependency-graph.js`'s file actually existing at runtime.

## Why no recalculation occurs yet

Exactly as in C2-PR1/PR2/PR3: this PR answers "which output groups
*would* need recalculation," not "what are those outputs' new
values." `resolveSnapshot()`/`resolveCell()` never evaluate a
formula, never call `app/waterfall_core.py` or any other financial
code, and never make a network/AJAX/htmx call (confirmed via `grep
-in "fetch(\|xmlhttprequest\|htmx.trigger\|htmx.ajax"
static/modelling/dependency-graph.js`, which matches nothing).

## What the next step toward incremental recalculation would look like

(Informational only — not implemented here.)

1. The coarse output groups this PR introduces (`overview-kpis`,
   `revenue`, `opex`, `capex`, `senior-debt`, `tax`, `scenarios`,
   `export-audit`) would need to be mapped, server-side, to the
   actual computation(s) in `app/waterfall_core.py`/`domain/*` that
   produce each group's values.
2. A real "preview" endpoint (almost certainly server-side, to
   preserve the single-source-of-truth-is-the-server invariant
   Save/Run/export already rely on) could accept exactly the
   `affectedGroups` list this PR's snapshot now carries, and
   selectively recompute only those groups instead of the whole
   project.
3. Cell-level (rather than grid-wildcard) precision could be added
   incrementally to the registry as real formula-level dependency
   information becomes available, without changing the public API
   shape (`resolveCell`/`resolveSnapshot`/`getAffectedGroups`/
   `explain` would all keep working — only the registry tables would
   grow more specific).
4. `FcLiveModel.flushScheduledRecalc()` remains the single seam where
   that future "trigger a real preview/recalc" call would be added —
   this PR deliberately stops short of that, exactly as C2-PR3 already
   flagged.

## Test coverage added

`tests/test_c2_pr4_dependency_graph_browser.py` — 9 new
production-route Playwright tests (real `uvicorn` subprocess, real
auth, real project creation, mirroring
`tests/test_c2_pr3_recalc_scheduler_browser.py`'s pattern):

1. `test_known_capex_cell_resolves_expected_groups`
2. `test_known_inputs_cell_resolves_expected_groups`
3. `test_known_senior_debt_cell_resolves_expected_groups`
4. `test_unknown_cell_resolves_conservatively_without_throwing`
5. `test_snapshot_resolution_is_deterministic`
6. `test_flush_complete_event_includes_affected_groups`
7. `test_dirty_state_unchanged_after_dependency_resolution`
8. `test_no_backend_run_request_fires`
9. `test_no_financial_values_change`

(Point 10 from the task spec — existing-suite regression — is the
full regression run reported separately in the PR description, not a
new test in this file.)

## Files changed

- `static/modelling/dependency-graph.js` — new module, the registry
  and resolution API.
- `static/modelling/live-model.js` — one additive block inside
  `flushScheduledRecalc()`, described above; every other function and
  behaviour is byte-for-byte unchanged.
- `app/templates/base.html` — one new `<script defer>` tag for
  `dependency-graph.js`, inserted before `live-model.js`'s tag.
- `tests/test_c2_pr4_dependency_graph_browser.py` — new test file.
- `docs/C2_PR4_DEPENDENCY_GRAPH_FOUNDATION_NOTE.md` — this note.

No change was made to `static/app.js` (confirmed via `git diff --stat
main -- static/app.js`, empty), and no change was made to any file
under `domain/`, `app/waterfall_core.py`, `app/input_adapter.py`, or
`app/project_factories.py` (confirmed via `git diff --stat main --
domain app/waterfall_core.py app/input_adapter.py
app/project_factories.py`, empty).
