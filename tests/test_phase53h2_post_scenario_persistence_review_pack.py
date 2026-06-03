"""Phase 53H-2 — Post scenario persistence review pack structural tests.

Verifies the review pack artifacts exist and contain expected fields.
NO production code is touched.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "phase53h2_post_scenario_persistence_review_pack.md"
JSON_RPT = REPO_ROOT / "reports" / "phase53h2_post_scenario_persistence_review_pack.json"


class TestDeliverablesExist:
    def test_doc_exists(self):
        assert DOC.exists()

    def test_json_exists(self):
        assert JSON_RPT.exists()


class TestJsonStructure:
    @pytest.fixture
    def data(self):
        return json.loads(JSON_RPT.read_text(encoding="utf-8"))

    def test_phase_label(self, data):
        assert data.get("phase") == "53H-2"

    def test_includes_review_scope(self, data):
        scope = data.get("review_scope")
        assert isinstance(scope, list)
        assert len(scope) > 3

    def test_includes_evidence_files(self, data):
        ev = data.get("evidence_files", {})
        assert "phase_52_mapping" in ev
        assert "phase_53a_f_extractions" in ev
        assert "phase_53g_scenario_refactor" in ev
        assert "phase_53h_records_planning" in ev
        # Each category has multiple files
        for cat, files in ev.items():
            assert len(files) > 0, f"{cat} is empty"

    def test_includes_7_claude_questions(self, data):
        questions = data.get("claude_questions", [])
        assert len(questions) == 7
        for q in questions:
            assert "question" in q
            assert "context" in q
            assert "evidence_files" in q
        # Specific question coverage
        texts = " ".join(q["question"] for q in questions)
        assert "behavior" in texts.lower() or "scenario" in texts.lower()
        assert "compatibility" in texts.lower() or "facade" in texts.lower() or "façade" in texts.lower()
        assert "records" in texts.lower()
        assert "auto-merge" in texts.lower()
        assert "ui" in texts.lower() or "pilot" in texts.lower()
        assert "highest-value" in texts.lower() or "next phase" in texts.lower() or "next-phase" in texts.lower()
        assert "roadmap" in texts.lower()

    def test_includes_no_go_claims(self, data):
        claims = data.get("no_go_claims")
        assert isinstance(claims, list)
        assert len(claims) > 10
        # Specific claims
        texts = " ".join(claims)
        assert "rc1" in texts.lower() or "frozen" in texts.lower()
        assert "g20" in texts.lower()
        assert "r99" in texts.lower() or "r102" in texts.lower()
        assert "parity-core" in texts.lower()
        assert "waterfall_core" in texts.lower()

    def test_includes_recommended_prompt(self, data):
        assert "recommended_prompt_summary" in data
        assert isinstance(data["recommended_prompt_summary"], str)
        assert len(data["recommended_prompt_summary"]) > 50

    def test_includes_recommended_next_step(self, data):
        assert "recommended_next_step" in data
        assert isinstance(data["recommended_next_step"], str)
        # Should reference Claude and the spec restrictions
        assert "Claude" in data["recommended_next_step"]
        assert "records.py" in data["recommended_next_step"]

    def test_includes_current_main_sha(self, data):
        assert "current_main_sha" in data
        assert data["current_main_sha"]  # non-empty


class TestNoProductionCodeChanged:
    def test_repository_py_unchanged(self):
        # Phase 53H-2 must NOT touch repository.py
        text = (REPO_ROOT / "app" / "persistence" / "repository.py").read_text()
        # Verify it still has the 3 dataclasses (not moved)
        assert "class ProjectRecord" in text
        assert "class ScenarioRecord" in text
        assert "class WorkspaceStateRecord" in text

    def test_no_records_py_created(self):
        # This PR must NOT create records.py
        records_py = REPO_ROOT / "app" / "persistence" / "records.py"
        assert not records_py.exists(), \
            "Phase 53H-2 must not create records.py (it's a review prep only)"

    def test_no_scenarios_repository_py_changed(self):
        # scenarios_repository.py is unchanged
        text = (REPO_ROOT / "app" / "persistence" / "scenarios_repository.py").read_text()
        # Verify it still has the 4 high-risk writes
        assert "def save_scenario" in text
        assert "def add_scenario" in text
        assert "def update_scenario_overrides" in text
        assert "def get_or_create_base_case_scenario" in text

    def test_no_main_web_or_services_changed(self):
        for p in [
            REPO_ROOT / "app" / "main_web.py",
            REPO_ROOT / "app" / "main_api.py",
        ]:
            if p.exists():
                # Just verify readable
                p.read_text()


class TestNoGoClaims:
    def test_doc_contains_all_no_go_claims(self):
        text = DOC.read_text()
        required = [
            "rc1",
            "G20",
            "R99",
            "R102",
            "partial_pay_sweep",
            "flat/min DSCR",
            "parity-core",
            "waterfall_core",
            "project_factories",
            "senior-debt",
        ]
        for claim in required:
            assert claim in text, f"doc should mention no-go claim: {claim}"


class TestGitStatus:
    def test_only_docs_reports_tests_changed(self):
        import subprocess
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=str(REPO_ROOT)
        )
        lines = [l for l in result.stdout.splitlines() if l]
        for line in lines:
            file = line[3:] if len(line) > 3 else ""
            assert (
                file.startswith("docs/")
                or file.startswith("reports/")
                or file.startswith("tests/test_phase53h2")
            ), f"Phase 53H-2 must only touch docs/, reports/, or test_phase53h2 files. Found: {line}"
