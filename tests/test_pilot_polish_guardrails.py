"""
Pilot Polish — Static guardrails.

Prevents regressions on:
  • KPI strip always renders six fo-kpi cells (never collapses to message-only)
  • Each analysis tab has a proper empty state (no internal API hints)
  • Project selector sidebar has no duplicate navigation concepts
  • New project template options don't expose dev-facing warning copy
  • Empty-state "No Sensitivity Loaded" / "No Lender Case Loaded" / etc. removed
"""

import re
from pathlib import Path

REPO = Path(__file__).parent.parent


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Part 2 — KPI ribbon always renders six cells
# ---------------------------------------------------------------------------

def test_kpi_strip_always_has_six_cells():
    src = _read("app/templates/partials/_kpi_strip.html")
    # The six data-fo-kpi attributes must all be present unconditionally
    for kpi in ("project-irr", "equity-irr", "npv", "min-dscr", "avg-dscr", "llcr"):
        assert f'data-fo-kpi="{kpi}"' in src, \
            f"_kpi_strip.html: data-fo-kpi=\"{kpi}\" cell not found — strip may collapse"


def test_kpi_strip_no_runtime_message_inside_conditional():
    src = _read("app/templates/partials/_kpi_strip.html")
    # Strip HTML/Jinja comments before checking rendered output
    src_no_comments = re.sub(r'\{#.*?#\}', '', src, flags=re.DOTALL)
    # The old single-cell collapse element must be gone from rendered output
    assert "fo-kpi--no-run" not in src_no_comments, \
        "_kpi_strip.html: old fo-kpi--no-run single-message cell still present in rendered output"
    assert 'class="fo-kpi fo-kpi--no-run"' not in src, \
        "_kpi_strip.html: old fo-kpi--no-run div still present"


def test_kpi_strip_has_hint_element():
    src = _read("app/templates/partials/_kpi_strip.html")
    assert "fo-kpi__hint" in src, \
        "_kpi_strip.html: fo-kpi__hint element not present for no-runtime sub-label"


def test_chrome_css_has_kpi_hint_rule():
    src = _read("static/chrome.css")
    assert ".fo-kpi__hint" in src, \
        "chrome.css: .fo-kpi__hint rule missing"


# ---------------------------------------------------------------------------
# Part 3 — Demo project template options don't expose internal dev copy
# ---------------------------------------------------------------------------

def test_new_project_options_no_warning_emoji():
    src = _read("main_web.py")
    # Find the NEW_PROJECT_TEMPLATE_OPTIONS block
    idx = src.find("NEW_PROJECT_TEMPLATE_OPTIONS")
    assert idx != -1, "main_web.py: NEW_PROJECT_TEMPLATE_OPTIONS not found"
    block = src[idx:idx+400]
    assert "⚠️ Unvalidated" not in block, \
        "main_web.py: NEW_PROJECT_TEMPLATE_OPTIONS still contains '⚠️ Unvalidated' dev copy"
    assert "Derived path" not in block, \
        "main_web.py: NEW_PROJECT_TEMPLATE_OPTIONS still contains 'Derived path' dev copy"


# ---------------------------------------------------------------------------
# Part 4 — Sidebar navigation simplified (no duplicate concepts)
# ---------------------------------------------------------------------------

def test_sidebar_no_all_projects_button():
    src = _read("app/templates/partials/project_selector.html")
    assert "All projects" not in src, \
        "project_selector.html: 'All projects' button still present alongside 'Home'"


def test_sidebar_projects_button_exists():
    src = _read("app/templates/partials/project_selector.html")
    assert "Projects" in src, \
        "project_selector.html: 'Projects' navigation button not found"


# ---------------------------------------------------------------------------
# Part 5 — Empty states: no internal copy / developer wording
# ---------------------------------------------------------------------------

def test_sensitivity_no_internal_empty_state():
    src = _read("app/templates/partials/scenario_sensitivity.html")
    assert "No Sensitivity Loaded" not in src, \
        "scenario_sensitivity.html: 'No Sensitivity Loaded' internal copy still present"
    assert "Generate analysis" not in src.lower() or "No model results" in src, \
        "scenario_sensitivity.html: empty state should use standard 'No model results available' copy"


def test_lender_no_internal_empty_state():
    src = _read("app/templates/partials/lender_case.html")
    assert "No Lender Case Loaded" not in src, \
        "lender_case.html: 'No Lender Case Loaded' internal copy still present"
    assert "GET /scenarios/lender-case" not in src, \
        "lender_case.html: internal URL hint still in empty state"


def test_bess_no_internal_empty_state():
    src = _read("app/templates/partials/bess_revenue_breakdown.html")
    assert "No BESS Revenue Data" not in src, \
        "bess_revenue_breakdown.html: 'No BESS Revenue Data' internal copy still present"


def test_exec_summary_no_internal_empty_state():
    src = _read("app/templates/partials/exec_summary.html")
    assert "No Executive Summary Loaded" not in src, \
        "exec_summary.html: 'No Executive Summary Loaded' internal copy still present"
    assert "/scenarios/exec-summary?project=" not in src, \
        "exec_summary.html: internal URL hint still in empty state"


def test_standard_empty_state_copy_present():
    """All analysis tabs must use the standard 'No model results available' copy."""
    for rel in (
        "app/templates/partials/scenario_sensitivity.html",
        "app/templates/partials/lender_case.html",
        "app/templates/partials/bess_revenue_breakdown.html",
        "app/templates/partials/exec_summary.html",
    ):
        src = _read(rel)
        assert "No model results available" in src, \
            f"{rel}: standard 'No model results available' empty-state title not found"
