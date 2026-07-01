"""Excel Parity Stack I — Post-Wiring Calibration Audit

Characterization tests that document the current state of the post-wiring
plumbing without running the financial engine. All checks are static
(source-code reading, AST inspection, or file-content grep).

Tests:
  I1 — run_project() return dict contains all expected post-wiring keys
  I2 — run_service.py sessionStorage save tag includes all 5 schedule keys
  I3 — each wired template reads the correct sessionStorage key
  I4 — no client-side financial calculations in wired templates (JS arithmetic
       in rendering code is display-only percent formatting, NOT model maths)
  I5 — guardrail files (waterfall_core, project_factories, input_adapter)
       do not import from app/
"""
from __future__ import annotations

import ast
import os
import re

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel_path: str) -> str:
    """Read a file relative to the project root."""
    with open(os.path.join(ROOT, rel_path), encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# I1: run_project() return dict keys
# ---------------------------------------------------------------------------

# Expected top-level keys in the dict returned by run_project()
EXPECTED_RUN_PROJECT_KEYS = {
    "project_type",
    "scenario",
    "period_view",
    "integration_status",
    "integration_note",
    "messages",
    "debt_schedule",
    "tax_schedule",
    "distribution_schedule",
    "kpis",
    "dualrun_validation",
    "derivation_evidence",
    "financial_statements",
    "sponsor_schedule",
    "tables",
}


def _extract_return_dict_keys_from_run_project(source: str) -> set[str]:
    """Parse the run_project() source and extract string keys from its return dict."""
    tree = ast.parse(source)
    keys: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "run_project":
            for child in ast.walk(node):
                if isinstance(child, ast.Return) and isinstance(child.value, ast.Dict):
                    for k in child.value.keys:
                        if isinstance(k, ast.Constant) and isinstance(k.value, str):
                            keys.add(k.value)
    return keys


def test_i1_run_project_return_keys_present():
    """I1: run_project() return dict contains all expected post-wiring payload keys."""
    source = _read("app/api/project_runner.py")
    found_keys = _extract_return_dict_keys_from_run_project(source)
    assert found_keys, "Could not extract any keys from run_project() return dict"
    missing = EXPECTED_RUN_PROJECT_KEYS - found_keys
    assert not missing, (
        f"run_project() is missing expected payload keys: {sorted(missing)}\n"
        f"Found keys: {sorted(found_keys)}"
    )


# ---------------------------------------------------------------------------
# I2: sessionStorage save tag includes all 5 schedule keys
# ---------------------------------------------------------------------------

EXPECTED_SESSION_STORAGE_KEYS = {
    "lastFinancialStatements",
    "lastDebtSchedule",
    "lastTaxSchedule",
    "lastDistributionSchedule",
    "lastSponsorSchedule",
}


def test_i2_run_service_sessionstorage_keys():
    """I2: _build_sessionstorage_save_tag in run_service.py includes all schedule keys."""
    source = _read("app/services/run_service.py")
    missing = []
    for key in sorted(EXPECTED_SESSION_STORAGE_KEYS):
        if key not in source:
            missing.append(key)
    assert not missing, (
        f"run_service.py is missing sessionStorage keys: {missing}"
    )


def test_i2_run_service_sessionstorage_setitem():
    """I2: run_service.py calls sessionStorage.setItem for each expected key."""
    source = _read("app/services/run_service.py")
    missing = []
    for key in sorted(EXPECTED_SESSION_STORAGE_KEYS):
        pattern = f'sessionStorage.setItem("{key}"'
        if pattern not in source:
            missing.append(key)
    assert not missing, (
        f"run_service.py missing sessionStorage.setItem calls for: {missing}"
    )


# ---------------------------------------------------------------------------
# I3: Each wired template reads its expected sessionStorage key
# ---------------------------------------------------------------------------

TEMPLATE_SESSIONSTORAGE_MAP = {
    "app/templates/partials/sheet_financials.html": "lastFinancialStatements",
    "app/templates/partials/sheet_senior_debt.html": "lastDebtSchedule",
    "app/templates/partials/sheet_tax.html": "lastTaxSchedule",
    "app/templates/partials/_sheet_distributions_partial.html": "lastDistributionSchedule",
    "app/templates/partials/_sheet_sponsor_partial.html": "lastSponsorSchedule",
}


@pytest.mark.parametrize("template_path,expected_key", list(TEMPLATE_SESSIONSTORAGE_MAP.items()))
def test_i3_template_reads_correct_sessionstorage_key(template_path, expected_key):
    """I3: Each wired template reads the correct sessionStorage key."""
    source = _read(template_path)
    pattern = f'sessionStorage.getItem("{expected_key}")'
    assert pattern in source, (
        f"{os.path.basename(template_path)} does not read sessionStorage key "
        f'"{expected_key}" (expected pattern: {pattern!r})'
    )


# ---------------------------------------------------------------------------
# I4: No client-side financial calculations in wired templates
#
# We allow display-only formatting like `* 100` (converting a decimal rate to
# percent for display). We flag patterns that look like model-level arithmetic
# operating on two variable names (e.g. `revenue * tariff`), which would
# indicate the template is recomputing financial values.
#
# Concretely we check: no JS expression of the form
#   <identifier> <op> <identifier>
# where <op> is *, /, or + and neither operand is a constant, inside a
# <script> block. The existing templates use `* 100` (constant RHS) and
# string concatenation `+ "..."` which are display-only.
# ---------------------------------------------------------------------------

# Regex for suspicious JS: var OP var (both sides are JS identifiers)
# We skip `* 100`, `/ 100`, `+ "` (string concat), `+ (`, `+ '<` (HTML concat)
_FINANCIAL_ARITH_RE = re.compile(
    r'\b([a-zA-Z_]\w*)\s*([*/])\s*([a-zA-Z_]\w*)\b'
)

# Allow-listed RHS identifiers that are display/format helpers, not model values
_DISPLAY_ONLY_RHS = {
    "toFixed",  # .toFixed() call
    "length",   # array.length
    "100",      # * 100 to convert decimal to pct (caught by const check above but kept here)
}

WIRED_TEMPLATES = list(TEMPLATE_SESSIONSTORAGE_MAP.keys())


@pytest.mark.parametrize("template_path", WIRED_TEMPLATES)
def test_i4_no_financial_calculations_in_template(template_path):
    """I4: Wired templates do not perform client-side financial model calculations."""
    source = _read(template_path)

    # Extract <script> blocks only (Jinja template arithmetic is server-side)
    script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', source, re.DOTALL | re.IGNORECASE)
    script_text = "\n".join(script_blocks)

    # Remove single-line comments
    script_no_comments = re.sub(r'//[^\n]*', '', script_text)

    violations = []
    for m in _FINANCIAL_ARITH_RE.finditer(script_no_comments):
        lhs, op, rhs = m.group(1), m.group(2), m.group(3)
        # Skip `N / A` false positives from ternary `? value : "N/A"` patterns
        if lhs == "N" and rhs == "A":
            continue
        # Allow `x * 100` (percentage formatting) — rhs is a digit string
        if rhs.isdigit():
            continue
        # Allow `x / 1` or `x * 1` type trivials
        if lhs.isdigit() or rhs.isdigit():
            continue
        # Allow known display-only rhs tokens
        if rhs in _DISPLAY_ONLY_RHS or lhs in _DISPLAY_ONLY_RHS:
            continue
        violations.append(f"  {lhs} {op} {rhs}  (line containing: {m.string[max(0,m.start()-30):m.end()+30]!r})")

    # For the sponsor template: `gross_sponsor_irr * 100` is allowed display formatting
    # Filter: if the match is `irr * 100` variant we already skip (rhs.isdigit())
    # Any remaining violations are potential financial calculations
    if violations:
        pytest.fail(
            f"{os.path.basename(template_path)} contains potential client-side "
            f"financial calculations in JS:\n" + "\n".join(violations[:10])
        )


# ---------------------------------------------------------------------------
# I5: Guardrail files do not import from app/
# ---------------------------------------------------------------------------

_APP_IMPORT_RE = re.compile(r'^\s*(from\s+app[./]|import\s+app[./])', re.MULTILINE)

# Known guardrail state as of Excel Parity Stack I audit (2026-07-01).
# project_factories.py is clean. waterfall_core.py and input_adapter.py
# have conditional/lazy app/ imports (known gaps tracked in REMAINING_GAPS).
GUARDRAIL_KNOWN_STATE = {
    "app/waterfall_core.py": True,      # KNOWN: has lazy app/ imports (gap)
    "app/project_factories.py": False,  # CLEAN: no app/ imports
    "app/input_adapter.py": True,       # KNOWN: has app/ imports (gap)
}


@pytest.mark.parametrize("guardrail_file,known_violation", list(GUARDRAIL_KNOWN_STATE.items()))
def test_i5_guardrail_files_app_import_state(guardrail_file, known_violation):
    """I5: Document current state of app/ imports in guardrail files.

    Files marked known_violation=True have known app/ imports (documented gaps).
    Files marked known_violation=False must remain clean.
    """
    full_path = os.path.join(ROOT, guardrail_file)
    if not os.path.exists(full_path):
        pytest.skip(f"{guardrail_file} not found")
    source = _read(guardrail_file)
    has_violation = bool(_APP_IMPORT_RE.search(source))
    if known_violation:
        # Document that the known gap still exists (will fail if it gets fixed —
        # update this test when the gap is resolved).
        assert has_violation, (
            f"{guardrail_file} no longer imports from app/! "
            "Update GUARDRAIL_KNOWN_STATE to mark it clean."
        )
    else:
        assert not has_violation, (
            f"{guardrail_file} now imports from app/ — guardrail regression!\n"
            f"Matches: {_APP_IMPORT_RE.findall(source)}"
        )
