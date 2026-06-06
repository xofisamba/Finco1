"""Phase 57A-9D — Run / materialization integration for
persisted CAPEX user-added sub-lines.

This module sits between the persistence layer
(``app.persistence.capex_sub_lines``) and the model layer
(``domain.inputs.CapexStructure``). Its single public
function, ``_apply_user_sub_lines_to_capex``, is the
canonical wire-up that the /run route calls in the
user-created path.

The 57A-9A design gate (PR #505) prescribes that user
sub-lines fold into the existing 15 named
``CapexItem.amount_keur`` fields via the locked
``CAPEX_CATEGORY_TO_FIELD`` mapping, with the scenario's
reserved-key overrides (``_capex_sub_line_overrides``)
applying on top. This module implements that wire-up
**without** touching the model formula path, the Excel
export, the UI, or the financial engine internals. It is
a pure materialization step on the model INPUT side: the
``CapexStructure`` is the input to the model, not the
output.

Hard rules (Phase 57A-9A design + 57A-9B Claude delta
review fix):

  - Factory projects (TUHO/Oborovo/Generic Solar/Generic
    Wind) have no user sub-lines. The helper returns the
    input ``capex`` unchanged. This is the TUHO/Oborovo
    parity guarantee.
  - User projects load active sub-lines from the
    ``capex_sub_lines`` table, keyed by ``project_id``.
    Soft-deleted rows are excluded.
  - Scenario override amount REPLACES project default
    amount (NOT a delta adjustment). This is the
    57A-9B Claude delta review fix, pinned by
    ``resolve_effective_sub_line_amount``.
  - Unknown ``sub_line_id`` overrides are ignored — the
    helper does not raise on stale override UUIDs. (A
    warning is logged so reviewers can see it, but the
    Run does not crash.)
  - Unknown parent categories raise ``ValueError``
    loudly. This is fail-fast: an unknown category
    would silently drop data, which the design gate
    explicitly forbids.
  - C.17 / C.18 are rejected at validation time (the
    57A-9B ``validate_parent_category`` helper). This
    module never receives them.
  - The 57A-8 in-memory preview rows (TMP markers) are
    NEVER loaded from the table — they are not persisted.
    This module only reads rows from
    ``capex_sub_lines``, which is the persisted table.

Type: runtime model-input integration, DRAFT PR (57A-9D).
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Optional

from app.persistence.capex_sub_lines import (
    CapexSubLine,
    fold_sub_lines_into_capex,
    list_sub_lines_for_project,
)


logger = logging.getLogger(__name__)


# Reserved scenario-override keys (57A-9A design, 57A-9C
# wire-up). When a scenario carries a sub-line override
# map under these keys, the helper applies it on top of
# the persisted default.
_RESERVED_SUB_LINE_OVERRIDES_KEY = "_capex_sub_line_overrides"


def _extract_sub_line_overrides(
    scenario_overrides: Optional[Mapping[str, Any]],
) -> dict:
    """Extract the per-scenario sub-line override map.

    The reserved key is consulted first. If the scenario
    carries a non-dict value at the reserved key (a
    malformed / hand-edited record), the helper falls
    back to an empty map — this is the same fail-soft
    behavior the 57A-9C silent-drop rule gives to
    unknown keys, applied to the reserved surface.

    Returns:
        A ``{sub_line_id: amount_keur}`` dict. Empty if
        the scenario is the Base case (no overrides), or
        if the reserved key is missing / malformed.
    """
    if not scenario_overrides:
        return {}
    raw = scenario_overrides.get(_RESERVED_SUB_LINE_OVERRIDES_KEY)
    if isinstance(raw, dict):
        return dict(raw)
    if raw is not None:
        logger.warning(
            "scenario_overrides[%r] is not a dict (%s); "
            "ignoring sub-line override map",
            _RESERVED_SUB_LINE_OVERRIDES_KEY,
            type(raw).__name__,
        )
    return {}


def _load_active_sub_lines(project_id: str) -> tuple[CapexSubLine, ...]:
    """Load active (is_active=1) sub-lines for a project.

    Uses a fresh SQLite connection (not a shared cursor)
    so this helper can be called from any context without
    forcing the caller to manage a cursor lifecycle. The
    DB path is read from the environment (the same path
    the persistence layer uses).

    Returns:
        A tuple of ``CapexSubLine`` records ordered by
        ``(parent_category_code ASC, display_order ASC)``
        — the canonical render order. Empty if the
        project has no persisted sub-lines, or if the
        project does not exist in the DB.

    Notes:
        Soft-deleted rows (is_active=0) are excluded. The
        audit / replay trail remains in the table; this
        helper just does not surface them.
    """
    db_path = Path(
        __import__("os").environ.get(
            "FINCO_DB_PATH",
            str(Path(__file__).resolve().parents[1] / "data" / "finco_runs.db"),
        )
    )
    if not db_path.exists():
        # The DB does not exist (test environment or
        # pre-init state). Return empty — this is the
        # factory no-op case.
        return ()
    with sqlite3.connect(str(db_path)) as conn:
        # list_sub_lines_for_project uses CapexSubLine.from_row
        # which expects row[...] dict-style access. We must
        # set row_factory=Row on the connection.
        conn.row_factory = sqlite3.Row
        rows = list_sub_lines_for_project(
            conn.cursor(), project_id, include_inactive=False,
        )
    return rows


def _apply_user_sub_lines_to_capex(
    capex: Any,
    *,
    project_id: str,
    scenario_overrides: Optional[Mapping[str, Any]] = None,
) -> Any:
    """Fold persisted user sub-lines into a CapexStructure.

    This is the **explicit Run/materialization boundary**
    for Phase 57A-9D. The /run route in the user-created
    path calls this helper AFTER the project's
    ``ProjectInputs`` is built from the snapshot, and
    BEFORE the model is run.

    Args:
        capex: a ``CapexStructure`` (from
            ``domain.inputs``) for the project. This is
            the input to the model; the helper MAY
            return a new ``CapexStructure`` with selected
            field amounts updated.
        project_id: the ``projects.project_id`` (UUID) of
            the user project. Used to look up persisted
            sub-lines in the ``capex_sub_lines`` table.
            For factory / template-seeded projects (TUHO,
            Oborovo, Generic Solar, Generic Wind), this
            helper is NOT called — the factory no-op case
            is handled by the empty ``user_sub_lines``
            short-circuit in ``fold_sub_lines_into_capex``.
        scenario_overrides: the active scenario's
            ``overrides_json`` dict (or None for Base
            case). The reserved key
            ``_capex_sub_line_overrides`` carries the
            ``{sub_line_id: amount_keur}`` map.

    Returns:
        A ``CapexStructure``. For factory projects and
        projects with no sub-lines, the input is returned
        unchanged. For user projects with sub-lines, a
        new ``CapexStructure`` is returned with the
        field amounts updated.

    Raises:
        ValueError: if a persisted sub-line carries an
            unknown parent category (e.g. C.99). This is
            fail-fast: silent drop would corrupt the
            parity guarantee. The 57A-9B
            ``validate_parent_category`` rejects C.17 and
            C.18 at persistence time, so they never reach
            this helper.

    Notes:
        - The helper does NOT mutate the input
          ``CapexStructure`` (``CapexStructure`` is a
          frozen dataclass, so mutation is impossible).
        - The helper does NOT generate fake runtime IDs.
          Sub-lines carry the persisted ``sub_line_id``
          (UUID) which is the scenario-override key.
        - The helper does NOT include 57A-8 in-memory
          preview rows. Those are not persisted.
        - The helper does NOT touch the model formula
          path, the Excel export, the UI, or the
          waterfall engine. It is purely an input-
          materialization step.
    """
    # Factory / template-seeded projects: the helper
    # returns capex unchanged via the empty-input
    # short-circuit in fold_sub_lines_into_capex. We
    # also short-circuit explicitly when project_id is
    # empty (defensive: callers from generic / template
    # paths MUST NOT pass an empty project_id).
    if not project_id:
        return capex

    user_sub_lines = _load_active_sub_lines(project_id)
    if not user_sub_lines:
        # Factory no-op path. No sub-lines persisted, so
        # the fold returns capex unchanged. TUHO/Oborovo
        # parity preserved by construction.
        return capex

    sub_line_overrides = _extract_sub_line_overrides(
        scenario_overrides,
    )

    # The fold helper:
    #   - excludes soft-deleted rows (it filters on
    #     is_active)
    #   - uses the locked CAPEX_CATEGORY_TO_FIELD mapping
    #   - calls resolve_effective_sub_line_amount (override
    #     REPLACES default, not a delta)
    #   - returns a NEW CapexStructure (no mutation)
    #   - raises ValueError on unknown parent category
    #     (fail-fast, not silent drop)
    folded = fold_sub_lines_into_capex(
        capex,
        user_sub_lines,
        scenario_overrides=sub_line_overrides,
    )

    # Log a warning for any override UUID that does not
    # match an active sub-line. This is a stale-override
    # case (the scenario was created when the line
    # existed, but the line was later removed or its
    # UUID changed). The Run does NOT crash; the warning
    # surfaces the inconsistency to the reviewer.
    if sub_line_overrides:
        active_uuids = {
            sub.sub_line_id for sub in user_sub_lines
        }
        stale = set(sub_line_overrides) - active_uuids
        for stale_uuid in stale:
            logger.warning(
                "Scenario override for sub_line_id %s "
                "does not match any active sub-line; "
                "ignoring (sub-line may have been "
                "soft-deleted or its UUID may have "
                "changed).",
                stale_uuid,
            )

    return folded
