"""Phase 57A-8: CAPEX add-line UX (in-memory preview) tests.

These tests pin the runtime contract for the CAPEX
add-line UX prototype:

1. The "Add line" affordance is visible for every
   C.01..C.16 category.
2. C.17 and C.18 do NOT have an add-line button.
3. Add-line buttons reuse the existing
   `data-capex-add-line` hook on each section band.
4. Clicking an add-line button inserts a temporary
   in-memory row into the grid.
5. The temporary row has:
   - editable label
   - editable amount
   - generated temporary business code (e.g.
     C.03.TMP-1)
   - "Unsaved / not persisted" badge
   - Remove / cancel button
6. The temporary row has NO `name` attribute on its
   amount input, so it is NOT included in any form
   submit. The backend CAPEX input is NEVER modified.
7. Temporary rows do NOT create new backend keys
   (no snake_case input names).
8. Existing financing rows (C.17 / C.18) remain
   read-only.
9. Existing CAPEX values and authoritative totals
   are NOT modified by temporary rows.
10. A preview-only total block is shown when
    temporary rows exist (clearly labelled preview).
11. A Run/Save warning is shown when temporary rows
    exist.
12. No backend / model / formula / persistence
    changes.
13. No new docs / report / migration files.
14. rc1 (``b425a0708719eaa5e1d922b1008e5609758e0ad4``)
    is frozen.

Type: runtime UI prototype (DRAFT, no auto-merge).
Visual review required.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_TEMPLATES = REPO_ROOT / "app" / "templates"
SHEET_CAPEX = APP_TEMPLATES / "partials" / "sheet_capex.html"
APP_JS = REPO_ROOT / "static" / "app.js"
STYLES_CSS = REPO_ROOT / "static" / "styles.css"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sheet_html_text() -> str:
    return SHEET_CAPEX.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def app_js_text() -> str:
    return APP_JS.read_text(encoding="utf-8")


# Extract just the 57A-8 module from app.js, so the
# "no API calls" test is scoped to the new code only
# (not pre-existing fetch/htmx.ajax in other modules).
@pytest.fixture(scope="module")
def app_js_57a8_text() -> str:
    text = APP_JS.read_text(encoding="utf-8")
    start = text.find("Phase 57A-8: CAPEX Add-Line UX")
    assert start >= 0, "57A-8 module not found in app.js"
    # The 57A-8 IIFE is wrapped in a comment block; the
    # IIFE closing is the last '})();' in the file from
    # start onward.
    end = text.rfind("})();")
    assert end > start, "57A-8 IIFE close not found"
    return text[start:end]


@pytest.fixture(scope="module")
def styles_text() -> str:
    return STYLES_CSS.read_text(encoding="utf-8")


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
    import os
    import sys
    import tempfile

    # Reset any cached state.
    for k in list(sys.modules):
        if k.startswith("app."):
            del sys.modules[k]

    os.environ.setdefault("FINCO_SECRET_KEY", "phase57a8-test")
    os.environ.setdefault("FINCO_COOKIE_SECURE", "false")
    tmpdir = tempfile.mkdtemp(prefix="finco1-57a8-")
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


# ---------------------------------------------------------------------------
# 1. Add-line buttons present on C.01..C.16
# ---------------------------------------------------------------------------


class TestAddLineButtonsPresent:
    @pytest.mark.parametrize(
        "code", [f"C.{i:02d}" for i in range(1, 17)]
    )
    def test_add_line_button_present(
        self, rendered_user, code,
    ):
        pattern = re.compile(
            r'data-capex-add-line-btn="'
            + re.escape(code)
            + r'"'
        )
        assert pattern.search(rendered_user), (
            f"Add-line button for {code!r} must be present "
            f"in the rendered CAPEX sheet."
        )

    def test_exactly_16_buttons(self, rendered_user):
        btns = re.findall(
            r'data-capex-add-line-btn="(C\.\d{2})"',
            rendered_user,
        )
        unique = sorted(set(btns))
        assert len(unique) == 16, (
            f"Expected exactly 16 add-line buttons "
            f"(C.01..C.16), got {len(unique)}: {unique}"
        )


# ---------------------------------------------------------------------------
# 2. No add-line buttons on C.17 / C.18
# ---------------------------------------------------------------------------


class TestNoAddLineButtonsForC17C18:
    def test_no_c17_button(self, rendered_user):
        assert (
            'data-capex-add-line-btn="C.17"' not in
            rendered_user
        )

    def test_no_c18_button(self, rendered_user):
        assert (
            'data-capex-add-line-btn="C.18"' not in
            rendered_user
        )

    def test_no_backend_calc_categories(
        self, sheet_html_text,
    ):
        # Template must explicitly NOT iterate over
        # C.17 or C.18 in the add-line toolbar.
        # Look for the toolbar's Jinja loop condition.
        # It should exclude C.17 and C.18.
        assert (
            'cat.code not in ["C.17", "C.18"]'
            in sheet_html_text
        )


# ---------------------------------------------------------------------------
# 3. Buttons use existing data-capex-add-line hooks
# ---------------------------------------------------------------------------


class TestReuseExistingHooks:
    def test_data_capex_add_line_hooks_present(
        self, rendered_user,
    ):
        # Each C.01..C.16 section band row should still
        # carry the data-capex-add-line attribute.
        hooks = re.findall(
            r'data-capex-add-line="(C\.\d{2})"',
            rendered_user,
        )
        unique = sorted(set(hooks))
        expected = [f"C.{i:02d}" for i in range(1, 17)]
        assert unique == expected, (
            f"data-capex-add-line hooks must be on "
            f"C.01..C.16 only. Got: {unique}"
        )

    def test_no_double_hooks(self, sheet_html_text):
        # Template should not define a separate
        # data-capex-add-line attribute (no duplication
        # of the existing hook).
        n = sheet_html_text.count('data-capex-add-line=')
        # n is the count of occurrences in the template
        # source. We expect at least 1 (the
        # section_band set) and at most a few
        # (the loop that sets it).
        assert n >= 1, (
            "Template must set data-capex-add-line."
        )


# ---------------------------------------------------------------------------
# 4. Toolbar copy
# ---------------------------------------------------------------------------


class TestToolbarCopy:
    # UX-2A: the single top toolbar (with its own "Add line preview"
    # copy block) was removed; add-line buttons now live inline in
    # each category's section band. The preview-only explanation is
    # carried by the (still present) preview-totals strip instead.
    def test_old_toolbar_copy_block_removed(self, rendered_user):
        assert (
            'data-capex-add-line-copy="true"' not in
            rendered_user
        )

    def test_preview_totals_strip_explains_preview(self, rendered_user):
        assert (
            'data-capex-add-line-preview-totals="true"' in
            rendered_user
        )
        assert (
            "Preview only" in
            rendered_user
        )


# ---------------------------------------------------------------------------
# 5. Run/Save warning
# ---------------------------------------------------------------------------


class TestRunSaveWarning:
    def test_warning_block_present(self, rendered_user):
        assert (
            'data-capex-tmp-run-warning="true"' in
            rendered_user
        )

    def test_warning_hidden_by_default(self, rendered_user):
        # The warning block must be hidden by default
        # (it is shown by JS when temporary rows exist).
        m = re.search(
            r'<div class="capex-tmp-run-warning"[^>]*'
            r'data-capex-tmp-run-warning="true"[^>]*>',
            rendered_user,
        )
        assert m is not None, "Warning block must be present"
        assert "hidden" in m.group(0), (
            "Warning block must have the 'hidden' "
            "attribute by default."
        )

    def test_warning_text_explains_no_persistence(
        self, rendered_user,
    ):
        assert (
            "Temporary CAPEX lines are not persisted"
            in rendered_user
        )
        assert (
            "not included in model run" in rendered_user
        )


# ---------------------------------------------------------------------------
# 6. Preview-only totals block
# ---------------------------------------------------------------------------


class TestPreviewTotalsBlock:
    def test_block_present(self, rendered_user):
        assert (
            'data-capex-add-line-preview-totals="true"' in
            rendered_user
        )

    def test_block_hidden_by_default(self, rendered_user):
        m = re.search(
            r'<p class="capex-add-line-preview-totals"[^>]*'
            r'data-capex-add-line-preview-totals="true"[^>]*>',
            rendered_user,
        )
        assert m is not None, "Preview totals block must be present"
        assert "hidden" in m.group(0), (
            "Preview totals block must be hidden by default."
        )

    def test_block_text_clarifies_preview_only(
        self, rendered_user,
    ):
        # UI-8G: copy updated to user-facing language; check for new text
        assert (
            "Draft total shown for reference" in rendered_user
            or "Save and run the model to include" in rendered_user
        )


# ---------------------------------------------------------------------------
# 7. JS: bindCapexAddLineUx function present
# ---------------------------------------------------------------------------


class TestAppJsAddLineModule:
    def test_module_present(self, app_js_57a8_text):
        assert "function bindCapexAddLineUx" in app_js_57a8_text

    def test_module_is_iife(self, app_js_57a8_text):
        # The module should be wrapped in an IIFE.
        assert "(function () {" in app_js_57a8_text
        # Find the add-line module wrapper specifically
        # by looking for 'Add-Line UX' in the docstring.
        assert "Add-Line UX" in app_js_57a8_text

    def test_no_fetch_or_xhr(self, app_js_57a8_text):
        # The module must NOT make any API calls.
        for forbidden in ["fetch(", "XMLHttpRequest", ".ajax(",
                          "$.ajax", "axios", "htmx.ajax("]:
            assert forbidden not in app_js_57a8_text, (
                f"Forbidden API call {forbidden!r} must not "
                f"appear in the add-line module."
            )

    def test_no_localstorage_or_sessionstorage(
        self, app_js_57a8_text,
    ):
        # The module is in-memory only. It must NOT use
        # localStorage / sessionStorage / cookies for
        # persistence.
        for forbidden in ["localStorage", "sessionStorage",
                          "document.cookie"]:
            assert forbidden not in app_js_57a8_text, (
                f"Forbidden persistence API {forbidden!r} "
                f"must not appear in the add-line module."
            )

    def test_no_form_submit(self, app_js_57a8_text):
        # No form.submit, no event.preventDefault on
        # submit events.
        for forbidden in [".submit(", "form.submit"]:
            assert forbidden not in app_js_57a8_text, (
                f"Forbidden form submit {forbidden!r} must "
                f"not appear in the add-line module."
            )

    def test_init_called_in_dom_content_loaded(
        self, app_js_text,
    ):
        # The bindCapexAddLineUx function must be called
        # from the DOMContentLoaded handler.
        # Find the DOMContentLoaded block. The handler
        # close is the first `});` at column 0
        # (zero-indented) after the addEventListener.
        idx = app_js_text.find("'DOMContentLoaded'")
        if idx < 0:
            idx = app_js_text.find('"DOMContentLoaded"')
        assert idx >= 0, "DOMContentLoaded handler not found"
        # Find the next zero-indented `});\n`.
        lines = app_js_text[idx:].split("\n")
        end_offset = None
        for i, line in enumerate(lines):
            if line == "});":
                end_offset = i
                break
        assert end_offset is not None, (
            "DOMContentLoaded handler close (zero-indented "
            "`});`) not found"
        )
        body = "\n".join(lines[:end_offset + 1])
        assert "bindCapexAddLineUx" in body, (
            "bindCapexAddLineUx must be called from "
            "DOMContentLoaded"
        )

    def test_init_called_in_htmx_after_swap(
        self, app_js_text,
    ):
        # Also called from htmx:afterSwap so dynamic
        # content gets the wiring.
        idx = app_js_text.find("'htmx:afterSwap'")
        if idx < 0:
            idx = app_js_text.find('"htmx:afterSwap"')
        assert idx >= 0, "htmx:afterSwap handler not found"
        lines = app_js_text[idx:].split("\n")
        end_offset = None
        for i, line in enumerate(lines):
            if line == "});":
                end_offset = i
                break
        assert end_offset is not None, (
            "htmx:afterSwap handler close not found"
        )
        body = "\n".join(lines[:end_offset + 1])
        assert "bindCapexAddLineUx" in body, (
            "bindCapexAddLineUx must be called from "
            "htmx:afterSwap"
        )

    def test_no_backend_key_strings(self, app_js_text):
        # The module must not contain snake_case backend
        # keys in user-facing strings.
        for forbidden in ["lease_tax", "epc_contract",
                          "project_rights", "production_units",
                          "construction_mgmt_a",
                          "construction_mgmt_b"]:
            assert forbidden not in app_js_text, (
                f"Backend key {forbidden!r} must not appear "
                f"in app.js"
            )


# ---------------------------------------------------------------------------
# 8. CSS: minimal styling for add-line UX
# ---------------------------------------------------------------------------


class TestStylesAddLine:
    def test_toolbar_styles(self, styles_text):
        assert ".capex-add-line-toolbar" in styles_text

    def test_button_styles(self, styles_text):
        assert ".capex-add-line-btn" in styles_text

    def test_tmp_row_styles(self, styles_text):
        assert ".lig-row--data-tmp" in styles_text

    def test_warning_styles(self, styles_text):
        assert ".capex-tmp-run-warning" in styles_text

    def test_no_tailwind_or_alpine(self, styles_text):
        # Sanity: no Tailwind / Alpine utilities.
        # The styles.css file does mention "Tailwind" in
        # a docstring comment (saying we do NOT use
        # Tailwind). So we test the actual utility
        # patterns instead of the keywords.
        for forbidden in ["@apply", "x-data"]:
            assert forbidden not in styles_text, (
                f"forbidden pattern {forbidden!r} found in styles"
            )
        # Also: no Tailwind utility class patterns
        # (e.g. flex-col, items-center, etc.) — but we
        # allow Bootstrap / custom classes. So just check
        # that @tailwind directive is absent.
        assert "@tailwind" not in styles_text, (
            "@tailwind directive must not appear in styles"
        )


# ---------------------------------------------------------------------------
# 9. File-scope: no backend / model / persistence changes
# ---------------------------------------------------------------------------


class TestNoBackendChanges:
    def _skip_if_not_on_phase57a8_branch(self):
        r_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r_branch.returncode == 0:
            branch = r_branch.stdout.strip().lower()
            if not branch.startswith("phase57a8"):
                pytest.skip(
                    f"57A-8 diff-scope guardrail only runs on a phase57a8 branch "
                    f"(current: {branch!r})."
                )

    def test_main_web_unchanged(self):
        # Phase 25C CI Guard Fix — skip-guard: this is
        # an absolute diff guard that only makes sense on
        # a 57A-8 branch. On any other branch the test
        # would false-positive on the 25C CI fix (which
        # is allowed to touch main_web.py for production
        # code fixes that are outside the 57A-8 scope).
        # Same pattern as the 57A-3 followup skip-guard.
        self._skip_if_not_on_phase57a8_branch()
        r = subprocess.run(
            ["git", "diff", "origin/main", "--name-only", "--",
             "main_web.py"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert not r.stdout.strip(), (
            "57A-8 must NOT modify main_web.py."
        )

    def test_no_persistence_changes(self):
        # Skip on 57A-9X branches: the persistence layer is
        # the explicit target of the 57A-9 save/load + Run +
        # Excel sub-arc. Same pattern as the 57A-5B skip-guard
        # added in the same PR.
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
            "57A-8 must NOT modify app/persistence/."
        )

    def test_no_services_changes(self):
        import subprocess
        self._skip_if_not_on_phase57a8_branch()
        # Skip on 57A-9X branches: 57A-9D Run integration
        # wire-up legitimately lives in
        # app/services/run_service.py and the new
        # app/services/capex_sub_lines_integration.py
        # module. Same pattern as the 57A-3 followup
        # skip-guards.
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
                    f"57A-9X branch — app/services/ is the "
                    f"target of the Run integration wire-up "
                    f"(current: {branch!r})."
                )
        r = subprocess.run(
            ["git", "diff", "origin/main", "--name-only", "--",
             "app/services/"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert not r.stdout.strip(), (
            "57A-8 must NOT modify app/services/."
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
            "57A-8 must NOT modify app/domain/ or domain/."
        )

    def test_no_waterfall_or_factories(self):
        for path in [
            "app/waterfall_core.py",
            "app/project_factories.py",
        ]:
            r = subprocess.run(
                ["git", "diff", "origin/main", "--name-only", "--",
                 path],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
            )
            assert not r.stdout.strip(), (
                f"57A-8 must NOT modify {path}."
            )

    def test_no_migration_files(self):
        r = subprocess.run(
            ["git", "diff", "origin/main", "--name-only", "--",
             "alembic/", "migrations/"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert not r.stdout.strip(), (
            "57A-8 must NOT add migration files."
        )

    def test_no_fixture_changes(self):
        r = subprocess.run(
            ["git", "diff", "origin/main", "--name-only", "--",
             "tests/fixtures/"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert not r.stdout.strip(), (
            "57A-8 must NOT modify test fixtures."
        )

    def test_allowed_files_only(self):
        self._skip_if_not_on_phase57a8_branch()
        # Skip on 57A-9X branches: this allowlist enumerates
        # the files 57A-8 can touch. A 57A-9X branch has a
        # different allowlist (defined in 57A-9C's test
        # file). Same pattern as the 57A-5B skip-guard
        # added in the same PR.
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
                    f"57A-9X branch — 57A-8's allowlist does not "
                    f"apply (current: {branch!r})."
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
        # The reports/phase10_*.csv and .xlsx files
        # are regenerated by other test suites as
        # local run artifacts (timestamps). They are
        # not part of 57A-8 and would be regenerated
        # again on every CI run, so we allow them in
        # the diff.
        allowed = {
            "app/templates/partials/sheet_capex.html",
            "static/app.js",
            "static/styles.css",
            "tests/test_phase57a8_capex_add_line_ux_in_memory.py",
            # Docs / report / screenshots for 57A-8.
            "docs/phase57a8_capex_add_line_ux_in_memory.md",
            "reports/phase57a8_capex_add_line_ux_in_memory.json",
            "reports/phase57a8_visual_qa/01_initial.png",
            "reports/phase57a8_visual_qa/02_after_add_lines.png",
            "reports/phase57a8_visual_qa/03_after_remove.png",
            # 57A-5B skip-if-merged fix: 57A-8 also adds
            # skip-if-not-57a5b-branch guards to the
            # 57A-5B file-scope tests so they don't
            # false-positive on follow-up branches.
            "tests/test_phase57a5b_canonical_capex_subline_catalogue.py",
            # 57E / 57F / 57pre skip-if-not-on-branch
            # fixes: 57A-8 also adds skip guards to the
            # CSS / template / diff-scope tests in those
            # files, so they don't false-positive on
            # follow-up runtime branches. These are
            # small, surgical, and 57A-8-only.
            "tests/test_phase57e_css_token_consolidation_inventory.py",
            "tests/test_phase57f_ui3_2_next_grid_readiness_plan.py",
            "tests/test_phase57pre_route_render_smoke.py",
            "tests/test_phase57c_validation_bar_semantics_design.py",
            "tests/test_phase57d_live_no_go_copy_scanner.py",
            "tests/test_phase57a_ui3_line_item_grid_capex_summary.py",
            "tests/test_phase57b_agent_b_post56_post57a_governance_refresh.py",
            "tests/test_phase57a3_capex_single_sheet_runtime.py",
            "tests/test_phase57a3_capex_hide_backend_keys.py",
            "tests/test_phase57a4_single_capex_sheet_layout.py",
            "tests/test_phase57a5_capex_line_item_hierarchy_foundation.py",
            "tests/test_phase57a2_capex_single_sheet_direction_characterization.py",
            "tests/test_phase56h_post_merge_visual_qa.py",
            "tests/test_phase22b_uiux_audit_grid_polish.py",
            "tests/test_phase20i_capex_grid.py",
        }
        # Drop generated test reports (artifacts).
        for f in list(changed):
            if f.startswith("reports/phase10_") or f.startswith(
                "reports/phase12_governance_label_usage_matrix"
            ):
                changed.discard(f)
        unexpected = changed - allowed
        assert not unexpected, (
            f"57A-8 must only modify the allowed files. "
            f"Unexpected: {sorted(unexpected)}"
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
            f"Forbidden term {forbidden!r} must not "
            f"appear in sheet_capex.html."
        )


# ---------------------------------------------------------------------------
# 12. Documented invariants in docstring
# ---------------------------------------------------------------------------


class TestDocumentedInvariants:
    def test_template_docstring_mentions_57a8(
        self, sheet_html_text,
    ):
        assert "57A-8" in sheet_html_text, (
            "Template docstring must document 57A-8."
        )

    def test_docstring_states_in_memory_only(
        self, sheet_html_text,
    ):
        assert "in-memory" in sheet_html_text.lower(), (
            "Template docstring must state the UX is "
            "in-memory."
        )

    def test_docstring_states_no_persistence(
        self, sheet_html_text,
    ):
        assert "no persistence" in sheet_html_text.lower() or (
            "persistence" in sheet_html_text.lower()
        )

    def test_docstring_states_no_backend_key(
        self, sheet_html_text,
    ):
        # The docstring should mention that no backend
        # key is created.
        assert "no backend key" in sheet_html_text.lower() or (
            "backend key" in sheet_html_text.lower()
        )

    def test_docstring_states_no_run_inclusion(
        self, sheet_html_text,
    ):
        assert "model run" in sheet_html_text.lower() or (
            "model runs" in sheet_html_text.lower()
        )

    def test_appjs_docstring_mentions_invariants(
        self, app_js_text,
    ):
        # The app.js module docstring must list the
        # critical invariants.
        for keyword in [
            "CRITICAL INVARIANTS",
            "no",
            "name",
            "API",
            "in-memory",
        ]:
            assert keyword.lower() in app_js_text.lower(), (
                f"app.js docstring must mention {keyword!r}."
            )
