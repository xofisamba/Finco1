"""Phase 25B-2: 3-Way / 4-Way Generic Scenario Compare tests.

This is the second deliverable from the 24-H closure review
recommendation (Phase 25B -- Generic UX Polish). It extends
the existing 2-way scenario compare surface to support a
multi-scenario compare view (Base / Downside / Upside / Custom)
in a single read-only table with deltas vs Base.

Hard constraints verified:
- generic exploratory path only
- no factory path changes (app/project_factories.py zero diff)
- no waterfall_core changes
- no Tailwind / Alpine
- no new financial formulas
- no persistence side effects
- no construction / C10 / R-PAR promotion
- rc1 untouched
- :root count = 3 (UI-2.5 invariant)

Test blocks (52 tests):

1. **TestMultiCompareHelper_PureUnit (12 tests).**
   The compare_multi_scenarios() helper.
2. **TestMultiCompareRoute_GET (12 tests).**
   The GET /scenarios/compare-multi endpoint.
3. **TestMultiCompareUI_Template (8 tests).**
   The partials/scenario_compare_multi.html template.
4. **TestMultiCompareSafety_Constraints (8 tests).**
   No factory leakage, no waterfall changes, no rc1.
5. **TestMultiCompareIntegration_EndToEnd (8 tests).**
   Full user journey + edge cases.
6. **TestMultiCompareCSS_StyleGuard (4 tests).**
   CSS classes + invariants.
"""

from __future__ import annotations

import os
import re
import sys
from copy import deepcopy
from pathlib import Path

import pytest

# Set test-friendly env vars BEFORE importing main_web
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only-25b2")
os.environ.setdefault("FINCO_COOKIE_SECURE", "false")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

MAIN_WEB = REPO_ROOT / "main_web.py"
MULTI_PARTIAL = REPO_ROOT / "app" / "templates" / "partials" / "scenario_compare_multi.html"
SCENARIO_WORKSPACE = REPO_ROOT / "app" / "templates" / "partials" / "scenario_workspace.html"
STYLES_CSS = REPO_ROOT / "static" / "styles.css"
WATERFALL_CORE = REPO_ROOT / "app" / "waterfall_core.py"
PROJECT_FACTORIES = REPO_ROOT / "app" / "project_factories.py"
EXPORTS_REPO = REPO_ROOT / "app" / "persistence" / "exports_repository.py"


# ── Helpers ──────────────────────────────────────────────────────────────

def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """Plain (unauthenticated) TestClient."""
    from fastapi.testclient import TestClient
    from main_web import app
    return TestClient(app)


@pytest.fixture
def auth_client():
    """Authenticated TestClient with a valid session cookie."""
    from fastapi.testclient import TestClient
    from main_web import app
    from app.auth import create_session_token, COOKIE_NAME
    tc = TestClient(app)
    token = create_session_token(user_id="u_25b2", username="admin")
    tc.cookies.set(COOKIE_NAME, token)
    return tc


@pytest.fixture
def four_scenarios():
    """Create a project + 4 scenarios for the auth user, return scenario IDs."""
    from app.persistence.db import init_db, get_cursor
    init_db()
    from app.persistence.projects_repository import save_project, get_project_by_code
    from app.persistence.scenarios_repository import save_scenario, list_scenarios

    USER_ID = "u_25b2"
    PROJECT_CODE = "test-25b2-fixture"

    rec = get_project_by_code(USER_ID, PROJECT_CODE)
    if not rec:
        rec = save_project(
            user_id=USER_ID,
            project_code=PROJECT_CODE,
            project_name="Test 25B-2",
            project_type="Wind",
            project_origin="user_created",
            source_project_template="test",
            baseline_snapshot={"tariff_eur_mwh": "50"},
        )
    PROJECT_ID = rec.project_id

    # Always clear stale scenarios from this user + project so the fixture
    # is deterministic and self-contained. Other suites may have left
    # empty / "No Summary" / "Empty Metadata" rows in the same DB.
    with get_cursor() as cur:
        cur.execute(
            "DELETE FROM scenarios WHERE user_id = ? AND project_id = ?",
            (USER_ID, PROJECT_ID),
        )

    existing = list_scenarios(USER_ID, project_id=PROJECT_ID, include_archived=True, limit=10)
    if len(existing) < 4:
        for i, name in enumerate(["Base", "Downside", "Upside", "Custom"][len(existing):]):
            idx = len(existing) + i
            save_scenario(
                user_id=USER_ID,
                project_id=PROJECT_ID,
                project_code=PROJECT_CODE,
                source_project_template="test",
                scenario_name=f"Fixture {name}",
                snapshot={"tariff_eur_mwh": str(50 + idx * 5)},
                last_run_summary={
                    "project_irr": 0.08 + idx * 0.01,
                    "equity_irr": 0.10 + idx * 0.015,
                    "avg_dscr": 1.2 + idx * 0.05,
                    "min_dscr": 1.0 + idx * 0.05,
                    "total_revenue_keur": 10000 + idx * 1000,
                    "total_ebitda_keur": 5000 + idx * 500,
                    "senior_debt_keur": 30000 + idx * 1000,
                    "shl_balance_keur": 5000 + idx * 500,
                    "distribution_keur": 2000 + idx * 200,
                },
                governance_state={
                    "g20_status": "PASS" if idx % 2 == 0 else "BLOCKED",
                    "r99_r102_status": "APPROVED" if idx == 0 else "PENDING",
                },
            )
    existing = list_scenarios(USER_ID, project_id=PROJECT_ID, include_archived=True, limit=20)
    # Prefer the 4 fixture scenarios (Base/Downside/Upside/Custom) in name order
    name_order = ["Fixture Base", "Fixture Downside", "Fixture Upside", "Fixture Custom"]
    by_name = {s.scenario_name: s for s in existing}
    chosen = [by_name[n] for n in name_order if n in by_name]
    if len(chosen) < 4:
        # Fallback: take any 4 (shouldn't normally happen)
        chosen = existing[:4]
    return {
        "user_id": USER_ID,
        "project_id": PROJECT_ID,
        "project_code": PROJECT_CODE,
        "scenario_ids": [s.scenario_id for s in chosen],
    }


# ── Test Block 1 — Helper (Pure Unit) ───────────────────────────────────

class TestMultiCompareHelper_PureUnit:
    """The compare_multi_scenarios() helper is the source of truth."""

    def test_helper_min_scenarios_constant(self):
        """MULTI_COMPARE_MIN_SCENARIOS = 2."""
        from app.persistence.exports_repository import MULTI_COMPARE_MIN_SCENARIOS
        assert MULTI_COMPARE_MIN_SCENARIOS == 2

    def test_helper_max_scenarios_constant(self):
        """MULTI_COMPARE_MAX_SCENARIOS = 4."""
        from app.persistence.exports_repository import MULTI_COMPARE_MAX_SCENARIOS
        assert MULTI_COMPARE_MAX_SCENARIOS == 4

    def test_helper_metric_order_has_10(self):
        """MULTI_COMPARE_METRIC_ORDER has 10 metrics."""
        from app.persistence.exports_repository import MULTI_COMPARE_METRIC_ORDER
        assert len(MULTI_COMPARE_METRIC_ORDER) == 10

    def test_helper_metric_labels_match_order(self):
        """Labels are defined for every metric key."""
        from app.persistence.exports_repository import (
            MULTI_COMPARE_METRIC_ORDER, MULTI_COMPARE_METRIC_LABELS,
        )
        for k in MULTI_COMPARE_METRIC_ORDER:
            assert k in MULTI_COMPARE_METRIC_LABELS

    def test_helper_rejects_too_few(self):
        """Returns None for <2 scenarios."""
        from app.persistence.exports_repository import compare_multi_scenarios
        assert compare_multi_scenarios("u_25b2", []) is None
        assert compare_multi_scenarios("u_25b2", ["x"]) is None

    def test_helper_rejects_too_many(self):
        """Returns None for >4 scenarios."""
        from app.persistence.exports_repository import compare_multi_scenarios
        assert compare_multi_scenarios("u_25b2", ["a", "b", "c", "d", "e"]) is None

    def test_helper_rejects_duplicates(self):
        """Returns None for duplicate scenario_ids."""
        from app.persistence.exports_repository import compare_multi_scenarios
        assert compare_multi_scenarios("u_25b2", ["a", "a"]) is None
        assert compare_multi_scenarios("u_25b2", ["a", "b", "a"]) is None

    def test_helper_rejects_unresolved(self):
        """Returns None when any scenario_id cannot be resolved."""
        from app.persistence.exports_repository import compare_multi_scenarios
        assert compare_multi_scenarios("u_25b2", ["nonexistent_aaaa", "nonexistent_bbbb"]) is None

    def test_helper_returns_dict_shape(self, four_scenarios):
        """Successful call returns dict with required keys."""
        from app.persistence.exports_repository import compare_multi_scenarios
        ids = four_scenarios["scenario_ids"][:2]
        result = compare_multi_scenarios(four_scenarios["user_id"], ids)
        assert result is not None
        for k in ("scenarios", "base_scenario_id", "metrics", "governance_rows"):
            assert k in result

    def test_helper_metrics_have_values_deltas_sign_classes(self, four_scenarios):
        """Each metric row has values[], deltas[], sign_classes[] (length N)."""
        from app.persistence.exports_repository import compare_multi_scenarios
        ids = four_scenarios["scenario_ids"]
        result = compare_multi_scenarios(four_scenarios["user_id"], ids)
        n = len(ids)
        for row in result["metrics"]:
            assert len(row["values"]) == n
            assert len(row["deltas"]) == n
            assert len(row["sign_classes"]) == n

    def test_helper_deltas_zero_for_base_column(self, four_scenarios):
        """The first scenario (base) always has delta=0 + sign_class=zero or n/a."""
        from app.persistence.exports_repository import compare_multi_scenarios
        ids = four_scenarios["scenario_ids"]
        result = compare_multi_scenarios(four_scenarios["user_id"], ids)
        for row in result["metrics"]:
            if row["deltas"][0] is not None:
                assert abs(row["deltas"][0]) < 1e-9
                assert row["sign_classes"][0] == "scm-delta--zero"
            else:
                # If base has no value, delta is n/a (legitimate behaviour)
                assert row["sign_classes"][0] == "scm-delta--na"

    def test_helper_sign_classes_are_valid(self, four_scenarios):
        """All sign_class values are in the allowed set."""
        from app.persistence.exports_repository import compare_multi_scenarios
        ids = four_scenarios["scenario_ids"]
        result = compare_multi_scenarios(four_scenarios["user_id"], ids)
        allowed = {"scm-delta--pos", "scm-delta--neg", "scm-delta--zero", "scm-delta--na"}
        for row in result["metrics"]:
            for sc in row["sign_classes"]:
                assert sc in allowed, f"unexpected sign class: {sc}"


# ── Test Block 2 — Route (GET /scenarios/compare-multi) ─────────────────

class TestMultiCompareRoute_GET:
    """The GET /scenarios/compare-multi endpoint."""

    def test_route_registered(self):
        """The route is registered."""
        from main_web import app
        paths = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/scenarios/compare-multi" in paths

    def test_unauthenticated_redirects_to_login(self, client):
        """Unauthenticated GET returns 302."""
        r = client.get("/scenarios/compare-multi?scenario_ids=sc1,sc2", follow_redirects=False)
        assert r.status_code == 302

    def test_empty_scenario_ids_returns_error_state(self, auth_client):
        """Empty scenario_ids returns 200 with 'Multi-Compare Unavailable'."""
        r = auth_client.get("/scenarios/compare-multi?scenario_ids=")
        assert r.status_code == 200
        assert "Multi-Compare Unavailable" in r.text

    def test_too_few_scenarios_returns_error(self, auth_client):
        """1 scenario returns 'needs at least 2'."""
        r = auth_client.get("/scenarios/compare-multi?scenario_ids=fake_only_one")
        assert r.status_code == 200
        assert "needs at least 2" in r.text

    def test_too_many_scenarios_returns_error(self, auth_client):
        """5 scenarios returns 'at most 4'."""
        r = auth_client.get(
            "/scenarios/compare-multi?scenario_ids=a,b,c,d,e"
        )
        assert r.status_code == 200
        assert "at most 4" in r.text

    def test_duplicates_returns_error(self, auth_client):
        """Duplicate scenario_ids returns 'duplicate' error."""
        r = auth_client.get("/scenarios/compare-multi?scenario_ids=a,a")
        assert r.status_code == 200
        assert "duplicate" in r.text

    def test_unresolved_scenarios_returns_error(self, auth_client):
        """Unresolved scenario_ids returns 'could not be resolved' error."""
        r = auth_client.get(
            "/scenarios/compare-multi?scenario_ids=nonexistent_aaaaaaaa,another_nonexistent"
        )
        assert r.status_code == 200
        assert "could not be resolved" in r.text

    def test_two_scenarios_renders_table(self, auth_client, four_scenarios):
        """2 scenarios renders the multi-compare table."""
        ids = four_scenarios["scenario_ids"][:2]
        r = auth_client.get(f"/scenarios/compare-multi?scenario_ids={','.join(ids)}")
        assert r.status_code == 200
        assert "scm-multi-table" in r.text
        assert "scm-chip--base" in r.text

    def test_four_scenarios_renders_table(self, auth_client, four_scenarios):
        """4 scenarios renders the multi-compare table."""
        ids = four_scenarios["scenario_ids"]
        r = auth_client.get(f"/scenarios/compare-multi?scenario_ids={','.join(ids)}")
        assert r.status_code == 200
        assert "scm-multi-table" in r.text
        assert "scm-chip--base" in r.text
        # Delta tokens should be present
        assert any(c in r.text for c in ["scm-delta--pos", "scm-delta--neg", "scm-delta--zero"])

    def test_response_includes_all_metric_labels(self, auth_client, four_scenarios):
        """Response has all 10 metric labels."""
        ids = four_scenarios["scenario_ids"]
        r = auth_client.get(f"/scenarios/compare-multi?scenario_ids={','.join(ids)}")
        assert r.status_code == 200
        for label in (
            "Revenue", "OPEX", "EBITDA", "CAPEX",
            "Senior Debt", "SHL", "Avg DSCR",
            "Project IRR", "Equity IRR", "Distributions",
        ):
            assert label in r.text, f"missing label: {label}"

    def test_response_includes_governance_rows(self, auth_client, four_scenarios):
        """Response has g20_status and r99_r102_status governance rows."""
        ids = four_scenarios["scenario_ids"]
        r = auth_client.get(f"/scenarios/compare-multi?scenario_ids={','.join(ids)}")
        assert r.status_code == 200
        assert "g20_status" in r.text
        assert "r99_r102_status" in r.text
        assert "scm-multi-row--gov" in r.text

    def test_response_includes_base_chip_marker(self, auth_client, four_scenarios):
        """The first scenario is marked with the 'Base' badge + chip--base class."""
        ids = four_scenarios["scenario_ids"]
        r = auth_client.get(f"/scenarios/compare-multi?scenario_ids={','.join(ids)}")
        assert r.status_code == 200
        assert "scm-chip--base" in r.text
        assert 'data-testid="scm-chip-base"' in r.text


# ── Test Block 3 — UI Template ──────────────────────────────────────────

class TestMultiCompareUI_Template:
    """The partials/scenario_compare_multi.html template."""

    def test_template_exists(self):
        """The template file exists."""
        assert MULTI_PARTIAL.exists()

    def test_template_has_testid_root(self):
        """The template has data-testid='multi-scenario-compare'."""
        text = _read_text(MULTI_PARTIAL)
        assert 'data-testid="multi-scenario-compare"' in text

    def test_template_has_empty_state(self):
        """The template has the 'Multi-Compare Unavailable' empty state."""
        text = _read_text(MULTI_PARTIAL)
        assert "Multi-Compare Unavailable" in text
        assert "multi-compare-empty-state" in text

    def test_template_has_exploratory_banner(self):
        """The template has the EXPLORATORY banner for generic projects."""
        text = _read_text(MULTI_PARTIAL)
        assert "scm-multi-exploratory-banner" in text
        assert "EXPLORATORY" in text
        assert "not Excel-parity validated" in text

    def test_template_has_base_banner(self):
        """The template has the descriptive banner for non-exploratory projects."""
        text = _read_text(MULTI_PARTIAL)
        assert "scm-multi-banner" in text
        assert "descriptive only" in text

    def test_template_has_scenario_chips(self):
        """The template has the Base + variant chips with testid."""
        text = _read_text(MULTI_PARTIAL)
        assert "scm-chip--base" in text
        assert "scm-chip" in text
        assert 'data-testid="scm-chip-base"' in text
        assert 'data-testid="scm-chip-variant"' in text

    def test_template_has_metric_table(self):
        """The template has the metric table with head row + data rows."""
        text = _read_text(MULTI_PARTIAL)
        assert "scm-multi-table" in text
        assert "scm-multi-row--head" in text
        assert "scm-multi-metric" in text
        assert "Deltas vs Base" in text

    def test_template_has_governance_rows(self):
        """The template has the governance rows (g20 + r99/r102)."""
        text = _read_text(MULTI_PARTIAL)
        assert "scm-multi-row--gov" in text
        assert "governance_rows" in text

    def test_template_uses_bracket_access_for_dict(self):
        """The template uses row['values'] to avoid Jinja2 dict.values() confusion."""
        text = _read_text(MULTI_PARTIAL)
        # At least 3 instances of bracket access
        assert text.count("['values']") >= 2
        assert text.count("['deltas']") >= 1
        assert text.count("['sign_classes']") >= 1
        # Should NOT use bare row.values
        assert "row.values" not in text
        assert "row.deltas" not in text
        assert "row.sign_classes" not in text


# ── Test Block 4 — Safety Constraints ──────────────────────────────────

class TestMultiCompareSafety_Constraints:
    """Hard-constraint guard tests."""

    def test_helper_no_factory_leakage(self, four_scenarios):
        """Helper does NOT return factory inputs directly."""
        from app.persistence.exports_repository import compare_multi_scenarios
        ids = four_scenarios["scenario_ids"]
        result = compare_multi_scenarios(four_scenarios["user_id"], ids)
        # No factory-shaped fields should appear
        assert "create_default_tuho_wind1" not in str(result)
        assert "create_default_oborovo" not in str(result)

    def test_helper_rejects_unrelated_user(self, four_scenarios):
        """Scenarios from another user cannot be compared (returns None)."""
        from app.persistence.exports_repository import compare_multi_scenarios
        ids = four_scenarios["scenario_ids"]
        # A different user_id should get None (scenarios belong to u_25b2)
        result = compare_multi_scenarios("unrelated_user_9999", ids)
        assert result is None

    def test_construction_flag_still_false(self):
        """app/waterfall_core.py still defaults to False."""
        text = _read_text(WATERFALL_CORE)
        m = re.search(
            r"getattr\(inputs\.info,\s*[\"\']use_construction_schedule_engine[\"\']\s*,\s*False\)",
            text,
        )
        assert m

    def test_no_rc1_in_route(self):
        """The new route + helper do not mention rc1 in code."""
        main_text = _read_text(MAIN_WEB)
        # Find the route block
        m = re.search(
            r"# ── Phase 25B-2.*?@app\.post\(\"/scenarios/save\"\)",
            main_text, re.DOTALL,
        )
        assert m, "Phase 25B-2 route block not found"
        block = m.group(0)
        assert "rc1" not in block.lower()
        # Helper file
        repo_text = _read_text(EXPORTS_REPO)
        # Find the helper block (between compare_multi_scenarios and the next def)
        m2 = re.search(
            r"def compare_multi_scenarios.*?^def ",
            repo_text, re.DOTALL | re.MULTILINE,
        )
        assert m2
        helper_block = m2.group(0)
        assert "rc1" not in helper_block.lower()

    def test_css_root_count_unchanged(self):
        """:root count is still 3 in static/styles.css."""
        text = _read_text(STYLES_CSS)
        root_count = len(re.findall(r"^:root\s*\{", text, re.MULTILINE))
        assert root_count == 3

    def test_no_new_financial_formulas(self):
        """The helper does NOT introduce new financial formulas."""
        repo_text = _read_text(EXPORTS_REPO)
        m = re.search(
            r"def compare_multi_scenarios.*?^def ",
            repo_text, re.DOTALL | re.MULTILINE,
        )
        assert m
        helper_block = m.group(0)
        # No math operations beyond subtraction
        for forbidden in [r"\.irr\(", r"npv\(", r"xirr\(",
                          r"import numpy", r"import pandas"]:
            assert not re.search(forbidden, helper_block), f"leaked: {forbidden}"
        # No tax / debt / IDC
        for bad in ["corporate_rate", "atad_", "shl_pik", "use_construction"]:
            assert bad not in helper_block, f"leaked: {bad}"

    def test_no_construction_flag_flips(self):
        """Diff vs main does not flip use_construction_schedule_engine to True."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "main...HEAD"],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        bad = re.findall(
            r"use_construction_schedule_engine\s*=\s*True",
            result.stdout,
        )
        assert not bad

    def test_factory_factories_unchanged(self):
        """app/project_factories.py has zero diff vs main."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "main...HEAD", "--", "app/project_factories.py"],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        assert result.stdout == "", (
            f"project_factories.py was modified: {result.stdout[:500]}"
        )


# ── Test Block 5 — End-to-End Integration ──────────────────────────────

class TestMultiCompareIntegration_EndToEnd:
    """Full user journey + edge cases."""

    def test_exploratory_banner_for_generic_project(self, auth_client, four_scenarios):
        """EXPLORATORY banner appears when the project is generic_solar/generic_wind."""
        from app.persistence.projects_repository import get_project_by_code
        from app.persistence.projects_repository import save_project
        rec = get_project_by_code(four_scenarios["user_id"], four_scenarios["project_code"])
        save_project(
            user_id=rec.user_id,
            project_code=rec.project_code,
            project_name=rec.project_name,
            project_type=rec.project_type,
            project_origin=rec.project_origin,
            source_project_template=rec.source_project_template or "test",
            template_source="generic_solar",
            baseline_snapshot=dict(rec.baseline_snapshot or {}),
        )
        ids = four_scenarios["scenario_ids"]
        r = auth_client.get(
            f"/scenarios/compare-multi?project={four_scenarios['project_code']}&scenario_ids={','.join(ids)}"
        )
        assert r.status_code == 200
        assert "scm-multi-exploratory-banner" in r.text
        assert "EXPLORATORY" in r.text

    def test_non_exploratory_banner_for_test_project(self, auth_client, four_scenarios):
        """Non-exploratory banner appears for non-generic template_source."""
        # Ensure template_source is 'test' (not generic_*)
        from app.persistence.projects_repository import get_project_by_code, save_project
        rec = get_project_by_code(four_scenarios["user_id"], four_scenarios["project_code"])
        save_project(
            user_id=rec.user_id,
            project_code=rec.project_code,
            project_name=rec.project_name,
            project_type=rec.project_type,
            project_origin=rec.project_origin,
            source_project_template="test",
            baseline_snapshot=dict(rec.baseline_snapshot or {}),
        )
        ids = four_scenarios["scenario_ids"]
        r = auth_client.get(
            f"/scenarios/compare-multi?project={four_scenarios['project_code']}&scenario_ids={','.join(ids)}"
        )
        assert r.status_code == 200
        assert "scm-multi-banner" in r.text
        assert "descriptive only" in r.text
        assert "scm-multi-exploratory-banner" not in r.text

    def test_three_scenarios_renders(self, auth_client, four_scenarios):
        """3 scenarios renders the table correctly."""
        ids = four_scenarios["scenario_ids"][:3]
        r = auth_client.get(f"/scenarios/compare-multi?scenario_ids={','.join(ids)}")
        assert r.status_code == 200
        assert "scm-multi-table" in r.text
        # No scm-multi-exploratory-banner (template_source is 'test')
        assert "scm-multi-exploratory-banner" not in r.text

    def test_missing_run_output_shows_soft_note(self, auth_client, four_scenarios):
        """A scenario with no last_run_summary shows the soft-error note."""
        # Create a 2nd scenario with no last_run_summary
        from app.persistence.scenarios_repository import save_scenario
        sid_no_summary = save_scenario(
            user_id=four_scenarios["user_id"],
            project_id=four_scenarios["project_id"],
            project_code=four_scenarios["project_code"],
            source_project_template="test",
            scenario_name="No Summary",
            snapshot={"tariff_eur_mwh": "99"},
            last_run_summary=None,  # missing!
        )
        # Compare base + this no-summary scenario
        ids = [four_scenarios["scenario_ids"][0], sid_no_summary.scenario_id]
        r = auth_client.get(f"/scenarios/compare-multi?scenario_ids={','.join(ids)}")
        assert r.status_code == 200
        # Should still render (helper tolerates None last_run_summary)
        assert "scm-multi-table" in r.text

    def test_deltas_have_correct_signs(self, auth_client, four_scenarios):
        """Deltas have the right sign (positive for higher values)."""
        ids = four_scenarios["scenario_ids"]
        r = auth_client.get(f"/scenarios/compare-multi?scenario_ids={','.join(ids)}")
        assert r.status_code == 200
        # For Revenue, scenarios 2,3,4 have higher values than 1 -> deltas positive
        # Look for "scm-delta--pos" tokens
        assert "scm-delta--pos" in r.text

    def test_four_scenario_chips_have_correct_count(self, auth_client, four_scenarios):
        """Four scenarios produce 1 base chip + 3 variant chips."""
        ids = four_scenarios["scenario_ids"]
        r = auth_client.get(f"/scenarios/compare-multi?scenario_ids={','.join(ids)}")
        assert r.status_code == 200
        # 1 base + 3 variants
        assert r.text.count('class="scm-chip"') >= 3
        assert r.text.count("scm-chip--base") >= 1
        # 3 "vs" separators between 4 chips
        assert r.text.count("scm-chip-vs") == 3

    def test_route_does_not_modify_db(self, auth_client, four_scenarios):
        """The route is read-only — no DB writes happen."""
        from app.persistence.scenarios_repository import get_scenario
        ids = four_scenarios["scenario_ids"]
        before = {sid: get_scenario(sid, four_scenarios["user_id"]) for sid in ids}
        r = auth_client.get(f"/scenarios/compare-multi?scenario_ids={','.join(ids)}")
        assert r.status_code == 200
        after = {sid: get_scenario(sid, four_scenarios["user_id"]) for sid in ids}
        # updated_at should be unchanged
        for sid in ids:
            assert before[sid].updated_at == after[sid].updated_at
            assert before[sid].last_run_summary == after[sid].last_run_summary

    def test_route_does_not_crash_on_missing_run_metadata(self, auth_client, four_scenarios):
        """A scenario with no last_run_summary / no governance_state does not crash."""
        from app.persistence.scenarios_repository import save_scenario
        # Create a 2nd scenario with empty last_run_summary
        sid_empty = save_scenario(
            user_id=four_scenarios["user_id"],
            project_id=four_scenarios["project_id"],
            project_code=four_scenarios["project_code"],
            source_project_template="test",
            scenario_name="Empty Metadata",
            snapshot={"tariff_eur_mwh": "77"},
            last_run_summary={},
            governance_state={},
        )
        ids = [four_scenarios["scenario_ids"][0], sid_empty.scenario_id]
        r = auth_client.get(f"/scenarios/compare-multi?scenario_ids={','.join(ids)}")
        assert r.status_code == 200
        assert "scm-multi-table" in r.text


# ── Test Block 6 — CSS Style Guard ─────────────────────────────────────

class TestMultiCompareCSS_StyleGuard:
    """CSS invariants."""

    def test_css_has_scm_multi_roots(self):
        """CSS has .scm-multi-* root classes."""
        text = _read_text(STYLES_CSS)
        assert ".scm-multi-compare" in text
        assert ".scm-multi-heading" in text
        assert ".scm-multi-table" in text
        assert ".scm-multi-row" in text

    def test_css_has_chip_styles(self):
        """CSS has .scm-chip and .scm-chip--base styles."""
        text = _read_text(STYLES_CSS)
        assert ".scm-chip" in text
        assert ".scm-chip--base" in text
        assert ".scm-chip-vs" in text

    def test_css_has_delta_sign_classes(self):
        """CSS has delta sign classes (pos / neg / zero / na)."""
        text = _read_text(STYLES_CSS)
        assert ".scm-delta--pos" in text
        assert ".scm-delta--neg" in text
        assert ".scm-delta--zero" in text
        assert ".scm-delta--na" in text

    def test_no_tailwind_or_alpine(self):
        """No Tailwind @apply or Alpine x-data."""
        text = _read_text(STYLES_CSS)
        # Check the multi-compare CSS block specifically
        multi_idx = text.find(".scm-multi-compare")
        assert multi_idx > 0
        multi_block = text[multi_idx:]
        assert "@apply" not in multi_block
        assert "x-data" not in multi_block
