# Final Product Acceptance Audit — Stack C

**Branch:** product-acceptance-stack-c
**Base SHA:** 2bde0fea7c677c362dcde4f6abb29cf696858eed
**Sprint context:** Final audit after 14 prior Product Gap PRs (PR1–PR12, Stack A, Stack B)

---

## Audited modules

| Area | Files audited |
|------|---------------|
| Visual/sheet consistency | `app/templates/partials/sheet_*.html`, `static/styles.css` (CSS classes) |
| Navigation | `app/templates/partials/workspace_shell.html`, `app/templates/partials/workspace_tabs.html` |
| Terminology | All `app/templates/partials/*.html` |
| Empty states | `partials/_empty_no_run.html`, `partials/_empty_no_project.html`, `partials/_empty_no_scenario.html`, `partials/empty_states_notice.html` |
| Runtime panels | `partials/runtime_summary.html`, `partials/shared_runtime_block.html`, `partials/_last_run_indicator.html`, `partials/workspace_shell.html` (runtime indicators) |
| Accessibility | `partials/workspace_shell.html` (ARIA labels, roles) |
| Legacy cleanup | All `app/templates/partials/*.html` (orphan survey) |

---

## Area 1: Visual consistency

**Finding: No changes required.**

All major screens use consistent `sheet-banner` headers, consistent `empty-state-notice` / `empty-state-notice--warn` CSS classes for unavailable-state panels, consistent `badge` / `badge-preview` / `badge-protected` patterns, and consistent `inp-readonly-notice` classes for read-only inputs. The CAPEX editable-cell gold standard (`fc-input-native`, `data-fc-editable`, `data-fc-raw`, `data-fc-kind`, `data-fc-addr`) is used consistently across CAPEX, OPEX, and Revenue sheets, established in PR1–PR5.

The `export-lineage-panel` block (lines 287–335 of `workspace_shell.html`) contains hardcoded strings "G20 BLOCKED" and "R99/R102 NOT APPROVED" but is wrapped in `{% if audit_mode %}`. Normal users never see this block (audit_mode is hardcoded False for normal sessions). Per the PR10 policy established for G20/R99/R102, audit_mode-gated governance content is acceptable for internal reviewers. This was intentionally not changed.

---

## Area 2: Sheet consistency

**Finding: No changes required.**

Every active sheet partial (`sheet_capex.html` through `sheet_tax.html`) has:
- `sheet-banner` div with `sheet-banner-tag` and `sheet-banner-badge` spans
- Section structure consistent with established patterns
- `inp-readonly-notice` for read-only cells (where applicable)
- `empty-state-notice--warn` for unavailable output panels (FS, Senior Debt, SHL, Tax)
- Consistent footer notes

`sheet_idc.html` exists on disk but has no corresponding tab, no include in `workspace_shell.html`, and no route — identified as an orphaned dead partial (see Area 8).

---

## Area 3: Navigation

**Finding: No changes required.**

Navigation is fully wired:
- 20 tabs in `workspace_tabs.html` each have a matching `id="panel-<value>"` in `workspace_shell.html`
- No duplicate tab IDs
- No dead links (all `href="#<panel>"` values resolve to existing panels)
- `panel-compare-mount` is an inner mounting point inside `panel-compare`, not a missing tab
- `panel-new-project` is a hidden slide-in panel for the New Project form, not a tab-linked panel

---

## Area 4: Terminology

**Finding: No changes required.**

Search confirmed:
- "C1", "C2", "Preview Architecture", "Runtime Pipeline" appear **only** in Jinja block comments (`{# ... #}`) in active templates — never in rendered HTML output
- "stub", "G20", "R99", "R102" appear only in Jinja comments or inside `{% if audit_mode %}` blocks
- "TODO", "FIXME" do not appear in any rendered text
- "Run" is used consistently (minor variation between "Run model" and "Run Model" exists but is acceptable — both are clear to users and not misleading)
- "CAPEX", "OPEX", "Revenue", "Senior Debt", "Tax", "Distribution", "Sponsor", "Export", "Scenarios", "Compare" are used consistently throughout navigation and sheet headers

---

## Area 5: Empty-state audit

**Finding: No changes required.**

Empty-state partials confirmed honest:
- `_empty_no_run.html` — explains why (no run yet) and what to do (click Run Model); no fake values
- `_empty_no_project.html` — explains next action; no fake values
- `_empty_no_scenario.html` — explains next action; no fake values
- `empty_states_notice.html` — no hardcoded financial figures, copy explains save→run flow
- All unavailable-output panels (`fs-unavailable-panel`, `sd-unavailable-panel`, `shl-unavailable-panel`, `tax-unavailable-panel`) explain why output is not available and what connects them

---

## Area 6: Runtime audit

**Finding: No changes required.**

- `runtime_summary.html` and `shared_runtime_block.html` exist and are included from `workspace_shell.html`
- `_last_run_indicator.html` exists
- Runtime status indicators in the workspace toolbar use `role="status"` and `aria-live="polite"` — values display correctly as "Idle" / "Preview executed" states
- No stale values: runtime indicators are populated by JS from server-sent data, not hardcoded
- No duplicated runtime values: the Operating Preview Panel (workspace_shell.html lines 392–561) consolidates all runtime indicators into one place (established in C2-PR21)

---

## Area 7: Accessibility quick audit

**Finding: No changes required.**

Key accessibility elements confirmed:
- `workspace-state-strip` div has `aria-label="Editable workspace state summary"`
- `workspace-lifecycle-panel` has `aria-label="Model lifecycle clarity"`
- `export-lineage-panel` has `aria-label="Export lineage summary"`
- Runtime status indicators all have `role="status"` and `aria-live="polite"` with descriptive `aria-label` strings
- Help panel has `aria-label="Help, onboarding, and model guidance"`
- Main form buttons ("Create project", "Close", "Run Model", "Save") have visible text labels
- Workspace tabs are `<button>` elements with text labels

No critical accessibility gaps found. All interactive elements have either `aria-label` attributes or visible text content.

---

## Area 8: Legacy cleanup

**Finding: One dead partial identified (sheet_idc.html). Retained on disk per conservative rule.**

Orphan survey results:

| Partial | Status | Notes |
|---------|--------|-------|
| `sheet_idc.html` | Dead — no tab, no include, no route | Retained. IDC (Interest During Construction) sheet was never wired to a tab in `workspace_tabs.html`. Safe to delete in a future cleanup PR if confirmed no external refs exist. |
| `audit_reconciliation_tab.html` | Referenced by `test_phase25a_pilot_product_polish_guided_workflow.py` | Retained. Existence-tested. |
| `_empty_state_message.html` | Phase 25C partial, not currently included | Retained. May be re-connected in future. |
| `_feedback_capture_panel.html` | Phase 25C partial, not currently included | Retained. |
| `_generic_pilot_script_panel.html` | Phase 25C partial, not currently included | Retained. |
| `_third_party_test_readiness.html` | Backed by `app/ui/third_party_test_readiness.py` | Retained — may be rendered via route not found in template includes. |
| `_validation_status_badge.html` | Formerly rendered via route | Retained. |
| `_dashboard_oob.html` | Rendered via OOB update in `main_web.py` | Not orphaned — wired to route. |
| `_matrix_cell_edit.html`, `_matrix_cell_updated.html`, `_matrix_run_result.html`, `_scenario_matrix_oob.html` | Rendered via routes in `main_web.py` | Not orphaned. |

Obsolete internal-reference comments (`C2-PR8`, `C2-PR10`, `C2-PR21`, etc.) in `workspace_shell.html` are inside Jinja block comments and are never rendered to users. They are retained as developer history notes — removing them would make the file harder to maintain without any user-visible benefit.

---

## Inconsistencies fixed

**None.** This final audit found no user-visible inconsistencies requiring fixes. All prior work (PR1–PR12, Stack A, Stack B) was thorough and complete.

---

## Inconsistencies intentionally left

| Item | Reason |
|------|--------|
| "G20 BLOCKED" / "R99/R102 NOT APPROVED" in `workspace_shell.html` Export Lineage panel | Inside `{% if audit_mode %}` block — reviewer-only, never shown to normal users. Per PR10 policy, audit_mode-gated governance content is acceptable. |
| `sheet_idc.html` on disk with no wired tab | Retained per conservative rule. Safe to delete in a dedicated cleanup PR after confirming no external references. |
| `C2-PR*` comments in `workspace_shell.html` | Jinja block comments only, never rendered. Developer history notes. |
| Minor "Run model" vs "Run Model" capitalisation variation | Not misleading. Both forms are clear to users. |

---

## Confirmation: Product Reality Gap Sprint complete

The Product Reality Gap Sprint (PR1–PR12, Stack A, Stack B, Stack C) is **complete**.

All known user-visible product gaps have been addressed:
- PR1–PR5: CAPEX, OPEX, Revenue Excel editing patterns
- PR6: Financial Statements (static tables → unavailable-state panels)
- PR7: Distribution/Sponsor (placeholder panels replaced)
- PR8: Senior Debt (output preview card replaced)
- PR9: Tax (G20/R99/R102 jargon removed from Tax tab, output preview replaced)
- PR10–PR12: Scenarios/Compare, Export, Dashboard (already honest; docs+tests only)
- Stack A (PR13–PR17): SHL empty-state fix, Save button loading indicator
- Stack B: OPEX/Revenue/FS already correct; docs+tests only
- Stack C (this PR): Final audit; docs+tests only

---

## Guardrail confirmation

The following files and directories were **not modified** on this branch:

- `domain/*` — all domain logic files
- `waterfall_core.py` — financial waterfall engine
- `input_adapter.py` — input adaptation layer
- `project_factories.py` — project factory logic
- All Run logic, Save logic, persistence logic
- Preview Architecture files
- Runtime Pipeline files
- Financial formulas

Changes on this branch are limited to:
- `tests/test_product_acceptance_stack_c_final_audit.py` (new test file)
- `docs/FINAL_PRODUCT_ACCEPTANCE_AUDIT.md` (this document)

---

## Recommendations for the next roadmap phase

1. **Delete `sheet_idc.html`** in a dedicated cleanup PR after confirming no external references outside the repository.

2. **Wire IDC tab** if Interest During Construction computation is planned — create `sheet_idc.html` (or repurpose the dead one) and add the tab to `workspace_tabs.html`.

3. **Connect Tax output** — `sheet_tax.html` currently shows an unavailable-state panel because no run-backed tax computation is wired. The next phase should connect the tax engine output.

4. **Connect Financial Statements** — `sheet_financials.html` shows unavailable panels for P&L, Cash Flow, and Balance Sheet. These are the most impactful screens for reviewer-facing output.

5. **Phase out orphaned Phase 25C partials** (`_empty_state_message.html`, `_feedback_capture_panel.html`, `_generic_pilot_script_panel.html`) or re-connect them — currently dead weight.

6. **Remove `C2-PR*` developer history comments** from `workspace_shell.html` in a future cleanup PR — they add noise without user value.
