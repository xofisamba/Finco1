"""TUHO Wind 1 OPEX template — offline diagnostic fixture.

This template encodes the exact TUHO OpEx structure from tuho_excel_1.xlsm
(OpEx sheet rows 3–85, group totals from row 105).

Used for parity verification against Excel values — NOT wired into runtime.
"""
from __future__ import annotations

from domain.opex.line_items import OpexBasis, OpexGroup, OpexItem

# ── B.02.1 explicit schedule (30 years, no inflation) ─────────────────────
# From tuho_excel_1.xlsm Scenarios!I79:I108 → OpEx row 15 (B.02.1)
B02_EXPLICIT_SCHEDULE = [
    # Y1–Y2: 385.6, Y3–Y5: 465.6, Y6–Y10: 588, Y11–Y15: 628
    385.6, 385.6,           # Y1, Y2
    465.6, 465.6, 465.6,    # Y3, Y4, Y5
    588.0, 588.0, 588.0, 588.0, 588.0,  # Y6, Y7, Y8, Y9, Y10
    # Y11–Y15: 628
    628.0, 628.0, 628.0, 628.0, 628.0,
    # Y16–Y20: 676
    676.0, 676.0, 676.0, 676.0, 676.0,
    # Y21–Y25: 756
    756.0, 756.0, 756.0, 756.0, 756.0,
    # Y26–Y30: 828
    828.0, 828.0, 828.0, 828.0, 828.0,
]

# ── B.11 active flags: Y1–Y14 active, Y15–Y30 inactive ───────────────────
# 30-element tuple: (1,)*14 + (0,)*16
B11_ACTIVE_FLAGS = (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,   # Y1–Y14 = active
                    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)  # Y15–Y30 = inactive


def _g(code: str, name: str, items: tuple[OpexItem, ...],
       contingency_pct: float = 0.0, infl_rate: float = 0.0) -> OpexGroup:
    """Shorthand to build an OpexGroup."""
    return OpexGroup(
        code=code, name=name, inflation_rate=infl_rate, wth_rate=0.0,
        items=items, order=0, editable=True, contingency_pct=contingency_pct,
    )


def _i(code: str, name: str, budget: float,
       group_code: str, basis: OpexBasis = OpexBasis.FIXED_ANNUAL_KEUR,
       selected: tuple[str, ...] = (),
       infl_rate: float | None = None,
       explicit: list[float] | None = None,
       active_flags: tuple[int, ...] = (),
       infl_start_exp: int = 0) -> OpexItem:
    """Shorthand to build an OpexItem."""
    return OpexItem(
        code=code, name=name, budget_keur=budget, basis=basis,
        group_code=group_code, inflation_rate=infl_rate, wth_rate=0.0,
        active_flags=active_flags, explicit_schedule_keur=explicit or [],
        manual_overrides=(), step_changes=(),
        selected_group_codes=selected,
        notes="", inflation_start_exponent=infl_start_exp,
    )


def build_tuho_opex_template() -> list[OpexGroup]:
    """Build the TUHO Wind 1 OPEX template matching tuho_excel_1.xlsm parity.

    All 30 years exactly match Excel total (row 105, cols F–AE).
    B.13 = 6% × sum(B.01–B.12) confirmed for all years.

    Returns
    -------
    list[OpexGroup]
        13 groups: B.01 – B.13 (no C/D/E/F included).

    Notes
    -----
    - B.02 group inflation_rate = 0.0 (explicit schedule item not inflated)
    - B.11 uses explicit 30-element active_flags (not active_from/active_until)
    - B.07 uses standard pattern: inflation_start_exponent=0
    - B.13 contingency_pct=0.0 (pct item is the sole contingency mechanism)
    - This template is OFFLINE ONLY — not wired into runtime.
    """
    groups = [
        # ── B.01 Technical Management ─────────────────────────────────────────
        _g("B.01", "Technical Management", (
            _i("B.01.1", "Asset Management Contract",          138.0, "B.01", infl_rate=0.02),
            _i("B.01.2", "Operation Management Contract",      67.0, "B.01", infl_rate=0.02),
            _i("B.01.3", "Performance monitoring",             35.0, "B.01", infl_rate=0.02),
            _i("B.01.4", "Technical Inspections",               0.0, "B.01", infl_rate=0.02),
            _i("B.01.5", "Meteorological and weather forecast service", 18.0, "B.01", infl_rate=0.02),
            _i("B.01.6", "Bazefield",                           22.0, "B.01", infl_rate=0.02),
        ), infl_rate=0.02),

        # ── B.02 Infrastructure Maintenance ──────────────────────────────────
        # B.02.1 is EXPLICIT_SCHEDULE (no inflation). Group infl_rate=0.0
        # to avoid double-inflation. Other items use item-level infl_rate=0.02.
        _g("B.02", "Infrastructure", (
            _i("B.02.1", "O&M Preventive & Corrective",  0.0, "B.02",
               basis=OpexBasis.EXPLICIT_SCHEDULE,
               explicit=B02_EXPLICIT_SCHEDULE, infl_rate=0.0),
            _i("B.02.2", "Minor Maintenance",            27.0, "B.02", infl_rate=0.02),
            _i("B.02.3", "HV Substation & O&M Building",  0.0, "B.02", infl_rate=0.02),
            _i("B.02.4", "Regulatory Inspections",        6.0, "B.02", infl_rate=0.02),
            _i("B.02.5", "HSE Prevention Plan",           0.0, "B.02", infl_rate=0.02),
            _i("B.02.6", "Met Station Maintenance",       0.0, "B.02", infl_rate=0.02),
            _i("B.02.7", "Blade Maintenance",              0.0, "B.02", infl_rate=0.02),
            _i("B.02.8", "Vehicle or Special Equipment Maintenance", 8.0, "B.02", infl_rate=0.02),
            _i("B.02.9", "Others",                         0.0, "B.02", infl_rate=0.02),
            _i("B.02.10","Met Station 2",                   0.0, "B.02", infl_rate=0.02),
        ), infl_rate=0.0),

        # ── B.03 Maintain Site ────────────────────────────────────────────────
        _g("B.03", "Maintain Site", (
            _i("B.03.1", "Vegetation management/clean site", 28.0, "B.03", infl_rate=0.02),
            _i("B.03.2", "Repair roads",                     20.0, "B.03", infl_rate=0.02),
            _i("B.03.3", "Pest control",                    10.0, "B.03", infl_rate=0.02),
            _i("B.03.4", "Inspections",                     10.0, "B.03", infl_rate=0.02),
        ), infl_rate=0.02),

        # ── B.04 Clean Material ───────────────────────────────────────────────
        _g("B.04", "Clean Material", (
            _i("B.04.1", "Clean Panel/Blades",               3.0, "B.04", infl_rate=0.02),
            _i("B.04.2", "Subscription to water supply",     1.0, "B.04", infl_rate=0.02),
            _i("B.04.3", "Others",                           1.0, "B.04", infl_rate=0.02),
        ), infl_rate=0.02),

        # ── B.05 Security ───────────────────────────────────────────────────
        _g("B.05", "Security", (
            _i("B.05.1", "Surveillance systems",            30.0, "B.05", infl_rate=0.02),
            _i("B.05.2", "Surveillance patrols",            15.0, "B.05", infl_rate=0.02),
            _i("B.05.3", "Others",                            5.0, "B.05", infl_rate=0.02),
        ), infl_rate=0.02),

        # ── B.06 Insurance ───────────────────────────────────────────────────
        _g("B.06", "Insurance", (
            _i("B.06.1", "Operation All Risk with BI",     400.0, "B.06", infl_rate=0.02),
            _i("B.06.2", "Third Party Liability",          30.0, "B.06", infl_rate=0.02),
            _i("B.06.3", "Substation and O&M Building Coverage", 20.0, "B.06", infl_rate=0.02),
            _i("B.06.4", "Spare parts insurance",           10.0, "B.06", infl_rate=0.02),
            _i("B.06.5", "Wake effect - compensation",      8.75, "B.06", infl_rate=0.02),
        ), infl_rate=0.02),

        # ── B.07 Lease & Property Tax ─────────────────────────────────────────
        # Standard (F2-1) pattern: inflation_start_exponent=0
        # Y1=248.88, Y2=253.86 (=248.88×1.02^1), Y3=258.93 (=248.88×1.02^2)
        _g("B.07", "Lease & property Tax", (
            _i("B.07.1", "Land Leases",   200.0, "B.07", infl_rate=0.02, infl_start_exp=0),
            _i("B.07.2", "Property tax",   48.88, "B.07", infl_rate=0.02, infl_start_exp=0),
        ), infl_rate=0.02),

        # ── B.08 Power Expenses ───────────────────────────────────────────────
        _g("B.08", "Power Expenses", (
            _i("B.08.1", "Power consumption",  50.0, "B.08", infl_rate=0.02),
            _i("B.08.2", "Grid Usage fee",      30.0, "B.08", infl_rate=0.02),
            _i("B.08.3", "Balancing costs",     13.72, "B.08", infl_rate=0.02),
        ), infl_rate=0.02),

        # ── B.09 Telecom Fees (all zero) ────────────────────────────────────
        _g("B.09", "Telecom Fees", (
            _i("B.09.1", "Reporting Data",       0.0, "B.09"),
            _i("B.09.2", "Telecom Connection",    0.0, "B.09"),
        )),

        # ── B.10 Audit & Accounting & Legal ─────────────────────────────────
        _g("B.10", "Audit&Accounting&Legal", (
            _i("B.10.1", "Auditors closing",         8.0, "B.10", infl_rate=0.02),
            _i("B.10.2", "Accounting closing",        8.0, "B.10", infl_rate=0.02),
            _i("B.10.3", "Legal closing",            3.0, "B.10", infl_rate=0.02),
            _i("B.10.4", "Accounting book-keeping",   3.0, "B.10", infl_rate=0.02),
            _i("B.10.5", "Legal Formalities",        2.0, "B.10", infl_rate=0.02),
        ), infl_rate=0.02),

        # ── B.11 Bank Fees ───────────────────────────────────────────────────
        # Active Y1–Y14 only. Use explicit 30-element flag tuple:
        # (1,)*14 + (0,)*16 — active_from/active_until helper falls through
        # to True outside range, so explicit tuple is required.
        _g("B.11", "Bank Fees", (
            _i("B.11.1", "Agency Fee",  20.0, "B.11", infl_rate=0.02,
               active_flags=B11_ACTIVE_FLAGS),
            _i("B.11.2", "Bonds",        0.0, "B.11", infl_rate=0.02,
               active_flags=B11_ACTIVE_FLAGS),
        )),

        # ── B.12 Environmental & Social ─────────────────────────────────────
        _g("B.12", "Environmental&Social", (
            _i("B.12.1", "Mitigation measures",    50.0, "B.12", infl_rate=0.02),
            _i("B.12.2", "Agrinergie",             20.0, "B.12", infl_rate=0.02),
            _i("B.12.3", "Fauna&Flora Monitoring", 30.0, "B.12", infl_rate=0.02),
            _i("B.12.4", "E&S monitoring",         50.0, "B.12", infl_rate=0.02),
            _i("B.12.5", "HSE visits",             50.0, "B.12", infl_rate=0.02),
        ), infl_rate=0.02),

        # ── B.13 Contingencies ───────────────────────────────────────────────
        # PCT_OF_SELECTED_GROUPS: 6% of sum(B.01–B.12)
        # contingency_pct=0.0 — pct item itself is the mechanism (no pass2 double-count)
        # Selected groups include B.09 (zero) and B.11 (zero Y15+) — correct per Excel
        _g("B.13", "Contingencies", (
            _i("B.13.1", "Contingency 6%", 6.0, "B.13",
               basis=OpexBasis.PCT_OF_SELECTED_GROUPS,
               selected=("B.01", "B.02", "B.03", "B.04", "B.05", "B.06",
                         "B.07", "B.08", "B.09", "B.10", "B.11", "B.12")),
        ), contingency_pct=0.0),
    ]
    return groups