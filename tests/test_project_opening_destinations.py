"""Navigation destination guard — fails if a hardcoded project-opening URL
appears outside approved locations.

Uses literal substring scanning (not regex) for clarity and correctness.
"""
import pathlib

REPO_ROOT = pathlib.Path(__file__).parent.parent

# Forbidden literal substrings in Python source (non-comment, non-docstring lines)
FORBIDDEN_LITERALS = [
    "/?project=",
    "/v2/workbook?project=",
]

# Forbidden literal substrings as href values in HTML templates
FORBIDDEN_HREF_LITERALS = [
    'href="/?project=',
    "href='/?project=",
    'href="/v2/workbook?project=',
    "href='/v2/workbook?project=",
]

# Python source exceptions (narrow, documented)
PYTHON_APPROVED = {
    "app/utils/workbook_flag.py",   # The helper itself — produces these URLs
    "app/v2/router.py",             # Internal V2-self-redirects (post-update, run, error)
    "app/v2/capex_router.py",       # Internal V2-self-redirects (post-capex-update)
    "app/v2/opex_router.py",        # Internal V2-self-redirects (post-opex-update)
}

# Template exceptions — legacy rollback surface only
# project_selector.html and project_browser.html contain hardcoded /?project= hrefs
# via window.location.href JS (not href= attributes), so they do NOT appear in
# FORBIDDEN_HREF_LITERALS scans. Keeping these as exceptions for documentation.
TEMPLATE_APPROVED = {
    "app/templates/partials/project_selector.html",
    "app/templates/partials/project_browser.html",
}


def _python_code_lines(text: str):
    """Yield (lineno, line) for lines that are not inside triple-quoted strings or comments."""
    in_triple = None  # None, '"""', or "'''"
    for lineno, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if in_triple:
            # Check if the triple-quote ends on this line
            if in_triple in raw:
                in_triple = None
            continue  # skip docstring body lines
        # Check if a triple-quote opens on this line
        for marker in ('"""', "'''"):
            if marker in raw:
                count = raw.count(marker)
                if count % 2 == 1:
                    # Odd number = opens but doesn't close on this line
                    in_triple = marker
                    break
        # Skip pure comment lines and blank lines
        if not stripped or stripped.startswith("#"):
            continue
        yield lineno, raw


def test_no_hardcoded_project_urls_in_python():
    """Hardcoded /?project= or /v2/workbook?project= must not appear in
    Python source outside PYTHON_APPROVED files."""
    violations = []
    search_roots = [
        REPO_ROOT / "app",
        REPO_ROOT / "main_web.py",
    ]
    py_files = []
    for root in search_roots:
        if root.is_file():
            py_files.append(root)
        else:
            py_files.extend(root.rglob("*.py"))

    for fpath in py_files:
        rel = str(fpath.relative_to(REPO_ROOT))
        if any(rel == a or rel.endswith("/" + a) for a in PYTHON_APPROVED):
            continue
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for lineno, line in _python_code_lines(text):
            for lit in FORBIDDEN_LITERALS:
                if lit in line:
                    violations.append(f"{rel}:{lineno}: {line.rstrip()}")
                    break

    assert not violations, (
        "Hardcoded project-opening URLs found — use project_workbook_url() instead:\n"
        + "\n".join(violations)
    )


def test_no_hardcoded_project_urls_in_templates():
    """Jinja2 templates must not have hardcoded href='/?project=' outside
    TEMPLATE_APPROVED files."""
    violations = []
    template_dir = REPO_ROOT / "app" / "templates"
    for fpath in template_dir.rglob("*.html"):
        rel = str(fpath.relative_to(REPO_ROOT))
        if any(rel == a or rel.endswith("/" + a.split("/")[-1]) for a in TEMPLATE_APPROVED):
            continue
        try:
            lines = fpath.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        for lineno, line in enumerate(lines, 1):
            for lit in FORBIDDEN_HREF_LITERALS:
                if lit in line:
                    violations.append(f"{rel}:{lineno}: {line.rstrip()}")
                    break

    assert not violations, (
        "Hardcoded project URLs in templates — use server-side url variables instead:\n"
        + "\n".join(violations)
    )


def test_guard_detects_literal_href_violation():
    """Guard must flag literal /?project= in an href."""
    violation_line = '  <a href="/?project=test">link</a>'
    flagged = any(lit in violation_line for lit in FORBIDDEN_HREF_LITERALS)
    assert flagged, "Guard did not detect /?project= href violation"
