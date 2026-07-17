"""
Phase 1A — Tests for finco_parity/baselines/manifest.json.

Validates structural integrity and cross-references against current codebase facts.
No engine execution.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

MANIFEST_PATH = Path(__file__).parent.parent / "finco_parity" / "baselines" / "manifest.json"

EXPECTED_BASELINE_IDS = {"tuho", "oborovo", "generic_solar", "generic_wind"}

_REQUIRED_BASELINE_KEYS = {
    "baseline_id",
    "display_name",
    "project_type_key",
    "project_code",
    "technology",
    "capacity_mw",
    "horizon_years",
    "factory_function",
    "run_path",
    "engine_designation",
    "fixture_selection",
    "identity_guard",
    "notes",
}

_REQUIRED_FIXTURE_KEYS = {
    "mechanism",
    "flag",
    "flag_value",
    "notes",
}


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def baselines(manifest) -> list[dict]:
    return manifest["baselines"]


@pytest.fixture(scope="module")
def baselines_by_id(baselines) -> dict[str, dict]:
    return {b["baseline_id"]: b for b in baselines}


class TestManifestStructure:
    def test_manifest_file_exists(self):
        assert MANIFEST_PATH.exists()

    def test_manifest_is_valid_json(self):
        json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_manifest_version_present(self, manifest):
        assert "manifest_version" in manifest

    def test_baselines_key_present(self, manifest):
        assert "baselines" in manifest
        assert isinstance(manifest["baselines"], list)

    def test_exactly_four_baselines(self, baselines):
        assert len(baselines) == 4

    def test_baseline_ids_correct(self, baselines_by_id):
        assert set(baselines_by_id.keys()) == EXPECTED_BASELINE_IDS

    def test_required_keys_present(self, baselines):
        for b in baselines:
            missing = _REQUIRED_BASELINE_KEYS - b.keys()
            assert not missing, f"baseline {b.get('baseline_id')!r} missing keys: {missing}"

    def test_notes_is_list_of_strings(self, baselines):
        for b in baselines:
            assert isinstance(b["notes"], list)
            for note in b["notes"]:
                assert isinstance(note, str)

    def test_fixture_selection_required_keys(self, baselines):
        for b in baselines:
            fs = b["fixture_selection"]
            missing = _REQUIRED_FIXTURE_KEYS - fs.keys()
            assert not missing, f"baseline {b['baseline_id']} fixture_selection missing: {missing}"


class TestManifestTUHO:
    def test_project_code(self, baselines_by_id):
        assert baselines_by_id["tuho"]["project_code"] == "TUHO-WIND-1"

    def test_project_type_key(self, baselines_by_id):
        assert baselines_by_id["tuho"]["project_type_key"] == "TUHO"

    def test_technology(self, baselines_by_id):
        assert baselines_by_id["tuho"]["technology"] == "wind"

    def test_capacity_mw(self, baselines_by_id):
        assert baselines_by_id["tuho"]["capacity_mw"] == pytest.approx(35.0)

    def test_horizon_years(self, baselines_by_id):
        assert baselines_by_id["tuho"]["horizon_years"] == 30

    def test_fixture_mechanism_is_capability_flag(self, baselines_by_id):
        assert baselines_by_id["tuho"]["fixture_selection"]["mechanism"] == "capability_flag"

    def test_fixture_flag_is_correct(self, baselines_by_id):
        fs = baselines_by_id["tuho"]["fixture_selection"]
        assert fs["flag"] == "use_frozen_excel_senior_debt_schedule"
        assert fs["flag_value"] is True

    def test_fixture_path_contains_phase7_tuho(self, baselines_by_id):
        path = baselines_by_id["tuho"]["fixture_selection"]["fixture_path_value"]
        assert "phase7_tuho" in path

    def test_identity_guard_is_null(self, baselines_by_id):
        # No project-code guard in waterfall_core.py; fixture is capability-driven
        assert baselines_by_id["tuho"]["identity_guard"] is None

    def test_factory_references_create_default_tuho_wind1(self, baselines_by_id):
        assert "create_default_tuho_wind1" in baselines_by_id["tuho"]["factory_function"]

    def test_tuho_code_matches_actual_factory(self, baselines_by_id):
        # Cross-reference against the actual factory
        from app.project_factories import create_default_tuho_wind1
        inputs = create_default_tuho_wind1()
        assert inputs.info.code == baselines_by_id["tuho"]["project_code"]


class TestManifestOborovo:
    def test_project_code_is_obr001(self, baselines_by_id):
        # Actual project code is OBR-001, not OBOROVO-SOLAR-1
        assert baselines_by_id["oborovo"]["project_code"] == "OBR-001"

    def test_project_type_key(self, baselines_by_id):
        assert baselines_by_id["oborovo"]["project_type_key"] == "Oborovo"

    def test_technology(self, baselines_by_id):
        assert baselines_by_id["oborovo"]["technology"] == "solar"

    def test_capacity_mw(self, baselines_by_id):
        assert baselines_by_id["oborovo"]["capacity_mw"] == pytest.approx(75.26)

    def test_fixture_mechanism_is_capability_flag(self, baselines_by_id):
        assert baselines_by_id["oborovo"]["fixture_selection"]["mechanism"] == "capability_flag"

    def test_fixture_path_contains_phase23q_oborovo(self, baselines_by_id):
        path = baselines_by_id["oborovo"]["fixture_selection"]["fixture_path_value"]
        assert "phase23q_oborovo" in path

    def test_identity_guard_is_null(self, baselines_by_id):
        assert baselines_by_id["oborovo"]["identity_guard"] is None

    def test_oborovo_code_matches_actual_factory(self, baselines_by_id):
        from app.project_factories import create_default_oborovo
        inputs = create_default_oborovo()
        assert inputs.info.code == baselines_by_id["oborovo"]["project_code"]


class TestManifestGenericProjects:
    def test_solar_project_code(self, baselines_by_id):
        assert baselines_by_id["generic_solar"]["project_code"] == "TEST-SOLAR-1"

    def test_wind_project_code(self, baselines_by_id):
        assert baselines_by_id["generic_wind"]["project_code"] == "TEST-WIND-1"

    def test_solar_project_type_key(self, baselines_by_id):
        assert baselines_by_id["generic_solar"]["project_type_key"] == "Test 1"

    def test_wind_project_type_key(self, baselines_by_id):
        assert baselines_by_id["generic_wind"]["project_type_key"] == "Test 2"

    def test_solar_capacity(self, baselines_by_id):
        assert baselines_by_id["generic_solar"]["capacity_mw"] == pytest.approx(50.0)

    def test_wind_capacity(self, baselines_by_id):
        assert baselines_by_id["generic_wind"]["capacity_mw"] == pytest.approx(40.0)

    def test_solar_horizon(self, baselines_by_id):
        assert baselines_by_id["generic_solar"]["horizon_years"] == 20

    def test_wind_horizon(self, baselines_by_id):
        assert baselines_by_id["generic_wind"]["horizon_years"] == 25

    def test_solar_no_frozen_fixture(self, baselines_by_id):
        assert baselines_by_id["generic_solar"]["fixture_selection"]["mechanism"] == "none"

    def test_wind_no_frozen_fixture(self, baselines_by_id):
        assert baselines_by_id["generic_wind"]["fixture_selection"]["mechanism"] == "none"

    def test_solar_no_identity_guard(self, baselines_by_id):
        assert baselines_by_id["generic_solar"]["identity_guard"] is None

    def test_wind_no_identity_guard(self, baselines_by_id):
        assert baselines_by_id["generic_wind"]["identity_guard"] is None

    def test_solar_code_matches_actual_factory(self, baselines_by_id):
        from app.project_factories import create_default_solar_project
        inputs = create_default_solar_project()
        assert inputs.info.code == baselines_by_id["generic_solar"]["project_code"]

    def test_wind_code_matches_actual_factory(self, baselines_by_id):
        from app.project_factories import create_default_wind_project
        inputs = create_default_wind_project()
        assert inputs.info.code == baselines_by_id["generic_wind"]["project_code"]


class TestManifestRunnerRegistryAlignment:
    """Cross-reference: manifest and legacy_snapshot._BASELINE_REGISTRY must agree."""

    def test_project_type_keys_match_runner_registry(self, baselines_by_id):
        from finco_parity.legacy_snapshot import _BASELINE_REGISTRY
        for bid, b in baselines_by_id.items():
            reg_pt = _BASELINE_REGISTRY[bid]["project_type"]
            assert reg_pt == b["project_type_key"], (
                f"baseline {bid!r}: manifest project_type_key {b['project_type_key']!r} "
                f"!= runner registry project_type {reg_pt!r}"
            )

    def test_factory_functions_match_runner_registry(self, baselines_by_id):
        from finco_parity.legacy_snapshot import _BASELINE_REGISTRY
        for bid, b in baselines_by_id.items():
            reg_src = _BASELINE_REGISTRY[bid]["input_source_id"]
            # Manifest factory_function should contain the same function name
            factory_fn = b["factory_function"].split(".")[-1]
            assert factory_fn in reg_src, (
                f"baseline {bid!r}: manifest factory {factory_fn!r} "
                f"not found in runner input_source_id {reg_src!r}"
            )
