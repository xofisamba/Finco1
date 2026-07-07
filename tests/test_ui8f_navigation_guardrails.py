"""
UI-8F — Worksheet navigation round-trip guardrails.

Prevents regressions on:
  • Every worksheet tab being reachable (HTMX attributes present)
  • Chrome preservation (hx-target / hx-select point at #main-canvas)
  • No duplicate legacy navigation visible (.top-header, .nav-compression hidden)
  • No modelling nav rail re-introduced in workspace_shell.html
  • Active-tab sync wired (htmx:pushedIntoHistory listener)
  • Tab-load indicator present and styled

Static analysis only — no server required.
"""

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# URL tabs — HTMX canvas-swap attributes
# ---------------------------------------------------------------------------

URL_TAB_IDS = [
    "scenarios",
    "compare",
    "sensitivity",
    "lender",
    "reports",
    "bess",
    "settings",
]

SHEET_TABS_HTML = "app/templates/partials/_sheet_tabs.html"


def _url_tab_block(tab_id: str) -> str:
    src = _read(SHEET_TABS_HTML)
    # Extract the <a> element block for this tab id
    pattern = rf'data-fo-sheet-id="{re.escape(tab_id)}"[^<]*(?:(?!<a ).)*?</a>'
    # Simpler: grab from href= up to closing </a>
    # Find start of the <a> tag containing this sheet id
    idx = src.find(f'data-fo-sheet-id="{tab_id}"')
    assert idx != -1, f"Tab '{tab_id}' not found in {SHEET_TABS_HTML}"
    start = src.rfind("<a ", 0, idx)
    end = src.find("</a>", idx) + 4
    return src[start:end]


@pytest.mark.parametrize("tab_id", URL_TAB_IDS)
def test_url_tab_has_hx_get(tab_id):
    block = _url_tab_block(tab_id)
    assert "hx-get=" in block, f"Tab '{tab_id}' missing hx-get"


@pytest.mark.parametrize("tab_id", URL_TAB_IDS)
def test_url_tab_targets_main_canvas(tab_id):
    block = _url_tab_block(tab_id)
    assert 'hx-target="#main-canvas"' in block, \
        f"Tab '{tab_id}' hx-target is not #main-canvas"


@pytest.mark.parametrize("tab_id", URL_TAB_IDS)
def test_url_tab_selects_main_canvas(tab_id):
    block = _url_tab_block(tab_id)
    assert 'hx-select="#main-canvas"' in block, \
        f"Tab '{tab_id}' hx-select is not #main-canvas"


@pytest.mark.parametrize("tab_id", URL_TAB_IDS)
def test_url_tab_pushes_url(tab_id):
    block = _url_tab_block(tab_id)
    assert 'hx-push-url="true"' in block, \
        f"Tab '{tab_id}' missing hx-push-url=\"true\""


@pytest.mark.parametrize("tab_id", URL_TAB_IDS)
def test_url_tab_has_indicator(tab_id):
    block = _url_tab_block(tab_id)
    assert 'hx-indicator="#fo-tab-indicator"' in block, \
        f"Tab '{tab_id}' missing hx-indicator"


@pytest.mark.parametrize("tab_id", URL_TAB_IDS)
def test_url_tab_has_fallback_href(tab_id):
    """Each URL tab must have a plain href= so it works without JS."""
    block = _url_tab_block(tab_id)
    assert "href=" in block, f"Tab '{tab_id}' has no fallback href"


# ---------------------------------------------------------------------------
# DOM-switch tabs — kind attribute
# ---------------------------------------------------------------------------

DOM_TAB_IDS = ["overview", "inputs", "revenue", "opex", "capex",
               "senior-debt", "tax", "pl"]


@pytest.mark.parametrize("tab_id", DOM_TAB_IDS)
def test_dom_tab_kind_attribute(tab_id):
    src = _read(SHEET_TABS_HTML)
    assert f'data-fo-sheet-id="{tab_id}"' in src, \
        f"DOM tab '{tab_id}' not found in {SHEET_TABS_HTML}"
    idx = src.find(f'data-fo-sheet-id="{tab_id}"')
    start = src.rfind("<button", 0, idx)
    end = src.find("</button>", idx) + 9
    block = src[start:end]
    assert 'data-fo-sheet-kind="dom"' in block, \
        f"Tab '{tab_id}' expected kind=dom"


# ---------------------------------------------------------------------------
# main-canvas swap target in base.html
# ---------------------------------------------------------------------------

def test_main_canvas_id_on_main_element():
    src = _read("app/templates/base.html")
    # <main id="main-canvas" ...> (whitespace-tolerant)
    assert re.search(r'<main\b[^>]*\bid="main-canvas"', src), \
        "base.html: <main id=\"main-canvas\"> not found — HTMX swap target missing"


# ---------------------------------------------------------------------------
# No duplicate legacy navigation
# ---------------------------------------------------------------------------

def test_top_header_hidden_in_css():
    src = _read("static/styles.css")
    # .top-header { display: none } must be present (UI-8A)
    m = re.search(r'\.top-header\s*\{[^}]*display\s*:\s*none', src, re.DOTALL)
    assert m, "styles.css: .top-header must have display:none (UI-8A)"


def test_nav_compression_hidden_in_css():
    src = _read("static/styles.css")
    m = re.search(r'\.nav-compression\s*\{[^}]*display\s*:\s*none', src, re.DOTALL)
    assert m, "styles.css: .nav-compression must have display:none (UI-8A)"


def test_no_modelling_nav_in_workspace_shell():
    """UI-8C removed the left nav rail — it must not reappear."""
    src = _read("app/templates/partials/workspace_shell.html")
    assert '_modelling_workspace_nav.html' not in src, \
        "workspace_shell.html still includes _modelling_workspace_nav.html (UI-8C regression)"


# ---------------------------------------------------------------------------
# Active-tab sync after HTMX navigation
# ---------------------------------------------------------------------------

def test_pushed_into_history_listener_present():
    src = _read(SHEET_TABS_HTML)
    assert "htmx:pushedIntoHistory" in src, \
        f"{SHEET_TABS_HTML}: htmx:pushedIntoHistory listener missing — active tab won't sync after canvas swap"


# ---------------------------------------------------------------------------
# Tab-load indicator
# ---------------------------------------------------------------------------

def test_tab_indicator_element_in_sheet_tabs():
    src = _read(SHEET_TABS_HTML)
    assert 'id="fo-tab-indicator"' in src, \
        f"{SHEET_TABS_HTML}: #fo-tab-indicator element not found"


def test_tab_indicator_styled_in_chrome_css():
    src = _read("static/chrome.css")
    assert ".fo-tab-indicator" in src, \
        "chrome.css: .fo-tab-indicator class not declared"


# ---------------------------------------------------------------------------
# Context panel toggle — UI-8B
# ---------------------------------------------------------------------------

CONTEXT_PARTIALS = [
    "app/templates/partials/_modelling_workspace_context_revenue.html",
    "app/templates/partials/_modelling_workspace_context_opex.html",
    "app/templates/partials/_modelling_workspace_context_capex.html",
    "app/templates/partials/_modelling_workspace_context_debt.html",
    "app/templates/partials/_modelling_workspace_context_tax.html",
]


@pytest.mark.parametrize("partial", CONTEXT_PARTIALS)
def test_context_partial_has_toggle_button(partial):
    src = _read(partial)
    assert "fo-modelling-workspace__context-toggle" in src, \
        f"{partial}: context-toggle button missing (UI-8B)"


@pytest.mark.parametrize("partial", CONTEXT_PARTIALS)
def test_context_partial_starts_collapsed(partial):
    src = _read(partial)
    assert "fo-modelling-workspace__context--collapsed" in src, \
        f"{partial}: context panel not initially collapsed (UI-8B)"


@pytest.mark.parametrize("partial", CONTEXT_PARTIALS)
def test_context_partial_has_sheet_attribute(partial):
    src = _read(partial)
    assert "data-fo-context-sheet=" in src, \
        f"{partial}: data-fo-context-sheet attribute missing (needed for localStorage key)"


# ---------------------------------------------------------------------------
# Financial statements runtime state — UI-8E
# ---------------------------------------------------------------------------

def test_statements_workspace_has_fs_state_attribute():
    src = _read("app/templates/partials/_statements_workspace_selector.html")
    assert 'data-fo-fs-state="no-runtime"' in src, \
        "_statements_workspace_selector.html: data-fo-fs-state default not set (UI-8E)"


def test_no_runtime_disables_toolbar_in_css():
    src = _read("static/statements-reporting.css")
    assert '[data-fo-fs-state="no-runtime"]' in src, \
        "statements-reporting.css: no-runtime state CSS rules missing (UI-8E)"


# ---------------------------------------------------------------------------
# All sheet-ids unique
# ---------------------------------------------------------------------------

def test_all_sheet_ids_unique():
    src = _read(SHEET_TABS_HTML)
    ids = re.findall(r'data-fo-sheet-id="([^"]+)"', src)
    assert len(ids) == len(set(ids)), \
        f"Duplicate data-fo-sheet-id values in {SHEET_TABS_HTML}: {ids}"


def test_all_expected_tabs_present():
    src = _read(SHEET_TABS_HTML)
    expected = DOM_TAB_IDS + URL_TAB_IDS
    ids = re.findall(r'data-fo-sheet-id="([^"]+)"', src)
    missing = [t for t in expected if t not in ids]
    assert not missing, f"Missing tabs in {SHEET_TABS_HTML}: {missing}"
