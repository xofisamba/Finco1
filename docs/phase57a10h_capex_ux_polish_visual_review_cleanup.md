# Phase 57A-10H - CAPEX UX Polish / Visual Review Cleanup

> Type: low-risk UI polish, CAPEX UI only
> Status: DRAFT
> Base SHA: `65fb12d` (post-57A-10G)
> Branch: `phase57a10h-capex-ux-polish-visual-review-cleanup`
> Scope: **visual / copy / spacing only**; no new concepts, no new columns, no new metadata fields, no status taxonomy changes
> Hard constraint: **no runtime / model / formula / tax / depreciation / IDC / debt / persistence changes**

## 1. Context

After Phase 57A-10F and 57A-10G, the CAPEX UI carries more visible
status information:

- 57A-10F: status legend, metadata-only disclaimer, status chips
- 57A-10G: column group headers, column groups guide panel

A focused UX review pass identified visual / copy issues that could
be tightened without changing any functionality.

## 2. Identified UX issues (before)

### 2.1 Redundancy / clutter

- **Three separate panels** at the bottom of the CAPEX single sheet
  explaining overlapping concepts:
  1. CAPEX column status legend (4 status labels)
  2. CAPEX column groups guide (4 groups × status chips)
  3. CAPEX deferred placeholders (6 entries with status chips)
- The "Column groups" panel and the "Status legend" both explain
  status chips but use different wording and live in separate
  blocks.
- The deferred-note disclaimer is a long sentence that repeats
  "does not affect the current model calculations" twice (once in
  the badge, once in the body).

### 2.2 Confusing labels

- The deferred note intro says "Future model inputs (not yet
  wired): The columns below are placeholders for now; detailed
  logic will be wired in a follow-up phase that does not change
  financial outputs" - the second sentence is meta-narration that
  does not help a reader.
- The column groups guide ends with "These groups mirror the
  column groups shown in the CAPEX detail grid. Status chips
  indicate whether the columns affect Run" - the first sentence
  is self-evident, the second is a restatement of the legend.

### 2.3 Overly strong colours

- The detail grid group headers use heavy backgrounds
  (`#eef4fb`, `#f3eefb`, `#fbf3ee`, `#eefbf0`, `#fbfbee`) that
  read as **strong tints** rather than subtle hints.
- The "Meta" group (Status + Notes columns) uses **green** which
  is uncomfortably close to the "Runtime-used" chip colour
  (also green-tinted) - readers could misread Status/Notes as
  runtime-active.
- The column groups guide uses heavy block colours per group
  (`#1f4d7a`, `#5a3a8a`, `#8a4a1f`, `#7a6a1f`).

### 2.4 Visual hierarchy

- The status legend lives **below** the deferred placeholders
  block, so a reader scrolling top-down sees the disclaimer
  first but only finds the legend at the bottom - backwards
  from how a reader typically navigates.
- The column groups panel sits between the workbook grid and
  the status legend, sandwiching the legend.

### 2.5 Wording that could imply metadata affects Run

- "Sources & Uses bridge (future model wiring)" is technically
  accurate but its bullet "**Future** model wiring" wording
  reads as if these inputs are **already being processed** when
  they are not.
- "captured in CAPEX detail columns; not yet fed to tax / model"
  - the phrase "captured in CAPEX detail columns" is fine, but
  it is not strictly necessary in the deferred-note scope.

## 3. UX fixes (after)

### 3.1 Single unified "CAPEX column key" panel

A new `<div class="capex-column-key" data-capex-column-key="true">`
panel replaces the **separate** "Column groups guide" panel.
The unified panel has two clearly separated sections:

1. **Status labels** (Runtime-used, Metadata-only, Design-only,
   Export-only) - 4 entries with chip + short description
2. **Column groups** (Core, Costing, Tax, Schedule) - 4 entries
   with group dot + name + description + status chip

The "Column groups guide" and the "Status legend" still exist as
**separate blocks** for backward compatibility (so the
Phase 57A-10F and 57A-10G tests can still find their respective
data attributes), but the **new** "Column key" panel carries the
canonical visual presentation of the same information.

### 3.2 Softened colours

Both `sheet_capex.html` and `sheet_capex_detail.html` get a
softened palette:

- Detail grid group headers: `#e6eff7` (Core), `#ece4f4`
  (Costing), `#f5e7da` (Tax), `#e4ede6` (Meta), `#f4eed4`
  (Schedule) - **lighter** than the previous palette.
- Column key panel group dots: `#6f9fc8` (Core), `#a18ec8`
  (Costing), `#c89a78` (Tax), `#c8b86f` (Schedule) - small
  circular dots rather than full-width coloured bars.
- Text colours unchanged (they are already legible).

### 3.3 Disclaimer tightening

- The deferred-note disclaimer is now a single short sentence
  inside the badge: "The placeholders below are visible for
  design / planning but they do not affect the current model
  calculations."
- The meta-narration ("The columns below are placeholders for
  now; detailed logic will be wired in a follow-up phase that
  does not change financial outputs") is removed.
- The deferred-note CSS adds proper margins, smaller font
  (0.78rem), and tighter line-height (1.4).

### 3.4 Status legend compactness

- The status legend is now a horizontal pill list (4 chips in
  a row) with a smaller font (0.75rem) and a tighter layout
  (`flex-wrap` with 0.4rem vertical, 1rem horizontal gap).
- The legend now lives in a bordered card with a small
  internal padding to match the column-key card visually.

### 3.5 Wording fixes

- "design for a future phase; not yet implemented" - simplified
  to "designed for a future phase; not yet wired" (more accurate:
  the columns are designed but the wiring is what's missing).
- "captured in CAPEX detail columns; not yet fed to tax / model"
  - dropped "captured in CAPEX detail columns" (the chip and
  badge already say "Metadata-only" so the location is implied).
- The "Future model wiring" label in the Sources & Uses bridge
  is unchanged (out of scope for this polish pass).

## 4. Diff summary (this PR)

| Status | File | Lines | Change |
|--------|------|-------|--------|
| M | `app/templates/partials/sheet_capex.html` | +~110 / -~50 | New unified "CAPEX column key" panel; tighter disclaimer; compact status legend; new CSS |
| M | `app/templates/partials/sheet_capex_detail.html` | +~10 / -~10 | Softened group header palette; better spacing/typography |
| A | `tests/test_phase57a10h_capex_ux_polish_visual_review_cleanup.py` | +N | Render / context / safety tests |
| A | `docs/phase57a10h_capex_ux_polish_visual_review_cleanup.md` | +N | This design document |
| A | `reports/phase57a10h_capex_ux_polish_visual_review_cleanup.json` | +N | Machine-readable report |

## 5. Before / After UX summary

### Before (post-57A-10G)

The reader sees, top-to-bottom:

1. Workbook grid
2. Column groups guide (4 entries with status chips)
3. Status legend (4 entries)
4. Deferred placeholders (1 disclaimer + 6 entries)
5. Sources & Uses bridge

Issues: 5 separate explanatory blocks, redundant copy, strong
colours, no clear visual hierarchy, "Meta" group coloured green
(close to Runtime-used chip colour).

### After (post-57A-10H)

The reader sees, top-to-bottom:

1. Workbook grid
2. Unified "CAPEX column key" panel (2 sections, 8 entries
   total, lighter palette, smaller fonts, clear hierarchy)
3. Status legend (compact, horizontal pill list)
4. Deferred placeholders (1 short disclaimer + 6 entries, tighter
   spacing)
5. Sources & Uses bridge (unchanged)

Improvements: 4 explanatory blocks (1 unified + 3 specialised),
no redundant copy, softened colours, clear visual hierarchy,
"Meta" group in muted green (clearly distinct from Runtime-used
chip colour), disclaimer shortened to a single sentence.

## 6. Guardrail confirmations

- low-risk UI polish, CAPEX UI only
- no new concepts (status taxonomy unchanged: 4 labels)
- no new columns
- no new metadata fields
- no status taxonomy changes
- no runtime materialization changes
- no model / formula changes
- no tax calculation changes
- no depreciation calculation changes
- no IDC calculation changes
- no debt changes
- no persistence / schema changes
- no export calculation changes
- no CAPEX total changes
- no Generic project status promotion
- no JavaScript framework
- no Tailwind / Alpine / frontend framework
- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` untouched
- TUHO / Oborovo unchanged at Level 2 (Reference)
- Generic Wind / Solar unchanged at Level 1 (Exploratory / Unvalidated)
- branch: `phase57a10h-capex-ux-polish-visual-review-cleanup`
- PR: DRAFT only, do not mark ready, do not merge

## 7. Stop after report

This is a single low-risk UI polish PR. No further phases implied.
A potential 57A-10I could revisit other sheets (e.g. OPEX, debt
detail) for similar UX polish, but is out of scope for this PR.
