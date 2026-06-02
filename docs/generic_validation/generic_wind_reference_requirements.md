# Generic Wind Reference Requirements

This file is the **technology-specific** checklist for generic
onshore (and, where sources permit, offshore) wind reference models.
It complements
`generic_reference_acquisition_plan.md`, which describes the
acquisition framework. This file describes what a generic wind
reference must contain to be considered for parity comparison with
the Finco1 model.

> **Generic wind remains exploratory and unvalidated for any
> external claim** (see
> `generic_validation_no_go_boundaries.md` and
> `docs/external_review/no_go_claims.md`). TUHO is a specific
> project, not generic wind, and does not constitute evidence for
> generic wind parity.

---

## 1. Scope

This file applies to:

* utility-scale onshore wind;
* utility-scale offshore wind, **only** if a source produces a
  reference of that class (default scope is onshore);
* wind with co-located BESS, where the BESS portion is handled
  separately under the BESS / hybrid scope.

Out of scope:

* distributed wind (rooftop, behind-the-meter);
* floating offshore (only if a dedicated source produces a
  reference).

## 2. Required components (six-component test)

A candidate is accepted only if all six components in
`generic_reference_acquisition_plan.md` §2 are present and verified.
The components are:

1. Source identification
2. Inputs (machine-readable or structured transcription)
3. Outputs (machine-readable or structured transcription)
4. Tolerance specification
5. Provenance and licence
6. Replay instructions

## 3. Technology-specific input metadata

Beyond the global minimum metadata in
`generic_reference_acquisition_plan.md` §3, a generic wind
reference must record:

* **turbine class** — IEC class (I, II, III, S) and the turbine's
  rated power (MW per turbine).
* **hub height** — meters.
* **rotor diameter** — meters.
* **specific power** — W/m² (computed if not given).
* **air density correction** — if the source uses a non-standard
  air density, the correction must be recorded.
* **wind resource** — source of wind data (onshore met mast, SODAR,
  reanalysis, ERA5), with year range and any bias correction.
* **P50 / P90 production estimate** — if the source provides a
  probabilistic production estimate, the percentiles used must be
  recorded.
* **soiling / blade degradation** — annual degradation rate,
  cleaning / inspection schedule.
* **availability and curtailment** — planned outage schedule,
  expected grid curtailment, export limit, ice/wake-loss model.
* **wake model** — if the source uses a wake model (Jensen,
  Larsen, CFD), the model and key parameters must be recorded.

## 4. Required parity outputs (wind-specific)

A wind reference must produce the following outputs at the same
granularity as the Finco1 model:

* **annual energy production (MWh)** — gross and net of
  availability, soiling, wake, curtailment.
* **revenue** — by year, broken down by:
  * PPA tariff revenue;
  * merchant revenue (if post-PPA exposure applies);
  * green certificate revenue (if applicable in the source's
    jurisdiction);
  * other revenue streams.
* **opex** — by year, broken down by:
  * fixed O&M (per-MW or fixed), including scheduled service
    intervals and major component replacement schedule;
  * variable O&M (per-MWh);
  * insurance;
  * land lease;
  * other opex.
* **EBITDA** — by year.
* **capex schedule** — by year (turbines, BoS, civil, grid,
  development, financing costs).
* **depreciation** — book and tax, by year.
* **senior debt service** — by period.
* **DSCR** — by year.
* **taxes** — CIT, WHT, other.
* **distributions** — by year.
* **equity IRR** — at the project level.
* **project IRR** — at the project level.

## 5. Acceptance thresholds (wind-specific)

Default tolerances (overridable per reference; see
`generic_reference_acquisition_plan.md` §5):

| Output | Default tolerance |
|---|---|
| Annual energy production (MWh) | ±1.5% or ±500 MWh (whichever is larger) |
| Annual revenue | ±0.5% or ±50 kEUR (whichever is larger) |
| Annual opex | ±0.5% or ±25 kEUR (whichever is larger) |
| Annual EBITDA | ±0.5% or ±50 kEUR (whichever is larger) |
| Capex (total) | ±0.5% or ±100 kEUR (whichever is larger) |
| Annual depreciation (tax) | ±0.5% or ±10 kEUR (whichever is larger) |
| Annual senior debt service | ±0.5% or ±25 kEUR (whichever is larger) |
| Annual DSCR | ±0.01 (absolute) |
| Annual tax | ±0.5% or ±10 kEUR (whichever is larger) |
| Annual distributions | ±0.5% or ±25 kEUR (whichever is larger) |
| Equity IRR | ±25 bps |
| Project IRR | ±25 bps |

Wind is generally more variable than solar, so the energy
production tolerance is wider (±1.5% vs ±1.0%). All other tolerances
match the solar defaults.

A reference is rejected if:

* any required component in §2 is missing;
* the source's stated tolerance is wider than the Finco1 model's
  acceptance thresholds;
* the licence does not permit internal use;
* the reference is essentially a copy of TUHO, Oborovo, or any
  other Finco1-produced model.

## 6. Wind-specific rejection criteria

In addition to the global rejection criteria in
`generic_reference_acquisition_plan.md` §5, a wind reference is
rejected if:

* the source does not provide a wind resource year range and the
  source is from before 2010 (modern turbines are outside the
  source's scope);
* the source does not document a wake model and the layout has
  more than 5 turbines (wake effects are non-trivial);
* the source assumes an annual degradation rate outside the range
  0.0%–1.5%/year, and the Finco1 model cannot be made to match
  without a documented model change;
* the source's hub-height / rotor-diameter / specific-power
  combination is implausible (e.g. specific power below 150 W/m² or
  above 600 W/m²) without justification;
* the source explicitly models BESS but does not separate BESS
  capex, opex, and revenue from the wind portion.

## 7. What this file does not do

This file does not:

* define the Finco1 model's wind inputs (those are in
  `domain/revenue/`, `domain/capex/`, etc.);
* validate the Finco1 model against any wind reference (the
  validation is the next step after acquisition);
* authorize any external claim about generic wind;
* relax the no-go list.

## 8. Cross-references

* `docs/generic_validation/generic_reference_acquisition_plan.md`
* `docs/generic_validation/generic_validation_no_go_boundaries.md`
* `reports/generic_validation/reference_model_inventory_template.json`
* `reports/generic_validation/generic_validation_readiness_matrix.json`
* `reports/validation/validation_evidence_matrix.json`
  (AREA-004 — generic wind)
* `docs/external_review/no_go_claims.md`

---

*End of generic wind reference requirements.*
