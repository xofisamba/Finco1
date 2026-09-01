# Upstream: Book Depreciable Asset Basis Authority

**Status**: `BOOK_DEPRECIABLE_ASSET_BASIS_UPSTREAM_DELIVERED`
**Branch**: `upstream-book-depreciable-asset-basis`
**Base**: `main` @ `c5d91ddf`
**Downstream blocker resolved for**: Phase C3 `BOOK_DEPRECIABLE_ASSET_BASIS_UPSTREAM_REQUIRED`

---

## Purpose

This upstream PR defines one canonical typed contract — `BookDepreciableAssetBasis` /
`BookDepreciableAssetComponent` — that represents the complete set of asset components
entering the book straight-line depreciation schedule at COD.

Prior to this PR, the book depreciable basis existed implicitly as scalar financing-cost
fields on `CapexStructure` (populated by `apply_capitalized_financing_costs`) and
recovered by `CapexStructure.book_depreciable_capex_items()`. That implicit path is
economically correct but lacks:
- A typed, auditable contract downstream consumers can interrogate
- Explicit provenance linking each component to its canonical source
- The capitalized IDC / raw IDC distinction (required for TUHO terminal IDC exclusion)
- A single builder function free from project-identity dispatch

---

## Canonical Causal Chain

There are two distinct basis representations. They are economically identical but serve different roles.

### A. Iterative Economic Production Path (drives PR-9 convergence)

```
each PR-9 outer iteration:
  Stage B2 provisional capitalized financing costs
    ↓
  apply_capitalized_financing_costs(orig_capex, ...)
    ↓
  updated CapexStructure (IDC / fee / VAT fields populated)
    ↓
  from_project_inputs(inner_inputs)    ← no book_basis kwarg; uses CapexStructure path
    ↓
  build_book_depreciable_asset_basis(updated_capex)
    ↓
  DepreciationInput.book_capex_items_for_depreciation
    ↓
  OperatingSchedules.book_depreciation_keur
    ↓
  tax / CFADS / Senior / SHL → next outer iteration
```

### B. Final Typed Downstream Handoff (after convergence)

```
orig_capex
  +
final ConstructionFinancingResult  (post-convergence; strict verification run)
  ↓
build_book_depreciable_asset_basis(orig_capex, construction_financing_result)
  ↓
BookDepreciableAssetBasis  (canonical typed contract)
  ↓
ProjectFinancingResult.book_depreciable_asset_basis  → downstream C3 / audit consumers
```

The final typed basis does **not** feed back into the PR-9 iteration loop. It is a downstream
handoff built once after convergence. Its economic equivalence to the iterative basis is proven
by Correction C (see below).

---

## Two Construction Paths

### Generic (Solar / Wind)

`construction_financing_result is None` → authority `GENERIC_CAPEX_STRUCTURE_BOOK_BASIS`

Components derived from `CapexStructure.book_depreciable_capex_items()` — the same
implicit path as before. All component provenance is `CAPEX_STRUCTURE_GENERIC`.
Economically identical to the pre-PR implicit path.

### Typed Construction (Oborovo / TUHO)

`construction_financing_result is not None` → authority `TYPED_CONSTRUCTION_FINANCING_RESULT_BOOK_BASIS`

| Component | Source field | Provenance |
|---|---|---|
| Hard CAPEX items | `CapexStructure.capex_items()` filtered by `is_depreciable` | `CAPEX_STRUCTURE_HARD_CAPEX` |
| Senior IDC | `sum(senior_idc_capitalized_uses_keur)` | `CONSTRUCTION_FINANCING_RESULT_SENIOR_IDC_CAPITALIZED_USES` |
| Commitment fees | `senior_commitment_fee_capitalized_keur` | `CONSTRUCTION_FINANCING_RESULT_SENIOR_COMMITMENT_FEE_CAPITALIZED` |
| Structuring fee | `sum(structuring_fee_keur)` | `CONSTRUCTION_FINANCING_RESULT_STRUCTURING_FEE` |
| VAT costs (combined) | `vat_idc_keur + vat_commitment_fee_keur` | `CONSTRUCTION_FINANCING_RESULT_VAT_CAPITALIZED` |

---

## Critical: Capitalized Uses vs Raw Accrual

### IDC

```
senior_idc_capitalized_uses_keur  ← basis component (capitalized uses)
                                    USED in BookDepreciableAssetBasis

senior_idc_accrual_keur           ← audit-only (raw accrual; may include terminal IDC)
                                    NEVER substituted for the above
```

For TUHO, `senior_idc_accrual_keur` includes terminal IDC (~217 kEUR) that accrues
after the last funded draw — this IDC is NOT capitalized as a use of funds and MUST
NOT enter the depreciable basis. `sum(senior_idc_capitalized_uses_keur)` is the
correct source.

### Commitment Fee

```
senior_commitment_fee_capitalized_keur  ← basis component (canonical capitalized scalar)
                                          Source: b2.capitalized_financing_costs.senior_commitment_fee_keur
                                          USED in BookDepreciableAssetBasis

senior_commitment_fee_accrual_keur      ← audit-only vector (raw period accruals)
                                          NEVER summed for the basis
```

`senior_commitment_fee_capitalized_keur` on `ConstructionFinancingResult` carries
the canonical scalar from `b2.capitalized_financing_costs.senior_commitment_fee_keur`,
which equals `sum(senior_fee_uses)` from Stage B2.

The builder enforces these distinctions by provenance.

---

## Correction C: Runtime-Truth and Economic-Basis Handshake Proof

Correction C proves that the final typed `BookDepreciableAssetBasis` is economically
identical to the iterative basis that drove the converged depreciation schedule.

### Behavioral depreciation equality (TUHO)

`test_tuho_final_typed_basis_reproduces_converged_book_depreciation` (Category 24):

```
final typed BookDepreciableAssetBasis
  → from_project_inputs(..., book_basis=final_typed_basis)
  → run_operating_model(...)
  → book_depreciation_keur  A

CapexStructure path (updated_capex after apply_capitalized_financing_costs)
  → from_project_inputs(inner_inputs)   # no book_basis
  → run_operating_model(...)
  → book_depreciation_keur  B

assert_allclose(A, B, rtol=1e-9, atol=1e-6)   ← passes
```

### Component handshake (TUHO)

`test_tuho_basis_component_accounting_identity` (Category 24):

| Component | Typed basis source | CFR source field |
|---|---|---|
| Hard depreciable CAPEX | components with provenance `CAPEX_STRUCTURE_HARD_CAPEX` | `CapexStructure.capex_items()` filtered `is_depreciable` |
| Capitalized Senior IDC | provenance `CONSTRUCTION_FINANCING_RESULT_SENIOR_IDC_CAPITALIZED_USES` | `sum(senior_idc_capitalized_uses_keur)` |
| Capitalized commitment fee | provenance `CONSTRUCTION_FINANCING_RESULT_SENIOR_COMMITMENT_FEE_CAPITALIZED` | `senior_commitment_fee_capitalized_keur` |
| Structuring fee | provenance `CONSTRUCTION_FINANCING_RESULT_STRUCTURING_FEE` | `sum(structuring_fee_keur)` |
| VAT financing costs | provenance `CONSTRUCTION_FINANCING_RESULT_VAT_CAPITALIZED` | `vat_idc_keur + vat_commitment_fee_keur` |

Financing components (IDC + fee + structuring + VAT) sum to the CFR total with **no residual
component and no balancing plug**.

---

## Economic Neutrality Proof

At PR-9 convergence, the following identity holds by the outer fixed-point invariant:

```
sum(senior_idc_capitalized_uses_keur)           == CapexStructure.idc_keur  (after apply_cap_fin_costs)
senior_commitment_fee_capitalized_keur           == CapexStructure.commitment_fees_keur
sum(structuring_fee_keur)                        == CapexStructure.bank_fees_keur
vat_idc_keur + vat_commitment_fee_keur           == CapexStructure.vat_costs_keur
```

The typed construction basis therefore produces identical depreciation economics to
the implicit `CapexStructure.book_depreciable_capex_items()` path. The economic delta
is zero. Verified by `TestGenericPathEconomicIdentity` in the test suite.

---

## PR-9 Fixed-Point Causality

The PR-9 outer fixed-point loop (in `financial_engine/financing/project.py`) runs
an iterative economic basis through the `CapexStructure` path on every outer
iteration:

```
outer iteration k:
  run_stage_b2_provisional(runtime_cfg)
    → CapitalizedFinancingCosts
  apply_capitalized_financing_costs(orig_capex, financing_costs)
    → updated_capex (CapexStructure with IDC/fee/VAT fields populated)
  replace(project_inputs, capex=updated_capex)
    → inner run_project_financing_model(inner_inputs, ...)
      → from_project_inputs(inner_inputs)          # no book_basis; uses CapexStructure path
        → DepreciationInput.book_capex_items_for_depreciation
          → run_operating_model → book_depreciation_keur
          → tax / CFADS / Senior / SHL
      → converged Senior + SHL for iteration k
  check outer_residual; loop until ≤ tolerance
```

After outer convergence, a final strict `run_stage_b2` verification run confirms
idempotence. The final typed `BookDepreciableAssetBasis` is then built **once**
from `orig_capex + final ConstructionFinancingResult` and exposed on
`ProjectFinancingResult.book_depreciable_asset_basis` for downstream and audit use.

**Two representations — one economics:**

| Representation | When built | Who uses it |
|---|---|---|
| Iterative economic basis (via `updated_capex` CapexStructure) | Each outer iteration | Inner operating model → depreciation → tax/CFADS/Senior/SHL → convergence |
| Final typed `BookDepreciableAssetBasis` (from `orig_capex + final CFR`) | Once, after convergence | Downstream consumers, audit, C3 financial statements |

These two representations are economically identical — proven by the
economic-neutrality identity (see below). The final typed basis does not feed
back into the iteration loop and does not affect convergence; it is a downstream
handoff, not a causal input to the fixed point.

---

## SHL and DSRA Exclusion

SHL PIK is on `FinancingStructure`, not `CapexStructure`, and its book/tax treatment
is OPEN per Phase C3 documentation. DSRA is a restricted current asset. Neither
enters the basis.

---

## Files Changed

| File | Change |
|---|---|
| `finco_core/inputs/book_depreciable_asset_basis.py` | NEW — typed contract |
| `financial_engine/book_basis.py` | NEW — canonical builder |
| `financial_engine/financing/contracts.py` | `ProjectFinancingResult.book_depreciable_asset_basis` field added |
| `financial_engine/financing/project.py` | (1) Iterative economic basis via `updated_capex` CapexStructure each outer iteration; (2) final typed CFR-based `BookDepreciableAssetBasis` built once after convergence for downstream/audit use |
| `financial_engine/adapters/project_inputs.py` | `from_project_inputs` accepts `book_basis` kwarg |
| `finco_core/inputs/__init__.py` | Re-export new types |
| `tests/test_upstream_book_depreciable_asset_basis.py` | NEW — 25 test categories (76 tests) |

---

## Governance Confirmations

- No `if project == "TUHO"`, no project-code dispatch, no identity whitelist
- No source workbook vectors in runtime
- No frozen expected basis, no target-fitting delta, no balancing plug
- `senior_idc_accrual_keur` is NOT used as the IDC basis component
- `senior_commitment_fee_accrual_keur` is NOT used as the fee basis component; `senior_commitment_fee_capitalized_keur` is used
- No import of `financial_engine.financial_statements.*` in new upstream files
- C1/C2 economics unchanged — `TestGenericPathEconomicIdentity` verifies
- PR #964 not modified, not merged
- PR #938 not modified
- `git diff --check` clean

---

## Remaining C3 Blockers (unchanged)

```
CASH_RESERVE_INTEREST_UPSTREAM_REQUIRED
FINANCING_INCOME_AUTHORITY_UNAVAILABLE
LEGAL_RESERVE_AUTHORITY_UNAVAILABLE
UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE
```

These are NOT addressed in this PR.
