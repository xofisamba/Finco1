# Excel-to-UI Mapping

> **Purpose:** Translate reviewed Excel model patterns (TUHO, Oborovo) into FincoGPT product structure.

## Principles

### Do Not Copy Excel 1:1
Excel workbooks encode decisions that were made for a specific model in a specific tool (Excel). FincoGPT is a Python/streamlit application — different strengths, different constraints. Translation requires judgment:

- Excel is cell-based; FincoGPT is object-based
- Excel allows arbitrary formula composition; FincoGPT requires structured inputs
- Excel sheets are flat; FincoGPT has domain layers (revenue, debt, tax, returns)

**Translation rule:** Capture the *intent* and *structure* of the Excel pattern, not its implementation details.

---

## Asset-Level Patterns (TUHO / Oborovo)

These are the primary blueprint for the asset-level model.

### Granular CAPEX
TUHO/Oborovo break CapEx into line items:
- Grid connection
- BoS (Balance of System)
- EPC contract
- Development costs
- Contingency

Each line item may have:
- A base amount in kEUR
- An escalation/inflation factor
- A timing (construction period distribution)

**FincoGPT mapping:** `domain/capex/` — tree-structured CapEx with per-item inflation and timing.

### Granular OPEX
TUHO/Oborovo OPEX is broken into categories:
- Technical Management (B.01)
- Infrastructure Maintenance (B.02)
- Clean Material (B.04)
- Power Expenses (B.08)
- Environmental & Social (B.12)
- Insurance
- Land lease
- Asset management fees

Each OPEX line may be:
- **Inflated from base** — compound inflation applied to base-year amount
- **Manual schedule** — explicitly entered per-year values
- **Mixed** — some years formula-driven, others manually overridden

**FincoGPT mapping:** `app/opex_engine.py` — `OpexLineItem` with `calculation_mode`.

### Scenario Columns
Excel models typically have scenario columns:
- Base (reference case)
- Downside (stress assumptions)
- Upside (optimistic assumptions)

Each scenario is a full copy of the base column with adjustments applied to specific drivers (yield, tariff, CapEx, OpEx).

**FincoGPT mapping:** `app/scenarios.py` — Base/Downside/Upside applied as deltas to preset inputs.

### Base Scenario Duplication
Excel models often create a "Base Copy" as a reference before applying scenario adjustments. This preserves the ability to see what the base assumptions were.

**FincoGPT mapping:** Presets serve as base assumptions. Scenario deltas are applied at runtime without mutating the preset.

### Manual/Hardcoded Overrides
Excel models frequently have cells with hardcoded values that deviate from formula-driven calculations. These are typically:
- Flagged with a different fill color (e.g., yellow = manual input)
- Accompanied by a note or comment
- Sometimes locked to prevent accidental overwriting

**FincoGPT mapping:**
- `is_hardcoded` flag on `OpexLineItem` / `CapExLineItem`
- `source: formula | manual` distinction
- Amber/warning UI indicator for manual entries
- Override notes stored per line item

---

## Portfolio BP Patterns (Future Roadmap)

> ⚠️ **These patterns are for later implementation. They are NOT part of the current roadmap.**

The Portfolio Business Plan (as reviewed from the Excel models) adds:

### Holding Company Layer
A parent entity above the asset SPV that:
- Owns equity in each asset
- May have its own debt (holding company debt)
- Aggregates distributions from assets

**Roadmap status:** Future Phase 3+. Not implemented in Release 1.

### Portfolio Aggregation
Multiple assets rolled up into a single view:
- Combined revenue, EBITDA, debt service
- Weighted average DSCR
- Portfolio-level IRR

**Roadmap status:** Experimental in current app. Full aggregation not yet implemented.

### Sponsor/Holding Cashflows
Sponsor-level cash flow after holding company expenses and debt service.

**Roadmap status:** Sponsor IRR is currently a placeholder. Full implementation deferred.

### Multi-Layer Capital Stack
Typical structure:
1. Senior debt (project finance, recourse to SPV only)
2. Subordinated debt / SHL (may sit at asset or hold co)
3. Equity (SPV level)
4. Shareholder loan (another subordinated instrument)

**Roadmap status:** SHL implemented at asset level. Hold co layer deferred.

### Distributions
Rules for how cash is distributed up from asset → hold co → equity holders.

**Roadmap status:** Distributions to equity holders implemented. Hold co layer deferred.

### Checks Sheet
Excel models often have a "checks" sheet that verifies:
- DSCR is above lockup threshold
- Debt is not exceeding covenants
- Tax computations are consistent

**Roadmap status:** DSCR checks implemented at waterfall level. Broader check engine deferred.

### Model Currency
Excel models may have:
- Functional currency (EUR, USD, HRK, BAM)
- Reporting currency
- FX rates applied to convert between them

**Roadmap status:** All calculations in EUR. Display label only. Full FX conversion deferred.

---

## Recommended Implementation Roadmap

This is the order in which to tackle the remaining work:

```
1. OPEX line-item engine        ← START HERE (post-rc1 safe first step)
   - OpexLineItem dataclass
   - generate_opex_schedule()
   - Backward-compatible with existing model

2. CAPEX line-item model
   - CapExLineItem dataclass
   - Per-item inflation and timing
   - Construction period distribution

3. Scenario columns
   - Named scenario assumptions (Base, Downside, Upside)
   - Scenario-specific input overrides
   - Visible delta vs. base

4. Portfolio / holding / sponsor design
   - Holding company layer
   - Sponsor-level cash flows
   - Multi-asset aggregation

5. Multi-currency support
   - Functional currency setting
   - FX rate table
   - Conversion at model boundaries
```

---

## What NOT to Implement Yet

Based on rc1 product state:

| Feature | Reason to Defer |
|---------|----------------|
| BESS/hybrid full waterfall | Revenue-only; waterfall in progress |
| Portfolio holding company | Sponsor IRR is placeholder; aggregation experimental |
| Full FX/multi-currency | All calcs in EUR; display only for now |
| Sponsor IRR real implementation | Placeholder only; waiting for sponsor cashflows |
| Excel workbook import | Anti-pattern; leads to tight coupling |
| Waterfall rewrite | Stable; no justification for breaking change |

---

## TUHO/Oborovo Excel Reference

Key structural observations from the reviewed Excel models:

**TUHO Wind (72 MW, Bosnia)**
- FC: 2028-06-30, COD: 2029-12-30
- SHL: 29,135 kEUR, PIK + sweep
- CO2 certificates: ~611 kEUR Y1
- Tax: BIH corporate, LCF, ATAD

**Oborovo Solar (53.63 MW, Croatia)**
- FC: 2026-03-31, COD: 2026-09-30
- SHL: 14,621 kEUR, PIK only
- Tax: Croatian CIT with LCF

Both models use:
- Semiannual time steps
- DSCR-sculpted senior debt
- 51-period horizon (25.5 years)
- Revenue = PPA + CO2 certificates

---

## Advanced OPEX Line Items (Experimental)

> **Status:** Experimental — available on branch `post-rc1-structure-roadmap`.

### Overview

Advanced OPEX replaces the legacy "simple OPEX" (a list of `OpexItem` objects with Y1 amount + inflation) with a granular line-item engine. Each line item has:

- `name` — human-readable label
- `category` — grouping (operations, infrastructure, insurance, land, power_expenses, environmental_social)
- `base_year_amount_keur` — Year 1 amount in kEUR
- `inflation_rate` — annual compound inflation
- `calculation_mode` — INFLATED_FROM_BASE (default) | MANUAL_SCHEDULE | MIXED
- `source` — FORMULA (default) | MANUAL | HARDCODED
- `is_hardcoded` — boolean flag for amber UI indicators
- `override_note` — free-text note for manual/hardcoded entries
- `manual_overrides_keur` — per-year override tuple (None = use formula value)

### Simple OPEX (Default)

The simple OPEX path (legacy `OpexItem` / `OpexParams`) remains the default. It is used when:
- Advanced OPEX is disabled in the UI
- No line items are configured
- Project type is BESS or Portfolio

### Technology Coverage

| Technology | Line Items | Default Categories |
|---|---|---|
| Solar | 7 | operations, infrastructure, clean_material, power_expenses, environmental_social, insurance, land |
| Wind | 6 | operations, infrastructure, power_expenses, environmental_social, insurance, land |
| BESS | — | Not yet implemented — simple OPEX only |
| Portfolio | — | Not yet implemented — simple OPEX only |

### OPEX Tab (Advanced OPEX)

The Advanced OPEX editor is a first-class **💸 OPEX tab** (position 4 in tab bar).

**Tab order:** Dashboard | Inputs | CapEx | **OPEX** | Revenue | Debt | Tax | Waterfall | Returns | Portfolio

**Editable project assumptions:** Moved from sidebar to Inputs tab as "Edit project assumptions" checkbox.

**OPEX Mode selector:** Simple | Advanced (radio, horizontal), default=Simple, Solar/Wind only.

**Advanced mode matrix:**
- `st.data_editor` with columns: `Line Item` (locked) | `Budget (kEUR)` | `Inflation (%)` | `Y1`...`Yn`
- WHT column removed (not yet applied to data model)
- Editing Budget or Inflation → updates formula base; override detection uses **new (edited) base**
- Editing a Y cell → that year becomes manual override (stored in `manual_overrides_keur[y_idx]`)
- Total OPEX row shown **below** matrix as read-only dataframe (not in data_editor)
- `num_rows="fixed"` keeps row count stable
- Stale-state warning shown after edits: `⚠️ OPEX inputs changed — click Run Model to update Dashboard, Debt, DSCR and Returns.`

### OPEX Tab (Advanced OPEX)

The Advanced OPEX editor moved from sidebar to a first-class **💸 OPEX tab**.

**Tab order:** Dashboard | Inputs | CapEx | **OPEX** | Revenue | Debt | Tax | Waterfall | Returns | Portfolio

**OPEX Mode selector** (inside OPEX tab):
- Simple OPEX (default) — uses legacy `OpexItem` path
- Advanced (line items) — Solar/Wind only; others show info message

**Advanced mode content:**
- Line-item editor: Name, Category, Base (kEUR), Inflation %, Source, HC flag, Override note
- Per-row expander showing full metadata
- Schedule preview matrix below editor:
  - Rows = line items (first column = "Line Item")
  - Columns = Y1, Y2, … Y{horizon}
  - Final row = **Total OPEX**
  - Uses `generate_opex_schedule()` as source of truth (values-only, no recalc)
- Warning banner when MANUAL source, is_hardcoded=True, or has_manual_overrides()

**State management:**
- `_opex_mode` in session state: "Simple" or "Advanced"
- Changing mode → `demo_result=None` (forces rerun)
- Editing any line item field → `last_advanced_opex_signature` updated → rerun
- Solar↔Wind switch → line items reinitialised from defaults
- Non-Solar/Wind → `advanced_opex_line_items=None`, mode=Simple

**Signature fields:** name, category, base_year_amount_keur, inflation_rate, source.value, is_hardcoded, override_note, manual_overrides_keur, calculation_mode.value

### Model Warnings

When advanced OPEX contains manual or hardcoded items, a warning is surfaced:
> "Advanced OPEX contains manual or hardcoded values. Review override notes."

Shown in the OPEX tab (banner) and appended to `demo.messages`.

### Integration Points

| Component | Change |
|---|---|
| `waterfall_core.run_waterfall_v3_core()` | Added `advanced_opex_line_items` parameter |
| `WaterfallRunConfig` | Added `advanced_opex_line_items` field |
| `WaterfallRunner.run()` | Passes config's `advanced_opex_line_items` to core |
| `ui_runner.run_demo_project()` | Accepts `advanced_opex_line_items` arg, threads to `_run_waterfall()` |
| `ui_runner._advanced_opex_warnings()` | New helper — detects manual/hardcoded items |
| `streamlit_app.py` | OPEX tab (💸) replaces sidebar expander |

### Export Integration

Advanced OPEX is integrated into the Excel export:

**OPEX Detail sheet** (created when `advanced_opex_line_items` is truthy — i.e. OPEX tab in Advanced mode):
- Columns: Line Item Name | Category | Year (1-based) | Value (kEUR) | Source | Is Override | Is Hardcoded | Override Note
- Rows: one per line item per year (horizon_years rows per item)
- Values-only (no formulas)
- Uses `generate_opex_schedule()` output directly

**Notes sheet warning** (when manual/hardcoded items detected):
- Entry: `Advanced OPEX` → `Manual or hardcoded values present — review override notes`
- Triggers on: `source==MANUAL`, `is_hardcoded==True`, or `has_manual_overrides()==True`
- Single consolidated entry (no duplicates)

**Behavior:**
- Simple OPEX mode → no OPEX Detail sheet, no Notes warning
- Advanced OPEX mode → OPEX Detail sheet + Notes warning if manual/hardcoded items present

### Next Steps

1. Add/delete line item buttons in OPEX matrix
2. Per-year override editor (cell-level highlight)
3. Group structure for OPEX items (Technical Management, Infrastructure Maintenance, etc.)
4. CAPEX line-item model (mirrors OPEX structure)
5. Support BESS/Hybrid advanced OPEX

