# Phase 57A-10G — CAPEX Advanced Column Groups

> Type: low-risk UI implementation, CAPEX UI only
> Status: DRAFT
> Base SHA: `8a0eb14` (post-57A-10F)
> Branch: `phase57a10g-capex-advanced-column-groups`
> Scope: **visual / semantic only** column groups for the CAPEX detail grid and the CAPEX single sheet
> Hard constraint: **no runtime / model / formula / tax / depreciation / IDC / debt / persistence changes**

## 1. Context

Phase 57A-10F (merged in PR #540) added:

- CAPEX status legend
- Metadata-only disclaimer
- Status chips for Runtime-used / Metadata-only / Design-only / Export-only
- CAPEX export/audit metadata scope wording

The CAPEX detail grid (`app/templates/partials/sheet_capex_detail.html`)
and the CAPEX single sheet (`app/templates/partials/sheet_capex.html`)
now carry more visible status information, but the **columns themselves
are not yet grouped into business sections**. A reader sees ~29 columns
in the detail grid (5 + 2 + 2 + 1 + 18 + 1) and has to mentally
re-categorise each one as "is this a runtime field, a costing
metadata field, a tax metadata field, a schedule field, or a
notes field?".

## 2. Goal

Improve CAPEX sheet readability by grouping advanced CAPEX columns
into clear business sections. This should make the CAPEX surface
easier to read **without changing any calculations**.

The 4 column groups are:

1. **Core** — Code, Name, Amount, Runtime-used fields
2. **Costing** — Contingency, Cost per MW / derived cost indicators
3. **Tax** — VAT %, WHT %, VAT applicability, WHT rate, tax metadata
4. **Schedule** — payment schedule, construction utilisation,
   spending profile, schedule metadata

Status chips from 57A-10F must remain visible. Metadata-only fields
must still say they do not affect Run. Design-only fields must not
look runtime-active.

## 3. Allowed / Not allowed

### Allowed

- CAPEX templates (`sheet_capex.html`, `sheet_capex_detail.html`)
- CSS only if needed and narrowly scoped (inline `<style>` block in
  each template; no external CSS additions)
- render/context/safety tests in `tests/`
- `docs/phase57a10g_*.md` design document
- `reports/phase57a10g_*.json` machine-readable report

### Not allowed

- no backend calculation changes
- no CAPEX model changes
- no persistence / schema changes
- no tax / depreciation / IDC / debt changes
- no JavaScript framework
- no Tailwind / Alpine
- no Generic project status changes
- no `main_web.py` / `main_api.py` changes
- no `static/` changes (no JS / CSS file additions)
- no `domain/` changes

## 4. Column group mapping (CAPEX detail grid)

The CAPEX detail grid in `sheet_capex_detail.html` has 29 columns
(data-col 1–29). They are grouped as follows:

| Group    | data-col | Colspan | Columns                                                                |
|----------|----------|---------|------------------------------------------------------------------------|
| Core     | 1–5      | 5       | Line Item, Code, Excel kEUR, App kEUR, Delta kEUR                      |
| Costing  | 6, 9     | 2       | Cont. %, Per MW                                                        |
| Tax      | 7, 8     | 2       | VAT %, WHT %                                                           |
| Status   | 10       | 1       | Status                                                                |
| Schedule | 11–28    | 18      | M1, M2, M3, M4, M5, M6, M7, M8, M9, M10, M11, M12, M13, M14, M15, M16, M17, M18 |
| Notes    | 29       | 1       | Notes                                                                 |

Total: 5 + 2 + 2 + 1 + 18 + 1 = **29 columns** ✅

**Note on "Status" and "Notes" columns**: these are flanking columns
(Status at col 10 sits between the costing/tax group and the
schedule group; Notes at col 29 sits after the schedule group).
The brief specifies 4 groups (Core, Costing, Tax, Schedule), so
Status and Notes are tagged with `data-capex-group="meta"` (a
sub-group of "metadata" / "non-financial-control" columns). They
remain visually distinct and are not hidden or merged into any
of the 4 main groups.

## 5. Visual / semantic implementation

### 5.1 `sheet_capex_detail.html`

A new `<tr class="fc-grid-header fc-grid-header--groups">` row is
inserted at the **top of `<thead>`**, **above** the existing
`fc-grid-header` row. The new row has 6 `<th>` cells with:

- `class="fc-th fc-capex-group-header"`
- `data-capex-group="<group>"` (one of: core, costing, tax, meta, schedule)
- `colspan` matching the column range
- `scope="colgroup"`

Inline `<style>` block adds narrowly scoped CSS keyed off
`.fc-capex-group-header[data-capex-group="..."]` with 5 colour-coded
backgrounds (Core = blue, Costing = purple, Tax = orange,
Meta = green, Schedule = yellow). No Tailwind, no Alpine.

The existing 2 rows in `<thead>` are unchanged. The status chips
on Cont. %, VAT %, WHT % column headers (Phase 57A-10F) remain
visible. The metadata-only chip text is preserved.

### 5.2 `sheet_capex.html`

A new `<div class="capex-column-groups" data-capex-column-groups="true">`
panel is inserted **above** the workbook grid
(`<div class="fc-grid-wrapper fc-capex-grid-wrapper">`). The panel
contains a 4-item `<ul>` with `<li data-capex-group="...">` cells,
each carrying a status chip (Runtime-used or Metadata-only) and a
short description. This is a **semantic guide** mirroring the column
groups shown in the detail grid.

Inline `<style>` block adds narrowly scoped CSS for
`.capex-column-groups` and its 4 group colour hints (matching the
detail grid palette). No Tailwind, no Alpine.

## 6. Diff summary (this PR)

| Status | File | Lines | Change |
|--------|------|-------|--------|
| M | `app/templates/partials/sheet_capex.html` | ~+60 / -0 | New column-groups panel + inline `<style>` block |
| M | `app/templates/partials/sheet_capex_detail.html` | ~+50 / -0 | New `<tr>` for column group headers + CSS in existing `<style>` block |
| A | `tests/test_phase57a10g_capex_advanced_column_groups.py` | +N | Render / context / safety tests |
| A | `docs/phase57a10g_capex_advanced_column_groups.md` | +N | This design document |
| A | `reports/phase57a10g_capex_advanced_column_groups.json` | +N | Machine-readable report |

## 7. Test plan

- All 57A-10F tests still pass (status legend, disclaimer, status chips)
- New 57A-10G tests:
  - 6 `<th class="fc-capex-group-header">` cells present in
    `sheet_capex_detail.html` `<thead>` row 0
  - colspans sum to 29 (5 + 2 + 2 + 1 + 18 + 1)
  - data-capex-group attribute present on each group header
  - 5 distinct group names: core, costing, tax, meta, schedule
  - `data-capex-column-groups="true"` block present in
    `sheet_capex.html`
  - 4 `<li data-capex-group="...">` entries present in the
    column-groups panel
  - All 4 status chips from 57A-10F still visible
  - Metadata-only disclaimer still visible
  - No UndefinedError / NameError / AttributeError (template
    syntax check)
  - Forbidden paths verified empty (no domain / persistence /
    main_web / main_api / static / tax / depreciation / debt changes)
  - rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` reachable
  - No CAPEX total change (no `_CAPEX_ITEM_FIELDS` tuple change,
    no `CapexItem` dataclass field change)
- TUHO parity: 68/68 unchanged
- Oborovo parity: 68/68 unchanged
- `import main_web`: OK
- `import app.excel_export`: OK

## 8. Guardrail confirmations

- low-risk UI implementation, CAPEX UI only
- no runtime materialization changes
- no model / formula changes
- no tax calculation changes
- no depreciation calculation changes
- no IDC calculation changes
- no debt changes
- no persistence / schema changes
- no new CAPEX logic
- no Generic project status promotion
- no Tailwind / Alpine / frontend framework
- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` untouched
- TUHO / Oborovo unchanged at Level 2 (Reference)
- Generic Wind / Solar unchanged at Level 1 (Exploratory / Unvalidated)
- branch: `phase57a10g-capex-advanced-column-groups`
- PR: DRAFT only, do not mark ready, do not merge

## 9. Stop after report

This is a single low-risk UI PR. No further phases implied. Next
phase candidate (if any) is a future 57A-10H that may add read-only
**rendering** of the metadata-only fields in the per-line rows of
the detail grid (still visual / semantic only).
