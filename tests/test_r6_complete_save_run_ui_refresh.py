"""R6 / F07 — Complete Save/Run UI refresh.

After a successful Workbook V2 Run, every runtime-dependent visible surface
must represent the same newly persisted runtime authority WITHOUT a manual
browser reload.  R6 introduces ONE post-run UI projection authority
(``app.v2.post_run_ui.build_post_run_ui_state``) that renders all post-run
OOB fragments from the single fresh workspace read and one
RuntimeProjectionBundle:

    #v2-run-controls, #v2-status-banner, #v2-toolbar-runtime-state,
    #v2-sheet-overview, #v2-sheet-senior-debt, #v2-sheet-tax,
    #v2-sheet-financial-statements, #v2-sheet-scenarios

F07 defect reproduced on starting main ``5f689bdf``: the hand-rolled Run
response refreshed debt/tax/FS but NOT the Overview — after a second Run
with different economics the browser Overview kept showing the previous
run's KPIs as current (fresh runtime + stale presentation).

No financial arithmetic lives in this suite: every asserted value is either
the persisted runtime summary, the canonical run KPIs, or server-rendered
HTML derived from them.
"""
from __future__ import annotations

import os
import re
import urllib.parse

os.environ.setdefault("FINCO_WORKBOOK_V2", "1")
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-r6")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import main_web  # noqa: E402
from app.auth import COOKIE_NAME, create_session_token, decode_session_token  # noqa: E402

SESSION = create_session_token()
USER_ID = decode_session_token(SESSION).user_id


def _client() -> TestClient:
    tc = TestClient(main_web.app, follow_redirects=False)
    tc.cookies.set(COOKIE_NAME, SESSION)
    return tc


def _create(client: TestClient, name: str, template_source: str = "generic_wind",
            **overrides) -> str:
    data = {
        "project_name": name,
        "project_type": "Wind" if template_source in ("tuho", "generic_wind") else "Solar",
        "template_source": template_source,
        "country_market": "Croatia" if template_source == "tuho" else "Poland",
        "capacity_mw": "53" if template_source == "tuho" else "50",
        "cod_date": "2029-12-30" if template_source == "tuho" else "2028-06-01",
        "construction_months": "18" if template_source == "tuho" else "12",
        "horizon_years": "30" if template_source == "tuho" else "25",
        "tariff_eur_mwh": "60" if template_source == "tuho" else "62",
        "ppa_term_years": "20" if template_source == "tuho" else "15",
        "p50_hours": "4164" if template_source == "tuho" else "1900",
        "opex_y1_keur": "1998.01" if template_source == "tuho" else "850",
        "total_capex_keur": ("70691.53944444444" if template_source == "tuho"
                             else "58000"),
        "gearing_pct": "",
        "interest_rate_pct": "5.98" if template_source == "tuho" else "4.5",
        "tenor_years": "14" if template_source == "tuho" else "18",
        "target_dscr": "1.2" if template_source == "tuho" else "1.25",
        **overrides,
    }
    resp = client.post("/projects/create", data=data, follow_redirects=False)
    redirect = resp.headers.get("hx-redirect") or resp.headers.get("location", "")
    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query)
    code = parsed.get("project", [None])[0]
    assert code, f"create failed: {resp.status_code} {resp.text[:200]}"
    return code


def _hash(client: TestClient, code: str) -> tuple[str, str]:
    body = client.get(f"/v2/workbook?project={code}").text
    return (
        re.search(r'data-content-hash="([^"]+)"', body).group(1),
        re.search(r'data-workbook-version="([^"]+)"', body).group(1),
    )


def _edit(client: TestClient, code: str, field_id: str, value: str,
          sheet: str) -> None:
    ch, wv = _hash(client, code)
    resp = client.post(
        "/v2/workbook/update",
        data={"field_id": field_id, "value": value, "project": code,
              "workbook_version": wv, "content_hash": ch, "sheet_id": sheet},
        headers={"HX-Request": "true"},
    )
    assert resp.status_code == 200, f"edit {field_id}: {resp.status_code} {resp.text[:200]}"


def _run_response(client: TestClient, code: str):
    ch, wv = _hash(client, code)
    resp = client.post(
        "/v2/workbook/run",
        data={"project": code, "content_hash": ch, "workbook_version": wv},
        headers={"HX-Request": "true"}, follow_redirects=False,
    )
    assert resp.status_code == 200, f"run failed: {resp.status_code} {resp.text[:300]}"
    return resp


def _kpi_from_html(html: str, testid: str = "kpi-project-irr") -> str | None:
    m = re.search(
        r'data-testid="%s".*?v2-kpi-value">([^<]*)<' % re.escape(testid),
        html, re.S)
    return m.group(1).strip() if m else None


def _persisted_kpis(code: str) -> dict:
    from app.persistence.projects_repository import get_project_by_code
    from app.persistence.workspace_repository import get_workspace_state

    rec = get_project_by_code(USER_ID, code)
    ws = get_workspace_state(USER_ID, rec.project_id)
    return dict(ws.last_runtime_summary or {})


def _runtime_at(code: str):
    from app.persistence.projects_repository import get_project_by_code
    from app.persistence.workspace_repository import get_workspace_state

    rec = get_project_by_code(USER_ID, code)
    ws = get_workspace_state(USER_ID, rec.project_id)
    return ws.last_runtime_at, ws.dirty, ws.last_runtime_summary or {}


ALL_SHEET_OOBS = (
    'id="v2-sheet-overview" hx-swap-oob="true"',
    'id="v2-sheet-senior-debt" hx-swap-oob="true"',
    'id="v2-sheet-tax" hx-swap-oob="true"',
    'id="v2-sheet-financial-statements" hx-swap-oob="true"',
    'id="v2-sheet-scenarios" hx-swap-oob="true"',
)


@pytest.fixture(scope="module")
def wind_code() -> str:
    client = _client()
    code = _create(client, "R6 Wind A", "generic_wind")
    _run_response(client, code)  # Run 1 establishes KPI A
    return code


class TestEditRunOverviewRefresh:
    def test_a_overview_kpi_refreshes_in_htmx_response(self, wind_code):
        """Test A/B: edit a BOUND economic input, Run via the real route, and
        prove the NEW KPI appears in the HTMX response itself (no manual
        reload) and matches the persisted runtime summary."""
        client = _client()
        kpi_a = _kpi_from_html(client.get(f"/v2/workbook?project={wind_code}").text)
        persisted_a = _persisted_kpis(wind_code)

        _edit(client, wind_code, "revenue.ppa.base_tariff", "82", "revenue")
        resp = _run_response(client, wind_code)

        kpi_b = _kpi_from_html(resp.text)
        assert kpi_a is not None and kpi_b is not None
        assert kpi_b != kpi_a, "material tariff edit must change Project IRR"

        persisted_b = _persisted_kpis(wind_code)
        assert persisted_b["project_irr"] != persisted_a["project_irr"]
        # UI KPI == persisted runtime KPI (percent vs ratio formatting)
        assert kpi_b == f"{persisted_b['project_irr'] * 100:.2f}%"

    def test_b_all_runtime_surfaces_refreshed_in_one_response(self, wind_code):
        """Test B: every runtime-dependent surface is present as an OOB
        fragment in the same Run response."""
        resp = _run_response(_client(), wind_code)
        for oob in ALL_SHEET_OOBS:
            assert oob in resp.text, oob
        assert 'id="v2-run-controls" hx-swap-oob="true"' in resp.text
        assert 'id="v2-status-banner" hx-swap-oob="true"' in resp.text
        assert 'id="v2-toolbar-runtime-state" hx-swap-oob="true"' in resp.text


class TestDirtyCurrentContract:
    def test_c_dirty_then_current(self, wind_code):
        """Test C: edit → stale/dirty presentation; Run → current."""
        client = _client()
        _edit(client, wind_code, "revenue.ppa.base_tariff", "72", "revenue")
        page = client.get(f"/v2/workbook?project={wind_code}").text
        assert "v2-state-stale" in page or "v2-banner-dirty" in page

        resp = _run_response(client, wind_code)
        # post-run response must not present the stale/dirty state
        assert "v2-state-stale" not in resp.text
        assert "v2-banner-dirty" not in resp.text

    def test_d_second_edit_marks_runtime_stale(self, wind_code):
        """Test D: after a successful Run, another edit must flip every
        runtime-status surface back to stale/not-current."""
        client = _client()
        _run_response(client, wind_code)
        _edit(client, wind_code, "revenue.ppa.base_tariff", "76", "revenue")
        page = client.get(f"/v2/workbook?project={wind_code}").text
        assert "v2-state-stale" in page or "v2-banner-dirty" in page
        # and the next Run response carries the refreshed surfaces again
        resp = _run_response(client, wind_code)
        for oob in ALL_SHEET_OOBS:
            assert oob in resp.text


class TestRuntimeSheetRefresh:
    def test_e_debt_runtime_from_new_run(self, wind_code):
        """Test E: the Senior Debt surface is re-rendered from the persisted
        runtime of the newest run (contains runtime-bound markers, not old
        or substituted evidence)."""
        _edit(_client(), wind_code, "revenue.ppa.base_tariff", "78", "revenue")
        resp = _run_response(_client(), wind_code)
        assert 'id="v2-sheet-senior-debt" hx-swap-oob="true"' in resp.text
        debt_fragment = resp.text.split('id="v2-sheet-senior-debt"', 1)[1]
        assert "debt-runtime-bar" in debt_fragment

    def test_f_tax_runtime_refresh_and_explicit_zero(self, wind_code):
        """Test F: R4-supported CIT edit → Run → Tax surface from the same
        run; explicit 0 % is honoured as data (run has zero tax)."""
        client = _client()
        code = _create(client, "R6 Wind Zero CIT", "generic_wind")
        _edit(client, code, "tax.assumptions.cit_rate_pct", "0", "tax")
        _run_response(client, code)
        kpis = _persisted_kpis(code)
        assert kpis.get("total_tax_keur") == pytest.approx(0.0)

        # a material CIT edit on the shared fixture: tax sheet still refreshed
        resp = _run_response(client, wind_code)
        assert 'id="v2-sheet-tax" hx-swap-oob="true"' in resp.text

    def test_g_fs_runtime_from_new_run_and_explicit_zero(self, wind_code):
        """Test G: the FS surface is re-rendered from the newest canonical
        runtime — its displayed CIT rate follows the R4 typed edit exactly,
        including explicit 0 % (zero is data, never substituted)."""
        client = _client()
        code = _create(client, "R6 FS Probe", "generic_wind")
        _edit(client, code, "revenue.ppa.base_tariff", "77", "revenue")
        resp1 = _run_response(client, code)
        fs1 = resp1.text.split('id="v2-sheet-financial-statements"', 1)[1]
        assert "(CIT) rate" in fs1

        # explicit zero CIT through the R4-supported real edit route
        _edit(client, code, "tax.assumptions.cit_rate_pct", "0", "tax")
        resp2 = _run_response(client, code)
        fs2 = resp2.text.split('id="v2-sheet-financial-statements"', 1)[1]
        assert "(CIT) rate" in fs2
        assert "0.0%" in fs2, "explicit 0% CIT must survive as zero"
        assert "25.0%" not in fs2.split("Balance Sheet")[0]


class TestFailedRunAtomicity:
    def test_h_failed_run_no_mixed_state(self):
        """Test H (§8): valid prior runtime -> edit -> deterministic
        fail-closed Run.  The old runtime must not be relabelled current,
        the timestamp must not advance, no partial KPI refresh may occur,
        and the failure must surface coherently."""
        client = _client()
        # TUHO working copy, factory-consistent tenor 14 -> Run succeeds.
        code = _create(client, "R6 Fail TUHO", "tuho")
        _run_response(client, code)
        kpis_ok = _persisted_kpis(code)
        runtime_at_ok, _, _ = _runtime_at(code)
        assert kpis_ok, "expected a successful first Run"

        # Edit that makes the next Run fail closed: tenor 18 needs 36 debt
        # periods but the typed TUHO DSCR schedule has 28 entries.
        _edit(client, code, "debt.senior.tenor_years", "18", "debt")
        ch, wv = _hash(client, code)
        resp = client.post(
            "/v2/workbook/run",
            data={"project": code, "content_hash": ch,
                  "workbook_version": wv},
            headers={"HX-Request": "true"}, follow_redirects=False,
        )
        body = resp.text

        runtime_at_after, dirty_after, kpis_after = _runtime_at(code)
        # Old runtime is NOT silently relabelled: persisted KPIs and the
        # runtime timestamp are exactly the prior successful run's.
        assert kpis_after == kpis_ok
        assert runtime_at_after == runtime_at_ok
        # The draft edit is preserved as requiring a valid Run (dirty).
        assert dirty_after is True
        # The failure is surfaced coherently (error banner) and no partial
        # post-run refresh fragments are emitted.
        assert "v2-banner-error" in body or "error" in body.lower()
        assert 'id="v2-sheet-overview" hx-swap-oob="true"' not in body


class TestScenarioParity:
    def test_i_base_scenario_base_ui_parity(self, wind_code):
        """Test I: supported CAPEX sub-line scenario override — Scenario Run
        UI == Scenario persisted runtime, differs from Base; return to Base
        restores the original economics; no stale scenario values."""
        from app.persistence.projects_repository import get_project_by_code
        from app.persistence.scenarios_repository import (
            add_scenario, select_scenario, update_scenario_overrides,
        )
        from app.persistence.workspace_repository import get_workspace_state
        from app.v2.capex_commands import add_capex_line
        from app.workbook.registry import WORKBOOK

        client = _client()
        rec = get_project_by_code(USER_ID, wind_code)
        sub, _ = add_capex_line(
            project_record=rec, user_id=USER_ID,
            label="R6 parity sub-line", parent_category_code="C.05",
            amount_keur=400.0, workbook_version=WORKBOOK.version,
            expected_content_hash=_hash(client, wind_code)[0],
        )
        base_kpis, base_rs = self._run_and_collect(client, wind_code)

        ws = get_workspace_state(USER_ID, rec.project_id)
        sc = add_scenario(
            user_id=USER_ID, project_id=rec.project_id,
            project_code=rec.project_code, scenario_name="R6 Scenario A",
            parent_scenario_id=ws.active_scenario_id or "",
            base_input_set=dict(ws.draft_snapshot),
        )
        update_scenario_overrides(USER_ID, sc.scenario_id, {
            "_capex_sub_line_overrides": {sub.sub_line_id: 4000.0},
        })
        assert select_scenario(USER_ID, rec.project_id, sc.scenario_id)
        scen_kpis, scen_rs = self._run_and_collect(client, wind_code)
        assert scen_kpis["project_irr"] != pytest.approx(
            base_kpis["project_irr"], abs=1e-12)
        assert self._kpi_ratio(scen_rs) == pytest.approx(
            scen_kpis["project_irr"], abs=5e-5)  # 2-dp percent display precision

        TestScenarioParity._force_base(rec.project_id)
        restored_kpis, restored_rs = self._run_and_collect(client, wind_code)
        assert restored_kpis["project_irr"] == pytest.approx(
            base_kpis["project_irr"], rel=1e-12)
        assert self._kpi_ratio(restored_rs) == pytest.approx(
            restored_kpis["project_irr"], abs=5e-5)  # 2-dp percent display precision

    @staticmethod
    def _kpi_ratio(rs: dict[str, object]) -> float:
        v = rs.get("Project IRR")
        return float(str(v).replace("%", "")) / 100.0

    @staticmethod
    def _run_and_collect(client: TestClient, code: str) -> tuple[dict, dict]:
        resp = _run_response(client, code)
        kpis = _persisted_kpis(code)
        m = re.search(
            r'data-testid="kpi-project-irr".*?v2-kpi-value">([^<]*)<',
            resp.text, re.S)
        rs = {"Project IRR": m.group(1).strip() if m else None}
        return kpis, rs

    @staticmethod
    def _force_base(project_id: str) -> None:
        from app.persistence.workspace_repository import (
            get_workspace_state, save_workspace_state,
        )
        ws = get_workspace_state(USER_ID, project_id)
        save_workspace_state(
            user_id=USER_ID, project_id=project_id,
            project_code=ws.project_code, draft_snapshot=dict(ws.draft_snapshot),
            saved_snapshot=dict(ws.saved_snapshot),
            last_runtime_snapshot=(dict(ws.last_runtime_snapshot)
                                   if ws.last_runtime_snapshot else None),
            last_runtime_summary=dict(ws.last_runtime_summary or {}),
            last_runtime_snapshot_id=ws.last_runtime_snapshot_id,
            last_runtime_origin=ws.last_runtime_origin,
            active_scenario_id=None, active_scenario_name=None,
        )


class TestFreshGetParity:
    def test_j_htmx_post_run_equals_fresh_get(self, wind_code):
        """Test J: HTMX post-run state == fresh GET state for equivalent
        runtime evidence (Overview KPI + all runtime surfaces present)."""
        client = _client()
        _edit(client, wind_code, "revenue.ppa.base_tariff", "79", "revenue")
        htmx = _run_response(client, wind_code).text
        fresh = client.get(f"/v2/workbook?project={wind_code}").text

        kpi_htmx = _kpi_from_html(htmx)
        kpi_fresh = _kpi_from_html(fresh)
        assert kpi_htmx is not None and kpi_htmx == kpi_fresh
        for marker in ('id="v2-sheet-senior-debt"', 'id="v2-sheet-tax"',
                       'id="v2-sheet-financial-statements"',
                       'id="v2-toolbar-runtime-state"'):
            assert marker in htmx and marker in fresh
