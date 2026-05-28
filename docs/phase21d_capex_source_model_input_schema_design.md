# Phase 21D — CAPEX Source Model / Input Schema Design

**Branch:** `phase21d-capex-source-model-input-schema-design`
**Base:** `origin/main` @ `1208f9c` (Phase 21C merged, PR #292)
**Goal:** Design the CAPEX source model and input schema — define source types, scopes, line definition structure, and payment schedule shape — before implementing CAPEX input wiring
**Status:** DESIGN ONLY — no runtime model changes — DO NOT MERGE until reviewed

---

## Executive Summary

Phase 21D defines the **CAPEX Source Model** and **Input Schema Design** that will guide future CAPEX input wiring. This phase is purely design/schema — no runtime model code is changed. The design addresses the four structural problems identified in Phase 21C:

1. **EPC C.02** — App's 52,800 kEUR (4-semester aggregate) vs Excel's 13,560 kEUR (per-batch one-shot reference) are **not directly comparable 1:1**
2. **Grid C.03** — App's 6,200 kEUR (full interconnection) vs Excel's 30 kEUR (GPA fee only) are **different scope** items
3. **Project Rights C.16** — Excel's 14,739 kEUR with no app field maps to it — needs a **deferred schema bucket** until wired
4. **M1–M18 Payment Schedule** — Monthly schedule shape and timing role need explicit definition separate from total CAPEX amount

The design introduces:
- **`CapexSourceType`** — classifies where a line's value originates (app input, excel reference, runtime computed, etc.)
- **`CapexScope`** — classifies the temporal/scope meaning of the amount (aggregate total, payment batch, fee only, project rights, etc.)
- **`CapexLineDefinition`** — the schema record for each C.01–C.18 line with all metadata
- **`CapexPaymentSchedule`** — the schema for 18-month payment schedule timing

---

## Current CAPEX Audit Status After Phase 21C

### Authority Counts (TUHO, Phase 21C)

| Status | Count | Notes |
|---|---|---|
| `backend_authoritative` | 8 | C.17.01/02/03, C.18.01/02/03, C.17.04/05 |
| `app_mapped` | 1 | C.13 Contingencies |
| `excel_reference_only` | 8 | C.01.01, C.04.01/02, C.05.01–04, C.11.04 |
| `scope_mismatch` | 5 | C.02, C.03.01, C.16.01/02/03 |
| `mismatch` | 17 | EPC sub-items, C.03.02, grid, insurances, land, DD, CM, audit, C.12, C.15 |
| `missing_runtime_source` | 2 | — |
| `not_applicable` | 35 | Zero rows in both |
| **Total child rows** | **73** | |

### C.01–C.18 Mapping Status

| Category | Excel kEUR | App kEUR | Status |
|---|---|---|---|
| C.01 Production Unit | 35,000 | 0 | `excel_reference_only` |
| C.02 EPC Contract | 13,560 | 52,800 | `scope_mismatch` (aggregate vs per-batch) |
| C.03 Grid Connection | 30 | 6,200 | `scope_mismatch` (GPA fee vs full interconnection) |
| C.04–C.05 Misc | 1,100 | 0 | `excel_reference_only` / `not_applicable` |
| C.06–C.12 Unmapped | ~4,000 | ~0 | `mismatch` / `not_applicable` |
| **C.13 Contingencies** | **2,992** | **2,992** | **`app_mapped`** ✅ |
| C.14–C.15 | 0 | 1,000 | `mismatch` |
| C.16 Project Rights | 14,739 | 0 | `scope_mismatch` (no app field) |
| C.17 Financing Costs | ~2,302 | ~2,525 | `backend_authoritative` ✅ |
| C.18 Reserve Accounts | 0 | 0 | `backend_authoritative` ✅ |

---

## Design Problem 1: EPC C.02 — Aggregate vs Payment Batch

### Current Problem

| Source | Amount | Scope |
|---|---|---|
| App `epc_contract` | **52,800 kEUR** | 4-semester aggregate EPC contract total |
| Excel C.02 reference | **13,560 kEUR** | One-shot per-batch EPC payment reference |

**Root cause:** The app (TUHO) uses a 6-month construction model with a lump-sum EPC value. Excel TUHO uses an 18-month construction period with batched payments. App's 52,800 = 4 × 13,200 (aggregated across construction semesters). Excel's 13,560 is a single batch reference amount.

The two values are NOT a 1:1 comparison. They have different **temporal scope**: app is an aggregate total across all construction periods, Excel is a per-batch reference.

### Design Decision

**Preserve the aggregate vs payment-batch distinction. Do not force equality.**

The detail grid should:
1. Display the app's `epc_contract.amount_keur = 52,800` as an **`aggregate_total`** scoped line
2. Show Excel's child rows (C.02.01–04) separately as **`payment_batch`** scoped reference rows
3. **NOT** display a mismatch badge when scopes differ — use `scope_mismatch` or render as separate rows without direct comparison

### Proposed Field Structure

```python
# In CapexLineDefinition for C.02 aggregate row:
source_type = CapexSourceType.APP_INPUT      # "app_input"
scope = CapexScope.AGGREGATE_TOTAL           # "aggregate_total"
amount_keur = 52800.0                        # app total
affects_runtime = True                       # epc_contract feeds capex total
runtime_field = "capex.epc_contract.amount_keur"
mapping_note = "App 52,800.00 kEUR — 4-semester EPC aggregate; Excel reference 13,560 kEUR is per-batch one-shot"

# In Excel payment-batch children:
source_type = CapexSourceType.EXCEL_REFERENCE  # or IMPORTED_SCHEDULE
scope = CapexScope.PAYMENT_BATCH                # "payment_batch"
amount_keur = <per-batch amount>
affects_runtime = False                          # not yet wired
mapping_note = "Excel reference payment batch; app has aggregate only"
```

---

## Design Problem 2: Grid Connection C.03 — Full Scope vs GPA Fee

### Current Problem

| Source | Amount | Scope |
|---|---|---|
| App `grid_connection` | **6,200 kEUR** | Full interconnection cost |
| Excel C.03.01 GPA fee | **30 kEUR** | Grid Purchase Agreement fee (prerequisite only) |
| Excel C.02.04 Grid connection | **10,800 kEUR** | Separate grid line in Excel |

**Root cause:** The app's `grid_connection` field conflates two Excel line items:
- C.03.01 (GPA fee, 30 kEUR) — administrative/regulatory fee
- C.02.04 (Grid connection = 10,800 kEUR) — physical interconnection cost

App's 6,200 kEUR appears to be a selective subset, not directly comparable to either Excel line item individually.

### Design Decision

**Subdivide app grid_connection into explicit sub-components:**

1. **`gpa_fee`** child row (maps to Excel C.03.01 = 30 kEUR): `scope = FEE_ONLY`
2. **`full_interconnection`** parent row (maps to total grid interconnection scope): `scope = AGGREGATE_TOTAL`

Alternatively, keep the 6,200 kEUR as `aggregate_total` scope and treat the Excel 30 kEUR row as `fee_only` scope — displayed separately rather than compared.

**The detail grid should NOT show a mismatch between 6,200 and 30 (different scopes).**

### Proposed Field Structure

```python
# GPA fee sub-row:
source_type = CapexSourceType.EXCEL_REFERENCE   # or APP_INPUT when wired
scope = CapexScope.FEE_ONLY                      # "fee_only"
amount_keur = 30.0
runtime_field = None   # not yet wired to runtime
mapping_note = "GPA fee — regulatory prerequisite, not full interconnection"

# Full interconnection (app field):
source_type = CapexSourceType.APP_INPUT
scope = CapexScope.AGGREGATE_TOTAL
amount_keur = 6200.0
affects_runtime = True
runtime_field = "capex.grid_connection.amount_keur"
```

---

## Design Problem 3: Project Rights C.16 — No App Field

### Current Problem

| Source | Amount | Scope |
|---|---|---|
| App TUHO `project_rights` | **0 kEUR** | No TUHO-specific project rights field set |
| App Oborovo `project_rights` | **3,024.5 kEUR** | Oborovo factory sets this |
| Excel C.16 total | **14,739 kEUR** | Akuro dev 2,739 + dev costs 2,000 + purchase 10,000 |

**Root cause:** The TUHO template does not populate `project_rights` (set to 0), and no other app field captures the 14,739 kEUR project rights costs from the Excel. This is a **material unmapped cost**.

**Key taxonomic question:** Is a project rights/premium:
- A depreciable CAPEX item?
- A non-depreciable acquisition premium?
- A tax-basis-specific item (e.g., land rights vs equipment rights)?

### Design Decision

**Create a deferred schema bucket — `project_rights` scope — not yet wired to runtime totals.**

- Add `CapexScope.PROJECT_RIGHTS = "project_rights"` to the scope enum
- Keep source_type as `EXCEL_REFERENCE` for now
- Mark as `deferred` until Phase 21E when the accounting/tax treatment is clarified
- **Do NOT wire into `capex_items` or affect runtime totals until the bucket meaning is confirmed**

Question to resolve in Phase 21E: Should `project_rights` be depreciable (reducing taxable income) or non-depreciable (acquisition premium, land rights)?

```python
# In CapexLineDefinition for C.16.01/02/03:
source_type = CapexSourceType.EXCEL_REFERENCE   # initially
scope = CapexScope.PROJECT_RIGHTS                 # "project_rights"
amount_keur = 2739.0 / 2000.0 / 10000.0         # per Excel sub-line
affects_runtime = False                          # not yet wired
depreciation_category = None                    # TBD — deferred
tax_basis_category = None                       # TBD — deferred
mapping_note = "Project rights/acquisition premium — deferred wiring until tax treatment confirmed"
```

---

## Design Problem 4: M1–M18 Payment Schedule — Timing vs Total

### Current Problem

The CAPEX detail grid shows M1–M18 columns with payment schedule fractions, but:
- Source of the schedule is unclear (Excel reference? app construction profile? imported file?)
- The schedule role in IDC capitalization is not defined
- The relationship between monthly schedule and total CAPEX amount is ambiguous

**Key question:** The monthly payment schedule drives **construction IDC timing** (when CAPEX is spent determines when IDC accrues), but the schedule should NOT duplicate the total CAPEX amount (18 payment amounts that sum to the total, OR 18 fractions that multiply the total).

### Design Decision

**Define `CapexPaymentSchedule` as a separate schema object, detached from `CapexLineDefinition.amount_keur`.**

The schedule is a **timing profile only** — it defines when CAPEX is drawn, which feeds IDC capitalization and senior debt drawdown. It does NOT hold a separate CAPEX total.

```python
@dataclass
class CapexPaymentSchedule:
    schedule_type: str           # "excel_m1_m18" | "app_profile" | "static_reference" | "missing"
    periods: list[float]         # 18 fractions f₀..f₁₇ summing to 1.0
    amounts_keur: list[float] | None  # optional: explicit amounts; computed from total if None
    total_keur: float           # total CAPEX this schedule applies to
    source: str                 # "excel_capex_sheet" | "app_construction_profile" | etc.
    authority_status: str       # mirrors row authority_status
    notes: str

# Usage:
# schedule = CapexPaymentSchedule(
#     schedule_type="excel_m1_m18",
#     periods=[0.05, 0.08, 0.10, 0.10, 0.10, 0.10, 0.09, 0.08, 0.07,
#              0.06, 0.05, 0.04, 0.03, 0.02, 0.02, 0.01, 0.0, 0.0],
#     total_keur=13560.0,
#     source="excel_capex_sheet",
#     authority_status="excel_reference",
#     notes="18-month Excel TUHO payment schedule; drives IDC timing"
# )
```

### Schedule Bridge to Construction IDC

Later phases (Phase 21F):
```
CapexPaymentSchedule.periods (18 fractions)
    → construction monthly draw schedule (monthly CAPEX spend)
    → IDC capitalization (interest accrues on each month's draw)
    → Senior debt drawdown (senior debt drawn as CAPEX spent)
```

The schedule TYPE distinguishes:
- `"excel_m1_m18"` — from imported Excel, 18-month reference
- `"app_profile"` — from app construction profile (6-month TUHO, 12-month Oborovo)
- `"static_reference"` — hard-coded reference only (not user-editable)
- `"missing"` — no schedule data available

---

## Proposed Source Model

### CapexSourceType

```python
class CapexSourceType:
    """Origin/source classification for a CAPEX line."""

    EXCEL_REFERENCE = "excel_reference"
    # Taken from Excel. Not present in app runtime. Display-only reference.

    APP_INPUT = "app_input"
    # User-specified or app-template value. May or may not feed runtime.

    RUNTIME_COMPUTED = "runtime_computed"
    # Derived by model calculations (e.g., IDC, bank fees). Not user-editable directly.

    USER_OVERRIDE = "user_override"
    # User-edited override that replaces the prior value/source.

    IMPORTED_SCHEDULE = "imported_schedule"
    # From an imported file/schedule (e.g., project rights payment schedule).
```

### CapexScope

```python
class CapexScope:
    """Temporal/structural scope classification for a CAPEX line amount."""

    AGGREGATE_TOTAL = "aggregate_total"
    # Total across all periods/batches (e.g., total EPC contract over construction)

    COMPONENT = "component"
    # Sub-component of a larger category (not the full picture)

    PAYMENT_BATCH = "payment_batch"
    # One payment in a multi-batch schedule (e.g., one of 4 EPC batches)

    MONTHLY_SCHEDULE = "monthly_schedule"
    # Monthly M1-M18 distribution of a CAPEX total

    FEE_ONLY = "fee_only"
    # Fee or prerequisite only (e.g., GPA administrative fee), not the full scope

    PROJECT_RIGHTS = "project_rights"
    # Acquisition/premium/project rights cost — deferred until tax treatment confirmed

    FINANCING_COST = "financing_cost"
    # IDC, commitment fees, bank fees — financing overhead

    RESERVE_ACCOUNT = "reserve_account"
    # DSRA, MMRA, working capital reserve

    LAND = "land"
    # Land lease/acquisition — non-depreciable, tax-basis treatment differs

    GENERIC = "generic"
    # Default fallback — no specific scope classification
```

### CapexLineDefinition

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class CapexLineDefinition:
    """Schema record for one CAPEX line item (C.01–C.18 child row)."""

    code: str
    # e.g. "C", "C.02", "C.02.01" — hierarchical code

    label: str
    # Human-readable label

    parent_code: Optional[str]
    # Parent code: "C" for top-level categories, "C.02" for C.02 children, etc.

    source_type: str
    # One of CapexSourceType values

    scope: str
    # One of CapexScope values

    amount_keur: Optional[float]
    # Amount in kEUR. None if not_applicable or missing.

    affects_runtime: bool
    # True if this line feeds into the financial model's CFADS or debt sizing.

    runtime_field: Optional[str]
    # e.g. "capex.epc_contract.amount_keur" — the app CapexStructure field.
    # None if not yet mapped or if source_type=EXCEL_REFERENCE.

    depreciation_category: Optional[str]
    # e.g. "plant_machinery", "land", "rights", "intangible" — for tax depreciation.
    # None if not yet determined or not applicable.

    tax_basis_category: Optional[str]
    # e.g. "tax_shield_eligible", "land_rights_excluded" — for tax shield calculation.
    # None if not yet determined.

    funding_category: Optional[str]
    # e.g. "equity", "senior_debt", "mezzanine", "grant" — how this CAPEX is funded.
    # None if not yet determined.

    mapping_note: str
    # Human-readable explanation of scope, mismatch reason, deferred status, etc.

    monthly_schedule: Optional[CapexPaymentSchedule]
    # Payment schedule (M1-M18 fractions or amounts) if applicable.
```

### CapexPaymentSchedule

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class CapexPaymentSchedule:
    """Payment schedule for a CAPEX line — defines timing, not total amount."""

    schedule_type: str
    # "excel_m1_m18" | "app_profile" | "static_reference" | "missing"

    periods: tuple[float, ...]
    # 18 fractions f₀..f₁₇ summing to 1.0.
    # Used to distribute total_keur across 18 months.

    amounts_keur: Optional[tuple[float, ...]]
    # Optional explicit 18-month amounts.
    # If None: computed as [total_keur × p for p in periods].

    total_keur: float
    # The total CAPEX amount this schedule applies to.

    source: str
    # Human-readable source description: "excel_capex_sheet", "app_construction_profile", etc.

    authority_status: str
    # Mirrors the row authority_status: "excel_reference", "app_mapped", "backend_authoritative"

    notes: str
    # Explanation of the schedule source and intended use for IDC/capitalization.
```

### CapexInputSchemaDesign

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class CapexInputSchemaDesign:
    """Top-level container for all CAPEX line definitions in one project."""

    project_code: str
    # e.g. "TUHO", "OBOROVO"

    lines: tuple[CapexLineDefinition, ...]
    # All C.01–C.18 line definitions

    schedules: tuple[CapexPaymentSchedule, ...]
    # Payment schedules keyed to lines

    version: str
    # Schema version, e.g. "2026.05.28-v1"

    notes: str
    # Overall schema notes and any pending questions
```

---

## Proposed Migration / Backward Compatibility

- Existing `capex_items` and `capex_detail_items` remain **fully compatible** — no schema changes to those keys
- `CapexLineDefinition`, `CapexScope`, `CapexSourceType` are **additive** — new fields on the definition record, not changes to the row data shape
- `CapexPaymentSchedule` is a **new optional field** on `CapexLineDefinition` — backward-compatible (existing rows have `None`)
- No data migration required for existing records
- Existing rows that are `affects_runtime=True` continue to work without changes
- Phase 21E will wire new lines using the new schema fields without touching existing wired lines

---

## Future Connection Points

### CAPEX Detail Grid → Template Rendering
- `CapexLineDefinition` feeds template rendering: source_type badge, scope badge, mismatch display logic
- Scope `PAYMENT_BATCH` renders as a sub-row indented under parent `AGGREGATE_TOTAL` row
- Scope `FEE_ONLY` renders with explanatory note explaining it's a prerequisite fee

### Construction Schedule Bridge
- `CapexPaymentSchedule.periods` (18 fractions) → monthly construction draw schedule
- Monthly draw → IDC capitalization (interest accrues on each month's outstanding CAPEX)
- Senior debt drawdown: senior debt is drawn proportionally to construction spend

### Depreciation / Tax Basis
- `depreciation_category` field on each `CapexLineDefinition` feeds depreciation schedule
- `tax_basis_category` field feeds tax shield calculation
- Land (C.07) = non-depreciable → excluded from tax shield
- Rights/project rights = intangibles → depreciation treatment TBD

### Senior Debt Funding
- `funding_category` on each line: "senior_debt", "equity", "mezzanine", "grant"
- Maps CAPEX lines to funding sources for debt/equity split calculations

### Excel Export
- `CapexLineDefinition.code` + `scope` + `amount_keur` map to Excel CapEx sheet columns
- Export: write app values and schedule back to Excel reference sheet for comparison

---

## Guardrails and Deferred Items

1. **EPC aggregate vs payment batch:** Do NOT force app 52,800 == Excel 13,560. Display separately with different scopes.
2. **C.16 Project Rights:** Do NOT wire into `capex_items` or runtime totals until Phase 21E. Keep as `deferred`.
3. **M1–M18 schedule:** Schedule is timing-only, NOT a separate CAPEX total. Do not double-count.
4. **Grid GPA fee (C.03.01):** Show as `FEE_ONLY` scope, not compared to full `AGGREGATE_TOTAL` grid_connection.
5. **No runtime wiring in this design phase.** Design only.
6. **Depreciation category for project rights:** Not resolved — deferred to Phase 21E with accounting input.

---

## Recommended Implementation Phases After Design

### Phase 21E — CAPEX Input Wiring (First Tranche)
1. EPC: Add `aggregate_total` (app row) + `payment_batch` (Excel children) separation; update detail grid display logic
2. Grid C.03: Add GPA fee sub-row (`FEE_ONLY` scope)
3. Update scope badge display: `≠scp` for `scope_mismatch`, no badge for legitimate scope differences

### Phase 21E or 21F — CAPEX Input Wiring (Second Tranche)
4. C.16 Project Rights: Add schema bucket, clarify accounting treatment with accounting input
5. M1–M18 schedule → construction draw schedule bridge

### Phase 21F — CAPEX Detail Grid Editing
6. Enable user editing for `app_mapped` rows via the CAPEX grid (C.13 Contingencies first)
7. Add row-level validation using `CapexLineDefinition` metadata

---

## Files in This Phase

| File | Purpose |
|---|---|
| `docs/phase21d_capex_source_model_input_schema_design.md` | Design document (this file) |
| `app/domain/capex/source_model.py` | Isolated schema stub dataclasses |
| `tests/test_phase21d_capex_source_model_schema_design.py` | Validation tests |

**No runtime model code changed in this phase.**
