"""Phase 12 closeout cleanup tests."""

from __future__ import annotations

import csv
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORTS = ROOT / "reports"


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_stale_co2_balancing_tests_now_expect_source_not_available():
    co2_test = (ROOT / "tests" / "test_phase10_co2_balancing_source_map_hardening.py").read_text(encoding="utf-8")
    pack_test = (ROOT / "tests" / "test_phase10_calibration_reconciliation_pack.py").read_text(encoding="utf-8")

    assert "SOURCE_NOT_AVAILABLE" in co2_test
    assert "MISSING_EVIDENCE" not in co2_test
    assert "SOURCE_NOT_AVAILABLE" in pack_test


def test_top_level_persistence_directory_no_longer_has_live_package_files():
    assert not (ROOT / "persistence" / "__init__.py").exists()
    assert not (ROOT / "persistence" / "repository.py").exists()
    assert not (ROOT / "persistence" / "database.py").exists()


def test_domain_persistence_directory_no_longer_has_live_package_files():
    domain_dir = ROOT / "domain" / "persistence"
    assert not (domain_dir / "__init__.py").exists()
    assert not any(domain_dir.glob("*.py"))


def test_app_persistence_still_exists():
    assert (ROOT / "app" / "persistence" / "__init__.py").exists()
    assert (ROOT / "app" / "persistence" / "db.py").exists()
    assert (ROOT / "app" / "persistence" / "repository.py").exists()


def test_persistence_consolidation_doc_exists():
    assert (DOCS / "phase12_persistence_consolidation.md").exists()


def test_governance_semantics_doc_includes_migration_status_table():
    text = (DOCS / "phase12_governance_semantics_cleanup.md").read_text(encoding="utf-8")
    assert "Migration-status table for remaining `MISSING_EVIDENCE` usage" in text
    assert "LEGACY_FROZEN_REFERENCE" in text
    assert "ACTIVE_TO_MIGRATE_LATER" in text
    assert "INTENTIONALLY_RETAINED" in text
    assert "REPLACED_BY_PRECISE_LABEL" in text


def test_closeout_cleanup_reports_exist():
    assert (REPORTS / "phase12_closeout_cleanup_summary.csv").exists()
    assert (REPORTS / "phase12_persistence_orphan_removal.csv").exists()


def test_closeout_cleanup_summary_contains_required_rows():
    rows = _csv_rows(REPORTS / "phase12_closeout_cleanup_summary.csv")
    items = {row["item"] for row in rows}
    assert "stale CO2 test assertions fixed" in items
    assert "top-level persistence removed" in items
    assert "domain/persistence removed" in items
    assert "persistence consolidation doc added" in items
    assert "MISSING_EVIDENCE boundary clarified" in items
    assert "G20 remains BLOCKED" in items
    assert "R99/R102 remain NOT APPROVED" in items


def test_governance_posture_unchanged_in_docs():
    persistence_doc = (DOCS / "phase12_persistence_consolidation.md").read_text(encoding="utf-8")
    semantics_doc = (DOCS / "phase12_governance_semantics_cleanup.md").read_text(encoding="utf-8")
    assert "G20" in persistence_doc and "BLOCKED" in persistence_doc
    assert "R99/R102" in persistence_doc and "NOT APPROVED" in persistence_doc
    assert "G20" in semantics_doc and "BLOCKED" in semantics_doc
    assert "R99/R102" in semantics_doc and "NOT APPROVED" in semantics_doc


def test_no_runtime_model_formula_files_changed():
    result = subprocess.run(
        ["git", "diff", "--name-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    changed = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    forbidden_prefixes = (
        "domain/waterfall",
        "domain/shl",
        "domain/tax",
        "app/waterfall",
        "app/ui_runner.py",
        "app/project_factories.py",
    )
    offenders = [path for path in changed if path.replace("\\", "/").startswith(forbidden_prefixes)]
    assert not offenders, offenders
