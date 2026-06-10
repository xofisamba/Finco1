# Phase P1-B — Generic Driver Status Badges (UI Explanation)

## Purpose

P1-B is the **UI explanation layer** that follows the
Phase P1-A driver-response audit (PR #600).

P1-A audited the Generic Solar / Wind runtime and found
that the 11 editable input drivers fall into four
distinct categories:

- 5 are **WIRED** — they flow into the runtime and
  move `project_irr` when changed.
- 4 are **WIRED_PARTIAL** — they flow into the runtime
  and affect `equity_irr`, `min_dscr`, debt sizing, etc.,
  but **do not move `project_irr`** under the current
  `DSCR_SCULPT` debt sizing method.
- 2 are **METADATA_ONLY** — they are saved/displayed
  for context but are **not currently used by the
  Generic runtime calculation**.
- 0 are `NOT_WIRED`.

P1-B **does not change any of that**. It only **labels
the drivers in the input form** so the pilot user
sees, at a glance, which fields are wired, which are
DSCR-sculpt drivers, and which are metadata.

## Why this matters

Without badges, a pilot user assumes the form fields
are all equally actionable — i.e. that nudging
`gearing_pct` will move `project_irr`. It won't.
That false expectation leads to "I changed the gear
and the IRR didn't move" confusion, which is the
exact pilot feedback we are trying to prevent (see
25C-3 feedback capture, PR #596).

## What is shipped

### 1. Two new badge classes

In `static/styles.css`:

- `.badge-metadata` — gray, subdued. Used for
  `ppa_term_years` and `construction_months`.
- `.badge-dscr-sculpt` — blue, info-style. Used for
  `gearing_pct`, `interest_rate_pct`, `tenor_years`,
  `target_dscr`.

### 2. Field-row badge updates

In `app/templates/partials/inputs_section.html`:

The `field_row` macro gained an optional
`badge_title` parameter (renders as a `title=`
attribute on the badge for tooltip support) and an
optional `data-driver-status` / `data-field-name`
attribute for downstream tooling.

The following fields now carry a metadata badge:

- `ppa_term_years` (Revenue / PPA Summary)
- `construction_months` (Schedule)

The following fields now carry a DSCR sculpt badge:

- `gearing_pct` (Financing Summary)
- `target_dscr` (Financing Summary)
- `interest_rate_pct` (Financing Summary)
- `tenor_years` (Financing Summary)

Fully wired drivers (`tariff_eur_mwh`, `p50_hours`,
`capacity_mw`, `total_capex_keur`, `opex_y1_keur`) get
**no badge** — the form stays uncluttered per the
P1-B brief.

### 3. Driver status legend (new block)

Below the existing Phase 24-H exploratory warning,
P1-B adds a `data-driver-status-legend="true"` block
that:

- shows a `METADATA ONLY` chip and a short copy
  explaining which fields are metadata-only and why
  they are kept
- shows a `DSCR SCULPT DRIVER` chip and a short copy
  explaining which fields are DSCR-sculpt drivers and
  that `project IRR may not change`

The block only renders when
`is_exploratory_project` is true (same condition
as the existing exploratory warning), so factory
TUHO / Oborovo references are unaffected.

## Tooltip copy

The tooltip copy is honest about the exploratory
scope. It uses negation — "may not change" — not
positive claim. It does not call the output
"lender-ready", "audit-ready", or "bank-approved".

The Phase 24-H exploratory notice (above the legend)
still does the heavy disclaiming work and remains
unchanged.

## What is NOT shipped

- No formula changes
- No model logic changes
- No `ProjectInputsSchema` changes
- No schema migration
- No persistence writes
- No new feature flags
- No `use_construction_schedule_engine=True`
- No `manual_gearing` debt sizing method
- No TUHO / Oborovo factory changes
- No C10, R-PAR, IDC, tax, debt, depreciation changes
- No JS calc, no Tailwind, no Alpine

`rc1` SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4`
remains untouched.

## File map (4 files)

| File | Change |
|---|---|
| `app/ui/generic_driver_status_badges.py` | NEW helper module — status vocabulary, badge mapping, tooltip copy, `FieldDriverStatus` dataclass, `get_field_badge(field)`, `is_metadata_only_field(field)`, `is_dscr_sculpt_driver_field(field)`, `is_wired_field(field)`, `get_field_status(field)` |
| `app/templates/partials/inputs_section.html` | MODIFIED — 6 `field_row` calls swap badge; new `badge_title` param on `field_row` macro; new `inp-driver-status-note` block below exploratory warning |
| `static/styles.css` | MODIFIED — adds `.badge-metadata` and `.badge-dscr-sculpt` classes + `.inp-driver-status-note` layout |
| `tests/test_phase_p1b_driver_status_badges.py` | NEW — 78 tests pinning mapping, tooltips, partial render, CSS presence, schema invariance, formula-file invariance, forbidden-path invariance, rc1 reachability, factory-path invariance, helper safety |

## How to verify locally

```bash
# Run the P1-B tests
pytest tests/test_phase_p1b_driver_status_badges.py -q

# 78/78 should pass
```

The helper is read-only and pure. It can be imported
in any future UI surface that wants the same field
→ status mapping.

## Recommended next steps (out of scope)

P1-B does NOT:

- Implement `manual_gearing` (Section 7 of the
  design doc). The 4 DSCR sculpt drivers stay
  labeled. A pilot user can still nudge them; the
  tooltip tells them IRR may not change.
- Restructure the input form layout.
- Promote any G20 / R99 / R102 status.

The next open decision (after this PR is reviewed)
is: do we want to implement `manual_gearing` as a
debt sizing method, or do we leave the current
DSCR sculpt + badge behavior and call it good?

Either path is fine; P1-B does not lock us in.
