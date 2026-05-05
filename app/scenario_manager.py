"""Scenario manager — structured scenario definitions and override application.

This module provides a clean scenario architecture separate from the domain
layer. It defines Base/Downside/Upside scenarios per project type and applies
numeric overrides to project inputs without rewriting domain objects beyond
their numeric fields.

Design:
- Scenario dataclass (frozen) — immutable scenario definition
- ScenarioManager — scenario registry and override application
- Only numeric field multipliers are applied; domain object structure is preserved

Backward compatible: does not replace app/scenarios.py (legacy scenario engine).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Optional


# ── Scenario dataclass ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Scenario:
    """Immutable scenario definition.

    Attributes
    ----------
    name : str
        Display name, e.g. "Base", "Downside", "Upside".
    description : str
        Human-readable description of the scenario.
    is_base : bool
        True for the base/reference scenario.
    revenue_multiplier : float
        Multiplier applied to revenue tariff fields (default 1.0 = no change).
    opex_multiplier : float
        Multiplier applied to OPEX Y1 amounts (default 1.0 = no change).
    capex_multiplier : float
        Multiplier applied to total CapEx (default 1.0 = no change).
    debt_sculpting_override : float | None
        Override DSCR target for this scenario. None = use base project value.
    annual_generation_hours : float | None
        Override operating/p50 hours. None = use base project value.
    """
    name: str
    description: str
    is_base: bool = False
    revenue_multiplier: float = 1.0
    opex_multiplier: float = 1.0
    capex_multiplier: float = 1.0
    debt_sculpting_override: Optional[float] = None
    annual_generation_hours: Optional[float] = None


# ── Scenario definitions ──────────────────────────────────────────────────────

# Solar scenarios — revenue is the primary sensitivity axis
_SOLAR_SCENARIOS: dict[str, Scenario] = {
    "Base": Scenario(
        name="Base",
        description="Reference case with base tariff and base operating assumptions.",
        is_base=True,
        revenue_multiplier=1.0,
        opex_multiplier=1.0,
        capex_multiplier=1.0,
    ),
    "Downside": Scenario(
        name="Downside",
        description="Downside: revenue -15%, opex +10%, capex +5%.",
        revenue_multiplier=0.85,
        opex_multiplier=1.10,
        capex_multiplier=1.05,
    ),
    "Upside": Scenario(
        name="Upside",
        description="Upside: revenue +15%, opex -5%, capex -3%.",
        revenue_multiplier=1.15,
        opex_multiplier=0.95,
        capex_multiplier=0.97,
    ),
}

# Wind scenarios — same multiplier logic as solar
_WIND_SCENARIOS: dict[str, Scenario] = {
    "Base": Scenario(
        name="Base",
        description="Reference case with base tariff and base operating assumptions.",
        is_base=True,
        revenue_multiplier=1.0,
        opex_multiplier=1.0,
        capex_multiplier=1.0,
    ),
    "Downside": Scenario(
        name="Downside",
        description="Downside: revenue -15%, opex +10%, capex +5%.",
        revenue_multiplier=0.85,
        opex_multiplier=1.10,
        capex_multiplier=1.05,
    ),
    "Upside": Scenario(
        name="Upside",
        description="Upside: revenue +15%, opex -5%, capex -3%.",
        revenue_multiplier=1.15,
        opex_multiplier=0.95,
        capex_multiplier=0.97,
    ),
}

# Fallback scenarios for project types without specific definitions
_DEFAULT_SCENARIOS: dict[str, Scenario] = {
    "Base": Scenario(
        name="Base",
        description="Base reference scenario.",
        is_base=True,
    ),
}


# ── ScenarioManager ────────────────────────────────────────────────────────────

class ScenarioManager:
    """Manages scenario registry and override application for a project type.

    Parameters
    ----------
    project_type : str
        Project type key, e.g. "solar", "wind", "bess".
    """

    def __init__(self, project_type: str):
        self.project_type = project_type.lower()
        self._scenarios = self._load_scenarios()
        self._active_scenario: str = "Base"

    def _load_scenarios(self) -> dict[str, Scenario]:
        """Load scenario definitions for this project type."""
        if self.project_type == "solar":
            return dict(_SOLAR_SCENARIOS)
        elif self.project_type == "wind":
            return dict(_WIND_SCENARIOS)
        else:
            return dict(_DEFAULT_SCENARIOS)

    @property
    def scenarios(self) -> dict[str, Scenario]:
        """All scenarios for this project type."""
        return self._scenarios

    @property
    def active_scenario(self) -> str:
        """Name of the currently active scenario."""
        return self._active_scenario

    def set_active(self, name: str) -> None:
        """Set the active scenario by name."""
        if name not in self._scenarios:
            raise KeyError(f"Unknown scenario {name!r}. Available: {list(self._scenarios.keys())}")
        self._active_scenario = name

    def get_scenario(self, name: str) -> Scenario:
        """Return the Scenario for the given name.

        Raises
        ------
        KeyError
            If the scenario name is not registered.
        """
        if name not in self._scenarios:
            raise KeyError(f"Unknown scenario {name!r}. Available: {list(self._scenarios.keys())}")
        return self._scenarios[name]

    def list_scenarios(self) -> list[str]:
        """Return sorted list of scenario names."""
        return sorted(self._scenarios.keys(), key=lambda n: (0 if self._scenarios[n].is_base else 1, n))

    # ── Override application ────────────────────────────────────────────────────

    TARIFF_FIELDS = ("ppa_base_tariff", "merchant_price", "merchant_price_eur_mwh",
                     "base_price", "tariff")
    HOURS_FIELDS = ("operating_hours_p50", "operating_hours_p90_10y",
                    "p50_hours", "equivalent_hours")

    def apply_overrides(self, project_inputs, scenario_name: str):
        """Apply scenario overrides to project inputs.

        Returns a **deep copy** of project_inputs with numeric fields scaled
        per the scenario multipliers. The original project_inputs is unchanged.

        Only numeric fields are modified; domain object structure is preserved.

        Parameters
        ----------
        project_inputs : ProjectInputs
            The base project inputs dataclass.
        scenario_name : str
            Name of the scenario to apply.

        Returns
        -------
        ProjectInputs
            New ProjectInputs with scenario overrides applied.

        Raises
        ------
        KeyError
            If the scenario name is not registered.
        """
        scenario = self.get_scenario(scenario_name)

        # Fast path: base scenario — return copy with no changes
        if scenario.is_base and scenario.revenue_multiplier == 1.0 \
                and scenario.opex_multiplier == 1.0 \
                and scenario.capex_multiplier == 1.0:
            return replace(project_inputs)

        tech = project_inputs.technical
        capex = project_inputs.capex
        opex = project_inputs.opex
        rev = project_inputs.revenue
        financing = project_inputs.financing

        # Revenue tariff multiplier
        if scenario.revenue_multiplier != 1.0:
            tariff_field = self._first_field(rev, self.TARIFF_FIELDS)
            if tariff_field:
                new_val = getattr(rev, tariff_field) * scenario.revenue_multiplier
                rev = replace(rev, **{tariff_field: new_val})

        # OPEX multiplier — scale y1_amount_keur on each item
        if scenario.opex_multiplier != 1.0 and opex:
            def _scale_opex_item(item):
                return replace(item, y1_amount_keur=item.y1_amount_keur * scenario.opex_multiplier)
            opex = tuple(_scale_opex_item(i) for i in opex)

        # CapEx multiplier — scale total CapEx via capex_overrides helper
        if scenario.capex_multiplier != 1.0 and capex.total_capex > 0:
            from app.capex_overrides import scale_capex_items
            capex = scale_capex_items(capex, capex.total_capex * scenario.capex_multiplier)

        # Annual generation hours override
        if scenario.annual_generation_hours is not None:
            hours_field = self._first_field(tech, self.HOURS_FIELDS)
            if hours_field:
                tech = replace(tech, **{hours_field: scenario.annual_generation_hours})

        # Debt sculpting override (DSCR target)
        if scenario.debt_sculpting_override is not None and hasattr(financing, "target_dscr"):
            financing = replace(financing, target_dscr=scenario.debt_sculpting_override)

        return replace(project_inputs, technical=tech, capex=capex, opex=opex,
                       revenue=rev, financing=financing)

    @staticmethod
    def _first_field(obj, candidates: tuple[str, ...]) -> Optional[str]:
        """Return the first field name in candidates that exists on obj."""
        for c in candidates:
            if hasattr(obj, c):
                return c
        return None
