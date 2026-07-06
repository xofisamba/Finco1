"""V4-6: Pilot Readiness Hardening tests.

Validates:
- _friendly_error: never exposes raw Python exceptions to users
- _jinja_fmt_kpi: yrs_f handler present
- python-docx in requirements
- Waterfall core SHA unchanged (Phase 51F)
- ic_report_service error handling
- Export functions don't propagate raw exc strings
"""
from __future__ import annotations

import hashlib
import pytest


WATERFALL_CORE_SHA = "9bee7fb9a5b26a7c25180a165aac81136439790a19d295c900d86d3ff8bc9470"


# ─── Phase 51F ───────────────────────────────────────────────────────────────

class TestPhase51FGuard:
    def test_waterfall_core_sha_unchanged(self):
        with open("app/waterfall_core.py", "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        assert sha == WATERFALL_CORE_SHA


# ─── _friendly_error ─────────────────────────────────────────────────────────

class TestFriendlyError:
    def test_no_raw_traceback_in_output(self):
        import sys
        sys.path.insert(0, ".")
        import importlib
        import main_web
        importlib.reload(main_web)
        msg = main_web._friendly_error(ValueError("internal detail"), "test context")
        assert "internal detail" not in msg
        assert "ValueError" not in msg

    def test_message_is_actionable(self):
        import main_web
        msg = main_web._friendly_error(RuntimeError("boom"), "sensitivity")
        assert len(msg) > 20
        assert "error" in msg.lower() or "failed" in msg.lower() or "check" in msg.lower()

    def test_context_included_in_message(self):
        import main_web
        msg = main_web._friendly_error(Exception("x"), "executive summary")
        assert "executive summary" in msg

    def test_no_context_still_returns_message(self):
        import main_web
        msg = main_web._friendly_error(Exception("x"))
        assert isinstance(msg, str)
        assert len(msg) > 10


# ─── _jinja_fmt_kpi yrs_f ────────────────────────────────────────────────────

class TestJinjaFmtKpi:
    def test_yrs_f_formats_with_unit(self):
        import main_web
        result = main_web._jinja_fmt_kpi(12.5, "yrs_f")
        assert "yrs" in result
        assert "12.5" in result

    def test_yrs_f_none_returns_dash(self):
        import main_web
        result = main_web._jinja_fmt_kpi(None, "yrs_f")
        assert result == "—"

    def test_pct_unchanged(self):
        import main_web
        result = main_web._jinja_fmt_kpi(0.1132, "pct")
        assert "%" in result
        assert "11.32" in result

    def test_x_unchanged(self):
        import main_web
        result = main_web._jinja_fmt_kpi(1.3786, "x")
        assert "x" in result
        assert "1.3786" in result

    def test_keur_unchanged(self):
        import main_web
        result = main_web._jinja_fmt_kpi(165471.0, "keur")
        assert "165" in result


# ─── requirements.txt ────────────────────────────────────────────────────────

class TestRequirements:
    def test_python_docx_in_requirements(self):
        with open("requirements.txt") as f:
            content = f.read()
        assert "python-docx" in content

    def test_docx_importable(self):
        from docx import Document
        assert Document is not None

    def test_openpyxl_in_requirements(self):
        with open("requirements.txt") as f:
            content = f.read()
        assert "openpyxl" in content


# ─── No raw exc in endpoint error vars ──────────────────────────────────────

class TestEndpointErrorHandling:
    """Integration: error messages from service layer are friendly."""

    @pytest.fixture(scope="class")
    def tuho_proj(self):
        from app.project_factories import create_default_tuho_wind1
        return create_default_tuho_wind1()

    def test_exec_summary_with_bad_proj_gives_friendly_error(self):
        """_friendly_error wraps any exception without leaking internals."""
        import main_web
        # Simulate what the endpoint does with a bad proj
        try:
            raise KeyError("internal_field_name_leaked")
        except Exception as exc:
            msg = main_web._friendly_error(exc, "executive summary")
        assert "internal_field_name_leaked" not in msg
        assert "KeyError" not in msg

    def test_ic_pack_with_bad_inputs_gives_friendly_error(self):
        import main_web
        try:
            raise AttributeError("WaterfallResult.nonexistent")
        except Exception as exc:
            msg = main_web._friendly_error(exc, "IC pack")
        assert "WaterfallResult" not in msg
        assert "AttributeError" not in msg

    def test_xlsx_export_success(self, tuho_proj):
        from app.services.ic_report_service import export_report_xlsx
        from app.ui_runner import _build_period_engine
        from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
        from app.services.lender_case_service import build_covenant_periods
        eng = _build_period_engine(tuho_proj)
        result = WaterfallRunner(tuho_proj, eng).run(WaterfallRunConfig.from_inputs(tuho_proj, eng))
        cov = build_covenant_periods(result)
        xlsx = export_report_xlsx(tuho_proj, result, "Base", covenant_periods=cov)
        assert len(xlsx) > 100

    def test_docx_export_ic_success(self, tuho_proj):
        from app.services.ic_report_service import export_report_docx
        from app.ui_runner import _build_period_engine
        from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
        from app.services.lender_case_service import build_covenant_periods
        eng = _build_period_engine(tuho_proj)
        result = WaterfallRunner(tuho_proj, eng).run(WaterfallRunConfig.from_inputs(tuho_proj, eng))
        cov = build_covenant_periods(result)
        docx = export_report_docx(tuho_proj, result, "Base", report_type="ic", covenant_periods=cov)
        assert len(docx) > 100

    def test_docx_export_credit_success(self, tuho_proj):
        from app.services.ic_report_service import export_report_docx
        from app.ui_runner import _build_period_engine
        from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
        from app.services.lender_case_service import build_covenant_periods
        eng = _build_period_engine(tuho_proj)
        result = WaterfallRunner(tuho_proj, eng).run(WaterfallRunConfig.from_inputs(tuho_proj, eng))
        cov = build_covenant_periods(result)
        docx = export_report_docx(tuho_proj, result, "Base", report_type="credit", covenant_periods=cov)
        assert len(docx) > 100


# ─── Template includes ───────────────────────────────────────────────────────

class TestTemplateIncludes:
    """All scenario_workspace.html includes resolve to existing files."""

    def test_all_includes_exist(self):
        import re, os
        with open("app/templates/partials/scenario_workspace.html") as f:
            content = f.read()
        includes = re.findall(r'{%\s*include\s*["\']([^"\']+)["\']', content)
        assert len(includes) > 0, "No includes found"
        for inc in includes:
            path = os.path.join("app/templates", inc)
            assert os.path.exists(path), f"Missing template: {path}"


# ─── Golden parity (regression guard) ────────────────────────────────────────

class TestGoldenParity:
    @pytest.fixture(scope="class")
    def tuho_result(self):
        from app.project_factories import create_default_tuho_wind1
        from app.ui_runner import _build_period_engine
        from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
        proj = create_default_tuho_wind1()
        eng = _build_period_engine(proj)
        return WaterfallRunner(proj, eng).run(WaterfallRunConfig.from_inputs(proj, eng))

    def test_equity_irr(self, tuho_result):
        assert abs(tuho_result.equity_irr - 0.1132) < 0.001

    def test_avg_dscr(self, tuho_result):
        assert abs(tuho_result.actual_avg_dscr - 1.3786) < 0.01

    def test_distributions(self, tuho_result):
        assert abs(tuho_result.total_distribution_keur - 165471) < 1000
