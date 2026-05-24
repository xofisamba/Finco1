"""Tests for the Phase 14B publish package validator."""

from __future__ import annotations

import subprocess
import sys
import uuid
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from scripts.validate_publish_package import (
    PackageValidationError,
    load_expected_files,
    parse_manifest_expected_files,
    validate_package,
)


ROOT = Path(__file__).resolve().parents[1]


def _make_zip(zip_path: Path, entries: dict[str, str]) -> None:
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as archive:
        for name, body in entries.items():
            archive.writestr(name, body)


@pytest.fixture
def local_tmp_dir():
    path = ROOT / f"phase14b_test_tmp_{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        if path.exists():
            for item in sorted(path.rglob("*"), reverse=True):
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    item.rmdir()
            path.rmdir()


def test_exact_zip_contents_pass(local_tmp_dir: Path):
    zip_path = local_tmp_dir / "bundle.zip"
    entries = {
        "docs/example.md": "doc",
        "tests/test_example.py": "assert True",
    }
    _make_zip(zip_path, entries)

    summary = validate_package(str(zip_path), list(entries.keys()))

    assert summary["file_count"] == 2
    assert summary["files"] == sorted(entries.keys())


def test_missing_file_fails(local_tmp_dir: Path):
    zip_path = local_tmp_dir / "bundle.zip"
    _make_zip(zip_path, {"docs/example.md": "doc"})

    with pytest.raises(PackageValidationError, match="missing"):
        validate_package(str(zip_path), ["docs/example.md", "tests/test_example.py"])


def test_extra_file_fails(local_tmp_dir: Path):
    zip_path = local_tmp_dir / "bundle.zip"
    _make_zip(
        zip_path,
        {
            "docs/example.md": "doc",
            "tests/test_example.py": "assert True",
            "app/unrelated.py": "oops",
        },
    )

    with pytest.raises(PackageValidationError, match="extra"):
        validate_package(str(zip_path), ["docs/example.md", "tests/test_example.py"])


def test_path_traversal_entry_fails(local_tmp_dir: Path):
    zip_path = local_tmp_dir / "bundle.zip"
    _make_zip(zip_path, {"../evil.txt": "nope"})

    with pytest.raises(PackageValidationError, match="Unsafe relative path"):
        validate_package(str(zip_path), ["../evil.txt"])


def test_absolute_path_entry_fails(local_tmp_dir: Path):
    zip_path = local_tmp_dir / "bundle.zip"
    _make_zip(zip_path, {"/abs/file.txt": "nope"})

    with pytest.raises(PackageValidationError, match="Absolute paths are not allowed"):
        validate_package(str(zip_path), ["/abs/file.txt"])


def test_drive_qualified_path_entry_fails(local_tmp_dir: Path):
    zip_path = local_tmp_dir / "bundle.zip"
    _make_zip(zip_path, {"C:/bad/file.txt": "nope"})

    with pytest.raises(PackageValidationError, match="Drive-qualified absolute paths"):
        validate_package(str(zip_path), ["C:/bad/file.txt"])


def test_empty_package_fails(local_tmp_dir: Path):
    zip_path = local_tmp_dir / "bundle.zip"
    with ZipFile(zip_path, "w", ZIP_DEFLATED):
        pass

    with pytest.raises(PackageValidationError, match="ZIP package is empty"):
        validate_package(str(zip_path), ["docs/example.md"])


def test_manifest_parsing_works():
    manifest = """
# Package Manifest

- Package Name: sample.zip
- Intended Branch: sample-branch
- Base Branch: main

## Expected Files
- docs/example.md
- tests/test_example.py

## Forbidden Categories
- runtime/model formula files
"""
    assert parse_manifest_expected_files(manifest) == [
        "docs/example.md",
        "tests/test_example.py",
    ]


def test_load_expected_files_from_manifest(local_tmp_dir: Path):
    manifest_path = local_tmp_dir / "manifest.md"
    manifest_path.write_text(
        """
# Package Manifest

## Expected Files
- docs/example.md
- tests/test_example.py
""".strip(),
        encoding="utf-8",
    )

    expected = load_expected_files(str(manifest_path), [])
    assert expected == ["docs/example.md", "tests/test_example.py"]


def test_cli_validator_prints_clean_summary(local_tmp_dir: Path):
    zip_path = local_tmp_dir / "bundle.zip"
    _make_zip(
        zip_path,
        {
            "docs/example.md": "doc",
            "tests/test_example.py": "assert True",
        },
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_publish_package.py",
            str(zip_path),
            "--expected-file",
            "docs/example.md",
            "--expected-file",
            "tests/test_example.py",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert "Publish package validation passed." in result.stdout
    assert "docs/example.md" in result.stdout
