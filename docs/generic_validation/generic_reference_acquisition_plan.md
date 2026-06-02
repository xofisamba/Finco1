# Generic Reference Acquisition Plan

This file is the **acquisition plan** for generic solar and wind
reference Excel models. It describes *how* the project will collect
usable reference models, *what* a usable reference must contain, and
*what happens after* a reference is collected.

> **This plan does not validate generic solar or wind.** Generic
> solar and wind remain exploratory and unvalidated for any external
> claim (see
> `docs/validation/internal_vs_external_validation_boundaries.md` and
> `docs/external_review/no_go_claims.md`). The plan is the
> *acquisition framework* that will eventually enable generic
> validation, not the validation itself.

---

## 1. Why this plan exists

TUHO (Wind 1) and Oborovo (Solar PV) are two specific reference
projects pinned by Phase 51F. They prove the model behaves correctly
*for those two projects*. They do not prove the model behaves
correctly for arbitrary solar or wind projects.

To claim anything about *generic* solar or *generic* wind, the
project needs a set of reference projects (preferably several per
technology) that:

* come from independent sources (not produced by the project);
* cover a range of geographies, sizes, and configurations;
* have published, auditable inputs and outputs;
* can be reproduced by the model within a defined tolerance.

This plan is the framework for acquiring such references.

## 2. What a usable reference model must contain

A usable reference has six components. A candidate is rejected if
*any* of the six is missing or unverified. See
`generic_solar_reference_requirements.md` and
`generic_wind_reference_requirements.md` for the technology-specific
checklist.

1. **Source identification** — who produced the model, when, and
   under what authority. The source must be independent of the
   Finco1 project.
2. **Inputs (machine-readable or transcribed to a structured
   format)** — every input the Finco1 model needs must be present
   or derivable. See the metadata and parity-output sections below.
3. **Outputs (machine-readable or transcribed)** — every parity
   output the Finco1 model is expected to reproduce must be present
   or derivable, at the same granularity.
4. **Tolerance specification** — the source's stated accuracy or
   tolerance, or an agreed tolerance with the source. The Finco1
   model's outputs must fall within this tolerance of the source's
   outputs.
5. **Provenance and licence** — explicit permission to use the
   reference for internal validation, including any required
   attribution or redaction.
6. **Replay instructions** — step-by-step instructions for
   reproducing the source's outputs from the inputs. Without replay
   instructions, the reference cannot be validated.

## 3. Minimum metadata (per reference)

The metadata recorded in
`reports/generic_validation/reference_model_inventory_template.json`
for each reference must include at least:

* **technology** — `solar` / `wind` / `solar+bess` / `wind+bess` /
  other.
* **country** — ISO 3166-1 alpha-2 code, plus region/state if
  relevant.
* **COD** (Commercial Operation Date) — actual or planned, with the
  distinction recorded.
* **capacity** — installed capacity, in MW (or MWh for BESS), with
  the measurement basis (DC vs AC for solar, nameplate vs
  curtailment-adjusted for wind).
* **revenue type** — PPA, merchant, regulated, hybrid, with key
  parameters (tariff, escalation, tenor, post-PPA exposure).
* **capex** — total and breakdown (modules, BoS, civil, grid,
  development, financing costs), with the basis (overnight,
  inclusive, in nominal or real money).
* **opex** — fixed and variable, with the basis (per-MW, per-MWh, or
  fixed annual).
* **debt assumptions** — type (senior, SHL, mezzanine), tenor,
  pricing, amortisation profile, DSCR target.
* **DSCR logic** — the project's stated DSCR policy (lock-up,
  sculpting, sweep, default cure). Note that
  `partial_pay_sweep` and flat/min DSCR sculpting are
  **NOT APPROVED** in the Finco1 model and must not be claimed in
  the reference.
* **tax assumptions** — CIT rate, LCF carryforward rules, ATAD
  EBITDA limitation applicability, withholding tax rates on debt
  service and dividends.
* **depreciation assumptions** — book and tax depreciation
  schedules, including any LCF-relevant rules.
* **distributions** — distribution policy (sweep, dividend
  waterfall, retention buffer) and lock-up periods.
* **export logic** — how the source produces its outputs (Excel
  template version, build version, runtime, etc.).

## 4. Required parity outputs

For each reference, the following outputs must be produced by both
the source and the Finco1 model, and compared within tolerance:

* **revenue** — annual and total, in source currency.
* **opex** — annual and total, in source currency.
* **EBITDA** — annual and total.
* **senior debt service** — annual schedule (interest + principal).
* **DSCR** — annual, with the same definition as the source.
* **taxes** — annual, broken down by CIT, WHT, and other
  categories present in the source.
* **distributions** — annual and total, with the same definition
  as the source.
* **equity IRR** — at the project level, with the same convention
  (date convention, interim cash flow treatment).

The full required parity table is in
`generic_solar_reference_requirements.md` and
`generic_wind_reference_requirements.md`.

## 5. Acceptance thresholds

A reference is considered **parity-acceptable** if:

* the Finco1 model's outputs match the source outputs within the
  tolerances below, for at least three independent references per
  technology, before the project may move generic solar or generic
  wind from `exploratory` to any stronger category in
  `reports/validation/validation_evidence_matrix.json`.

Default tolerances (override per reference if the source specifies
stricter or looser limits):

| Output | Default tolerance |
|---|---|
| Annual revenue | ±0.5% or ±50 kEUR (whichever is larger) |
| Annual opex | ±0.5% or ±25 kEUR (whichever is larger) |
| Annual EBITDA | ±0.5% or ±50 kEUR (whichever is larger) |
| Annual senior debt service | ±0.5% or ±25 kEUR (whichever is larger) |
| Annual DSCR | ±0.01 (absolute) |
| Annual tax | ±0.5% or ±10 kEUR (whichever is larger) |
| Annual distributions | ±0.5% or ±25 kEUR (whichever is larger) |
| Equity IRR | ±25 bps |
| Project IRR | ±25 bps |

A reference is **rejected** if:

* any required component in §2 is missing;
* the source cannot be reproduced from its inputs (the model
  produces different outputs than the source, on the source's own
  inputs);
* the source's stated tolerance is wider than the Finco1 model's
  acceptance thresholds, making parity comparison meaningless;
* the licence does not permit internal use;
* the reference is essentially a copy of TUHO or Oborovo, or of any
  other Finco1-produced model.

## 6. Confidentiality and provenance

References may come from third-party lenders, sponsors, advisers,
publications, or other sources. Each reference must be handled
according to:

* its licence and the source's NDA or contract terms;
* the project's general confidentiality posture (no customer data
  leaves the project; no third-party data is shared beyond the
  project team);
* the no-go claim list — the project does not make lender, bank,
  audit, certification, regulatory, or SaaS claims about any
  reference.

Each reference's provenance is recorded in
`reports/generic_validation/reference_model_inventory_template.json`
(acquired date, source, contact, licence, classification).

## 7. Acquisition workflow

1. **Identify candidate.** A team member proposes a candidate with
   a short rationale. The candidate is logged in the inventory
   template with status `candidate`.
2. **Initial gate.** The candidate is checked against the six
   components in §2. If any is missing, the candidate is rejected
   or marked `incomplete` until the gap is filled.
3. **Licence check.** The candidate's licence and NDA status is
   verified. If the licence is incompatible with internal use, the
   candidate is rejected.
4. **Inputs and outputs transcribed.** The inputs are transcribed
   into the Finco1 model's input format. The outputs are
   transcribed into a structured comparison sheet. The candidate's
   status moves to `transcribed`.
5. **First parity run.** The Finco1 model is run on the transcribed
   inputs. The outputs are compared to the source outputs. The
   candidate's status moves to `parity-pass` or `parity-fail`.
6. **Tolerance refinement.** If `parity-fail`, the discrepancy is
   investigated. Either the input transcription is corrected, the
   model is corrected (via the documented model-change protocol,
   not silently), or the tolerance is revisited and recorded.
7. **Final accept or reject.** The reference is moved to
   `accepted` or `rejected` in the inventory. The decision and
   rationale are recorded.

## 8. Outputs of the acquisition process

The acquisition process produces:

* the inventory file
  (`reports/generic_validation/reference_model_inventory_template.json`,
  populated per reference);
* parity reports per reference (machine-readable, in the same
  directory or a sub-directory);
* an updated `generic_validation_readiness_matrix.json` showing
  the count of accepted references per technology.

It does **not** produce:

* a generic-solar or generic-wind external claim;
* a relaxation of the no-go list;
* a change to the matrix's `exploratory` category for generic solar
  or wind. The category only changes after at least three accepted
  references per technology, an internal review of the parity
  results, and a dedicated governance change.

## 9. Dependencies

* The B3 validation evidence matrix
  (`reports/validation/validation_evidence_matrix.json`) is the
  authoritative record of generic-solar and generic-wind evidence
  status. B2 feeds into it but does not override it.
* The Phase 51F guardrails cover the model core. They do not
  automatically cover generic solar or wind; new pins for
  generic-solar and generic-wind parity outputs must be added with
  the documented intentional-update protocol.
* The B7 pilot protocol may use an accepted reference to drive a
  pilot scenario, but only after the reference is accepted.

## 10. Cross-references

* `docs/generic_validation/generic_solar_reference_requirements.md`
* `docs/generic_validation/generic_wind_reference_requirements.md`
* `docs/generic_validation/generic_validation_no_go_boundaries.md`
* `reports/generic_validation/reference_model_inventory_template.json`
* `reports/generic_validation/generic_validation_readiness_matrix.json`
* `docs/validation/validation_evidence_matrix.md` (B3 narrative)
* `reports/validation/validation_evidence_matrix.json` (B3 matrix)
* `docs/external_review/no_go_claims.md` (no-go list)

---

*End of generic reference acquisition plan.*
