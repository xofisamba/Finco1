# Phase 54C — Design System, Tokens, and UI Copy Guardrails

## Context

Phase 54C specifies the design system (visual direction, typography,
spacing, component vocabulary) and the safe UI copy vocabulary
before any runtime implementation. **No runtime code changes. Docs/
report/test only.** Builds on 54A and 54B.

## Current Main SHA

`2c66cff8a1082ea44482a4199a4e5a48ddc40bf3` (post-54B merge)

## Visual Design Direction

### Color palette (recommended for UI-2)

**Base:**
- `--bg-slate-50`: `#f0f4f8` (current `--bg`)
- `--surface-white`: `#ffffff` (current `--surface`)
- `--border-light`: `#dde4ed` (current `--border`)
- `--border-strong`: `#c4cedd` (current `--border-strong`)

**Primary navy (sidebar / brand):**
- `--navy-900`: `#0f1b2d` (current `--sidebar-bg`)
- `--navy-800`: `#1e3a5f` (current `--sidebar-border`)
- `--navy-700`: `#1d3352` (current `--sidebar-hover`)
- `--navy-500`: `#1a56db` (current `--sidebar-active` / primary)

**Accent (controlled blue):**
- `--blue-primary`: `#1a56db` (current `--primary`)
- `--blue-hover`: `#1744b8` (current `--primary-hover`)

**Clean-energy muted green (secondary):**
- `--green-600`: `#0f7a52` (calm, finance-neutral)
- `--green-100`: `#e0f0e9` (chip background)

**Status (semantic):**
- `--status-pass`: `#0f7a52` (matches green-600, finance-neutral)
- `--status-warn`: `#b45309` (amber, not red)
- `--status-fail`: `#b91c1c` (deep red, not bright)
- `--status-info`: `#1a56db` (primary blue)

**Text:**
- `--text-primary`: `#0f1b2d` (navy-900, body)
- `--text-secondary`: `#475569` (slate-600, muted body)
- `--text-muted`: `#7a96b8` (current `--sidebar-muted`, meta)

**Light mode first; dark mode later.** The current `static/styles.css`
already uses this palette; UI-2 will formalize it via CSS custom
properties for the design tokens that are still implicit.

### Typography

- **Body font:** Inter (or system fallback `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`)
- **Monospace font:** `ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace`
- **Tabular numeric style:** `font-feature-settings: "tnum" 1, "lnum" 1;` for all numeric cells
- **Right-aligned numbers:** `text-align: right; font-variant-numeric: tabular-nums;` for finance cells
- **Sizes:**
  - `--text-xs`: 11px (chips, badges)
  - `--text-sm`: 13px (small body, table cells)
  - `--text-base`: 14px (default body)
  - `--text-md`: 16px (emphasized)
  - `--text-lg`: 18px (section headers)
  - `--text-xl`: 22px (KPI values)
  - `--text-2xl`: 28px (page headers)
  - `--text-3xl`: 36px (dashboard hero)

### Spacing and density

- `--space-1`: 4px (chip padding-y, badge gap)
- `--space-2`: 8px (input padding, table cell padding-x)
- `--space-3`: 12px (card padding)
- `--space-4`: 16px (section gap)
- `--space-6`: 24px (page gap)
- `--space-8`: 32px (hero block gap)

**Density modes:**
- **Dashboard cards:** 16px padding, 24px gap between cards
- **Dense grids (line items):** 8px row padding, 12px column gap
- **Sticky headers:** `position: sticky; top: 0;` (already used)
- **Sticky frozen columns:** `position: sticky; left: 0;` (UI-2 implementation)

## Component Vocabulary

### Chip (small, inline status indicator)

- **Use for:** Runtime Impact, validation state, source-locked
- **Anatomy:** Icon + label + (optional tooltip)
- **Variants:** drives, display-only, pending, needs-review, source-locked, fixture-backed, frozen-schedule
- **Implementation:** `<span class="chip chip-{state}">{icon} {label}</span>`

### Badge (small, context indicator)

- **Use for:** PASS / WARN / FAIL on audit reconciliation; scope notice
- **Anatomy:** Label only (no icon)
- **Variants:** pass, warn, fail, info
- **Implementation:** `<span class="badge badge-{state}">{label}</span>`

### Banner (page-level context strip)

- **Use for:** state clarity (factory / user / active / draft / etc.)
- **Anatomy:** Icon + title + (optional description) + (optional action)
- **Variants:** info, success, warn, fail, neutral
- **Implementation:** `<div class="banner banner-{tone}">{icon}<div>{title}{desc}</div>{action}</div>`

### Card (grouped content block)

- **Use for:** KPI cards, scenario summary, section content
- **Anatomy:** Title + body + (optional footer)
- **Implementation:** `<div class="card">{title}{body}{footer}</div>`

### Grid (line item table)

- **Use for:** CAPEX / OPEX / Revenue / etc.
- **Anatomy:** header + rows + (optional) sticky-left col, sticky-header
- **Implementation:** shared `LineItemGrid` macro/partial (54D spec)

### Section (page subdivision)

- **Use for:** tab panels, content sections
- **Implementation:** `<section class="section">{title}{body}</section>`

### Status pill (compact status)

- **Use for:** compact state in lists
- **Implementation:** `<span class="status-pill status-{state}">{label}</span>`

### Tooltip (hover/focus disclosure)

- **Use for:** sub-reason explanations on Runtime Impact chips
- **Implementation:** HTML `title` attribute initially, custom tooltip in UI-2 if needed

### Validation marker (cell-level indicator)

- **Use for:** input cell with validation issue
- **Anatomy:** icon-only on the cell border
- **Implementation:** `<span class="validation-marker validation-marker-{severity}"></span>`

## 4-State Runtime Impact Chip Standard

| State | Chip label | Color | Icon | Tooltip (full) |
|---|---|---|---|---|
| **Drives model** | "Drives model" | green-600 | ✓ | "Input is runtime-effective and directly affects calculation outputs." |
| **Display only** | "Display only" | slate-600 | ◯ | "Field is visible for reference but does not currently affect runtime calculations." |
| **Pending** | "Pending" | amber-600 | ⏳ | "Field is planned or captured but not yet wired to runtime." |
| **Needs review** | "Needs review" | red-600 | ⚠ | "Field has ambiguous mapping, unresolved source issue, or validation concern. Requires review." |

**Sub-reason tooltip text** (appended to main tooltip):
- "Timing only — used for construction timing/draw schedule only"
- "Reference only — shown for reference, not runtime-effective"
- "Pending treatment — captured but treatment is pending"
- "Pending runtime source — runtime source not yet connected"
- "Not comparable — scope mismatch prevents comparison"
- "Deferred — intentionally deferred"
- "Not applicable — does not apply to this project/scenario"
- "Fixture-backed — value comes from a fixture CSV, not runtime solver"
- "Frozen schedule — uses a frozen/scheduled value, not computed"
- "Source locked — source is locked (e.g., Excel calibration)"
- "Validation warning — has a validation concern"
- "Excel parity known gap — known difference from Excel, documented"

## State Clarity Banner Copy (11 contexts)

| Context | Banner title | Tone | Description |
|---|---|---|---|
| **Factory template** | "Factory template" | info | "This project uses a factory template. Some inputs are source-locked or fixture-backed." |
| **User-created project** | "User-created project" | info | "You created this project. All inputs are editable unless source-locked." |
| **Active scenario** | "Active scenario" | info | "Editing the active scenario updates the model in real time." (Note: "in real time" must NOT be used; use "as you save") |
| **Saved scenario** | "Saved scenario" | success | "Saved at {timestamp}. Scenario ID: {id}." |
| **Browser draft** | "Browser draft" | warn | "This is an unsaved browser draft. Close the tab and your changes may be lost." |
| **Dirty state** | "Unsaved changes" | warn | "This scenario has unsaved changes. Last saved at {timestamp}." |
| **Stale result** | "Stale result" | warn | "Inputs changed since last run. Re-run the model for current results." |
| **Last run** | "Last run: {timestamp}" | neutral | "Run completed at {timestamp}. Run ID: {id}." |
| **Validation failed** | "Validation failed" | fail | "Model run did not pass internal validation. See audit tab for details." |
| **Display-only row** | "Display only" | neutral | "This row is for reference. Editing is disabled." |
| **Pending runtime source** | "Pending runtime source" | warn | "This input is captured but the runtime source is not yet wired. Display only." |

**Rejection list (do NOT use these as banner copy):**
- ❌ "Live model"
- ❌ "Real-time results"
- ❌ "Auto-saved" (unless implemented)
- ❌ "Locked" (use "Saved" or "Versioned")
- ❌ "Production"
- ❌ "Bankable"
- ❌ "Audit-ready"

## No-Go UI Copy Scanner Specification

The scanner checks all user-facing text (template strings, partials, JS strings, services that return user-facing copy) against a forbidden list.

### Forbidden claims (BANNED in any UI copy)

- `bankable`, `bank-grade`
- `lender-ready`, `lender-grade`
- `certified`
- `audit-ready`, `audit-grade`
- `validated` (alone — only "model check" / "internal validation" allowed)
- `investor-ready`
- `SaaS-ready`
- `production-ready`
- `external validation`
- `customer reference`
- `investment advice`
- `guaranteed returns`

### Scanner rules

1. **Exact match:** Any template/comment/JS string containing a forbidden claim fails
2. **Context exemption:** Some words may appear in user docs as the
   negation of the claim (e.g., "Not lender-ready" is allowed)
3. **Implementation:** Phase 54E closeout adds a test that scans
   `app/templates/`, `static/`, and `app/services/` (read-only paths)
   for forbidden claims

### Safe UI terms (preferred)

- `model evidence` (instead of "validated")
- `reconciliation` (instead of "audit")
- `audit trail` (allowed, with clear "internal model audit" prefix)
- `validation checks` (instead of "validation")
- `review status` (instead of "approval")
- `internal confidence` (with clear heatmap context)
- `controlled pilot` (allowed)
- `source mapping` (allowed)
- `model provenance` (allowed)
- `internal model evidence` (allowed)

## Component token table (UI-2 implementation starter)

| Token | Value | Used for |
|---|---|---|
| `--chip-padding-y` | 2px | Runtime Impact chip vertical padding |
| `--chip-padding-x` | 8px | Runtime Impact chip horizontal padding |
| `--chip-radius` | 4px | chip corner radius |
| `--chip-font-size` | 11px | chip text size |
| `--badge-padding-y` | 2px | badge vertical padding |
| `--badge-padding-x` | 6px | badge horizontal padding |
| `--banner-padding` | 12px | banner content padding |
| `--banner-radius` | 6px | banner corner radius |
| `--banner-icon-size` | 16px | banner icon size |
| `--card-padding` | 16px | card inner padding |
| `--card-radius` | 8px | card corner radius |
| `--card-shadow` | 0 1px 2px rgba(15, 27, 45, 0.05) | card elevation |
| `--grid-cell-padding-y` | 8px | line item cell padding |
| `--grid-cell-padding-x` | 12px | line item cell padding |
| `--grid-border` | 1px solid var(--border) | grid cell border |
| `--grid-header-bg` | #f7f9fc | grid header background |
| `--grid-row-stripe` | #f7f9fc | even row background |

## Recommendation for 54D

Proceed to **Phase 54D — Shared LineItemGrid specification**:

1. Define the grid design grammar (rows × columns, frozen left col, sticky header)
2. Specify the required columns (code, line item, runtime impact, total, period values, source/audit, delta)
3. Specify cell states (input, calculated, display-only, pending, needs-review, validation issue)
4. Define the 8 variants (CAPEX, OPEX, Revenue, Debt/DSCR, SHL/Distribution, CFADS/Cash Flow, Scenario Compare, Audit/Reconciliation)
5. Specify the implementation plan (Jinja macro first, HTMX for mode swaps, Alpine later)
6. Define the context key contract candidates

## Hard Gates (54C)

- ✓ Only docs/report/test files added
- ✓ No templates/CSS/JS/services/persistence changes
- ✓ Branch based on post-54B main `2c66cff8a1082ea44482a4199a4e5a48ddc40bf3`
- ✓ Visual design direction specified
- ✓ Typography and spacing tokens defined
- ✓ 9 components in vocabulary
- ✓ 4-state Runtime Impact chip standard with exact copy and tooltips
- ✓ 11-context state clarity banner copy
- ✓ No-go UI copy scanner spec
- ✓ Allowed and forbidden copy examples
- ✓ rc1 (b425a07) untouched

## Files Created in 54C

- `docs/phase54c_design_system_tokens_copy_guardrails.md` (this file)
- `reports/phase54c_design_system_tokens_copy_guardrails.json`
- `tests/test_phase54c_design_system_tokens_copy_guardrails.py` (guardrail)
