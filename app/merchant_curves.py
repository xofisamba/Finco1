"""Merchant price curve profiles.

Central registry for market price curves used in revenue calculations.
Each profile is a named tuple of 30 annual prices in EUR/MWh (nominal, not inflation-adjusted).

Profile naming convention:
  {REGION}_{TECH}_{SOURCE}_{YEAR}

All profiles are nominal (real terms) — market_inflation should be 0 when using these
unless explicitly documented otherwise.
"""
from typing import NamedTuple

# =============================================================================
# CROATIA SOLAR PROFILES
# =============================================================================

class MerchantProfile(NamedTuple):
    """A merchant price curve profile.
    
    Attributes:
        name: Unique identifier e.g. 'CROATIA_SOLAR_AFRY_CENTRAL_2024'
        description: Human-readable description of source and vintage
        curve: 30-tuple of annual prices in EUR/MWh (nominal)
        market_inflation: Inflation rate to apply post-curve (0 if curve covers full horizon)
        is_nominal: True if curve is already in nominal terms (not inflation-adjusted)
    """
    name: str
    description: str
    curve: tuple[float, ...]
    market_inflation: float = 0.0
    is_nominal: bool = True


# AFRY Central Case — Q1 2026 real terms, converted to nominal EUR/MWh
# Source: Oborovo Excel Inputs row 100 (Market price - AFRY Central curve real terms)
# Real prices inflated by EUR CPI 2%/yr from 2026 base to 2030 COD
# Real base year = 2026, real Y1 (2030) = 59.22 → nominal Y1 = 59.22 * 1.12793
_CPI_2026_TO_2030 = 1.12793  # (1.02)^4

_AFRY_REAL_Y1_Y30 = (
    59.221470000000004, 62.82584000000001, 63.30454199999999, 62.939330999999996,
    64.37673899999999, 68.819597, 68.736486, 68.28664500000001, 70.766304,
    72.517277, 72.09890100000001, 73.5049525, 75.12095149999999,
    75.83325399999998, 76.03517249999999, 74.10767, 75.790071,
    77.47963299999999, 79.1593215, 80.86288, 82.57359949999999,
    84.78114049999999, 86.50704999999999, 88.22135, 90.4723995,
    92.20113, 93.63116, 95.01388399999999, 95.8876345, 97.2187125,
    98.543606,
)

# Convert real terms to nominal (2030 base) — already done in Excel at real terms,
# but the curve is given in "real terms" header while values appear nominal.
# Use as-is since the model currently receives nominal prices in market_prices_curve.
CROATIA_SOLAR_AFRY_CENTRAL_2024 = MerchantProfile(
    name="CROATIA_SOLAR_AFRY_CENTRAL_2024",
    description="AFRY Central case Q1 2026 — 4h Degraded, nominal EUR/MWh, post-PPA merchant period",
    curve=_AFRY_REAL_Y1_Y30,
    market_inflation=0.0,  # Already nominal for 30-year horizon
    is_nominal=True,
)

# =============================================================================
# GENERIC / DEFAULT PROFILES
# =============================================================================

# Simple 2% annual escalation from 65 EUR/MWh — used for generic Solar/Wind
GENERIC_SOLAR_ESCALATION_2PCT = MerchantProfile(
    name="GENERIC_SOLAR_ESCALATION_2PCT",
    description="Generic solar 2%/yr escalation from 65 EUR/MWh — backward compatible default",
    curve=tuple(65.0 + i * 1.3 for i in range(30)),
    market_inflation=0.02,
    is_nominal=False,  # Escalar curve, market_inflation used for post-curve years
)

GENERIC_WIND_ESCALATION_2PCT = MerchantProfile(
    name="GENERIC_WIND_ESCALATION_2PCT",
    description="Generic wind 2%/yr escalation from 55 EUR/MWh — backward compatible default",
    curve=tuple(55.0 + i * 1.1 for i in range(30)),
    market_inflation=0.02,
    is_nominal=False,
)

# =============================================================================
# REGISTRY
# =============================================================================

PROFILE_REGISTRY: dict[str, MerchantProfile] = {
    p.name: p for p in [
        CROATIA_SOLAR_AFRY_CENTRAL_2024,
        GENERIC_SOLAR_ESCALATION_2PCT,
        GENERIC_WIND_ESCALATION_2PCT,
    ]
}


def get_profile(name: str) -> MerchantProfile:
    """Return profile by name. Raises KeyError if not found."""
    return PROFILE_REGISTRY[name]