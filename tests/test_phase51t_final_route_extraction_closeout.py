"""Phase 51T — Final route extraction closeout structural tests.

Validates the closeout doc + JSON reflect the post-Phase 51
state and don't overfit to specific prose.
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
CLOSE_DOC = REPO_ROOT / "docs" / "phase51t_final_route_extraction_closeout.md"
CLOSE_JSON = REPO_ROOT / "reports" / "phase51t_final_route_extraction_closeout.json"


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


def _get_route_non_blank(route_path: str) -> int:
    """Return non-blank line count of a route in main_web.py."""
    text = _read(MAIN_WEB)
    pattern = re.escape(f'@app.post("{route_path}")')
    if "{" not in route_path:
        # Try GET as well
        pattern = re.escape(f'@app.(get|post)("{route_path}")')
    m = re.search(
        pattern + r"\s*\nasync def \w+\(.*?(?=\n@app\.(get|post|put|delete|route)\(|\Z)",
        text,
        re.DOTALL,
    )
    if m is None:
        return 0
    body = m.group(0)
    return len([l for l in body.splitlines() if l.strip()])


class TestCloseoutFilesExist:
    def test_doc_exists(self):
        assert CLOSE_DOC.exists()

    def test_json_exists(self):
        assert CLOSE_JSON.exists()

    def test_doc_is_substantial(self):
        assert CLOSE_DOC.stat().st_size > 5000

    def test_json_is_valid(self):
        data = _read_json(CLOSE_JSON)
        assert isinstance(data, dict)


class TestCloseoutJsonStructure:
    def test_phase_field(self):
        assert _read_json(CLOSE_JSON).get("phase") == "51T"

    def test_phase51_complete(self):
        assert _read_json(CLOSE_JSON).get("phase51_complete") is True

    def test_remaining_inline_hotspots_zero(self):
        assert _read_json(CLOSE_JSON).get("remaining_inline_hotspots") == 0

    def test_rc1_touched_false(self):
        assert _read_json(CLOSE_JSON).get("rc1_touched") is False

    def test_production_code_changed_false(self):
        assert _read_json(CLOSE_JSON).get("production_code_changed") is False

    def test_changed_files_in_scope(self):
        # Phase 51T is docs/report/verification only
        files = _read_json(CLOSE_JSON).get("changed_files", ["docs/phase51t_final_route_extraction_closeout.md", "reports/phase51t_final_route_extraction_closeout.json"])
        for f in files:
            assert f.startswith("docs/") or f.startswith("reports/") or f.startswith("tests/")

    def test_includes_390(self):
        assert "390" in str(_read_json(CLOSE_JSON).get("agent_b_prs_integrated", {}))

    def test_includes_394(self):
        assert "394" in str(_read_json(CLOSE_JSON).get("agent_b_prs_integrated", {}))

    def test_includes_398(self):
        assert "398" in str(_read_json(CLOSE_JSON).get("agent_b_prs_integrated", {}))

    def test_18_service_modules(self):
        data = _read_json(CLOSE_JSON)
        assert data["summary"]["service_modules_total"] == 18

    def test_no_go_claims(self):
        data = _read_json(CLOSE_JSON)
        claims = data.get("no_go_claims", [])
        for c in ["no_bankability_claim", "no_saas_ready_claim", "g20_remains_blocked"]:
            assert c in claims

    def test_phase51f_guardrails_pass(self):
        data = _read_json(CLOSE_JSON)
        assert data["phase51f_guardrails"]["engine_output_golden_tubo_oborovo"] == "PASS"
        assert data["phase51f_guardrails"]["parity_core_lock_4_sha256"] == "PASS"
        assert "PASS" in data["phase51f_guardrails"]["no_service_imports_main_web_or_main_api"]

    def test_remaining_risks_documented(self):
        data = _read_json(CLOSE_JSON)
        risks = data.get("remaining_risks", [])
        assert len(risks) >= 5

    def test_recommended_next_steps(self):
        data = _read_json(CLOSE_JSON)
        assert "primary" in data.get("recommended_next_steps", {})


class TestCloseoutDocSections:
    @pytest.mark.parametrize("section", [
        "## Executive summary",
        "## Final route inventory",
        "## Phase 51 completion summary",
        "## Final service inventory",
        "## Hotspot map",
        "## Phase 51F guardrail status",
        "## No-go claims",
        "## Agent A / Agent B boundary",
        "## Remaining risks",
        "## Recommended next steps",
    ])
    def test_section_present(self, section):
        text = _read(CLOSE_DOC)
        assert section in text


class TestServiceCleanlinessFinal:
    def test_no_service_imports_main_web(self):
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
        offenders = []
        for svc in sorted(SERVICES_DIR.glob("*.py")):
            if svc.name in ("__init__.py",):
                continue
            text = _read(svc)
            clean = _strip_docstrings_and_comments(text)
            if re.search(r'^\s*(import|from)\s+main_api', clean, re.MULTILINE):
                offenders.append(svc.name)
        assert not offenders, f"Services importing main_api: {offenders}"


class TestPhase51FGuardrailsPass:
    def test_guardrails_run(self):
        import subprocess
        result = subprocess.run(
            ["python3", "-m", "pytest", "tests/test_phase51f_parallel_work_guardrails.py", "-q", "--tb=line"],
            capture_output=True, text=True, cwd=REPO_ROOT, timeout=120,
        )
        assert "21 passed" in result.stdout or "21 passed" in result.stderr
