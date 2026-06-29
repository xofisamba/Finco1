"""Preview service — extracted from main_web.py for C2-PR23.

Holds the `/model/preview` route's validation/computation/echo logic,
moved out of `main_web.py` verbatim (no behaviour change — see
docs/C2_PR23_PREVIEW_SERVICE_BOUNDARY.md for the characterization-
test-then-refactor methodology used to prove this).

The route in `main_web.py` remains a thin adapter:
  (a) auth check
  (b) project authorization check (via `get_project_by_code`)
  (c) call into `validate_preview_payload()` / `build_preview_response()`
      below
  (d) return the JSON response

This module NEVER calls the real financial engine (`domain/*`,
`app/waterfall_core.py`, `app/input_adapter.py`,
`app/project_factories.py`) and NEVER mutates persistence. Every
operating-preview field (capex/revenue/opex/ebitda/operating_cash_flow)
is computed CLIENT-SIDE and merely validated/echoed here — see
docs/C2_PR10_CAPEX_TOTAL_PREVIEW.md through
docs/C2_PR16_OPERATING_CF_PREVIEW.md for each field's own history.

C2-PR24 adds the first BACKEND-COMPUTED preview field here: a small
debt preview stub (`compute_debt_preview`), which is the deliberate
exception to "client computes, server only echoes" — it is computed
entirely from SAVED project inputs already available server-side
(never from the incoming preview payload). See
docs/C2_PR24_BACKEND_DEBT_PREVIEW_STUB.md.
"""
from __future__ import annotations

from typing import Any, Optional


def sorted_unique_strings(value: Any) -> list[str]:
    """Defensive normalizer mirroring the original
    `_c2_pr7_sorted_unique_strings` helper: returns a sorted list of
    unique strings from `value` (tolerating non-list/non-string input
    by treating any non-conforming item as simply absent, never
    raising)."""
    if not isinstance(value, list):
        return []
    seen: set[str] = set()
    out: list[str] = []
    for item in value:
        if isinstance(item, str) and item not in seen:
            seen.add(item)
            out.append(item)
    out.sort()
    return out


def validate_preview_payload(body: Any) -> tuple[bool, list[str]]:
    """Defensive, non-throwing shape-check mirroring
    ``FcRecalcPreview.validatePreviewPayload`` in
    ``static/modelling/recalc-preview.js``. Returns ``(ok, errors)``
    where ``errors`` is a list of human-readable validation problems
    (empty when ``ok`` is True). Tolerates missing/extra fields by
    treating any deviation from the expected shape as invalid rather
    than raising.
    """
    errors = []
    if not isinstance(body, dict):
        return False, ["request body must be a JSON object"]

    if not isinstance(body.get("valid"), bool):
        errors.append("'valid' must be a boolean")

    dirty_cells = body.get("dirtyCells")
    if not isinstance(dirty_cells, list) or not all(isinstance(v, str) for v in dirty_cells):
        errors.append("'dirtyCells' must be an array of strings")

    affected_groups = body.get("affectedGroups")
    if not isinstance(affected_groups, list) or not all(isinstance(v, str) for v in affected_groups):
        errors.append("'affectedGroups' must be an array of strings")

    if not isinstance(body.get("projectDirty"), bool):
        errors.append("'projectDirty' must be a boolean")

    if not isinstance(body.get("reason"), str):
        errors.append("'reason' must be a string")

    execution_status = body.get("executionStatus")
    if execution_status is not None and not isinstance(execution_status, str):
        errors.append("'executionStatus' must be a string or null")

    project = body.get("project")
    if project is not None and not isinstance(project, str):
        errors.append("'project' must be a string or null")

    # C2-PR10: capexTotalPreview is additive/optional. If present, it
    # must be null or a finite real number — never a string, never
    # NaN/Infinity. This field carries the CLIENT-computed sum of the
    # live (possibly-unsaved) CAPEX grid cell values; the server only
    # echoes it back (rounded) under the new "capex" response field,
    # it never recomputes or second-guesses it against persistence.
    if "capexTotalPreview" in body:
        capex_total_preview = body.get("capexTotalPreview")
        if capex_total_preview is not None and (
            isinstance(capex_total_preview, bool)
            or not isinstance(capex_total_preview, (int, float))
            or capex_total_preview != capex_total_preview  # NaN check
            or capex_total_preview in (float("inf"), float("-inf"))
        ):
            errors.append("'capexTotalPreview' must be a finite number or null")

    # C2-PR13: revenueTotalPreview is additive/optional, mirroring
    # capexTotalPreview's validation exactly.
    if "revenueTotalPreview" in body:
        revenue_total_preview = body.get("revenueTotalPreview")
        if revenue_total_preview is not None and (
            isinstance(revenue_total_preview, bool)
            or not isinstance(revenue_total_preview, (int, float))
            or revenue_total_preview != revenue_total_preview  # NaN check
            or revenue_total_preview in (float("inf"), float("-inf"))
        ):
            errors.append("'revenueTotalPreview' must be a finite number or null")

    # C2-PR14: opexTotalPreview is additive/optional, mirroring
    # capexTotalPreview/revenueTotalPreview's validation exactly.
    if "opexTotalPreview" in body:
        opex_total_preview = body.get("opexTotalPreview")
        if opex_total_preview is not None and (
            isinstance(opex_total_preview, bool)
            or not isinstance(opex_total_preview, (int, float))
            or opex_total_preview != opex_total_preview  # NaN check
            or opex_total_preview in (float("inf"), float("-inf"))
        ):
            errors.append("'opexTotalPreview' must be a finite number or null")

    # C2-PR15: ebitdaPreview is additive/optional.
    if "ebitdaPreview" in body:
        ebitda_preview = body.get("ebitdaPreview")
        if ebitda_preview is not None and (
            isinstance(ebitda_preview, bool)
            or not isinstance(ebitda_preview, (int, float))
            or ebitda_preview != ebitda_preview  # NaN check
            or ebitda_preview in (float("inf"), float("-inf"))
        ):
            errors.append("'ebitdaPreview' must be a finite number or null")

    # C2-PR16: operatingCashFlowPreview is additive/optional.
    if "operatingCashFlowPreview" in body:
        ocf_preview = body.get("operatingCashFlowPreview")
        if ocf_preview is not None and (
            isinstance(ocf_preview, bool)
            or not isinstance(ocf_preview, (int, float))
            or ocf_preview != ocf_preview  # NaN check
            or ocf_preview in (float("inf"), float("-inf"))
        ):
            errors.append("'operatingCashFlowPreview' must be a finite number or null")

    return (len(errors) == 0), errors


def _is_finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value == value  # not NaN
        and value not in (float("inf"), float("-inf"))
    )


def compute_debt_preview(body: Any, project_record: Optional[Any]) -> dict[str, Any]:
    """C2-PR25: backend-computed Debt Preview v2 — saved-inputs
    breakdown.

    Extends the C2-PR24 single-number placeholder into a small
    breakdown so the user can see exactly which SAVED inputs the
    preview is anchored to (without ever reading any unsaved
    frontend payload field).

    Deliberately NOT real debt sculpting/amortization/DSCR/interest
    schedule/debt service — see docs/C2_PR24_BACKEND_DEBT_PREVIEW_STUB.md
    and docs/C2_DEBT_PREVIEW_CHECKPOINT.md for the full rationale and
    explicit out-of-scope list.

    This function may ONLY use SAVED project inputs already available
    server-side via `project_record.baseline_snapshot` (the same
    project-loading mechanism the route already uses for
    authorization, via `get_project_by_code`). It NEVER reads any
    preview field from `body` (the incoming, possibly-unsaved frontend
    payload) as a debt-calculation input — `body` is accepted purely
    for signature symmetry with the other preview functions and is not
    read here at all.

    Calculation (when both saved inputs are present/valid finite
    numbers): ``senior_debt_preview = saved_capex_total *
    (saved_gearing_pct / 100.0)``, rounded to 2dp. `gearing_pct` is
    stored as a 0-100 percentage (see
    app/persistence/projects_repository.py's `"gearing_pct": str(...
    gearing_ratio * 100)` and app/input_adapter.py's
    `gearing_ratio=value / 100.0`), so dividing by 100.0 here matches
    that exact convention.

    Response shape (added vs. C2-PR24):
      - `senior_debt_preview`: the placeholder number (unchanged)
      - `saved_total_capex`:    the saved CAPEX the preview is anchored
                                 to (new, C2-PR25; same value the formula
                                 reads; None when unavailable)
      - `saved_gearing_pct`:   the saved gearing percent the preview is
                                 anchored to (new, C2-PR25; same value
                                 the formula reads; None when unavailable)

    Unavailable response uses the same `status`/`currency`/`basis`
    trio (all three are ALWAYS present so the frontend can render a
    consistent 3-field panel and the renderer can gate on `status`
    exactly as it does today).
    """
    unavailable = {
        "status": "preview-unavailable",
        "senior_debt_preview": None,
        "saved_total_capex": None,
        "saved_gearing_pct": None,
        "currency": "EUR",
        "basis": "saved-inputs-only",
    }

    if project_record is None:
        return unavailable

    snapshot = getattr(project_record, "baseline_snapshot", None)
    if not isinstance(snapshot, dict):
        return unavailable

    saved_capex_total = _safe_float(snapshot.get("total_capex_keur"))
    saved_gearing_pct = _safe_float(snapshot.get("gearing_pct"))

    if saved_capex_total is None or saved_gearing_pct is None:
        return unavailable
    if not _is_finite_number(saved_capex_total) or not _is_finite_number(saved_gearing_pct):
        return unavailable

    senior_debt_preview = round(saved_capex_total * (saved_gearing_pct / 100.0), 2)

    return {
        "status": "preview-ready",
        "senior_debt_preview": senior_debt_preview,
        "saved_total_capex": round(saved_capex_total, 2),
        "saved_gearing_pct": round(saved_gearing_pct, 2),
        "currency": "EUR",
        "basis": "saved-inputs-only",
    }


def _safe_float(value: Any) -> Optional[float]:
    """Parses `value` as a finite float, tolerating the string-typed
    form-field convention used throughout `baseline_snapshot` (e.g.
    `"50000"`, `"50000.0"`). Returns None on anything unparseable,
    never raises."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            parsed = float(stripped)
        except ValueError:
            return None
        if parsed != parsed or parsed in (float("inf"), float("-inf")):
            return None
        return parsed
    return None


def build_preview_response(body: dict[str, Any], project_record: Optional[Any]) -> dict[str, Any]:
    """Builds the full, valid-payload `/model/preview` JSON response
    body, exactly mirroring the original inline `model_preview()`
    route logic field-for-field (no behaviour change — see
    docs/C2_PR23_PREVIEW_SERVICE_BOUNDARY.md).

    `project_record` is the already-resolved `ProjectRecord` (or
    `None` when the payload's `project` field was null/absent) from
    the route's own `get_project_by_code()` authorization call — this
    function does not perform its own project lookup.
    """
    dirty_cells = sorted_unique_strings(body.get("dirtyCells"))
    affected_groups = sorted_unique_strings(body.get("affectedGroups"))

    response_body: dict[str, Any] = {
        "ok": True,
        "status": "stubbed",
        "executed": False,
        "accepted": True,
        "affectedGroups": affected_groups,
        "dirtyCells": dirty_cells,
        "warnings": [],
        "message": "Preview endpoint contract accepted payload; recalculation is not implemented yet.",
        "overview": {
            "runtime_status": "Preview executed",
            "updated": True,
        },
    }

    if "capexTotalPreview" in body and body.get("capexTotalPreview") is not None:
        response_body["capex"] = {
            "capex_total_preview": round(float(body["capexTotalPreview"]), 2),
            "currency": "EUR",
        }

    if "revenueTotalPreview" in body and body.get("revenueTotalPreview") is not None:
        response_body["revenue"] = {
            "preview": round(float(body["revenueTotalPreview"]), 2),
            "currency": "EUR",
        }

    if "opexTotalPreview" in body and body.get("opexTotalPreview") is not None:
        response_body["opex"] = {
            "preview": round(float(body["opexTotalPreview"]), 2),
            "currency": "EUR",
        }

    if "ebitdaPreview" in body and body.get("ebitdaPreview") is not None:
        response_body["ebitda"] = {
            "preview": round(float(body["ebitdaPreview"]), 2),
            "currency": "EUR",
        }

    if "operatingCashFlowPreview" in body and body.get("operatingCashFlowPreview") is not None:
        response_body["operating_cash_flow"] = {
            "preview": round(float(body["operatingCashFlowPreview"]), 2),
            "currency": "EUR",
        }

    # C2-PR24: additive "debt" field. The FIRST backend-computed
    # preview field in this response — see compute_debt_preview()'s
    # own docstring and docs/C2_PR24_BACKEND_DEBT_PREVIEW_STUB.md.
    # Unlike every field above, this is unconditionally present (never
    # omitted), since "unavailable" is itself a meaningful, always-
    # renderable status for this slice.
    response_body["debt"] = compute_debt_preview(body, project_record)

    return response_body
