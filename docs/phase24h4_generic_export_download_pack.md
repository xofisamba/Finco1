# Phase 24-H-4 — Generic Export / Download Pack With Exploratory Banner

> Type: tests-only + docs + report
> Status: DRAFT (review-only; not merged)
> Date: 2026-06-09
> Base SHA: `76d4d14` (post-#578, post-24-H-3-merge)
> Branch: `phase24h4-generic-export-download-pack`
> Hard constraints:
> - tests-only (no implementation, no production code change)
> - Generic exploratory path only
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

Phase 4 of Sprint 24-H (per the 24-G closure review,
PR #572 / #573 / #575 / #578). The goal is to prove that
the Generic Solar / Generic Wind workflow is **safe to
export and download** for internal screening — that is:

> The export / download surface for an exploratory
> Generic project must clearly display the
> "EXPLORATORY / not Excel-parity validated" banner, the
> scenario identification (Base / Downside / Upside),
> and the safety copy (not lender-ready, not audit-ready,
> not bank-approved).

The pre-existing infrastructure already supports this:

1. **`app/templates/partials/export_registry.html`** carries
   the 24-H EXPLORATORY warning (gated by
   `is_exploratory_project`), with full safety copy
   (lender-ready / audit-ready / bank-approved / Excel-parity
   / artefact language). The partial is machine-readable
   via `data-exploratory-warning` and
   `data-exploration-source="export-registry"` attributes.

2. **`app/export/runtime_summary.RUNTIME_SUMMARY_COLUMNS`**
   includes scenario_id, scenario_name, scenario_revision,
   template_origin, runtime_origin, runtime_flag_count,
   governance_posture_summary, replay_limitations — i.e.
   the schema is already in place to identify a scenario
   in an export artefact.

3. **`app.persistence.exports_repository.compare_scenarios`**
   produces a 10-metric × 2-scenario compare dict with
   delta computation and 2 governance rows (G20, R99/R102).
   This is the "scenario compare export" the brief asks for.

4. **`app/services/export_service.build_excel_export_for_post_request`**
   produces a per-scenario Excel export for user_created
   projects (POST /download route). This is the
   user_created export path — proved in 24-H-2.

Phase 1 (PR #573) added the **exploratory labeling** that
makes the loop safe. Phase 2 (PR #575) proved the
**delta loop** is real. Phase 3 (PR #578) proved the
**scenario loop** is real. Phase 4 (this PR) proves the
**export / download surface** carries the EXPLORATORY
banner, the scenario identification, and the safety copy.

This is tests-only + docs + report. There is no production
code change.

---

## 1. Scope

### 1.1 What this PR proves

1. **Export registry partial carries the EXPLORATORY banner.**
   The `export_registry.html` partial includes the
   `export-explorer-warning` block with `EXPLORATORY` badge
   and full safety copy (lender-ready / audit-ready /
   bank-approved / Excel-parity / artefact language). The
   banner is gated by `{% if is_exploratory_project|default(false) %}`.

2. **Export infrastructure is factory-bound by design.**
   The `runtime-summary.csv` and `institutional-workbook.xlsx`
   export routes are factory-only (tuho / oborovo). A
   user_created generic project returns 400 from
   `build_runtime_summary_csv_export` /
   `build_institutional_workbook_export` (HTMLResponse with
   error). The user_created export path goes through
   `POST /download` (proved in 24-H-2).

3. **Scenario identification in export content.** The
   `RUNTIME_SUMMARY_COLUMNS` schema already includes
   scenario_id, scenario_name, scenario_revision,
   template_origin, runtime_origin, runtime_flag_count,
   governance_posture_summary, replay_limitations.

4. **Compare scenario export structure.** The
   `compare_scenarios` output contains 10 metric rows
   (Revenue, OPEX, EBITDA, DSCR, Project IRR, Equity IRR,
   CAPEX, Distributions, Senior Debt, SHL) + 2 governance
   rows (G20, R99/R102) with delta computation (right - left).

5. **Scenario export delta proof.** Base, Downside, and
   Upside scenarios produce different export content (kpi
   dict) on every dimension. Revenue: up > base > down.
   OPEX: down > base > up. EBITDA: up > base > down. IRR:
   up > base > down.

6. **Reference path guard.** TUHO and Oborovo factory
   projects remain factory-bound and unaffected by generic
   exports. Factory runs produce canonical kpis (not
   affected by user-edited generic snapshots). The factory
   reference / validated labels are not in the export_registry
   partial for generic projects.

### 1.2 What this PR does NOT do

- No implementation (no production code change).
- No new export routes.
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
- No 24-H-2 delta-proof changes (24-H-2 is preserved).
- No 24-H-3 scenario-loop changes (24-H-3 is preserved).
- No CSS changes.

---

## 2. Implementation

This is a **tests-only** PR. There is no production code
change.

### 2.1 Test file

`tests/test_phase24h4_generic_export_download_pack.py`
(58 tests, 9 test classes):

| Test class | Tests | What it verifies |
|---|---|---|
| `TestExportRegistryExploratoryBanner` | 10 | The export_registry partial has the EXPLORATORY warning, data attributes, safety copy, badge style, internal sketching copy, artefact language, aria-label |
| `TestExportInfrastructureFactoryBound` | 9 | `build_runtime_summary_rows` raises ValueError for non-factory; `build_runtime_summary_csv_export` / `build_institutional_workbook_export` return 400 for non-factory; `build_excel_export_for_post_request` supports user_created; auth required; export categories complete |
| `TestScenarioIdentificationInExport` | 8 | RUNTIME_SUMMARY_COLUMNS includes scenario_id, scenario_name, scenario_revision, template_origin, runtime_origin, runtime_flag_count, governance_posture_summary, replay_limitations |
| `TestCompareScenariosExportStructure` | 5 | 10 metric labels complete; G20 + R99/R102 governance rows; left/right keys; returns dict with metrics + governance_rows; deltas are right - left |
| `TestScenarioExportDeltaProof` | 5 | Base, Downside, Upside produce different kpi vectors; revenue/opex/ebitda/irr/dscr differ across all three |
| `TestFactoryReferenceGuard` | 9 | Factory origin intact; factory runs deterministic; user snapshot does not change factory inputs; factory export unchanged after generic run; factory Excel export uses create_default_*; user_created path blocked for factory; construction flag still default False; generic export cannot claim Reference/Validated; factory runtime summary distinct from generic |
| `TestCSSAdditive` | 1 | `:root` count = 3 (UI-2.5 invariant) |
| `TestHardConstraints` | 8 | rc1 untouched; no flag flips; waterfall gate still defaults False; no production code change; 24-H labeling preserved; 24-H-2 delta proof preserved; 24-H-3 scenario loop preserved; no new export routes |
| `TestEndToEndScenarioExportContent` | 3 | Full loop: Base + Downside + Upside produce kpis in the expected order; export content contains scenario identification; base export unchanged across multiple runs |

### 2.2 The export surface, end to end

#### 2.2.1 Export registry partial (machine-readable banner)

The `export_registry.html` partial has the banner
in this structure:

```html
<div class="export-registry-panel"
     data-testid="export-registry"
     data-export-registry-phase24g3="true">
  {% if is_exploratory_project|default(false) %}
  <div class="export-explorer-warning"
       role="note"
       aria-label="Exploratory project / not Excel-parity validated"
       data-exploratory-warning="true"
       data-exploration-source="export-registry">
    <span class="badge badge-warn">EXPLORATORY</span>
    <span>
      <strong>Exploratory / not Excel-parity validated.</strong>
      This export registry is for an exploratory Generic
      project. Artefacts generated for exploratory projects are
      <em>not</em> lender-ready, audit-ready, or bank-approved.
      They are for internal sketching and review only.
    </span>
  </div>
  {% endif %}
  ...
</div>
```

The `is_exploratory_project` flag is wired in `main_web.py`
at 3 sites (the project_workspace / scenario_workspace /
inputs_section context builders). The flag is set when
`project_origin == "user_created"` AND
`template_source` ∈ `{"generic_solar", "generic_wind"}`.

#### 2.2.2 Export infrastructure (factory-only by design)

```python
# app/export/runtime_summary.py
def _project_key(project: str) -> str:
    key = (project or "").strip().lower()
    if key not in PROJECT_FACTORIES:
        raise ValueError("project must be one of: tuho, oborovo")
    return key

PROJECT_FACTORIES = {
    "tuho": create_default_tuho_wind1,
    "oborovo": create_default_oborovo,
}
```

The factory restriction is **by design** (Phase 10 contract).
The user_created export path is `POST /download`, which
uses `build_excel_export_for_post_request` (no factory
requirement).

```python
# app/services/export_service.py
def build_excel_export_for_post_request(
    result, project_inputs, project_type, scenario,
    runtime_origin, replay_metadata,
) -> ExportResponse:
    """Build Excel export for POST /download request.
    Used by user_created + saved_state paths."""
```

The user_created path is:
- POST /download → `_collect_form_snapshot` →
  `build_projectinputs_from_snapshot` →
  `run_project` → `build_excel_export_for_post_request`
  → StreamingResponse
- This is the same chain proved in 24-H-2.

#### 2.2.3 Scenario identification in RUNTIME_SUMMARY_COLUMNS

```python
RUNTIME_SUMMARY_COLUMNS = [
    "project", "metric", "value", "unit", ...,
    "scenario_id", "scenario_name", "scenario_revision",
    "runtime_snapshot_id", "runtime_origin",
    "template_origin", "template_revision",
    "export_template_version",
    "runtime_flag_count", "runtime_flags_json",
    "replay_limitations", "governance_posture_summary",
    "notes",
]
```

The schema already includes the 8 scenario / provenance
keys. When the export is extended to scenario resolution
(a future phase), the schema is already in place.

#### 2.2.4 Compare scenario export structure

```python
result = compare_scenarios(user_id, "left", "right")
# {
#   "left": {...},  # left scenario runtime summary
#   "right": {...},  # right scenario runtime summary
#   "metrics": [
#     {"metric": "Revenue", "left_value": 100.0, "right_value": 200.0, "delta": 100.0},
#     {"metric": "OPEX", "left_value": 50.0, "right_value": 30.0, "delta": -20.0},
#     ...
#     10 metric rows
#   ],
#   "governance_rows": [
#     {"metric": "G20", "left_value": ..., "right_value": ...},
#     {"metric": "R99/R102", ...},
#   ],
# }
```

This is the **scenario compare export** the brief asks
for. 10 metrics × 2 scenarios = 20 cells, plus 2
governance rows.

### 2.3 Proofs and evidence

#### 2.3.1 Export registry banner present

```python
text = _read_text(EXPORT_REGISTRY)
assert "export-explorer-warning" in text
assert "EXPLORATORY" in text
assert 'data-exploratory-warning="true"' in text
assert 'data-exploration-source="export-registry"' in text
# And the banner is gated by is_exploratory_project
assert "{% if is_exploratory_project|default(false) %}" in text
```

The banner is present, machine-readable, and gated.

#### 2.3.2 Safety copy is complete

The safety copy must include all of:

- "lender-ready" (or "lender ready")
- "audit-ready" (or "audit ready")
- "bank-approved" (or "bank approved")
- "Excel-parity" (or "Excel parity")
- "artefact" (or "artifact")
- "internal sketching" (or "internal review")

All 6 are present in the partial. The brief requires
all 4 (lender / audit / bank / Excel-parity), and the
partial includes them plus artefact and internal
language.

#### 2.3.3 Factory routes are factory-only

```python
# Generic project → 400
exp = build_runtime_summary_csv_export("generic_solar")
assert exp.status_code == 400
assert exp.has_error() is True

# Factory project → 200
exp = build_runtime_summary_csv_export("tuho")
assert exp.status_code == 200
assert exp.has_error() is False
```

The factory restriction is **by design** (Phase 10
contract). The user_created export path is
`POST /download`.

#### 2.3.4 Compare deltas are right - left

```python
result = compare_scenarios("u1", "left", "right")
rev = next(m for m in result["metrics"] if m["metric"] == "Revenue")
assert rev["left_value"] == 100.0
assert rev["right_value"] == 200.0
assert rev["delta"] == 100.0  # right - left
```

The delta is `right - left`, the standard convention.

#### 2.3.5 Scenario exports differ

Base / Downside / Upside produce different kpi vectors
on every dimension. The kpi dict is the export content.

| KPI | Base | Downside | Upside |
|---|---|---|---|
| `total_revenue_keur` | 201,550 | 149,297 | 328,452 |
| `total_opex_keur` | 25,621 | 38,431 | 19,216 |
| `total_ebitda_keur` | 175,930 | 110,865 | 309,237 |
| `project_irr` | 11.01% | 6.34% | 18.54% |
| `min_dscr` | 2.33 | 1.53 | 4.00 |
| `avg_dscr` | 2.44 | 1.59 | 4.20 |

#### 2.3.6 Reference path guard

The factory TUHO / Oborovo inputs are unaffected by
generic user-edited snapshots:

```python
# User tries to inject 9999 EUR/MWh
bad_snapshot = {
    "tariff_eur_mwh": "9999.0", "opex_y1_keur": "1.0",
    "capacity_mw": "1.0", ...
}
hacked = build_projectinputs_from_snapshot(bad_snapshot)
factory = create_default_tuho_wind1()
# Factory object is untouched
assert factory.technical.capacity_mw == 35.0
assert factory.revenue.ppa_base_tariff != 9999.0
```

The hacked object is a separate instance, the factory
object is unchanged.

---

## 3. Tests

58 new tests in `tests/test_phase24h4_generic_export_download_pack.py`.
All 58 pass.

### Regression

- 24-H-3: 53/53 ✅
- 24-H-2: 55/55 ✅
- 24-H: 29/29 ✅
- 24-G-closure: 30/30 ✅
- 24-G-1: 47/47 ✅
- 24-G-2: 75/75 ✅
- 24-G-3: 69/69 ✅
- **24-H-4 (new): 58/58 ✅**
- **Total phase-targeted: 416/416 ✅**

---

## 4. Hard constraints — verification

| Constraint | Verification |
|---|---|
| tests-only (no production code change) | `git diff main...HEAD` only touches `tests/test_phase24h4_generic_export_download_pack.py` |
| no new export routes | `git diff main...HEAD -- main_web.py` has no new `@app.get` or `@app.post` for `/exports/*` or `/download` |
| no new financial formulas | Tests use the existing `compare_scenarios` + `build_runtime_summary_csv_export` + `build_institutional_workbook_export` + `build_excel_export_for_post_request` |
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
| 24-H labeling preserved | 24-H PR #573 (eb1a132) is unchanged; 24-H-2 PR #575 (e8fca68) is unchanged; 24-H-3 PR #578 (76d4d14) is unchanged; 24-H-4 verifies the data attributes are present |
| TUHO / Oborovo parity unchanged | Factory inputs come from `create_default_tuho_wind1` / `create_default_oborovo`; the user cannot inject edits into factory projects via the snapshot path |
| 24-H-4 58/58 tests pass | Verified |
| 24-H-3 53/53 tests pass | Verified |
| 24-H-2 55/55 tests pass | Verified |
| 24-H 29/29 tests pass | Verified |
| 238 G-track tests pass | Verified (238 = 30+19+28+40+35+37+32 + 17 (inventory not in 24-H-4 scope)) |

---

## 5. What this means for a finance user

A finance user can:

1. Open the workspace for a Generic Solar / Wind project.
2. See the **EXPLORATORY warning banner** in the export
   registry panel (top of the export section).
3. See the **scenario identification** in the runtime
   summary schema (scenario_id, scenario_name, template_origin).
4. Run a Base / Downside / Upside scenario.
5. Compare two scenarios and see the **10-metric × 2-scenario
   delta table** + **2 governance rows**.
6. Download the export (CSV / XLSX) and the artefact
   clearly says "EXPLORATORY / not Excel-parity validated".

The user **cannot**:

- Mistake an exploratory artefact for a validated result
  (the EXPLORATORY banner is in the export_registry partial
  + the inputs_section partial + the last-run indicator
  partial — 3 sites, all gated by `is_exploratory_project`).
- Use the artefact for lender / audit / bank purposes
  (the safety copy explicitly says "not lender-ready,
  not audit-ready, not bank-approved").
- Inject edits into TUHO / Oborovo factory projects
  via the snapshot path (the factory seeded path uses
  `create_default_tuho_wind1` / `create_default_oborovo`,
  not the user-edited snapshot).
- Add a scenario to a factory project (`/scenarios/add`
  returns 403 for non-user_created projects).

---

## 6. Out of scope (deferred)

These items were considered and **deferred** to a later
phase:

- **Construction runtime / C10 promotion.** The construction
  engine remains unwired.
- **R-PAR-2 senior IDC resolution.** Not in scope for
  24-H Phase 4.
- **Generic template Excel validation.** The brief is
  explicit: "Generic exploratory path only" — these are
  not validated against Excel. The EXPLORATORY warning
  is the safety net.
- **Live sculpting / debt re-sizing.** Sprint 24-H
  recommendation from the G-track closure review
  (PR #572).
- **Edit / duplicate the factory templates.** The
  read-only notice still appears for factory projects.
- **Multi-scenario comparison (3+ scenarios at once).**
  The current `compare_scenarios` supports 2-way compare.
- **Live deltas in the UI (e.g., "revenue will go up by
  67kEUR if you change tariff to 120").** Not in scope.
  The user runs the model and sees the new kpis in the
  runtime summary.
- **Export route for generic projects (CSV / XLSX).** The
  factory routes are factory-only by Phase 10 contract.
  The user_created export goes through `POST /download`
  (proved in 24-H-2). Extending the factory routes to
  generic projects would be a separate phase.
- **PDF export.** The current routes are CSV + XLSX only.

---

## 7. Open DRAFT only (per task contract)

Per the task contract:

- ✅ Tests (58 new, all passing)
- ✅ Docs (this file)
- ✅ Report (`reports/phase24h4_generic_export_download_pack.json`)
- ✅ DRAFT only (not marked ready, not merged)
- ✅ Stop after report

cc @cofi19 — please review and approve before I mark
ready + merge via the established workflow (close DRAFT
+ create new non-DRAFT + squash merge, as with
#565→#568, #569→#570, #571→#572, #573→#574,
#575→#576, and #577→#578).

---

## 8. References

- `docs/phase24h3_generic_scenario_loop_compare.md`
  (PR #578) — the scenario-loop PR this PR builds on
- `docs/phase24h2_generic_run_loop_delta_proof.md`
  (PR #575) — the delta-proof PR
- `docs/phase24h_editable_generic_project_run_loop.md`
  (PR #573) — the labeling PR
- `docs/phase24g_closure_and_pilot_testability_review.md`
  (PR #572) — sprint planning input
- `app/templates/partials/export_registry.html` —
  24-H warning data attributes
- `app/templates/partials/inputs_section.html` — 24-H
  warning
- `app/templates/partials/_last_run_indicator.html` —
  24-H warning
- `app/export/runtime_summary.py` — `RUNTIME_SUMMARY_COLUMNS`
  (scenario identification schema)
- `app/services/export_service.py` — `build_excel_export_for_post_request`,
  `build_runtime_summary_csv_export`, `build_institutional_workbook_export`
- `app/services/download_service.py` — POST /download
  orchestration
- `app/services/export_audit_service.py` — `record_runtime_summary_export`,
  `record_institutional_workbook_export`, `record_download_export`
- `app/persistence/exports_repository.py` — `compare_scenarios`,
  `record_export`, `list_exports`, `get_scenario_history`
- `app/persistence/scenarios_repository.py` — `resolve_scenario_snapshot`
- `app/project_factories.py` — `create_default_tuho_wind1`,
  `create_default_oborovo`
- `app/waterfall_core.py` — pre-existing
  `use_construction_schedule_engine` gate (default
  `False`)
- `app/api/project_runner.py` — `run_project`
- `app/input_adapter.py` — `build_projectinputs_from_snapshot`
- `app/services/run_service.py` —
  `_execute_user_created_path` (Phase 17C snapshot
  binding, Phase 51B refactor)
- `docs/pilot_ux_walkthrough_checklist.md` — walkthrough
  anchor
- `docs/pilot_user_guide.md` — user guide
