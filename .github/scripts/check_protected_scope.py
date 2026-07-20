#!/usr/bin/env python3
"""check_protected_scope.py — Narrow governance check for protected production files.

Recon Fix 01 approval: exactly one declarative ppa_indexation_start_policy assignment
added to create_default_oborovo() in app/project_factories.py.

Rules:
  - app/project_factories.py is the ONLY approved protected file for this PR.
  - No other protected-scope file may be changed.
  - No production lines may be REMOVED from project_factories.py.
  - The only approved non-comment, non-blank addition is:
        ppa_indexation_start_policy="FIRST_FULL_CALENDAR_YEAR_AS_BASE",
    and it must appear in exactly one location in the diff (the Oborovo factory).
  - The approved addition must not be mixed with other executable content on
    the same logical line.
  - Duplicate assignments (same pattern appearing more than once as an addition)
    are rejected.

Usage:
    python3 check_protected_scope.py <base_ref> <head_ref>

Exit codes:
    0 — All protected-scope changes are within the approved set.
    1 — Unexpected protected-scope changes detected.
"""
from __future__ import annotations

import subprocess
import sys

PROTECTED_SCOPE = [
    "app/",
    "domain/",
    "main_web.py",
    "main_api.py",
    "finco_core/waterfall/",
]

# The only file allowed to change in protected scope for Recon Fix 01.
_APPROVED_FILE = "app/project_factories.py"

# The only approved addition pattern (must appear exactly once, standalone).
_APPROVED_ADDITION = 'ppa_indexation_start_policy="FIRST_FULL_CALENDAR_YEAR_AS_BASE"'

# The factory function that owns the approved change.
_APPROVED_FACTORY = "def create_default_oborovo"


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()


def get_changed_protected_files(base: str, head: str) -> list[str]:
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


def _is_blank_or_comment(content: str) -> bool:
    """True if the line content (after stripping leading +/- and whitespace) is blank or a comment."""
    return not content or content.startswith("#")


def check_factories_diff(diff: str) -> tuple[bool, list[str]]:
    """Inspect the diff for app/project_factories.py.

    Returns (approved, [error_messages]).

    Approval requires ALL of:
    1. No removed production lines (lines starting with '-', excluding '---' header).
    2. All added lines are blank, comments, or contain _APPROVED_ADDITION.
    3. The approved addition appears exactly once in added lines.
    4. The approved addition must be the only executable content on its line
       (no extra statements or identifiers beside it).
    5. The addition must appear in the _APPROVED_FACTORY hunk context.
    """
    errors: list[str] = []
    addition_count = 0
    in_approved_factory = False

    for line in diff.split("\n"):
        # Track which factory function we are inside based on context/hunk lines.
        # Context lines (not starting with + or -) reveal the surrounding code.
        if not line.startswith("+") and not line.startswith("-"):
            if _APPROVED_FACTORY in line:
                in_approved_factory = True
            elif line.startswith("diff ") or line.startswith("@@"):
                # New hunk — reset factory context; check hunk header for factory name.
                if "@@" in line and _APPROVED_FACTORY not in line:
                    in_approved_factory = False
            continue

        # Skip diff header lines.
        if line.startswith("---") or line.startswith("+++"):
            continue

        content = line[1:].strip()  # strip leading +/- and whitespace

        if line.startswith("-"):
            # Removed line: blank/comment removals are acceptable (e.g. reformatting).
            if _is_blank_or_comment(content):
                continue
            errors.append(f"Unapproved removed production line: {line!r}")
            continue

        # Added line (starts with +).
        if _is_blank_or_comment(content):
            continue

        if _APPROVED_ADDITION not in content:
            errors.append(f"Unapproved added line: {line!r}")
            continue

        # Line contains the approved addition. Check it is not mixed with other executable content.
        # Strip the approved pattern itself and any surrounding punctuation/whitespace.
        remainder = content.replace(_APPROVED_ADDITION, "").replace(",", "").strip()
        if remainder:
            errors.append(
                f"Approved pattern found but mixed with extra executable content: {line!r}"
            )
            continue

        # Verify the addition is in the Oborovo factory context.
        if not in_approved_factory:
            errors.append(
                f"Approved pattern found outside {_APPROVED_FACTORY}(): {line!r}"
            )
            continue

        addition_count += 1

    if addition_count == 0 and not errors:
        errors.append(
            f"Expected exactly one addition of {_APPROVED_ADDITION!r} "
            f"in {_APPROVED_FACTORY}(), but found none."
        )
    elif addition_count > 1:
        errors.append(
            f"Duplicate approved addition: {_APPROVED_ADDITION!r} appears "
            f"{addition_count} times. Only one (in {_APPROVED_FACTORY}()) is approved."
        )

    return len(errors) == 0, errors


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

    # Only app/project_factories.py is approved for Recon Fix 01.
    unapproved_files = [f for f in protected_changed if f != _APPROVED_FILE]
    if unapproved_files:
        print(
            "ERROR: Protected files changed that are not approved for Recon Fix 01:\n"
            + "\n".join(f"  {f}" for f in unapproved_files),
            file=sys.stderr,
        )
        return 1

    if len(protected_changed) > 1:
        print(
            f"ERROR: Multiple protected files changed. Only {_APPROVED_FILE} "
            f"is approved for Recon Fix 01. Changed: {protected_changed}",
            file=sys.stderr,
        )
        return 1

    diff = get_diff_for_file(base, head, _APPROVED_FILE)
    approved, errors = check_factories_diff(diff)

    if not approved:
        print(
            f"ERROR: {_APPROVED_FILE} diff fails Recon Fix 01 governance:\n"
            + "\n".join(f"  {e}" for e in errors),
            file=sys.stderr,
        )
        print(
            "\nApproved changes for Recon Fix 01:\n"
            f"  - Exactly one addition of {_APPROVED_ADDITION!r}\n"
            f"    inside {_APPROVED_FACTORY}()\n"
            "  - Comment lines (starting with #) or blank lines only\n"
            "  - No removed production lines\n"
            "  - No duplicate assignments\n"
            "  - No extra executable content on the approved line\n"
            "  - No other protected file may be changed",
            file=sys.stderr,
        )
        return 1

    print(
        f"Protected production scope: {_APPROVED_FILE} changed within Recon Fix 01 "
        f"approved narrow surface (exactly one declarative ppa_indexation_start_policy "
        f"assignment in {_APPROVED_FACTORY}())."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
