"""UX-2D-OPEX-READABILITY-CLEANUP.

OPEX detail sheet (sheet_opex_detail.html) — the live-rendered OPEX tab —
read like a raw data dump: years were visually disconnected, category
hierarchy was weak, the legend was dense, and numeric values had no
thousands-separator readability. This phase is presentation-only:
year-group banding CSS, stronger category-row styling, a simplified
legend, zebra-striped child rows, and thousands-separator formatting on
year/budget values. No model, formula, runtime, export, or persistence
logic changes.

Tests:
  1. OPEX schedule renders year columns (Y1..Yn headers).
  2. Category rows render (code + name + total cells).
  3. Category hierarchy / indentation classes exist (fc-cat-row,
     fc-cell--indented, fc-child-indicator, uppercase category styling).
  4. No important OPEX rows removed (category + child + notes content
     still present).
  5. OPEX remains editable where previously editable (no change to the
     is_user_project / editability branches).
  6. No internal terminology leaks (factory, golden, create_default_,
     template_source).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from jinja2 import Environment

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")

TEMPLATE_PATH = Path(REPO_ROOT) / "app/templates/partials/sheet_opex_detail.html"


def _render(ctx):
    env = Environment()
    tmpl = env.from_string(TEMPLATE_PATH.read_text())
    return tmpl.render(**ctx)


def _base_ctx(is_user_project=False):
    return {
        "is_user_project": is_user_project,
        "project_ctx": {
            "name": "Test Project",
            "horizon_years": 25,
            "opex_y1_total_keur": 1234.5,
            "opex_contingency_pct": 4,
            "opex_contingency_method": "pct-of-total",
            "opex_detail_items": [
                {
                    "code": "B.01",
                    "name": "Technical Management",
                    "is_contingency": False,
                    "contingency_pct": 0.0,
                    "yearly_totals": [1234.5] * 25,
                    "children": [
                        {
                            "code": "B.01.01",
                            "name": "Asset Management Contract",
                            "budget_y1_keur": 1234.5,
                            "inflation_pct": 2.0,
                            "wth_rate": 0.0,
                            "notes": "annual fee",
                            "active_flags": [1] * 25,
                            "yearly_values": [1234.5] * 25,
                        },
                        {
                            "code": "B.01.02",
                            "name": "Site Security",
                            "budget_y1_keur": 50.0,
                            "inflation_pct": 0.0,
                            "wth_rate": 0.0,
                            "notes": None,
                            "active_flags": [1] * 25,
                            "yearly_values": [50.0] * 25,
                        },
                    ],
                },
                {
                    "code": "B.13",
                    "name": "Contingency",
                    "is_contingency": True,
                    "contingency_pct": 4.0,
                    "yearly_totals": [60.0] * 25,
                    "children": [],
                },
            ],
            "opex_items": [],
        },
    }


class TestYearColumnsRender:
    def test_year_headers_present(self):
        rendered = _render(_base_ctx())
        for y in (1, 2, 8, 9, 16, 25):
            assert f">Y{y}<" in rendered, f"Year column Y{y} header missing"

    def test_year_group_classes_present(self):
        rendered = _render(_base_ctx())
        assert "yr-early" in rendered
        assert "yr-mid" in rendered


class TestCategoryRowsRender:
    def test_category_code_and_name_render(self):
        rendered = _render(_base_ctx())
        assert "B.01" in rendered
        assert "Technical Management" in rendered

    def test_category_total_cells_render(self):
        rendered = _render(_base_ctx())
        assert "fc-cell--cat-total" in rendered


class TestCategoryHierarchyClasses:
    def test_cat_row_class_present(self):
        rendered = _render(_base_ctx())
        assert "fc-cat-row" in rendered

    def test_indentation_classes_present(self):
        rendered = _render(_base_ctx())
        assert "fc-cell--indented" in rendered
        assert "fc-child-indicator" in rendered

    def test_category_name_styling_hook_present(self):
        rendered = _render(_base_ctx())
        assert "fc-cat-name" in rendered

    def test_category_name_uppercase_is_css_only(self):
        # The rendered HTML text must keep its original case so other
        # tests / data integrity checks that search for exact category
        # names still match -- visual caps come from CSS text-transform.
        rendered = _render(_base_ctx())
        assert "Technical Management" in rendered
        assert "TECHNICAL MANAGEMENT" not in rendered


class TestNoImportantRowsRemoved:
    def test_all_categories_present(self):
        rendered = _render(_base_ctx())
        assert "B.01" in rendered
        assert "B.13" in rendered

    def test_all_children_present(self):
        rendered = _render(_base_ctx())
        assert "Asset Management Contract" in rendered
        assert "Site Security" in rendered

    def test_notes_cell_present(self):
        rendered = _render(_base_ctx())
        assert "annual fee" in rendered

    def test_contingency_badge_present(self):
        rendered = _render(_base_ctx())
        assert "badge-contingency" in rendered


class TestEditabilityPreserved:
    def test_user_project_budget_cell_unchanged_structure(self):
        rendered = _render(_base_ctx(is_user_project=True))
        assert "Line editing deferred" in rendered

    def test_reference_project_budget_cell_unchanged_structure(self):
        rendered = _render(_base_ctx(is_user_project=False))
        assert "fc-cell-runtime" in rendered


class TestNumericReadability:
    def test_thousands_separator_on_large_value(self):
        rendered = _render(_base_ctx())
        assert "1,234.50" in rendered


class TestNoInternalTerminologyLeak:
    @pytest.mark.parametrize(
        "forbidden", ["factory", "create_default_", "golden", "template_source"]
    )
    def test_forbidden_term_not_rendered_as_text(self, forbidden):
        rendered = _render(_base_ctx())
        assert f">{forbidden}<" not in rendered.lower()
        assert f"{forbidden} default value" not in rendered.lower()


class TestUX2DFileScope:
    ALLOWED_PREFIXES = (
        "app/templates/partials/sheet_opex_detail.html",
        "tests/test_ux2d_",
    )
    DISALLOWED_PREFIXES = (
        "domain/",
        "app/waterfall_core.py",
        "app/input_adapter.py",
        "app/project_factories.py",
        "app/persistence/",
        "app/services/",
        "app/export/",
        "main_web.py",
        "main_api.py",
    )

    def test_file_scope(self):
        import shutil
        import subprocess
        if shutil.which("git") is None:
            pytest.skip("git not available")
        result = subprocess.run(
            ["git", "-C", REPO_ROOT, "diff", "--name-only", "origin/main"],
            capture_output=True, text=True,
        )
        changed = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        for f in changed:
            assert not any(f.startswith(p) for p in self.DISALLOWED_PREFIXES), (
                f"UX-2D must not touch {f}"
            )
            assert any(f.startswith(p) for p in self.ALLOWED_PREFIXES), (
                f"UX-2D file outside allowed scope: {f}"
            )
