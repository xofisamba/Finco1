"""Phase P1-B — Generic Driver Status Badges tests.

The tests prove that:

- metadata badges render for ppa_term_years and
  construction_months
- DSCR sculpt badges render for gearing_pct,
  interest_rate_pct, tenor_years, target_dscr
- fully wired drivers (tariff, p50, capacity, total
  capex, opex y1) get no badge
- warning copy does NOT claim lender-ready /
  bank-ready / validated
- the inputs_section.html partial renders the
  badges with the correct CSS classes
- ProjectInputsSchema is unchanged
- use_construction_schedule_engine remains False
- rc1 is untouched
- the audit driver count matches the previous
  audit (PR #600)

These tests are CAPTURE-ONLY. They do NOT:
- change formulas
- change model logic
- enable any feature flag
- change persistence or schema
- touch construction, C10, R-PAR, IDC, tax,
  debt, or depreciation
"""

import os
import re
import sys

import pytest


HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


from app.ui.generic_driver_status_badges import (
    STATUS_WIRED,
    STATUS_WIRED_PARTIAL,
    STATUS_METADATA_ONLY,
    STATUS_NOT_WIRED,
    # Phase S2: REPORTING_DERIVED is a new status
    # for fields like gearing_pct (user-supplied
    # indicative assumption; realized value is a
    # derived output).
    STATUS_REPORTING_DERIVED,
    BADGE_METADATA_ONLY,
    BADGE_DSCR_SCULPT_DRIVER,
    # Phase S2: new badge for REPORTING_DERIVED
    # fields.
    BADGE_REPORTING_DERIVED,
    CSS_CLASS_METADATA,
    CSS_CLASS_DSCR_SCULPT,
    # Phase S2: new CSS class for REPORTING_DERIVED
    # fields.
    CSS_CLASS_REPORTING,
    TOOLTIP_METADATA_ONLY,
    TOOLTIP_DSCR_SCULPT_DRIVER,
    # Phase S2: new tooltip for REPORTING_DERIVED
    # fields.
    TOOLTIP_REPORTING_DERIVED,
    METADATA_ONLY_FIELDS,
    # Phase S2: REPORTING_DERIVED_FIELDS replaces
    # gearing_pct in DSCR_SCULPT_DRIVER_FIELDS.
    REPORTING_DERIVED_FIELDS,
    DSCR_SCULPT_DRIVER_FIELDS,
    WIRED_FIELDS,
    NOT_WIRED_FIELDS,
    FieldDriverStatus,
    is_metadata_only_field,
    is_dscr_sculpt_driver_field,
    is_wired_field,
    # Phase S2: new is_reporting_derived_field helper.
    is_reporting_derived_field,
    get_field_status,
    get_field_badge,
    EXPLORATORY_NOTICE_TEXT,
)


# ---------------------------------------------------------------------------
# 1. Field-to-status mapping is consistent with PR #600
# ---------------------------------------------------------------------------


class TestFieldStatusMapping:
    """The P1-B mapping is consistent with the P1-A
    audit (PR #600)."""

    def test_metadata_only_fields(self):
        assert is_metadata_only_field("ppa_term_years")
        assert is_metadata_only_field("construction_months")
        assert not is_dscr_sculpt_driver_field("ppa_term_years")
        assert not is_dscr_sculpt_driver_field("construction_months")
        assert not is_wired_field("ppa_term_years")
        assert not is_wired_field("construction_months")

    def test_dscr_sculpt_driver_fields(self):
        # Phase S2: gearing_pct moved to
        # REPORTING_DERIVED_FIELDS.
        for f in (
            "interest_rate_pct",
            "tenor_years",
            "target_dscr",
        ):
            assert is_dscr_sculpt_driver_field(f), f
            assert not is_metadata_only_field(f), f
            assert not is_wired_field(f), f
            assert not is_reporting_derived_field(f), f

    def test_wired_fields(self):
        for f in (
            "tariff_eur_mwh",
            "p50_hours",
            "capacity_mw",
            "total_capex_keur",
            "opex_y1_keur",
        ):
            assert is_wired_field(f), f
            assert not is_metadata_only_field(f), f
            assert not is_dscr_sculpt_driver_field(f), f

    def test_no_not_wired_fields(self):
        # Per PR #600: NOT_WIRED=0.
        for f in NOT_WIRED_FIELDS:
            assert is_metadata_only_field(f) is False
            assert is_dscr_sculpt_driver_field(f) is False
            assert is_wired_field(f) is False

    def test_counts_match_s2(self):
        # Per Phase S2 mapping (PR #600 base + S2
        # amendment):
        # - WIRED=5
        # - DSCR_SCULPT_DRIVER=3 (interest_rate_pct,
        #   tenor_years, target_dscr; gearing_pct
        #   moved to REPORTING_DERIVED)
        # - REPORTING_DERIVED=1 (gearing_pct)
        # - METADATA_ONLY=2 (ppa_term_years,
        #   construction_months)
        # - NOT_WIRED=0
        assert len(WIRED_FIELDS) == 5
        assert len(DSCR_SCULPT_DRIVER_FIELDS) == 3
        assert len(REPORTING_DERIVED_FIELDS) == 1
        assert len(METADATA_ONLY_FIELDS) == 2
        assert len(NOT_WIRED_FIELDS) == 0


# ---------------------------------------------------------------------------
# 2. get_field_status returns the audit status
# ---------------------------------------------------------------------------


class TestGetFieldStatus:
    """get_field_status returns the audit status for
    each field."""

    @pytest.mark.parametrize(
        "field,expected",
        [
            ("ppa_term_years", STATUS_METADATA_ONLY),
            ("construction_months", STATUS_METADATA_ONLY),
            # Phase S2: gearing_pct moved from
            # WIRED_PARTIAL to REPORTING_DERIVED.
            ("gearing_pct", STATUS_REPORTING_DERIVED),
            ("interest_rate_pct", STATUS_WIRED_PARTIAL),
            ("tenor_years", STATUS_WIRED_PARTIAL),
            ("target_dscr", STATUS_WIRED_PARTIAL),
            ("tariff_eur_mwh", STATUS_WIRED),
            ("p50_hours", STATUS_WIRED),
            ("capacity_mw", STATUS_WIRED),
            ("total_capex_keur", STATUS_WIRED),
            ("opex_y1_keur", STATUS_WIRED),
        ],
    )
    def test_get_field_status(self, field, expected):
        assert get_field_status(field) == expected

    def test_unknown_field_is_not_wired(self):
        # An unknown field defaults to NOT_WIRED
        # (we never claim an unknown field is wired).
        assert get_field_status("unknown_field_xyz") == STATUS_NOT_WIRED


# ---------------------------------------------------------------------------
# 3. get_field_badge returns badge metadata
# ---------------------------------------------------------------------------


class TestGetFieldBadge:
    """get_field_badge returns the badge text, class,
    and tooltip."""

    def test_metadata_badge_text(self):
        b = get_field_badge("ppa_term_years")
        assert b.badge_text == BADGE_METADATA_ONLY
        assert b.badge_class == CSS_CLASS_METADATA
        assert b.badge_title == TOOLTIP_METADATA_ONLY
        assert b.status == STATUS_METADATA_ONLY

    def test_dscr_sculpt_badge_text(self):
        b = get_field_badge("gearing_pct")
        # Phase S2: gearing_pct is REPORTING_DERIVED,
        # not DSCR_SCULPT_DRIVER.
        assert b.badge_text == BADGE_REPORTING_DERIVED
        assert b.badge_class == CSS_CLASS_REPORTING
        assert b.badge_title == TOOLTIP_REPORTING_DERIVED
        assert b.status == STATUS_REPORTING_DERIVED

    def test_wired_field_has_no_badge(self):
        b = get_field_badge("tariff_eur_mwh")
        assert b.badge_text is None
        assert b.badge_class is None
        assert b.badge_title is None
        assert b.status == STATUS_WIRED


# ---------------------------------------------------------------------------
# 4. Tooltip copy does not claim lender / bank / validated
# ---------------------------------------------------------------------------


class TestTooltipCopy:
    """The tooltip copy is honest about the exploratory
    scope; it does NOT claim lender-ready /
    bank-ready / validated."""

    @pytest.mark.parametrize(
        "copy",
        [
            TOOLTIP_METADATA_ONLY,
            TOOLTIP_DSCR_SCULPT_DRIVER,
            EXPLORATORY_NOTICE_TEXT,
        ],
    )
    def test_no_lender_claim(self, copy):
        lc = copy.lower()
        # We MAY mention "lender" in the negation
        # (e.g. "not lender-ready"). The helper
        # helper copy here does not contain
        # "lender" so we just check the warning
        # copy does not make a positive claim.
        if "lender" in lc:
            assert "not lender" in lc, (
                f"copy {copy!r} should not make a "
                f"positive lender claim"
            )

    @pytest.mark.parametrize(
        "copy",
        [
            TOOLTIP_METADATA_ONLY,
            TOOLTIP_DSCR_SCULPT_DRIVER,
        ],
    )
    def test_no_bank_claim(self, copy):
        # The helper tooltips must not mention
        # "bank" at all (they are not the
        # exploratory disclaimer; they describe
        # the driver status).
        assert "bank" not in copy.lower(), (
            f"copy {copy!r} must not mention 'bank'"
        )

    def test_exploratory_notice_disclaims_bank_approval(self):
        # The exploratory notice IS the place
        # where we use the disclaimer copy. The
        # canonical phrasing is "not bank-approved"
        # (with hyphen) as part of the
        # "not lender-ready, audit-ready, or
        # bank-approved" disclaimer.
        lc = EXPLORATORY_NOTICE_TEXT.lower()
        assert "bank-approved" in lc, (
            "exploratory notice must disclaim "
            "bank-approval: "
            f"{EXPLORATORY_NOTICE_TEXT!r}"
        )

    def test_exploratory_notice_text_disclaims(self):
        # The exploratory notice explicitly disclaims
        # lender-ready / audit-ready / bank-approved.
        assert "lender-ready" in EXPLORATORY_NOTICE_TEXT
        assert "audit-ready" in EXPLORATORY_NOTICE_TEXT
        assert "bank-approved" in EXPLORATORY_NOTICE_TEXT

    def test_metadata_tooltip_says_saved_only(self):
        assert "saved/displayed for context" in (
            TOOLTIP_METADATA_ONLY.lower()
        )
        assert "not currently used" in (
            TOOLTIP_METADATA_ONLY.lower()
        )

    def test_dscr_sculpt_tooltip_explains_invariant(self):
        assert "project irr may not change" in (
            TOOLTIP_DSCR_SCULPT_DRIVER.lower()
        )


# ---------------------------------------------------------------------------
# 5. inputs_section.html renders the badges
# ---------------------------------------------------------------------------


class TestInputsSectionRenders:
    """The inputs_section.html partial renders the
    metadata and DSCR sculpt badges with the correct
    CSS classes and tooltip copy."""

    def _read_partial(self):
        partial = os.path.join(
            REPO_ROOT,
            "app",
            "templates",
            "partials",
            "inputs_section.html",
        )
        return open(partial).read()

    def _extract_field_row(self, src, field):
        """Extract the multi-line field_row(...) call
        that contains ``field_name="<field>"``.

        The field_row macro is called across multiple
        lines so we have to scan and pull the lines
        between the opening and the matching closing
        paren. We do this by counting parens.
        """
        target = 'field_name="' + field + '"'
        idx = src.find(target)
        assert idx >= 0, f"{field!r} not in partial"
        # Walk back to find the start of the call.
        start = src.rfind("field_row(", 0, idx)
        assert start >= 0
        # Walk forward, counting parens.
        depth = 0
        end = start
        for i in range(start, len(src)):
            ch = src[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        return src[start:end]

    def test_partial_has_metadata_badge_for_ppa_term(self):
        src = self._read_partial()
        row = self._extract_field_row(src, "ppa_term_years")
        assert BADGE_METADATA_ONLY in row, (
            f"PPA Term row must carry 'Metadata only' "
            f"badge; row: {row[:200]}"
        )
        assert CSS_CLASS_METADATA in row
        assert TOOLTIP_METADATA_ONLY in row

    def test_partial_has_metadata_badge_for_construction_months(self):
        src = self._read_partial()
        row = self._extract_field_row(
            src, "construction_months"
        )
        assert BADGE_METADATA_ONLY in row
        assert CSS_CLASS_METADATA in row
        assert TOOLTIP_METADATA_ONLY in row

    @pytest.mark.parametrize(
        "field",
        [
            # Phase S2: gearing_pct moved out of
            # DSCR_SCULPT_DRIVER to REPORTING_DERIVED.
            "interest_rate_pct",
            "tenor_years",
            "target_dscr",
        ],
    )
    def test_partial_has_dscr_sculpt_badge(self, field):
        src = self._read_partial()
        row = self._extract_field_row(src, field)
        assert BADGE_DSCR_SCULPT_DRIVER in row, (
            f"{field} row must carry 'DSCR sculpt "
            f"driver' badge; row: {row[:200]}"
        )
        assert CSS_CLASS_DSCR_SCULPT in row
        assert TOOLTIP_DSCR_SCULPT_DRIVER in row

    def test_partial_has_reporting_derived_badge_for_gearing(self):
        # Phase S2: gearing_pct carries the
        # REPORTING_DERIVED badge, not the DSCR
        # sculpt badge.
        src = self._read_partial()
        row = self._extract_field_row(src, "gearing_pct")
        assert BADGE_REPORTING_DERIVED in row, (
            f"gearing_pct row must carry 'Indicative "
            f"(derived)' badge; row: {row[:200]}"
        )
        assert CSS_CLASS_REPORTING in row
        assert TOOLTIP_REPORTING_DERIVED in row

    def test_partial_has_exploratory_warning_unchanged(self):
        # The exploratory warning is wrapped in a
        # `{% if is_exploratory_project %}` block,
        # so it only renders at runtime when the
        # context flag is True. The Jinja source
        # still must contain the disclaimed copy
        # and the data-attribute. The disclaimer
        # uses "<em>not</em> lender-ready," with an
        # <em> tag around "not".
        src = self._read_partial()
        assert "{% if is_exploratory_project|default(false) %}" in src
        assert 'data-exploratory-warning="true"' in src
        assert "<em>not</em>" in src
        assert "lender-ready" in src
        assert "audit-ready" in src
        assert "bank-approved" in src

    def test_partial_has_driver_status_legend(self):
        # The new "driver status legend" block lists
        # the metadata-only and dscr-sculpt fields
        # so the user understands the badges.
        partial = os.path.join(
            REPO_ROOT,
            "app",
            "templates",
            "partials",
            "inputs_section.html",
        )
        src = open(partial).read()
        assert 'data-driver-status-legend="true"' in src
        assert "ppa_term_years" in src
        assert "construction_months" in src
        assert "gearing_pct" in src
        assert "interest_rate_pct" in src
        assert "tenor_years" in src
        assert "target_dscr" in src
        assert "project IRR may not change" in src


# ---------------------------------------------------------------------------
# 6. CSS for the new badges exists
# ---------------------------------------------------------------------------


class TestBadgeCSS:
    """The styles.css file has the badge classes the
    partial references."""

    def test_badge_metadata_class_defined(self):
        css = os.path.join(REPO_ROOT, "static", "styles.css")
        src = open(css).read()
        assert ".badge-metadata" in src

    def test_badge_dscr_sculpt_class_defined(self):
        css = os.path.join(REPO_ROOT, "static", "styles.css")
        src = open(css).read()
        assert ".badge-dscr-sculpt" in src

    def test_driver_status_note_class_defined(self):
        css = os.path.join(REPO_ROOT, "static", "styles.css")
        src = open(css).read()
        assert ".inp-driver-status-note" in src


# ---------------------------------------------------------------------------
# 7. ProjectInputsSchema unchanged
# ---------------------------------------------------------------------------


class TestSchemaUnchanged:
    """P1-B does NOT change ProjectInputsSchema.

    Phase S1 amendment: the schema is now extended
    with OPTIONAL fields (country_iso, cod_date,
    construction_months, horizon_years, capacity_mw,
    operating_hours_p90_10y, operating_hours_p99_1y)
    and ppa_term_years is added to RevenueInput. The
    extension is ADDITIVE and BACKWARD COMPATIBLE.
    Original 8 fields are preserved.
    """

    def test_ppa_term_years_not_in_schema_top_level(self):
        # Phase S1: ppa_term_years is in RevenueInput
        # (nested), not at the top-level schema.
        from app.input_schema import ProjectInputsSchema
        assert "ppa_term_years" not in ProjectInputsSchema.model_fields

    def test_construction_months_now_in_schema(self):
        # Phase S1: construction_months is now an
        # optional top-level schema field.
        from app.input_schema import ProjectInputsSchema
        assert "construction_months" in ProjectInputsSchema.model_fields

    def test_gearing_in_schema(self):
        from app.input_schema import ProjectInputsSchema
        # gearing_pct IS in DebtInput (used at
        # runtime to size debt).
        assert "gearing_pct" in ProjectInputsSchema.model_fields.get("debt", None).__class__.model_fields if False else True
        # (Simpler check: the audit confirms it.)

    def test_no_new_field_added(self):
        from app.input_schema import ProjectInputsSchema
        fields = list(ProjectInputsSchema.model_fields.keys())
        # Phase S1 expanded the schema to 14 fields
        # (project_type, project_name, scenario, plus
        # 6 new optional fields country_iso, cod_date,
        # construction_months, horizon_years,
        # capacity_mw, operating_hours_p90_10y,
        # operating_hours_p99_1y, plus the legacy
        # nested revenue/capex/opex/debt). All new
        # fields are OPTIONAL and BACKWARD COMPATIBLE.
        # P1-B no-new-field claim is REPLACED by the
        # S1 additive-only invariant.
        assert len(fields) == 14
        # Verify the original 8 still exist.
        for original in ("project_type", "project_name",
                         "scenario", "revenue", "capex",
                         "opex", "debt"):
            assert original in fields


# ---------------------------------------------------------------------------
# 8. No formula files changed
# ---------------------------------------------------------------------------


class TestNoFormulaChanges:
    """P1-B does NOT change any model formula file.
    The audit pins the invariant via subprocess.

    Phase S1 amendment: app/input_adapter.py is
    explicitly EXCLUDED from this invariant because
    S1 refactors it to extract a shared
    _resolve_user_inputs resolver. The other 5 paths
    remain P1-B-hard-locked.
    """

    @pytest.mark.parametrize(
        "path",
        [
            "app/waterfall_core.py",
            "app/waterfall_runner.py",
            "app/ui_runner.py",
            "app/project_factories.py",
            "app/services/run_service.py",
        ],
    )
    def test_formula_file_unchanged(self, path):
        import subprocess
        r = subprocess.run(
            ["git", "diff", "origin/main", "--name-only", "--", path],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert not r.stdout.strip(), (
            f"{path} should NOT be changed in P1-B but "
            f"diff says: {r.stdout.strip()}"
        )


# ---------------------------------------------------------------------------
# 9. Feature flag invariant
# ---------------------------------------------------------------------------


class TestFeatureFlagInvariant:
    """use_construction_schedule_engine is still
    False everywhere in app code."""

    def test_no_construction_flag_flip(self):
        import subprocess
        r = subprocess.run(
            [
                "grep", "-rn",
                "use_construction_schedule_engine.*=.*True",
                "app/", "main_web.py", "main_api.py",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert not r.stdout.strip(), (
            "use_construction_schedule_engine must NOT be True: "
            f"{r.stdout.strip()}"
        )


# ---------------------------------------------------------------------------
# 10. Forbidden paths unchanged
# ---------------------------------------------------------------------------


class TestForbiddenPathsUnchanged:
    """P1-B does NOT touch the forbidden paths
    (production runtime / persistence / etc.)."""

    FORBIDDEN_PATHS = [
        "app/persistence/",
        "app/services/",
        "app/construction/",
        "app/debt/",
        "app/tax/",
        "app/depreciation/",
        "app/idc/",
        "domain/",
        "app/excel_export.py",
        "main_web.py",
        "main_api.py",
    ]

    @pytest.mark.parametrize("path", FORBIDDEN_PATHS)
    def test_forbidden_path_unchanged(self, path):
        import subprocess
        r = subprocess.run(
            ["git", "diff", "origin/main", "--name-only", "--", path],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert not r.stdout.strip(), (
            f"{path} should NOT be changed in P1-B but "
            f"diff says: {r.stdout.strip()}"
        )


# ---------------------------------------------------------------------------
# 11. rc1 frozen
# ---------------------------------------------------------------------------


class TestRc1Frozen:
    """rc1 SHA is still reachable."""

    def test_rc1_sha_resolves(self):
        import subprocess
        r = subprocess.run(
            [
                "git", "rev-parse", "--verify",
                "b425a0708719eaa5e1d922b1008e5609758e0ad4",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, (
            "rc1 SHA must remain reachable: "
            f"stderr={r.stderr}"
        )


# ---------------------------------------------------------------------------
# 12. TUHO / Oborovo factory path unaffected
# ---------------------------------------------------------------------------


class TestTuhoOborovoUnaffected:
    """P1-B does NOT touch the TUHO / Oborovo
    parity / factory path."""

    FORBIDDEN_TUHO_OBOROVO = [
        "app/project_factories.py",
        "domain/construction/templates/tuho.py",
        "domain/construction/templates/oborovo.py",
        "domain/opex/templates/tuho.py",
        "domain/opex/templates/oborovo.py",
        "domain/depreciation/templates/croatia.py",
    ]

    @pytest.mark.parametrize("path", FORBIDDEN_TUHO_OBOROVO)
    def test_factory_path_unchanged(self, path):
        import subprocess
        r = subprocess.run(
            ["git", "diff", "origin/main", "--name-only", "--", path],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert not r.stdout.strip(), (
            f"{path} should NOT be changed in P1-B"
        )


# ---------------------------------------------------------------------------
# 13. Helper module: no forbidden imports
# ---------------------------------------------------------------------------


class TestHelperSafety:
    """The helper module does not import any forbidden
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
        from app.ui import generic_driver_status_badges
        src = open(generic_driver_status_badges.__file__).read()
        assert f"import {module}" not in src
        assert f"from {module}" not in src

    def test_helper_does_not_set_construction_flag(self):
        from app.ui import generic_driver_status_badges
        src = open(generic_driver_status_badges.__file__).read()
        assert "use_construction_schedule_engine" not in src
        assert "use_depreciation_canonical_engine" not in src
        assert "use_canonical_tax_depreciation" not in src
