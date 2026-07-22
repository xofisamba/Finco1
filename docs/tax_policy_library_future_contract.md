# Tax Policy Library — Future Architecture Contract

**Status**: ARCHITECTURE ONLY — NOT IMPLEMENTED.
No persistence, roles, approval workflow, or UI is implemented in Stage B1.
This document is a forward contract so current engine architecture does not block future implementation.

**Predecessor**: Stage B1 (`recon-fix-03-stageb1-book-depreciation`, PR #905).
**Reviewed**: 2026-07-22.

---

## 1. Engine Capability vs Policy Data Separation

The engine exposes **capabilities**; country/jurisdiction **policy data** is separate.

### Level 1 — Engine Capabilities

The engine knows HOW to perform a computation. Examples:

| Capability | Engine enum/flag | Status |
|------------|-----------------|--------|
| Tax depreciation mode | `TaxDepreciationMode` | Partial (BOOK_BASED_PERCENTAGE implemented; STATUTORY/CUSTOM reserved) |
| CIT calculation | `compute_period_tax()` | Implemented |
| Loss carryforward | `TaxParams.loss_carryforward_years/cap` | Implemented |
| ATAD/EBITDA interest limitation | `TaxParams.atad_ebitda_limit` | Implemented |
| Thin capitalisation | `TaxParams.thin_cap_de_ratio` | Implemented |
| WHT (dividends, SHL interest) | `TaxParams.wht_*` | Implemented |
| VAT facility | Stage B2 | Pending |

### Level 2 — Versioned Country / Jurisdiction Tax Policy Library

A **Tax Policy** is a versioned, structured record of a country's tax rules at a point in time.

Conceptual schema:

```
TaxPolicy:
  jurisdiction: str               # e.g. "HR" (Croatia), "ME" (Montenegro), "RS" (Serbia)
  sub_jurisdiction: str | None    # entity type, canton, etc.
  version: str                    # e.g. "2026.1"
  effective_from: date
  effective_to: date | None       # None = still current

  cit_rate: float                 # statutory CIT rate
  cit_rules: str | None           # free-text notes on special rules

  tax_depreciation_mode: TaxDepreciationMode
  tax_asset_groups: list[TaxAssetGroup]   # for STATUTORY_TAX_SCHEDULE
  tax_deductible_book_dep_pct: float      # for BOOK_BASED_PERCENTAGE

  loss_carryforward_years: int
  loss_carryforward_cap: float

  interest_deductibility: InterestDeductibilityPolicy  # ATAD / thin cap rules
  thin_cap_de_ratio: float | None

  wht_dividends: float
  wht_interest_to_sponsor: float
  wht_other: dict[str, float]

  vat_rate: float
  vat_applicable_categories: list[str]

  source_provenance: str          # e.g. "Croatian Tax Administration Act 2026, Art. 12"
  notes: str
```

Tax Asset Group (for STATUTORY_TAX_SCHEDULE):

```
TaxAssetGroup:
  group_id: str                   # e.g. "I", "II", "buildings"
  description: str
  method: str                     # "straight_line" | "declining_balance" | ...
  rate_or_life: float             # statutory rate (%) or life (years) depending on method
  eligible_asset_classes: list[str]
```

### Level 3 — Project Tax Configuration

A project:

1. **Selects/pins** a Tax Policy version (e.g. `"HR/2026.1"`).
2. **Inherits** all policy assumptions from that version.
3. May apply **explicit project overrides** for specific fields.
4. Each override must carry a `reason` and `source_provenance`.

Conceptual schema:

```
ProjectTaxConfig:
  pinned_policy_version: str           # e.g. "HR/2026.1"
  overrides: list[TaxPolicyOverride]

TaxPolicyOverride:
  field: str                           # e.g. "cit_rate"
  value: Any
  reason: str                          # why this project deviates from country policy
  source_provenance: str               # workbook reference, legal opinion, etc.
  approved_by: str | None              # future governance field
```

---

## 2. Effective Dates and Versioning

- Each `TaxPolicy` has `effective_from` / `effective_to` date range.
- Projects must pin a specific version, not `"latest"`, so financial models are reproducible.
- When legislation changes, a new policy version is created; existing pinned projects are unaffected.
- Version identifiers: `{jurisdiction}/{year}.{minor}` (e.g. `"HR/2026.1"`, `"ME/2026.1"`).

---

## 3. Tax Depreciation Modes

The `TaxDepreciationMode` engine capability has three states:

| Mode | Description | Engine Status |
|------|-------------|---------------|
| `BOOK_BASED_PERCENTAGE` | `tax_dep = book_dep × deductible_pct` | Implemented |
| `STATUTORY_TAX_SCHEDULE` | Independent asset-group schedule; lives/rates set by statute | Reserved — raises `NotImplementedError` |
| `CUSTOM_SCHEDULE` | Externally supplied period-by-period depreciation | Reserved — raises `NotImplementedError` |

The **policy library** (Level 2) specifies which mode applies to a jurisdiction.
The **engine** (Level 1) only knows how to execute a mode.
The **project config** (Level 3) may override the mode if project circumstances require it (with documented reason).

---

## 4. Asset-Group Mapping for Statutory Depreciation

When `STATUTORY_TAX_SCHEDULE` is implemented, the engine will:

1. Look up the project's pinned Tax Policy.
2. For each `CapexItem`, resolve its `tax_asset_class` to a `TaxAssetGroup`.
3. Apply the group's statutory method and rate/life.
4. Compute tax depreciation period-by-period, independent of book depreciation.

The `CapexItem.asset_class` field is the mapping key. Asset classes must be enumerated in the Tax Policy's `TaxAssetGroup` records.

---

## 5. Project Policy Pinning

```
ProjectInputs.tax: TaxParams
    → .tax_policy_version: str | None    # future field; currently None (compatibility mode)
    → .tax_depreciation_mode             # explicit current field
    → .tax_deductible_book_dep_pct       # explicit current field
```

When `tax_policy_version` is non-None (future), the engine resolves the full policy record
and uses it as the base; `TaxParams` fields then represent explicit project overrides only.

When `tax_policy_version` is None (current), the engine uses `TaxParams` fields directly
(compatibility mode — current behavior).

---

## 6. Current TaxParams Defaults: Compatibility, Not Global Rules

The current `TaxParams` defaults:

```python
tax_depreciation_mode: TaxDepreciationMode = TaxDepreciationMode.BOOK_BASED_PERCENTAGE
tax_deductible_book_dep_pct: float = 1.0
```

are **COMPATIBILITY DEFAULTS**, not a declaration that all countries or all projects use
100% book-based tax depreciation. These defaults preserve legacy behavior where tax dep
and book dep were numerically equal.

**Oborovo explicitly uses `BOOK_BASED_PERCENTAGE = 100%`** because the source workbook
calibration (P&L, no depreciation add-back in Fiscal Reintegration bridge) supports that
project policy. This is a project-specific fact, not a universal assumption.

Future projects must receive tax depreciation assumptions through:
- Selected versioned Tax Policy (Level 2)
- Plus project-level overrides (Level 3)

**Do not add further country-specific tax assumptions to `project_factories.py`.**

---

## 7. Source Provenance Requirements

Every tax assumption — whether in a Tax Policy record or a project override — must carry:

- `source_provenance: str` — the legal/workbook reference that justifies the value.
- `reviewed_date: date` — when the source was verified.
- `reviewer: str | None` — future governance field.

Acceptable source classes (future governance):
- Primary legislation / tax code
- Secondary regulation / implementing act
- Official tax authority guidance / circular
- Authoritative tax legal opinion or memorandum

Example schema (placeholder — no values are authoritative until source-reviewed and approved):

```
source_provenance: <AUTHORITATIVE_SOURCE_REQUIRED>
reviewed_date: <REVIEW_DATE_REQUIRED>
reviewer: <REVIEWER_IDENTITY_REQUIRED_WHEN_GOVERNANCE_IMPLEMENTED>
```

---

## 7a. Source Governance Rule (future enforcement)

**No Tax Policy value may become APPROVED or LOCKED unless it has ALL of the following**:

1. `source_provenance` — specific citation (legislation, regulation, or approved legal opinion)
2. `effective_from` date — when the rule took effect in the jurisdiction
3. `jurisdiction` — ISO country code or sub-jurisdiction identifier
4. `reviewed_date` — date the source was verified against the primary text
5. `reviewer` identity — when the governance role infrastructure is implemented

Tax values without these fields remain in DRAFT status only and must not be used in
production financial models.

This rule is a **future governance contract**. It is NOT enforced in Stage B1 or B2.

---

## 8. Future Review / Approve / Lock Lifecycle

Tax Policy records will follow a governance lifecycle. **NOT implemented in Stage B1.**

```
DRAFT → REVIEWED → APPROVED → LOCKED
```

| Status | Who can edit | Description |
|--------|-------------|-------------|
| DRAFT | Tax Editor | In preparation; not used in production models |
| REVIEWED | Tax Reviewer | Technically verified; may be used in draft projects |
| APPROVED | Tax Approver/Admin | Verified and approved; may be used in production models |
| LOCKED | (immutable) | Historical record; cannot be edited; new version must be created |

Future roles (not implemented):
- **Tax Editor**: creates/edits DRAFT policy records
- **Tax Reviewer**: moves DRAFT → REVIEWED
- **Tax Approver/Admin**: moves REVIEWED → APPROVED; locks superseded versions

These roles are an enterprise governance feature. Do NOT implement in Stage B1 or B2.

---

## 9. Future Workbook V2 Tax UI

The Workbook V2 Tax tab will expose:

**Header (per-project)**:
- Jurisdiction
- Selected Tax Policy version
- Effective date range
- Policy status (DRAFT / REVIEWED / APPROVED / LOCKED)

**Sections**:

| Section | Fields |
|---------|--------|
| Corporate Income Tax | Rate, rules summary |
| Tax Depreciation | Mode, deductible %, asset groups |
| Tax Losses | Carryforward years, cap |
| Interest Deductibility | ATAD EBITDA limit, thin cap ratio, safe harbour |
| Withholding Tax | Dividends, SHL interest, other |
| VAT | Rate, applicable categories |
| Project Overrides | Per-field override table |

**UI distinction — required**:

Each tax assumption must be displayed as either:

| Assumption | Country Policy | Project Value | Status |
|------------|---------------|---------------|--------|
| CIT rate | 10% | 10% | Inherited |
| Interest WHT | 5% | 0% | **Override** |

`Inherited` = value comes from pinned Tax Policy unchanged.
`Override` = project has explicitly overridden the policy value; reason and provenance must be visible.

Derived outputs (tax depreciation schedule, CIT charge, effective tax rate) must be
display-only — never editable primary inputs in the standard UI.

Do NOT implement this UI in Stage B1 or B2.

---

## 10. Migration Path from Current TaxParams / Project-Factory Calibration

| Current (Stage B1) | Future (Tax Policy Library) |
|--------------------|-----------------------------|
| `TaxParams.tax_depreciation_mode` (default `BOOK_BASED_PERCENTAGE`) | Inherited from pinned Tax Policy; `TaxParams` field becomes project override only |
| `TaxParams.tax_deductible_book_dep_pct = 1.0` (default) | Policy field; project overrides with documented reason |
| `TaxParams.corporate_rate = 0.10` (default) | Policy field |
| `TaxParams.loss_carryforward_years = 5` | Policy field |
| Project factories set tax params inline | Project factories pin a policy version; overrides only for project-specific deviations |

Migration is non-breaking: the `tax_policy_version = None` compatibility mode keeps all
current projects working without change. Migration to pinned policies can be done
project-by-project as policy records are created and approved.

---

## 11. Policy Record Structure — Generic Template (No Real Tax Values)

The following is a structural template only. It contains NO real tax rates or jurisdiction-specific
values. Actual policy records must be created by a Tax Editor with authoritative source citations
and approved by a Tax Approver before use in production models.

```
Tax Policy Template:
  jurisdiction: <ISO_COUNTRY_CODE_OR_SUB_JURISDICTION>
  sub_jurisdiction: <ENTITY_TYPE_OR_REGION_IF_APPLICABLE>
  version: "<JURISDICTION>/<YEAR>.<MINOR>"
  effective_from: <SOURCE_REQUIRED>
  effective_to: <SOURCE_REQUIRED_OR_NULL_IF_CURRENT>

  cit_rate: <SOURCE_REQUIRED>
  cit_rules: <SOURCE_REQUIRED>

  tax_depreciation_mode: <SOURCE_REQUIRED>   # BOOK_BASED_PERCENTAGE | STATUTORY_TAX_SCHEDULE | CUSTOM_SCHEDULE
  tax_asset_groups: <SOURCE_REQUIRED_FOR_STATUTORY_SCHEDULE>
  tax_deductible_book_dep_pct: <SOURCE_REQUIRED_FOR_BOOK_BASED>

  loss_carryforward_years: <SOURCE_REQUIRED>
  loss_carryforward_cap: <SOURCE_REQUIRED>

  wht_dividends: <SOURCE_REQUIRED>
  wht_interest_to_sponsor: <SOURCE_REQUIRED>

  vat_rate: <SOURCE_REQUIRED>

  source_provenance: <AUTHORITATIVE_SOURCE_REQUIRED>
  reviewed_date: <REVIEW_DATE_REQUIRED>
  reviewer: <REVIEWER_IDENTITY_REQUIRED_WHEN_GOVERNANCE_IMPLEMENTED>
```

**No country-specific tax values appear in this architecture document.** Values are only
introduced once a Tax Editor has produced a record with authoritative sources and a Tax Approver
has moved it to APPROVED status. Stage B1 contains no approved Tax Policy records.

---

## 12. Oborovo Tax Treatment: Project Calibration Source Truth

Oborovo currently uses:
- `tax_depreciation_mode = BOOK_BASED_PERCENTAGE`
- `tax_deductible_book_dep_pct = 1.0` (100%)

This is **PROJECT CALIBRATION SOURCE TRUTH** — the source workbook (reviewed 2026-07-22)
shows no depreciation add-back in the Fiscal Reintegration bridge, supporting 100%
deductibility for this specific project.

This is NOT a validated country Tax Policy Library record. It is:
- a project-level calibration assumption
- supported by source workbook evidence
- not yet validated against the primary tax legislation

Future migration path:
1. Tax Editor creates a jurisdictional Tax Policy record with authoritative sources
2. Tax Approver approves and locks the record
3. Oborovo project pins the approved policy version
4. Any deviation (e.g. if the project-specific rate differs from the standard policy) becomes
   an explicit project override with documented reason and source provenance
