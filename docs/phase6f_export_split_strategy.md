# Phase 6F-E — Excel/Export Split Strategy

**Repository:** xofisamba/Finco1
**Branch:** `phase6f-export-split-planning`
**Date:** 2026-05-12
**Type:** Architecture Strategy Document
**Scope:** Documentation only — no implementation changes

---

## Status

**STRATEGY ACCEPTED** — Implementation deferred to Phase 7A/7B.

---

## Context

Phase 6 has built a comprehensive tax audit export layer. The Excel export
(`app/excel_export.py`) now produces multiple sheets across several domains:
SPV P&L, SPV tax, HoldCo tax, tax assumptions, and tax snapshots. Each
domain owns its own sheet-writing logic.

Phase 7 will introduce sponsor cashflow and sponsor IRR outputs. Before that
work begins, this document establishes the export split strategy — defining
which layer owns which sheets, what naming conventions apply, and how
export ownership maps to the model's layer architecture.

---

## 1. Current Export Architecture State

### What exists

`app/excel_export.py::build_excel_export()` is the single entry point. It accepts
optional results from three domains and attaches their audit sheets:

```
build_excel_export(
    result=run_result,                 # core waterfall result (required)
    tax_results=None,                  # SPV tax result (optional)
    holdco_tax_results=None,           # HoldCo tax result (optional)
    tax_assumption_snapshot=None,       # tax assumptions snapshot (optional)
)
```

### Current sheet ownership

| Sheet group | Owner module | Sheet names |
|------------|--------------|-------------|
| Core waterfall | `app/excel_export.py` | CF Summary, Debt, Validation |
| SPV tax audit | `app/tax_excel_export.py` | Tax Summary, Tax_{EntityCode} |
| HoldCo tax audit | `app/holdco_tax_excel_export.py` | HoldCo Tax Summary, HoldCo Tax_{EntityCode} |
| Tax assumptions UI | `app/tax_assumptions_excel_export.py` | Tax Templates, Tax Tiers, Tax Dep Rules, Tax Overrides, Resolved Tax Config |
| Tax snapshot audit | `app/tax_assumptions_snapshot_excel_export.py` | Tax Snapshot Templates, Tax Snapshot Overrides, Tax Snapshot Resolved |

### Key design decisions already in place

- **AUDIT-ONLY row 1**: Every sheet starts with `AUDIT-ONLY: read-only governance artifact...` in cell A1
- **Optional integration**: All domain exports are opt-in via `None` default parameters
- **Sheet sanitization**: All names sanitized for Excel (`/\*?[]:` → `_`), 31-char limit enforced
- **Deduplication**: `base` → `base_2` → `base_3` strategy for name collisions
- **No formula export**: Values-only export; no `openpyxl` formula writing

---

## 2. Why Export Split Is Needed

### Problem: Layer ownership ambiguity

Without clear ownership boundaries, new sheets are added ad-hoc to existing
modules, creating coupling between unrelated domains. For example, a sponsor
cashflow sheet might be mistakenly added to `app/tax_excel_export.py` if the
developer is not careful.

### Problem: Naming inconsistency

Each export module currently uses its own naming conventions. SPV tax uses
`Tax_{EntityCode}`, HoldCo uses `HoldCo Tax_{EntityCode}`, tax assumptions use
`Tax Snapshot *`. Without standardization, users cannot predict sheet names.

### Problem: Metric duplication across layers

If SPV tax audit and HoldCo tax audit both compute "total CIT paid", they may
store it with different names or in different row positions. A user comparing
SPV and HoldCo CIT in the same workbook may get conflicting figures.

### Problem: Snapshot/export traceability

`TaxAssumptionSnapshot` is created at one point in time, but the audit sheets
exported from it are created later. If the model's tax configuration changes
between snapshot creation and export, the audit sheets may not reflect the
snapshot. No traceability mechanism exists.

### Why now — before Phase 7

Phase 7 will introduce sponsor cashflow and sponsor IRR sheets. If the split
strategy is not established now, sponsor sheets will be added inconsistently.
Establishing boundaries now ensures:
1. Each layer's sheets are owned by the correct module
2. Naming is predictable across layers
3. No metric duplication between SPV, HoldCo, and Sponsor layers
4. Validation fixtures and export sheets are aligned

---

## 3. Accounting Outputs vs Cashflow Outputs

### Accounting outputs (accrual)

- **P&L / Income Statement**: revenue, EBITDA, EBT, net income — all on accrual basis
- **Tax**: computed as owed per period, not yet paid
- **Depreciation**: accounting book (straight-line or asset-life based)
- **Recognition**: follows accounting period, not cash movement

These outputs belong in SPV-layer sheets. They are the "income statement"
view of the project.

### Cashflow outputs (cash)

- **Cash Flow Statement**: operating CF, investing CF, financing CF — actual cash movements
- **Debt service**: principal and interest actually paid in each period
- **Tax**: CIT actually paid (after cash timing lag)
- **Equity injections**: cash actually injected in each period
- **Sponsor distributions**: cash actually received by sponsor

These outputs belong in SPV-layer cashflow sheets and in the future Sponsor-layer
sheets. They are the "cash ledger" view.

### Separation principle

**No sheet should mix accrual and cash outputs in the same column structure.**
If a sheet has a "Tax (kEUR)" column, it must be unambiguous whether it is
accrual tax or cash tax. Ambiguity here creates audit risk and confusion for
covenant reviewers.

### Naming convention for disambiguation

When a metric exists in both accrual and cash forms, the sheet or column name
must disambiguate:

| Accrual | Cash |
|---------|------|
| `Tax Accrual (kEUR)` | `Tax Cash (kEUR)` |
| `EBITDA (kEUR)` | `Op Cash Flow (kEUR)` |
| `Net Income (kEUR)` | `Distributable Cash (kEUR)` |

---

## 4. SPV Layer Export Responsibilities

The SPV layer export covers a single project entity (e.g., Oborovo Solar d.o.o.).

### SPV sheet ownership

| Sheet | Owner | Content |
|-------|-------|---------|
| `CF Summary` | `excel_export.py` | Waterfall cashflow summary — existing |
| `Debt` | `excel_export.py` | Debt schedule — existing |
| `Validation` | `excel_export.py` | Input validation results — existing |
| `Tax Summary` | `tax_excel_export.py` | SPV tax summary — existing |
| `Tax_{EntityCode}` | `tax_excel_export.py` | Per-entity SPV tax detail — existing |

### SPV accrual sheets (existing)

`Tax Summary` and `Tax_{EntityCode}` sheets export **accrual CIT** — the tax
liability computed per period. These are audit-only sheets showing the tax
computation, not cash paid.

**Naming rule:** SPV tax sheets use `Tax_` prefix. No suffix for accrual vs cash
since the sheet name explicitly says "Tax" (accrual). Future cash tax sheets
will use `Tax Cash_` prefix.

### SPV cashflow sheet (future)

A `CF Detail` or `Cash Flow Detail` sheet may be added in Phase 7A to show
the cash flow waterfall with actual debt service and cash tax applied.

**Naming rule:** Cashflow sheets use `CF` prefix (`CF Detail`, `CF Summary`).

### SPV ownership boundary

`app/tax_excel_export.py` owns all SPV tax audit sheets. No other module may
write SPV tax sheets. Future sponsor cashflow sheets are owned by a future
`sponsor_excel_export.py`, not by `tax_excel_export.py`.

---

## 5. HoldCo Layer Export Responsibilities

The HoldCo layer export covers the HoldCo entity that aggregates one or more
SPV investments.

### HoldCo sheet ownership

| Sheet | Owner | Content |
|-------|-------|---------|
| `HoldCo Tax Summary` | `holdco_tax_excel_export.py` | HoldCo CIT summary — existing |
| `HoldCo Tax_{EntityCode}` | `holdco_tax_excel_export.py` | Per-entity HoldCo tax detail — existing |

### HoldCo accrual sheets (existing)

`HoldCo Tax Summary` and `HoldCo Tax_{EntityCode}` export **accrual CIT**
computed at the HoldCo level. WHT amounts are shown separately per entity.

**Naming rule:** HoldCo sheets use `HoldCo Tax_` prefix. The prefix makes it
immediately clear these are HoldCo-level, not SPV-level.

### HoldCo cashflow sheet (future)

A `HoldCo CF Summary` sheet may be added in Phase 7A showing HoldCo-level
cashflows: dividend income, SHL interest, HoldCo OpEx, CIT cash paid, WHT
remitted, distributions to Sponsor.

**Naming rule:** `HoldCo CF_` prefix for cashflow, `HoldCo CF Summary` for
consolidated.

### HoldCo ownership boundary

`app/holdco_tax_excel_export.py` owns all HoldCo tax audit sheets. Future
HoldCo cashflow sheets are also owned by a future `sponsor_excel_export.py`
since HoldCo cashflows feed directly into sponsor cashflows.

---

## 6. Future Sponsor Layer Export Responsibilities

The Sponsor layer export covers sponsor-level cashflows, capital account,
and IRR results.

### Anticipated sponsor sheet ownership (Phase 7A/7B)

| Sheet | Owner | Content |
|-------|-------|---------|
| `Sponsor CF Summary` | `sponsor_excel_export.py` (future) | Sponsor-level cashflow summary |
| `Sponsor Capital Account` | `sponsor_excel_export.py` (future) | Equity injection log + balance |
| `Sponsor IRR` | `sponsor_excel_export.py` (future) | IRR by scenario/tranche |

### Sponsor cashflow sheet

`Sponsor CF Summary` aggregates cashflows across all HoldCo investments:
- Equity injections (from `EquityInjection` records) per period
- Distributions received from HoldCo per period
- WHT on distributions per period
- Net cashflow to sponsor per period

**Naming rule:** `Sponsor CF_` prefix. Cashflow is always cash, never accrual.

### Sponsor IRR sheet

`Sponsor IRR` shows computed IRR and MOIC per scenario/tranche. This is a
**derived output** — the sheet contains results, not inputs.

**Naming rule:** `Sponsor IRR` (no suffix, singular). Detail sheets for
sub-scenarios use `Sponsor IRR_{ScenarioName}`.

### Sponsor ownership boundary

All sponsor-layer sheets are owned by a future `app/sponsor_excel_export.py`.
No existing module (`excel_export.py`, `tax_excel_export.py`,
`holdco_tax_excel_export.py`) may write sponsor sheets.

### Cross-layer coordination

`build_excel_export()` will eventually call:

```python
if sponsor_results is not None:
    write_sponsor_sheets(writer, sponsor_results)  # future
```

Sponsor sheets are appended after HoldCo sheets. The order in the workbook
reflects the model's layer hierarchy: SPV → HoldCo → Sponsor.

---

## 7. Validation/Export Alignment Principles

### Golden validation fixtures vs presentation formatting

**Golden validation fixtures** (`tests/golden/fixtures/`) are machine-readable
JSON fixtures containing metric values and tolerances. They are designed for
deterministic test validation.

**Presentation formatting** (Excel export) is human-readable, formatted for
covenant review and due diligence. They are different artifacts.

### Alignment principle

1. **Fixture first, export second.** If a golden fixture defines
   `equity_irr_30y`, the Excel sheet must have a cell or column that maps
   directly to that metric — same name, same numeric value, same unit.
   The Excel formatting (colors, fonts, column widths) is free to differ.
2. **No metric invented in export.** Every metric in an Excel sheet must be
   traceable back to a model output. Metrics computed in the export writer
   (e.g., formatting-only derived values) are not audit-traceable.
3. **Fixture names map to export column/row names.** If fixture uses
   `equity_irr_30y`, the export sheet should use the same name or a clear
   alias documented in the fixture metadata.

### Traceability mechanism (future)

Each Excel sheet's header row should include a reference to its source:

```
Row 1: AUDIT-ONLY: read-only governance artifact (source: SPV tax engine)
Row 2: Metric Name | Value | Unit | Source
```

This allows reviewers to trace each number back to its origin model output.

---

## 8. Snapshot/Export Consistency Requirements

### The snapshot-to-export gap

`TaxAssumptionSnapshot` captures tax configuration at a point in time.
Later, `write_tax_assumption_snapshot_sheets()` exports those snapshot values
to Excel. If the model is run again between snapshot creation and export,
the exported values may not match the snapshot if the model's tax configuration
has changed.

### Consistency requirement

**A snapshot export must reflect the snapshot's values, not the model's current
values.** The export writer must use the snapshot's stored values, not
re-compute from the model.

Current implementation already follows this: `write_tax_assumption_snapshot_sheets()`
reads directly from snapshot dataclasses, not from model outputs.

### Future snapshot consistency rules

If future snapshot types are added (e.g., `SponsorCashflowSnapshot`,
`EquityInjectionSnapshot`):

1. Snapshot creation captures model outputs at creation time
2. Snapshot export writes from snapshot data, not from current model
3. Snapshot and model must be stored/linked so reviewers can verify which
   model version produced which snapshot
4. `snapshot_label` + `created_at` + `model_version` fields provide
   traceability

### Audit note requirement

Every snapshot-exported sheet must carry an audit note confirming the sheet
reflects a point-in-time capture, not current model state. This is already
implemented in all Phase 6 export modules.

---

## 9. Risks of Mixed Export Semantics

### Risk 1: Accrual/cash mixing

If `Tax Summary` (accrual) and `Tax Cash Summary` (cash) sheets use the same
column name, users will confuse them. Covenant compliance depends on
correctly identifying which figure is used in DSCR tests.

**Mitigation:** Mandatory disambiguation in sheet/column names. Accrual: `Tax`.
Cash: `Tax Cash`. No ambiguity.

### Risk 2: Metric duplication with different values

If SPV tax exports "total CIT" and HoldCo tax also exports "total CIT", a user
reading both may think they are the same metric. In reality, they are different
(SPV-level vs HoldCo-level) and may have different values.

**Mitigation:** Prefix-based disambiguation (`Tax_*` vs `HoldCo Tax_*`).
Every metric in a HoldCo sheet must be explicitly labeled as HoldCo-level.

### Risk 3: Export drift from model

If the Excel export writer is modified to "clean up" values or normalize
formatting, it may inadvertently change the model output values. The export
should be a faithful copy of the model's computed values, not a reformatted
version.

**Mitigation:** Export writers are passive — they read model outputs and write
them to Excel. No calculation, normalization, or re-interpretation in the
export writer. Any normalization happens in the model layer before results
reach the export writer.

### Risk 4: Sheet name collision

If a future sponsor sheet uses the same name as an existing SPV or HoldCo
sheet, the workbook becomes confusing.

**Mitigation:** Layered naming with prefix hierarchy. SPV: `Tax_*`.
HoldCo: `HoldCo Tax_*`. Sponsor: `Sponsor CF_*`, `Sponsor IRR_*`.
Prefix hierarchy prevents collision.

### Risk 5: Snapshot export using stale data

If a snapshot is created, then the model is re-run (inputs or parameters
changed), then the snapshot export is generated — if the export writer
accidentally reads from the current model instead of the snapshot, the export
reflects the new model, not the snapshot.

**Mitigation:** Snapshot export functions accept only snapshot dataclasses.
They have no access to the running model. The data flow is:
`model → snapshot (frozen) → export writer → Excel`.
Not: `model → export writer → Excel` with snapshot as side channel.

---

## 10. Explicit Non-Scope

The following are explicitly out of scope for Phase 6F-E and the export
strategy:

| Item | Reason |
|------|--------|
| XLSX writer refactor | No change to `openpyxl` usage patterns |
| Formatting redesign | Colors, fonts, column widths not in scope |
| Workbook performance optimization | Large workbook speed not addressed |
| UI coupling | Streamlit/export coupling not designed |
| Sponsor waterfall implementation | Phase 7B topic |
| Export-side recalculation | Export writers are passive; no re-computation |
| Multi-workbook export | Single workbook per run; cross-workbook links not designed |
| External data ingestion | No API calls, no file downloads in exports |

---

## 11. Recommendation for Phase 7A/7B Export Evolution

### Phase 7A — Sponsor Cashflow Export

**Design checklist:**
- [ ] New module `app/sponsor_excel_export.py` owns all sponsor sheets
- [ ] `build_excel_export()` accepts new `sponsor_results=None` parameter
- [ ] Sponsor cashflow sheet named `Sponsor CF Summary` (consolidated) or `Sponsor CF_{Tranche}` (per tranche)
- [ ] Capital account sheet named `Sponsor Capital Account` with equity injection log
- [ ] All sponsor sheet column/row names align with golden fixture names
- [ ] AUDIT-ONLY row 1 on every sponsor sheet
- [ ] `model_version` and `snapshot_label` (if applicable) in sheet header
- [ ] Sponsor sheets appended after HoldCo sheets; layer order preserved

### Phase 7B — Sponsor IRR Export

**Design checklist:**
- [ ] `Sponsor IRR` sheet added to `sponsor_excel_export.py`
- [ ] IRR values are **derived outputs** — computed from sponsor cashflows, not from model inputs
- [ ] Sheet includes scenario name, tranche, and equity invested as reference
- [ ] AUDIT-ONLY row 1 with source attribution
- [ ] IRR values are machine-readable floats (not text descriptions)
- [ ] MOIC shown alongside IRR per scenario

### Naming consistency standards

| Layer | Prefix | Example |
|-------|--------|---------|
| SPV tax | `Tax_` | `Tax Summary`, `Tax_OBOROVO` |
| HoldCo tax | `HoldCo Tax_` | `HoldCo Tax Summary`, `HoldCo Tax_HC1` |
| HoldCo cashflow | `HoldCo CF_` | `HoldCo CF Summary` (future) |
| Sponsor cashflow | `Sponsor CF_` | `Sponsor CF Summary`, `Sponsor CF_TrancheA` |
| Sponsor IRR | `Sponsor IRR` | `Sponsor IRR`, `Sponsor IRR_Downside` |
| Sponsor capital | `Sponsor CapAcct_` | `Sponsor CapAcct` (future) |

**Suffix rule:** Use `_EntityCode` for per-entity detail sheets. Use `_ScenarioName`
for per-scenario sheets. No numeric suffixes (`_2`, `_3`) in user-facing names —
those are internal deduplication handles only.

### Export module ownership summary

| Module | Owner | Sheets |
|--------|-------|--------|
| `app/excel_export.py` | Core | CF Summary, Debt, Validation, Notes |
| `app/tax_excel_export.py` | SPV Tax | Tax Summary, Tax_{EntityCode} |
| `app/holdco_tax_excel_export.py` | HoldCo Tax | HoldCo Tax Summary, HoldCo Tax_{EntityCode} |
| `app/tax_assumptions_excel_export.py` | Tax Admin | Tax Templates, Tax Tiers, Tax Dep Rules, Tax Overrides, Resolved Tax Config |
| `app/tax_assumptions_snapshot_excel_export.py` | Tax Admin | Tax Snapshot Templates, Tax Snapshot Overrides, Tax Snapshot Resolved |
| `app/sponsor_excel_export.py` | **Future** | Sponsor CF Summary, Sponsor CapAcct, Sponsor IRR |

---

*End of Strategy Document — Phase 6F-E Export Split Strategy*
*Branch: phase6f-export-split-planning*
*Implementation: Phase 7A/7B sponsor export*