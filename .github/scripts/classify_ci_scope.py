#!/usr/bin/env python3
"""
CI scope classifier — xofisamba/Finco1.

Classifies a PR diff into one of four mutually-exclusive outputs:

  ui_only=true          Only presentation/template/UI files changed.
                        No financial engine regression required.
  docs_only=true        Only documentation / markdown files changed.
  workflow_only=true    Only .github/ files changed.
  engine_sensitive=true Engine authority, domain, service, persistence,
                        workbook, or unknown files changed.
                        Full engine authority regression must run.

ONE of the four is set to 'true'; the others are 'false'.
Default (unknown/mixed/empty): engine_sensitive=true.

Classification is FAIL-SAFE:
  - Any unrecognised path → engine_sensitive=true
  - Any mix containing a non-UI path → engine_sensitive=true
  - Classification errors → engine_sensitive=true

Usage:
  python3 classify_ci_scope.py --base <sha> --head <sha>
  python3 classify_ci_scope.py --files file1.py file2.html   (for tests)

Outputs GitHub Actions output format (KEY=VALUE, one per line).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import PurePosixPath

# ── Frozen authority paths ────────────────────────────────────────────────────
# ANY change to a file matching these prefixes → engine_sensitive=true.
FROZEN_AUTHORITY_PREFIXES = (
    "financial_engine/",
    "finco_core/",
    "domain/",
    "app/api/",
    "app/services/",
    "app/persistence/",
    "app/workbook/",
    "app/project_factories",
    "constraints.txt",
)

# ── Safe UI-only prefixes ─────────────────────────────────────────────────────
# ALL changed files must match one of these for ui_only=true.
SAFE_UI_PREFIXES = (
    "app/templates/",
    "app/v2/",
    "app/v1/",
    "static/",
)

SAFE_UI_PATTERNS = (
    re.compile(r"^tests/test_ui"),
    re.compile(r"^tests/test_htmx"),
    re.compile(r"^tests/test_phase57pre_route_render_smoke\.py$"),
    re.compile(r"^tests/test_workbook"),
)

# ── Documentation-only patterns ───────────────────────────────────────────────
DOCS_PREFIXES = ("docs/",)
DOCS_PATTERNS = (
    re.compile(r"^README"),
    re.compile(r"^CHANGELOG"),
    re.compile(r"^[^/]+\.md$"),
    re.compile(r"^[^/]+\.txt$", re.I),  # top-level txt files (non-constraints)
)

# ── Workflow-only patterns ────────────────────────────────────────────────────
WORKFLOW_PREFIXES = (".github/",)


# ─────────────────────────────────────────────────────────────────────────────

def _classify_file(path: str) -> str:
    """
    Return one of: 'frozen_authority', 'ui_only', 'docs_only', 'workflow_only',
    'engine_sensitive' (catch-all for anything not explicitly categorised).
    """
    # Frozen authority always wins — check first.
    for prefix in FROZEN_AUTHORITY_PREFIXES:
        if path.startswith(prefix):
            return "frozen_authority"  # strong engine_sensitive signal

    # Workflow files
    for prefix in WORKFLOW_PREFIXES:
        if path.startswith(prefix):
            return "workflow_only"

    # Documentation / markdown
    for prefix in DOCS_PREFIXES:
        if path.startswith(prefix):
            return "docs_only"
    for pat in DOCS_PATTERNS:
        if pat.match(path):
            # Don't count constraints.txt as docs
            if path == "constraints.txt":
                return "engine_sensitive"
            return "docs_only"

    # Safe UI paths
    for prefix in SAFE_UI_PREFIXES:
        if path.startswith(prefix):
            return "ui_only"
    for pat in SAFE_UI_PATTERNS:
        if pat.match(path):
            return "ui_only"

    # Everything else is engine_sensitive (fail-safe)
    return "engine_sensitive"


def classify(files: list[str]) -> dict[str, str]:
    """
    Classify a list of changed files into CI scope outputs.

    Returns a dict of output key→value strings (GitHub Actions format).
    """
    if not files:
        # Empty diff — treat as workflow/docs change (safe)
        return {
            "ui_only": "false",
            "docs_only": "false",
            "workflow_only": "true",
            "engine_sensitive": "false",
            "changed_files": "0",
            "reason": "empty diff — classified as workflow-only (safe)",
        }

    categories = {_classify_file(f) for f in files}
    changed = str(len(files))

    # Any frozen authority file → engine_sensitive, full stop.
    if "frozen_authority" in categories or "engine_sensitive" in categories:
        changed_ea = [f for f in files if _classify_file(f) in ("frozen_authority", "engine_sensitive")]
        return {
            "ui_only": "false",
            "docs_only": "false",
            "workflow_only": "false",
            "engine_sensitive": "true",
            "changed_files": changed,
            "reason": f"engine-sensitive or frozen-authority files changed: {changed_ea[:5]}",
        }

    unique = categories - {"frozen_authority", "engine_sensitive"}

    # Pure UI-only
    if unique == {"ui_only"}:
        return {
            "ui_only": "true",
            "docs_only": "false",
            "workflow_only": "false",
            "engine_sensitive": "false",
            "changed_files": changed,
            "reason": "all changed files are UI/template/presentation paths",
        }

    # Pure docs-only
    if unique == {"docs_only"}:
        return {
            "ui_only": "false",
            "docs_only": "true",
            "workflow_only": "false",
            "engine_sensitive": "false",
            "changed_files": changed,
            "reason": "all changed files are documentation",
        }

    # Pure workflow-only
    if unique == {"workflow_only"}:
        return {
            "ui_only": "false",
            "docs_only": "false",
            "workflow_only": "true",
            "engine_sensitive": "false",
            "changed_files": changed,
            "reason": "all changed files are .github/ workflow/script files",
        }

    # Mixed safe categories (e.g. ui_only + docs_only + workflow_only) → ui_only wins
    # as long as no engine-sensitive file is present (already handled above).
    has_ui = "ui_only" in unique
    has_docs = "docs_only" in unique
    has_wf = "workflow_only" in unique
    if has_ui and not (categories - {"ui_only", "docs_only", "workflow_only"}):
        return {
            "ui_only": "true",
            "docs_only": "false",
            "workflow_only": "false",
            "engine_sensitive": "false",
            "changed_files": changed,
            "reason": "all changed files are UI/docs/workflow (no engine authority)",
        }

    # Any other combination → engine_sensitive (fail-safe)
    return {
        "ui_only": "false",
        "docs_only": "false",
        "workflow_only": "false",
        "engine_sensitive": "true",
        "changed_files": changed,
        "reason": f"unclassified file categories {unique!r} — defaulting to engine_sensitive",
    }


def get_changed_files(base: str, head: str) -> list[str]:
    """Return list of changed file paths between base and head."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{base}...{head}"],
            capture_output=True, text=True, check=True,
        )
        files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
        if not files:
            # Fallback: diff against direct parent
            result2 = subprocess.run(
                ["git", "diff", "--name-only", f"{base}..{head}"],
                capture_output=True, text=True, check=True,
            )
            files = [f.strip() for f in result2.stdout.splitlines() if f.strip()]
        return files
    except subprocess.CalledProcessError as exc:
        print(f"WARNING: git diff failed: {exc.stderr}", file=sys.stderr)
        # Fail-safe: return a sentinel that triggers engine_sensitive
        return ["UNKNOWN_GIT_DIFF_ERROR"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--base", metavar="SHA", help="Base commit SHA")
    group.add_argument("--files", nargs="+", metavar="FILE",
                       help="Explicit file list (for tests / dry-run)")
    parser.add_argument("--head", metavar="SHA",
                        help="Head commit SHA (required with --base)")
    args = parser.parse_args(argv)

    if args.files:
        files = args.files
    else:
        if not args.head:
            parser.error("--head is required when --base is given")
        files = get_changed_files(args.base, args.head)

    result = classify(files)

    # Emit GitHub Actions output format
    for key, value in result.items():
        print(f"{key}={value}")

    # Also print a human-readable summary to stderr
    scope = (
        "ENGINE_SENSITIVE" if result["engine_sensitive"] == "true"
        else "UI_ONLY" if result["ui_only"] == "true"
        else "DOCS_ONLY" if result["docs_only"] == "true"
        else "WORKFLOW_ONLY"
    )
    print(
        f"\nCI scope: {scope} | {result['changed_files']} file(s) changed",
        file=sys.stderr,
    )
    print(f"Reason: {result['reason']}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
