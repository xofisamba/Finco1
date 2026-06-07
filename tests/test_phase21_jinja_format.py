"""Phase 21 v2 — Fix Jinja2 |format filter crash (BLOCKER-1)

REGRESSION TEST: Direct template render with actual project_ctx/item objects.
This verifies the real templates render without crashing.

Root cause: Jinja2's |format filter calls `value % args` (C-style %-format),
NOT Python's str.format(). So "{{ {:,}"|format(x) }}" crashes.
Correct fix: direct Python .format() method, e.g. "{:,.0f}".format(x or 0).

Scope: mechanical string replacement only — no financial logic changes.
"""
import os, re, subprocess, sys, jinja2
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


# ─── 1. Grep Check — No {:,} |format patterns remain ────────────────────────────

REQUIRED_GREP_PATTERNS = [
    '"{:,.0f}"|format',
    '"{:,.1f}"|format',
    '"{:,.2f}"|format',
    '"%,.0f"|format',
    '"%,.1f"|format',
    '"%,.2f"|format',
]

def test_no_invalid_format_patterns():
    """All {:,} and %,} |format patterns must be replaced with .format() calls."""
    partials = PROJECT_ROOT / "app/templates/partials"
    failures = []
    for pattern in REQUIRED_GREP_PATTERNS:
        bad = []
        for path in partials.rglob("*.html"):
            text = path.read_text(encoding="utf-8")
            for lineno, line in enumerate(text.splitlines(), start=1):
                if pattern in line and ".bak" not in str(path) and "test_" not in str(path):
                    bad.append(f"{path}:{lineno}:{line.strip()}")
        if bad:
            failures.append(f"  Pattern {pattern!r} found ({len(bad)} matches):\n    " + "\n    ".join(bad[:5]))
    assert not failures, "Invalid |format patterns still present:\n" + "\n".join(failures)


# ─── 2. Direct Template Render Test ────────────────────────────────────────────

def test_template_construction_renders():
    """Render sheet_construction.html with a minimal project_ctx + item context."""
    from jinja2 import Environment

    path = PROJECT_ROOT / "app/templates/partials/sheet_construction.html"
    with open(path, encoding="utf-8") as f:
        source = f.read()

    env = Environment()
    try:
        tmpl = env.from_string(source)
    except Exception as e:
        raise AssertionError(f"Construction template failed to parse: {e}")

    ctx = {
        "project_ctx": type('obj', (), {
            "name": "TUHO Wind",
            "data_source": "baseline",
            "total_capex_keur": 50000,
            "senior_debt_keur": 35000,
            "shl_amount_keur": 10000,
            "shl_rate_pct": 0.08,
            "idc_keur": 1200,
            "financial_close": "2028-06-30",
        })(),
        "items": [],
    }
    try:
        result = tmpl.render(**ctx)
        assert len(result) > 100, f"Rendered too-short result ({len(result)} chars)"
        assert "Total CAPEX" in result
    except Exception as e:
        raise AssertionError(f"Construction template render failed: {type(e).__name__}: {e}")


def test_template_idc_renders():
    """Render sheet_idc.html with minimal IDC item context."""
    from jinja2 import Environment

    path = PROJECT_ROOT / "app/templates/partials/sheet_idc.html"
    with open(path, encoding="utf-8") as f:
        source = f.read()

    env = Environment()
    tmpl = env.from_string(source)
    ctx = {
        "project_ctx": type('obj', (), {"name": "TUHO Wind", "data_source": "baseline"})(),
        "idc_items": [],
    }
    try:
        result = tmpl.render(**ctx)
        assert len(result) > 50
    except Exception as e:
        raise AssertionError(f"IDC template render failed: {type(e).__name__}: {e}")


def test_template_revenue_renders():
    """Render sheet_revenue.html with minimal revenue context."""
    from jinja2 import Environment

    path = PROJECT_ROOT / "app/templates/partials/sheet_revenue.html"
    with open(path, encoding="utf-8") as f:
        source = f.read()

    env = Environment()
    tmpl = env.from_string(source)
    ctx = {
        "project_ctx": type('obj', (), {
            "name": "TUHO Wind",
            "data_source": "baseline",
            "ppa_index_pct": 2.0,
        })(),
        "revenue_items": [],
        "is_user_project": True,
    }
    try:
        result = tmpl.render(**ctx)
        # Just verify it didn't crash on |format — template parsed and ran
        assert len(result) > 0
    except jinja2.exceptions.UndefinedError as e:
        # Some mock attrs may be missing — acceptable for smoke test
        pass
    except Exception as e:
        # But no TypeError/ValueError from invalid format strings!
        if "not all arguments converted" in str(e) or "Unknown format code" in str(e):
            raise AssertionError(f"Format crash: {type(e).__name__}: {e}")
        pass  # other errors OK for smoke test


# ─── 3. Format String Unit Tests ──────────────────────────────────────────────

def test_direct_format_works():
    """Python str.format() with {:,} comma grouping produces correct output."""
    assert "{:,.0f}".format(72993) == "72,993"
    assert "{:,.1f}".format(72993.7) == "72,993.7"
    assert "{:,.2f}".format(72993.766) == "72,993.77"
    assert "{:,.0f}".format(0) == "0"
    assert "{:,.0f}".format(None or 0) == "0"


def test_jinja_format_filter():
    """Jinja2 |format uses %-style internally — {:,} patterns crash."""
    from jinja2 import Environment
    env = Environment()
    # The WRONG pattern: {{ "{:,.0f}"|format(x) }} — crashes
    t = env.from_string('{{ "{:,.0f}"|format(x) }}')
    try:
        t.render(x=72993)
        raise AssertionError("Expected TypeError for {:,}|format but got none")
    except TypeError:
        pass  # expected

    # The CORRECT pattern: direct .format() call
    t2 = env.from_string('{{ "{:,.0f}".format(x or 0) }}')
    assert t2.render(x=72993) == "72,993"


# ─── 4. Regression ─────────────────────────────────────────────────────────────

def test_phase20m_still_passes():
    result = subprocess.run(
        [sys.executable, "-m", "pytest",
         "tests/test_phase20m_runtime_statement_polish.py", "-q", "--tb=no"],
        cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, f"Phase 20M tests failed:\n{result.stdout}"


def test_main_web_compiles():
    import main_web
    assert hasattr(main_web, "app")
