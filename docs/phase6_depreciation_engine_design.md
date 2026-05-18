# Phase 6 — Depreciation Engine Design

## Branch
`phase6-depreciation-engine-design`

## Status
**Stage 1: Docs-only architecture design. No production code. No runtime changes.**

---

## 1. Executive Summary

Phase 6 diagnostic work is complete. The Phase 6 tax validation pack (PR #80) has been approved with confidence 9.5/10 and no blockers. The key structural finding is the **useful-life policy/input mismatch** between Excel and Python:

- Excel/TUHO uses **20-year useful life** for main CAPEX categories (turbines, EPC, grid, project rights)
- Excel/TUHO uses **12-year useful life** for financing costs (IDCs, commitment fees, bank fees)
- Python uses a **30-year straight-line** canonical assumption
- This mismatch causes CIT/R67 timing differences but is **not** an Excel accelerated write-off — it is a deliberate project-specific input choice

**R99/R102 remain BLOCKED.** The depreciation engine design does not unblock R99. R99 design is only authorized after: useful-life canonical decision, loss-window decision, residual recheck, and external sign-off.

The long-term solution is **not** a TUHO-only hardcoded bridge. It is a `domain/depreciation` module with per-category `useful_life_years` sourced from project inputs — applicable to TUHO, Oborovo, and future projects.

This branch is Stage 1 only: architecture design, no implementation.

---

## 2. Problem Statement

### Current State

| Source | Main CAPEX Useful Life | Financing Cost Useful Life |
|--------|----------------------:|---------------------------:|
| Excel/TUHO Inputs D358–D379 | **20 years** | **12 years** (IDCs/commitment fees/bank fees) |
| Python (current canonical) | **30 years** straight-line | 30 years (same) |

### Observed Impact

- Yr13–20: Python depreciates less per period → higher taxable income → Python overpays CIT vs Excel by +5,697 kEUR
- Yr21–30: Python still depreciates (30yr schedule), Excel has 0 → Python underpays CIT by −425 kEUR
- Net observed R67 residual: +5,271 kEUR over yr13–30 (Python > Excel)

### Nature of the Mismatch

This is **not** an Excel accelerated write-off. Excel Dep R30 reaches 0 in yr21 because the assets are fully depreciated after the explicit 20-year useful life specified in the Inputs sheet. Python's 30-year straight-line is a conservative institutional assumption — appropriate for some contexts but not for TUHO.

For wind turbines, 20–25 years is industry-normal. 30 years is a conservative modelling choice. The right solution is configurable per-category useful life, not a TUHO-only plug.

---

## 3. Non-Goals

This branch explicitly does NOT:

- ❌ Implement a TUHO-only hardcoded depreciation bridge
- ❌ Integrate the depreciation engine into the runtime waterfall
- ❌ Promote R99/R102
- ❌ Plug the tax residual with a scalar adjustment
- ❌ Change existing waterfall behavior
- ❌ Opt in factories
- ❌ Modify any production code in `app/`, `domain/`, or `tests/`

---

## 4. Proposed Package Architecture

```
domain/depreciation/
 __init__.py          # Public API exports
 config.py           # DepreciationConfig dataclass + defaults
 categories.py        # AssetCategoryRule + registry
 engine.py           # DepreciationEngine class
 result.py           # DepreciationScheduleResult, DepreciationScheduleEntry
 templates/
   __init__.py
   croatia.py        # Croatia-specific defaults (20yr main CAPEX, 12yr financing)
   default.py       # Conservative fallback template (30yr)
```

### Design Principles

1. **Input-first**: `useful_life_years` is sourced from project inputs when available
2. **Template fallback**: country/template defaults when no project input exists
3. **Conservative fallback only**: explicit warning if falling back to the default 30-year assumption
4. **Book + tax dual-track**: engine can produce both book and tax schedules (or explicitly map one to the other)
5. **No runtime coupling in Stage 2**: offline engine only; waterfall integration only behind a default-off guard in Stage 3

---

## 5. Proposed Dataclasses

```python
@dataclass
class AssetCategoryRule:
    """Per-category depreciation rule."""
    category_id: str                    # e.g. "turbines", "epc", "idc"
    category_name: str                  # Human-readable label
    capex_amount_keur: float            # Gross asset basis for this category
    useful_life_years: int              # Depreciation period in years
    depreciation_method: str            # "straight_line", "zero_after_life", ...
    start_period: int                  # Period index when depreciation begins
    end_period: int                    # Period index when depreciation ends (inclusive)
    residual_value_keur: float = 0.0    # Scrap/residual value at end of useful life
    is_financing_cost: bool = False    # True for IDC/commitment fees/bank fees
    source_reference: str = ""          # e.g. "Excel Inputs!D358" or "project input"
    frequency: str = "semiannual"       # "annual" or "semiannual"


@dataclass
class DepreciationScheduleEntry:
    """One period's depreciation output."""
    period_index: int
    book_depreciation_keur: float
    tax_depreciation_keur: float
    cumulative_book_keur: float
    cumulative_tax_keur: float
    remaining_book_basis_keur: float
    remaining_tax_basis_keur: float
    is_zero_after_life: bool = False   # True if useful life has ended


@dataclass
class DepreciationScheduleResult:
    """Full schedule for one asset category."""
    category_id: str
    entries: list[DepreciationScheduleEntry]
    total_book_depreciation_keur: float
    total_tax_depreciation_keur: float
    frequency: str


@dataclass
class DepreciationConfig:
    """Top-level configuration for a depreciation run."""
    asset_categories: list[AssetCategoryRule]
    period_count: int
    period_frequency: str = "semiannual"   # "annual" or "semiannual"
    country_template: str = "croatia"        # Controls default useful lives if not overridden
    project_inputs_overrides: dict = {}     # Optional per-category overrides from project inputs
    fallback_warning_enabled: bool = True


@dataclass
class DepreciationTemplate:
    """Country/template-level defaults for useful life by asset category."""
    template_id: str
    template_name: str
    defaults: dict[str, int]   # category_id → useful_life_years
    notes: str = ""
```

---

## 6. Depreciation Methods

### Supported (Stage 2+)

| Method | Description |
|--------|-------------|
| `straight_line` | Equal periodic depreciation over useful life; residual = 0 |
| `zero_after_life` | Depreciates normally during useful life; automatically 0 after `useful_life_years` expires (primary method for asset categories) |
| `custom_schedule` | Explicit period-by-period amounts from a provided schedule array |

### Future Placeholders

| Method | Status |
|--------|--------|
| `accelerated` | Not in scope for Stage 2; placeholder for future regulatory acceleration |
| `declining_balance` | Not in scope for Stage 2; placeholder for tax-specific methods |
| `tax_specific_schedule` | Not in scope for Stage 2; placeholder for separate tax schedule |

**Note:** `zero_after_life` handles both annual and semiannual frequency. The useful life is expressed in **years**; the engine converts to number of periods based on `frequency`.

---

## 7. Useful-Life Sourcing

```
useful_life_years resolution order:
  1. project_inputs_overrides (per AssetCategoryRule)
     → explicit project input from workbook
  2. template defaults (from DepreciationTemplate)
     → e.g. croatia.py: main_CAPEX=20yr, financing_costs=12yr
  3. conservative fallback (30 years)
     → emits a DeprecationWarning if fallback_warning_enabled=True
```

### Croatia / TUHO Template Defaults (`templates/croatia.py`)

```python
CROATIA_DEFAULTS = {
    "turbines":          20,   # Production unit / turbines
    "epc":               20,   # EPC Contract
    "grid_connection":  20,   # Grid connection
    "project_rights":   20,   # Project Rights
    "idc":               12,   # IDC / Interest During Construction
    "commitment_fees":  12,   # Commitment fees
    "bank_fees":         12,   # Bank fees / arrangement fees
    "other":            20,   # Other CAPEX — conservative fallback
}
```

**Fallback warning example:**
```
DepreciationWarning: No useful_life_years specified for category "other" in project.
Falling back to CROATIA_DEFAULTS["other"]=20 years.
If falling back to 30 years, set fallback_warning_enabled=False explicitly.
```

---

## 8. Book vs Tax Depreciation Distinction

### Current Python Tax Bridge

The current Python tax bridge (in `waterfall_core.py`) maintains:
- `book_depreciation_keur` — from the depreciation ledger
- `tax_depreciation_audit_keur` — from the depreciation ledger

These flow into the tax bridge formula as separate terms.

### Future Engine Design

The future `DepreciationEngine` should produce both book and tax schedules:

**Option A — Dual-schedule engine (preferred):**
- Produces `book_schedule` and `tax_schedule` simultaneously
- Each is a `DepreciationScheduleResult` with per-period `book_depreciation_keur` / `tax_depreciation_keur`
- Integration layer maps one (or both) into the tax bridge

**Option B — Single schedule + mapping:**
- Engine produces one schedule
- Tax schedule = `book_schedule × tax_book_ratio` where ratio is from project inputs
- Simpler but less flexible

**No change to current Python bridge in this design.** The Stage 2 engine is offline-only. Runtime integration (Stage 3) will decide between Option A and B.

---

## 9. Integration Plan by Stages

### Stage 1 (This Branch)
- Docs-only architecture design
- No production code, no runtime changes
- Produces `docs/phase6_depreciation_engine_design.md`

### Stage 2 — Offline Engine Only
- Implement `domain/depreciation/` package
- Tests against TUHO Dep R30 and R31 extractions
- **Expected parity target:** ±1 kEUR per period for TUHO extraction
- No waterfall integration
- No factory opt-in
- No R99 unblock

### Stage 3 — Runtime Adapter (Default-Off)
- TUHO-only guarded opt-in behind a feature flag
- Compare R67 residual before/after
- Keep R99 BLOCKED throughout
- No factory opt-in
- Oborovo remains guarded

### Stage 4 — Generalization
- Oborovo template support
- User-visible input for useful life per category
- UI/export visibility for depreciation schedules
- R99 design only after Stages 2–4 complete and external sign-off obtained

---

## 10. Testing Strategy (for Stage 2+)

| Test | Description | Expected Outcome |
|------|-------------|-----------------|
| `test_straight_line_schedule` | Category depreciates equally over useful life | Annual amount = capex / useful_life_years |
| `test_zero_after_life` | Verify 0 depreciation after useful life ends | All periods after life = 0 |
| `test_tuho_dep_r30_parity` | TUHO 20-year engine vs Excel Dep R30 | ±1 kEUR per period, ±10 kEUR cumulative |
| `test_tuho_financing_costs_12yr` | Financing costs (IDC/commitment/bank fees) 12-year schedule vs Excel Dep R30 | ±1 kEUR per period |
| `test_fallback_warning_emitted` | Missing project input falls back to 30 years | DeprecationWarning emitted |
| `test_default_behavior_unchanged` | Existing ledger depreciation unchanged when engine not active | Current fixture values preserved |
| `test_no_factory_opt_in` | Engine flag does not auto-opt-in factories | Feature flag default = OFF |
| `test_r99_still_blocked` | R99 promotion gate still fails after engine introduction | R99 gate = BLOCKED |

---

## 11. Excel Parity Targets

| Target | Per-Period Tolerance | Cumulative Tolerance |
|--------|---------------------:|---------------------:|
| TUHO Dep R30 (main CAPEX, 20yr) | ±1 kEUR | ±10 kEUR |
| TUHO Dep R31 (financing costs, 12yr) | ±1 kEUR | ±10 kEUR |

### R67 Recheck After Depreciation Engine

After Stage 3 integration, recheck the R67 residual:
- **Not necessarily solved** — other drivers (SHL, senior, EBITDA, loss CF) remain unaddressed
- **Expected improvement:** the useful-life mismatch contribution (approx −2,783 kEUR net) should be reduced
- **New residual target:** document residual change; not a closure target
- **Formal tolerance:** ±2,000 kEUR cumulative for yr13–30 (from validation pack gate table)

---

## 12. Governance / Open Decisions

The following canonical decisions are **still pending** and must be resolved before Stage 3 runtime integration:

| Decision | Options | Current State |
|----------|---------|--------------|
| Default renewable useful life | 20, 25, or 30 years | Python canonical = 30yr; Excel = 20yr |
| Should useful life always come from project input? | Yes (mandatory) / No (template fallback allowed) | Template fallback allowed with warning |
| Should tax depreciation follow book depreciation or separate schedule? | Same as book / Separate tax schedule | Current Python = separate; future TBD |
| Should financing costs depreciate/amortize over 12 years by default? | 12 years / Other | Excel TUHO = 12yr for IDC/commitment/bank fees |
| How to handle assets with COD/phased COD? | Single COD date / Phased per category | Not yet designed |

These decisions require stakeholder input (sponsor, tax advisor, auditor) before Stage 3.

---

## 13. R99/R102 Gate Reminder

**R99/R102 remain BLOCKED throughout all stages.**

The depreciation engine design does **not** unblock R99. R99 design is only authorized after all of the following:

1. ✅ Useful-life canonical decision (above)
2. ✅ Loss-window canonical decision
3. ✅ Residual recheck after depreciation engine integration
4. ✅ External reviewer sign-off on Phase 6 validation pack

---

## 14. Minor Validation Pack Doc Fixes

Two small corrections identified during design review, applied to `docs/phase6_tax_validation_pack.md` in this branch:

### Fix 1 — CO2 Y1 Revenue Reference

**Before:** "CO2 revenue Y1 = 611 kEUR" (ambiguous source)

**After:** "CO2 revenue Y1 = 611 kEUR is CF R35 'CO2 Certificates Sales'. CF R36 is the CO2 price per MWh (4.191 EUR/MWh)."

### Fix 2 — ATAD / R34 Framing

**Before:** Implied R34 = 0 means Excel has no ATAD mechanism at all

**After:** "R34 = 0 for TUHO Y13–30 because thin-cap is not binding in profit years. R34 is non-zero for Y4–12 (construction period), total around −9,243 kEUR, and is calibrated. Excel has a thin-cap / fiscal reintegration mechanism; it is not visible in R35 during profit years but is active in loss/construction years."

---

## Validation
- This branch: docs only, no production code changes
- Changed files: `docs/phase6_depreciation_engine_design.md`, `docs/phase6_tax_validation_pack.md` (minor fixes only)
- No runtime integration
- No factory opt-in
- R99/R102: BLOCKED

---

## Recommended Next Branch
**`phase6-depreciation-engine-impl`** (Stage 2 — offline engine implementation, tests against TUHO Dep R30/R31, no runtime integration)