"""
Workbook V2 — WorkbookService: pure domain service layer.

Architecture position:

  WorkspaceStateRecord  (persistence)
          │
          ▼
  WorkbookService                       ← this module
          │
          ├── build_input_set()  ──▶ ProjectInputSet  (PR 2)
          │       └── to_projectinputs()  ──▶ ProjectInputs (existing engine)
          │
          ├── get_runtime_result() ──▶ RuntimeResult  (PR 3)
          │       └── to_sessionstorage_script() ──▶ <script>…</script>
          │
          └── runtime_hydration_script()  (convenience wrapper)

Design invariants:
- All methods are pure functions (no DB calls, no HTTP, no I/O, no side effects).
- WorkbookService never imports from app.persistence directly.
- It delegates to ProjectInputSet and RuntimeResult; it does not duplicate logic.
- It is the single controlled entry point for converting persistence types
  into Workbook V2 domain types, so future callers (app/v2/ shell, PR 5;
  sheet migration, PR 6) import from here rather than from input_set.py or
  runtime_result.py directly.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from app.workbook.input_set import ProjectInputSet
from app.workbook.runtime_result import RuntimeResult

if TYPE_CHECKING:
    from app.persistence.records import WorkspaceStateRecord
    from app.domain.project_inputs import ProjectInputs  # engine domain object


class WorkbookService:
    """Pure domain service coordinating Workbook V2 types.

    All methods are static — there is no instance state.  Import and call
    directly::

        from app.workbook.service import WorkbookService

        pis = WorkbookService.build_input_set(snapshot)
        rr  = WorkbookService.get_runtime_result(ws)
    """

    # ------------------------------------------------------------------ #
    # Input set construction                                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def build_input_set(
        snapshot: dict[str, Any],
    ) -> ProjectInputSet:
        """Build a ProjectInputSet from a flat snapshot dict.

        Parameters
        ----------
        snapshot : dict
            Flat key→value snapshot (e.g. ``workspace_state.draft_snapshot``).
            May include ``template_source`` and ``project_origin`` keys, which
            ProjectInputSet.from_snapshot() extracts as provenance metadata.

        Returns
        -------
        ProjectInputSet
            Immutable, hash-stable input aggregate.
        """
        return ProjectInputSet.from_snapshot(snapshot=snapshot)

    @staticmethod
    def build_input_set_from_workspace(ws: "WorkspaceStateRecord") -> ProjectInputSet:
        """Build a ProjectInputSet from a WorkspaceStateRecord's draft snapshot.

        Uses the draft snapshot (the current editable state) rather than the
        saved_snapshot (the last immutable runtime boundary).

        Injects ``ws.project_code`` as ``template_source`` when the draft
        snapshot does not already carry one, so the engine's provenance
        routing is always set correctly.

        Parameters
        ----------
        ws : WorkspaceStateRecord
            Persisted workspace state record.

        Returns
        -------
        ProjectInputSet
        """
        snapshot = dict(ws.draft_snapshot)
        if ws.project_code and not snapshot.get("template_source"):
            snapshot["template_source"] = ws.project_code
        return ProjectInputSet.from_snapshot(snapshot=snapshot)

    # ------------------------------------------------------------------ #
    # Engine bridge                                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def to_projectinputs(pis: ProjectInputSet) -> "ProjectInputs":
        """Convert a ProjectInputSet to the engine's ProjectInputs domain object.

        This is the bridge between Workbook V2's canonical input model and the
        existing WaterfallRunner input type.  No formula or engine logic lives
        here — the conversion is fully delegated to ProjectInputSet.to_projectinputs().

        Parameters
        ----------
        pis : ProjectInputSet
            Validated, immutable input aggregate.

        Returns
        -------
        ProjectInputs
            The engine's frozen domain object.
        """
        return pis.to_projectinputs()

    # ------------------------------------------------------------------ #
    # RuntimeResult                                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_runtime_result(ws: "WorkspaceStateRecord") -> Optional[RuntimeResult]:
        """Reconstruct a RuntimeResult from a persisted WorkspaceStateRecord.

        Returns None when no run has been persisted yet (last_runtime_snapshot_id
        is absent or last_runtime_summary is empty).

        Parameters
        ----------
        ws : WorkspaceStateRecord

        Returns
        -------
        RuntimeResult | None
        """
        return RuntimeResult.from_workspace_state(ws)

    @staticmethod
    def runtime_hydration_script(ws: "WorkspaceStateRecord") -> str:
        """Return the sessionStorage hydration <script> block for this workspace.

        Convenience wrapper: reconstructs RuntimeResult and calls
        to_sessionstorage_script().  Returns an empty string when no
        RuntimeResult is persisted (so callers can safely concatenate without
        an extra None check).

        Parameters
        ----------
        ws : WorkspaceStateRecord

        Returns
        -------
        str
            A ``<script>…</script>`` block, or empty string if no runtime.
        """
        rr = RuntimeResult.from_workspace_state(ws)
        if rr is None:
            return ""
        return rr.to_sessionstorage_script()
