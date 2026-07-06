"""UI-3 — Excel-style Worksheet Navigation — smoke / governance tests.

Verifies the additive introduction of the new top-level worksheet
navigation strip (replacing the UI-2 reserve placeholder):

  - static/sheet-tabs.css exists and declares the .fo-sheets /
    .fo-sheet class family
  - app/templates/partials/_sheet_tabs.html exists
  - app/templates/partials/_app_chrome.html mounts _sheet_tabs.html
    (replacing the reserve placeholder)
  - app/templates/base.html loads sheet-tabs.css AFTER chrome.css
  - All 14 worksheet tabs are present in the partial, namespaced
    under .fo-sheet (no leakage onto legacy .fc-, .ps-, .scm-,
    .top-header, .dashboard-* classes)
  - sheet-tabs.css consumes only --fo-* design tokens; no raw hex,
    rgba, px box-shadows
  - DOM-switch tabs (Modeling) wire through the existing
    window.switchTab() — no new JS file, no new behaviour
  - URL tabs (Analysis / Delivery / Storage) point to EXISTING
    production routes — no new route is added
  - The strip reuses dirty state from existing context, no new
    domain / persistence / engine change
  - Keyboard support: Ctrl/Cmd + 1..8 routes through switchTab for
    Modeling tabs; Ctrl/Cmd + 9..0 navigates to URL tabs
  - No engine / persistence / route / calculation / report / styles.css
    / template-rename change
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Repo paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
TOKENS_CSS = REPO_ROOT / "static" / "tokens.css"
CHROME_CSS = REPO_ROOT / "static" / "chrome.css"
SHEET_TABS_CSS = REPO_ROOT / "static" / "sheet-tabs.css"
BASE_HTML = REPO_ROOT / "app" / "templates" / "base.html"
APP_CHROME_HTML = (
    REPO_ROOT / "app" / "templates" / "partials" / "_app_chrome.html"
)
SHEET_TABS_HTML = (
    REPO_ROOT / "app" / "templates" / "partials" / "_sheet_tabs.html"
)


# ---------------------------------------------------------------------------
# 1. Files exist
# ---------------------------------------------------------------------------

class TestFilesExist:
    """All UI-3 deliverables must exist on disk."""

    @pytest.mark.parametrize("path", [
        SHEET_TABS_CSS,
        SHEET_TABS_HTML,
    ])
    def test_deliverable_file_present(self, path):
        assert path.is_file(), (
            f"UI-3 deliverable missing: {path}"
        )


class TestSheetTabsCssSanity:
    """sheet-tabs.css must be a non-trivial, balanced CSS sheet."""

    def test_sheet_tabs_css_has_header_comment(self):
        text = SHEET_TABS_CSS.read_text(encoding="utf-8")
        assert "WORKSHEET" in text, (
            "sheet-tabs.css must start with the Finco One worksheet "
            "navigation header."
        )

    def test_sheet_tabs_css_balanced_braces(self):
        text = SHEET_TABS_CSS.read_text(encoding="utf-8")
        assert text.count("{") == text.count("}"), (
            "sheet-tabs.css must have balanced braces."
        )

    def test_sheet_tabs_css_substantive_size(self):
        assert SHEET_TABS_CSS.stat().st_size > 3000, (
            f"sheet-tabs.css should be substantive; got "
            f"{SHEET_TABS_CSS.stat().st_size} bytes."
        )


# ---------------------------------------------------------------------------
# 2. .fo-* class namespacing
# ---------------------------------------------------------------------------

REQUIRED_FO_CLASSES = [
    "fo-sheets",
    "fo-sheets__divider",
    "fo-sheets__spacer",
    "fo-sheet",
    "fo-sheet--active",
    "fo-sheet--dirty",
    "fo-sheet__dot",
    "fo-sheet__dot--clean",
    "fo-sheet__dot--edited",
    "fo-sheet__dot--warn",
    "fo-sheet__dot--error",
    "fo-sheet__dot--running",
    "fo-sheet__dot--complete",
    "fo-sheet__dot--none",
    "fo-sheet__label",
    "fo-sheet__kbd",
]


class TestFoClassNamespacing:
    """UI-3 worksheet classes are namespaced strictly under `fo-`."""

    @pytest.mark.parametrize("cls", REQUIRED_FO_CLASSES)
    def test_fo_class_appears_in_sheet_tabs_css(self, cls):
        text = SHEET_TABS_CSS.read_text(encoding="utf-8")
        pattern = re.compile(rf"\.{re.escape(cls)}\b")
        assert pattern.search(text), (
            f"Required worksheet class .{cls} not declared in "
            f"sheet-tabs.css."
        )

    @pytest.mark.parametrize("cls", REQUIRED_FO_CLASSES)
    def test_fo_class_does_not_leak_into_styles_css(self, cls):
        legacy_text = (REPO_ROOT / "static" / "styles.css").read_text(
            encoding="utf-8"
        )
        legacy_pattern = re.compile(rf"\.{re.escape(cls)}\b")
        assert not legacy_pattern.search(legacy_text), (
            f"Worksheet class .{cls} leaked into static/styles.css; "
            f"sheet-tabs.css owns its own stylesheet."
        )


# ---------------------------------------------------------------------------
# 3. sheet-tabs.css consumes ONLY --fo-* tokens
# ---------------------------------------------------------------------------

class TestSheetTabsCssOnlyConsumesFoTokens:
    """sheet-tabs.css must consume only --fo-* tokens."""

    def test_no_raw_hex_colours(self):
        text = SHEET_TABS_CSS.read_text(encoding="utf-8")
        text_no_comments = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        offenders = []
        for line_no, raw in enumerate(text_no_comments.splitlines(), start=1):
            if re.search(r"#[0-9a-fA-F]{3,8}\b", raw):
                offenders.append((line_no, raw))
        assert not offenders, (
            "sheet-tabs.css must not declare raw hex colours; "
            "use --fo-* tokens instead. Offends:\n  " +
            "\n  ".join(f"L{n}: {l}" for n, l in offenders)
        )

    def test_no_raw_rgb_colours(self):
        text = SHEET_TABS_CSS.read_text(encoding="utf-8")
        text_no_comments = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        offenders = []
        for line_no, raw in enumerate(text_no_comments.splitlines(), start=1):
            if re.search(r"\brgba?\s*\(", raw):
                offenders.append((line_no, raw))
        assert not offenders, (
            "sheet-tabs.css must not declare raw rgba() colours; "
            "use --fo-* tokens. Offends:\n  " +
            "\n  ".join(f"L{n}: {l}" for n, l in offenders)
        )

    def test_uses_fo_tokens(self):
        text = SHEET_TABS_CSS.read_text(encoding="utf-8")
        for token in [
            "--fo-paper",
            "--fo-surface",
            "--fo-ink",
            "--fo-ink-soft",
            "--fo-line",
            "--fo-brand-600",
            "--fo-rag-green",
            "--fo-rag-amber",
            "--fo-rag-red",
            "--fo-font-ui",
            "--fo-font-mono",
            "--fo-text-md",
            "--fo-chrome-tabs-h",
            "--fo-t-fast",
        ]:
            assert token in text, (
                f"sheet-tabs.css must consume {token} from tokens.css."
            )

    def test_no_legacy_palette_alias(self):
        text = SHEET_TABS_CSS.read_text(encoding="utf-8")
        for legacy in ["--sidebar-bg", "--primary", "--surface",
                        "--border", "--text-secondary"]:
            pattern = re.compile(rf"var\(\s*{re.escape(legacy)}\b")
            assert not pattern.search(text), (
                f"sheet-tabs.css must not reference legacy token "
                f"{legacy}."
            )


# ---------------------------------------------------------------------------
# 4. base.html wiring — sheet-tabs.css link + partial include + ordering
# ---------------------------------------------------------------------------

class TestBaseHtmlWiring:
    """base.html loads sheet-tabs.css after chrome.css; chrome partial
    mounts _sheet_tabs.html instead of the UI-2 reserve placeholder."""

    def test_sheet_tabs_css_linked(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert "/static/sheet-tabs.css" in text, (
            "base.html must link static/sheet-tabs.css as a stylesheet."
        )

    def test_load_order_tokens_styles_chrome_sheets(self):
        # tokens.css → styles.css → chrome.css → sheet-tabs.css
        text = BASE_HTML.read_text(encoding="utf-8")
        t = text.find("/static/tokens.css")
        s = text.find("/static/styles.css")
        c = text.find("/static/chrome.css")
        st = text.find("/static/sheet-tabs.css")
        assert t > 0 and s > 0 and c > 0 and st > 0
        assert t < s < c < st, (
            "Load order MUST be tokens → styles → chrome → sheet-tabs."
        )


class TestAppChromeMountsSheets:
    """_app_chrome.html mounts _sheet_tabs.html, replacing the UI-2
    reserve placeholder."""

    def test_app_chrome_includes_sheet_tabs(self):
        text = APP_CHROME_HTML.read_text(encoding="utf-8")
        assert "_sheet_tabs.html" in text, (
            "_app_chrome.html must include _sheet_tabs.html."
        )

    def test_app_chrome_no_longer_renders_reserve_placeholder(self):
        # The UI-2 placeholder text is gone — _sheet_tabs.html now
        # replaces it. The class .fo-sheet-tab-reserve may still be
        # declared in chrome.css (it's just CSS), but the partial
        # element is no longer mounted.
        text = APP_CHROME_HTML.read_text(encoding="utf-8")
        assert "fo-sheet-tab-reserve__placeholder" not in text, (
            "UI-2 reserve placeholder element must be removed from "
            "_app_chrome.html once UI-3 mounts the real sheet strip."
        )

    def test_legacy_top_header_still_present(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        idx = 0
        found = False
        while True:
            idx = text.find('<header class="top-header">', idx)
            if idx < 0:
                break
            before = text[:idx]
            last_open = before.rfind('{#')
            last_close = before.rfind('#}')
            if last_open > last_close:
                idx += 1
                continue
            found = True
            break
        assert found, (
            "Legacy <header class=\"top-header\"> must remain in "
            "base.html — UI-3 is additive only."
        )


# ---------------------------------------------------------------------------
# 5. Sheet strip contents — every sheet declared
# ---------------------------------------------------------------------------

# The 14 worksheet tabs locked by the UI-3 brief. Order matters
# because the macro emits them sequentially and the sheet strip is
# visually a single horizontal row.
EXPECTED_TABS = [
    ("overview",    "Overview",   "modeling", "/"),
    ("inputs",      "Inputs",     "modeling", "/"),
    ("revenue",     "Revenue",    "modeling", "/"),
    ("opex",        "OPEX",       "modeling", "/"),
    ("capex",       "CAPEX",      "modeling", "/"),
    ("senior-debt", "Debt",       "modeling", "/"),
    ("tax",         "Tax",        "modeling", "/"),
    ("pl",          "Financials", "modeling", "/"),
    ("scenarios",   "Scenarios",  "analysis", "/scenarios"),
    ("compare",     "Compare",    "analysis", "/scenarios/compare"),
    ("sensitivity", "Sensitivity","analysis", "/scenarios/sensitivity"),
    ("lender",      "Lender",     "delivery", "/scenarios/lender-case"),
    ("reports",     "Reports",    "delivery", "/scenarios/exec-summary"),
    ("bess",        "BESS",       "storage",  "/scenarios/bess-revenue"),
    ("settings",    "Settings",   "storage",  "/help"),
]


class TestSheetTabsPartial:
    """_sheet_tabs.html must declare every locked tab from the brief."""

    @pytest.mark.parametrize(
        ("tab_id", "label", "group", "_href"),
        EXPECTED_TABS,
        ids=[f"{t[0]}" for t in EXPECTED_TABS],
    )
    def test_tab_declared(self, tab_id, label, group, _href):
        text = SHEET_TABS_HTML.read_text(encoding="utf-8")
        # The data-fo-sheet-id attribute carries the tab id, the
        # data-fo-sheet-group the group, and the visible label is
        # wrapped in .fo-sheet__label.
        assert f'data-fo-sheet-id="{tab_id}"' in text, (
            f"Tab id {tab_id!r} not declared in _sheet_tabs.html."
        )
        assert f'data-fo-sheet-group="{group}"' in text, (
            f"Group {group!r} not declared for tab {tab_id!r}."
        )
        assert label in text, (
            f"Label {label!r} not visible in _sheet_tabs.html."
        )

    def test_dom_switch_tabs_target_existing_panels(self):
        # Modeling tabs must call switchTab (data-fo-sheet-kind="dom")
        # — they must NOT navigate to URLs.
        text = SHEET_TABS_HTML.read_text(encoding="utf-8")
        for tab_id in ("overview", "inputs", "revenue", "opex",
                        "capex", "senior-debt", "tax", "pl"):
            # Each Modeling tab carries a data-fo-sheet-kind="dom" and
            # is inside a <button>, not an <a href>.
            pat = re.compile(
                rf'data-fo-sheet-id="{tab_id}".*?data-fo-sheet-kind="dom"',
                re.DOTALL,
            )
            assert pat.search(text), (
                f"Modeling tab {tab_id} must be DOM-switch (button + "
                f"kind=dom)."
            )

    def test_url_tabs_link_to_existing_routes(self):
        # URL tabs must point to EXISTING routes in main_web.py.
        # The HTML attribute order on each <a> element is:
        #   <a href="..." class="..." data-fo-sheet-id="..." ...>
        # so we assert the two attributes co-exist on the SAME <a>
        # element (greedy match across a single tag).
        text = SHEET_TABS_HTML.read_text(encoding="utf-8")
        for tab_id, _label, _group, href in EXPECTED_TABS:
            if tab_id in ("overview", "inputs", "revenue", "opex",
                          "capex", "senior-debt", "tax", "pl"):
                continue
            # Find the <a ...> opening tag that carries data-fo-sheet-id
            # for this tab.
            pat = re.compile(
                rf'<a[^>]*data-fo-sheet-id="{re.escape(tab_id)}"[^>]*>',
                re.DOTALL,
            )
            m = pat.search(text)
            assert m is not None, (
                f"URL tab {tab_id!r} not found as <a data-fo-sheet-id>."
            )
            tag_text = m.group()
            assert f'href="{href}"' in tag_text, (
                f"URL tab {tab_id} <a> must link to existing route "
                f"{href!r}; got tag {tag_text!r}."
            )

    def test_status_dots_present_on_every_tab(self):
        # Each tab must include a .fo-sheet__dot so the status channel
        # is wired even when no specific status is reported.
        text = SHEET_TABS_HTML.read_text(encoding="utf-8")
        # Count the number of <button ...fo-sheet...> and <a ...fo-sheet...>
        # tab emitters.
        n_buttons = len(re.findall(
            r'<button[^>]+class="[^"]*fo-sheet\b', text
        ))
        n_anchors = len(re.findall(
            r'<a[^>]+class="[^"]*fo-sheet\b', text
        ))
        n_dots = text.count('fo-sheet__dot')
        # At least one dot per tab emitter.
        assert n_dots >= n_buttons + n_anchors, (
            f"Every worksheet tab must carry a .fo-sheet__dot; got "
            f"{n_dots} dots for {n_buttons + n_anchors} tabs."
        )

    def test_dirty_state_visual_treatment(self):
        # When inputs are dirty, the strip must apply the
        # .fo-sheet--dirty visual treatment — no modal, no banner,
        # no popup. Per brief PART E.
        text = SHEET_TABS_HTML.read_text(encoding="utf-8")
        assert "fo-sheet--dirty" in text, (
            "Sheet strip must apply .fo-sheet--dirty class on dirty "
            "inputs (no modal, no banner)."
        )


# ---------------------------------------------------------------------------
# 6. Keyboard plumbing — Ctrl/Cmd + 1..8 routes through switchTab
# ---------------------------------------------------------------------------

class TestKeyboardShortcuts:
    """Keyboard plumbing must NOT introduce a new JS file; it must be
    embedded inside _sheet_tabs.html and route through window.switchTab."""

    def test_keydown_handler_is_embedded(self):
        text = SHEET_TABS_HTML.read_text(encoding="utf-8")
        assert "keydown" in text, (
            "_sheet_tabs.html must embed a keydown handler."
        )
        # Must use addEventListener — no inline onkeydown.
        assert "onkeydown" not in text, (
            "Keyboard handler must be added via addEventListener, "
            "not via inline onkeydown."
        )

    def test_ctrl_meta_modifier_required(self):
        text = SHEET_TABS_HTML.read_text(encoding="utf-8")
        # e.ctrlKey || e.metaKey is the canonical phrasing.
        assert "ctrlKey" in text and "metaKey" in text, (
            "Keyboard handler must require Ctrl or Cmd."
        )

    def test_dom_tabs_route_through_switch_tab(self):
        text = SHEET_TABS_HTML.read_text(encoding="utf-8")
        assert "window.switchTab" in text, (
            "DOM-switch tabs must route through window.switchTab()."
        )
        assert "'1'" in text and "'8'" in text, (
            "Keyboard handler must bind Ctrl+1..Ctrl+8 for Modeling."
        )

    def test_url_tabs_navigate_via_location_href(self):
        text = SHEET_TABS_HTML.read_text(encoding="utf-8")
        assert "window.location.href" in text, (
            "URL tabs must navigate via window.location.href."
        )

    def test_no_new_static_js_file_created(self, repo_diff):
        # UI-3 must not add a new JS file under static/. The CSS file
        # static/sheet-tabs.css is allowed (and required) — it's a new
        # stylesheet, not a new behaviour file.
        for path in repo_diff.untracked_paths:
            if not path.startswith("static/"):
                continue
            assert path.endswith(".css"), (
                f"UI-3 must not create new files under static/ other "
                f"than .css; found {path!r}."
            )


# ---------------------------------------------------------------------------
# 7. Forbidden paths — UI-3 is additive only
# ---------------------------------------------------------------------------

FORBIDDEN_PATHS = [
    # engine / factory / domain
    "app/waterfall_core.py",
    "app/waterfall_runner.py",
    "app/input_adapter.py",
    "app/project_factories.py",
    "app/capex_engine.py",
    "app/opex_engine.py",
    "app/depreciation_engine.py",
    "app/excel_export.py",
    "app/services/save_run_service.py",
    "app/services/run_service.py",
    "app/services/compare_service.py",
    "app/services/download_service.py",
    "app/services/preview_context.py",
    "app/services/previews/",
    "app/persistence/",
    "app/validation_status.py",
    "domain/",
    "main_web.py",
    "main_api.py",
    # static — JS / legacy CSS / interaction layer
    "static/app.js",
    "static/styles.css",
    "static/chrome.css",
    "static/modelling/",
    "static/interaction/",
    # Existing pages / templates
    "app/templates/partials/_dashboard.html",
    "app/templates/partials/_nav_compression.html",
    "app/templates/partials/workspace_tabs.html",
    "app/templates/partials/_last_run_indicator.html",
    "app/templates/partials/_generic_status_line.html",
    "app/templates/partials/_brand_bar.html",
    "app/templates/partials/_command_bar.html",
    "app/templates/partials/_kpi_strip.html",
    "app/templates/partials/scen_mtx.html",
]


class TestForbiddenPathsUntouched:
    """UI-3 is additive only — no domain / engine / persistence / route
    / JS / styles.css / existing-page edit."""

    @pytest.mark.parametrize("relpath", FORBIDDEN_PATHS)
    def test_path_does_not_exist_or_unchanged(self, relpath, repo_diff):
        if not (REPO_ROOT / relpath).exists():
            pytest.skip(f"{relpath} does not exist in repo")
        assert relpath not in repo_diff.changed_paths, (
            f"UI-3 must not modify {relpath}; chrome-only PR. "
            f"Changed files: {sorted(repo_diff.changed_paths)}"
        )


# ---------------------------------------------------------------------------
# 8. base.html diff is additive
# ---------------------------------------------------------------------------

class TestBaseHtmlAdditiveOnly:
    """base.html must load chrome.css, tokens.css, styles.css,
    sheet-tabs.css, and workspace.css; the diff against origin/main
    must remain strictly additive.

    sheet-tabs.css was added in PR #814 (UI-3 worksheet navigation),
    so it already lives on main. UI-4 / UI-N PRs that extend base.html
    (adding more <link> tags or {% include %} directives or Jinja
    comments) are fine — the test below enforces only the additive
    envelope, not the exact diff content.
    """

    def test_base_html_has_chrome_tokens_styles_sheets_workspace(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        for needle in (
            "/static/chrome.css",
            "/static/tokens.css",
            "/static/styles.css",
            "/static/sheet-tabs.css",
            "/static/workspace.css",
            "/static/modelling-workspace.css",
            "/static/statements-reporting.css",
        ):
            assert needle in text, (
                f"base.html must reference {needle} as a stylesheet."
            )

    def test_base_html_diff_is_minimal(self, repo_diff):
        if "app/templates/base.html" not in repo_diff.changed_paths:
            return
        hunks = repo_diff.hunks_for("app/templates/base.html")
        added_lines = [h["content"] for h in hunks if h["op"] == "+"]
        removed_lines = [h["content"] for h in hunks if h["op"] == "-"]
        # Forbidden: any removal that affects an existing link / header.
        for needle in ("/static/styles.css", "/static/tokens.css",
                        "/static/chrome.css", "/static/sheet-tabs.css",
                        "/static/workspace.css",
                        "/static/modelling-workspace.css",
                        "/static/statements-reporting.css",
                        '<header class="top-header">'):
            assert not any(needle in line for line in removed_lines), (
                f"UI-3 must not remove existing line containing "
                f"{needle!r}."
            )
        # Allowed: <link> additions + Jinja {# ... #} comments only.
        inside_jinja = False
        for line in added_lines:
            stripped = line.strip()
            if not stripped:
                continue
            if inside_jinja:
                if "#}" in stripped:
                    inside_jinja = False
                continue
            if stripped.startswith("{#"):
                if "#}" not in stripped:
                    inside_jinja = True
                continue
            assert stripped.startswith("<link"), (
                f"base.html diff contains an unexpected added line: "
                f"{line!r}"
            )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class _RepoDiff:
    """Wraps `git diff origin/main --name-only` + per-file hunks."""

    def __init__(self) -> None:
        import subprocess
        out = subprocess.run(
            ["git", "diff", "--name-only", "origin/main", "--"],
            cwd=str(REPO_ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
        self.changed_paths = {
            line.strip()
            for line in out.stdout.splitlines()
            if line.strip()
        }
        ls = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "--"],
            cwd=str(REPO_ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
        self.untracked_paths: set[str] = {
            line.strip()
            for line in ls.stdout.splitlines()
            if line.strip()
        }
        self._hunks: dict[str, list[dict]] = {}
        for path in sorted(self.changed_paths):
            self._hunks[path] = self._parse_hunks(path)

    def _parse_hunks(self, path: str) -> list[dict]:
        import subprocess
        proc = subprocess.run(
            ["git", "diff", "origin/main", "--", path],
            cwd=str(REPO_ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
        hunks: list[dict] = []
        for line in proc.stdout.splitlines():
            if not line:
                continue
            if line.startswith("+++") or line.startswith("---"):
                continue
            if line.startswith("@@"):
                continue
            if line.startswith("+"):
                hunks.append({"op": "+", "content": line[1:]})
            elif line.startswith("-"):
                hunks.append({"op": "-", "content": line[1:]})
        return hunks

    def hunks_for(self, path: str) -> list[dict]:
        return list(self._hunks.get(path, []))


@pytest.fixture(scope="session")
def repo_diff():
    return _RepoDiff()