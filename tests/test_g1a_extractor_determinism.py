"""G1A-EXTRACTOR tests: fixture/manifest schema validity and determinism.

These tests validate the Generic Solar / Generic Wind Tier-1 extraction
pipeline (scripts/extract_generic_golden.py) without touching any Finco1
runtime code. They assert:
  - the fixtures and manifests on disk satisfy the required schema
  - re-running the extractor produces byte-for-byte identical output
  - the recorded workbook SHA256 matches the actual committed workbook
"""
from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures"
MANIFEST_DIR = FIXTURE_DIR / "excel_reference"
REF_MODEL_DIR = REPO_ROOT / "validation" / "reference_models"
EXTRACTOR_SCRIPT = REPO_ROOT / "scripts" / "extract_generic_golden.py"

PROJECTS = ["generic_solar", "generic_wind"]

REQUIRED_ANCHORS = {
    "total_revenue_keur",
    "total_opex_keur",
    "total_ebitda_keur",
    "total_capex_keur",
    "idc_keur",
    "bank_fees_keur",
    "senior_debt_keur",
    "senior_debt_service_p1_keur",
    "senior_debt_service_p2_keur",
    "senior_debt_service_p3_keur",
    "avg_dscr",
    "min_dscr",
    "project_irr",
    "equity_irr",
    "realized_gearing",
}


def _fixture_path(project: str) -> Path:
    return FIXTURE_DIR / f"excel_golden_{project}.json"


def _manifest_path(project: str) -> Path:
    return MANIFEST_DIR / f"{project}_manifest.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("project", PROJECTS)
def test_fixture_exists_and_is_valid_json(project: str) -> None:
    data = json.loads(_fixture_path(project).read_text())
    assert data["project"] == project


@pytest.mark.parametrize("project", PROJECTS)
def test_fixture_schema(project: str) -> None:
    data = json.loads(_fixture_path(project).read_text())

    for key in (
        "project",
        "source_workbook",
        "workbook_sha256",
        "extraction_note",
        "extraction_date",
        "spec_version",
        "extractor_version",
        "worksheets",
        "golden_cells",
        "initial_tolerances",
    ):
        assert key in data, f"{project} fixture missing top-level key {key!r}"

    assert isinstance(data["worksheets"], dict)
    assert "Summary" in data["worksheets"]
    assert isinstance(data["golden_cells"], dict)
    assert isinstance(data["initial_tolerances"], dict)
    assert len(data["workbook_sha256"]) == 64


@pytest.mark.parametrize("project", PROJECTS)
def test_fixture_has_exactly_tier1_anchors(project: str) -> None:
    data = json.loads(_fixture_path(project).read_text())
    assert set(data["golden_cells"]) == REQUIRED_ANCHORS
    assert set(data["initial_tolerances"]) == REQUIRED_ANCHORS


@pytest.mark.parametrize("project", PROJECTS)
def test_fixture_anchors_are_traceable_to_summary_cells(project: str) -> None:
    data = json.loads(_fixture_path(project).read_text())

    for anchor, info in data["golden_cells"].items():
        assert info["sheet"] == "Summary", anchor
        assert info["cell"].startswith("C"), anchor
        assert isinstance(info["formula"], str) and info["formula"].startswith("="), anchor
        assert isinstance(info["value"], (int, float)), anchor


@pytest.mark.parametrize("project", PROJECTS)
def test_fixture_no_wallclock_timestamp_drift(project: str) -> None:
    """extraction_date must come from the workbook's own embedded metadata,
    not from "now" -- re-running the extractor must not change it."""
    data = json.loads(_fixture_path(project).read_text())
    assert data["extraction_date"]
    # ISO-8601, parseable, but deliberately not compared to wall-clock time.
    assert "T" in data["extraction_date"]


@pytest.mark.parametrize("project", PROJECTS)
def test_manifest_schema(project: str) -> None:
    manifest = json.loads(_manifest_path(project).read_text())

    for key in (
        "workbook_filename",
        "workbook_path",
        "workbook_sha256",
        "extractor_version",
        "extraction_script",
        "spec_version",
        "anchor_list",
        "fixture_path",
    ):
        assert key in manifest, f"{project} manifest missing key {key!r}"

    assert manifest["extraction_script"] == "scripts/extract_generic_golden.py"
    assert set(manifest["anchor_list"]) == REQUIRED_ANCHORS
    assert len(manifest["workbook_sha256"]) == 64


@pytest.mark.parametrize("project", PROJECTS)
def test_manifest_and_fixture_hashes_agree(project: str) -> None:
    manifest = json.loads(_manifest_path(project).read_text())
    fixture = json.loads(_fixture_path(project).read_text())
    assert manifest["workbook_sha256"] == fixture["workbook_sha256"]


@pytest.mark.parametrize("project", PROJECTS)
def test_workbook_hash_matches_committed_file(project: str) -> None:
    manifest = json.loads(_manifest_path(project).read_text())
    workbook_path = REPO_ROOT / manifest["workbook_path"]
    assert workbook_path.exists()
    assert _sha256(workbook_path) == manifest["workbook_sha256"]


def test_extraction_succeeds_and_is_idempotent(tmp_path) -> None:
    """Running the extractor twice against the unchanged committed
    workbooks must produce byte-for-byte identical fixtures and manifests
    (determinism requirement)."""
    before = {
        p: _fixture_path(p).read_bytes() for p in PROJECTS
    }
    before_manifests = {
        p: _manifest_path(p).read_bytes() for p in PROJECTS
    }

    result = subprocess.run(
        [sys.executable, str(EXTRACTOR_SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    for p in PROJECTS:
        assert _fixture_path(p).read_bytes() == before[p], f"{p} fixture changed after re-run"
        assert _manifest_path(p).read_bytes() == before_manifests[p], f"{p} manifest changed after re-run"


def test_extractor_module_imports_without_runtime_engine_dependency() -> None:
    """The extractor must not import any Finco1 runtime/domain modules."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        module = importlib.import_module("extract_generic_golden")
    finally:
        sys.path.pop(0)

    forbidden_imports = (
        "waterfall_core",
        "project_factories",
        "input_adapter",
    )
    source_lines = Path(module.__file__).read_text().splitlines()
    import_lines = [
        line for line in source_lines
        if line.strip().startswith("import ") or line.strip().startswith("from ")
    ]
    for token in forbidden_imports:
        assert not any(token in line for line in import_lines), (
            f"forbidden runtime module reference in import statement: {token}"
        )
