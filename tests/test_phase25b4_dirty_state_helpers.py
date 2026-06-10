"""Phase 25B-4 — Dirty state UI helper unit tests.

These tests pin the behaviour of ``app.ui.dirty_state`` and the
shape of the ``dirty_state_ui`` payload that flows from
``_workspace_refresh_payload`` into the workspace template.

No DB, no HTTP, no template render. Pure Python.
"""
from __future__ import annotations

import pytest

from app.ui.dirty_state import (
    SAVED_BADGE_LABEL,
    UNSAVED_BADGE_LABEL,
    STALE_BADGE_LABEL,
    badge_saved_state,
    build_dirty_state_ui,
    changes_not_saved_notice,
    run_disabled_warning,
    scenario_dirty_indicator,
)


# ─────────────────────────────────────────────────────────────────────────
# Test 1: badge_saved_state — saved/unsaved/stale/factory matrix
# ─────────────────────────────────────────────────────────────────────────

class TestBadgeSavedState:
    def test_clean_user_project_is_saved(self):
        result = badge_saved_state(dirty=False, has_runtime_snapshot=True, is_user_project=True)
        assert result["state"] == "saved"
        assert result["label"] == SAVED_BADGE_LABEL
        assert result["css_class"] == "ds-badge--saved"

    def test_clean_user_project_no_snapshot_is_saved(self):
        result = badge_saved_state(dirty=False, has_runtime_snapshot=False, is_user_project=True)
        assert result["state"] == "saved"
        assert result["label"] == SAVED_BADGE_LABEL

    def test_dirty_user_project_no_snapshot_is_unsaved(self):
        result = badge_saved_state(dirty=True, has_runtime_snapshot=False, is_user_project=True)
        assert result["state"] == "unsaved"
        assert result["label"] == UNSAVED_BADGE_LABEL
        assert result["css_class"] == "ds-badge--unsaved"

    def test_dirty_user_project_with_snapshot_is_stale(self):
        result = badge_saved_state(dirty=True, has_runtime_snapshot=True, is_user_project=True)
        assert result["state"] == "stale"
        assert result["label"] == STALE_BADGE_LABEL
        assert result["css_class"] == "ds-badge--stale"

    def test_factory_project_is_factory(self):
        result = badge_saved_state(dirty=False, has_runtime_snapshot=False, is_user_project=False)
        assert result["state"] == "factory"
        assert "Read-only" in result["label"]
        assert result["css_class"] == "ds-badge--factory"

    def test_factory_overrides_dirty(self):
        # Even if dirty were passed (shouldn't happen, but defensive),
        # factory projects never show "unsaved" / "stale" badges.
        result = badge_saved_state(dirty=True, has_runtime_snapshot=True, is_user_project=False)
        assert result["state"] == "factory"

    def test_badge_has_icon(self):
        for kwargs in [
            dict(dirty=False, has_runtime_snapshot=False, is_user_project=True),
            dict(dirty=True, has_runtime_snapshot=False, is_user_project=True),
            dict(dirty=True, has_runtime_snapshot=True, is_user_project=True),
            dict(dirty=False, has_runtime_snapshot=False, is_user_project=False),
        ]:
            result = badge_saved_state(**kwargs)
            assert isinstance(result["icon"], str) and len(result["icon"]) >= 1


# ─────────────────────────────────────────────────────────────────────────
# Test 2: scenario_dirty_indicator
# ─────────────────────────────────────────────────────────────────────────

class TestScenarioDirtyIndicator:
    def test_active_dirty_user_project_is_dirty(self):
        result = scenario_dirty_indicator(
            is_active_scenario=True, workspace_dirty=True, is_user_project=True,
        )
        assert result["is_dirty"] is True
        assert result["css_class"] == "ds-dot--dirty"

    def test_inactive_user_project_is_clean(self):
        # Even when workspace is dirty, inactive scenarios are not dirty.
        result = scenario_dirty_indicator(
            is_active_scenario=False, workspace_dirty=True, is_user_project=True,
        )
        assert result["is_dirty"] is False
        assert result["css_class"] == ""

    def test_active_clean_user_project_is_clean(self):
        result = scenario_dirty_indicator(
            is_active_scenario=True, workspace_dirty=False, is_user_project=True,
        )
        assert result["is_dirty"] is False

    def test_factory_project_never_dirty(self):
        result = scenario_dirty_indicator(
            is_active_scenario=True, workspace_dirty=True, is_user_project=False,
        )
        assert result["is_dirty"] is False
        assert "Factory" in result["title"]

    def test_clean_state_title_present(self):
        result = scenario_dirty_indicator(
            is_active_scenario=False, workspace_dirty=False, is_user_project=True,
        )
        assert "Clean" in result["title"]


# ─────────────────────────────────────────────────────────────────────────
# Test 3: changes_not_saved_notice
# ─────────────────────────────────────────────────────────────────────────

class TestChangesNotSavedNotice:
    def test_dirty_user_project_returns_notice(self):
        result = changes_not_saved_notice(dirty=True, is_user_project=True)
        assert result is not None
        assert "Changes not yet saved" in result["title"]
        assert "Save to persist" in result["body"]
        assert "Run does not auto-save" in result["body"]
        assert result["css_class"] == "ds-notice--unsaved"

    def test_clean_user_project_returns_none(self):
        result = changes_not_saved_notice(dirty=False, is_user_project=True)
        assert result is None

    def test_factory_project_returns_factory_notice(self):
        result = changes_not_saved_notice(dirty=True, is_user_project=False)
        assert result is not None
        assert "Factory" in result["title"]
        assert "Duplicate" in result["body"]
        assert result["css_class"] == "ds-notice--factory"

    def test_factory_clean_returns_factory_notice(self):
        # Factory project — even when clean, we still show the read-only
        # notice so the user understands the baseline can't be modified.
        result = changes_not_saved_notice(dirty=False, is_user_project=False)
        assert result is not None
        assert "Factory" in result["title"]


# ─────────────────────────────────────────────────────────────────────────
# Test 4: run_disabled_warning
# ─────────────────────────────────────────────────────────────────────────

class TestRunDisabledWarning:
    def test_stale_user_project_returns_warning(self):
        result = run_disabled_warning(dirty=True, has_runtime_snapshot=True, is_user_project=True)
        assert result is not None
        assert "older than current draft" in result["title"]
        assert "Re-run after saving" in result["body"]
        assert result["css_class"] == "ds-warning--stale"

    def test_dirty_no_snapshot_no_warning(self):
        # No snapshot bound → running will not be stale (just no prior result).
        result = run_disabled_warning(dirty=True, has_runtime_snapshot=False, is_user_project=True)
        assert result is None

    def test_clean_no_warning(self):
        result = run_disabled_warning(dirty=False, has_runtime_snapshot=True, is_user_project=True)
        assert result is None

    def test_factory_no_warning(self):
        result = run_disabled_warning(dirty=True, has_runtime_snapshot=True, is_user_project=False)
        assert result is None


# ─────────────────────────────────────────────────────────────────────────
# Test 5: build_dirty_state_ui — composition
# ─────────────────────────────────────────────────────────────────────────

class TestBuildDirtyStateUi:
    SCENARIOS = [
        {"scenario_id": "a1", "scenario_name": "Base"},
        {"scenario_id": "a2", "scenario_name": "Downside"},
        {"scenario_id": "a3", "scenario_name": "Upside"},
    ]

    def test_clean_user_project(self):
        result = build_dirty_state_ui(
            dirty=False,
            has_runtime_snapshot=True,
            is_user_project=True,
            active_scenario_id="a1",
            scenarios=self.SCENARIOS,
        )
        assert result["badge"]["state"] == "saved"
        assert result["notice"] is None
        assert result["run_warning"] is None
        # All scenarios clean.
        assert all(d["is_dirty"] is False for d in result["scenario_dots"])

    def test_dirty_user_project(self):
        result = build_dirty_state_ui(
            dirty=True,
            has_runtime_snapshot=False,
            is_user_project=True,
            active_scenario_id="a1",
            scenarios=self.SCENARIOS,
        )
        assert result["badge"]["state"] == "unsaved"
        assert result["notice"] is not None
        assert result["run_warning"] is None
        # Only the active scenario is dirty.
        dirty = [d for d in result["scenario_dots"] if d["is_dirty"]]
        assert len(dirty) == 1
        assert dirty[0]["scenario_id"] == "a1"

    def test_stale_user_project(self):
        result = build_dirty_state_ui(
            dirty=True,
            has_runtime_snapshot=True,
            is_user_project=True,
            active_scenario_id="a2",
            scenarios=self.SCENARIOS,
        )
        assert result["badge"]["state"] == "stale"
        assert result["run_warning"] is not None
        # Active scenario is the dirty one.
        dirty = [d for d in result["scenario_dots"] if d["is_dirty"]]
        assert dirty[0]["scenario_id"] == "a2"

    def test_factory_project(self):
        result = build_dirty_state_ui(
            dirty=False,
            has_runtime_snapshot=True,
            is_user_project=False,
            active_scenario_id="a1",
            scenarios=self.SCENARIOS,
        )
        assert result["badge"]["state"] == "factory"
        # Factory shows the read-only notice, no unsaved, no run warning.
        assert result["notice"] is not None
        assert "Factory" in result["notice"]["title"]
        assert result["run_warning"] is None
        # No scenario is dirty.
        assert all(d["is_dirty"] is False for d in result["scenario_dots"])

    def test_no_scenarios(self):
        result = build_dirty_state_ui(
            dirty=True,
            has_runtime_snapshot=True,
            is_user_project=True,
            active_scenario_id="",
            scenarios=None,
        )
        assert result["scenario_dots"] == []
        assert result["badge"]["state"] == "stale"

    def test_empty_scenarios(self):
        result = build_dirty_state_ui(
            dirty=True,
            has_runtime_snapshot=True,
            is_user_project=True,
            active_scenario_id="",
            scenarios=[],
        )
        assert result["scenario_dots"] == []

    def test_scenarios_with_missing_ids(self):
        # Defensive: scenarios without id are skipped.
        result = build_dirty_state_ui(
            dirty=True,
            has_runtime_snapshot=False,
            is_user_project=True,
            active_scenario_id="",
            scenarios=[{"scenario_name": "no-id"}, {"scenario_id": "a2", "scenario_name": "Downside"}],
        )
        # No active scenario → no dirty dot anywhere.
        assert all(d["is_dirty"] is False for d in result["scenario_dots"])
        # But the scenarios are still listed.
        assert len(result["scenario_dots"]) == 2

    def test_payload_shape_is_stable(self):
        result = build_dirty_state_ui(
            dirty=False, has_runtime_snapshot=False, is_user_project=True,
            active_scenario_id="a1", scenarios=self.SCENARIOS,
        )
        assert set(result.keys()) == {"badge", "notice", "run_warning", "scenario_dots"}
        assert set(result["badge"].keys()) == {"label", "state", "css_class", "icon"}
        for dot in result["scenario_dots"]:
            assert set(dot.keys()) == {
                "scenario_id", "scenario_name", "is_active", "is_dirty", "css_class", "title",
            }
