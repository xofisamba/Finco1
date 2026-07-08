"""
Sprint 14D — CAPEX grid rebuild guardrails.

Verifies:
- C.01 through C.18 category codes present in sheet_capex.html
- Summary strip (Hard CAPEX / Financing / Total CAPEX) present
- Grid wrapper rendered with proper class for scroll/sticky
- No blank grid (lig_render macro called)
- CAPEX/MW metric present
- No engine/calculation changes
"""
from pathlib import Path

REPO = Path(__file__).parent.parent


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def test_capex_c01_through_c18_groups():
    src = _read("app/templates/partials/sheet_capex.html")
    for code in ["C.01", "C.02", "C.03", "C.04", "C.05", "C.06",
                 "C.07", "C.08", "C.09", "C.10", "C.11", "C.12",
                 "C.13", "C.14", "C.15", "C.16", "C.17", "C.18"]:
        assert code in src, \
            f"sheet_capex.html: CAPEX category {code} not found"


def test_capex_summary_strip_present():
    src = _read("app/templates/partials/sheet_capex.html")
    assert "capex-summary-strip" in src, \
        "sheet_capex.html: capex-summary-strip missing"
    assert "Hard CAPEX" in src, \
        "sheet_capex.html: Hard CAPEX label missing"
    assert "Total CAPEX" in src, \
        "sheet_capex.html: Total CAPEX label missing"


def test_capex_grid_wrapper_present():
    src = _read("app/templates/partials/sheet_capex.html")
    assert "fc-capex-grid-wrapper" in src, \
        "sheet_capex.html: fc-capex-grid-wrapper not found"
    assert "capex-single-sheet" in src, \
        "sheet_capex.html: capex-single-sheet ID missing"


def test_capex_grid_rendered_via_macro():
    src = _read("app/templates/partials/sheet_capex.html")
    assert "lig_render" in src, \
        "sheet_capex.html: lig_render macro not called — grid may be blank"


def test_capex_mw_metric_present():
    src = _read("app/templates/partials/sheet_capex.html")
    assert "CAPEX / MW" in src or "capex_mw" in src.lower() or "capacity_mw" in src, \
        "sheet_capex.html: CAPEX/MW metric not found"


def test_capex_css_sticky_improvements():
    css = _read("static/styles.css")
    assert "fc-capex-grid-wrapper" in css, \
        "styles.css: fc-capex-grid-wrapper rule missing"
    assert "overflow-y" in css, \
        "styles.css: overflow-y (vertical scroll) not set"


def test_capex_no_engine_changes():
    """Confirm waterfall_core.py not modified in this sprint."""
    import subprocess
    result = subprocess.run(
        ["git", "diff", "HEAD~5", "--name-only"],
        cwd=str(REPO), capture_output=True, text=True
    )
    changed = result.stdout
    assert "waterfall_core.py" not in changed, \
        "waterfall_core.py was modified — engine changes are forbidden in Sprint 14"
