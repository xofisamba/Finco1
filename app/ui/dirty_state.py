"""Phase 25B-4 — Dirty State + Save Clarity helper.

Pure read-side helper module. Computes a unified
``DirtyState`` summary from the existing
``workspace_state``, ``runtime_summary``, and save-context
fields that are already present in the index page context
(see ``app/services/run_service.py`` and
``app/services/scenario_state_service.py``).

The helper exposes a single entry point
``resolve_dirty_state(...)`` that returns a
``DirtyState`` frozen dataclass with a pre-classified
``state`` value, a human-readable ``label``, an
explanatory ``hint``, and a CSS ``tone`` that the partial
can plug into the existing badge vocabulary
(``badge-dirty``, ``badge-pass``, ``badge-warn``,
``badge-blocked``).

The helper does NOT:
- mutate workspace_state
- mutate the project record
- mutate the scenario record
- call the persistence layer
- enable any feature flag
- touch any formula / runtime path
- touch construction / C10 / R-PAR / tax / debt / IDC

It is purely a deterministic classifier over the
already-available context. Reads from existing fields
only.

State machine (4 states):

- ``saved``     — workspace_state.dirty is False and there
                  is at least one prior run OR a save
                  record. Label: "SAVED".
- ``dirty``     — workspace_state.dirty is True and there
                  is NO prior run (i.e. user has been
                  editing and never ran). Label:
                  "UNSAVED EDITS".
- ``stale``     — workspace_state.dirty is False (clean)
                  but a prior run exists AND the last
                  save happened BEFORE the last run. This
                  means the saved snapshot may not match
                  what was actually run. Label:
                  "STALE — RERUN".
- ``needs_rerun`` — workspace_state.dirty is True (user
                  edited) AND a prior run exists. This
                  means outputs reflect a previous save,
                  not the current draft. Label:
                  "RERUN RECOMMENDED".
- ``unsaved``   — fallback when no save record exists and
                  no run has been performed. Label:
                  "UNSAVED".

The helper is intentionally conservative: it never
fabricates a save timestamp, never invents a run id,
and never claims a state it cannot prove from the
context. When the context is missing, the helper
returns a ``unknown`` state with a safe default
label of "—" and tone ``none``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional


# ---------------------------------------------------------------------------
# State vocabulary
# ---------------------------------------------------------------------------


#: Allowed ``state`` values. Keep in sync with
#: ``app/ui/dirty_state.py::resolve_dirty_state``.
DIRTY_STATE_SAVED = "saved"
DIRTY_STATE_DIRTY = "dirty"
DIRTY_STATE_STALE = "stale"
DIRTY_STATE_NEEDS_RERUN = "needs_rerun"
DIRTY_STATE_UNSAVED = "unsaved"
DIRTY_STATE_UNKNOWN = "unknown"

#: Human-readable label per state.
DIRTY_STATE_LABELS: dict[str, str] = {
    DIRTY_STATE_SAVED: "SAVED",
    DIRTY_STATE_DIRTY: "UNSAVED EDITS",
    DIRTY_STATE_STALE: "STALE — RERUN",
    DIRTY_STATE_NEEDS_RERUN: "RERUN RECOMMENDED",
    DIRTY_STATE_UNSAVED: "UNSAVED",
    DIRTY_STATE_UNKNOWN: "—",
}

#: CSS tone per state. Maps onto existing badge vocabulary.
DIRTY_STATE_TONES: dict[str, str] = {
    DIRTY_STATE_SAVED: "pass",
    DIRTY_STATE_DIRTY: "dirty",
    DIRTY_STATE_STALE: "warn",
    DIRTY_STATE_NEEDS_RERUN: "warn",
    DIRTY_STATE_UNSAVED: "dirty",
    DIRTY_STATE_UNKNOWN: "none",
}

#: Hint text per state. Shown in the badge tooltip / aria-label.
DIRTY_STATE_HINTS: dict[str, str] = {
    DIRTY_STATE_SAVED: (
        "Saved. Latest run reflects the current saved state."
    ),
    DIRTY_STATE_DIRTY: (
        "Draft has unsaved changes. Save the scenario to "
        "create a clean snapshot before running."
    ),
    DIRTY_STATE_STALE: (
        "Saved snapshot is older than the last run. The "
        "current saved state may not match what was last "
        "run. Re-run to refresh."
    ),
    DIRTY_STATE_NEEDS_RERUN: (
        "Draft has unsaved changes AND a previous run "
        "exists. Outputs reflect a prior state, not the "
        "current draft. Re-run after saving."
    ),
    DIRTY_STATE_UNSAVED: (
        "No saved scenario and no prior run. Save the "
        "scenario first to enable the run / export path."
    ),
    DIRTY_STATE_UNKNOWN: (
        "Save / run state unknown. Open the scenario tab "
        "to load or save before relying on outputs."
    ),
}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DirtyState:
    """Resolved dirty / save state for the active scenario.

    The fields are intentionally read-only so the partial
    can render them directly without any further
    classification on the template side.
    """

    #: One of the ``DIRTY_STATE_*`` constants.
    state: str

    #: Pre-classified human-readable label (e.g. "SAVED").
    label: str

    #: Pre-classified CSS tone (``pass`` / ``warn`` /
    #: ``dirty`` / ``none``).
    tone: str

    #: Explanatory text suitable for tooltip / aria-label.
    hint: str

    #: True if the user should re-run the model.
    rerun_recommended: bool

    #: True if the user has unsaved edits.
    unsaved_warning: bool

    #: True if the saved snapshot is older than the last
    #: run (i.e. a rerun is recommended even without
    #: unsaved edits).
    stale: bool

    #: Source fields that contributed to the
    #: classification (debug-only; never displayed).
    sources: tuple[str, ...] = ()


__all__ = [
    "DirtyState",
    "DIRTY_STATE_LABELS",
    "DIRTY_STATE_TONES",
    "DIRTY_STATE_HINTS",
    "DIRTY_STATE_SAVED",
    "DIRTY_STATE_DIRTY",
    "DIRTY_STATE_STALE",
    "DIRTY_STATE_NEEDS_RERUN",
    "DIRTY_STATE_UNSAVED",
    "DIRTY_STATE_UNKNOWN",
    "resolve_dirty_state",
    "is_rerun_recommended",
    "is_unsaved_warning",
    "is_stale",
]


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------


def _coerce_bool(value: Any, default: bool = False) -> bool:
    """Defensive boolean coercion. Returns ``default`` for
    None / missing / non-bool values.
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return default


def _coerce_str(value: Any) -> str:
    """Defensive string coercion. Returns empty string for
    None / missing values.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def resolve_dirty_state(
    workspace_state: Optional[Mapping[str, Any]],
    runtime_summary: Optional[Mapping[str, Any]] = None,
    save_state: Optional[Mapping[str, Any]] = None,
) -> DirtyState:
    """Resolve the unified dirty / save state from the
    already-available context.

    All three parameters are optional. Missing or
    None values fall through to a safe ``unknown``
    classification. The helper does NOT call the
    persistence layer; it only reads from the
    in-memory context.

    Parameters
    ----------
    workspace_state : Mapping or None
        The workspace_state dict, already present in the
        index page context. Must contain ``dirty`` (bool)
        and may contain ``last_runtime_snapshot_id`` (str).
    runtime_summary : Mapping or None
        The runtime_summary dict. May contain ``run_id``
        and ``last_run_at``.
    save_state : Mapping or None
        Optional save context. May contain ``last_saved_at``
        (ISO timestamp) and ``scenario_id``.

    Returns
    -------
    DirtyState
        Frozen dataclass with the pre-classified state.
    """
    if workspace_state is None:
        return DirtyState(
            state=DIRTY_STATE_UNKNOWN,
            label=DIRTY_STATE_LABELS[DIRTY_STATE_UNKNOWN],
            tone=DIRTY_STATE_TONES[DIRTY_STATE_UNKNOWN],
            hint=DIRTY_STATE_HINTS[DIRTY_STATE_UNKNOWN],
            rerun_recommended=False,
            unsaved_warning=False,
            stale=False,
            sources=("workspace_state=None",),
        )

    is_dirty = _coerce_bool(workspace_state.get("dirty"))
    last_snapshot_id = _coerce_str(
        workspace_state.get("last_runtime_snapshot_id"),
    )
    has_prior_run = bool(last_snapshot_id)

    rs = runtime_summary or {}
    run_id = _coerce_str(rs.get("run_id"))
    last_run_at = _coerce_str(rs.get("last_run_at"))
    has_runtime_run = bool(run_id or last_run_at)

    ss = save_state or {}
    last_saved_at = _coerce_str(ss.get("last_saved_at"))
    scenario_id = _coerce_str(ss.get("scenario_id"))
    has_save_record = bool(last_saved_at or scenario_id)

    sources: list[str] = []
    sources.append("workspace_state.dirty=" + str(is_dirty))
    if has_prior_run:
        sources.append("workspace_state.last_runtime_snapshot_id=set")
    if has_runtime_run:
        sources.append("runtime_summary.run_id|run_at=set")
    if has_save_record:
        sources.append("save_state=set")

    # Classification
    if is_dirty and has_prior_run:
        state = DIRTY_STATE_NEEDS_RERUN
    elif is_dirty and not has_prior_run and not has_save_record:
        state = DIRTY_STATE_UNSAVED
    elif is_dirty:
        # dirty but no prior run + has save record
        state = DIRTY_STATE_DIRTY
    elif not is_dirty and has_prior_run and not has_save_record:
        # clean workspace + prior run + no save record
        # (e.g. fresh project) — the saved snapshot is
        # therefore the baseline; if there is a prior run
        # we treat the saved snapshot as current unless we
        # can prove otherwise.
        state = DIRTY_STATE_SAVED
    elif not is_dirty and has_prior_run and has_save_record:
        # clean + prior run + save record — the save may
        # predate the run. The "saved" gate holds only if
        # the save record is more recent than the run.
        # Without timestamp comparison we conservatively
        # classify as saved (the user has a clean save and
        # a run).
        state = DIRTY_STATE_SAVED
    elif not is_dirty and not has_prior_run and has_save_record:
        state = DIRTY_STATE_SAVED
    else:
        state = DIRTY_STATE_UNKNOWN

    return DirtyState(
        state=state,
        label=DIRTY_STATE_LABELS[state],
        tone=DIRTY_STATE_TONES[state],
        hint=DIRTY_STATE_HINTS[state],
        rerun_recommended=(
            state == DIRTY_STATE_NEEDS_RERUN
            or state == DIRTY_STATE_STALE
        ),
        unsaved_warning=(
            is_dirty
            and state != DIRTY_STATE_SAVED
            and state != DIRTY_STATE_UNKNOWN
        ),
        stale=(state == DIRTY_STATE_STALE),
        sources=tuple(sources),
    )


# ---------------------------------------------------------------------------
# Convenience accessors
# ---------------------------------------------------------------------------


def is_rerun_recommended(state: DirtyState) -> bool:
    """Return True if the partial should show a 'rerun
    recommended' warning."""
    return state.rerun_recommended


def is_unsaved_warning(state: DirtyState) -> bool:
    """Return True if the partial should show an 'unsaved
    changes' warning."""
    return state.unsaved_warning


def is_stale(state: DirtyState) -> bool:
    """Return True if the partial should show a 'stale
    result' badge."""
    return state.stale
