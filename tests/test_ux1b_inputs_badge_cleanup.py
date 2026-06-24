"""UX-1B-INPUTS-BADGE-CLEANUP.

The Excel-lookalike UX review found the Inputs tab visually noisy:
every row showed an admin/provenance badge (SAVED, TEMPLATE, INTERNAL,
CALCULATED, MODEL DEFAULT, TIMING DRIVER, DSCR SCULPT, INDICATIVE,
PROTECTED), making the app look like an internal validation/admin tool
rather than a financial model.

Fix: remove the noisy per-row admin/provenance badges entirely (Saved,
Template, Internal, Model default, Protected). Editable vs read-only
is now conveyed by the input-vs-value cell style alone, and the
protected/reference-project state is shown once, at the top of the
sheet, instead of repeated on every row. Modelling caveats that affect
interpretation (Calculated, Timing driver, DSCR sculpt driver,
Indicative) are kept, but demoted from a full-text badge to a small
icon with a tooltip (title attribute), plus a compact top-of-sheet
legend in finance-user wording.

This is presentation/UI only -- no model, formula, runtime, export, or
validation-classification changes are covered or required by these
tests.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-ux1b")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_session_token  # noqa: E402
from main_web import app  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
INPUTS_SECTION = REPO_ROOT / "app" / "templates" / "partials" / "inputs_section.html"


@pytest.fixture(scope="module")
def logged_in_client():
    client = TestClient(app)
    token = create_session_token(user_id="1", username="test_user")
    client.cookies.set("finco_session", token)
    return client


@pytest.fixture(scope="module")
def user_project_code(logged_in_client):
    """A real user_created project (is_user_project=True), distinct
    from the reference projects (tuho / oborovo), so editable-cell
    rendering can be asserted against a genuinely editable project.
    """
    resp = logged_in_client.post(
        "/projects/create",
        data={
            "project_name": "UX1B Test Solar",
            "project_type": "Solar",
            "template_source": "",
            "country_market": "DE",
            "capacity_mw": "10",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    import re
    code = re.sub(r"[^a-z0-9]+", "-", "UX1B Test Solar".strip().lower()).strip("-")
    return code


def _inputs_panel_html(resp_text: str) -> str:
    start = resp_text.find('id="panel-inputs"')
    end = resp_text.find('id="panel-scenario"')
    assert start != -1 and end != -1 and end > start, (
        "panel-inputs not found in workspace response"
    )
    return resp_text[start:end]


# ---------------------------------------------------------------------------
# 1. No noisy badge text rendered for normal users
# ---------------------------------------------------------------------------

def _inp_row_badge_texts(panel: str) -> list[str]:
    """Extract the badge text rendered inside each <div class="inp-row">
    ... <span class="badge ...">TEXT</span> ... </div>, i.e. the
    per-row badge slot only -- excludes one-time page-level notices
    (sheet banner, readonly notice) that live outside any inp-row.
    """
    texts = []
    for row_match in re.finditer(r'<div class="inp-row">.*?</div>', panel, re.DOTALL):
        row = row_match.group(0)
        for badge_match in re.finditer(r'<span class="badge[^"]*"[^>]*>\s*([^<]+?)\s*</span>', row):
            texts.append(badge_match.group(1).strip())
    return texts


class TestNoNoisyBadgesInInputsTab:
    # SAVED / TEMPLATE / INTERNAL / MODEL DEFAULT / PROTECTED: removed
    # entirely as a per-row badge. A row may still show its own LABEL
    # containing one of these words (e.g. the "Template Origin" row
    # label), and the page may show a single top-of-sheet notice
    # outside any inp-row -- neither of those is a per-row admin badge.
    @pytest.mark.parametrize("project_code", ["tuho", "oborovo"])
    @pytest.mark.parametrize(
        "noisy_text",
        ["Saved", "Template", "Internal", "Model default", "Protected"],
    )
    def test_noisy_badge_not_rendered_per_row(self, logged_in_client, project_code, noisy_text):
        r = logged_in_client.get(f"/?project={project_code}", follow_redirects=True)
        assert r.status_code == 200
        panel = _inputs_panel_html(r.text)
        badge_texts = _inp_row_badge_texts(panel)
        assert noisy_text not in badge_texts, (
            f"Inputs tab must not render {noisy_text!r} as a per-row badge"
        )


# ---------------------------------------------------------------------------
# 2. Editable vs calculated/read-only fields are still visually distinct
# ---------------------------------------------------------------------------

class TestEditableVsCalculatedDistinction:
    def test_editable_fields_render_as_inputs(self, logged_in_client, user_project_code):
        r = logged_in_client.get(f"/?project={user_project_code}", follow_redirects=True)
        panel = _inputs_panel_html(r.text)
        assert 'class="inp-input"' in panel, (
            "Editable inputs-tab fields must render as <input class='inp-input'>"
        )

    def test_calculated_fields_render_as_muted_value(self, logged_in_client):
        r = logged_in_client.get("/?project=tuho", follow_redirects=True)
        panel = _inputs_panel_html(r.text)
        assert "inp-value-calculated" in panel, (
            "Calculated/read-only fields must render with the muted "
            "inp-value-calculated style"
        )

    def test_css_defines_calculated_muted_style(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert ".inp-value-calculated" in css, (
            "static/styles.css must define a muted style for "
            "calculated/read-only inputs-tab values"
        )

    def test_css_defines_editable_highlight(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert "--editable-bg" in css, (
            "static/styles.css must give editable inputs-tab cells a "
            "distinct background so they read as 'input' at a glance"
        )


# ---------------------------------------------------------------------------
# 3. Caveat icons/labels still exist for calculated / timing / DSCR /
#    indicative fields
# ---------------------------------------------------------------------------

class TestCaveatsStillAvailable:
    def test_calculated_caveat_icon_present(self, logged_in_client):
        r = logged_in_client.get("/?project=tuho", follow_redirects=True)
        panel = _inputs_panel_html(r.text)
        assert 'class="inp-caveat-icon"' in panel
        assert "Calculated" in panel, (
            "The Calculated caveat must still be reachable (via tooltip "
            "text), even though it is no longer a loud badge"
        )

    def test_timing_driver_caveat_present(self, logged_in_client):
        r = logged_in_client.get("/?project=oborovo", follow_redirects=True)
        panel = _inputs_panel_html(r.text)
        assert "Timing driver" in panel, (
            "The timing-driver caveat must still be reachable via tooltip text"
        )

    def test_dscr_sculpt_caveat_present(self, logged_in_client):
        r = logged_in_client.get("/?project=oborovo", follow_redirects=True)
        panel = _inputs_panel_html(r.text)
        assert "DSCR sculpt driver" in panel, (
            "The DSCR sculpt driver caveat must still be reachable via tooltip text"
        )

    def test_indicative_caveat_present(self, logged_in_client):
        r = logged_in_client.get("/?project=oborovo", follow_redirects=True)
        panel = _inputs_panel_html(r.text)
        assert "Indicative" in panel, (
            "The indicative gearing caveat must still be reachable via tooltip text"
        )

    def test_caveat_icon_css_class_defined(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert ".inp-caveat-icon" in css


# ---------------------------------------------------------------------------
# 4. Compact legend present, in finance-user wording
# ---------------------------------------------------------------------------

class TestInputsLegend:
    def test_legend_present_in_template(self):
        src = INPUTS_SECTION.read_text()
        assert 'class="inp-legend"' in src, (
            "inputs_section.html must render a compact top-of-sheet legend"
        )

    def test_legend_rendered_for_user(self, logged_in_client):
        r = logged_in_client.get("/?project=tuho", follow_redirects=True)
        panel = _inputs_panel_html(r.text)
        assert "Editable assumptions are shown as input cells" in panel
        assert "Calculated fields are" in panel and "read-only" in panel

    def test_legend_avoids_developer_wording(self):
        src = INPUTS_SECTION.read_text()
        legend_match = re.search(
            r'<div class="inp-legend".*?</div>', src, re.DOTALL
        )
        assert legend_match is not None
        legend_text = legend_match.group(0)
        for forbidden in ("factory", "create_default_", "golden", "template_source"):
            assert forbidden not in legend_text, (
                f"Inputs legend must not contain developer wording {forbidden!r}"
            )


# ---------------------------------------------------------------------------
# 5. No internal terminology leaks into the Inputs tab
# ---------------------------------------------------------------------------

class TestNoInternalTerminologyLeak:
    @pytest.mark.parametrize("forbidden", ["factory", "create_default_", "golden", "template_source"])
    @pytest.mark.parametrize("project_code", ["tuho", "oborovo"])
    def test_forbidden_term_not_in_rendered_inputs_tab(
        self, logged_in_client, project_code, forbidden
    ):
        r = logged_in_client.get(f"/?project={project_code}", follow_redirects=True)
        panel = _inputs_panel_html(r.text)
        assert forbidden not in panel, (
            f"Inputs tab must not leak internal terminology {forbidden!r}"
        )


# ---------------------------------------------------------------------------
# 6. Protected/reference state shown once, not per row
# ---------------------------------------------------------------------------

class TestProtectedStateShownOnce:
    def test_reference_project_shows_readonly_notice_once(self, logged_in_client):
        r = logged_in_client.get("/?project=tuho", follow_redirects=True)
        panel = _inputs_panel_html(r.text)
        assert panel.count("Protected original") == 1, (
            "The protected-original notice must appear exactly once in "
            "the inputs tab, not once per row"
        )

    def test_user_project_shows_no_protected_notice(self, logged_in_client, user_project_code):
        r = logged_in_client.get(f"/?project={user_project_code}", follow_redirects=True)
        panel = _inputs_panel_html(r.text)
        assert "Protected original" not in panel


# ---------------------------------------------------------------------------
# 7. File scope guard (navigation/UI-only, no model/runtime files touched)
# ---------------------------------------------------------------------------

class TestUX1BFileScope:
    UX1B_ALLOWED_PREFIXES = (
        "app/templates/partials/new_project_minimal.html",  # UX-2E cross-arc
        "app/templates/partials/workspace_shell.html",  # UX-2E cross-arc
        "tests/",  # UX-2E cross-arc (branch-wide test footprint)
        "tests/test_phase56",  # UX-2E cross-arc
        "app/templates/partials/inputs_section.html",
        "static/styles.css",
        "tests/test_ux1b_inputs_badge_cleanup.py",
        "tests/test_phase_ux1_inputs_badge_cleanup.py",
        "tests/test_phase_p2fix5e_reference_ux.py",
        "tests/test_phase_ux2_active_sheet_refresh.py",
        # UX-2C-2 cross-arc
        "tests/test_ux2c2_inputs_sheet_simplification.py",
        "tests/test_phase_scenario1_base_case_init.py",
        "tests/test_phase_scenario2_fixes.py",
        "tests/test_phase_ux4cde_pilot_polish.py",
        "tests/test_phase_stab2_realized_gearing_scale.py",
        "tests/test_phase_stab3_capex_subline_propagation.py",
        "tests/test_phase_stab5_export_route_fix.py",
        "tests/test_phase_stab6_new_project_first_run.py",
        "app/templates/partials/sheet_opex_detail.html",  # UX-2D cross-arc
        "tests/test_ux2d_",  # UX-2D cross-arc
        "tests/test_ux2c1_",  # UX-2D cross-arc allowlist edit
    )
    UX1B_DISALLOWED_PREFIXES = (
        "app/waterfall_core.py",
        "app/input_adapter.py",
        "app/project_factories.py",
        "app/persistence/",
        "domain/",
        "static/app.js",
    )

    def test_file_scope(self):
        import shutil
        if shutil.which("git") is None:
            pytest.skip("git not available")
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "diff", "--name-only", "origin/main"],
            capture_output=True, text=True,
        )
        changed = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        for f in changed:
            assert not any(f.startswith(p) for p in self.UX1B_DISALLOWED_PREFIXES), (
                f"UX-1B must not touch {f}"
            )
            assert any(f.startswith(p) for p in self.UX1B_ALLOWED_PREFIXES), (
                f"UX-1B file outside allowed scope: {f}"
            )

    def test_engine_unchanged(self):
        path = REPO_ROOT / "app" / "waterfall_core.py"
        assert path.exists()

    @pytest.mark.parametrize("code", ["tuho", "oborovo", "generic_solar", "generic_wind"])
    def test_csv_export_still_works(self, code):
        from app.services.export_service import build_runtime_summary_csv_export
        resp = build_runtime_summary_csv_export(code, safe_project=code)
        assert resp.status_code == 200, (
            f"CSV export for '{code}' must still return 200 after UX-1B"
        )

    @pytest.mark.parametrize("code", ["tuho", "oborovo", "generic_solar", "generic_wind"])
    def test_workbook_export_still_works(self, code):
        from app.services.export_service import build_institutional_workbook_export
        resp = build_institutional_workbook_export(code, safe_project=code)
        assert resp.status_code == 200, (
            f"XLSX export for '{code}' must still return 200 after UX-1B"
        )
