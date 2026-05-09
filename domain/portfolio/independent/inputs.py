"""Phase 1 MVP: Independent SPV portfolio aggregation.

Architecture:
- Each SPV runs through the existing single-asset engine independently
- Results are preserved per-SPV and aggregated into summary metrics
- NO shared financing, NO pooled debt sculpting, NO cross-default enforcement

This module is NOT the pooled-financing portfolio path (see domain/portfolio/waterfall.py).
Phase 1 is opt-in via IndependentPortfolioInputs feature flag.

Strategic constraints (Phase 1):
- No HoldCo entity
- No SHL / intercompany flows
- No Sponsor IRR
- No monthly model frequency
- No cross-SPV cash pooling
- No retained earnings constraint
- DSRF: optional placeholder only, default disabled
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Re-export the canonical DSRFConfig from the pure engine module.
# inputs.py holds the portfolio-level schema; dsrf.py holds the engine.
from domain.portfolio.independent.dsrf import (
    DSRFConfig as _CanonicalDSRFConfig,
)


# Re-export for backward-compatible import from this module
DSRFConfig = _CanonicalDSRFConfig


@dataclass(frozen=True)
class IndependentPortfolioInputs:
    """Independent SPV portfolio — Phase 1 MVP.

    Each SPV runs independently through the existing calibrated single-asset engine.
    Results are aggregated into summary metrics.

    NO shared financing. NO pooled debt sculpting. NO cross-default.

    Usage:
        from domain.portfolio.independent import IndependentPortfolioInputs

        portfolio = IndependentPortfolioInputs(
            projects=(project1, project2, project3),
            portfolio_name="My Portfolio",
            dsrf=DSRFConfig(),  # optional, default disabled
        )
        result = run_independent_portfolio(portfolio)
    """
    # All projects must have unique codes (enforced at ProjectInputs level)
    projects: tuple["ProjectInputs", ...]  # forward reference, resolved at runtime
    portfolio_name: str = "Portfolio"

    # DSRF: optional, default None (disabled)
    dsrf: Optional[DSRFConfig] = None

    def __post_init__(self):
        if len(self.projects) < 1:
            raise ValueError("Portfolio must contain at least 1 project")
        codes = [p.info.code for p in self.projects]
        if len(set(codes)) != len(codes):
            raise ValueError(f"Project codes must be unique, got: {codes}")


# Phase 1 limitations — exported for documentation
PHASE1_LIMITATIONS = """
Phase 1 MVP Limitations:
- No HoldCo entity
- No SHL / intercompany flows
- No Sponsor IRR (placeholder only, not computed)
- No monthly model frequency
- No cross-SPV cash pooling
- No retained earnings constraint
- No portfolio-level debt sculpting (per-SPV debt only)
- DSRF: optional placeholder only, not integrated into calculations

Pooled Financing (domain/portfolio/waterfall.py) is experimental / Phase 2+:
- Shared financing with cross-default enforcement
- Portfolio-level debt sculpting from pooled CFADS
- Not enabled by default in Phase 1
""".strip()


__all__ = [
    "DSRFConfig",
    "IndependentPortfolioInputs",
    "PHASE1_LIMITATIONS",
]