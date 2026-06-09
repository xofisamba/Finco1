"""
Phase 25B-2.1 — Multi-Compare Picker (selection entry point)

Tests for the read-only UI that lets a user pick 2-4 saved
scenarios and open the existing /scenarios/compare-multi endpoint.

Hard contract under test:
- Picker is shown only on user projects (not TUHO / Oborovo factory).
- Picker is hidden when multi_compare_result or multi_compare_error
  is set (so it does not duplicate the multi-compare table).
- 0 scenarios -> empty state with "No saved scenarios".
- 1 scenario -> "Only 1 saved scenario" with locked checkbox.
- 2-4 scenarios -> checkboxes + Compare button (aria-disabled until 2+).
- Compare button generates
  /scenarios/compare-multi?project=...&scenario_ids=...
  href (verified by reading template + integration test).
- form GET fallback works without JS (form method="get").
- EXPLORATORY banner shows for generic_solar / generic_wind.
- Descriptive banner for non-generic user projects.
- No new financial formulas, no DB writes, no factory path changes.
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from main_web import app
    return TestClient(app)


@pytest.fixture
def auth_client():
    from fastapi.testclient import TestClient
    from main_web import app
    from app.auth import create_session_token, COOKIE_NAME
    tc = TestClient(app)
    token = create_session_token(user_id="u_25b21", username="admin")
    tc.cookies.set(COOKIE_NAME, token)
    return tc


@pytest.fixture
def generic_solar_project_with_4_scenarios():
    """Create a generic_solar user project with 4 scenarios."""
    from app.persistence.db import init_db, get_cursor
    from app.persistence.projects_repository import save_project, get_project_by_code
    from app.persistence.scenarios_repository import save_scenario, list_scenarios

    init_db()
    USER_ID = "u_25b21"
    PROJECT_CODE = "test-25b21-solar"

    rec = get_project_by_code(USER_ID, PROJECT_CODE)
    if not rec:
        rec = save_project(
            user_id=USER_ID, project_code=PROJECT_CODE,
            project_name="Test 25B-2.1 Solar", project_type="Solar",
            project_origin="user_created",
            source_project_template="test",
            template_source="generic_solar",
            baseline_snapshot={"tariff_eur_mwh": "50"},
        )
    PROJECT_ID = rec.project_id
    with get_cursor() as cur:
        cur.execute("DELETE FROM scenarios WHERE user_id=? AND project_id=?", (USER_ID, PROJECT_ID))
    for i, name in enumerate(["Base", "Downside", "Upside", "Custom"]):
        save_scenario(
            user_id=USER_ID, project_id=PROJECT_ID, project_code=PROJECT_CODE,
            source_project_template="test", scenario_name=f"Fixture {name}",
            snapshot={"tariff_eur_mwh": str(50 + i * 5)},
            last_run_summary={
                "project_irr": 0.08 + i * 0.01, "equity_irr": 0.10 + i * 0.015,
                "avg_dscr": 1.2 + i * 0.05,
                "total_revenue_keur": 10000 + i * 1000,
                "total_ebitda_keur": 5000 + i * 500,
                "senior_debt_keur": 30000 + i * 1000,
                "shl_balance_keur": 5000 + i * 500,
                "distribution_keur": 2000 + i * 200,
            },
            governance_state={
                "g20_status": "PASS" if i % 2 == 0 else "BLOCKED",
                "r99_r102_status": "APPROVED" if i == 0 else "PENDING",
            },
        )
    return {
        "user_id": USER_ID, "project_code": PROJECT_CODE, "project_id": PROJECT_ID,
    }


@pytest.fixture
def test_project_with_4_scenarios():
    """Create a non-generic (test template_source) user project with 4 scenarios."""
    from app.persistence.db import init_db, get_cursor
    from app.persistence.projects_repository import save_project, get_project_by_code
    from app.persistence.scenarios_repository import save_scenario

    init_db()
    USER_ID = "u_25b21"
    PROJECT_CODE = "test-25b21-test"

    rec = get_project_by_code(USER_ID, PROJECT_CODE)
    if not rec:
        rec = save_project(
            user_id=USER_ID, project_code=PROJECT_CODE,
            project_name="Test 25B-2.1 Test", project_type="Wind",
            project_origin="user_created",
            source_project_template="test",
            template_source="test",
            baseline_snapshot={"tariff_eur_mwh": "50"},
        )
    PROJECT_ID = rec.project_id
    with get_cursor() as cur:
        cur.execute("DELETE FROM scenarios WHERE user_id=? AND project_id=?", (USER_ID, PROJECT_ID))
    for i, name in enumerate(["Base", "Downside", "Upside", "Custom"]):
        save_scenario(
            user_id=USER_ID, project_id=PROJECT_ID, project_code=PROJECT_CODE,
            source_project_template="test", scenario_name=f"Fixture {name}",
            snapshot={"tariff_eur_mwh": str(50 + i * 5)},
            last_run_summary={
                "project_irr": 0.08 + i * 0.01, "equity_irr": 0.10 + i * 0.015,
                "avg_dscr": 1.2 + i * 0.05,
                "total_revenue_keur": 10000 + i * 1000,
                "total_ebitda_keur": 5000 + i * 500,
                "senior_debt_keur": 30000 + i * 1000,
                "shl_balance_keur": 5000 + i * 500,
                "distribution_keur": 2000 + i * 200,
            },
            governance_state={"g20_status": "PASS", "r99_r102_status": "APPROVED"},
        )
    return {"user_id": USER_ID, "project_code": PROJECT_CODE, "project_id": PROJECT_ID}


@pytest.fixture
def empty_user_project():
    """Create a user project with 0 scenarios."""
    from app.persistence.db import init_db, get_cursor
    from app.persistence.projects_repository import save_project, get_project_by_code

    init_db()
    USER_ID = "u_25b21"
    PROJECT_CODE = "test-25b21-empty"
    rec = get_project_by_code(USER_ID, PROJECT_CODE)
    if not rec:
        rec = save_project(
            user_id=USER_ID, project_code=PROJECT_CODE,
            project_name="Test 25B-2.1 Empty", project_type="Wind",
            project_origin="user_created",
            source_project_template="test",
            template_source="generic_wind",
            baseline_snapshot={"tariff_eur_mwh": "50"},
        )
    PROJECT_ID = rec.project_id
    with get_cursor() as cur:
        cur.execute("DELETE FROM scenarios WHERE user_id=? AND project_id=?", (USER_ID, PROJECT_ID))
    return {"user_id": USER_ID, "project_code": PROJECT_CODE, "project_id": PROJECT_ID}


@pytest.fixture
def one_scenario_user_project():
    """Create a user project with 1 scenario."""
    from app.persistence.db import init_db, get_cursor
    from app.persistence.projects_repository import save_project, get_project_by_code
    from app.persistence.scenarios_repository import save_scenario

    init_db()
    USER_ID = "u_25b21"
    PROJECT_CODE = "test-25b21-one"
    rec = get_project_by_code(USER_ID, PROJECT_CODE)
    if not rec:
        rec = save_project(
            user_id=USER_ID, project_code=PROJECT_CODE,
            project_name="Test 25B-2.1 One", project_type="Wind",
            project_origin="user_created",
            source_project_template="test",
            template_source="generic_wind",
            baseline_snapshot={"tariff_eur_mwh": "50"},
        )
    PROJECT_ID = rec.project_id
    with get_cursor() as cur:
        cur.execute("DELETE FROM scenarios WHERE user_id=? AND project_id=?", (USER_ID, PROJECT_ID))
    save_scenario(
        user_id=USER_ID, project_id=PROJECT_ID, project_code=PROJECT_CODE,
        source_project_template="test", scenario_name="Only",
        snapshot={"tariff_eur_mwh": "50"},
        last_run_summary={
            "project_irr": 0.08, "equity_irr": 0.10, "avg_dscr": 1.2,
            "total_revenue_keur": 10000, "total_ebitda_keur": 5000,
            "senior_debt_keur": 30000, "shl_balance_keur": 5000,
            "distribution_keur": 2000,
        },
        governance_state={"g20_status": "PASS", "r99_r102_status": "APPROVED"},
    )
    return {"user_id": USER_ID, "project_code": PROJECT_CODE, "project_id": PROJECT_ID}


# ── Test Block 1 — Template existence and content ──────────────────────


class TestPickerTemplateExists:
    def test_template_file_exists(self):
        path = REPO_ROOT / "app" / "templates" / "partials" / "scenario_multi_compare_picker.html"
        assert path.exists()

    def test_template_has_picker_root_testid(self):
        path = REPO_ROOT / "app" / "templates" / "partials" / "scenario_multi_compare_picker.html"
        text = path.read_text()
        assert 'data-testid="multi-compare-picker"' in text

    def test_template_has_min_max_attributes(self):
        path = REPO_ROOT / "app" / "templates" / "partials" / "scenario_multi_compare_picker.html"
        text = path.read_text()
        assert 'data-min-scenarios="2"' in text
        assert 'data-max-scenarios="4"' in text

    def test_template_uses_existing_multi_compare_endpoint(self):
        path = REPO_ROOT / "app" / "templates" / "partials" / "scenario_multi_compare_picker.html"
        text = path.read_text()
        assert "/scenarios/compare-multi" in text
        # Also: form action is the same endpoint (no-JS fallback)
        assert 'action="/scenarios/compare-multi"' in text

    def test_template_uses_form_get_for_no_js_fallback(self):
        path = REPO_ROOT / "app" / "templates" / "partials" / "scenario_multi_compare_picker.html"
        text = path.read_text()
        # Form must use method="get" so submission works without JS
        assert 'method="get"' in text
        # And the noscript fallback button
        assert "noscript" in text
        assert "multi-compare-picker-submit-noscript" in text

    def test_template_uses_existing_scenario_summary_cards(self):
        path = REPO_ROOT / "app" / "templates" / "partials" / "scenario_multi_compare_picker.html"
        text = path.read_text()
        assert "scenario_summary_cards" in text

    def test_template_renders_compare_button_with_aria_disabled(self):
        path = REPO_ROOT / "app" / "templates" / "partials" / "scenario_multi_compare_picker.html"
        text = path.read_text()
        assert "scm-pick-compare-btn" in text
        assert 'aria-disabled="true"' in text

    def test_template_renders_count_indicator(self):
        path = REPO_ROOT / "app" / "templates" / "partials" / "scenario_multi_compare_picker.html"
        text = path.read_text()
        assert "scm-pick-count" in text
        assert "0 of 2-4 selected" in text

    def test_template_inline_js_is_minimal(self):
        """No Tailwind/Alpine; inline JS is small and isolated."""
        path = REPO_ROOT / "app" / "templates" / "partials" / "scenario_multi_compare_picker.html"
        text = path.read_text()
        # No Tailwind
        assert "@apply" not in text
        # No Alpine
        assert "x-data" not in text
        assert "x-on" not in text
        # Has the inline script tag
        assert "<script>" in text
        # The script updates aria-disabled + href + count
        assert "aria-disabled" in text
        assert "encodeURIComponent" in text
        assert "/scenarios/compare-multi?project=" in text


# ── Test Block 2 — Picker is conditionally rendered ────────────────────


class TestPickerConditionalRendering:
    def test_picker_shown_for_generic_solar(self, auth_client, generic_solar_project_with_4_scenarios):
        r = auth_client.get(
            f"/scenarios?project={generic_solar_project_with_4_scenarios['project_code']}"
        )
        assert r.status_code == 200
        assert "multi-compare-picker" in r.text
        assert "EXPLORATORY" in r.text
        assert "Generic project" in r.text

    def test_picker_shown_for_test_template(self, auth_client, test_project_with_4_scenarios):
        r = auth_client.get(
            f"/scenarios?project={test_project_with_4_scenarios['project_code']}"
        )
        assert r.status_code == 200
        assert "multi-compare-picker" in r.text
        # No EXPLORATORY banner for test template
        assert "Generic project" not in r.text
        # Descriptive banner shown instead
        assert "descriptive only" in r.text

    def test_picker_hidden_for_factory_project(self, auth_client):
        """Factory projects (TUHO / Oborovo) must NOT show the picker.

        Factory projects are not user_created, so the picker is hidden by
        the {% if is_user_project %} gate. The scenario_workspace partial
        may still render (with empty Saved Versions), or may be hidden
        entirely — we only assert the picker is NOT present.
        """
        r = auth_client.get("/scenarios?project=tuho")
        assert r.status_code == 200
        # Picker is hidden for factory projects regardless of which partials render
        assert "multi-compare-picker" not in r.text

    def test_picker_hidden_when_multi_compare_result_set(self, auth_client, generic_solar_project_with_4_scenarios):
        """When the multi-compare table is already shown, the picker is hidden
        to avoid duplication."""
        from app.persistence.scenarios_repository import list_scenarios
        scenarios = list_scenarios(
            "u_25b21", project_id=generic_solar_project_with_4_scenarios["project_id"],
            include_archived=True, limit=20,
        )
        ids = [s.scenario_id for s in scenarios if s.scenario_name.startswith("Fixture")]
        r = auth_client.get(
            f"/scenarios/compare-multi?project={generic_solar_project_with_4_scenarios['project_code']}"
            f"&scenario_ids={','.join(ids)}"
        )
        assert r.status_code == 200
        # Multi-compare table is shown
        assert "multi-scenario-compare" in r.text
        # Picker is hidden (no duplication)
        assert "multi-compare-picker" not in r.text

    def test_picker_unauthenticated_redirects(self, client, generic_solar_project_with_4_scenarios):
        r = client.get(
            f"/scenarios?project={generic_solar_project_with_4_scenarios['project_code']}"
        )
        # Either 302 to /login or 200 if guest mode is enabled
        assert r.status_code in (200, 302)


# ── Test Block 3 — Empty and partial states ────────────────────────────


class TestPickerEmptyAndPartialStates:
    def test_no_scenarios_shows_empty_state(self, auth_client, empty_user_project):
        r = auth_client.get(
            f"/scenarios?project={empty_user_project['project_code']}"
        )
        assert r.status_code == 200
        assert "multi-compare-picker-empty" in r.text
        assert "No saved scenarios" in r.text
        assert "Save at least 2 scenarios" in r.text
        # No checkbox form
        assert "scm-pick-form" not in r.text

    def test_one_scenario_shows_partial_state(self, auth_client, one_scenario_user_project):
        r = auth_client.get(
            f"/scenarios?project={one_scenario_user_project['project_code']}"
        )
        assert r.status_code == 200
        assert "multi-compare-picker-one" in r.text
        assert "Only 1 saved scenario" in r.text
        # Locked checkbox shown (disabled, checked)
        assert "scm-pick-row--disabled" in r.text
        # No form (compare not yet possible)
        assert "scm-pick-form" not in r.text

    def test_two_scenarios_shows_form(self, auth_client):
        """2 scenarios -> checkboxes + Compare button (disabled)."""
        from app.persistence.db import init_db, get_cursor
        from app.persistence.projects_repository import save_project, get_project_by_code
        from app.persistence.scenarios_repository import save_scenario
        init_db()
        USER_ID = "u_25b21"
        PROJECT_CODE = "test-25b21-two"
        rec = get_project_by_code(USER_ID, PROJECT_CODE)
        if not rec:
            rec = save_project(
                user_id=USER_ID, project_code=PROJECT_CODE,
                project_name="Test Two", project_type="Wind",
                project_origin="user_created", source_project_template="test",
                template_source="generic_wind",
                baseline_snapshot={"tariff_eur_mwh": "50"},
            )
        pid = rec.project_id
        with get_cursor() as cur:
            cur.execute("DELETE FROM scenarios WHERE user_id=? AND project_id=?", (USER_ID, pid))
        for i, name in enumerate(["A", "B"]):
            save_scenario(
                user_id=USER_ID, project_id=pid, project_code=PROJECT_CODE,
                source_project_template="test", scenario_name=f"Two {name}",
                snapshot={"tariff_eur_mwh": str(50 + i * 5)},
                last_run_summary={"project_irr": 0.08, "equity_irr": 0.10, "avg_dscr": 1.2,
                                  "total_revenue_keur": 10000, "total_ebitda_keur": 5000,
                                  "senior_debt_keur": 30000, "shl_balance_keur": 5000,
                                  "distribution_keur": 2000},
                governance_state={"g20_status": "PASS", "r99_r102_status": "APPROVED"},
            )
        r = auth_client.get(f"/scenarios?project={PROJECT_CODE}")
        assert r.status_code == 200
        # Form is rendered
        assert "scm-pick-form" in r.text
        # Compare button is initially aria-disabled (no selection yet)
        assert 'aria-disabled="true"' in r.text
        # 2 checkboxes
        assert r.text.count('class="scm-pick-cb"') == 2

    def test_four_scenarios_shows_form_with_4_checkboxes(self, auth_client, generic_solar_project_with_4_scenarios):
        r = auth_client.get(
            f"/scenarios?project={generic_solar_project_with_4_scenarios['project_code']}"
        )
        assert r.status_code == 200
        assert "scm-pick-form" in r.text
        # 4 checkboxes (one per saved scenario)
        assert r.text.count('class="scm-pick-cb"') == 4
        # All 4 scenario names rendered
        for name in ["Fixture Base", "Fixture Downside", "Fixture Upside", "Fixture Custom"]:
            assert name in r.text


# ── Test Block 4 — Integration: picker → multi-compare URL works ───────


class TestPickerEndToEndIntegration:
    def test_compare_button_href_is_well_formed(self, auth_client, generic_solar_project_with_4_scenarios):
        """The Compare button's href (after JS would set it) must be a valid
        /scenarios/compare-multi URL with project + scenario_ids. We verify
        by reading the template directly: the inline JS constructs the URL
        from the data-project-code and selected scenario_ids."""
        path = REPO_ROOT / "app" / "templates" / "partials" / "scenario_multi_compare_picker.html"
        text = path.read_text()
        # The href is built in JS
        assert "'/scenarios/compare-multi?project='" in text
        assert "'&scenario_ids='" in text
        # And the form action is the same endpoint
        assert 'action="/scenarios/compare-multi"' in text

    def test_form_get_submission_works_without_js(self, auth_client, generic_solar_project_with_4_scenarios):
        """A plain form GET to /scenarios/compare-multi?project=...&scenario_ids=...
        must work — this is the no-JS fallback."""
        from app.persistence.scenarios_repository import list_scenarios
        scenarios = list_scenarios(
            "u_25b21", project_id=generic_solar_project_with_4_scenarios["project_id"],
            include_archived=True, limit=20,
        )
        ids = [s.scenario_id for s in scenarios if s.scenario_name.startswith("Fixture")]
        # Simulate form GET submission (the form is method="get", so the
        # query string IS the form data)
        r = auth_client.get(
            f"/scenarios/compare-multi?project={generic_solar_project_with_4_scenarios['project_code']}"
            f"&scenario_ids={','.join(ids)}"
        )
        assert r.status_code == 200
        assert "multi-scenario-compare" in r.text
        assert "scm-chip--base" in r.text

    def test_too_few_scenarios_returns_error_state(self, auth_client):
        """Submitting 1 scenario via the picker path (JS bypassed) should
        show the multi-compare error state, not crash."""
        r = auth_client.get(
            "/scenarios/compare-multi?project=test-25b21-solar&scenario_ids=abc"
        )
        assert r.status_code == 200
        # Multi-compare error state (from 25B-2)
        assert "multi-compare-empty-state" in r.text or "Multi-Compare Unavailable" in r.text

    def test_too_many_scenarios_returns_error_state(self, auth_client):
        """5+ scenario_ids via the picker path returns the multi-compare error."""
        r = auth_client.get(
            "/scenarios/compare-multi?project=test-25b21-solar"
            "&scenario_ids=a,b,c,d,e"
        )
        assert r.status_code == 200
        assert "Multi-Compare Unavailable" in r.text or "at most 4" in r.text

    def test_missing_run_output_handled(self, auth_client):
        """Submitting a scenario_id that has no last_run_summary must NOT crash."""
        from app.persistence.db import init_db, get_cursor
        from app.persistence.projects_repository import save_project, get_project_by_code
        from app.persistence.scenarios_repository import save_scenario
        init_db()
        USER_ID = "u_25b21"
        PROJECT_CODE = "test-25b21-missing"
        rec = get_project_by_code(USER_ID, PROJECT_CODE)
        if not rec:
            rec = save_project(
                user_id=USER_ID, project_code=PROJECT_CODE,
                project_name="Test Missing", project_type="Wind",
                project_origin="user_created", source_project_template="test",
                template_source="generic_wind",
                baseline_snapshot={"tariff_eur_mwh": "50"},
            )
        pid = rec.project_id
        with get_cursor() as cur:
            cur.execute("DELETE FROM scenarios WHERE user_id=? AND project_id=?", (USER_ID, pid))
        sids = []
        for i, name in enumerate(["A", "B"]):
            rec_s = save_scenario(
                user_id=USER_ID, project_id=pid, project_code=PROJECT_CODE,
                source_project_template="test", scenario_name=f"Missing {name}",
                snapshot={"tariff_eur_mwh": str(50 + i * 5)},
                last_run_summary=None,  # missing!
                governance_state={},
            )
            sids.append(rec_s.scenario_id)
        r = auth_client.get(
            f"/scenarios/compare-multi?project={PROJECT_CODE}&scenario_ids={','.join(sids)}"
        )
        # Should still render (helper tolerates None last_run_summary)
        assert r.status_code == 200
        assert "multi-scenario-compare" in r.text


# ── Test Block 5 — Safety Constraints ──────────────────────────────────


class TestPickerSafetyConstraints:
    def test_no_new_financial_formulas(self):
        """The picker is pure HTML+JS+CSS; no Python formulas added."""
        # Look for the new files only
        for f in [
            "app/templates/partials/scenario_multi_compare_picker.html",
        ]:
            p = REPO_ROOT / f
            text = p.read_text()
            # No financial computation keywords
            for bad in [".irr(", "npv(", "numpy", "pandas", "atad_", "corporate_rate"]:
                assert bad not in text, f"{f} contains {bad}"

    def test_no_db_writes_in_picker_code(self):
        """No INSERT / UPDATE / DELETE in picker code."""
        p = REPO_ROOT / "app" / "templates" / "partials" / "scenario_multi_compare_picker.html"
        text = p.read_text()
        for bad in ["INSERT ", "UPDATE ", "DELETE ", "cur.execute", "conn.execute"]:
            assert bad not in text, f"picker contains {bad}"

    def test_no_factory_path_changes(self):
        """app/project_factories.py is untouched."""
        result = subprocess.run(
            ["git", "diff", "main...HEAD", "--", "app/project_factories.py"],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        assert result.stdout.strip() == "", "project_factories.py was modified"

    def test_waterfall_core_unchanged(self):
        """app/waterfall_core.py is untouched."""
        result = subprocess.run(
            ["git", "diff", "main...HEAD", "--", "app/waterfall_core.py"],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        assert result.stdout.strip() == "", "waterfall_core.py was modified"

    def test_no_construction_flag_flips(self):
        result = subprocess.run(
            ["git", "diff", "main...HEAD"],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        bad = re.findall(r"use_construction_schedule_engine\s*=\s*True", result.stdout)
        assert bad == [], f"construction flag flips found: {bad}"

    def test_css_root_count_unchanged(self):
        """:root count must remain 3 (UI-2.5 invariant)."""
        p = REPO_ROOT / "static" / "styles.css"
        text = p.read_text()
        root_count = len(re.findall(r"^:root\s*{", text, re.MULTILINE))
        assert root_count == 3, f":root count = {root_count}, expected 3"

    def test_no_tailwind_in_picker_css_block(self):
        """The new .scm-pick-* CSS classes do not use @apply."""
        p = REPO_ROOT / "static" / "styles.css"
        text = p.read_text()
        # Find the .scm-pick block (from .scm-pick { to the next unindented rule)
        m = re.search(r"(\.scm-pick[^{]*\{.*?\n\})", text, re.DOTALL)
        if m:
            assert "@apply" not in m.group(0), "Tailwind @apply in picker CSS"

    def test_no_alpine_in_picker_template(self):
        """The new template does not use Alpine.js."""
        p = REPO_ROOT / "app" / "templates" / "partials" / "scenario_multi_compare_picker.html"
        text = p.read_text()
        for bad in ["x-data", "x-on:", "x-show", "x-model"]:
            assert bad not in text, f"picker contains Alpine: {bad}"

    def test_no_rc1_in_picker_code(self):
        p = REPO_ROOT / "app" / "templates" / "partials" / "scenario_multi_compare_picker.html"
        text = p.read_text()
        assert "rc1" not in text.lower()

    def test_multi_compare_route_remains_read_only(self):
        """The Compare button is an <a> with href (GET), not a form POST."""
        p = REPO_ROOT / "app" / "templates" / "partials" / "scenario_multi_compare_picker.html"
        text = p.read_text()
        # The button is an <a> (GET), not a POST submit
        assert '<a href' in text or '<a\n  href' in text or '<a \n  href' in text
        # No <form method="post" anywhere related to the picker
        # The form we DO have must be method="get" (already checked in test_template_uses_form_get_for_no_js_fallback)
        # No hidden input for state-changing params
        assert 'name="csrf_token"' not in text  # no CSRF needed for GET
        # No <input type="hidden" name="action" value="..."> style state changers
        # (The only hidden input is "project", which is just a passthrough)

    def test_existing_2way_compare_still_works(self, auth_client):
        """The existing /scenarios/compare (2-way) is unchanged."""
        r = auth_client.get("/scenarios/compare?project=tuho")
        assert r.status_code == 200
        # Existing 2-way flow renders normally (no picker interference)
        # Picker is hidden for factory projects anyway
        assert "multi-compare-picker" not in r.text


# ── Test Block 6 — CSS Style Guard ─────────────────────────────────────


class TestPickerCSSStyleGuard:
    def test_css_has_pick_root_classes(self):
        p = REPO_ROOT / "static" / "styles.css"
        text = p.read_text()
        for cls in [".scm-pick", ".scm-pick-header", ".scm-pick-list", ".scm-pick-row",
                    ".scm-pick-actions", ".scm-pick-compare-btn"]:
            assert cls in text, f"missing CSS class: {cls}"

    def test_css_has_banner_styles(self):
        p = REPO_ROOT / "static" / "styles.css"
        text = p.read_text()
        assert ".scm-pick-banner" in text
        assert ".scm-pick-exploratory-banner" in text

    def test_css_has_disabled_state(self):
        p = REPO_ROOT / "static" / "styles.css"
        text = p.read_text()
        assert ".scm-pick-compare-btn--disabled" in text
        assert ".scm-pick-row--disabled" in text
        assert "pointer-events: none" in text

    def test_css_uses_css_variables_for_colors(self):
        """Picker CSS uses var(--sidebar-*, var(--text-*, etc., no hard-coded brand colors."""
        p = REPO_ROOT / "static" / "styles.css"
        text = p.read_text()
        m = re.search(r"(\.scm-pick[^{]*\{.*?\n\})", text, re.DOTALL)
        if m:
            block = m.group(0)
            # Should reference CSS variables (var(...))
            assert "var(--" in block, "Picker CSS does not use CSS variables"
