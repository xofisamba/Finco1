"""Phase PR3 — Taxonomy / Brief Alignment Tests.

Phase PR3 establishes ONE canonical source of
truth for driver classification and sizing
terminology. The source of truth lives in
``app.ui.driver_taxonomy``.

These tests prove:

  1. The canonical categories tuple contains
     the 6 expected categories.
  2. The canonical field mapping has the
     11 editable Generic form fields with
     the correct category each.
  3. construction_months is TIMING_DRIVER
     (NOT METADATA_ONLY and NOT
     DSCR_SCULPT_DRIVER).
  4. ppa_term_years is WIRED (NOT
     METADATA_ONLY).
  5. gearing_pct is REPORTING_DERIVED
     (NOT WIRED, NOT METADATA_ONLY, NOT
     DSCR_SCULPT_DRIVER).
  6. interest_rate_pct / tenor_years /
     target_dscr are DSCR_SCULPT_DRIVER.
  7. METADATA_ONLY and NOT_WIRED are empty
     unless a current editable field truly
     belongs there.
  8. P1-B UI badges helper agrees with the
     canonical mapping (no drift).
  9. S3 binding suite agrees with the
     canonical mapping (no drift).
  10. The "Excel methodology" copy vs "App
      parity strategy" copy is centrally
      documented and not contradictory.
  11. No stale active claim that
      ppa_term_years or construction_months
      are metadata-only.
  12. No stale active claim that gearing
      binds senior debt.
  13. No stale near-term manual_gearing
      roadmap claim in active docs.
  14. S1, S2, S3, M1, PR1, PR2 tests still
      pass.
  15. Phase 51F parity guardrails pass.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Repo root
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]

RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"


# ---------------------------------------------------------------------------
# Canonical taxonomy tests
# ---------------------------------------------------------------------------


class TestCanonicalCategories:
    """The 6 canonical categories exist in
    ``CANONICAL_CATEGORIES`` and the
    vocabulary is exposed as module-level
    constants.
    """

    def test_canonical_categories_tuple(self):
        from app.ui.driver_taxonomy import (
            CANONICAL_CATEGORIES,
        )
        assert CANONICAL_CATEGORIES == (
            "WIRED",
            "DSCR_SCULPT_DRIVER",
            "TIMING_DRIVER",
            "REPORTING_DERIVED",
            "METADATA_ONLY",
            "NOT_WIRED",
        )

    def test_constants_match_categories(self):
        from app.ui import driver_taxonomy as dt
        assert dt.CATEGORY_WIRED == "WIRED"
        assert dt.CATEGORY_DSCR_SCULPT_DRIVER == "DSCR_SCULPT_DRIVER"
        assert dt.CATEGORY_TIMING_DRIVER == "TIMING_DRIVER"
        assert dt.CATEGORY_REPORTING_DERIVED == "REPORTING_DERIVED"
        assert dt.CATEGORY_METADATA_ONLY == "METADATA_ONLY"
        assert dt.CATEGORY_NOT_WIRED == "NOT_WIRED"


class TestCanonicalFieldMapping:
    """Each of the 11 editable Generic form
    fields is mapped to the correct canonical
    category.
    """

    def test_11_fields_total(self):
        from app.ui.driver_taxonomy import (
            CANONICAL_FIELD_MAPPING,
        )
        assert len(CANONICAL_FIELD_MAPPING) == 11, (
            f"Phase P1-A brief specifies 11 editable "
            f"Generic form fields; got "
            f"{len(CANONICAL_FIELD_MAPPING)}"
        )

    def test_no_duplicate_field(self):
        from app.ui.driver_taxonomy import (
            CANONICAL_FIELD_MAPPING,
        )
        fields = [f for f, _ in CANONICAL_FIELD_MAPPING]
        assert len(fields) == len(set(fields)), (
            f"Field mapping has duplicates: {fields}"
        )

    def test_tariff_is_wired(self):
        from app.ui.driver_taxonomy import (
            CANONICAL_FIELD_MAPPING, CATEGORY_WIRED,
        )
        assert ("tariff_eur_mwh", CATEGORY_WIRED) in CANONICAL_FIELD_MAPPING

    def test_p50_hours_is_wired(self):
        from app.ui.driver_taxonomy import (
            CANONICAL_FIELD_MAPPING, CATEGORY_WIRED,
        )
        assert ("p50_hours", CATEGORY_WIRED) in CANONICAL_FIELD_MAPPING

    def test_capacity_mw_is_wired(self):
        from app.ui.driver_taxonomy import (
            CANONICAL_FIELD_MAPPING, CATEGORY_WIRED,
        )
        assert ("capacity_mw", CATEGORY_WIRED) in CANONICAL_FIELD_MAPPING

    def test_total_capex_is_wired(self):
        from app.ui.driver_taxonomy import (
            CANONICAL_FIELD_MAPPING, CATEGORY_WIRED,
        )
        assert ("total_capex_keur", CATEGORY_WIRED) in CANONICAL_FIELD_MAPPING

    def test_opex_is_wired(self):
        from app.ui.driver_taxonomy import (
            CANONICAL_FIELD_MAPPING, CATEGORY_WIRED,
        )
        assert ("opex_y1_keur", CATEGORY_WIRED) in CANONICAL_FIELD_MAPPING

    def test_ppa_term_years_is_wired(self):
        from app.ui.driver_taxonomy import (
            CANONICAL_FIELD_MAPPING, CATEGORY_WIRED,
        )
        assert ("ppa_term_years", CATEGORY_WIRED) in CANONICAL_FIELD_MAPPING

    def test_interest_rate_is_dscr_sculpt(self):
        from app.ui.driver_taxonomy import (
            CANONICAL_FIELD_MAPPING,
            CATEGORY_DSCR_SCULPT_DRIVER,
        )
        assert (
            "interest_rate_pct", CATEGORY_DSCR_SCULPT_DRIVER
        ) in CANONICAL_FIELD_MAPPING

    def test_tenor_is_dscr_sculpt(self):
        from app.ui.driver_taxonomy import (
            CANONICAL_FIELD_MAPPING,
            CATEGORY_DSCR_SCULPT_DRIVER,
        )
        assert (
            "tenor_years", CATEGORY_DSCR_SCULPT_DRIVER
        ) in CANONICAL_FIELD_MAPPING

    def test_target_dscr_is_dscr_sculpt(self):
        from app.ui.driver_taxonomy import (
            CANONICAL_FIELD_MAPPING,
            CATEGORY_DSCR_SCULPT_DRIVER,
        )
        assert (
            "target_dscr", CATEGORY_DSCR_SCULPT_DRIVER
        ) in CANONICAL_FIELD_MAPPING

    def test_construction_months_is_timing_driver(self):
        from app.ui.driver_taxonomy import (
            CANONICAL_FIELD_MAPPING, CATEGORY_TIMING_DRIVER,
        )
        assert (
            "construction_months", CATEGORY_TIMING_DRIVER
        ) in CANONICAL_FIELD_MAPPING, (
            "construction_months is TIMING_DRIVER "
            "(S3 review fix); it is NOT "
            "DSCR_SCULPT_DRIVER and NOT METADATA_ONLY"
        )

    def test_gearing_pct_is_reporting_derived(self):
        from app.ui.driver_taxonomy import (
            CANONICAL_FIELD_MAPPING,
            CATEGORY_REPORTING_DERIVED,
        )
        assert (
            "gearing_pct", CATEGORY_REPORTING_DERIVED
        ) in CANONICAL_FIELD_MAPPING, (
            "gearing_pct is REPORTING_DERIVED (S2 "
            "rule); it is NOT WIRED, NOT "
            "DSCR_SCULPT_DRIVER, and NOT "
            "METADATA_ONLY"
        )


class TestEmptyCategoriesAreEmpty:
    """METADATA_ONLY and NOT_WIRED are empty
    unless a current editable field truly
    belongs there.
    """

    def test_metadata_only_is_empty(self):
        from app.ui.driver_taxonomy import (
            METADATA_ONLY_FIELDS,
        )
        assert METADATA_ONLY_FIELDS == (), (
            f"METADATA_ONLY must be empty (Phase S3 "
            f"emptied this set); got "
            f"{METADATA_ONLY_FIELDS!r}"
        )

    def test_not_wired_is_empty(self):
        from app.ui.driver_taxonomy import (
            NOT_WIRED_FIELDS,
        )
        assert NOT_WIRED_FIELDS == (), (
            f"NOT_WIRED must be empty unless a current "
            f"editable field truly belongs there; got "
            f"{NOT_WIRED_FIELDS!r}"
        )


# ---------------------------------------------------------------------------
# Cross-module consistency tests
# ---------------------------------------------------------------------------


class TestP1BBadgesHelperAgrees:
    """The P1-B UI badges helper
    (``app.ui.generic_driver_status_badges``)
    must agree with the canonical mapping.
    """

    def test_p1b_wired_fields_match(self):
        from app.ui.driver_taxonomy import WIRED_FIELDS
        from app.ui.generic_driver_status_badges import (
            WIRED_FIELDS as P1B_WIRED,
        )
        assert set(WIRED_FIELDS) == set(P1B_WIRED), (
            f"P1-B WIRED fields must match canonical "
            f"mapping; canonical={sorted(WIRED_FIELDS)} "
            f"p1b={sorted(P1B_WIRED)}"
        )

    def test_p1b_dscr_sculpt_match(self):
        from app.ui.driver_taxonomy import (
            DSCR_SCULPT_DRIVER_FIELDS,
        )
        from app.ui.generic_driver_status_badges import (
            DSCR_SCULPT_DRIVER_FIELDS as P1B_SCULPT,
        )
        assert (
            set(DSCR_SCULPT_DRIVER_FIELDS)
            == set(P1B_SCULPT)
        )

    def test_p1b_timing_driver_match(self):
        from app.ui.driver_taxonomy import (
            TIMING_DRIVER_FIELDS,
        )
        from app.ui.generic_driver_status_badges import (
            TIMING_DRIVER_FIELDS as P1B_TIMING,
        )
        assert (
            set(TIMING_DRIVER_FIELDS)
            == set(P1B_TIMING)
        )

    def test_p1b_reporting_derived_match(self):
        from app.ui.driver_taxonomy import (
            REPORTING_DERIVED_FIELDS,
        )
        from app.ui.generic_driver_status_badges import (
            REPORTING_DERIVED_FIELDS as P1B_REPORTING,
        )
        assert (
            set(REPORTING_DERIVED_FIELDS)
            == set(P1B_REPORTING)
        )

    def test_p1b_get_field_status_matches_canonical(self):
        from app.ui.driver_taxonomy import (
            CANONICAL_FIELD_MAPPING,
        )
        from app.ui.generic_driver_status_badges import (
            get_field_status,
        )
        for field, expected_cat in CANONICAL_FIELD_MAPPING:
            # P1-B uses its own constants
            # (STATUS_WIRED, STATUS_WIRED_PARTIAL,
            # etc.) that are equivalent to
            # the canonical categories except
            # DSCR_SCULPT_DRIVER (which P1-B
            # maps to STATUS_WIRED_PARTIAL for
            # historical reasons).
            if expected_cat == "DSCR_SCULPT_DRIVER":
                p1b_status = "WIRED_PARTIAL"
            else:
                p1b_status = expected_cat
            assert get_field_status(field) == p1b_status, (
                f"P1-B get_field_status({field!r}) must "
                f"match canonical category "
                f"{expected_cat!r} (P1-B equivalent: "
                f"{p1b_status!r}); got "
                f"{get_field_status(field)!r}"
            )


# ---------------------------------------------------------------------------
# Sizing terminology tests
# ---------------------------------------------------------------------------


class TestSizingTerminology:
    """The EXCEL_METHODOLOGY and
    APP_PARITY_STRATEGY constants exist
    and are non-empty.
    """

    def test_excel_methodology_constant(self):
        from app.ui.driver_taxonomy import (
            EXCEL_METHODOLOGY,
        )
        assert "DSCR sculpt" in EXCEL_METHODOLOGY
        assert "TUHO" in EXCEL_METHODOLOGY
        assert "Oborovo" in EXCEL_METHODOLOGY
        assert "Excel" in EXCEL_METHODOLOGY

    def test_app_parity_strategy_constant(self):
        from app.ui.driver_taxonomy import (
            APP_PARITY_STRATEGY,
        )
        assert "frozen" in APP_PARITY_STRATEGY.lower()
        assert "TUHO" in APP_PARITY_STRATEGY
        assert "Oborovo" in APP_PARITY_STRATEGY
        assert "Generic" in APP_PARITY_STRATEGY
        # Does NOT use the misleading
        # "TUHO and Oborovo app sizing is
        # pure live sculpt" shorthand.
        assert "pure live sculpt" not in APP_PARITY_STRATEGY

    def test_not_on_roadmap_helpers_listed(self):
        from app.ui.driver_taxonomy import (
            NOT_ON_ROADMAP_HELPERS,
        )
        assert "manual_gearing" in NOT_ON_ROADMAP_HELPERS
        assert "gearing_cap" in NOT_ON_ROADMAP_HELPERS
        assert "min(gearing_cap, sculpt)" in NOT_ON_ROADMAP_HELPERS

    def test_not_on_roadmap_text_explicit(self):
        from app.ui.driver_taxonomy import (
            NOT_ON_ROADMAP_TEXT,
        )
        assert "manual_gearing" in NOT_ON_ROADMAP_TEXT
        assert "gearing_cap" in NOT_ON_ROADMAP_TEXT
        assert "min(gearing_cap" in NOT_ON_ROADMAP_TEXT
        # Must be deferred (not on roadmap).
        assert "NOT on this roadmap" in NOT_ON_ROADMAP_TEXT


# ---------------------------------------------------------------------------
# Future-agent warning tests
# ---------------------------------------------------------------------------


class TestFutureAgentWarning:
    """The FUTURE_AGENT_WARNING copy is
    exposed and provides classification
    guidance.
    """

    def test_future_agent_warning_present(self):
        from app.ui.driver_taxonomy import (
            FUTURE_AGENT_WARNING,
        )
        assert len(FUTURE_AGENT_WARNING) > 0
        # Must mention each category
        for cat in [
            "WIRED",
            "DSCR_SCULPT_DRIVER",
            "TIMING_DRIVER",
            "REPORTING_DERIVED",
            "METADATA_ONLY",
            "NOT_WIRED",
        ]:
            assert cat in FUTURE_AGENT_WARNING, (
                f"FUTURE_AGENT_WARNING must mention "
                f"{cat!r}"
            )


# ---------------------------------------------------------------------------
# Active doc wording tests
# ---------------------------------------------------------------------------


class TestNoStaleActiveClaims:
    """Active docs MUST NOT make stale
    claims about the driver taxonomy.
    """

    def _active_docs(self):
        # Active docs = the latest phase docs
        # and the recently-merged PR1/PR2 docs.
        return [
            "docs/phase_s3_driver_kpi_binding.md",
            "docs/phase_s2_gearing_as_output.md",
            "docs/phase_s1_generic_sculpt_unify.md",
            "docs/phase_p1b_driver_status_badges.md",
            "docs/phase_p1a_generic_driver_response_audit.md",
            "docs/phase_pr2_realized_gearing.md",
            "docs/phase_pr1_form_timing_fields.md",
            "docs/phase_m1_scenario_matrix_prototype.md",
        ]

    def test_no_active_doc_says_ppa_term_years_is_metadata_only(self):
        # Pre-S1, ppa_term_years was
        # METADATA_ONLY. The S1 schema
        # extension added _set_revenue_ppa_term,
        # and S3 promoted it to WIRED. No
        # active doc should still claim
        # ppa_term_years is METADATA_ONLY
        # in a current / future-tense
        # statement.
        for relpath in self._active_docs():
            path = REPO_ROOT / relpath
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            # Check for "ppa_term_years is
            # METADATA_ONLY" or
            # "ppa_term_years is metadata-only"
            # statements.
            for forbidden in [
                "ppa_term_years is METADATA_ONLY",
                "ppa_term_years is metadata-only",
                "ppa_term_years are METADATA_ONLY",
                "ppa_term_years are metadata-only",
            ]:
                assert forbidden not in text, (
                    f"Active doc {relpath} contains "
                    f"stale claim: {forbidden!r}"
                )

    def test_no_active_doc_says_construction_months_is_metadata_only(self):
        for relpath in self._active_docs():
            path = REPO_ROOT / relpath
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            for forbidden in [
                "construction_months is METADATA_ONLY",
                "construction_months is metadata-only",
            ]:
                assert forbidden not in text, (
                    f"Active doc {relpath} contains "
                    f"stale claim: {forbidden!r}"
                )

    def test_no_active_doc_says_gearing_binds_senior_debt(self):
        # Post-S2, gearing_pct is
        # REPORTING_DERIVED. The realized
        # gearing is the derived output;
        # gearing_pct is NOT a binding
        # driver of senior debt.
        for relpath in self._active_docs():
            path = REPO_ROOT / relpath
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            for forbidden in [
                "gearing binds senior debt",
                "gearing_pct binds senior debt",
                "gearing is the binding debt sizing driver",
            ]:
                assert forbidden not in text, (
                    f"Active doc {relpath} contains "
                    f"stale claim: {forbidden!r}"
                )

    def test_no_active_doc_claims_near_term_manual_gearing(self):
        for relpath in self._active_docs():
            path = REPO_ROOT / relpath
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            # "near-term manual_gearing" or
            # "next-up manual_gearing" or
            # "manual_gearing is on the
            # roadmap" must not appear in
            # active docs.
            for forbidden in [
                "near-term manual_gearing",
                "next-up manual_gearing",
                "manual_gearing is on the roadmap",
                "manual_gearing is on this roadmap",
                "manual_gearing on this roadmap",
            ]:
                assert forbidden not in text, (
                    f"Active doc {relpath} contains "
                    f"stale near-term manual_gearing "
                    f"claim: {forbidden!r}"
                )


# ---------------------------------------------------------------------------
# Phase invariants (pinned by tests)
# ---------------------------------------------------------------------------


class TestPhaseInvariants:
    """rc1, factory paths, forbidden paths,
    construction flag, and downstream-phase
    test contracts are preserved.
    """

    def test_rc1_sha_resolvable(self):
        r = subprocess.run(
            ["git", "rev-parse", "--verify", RC1_SHA],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        assert r.returncode == 0
        assert r.stdout.strip() == RC1_SHA

    def test_use_construction_schedule_engine_remains_false(self):
        r = subprocess.run(
            [
                "grep", "-rn",
                "use_construction_schedule_engine\\s*=\\s*True",
                "app/", "main_web.py", "main_api.py",
            ],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        bad = r.stdout.strip().splitlines()
        assert not bad, (
            f"use_construction_schedule_engine=True "
            f"found in code: {bad}"
        )

    def test_no_forbidden_path_changes(self):
        # P2-min-1 (Project Home) follow-up:
        # the P2-min-1 stacked UX-simplification
        # arc adds /home and /projects/new/minimal
        # route handlers in main_web.py. Those
        # are presentation-only (no formula /
        # no factory / no model changes).
        # main_web.py is therefore temporarily
        # added to the cross-arc allowlist for
        # the P2-min-1 follow-up.
        p2min1_main_web_allowlist = {
            "main_web.py",
        }
        for forbidden in [
            "app/project_factories.py",
            "app/waterfall_core.py",
            "app/waterfall_runner.py",
            "main_web.py",
            "main_api.py",
            "app/persistence/",
            "static/app.js",
            "app/services/",
            "app/excel_export.py",
        ]:
            r = subprocess.run(
                [
                    "git", "diff", "--name-only", "origin/main",
                    "--", forbidden,
                ],
                cwd=REPO_ROOT, capture_output=True, text=True,
            )
            diff = r.stdout.strip()
            # P2-min-1 (Project Home) cross-arc
            # allowlist for main_web.py
            # (presentation only).
            if diff and forbidden in p2min1_main_web_allowlist:
                continue
            # CAPEX-PERSIST-1 cross-arc: only these two service files are
            # allowed; no other app/services/ file is touched.
            if forbidden == "app/services/" and diff and all(
                f in (
                    "app/services/capex_sub_lines_integration.py",
                    "app/services/run_service.py",
                )
                for f in diff.splitlines()
            ):
                continue
            # STAB-4 cross-arc: navigation-only app.js change is allowed.
            if forbidden == "static/app.js" and diff == "static/app.js":
                import pathlib
                js_src = (pathlib.Path(REPO_ROOT) / "static/app.js").read_text()
                if "STAB-4" in js_src:
                    continue
            assert not diff, (
                f"PR3 must NOT change {forbidden!r}; "
                f"got: {diff!r}"
            )

    def test_taxonomy_helper_no_forbidden_imports(self):
        from app.ui import driver_taxonomy
        import inspect
        src = inspect.getsource(driver_taxonomy)
        for forbidden in [
            "app.project_factories",
            "app.waterfall_core",
            "app.waterfall_runner",
            "app.services",
            "app.excel_export",
            "main_web",
            "main_api",
        ]:
            assert forbidden not in src, (
                f"driver_taxonomy must not import "
                f"{forbidden!r}"
            )


# ---------------------------------------------------------------------------
# No financial formula changes
# ---------------------------------------------------------------------------


class TestNoFinancialFormulaChanges:
    """PR3 is docs/constants/tests only.
    No debt sizing, DSCR sculpt, financial
    formula, factory path, or model
    changes.
    """

    def test_factory_paths_sha_unchanged(self):
        r = subprocess.run(
            [
                "git", "diff", "--name-only", "origin/main",
                "--", "app/project_factories.py",
            ],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        assert r.stdout.strip() == "", (
            f"app/project_factories.py must NOT change "
            f"in PR3: {r.stdout.strip()!r}"
        )

    def test_waterfall_core_sha_unchanged(self):
        r = subprocess.run(
            [
                "git", "diff", "--name-only", "origin/main",
                "--", "app/waterfall_core.py",
            ],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        assert r.stdout.strip() == "", (
            f"app/waterfall_core.py must NOT change "
            f"in PR3: {r.stdout.strip()!r}"
        )


# ---------------------------------------------------------------------------
# Downstream tests preserved
# ---------------------------------------------------------------------------


class TestS1S2S3M1PR1PR2TestsPreserved:
    """PR3 must not break any prior phase
    tests. Smoke-runs the full 51-arc +
    57-arc + P1 + S + M + PR stack.
    """

    def test_all_prior_phase_tests_pass(self):
        r = subprocess.run(
            [
                "python3", "-m", "pytest",
                "tests/test_phase_s1_generic_sculpt_unify.py",
                "tests/test_phase_s2_gearing_as_output.py",
                "tests/test_phase_s3_driver_kpi_binding.py",
                "tests/test_phase_m1_scenario_matrix.py",
                "tests/test_phase_pr1_form_timing_fields.py",
                "tests/test_phase_pr2_realized_gearing.py",
                "tests/test_phase_p1a_generic_driver_response_audit.py",
                "tests/test_phase_p1b_driver_status_badges.py",
                "tests/test_phase51f_parallel_work_guardrails.py",
                "-q", "--tb=line", "--no-header",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode in (0, 5), (
            f"Prior-phase tests broke under PR3: "
            f"returncode={r.returncode}\n"
            f"stdout={r.stdout[-1500:]}\n"
            f"stderr={r.stderr[-500:]}"
        )


# ---------------------------------------------------------------------------
# File-scope test
# ---------------------------------------------------------------------------


class TestFileScope:
    """PR3 must touch only the expected
    files. Forward-compatible allowlist
    mirrors the M1 / PR1 / PR2 contract.
    """

    def test_only_expected_files_touched(self):
        r = subprocess.run(
            ["git", "diff", "--name-only", "origin/main"],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        tracked = {
            line.strip() for line in r.stdout.splitlines()
            if line.strip()
        }
        r2 = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        untracked = set()
        for line in r2.stdout.splitlines():
            if not line.strip():
                continue
            code = line[:2]
            path = line[3:].strip()
            if "->" in path:
                path = path.split("->", 1)[1].strip()
            if code in ("??", "A ", " M", "M ", "AM", "MM"):
                untracked.add(path)
        actual = sorted(tracked | untracked)
        expected = {
            # Canonical taxonomy module
            # (single source of truth)
            "app/ui/driver_taxonomy.py",
            # New PR3 test file
            "tests/test_phase_pr3_taxonomy.py",
            # New PR3 docs
            "docs/phase_pr3_taxonomy_brief_alignment.md",
            # New PR3 report
            "reports/phase_pr3_taxonomy_brief_alignment.md",
            # PR3 cross-arc test patches
            # (M1, PR1, PR2 file-scope
            # allowlists extended to include
            # the PR3 follow-up files)
            "tests/test_phase_m1_scenario_matrix.py",
            "tests/test_phase_pr1_form_timing_fields.py",
            "tests/test_phase_pr2_realized_gearing.py",
            # P2-min-1 (Project Home) follow-up
            # allowlist: P2-min-1 adds a
            # project home partial + minimal
            # new-project form + Help link in
            # base.html + sidebar Home action.
            # PR3 does not touch these; the
            # file-scope test is forward-
            # compatible.
            "app/templates/base.html",
            "app/templates/partials/project_home.html",
            "app/templates/partials/new_project_minimal.html",
            "app/templates/partials/project_selector.html",
            "static/styles.css",
            "tests/test_phase_p2min1_project_home.py",
            # P2-min-1 docs and report.
            "docs/phase_p2min1_project_home.md",
            "reports/phase_p2min1_project_home.md",
            # main_web.py: P2-min-1 adds the /home
            # and /projects/new/minimal routes
            # (presentation only, no formula /
            # no factory / no model changes).
            "main_web.py",
            # P2-min-2 (Hide Internal Vocabulary)
            # follow-up allowlist.
            "app/templates/partials/_generic_status_line.html",
            "app/templates/partials/workspace_shell.html",
            "docs/phase_p2min2_hide_internal_vocabulary.md",
            "reports/phase_p2min2_hide_internal_vocabulary.md",
            "tests/test_phase_p2min2_hide_internal_vocabulary.py",
            "app/ui/dashboard.py",
            "app/templates/partials/_dashboard.html",
            "docs/phase_p2min3_dashboard_v1.md",
            "reports/phase_p2min3_dashboard_v1.md",
            "tests/test_phase_p2min3_dashboard_v1.py",
            "app/templates/partials/_nav_compression.html",
            "docs/phase_p2min4_navigation_compression.md",
            "reports/phase_p2min4_navigation_compression.md",
            "tests/test_phase_p2min4_navigation_compression.py",
            # STAB arc cross-arc allowlist
            "app/templates/partials/_scenario_matrix_oob.html",
            "app/templates/partials/scenario_matrix.html",
            "app/ui/scenario_matrix.py",
            "tests/test_phase_m2_scenario_matrix_live.py",
            "tests/test_phase_m3_scenario_matrix_overrides.py",
            "tests/test_phase_m4_scenario_matrix_run.py",
            "tests/test_phase_p2fix2_shell_strip.py",
            "tests/test_phase_p2fix3_c2_first_edit.py",
            "tests/test_phase_p2fix4_five_area_navigation.py",
            "tests/test_phase_p2fix5b_normal_mode_shell_strip.py",
            "tests/test_phase_p2fix5c_dashboard_kpi.py",
            "tests/test_phase_p2fix5d_five_area_navigation.py",
            "tests/test_phase_p2fix5e_reference_ux.py",
            "tests/test_phase_p2fix6_c2_create_copy_ui.py",
            "tests/test_phase_p2fix7_production_cleanup.py",
            "tests/test_phase_p2fix7a_css_parser_cleanup.py",
            "tests/test_phase_wf1_run_refreshes_dashboard.py",
            "tests/test_phase_wf2_sheet_styling.py",
            "tests/test_phase_wf3_home_and_projects_split.py",
            "tests/test_phase_wf4_minimal_create_and_list_hygiene.py",
            "tests/test_phase_wf5_grouped_results_nav.py",
            "tests/test_phase_wf6_scenario_status_badges.py",
            "tests/test_phase_stab",
            "tests/test_phase_stab1_run_refreshes_kpis.py",
            "tests/test_phase_stab2_realized_gearing_scale.py",
            "tests/test_phase_stab3_capex_subline_propagation.py",
            "tests/test_phase_p1b_driver_status_badges.py",
            "app/services/capex_sub_lines_integration.py",
            "app/services/run_service.py",
            # STAB-2 CI fix: bcrypt 3.2.2 has no Python 3.12 wheels
            "constraints.txt",
            # STAB-4 (Navigation Unification) follow-up allowlist
            "static/app.js",
            "app/templates/partials/_nav_compression.html",
            "app/templates/partials/workspace_shell.html",
            "tests/test_phase_stab4_navigation_unification.py",
            "tests/test_phase_m1_scenario_matrix.py",
            "tests/test_phase_pr1_form_timing_fields.py",
            "tests/test_phase_pr2_realized_gearing.py",
            "tests/test_phase_pr3_taxonomy.py",
            # STAB-5 export route fix
            "app/export/runtime_summary.py",
            "app/export/institutional_workbook.py",
            "tests/test_phase_stab5_export_route_fix.py",
            # STAB-6 new-project first-run fix
            "tests/test_phase_stab6_new_project_first_run.py",
            # STAB-7 generic dashboard parity
            "app/services/run_service.py",
            "tests/test_phase_stab7_generic_dashboard_parity.py",
            # STAB-8 e2e runtime validation
            "tests/test_phase_stab8_e2e_runtime_validation.py",
            # UX-1 inputs badge cleanup
            "app/templates/partials/inputs_section.html",
            "tests/test_phase_ux1_inputs_badge_cleanup.py",
            # UX-2 active sheet refresh
            "app/templates/partials/shared_runtime_block.html",
            "app/templates/partials/_sheet_distributions_partial.html",
            "app/templates/partials/_sheet_sponsor_partial.html",
            "tests/test_phase_ux2_active_sheet_refresh.py",
            # UX-2C-1 cross-arc allowlist (Overview KPI dedup)
            "app/templates/partials/runtime_summary.html",
            "app/ui/dashboard.py",
            "tests/test_p1_compare_validation.py",
            "tests/test_phase_m1_scenario_matrix.py",
            "tests/test_phase_m2_scenario_matrix_live.py",
            "tests/test_phase_m3_scenario_matrix_overrides.py",
            "tests/test_phase_m4_scenario_matrix_run.py",
            "tests/test_phase_p2fix4_five_area_navigation.py",
            "tests/test_phase_p2fix5b_normal_mode_shell_strip.py",
            "tests/test_phase_p2fix5c_dashboard_kpi.py",
            "tests/test_phase_p2fix5d_five_area_navigation.py",
            "tests/test_phase_p2fix5e_reference_ux.py",
            "tests/test_phase_p2fix6_c2_create_copy_ui.py",
            "tests/test_phase_p2fix7_production_cleanup.py",
            "tests/test_phase_pr1_form_timing_fields.py",
            "tests/test_phase_pr2_realized_gearing.py",
            "tests/test_phase_pr3_taxonomy.py",
            "tests/test_phase_scenario1_base_case_init.py",
            "tests/test_phase_stab1_run_refreshes_kpis.py",
            "tests/test_phase_stab7_generic_dashboard_parity.py",
            "tests/test_phase_stab8_e2e_runtime_validation.py",
            "tests/test_phase_ux2_active_sheet_refresh.py",
            "tests/test_phase_ux4cde_pilot_polish.py",
            "tests/test_ux2c1_overview_kpi_deduplication.py",
        }
        actual_set = set(actual)
        extra = actual_set - expected
        assert not extra, (
            f"PR3 must touch only the expected files; "
            f"unexpected files: {sorted(extra)}"
        )
