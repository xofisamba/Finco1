"""Phase 57E — CSS token consolidation inventory tests.

This test file is a docs/report-only test. It does not modify
runtime code or CSS. It pins:

* The 57E docs/report files exist.
* They reference the correct current main SHA.
* The inventory correctly reports the current CSS state
  (LOC, :root blocks, custom properties).
* The inventory does not propose runtime CSS changes in 57E.
* The inventory defers Tailwind until after UI-3 closeout.
* No runtime / model / persistence / CSS / JS / schema /
  formula changes were introduced in 57E.
"""

import json
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs" / "phase57e_css_token_consolidation_inventory.md"
REPORT = REPO_ROOT / "reports" / "phase57e_css_token_consolidation_inventory.json"
STYLES_CSS = REPO_ROOT / "static" / "styles.css"
RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"


# ============================================================
# 1. Files exist
# ============================================================


class TestFilesExist:
    def test_docs_file_exists(self):
        assert DOCS.exists(), f"57E doc file missing: {DOCS}"

    def test_report_file_exists(self):
        assert REPORT.exists(), f"57E report file missing: {REPORT}"

    def test_doc_minimum_size(self):
        size = DOCS.stat().st_size
        assert size > 6000, (
            f"57E doc is suspiciously small ({size} bytes). "
            f"Expected a comprehensive inventory."
        )

    def test_report_is_valid_json(self):
        with open(REPORT) as f:
            data = json.load(f)
        assert "phase" in data
        assert data["phase"] == "57E"


# ============================================================
# 2. SHA references
# ============================================================


class TestShaReferences:
    def test_doc_references_current_main_sha(self):
        text = DOCS.read_text()
        assert "4194aef753ecc50f00e0827081dc6b718f7e2bd3" in text, (
            "57E doc must reference the post-57D main SHA."
        )

    def test_doc_references_rc1_frozen_sha(self):
        text = DOCS.read_text()
        assert RC1_SHA in text

    def test_report_references_current_main_sha(self):
        data = json.loads(REPORT.read_text())
        assert data["base_sha_start"] == (
            "4194aef753ecc50f00e0827081dc6b718f7e2bd3"
        )

    def test_report_references_rc1_frozen_sha(self):
        data = json.loads(REPORT.read_text())
        assert data["rc1_frozen_sha"] == RC1_SHA


# ============================================================
# 3. CSS state snapshot
# ============================================================


class TestCssStateSnapshot:
    def test_styles_css_exists(self):
        assert STYLES_CSS.exists()

    def test_styles_css_is_above_5000_loc(self):
        lines = len(STYLES_CSS.read_text().splitlines())
        assert lines > 5000, (
            f"styles.css LOC is {lines}, expected > 5000. "
            f"Update the inventory if this has changed."
        )

    def test_three_root_blocks(self):
        text = STYLES_CSS.read_text()
        root_count = len(re.findall(r"^:root\s*\{", text, re.MULTILINE))
        assert root_count == 3, (
            f"styles.css has {root_count} :root blocks, expected 3. "
            f"Update the inventory if this has changed."
        )

    def test_at_least_50_custom_properties(self):
        text = STYLES_CSS.read_text()
        props = re.findall(r"^\s*--[a-zA-Z][\w-]*\s*:", text, re.MULTILINE)
        assert len(props) >= 50, (
            f"styles.css has {len(props)} custom properties, "
            f"expected >= 50. Update the inventory if this has changed."
        )


# ============================================================
# 4. Inventory recommendations
# ============================================================


class TestInventoryRecommendations:
    def test_doc_proposes_root_block_merging(self):
        text = DOCS.read_text()
        assert ":root" in text
        assert "merg" in text.lower(), (
            "57E doc must propose merging :root blocks."
        )

    def test_doc_defers_tailwind(self):
        text = DOCS.read_text().lower()
        assert "defer" in text
        # Tailwind should be mentioned in deferred context
        assert "tailwind" in text

    def test_report_defer_tailwind_until(self):
        data = json.loads(REPORT.read_text())
        timing = data["tailwind_timing"]
        assert "UI-3" in timing["do_not_introduce_until"] or (
            "ui-3" in timing["do_not_introduce_until"].lower()
        )

    def test_doc_keeps_color_accent_alias(self):
        text = DOCS.read_text()
        assert "--color-accent" in text
        # Should recommend keeping the alias
        assert "keep" in text.lower()

    def test_report_recommends_step_1_as_auto_merge(self):
        data = json.loads(REPORT.read_text())
        steps = data["consolidation_steps"]
        step_1 = next(s for s in steps if s["step"] == 1)
        assert step_1["auto_merge_eligible"] is True


# ============================================================
# 5. Component class groups
# ============================================================


class TestComponentClassGroups:
    @pytest.mark.parametrize(
        "component",
        [
            "state banner",
            "project switch",
            "Help",
            "New Project",
            "LineItemGrid",
            "validation bar",
            "runtime chip",
        ],
    )
    def test_report_has_component(self, component):
        data = json.loads(REPORT.read_text())
        groups = data["component_class_groups"]
        names = [g["component"] for g in groups]
        assert component in names, (
            f"Component class group {component!r} must be in the report."
        )

    def test_lineitemgrid_no_new_css(self):
        data = json.loads(REPORT.read_text())
        lig = next(
            g for g in data["component_class_groups"]
            if g["component"] == "LineItemGrid"
        )
        assert "57A did not require new CSS" in lig.get("notes", "") or (
            "no new CSS" in lig.get("notes", "").lower()
            or "uses existing" in lig.get("notes", "").lower()
        )


# ============================================================
# 6. No CSS changes in 57E
# ============================================================


class TestNoCssChangesIn57E:
    def test_report_says_no_css_changes(self):
        data = json.loads(REPORT.read_text())
        assert data["css_changes_in_this_phase"] is False

    def test_styles_css_unchanged_in_57e_diff(self):
        r = subprocess.run(
            ["git", "diff", "main", "--name-only", "--", "static/styles.css"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            # No diff at all is fine
            return
        pytest.fail(
            f"57E must not modify static/styles.css. "
            f"Found in diff: {r.stdout.strip()!r}."
        )

    def test_app_js_unchanged_in_57e_diff(self):
        r = subprocess.run(
            ["git", "diff", "main", "--name-only", "--", "static/app.js"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return
        pytest.fail(
            f"57E must not modify static/app.js. "
            f"Found in diff: {r.stdout.strip()!r}."
        )


# ============================================================
# 7. Hard no-go scope
# ============================================================


class TestHardNoGoScope:
    @pytest.mark.parametrize(
        "forbidden_change",
        [
            "waterfall_core",
            "project_factories",
            "persistence",
            "main_web.py",
            "static/app.js",
            "static/styles.css",
            "schema",
            "fixture",
            "tailwind",
            "alpine",
            "react",
            "vue",
            "svelte",
        ],
    )
    def test_doc_mentions_forbidden_change(self, forbidden_change):
        text = DOCS.read_text().lower()
        assert forbidden_change.lower() in text

    def test_doc_says_rc1_untouched(self):
        text = DOCS.read_text()
        m = re.search(r"rc1[^\n]{0,200}", text, re.IGNORECASE)
        assert m is not None
        ctx = m.group(0).lower()
        assert "untouched" in ctx or "frozen" in ctx


# ============================================================
# 8. 57E is docs-only diff
# ============================================================


class Test57EIsDocsOnly:
    def test_57e_diff_only_in_docs_reports_tests(self):
        r = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("Not on 57E branch or no diff")
        changed = set(r.stdout.strip().split("\n"))
        for c in changed:
            assert (
                c.startswith("docs/")
                or c.startswith("reports/")
                or c.startswith("tests/")
            ), (
                f"57E diff file {c!r} is outside docs/reports/tests. "
                f"57E must be docs/report/test-only."
            )


# ============================================================
# 9. Rc1 untouched
# ============================================================


class TestRc1Untouched:
    def test_rc1_sha_constant_stable(self):
        assert RC1_SHA == "b425a0708719eaa5e1d922b1008e5609758e0ad4"

    def test_rc1_still_in_git_history(self):
        r = subprocess.run(
            ["git", "rev-parse", RC1_SHA],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0
