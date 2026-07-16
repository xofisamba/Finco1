"""Pytest configuration and shared fixtures.

# Stack AA — Test Suite Rationalization
#
# Test categories (see docs/TEST_SUITE_RATIONALIZATION.md for full census):
#
#   Core engine        ~200 files  High-value unit tests; partially in CI
#   Parity / golden      21 files  Stack baselines; covered by parity_guardrails.yml
#   Phase development   459 files  Historical characterization; not in CI
#   Browser / Playwright 39 files  Self-skip via pytest.importorskip when absent
#   UI component (non-browser) 32  Markup contract tests
#   Integration           5 files  End-to-end; partially skipped (see below)
#   Legacy / disabled    29 files  Skipped via CORE_LEGACY_TEST_FILES / _CALIBRATION_DISABLED_FILES
#
# Skip categories managed here:
#
#   CORE_LEGACY_TEST_FILES       — require 'core' package (not present in active engine)
#   _CALIBRATION_DISABLED_FILES  — require app.calibration (disabled; raises ImportError)
#   integration/test_fid_deck_excel.py — requires app.calibration (oborovo shim)
#   OPENPYXL_TEST_FILES          — require openpyxl (optional)
#
# Quarantined (managed in-file, not here):
#   test_persistence.py          — pytest.skip(allow_module_level=True)
#   test_repository.py           — pytest.skip(allow_module_level=True)
#   Enforcement: tests/test_phase57f_legacy_quarantine.py (in CI)
"""
import importlib.util
import os
import shutil
import sys
import tempfile
import types
from pathlib import Path

import pytest

# Add domain to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Module-level test isolation: every test that imports main_web
# (or anything that imports app.persistence.db) MUST see a
# FINCO_DB_PATH that points to a temporary file OUTSIDE the
# repository default DB. The autouse session fixture below is
# too late: app.persistence.db reads FINCO_DB_PATH at import
# time, which happens before any test-session fixture runs.
# Therefore we set the env var RIGHT NOW, at conftest import
# time, before any test module can import main_web.
#
# Path-safety contract: the env var is accepted ONLY if its
# Path(value).expanduser().resolve() resolves to a path OUTSIDE
# the repository working tree AND not equal to the production
# default at app/data/finco_runs.db. We do NOT compare raw
# strings (relative paths, ./, ../, symlinks, and
# equals-checks against the production path are all rejected
# on the resolved path).
# ---------------------------------------------------------------------------
_REPO_ROOT_RESOLVED = Path(__file__).resolve().parent.parent
_DEFAULT_PROD_DB_RESOLVED = str(
    (_REPO_ROOT_RESOLVED / "app" / "data" / "finco_runs.db").resolve()
)


def _is_repository_path(value: str) -> bool:
    """Return True if the path resolves inside the repository
    working tree or is the production default."""
    try:
        p = Path(value).expanduser().resolve()
    except (OSError, RuntimeError):
        return True
    if str(p) == _DEFAULT_PROD_DB_RESOLVED:
        return True
    try:
        p.relative_to(_REPO_ROOT_RESOLVED)
        return True
    except ValueError:
        return False


# Decide FIRST whether an existing FINCO_DB_PATH is
# repository-resolving or an explicit external path. Only
# allocate a session-owned tmpdir if the env is missing or
# unsafe.
_existing = os.environ.get("FINCO_DB_PATH", "")
if not _existing or _is_repository_path(_existing):
    # The env var is missing, OR it points at a path inside
    # the repository (production default, symlink, ./, ../,
    # relative). Allocate an owned session tmpdir and a DB
    # file inside it.
    _ISOLATION_TMP_DIR_RESOLVED = Path(
        tempfile.mkdtemp(prefix="finco_test_db_")
    )
    _ISOLATION_DB_PATH_RESOLVED = str(
        _ISOLATION_TMP_DIR_RESOLVED / "finco_runs.db"
    )
    Path(_ISOLATION_DB_PATH_RESOLVED).touch()
    os.environ["FINCO_DB_PATH"] = _ISOLATION_DB_PATH_RESOLVED
    CONFTEST_OWNS_ISOLATION_DIR = True
else:
    # The operator (or a pre-existing test) explicitly set a
    # non-repository path. Keep it. Do NOT allocate an
    # unused isolation directory; conftest does NOT own
    # any directory in this case.
    _ISOLATION_TMP_DIR_RESOLVED = None
    _ISOLATION_DB_PATH_RESOLVED = _existing
    CONFTEST_OWNS_ISOLATION_DIR = False


def _install_test_bcrypt_stub() -> None:
    """Provide a tiny test-only bcrypt shim when the optional dependency is absent.

    Some non-auth test modules import app.auth indirectly through fixtures or route
    modules. In local environments without bcrypt installed, we still want those
    tests to collect as long as they are not validating bcrypt itself.
    """
    if "bcrypt" in sys.modules or importlib.util.find_spec("bcrypt") is not None:
        return
    fake_bcrypt = types.SimpleNamespace(
        gensalt=lambda rounds=12: b"salt",
        hashpw=lambda password, salt: b"stub-hash",
        checkpw=lambda password, hashed: True,
    )
    sys.modules["bcrypt"] = fake_bcrypt


_install_test_bcrypt_stub()


# AA3-Group1: Require the 'core' package (pre-refactor engine). Skipped when absent.
# These 12 files cover the historical waterfall engine. Retained for reference;
# they will never run until core/ is restored.
CORE_LEGACY_TEST_FILES = {
    "test_hybrid_clipping.py",
    "test_wind1_fixture.py",
    "test_bess_engine.py",
    "test_capex_tree.py",
    "test_equity.py",
    "test_generic_tax.py",
    "test_goal_seek.py",
    "test_hybrid_engine.py",
    "test_hybrid_lp_engine.py",
    "test_monte_carlo.py",
    "test_waterfall_dscr.py",
    "test_wind_engine.py",
}

SQLALCHEMY_TEST_FILES = set()

OPENPYXL_TEST_FILES = {
    "test_fid_deck_excel.py",
}

# Stack Q: f-string syntax fix applied directly in test_phase24g3_capex_sheet_readability.py.
# The Stack P temporary exclusion is removed.
SYNTAX_ERROR_FILES: set = set()

# AA3-Group2: Require app.calibration (disabled via ImportError guard in app/calibration.py).
# These 16 files are skipped in the active engine. Retained for when calibration is re-enabled.
_CALIBRATION_DISABLED_FILES = frozenset([
    "test_debt_dscr_schedule_policy.py",
    "test_debt_excel_alignment.py",
    "test_finco_gpt_calibration_runner.py",
    "test_finco_gpt_calibration_serialization.py",
    "test_finco_gpt_headless_core.py",
    "test_headless_calibration_runner.py",
    "test_oborovo_excel_reconciliation.py",
    "test_opex_excel_alignment.py",
    "test_period_engine_excel_alignment.py",
    "test_pl_tax_excel_alignment.py",
    "test_project_irr_excel_alignment.py",
    "test_regression.py",
    "test_revenue_excel_alignment.py",
    "test_revenue_formula_units.py",
    "test_shl_excel_alignment.py",
    "test_tuho_excel_reconciliation.py",
])


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _app_calibration_available() -> bool:
    """Check if app.calibration can be imported (not disabled by guard)."""
    spec = importlib.util.find_spec("app.calibration")
    if spec is None:
        return False
    try:
        importlib.import_module("app.calibration")
        return True
    except ImportError:
        return False



@pytest.fixture(autouse=True, scope="session")
def _oborovo_compat_shim():
    """Ensure Oborovo shim is installed before any test runs."""
    import app.project_factories  # noqa: F401


@pytest.fixture(autouse=True)
def _reassert_finco_db_path():
    """Re-set ``FINCO_DB_PATH`` to the session tmpdir at the start
    of every test. A per-test ``monkeypatch.setenv("FINCO_DB_PATH",
    ...)`` is allowed (it will be reset to the isolation path
    after the test), but the value must never be allowed to point
    at a path that resolves inside the repository. If a test
    accidentally re-points at a repository path, we re-correct
    it here."""
    current = os.environ.get("FINCO_DB_PATH", "")
    if not current or _is_repository_path(current):
        os.environ["FINCO_DB_PATH"] = _ISOLATION_DB_PATH_RESOLVED
    # Also re-point the cached app.persistence.db.DB_PATH if
    # the module has already been imported with a
    # repository-resolving path.
    try:
        import app.persistence.db as _db
    except ImportError:
        _db = None
    if _db is not None:
        if _is_repository_path(_db.DB_PATH):
            _db.DB_PATH = _ISOLATION_DB_PATH_RESOLVED
    yield


def pytest_sessionfinish(session, exitstatus):
    """Real teardown hook: clean up the conftest-owned
    isolation tmpdir at the end of the pytest session. Only
    remove directories that conftest itself created; an
    operator-provided external path is preserved."""
    if not CONFTEST_OWNS_ISOLATION_DIR:
        return
    if _ISOLATION_TMP_DIR_RESOLVED is None:
        return
    if not _ISOLATION_TMP_DIR_RESOLVED.exists():
        return
    try:
        shutil.rmtree(_ISOLATION_TMP_DIR_RESOLVED)
    except OSError:
        pass


@pytest.fixture(autouse=True)
def reset_auth_rate_limit():
    """Clear in-memory rate limiting store between tests to prevent cross-test pollution."""
    import app.auth
    app.auth._rate_limit_store.clear()
    yield
    app.auth._rate_limit_store.clear()

def pytest_ignore_collect(collection_path, config):
    """Skip legacy/disabled test modules when their required runtime is absent.

    See docs/TEST_SUITE_RATIONALIZATION.md §AA3 for the full category breakdown.
    """
    path = Path(str(collection_path))
    name = path.name
    full_path = str(path)

    # Skip files that require app.calibration when it's disabled
    if name in _CALIBRATION_DISABLED_FILES and not _app_calibration_available():
        return True

    # Skip integration test that uses ProjectInputs.create_default_oborovo
    # which requires app.calibration (oborovo shim imports from there)
    if "integration/test_fid_deck_excel.py" in full_path:
        return True

    if name in SYNTAX_ERROR_FILES:
        return True
    if name in CORE_LEGACY_TEST_FILES and not _module_available("core"):
        return True
    if name in SQLALCHEMY_TEST_FILES and not _module_available("sqlalchemy"):
        return True
    if name in OPENPYXL_TEST_FILES and not _module_available("openpyxl"):
        return True
    return False
