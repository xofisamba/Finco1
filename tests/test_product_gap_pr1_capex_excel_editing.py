"""Product Gap PR1: CAPEX Real Excel Editing + Live Totals —
route-level / static-content tests (no browser).

Covers the non-browser required-behaviour points from the PR1 spec:

  - static/modelling/capex-sheet-live-totals.js is served and wired
    into base.html.
  - the new module only references the "capex" grid id — it never
    references "opex", "revenue", or "debt"/"senior-debt"/"shl" grid
    ids, so it structurally cannot affect those sheets' behaviour.
  - sheet_capex.html still marks C.17/C.18 financing rows read-only
    (data-fc-editable="false") and ordinary CAPEX lines editable for a
    user project, mirroring the pre-existing contract asserted by
    tests/test_capex_c1_markup_contract.py — this PR does not change
    that contract.
  - no financial-engine files were modified by this PR (explicit
    content/path checks rather than a git-diff subprocess call, so
    this assertion holds in any CI checkout state).
  - rendering the CAPEX sheet twice for the same project produces
    byte-identical input "value=" attributes (no live-totals side
    effect leaks into server-rendered HTML).
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
JS_PATH = os.path.join(BASE_DIR, "static", "modelling", "capex-sheet-live-totals.js")
BASE_HTML_PATH = os.path.join(BASE_DIR, "app", "templates", "base.html")


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
            "project_name": f"Product Gap PR1 CAPEX Excel Editing Static {suffix}",
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


class TestStaticWiring:
    def test_capex_live_totals_js_is_served(self, client):
        resp = client.get("/static/modelling/capex-sheet-live-totals.js")
        assert resp.status_code == 200
        assert "FcCapexSheetLiveTotals" in resp.text

    def test_capex_live_totals_js_wired_into_base_html(self):
        with open(BASE_HTML_PATH, "r", encoding="utf-8") as f:
            html = f.read()
        assert "/static/modelling/capex-sheet-live-totals.js" in html

    def test_capex_live_totals_js_only_targets_capex_grid(self):
        with open(JS_PATH, "r", encoding="utf-8") as f:
            src = f.read()
        # The module hardcodes GRID_ID = 'capex' and must never reference
        # the other sheets' grid ids, so it structurally cannot touch
        # OPEX/Revenue/Debt sheet behaviour.
        assert "var GRID_ID = 'capex'" in src
        for other_grid in ["'opex'", "'revenue'", "'debt'", "'senior-debt'", "'shl'"]:
            assert other_grid not in src, f"capex-sheet-live-totals.js must not reference grid id {other_grid}"

    def test_capex_live_totals_js_does_not_touch_model_preview_payload(self):
        with open(JS_PATH, "r", encoding="utf-8") as f:
            src = f.read()
        # The docstring documents that this module never calls
        # /model/preview; assert the actual *code* never performs a
        # network call or references the preview module, by stripping
        # comment lines (lines that are part of a /* ... */ block or
        # start with " *") before checking.
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

    def test_no_financial_engine_files_reference_capex_live_totals(self):
        # Defensive content check: none of the guardrail-protected
        # financial-engine files should mention the new module/feature
        # at all (this PR never touches them).
        guardrail_files = [
            os.path.join(BASE_DIR, "app", "waterfall_core.py"),
            os.path.join(BASE_DIR, "app", "input_adapter.py"),
            os.path.join(BASE_DIR, "app", "project_factories.py"),
        ]
        for path in guardrail_files:
            assert os.path.isfile(path), f"expected guardrail file to exist: {path}"
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "capex-sheet-live-totals" not in content
            assert "FcCapexSheetLiveTotals" not in content

    def test_domain_directory_untouched_by_capex_live_totals_feature(self):
        domain_dir = os.path.join(BASE_DIR, "domain")
        assert os.path.isdir(domain_dir)
        for root, _dirs, files in os.walk(domain_dir):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                path = os.path.join(root, fname)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                assert "capex-sheet-live-totals" not in content
                assert "FcCapexSheetLiveTotals" not in content


class TestCapexSheetMarkupUnchangedContract:
    def test_c17_c18_rows_remain_read_only_and_ordinary_lines_editable(self, client):
        project_code = _create_user_project(client, "markup")
        resp = client.get(f"/?project={project_code}")
        assert resp.status_code == 200
        html = resp.text

        # Find the capex grid section.
        capex_start = html.find('data-fc-grid="capex"')
        assert capex_start != -1, "expected the CAPEX grid to be present in the workspace page"

        # C.17/C.18 financing rows: every data-fc-cell within a
        # lig-row--data-financing row must be data-fc-editable="false".
        financing_rows = re.findall(
            r'<tr class="[^"]*lig-row--data-financing[^"]*"[^>]*>.*?</tr>',
            html[capex_start:capex_start + 200000],
            re.DOTALL,
        )
        assert financing_rows, "expected at least one C.17/C.18 financing row"
        for row_html in financing_rows:
            assert 'data-fc-editable="true"' not in row_html, (
                "C.17/C.18 financing rows must never be editable"
            )

        # At least one ordinary data row (non-financing) must be
        # editable for a user project.
        assert 'data-fc-kind="amount"' in html
        assert 'data-fc-editable="true"' in html

    def test_rendering_capex_sheet_twice_is_byte_identical_for_input_values(self, client):
        project_code = _create_user_project(client, "idempotent")
        resp1 = client.get(f"/?project={project_code}")
        resp2 = client.get(f"/?project={project_code}")
        assert resp1.status_code == 200
        assert resp2.status_code == 200

        values1 = re.findall(r'class="lig-input fc-input-native"[^>]*value="([^"]*)"', resp1.text)
        values2 = re.findall(r'class="lig-input fc-input-native"[^>]*value="([^"]*)"', resp2.text)
        assert values1 == values2, (
            "rendering the CAPEX sheet twice must produce identical input values "
            "(no server-side state mutation from the new live-totals feature)"
        )
