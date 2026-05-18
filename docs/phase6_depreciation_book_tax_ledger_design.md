# Phase 6 Depreciation Book/Tax Ledger Design

## 1. Executive Summary

After the default-off SHL gross accrued P&L bridge, the largest validated TUHO R35 source gap is closed. The remaining taxable-income-before-losses delta is no longer an SHL ownership issue:

| Driver | Current status | Delta |
| --- | --- | ---: |
| SHL interest gross/net/timing | Closed | 0.0 kEUR |
| Book/tax depreciation timing | Open | +2,302.2 kEUR |
| OPEX/local-tax/minor row timing | Open | -733.5 kEUR |
| Senior interest timing/basis | Open | +355.4 kEUR |
| R34 fiscal reintegration | Calibrated | 0.0 kEUR |
| Other/unmapped | Open | -55.0 kEUR |

Depreciation is therefore the primary remaining R35 blocker. The issue is ownership, not a scalar residual: Excel separates book depreciation used in P&L and Balance Sheet presentation from tax depreciation used in the tax bridge. Python still needs an explicit ledger that can own both bases without mixing accounting presentation with tax deduction logic.

This work should stay separate from SHL and loss engine work. SHL gross accrued interest is now an input to P&L attribution; rolling losses consume taxable income after book-to-tax adjustments; neither should own asset-class depreciation schedules. A depreciation ledger gives Phase 6 a clean source for P&L R13, Dep R30/R31, Balance Sheet accumulated depreciation/NBV, and later R35/R67 validation.

This branch is design-only. It does not change runtime formulas, tax formulas, P&L formulas, R99/R102 source status, SHL FCF behavior, project factories, UI, cache, or persistence.

## 2. Excel Mapping

The future Python implementation should treat Excel depreciation rows as distinct book and tax concepts even where workbook labels are terse or project-specific.

| Excel area | Row/sheet | Meaning | Future Python owner |
| --- | --- | --- | --- |
| CAPEX categories | CAPEX sheets / project inputs | Construction spend by asset category, including timing and capitalization basis | `domain/depreciation.asset` through construction handoff |
| Inputs CAPEX summary | Inputs CAPEX summary rows | Aggregated asset bases and placed-in-service assumptions | `domain/depreciation.ledger` input builder |
| Dep R30 | Dep sheet R30 | Book depreciation schedule used for financial statements | `domain/depreciation.schedule` book policy |
| Dep R31 | Dep sheet R31 | Tax or unlevered depreciation schedule used for tax bridge | `domain/depreciation.schedule` tax policy |
| P&L R13 | P&L depreciation | Book depreciation expense in accounting EBT | Financial statements P&L consumes ledger book depreciation |
| BS gross assets | Balance Sheet fixed-asset rows | Gross book asset basis before accumulated depreciation | Balance Sheet assembly consumes ledger gross book basis |
| BS accumulated depreciation | Balance Sheet accumulated depreciation rows | Cumulative book depreciation | Balance Sheet assembly consumes ledger accumulated book depreciation |
| BS net book value | Balance Sheet NBV rows | Gross assets less accumulated book depreciation | Balance Sheet assembly consumes ledger book NBV |
| Tax bridge depreciation adjustment | P&L/tax bridge R31/R35 path | Tax depreciation and book-tax adjustment needed to reach taxable income | Tax bridge consumes ledger tax depreciation and book-tax difference |

The design assumption is:

```text
P&L R13 = book depreciation
Dep R30 = book depreciation evidence row
Dep R31 = tax depreciation / tax deduction evidence row
R35 = book EBT + explicit tax adjustments
```

## 3. Target Architecture

Create a dedicated package for depreciation ownership:

```text
domain/depreciation/
  __init__.py
  asset.py
  schedule.py
  ledger.py
  result.py
  templates/croatia.py
```

### Ownership Boundaries

| Module | Responsibility | Does not own |
| --- | --- | --- |
| `asset.py` | Asset classes, capitalization basis, placed-in-service metadata | Period cash waterfall or tax payable |
| `schedule.py` | Straight-line book and tax depreciation schedules | Revenue, OPEX, SHL, senior debt |
| `ledger.py` | Period ledger assembly from asset classes and policies | Runtime cashflow formulas |
| `result.py` | Immutable result dataclasses for period and full-horizon outputs | Project factory opt-in |
| `templates/croatia.py` | Croatia default policies and tax template assumptions | Workbook-specific override values unless explicit |

### Proposed Dataclasses

```python
@dataclass(frozen=True)
class AssetClassConfig:
    asset_class: str
    gross_asset_basis_keur: float
    book_depreciable_basis_keur: float
    tax_depreciable_basis_keur: float
    placed_in_service_period: int
    depreciation_start_period: int
    source_label: str = ""
```

```python
@dataclass(frozen=True)
class DepreciationPolicy:
    method: str = "straight_line"
    useful_life_book_periods: int | None = None
    useful_life_tax_periods: int | None = None
    period_frequency: str = "semiannual"
    partial_period_convention: str = "none"
```

```python
@dataclass(frozen=True)
class DepreciationLedgerInput:
    asset_classes: tuple[AssetClassConfig, ...]
    policies: Mapping[str, DepreciationPolicy]
    period_count: int
    period_frequency: str
    cod_period: int
```

```python
@dataclass(frozen=True)
class DepreciationPeriodResult:
    period_index: int
    asset_class: str
    gross_asset_basis_keur: float
    book_depreciation_keur: float
    tax_depreciation_keur: float
    accumulated_book_depreciation_keur: float
    accumulated_tax_depreciation_keur: float
    nbv_book_keur: float
    nbv_tax_keur: float
    book_tax_difference_keur: float
```

```python
@dataclass(frozen=True)
class DepreciationLedgerResult:
    periods: tuple[DepreciationPeriodResult, ...]
    total_book_depreciation_keur: float
    total_tax_depreciation_keur: float
    ending_nbv_book_keur: float
    ending_nbv_tax_keur: float
```

The first implementation should support straight-line depreciation only. Additional methods should be added only when an Excel fixture proves they are needed.

## 4. CAPEX / Construction Integration

The depreciation ledger should receive an explicit construction handoff rather than reading construction internals directly. The future handoff should be a stable list of capitalized asset line items.

Required future input fields:

| Field | Purpose |
| --- | --- |
| `asset_class` | Maps CAPEX categories to book/tax policy |
| `capex_amount_keur` | Direct spend before capitalization adjustments |
| `vat_applicable` | Marks whether VAT is part of recoverable/non-recoverable treatment |
| `wht_applicable` | Marks whether WHT is relevant to capitalization or tax basis |
| `financing_costs_keur` | Financing costs or IDC to classify separately |
| `senior_idc_keur` | Senior IDC if project policy capitalizes it for book or tax |
| `vat_facility_idc_keur` | VAT facility financing cost handoff for future work |
| `cod_date` | Commercial operation date |
| `placed_in_service_date` | Asset availability date by category |
| `partial_period_convention` | Start-date convention for depreciation |

VAT facility treatment is explicitly out of scope for this design branch. The ledger interface should leave room for VAT and financing-cost classification but must not implement VAT facility logic until a dedicated workstream owns it.

## 5. P&L / BS / Tax Bridge Integration

Future source-of-truth flow:

```text
construction/CAPEX handoff
  -> depreciation ledger
     -> book depreciation -> P&L R13 and BS accumulated depreciation/NBV
     -> tax depreciation  -> tax bridge depreciation adjustment / R31
```

Detailed integration policy:

| Consumer | Source | Rule |
| --- | --- | --- |
| P&L R13 | Ledger book depreciation | P&L uses accounting depreciation, not tax depreciation |
| P&L R32 EBT | P&L R13 plus revenue/OPEX/debt rows | EBT is a book P&L concept |
| Tax bridge R35 | Book EBT plus explicit tax adjustments | R35 should not be built from a hidden tax-depreciation shortcut |
| Tax bridge R31 | Ledger tax depreciation | R31 remains a tax bridge/audit row |
| Balance Sheet | Ledger gross assets and accumulated book depreciation | BS uses book gross asset basis and book NBV |
| R99/R102 | Still blocked | No runtime source acceptance until R35/R67 validation passes |

This makes book-tax differences explicit:

```text
book_tax_difference_keur = tax_depreciation_keur - book_depreciation_keur
taxable_income_before_losses =
  book_ebt
  + fiscal_reintegration
  + explicit book-tax depreciation adjustment
  + other proven tax adjustments
```

## 6. TUHO / Oborovo Parity Strategy

Fixture strategy should be established before any runtime bridge:

| Fixture | Purpose |
| --- | --- |
| Excel book depreciation by period | Validate P&L R13 / Dep R30 |
| Excel tax depreciation by period | Validate Dep R31 and tax bridge deduction |
| Category-level CAPEX basis | Validate asset-class ownership where extractable |
| Accumulated depreciation / NBV | Validate Balance Sheet linkage |
| Period dates and COD markers | Validate start conventions |

Acceptance targets:

| Target | Tolerance |
| --- | --- |
| Book depreciation R13/R30 | within +/-0.5 kEUR per period |
| Tax depreciation R31 | within +/-0.5 kEUR per period |
| Accumulated book depreciation | within +/-0.5 kEUR per material period |
| Net book value | within +/-0.5 kEUR per material period |
| Total book depreciation | within +/-0.1% cumulative |
| Total tax depreciation | within +/-0.1% cumulative |
| Runtime behavior before flag branch | unchanged |

TUHO should be implemented first because it is the current R35/R67 blocker. Oborovo should remain diagnostic until its CAPEX categories, depreciation evidence rows, and period conventions are proven to the same standard.

## 7. Implementation Roadmap

### A. `phase6-depreciation-book-tax-ledger-design`

This branch. Produce the ownership and integration design only.

### B. `phase6-depreciation-book-tax-offline-engine`

Implement the offline ledger package and fixture-backed TUHO/Oborovo tests. No runtime wiring, no ProjectInfo flags, and no R99/R102 acceptance.

### C. `phase6-book-depreciation-pnl-bridge`

Add a default-off P&L bridge so financial statements P&L R13 can consume book depreciation from the ledger. Preserve legacy P&L behavior when off.

### D. `phase6-bs-consumes-book-depreciation`

Use ledger gross assets, accumulated book depreciation, and NBV in the offline Balance Sheet assembly. Keep cash residual and R99/R102 status unchanged.

### E. `phase6-tax-bridge-consumes-tax-depreciation`

Allow the tax bridge, behind the existing tax-bridge discipline, to consume explicit tax depreciation and book-tax adjustment rows. R99/R102 remains audit-only.

### F. `phase6-r35-full-validation`

Re-run R35/R67 validation after SHL gross interest, book/tax depreciation, and vintage loss engine alignment. Only then reassess R99 runtime source promotion.

## 8. Risk And Scope Discipline

Hard forbidden scope for this branch:

- runtime formula changes
- tax formula changes
- P&L formula changes
- depreciation runtime implementation
- SHL changes
- loss engine changes
- R99/R102 runtime source acceptance
- SHL FCF opt-in
- project factory opt-in
- UI/cache/persistence changes

Risks for future branches:

| Risk | Mitigation |
| --- | --- |
| Treating tax depreciation as P&L depreciation | Keep R13/R30 book rows and R31 tax row separate |
| Hidden CAPEX category mismatch | Require category-level fixture evidence where available |
| Capitalized financing-cost ambiguity | Carry separate fields for IDC and VAT facility IDC; do not blend silently |
| BS imbalance from placeholder assets | Mark residual cash/assets explicitly until ledger sources are proven |
| Premature R99 acceptance | Require R35/R67 validation before source promotion |

## 9. Deliverable

This branch creates:

```text
docs/phase6_depreciation_book_tax_ledger_design.md
```

Architecture recommendation: implement a dedicated offline `domain/depreciation/` ledger that owns book and tax depreciation separately by asset class, then consume it through default-off P&L, Balance Sheet, and tax-bridge branches.

R99 readiness status: blocked. R99/R102 should remain audit-only until book depreciation, tax depreciation, R35, loss engine, and R67 dual-target validation pass.

Recommended next branch:

```text
phase6-depreciation-book-tax-offline-engine
```
