"""Oborovo Solar PV — detailed offline OPEX template.

Maps B.01–B.13 groups from the Excel Inputs/OPEX sheet.
Category rows (B.01, B.02, etc.) are computed totals from child lines.

OPEX totals for Phase 20U-C aligned periods:
  Y1 total (excl. B.13): ~1,287 kEUR  ✓ matches Phase 20U-C reference
  B.02 steps 244 → 185.64 at Y2        ✓ matches Excel anchor
  B.12 steps 32 → 12.4848 at Y3        ✓ matches Excel anchor
  B.13 = 4% × non-contingency OPEX     ✓ matches Phase 20U-C

Total Oborovo OPEX (each year) = sum of all category totals = sum of children

IMPORTANT — B.02 structure:
  B.02.1 (O&M Services) has step_changes: Y1=244, Y2+=185.64
  B.02.2–B.02.10 are minor maintenance sub-items at 0 budget
  (used only to mirror the TUHO multi-line B.02 structure)
  → B.02 group Y1 total = 244 + 0 = 244 kEUR ✓
  → B.02 group Y2+ total = 185.64 + 0 = 185.64 kEUR ✓

IMPORTANT — B.12 structure:
  B.12.1 (Mitigation measures) has step_changes: Y1-Y2=32, Y3+=12.4848
  B.12.2 (Agrinergie) = 0
  → B.12 group Y1 total = 32 kEUR ✓
  → B.12 group Y3+ total = 12.4848 kEUR ✓
"""

from __future__ import annotations

from domain.opex.line_items import OpexBasis, OpexContingencyMethod, OpexGroup, OpexItem, OpexItemStep


def _item(
    code: str,
    name: str,
    budget: float,
    group_code: str,
    *,
    basis: OpexBasis = OpexBasis.FIXED_ANNUAL_KEUR,
    inflation: float | None = 0.02,
    wth_rate: float | None = None,
    step_changes: tuple[OpexItemStep, ...] = (),
    active_flags: tuple[bool, ...] = (),
    notes: str = "",
    selected_group_codes: tuple[str, ...] = (),
) -> OpexItem:
    """Create an OpexItem for the Oborovo template."""
    return OpexItem(
        code=code,
        name=name,
        budget_keur=budget,
        basis=basis,
        group_code=group_code,
        inflation_rate=inflation,
        wth_rate=wth_rate,
        step_changes=step_changes,
        active_flags=active_flags,
        notes=notes,
        selected_group_codes=selected_group_codes,
    )


def _group(
    code: str,
    name: str,
    items: tuple[OpexItem, ...],
    *,
    inflation: float = 0.02,
    wth_rate: float = 0.0,
    contingency_pct: float = 0.0,
    contingency_method: OpexContingencyMethod = OpexContingencyMethod.FIXED_AMOUNT,
) -> OpexGroup:
    """Create an OpexGroup for the Oborovo template."""
    return OpexGroup(
        code=code,
        name=name,
        inflation_rate=inflation,
        wth_rate=wth_rate,
        items=items,
        contingency_pct=contingency_pct,
        contingency_method=contingency_method,
    )


# ── Step definitions ───────────────────────────────────────────────────────────

B02_STEP = (OpexItemStep(year_index=2, new_budget_keur=185.64),)
# B.12 steps at Y3 from 32 → 12.4848 (annual)
B12_STEP = (OpexItemStep(year_index=3, new_budget_keur=12.4848),)


def build_oborovo_opex_template() -> list[OpexGroup]:
    """Build Oborovo detailed OPEX template.

    B.01: Technical Management — 198 kEUR Y1
      Sub-lines modeled after TUHO structure (exact Oborovo sub-item
      budget not in source — values are representative placeholders).
      Sum of B.01.01–B.01.06 = 198 kEUR for Y1.

    B.02: Infrastructure Maintenance
      B.02.1 (O&M Services): 244 kEUR Y1, steps to 185.64 at Y2+
        — matches Excel B.02 Y1=244, Y2=185.64 anchor
      B.02.2–B.02.10: minor maintenance sub-items at 0 kEUR
        — mirrors TUHO B.02 structure

    B.03 Maintain Site: 45 kEUR Y1
    B.04 Clean Material: 40 kEUR Y1
    B.05 Security: 30 kEUR Y1
    B.06 Insurance: 255 kEUR Y1
    B.07 Lease&Property Tax: 208.08 kEUR Y1
    B.08 Power Expenses: 177 kEUR Y1 (flat)
    B.09 Fees: 14 kEUR Y1 (flat)
    B.10 Audit, Accounting & Legal: 24 kEUR Y1
    B.11 Bank Fees: 20 kEUR Y1

    B.12: Environmental & Social
      B.12.1 (Mitigation measures): 32 kEUR Y1-Y2, steps to 12.4848 at Y3+
        — matches Excel B.12 step at Y3
      B.12.2 (Agrinergie): 0 kEUR (structural placeholder)

    B.13: Contingency — 4% × non-contingency OPEX (B.01–B.12)
    """
    return [
        # ════════════════════════════════════════════════════════════════════════
        # B.01 — Technical Management
        # ════════════════════════════════════════════════════════════════════════
        _group(
            "B.01",
            "Technical Management",
            (
                # Y1 budget = 198 kEUR; sub-item breakdown is a TUHO-based
                # approximation (exact Oborovo B.01.01–B.01.0x budgets not in source).
                _item("B.01.01", "Asset Management Contract",
                      60.0, "B.01",
                      notes="placeholder — exact Oborovo B.01 sub-item budget not in source"),
                _item("B.01.02", "Operation Management Contract",
                      65.0, "B.01",
                      notes="placeholder"),
                _item("B.01.03", "Performance Monitoring",
                      28.0, "B.01",
                      notes="placeholder"),
                _item("B.01.04", "Technical Inspections",
                      20.0, "B.01",
                      notes="placeholder"),
                _item("B.01.05", "SCADA / Monitoring",
                      15.0, "B.01",
                      notes="placeholder"),
                _item("B.01.06", "Other Technical Services",
                      10.0, "B.01",
                      notes="placeholder — Y1 sum = 198 kEUR"),
            ),
        ),

        # ════════════════════════════════════════════════════════════════════════
        # B.02 — Infrastructure Maintenance
        # ════════════════════════════════════════════════════════════════════════
        _group(
            "B.02",
            "Infrastructure Maintenance",
            (
                _item(
                    "B.02.1",
                    "O&M Services",
                    244.0,   # Y1 annual budget
                    "B.02",
                    step_changes=B02_STEP,   # Y2+ → 185.64 (per Excel B.02 step schedule)
                    notes="B.02.1 active Y1-Y2; step at Y2→185.64 matches Excel anchor",
                ),
                # Sub-items mirroring TUHO B.02.2–B.02.10 structure (all 0 kEUR)
                _item("B.02.2",  "Minor Maintenance",             0.0, "B.02"),
                _item("B.02.3",  "HV Substation and O&M Building", 0.0, "B.02"),
                _item("B.02.4",  "Regulatory Inspections",        0.0, "B.02"),
                _item("B.02.5",  "HSE Prevention Plan",           0.0, "B.02"),
                _item("B.02.6",  "Met Station Maintenance",       0.0, "B.02"),
                _item("B.02.7",  "Blade Maintenance",             0.0, "B.02"),
                _item("B.02.8",  "Vehicle/Special Equipment",     0.0, "B.02"),
                _item("B.02.9",  "Others",                        0.0, "B.02"),
                _item("B.02.10", "Met Station 2",                 0.0, "B.02"),
            ),
            # Group inflation applies to items without explicit step_changes
            inflation=0.02,
        ),

        # ════════════════════════════════════════════════════════════════════════
        # B.03 — Maintain Site
        # ════════════════════════════════════════════════════════════════════════
        _group(
            "B.03",
            "Maintain Site",
            (
                _item("B.03.1", "Vegetation management", 30.0, "B.03"),
                _item("B.03.2", "Repair roads",          10.0, "B.03"),
                _item("B.03.3", "Pest control",           5.0, "B.03"),
            ),
        ),

        # ════════════════════════════════════════════════════════════════════════
        # B.04 — Clean Material
        # ════════════════════════════════════════════════════════════════════════
        _group(
            "B.04",
            "Clean Material",
            (
                _item("B.04.1", "Clean panel / blades",  30.0, "B.04"),
                _item("B.04.2", "Cleaning supplies",     10.0, "B.04"),
            ),
        ),

        # ════════════════════════════════════════════════════════════════════════
        # B.05 — Security
        # ════════════════════════════════════════════════════════════════════════
        _group(
            "B.05",
            "Security",
            (
                _item("B.05.1", "Surveillance systems",  20.0, "B.05"),
                _item("B.05.2", "Surveillance patrols",    7.0, "B.05"),
                _item("B.05.3", "Other security",          3.0, "B.05"),
            ),
        ),

        # ════════════════════════════════════════════════════════════════════════
        # B.06 — Insurance
        # ════════════════════════════════════════════════════════════════════════
        _group(
            "B.06",
            "Insurance",
            (
                _item("B.06.1", "Operation All Risk with BI",     220.0, "B.06"),
                _item("B.06.2", "Third Party Liability",           20.0, "B.06"),
                _item("B.06.3", "Substation / O&M Building",      10.0, "B.06"),
                _item("B.06.4", "Spare parts insurance",            5.0, "B.06"),
            ),
        ),

        # ════════════════════════════════════════════════════════════════════════
        # B.07 — Lease & Property Tax
        # ════════════════════════════════════════════════════════════════════════
        _group(
            "B.07",
            "Lease & Property Tax",
            (
                _item("B.07.1", "Land Leases",    180.0, "B.07"),
                _item("B.07.2", "Property tax",    28.08, "B.07"),
            ),
        ),

        # ════════════════════════════════════════════════════════════════════════
        # B.08 — Power Expenses (flat — no inflation)
        # ════════════════════════════════════════════════════════════════════════
        _group(
            "B.08",
            "Power Expenses",
            (
                _item("B.08.1", "Power consumption",  120.0, "B.08",
                      inflation=0.0),
                _item("B.08.2", "Grid usage fee",       40.0, "B.08",
                      inflation=0.0),
                _item("B.08.3", "Balancing costs",      17.0, "B.08",
                      inflation=0.0),
            ),
            inflation=0.0,
        ),

        # ════════════════════════════════════════════════════════════════════════
        # B.09 — Fees (flat)
        # ════════════════════════════════════════════════════════════════════════
        _group(
            "B.09",
            "Fees",
            (
                _item("B.09.1", "Bank fees", 14.0, "B.09",
                      inflation=0.0),
            ),
            inflation=0.0,
        ),

        # ════════════════════════════════════════════════════════════════════════
        # B.10 — Audit, Accounting & Legal
        # ════════════════════════════════════════════════════════════════════════
        _group(
            "B.10",
            "Audit, Accounting & Legal",
            (
                _item("B.10.1", "Audit",      15.0, "B.10"),
                _item("B.10.2", "Accounting",  5.0, "B.10"),
                _item("B.10.3", "Legal",       4.0, "B.10"),
            ),
        ),

        # ════════════════════════════════════════════════════════════════════════
        # B.11 — Bank Fees
        # ════════════════════════════════════════════════════════════════════════
        _group(
            "B.11",
            "Bank Fees",
            (
                _item("B.11.1", "Bank transaction fees",
                      20.0, "B.11"),
            ),
        ),

        # ════════════════════════════════════════════════════════════════════════
        # B.12 — Environmental & Social
        # ════════════════════════════════════════════════════════════════════════
        _group(
            "B.12",
            "Environmental & Social",
            (
                _item(
                    "B.12.1",
                    "Mitigation measures",
                    32.0,   # Y1 annual budget
                    "B.12",
                    step_changes=B12_STEP,   # Y3+ → 12.4848 per Excel
                    notes="B.12.1 steps at Y3→12.4848 (matches Excel B.12 step)",
                ),
                _item("B.12.2", "Agrinergie",
                      0.0, "B.12"),
            ),
            inflation=0.02,
        ),

        # ════════════════════════════════════════════════════════════════════════
        # B.13 — Contingency  (4% × sum of B.01–B.12)
        # ════════════════════════════════════════════════════════════════════════
        _group(
            "B.13",
            "Contingency",
            (
                _item(
                    "B.13.1",
                    "Contingency reserve",
                    0.0,   # budget ignored when basis=PCT_OF_SELECTED_GROUPS
                    "B.13",
                    basis=OpexBasis.PCT_OF_SELECTED_GROUPS,
                    selected_group_codes=tuple(f"B.{idx:02d}" for idx in range(1, 13)),
                    notes="4% x non-contingency OPEX (B.01-B.12)",
                ),
            ),
            contingency_pct=4.0,
            contingency_method=OpexContingencyMethod.PERCENTAGE_OF_OPEX,
        ),
    ]


__all__ = ["build_oborovo_opex_template"]
