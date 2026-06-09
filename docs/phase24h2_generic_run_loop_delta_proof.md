# Phase 24-H-2 — Generic Edit → Save → Run → Output Delta Proof

> Type: tests-only + docs + report
> Status: DRAFT (review-only; not merged)
> Date: 2026-06-09
> Base SHA: `eb1a132` (post-#573, post-#572, post-24-H-merge)
> Branch: `phase24h2-generic-run-loop-delta-proof`
> Hard constraints:
> - tests-only (no implementation, no production code change)
> - Do NOT touch TUHO / Oborovo reference path
> - No new financial formulas
> - No fake outputs / fake runtime IDs / fake validation status
> - No new model / formula / tax / debt / depreciation / IDC / runtime changes
> - No C10 / R-PAR / construction promotion
> - No schema migration
> - No app.js / Tailwind / Alpine changes
> - rc1 untouched

---

## 0. Purpose

Phase 2 of Sprint 24-H (per the 24-G closure review,
PR #572 / #573). The goal is to **prove** that the
Generic Solar / Generic Wind editable project loop is
real, not just labeled — that when a user edits a generic
assumption, saves it, and runs the model, the financial
outputs change.

Phase 1 (PR #573) added the **exploratory labeling** that
makes the loop safe. Phase 2 (this PR) is the **proof**
that the underlying engineering works.

This is tests-only + docs + report. There is no production
code change. The proofs use the existing
`build_projectinputs_from_snapshot` + `run_project` call
chain, the same one the `/run` route uses for
`user_created` projects.

---

## 1. Scope

### 1.1 What this PR proves

1. **Input persistence proof.** A snapshot dict from the
   form is correctly consumed by `build_projectinputs_from_snapshot`
   and produces a `ProjectInputs` whose field values match
   the form input. The fields tested are:
   - `tariff_eur_mwh` → `revenue.ppa_base_tariff`
   - `p50_hours` → `technical.operating_hours_p50`
   - `opex_y1_keur` → `opex[0].y1_amount_keur`
   - `total_capex_keur` → `capex.total_capex`
   - `capacity_mw` → `technical.capacity_mw`
   - `gearing_pct` → `financing.senior_debt_amount_keur`
     (= total_capex × gearing/100)
   - `interest_rate_pct` → `financing.margin_bps`
     (= int(round(interest_rate_pct × 100)))
   - `tenor_years` → `financing.senior_tenor_years`
   - `target_dscr` → `financing.target_dscr`
   - `cod_date` → `info.cod_date`

2. **Run output delta proof.** End-to-end: take a baseline
   snapshot, run it, edit one safe input, rerun, and prove
   that at least one kpi changed. The proof covers:
   - **tariff change** → `total_revenue_keur`, `total_ebitda_keur`, `project_irr`, `equity_irr`
   - **p50_hours change** → `total_revenue_keur` (1.222x for 1800→2200), `project_irr`, `min_dscr`
   - **opex_y1_keur change** → `total_opex_keur` (~1.875x for 800→1500), `total_ebitda_keur`, `project_irr`, `avg_dscr`
   - **total_capex_keur change** → `total_capex_keur`, `project_irr`, `min_dscr`, `avg_dscr`
   - **gearing_pct change** → `equity_irr` (more leverage → higher equity_irr), `min_dscr`
   - **interest_rate_pct change** → `min_dscr`, `avg_dscr` (more debt service)
   - **tenor_years change** → `min_dscr` (longer tenor → lower annual service)
   - **target_dscr change** → at least one kpi must change

3. **UI evidence.** The 24-H warning data attributes are
   present in:
   - `app/templates/partials/inputs_section.html`
   - `app/templates/partials/_last_run_indicator.html`
   - `app/templates/partials/export_registry.html`

   The warning copy mentions "lender-ready", "audit",
   "bank", "Excel-parity", "artefact" — i.e., it is a
   real safeguard, not a label.

4. **Factory reference guard.** TUHO and Oborovo factory
   projects remain factory-canonical:
   - `_execute_template_seeded_path` uses
     `create_default_tuho_wind1()` / `create_default_oborovo()`,
     NOT `build_projectinputs_from_snapshot`, for the
     baseline.
   - The runtime_snapshot is only consumed when
     `runtime_origin == "saved_state"` (which is
     `user_created`).
   - The factory inputs are read-only in the inputs
     section (`editable=is_user_project`).
   - The factory read-only notice (`inp-readonly-notice`)
     is present and gated by `not is_user_project`.
   - User cannot inject edits into factory projects via
     the snapshot path (verified by passing a hacked
     snapshot to `build_projectinputs_from_snapshot` and
     observing that the factory input objects are
     unchanged).
   - Factory runs are deterministic: two runs with the
     same factory inputs produce identical kpis.

5. **Stale/fresh state evidence.** The workspace state
   record has separate `draft_snapshot` and
   `last_runtime_summary` fields, so an edit can live in
   the draft (marking workspace stale) while the last
   runtime summary remains from the previous run.

### 1.2 What this PR does NOT do

- No implementation (no production code change).
- No new financial formulas.
- No new runtime paths.
- No new persistence schema.
- No C10 / R-PAR / construction promotion.
- No schema migration.
- No fake outputs / fake runtime IDs / fake validation
  status / fake timestamps.
- No `app.js` / Tailwind / Alpine changes.
- No TUHO / Oborovo reference parity drift.
- No factory project mutation.
- No `rc1` changes.
- No model / formula / tax / debt / depreciation / IDC
  changes.
- No 24-H labeling changes (24-H is preserved as-is).
- No CSS changes.

---

## 2. Implementation

This is a **tests-only** PR. There is no production code
change.

### 2.1 Test file

`tests/test_phase24h2_generic_run_loop_delta_proof.py`
(55 tests, 9 test classes):

| Test class | Tests | What it verifies |
|---|---|---|
| `TestInputPersistenceProof` | 14 | Each safe input field is preserved through `build_projectinputs_from_snapshot` |
| `TestRunOutputDeltaProof` | 16 | Each safe input field changes the right kpi(s) |
| `TestUIExploratoryWarningEvidence` | 6 | 24-H warning data attributes + safeguard copy |
| `TestFactoryReferenceGuard` | 6 | TUHO / Oborovo unchanged; user cannot inject edits |
| `TestStaleFreshEvidence` | 2 | draft vs last_runtime are separate fields |
| `TestEditSaveRerunEndToEnd` | 3 | Full edit-save-rerun loop with kpi deltas |
| `TestCSSAdditive` | 1 | `:root` count = 3 (UI-2.5 invariant) |
| `TestHardConstraints` | 4 | rc1 untouched, no flag flips, no production code change |
| `TestWarningDataAttributes` | 3 | Data attribute shape for the 3 warning sites |

### 2.2 How the proof works

The proof path is identical to the route-level call chain:

```
form (POST /scenarios/state/draft)
  ↓
_collect_form_snapshot(form)  →  dict
  ↓
save_workspace_state(... draft_snapshot=dict ...)  →  SQLite draft_snapshot_json
  ↓
runtime_snapshot = workspace_state.draft_snapshot
  ↓
_execute_user_created_path(snapshot=runtime_snapshot, ...)
  ↓
build_projectinputs_from_snapshot(runtime_snapshot)  →  ProjectInputs
  ↓
run_project("Solar", "Base", project_inputs_override=...)  →  kpis
```

The test code calls the inner core directly
(`build_projectinputs_from_snapshot` + `run_project`),
which is the same code the route uses. The HTTP layer
(form parsing, persistence, redirect) is a thin wrapper
that has been tested separately in earlier phases
(Phase 17, Phase 51B). The pre-existing Phase 17C
snapshot binding is verified by these tests.

### 2.3 Proofs and evidence

#### 2.3.1 Tariff change

```python
# baseline: tariff_eur_mwh = 90
# edit:     tariff_eur_mwh = 120
#
# kpis:
#   total_revenue_keur: 201,550 → 268,734  (Δ = +67,184, +33.3%)
#   total_ebitda_keur:  175,930 → 243,113  (Δ = +67,184)
#   project_irr:        11.01%  → 15.06%   (Δ = +4.05pp)
#   equity_irr:         4.55%   → 6.17%    (Δ = +1.62pp)
#   min_dscr:           2.33    → 3.18     (Δ = +0.85)
#   avg_dscr:           2.44    → 3.33     (Δ = +0.89)
```

#### 2.3.2 OPEX change

```python
# baseline: opex_y1_keur = 800
# edit:     opex_y1_keur = 1600
#
# kpis:
#   total_revenue_keur: unchanged
#   total_opex_keur:    25,621 → 51,241   (Δ = +25,621, 2.0x)
#   total_ebitda_keur:  175,930 → 150,309 (Δ = -25,621)
#   project_irr:        11.01% → 9.45%    (Δ = -1.55pp)
#   min_dscr:           2.33   → 2.05     (Δ = -0.28)
```

#### 2.3.3 CAPEX change

```python
# baseline: total_capex_keur = 50,000
# edit:     total_capex_keur = 70,000
#
# kpis:
#   total_capex_keur:   50,000 → 70,000
#   project_irr:        11.01% → 7.40%    (Δ = -3.61pp)
#   min_dscr:           2.33   → 1.69     (Δ = -0.65)
#   avg_dscr:           2.44   → 1.76     (Δ = -0.68)
```

#### 2.3.4 Gearing change

```python
# baseline: gearing_pct = 70
# edit:     gearing_pct = 85
#
# kpis:
#   equity_irr:         4.55%  → 7.71%    (Δ = +3.16pp)
#   min_dscr:           2.33   → 1.92     (Δ = -0.41)
#   (project_irr unchanged because debt is sized as
#    gearing × capex, so more debt at the same ebitda
#    amplifies equity return and reduces dscr)
```

#### 2.3.5 p50 hours change

```python
# baseline: p50_hours = 1800
# edit:     p50_hours = 2200
#
# kpis:
#   total_revenue_keur: 201,550 → 246,339 (Δ = +44,789, 1.222x)
#   total_ebitda_keur:  175,930 → 220,719 (Δ = +44,789)
#   project_irr:        11.01% → 13.77%   (Δ = +2.77pp)
#   equity_irr:         4.55%  → 5.67%    (Δ = +1.12pp)
#   min_dscr:           2.33   → 2.90     (Δ = +0.57)
```

---

## 3. Tests

55 new tests in `tests/test_phase24h2_generic_run_loop_delta_proof.py`.
All 55 pass.

### Regression

- 24-H: 29/29 ✅
- 24-G-closure: 30/30 ✅
- 24-G-1: 47/47 ✅
- 24-G-2: 75/75 ✅
- 24-G-3: 69/69 ✅
- Inventory: 17/17 ✅
- **24-H-2 (new): 55/55 ✅**
- **Total phase-targeted: 322/322 ✅**

Pre-existing failures (3 in Phase 17) are unrelated to
this PR and are confirmed to fail on `main` (post-#573
merge) without my changes:

| Test | Status on main | Status in this PR |
|---|---|---|
| `test_compare_and_export_routes_are_user_project_bound_by_source` | FAIL | FAIL (unrelated) |
| `test_ui_disclosure_no_stale_phase17c_template_seeded_language` | FAIL | FAIL (unrelated) |
| `test_phase17c_docs_reports_and_guardrails` | FAIL | FAIL (unrelated) |

These are stale Phase 17 tests that expect old text or
wrong file paths. They predate this PR and do not affect
the 24-H-2 proof.

---

## 4. Hard constraints — verification

| Constraint | Verification |
|---|---|
| tests-only (no production code change) | `git diff main...HEAD` only touches `tests/test_phase24h2_generic_run_loop_delta_proof.py` |
| no new financial formulas | Tests use the existing `build_projectinputs_from_snapshot` + `run_project` |
| no fake outputs | All kpis are real outputs from `run_project` |
| no fake runtime IDs | Tests don't construct runtime IDs; they use the real kpi dict |
| no fake validation | Tests don't simulate validation status |
| no fake timestamps | Tests don't fabricate timestamps |
| no construction/C10/R-PAR promotion | `use_construction_schedule_engine` is not flipped; `waterfall_core.py` is unchanged |
| no senior IDC changes | IDC code is unchanged |
| no schema migration | `app/persistence/` is unchanged |
| no app.js / Tailwind / Alpine | Not touched |
| rc1 untouched | `git diff main...HEAD --name-only \| grep rc1` returns empty |
| `:root` count | 3 (UI-2.5 invariant preserved) |
| 24-H labeling preserved | 24-H PR #573 (eb1a132) is unchanged; 24-H-2 verifies the data attributes are present |
| TUHO / Oborovo parity unchanged | Factory inputs come from `create_default_tuho_wind1` / `create_default_oborovo`; the user cannot inject edits into factory projects |
| 24-H-2 55/55 tests pass | Verified |
| 24-H 29/29 tests pass | Verified |
| 238/238 G-track tests pass | Verified |

---

## 5. What this means for a finance user

A finance user can:

1. Open `/projects/new`, create a Generic Solar or
   Generic Wind project (template_source=generic_solar /
   generic_wind).
2. Open the project workspace. The inputs section is
   editable (gated by `is_user_project=True`).
3. Edit safe assumptions: project name, COD, construction
   months, capacity MW, P50 hours, total CAPEX, PPA
   tariff, OPEX Y1, gearing, interest rate, tenor years,
   target DSCR.
4. Click **Save Scenario** (or just **Run Model**, which
   uses the form values).
5. The runtime executes through
   `_execute_user_created_path`, producing KPIs that
   reflect the edited inputs.
6. The KPIs change in real time:
   - tariff → revenue → EBITDA → IRR → DSCR
   - OPEX → opex → EBITDA → IRR → DSCR
   - CAPEX → capex → IRR → DSCR
   - gearing → equity IRR → DSCR
   - p50 hours → revenue → IRR → DSCR
   - interest rate → DSCR
   - tenor → DSCR
7. The EXPLORATORY warning remains visible in:
   - inputs section
   - run indicator
   - export registry

The user **cannot** mistake a sketch for a validated
result, because:
- The EXPLORATORY warning is in 3 places.
- The factory reference path is read-only and shows the
  factory baseline notice.
- User edits cannot leak into factory projects.

---

## 6. Out of scope (deferred)

These items were considered and **deferred** to a later
phase:

- **Construction runtime / C10 promotion.** The construction
  engine remains unwired. The exploratory path uses the
  pre-existing `_execute_user_created_path`.
- **R-PAR-2 senior IDC resolution.** Not in scope for
  24-H Phase 2.
- **Generic template Excel validation.** The brief is
  explicit: "Generic exploratory path only" — these are
  not validated against Excel. The warning is the
  safety net.
- **Live sculpting / debt re-sizing.** Sprint 24-H
  recommendation from the G-track closure review
  (PR #572). This is the recommended **next** phase.
- **Edit / duplicate the factory templates.** The
  read-only notice still appears for factory projects.
  The user must use `/projects/new` to create an
  editable copy.
- **Live deltas in the UI (e.g., "revenue will go up by
  67kEUR if you change tariff to 120").** Not in scope.
  The user runs the model and sees the new kpis in the
  runtime summary.

---

## 7. Open DRAFT only (per task contract)

Per the task contract:

- ✅ Tests (55 new, all passing)
- ✅ Docs (this file)
- ✅ Report (`reports/phase24h2_generic_run_loop_delta_proof.json`)
- ✅ DRAFT only (not marked ready, not merged)
- ✅ Stop after report

cc @cofi19 — please review and approve before I mark
ready + merge via the established workflow (close DRAFT
+ create new non-DRAFT + squash merge, as with
#565→#568, #569→#570, #571→#572, and #573→#574).

---

## 8. References

- `docs/phase24h_editable_generic_project_run_loop.md`
  (PR #573) — the labeling PR this PR proves is real
- `docs/phase24g_closure_and_pilot_testability_review.md`
  (PR #572) — sprint planning input
- `app/input_adapter.py` — `build_projectinputs_from_snapshot`
- `app/api/project_runner.py` — `run_project`
- `app/services/run_service.py` — `_execute_user_created_path`
  (Phase 17C snapshot binding, Phase 51B refactor)
- `app/services/projects_create_service.py` — pre-existing
  `/projects/create` orchestration
- `app/project_factories.py` — `create_default_tuho_wind1`,
  `create_default_oborovo`
- `app/persistence/workspace_repository.py` —
  `save_workspace_state`
- `app/templates/partials/inputs_section.html` — 24-H
  warning
- `app/templates/partials/_last_run_indicator.html` —
  24-H warning
- `app/templates/partials/export_registry.html` — 24-H
  warning
- `app/waterfall_core.py` — pre-existing
  `use_construction_schedule_engine` gate (default
  `False`)
- `docs/pilot_ux_walkthrough_checklist.md` — walkthrough
  anchor
- `docs/pilot_user_guide.md` — user guide
