# Phase 47 — Export Hygiene Runtime Metadata

**Branch:** `phase47-export-hygiene-runtime-metadata`
**Base SHA:** `a5fafdf8b93ff23d7272b11b1928798b3bc9fa63`
**Head SHA:** (to be filled after commit)
**Phase:** 47

---

## 1. Objective

Add lightweight runtime/export metadata to pilot-facing export artefacts so every downloaded output clearly identifies:

- The project and scenario/run basis
- Validation status and trusted scope
- Last-clean-backend-run boundary
- Non-claims (not bank/lender/audit/certification approval)

This is a low-risk code change focused entirely on export metadata and trust hygiene. No financial formulas, runtime calculations, or model outputs are changed.

---

## 2. Export Paths Inspected

| Export module | Artefact | Status |
|--------------|----------|--------|
| `app/export/institutional_workbook.py` | Institutional Workbook | ✅ Export_Metadata sheet added |
| `app/export/calibration_reconciliation.py` | Calibration Reconciliation Workbook | ✅ Export_Metadata sheet added |
| `app/export/runtime_summary.py` | Runtime Summary CSV | ✅ CSV header includes provenance fields; companion metadata not needed (already machine-readable with header) |
| `app/export/registry.py` | Export registry / download orchestration | No model output changes needed |
| `app/templates/partials/runtime_summary.html` | Runtime summary banner (UI) | ✅ Already shows "Exports reflect last clean backend run" notice (pre-existing) |
| `app/templates/partials/pilot_workflow_guide.html` | Pilot workflow guide | ✅ Non-claims language present (pre-existing) |

---

## 3. Metadata Fields Added

New file: `app/export_metadata.py`

Function: `build_export_metadata(...) → dict[str, str]`

| Field | Description |
|-------|-------------|
| `export_generated_at` | ISO timestamp when export was generated |
| `export_type` | Type of export artefact |
| `active_project` | Active project key (tuho/oborovo/generic) |
| `project_id` | Project identifier |
| `project_name` | Human-readable project name |
| `scenario_id` | Scenario identifier |
| `scenario_name` | Scenario name |
| `scenario_saved_at` | Scenario save timestamp |
| `last_clean_backend_run_at` | Last clean backend run timestamp |
| `dirty_or_stale_warning` | Warning if workspace has unsaved changes |
| `validation_status` | Validation status string |
| `trusted_pilot_scope` | TUHO/Oborovo trusted scope description |
| `generic_boundary` | Generic solar/wind boundary warning |
| `non_claims` | Explicit non-claims: not bank/lender/audit/certification |
| `backend_source_of_truth` | Backend is source of truth; exports reflect last clean run |

Helper: `metadata_rows(meta) → list[tuple[str, str]]` converts dict to ordered display rows.

---

## 4. Excel Metadata Implementation

### Institutional Workbook (`app/export/institutional_workbook.py`)

- Added `Export_Metadata` as the **first sheet** (sheet order 0)
- New function `_write_export_metadata_sheet(sheet, bundle)`
- Sheet includes:
  - All 15 metadata fields from `build_export_metadata()`
  - Prominent NON-CLAIMS block with 10 warning lines
  - Trusted scope confirmation for TUHO/Oborovo
  - Generic boundary warning for generic solar/wind
  - Guardrail confirmations (G20 BLOCKED, R99/R102 NOT APPROVED, etc.)
- All value sheets unchanged (Cover through Gap Register unchanged)

### Calibration Reconciliation Workbook (`app/export/calibration_reconciliation.py`)

- Added `Export_Metadata` as the **first sheet** (before Cover)
- New function `_write_export_metadata_sheet(sheet)`
- Sheet includes same metadata fields and NON-CLAIMS block
- All reconciliation sheets unchanged

---

## 5. CSV Metadata Decision

**Runtime Summary CSV** (`app/export/runtime_summary.py`):

The existing CSV already contains comprehensive provenance header columns:
- `export_generated_at`, `runtime_generated_at`, `source_branch`, `branch_name`, `commit_sha`
- `runtime_timestamp`, `active_project`, `scenario_id`, `scenario_name`
- `runtime_snapshot_id`, `runtime_origin`, `template_origin`, `template_revision`
- `export_template_version`, `runtime_flag_count`, `runtime_flags_json`
- `replay_limitations`, `governance_posture_summary`

Adding header comments would break machine-readability for existing CSV consumers.
Therefore: **no companion metadata CSV needed**. The existing header columns provide equivalent provenance.

---

## 6. UI Copy Changes

**`app/templates/partials/runtime_summary.html`** — pre-existing notice already states:
> "Exports reflect the last clean backend run, not unsaved draft edits."

This notice was already present. No UI copy changes were needed.

**`app/templates/partials/pilot_workflow_guide.html`** — pre-existing non-claims language already present.

---

## 7. Validation / Generic Boundary Treatment

| Project | Status in metadata |
|---------|-------------------|
| TUHO (tuho) | `trusted_pilot_scope = TUHO frozen-template path...` |
| Oborovo (oborovo) | `trusted_pilot_scope = Oborovo frozen-template path...` |
| Generic (any other) | `generic_boundary = Generic solar/wind exploratory/unvalidated` |

Both TUHO and Oborovo show the trusted scope. Generic projects get the boundary warning.

---

## 8. Guardrails Confirmed

| Gate | Status |
|------|--------|
| No financial formula changes | ✅ Confirmed |
| No runtime calculation changes | ✅ Confirmed |
| No model output changes | ✅ Confirmed |
| G20 | BLOCKED — unchanged |
| R99 | NOT APPROVED — unchanged |
| R102 | NOT APPROVED — unchanged |
| partial_pay_sweep | Not promoted — unchanged |
| flat/min DSCR sculpting | Not promoted — unchanged |
| Backend source of truth | Confirmed |
| No JS financial calculations | Confirmed — JS untouched |
| No fixture CSVs changed | ✅ Confirmed |
| No schema migrations | ✅ Confirmed |
| No generic validation implemented | ✅ Confirmed |
| No multi-user/RBAC/SSO implemented | ✅ Confirmed |
| No billing implemented | ✅ Confirmed |

---

## 9. Paid Pilot Blockers (Unchanged)

| Blocker | Status |
|---------|--------|
| Generic solar validation | Not resolved |
| Generic wind validation | Not resolved |
| Generic wind CO2 | Not wired |
| Construction IDC | Not wired |
| C.16 Project Rights | Not wired |
| M1-M18 IDC | Not wired |

---

## 10. Recommended Next Phase

**Phase 48 — Real-User Session Debrief and Pilot Status Update**

After the first real-user session is completed (pending from Phase 46 framework), debrief the results, update the issue log, and confirm or revise the pilot continuation recommendation.

---

## 11. Changed Files

| File | Change |
|------|--------|
| `app/export_metadata.py` | New — `build_export_metadata()` and `metadata_rows()` |
| `app/export/institutional_workbook.py` | Added `Export_Metadata` first sheet; imports `export_metadata` |
| `app/export/calibration_reconciliation.py` | Added `Export_Metadata` first sheet; imports `export_metadata` |
| `docs/phase47_export_hygiene_runtime_metadata.md` | This document |
| `docs/phase47_export_metadata_matrix.md` | Export metadata matrix |
| `reports/phase47_export_metadata_summary.json` | JSON summary |
| `tests/test_phase47_export_hygiene_runtime_metadata.py` | Phase 47 tests |