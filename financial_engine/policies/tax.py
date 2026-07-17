"""financial_engine.policies.tax — TaxPolicy structural contract.

Preparatory only for Phase 2B. No tax calculation performed here.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaxPolicy:
    """Structural contract for a jurisdiction's tax policy.

    Phase 2B will implement actual tax calculations using this contract.
    Phase 2A does not consume this type.
    """
    policy_id: str
    corporate_rate: float
    loss_carryforward_years: int
    tax_depreciation_basis: str
    atad_applies: bool
