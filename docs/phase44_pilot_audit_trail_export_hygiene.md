# Phase 44 — Pilot Audit Trail Polish and Export Hygiene Enforcement

**Branch:** `phase44-pilot-audit-trail-export-hygiene`
**Base SHA:** `28afc581900bb5025d509a626de8d8369664d41f` (after PR #355 Phase 43 merge)
**Date:** 2026-06-01
**Type / Scope:** Pilot UX hygiene, audit/export wording, documentation — no model logic changes

---

## 1. Objective

Polish pilot-facing audit trail clarity and enforce export hygiene language/metadata so pilot users understand exactly what each export represents and whether it reflects the last clean backend run.

**No formula changes. No runtime changes. No runtime calculation changes. No model file changes. No JS financial calculations.**

---

## 2. Inspected Surfaces

| Surface | File |
|---------|------|
| Runtime summary | `app/templates/partials/runtime_summary.html` |
| Audit/reconciliation tab | `app/templates/partials/audit_reconciliation_tab.html` |
| Debt/DSCR/SHL panel | `app/templates/partials/debt_dscr_shl_panel.html` |
| Scenario version history | `app/templates/partials/scenario_version_history.html` |
| Pilot limitations notice | `app/templates/partials/pilot_limitations_notice.html` |
| Pilot workflow guide | `app/templates/partials/pilot_workflow_guide.html` |
| Workspace shell | `app/templates/partials/workspace_shell.html` |
| Pilot user guide | `docs/pilot_user_guide.md` |

---

## 3. Hygiene Issues Found

| Issue | Surface | Risk | Resolution |
|-------|---------|------|------------|
| Runtime summary did not clearly distinguish current draft vs last clean run | `runtime_summary.html` | User could assume draft = last run | Enhanced notice with draft/run distinction |
| Export step hint did not remind user to re-run after changes | `pilot_workflow_guide.html` | User could export stale outputs | Updated hint: "Exports reflect last clean run. Re-run after input changes." |
| Audit/reconciliation disclaimer already present | `audit_reconciliation_tab.html` | Already correct — no change needed | — |
| Pilot limitations notice already strong | `pilot_limitations_notice.html` | Already correct — no change needed | — |
| Workspace shell already has review boundary note | `workspace_shell.html` | Already correct — no change needed | — |

---

## 4. Display-Only Changes Made

| File | Change |
|------|--------|
| `app/templates/partials/runtime_summary.html` | Enhanced runtime notice: added "current workspace draft vs last clean run" distinction, explicit "re-run after any input change" instruction, export boundary reminder |
| `app/templates/partials/pilot_workflow_guide.html` | Step 7 hint updated: "Exports reflect the last clean backend run. Re-run after input changes." |

**No JS financial calculations added. No model logic changed. No formula changes.**

---

## 5. Export Hygiene Rules

| Rule | Description |
|------|-------------|
| **Last clean run boundary** | Exports reflect the last clean backend run, not browser-side draft edits |
| **Re-run before export** | After any input change, re-run model before exporting |
| **Scenario save first** | Save a named scenario before changing inputs — provides a recoverable baseline |
| **Timestamp filenames** | Exports should use timestamped filenames to avoid confusion |
| **No stale exports** | Never share an export that was generated before the most recent clean run |
| **Generic path warning** | Generic solar/wind exports are unvalidated — do not use for financial decisions |
| **Internal review only** | Audit/reconciliation tab is internal review tooling — not an external audit or certification |

---

## 6. Audit Trail Interpretation

| Concept | Clarification |
|---------|---------------|
| Draft edits | Browser-side changes not yet saved or run — not reflected in exports |
| Saved scenario | Named snapshot saved by user — the input baseline for the next run |
| Last clean backend run | Most recent successful model execution — authoritative output basis for exports |
| Runtime summary | Reflects the last clean backend run, not the current draft workspace |
| Audit/reconciliation | Internal review evidence for TUHO/Oborovo frozen-template paths — not certified external audit |

---

## 7. Last Clean Backend Run Boundary

The "last clean backend run" is the authoritative output boundary. All exports (XLSX, CSV, parity workbooks) are generated from this run and inherit its provenance metadata.

**What this means for pilots:**
- Exports will not reflect unsaved draft edits
- Re-run after any input change to update the authoritative output
- The runtime summary badge shows the last clean run timestamp
- Export lineage panel shows runtime snapshot ID and generated-at time

---

## 8. Generic Exclusion Reminder

| Project | Status |
|---------|--------|
| TUHO Wind (72 MW, Croatia) | ✅ Validated — within tolerance |
| Oborovo Solar (53.63 MW, Croatia) | ✅ Validated — within tolerance |
| Generic solar | ❌ Unvalidated — exploratory only |
| Generic wind | ❌ Unvalidated — exploratory only |

Generic projects must not be used as a basis for financial decisions. Exploratory outputs are excluded from trusted pilot conclusions unless separately reviewed.

---

## 9. Non-Claims

FincoGPT outputs must never be represented as:
- ❌ Bank approval or lender approval
- ❌ Certified external audit
- ❌ SaaS-ready or enterprise-ready
- ❌ Compliant with any financial regulation

The Audit/Parity tab is **internal review evidence** for TUHO/Oborovo frozen-template paths only. Generic projects remain unvalidated.

---

## 10. Issue Routing

All pilot issues (including hygiene questions like stale export confusion) go to `docs/pilot_issue_intake_template.md`. Triage board at `docs/pilot_issue_triage_board_template.md` handles ongoing tracking.

Stale export or draft/run confusion should be routed as **clarification**. Generic path misuse is a **pause trigger** (see Phase 43 pause policy).

## 11. Guardrails Confirmation

| Gate | Status |
|------|--------|
| G20 | BLOCKED — not changed |
| R99 | NOT APPROVED — not changed |
| R102 | NOT APPROVED — not changed |
| partial_pay_sweep | Not promoted — confirmed |
| flat/min DSCR sculpting | Not promoted — confirmed |
| Backend source of truth | Confirmed — JS is display-only |
| No formula/runtime/model changes | Confirmed — display-only template changes only |
| No JS financial calculations | Confirmed — JS untouched |

---

## 12. Recommended Next Phase

**Phase 45 — Pilot Closeout and Handoff Summary**

Consolidate all pilot documentation, confirm readiness for ongoing operations, and produce the final pilot closeout summary.

---

## 13. Changed Files

| File | Type | Description |
|------|------|-------------|
| `docs/phase44_pilot_audit_trail_export_hygiene.md` | Doc | This document |
| `docs/pilot_audit_export_hygiene_checklist.md` | Doc | Hygiene checklist |
| `docs/phase44_audit_export_hygiene_matrix.md` | Doc | Hygiene matrix |
| `reports/phase44_audit_export_hygiene_summary.json` | Doc | JSON summary |
| `app/templates/partials/runtime_summary.html` | Template | Enhanced runtime notice copy |
| `app/templates/partials/pilot_workflow_guide.html` | Template | Export step hint updated |
| `tests/test_phase44_pilot_audit_trail_export_hygiene.py` | Test | Phase 44 tests |