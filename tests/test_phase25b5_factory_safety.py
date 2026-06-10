"""Phase 25B-5 — Factory safety, hard constraints, no-regression.

Pins that the scenario workflow polish work does not:
- mutate factory projects
- touch model formulas
- break save/load / compare / multi-compare / export paths
- introduce Tailwind / Alpine / inline <script>
- add flag flips or construction-engine promotion
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.ui.scenario_workflow import (
    build_compare_shortcut_links,
    build_scenario_workflow_ui,
    classify_scenario_label,
    quick_summary_card,
    workflow_state,
)


# ─────────────────────────────────────────────────────────────────────────
# Test 1: factory projects get the same workflow UI as user projects
# ─────────────────────────────────────────────────────────────────────────

class TestFactoryProjectsUnaffected:
    """Factory projects (TUHO / Oborovo) can also have scenarios (after
    Save As). The workflow UI must not crash and must not inject any
    autosave / mutation logic into those scenarios either."""

    def test_factory_cards_classify_normally(self):
        # After Save As, factory-saved scenarios are user-owned and
        # workflow UI is shown. The helper is agnostic to origin.
        cards = [
            {"scenario_id": "a", "scenario_name": "Base", "equity_irr": 0.10},
        ]
        result = build_scenario_workflow_ui(cards, active_scenario_id="a")
        assert result["by_scenario"]["a"]["label"]["kind"] == "base"

    def test_factory_does_not_inject_dirty_or_unsaved(self):
        # The workflow UI is read-only — it must never surface a
        # "Saved/Unsaved" badge (that's Phase 25B-4's job).
        cards = [
            {"scenario_id": "a", "scenario_name": "Base"},
            {"scenario_id": "b", "scenario_name": "Downside"},
        ]
        result = build_scenario_workflow_ui(cards, active_scenario_id="a")
        for entry in result["by_scenario"].values():
            assert "dirty" not in entry["label"]
            assert "saved" not in entry["label"]["kind"]
            assert "unsaved" not in entry["label"]["kind"]


# ─────────────────────────────────────────────────────────────────────────
# Test 2: hard constraints
# ─────────────────────────────────────────────────────────────────────────

class TestHardConstraints:
    def test_helper_does_not_import_db(self):
        text = Path("app/ui/scenario_workflow.py").read_text()
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
                f"app/ui/scenario_workflow.py must not import {forbidden}"
            )

    def test_helper_has_no_io(self):
        text = Path("app/ui/scenario_workflow.py").read_text()
        for forbidden in ["open(", ".write(", "json.load", "json.dump"]:
            assert forbidden not in text, (
                f"app/ui/scenario_workflow.py must not perform I/O ({forbidden})"
            )

    def test_helper_has_no_time_calls(self):
        text = Path("app/ui/scenario_workflow.py").read_text()
        for forbidden in ["datetime.now", "time.time", "datetime.utcnow"]:
            assert forbidden not in text

    def test_helper_has_no_model_or_tax_or_debt(self):
        text = Path("app/ui/scenario_workflow.py").read_text()
        for forbidden in [
            "waterfall", "tax_engine", "depreciation", "construction",
            "senior_idc", "debt_sculpt", "rpar",
        ]:
            assert forbidden.lower() not in text.lower(), (
                f"app/ui/scenario_workflow.py must not reference {forbidden}"
            )

    def test_helper_has_no_compare_service(self):
        text = Path("app/ui/scenario_workflow.py").read_text()
        for forbidden in ["compare_service", "base_vs_active_compare", "multi_compare"]:
            assert forbidden not in text

    def test_helper_does_not_mutate_input(self):
        text = Path("app/ui/scenario_workflow.py").read_text()
        for forbidden in ["cards.append", "cards.update", "cards.pop", ".sort()"]:
            assert forbidden not in text, (
                f"app/ui/scenario_workflow.py must not mutate input: {forbidden}"
            )

    def test_partial_uses_no_inline_script(self):
        text = Path("app/templates/partials/scenario_workflow_indicators.html").read_text()
        # Strip Jinja comments and HTML comments to avoid matching
        # legitimate references like "No inline <script>".
        import re as _re
        stripped = _re.sub(r"\{#.*?#\}", "", text, flags=_re.DOTALL)
        stripped = _re.sub(r"<!--.*?-->", "", stripped, flags=_re.DOTALL)
        assert "<script" not in stripped
        assert "onclick=" not in stripped
        assert "onchange=" not in stripped
        assert "onload=" not in stripped

    def test_no_tailwind_or_alpine(self):
        for fname in [
            "app/ui/scenario_workflow.py",
            "app/templates/partials/scenario_workflow_indicators.html",
        ]:
            text = Path(fname).read_text()
            for forbidden in ["tailwind", "alpine", "x-data", "x-show", "x-bind"]:
                pattern = re.compile(
                    rf"{re.escape(forbidden)}[\"'`<>=:\s]",
                    re.IGNORECASE,
                )
                assert not pattern.search(text), (
                    f"{fname} must not use {forbidden}"
                )

    def test_css_did_not_modify_root_count(self):
        text = Path("static/styles.css").read_text()
        # Phase 24G-2 invariant: 3 :root blocks.
        assert len(re.findall(r"^:root", text, re.MULTILINE)) == 3

    def test_no_important_on_sw_rules(self):
        text = Path("static/styles.css").read_text()
        # Find lines that are properties of .sw-* rules and assert
        # no !important.
        in_sw = False
        for line in text.splitlines():
            stripped = line.strip()
            if re.match(r"^\.sw-", stripped) and "{" in stripped:
                in_sw = True
                continue
            if in_sw:
                if "}" in stripped and not stripped.startswith("."):
                    in_sw = False
                    continue
                if in_sw and "{" not in stripped and stripped:
                    assert "!important" not in stripped, (
                        f".sw-* CSS must not use !important: {line}"
                    )

    def test_no_construction_flag_flips(self):
        text = Path("app/ui/scenario_workflow.py").read_text()
        assert "use_construction_schedule_engine" not in text

    def test_no_autosave_in_partial(self):
        text = Path("app/templates/partials/scenario_workflow_indicators.html").read_text()
        for forbidden in ["<form", "submit(", "fetch("]:
            assert forbidden not in text


# ─────────────────────────────────────────────────────────────────────────
# Test 3: CSS completeness — the .svh-card--active rule exists
# ─────────────────────────────────────────────────────────────────────────

class TestCSSCompleteness:
    """The .svh-card--active class existed in the template but had NO
    CSS rules before Phase 25B-5. Verify the rules now exist."""

    def test_svh_card_active_rule_exists(self):
        text = Path("static/styles.css").read_text()
        # Look for the rule with a non-empty body.
        m = re.search(r"\.svh-card--active\s*\{([^}]*)\}", text)
        assert m is not None, "Missing .svh-card--active CSS rule"
        body = m.group(1)
        # Must define border-color (or similar highlight).
        assert "border-color" in body or "background" in body or "outline" in body, (
            f".svh-card--active body is empty: {body!r}"
        )

    def test_svh_card_base_rule_exists(self):
        text = Path("static/styles.css").read_text()
        m = re.search(r"\.svh-card\s*\{([^}]*)\}", text)
        assert m is not None, "Missing .svh-card base CSS rule"

    def test_sw_label_class_exists(self):
        text = Path("static/styles.css").read_text()
        for cls in ["sw-label", "sw-label--base", "sw-label--downside", "sw-label--upside", "sw-label--custom"]:
            m = re.search(rf"\.{cls}\s*\{{", text)
            assert m is not None, f"Missing .{cls} CSS rule"

    def test_sw_quick_summary_classes_exist(self):
        text = Path("static/styles.css").read_text()
        for cls in ["sw-quick-summary", "sw-quick-summary__row", "sw-quick-summary__label", "sw-quick-summary__value"]:
            m = re.search(rf"\.{cls}\s*\{{", text)
            assert m is not None, f"Missing .{cls} CSS rule"

    def test_sw_compare_link_classes_exist(self):
        text = Path("static/styles.css").read_text()
        for cls in ["sw-compare-link", "sw-compare-link__arrow", "sw-compare-link__label"]:
            m = re.search(rf"\.{cls}\s*\{{", text)
            assert m is not None, f"Missing .{cls} CSS rule"

    def test_sw_empty_state_classes_exist(self):
        text = Path("static/styles.css").read_text()
        for cls in ["sw-empty-notice", "sw-empty--empty", "sw-empty--one", "sw-empty--two", "sw-empty--many"]:
            m = re.search(rf"\.{cls}\s*\{{", text)
            assert m is not None, f"Missing .{cls} CSS rule"

    def test_sw_state_color_classes_exist(self):
        text = Path("static/styles.css").read_text()
        for cls in ["sw-state--good", "sw-state--ok", "sw-state--bad", "sw-state--n_a"]:
            m = re.search(rf"\.{cls}\s*\{{", text)
            assert m is not None, f"Missing .{cls} CSS rule"


# ─────────────────────────────────────────────────────────────────────────
# Test 4: payload shape stability
# ─────────────────────────────────────────────────────────────────────────

class TestPayloadShape:
    def test_top_level_keys(self):
        result = build_scenario_workflow_ui([], active_scenario_id="")
        assert set(result.keys()) == {"by_scenario", "compare_links", "state"}

    def test_by_scenario_entry_keys(self):
        cards = [{"scenario_id": "a", "scenario_name": "Base"}]
        result = build_scenario_workflow_ui(cards, active_scenario_id="a")
        entry = result["by_scenario"]["a"]
        assert set(entry.keys()) == {"label", "quick_summary", "is_active"}

    def test_compare_link_keys(self):
        cards = [
            {"scenario_id": "a", "scenario_name": "Base"},
            {"scenario_id": "b", "scenario_name": "Downside"},
        ]
        result = build_scenario_workflow_ui(cards, active_scenario_id="a")
        link = result["compare_links"][0]
        assert set(link.keys()) == {
            "href", "label", "kind", "css_class", "right_scenario_id", "right_scenario_name",
        }

    def test_state_keys(self):
        result = build_scenario_workflow_ui([], active_scenario_id="")
        assert set(result["state"].keys()) == {"count", "state", "message", "css_class"}
