from __future__ import annotations

import os
import sqlite3
import uuid
from io import BytesIO
from pathlib import Path

import openpyxl
import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def test_db(monkeypatch):
    temp_root = REPO_ROOT / ".tmp_phase57a9h"
    temp_root.mkdir(exist_ok=True)
    db_file = temp_root / f"phase57a9h_{uuid.uuid4().hex[:8]}.db"
    monkeypatch.setenv("FINCO_DB_PATH", str(db_file))
    import app.persistence.db as db_mod

    monkeypatch.setattr(db_mod, "DB_PATH", str(db_file))
    db_mod.init_db()
    try:
        yield db_file
    finally:
        for suffix in ("", "-wal", "-shm"):
            try:
                (Path(str(db_file) + suffix)).unlink(missing_ok=True)
            except PermissionError:
                pass


def _snapshot(**overrides):
    data = {
        "active_project": "pilot-capex-dup",
        "project_name": "Capex Dup Project",
        "project_type": "Solar",
        "project_origin": "user_created",
        "template_source": "generic_solar",
        "country_market": "Croatia",
        "scenario": "Base",
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
    }
    data.update(overrides)
    return data


def _load_wb(excel_bytes: bytes):
    return openpyxl.load_workbook(BytesIO(excel_bytes), data_only=True)


def _sheet_rows_by_business_code(ws) -> list[dict[str, object]]:
    headers = None
    found_header = False
    rows = []
    for row in ws.iter_rows(values_only=True):
        values = list(row)
        if not found_header:
            if "Business Code" in values:
                headers = values
                found_header = True
            continue
        if all(v in (None, "") for v in values):
            continue
        if values[0] == "Note":
            continue
        record = {
            str(headers[idx]): values[idx] if idx < len(values) else None
            for idx in range(len(headers))
            if headers[idx] is not None
        }
        if record.get("Business Code") in (None, ""):
            continue
        rows.append(record)
    assert headers is not None
    return rows


def _make_user_project(user_id: str = "u57a9h"):
    from app.persistence.repository import create_project_record

    return create_project_record(
        user_id=user_id,
        project_code="pilot-capex-dup",
        project_name="Capex Dup Project",
        project_type="Solar",
        project_origin="user_project",
        template_source="generic_solar",
        baseline_snapshot=_snapshot(),
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT_APPROVED"},
    )


def _create_sub_line(project_id: str, *, parent: str, label: str, amount: float):
    from app.persistence.capex_sub_lines import create_sub_line

    with sqlite3.connect(os.environ["FINCO_DB_PATH"]) as conn:
        conn.row_factory = sqlite3.Row
        sub = create_sub_line(
            conn.cursor(),
            project_id=project_id,
            parent_category_code=parent,
            label=label,
            amount_keur=amount,
            comments=f"{label} comment",
        )
        conn.commit()
        return sub


def _count_sub_lines(project_id: str) -> int:
    with sqlite3.connect(os.environ["FINCO_DB_PATH"]) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT COUNT(*) FROM capex_sub_lines WHERE project_id=?",
            (project_id,),
        ).fetchone()
        return int(row[0])


def _make_scenario_a(project, user_id: str = "u57a9h"):
    from app.persistence.repository import (
        add_scenario,
        seed_scenarios_if_needed,
        update_scenario_overrides,
    )

    base = seed_scenarios_if_needed(
        user_id=user_id,
        project_id=project.project_id,
        project_code=project.project_code,
        project_type="Solar",
        source_project_template="generic_solar",
        baseline_snapshot=_snapshot(),
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT_APPROVED"},
        template_origin="generic_solar",
    )
    scenario = add_scenario(
        user_id=user_id,
        project_id=project.project_id,
        project_code=project.project_code,
        scenario_name="Scenario A",
        parent_scenario_id=base.scenario_id,
        base_input_set=base.base_input_set,
        overrides={"tariff_eur_mwh": "72"},
    )
    c02 = _create_sub_line(project.project_id, parent="C.02", label="Extra EPC", amount=1000.0)
    c08 = _create_sub_line(project.project_id, parent="C.08", label="Extra DD", amount=200.0)
    c11 = _create_sub_line(project.project_id, parent="C.11", label="Extra Legal", amount=300.0)
    meta = {
        c02.sub_line_id: {"business_code": c02.business_code, "copied_from": "phase57a9h"},
        c08.sub_line_id: {"business_code": c08.business_code, "copied_from": "phase57a9h"},
        c11.sub_line_id: {"business_code": c11.business_code, "copied_from": "phase57a9h"},
    }
    updated = update_scenario_overrides(
        user_id,
        scenario.scenario_id,
        {
            "_capex_sub_line_overrides": {
                c02.sub_line_id: 1750.0,
                c08.sub_line_id: 225.0,
                c11.sub_line_id: 325.0,
            },
            "_capex_sub_line_overrides_metadata": meta,
            "unknown_key_should_drop": 999,
        },
    )
    return base, updated, (c02, c08, c11)


class TestPhase57A9HDuplicateScenarioCapexOverrideFix:
    def test_duplicate_preserves_capex_override_map_and_metadata(self, test_db):
        from app.persistence.repository import duplicate_scenario, get_scenario

        project = _make_user_project()
        _base, scenario_a, (c02, c08, c11) = _make_scenario_a(project)

        scenario_b = duplicate_scenario("u57a9h", scenario_a.scenario_id, "Scenario B")
        assert scenario_b is not None

        reloaded_a = get_scenario(scenario_a.scenario_id, "u57a9h")
        reloaded_b = get_scenario(scenario_b.scenario_id, "u57a9h")
        assert reloaded_a is not None and reloaded_b is not None

        assert reloaded_b.overrides.get("_capex_sub_line_overrides") == (
            reloaded_a.overrides.get("_capex_sub_line_overrides")
        )
        assert reloaded_b.overrides.get("_capex_sub_line_overrides_metadata") == (
            reloaded_a.overrides.get("_capex_sub_line_overrides_metadata")
        )
        assert reloaded_b.overrides.get("tariff_eur_mwh") == "72"
        assert "unknown_key_should_drop" not in reloaded_b.overrides
        assert reloaded_b.overrides["_capex_sub_line_overrides"][c02.sub_line_id] == 1750.0
        assert reloaded_b.overrides["_capex_sub_line_overrides"][c08.sub_line_id] == 225.0
        assert reloaded_b.overrides["_capex_sub_line_overrides"][c11.sub_line_id] == 325.0

    def test_duplicate_preserves_base_input_set_and_source_is_unchanged(self, test_db):
        from app.persistence.repository import duplicate_scenario, get_scenario

        project = _make_user_project()
        _base, scenario_a, _subs = _make_scenario_a(project)
        base_input_before = dict(scenario_a.base_input_set)
        overrides_before = dict(scenario_a.overrides)

        scenario_b = duplicate_scenario("u57a9h", scenario_a.scenario_id, "Scenario B")
        reloaded_a = get_scenario(scenario_a.scenario_id, "u57a9h")
        reloaded_b = get_scenario(scenario_b.scenario_id, "u57a9h")

        assert reloaded_b.base_input_set == base_input_before
        assert reloaded_a.base_input_set == base_input_before
        assert reloaded_a.overrides == overrides_before
        assert reloaded_b.copied_from_scenario_id == scenario_a.scenario_id
        assert reloaded_b.scenario_id != scenario_a.scenario_id
        assert reloaded_b.scenario_name == "Scenario B"
        assert reloaded_b.is_base_case is False

    def test_duplicate_keeps_project_level_uuid_references_and_creates_no_new_sub_lines(self, test_db):
        from app.persistence.repository import duplicate_scenario

        project = _make_user_project()
        _base, scenario_a, (c02, c08, c11) = _make_scenario_a(project)
        count_before = _count_sub_lines(project.project_id)

        scenario_b = duplicate_scenario("u57a9h", scenario_a.scenario_id, "Scenario B")
        assert scenario_b is not None

        count_after = _count_sub_lines(project.project_id)
        assert count_after == count_before
        override_map = scenario_b.overrides["_capex_sub_line_overrides"]
        assert set(override_map) == {c02.sub_line_id, c08.sub_line_id, c11.sub_line_id}

    def test_duplicate_run_materialization_uses_copied_override_amount(self, test_db):
        from app.services.capex_sub_lines_integration import _apply_user_sub_lines_to_capex
        from app.persistence.repository import duplicate_scenario
        from app.ui_runner import run_demo_project

        project = _make_user_project()
        _base, scenario_a, (c02, _c08, _c11) = _make_scenario_a(project)
        scenario_b = duplicate_scenario("u57a9h", scenario_a.scenario_id, "Scenario B")

        demo = run_demo_project("Solar", "Base")
        before = demo.project_inputs.capex.epc_contract.amount_keur
        after = _apply_user_sub_lines_to_capex(
            demo.project_inputs.capex,
            project_id=project.project_id,
            scenario_overrides=scenario_b.overrides,
        )

        assert scenario_b.overrides["_capex_sub_line_overrides"][c02.sub_line_id] == 1750.0
        assert after.epc_contract.amount_keur == before + 1750.0
        assert after.epc_contract.amount_keur != before + 1000.0

    def test_duplicate_export_audit_sheet_uses_copied_effective_amounts(self, test_db):
        from app.excel_export import build_excel_export
        from app.persistence.repository import duplicate_scenario
        from app.ui_runner import run_demo_project

        project = _make_user_project()
        _base, scenario_a, (c02, c08, c11) = _make_scenario_a(project)
        scenario_b = duplicate_scenario("u57a9h", scenario_a.scenario_id, "Scenario B")

        demo = run_demo_project("Solar", "Base")
        wb = _load_wb(
            build_excel_export(
                result=demo.result,
                project_inputs=demo.project_inputs,
                provenance_metadata={
                    "project_id": project.project_id,
                    "active_scenario_id": scenario_b.scenario_id,
                    "active_scenario_name": scenario_b.scenario_name,
                },
            )
        )
        rows = _sheet_rows_by_business_code(wb["CapEx_SubLines_Audit"])
        row_c02 = next(r for r in rows if r["Business Code"] == c02.business_code)
        row_c08 = next(r for r in rows if r["Business Code"] == c08.business_code)
        row_c11 = next(r for r in rows if r["Business Code"] == c11.business_code)

        assert row_c02["Effective Amount (kEUR)"] == 1750
        assert row_c02["Effective Amount (kEUR)"] != 1000
        assert row_c08["Effective Amount (kEUR)"] == 225
        assert row_c11["Effective Amount (kEUR)"] == 325

    def test_factory_projects_remain_without_user_line_mutation(self, test_db):
        from app.persistence.repository import duplicate_scenario, save_project, save_scenario

        tuho = save_project(
            user_id="u57a9h",
            project_code="tuho",
            project_name="TUHO",
            source_project_template="tuho",
            project_origin="factory_template",
            is_readonly=True,
        )
        scenario = save_scenario(
            user_id="u57a9h",
            project_id=tuho.project_id,
            scenario_name="TUHO Snapshot",
            project_code="tuho",
            source_project_template="tuho",
            snapshot={"active_project": "tuho", "scenario": "Base"},
        )
        before = _count_sub_lines(tuho.project_id)
        copied = duplicate_scenario("u57a9h", scenario.scenario_id, "TUHO Copy")
        after = _count_sub_lines(tuho.project_id)

        assert copied is not None
        assert before == 0
        assert after == 0
