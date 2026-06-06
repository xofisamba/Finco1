from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relpath: str) -> str:
    return (REPO_ROOT / relpath).read_text(encoding="utf-8")


def test_legacy_test_persistence_is_explicitly_quarantined():
    text = _read("tests/test_persistence.py")
    assert "pytest.skip(" in text
    assert "allow_module_level=True" in text
    assert "Legacy SQLAlchemy persistence tests are quarantined" in text


def test_legacy_test_repository_is_explicitly_quarantined():
    text = _read("tests/test_repository.py")
    assert "pytest.skip(" in text
    assert "allow_module_level=True" in text
    assert "Legacy SQLAlchemy repository tests are quarantined" in text
