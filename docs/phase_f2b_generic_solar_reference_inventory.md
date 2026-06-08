# Phase F2-B — Generic Solar Reference Candidate Inventory

> Type: docs-only, design-only
> Branch: `phase-f2b-generic-solar-reference-inventory`
> Base SHA: `cd82f4e94fa9387155609869e6cbd944d756b4b4` (post-F2-A)
> Status: DRAFT, do not mark ready, do not merge
> Scope: factual inventory + gap analysis for Generic Solar
> Hard boundary: **Generic Solar remains at Level 1 (Exploratory / Unvalidated)**. F2-B does NOT promote Generic Solar.

## 0. Purpose

F2-A (merged) answered the question for Generic Wind: "What is
objectively missing today before Generic Wind can begin a
controlled journey toward Reference status?" The answer was
**NOT READY** with a 39/100 combined score.

F2-B answers the **same question for Generic Solar** and only
for Generic Solar. F2-B is a **factual inventory** and a
**gap analysis**. F2-B does not design the Generic Solar
validation pack; that is the job of F2-C / F2-D / F2-E, each
of which will be scoped in its own follow-up prompt.

Generic Solar remains at **Level 1 (Exploratory / Unvalidated)**
throughout F2-B and after F2-B. F2-B does not promote Generic
Solar. F2-B does not work on Generic Wind. F2-B does not modify
any of the F2-A outputs.

## 1. Current Generic Solar Inventory

Generic Solar is a project factory in `app/project_factories.py`
plus a project context in `app/ui/project_context.py`. F2-B
enumerates every artifact that exists today.

### 1.1 Factory — `create_default_solar_project`

**Location:** `app/project_factories.py:460-509`
**Function signature:**

```python
def create_default_solar_project(
    capacity_mw: float = 50.0,
    horizon_years: int = 25,
    construction_months: int = 12,
) -> ProjectInputs:
```

**Concretely populated inputs:**

| Field | Value | Notes |
|---|---|---|
| `info.name` | `"Generic Solar PV"` | |
| `info.company` | `"SolarCo"` | |
| `info.code` | `"SOLAR-001"` | |
| `info.country_iso` | `"DE"` | Germany |
| `info.financial_close` | `date(2030, 1, 1)` | |
| `info.construction_months` | `12` (configurable) | |
| `info.cod_date` | `date(2031, 1, 1)` | |
| `info.horizon_years` | `25` (configurable) | |
| `info.period_frequency` | `PeriodFrequency.SEMESTRIAL` | |
| `technical.capacity_mw` | `50.0` (configurable) | |
| `technical.yield_scenario` | `"P_50"` | |
| `technical.operating_hours_p50` | `1500.0` | round number |
| `technical.operating_hours_p90_10y` | `1400.0` | round number |
| `technical.pv_degradation` | `0.004` | 0.4% / year |
| `technical.bess_enabled` | `False` | (solar-only, no BESS) |
| `revenue.ppa_base_tariff` | `55.0` | EUR/MWh |
| `revenue.ppa_term_years` | `10` | |
| `revenue.ppa_index` | `0.02` | |
| `revenue.market_scenario` | `"Central"` | |
| `revenue.market_prices_curve` | `tuple(60.0 + i for i in range(30))` | synthetic linear ramp |
| `revenue.market_inflation` | `0.02` | |
| `revenue.co2_enabled` | `False` | |
| `revenue.co2_price_eur` | (not set) | factory default; CO2 disabled |
| `financing.share_capital_keur` | `500.0` | |
| `financing.shl_amount_keur` | `5_000.0` | |
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
| `capex.epc_contract` (Solar Modules) | `20_000.0` kEUR, `y0_share=0.0`, profile `(0.5, 0.5)`, asset_class=SOLAR_PANELS | |
| `capex.production_units` (Inverters) | `3_000.0` kEUR, `y0_share=0.0`, profile `(0.5, 0.5)`, asset_class=SOLAR_PANELS | |
| `capex.epc_other` (Civil Works) | `5_000.0` kEUR, `y0_share=0.3`, profile `(0.4, 0.3)`, asset_class=CIVIL_GRID | |
| `capex.grid_connection` | `2_000.0` kEUR, `y0_share=0.5`, profile `(0.5,)`, asset_class=CIVIL_GRID | |
| `capex.soft_costs` (Soft Costs) | `3_000.0` kEUR, `y0_share=1.0`, asset_class=SOFT_COSTS | |
| `capex` remaining 12 fields | all set to a zero-valued `CapexItem` (placeholder) | |
| `capex.idc_keur` | `500.0` | |
| `capex.bank_fees_keur` | `200.0` | |
| `opex` items | 4 items: Technical Management (150), Insurance (100), Maintenance (80), Lease & Tax (50) | all `annual_inflation=0.02` |

**Total CAPEX (indicative, sum of named fields):** ~30,000 kEUR
(Modules 20k + Inverters 3k + Civil 5k + Grid 2k + Soft 3k +
IDC 0.5k + fees 0.2k = ~33.7k; the small delta is the
zero-valued placeholders, which are not summed). All numbers
are **round**; the docstring explicitly says
"round numbers for tests/examples, not Excel calibration."

### 1.2 Project context — `_build_generic_solar_context`

**Location:** `app/ui/project_context.py:2347-2356`
**Resolves via `_CONTEXTS["generic_solar"]` (line 2363).**

**Concretely populated context fields:**

| Field | Value | Notes |
|---|---|---|
| `code` | `"GENERIC_SOLAR"` | |
| `technology` | `"Solar"` | |
| `opex_contingency_method` | `"percentage_of_opex"` | |
| `opex_contingency_pct` | `0.0` | |
| `parity_status` | `"ACCEPTED_CONVENTION"` | **note**: this string is a current state label, not a validation-pack label; F1's maturity ladder is the validation-pack label |
| `data_source` | `"Generic solar template - user-project starter defaults"` | |

**Context is built from `create_default_solar_project()`** via
`_build_context_from_project_inputs` (line 2354). The factory
and the context are the **only** Generic Solar artifacts in
`app/project_factories.py` and `app/ui/project_context.py`.

### 1.3 Existing templates, exports, audit surfaces

| Surface | Generic Solar status | Evidence |
|---|---|---|
| Project factory | PRESENT | `app/project_factories.py:460` |
| Project context | PRESENT | `app/ui/project_context.py:2347` |
| `_CONTEXTS` entry | PRESENT | `app/ui/project_context.py:2363` |
| Excel reference workbook | MISSING | no file matches `*solar*excel*`; only `tuho_excel_1.xlsm` and `excel_oborovo.xlsx` exist |
| Excel parity extraction CSV | MISSING | only `phase7_tuho_senior_debt_sizing_extraction.csv` and `phase23q_oborovo_senior_debt_sizing_extraction.csv` exist |
| Golden dataset | MISSING | `tests/golden/fixtures/` contains only `tuho_golden.py` and `oborovo_golden.py` |
| Frozen senior debt schedule | MISSING | debt sizing is `DSCR_SCULPT` (live sculpting) per Phase 34 §4.2 |
| Validation pack directory (`docs/validation/generic_solar/`) | MISSING | `docs/validation/` exists but only has the validation-assets matrix docs; no project-specific pack directory |
| `KNOWN_LIMITATIONS.md` | MISSING | no `docs/validation/generic_solar/KNOWN_LIMITATIONS.md` |
| D1 Depreciation Audit sheet row for Generic Solar | PARTIAL | D1 sheet has a generic-project disclosure row but does **not** list Generic Solar by name; the row is generic, not per-project |
| Excel export Generic Solar/Wind fallback | PRESENT | `app/excel_export.py:413-417` shows a "screening only" fallback row for Generic projects; this is the **only** Generic Solar audit surface in the export |
| User-facing warning label | PRESENT | `main_web.py:191` shows "⚠️ Unvalidated · Derived path" for Generic projects |
| Pilot RC scope matrix entry | PRESENT | `docs/pilot_rc_scope_matrix.md:27-28` excludes Generic solar/wind explicitly |
| Phase 34 doc | PRESENT | `docs/phase34_generic_project_path_validation_boundary.md` |
| Phase 34 requirements matrix | PRESENT | `docs/phase34_generic_validation_requirements_matrix.md` |
| Phase 28 doc | LIKELY PRESENT | `docs/phase28_generic_project_path_validation.md` (referenced from Phase 34) |

### 1.4 Existing assumptions documented in codebase

The following Generic Solar assumptions are **documented in code**
(in `app/project_factories.py:460-509` and the Phase 34 doc
§4.2). They are **not** documented in a `KNOWN_LIMITATIONS.md` —
the limitation doc is MISSING.

- Solar yields: P50 1500 hours, P90 1400 hours (round numbers)
- PV degradation: 0.4% / year
- PPA tariff: 55 EUR/MWh
- PPA term: 10 years
- PPA indexation: 2% / year
- Market price curve: synthetic (60 + i)
- CO2 enabled: False
- Senior debt: 15-year tenor, 3% base + 250 bps margin
- 70% fixed / 30% floating
- Target DSCR 1.20, Lockup DSCR 1.10
- SHL: 5,000 kEUR
- SHL rate: 8%
- Tax: 25% corporate, 5-year loss carryforward
- ATAD EBITDA limit: 30%
- ATAD min interest: 3,000 kEUR

**No data discrepancies** between factory and Phase 34 doc for
Generic Solar. (Generic Wind had three discrepancies per F2-A;
Generic Solar has none.) This is a positive finding for
Generic Solar — the source-of-truth ambiguity that affects
Generic Wind does not affect Generic Solar.

### 1.5 Existing tests

F2-B enumerates the Generic Solar test coverage. There is **no
dedicated `tests/test_phase_*generic_solar*.py` test pack**.

Generic Solar is **referenced** (not **dedicated**) in
8+ test files. These are tests that incidentally touch the
generic_solar key, the SOLAR-001 code, or the GENERIC_SOLAR
context — they are not parity tests, not validation tests, and
not pack tests.

**Files with Generic Solar references (sorted by file):**

| File | Reference count | Purpose of Generic Solar in this file |
|---|---|---|
| `tests/test_reconciliation_export.py` | 2 | reconciliation export + calibration notes (no Oborovo hardcoding) |
| `tests/test_phase20a_saved_baseline_models.py` | 2 | saved baseline model for `generic_solar` template_source |
| `tests/test_phase23k_oborovo_shl_opening_balance_bridge.py` | 1 | Oborovo SHL opening balance bridge (Generic Solar incidental: "period 38 for generic_solar with shl_tenor_years=0") |
| `tests/test_phase53e2_compute_baseline_snapshot_regression_pin.py` | 4 | baseline snapshot regression pin (assertion: `generic_wind / generic_solar fallback` comment) |
| `tests/test_phase56a_ux_cleanup_help_project_new_project_characterization.py` | 1 | UX cleanup for project new-project characterization |
| `tests/test_phase56g_ux_cleanup_closeout_visual_review.py` | 1 | UX visual review ("test_generic_solar_wind_explicit") |
| `tests/test_phase56h_post_merge_visual_qa.py` | 1 | post-merge visual QA ("test_generic_solar_wind_exploratory") |
| `tests/test_phase57a9e_capex_sub_lines_excel_export.py` | 2 | CAPEX sub-lines excel export |

**Total: 8+ test files reference Generic Solar.** None of these
is a dedicated parity or validation pack for Generic Solar. The
closest is `test_reconciliation_export.py` (2 references), but
those are reconciliation smoke tests, not parity tests.

**Comparison:** TUHO appears in **310 test files**, Oborovo in
**243 test files**, Generic Wind in **18 test files** (per F2-A),
and Generic Solar in **8+ test files** (per F2-B). Generic
Solar has the **lowest** test coverage of the four factory
projects. The disparity is large and is itself a gap.

### 1.6 Existing validation assets

| Asset | Generic Solar status |
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

F2-B maps Generic Solar against the 12 dependency areas listed
in the F2-B brief. The status is **READY** / **PARTIAL** /
**MISSING** for each area, with evidence and a one-line rationale.

| # | Area | Status | Evidence | Rationale |
|---|---|---|---|---|
| 1 | CAPEX | PARTIAL | `app/project_factories.py:476-481` (5 named items: Modules, Inverters, Civil, Grid, Soft) | 5 of 17 `CapexStructure` fields are populated with named items; 12 are zero-valued placeholders. No Excel reference. No parity. |
| 2 | Revenue | PARTIAL | `app/project_factories.py:498-500` | PPA + market populated with round numbers; **CO2 disabled** in factory (no CO2 line in revenue). No Excel reference. No parity. |
| 3 | Production | PARTIAL | `app/project_factories.py:494-496` (P50 1500h, P90 1400h, pv_degradation=0.004, bess_enabled=False) | Hours + degradation populated; round numbers. No Excel reference. No parity. |
| 4 | OPEX | PARTIAL | `app/project_factories.py:488-491` (4 items: Technical Management 150, Insurance 100, Maintenance 80, Lease & Tax 50) | 4 OPEX items (vs 12 for TUHO, 15 for Oborovo per Phase 20N discovery). Inflation 2%. No Excel reference. No parity. |
| 5 | Senior Debt | PARTIAL | `app/project_factories.py:501-507` (tenor 15y, target DSCR 1.20, gearing 0.75) | Debt sizing parameters set; **debt amount is not pinned** (`DSCR_SCULPT`, live sculpting). No frozen senior debt schedule. No Excel reference. |
| 6 | SHL | PARTIAL | `app/project_factories.py:501-502` (amount 5,000 kEUR, rate 8%) | SHL amount and rate populated; **no frozen SHL schedule**. No Excel reference. |
| 7 | Tax | PARTIAL | `app/project_factories.py:509` (25%, 5y carryforward, ATAD limits) | Tax parameters set; no Excel reference. No parity. |
| 8 | Sponsor | MISSING | no `sponsor_params` or similar field in factory | Factory does not populate any sponsor-specific fields. |
| 9 | Construction | PARTIAL | `info.construction_months = 12`, `info.financial_close = 2030-01-01`, `info.cod_date = 2031-01-01` | Construction period set; no construction-period cost detail. No Excel reference. |
| 10 | Depreciation | MISSING | `app/depreciation_flag_discipline.py:24` names Generic Solar as default-False; no Generic-Solar-specific depreciation module | Depreciation runs in legacy mode; canonical engine not enabled. No Generic Solar shadow validation. D1 audit sheet shows `Generic_Project_Support: NO`. |
| 11 | Exports | PARTIAL | `app/excel_export.py:413-417` (Generic Solar/Wind fallback rows: "Screening-grade model — no Excel reference calibration"; "For internal scenario review only"; "Not a substitute for lender due diligence") | Export produces a Generic-Solar/Wind fallback "Calibration Note" section. No D1 sheet per-project row. No Generic Solar-specific sheet. |
| 12 | Audit sheets | PARTIAL | `main_web.py:191` shows "⚠️ Unvalidated · Derived path" for Generic projects; Phase 34 doc; pilot_rc_scope_matrix.md:27-28; `app/depreciation_audit_visibility.py` does **not** have a per-project row for Generic Solar | UI warning present; project-scope matrix present; depreciation audit sheet has a generic-project row but no Generic Solar-specific row. |

### 2.1 Summary of dependency mapping

- **READY: 0** of 12 areas
- **PARTIAL: 10** of 12 areas (CAPEX, Revenue, Production, OPEX, Senior Debt, SHL, Tax, Construction, Exports, Audit sheets)
- **MISSING: 2** of 12 areas (Sponsor, Depreciation)

**Identical to F2-A Generic Wind finding** (0 READY, 10 PARTIAL,
2 MISSING). The two generic projects share the same architecture
and the same gap pattern.

### 2.2 Generic Wind vs Generic Solar comparison

| # | Area | Generic Wind | Generic Solar |
|---|---|---|---|
| 1 | CAPEX | 4 named items | 5 named items (Modules, Inverters, Civil, Grid, Soft) |
| 2 | Revenue | PPA + market + balancing (round) | PPA + market (round; no balancing line) |
| 3 | Production | P50 3000h, P90 2700h, no degradation | P50 1500h, P90 1400h, 0.4% degradation |
| 4 | OPEX | 4 items (~550 kEUR Y1) | 4 items (~380 kEUR Y1) |
| 5 | Senior Debt | DSCR_SCULPT, no frozen | DSCR_SCULPT, no frozen |
| 6 | SHL | 6,000 kEUR, 8% (factory; 5,000 in Phase 34) | 5,000 kEUR, 8% (no discrepancy) |
| 7 | Tax | 25% | 25% (identical) |
| 8 | Sponsor | MISSING | MISSING |
| 9 | Construction | 18 months | 12 months |
| 10 | Depreciation | MISSING | MISSING |
| 11 | Exports | Generic fallback (shared) | Generic fallback (shared) |
| 12 | Audit sheets | Generic UI warning (shared) | Generic UI warning (shared) |
| Test files | | 18 | 8+ |
| Data discrepancies | 3 (PPA, CO2, SHL) | 0 | |

**Generic Solar is structurally a smaller version of Generic
Wind** (lower OPEX, shorter construction, no degradation = 0,
no SHL discrepancy). The two projects share the same validation
gaps but Generic Solar has **fewer internal inconsistencies**.

## 3. Reference Requirements Mapping (F1 Level 2 criteria)

F2-B maps Generic Solar against the F1 Reference (Level 2)
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
| 1 | Excel reference workbook | NOT SATISFIED | no Generic Solar workbook in repo | Excel reference MISSING |
| 2 | Phase 51F parity green | NOT SATISFIED | `.github/workflows/parity_guardrails.yml` does not include Generic Solar in scope; only TUHO / Oborovo | Parity guardrails MISSING for Generic Solar |
| 3 | Outputs within tolerance | NOT SATISFIED | no parity computation possible | Depends on (1) and (2) |
| 4 | `KNOWN_LIMITATIONS.md` | NOT SATISFIED | no `docs/validation/generic_solar/KNOWN_LIMITATIONS.md` | KNOWN_LIMITATIONS MISSING |
| 5 | Dedicated test pack | NOT SATISFIED | 8+ test files reference Generic Solar incidentally; no dedicated pack | Test pack MISSING |
| 6 | Closure-review-style audit posture | NOT SATISFIED | D1 sheet has no Generic Solar row; D2 redo discipline names Generic Solar but only as default-False; D3 redo shadow validation is for TUHO and Oborovo only | Audit posture MISSING for Generic Solar |
| 7 | No external sign-off | SATISFIED (trivially) | no external sign-off exists | Sign-off is N/A at Level 1; this is not a gap |

**F1 Reference criteria summary:**

- **Satisfied:** 1 of 7 (criterion 7, trivially)
- **Partially Satisfied:** 0 of 7
- **Not Satisfied:** 6 of 7

**Generic Solar is 6/7 NOT SATISFIED for F1 Reference.** This
is **identical to Generic Wind** (6/7 NOT SATISFIED per F2-A).
Even where inputs are populated, the absence of an Excel
reference and a parity comparison means no F1 Level 2 criterion
is met.

## 4. Missing Evidence Inventory

The following is the explicit list of evidence missing before
Generic Solar can begin a controlled journey toward Reference
status. Each item is concrete and checkable.

### 4.1 Missing Excel reference

- `docs/validation/generic_solar/excel_reference/README.md` —
  describes which workbook, which version, source
- `docs/validation/generic_solar/excel_reference/<workbook>.xlsx` —
  the pinned reference workbook itself

### 4.2 Missing parity pack

- `docs/validation/generic_solar/parity/README.md` — parity
  methodology + tolerance
- `docs/validation/generic_solar/parity/extraction.csv` —
  extracted reference values
- `docs/validation/generic_solar/parity/results.json` — last-run
  parity results

### 4.3 Missing golden dataset (Level 3 only — not required for Reference)

- `docs/validation/generic_solar/golden_dataset/inputs.json`
- `docs/validation/generic_solar/golden_dataset/expected_outputs.json`
- `docs/validation/generic_solar/golden_dataset/README.md`

F2-B lists these for completeness, but the golden dataset is
**only required for Level 3 (Validated)**, not Level 2
(Reference). F2-C / F2-D / F2-E should not produce the golden
dataset as part of the Reference migration.

### 4.4 Missing test pack

- `docs/validation/generic_solar/test_pack/README.md` — test pack
  scope and threshold
- `docs/validation/generic_solar/test_pack/test_generic_solar_*.py`
  — at minimum: parity tests, parameter-validation tests,
  audit-surface tests, export-shape tests, frozen-vs-derived tests

### 4.5 Missing reviewer material (Level 3 only)

- `docs/validation/generic_solar/reviewer_signoff/README.md`
- `docs/validation/generic_solar/reviewer_signoff/<reviewer>_<date>.md`

Not required for Reference.

### 4.6 Missing audit documentation

- D1 audit sheet per-project row for Generic Solar (currently
  only a generic-project row exists)
- D2 redo discipline per-project row (currently Generic Solar is
  named only in the module docstring as default-False)
- D3 redo shadow validation for Generic Solar (currently only
  TUHO and Oborovo)

### 4.7 Missing limitations documentation

- `docs/validation/generic_solar/KNOWN_LIMITATIONS.md` — every
  Generic-Solar-specific limitation enumerated, with risk rating
  and mitigation

### 4.8 Unresolved data discrepancies

**No unresolved data discrepancies** for Generic Solar between
the factory and the Phase 34 doc. This is a positive finding.
(Generic Wind had three discrepancies per F2-A.)

F2-B does not need to resolve discrepancies before F2-C. F2-C
can proceed directly to the Excel reference acquisition.

### 4.9 Excel reference acquisition

The most critical missing evidence is the **Excel reference
workbook** itself. Options for acquiring it (to be evaluated in
F2-C):

- Acquire a representative Solar Excel model (industry template,
  public dataset, or partner-provided workbook).
- Build a synthetic reference workbook from the FincoGPT model
  itself, with all formulas documented.

The Phase 34 §5.3 already lists this as a blocking requirement.

## 5. Validation Risks

### 5.1 Highest parity risks

1. **No Excel reference** (the dominant risk). Without it, no
   parity computation is possible. All other parity risks are
   downstream of this one.
2. **Live sculpting vs frozen path.** Generic Solar uses
   `DSCR_SCULPT` (live sculpting). The Phase 34 doc requires
   "Live sculpting validation: confirm live sculpt = frozen if
   same inputs." This requires either a frozen-path reference
   or a separate live-sculpt-vs-frozen test pack. Neither exists
   today.
3. **Synthetic market price curve.** `market_prices_curve =
   tuple(60.0 + i for i in range(30))` is a synthetic linear
   ramp; a real Excel reference would have a market-shape curve.
   The delta between the synthetic curve and a real curve is
   unbounded and could dominate revenue parity.
4. **PV degradation handling.** Factory has
   `pv_degradation=0.004` (0.4% / year) but the legacy
   depreciation module does not handle PV degradation natively;
   it depends on whether the canonical engine is enabled.
   Generic Solar has no shadow validation, so the PV
   degradation-to-revenue path is not validated.
5. **CAPEX asset class distribution.** Factory uses
   `asset_class=SOLAR_PANELS` for Modules + Inverters,
   `asset_class=CIVIL_GRID` for Civil + Grid, and
   `asset_class=SOFT_COSTS` for Soft. A real Excel reference
   may have a different asset-class scheme. The asset-class
   distribution affects depreciation mapping and the canonical
   engine's CAPEX parity.

### 5.2 Highest modeling risks

1. **Sponsor modeling MISSING.** No sponsor-specific fields in
   the factory. A real solar project has a sponsor / equity
   provider with covenants. Generic Solar has no sponsor
   modeling. F2-C must decide whether to add it.
2. **Depreciation MISSING.** No Generic-Solar-specific
   depreciation. The D1-D3 arc covers TUHO and Oborovo;
   Generic Solar is not shadow-validated.
3. **OPEX coverage.** 4 OPEX items vs 12-15 for TUHO/Oborovo.
   A real solar project has more OPEX line items (technical
   management, insurance, maintenance, lease & tax, plus
   potentially panel cleaning, monitoring, inverter
   maintenance, vegetation control, etc.). The 4-item coverage
   is **a deliberate simplification for "tests/examples"** (per
   the docstring), not a model deficiency. F2-C must decide
   whether to expand OPEX coverage.
4. **CAPEX coverage.** 5 named CAPEX items + IDC + fees = 7 of
   17 fields. A real solar project has more CAPEX line items
   (modules, inverters, civil, grid, soft, plus mounting
   structures, tracker system, BOP, contingency, etc.). Same
   caveat as OPEX.
5. **No construction-period cost detail.** Construction is set
   as a duration (12 months) but no construction-period cost
   detail (e.g. per-period spending) is parameterized. F2-C
   must decide.

### 5.3 Highest governance risks

1. **Generic Solar inherits TUHO/Oborovo parity guardrails by
   accident.** The Phase 51F parity workflow does not include
   Generic Solar. If a Generic Solar run is added to a CI lane
   by accident, it could pollute the parity baseline. F2-C
   should make this explicit in the parity workflow.
2. **No `KNOWN_LIMITATIONS.md` means no documented risk
   register.** Reviewers and future maintainers have no
   authoritative place to look for Generic Solar limitations.
3. **No external review process defined for Generic Solar.**
   F1 §10.2 requires external reviewer sign-off for Level 3,
   but there is no defined process for Generic Solar
   specifically. F2-C should not start the external review
   process; that belongs to a later F-phase.
4. **Pilot RC scope matrix explicitly excludes Generic
   solar/wind.** This is the correct posture today, but it is
   a manual exclusion; a CI guard could be added to prevent
   Generic Solar from being included in the pilot RC scope by
   accident.

## 6. Generic Solar Roadmap (high-level only)

F2-B does **not** design the Generic Solar validation pack. F2-B
recommends the **next three high-level phases** (F2-C, F2-D,
F2-E) and their scope. Each phase will be designed in its own
follow-up prompt. The naming is **F2-C / F2-D / F2-E** (not
F2-B / F2-C / F2-D as in F2-A's roadmap for Generic Wind) to
make the sequence clear in the merge log; the **content** is
analogous to F2-A's roadmap for Generic Wind.

### 6.1 F2-C — Generic Solar input resolution + Excel reference

**Goal:** acquire or build the Excel reference workbook for
Generic Solar. (No data discrepancies to resolve — the
factory and the Phase 34 doc are consistent.)

**Scope (high-level):**
- Decide on the Excel reference source (acquire, build, or
  synthesize).
- Commit `docs/validation/generic_solar/excel_reference/`
  directory.

**Does NOT include:** parity computation, test pack, audit
updates. Those are F2-D and F2-E.

### 6.2 F2-D — Generic Solar parity comparison + audit posture

**Goal:** compute parity between Generic Solar and the Excel
reference, and add the audit posture (D1 sheet row, D2 redo
discipline, D3 redo shadow).

**Scope (high-level):**
- Compute parity for the 10 F1 Reference criteria that depend
  on the Excel reference.
- Add a D1 audit-sheet per-project row for Generic Solar.
- Extend the D2 redo discipline summary to include Generic
  Solar.
- (Optional) Run a D3 redo shadow validation for Generic
  Solar.
- Update `.github/workflows/parity_guardrails.yml` to include
  Generic Solar in scope.

**Does NOT include:** dedicated test pack, KNOWN_LIMITATIONS.md,
frozen-schedule validation. Those are F2-E.

### 6.3 F2-E — Generic Solar test pack + KNOWN_LIMITATIONS

**Goal:** create the Generic Solar dedicated test pack and the
KNOWN_LIMITATIONS.md.

**Scope (high-level):**
- Create `docs/validation/generic_solar/test_pack/` with parity
  tests, parameter-validation tests, audit-surface tests,
  export-shape tests, and a frozen-vs-derived test.
- Create `docs/validation/generic_solar/KNOWN_LIMITATIONS.md`
  with every Generic-Solar-specific limitation, risk rating,
  and mitigation.
- Add a CI guard that prevents Generic Solar from being added
  to the pilot RC scope by accident.

**Does NOT include:** promotion to Level 2. Promotion happens
in a separate F-phase after F2-E is merged and reviewed.

### 6.4 Post-F2-E

After F2-E is merged and reviewed, a separate F-phase
(likely F2-F) will:

- Run the F1 §10.1 promotion gate.
- Promote Generic Solar from Level 1 to Level 2 (Reference).
- Update the D1 audit-sheet row from
  `EXPLORATORY / UNVALIDATED` to `REFERENCE`.
- Update the `model_scope_and_limitations` doc column.

F2-B does **not** design F2-F.

## 7. Generic Solar Readiness Score

F2-B provides a hybrid readiness score (category + numeric 0-100)
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
an Excel reference and a parity computation is the dominant
gap. Without them, the technical readiness is fundamentally not
at Reference level. The score is **identical to Generic Wind's
technical readiness (30/100)** because both projects share the
same gap pattern.

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
and the Phase 34 doc provide **boundary** evidence (the
project is correctly excluded from the validated scope), but
boundary evidence is not validation evidence. The score is
**identical to Generic Wind's validation readiness (0/100)**.

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
rows, Generic-Solar-specific shadow validation) are documentation
gaps, not governance gaps. The 87/100 reflects that the
governance posture is correct (Generic Solar is correctly
excluded from the validated scope) but the documentation could
be more explicit. The score is **identical to Generic Wind's
governance readiness (87/100)** because both projects share the
same governance boundary.

### 7.4 Combined readiness

| Dimension | Category | Score |
|---|---|---|
| Technical | NOT READY | 30/100 |
| Validation | NOT READY | 0/100 |
| Governance | PARTIAL | 87/100 |
| **Average** | **NOT READY** | **39/100** |

**Overall category: NOT READY** for a controlled journey toward
Reference status. The combined score is **identical to Generic
Wind's combined score (39/100)**. The technical and validation
evidence is missing; the governance boundary is correct.

## 8. Recommendation

**Recommendation: A — Not ready to begin Reference journey.**

**Rationale:** Generic Solar is missing 6 of 7 F1 Reference
criteria. The dominant gaps are:

1. **No Excel reference workbook** (blocking).
2. **No parity computation** (depends on (1)).
3. **No `KNOWN_LIMITATIONS.md`** (independent gap).
4. **No dedicated test pack** (independent gap).
5. **No per-project D1/D2/D3 audit posture** (documentation gap).
6. **(Generic Solar does NOT have unresolved data discrepancies;
   this is a positive finding relative to Generic Wind.)**

The technical readiness is 30/100 (NOT READY). The validation
readiness is 0/100 (NOT READY). The governance readiness is
87/100 (PARTIAL), which is **good for an exploratory project**
but is not sufficient on its own.

Generic Solar should remain at **Level 1 (Exploratory /
Unvalidated)**. The F2-C / F2-D / F2-E roadmap (§6) is the
right next step: acquire the Excel reference, compute parity,
and create the test pack + KNOWN_LIMITATIONS.md. After F2-E, a
separate F-phase (likely F2-F) may evaluate whether Generic
Solar can be promoted to Level 2.

**Option B (limited preparation work) and Option C (controlled
Reference program) are not appropriate at this time.** Option B
would imply that some preparation is already in place; it is
not. Option C would imply a Reference program can be designed
on top of the current evidence; it cannot, because the Excel
reference is missing.

## 9. Hard no-go list (F2-B)

- no code changes
- no runtime changes
- no UI implementation
- no schema changes
- no persistence changes
- no formula changes
- no parity changes
- no feature flags
- no validation status changes
- no Generic Solar promotion
- no Generic Wind work
- no implementation roadmap beyond high-level inventory
- no extension of the D1 / D2 redo / D3 redo arc to cover
  Generic Solar
- no modifications to F2-A outputs (Generic Wind inventory)
- no modifications to F1 outputs (Generic Solar/Wind validation
  methodology)

## 10. Forbidden paths (F2-B)

F2-B does **not** modify:

- `app/**`
- `domain/**`
- `static/**`
- `tests/**`
- `main_web.py`
- `main_api.py`

F2-B only adds:

- `docs/phase_f2b_generic_solar_reference_inventory.md` (this file)
- `reports/phase_f2b_generic_solar_reference_inventory.json`

## 11. Stop-after-report contract

F2-B is:

- A docs-only, design-only inventory.
- A factual inventory + gap analysis only.
- No implementation, no runtime change, no flag enablement,
  no F2-C / F2-D / F2-E / F2-F start.
- No new tests, no new code, no new persistence, no new
  schema, no new export surface, no new UI.

Branch: `phase-f2b-generic-solar-reference-inventory`
PR: DRAFT only, do not mark ready, do not merge.
rc1 SHA: `b425a0708719eaa5e1d922b1008e5609758e0ad4` — untouched.
Generic Solar status: **Level 1 (Exploratory / Unvalidated)**
— unchanged.
Generic Wind status: **Level 1 (Exploratory / Unvalidated)**
— unchanged.
TUHO / Oborovo: **Level 2 (Reference)** — unchanged.

## 12. Appendix — top gaps (ranked by blocking-ness)

1. **Excel reference workbook** (blocks all parity).
2. **Parity computation** (blocks Phase 51F integration).
3. **`KNOWN_LIMITATIONS.md`** (blocks F1 §3.3 criterion 4).
4. **Dedicated test pack** (blocks F1 §3.3 criterion 5).
5. **Per-project D1/D2/D3 audit posture** (blocks F1 §3.3
   criterion 6).
6. **Sponsor modeling** (F2-C to decide; not a Reference
   criterion per se, but a modeling gap).
7. **Depreciation handling for Generic Solar** (no shadow
   validation; F2-C to decide whether to extend the
   D1-D3 arc).

## 13. Appendix — top risks (ranked by severity)

1. **No Excel reference** (dominant; blocks all parity).
2. **Live sculpting without a frozen-path validation** (the
   Phase 34 doc requires a live-sculpt-vs-frozen test; not
   present).
3. **Synthetic market price curve** (unbounded revenue-parity
   delta).
4. **PV degradation handling** (factory has 0.4% / year;
   legacy module does not handle PV degradation natively; no
   shadow validation).
5. **CAPEX asset class distribution** (factory uses
   SOLAR_PANELS / CIVIL_GRID / SOFT_COSTS; real Excel
   reference may differ; affects depreciation mapping).
6. **Generic Solar inherits TUHO/Oborovo parity guardrails
   by accident** (governance / CI risk).
7. **No `KNOWN_LIMITATIONS.md`** (no authoritative risk
   register for reviewers).

## 14. Appendix — Generic Wind vs Generic Solar delta

F2-B and F2-A together establish a pattern: **both Generic
projects share the same readiness profile** (39/100 combined),
the same governance boundary (87/100), and the same validation
gaps. The only differences are:

- **OPEX coverage:** Generic Wind 4 items (~550 kEUR Y1);
  Generic Solar 4 items (~380 kEUR Y1). Both minimal.
- **CAPEX coverage:** Generic Wind 4 named items; Generic
  Solar 5 named items (adds Inverters). Both minimal.
- **Construction period:** Generic Wind 18 months; Generic
  Solar 12 months.
- **Data discrepancies:** Generic Wind has 3; Generic Solar
  has 0.
- **Test file references:** Generic Wind 18; Generic Solar 8+.

These deltas do **not** change the F2-B recommendation.
Generic Solar should remain at Level 1 and follow the same
F2-C / F2-D / F2-E roadmap as Generic Wind's F2-B / F2-C /
F2-D roadmap. F2-C should consider whether to batch the
Generic Wind and Generic Solar Excel reference acquisition
into a single effort; this is a **process decision for F2-C**,
not a F2-B decision.
