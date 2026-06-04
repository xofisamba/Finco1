# Phase 55D — Live no-go scanner plan and UI-3 readiness closeout

## Status

DRAFT, docs-only closeout for the post-UI-2 review response.

## Current main SHA

`cf3c51a7b74752037809da7c3eb17824c41fd803` (post-55C, post-55B, post-55A)

## Summary of 55A-55C

| Phase | Title | Status | Merge SHA |
|---|---|---|---|
| 55A | Agent B post-UI-2 governance refresh | MERGED (#469) | `1b97a2b747331c10a848369cef1e3738ecea438d` |
| 55B | UI-3.1 LineItemGrid characterization | MERGED (#470) | `5b722e475e2520d00df4d800619dedbdb47b1bea` |
| 55C | Tailwind-0 / CSS token feasibility | MERGED (#471) | `cf3c51a7b74752037809da7c3eb17824c41fd803` |
| 55D | UI-3 readiness and no-go scanner plan | This PR (DRAFT) | (pending) |

## Final recommendations

### Agent B status

**Status: REFRESHED.** 55A documented stale references and provided a
refreshed summary. No actual edit to existing Agent B docs (out of
scope for 55A). Next mandatory refresh point: after UI-3.1 (LineItemGrid)
merge.

### UI-3 first runtime phase

**Recommendation: UI-3.1 = `sheet_capex.html` (CAPEX summary) pilot.**

Rationale (from 55B):

- Smallest sheet (235 LOC) with the full `fc-grid` design system.
- Single period column (Year 1 kEUR) — no multi-period complexity.
- Has section bands, subtotals, input vs runtime cells.
- Has read-only notice for baselines.
- Already tested daily by users.

Migration order (from 55B):

1. `sheet_capex.html` (CAPEX summary) — first pilot
2. `sheet_opex.html` (OPEX summary) — second, similar structure
3. `sheet_revenue.html` (Revenue) — third, non-numeric cell variant
4. `sheet_capex_detail.html` (CAPEX detail) — fourth, multi-period + sticky
5. `sheet_opex_detail.html` (OPEX detail) — fifth, multi-period + sticky
6. Other sheets (construction, IDC, senior_debt, shl, tax, financials) — bulk last

### Tailwind timing

**Recommendation: After UI-3 closeout. NOT now.**

From 55C:

- styles.css is 4,686 LOC, 124 KB, 5 `:root` blocks.
- 5-step Tailwind plan: Tailwind-0 (this) -> 1 (build) -> 2 (token
  mapping) -> 3 (pilot) -> 4 (LineItemGrid).
- **Pre-Tailwind: 1-2 PRs of token consolidation** (merge `:root`
  blocks, replace ad-hoc hex, document tokens).

### No-go scanner implementation

**Recommendation: Defer implementation, but design the live scanner
in this PR so it can be implemented as a follow-up Phase 55E or as
part of UI-3 prep.**

See "Live no-go scanner design" below.

### Visual review requirement

**All UI-3 runtime PRs require 100% visual review by user before
merge.** This is the same policy that worked for UI-2.

## Live no-go scanner design

### Target files

The scanner should target:

- `app/templates/**/*.html` — all Jinja templates
- `static/app.js` — vanilla JS
- `static/styles.css` — only for `<content>` properties (rare)

The scanner should NOT target:

- `docs/**/*.md` — docs can mention forbidden terms in lists of
  what NOT to do
- `reports/**/*.json` — reports can mention forbidden terms in
  inventories of no-go claims
- `tests/test_*.py` — tests can mention forbidden terms in test
  fixtures
- `app/persistence/records.py` — the "NOT_APPROVED" / "BLOCKED"
  governance state values are legitimate enum-like strings

### Forbidden positive claims (15 terms from 54H)

The scanner should flag these as positive/factual UI claims:

- bankable, bank-grade
- lender-ready
- certified
- audit-ready
- validated (in copy, not in code identifiers like "is_validated")
- investor-ready
- SaaS-ready
- production-ready
- external validation
- customer reference
- investment advice
- guaranteed returns

### Allowed contexts (false-positive policy)

The scanner should NOT flag:

- "is_validated" / "is_approved" — Python identifiers
- "validation_summary" / "validation_bar" — variable/class names
- "validated" in comments
- "validated" in a string like "validated against backend" (descriptive)
- "validated" in `data-` attributes like `data-validated="true"`
- "validation" by itself (not a no-go term)
- "validate" verb (legitimate action)
- "no-go" / "no-go claims" (self-referential)
- Lists of forbidden terms in docs (docs/external_review/no_go_claims.md)
- Test files that include the term as a fixture

### False positive policy

- Each finding must include: file path, line number, the match, and
  the surrounding 80 characters of context.
- The scanner should NOT auto-fix anything.
- A finding is a *signal* for human review, not a hard error.
- A finding can be:
  - **Dismissed** — false positive, document why.
  - **Fixed** — replace with a safe term.
  - **Documented exception** — a single line comment in the file
    explaining the legitimate use, e.g.,
    `{# no-go: 'validated' is a code identifier, not UI copy #}`.

### Whether CSS comments should be scanned

- **No.** CSS comments are developer notes. A scanner for UI copy
  should not flag CSS comments.
- The only CSS scan is for `content: "..."` properties that are
  rendered to the user (rare; mostly used for icons and tooltips).

### Whether docs no-go lists should be exempted

- **Yes, by file path pattern.** Anything under `docs/` and
  `reports/` is exempted by default. The scanner should have an
  `--include-docs` flag for an explicit opt-in.
- Test files are exempted by default. The scanner should have an
  `--include-tests` flag for an explicit opt-in.

### Implementation approach (deferred)

When implemented, the scanner should be a Python script:

- `tools/no_go_scanner.py` (or similar)
- Walks `app/templates/`, scans for the 15 forbidden terms.
- Emits JSON or human-readable output.
- Has a `--strict` mode that fails CI on any finding.
- Has a `--report` mode that produces a markdown report without
  failing.
- Has a `--baseline` file for known false positives.

Recommended phasing:

- 55E (deferred) — implement the scanner, `--report` mode only.
- 55F (deferred) — add `--strict` mode, run in CI.
- 55G (deferred) — populate `--baseline` with current false positives.

## Context-wiring backlog

Three context keys from UI-2 are currently dormant in `index.html`:

| Context key | Used by | Current state | Workaround in UI-2 |
|---|---|---|---|
| `banner_context` | `_state_banner.html` | NOT set anywhere | Renders nothing |
| `validation_summary` | `_validation_summary_bar.html` | NOT in index.html context | Fallback to info bar (audit_reconciliation_tab only) |
| `runtime_summary` | `_last_run_indicator.html` | NOT in index.html context | Renders nothing |

### Wiring options (each is its own PR, each is a UI-2.x follow-up):

#### Option 1: Wire `runtime_summary` to index.html (lowest risk)

- Add `"runtime_summary": runtime_summary_to_dict(...)` to the
  index.html render context in `main_web.py`.
- This activates the run-source indicator.
- Backend changes are minor; mostly plumbing.
- Pilot impact: low.

#### Option 2: Wire `validation_summary` to index.html

- Add `"validation_summary": validation_summary_for_workspace(...)` to
  the index.html render context in `main_web.py`.
- This activates the validation summary bar on the dashboard.
- Backend: minor; needs a `validation_summary_for_workspace` helper.
- Pilot impact: low.

#### Option 3: Wire `banner_context` to index.html

- Add `"banner_context": banner_context_for_workspace(...)` to the
  index.html render context in `main_web.py`.
- This activates the state clarity banner.
- Backend: moderate; needs a `banner_context_for_workspace` helper
  that detects 11 banner contexts.
- Pilot impact: medium.

**Recommendation: Option 1 first, then 2, then 3.** Each is its own
PR with its own visual review.

## First UI-3 implementation prompt preview

```
# UI-3.1 — LineItemGrid pilot (CAPEX summary)

Branch: phase-ui3-1-line-item-grid-pilot-capex
Base: main@<post-55D>

Type: runtime template refactor (no backend changes)
Draft: YES (no auto-merge)
Visual review: REQUIRED before merge

## Objective

Introduce a shared `app/templates/partials/_line_item_grid.html` macro
that wraps the existing `fc-grid` design system, and use it in
`sheet_capex.html` (CAPEX summary) as the first pilot.

## Allowed files

- app/templates/partials/_line_item_grid.html (NEW)
- app/templates/partials/sheet_capex.html (refactor to use new macro)
- static/styles.css (additive only, no class removals)
- tests/test_ui3_1_line_item_grid_pilot_capex.py
- docs/ui3_1_line_item_grid_pilot_capex.md
- reports/ui3_1_line_item_grid_pilot_capex.json

## Hard gates

- Snapshot test: rendered HTML of sheet_capex.html before/after is
  byte-equivalent for the same input.
- All 754 relevant tests still pass.
- No new no-go UI claims.
- rc1 untouched.
- Visual review by user before merge.

## Migration order

This is step 1 of 6 (per 55B). Each step is its own PR.
```

## First Tailwind implementation prompt preview (if/when approved)

```
# Tailwind-1 — Build config only

Branch: phase-tailwind-1-build-config
Base: main@<after UI-3 closeout>

Type: build infra only (no template changes, no visual change)
Draft: YES (no auto-merge)

## Objective

Establish a Tailwind v4 + PostCSS build pipeline.
No template changes. No visual change.

## Allowed files

- package.json (NEW)
- tailwind.config.js (NEW)
- postcss.config.js (NEW)
- .gitignore (add dist/, node_modules/)
- static/styles.generated.css (NEW, build artifact)
- tests/test_tailwind_1_build_config.py
- docs/tailwind_1_build_config.md
- reports/tailwind_1_build_config.json

## Hard gates

- `npm run build:css` produces a valid `static/styles.generated.css`.
- The generated file is loaded only if `?tailwind=1` query param is
  set (so we can A/B test).
- No template changes.
- All existing tests pass.
- rc1 untouched.
- Visual review: no change expected.
```

## Agent B next prompt preview (deferred)

```
# Agent B refresh after UI-3.1 (CAPEX summary pilot)

Branch: phase-agent-b-post-ui3-1-refresh
Base: main@<post UI-3.1 merge>

Type: docs-only

## Objective

Refresh Agent B governance docs to reflect the new
`LineItemGrid` macro and the first migration (CAPEX summary).

## Allowed files

- docs/agent_b_*.md (refresh, not rewrite)
- reports/agent_b_*.json (refresh)
- tests/test_agent_b_post_ui3_1.py

## Hard gates

- No production code changed
- No templates changed
- No static CSS/JS changed
- All existing tests pass
- rc1 untouched
```

## Hard gates verified (this PR)

- ✓ Only docs/report added
- ✓ No production code changed
- ✓ No templates changed
- ✓ No static CSS/JS changed
- ✓ No frontend dependency changes
- ✓ No app/services, app/persistence changes
- ✓ No main_web.py changes
- ✓ No model/parity-core/schema/formula/fixture changes
- ✓ No no-go UI claims introduced
- ✓ rc1 SHA `b425a07` untouched
- ✓ PR is docs/report/test-only

## Recommended next step

After this PR merges, the post-UI-2 review response is CLOSED.

**Future work (out of scope now):**

1. **UI-3.1 = `sheet_capex.html` pilot** — first runtime work after
   this closeout.
2. **Token consolidation PR** (1-2 PRs of `:root` block merging and
   ad-hoc hex replacement) before Tailwind.
3. **Live no-go scanner** (Phase 55E, deferred) — implement the
   scanner design above.
4. **Context-wiring backlog** — Option 1 (runtime_summary) first,
   then Option 2 (validation_summary), then Option 3 (banner_context).
5. **Agent B refresh** after UI-3.1 merge.

None of these is started yet. Stop after this PR.
