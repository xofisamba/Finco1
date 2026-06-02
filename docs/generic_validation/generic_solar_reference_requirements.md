# Generic Solar Reference Requirements

This file is the **technology-specific** checklist for generic solar
photovoltaic (PV) reference models. It complements
`generic_reference_acquisition_plan.md`, which describes the
acquisition framework. This file describes what a generic solar
reference must contain to be considered for parity comparison with
the Finco1 model.

> **Generic solar remains exploratory and unvalidated for any
> external claim** (see
> `generic_validation_no_go_boundaries.md` and
> `docs/external_review/no_go_claims.md`). Oborovo is a specific
> project, not generic solar, and does not constitute evidence for
> generic solar parity.

---

## 1. Scope

This file applies to:

* utility-scale solar PV (ground-mounted, fixed-tilt or
  single-axis tracker);
* solar PV with co-located BESS, where the BESS portion is handled
  separately under the BESS / hybrid scope;
* rooftop or distributed solar **only** if a source produces a
  reference of that class (utility-scale is the default scope).

Out of scope:

* concentrated solar power (CSP);
* solar thermal;
* floating PV (only if a dedicated source produces a reference).

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
`generic_reference_acquisition_plan.md` §3, a generic solar
reference must record:

* **technology subtype** — `mono-Si` / `poly-Si` / `thin-film` /
  `bifacial` / `HJT` / other.
* **mounting** — `fixed-tilt` / `single-axis-tracker` /
  `dual-axis-tracker` (rare).
* **tilt and azimuth** (if fixed) or **tracking algorithm** (if
  tracking).
* **inverter topology** — central / string / micro, with DC/AC
  ratio.
* **soiling and degradation** — annual degradation rate, soiling
  loss assumption, cleaning schedule.
* **P50 / P90 production estimate** — if the source provides a
  probabilistic production estimate, the percentiles used must be
  recorded.
* **resource data** — source of solar resource (satellite,
  ground-measured, TMY), with year range and any bias correction.
* **availability and curtailment** — planned outage schedule,
  expected grid curtailment, export limit.

## 4. Required parity outputs (solar-specific)

A solar reference must produce the following outputs at the same
granularity as the Finco1 model:

* **annual energy production (MWh)** — gross and net of
  availability, soiling, curtailment.
* **revenue** — by year, broken down by:
  * PPA tariff revenue;
  * merchant revenue (if post-PPA exposure applies);
  * CO2 certificate revenue (if applicable in the source's
    jurisdiction);
  * other revenue streams.
* **opex** — by year, broken down by:
  * fixed O&M (per-MW or fixed);
  * variable O&M (per-MWh);
  * insurance;
  * land lease;
  * other opex.
* **EBITDA** — by year.
* **capex schedule** — by year (often back-loaded to construction
  years).
* **depreciation** — book and tax, by year.
* **senior debt service** — by period (semiannual if the source
  uses semiannual periods, as the Finco1 model does).
* **DSCR** — by year (or by period, mapped to year for reporting).
* **taxes** — CIT, WHT (on debt service and dividends), other.
* **distributions** — by year, with the same definition as the
  source.
* **equity IRR** — at the project level, with the source's stated
  convention.
* **project IRR** — at the project level, with the source's
  stated convention.

## 5. Acceptance thresholds (solar-specific)

Default tolerances (overridable per reference; see
`generic_reference_acquisition_plan.md` §5):

| Output | Default tolerance |
|---|---|
| Annual energy production (MWh) | ±1.0% or ±500 MWh (whichever is larger) |
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

A reference is rejected if:

* any required component in §2 is missing;
* the source's stated tolerance is wider than the Finco1 model's
  acceptance thresholds;
* the licence does not permit internal use;
* the reference is essentially a copy of Oborovo, TUHO, or any
  other Finco1-produced model.

## 6. Solar-specific rejection criteria

In addition to the global rejection criteria in
`generic_reference_acquisition_plan.md` §5, a solar reference is
rejected if:

* the source does not provide a resource data year range and the
  source is from before 2010 (modern modules and inverters are
  outside the source's scope);
* the source assumes a degradation rate outside the range
  0.0%–1.5%/year, and the Finco1 model cannot be made to match
  without a documented model change;
* the source uses a soiling loss outside the range 1%–5% without
  justification;
* the source's DC/AC ratio is outside the range 1.0–1.5, and the
  reference is presented as representative of utility-scale
  practice;
* the source explicitly models BESS but does not separate BESS
  capex, opex, and revenue from the PV portion.

## 7. What this file does not do

This file does not:

* define the Finco1 model's solar inputs (those are in
  `domain/revenue/`, `domain/capex/`, etc.);
* validate the Finco1 model against any solar reference (the
  validation is the next step after acquisition);
* authorize any external claim about generic solar;
* relax the no-go list.

## 8. Cross-references

* `docs/generic_validation/generic_reference_acquisition_plan.md`
* `docs/generic_validation/generic_validation_no_go_boundaries.md`
* `reports/generic_validation/reference_model_inventory_template.json`
* `reports/generic_validation/generic_validation_readiness_matrix.json`
* `reports/validation/validation_evidence_matrix.json`
  (AREA-003 — generic solar)
* `docs/external_review/no_go_claims.md`

---

*End of generic solar reference requirements.*
