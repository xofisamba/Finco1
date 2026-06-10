# Phase S2 — Gearing as Output / Derived Reporting Metric — Governance Doc

## Status

- **Type:** UI / labels / derived-metric cleanup.
  No formula changes. No model changes. No factory
  changes. No frozen-schedule changes.
- **Branch:** `phase-s2-gearing-as-output`
- **Base:** main @ `3c33f19` (post-S1 merge)
- **Goal:** make the Generic Solar / Generic
  Wind sizing path honest about the role of
  gearing in DSCR-sculpt sizing. Realized
  gearing is a derived output; the
  user-supplied `gearing_pct` is an indicative
  assumption that the runtime preserves as a
  reporting metric but does NOT use to size
  senior debt.

## Why S2 is necessary (the S1 followup gap)

Phase S1 unified the Generic sizing path on
DSCR sculpt. The runtime now sizes senior
debt to hit `target_dscr` via the sculpt
engine, and the user-supplied `gearing_pct`
is preserved as a reporting metric. The
backend authority is correct.

However, after S1, the UI still showed:

- The Financing Summary row labeled
  `gearing_pct` with the **"DSCR sculpt
  driver"** badge and a tooltip claiming
  it "affects debt / equity / DSCR outputs
  under the current DSCR sculpting method".
- The narrative note in the inputs section
  said `gearing_pct, interest_rate_pct,
  tenor_years, and target_dscr affect debt /
  equity / DSCR outputs`.
- The Senior Debt sheet and the new-project
  form used the bare label `Gearing` /
  `Gearing (%)`.
- The Project Review showed a row labeled
  `Gearing` with no honest copy explaining
  that the value is an indicative input and
  the realized gearing is a derived output.

These labels could create a user impression
that `gearing_pct` directly sizes senior
debt (the old `capex * gearing` formula).
After S1, that formula is not what runs.

S2 is the user-facing cleanup that aligns
the labels with the S1 backend behavior.

## The S2 contract (what changed)

### Driver status mapping

`gearing_pct` moved from
`DSCR_SCULPT_DRIVER_FIELDS` to a new
`REPORTING_DERIVED_FIELDS` set. The
remaining `DSCR_SCULPT_DRIVER_FIELDS` are
`interest_rate_pct`, `tenor_years`, and
`target_dscr` (3 fields, down from 4).

```
REPORTING_DERIVED_FIELDS = ("gearing_pct",)
DSCR_SCULPT_DRIVER_FIELDS = (
    "interest_rate_pct",
    "tenor_years",
    "target_dscr",
)
```

### Badge vocabulary

The new badge for `gearing_pct`:

- **Status:** `REPORTING_DERIVED`
- **Badge text:** "Indicative (derived)"
- **CSS class:** `badge-reporting` (soft
  green palette, visually distinct from
  `badge-metadata` (gray, "no effect") and
  `badge-dscr-sculpt` (blue, "binds"))
- **Tooltip:** "Indicative gearing
  assumption. The realized gearing is shown
  as a derived output (senior debt / total
  CAPEX). Under DSCR sculpt sizing, senior
  debt is sized to hit target DSCR, so the
  user-supplied gearing_pct is preserved as
  a reporting metric, not as a binding
  senior debt sizing driver."

### User-facing labels (template / project review / helpers)

| Old label | New label | File |
|---|---|---|
| `Gearing` (badge: "DSCR sculpt driver") | `Indicative gearing (input)` (badge: "Indicative (derived)") | `app/templates/partials/inputs_section.html` |
| `Gearing` (assumptions panel) | `Indicative gearing (input)` | `app/templates/partials/sheet_senior_debt.html` |
| `Gearing (%)` (form) | `Gearing (%, indicative)` | `app/templates/partials/new_project_form.html` |
| `Gearing` (project review row) | `Indicative gearing (input)` | `app/ui/project_review.py` |
| `Gearing (%)` (input helpers row) | `Gearing (%, indicative input)` | `app/input_helpers.py` |
| `Gearing (%, indicative input)` (workbook) | same | `app/ui/project_context.py` (downstream) |

### Narrative note in inputs section

Old:

> `gearing_pct`, `interest_rate_pct`,
> `tenor_years`, and `target_dscr` affect
> debt / equity / DSCR outputs under the
> current DSCR sculpting method, but project
> IRR may not change (see the "DSCR sculpt
> driver" badges next to those fields).

New:

> `interest_rate_pct`, `tenor_years`, and
> `target_dscr` affect debt / equity / DSCR
> outputs under the current DSCR sculpting
> method, but project IRR may not change
> (see the "DSCR sculpt driver" badges next
> to those fields).
>
> `gearing_pct` is an indicative gearing
> assumption. The realized gearing is shown
> as a derived output (senior debt / total
> CAPEX). Under DSCR sculpt sizing, senior
> debt is sized to hit target DSCR, so the
> user-supplied gearing_pct is preserved as
> a reporting metric, not as a binding
> senior debt sizing driver (see the
> "Indicative (derived)" badge next to
> that field).

### CSS class

A new `.badge-reporting` class is defined
in `static/styles.css`, with a soft green
palette that is visually distinct from both
the gray "metadata only" badge and the
blue "DSCR sculpt driver" badge.

```css
.badge-reporting {
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
  padding: 0.18rem 0.45rem;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  white-space: nowrap;
}
```

## What S2 does NOT do

- **No financial formula changes.** The
  runtime `dscr_sculpt` path is unchanged.
- **No model changes.** No `waterfall_core`,
  no `waterfall_runner`, no `project_factories`.
- **No factory path changes.** TUHO,
  Oborovo, and Generic factories are
  preserved bit-exact:
  - TUHO: `debt_sizing_method="fixed"`,
    `fixed_debt_keur=43359.0`.
  - Oborovo: `debt_sizing_method="gearing_cap"`,
    `fixed_debt_keur=42852.26672602787`.
  - Generic Solar / Wind:
    `debt_sizing_method="dscr_sculpt"`.
- **No frozen-schedule changes.**
- **No `manual_gearing` debt sizing method.**
- **No `min(gearing cap, sculpt)` blend.** The
  runtime may fall back to the gearing cap if
  CFADS is insufficient to hit `target_dscr`,
  but S2 does not introduce a new sizing
  semantic.
- **No `ProjectInputsSchema` change.** The
  schema and resolver are unchanged.
- **No `use_construction_schedule_engine`
  flip.** Remains False.
- **No R99 / R102 / G20 promotion.**
- **No `static/app.js` changes.** UI changes
  are confined to Jinja templates, the
  `app/ui/generic_driver_status_badges.py`
  helper, and the `static/styles.css` palette.
- **No `main_web.py` / `main_api.py` changes.**
- **No Tailwind / Alpine / React / Vue /
  Svelte.**
- **No JS calc.**
- **No `rc1` change.**
  `b425a0708719eaa5e1d922b1008e5609758e0ad4`
  preserved.

## What remains for S3 driver-to-KPI binding suite

S2 only relabels the existing fields and
adds a new badge vocabulary. S3 will be the
followup arc that introduces per-driver
sensitivity tests (one test per
non-metadata field, asserting exactly which
KPI moves and by how much for a unit change
in the input). S3 is its own larger arc and
is NOT scoped by S2.

## Why this is honest, not just a label change

The tooltip text on the `Indicative (derived)`
badge explicitly states that `gearing_pct` is
an indicative assumption and that the
realized gearing is a derived output
(senior debt / total CAPEX). The runtime
proves this claim: the S2 test
`test_wind_senior_debt_invariant_under_gearing_sweep`
runs the same Wind inputs at
gearing_pct = 40 / 70 / 85 and asserts that
all three produce exactly the same
`senior_debt_amount_keur` (the sculpt engine
chose a debt size of 15,612.87 kEUR for all
three, which is 31.2% of the 50,000 kEUR
capex — different from any of the user
inputs). The realized gearing is 31.2%, not
40% / 70% / 85%.

The S2 test
`test_realized_gearing_equals_senior_debt_over_capex`
further asserts that the realized gearing
differs from the user-supplied input
(proving the input is not the formula).

## Stop-after-report contract

DRAFT PR only. Do NOT mark ready. Do NOT
merge. Awaiting user review and explicit
go-ahead.
