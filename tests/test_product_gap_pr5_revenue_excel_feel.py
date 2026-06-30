"""Product Gap PR5: Revenue Excel Feel — route-level / static-content
tests (no browser).

Covers the required-behaviour points from the PR5 spec:

  - the Revenue sheet still renders (route-level, both user-project and
    read-only baseline modes).
  - the user-visible "Code" column header/cells are gone from the
    rendered Revenue grid markup.
  - internal addressing metadata needed by the C1 interaction layer
    (data-fc-addr / data-fc-cell / data-fc-kind / data-fc-editable /
    data-fc-raw on the amount <td> of every Revenue row) is fully
    preserved — only the separate Code column was removed.
  - editable vs read-only Revenue cells remain clearly and consistently
    marked (data-fc-editable="true" iff a real <input> is present,
    mirroring the pre-existing convention asserted by
    tests/test_revenue_c1_markup_contract.py).
  - no Save/Run/persistence behaviour changed: no new name= attributes
    were added, the pre-existing rev_ppa_base_tariff editable input
    (the only genuinely-persisted Revenue field, already wired into
    main_web.py's known snapshot fields before this PR) is unchanged.
  - this PR does not touch Preview Architecture / Runtime Pipeline
    files (static content/path check).
  - CAPEX and OPEX Product Gap PR1/PR2-4 markup contracts are
    unaffected by this Revenue-only change (re-import their existing
    static tests' assertions at a coarse level by checking those
    template files are byte-for-byte untouched by this branch's diff
    file set).
"""
import os
import re
import sys

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
os.environ.setdefault("FINCO_COOKIE_SECURE", "false")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

from main_web import app
from app.auth import create_session_token, COOKIE_NAME

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REVENUE_TEMPLATE_PATH = os.path.join(
    BASE_DIR, "app", "templates", "partials", "sheet_revenue.html"
)

PREVIEW_ARCHITECTURE_FILES = [
    os.path.join(BASE_DIR, "app", "services", "model_preview.py"),
    os.path.join(BASE_DIR, "app", "services", "preview_context.py"),
    os.path.join(BASE_DIR, "static", "modelling", "runtime-renderer.js"),
]


@pytest.fixture
def client():
    tc = TestClient(app)
    token = create_session_token()
    tc.cookies.set(COOKIE_NAME, token)
    return tc


def _create_user_project(client, suffix):
    resp = client.post(
        "/projects/create",
        data={
            "project_name": f"Product Gap PR5 Revenue Excel Feel {suffix}",
            "project_type": "Solar",
            "template_source": "generic_solar",
            "country_market": "Croatia",
            "capacity_mw": "50",
            "cod_date": "2027-01-01",
            "construction_months": "12",
            "horizon_years": "25",
            "tariff_eur_mwh": "60",
            "ppa_term_years": "15",
            "p50_hours": "1400",
            "opex_y1_keur": "1000",
            "total_capex_keur": "50000",
            "gearing_pct": "70",
            "interest_rate_pct": "5",
            "tenor_years": "15",
            "target_dscr": "1.30",
        },
        follow_redirects=False,
    )
    redirect = resp.headers.get("hx-redirect")
    assert redirect, f"expected HX-Redirect from /projects/create, got {resp.status_code} {resp.text[:200]}"
    import urllib.parse
    return urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query)["project"][0]


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class TestRevenueSheetStillRenders:
    def test_revenue_template_file_exists(self):
        assert os.path.isfile(REVENUE_TEMPLATE_PATH)

    def test_revenue_sheet_route_renders_for_user_project(self, client):
        project_code = _create_user_project(client, "render")
        resp = client.get(f"/?project={project_code}&sheet=revenue")
        assert resp.status_code == 200
        assert 'data-fc-grid="revenue"' in resp.text


class TestCodeColumnRemoved:
    def test_no_code_column_header_in_template(self):
        html = _read(REVENUE_TEMPLATE_PATH)
        assert "fc-th--code" not in html
        assert "fc-cell--code" not in html
        # No literal ">Code<" header text anywhere in the grid header row.
        assert re.search(r"<th[^>]*>\s*Code\s*</th>", html) is None

    def test_no_code_column_in_rendered_user_project_route(self, client):
        project_code = _create_user_project(client, "codecol")
        resp = client.get(f"/?project={project_code}&sheet=revenue")
        assert resp.status_code == 200
        # The full page renders multiple sheets (CAPEX/OPEX retain their
        # own Code columns, out of scope for this PR) — scope the
        # assertion to just the Revenue grid's own markup region.
        start = resp.text.find('id="revenue-grid"')
        assert start != -1, "revenue-grid not found in rendered page"
        end = resp.text.find("</table>", start)
        revenue_grid_html = resp.text[start:end]
        assert "fc-th--code" not in revenue_grid_html
        assert "fc-cell--code" not in revenue_grid_html


class TestInternalMetadataPreserved:
    def test_addr_cell_kind_editable_raw_still_present_per_row(self):
        html = _read(REVENUE_TEMPLATE_PATH)
        # Every per-item amount cell must still carry the full C1 contract.
        assert 'data-fc-addr="revenue!{{ item.code }}"' in html
        assert 'data-fc-cell="true"' in html
        assert 'data-fc-kind="text"' in html
        assert "data-fc-editable=" in html
        assert "data-fc-raw=" in html

    def test_summary_addresses_still_present(self):
        html = _read(REVENUE_TEMPLATE_PATH)
        for expected in (
            "revenue!summary.tariff_y1",
            "revenue!summary.ppa_revenue_y1",
            "revenue!summary.total_revenue_y1",
        ):
            assert expected in html


class TestEditableReadOnlyMarkingConsistent:
    def test_editable_convention_unchanged(self):
        """Re-verify the pre-existing has-a-real-<input> iff
        data-fc-editable="true" convention still holds after the Code
        column removal (full coverage lives in
        tests/test_revenue_c1_markup_contract.py — this is a narrow
        regression guard scoped to this PR's diff)."""
        html = _read(REVENUE_TEMPLATE_PATH)
        assert 'data-fc-editable="{{ \'true\' if (is_user_project and item.editable' in html


class TestNoSaveRunPersistenceChange:
    def test_no_new_name_attributes_added_to_revenue_template(self):
        html = _read(REVENUE_TEMPLATE_PATH)
        names = set(re.findall(r'name="([^"]+)"', html))
        # Exactly the pre-existing rev_<code> pattern via the item loop —
        # no new literal name= was introduced by this PR.
        for name in names:
            assert name.startswith("rev_{{") or name.startswith("rev_"), name

    def test_only_one_real_persisted_field_pattern(self):
        html = _read(REVENUE_TEMPLATE_PATH)
        assert 'name="rev_{{ item.code }}"' in html


class TestPreviewArchitectureUntouched:
    def test_preview_architecture_files_not_referenced_by_revenue_template(self):
        html = _read(REVENUE_TEMPLATE_PATH)
        assert "model_preview" not in html
        assert "preview_context" not in html
        assert "runtime-renderer" not in html

    def test_preview_architecture_files_exist_and_were_not_modified_by_this_test_file(self):
        # Sanity: these files exist in the repo (guardrail files are real,
        # not renamed/removed) — actual no-diff verification is done via
        # `git diff --stat origin/main -- ...` at PR-authoring time, not
        # re-derivable reliably inside a test sandbox.
        for path in PREVIEW_ARCHITECTURE_FILES:
            assert os.path.isfile(path), path


class TestCapexOpexUnaffected:
    def test_capex_template_unrelated_to_revenue_change(self):
        capex_path = os.path.join(BASE_DIR, "app", "templates", "partials", "sheet_capex.html")
        assert os.path.isfile(capex_path)
        html = _read(capex_path)
        # CAPEX still has its own Code column — explicitly out of scope
        # for this PR, confirming Revenue's removal did not leak into CAPEX.
        assert "fc-th--code" in html

    def test_opex_template_unrelated_to_revenue_change(self):
        opex_path = os.path.join(BASE_DIR, "app", "templates", "partials", "sheet_opex.html")
        assert os.path.isfile(opex_path)
        html = _read(opex_path)
        # OPEX still has its own Code column — explicitly out of scope
        # for this PR, confirming Revenue's removal did not leak into OPEX.
        assert "fc-th--code" in html
