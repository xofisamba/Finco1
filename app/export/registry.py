"""Lightweight export artifact registry for Phase 10.

The registry centralizes artifact names, categories, scope, and governance
labels. It deliberately avoids recalculating model outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import csv


class ExportCategory(StrEnum):
    PARITY = "parity"
    RUNTIME = "runtime"
    GOVERNANCE = "governance"
    AUDIT = "audit"
    VALIDATION = "validation"
    WORKBOOK = "workbook"
    SOURCE_MAP = "source_map"


VALID_CATEGORIES = {category.value for category in ExportCategory}


@dataclass(frozen=True)
class ExportArtifact:
    artifact_name: str
    category: ExportCategory
    project_scope: str
    format: str
    runtime_or_preview: str
    governance_sensitive: bool
    current_status: str
    description: str
    path: str
    notes: str = ""

    def to_report_row(self) -> dict[str, str]:
        return {
            "artifact_name": self.artifact_name,
            "category": self.category.value,
            "project_scope": self.project_scope,
            "format": self.format,
            "runtime_or_preview": self.runtime_or_preview,
            "governance_sensitive": "yes" if self.governance_sensitive else "no",
            "current_status": self.current_status,
            "notes": self.notes or self.description,
        }


class ExportRegistry:
    def __init__(self, artifacts: tuple[ExportArtifact, ...]):
        names = [artifact.artifact_name for artifact in artifacts]
        if len(names) != len(set(names)):
            raise ValueError("Export artifact names must be unique")
        self._artifacts = artifacts

    @property
    def artifacts(self) -> tuple[ExportArtifact, ...]:
        return self._artifacts

    def by_category(self, category: ExportCategory) -> tuple[ExportArtifact, ...]:
        return tuple(
            artifact for artifact in self._artifacts if artifact.category == category
        )

    def to_report_rows(self) -> list[dict[str, str]]:
        return [artifact.to_report_row() for artifact in self._artifacts]


def default_export_registry() -> ExportRegistry:
    return ExportRegistry(
        (
            ExportArtifact(
                artifact_name="TUHO full line-item horizontal review workbook",
                category=ExportCategory.PARITY,
                project_scope="TUHO",
                format="xlsx",
                runtime_or_preview="review",
                governance_sensitive=True,
                current_status="accepted_with_minor_follow_up",
                description="Corrected horizontal reviewer workbook from Phase 9.",
                path="reports/phase9_tuho_full_line_item_horizontal_review_workbook.xlsx",
                notes="Primary parity evidence base; G20 still requires stakeholder gate sign-off.",
            ),
            ExportArtifact(
                artifact_name="TUHO final parity closeout status",
                category=ExportCategory.GOVERNANCE,
                project_scope="TUHO",
                format="csv",
                runtime_or_preview="review",
                governance_sensitive=True,
                current_status="g20_blocked_pending_stakeholder_acceptance",
                description="Final TUHO parity closeout status register.",
                path="reports/phase9_final_tuho_parity_closeout_status.csv",
                notes="No runtime approval implied.",
            ),
            ExportArtifact(
                artifact_name="Phase 10 runtime summary export",
                category=ExportCategory.RUNTIME,
                project_scope="TUHO, Oborovo",
                format="csv",
                runtime_or_preview="runtime",
                governance_sensitive=True,
                current_status="foundation",
                description="Standardized project runtime summary with provenance metadata.",
                path="/exports/runtime-summary.csv",
                notes="Values are sourced from existing runtime outputs.",
            ),
            ExportArtifact(
                artifact_name="Phase 10 institutional workbook skeleton",
                category=ExportCategory.WORKBOOK,
                project_scope="TUHO, Oborovo",
                format="xlsx",
                runtime_or_preview="runtime",
                governance_sensitive=True,
                current_status="foundation",
                description="Institutional workbook skeleton with governance and runtime summary sheets.",
                path="/exports/institutional-workbook.xlsx",
                notes="Structured review workbook only; placeholder sheets do not fabricate values.",
            ),
            ExportArtifact(
                artifact_name="Phase 10 export registry",
                category=ExportCategory.VALIDATION,
                project_scope="portfolio",
                format="csv",
                runtime_or_preview="review",
                governance_sensitive=False,
                current_status="foundation",
                description="Registry of known exports and governance labels.",
                path="reports/phase10_export_registry.csv",
                notes="Centralizes artifact metadata for reviewer workflows.",
            ),
            ExportArtifact(
                artifact_name="TUHO horizontal source map",
                category=ExportCategory.SOURCE_MAP,
                project_scope="TUHO",
                format="csv",
                runtime_or_preview="review",
                governance_sensitive=True,
                current_status="available",
                description="Source map for the corrected TUHO horizontal workbook.",
                path="reports/phase9_tuho_full_line_item_horizontal_source_map.csv",
                notes="Keeps missing evidence explicit rather than silently filling values.",
            ),
            ExportArtifact(
                artifact_name="TUHO horizontal gap analysis",
                category=ExportCategory.AUDIT,
                project_scope="TUHO",
                format="csv",
                runtime_or_preview="review",
                governance_sensitive=True,
                current_status="available",
                description="Gap register backing the corrected TUHO horizontal workbook.",
                path="reports/phase9_tuho_full_line_item_horizontal_gap_analysis.csv",
                notes="G20 and R99/R102 rows remain governance blockers.",
            ),
            ExportArtifact(
                artifact_name="Financial statements audit workbook",
                category=ExportCategory.WORKBOOK,
                project_scope="TUHO, Oborovo",
                format="xlsx",
                runtime_or_preview="audit",
                governance_sensitive=True,
                current_status="available",
                description="Offline financial statements audit workbook export.",
                path="domain/financial_statements/export_excel.py",
                notes="Existing Stage 4 export helper; not rewritten in this branch.",
            ),
        )
    )


def write_export_registry_csv(path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = default_export_registry().to_report_rows()
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "artifact_name",
                "category",
                "project_scope",
                "format",
                "runtime_or_preview",
                "governance_sensitive",
                "current_status",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    return output_path
