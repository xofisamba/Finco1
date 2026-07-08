"""
Sprint 14E — OPEX grid rebuild guardrails.

Verifies:
- B.01-B.13 groups rendered via dynamic group loop
- OPEX/MW and OPEX/MWh KPI cards in summary strip
- Year columns Y1-Y10 present in table header
- Grid wrapper has horizontal scroll class
- Sticky column classes applied
- No engine/calculation changes
"""
from pathlib import Path

REPO = Path(__file__).parent.parent


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def test_opex_dynamic_group_loop():
    src = _read("app/templates/partials/sheet_opex.html")
    assert "seen_groups" in src, \
        "sheet_opex.html: dynamic group loop (seen_groups) missing"


def test_opex_kpi_opex_per_mw():
    src = _read("app/templates/partials/sheet_opex.html")
    assert "OPEX / MW" in src, \
        "sheet_opex.html: OPEX / MW KPI missing from summary strip"


def test_opex_kpi_opex_per_mwh():
    src = _read("app/templates/partials/sheet_opex.html")
    assert "OPEX / MWh" in src, \
        "sheet_opex.html: OPEX / MWh KPI missing from summary strip"


def test_opex_year_columns_in_header():
    src = _read("app/templates/partials/sheet_opex.html")
    assert "_opex_display_years" in src, \
        "sheet_opex.html: _opex_display_years loop variable missing"
    assert "opex-ws-yr-col" in src, \
        "sheet_opex.html: opex-ws-yr-col year column class missing"


def test_opex_grid_wrapper_for_scroll():
    src = _read("app/templates/partials/sheet_opex.html")
    assert "opex-ws-grid-wrapper" in src, \
        "sheet_opex.html: opex-ws-grid-wrapper missing (no horizontal scroll)"


def test_opex_summary_strip_present():
    src = _read("app/templates/partials/sheet_opex.html")
    assert "opex-ws-summary-strip" in src, \
        "sheet_opex.html: opex-ws-summary-strip missing"
    assert "Total OPEX Y1" in src, \
        "sheet_opex.html: Total OPEX Y1 label missing"


def test_opex_collapse_controls_present():
    src = _read("app/templates/partials/sheet_opex.html")
    assert "opexWsToggleGroup" in src, \
        "sheet_opex.html: opexWsToggleGroup JS function missing"
    assert "opexWsExpandAll" in src and "opexWsCollapseAll" in src, \
        "sheet_opex.html: Expand All / Collapse All buttons missing"


def test_opex_css_sticky_and_scroll():
    css = _read("static/styles.css")
    assert "opex-ws-grid-wrapper" in css, \
        "styles.css: opex-ws-grid-wrapper CSS missing"
    assert "opex-ws-col-label" in css, \
        "styles.css: opex-ws-col-label sticky column CSS missing"
    assert "opex-ws-yr-col" in css, \
        "styles.css: opex-ws-yr-col year column CSS missing"


def test_opex_no_engine_changes():
    """Confirm waterfall_core.py not modified."""
    import subprocess
    result = subprocess.run(
        ["git", "diff", "HEAD~6", "--name-only"],
        cwd=str(REPO), capture_output=True, text=True
    )
    assert "waterfall_core.py" not in result.stdout, \
        "waterfall_core.py modified — engine changes forbidden in Sprint 14"
