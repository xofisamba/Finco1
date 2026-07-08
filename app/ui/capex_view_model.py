"""
CAPEX View Model — Excel-faithful display layer for CAPEX grids.

Transforms ProjectContext.capex_detail_items into template-ready dataclasses.
No engine logic, no persistence, no routes.

Excel source: C.01–C.18 structure (TUHO + Oborovo mapping, PR #849).

Editability contract:
  - Group header rows (C.01, C.02, …)   → never editable (display only)
  - C.17 Financing Costs sub-lines       → never editable (backend computed)
  - C.18 Reserve Accounts sub-lines      → never editable (backend computed)
  - All other sub-lines                  → editable for user projects only
  - is_custom lines (future)             → editable while is_active is True
  - Per-MW column                        → always derived, never submitted
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ui.project_context import ProjectContext

# ---------------------------------------------------------------------------
# Codes that are always backend-computed / read-only
# ---------------------------------------------------------------------------
_READONLY_GROUP_CODES = frozenset({"C.17", "C.18"})

# Hard CAPEX = C.01–C.16 (everything except C.17, C.18)
_FINANCING_CODE = "C.17"
_RESERVE_CODE = "C.18"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CapexLineVM:
    """Single sub-line row in the CAPEX Excel grid."""

    code: str
    parent_code: str
    name: str

    # Primary amount in kEUR (user-editable for editable lines)
    amount_keur: float

    # Derived display column — never submitted to engine
    per_mw: float

    # Editability flags
    is_editable: bool           # True iff user may change amount_keur
    is_group: bool              # True = group header row, not a data row
    is_readonly_financing: bool  # True for any line under C.17 or C.18

    # Future: user-managed line items
    is_custom: bool   # True = user-added (not in Excel template)
    is_active: bool   # False = user has deactivated this line (excluded from totals)


@dataclass(frozen=True)
class CapexGroupVM:
    """Group header (C.01, C.02, …) with its sub-lines."""

    code: str
    name: str
    lines: tuple[CapexLineVM, ...]

    # Derived totals — always display-only
    subtotal_keur: float
    subtotal_per_mw: float

    # True for C.17, C.18 — group and all sub-lines are read-only
    is_readonly: bool


@dataclass(frozen=True)
class CapexViewModel:
    """Full CAPEX sheet view model, ready for template iteration."""

    project_name: str
    capacity_mw: float

    groups: tuple[CapexGroupVM, ...]  # C.01–C.18 in Excel order

    # Aggregated totals
    hard_capex_keur: float    # sum of active groups C.01–C.16
    hard_capex_per_mw: float
    financing_keur: float     # C.17 subtotal
    reserve_keur: float       # C.18 subtotal
    total_capex_keur: float   # hard + financing + reserve
    total_per_mw: float

    is_user_project: bool


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def _safe_per_mw(amount_keur: float, capacity_mw: float) -> float:
    if capacity_mw > 0:
        return amount_keur / capacity_mw
    return 0.0


def build_capex_view_model(
    project_ctx: "ProjectContext",
    is_user_project: bool = False,
) -> CapexViewModel:
    """
    Build a CapexViewModel from ProjectContext.capex_detail_items.

    Args:
        project_ctx:     Populated ProjectContext (frozen dataclass).
        is_user_project: True iff the current session user owns this project
                         and may edit line-item amounts.

    Returns:
        Fully populated CapexViewModel ready for template rendering.
        No lazy evaluation — all derived fields computed here.
    """
    capacity_mw = project_ctx.capacity_mw
    groups: list[CapexGroupVM] = []

    for cat in project_ctx.capex_detail_items:
        group_code: str = cat["code"]
        group_name: str = cat["name"]
        is_backend_group: bool = cat.get("is_backend_calculated", False)
        group_readonly = group_code in _READONLY_GROUP_CODES or is_backend_group

        lines: list[CapexLineVM] = []
        for child in cat.get("children", ()):
            child_code: str = child["code"]
            amount_keur: float = float(child.get("amount_keur") or 0.0)
            per_mw: float = _safe_per_mw(amount_keur, capacity_mw)

            child_backend: bool = child.get("is_backend_calculated", False)
            editable = (
                is_user_project
                and not group_readonly
                and not child_backend
            )

            lines.append(CapexLineVM(
                code=child_code,
                parent_code=group_code,
                name=child["name"],
                amount_keur=amount_keur,
                per_mw=per_mw,
                is_editable=editable,
                is_group=False,
                is_readonly_financing=group_readonly,
                is_custom=False,   # future: set from user-stored overrides
                is_active=True,    # future: set from user-stored deactivation
            ))

        active_lines = [ln for ln in lines if ln.is_active]
        subtotal_keur = sum(ln.amount_keur for ln in active_lines)
        subtotal_per_mw = _safe_per_mw(subtotal_keur, capacity_mw)

        groups.append(CapexGroupVM(
            code=group_code,
            name=group_name,
            lines=tuple(lines),
            subtotal_keur=subtotal_keur,
            subtotal_per_mw=subtotal_per_mw,
            is_readonly=group_readonly,
        ))

    # Aggregate totals
    hard_capex_keur = sum(
        g.subtotal_keur for g in groups
        if g.code not in _READONLY_GROUP_CODES
    )
    financing_keur = next(
        (g.subtotal_keur for g in groups if g.code == _FINANCING_CODE), 0.0
    )
    reserve_keur = next(
        (g.subtotal_keur for g in groups if g.code == _RESERVE_CODE), 0.0
    )
    total_capex_keur = hard_capex_keur + financing_keur + reserve_keur

    return CapexViewModel(
        project_name=project_ctx.name,
        capacity_mw=capacity_mw,
        groups=tuple(groups),
        hard_capex_keur=hard_capex_keur,
        hard_capex_per_mw=_safe_per_mw(hard_capex_keur, capacity_mw),
        financing_keur=financing_keur,
        reserve_keur=reserve_keur,
        total_capex_keur=total_capex_keur,
        total_per_mw=_safe_per_mw(total_capex_keur, capacity_mw),
        is_user_project=is_user_project,
    )
