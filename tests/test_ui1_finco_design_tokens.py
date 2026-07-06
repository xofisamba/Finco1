"""UI-1 — Finco One Design Tokens — smoke tests.

Verifies the additive introduction of `static/tokens.css`:
  - tokens.css exists at static/tokens.css
  - the file declares the key --fo-* design-token variables
  - tokens.css is loaded BEFORE styles.css in app/templates/base.html
  - no financial / engine / persistence files changed
  - no template redesign (additive only)
  - no class renames in legacy styles.css

All tests are read-only: they inspect the repository's on-disk state.
No test starts the application, hits the database, or imports runtime
modules. This keeps the smoke suite hermetic and fast.
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
STYLES_CSS = REPO_ROOT / "static" / "styles.css"
BASE_HTML = REPO_ROOT / "app" / "templates" / "base.html"


# ---------------------------------------------------------------------------
# 1. tokens.css exists
# ---------------------------------------------------------------------------

class TestTokensCssExists:
    """The Fable design-tokens file must be present at static/tokens.css."""

    def test_tokens_css_file_present(self):
        assert TOKENS_CSS.is_file(), (
            f"Expected Finco One design tokens at {TOKENS_CSS}, "
            f"but file does not exist."
        )

    def test_tokens_css_is_non_empty(self):
        assert TOKENS_CSS.is_file()
        assert TOKENS_CSS.stat().st_size > 1024, (
            f"tokens.css should be a substantive token sheet; "
            f"got {TOKENS_CSS.stat().st_size} bytes."
        )

    def test_tokens_css_is_valid_css(self):
        # Open + close brace sanity check — a CSS file must have balanced
        # top-level braces.
        text = TOKENS_CSS.read_text(encoding="utf-8")
        assert text.count("{") == text.count("}"), (
            "tokens.css must have balanced braces — got "
            f"{text.count('{')} open vs {text.count('}')} close."
        )

    def test_tokens_css_has_header_comment(self):
        # The deliverable header comment references the file path; this guards
        # against accidental replacement with a different token sheet.
        text = TOKENS_CSS.read_text(encoding="utf-8")
        assert "FINCO ONE — DESIGN TOKENS" in text
        assert "static/tokens.css" in text


# ---------------------------------------------------------------------------
# 2. Key --fo-* variables exist
# ---------------------------------------------------------------------------

# Each tuple is (category, variable, expected to be present).
# These cover every category the Fable token sheet declares. If a future
# token-sheet revision drops one of these, this test fails immediately so
# downstream code that consumes the variable does not silently break.
REQUIRED_FO_VARIABLES = [
    # brand scale
    ("brand", "--fo-brand-600"),
    ("brand", "--fo-brand-700"),
    ("brand", "--fo-brand-500"),
    # neutrals
    ("neutrals", "--fo-slate-50"),
    ("neutrals", "--fo-slate-500"),
    ("neutrals", "--fo-slate-900"),
    # semantic UI
    ("semantic", "--fo-paper"),
    ("semantic", "--fo-surface"),
    ("semantic", "--fo-ink"),
    ("semantic", "--fo-ink-soft"),
    ("semantic", "--fo-line"),
    ("semantic", "--fo-focus"),
    ("semantic", "--fo-link"),
    # RAG / status
    ("rag", "--fo-rag-green"),
    ("rag", "--fo-rag-amber"),
    ("rag", "--fo-rag-red"),
    ("rag", "--fo-state-dirty"),
    # data-viz
    ("dataviz", "--fo-viz-1"),
    ("dataviz", "--fo-viz-pos"),
    # typography
    ("typography", "--fo-font-ui"),
    ("typography", "--fo-font-mono"),
    ("typography", "--fo-text-xs"),
    ("typography", "--fo-text-md"),
    ("typography", "--fo-text-lg"),
    ("typography", "--fo-text-xl"),
    ("typography", "--fo-text-2xl"),
    ("typography", "--fo-weight-regular"),
    ("typography", "--fo-weight-semibold"),
    # spacing scale
    ("spacing", "--fo-s1"),
    ("spacing", "--fo-s2"),
    ("spacing", "--fo-s4"),
    ("spacing", "--fo-s8"),
    # layout
    ("layout", "--fo-row-h"),
    ("layout", "--fo-chrome-tabs-h"),
    ("layout", "--fo-bp-lg"),
    # radius / shadow
    ("radius_shadow", "--fo-r-sm"),
    ("radius_shadow", "--fo-r-md"),
    ("radius_shadow", "--fo-shadow-card"),
    ("radius_shadow", "--fo-shadow-popover"),
    # motion
    ("motion", "--fo-t-fast"),
    ("motion", "--fo-t-base"),
    ("motion", "--fo-ease"),
]


class TestKeyFoVariablesExist:
    """Every category of design token must be present."""

    @pytest.mark.parametrize(
        ("category", "variable"),
        REQUIRED_FO_VARIABLES,
        ids=[f"{cat}:{var}" for cat, var in REQUIRED_FO_VARIABLES],
    )
    def test_required_variable_present(self, category, variable):
        text = TOKENS_CSS.read_text(encoding="utf-8")
        # Use a word-boundary regex so `--fo-s1` does not match `--fo-s10`.
        pattern = re.compile(rf"(?<![\w-]){re.escape(variable)}\s*:")
        assert pattern.search(text), (
            f"Required design token {variable!r} ({category}) "
            f"not declared in tokens.css."
        )

    def test_no_legacy_unprefixed_aliases_added(self):
        # The token sheet must not introduce un-prefixed aliases that would
        # collide with existing variables in styles.css. Each declaration
        # must start with --fo- (or be a CSS-level @-rule / .util class).
        text = TOKENS_CSS.read_text(encoding="utf-8")
        bad = []
        for line_no, raw in enumerate(text.splitlines(), start=1):
            stripped = raw.strip()
            if not stripped or stripped.startswith(("/*", "*", "//")):
                continue
            # variable declarations
            if ":" in stripped and not stripped.startswith((".", "#", "[", ":", "@")):
                var_name = stripped.split(":", 1)[0].strip()
                # ignore selectors with ":" pseudo-classes — the
                # .startswith filter above already excludes them
                if var_name.startswith("--") and not var_name.startswith("--fo-"):
                    bad.append((line_no, var_name))
        assert not bad, (
            "tokens.css must only declare --fo-* variables (no un-prefixed "
            "aliases); offends:\n  " +
            "\n  ".join(f"L{n}: {v}" for n, v in bad)
        )


# ---------------------------------------------------------------------------
# 3. tokens.css loaded BEFORE styles.css in base.html
# ---------------------------------------------------------------------------

class TestLoadOrderInBaseHtml:
    """tokens.css <link> must appear BEFORE styles.css <link>."""

    def test_base_html_loads_tokens_css(self):
        assert BASE_HTML.is_file()
        text = BASE_HTML.read_text(encoding="utf-8")
        assert "/static/tokens.css" in text, (
            "base.html must link static/tokens.css as a stylesheet."
        )

    def test_base_html_loads_styles_css(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert "/static/styles.css" in text, (
            "base.html must continue to link static/styles.css "
            "(legacy stylesheet must remain)."
        )

    def test_tokens_css_loaded_before_styles_css(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        tokens_idx = text.find("/static/tokens.css")
        styles_idx = text.find("/static/styles.css")
        assert tokens_idx > 0, "tokens.css link missing from base.html"
        assert styles_idx > 0, "styles.css link missing from base.html"
        assert tokens_idx < styles_idx, (
            "tokens.css MUST be loaded BEFORE styles.css so --fo-* variables "
            "are available when legacy classes compute their values."
        )

    def test_tokens_css_uses_cache_busting_version(self):
        # Same ?v={{ asset_version }} query as styles.css — ensures both
        # bust the cache together when asset_version changes.
        text = BASE_HTML.read_text(encoding="utf-8")
        assert re.search(
            r'<link\s+rel="stylesheet"\s+href="/static/tokens\.css\?v=\{\{\s*asset_version\s*\}\}"',
            text,
        ), "tokens.css link must include ?v={{ asset_version }} for cache busting."


# ---------------------------------------------------------------------------
# 4. No financial / engine / persistence / template logic changes
# ---------------------------------------------------------------------------

# Forbidden paths — any commit that touches these is a non-UI-1 change.
# The list is conservative; UI-1 is tokens + base.html link only.
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
    "app/services/projs_create_service.py",
    "app/services/preview_context.py",
    "app/services/previews/",
    "app/persistence/",
    "domain/",
    "main_web.py",
    "main_api.py",
    "static/app.js",
    "static/modelling/",
    "static/interaction/",
    "static/styles.css",  # must NOT be touched
]


class TestForbiddenPathsUntouched:
    """UI-1 is additive only — no domain / engine / persistence / JS / styles.css touch."""

    @pytest.mark.parametrize("relpath", FORBIDDEN_PATHS)
    def test_path_does_not_exist_or_unchanged(self, relpath, repo_diff):
        # repo_diff is a session-scoped fixture that lists files changed
        # relative to origin/main. If the file is in the changed set AND
        # it actually exists in the working tree, the test fails. If the
        # path does not exist in the repo (e.g. app/services/previews/
        # does not apply here), the test passes — it's a structural
        # guarantee, not an "every project must have this folder" rule.
        if not (REPO_ROOT / relpath).exists():
            pytest.skip(f"{relpath} does not exist in repo")
        assert relpath not in repo_diff.changed_paths, (
            f"UI-1 must not modify {relpath}; this is a tokens-only PR. "
            f"Changed files: {sorted(repo_diff.changed_paths)}"
        )


# ---------------------------------------------------------------------------
# 5. No template redesign — additive only
# ---------------------------------------------------------------------------

class TestBaseHtmlAdditiveOnly:
    """base.html must continue to load tokens.css; the style additions
    on the file must follow the additive contract established by UI-1.

    This test enforces:
    - The tokens.css <link> line is still present in base.html.
    - The styles.css <link> line is still present in base.html.
    - tokens.css is loaded BEFORE styles.css.
    - The diff against origin/main ONLY contains:
        - <link rel="stylesheet" ...> tags (one per added stylesheet)
        - {% include "partials/..." %} directives
        - Jinja {# ... #} comment blocks
    No other categories of edits may slip in.
    """

    def test_base_html_has_tokens_and_styles(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert "/static/tokens.css" in text, (
            "tokens.css link missing from base.html."
        )
        assert "/static/styles.css" in text, (
            "styles.css link missing from base.html."
        )
        # tokens.css MUST come before styles.css.
        assert text.find("/static/tokens.css") < text.find(
            "/static/styles.css"
        ), "tokens.css must load BEFORE styles.css in base.html."

    def test_base_html_diff_is_minimal(self, repo_diff):
        # Cross-arc invariant: base.html is allowed to be modified by
        # any UI-N PR (UI-2/3/4/5/6/7 added a <link> per layer), but a
        # *fix* PR that only patches existing partials is also valid.
        # Skip the assertion when base.html wasn't touched (the rest
        # of the diff contract is enforced by TestForbiddenPathsUntouched
        # + TestStylesheetBaseHtmlReachable etc.).
        if "app/templates/base.html" not in repo_diff.changed_paths:
            pytest.skip(
                "base.html not modified — fix PR that only patches "
                "existing partials. The additive-only contract is "
                "enforced by the forbidden-path guards below."
            )
        # Inspect the diff hunks. Each added line must fall into one
        # of these allowed buckets:
        #   - <link rel="stylesheet" ...> tag (any stylesheet)
        #   - {% include "partials/_*.html" %} directive
        #   - Jinja {# ... #} comment (single or multi-line)
        # Anything else is a non-additive edit.
        hunks = repo_diff.hunks_for("app/templates/base.html")
        added_lines = [h["content"] for h in hunks if h["op"] == "+"]
        removed_lines = [h["content"] for h in hunks if h["op"] == "-"]
        # Forbidden: any removal that affects an existing chrome link
        # or template marker.
        for needle in ("/static/styles.css", "/static/tokens.css",
                        '<header class="top-header">'):
            assert not any(needle in line for line in removed_lines), (
                f"base.html diff must not remove existing line "
                f"containing {needle!r}."
            )
        # Walk the added lines; track whether we're inside a Jinja
        # comment block ({# ... #}). Lines inside such a block are
        # allowed.
        inside_jinja_comment = False
        for line in added_lines:
            stripped = line.strip()
            if not stripped:
                continue
            if inside_jinja_comment:
                if "#}" in stripped:
                    inside_jinja_comment = False
                continue
            if stripped.startswith("{#"):
                # Single-line or first-line of multi-line comment.
                if "#}" not in stripped:
                    inside_jinja_comment = True
                continue
            allowed = (
                stripped.startswith("<link")
                or stripped.startswith('{% include')
            )
            assert allowed, (
                f"base.html diff contains an unexpected added line: {line!r}"
            )


# ---------------------------------------------------------------------------
# 6. styles.css must be byte-identical (UI-1 does not touch it)
# ---------------------------------------------------------------------------

class TestLegacyStylesCssUnchanged:
    """legacy styles.css must remain byte-identical after UI-1."""

    def test_styles_css_unchanged(self, repo_diff):
        assert "static/styles.css" not in repo_diff.changed_paths, (
            "UI-1 must NOT modify static/styles.css; "
            "tokens.css layers alongside it."
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class _RepoDiff:
    """Minimal representation of `git diff origin/main --name-only` plus
    per-file unified-diff hunks. Built once per test session."""

    def __init__(self) -> None:
        import subprocess
        # name-only list
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
        # per-file hunks
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