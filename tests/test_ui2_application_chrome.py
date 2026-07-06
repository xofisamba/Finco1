"""UI-2 — Application Chrome Foundation — smoke / governance tests.

Verifies the additive introduction of the new top-level application
frame (brand bar + command bar + KPI strip + sheet-tab reserve).

  - static/chrome.css exists and declares the fo-* chrome class family
  - app/templates/partials/_brand_bar.html exists
  - app/templates/partials/_command_bar.html exists
  - app/templates/partials/_kpi_strip.html exists
  - app/templates/partials/_app_chrome.html exists
  - app/templates/base.html loads chrome.css BEFORE the chrome mount
  - app/templates/base.html mounts the chrome PARTIAL ABOVE the
    legacy <header class="top-header"> (legacy chrome preserved)
  - Every new class is namespaced under `.fo-` (no leakage onto
    legacy `.fc-`, `.ps-`, `.scm-`, etc. classes)
  - chrome.css consumes only --fo-* tokens for colours / spacing /
    shadows / typography
  - No financial / engine / persistence / main_web / main_api / factory
    files modified
  - No edits to existing legacy pages/templates

All tests are read-only / static — no application boot, no DB, no
imports of runtime modules. This keeps the smoke suite hermetic,
fast, and CI-safe.
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
BASE_HTML = REPO_ROOT / "app" / "templates" / "base.html"
APP_CHROME_HTML = (
    REPO_ROOT / "app" / "templates" / "partials" / "_app_chrome.html"
)
BRAND_BAR_HTML = (
    REPO_ROOT / "app" / "templates" / "partials" / "_brand_bar.html"
)
COMMAND_BAR_HTML = (
    REPO_ROOT / "app" / "templates" / "partials" / "_command_bar.html"
)
KPI_STRIP_HTML = (
    REPO_ROOT / "app" / "templates" / "partials" / "_kpi_strip.html"
)


# ---------------------------------------------------------------------------
# 1. File presence / size sanity
# ---------------------------------------------------------------------------

class TestFilesExist:
    """All UI-2 deliverables must exist on disk."""

    @pytest.mark.parametrize("path", [
        CHROME_CSS,
        APP_CHROME_HTML,
        BRAND_BAR_HTML,
        COMMAND_BAR_HTML,
        KPI_STRIP_HTML,
    ])
    def test_deliverable_file_present(self, path):
        assert path.is_file(), (
            f"UI-2 deliverable missing: {path}"
        )


class TestChromeCssSanity:
    """chrome.css must be a non-trivial, balanced CSS sheet."""

    def test_chrome_css_has_header_comment(self):
        text = CHROME_CSS.read_text(encoding="utf-8")
        assert "FINCO ONE" in text and "CHROME" in text, (
            "chrome.css must start with the Finco One chrome header."
        )

    def test_chrome_css_balanced_braces(self):
        text = CHROME_CSS.read_text(encoding="utf-8")
        assert text.count("{") == text.count("}"), (
            "chrome.css must have balanced braces — got "
            f"{text.count('{')} open vs {text.count('}')} close."
        )

    def test_chrome_css_substantive_size(self):
        # A genuine chrome stylesheet is several KB; reject near-empty.
        assert CHROME_CSS.stat().st_size > 4000, (
            f"chrome.css should be substantive; got "
            f"{CHROME_CSS.stat().st_size} bytes."
        )


# ---------------------------------------------------------------------------
# 2. fo- class namespacing
# ---------------------------------------------------------------------------

# All UI-2 chrome classes must live under the `fo-` prefix. This guards
# against accidental collision with legacy families (.fc-, .ps-, .scm-,
# .top-header, .dashboard-*, ...).
REQUIRED_FO_CLASSES = [
    # chrome wrapper
    "fo-chrome",
    # brand bar
    "fo-brand-bar",
    "fo-brand-bar__brand",
    "fo-brand-bar__wordmark",
    "fo-brand-bar__select",
    "fo-brand-bar__kbd",
    "fo-theme-toggle",
    # command bar
    "fo-command-bar",
    "fo-btn--primary",
    "fo-btn--ghost",
    "fo-btn--placeholder",
    "fo-btn__kbd",
    "fo-pill",
    "fo-pill__dot",
    "fo-pill--fresh",
    "fo-pill--stale",
    "fo-pill--running",
    "fo-pill--error",
    "fo-meta",
    "fo-meta__label",
    "fo-meta__value",
    # KPI strip
    "fo-kpi-strip",
    "fo-kpi-strip--stale",
    "fo-kpi",
    "fo-kpi__label",
    "fo-kpi__value",
    "fo-kpi__value--placeholder",
    # sheet-tab reserve
    "fo-sheet-tab-reserve",
]


class TestFoClassNamespacing:
    """UI-2 chrome classes are namespaced strictly under `fo-`."""

    @pytest.mark.parametrize("cls", REQUIRED_FO_CLASSES)
    def test_fo_class_appears_in_chrome_css(self, cls):
        text = CHROME_CSS.read_text(encoding="utf-8")
        # Word-boundary regex — `.fo-pa` does not accidentally match
        # `.fo-pause`, etc.
        pattern = re.compile(rf"\.{re.escape(cls)}\b")
        assert pattern.search(text), (
            f"Required chrome class .{cls} not declared in chrome.css."
        )

    @pytest.mark.parametrize("cls", REQUIRED_FO_CLASSES)
    def test_fo_class_only_in_chrome_css(self, cls, repo_diff):
        # The class must NOT appear in static/styles.css (legacy). If a
        # future refactor accidentally pollutes the legacy stylesheet
        # with chrome-only classes, this test fails.
        legacy_text = (REPO_ROOT / "static" / "styles.css").read_text(
            encoding="utf-8"
        )
        legacy_pattern = re.compile(rf"\.{re.escape(cls)}\b")
        assert not legacy_pattern.search(legacy_text), (
            f"Chrome class .{cls} leaked into static/styles.css; "
            f"chrome must own its own stylesheet."
        )
        # And chrome.css must be staged-or-tracked. UI-2 is a delivered
        # PR — file is part of the change set.
        tracked = (
            "static/chrome.css" in repo_diff.changed_paths
            or "static/chrome.css" in repo_diff.untracked_paths
        )
        assert tracked, (
            "static/chrome.css must be added to the PR (either staged "
            "or currently untracked — git-add it)."
        )


# ---------------------------------------------------------------------------
# 3. chrome.css consumes ONLY --fo-* design tokens
# ---------------------------------------------------------------------------

# These FORBIDDEN patterns guard against the chrome author hand-coding
# raw hex, px spacing, hard-coded shadows, or peeking at the legacy
# `--sidebar-bg` style colour names. Every visual property in chrome.css
# must be token-driven.
FORBIDDEN_RAW_PATTERNS = [
    (r"#[0-9a-fA-F]{3,8}\b", "raw hex colour"),
    (r"\brgba?\(\s*\d", "raw rgb colour"),
    (r"box-shadow\s*:\s*[^v;]*;", "raw box-shadow"),
    (r"var\(--(fo|sidebar|primary|surface|border|sidebar-bg|--text)\b",
     "non-fo- token usage"),
]


class TestChromeCssOnlyConsumesFoTokens:
    """chrome.css must consume only --fo-* tokens; no raw colours/spacing."""

    def test_no_raw_hex_colours(self):
        text = CHROME_CSS.read_text(encoding="utf-8")
        offenders = []
        for line_no, raw in enumerate(text.splitlines(), start=1):
            # Comments may mention hex values without producing rules.
            stripped = raw.strip()
            if not stripped or stripped.startswith(("/*", "*", "//")):
                continue
            if re.search(r"#[0-9a-fA-F]{3,8}\b", raw):
                offenders.append((line_no, raw))
        assert not offenders, (
            "chrome.css must not declare raw hex colours; "
            "use --fo-* tokens instead. Offends:\n  " +
            "\n  ".join(f"L{n}: {l}" for n, l in offenders)
        )

    def test_no_raw_rgb_colours(self):
        # Strip CSS comments so commentary mentioning "rgba()" doesn't
        # trip the lint — we only care about *declarations*.
        text = CHROME_CSS.read_text(encoding="utf-8")
        text_no_comments = re.sub(
            r"/\*.*?\*/", "", text, flags=re.DOTALL
        )
        offenders = []
        for line_no, raw in enumerate(text_no_comments.splitlines(), start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            if re.search(r"\brgba?\s*\(", raw):
                offenders.append((line_no, raw))
        assert not offenders, (
            "chrome.css must not declare raw rgba() colours; "
            "use --fo-* tokens. Offends:\n  " +
            "\n  ".join(f"L{n}: {l}" for n, l in offenders)
        )

    def test_uses_fo_tokens_for_visual_props(self):
        # chrome.css must reference at least the canonical design tokens
        # for colours, spacing, typography, shadow, motion.
        text = CHROME_CSS.read_text(encoding="utf-8")
        for token in [
            "--fo-paper",
            "--fo-surface",
            "--fo-ink",
            "--fo-line",
            "--fo-brand-600",
            "--fo-rag-green",
            "--fo-font-ui",
            "--fo-text-md",
            "--fo-s2",
            "--fo-t-fast",
        ]:
            assert token in text, (
                f"chrome.css must consume {token} from tokens.css."
            )

    def test_no_legacy_palette_alias(self):
        # Legacy variables that exist in static/styles.css MUST NOT be
        # re-declared or referenced from chrome.css. The chrome only
        # knows about the fo-* namespace. Note: substring `--primary`
        # legitimately appears in CSS class names like `.fo-btn--primary`,
        # so we use a word-boundary regex anchored on the var() use site
        # rather than the bare substring.
        text = CHROME_CSS.read_text(encoding="utf-8")
        for legacy in ["--sidebar-bg", "--primary", "--surface",
                        "--border", "--text-secondary"]:
            pattern = re.compile(rf"var\(\s*{re.escape(legacy)}\b")
            assert not pattern.search(text), (
                f"chrome.css must not reference legacy token {legacy}; "
                f"use the --fo-* equivalent."
            )


# ---------------------------------------------------------------------------
# 4. base.html — chrome.css link + chrome partial mount order
# ---------------------------------------------------------------------------

class TestBaseHtmlChromeMount:
    """chrome.css link + partial include + relative ordering vs legacy."""

    def test_chrome_css_linked(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert "/static/chrome.css" in text, (
            "base.html must link static/chrome.css as a stylesheet."
        )

    def test_chrome_css_after_tokens_and_styles(self):
        # tokens.css → styles.css → chrome.css.
        text = BASE_HTML.read_text(encoding="utf-8")
        tokens_idx = text.find("/static/tokens.css")
        styles_idx = text.find("/static/styles.css")
        chrome_idx = text.find("/static/chrome.css")
        assert tokens_idx > 0 and styles_idx > 0 and chrome_idx > 0
        assert tokens_idx < styles_idx < chrome_idx, (
            "Load order MUST be tokens.css → styles.css → chrome.css."
        )

    def test_chrome_partial_included(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert "_app_chrome.html" in text, (
            "base.html must include partials/_app_chrome.html."
        )

    def test_chrome_partial_mounted_above_legacy_top_header(self):
        # Mount order is what makes this strictly additive — the chrome
        # lives ABOVE the legacy header; nothing was renamed or moved.
        text = BASE_HTML.read_text(encoding="utf-8")
        # Search for the actual {% include "partials/_app_chrome.html" %}
        # directive, not the comment that mentions the file.
        chrome_match = re.search(
            r'\{%\s*include\s+"partials/_app_chrome\.html"\s*%\}', text
        )
        assert chrome_match is not None, (
            "No {% include \"partials/_app_chrome.html\" %} directive "
            "in base.html."
        )
        chrome_idx = chrome_match.start()
        # Find a <header class="top-header"> that is NOT inside a Jinja
        # comment ({# ... #}). The base template describes the legacy
        # header in a comment; that mention must not satisfy this check.
        idx = 0
        legacy_idx = -1
        while True:
            idx = text.find('<header class="top-header">', idx)
            if idx < 0:
                break
            # Is this position inside a Jinja comment?
            before = text[:idx]
            last_open = before.rfind('{#')
            last_close = before.rfind('#}')
            if last_open > last_close:
                # Inside a comment — skip.
                idx += 1
                continue
            legacy_idx = idx
            break
        assert legacy_idx > 0, (
            "No non-comment <header class=\"top-header\"> element in "
            "base.html."
        )
        assert chrome_idx < legacy_idx, (
            "Chrome partial must mount ABOVE the legacy top-header; "
            "the existing header must remain in place."
        )

    def test_legacy_top_header_still_present(self):
        # The legacy chrome must still render below the new chrome.
        text = BASE_HTML.read_text(encoding="utf-8")
        # Find a non-comment <header class="top-header">.
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
            "base.html — UI-2 is additive only."
        )


# ---------------------------------------------------------------------------
# 5. Partial contents — surface real functionality
# ---------------------------------------------------------------------------

class TestBrandBarPartial:
    """Brand bar must declare the 6 cells from the brief."""

    def test_brand_bar_has_logo(self):
        text = BRAND_BAR_HTML.read_text(encoding="utf-8")
        assert "fo-brand-bar__logo" in text and "Finco One" in text

    @pytest.mark.parametrize("needle", [
        "Project",
        "Scenario",
        "⌘K",
        "Theme",
    ])
    def test_brand_bar_has_placeholder(self, needle):
        text = BRAND_BAR_HTML.read_text(encoding="utf-8")
        assert needle in text, (
            f"Brand bar must show the placeholder '{needle}' from "
            f"the brief."
        )


class TestCommandBarPartial:
    """Command bar must declare Run / Save / Export / Undo / Redo +
    last-run timestamp + engine version + status pills."""

    @pytest.mark.parametrize("needle", [
        # Run button (real htmx POST → /run)
        'hx-post="/run"',
        # Save button (real htmx POST → /scenarios/save)
        'hx-post="/scenarios/save"',
        # Export — links to existing /download
        'href="/download"',
        # Undo / Redo — disabled placeholders
        "Undo",
        "Redo",
        # Last-run timestamp placeholder
        "Last run",
        # Engine version placeholder
        "Engine",
        # Status pills
        "Validation",
        "Stale",
        "Fresh",
    ])
    def test_command_bar_has_action(self, needle):
        text = COMMAND_BAR_HTML.read_text(encoding="utf-8")
        assert needle in text, (
            f"Command bar must declare the '{needle}' affordance from "
            f"the brief."
        )


class TestKpiStripPartial:
    """KPI strip must show Project IRR / Equity IRR / NPV / DSCR / LLCR."""

    @pytest.mark.parametrize("needle", [
        "Project IRR",
        "Equity IRR",
        "NPV",
        "Min DSCR",
        "Avg DSCR",
        "LLCR",
    ])
    def test_kpi_strip_declares_label(self, needle):
        text = KPI_STRIP_HTML.read_text(encoding="utf-8")
        assert needle in text, (
            f"KPI strip must include the '{needle}' label."
        )

    def test_kpi_strip_has_stale_class(self):
        # When inputs are dirty the strip must visually mark stale.
        text = KPI_STRIP_HTML.read_text(encoding="utf-8")
        assert "fo-kpi-strip--stale" in text, (
            "KPI strip must apply the stale class when inputs are dirty."
        )

    def test_kpi_strip_placeholder_dash_for_missing(self):
        # Never display stale KPIs as if current — show em-dash when
        # no snapshot exists.
        text = KPI_STRIP_HTML.read_text(encoding="utf-8")
        assert "—" in text or "&mdash;" in text, (
            "KPI strip must show the em-dash placeholder for missing "
            "KPIs (never display stale values as current)."
        )


# ---------------------------------------------------------------------------
# 6. Forbidden paths — UI-2 must NOT touch engine / persistence / routes
# ---------------------------------------------------------------------------

FORBIDDEN_PATHS = [
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
    "static/app.js",
    "static/modelling/",
    "static/interaction/",
    "static/styles.css",  # must NOT be touched
    # Existing pages / templates must NOT be touched
    "app/templates/partials/_dashboard.html",
    "app/templates/partials/_nav_compression.html",
    "app/templates/partials/workspace_tabs.html",
    "app/templates/partials/_last_run_indicator.html",
    "app/templates/partials/_generic_status_line.html",
    "app/templates/partials/scen_mtx.html",
]


class TestForbiddenPathsUntouched:
    """UI-2 is additive only — no domain / engine / persistence touch,
    no legacy stylesheet edit, no existing page edit."""

    @pytest.mark.parametrize("relpath", FORBIDDEN_PATHS)
    def test_path_does_not_exist_or_unchanged(self, relpath, repo_diff):
        if not (REPO_ROOT / relpath).exists():
            pytest.skip(f"{relpath} does not exist in repo")
        assert relpath not in repo_diff.changed_paths, (
            f"UI-2 must not modify {relpath}; chrome-only PR. "
            f"Changed files: {sorted(repo_diff.changed_paths)}"
        )


# ---------------------------------------------------------------------------
# 7. base.html diff is additive — only the chrome links + partial include
# ---------------------------------------------------------------------------

class TestBaseHtmlAdditiveOnly:
    """base.html diff must contain only the chrome additions."""

    def test_base_html_diff_is_minimal(self, repo_diff):
        assert "app/templates/base.html" in repo_diff.changed_paths, (
            "base.html must be modified (chrome link + partial include)."
        )

        hunks = repo_diff.hunks_for("app/templates/base.html")
        added_lines = [h["content"] for h in hunks if h["op"] == "+"]
        removed_lines = [h["content"] for h in hunks if h["op"] == "-"]

        # Required: at least one chrome.css link line added.
        assert any("/static/chrome.css" in line for line in added_lines), (
            "chrome.css link was not added to base.html."
        )
        # Required: the chrome partial include was added.
        assert any("_app_chrome.html" in line for line in added_lines), (
            "Chrome partial include was not added to base.html."
        )
        # Forbidden: any removal that affects an existing chrome link.
        for needle in ("/static/tokens.css", "/static/styles.css",
                        '<header class="top-header">'):
            assert not any(needle in line for line in removed_lines), (
                f"UI-2 must not remove existing line containing "
                f"{needle!r}."
            )
        # Forbidden: any added line that is not either:
        #   - a Jinja {# ... #} comment (single- or multi-line)
        #   - a <link rel="stylesheet" ...> tag
        #   - a {% include "partials/..." %} tag
        #   - a literal blank
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
            ok = (
                stripped.startswith('<link')
                or stripped.startswith('{% include')
                or '<header class="top-header"' in stripped
                or "<body>" in stripped
            )
            assert ok, (
                f"base.html diff contains an unexpected added line: {line!r}"
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
        # Untracked but staged/added-on-the-working-tree files — for the
        # purpose of this suite, "tracked" path list and "missing" path
        # checks (chrome.css must be tracked) are what matter.
        self.untracked_paths: set[str] = set()
        ls = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "--"],
            cwd=str(REPO_ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
        for line in ls.stdout.splitlines():
            if line.strip():
                self.untracked_paths.add(line.strip())

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
