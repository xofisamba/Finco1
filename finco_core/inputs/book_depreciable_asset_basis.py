"""finco_core.inputs.book_depreciable_asset_basis — Canonical typed contract for the book
depreciable asset basis consumed by the clean book depreciation engine.

Authority: BOOK_DEPRECIABLE_ASSET_BASIS_UPSTREAM_REQUIRED (see Phase C3 authority doc).

Each project run produces one BookDepreciableAssetBasis instance carrying all components
that enter the straight-line book depreciation schedule. The two construction paths are:

  Generic (Solar / Wind): basis derived from CapexStructure.book_depreciable_capex_items()
      using the financing-cost fields already held on CapexStructure.

  Typed construction (Oborovo / TUHO): basis derived directly from ConstructionFinancingResult
      — hard CAPEX from CapexStructure.capex_items(), financing components from the
      canonically resolved ConstructionFinancingResult vectors. This is the authoritative
      source for the capitalized IDC distinction (sum of capitalized USES, not raw accrual).

SHL PIK and DSRA are excluded by policy (not CAPEX, not depreciable assets).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class BookDepreciableAssetComponent:
    """One depreciable asset component within the book basis.

    Each component maps directly to one CapexItemForDep entry when the basis
    is wired into DepreciationInput.book_capex_items_for_depreciation.
    """
    code: str
    name: str
    amount_keur: float
    asset_class_code: str
    useful_life_override: Optional[int]
    provenance: str


@dataclass(frozen=True)
class BookDepreciableAssetBasis:
    """Complete canonical book depreciable asset basis for one project at COD.

    Produced after PR-9 outer fixed-point convergence. Carries all components
    whose amounts will enter the straight-line book depreciation schedule over
    the operating life of the asset.

    authority values:
      "GENERIC_CAPEX_STRUCTURE_BOOK_BASIS"
          — generic path (Solar / Wind); CapexStructure fields are the source.
      "TYPED_CONSTRUCTION_FINANCING_RESULT_BOOK_BASIS"
          — typed construction path (Oborovo / TUHO); ConstructionFinancingResult
            is the authoritative source for financing-cost components.
    """
    components: tuple[BookDepreciableAssetComponent, ...]
    authority: str

    @property
    def total_keur(self) -> float:
        return sum(c.amount_keur for c in self.components)
