"""Phase WF-2 — Results Sheet Styling.

Acceptance criteria:
1. Every CSS class used in sheet_*.html has at least one rule in
   static/styles.css (zero-coverage regression guard).
2. Key structural classes render in workspace sheet routes.
3. Engine MD5 unchanged.
4. File scope: only allowed files changed.
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-wf2")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_session_token  # noqa: E402
from main_web import app  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
ENGINE_MD5 = "6bf49f33efc989736c17cea0cb9b7723"

# Valid CSS class name pattern (BEM-style with at least one dash)
_CLASS_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9]*(-[a-zA-Z0-9]+)+(__[a-zA-Z0-9-]+)?$')


def _sheet_classes() -> set[str]:
    """Return all CSS class names used in sheet_*.html templates."""
    classes: set[str] = set()
    for tmpl in (REPO_ROOT / "app" / "templates" / "partials").glob("sheet_*.html"):
        for m in re.finditer(r'class="([^"]+)"', tmpl.read_text()):
            for cls in m.group(1).split():
                if _CLASS_RE.match(cls):
                    classes.add(cls)
    return classes


@pytest.fixture(scope="module")
def client():
    c = TestClient(app, follow_redirects=True)
    token = create_session_token(user_id="wf2_user", username="wf2_user")
    c.cookies.set("finco_session", token)
    # Seed workspace
    c.get("/?project=tuho")
    return c


# ---------------------------------------------------------------------------
# 1. Engine parity
# ---------------------------------------------------------------------------

class TestEngineParity:
    def test_engine_md5_unchanged(self):
        md5 = hashlib.md5(
            (REPO_ROOT / "app" / "waterfall_core.py").read_bytes()
        ).hexdigest()
        assert md5 == ENGINE_MD5, (
            f"waterfall_core.py MD5 changed: expected {ENGINE_MD5}, got {md5}"
        )


# ---------------------------------------------------------------------------
# 2. Zero-coverage regression guard
# ---------------------------------------------------------------------------

class TestSheetClassCoverage:
    """Every CSS class name used in sheet_*.html must have at least
    one rule in static/styles.css."""

    @pytest.fixture(autouse=True)
    def load_css(self):
        self.css = (REPO_ROOT / "static" / "styles.css").read_text()

    def test_no_zero_coverage_classes(self):
        missing = []
        for cls in sorted(_sheet_classes()):
            pattern = r'\.' + re.escape(cls) + r'[\s{,\[:\)]'
            if not re.search(pattern, self.css):
                missing.append(cls)
        assert not missing, (
            f"Classes used in sheet_*.html with ZERO CSS rules "
            f"({len(missing)}): {missing}"
        )

    def test_wf2_marker_present(self):
        assert "Phase WF-2" in self.css, (
            "WF-2 marker comment must be present in static/styles.css"
        )


# ---------------------------------------------------------------------------
# 3. Key classes present in rendered sheets
# ---------------------------------------------------------------------------

class TestSheetStructure:
    """Sheet templates are rendered inside the workspace via /?project=.
    All sheet_*.html partials are included in workspace_shell.html."""

    @pytest.fixture(autouse=True)
    def inject(self, client):
        self.client = client
        r = client.get("/?project=tuho")
        assert r.status_code == 200
        self.html = r.text

    def test_capex_summary_strip_in_workspace(self):
        assert "capex-summary-strip" in self.html

    def test_capex_summary_card_in_workspace(self):
        assert "capex-summary-card" in self.html

    def test_runtime_block_in_workspace(self):
        assert "runtime-block" in self.html

    def test_rb_metric_in_workspace(self):
        assert "rb-metric" in self.html

    def test_fc_data_row_in_workspace(self):
        assert "fc-data-row" in self.html


# ---------------------------------------------------------------------------
# 4. File scope
# ---------------------------------------------------------------------------

class TestFileScope:
    def test_only_allowed_files_changed(self):
        import shutil
        import subprocess
        if shutil.which("git") is None or not (REPO_ROOT / ".git").exists():
            pytest.skip("git not available")
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "diff", "--name-only", "origin/main"],
            capture_output=True, text=True,
        )
        changed = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        allowed_prefixes = (
            "static/styles.css",
            "tests/test_phase_wf2_",
            "tests/test_phase_wf1_",
            "tests/test_phase_wf3_",
            "tests/test_phase_wf4_",
            "tests/test_phase_wf5_",
            "tests/test_phase_wf6_",
            # cross-arc
            "app/templates/partials/",
            "app/templates/base.html",
            "app/templates/index.html",
            "app/templates/project_home_page.html",
            "app/templates/project_new_page.html",
            "app/templates/project_browse_page.html",
            "app/middleware/security_headers.py",
            "app/ui/dashboard.py",
            "main_web.py",
            "scripts/",
            "tests/test_phase_p2fix",
            "docs/phase_wf",
            "reports/phase_wf",
            "app/ui/scenario_matrix.py",
            "app/templates/partials/scenario_matrix.html",
            "tests/test_phase_m2_",
            "tests/test_phase_m1_",
            "tests/test_phase_m3_",
            "tests/test_phase_m4_",
            "app/templates/partials/_matrix_cell_updated.html",
            "app/templates/partials/_matrix_cell_edit.html",
            "app/templates/partials/_matrix_run_result.html",
        )
        disallowed_prefixes = (
            "app/persistence/",
            "app/services/",
            "app/waterfall_core.py",
            "app/project_factories.py",
            "app/excel_export.py",
            "main_api.py",
            "static/app.js",
        )
        for f in changed:
            assert not any(f.startswith(p) for p in disallowed_prefixes), (
                f"Disallowed file changed: {f}"
            )
            assert any(f.startswith(p) for p in allowed_prefixes), (
                f"File outside allowed scope: {f}"
            )
