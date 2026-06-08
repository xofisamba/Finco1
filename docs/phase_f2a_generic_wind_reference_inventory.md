# Phase F2-A — Generic Wind Reference Candidate Inventory

> Type: docs-only, design-only
> Branch: `phase-f2a-generic-wind-reference-inventory`
> Base SHA: `c8471f3bd2ef150237d7bd779360ba2af538330e` (post-F1)
> Status: DRAFT, do not mark ready, do not merge
> Scope: factual inventory + gap analysis for Generic Wind
> Hard boundary: **Generic Wind remains at Level 1 (Exploratory / Unvalidated)**. F2-A does NOT promote Generic Wind.

## 0. Purpose

F1 (merged) defined the maturity ladder, the validation framework,
and the governance gates. F2-A answers one specific question:

> "What is objectively missing today before Generic Wind can begin a controlled journey toward Reference status?"

F2-A is a **factual inventory** and a **gap analysis**. F2-A does
not design the Generic Wind validation pack; that is the job of
F2-B / F2-C / F2-D, each of which will be scoped in its own
follow-up prompt. F2-A only enumerates what exists today, what
is missing, and what is the next high-level step.

Generic Wind remains at **Level 1 (Exploratory / Unvalidated)**
throughout F2-A and after F2-A. F2-A does not promote Generic Wind.

## 1. Current Generic Wind Inventory

Generic Wind is a project factory in `app/project_factories.py`
plus a project context in `app/ui/project_context.py`. F2-A
enumerates every artifact that exists today.

### 1.1 Factory — `create_default_wind_project`

**Location:** `app/project_factories.py:517-572`
**Function signature:**

```python
def create_default_wind_project(
    capacity_mw: float = 50.0,
    horizon_years: int = 25,
    construction_months: int = 18,
) -> ProjectInputs:
```

**Concretely populated inputs:**

| Field | Value | Notes |
|---|---|---|
| `info.name` | `"Generic Wind Farm"` | |
| `info.company` | `"WindCo"` | |
| `info.code` | `"WIND-001"` | |
| `info.country_iso` | `"DE"` | Germany |
| `info.financial_close` | `date(2030, 1, 1)` | |
| `info.construction_months` | `18` (configurable) | |
| `info.cod_date` | `date(2031, 7, 1)` | |
| `info.horizon_years` | `25` (configurable) | |
| `info.period_frequency` | `PeriodFrequency.SEMESTRIAL` | |
| `technical.capacity_mw` | `50.0` (configurable) | |
| `technical.yield_scenario` | `"P_50"` | |
| `technical.operating_hours_p50` | `3000.0` | round number |
| `technical.operating_hours_p90_10y` | `2700.0` | round number |
| `technical.pv_degradation` | `0.0` | round number |
| `technical.bess_enabled` | `False` | |
| `revenue.ppa_base_tariff` | `60.0` | EUR/MWh; **note**: this is `60.0` in the factory, but the Phase 34 doc cites `55.0`; this discrepancy is itself a known data point |
| `revenue.ppa_term_years` | `12` | |
| `revenue.ppa_index` | `0.02` | |
| `revenue.market_scenario` | `"Central"` | |
| `revenue.market_prices_curve` | `(65.0 + i * 1.2 for i in range(30))` | synthetic |
| `revenue.market_inflation` | `0.02` | |
| `revenue.balancing_cost_wind_eur_mwh` | `8.0` | |
| `revenue.co2_enabled` | `True` | note: factory has `True`; Phase 34 doc cites "no"; this is a discrepancy |
| `revenue.co2_price_eur` | `5.0` | |
| `financing.share_capital_keur` | `500.0` | |
| `financing.shl_amount_keur` | `6_000.0` | |
| `financing.shl_rate` | `0.08` | |
| `financing.gearing_ratio` | `0.75` | |
| `financing.senior_tenor_years` | `15` | |
| `financing.base_rate` | `0.03` | |
| `financing.margin_bps` | `250` | |
| `financing.floating_share` | `0.3` | |
| `financing.fixed_share` | `0.7` | |
| `financing.hedge_coverage` | `0.8` | |
| `financing.target_dscr` | `1.20` | |
| `financing.lockup_dscr` | `1.10` | |
| `financing.dsra_months` | `6` | |
| `financing.equity_irr_method` | `EquityIRRMethod.EQUITY_ONLY.value` | |
| `financing.debt_sizing_method` | `DebtSizingMethod.DSCR_SCULPT.value` | **live sculpting, no frozen fixture** |
| `tax.corporate_rate` | `0.25` | |
| `tax.loss_carryforward_years` | `5` | |
| `tax.loss_carryforward_cap` | `1.0` | |
| `tax.atad_ebitda_limit` | `0.30` | |
| `tax.atad_min_interest_keur` | `3000.0` | |
| `capex.epc_contract` (Wind Turbines) | `30_000.0` kEUR, `y0_share=0.4`, profile `(0.6,)` | |
| `capex.epc_other` (Civil Works) | `6_000.0` kEUR, `y0_share=0.3`, profile `(0.4, 0.3)` | |
| `capex.grid_connection` | `3_000.0` kEUR, `y0_share=0.5`, profile `(0.5,)` | |
| `capex.soft_costs` (Soft Costs) | `4_000.0` kEUR, `y0_share=1.0` | |
| `capex.idc_keur` | `800.0` | |
| `capex.bank_fees_keur` | `300.0` | |
| `capex` remaining 13 fields | all set to a zero-valued `CapexItem` (placeholder) | |
| `opex` items | 4 items: Technical Management (200), Insurance (150), Maintenance (120), Lease & Tax (80) | all `annual_inflation=0.02` |

**Total CAPEX (indicative, sum of named fields):** ~43,300 kEUR
(Turbines 30k + Civil 6k + Grid 3k + Soft 4k + IDC 0.8k + fees 0.3k
= ~44.1k; Phase 34 doc cites ~43,000 kEUR; the small delta is the
zero-valued placeholders, which are not summed in either case).
All numbers are **round**; the docstring explicitly says
"round numbers for tests/examples, not Excel calibration."

### 1.2 Project context — `_build_generic_wind_context`

**Location:** `app/ui/project_context.py:2335-2344`
**Resolves via `_CONTEXTS["generic_wind"]` (line 2362).**

**Concretely populated context fields:**

| Field | Value | Notes |
|---|---|---|
| `code` | `"GENERIC_WIND"` | |
| `technology` | `"Wind"` | |
| `opex_contingency_method` | `"percentage_of_opex"` | |
| `opex_contingency_pct` | `0.0` | |
| `parity_status` | `"ACCEPTED_CONVENTION"` | **note**: this string is a current state label, not a validation-pack label; F1's maturity ladder is the validation-pack label |
| `data_source` | `"Generic wind template - user-project starter defaults"` | |

**Context is built from `create_default_wind_project()`** via
`_build_context_from_project_inputs` (line 2342). The factory and
the context are the **only** Generic Wind artifacts in
`app/project_factories.py` and `app/ui/project_context.py`.

### 1.3 Existing templates, exports, audit surfaces

| Surface | Generic Wind status | Evidence |
|---|---|---|
| Project factory | PRESENT | `app/project_factories.py:517` |
| Project context | PRESENT | `app/ui/project_context.py:2335` |
| `_CONTEXTS` entry | PRESENT | `app/ui/project_context.py:2362` |
| Excel reference workbook | MISSING | no file matches `*wind*excel*`; only `tuho_excel_1.xlsm` and `excel_oborovo.xlsx` exist (per Phase 34 doc, not pinned to Generic Wind) |
| Excel parity extraction CSV | MISSING | only `phase7_tuho_senior_debt_sizing_extraction.csv` and `phase23q_oborovo_senior_debt_sizing_extraction.csv` exist |
| Golden dataset | MISSING | `tests/golden/fixtures/` contains only `tuho_golden.py` and `oborovo_golden.py` |
| Frozen senior debt schedule | MISSING | debt sizing is `DSCR_SCULPT` (live sculpting) per Phase 34 §4.2 |
| Validation pack directory (`docs/validation/generic_wind/`) | MISSING | `docs/validation/` exists but only has the validation-assets matrix docs; no project-specific pack directory |
| `KNOWN_LIMITATIONS.md` | MISSING | no `docs/validation/generic_wind/KNOWN_LIMITATIONS.md` |
| D1 Depreciation Audit sheet row for Generic Wind | PARTIAL | D1 sheet has a generic-project disclosure row but does **not** list Generic Wind by name; the row is generic, not per-project |
| Excel export Generic Solar/Wind fallback | PRESENT | `app/excel_export.py:413-417` shows a "screening only" fallback row for Generic projects; this is the **only** Generic Wind audit surface in the export |
| User-facing warning label | PRESENT | `main_web.py:191` shows "⚠️ Unvalidated · Derived path" for Generic projects |
| Pilot RC scope matrix entry | PRESENT | `docs/pilot_rc_scope_matrix.md` excludes Generic Wind explicitly |
| Phase 34 doc | PRESENT | `docs/phase34_generic_project_path_validation_boundary.md` |
| Phase 34 requirements matrix | PRESENT | `docs/phase34_generic_validation_requirements_matrix.md` |
| Phase 28 doc | LIKELY PRESENT | `docs/phase28_generic_project_path_validation.md` (referenced from Phase 34) |

### 1.4 Existing assumptions documented in codebase

The following Generic Wind assumptions are **documented in code**
(in `app/project_factories.py:517-572` and the Phase 34 doc
§4.2). They are **not** documented in a `KNOWN_LIMITATIONS.md` —
the limit-ation doc is MISSING.

- Wind yields: P50 3000 hours, P90 2700 hours (round numbers)
- PPA tariff: 60 EUR/MWh (factory value) / 55 EUR/MWh (Phase 34 doc) — **discrepancy**
- PPA term: 12 years
- PPA indexation: 2% / year
- Market price curve: synthetic (65 + 1.2 × i)
- Balancing cost: 8 EUR/MWh
- CO2 enabled: True (factory) / disabled (Phase 34 doc) — **discrepancy**
- CO2 price: 5 EUR/tCO2
- Senior debt: 15-year tenor, 3% base + 250 bps margin
- 70% fixed / 30% floating
- Target DSCR 1.20, Lockup DSCR 1.10
- SHL: 6,000 kEUR (factory) / 5,000 kEUR (Phase 34 doc) — **discrepancy**
- SHL rate: 8%
- Tax: 25% corporate, 5-year loss carryforward
- ATAD EBITDA limit: 30%
- ATAD min interest: 3,000 kEUR

**Three discrepancies** between factory and Phase 34 doc:
PPA tariff (60 vs 55), CO2 enabled (True vs False), SHL amount
(6,000 vs 5,000). F2-A only **inventories** these; F2-B/C/D must
resolve them before any parity comparison.

### 1.5 Existing tests

F2-A enumerates the Generic Wind test coverage. There is **no
dedicated `tests/test_phase_*generic_wind*.py` test pack**.

Generic Wind is **referenced** (not **dedicated**) in 18 test
files. These are tests that incidentally touch the generic_wind
key, the WIND-001 code, or the GENERIC_WIND context — they are
not parity tests, not validation tests, and not pack tests.

**Files with Generic Wind references (sample, sorted by file):**

| File | Reference count | Purpose of Generic Wind in this file |
|---|---|---|
| `tests/test_reconciliation_export.py` | 1 | reconciliation path passes through generic |
| `tests/test_project_factories.py` | 1+ | factory creation smoke test (asserts name="Generic Wind Farm", capacity=50.0, P50=3000.0) |
| `tests/test_phase17_from_scratch_runtime_path.py` | 1 | from-scratch runtime path |
| `tests/test_phase17_new_project_foundation.py` | 3 | new-project foundation |
| `tests/test_phase17_required_field_input_form.py` | 2 | input form smoke |
| `tests/test_phase17_user_project_e2e_runtime_export_validation.py` | 2 | E2E smoke (not parity) |
| `tests/test_phase18_live_browser_user_project_smoke.py` | 1 | live browser smoke |
| `tests/test_phase18_user_project_workbook_artifact_validation.py` | 1 | workbook artifact smoke |
| `tests/test_phase20a_saved_baseline_models.py` | 3 | saved baseline models |
| `tests/test_phase20d_inputs_primary_surface.py` | 1 | inputs UI surface |
| `tests/test_phase20f_active_scenario_runtime_binding.py` | 4 | active-scenario binding |
| `tests/test_phase21_opex_detail_line_item_grid.py` | 5 | OPEX line-item grid |
| `tests/test_phase24c1_frozen_vs_derived_warning.py` | 1 | frozen-vs-derived warning |
| `tests/test_phase29a_tuho_co2_revenue_deep_dive.py` | 2 | TUHO CO2 deep-dive (Generic Wind is incidental) |
| `tests/test_phase34_generic_project_path_validation_boundary.py` | 5 | **the closest test to a Generic Wind validation test** — but it is a validation-boundary test, not a parity test |
| `tests/test_phase51m1_projects_create_route_golden_characterization.py` | 3 | route golden characterization |
| `tests/test_phase53e2_compute_baseline_snapshot_regression_pin.py` | 8 | baseline snapshot regression pin |
| `tests/test_phase56a_ux_cleanup_help_project_new_project_characterization.py` | 2 | UX cleanup |
| `tests/test_phase56g_ux_cleanup_closeout_visual_review.py` | 1 | UX visual review |
| `tests/test_phase57a10c_capex_contingency_design.py` | 1 | CAPEX contingency design |
| `tests/test_phase57a10d_capex_vat_wht_depreciation_basis_design.py` | 1 | CAPEX VAT/WHT/depreciation basis |
| `tests/test_phase57a10e_capex_tax_metadata_persistence_design.py` | 1 | CAPEX tax metadata persistence |
| `tests/test_phase57a9d_capex_sub_lines_run_integration.py` | 1 | CAPEX sub-lines run integration |
| `tests/test_portfolio_waterfall.py` | 6 | portfolio waterfall |
| `tests/test_oborovo_debt_service.py` | 1 | Oborovo debt service (Generic Wind incidental) |

**Total: 18 test files reference Generic Wind.** None of these is
a dedicated parity or validation pack for Generic Wind. The
closest is `test_phase34_generic_project_path_validation_boundary.py`
(5 references), but it is a **boundary** test (asserting that the
generic path is unvalidated and the warning label is present), not
a parity test.

**Comparison:** TUHO appears in **310 test files**, Oborovo in
**243 test files**. Generic Wind appears in **18 test files**.
The disparity is large and is itself a gap.

### 1.6 Existing validation assets

| Asset | Generic Wind status |
|---|---|
| Excel reference workbook | MISSING |
| Parity extraction CSV | MISSING |
| Parity results JSON | MISSING |
| Golden dataset | MISSING |
| Test pack | MISSING (only incidental references) |
| `KNOWN_LIMITATIONS.md` | MISSING |
| Reviewer sign-off | MISSING |
| `excel_reference/README.md` | MISSING |
| `parity/README.md` | MISSING |
| `test_pack/README.md` | MISSING |
| `golden_dataset/inputs.json` | MISSING |
| `golden_dataset/expected_outputs.json` | MISSING |
| `golden_dataset/README.md` | MISSING |
| `reviewer_signoff/README.md` | MISSING |
| Per-project validation pack directory | MISSING |

## 2. Dependency Mapping

F2-A maps Generic Wind against the 12 dependency areas listed
in the F2-A brief. The status is **READY** / **PARTIAL** /
**MISSING** for each area, with evidence and a one-line rationale.

| # | Area | Status | Evidence | Rationale |
|---|---|---|---|---|
| 1 | CAPEX | PARTIAL | `app/project_factories.py:534-548` (4 named items + 2 IDC/fees) | 4 of 17 `CapexStructure` fields are populated with named items; 13 are zero-valued placeholders. No Excel reference. No parity. |
| 2 | Revenue | PARTIAL | `app/project_factories.py:555-559` | PPA + market + balancing are populated with round numbers; **discrepancy** between factory (60 EUR/MWh) and Phase 34 doc (55 EUR/MWh). No Excel reference. No parity. |
| 3 | Production | PARTIAL | `app/project_factories.py:551-554` (P50 3000h, P90 2700h, bess_enabled=False) | Hours populated; round numbers; no `yield_curve` or `production_shape` per period. No Excel reference. No parity. |
| 4 | OPEX | PARTIAL | `app/project_factories.py:549-552` (4 items, ~430 kEUR Y1) | 4 OPEX items (vs 12 for TUHO, 15 for Oborovo per Phase 20N discovery). Inflation 2%. No Excel reference. No parity. |
| 5 | Senior Debt | PARTIAL | `app/project_factories.py:560-565` (tenor 15y, target DSCR 1.20, gearing 0.75) | Debt sizing parameters set; **debt amount is not pinned** (`DSCR_SCULPT`, live sculpting). No frozen senior debt schedule. No Excel reference. |
| 6 | SHL | PARTIAL | `app/project_factories.py:560-561` (amount 6,000 kEUR, rate 8%) | SHL amount and rate populated; **discrepancy** between factory (6,000) and Phase 34 doc (5,000). No frozen SHL schedule. No Excel reference. |
| 7 | Tax | PARTIAL | `app/project_factories.py:570-572` (25%, 5y carryforward, ATAD limits) | Tax parameters set; no Excel reference. No parity. |
| 8 | Sponsor | MISSING | no `sponsor_params` or similar field in factory | Factory does not populate any sponsor-specific fields (no equity provider name, no sponsor covenant, no dividend policy). |
| 9 | Construction | PARTIAL | `info.construction_months = 18`, `info.financial_close = 2030-01-01`, `info.cod_date = 2031-07-01` | Construction period set; no construction-period cost detail. No Excel reference. |
| 10 | Depreciation | MISSING | `app/depreciation_flag_discipline.py:25` names Generic Wind as default-False; no Generic Wind-specific depreciation module | Depreciation runs in legacy mode; canonical engine not enabled. No Generic Wind shadow validation. D1 audit sheet shows `Generic_Project_Support: NO`. |
| 11 | Exports | PARTIAL | `app/excel_export.py:413-417` (Generic Solar/Wind fallback rows: "Screening-grade model — no Excel reference calibration"; "For internal scenario review only"; "Not a substitute for lender due diligence") | Export produces a Generic-Solar/Wind fallback "Calibration Note" section. No D1 sheet per-project row. No Generic Wind-specific sheet. |
| 12 | Audit sheets | PARTIAL | `main_web.py:191` shows "⚠️ Unvalidated · Derived path" for Generic projects; Phase 34 doc; pilot_rc_scope_matrix.md; `app/depreciation_audit_visibility.py` does **not** have a per-project row for Generic Wind | UI warning present; project-scope matrix present; depreciation audit sheet has a generic-project row but no Generic Wind-specific row. |

### 2.1 Summary of dependency mapping

- **READY: 0** of 12 areas
- **PARTIAL: 10** of 12 areas (CAPEX, Revenue, Production, OPEX, Senior Debt, SHL, Tax, Construction, Exports, Audit sheets)
- **MISSING: 2** of 12 areas (Sponsor, Depreciation)

Every PARTIAL area is "partial" for the same reason: inputs are
populated with **round numbers**, no **Excel reference** exists,
and no **parity** has been computed.

## 3. Reference Requirements Mapping (F1 Level 2 criteria)

F2-A maps Generic Wind against the F1 Reference (Level 2)
criteria. F1 §3.3 requires all of the following for Level 2:

1. Excel reference workbook is committed and pinned.
2. Phase 51F parity guardrails are green for the project.
3. Outputs are bit-for-bit identical (or within tolerance) to the
   Excel reference for the frozen input set.
4. `KNOWN_LIMITATIONS.md` is current.
5. A test pack exists; dedicated tests pass in isolation and in
   the full 57-arc stack.
6. The project is referenced by the closure-review-style audit
   posture (D1 sheet, D2 redo discipline, D3 redo shadow).
7. The project does **not** have a "Validated" sign-off from an
   external reviewer.

| # | F1 Reference criterion | Status | Evidence | Rationale |
|---|---|---|---|---|
| 1 | Excel reference workbook | NOT SATISFIED | no Generic Wind workbook in repo | Excel reference MISSING |
| 2 | Phase 51F parity green | NOT SATISFIED | `.github/workflows/parity_guardrails.yml` does not include Generic Wind in scope; only TUHO / Oborovo | Parity guardrails MISSING for Generic Wind |
| 3 | Outputs within tolerance | NOT SATISFIED | no parity computation possible | Depends on (1) and (2) |
| 4 | `KNOWN_LIMITATIONS.md` | NOT SATISFIED | no `docs/validation/generic_wind/KNOWN_LIMITATIONS.md` | KNOWN_LIMITATIONS MISSING |
| 5 | Dedicated test pack | NOT SATISFIED | 18 test files reference Generic Wind incidentally; no dedicated pack | Test pack MISSING |
| 6 | Closure-review-style audit posture | NOT SATISFIED | D1 sheet has no Generic Wind row; D2 redo discipline names Generic Wind but only as default-False; D3 redo shadow validation is for TUHO and Oborovo only | Audit posture MISSING for Generic Wind |
| 7 | No external sign-off | SATISFIED (trivially) | no external sign-off exists | Sign-off is N/A at Level 1; this is not a gap |

**F1 Reference criteria summary:**

- **Satisfied:** 1 of 7 (criterion 7, trivially)
- **Partially Satisfied:** 0 of 7
- **Not Satisfied:** 6 of 7

**Generic Wind is 6/7 NOT SATISFIED for F1 Reference.** Even
where inputs are populated, the absence of an Excel reference
and a parity comparison means no F1 Level 2 criterion is met.

## 4. Missing Evidence Inventory

The following is the explicit list of evidence missing before
Generic Wind can begin a controlled journey toward Reference
status. Each item is concrete and checkable.

### 4.1 Missing Excel reference

- `docs/validation/generic_wind/excel_reference/README.md` —
  describes which workbook, which version, source
- `docs/validation/generic_wind/excel_reference/<workbook>.xlsx` —
  the pinned reference workbook itself

### 4.2 Missing parity pack

- `docs/validation/generic_wind/parity/README.md` — parity
  methodology + tolerance
- `docs/validation/generic_wind/parity/extraction.csv` —
  extracted reference values
- `docs/validation/generic_wind/parity/results.json` — last-run
  parity results

### 4.3 Missing golden dataset (Level 3 only — not required for Reference)

- `docs/validation/generic_wind/golden_dataset/inputs.json`
- `docs/validation/generic_wind/golden_dataset/expected_outputs.json`
- `docs/validation/generic_wind/golden_dataset/README.md`

F2-A lists these for completeness, but the golden dataset is
**only required for Level 3 (Validated)**, not Level 2
(Reference). F2-B / F2-C / F2-D should not produce the golden
dataset as part of the Reference migration.

### 4.4 Missing test pack

- `docs/validation/generic_wind/test_pack/README.md` — test pack
  scope and threshold
- `docs/validation/generic_wind/test_pack/test_generic_wind_*.py`
  — at minimum: parity tests, parameter-validation tests,
  audit-surface tests, export-shape tests, frozen-vs-derived tests

### 4.5 Missing reviewer material (Level 3 only)

- `docs/validation/generic_wind/reviewer_signoff/README.md`
- `docs/validation/generic_wind/reviewer_signoff/<reviewer>_<date>.md`

Not required for Reference.

### 4.6 Missing audit documentation

- D1 audit sheet per-project row for Generic Wind (currently
  only a generic-project row exists)
- D2 redo discipline per-project row (currently Generic Wind is
  named only in the module docstring as default-False)
- D3 redo shadow validation for Generic Wind (currently only
  TUHO and Oborovo)

### 4.7 Missing limitations documentation

- `docs/validation/generic_wind/KNOWN_LIMITATIONS.md` — every
  Generic-Wind-specific limitation enumerated, with risk rating
  and mitigation

### 4.8 Unresolved data discrepancies

These three discrepancies between the factory and the Phase 34
doc must be resolved before any parity comparison:

| Field | Factory value | Phase 34 value | Resolution owner |
|---|---|---|---|
| PPA tariff | `60.0` EUR/MWh | `55.0` EUR/MWh | F2-B or earlier |
| CO2 enabled | `True` | `False` (Phase 34 says "no") | F2-B or earlier |
| SHL amount | `6_000` kEUR | `5_000` kEUR | F2-B or earlier |

Note: the Phase 34 doc is older than the current factory code.
The current factory is the source of truth. F2-B should update
the Phase 34 doc to match the factory, **or** justify any
deliberate divergence.

### 4.9 Excel reference acquisition

The most critical missing evidence is the **Excel reference
workbook** itself. Options for acquiring it (to be evaluated in
F2-B):

- Acquire a representative Wind Excel model (industry template,
  public dataset, or partner-provided workbook).
- Build a synthetic reference workbook from the FincoGPT model
  itself, with all formulas documented.

The Phase 34 §5.3 already lists this as a blocking requirement.

## 5. Validation Risks

### 5.1 Highest parity risks

1. **No Excel reference** (the dominant risk). Without it, no
   parity computation is possible. All other parity risks are
   downstream of this one.
2. **Live sculpting vs frozen path.** Generic Wind uses
   `DSCR_SCULPT` (live sculpting). The Phase 34 doc requires
   "Live sculpting validation: confirm live sculpt = frozen if
   same inputs." This requires either a frozen-path reference
   or a separate live-sculpt-vs-frozen test pack. Neither exists
   today.
3. **Synthetic market price curve.** `market_prices_curve = (65.0
   + i * 1.2 for i in range(30))` is a synthetic linear ramp; a
   real Excel reference would have a market-shape curve. The
   delta between the synthetic curve and a real curve is
   unbounded and could dominate revenue parity.
4. **CO2 treatment.** Factory has `co2_enabled=True, co2_price=5.0`
   but Phase 34 says "CO2 disabled" — the discrepancy itself is
   a risk. If CO2 is enabled for Generic Wind, the CO2 revenue
   line contributes to revenue parity, and the canonical engine
   shadow validation is not yet Generic-Wind-aware.
5. **Discrepancies not yet resolved.** Three documented
   discrepancies (PPA, CO2, SHL) are unresolved.

### 5.2 Highest modeling risks

1. **Sponsor modeling MISSING.** No sponsor-specific fields in
   the factory. A real wind project has a sponsor / equity
   provider with covenants. Generic Wind has no sponsor
   modeling. F2-B must decide whether to add it.
2. **Depreciation MISSING.** No Generic-Wind-specific
   depreciation. The D1-D3 arc covers TUHO and Oborovo;
   Generic Wind is not shadow-validated.
3. **OPEX coverage.** 4 OPEX items vs 12-15 for TUHO/Oborovo.
   A real wind project has more OPEX line items (technical
   management, insurance, maintenance, lease & tax, plus
   potentially grid fees, balancing, environment, monitoring,
   etc.). The 4-item coverage is **a deliberate simplification
   for "tests/examples"** (per the docstring), not a model
   deficiency. F2-B must decide whether to expand OPEX coverage.
4. **CAPEX coverage.** 4 named CAPEX items + IDC + fees = 6 of
   17 fields. A real wind project has more CAPEX line items
   (turbines, civil, grid, soft, plus BOP, contingency, etc.).
   Same caveat as OPEX.
5. **No construction-period cost detail.** Construction is set
   as a duration (18 months) but no construction-period cost
   detail (e.g. per-period spending) is parameterized. F2-B
   must decide.

### 5.3 Highest governance risks

1. **Generic Wind inherits TUHO/Oborovo parity guardrails by
   accident.** The Phase 51F parity workflow does not include
   Generic Wind. If a Generic Wind run is added to a CI lane
   by accident, it could pollute the parity baseline. F2-B
   should make this explicit in the parity workflow.
2. **No `KNOWN_LIMITATIONS.md` means no documented risk
   register.** Reviewers and future maintainers have no
   authoritative place to look for Generic Wind limitations.
3. **No external review process defined for Generic Wind.**
   F1 §10.2 requires external reviewer sign-off for Level 3,
   but there is no defined process for Generic Wind specifically.
   F2-B should not start the external review process; that
   belongs to a later F-phase.
4. **Pilot RC scope matrix explicitly excludes Generic Wind.**
   This is the correct posture today, but it is a manual
   exclusion; a CI guard could be added to prevent Generic Wind
   from being included in the pilot RC scope by accident.

## 6. Generic Wind Roadmap (high-level only)

F2-A does **not** design the Generic Wind validation pack. F2-A
recommends the **next three high-level phases** (F2-B, F2-C,
F2-D) and their scope. Each phase will be designed in its own
follow-up prompt.

### 6.1 F2-B — Generic Wind input resolution + Excel reference

**Goal:** resolve the three data discrepancies (PPA, CO2, SHL)
and acquire or build the Excel reference workbook.

**Scope (high-level):**
- Update the Phase 34 doc to match the current factory (or
  justify any deliberate divergence).
- Decide on the Excel reference source (acquire, build, or
  synthesize).
- Commit `docs/validation/generic_wind/excel_reference/`
  directory.

**Does NOT include:** parity computation, test pack, audit
updates. Those are F2-C and F2-D.

### 6.2 F2-C — Generic Wind parity comparison + audit posture

**Goal:** compute parity between Generic Wind and the Excel
reference, and add the audit posture (D1 sheet row, D2 redo
discipline, D3 redo shadow).

**Scope (high-level):**
- Compute parity for the 10 F1 Reference criteria that depend
  on the Excel reference.
- Add a D1 audit-sheet per-project row for Generic Wind.
- Extend the D2 redo discipline summary to include Generic Wind.
- (Optional) Run a D3 redo shadow validation for Generic Wind.
- Update `.github/workflows/parity_guardrails.yml` to include
  Generic Wind in scope.

**Does NOT include:** dedicated test pack, KNOWN_LIMITATIONS.md,
frozen-schedule validation. Those are F2-D.

### 6.3 F2-D — Generic Wind test pack + KNOWN_LIMITATIONS

**Goal:** create the Generic Wind dedicated test pack and the
KNOWN_LIMITATIONS.md.

**Scope (high-level):**
- Create `docs/validation/generic_wind/test_pack/` with parity
  tests, parameter-validation tests, audit-surface tests,
  export-shape tests, and a frozen-vs-derived test.
- Create `docs/validation/generic_wind/KNOWN_LIMITATIONS.md`
  with every Generic-Wind-specific limitation, risk rating,
  and mitigation.
- Add a CI guard that prevents Generic Wind from being added
  to the pilot RC scope by accident.

**Does NOT include:** promotion to Level 2. Promotion happens
in a separate F-phase after F2-D is merged and reviewed.

### 6.4 Post-F2-D

After F2-D is merged and reviewed, a separate F-phase
(likely F2-E) will:

- Run the F1 §10.1 promotion gate.
- Promote Generic Wind from Level 1 to Level 2 (Reference).
- Update the D1 audit-sheet row from
  `EXPLORATORY / UNVALIDATED` to `REFERENCE`.
- Update the `model_scope_and_limitations` doc column.

F2-A does **not** design F2-E.

## 7. Generic Wind Readiness Score

F2-A provides a hybrid readiness score (category + numeric 0-100)
for three dimensions.

### 7.1 Technical Readiness

| Component | Status | Weight | Score |
|---|---|---|---|
| Factory inputs populated | YES | 30% | 30 |
| Excel reference | NO | 30% | 0 |
| Parity computed | NO | 20% | 0 |
| Test pack | NO | 10% | 0 |
| Audit posture (D1/D2/D3) | NO | 10% | 0 |
| **Total** | | **100%** | **30/100** |

**Category: NOT READY** (30/100)

**Rationale:** The factory inputs are populated with round
numbers, which is necessary but not sufficient. The absence of
an Excel reference and a parity computation is the dominant gap.
Without them, the technical readiness is fundamentally not at
Reference level.

### 7.2 Validation Readiness

| Component | Status | Weight | Score |
|---|---|---|---|
| Validation pack directory | NO | 25% | 0 |
| `KNOWN_LIMITATIONS.md` | NO | 25% | 0 |
| Parity pack (extraction, results) | NO | 20% | 0 |
| Dedicated test pack | NO | 15% | 0 |
| Phase 51F parity green | NO | 10% | 0 |
| Per-project D1/D2/D3 audit posture | NO | 5% | 0 |
| **Total** | | **100%** | **0/100** |

**Category: NOT READY** (0/100)

**Rationale:** The validation pack directory does not exist;
none of the F1 §3.3 criteria are met. This is the lowest
readiness of the three dimensions. The Pilot RC scope matrix
and the Phase 34 doc provide **boundary** evidence (the project
is correctly excluded from the validated scope), but boundary
evidence is not validation evidence.

### 7.3 Governance Readiness

| Component | Status | Weight | Score |
|---|---|---|---|
| Pilot RC scope matrix exclusion | YES | 25% | 25 |
| User-facing warning label | YES | 20% | 20 |
| Phase 34 doc | YES | 20% | 20 |
| Phase 34 requirements matrix | YES | 15% | 15 |
| D1 sheet generic-project row | YES (partial) | 10% | 5 |
| D2 redo discipline naming | YES (partial) | 5% | 2 |
| D3 redo shadow validation | NO | 5% | 0 |
| **Total** | | **100%** | **87/100** |

**Category: PARTIAL** (87/100)

**Rationale:** The governance boundary is **strong** for an
exploratory project. The Pilot RC scope matrix, the user-facing
warning label, the Phase 34 doc, and the Phase 34 requirements
matrix are all in place. The remaining gaps (per-project D1/D2/D3
rows, Generic-Wind-specific shadow validation) are documentation
gaps, not governance gaps. The 87/100 reflects that the
governance posture is correct (Generic Wind is correctly
excluded from the validated scope) but the documentation could
be more explicit.

### 7.4 Combined readiness

| Dimension | Category | Score |
|---|---|---|
| Technical | NOT READY | 30/100 |
| Validation | NOT READY | 0/100 |
| Governance | PARTIAL | 87/100 |
| **Average** | **NOT READY** | **39/100** |

**Overall category: NOT READY** for a controlled journey toward
Reference status. The governance posture is correct (Generic
Wind is correctly held at Level 1), but the technical and
validation evidence is missing.

## 8. Recommendation

**Recommendation: A — Not ready to begin Reference journey.**

**Rationale:** Generic Wind is missing 6 of 7 F1 Reference
criteria. The dominant gaps are:

1. **No Excel reference workbook** (blocking).
2. **No parity computation** (depends on (1)).
3. **No `KNOWN_LIMITATIONS.md`** (independent gap).
4. **No dedicated test pack** (independent gap).
5. **No per-project D1/D2/D3 audit posture** (documentation gap).
6. **Three unresolved data discrepancies** (PPA, CO2, SHL).

The technical readiness is 30/100 (NOT READY). The validation
readiness is 0/100 (NOT READY). The governance readiness is
87/100 (PARTIAL), which is **good for an exploratory project**
but is not sufficient on its own.

Generic Wind should remain at **Level 1 (Exploratory /
Unvalidated)**. The F2-B / F2-C / F2-D roadmap (§6) is the
right next step: resolve the data discrepancies, acquire the
Excel reference, compute parity, and create the test pack +
KNOWN_LIMITATIONS.md. After F2-D, a separate F-phase (likely
F2-E) may evaluate whether Generic Wind can be promoted to
Level 2.

**Option B (limited preparation work) and Option C (controlled
Reference program) are not appropriate at this time.** Option B
would imply that some preparation is already in place; it is
not. Option C would imply a Reference program can be designed
on top of the current evidence; it cannot, because the Excel
reference is missing.

## 9. Hard no-go list (F2-A)

- no code changes
- no runtime changes
- no UI implementation
- no schema changes
- no persistence changes
- no formula changes
- no parity changes
- no feature flags
- no validation status changes
- no Generic Wind promotion
- no Generic Solar work
- no implementation roadmap beyond high-level inventory
- no extension of the D1 / D2 redo / D3 redo arc to cover
  Generic Wind

## 10. Forbidden paths (F2-A)

F2-A does **not** modify:

- `app/**`
- `domain/**`
- `static/**`
- `tests/**`
- `main_web.py`
- `main_api.py`

F2-A only adds:

- `docs/phase_f2a_generic_wind_reference_inventory.md` (this file)
- `reports/phase_f2a_generic_wind_reference_inventory.json`

## 11. Stop-after-report contract

F2-A is:

- A docs-only, design-only inventory.
- A factual inventory + gap analysis only.
- No implementation, no runtime change, no flag enablement,
  no F2-B / F2-C / F2-D / F2-E start.
- No new tests, no new code, no new persistence, no new
  schema, no new export surface, no new UI.

Branch: `phase-f2a-generic-wind-reference-inventory`
PR: DRAFT only, do not mark ready, do not merge.
rc1 SHA: `b425a0708719eaa5e1d922b1008e5609758e0ad4` — untouched.
Generic Wind status: **Level 1 (Exploratory / Unvalidated)**
— unchanged.

## 12. Appendix — top gaps (ranked by blocking-ness)

1. **Excel reference workbook** (blocks all parity).
2. **Parity computation** (blocks Phase 51F integration).
3. **Three data discrepancies** (PPA, CO2, SHL).
4. **`KNOWN_LIMITATIONS.md`** (blocks F1 §3.3 criterion 4).
5. **Dedicated test pack** (blocks F1 §3.3 criterion 5).
6. **Per-project D1/D2/D3 audit posture** (blocks F1 §3.3
   criterion 6).
7. **Sponsor modeling** (F2-B to decide; not a Reference
   criterion per se, but a modeling gap).
8. **Depreciation handling for Generic Wind** (no shadow
   validation; F2-B to decide whether to extend the
   D1-D3 arc).

## 13. Appendix — top risks (ranked by severity)

1. **No Excel reference** (dominant; blocks all parity).
2. **Live sculpting without a frozen-path validation** (the
   Phase 34 doc requires a live-sculpt-vs-frozen test; not
   present).
3. **Synthetic market price curve** (unbounded revenue-parity
   delta).
4. **CO2 treatment discrepancy** (factory vs Phase 34 doc).
5. **Generic Wind inherits TUHO/Oborovo parity guardrails
   by accident** (governance / CI risk).
6. **No `KNOWN_LIMITATIONS.md`** (no authoritative risk
   register for reviewers).
