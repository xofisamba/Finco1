"""financial_engine.shl.construction — SHL construction-period PIK calculator (Fix 2 C3B3FIX2A).

Pure computation module. No project-name or project-code dispatch.
No imports from app, finco_core waterfall, or any production runtime.

SHL construction PIK is the interest that accretes into the SHL liability balance
during the construction phase (before COD). It is distinct from operating-period
PIK, which is computed by the SHL period engine (financial_engine.shl.engine).

Two methods are supported:

SIMPLE:
    PIK = principal × annual_rate × construction_day_count_fraction
    Linear approximation. Default for all existing Generic Solar/Wind/Oborovo
    projects (construction_day_count_fraction = 0, so PIK = 0 for those).

COMPOUND_PERIODIC:
    PIK = principal × ((1 + annual_rate) ^ construction_day_count_fraction − 1)
    Exponential accrual over the full construction period.
    KUPI source workbook uses this convention.

Source-evidence values (Fix 2 derivation record, not production inputs):
    KUPI source SHL basis : 68_152.996 kEUR
    Finco SHL basis       : 79_595.855 kEUR
    Annual rate           : 0.08 (8%)
    Construction fraction : 2.0 years
    COMPOUND − SIMPLE delta (source basis) : +436.179 kEUR
    COMPOUND − SIMPLE delta (Finco basis)  : +509.413 kEUR
    (CROSS_BASIS_SHL_PIK_DIFFERENCE = +1_394.678 kEUR is NOT the pure method delta.)
"""
from __future__ import annotations

import math

from finco_core.inputs._models import ShlConstructionInterestMethod


def compute_shl_construction_pik_keur(
    shl_cash_principal_keur: float,
    annual_rate: float,
    construction_day_count_fraction: float,
    method: ShlConstructionInterestMethod,
) -> float:
    """Return SHL construction PIK in kEUR for the given method.

    Parameters
    ----------
    shl_cash_principal_keur:
        Derived SHL cash principal at Financial Close. Must be >= 0.
    annual_rate:
        Annual SHL interest rate (e.g. 0.08 for 8%). Must be >= 0 and finite.
    construction_day_count_fraction:
        Construction period expressed as a year-fraction (e.g. 2.0 for 24 months).
        Must be >= 0 and finite. Zero yields zero PIK for both methods.
    method:
        ShlConstructionInterestMethod.SIMPLE or COMPOUND_PERIODIC.

    Returns
    -------
    float
        SHL PIK accreted during construction (kEUR). Always >= 0.

    Raises
    ------
    ValueError
        If any input violates domain constraints.
    """
    if not math.isfinite(shl_cash_principal_keur):
        raise ValueError(f"shl_cash_principal_keur must be finite, got {shl_cash_principal_keur!r}")
    if shl_cash_principal_keur < 0.0:
        raise ValueError(f"shl_cash_principal_keur must be >= 0, got {shl_cash_principal_keur!r}")
    if not math.isfinite(annual_rate):
        raise ValueError(f"annual_rate must be finite, got {annual_rate!r}")
    if annual_rate < 0.0:
        raise ValueError(f"annual_rate must be >= 0, got {annual_rate!r}")
    if not math.isfinite(construction_day_count_fraction):
        raise ValueError(f"construction_day_count_fraction must be finite, got {construction_day_count_fraction!r}")
    if construction_day_count_fraction < 0.0:
        raise ValueError(f"construction_day_count_fraction must be >= 0, got {construction_day_count_fraction!r}")

    if construction_day_count_fraction == 0.0 or shl_cash_principal_keur == 0.0:
        return 0.0

    if method == ShlConstructionInterestMethod.SIMPLE:
        return shl_cash_principal_keur * annual_rate * construction_day_count_fraction
    elif method == ShlConstructionInterestMethod.COMPOUND_PERIODIC:
        return shl_cash_principal_keur * ((1.0 + annual_rate) ** construction_day_count_fraction - 1.0)
    else:
        raise ValueError(
            f"compute_shl_construction_pik_keur: unsupported method {method!r}. "
            "Only SIMPLE and COMPOUND_PERIODIC are supported."
        )
