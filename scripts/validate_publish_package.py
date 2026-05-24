"""Validate scoped ZIP publish packages against an expected file list.

This is a developer utility only. It does not use git, network access, or
application runtime imports.
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import PurePosixPath


EXPECTED_FILES_HEADER = "## Expected Files"


class PackageValidationError(ValueError):
    """Raised when a publish package or manifest is invalid."""


def normalize_member_name(name: str) -> str:
    """Return a normalized relative ZIP member path or raise on unsafe paths."""
    if not name:
        raise PackageValidationError("ZIP entry path is empty.")

    normalized = name.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]

    if not normalized:
        raise PackageValidationError("ZIP entry path is empty after normalization.")
    if normalized.endswith("/"):
        raise PackageValidationError(f"Directory entries are not allowed: {name}")
    if normalized.startswith("/"):
        raise PackageValidationError(f"Absolute paths are not allowed: {name}")
    if re.match(r"^[A-Za-z]:/", normalized):
        raise PackageValidationError(f"Drive-qualified absolute paths are not allowed: {name}")

    path = PurePosixPath(normalized)
    parts = path.parts
    if any(part in ("..", "") for part in parts):
        raise PackageValidationError(f"Unsafe relative path is not allowed: {name}")

    return path.as_posix()


def parse_manifest_expected_files(manifest_text: str) -> list[str]:
    """Extract expected file paths from a simple Markdown manifest."""
    lines = manifest_text.splitlines()
    in_expected = False
    expected: list[str] = []

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not in_expected:
            if stripped == EXPECTED_FILES_HEADER:
                in_expected = True
            continue

        if stripped.startswith("## "):
            break
        if not stripped:
            continue
        if stripped.startswith("- "):
            expected.append(normalize_member_name(stripped[2:].strip()))

    if not expected:
        raise PackageValidationError("Manifest does not define any expected files under '## Expected Files'.")
    return expected


def load_expected_files(manifest_path: str | None, expected_files: list[str] | None) -> list[str]:
    """Load expected file paths from a manifest or explicit list."""
    explicit = [normalize_member_name(item) for item in (expected_files or [])]
    if manifest_path:
        with open(manifest_path, encoding="utf-8") as handle:
            manifest_expected = parse_manifest_expected_files(handle.read())
        if explicit and explicit != manifest_expected:
            raise PackageValidationError("Expected files were supplied twice and do not match.")
        return manifest_expected
    if not explicit:
        raise PackageValidationError("Provide either --manifest or one or more --expected-file entries.")
    return explicit


def inspect_zip_contents(zip_path: str) -> list[str]:
    """Return normalized ZIP file member paths and reject unsafe entries."""
    members: list[str] = []
    with zipfile.ZipFile(zip_path, "r") as archive:
        infos = archive.infolist()
        if not infos:
            raise PackageValidationError("ZIP package is empty.")
        for info in infos:
            if info.is_dir():
                raise PackageValidationError(f"Directory entries are not allowed: {info.filename}")
            members.append(normalize_member_name(info.filename))
    if not members:
        raise PackageValidationError("ZIP package does not contain any files.")
    return members


def validate_package(zip_path: str, expected_files: list[str]) -> dict[str, object]:
    """Validate the ZIP package contents against the expected file list."""
    normalized_expected = sorted({normalize_member_name(item) for item in expected_files})
    if not normalized_expected:
        raise PackageValidationError("Expected file list is empty.")

    members = inspect_zip_contents(zip_path)
    member_set = set(members)
    expected_set = set(normalized_expected)

    missing = sorted(expected_set - member_set)
    extra = sorted(member_set - expected_set)
    if missing or extra:
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("extra: " + ", ".join(extra))
        raise PackageValidationError("ZIP contents do not match expected scope (" + "; ".join(details) + ").")

    return {
        "zip_path": zip_path,
        "file_count": len(normalized_expected),
        "files": normalized_expected,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a scoped publish ZIP package.")
    parser.add_argument("zip_path", help="Path to the ZIP package to validate.")
    parser.add_argument(
        "--manifest",
        help="Path to a Markdown manifest containing an '## Expected Files' list.",
    )
    parser.add_argument(
        "--expected-file",
        dest="expected_files",
        action="append",
        default=[],
        help="Expected relative path inside the ZIP. May be supplied multiple times.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        expected = load_expected_files(args.manifest, args.expected_files)
        summary = validate_package(args.zip_path, expected)
    except PackageValidationError as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    print("Publish package validation passed.")
    print(f"ZIP: {summary['zip_path']}")
    print(f"Files: {summary['file_count']}")
    for item in summary["files"]:
        print(f" - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
