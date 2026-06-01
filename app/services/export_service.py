"""Export service — extracted from main_web.py for Phase 49B.

This module provides export/download orchestration functions that were
previously embedded directly in main_web.py route handlers.

All functions are behavior-preserving — no financial formulas, runtime
calculations, or model output changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi.responses import HTMLResponse, StreamingResponse

from app.export.runtime_summary import build_runtime_summary_csv, build_runtime_summary_rows
from app.export.institutional_workbook import export_institutional_workbook_skeleton


@dataclass(frozen=True)
class ExportResponse:
    """Result of an export service function — route handler composes the response."""
    bytes_data: bytes | None = None
    filename: str | None = None
    media_type: str | None = None
    status_code: int = 200
    error_content: str | None = None  # HTML error page content
    headers: dict | None = None

    def has_error(self) -> bool:
        return self.error_content is not None

    def has_bytes(self) -> bool:
        return self.bytes_data is not None


def _make_streaming_response(export: ExportResponse) -> StreamingResponse | HTMLResponse:
    """Convert an ExportResponse to the appropriate FastAPI response."""
    if export.has_error():
        return HTMLResponse(content=export.error_content, status_code=export.status_code)
    return StreamingResponse(
        iter([export.bytes_data]),
        media_type=export.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{export.filename}"',
            "Content-Length": str(len(export.bytes_data)),
        },
    )


# ── Values-only Excel export ────────────────────────────────────────────────

def build_values_only_export_for_project(
    project_type: str,
    scenario: str,
    *,
    project_inputs_override=None,
    runtime_origin: str = "factory_base_runtime",
    replay_metadata: dict | None = None,
) -> ExportResponse:
    """Build values-only Excel export bytes and metadata.

    Behavior matches the original download_post/download_get logic in main_web.py.
    """
    from app.excel_export import build_excel_export
    from app.ui_runner import run_demo_project

    try:
        demo = run_demo_project(
            project_type if project_type else "Solar",
            scenario if scenario else "Base",
            project_inputs_override=project_inputs_override,
        )
        filename = f"fincogpt_{project_type.lower()}_{scenario.lower()}.xlsx"
        excel_bytes = build_excel_export(
            result=demo.result,
            project_inputs=demo.project_inputs,
            provenance_metadata=replay_metadata or {},
        )
        return ExportResponse(
            bytes_data=excel_bytes,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            status_code=200,
            headers={
                "Content-Length": str(len(excel_bytes)),
            },
        )
    except (ValueError, Exception) as e:
        return ExportResponse(
            status_code=400,
            error_content=(
                f"<html><body><h2>Excel generation failed</h2>"
                f"<p>Invalid input: {str(e)}</p><a href='/'>Back</a></body></html>"
            ),
        )


# ── Runtime Summary CSV export ───────────────────────────────────────────────

def build_runtime_summary_csv_export(
    runtime_project_code: str,
    *,
    safe_project: str | None = None,
    project_record=None,
    user_id=None,
) -> ExportResponse:
    """Build runtime summary CSV bytes and metadata.

    Behavior matches the original runtime_summary_export logic in main_web.py.
    """
    try:
        runtime_rows = build_runtime_summary_rows(runtime_project_code)
        csv_text = build_runtime_summary_csv(
            runtime_project_code,
            generated_at=runtime_rows[0]["generated_at"],
            source_branch=runtime_rows[0]["source_branch"],
        )
    except ValueError as exc:
        return ExportResponse(
            status_code=400,
            error_content=(
                f"<html><body><h2>Runtime summary export failed</h2>"
                f"<p>{str(exc)}</p><a href='/'>Back</a></body></html>"
            ),
        )

    filename = f"phase10_{safe_project or runtime_project_code}_runtime_summary.csv"
    data = csv_text.encode("utf-8")
    return ExportResponse(
        bytes_data=data,
        filename=filename,
        media_type="text/csv",
        status_code=200,
        headers={
            "Content-Length": str(len(data)),
        },
    )


# ── Institutional Workbook export ─────────────────────────────────────────────

def build_institutional_workbook_export(
    runtime_project_code: str,
    *,
    safe_project: str | None = None,
    project_record=None,
    user_id=None,
) -> ExportResponse:
    """Build institutional workbook bytes and metadata.

    Behavior matches the original institutional_workbook_export logic in main_web.py.
    """
    try:
        runtime_rows = build_runtime_summary_rows(runtime_project_code)
        workbook_bytes = export_institutional_workbook_skeleton(runtime_project_code)
    except ValueError as exc:
        return ExportResponse(
            status_code=400,
            error_content=(
                f"<html><body><h2>Institutional workbook export failed</h2>"
                f"<p>{str(exc)}</p><a href='/'>Back</a></body></html>"
            ),
        )

    filename = f"phase10_{safe_project or runtime_project_code}_institutional_workbook_skeleton.xlsx"
    return ExportResponse(
        bytes_data=workbook_bytes,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        status_code=200,
        headers={
            "Content-Length": str(len(workbook_bytes)),
        },
    )


# ── Public API — compose and return FastAPI response ─────────────────────────

def serve_values_only_export(project_type: str, scenario: str, **kwargs) -> StreamingResponse | HTMLResponse:
    """Thin wrapper for route handlers — returns FastAPI response."""
    export = build_values_only_export_for_project(project_type, scenario, **kwargs)
    return _make_streaming_response(export)


def serve_runtime_summary_csv(runtime_project_code: str, safe_project: str | None = None, **kwargs) -> StreamingResponse | HTMLResponse:
    """Thin wrapper for route handlers — returns FastAPI response."""
    export = build_runtime_summary_csv_export(runtime_project_code, safe_project=safe_project, **kwargs)
    return _make_streaming_response(export)


def serve_institutional_workbook(runtime_project_code: str, safe_project: str | None = None, **kwargs) -> StreamingResponse | HTMLResponse:
    """Thin wrapper for route handlers — returns FastAPI response."""
    export = build_institutional_workbook_export(runtime_project_code, safe_project=safe_project, **kwargs)
    return _make_streaming_response(export)