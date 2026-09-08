"""UI-1 — Finco One Design Tokens — hermetic smoke tests.

Verifies the structural invariants of `static/tokens.css`:
  - tokens.css exists at static/tokens.css
  - the file declares the key --fo-* design-token variables
  - tokens.css is loaded BEFORE styles.css in app/templates/base.html
  - required stylesheet links are reachable in the template
  - no invalid unprefixed token declarations

These tests are read-only: they inspect the repository's on-disk state.
No test starts the application, hits the database, runs git, or imports
runtime modules.  Tests are hermetic on:
  - local checkout
  - PR merge checkout
  - shallow CI checkout (no origin/main required)
  - main branch
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
        text = BASE_HTML.read_text(encoding="utf-8")
        assert re.search(
            r'<link\s+rel="stylesheet"\s+href="/static/tokens\.css\?v=\{\{\s*asset_version\s*\}\}"',
            text,
        ), "tokens.css link must include ?v={{ asset_version }} for cache busting."


# ---------------------------------------------------------------------------
# 4. base.html structural invariants (hermetic — no git diff)
# ---------------------------------------------------------------------------

class TestBaseHtmlStructural:
    """base.html must carry the required stylesheet links in the correct order.

    These are perpetual structural invariants valid on any checkout — no git
    comparison required.  (Historical UI-1 PR-diff assertions that required
    origin/main are removed: they are not valid permanent fast-ring invariants
    for future UI PRs running in shallow CI checkouts.)
    """

    def test_base_html_has_tokens_and_styles(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert "/static/tokens.css" in text, (
            "tokens.css link missing from base.html."
        )
        assert "/static/styles.css" in text, (
            "styles.css link missing from base.html."
        )
        assert text.find("/static/tokens.css") < text.find(
            "/static/styles.css"
        ), "tokens.css must load BEFORE styles.css in base.html."

    def test_styles_css_exists_on_disk(self):
        """static/styles.css must exist in the working tree."""
        assert STYLES_CSS.is_file(), (
            f"static/styles.css not found at {STYLES_CSS}"
        )

    def test_tokens_css_and_styles_css_both_linked(self):
        """Both stylesheets must be explicitly linked in base.html."""
        text = BASE_HTML.read_text(encoding="utf-8")
        assert re.search(r'href=["\'][^"\']*tokens\.css', text), (
            "No <link> to tokens.css found in base.html"
        )
        assert re.search(r'href=["\'][^"\']*styles\.css', text), (
            "No <link> to styles.css found in base.html"
        )


# ---------------------------------------------------------------------------
# 5. No Streamlit in main entry point
# ---------------------------------------------------------------------------

class TestNoStreamlit:
    def test_no_streamlit_import_in_main_web(self):
        """main_web.py must not import Streamlit."""
        src = (REPO_ROOT / "main_web.py").read_text(encoding="utf-8")
        assert "import streamlit" not in src
        assert "from streamlit" not in src
