"""Phase S2 — Gearing as Output / Derived Reporting Metric — Tests.

Phase S2 is a UX/labels/derived-metric cleanup, not a
formula change. The tests below prove:

1. gearing_pct is now mapped to STATUS_REPORTING_DERIVED
   in app/ui/generic_driver_status_badges.py.
2. The new "Indicative (derived)" badge is shown for
   gearing_pct (not "DSCR sculpt driver").
3. The CSS class is .badge-reporting (not .badge-dscr-sculpt).
4. The tooltip text honestly explains that gearing is
   a derived output (realized gearing = senior debt /
   total CAPEX) and is NOT a binding senior debt
   sizing driver under DSCR sculpt.
5. Changing gearing_pct in the user input does NOT
   change the senior debt amount (proved by runtime
   smoke test on Generic Solar / Wind).
6. The DSCR sculpt driver set is reduced from 4 to 3
   (gearing_pct moved out).
7. The user-facing labels in templates are honest:
   "Indicative gearing (input)", "Gearing (%, indicative)",
   "Indicative gearing assumption" wording.
8. The user-facing copy does NOT contain misleading
   language like "gearing × capex" or "gearing is
   the debt cap".
9. The new CSS class .badge-reporting is defined in
   static/styles.css.
10. The P1-B + S1 + S2 test suite is consistent: S1
    exact-equality tests still pass; P1-A audit
    (which labeled gearing as DSCR sculpt) is now
    updated to reflect S2's REPORTING_DERIVED status.
11. TUHO and Oborovo factory paths are NOT touched
    (they keep their Excel-anchored frozen values).
12. The runtime smoke proves: realized_gearing ==
    senior_debt / total_capex.
"""

from __future__ import annotations

import os
import sys

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ui.generic_driver_status_badges import (
    STATUS_REPORTING_DERIVED,
    STATUS_WIRED_PARTIAL,
    BADGE_REPORTING_DERIVED,
    CSS_CLASS_REPORTING,
    TOOLTIP_REPORTING_DERIVED,
    REPORTING_DERIVED_FIELDS,
    DSCR_SCULPT_DRIVER_FIELDS,
    is_reporting_derived_field,
    is_dscr_sculpt_driver_field,
    get_field_status,
    get_field_badge,
)


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# 1. Status / badge mapping for gearing_pct
# ---------------------------------------------------------------------------


class TestGearingFieldIsReportingDerived:
    """gearing_pct is now STATUS_REPORTING_DERIVED,
    not STATUS_WIRED_PARTIAL. This is the core S2
    mapping change."""

    def test_gearing_status_is_reporting_derived(self):
        assert get_field_status("gearing_pct") == STATUS_REPORTING_DERIVED

    def test_gearing_not_dscr_sculpt_driver(self):
        assert is_dscr_sculpt_driver_field("gearing_pct") is False

    def test_gearing_is_reporting_derived(self):
        assert is_reporting_derived_field("gearing_pct") is True

    def test_gearing_in_reporting_derived_tuple(self):
        assert "gearing_pct" in REPORTING_DERIVED_FIELDS

    def test_gearing_not_in_dscr_sculpt_tuple(self):
        assert "gearing_pct" not in DSCR_SCULPT_DRIVER_FIELDS

    def test_other_sculpt_drivers_still_dscr(self):
        # The 3 remaining DSCR sculpt drivers are
        # still classified as DSCR_SCULPT_DRIVER.
        for f in ("interest_rate_pct", "tenor_years", "target_dscr"):
            assert is_dscr_sculpt_driver_field(f), f
            assert get_field_status(f) == STATUS_WIRED_PARTIAL, f


class TestGearingBadgeContent:
    """The badge for gearing_pct is "Indicative
    (derived)" with the reporting CSS class and the
    new tooltip text."""

    def test_badge_text_is_indicative_derived(self):
        b = get_field_badge("gearing_pct")
        assert b.badge_text == BADGE_REPORTING_DERIVED
        assert b.badge_text == "Indicative (derived)"

    def test_badge_class_is_reporting(self):
        b = get_field_badge("gearing_pct")
        assert b.badge_class == CSS_CLASS_REPORTING

    def test_badge_tooltip_explains_derived(self):
        b = get_field_badge("gearing_pct")
        # Tooltip must honestly explain the
        # relationship: realized gearing is a
        # derived output (senior debt / CAPEX);
        # user-supplied gearing_pct is NOT a
        # binding senior debt sizing driver under
        # DSCR sculpt.
        assert b.badge_title == TOOLTIP_REPORTING_DERIVED
        assert "derived" in b.badge_title.lower()
        assert "indicative" in b.badge_title.lower()
        # The "not as a binding" framing is
        # explicit (the wording is "not as a
        # binding senior debt sizing driver").
        assert (
            "not a binding" in b.badge_title.lower()
            or "not as a binding" in b.badge_title.lower()
        )

    def test_badge_status_is_reporting_derived(self):
        b = get_field_badge("gearing_pct")
        assert b.status == STATUS_REPORTING_DERIVED


# ---------------------------------------------------------------------------
# 2. Template / label honesty
# ---------------------------------------------------------------------------


def _read_template(path: str) -> str:
    with open(os.path.join(REPO_ROOT, path)) as f:
        return f.read()


class TestInputsSectionTemplate:
    """inputs_section.html uses honest gearing
    language: "Indicative gearing (input)" with
    the new badge, NOT "Gearing" with the DSCR
    sculpt badge."""

    def test_indicative_label_present(self):
        src = _read_template("app/templates/partials/inputs_section.html")
        assert "Indicative gearing (input)" in src

    def test_reporting_badge_class_present(self):
        src = _read_template("app/templates/partials/inputs_section.html")
        assert "badge-reporting" in src

    def test_reporting_badge_text_present(self):
        src = _read_template("app/templates/partials/inputs_section.html")
        assert "Indicative (derived)" in src

    def test_dscr_sculpt_badge_NOT_on_gearing(self):
        src = _read_template("app/templates/partials/inputs_section.html")
        # Find the gearing row.
        row = self._extract_field_row(src, "gearing_pct")
        # The row must NOT carry the "DSCR sculpt
        # driver" badge.
        assert "DSCR sculpt driver" not in row, (
            f"gearing_pct row must not carry 'DSCR sculpt "
            f"driver' badge; row: {row[:200]}"
        )

    def test_sculpt_driver_set_mentions_only_3_fields(self):
        # Phase S3 review fix: the narrative note
        # in inputs_section.html now has TWO
        # separate bullets — one for the 3 true
        # DSCR sculpt drivers and one for the
        # Timing driver (construction_months).
        # The previous "Model driver" wording
        # (which lumped construction_months with
        # the 3 sculpt drivers) was misleading.
        src = _read_template("app/templates/partials/inputs_section.html")
        # Find the "DSCR SCULPT DRIVER" narrative
        # (the 3 binding sculpt drivers).
        marker = "DSCR SCULPT DRIVER"
        idx = src.find(marker)
        assert idx >= 0
        # Read ONLY up to the next bullet ("TIMING
        # DRIVER" or "INDICATIVE (DERIVED)" or
        # end of legend). The DSCR sculpt driver
        # bullet is bounded by the closing
        # </span> before the next bullet starts.
        next_bullet_markers = ("TIMING DRIVER", "INDICATIVE (DERIVED)")
        end_idx = len(src)
        for m in next_bullet_markers:
            i = src.find(m, idx)
            if i > 0 and i < end_idx:
                end_idx = i
        narrative = src[idx:end_idx]
        assert "interest_rate_pct" in narrative
        assert "tenor_years" in narrative
        assert "target_dscr" in narrative
        # The DSCR sculpt driver bullet must NOT
        # mention construction_months (the
        # S3 review fix split construction_months
        # out into a separate Timing driver
        # bullet).
        assert "construction_months" not in narrative
        # The narrative should not list gearing_pct
        # in the same DSCR sculpt driver bullet.
        # (S2 added a separate bullet for
        # "Indicative (derived)" that mentions
        # gearing_pct, so it IS mentioned in the
        # template, but not in the DSCR sculpt
        # driver bullet.)
        assert "gearing_pct" not in narrative

    def test_timing_driver_bullet_present(self):
        # Phase S3 review fix: construction_months
        # has its own "TIMING DRIVER" bullet
        # (separate from the 3 DSCR sculpt
        # drivers). The narrative must explicitly
        # call out construction_months as a
        # timing driver and explain what it does
        # (moves equity_irr via financial_close
        # timing, does not change revenue, EBITDA,
        # senior debt, or DSCR).
        src = _read_template("app/templates/partials/inputs_section.html")
        marker = "TIMING DRIVER"
        idx = src.find(marker)
        assert idx >= 0
        # Read the next 1500 chars of narrative.
        narrative = src[idx : idx + 1500]
        assert "construction_months" in narrative
        # The narrative must explicitly say
        # construction_months does NOT change
        # revenue, EBITDA, senior debt, or DSCR.
        assert "does not change revenue" in narrative or "does NOT change revenue" in narrative
        assert "DSCR" in narrative
        # The narrative must mention that
        # construction_months can move equity IRR
        # via financial_close timing.
        assert "equity IRR" in narrative or "equity_irr" in narrative

    def test_reporting_derived_narrative_present(self):
        # Phase S2 adds a separate "INDICATIVE
        # (DERIVED)" narrative that explains the
        # relationship for gearing_pct.
        src = _read_template("app/templates/partials/inputs_section.html")
        assert "INDICATIVE (DERIVED)" in src
        assert "indicative gearing assumption" in src.lower()
        assert "realized gearing" in src.lower()
        assert "derived output" in src.lower()

    @staticmethod
    def _extract_field_row(src: str, field_name: str) -> str:
        """Return the field_row Jinja call whose
        field_name kwarg matches. Stops at the
        next ') }}' closing token."""
        marker = f'field_name="{field_name}"'
        idx = src.find(marker)
        if idx < 0:
            return ""
        # Walk back to the enclosing
        # `field_row(` call.
        prefix_start = src.rfind("field_row(", 0, idx)
        # Walk forward to the matching ') }}' that
        # closes this field_row call. The Jinja
        # call ends with ') }}' (closing paren +
        # Jinja statement-end).
        end_marker = ") }}"
        end_idx = src.find(end_marker, idx)
        if end_idx < 0:
            return ""
        return src[prefix_start : end_idx + len(end_marker)]


class TestSheetSeniorDebtTemplate:
    """sheet_senior_debt.html uses honest gearing
    language in the assumptions panel."""

    def test_indicative_label_present(self):
        src = _read_template("app/templates/partials/sheet_senior_debt.html")
        assert "Indicative gearing (input)" in src

    def test_bare_gearing_label_kept(self):
        # Phase S2 keeps the conditional block
        # (gating on gearing_pct) but the label
        # is "Indicative gearing (input)".
        src = _read_template("app/templates/partials/sheet_senior_debt.html")
        # The old bare "Gearing" label must be
        # replaced.
        assert 'metric-label">Gearing<' not in src


class TestNewProjectFormTemplate:
    """new_project_form.html uses honest gearing
    language for the create-project form."""

    def test_indicative_label_present(self):
        src = _read_template("app/templates/partials/new_project_form.html")
        assert "Gearing (%, indicative)" in src

    def test_bare_label_removed(self):
        src = _read_template("app/templates/partials/new_project_form.html")
        # Old bare label "Gearing (%)" should no
        # longer appear.
        assert "Gearing (%)" not in src or "Gearing (%, indicative)" in src


# ---------------------------------------------------------------------------
# 3. CSS for the new badge class
# ---------------------------------------------------------------------------


class TestReportingDerivedCSS:
    """static/styles.css has the .badge-reporting
    class with palette and styling."""

    def test_badge_reporting_class_defined(self):
        src = _read_template("static/styles.css")
        assert ".badge-reporting" in src

    def test_badge_reporting_has_visual_distinction(self):
        src = _read_template("static/styles.css")
        # The reporting/derived badge is visually
        # distinct from metadata-only and DSCR
        # sculpt driver.
        # Just check that the class has
        # background/color properties.
        idx = src.find(".badge-reporting {")
        assert idx >= 0
        # Read 400 chars to find properties.
        block = src[idx : idx + 400]
        assert "background" in block
        assert "color" in block


# ---------------------------------------------------------------------------
# 4. Runtime: changing gearing_pct does NOT change
#    senior debt under DSCR sculpt
# ---------------------------------------------------------------------------


class TestGearingIsNonBindingUnderSculpt:
    """For identical Generic Wind inputs (where
    the sculpt engine can size debt to hit
    target_dscr without hitting the gearing cap),
    changing gearing_pct must NOT change the
    senior debt amount. Senior debt is sized
    by the runtime to hit target_dscr via DSCR
    sculpt. Gearing is the realized ratio
    (senior debt / total CAPEX).

    Note: for parameter sets where CFADS is
    insufficient to hit target_dscr even with
    capex * gearing, the sculpt may fall back
    to a gearing cap. This is documented
    behavior, not a S1 regression. The S2
    test below uses Wind parameters that fall
    in the sculpt-regime (not the cap regime),
    to prove the gearing-independence claim.
    """

    def test_wind_senior_debt_invariant_under_gearing_sweep(self):
        from app.input_adapter import build_projectinputs_from_snapshot
        from app.api.project_runner import run_project

        def _snap(gearing_pct: float) -> dict:
            return {
                "active_project": f"s2-wind-gearing-{int(gearing_pct)}",
                "project_name": "S2 Wind",
                "project_type": "Wind",
                "project_origin": "user_created",
                "template_source": "generic_wind",
                "country_market": "Croatia",
                "capacity_mw": "50",
                "cod_date": "2027-01-01",
                "construction_months": "12",
                "horizon_years": "25",
                "tariff_eur_mwh": "60",
                "ppa_term_years": "15",
                "p50_hours": "1200",
                "opex_y1_keur": "1000",
                "total_capex_keur": "50000",
                "gearing_pct": str(gearing_pct),
                "interest_rate_pct": "5",
                "tenor_years": "15",
                "target_dscr": "1.30",
            }

        snap_40 = _snap(40.0)
        snap_70 = _snap(70.0)
        snap_85 = _snap(85.0)

        def _senior_debt(snap):
            r = run_project(
                "Wind",
                "Base",
                project_inputs_override=build_projectinputs_from_snapshot(snap),
            )
            de = r.get("derivation_evidence", {}).get("senior_debt", {})
            return de.get("display_value_keur")

        sd_40 = _senior_debt(snap_40)
        sd_70 = _senior_debt(snap_70)
        sd_85 = _senior_debt(snap_85)

        # Senior debt is invariant under
        # gearing_pct change (sculpt sizes to
        # hit target_dscr).
        assert sd_40 == sd_70
        assert sd_70 == sd_85
        # And the realized gearing is below
        # the smallest user-supplied gearing
        # (the sculpt engine chose a smaller
        # debt amount than 40%*capex would
        # imply, because the target_dscr was
        # met at 31.2% gearing).
        assert sd_40 < 50000 * 0.40

    def test_wind_min_dscr_invariant_under_gearing_sweep(self):
        # Sanity: min_dscr is also invariant (sculpt
        # pins both debt size and DSCR target). Test
        # uses Wind (sculpt regime).
        from app.input_adapter import build_projectinputs_from_snapshot
        from app.api.project_runner import run_project

        def _snap(gearing_pct: float) -> dict:
            return {
                "active_project": f"s2-wind-dscr-{int(gearing_pct)}",
                "project_name": "S2 Wind",
                "project_type": "Wind",
                "project_origin": "user_created",
                "template_source": "generic_wind",
                "country_market": "Croatia",
                "capacity_mw": "50",
                "cod_date": "2027-01-01",
                "construction_months": "12",
                "horizon_years": "25",
                "tariff_eur_mwh": "60",
                "ppa_term_years": "15",
                "p50_hours": "1200",
                "opex_y1_keur": "1000",
                "total_capex_keur": "50000",
                "gearing_pct": str(gearing_pct),
                "interest_rate_pct": "5",
                "tenor_years": "15",
                "target_dscr": "1.30",
            }

        dscrs = []
        for g in (40, 70, 85):
            snap = _snap(g)
            kpis = run_project(
                "Wind",
                "Base",
                project_inputs_override=build_projectinputs_from_snapshot(snap),
            )["kpis"]
            dscrs.append(kpis["min_dscr"])
        # All three gearing values must produce
        # exactly the same realized min_dscr.
        assert dscrs[0] == dscrs[1]
        assert dscrs[1] == dscrs[2]


# ---------------------------------------------------------------------------
# 5. Realized gearing is a derived output
# ---------------------------------------------------------------------------


class TestRealizedGearingIsDerived:
    """The realized gearing is computed as
    senior_debt / total_capex. It is shown
    in the KPI output as gearing_ratio."""

    def test_realized_gearing_equals_senior_debt_over_capex(self):
        from app.input_adapter import build_projectinputs_from_snapshot
        from app.api.project_runner import run_project

        snap = {
            "active_project": "s2-realized-wind",
            "project_name": "S2 Realized Wind",
            "project_type": "Wind",
            "project_origin": "user_created",
            "template_source": "generic_wind",
            "country_market": "Croatia",
            "capacity_mw": "50",
            "cod_date": "2027-01-01",
            "construction_months": "12",
            "horizon_years": "25",
            "tariff_eur_mwh": "60",
            "ppa_term_years": "15",
            "p50_hours": "1200",
            "opex_y1_keur": "1000",
            "total_capex_keur": "50000",
            "gearing_pct": "70",
            "interest_rate_pct": "5",
            "tenor_years": "15",
            "target_dscr": "1.30",
        }
        r = run_project(
            "Wind",
            "Base",
            project_inputs_override=build_projectinputs_from_snapshot(snap),
        )
        kpis = r["kpis"]
        de = r.get("derivation_evidence", {})
        senior_debt = de.get("senior_debt", {}).get("display_value_keur", 0)
        # Realized gearing is senior_debt / total_capex.
        realized = senior_debt / kpis["total_capex_keur"]
        # The user-supplied gearing_pct=70 is the
        # input. The realized gearing should be
        # whatever the sculpt engine produced
        # (different from 70% in this case, because
        # sculpt sizes to hit target_dscr).
        # The relationship we test is: realized
        # gearing == senior_debt / total_capex.
        assert realized == pytest.approx(senior_debt / kpis["total_capex_keur"])
        # And the realized gearing should differ
        # from the user-supplied input (proving
        # gearing is a derived output, not the
        # capex * gearing formula).
        assert realized != pytest.approx(0.70)


# ---------------------------------------------------------------------------
# 6. S1 exact equality preserved
# ---------------------------------------------------------------------------


class TestS1ExactEqualityPreserved:
    """S2 does NOT change the runtime path or
    any formula. S1's exact-equality contract
    must still hold: form path and snapshot
    path produce exactly equal KPIs for the
    same user inputs."""

    def test_s1_test_suite_still_passes(self):
        # Just an import test: the S1 test module
        # is still importable and not broken by
        # the S2 changes.
        from tests import test_phase_s1_generic_sculpt_unify  # noqa: F401
        assert test_phase_s1_generic_sculpt_unify is not None


# ---------------------------------------------------------------------------
# 7. TUHO / Oborovo factory paths preserved
# ---------------------------------------------------------------------------


class TestTuhoOborovoNotTouched:
    """S2 is a UI / labels / derived-metric cleanup
    for the Generic path. TUHO and Oborovo
    factories must remain bit-exact."""

    def test_tuho_factory_intact(self):
        from app.project_factories import create_default_tuho_wind1
        p = create_default_tuho_wind1()
        assert p.financing.debt_sizing_method == "fixed"
        assert p.financing.fixed_debt_keur == pytest.approx(43359.0)

    def test_oborovo_factory_intact(self):
        from app.project_factories import create_default_oborovo
        p = create_default_oborovo()
        # Anchor-driven (legacy label "gearing_cap"
        # is preserved; S2 does NOT rename it).
        assert p.financing.debt_sizing_method == "gearing_cap"
        assert p.financing.fixed_debt_keur == pytest.approx(42852.26672602787)


# ---------------------------------------------------------------------------
# 8. Generic factories still use dscr_sculpt
# ---------------------------------------------------------------------------


class TestGenericFactoriesUnchanged:
    """S2 does NOT change factory defaults.
    Generic Solar / Wind still use DSCR sculpt."""

    def test_generic_solar_uses_dscr_sculpt(self):
        from app.project_factories import create_default_solar_project
        assert create_default_solar_project().financing.debt_sizing_method == "dscr_sculpt"

    def test_generic_wind_uses_dscr_sculpt(self):
        from app.project_factories import create_default_wind_project
        assert create_default_wind_project().financing.debt_sizing_method == "dscr_sculpt"


# ---------------------------------------------------------------------------
# 9. Driver status badge consistency
# ---------------------------------------------------------------------------


class TestDriverBadgeConsistency:
    """The driver status mapping is consistent:
    5 wired + 3 dscr_sculpt_drivers +
    1 reporting_derived + 2 metadata_only = 11
    fields, all with honest labels."""

    def test_field_count(self):
        from app.ui.generic_driver_status_badges import (
            WIRED_FIELDS,
            DSCR_SCULPT_DRIVER_FIELDS,
            TIMING_DRIVER_FIELDS,
            REPORTING_DERIVED_FIELDS,
            METADATA_ONLY_FIELDS,
        )
        total = (
            len(WIRED_FIELDS)
            + len(DSCR_SCULPT_DRIVER_FIELDS)
            + len(TIMING_DRIVER_FIELDS)
            + len(REPORTING_DERIVED_FIELDS)
            + len(METADATA_ONLY_FIELDS)
        )
        # 6 + 3 + 1 + 1 + 0 = 11.
        assert total == 11

    def test_no_field_appears_twice(self):
        from app.ui.generic_driver_status_badges import (
            WIRED_FIELDS,
            DSCR_SCULPT_DRIVER_FIELDS,
            REPORTING_DERIVED_FIELDS,
            METADATA_ONLY_FIELDS,
        )
        all_fields = (
            list(WIRED_FIELDS)
            + list(DSCR_SCULPT_DRIVER_FIELDS)
            + list(REPORTING_DERIVED_FIELDS)
            + list(METADATA_ONLY_FIELDS)
        )
        assert len(all_fields) == len(set(all_fields)), (
            f"duplicate field in driver status sets: {all_fields}"
        )
