"""finco_recon.materiality — Report-only materiality thresholds.

These thresholds affect report highlighting and delta classification only.
They NEVER change clean-engine calculations.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaterialitySettings:
    """Report-only materiality thresholds for the Excel↔Python reconciliation.

    All thresholds affect highlighting and MATCH/TIMING-ROUNDING priority only.
    Zero raw deltas are always stored in 15_RAW_RECON regardless of materiality.
    """
    absolute_keur: float = 1.0          # 1 kEUR = EUR 1,000
    relative_fraction: float = 0.001    # 0.1%
    mwh_threshold: float = 10.0         # MWh
    price_eur_mwh: float = 0.10         # EUR/MWh
    ratio_threshold: float = 0.005      # 0.5% (for DSCR, gearing ratios)

    def is_material(
        self,
        abs_delta: float,
        excel_val: float | None = None,
        python_val: float | None = None,
        unit: str = "kEUR",
    ) -> bool:
        """True if the delta exceeds the materiality threshold.

        A delta is material when EITHER the absolute OR relative threshold is breached.
        """
        if unit in ("kEUR",):
            if abs(abs_delta) >= self.absolute_keur:
                return True
            if excel_val is not None and python_val is not None:
                ref = max(abs(excel_val), abs(python_val), 0.001)
                if abs(abs_delta) / ref >= self.relative_fraction:
                    return True
            return False
        if unit == "MWh":
            return abs(abs_delta) >= self.mwh_threshold
        if unit in ("EUR/MWh",):
            return abs(abs_delta) >= self.price_eur_mwh
        if unit in ("x", "%", "frac"):
            return abs(abs_delta) >= self.ratio_threshold
        return abs(abs_delta) > 0.0001


DEFAULT_MATERIALITY = MaterialitySettings()
