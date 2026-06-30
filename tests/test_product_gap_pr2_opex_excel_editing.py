"""Product Gap PR2/PR3/PR4: OPEX Real Excel Editing + Live Operating
Totals — route-level / static-content tests (no browser).

Mirrors tests/test_product_gap_pr1_capex_excel_editing.py's coverage,
adapted to the OPEX grid's actual editable surface (only the Y1
"Budget" cell per non-contingency child line is editable; the Y2..Yn
year cells and contingency-category lines are never editable — see
docs/PRODUCT_GAP_PR2_OPEX_EXCEL_EDITING.md).

Covers:
  - static/modelling/opex-sheet-live-totals.js is served and wired
    into base.html.
  - the new module only references the "opex" grid id — it never
    references "capex"/"revenue"/"debt"/"senior-debt"/"shl" grid ids,
    so it structurally cannot affect those sheets' behaviour.
  - the module's code (comments excluded) never references
    /model/preview, fetch(, or FcRecalcPreview.
  - no financial-engine files were modified by this PR (explicit
    content/path checks).
  - sheet_opex_detail.html still marks contingency-category lines
    read-only and ordinary (non-contingency) lines editable for a user
    project, mirroring the pre-existing C2-PR17 contract — this PR
    does not change that contract.
  - the new Operating Subtotal / Total OPEX (Y1) rows are present and
    correctly marked with data-opex-row.
  - rendering the OPEX sheet twice for the same project produces
    byte-identical input "value=" attributes (no server-side state
    leak).
  - the existing C2-PR18 preview-only governance note still contains
    its required phrases (regression; PR4 only lightly edited the
    copy, see tests/test_c2_pr18_opex_preview_only_governance.py for
    the full check).
"""
import os
import re
import sys
import urllib.parse

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
os.environ.setdefault("FINCO_COOKIE_SECURE", "false")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

from main_web import app
from app.auth import create_session_token, COOKIE_NAME

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS_PATH = os.path.join(BASE_DIR, "static", "modelling", "opex-sheet-live-totals.js")
BASE_HTML_PATH = os.path.join(BASE_DIR, "app", "templates", "base.html")
CAPEX_JS_PATH = os.path.join(BASE_DIR, "static", "modelling", "capex-sheet-live-totals.js")


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
            "project_name": f"Product Gap PR2 OPEX Excel Editing Static {suffix}",
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
    return urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query)["project"][0]


def _create_user_project_with_contingency(client):
    """Duplicate the oborovo factory project (real B.13 contingency
    OPEX category) into an editable user project."""
    resp = client.post(
        "/projects/oborovo/save-as",
        data={"new_project_name": "Product Gap PR2 OPEX contingency check"},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303), f"expected redirect, got {resp.status_code}: {resp.text[:300]}"
    location = resp.headers.get("location")
    assert location, "expected Location header from /projects/oborovo/save-as"
    return urllib.parse.parse_qs(urllib.parse.urlparse(location).query)["project"][0]


class TestStaticWiring:
    def test_opex_live_totals_js_is_served(self, client):
        resp = client.get("/static/modelling/opex-sheet-live-totals.js")
        assert resp.status_code == 200
        assert "FcOpexSheetLiveTotals" in resp.text

    def test_opex_live_totals_js_wired_into_base_html(self):
        with open(BASE_HTML_PATH, "r", encoding="utf-8") as f:
            html = f.read()
        assert "/static/modelling/opex-sheet-live-totals.js" in html

    def test_opex_live_totals_js_only_targets_opex_grid(self):
        with open(JS_PATH, "r", encoding="utf-8") as f:
            src = f.read()
        assert "var GRID_ID = 'opex'" in src
        for other_grid in ["'capex'", "'revenue'", "'debt'", "'senior-debt'", "'shl'"]:
            assert other_grid not in src, f"opex-sheet-live-totals.js must not reference grid id {other_grid}"

    def test_opex_live_totals_js_does_not_touch_model_preview_payload(self):
        with open(JS_PATH, "r", encoding="utf-8") as f:
            src = f.read()
        code_lines = []
        in_block_comment = False
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith("/*"):
                in_block_comment = True
            if in_block_comment:
                if "*/" in stripped:
                    in_block_comment = False
                continue
            if stripped.startswith("*") or stripped.startswith("//"):
                continue
            code_lines.append(line)
        code = "\n".join(code_lines)
        assert "/model/preview" not in code
        assert "fetch(" not in code
        assert "FcRecalcPreview" not in code

    def test_no_financial_engine_files_reference_opex_live_totals(self):
        guardrail_files = [
            os.path.join(BASE_DIR, "app", "waterfall_core.py"),
            os.path.join(BASE_DIR, "app", "input_adapter.py"),
            os.path.join(BASE_DIR, "app", "project_factories.py"),
        ]
        for path in guardrail_files:
            assert os.path.isfile(path), f"expected guardrail file to exist: {path}"
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "opex-sheet-live-totals" not in content
            assert "FcOpexSheetLiveTotals" not in content

    def test_domain_directory_untouched_by_opex_live_totals_feature(self):
        domain_dir = os.path.join(BASE_DIR, "domain")
        assert os.path.isdir(domain_dir)
        for root, _dirs, files in os.walk(domain_dir):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                path = os.path.join(root, fname)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                assert "opex-sheet-live-totals" not in content
                assert "FcOpexSheetLiveTotals" not in content

    def test_capex_live_totals_module_untouched(self):
        # Regression guardrail: this PR must not modify the CAPEX PR1
        # module at all.
        assert os.path.isfile(CAPEX_JS_PATH)
        with open(CAPEX_JS_PATH, "r", encoding="utf-8") as f:
            src = f.read()
        assert "var GRID_ID = 'capex'" in src
        assert "'opex'" not in src


class TestOpexSheetMarkupContract:
    def test_contingency_lines_remain_read_only_and_ordinary_lines_editable(self, client):
        project_code = _create_user_project_with_contingency(client)
        resp = client.get(f"/?project={project_code}")
        assert resp.status_code == 200
        html = resp.text

        budget_cells = re.findall(
            r'data-fc-addr="opex!([^"]*)\.budget"[^>]*data-fc-editable="(true|false)"',
            html,
        )
        assert budget_cells, "expected at least one OPEX budget cell"
        contingency_editable = [c for c in budget_cells if c[0].startswith("B.13") and c[1] == "true"]
        assert contingency_editable == [], "contingency-category OPEX lines must never be editable"
        non_contingency_editable = [c for c in budget_cells if not c[0].startswith("B.13") and c[1] == "true"]
        assert non_contingency_editable, "expected at least one editable non-contingency OPEX budget cell"

    def test_year_columns_remain_read_only(self, client):
        project_code = _create_user_project(client, "year-readonly")
        resp = client.get(f"/?project={project_code}")
        html = resp.text
        year_cells = re.findall(
            r'data-fc-addr="opex![^"]*\.Y\d+"[^>]*data-fc-kind="amount"[^>]*data-fc-editable="(true|false)"',
            html,
        )
        assert year_cells, "expected per-year OPEX cells in the markup"
        assert all(v == "false" for v in year_cells), (
            "OPEX Y1..Yn per-year cells must remain read-only; only the Budget cell is editable"
        )

    def test_operating_subtotal_and_grand_total_rows_present(self, client):
        project_code = _create_user_project(client, "totals-present")
        resp = client.get(f"/?project={project_code}")
        html = resp.text
        assert 'data-opex-row="operating-subtotal"' in html
        assert 'data-opex-row="grand-total"' in html
        assert 'data-fc-addr="opex!operating-subtotal.Y1"' in html
        assert 'data-fc-addr="opex!grand-total.Y1"' in html

    def test_category_subtotal_rows_marked_with_contingency_flag(self, client):
        project_code = _create_user_project_with_contingency(client)
        html = client.get(f"/?project={project_code}").text
        assert 'data-opex-row="cat-subtotal-B.13"' in html
        m = re.search(
            r'data-opex-row="cat-subtotal-B\.13"\s+data-opex-contingency="(true|false)"',
            html,
        )
        assert m and m.group(1) == "true", "B.13 contingency category subtotal must be flagged data-opex-contingency=true"

    def test_rendering_opex_sheet_twice_is_byte_identical_for_input_values(self, client):
        project_code = _create_user_project(client, "idempotent")
        resp1 = client.get(f"/?project={project_code}")
        resp2 = client.get(f"/?project={project_code}")
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        values1 = re.findall(r'class="fc-input-native"[^>]*value="([^"]*)"', resp1.text)
        values2 = re.findall(r'class="fc-input-native"[^>]*value="([^"]*)"', resp2.text)
        assert values1 == values2, (
            "rendering the OPEX sheet twice must produce identical input values "
            "(no server-side state mutation from the new live-totals feature)"
        )

    def test_budget_inputs_still_have_no_name_attribute(self, client):
        # Regression: C2-PR17's persistence boundary must be unchanged.
        project_code = _create_user_project(client, "no-name-attr")
        html = client.get(f"/?project={project_code}").text
        opex_start = html.find('data-fc-grid="opex"')
        assert opex_start != -1
        segment = html[opex_start:opex_start + 400000]
        budget_inputs = re.findall(
            r'<input type="number"[^>]*aria-label="OPEX budget[^>]*>',
            segment,
        )
        assert budget_inputs, "expected at least one OPEX budget <input>"
        for tag in budget_inputs:
            assert "name=" not in tag, "OPEX budget inputs must not have a name= attribute (preview-only, not saved)"


class TestGovernanceNoteStillPresent:
    def test_preview_only_note_still_present_with_required_phrases(self, client):
        project_code = _create_user_project(client, "note-phrases")
        html = client.get(f"/?project={project_code}").text
        assert "preview-only for now" in html
        assert "not saved yet" in html
        assert "Run uses the saved model inputs" in html
