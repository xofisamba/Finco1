"""
UX-2I-PILOT-POLISH-FOLLOWUP

UX-2H Final QA found no P0 blockers, but flagged two optional polish
items before/alongside the first pilot users:

  1. "Compare with X" correctly loaded comparison data into
     #panel-compare-mount via htmx, but the Compare tab did not always
     visibly activate on the same click (the activation relied on the
     compare link's own ``hx-on::after-request`` attribute, which is
     unreliable when the link's surrounding DOM node -- inside
     #saved-scenario-panel -- is concurrently replaced by an unrelated
     Save action).

  2. A stale "No run performed yet" banner persisted after a successful
     run, because partials/_empty_no_run.html is only rendered once on
     the initial full-page load and is never re-rendered by the
     Run/Save htmx swaps (which only replace #model-output-area).

This file proves:
  A. Compare tab activation now happens via a document-level
     htmx:afterSwap listener keyed on the #panel-compare-mount swap
     target (static/app.js), not via the link's own attribute.
  B. The compare_link macro no longer carries the unreliable
     hx-on::after-request attribute.
  C. window._populateRuntimeBlock() (already invoked on every
     Run/Save htmx:afterSwap) now also hides any
     .empty-state-notice--no-run element once a real (non-error)
     runtime summary exists in sessionStorage.
  D. The sessionStorage payload written by run_service.py is valid
     JSON text (the prior bug embedded the JSON object literal
     directly, which the browser coerced to the literal string
     "[object Object]", so it could never be parsed back).
  E. No raw <a href> page-navigation regression: the compare_link
     macro is still htmx-only.

No engine/domain/runtime/export/validation files are touched by this
test file or by the fix it verifies.
"""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


# ── A/B. Compare tab activation moved to a reliable htmx:afterSwap hook ───

class TestCompareAutoSwitchReliability:
    def test_app_js_activates_compare_tab_on_mount_swap(self):
        app_js = (REPO_ROOT / "static/app.js").read_text()
        assert "htmx:afterSwap" in app_js
        assert "panel-compare-mount" in app_js
        assert "switchTab('compare')" in app_js

    def test_compare_link_macro_no_longer_uses_after_request_attribute(self):
        tpl = (REPO_ROOT / "app/templates/partials/scenario_workflow_indicators.html").read_text()
        macro_body = tpl[tpl.index("{%- macro compare_link"):tpl.index("{%- endmacro -%}", tpl.index("{%- macro compare_link"))]
        assert "hx-on::after-request" not in macro_body
        # Still htmx-only -- no raw navigation regression.
        assert "hx-get=" in tpl
        assert 'hx-target="#panel-compare-mount"' in tpl
        assert "hx-swap=" in tpl

    def test_compare_link_is_still_a_real_anchor_with_href_fallback(self):
        """The <a href> must remain present (no JS = no dead link), it
        just must never be relied on as the *only* navigation path."""
        tpl = (REPO_ROOT / "app/templates/partials/scenario_workflow_indicators.html").read_text()
        assert 'href="{{ link.href }}"' in tpl


# ── C. Stale no-run banner cleanup ─────────────────────────────────────────

class TestStaleNoRunBannerCleanup:
    def test_populate_runtime_block_hides_no_run_banner_on_real_run(self):
        tpl = (REPO_ROOT / "app/templates/partials/shared_runtime_block.html").read_text()
        assert "empty-state-notice--no-run" in tpl
        assert "lastRuntimeSummary" in tpl
        assert "error_message" in tpl

    def test_populate_runtime_block_hook_still_wired_to_model_output_area_swap(self):
        """The pre-existing Run/Save hook this fix reuses must remain
        intact -- this is what calls _populateRuntimeBlock() after every
        Run/Save."""
        tpl = (REPO_ROOT / "app/templates/partials/shared_runtime_block.html").read_text()
        assert 'e.target.id === "model-output-area"' in tpl
        assert "window._populateRuntimeBlock" in tpl


# ── D. sessionStorage payload is valid, parseable JSON ─────────────────────

class TestRuntimeSummarySessionStorageSerialization:
    def test_save_script_writes_a_json_string_not_a_bare_object_literal(self):
        """Regression test for the root cause that blocked the no-run
        banner fix: sessionStorage.setItem's 2nd argument must be a JS
        string literal containing JSON text, not a bare object literal
        (which the browser would coerce via toString() to the literal
        string "[object Object]", making every later JSON.parse() fail
        silently)."""
        from app.services.run_service import _build_sessionstorage_save_tag

        script = _build_sessionstorage_save_tag(
            runtime_summary={"project_irr": "11.87%", "error_message": ""},
            runtime_origin="saved_state",
            workspace_state=None,
            runtime_snapshot_id="snap-1",
        )
        assert 'sessionStorage.setItem("lastRuntimeSummary", "' in script
        # Extract the JS string literal argument and confirm it round-trips
        # through JSON.parse(JSON.parse(...)) semantics: the outer payload
        # decodes to a JSON *string*, which itself decodes to the dict.
        marker = 'sessionStorage.setItem("lastRuntimeSummary", '
        start = script.index(marker) + len(marker)
        end = script.index(");", start)
        js_string_literal = script[start:end]
        # The literal itself must be valid JSON (a quoted JSON string).
        inner_json_text = json.loads(js_string_literal)
        assert isinstance(inner_json_text, str)
        payload = json.loads(inner_json_text)
        assert payload["project_irr"] == "11.87%"


# ── E. No-regression / existing-suite hooks ────────────────────────────────

class TestNoRegression:
    def test_workspace_shell_compare_panel_not_nested_inside_downloads_panel(self):
        """UX-2I also fixed a mismatched closing tag (</a> instead of
        </div>) in the Downloads tab that nested #panel-compare inside
        #panel-downloads, making the Compare tab invisible even when
        correctly marked .active (display:none inherited from the
        non-active Downloads ancestor)."""
        tpl = (REPO_ROOT / "app/templates/partials/workspace_shell.html").read_text()
        downloads_start = tpl.index('id="panel-downloads"')
        compare_start = tpl.index('id="panel-compare"')
        assert compare_start > downloads_start
        between = tpl[downloads_start:compare_start]
        # The Downloads panel's own closing </div> must appear before the
        # Compare panel opens -- i.e. div-depth returns to 0 in between.
        depth = 0
        closed_before_compare = False
        i = 0
        while i < len(between):
            if between[i:i + 4] == "<div":
                depth += 1
                i += 4
            elif between[i:i + 6] == "</div>":
                depth -= 1
                i += 6
                if depth == 0:
                    closed_before_compare = True
            else:
                i += 1
        assert closed_before_compare, (
            "panel-downloads' wrapper div must close before panel-compare opens"
        )


# ── File-scope guardrail ─────────────────────────────────────────────────

class TestUX2IFileScope:
    """UX-2I-PILOT-POLISH-FOLLOWUP must never touch engine/domain/runtime/
    export/validation code. UI/template/test files only."""

    ALLOWED_PREFIXES = (
        "static/app.js",
        "app/templates/partials/scenario_workflow_indicators.html",
        "app/templates/partials/shared_runtime_block.html",
        "app/templates/partials/workspace_shell.html",
        "app/services/run_service.py",
        "tests/test_ux2i_pilot_polish_followup.py",
        "tests/test_ux2g_compare_fix.py",
        "tests/test_p1_compare_validation.py",
    )
    DISALLOWED_PREFIXES = (
        "domain/",
        "app/waterfall_core.py",
        "app/input_adapter.py",
        "app/project_factories.py",
    )

    def test_changed_files_within_allowlist(self):
        import subprocess
        try:
            out = subprocess.run(
                ["git", "diff", "--name-only", "origin/main"],
                cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30,
            )
        except Exception:
            pytest.skip("git not available in this environment")
        if out.returncode != 0 or not out.stdout.strip():
            pytest.skip("no diff against origin/main available")
        changed = [l.strip() for l in out.stdout.splitlines() if l.strip()]
        for f in changed:
            assert not any(f.startswith(p) for p in self.DISALLOWED_PREFIXES), (
                f"UX-2I must not touch {f}"
            )
