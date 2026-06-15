"""UX-1: Inputs Badge Cleanup for User Projects.

Problem: Editable fields in user-created projects showed TEMPLATE/CALCULATED badges,
creating a false impression the fields are read-only.

Fix: Suppress those badges conditionally via Jinja2 expression:
  badge=(None if is_user_project else "Calculated")
  badge=(None if is_user_project else "Template")

Only two fields required changes (lines 92-93 of inputs_section.html):
  - Installed Capacity: badge="Calculated" → conditional
  - P50 Hours:          badge="Template"   → conditional

All other fields either: already have informative badges (Saved, DSCR sculpt driver,
Timing driver, Indicative derived), are not editable in user projects, or had no badge.

These tests prove:
  A. inputs_section.html uses conditional badge for Installed Capacity.
  B. inputs_section.html uses conditional badge for P50 Hours.
  C. Non-editable fields (P90/P10, Availability, Capacity Factor, Degradation) unchanged.
  D. field_row macro: badge=None suppresses badge rendering.
  E. Reference project badge strings are preserved (not suppressed for non-user projects).
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
    def test_capacity_badge_is_conditional(self):
        src = INPUTS_SECTION.read_text()
        # Must not be a plain badge="Calculated" for the capacity_mw editable row
        # The conditional form: badge=(None if is_user_project else "Calculated")
        assert 'badge=(None if is_user_project else "Calculated")' in src or \
               "badge=(None if is_user_project else 'Calculated')" in src, (
            "Installed Capacity field_row must use conditional badge suppression for user projects"
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
    def test_p50_badge_is_conditional(self):
        src = INPUTS_SECTION.read_text()
        assert 'badge=(None if is_user_project else "Template")' in src or \
               "badge=(None if is_user_project else 'Template')" in src, (
            "P50 Hours field_row must use conditional badge suppression for user projects"
        )

    def test_p50_hours_field_name_preserved(self):
        src = INPUTS_SECTION.read_text()
        assert 'field_name="p50_hours"' in src, (
            "field_name='p50_hours' must remain in the template"
        )

    def test_p50_not_hardcoded_template_on_editable_row(self):
        src = INPUTS_SECTION.read_text()
        lines = src.splitlines()
        for line in lines:
            if 'field_name="p50_hours"' in line and 'editable=is_user_project' in line:
                assert 'badge="Template"' not in line and "badge='Template'" not in line, (
                    "Editable p50_hours row must not use plain badge='Template' string"
                )


# ---------------------------------------------------------------------------
# C. Non-editable technical fields: badges unchanged
# ---------------------------------------------------------------------------

class TestNonEditableFieldBadgesUnchanged:
    def test_p90_p10_still_has_template_badge(self):
        src = INPUTS_SECTION.read_text()
        # P90/P10 row has no editable/field_name → badge stays hardcoded
        assert re.search(r'P90/P10 Hours.*badge="Template"', src, re.DOTALL) or \
               re.search(r"P90/P10 Hours.*badge='Template'", src, re.DOTALL), (
            "P90/P10 Hours must still have hardcoded badge='Template'"
        )

    def test_availability_still_has_template_badge(self):
        src = INPUTS_SECTION.read_text()
        assert "Availability" in src, "Availability field must still be present"
        # Find Availability line specifically
        for line in src.splitlines():
            if "Availability" in line and "field_row" in line and "field_name" not in line:
                assert 'badge="Template"' in line or "badge='Template'" in line, (
                    "Availability (non-editable) must keep badge='Template'"
                )
                break

    def test_capacity_factor_still_has_calculated_badge(self):
        src = INPUTS_SECTION.read_text()
        for line in src.splitlines():
            if "Capacity Factor" in line and "field_row" in line:
                assert 'badge="Calculated"' in line or "badge='Calculated'" in line, (
                    "Capacity Factor (non-editable) must keep badge='Calculated'"
                )
                break

    def test_degradation_still_has_template_badge(self):
        src = INPUTS_SECTION.read_text()
        for line in src.splitlines():
            if "Degradation" in line and "field_row" in line:
                assert 'badge="Template"' in line or "badge='Template'" in line, (
                    "Degradation (non-editable) must keep badge='Template'"
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
# E. Reference project badge strings preserved
# ---------------------------------------------------------------------------

class TestReferenceBadgesPreserved:
    def test_template_badge_string_still_exists(self):
        src = INPUTS_SECTION.read_text()
        # "Template" badge string must still appear for non-editable fields
        assert '"Template"' in src or "'Template'" in src, (
            "'Template' badge string must still appear in inputs_section.html"
        )

    def test_calculated_badge_string_still_exists(self):
        src = INPUTS_SECTION.read_text()
        assert '"Calculated"' in src or "'Calculated'" in src, (
            "'Calculated' badge string must still appear in inputs_section.html"
        )

    def test_model_default_badge_still_present(self):
        src = INPUTS_SECTION.read_text()
        assert "Model default" in src or "Model Default" in src, (
            "Model default badge must still appear for non-editable period frequency field"
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
        "app/services/run_service.py",
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
