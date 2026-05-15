"""Result objects for distribution account calculations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class R99InputResult:
    """Audit result for one TUHO R99/R102 input-engine period."""

    r69_fcf_banks_keur: float
    r84_fcf_junior_keur: float
    r98_distribution_account_keur: float
    r99_fcf_for_distribution_keur: float
    r100_carryforward_keur: float
    r102_fcf_for_shl_keur: float
    fcf_for_shl_keur: float
    locked: bool
    lockup_reasons: tuple[str, ...] = ()
