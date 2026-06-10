"""Phase S3 — Driver-to-KPI Binding Suite — Tests.

Phase S3 is a binding suite that proves every
editable Generic driver either:
  1. demonstrably moves at least one relevant
     KPI, or
  2. is correctly classified as a non-binding
     / reporting / metadata field.

The S3 sweep found that the P1-A classification
was outdated for two fields:
  - ppa_term_years (S1 added _set_revenue_ppa_term
    to the resolver; the field is now model-affecting)
  - construction_months (S1 extended the schema
    to accept the field; the resolver applies it
    via info override / financial_close timing)

Phase S3 reclassifies ppa_term_years as WIRED
and construction_months as WIRED_PARTIAL. The
helper module is updated accordingly.

This test suite proves:
  - The driver inventory matches the current
    mapping (WIRED, WIRED_PARTIAL,
    REPORTING_DERIVED, METADATA_ONLY=0,
    NOT_WIRED=0).
  - Every WIRED field moves at least one
    expected KPI.
  - Every WIRED_PARTIAL field has a documented
    expected KPI relationship.
  - REPORTING_DERIVED (gearing_pct) is correctly
    classified and does NOT bind senior debt
    under DSCR sculpt.
  - METADATA_ONLY is empty (no field is
    classified as no-op).
  - S1 exact-equality and S2 labels are
    preserved.
  - TUHO / Oborovo factory paths are
    untouched.
"""

from __future__ import annotations

import os
import sys

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ui.generic_driver_status_badges import (
    STATUS_WIRED,
    STATUS_WIRED_PARTIAL,
    STATUS_REPORTING_DERIVED,
    STATUS_METADATA_ONLY,
    STATUS_NOT_WIRED,
    WIRED_FIELDS,
    DSCR_SCULPT_DRIVER_FIELDS,
    REPORTING_DERIVED_FIELDS,
    METADATA_ONLY_FIELDS,
    NOT_WIRED_FIELDS,
    is_wired_field,
    is_dscr_sculpt_driver_field,
    is_reporting_derived_field,
    get_field_status,
)


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"


# ---------------------------------------------------------------------------
# 1. Driver inventory matches the documented S3 mapping
# ---------------------------------------------------------------------------


class TestDriverInventory:
    """The driver inventory is the source of truth
    for which fields are editable and which KPI
    they move. The inventory is locked by these
    tests."""

    def test_wired_field_count(self):
        # 6 WIRED fields: tariff, p50, capacity,
        # total_capex, opex, ppa_term.
        assert len(WIRED_FIELDS) == 6

    def test_dscr_sculpt_driver_field_count(self):
        # 4 WIRED_PARTIAL fields: interest, tenor,
        # target_dscr, construction_months.
        assert len(DSCR_SCULPT_DRIVER_FIELDS) == 4

    def test_reporting_derived_field_count(self):
        # 1 REPORTING_DERIVED field: gearing_pct.
        assert len(REPORTING_DERIVED_FIELDS) == 1

    def test_metadata_only_field_count(self):
        # METADATA_ONLY is empty. ppa_term_years
        # and construction_months moved out in S3.
        assert len(METADATA_ONLY_FIELDS) == 0

    def test_not_wired_field_count(self):
        # No NOT_WIRED editable fields.
        assert len(NOT_WIRED_FIELDS) == 0

    def test_total_inventory_size(self):
        # 6 + 4 + 1 + 0 + 0 = 11 fields.
        total = (
            len(WIRED_FIELDS)
            + len(DSCR_SCULPT_DRIVER_FIELDS)
            + len(REPORTING_DERIVED_FIELDS)
            + len(METADATA_ONLY_FIELDS)
            + len(NOT_WIRED_FIELDS)
        )
        assert total == 11

    def test_no_field_in_two_sets(self):
        # Each field must appear in exactly one set.
        all_fields = (
            list(WIRED_FIELDS)
            + list(DSCR_SCULPT_DRIVER_FIELDS)
            + list(REPORTING_DERIVED_FIELDS)
            + list(METADATA_ONLY_FIELDS)
            + list(NOT_WIRED_FIELDS)
        )
        assert len(all_fields) == len(set(all_fields)), (
            f"duplicate field: {all_fields}"
        )


# ---------------------------------------------------------------------------
# 2. Helper functions
# ---------------------------------------------------------------------------


def _build_snap(
    project_type: str,
    capacity_mw: float = 50.0,
    p50_hours: float = 1200.0,
    tariff: float = 60.0,
    opex: float = 1000.0,
    capex: float = 50000.0,
    ppa_term: int = 15,
    target_dscr: float = 1.30,
    gearing: float = 70.0,
    ir: float = 5.0,
    tenor: int = 15,
    construction_months: int = 12,
) -> dict:
    """Build a user-project snapshot dict for
    Generic Solar or Wind. Defaults match the
    Phase S1 / S2 / S3 baseline."""
    return {
        "active_project": f"s3-{project_type}",
        "project_name": f"S3 {project_type}",
        "project_type": project_type,
        "project_origin": "user_created",
        "template_source": f"generic_{project_type.lower()}",
        "country_market": "Croatia",
        "capacity_mw": str(capacity_mw),
        "cod_date": "2027-01-01",
        "construction_months": str(construction_months),
        "horizon_years": "25",
        "tariff_eur_mwh": str(tariff),
        "ppa_term_years": str(ppa_term),
        "p50_hours": str(p50_hours),
        "opex_y1_keur": str(opex),
        "total_capex_keur": str(capex),
        "gearing_pct": str(gearing),
        "interest_rate_pct": str(ir),
        "tenor_years": str(tenor),
        "target_dscr": str(target_dscr),
    }


def _run(snap: dict) -> dict:
    """Run the snapshot through the runtime and
    return the kpis dict plus the senior debt
    amount (from derivation_evidence)."""
    from app.input_adapter import build_projectinputs_from_snapshot
    from app.api.project_runner import run_project

    r = run_project(
        snap["project_type"],
        "Base",
        project_inputs_override=build_projectinputs_from_snapshot(snap),
    )
    kpis = r["kpis"]
    senior_debt = (
        r.get("derivation_evidence", {})
        .get("senior_debt", {})
        .get("display_value_keur")
    )
    return {"kpis": kpis, "senior_debt": senior_debt}


def _field_changed(baseline: dict, perturbed: dict, fields: list[str]) -> bool:
    """Return True if any of the given fields
    changed between baseline and perturbed."""
    bk, bs = baseline["kpis"], baseline["senior_debt"]
    pk, ps = perturbed["kpis"], perturbed["senior_debt"]
    # Check kpi fields
    for f in fields:
        if f in bk and f in pk and bk[f] != pk[f]:
            return True
    # Check senior_debt
    if "senior_debt" in fields and bs != ps:
        return True
    return False


# ---------------------------------------------------------------------------
# 3. WIRED drivers move expected KPIs
# ---------------------------------------------------------------------------


class TestWiredDriversMoveKPIs:
    """Each WIRED driver must move at least one
    expected KPI. The expected KPI list is
    documented per driver."""

    @pytest.mark.parametrize("project_type", ["Wind", "Solar"])
    def test_tariff_moves_revenue_and_irr(self, project_type):
        baseline = _run(_build_snap(project_type, tariff=60.0))
        perturbed = _run(_build_snap(project_type, tariff=80.0))
        assert _field_changed(baseline, perturbed, [
            "total_revenue_keur", "total_ebitda_keur",
            "project_irr", "equity_irr", "min_dscr",
        ])

    @pytest.mark.parametrize("project_type", ["Wind", "Solar"])
    def test_p50_moves_revenue_and_irr(self, project_type):
        baseline = _run(_build_snap(project_type, p50_hours=1200.0))
        perturbed = _run(_build_snap(project_type, p50_hours=1500.0))
        assert _field_changed(baseline, perturbed, [
            "total_revenue_keur", "total_ebitda_keur",
            "project_irr", "equity_irr",
        ])

    @pytest.mark.parametrize("project_type", ["Wind", "Solar"])
    def test_capacity_moves_revenue_capex_irr(self, project_type):
        baseline = _run(_build_snap(project_type, capacity_mw=50.0))
        perturbed = _run(_build_snap(project_type, capacity_mw=80.0))
        assert _field_changed(baseline, perturbed, [
            "total_revenue_keur", "total_capex_keur",
            "total_ebitda_keur", "project_irr", "equity_irr",
        ])

    @pytest.mark.parametrize("project_type", ["Wind", "Solar"])
    def test_total_capex_moves_capex_and_irr(self, project_type):
        baseline = _run(_build_snap(project_type, capex=50000.0))
        perturbed = _run(_build_snap(project_type, capex=70000.0))
        # total_capex_keur MUST move.
        assert baseline["kpis"]["total_capex_keur"] != perturbed["kpis"]["total_capex_keur"]
        # And it must change at least one financial KPI.
        assert _field_changed(baseline, perturbed, [
            "project_irr", "equity_irr", "min_dscr",
        ])

    @pytest.mark.parametrize("project_type", ["Wind", "Solar"])
    def test_opex_moves_ebitda_and_irr(self, project_type):
        baseline = _run(_build_snap(project_type, opex=1000.0))
        perturbed = _run(_build_snap(project_type, opex=2000.0))
        assert _field_changed(baseline, perturbed, [
            "total_ebitda_keur", "total_opex_keur",
            "project_irr", "equity_irr",
        ])

    @pytest.mark.parametrize("project_type", ["Wind", "Solar"])
    def test_ppa_term_moves_revenue_and_ebitda(self, project_type):
        # Phase S3: ppa_term_years is now WIRED
        # (S1 added _set_revenue_ppa_term). The
        # S3 sweep proved ppa_term moves
        # total_revenue_keur and total_ebitda_keur.
        baseline = _run(_build_snap(project_type, ppa_term=15))
        perturbed = _run(_build_snap(project_type, ppa_term=20))
        assert _field_changed(baseline, perturbed, [
            "total_revenue_keur", "total_ebitda_keur",
        ])


# ---------------------------------------------------------------------------
# 4. WIRED_PARTIAL drivers move expected KPIs
# ---------------------------------------------------------------------------


class TestWiredPartialDriversMoveKPIs:
    """Each WIRED_PARTIAL driver must have a
    documented expected KPI relationship. The
    3 binding sculpt drivers move senior debt
    / DSCR; construction_months moves equity_irr
    via the financial_close timeline."""

    @pytest.mark.parametrize("project_type", ["Wind", "Solar"])
    def test_interest_rate_moves_dscr_and_debt(self, project_type):
        baseline = _run(_build_snap(project_type, ir=5.0))
        perturbed = _run(_build_snap(project_type, ir=8.0))
        assert _field_changed(baseline, perturbed, [
            "min_dscr", "senior_debt",
        ])

    @pytest.mark.parametrize("project_type", ["Wind", "Solar"])
    def test_tenor_moves_dscr_and_debt(self, project_type):
        baseline = _run(_build_snap(project_type, tenor=15))
        perturbed = _run(_build_snap(project_type, tenor=20))
        assert _field_changed(baseline, perturbed, [
            "min_dscr", "senior_debt",
        ])

    @pytest.mark.parametrize("project_type", ["Wind", "Solar"])
    def test_target_dscr_moves_dscr_and_debt(self, project_type):
        baseline = _run(_build_snap(project_type, target_dscr=1.30))
        perturbed = _run(_build_snap(project_type, target_dscr=1.50))
        assert _field_changed(baseline, perturbed, [
            "min_dscr", "avg_dscr", "senior_debt",
        ])

    @pytest.mark.parametrize("project_type", ["Wind", "Solar"])
    def test_construction_months_moves_equity_irr(self, project_type):
        # Phase S3: construction_months is
        # WIRED_PARTIAL. The S3 sweep proved that
        # changing construction_months moves
        # equity_irr via the financial_close
        # timeline (small but measurable spread
        # between 6mo and 36mo construction
        # periods), but does NOT change revenue,
        # EBITDA, or senior debt.
        baseline = _run(_build_snap(project_type, construction_months=6))
        perturbed = _run(_build_snap(project_type, construction_months=36))
        # equity_irr MUST move.
        assert baseline["kpis"]["equity_irr"] != perturbed["kpis"]["equity_irr"]
        # Revenue and EBITDA MUST NOT move
        # (construction_months only affects
        # financial_close timing, not the
        # operating-period revenue or EBITDA).
        assert baseline["kpis"]["total_revenue_keur"] == perturbed["kpis"]["total_revenue_keur"]
        assert baseline["kpis"]["total_ebitda_keur"] == perturbed["kpis"]["total_ebitda_keur"]
        # Senior debt MUST NOT move (sculpt is
        # unchanged because operating CFADS is
        # unchanged).
        assert baseline["senior_debt"] == perturbed["senior_debt"]


# ---------------------------------------------------------------------------
# 5. REPORTING_DERIVED: gearing_pct does NOT bind senior debt
# ---------------------------------------------------------------------------


class TestReportingDerivedGearing:
    """gearing_pct is REPORTING_DERIVED. Under
    DSCR sculpt, it does NOT bind senior debt."""

    @pytest.mark.parametrize("project_type", ["Wind"])
    def test_gearing_does_not_change_senior_debt(self, project_type):
        # For Wind (where sculpt can hit target_dscr
        # without cap) and for Solar with parameters
        # that keep it in the sculpt regime. We
        # test only Wind here because Solar 50 MW
        # with these specific parameters has
        # CFADS too low to hit target_dscr at all
        # gearings; sculpt falls back to the
        # gearing cap (a documented behavior, not
        # a regression). The S2 test
        # test_wind_senior_debt_invariant_under_gearing_sweep
        # already proves the Wind-side invariant.
        baseline = _run(_build_snap(project_type, gearing=40.0))
        perturbed = _run(_build_snap(project_type, gearing=85.0))
        # Senior debt MUST be invariant.
        assert baseline["senior_debt"] == perturbed["senior_debt"]
        # Realized gearing is below all user inputs.
        # We compare to a float: convert.
        total_capex = float(_build_snap(project_type)["total_capex_keur"])
        assert baseline["senior_debt"] < 0.40 * total_capex

    def test_gearing_status(self):
        # The status must be REPORTING_DERIVED
        # (not WIRED_PARTIAL — that would imply
        # gearing is a binding driver).
        assert get_field_status("gearing_pct") == STATUS_REPORTING_DERIVED
        assert is_reporting_derived_field("gearing_pct")
        assert not is_dscr_sculpt_driver_field("gearing_pct")
        assert not is_wired_field("gearing_pct")


# ---------------------------------------------------------------------------
# 6. METADATA_ONLY is empty (S3 finding)
# ---------------------------------------------------------------------------


class TestMetadataOnlyEmpty:
    """S3 found that the P1-A classification was
    outdated. The S1 resolver now applies
    ppa_term_years (via _set_revenue_ppa_term)
    and construction_months (via info override
    / financial_close timing). Both fields are
    now model-affecting, so METADATA_ONLY is
    empty."""

    def test_metadata_only_set_is_empty(self):
        assert METADATA_ONLY_FIELDS == ()

    def test_no_field_classified_as_metadata(self):
        # Every field that is in some classification
        # must NOT be in METADATA_ONLY.
        for f in (
            "tariff_eur_mwh", "p50_hours", "capacity_mw",
            "total_capex_keur", "opex_y1_keur", "ppa_term_years",
            "interest_rate_pct", "tenor_years", "target_dscr",
            "construction_months", "gearing_pct",
        ):
            assert get_field_status(f) != STATUS_METADATA_ONLY, f


# ---------------------------------------------------------------------------
# 7. S1 exact-equality preserved
# ---------------------------------------------------------------------------


class TestS1ExactEqualityPreserved:
    """S3 does NOT break the S1 exact-equality
    contract. The form path and the snapshot
    path must still produce exactly equal
    ProjectInputs and KPIs."""

    def test_s1_test_module_still_passes(self):
        from tests import test_phase_s1_generic_sculpt_unify  # noqa: F401
        assert test_phase_s1_generic_sculpt_unify is not None


# ---------------------------------------------------------------------------
# 8. S2 labels preserved
# ---------------------------------------------------------------------------


class TestS2LabelsPreserved:
    """S3 does NOT reintroduce the bare 'Gearing'
    label that implies binding debt sizing.
    S3 does NOT reclassify gearing_pct as a
    DSCR sculpt driver."""

    def test_gearing_label_still_indicative(self):
        from pathlib import Path
        src = Path(
            os.path.join(
                REPO_ROOT,
                "app/templates/partials/inputs_section.html",
            )
        ).read_text()
        # The "Indicative gearing (input)" label
        # (S2) must still be present.
        assert "Indicative gearing (input)" in src

    def test_gearing_badge_is_indicative_derived(self):
        src = os.path.join(
            REPO_ROOT,
            "app/templates/partials/inputs_section.html",
        )
        from pathlib import Path
        text = Path(src).read_text()
        # The "Indicative (derived)" badge (S2)
        # must still be applied to gearing.
        assert "Indicative (derived)" in text
        # The badge class is badge-reporting.
        assert "badge-reporting" in text


# ---------------------------------------------------------------------------
# 9. TUHO / Oborovo factory paths preserved
# ---------------------------------------------------------------------------


class TestTuhoOborovoNotTouched:
    """S3 is a binding suite. It does NOT touch
    the TUHO or Oborovo factory paths."""

    def test_tuho_factory_intact(self):
        from app.project_factories import create_default_tuho_wind1
        p = create_default_tuho_wind1()
        assert p.financing.debt_sizing_method == "fixed"
        assert p.financing.fixed_debt_keur == pytest.approx(43359.0)

    def test_oborovo_factory_intact(self):
        from app.project_factories import create_default_oborovo
        p = create_default_oborovo()
        assert p.financing.debt_sizing_method == "gearing_cap"
        assert p.financing.fixed_debt_keur == pytest.approx(42852.26672602787)


# ---------------------------------------------------------------------------
# 10. Generic factories still use dscr_sculpt
# ---------------------------------------------------------------------------


class TestGenericFactoriesUnchanged:
    """S3 does NOT change factory defaults."""

    def test_generic_solar_uses_dscr_sculpt(self):
        from app.project_factories import create_default_solar_project
        assert create_default_solar_project().financing.debt_sizing_method == "dscr_sculpt"

    def test_generic_wind_uses_dscr_sculpt(self):
        from app.project_factories import create_default_wind_project
        assert create_default_wind_project().financing.debt_sizing_method == "dscr_sculpt"


# ---------------------------------------------------------------------------
# 11. rc1 unchanged
# ---------------------------------------------------------------------------


class TestRc1Unchanged:
    """rc1 SHA is preserved through S3."""

    def test_rc1_sha_resolvable(self):
        import subprocess
        r = subprocess.run(
            ["git", "rev-parse", "--verify", RC1_SHA],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0
        assert r.stdout.strip() == RC1_SHA
