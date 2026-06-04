# UI-2.2 — Runtime Impact Chip Partial

## Context

UI-2.2 is the second runtime UI implementation, stacked on top of
UI-2.1. It adds a reusable Runtime Impact chip partial and wires
it into `sheet_capex_detail.html` (replacing the inline chip with
a Jinja include, KEEPING the old `_rt_tooltip` macro for backward
compatibility).

**This is a DRAFT PR. NO auto-merge. User visual review required.**

## Branch

`phase-ui2-2-runtime-impact-chip`
**Base:** UI-2.1 branch head (`bc23496237416c0b66c33b67d28ff5585f8e7caa`)

## Files Changed

### New files
- `app/templates/partials/_runtime_impact_chip.html` (NEW, 38 lines)
- `tests/test_ui2_2_runtime_impact_chip_partial.py` (NEW, 49 tests)
- `docs/ui2_2_runtime_impact_chip_partial.md` (this file)
- `reports/ui2_2_runtime_impact_chip_partial.json`

### Modified files (additive only)
- `app/templates/partials/sheet_capex_detail.html` (replace inline chip with `{% with %}` + `{% include %}`)
- `static/styles.css` (added 40 lines of `.chip-*` classes)

### NOT changed
- `main_web.py`
- `app/services/`
- `app/persistence/`
- `app/runtime_impact_taxonomy.py`
- `static/app.js`
- All other templates
- All other CSS classes
- `:root` CSS variables

## Chip Spec

### 4 supported states

| State | Tooltip | Class | Color |
|---|---|---|---|
| `Drives model` | "Included in model calculations." | `chip-drives-model` | green (`#0f7a52`) |
| `Display only` | "Shown for review; does not affect calculations." | `chip-display-only` | slate (`#475569`) |
| `Pending` | "Mapped but not yet connected to runtime calculations." | `chip-pending` | amber (`#b45309`) |
| `Needs review` | "Requires review before use." | `chip-needs-review` | red (`#b91c1c`) |
| (fallback) | "Runtime impact: {value}" | `chip-unknown`, `chip-fallback` | slate (`#7a96b8`) |

### HTML structure

```html
<span class="chip chip-{state-class}" title="{tooltip}">{label}</span>
```

## Behavior

- Renders NOTHING if `runtime_impact` is missing (safe default)
- Renders a chip with the runtime impact label and tooltip
- Optional `sub_reason` parameter is appended to the tooltip
- The old `_rt_tooltip` macro in `sheet_capex_detail.html` is **preserved** (not removed)

## Backward Compatibility

- ✓ The old `.badge-rt-*` CSS classes are still defined in `sheet_capex_detail.html` (inline style block)
- ✓ The `_rt_tooltip` macro is preserved
- ✓ The old inline chip is commented out (not deleted) for reference
- ✓ The behavior is the same: chip shows the runtime impact, tooltip on hover

## No-Go Copy Check

- ✓ No "bankable", "lender-ready", "certified", "audit-ready"
- ✓ No "investor-ready", "SaaS-ready", "production-ready"
- ✓ No "guaranteed returns", "investment advice", "customer reference"
- ✓ No "external validation"
- ✓ No "validated" alone (no positive claim)
- ✓ Tooltip "Display only" copy uses "does not affect calculations" (safe)

## Hard Gates (UI-2.2)

- ✓ Only allowed files modified
- ✓ No backend/service/persistence changes
- ✓ No `runtime_impact_taxonomy.py` changes
- ✓ No `static/app.js` changes
- ✓ No `:root` CSS variable changes
- ✓ No new forbidden UI claims
- ✓ Phase 51F (21/21) + 52F G1-G6 (10/10) + 53I + 54x + UI-2.1 tests pass
- ✓ 49 new UI-2.2 tests pass
- ✓ 612 total tests pass
- ✓ rc1 (b425a07) untouched

## Visual Review Checklist

For the user (after PR is opened as DRAFT):

- [ ] Chip renders with correct color for each of 4 states
- [ ] Tooltip shows on hover (title attribute)
- [ ] Chip is small, inline, and doesn't break layout
- [ ] Empty/missing `runtime_impact` renders nothing (no empty span, no whitespace)
- [ ] Sheet's CAPEX detail page still works
- [ ] Other sheets that use the old `.badge-rt-*` style still work
- [ ] No regression in runtime summary, audit, or scenario views
- [ ] Old `.badge-rt-*` chips in other partials (if any) still work

## Test results

- `tests/test_ui2_2_*.py`: 49/49 pass
- `tests/test_ui2_1_*.py`: 56/56 pass
- `tests/test_phase54*.py`: 412/412 pass
- `tests/test_phase51f_*.py`: 21/21 pass
- `tests/test_phase52f_*.py`: 29/29 pass
- `tests/test_phase53i4_*.py`: 45/45 pass
- **Total: 612/612 pass**
