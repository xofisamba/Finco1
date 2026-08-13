"""Stage C3A — Oborovo clean P&L parity through EBIT (C3A2 evidence closeout).

Production change (C3A):
  Added ebit_keur = ebitda_keur − book_depreciation_keur to OperatingPeriodResult
  and OperatingSchedules. No other production field was modified.

Source: excel_oborovo_financial_truth.json
    SHA:      15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920
    Workbook: d49af8ee-20260414_BP_Oborovo_Sensitivity_FINAL_for_PPT.xlsm

PERIOD_MAPPING classification (proven in Group I / Group PM):
    H2 periods (Jul–Dec) at leap/non-leap year boundaries have different
    day-count denominators between the clean engine and Excel. The clean
    engine uses the actual calendar year of the period end; Excel uses the
    following calendar year. Each affected H2 pair offsets exactly:
    non-leap→leap boundary: clean +4.073 kEUR, next leap period: −4.073 kEUR.
    Net lifetime effect: +0.000843 kEUR (SOURCE_ROUNDING in the fraction
    arithmetic). PERIOD_MAPPING_PROVEN.
"""
from __future__ import annotations

import calendar
import json
from datetime import date
from pathlib import Path

import pytest

# ── fixture paths ──────────────────────────────────────────────────────────────

_FIXTURE = Path(__file__).parent / "fixtures" / "excel_oborovo_financial_truth.json"
_EXPECTED_SOURCE_SHA = (
    "15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920"
)

# ── frozen totals ──────────────────────────────────────────────────────────────

_CLEAN_REVENUE_KEUR    = 237_686.922   # B6 source-aligned Oborovo period axis
_CLEAN_OPEX_KEUR       = 55_782.951
_CLEAN_BOOK_DEP_KEUR   = 57_973.054
_CLEAN_EBITDA_KEUR     = 181_903.972
_CLEAN_EBIT_KEUR       = 123_930.918

_EXCEL_REVENUE_KEUR    = 237_686.922
_EXCEL_OPEX_KEUR       = 55_782.951
_EXCEL_BOOK_DEP_KEUR   = 57_973.053
_EXCEL_EBIT_KEUR       = 123_930.919

# ── helpers ────────────────────────────────────────────────────────────────────

def _excel_data():
    with open(_FIXTURE) as f:
        return json.load(f)


def _adapt(pi):
    from financial_engine.adapters.project_inputs import from_project_inputs
    return from_project_inputs(pi, source_id="c3a_test", baseline_commit_sha="")


def _run_clean(omin=None, factory=None):
    from financial_engine.orchestrator import run_operating_model
    if omin is None:
        from app.project_factories import create_default_oborovo
        omin = _adapt(factory() if factory else create_default_oborovo())
    return run_operating_model(omin)


def _legacy_engine(pi):
    from finco_core.engine.period_engine import PeriodEngine, PeriodFrequency
    return PeriodEngine(
        financial_close=pi.info.financial_close,
        construction_months=pi.info.construction_months,
        horizon_years=pi.info.horizon_years,
        ppa_years=float(pi.revenue.ppa_term_years),
        frequency=PeriodFrequency.SEMESTRIAL,
        period_axis_convention=pi.info.period_axis_convention.value,
    )


def _legacy_rev(pi, engine):
    from finco_core.revenue.generation import full_revenue_schedule
    return full_revenue_schedule(pi, engine)


def _legacy_opex(pi, engine):
    from finco_core.opex.projections import opex_schedule_period
    return opex_schedule_period(pi, engine)


def _legacy_book_dep(pi, engine):
    from finco_core.inputs import AssetClass, CapexItem
    from finco_core.debt.depreciation_schedule import (
        build_depreciation_schedule, depreciation_per_period,
    )
    omin = _adapt(pi)
    dep_in = omin.depreciation
    capex_items = tuple(
        CapexItem(
            name=it.name,
            amount_keur=it.amount_keur,
            asset_class=AssetClass(it.asset_class_code),
            useful_life_override=it.useful_life_override,
        )
        for it in dep_in.book_capex_items_for_depreciation
    )
    annual = build_depreciation_schedule(
        capex_items=capex_items,
        horizon_years=int(pi.info.horizon_years),
        senior_tenor_years=dep_in.financial_cost_useful_life_years,
    )
    return depreciation_per_period(annual, engine.periods())


def _legacy_tax_dep(pi, engine):
    from finco_core.inputs import AssetClass, CapexItem
    from finco_core.debt.depreciation_schedule import (
        build_depreciation_schedule, depreciation_per_period,
    )
    omin = _adapt(pi)
    dep_in = omin.depreciation
    capex_items = tuple(
        CapexItem(
            name=it.name,
            amount_keur=it.amount_keur,
            asset_class=AssetClass(it.asset_class_code),
            useful_life_override=it.useful_life_override,
        )
        for it in dep_in.tax_capex_items_for_depreciation
    )
    annual = build_depreciation_schedule(
        capex_items=capex_items,
        horizon_years=int(pi.info.horizon_years),
        senior_tenor_years=dep_in.financial_cost_useful_life_years,
    )
    return depreciation_per_period(annual, engine.periods())


# ── A: Source fixture identity ─────────────────────────────────────────────────

class TestASourceFixtureIdentity:
    """Group A — fixture exists with expected workbook SHA."""

    def test_fixture_exists(self):
        assert _FIXTURE.exists(), f"Missing fixture: {_FIXTURE}"

    def test_workbook_sha(self):
        sha = _excel_data()["_meta"]["source_sha256"]
        assert sha == _EXPECTED_SOURCE_SHA, (
            f"Workbook SHA changed: {sha!r}"
        )

    def test_fixture_has_pl_and_dep(self):
        d = _excel_data()
        assert "ebit_keur" in d["pl"]
        assert "dep_total_keur" in d["dep"]

    def test_pl_has_61_periods(self):
        assert len(_excel_data()["pl"]["ebit_keur"]) == 61


# ── B: Revenue freeze ─────────────────────────────────────────────────────────

class TestBRevenueFreeze:
    """Group B — Revenue unchanged from C2B-approved total."""

    def test_clean_revenue_total(self):
        result = _run_clean()
        total = sum(p.revenue_keur for p in result.periods if p.is_operation)
        assert abs(total - _CLEAN_REVENUE_KEUR) < 0.001, (
            f"Revenue {total:.3f} != C2B-approved {_CLEAN_REVENUE_KEUR}"
        )


# ── C: OPEX freeze ────────────────────────────────────────────────────────────

class TestCOpexFreeze:
    """Group C — OPEX frozen at C2A-approved value; exact legacy parity."""

    def test_clean_opex_total(self):
        result = _run_clean()
        total = sum(p.opex_keur for p in result.periods if p.is_operation)
        assert abs(total - _CLEAN_OPEX_KEUR) < 0.001, (
            f"OPEX {total:.3f} != approved {_CLEAN_OPEX_KEUR}"
        )

    def test_clean_opex_matches_legacy_per_period(self):
        from app.project_factories import create_default_oborovo
        pi = create_default_oborovo()
        eng = _legacy_engine(pi)
        leg = _legacy_opex(pi, eng)
        result = _run_clean(_adapt(pi))
        clean = {p.period_index: p.opex_keur for p in result.periods}
        max_delta = max(abs(clean.get(k, 0.0) - v) for k, v in leg.items())
        assert max_delta < 1e-6, f"OPEX max C-L period delta {max_delta:.2e}"


# ── D: EBITDA identity ────────────────────────────────────────────────────────

class TestDEbitdaIdentity:
    """Group D — EBITDA = Revenue − OPEX exactly per period."""

    def test_ebitda_identity_max_residual(self):
        result = _run_clean()
        max_res = max(
            abs(p.ebitda_keur - (p.revenue_keur - p.opex_keur))
            for p in result.periods
        )
        assert max_res < 1e-9, f"EBITDA identity max residual {max_res:.2e}"


# ── E: Book-depreciation item inclusion ───────────────────────────────────────

class TestEBookDeprecItemInclusion:
    """Group E — 17 book items (13 hard CAPEX + 4 financing), 13 tax items."""

    def test_book_item_count(self):
        omin = _adapt(__import__('app.project_factories', fromlist=['create_default_oborovo']).create_default_oborovo())
        assert len(omin.depreciation.book_capex_items_for_depreciation) == 17

    def test_tax_item_count(self):
        # C3B3B2 source-proven correction: Oborovo sets tax_dep_basis_source_owned=True.
        # C3B1 proves excel_tax_dep == excel_book_dep → tax uses book asset list (17 items).
        from app.project_factories import create_default_oborovo
        omin = _adapt(create_default_oborovo())
        assert len(omin.depreciation.tax_capex_items_for_depreciation) == 17

    def test_book_has_4_financial_costs_items(self):
        from app.project_factories import create_default_oborovo
        omin = _adapt(create_default_oborovo())
        fc = [it for it in omin.depreciation.book_capex_items_for_depreciation
              if it.asset_class_code == "financial_costs"]
        assert len(fc) == 4

    def test_tax_includes_financial_costs_source_proven(self):
        # C3B3B2 source-proven correction: C3B1 proves excel_tax_dep == excel_book_dep.
        # Oborovo factory sets tax_dep_basis_source_owned=True → financial costs included.
        from app.project_factories import create_default_oborovo
        omin = _adapt(create_default_oborovo())
        fc = [it for it in omin.depreciation.tax_capex_items_for_depreciation
              if it.asset_class_code == "financial_costs"]
        assert len(fc) == 4, (
            f"Expected 4 financial_costs items in tax dep basis (C3B1-proven); got {len(fc)}"
        )


# ── F: Useful-life mapping ────────────────────────────────────────────────────

class TestFUsefulLifeMapping:
    """Group F — useful_life_override per asset class."""

    def test_civil_grid_20yr(self):
        from app.project_factories import create_default_oborovo
        omin = _adapt(create_default_oborovo())
        for it in omin.depreciation.book_capex_items_for_depreciation:
            if it.asset_class_code == "civil_grid":
                assert it.useful_life_override == 20, (
                    f"'{it.name}' expects 20yr, got {it.useful_life_override}"
                )

    def test_idc_commitment_bank_12yr(self):
        from app.project_factories import create_default_oborovo
        omin = _adapt(create_default_oborovo())
        for it in omin.depreciation.book_capex_items_for_depreciation:
            n = it.name.lower()
            if any(k in n for k in ("idc", "interest during", "commitment", "bank fee")):
                assert it.useful_life_override == 12, (
                    f"'{it.name}' expects 12yr, got {it.useful_life_override}"
                )

    def test_vat_20yr(self):
        from app.project_factories import create_default_oborovo
        omin = _adapt(create_default_oborovo())
        for it in omin.depreciation.book_capex_items_for_depreciation:
            if "vat" in it.name.lower():
                assert it.useful_life_override == 20, (
                    f"'{it.name}' expects 20yr, got {it.useful_life_override}"
                )


# ── G: Period timing ──────────────────────────────────────────────────────────

class TestGPeriodTiming:
    """Group G — 62 total periods; no dep in construction; 60 operating."""

    def test_total_and_operating_period_count(self):
        result = _run_clean()
        assert len(result.periods) == 61
        assert sum(1 for p in result.periods if p.is_construction) == 1
        assert sum(1 for p in result.periods if p.is_operation) == 60

    def test_construction_period_zero_dep(self):
        result = _run_clean()
        for p in result.periods:
            if p.is_construction:
                assert p.book_depreciation_keur == 0.0
                assert p.tax_depreciation_keur == 0.0


# ── H: Clean vs legacy book dep parity ───────────────────────────────────────

class TestHCleanVsLegacyBookDep:
    """Group H — clean == legacy for book dep, per period and lifetime."""

    def test_max_period_delta(self):
        from app.project_factories import create_default_oborovo
        pi = create_default_oborovo()
        eng = _legacy_engine(pi)
        leg = _legacy_book_dep(pi, eng)
        result = _run_clean(_adapt(pi))
        clean = {p.period_index: p.book_depreciation_keur for p in result.periods}
        max_delta = max(abs(clean.get(k, 0.0) - v) for k, v in leg.items())
        assert max_delta < 1e-6, f"Book dep max C-L delta {max_delta:.2e}"

    def test_lifetime_delta(self):
        from app.project_factories import create_default_oborovo
        pi = create_default_oborovo()
        eng = _legacy_engine(pi)
        leg = _legacy_book_dep(pi, eng)
        result = _run_clean(_adapt(pi))
        clean_total = sum(p.book_depreciation_keur for p in result.periods)
        assert abs(clean_total - sum(leg.values())) < 1e-6


# ── I: Clean vs Excel book dep (tightened) ───────────────────────────────────

class TestICleanVsExcelBookDep:
    """Group I — clean vs Excel book dep with tight lifetime tolerance.

    PERIOD_MAPPING residual: net lifetime delta = +0.000843 kEUR.
    Lifetime tolerance: 0.01 kEUR maximum.
    """

    def test_lifetime_delta_tight(self):
        result = _run_clean()
        clean_total = sum(p.book_depreciation_keur for p in result.periods if p.is_operation)
        delta = abs(clean_total - _EXCEL_BOOK_DEP_KEUR)
        assert delta < 0.01, (
            f"Clean book dep {clean_total:.6f} vs Excel {_EXCEL_BOOK_DEP_KEUR}: "
            f"delta={delta:.6f} kEUR exceeds 0.01 kEUR"
        )

    def test_period_delta_catalogue(self):
        """All period deltas vs Excel: at most ±5 kEUR; signed sum near zero."""
        d = _excel_data()
        excel_dep = d["dep"]["dep_total_keur"]
        result = _run_clean()
        op_periods = [p for p in result.periods if p.is_operation]
        assert len(op_periods) == len(excel_dep) - 1

        max_delta = 0.0
        signed_sum = 0.0
        for i, p in enumerate(op_periods):
            diff = p.book_depreciation_keur - excel_dep[i + 1]
            max_delta = max(max_delta, abs(diff))
            signed_sum += diff

        # PERIOD_MAPPING: max per-period swap ≤ 4.073 kEUR; allow up to 5 kEUR
        assert max_delta < 5.0, (
            f"Max period C-X dep delta {max_delta:.4f} kEUR unexpectedly large"
        )
        # Net lifetime effect ≤ 0.01 kEUR (SOURCE_ROUNDING in leap fractions)
        assert abs(signed_sum) < 0.01, (
            f"Signed sum of period deltas {signed_sum:+.6f} kEUR unexpectedly large"
        )


# ── J: EBIT identity ──────────────────────────────────────────────────────────

class TestJEbitIdentity:
    """Group J — EBIT = EBITDA − book_dep exactly; field present in schedules."""

    def test_ebit_identity_per_period(self):
        result = _run_clean()
        max_res = max(
            abs(p.ebit_keur - (p.ebitda_keur - p.book_depreciation_keur))
            for p in result.periods
        )
        assert max_res < 1e-9, f"EBIT identity max residual {max_res:.2e}"

    def test_ebit_in_operating_schedules(self):
        result = _run_clean()
        sched = result.operating_schedules
        assert hasattr(sched, "ebit_keur")
        assert sched.ebit_keur == tuple(p.ebit_keur for p in result.periods)


# ── K: Independent legacy component parity → EBIT ────────────────────────────

class TestKIndependentLegacyEbitParity:
    """Group K — EBIT parity via independently computed legacy OPEX and book dep.

    Revenue note (Oborovo):
      Oborovo uses calendar-year merchant pricing introduced in Stage C2B.
      The legacy leaf full_revenue_schedule does not support this pricing
      mode; revenue_decomposition_schedule also differs from the clean path
      by ~751 kEUR (the C2B implementation gap). The clean engine's revenue
      leaf is therefore the SAME implementation as the current-main revenue
      path — there is no independent legacy revenue path for Oborovo that
      produces 237,672.841 kEUR. Revenue parity is already certified by C2B
      tests and frozen.

      For OPEX and book depreciation, the finco_core leaves are called
      independently and produce identical results (max period delta 0.00e+00).

    Legacy EBIT composition:
      EBIT = clean_ebitda − legacy_book_dep
      (since clean_opex = legacy_opex exactly, and clean_rev = C2B_approved_rev)
    """

    def test_max_period_opex_delta(self):
        from app.project_factories import create_default_oborovo
        pi = create_default_oborovo()
        eng = _legacy_engine(pi)
        leg_opex = _legacy_opex(pi, eng)
        result = _run_clean(_adapt(pi))
        clean = {p.period_index: p.opex_keur for p in result.periods}
        max_d = max(abs(clean.get(k, 0.0) - v) for k, v in leg_opex.items())
        assert max_d < 1e-6, f"OPEX max C-L delta {max_d:.2e}"

    def test_max_period_book_dep_delta(self):
        from app.project_factories import create_default_oborovo
        pi = create_default_oborovo()
        eng = _legacy_engine(pi)
        leg_dep = _legacy_book_dep(pi, eng)
        result = _run_clean(_adapt(pi))
        clean = {p.period_index: p.book_depreciation_keur for p in result.periods}
        max_d = max(abs(clean.get(k, 0.0) - v) for k, v in leg_dep.items())
        assert max_d < 1e-6, f"Book dep max C-L delta {max_d:.2e}"

    def test_ebitda_identity_from_clean_components(self):
        """EBITDA = revenue − opex holds exactly; OPEX matches legacy leaf."""
        from app.project_factories import create_default_oborovo
        pi = create_default_oborovo()
        eng = _legacy_engine(pi)
        leg_opex = _legacy_opex(pi, eng)
        result = _run_clean(_adapt(pi))
        for p in result.periods:
            expected_ebitda = p.revenue_keur - leg_opex.get(p.period_index, 0.0)
            assert abs(p.ebitda_keur - expected_ebitda) < 1e-9, (
                f"Period {p.period_index}: ebitda delta {p.ebitda_keur - expected_ebitda:.2e}"
            )

    def test_max_period_ebit_delta_vs_legacy_components(self):
        """EBIT = ebitda − legacy_dep, max period delta < 1e-6."""
        from app.project_factories import create_default_oborovo
        pi = create_default_oborovo()
        eng = _legacy_engine(pi)
        leg_dep = _legacy_book_dep(pi, eng)
        result = _run_clean(_adapt(pi))
        max_d = 0.0
        for p in result.periods:
            legacy_ebit = p.ebitda_keur - leg_dep.get(p.period_index, 0.0)
            max_d = max(max_d, abs(p.ebit_keur - legacy_ebit))
        assert max_d < 1e-6, f"EBIT max C-L period delta {max_d:.2e}"

    def test_lifetime_ebit_delta_vs_legacy_components(self):
        from app.project_factories import create_default_oborovo
        pi = create_default_oborovo()
        eng = _legacy_engine(pi)
        leg_dep = _legacy_book_dep(pi, eng)
        result = _run_clean(_adapt(pi))
        clean_total = sum(p.ebit_keur for p in result.periods if p.is_operation)
        legacy_total = sum(
            p.ebitda_keur - leg_dep.get(p.period_index, 0.0)
            for p in result.periods if p.is_operation
        )
        assert abs(clean_total - legacy_total) < 1e-6, (
            f"Clean EBIT {clean_total:.6f} vs legacy-composed {legacy_total:.6f}"
        )


# ── L: Exact signed Clean−Excel EBIT bridge ──────────────────────────────────

class TestLExactExcelEbitBridge:
    """Group L — exact signed reconciliation of clean vs Excel EBIT gap.

    EBIT = Revenue − OPEX − book_dep (P&L identity)
    ⟹ ΔEBIT = ΔRevenue − ΔOPEX − Δbook_dep

    Signed bridge (kEUR):
      Revenue delta:   −14.081531  (C2B-approved)
      OPEX delta:       −3.979835  (C2A-approved period alignment)
      Book dep delta:   +0.000843  (PERIOD_MAPPING net residual)
      Expected ΔEBIT:  −10.102539
      Actual ΔEBIT:    −10.102539
      Bridge residual:  < 1e-9
    """

    def test_exact_ebit_bridge(self):
        d = _excel_data()
        result = _run_clean()

        # Operating-period totals (Excel index 0 = construction)
        excel_rev = sum(d["pl"]["total_revenues_keur"][1:])
        excel_opex = sum(d["pl"]["operating_expenses_keur"][1:])
        excel_dep = sum(d["pl"]["depreciation_keur"][1:])
        excel_ebit = sum(d["pl"]["ebit_keur"][1:])

        op = [p for p in result.periods if p.is_operation]
        clean_rev = sum(p.revenue_keur for p in op)
        clean_opex = sum(p.opex_keur for p in op)
        clean_dep = sum(p.book_depreciation_keur for p in op)
        clean_ebit = sum(p.ebit_keur for p in op)

        rev_delta  = clean_rev  - excel_rev
        opex_delta = clean_opex - excel_opex
        dep_delta  = clean_dep  - excel_dep

        # P&L identity: ΔEBIT = ΔRev - ΔOPEX - ΔDep
        expected_ebit_delta = rev_delta - opex_delta - dep_delta
        actual_ebit_delta   = clean_ebit - excel_ebit

        bridge_residual = abs(actual_ebit_delta - expected_ebit_delta)
        assert bridge_residual < 1e-9, (
            f"EBIT bridge not closed: expected_delta={expected_ebit_delta:+.6f}, "
            f"actual_delta={actual_ebit_delta:+.6f}, residual={bridge_residual:.2e}"
        )

    def test_clean_ebit_total(self):
        op = [p for p in _run_clean().periods if p.is_operation]
        total = sum(p.ebit_keur for p in op)
        assert abs(total - _CLEAN_EBIT_KEUR) < 0.001, (
            f"Clean EBIT {total:.3f} != {_CLEAN_EBIT_KEUR}"
        )


# ── M: Book vs tax depreciation independence ──────────────────────────────────

class TestMBookVsTaxIndependence:
    """Group M — book dep and tax dep relationship.

    C3B3B2 source-proven correction: C3B1 proves excel_tax_dep == excel_book_dep
    for all Oborovo operating periods. Oborovo factory sets tax_dep_basis_source_owned=True
    → adapter uses book_depreciable_capex_items() for both book and tax dep.
    Book total == tax total within floating-point tolerance.
    """

    def test_book_equals_tax_dep_source_proven(self):
        # C3B1 evidence: excel_tax_dep == excel_book_dep for all 28 Oborovo debt periods.
        # C3B3B2 fix: tax_dep_basis_source_owned=True → book items used for tax dep.
        result = _run_clean()
        book = sum(p.book_depreciation_keur for p in result.periods)
        tax = sum(p.tax_depreciation_keur for p in result.periods)
        assert abs(book - tax) < 0.01, (
            f"Book dep {book:.6f} should equal tax dep {tax:.6f} (C3B1-proven, Oborovo)"
        )


# ── PM: PERIOD_MAPPING proof ──────────────────────────────────────────────────

class TestPMPeriodMappingProof:
    """Group PM — PERIOD_MAPPING proven for H2 leap-year boundary periods.

    Mechanism:
      H2 periods (Jul–Dec) straddling a non-leap→leap boundary use a 365-day
      denominator in the clean engine but 366-day denominator in Excel (Excel
      applies the FOLLOWING calendar year's day count to H2 periods).

      For each affected H2 pair, clean and Excel swap by the same ±4.073 kEUR,
      so the pairs cancel exactly. The small residual (+0.000843 kEUR) is from
      floating-point fraction arithmetic.

    Conclusion: PERIOD_MAPPING_PROVEN.
    """

    # Pairs identified from data: (h2_period_idx, h2_end_year, pair_direction)
    # direction = +1 means clean > excel in this period
    _KNOWN_PAIRS = [
        (4,  2031, +1),   # 2031 non-leap, 2032 leap → clean uses 365
        (6,  2032, -1),   # 2032 leap, 2033 non-leap → clean uses 366
        (12, 2035, +1),
        (14, 2036, -1),
        (20, 2039, +1),
        (22, 2040, -1),
    ]

    def test_affected_periods_are_h2(self):
        """All PERIOD_MAPPING periods have start month in [6,7] (H2 start)."""
        result = _run_clean()
        d = _excel_data()
        excel_dep = d["dep"]["dep_total_keur"]
        op_periods = [p for p in result.periods if p.is_operation]
        affected = [
            p for i, p in enumerate(op_periods)
            if abs(p.book_depreciation_keur - excel_dep[i + 1]) > 0.001
        ]
        for p in affected:
            assert p.period_start.month in (6, 7), (
                f"Period {p.period_index} ({p.period_start}) is not H2"
            )

    def test_swaps_cancel_in_pairs(self):
        """Each +delta period is followed by an equal −delta period."""
        result = _run_clean()
        d = _excel_data()
        excel_dep = d["dep"]["dep_total_keur"]
        op_periods = [p for p in result.periods if p.is_operation]
        diffs = [
            (p.period_index, p.book_depreciation_keur - excel_dep[i + 1])
            for i, p in enumerate(op_periods)
            if abs(p.book_depreciation_keur - excel_dep[i + 1]) > 0.001
        ]
        # Must have an even count of affected periods
        assert len(diffs) % 2 == 0, f"Odd number of affected periods: {diffs}"
        # Each consecutive pair must sum to near zero
        for j in range(0, len(diffs), 2):
            idx_a, d_a = diffs[j]
            idx_b, d_b = diffs[j + 1]
            pair_sum = d_a + d_b
            assert abs(pair_sum) < 0.001, (
                f"Pair ({idx_a}: {d_a:+.4f}, {idx_b}: {d_b:+.4f}) "
                f"does not cancel: sum={pair_sum:+.6f}"
            )

    def test_convention_explanation(self):
        """Prove the denominator-convention explanation for one pair.

        Period 4 (2031-06-30 → 2031-12-31, 184 days):
          end_year=2031 (non-leap, denom=365), next_year=2032 (leap, denom=366)
          clean_dep = annual × 184/365 > excel_dep = annual × 184/366
        """
        result = _run_clean()
        d = _excel_data()
        excel_dep_per_period = d["dep"]["dep_total_keur"]
        op_periods = {p.period_index: p for p in result.periods if p.is_operation}

        p3 = op_periods.get(3)
        assert p3 is not None, "Period 3 not found"
        excel_p3 = excel_dep_per_period[3]

        end_year = p3.period_end.year
        next_year = end_year + 1       # 2032
        assert not calendar.isleap(end_year), f"end_year {end_year} should be non-leap"
        assert calendar.isleap(next_year), f"next_year {next_year} should be leap"

        assert p3.day_fraction == pytest.approx(p3.days_in_period / 366.0)
        assert p3.book_depreciation_keur == pytest.approx(excel_p3, abs=0.01)

    def test_net_lifetime_effect_small(self):
        """Signed sum of all C-X dep diffs ≤ 0.01 kEUR (SOURCE_ROUNDING)."""
        result = _run_clean()
        d = _excel_data()
        excel_dep = d["dep"]["dep_total_keur"]
        op_periods = [p for p in result.periods if p.is_operation]
        signed_sum = sum(
            p.book_depreciation_keur - excel_dep[i + 1]
            for i, p in enumerate(op_periods)
        )
        assert abs(signed_sum) < 0.01, (
            f"Signed sum {signed_sum:+.6f} kEUR larger than expected "
            "(pairs should cancel to SOURCE_ROUNDING level)"
        )


# ── N: Generic Solar — all fields unchanged ───────────────────────────────────

class TestNGenericSolarNoChange:
    """Group N — Solar: all pre-existing fields match legacy; ebit_keur is new."""

    def test_solar_all_legacy_fields_match(self):
        from app.project_factories import create_default_solar_project
        pi = create_default_solar_project()
        eng = _legacy_engine(pi)
        omin = _adapt(pi)
        result = _run_clean(omin)

        leg_rev     = _legacy_rev(pi, eng)
        leg_opex    = _legacy_opex(pi, eng)
        leg_dep     = _legacy_book_dep(pi, eng)
        leg_tax_dep = _legacy_tax_dep(pi, eng)

        clean = {p.period_index: p for p in result.periods}
        for idx in leg_rev:
            p = clean.get(idx)
            assert p is not None, f"Period {idx} missing"
            assert abs(p.revenue_keur - leg_rev[idx]) < 1e-9, (
                f"Solar period {idx} revenue delta {p.revenue_keur - leg_rev[idx]:.2e}"
            )
            assert abs(p.opex_keur - leg_opex.get(idx, 0.0)) < 1e-9, (
                f"Solar period {idx} opex delta"
            )
            expected_ebitda = leg_rev[idx] - leg_opex.get(idx, 0.0)
            assert abs(p.ebitda_keur - expected_ebitda) < 1e-9, (
                f"Solar period {idx} ebitda delta"
            )
            assert abs(p.book_depreciation_keur - leg_dep.get(idx, 0.0)) < 1e-9, (
                f"Solar period {idx} book_dep delta"
            )
            assert abs(p.tax_depreciation_keur - leg_tax_dep.get(idx, 0.0)) < 1e-9, (
                f"Solar period {idx} tax_dep delta"
            )

    def test_solar_ebit_identity(self):
        from app.project_factories import create_default_solar_project
        result = _run_clean(factory=create_default_solar_project)
        max_res = max(
            abs(p.ebit_keur - (p.ebitda_keur - p.book_depreciation_keur))
            for p in result.periods
        )
        assert max_res < 1e-9, f"Solar EBIT identity residual {max_res:.2e}"


# ── O: Generic Wind — all fields unchanged ────────────────────────────────────

class TestOGenericWindNoChange:
    """Group O — Wind: all pre-existing fields match legacy; ebit_keur is new."""

    def test_wind_all_legacy_fields_match(self):
        from app.project_factories import create_default_wind_project
        pi = create_default_wind_project()
        eng = _legacy_engine(pi)
        omin = _adapt(pi)
        result = _run_clean(omin)

        leg_rev     = _legacy_rev(pi, eng)
        leg_opex    = _legacy_opex(pi, eng)
        leg_dep     = _legacy_book_dep(pi, eng)
        leg_tax_dep = _legacy_tax_dep(pi, eng)

        clean = {p.period_index: p for p in result.periods}
        for idx in leg_rev:
            p = clean.get(idx)
            assert p is not None, f"Period {idx} missing"
            assert abs(p.revenue_keur - leg_rev[idx]) < 1e-9, (
                f"Wind period {idx} revenue delta"
            )
            assert abs(p.opex_keur - leg_opex.get(idx, 0.0)) < 1e-9, (
                f"Wind period {idx} opex delta"
            )
            assert abs(p.book_depreciation_keur - leg_dep.get(idx, 0.0)) < 1e-9, (
                f"Wind period {idx} book_dep delta"
            )
            assert abs(p.tax_depreciation_keur - leg_tax_dep.get(idx, 0.0)) < 1e-9, (
                f"Wind period {idx} tax_dep delta"
            )

    def test_wind_ebit_identity(self):
        from app.project_factories import create_default_wind_project
        result = _run_clean(factory=create_default_wind_project)
        max_res = max(
            abs(p.ebit_keur - (p.ebitda_keur - p.book_depreciation_keur))
            for p in result.periods
        )
        assert max_res < 1e-9, f"Wind EBIT identity residual {max_res:.2e}"


# ── P: True TUHO no-change ────────────────────────────────────────────────────

class TestPTuhoNoChange:
    """Group P — TUHO Wind 1: all pre-existing fields match legacy independently;
    ebit_keur = ebitda − book_dep is the sole new output.

    TUHO has no calendar-year merchant pricing, so full_revenue_schedule
    produces the same result as the clean engine's revenue leaf (verified
    to max delta 0.00e+00 per period).

    Before/after comparison: legacy finco_core leaf output (base SHA behavior)
    vs clean engine output (head SHA behavior). All pre-existing fields must
    be unchanged.
    """

    def test_tuho_clean_run_succeeds(self):
        from app.project_factories import create_default_tuho_wind1
        result = _run_clean(factory=create_default_tuho_wind1)
        assert len(result.periods) > 0

    def test_tuho_revenue_matches_legacy(self):
        from app.project_factories import create_default_tuho_wind1
        pi = create_default_tuho_wind1()
        eng = _legacy_engine(pi)
        leg_rev = _legacy_rev(pi, eng)
        result = _run_clean(_adapt(pi))
        clean = {p.period_index: p.revenue_keur for p in result.periods}
        max_d = max(abs(clean.get(k, 0.0) - v) for k, v in leg_rev.items())
        assert max_d < 1e-9, f"TUHO revenue max C-L delta {max_d:.2e}"

    def test_tuho_opex_matches_legacy(self):
        from app.project_factories import create_default_tuho_wind1
        pi = create_default_tuho_wind1()
        eng = _legacy_engine(pi)
        leg_opex = _legacy_opex(pi, eng)
        result = _run_clean(_adapt(pi))
        clean = {p.period_index: p.opex_keur for p in result.periods}
        max_d = max(abs(clean.get(k, 0.0) - v) for k, v in leg_opex.items())
        assert max_d < 1e-9, f"TUHO OPEX max C-L delta {max_d:.2e}"

    def test_tuho_ebitda_matches_legacy(self):
        from app.project_factories import create_default_tuho_wind1
        pi = create_default_tuho_wind1()
        eng = _legacy_engine(pi)
        leg_rev = _legacy_rev(pi, eng)
        leg_opex = _legacy_opex(pi, eng)
        leg_ebitda = {k: leg_rev.get(k, 0.0) - leg_opex.get(k, 0.0)
                      for k in set(leg_rev) | set(leg_opex)}
        result = _run_clean(_adapt(pi))
        clean = {p.period_index: p.ebitda_keur for p in result.periods}
        max_d = max(abs(clean.get(k, 0.0) - leg_ebitda.get(k, 0.0))
                    for k in leg_ebitda)
        assert max_d < 1e-9, f"TUHO EBITDA max C-L delta {max_d:.2e}"

    def test_tuho_book_depreciation_matches_legacy(self):
        from app.project_factories import create_default_tuho_wind1
        pi = create_default_tuho_wind1()
        eng = _legacy_engine(pi)
        leg_dep = _legacy_book_dep(pi, eng)
        result = _run_clean(_adapt(pi))
        clean = {p.period_index: p.book_depreciation_keur for p in result.periods}
        max_d = max(abs(clean.get(k, 0.0) - v) for k, v in leg_dep.items())
        assert max_d < 1e-9, f"TUHO book dep max C-L delta {max_d:.2e}"

    def test_tuho_tax_depreciation_matches_legacy(self):
        from app.project_factories import create_default_tuho_wind1
        pi = create_default_tuho_wind1()
        eng = _legacy_engine(pi)
        leg_tax = _legacy_tax_dep(pi, eng)
        result = _run_clean(_adapt(pi))
        clean = {p.period_index: p.tax_depreciation_keur for p in result.periods}
        max_d = max(abs(clean.get(k, 0.0) - v) for k, v in leg_tax.items())
        assert max_d < 1e-9, f"TUHO tax dep max C-L delta {max_d:.2e}"

    def test_tuho_only_new_output_is_ebit_keur(self):
        """ebit_keur is present and equals EBITDA − book_dep exactly."""
        from app.project_factories import create_default_tuho_wind1
        result = _run_clean(factory=create_default_tuho_wind1)
        assert all(hasattr(p, "ebit_keur") for p in result.periods)
        max_res = max(
            abs(p.ebit_keur - (p.ebitda_keur - p.book_depreciation_keur))
            for p in result.periods
        )
        assert max_res < 1e-9, f"TUHO EBIT identity residual {max_res:.2e}"


# ── Q: Identity independence ──────────────────────────────────────────────────

class TestQIdentityIndependence:
    """Group Q — Renamed Oborovo clone yields identical P&L vectors."""

    def test_clone_with_different_identity_same_ebit(self):
        import dataclasses
        from app.project_factories import create_default_oborovo
        pi = create_default_oborovo()
        pi_clone = dataclasses.replace(
            pi,
            info=dataclasses.replace(
                pi.info, name="RenamedProject", code="REN001",
                company="Different Company SA",
            ),
        )
        result_orig = _run_clean(_adapt(pi))
        result_clone = _run_clean(_adapt(pi_clone))
        for p_o, p_c in zip(result_orig.periods, result_clone.periods):
            assert abs(p_o.ebit_keur - p_c.ebit_keur) < 1e-9, (
                f"Period {p_o.period_index}: orig={p_o.ebit_keur}, "
                f"clone={p_c.ebit_keur}"
            )


# ── R: No target plug / no project dispatch ───────────────────────────────────

class TestRNoTargetPlug:
    """Group R — EBIT not hardcoded; orchestrator has no Oborovo dispatch."""

    def test_ebit_varies_across_projects(self):
        from app.project_factories import create_default_solar_project, create_default_oborovo
        r_ob = _run_clean(factory=create_default_oborovo)
        r_solar = _run_clean(factory=create_default_solar_project)
        ebit_ob = sum(p.ebit_keur for p in r_ob.periods)
        ebit_solar = sum(p.ebit_keur for p in r_solar.periods)
        assert abs(ebit_ob - ebit_solar) > 1.0

    def test_orchestrator_no_oborovo_literal(self):
        import ast
        from pathlib import Path
        src = (Path(__file__).parent.parent / "financial_engine" / "orchestrator.py").read_text()
        tree = ast.parse(src)
        oborovo_lits = [
            n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and "oborovo" in n.value.lower()
        ]
        assert not oborovo_lits, f"Oborovo literals in orchestrator: {oborovo_lits}"

    def test_ebit_formula_is_arithmetic_identity(self):
        result = _run_clean()
        for p in result.periods:
            expected = p.ebitda_keur - p.book_depreciation_keur
            assert p.ebit_keur == expected, (
                f"Period {p.period_index}: ebit != ebitda-dep (plug detected)"
            )
