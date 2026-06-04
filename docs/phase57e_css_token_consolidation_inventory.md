# Phase 57E — CSS token consolidation inventory and plan

## Status

DRAFT → marked ready → squash merged in the 57E overnight branch
(see `reports/phase57e_css_token_consolidation_inventory.json`
for the merge SHA).

This is a **docs/report/test-only inventory**. No CSS changes
in 57E. The proposed CSS work is a follow-up PR (57E-1 or
similar) that must be approved by the user before
implementation.

## Current main SHA (start of 57E)

`4194aef753ecc50f00e0827081dc6b718f7e2bd3` (post-57D, Live
no-go copy scanner merged)

## Current main SHA (after 57E)

Reported in the 57E combined report.

## rc1 frozen SHA

`b425a0708719eaa5e1d922b1008e5609758e0ad4` — must remain
untouched throughout the 57E-1 follow-up CSS work as well.

## Current CSS state (snapshot)

### `static/styles.css` size
- 5,018 lines (5,018 LOC, post-57A)
- 594 unique class selectors (rough count via
  `grep -oE '^\.[a-zA-Z][a-zA-Z0-9_-]+' static/styles.css | sort -u | wc -l`)
- 81 total `:root` block custom properties (across 3 `:root` blocks)

### `:root` blocks
- **Block 1** — `static/styles.css:10` (main design tokens)
- **Block 2** — `static/styles.css:828` (typography tokens)
- **Block 3** — `static/styles.css:2695` (cell / runtime tokens)

The 3 `:root` blocks are spread across the file. This makes
maintenance harder than necessary. Consolidation is a logical
first step before any Tailwind work.

### Custom property inventory

#### Block 1 (main design tokens, ~62 props)
- Sidebar (8): `--sidebar-bg`, `--sidebar-border`,
  `--sidebar-section`, `--sidebar-hover`, `--sidebar-active`,
  `--sidebar-text`, `--sidebar-muted`, `--sidebar-badge-bg`
- Content area (5): `--bg`, `--surface`, `--surface-2`,
  `--border`, `--border-strong`
- Accents (8): `--primary`, `--primary-hover`,
  `--primary-light`, `--accent`, `--accent-hover`,
  `--accent-light`, `--teal`, `--teal-light`
- Status badges (12): `--pass-bg/-text/-border`,
  `--warn-bg/-text/-border`, `--blocked-bg/-text/-border`,
  `--convention-bg/-text/-border` (4 badge families)
- + others (text colors, shadows, etc.)

#### Block 2 (typography, ~2 props)
- `--font-sans`
- `--font-mono`

#### Block 3 (cell / runtime tokens, ~17 props)
- `--color-accent` (alias of `--accent`)
- `--border-subtle`, `--border-muted`
- `--cell-pad-v`, `--cell-pad-h`, `--cell-h`
- `--font-cell`, `--font-label`, `--font-badge`
- `--cell-inherited-bg`, `--cell-override-bg`,
  `--cell-base-bg`, `--cell-runtime-bg`,
  `--cell-factory-bg`, `--cell-warning-bg`,
  `--cell-error-bg`, `--cell-dirty-bg`

### Duplicate / overlapping tokens

- `--color-accent` (Block 3) is a duplicate alias of
  `--accent` (Block 1). The alias exists because some
  inline styles reference `--color-accent` directly. The
  alias can be removed if all inline-style references are
  updated, OR kept as a forward-compatible alias.
- `--cell-warning-bg` and `--cell-error-bg` use `var(--warn-bg)`
  and `var(--blocked-bg)` respectively, which is good
  (single source of truth). They could be removed and the
  direct vars used instead.
- `--cell-pad-v/-h` and `--cell-h` are referenced only in
  the cell-related CSS. If a future Tailwind config
  replaces these, they can be removed.

### Component class groups

| Component | Prefix | Count | Notes |
|---|---|---|---|
| state banner | `.dirty-state-banner`, `.workspace-state-banner` | 11+ | UI-2.1 (state banner polish, 56F) |
| project switch | `.sidebar-section`, `.project-card` | ~20 | Sidebar / 56E (project switch simplification) |
| Help | `.pilot-help-onboarding` (`.pho-`) | 5+ | 56B (help section) |
| New Project | `.np-` (new project form) | 8+ | 56C (new project v1 form) |
| LineItemGrid | `.lig-` | 0 new (uses existing `.fc-*`) | 57A (LineItemGrid CAPEX pilot) |
| validation bar | `.validation-summary-bar` (`.vsb-`) | ~10 | UI-2.3 (55F) |
| runtime chip | `.runtime-impact-chip` (`.ric-`) | ~5 | UI-2.2 |

The LineItemGrid (57A) did **not** require any new CSS — it
uses the existing `.fc-grid`, `.fc-cell`, `.fc-cell--code`,
`.fc-cell--amount`, `.fc-total-row`, `.fc-subtotal-row`,
`.fc-section-band`, `.fc-grand-total`,
`.fc-hard-capex-total`, `.fc-delta-row`, `.fc-cell-input`,
`.fc-cell-runtime`, `.fc-input-native` classes that were
already in `styles.css` for the original hand-written table.

This is intentional: the 57A migration is a presentation
refactor only, and reusing the existing CSS classes keeps
the visual look byte-for-byte identical to the pre-57A
hand-written table.

## Recommended consolidation sequence

### Step 1 (low risk, auto-merge eligible): `:root` block merging

Combine the 3 `:root` blocks into a single `:root` block at
the top of the file. Move all custom properties to that
single block. Order them logically:
- Color tokens
- Typography tokens
- Spacing tokens
- Cell / runtime tokens

This is **low risk** because:
- No new tokens are introduced.
- No tokens are renamed.
- The visual look is unchanged.
- The order in which tokens are declared does not affect
  their use.

### Step 2 (medium risk, requires visual review): remove duplicate `--color-accent` alias

Either:
- Update all inline-style references to use `--accent` directly,
  and remove the alias; OR
- Keep the alias as a forward-compatible shim.

Recommended: keep the alias. The cost is one line of CSS;
the benefit is that any future code that references
`--color-accent` continues to work.

### Step 3 (medium risk, requires visual review): rename `fc-*` classes to `cell-*` or component-scoped names

The `fc-*` prefix was introduced in Phase 20I as an
abbreviation for "finco cell". It is now used widely
(`.fc-grid`, `.fc-cell`, `.fc-cell--code`, etc.). Renaming
to a more descriptive prefix (e.g. `.cell-grid`,
`.cell-code`, etc.) would be a visual-review-required
change because every template references the old class
names.

**Recommend DEFER until Tailwind.** If Tailwind is
introduced, the `fc-*` classes can be replaced with
utility classes, and the rename is moot.

### Step 4 (high risk, requires full visual review): Tailwind build config

**DEFER.** Tailwind is explicitly out of scope until after
UI-3 closeout. The 55C tailwind-0 feasibility study
documented this.

## What can be auto-merged

**Step 1 only** (`:root` block merging) is auto-merge
eligible. It is a docs / CSS refactor that:
- does not change any token value
- does not change any class name
- does not change any visual property

The user can review the diff and merge Step 1 without
visual review (the change is purely structural).

## What requires visual review

**Steps 2-4** all require visual review. They should NOT
auto-merge. They should be PRs that the user reviews
manually.

## Tailwind timing recommendation

- **Do NOT introduce Tailwind until after UI-3 closeout.**
  The UI-3 arc (57A done, 57F planned) is the right time
  to evaluate Tailwind. Until then, hand-written CSS
  remains.
- When Tailwind is introduced, do it as a single
  configuration change that adds Tailwind utilities
  alongside the existing custom CSS (not as a
  replacement). This is a build-config change, not a
  visual change.
- Replace `fc-*` classes with Tailwind utilities
  gradually, one component at a time, with visual
  review per component.

## Hard no-go / scope for 57E

- No financial model changes.
- No `app/waterfall_core.py` changes.
- No `app/project_factories.py` changes.
- No `app/persistence/` changes.
- No `app/services/` changes.
- No `main_web.py` changes.
- No `static/app.js` changes.
- **No `static/styles.css` changes** (this is the inventory,
  not the change).
- No schema / migration changes.
- No fixture CSV changes.
- No frontend dependency changes.
- No Tailwind / Alpine / React / Vue / Svelte.
- No G20/R99/R102 guard promotion.
- No generic Solar/Wind runtime work.
- No BESS / Hybrid / Portfolio work.
- No forbidden user-facing claims.
- rc1 frozen.

## Auto-merge policy

57E is `docs/report/test-only`. It is auto-merge eligible
if all hard gates pass. The CSS consolidation work
proposed in this document is **not** part of 57E; it is
deferred to a future PR that the user must approve.
