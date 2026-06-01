"""Export service — extracted from main_web.py for Phase 49B.

Behavior-preserving refactor — no financial formulas, runtime calculations,
or model output changes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi.responses import HTMLResponse, StreamingResponse


@dataclass(frozen=True)
class ExportResponse:
    """Result of an export service function.

    Attributes
    ----------
    bytes_data : bytes | None
        Raw export bytes, if generated successfully.
    filename : str | None
        Suggested filename for the Content-Disposition header.
    media_type : str | None
        MIME content type.
    status_code : int
        HTTP status code (200 = success, 400 = bad request).
    error_content : str | None
        HTML error page content, if status_code != 200.
    metadata : dict[str, Any]
        Provenance/runtime metadata extracted during export generation.
        Used by route handlers to populate record_export replay_metadata
        with the same timestamps/origin values the runtime generated.

        CSV / workbook exports populate these keys from runtime_rows[0]:
          - export_generated_at  : str  (ISO timestamp of export generation)
          - runtime_generated_at  : str  (ISO timestamp of the runtime run)
          - runtime_origin        : str  (e.g. "factory_base_runtime", "saved_state")
          - generated_at          : str  (alias for export_generated_at)
          - source_branch         : str  (git branch at runtime generation)

        Excel export (GET /download) accepts an optional replay_metadata
        dict that is passed through to build_excel_export unchanged.
    """
    bytes_data: bytes | None = None
    filename: str | None = None
    media_type: str | None = None
    status_code: int = 200
    error_content: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

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


# ── Values-only Excel export ──────────────────────────────────────────────────

def build_values_only_export_for_project(
    result,
    project_inputs,
    project_type: str,
    scenario: str,
    *,
    replay_metadata: dict | None = None,
) -> ExportResponse:
    """Build values-only Excel export bytes.

    ``result`` and ``project_inputs`` come from the completed model run
    (e.g. ``run_demo_project(...).result`` / ``run_demo_project(...).project_inputs``).
    ``replay_metadata`` is passed directly to ``build_excel_export`` unchanged,
    giving the Excel file the same provenance timestamps as the route's
    ``record_export`` call.

    Behavior matches the original download_get logic in main_web.py.
    """
    from app.excel_export import build_excel_export

    try:
        filename = f"fincogpt_{project_type.lower()}_{scenario.lower()}.xlsx"
        excel_bytes = build_excel_export(
            result=result,
            project_inputs=project_inputs,
            provenance_metadata=replay_metadata or {},
        )
        return ExportResponse(
            bytes_data=excel_bytes,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            status_code=200,
        )
    except (ValueError, Exception) as e:
        return ExportResponse(
            status_code=400,
            error_content=(
                f"<html><body><h2>Excel generation failed</h2>"
                f"<p>Invalid input: {str(e)}</p><a href='/'>Back</a></body></html>"
            ),
        )


# ── Runtime Summary CSV export ────────────────────────────────────────────────

def build_runtime_summary_csv_export(
    runtime_project_code: str,
    *,
    safe_project: str | None = None,
) -> ExportResponse:
    """Build runtime summary CSV bytes.

    Populates ExportResponse.metadata with fields extracted from
    runtime_rows[0] so that callers can use the same
    export_generated_at / runtime_generated_at / runtime_origin values
    in their record_export() calls that the runtime itself recorded.

    Behavior matches the original runtime_summary_export logic in main_web.py.
    """
    from app.export.runtime_summary import build_runtime_summary_csv, build_runtime_summary_rows

    try:
        runtime_rows = build_runtime_summary_rows(runtime_project_code)
        first_row = runtime_rows[0]
        csv_text = build_runtime_summary_csv(
            runtime_project_code,
            generated_at=first_row["generated_at"],
            source_branch=first_row["source_branch"],
        )
    except ValueError as exc:
        return ExportResponse(
            status_code=400,
            error_content=(
                f"<html><body><h2>Runtime summary export failed</h2>"
                f"<p>{str(exc)}</p><a href='/'>Back</a></body></html>"
            ),
        )

    # Preserve provenance timestamps for the caller's record_export.
    # These must match what the runtime itself recorded.
    metadata = {
        "export_generated_at": first_row["export_generated_at"],
        "runtime_generated_at": first_row["runtime_generated_at"],
        "runtime_origin": first_row["runtime_origin"],
        "generated_at": first_row["generated_at"],
        "source_branch": first_row["source_branch"],
    }

    filename = f"phase10_{safe_project or runtime_project_code}_runtime_summary.csv"
    data = csv_text.encode("utf-8")
    return ExportResponse(
        bytes_data=data,
        filename=filename,
        media_type="text/csv",
        status_code=200,
        metadata=metadata,
    )


# ── Institutional Workbook export ─────────────────────────────────────────────

def build_institutional_workbook_export(
    runtime_project_code: str,
    *,
    safe_project: str | None = None,
) -> ExportResponse:
    """Build institutional workbook bytes.

    Populates ExportResponse.metadata with fields extracted from
    runtime_rows[0] so that callers can use the same
    export_generated_at / runtime_generated_at / runtime_origin values
    in their record_export() calls that the runtime itself recorded.

    Behavior matches the original institutional_workbook_export logic in main_web.py.
    """
    from app.export.institutional_workbook import export_institutional_workbook_skeleton
    from app.export.runtime_summary import build_runtime_summary_rows

    try:
        runtime_rows = build_runtime_summary_rows(runtime_project_code)
        first_row = runtime_rows[0]
        workbook_bytes = export_institutional_workbook_skeleton(runtime_project_code)
    except ValueError as exc:
        return ExportResponse(
            status_code=400,
            error_content=(
                f"<html><body><h2>Institutional workbook export failed</h2>"
                f"<p>{str(exc)}</p><a href='/'>Back</a></body></html>"
            ),
        )

    # Preserve provenance timestamps for the caller's record_export.
    metadata = {
        "export_generated_at": first_row["export_generated_at"],
        "runtime_generated_at": first_row["runtime_generated_at"],
        "runtime_origin": first_row["runtime_origin"],
        "generated_at": first_row["generated_at"],
        "source_branch": first_row["source_branch"],
    }

    filename = f"phase10_{safe_project or runtime_project_code}_institutional_workbook_skeleton.xlsx"
    return ExportResponse(
        bytes_data=workbook_bytes,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        status_code=200,
        metadata=metadata,
    )


# ── Public API — compose and return FastAPI response ─────────────────────────

def serve_values_only_export(
    project_type: str,
    scenario: str,
    *,
    replay_metadata: dict | None = None,
) -> StreamingResponse | HTMLResponse:
    """Thin wrapper for route handlers — returns FastAPI response."""
    export = build_values_only_export_for_project(
        project_type,
        scenario,
        replay_metadata=replay_metadata,
    )
    return _make_streaming_response(export)


def serve_runtime_summary_csv(
    runtime_project_code: str,
    safe_project: str | None = None,
) -> StreamingResponse | HTMLResponse:
    """Thin wrapper for route handlers — returns FastAPI response."""
    export = build_runtime_summary_csv_export(
        runtime_project_code,
        safe_project=safe_project,
    )
    return _make_streaming_response(export)


def serve_institutional_workbook(
    runtime_project_code: str,
    safe_project: str | None = None,
) -> StreamingResponse | HTMLResponse:
    """Thin wrapper for route handlers — returns FastAPI response."""
    export = build_institutional_workbook_export(
        runtime_project_code,
        safe_project=safe_project,
    )
    return _make_streaming_response(export)