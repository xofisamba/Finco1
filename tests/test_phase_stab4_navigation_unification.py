"""
STAB-4 — Navigation Unification & Results Visibility
Acceptance tests (presentation-layer only; no model/formula changes).

Checks:
  1. _nav_compression.html — Results button targets 'revenue', not 'capex'
  2. _nav_compression.html — Export & Audit button targets 'downloads', not 'audit'
  3. workspace_shell.html — results-subnav-wrapper present before construction panel
  4. workspace_shell.html — _results_subnav.html NOT included inside panel-capex
  5. workspace_shell.html — results-subnav-wrapper has --hidden class by default
  6. app.js — switchTab syncs .nav-compression-tab active state
  7. app.js — switchTab syncs .results-subnav-tab active state
  8. app.js — switchTab shows/hides results-subnav-wrapper
  9. styles.css — .results-subnav-wrapper--hidden rule present
 10. Engine MD5 guard — waterfall_core.py unchanged
"""

import hashlib
import pathlib
import re

ROOT = pathlib.Path(__file__).parent.parent

NAV_COMPRESSION = ROOT / "app/templates/partials/_nav_compression.html"
WORKSPACE_SHELL = ROOT / "app/templates/partials/workspace_shell.html"
APP_JS = ROOT / "static/app.js"
STYLES_CSS = ROOT / "static/styles.css"
WATERFALL = ROOT / "app/waterfall_core.py"

EXPECTED_ENGINE_MD5 = "6bf49f33efc989736c17cea0cb9b7723"

RESULTS_TABS = [
    "construction", "production", "revenue", "opex", "capex",
    "senior-debt", "shl", "tax", "pl", "cashflow", "balance",
    "distributions", "sponsor",
]


def _read(path):
    return path.read_text(encoding="utf-8")


# ── 1. Results button targets revenue ────────────────────────────────────────

def test_nav_results_button_targets_revenue():
    src = _read(NAV_COMPRESSION)
    # find the results button block
    m = re.search(
        r'id="nav-compression-tab-results"[^>]*>.*?</button>',
        src, re.DOTALL
    )
    assert m, "nav-compression-tab-results button not found"
    btn = m.group(0)
    assert 'data-target-tab="revenue"' in btn, "Results button should target revenue"
    assert 'switchTab(\'revenue\')' in btn, "Results button onclick should switchTab('revenue')"
    assert 'aria-controls="panel-revenue"' in btn


def test_nav_results_button_does_not_target_capex():
    src = _read(NAV_COMPRESSION)
    m = re.search(
        r'id="nav-compression-tab-results"[^>]*>.*?</button>',
        src, re.DOTALL
    )
    assert m
    btn = m.group(0)
    assert 'data-target-tab="capex"' not in btn
    assert 'switchTab(\'capex\')' not in btn


# ── 2. Export & Audit button targets downloads ───────────────────────────────

def test_nav_export_audit_button_targets_downloads():
    src = _read(NAV_COMPRESSION)
    m = re.search(
        r'id="nav-compression-tab-export-audit"[^>]*>.*?</button>',
        src, re.DOTALL
    )
    assert m, "nav-compression-tab-export-audit button not found"
    btn = m.group(0)
    assert 'data-target-tab="downloads"' in btn
    assert 'switchTab(\'downloads\')' in btn
    assert 'aria-controls="panel-downloads"' in btn


def test_nav_export_audit_does_not_target_audit_only():
    src = _read(NAV_COMPRESSION)
    m = re.search(
        r'id="nav-compression-tab-export-audit"[^>]*>.*?</button>',
        src, re.DOTALL
    )
    assert m
    btn = m.group(0)
    assert 'data-target-tab="audit"' not in btn


# ── 3. results-subnav-wrapper present before construction panel ───────────────

def test_workspace_shell_has_results_subnav_wrapper():
    src = _read(WORKSPACE_SHELL)
    assert 'id="results-subnav-wrapper"' in src, \
        "results-subnav-wrapper div must exist in workspace_shell.html"


def test_results_subnav_wrapper_before_construction():
    src = _read(WORKSPACE_SHELL)
    wrapper_pos = src.find('id="results-subnav-wrapper"')
    construction_pos = src.find('id="panel-construction"')
    assert wrapper_pos != -1
    assert construction_pos != -1
    assert wrapper_pos < construction_pos, \
        "results-subnav-wrapper must appear before panel-construction"


def test_results_subnav_wrapper_includes_subnav():
    src = _read(WORKSPACE_SHELL)
    m = re.search(
        r'id="results-subnav-wrapper".*?</div>',
        src, re.DOTALL
    )
    assert m, "results-subnav-wrapper div not found"
    wrapper_block = m.group(0)
    assert '_results_subnav.html' in wrapper_block, \
        "_results_subnav.html must be included inside results-subnav-wrapper"


# ── 4. _results_subnav NOT inside panel-capex ────────────────────────────────

def test_results_subnav_not_inside_panel_capex():
    src = _read(WORKSPACE_SHELL)
    m = re.search(
        r'id="panel-capex"[^>]*>.*?</div>',
        src, re.DOTALL
    )
    assert m, "panel-capex not found"
    capex_block = m.group(0)
    assert '_results_subnav.html' not in capex_block, \
        "_results_subnav.html must not be included inside panel-capex"


# ── 5. results-subnav-wrapper has --hidden class by default ──────────────────

def test_results_subnav_wrapper_hidden_by_default():
    src = _read(WORKSPACE_SHELL)
    m = re.search(r'id="results-subnav-wrapper"[^>]*class="([^"]*)"', src)
    assert m, "results-subnav-wrapper class attribute not found"
    classes = m.group(1)
    assert 'results-subnav-wrapper--hidden' in classes, \
        "results-subnav-wrapper must have --hidden class by default"


# ── 6. app.js syncs .nav-compression-tab active state ────────────────────────

def test_appjs_syncs_nav_compression_tab():
    src = _read(APP_JS)
    assert '.nav-compression-tab' in src, \
        "app.js must reference .nav-compression-tab for active-state sync"
    assert 'data-p2fix4-area' in src, \
        "app.js must use data-p2fix4-area attribute to find nav area buttons"


def test_appjs_results_tabs_list_complete():
    src = _read(APP_JS)
    for tab in RESULTS_TABS:
        assert f"'{tab}'" in src or f'"{tab}"' in src, \
            f"RESULTS_TABS list in app.js missing '{tab}'"


# ── 7. app.js syncs .results-subnav-tab active state ─────────────────────────

def test_appjs_syncs_results_subnav_tab():
    src = _read(APP_JS)
    assert '.results-subnav-tab' in src, \
        "app.js must reference .results-subnav-tab for active-state sync"
    assert 'results-subnav-tab-' in src, \
        "app.js must build results-subnav-tab-{tabId} element ID"


# ── 8. app.js shows/hides results-subnav-wrapper ─────────────────────────────

def test_appjs_shows_hides_subnav_wrapper():
    src = _read(APP_JS)
    assert 'results-subnav-wrapper' in src, \
        "app.js must reference results-subnav-wrapper"
    assert 'results-subnav-wrapper--hidden' in src, \
        "app.js must add/remove results-subnav-wrapper--hidden class"


# ── 9. styles.css has the hidden utility class ───────────────────────────────

def test_styles_has_results_subnav_wrapper_hidden():
    src = _read(STYLES_CSS)
    assert '.results-subnav-wrapper--hidden' in src, \
        "styles.css must define .results-subnav-wrapper--hidden"
    assert 'display: none' in src or 'display:none' in src, \
        "styles.css .results-subnav-wrapper--hidden must set display:none"


# ── 10. Engine MD5 guard ──────────────────────────────────────────────────────

def test_engine_md5_unchanged():
    data = WATERFALL.read_bytes()
    actual = hashlib.md5(data).hexdigest()
    assert actual == EXPECTED_ENGINE_MD5, (
        f"waterfall_core.py MD5 changed: {actual} != {EXPECTED_ENGINE_MD5}"
    )
