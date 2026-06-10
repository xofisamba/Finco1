# Phase S3 — Driver-to-KPI Binding Suite — Governance Doc

## Status

- **Type:** Tests + minimal helper/template
  updates. No formula changes. No model changes.
  No factory changes. No frozen-schedule
  changes.
- **Branch:** `phase-s3-driver-kpi-binding-suite`
- **Base:** main @ `20c7298` (post-S2 merge)
- **Goal:** Before internal pilot, prove that
  every editable Generic driver either
  demonstrably moves at least one relevant KPI
  or is correctly classified as a non-binding
  / reporting / metadata field.

## The S3 finding (key insight)

S1 unified Generic on DSCR sculpt and added
`ppa_term_years` to the schema (which affects
`total_revenue_keur` and `total_ebitda_keur`
via the PPA tariff duration) and
`construction_months` (which affects
`equity_irr` via the `financial_close` timing
shift). After S1, the runtime consumes both
fields, but the P1-A classification still
labels them as `METADATA_ONLY`. This is a
classification mismatch.

S3 corrects the mismatch with a **runtime
sweep** (not a guess): for each driver, the
test suite perturbs the value by a meaningful
amount and asserts which KPIs move.

## S3 review fix (Round 2)

Round 1 of S3 lumped `construction_months`
with the 3 true DSCR sculpt drivers under a
single "Model driver" badge. Review feedback
rejected that classification because
`construction_months` does NOT bind senior
debt / DSCR — it only shifts the
construction-period timeline.

**Round 2 splits the classification into
two separate sets:**

- **DSCR sculpt drivers (3 fields):** the
  fields that actually bind senior debt /
  DSCR under the current DSCR sculpt sizing
  method. Badge: "DSCR sculpt driver" (blue).
- **Timing drivers (1 field):**
  `construction_months` is a model-affecting
  field via the construction-period timeline,
  not via the DSCR sculpt engine. Badge:
  "Timing driver" (soft amber).

This matches what the runtime actually does:
`construction_months` can move `equity_irr`
by ~10bps (between 6mo and 36mo construction
periods) via the `financial_close` timing,
but it does NOT change `revenue`, `EBITDA`,
`senior debt`, or `DSCR`.

## The S3 driver inventory (locked by tests)

### WIRED (6 fields, no badge by default)

| Field | Moves | Tested |
|---|---|---|
| `tariff_eur_mwh` | revenue, EBITDA, IRR, DSCR, debt | Yes |
| `p50_hours` | revenue, EBITDA, IRR, DSCR, debt | Yes |
| `capacity_mw` | revenue, CAPEX, EBITDA, IRR, DSCR, debt | Yes |
| `total_capex_keur` | CAPEX, IRR, DSCR (sculpt re-sizes debt) | Yes |
| `opex_y1_keur` | EBITDA, OPEX, IRR, DSCR, debt | Yes |
| `ppa_term_years` | revenue, EBITDA (S3 reclassification) | Yes |

### DSCR SCULPT DRIVERS (3 fields, "DSCR sculpt driver" badge, blue)

These are the fields that actually bind
senior debt / DSCR under the current DSCR
sculpt sizing method. Moving these changes
`min_dscr` and `senior_debt_amount_keur`
directly.

| Field | Moves | Tested |
|---|---|---|
| `interest_rate_pct` | DSCR, debt | Yes |
| `tenor_years` | DSCR, debt | Yes |
| `target_dscr` | DSCR, debt | Yes |

### TIMING DRIVERS (1 field, "Timing driver" badge, soft amber)

`construction_months` is **not** a DSCR
sculpt driver. It is a model-affecting field
via the construction-period timeline (shifts
`financial_close`). It can move `equity_irr`
by ~10bps (between 6mo and 36mo construction
periods) but does **NOT** change `revenue`,
`EBITDA`, `senior debt`, or `DSCR`.

| Field | Moves | Tested |
|---|---|---|
| `construction_months` | equity_irr (via financial_close timing) | Yes |

### REPORTING_DERIVED (1 field, "Indicative (derived)" badge)

| Field | Binding? | Tested |
|---|---|---|
| `gearing_pct` | NO (S2 invariant) | Yes |

### METADATA_ONLY (0 fields)

`ppa_term_years` and `construction_months` were
in `METADATA_ONLY` per the P1-A audit, but S1
made them model-affecting. S3 corrects the
classification by moving them out.

### NOT_WIRED (0 fields)

No editable field is `NOT_WIRED`.

## The KPI response map (proven by S3 tests)

| Field | total_revenue | total_ebitda | total_capex | project_irr | equity_irr | min_dscr | senior_debt |
|---|---|---|---|---|---|---|---|
| `tariff_eur_mwh` | ✓ | ✓ | – | ✓ | ✓ | ✓ | ✓ |
| `p50_hours` | ✓ | ✓ | – | ✓ | ✓ | ✓ | ✓ |
| `capacity_mw` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `total_capex_keur` | – | – | ✓ | ✓ | ✓ | ✓ | – (sculpt) |
| `opex_y1_keur` | – | ✓ | – | ✓ | ✓ | ✓ | ✓ |
| `ppa_term_years` | ✓ | ✓ | – | – | – | – | – |
| `interest_rate_pct` | – | – | – | – | – | ✓ | ✓ |
| `tenor_years` | – | – | – | – | – | ✓ | ✓ |
| `target_dscr` | – | – | – | – | – | ✓ | ✓ |
| `construction_months` | – | – | – | – | ✓ | – | – |
| `gearing_pct` | – | – | – | – | – | – | – (S2 invariant) |

✓ = KPI changes when the field is perturbed
– = KPI does not change

## The S3 KPI-binding rules (semantic)

1. **Revenue drivers** (tariff, p50, capacity,
   ppa_term) all move `total_revenue_keur` and
   therefore `total_ebitda_keur`.
2. **Production drivers** (p50, capacity) move
   generation, which is the multiplier on
   revenue.
3. **CAPEX** (capacity, total_capex) moves
   `total_capex_keur`; under DSCR sculpt, the
   senior debt re-sizes to hit `target_dscr`,
   so the debt amount may NOT change but the
   DSCR profile does.
4. **OPEX** (opex) moves `total_opex_keur` and
   therefore `total_ebitda_keur`.
5. **DSCR sculpt drivers** (interest_rate,
   tenor, target_dscr) move senior debt and
   the realized DSCR profile. These are the
   only fields that change `min_dscr` and
   `senior_debt_amount_keur` directly.
6. **Timing drivers** (construction_months)
   move `financial_close` (and therefore the
   construction-period timing), which affects
   equity_irr by a small amount (~10bps
   spread between 6mo and 36mo) but does NOT
   change revenue, EBITDA, senior debt, or
   DSCR. Construction_months is NOT a DSCR
   sculpt driver.
7. **gearing_pct** is `REPORTING_DERIVED`:
   under DSCR sculpt, the user-supplied
   gearing is preserved as a reporting metric
   but is NOT a binding driver of senior
   debt size. The realized gearing is
   `senior_debt / total_capex`.

## What S3 does NOT do

- **No formula / model / construction / C10 /
  R-PAR / IDC / tax / debt / depreciation
  changes.**
- **No factory path changes.** TUHO, Oborovo,
  and Generic factories preserved bit-exact.
- **No frozen-schedule changes.**
- **No `manual_gearing` debt sizing method.**
- **No `min(gearing cap, sculpt)` blend.**
- **No `ProjectInputsSchema` removals.**
- **No `use_construction_schedule_engine`
  flip.** Remains False.
- **No R99 / R102 / G20 promotion.**
- **No `static/app.js` changes.** UI changes
  are confined to the helper module
  (`app/ui/generic_driver_status_badges.py`),
  the inputs_section.html partial
  (PPA Term and Construction Period rows), and
  P1-B / S2 test files.
- **No `main_web.py` / `main_api.py`
  changes.**
- **No Tailwind / Alpine / React / Vue /
  Svelte.**
- **No JS calc.**
- **No `rc1` change.** SHA
  `b425a0708719eaa5e1d922b1008e5609758e0ad4`
  preserved.

## Pilot implication

The driver inventory above is what the pilot
user will see in the form. Every editable
field either:

- moves an expected KPI (proved by a runtime
  test in `test_phase_s3_driver_kpi_binding.py`),
  or
- is correctly classified as a non-binding
  reporting field (gearing_pct).

This means the pilot user cannot be misled
into thinking a field does something it
doesn't do. The badge vocabulary and the
test suite together guarantee the truth.

## Stop-after-report contract

DRAFT PR only. Do NOT mark ready. Do NOT
merge. Awaiting user review and explicit
go-ahead.

## What remains for M1 / M2

M1 / M2 are the scenario matrix phases:
multi-scenario Base / Downside / Upside
coverage at scale. The S3 binding suite
provides the per-driver sensitivity evidence
that M1 / M2 will need for cross-scenario
KPI variance analysis.
