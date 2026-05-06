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

### ScenarioManager (Foundation — Not Integrated)

- `app/scenario_manager.py` provides `Scenario` dataclass and `ScenarioManager` class.
- **This is a foundation module. It is not yet wired into `run_demo_project()`.**
- The active scenario engine is `app/scenarios.apply_scenario()` (legacy).
- The two engines use **different revenue/tariff multipliers** (legacy: −5%/+3%; ScenarioManager: −15%/+15%).
- Migration plan: wire `ScenarioManager.apply_overrides()` into `run_demo_project()`, then remove legacy engine.
- See `docs/ARCHITECTURE.md` §ScenarioManager for full details.

### CAPEX Matrix — Now Wired to Waterfall (2026-05-06)

- The **💰 CapEx tab** shows an editable CAPEX matrix with `CapexLineItem` objects.
- The matrix uses `generate_capex_schedule()` to compute per-period draws.
- `capex_line_items` from UI → `run_demo_project()` → `waterfall_core` → total CAPEX override applied.
- **⚠️ Depreciation integration is future work:** Advanced CAPEX currently overrides `total_capex` in the waterfall (affecting IRR/debt sizing), but the **depreciation schedule** still uses legacy `CapexItem` asset-class breakdown from the factory. Full per-asset-class depreciation from CapexLineItems is not yet implemented.
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
