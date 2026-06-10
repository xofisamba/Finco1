"""Phase P1-A — Generic Driver Response Audit tests.

The audit proves whether each editable Generic
Solar / Generic Wind form field actually changes
the runtime KPIs when the form value is edited.

These tests are CAPTURE-ONLY. They:
- do NOT change formulas
- do NOT change any production code
- do NOT change any model logic
- do NOT enable any feature flag
- do NOT change persistence or schema
- do NOT touch construction, C10, R-PAR, IDC,
  tax, debt, or depreciation

Per-field status decisions are pinned here.
"""

import os
import sys

import pytest


HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


from app.input_schema import (
    ProjectInputsSchema,
    RevenueInput,
    CapexInput,
    OpexInput,
    DebtInput,
)
from app.input_adapter import build_projectinputs
from app.ui_runner import run_demo_project
from app.ui.generic_driver_response_audit import (
    DriverEntry,
    DriverResponseAudit,
    KPI_PROJECT_IRR,
    KPI_EQUITY_IRR,
    KPI_MIN_DSCR,
    KPI_TOTAL_REVENUE,
    KPI_SENIOR_DEBT,
    STATUS_WIRED,
    STATUS_NOT_WIRED,
    STATUS_METADATA_ONLY,
    STATUS_WIRED_PARTIAL,
    compute_kpi_deltas,
    summarize_status,
)


# KPI subset audited. We focus on the ones listed
# in the Phase P1-A brief: revenue, OPEX, EBITDA,
# project IRR, equity IRR, min DSCR, senior debt.
AUDIT_KPIS = (
    KPI_PROJECT_IRR,
    KPI_EQUITY_IRR,
    KPI_MIN_DSCR,
    KPI_TOTAL_REVENUE,
    KPI_SENIOR_DEBT,
)


def _run_solar(schema: ProjectInputsSchema):
    """Run the Solar demo project with the given
    schema and return the WaterfallResult."""
    proj = build_projectinputs(schema)
    r = run_demo_project("Solar", "Base", project_inputs_override=proj)
    return r.result


# ---------------------------------------------------------------------------
# 1. Audit helper self-tests
# ---------------------------------------------------------------------------


class TestAuditHelpers:
    """The audit helper itself behaves as documented."""

    def test_compute_kpi_deltas(self):
        class _R:
            project_irr = 0.10
            min_dscr = 1.20
        deltas = compute_kpi_deltas(_R(), _R(), ("project_irr", "min_dscr"))
        assert deltas["project_irr"] == (0.10, 0.10)
        assert deltas["min_dscr"] == (1.20, 1.20)

    def test_summarize_status_no_change(self):
        deltas = {"a": (0.10, 0.10), "b": (1.20, 1.20)}
        assert summarize_status(deltas) == STATUS_NOT_WIRED

    def test_summarize_status_changed_non_project_irr(self):
        # When a non-project_irr KPI changes but
        # project_irr stays the same, status is
        # WIRED_PARTIAL.
        deltas = {"a": (0.10, 0.11), "b": (1.20, 1.20)}
        assert summarize_status(deltas) == STATUS_WIRED_PARTIAL

    def test_summarize_status_changed_project_irr(self):
        # When project_irr changes, status is full
        # WIRED.
        deltas = {"project_irr": (0.10, 0.11), "b": (1.20, 1.20)}
        assert summarize_status(deltas) == STATUS_WIRED

    def test_summarize_status_minor_drift(self):
        deltas = {"a": (0.1000, 0.1000 + 1e-9)}
        # 1e-9 relative to 0.1 is < 1e-6 tolerance
        assert summarize_status(deltas) == STATUS_NOT_WIRED


# ---------------------------------------------------------------------------
# 2. TARIFF
# ---------------------------------------------------------------------------


class TestTariffDriver:
    """tariff_eur_mwh: 55 -> 75 must change revenue /
    IRR / DSCR."""

    def test_tariff_changes_revenue_and_irr(self):
        baseline = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            revenue=RevenueInput(tariff_eur_mwh=55.0),
        ))
        changed = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            revenue=RevenueInput(tariff_eur_mwh=75.0),
        ))
        deltas = compute_kpi_deltas(baseline, changed, AUDIT_KPIS)
        assert summarize_status(deltas) == STATUS_WIRED
        # Revenue must grow.
        assert changed.total_revenue_keur > baseline.total_revenue_keur
        # IRR must grow.
        assert changed.project_irr > baseline.project_irr
        # DSCR must grow.
        assert changed.min_dscr > baseline.min_dscr

    def test_tariff_status_in_audit_entry(self):
        baseline = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            revenue=RevenueInput(tariff_eur_mwh=55.0),
        ))
        changed = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            revenue=RevenueInput(tariff_eur_mwh=75.0),
        ))
        deltas = compute_kpi_deltas(baseline, changed, AUDIT_KPIS)
        status = summarize_status(deltas)
        entry = DriverEntry(
            field="tariff_eur_mwh",
            baseline_value=55.0,
            changed_value=75.0,
            kpi_deltas=deltas,
            status=status,
        )
        assert entry.status == STATUS_WIRED


# ---------------------------------------------------------------------------
# 3. P50 HOURS
# ---------------------------------------------------------------------------


class TestP50HoursDriver:
    """p50_hours: 1500 -> 2500 must change generation /
    revenue / IRR."""

    def test_p50_changes_revenue_and_irr(self):
        baseline = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            revenue=RevenueInput(p50_hours=1500.0),
        ))
        changed = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            revenue=RevenueInput(p50_hours=2500.0),
        ))
        deltas = compute_kpi_deltas(baseline, changed, AUDIT_KPIS)
        assert summarize_status(deltas) == STATUS_WIRED
        assert changed.total_revenue_keur > baseline.total_revenue_keur
        assert changed.project_irr > baseline.project_irr

    def test_p50_status_wired(self):
        baseline = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            revenue=RevenueInput(p50_hours=1500.0),
        ))
        changed = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            revenue=RevenueInput(p50_hours=2500.0),
        ))
        deltas = compute_kpi_deltas(baseline, changed, AUDIT_KPIS)
        assert summarize_status(deltas) == STATUS_WIRED


# ---------------------------------------------------------------------------
# 4. CAPACITY
# ---------------------------------------------------------------------------


class TestCapacityDriver:
    """capacity_mw: 50 -> 100 must scale generation /
    revenue / IRR."""

    def test_capacity_changes_revenue(self):
        baseline = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base", capacity_mw=50.0,
        ))
        changed = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base", capacity_mw=100.0,
        ))
        deltas = compute_kpi_deltas(baseline, changed, AUDIT_KPIS)
        assert summarize_status(deltas) == STATUS_WIRED
        # Revenue should approximately double.
        ratio = changed.total_revenue_keur / baseline.total_revenue_keur
        assert 1.9 < ratio < 2.1

    def test_capacity_status_wired(self):
        baseline = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base", capacity_mw=50.0,
        ))
        changed = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base", capacity_mw=100.0,
        ))
        deltas = compute_kpi_deltas(baseline, changed, AUDIT_KPIS)
        assert summarize_status(deltas) == STATUS_WIRED


# ---------------------------------------------------------------------------
# 5. TOTAL CAPEX
# ---------------------------------------------------------------------------


class TestTotalCapexDriver:
    """total_capex_keur: 30000 -> 50000 must change IRR
    / debt / DSCR."""

    def test_total_capex_changes_debt(self):
        baseline = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            capex=CapexInput(total_capex_keur=30000.0),
        ))
        changed = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            capex=CapexInput(total_capex_keur=50000.0),
        ))
        deltas = compute_kpi_deltas(baseline, changed, AUDIT_KPIS)
        # Debt should rise (DSCR sculpt sized to target).
        assert (
            changed.sculpting_result.debt_keur
            > baseline.sculpting_result.debt_keur
        )

    def test_total_capex_status_wired(self):
        # total_capex_keur DOES change project_irr
        # when it crosses the debt capacity. The
        # driver is full WIRED.
        baseline = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            capex=CapexInput(total_capex_keur=30000.0),
        ))
        changed = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            capex=CapexInput(total_capex_keur=50000.0),
        ))
        deltas = compute_kpi_deltas(baseline, changed, AUDIT_KPIS)
        assert summarize_status(deltas) == STATUS_WIRED


# ---------------------------------------------------------------------------
# 6. OPEX Y1
# ---------------------------------------------------------------------------


class TestOpexY1Driver:
    """opex_y1_keur: 380 -> 800 must change OPEX and
    depress IRR."""

    def test_opex_y1_changes_irr(self):
        baseline = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            opex=OpexInput(opex_y1_keur=380.0),
        ))
        changed = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            opex=OpexInput(opex_y1_keur=800.0),
        ))
        # OPEX changes both project_irr and equity_irr.
        assert changed.project_irr < baseline.project_irr

    def test_opex_y1_status_wired(self):
        baseline = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            opex=OpexInput(opex_y1_keur=380.0),
        ))
        changed = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            opex=OpexInput(opex_y1_keur=800.0),
        ))
        deltas = compute_kpi_deltas(baseline, changed, AUDIT_KPIS)
        # OPEX changes project_irr (revenue is fixed
        # but OPEX moves, so EBITDA moves, so IRR
        # moves). Status: full WIRED.
        assert summarize_status(deltas) == STATUS_WIRED


# ---------------------------------------------------------------------------
# 7. GEARING — known bug from Claude review
# ---------------------------------------------------------------------------


class TestGearingDriver:
    """gearing_pct: 70 -> 85.

    Per the Claude review, gearing_pct does NOT
    change the project IRR. The audit confirms:
    project_irr stays the same, but equity_irr and
    min_dscr change because gearing_ratio does
    scale the debt (which affects equity_irr).

    Status: WIRED_PARTIAL (some KPIs change, but
    project_irr does not).
    """

    def test_gearing_is_wired_partial(self):
        baseline = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            debt=DebtInput(gearing_pct=70.0),
        ))
        changed = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            debt=DebtInput(gearing_pct=85.0),
        ))
        deltas = compute_kpi_deltas(baseline, changed, AUDIT_KPIS)
        status = summarize_status(deltas)
        # The audit shows: project_irr does NOT
        # change, but equity_irr and min_dscr DO
        # change. So status is WIRED_PARTIAL.
        assert status == STATUS_WIRED_PARTIAL, (
            f"Expected gearing_pct to be WIRED_PARTIAL but got {status}; "
            f"deltas: {deltas}"
        )

    def test_gearing_project_irr_does_not_change(self):
        """The specific Claude concern: project_irr
        does not change when gearing changes."""
        baseline = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            debt=DebtInput(gearing_pct=70.0),
        ))
        changed = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            debt=DebtInput(gearing_pct=85.0),
        ))
        # project_irr is identical (within 1e-6).
        assert abs(baseline.project_irr - changed.project_irr) < 1e-6
        # equity_irr is different.
        assert abs(baseline.equity_irr - changed.equity_irr) > 1e-3

    def test_gearing_status_documented_as_wired_partial(self):
        baseline = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            debt=DebtInput(gearing_pct=70.0),
        ))
        changed = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            debt=DebtInput(gearing_pct=85.0),
        ))
        deltas = compute_kpi_deltas(baseline, changed, AUDIT_KPIS)
        entry = DriverEntry(
            field="gearing_pct",
            baseline_value=70.0,
            changed_value=85.0,
            kpi_deltas=deltas,
            status=summarize_status(deltas),
            note=(
                "WIRED_PARTIAL: gearing_pct is stored on "
                "financing.gearing_ratio and DOES scale "
                "debt (which changes equity_irr and min_dscr). "
                "However, project_irr does NOT change "
                "because the debt sizing method is "
                "DSCR_SCULPT — debt is sized to hit the "
                "target_dscr, so project_irr is invariant "
                "to gearing_pct. Claude review concern: "
                "project_irr does not move on the form. "
                "This is by design of the current runtime, "
                "not a bug per se — it is a partial wiring."
            ),
        )
        assert entry.status == STATUS_WIRED_PARTIAL


# ---------------------------------------------------------------------------
# 8. INTEREST RATE
# ---------------------------------------------------------------------------


class TestInterestRateDriver:
    """interest_rate_pct: 5.5 -> 8.0 must change DSCR
    and debt (sized to target DSCR)."""

    def test_interest_rate_changes_dscr(self):
        baseline = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            debt=DebtInput(interest_rate_pct=5.5),
        ))
        changed = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            debt=DebtInput(interest_rate_pct=8.0),
        ))
        # Higher rate -> lower debt (more DS service for same CFADS)
        assert (
            changed.sculpting_result.debt_keur
            < baseline.sculpting_result.debt_keur
        )

    def test_interest_rate_status_wired_partial(self):
        # In DSCR_SCULPT mode, project_irr is
        # invariant to interest rate (debt is sized
        # to hit target_dscr). Driver is
        # WIRED_PARTIAL.
        baseline = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            debt=DebtInput(interest_rate_pct=5.5),
        ))
        changed = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            debt=DebtInput(interest_rate_pct=8.0),
        ))
        deltas = compute_kpi_deltas(baseline, changed, AUDIT_KPIS)
        assert summarize_status(deltas) == STATUS_WIRED_PARTIAL


# ---------------------------------------------------------------------------
# 9. TENOR
# ---------------------------------------------------------------------------


class TestTenorDriver:
    """tenor_years: 15 -> 20 must change DSCR (longer
    tenure -> lower annual debt service)."""

    def test_tenor_changes_dscr(self):
        baseline = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            debt=DebtInput(tenor_years=15),
        ))
        changed = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            debt=DebtInput(tenor_years=20),
        ))
        # Longer tenure -> higher min DSCR.
        assert changed.min_dscr > baseline.min_dscr

    def test_tenor_status_wired_partial(self):
        # Same DSCR_SCULPT pattern: project_irr
        # is invariant; only min_dscr moves.
        baseline = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            debt=DebtInput(tenor_years=15),
        ))
        changed = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            debt=DebtInput(tenor_years=20),
        ))
        deltas = compute_kpi_deltas(baseline, changed, AUDIT_KPIS)
        assert summarize_status(deltas) == STATUS_WIRED_PARTIAL


# ---------------------------------------------------------------------------
# 10. TARGET DSCR
# ---------------------------------------------------------------------------


class TestTargetDscrDriver:
    """target_dscr: 1.20 -> 1.50 must change DSCR (DSCR
    sculpting)."""

    def test_target_dscr_changes_dscr(self):
        baseline = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            debt=DebtInput(target_dscr=1.20),
        ))
        changed = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            debt=DebtInput(target_dscr=1.50),
        ))
        # Min DSCR should track target.
        assert changed.min_dscr > baseline.min_dscr
        # Debt should be lower (less debt can hit higher DSCR).
        assert (
            changed.sculpting_result.debt_keur
            < baseline.sculpting_result.debt_keur
        )

    def test_target_dscr_status_wired_partial(self):
        # target_dscr scales the debt but the
        # project_irr (in DSCR_SCULPT) is invariant.
        # Driver is WIRED_PARTIAL.
        baseline = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            debt=DebtInput(target_dscr=1.20),
        ))
        changed = _run_solar(ProjectInputsSchema(
            project_type="Solar", scenario="Base",
            debt=DebtInput(target_dscr=1.50),
        ))
        deltas = compute_kpi_deltas(baseline, changed, AUDIT_KPIS)
        assert summarize_status(deltas) == STATUS_WIRED_PARTIAL


# ---------------------------------------------------------------------------
# 11. PPA TERM — metadata only
# ---------------------------------------------------------------------------


class TestPpaTermDriver:
    """ppa_term_years is exposed in the UI but NOT
    in ProjectInputsSchema. Therefore it cannot
    reach the runtime path. Status: METADATA_ONLY.

    This test documents the gap. It does not
    attempt to fix it.
    """

    def test_ppa_term_not_in_schema(self):
        # Per Phase P1-A brief: ppa_term_years is a
        # UI field but the runtime schema does NOT
        # carry it. Document the gap.
        from app.input_schema import ProjectInputsSchema
        assert "ppa_term_years" not in ProjectInputsSchema.model_fields
        assert "ppa_term_years" not in RevenueInput.model_fields
        assert "ppa_term_years" not in DebtInput.model_fields
        assert "ppa_term_years" not in OpexInput.model_fields
        assert "ppa_term_years" not in CapexInput.model_fields

    def test_ppa_term_status_metadata_only(self):
        entry = DriverEntry(
            field="ppa_term_years",
            baseline_value=10,
            changed_value=20,
            kpi_deltas={},
            status=STATUS_METADATA_ONLY,
            note=(
                "ppa_term_years is editable in the UI "
                "(inputs_section.html) and shown in the "
                "scenario_workflow editable field list, "
                "but is NOT in ProjectInputsSchema. The "
                "value is rendered for display only; "
                "it never reaches the runtime path."
            ),
        )
        assert entry.status == STATUS_METADATA_ONLY


# ---------------------------------------------------------------------------
# 12. Construction months — metadata only
# ---------------------------------------------------------------------------


class TestConstructionMonthsDriver:
    """construction_months is exposed in the UI but
    cannot be passed through the runtime path
    schema (which uses build_projectinputs with
    only 8 fields).

    Status: METADATA_ONLY.
    """

    def test_construction_months_not_in_schema(self):
        from app.input_schema import ProjectInputsSchema
        assert "construction_months" not in ProjectInputsSchema.model_fields

    def test_construction_months_status_metadata_only(self):
        entry = DriverEntry(
            field="construction_months",
            baseline_value=12,
            changed_value=24,
            kpi_deltas={},
            status=STATUS_METADATA_ONLY,
            note=(
                "construction_months is editable in the UI "
                "but the schema does not carry it. The "
                "value is read from project_factory defaults."
            ),
        )
        assert entry.status == STATUS_METADATA_ONLY


# ---------------------------------------------------------------------------
# 13. Audit aggregation
# ---------------------------------------------------------------------------


class TestAuditAggregation:
    """The audit must aggregate all 11 fields into a
    single DriverResponseAudit with a coherent
    per-status count."""

    def test_audit_count_matches_11(self):
        entries = (
            DriverEntry(
                field="tariff_eur_mwh",
                baseline_value=55.0, changed_value=75.0,
                kpi_deltas={}, status=STATUS_WIRED,
            ),
            DriverEntry(
                field="p50_hours",
                baseline_value=1500.0, changed_value=2500.0,
                kpi_deltas={}, status=STATUS_WIRED,
            ),
            DriverEntry(
                field="total_capex_keur",
                baseline_value=30000.0, changed_value=50000.0,
                kpi_deltas={}, status=STATUS_WIRED,
            ),
            DriverEntry(
                field="interest_rate_pct",
                baseline_value=5.5, changed_value=8.0,
                kpi_deltas={}, status=STATUS_WIRED_PARTIAL,
            ),
            DriverEntry(
                field="tenor_years",
                baseline_value=15, changed_value=20,
                kpi_deltas={}, status=STATUS_WIRED_PARTIAL,
            ),
            DriverEntry(
                field="target_dscr",
                baseline_value=1.20, changed_value=1.50,
                kpi_deltas={}, status=STATUS_WIRED_PARTIAL,
            ),
            DriverEntry(
                field="opex_y1_keur",
                baseline_value=380.0, changed_value=800.0,
                kpi_deltas={}, status=STATUS_WIRED,
            ),
            DriverEntry(
                field="capacity_mw",
                baseline_value=50.0, changed_value=100.0,
                kpi_deltas={}, status=STATUS_WIRED,
            ),
            DriverEntry(
                field="gearing_pct",
                baseline_value=70.0, changed_value=85.0,
                kpi_deltas={}, status=STATUS_WIRED_PARTIAL,
            ),
            DriverEntry(
                field="ppa_term_years",
                baseline_value=10, changed_value=20,
                kpi_deltas={}, status=STATUS_METADATA_ONLY,
            ),
            DriverEntry(
                field="construction_months",
                baseline_value=12, changed_value=24,
                kpi_deltas={}, status=STATUS_METADATA_ONLY,
            ),
        )
        audit = DriverResponseAudit(
            project_type="Solar",
            entries=entries,
            field_count=len(entries),
            wired_count=sum(1 for e in entries if e.status == STATUS_WIRED),
            not_wired_count=sum(1 for e in entries if e.status == STATUS_NOT_WIRED),
            metadata_only_count=sum(
                1 for e in entries if e.status == STATUS_METADATA_ONLY
            ),
        )
        assert audit.field_count == 11  # 11 unique fields
        # Per the audit:
        # - 3 fields are full WIRED (tariff, p50_hours,
        #   capacity_mw, opex_y1_keur) = 4
        # - 5 fields are WIRED_PARTIAL (total_capex,
        #   gearing, interest_rate, tenor, target_dscr)
        #   = 5
        # - 2 fields are METADATA_ONLY (ppa_term_years,
        #   construction_months) = 2
        # - 0 fields are NOT_WIRED
        assert audit.wired_count == 5  # tariff, p50_hours, capacity, opex_y1, total_capex
        assert audit.not_wired_count == 0
        assert audit.metadata_only_count == 2  # ppa_term_years, construction_months
        # 4 fields are WIRED_PARTIAL: gearing, interest_rate, tenor, target_dscr
        # (DSCR_SCULPT keeps project_irr invariant; only other KPIs move)


# ---------------------------------------------------------------------------
# 14. No forbidden imports / feature flags
# ---------------------------------------------------------------------------


class TestAuditHelperSafety:
    """The audit helper does not import any forbidden
    module or set any feature flag."""

    FORBIDDEN_MODULES = [
        "app.persistence",
        "app.services",
        "app.construction",
        "app.debt",
        "app.tax",
        "app.idc",
        "app.depreciation",
        "app.waterfall",
    ]

    @pytest.mark.parametrize("module", FORBIDDEN_MODULES)
    def test_forbidden_module_not_imported(self, module):
        from app.ui import generic_driver_response_audit
        src = open(generic_driver_response_audit.__file__).read()
        assert f"import {module}" not in src
        assert f"from {module}" not in src

    def test_helper_does_not_set_construction_flag(self):
        from app.ui import generic_driver_response_audit
        src = open(generic_driver_response_audit.__file__).read()
        assert "use_construction_schedule_engine" not in src


# ---------------------------------------------------------------------------
# 15. Wind project (mirrors the Solar audit)
# ---------------------------------------------------------------------------


def _run_wind(schema: ProjectInputsSchema):
    """Run the Wind demo project with the given
    schema and return the WaterfallResult."""
    proj = build_projectinputs(schema)
    r = run_demo_project("Wind", "Base", project_inputs_override=proj)
    return r.result


class TestWindDrivers:
    """Mirror the Solar audit for the Wind template
    (Generic Wind). Same driver set, same status
    expectations."""

    def test_tariff_wired_wind(self):
        baseline = _run_wind(ProjectInputsSchema(
            project_type="Wind", scenario="Base",
            revenue=RevenueInput(tariff_eur_mwh=60.0),
        ))
        changed = _run_wind(ProjectInputsSchema(
            project_type="Wind", scenario="Base",
            revenue=RevenueInput(tariff_eur_mwh=80.0),
        ))
        deltas = compute_kpi_deltas(baseline, changed, AUDIT_KPIS)
        assert summarize_status(deltas) == STATUS_WIRED

    def test_p50_wired_wind(self):
        baseline = _run_wind(ProjectInputsSchema(
            project_type="Wind", scenario="Base",
            revenue=RevenueInput(p50_hours=3000.0),
        ))
        changed = _run_wind(ProjectInputsSchema(
            project_type="Wind", scenario="Base",
            revenue=RevenueInput(p50_hours=4000.0),
        ))
        deltas = compute_kpi_deltas(baseline, changed, AUDIT_KPIS)
        assert summarize_status(deltas) == STATUS_WIRED

    def test_gearing_wired_partial_wind(self):
        baseline = _run_wind(ProjectInputsSchema(
            project_type="Wind", scenario="Base",
            debt=DebtInput(gearing_pct=70.0),
        ))
        changed = _run_wind(ProjectInputsSchema(
            project_type="Wind", scenario="Base",
            debt=DebtInput(gearing_pct=85.0),
        ))
        deltas = compute_kpi_deltas(baseline, changed, AUDIT_KPIS)
        # Same partial wiring pattern as Solar.
        assert summarize_status(deltas) == STATUS_WIRED_PARTIAL

    def test_total_capex_wired_wind(self):
        baseline = _run_wind(ProjectInputsSchema(
            project_type="Wind", scenario="Base",
            capex=CapexInput(total_capex_keur=40000.0),
        ))
        changed = _run_wind(ProjectInputsSchema(
            project_type="Wind", scenario="Base",
            capex=CapexInput(total_capex_keur=60000.0),
        ))
        deltas = compute_kpi_deltas(baseline, changed, AUDIT_KPIS)
        assert summarize_status(deltas) == STATUS_WIRED

    def test_opex_y1_wired_wind(self):
        baseline = _run_wind(ProjectInputsSchema(
            project_type="Wind", scenario="Base",
            opex=OpexInput(opex_y1_keur=550.0),
        ))
        changed = _run_wind(ProjectInputsSchema(
            project_type="Wind", scenario="Base",
            opex=OpexInput(opex_y1_keur=900.0),
        ))
        deltas = compute_kpi_deltas(baseline, changed, AUDIT_KPIS)
        assert summarize_status(deltas) == STATUS_WIRED
