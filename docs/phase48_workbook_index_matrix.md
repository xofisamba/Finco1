# Phase 48 — Workbook Index Matrix

**Branch:** `phase48-export-index-readme-sheet-polish`
**Base SHA:** `d6276fac210d960a6a4b7e2c201a51e4d3fac8d3`

---

## Workbook Index Coverage

| Workbook | Index sheet name | Sheet order | Sheet inventory table? | Validation status included? | Generic warning included? | Non-claims included? | Guardrails included? | Follow-up |
|----------|-----------------|-------------|----------------------|---------------------------|------------------------|---------------------|---------------------|-----------|
| Institutional Runtime Workbook | `Workbook_Index` | 1 (after Export_Metadata) | ✅ Sheet Name / Purpose / Audience / Status / Notes | ✅ Status column: Runtime / Runtime+Template / Template+Runtime / Review | ✅ Generic Boundary section with amber warning fill | ✅ NON-CLAIMS section with 6 items | ✅ Guardrails section (G20/R99/R102/partial_pay_sweep/backend) | None |
| Calibration Reconciliation Workbook | `Workbook_Index` | 1 (after Export_Metadata) | ✅ Same columns | ✅ Status column | ✅ Generic Boundary section | ✅ NON-CLAIMS section | ✅ Guardrails section | None |
| Runtime Summary CSV | N/A (header-only export) | N/A | N/A — CSV has no sheets | N/A | ⚠️ via replay_limitations column | ⚠️ via replay_limitations | N/A | None — existing provenance columns sufficient |
| UI runtime summary banner | N/A (display, not export) | N/A | N/A | N/A | ⚠️ already shows "Exports reflect last clean run" | N/A | N/A | Consider adding generic warning to UI in follow-up |

---

## Sheet Order Verification

| Position | Institutional Workbook | Calibration Workbook |
|----------|----------------------|---------------------|
| 0 | Export_Metadata (Phase 47) | Export_Metadata (Phase 47) |
| 1 | **Workbook_Index (Phase 48)** | **Workbook_Index (Phase 48)** |
| 2 | Cover | Cover |
| 3 | Governance | Navigation |
| 4 | Runtime Summary | Executive Dashboard |
| ... | (remaining sheets) | (remaining sheets) |

---

## Workbook_Index Sections by Workbook

| Section | Institutional | Calibration | Notes |
|---------|--------------|-------------|-------|
| Metadata (workbook/project/export type) | ✅ | ✅ | |
| Sheet Inventory table | ✅ 18 rows | ✅ 20 rows | |
| Trusted Pilot Scope | ✅ TUHO + Oborovo | ✅ (via Export_Metadata) | Calibration inherits via Export_Metadata |
| Generic Boundary | ✅ warning fill | ✅ warning fill | |
| Export Hygiene | ✅ | ✅ | |
| Audit Interpretation | ✅ | ✅ | |
| NON-CLAIMS | ✅ 6 items | ✅ 6 items | |
| Guardrails | ✅ 6 items | ✅ 6 items | |

---

## Guardrails Verification

| Guardrail | Institutional Workbook_Index | Calibration Workbook_Index |
|-----------|---------------------------|--------------------------|
| G20 BLOCKED | ✅ stated | ✅ stated |
| R99 NOT APPROVED | ✅ stated | ✅ stated |
| R102 NOT APPROVED | ✅ stated | ✅ stated |
| partial_pay_sweep not promoted | ✅ stated | ✅ stated |
| flat/min DSCR sculpting not promoted | ✅ stated | ✅ stated |
| Backend source of truth | ✅ stated | ✅ stated |
| No formula/runtime/model changes | ✅ confirmed in docs | ✅ confirmed in docs |

---

## Phase 48 Implementation Status

| Item | Status |
|------|--------|
| workbook_index.py helper created | ✅ |
| INSTITUTIONAL_SHEET_INVENTORY defined | ✅ |
| CALIBRATION_SHEET_INVENTORY defined | ✅ |
| write_workbook_index_sheet_full() implemented | ✅ |
| Institutional workbook Workbook_Index added | ✅ |
| Calibration reconciliation Workbook_Index added | ✅ |
| Export_Metadata stays first sheet | ✅ |
| Workbook_Index is second sheet | ✅ |
| All 8 sections present | ✅ |
| Sheet inventory table with 5 columns | ✅ |
| Generic boundary warning | ✅ |
| NON-CLAIMS block | ✅ |
| Guardrails section | ✅ |
| Docs created | ✅ |
| Tests written | ✅ |