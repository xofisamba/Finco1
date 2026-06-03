"""Phase 52F — Persistence guardrail regression tests.

Lightweight structural guardrails that complement the Phase 51F suite.
These are non-invasive (no runtime behavior change) and only fail on
clear boundary violations.

Currently implemented (all safe, no false-positive risk on formatting):

  G1 — No direct sqlite3 / SQLAlchemy imports outside app/persistence/*
  G2 — No service imports main_web or main_api (re-affirm 51F guardrail)
  G3 — No direct sqlite3.Connection instantiation outside app/persistence/*
  G4 — No app/services/*.py file imports get_cursor directly
  G5 — repository.py still has the documented single-transaction pattern
  G6 — No service imports a private (underscore-prefixed) function from
       app.persistence.repository (services should use public surface only)

Deferred to Phase 53+ (would be brittle or require runtime behavior change):
  - D1: route no-refattening (current main_web route body size baseline)
  - D2: service-count / no-new-service-without-justification
  - D3: UI context key contract (no stable source yet)
  - D4: docs no-go scanner (would fail on harmless formatting changes)
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Dict, List

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = REPO_ROOT / "app"
SERVICES_DIR = APP_DIR / "services"
PERSISTENCE_DIR = APP_DIR / "persistence"
REPOSITORY_PY = PERSISTENCE_DIR / "repository.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _strip_docstrings_and_comments(src: str) -> str:
    """Remove docstrings (triple-quoted) and trailing comments so we can grep for real imports."""
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    src = re.sub(r"'''[\s\S]*?'''", "", src)
    out = []
    for line in src.splitlines():
        in_string = False
        quote_char = None
        cleaned = []
        for ch in line:
            if ch in ('"', "'") and not in_string:
                in_string = True
                quote_char = ch
                cleaned.append(ch)
            elif ch == quote_char and in_string:
                in_string = False
                quote_char = None
                cleaned.append(ch)
            elif ch == "#" and not in_string:
                break
            else:
                cleaned.append(ch)
        out.append("".join(cleaned))
    return "\n".join(out)


# ----------------------------- G1: no direct sqlite3 / SQLAlchemy imports outside persistence ----------------------------


class TestG1NoDirectDbImportsOutsidePersistence:
    """G1 — no direct sqlite3 or sqlalchemy imports outside app/persistence/*.

    Rationale: the persistence layer is the single choke point. A
    `import sqlite3` or `from sqlalchemy import ...` in main_web or a
    service would bypass the choke point and split transactional
    behavior across modules.
    """

    FORBIDDEN_TOP_LEVEL = ("sqlite3", "sqlalchemy", "peewee", "pymongo", "psycopg2")

    @pytest.mark.parametrize("module_name", ["sqlite3", "sqlalchemy"])
    def test_no_module_import_outside_persistence(self, module_name):
        offenders: List[str] = []
        for root, dirs, fnames in __import__("os").walk(APP_DIR):
            # Skip the persistence package itself
            if str(PERSISTENCE_DIR) in str(root):
                continue
            for f in fnames:
                if not f.endswith(".py") or f == "__init__.py":
                    continue
                p = Path(root) / f
                text = _read(p)
                cleaned = _strip_docstrings_and_comments(text)
                # Find import statements
                for line in cleaned.splitlines():
                    stripped = line.lstrip()
                    if stripped.startswith(f"import {module_name}") or stripped.startswith(f"from {module_name}"):
                        offenders.append(f"{p}:{line.strip()}")
        assert offenders == [], f"direct {module_name} import outside app/persistence: {offenders}"


# ----------------------------- G2: no service imports main_web or main_api (re-affirm 51F) ----------------------------


class TestG2NoServiceImportsMainWebOrApi:
    """G2 — re-affirm the Phase 51F guardrail. Services must not import main_web / main_api.

    Rationale: services exist to be the narrowing layer between routes
    and persistence. A reverse import would couple them back to the
    route layer and undermine Phase 51's architecture.
    """

    def test_no_service_imports_main_web(self):
        offenders: List[str] = []
        for svc in SERVICES_DIR.glob("*.py"):
            if svc.name == "__init__.py":
                continue
            cleaned = _strip_docstrings_and_comments(_read(svc))
            for line in cleaned.splitlines():
                stripped = line.lstrip()
                if stripped.startswith("import main_web") or stripped.startswith("from main_web"):
                    offenders.append(f"{svc}:{line.strip()}")
        assert offenders == [], f"services import main_web: {offenders}"

    def test_no_service_imports_main_api(self):
        offenders: List[str] = []
        for svc in SERVICES_DIR.glob("*.py"):
            if svc.name == "__init__.py":
                continue
            cleaned = _strip_docstrings_and_comments(_read(svc))
            for line in cleaned.splitlines():
                stripped = line.lstrip()
                if stripped.startswith("import main_api") or stripped.startswith("from main_api"):
                    offenders.append(f"{svc}:{line.strip()}")
        assert offenders == [], f"services import main_api: {offenders}"


# ----------------------------- G3: no sqlite3.Connection instantiation outside persistence ----------------------------


class TestG3NoDirectConnectionInstantiationOutsidePersistence:
    """G3 — no sqlite3.Connection() or create_engine() instantiation outside app/persistence/*.

    Rationale: even if `import sqlite3` is allowed (e.g. type hint),
    actually instantiating a connection outside the choke point would
    bypass the transactional contract.
    """

    def test_no_sqlite3_connection_call_outside_persistence(self):
        offenders: List[str] = []
        for root, dirs, fnames in __import__("os").walk(APP_DIR):
            if str(PERSISTENCE_DIR) in str(root):
                continue
            for f in fnames:
                if not f.endswith(".py") or f == "__init__.py":
                    continue
                p = Path(root) / f
                text = _read(p)
                cleaned = _strip_docstrings_and_comments(text)
                for line in cleaned.splitlines():
                    stripped = line.lstrip()
                    # Look for sqlite3.Connection( or sqlite3.connect(
                    if re.search(r"\bsqlite3\.(Connection|connect)\s*\(", stripped):
                        offenders.append(f"{p}:{line.strip()}")
        assert offenders == [], f"sqlite3.Connection or sqlite3.connect outside app/persistence: {offenders}"


# ----------------------------- G4: no service imports get_cursor directly ----------------------------


class TestG4NoServiceImportsGetCursor:
    """G4 — no service or route imports get_cursor from app.persistence.db.

    Rationale: get_cursor is the transactional choke point. It must
    only be used inside app/persistence/* to preserve the contract
    that all writes go through a single function.
    """

    def test_no_service_imports_get_cursor(self):
        offenders: List[str] = []
        for root, dirs, fnames in __import__("os").walk(APP_DIR):
            if str(PERSISTENCE_DIR) in str(root):
                continue
            for f in fnames:
                if not f.endswith(".py") or f == "__init__.py":
                    continue
                p = Path(root) / f
                text = _read(p)
                cleaned = _strip_docstrings_and_comments(text)
                for line in cleaned.splitlines():
                    stripped = line.lstrip()
                    if re.search(r"\bget_cursor\b", stripped):
                        offenders.append(f"{p}:{line.strip()}")
        assert offenders == [], f"get_cursor used outside app/persistence: {offenders}"


# ----------------------------- G5: repository.py has the single-transaction pattern ----------------------------


class TestG5RepositorySingleTransactionPattern:
    """G5 — repository.py uses the single-transaction `with get_cursor()` pattern.

    Rationale: the 52B side-effect map established that all 15 write
    functions use a single `with get_cursor() as cur:` block per
    function call. A regression here (e.g. nested transactions,
    explicit cur.commit() calls) would break the transactional
    contract that Phase 53 will preserve.
    """

    def test_repository_imports_get_cursor(self):
        text = _read(REPOSITORY_PY)
        assert "from app.persistence.db import get_cursor" in text

    def test_no_explicit_cur_commit_or_flush(self):
        text = _read(REPOSITORY_PY)
        cleaned = _strip_docstrings_and_comments(text)
        for line in cleaned.splitlines():
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            assert "cur.commit" not in stripped, f"explicit cur.commit found: {line}"
            assert "cur.flush" not in stripped, f"explicit cur.flush found: {line}"
            assert "conn.commit" not in stripped, f"explicit conn.commit found: {line}"
            assert "connection.commit" not in stripped, f"explicit connection.commit found: {line}"

    def test_at_least_20_with_get_cursor_blocks(self):
        text = _read(REPOSITORY_PY)
        n = len(re.findall(r"with\s+get_cursor\(\)\s+as\s+cur", text))
        assert n >= 20, f"expected >= 20 with get_cursor() blocks in repository.py, got {n}"


# ----------------------------- G6: services use public surface only ----------------------------


class TestG6ServicesUsePublicSurfaceOnly:
    """G6 — services do not import private (underscore-prefixed) functions from app.persistence.repository.

    Rationale: the public surface of app.persistence.repository is
    the documented contract. A service importing a private function
    (e.g. `from app.persistence.repository import _compute_baseline_snapshot`)
    would couple to internal implementation details that Phase 53 may
    move.
    """

    def test_no_service_imports_private_repository_symbol(self):
        offenders: List[str] = []
        for root, dirs, fnames in __import__("os").walk(APP_DIR):
            if str(PERSISTENCE_DIR) in str(root):
                continue
            for f in fnames:
                if not f.endswith(".py") or f == "__init__.py":
                    continue
                p = Path(root) / f
                text = _read(p)
                # Find lines that import from app.persistence.repository and reference _name
                for m in re.finditer(r"from\s+app\.persistence\.repository\s+import\s+([^\n]+)", text):
                    symbols = m.group(1)
                    # Look for _name (underscore-prefixed)
                    for sym in re.findall(r"\b_\w+", symbols):
                        offenders.append(f"{p}: import {sym} from app.persistence.repository")
        assert offenders == [], f"services import private symbols from app.persistence.repository: {offenders}"
