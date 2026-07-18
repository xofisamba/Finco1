"""finco_parity.tax_reference_inputs — Explicit per-baseline tax reference registry.

This module is the parity-layer source of truth for:
  * Per-baseline TaxPolicy (constructed from canonical project inputs).
  * Opening loss vintage positions.

It does NOT live inside financial_engine.  The financial_engine accepts an
explicit TaxPolicy and explicit opening vintages; project identity is resolved
HERE, in the parity adapter layer.

Opening loss origin-year convention
------------------------------------
TUHO reports ``prior_tax_loss_keur = 25 000`` kEUR.  The project inputs do not
carry an explicit vintage year.  Convention adopted here:

    origin_tax_year = financial_close.year − 1

For TUHO this yields 2028.  With ``loss_carryforward_years = 5``:
    last_usable_tax_year = 2028 + 5 = 2033

The loss is therefore available for use in calendar years 2030–2033
(construction year 2029 does not generate taxable income, and expiry occurs
when last_usable_tax_year < current_tax_year, i.e. from 2034 onwards).

Source: project_factories.create_default_tuho_wind1() → pi.tax.prior_tax_loss_keur
Rationale: "Convention: year before financial close (financial_close.year − 1).
No explicit vintage origin year in project inputs."

For baselines with no opening losses, an explicit reviewed-zero position is
recorded rather than relying on an absent tuple.
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Registry schema
# ---------------------------------------------------------------------------

_OPENING_LOSS_REGISTRY: dict[str, list[dict[str, Any]]] = {
    "tuho": [
        {
            "vintage_id": "tuho_prior_loss_opening",
            "source_field": "project_inputs.tax.prior_tax_loss_keur",
            "amount_keur": 25_000.0,
            "origin_tax_year": 2028,
            # origin_tax_year = financial_close.year (2029) - 1 = 2028
            # No explicit vintage year in project inputs; convention applied.
            "source_rationale": (
                "Convention: year before financial close 2029-07-01 → origin 2028. "
                "last_usable = 2028 + 5 = 2033. "
                "Source: create_default_tuho_wind1().tax.prior_tax_loss_keur."
            ),
            "policy_id": "hr_standard_factory_v1",
        }
    ],
    "oborovo": [
        {
            "vintage_id": None,  # reviewed zero position — no opening loss
            "source_field": "project_inputs.tax.prior_tax_loss_keur",
            "amount_keur": 0.0,
            "origin_tax_year": None,
            "source_rationale": (
                "Reviewed zero: create_default_oborovo().tax.prior_tax_loss_keur == 0.0"
            ),
            "policy_id": "hr_reduced_factory_v1",
        }
    ],
    "generic_solar": [
        {
            "vintage_id": None,
            "source_field": "project_inputs.tax.prior_tax_loss_keur",
            "amount_keur": 0.0,
            "origin_tax_year": None,
            "source_rationale": (
                "Reviewed zero: create_default_solar_project().tax.prior_tax_loss_keur == 0.0"
            ),
            "policy_id": "de_demo_factory_v1",
        }
    ],
    "generic_wind": [
        {
            "vintage_id": None,
            "source_field": "project_inputs.tax.prior_tax_loss_keur",
            "amount_keur": 0.0,
            "origin_tax_year": None,
            "source_rationale": (
                "Reviewed zero: create_default_wind_project().tax.prior_tax_loss_keur == 0.0"
            ),
            "policy_id": "de_demo_factory_v1",
        }
    ],
}

# ---------------------------------------------------------------------------
# Per-baseline policy parameters derived from canonical project inputs.
# Policy IDs encode country and designation — NOT project names or codes.
# ---------------------------------------------------------------------------

_POLICY_PARAMS: dict[str, dict[str, Any]] = {
    "tuho": {
        "policy_id": "hr_standard_factory_v1",
        "policy_version": "1.0",
        # Source: create_default_tuho_wind1().tax  (country HR, rate 18%)
        "corporate_rate": 0.18,
        "periods_per_tax_year": 2,
        "loss_carryforward_years": 5,
        "atad_enabled": True,
        "atad_ebitda_limit": 0.30,
        "atad_de_minimis_threshold_keur_annual": 3_000.0,
        "cash_tax_timing": "tax_year_last_period",
        "cash_tax_payment_lag_periods": 0,
    },
    "oborovo": {
        "policy_id": "hr_reduced_factory_v1",
        "policy_version": "1.0",
        # Source: create_default_oborovo().tax  (country HR, rate 10%)
        "corporate_rate": 0.10,
        "periods_per_tax_year": 2,
        "loss_carryforward_years": 5,
        "atad_enabled": True,
        "atad_ebitda_limit": 0.30,
        "atad_de_minimis_threshold_keur_annual": 3_000.0,
        "cash_tax_timing": "tax_year_last_period",
        "cash_tax_payment_lag_periods": 0,
    },
    "generic_solar": {
        "policy_id": "de_demo_factory_v1",
        "policy_version": "1.0",
        # Source: create_default_solar_project().tax  (country DE, rate 25%)
        # NOTE: 25% is the explicit model/factory assumption, NOT a verified
        # German legal tax rate.  German CIT + solidarity surcharge is ~15.83%
        # at the federal level before trade tax.  The factory uses 25% as a
        # rounded demonstration rate.
        "corporate_rate": 0.25,
        "periods_per_tax_year": 2,
        "loss_carryforward_years": 5,
        "atad_enabled": True,
        "atad_ebitda_limit": 0.30,
        "atad_de_minimis_threshold_keur_annual": 3_000.0,
        "cash_tax_timing": "tax_year_last_period",
        "cash_tax_payment_lag_periods": 0,
    },
    "generic_wind": {
        "policy_id": "de_demo_factory_v1",
        "policy_version": "1.0",
        # Source: create_default_wind_project().tax  (country DE, rate 25%)
        # NOTE: 25% is the explicit model/factory assumption.  See generic_solar.
        "corporate_rate": 0.25,
        "periods_per_tax_year": 2,
        "loss_carryforward_years": 5,
        "atad_enabled": True,
        "atad_ebitda_limit": 0.30,
        "atad_de_minimis_threshold_keur_annual": 3_000.0,
        "cash_tax_timing": "tax_year_last_period",
        "cash_tax_payment_lag_periods": 0,
    },
}


def build_tax_policy(baseline_id: str):
    """Build a TaxPolicy for the given baseline from canonical project inputs.

    Parameters
    ----------
    baseline_id:
        One of ``tuho``, ``oborovo``, ``generic_solar``, ``generic_wind``.

    Returns
    -------
    TaxPolicy (frozen dataclass from financial_engine.policies.tax).
    """
    if baseline_id not in _POLICY_PARAMS:
        raise ValueError(
            f"No policy registered for baseline_id {baseline_id!r}. "
            f"Valid: {sorted(_POLICY_PARAMS)}"
        )
    from financial_engine.policies.tax import TaxPolicy, CashTaxTiming

    p = _POLICY_PARAMS[baseline_id]
    return TaxPolicy(
        policy_id=p["policy_id"],
        policy_version=p["policy_version"],
        corporate_rate=p["corporate_rate"],
        periods_per_tax_year=p["periods_per_tax_year"],
        loss_carryforward_years=p["loss_carryforward_years"],
        atad_enabled=p["atad_enabled"],
        atad_ebitda_limit=p["atad_ebitda_limit"],
        atad_de_minimis_threshold_keur_annual=p["atad_de_minimis_threshold_keur_annual"],
        cash_tax_timing=CashTaxTiming(p["cash_tax_timing"]),
        cash_tax_payment_lag_periods=p["cash_tax_payment_lag_periods"],
    )


def build_opening_loss_vintages(baseline_id: str) -> tuple:
    """Build the opening loss vintage tuple for the given baseline.

    Returns an empty tuple for baselines with reviewed-zero positions.
    For TUHO, returns the 25 000 kEUR opening vintage.
    """
    if baseline_id not in _OPENING_LOSS_REGISTRY:
        raise ValueError(
            f"No opening loss registry entry for {baseline_id!r}. "
            f"Valid: {sorted(_OPENING_LOSS_REGISTRY)}"
        )
    from financial_engine.inputs import OpeningTaxLossVintageInput

    vintages = []
    for entry in _OPENING_LOSS_REGISTRY[baseline_id]:
        amount = entry["amount_keur"]
        if amount <= 0.0 or entry["origin_tax_year"] is None:
            # Reviewed zero — no vintage to create.
            continue
        vintages.append(OpeningTaxLossVintageInput(
            origin_tax_year=entry["origin_tax_year"],
            amount_keur=amount,
            source_label=entry.get("source_rationale", "")[:120],
        ))
    return tuple(vintages)


def get_policy_summary() -> dict[str, dict[str, Any]]:
    """Return a human-readable summary of all registered policies."""
    return {
        bid: {
            "policy_id": p["policy_id"],
            "corporate_rate": p["corporate_rate"],
            "loss_carryforward_years": p["loss_carryforward_years"],
            "atad_enabled": p["atad_enabled"],
            "atad_ebitda_limit": p["atad_ebitda_limit"],
            "atad_de_minimis_threshold_keur_annual": p["atad_de_minimis_threshold_keur_annual"],
        }
        for bid, p in _POLICY_PARAMS.items()
    }


def get_opening_loss_summary() -> dict[str, list[dict[str, Any]]]:
    """Return the full opening loss registry for audit purposes."""
    return {
        bid: [dict(entry) for entry in entries]
        for bid, entries in _OPENING_LOSS_REGISTRY.items()
    }
