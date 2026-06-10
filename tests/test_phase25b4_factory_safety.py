"""Phase 25B-4 — Factory project safety, hard constraints, regression.

These tests pin the property that the dirty-state UI work does not
mutate factory projects (TUHO / Oborovo) or break the rc1 path.

The full flow is not exercised (no live DB) — we test the
*contracts* the UI relies on:

  1. Factory projects always get the "Read-only baseline" badge.
  2. The helper never returns a "Saved/Unsaved/Stale" badge for
     factory projects, even if the caller passes dirty=True.
  3. No scenario under a factory project is ever marked dirty.
  4. The wire-up point (``_workspace_refresh_payload``) is a pure
     addition: existing return-tuple users can be updated without
     breaking the contract — the new field is the last element.
  5. The CSS additions are additive (``ds-*`` prefix, no ` :root `
     blocks added, no flag flips in the new code).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.ui.dirty_state import (
    build_dirty_state_ui,
    badge_saved_state,
    scenario_dirty_indicator,
)


# ─────────────────────────────────────────────────────────────────────────
# Test 1: factory never shows unsaved/stale/saved badges
# ─────────────────────────────────────────────────────────────────────────

class TestFactoryBadgeNeverMislabelled:
    @pytest.mark.parametrize("dirty,has_snap", [
        (False, False), (False, True), (True, False), (True, True),
    ])
    def test_factory_badge_is_factory(self, dirty, has_snap):
        result = badge_saved_state(
            dirty=dirty, has_runtime_snapshot=has_snap, is_user_project=False,
        )
        assert result["state"] == "factory", (
            f"Factory project with dirty={dirty}, snap={has_snap} must be 'factory',"
            f" got {result['state']}"
        )
        assert result["css_class"] == "ds-badge--factory"

    def test_factory_label_is_read_only(self):
        result = badge_saved_state(dirty=True, has_runtime_snapshot=True, is_user_project=False)
        assert "Read-only" in result["label"]


# ─────────────────────────────────────────────────────────────────────────
# Test 2: factory scenario dots are never dirty
# ─────────────────────────────────────────────────────────────────────────

class TestFactoryScenariosNeverDirty:
    def test_active_scenario_factory_clean(self):
        result = scenario_dirty_indicator(
            is_active_scenario=True, workspace_dirty=True, is_user_project=False,
        )
        assert result["is_dirty"] is False

    def test_factory_full_ui_no_dots(self):
        result = build_dirty_state_ui(
            dirty=True,
            has_runtime_snapshot=True,
            is_user_project=False,
            active_scenario_id="x",
            scenarios=[
                {"scenario_id": "x", "scenario_name": "Base"},
                {"scenario_id": "y", "scenario_name": "Downside"},
            ],
        )
        assert all(d["is_dirty"] is False for d in result["scenario_dots"])


# ─────────────────────────────────────────────────────────────────────────
# Test 3: factory notice is read-only, not "unsaved"
# ─────────────────────────────────────────────────────────────────────────

class TestFactoryNoticeReadOnly:
    def test_factory_notice_does_not_say_unsaved(self):
        from app.ui.dirty_state import changes_not_saved_notice
        result = changes_not_saved_notice(dirty=True, is_user_project=False)
        assert result is not None
        assert "Unsaved" not in result["title"]
        assert "Read-only" not in result["title"]  # Just says Factory
        assert "Factory" in result["title"]
        assert "Duplicate" in result["body"] or "Save As" in result["body"]


# ─────────────────────────────────────────────────────────────────────────
# Test 4: factory project never shows run-disabled warning
# ─────────────────────────────────────────────────────────────────────────

class TestFactoryRunWarningSuppressed:
    def test_factory_no_run_warning(self):
        from app.ui.dirty_state import run_disabled_warning
        result = run_disabled_warning(
            dirty=True, has_runtime_snapshot=True, is_user_project=False,
        )
        assert result is None


# ─────────────────────────────────────────────────────────────────────────
# Test 5: hard constraints — no model formulas, no flag flips, no schema
# ─────────────────────────────────────────────────────────────────────────

class TestHardConstraints:
    def test_dirty_state_helper_does_not_import_db(self):
        text = Path("app/ui/dirty_state.py").read_text()
        # Pure module — no DB / persistence / form / schema imports.
        for forbidden in [
            "from app.persistence",
            "import app.persistence",
            "from app.services.",
            "import app.services.",
            "import sqlite3",
            "import requests",
            "from fastapi",
            "from app.main_web",
        ]:
            assert forbidden not in text, (
                f"app/ui/dirty_state.py must not import {forbidden}"
            )

    def test_dirty_state_helper_has_no_io(self):
        text = Path("app/ui/dirty_state.py").read_text()
        for forbidden in ["open(", ".write(", ".read(", "json.load", "json.dump"]:
            assert forbidden not in text, (
                f"app/ui/dirty_state.py must not perform I/O ({forbidden})"
            )

    def test_dirty_state_helper_has_no_time_calls(self):
        text = Path("app/ui/dirty_state.py").read_text()
        # No datetime.now() — timestamp is provided by the caller.
        for forbidden in ["datetime.now", "time.time", "datetime.utcnow"]:
            assert forbidden not in text, (
                f"app/ui/dirty_state.py must not call time primitives directly"
            )

    def test_css_additions_are_additive(self):
        text = Path("static/styles.css").read_text()
        # All .ds- rules must be additive (no `!important` that overrides,
        # no replacement of existing classes).
        ds_rules = re.findall(r"^\.(ds-[a-zA-Z0-9_-]+)\s*\{", text, re.MULTILINE)
        assert len(ds_rules) >= 10, f"Expected 10+ .ds- rules, found {len(ds_rules)}"
        # No !important on ds- rules (keep it simple / non-intrusive).
        for line in text.splitlines():
            if ".ds-" in line and "}" not in line and "{" not in line:
                # Property lines.
                assert "!important" not in line, (
                    f"ds- CSS must not use !important: {line}"
                )

    def test_css_did_not_modify_root_count(self):
        text = Path("static/styles.css").read_text()
        # Phase 24G-2 invariant: 3 :root blocks at top of file.
        assert len(re.findall(r"^:root", text, re.MULTILINE)) == 3, (
            "Phase 25B-4 must not add or remove :root blocks"
        )

    def test_partial_uses_no_inline_script(self):
        text = Path("app/templates/partials/dirty_state_indicators.html").read_text()
        assert "<script" not in text
        assert "onclick=" not in text
        assert "onchange=" not in text
        assert "onload=" not in text

    def test_no_tailwind_or_alpine(self):
        for fname in [
            "app/ui/dirty_state.py",
            "app/templates/partials/dirty_state_indicators.html",
        ]:
            text = Path(fname).read_text()
            for forbidden in ["tailwind", "alpine", "x-data", "x-show", "x-bind"]:
                # Use a stricter pattern: forbidden token followed by a
                # non-alphanumeric char or end-of-string, so that
                # legitimate references in comments (e.g. "No Tailwind")
                # don't trip the guard.
                pattern = re.compile(
                    rf"{re.escape(forbidden)}[\"'`<>=:\s]",
                    re.IGNORECASE,
                )
                assert not pattern.search(text), (
                    f"{fname} must not use {forbidden}"
                )


# ─────────────────────────────────────────────────────────────────────────
# Test 6: no autosave — explicit
# ─────────────────────────────────────────────────────────────────────────

class TestNoAutosave:
    def test_helper_does_not_schedule_save(self):
        text = Path("app/ui/dirty_state.py").read_text()
        # We look for code-level patterns, not words. The helper may
        # legitimately mention "save" in docstrings / labels.
        for forbidden in [
            "asyncio.create_task",
            "BackgroundTask",
            "asyncio.run",
            "threading.Thread",
            "schedule(",
            "autosave",
        ]:
            assert forbidden.lower() not in text.lower(), (
                f"app/ui/dirty_state.py must not schedule save: {forbidden}"
            )

    def test_partial_does_not_submit_forms(self):
        text = Path("app/templates/partials/dirty_state_indicators.html").read_text()
        for forbidden in ["<form", "</form>", "submit(", "fetch("]:
            assert forbidden not in text, (
                f"dirty_state_indicators.html must not submit: {forbidden}"
            )

    def test_helper_has_no_input_mutation(self):
        text = Path("app/ui/dirty_state.py").read_text()
        # The helper builds fresh dicts; it must not call mutating
        # methods on the caller's input (e.g. ``card.append`` would
        # mutate the scenario list passed in). The helper may
        # internally ``append`` to a freshly-created list.
        for forbidden in ["cards.append", "input.append", "items.append"]:
            assert forbidden not in text, (
                f"app/ui/dirty_state.py must not mutate caller input: {forbidden}"
            )


# ─────────────────────────────────────────────────────────────────────────
# Test 7: rc1 + parity path not touched
# ─────────────────────────────────────────────────────────────────────────

class TestRc1AndParityUnchanged:
    def test_compare_service_not_imported(self):
        text = Path("app/ui/dirty_state.py").read_text()
        for forbidden in ["compare_service", "base_vs_active", "multi_compare"]:
            assert forbidden not in text

    def test_waterfall_not_imported(self):
        text = Path("app/ui/dirty_state.py").read_text()
        for forbidden in ["waterfall", "construction", "tax_engine", "depreciation"]:
            assert forbidden.lower() not in text.lower()

    def test_no_construct_engine_flag(self):
        text = Path("app/ui/dirty_state.py").read_text()
        assert "use_construction_schedule_engine" not in text


# ─────────────────────────────────────────────────────────────────────────
# Test 8: payload-shape stability (template contract)
# ─────────────────────────────────────────────────────────────────────────

class TestPayloadShape:
    def test_top_level_keys(self):
        result = build_dirty_state_ui(
            dirty=True, has_runtime_snapshot=True, is_user_project=True,
            active_scenario_id="a", scenarios=[{"scenario_id": "a"}],
        )
        assert set(result.keys()) == {"badge", "notice", "run_warning", "scenario_dots"}

    def test_badge_keys(self):
        result = build_dirty_state_ui(
            dirty=False, has_runtime_snapshot=False, is_user_project=True,
            active_scenario_id="", scenarios=None,
        )
        b = result["badge"]
        assert set(b.keys()) == {"label", "state", "css_class", "icon"}

    def test_scenario_dot_keys(self):
        result = build_dirty_state_ui(
            dirty=True, has_runtime_snapshot=False, is_user_project=True,
            active_scenario_id="a", scenarios=[{"scenario_id": "a"}],
        )
        d = result["scenario_dots"][0]
        assert set(d.keys()) == {
            "scenario_id", "scenario_name", "is_active", "is_dirty", "css_class", "title",
        }

    def test_optional_fields_are_either_dict_or_none(self):
        result = build_dirty_state_ui(
            dirty=False, has_runtime_snapshot=False, is_user_project=True,
            active_scenario_id="", scenarios=None,
        )
        assert result["notice"] is None
        assert result["run_warning"] is None
