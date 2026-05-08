# Known Limitations — FincoGPT Release 1

_Valid as of 2026-05-06 | Branch: post-rc1-structure-roadmap_

---

## 1. Supported Scope

**Release 1 is a screening and demonstration model.**

| Feature | Status | Notes |
|---------|--------|-------|
| Solar project | ✅ Full model | Revenue → CFADS → DSCR → debt → returns |
| Wind project | ✅ Full model | Same structure as Solar |
| Scenario selector (Base/Downside/Upside) | ✅ Functional | Solar and Wind only; BESS/Portfolio always Base |
| Simple OPEX | ✅ Functional | `OpexItem` list with Y1 amount + inflation |
| Advanced OPEX (line-item engine) | ✅ Functional MVP | Solar and Wind; BESS/Portfolio use Simple OPEX |
| OPEX → waterfall integration | ✅ Functional | Advanced OPEX is threaded through `run_demo_project()` → `WaterfallRunner` |
| OPEX → DSCR sculpting | ❌ Not modelled | OPEX does not respond to DSCR target changes |
| Excel export | ✅ Functional | Values-only (no formula export); covers all tabs |

**Intended use:** Early-stage project screening, investor presentation demo, model structure review.

**Not intended for:** Investment committee decisions, due diligence, audited financials, live project monitoring.

---

## 2. Experimental Scope

Features that are structurally present but not validated for production use.

### Portfolio Aggregation
- Portfolio mode combines Solar + Wind into a pooled view.
- **Portfolio project IRR**: calculated but not independently validated.
- **Portfolio sponsor IRR**: placeholder — returns `0.0` / shows "⏳ Placeholder" in UI and export.
- **Do not use for investment decisions.**

### Holding Company Layer
- Conceptually described in `docs/excel_to_ui_mapping.md` (Portfolio BP Patterns).
- Not implemented in the runtime model.
- Distributions go directly from asset SPV to equity holders; no intermediate hold-co layer.

---

## 3. Partial Implementations

### BESS / Hybrid (Solar+BESS, Wind+BESS)

- Revenue from storage and/or hybrid PPA is calculated.
- Waterfall model runs (debt sizing, DSCR, distributions).
- **⚠️ BESS revenue-only warnings are shown** (`W_ZERO_GENERATION`, `W_DSCR_BELOW_TARGET`).
- Full BESS cost structure and hybrid optimisation are **not yet implemented**.
- Scenario selector is blocked for BESS types (always shows Base case).

### ScenarioManager — Now Integrated (2026-05-06)

- `app/scenario_manager.py` provides `Scenario` dataclass and `ScenarioManager` class.
- **Active runtime engine** — wired into `run_demo_project()` for all Solar/Wind scenarios.
- Uses identical multiplier values as legacy engine (revenue −5%/+3%, capex +5%/−3%, opex +10%/−5%, p50 0.90/1.05, degradation 1.15/0.90).
- `app/scenarios.apply_scenario()` is deprecated — retained for backward compatibility only (marked with deprecation comment in file).
- `scenario_summary()` drives UI scenario table, Excel export delta table, and UI runner display — all three now use the same source.
- **⚠️ CAPEX depreciation uses legacy path:** per-asset-class depreciation from factory `CapexItem` objects, not from `CapexLineItem` breakdown. See CAPEX Matrix section above.

### CAPEX Matrix — Integrated (2026-05-06)

- The **💰 CapEx tab** shows an editable CAPEX matrix with `CapexLineItem` objects.
- The matrix uses `generate_capex_schedule()` to compute per-period draws.
- `capex_line_items` from UI → `run_demo_project()` → `waterfall_core` → total CAPEX override applied.
- **Depreciation integration complete:** `app/depreciation_engine.generate_schedule()` provides per-asset-class straight-line depreciation from CapexLineItems. `advanced_capex_depreciation_schedule` parameter threads the schedule through `run_waterfall_v3_core()` and `WaterfallRunConfig`. When provided, it replaces the legacy CapexItem-based depreciation for the tax-shield calculation.
- **⚠️ Note:** Default CapexLineItem totals (84,850 kEUR for 50MW Solar) differ from factory defaults (30,700 kEUR) — this is intentional as the line-item engine models a more granular cost build-up. Users see the higher total when Advanced CAPEX is active.
- See `docs/ARCHITECTURE.md` §CAPEX status for full details.

---

## 4. Placeholders

### Sponsor IRR
- `result.sponsor_irr` is computed by the model (equity-level XIRR).
- Excel export shows the actual computed value (not a placeholder label).
- Portfolio-level sponsor IRR shows "⏳ Placeholder" — sponsor cash-flow aggregation is not yet implemented.
- **Sponsor IRR should not be used as the primary investment decision metric without manual review.**

### LCOE
- Displayed in UI and exported as a KPI.
- Methodology note in export: "Excludes debt service — see methodology document for details."

---

## 5. Export Limitations

- **Values only** — no Excel formulas are written to the export workbook.
- All numeric values are static; recalculation is not supported in Excel.
- No named ranges, no macros.
- Semiannual periods shown as column headers (date labels); no automatic grouping to annual in the raw export — `aggregate_period_table_annual()` is applied per-tab when user selects "Annual" view.

---

## 6. Calibration Status (2026-05-08 P0 Sprint)

### Fixed Bugs

| Issue | Impact | Status |
|-------|--------|--------|
| Oborovo debt-service fixed_debt_keur payment bug | DSCR 0.181→1.250, Equity IRR 9.96%→10.16% | ✅ Fixed |
| TUHO Project IRR levered tax basis | Project IRR 10.46%→9.47% (matches reference 9.47%) | ✅ Fixed |

### Remaining Calibration Gaps (P1)

| Issue | Impact | Path |
|-------|--------|------|
| Oborovo merchant price curve vintage mismatch | Project IRR +0.69pp vs Excel (8.65% vs 7.96%) | Merchant curve framework P1 |
| Oborovo depreciation convention (20y vs 30y asset life) | Deferred tax timing difference | Depreciation P1 |

### TUHO CO2 Revenue
- CO2 revenue calibrated: equity IRR 11.81% vs reference 11.61% (+0.20pp within ±1.0pp)
- TUHO project IRR now correctly calibrated after unlevered tax fix

---

**Model status: screening-grade, not audited financial advice.**

---

## 6. Future Roadmap

These items are **not in scope for Release 1**:

| Item | Priority | Notes |
|------|----------|-------|
| CAPEX matrix → waterfall integration | High | Wire `CapexLineItem` / `generate_capex_schedule()` into `WaterfallRunConfig` |
| ScenarioManager migration | High | Replace legacy `apply_scenario()` with `ScenarioManager.apply_overrides()`; reconcile multiplier values |
| BESS / Hybrid full waterfall | Medium | Revenue-only shown; full cost + hybrid optimisation pending |
| Sponsor IRR portfolio aggregation | Medium | Implement sponsor-level cash-flow aggregation across assets |
| Debt-sculpting-aware OPEX | Medium | OPEX responds to DSCR target changes |
| Add/delete OPEX line items in UI | Low | Currently fixed line-item set per technology |
| Multi-currency / FX conversion | Low | All calculations in EUR; FX table deferred |
| Excel workbook import | Low | Anti-pattern; leads to tight coupling |
| Holding company layer | Low | Requires sponsor-level cash flows + hold-co debt |

---

## 7. Validation Coverage

`domain/validation.py` provides:

- `validate_project_inputs()` — structural validation (capacity, pricing, tenor sanity)
- `warn_model_unrealistic()` — plausibility checks (DSCR floor, generation floor)

Validation is run on every `run_demo_project()` call. Results are shown in the **🔍 Validation** expander in the UI.

Validation does **not** cover:
- Cross-tab arithmetic consistency (CFADS = Revenue − OPEX − Tax)
- Debt schedule mathematical correctness
- Tax computation against jurisdiction-specific rules

---

### Custom Input Schema MVP
- Custom inputs via JSON supported in API and CLI
- YAML input not yet supported
- `project_name` field in JSON is parsed but not propagated to `ProjectInfo.name` (frozen dataclass limitation)
- `total_capex_keur` must be greater than fixed other capex items (~10,000 kEUR for Solar)
- CAPEX depreciation: `app/depreciation_engine.generate_schedule()` provides per-asset-class straight-line depreciation from CapexLineItems; integrated via `advanced_capex_depreciation_schedule` parameter in `run_waterfall_v3_core()` and `WaterfallRunConfig`. Legacy CapexItem path remains the default for backward compatibility.

### /validate endpoint (API)
- Performs structural (Pydantic) + business-rule validation
- NO waterfall execution — validation only, no financial feasibility guarantee
- Warnings for suspicious but allowed values (e.g., very high gearing >85%, low tariff <10 EUR/MWh)

---

## 8. How to Interpret the Numbers

| Metric | What It Means | Caveat |
|--------|--------------|--------|
| Project IRR | XIRR of total cashflows (debt + equity) | NPV at 0 discount = XIRR crossover |
| Equity IRR | XIRR of equity cashflows only | Assumes debt is priced at model rate |
| Sponsor IRR | Equity IRR + any subordinated returns | Single-project only; portfolio placeholder |
| DSCR | CFADS / Senior Debt Service per period | Model uses sculpted debt; actual DSCR ≠ target if revenue varies |
| Sculpted DSCR | The debt sizing target (e.g., 1.20×) | Model forces this target by adjusting debt quantum |
| Actual DSCR | Realised DSCR given actual period cashflows | Shown in Excel DSCR Summary tab |
| Min / Avg DSCR (Dashboard) | Actual DSCR statistics | Shown in Dashboard KPI cards |
---

## 9. Validation & Test Philosophy

**Golden outputs are branch-current reference values — NOT bank certification.**

The `TestScenarioManagerGoldenOutputs` test uses hardcoded KPI values captured from a
single isolated run of `run_demo_project('Solar', 'Base')`. These values drift with any
change to the calculation engine and are intentionally tight (±25bps IRR, ±0.02 DSCR,
±1% revenue/EBITDA) to catch regressions. Wide bounds would only catch gross errors.

**No mutation guarantee.**
All `apply_overrides()` operations use `dataclasses.replace()` to return fresh copies.
`scale_capex_items()` and OPEX scaling follow the same pattern. Original `ProjectInputs`
objects are never modified. Mutation of shared module-level state is treated as a bug
and covered by `TestScenarioManagerNoMutation`.

**Determinism.**
Repeated runs of the full test suite produce identical Solar Base KPI values
as isolated runs. If isolated and suite-integrated runs diverge, mutation leakage is the
primary suspect.

**Test isolation.**
Each test constructs its own `ScenarioManager` and `ProjectInputs` from factory functions.
No shared mutable state at module level.

| What is tested | What is NOT tested |
|---------------|-------------------|
| Override logic correctness | Bank-certification accuracy |
| KPI regression detection (±tight tolerance) | Model assumptions validity |
| No mutation of original inputs | Excel formula correctness |
| Deterministic full-suite runs | Cross-tab arithmetic audit |

