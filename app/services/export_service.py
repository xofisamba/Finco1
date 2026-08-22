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
        # PR-8 single-calculation contract: ONE production execution → rows
        # once → the SAME rows are serialized to CSV. The serialization layer
        # is financial-calculation-free.
        runtime_rows = build_runtime_summary_rows(runtime_project_code)
        first_row = runtime_rows[0]
        csv_text = build_runtime_summary_csv(
            runtime_project_code,
            generated_at=first_row["generated_at"],
            source_branch=first_row["source_branch"],
            rows=runtime_rows,
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
    from app.export.institutional_workbook import (
        _build_export_bundle,
        export_institutional_workbook_from_bundle,
    )

    try:
        # PR-8 single-calculation contract: ONE authority execution → ONE
        # bundle (which already contains runtime_rows, runtime_result and
        # authority metadata) → pure serialization to workbook bytes. No
        # second model run, no separately rebuilt runtime rows.
        bundle = _build_export_bundle(runtime_project_code)
        first_row = bundle.runtime_rows[0]
        workbook_bytes = export_institutional_workbook_from_bundle(bundle)
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


def build_excel_export_for_post_request(
    result,
    project_inputs,
    project_type: str,
    scenario: str,
    runtime_origin: str,
    replay_metadata: dict,
) -> ExportResponse:
    """Build Excel export for POST /download request.

    This function encapsulates the Excel generation portion of the POST /download
    route. It receives a fully-constructed ``replay_metadata`` dict (already mutated
    by the route for ``baseline_source`` when applicable) and produces an
    ExportResponse with bytes, filename, and media type.

    The route retains all orchestration responsibility:
      - authentication / session
      - form parsing
      - project record lookup
      - runtime guard
      - runtime origin resolution
      - build_projectinputs vs build_projectinputs_from_snapshot selection
      - record_export
      - StreamingResponse / HTMLResponse return

    Parameters
    ----------
    result : ModelResult
        Completed model run result (e.g. demo.result).
    project_inputs : ProjectInputs
        Project inputs from the model run (e.g. demo.project_inputs).
    project_type : str
        Project type string from the form (e.g. "Solar", "Wind").
    scenario : str
        Scenario string from the form (e.g. "Base", "Downside").
    runtime_origin : str
        Runtime origin string (e.g. "factory_base_runtime", "saved_state").
        Passed to build_excel_export as provenance_metadata["runtime_origin"].
    replay_metadata : dict
        Provenance metadata already built by the route. Must include all fields
        required for record_export including scenario_id, active_scenario_id,
        template_origin_override, scenario_provenance, warning_note, and
        baseline_source (already set by route before calling this function
        when project_origin == "saved_baseline").

    Returns
    -------
    ExportResponse
        With bytes_data, filename, media_type, and status_code on success;
        or error_content and status_code on failure.

    Behavior matches the original Excel generation portion of download_post
    in main_web.py. No financial formulas, runtime calculations, or model outputs
    are changed.
    """
    from app.excel_export import build_excel_export

    # Ensure runtime_origin is in metadata (build_excel_export expects it)
    metadata = dict(replay_metadata)
    metadata["runtime_origin"] = runtime_origin
    metadata.setdefault("capex_sub_lines_audit_mode", "active_only")

    filename = f"fincogpt_{project_type.lower()}_{scenario.lower()}.xlsx"

    try:
        excel_bytes = build_excel_export(
            result=result,
            project_inputs=project_inputs,
            provenance_metadata=metadata,
        )
        return ExportResponse(
            bytes_data=excel_bytes,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            status_code=200,
        )
    except (ValueError, Exception) as e:
        return ExportResponse(
            status_code=500,
            error_content=(
                f"<html><body><h2>Excel generation failed</h2>"
                f"<p>{str(e)}</p><a href='/'>Back</a></body></html>"
            ),
        )


# ── Public API — compose and return FastAPI response ─────────────────────────

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
