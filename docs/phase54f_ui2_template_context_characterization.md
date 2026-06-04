# Phase 54F — UI-2 Template/Context Characterization Map

## Context

Phase 54F maps current templates and context keys that UI-2 will
touch **before** any runtime implementation. **No runtime code
changes. Docs/report/test only.** This is the first phase of the
54F-54J pre-implementation characterization block.

## Current Main SHA

`3c55439ef935ec91e1f3bb8c5e6e736041ff4a6c` (post-54E merge)

## UI-2 planned items (from 54E)

1. State clarity banner partial
2. Runtime Impact chip partial
3. Validation summary bar
4. Factory lock indicator
5. Stale result warning
6. Run-source indicator

## Target template inventory

### Per UI-2 item

#### UI-2.1 — State clarity banner partial

- **Target:** `app/templates/index.html` (current `gov-banner` div is a one-off governance banner; UI-2 will add general-purpose banner partial)
- **Likely new file:** `app/templates/partials/_state_banner.html` (Jinja partial)
- **Will be included in:** `index.html`, `scenario_workspace.html`, `workspace_shell.html` (likely 2-3 includes)
- **Tone of change:** additive only (new partial, no removal)

#### UI-2.2 — Runtime Impact chip partial

- **Target:** `app/templates/partials/sheet_capex_detail.html` (current inline chip)
- **Current pattern:** `<span class="badge badge-rt badge-rt-{{ rt_class }}" title="{{ _rt_tooltip(rt) }}">{{ rt }}</span>`
- **Helper:** `_rt_tooltip(rt)` defined in this sheet
- **Likely new file:** `app/templates/partials/_runtime_impact_chip.html` (Jinja partial)
- **Will be included in:** `sheet_capex_detail.html` (replace inline), and `audit_reconciliation_tab.html` (uses "Drives model" as `audit-row-status` class — could be migrated)
- **Tone of change:** additive, replaces inline chip in 1-2 sheets

#### UI-2.3 — Validation summary bar

- **Target:** `app/templates/partials/audit_reconciliation_tab.html` (top of the tab)
- **Current state:** `audit-row-status` spans show individual check results; no top-level summary
- **Likely new file:** `app/templates/partials/_validation_summary_bar.html`
- **Will be included in:** `audit_reconciliation_tab.html` (top)
- **Tone of change:** additive

#### UI-2.4 — Factory lock indicator

- **Target:** `app/templates/partials/workspace_shell.html` (or `index.html`)
- **Current state:** No factory lock indicator. `pilot_limitations_notice.html` mentions "TUHO / Oborovo frozen-template" as text.
- **Likely new file:** `app/templates/partials/_factory_lock_indicator.html`
- **Will be included in:** `workspace_shell.html` or `index.html`
- **Tone of change:** additive

#### UI-2.5 — Stale result warning

- **Target:** `app/templates/index.html` (top of model output area)
- **Current state:** `empty_states_notice.html::stale_run()` macro already exists with exact copy "Stale run" + "⏱️" icon + warning text
- **Likely new file:** None (reuse existing `stale_run()` macro)
- **Will be included in:** `index.html` (top of `runtime_summary.html` block)
- **Tone of change:** additive, reuses existing macro

#### UI-2.6 — Run-source indicator

- **Target:** `app/templates/partials/runtime_summary.html` (top of `run-banner`)
- **Current state:** `rs-provenance-banner` already shows scenario name + data source label + `ran_at` timestamp + status badge. Almost all the data is there.
- **Likely new file:** `app/templates/partials/_last_run_indicator.html` (compact version, for use outside `runtime_summary.html`)
- **Will be included in:** `index.html` (top), `scenario_workspace.html` (top), maybe `kpis.html`
- **Tone of change:** additive, may include in 2-3 places

## Context key inventory (per target template)

### `app/templates/index.html` (current)

- **Variables used:** None (only the static `gov-banner` block)
- **Service source:** None directly (governance banner is hardcoded G20 status)

### `app/templates/partials/runtime_summary.html` (UI-2.5, UI-2.6 target)

- **`runtime_summary` dict** with keys:
  - `project_name` (str)
  - `active_scenario_name` (str, optional)
  - `data_source_label` (str, optional)
  - `ran_at` (str, formatted timestamp)
  - `status` (str, "ok" or "error")
  - `project_irr`, `equity_irr`, `avg_dscr`, `senior_debt_keur`, `total_revenue_keur`, `total_ebitda_keur`, `total_opex_keur`, `total_distributions_keur` (each can be `NOT_AVAILABLE`)
  - `error_message` (str, optional)
- **`messages`:** list of strings
- **Service source:** `run_service` builds `runtime_summary` from `runs_repository.get_run(...)` + `scenarios_repository.get_scenario(...)` + `projects_repository.get_project(...)`
- **Existing data fields useful for UI-2:**
  - `ran_at` (timestamp) — for UI-2.6
  - `data_source_label` — for UI-2.4 factory lock
  - `status` (ok/error) — for UI-2.6
  - `active_scenario_name` — for UI-2.6
- **Missing keys for UI-2:** None for UI-2.5/UI-2.6 (current data is sufficient)

### `app/templates/partials/sheet_capex_detail.html` (UI-2.2 target)

- **`child` dict** (per line item):
  - `code`, `name` (str)
  - `runtime_impact` (str, e.g., "Drives model", "Display only", "Pending", "Needs review")
  - `values[]` (per period)
  - sub-reason: stored in `runtime_impact` or a separate field — needs investigation
- **Helper:** `_rt_tooltip(rt)` defined inline
- **Service source:** `sheet_capex_detail` is rendered by the project editor route
- **Existing data fields useful for UI-2:**
  - `runtime_impact` (the 4-state value) — sufficient for UI-2.2
- **Missing keys for UI-2:** Sub-reason tooltip text is computed via `_rt_tooltip` (a local function in the template). For UI-2 partial, this should be moved to a shared helper or `runtime_impact_taxonomy.py`.

### `app/templates/partials/audit_reconciliation_tab.html` (UI-2.3 target)

- **Variables used:** (need full investigation; partially read)
- **Current state:** Many `audit-row-status` spans with PASS/WARN/FAIL text
- **Existing data fields useful for UI-2:**
  - Audit check results: pass / warn / fail counts
  - Scope notice: "TUHO / Oborovo only"
  - Source-locked / fixture-backed markers
- **Missing keys for UI-2:** Top-level summary (pass count, warn count, fail count, last validated timestamp) — **need backend to expose** these. Either via existing `validation_service` or by adding a new context builder.

### `app/templates/partials/workspace_shell.html` (UI-2.4 target)

- **Variables used:** Project + scenario context
- **Existing data fields useful for UI-2:**
  - Project `factory_template` flag (need to verify if this exists)
  - Or use `data_source_label` from runtime_summary
- **Missing keys for UI-2:** A clean `is_factory_template: bool` field on the project context. **Need to verify if this exists** in the project context.

## Route/service context sources

### `main_web.py` routes (read-only inspection)

- `runtime_summary` is rendered into a partial that gets HTMX-swapped into the model output area
- `index.html` extends `base.html` and includes `workspace_shell.html`
- `scenario_workspace.html` is the scenario-specific shell

### Services that produce these contexts (read-only inspection)

- `app/services/scenario_state_service.py` — builds scenario state for `index.html` / `workspace_shell.html`
- `app/services/run_service.py` — runs model, produces `runtime_summary`
- `app/services/save_run_service.py` — saves run output
- `app/services/projects_create_service.py` — creates new project
- `app/services/project_save_as_service.py` — duplicate as

### `app/runtime_impact_taxonomy.py` (existing)

- 4-state taxonomy
- Legacy mapping for backward compat
- 12 sub-reason tooltips
- This is the canonical source for UI-2.2 chip copy

## Existing status patterns

### Banner classes (current)

- `.gov-banner` / `.gov-blocked` — governance banner (current, hardcoded in `index.html`)
- `.error-banner` — error banner (current, in `error_banner.html`)
- `.pilot-limitations-notice` — pilot limitations (current, in `pilot_limitations_notice.html`)
- `.empty-state-notice` — empty state (current, in `empty_states_notice.html`)
- `.alert` / `.alert-error` / `.alert-info` — alerts (current, in `validation.html`)
- `.run-banner` — run summary banner (current, in `runtime_summary.html`)

### Status badges (current)

- `.badge` + tone variants: `.badge-pass`, `.badge-warn`, `.badge-blocked`, `.badge-info`, `.badge-runtime`
- `.badge-rt` + 4 state variants: `.badge-rt-drives-model`, `.badge-rt-display-only`, `.badge-rt-pending`, `.badge-rt-needs-review`
- `.audit-row-status` — current inline status text in audit reconciliation
- `.run-type-badge`, `.run-scenario-badge` — in run history

### Chip vs badge

- Currently using `.badge` for both chip and badge semantics
- UI-2 will introduce `.chip` as a new class for the Runtime Impact chip standard
- `.badge` remains for status badges (PASS/WARN/FAIL)

## Missing context keys for UI-2

| Key | Needed for | Backend status |
|---|---|---|
| `is_factory_template: bool` | UI-2.4 factory lock | **Verify**: may need backend addition |
| `is_browser_draft: bool` | UI-2.1 dirty state banner | **Verify**: may need backend addition |
| `is_saved: bool` | UI-2.1 saved scenario banner | **Verify**: may need backend addition |
| `validation_summary: { pass: int, warn: int, fail: int, last_validated_at: str }` | UI-2.3 validation summary bar | **Verify**: may need backend addition |
| `inputs_changed_since_run: bool` | UI-2.5 stale result warning | **Verify**: may need backend addition |
| `sub_reason: str` (per runtime_impact) | UI-2.2 sub-reason tooltip | Likely present, needs verification |

**Action:** Phase 54G will specify which missing keys require backend
changes (and how to defer them if so).

## UI-2 risk matrix

| UI-2 item | Risk | Reason | Auto-merge eligible? |
|---|---|---|---|
| UI-2.1 state banner | low | New partial, additive, well-spec'd | NO (first runtime change) |
| UI-2.2 runtime chip | low | New partial, replaces inline chip in 1 sheet | NO |
| UI-2.3 validation bar | low-medium | Needs backend `validation_summary` key | NO |
| UI-2.4 factory lock | low-medium | Needs backend `is_factory_template` key | NO |
| UI-2.5 stale warning | low | Reuses existing `stale_run()` macro | NO |
| UI-2.6 run-source | low | Mostly display, may need data rearrangement | NO |

## Must-not-change list (54F)

In addition to the 54E must-not-change list:

- **All current templates are NOT to be removed or rewritten** —
  only minimal additive changes (a new partial + a single include)
- **CSS variables** (`:root` block in `static/styles.css`) are
  not to be changed — only additive class definitions
- **`_rt_tooltip(rt)` helper** in `sheet_capex_detail.html` is
  not to be removed until the new chip partial is verified
- **`runtime_summary` dict** shape is not to change — UI-2.6
  uses existing keys
- **rc1 (b425a07)** remains frozen

## Recommendation for 54G

Proceed to **Phase 54G — UI-2 implementation boundary and test plan**:

1. For each UI-2 item, specify exact files that change
2. Define allowed context keys (existing + new)
3. Specify which tests are required (snapshot, string, no-go copy)
4. Define manual review checklist
5. Define rollback plan
6. Confirm auto-merge policy: NONE for runtime UI changes

## Hard Gates (54F)

- ✓ Only docs/report/test files added
- ✓ No templates/CSS/JS/services/persistence changes
- ✓ Branch based on post-54E main `3c55439ef935ec91e1f3bb8c5e6e736041ff4a6c`
- ✓ Target template inventory for all 6 UI-2 items
- ✓ Context key inventory per target
- ✓ Route/service context sources traced
- ✓ Existing status patterns documented
- ✓ Missing context keys identified
- ✓ UI-2 risk matrix defined
- ✓ Must-not-change list extended
- ✓ rc1 (b425a07) untouched

## Files Created in 54F

- `docs/phase54f_ui2_template_context_characterization.md` (this file)
- `reports/phase54f_ui2_template_context_characterization.json`
- `tests/test_phase54f_ui2_template_context_characterization.py` (guardrail)
