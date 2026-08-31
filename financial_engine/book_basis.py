"""financial_engine.book_basis — Canonical builder for BookDepreciableAssetBasis.

One function, two paths:

  Generic (Solar / Wind, construction_financing_result is None):
      Converts CapexStructure.book_depreciable_capex_items() directly to
      BookDepreciableAssetComponent entries. Economically identical to the
      current implicit CapexStructure path.

  Typed construction (Oborovo / TUHO, construction_financing_result is not None):
      Hard CAPEX from CapexStructure.capex_items() (filtered by is_depreciable).
      Financing components from ConstructionFinancingResult:
          IDC    — sum(senior_idc_capitalized_uses_keur)   (NOT senior_idc_accrual_keur)
          Fee    — sum(senior_commitment_fee_accrual_keur)
          Struct — sum(structuring_fee_keur)
          VAT    — vat_idc_keur + vat_commitment_fee_keur

Useful-life evidence (Oborovo Inputs sheet, MANUAL_WORKBOOK_SOURCE_EVIDENCE,
confirmed 2026-07-22): IDC, commitment fees, bank fees → 12 years; VAT costs → 20 years.

No project-code dispatch. No project-name dispatch. No identity whitelist.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from finco_core.inputs.book_depreciable_asset_basis import (
    BookDepreciableAssetBasis,
    BookDepreciableAssetComponent,
)

if TYPE_CHECKING:
    from finco_core.inputs._models import CapexStructure
    from financial_engine.financing.contracts import ConstructionFinancingResult

_GENERIC_AUTHORITY = "GENERIC_CAPEX_STRUCTURE_BOOK_BASIS"
_TYPED_AUTHORITY = "TYPED_CONSTRUCTION_FINANCING_RESULT_BOOK_BASIS"

_PROV_GENERIC = "CAPEX_STRUCTURE_GENERIC"
_PROV_HARD_CAPEX = "CAPEX_STRUCTURE_HARD_CAPEX"
_PROV_IDC = "CONSTRUCTION_FINANCING_RESULT_SENIOR_IDC_CAPITALIZED_USES"
_PROV_FEE = "CONSTRUCTION_FINANCING_RESULT_SENIOR_COMMITMENT_FEE_ACCRUAL"
_PROV_STRUCT = "CONSTRUCTION_FINANCING_RESULT_STRUCTURING_FEE"
_PROV_VAT = "CONSTRUCTION_FINANCING_RESULT_VAT_CAPITALIZED"


def build_book_depreciable_asset_basis(
    capex_structure: "CapexStructure",
    construction_financing_result: "ConstructionFinancingResult | None" = None,
) -> BookDepreciableAssetBasis:
    """Build the canonical book depreciable asset basis for one project.

    Args:
        capex_structure: The converged CapexStructure (with financing-cost fields
            populated by apply_capitalized_financing_costs for the typed path, or
            directly from project inputs for the generic path).
        construction_financing_result: The converged ConstructionFinancingResult
            from the PR-9 outer fixed-point. None for Solar / Wind (generic path).

    Returns:
        BookDepreciableAssetBasis with one component per depreciable line item.
    """
    if construction_financing_result is not None:
        return _build_typed_construction_basis(capex_structure, construction_financing_result)
    return _build_generic_basis(capex_structure)


def _build_generic_basis(capex_structure: "CapexStructure") -> BookDepreciableAssetBasis:
    components = tuple(
        BookDepreciableAssetComponent(
            code=item.name,
            name=item.name,
            amount_keur=item.amount_keur,
            asset_class_code=item.asset_class.value,
            useful_life_override=item.useful_life_override,
            provenance=_PROV_GENERIC,
        )
        for item in capex_structure.book_depreciable_capex_items()
        if item.amount_keur != 0.0
    )
    return BookDepreciableAssetBasis(
        components=components,
        authority=_GENERIC_AUTHORITY,
    )


def _build_typed_construction_basis(
    capex_structure: "CapexStructure",
    cfr: "ConstructionFinancingResult",
) -> BookDepreciableAssetBasis:
    components: list[BookDepreciableAssetComponent] = []

    # Hard CAPEX: source-proven depreciable items
    for item in capex_structure.capex_items():
        if not item.is_depreciable:
            continue
        if item.amount_keur == 0.0:
            continue
        components.append(BookDepreciableAssetComponent(
            code=item.name,
            name=item.name,
            amount_keur=item.amount_keur,
            asset_class_code=item.asset_class.value,
            useful_life_override=item.useful_life_override,
            provenance=_PROV_HARD_CAPEX,
        ))

    # Capitalized Senior IDC — use capitalized-USE vector, not raw accrual.
    # Terminal IDC (accures after last funded draw) is excluded from capitalized uses.
    idc = sum(cfr.senior_idc_capitalized_uses_keur)
    if idc > 0.0:
        components.append(BookDepreciableAssetComponent(
            code="senior_idc",
            name="IDC (Interest During Construction)",
            amount_keur=idc,
            asset_class_code="financial_costs",
            useful_life_override=12,
            provenance=_PROV_IDC,
        ))

    # Senior commitment fees (accrual == capitalized-use total at convergence)
    commitment_fee = sum(cfr.senior_commitment_fee_accrual_keur)
    if commitment_fee > 0.0:
        components.append(BookDepreciableAssetComponent(
            code="senior_commitment_fee",
            name="Commitment Fees",
            amount_keur=commitment_fee,
            asset_class_code="financial_costs",
            useful_life_override=12,
            provenance=_PROV_FEE,
        ))

    # Structuring / arrangement fee
    structuring = sum(cfr.structuring_fee_keur)
    if structuring > 0.0:
        components.append(BookDepreciableAssetComponent(
            code="structuring_fee",
            name="Bank Fees",
            amount_keur=structuring,
            asset_class_code="financial_costs",
            useful_life_override=12,
            provenance=_PROV_STRUCT,
        ))

    # VAT-facility financing costs (combined; evidence: dep_vat_keur, 20-year useful life)
    vat = cfr.vat_idc_keur + cfr.vat_commitment_fee_keur
    if vat > 0.0:
        components.append(BookDepreciableAssetComponent(
            code="vat_costs",
            name="VAT Costs",
            amount_keur=vat,
            asset_class_code="financial_costs",
            useful_life_override=20,
            provenance=_PROV_VAT,
        ))

    return BookDepreciableAssetBasis(
        components=tuple(components),
        authority=_TYPED_AUTHORITY,
    )
