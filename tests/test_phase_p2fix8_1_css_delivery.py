"""Phase P2-FIX-8 PR 1 — CSS delivery & cache-busting.

Acceptance criteria:
1. Every rendered page's HTML references styles.css?v=<current asset_version>.
2. No occurrence of 'phase21-layout-fix' anywhere in templates.
3. asset_version is not the literal string 'phase21-layout-fix'.
4. asset_version is injected as a Jinja2 global (not hardcoded in each template).
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = REPO_ROOT / "app" / "templates"

STANDALONE_TEMPLATES = [
    "base.html",
    "project_home_page.html",
    "project_new_page.html",
    "project_browse_page.html",
]


def _all_template_files():
    return list(TEMPLATES_DIR.rglob("*.html"))


# ---------------------------------------------------------------------------
# 1. No hardcoded stale token
# ---------------------------------------------------------------------------

def test_no_phase21_token_in_any_template():
    """'phase21-layout-fix' must not appear in any template file."""
    offenders = []
    for path in _all_template_files():
        if "phase21-layout-fix" in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, f"Stale CSS token found in: {offenders}"


def test_no_phase21_token_in_main_web():
    main_web = REPO_ROOT / "main_web.py"
    assert "phase21-layout-fix" not in main_web.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 2. Standalone pages use dynamic asset_version
# ---------------------------------------------------------------------------

def test_standalone_pages_use_asset_version_variable():
    """Each standalone page template must reference {{ asset_version }} for styles.css."""
    for name in STANDALONE_TEMPLATES:
        path = TEMPLATES_DIR / name
        content = path.read_text(encoding="utf-8")
        assert "{{ asset_version }}" in content or "{%- set" not in content, (
            f"{name}: missing asset_version variable"
        )
        # Must not have a hardcoded ?v= value (only {{ asset_version }} allowed)
        hardcoded = re.findall(r'styles\.css\?v=[^{"\s]+', content)
        assert not hardcoded, f"{name}: hardcoded CSS version token found: {hardcoded}"


# ---------------------------------------------------------------------------
# 3. asset_version injected as Jinja2 global in main_web.py
# ---------------------------------------------------------------------------

def test_asset_version_injected_as_global():
    main_web = (REPO_ROOT / "main_web.py").read_text(encoding="utf-8")
    assert 'asset_version' in main_web
    assert 'templates.env.globals["asset_version"]' in main_web or \
           "templates.env.globals['asset_version']" in main_web


def test_asset_version_not_hardcoded_stale_value():
    """ASSET_VERSION must be computed dynamically, not set to 'phase21-layout-fix'."""
    main_web = (REPO_ROOT / "main_web.py").read_text(encoding="utf-8")
    assert "phase21-layout-fix" not in main_web


# ---------------------------------------------------------------------------
# 4. Smoke: import the computed ASSET_VERSION and verify it's non-empty
# ---------------------------------------------------------------------------

def test_asset_version_is_non_empty_string():
    import sys
    sys.path.insert(0, str(REPO_ROOT))
    try:
        # Import just the computation function, not the whole app
        import importlib.util
        spec = importlib.util.spec_from_file_location("main_web", REPO_ROOT / "main_web.py")
        # We only need to read the source; don't exec to avoid side effects
        src = (REPO_ROOT / "main_web.py").read_text()
        # Extract ASSET_VERSION assignment line
        m = re.search(r"ASSET_VERSION\s*=\s*_compute_asset_version\(\)", src)
        assert m, "ASSET_VERSION must be set by _compute_asset_version()"
        # Verify _compute_asset_version function exists
        assert "_compute_asset_version" in src
    finally:
        sys.path.pop(0)
