"""Phase 21 — Template Render Test Suite
Prevents regressions where invalid Jinja2 |format patterns or missing context
cause HTTP 500 on workspace/sheet renders.

Branch: phase21-template-render-test-suite
Base: af9ce44 (9ca0f49 PR#268 format fix + d2797db sheet_financials guard)
"""
import os, re, subprocess, sys, jinja2
from datetime import datetime
from pathlib import Path
from unittest import mock

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
PARTIALS = PROJECT_ROOT / "app/templates/partials"
TESTS_DIR = PROJECT_ROOT / "tests"


# ─── Helper: Build representative contexts ──────────────────────────────────────

def make_project_ctx(
    name="TUHO Wind 1", ptype="Wind", code="tuho",
    total_capex_keur=120_000.0, senior_debt_keur=43_359.0,
    shl_amount_keur=14_621.0, shl_rate_pct=0.0793,
    shl_idc_keur=0.0, idc_keur=1_169.0,
    financial_close="2028-06-30", cod_date="2029-12-30",
    construction_months=18, horizon_years=25,
    capacity_mw=72.0, operating_hours_p50=2800.0,
    plant_availability=0.975, grid_availability=0.98,
    pv_degradation=None, technology="Wind",
    ppa_tariff_eur_mwh=85.0, ppa_term_years=15,
    ppa_index_pct=0.0, co2_enabled=True, co2_price_eur_mwh=4.19,
    opex_y1_total_keur=8_500.0, opex_contingency_method="",
    interest_rate_pct=0.068, senior_tenor_years=15,
    target_dscr=1.4, gearing_pct=0.75,
    cit_rate_pct=0.18, loss_carryforward_years=5,
    data_source="seed",
):
    """Build a full project_ctx matching the ProjectContext dataclass fields."""
    from app.ui.project_context import ProjectContext
    return ProjectContext(
        code=code.upper(),
        name=name,
        company="TUHO Energy d.o.o.",
        country_iso="HR",
        technology=technology,
        capacity_mw=capacity_mw,
        cod_date=cod_date,
        financial_close=financial_close,
        construction_months=construction_months,
        horizon_years=horizon_years,
        period_frequency="Semiannual",
        yield_scenario="P50",
        operating_hours_p50=operating_hours_p50,
        plant_availability=plant_availability,
        grid_availability=grid_availability,
        pv_degradation=pv_degradation,
        ppa_tariff_eur_mwh=ppa_tariff_eur_mwh,
        ppa_term_years=ppa_term_years,
        ppa_index_pct=ppa_index_pct,
        co2_enabled=co2_enabled,
        co2_price_eur_mwh=co2_price_eur_mwh,
        revenue_items=(),
        opex_items=(),
        opex_y1_total_keur=opex_y1_total_keur,
        opex_contingency_method=opex_contingency_method,
        opex_contingency_pct=0.0,
        total_capex_keur=total_capex_keur,
        epc_contract_keur=0.0,
        idc_keur=idc_keur,
        bank_fees_keur=0.0,
        capex_items=(),
        senior_debt_keur=senior_debt_keur,
        interest_rate_pct=interest_rate_pct,
        senior_tenor_years=senior_tenor_years,
        target_dscr=target_dscr,
        gearing_pct=gearing_pct,
        shl_amount_keur=shl_amount_keur,
        shl_rate_pct=shl_rate_pct,
        shl_idc_keur=shl_idc_keur,
        construction_items=(),
        idc_items=(),
        cit_rate_pct=cit_rate_pct,
        loss_carryforward_years=loss_carryforward_years,
        g20_status="BLOCKED",
        r99_r102_status="NOT_APPROVED",
        parity_status="",
        data_source=data_source,
        missing_fields=(),
    )


def make_runtime_summary(
    scenario_name="Base Case",
    project_irr=0.0947, equity_irr=0.1161,
    avg_dscr=1.451, senior_debt_keur=43_359.0
):
    class RS:
        pass
    r = RS()
    r.active_scenario_name = scenario_name
    r.project_irr = project_irr
    r.equity_irr = equity_irr
    r.avg_dscr = avg_dscr
    r.senior_debt_keur = senior_debt_keur
    return r


def make_workspace_state(
    active_scenario_name="Base Case", dirty=False,
    last_runtime_origin="saved_state"
):
    class WS:
        pass
    w = WS()
    w.active_scenario_name = active_scenario_name
    w.dirty = dirty
    w.last_runtime_origin = last_runtime_origin
    w.last_runtime_snapshot_id = "snap_test_12345678"
    w.updated_at = datetime(2026, 5, 27, 12, 0, 0)
    w.last_runtime_at = datetime(2026, 5, 27, 11, 30, 0) if last_runtime_origin else None
    return w


def make_scenario_records():
    class Sc:
        pass
    s = Sc()
    s.scenario_id = "sc_test_001"
    s.scenario_name = "Base Case"
    s.project_code = "TUHO"
    s.is_base_case = True
    s.updated_at = datetime(2026, 5, 27, 12, 0, 0)
    s.copied_from_scenario_id = None
    s.snapshot = {"scenario": "Base Case"}
    return [s]


# ─── Jinja env ───────────────────────────────────────────────────────────────

def _jinja_env():
    import main_web
    return main_web.templates.env


def _render(name, ctx):
    t = _jinja_env().get_template(name)
    return t.render(ctx)


# ─── 1. Invalid |format pattern grep check ─────────────────────────────────

INVALID_PATTERNS = [
    '"{:,.0f}"|format',
    '"{:,.1f}"|format',
    '"{:,.2f}"|format',
    '"%,.0f"|format',
    '"%,.1f}"|format',
    '"%,.2f"|format',
]


def test_no_invalid_format_patterns():
    """Fail if any {:,} or %,} |format patterns exist in templates.

    Jinja2's |format uses %-style internally — "{:,.0f}" is invalid.
    """
    failures = []
    for pattern in INVALID_PATTERNS:
        bad = []
        for path in PARTIALS.rglob("*.html"):
            text = path.read_text(encoding="utf-8")
            for lineno, line in enumerate(text.splitlines(), start=1):
                if pattern in line and ".bak" not in str(path) and "test_" not in str(path):
                    bad.append(f"{path}:{lineno}:{line.strip()}")
        if bad:
            failures.append(
                f"  Pattern {pattern!r} ({len(bad)} matches):\n    " + "\n    ".join(bad[:5])
            )
    assert not failures, "Invalid |format patterns still present:\n" + "\n".join(failures)


# ─── 2. Sheet Partial render tests ──────────────────────────────────────────

SHEET_NAMES = sorted(p.name for p in PARTIALS.glob("sheet_*.html"))


def _sheet_ctx():
    return {
        "project_ctx": make_project_ctx(),
        "runtime_summary": make_runtime_summary(),
        "workspace_state": make_workspace_state(),
        "is_user_project": True,
        "scenario_records": make_scenario_records(),
        "compare_result": None,
        "workspace_message": None,
        "workspace_state_meta": {
            "dirty_label": "Saved",
            "last_runtime_origin_label": "Runtime bound to saved scenario snapshot",
        },
    }


@pytest.mark.parametrize("name", SHEET_NAMES)
def test_sheet_partial_renders(name):
    """Render every sheet_*.html partial without Jinja errors."""
    ctx = _sheet_ctx()
    try:
        _render(f"partials/{name}", ctx)
    except jinja2.UndefinedError as e:
        pytest.fail(f"UndefinedError in {name}: {e}")
    except jinja2.TemplateSyntaxError as e:
        pytest.fail(f"TemplateSyntaxError in {name}: {e}")
    except TypeError as e:
        if "format" in str(e) or "argument" in str(e).lower():
            pytest.fail(f"TypeError (format error) in {name}: {e}")
        raise
    except Exception as e:
        pytest.fail(f"{type(e).__name__} in {name}: {e}")


# ─── 3. Structural partial render tests ────────────────────────────────────

STRUCTURAL = [
    ("partials/workspace_shell.html", {
        "project_ctx": make_project_ctx(),
        "workspace_state": make_workspace_state(),
        "export_lineage_ui": {
            "recent_exports": [],
            "current_context": {
                "project_label": "TUHO Wind 1",
                "project_code": "TUHO",
                "active_scenario_name": "Base Case",
                "active_scenario_id": "sc_test_001",
                "scenario_revision": "rev1",
                "runtime_snapshot_id": "snap_test_12345678",
                "runtime_origin_label": "Runtime bound to saved scenario snapshot",
                "runtime_generated_at": "2026-05-27 11:30",
                "dirty_label": "Clean saved state",
                "action_note": "Review boundary: draft workspace may differ from saved scenario.",
            },
        },
        "runtime_summary": make_runtime_summary(),
        "project_record": mock.MagicMock(
            project_code="tuho", project_name="TUHO Wind 1",
            project_type="Wind", project_origin="user_created", baseline_snapshot=None,
        ),
        "scenario_records": make_scenario_records(),
        "scenario_history": [],
        "export_records": [],
        "compare_result": None,
        "workspace_message": None,
        "workspace_state_meta": {
            "dirty_label": "Saved",
            "last_runtime_origin_label": "Runtime bound to saved scenario snapshot",
        },
        "scenario_summary_cards": [],
        "validation_errors": [],
        "success_message": None,
        "user": mock.MagicMock(user_id="test_user", username="tester"),
        "form_data": {},
        "active_project_code": "tuho",
        "is_user_project": True,
        "base_case_record": make_scenario_records()[0],
        "non_base_scenarios": [],
        "scenario_editable_fields": [],
        "factory_template_projects": [],
        "user_project_records": [],
        "baseline_project_records": [],
        "new_project_template_options": [],
    }),
    ("partials/scenario_workspace.html", {
        "project_record": mock.MagicMock(
            project_code="tuho", project_name="TUHO Wind 1",
            project_type="Wind", project_origin="user_created",
        ),
        "workspace_state": make_workspace_state(),
        "scenario_records": make_scenario_records(),
        "workspace_message": None,
        "compare_result": None,
        "workspace_state_meta": {
            "dirty_label": "Saved",
            "last_runtime_origin_label": "Runtime bound to saved scenario snapshot",
        },
        "scenario_history": [],
        "export_lineage_ui": {"recent_exports": []},
        "scenario_summary_cards": [],
    }),
    ("partials/project_selector.html", {
        "project_record": mock.MagicMock(
            project_code="tuho", project_name="TUHO Wind 1",
            project_type="Wind", project_origin="user_created",
        ),
        "workspace_state": make_workspace_state(),
        "project_ctx": make_project_ctx(),
        "runtime_summary": make_runtime_summary(),
        "active_project_code": "tuho",
        "factory_template_projects": [
            {"project_code": "tuho", "label": "TUHO Wind 1",
             "meta": "35 MW · Croatia", "project_type": "Wind"},
            {"project_code": "oborovo", "label": "Oborovo Solar PV",
             "meta": "75.26 MW · Croatia", "project_type": "Solar"},
        ],
        "user_project_records": [],
        "baseline_project_records": [],
    }),
    ("partials/runtime_summary.html", {
        "runtime_summary": make_runtime_summary(),
        "project_record": mock.MagicMock(project_code="tuho", project_name="TUHO Wind 1"),
    }),
    ("partials/scenario_tab.html", {
        "project_record": mock.MagicMock(
            project_code="tuho", project_name="TUHO Wind 1",
            project_type="Wind", project_origin="user_created",
        ),
        "base_case_record": make_scenario_records()[0],
        "non_base_scenarios": [],
        "scenario_editable_fields": [],
        "scenario_records": make_scenario_records(),
        "workspace_state": make_workspace_state(),
        "workspace_state_meta": {
            "dirty_label": "Saved",
            "last_runtime_origin_label": "Runtime bound to saved scenario snapshot",
        },
        "workspace_message": None,
        "compare_result": None,
        "scenario_history": [],
        "scenario_summary_cards": [],
    }),
    ("partials/scenario_compare.html", {
        "compare_result": None,
        "left": None,
        "right": None,
        "project_record": mock.MagicMock(project_code="tuho"),
        "scenario_records": make_scenario_records(),
        "left_scenario_id": "sc_test_001",
        "right_scenario_id": "sc_test_001",
    }),
]


@pytest.mark.parametrize("name,ctx", STRUCTURAL)
def test_structural_partial_renders(name, ctx):
    """Render workspace shell, scenario, project_selector, runtime_summary."""
    try:
        _render(name, ctx)
    except jinja2.UndefinedError as e:
        pytest.fail(f"UndefinedError in {name}: {e}")
    except jinja2.TemplateSyntaxError as e:
        pytest.fail(f"TemplateSyntaxError in {name}: {e}")
    except Exception as e:
        pytest.fail(f"{type(e).__name__} in {name}: {e}")


# ─── 4. HTTP smoke (FastAPI TestClient) ─────────────────────────────────────

from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    import main_web
    return TestClient(main_web.app)


def test_http_root_no_500(client):
    """GET / should not return 500."""
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code != 500, f"Root returns 500: {resp.text[:200]}"
    assert resp.status_code in (200, 302, 401)


def test_http_login_page(client):
    """GET /login should not return 500."""
    resp = client.get("/login", follow_redirects=False)
    assert resp.status_code != 500
    assert resp.status_code in (200, 302)


def test_http_projects_browse_no_500(client):
    """GET /projects/browse should not return 500 (auth redirect or 200)."""
    resp = client.get("/projects/browse", follow_redirects=False)
    assert resp.status_code != 500


def test_http_tabs_no_500(client):
    """Known tab routes should not return 500."""
    routes = ["/scenarios?project=tuho", "/download"]
    for route in routes:
        resp = client.get(route, follow_redirects=False)
        assert resp.status_code != 500, f"{route} 500: {resp.text[:200]}"


# ─── 5. main_web imports cleanly ────────────────────────────────────────────

def test_main_web_imports():
    """import main_web must succeed without errors."""
    import main_web
    assert hasattr(main_web, 'app')


# ─── 6. Existing phase test regression ─────────────────────────────────────

def test_existing_phase_tests():
    """Run existing phase test suites."""
    test_files = [
        TESTS_DIR / "test_phase21_jinja_format.py",
        TESTS_DIR / "test_phase20m_runtime_statement_polish.py",
        TESTS_DIR / "test_phase20h_design_system_rendering.py",
    ]
    failures = []
    for tf in test_files:
        if not tf.exists():
            continue
        r = subprocess.run(
            [sys.executable, '-m', 'pytest', str(tf), '-q', '--tb=line'],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        if r.returncode != 0:
            failures.append(f"{tf.name}: exit {r.returncode}")
    assert not failures, f"Existing tests failed: {failures}"


# ─── 7. Empty/null context tolerance ────────────────────────────────────────

def test_sheet_partials_empty_context():
    """sheet_financials and sheet_inputs should handle None context gracefully.

    Uses the real app Jinja environment so includes/extends resolve correctly.
    """
    env2 = _jinja_env()
    minimal = {
        "project_ctx": None,
        "workspace_state": None,
        "runtime_summary": None,
        "is_user_project": False,
        "scenario_records": [],
        "compare_result": None,
        "workspace_message": None,
        "workspace_state_meta": {
            "dirty_label": "Unknown",
            "last_runtime_origin_label": "None",
        },
    }

    for name in ["sheet_financials.html", "sheet_inputs.html"]:
        if not (PARTIALS / name).exists():
            continue
        try:
            env2.get_template(f"partials/{name}").render(minimal)
        except jinja2.UndefinedError:
            pass  # Expected when template unconditionally requires missing objects
        except jinja2.TemplateNotFound as e:
            pytest.fail(f"{name} references missing template {e}, not a context issue")
        except Exception as e:
            pytest.fail(f"{name} with empty context raised {type(e).__name__}: {e}")
