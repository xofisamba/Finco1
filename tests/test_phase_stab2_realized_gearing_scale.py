"""STAB-2: Fix Realized Gearing double-scaling in scenario matrix.

Defect: scenario matrix Realized Gearing Base cell showed ~5940% instead
of ~59.4%.

Root cause: project_context._compute_realized_gearing_pct stores
realized_gearing_pct as a percentage in [0, 100] (e.g. 59.4). But the
MatrixRow for 'realized_gearing_pct' used _fmt_pct which multiplies by
100, double-scaling to ~5940%.

Fix: introduce _fmt_pct_already_pct formatter (no × 100) and assign it
to the realized_gearing_pct MatrixRow.

These tests prove:
  A. _fmt_pct_already_pct exists and formats without × 100.
  B. The realized_gearing_pct MatrixRow uses _fmt_pct_already_pct.
  C. build_matrix_rows populates the realized_gearing_pct cell correctly
     (59.4 → "59.40%", not "5940.00%").
  D. Other pct rows (interest_rate_pct, gearing_pct) still use _fmt_pct
     (× 100) unchanged.
  E. Engine MD5 unchanged; TUHO / Oborovo parity preserved.
  F. File scope clean.
"""
from __future__ import annotations

import hashlib
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


# ---------------------------------------------------------------------------
# A. _fmt_pct_already_pct formatter
# ---------------------------------------------------------------------------

class TestFmtPctAlreadyPct:
    def test_exists(self):
        from app.ui.scenario_matrix import _fmt_pct_already_pct
        assert callable(_fmt_pct_already_pct)

    def test_no_multiplication(self):
        from app.ui.scenario_matrix import _fmt_pct_already_pct
        assert _fmt_pct_already_pct(59.4) == "59.40%", (
            "59.4 (already a percentage) must format to '59.40%', not '5940.00%'"
        )

    def test_none_returns_dash(self):
        from app.ui.scenario_matrix import _fmt_pct_already_pct
        assert _fmt_pct_already_pct(None) == "—"

    def test_zero_formats(self):
        from app.ui.scenario_matrix import _fmt_pct_already_pct
        assert _fmt_pct_already_pct(0.0) == "0.00%"

    def test_hundred_formats(self):
        from app.ui.scenario_matrix import _fmt_pct_already_pct
        assert _fmt_pct_already_pct(100.0) == "100.00%"

    def test_does_not_multiply_by_100(self):
        from app.ui.scenario_matrix import _fmt_pct_already_pct, _fmt_pct
        val = 59.4
        already_pct = _fmt_pct_already_pct(val)
        wrong = _fmt_pct(val)
        assert already_pct != wrong, (
            "_fmt_pct_already_pct and _fmt_pct must differ for percentage inputs"
        )
        assert "5940" not in already_pct, (
            "Must not double-scale to 5940%"
        )


# ---------------------------------------------------------------------------
# B. realized_gearing_pct MatrixRow uses _fmt_pct_already_pct
# ---------------------------------------------------------------------------

class TestRealizedGearingRowFormatter:
    def test_realized_gearing_row_uses_already_pct(self):
        from app.ui.scenario_matrix import KPI_ROWS, _fmt_pct_already_pct
        rg_rows = [r for r in KPI_ROWS if r.attr == "realized_gearing_pct"]
        assert rg_rows, "realized_gearing_pct must be in KPI_ROWS"
        row = rg_rows[0]
        assert row.fmt is _fmt_pct_already_pct, (
            "realized_gearing_pct row must use _fmt_pct_already_pct "
            "(not _fmt_pct which would double-scale)"
        )

    def test_other_pct_rows_still_use_fmt_pct(self):
        from app.ui.scenario_matrix import INPUT_ROWS, _fmt_pct
        for attr in ("interest_rate_pct", "gearing_pct"):
            rows = [r for r in INPUT_ROWS if r.attr == attr]
            assert rows, f"{attr} must be in INPUT_ROWS"
            assert rows[0].fmt is _fmt_pct, (
                f"{attr} must use _fmt_pct (fraction → percentage)"
            )


# ---------------------------------------------------------------------------
# C. build_matrix_rows — realized_gearing_pct formats without double-scale
# ---------------------------------------------------------------------------

class TestRealizedGearingCellValue:
    def _ctx(self):
        class FakeCtx:
            ppa_tariff_eur_mwh = 75.0
            operating_hours_p50 = 2800
            capacity_mw = 35.0
            total_capex_keur = 42000.0
            opex_y1_total_keur = 1200.0
            interest_rate_pct = 0.045      # fraction → _fmt_pct gives "4.50%"
            senior_tenor_years = 18
            target_dscr = 1.30
            gearing_pct = 0.70             # fraction → _fmt_pct gives "70.00%"
            ppa_term_years = 15
            construction_months = 18
            realized_gearing_pct = 59.4    # percentage → _fmt_pct_already_pct gives "59.40%"
        return FakeCtx()

    def test_realized_gearing_base_cell_not_double_scaled(self):
        from app.ui.scenario_matrix import build_matrix_rows, ROW_KIND_KPI
        rows = build_matrix_rows(self._ctx())
        rg_row = next(r for r in rows if r["row"].attr == "realized_gearing_pct")
        val = rg_row["base"]
        assert "5940" not in val, (
            f"Realized Gearing must not be double-scaled; got {val!r}"
        )
        assert "59.40%" == val, (
            f"realized_gearing_pct=59.4 must show '59.40%'; got {val!r}"
        )

    def test_interest_rate_still_correct(self):
        from app.ui.scenario_matrix import build_matrix_rows
        rows = build_matrix_rows(self._ctx())
        ir_row = next(r for r in rows if r["row"].attr == "interest_rate_pct")
        assert "4.50%" == ir_row["base"], (
            f"interest_rate_pct=0.045 must show '4.50%'; got {ir_row['base']!r}"
        )

    def test_indicative_gearing_still_correct(self):
        from app.ui.scenario_matrix import build_matrix_rows
        rows = build_matrix_rows(self._ctx())
        gearing_row = next(r for r in rows if r["row"].attr == "gearing_pct")
        assert "70.00%" == gearing_row["base"], (
            f"gearing_pct=0.70 must show '70.00%'; got {gearing_row['base']!r}"
        )

    def test_realized_gearing_none_shows_dash(self):
        from app.ui.scenario_matrix import build_matrix_rows, ROW_KIND_KPI

        class NullCtx:
            ppa_tariff_eur_mwh = None
            operating_hours_p50 = None
            capacity_mw = None
            total_capex_keur = None
            opex_y1_total_keur = None
            interest_rate_pct = None
            senior_tenor_years = None
            target_dscr = None
            gearing_pct = None
            ppa_term_years = None
            construction_months = None
            realized_gearing_pct = None

        rows = build_matrix_rows(NullCtx())
        rg_row = next(r for r in rows if r["row"].attr == "realized_gearing_pct")
        assert rg_row["base"] == "—", (
            f"None realized_gearing_pct must show '—'; got {rg_row['base']!r}"
        )


# ---------------------------------------------------------------------------
# D. project_context stores realized_gearing_pct as percentage (0-100)
# ---------------------------------------------------------------------------

class TestComputeRealizedGearingPct:
    def test_returns_percentage_not_fraction(self):
        from app.ui.project_context import _compute_realized_gearing_pct
        result = _compute_realized_gearing_pct(59400.0, 100000.0)
        assert result is not None
        assert abs(result - 59.4) < 0.01, (
            f"Expected 59.4 (percentage); got {result}"
        )
        assert result > 1.0, (
            "realized_gearing_pct must be in percentage units (>1), not fraction (<1)"
        )

    def test_tuho_like_gearing(self):
        from app.ui.project_context import _compute_realized_gearing_pct
        result = _compute_realized_gearing_pct(29400.0, 42000.0)
        assert result is not None
        assert abs(result - 70.0) < 0.01, (
            f"Expected ~70.0%; got {result}"
        )


# ---------------------------------------------------------------------------
# E. Engine MD5 + parity
# ---------------------------------------------------------------------------

class TestStab2Parity:
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
        assert abs(dscr - TUHO_P1_DSCR) < 0.001, f"TUHO P1 DSCR={dscr}; expected {TUHO_P1_DSCR}"

    def test_oborovo_p1_dscr(self):
        from app.project_factories import create_default_oborovo
        from app.ui_runner import _build_period_engine, _run_waterfall
        proj = create_default_oborovo()
        result = _run_waterfall(proj, _build_period_engine(proj))
        dscr = self._first_finite_dscr(result.periods)
        assert dscr is not None
        assert abs(dscr - OBOROVO_P1_DSCR) < 0.01, f"Oborovo P1 DSCR={dscr}; expected {OBOROVO_P1_DSCR}"


# ---------------------------------------------------------------------------
# F. File scope
# ---------------------------------------------------------------------------

class TestStab2FileScope:
    STAB2_ALLOWED_PREFIXES = (
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
        # STAB-4 navigation-only changes
        "static/app.js",
        "app/templates/partials/_nav_compression.html",
        "app/templates/partials/workspace_shell.html",
        # STAB-5 export route fix
        "main_web.py",
        "app/export/runtime_summary.py",
        "app/export/institutional_workbook.py",
        "tests/test_phase_stab5_",
        # STAB-6 new-project first-run fix
        "tests/test_phase_stab6_",
        # STAB-7 generic dashboard parity
        "app/services/run_service.py",
        "tests/test_phase_stab7_",
    )

    STAB2_DISALLOWED_PREFIXES = (
        "app/waterfall_core.py",
        "app/project_factories.py",
        "app/persistence/",
        # app/services/ narrowed: run_service.py allowed from STAB-7 onwards
        "app/services/export_audit_service.py",
        "main_api.py",
        "app/ui/project_context.py",
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
            # STAB-4: app.js change must be navigation-only
            if f == "static/app.js":
                import pathlib as _pl
                js_src = (_pl.Path(REPO_ROOT) / "static/app.js").read_text()
                assert "STAB-4" in js_src, f"static/app.js changed without STAB-4 marker"
                continue
            assert not any(f.startswith(p) for p in self.STAB2_DISALLOWED_PREFIXES), (
                f"STAB-2 must not touch {f}"
            )
            assert any(f.startswith(p) for p in self.STAB2_ALLOWED_PREFIXES), (
                f"STAB-2 file outside allowed scope: {f}"
            )

    def test_engine_md5_in_scope(self):
        path = Path(REPO_ROOT) / "app/waterfall_core.py"
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        assert digest == ENGINE_MD5
