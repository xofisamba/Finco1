"""Distribution accounting policy for the dividend accounting layer.

Controls whether the WHT, legal reserve, and accounting-cap second pass
runs in the shareholder waterfall model.

Authority:
    Projects with SOURCE_PROVEN authority have had their dividend accounting
    formulas traced to a workbook source. Projects without this policy
    preserve frozen G2C semantics (gross == net == legal_equity_distribution).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class DistributionAccountingAuthority(str, Enum):
    UNRESOLVED = "UNRESOLVED"
    GENERIC_FINCO_POLICY = "GENERIC_FINCO_POLICY"
    SOURCE_PROVEN = "SOURCE_PROVEN"


@dataclass(frozen=True)
class DistributionAccountingPolicy:
    """Authority for the dividend accounting layer (WHT, legal reserve, accounting cap)."""
    enabled: bool = False
    authority: DistributionAccountingAuthority = DistributionAccountingAuthority.UNRESOLVED
    dividend_wht_rate: float = 0.0        # e.g. 0.05 for Oborovo, 0.0 for TUHO
    legal_reserve_cap_fraction: float = 0.10  # default 10%
