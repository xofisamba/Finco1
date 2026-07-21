"""Oborovo hierarchical OPEX model — production configuration.

Returns the fully-declared OpexModelInput for Oborovo's B.01-B.13 cost structure.
This is the single authoritative source of the hierarchical config for Oborovo.

No identity dispatch here — callers supply this model via the capability field
`ProjectInputs.hierarchical_opex_capability`.  The presence of a non-None value
is the only dispatch signal; project name/code are never consulted.

Subitem data is sourced from `tests/fixtures/excel_oborovo_opex_structural_truth.json`
(the Excel-reconciled ground truth).  Numbers must not be changed without an
accompanying update to that fixture and a passing reconciliation test.
"""
from __future__ import annotations

from finco_core.opex.hierarchical import (
    OpexActivationMode,
    OpexActivationSchedule,
    OpexAmountBasis,
    OpexCategoryCalculationType,
    OpexCategoryInput,
    OpexEscalationConvention,
    OpexModelInput,
    OpexSubitemInput,
)

_HORIZON = 30  # operating years
_always_flags: tuple[bool, ...] = (True,) * _HORIZON
_never_flags: tuple[bool, ...] = (False,) * _HORIZON


def _si(
    code: str,
    name: str,
    amount: float,
    *,
    mode: OpexActivationMode = OpexActivationMode.ALWAYS,
    flags: tuple[bool, ...] | None = None,
) -> OpexSubitemInput:
    schedule = None
    if mode == OpexActivationMode.MANUAL:
        assert flags is not None
        schedule = OpexActivationSchedule(
            annual_flags=flags,
            period_overrides=(),
        )
    return OpexSubitemInput(
        code=code,
        name=name,
        amount_basis=OpexAmountBasis.ANNUAL_RUN_RATE,
        base_amount_keur=amount,
        activation_mode=mode,
        activation_schedule=schedule,
    )


def _cat_sum(
    code: str,
    name: str,
    subitems: tuple[OpexSubitemInput, ...],
    *,
    inflation: float = 0.02,
    convention: OpexEscalationConvention = OpexEscalationConvention.YEAR_1_AS_BASE,
) -> OpexCategoryInput:
    return OpexCategoryInput(
        code=code,
        name=name,
        calculation_type=OpexCategoryCalculationType.SUBITEM_SUM,
        inflation_rate=inflation,
        escalation_convention=convention,
        subitems=subitems,
        percentage_rate=0.0,
        percentage_base_codes=(),
    )


def build_oborovo_hierarchical_opex_model() -> OpexModelInput:
    """Build and return the Oborovo OpexModelInput (all 61 B.01-B.12 subitems).

    Caller must also supply OpexCalculationContext with:
      - senior_debt_tenor_years = inputs.financing.senior_tenor_years  (= 14)
      - external_annual_series = (("D", (0.0,)*30), ("F", (0.0,)*30))

    Prefer build_oborovo_opex_capability() which packages both.
    """
    # ── Activation flag sets ─────────────────────────────────────────────────
    _y1_only: tuple[bool, ...] = (True,) + (False,) * 29
    _y2_30: tuple[bool, ...] = (False,) + (True,) * 29
    _y1_2: tuple[bool, ...] = (True, True) + (False,) * 28
    _y3_30: tuple[bool, ...] = (False, False) + (True,) * 28
    _y11_30: tuple[bool, ...] = (False,) * 10 + (True,) * 20

    # ── B.01 Technical Management  (inf=0.02, YEAR_1_AS_BASE) — 4 subitems ──
    b01 = _cat_sum("B.01", "Technical Management", (
        _si("B.01.1", "Asset Management Contract", 64.0),
        _si("row_5",  "Operation Management Contract", 105.0),
        _si("B.01.2", "Bazefield", 29.0),
        _si("B.01.3", "Others", 0.0),
    ))

    # ── B.02 Infrastructure Maintenance  (inf=0.02, YEAR_1_AS_BASE) — 17 subitems ──
    # Y1 total: 179 + 1 + 64 = 244;  Y2: (117 + 1 + 64) × 1.02 = 185.64
    b02 = _cat_sum("B.02", "Infrastructure Maintenance", (
        _si("B.02.1", "O&M – Preventive & Corrective Y1-2", 179.0,
            mode=OpexActivationMode.MANUAL, flags=_y1_only),
        _si("B.02.2", "O&M – Preventive & Corrective - Y3-30", 117.0,
            mode=OpexActivationMode.MANUAL, flags=_y2_30),
        _si("B.02.3", "Substation&O&M Building (included in O&M – Preventive & Corrective)",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
        _si("row_12", "Inverters / Kiosks / Transformers (included in O&M – Preventive & Corrective)",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
        _si("row_13", "Regulatory Inspections", 0.0),
        _si("B.02.4", "Inverter service contract / MRA", 1.0),
        _si("B.02.5", "Spare parts reprocurement (maintenance contract with contractors)", 64.0),
        _si("B.02.6", "Sponsor Operation Mgt - BESS", 0.0),
        _si("row_17", "BESS-EPC preventive and corrective maintenance - 5,5€/kW", 0.0),
        _si("row_18", "Spare part refru (included in EPC PM & CM)", 0.0),
        _si("row_19", "PCS Warranty extension (included in EPC PM & CM)", 0.0),
        _si("row_20", "BESS Perf guarantee ( Availability / RTE ) - 1500€/BESS", 0.0),
        _si("row_21", "BESS Preventive Maintenance (1k€/BESS)", 0.0),
        _si("row_22", "BESS Preventive Maintenance + Warranty Extension Y6 -> 10 - (5,5k€/BESS)", 0.0),
        _si("row_23", "BESS Preventive Maintenance + Warranty Extension Y11 -> 15 - (6k€/BESS)", 0.0),
        _si("row_24", "BESS Preventive Maintenance + Warranty Extension Y16 -> 20- (6,5k€/BESS)", 0.0),
        _si("row_25", "BESS Preventive Maintenance + Warranty Extension Y21 -> 25", 0.0),
    ))

    # ── B.03 Maintain Site  (inf=0.02, YEAR_1_AS_BASE) — 4 subitems ──
    b03 = _cat_sum("B.03", "Maintain Site", (
        _si("B.03.1", "Clean Site (included in O&M – Preventive & Corrective)", 29.3),
        _si("B.03.2", "Repair roads (included in O&M – Preventive & Corrective)", 14.1),
        _si("row_29", "Pest Control", 1.8),
        _si("B.03.3", "Others", 0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
    ))

    # ── B.04 Clean Material  (inf=0.02, YEAR_1_AS_BASE) — 3 subitems ──
    b04 = _cat_sum("B.04", "Clean Material", (
        _si("B.04.1", "Clean Panels (included in O&M – Preventive & Corrective)", 40.0),
        _si("B.04.2", "Subscription to water supply", 0.0),
        _si("B.04.9", "Others", 0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
    ))

    # ── B.05 Security  (inf=0.02, YEAR_1_AS_BASE) — 3 subitems ──
    b05 = _cat_sum("B.05", "Security", (
        _si("B.05.1", "Surveillance systems", 30.1),
        _si("B.05.2", "Surveillance patrols", 0.0),
        _si("B.05.9", "Others", 0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
    ))

    # ── B.06 Insurance  (inf=0.02, YEAR_1_AS_BASE) — 5 subitems ──
    b06 = _cat_sum("B.06", "Insurance", (
        _si("B.06.1", "Operation All Risk with Business Interruption (OAR-BI)", 250.0),
        _si("B.06.2", "Third Party Liability (TPL)", 5.0),
        _si("B.06.3",
            "Substation and O&M Building Coverage (DO) (TBD by the insurance team depending on project)",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
        _si("B.06.4",
            "Spare parts insurance (TBD by the insurance team depending on project)",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
        _si("B.06.9", "Storage Insurance", 0.0),
    ))

    # ── B.07 Lease & Property Tax  (inf=0.02, PRE_OPERATION_BASE) — 2 subitems ──
    # PRE_OPERATION_BASE: Y1 = base × (1+inf)^1 (matches Excel convention)
    b07 = _cat_sum("B.07", "Lease & Property Tax", (
        _si("B.07.1", "Land Leases", 204.0),
        _si("B.07.4", "Property tax", 0.0),
    ), convention=OpexEscalationConvention.PRE_OPERATION_BASE)

    # ── B.08 Power Expenses  (inf=0.0, YEAR_1_AS_BASE) — 4 subitems ──
    # B.08.3: 372.9024, MANUAL active Y11-30 (first 10 false, next 20 true)
    b08 = _cat_sum("B.08", "Power Expenses", (
        _si("B.08.1", "Power consumption", 40.0),
        _si("B.08.2", "Grid Usage fee", 86.8608),
        _si("B.08.3", "Balancing costs", 372.9024,
            mode=OpexActivationMode.MANUAL, flags=_y11_30),
        _si("B.08.8", "Grid usage fee Storage", 50.0),
    ), inflation=0.0)

    # ── B.09 Fees  (inf=0.0, YEAR_1_AS_BASE) — 4 subitems ──
    b09 = _cat_sum("B.09", "Fees", (
        _si("B.09.1", "Reporting Data", 5.0),
        _si("B.09.2", "Local concession fee", 4.0),
        _si("B.09.3", "SCADA (to be included in O&M contract)", 5.0),
        _si("B.09.4", "Alarm/Security (included in Reporting Data)",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
    ), inflation=0.0)

    # ── B.10 Audit & Accounting & Legal  (inf=0.02, YEAR_1_AS_BASE) — 6 subitems ──
    b10 = _cat_sum("B.10", "Audit & Accounting & Legal", (
        _si("B.10.1", "Auditors closing Y1&2", 16.0,
            mode=OpexActivationMode.MANUAL, flags=_y1_2),
        _si("B.10.2", "Auditors closing >=Y3", 8.0,
            mode=OpexActivationMode.MANUAL, flags=_y3_30),
        _si("B.10.3", "Accounting closing", 8.0),
        _si("B.10.4", "Legal closing (included in Accounting Closing)",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
        _si("B.10.5", "Accounting book-keeping (included in Accounting Closing)",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
        _si("B.10.6", "Others",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
    ))

    # ── B.11 Bank Fees  (inf=0.02, YEAR_1_AS_BASE) — 4 subitems ──
    # B.11.3: 20 kEUR, SENIOR_DEBT_TENOR_ACTIVE (active while year_index <= tenor)
    b11 = _cat_sum("B.11", "Bank Fees", (
        _si("B.11.1", "Agency Fee (included in Bank Fees)",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
        _si("B.11.2", "Bonds",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
        _si("B.11.3", "Bank Fees", 20.0,
            mode=OpexActivationMode.SENIOR_DEBT_TENOR_ACTIVE),
        _si("B.11.4", "Others",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
    ))

    # ── B.12 Environmental & Social  (inf=0.02, YEAR_1_AS_BASE) — 5 subitems ──
    b12 = _cat_sum("B.12", "Environmental & Social", (
        _si("B.12.1", "Mitigation measures ", 10.0),
        _si("B.12.2", "Agrinergie",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
        _si("B.12.3", "Fauna&Flaura Monitoring (Y1&2)", 10.0,
            mode=OpexActivationMode.MANUAL, flags=_y1_2),
        _si("B.12.5", "E&S monitoring (Y1&2)", 10.0,
            mode=OpexActivationMode.MANUAL, flags=_y1_2),
        _si("B.12.6", "HSE: Monthly visit + yearly visit + elect/fire/other controls", 2.0),
    ))

    # ── B.13 Contingencies  (PERCENTAGE_OF_SELECTED_BASES, rate=4%) ──
    # Bases: B.01..B.12 + D (Salary) + F (Taxes)
    b13 = OpexCategoryInput(
        code="B.13",
        name="Contingencies",
        calculation_type=OpexCategoryCalculationType.PERCENTAGE_OF_SELECTED_BASES,
        inflation_rate=0.0,
        escalation_convention=OpexEscalationConvention.YEAR_1_AS_BASE,
        subitems=(),
        percentage_rate=0.04,
        percentage_base_codes=(
            "B.01", "B.02", "B.03", "B.04", "B.05",
            "B.06", "B.07", "B.08", "B.09", "B.10",
            "B.11", "B.12", "D", "F",
        ),
    )

    return OpexModelInput(
        categories=(b01, b02, b03, b04, b05, b06, b07, b08, b09, b10, b11, b12, b13),
    )


def build_oborovo_opex_capability():
    """Build the HierarchicalOpexCapability for Oborovo.

    NOT called by generic dispatch — used only by the project factory.
    D (Salary & Payroll) and F (Taxes) are currently zero for Oborovo
    but must be explicit — _ext_value() asserts on absent codes.
    """
    from finco_core.opex._capability import HierarchicalOpexCapability
    _zeros: tuple[float, ...] = (0.0,) * _HORIZON
    return HierarchicalOpexCapability(
        opex_model=build_oborovo_hierarchical_opex_model(),
        external_annual_series=(("D", _zeros), ("F", _zeros)),
    )
