# Phase 48 — Export Index / README Sheet Polish

**Branch:** `phase48-export-index-readme-sheet-polish`
**Base SHA:** `d6276fac210d960a6a4b7e2c201a51e4d3fac8d3`
**Head SHA:** (to be filled after commit)
**Phase:** 48

---

## 1. Objective

Add user-facing **Workbook_Index** sheets to pilot-facing Excel exports so reviewers and pilot users can understand:

- What the workbook is
- What each sheet is for
- Which outputs are validated pilot evidence vs internal review evidence
- What is unvalidated/excluded
- How stale export boundaries work
- Non-claims

This is an export UX / workbook navigation code change. **No financial formulas, runtime calculations, or model outputs changed.**

---

## 2. Workbook Exports Inspected

| Workbook | Module | Current sheets | Status |
|----------|--------|---------------|--------|
| Institutional Runtime Workbook | `app/export/institutional_workbook.py` | Export_Metadata, Cover, Governance, Runtime Summary, Inputs, Construction, OPEX, CAPEX, Revenue, Senior Debt, SHL, Tax, P&L, Cash Flow, Balance Sheet, Audit, Gap Register | ✅ Workbook_Index added |
| Calibration Reconciliation Workbook | `app/export/calibration_reconciliation.py` | Export_Metadata, Cover, Navigation, Executive Dashboard, Executive Summary, Review Signoff, Governance, Governance Timeline, Readiness Matrix, Runtime Summary, Revenue Reconciliation, CO2 & Balancing, OPEX, Senior Debt, SHL, Tax, CFADS Waterfall, Distributions, Returns | ✅ Workbook_Index added |

---

## 3. Sheet Order Decision

| Position | Sheet | Reason |
|----------|-------|--------|
| 0 | Export_Metadata | Phase 47 standard — provenance, trust hygiene, non-claims, 15 metadata fields |
| 1 | **Workbook_Index** | Phase 48 — sheet inventory and workbook guide, second for visibility |
| 2+ | (existing sheets) | Unchanged — Cover, Governance, etc. |

**Export_Metadata stays as first sheet** (Phase 47 standard). **Workbook_Index is second sheet** (Phase 48 addition).

---

## 4. Workbook_Index Content

### Sections

1. **Metadata** — Workbook name, project, export type, added phase
2. **Sheet Inventory Table** — Sheet Name / Purpose / Audience / Status / Notes
3. **Trusted Pilot Scope** — TUHO/Oborovo frozen-template paths
4. **Generic Boundary** — Exploratory/unvalidated warning
5. **Export Hygiene** — Last clean backend run, re-run after input changes
6. **Audit Interpretation** — Internal review evidence, not certified audit
7. **NON-CLAIMS** — Not bank/lender/certification/SaaS-ready
8. **Guardrails** — G20 BLOCKED, R99/R102 NOT APPROVED, partial_pay_sweep not promoted, flat/min DSCR not promoted, backend source of truth

### Sheet Inventory Fields

| Field | Description |
|-------|-------------|
| Sheet Name | Sheet tab name |
| Purpose | What the sheet contains |
| Audience | Who the sheet is for |
| Status | Validation status: Runtime / Runtime+Template / Template+Runtime / Review |
| Notes | Additional context |

---

## 5. Code Structure

New file: `app/export/workbook_index.py`

```python
INSTITUTIONAL_SHEET_INVENTORY  # 18 rows for institutional workbook
CALIBRATION_SHEET_INVENTORY    # 20 rows for calibration workbook
write_workbook_index_sheet_full(...)  # Full sheet writer with all sections
```

Applied to:
- `app/export/institutional_workbook.py` — Workbook_Index after Export_Metadata
- `app/export/calibration_reconciliation.py` — Workbook_Index after Export_Metadata

Styling: basic openpyxl — bold section headers, alternating row fills, wrapped text, column widths.

---

## 6. Validation / Generic Boundary Treatment

| Project type | Workbook_Index treatment |
|--------------|--------------------------|
| TUHO / Oborovo | Trusted scope section with green fill, all sections visible |
| Generic | Generic boundary section with warning fill (amber/red) |

Both include non-claims and guardrails.

---

## 7. Guardrails Confirmed

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

---

## 8. Paid Pilot Blockers (Unchanged)

| Blocker | Status |
|---------|--------|
| Generic solar validation | Not resolved |
| Generic wind validation | Not resolved |
| Generic wind CO2 | Not wired |
| Construction IDC | Not wired |
| C.16 Project Rights | Not wired |
| M1-M18 IDC | Not wired |

---

## 9. Recommended Next Phase

**Phase 49** — either:
- Real-User Session Debrief (if actual user notes available from Phase 46 framework), OR
- Export Download UX Polish (add "Download with metadata" / "Last clean run" indicators to UI download buttons)

---

## 10. Changed Files

| File | Change |
|------|--------|
| `app/export/workbook_index.py` | New — sheet inventory constants and `write_workbook_index_sheet_full()` |
| `app/export/institutional_workbook.py` | Import `workbook_index`, add `Workbook_Index` second sheet |
| `app/export/calibration_reconciliation.py` | Import `workbook_index`, add `Workbook_Index` second sheet |
| `docs/phase48_export_index_readme_sheet_polish.md` | This document |
| `docs/phase48_workbook_index_matrix.md` | Workbook index matrix |
| `reports/phase48_export_index_readme_summary.json` | JSON summary |
| `tests/test_phase48_export_index_readme_sheet_polish.py` | Phase 48 tests |