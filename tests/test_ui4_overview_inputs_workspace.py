"""UI-4 — Overview + Inputs Workspace Redesign — smoke / governance tests.

Verifies the additive introduction of the redesigned Overview + Inputs
workspace surfaces (no engine / route / calculation / persistence /
styles.css / template-rename change):

  - static/workspace.css exists, .fo-* namespace, only --fo-* tokens
  - app/templates/partials/_overview_workspace.html exists with all
    four cards (Project Summary / KPI Grid / Model Health /
    Recent Activity)
  - app/templates/partials/_inputs_workspace.html exists with sticky
    section navigator + collapsible section surface
  - workspace_shell.html mounts the two partials in their respective
    panels (panel-overview, panel-inputs)
  - base.html loads workspace.css AFTER sheet-tabs.css
  - workspace.css consumes only --fo-* tokens; no raw hex / rgba;
    no legacy var() references
  - All class families are namespaced under .fo-* (no leak onto
    legacy .fc-, .ps-, .scm-, .top-header, .dashboard-*, .inp-card,
    .inp-row, .inp-section-* classes)
  - Legacy inputs_section.html is NOT modified (the wrapper is
    progressive enhancement: failure of the collapser script
    does NOT break inputs)
  - C2 preview indicators (capex-total-preview, ebitda-preview,
    debt-preview, tax-preview, irr-preview, dscr-preview) remain
    in the DOM — they are owned by the legacy inner content and
    must NOT be removed by UI-4
  - No engine / persistence / main_web / main_api / factory / route
    change
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Repo paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
TOKENS_CSS = REPO_ROOT / "static" / "tokens.css"
WORKSPACE_CSS = REPO_ROOT / "static" / "workspace.css"
BASE_HTML = REPO_ROOT / "app" / "templates" / "base.html"
WORKSPACE_SHELL_HTML = (
    REPO_ROOT / "app" / "templates" / "partials" / "workspace_shell.html"
)
OVERVIEW_WORKSPACE_HTML = (
    REPO_ROOT / "app" / "templates" / "partials" / "_overview_workspace.html"
)
INPUTS_WORKSPACE_HTML = (
    REPO_ROOT / "app" / "templates" / "partials" / "_inputs_workspace.html"
)
INPUTS_SECTION_HTML = (
    REPO_ROOT / "app" / "templates" / "partials" / "inputs_section.html"
)


# ---------------------------------------------------------------------------
# 1. Files exist
# ---------------------------------------------------------------------------

class TestFilesExist:
    """All UI-4 deliverables must exist on disk."""

    @pytest.mark.parametrize("path", [
        WORKSPACE_CSS,
        OVERVIEW_WORKSPACE_HTML,
        INPUTS_WORKSPACE_HTML,
    ])
    def test_deliverable_file_present(self, path):
        assert path.is_file(), (
            f"UI-4 deliverable missing: {path}"
        )


class TestWorkspaceCssSanity:
    """workspace.css must be a non-trivial, balanced CSS sheet."""

    def test_workspace_css_has_header_comment(self):
        text = WORKSPACE_CSS.read_text(encoding="utf-8")
        assert "WORKSPACE" in text, (
            "workspace.css must start with the Finco One workspace "
            "redesign header."
        )

    def test_workspace_css_balanced_braces(self):
        text = WORKSPACE_CSS.read_text(encoding="utf-8")
        assert text.count("{") == text.count("}"), (
            "workspace.css must have balanced braces."
        )

    def test_workspace_css_substantive_size(self):
        assert WORKSPACE_CSS.stat().st_size > 4000, (
            f"workspace.css should be substantive; got "
            f"{WORKSPACE_CSS.stat().st_size} bytes."
        )


# ---------------------------------------------------------------------------
# 2. .fo-* class namespacing
# ---------------------------------------------------------------------------

REQUIRED_FO_CLASSES = [
    # Overview workspace
    "fo-overview-workspace",
    "fo-project-summary",
    "fo-project-summary__header",
    "fo-project-summary__title",
    "fo-project-summary__sub",
    "fo-project-summary__pill",
    "fo-project-summary__pill--user",
    "fo-project-summary__grid",
    "fo-project-summary__cell",
    "fo-project-summary__label",
    "fo-project-summary__value",
    "fo-project-summary__value--placeholder",
    "fo-kpi-grid",
    "fo-kpi-grid__header",
    "fo-kpi-grid__title",
    "fo-kpi-grid__caption",
    "fo-kpi-grid__cells",
    "fo-kpi-grid__cell",
    "fo-kpi-grid__label",
    "fo-kpi-grid__value",
    "fo-kpi-grid__value--placeholder",
    "fo-health",
    "fo-health__title",
    "fo-health__list",
    "fo-health__item",
    "fo-health__icon",
    "fo-health__icon--warn",
    "fo-health__icon--error",
    "fo-health__icon--info",
    "fo-activity",
    "fo-activity__title",
    "fo-activity__rows",
    "fo-activity__cell",
    "fo-activity__label",
    "fo-activity__value",
    # Inputs workspace
    "fo-inputs-workspace",
    "fo-inputs-workspace__nav",
    "fo-inputs-workspace__nav-title",
    "fo-inputs-workspace__nav-list",
    "fo-inputs-workspace__nav-link",
    "fo-inputs-workspace__nav-dot",
    "fo-inputs-workspace__nav-label",
    "fo-inputs-workspace__content",
    "fo-inputs-workspace__kbd-hint",
    "fo-inputs-workspace__details",
    "fo-inputs-workspace__note",
]


class TestFoClassNamespacing:
    """UI-4 workspace classes are namespaced strictly under `fo-`."""

    @pytest.mark.parametrize("cls", REQUIRED_FO_CLASSES)
    def test_fo_class_appears_in_workspace_css(self, cls):
        text = WORKSPACE_CSS.read_text(encoding="utf-8")
        pattern = re.compile(rf"\.{re.escape(cls)}\b")
        assert pattern.search(text), (
            f"Required workspace class .{cls} not declared in "
            f"workspace.css."
        )

    @pytest.mark.parametrize("cls", REQUIRED_FO_CLASSES)
    def test_fo_class_does_not_leak_into_legacy_stylesheets(self, cls):
        # Workspace classes must NOT bleed into styles.css,
        # chrome.css, or sheet-tabs.css.
        legacy_paths = [
            REPO_ROOT / "static" / "styles.css",
            REPO_ROOT / "static" / "chrome.css",
            REPO_ROOT / "static" / "sheet-tabs.css",
        ]
        for legacy in legacy_paths:
            if not legacy.is_file():
                continue
            text = legacy.read_text(encoding="utf-8")
            # Strip comments.
            text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
            pattern = re.compile(rf"\.{re.escape(cls)}\b")
            assert not pattern.search(text), (
                f"Workspace class .{cls} leaked into "
                f"{legacy.name}; workspace.css owns its own namespace."
            )


# ---------------------------------------------------------------------------
# 3. workspace.css consumes ONLY --fo-* tokens
# ---------------------------------------------------------------------------

class TestWorkspaceCssOnlyConsumesFoTokens:
    """workspace.css must consume only --fo-* tokens."""

    def test_no_raw_hex_colours(self):
        text = WORKSPACE_CSS.read_text(encoding="utf-8")
        text_no_comments = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        offenders = []
        for line_no, raw in enumerate(text_no_comments.splitlines(), start=1):
            if re.search(r"#[0-9a-fA-F]{3,8}\b", raw):
                offenders.append((line_no, raw))
        assert not offenders, (
            "workspace.css must not declare raw hex colours; "
            "use --fo-* tokens instead. Offends:\n  " +
            "\n  ".join(f"L{n}: {l}" for n, l in offenders)
        )

    def test_no_raw_rgb_colours(self):
        text = WORKSPACE_CSS.read_text(encoding="utf-8")
        text_no_comments = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        offenders = []
        for line_no, raw in enumerate(text_no_comments.splitlines(), start=1):
            if re.search(r"\brgba?\s*\(", raw):
                offenders.append((line_no, raw))
        assert not offenders, (
            "workspace.css must not declare raw rgba() colours; "
            "use --fo-* tokens. Offends:\n  " +
            "\n  ".join(f"L{n}: {l}" for n, l in offenders)
        )

    def test_uses_fo_tokens(self):
        text = WORKSPACE_CSS.read_text(encoding="utf-8")
        for token in [
            "--fo-paper",
            "--fo-surface",
            "--fo-ink",
            "--fo-ink-soft",
            "--fo-line",
            "--fo-brand-600",
            "--fo-brand-700",
            "--fo-rag-green",
            "--fo-rag-amber",
            "--fo-rag-red",
            "--fo-font-ui",
            "--fo-font-mono",
            "--fo-text-md",
            "--fo-text-lg",
            "--fo-text-xl",
            "--fo-s2",
            "--fo-s3",
            "--fo-s4",
            "--fo-s5",
            "--fo-r-sm",
            "--fo-r-lg",
            "--fo-shadow-card",
            "--fo-t-fast",
            "--fo-chrome-brand-h",
            "--fo-chrome-cmd-h",
            "--fo-chrome-tabs-h",
        ]:
            assert token in text, (
                f"workspace.css must consume {token} from tokens.css."
            )

    def test_no_legacy_palette_alias(self):
        text = WORKSPACE_CSS.read_text(encoding="utf-8")
        for legacy in ["--sidebar-bg", "--primary", "--surface",
                        "--border", "--text-secondary"]:
            pattern = re.compile(rf"var\(\s*{re.escape(legacy)}\b")
            assert not pattern.search(text), (
                f"workspace.css must not reference legacy token {legacy}."
            )


# ---------------------------------------------------------------------------
# 4. base.html — workspace.css link + ordering
# ---------------------------------------------------------------------------

class TestBaseHtmlWiring:
    """base.html loads workspace.css after sheet-tabs.css."""

    def test_workspace_css_linked(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert "/static/workspace.css" in text, (
            "base.html must link static/workspace.css as a stylesheet."
        )

    def test_load_order_tokens_styles_chrome_sheets_workspace(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        t = text.find("/static/tokens.css")
        s = text.find("/static/styles.css")
        c = text.find("/static/chrome.css")
        st = text.find("/static/sheet-tabs.css")
        w = text.find("/static/workspace.css")
        assert t > 0 and s > 0 and c > 0 and st > 0 and w > 0
        assert t < s < c < st < w, (
            "Load order MUST be tokens → styles → chrome → "
            "sheet-tabs → workspace."
        )


# ---------------------------------------------------------------------------
# 5. Workspace partials — surface real functionality
# ---------------------------------------------------------------------------

class TestOverviewWorkspacePartial:
    """_overview_workspace.html must declare the four cards from PART A."""

    @pytest.mark.parametrize("needle", [
        # Project Summary card
        "Project Summary",
        "Technology",
        "Country",
        "Capacity",
        "Currency",
        "Last Run",
        "Active Scenario",
        # KPI Grid
        "Key metrics",
        "Project IRR",
        "Equity IRR",
        "NPV",
        "Min DSCR",
        "Avg DSCR",
        "LLCR",
        "Lifetime EBITDA",
        "Lifetime Distributions",
        # Model Health
        "Model health",
        "Validation",
        "Balance Sheet",
        "Tax model",
        "Debt schedule",
        # Recent Activity
        "Recent activity",
    ])
    def test_overview_declares_label(self, needle):
        text = OVERVIEW_WORKSPACE_HTML.read_text(encoding="utf-8")
        assert needle in text, (
            f"Overview workspace must include the '{needle}' label."
        )

    def test_overview_kpi_grid_has_eight_cells(self):
        # PART A brief lists exactly 8 KPIs in the grid.
        text = OVERVIEW_WORKSPACE_HTML.read_text(encoding="utf-8")
        # The KPI spec list is the canonical source.
        spec_block = re.search(
            r"_kpi_specs\s*=\s*\[(.*?)\]", text, re.DOTALL
        )
        assert spec_block is not None, (
            "Overview workspace must declare _kpi_specs list."
        )
        n = len(re.findall(r"\('[^']+',\s*'[^']+'\)", spec_block.group(1)))
        assert n == 8, (
            f"Overview KPI grid must declare 8 KPIs (per PART A); got {n}."
        )

    def test_overview_no_engine_invention(self):
        # Per brief: never invent new calculations.
        text = OVERVIEW_WORKSPACE_HTML.read_text(encoding="utf-8")
        # No arithmetic operators inside Jinja expressions beyond
        # trivial ternary fallbacks. The Overview workspace only
        # formats existing values.
        # Guard 1: no Python math imports.
        for forbidden in ("import math", "import numpy", "from math",
                           "from numpy"):
            assert forbidden not in text, (
                f"Overview workspace must not invent calculations; "
                f"found {forbidden!r}."
            )
        # Guard 2: no Jinja arithmetic filter chains that suggest
        # bespoke computation (we deliberately permit trivial
        # default fallbacks like `value if x else y`).
        for forbidden in ("{% set _irr =", "{% set _dscr =",
                           "{% set _npv ="):
            assert forbidden not in text, (
                f"Overview workspace must not invent calculations; "
                f"found {forbidden!r}."
            )

    def test_overview_dirty_state_visible(self):
        # PART E (carried over): dirty state must be visible somewhere
        # on the page (Project Summary status, Model Health, Activity).
        text = OVERVIEW_WORKSPACE_HTML.read_text(encoding="utf-8")
        assert "dirty" in text.lower() or "_dirty" in text


class TestInputsWorkspacePartial:
    """_inputs_workspace.html must declare the navigator + collapsible
    section surface from PART B + PART D."""

    @pytest.mark.parametrize("needle", [
        # PART B: groups declared in the navigator
        "Identity",
        "Schedule",
        "Technical",
        "Revenue",
        "CAPEX",
        "OPEX",
        "Debt",
        "Tax",
        # PART D: in-page section navigator
        "Sections",
        "fo-inputs-workspace__nav",
        # PART F: keyboard hint
        "Tab",
    ])
    def test_inputs_declares_surface(self, needle):
        text = INPUTS_WORKSPACE_HTML.read_text(encoding="utf-8")
        assert needle in text, (
            f"Inputs workspace must include {needle!r}."
        )

    def test_inputs_includes_legacy_inputs_section_partial(self):
        # The wrapper must include the legacy inputs_section.html so
        # every existing field still renders. UI-4 only wraps.
        text = INPUTS_WORKSPACE_HTML.read_text(encoding="utf-8")
        assert '{% include "partials/inputs_section.html" %}' in text, (
            "Inputs workspace must include the legacy inputs_section.html."
        )

    def test_inputs_collapser_script_present(self):
        # Progressive-enhancement collapser must be embedded.
        text = INPUTS_WORKSPACE_HTML.read_text(encoding="utf-8")
        assert "<script>" in text
        assert "details" in text and "summary" in text
        # Must wrap .inp-card elements.
        assert ".inp-card" in text
        # Must use IntersectionObserver for scrollspy.
        assert "IntersectionObserver" in text

    def test_inputs_section_navigator_links_eight_sections(self):
        text = INPUTS_WORKSPACE_HTML.read_text(encoding="utf-8")
        # The _sections list is the canonical source for the navigator.
        spec_block = re.search(
            r"_sections\s*=\s*\[(.*?)\]", text, re.DOTALL
        )
        assert spec_block is not None, (
            "Inputs workspace must declare _sections list."
        )
        n = len(re.findall(r"\('[^']+',\s*'[^']+'", spec_block.group(1)))
        assert n == 8, (
            f"Inputs section navigator must declare 8 sections (per "
            f"PART B); got {n}."
        )


# ---------------------------------------------------------------------------
# 6. Legacy inputs_section.html must NOT be modified by UI-4
# ---------------------------------------------------------------------------

class TestLegacyInputsSectionUntouched:
    """UI-4 must not modify inputs_section.html. The wrapper is
    progressive enhancement that depends on the canonical header
    text strings ("Identity", "Schedule", ...) declared in the
    legacy partial."""

    def test_inputs_section_file_unchanged(self, repo_diff):
        assert "app/templates/partials/inputs_section.html" not in (
            repo_diff.changed_paths
        ), (
            "UI-4 must not modify inputs_section.html; the wrapper is "
            "progressive enhancement only."
        )


# ---------------------------------------------------------------------------
# 7. C2 preview indicators must remain in the DOM
# ---------------------------------------------------------------------------

# C2-PR8..C2-PR32 indicators are owned by legacy inner content on the
# Overview panel. UI-4 must NOT remove them — the C2 runtime renderer
# (static/modelling/runtime-renderer.js) patches these specific IDs.
C2_PREVIEW_INDICATOR_IDS = [
    "capex-total-preview",
    "revenue-total-preview",
    "opex-total-preview",
    "ebitda-preview",
    "operating-cf-preview",
    "debt-preview",
    "tax-preview",
    "irr-preview",
    "dscr-preview",
    "overview-runtime-status",
]


class TestC2PreviewIndicatorsPreserved:
    """The C2 preview indicator IDs must remain in workspace_shell.html.
    UI-4 only ADDS content to panel-overview; it must not touch the
    legacy preview panel markup."""

    def test_preview_indicators_present_in_workspace_shell(self):
        text = WORKSPACE_SHELL_HTML.read_text(encoding="utf-8")
        missing = []
        for indicator_id in C2_PREVIEW_INDICATOR_IDS:
            if f'id="{indicator_id}"' not in text:
                missing.append(indicator_id)
        assert not missing, (
            f"C2 preview indicators missing from workspace_shell.html: "
            f"{missing}. UI-4 must NOT remove them."
        )


# ---------------------------------------------------------------------------
# 8. workspace_shell.html mounts the two new partials
# ---------------------------------------------------------------------------

class TestWorkspaceShellMountsNewPartials:
    """workspace_shell.html must mount _overview_workspace.html at the
    top of panel-overview and _inputs_workspace.html inside
    panel-inputs."""

    def test_overview_panel_mounts_workspace(self):
        text = WORKSPACE_SHELL_HTML.read_text(encoding="utf-8")
        # Find the <div id="panel-overview"> opener.
        idx = text.find('<div class="tab-panel active" id="panel-overview">')
        assert idx > 0, "panel-overview not found in workspace_shell.html."
        # The overview workspace include must appear AFTER the opener
        # and BEFORE the legacy inner content (capex-total-preview).
        overview_idx = text.find('partials/_overview_workspace.html', idx)
        legacy_idx = text.find('id="capex-total-preview"', idx)
        assert overview_idx > 0 and legacy_idx > 0
        assert overview_idx < legacy_idx, (
            "Overview workspace must mount BEFORE the legacy preview "
            "panel content."
        )

    def test_inputs_panel_mounts_workspace(self):
        text = WORKSPACE_SHELL_HTML.read_text(encoding="utf-8")
        idx = text.find('<div class="tab-panel" id="panel-inputs">')
        assert idx > 0, "panel-inputs not found in workspace_shell.html."
        inputs_idx = text.find('partials/_inputs_workspace.html', idx)
        assert inputs_idx > 0, (
            "Inputs workspace must be mounted inside panel-inputs."
        )


# ---------------------------------------------------------------------------
# 9. Forbidden paths — UI-4 is additive only
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
    "app/templates/partials/sheet_inputs.html",
    "app/templates/partials/inputs_section.html",
]


class TestForbiddenPathsUntouched:
    """UI-4 is additive only — no engine / persistence / route / JS /
    existing-stylesheet / existing-page edit."""

    @pytest.mark.parametrize("relpath", FORBIDDEN_PATHS)
    def test_path_does_not_exist_or_unchanged(self, relpath, repo_diff):
        if not (REPO_ROOT / relpath).exists():
            pytest.skip(f"{relpath} does not exist in repo")
        assert relpath not in repo_diff.changed_paths, (
            f"UI-4 must not modify {relpath}; workspace-only PR. "
            f"Changed files: {sorted(repo_diff.changed_paths)}"
        )


# ---------------------------------------------------------------------------
# 10. base.html diff is additive
# ---------------------------------------------------------------------------

class TestBaseHtmlAdditiveOnly:
    """base.html diff may only contain <link> additions and Jinja
    comments for the UI-4 entry."""

    def test_base_html_diff_is_minimal(self, repo_diff):
        if "app/templates/base.html" not in repo_diff.changed_paths:
            return
        hunks = repo_diff.hunks_for("app/templates/base.html")
        added_lines = [h["content"] for h in hunks if h["op"] == "+"]
        removed_lines = [h["content"] for h in hunks if h["op"] == "-"]
        assert any("/static/workspace.css" in line for line in added_lines), (
            "workspace.css link was not added to base.html."
        )
        for needle in (
            "/static/styles.css", "/static/tokens.css",
            "/static/chrome.css", "/static/sheet-tabs.css",
            '<header class="top-header">',
        ):
            assert not any(needle in line for line in removed_lines), (
                f"UI-4 must not remove existing line containing "
                f"{needle!r}."
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
                f"base.html diff contains an unexpected added line: "
                f"{line!r}"
            )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class _RepoDiff:
    """Wraps `git diff origin/main --name-only` + per-file hunks."""

    def __init__(self) -> None:
        import subprocess
        out = subprocess.run(
            ["git", "diff", "--name-only", "origin/main", "--"],
            cwd=str(REPO_ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
        self.changed_paths = {
            line.strip()
            for line in out.stdout.splitlines()
            if line.strip()
        }
        ls = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "--"],
            cwd=str(REPO_ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
        self.untracked_paths: set[str] = {
            line.strip()
            for line in ls.stdout.splitlines()
            if line.strip()
        }
        self._hunks: dict[str, list[dict]] = {}
        for path in sorted(self.changed_paths):
            self._hunks[path] = self._parse_hunks(path)

    def _parse_hunks(self, path: str) -> list[dict]:
        import subprocess
        proc = subprocess.run(
            ["git", "diff", "origin/main", "--", path],
            cwd=str(REPO_ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
        hunks: list[dict] = []
        for line in proc.stdout.splitlines():
            if not line:
                continue
            if line.startswith("+++") or line.startswith("---"):
                continue
            if line.startswith("@@"):
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