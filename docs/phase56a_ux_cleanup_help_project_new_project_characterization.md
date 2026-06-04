# Phase 56A — UX cleanup characterization: Help, Project switch, New Project flow

## Status

DRAFT, docs-only inventory. No runtime changes. No template/CSS/JS changes.

## Current main SHA

`12b82ca9ecd2fb6629c5238dad2d2938ec4694ac` (post-Phase 55G)

## 1. Current Help inventory

### Help content locations

| File | LOC | Where included | Content type |
|---|---:|---|---|
| `app/templates/partials/pilot_help_onboarding.html` | 222 | `workspace_shell.html` Overview tab | **Full Help block** with 4 sections: What is FincoGPT, Validated templates, Demo/Pilot mode, How to run a pilot workflow |
| `app/templates/partials/pilot_workflow_guide.html` | ~80 | `workspace_shell.html` Overview tab | **Pilot Workflow Guide** (5-step stepper) |
| `app/templates/partials/pilot_limitations_notice.html` | small | `workspace_shell.html` (referenced) | **Limitations notice** |
| Inline help in `app/templates/partials/inputs_section.html` | small | Inputs tab | Micro-help on input section |
| Inline help in `app/templates/partials/sheet_capex.html` | small | CAPEX sheet | Sheet-level contextual help |

### User-facing copy in current Help

The 222-line `pilot_help_onboarding.html` includes:

- "[Validated] TUHO Wind (72 MW, Croatia) - frozen-template, parity-validated against Excel"
- "[Validated] Oborovo Solar (53.63 MW, Croatia) - frozen-template, parity-validated against Excel"
- "[Warning] Generic / new projects - unvalidated; assumptions and outputs should be reviewed independently"

The word **"validated"** appears as a positive claim, which is on the no-go list. The Help block as currently written risks a no-go claim. This needs to be rephrased in a future PR (e.g., "trustworthy pilot evidence" or "frozen-template pilot evidence" instead of "validated").

### Where Help appears

- Help appears on the **Overview tab** in `workspace_shell.html` (line ~205-209).
- Help is **NOT** shown on each sheet by default. The 222-line block is the single biggest piece of inline help in the app.
- `pilot_workflow_guide.html` is also on the Overview tab.

### What should move to a dedicated Help sidebar section

The full `pilot_help_onboarding.html` block (222 lines) should move to a **dedicated Help sidebar section/page**:

- What is FincoGPT
- Validated templates (with safer language: "trusted pilot evidence" instead of "validated")
- Demo / Pilot mode
- How to run a pilot workflow
- Limitations notice
- Pilot workflow guide (the stepper)

### What should remain as contextual micro-help

- Sheet-level micro-help in `inputs_section.html` and `sheet_capex.html` (small inline notes only).
- Tooltip-style hints in form fields (e.g., "What's a P50 hours?") — these stay in form, not in main Help.

## 2. Current sidebar/project switch inventory

### Sidebar partials

- `app/templates/partials/project_selector.html` (185 LOC) — main sidebar project card.
- `app/templates/partials/project_browser.html` — main-area project browser (factory, baselines, user).

### Current sidebar state display

The sidebar shows:
- Active project type badge (Wind/Solar)
- Active project name
- Active scenario (if any)
- Project code (small meta)
- State badges: "Unsaved changes" / "Saved"
- Quick action buttons: "Load / Switch" and "New Project"

### Current Load/Switch behavior

- User clicks "Load / Switch" in the sidebar
- A modal-like panel opens in the main area (`project_browser.html`)
- Three tabs: "Factory Templates", "Saved Baselines", "My Projects"
- User clicks a project card → calls `switchToProject(project_code)` JS function
- Page reloads to load the new project

### Current New Project behavior

- User clicks "New Project" in the sidebar
- The `panel-new-project` div in `workspace_shell.html` shows `new_project_form.html`
- Form has 13 fields (see section 3)
- User fills form, submits → POST `/projects/create` → reload

### User confusion points

1. **Three sidebar buttons / 2 action buttons** + the project state display can be overwhelming.
2. **Debug-style labels** in the active project card: e.g., `ps-ap-meta` shows the raw `project_code` which is a slug like `tuho-2026-wind-01`. This looks like a debug value to the user.
3. **State badges are tight** — "Unsaved changes" + "Saved" badge can appear simultaneously in some flows.
4. **The "New Project" button is small** and tucked into the quick actions. There's no clear "switch vs create" hierarchy.
5. **No clear "what project am I in right now" answer** for a new user — the workflow guide is needed but is on the Overview tab.

### Proposed simplified navigation

- **Sidebar top**: large active project card (type + name + scenario) — simpler.
- **Below the card**: a single line "Load / Switch" + "New Project" — but bigger, more discoverable.
- **Hide debug labels** (project_code) by default; show only on hover or in an expanded view.
- **Move Help to a dedicated Help section** so it doesn't compete for the Overview tab real estate.

## 3. Current New Project form inventory

### Current fields (13)

In `app/templates/partials/new_project_form.html` (100 lines):

| Field | Type | Currently required | Affects formulas? | Should stay? |
|---|---|---|---|---|
| project_name | text | yes | yes | YES — master data |
| project_type | select | yes | yes | YES — master data |
| template_source | select | yes | yes | YES — master data |
| country_market | text | yes | yes | YES — master data |
| capacity_mw | number | yes | yes | YES — master data |
| cod_date | date | yes | yes | **REPLACE: derive from start + duration** |
| construction_months | number | yes | yes | YES — keep (used to derive COD) |
| horizon_years | number | yes | yes | **MOVE to Inputs** |
| tariff_eur_mwh | number | yes | yes | **MOVE to Inputs** |
| ppa_term_years | number | yes | yes | **MOVE to Inputs** |
| p50_hours | number | yes | yes | **MOVE to Inputs** |
| opex_y1_keur | number | yes | yes | **MOVE to Inputs** |
| total_capex_keur | number | yes | yes | **MOVE to Inputs** |
| gearing_pct | number | yes | yes | **MOVE to Inputs** |
| interest_rate_pct | number | yes | yes | **MOVE to Inputs** |
| tenor_years | number | yes | yes | **MOVE to Inputs** |
| target_dscr | number | yes | yes | **MOVE to Inputs** |

That's 17 fields total. The user is asked to fill in 17 inputs on the create form, but only 6 are real master data.

## 4. Proposed New Project v1 form

### Fields (10 master data + 1 derived)

| Field | Type | Required | Notes |
|---|---|---|---|
| `project_name` | text | yes | Master data |
| `spv_name` | text | yes | **NEW**: SPV / company name (was missing) |
| `country_or_market` | text | yes | Master data (renamed from `country_market`) |
| `technology` | select | yes | **RENAMED** from `project_type` to `technology` (cleaner copy: solar / wind) |
| `capacity_mw` | number | yes | Master data |
| `currency` | select | yes | **NEW**: EUR / USD / HRK (defaults to EUR) |
| `construction_start_date` | date | yes | **NEW**: replaces "COD date" as the primary input |
| `construction_duration_months` | number | yes | **RENAMED** from `construction_months` for clarity |
| `cod_date` | derived | read-only | **DERIVED**: `construction_start_date + construction_duration_months` |
| `template_source` | select | yes | Generic Solar / Generic Wind (with ⚠️ Unvalidated label) / TUHO / Oborovo (trusted pilot evidence) |

### Explicitly excluded from initial create form

These move to **Inputs** (which is the next step after project creation):

- `horizon_years`
- `tariff_eur_mwh` (PPA tariff)
- `ppa_term_years`
- `p50_hours`
- `opex_y1_keur`
- `total_capex_keur`
- `gearing_pct`
- `interest_rate_pct`
- `tenor_years`
- `target_dscr`
- Tax assumptions (deferred to Inputs)
- SHL assumptions (deferred to Inputs)
- Advanced construction schedule (deferred to Inputs)

After project creation, the project is saved to the DB, then the user is redirected to the new project with the Inputs tab active, so they can fill in the detailed assumptions.

## 5. COD calculation policy

### Formula

```
COD = construction_start_date + construction_duration_months
```

### Date convention

- Same day-of-month if possible (e.g., March 15 + 6 months = September 15).
- Month-end handling: if the start is January 31 and duration is 1 month, the result is February 28 (or 29 in a leap year). Python's `dateutil.relativedelta` handles this correctly.
- Leap-year handling: `relativedelta(months=+N)` correctly handles February 29 → February 28 in non-leap years.
- Validation: missing or invalid duration must produce a clear error.

### Display

- **COD shown read-only in the create form** (no input field).
- Calculated client-side in JavaScript for live preview (NOT a financial calculation — purely a date arithmetic), or calculated server-side on form submission.

### Manual override

- Manual COD override is **deferred** and must be:
  - **Explicit**: a separate "Override COD" toggle that the user has to enable.
  - **Audited**: any override is recorded in the project record's `replay_metadata` so it's reviewable.
- **NOT a default**: by default, COD is always derived.

## 6. Proposed implementation phases

### 56B — Help section: remove full inline help from sheets and Overview

- **Objective**: move the 222-line `pilot_help_onboarding.html` and `pilot_workflow_guide.html` out of the Overview tab into a dedicated Help sidebar section.
- **Allowed files**:
  - `app/templates/partials/help_section.html` (NEW, 1-line stub to start)
  - `app/templates/partials/workspace_shell.html` (remove help includes, add Help tab)
  - `app/templates/partials/sidebar_help_link.html` (NEW, if needed)
  - `static/styles.css` (additive only — no class removals)
  - `tests/test_phase56b_*.py`
  - `docs/phase56b_*.md`, `reports/phase56b_*.json`
- **Tests**: snapshot test of Help section render; no-go copy check (rephrase "validated" → "trusted pilot evidence").
- **Risk**: LOW. Help content is moved, not removed. We can always link to the original locations during a deprecation period.
- **Auto-merge**: NO (visual review required).
- **Visual review**: REQUIRED before merge. User must see the new Help section.

### 56C — New Project v1 form simplification

- **Objective**: trim the create form to 10 master data fields. Move 11 detailed assumption fields to Inputs.
- **Allowed files**:
  - `app/templates/partials/new_project_form.html` (replace with v1)
  - `app/services/projects_create_service.py` (deprecate old fields, accept new ones, default detailed fields)
  - `app/persistence/projects_repository.py` (default values for omitted fields)
  - `main_web.py` (update `/projects/create` Form() to match)
  - `tests/test_phase56c_*.py` (and update existing `test_phase51m1_*`, `test_phase51m2_*` if needed)
  - `docs/phase56c_*.md`, `reports/phase56c_*.json`
- **Tests**:
  - Old fields still accepted for backward compat (deprecated, not removed).
  - New minimal fields create a project.
  - Project is saved to DB with safe defaults for omitted fields.
  - After creation, user is redirected to Inputs tab.
- **Risk**: MEDIUM. Changing the create form is user-visible. The 11 fields can be set as defaults; the user fills them in later. This is a UX win, not a behavior change.
- **Auto-merge**: NO (visual review required).
- **Visual review**: REQUIRED before merge.

### 56D — COD derived field wiring

- **Objective**: add the derived `cod_date` field; remove the manual input; ensure backward compat for projects created before 56D.
- **Allowed files**:
  - `app/templates/partials/new_project_form.html` (replace manual input with read-only)
  - `app/services/projects_create_service.py` (compute COD)
  - `app/persistence/projects_repository.py` (validate COD matches start+duration for new projects)
  - `main_web.py` (no Form() change — derived server-side)
  - `tests/test_phase56d_*.py`
  - `docs/phase56d_*.md`, `reports/phase56d_*.json`
- **Tests**:
  - COD computation correctness (including leap year, month-end).
  - Old projects with manual `cod_date` still work.
  - New projects always have `cod_date = start + duration`.
- **Risk**: LOW. Computation is deterministic. Old data is preserved.
- **Auto-merge**: NO (visual review required).
- **Visual review**: REQUIRED before merge.

### 56E — Project switch simplification

- **Objective**: simplify the sidebar so that "Load / Switch" and "New Project" are more discoverable; hide debug labels by default; clean up the active project card.
- **Allowed files**:
  - `app/templates/partials/project_selector.html` (cosmetic cleanup)
  - `app/templates/partials/project_browser.html` (cosmetic cleanup)
  - `static/styles.css` (additive only)
  - `tests/test_phase56e_*.py`
  - `docs/phase56e_*.md`, `reports/phase56e_*.json`
- **Tests**:
  - Active project card shows clean labels.
  - `project_code` is hidden by default, available on hover.
  - No debug labels (no `ps-ap-meta` visible without expansion).
  - Load/Switch and New Project buttons are big and discoverable.
- **Risk**: LOW. Cosmetic changes only.
- **Auto-merge**: NO (visual review required).
- **Visual review**: REQUIRED before merge.

### 56F — State banner visual hierarchy polish

- **Objective**: make state banners and governance cards less visually dominant. Keep the functionality, improve hierarchy.
- **Allowed files**:
  - `static/styles.css` (additive `.banner-tone-*` rules, smaller padding/typography)
  - `app/templates/partials/_state_banner.html` (optional small markup change)
  - `tests/test_phase56f_*.py`
  - `docs/phase56f_*.md`, `reports/phase56f_*.json`
- **Tests**:
  - No regression in banner content / context keys.
  - Visual hierarchy improved (smaller, less dominant).
  - No no-go copy.
- **Risk**: LOW. Style only.
- **Auto-merge**: NO (visual review required).
- **Visual review**: REQUIRED before merge.

### 56G — UX cleanup closeout + visual review

- **Objective**: final visual review + Agent B governance refresh + live no-go scanner implementation.
- **Allowed files**:
  - docs/report/test only
  - live no-go scanner (if not yet implemented)
- **Tests**: visual review checklist.
- **Risk**: LOW. Closeout.
- **Auto-merge**: NO (visual review required).

## 7. Risk review

| Risk | Severity | Mitigation |
|---|---|---|
| Changing project creation too soon | MEDIUM | 56C accepts old fields for backward compat. Detailed fields get safe defaults. |
| Hiding useful Help | MEDIUM | 56B moves Help, doesn't delete it. Old locations can be linked during a transition period. |
| Moving assumptions out of create form | MEDIUM | Detailed fields get safe defaults (zero or baseline values) so the project can be created. User fills them in Inputs. |
| COD date calculation | LOW | `relativedelta` is well-tested; leap year and month-end are handled. |
| Generic solar/wind appearing validated | HIGH | Use the existing `⚠️ Unvalidated · Derived path` label from `NEW_PROJECT_TEMPLATE_OPTIONS`. Never use the word "validated" as a positive claim. |
| Confusing factory templates vs generic projects | HIGH | Already addressed by tab separation in `project_browser.html` (Factory Templates vs Saved Baselines vs My Projects). Plus the existing `badge-muted` for factory and `badge-pass` for user. |
| Visual regression | MEDIUM | Visual review required on every runtime PR. |
| Loss of `ps-ap-meta` debug info | LOW | Keep it in the HTML, just hide via CSS. Can be re-enabled for support. |
| Help block contains the word "validated" | HIGH | The 222-line `pilot_help_onboarding.html` block literally says "[Validated]". This must be rephrased in 56B. |

## 8. Recommendation

**Recommended next implementation PR: 56B — Help section.**

Rationale:

1. **Lowest model risk**: Help is moved, not removed. No backend/persistence changes. No financial changes.
2. **No-go copy fix**: 56B rephrases "validated" → "trusted pilot evidence" or similar, removing a no-go claim.
3. **Visual improvement immediate**: removing the 222-line inline Help block from the Overview tab makes the page much cleaner.
4. **Sets the pattern**: 56B establishes the "Help = dedicated section" pattern that 56E can also use for the sidebar.

After 56B, the natural order is:

1. **56E** (project switch simplification) — also LOW risk, also visual.
2. **56F** (state banner polish) — LOW risk, style only.
3. **56C** (new project v1) — MEDIUM risk, but well-tested.
4. **56D** (COD derived) — LOW risk, computation only.
5. **56G** (closeout) — docs only.

## Hard gates verified (this PR)

- ✓ Only docs/report files added
- ✓ No production code changed
- ✓ No templates changed
- ✓ No static CSS/JS changed
- ✓ No frontend dependency changes
- ✓ No app/services, app/persistence changes
- ✓ No main_web.py changes
- ✓ No model/parity-core/schema/formula/fixture changes
- ✓ No no-go UI claims introduced (this is a characterization; future PRs must rephrase "validated" copy)
- ✓ rc1 SHA `b425a07` untouched
- ✓ 707 relevant tests pass

## Recommended next step

**56B — Help section: remove full inline help from sheets and Overview.**
