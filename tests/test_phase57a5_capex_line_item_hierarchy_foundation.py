"""Phase 57A-5: CAPEX line-item hierarchy foundation tests.

These tests pin the foundation for the C.01..C.18 line-
item hierarchy:

1. C.01..C.18 category bands render in the primary path.
2. C.01..C.18 sub-lines render under their parent
   category.
3. C.01..C.16 sub-line amounts are editable in user
   project mode.
4. Category subtotals are derived from sub-lines
   (read-only).
5. Hard CAPEX Total (C.01..C.16) is derived from
   category subtotals (read-only).
6. Grand Total CAPEX (C.01..C.18) is derived from
   sections (read-only).
7. C.17 and C.18 are backend-calculated and are NOT
   editable.
8. Each C.01..C.16 category band carries
   `data-capex-add-line="<code>"` as a foundation for
   the 57A-6 add-line UX.
9. C.17 and C.18 do NOT carry data-capex-add-line
   (they are read-only).
10. No persistence / schema change in 57A-5.

Type: runtime UI + safe data structure change
(DRAFT, no auto-merge). Visual review required.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_TEMPLATES = REPO_ROOT / "app" / "templates"
SHEET_CAPEX = APP_TEMPLATES / "partials" / "sheet_capex.html"


@pytest.fixture(scope="module")
def sheet_html_text() -> str:
    return SHEET_CAPEX.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def env():
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    return Environment(
        loader=FileSystemLoader(str(APP_TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )


# A full C.01..C.18 project context.
FULL_PROJECT_CTX = {
    "name": "Full Project",
    "data_source": "User Project",
    "capacity_mw": 50.0,
    "total_capex_keur": 50000.0,
    "capex_items": [],
    "capex_detail_items": {
        "categories": [
            {
                "code": f"C.{i:02d}",
                "name": f"Category {i}",
                "is_backend_calculated": i in [17, 18],
                "children": [
                    {
                        "code": f"C.{i:02d}.0{j}",
                        "name": f"Line {i}.{j}",
                        "amount_keur": 100.0 * (i + j),
                    }
                    for j in range(1, 4)
                ],
            }
            for i in range(1, 19)
        ],
        "grand_total_keur": 50000.0,
        "hard_capex_total_keur": 45000.0,
        "financing_total_keur": 5000.0,
    },
    "construction_months": 18,
    "hard_capex_total_keur": 45000.0,
    "financing_total_keur": 5000.0,
    "grand_total_keur": 50000.0,
}


@pytest.fixture(scope="module")
def rendered_full_html(env):
    tmpl = env.get_template("partials/sheet_capex.html")
    return tmpl.render(
        project_ctx=FULL_PROJECT_CTX,
        is_user_project=True,
    )


# ---------------------------------------------------------------------------
# 1. C.01..C.18 category bands
# ---------------------------------------------------------------------------


class TestC01ToC18CategoryBands:
    @pytest.mark.parametrize(
        "code",
        [f"C.{i:02d}" for i in range(1, 19)],
    )
    def test_category_band_present(self, rendered_full_html, code):
        # Every C.01..C.18 category band must be
        # present in the rendered HTML.
        assert (
            f'data-capex-category="{code}"' in
            rendered_full_html
        ), (
            f"Category {code!r} must be present in the "
            f"rendered HTML."
        )


# ---------------------------------------------------------------------------
# 2. Sub-lines render under each category
# ---------------------------------------------------------------------------


class TestSubLinesRendered:
    def test_sub_lines_present(self, rendered_full_html):
        # Sub-lines have data-capex-code-full="C.XX.YY".
        matches = re.findall(
            r'data-capex-code-full="(C\.\d{2}\.\d{2})"',
            rendered_full_html,
        )
        # 18 categories x 3 sub-lines = 54 sub-lines.
        assert len(set(matches)) == 54, (
            f"Expected 54 unique sub-lines. Found "
            f"{len(set(matches))}."
        )

    def test_sub_line_amounts_present(self, rendered_full_html):
        # Sub-line amount cells have data-capex-code with
        # sanitized code (no dots).
        matches = re.findall(
            r'data-capex-code="(C_\d{2}_\d{2})"',
            rendered_full_html,
        )
        assert len(set(matches)) == 54, (
            f"Expected 54 unique sanitized sub-line codes "
            f"in data-capex-code. Found {len(set(matches))}."
        )


# ---------------------------------------------------------------------------
# 3. C.01..C.16 editable in user project mode
# ---------------------------------------------------------------------------


class TestC01ToC16Editable:
    @pytest.mark.parametrize(
        "code",
        [f"C.{i:02d}.01" for i in range(1, 17)],
    )
    def test_sub_line_input_editable(
        self, rendered_full_html, code,
    ):
        sanitized = code.replace(".", "_")
        # The sub-line amount input has
        # name="capex_<sanitized>_keur".
        pattern = re.compile(
            r'name="capex_'
            + re.escape(sanitized)
            + r'_keur"'
        )
        assert pattern.search(rendered_full_html), (
            f"Sub-line {code!r} (sanitized: "
            f"{sanitized!r}) must have an editable "
            f"<input name=\"capex_{sanitized}_keur\"> "
            f"in user project mode."
        )


# ---------------------------------------------------------------------------
# 4. Category subtotals derived (read-only)
# ---------------------------------------------------------------------------


class TestCategorySubtotalsDerived:
    @pytest.mark.parametrize(
        "code",
        [f"C.{i:02d}" for i in range(1, 17)],
    )
    def test_category_subtotal_present(
        self, rendered_full_html, code,
    ):
        # Each C.01..C.16 category must have a subtotal
        # row.
        assert (
            f'data-capex-row="cat-subtotal-{code}"' in
            rendered_full_html
        ), (
            f"Category subtotal for {code!r} must be "
            f"present."
        )


# ---------------------------------------------------------------------------
# 5. Hard CAPEX Total
# ---------------------------------------------------------------------------


class TestHardCapexTotal:
    def test_hard_capex_total_present(self, rendered_full_html):
        assert "data-capex-row=\"hard-capex-total\"" in (
            rendered_full_html
        )
        assert "Hard CAPEX Total" in rendered_full_html


# ---------------------------------------------------------------------------
# 6. Grand Total
# ---------------------------------------------------------------------------


class TestGrandTotal:
    def test_grand_total_present(self, rendered_full_html):
        assert "data-capex-row=\"grand-total\"" in (
            rendered_full_html
        )
        assert "Total CAPEX" in rendered_full_html


# ---------------------------------------------------------------------------
# 7. C.17 and C.18 are read-only
# ---------------------------------------------------------------------------


class TestC17C18ReadOnly:
    @pytest.mark.parametrize("code", ["C.17.01", "C.18.01"])
    def test_financing_line_not_editable(
        self, rendered_full_html, code,
    ):
        sanitized = code.replace(".", "_")
        # C.17 and C.18 sub-lines must NOT have an
        # editable <input> in user project mode.
        pattern = re.compile(
            r'name="capex_'
            + re.escape(sanitized)
            + r'_keur"'
        )
        assert not pattern.search(rendered_full_html), (
            f"Financing/reserve line {code!r} must NOT "
            f"have an editable <input>."
        )

    def test_financing_lines_have_data_financing_class(
        self, rendered_full_html,
    ):
        # C.17 / C.18 rows have the data_financing CSS
        # class.
        assert "lig-row--data-financing" in (
            rendered_full_html
        )


# ---------------------------------------------------------------------------
# 8. data-capex-add-line foundation hook
# ---------------------------------------------------------------------------


class TestAddLineHook:
    @pytest.mark.parametrize(
        "code",
        [f"C.{i:02d}" for i in range(1, 17)],
    )
    def test_c01_to_c16_has_add_line(
        self, rendered_full_html, code,
    ):
        # Each C.01..C.16 category band must have a
        # data-capex-add-line="<code>" attribute.
        assert (
            f'data-capex-add-line="{code}"' in
            rendered_full_html
        ), (
            f"Category {code!r} must have "
            f"data-capex-add-line=\"{code}\" as the "
            f"foundation for the 57A-6 add-line UX."
        )

    def test_c17_does_not_have_add_line(
        self, rendered_full_html,
    ):
        # C.17 must NOT have data-capex-add-line="C.17"
        # (it is backend-calculated and must not be
        # user-editable).
        assert (
            'data-capex-add-line="C.17"' not in
            rendered_full_html
        ), (
            "C.17 must NOT have data-capex-add-line. "
            "Financing rows are backend-calculated."
        )

    def test_c18_does_not_have_add_line(
        self, rendered_full_html,
    ):
        assert (
            'data-capex-add-line="C.18"' not in
            rendered_full_html
        ), (
            "C.18 must NOT have data-capex-add-line. "
            "Reserve rows are backend-calculated."
        )


# ---------------------------------------------------------------------------
# 9. No persistence / schema change
# ---------------------------------------------------------------------------


class TestNoPersistenceSchemaChange:
    def test_no_main_web_changes(self):
        import subprocess
        r = subprocess.run(
            ["git", "diff", "origin/main", "--name-only", "--",
             "main_web.py"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert not r.stdout.strip(), (
            "57A-5 must NOT modify main_web.py."
        )

    def test_no_services_changes(self):
        import subprocess
        r = subprocess.run(
            ["git", "diff", "origin/main", "--name-only", "--",
             "app/services/"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert not r.stdout.strip(), (
            "57A-5 must NOT modify app/services/."
        )

    def test_no_persistence_changes(self):
        import subprocess
        # Skip on 57A-9X branches: the persistence layer is
        # the explicit target of the 57A-9 save/load + Run +
        # Excel sub-arc. Same pattern as the 57A-5B /
        # 57A-8 skip-guards added in the same PR.
        r_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r_branch.returncode == 0:
            branch = r_branch.stdout.strip()
            if "57a9" in branch.lower():
                pytest.skip(
                    f"57A-9X branch — app/persistence/ is the "
                    f"target of the save/load wiring "
                    f"(current: {branch!r})."
                )
        r = subprocess.run(
            ["git", "diff", "origin/main", "--name-only", "--",
             "app/persistence/"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert not r.stdout.strip(), (
            "57A-5 must NOT modify app/persistence/."
        )

    def test_no_domain_changes(self):
        import subprocess
        r = subprocess.run(
            ["git", "diff", "origin/main", "--name-only", "--",
             "app/domain/"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert not r.stdout.strip(), (
            "57A-5 must NOT modify app/domain/."
        )

    def test_no_static_changes(self):
        import subprocess
        # Skip if not on a 57A-5 branch.
        r_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r_branch.returncode == 0:
            branch = r_branch.stdout.strip()
            if (
                branch == "main"
                or (
                    "57a5" not in branch.lower()
                    and "57a-5" not in branch.lower()
                )
            ):
                pytest.skip(
                    f"Not on a 57A-5 branch (current: "
                    f"{branch!r})."
                )
        for path in ["static/app.js", "static/styles.css"]:
            r = subprocess.run(
                ["git", "diff", "origin/main", "--name-only", "--",
                 path],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
            )
            assert not r.stdout.strip(), (
                f"57A-5 must NOT modify {path}."
            )

    def test_no_migration_files(self):
        import subprocess
        r = subprocess.run(
            ["git", "diff", "origin/main", "--name-only", "--",
             "alembic/", "migrations/"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert not r.stdout.strip(), (
            "57A-5 must NOT add migration files."
        )


# ---------------------------------------------------------------------------
# 10. File-scope
# ---------------------------------------------------------------------------


class TestFileScope:
    def test_sheet_capex_changed(self):
        import subprocess
        r_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r_branch.returncode == 0:
            branch = r_branch.stdout.strip()
            if branch == "main":
                pytest.skip(
                    "On main branch; 57A-5 has been merged. "
                    "This test is only meaningful on the "
                    "57A-5 unmerged branch."
                )
            if (
                "57a5" not in branch.lower()
                and "57a-5" not in branch.lower()
            ):
                pytest.skip(
                    f"Not on a 57A-5 branch (current: "
                    f"{branch!r})."
                )
        r = subprocess.run(
            ["git", "diff", "origin/main", "--name-only", "--",
             "app/templates/partials/sheet_capex.html"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0
        assert (
            r.stdout.strip()
            == "app/templates/partials/sheet_capex.html"
        )

    def test_no_documentation_files_added(self):
        import subprocess
        # Skip if not on a 57A-5 branch.
        r_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r_branch.returncode == 0:
            branch = r_branch.stdout.strip()
            if (
                branch == "main"
                or (
                    "57a5" not in branch.lower()
                    and "57a-5" not in branch.lower()
                )
            ):
                pytest.skip(
                    f"Not on a 57A-5 branch (current: "
                    f"{branch!r})."
                )
        r = subprocess.run(
            ["git", "diff", "origin/main", "--name-only", "--",
             "docs/", "reports/"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert not r.stdout.strip(), (
            f"57A-5 must not modify docs/ or reports/. "
            f"Found: {r.stdout.strip()!r}."
        )


# ---------------------------------------------------------------------------
# 11. rc1 untouched
# ---------------------------------------------------------------------------


class TestRc1Untouched:
    def test_rc1_sha_unchanged(self):
        import subprocess
        r = subprocess.run(
            ["git", "rev-parse", "--verify",
             "b425a0708719eaa5e1d922b1008e5609758e0ad4"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, (
            "rc1 frozen SHA must still resolve."
        )


# ---------------------------------------------------------------------------
# 12. No-go copy
# ---------------------------------------------------------------------------


class TestNoNoGoCopy:
    @pytest.mark.parametrize(
        "forbidden",
        [
            "validated",
            "guaranteed",
            "100% accurate",
            "production-ready",
            "saas-ready",
        ],
    )
    def test_no_forbidden_claims(self, sheet_html_text, forbidden):
        pattern = re.compile(
            r"\b" + re.escape(forbidden) + r"\b",
            re.IGNORECASE,
        )
        assert not pattern.search(sheet_html_text), (
            f"Forbidden term {forbidden!r} must not "
            f"appear in sheet_capex.html."
        )
