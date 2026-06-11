# Phase P2-FIX-2 — Shell Strip / Move Governance-Lineage to Audit

**Branch:** `p2-fix-2-shell-strip`
**Base:** `main` @ `c8564fa` (post P2-FIX-1, post P2-min-4)
**Type:** presentation-only
**Status:** DRAFT (PR #616)

---

## Goal

Move internal governance, lineage, runtime-source and review-boundary content
out of the normal workspace shell and into Export & Audit / reviewer-only
surfaces. Normal-mode users see only:

- Project name
- technology / country / capacity chip
- status: Draft / Saved / Unsaved changes / Needs rerun / Run completed
- active scenario
- actions: Run / Save / Save As / Duplicate / Export
- Downloads where appropriate

The audit / reviewer surface (Audit / Reference tab) retains all relocated
information so reviewers can still see governance posture, runtime-source
flags, and review-boundary notes.

---

## Architecture (C2-aligned)

```
NORMAL MODE (audit_mode = False)            AUDIT MODE (audit_mode = True)
─────────────────────────────────            ──────────────────────────────
workspace overview (no governance,           full governance / lineage /
  no lifecycle panel, no review boundary)     lifecycle panel / review
                                                 boundary / G20 / R99 / R102
project input sheets (no G20/R99)            full G20 / R99 / R102 governance
                                                 status
Distributions / Sponsor placeholders         full "R99/R102 NOT APPROVED"
  (single "Internal-use model" line)            placeholder text
Inputs / Output sheets (no parity /          full parity workbooks /
  no factory / no reference terminology)       reference workbooks
sidebar (no G20 / R99 / R102 panel)          full Governance panel
                                                 (G20 Gate / R99/R102
                                                 Promotion)
```

The `audit_mode` context flag is plumbed through `main_web.py` into
`index.html` and `scenario_workspace.html`. Default is `False`. Reviewer
mode can be enabled via a future toggle without re-architecting.

The audit tab (`panel-audit`) ALWAYS renders the relocated content via
`partials/_audit_governance_relocated.html`, regardless of `audit_mode`.

---

## Files changed (32 files, ~+850 / -180 lines)

### New files

- `app/templates/partials/_audit_governance_relocated.html` (NEW, 9.5 KB)
  - Contains: Review boundary note, Lifecycle Clarity panel, Export Lineage
    panel, Governance Status card, Reference Evidence card. Rendered inside
    `panel-audit` (Audit / Reference tab). Includes `data-p2fix2-audit-relocated`
    attribute for test introspection.
- `tests/test_phase_p2fix2_shell_strip.py` (NEW, 20 tests, 5 test classes)
  - All tests pass.
- `docs/phase_p2fix2_shell_strip.md` (this doc)
- `reports/phase_p2fix2_shell_strip.md` (test report)

### Modified files (presentation only)

**Templates** (29 files):
- `app/templates/base.html` — wrap Governance sidebar in `{% if audit_mode %}`
- `app/templates/index.html` — wrap Governance Banner; replace blocked
  governance copy with neutral "Reference project" disclosure in normal mode
- `app/templates/partials/workspace_shell.html` — wrap Review boundary,
  Lifecycle panel, Export Lineage panel, Governance cards row, and
  Downloads-side Governance posture in `{% if audit_mode %}`; rename
  "Audit / Parity" tab to "Audit / Reference"
- `app/templates/partials/workspace_tabs.html` — same
- `app/templates/partials/_state_banner.html` — relabel "Factory template"
  → "Protected original"
- `app/templates/partials/_factory_lock_indicator.html` — relabel
- `app/templates/partials/inputs_section.html` — gate G20 / R99/R102 rows
  in `tax_rows`; fall back to neutral Tax Summary in normal mode
- `app/templates/partials/sheet_inputs.html` — relabel "Factory reference
  baseline" → "Protected reference project"
- `app/templates/partials/sheet_capex.html` — relabel data_source badge
- `app/templates/partials/sheet_capex_detail.html` — same
- `app/templates/partials/sheet_construction.html` — relabel
- `app/templates/partials/sheet_idc.html` — relabel
- `app/templates/partials/sheet_opex.html` — relabel
- `app/templates/partials/sheet_opex_detail.html` — relabel legend
- `app/templates/partials/sheet_revenue.html` — relabel
- `app/templates/partials/sheet_senior_debt.html` — relabel "static
  factory values" → "static reference values"
- `app/templates/partials/sheet_shl.html` — same
- `app/templates/partials/sheet_tax.html` — wrap G20 / R99/R102
  metrics in `{% if audit_mode %}`; ship neutral Tax summary in normal
- `app/templates/partials/sheet_financials.html` — relabel
- `app/templates/partials/scenario_tab.html` — relabel "Baselines cannot
  add scenarios" → "Reference projects cannot add scenarios"
- `app/templates/partials/scenario_compare.html` — relabel "governance
  posture" → "reviewer notes"
- `app/templates/partials/empty_states_notice.html` — "Audit / Parity" →
  "Audit / Reference"
- `app/templates/partials/pilot_help_onboarding.html` — relabel all
  "Audit / Parity" / "parity workbooks" / "parity evidence" /
  "parity anchors" / "parity-reviewed" → reference equivalents
- `app/templates/partials/pilot_limitations_notice.html` — same +
  "EXPLORATORY" / "parity-validated" → "Internal-use model" / "has
  reference evidence against Excel"
- `app/templates/partials/pilot_workflow_guide.html` — same
- `app/templates/partials/project_review_card.html` — relabel
  "Factory baseline" + "Exploratory Limitations" → "Protected original" /
  "Internal-use model notes"
- `app/templates/partials/debt_dscr_shl_panel.html` — relabel
- `app/templates/partials/export_registry.html` — relabel "parity
  evidence" / "parity" badge → "reference evidence" / "reference"
- `app/templates/partials/audit_reconciliation_tab.html` — relabel
- `app/templates/partials/new_project_form.html` — relabel
  "EXPLORATORY" / "exploratory" → "Internal-use model"

**UI presentation services** (2 files):
- `app/ui/dirty_state.py` — relabel "Factory baseline" / "Read-only
  baseline" → "Protected original" / "Read-only protected original"
- `app/ui/project_review.py` — relabel "R-PAR implementation" /
  "exploratory only" / "Excel-parity-validated" → "Pari-passu reserves
  ..." / "internal-use model only" / "Excel-validated"

**Routes** (1 file):
- `main_web.py` — add `audit_mode: False` to the workspace context
  (presentation only, default off)

---

## Hidden != deleted

The underlying data model is unchanged. The following internal literals
are still used by the data layer (and the audit surface) and are NOT
removed:

- `project_origin = factory_template` (data layer; lives in
  `app/persistence/projects_repository.py` and `db.py`)
- `saved_baseline` (data layer; same)
- `list_baseline_records()` (data layer; same)
- `capex_sub_lines` factory guard (`assert_project_allows_capex_sub_lines`,
  from P2-FIX-1)
- `use_construction_schedule_engine = False` (unchanged)

The P2-FIX-2 test suite pins this:

- `TestShellStripHiddenNotDeleted::test_factory_template_origin_literal_in_data_model`
- `TestShellStripHiddenNotDeleted::test_baseline_record_literal_in_data_model`

Both grep `app/persistence/` and assert that the literals are still
referenced. This is the data-model integrity guarantee.

---

## Tests (20 PASS)

| Test class | Tests | Verifies |
|---|---|---|
| `TestShellStripNormalMode` | 6 | Workspace overview, Inputs, Scenarios, Capex sheet, default route, placeholder notes — none of them contain forbidden terms in normal mode (after stripping the audit tab). |
| `TestShellStripAuditSurfacePreserved` | 7 | Audit tab contains the relocated information: Lifecycle Clarity, Export Lineage, Governance Status, G20 BLOCKED, R99/R102, Review boundary. |
| `TestShellStripNewProjectMinimal` | 1 | `/projects/new` minimal form does not contain forbidden terms. |
| `TestShellStripInvariants` | 4 | Workspace renders 200 OK for all 3 projects, "Protected original" wording present for TUHO, "Internal-use model" line present for generic project, audit_mode plumbed through. |
| `TestShellStripFileScope` | 1 | Only `app/templates/`, `app/ui/`, `main_web.py`, the test file, docs and reports are touched. No `app/persistence/`, `app/services/`, `main_api.py`, `static/app.js`, `app/waterfall_core.py`, `app/project_factories.py`, or `app/excel_export.py` changes. |
| `TestShellStripHiddenNotDeleted` | 2 | `factory_template` and `baseline` literals are still referenced in `app/persistence/`. |

**Total: 20 / 20 PASS.**

---

## Hard constraints preserved (verified)

- ✅ rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` preserved
- ✅ TUHO parity netaknut (no financial output change)
- ✅ Oborovo parity netaknut (no financial output change)
- ✅ `use_construction_schedule_engine` = False
- ✅ No formula / debt / DSCR / tax / IDC / construction / R-PAR / C10 / R99 / R102 / G20 promotion changes
- ✅ No persistence schema migration
- ✅ No `static/app.js` changes (0 lines diff)
- ✅ No `main_api.py` changes
- ✅ No route / CSS class / context-key / project_origin renames (backward compat preserved; only user-visible display text is relabeled)
- ✅ No new dependencies
- ✅ No Tailwind / Alpine / React / Vue / Svelte
- ✅ No Chart.js / Plotly / D3

---

## Stop-after-report

- PR #616 is **DRAFT** (not marked ready, not merged)
- Do NOT start P2-FIX-3 until P2-FIX-2 is approved
- Do NOT touch rc1, construction/C10/R-PAR, debt formulas, tax,
  depreciation, IDC, persistence schema, manual_gearing, Tailwind,
  factory path changes, R99/R102/G20 promotion

---

## P2-FIX arc roadmap (post-P2-FIX-2)

1. P2-FIX-1 (this PR) — MERGED @ `c8564fa`
2. P2-FIX-2 (this PR) — DRAFT #616
3. P2-FIX-3 — reference projects as normal projects using C2 first-edit / create-copy behavior
4. P2-FIX-4 — five-area navigation + dashboard landing + reviewer mode

`manual_gearing` is NOT on this roadmap.
