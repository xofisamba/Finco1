"""UI-5 — Unified Modelling Workspace (Revenue / OPEX / CAPEX / Debt / Tax).

Verifies the additive introduction of the unified modelling workspace
chrome across the 5 core modelling sheets. Same governance contract as
UI-4 (no engine / route / calculation / persistence / styles.css /
template-rename change).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
TOKENS_CSS = REPO_ROOT / "static" / "tokens.css"
MODELLING_WORKSPACE_CSS = REPO_ROOT / "static" / "modelling-workspace.css"
BASE_HTML = REPO_ROOT / "app" / "templates" / "base.html"
WORKSPACE_SHELL_HTML = (
    REPO_ROOT / "app" / "templates" / "partials" / "workspace_shell.html"
)
CHROME_PARTIAL = (
    REPO_ROOT / "app" / "templates" / "partials" / "_modelling_workspace_chrome.html"
)
INIT_PARTIAL = (
    REPO_ROOT / "app" / "templates" / "partials" / "_modelling_workspace_init.html"
)
HEADER_PARTIAL = (
    REPO_ROOT / "app" / "templates" / "partials" / "_modelling_workspace_header.html"
)
NAV_PARTIAL = (
    REPO_ROOT / "app" / "templates" / "partials" / "_modelling_workspace_nav.html"
)
CONTEXT_PARTIALS = {
    "revenue": REPO_ROOT / "app" / "templates" / "partials" / "_modelling_workspace_context_revenue.html",
    "opex": REPO_ROOT / "app" / "templates" / "partials" / "_modelling_workspace_context_opex.html",
    "capex": REPO_ROOT / "app" / "templates" / "partials" / "_modelling_workspace_context_capex.html",
    "debt": REPO_ROOT / "app" / "templates" / "partials" / "_modelling_workspace_context_debt.html",
    "tax": REPO_ROOT / "app" / "templates" / "partials" / "_modelling_workspace_context_tax.html",
}


REQUIRED_FO_CLASSES = [
    "fo-modelling-workspace",
    "fo-modelling-workspace__header",
    "fo-modelling-workspace__title-row",
    "fo-modelling-workspace__title",
    "fo-modelling-workspace__status",
    "fo-modelling-workspace__pill",
    "fo-modelling-workspace__pill--dirty",
    "fo-modelling-workspace__pill--saved",
    "fo-modelling-workspace__pill--ok",
    "fo-modelling-workspace__pill--warn",
    "fo-modelling-workspace__pill--fail",
    "fo-modelling-workspace__pill-dot",
    "fo-modelling-workspace__pill-icon",
    "fo-modelling-workspace__description",
    "fo-modelling-workspace__layout",
    "fo-modelling-workspace__nav",
    "fo-modelling-workspace__nav-title",
    "fo-modelling-workspace__nav-list",
    "fo-modelling-workspace__nav-link",
    "fo-modelling-workspace__nav-dot",
    "fo-modelling-workspace__nav-label",
    "fo-modelling-workspace__content",
    "fo-modelling-workspace__context",
    "fo-modelling-workspace__context-title",
    "fo-modelling-workspace__context-list",
    "fo-modelling-workspace__context-row",
    "fo-modelling-workspace__context-label",
    "fo-modelling-workspace__context-value",
    "fo-modelling-workspace__context-value--placeholder",
    "fo-modelling-workspace__context-hint",
    "fo-modelling-workspace__section",
    "fo-modelling-workspace__section-header",
    "fo-modelling-workspace__section-header-num",
    "fo-modelling-workspace__section-warnings",
]


class TestFilesExist:
    @pytest.mark.parametrize("path", [
        MODELLING_WORKSPACE_CSS,
        CHROME_PARTIAL,
        INIT_PARTIAL,
        HEADER_PARTIAL,
        NAV_PARTIAL,
        *CONTEXT_PARTIALS.values(),
    ])
    def test_deliverable_present(self, path):
        assert path.is_file(), f"UI-5 deliverable missing: {path}"


class TestModellingWorkspaceCssSanity:
    def test_workspace_css_has_header_comment(self):
        text = MODELLING_WORKSPACE_CSS.read_text(encoding="utf-8")
        assert "MODELLING WORKSPACE" in text.upper()

    def test_workspace_css_balanced_braces(self):
        text = MODELLING_WORKSPACE_CSS.read_text(encoding="utf-8")
        assert text.count("{") == text.count("}")

    def test_workspace_css_substantive(self):
        assert MODELLING_WORKSPACE_CSS.stat().st_size > 8000


class TestFoClassNamespacing:
    @pytest.mark.parametrize("cls", REQUIRED_FO_CLASSES)
    def test_fo_class_appears_in_modelling_workspace_css(self, cls):
        text = MODELLING_WORKSPACE_CSS.read_text(encoding="utf-8")
        pattern = re.compile(rf"\.{re.escape(cls)}\b")
        assert pattern.search(text), (
            f"Required class .{cls} not declared in modelling-workspace.css."
        )

    @pytest.mark.parametrize("cls", REQUIRED_FO_CLASSES)
    def test_fo_class_does_not_leak_into_legacy_stylesheets(self, cls):
        legacy_paths = [
            REPO_ROOT / "static" / "styles.css",
            REPO_ROOT / "static" / "chrome.css",
            REPO_ROOT / "static" / "sheet-tabs.css",
            REPO_ROOT / "static" / "workspace.css",
        ]
        for legacy in legacy_paths:
            if not legacy.is_file():
                continue
            text = legacy.read_text(encoding="utf-8")
            text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
            pattern = re.compile(rf"\.{re.escape(cls)}\b")
            assert not pattern.search(text), (
                f"Modelling-workspace class .{cls} leaked into "
                f"{legacy.name}."
            )


class TestModellingWorkspaceCssOnlyConsumesFoTokens:
    def test_no_raw_hex_colours(self):
        text = MODELLING_WORKSPACE_CSS.read_text(encoding="utf-8")
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        offenders = []
        for line_no, raw in enumerate(text.splitlines(), start=1):
            if re.search(r"#[0-9a-fA-F]{3,8}\b", raw):
                offenders.append((line_no, raw))
        assert not offenders, (
            "modelling-workspace.css must not declare raw hex colours; "
            "use --fo-* tokens. Offends:\n  " +
            "\n  ".join(f"L{n}: {l}" for n, l in offenders)
        )

    def test_no_raw_rgb_colours(self):
        text = MODELLING_WORKSPACE_CSS.read_text(encoding="utf-8")
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        offenders = []
        for line_no, raw in enumerate(text.splitlines(), start=1):
            if re.search(r"\brgba?\s*\(", raw):
                offenders.append((line_no, raw))
        assert not offenders, (
            "modelling-workspace.css must not declare raw rgba() colours."
        )

    def test_uses_fo_tokens(self):
        text = MODELLING_WORKSPACE_CSS.read_text(encoding="utf-8")
        for token in [
            "--fo-paper", "--fo-line", "--fo-ink", "--fo-ink-soft",
            "--fo-ink-faint", "--fo-brand-50", "--fo-brand-600",
            "--fo-brand-700", "--fo-rag-neutral-bg", "--fo-rag-amber",
            "--fo-rag-amber-bg", "--fo-rag-green", "--fo-rag-green-bg",
            "--fo-rag-red", "--fo-rag-red-bg",
            "--fo-font-ui", "--fo-font-mono",
            "--fo-text-xs", "--fo-text-sm", "--fo-text-md",
            "--fo-text-lg", "--fo-text-xl",
            "--fo-s1", "--fo-s2", "--fo-s3", "--fo-s4", "--fo-s5",
            "--fo-r-sm", "--fo-r-md", "--fo-r-lg",
            "--fo-weight-regular", "--fo-weight-medium",
            "--fo-weight-semibold", "--fo-weight-bold",
            "--fo-t-fast", "--fo-ease",
            "--fo-chrome-brand-h", "--fo-chrome-cmd-h",
        ]:
            assert token in text, (
                f"modelling-workspace.css must consume {token} from tokens.css."
            )

    def test_no_legacy_palette_alias(self):
        text = MODELLING_WORKSPACE_CSS.read_text(encoding="utf-8")
        for legacy in ["--sidebar-bg", "--primary", "--surface",
                        "--border", "--text-secondary"]:
            pattern = re.compile(rf"var\(\s*{re.escape(legacy)}\b")
            assert not pattern.search(text), (
                f"modelling-workspace.css must not reference legacy token {legacy}."
            )


class TestBaseHtmlWiring:
    def test_modelling_workspace_css_linked(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert "/static/modelling-workspace.css" in text, (
            "base.html must link static/modelling-workspace.css as a stylesheet."
        )

    def test_load_order_tokens_styles_chrome_sheets_workspace_modelling(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        t = text.find("/static/tokens.css")
        s = text.find("/static/styles.css")
        c = text.find("/static/chrome.css")
        st = text.find("/static/sheet-tabs.css")
        w = text.find("/static/workspace.css")
        m = text.find("/static/modelling-workspace.css")
        assert t > 0 and s > 0 and c > 0 and st > 0 and w > 0 and m > 0
        assert t < s < c < st < w < m, (
            "Load order MUST be tokens → styles → chrome → sheet-tabs → "
            "workspace → modelling-workspace."
        )


class TestPartials:
    @pytest.mark.parametrize("name,path", list(CONTEXT_PARTIALS.items()))
    def test_context_partial_uses_only_known_project_ctx_fields(self, name, path):
        text = path.read_text(encoding="utf-8")
        # The 5 context panels must read from project_ctx only.
        assert "project_ctx." in text, (
            f"{name} context panel must read from project_ctx."
        )
        # Never invent new calculations: no Python math imports, no
        # engine calculations, no tax/debt engine invocations.
        for forbidden in ("import math", "import numpy", "from math",
                           "from numpy", "import scipy",
                           "run_scenario", "compute_irr", "compute_dscr",
                           "compute_npv", "app/capex_engine",
                           "app/waterfall_core"):
            assert forbidden not in text, (
                f"{name} context panel must not invent calculations; "
                f"found {forbidden!r}."
            )

    def test_header_partial_declares_dirty_and_validation_pills(self):
        text = HEADER_PARTIAL.read_text(encoding="utf-8")
        for needle in (
            "fo-modelling-workspace__header",
            "fo-modelling-workspace__title",
            "fo-modelling-workspace__pill--dirty",
            "fo-modelling-workspace__pill--saved",
            "fo-modelling-workspace__pill--ok",
            "fo-modelling-workspace__pill--warn",
            "fo-modelling-workspace__pill--fail",
        ):
            assert needle in text, f"Header partial must include {needle!r}."

    def test_init_partial_uses_intersection_observer(self):
        text = INIT_PARTIAL.read_text(encoding="utf-8")
        assert "IntersectionObserver" in text
        assert "initModellingWorkspace" in text
        for k in ("revenue", "opex", "capex", "senior-debt", "tax"):
            assert k in text, (
                f"Init partial must wire sheet '{k}'."
            )

    def test_nav_partial_declares_sticky_anchor_links(self):
        text = NAV_PARTIAL.read_text(encoding="utf-8")
        for needle in ("fo-modelling-workspace__nav", "fo-modelling-workspace__nav-link",
                        "fo-modelling-workspace__nav-title", "Sections"):
            assert needle in text, f"Nav partial must include {needle!r}."


class TestWorkspaceShellMountsNewPartials:
    """All 5 modelling panels (revenue/opex/capex/senior-debt/tax) must
    wrap their content in a `fo-modelling-workspace` section and include
    the section nav + context panel partials."""

    @pytest.mark.parametrize("kind,context_partial", [
        ("revenue", "_modelling_workspace_context_revenue.html"),
        ("opex", "_modelling_workspace_context_opex.html"),
        ("capex", "_modelling_workspace_context_capex.html"),
        ("senior-debt", "_modelling_workspace_context_debt.html"),
        ("tax", "_modelling_workspace_context_tax.html"),
    ])
    def test_panel_mounts_workspace(self, kind, context_partial):
        text = WORKSPACE_SHELL_HTML.read_text(encoding="utf-8")
        idx = text.find(f'data-fo-mod-kind="{kind}"')
        assert idx > 0, (
            f"data-fo-mod-kind={kind!r} not found in workspace_shell.html."
        )
        assert f'partials/_modelling_workspace_nav.html' in text[idx:idx + 5000]
        assert f'partials/{context_partial}' in text[idx:idx + 5000]


class TestInitIncludedInShell:
    def test_init_partial_included_at_end(self):
        text = WORKSPACE_SHELL_HTML.read_text(encoding="utf-8")
        # The init partial is included at the bottom of workspace_shell.html.
        assert "_modelling_workspace_init.html" in text, (
            "workspace_shell.html must include the init partial."
        )


# ---------------------------------------------------------------------------
# Forbidden paths
# ---------------------------------------------------------------------------

FORBIDDEN_PATHS = [
    "app/waterfall_core.py",
    "app/waterfall_runner.py",
    "app/input_adapter.py",
    "app/project_factories.py",
    "app/capex_engine.py",
    "app/opex_engine.py",
    "app/depreciation_engine.py",
    "app/excel_export.py",
    "app/services/save_run_service.py",
    "app/services/run_service.py",
    "app/services/compare_service.py",
    "app/services/download_service.py",
    "app/services/preview_context.py",
    "app/services/previews/",
    "app/persistence/",
    "domain/",
    "main_web.py",
    "main_api.py",
    "static/app.js",
    "static/styles.css",
    "static/chrome.css",
    "static/sheet-tabs.css",
    "static/workspace.css",
    "static/modelling/",
    "static/interaction/",
    "app/templates/partials/_dashboard.html",
    "app/templates/partials/_nav_compression.html",
    "app/templates/partials/workspace_tabs.html",
    "app/templates/partials/_last_run_indicator.html",
    "app/templates/partials/_generic_status_line.html",
    "app/templates/partials/_brand_bar.html",
    "app/templates/partials/_command_bar.html",
    "app/templates/partials/_kpi_strip.html",
    "app/templates/partials/_sheet_tabs.html",
    "app/templates/partials/_app_chrome.html",
    "app/templates/partials/sheet_revenue.html",
    "app/templates/partials/sheet_opex.html",
    "app/templates/partials/sheet_opex_detail.html",
    "app/templates/partials/sheet_capex.html",
    "app/templates/partials/sheet_capex_detail.html",
    "app/templates/partials/sheet_senior_debt.html",
    "app/templates/partials/sheet_shl.html",
    "app/templates/partials/sheet_tax.html",
    "app/templates/partials/sheet_inputs.html",
    "app/templates/partials/inputs_section.html",
    "app/templates/partials/_overview_workspace.html",
    "app/templates/partials/_inputs_workspace.html",
]


class TestForbiddenPathsUntouched:
    @pytest.mark.parametrize("relpath", FORBIDDEN_PATHS)
    def test_path_unchanged(self, relpath, repo_diff):
        if not (REPO_ROOT / relpath).exists():
            pytest.skip(f"{relpath} does not exist in repo")
        assert relpath not in repo_diff.changed_paths, (
            f"UI-5 must not modify {relpath}; modelling workspace only. "
            f"Changed: {sorted(repo_diff.changed_paths)}"
        )


class TestBaseHtmlAdditiveOnly:
    def test_base_html_diff_is_minimal(self, repo_diff):
        if "app/templates/base.html" not in repo_diff.changed_paths:
            return
        hunks = repo_diff.hunks_for("app/templates/base.html")
        added_lines = [h["content"] for h in hunks if h["op"] == "+"]
        removed_lines = [h["content"] for h in hunks if h["op"] == "-"]
        for needle in ("/static/styles.css", "/static/tokens.css",
                        "/static/chrome.css", "/static/sheet-tabs.css",
                        "/static/workspace.css", "/static/modelling-workspace.css",
                        "/static/statements-reporting.css",
                        "/static/power-user.css",
                        '<header class="top-header">'):
            assert not any(needle in line for line in removed_lines), (
                f"UI-5 must not remove existing line containing {needle!r}."
            )
        inside_jinja = False
        for line in added_lines:
            stripped = line.strip()
            if not stripped:
                continue
            if inside_jinja:
                if "#}" in stripped:
                    inside_jinja = False
                continue
            if stripped.startswith("{#"):
                if "#}" not in stripped:
                    inside_jinja = True
                continue
            assert stripped.startswith("<link"), (
                f"base.html diff contains an unexpected added line: {line!r}"
            )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class _RepoDiff:
    def __init__(self) -> None:
        import subprocess
        out = subprocess.run(
            ["git", "diff", "--name-only", "origin/main", "--"],
            cwd=str(REPO_ROOT), check=True, capture_output=True, text=True,
        )
        self.changed_paths = {
            line.strip() for line in out.stdout.splitlines() if line.strip()
        }
        ls = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "--"],
            cwd=str(REPO_ROOT), check=True, capture_output=True, text=True,
        )
        self.untracked_paths = {
            line.strip() for line in ls.stdout.splitlines() if line.strip()
        }
        self._hunks: dict[str, list[dict]] = {}
        for path in sorted(self.changed_paths):
            self._hunks[path] = self._parse_hunks(path)

    def _parse_hunks(self, path: str) -> list[dict]:
        import subprocess
        proc = subprocess.run(
            ["git", "diff", "origin/main", "--", path],
            cwd=str(REPO_ROOT), check=True, capture_output=True, text=True,
        )
        hunks: list[dict] = []
        for line in proc.stdout.splitlines():
            if not line or line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
                continue
            if line.startswith("+"):
                hunks.append({"op": "+", "content": line[1:]})
            elif line.startswith("-"):
                hunks.append({"op": "-", "content": line[1:]})
        return hunks

    def hunks_for(self, path: str) -> list[dict]:
        return list(self._hunks.get(path, []))


@pytest.fixture(scope="session")
def repo_diff():
    return _RepoDiff()
