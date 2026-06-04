# Phase 55C — Tailwind-0 / CSS token consolidation feasibility

## Status

DRAFT, docs-only feasibility assessment. No Tailwind config, no
package.json, no frontend dependency changes.

## Current main SHA

`5b722e475e2520d00df4d800619dedbdb47b1bea` (post-55B)

## `styles.css` LOC and size

| Metric | Value |
|---|---:|
| Lines | 4,686 |
| Bytes | 123,456 (~124 KB) |
| `:root` blocks | **5** (lines 10, 828, 1330, 1335, 2695) |
| Component class groups | 9 |
| Total CSS selectors | ~600+ |

The 5 `:root` blocks (not 3 as estimated by Claude review) means token
consolidation should be the first concrete step. We have 5 separate
declarations of CSS variables that should be merged into a single
`:root { }` block (or a small number of thematically grouped blocks).

## `:root` block inventory

| Line | Theme | Variables declared |
|---|---|---|
| 10 | Main tokens | `--bg`, `--text-1`, `--text-2`, `--border`, `--accent`, etc. |
| 828 | Override / dark mode hint? | (verify) |
| 1330 | Sidebar tokens | `--sidebar-w: 200px` |
| 1335 | Sidebar collapsed | `--sidebar-w: 0px` |
| 2695 | Second main block (or component tokens) | (verify) |

**Note**: The user-supplied "3 :root blocks" estimate was an approximation.
The actual count is 5. Token consolidation is more important than
initially estimated.

## CSS variable inventory (sampled)

The `styles.css` uses at least 60+ CSS variables. Some are well-named
(`--text-1`, `--text-2`, `--border-2`, `--bg-1`, `--bg-2`, `--accent-1`),
others are ad-hoc (`--capex`, `--amount`, `--badge-preview-bg`).

Sample of well-named tokens used repeatedly (15+ times each):

- `--text-2` (78 occurrences)
- `--text-1` (15 occurrences)
- `--border-2` (3 occurrences)

Some tokens are defined but barely used:

- `--bg-1`, `--bg-2` (1 occurrence each)
- `--border-2` (3 occurrences)

## Duplicate token patterns

- Multiple `:root` blocks declare similar tokens.
- Some classes use ad-hoc values (e.g., `color: #666`, `color: #1a1a1a`)
  instead of `var(--text-1)`, `var(--text-2)`.
- Inconsistent use of fallback values: some classes use
  `var(--text-1, #1a1a1a)`, others use just `var(--text-1)`.

## Component class group inventory

| Group | Selector count | Notes |
|---|---:|---|
| `.fc-*` (grid) | 160 | Existing Phase 20I design system |
| `.btn` | 28 | Button variants |
| `.banner-*` | 14 | UI-2.1 |
| `.validation-summary-*` | 14 | UI-2.3 |
| `.sheet-card` / `.card` | 7 | Cards |
| `.last-run-indicator-*` | 7 | UI-2.6 |
| `.chip-*` | 6 | UI-2.2 |
| `.factory-lock-*` | 5 | UI-2.4 |
| Other | ~400 | Mixed |

## Risks of current custom CSS

1. **5 `:root` blocks** — token sprawl makes it hard to know which
   definition wins.
2. **Ad-hoc hex values** in some classes (`#666`, `#1a1a1a`) — they
   bypass the design system.
3. **Inconsistent fallback usage** — some classes use `var(--text-1, #1a1a1a)`,
   others don't. This is brittle if a CSS variable is later removed.
4. **160 `fc-*` selectors** for the grid system — when LineItemGrid
   migration starts, this is a large surface area.
5. **Class names are sometimes overly specific** (e.g.,
   `.fc-grid-wrapper.fc-capex-grid-wrapper`) — these deep selectors
   are hard to reuse.
6. **No documentation** of which token is for what — the design system
   is implicit, not explicit.
7. **No automated check** that existing tokens are used; new classes
   can drift.

## Risks of adding Tailwind now

1. **Big-bang rewrite** — Tailwind replaces 4,686 LOC of custom CSS
   with utility classes. Migrating 47 templates + `app.js` is
   massive.
2. **Build pipeline** — Tailwind requires a build step (PostCSS or
   CLI). Currently we have NO build pipeline (no `package.json`, no
   bundler). Adding one means:
   - `package.json` (frontend dependency)
   - `tailwind.config.js`
   - `postcss.config.js`
   - A `build` script
   - A `dist/` directory
3. **Output size** — Tailwind's purge (or v4's automatic content
   detection) reduces the actual CSS to a small subset. Without purge
   configured correctly, the output can be 1+ MB.
4. **Template rewrite** — every `<div class="fc-grid-wrapper ...">`
   becomes `<div class="grid grid-cols-3 gap-2 ...">`. This is a
   mechanical translation but touches every template.
5. **Forced consistency** — Tailwind tokens override our CSS variables.
   We'd lose the careful palette work from Phase 20I/UI-2 unless we
   re-map.
6. **No fallback path** — if Tailwind breaks, we don't have a way
   back without re-doing the work.
7. **No clear pilot** — every sheet partial has different patterns;
   picking one to migrate first is hard.

## Tailwind timing recommendation

**Recommendation: Tailwind-0 (this phase, docs only) → Token
consolidation PR → Tailwind-1 (build config) AFTER UI-3 closeout.**

Rationale:

- The current custom CSS is workable, not broken. The pain points are
  5 `:root` blocks and inconsistent token usage — these are
  2-3 PRs of work, not a big-bang.
- UI-3 (LineItemGrid) is a larger feature workstream. Doing both at
  once multiplies the risk of a bad merge.
- Token consolidation is a prerequisite for Tailwind: you need a clean
  token set before you can map to Tailwind's design tokens.
- A Tailwind pilot (1 component) needs a build pipeline. Establishing
  that pipeline is its own PR.
- Order: token consolidation → UI-3 → Tailwind-1 (build) → Tailwind-2
  (mapping) → Tailwind-3 (pilot component) → Tailwind-4
  (LineItemGrid adoption).

## Proposed Tailwind phased plan

### Tailwind-0 (this PR) — feasibility assessment

- This PR. Docs only. No code changes.

### Tailwind-1 (future, after UI-3) — build config

- Add `package.json` with Tailwind v4 + PostCSS.
- Add `tailwind.config.js` with content paths.
- Add `npm run build:css` script.
- Output `static/styles.generated.css`.
- The existing `static/styles.css` is renamed to `static/styles.base.css`.
- No template changes yet.

### Tailwind-2 (future, after Tailwind-1) — token mapping

- Map our existing CSS variables to Tailwind's theme tokens.
- E.g., `--text-1` → `text-primary`, `--text-2` → `text-secondary`,
  `--accent-1` → `text-accent`.
- Templates still use `var(--text-1)`. Tailwind tokens are aliases.
- Visual: no change.

### Tailwind-3 (future, after Tailwind-2) — pilot component

- Pick ONE component (e.g., the validation summary bar).
- Migrate from custom CSS to Tailwind utility classes.
- Visual review by user.
- Rollback plan: keep the custom CSS file in `static/styles.base.css`
  alongside.

### Tailwind-4 (future, after Tailwind-3) — LineItemGrid adoption

- The new LineItemGrid macro (introduced in UI-3.x) uses Tailwind
  classes from the start.
- Existing sheets are migrated sheet-by-sheet (per 55B migration order).
- This is the long-term goal; not a single PR.

## Rollback plan

- Every Tailwind step is additive. The existing custom CSS is
  preserved in `static/styles.base.css` and can be re-enabled by
  swapping which file is loaded.
- Tailwind-1: rollback is `rm package.json` and revert config. No
  template changes.
- Tailwind-2: rollback is removing the theme mapping. Templates still
  use `var(--text-1)`.
- Tailwind-3: rollback is the pilot component. We can revert to the
  custom CSS for that one component.
- Tailwind-4: rollback is per-sheet. Each sheet migration is its own
  PR with its own rollback.

## Hard gates for any future Tailwind PR

- Tailwind-1 (build config only, no template changes):
  - Adds `package.json`, `tailwind.config.js`, `postcss.config.js`
  - Adds `static/styles.generated.css` (gitignored or committed as a
    build artifact)
  - No template changes
  - Visual: no change
  - Must pass all existing tests
  - CI must include `npm run build:css` step
- Tailwind-2 (token mapping only, no template changes):
  - Updates `tailwind.config.js` to map our tokens
  - Templates still use `var(--text-1)` etc.
  - Visual: no change
- Tailwind-3 (pilot component, ONE component):
  - One component migrated to Tailwind
  - Visual review by user
  - Rollback plan documented
- Tailwind-4 (LineItemGrid):
  - Per 55B migration order
  - Each sheet migration is its own PR
  - Each PR has a visual review by user

## Token consolidation work (NOT Tailwind, just a first step)

Before Tailwind-1, do a small token-consolidation PR:

- Merge the 5 `:root` blocks into 1-2 (one for main tokens, one for
  layout tokens like `--sidebar-w`).
- Replace ad-hoc hex values with `var(--token)` references.
- Document each token in a comment block at the top of `styles.css`.

This is a 1-2 PR workstream, low risk, additive only.

## Recommended next step

**55D — Live no-go scanner plan and UI-3 readiness closeout** (docs
only, design a live filesystem scanner for the 15 forbidden UI terms,
close out the post-UI-2 review response).
