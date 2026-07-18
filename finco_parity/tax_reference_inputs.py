"""finco_parity.tax_reference_inputs — Explicit per-baseline tax reference registry.

This module is the parity-layer source of truth for:
  * Per-baseline TaxPolicy (constructed from canonical project inputs).
  * Opening loss vintage positions.

It does NOT live inside financial_engine.  The financial_engine accepts an
explicit TaxPolicy and explicit opening vintages; project identity is resolved
HERE, in the parity adapter layer.

TUHO opening-loss: UNRESOLVED
-------------------------------
TUHO reports ``prior_tax_loss_keur = 25 000`` kEUR in
``project_factories.create_default_tuho_wind1()``.  This is a factory
hard-coded default with no supporting Excel extract.

Evidence:
  * ``docs/phase7f_tuho_tax_basis_diagnostic.md`` — CRITICAL DISCREPANCY:
    Python engine 25 000 kEUR vs Excel ~3 569 kEUR (7× larger).
  * ``docs/phase6_tax_bridge_residual_r67_final_calibration.md`` — states
    "near-expiry assumption pending full pre-COD Excel loss extract".
  * The factory convention ``origin_tax_year = financial_close.year − 1 = 2028``
    has no supporting source document.

Because neither the amount nor the origin year can be verified against an
authoritative primary source, ``build_opening_loss_vintages("tuho")`` raises
``TuhoOpeningLossVintageUnresolved``.  Callers must handle this stop condition.

Permitted outcome: ``TUHO TAX_CFADS_V1 = INPUT_SOURCE_BLOCKED``.

For baselines with no opening losses, an explicit reviewed-zero position is
recorded rather than relying on an absent tuple.
"""
from __future__ import annotations

from typing import Any


class TuhoOpeningLossVintageUnresolved(RuntimeError):
    """Raised when TUHO opening-loss vintage cannot be resolved from a primary source.

    The factory value (25 000 kEUR, origin 2028) is a hard-coded default with no
    supporting Excel extract.  Until a verified source is provided the TUHO
    TAX_CFADS_V1 result is INPUT_SOURCE_BLOCKED.
    """


# ---------------------------------------------------------------------------
# Registry schema
# ---------------------------------------------------------------------------

_OPENING_LOSS_REGISTRY: dict[str, list[dict[str, Any]]] = {
    "tuho": [
        {
            # UNRESOLVED — factory hard-coded default, no Excel source.
            # build_opening_loss_vintages("tuho") raises TuhoOpeningLossVintageUnresolved.
            # Do NOT use this entry directly.
            "vintage_id": "tuho_prior_loss_opening_UNRESOLVED",
            "source_field": "project_inputs.tax.prior_tax_loss_keur",
            "amount_keur": 25_000.0,
            "origin_tax_year": None,   # unresolved — no verified source
            "source_rationale": (
                "UNRESOLVED: factory default 25 000 kEUR with no Excel extract. "
                "Excel shows ~3 569 kEUR (phase7f_tuho_tax_basis_diagnostic.md). "
                "Origin year 2028 is a code convention, not from any source document. "
                "Status: TUHO_OPENING_LOSS_VINTAGE_UNRESOLVED."
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

    Raises
    ------
    TuhoOpeningLossVintageUnresolved
        For ``baseline_id == "tuho"``: the factory opening-loss amount and
        origin year cannot be verified against an authoritative primary source.
        Callers must catch this and return ``INPUT_SOURCE_BLOCKED`` for TUHO.
    """
    if baseline_id not in _OPENING_LOSS_REGISTRY:
        raise ValueError(
            f"No opening loss registry entry for {baseline_id!r}. "
            f"Valid: {sorted(_OPENING_LOSS_REGISTRY)}"
        )

    if baseline_id == "tuho":
        raise TuhoOpeningLossVintageUnresolved(
            "TUHO_OPENING_LOSS_VINTAGE_UNRESOLVED: factory value 25 000 kEUR "
            "(origin 2028) has no verified Excel source. "
            "Excel extract shows ~3 569 kEUR (phase7f_tuho_tax_basis_diagnostic.md). "
            "Permitted outcome: TUHO TAX_CFADS_V1 = INPUT_SOURCE_BLOCKED."
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
