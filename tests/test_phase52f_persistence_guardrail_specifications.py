"""Phase 52F — Persistence guardrail specifications structural tests.

Validates the spec doc + JSON reflect the guardrail inventory and the
G1-G6 implemented / D1-D4 deferred split.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "phase52f_persistence_guardrail_specifications.md"
JSON_REPORT = REPO_ROOT / "reports" / "phase52f_persistence_guardrail_specifications.json"
GUARDRAIL_REGRESSION_TEST = REPO_ROOT / "tests" / "test_phase52f_persistence_guardrail_regression.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def data() -> Dict[str, Any]:
    return _read_json(JSON_REPORT)


class TestDocsAndJsonExist:
    def test_doc_exists(self):
        assert DOC.exists()
    def test_json_exists(self):
        assert JSON_REPORT.exists()
    def test_doc_mentions_phase_52f(self):
        assert "Phase 52F" in _read(DOC)


class TestExistingGuardrails:
    def test_existing_guardrails_present(self, data):
        assert "existing_guardrails" in data
        assert len(data["existing_guardrails"]) == 4
        assert data["total_existing_guardrail_tests"] == 21


class TestImplementedGuardrails:
    def test_implemented_guardrails_count(self, data):
        assert len(data["implemented_guardrails"]) == 6

    def test_implemented_guardrails_have_test_classes(self, data):
        for g in data["implemented_guardrails"]:
            assert "test_class" in g
            assert g["test_class"].startswith("TestG")

    def test_implemented_total_tests(self, data):
        assert data["implemented_total_tests"] == 10

    def test_guardrail_regression_test_file_exists(self):
        assert GUARDRAIL_REGRESSION_TEST.exists()


class TestDeferredGuardrails:
    def test_deferred_guardrails_count(self, data):
        assert len(data["deferred_guardrails"]) == 4

    def test_deferred_includes_route_no_refattening(self, data):
        names = {g["name"] for g in data["deferred_guardrails"]}
        assert "route no-refattening" in names

    def test_deferred_includes_ui_context_key_contract(self, data):
        names = {g["name"] for g in data["deferred_guardrails"]}
        assert "UI context key contract" in names

    def test_deferred_includes_docs_no_go_scanner(self, data):
        names = {g["name"] for g in data["deferred_guardrails"]}
        assert "docs no-go scanner" in names


class TestFalsePositiveRisks:
    def test_false_positive_risks_present(self, data):
        assert "false_positive_risks" in data
        for k in ("G1", "G2", "G3", "G4", "G5", "G6"):
            assert k in data["false_positive_risks"]


class TestRequiredBeforePhase:
    def test_phase53_required_guardrails(self, data):
        assert "phase53_required_guardrails" in data
        assert set(data["phase53_required_guardrails"]) == {"G1","G2","G3","G4","G5","G6"}

    def test_phase54_required_guardrails(self, data):
        assert "phase54_required_guardrails" in data
        assert "D3" in data["phase54_required_guardrails"]


class TestProposedGuardrails:
    def test_proposed_guardrails_total(self, data):
        assert len(data["proposed_guardrails"]) == 10

    def test_proposed_includes_all_6_G(self, data):
        ids = {g["id"] for g in data["proposed_guardrails"]}
        for g in ("G1","G2","G3","G4","G5","G6"):
            assert g in ids

    def test_proposed_includes_all_4_D(self, data):
        ids = {g["id"] for g in data["proposed_guardrails"]}
        for d in ("D1","D2","D3","D4"):
            assert d in ids


class TestRecommendedNextStep:
    def test_recommended_next_step(self, data):
        assert data.get("recommended_next_step") == "52G Phase 52 closeout"
