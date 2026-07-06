"""UI-7 — Power User Workflow (Command Palette · Global Search · Keyboard).

Verifies the additive introduction of the command palette, global
search, quick actions, keyboard shortcuts overlay, jump-to button,
recently-edited strip, skeleton loaders, and refreshed empty
states. No engine / route / calculation / persistence change.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
TOKENS_CSS = REPO_ROOT / "static" / "tokens.css"
POWER_CSS = REPO_ROOT / "static" / "power-user.css"
BASE_HTML = REPO_ROOT / "app" / "templates" / "base.html"
WORKSPACE_SHELL_HTML = (
    REPO_ROOT / "app" / "templates" / "partials" / "workspace_shell.html"
)
PALETTE_PARTIAL = (
    REPO_ROOT / "app" / "templates" / "partials" / "_power_user_palette.html"
)
SHORTCUTS_PARTIAL = (
    REPO_ROOT / "app" / "templates" / "partials" / "_power_user_shortcuts.html"
)
JUMP_PARTIAL = (
    REPO_ROOT / "app" / "templates" / "partials" / "_power_user_jump.html"
)
RECENT_PARTIAL = (
    REPO_ROOT / "app" / "templates" / "partials" / "_power_user_recent.html"
)
EMPTY_PARTIAL = (
    REPO_ROOT / "app" / "templates" / "partials" / "_power_user_empty.html"
)
SKELETON_PARTIAL = (
    REPO_ROOT / "app" / "templates" / "partials" / "_power_user_skeleton.html"
)
INIT_PARTIAL = (
    REPO_ROOT / "app" / "templates" / "partials" / "_power_user_init.html"
)


REQUIRED_FO_CLASSES = [
    # Command palette
    "fo-power-palette-backdrop",
    "fo-power-palette",
    "fo-power-palette__input",
    "fo-power-palette__results",
    "fo-power-palette__group",
    "fo-power-palette__group-title",
    "fo-power-palette__list",
    "fo-power-palette__item",
    "fo-power-palette__item-icon",
    "fo-power-palette__item-label",
    "fo-power-palette__item-hint",
    "fo-power-palette__item-kbd",
    "fo-power-palette__empty",
    "fo-power-palette__footer",
    "fo-power-palette__footer-kbds",
    # Shortcuts overlay
    "fo-power-shortcuts-backdrop",
    "fo-power-shortcuts",
    "fo-power-shortcuts__header",
    "fo-power-shortcuts__title",
    "fo-power-shortcuts__close",
    "fo-power-shortcuts__body",
    "fo-power-shortcuts__group",
    "fo-power-shortcuts__group-title",
    "fo-power-shortcuts__row",
    "fo-power-shortcuts__row-label",
    "fo-power-shortcuts__row-kbds",
    "fo-power-shortcuts__row-kbd",
    # Recently edited
    "fo-power-recent",
    "fo-power-recent__title",
    "fo-power-recent__clear",
    "fo-power-recent__list",
    "fo-power-recent__item",
    "fo-power-recent__item-icon",
    "fo-power-recent__item-label",
    "fo-power-recent__item-meta",
    "fo-power-recent__empty",
    # Empty state
    "fo-power-empty",
    "fo-power-empty__icon",
    "fo-power-empty__title",
    "fo-power-empty__body",
    "fo-power-empty__actions",
    "fo-power-empty__btn",
    "fo-power-empty__btn--primary",
    # Skeleton loaders
    "fo-power-skeleton",
    "fo-power-skeleton--block",
    "fo-power-skeleton--circle",
    "fo-power-skeleton--row",
    # Jump-to
    "fo-power-jump",
    "fo-power-jump__btn",
    "fo-power-jump__btn-kbd",
]


class TestFilesExist:
    @pytest.mark.parametrize("path", [
        POWER_CSS,
        PALETTE_PARTIAL,
        SHORTCUTS_PARTIAL,
        JUMP_PARTIAL,
        RECENT_PARTIAL,
        EMPTY_PARTIAL,
        SKELETON_PARTIAL,
        INIT_PARTIAL,
    ])
    def test_deliverable_present(self, path):
        assert path.is_file(), f"UI-7 deliverable missing: {path}"


class TestPowerCssSanity:
    def test_css_has_header_comment(self):
        text = POWER_CSS.read_text(encoding="utf-8")
        assert "POWER USER" in text.upper()

    def test_css_balanced_braces(self):
        text = POWER_CSS.read_text(encoding="utf-8")
        assert text.count("{") == text.count("}")

    def test_css_substantive(self):
        assert POWER_CSS.stat().st_size > 6000

    def test_print_block_present(self):
        # PART H — empty states, skeleton, palette, shortcuts hidden
        # in print.
        text = POWER_CSS.read_text(encoding="utf-8")
        assert "@media print" in text
        assert ".fo-power-palette" in text
        assert ".fo-power-shortcuts" in text


class TestFoClassNamespacing:
    @pytest.mark.parametrize("cls", REQUIRED_FO_CLASSES)
    def test_fo_class_declared_in_power_css(self, cls):
        text = POWER_CSS.read_text(encoding="utf-8")
        pattern = re.compile(rf"\.{re.escape(cls)}\b")
        assert pattern.search(text), (
            f"Required class .{cls} not declared in power-user.css."
        )

    @pytest.mark.parametrize("cls", REQUIRED_FO_CLASSES)
    def test_fo_class_does_not_leak_into_legacy_stylesheets(self, cls):
        legacy_paths = [
            REPO_ROOT / "static" / "styles.css",
            REPO_ROOT / "static" / "chrome.css",
            REPO_ROOT / "static" / "sheet-tabs.css",
            REPO_ROOT / "static" / "workspace.css",
            REPO_ROOT / "static" / "modelling-workspace.css",
            REPO_ROOT / "static" / "statements-reporting.css",
        ]
        for legacy in legacy_paths:
            if not legacy.is_file():
                continue
            text = legacy.read_text(encoding="utf-8")
            text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
            pattern = re.compile(rf"\.{re.escape(cls)}\b")
            assert not pattern.search(text), (
                f"Power-user class .{cls} leaked into {legacy.name}."
            )


class TestPowerCssOnlyConsumesFoTokens:
    def test_no_raw_hex_colours(self):
        text = POWER_CSS.read_text(encoding="utf-8")
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        offenders = []
        for line_no, raw in enumerate(text.splitlines(), start=1):
            if re.search(r"#[0-9a-fA-F]{3,8}\b", raw):
                offenders.append((line_no, raw))
        assert not offenders, (
            "power-user.css must not declare raw hex colours. "
            "Offends:\n  " +
            "\n  ".join(f"L{n}: {l}" for n, l in offenders)
        )

    def test_no_raw_rgb_colours_in_user_declared_blocks(self):
        # Note: the palette shadow uses rgba() — that's the ONLY
        # exception, declared explicitly as a box-shadow stack. The
        # rest of the stylesheet must consume --fo-* tokens.
        text = POWER_CSS.read_text(encoding="utf-8")
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        # Find every rgba() and assert it lives inside the
        # .fo-power-palette box-shadow rule (the only allowed use).
        offenders = []
        for line_no, raw in enumerate(text.splitlines(), start=1):
            if re.search(r"\brgba?\s*\(", raw):
                # Allowed: the palette shadow stack only.
                if "rgba(0, 0, 0" in raw or "rgba(15, 23, 42" in raw:
                    continue
                offenders.append((line_no, raw))
        assert not offenders, (
            "power-user.css may only use rgba() inside the palette "
            "shadow stack. Offends:\n  " +
            "\n  ".join(f"L{n}: {l}" for n, l in offenders)
        )

    def test_uses_fo_tokens(self):
        text = POWER_CSS.read_text(encoding="utf-8")
        for token in [
            "--fo-paper", "--fo-line", "--fo-ink", "--fo-ink-soft",
            "--fo-ink-faint", "--fo-brand-50", "--fo-brand-600",
            "--fo-brand-700", "--fo-brand-800",
            "--fo-rag-neutral-bg",
            "--fo-font-ui", "--fo-font-mono",
            "--fo-text-xs", "--fo-text-sm", "--fo-text-md",
            "--fo-text-lg", "--fo-text-xl",
            "--fo-s2", "--fo-s3", "--fo-s4", "--fo-s5",
            "--fo-r-sm", "--fo-r-md", "--fo-r-lg",
            "--fo-weight-medium", "--fo-weight-semibold",
            "--fo-t-fast", "--fo-ease",
        ]:
            assert token in text, (
                f"power-user.css must consume {token} from tokens.css."
            )

    def test_no_legacy_palette_alias(self):
        text = POWER_CSS.read_text(encoding="utf-8")
        for legacy in ["--sidebar-bg", "--primary", "--surface",
                        "--border", "--text-secondary"]:
            pattern = re.compile(rf"var\(\s*{re.escape(legacy)}\b")
            assert not pattern.search(text), (
                f"power-user.css must not reference legacy token {legacy}."
            )


class TestBaseHtmlWiring:
    def test_power_css_linked(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert "/static/power-user.css" in text, (
            "base.html must link static/power-user.css."
        )

    def test_load_order_full_ui_stack(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        order = [
            "/static/tokens.css",
            "/static/styles.css",
            "/static/chrome.css",
            "/static/sheet-tabs.css",
            "/static/workspace.css",
            "/static/modelling-workspace.css",
            "/static/statements-reporting.css",
            "/static/power-user.css",
        ]
        positions = [text.find(p) for p in order]
        assert all(p > 0 for p in positions), (
            f"All UI stylesheets must be linked. Positions: {positions}"
        )
        assert positions == sorted(positions), (
            f"Stylesheets MUST load in order: {order}"
        )


class TestPartials:
    def test_palette_partial_declares_modal_palette(self):
        text = PALETTE_PARTIAL.read_text(encoding="utf-8")
        for needle in (
            "fo-power-palette",
            "fo-power-palette__input",
            "fo-power-palette__results",
            "role=\"dialog\"",
            "aria-modal=\"true\"",
            "data-fo-power-palette",
            "Search projects, scenarios, sheets, reports",
        ):
            assert needle in text, (
                f"Palette partial must declare {needle!r}."
            )

    def test_palette_partial_lists_all_target_groups(self):
        # PART A: Projects, Scenarios, Sheets, Reports, BESS, Lender,
        # Sensitivity, Compare, Financial Statements, Settings, Help.
        text = PALETTE_PARTIAL.read_text(encoding="utf-8")
        for needle in (
            "Modelling sheets",
            "Reports & workspaces",
            "Executive Summary",
            "IC Pack",
            "Investment Committee",
            "Credit Pack",
            "Lender Workspace",
            "Sensitivity",
            "Compare",
            "BESS",
            "Help",
        ):
            assert needle in text, (
                f"Palette partial must list {needle!r} as a quick action."
            )

    def test_shortcuts_partial_declares_all_shortcuts(self):
        text = SHORTCUTS_PARTIAL.read_text(encoding="utf-8")
        # PART E: Ctrl+K, F9, Ctrl+S, Esc, ?
        for needle in ("Ctrl", "K", "F9", "S", "Esc", "?"):
            assert needle in text, (
                f"Shortcuts partial must reference {needle!r}."
            )
        # Sheet shortcuts: Ctrl+1..8, Ctrl+9 (scenarios), Ctrl+0
        # (compare)
        for needle in ("Ctrl", "1", "2", "3", "4", "5", "6", "7", "8",
                        "9", "0"):
            assert needle in text, (
                f"Shortcuts partial must reference {needle!r}."
            )

    def test_jump_partial_declares_floating_button(self):
        text = JUMP_PARTIAL.read_text(encoding="utf-8")
        for needle in (
            "fo-power-jump",
            "fo-power-jump__btn",
            "data-fo-power-palette-trigger",
            "Ctrl + K",
        ):
            assert needle in text, (
                f"Jump partial must declare {needle!r}."
            )

    def test_recent_partial_uses_session_storage_hook(self):
        text = RECENT_PARTIAL.read_text(encoding="utf-8")
        for needle in (
            "fo-power-recent",
            "data-fo-power-recent",
            "data-fo-power-recent-list",
            "data-fo-power-recent-clear",
            "No recent activity yet",
        ):
            assert needle in text, (
                f"Recent partial must declare {needle!r}."
            )

    def test_empty_partial_declares_refreshed_layout(self):
        text = EMPTY_PARTIAL.read_text(encoding="utf-8")
        for needle in (
            "fo-power-empty",
            "fo-power-empty__icon",
            "fo-power-empty__title",
            "fo-power-empty__body",
            "fo-power-empty__actions",
            "fo-power-empty__btn",
            "fo-power-empty__btn--primary",
        ):
            assert needle in text, (
                f"Empty partial must declare {needle!r}."
            )

    def test_skeleton_partial_declares_three_variants(self):
        text = SKELETON_PARTIAL.read_text(encoding="utf-8")
        for needle in (
            "fo-power-skeleton",
            "fo-power-skeleton--block",
            "fo-power-skeleton--circle",
            "fo-power-skeleton--row",
        ):
            assert needle in text, (
                f"Skeleton partial must declare {needle!r}."
            )

    def test_init_partial_wires_palette_shortcuts_recent(self):
        text = INIT_PARTIAL.read_text(encoding="utf-8")
        # PART A: Ctrl+K opens palette.
        assert "ctrlKey" in text or "metaKey" in text
        assert "open" in text
        assert "close" in text
        # PART B: fuzzy/substring search.
        assert "score" in text
        # PART D: sessionStorage recent.
        assert "sessionStorage" in text
        # PART E: keyboard shortcuts.
        assert "F9" in text
        # PART I: aria-modal / role=dialog already in markup, JS uses
        # focus + blur.
        assert "focus()" in text
        # PART J: re-uses existing switchTab.
        assert "window.switchTab" in text
        # No new backend logic.
        assert "fetch(" not in text or "/run" in text or "/save" in text


# ---------------------------------------------------------------------------
# Mount tests
# ---------------------------------------------------------------------------

class TestWorkspaceShellMountsPowerUser:
    """workspace_shell.html must mount the palette, shortcuts, jump,
    recent, and init partials (PART A, E, F, D)."""

    @pytest.mark.parametrize("partial", [
        "_power_user_palette.html",
        "_power_user_shortcuts.html",
        "_power_user_jump.html",
        "_power_user_recent.html",
        "_power_user_init.html",
    ])
    def test_partial_mounted(self, partial):
        text = WORKSPACE_SHELL_HTML.read_text(encoding="utf-8")
        assert partial in text, (
            f"workspace_shell.html must mount {partial}."
        )


# ---------------------------------------------------------------------------
# Forbidden paths — UI-7 is presentation only
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
    "static/modelling-workspace.css",
    "static/statements-reporting.css",
    "static/modelling/",
    "static/interaction/",
]


class TestForbiddenPathsUntouched:
    @pytest.mark.parametrize("relpath", FORBIDDEN_PATHS)
    def test_path_unchanged(self, relpath, repo_diff):
        if not (REPO_ROOT / relpath).exists():
            pytest.skip(f"{relpath} does not exist in repo")
        assert relpath not in repo_diff.changed_paths, (
            f"UI-7 must not modify {relpath}; presentation only. "
            f"Changed: {sorted(repo_diff.changed_paths)}"
        )


class TestBaseHtmlAdditiveOnly:
    def test_base_html_diff_is_minimal(self, repo_diff):
        if "app/templates/base.html" not in repo_diff.changed_paths:
            return
        hunks = repo_diff.hunks_for("app/templates/base.html")
        added_lines = [h["content"] for h in hunks if h["op"] == "+"]
        removed_lines = [h["content"] for h in hunks if h["op"] == "-"]
        for needle in (
            "/static/styles.css", "/static/tokens.css",
            "/static/chrome.css", "/static/sheet-tabs.css",
            "/static/workspace.css", "/static/modelling-workspace.css",
            "/static/statements-reporting.css",
            "/static/power-user.css",
            '<header class="top-header">',
        ):
            assert not any(needle in line for line in removed_lines), (
                f"UI-7 must not remove existing line containing {needle!r}."
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