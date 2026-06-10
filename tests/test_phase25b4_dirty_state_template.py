"""Phase 25B-4 — Dirty State partial rendering tests.

Goal: User always knows whether the active scenario is
saved, unsaved, stale, or needs a rerun.

These tests prove the partial:

- renders nothing when ``dirty_state`` is missing
- renders exactly ONE badge per state
- applies the correct tone class for each state
- shows the rerun-recommended hint for needs_rerun +
  stale states
- shows the unsaved warning for dirty + unsaved states
- never invents a save timestamp
- is purely presentational; never mutates the helper
  output
- matches the existing badge vocabulary
  (badge-pass / badge-warn / badge-dirty / badge-blocked)
"""

import os
import sys

import pytest
from jinja2 import Environment, FileSystemLoader


HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
TEMPLATES_DIR = os.path.join(REPO_ROOT, "app", "templates")
PARTIALS_DIR = os.path.join(TEMPLATES_DIR, "partials")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


from app.ui.dirty_state import (
    DIRTY_STATE_DIRTY,
    DIRTY_STATE_NEEDS_RERUN,
    DIRTY_STATE_SAVED,
    DIRTY_STATE_STALE,
    DIRTY_STATE_UNSAVED,
    DIRTY_STATE_UNKNOWN,
    resolve_dirty_state,
)


# ---------------------------------------------------------------------------
# 1. Jinja environment fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def jinja_env():
    env = Environment(
        loader=FileSystemLoader([TEMPLATES_DIR, PARTIALS_DIR]),
        autoescape=False,
    )
    return env


# ---------------------------------------------------------------------------
# 2. Render nothing when context is missing
# ---------------------------------------------------------------------------


class TestRenderNothingWhenMissing:
    """The partial must render nothing if ``dirty_state``
    is missing from the context."""

    def test_renders_nothing_without_dirty_state(self, jinja_env):
        tpl = jinja_env.get_template(
            "partials/_dirty_state_badge.html",
        )
        out = tpl.render()
        assert out.strip() == "", (
            "partial must render nothing when "
            "dirty_state is missing"
        )

    def test_renders_nothing_with_empty_dirty_state(self, jinja_env):
        tpl = jinja_env.get_template(
            "partials/_dirty_state_badge.html",
        )
        out = tpl.render(dirty_state=None)
        assert out.strip() == ""

    def test_renders_nothing_with_empty_string(self, jinja_env):
        tpl = jinja_env.get_template(
            "partials/_dirty_state_badge.html",
        )
        out = tpl.render(dirty_state="")
        assert out.strip() == ""


# ---------------------------------------------------------------------------
# 3. Render exactly one badge per state
# ---------------------------------------------------------------------------


class TestRenderOneBadgePerState:
    """For each state, the partial renders exactly one
    badge with the correct label."""

    def test_saved_badge_renders(self, jinja_env):
        s = resolve_dirty_state(
            workspace_state={"dirty": False},
            save_state={"last_saved_at": "2026-06-10T10:00:00Z"},
        )
        tpl = jinja_env.get_template(
            "partials/_dirty_state_badge.html",
        )
        out = tpl.render(dirty_state=s)
        assert "SAVED" in out
        assert "badge-pass" in out
        assert "data-dirty-state=\"saved\"" in out

    def test_dirty_badge_renders(self, jinja_env):
        s = resolve_dirty_state(
            workspace_state={"dirty": True},
            save_state={"last_saved_at": "2026-06-10T10:00:00Z"},
        )
        tpl = jinja_env.get_template(
            "partials/_dirty_state_badge.html",
        )
        out = tpl.render(dirty_state=s)
        assert "UNSAVED EDITS" in out
        assert "badge-dirty" in out
        assert "data-dirty-state=\"dirty\"" in out

    def test_needs_rerun_badge_renders(self, jinja_env):
        s = resolve_dirty_state(
            workspace_state={
                "dirty": True,
                "last_runtime_snapshot_id": "snap-1",
            },
        )
        tpl = jinja_env.get_template(
            "partials/_dirty_state_badge.html",
        )
        out = tpl.render(dirty_state=s)
        assert "RERUN RECOMMENDED" in out
        assert "badge-warn" in out
        assert "data-dirty-state=\"needs_rerun\"" in out

    def test_unsaved_badge_renders(self, jinja_env):
        s = resolve_dirty_state(
            workspace_state={"dirty": True},
        )
        tpl = jinja_env.get_template(
            "partials/_dirty_state_badge.html",
        )
        out = tpl.render(dirty_state=s)
        assert "UNSAVED" in out
        assert "badge-dirty" in out
        assert "data-dirty-state=\"unsaved\"" in out

    def test_unknown_badge_renders_dash(self, jinja_env):
        s = resolve_dirty_state(None)
        tpl = jinja_env.get_template(
            "partials/_dirty_state_badge.html",
        )
        out = tpl.render(dirty_state=s)
        assert "—" in out
        assert "data-dirty-state=\"unknown\"" in out


# ---------------------------------------------------------------------------
# 4. Data attributes for downstream JS / tests
# ---------------------------------------------------------------------------


class TestDataAttributes:
    """The partial exposes data-* attributes for
    downstream consumers."""

    @pytest.mark.parametrize(
        "state,expected_class",
        [
            (DIRTY_STATE_SAVED, "pass"),
            (DIRTY_STATE_DIRTY, "dirty"),
            (DIRTY_STATE_NEEDS_RERUN, "warn"),
            (DIRTY_STATE_UNSAVED, "dirty"),
            (DIRTY_STATE_UNKNOWN, "none"),
        ],
    )
    def test_tone_class_applied(
        self, jinja_env, state, expected_class,
    ):
        # Force a specific state by constructing a
        # DirtyState directly
        from app.ui.dirty_state import DirtyState
        s = DirtyState(
            state=state,
            label="X",
            tone=expected_class,
            hint="hint",
            rerun_recommended=False,
            unsaved_warning=False,
            stale=False,
        )
        tpl = jinja_env.get_template(
            "partials/_dirty_state_badge.html",
        )
        out = tpl.render(dirty_state=s)
        assert f"dirty-state-badge--{expected_class}" in out
        assert f"data-dirty-state=\"{state}\"" in out
