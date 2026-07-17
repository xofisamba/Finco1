"""
Phase 1A — Tests for finco_parity/baselines/manifest.json.

Validates structural integrity and cross-references against known codebase facts.
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
    "technology",
    "factory_function",
    "run_path",
    "engine_designation",
    "frozen_fixture_active",
    "notes",
}


@pytest.fixture(scope="module")
def manifest() -> dict:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return data


@pytest.fixture(scope="module")
def baselines(manifest) -> list[dict]:
    return manifest["baselines"]


@pytest.fixture(scope="module")
def baselines_by_id(baselines) -> dict[str, dict]:
    return {b["baseline_id"]: b for b in baselines}


class TestManifestStructure:
    def test_manifest_file_exists(self):
        assert MANIFEST_PATH.exists(), f"manifest not found at {MANIFEST_PATH}"

    def test_manifest_is_valid_json(self):
        json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))  # no exception

    def test_manifest_version_present(self, manifest):
        assert "manifest_version" in manifest

    def test_baselines_key_present(self, manifest):
        assert "baselines" in manifest
        assert isinstance(manifest["baselines"], list)

    def test_exactly_four_baselines(self, baselines):
        assert len(baselines) == 4

    def test_baseline_ids_correct(self, baselines_by_id):
        assert set(baselines_by_id.keys()) == EXPECTED_BASELINE_IDS

    def test_required_keys_present_on_each_baseline(self, baselines):
        for b in baselines:
            missing = _REQUIRED_BASELINE_KEYS - b.keys()
            assert not missing, f"baseline {b.get('baseline_id')!r} missing keys: {missing}"

    def test_notes_is_list_of_strings(self, baselines):
        for b in baselines:
            assert isinstance(b["notes"], list), f"{b['baseline_id']}: notes must be a list"
            for note in b["notes"]:
                assert isinstance(note, str), f"{b['baseline_id']}: note must be a string"

    def test_frozen_fixture_active_is_bool(self, baselines):
        for b in baselines:
            assert isinstance(b["frozen_fixture_active"], bool)


class TestManifestTUHO:
    def test_tuho_project_type_key(self, baselines_by_id):
        assert baselines_by_id["tuho"]["project_type_key"] == "TUHO"

    def test_tuho_project_code(self, baselines_by_id):
        assert baselines_by_id["tuho"]["project_code"] == "TUHO-WIND-1"

    def test_tuho_technology(self, baselines_by_id):
        assert baselines_by_id["tuho"]["technology"] == "wind"

    def test_tuho_frozen_fixture_active(self, baselines_by_id):
        assert baselines_by_id["tuho"]["frozen_fixture_active"] is True

    def test_tuho_frozen_fixture_path_present(self, baselines_by_id):
        assert baselines_by_id["tuho"]["frozen_fixture_path"] is not None

    def test_tuho_factory_references_correct_function(self, baselines_by_id):
        assert "create_default_tuho_wind1" in baselines_by_id["tuho"]["factory_function"]

    def test_tuho_identity_guard_present(self, baselines_by_id):
        assert baselines_by_id["tuho"]["identity_guard"] is not None


class TestManifestOborovo:
    def test_oborovo_project_type_key(self, baselines_by_id):
        assert baselines_by_id["oborovo"]["project_type_key"] == "Oborovo"

    def test_oborovo_project_code(self, baselines_by_id):
        assert baselines_by_id["oborovo"]["project_code"] == "OBOROVO-SOLAR-1"

    def test_oborovo_technology(self, baselines_by_id):
        assert baselines_by_id["oborovo"]["technology"] == "solar"

    def test_oborovo_frozen_fixture_active(self, baselines_by_id):
        assert baselines_by_id["oborovo"]["frozen_fixture_active"] is True

    def test_oborovo_factory_references_correct_function(self, baselines_by_id):
        assert "create_default_oborovo" in baselines_by_id["oborovo"]["factory_function"]


class TestManifestGenericProjects:
    def test_generic_solar_project_type_key(self, baselines_by_id):
        assert baselines_by_id["generic_solar"]["project_type_key"] == "Test 1"

    def test_generic_wind_project_type_key(self, baselines_by_id):
        assert baselines_by_id["generic_wind"]["project_type_key"] == "Test 2"

    def test_generic_solar_no_frozen_fixture(self, baselines_by_id):
        assert baselines_by_id["generic_solar"]["frozen_fixture_active"] is False

    def test_generic_wind_no_frozen_fixture(self, baselines_by_id):
        assert baselines_by_id["generic_wind"]["frozen_fixture_active"] is False

    def test_generic_solar_no_identity_guard(self, baselines_by_id):
        assert baselines_by_id["generic_solar"]["identity_guard"] is None

    def test_generic_wind_no_identity_guard(self, baselines_by_id):
        assert baselines_by_id["generic_wind"]["identity_guard"] is None

    def test_generic_solar_capacity(self, baselines_by_id):
        assert baselines_by_id["generic_solar"]["capacity_mw"] == 50

    def test_generic_wind_capacity(self, baselines_by_id):
        assert baselines_by_id["generic_wind"]["capacity_mw"] == 40
