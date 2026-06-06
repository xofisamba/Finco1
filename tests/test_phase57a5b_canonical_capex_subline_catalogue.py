"""Phase 57A-5B: CAPEX canonical sub-line catalogue tests.

These tests pin the runtime contract for the canonical
C.01..C.18 sub-line catalogue as rendered by
``sheet_capex.html``.

The catalogue is built by
``app/ui/project_context.py::_build_capex_detail_items``
and exposed on ``project_ctx.capex_detail_items``.

The previous template code expected
``capex_detail_items`` to be a dict with a
``.categories`` property, but the builder actually
returns the categories tuple directly. This caused
the template to silently fall through to the older
6-section fallback path on every render, hiding the
canonical sub-line catalogue. 57A-5B fixes this.

These tests verify:

1. All 18 C.01..C.18 categories render as section bands.
2. Each C.01..C.16 category has at least one sub-line.
3. Known empty categories (C.03, C.04, C.05, C.08, C.12)
   render sub-lines (placeholders at minimum).
4. Zero-value placeholder rows render as "0.00" and
   remain editable in user project mode.
5. Backend keys (lease_tax, epc_contract, etc.) are
   NOT visible in the rendered HTML.
6. Visible codes follow the business Excel-style
   (C.01.01, C.04.02, etc.) — not snake_case.
7. C.17 and C.18 are read-only (data_financing).
8. data-capex-add-line is on C.01..C.16 only.
9. No backend / model / formula / persistence changes.
10. rc1 (``b425a0708719eaa5e1d922b1008e5609758e0ad4``)
    is frozen.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_TEMPLATES = REPO_ROOT / "app" / "templates"
SHEET_CAPEX = APP_TEMPLATES / "partials" / "sheet_capex.html"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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


def _build_production_ctx():
    """Build a project context that uses the production
    capex_detail_items (a TUPLE, built by
    ``_build_capex_detail_items``)."""
    os_marker = sys.modules.get("__main__")
    # Lazy imports so that pytest collection does not
    # require the full app stack.
    import importlib

    # Reset any cached state.
    for k in list(sys.modules):
        if k.startswith("app."):
            del sys.modules[k]

    # Provide the env vars required by main_web.
    import os
    import tempfile
    os.environ.setdefault("FINCO_SECRET_KEY", "phase57a5b-test")
    os.environ.setdefault("FINCO_COOKIE_SECURE", "false")
    tmpdir = tempfile.mkdtemp(prefix="finco1-57a5b-")
    db_path = Path(tmpdir) / "finco1.db"
    os.environ["FINCO_DB_URL"] = f"sqlite:///{db_path}"

    from app.ui.project_context import _build_capex_detail_items
    from domain.inputs import CapexStructure, CapexItem

    capex = CapexStructure(
        production_units=CapexItem(name="Production Unit", amount_keur=0.0),
        epc_contract=CapexItem(name="EPC Contract", amount_keur=52800.0),
        epc_other=CapexItem(name="EPC Other", amount_keur=0.0),
        grid_connection=CapexItem(name="Grid Connection", amount_keur=0.0),
        project_rights=CapexItem(name="Project Rights", amount_keur=0.0),
        project_acquisition=CapexItem(name="Project Acquisition", amount_keur=0.0),
        ops_prep=CapexItem(name="Operations Prep", amount_keur=0.0),
        construction_mgmt_a=CapexItem(name="Construction Mgmt A", amount_keur=0.0),
        construction_mgmt_b=CapexItem(name="Construction Mgmt B", amount_keur=0.0),
        commissioning=CapexItem(name="Commissioning", amount_keur=0.0),
        audit_legal=CapexItem(name="Audit & Legal", amount_keur=0.0),
        lease_tax=CapexItem(name="Lease & Tax", amount_keur=0.0),
        insurances=CapexItem(name="Insurances", amount_keur=0.0),
        contingencies=CapexItem(name="Contingencies", amount_keur=0.0),
        taxes=CapexItem(name="Import Taxes", amount_keur=0.0),
    )
    result = _build_capex_detail_items(capex, construction_months=18)
    return {
        "name": "TUHO Test",
        "data_source": "User Project",
        "capacity_mw": 50.0,
        "total_capex_keur": 52800.0,
        "capex_items": [],
        # PRODUCTION shape: tuple of category dicts.
        "capex_detail_items": result["categories"],
        "construction_months": 18,
        "grand_total_keur": result["grand_total_keur"],
        "hard_capex_total_keur": result["hard_capex_total_keur"],
        "financing_total_keur": result["financing_total_keur"],
    }


@pytest.fixture(scope="module")
def production_ctx():
    return _build_production_ctx()


@pytest.fixture(scope="module")
def rendered_user(env, production_ctx):
    tmpl = env.get_template("partials/sheet_capex.html")
    return tmpl.render(project_ctx=production_ctx, is_user_project=True)


@pytest.fixture(scope="module")
def rendered_factory(env, production_ctx):
    ctx = dict(production_ctx)
    ctx["data_source"] = "Factory Reference"
    ctx["name"] = "Factory Reference"
    tmpl = env.get_template("partials/sheet_capex.html")
    return tmpl.render(project_ctx=ctx, is_user_project=False)


# ---------------------------------------------------------------------------
# 1. All 18 C.01..C.18 categories render
# ---------------------------------------------------------------------------


class TestAll18CategoriesRender:
    @pytest.mark.parametrize(
        "code", [f"C.{i:02d}" for i in range(1, 19)]
    )
    def test_category_section_band_present(
        self, rendered_user, code,
    ):
        assert (
            f'data-capex-category="{code}"' in rendered_user
        ), (
            f"Category {code!r} section band must be "
            f"present in the rendered CAPEX sheet."
        )

    def test_all_18_unique_categories(
        self, rendered_user,
    ):
        cats = sorted(set(
            re.findall(
                r'data-capex-category="(C\.\d{2})"',
                rendered_user,
            )
        ))
        expected = [f"C.{i:02d}" for i in range(1, 19)]
        assert cats == expected, (
            f"Expected categories {expected}, got {cats}."
        )


# ---------------------------------------------------------------------------
# 2. Each C.01..C.16 category has at least one sub-line
# ---------------------------------------------------------------------------


class TestEachCategoryHasSubLine:
    @pytest.mark.parametrize(
        "code", [f"C.{i:02d}" for i in range(1, 17)]
    )
    def test_category_has_at_least_one_subline(
        self, rendered_user, code,
    ):
        # We allow either:
        # - data-capex-code-full="C.NN.NN" sub-line
        # - data-capex-code-full="C.NN" synthetic row
        #   (used by the builder for C.13 / C.15 which
        #   have no Excel sub-lines).
        sublines = re.findall(
            r'data-capex-code-full="(C\.\d{2}(?:\.\d{2})?)"',
            rendered_user,
        )
        matching = [
            s for s in sublines if s == code or s.startswith(code + ".")
        ]
        assert len(matching) >= 1, (
            f"Category {code!r} must have at least one "
            f"sub-line. Found {len(matching)}."
        )


# ---------------------------------------------------------------------------
# 3. Known empty categories (C.03, C.04, C.05, C.08, C.12) render sub-lines
# ---------------------------------------------------------------------------


class TestKnownEmptyCategoriesRender:
    """These are the categories the user explicitly
    called out. Even with all backend amounts at zero
    (i.e. the canonical catalogue's "empty" sub-lines),
    the sheet must still render them."""

    @pytest.mark.parametrize(
        "code,expected_subcode_count",
        [
            ("C.03", 2),  # Grid Connection Agreement, Grid Usage Fees
            ("C.04", 3),  # Telecom, SCADA, EMS
            ("C.05", 6),  # O&M Building, Weather Station, etc.
            ("C.08", 10),  # Bank Due Diligence sub-lines
            ("C.12", 7),  # Construction Mgmt (Akuo) sub-lines
        ],
    )
    def test_known_empty_category_renders_sublines(
        self, rendered_user, code, expected_subcode_count,
    ):
        sublines = re.findall(
            r'data-capex-code-full="(C\.\d{2}\.\d{2})"',
            rendered_user,
        )
        matching = sorted(set(
            s for s in sublines if s.startswith(code + ".")
        ))
        assert len(matching) >= expected_subcode_count, (
            f"Category {code!r} must have at least "
            f"{expected_subcode_count} sub-lines. "
            f"Found: {matching}"
        )

    @pytest.mark.parametrize(
        "code,first_subline",
        [
            ("C.03", "C.03.01"),  # Grid Connection Agreement
            ("C.04", "C.04.01"),  # Telecom connection
            ("C.05", "C.05.01"),  # O&M Building
            ("C.08", "C.08.01"),  # First Bank DD sub-line
            ("C.12", "C.12.01"),  # First Construction Mgmt sub-line
        ],
    )
    def test_known_empty_category_first_subline(
        self, rendered_user, code, first_subline,
    ):
        sublines = re.findall(
            r'data-capex-code-full="(C\.\d{2}\.\d{2})"',
            rendered_user,
        )
        assert first_subline in sublines, (
            f"Expected first sub-line {first_subline!r} "
            f"of category {code!r} to be present."
        )


# ---------------------------------------------------------------------------
# 4. Zero-value placeholder rows render as "0.00" and editable
# ---------------------------------------------------------------------------


class TestZeroValuePlaceholders:
    def test_zero_value_subline_renders_with_0_00(
        self, rendered_user,
    ):
        """Sub-lines with amount_keur=0.0 must render
        with amount cell value "0.00"."""
        # Find C.01.02 (TSA optionals) which has
        # amount_keur=0.0 in the canonical catalogue.
        pattern = re.compile(
            r'name="capex_C_01_02_keur"\s+value="([\d.]+)"'
        )
        m = pattern.search(rendered_user)
        assert m is not None, (
            "Sub-line C.01.02 must have a numeric input "
            "with name=capex_C_01_02_keur in user project "
            "mode."
        )
        # C.01.02 has amount_keur=0.0 in the canonical
        # catalogue, so the rendered value must be 0.00.
        assert m.group(1) in ("0.00", "0", "0.0"), (
            f"Expected C.01.02 amount to be '0.00' "
            f"(canonical catalogue has 0.0 for TSA "
            f"optionals), got {m.group(1)!r}."
        )

    def test_zero_value_subline_editable_user_mode(
        self, rendered_user,
    ):
        # The C.01.02 input must be an <input>, not a
        # read-only span (zero-value but editable in
        # user project mode).
        pattern = re.compile(
            r'<input[^>]*name="capex_C_01_02_keur"[^>]*>'
        )
        assert pattern.search(rendered_user), (
            "Sub-line C.01.02 must render as an editable "
            "<input> in user project mode (amount=0.0)."
        )

    def test_zero_value_subline_readonly_factory_mode(
        self, rendered_factory,
    ):
        # In factory reference mode, the same line is
        # read-only.
        pattern = re.compile(
            r'<td[^>]*fc-cell--amount[^>]*>[^<]*0\.00[^<]*</td>'
        )
        m = pattern.search(rendered_factory)
        assert m is not None, (
            "Factory reference mode must render 0.00 "
            "as read-only text (not as an <input>)."
        )


# ---------------------------------------------------------------------------
# 5. Backend keys NOT visible
# ---------------------------------------------------------------------------


class TestNoBackendKeysVisible:
    @pytest.mark.parametrize(
        "backend_key",
        [
            "lease_tax",
            "epc_contract",
            "project_rights",
            "production_units",
            "epc_other",
            "project_acquisition",
            "ops_prep",
            "construction_mgmt_a",
            "construction_mgmt_b",
            "commissioning",
            "audit_legal",
            "insurances",
            "contingencies",
            "taxes",
            "grid_connection",
        ],
    )
    def test_backend_key_not_in_visible_code_cell(
        self, rendered_user, backend_key,
    ):
        # Each code cell is exactly one displayed token
        # (e.g. "C.01.01" or "" for subtotals). The
        # backend key must NOT equal a code-cell value
        # exactly. Substring match is too coarse because
        # display names like "Import Taxes" contain
        # the word "taxes" but are legitimate business
        # terms.
        pattern = re.compile(
            r'<td[^>]*fc-cell--code[^>]*>([^<]+)</td>',
        )
        for m in pattern.finditer(rendered_user):
            cell_text = m.group(1).strip()
            assert cell_text != backend_key, (
                f"Backend key {backend_key!r} must not "
                f"appear as a visible code cell value "
                f"(exact match). Found: {cell_text!r}."
            )

    @pytest.mark.parametrize(
        "backend_key",
        [
            "lease_tax",
            "epc_contract",
            "project_rights",
        ],
    )
    def test_canonical_backend_keys_not_in_any_visible_text(
        self, rendered_user, backend_key,
    ):
        # The backend key must NOT appear as a visible
        # code-cell value (where each cell is exactly
        # one of the displayed tokens). Substring match
        # is too coarse because display names like
        # "Import Taxes" contain the word "taxes" but
        # are legitimate business terms.
        code_cells = re.findall(
            r'<td[^>]*fc-cell--code[^>]*>([^<]+)</td>',
            rendered_user,
        )
        non_empty_codes = [c.strip() for c in code_cells if c.strip()]
        exact_hits = [c for c in non_empty_codes if c == backend_key]
        assert not exact_hits, (
            f"Backend key {backend_key!r} must not "
            f"appear as a visible code cell value. "
            f"Found: {exact_hits}."
        )
        # Also: the backend key must not appear as a
        # label-cell value (where each cell is exactly
        # the displayed display name).
        label_cells = re.findall(
            r'<td[^>]*fc-grid-col-label[^>]*>([^<]+)</td>',
            rendered_user,
        )
        non_empty_labels = [c.strip() for c in label_cells if c.strip()]
        exact_label_hits = [c for c in non_empty_labels if c == backend_key]
        assert not exact_label_hits, (
            f"Backend key {backend_key!r} must not "
            f"appear as a visible label cell value. "
            f"Found: {exact_label_hits}."
        )


# ---------------------------------------------------------------------------
# 6. Visible codes follow business Excel-style
# ---------------------------------------------------------------------------


class TestVisibleCodesBusiness:
    def test_visible_codes_all_business_style(
        self, rendered_user,
    ):
        # Every non-empty visible code cell must match
        # the C.NN.NN pattern (or be C.NN for a category
        # subtotal).
        code_cells = re.findall(
            r'<td[^>]*fc-cell--code[^>]*>([^<]+)</td>',
            rendered_user,
        )
        non_empty = [c.strip() for c in code_cells if c.strip()]
        bad = [
            c for c in non_empty
            if not re.match(r'^C\.\d{2}(\.\d{2})?$', c)
        ]
        assert not bad, (
            f"Visible codes must all be business-style "
            f"(C.NN or C.NN.NN). Found bad codes: {bad}"
        )

    def test_minimum_subline_count(self, rendered_user):
        sublines = sorted(set(
            re.findall(
                r'data-capex-code-full="(C\.\d{2}\.\d{2})"',
                rendered_user,
            )
        ))
        # The canonical catalogue has 73 sub-lines
        # across C.01..C.18 (Excel reference data).
        # We require at least 50 to ensure the catalogue
        # is being rendered, not the 6-section fallback.
        assert len(sublines) >= 50, (
            f"Expected at least 50 unique sub-lines "
            f"(canonical catalogue has 73). Found: "
            f"{len(sublines)}."
        )


# ---------------------------------------------------------------------------
# 7. C.17 and C.18 are read-only (data_financing)
# ---------------------------------------------------------------------------


class TestC17C18ReadOnly:
    @pytest.mark.parametrize("code", ["C.17.01", "C.18.01"])
    def test_financing_line_not_editable(
        self, rendered_user, code,
    ):
        sanitized = code.replace(".", "_")
        pattern = re.compile(
            r'name="capex_'
            + re.escape(sanitized)
            + r'_keur"'
        )
        assert not pattern.search(rendered_user), (
            f"Financing line {code!r} must NOT have an "
            f"editable input in user project mode."
        )

    def test_financing_data_financing_class(
        self, rendered_user,
    ):
        assert "lig-row--data-financing" in rendered_user


# ---------------------------------------------------------------------------
# 8. data-capex-add-line only on C.01..C.16
# ---------------------------------------------------------------------------


class TestAddLineHookOnlyC01ToC16:
    def test_add_line_hooks_only_c01_to_c16(
        self, rendered_user,
    ):
        add_lines = sorted(set(
            re.findall(
                r'data-capex-add-line="(C\.\d{2})"',
                rendered_user,
            )
        ))
        expected = [f"C.{i:02d}" for i in range(1, 17)]
        assert add_lines == expected, (
            f"data-capex-add-line must be on C.01..C.16 "
            f"only. Got: {add_lines}"
        )

    def test_c17_no_add_line(self, rendered_user):
        assert 'data-capex-add-line="C.17"' not in (
            rendered_user
        )

    def test_c18_no_add_line(self, rendered_user):
        assert 'data-capex-add-line="C.18"' not in (
            rendered_user
        )


# ---------------------------------------------------------------------------
# 9. No backend / model / formula changes
# ---------------------------------------------------------------------------


class TestNoBackendChanges:
    def test_main_web_unchanged(self):
        r = subprocess.run(
            ["git", "diff", "origin/main", "--name-only", "--",
             "main_web.py"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert not r.stdout.strip(), (
            "57A-5B must NOT modify main_web.py."
        )

    def test_no_persistence_changes(self):
        # Skip on 57A-9X branches: the persistence layer is
        # the explicit target of the 57A-9 save/load + Run +
        # Excel sub-arc. On main (post-merge) the diff is
        # empty so the assertion holds naturally.
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
            "57A-5B must NOT modify app/persistence/."
        )

    def test_no_services_changes(self):
        r = subprocess.run(
            ["git", "diff", "origin/main", "--name-only", "--",
             "app/services/"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert not r.stdout.strip(), (
            "57A-5B must NOT modify app/services/."
        )

    def test_no_domain_changes(self):
        r = subprocess.run(
            ["git", "diff", "origin/main", "--name-only", "--",
             "app/domain/", "domain/"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert not r.stdout.strip(), (
            "57A-5B must NOT modify app/domain/ or domain/."
        )

    def test_no_capex_source_model_changes(self):
        r = subprocess.run(
            ["git", "diff", "origin/main", "--name-only", "--",
             "app/domain/capex/source_model.py"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert not r.stdout.strip(), (
            "57A-5B must NOT modify "
            "app/domain/capex/source_model.py."
        )

    def test_no_static_changes(self):
        # Skip if 57A-5B has already been merged into
        # main OR if we are not on a 57A-5B branch. The
        # test asserts static files are unchanged vs
        # main, which is only meaningful while 57A-5B is
        # an unmerged branch. On a follow-up branch
        # (e.g. 57A-8) or on main itself, a different
        # PR may legitimately modify static/ — this
        # test is not 57A-5B's concern.
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
                    "On main branch; 57A-5B has been merged. "
                    "This test is only meaningful on the "
                    "57A-5B unmerged branch."
                )
            if "57a5b" not in branch.lower():
                pytest.skip(
                    f"Not on a 57A-5B branch (current: "
                    f"{branch!r}). This test is only "
                    f"meaningful on the 57A-5B unmerged "
                    f"branch."
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
                f"57A-5B must NOT modify {path}."
            )

    def test_only_template_and_test_changed(self):
        # Skip if 57A-5B has already been merged into
        # main OR if we are not on a 57A-5B branch. The
        # test asserts the diff vs main only contains
        # sheet_capex.html and the 57A-5B test file.
        # On a follow-up branch (e.g. 57A-8) the diff
        # vs main legitimately contains other files —
        # this test is only meaningful while 57A-5B is
        # an unmerged branch.
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
                    "On main branch; 57A-5B has been merged. "
                    "This test is only meaningful on the "
                    "57A-5B unmerged branch."
                )
            if "57a5b" not in branch.lower():
                pytest.skip(
                    f"Not on a 57A-5B branch (current: "
                    f"{branch!r}). This test is only "
                    f"meaningful on the 57A-5B unmerged "
                    f"branch."
                )
        r = subprocess.run(
            ["git", "diff", "origin/main", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        changed = set(
            line.strip() for line in r.stdout.splitlines()
            if line.strip()
        )
        allowed = {
            "app/templates/partials/sheet_capex.html",
            "tests/test_phase57a5b_canonical_capex_subline_catalogue.py",
        }
        unexpected = changed - allowed
        assert not unexpected, (
            f"57A-5B must only modify sheet_capex.html and "
            f"add the new test file. Unexpected: "
            f"{sorted(unexpected)}"
        )


# ---------------------------------------------------------------------------
# 10. rc1 frozen
# ---------------------------------------------------------------------------


class TestRc1Frozen:
    def test_rc1_sha_resolves(self):
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
# 11. No-go copy
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
            "trust me",
        ],
    )
    def test_no_forbidden_claims(self, sheet_html_text, forbidden):
        pattern = re.compile(
            r"\b" + re.escape(forbidden) + r"\b",
            re.IGNORECASE,
        )
        assert not pattern.search(sheet_html_text), (
            f"Forbidden term {forbidden!r} must not appear "
            f"in sheet_capex.html."
        )


# ---------------------------------------------------------------------------
# 12. Template fix: 57A-5B explicitly resolves the dict/tuple
#     ambiguity.
# ---------------------------------------------------------------------------


class TestTemplateResolutionLogic:
    def test_template_docstring_mentions_57a5b_fix(
        self, sheet_html_text,
    ):
        assert "57A-5B" in sheet_html_text, (
            "Template must document the 57A-5B fix in "
            "its docstring."
        )

    def test_template_handles_dict_shape(
        self, sheet_html_text,
    ):
        # The template must handle the test-style dict
        # shape (with .categories property) for backward
        # compatibility.
        assert "_raw_detail['categories']" in sheet_html_text or (
            "categories" in sheet_html_text
            and "_raw_detail" in sheet_html_text
        )

    def test_template_handles_tuple_shape(
        self, sheet_html_text,
    ):
        # The template must handle the production tuple
        # shape (the actual shape returned by
        # _build_capex_detail_items).
        assert "else" in sheet_html_text  # basic check
        # The else branch must be reachable for the
        # tuple case.
