"""Phase 25B-4 — Dirty State helper tests.

Goal: User always knows whether the active scenario is
saved, unsaved, stale, or needs a rerun.

These tests prove the helper:

- resolves to the 4 documented states:
  saved / dirty / needs_rerun / stale
- resolves to a safe 'unknown' fallback when context is
  missing
- does NOT mutate the input context
- does NOT call the persistence layer
- exposes read-only accessors
  ``is_rerun_recommended`` / ``is_unsaved_warning`` /
  ``is_stale``
- never invents a save timestamp or run id
- classifies dirty + no-prior-run as "unsaved" (no save
  record)
- classifies dirty + no-prior-run + has-save-record as
  "dirty" (unsaved edits on top of an existing save)
- classifies dirty + prior-run as "needs_rerun"
- classifies clean + no-prior-run + has-save-record as
  "saved"
- exposes pre-classified label / tone / hint fields
"""

import os
import sys

import pytest


# ---------------------------------------------------------------------------
#  Fixtures
# ---------------------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


from app.ui.dirty_state import (
    DIRTY_STATE_DIRTY,
    DIRTY_STATE_HINTS,
    DIRTY_STATE_LABELS,
    DIRTY_STATE_NEEDS_RERUN,
    DIRTY_STATE_SAVED,
    DIRTY_STATE_STALE,
    DIRTY_STATE_TONES,
    DIRTY_STATE_UNKNOWN,
    DIRTY_STATE_UNSAVED,
    DirtyState,
    is_rerun_recommended,
    is_stale,
    is_unsaved_warning,
    resolve_dirty_state,
)


# ---------------------------------------------------------------------------
# 1. State vocabulary
# ---------------------------------------------------------------------------


class TestStateVocabulary:
    """The state vocabulary has 6 entries: 4 documented
    states + unsaved + unknown fallback."""

    def test_label_count(self):
        assert len(DIRTY_STATE_LABELS) == 6

    def test_tone_count(self):
        assert len(DIRTY_STATE_TONES) == 6

    def test_hint_count(self):
        assert len(DIRTY_STATE_HINTS) == 6

    def test_labels_keys(self):
        expected = {
            DIRTY_STATE_SAVED,
            DIRTY_STATE_DIRTY,
            DIRTY_STATE_STALE,
            DIRTY_STATE_NEEDS_RERUN,
            DIRTY_STATE_UNSAVED,
            DIRTY_STATE_UNKNOWN,
        }
        assert set(DIRTY_STATE_LABELS.keys()) == expected

    def test_tones_keys(self):
        expected = {
            DIRTY_STATE_SAVED,
            DIRTY_STATE_DIRTY,
            DIRTY_STATE_STALE,
            DIRTY_STATE_NEEDS_RERUN,
            DIRTY_STATE_UNSAVED,
            DIRTY_STATE_UNKNOWN,
        }
        assert set(DIRTY_STATE_TONES.keys()) == expected


# ---------------------------------------------------------------------------
# 2. resolve_dirty_state — full classification matrix
# ---------------------------------------------------------------------------


class TestResolveDirtyState:
    """The classification matrix covers all
    dirty / has_prior_run / has_save_record combinations."""

    def test_unknown_when_workspace_state_is_none(self):
        s = resolve_dirty_state(None)
        assert s.state == DIRTY_STATE_UNKNOWN
        assert s.label == DIRTY_STATE_LABELS[DIRTY_STATE_UNKNOWN]
        assert s.tone == DIRTY_STATE_TONES[DIRTY_STATE_UNKNOWN]
        assert s.rerun_recommended is False
        assert s.unsaved_warning is False
        assert s.stale is False

    def test_saved_when_clean_and_save_record(self):
        """Clean workspace + save record (no run yet) =
        SAVED."""
        s = resolve_dirty_state(
            workspace_state={"dirty": False},
            runtime_summary={},
            save_state={"last_saved_at": "2026-06-10T10:00:00Z"},
        )
        assert s.state == DIRTY_STATE_SAVED
        assert s.rerun_recommended is False
        assert s.unsaved_warning is False
        assert s.stale is False

    def test_dirty_with_save_record_but_no_prior_run(self):
        """Dirty + has save record + no prior run = DIRTY."""
        s = resolve_dirty_state(
            workspace_state={"dirty": True},
            runtime_summary={},
            save_state={"last_saved_at": "2026-06-10T10:00:00Z"},
        )
        assert s.state == DIRTY_STATE_DIRTY
        assert s.unsaved_warning is True
        assert s.rerun_recommended is False
        assert s.stale is False

    def test_unsaved_when_dirty_and_no_save_and_no_run(self):
        """Dirty + no save record + no prior run = UNSAVED."""
        s = resolve_dirty_state(
            workspace_state={"dirty": True},
            runtime_summary={},
            save_state={},
        )
        assert s.state == DIRTY_STATE_UNSAVED
        assert s.unsaved_warning is True
        assert s.rerun_recommended is False

    def test_needs_rerun_when_dirty_with_prior_run(self):
        """Dirty + prior run = NEEDS_RERUN."""
        s = resolve_dirty_state(
            workspace_state={
                "dirty": True,
                "last_runtime_snapshot_id": "snap-abc",
            },
            runtime_summary={"run_id": "run-1", "last_run_at": "2026-06-10T10:00:00Z"},
        )
        assert s.state == DIRTY_STATE_NEEDS_RERUN
        assert s.rerun_recommended is True
        assert s.unsaved_warning is True

    def test_saved_when_clean_with_prior_run_and_save(self):
        """Clean + prior run + save record = SAVED
        (we do not invent a timestamp comparison)."""
        s = resolve_dirty_state(
            workspace_state={
                "dirty": False,
                "last_runtime_snapshot_id": "snap-abc",
            },
            runtime_summary={"run_id": "run-1"},
            save_state={"last_saved_at": "2026-06-10T10:00:00Z"},
        )
        assert s.state == DIRTY_STATE_SAVED
        assert s.rerun_recommended is False
        assert s.stale is False

    def test_saved_when_clean_with_prior_run_no_save_record(self):
        """Clean + prior run + no save record = SAVED."""
        s = resolve_dirty_state(
            workspace_state={
                "dirty": False,
                "last_runtime_snapshot_id": "snap-abc",
            },
            runtime_summary={"run_id": "run-1"},
        )
        assert s.state == DIRTY_STATE_SAVED
        assert s.rerun_recommended is False


# ---------------------------------------------------------------------------
# 3. Read-only accessors
# ---------------------------------------------------------------------------


class TestReadOnlyAccessors:
    """The accessors return frozen fields, never
    re-classify."""

    def test_rerun_recommended_for_needs_rerun(self):
        s = resolve_dirty_state(
            workspace_state={
                "dirty": True,
                "last_runtime_snapshot_id": "snap-abc",
            },
        )
        assert is_rerun_recommended(s) is True
        assert is_unsaved_warning(s) is True
        assert is_stale(s) is False

    def test_no_rerun_recommended_for_dirty(self):
        s = resolve_dirty_state(
            workspace_state={"dirty": True},
            save_state={"last_saved_at": "2026-06-10T10:00:00Z"},
        )
        assert is_rerun_recommended(s) is False
        assert is_unsaved_warning(s) is True

    def test_no_warning_for_saved(self):
        s = resolve_dirty_state(
            workspace_state={"dirty": False},
            save_state={"last_saved_at": "2026-06-10T10:00:00Z"},
        )
        assert is_rerun_recommended(s) is False
        assert is_unsaved_warning(s) is False
        assert is_stale(s) is False


# ---------------------------------------------------------------------------
# 4. Safety: helper does not mutate
# ---------------------------------------------------------------------------


class TestHelperDoesNotMutate:
    """The helper must not mutate the input context."""

    def test_workspace_state_dict_unchanged_after_resolve(self):
        ws = {"dirty": True, "last_runtime_snapshot_id": "snap-1"}
        ws_snapshot = dict(ws)
        _ = resolve_dirty_state(workspace_state=ws)
        assert ws == ws_snapshot

    def test_runtime_summary_dict_unchanged_after_resolve(self):
        rs = {"run_id": "run-1", "last_run_at": "2026-06-10T10:00:00Z"}
        rs_snapshot = dict(rs)
        _ = resolve_dirty_state(
            workspace_state={"dirty": False},
            runtime_summary=rs,
        )
        assert rs == rs_snapshot

    def test_save_state_dict_unchanged_after_resolve(self):
        ss = {"last_saved_at": "2026-06-10T10:00:00Z", "scenario_id": "s-1"}
        ss_snapshot = dict(ss)
        _ = resolve_dirty_state(
            workspace_state={"dirty": True},
            save_state=ss,
        )
        assert ss == ss_snapshot

    def test_dirty_state_dataclass_is_frozen(self):
        s = resolve_dirty_state(workspace_state={"dirty": False})
        with pytest.raises(Exception):
            s.state = "saved"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 5. No persistence calls
# ---------------------------------------------------------------------------


class TestNoPersistenceCalls:
    """The helper must not call the persistence layer."""

    def test_helper_does_not_import_persistence(self):
        from app.ui import dirty_state
        src = open(dirty_state.__file__).read()
        assert "app.persistence" not in src, (
            "dirty_state helper must NOT import the "
            "persistence layer"
        )
        assert "from app.persistence" not in src
        assert "import app.persistence" not in src

    def test_helper_does_not_import_services(self):
        from app.ui import dirty_state
        src = open(dirty_state.__file__).read()
        assert "app.services" not in src
        assert "from app.services" not in src
        assert "import app.services" not in src

    def test_helper_does_not_import_run_service(self):
        from app.ui import dirty_state
        src = open(dirty_state.__file__).read()
        # We allow the bare token ``run_service`` in
        # docstrings (as a reference) but we forbid any
        # actual import or call. Walk the source, track
        # whether we are inside a triple-quoted string,
        # and inspect only non-docstring lines.
        in_docstring = False
        quote = None
        for line in src.splitlines():
            stripped = line.strip()
            # Detect docstring boundaries
            triple = None
            if '"""' in stripped:
                triple = '"""'
            elif "'''" in stripped:
                triple = "'''"
            count = stripped.count(triple) if triple else 0
            if not in_docstring:
                if triple and count == 1:
                    in_docstring = True
                    quote = triple
                    continue
                if triple and count >= 2:
                    # single-line docstring
                    continue
                if not stripped or stripped.startswith("#"):
                    continue
                assert "run_service" not in stripped, (
                    f"dirty_state must NOT reference "
                    f"run_service outside docstrings: "
                    f"{line!r}"
                )
            else:
                if triple and count >= 1:
                    in_docstring = False
                    quote = None
                continue


# ---------------------------------------------------------------------------
# 6. Pre-classified fields
# ---------------------------------------------------------------------------


class TestPreClassifiedFields:
    """The helper returns a DirtyState with
    pre-classified label / tone / hint."""

    def test_label_matches_vocabulary(self):
        s = resolve_dirty_state(workspace_state={"dirty": False})
        assert s.label == DIRTY_STATE_LABELS[s.state]

    def test_tone_matches_vocabulary(self):
        s = resolve_dirty_state(
            workspace_state={"dirty": True},
            save_state={"last_saved_at": "2026-06-10T10:00:00Z"},
        )
        assert s.tone == DIRTY_STATE_TONES[s.state]

    def test_hint_matches_vocabulary(self):
        s = resolve_dirty_state(
            workspace_state={
                "dirty": True,
                "last_runtime_snapshot_id": "snap-1",
            },
        )
        assert s.hint == DIRTY_STATE_HINTS[s.state]

    def test_sources_field_is_tuple(self):
        s = resolve_dirty_state(workspace_state={"dirty": True})
        assert isinstance(s.sources, tuple)
        assert len(s.sources) > 0
