#!/usr/bin/env python3
"""check_protected_scope.py — Narrow governance check for protected production files.

Checks that the only protected-scope changes in a diff are explicitly approved.
Approved changes are hardcoded as a minimal set; anything outside fails.

Usage:
    python3 check_protected_scope.py <base_ref> <head_ref>

Exit codes:
    0 — All protected-scope changes are within the approved set (or no changes).
    1 — Unexpected protected-scope changes detected.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap

PROTECTED_SCOPE = [
    "app/",
    "domain/",
    "main_web.py",
    "main_api.py",
    "finco_core/waterfall/",
]

# ---------------------------------------------------------------------------
# Approved narrow changes for Recon Fix 01.
# Each entry is (file, approved_diff_pattern) where approved_diff_pattern is a
# substring that must be present in the added lines of the diff.
# The file must be the ONLY protected-scope file changed, and its diff must
# consist ONLY of lines matching the approved additions plus comment/blank lines.
# ---------------------------------------------------------------------------
_RECON_FIX_01_APPROVED: dict[str, list[str]] = {
    "app/project_factories.py": [
        # Oborovo: authoritative policy set to FIRST_FULL_CALENDAR_YEAR_AS_BASE
        'ppa_indexation_start_policy="FIRST_FULL_CALENDAR_YEAR_AS_BASE"',
        # TUHO: COD=Jan-1, identical to AFTER_OY but avoids intra-period validation
        'ppa_indexation_start_policy="FIRST_FULL_CALENDAR_YEAR_AS_BASE"',
        # Solar: COD=Jan-1, identical to AFTER_OY but avoids intra-period validation
        'ppa_indexation_start_policy="FIRST_FULL_CALENDAR_YEAR_AS_BASE"',
        # Wind: COD=Jul-1, governed B4 drift
        'ppa_indexation_start_policy="FIRST_FULL_CALENDAR_YEAR_AS_BASE"',
    ],
}

# When a protected file is changed but ONLY in ways that match the approved
# set below, it is allowed. All additions in the protected file diff must be
# either: empty/whitespace lines, comment lines (#), or lines that contain
# only approved content strings.
_APPROVED_ADDITION_PATTERNS = {
    "app/project_factories.py": {
        # Declarative policy field: only these strings are approved as additions.
        'ppa_indexation_start_policy="FIRST_FULL_CALENDAR_YEAR_AS_BASE"',
        # Comment lines approved by pattern (any comment is allowed for this file)
        # Marker: empty or whitespace-only lines
    }
}


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()


def get_changed_protected_files(base: str, head: str) -> list[str]:
    """Return protected-scope files changed between base and head."""
    changed_all = run(["git", "diff", "--name-only", f"{base}...{head}"])
    changed = changed_all.split("\n") if changed_all else []
    protected: list[str] = []
    for f in changed:
        if not f:
            continue
        for scope in PROTECTED_SCOPE:
            if f == scope or f.startswith(scope):
                protected.append(f)
                break
    return protected


def get_diff_for_file(base: str, head: str, filepath: str) -> str:
    return run(["git", "diff", f"{base}...{head}", "--", filepath])


def is_addition_approved(line: str, approved_patterns: set[str]) -> bool:
    """Check if an added diff line (stripped of the leading +) is approved."""
    stripped = line.lstrip("+").strip()
    # Empty lines and comment-only lines are always allowed
    if not stripped or stripped.startswith("#"):
        return True
    # Check against approved patterns
    return any(pat in stripped for pat in approved_patterns)


def check_file_diff_approved(filepath: str, diff: str) -> tuple[bool, list[str]]:
    """Return (approved, [violation_lines])."""
    approved_patterns = _APPROVED_ADDITION_PATTERNS.get(filepath)
    if approved_patterns is None:
        # File not in approved set at all
        return False, [f"File {filepath!r} has no approved-change entry."]

    violations: list[str] = []
    for line in diff.split("\n"):
        if not line.startswith("+") or line.startswith("+++"):
            continue  # context or removed lines
        if not is_addition_approved(line, approved_patterns):
            violations.append(line)
    return len(violations) == 0, violations


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: check_protected_scope.py <base_ref> <head_ref>", file=sys.stderr)
        return 1

    base, head = sys.argv[1], sys.argv[2]
    protected_changed = get_changed_protected_files(base, head)

    if not protected_changed:
        print("Protected production scope: unchanged")
        return 0

    print(f"Protected-scope files changed: {protected_changed}")

    # All changed files must be in the approved set
    unapproved_files = [f for f in protected_changed if f not in _APPROVED_ADDITION_PATTERNS]
    if unapproved_files:
        print(
            f"ERROR: Protected files changed that are not in the approved set:\n"
            + "\n".join(f"  {f}" for f in unapproved_files),
            file=sys.stderr,
        )
        return 1

    # Only app/project_factories.py is approved; check it's the only one changed
    if len(protected_changed) > 1:
        print(
            f"ERROR: Multiple protected files changed. Only app/project_factories.py "
            f"is approved for Recon Fix 01. Changed: {protected_changed}",
            file=sys.stderr,
        )
        return 1

    # Check the diff of the approved file
    filepath = protected_changed[0]
    diff = get_diff_for_file(base, head, filepath)
    approved, violations = check_file_diff_approved(filepath, diff)

    if not approved:
        print(
            f"ERROR: {filepath} contains unapproved changes beyond the Recon Fix 01 "
            f"declarative policy assignments.\n"
            f"Unapproved added lines:\n"
            + "\n".join(f"  {v}" for v in violations[:10]),
            file=sys.stderr,
        )
        print(
            textwrap.dedent("""
            Approved changes for Recon Fix 01:
              - ppa_indexation_start_policy="FIRST_FULL_CALENDAR_YEAR_AS_BASE" assignments
              - Comment lines (lines starting with #)
              - Empty lines
            Any formula, control-flow, dispatch, or other changes are NOT approved.
            """),
            file=sys.stderr,
        )
        return 1

    print(
        f"Protected production scope: {filepath} changed within Recon Fix 01 "
        f"approved narrow surface (declarative ppa_indexation_start_policy assignments only)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
