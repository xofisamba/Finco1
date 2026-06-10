"""Phase 25B-5 — Scenario workflow polish helper unit tests.

Pure-function tests for ``app.ui.scenario_workflow``. No DB, no HTTP,
no template render. Each test pins one contract.
"""
from __future__ import annotations

import pytest

from app.ui.scenario_workflow import (
    BASE_LABELS,
    DOWNSIDE_LABELS,
    UPSIDE_LABELS,
    build_compare_shortcut_links,
    build_scenario_workflow_ui,
    classify_scenario_label,
    quick_summary_card,
    workflow_state,
)


# ─────────────────────────────────────────────────────────────────────────
# Test 1: classify_scenario_label
# ─────────────────────────────────────────────────────────────────────────

class TestClassifyScenarioLabel:
    @pytest.mark.parametrize("name", ["base", "Base", "BASE", "Baseline", "Case", "Main"])
    def test_base_labels(self, name):
        result = classify_scenario_label(name)
        assert result["kind"] == "base"
        assert result["display_name"] == name
        assert result["css_class"] == "sw-label--base"

    @pytest.mark.parametrize("name", ["downside", "Downside", "Down", "low", "P10", "pessimistic", "stress"])
    def test_downside_labels(self, name):
        result = classify_scenario_label(name)
        assert result["kind"] == "downside"
        assert result["css_class"] == "sw-label--downside"

    @pytest.mark.parametrize("name", ["upside", "Upside", "Up", "high", "P90", "optimistic"])
    def test_upside_labels(self, name):
        result = classify_scenario_label(name)
        assert result["kind"] == "upside"
        assert result["css_class"] == "sw-label--upside"

    @pytest.mark.parametrize("name", ["My Custom", "Scenario X", "Best Case", "Reference"])
    def test_custom_labels(self, name):
        result = classify_scenario_label(name)
        assert result["kind"] == "custom"
        assert result["css_class"] == "sw-label--custom"

    def test_empty_string_is_custom(self):
        result = classify_scenario_label("")
        assert result["kind"] == "custom"

    def test_none_is_custom(self):
        result = classify_scenario_label(None)  # type: ignore[arg-type]
        assert result["kind"] == "custom"

    def test_label_has_icon(self):
        for kind in ("base", "downside", "upside", "custom"):
            label = next(
                v for v in [
                    next(iter(BASE_LABELS)),
                    next(iter(DOWNSIDE_LABELS)),
                    next(iter(UPSIDE_LABELS)),
                    "My Custom",
                ] if classify_scenario_label(v)["kind"] == kind
            )
            result = classify_scenario_label(label)
            assert isinstance(result["icon"], str) and len(result["icon"]) >= 1


# ─────────────────────────────────────────────────────────────────────────
# Test 2: quick_summary_card
# ─────────────────────────────────────────────────────────────────────────

class TestQuickSummaryCard:
    def test_full_card(self):
        card = {
            "equity_irr": 0.12,
            "project_irr": 0.09,
            "avg_dscr": 1.5,
        }
        result = quick_summary_card(card)
        assert result["equity_irr_pct"] == "12.0 %"
        assert result["project_irr_pct"] == "9.0 %"
        assert result["avg_dscr_x"] == "1.50 x"
        assert result["irr_state"] == "good"
        assert result["dscr_state"] == "good"

    def test_partial_card_only_irr(self):
        card = {"equity_irr": 0.10}
        result = quick_summary_card(card)
        assert result["equity_irr_pct"] == "10.0 %"
        assert result["project_irr_pct"] == "—"
        assert result["avg_dscr_x"] == "—"
        assert result["irr_state"] == "ok"
        assert result["dscr_state"] == "n_a"

    def test_state_thresholds_irr(self):
        # Below 8 % → bad
        assert quick_summary_card({"equity_irr": 0.05})["irr_state"] == "bad"
        # 8 % to <12 % → ok
        assert quick_summary_card({"equity_irr": 0.08})["irr_state"] == "ok"
        assert quick_summary_card({"equity_irr": 0.11})["irr_state"] == "ok"
        # ≥ 12 % → good
        assert quick_summary_card({"equity_irr": 0.12})["irr_state"] == "good"
        assert quick_summary_card({"equity_irr": 0.20})["irr_state"] == "good"

    def test_state_thresholds_dscr(self):
        assert quick_summary_card({"avg_dscr": 1.0})["dscr_state"] == "bad"
        assert quick_summary_card({"avg_dscr": 1.2})["dscr_state"] == "ok"
        assert quick_summary_card({"avg_dscr": 1.4})["dscr_state"] == "ok"
        assert quick_summary_card({"avg_dscr": 1.5})["dscr_state"] == "good"
        assert quick_summary_card({"avg_dscr": 2.0})["dscr_state"] == "good"

    def test_none_values(self):
        result = quick_summary_card({})
        assert result["equity_irr_pct"] == "—"
        assert result["project_irr_pct"] == "—"
        assert result["avg_dscr_x"] == "—"
        assert result["irr_state"] == "n_a"
        assert result["dscr_state"] == "n_a"

    def test_invalid_value_treated_as_none(self):
        # Non-numeric values must be treated as n_a, not crash.
        result = quick_summary_card({"equity_irr": "not-a-number"})
        assert result["irr_state"] == "n_a"
        assert result["equity_irr_pct"] == "—"

    def test_format_is_tabular(self):
        # Padded to one decimal place for percent, two for DSCR.
        assert quick_summary_card({"equity_irr": 0.123})["equity_irr_pct"] == "12.3 %"
        assert quick_summary_card({"avg_dscr": 1.234})["avg_dscr_x"] == "1.23 x"


# ─────────────────────────────────────────────────────────────────────────
# Test 3: build_compare_shortcut_links
# ─────────────────────────────────────────────────────────────────────────

class TestCompareShortcutLinks:
    def test_no_active_returns_empty(self):
        cards = [{"scenario_id": "a", "scenario_name": "Base"}]
        assert build_compare_shortcut_links(cards, active_scenario_id="") == []

    def test_active_not_found_returns_empty(self):
        cards = [{"scenario_id": "a", "scenario_name": "Base"}]
        assert build_compare_shortcut_links(cards, active_scenario_id="z") == []

    def test_base_active_shows_downside_and_upside(self):
        cards = [
            {"scenario_id": "a", "scenario_name": "Base"},
            {"scenario_id": "b", "scenario_name": "Downside"},
            {"scenario_id": "c", "scenario_name": "Upside"},
        ]
        links = build_compare_shortcut_links(cards, active_scenario_id="a")
        assert len(links) == 2
        names = [l["right_scenario_name"] for l in links]
        assert "Downside" in names
        assert "Upside" in names

    def test_base_active_excludes_other_custom(self):
        cards = [
            {"scenario_id": "a", "scenario_name": "Base"},
            {"scenario_id": "b", "scenario_name": "Downside"},
            {"scenario_id": "c", "scenario_name": "MyCustom"},
        ]
        links = build_compare_shortcut_links(cards, active_scenario_id="a")
        # When active is Base, we only show downside / upside, not
        # arbitrary custom scenarios.
        names = [l["right_scenario_name"] for l in links]
        assert names == ["Downside"]
        assert "MyCustom" not in names

    def test_downside_active_compares_with_base(self):
        cards = [
            {"scenario_id": "a", "scenario_name": "Base"},
            {"scenario_id": "b", "scenario_name": "Downside"},
            {"scenario_id": "c", "scenario_name": "Upside"},
        ]
        links = build_compare_shortcut_links(cards, active_scenario_id="b")
        names = [l["right_scenario_name"] for l in links]
        assert "Base" in names
        # Upside is also a valid comparison target.
        assert "Upside" in names

    def test_link_shape(self):
        cards = [
            {"scenario_id": "a", "scenario_name": "Base"},
            {"scenario_id": "b", "scenario_name": "Downside"},
        ]
        links = build_compare_shortcut_links(cards, active_scenario_id="a")
        assert len(links) == 1
        link = links[0]
        assert link["href"] == "/scenarios/compare?left_scenario_id=a&right_scenario_id=b"
        assert link["label"] == "Compare with Downside"
        assert link["kind"] == "downside"
        assert link["css_class"] == "sw-label--downside"
        assert link["right_scenario_id"] == "b"

    def test_sorted_by_kind_then_label(self):
        # When active is custom, links should come out sorted:
        # base first, then downside, then upside, then custom.
        cards = [
            {"scenario_id": "a", "scenario_name": "MyScenario"},
            {"scenario_id": "b", "scenario_name": "Base"},
            {"scenario_id": "c", "scenario_name": "Downside"},
            {"scenario_id": "d", "scenario_name": "Upside"},
        ]
        links = build_compare_shortcut_links(cards, active_scenario_id="a")
        kinds = [l["kind"] for l in links]
        # Order: base (0), downside (1), upside (2). Custom is the
        # active scenario, not a target.
        assert kinds == ["base", "downside", "upside"]


# ─────────────────────────────────────────────────────────────────────────
# Test 4: workflow_state
# ─────────────────────────────────────────────────────────────────────────

class TestWorkflowState:
    def test_empty(self):
        result = workflow_state([])
        assert result["count"] == 0
        assert result["state"] == "empty"
        assert "No saved scenarios" in result["message"]

    def test_none_cards(self):
        result = workflow_state(None)  # type: ignore[arg-type]
        assert result["state"] == "empty"
        assert result["count"] == 0

    def test_one(self):
        result = workflow_state([{"scenario_id": "a"}])
        assert result["count"] == 1
        assert result["state"] == "one"
        assert "Add at least one more" in result["message"]

    def test_two(self):
        result = workflow_state([{"scenario_id": "a"}, {"scenario_id": "b"}])
        assert result["count"] == 2
        assert result["state"] == "two"

    def test_many(self):
        result = workflow_state([{"scenario_id": f"s{i}"} for i in range(5)])
        assert result["count"] == 5
        assert result["state"] == "many"
        assert "5 scenarios" in result["message"]

    def test_css_class_present(self):
        for state in ("empty", "one", "two", "many"):
            cards = [{"scenario_id": "a"}] if state != "empty" else []
            if state == "two":
                cards = [{"scenario_id": "a"}, {"scenario_id": "b"}]
            elif state == "many":
                cards = [{"scenario_id": f"s{i}"} for i in range(3)]
            result = workflow_state(cards)
            assert result["css_class"] == f"sw-empty--{state}"


# ─────────────────────────────────────────────────────────────────────────
# Test 5: build_scenario_workflow_ui (composer)
# ─────────────────────────────────────────────────────────────────────────

class TestBuildScenarioWorkflowUi:
    CARDS = [
        {"scenario_id": "a", "scenario_name": "Base", "equity_irr": 0.12, "project_irr": 0.09, "avg_dscr": 1.5},
        {"scenario_id": "b", "scenario_name": "Downside", "equity_irr": 0.05, "project_irr": 0.03, "avg_dscr": 1.0},
        {"scenario_id": "c", "scenario_name": "Upside", "equity_irr": 0.18, "project_irr": 0.13, "avg_dscr": 2.0},
    ]

    def test_composer_shape(self):
        result = build_scenario_workflow_ui(self.CARDS, active_scenario_id="a")
        assert set(result.keys()) == {"by_scenario", "compare_links", "state"}
        assert len(result["by_scenario"]) == 3
        assert result["state"]["count"] == 3
        assert result["state"]["state"] == "many"

    def test_by_scenario_keys(self):
        result = build_scenario_workflow_ui(self.CARDS, active_scenario_id="a")
        for sid in ("a", "b", "c"):
            entry = result["by_scenario"][sid]
            assert "label" in entry
            assert "quick_summary" in entry
            assert "is_active" in entry
            assert entry["is_active"] is (sid == "a")

    def test_no_active(self):
        result = build_scenario_workflow_ui(self.CARDS, active_scenario_id="")
        # No active scenario → no is_active True anywhere.
        assert all(e["is_active"] is False for e in result["by_scenario"].values())
        # But labels and quick summary still computed.
        assert result["by_scenario"]["a"]["label"]["kind"] == "base"
        # Compare links empty.
        assert result["compare_links"] == []

    def test_empty_cards(self):
        result = build_scenario_workflow_ui([], active_scenario_id="")
        assert result["by_scenario"] == {}
        assert result["compare_links"] == []
        assert result["state"]["state"] == "empty"

    def test_cards_without_id_skipped(self):
        cards = [{"scenario_name": "NoId"}]
        result = build_scenario_workflow_ui(cards, active_scenario_id="x")
        assert result["by_scenario"] == {}
