# Upstream: Book Depreciable Asset Basis Authority

**Status**: `BOOK_DEPRECIABLE_ASSET_BASIS_UPSTREAM_CORRECTION_A_IN_PROGRESS`
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

```
ProjectInputs.capex (hard CAPEX items)
  +
ConstructionFinancingResult (converged; from PR-9 outer fixed-point)
  |
  ▼
build_book_depreciable_asset_basis(capex_structure, construction_financing_result)
  |
  ▼
BookDepreciableAssetBasis (canonical typed contract)
  |
  ├─▶ ProjectFinancingResult.book_depreciable_asset_basis  (downstream handoff)
  |
  └─▶ from_project_inputs(inputs, book_basis=basis)
        |
        ▼
      DepreciationInput.book_capex_items_for_depreciation
        |
        ▼
      OperatingSchedules.book_depreciation_keur → P&L → C3 financial statements
```

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

## PR-9 Fixed-Point Causality Preserved

The PR-9 outer fixed-point loop (in `financial_engine/financing/project.py`) is
unchanged. `apply_capitalized_financing_costs` still runs each iteration, correctly
updating `CapexStructure` fields. The canonical basis is built **only once**, after
convergence, from the final `ConstructionFinancingResult`. It is passed into
`from_project_inputs` as the `book_basis` argument, which feeds
`DepreciationInput.book_capex_items_for_depreciation`. The basis does not
participate in the iteration loop and does not affect convergence.

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
| `financial_engine/financing/project.py` | Build basis after convergence; pass to result |
| `financial_engine/adapters/project_inputs.py` | `from_project_inputs` accepts `book_basis` kwarg |
| `finco_core/inputs/__init__.py` | Re-export new types |
| `tests/test_upstream_book_depreciable_asset_basis.py` | NEW — 23 test categories |

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
