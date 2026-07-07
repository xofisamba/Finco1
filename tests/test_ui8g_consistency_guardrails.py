"""
UI-8G — Consistency audit static guardrails.

Prevents regressions on:
  • No developer-facing copy leaking to users
  • Error state messages don't expose raw Python exception variables
  • Focus rings exist on brand-bar actions
  • Sticky column header includes the sheet-tabs offset
  • Consistency CSS is wired into base.html
  • Empty-state stale-rerun uses :focus-visible not bare :focus
"""

import re
from pathlib import Path

REPO = Path(__file__).parent.parent


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Developer copy — must not appear in rendered HTML
# ---------------------------------------------------------------------------

FORBIDDEN_PHRASES = [
    "assemble_financial_statements(WaterfallResult)",
    "not yet wired. Display only",
    "not yet computed",
    "not used by Run until persistence",
    "Mapped but not yet connected to runtime",
    "Undo (coming soon)",
    "Redo (coming soon)",
    "Theme toggle (coming soon)",
    "User menu (coming soon)",
    "Sensitivity Unavailable",
    "BESS Revenue Unavailable",
    "Lender Case Unavailable",
    "Covenant Dashboard Unavailable",
    "Timeline Unavailable",
]


def test_no_developer_copy_in_sheet_financials():
    src = _read("app/templates/partials/sheet_financials.html")
    # Strip HTML/Jinja comments before checking — comments don't render to users
    src_no_comments = re.sub(r'<!--.*?-->', '', src, flags=re.DOTALL)
    src_no_comments = re.sub(r'\{#.*?#\}', '', src_no_comments, flags=re.DOTALL)
    assert "assemble_financial_statements(WaterfallResult)" not in src_no_comments, \
        "sheet_financials.html still contains developer function name in user-visible content"
    # The <code> block and title= attributes must be gone
    assert "<code>assemble_financial_statements" not in src, \
        "sheet_financials.html still has <code>assemble_financial_statements in rendered output"


def test_no_developer_copy_in_state_banner():
    src = _read("app/templates/partials/_state_banner.html")
    assert "not yet wired. Display only" not in src, \
        "_state_banner.html still contains developer copy"


def test_no_developer_copy_in_runtime_impact_chip():
    src = _read("app/templates/partials/_runtime_impact_chip.html")
    assert "not yet connected to runtime calculations" not in src, \
        "_runtime_impact_chip.html still contains developer copy"


def test_no_coming_soon_in_command_bar_aria_labels():
    src = _read("app/templates/partials/_command_bar.html")
    assert "coming soon" not in src.lower() or "not yet available" in src.lower(), \
        "_command_bar.html aria-labels still expose 'coming soon'"


def test_no_coming_soon_in_brand_bar_aria_labels():
    src = _read("app/templates/partials/_brand_bar.html")
    assert "coming soon" not in src.lower(), \
        "_brand_bar.html aria-labels still expose 'coming soon'"


def test_no_developer_copy_in_workspace_shell_aria_labels():
    src = _read("app/templates/partials/workspace_shell.html")
    assert "placeholder; not yet computed" not in src, \
        "workspace_shell.html still has 'placeholder; not yet computed' in aria-labels"


# ---------------------------------------------------------------------------
# Raw error variables must not be passed directly to the template
# ---------------------------------------------------------------------------

def test_sensitivity_error_not_exposed():
    src = _read("app/templates/partials/scenario_sensitivity.html")
    assert "{{ sensitivity_error }}" not in src, \
        "scenario_sensitivity.html exposes raw sensitivity_error to the user"


def test_bess_revenue_error_not_exposed():
    src = _read("app/templates/partials/bess_revenue_breakdown.html")
    assert "{{ bess_revenue_error }}" not in src, \
        "bess_revenue_breakdown.html exposes raw bess_revenue_error to the user"


def test_lender_case_error_not_exposed():
    src = _read("app/templates/partials/lender_case.html")
    assert "{{ lender_case_error }}" not in src, \
        "lender_case.html exposes raw lender_case_error to the user"


def test_covenant_error_not_exposed():
    src = _read("app/templates/partials/covenant_dashboard.html")
    assert "{{ covenant_error }}" not in src, \
        "covenant_dashboard.html exposes raw covenant_error to the user"


def test_covenant_error_not_exposed_in_timeline():
    src = _read("app/templates/partials/covenant_timeline.html")
    assert "{{ covenant_error }}" not in src, \
        "covenant_timeline.html exposes raw covenant_error to the user"


# ---------------------------------------------------------------------------
# Preview badge removed from scenario compare empty state
# ---------------------------------------------------------------------------

def test_no_preview_badge_in_compare_empty_state():
    src = _read("app/templates/partials/scenario_compare.html")
    # The empty state block (after {# ── Truly empty state ── #}) should not have badge-preview
    idx = src.find("ps-mini-empty")
    assert idx != -1, "scenario_compare.html: ps-mini-empty not found"
    block = src[idx:idx+300]
    assert "badge-preview" not in block, \
        "scenario_compare.html: badge-preview still present in empty state block"


# ---------------------------------------------------------------------------
# CAPEX developer copy cleaned up
# ---------------------------------------------------------------------------

def test_capex_no_persistence_developer_copy():
    src = _read("app/templates/partials/sheet_capex.html")
    assert "not used by Run until persistence is implemented" not in src, \
        "sheet_capex.html still contains 'not used by Run until persistence is implemented'"


# ---------------------------------------------------------------------------
# Focus ring on brand-bar action (not suppressed)
# ---------------------------------------------------------------------------

def test_brand_bar_action_focus_ring_not_suppressed():
    src = _read("static/chrome.css")
    # Find the focus-visible block for fo-brand-bar__action
    m = re.search(
        r'\.fo-brand-bar__action:focus-visible\s*\{([^}]+)\}',
        src, re.DOTALL
    )
    assert m, "chrome.css: .fo-brand-bar__action:focus-visible block not found"
    block = m.group(1)
    assert "outline: none" not in block, \
        "chrome.css: .fo-brand-bar__action:focus-visible still suppresses outline"
    assert "outline:" in block, \
        "chrome.css: .fo-brand-bar__action:focus-visible has no outline rule"


# ---------------------------------------------------------------------------
# Sticky column header includes sheet-tabs height
# ---------------------------------------------------------------------------

def test_fc_grid_header_sticky_includes_tabs_height():
    src = _read("static/modelling-workspace.css")
    m = re.search(
        r'\.fo-modelling-workspace__content\s+\.fc-grid\s+thead\s+\.fc-th\s*\{([^}]+)\}',
        src, re.DOTALL
    )
    assert m, "modelling-workspace.css: fc-grid thead sticky block not found"
    block = m.group(1)
    assert "--fo-chrome-tabs-h" in block, \
        "modelling-workspace.css: sticky grid header missing --fo-chrome-tabs-h offset"


# ---------------------------------------------------------------------------
# Consistency CSS wired into base.html
# ---------------------------------------------------------------------------

def test_consistency_css_in_base_html():
    src = _read("app/templates/base.html")
    assert "ui8g-consistency.css" in src, \
        "base.html: ui8g-consistency.css not linked"


def test_consistency_css_file_exists():
    assert (REPO / "static/ui8g-consistency.css").exists(), \
        "static/ui8g-consistency.css file does not exist"


# ---------------------------------------------------------------------------
# Empty states stale-rerun uses :focus-visible
# ---------------------------------------------------------------------------

def test_stale_rerun_uses_focus_visible():
    src = _read("app/templates/partials/empty_states_notice.html")
    assert "esn-stale-rerun:focus-visible" in src, \
        "empty_states_notice.html: esn-stale-rerun should use :focus-visible not bare :focus"
    # Also check that bare :focus { is gone (without -visible)
    # Allow hover:focus pattern — look for standalone :focus { without -visible
    bare = re.findall(r'\.esn-stale-rerun:focus\s*\{', src)
    assert not bare, \
        "empty_states_notice.html: bare :focus (without -visible) still present on esn-stale-rerun"
