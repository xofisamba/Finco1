"""
OPEX View Model — Excel-faithful display layer for OPEX grids.

Transforms ProjectContext.opex_detail_items into template-ready dataclasses.
No engine logic, no persistence, no routes.

Excel source: B.01–B.13 structure (TUHO + Oborovo mapping, PR #849).

Year value contract:
  Year escalation formula (simple lines):
      Yn = Y1_budget × (1 + inflation_pct / 100)^(n-1)

  Pre-computed `yearly_values` from opex_detail_items are used when present
  (they correctly handle step schedules and conditional activation).
  `compute_year_values()` is exposed for the simple formula case.

  Step schedules (e.g. TUHO B.02.1 ramp: Y1=385.6, Y3=465.6, Y6=588,
  Y11=628) and conditional lines (e.g. Oborovo B.08 Balancing zero Y1–Y10)
  are supported via the pre-computed yearly_values field. Custom schedule
  editing is out of scope for v1.

Editability contract:
  - Group header rows (B.01, B.02, …)   → display only
  - B.13 Contingencies sub-lines         → amount derived, rate editable
  - All other sub-lines                  → Y1 amount editable for user projects
  - WHT flag                             → display only, set by project template
  - Year columns Y2–YN                   → always derived, never submitted
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ui.project_context import ProjectContext

# Default number of year columns to display
DEFAULT_DISPLAY_YEARS = 10
MAX_DISPLAY_YEARS = 30

_CONTINGENCY_CODE = "B.13"


# ---------------------------------------------------------------------------
# Pure formula — exposed for testing and future template use
# ---------------------------------------------------------------------------

def compute_year_values(
    y1_keur: float,
    inflation_pct: float,
    n_years: int,
) -> list[float]:
    """
    Compute year values for a simple escalating OPEX line.

    Yn = Y1 × (1 + inflation_pct/100)^(n-1)

    Index 0 = Y1, index 1 = Y2, …, index n_years-1 = Yn.
    """
    rate = 1.0 + inflation_pct / 100.0
    return [y1_keur * (rate ** (yr - 1)) for yr in range(1, n_years + 1)]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OpexLineVM:
    """Single sub-line row in the OPEX Excel grid."""

    code: str
    parent_code: str
    name: str

    # Y1 budget (user-editable for editable lines)
    y1_keur: float

    # Group-level escalation rate applied to this line
    inflation_pct: float

    # Withholding Tax flag — display column only, set by project template
    wht_flag: bool

    # Editability flags
    is_editable: bool      # True iff user may change y1_keur
    is_group: bool         # True = group header row
    is_contingency: bool   # True = B.13 derived line

    # Future: user-managed line items
    is_custom: bool   # True = user-added (not in Excel template)
    is_active: bool   # False = user has deactivated this line

    # Pre-computed year values (index 0 = Y1, index 1 = Y2, …)
    # Length = display_years (from OpexViewModel).
    # Uses source yearly_values when available; falls back to compute_year_values().
    year_values: tuple[float, ...]


@dataclass(frozen=True)
class OpexGroupVM:
    """Group header (B.01, B.02, …) with its sub-lines."""

    code: str
    name: str
    inflation_pct: float   # group-level default escalation rate
    is_contingency: bool
    contingency_pct: float  # 0.0 unless is_contingency

    lines: tuple[OpexLineVM, ...]

    # Derived: sum of active sub-lines per display year (index 0 = Y1)
    subtotal_per_year: tuple[float, ...]


@dataclass(frozen=True)
class OpexViewModel:
    """Full OPEX sheet view model, ready for template iteration."""

    project_name: str
    capacity_mw: float
    p50_annual_mwh: float   # operating_hours_p50 × capacity_mw

    groups: tuple[OpexGroupVM, ...]  # B.01–B.13 in Excel order

    # Contingency rate (from B.13 / project_ctx.opex_contingency_pct)
    contingency_rate: float

    # Per-year totals (index 0 = Y1, …, index display_years-1)
    total_excl_contingency: tuple[float, ...]
    total_incl_contingency: tuple[float, ...]

    # Number of year columns being displayed (1 ≤ display_years ≤ 30)
    display_years: int

    # Y1 KPI metrics
    opex_per_mw_y1: float    # total_y1_incl / capacity_mw
    opex_per_mwh_y1: float   # total_y1_incl × 1000 / p50_annual_mwh

    is_user_project: bool


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def _clamp_display_years(n: int) -> int:
    return max(1, min(n, MAX_DISPLAY_YEARS))


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator > 0:
        return numerator / denominator
    return 0.0


def _get_year_values(
    child: dict,
    n_years: int,
) -> tuple[float, ...]:
    """
    Return display-year values for a child line.

    Prefers the pre-computed yearly_values from the data source (which
    correctly handles step schedules and conditional activation). Falls back
    to the simple escalation formula when not available.
    """
    source_values: list[float] | None = child.get("yearly_values")
    y1: float = float(child.get("budget_y1_keur") or 0.0)
    inflation: float = float(child.get("inflation_pct") or 0.0)

    if source_values and len(source_values) >= n_years:
        return tuple(float(v) for v in source_values[:n_years])

    # Fallback: simple escalation (no step schedules)
    return tuple(compute_year_values(y1, inflation, n_years))


def build_opex_view_model(
    project_ctx: "ProjectContext",
    is_user_project: bool = False,
    display_years: int = DEFAULT_DISPLAY_YEARS,
) -> OpexViewModel:
    """
    Build an OpexViewModel from ProjectContext.opex_detail_items.

    Args:
        project_ctx:     Populated ProjectContext (frozen dataclass).
        is_user_project: True iff the current session user owns this project.
        display_years:   How many year columns to render (default 10, max 30).

    Returns:
        Fully populated OpexViewModel ready for template rendering.
    """
    display_years = _clamp_display_years(display_years)
    capacity_mw: float = project_ctx.capacity_mw
    p50_annual_mwh: float = project_ctx.operating_hours_p50 * capacity_mw
    contingency_rate: float = float(getattr(project_ctx, "opex_contingency_pct", 0.0))

    groups: list[OpexGroupVM] = []

    for cat in project_ctx.opex_detail_items:
        group_code: str = cat["code"]
        group_name: str = cat["name"]
        group_inflation: float = float(cat.get("inflation_pct") or 0.0)
        is_contingency_group: bool = cat.get("is_contingency", False)
        cat_contingency_pct: float = float(cat.get("contingency_pct") or 0.0)

        lines: list[OpexLineVM] = []
        for child in cat.get("children", []):
            child_code: str = child["code"]
            y1_keur: float = float(child.get("budget_y1_keur") or 0.0)
            inflation_pct: float = float(child.get("inflation_pct") or group_inflation)
            wht_flag: bool = float(child.get("wth_rate") or 0.0) > 0
            is_contingency_line: bool = is_contingency_group

            editable = (
                is_user_project
                and not is_contingency_line
            )

            year_values = _get_year_values(child, display_years)

            lines.append(OpexLineVM(
                code=child_code,
                parent_code=group_code,
                name=child["name"],
                y1_keur=y1_keur,
                inflation_pct=inflation_pct,
                wht_flag=wht_flag,
                is_editable=editable,
                is_group=False,
                is_contingency=is_contingency_line,
                is_custom=False,   # future: set from user-stored overrides
                is_active=True,    # future: set from user-stored deactivation
                year_values=year_values,
            ))

        # Group subtotal per year: sum of active non-contingency sub-lines
        active_lines = [ln for ln in lines if ln.is_active]
        subtotal_per_year = tuple(
            sum(ln.year_values[yr] for ln in active_lines if not ln.is_contingency)
            for yr in range(display_years)
        )

        groups.append(OpexGroupVM(
            code=group_code,
            name=group_name,
            inflation_pct=group_inflation,
            is_contingency=is_contingency_group,
            contingency_pct=cat_contingency_pct if is_contingency_group else 0.0,
            lines=tuple(lines),
            subtotal_per_year=subtotal_per_year,
        ))

    # Aggregate totals per year
    non_contingency_groups = [g for g in groups if not g.is_contingency]
    total_excl = tuple(
        sum(g.subtotal_per_year[yr] for g in non_contingency_groups)
        for yr in range(display_years)
    )
    # Contingency = rate × excl total per year
    total_incl = tuple(
        total_excl[yr] * (1.0 + contingency_rate / 100.0)
        for yr in range(display_years)
    )

    total_y1_incl = total_incl[0] if total_incl else 0.0

    return OpexViewModel(
        project_name=project_ctx.name,
        capacity_mw=capacity_mw,
        p50_annual_mwh=p50_annual_mwh,
        groups=tuple(groups),
        contingency_rate=contingency_rate,
        total_excl_contingency=total_excl,
        total_incl_contingency=total_incl,
        display_years=display_years,
        opex_per_mw_y1=_safe_div(total_y1_incl, capacity_mw),
        opex_per_mwh_y1=_safe_div(total_y1_incl * 1000.0, p50_annual_mwh),
        is_user_project=is_user_project,
    )
