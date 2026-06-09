# Phase 24-H Closure — Generic Modelling Loop Testability Review

> Type: DOCS + REPORT + TESTS ONLY (no implementation, no runtime/model/persistence changes)
> Status: DRAFT (review-only; not merged)
> Date: 2026-06-09
> Base SHA: `1791f32` (post-#580, post-24-H-4-merge)
> Branch: `phase24h-closure-generic-modelling-loop-review`
> Hard constraints:
> - docs/report/tests only
> - no runtime changes
> - no model/formula changes
> - no persistence/schema changes
> - no C10 / R-PAR work
> - no construction promotion
> - rc1 untouched

---

## 0. Purpose

A consolidated closure review of **Sprint 24-H** and a
**testability assessment** answering the question:

> Is FincoGPT now meaningfully testable by another internal
> finance user as an exploratory modelling tool for Generic
> Solar / Generic Wind projects?

This document does **not**:

- Touch any production code.
- Promote any feature flag.
- Implement any of the items it ranks.
- Make any bank / lender / external audit claim.

It is a structured, ranked, evidence-based review that:

1. Audits the 10 required questions a finance user, a
   renewable developer, and a product manager would ask.
2. Distinguishes what is now **user-testable** from what
   is **only test-proven but not UX-polished** from what
   still requires **manual / user guidance**.
3. Identifies the **top remaining blockers**.
4. Recommends a **next sprint** scope.
5. Preserves all hard constraints (rc1 untouched, no model
   changes, no runtime changes, no construction promotion).

---

## 1. Sprint 24-H — what was delivered

Sprint 24-H is the 4-PR / 5-doc arc that began with the
G-track closure review (PR #572) and closed with the
export / download pack (PR #580). All four PRs are
merged into `main`. No further code work is pending in
this track.

### 1.1 PR #573 — Phase 24-H-1 (Labeling)

- **Type:** UI + minimal-orchestration
- **Branch:** `phase24h-editable-generic-project-run-loop`
- **Head:** `eb1a132`
- **Status:** ✅ MERGED
- **Delivered:**
  - **`is_exploratory_project` flag** wired in 3 sites
    (project_workspace / scenario_workspace / inputs_section
    context builders).
  - **EXPLORATORY warning** in 3 partials:
    - `app/templates/partials/inputs_section.html`
    - `app/templates/partials/_last_run_indicator.html`
    - `app/templates/partials/export_registry.html`
  - **Safety copy:** "Exploratory / not Excel-parity
    validated. Not lender-ready, audit-ready, or
    bank-approved. For internal sketching only."
  - **Read-only notice preserved for factory projects**
    (`{% if not is_user_project %}`).
- **Tests:** 29/29 (all passing).
- **Hard constraints honored:** no model / formula / tax /
  debt / depreciation / IDC / persistence / runtime /
  project-status / generic-promotion / C10 /
  construction-flag changes. UI only.

### 1.2 PR #575 — Phase 24-H-2 (Delta Proof)

- **Type:** tests-only + docs + report
- **Branch:** `phase24h2-generic-run-loop-delta-proof`
- **Head:** `363f273` (squash-merge at `e8fca68`)
- **Status:** ✅ MERGED
- **Delivered:**
  - End-to-end proof that a user's edit changes the
    financial outputs (delta proof).
  - `tariff` 90 → 150 raises revenue by ~67%.
  - `opex` 800 → 1500 raises OPEX by ~88%.
  - `capex` 50,000 → 80,000 lowers IRR.
  - Stale-fresh evidence (workspace_state stays in sync).
- **Tests:** 55/55 (all passing).
- **Hard constraints honored:** tests-only.

### 1.3 PR #578 — Phase 24-H-3 (Scenario Loop + Compare)

- **Type:** tests-only + docs + report
- **Branch:** `phase24h3-generic-scenario-loop-compare`
- **Head:** `c3d286c` (squash-merge at `76d4d14`)
- **Status:** ✅ MERGED
- **Delivered:**
  - Proof that the Generic scenario loop is real:
    `resolve_scenario_snapshot(base, overrides) → effective
    snapshot → run_project → kpis`.
  - Base + Downside + Upside produce different kpi
    vectors on every dimension.
  - Compare structure (10 metric rows + 2 governance
    rows with delta computation).
  - Mutation isolation (resolving a scenario does NOT
    mutate the Base case).
- **Tests:** 53/53 (all passing).
- **Hard constraints honored:** tests-only.

### 1.4 PR #580 — Phase 24-H-4 (Export / Download Pack)

- **Type:** tests-only + docs + report
- **Branch:** `phase24h4-generic-export-download-pack`
- **Head:** `4cf3045` (squash-merge at `1791f32`)
- **Status:** ✅ MERGED
- **Delivered:**
  - Export registry partial carries the EXPLORATORY
    banner.
  - Export infrastructure is factory-bound by design
    (runtime-summary.csv / institutional-workbook.xlsx
    are tuho / oborovo only).
  - User-created generic export goes through POST /download
    (proved in 24-H-2).
  - Scenario identification schema already in place
    (`RUNTIME_SUMMARY_COLUMNS` includes scenario_id,
    scenario_name, template_origin, runtime_origin,
    runtime_flag_count, governance_posture_summary,
    replay_limitations).
- **Tests:** 58/58 (all passing).
- **Hard constraints honored:** tests-only.

---

## 2. The 10 required questions

The closure review audits each of the 10 questions with
machine-readable evidence (in
`tests/test_phase24h_closure_generic_modelling_loop_review.py`).

### 2.1 Q1 — Can a user now create/open Generic Solar or Generic Wind?

**Answer: YES (UI + service-level proof).**

| Layer | Status | Evidence |
|---|---|---|
| UI: `NEW_PROJECT_TEMPLATE_OPTIONS` exposes `generic_solar` and `generic_wind` | ✅ | `main_web.py:194-195` — labels say "Generic Solar / Generic Wind ⚠️ Unvalidated · Derived path" |
| UI: `/projects/new` form renders the form with template_source | ✅ | `app/templates/partials/new_project_form.html` |
| Service: `/projects/create` accepts `template_source=generic_solar` or `generic_wind` | ✅ | `main_web.py:2280` (POST /projects/create) |
| Service: creates `user_created` project_record | ✅ | `app/services/projects_create_service.py` |

**Gap (test-proven, not UX-polished):** the form requires
the user to fill in 16 fields before creating the
project. There is no "Use the factory defaults" button
that would pre-fill the form with `create_default_solar_project()`
or `create_default_wind_project()` baseline values. A
finance user has to know the right tariff / opex / capex
numbers for a generic sketch from scratch.

### 2.2 Q2 — Can a user edit key assumptions?

**Answer: YES (UI + service-level proof).**

| Layer | Status | Evidence |
|---|---|---|
| UI: `inputs_section.html` is editable for `is_user_project=True` | ✅ | `editable=is_user_project` |
| UI: 16 input fields exposed | ✅ | project name, technology, capacity MW, COD, construction months, horizon years, total CAPEX, P50 hours, PPA tariff, PPA term, OPEX Y1, gearing, interest rate, tenor, target DSCR, country_market |
| Service: `build_projectinputs_from_snapshot` accepts all 16 fields | ✅ | `app/input_adapter.py` |
| Service: `run_project("Solar", "Base", project_inputs_override=...)` honors the snapshot | ✅ | `app/api/project_runner.py` |

**Gap (test-proven, not UX-polished):** the form does not
show **inline validation** for "is this tariff reasonable
for Croatian solar?" or "is this OPEX too low?". A user
can type 0.001 EUR/MWh and the model will happily
produce an output.

### 2.3 Q3 — Can a user save and rerun?

**Answer: YES (UI + service-level proof).**

| Layer | Status | Evidence |
|---|---|---|
| UI: `/scenarios/state/draft` route persists the in-progress edits | ✅ | `main_web.py:2418` |
| UI: `/scenarios/save` route persists a named scenario | ✅ | `main_web.py:2563` |
| UI: `/run` route runs the model | ✅ | `main_web.py:1924-1925` |
| UI: `/save-run` route persists the runtime summary | ✅ | `main_web.py:3111` |
| Service: `resolve_scenario_snapshot` is the chain that links save → rerun | ✅ | `app/persistence/scenarios_repository.py` |

**Gap (test-proven, not UX-polished):** the save flow
requires the user to **explicitly click Save** after
editing. There is no "auto-save on dirty" mechanism.
A user who edits and then closes the browser loses the
draft.

### 2.4 Q4 — Do outputs demonstrably change?

**Answer: YES (service-level proof; UI verified by
Phase 24-H-2).**

| Proof | Delta |
|---|---|
| tariff 90 → 150 | revenue +67%, project_irr ↑, equity_irr ↑ |
| opex 800 → 1500 | opex +88%, ebitda ↓, project_irr ↓, avg_dscr ↓ |
| capex 50,000 → 80,000 | project_irr ↓ |

The financial outputs change **proportionally** to the
edits. The model honors the snapshot end-to-end.

**Gap (test-proven, not UX-polished):** the runtime
summary panel does not show a **delta indicator** like
"Project IRR went from 11.01% to 18.54% (+7.53pp) when
you changed tariff to 130". The user sees the new kpis
but not the explicit delta from the previous run.

### 2.5 Q5 — Can a user create Base/Downside/Upside?

**Answer: YES (UI + service-level proof).**

| Layer | Status | Evidence |
|---|---|---|
| UI: `/scenarios/add` route creates a child scenario | ✅ | `main_web.py:2732` (returns 403 for non-user_created) |
| UI: `/scenarios/{id}/duplicate` route duplicates the base case | ✅ | `main_web.py:2648` |
| UI: `/scenarios/{id}/update-overrides` route updates the override set | ✅ | `main_web.py:2829` |
| Service: `resolve_scenario_snapshot(base, overrides)` produces the effective snapshot | ✅ | proved in 24-H-3 |

The user can:

1. Create a Base case.
2. Click "Add Scenario" → enter a name → save.
3. Edit the new scenario's inputs.
4. Click "Save" again.
5. Click "Run Model".

**Gap (test-proven, not UX-polished):** the UI does not
expose an explicit **"Downside" / "Upside" / "Custom"**
preset. The user must invent the names themselves. There
is no "tweak from Base by ±15% tariff" one-click helper.

### 2.6 Q6 — Can a user compare scenario outputs?

**Answer: YES (UI + service-level proof).**

| Layer | Status | Evidence |
|---|---|---|
| UI: Compare tab in workspace_shell | ✅ | `app/templates/partials/workspace_shell.html:744` |
| UI: `scenario_compare.html` partial has 3 states | ✅ | empty, base-only, full compare (Base vs Active + Left vs Right) |
| UI: Metrics table with delta column | ✅ | `ps-compare-row--head` + `ps-compare-row` |
| Service: `/scenarios/compare` route | ✅ | `main_web.py:2522` |
| Service: `/compare` (POST) route | ✅ | `main_web.py:2000-2001` |
| Service: `compare_scenarios` builds 10 metric rows + 2 governance rows with delta | ✅ | `app/persistence/exports_repository.py` |

**Gap (test-proven, not UX-polished):** the compare
panel works for **2 scenarios at a time**. There is no
**3-way / 4-way compare** (Base + Downside + Upside in
a single table). A user who wants to see all three side
by side has to compare twice.

### 2.7 Q7 — Can a user export or download an exploratory package?

**Answer: YES (UI + service-level proof).**

| Layer | Status | Evidence |
|---|---|---|
| UI: Export registry partial | ✅ | `app/templates/partials/export_registry.html` |
| UI: 5+ export cards visible | ✅ | workbook, calibration, runtime, parity, gap, source, governance |
| UI: EXPLORATORY banner on export registry | ✅ | `export-explorer-warning` block |
| UI: /download route (POST + GET) | ✅ | `main_web.py:2039, 2091` |
| UI: /exports/runtime-summary.csv | ✅ | factory-only (tuho / oborovo) |
| UI: /exports/institutional-workbook.xlsx | ✅ | factory-only (tuho / oborovo) |
| Service: `build_excel_export_for_post_request` for user_created | ✅ | `app/services/export_service.py` |

**Gap (test-proven, not UX-polished):** the
runtime-summary.csv and institutional-workbook.xlsx
export routes are **factory-only** (tuho / oborovo).
A user_created generic project cannot get a
runtime-summary.csv via the dedicated route — they
must go through POST /download (which is generic-aware
and produces an XLSX). There is no "scenario name in
the filename" pattern for generic exports.

### 2.8 Q8 — Are all generic outputs clearly labeled exploratory / not validated?

**Answer: YES (UI + 3 sites + safety copy).**

| Site | Status | Evidence |
|---|---|---|
| `inputs_section.html` | ✅ | `inp-exploratory-notice` with EXPLORATORY badge + safety copy |
| `_last_run_indicator.html` | ✅ | `last-run-indicator__row--exploratory` |
| `export_registry.html` | ✅ | `export-explorer-warning` |
| `pilot_limitations_notice.html` | ✅ | Generic projects listed as "not yet validated against Excel" |
| `pilot_workflow_guide.html` | ✅ | Step 1 says "generic is exploratory only" |

The safety copy is **complete**: lender-ready /
audit-ready / bank-approved / Excel-parity / artefact /
internal sketching. The badge style is `badge-warn` (not
blocked, not convention).

**Gap (test-proven, not UX-polished):** the warnings are
**always-on for generic projects**. There is no "I've
reviewed this and accept the risk" checkbox. Some
finance users may want to dismiss the warning after
reading it.

### 2.9 Q9 — Are TUHO/Oborovo reference paths still protected?

**Answer: YES (UI + service-level proof).**

| Layer | Status | Evidence |
|---|---|---|
| UI: factory read-only notice in inputs_section | ✅ | `inp-readonly-notice` + `{% if not is_user_project %}` |
| UI: editable=False for factory projects | ✅ | `editable=is_user_project` |
| Service: `/scenarios/add` returns 403 for non-user_created | ✅ | `app/services/scenarios_add_service.py` |
| Service: factory seeded path uses `create_default_tuho_wind1` / `create_default_oborovo` | ✅ | `app/services/run_service.py` |
| Construction flag still defaults to False | ✅ | `app/waterfall_core.py` |

A user **cannot**:

- Edit a factory project's inputs.
- Add a scenario to a factory project.
- Inject a user-edited snapshot into a factory run
  (the factory path uses the canonical factory inputs,
  not the user snapshot, when `runtime_origin != "saved_state"`).
- Claim a generic export is "Reference" or "Validated"
  (the export_registry partial uses `EXPLORATORY` for
  generic projects).

### 2.10 Q10 — What still prevents this from being a fully working internal tool?

This is the **honest gap list**. Six items:

1. **No Excel-parity validation for generic projects.**
   The model is the same (proven in 24-H-2 / 24-H-3), but
   there is no comparison against an Excel reference
   workbook. The EXPLORATORY warning is the safety net.

2. **No CO2 / certificates / balancing / period-mapping
   parity.** The Oborovo and TUHO factories include CO2
   revenue, certificate revenue, balancing revenue, and
   period mapping. The generic template does not.

3. **No sculpting / live debt-sizing.** The senior debt
   schedule is fixture-backed from Excel for TUHO /
   Oborovo. A user creating a generic project gets a
   fixed-shape debt schedule, not a live
   `min_DSCR`-sized debt amount. This is **by design**
   (Phase 10 contract) but it means the IRR for a
   generic project is less realistic.

4. **No senior IDC resolution.** The IDC accrues on the
   senior balance (R-PAR-2). Generic projects use a
   simplified IDC, not the R-PAR-2 resolution.

5. **No construction runtime / C10 promotion.** Generic
   projects use the same waterfall as TUHO / Oborovo
   (which is fixture-backed). The construction schedule
   engine is unwired.

6. **No PDF export.** The current routes are CSV + XLSX
   only. A finance user who wants a "share this with a
   colleague" PDF has to convert manually.

---

## 3. What is now user-testable

The following flows are **user-testable** today (i.e., a
finance user can complete them end-to-end through the UI):

1. **Create a Generic Solar / Wind project.** ✅
   `/projects/new` → fill in 16 fields → `Create Project`.

2. **Open an existing Generic project.** ✅
   `/projects/browse` → click the project.

3. **Edit the project's inputs.** ✅
   Sidebar inputs are editable. The change is reflected
   in the runtime summary after a Run.

4. **Save a Base case.** ✅
   `Save Scenario` → enter a name → `Save`.

5. **Run the model.** ✅
   `Run Model` button → backend computes kpis.

6. **Create a Downside scenario.** ✅
   `Add Scenario` → enter "Downside" → edit tariff/opex
   lower → `Save Scenario`.

7. **Create an Upside scenario.** ✅
   `Add Scenario` → enter "Upside" → edit tariff/opex
   higher → `Save Scenario`.

8. **Run Downside / Upside.** ✅
   Switch to the scenario → `Run Model`.

9. **Compare Base vs Downside (or Base vs Upside).** ✅
   Compare tab → select two scenarios → see 10-metric
   delta table.

10. **Export / download an XLSX.** ✅
    `Download` button → XLSX with inputs + outputs +
    governance rows.

11. **See EXPLORATORY warning everywhere.** ✅
    Inputs section + run indicator + export registry.

12. **Cannot accidentally edit a factory project.** ✅
    Factory read-only notice is always visible.

13. **Cannot add a scenario to a factory project.** ✅
    `/scenarios/add` returns 403 for non-user_created.

14. **Cannot mistake generic for Reference / Validated.** ✅
    The export registry says "EXPLORATORY" (badge-warn) for
    user_created+generic. The safety copy is explicit.

---

## 4. What remains only test-proven but not UX-polished

These flows are **service-level proof only**. The user
journey requires manual / user guidance:

1. **Creating a generic project requires the user to fill
   in 16 fields from scratch.** A "Use generic defaults"
   button that pre-fills from `create_default_solar_project()`
   would be a small UX improvement.

2. **The scenario loop requires manual name invention.**
   No "Downside / Upside / Custom" preset. A dropdown
   with three presets (Downside, Upside, Custom) would
   be a small UX improvement.

3. **The compare panel supports 2 scenarios at a time.**
   A 3-way / 4-way table would be a small UX improvement.

4. **The runtime summary does not show a delta indicator.**
   "Project IRR: 11.01% (was 6.34% before this run)"
   would be a small UX improvement.

5. **The factory export routes are factory-only.** A
   user_created generic project cannot get a
   runtime-summary.csv via the dedicated route. Extending
   the factory routes to generic projects (with the
   EXPLORATORY banner carried over) would be a small
   improvement.

6. **No auto-save on dirty.** A user who edits and closes
   the browser loses the draft. An auto-save indicator
   would be a small UX improvement.

7. **The runtime summary does not show the input edits
   that drove the change.** A "what changed" badge next
   to the kpi would be a small UX improvement.

---

## 5. What still requires manual / user guidance

These flows are **not even service-level proof**. A
finance user must work around them:

1. **Generic template Excel validation.** No reference
   workbook to compare against. The user must trust the
   model.

2. **CO2 / certificates / balancing.** Generic projects
   have a flat CO2 / certificate / balancing assumption
   (or none). A user who wants realistic numbers has to
   set them manually.

3. **Sculpting / live debt-sizing.** Generic projects
   use a fixed-shape debt schedule. A user who wants
   `min_DSCR`-sized debt has to size it manually.

4. **Senior IDC.** Generic projects use a simplified IDC
   accrual. A user who wants R-PAR-2 has to model it
   manually.

5. **Construction runtime / C10.** Generic projects use
   the same waterfall as TUHO / Oborovo (fixture-backed).
   A user who wants live construction has to model it
   manually.

6. **PDF export.** No PDF route. A user who wants PDF
   has to convert XLSX → PDF manually.

---

## 6. Top remaining blockers

Ranked by **user impact × parity risk × implementation effort**:

| Rank | Blocker | User impact | Parity risk | Impl. risk | Effort |
|---|---|---|---|---|---|
| 1 | No Excel-parity validation for generic | 5 | 5 | 5 | XL |
| 2 | No CO2 / certificates / balancing parity | 4 | 4 | 3 | L |
| 3 | No sculpting / live debt-sizing | 4 | 4 | 5 | XL |
| 4 | No senior IDC resolution (R-PAR-2) | 3 | 3 | 3 | L |
| 5 | No construction runtime / C10 | 3 | 3 | 5 | XL |
| 6 | No PDF export | 2 | 0 | 1 | S |
| 7 | No auto-save on dirty | 2 | 0 | 1 | S |
| 8 | No 3-way scenario compare | 2 | 0 | 2 | M |
| 9 | No "what changed" delta indicator | 2 | 0 | 1 | S |
| 10 | No "Use generic defaults" pre-fill | 1 | 0 | 1 | S |

Items 1-5 are **out of scope for Sprint 24-H** by design
(they are R-PAR-2 / C10 / construction promotion, which
are explicitly excluded from 24-H hard constraints).

Items 6-10 are **small UX polishes** that could be done
in a future sprint without parity risk.

---

## 7. Recommended next sprint

**Phase 25B — Generic UX Polish** (recommended scope):

| Item | Effort | Sprint |
|---|---|---|
| "Use generic defaults" pre-fill button on /projects/new | S | 25B-1 |
| 3-way / 4-way scenario compare table | M | 25B-2 |
| "What changed" delta indicator in runtime summary | S | 25B-3 |
| Auto-save indicator on dirty | S | 25B-4 |
| Extend factory export routes to generic (with EXPLORATORY banner) | M | 25B-5 |
| PDF export (route + library) | M | 25B-6 |

**Out of scope** (deferred to a later sprint):

- Excel-parity validation (requires an Excel reference workbook).
- CO2 / certificates / balancing parity.
- Sculpting / live debt-sizing.
- R-PAR-2 senior IDC resolution.
- Construction runtime / C10.

**Hard constraints preserved:**

- No model / formula / tax / debt / IDC changes.
- No construction promotion.
- No C10 / R-PAR work in this sprint.
- rc1 untouched.
- TUHO / Oborovo factory paths preserved.
- All 24-H proofs preserved (29 + 55 + 53 + 58 = 195 tests).

---

## 8. Honest summary

**What Sprint 24-H achieved:** FincoGPT is now meaningfully
testable as a Generic Solar / Generic Wind exploratory
modelling tool. A finance user can:

- Create a Generic project, edit inputs, save a Base case,
  add Downside / Upside scenarios, run all three, compare
  any two, and export / download an XLSX.

**What Sprint 24-H did not achieve:** Generic outputs are
not Excel-parity validated. The senior debt schedule,
CO2 / certificates / balancing, IDC, and construction
runtime are still fixture-backed from the TUHO / Oborovo
reference. A user who treats a generic project output as
a "bank-ready" result will be misled — the EXPLORATORY
warning exists precisely to prevent that.

**What a finance user can confidently use it for today:**

- Internal screening ("if the tariff is 90 vs 130, what's
  the IRR?").
- Capacity / sizing sketches ("if we go from 50 MW to
  75 MW, what's the impact on DSCR?").
- Sensitivity tables ("if opex rises 20%, what happens
  to distributions?").

**What a finance user cannot confidently use it for today:**

- Lender / bank / external audit pack.
- Excel-parity validation.
- Live debt sculpting.
- Construction-cost sculpting.

The closure review recommends **Phase 25B — Generic UX
Polish** as the next sprint, with hard constraints
preserved (no model / formula / construction changes).

---

## 9. References

- `docs/phase24h_editable_generic_project_run_loop.md`
  (PR #573) — Phase 24-H-1 (Labeling)
- `docs/phase24h2_generic_run_loop_delta_proof.md`
  (PR #575) — Phase 24-H-2 (Delta Proof)
- `docs/phase24h3_generic_scenario_loop_compare.md`
  (PR #578) — Phase 24-H-3 (Scenario Loop + Compare)
- `docs/phase24h4_generic_export_download_pack.md`
  (PR #580) — Phase 24-H-4 (Export / Download Pack)
- `docs/phase24g_closure_and_pilot_testability_review.md`
  (PR #572) — G-track closure review (sprint planning input)
- `docs/pilot_ux_walkthrough_checklist.md` — walkthrough anchor
- `docs/pilot_user_guide.md` — user guide
- `app/templates/partials/pilot_workflow_guide.html` — 7-step
  workflow stepper (Phase 25A)
- `app/templates/partials/pilot_limitations_notice.html` —
  4-limitation notice (Phase 25A)
- `app/templates/partials/scenario_compare.html` — compare
  panel (3 states)
- `app/templates/partials/inputs_section.html` — 24-H
  warning + factory read-only notice
- `app/templates/partials/_last_run_indicator.html` — 24-H
  warning
- `app/templates/partials/export_registry.html` — 24-H
  warning + 5+ export cards
- `app/persistence/scenarios_repository.py` —
  `resolve_scenario_snapshot`
- `app/persistence/exports_repository.py` —
  `compare_scenarios`
- `app/persistence/_helpers.py` — `_metric_value`,
  `_safe_number`
- `app/services/scenarios_add_service.py` —
  `execute_scenarios_add_route` (user_created gate)
- `app/services/scenarios_save_service.py` —
  `execute_scenarios_save_route`
- `app/services/scenarios_duplicate_service.py` —
  `execute_scenario_duplicate_route`
- `app/services/scenario_update_overrides_service.py` —
  `execute_scenario_update_overrides_route`
- `app/services/download_service.py` — POST /download
  orchestration
- `app/services/export_audit_service.py` — `record_*_export`
  audit wrappers
- `app/services/run_service.py` —
  `_execute_user_created_path` (Phase 17C snapshot
  binding, Phase 51B refactor)
- `app/services/projects_create_service.py` —
  `execute_projects_create_route`
- `app/input_adapter.py` — `build_projectinputs_from_snapshot`
- `app/api/project_runner.py` — `run_project`
- `app/project_factories.py` — `create_default_tuho_wind1`,
  `create_default_oborovo`
- `app/waterfall_core.py` — pre-existing
  `use_construction_schedule_engine` gate (default `False`)
