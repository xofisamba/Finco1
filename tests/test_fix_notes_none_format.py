"""Regression test for the notes / context format-on-None crash.

When `project_ctx.cit_rate_pct`, `senior_debt_keur`, `loss_carryforward_years`,
or `target_dscr` is `None` (e.g. user-created project before first Run),
`_statements_workspace_notes.html` previously raised
`TypeError: unsupported format string passed to NoneType.__format__`
because Jinja2's `|default(0)` filter only catches `Undefined`, not `None`.

The fix replaces `x|default(0)` with `x or 0` inside `format(...)` calls
(Python's `or` catches `None`) and adds a truthy-check on the conditional
guards (`is defined and x`) so the notes panel renders even when the
project has no Run history yet.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader


REPO_ROOT = Path(__file__).resolve().parents[1]
TPL_NOTES = "partials/_statements_workspace_notes.html"
TPL_SHELL = "partials/workspace_shell.html"


class _ProjectCtx:
    """Minimal stand-in for the real project_ctx used by the index route.

    All numeric attributes are `None` to reproduce the user-created
    pre-Run state."""

    country_iso = "SI"
    cit_rate_pct = None
    loss_carryforward_years = None
    senior_debt_keur = None
    senior_tenor_years = None
    target_dscr = None
    ppa_tariff_eur_mwh = None
    capacity_mw = None
    horizon_years = None
    total_capex_keur = None
    hard_capex_total_keur = None
    opex_y1_total_keur = None


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(REPO_ROOT / "app" / "templates"))
    )


class TestNotesPanelRendersWithAllNone:
    """The notes panel must render without raising when project_ctx
    has no Run history yet (all numeric fields None)."""

    def test_notes_renders_without_exception(self):
        env = _env()
        tmpl = env.get_template(TPL_NOTES)
        out = tmpl.render(project_ctx=_ProjectCtx(), _extra_notes=None)
        assert isinstance(out, str)
        assert "Financial Notes" in out

    def test_notes_contains_fallback_text(self):
        env = _env()
        tmpl = env.get_template(TPL_NOTES)
        out = tmpl.render(project_ctx=_ProjectCtx(), _extra_notes=None)
        # Em-dash placeholder appears when a value is missing.
        assert "—" in out or "0" in out

    def test_notes_contains_SHL_convention(self):
        """Static disclosures always render, even when project_ctx is empty."""
        env = _env()
        tmpl = env.get_template(TPL_NOTES)
        out = tmpl.render(project_ctx=_ProjectCtx(), _extra_notes=None)
        assert "SHL" in out
        assert "Balance Sheet closes" in out


class TestWorkspaceShellNoFormatXDefaultForNumerics:
    """workspace_shell.html uses format() with project_ctx numeric fields.

    `format(project_ctx.X|default(0))` does NOT catch None — the
    fix uses `format(project_ctx.X or 0)` instead. This test enforces
    that no format() call on a project_ctx numeric falls back to
    `|default(...)` — a static-grep check that catches regressions
    faster than rendering."""

    def test_no_format_x_default_for_project_ctx(self):
        text = (REPO_ROOT / "app" / "templates" / TPL_SHELL).read_text(
            encoding="utf-8"
        )
        bad = []
        for line_no, raw in enumerate(text.splitlines(), start=1):
            if "format(project_ctx" not in raw:
                continue
            # Extract the argument list inside the format(...)
            try:
                inside = raw.split("format(project_ctx", 1)[1]
                end = inside.find(")")
                if end == -1:
                    continue
                inside = inside[:end]
            except Exception:
                continue
            if "|default" in inside:
                bad.append((line_no, raw))
        assert not bad, (
            "workspace_shell.html has format(project_ctx.X|default(...)) "
            "calls — the default filter does not catch Python None. "
            "Use `format(project_ctx.X or Y)` instead. Offenders:\n"
            + "\n".join(f"  L{n}: {l}" for n, l in bad)
        )


class TestPartialNoLongerUsesDefaultFilterInsideFormat:
    """Belt-and-suspenders check: ensure we never reintroduce the bug."""

    def test_notes_partial_no_format_x_default(self):
        text = (REPO_ROOT / "app" / "templates" / TPL_NOTES).read_text(
            encoding="utf-8"
        )
        # The bug pattern was `format(project_ctx.X|default(0))`.
        # After the fix, it should be `format(project_ctx.X or 0)`.
        assert "format(project_ctx" not in text or "|default" not in text.split(
            "format(project_ctx", 1
        )[1].split(")", 1)[0], (
            "Bug pattern reintroduced: format(project_ctx.X|default(0)) "
            "does not catch None — use `format(project_ctx.X or 0)` instead."
        )

    def test_shell_partial_no_format_x_default_for_numeric(self):
        text = (REPO_ROOT / "app" / "templates" / TPL_SHELL).read_text(
            encoding="utf-8"
        )
        # Within format() calls, project_ctx.X must use `or Y` not
        # `|default(Y)` (the latter does not catch None).
        for raw in text.splitlines():
            if "format(project_ctx" not in raw:
                continue
            inside = raw.split("format(project_ctx", 1)[1]
            if ")" in inside:
                inside = inside.split(")", 1)[0]
            assert "|default" not in inside, (
                f"Bug pattern reintroduced: format(project_ctx.X|default(...)) "
                f"in workspace_shell.html line: {raw!r}"
            )


class TestReproOriginalBug:
    """Reproduce the original failure mode against the OLD code path.

    If we ever regress, this test catches the TypeError before it
    reaches a user."""

    def test_original_default_filter_does_not_catch_none(self):
        # Direct repro of the Jinja2 quirk that caused the 500.
        # `|default(0)` on a Python None returns None, NOT 0 — and
        # format("{...}".format(None)) raises TypeError.
        # This test documents the *root cause*; it does not assert a
        # specific output, only that the bug pattern is reproducible.
        env = Environment()
        class PC:
            x = None
        try:
            env.from_string(
                "{{ \"{0:.2f}\".format(pc.x|default(0)) }}"
            ).render(pc=PC())
        except TypeError as e:
            assert "unsupported format string" in str(e)
            return
        # If Jinja2 ever changes default semantics to catch None,
        # this test will start failing — re-evaluate the fix.
        pytest.fail(
            "Sanity check: `|default(0)` on None no longer triggers "
            "format() TypeError. Re-evaluate whether the `or 0` fix "
            "is still needed."
        )

    def test_or_catches_none(self):
        env = Environment()
        class PC:
            x = None
        rendered = env.from_string(
            "{{ \"{0:.2f}\".format(pc.x or 0) }}"
        ).render(pc=PC())
        assert rendered == "0.00", (
            "`or 0` correctly catches Python None — this is what the "
            "fix uses."
        )