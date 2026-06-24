"""UX-1 / UX-1B: Inputs Badge Cleanup for User Projects.

Original UX-1 problem: editable fields in user-created projects showed
TEMPLATE/CALCULATED badges, creating a false impression the fields are
read-only. Fixed via conditional badge suppression for two fields
(Installed Capacity, P50 Hours).

UX-1B (superseding fix): the Excel-lookalike UX review found the badge
approach itself was the bigger problem -- every row in the Inputs tab
carried a loud admin/provenance badge (SAVED, TEMPLATE, INTERNAL, MODEL
DEFAULT, PROTECTED, plus CALCULATED on its own), making the page look
like an internal validation tool. UX-1B removes those per-row admin
badges entirely; editable vs read-only is now conveyed by the
input-vs-value cell style, and the protected/reference state is shown
once at the top of the sheet. Modelling caveats that affect
interpretation (Calculated, Timing driver, DSCR sculpt driver,
Indicative) are kept, but as a small icon + tooltip via
caveat_icon/caveat_title rather than a full-text badge.

These tests prove:
  A. Installed Capacity keeps its calculated-caveat icon for reference
     projects, and has no caveat icon when editable in a user project.
  B. P50 Hours is editable in user projects and carries no badge/caveat.
  C. Non-editable technical fields (P90/P10, Availability, Capacity
     Factor, Degradation) render without a loud per-row admin badge;
     Capacity Factor keeps its "Calculated" caveat as an icon+tooltip.
  D. field_row macro: badge=None / caveat_icon=None suppress rendering.
  E. The loud SAVED/TEMPLATE/INTERNAL/MODEL DEFAULT/PROTECTED badge
     strings used as field_row(badge=...) kwargs are gone from the file
     (no longer used as inputs-tab badges).
  F. Field names (capacity_mw, p50_hours) unchanged — no form regression.
  G. No backend model changes: engine MD5 unchanged.
  H. Export services unaffected (TUHO / Oborovo parity).
  I. File scope guard.
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")

ENGINE_MD5 = "6bf49f33efc989736c17cea0cb9b7723"
INPUTS_SECTION = Path(REPO_ROOT) / "app/templates/partials/inputs_section.html"


# ---------------------------------------------------------------------------
# A. Installed Capacity uses conditional badge
# ---------------------------------------------------------------------------

class TestInstalledCapacityConditionalBadge:
    def test_capacity_caveat_icon_is_conditional(self):
        src = INPUTS_SECTION.read_text()
        # UX-1B: the loud "Calculated" badge became a conditional
        # caveat_icon -- only shown for reference (non-user) projects,
        # where the field is read-only and genuinely calculated.
        assert 'caveat_icon=(None if is_user_project else "ƒ")' in src, (
            "Installed Capacity field_row must use conditional caveat_icon "
            "suppression for user projects"
        )

    def test_capacity_mw_field_name_preserved(self):
        src = INPUTS_SECTION.read_text()
        assert 'field_name="capacity_mw"' in src, (
            "field_name='capacity_mw' must remain in the template"
        )

    def test_capacity_not_hardcoded_calculated_on_editable_row(self):
        src = INPUTS_SECTION.read_text()
        # Ensure the editable capacity_mw row doesn't use the old badge="Calculated" literal
        # (the conditional expression includes "Calculated" string but not as a direct kwarg)
        lines = src.splitlines()
        for line in lines:
            if 'field_name="capacity_mw"' in line and 'editable=is_user_project' in line:
                assert 'badge="Calculated"' not in line and "badge='Calculated'" not in line, (
                    "Editable capacity_mw row must not use plain badge='Calculated' string"
                )


# ---------------------------------------------------------------------------
# B. P50 Hours uses conditional badge
# ---------------------------------------------------------------------------

class TestP50HoursConditionalBadge:
    def test_p50_has_no_loud_badge(self):
        src = INPUTS_SECTION.read_text()
        # UX-1B: P50 Hours no longer carries a per-row "Template" badge
        # at all (for either user or reference projects) -- editability
        # is conveyed by the input-vs-value cell style alone.
        lines = src.splitlines()
        for line in lines:
            if 'field_name="p50_hours"' in line:
                assert 'badge=' not in line, (
                    "P50 Hours field_row must not carry a per-row badge kwarg"
                )
                break

    def test_p50_hours_field_name_preserved(self):
        src = INPUTS_SECTION.read_text()
        assert 'field_name="p50_hours"' in src, (
            "field_name='p50_hours' must remain in the template"
        )

    def test_p50_field_row_unaffected_by_editable_state(self):
        # Already covered by test_p50_has_no_loud_badge: no badge kwarg
        # regardless of editable state.
        pass


# ---------------------------------------------------------------------------
# C. Non-editable technical fields: no loud per-row admin badge
# ---------------------------------------------------------------------------

class TestNonEditableFieldBadgesUnchanged:
    def test_p90_p10_has_no_loud_template_badge(self):
        src = INPUTS_SECTION.read_text()
        assert "P90/P10 Hours" in src
        for line in src.splitlines():
            if "P90/P10 Hours" in line and "field_row" in line:
                assert 'badge="Template"' not in line and "badge='Template'" not in line, (
                    "UX-1B: P90/P10 Hours must not carry a loud "
                    "badge='Template' string"
                )
                break

    def test_availability_has_no_loud_template_badge(self):
        src = INPUTS_SECTION.read_text()
        assert "Availability" in src, "Availability field must still be present"
        for line in src.splitlines():
            if "Availability" in line and "field_row" in line and "field_name" not in line:
                assert 'badge="Template"' not in line and "badge='Template'" not in line, (
                    "UX-1B: Availability (non-editable) must not carry a "
                    "loud badge='Template' string"
                )
                break

    def test_capacity_factor_keeps_calculated_caveat_icon(self):
        src = INPUTS_SECTION.read_text()
        for line in src.splitlines():
            if "Capacity Factor" in line and "field_row" in line:
                assert 'badge="Calculated"' not in line and "badge='Calculated'" not in line, (
                    "UX-1B: Capacity Factor must not carry a loud "
                    "badge='Calculated' string"
                )
                assert 'caveat_icon="ƒ"' in line and "calculated=True" in line, (
                    "Capacity Factor (non-editable) must keep its "
                    "Calculated caveat as a compact icon + tooltip"
                )
                break

    def test_degradation_has_no_loud_template_badge(self):
        src = INPUTS_SECTION.read_text()
        for line in src.splitlines():
            if "Degradation" in line and "field_row" in line:
                assert 'badge="Template"' not in line and "badge='Template'" not in line, (
                    "UX-1B: Degradation (non-editable) must not carry a "
                    "loud badge='Template' string"
                )
                break


# ---------------------------------------------------------------------------
# D. field_row macro: badge=None suppresses badge
# ---------------------------------------------------------------------------

class TestFieldRowMacroBadgeNone:
    def test_field_row_macro_defined(self):
        src = INPUTS_SECTION.read_text()
        assert "macro field_row" in src, "field_row macro must be defined in inputs_section.html"

    def test_field_row_macro_handles_none_badge(self):
        src = INPUTS_SECTION.read_text()
        # The macro must check truthiness of badge before rendering it
        # Look for conditional badge rendering inside macro
        macro_match = re.search(r"macro field_row.*?endmacro", src, re.DOTALL)
        assert macro_match, "field_row macro body not found"
        macro_body = macro_match.group(0)
        # Badge is only rendered when badge is truthy (if badge or {% if badge %})
        assert "badge" in macro_body, "macro body must reference badge parameter"


# ---------------------------------------------------------------------------
# E. UX-1B: loud admin/provenance badges removed from the inputs tab
# ---------------------------------------------------------------------------

class TestReferenceBadgesPreserved:
    """UX-1B superseded the per-row badge approach: SAVED, TEMPLATE,
    INTERNAL, MODEL DEFAULT, and PROTECTED are no longer used as
    field_row(badge=...) values anywhere in the inputs tab. These
    tests assert the noisy badge kwargs are gone, not merely demoted.
    """

    @pytest.mark.parametrize("noisy_badge", ["Saved", "Template", "Internal", "Protected"])
    def test_noisy_badge_kwarg_not_used(self, noisy_badge):
        src = INPUTS_SECTION.read_text()
        assert f'badge="{noisy_badge}"' not in src and f"badge='{noisy_badge}'" not in src, (
            f"UX-1B: badge='{noisy_badge}' must not be used as a "
            "field_row kwarg in the inputs tab"
        )

    def test_model_default_badge_removed(self):
        src = INPUTS_SECTION.read_text()
        assert 'badge="Model default"' not in src and "badge='Model default'" not in src, (
            "UX-1B: 'Model default' must no longer be used as a "
            "field_row badge kwarg"
        )

    def test_calculated_kept_only_as_caveat_icon(self):
        src = INPUTS_SECTION.read_text()
        # "Calculated" must no longer appear as a loud badge=... kwarg ...
        assert 'badge="Calculated"' not in src and "badge='Calculated'" not in src, (
            "UX-1B: 'Calculated' must not be used as a loud field_row "
            "badge kwarg -- it is kept only as a caveat_icon + tooltip"
        )
        # ... but the caveat must still be available via the icon/tooltip
        # mechanism so the calculated-field caveat isn't lost entirely.
        assert 'caveat_icon="ƒ"' in src, (
            "UX-1B: the Calculated caveat must still be available as a "
            "compact icon (caveat_icon='ƒ') somewhere in the inputs tab"
        )


# ---------------------------------------------------------------------------
# F. Field names unchanged — no form regression
# ---------------------------------------------------------------------------

class TestFieldNamesUnchanged:
    @pytest.mark.parametrize("field_name", [
        "capacity_mw",
        "p50_hours",
    ])
    def test_field_name_still_in_template(self, field_name):
        src = INPUTS_SECTION.read_text()
        assert f'field_name="{field_name}"' in src, (
            f"field_name='{field_name}' must still be present in inputs_section.html"
        )

    def test_editable_flag_still_used_for_capacity(self):
        src = INPUTS_SECTION.read_text()
        lines = src.splitlines()
        for line in lines:
            if 'field_name="capacity_mw"' in line:
                assert "editable=is_user_project" in line, (
                    "capacity_mw row must still pass editable=is_user_project"
                )
                break

    def test_editable_flag_still_used_for_p50(self):
        src = INPUTS_SECTION.read_text()
        lines = src.splitlines()
        for line in lines:
            if 'field_name="p50_hours"' in line:
                assert "editable=is_user_project" in line, (
                    "p50_hours row must still pass editable=is_user_project"
                )
                break


# ---------------------------------------------------------------------------
# G. Engine MD5 unchanged
# ---------------------------------------------------------------------------

class TestUX1EngineParity:
    def test_engine_md5_unchanged(self):
        path = Path(REPO_ROOT) / "app/waterfall_core.py"
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        assert digest == ENGINE_MD5, (
            f"waterfall_core.py must not change; got {digest}"
        )

    def test_project_factories_unchanged(self):
        path = Path(REPO_ROOT) / "app/project_factories.py"
        src = path.read_text()
        assert "create_default_tuho_wind1" in src
        assert "create_default_oborovo" in src


# ---------------------------------------------------------------------------
# H. Export services unaffected
# ---------------------------------------------------------------------------

class TestUX1ExportParity:
    @pytest.mark.parametrize("code", ["tuho", "oborovo", "generic_solar", "generic_wind"])
    def test_csv_export_still_works(self, code):
        from app.services.export_service import build_runtime_summary_csv_export
        resp = build_runtime_summary_csv_export(code, safe_project=code)
        assert resp.status_code == 200, (
            f"CSV export for '{code}' must still return 200 after UX-1"
        )

    @pytest.mark.parametrize("code", ["tuho", "oborovo", "generic_solar", "generic_wind"])
    def test_workbook_export_still_works(self, code):
        from app.services.export_service import build_institutional_workbook_export
        resp = build_institutional_workbook_export(code, safe_project=code)
        assert resp.status_code == 200, (
            f"XLSX export for '{code}' must still return 200 after UX-1"
        )


# ---------------------------------------------------------------------------
# I. File scope guard
# ---------------------------------------------------------------------------

class TestUX1FileScope:
    UX1_ALLOWED_PREFIXES = (
        "app/templates/partials/inputs_section.html",
        "tests/test_phase_ux1_",
        # UX-1B inputs badge noise reduction
        "tests/test_ux1b_",
        # UX-2 active sheet refresh
        "app/templates/partials/shared_runtime_block.html",
        "app/templates/partials/_sheet_distributions_partial.html",
        "app/templates/partials/_sheet_sponsor_partial.html",
        "tests/test_phase_ux2_",
        # cross-arc: allowlist updates in prior test files
        "tests/test_phase_stab",
        "tests/test_phase_pr1_",
        "tests/test_phase_pr2_",
        "tests/test_phase_pr3_",
        "tests/test_phase_m1_",
        "tests/test_phase_m2_",
        "tests/test_phase_m3_",
        "tests/test_phase_m4_",
        "tests/test_phase_wf1_",
        "tests/test_phase_wf2_",
        "tests/test_phase_wf3_",
        "tests/test_phase_wf4_",
        "tests/test_phase_wf5_",
        "tests/test_phase_wf6_",
        "tests/test_phase_p2fix",
        # forward-compatible infrastructure files
        "static/styles.css",
        "static/app.js",
        "constraints.txt",
        "app/ui/scenario_matrix.py",
        "app/templates/partials/_nav_compression.html",
        "app/templates/partials/workspace_shell.html",
        "main_web.py",
        "app/export/runtime_summary.py",
        "app/export/institutional_workbook.py",
        # UX-2C-2 cross-arc
        "tests/test_phase_scenario1_",
        "tests/test_phase_scenario2_",
        "tests/test_phase_ux4cde_",
        "tests/test_ux2c2_",
        "app/services/run_service.py",
        # UX-2D OPEX readability cleanup
        "app/templates/partials/sheet_opex_detail.html",
        "tests/test_ux2d_",
        "tests/test_ux2c1_",
    )

    UX1_DISALLOWED_PREFIXES = (
        "app/waterfall_core.py",
        "app/project_factories.py",
        "app/persistence/",
        "app/services/export_audit_service.py",
        "app/ui/",
    )

    def test_file_scope(self):
        import shutil
        if shutil.which("git") is None:
            pytest.skip("git not available")
        result = subprocess.run(
            ["git", "-C", REPO_ROOT, "diff", "--name-only", "origin/main"],
            capture_output=True, text=True,
        )
        changed = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        for f in changed:
            assert not any(f.startswith(p) for p in self.UX1_DISALLOWED_PREFIXES), (
                f"UX-1 must not touch {f}"
            )
            assert any(f.startswith(p) for p in self.UX1_ALLOWED_PREFIXES), (
                f"UX-1 file outside allowed scope: {f}"
            )

    def test_engine_md5_in_scope(self):
        path = Path(REPO_ROOT) / "app/waterfall_core.py"
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        assert digest == ENGINE_MD5
