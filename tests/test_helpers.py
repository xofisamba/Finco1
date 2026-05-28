"""
Shared test helpers for Finco1 test suite.
Provides repo-root resolution independent of deployment path.
"""
from pathlib import Path
import sys

# Repo root = parent of tests/
REPO_ROOT = Path(__file__).resolve().parents[1]

# Portable Python interpreter (sys.executable already points to the running interpreter)
PYTHON = sys.executable
