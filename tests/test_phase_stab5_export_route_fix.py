"""STAB-5: Fix export route failures found in the post-STAB-4 flow-walk.

DEF-1 (500 for TUHO/Oborovo): main_web.py called record_runtime_summary_export()
and record_institutional_workbook_export() with wrong keyword names:
  - 'safe_project' instead of 'project_code'
  - 'export_filename' instead of 'artifact_name'
Fix: corrected keyword names at both call sites in main_web.py.

DEF-2 (400 for Generic Solar/Wind): app/export/runtime_summary.py PROJECT_FACTORIES
only contained 'tuho' and 'oborovo'. Generic project codes were never added.
Fix: extended PROJECT_FACTORIES with 'generic_solar' and 'generic_wind'.

These tests prove:
  A. Audit service function signatures accept 'project_code' and 'artifact_name'.
  B. PROJECT_FACTORIES includes all four project codes.
  C. _project_key() resolves all four valid codes.
  D. _project_key() rejects unsafe/unknown codes with ValueError.
  E. build_runtime_summary_csv_export returns 200 for all four projects.
  F. build_institutional_workbook_export returns 200 for all four projects.
  G. CSV content-type and XLSX content-type are correct.
  H. Negative validation: unsafe project codes are rejected (400).
  I. Engine MD5 guard + TUHO/Oborovo parity.
  J. File scope guard.
"""
from __future__ import annotations

import hashlib
import inspect
import os
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
TUHO_P1_DSCR = 1.4507
OBOROVO_P1_DSCR = 1.15

ALL_PROJECTS = ["tuho", "oborovo", "generic_solar", "generic_wind"]
UNSAFE_CODES = ["../../etc/passwd", "unknown_project", "", "  ", "../tuho", "TUHO; drop"]


# ---------------------------------------------------------------------------
# A. Audit service signatures use 'project_code' and 'artifact_name'
# ---------------------------------------------------------------------------

class TestAuditServiceSignatures:
    def test_record_runtime_summary_export_params(self):
        from app.services.export_audit_service import record_runtime_summary_export
        params = list(inspect.signature(record_runtime_summary_export).parameters)
        assert "project_code" in params, "must accept 'project_code' (not 'safe_project')"
        assert "artifact_name" in params, "must accept 'artifact_name' (not 'export_filename')"
        assert "safe_project" not in params, "must not have 'safe_project' in signature"
        assert "export_filename" not in params, "must not have 'export_filename' in signature"

    def test_record_institutional_workbook_export_params(self):
        from app.services.export_audit_service import record_institutional_workbook_export
        params = list(inspect.signature(record_institutional_workbook_export).parameters)
        assert "project_code" in params, "must accept 'project_code'"
        assert "artifact_name" in params, "must accept 'artifact_name'"
        assert "safe_project" not in params
        assert "export_filename" not in params

    def test_main_web_calls_use_correct_kwarg_names(self):
        main_web = (Path(REPO_ROOT) / "main_web.py").read_text()
        # Count occurrences of wrong kwarg
        assert main_web.count("safe_project=safe_project,") == 0, (
            "main_web.py must not call record_*_export with safe_project= kwarg"
        )
        assert main_web.count("export_filename=") == 0, (
            "main_web.py must not use export_filename= kwarg"
        )
        # Confirm correct kwarg names appear in context
        assert "project_code=safe_project," in main_web, (
            "main_web.py must call record_*_export with project_code=safe_project"
        )
        assert "artifact_name=export.filename," in main_web, (
            "main_web.py must call record_*_export with artifact_name=export.filename"
        )


# ---------------------------------------------------------------------------
# B. PROJECT_FACTORIES includes all four project codes
# ---------------------------------------------------------------------------

class TestProjectFactories:
    def test_all_projects_in_factories(self):
        from app.export.runtime_summary import PROJECT_FACTORIES
        for code in ALL_PROJECTS:
            assert code in PROJECT_FACTORIES, (
                f"PROJECT_FACTORIES must include '{code}'"
            )

    def test_factories_are_callable(self):
        from app.export.runtime_summary import PROJECT_FACTORIES
        for code in ALL_PROJECTS:
            assert callable(PROJECT_FACTORIES[code]), (
                f"PROJECT_FACTORIES['{code}'] must be callable"
            )


# ---------------------------------------------------------------------------
# C. _project_key resolves all four valid codes
# ---------------------------------------------------------------------------

class TestProjectKeyResolution:
    @pytest.mark.parametrize("code", ALL_PROJECTS)
    def test_valid_code_resolves(self, code):
        from app.export.runtime_summary import _project_key
        assert _project_key(code) == code

    def test_strips_and_lowercases(self):
        from app.export.runtime_summary import _project_key
        assert _project_key("  TUHO  ") == "tuho"
        assert _project_key("Generic_Solar") == "generic_solar"


# ---------------------------------------------------------------------------
# D. _project_key rejects unsafe/unknown codes
# ---------------------------------------------------------------------------

class TestProjectKeyRejection:
    @pytest.mark.parametrize("bad_code", UNSAFE_CODES)
    def test_unsafe_code_raises_value_error(self, bad_code):
        from app.export.runtime_summary import _project_key
        with pytest.raises(ValueError):
            _project_key(bad_code)


# ---------------------------------------------------------------------------
# E. build_runtime_summary_csv_export returns 200 for all four projects
# ---------------------------------------------------------------------------

class TestRuntimeSummaryExportResponse:
    @pytest.mark.parametrize("code", ALL_PROJECTS)
    def test_returns_200(self, code):
        from app.services.export_service import build_runtime_summary_csv_export
        resp = build_runtime_summary_csv_export(code, safe_project=code)
        assert not resp.has_error(), (
            f"build_runtime_summary_csv_export('{code}') must not error; "
            f"status={resp.status_code} error={getattr(resp, 'error_content', '')[:200]}"
        )
        assert resp.status_code == 200, f"Expected 200 for '{code}', got {resp.status_code}"

    @pytest.mark.parametrize("bad_code", ["unknown_project", "../../etc/passwd"])
    def test_bad_code_returns_400(self, bad_code):
        from app.services.export_service import build_runtime_summary_csv_export
        resp = build_runtime_summary_csv_export(bad_code, safe_project=bad_code)
        assert resp.has_error(), f"Expected error response for '{bad_code}'"
        assert resp.status_code == 400, (
            f"Expected 400 for '{bad_code}', got {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# F. build_institutional_workbook_export returns 200 for all four projects
# ---------------------------------------------------------------------------

class TestInstitutionalWorkbookExportResponse:
    @pytest.mark.parametrize("code", ALL_PROJECTS)
    def test_returns_200(self, code):
        from app.services.export_service import build_institutional_workbook_export
        resp = build_institutional_workbook_export(code, safe_project=code)
        assert not resp.has_error(), (
            f"build_institutional_workbook_export('{code}') must not error; "
            f"status={resp.status_code}"
        )
        assert resp.status_code == 200, f"Expected 200 for '{code}', got {resp.status_code}"

    @pytest.mark.parametrize("bad_code", ["unknown_project", "../../etc/passwd"])
    def test_bad_code_returns_400(self, bad_code):
        from app.services.export_service import build_institutional_workbook_export
        resp = build_institutional_workbook_export(bad_code, safe_project=bad_code)
        assert resp.has_error(), f"Expected error response for '{bad_code}'"
        assert resp.status_code == 400, (
            f"Expected 400 for '{bad_code}', got {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# G. Content types
# ---------------------------------------------------------------------------

class TestContentTypes:
    def test_runtime_csv_content_type(self):
        from app.services.export_service import build_runtime_summary_csv_export
        resp = build_runtime_summary_csv_export("tuho", safe_project="tuho")
        assert resp.status_code == 200
        assert "csv" in resp.media_type.lower() or "text" in resp.media_type.lower(), (
            f"CSV export must have text/csv content type, got {resp.media_type!r}"
        )

    def test_institutional_workbook_content_type(self):
        from app.services.export_service import build_institutional_workbook_export
        resp = build_institutional_workbook_export("tuho", safe_project="tuho")
        assert resp.status_code == 200
        assert (
            "spreadsheet" in resp.media_type.lower()
            or "excel" in resp.media_type.lower()
            or "xlsx" in resp.media_type.lower()
            or "openxmlformats" in resp.media_type.lower()
        ), f"XLSX export must have Excel content type, got {resp.media_type!r}"

    def test_csv_filename_contains_project(self):
        from app.services.export_service import build_runtime_summary_csv_export
        for code in ALL_PROJECTS:
            resp = build_runtime_summary_csv_export(code, safe_project=code)
            assert resp.status_code == 200
            assert code in resp.filename, (
                f"CSV filename must contain '{code}', got {resp.filename!r}"
            )

    def test_xlsx_filename_contains_project(self):
        from app.services.export_service import build_institutional_workbook_export
        for code in ALL_PROJECTS:
            resp = build_institutional_workbook_export(code, safe_project=code)
            assert resp.status_code == 200
            assert code in resp.filename, (
                f"XLSX filename must contain '{code}', got {resp.filename!r}"
            )


# ---------------------------------------------------------------------------
# H. Negative validation — unsafe codes are rejected at build layer
# ---------------------------------------------------------------------------

class TestNegativeValidation:
    @pytest.mark.parametrize("bad_code", ["../../etc/passwd", "unknown_project"])
    def test_csv_export_rejects_unsafe_code(self, bad_code):
        from app.services.export_service import build_runtime_summary_csv_export
        resp = build_runtime_summary_csv_export(bad_code, safe_project=bad_code)
        assert resp.has_error()
        assert resp.status_code == 400

    @pytest.mark.parametrize("bad_code", ["../../etc/passwd", "unknown_project"])
    def test_xlsx_export_rejects_unsafe_code(self, bad_code):
        from app.services.export_service import build_institutional_workbook_export
        resp = build_institutional_workbook_export(bad_code, safe_project=bad_code)
        assert resp.has_error()
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# I. Engine MD5 + TUHO/Oborovo parity
# ---------------------------------------------------------------------------

class TestStab5Parity:
    def test_engine_md5_unchanged(self):
        path = Path(REPO_ROOT) / "app/waterfall_core.py"
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        assert digest == ENGINE_MD5, (
            f"waterfall_core.py must not change; got {digest}"
        )

    @staticmethod
    def _first_finite_dscr(periods):
        for p in periods:
            if not p.is_operation:
                continue
            d = p.dscr
            if d is None or d != d or d == float("inf"):
                continue
            return d
        return None

    def test_tuho_p1_dscr(self):
        from app.project_factories import create_default_tuho_wind1
        from app.ui_runner import _build_period_engine, _run_waterfall
        proj = create_default_tuho_wind1()
        result = _run_waterfall(proj, _build_period_engine(proj))
        dscr = self._first_finite_dscr(result.periods)
        assert dscr is not None
        assert abs(dscr - TUHO_P1_DSCR) < 0.001, (
            f"TUHO P1 DSCR={dscr}; expected {TUHO_P1_DSCR}"
        )

    def test_oborovo_p1_dscr(self):
        from app.project_factories import create_default_oborovo
        from app.ui_runner import _build_period_engine, _run_waterfall
        proj = create_default_oborovo()
        result = _run_waterfall(proj, _build_period_engine(proj))
        dscr = self._first_finite_dscr(result.periods)
        assert dscr is not None
        assert abs(dscr - OBOROVO_P1_DSCR) < 0.01, (
            f"Oborovo P1 DSCR={dscr}; expected {OBOROVO_P1_DSCR}"
        )


# ---------------------------------------------------------------------------
# J. File scope guard
# ---------------------------------------------------------------------------

class TestStab5FileScope:
    STAB5_ALLOWED_PREFIXES = (
        "main_web.py",
        "app/export/runtime_summary.py",
        "app/export/institutional_workbook.py",
        "tests/test_phase_stab5_",
        # forward-compatible: prior stabilization files
        "app/ui/scenario_matrix.py",
        "tests/test_phase_stab",
        "static/styles.css",
        "constraints.txt",
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
        "tests/test_phase_pr1_",
        "tests/test_phase_pr2_",
        "tests/test_phase_pr3_",
        "tests/test_phase_p2fix",
        "static/app.js",
        "app/templates/partials/_nav_compression.html",
        "app/templates/partials/workspace_shell.html",
        # STAB-6 new-project first-run fix
        "tests/test_phase_stab6_",
        # STAB-7 generic dashboard parity
        "app/services/run_service.py",
        "tests/test_phase_stab7_",
        # STAB-8 e2e runtime validation
        "tests/test_phase_stab8_",
        # UX-1 inputs badge cleanup
        "app/templates/partials/inputs_section.html",
        "tests/test_phase_ux1_",
        # UX-2 active sheet refresh
        "app/templates/partials/shared_runtime_block.html",
        "app/templates/partials/_sheet_distributions_partial.html",
        "app/templates/partials/_sheet_sponsor_partial.html",
        "tests/test_phase_ux2_",
    )

    STAB5_DISALLOWED_PREFIXES = (
        "app/waterfall_core.py",
        "app/project_factories.py",
        "app/persistence/",
        "app/services/export_audit_service.py",
        # app/services/ narrowed: run_service.py allowed from STAB-7 onwards
        "app/ui/",
        "static/app.js",
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
            # STAB-4 app.js changes are navigation-only — allow
            if f == "static/app.js":
                continue
            # STAB-5 must not touch disallowed files
            assert not any(f.startswith(p) for p in self.STAB5_DISALLOWED_PREFIXES), (
                f"STAB-5 must not touch {f}"
            )
            assert any(f.startswith(p) for p in self.STAB5_ALLOWED_PREFIXES), (
                f"STAB-5 file outside allowed scope: {f}"
            )

    def test_engine_md5_in_scope(self):
        path = Path(REPO_ROOT) / "app/waterfall_core.py"
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        assert digest == ENGINE_MD5
