"""Sponsor ↔ Project adapter.

Wires real project/SPV cashflow outputs into the sponsor runner so that
Oborovo/TUHO sponsor calibration can validate actual 60-period economics.

Pure deterministic wiring — no persistence coupling, no UI concerns.

Adapter responsibilities:
  1. Run the project waterfall for a given project factory.
  2. Extract `distribution_keur` (SPV-level cash available for sponsor
     distribution) as a tuple aligned to the SPV's semiannual period index.
  3. Build a `SponsorRunConfig` for LP/GP given the SPV capital structure.

The SPV capital structure is fixed per project:
  Oborovo Solar PV: LP 80% / GP 20%, total equity = 500 kEUR
  TUHO   Wind 1:    LP 80% / GP 20%, total equity = 500 kEUR

For both projects the LP/GP commitment split mirrors ownership (proportional).
The `available_cash_by_period` passed to the sponsor runner represents
FCF after senior debt service — i.e., the cash "free" to distribute to
the SPV equityholders (LP + GP) in each period.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Callable, Sequence
    from app.sponsor_runner import SponsorRunConfig


# ─── Constants for known project capital structures ───────────────────────────

OBOROVO_CAPITAL_STRUCTURE = {
    "lp_commitment_keur": 400.0,   # 80% × 500 kEUR
    "gp_commitment_keur": 100.0,   # 20% × 500 kEUR
    "ownership": {"LP-1": 0.80, "GP-1": 0.20},
}

TUHO_CAPITAL_STRUCTURE = {
    "lp_commitment_keur": 400.0,   # 80% × 500 kEUR
    "gp_commitment_keur": 100.0,   # 20% × 500 kEUR
    "ownership": {"LP-1": 0.80, "GP-1": 0.20},
}


# ─── Adapter result ───────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class ProjectToSponsorAdapter:
    """Result of wiring a project model into the sponsor runner."""

    #: SponsorRunConfig ready to pass to run_sponsor_waterfall.
    sponsor_config: SponsorRunConfig
    #: Raw SPV distribution timeline used to build the config.
    spv_distributions_keur: tuple[float, ...]
    #: Total SPV distributions across all periods.
    total_spv_distributions_keur: float
    #: Project equity IRR (from the project waterfall).
    project_equity_irr: float
    #: SPV sponsor IRR (blended LP+GP IRR, from project waterfall).
    spv_sponsor_irr: float
    #: Golden reference total distributions (None if not yet calibrated).
    golden_total_distributions_keur: float | None
    #: Golden reference LP equity IRR (None if not yet calibrated).
    golden_lp_equity_irr: float | None


# ─── Adapter builders ─────────────────────────────────────────────────────────

def build_oborovo_adapter(
    project_factory: Callable[[], Any] | None = None,
    golden_lp_equity_irr: float | None = 0.106,
    golden_total_distributions_keur: float | None = 104918.0,
) -> ProjectToSponsorAdapter:
    """Build Oborovo Solar PV sponsor adapter.

    Parameters
    ----------
    project_factory
        Project factory callable. Defaults to create_default_oborovo.
    golden_lp_equity_irr
        Golden LP equity IRR target (Excel reference).  Defaults to 10.60%.
    golden_total_distributions_keur
        Golden total distributions target.  Defaults to 104,918 kEUR.

    Returns
    -------
    ProjectToSponsorAdapter
        Pre-built SponsorRunConfig + diagnostics.
    """
    from app.project_factories import create_default_oborovo
    from app.ui_runner import _build_period_engine, _run_waterfall
    from app.sponsor_runner import SponsorRunConfig

    factory = project_factory or create_default_oborovo
    proj = factory() if callable(project_factory) else project_factory

    if proj is None:
        proj = create_default_oborovo()

    engine = _build_period_engine(proj)
    result = _run_waterfall(proj, engine)

    # Extract SPV distributions: distribution_keur per period
    spv_distributions = tuple(p.distribution_keur for p in result.periods)
    total_spv = sum(spv_distributions)

    # Build sponsor config
    cap = OBOROVO_CAPITAL_STRUCTURE
    config = SponsorRunConfig(
        ownership_percentages=cap["ownership"],
        committed_capital_keur={
            "LP-1": cap["lp_commitment_keur"],
            "GP-1": cap["gp_commitment_keur"],
        },
        hurdle_rate_pa=0.08,
        compounding_convention="SEMIANNUAL",
        gp_promote_share=0.20,
        available_cash_by_period=spv_distributions,
        num_periods=len(spv_distributions),
    )

    return ProjectToSponsorAdapter(
        sponsor_config=config,
        spv_distributions_keur=spv_distributions,
        total_spv_distributions_keur=total_spv,
        project_equity_irr=result.equity_irr,
        spv_sponsor_irr=result.sponsor_irr,
        golden_total_distributions_keur=golden_total_distributions_keur,
        golden_lp_equity_irr=golden_lp_equity_irr,
    )


def build_tuho_adapter(
    project_factory: Callable[[], Any] | None = None,
    golden_lp_equity_irr: float | None = 0.1161,
    golden_total_distributions_keur: float | None = 118314.0,
) -> ProjectToSponsorAdapter:
    """Build TUHO Wind 1 sponsor adapter.

    Parameters
    ----------
    project_factory
        Project factory callable.  Defaults to create_default_tuho_wind1.
    golden_lp_equity_irr
        Golden LP equity IRR target (Excel reference).  Defaults to 11.61%.
    golden_total_distributions_keur
        Golden total distributions target.  Defaults to 118,314 kEUR.

    Returns
    -------
    ProjectToSponsorAdapter
        Pre-built SponsorRunConfig + diagnostics.
    """
    from app.project_factories import create_default_tuho_wind1
    from app.ui_runner import _build_period_engine, _run_waterfall
    from app.sponsor_runner import SponsorRunConfig

    factory = project_factory or create_default_tuho_wind1
    proj = factory() if callable(project_factory) else project_factory

    if proj is None:
        proj = create_default_tuho_wind1()

    engine = _build_period_engine(proj)
    result = _run_waterfall(proj, engine)

    # Extract SPV distributions
    spv_distributions = tuple(p.distribution_keur for p in result.periods)
    total_spv = sum(spv_distributions)

    cap = TUHO_CAPITAL_STRUCTURE
    config = SponsorRunConfig(
        ownership_percentages=cap["ownership"],
        committed_capital_keur={
            "LP-1": cap["lp_commitment_keur"],
            "GP-1": cap["gp_commitment_keur"],
        },
        hurdle_rate_pa=0.08,
        compounding_convention="SEMIANNUAL",
        gp_promote_share=0.20,
        available_cash_by_period=spv_distributions,
        num_periods=len(spv_distributions),
    )

    return ProjectToSponsorAdapter(
        sponsor_config=config,
        spv_distributions_keur=spv_distributions,
        total_spv_distributions_keur=total_spv,
        project_equity_irr=result.equity_irr,
        spv_sponsor_irr=result.sponsor_irr,
        golden_total_distributions_keur=golden_total_distributions_keur,
        golden_lp_equity_irr=golden_lp_equity_irr,
    )


# ─── Calibration report helper ────────────────────────────────────────────────

def calibration_report(adapter: ProjectToSponsorAdapter) -> dict[str, Any]:
    """Produce a deterministic calibration report from an adapter result.

    Returns a dict with:
      - spv_total_dist_keur   : actual SPV total distributions
      - golden_total_dist_keur : golden reference (or None)
      - dist_delta_keur        : actual - golden
      - dist_delta_pct         : delta as % of golden
      - project_equity_irr     : project equity IRR
      - spv_sponsor_irr        : blended sponsor IRR
      - golden_lp_irr          : golden LP equity IRR (or None)
      - lp_irr_vs_golden_pp    : IRR delta in pp (or None)
    """
    actual = adapter.total_spv_distributions_keur
    golden = adapter.golden_total_distributions_keur
    golden_irr = adapter.golden_lp_equity_irr

    dist_delta_keur = (actual - golden) if golden else None
    dist_delta_pct = (dist_delta_keur / golden) if golden else None
    irr_delta_pp = (
        ((adapter.spv_sponsor_irr - golden_irr) * 100)
        if golden_irr is not None
        else None
    )

    return {
        "spv_total_dist_keur": round(actual, 1),
        "golden_total_dist_keur": golden,
        "dist_delta_keur": round(dist_delta_keur, 1) if dist_delta_keur else None,
        "dist_delta_pct": round(dist_delta_pct * 100, 3) if dist_delta_pct else None,
        "project_equity_irr": round(adapter.project_equity_irr * 100, 3),
        "spv_sponsor_irr": round(adapter.spv_sponsor_irr * 100, 3),
        "golden_lp_irr": round(golden_irr * 100, 3) if golden_irr else None,
        "irr_delta_pp": round(irr_delta_pp, 2) if irr_delta_pp else None,
        "num_periods": len(adapter.spv_distributions_keur),
        "first_period_dist_keur": round(adapter.spv_distributions_keur[0], 1),
        "last_period_dist_keur": round(adapter.spv_distributions_keur[-1], 1),
    }
