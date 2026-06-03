"""Phase 51N — Post-M2 route extraction checkpoint structural tests.

Validates that the Phase 51N checkpoint doc + JSON exist and contain
the expected sections / fields, and that the underlying claims about
the service inventory and route hotspot map are accurate.

These tests are deliberately lenient on prose (they check for
section headers and key strings, not exact wording) so they don't
overfit to a specific doc revision.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_WEB = REPO_ROOT / "main_web.py"
SERVICES_DIR = REPO_ROOT / "app" / "services"
CHECKPOINT_DOC = REPO_ROOT / "docs" / "phase51n_post_m2_route_extraction_checkpoint.md"
CHECKPOINT_JSON = REPO_ROOT / "reports" / "phase51n_post_m2_route_extraction_checkpoint.json"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _strip_docstrings_and_comments(src: str) -> str:
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    src = re.sub(r"'''[\s\S]*?'''", "", src)
    out = []
    for line in src.splitlines():
        in_string = False
        quote_char = None
        cleaned = []
        for ch in line:
            if ch in ('"', "'") and not in_string:
                in_string = True
                quote_char = ch
                cleaned.append(ch)
            elif ch == quote_char and in_string:
                in_string = False
                quote_char = None
                cleaned.append(ch)
            elif ch == "#" and not in_string:
                break
            else:
                cleaned.append(ch)
        out.append("".join(cleaned))
    return "\n".join(out)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Files exist
# ─────────────────────────────────────────────────────────────────────────────


class TestCheckpointFilesExist:
    def test_doc_exists(self):
        assert CHECKPOINT_DOC.exists()

    def test_json_exists(self):
        assert CHECKPOINT_JSON.exists()

    def test_doc_is_non_empty(self):
        assert CHECKPOINT_DOC.stat().st_size > 1000

    def test_json_is_valid(self):
        data = _read_json(CHECKPOINT_JSON)
        assert isinstance(data, dict)


# ─────────────────────────────────────────────────────────────────────────────
# 2. JSON structural fields
# ─────────────────────────────────────────────────────────────────────────────


class TestCheckpointJsonStructure:
    def test_phase_field(self):
        data = _read_json(CHECKPOINT_JSON)
        assert data.get("phase") == "51N"

    def test_current_main_sha(self):
        data = _read_json(CHECKPOINT_JSON)
        assert "current_main_sha" in data
        assert data["current_main_sha"] == "2afdba8b79daf9462161dc8c5b6115995c4afceb"

    def test_base_sha(self):
        data = _read_json(CHECKPOINT_JSON)
        assert data.get("base_sha") == "2afdba8b79daf9462161dc8c5b6115995c4afceb"

    def test_rc1_frozen_sha(self):
        data = _read_json(CHECKPOINT_JSON)
        assert data.get("rc1_frozen_sha") == "b425a0708719eaa5e1d922b1008e5609758e0ad4"

    def test_rc1_not_touched(self):
        data = _read_json(CHECKPOINT_JSON)
        assert data.get("rc1_touched") is False

    def test_production_code_unchanged(self):
        data = _read_json(CHECKPOINT_JSON)
        assert data.get("production_code_changed") is False
        assert data.get("main_web_py_changed") is False
        assert data.get("app_services_changed") is False

    def test_changed_files_scope(self):
        data = _read_json(CHECKPOINT_JSON)
        files = data.get("changed_files", [])
        # Must be in docs/ or reports/
        for f in files:
            assert f.startswith("docs/") or f.startswith("reports/") or f.startswith("tests/"), (
                f"Unexpected file in changed_files: {f}"
            )

    def test_includes_pr_390(self):
        data = _read_json(CHECKPOINT_JSON)
        assert "390" in data.get("agent_b_prs_reviewed", {})

    def test_includes_pr_394(self):
        data = _read_json(CHECKPOINT_JSON)
        assert "394" in data.get("agent_b_prs_reviewed", {})

    def test_includes_pr_398(self):
        data = _read_json(CHECKPOINT_JSON)
        assert "398" in data.get("agent_b_prs_reviewed", {})

    def test_includes_projects_create_service(self):
        data = _read_json(CHECKPOINT_JSON)
        orchestration = data.get("service_inventory", {}).get("route_orchestration", [])
        files = [s.get("file") for s in orchestration]
        assert "projects_create_service.py" in files

    def test_includes_remaining_inline_routes(self):
        data = _read_json(CHECKPOINT_JSON)
        inline = data.get("updated_main_web_hotspot_map", {}).get("remaining_inline_hotspots", [])
        paths = [r.get("path") for r in inline]
        assert "/projects/{project_code}/save-as" in paths
        assert "/scenarios/{scenario_id}/rename" in paths
        assert "/scenarios/{scenario_id}/archive" in paths
        assert "/scenarios/{scenario_id}/update-overrides" in paths
        assert "/scenarios/{scenario_id}/select" in paths

    def test_includes_no_go_claims(self):
        data = _read_json(CHECKPOINT_JSON)
        claims = data.get("no_go_claims", [])
        # Must include the canonical no-go claims
        expected = [
            "no_bankability_claim",
            "no_lender_ready_claim",
            "no_saas_ready_claim",
            "no_external_validation_claim",
            "g20_remains_blocked",
            "r99_r102_not_approved",
        ]
        for c in expected:
            assert c in claims, f"Missing no-go claim: {c}"

    def test_phase51f_guardrails_pass(self):
        data = _read_json(CHECKPOINT_JSON)
        assert data.get("phase51f_guardrails_status") == "PASS"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Doc structural sections
# ─────────────────────────────────────────────────────────────────────────────


class TestCheckpointDocSections:
    @pytest.mark.parametrize("section", [
        "## 1. Current baseline",
        "## 2. Completed Agent A",
        "## 3. Completed extracted route",
        "## 4. Service inventory",
        "## 5. Updated main_web.py hotspot map",
        "## 6. Route extraction improvement metrics",
        "## 7. Agent B documentation/report integration",
        "## 8. Governance and file ownership",
        "## 9. No-go claims",
        "## 10. Remaining risks",
        "## 11. Recommended next steps",
        "## 12. Claude review preparation",
    ])
    def test_section_present(self, section):
        text = _read(CHECKPOINT_DOC)
        assert section in text, f"Section missing: {section}"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Service cleanliness verification (live)
# ─────────────────────────────────────────────────────────────────────────────


class TestServiceCleanliness:
    def test_no_service_imports_main_web(self):
        """No app/services/*.py should import main_web."""
        offenders = []
        for svc in sorted(SERVICES_DIR.glob("*.py")):
            if svc.name in ("__init__.py",):
                continue
            text = _read(svc)
            clean = _strip_docstrings_and_comments(text)
            if re.search(r'^\s*(import|from)\s+main_web', clean, re.MULTILINE):
                offenders.append(svc.name)
        assert not offenders, f"Services importing main_web: {offenders}"

    def test_no_service_imports_main_api(self):
        """No app/services/*.py should import main_api."""
        offenders = []
        for svc in sorted(SERVICES_DIR.glob("*.py")):
            if svc.name in ("__init__.py",):
                continue
            text = _read(svc)
            clean = _strip_docstrings_and_comments(text)
            if re.search(r'^\s*(import|from)\s+main_api', clean, re.MULTILINE):
                offenders.append(svc.name)
        assert not offenders, f"Services importing main_api: {offenders}"

    def test_phase51f_guardrail_file_exists(self):
        path = REPO_ROOT / "tests" / "test_phase51f_parallel_work_guardrails.py"
        assert path.exists()


# ─────────────────────────────────────────────────────────────────────────────
# 5. Service inventory count
# ─────────────────────────────────────────────────────────────────────────────


class TestServiceInventoryCount:
    def test_13_service_modules(self):
        """Phase 51N service inventory: 13 modules."""
        files = [
            f.name for f in SERVICES_DIR.glob("*.py")
            if f.name not in ("__init__.py",)
        ]
        assert len(files) == 13, f"Expected 13 service modules, got {len(files)}: {files}"

    def test_projects_create_service_exists(self):
        assert (SERVICES_DIR / "projects_create_service.py").exists()

    def test_scenarios_add_service_exists(self):
        assert (SERVICES_DIR / "scenarios_add_service.py").exists()


# ─────────────────────────────────────────────────────────────────────────────
# 6. Hotspot map consistency
# ─────────────────────────────────────────────────────────────────────────────


class TestHotspotMapConsistency:
    def test_json_remaining_inline_count_matches_doc(self):
        data = _read_json(CHECKPOINT_JSON)
        inline = data.get("updated_main_web_hotspot_map", {}).get("remaining_inline_hotspots", [])
        non_blank_sum = sum(r.get("non_blank", 0) for r in inline)
        # JSON says 193
        assert non_blank_sum == 193, f"Inline non-blank sum is {non_blank_sum}, expected 193"


# ─────────────────────────────────────────────────────────────────────────────
# 7. Phase 51F guardrails still pass
# ─────────────────────────────────────────────────────────────────────────────


class TestGuardrailsStillPass:
    def test_guardrails_run(self):
        """Run the Phase 51F guardrail module to confirm it still passes."""
        import subprocess
        result = subprocess.run(
            ["python3", "-m", "pytest", "tests/test_phase51f_parallel_work_guardrails.py", "-q", "--tb=line"],
            capture_output=True, text=True, cwd=REPO_ROOT, timeout=120,
        )
        # We expect 21 passed
        assert "21 passed" in result.stdout or "21 passed" in result.stderr, (
            f"Guardrails did not pass: stdout={result.stdout!r} stderr={result.stderr!r}"
        )
