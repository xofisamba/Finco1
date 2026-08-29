"""Typed downstream valuation and lender-coverage input authority."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class DiscountConvention(str, Enum):
    """Supported canonical dated discount convention."""

    ACT_365_FIXED = "ACT_365_FIXED"


class ValuationDatePolicy(str, Enum):
    """Authority for the date from which Project cash flows are discounted."""

    EXPLICIT_DATE = "EXPLICIT_DATE"
    FIRST_PROJECT_CASHFLOW_DATE = "FIRST_PROJECT_CASHFLOW_DATE"


class CoverageCfadsCase(str, Enum):
    """Canonical lender cash-flow case selected by an explicit policy."""

    BASE = "BASE"
    BANK = "BANK"


class CoverageCalculationDatePolicy(str, Enum):
    """Supported coverage measurement boundary."""

    FIRST_SENIOR_PERIOD_OPENING = "FIRST_SENIOR_PERIOD_OPENING"


@dataclass(frozen=True)
class ProjectValuationPolicy:
    """Explicit Project NPV authority; never inferred from financing terms."""

    annual_discount_rate: float | None
    valuation_date_policy: ValuationDatePolicy
    discount_convention: DiscountConvention
    authority_label: str
    explicit_valuation_date: date | None = None


@dataclass(frozen=True)
class DebtCoverageValuationPolicy:
    """Explicit LLCR/PLCR rate, case and calculation-boundary authority."""

    annual_discount_rate: float | None
    cfads_case: CoverageCfadsCase | None
    calculation_date_policy: CoverageCalculationDatePolicy
    discount_convention: DiscountConvention
    authority_label: str


@dataclass(frozen=True)
class ValuationPolicies:
    """Optional C2 policies attached to typed ProjectInputs."""

    project: ProjectValuationPolicy | None = None
    coverage: DebtCoverageValuationPolicy | None = None
