"""Offline TUHO OPEX template calibrated to the Excel annual totals."""

from __future__ import annotations

from domain.opex.line_items import OpexBasis, OpexContingencyMethod, OpexGroup, OpexItem

B02_EXPLICIT_SCHEDULE = (
    385.6,
    385.6,
    465.6,
    465.6,
    465.6,
    588.0,
    588.0,
    588.0,
    588.0,
    588.0,
    628.0,
    628.0,
    628.0,
    628.0,
    628.0,
    676.0,
    676.0,
    676.0,
    676.0,
    676.0,
    756.0,
    756.0,
    756.0,
    756.0,
    756.0,
    828.0,
    828.0,
    828.0,
    828.0,
    828.0,
)
B11_ACTIVE_FLAGS = (True,) * 14 + (False,) * 16


def _item(
    code: str,
    name: str,
    budget: float,
    group_code: str,
    *,
    basis: OpexBasis = OpexBasis.FIXED_ANNUAL_KEUR,
    inflation: float | None = 0.02,
    explicit: tuple[float, ...] = (),
    selected: tuple[str, ...] = (),
    active_flags: tuple[bool, ...] = (),
) -> OpexItem:
    return OpexItem(
        code=code,
        name=name,
        budget_keur=budget,
        basis=basis,
        group_code=group_code,
        inflation_rate=inflation,
        active_flags=active_flags,
        explicit_schedule_keur=explicit,
        selected_group_codes=selected,
    )


def _group(
    code: str,
    name: str,
    items: tuple[OpexItem, ...],
    *,
    inflation: float = 0.02,
    contingency_pct: float = 0.0,
    contingency_method: OpexContingencyMethod = OpexContingencyMethod.FIXED_AMOUNT,
) -> OpexGroup:
    return OpexGroup(
        code=code,
        name=name,
        inflation_rate=inflation,
        items=items,
        contingency_pct=contingency_pct,
        contingency_method=contingency_method,
    )


def build_tuho_opex_template() -> list[OpexGroup]:
    """Build the offline TUHO OPEX template.

    This is not connected to runtime cash flow. It exists only for Excel parity
    testing of the line-item engine and TUHO mapping.
    """

    selected_groups = tuple(f"B.{idx:02d}" for idx in range(1, 13))
    return [
        _group(
            "B.01",
            "Technical Management",
            (
                _item("B.01.1", "Asset Management Contract", 138.0, "B.01"),
                _item("B.01.2", "Operation Management Contract", 67.0, "B.01"),
                _item("B.01.3", "Performance monitoring", 35.0, "B.01"),
                _item("B.01.4", "Technical Inspections", 0.0, "B.01"),
                _item("B.01.5", "Meteorological and weather forecast service", 18.0, "B.01"),
                _item("B.01.6", "Bazefield", 22.0, "B.01"),
            ),
        ),
        _group(
            "B.02",
            "Infrastructure",
            (
                _item(
                    "B.02.1",
                    "O&M Preventive and Corrective",
                    0.0,
                    "B.02",
                    basis=OpexBasis.EXPLICIT_SCHEDULE,
                    inflation=0.0,
                    explicit=B02_EXPLICIT_SCHEDULE,
                ),
                _item("B.02.2", "Minor Maintenance", 27.0, "B.02"),
                _item("B.02.3", "HV Substation and O&M Building", 0.0, "B.02"),
                _item("B.02.4", "Regulatory Inspections", 6.0, "B.02"),
                _item("B.02.5", "HSE Prevention Plan", 0.0, "B.02"),
                _item("B.02.6", "Met Station Maintenance", 0.0, "B.02"),
                _item("B.02.7", "Blade Maintenance", 0.0, "B.02"),
                _item("B.02.8", "Vehicle or Special Equipment Maintenance", 8.0, "B.02"),
                _item("B.02.9", "Others", 0.0, "B.02"),
                _item("B.02.10", "Met Station 2", 0.0, "B.02"),
            ),
            inflation=0.0,
        ),
        _group(
            "B.03",
            "Maintain Site",
            (
                _item("B.03.1", "Vegetation management", 28.0, "B.03"),
                _item("B.03.2", "Repair roads", 20.0, "B.03"),
                _item("B.03.3", "Pest control", 10.0, "B.03"),
                _item("B.03.4", "Inspections", 10.0, "B.03"),
            ),
        ),
        _group(
            "B.04",
            "Clean Material",
            (
                _item("B.04.1", "Clean panel/blades", 3.0, "B.04"),
                _item("B.04.2", "Subscription to water supply", 1.0, "B.04"),
                _item("B.04.3", "Others", 1.0, "B.04"),
            ),
        ),
        _group(
            "B.05",
            "Security",
            (
                _item("B.05.1", "Surveillance systems", 30.0, "B.05"),
                _item("B.05.2", "Surveillance patrols", 15.0, "B.05"),
                _item("B.05.3", "Others", 5.0, "B.05"),
            ),
        ),
        _group(
            "B.06",
            "Insurance",
            (
                _item("B.06.1", "Operation All Risk with BI", 400.0, "B.06"),
                _item("B.06.2", "Third Party Liability", 30.0, "B.06"),
                _item("B.06.3", "Substation and O&M Building Coverage", 20.0, "B.06"),
                _item("B.06.4", "Spare parts insurance", 10.0, "B.06"),
                _item("B.06.5", "Wake effect compensation", 8.75, "B.06"),
            ),
        ),
        _group(
            "B.07",
            "Lease and property Tax",
            (
                _item("B.07.1", "Land Leases", 200.0, "B.07"),
                _item("B.07.2", "Property tax", 48.88, "B.07"),
            ),
        ),
        _group(
            "B.08",
            "Power Expenses",
            (
                _item("B.08.1", "Power consumption", 50.0, "B.08"),
                _item("B.08.2", "Grid usage fee", 30.0, "B.08"),
                _item("B.08.3", "Balancing costs", 13.72, "B.08"),
            ),
        ),
        _group(
            "B.09",
            "Telecom Fees",
            (
                _item("B.09.1", "Reporting Data", 0.0, "B.09", inflation=0.0),
                _item("B.09.2", "Telecom Connection", 0.0, "B.09", inflation=0.0),
            ),
            inflation=0.0,
        ),
        _group(
            "B.10",
            "Audit Accounting Legal",
            (
                _item("B.10.1", "Auditors closing", 8.0, "B.10"),
                _item("B.10.2", "Accounting closing", 8.0, "B.10"),
                _item("B.10.3", "Legal closing", 3.0, "B.10"),
                _item("B.10.4", "Accounting book-keeping", 3.0, "B.10"),
                _item("B.10.5", "Legal Formalities", 2.0, "B.10"),
            ),
        ),
        _group(
            "B.11",
            "Bank Fees",
            (
                _item("B.11.1", "Agency Fee", 20.0, "B.11", active_flags=B11_ACTIVE_FLAGS),
                _item("B.11.2", "Bonds", 0.0, "B.11", active_flags=B11_ACTIVE_FLAGS),
            ),
        ),
        _group(
            "B.12",
            "Environmental and Social",
            (
                _item("B.12.1", "Mitigation measures", 50.0, "B.12"),
                _item("B.12.2", "Agrinergie", 20.0, "B.12"),
                _item("B.12.3", "Fauna and Flora Monitoring", 30.0, "B.12"),
                _item("B.12.4", "E&S monitoring", 50.0, "B.12"),
                _item("B.12.5", "HSE visits", 50.0, "B.12"),
            ),
        ),
        _group(
            "B.13",
            "Contingencies",
            (
                _item(
                    "B.13.1",
                    "Contingency 6%",
                    6.0,
                    "B.13",
                    basis=OpexBasis.PCT_OF_SELECTED_GROUPS,
                    inflation=0.0,
                    selected=selected_groups,
                ),
            ),
            inflation=0.0,
            contingency_pct=6.0,
            contingency_method=OpexContingencyMethod.PERCENTAGE_OF_OPEX,
        ),
    ]
