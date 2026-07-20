"""Oborovo hierarchical OPEX model — production configuration.

Returns the fully-declared OpexModelInput for Oborovo's B.01-B.13 cost structure.
This is the single authoritative source of the hierarchical config for Oborovo.

No identity dispatch here — callers supply this model via the capability field
`ProjectInputs.hierarchical_opex_model`.  The presence of a non-None value is
the only dispatch signal; project name/code are never consulted.

Subitem data is sourced from `tests/fixtures/excel_oborovo_opex_structural_truth.json`
(the Excel-reconciled ground truth).  Numbers must not be changed without an
accompanying update to that fixture and a passing reconciliation test.
"""
from __future__ import annotations

from finco_core.opex.hierarchical import (
    OpexActivationMode,
    OpexActivationSchedule,
    OpexAmountBasis,
    OpexCalculationContext,
    OpexCategoryCalculationType,
    OpexCategoryInput,
    OpexEscalationConvention,
    OpexModelInput,
    OpexSubitemInput,
)

_HORIZON = 30  # operating years
_always_flags: tuple[bool, ...] = (True,) * _HORIZON
_never_flags: tuple[bool, ...] = (False,) * _HORIZON


def _always() -> OpexActivationMode:
    return OpexActivationMode.ALWAYS


def _manual(flags: tuple[bool, ...]) -> OpexActivationMode:
    return OpexActivationMode.MANUAL


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
    """Build and return the Oborovo OpexModelInput.

    Caller must also build OpexCalculationContext with:
      - senior_debt_tenor_years = inputs.financing.senior_tenor_years  (= 14)
      - external_annual_series = (("D", (0.0,)*30), ("F", (0.0,)*30))
    """
    # B.01 Technical Management  (inf=0.02, YEAR_1_AS_BASE)
    # subitems: 64 + 105 + 29 + 0
    b01 = _cat_sum("B.01", "Technical Management", (
        _si("B.01.1", "Technical Management - Core", 64.0),
        _si("B.01.row5", "Technical Management - Supervision", 105.0),
        _si("B.01.2", "Technical Management - Support", 29.0),
        _si("B.01.3", "Technical Management - Reserve", 0.0),
    ))

    # B.02 Infrastructure Maintenance  (inf=0.02, YEAR_1_AS_BASE)
    # B.02.1: 179 Y1-only; B.02.2: 117 Y2-30; B.02.4: 1 always; B.02.5: 64 always
    # Y1 total: (179 + 1 + 64) × 1.0 = 244;  Y2: (117 + 1 + 64) × 1.02 = 185.64
    _y1_only: tuple[bool, ...] = (True,) + (False,) * 29
    _y2_30: tuple[bool, ...] = (False,) + (True,) * 29
    b02 = _cat_sum("B.02", "Infrastructure Maintenance", (
        _si("B.02.1", "Infrastructure Maintenance - Y1 Mobilisation", 179.0,
            mode=OpexActivationMode.MANUAL, flags=_y1_only),
        _si("B.02.2", "Infrastructure Maintenance - Ongoing", 117.0,
            mode=OpexActivationMode.MANUAL, flags=_y2_30),
        _si("B.02.3", "Infrastructure Maintenance - Reserve A", 0.0),
        _si("B.02.4", "Infrastructure Maintenance - Spare Parts", 1.0),
        _si("B.02.5", "Infrastructure Maintenance - Major O&M", 64.0),
        _si("B.02.6", "Infrastructure Maintenance - Reserve B", 0.0),
    ))

    # B.03 Maintain Site  (inf=0.02, YEAR_1_AS_BASE)
    # 29.3 + 14.1 + 1.8 + 0(never)
    b03 = _cat_sum("B.03", "Maintain Site", (
        _si("B.03.1", "Maintain Site - Civil Works", 29.3),
        _si("B.03.2", "Maintain Site - Vegetation", 14.1),
        _si("B.03.row29", "Pest Control", 1.8),
        _si("B.03.3", "Maintain Site - Reserve",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
    ))

    # B.04 Clean Material  (inf=0.02, YEAR_1_AS_BASE)
    b04 = _cat_sum("B.04", "Clean Material", (
        _si("B.04.1", "Clean Material - Panels", 40.0),
        _si("B.04.2", "Clean Material - Infrastructure", 0.0),
        _si("B.04.9", "Clean Material - Reserve",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
    ))

    # B.05 Security  (inf=0.02, YEAR_1_AS_BASE)
    b05 = _cat_sum("B.05", "Security", (
        _si("B.05.1", "Security - Operations", 30.1),
        _si("B.05.2", "Security - Equipment", 0.0),
        _si("B.05.9", "Security - Reserve",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
    ))

    # B.06 Insurance  (inf=0.02, YEAR_1_AS_BASE)
    # 250 + 5 + 0(never) + 0(never) + 0(always)
    b06 = _cat_sum("B.06", "Insurance", (
        _si("B.06.1", "Insurance - Property All Risk", 250.0),
        _si("B.06.2", "Insurance - Liability", 5.0),
        _si("B.06.3", "Insurance - Reserve A",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
        _si("B.06.4", "Insurance - Reserve B",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
        _si("B.06.9", "Insurance - Miscellaneous", 0.0),
    ))

    # B.07 Lease & Property Tax  (inf=0.02, PRE_OPERATION_BASE)
    # The PRE_OPERATION_BASE convention matches Excel: Y1 = base × (1+inf)^1
    b07 = _cat_sum("B.07", "Lease & Property Tax", (
        _si("B.07.1", "Lease & Property Tax - Land Lease", 204.0),
        _si("B.07.4", "Lease & Property Tax - Property Tax", 0.0),
    ), convention=OpexEscalationConvention.PRE_OPERATION_BASE)

    # B.08 Power Expenses  (inf=0.0, YEAR_1_AS_BASE)
    # B.08.3: 372.9024, Y11-30 (first 10 = False, next 20 = True)
    _y11_30: tuple[bool, ...] = (False,) * 10 + (True,) * 20
    b08 = _cat_sum("B.08", "Power Expenses", (
        _si("B.08.1", "Power Expenses - Auxiliary Consumption", 40.0),
        _si("B.08.2", "Power Expenses - Grid Fees", 86.8608),
        _si("B.08.3", "Power Expenses - Repowering Reserve", 372.9024,
            mode=OpexActivationMode.MANUAL, flags=_y11_30),
        _si("B.08.8", "Power Expenses - Miscellaneous", 50.0),
    ), inflation=0.0)

    # B.09 Fees  (inf=0.0, YEAR_1_AS_BASE)
    b09 = _cat_sum("B.09", "Fees", (
        _si("B.09.1", "Fees - Management", 5.0),
        _si("B.09.2", "Fees - Regulatory", 4.0),
        _si("B.09.3", "Fees - Other", 5.0),
        _si("B.09.4", "Fees - Reserve",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
    ), inflation=0.0)

    # B.10 Audit & Accounting & Legal  (inf=0.02, YEAR_1_AS_BASE)
    # B.10.1: 16, Y1-2; B.10.2: 8, Y3-30; B.10.3: 8, always
    _y1_2: tuple[bool, ...] = (True, True) + (False,) * 28
    _y3_30: tuple[bool, ...] = (False, False) + (True,) * 28
    b10 = _cat_sum("B.10", "Audit & Accounting & Legal", (
        _si("B.10.1", "Audit&Accounting - Setup Phase", 16.0,
            mode=OpexActivationMode.MANUAL, flags=_y1_2),
        _si("B.10.2", "Audit&Accounting - Ongoing", 8.0,
            mode=OpexActivationMode.MANUAL, flags=_y3_30),
        _si("B.10.3", "Legal - Ongoing", 8.0),
        _si("B.10.4", "Audit&Accounting - Reserve A",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
        _si("B.10.5", "Audit&Accounting - Reserve B",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
        _si("B.10.6", "Audit&Accounting - Reserve C",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
    ))

    # B.11 Bank Fees  (inf=0.02, YEAR_1_AS_BASE)
    # B.11.3: 20, SENIOR_DEBT_TENOR_ACTIVE (active while year_index <= tenor)
    b11 = _cat_sum("B.11", "Bank Fees", (
        _si("B.11.1", "Bank Fees - Reserve A",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
        _si("B.11.2", "Bank Fees - Reserve B",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
        _si("B.11.3", "Bank Fees - Senior Debt Agency", 20.0,
            mode=OpexActivationMode.SENIOR_DEBT_TENOR_ACTIVE),
        _si("B.11.4", "Bank Fees - Reserve C",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
    ))

    # B.12 Environmental & Social  (inf=0.02, YEAR_1_AS_BASE)
    # B.12.1: 10 always; B.12.2: 0 never; B.12.3: 10 Y1-2; B.12.5: 10 Y1-2; B.12.6: 2 always
    b12 = _cat_sum("B.12", "Environmental & Social", (
        _si("B.12.1", "Environmental & Social - Monitoring", 10.0),
        _si("B.12.2", "Environmental & Social - Reserve",
            0.0, mode=OpexActivationMode.MANUAL, flags=_never_flags),
        _si("B.12.3", "Environmental & Social - Commissioning", 10.0,
            mode=OpexActivationMode.MANUAL, flags=_y1_2),
        _si("B.12.5", "Environmental & Social - Reporting", 10.0,
            mode=OpexActivationMode.MANUAL, flags=_y1_2),
        _si("B.12.6", "Environmental & Social - Community", 2.0),
    ))

    # B.13 Contingencies  (PERCENTAGE_OF_SELECTED_BASES, rate=4%)
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


def build_oborovo_opex_context(senior_debt_tenor_years: int) -> OpexCalculationContext:
    """Build the OpexCalculationContext for Oborovo.

    D (Salary & Payroll) and F (Taxes) are currently zero for Oborovo
    but must be explicit — _ext_value() asserts on absent codes.
    """
    zeros: tuple[float, ...] = (0.0,) * _HORIZON
    return OpexCalculationContext(
        senior_debt_tenor_years=senior_debt_tenor_years,
        external_annual_series=(("D", zeros), ("F", zeros)),
    )
