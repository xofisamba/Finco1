import csv
import io
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.export.registry import VALID_CATEGORIES, default_export_registry
from app.export.runtime_summary import (
    RUNTIME_SUMMARY_COLUMNS,
    build_runtime_summary_csv,
    build_runtime_summary_rows,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_REPORT = ROOT / "reports" / "phase10_export_registry.csv"
DOC = ROOT / "docs" / "phase10_excel_parity_export_foundation.md"


def _csv_rows(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


def test_export_registry_exists_and_has_unique_artifacts():
    registry = default_export_registry()
    names = [artifact.artifact_name for artifact in registry.artifacts]
    assert names
    assert len(names) == len(set(names))
    assert REGISTRY_REPORT.exists()


def test_export_artifact_categories_are_valid():
    registry = default_export_registry()
    assert {artifact.category.value for artifact in registry.artifacts}.issubset(
        VALID_CATEGORIES
    )
    rows = list(csv.DictReader(REGISTRY_REPORT.open(newline="", encoding="utf-8")))
    assert {row["category"] for row in rows}.issubset(VALID_CATEGORIES)


def test_runtime_summary_export_generates_tuho_and_oborovo_csvs():
    tuho = _csv_rows(
        build_runtime_summary_csv(
            "tuho",
            generated_at="2026-05-22T00:00:00+00:00",
            source_branch="test",
        )
    )
    oborovo = _csv_rows(
        build_runtime_summary_csv(
            "oborovo",
            generated_at="2026-05-22T00:00:00+00:00",
            source_branch="test",
        )
    )

    assert tuho
    assert oborovo
    assert set(tuho[0].keys()) == set(RUNTIME_SUMMARY_COLUMNS)
    assert tuho != oborovo
    assert tuho[0]["project"] != oborovo[0]["project"]


def test_runtime_exports_contain_governance_labels_timestamps_and_runtime_status():
    rows = build_runtime_summary_rows(
        "tuho",
        generated_at="2026-05-22T00:00:00+00:00",
        source_branch="test",
    )
    assert {row["runtime_or_preview"] for row in rows} == {"runtime"}
    assert {row["g20_status"] for row in rows} == {"BLOCKED"}
    assert {row["r99_r102_status"] for row in rows} == {"NOT APPROVED"}
    assert {row["generated_at"] for row in rows} == {"2026-05-22T00:00:00+00:00"}
    assert any(row["metric"] == "total_distributions_keur" for row in rows)
    assert any(row["metric"] == "total_shl_service_keur" for row in rows)


def test_downloads_tab_renders_export_registry_entries():
    env = Environment(loader=FileSystemLoader(ROOT / "app" / "templates"))
    template = env.get_template("partials/export_registry.html")
    rendered = template.render()
    assert "Phase 10 Export Registry" in rendered
    assert "TUHO Runtime Summary CSV" in rendered
    assert "Oborovo Runtime Summary CSV" in rendered
    assert "G20 BLOCKED" in rendered
    assert "R99/R102 NOT APPROVED" in rendered


def test_runtime_summary_route_is_registered_without_preview_label():
    main_web = (ROOT / "main_web.py").read_text(encoding="utf-8")
    assert '@app.get("/exports/runtime-summary.csv")' in main_web
    assert "build_runtime_summary_csv(project)" in main_web
    assert "runtime_or_preview" not in main_web


def test_docs_state_no_runtime_changes_and_governance_status():
    text = DOC.read_text(encoding="utf-8")
    assert "No runtime formulas" in text
    assert "G20 remains `BLOCKED`" in text
    assert "R99/R102 remains `NOT APPROVED`" in text
