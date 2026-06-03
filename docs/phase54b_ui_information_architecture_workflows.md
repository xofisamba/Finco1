# Phase 54B — Information Architecture and Workflow Map

## Context

Phase 54B defines the FincoGPT UI information architecture (IA) and
the 10 core analyst workflows. **No runtime code changes. Docs/
report/test only.** This builds on 54A's frontend inventory.

## Current Main SHA

`8476fe79d07e3cb72bf3b6621c09021f5c8a5b1d` (post-54A merge)

## Information Architecture (11 sections)

### 1. Dashboard / Overview

- **Purpose:** First-page analyst view: active scenario summary, KPIs, recent runs, validation status.
- **User intent:** "Where am I? What is the state of my work?"
- **Current templates:** `index.html`, `kpis.html`, `runtime_summary.html`, `errors.html`
- **Backend dependencies:** `scenario_state_service`, `run_service`, `validation_service`
- **State indicators needed:** Active scenario ID, last run time, validation status, factory vs user-created
- **Risks:** KPI overload, stale result confusion
- **No-go copy concerns:** Avoid "live" or "real-time" claims; use "last run" with timestamp
- **Pilot priority:** HIGH (top of analyst workflow)
- **Enterprise priority:** HIGH

### 2. Projects

- **Purpose:** Project browser, create/duplicate/select projects.
- **User intent:** "Find or create a project to work on."
- **Current templates:** `project_browser.html`, `project_selector.html`, `new_project_form.html`, `new_project_result.html`
- **Backend dependencies:** `projects_create_service`, `project_save_as_service`
- **State indicators needed:** Factory template vs user-created, locked source, last modified
- **Risks:** Confusion between factory templates and user projects
- **No-go copy concerns:** Don't claim "template library" if it isn't a curated, validated library
- **Pilot priority:** HIGH
- **Enterprise priority:** MEDIUM

### 3. Inputs

- **Purpose:** Edit revenue, OPEX, CAPEX assumptions.
- **User intent:** "Change inputs and see impact on the model."
- **Current templates:** `inputs_section.html`, `sheet_revenue.html`, `sheet_opex.html`, `sheet_opex_detail.html`, `sheet_capex.html`, `sheet_capex_detail.html`, `sheet_production.html`, `sheet_construction.html`, `sheet_idc.html`, `sheet_inputs.html`
- **Backend dependencies:** `scenarios_save_service`, `scenarios_add_service`, `scenario_update_overrides_service`
- **State indicators needed:** Runtime Impact per line item, fixture-backed, frozen schedule, source-locked
- **Risks:** Display-only inputs may be edited (UI bug)
- **No-go copy concerns:** Avoid "validated assumption" — use "model assumption" or "captured value"
- **Pilot priority:** HIGH
- **Enterprise priority:** HIGH

### 4. Financing

- **Purpose:** Senior debt / DSCR, SHL / distribution, Tax configuration.
- **User intent:** "Configure debt and equity layer assumptions."
- **Current templates:** `sheet_senior_debt.html`, `sheet_shl.html`, `sheet_tax.html`, `debt_dscr_shl_panel.html`
- **Backend dependencies:** `run_service`, `save_run_service`
- **State indicators needed:** Senior debt source (TUHO/Oborovo vs other), DSCR threshold, sculpting status
- **Risks:** `flat/min DSCR sculpting` not promoted — UI must not present as selectable if not promoted
- **No-go copy concerns:** Avoid "lender-grade" / "credit committee" claims
- **Pilot priority:** HIGH
- **Enterprise priority:** HIGH

### 5. Scenarios

- **Purpose:** Manage scenarios: list, create, load, save, archive, version.
- **User intent:** "Switch between scenarios, save my work, compare scenarios."
- **Current templates:** `scenario_tab.html`, `scenario_load_result.html`, `scenario_version_history.html`, `scenario_workspace.html`, `scenario_compare.html`
- **Backend dependencies:** `scenarios_add_service`, `scenarios_save_service`, `scenario_rename_service`, `scenario_archive_service`, `scenario_duplicate_service`, `scenario_select_service`, `scenario_update_overrides_service`
- **State indicators needed:** Active vs saved vs draft, base case, archived
- **Risks:** Confusing draft vs saved vs active
- **No-go copy concerns:** Avoid "scenario library" if not curated
- **Pilot priority:** HIGH
- **Enterprise priority:** MEDIUM

### 6. Compare

- **Purpose:** Side-by-side scenario comparison.
- **User intent:** "What changed between two scenarios?"
- **Current templates:** `scenario_compare.html`, `comparison.html`
- **Backend dependencies:** `compare_service`
- **State indicators needed:** Scenarios being compared, scope differences
- **Risks:** Comparing scenarios with mismatched scope (project_code, scope)
- **No-go copy concerns:** Avoid "delta" as if it were a finance-team delta
- **Pilot priority:** MEDIUM
- **Enterprise priority:** MEDIUM

### 7. Audit & Reconciliation

- **Purpose:** Review run history, validation results, audit trail.
- **User intent:** "What did the model do? Is it consistent?"
- **Current templates:** `audit_reconciliation_tab.html`, `run_history.html`, `validation.html`
- **Backend dependencies:** `validation_service`, `export_audit_service`, `run_service`
- **State indicators needed:** Pass/warn/fail badges, scope notice, last validation timestamp
- **Risks:** "PASS" / "FAIL" badges may imply external validation
- **No-go copy concerns:** Must NOT use "audit-ready" / "audit-grade"; use "audit trail" or "internal validation"
- **Pilot priority:** HIGH
- **Enterprise priority:** HIGH

### 8. Reports / Exports

- **Purpose:** Download Excel, PDF, JSON exports.
- **User intent:** "Export my work to share with collaborators."
- **Current templates:** `export_registry.html`
- **Backend dependencies:** `export_service`, `export_audit_service`, `download_service`
- **State indicators needed:** Export format, last exported timestamp, scope
- **Risks:** Exports may be mistaken for "official" reports
- **No-go copy concerns:** Avoid "report" as a finance-team term; use "model export"
- **Pilot priority:** MEDIUM
- **Enterprise priority:** MEDIUM

### 9. Data Room

- **Purpose:** Project context, fixtures, source documents.
- **User intent:** "What inputs backed this model?"
- **Current templates:** None currently (planned)
- **Backend dependencies:** Not yet implemented
- **State indicators needed:** Fixture-backed items, source-locked items, source-locked dates
- **Risks:** "Data room" is a lender/audit term — may imply external validation
- **No-go copy concerns:** Avoid "data room" as a term unless explicitly internal; use "model source" or "captured inputs"
- **Pilot priority:** LOW (out of UI-1 scope)
- **Enterprise priority:** MEDIUM

### 10. Settings

- **Purpose:** User preferences, scenario defaults, display options.
- **User intent:** "Configure my experience."
- **Current templates:** None currently
- **Backend dependencies:** Not yet implemented
- **State indicators needed:** Theme (light/dark), default scenario template
- **Risks:** Over-promising (e.g., "custom themes" without implementing)
- **No-go copy concerns:** None specific
- **Pilot priority:** LOW
- **Enterprise priority:** LOW

### 11. Help / Onboarding (implicit)

- **Purpose:** Pilot onboarding, workflow guides, limitations notice.
- **User intent:** "How do I use this?"
- **Current templates:** `pilot_help_onboarding.html`, `pilot_workflow_guide.html`, `pilot_limitations_notice.html`
- **Backend dependencies:** None (static content)
- **State indicators needed:** Pilot scope, known limitations
- **Risks:** Pilot help may drift from actual limitations
- **No-go copy concerns:** Must keep limitations copy synchronized with audit_reconciliation_tab
- **Pilot priority:** HIGH (must be present)
- **Enterprise priority:** LOW

## 10 Core Analyst Workflows

### Workflow 1: Review factory template

- **Steps:** Open project browser → click factory template → review inputs → review sheets → review audit tab
- **Templates:** `project_browser.html` → `index.html` → `audit_reconciliation_tab.html`
- **State indicators needed:** Factory badge, source-locked markers, validation status
- **No-go copy concerns:** Use "factory template" not "validated template" or "lender template"

### Workflow 2: Duplicate project / create scenario

- **Steps:** Open project → click "save as" or "duplicate scenario" → enter name → save
- **Templates:** `index.html` → `new_project_form.html` or scenario_workspace.html
- **State indicators needed:** New project badge, copy-as-of timestamp
- **Risks:** User may not realize they have a copy vs the original

### Workflow 3: Edit assumptions

- **Steps:** Open inputs section → edit line item → save (auto-draft or explicit)
- **Templates:** `inputs_section.html`, `sheet_*.html`
- **State indicators needed:** Runtime Impact chip per line item, dirty marker
- **Risks:** Display-only inputs appear editable; fixture-backed values appear editable

### Workflow 4: Save scenario

- **Steps:** Click save → confirm → receive save_result
- **Templates:** `save_result.html`, `scenario_load_result.html`
- **State indicators needed:** Save success, scenario ID, timestamp
- **No-go copy concerns:** Avoid "committed" / "locked" — use "saved" / "versioned"

### Workflow 5: Run model

- **Steps:** Click "run" → see runtime_summary → see validation results
- **Templates:** `runtime_summary.html`, `validation.html`, `errors.html`
- **State indicators needed:** Run in progress, last run timestamp, validation status
- **No-go copy concerns:** Use "model run" not "calculation" / "valuation"

### Workflow 6: Validate

- **Steps:** Open audit tab → review validation summary → review pass/warn/fail badges
- **Templates:** `audit_reconciliation_tab.html`, `validation.html`
- **State indicators needed:** Pass/warn/fail, scope notice, source-locked, fixture-backed
- **No-go copy concerns:** Must use "internal validation" / "model check"; never "validated" alone

### Workflow 7: Compare scenarios

- **Steps:** Open compare tab → select two scenarios → view diff
- **Templates:** `scenario_compare.html`, `comparison.html`
- **State indicators needed:** Scenario IDs, scope match indicator
- **Risks:** Comparing scenarios with mismatched scope (project_code, scope)

### Workflow 8: Audit/reconcile

- **Steps:** Open audit tab → review badge summary → drill into specific checks → review run history
- **Templates:** `audit_reconciliation_tab.html`, `run_history.html`
- **State indicators needed:** Pass/warn/fail per check, run history with timestamps
- **No-go copy concerns:** "Audit" here is internal model audit, not external audit

### Workflow 9: Download/export

- **Steps:** Open export registry → select format → click download
- **Templates:** `export_registry.html`
- **State indicators needed:** Format, scope, last exported timestamp
- **No-go copy concerns:** Use "export" not "report"; use "model output" not "report"

### Workflow 10: Review run/scenario history

- **Steps:** Open history tab → see run list → see scenario version list
- **Templates:** `run_history.html`, `scenario_version_history.html`
- **State indicators needed:** Timestamp, scenario ID, run ID, success/fail
- **No-go copy concerns:** Use "run history" not "audit log"

## Backend Dependency Map

| Section | Primary services | Persistence |
|---|---|---|
| Dashboard | `scenario_state_service`, `run_service` | `scenarios_repository`, `runs_repository` |
| Projects | `projects_create_service`, `project_save_as_service` | `projects_repository` |
| Inputs | `scenarios_save_service`, `scenarios_add_service` | `scenarios_repository` |
| Financing | `run_service`, `save_run_service` | `scenarios_repository`, `runs_repository` |
| Scenarios | scenario_*_service (7 services) | `scenarios_repository` |
| Compare | `compare_service` | `scenarios_repository` |
| Audit & Reconciliation | `validation_service`, `export_audit_service`, `run_service` | `scenarios_repository`, `runs_repository`, `exports_repository` |
| Reports / Exports | `export_service`, `export_audit_service`, `download_service` | `exports_repository` |
| Data Room | (not yet implemented) | (not yet implemented) |
| Settings | (not yet implemented) | (not yet implemented) |
| Help / Onboarding | none (static) | none |

## State Indicator Requirements

Across all sections, the following state indicators are needed:

1. **Active scenario** (which scenario is the analyst working in)
2. **Saved vs draft** (state of current work)
3. **Last run** (when was the model last executed)
4. **Validation status** (pass / warn / fail)
5. **Factory vs user-created** (project origin)
6. **Source-locked / fixture-backed** (input origin)
7. **Runtime Impact per line item** (drives / display-only / pending / needs-review)
8. **Scope match** (when comparing scenarios)
9. **Stale result warning** (model result from older run)
10. **Display-only row marker** (visible but not editable)

## Priority Matrix

| Section | Pilot priority | Enterprise priority | UI-1 (docs) | UI-2 (run) | UI-3 (later) |
|---|---|---|---|---|---|
| Dashboard | HIGH | HIGH | ✓ | ✓ | |
| Projects | HIGH | MEDIUM | ✓ | ✓ | |
| Inputs | HIGH | HIGH | ✓ | ✓ | |
| Financing | HIGH | HIGH | ✓ | ✓ | |
| Scenarios | HIGH | MEDIUM | ✓ | ✓ | |
| Compare | MEDIUM | MEDIUM | ✓ | | ✓ |
| Audit & Reconciliation | HIGH | HIGH | ✓ | ✓ | |
| Reports / Exports | MEDIUM | MEDIUM | ✓ | | ✓ |
| Data Room | LOW | MEDIUM | ✓ | | ✓ |
| Settings | LOW | LOW | ✓ | | ✓ |
| Help / Onboarding | HIGH | LOW | ✓ | ✓ | |

## No-Go Copy Risks (54B)

| Risk | Section | Mitigation |
|---|---|---|
| "Validated" / "audit-ready" / "lender-grade" | All | Use "internal validation" / "model check" / "audit trail" |
| "Real-time" / "live" | Dashboard | Use "last run" with timestamp |
| "Production-ready" / "SaaS-ready" | All | Do not use at all in pilot |
| "Committed" / "locked" | Scenarios | Use "saved" / "versioned" |
| "Data room" | Data Room | Use "model source" or "captured inputs" |
| "Report" | Reports | Use "export" / "model output" |
| "Bankable" / "lender-ready" | All | BANNED in any copy |

## Recommendation for 54C

Proceed to **Phase 54C — Design system, tokens, and UI copy guardrails**:

1. Define the visual design tokens (colors, typography, spacing)
2. Specify the component vocabulary (chip, badge, banner, card, grid, section, status pill, tooltip, validation marker)
3. Lock the 4-state Runtime Impact chip standard with exact copy
4. Specify the state clarity banner copy for 11 contexts
5. Build the no-go UI copy scanner specification

## Hard Gates (54B)

- ✓ Only docs/report/test files added
- ✓ No templates/CSS/JS/services/persistence changes
- ✓ Branch based on post-54A main `8476fe79d07e3cb72bf3b6621c09021f5c8a5b1d`
- ✓ IA covers all 11 sections
- ✓ All 10 core workflows mapped
- ✓ Backend dependencies traced
- ✓ No-go copy risks identified per section
- ✓ Priority matrix defined
- ✓ rc1 (b425a07) untouched

## Files Created in 54B

- `docs/phase54b_ui_information_architecture_workflows.md` (this file)
- `reports/phase54b_ui_information_architecture_workflows.json`
- `tests/test_phase54b_ui_information_architecture_workflows.py` (guardrail)
