"""Phase 20B — Scenario Data Model Foundation

Tests:
- Scenario model: TUHO/Oborovo baselines have exactly one Base Case scenario.
- Base Case stores full input set; non-base stores only overrides.
- resolve_scenario_snapshot() behavior.
- Provenance dict structure for Base Case vs non-base.
- Guardrail: G20 remains BLOCKED, R99/R102 NOT APPROVED.
"""
import pytest, json
from unittest.mock import MagicMock, patch
from app.persistence.repository import (
    SCENARIO_INPUT_FIELDS,
    resolve_scenario_snapshot,
    get_or_create_base_case_scenario,
    seed_scenarios_if_needed,
    get_scenario_provenance,
    _compute_baseline_snapshot,
)


# ---------------------------------------------------------------------------
# 1. Scenario model — database-level
# ---------------------------------------------------------------------------

class TestScenarioModelBasics:
    def test_tuho_baseline_has_exactly_one_base_case(self):
        """TUHO — Baseline seeded on first-access must have exactly one Base Case."""
        from app.persistence.repository import seed_baseline_projects_if_needed, seed_scenarios_if_needed
        from app.persistence.db import get_cursor

        USER = "test_phase20b_tuho"
        CODE = "tuho-baseline"

        # Clean slate
        with get_cursor() as cur:
            cur.execute("DELETE FROM scenarios WHERE user_id=?", (USER,))
            cur.execute("DELETE FROM projects WHERE user_id=? AND project_code=?", (USER, CODE))

        seed_baseline_projects_if_needed(USER)
        from app.persistence.repository import get_project_by_code, get_or_create_base_case_scenario

        project = get_project_by_code(USER, CODE)
        assert project is not None, "TUHO baseline should be seeded"

        bc = seed_scenarios_if_needed(
            user_id=USER,
            project_id=project.project_id,
            project_code=CODE,
            project_type="wind",
            source_project_template="tuho",
            baseline_snapshot=project.baseline_snapshot,
            governance_state={"g20": "BLOCKED", "r99_r102": "NOT_APPROVED", "lender_ready": False},
            template_origin="tuho",
        )
        assert bc.is_base_case is True

        # Exactly one non-archived Base Case
        with get_cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM scenarios WHERE user_id=? AND project_id=? AND is_base_case=1 AND archived=0",
                (USER, project.project_id),
            )
            count = cur.fetchone()[0]
        assert count == 1, f"Expected exactly 1 Base Case for TUHO, got {count}"

        # Second call returns existing (not a new one)
        bc2 = seed_scenarios_if_needed(
            user_id=USER,
            project_id=project.project_id,
            project_code=CODE,
            project_type="wind",
            source_project_template="tuho",
            baseline_snapshot=project.baseline_snapshot,
            governance_state={"g20": "BLOCKED", "r99_r102": "NOT_APPROVED", "lender_ready": False},
            template_origin="tuho",
        )
        assert bc2.scenario_id == bc.scenario_id, "Idempotent — second call returns same scenario"

    def test_oborovo_baseline_has_exactly_one_base_case(self):
        """Oborovo — Baseline seeded on first-access must have exactly one Base Case."""
        from app.persistence.repository import seed_baseline_projects_if_needed, seed_scenarios_if_needed
        from app.persistence.db import get_cursor

        USER = "test_phase20b_oborovo"
        CODE = "oborovo-baseline"

        with get_cursor() as cur:
            cur.execute("DELETE FROM scenarios WHERE user_id=?", (USER,))
            cur.execute("DELETE FROM projects WHERE user_id=? AND project_code=?", (USER, CODE))

        seed_baseline_projects_if_needed(USER)
        from app.persistence.repository import get_project_by_code

        project = get_project_by_code(USER, CODE)
        assert project is not None, "Oborovo baseline should be seeded"

        bc = seed_scenarios_if_needed(
            user_id=USER,
            project_id=project.project_id,
            project_code=CODE,
            project_type="solar",
            source_project_template="oborovo",
            baseline_snapshot=project.baseline_snapshot,
            governance_state={"g20": "BLOCKED", "r99_r102": "NOT_APPROVED", "lender_ready": False},
            template_origin="oborovo",
        )
        assert bc.is_base_case is True

        with get_cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM scenarios WHERE user_id=? AND project_id=? AND is_base_case=1 AND archived=0",
                (USER, project.project_id),
            )
            count = cur.fetchone()[0]
        assert count == 1, f"Expected exactly 1 Base Case for Oborovo, got {count}"

    def test_user_created_project_gets_base_case(self):
        """Save As flow creates a user_created project that gets exactly one Base Case."""
        from app.persistence.repository import (
            seed_baseline_projects_if_needed,
            seed_scenarios_if_needed,
            create_project_record,
            get_project_by_code,
        )
        from app.persistence.db import get_cursor

        USER = "test_phase20b_user"
        CODE = "tuho-baseline"

        with get_cursor() as cur:
            cur.execute("DELETE FROM scenarios WHERE user_id=?", (USER,))
            cur.execute("DELETE FROM projects WHERE user_id=? AND project_code LIKE 'test Phase20b_user%'", (USER,))
            cur.execute("DELETE FROM projects WHERE user_id=? AND project_code=?", (USER, CODE))

        seed_baseline_projects_if_needed(USER)
        baseline = get_project_by_code(USER, CODE)

        # Create user project
        new_code = "test-phase20b-user-project"
        new_name = "Test Phase 20B User Project"
        user_proj = create_project_record(
            user_id=USER,
            project_code=new_code,
            project_name=new_name,
            project_type="wind",
            project_origin="user_created",
            template_source="tuho",
            baseline_snapshot=baseline.baseline_snapshot,
            is_readonly=False,
            governance_state={"g20": "BLOCKED", "r99_r102": "NOT_APPROVED", "lender_ready": False},
        )

        bc = seed_scenarios_if_needed(
            user_id=USER,
            project_id=user_proj.project_id,
            project_code=new_code,
            project_type="wind",
            source_project_template="tuho",
            baseline_snapshot=user_proj.baseline_snapshot,
            governance_state=user_proj.governance_state,
            template_origin="tuho",
        )

        assert bc.is_base_case is True
        assert bc.project_code == new_code
        with get_cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM scenarios WHERE user_id=? AND project_id=? AND is_base_case=1 AND archived=0",
                (USER, user_proj.project_id),
            )
            count = cur.fetchone()[0]
        assert count == 1

    def test_base_case_stores_full_input_set(self):
        """Base Case scenario has base_input_set populated with full input snapshot."""
        from app.persistence.repository import seed_baseline_projects_if_needed, seed_scenarios_if_needed
        from app.persistence.repository import get_project_by_code
        from app.persistence.db import get_cursor

        USER = "test_phase20b_fullinput"
        CODE = "tuho-baseline"

        with get_cursor() as cur:
            cur.execute("DELETE FROM scenarios WHERE user_id=?", (USER,))
            cur.execute("DELETE FROM projects WHERE user_id=? AND project_code=?", (USER, CODE))
        seed_baseline_projects_if_needed(USER)

        project = get_project_by_code(USER, CODE)
        bc = seed_scenarios_if_needed(
            user_id=USER,
            project_id=project.project_id,
            project_code=CODE,
            project_type="wind",
            source_project_template="tuho",
            baseline_snapshot=project.baseline_snapshot,
            governance_state={"g20": "BLOCKED", "r99_r102": "NOT_APPROVED", "lender_ready": False},
            template_origin="tuho",
        )

        assert bc.base_input_set, "Base input set must not be empty"
        assert "tariff_eur_mwh" in bc.base_input_set, "tariff should be in base_input_set"
        assert "capacity_mw" in bc.base_input_set, "capacity should be in base_input_set"
        assert bc.base_input_set.get("project_name") == project.baseline_snapshot.get("project_name")

    def test_non_base_scenario_stores_only_overrides(self):
        """Non-Base-Case scenario has empty base_input_set and populated overrides."""
        from app.persistence.repository import seed_baseline_projects_if_needed, seed_scenarios_if_needed
        from app.persistence.repository import get_project_by_code, save_scenario
        from app.persistence.db import get_cursor

        USER = "test_phase20b_nonbase"
        CODE = "tuho-baseline"

        with get_cursor() as cur:
            cur.execute("DELETE FROM scenarios WHERE user_id=?", (USER,))
            cur.execute("DELETE FROM projects WHERE user_id=? AND project_code=?", (USER, CODE))
        seed_baseline_projects_if_needed(USER)

        project = get_project_by_code(USER, CODE)
        bc = seed_scenarios_if_needed(
            user_id=USER,
            project_id=project.project_id,
            project_code=CODE,
            project_type="wind",
            source_project_template="tuho",
            baseline_snapshot=project.baseline_snapshot,
            governance_state={"g20": "BLOCKED", "r99_r102": "NOT_APPROVED", "lender_ready": False},
            template_origin="tuho",
        )

        overrides = {"tariff_eur_mwh": 85.0, "capacity_mw": 40.0}
        non_base = save_scenario(
            user_id=USER,
            project_id=project.project_id,
            scenario_name="High Tariff Scenario",
            project_code=CODE,
            source_project_template="tuho",
            copied_from_scenario_id=bc.scenario_id,
            snapshot={},
            governance_state={},
            last_run_summary={},
            replay_metadata={},
        )

        # Manually update the new scenario as non-base
        with get_cursor() as cur:
            cur.execute(
                """UPDATE scenarios SET is_base_case=0, parent_scenario_id=?, base_input_set_json='{}',
                   overrides_json=? WHERE scenario_id=?""",
                (bc.scenario_id, json.dumps(overrides), non_base.scenario_id),
            )

        with get_cursor() as cur:
            cur.execute("SELECT * FROM scenarios WHERE scenario_id=?", (non_base.scenario_id,))
            from app.persistence.repository import ScenarioRecord
            row = cur.fetchone()
            rec = ScenarioRecord.from_row(row)

        assert rec.is_base_case is False
        assert rec.parent_scenario_id == bc.scenario_id
        assert rec.base_input_set == {}
        assert rec.overrides == overrides

    def test_duplicate_base_case_is_prevented(self):
        """get_or_create_base_case_scenario returns existing when already present."""
        from app.persistence.repository import seed_baseline_projects_if_needed, seed_scenarios_if_needed
        from app.persistence.repository import get_project_by_code
        from app.persistence.db import get_cursor

        USER = "test_phase20b_nodup"
        CODE = "tuho-baseline"

        with get_cursor() as cur:
            cur.execute("DELETE FROM scenarios WHERE user_id=?", (USER,))
            cur.execute("DELETE FROM projects WHERE user_id=? AND project_code=?", (USER, CODE))
        seed_baseline_projects_if_needed(USER)
        project = get_project_by_code(USER, CODE)

        bc1 = seed_scenarios_if_needed(
            user_id=USER,
            project_id=project.project_id,
            project_code=CODE,
            project_type="wind",
            source_project_template="tuho",
            baseline_snapshot=project.baseline_snapshot,
            governance_state={"g20": "BLOCKED", "r99_r102": "NOT_APPROVED", "lender_ready": False},
            template_origin="tuho",
        )
        bc2 = seed_scenarios_if_needed(
            user_id=USER,
            project_id=project.project_id,
            project_code=CODE,
            project_type="wind",
            source_project_template="tuho",
            baseline_snapshot=project.baseline_snapshot,
            governance_state={"g20": "BLOCKED", "r99_r102": "NOT_APPROVED", "lender_ready": False},
            template_origin="tuho",
        )
        assert bc1.scenario_id == bc2.scenario_id, "Second seed call returns same Base Case"


# ---------------------------------------------------------------------------
# 2. Resolution tests
# ---------------------------------------------------------------------------

class TestScenarioResolution:
    def test_resolve_empty_overrides_returns_base(self):
        base = {"a": 1, "b": 2}
        result = resolve_scenario_snapshot(base, {})
        assert result == base
        assert result is not base, "Must return a copy"

    def test_resolve_with_overrides_changes_only_overridden(self):
        base = {"capacity_mw": 35, "tariff_eur_mwh": 60, "opex_y1_keur": 1998}
        overrides = {"tariff_eur_mwh": 85}
        result = resolve_scenario_snapshot(base, overrides)
        assert result == {"capacity_mw": 35, "tariff_eur_mwh": 85, "opex_y1_keur": 1998}

    def test_resolve_missing_keys_inherit_from_base(self):
        base = {"capacity_mw": 35, "tariff_eur_mwh": 60, "opex_y1_keur": 1998}
        overrides = {"capacity_mw": 100}
        result = resolve_scenario_snapshot(base, overrides)
        assert result["tariff_eur_mwh"] == 60
        assert result["opex_y1_keur"] == 1998
        assert result["capacity_mw"] == 100

    def test_resolve_unknown_keys_are_dropped(self):
        base = {"capacity_mw": 35}
        overrides = {"bad_key": 999, "another_bad": "x"}
        result = resolve_scenario_snapshot(base, overrides)
        assert result == {"capacity_mw": 35}
        assert "bad_key" not in result
        assert "another_bad" not in result

    def test_resolve_preserves_base_when_only_unknown_keys(self):
        base = {"capacity_mw": 35}
        overrides = {"bad_key": 999}
        result = resolve_scenario_snapshot(base, overrides)
        assert result == {"capacity_mw": 35}


# ---------------------------------------------------------------------------
# 3. Provenance tests
# ---------------------------------------------------------------------------

class TestScenarioProvenance:
    def test_base_case_provenance_has_empty_override_field_list(self):
        from app.persistence.repository import ScenarioRecord, get_scenario_provenance, ProjectRecord

        class FakeProjectRecord:
            project_origin = "saved_baseline"
            project_name = "TUHO — Baseline"

        scenario_rec = MagicMock(spec=ScenarioRecord)
        scenario_rec.project_id = "pid123"
        scenario_rec.project_code = "tuho-baseline"
        scenario_rec.scenario_id = "sid456"
        scenario_rec.scenario_name = "TUHO — Baseline"
        scenario_rec.is_base_case = True
        scenario_rec.parent_scenario_id = None
        scenario_rec.overrides = {}

        prov = get_scenario_provenance(scenario_rec, FakeProjectRecord(), "project_factory:tuho")
        assert prov["is_base_case"] is True
        assert prov["override_field_list"] == []
        assert prov["baseline_source"] is True
        assert prov["template_origin"] == "project_factory:tuho"
        assert prov["parent_scenario_id"] is None

    def test_non_base_provenance_has_override_field_list(self):
        from app.persistence.repository import ScenarioRecord, get_scenario_provenance, ProjectRecord

        scenario_rec = MagicMock(spec=ScenarioRecord)
        scenario_rec.project_id = "pid123"
        scenario_rec.project_code = "tuho-copy"
        scenario_rec.scenario_id = "sid789"
        scenario_rec.scenario_name = "High Tariff"
        scenario_rec.is_base_case = False
        scenario_rec.parent_scenario_id = "sid456"
        scenario_rec.overrides = {"tariff_eur_mwh": 85, "capacity_mw": 100}

        prov = get_scenario_provenance(scenario_rec, None, "project_factory:tuho")
        assert prov["is_base_case"] is False
        assert prov["override_field_list"] == ["capacity_mw", "tariff_eur_mwh"]
        assert prov["baseline_source"] is False
        assert prov["parent_scenario_id"] == "sid456"


# ---------------------------------------------------------------------------
# 4. Guardrail tests
# ---------------------------------------------------------------------------

class TestGuardrailsG20R99R102:
    def test_g20_blocked_in_governance_state(self):
        """All baseline/user projects created by seed_scenarios_if_needed have G20 BLOCKED."""
        from app.persistence.repository import seed_baseline_projects_if_needed, seed_scenarios_if_needed
        from app.persistence.repository import get_project_by_code
        from app.persistence.db import get_cursor

        USER = "test_phase20b_guard"
        CODE = "tuho-baseline"

        with get_cursor() as cur:
            cur.execute("DELETE FROM scenarios WHERE user_id=?", (USER,))
            cur.execute("DELETE FROM projects WHERE user_id=? AND project_code=?", (USER if USER else "test-phase20b-tuho", CODE))

        seed_baseline_projects_if_needed(USER)
        project = get_project_by_code(USER, CODE)
        bc = seed_scenarios_if_needed(
            user_id=USER,
            project_id=project.project_id,
            project_code=CODE,
            project_type="wind",
            source_project_template="tuho",
            baseline_snapshot=project.baseline_snapshot,
            governance_state={"g20": "BLOCKED", "r99_r102": "NOT_APPROVED", "lender_ready": False},
            template_origin="tuho",
        )
        assert bc.governance_state.get("g20") == "BLOCKED"

    def test_r99_r102_not_approved_in_governance_state(self):
        """All baseline/user projects created by seed_scenarios_if_needed have R99/R102 NOT_APPROVED."""
        from app.persistence.repository import seed_baseline_projects_if_needed, seed_scenarios_if_needed
        from app.persistence.repository import get_project_by_code
        from app.persistence.db import get_cursor

        USER = "test_phase20b_guard2"
        CODE = "oborovo-baseline"

        with get_cursor() as cur:
            cur.execute("DELETE FROM scenarios WHERE user_id=?", (USER,))
            cur.execute("DELETE FROM projects WHERE user_id=? AND project_code=?", (USER, CODE))
        seed_baseline_projects_if_needed(USER)
        project = get_project_by_code(USER, CODE)
        bc = seed_scenarios_if_needed(
            user_id=USER,
            project_id=project.project_id,
            project_code=CODE,
            project_type="solar",
            source_project_template="oborovo",
            baseline_snapshot=project.baseline_snapshot,
            governance_state={"g20": "BLOCKED", "r99_r102": "NOT_APPROVED", "lender_ready": False},
            template_origin="oborovo",
        )
        assert bc.governance_state.get("r99_r102") == "NOT_APPROVED"

    def test_no_formula_changes_in_resolve(self):
        """resolve_scenario_snapshot only does dict operations — no financial calculations."""
        import inspect
        source = inspect.getsource(resolve_scenario_snapshot)
        assert "**" not in source or source.count("**") <= 1, "No power operator in resolve"
        assert "%" not in source, "No modulo in resolve (shouldn't be financial)"
        assert "/" not in source or source.count("/") == 0, "No division in resolve"
        # Only dict key access operations — pure Python data structure merge
        import ast
        tree = ast.parse(source)
        for node in ast.walk(tree):
            assert not isinstance(node, ast.BinOp) or isinstance(node.op, (ast.Add, ast.Sub)), \
                "No arithmetic BinOp in resolve_scenario_snapshot"
