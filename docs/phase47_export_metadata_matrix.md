# Phase 47 — Export Metadata Matrix

**Branch:** `phase47-export-hygiene-runtime-metadata`
**Base SHA:** `a5fafdf8b93ff23d7272b11b1928798b3bc9fa63`

---

## Export Artefacts and Metadata Coverage

| Export artefact | Module | Metadata location | Last clean run included? | Scenario included? | Validation status included? | Generic warning included? | Machine-readable impact | Follow-up |
|----------------|--------|-------------------|------------------------|--------------------|---------------------------|------------------------|------------------------|-----------|
| Institutional Workbook | `app/export/institutional_workbook.py` | `Export_Metadata` sheet (first sheet) | ✅ runtime_timestamp used as proxy | ✅ scenario_id, scenario_name | ✅ validation_status field | ✅ generic_boundary field | None — new sheet only | None |
| Calibration Reconciliation Workbook | `app/export/calibration_reconciliation.py` | `Export_Metadata` sheet (first sheet) | ✅ runtime_timestamp used as proxy | ✅ scenario_id, scenario_name | ✅ validation_status field | ✅ generic_boundary field | None — new sheet only | None |
| Runtime Summary CSV | `app/export/runtime_summary.py` | CSV header columns (pre-existing) | ✅ runtime_generated_at | ✅ scenario_id, scenario_name | ⚠️ governance_posture_summary column | ⚠️ replay_limitations column | None — existing columns only | CSV consumer compatibility confirmed; no companion metadata |
| Values-only Excel | (download via Streamlit) | Not yet inspected | — | — | — | — | — | Inspect in follow-up phase |
| Parity Workbook | `app/export/calibration_reconciliation.py` (reconciliation sheets) | Same Export_Metadata sheet | ✅ via workbook | ✅ via workbook | ✅ via workbook | ✅ via workbook | None | Part of calibration workbook |
| Gap Register | `app/export/institutional_workbook.py` (Gap Register sheet) | Not separate | ✅ via workbook metadata | ✅ via workbook | ✅ via workbook | ✅ via workbook | None | Part of institutional workbook |
| Source Map | Not yet inspected | — | — | — | — | — | — | Inspect in follow-up phase |
| UI runtime summary banner | `app/templates/partials/runtime_summary.html` | Pre-existing display notice | ✅ "Exports reflect last clean backend run" pre-existing | N/A (UI display) | N/A | ⚠️ generic boundary not shown in UI banner | None | Consider adding generic warning to UI in follow-up |

---

## Metadata Fields by Export Artefact

| Metadata field | Institutional Workbook | Calibration Workbook | Runtime Summary CSV |
|---------------|----------------------|---------------------|--------------------|
| export_generated_at | ✅ | ✅ | ✅ (as export_generated_at) |
| export_type | ✅ | ✅ | ✅ (as export_type) |
| active_project | ✅ | ✅ | ✅ |
| project_id | ✅ | ✅ | ✅ (as project) |
| project_name | ✅ | ✅ | ✅ (as project in metric rows) |
| scenario_id | ✅ | ✅ | ✅ |
| scenario_name | ✅ | ✅ | ✅ |
| scenario_saved_at | ✅ | ✅ | ❌ (not in CSV) |
| last_clean_backend_run_at | ✅ (using runtime_timestamp) | ✅ (using runtime_timestamp) | ✅ (as runtime_generated_at) |
| dirty_or_stale_warning | ✅ | ✅ | ⚠️ via replay_limitations |
| validation_status | ✅ | ✅ | ⚠️ via governance_posture_summary |
| trusted_pilot_scope | ✅ | ✅ | ⚠️ via governance_posture_summary |
| generic_boundary | ✅ | ✅ | ⚠️ via replay_limitations |
| non_claims | ✅ (prominent block) | ✅ (prominent block) | ⚠️ via replay_limitations |
| backend_source_of_truth | ✅ | ✅ | ✅ implied by replay_limitations |

---

## Phase 47 Implementation Status

| Artefact | Export_Metadata sheet added? | Non-claims block? | Last clean run? | Generic warning? |
|----------|-----------------------------|-----------------|----------------|-----------------|
| Institutional Workbook | ✅ Yes (first sheet) | ✅ 10-line block | ✅ runtime_timestamp | ✅ generic_boundary field |
| Calibration Reconciliation Workbook | ✅ Yes (first sheet) | ✅ 5-line block | ✅ runtime_timestamp | ✅ generic_boundary field |
| Runtime Summary CSV | N/A (header-only) | ⚠️ replay_limitations column | ✅ runtime_generated_at | ⚠️ replay_limitations column |

---

## Guardrails Status

| Guardrail | Institutional | Calibration | CSV | UI |
|-----------|--------------|-------------|-----|-----|
| No formula changes | ✅ | ✅ | ✅ | ✅ |
| No runtime changes | ✅ | ✅ | ✅ | ✅ |
| No model output changes | ✅ | ✅ | ✅ | ✅ |
| G20 BLOCKED | ✅ stated in NON-CLAIMS | ✅ stated in NON-CLAIMS | ✅ governance_posture_summary | N/A |
| R99/R102 NOT APPROVED | ✅ stated in NON-CLAIMS | ✅ stated in NON-CLAIMS | ✅ governance_posture_summary | N/A |
| partial_pay_sweep not promoted | ✅ stated in NON-CLAIMS | ✅ stated in NON-CLAIMS | ⚠️ | N/A |
| flat/min DSCR not promoted | ✅ stated in NON-CLAIMS | ✅ stated in NON-CLAIMS | ⚠️ | N/A |
| Backend source of truth | ✅ stated | ✅ stated | ✅ implied | ✅ pre-existing UI notice |
| No JS financial logic | ✅ | ✅ | ✅ | ✅ |
| No fixture CSVs changed | ✅ | ✅ | ✅ | ✅ |