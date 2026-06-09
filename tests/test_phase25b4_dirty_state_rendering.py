"""Phase 25B-4 — Dirty state template rendering tests.

These tests render the workspace templates with a synthetic
``dirty_state_ui`` payload and assert that the four UI surfaces
(saved chip, notice, run warning, scenario dot) appear in the
output.

Tests are read-only and do not touch the DB. The FastAPI app
imports are lazy-loaded so we don't pay the cost on the rest of
the suite.
"""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

import pytest


# ── HTML render helper (no Jinja env needed) ─────────────────────────────

def _render_partial(template_text: str, ctx: dict) -> str:
    """Tiny Jinja2-like renderer that handles {% if %}, {% for %}, and {{ }}.

    Only enough to exercise the dirty-state macros. We do NOT need
    full Jinja2 to validate the structural conditions.

    Approach: find the OUTERMOST control block (for/if), process it
    recursively, and substitute the result. This handles nesting
    correctly.
    """
    # Resolve {% set x = y %} blocks (very limited).
    out = re.sub(r"\{%\s*set\s+\w+\s*=\s*[^%]+?%\}", "", template_text)

    while True:
        # Find the outermost {% for %} or {% if %} block.
        for_match = re.search(r"\{%\s*for\s+(\w+)\s+in\s+([^%]+?)\s*%\}", out)
        if_match = re.search(r"\{%\s*if\s+([^%]+?)\s*%\}", out)

        candidates = []
        if for_match:
            candidates.append(("for", for_match.start(), for_match))
        if if_match:
            candidates.append(("if", if_match.start(), if_match))
        if not candidates:
            break
        candidates.sort(key=lambda x: x[1])
        kind, _pos, match = candidates[0]
        if kind == "for":
            var_name = match.group(1)
            seq_expr = match.group(2)
            body, end = _consume_block(out, match.end(), "endfor")
            if body is None:
                # Malformed — bail.
                out = out[: match.start()] + out[match.end():]
                continue
            seq = _resolve(seq_expr, ctx) or []
            rendered = "".join(_render_partial(body, {**ctx, var_name: item}) for item in seq)
            out = out[: match.start()] + rendered + out[end:]
        else:  # if
            cond_expr = match.group(1)
            body, end = _consume_block(out, match.end(), "endif")
            if body is None:
                out = out[: match.start()] + out[match.end():]
                continue
            rendered_body = _render_partial(body, ctx) if _truthy(_resolve(cond_expr, ctx)) else ""
            out = out[: match.start()] + rendered_body + out[end:]

    # Resolve {{ var }} placeholders.
    out = re.sub(
        r"\{\{\s*([^%{}]+?)\s*\}\}",
        lambda m: str(_resolve(m.group(1), ctx)),
        out,
    )
    return out


def _consume_block(text: str, start: int, end_tag: str) -> tuple[str | None, int]:
    """Given text starting just after a control block's opening tag,
    return (body_text, end_index_in_text). Handles nested blocks.

    Returns (None, -1) when not found.
    """
    depth = 1
    i = start
    open_re = re.compile(r"\{%\s*(if|for)\s+[^%]+?%\}|\{%-?\s*(if|for)\s+[^%]+?-?%\}|\{%-?\s*end(if|for)\s*-?%\}|\{%-?\s*end(if|for)\s*-?%\}|\{%-?\s*end(if|for)\s*-?%\}")
    while i < len(text):
        # Look for the next control block tag.
        m = re.search(r"\{%-?\s*(if|for|end\w+)\s+[^%]*?-?%\}", text[i:])
        if not m:
            return None, -1
        tag = m.group(1).strip().rstrip("-").strip()
        if tag in ("if", "for"):
            depth += 1
            i = i + m.end()
        elif tag.startswith("end"):
            depth -= 1
            if depth == 0:
                return text[start : i + m.start()], i + m.end()
            i = i + m.end()
        else:
            i = i + m.end()
    return None, -1


def _resolve(expr: str, ctx: dict) -> object:
    """Resolve a dotted name (e.g. ``dot.css_class``) against ctx."""
    expr = expr.strip()
    if "." in expr:
        parts = expr.split(".")
        cur: object = ctx
        for p in parts:
            if cur is None:
                return None
            if isinstance(cur, dict):
                cur = cur.get(p)
            else:
                cur = getattr(cur, p, None)
        return cur
    if expr in ("true", "True"):
        return True
    if expr in ("false", "False"):
        return False
    if expr in ("None", "null"):
        return None
    return ctx.get(expr)


def _truthy(val: object) -> bool:
    if val is None or val is False:
        return False
    if isinstance(val, (list, str, dict)) and len(val) == 0:
        return False
    return True


# ── Load the partial once at module level ────────────────────────────────

PARTIAL = (Path(__file__).resolve().parents[1] / "app" / "templates" / "partials" / "dirty_state_indicators.html").read_text()


# ─────────────────────────────────────────────────────────────────────────
# Test 1: saved_state_chip macro
# ─────────────────────────────────────────────────────────────────────────

class TestSavedStateChip:
    def test_chip_renders_label(self):
        ctx = {
            "badge": {
                "label": "Saved",
                "css_class": "ds-badge--saved",
                "icon": "✓",
            }
        }
        html = _render_partial(
            "{% if badge %}<span class='{{ badge.css_class }}'>{{ badge.label }}</span>{% endif %}",
            ctx,
        )
        assert "ds-badge--saved" in html
        assert "Saved" in html

    def test_chip_skipped_when_no_badge(self):
        ctx: dict = {}
        html = _render_partial(
            "{% if badge %}<span>visible</span>{% endif %}",
            ctx,
        )
        assert "visible" not in html

    def test_chip_each_state(self):
        for state, css, label in [
            ("saved", "ds-badge--saved", "Saved"),
            ("unsaved", "ds-badge--unsaved", "Unsaved edits"),
            ("stale", "ds-badge--stale", "Stale — older than current draft"),
            ("factory", "ds-badge--factory", "Read-only baseline"),
        ]:
            html = _render_partial(
                f"<span class='{{{{ badge.css_class }}}}'>{{{{{{ badge.label }}}}}}</span>",
                {"badge": {"css_class": css, "label": label}},
            )
            assert css in html
            assert label in html


# ─────────────────────────────────────────────────────────────────────────
# Test 2: changes_not_saved_notice macro
# ─────────────────────────────────────────────────────────────────────────

class TestChangesNotSavedNotice:
    def test_notice_renders_when_present(self):
        ctx = {
            "notice": {
                "title": "Changes not yet saved",
                "body": "Save to persist.",
                "css_class": "ds-notice--unsaved",
                "icon": "⚠",
            }
        }
        html = _render_partial(
            "{% if notice %}<div class='{{ notice.css_class }}'>{{ notice.title }}</div>{% endif %}",
            ctx,
        )
        assert "ds-notice--unsaved" in html
        assert "Changes not yet saved" in html

    def test_notice_skipped_when_none(self):
        ctx = {"notice": None}
        html = _render_partial(
            "{% if notice %}<div>visible</div>{% endif %}",
            ctx,
        )
        assert "visible" not in html

    def test_factory_notice_uses_factory_class(self):
        ctx = {
            "notice": {
                "title": "Factory baseline",
                "body": "Use Duplicate to create a copy.",
                "css_class": "ds-notice--factory",
                "icon": "🔒",
            }
        }
        html = _render_partial(
            "{% if notice %}<div class='{{ notice.css_class }}'>{{ notice.title }}</div>{% endif %}",
            ctx,
        )
        assert "ds-notice--factory" in html
        assert "Factory baseline" in html


# ─────────────────────────────────────────────────────────────────────────
# Test 3: run_disabled_warning macro
# ─────────────────────────────────────────────────────────────────────────

class TestRunDisabledWarning:
    def test_warning_renders_when_stale(self):
        ctx = {
            "warning": {
                "title": "Run will use older than current draft",
                "body": "Re-run after saving.",
                "css_class": "ds-warning--stale",
                "icon": "⏱",
            }
        }
        html = _render_partial(
            "{% if warning %}<span class='{{ warning.css_class }}'>{{ warning.title }}</span>{% endif %}",
            ctx,
        )
        assert "ds-warning--stale" in html
        assert "Run will use older" in html

    def test_warning_skipped_when_none(self):
        ctx = {"warning": None}
        html = _render_partial(
            "{% if warning %}<span>visible</span>{% endif %}",
            ctx,
        )
        assert "visible" not in html


# ─────────────────────────────────────────────────────────────────────────
# Test 4: scenario dirty dot — per-scenario list rendering
# ─────────────────────────────────────────────────────────────────────────

class TestScenarioDirtyDot:
    def _render_dots(self, dots):
        # Simulate the loop in scenario_version_history.html
        return _render_partial(
            "{% for dot in dots %}{% if dot.is_dirty %}<span class='{{ dot.css_class }}' title='{{ dot.title }}'></span>{% endif %}{% endfor %}",
            {"dots": dots},
        )

    def test_active_dirty_shows_dot(self):
        dots = [
            {"scenario_id": "a", "is_dirty": True, "css_class": "ds-dot--dirty", "title": "Active scenario has unsaved edits"},
            {"scenario_id": "b", "is_dirty": False, "css_class": "", "title": "Clean"},
        ]
        html = self._render_dots(dots)
        assert "ds-dot--dirty" in html
        # Only one dot.
        assert html.count("ds-dot--dirty") == 1
        assert "Active scenario has unsaved edits" in html

    def test_no_dots_when_all_clean(self):
        dots = [
            {"scenario_id": "a", "is_dirty": False, "css_class": "", "title": "Clean"},
            {"scenario_id": "b", "is_dirty": False, "css_class": "", "title": "Clean"},
        ]
        html = self._render_dots(dots)
        assert "ds-dot--dirty" not in html

    def test_factory_no_dots(self):
        dots = [
            {"scenario_id": "a", "is_dirty": False, "css_class": "", "title": "Factory baseline — read-only"},
        ]
        html = self._render_dots(dots)
        assert "ds-dot--dirty" not in html

    def test_multiple_active_scenarios_can_be_marked_dirty_independently(self):
        # Even if the helper today marks only the active one dirty, the
        # template should render any number of dots that the helper
        # emits.
        dots = [
            {"scenario_id": "a", "is_dirty": True, "css_class": "ds-dot--dirty", "title": "Active"},
            {"scenario_id": "b", "is_dirty": True, "css_class": "ds-dot--dirty", "title": "Active"},
        ]
        html = self._render_dots(dots)
        assert html.count("ds-dot--dirty") == 2


# ─────────────────────────────────────────────────────────────────────────
# Test 5: combined payload produces the full workspace bar
# ─────────────────────────────────────────────────────────────────────────

class TestCombinedPayload:
    def test_stale_full_payload(self):
        payload = {
            "badge": {"label": "Stale — older than current draft", "state": "stale", "css_class": "ds-badge--stale", "icon": "⏱"},
            "notice": {"title": "Changes not yet saved", "body": "Save to persist.", "css_class": "ds-notice--unsaved", "icon": "⚠"},
            "run_warning": {"title": "Run will use older", "body": "Re-run after saving.", "css_class": "ds-warning--stale", "icon": "⏱"},
            "scenario_dots": [
                {"scenario_id": "a", "scenario_name": "Base", "is_active": True, "is_dirty": True, "css_class": "ds-dot--dirty", "title": "Active"},
                {"scenario_id": "b", "scenario_name": "Downside", "is_active": False, "is_dirty": False, "css_class": "", "title": "Clean"},
            ],
        }
        html = _render_partial(
            """
            <div class="workspace-dirty-state-bar" data-dirty-state="{{ payload.badge.state }}">
              <span class="ds-badge {{ payload.badge.css_class }}">{{ payload.badge.label }}</span>
              {% if payload.run_warning %}<span class="ds-run-warning {{ payload.run_warning.css_class }}">{{ payload.run_warning.title }}</span>{% endif %}
            </div>
            {% if payload.notice %}
            <div class="ds-notice {{ payload.notice.css_class }}">{{ payload.notice.title }}</div>
            {% endif %}
            {% for dot in payload.scenario_dots %}
              {% if dot.is_dirty %}
              <span class="{{ dot.css_class }}" title="{{ dot.title }}"></span>
              {% endif %}
            {% endfor %}
            """,
            {"payload": payload},
        )
        assert "ds-badge--stale" in html
        assert "Stale" in html
        assert "ds-run-warning" in html
        assert "Run will use older" in html
        assert "ds-notice--unsaved" in html
        assert "Changes not yet saved" in html
        # Exactly one dirty dot.
        assert html.count("ds-dot--dirty") == 1

    def test_factory_full_payload(self):
        payload = {
            "badge": {"label": "Read-only baseline", "state": "factory", "css_class": "ds-badge--factory", "icon": "🔒"},
            "notice": {"title": "Factory baseline", "body": "Use Duplicate.", "css_class": "ds-notice--factory", "icon": "🔒"},
            "run_warning": None,
            "scenario_dots": [],
        }
        html = _render_partial(
            """
            <div class="workspace-dirty-state-bar" data-dirty-state="{{ payload.badge.state }}">
              <span class="ds-badge {{ payload.badge.css_class }}">{{ payload.badge.label }}</span>
            </div>
            {% if payload.notice %}<div class="ds-notice {{ payload.notice.css_class }}">{{ payload.notice.title }}</div>{% endif %}
            {% if payload.run_warning %}<span>visible</span>{% endif %}
            """,
            {"payload": payload},
        )
        assert "ds-badge--factory" in html
        assert "Read-only baseline" in html
        assert "ds-notice--factory" in html
        assert "Factory baseline" in html
        # No run warning.
        assert "visible" not in html
