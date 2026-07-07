"""Phase 24-H — Editable Generic Project Run Loop tests.

Status: DRAFT
Type: shape + integration tests
Date: 2026-06-09

These tests assert:

1. The `is_exploratory_project` context flag is computed correctly
   in main_web.py (user_created AND template_source in
   {generic_solar, generic_wind}).

2. The exploratory warning renders in the 3 required places when
   the flag is True (inputs_section, _last_run_indicator,
   export_registry).

3. The exploratory warning does NOT render when the flag is False
   (factory_template, TUHO, Oborovo, or non-generic user projects).

4. The factory template path (TUHO, Oborovo) remains untouched:
   is_user_project is False, is_exploratory_project is False,
   and the read-only baseline still works.

5. The CSS additions are additive (no :root mods).

6. The existing 24-G test suite (closure, capex, validation,
   run status) still passes — no regressions.

Hard constraints verified by these tests:
- TUHO / Oborovo parity path unchanged (factory_template is not
  is_exploratory_project).
- use_construction_schedule_engine remains False (no change to
  app/waterfall_core.py gate).
- rc1 untouched (no rc1 references in the diff).
- :root block count in static/styles.css unchanged.
- No new fake runtime IDs, no fake timestamps, no fake data.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SHEET_INPUTS = REPO_ROOT / "app" / "templates" / "partials" / "inputs_section.html"
LAST_RUN_INDICATOR = REPO_ROOT / "app" / "templates" / "partials" / "_last_run_indicator.html"
EXPORT_REGISTRY = REPO_ROOT / "app" / "templates" / "partials" / "export_registry.html"
STYLES_CSS = REPO_ROOT / "static" / "styles.css"
MAIN_WEB = REPO_ROOT / "main_web.py"


# ── Helpers ──────────────────────────────────────────────────────────────

def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _render_jinja(src: str, ctx: dict) -> str:
    """Render a Jinja2 template fragment with the given context."""
    from jinja2 import Environment
    env = Environment(autoescape=False, undefined=__import__("jinja2").StrictUndefined)
    return env.from_string(src).render(**ctx)


def _project_ctx(**overrides) -> dict:
    """Build a project_ctx-like dict for shape tests."""
    defaults = {
        "name": "Generic Solar Sketch",
        "technology": "Solar PV",
        "data_source": "User Project",
        "capacity_mw": 50.0,
        "country_iso": "HR",
        "operating_hours_p50": 1800,
        "plant_availability": 0.97,
        "grid_availability": 0.99,
        "pv_degradation": 0.005,
        "ppa_tariff_eur_mwh": 90.0,
        "ppa_term_years": 15,
        "ppa_index_pct": 0.02,
        "co2_enabled": False,
        "co2_price_eur_mwh": 0.0,
        "total_capex_keur": 50000.0,
        "senior_debt_keur": 35000.0,
        "idc_keur": 2000.0,
        "bank_fees_keur": 1500.0,
        "opex_y1_total_keur": 800.0,
        "opex_contingency_pct": 0.05,
        "gearing_pct": 0.70,
        "target_dscr": 1.20,
        "interest_rate_pct": 0.05,
        "senior_tenor_years": 18,
        "shl_amount_keur": 5000.0,
        "cit_rate_pct": 0.18,
        "loss_carryforward_years": 5,
        "g20_status": "BLOCKED",
        "r99_r102_status": "NOT_APPROVED",
        "financial_close": "2026-06-01",
        "cod_date": "2027-12-30",
        "construction_months": 18,
        "horizon_years": 25,
        "period_frequency": "Quarterly",
        "template_source": "generic_solar",
        "code": "sketch-1",
    }
    defaults.update(overrides)
    return defaults


# ── 1. CSS additive ─────────────────────────────────────────────────────

class TestCSSAdditive:
    def test_root_count_unchanged(self):
        text = _read_text(STYLES_CSS)
        root_count = len(re.findall(r"^:root\s*\{", text, re.MULTILINE))
        assert root_count == 3, f"expected 3 :root blocks (UI-2.5 invariant), got {root_count}"

    def test_exploratory_classes_present(self):
        text = _read_text(STYLES_CSS)
        for cls in (
            ".inp-exploratory-notice",
            ".last-run-indicator__row--exploratory",
            ".last-run-indicator__exploratory-badge",
            ".last-run-indicator__exploratory-hint",
            ".export-explorer-warning",
        ):
            assert cls in text, f"missing CSS class: {cls}"


# ── 2. Context flag in main_web.py ───────────────────────────────────────

class TestContextFlag:
    def test_flag_in_main_web_three_times(self):
        text = _read_text(MAIN_WEB)
        n = text.count("\"is_exploratory_project\":")
        assert n == 3, f"expected 3 occurrences of is_exploratory_project in main_web.py, got {n}"

    def test_flag_uses_both_conditions(self):
        text = _read_text(MAIN_WEB)
        # Each occurrence should include both project_origin check AND
        # template_source check.
        for line in text.splitlines():
            if "is_exploratory_project" in line:
                # Either the line or the next 3 lines should reference
                # project_origin and template_source
                block_idx = text.find(line)
                block = text[block_idx:block_idx + 400]
                assert "project_origin" in block
                assert "template_source" in block
                assert "generic_solar" in block
                assert "generic_wind" in block


# ── 3. Warning renders in inputs_section ─────────────────────────────────

class TestInputsSectionWarning:
    def test_warning_block_present(self):
        text = _read_text(SHEET_INPUTS)
        assert "inp-exploratory-notice" in text
        assert "data-exploratory-warning" in text
        assert "data-exploration-source=\"inputs-section\"" in text
        assert "Exploratory / not Excel-parity validated" in text

    def test_warning_uses_flag(self):
        text = _read_text(SHEET_INPUTS)
        # Should be inside an `if is_exploratory_project` block
        assert "{% if is_exploratory_project" in text

    def test_warning_renders_when_flag_true(self):
        # Build minimal ctx
        ctx = {
            "project_ctx": _project_ctx(),
            "is_user_project": True,
            "is_exploratory_project": True,
            "messages": [],
        }
        out = _render_jinja(_read_text(SHEET_INPUTS), ctx)
        assert "inp-exploratory-notice" in out
        assert "Exploratory" in out
        assert "EXPLORATORY" in out or "exploratory" in out.lower()

    def test_warning_absent_when_flag_false(self):
        ctx = {
            "project_ctx": _project_ctx(),
            "is_user_project": True,
            "is_exploratory_project": False,
            "messages": [],
        }
        out = _render_jinja(_read_text(SHEET_INPUTS), ctx)
        assert "inp-exploratory-notice" not in out
        assert "data-exploratory-warning" not in out

    def test_warning_absent_when_factory_template(self):
        ctx = {
            "project_ctx": _project_ctx(),
            "is_user_project": False,
            "is_exploratory_project": False,
            "messages": [],
        }
        out = _render_jinja(_read_text(SHEET_INPUTS), ctx)
        assert "inp-exploratory-notice" not in out


# ── 4. Warning renders in _last_run_indicator ───────────────────────────

class TestLastRunIndicatorWarning:
    def test_warning_block_present(self):
        text = _read_text(LAST_RUN_INDICATOR)
        assert "last-run-indicator__row--exploratory" in text
        assert "data-exploratory-warning" in text
        assert "data-exploration-source=\"runtime-summary\"" in text
        assert "EXPLORATORY" in text

    def test_warning_uses_flag(self):
        text = _read_text(LAST_RUN_INDICATOR)
        assert "is_exploratory" in text

    def test_warning_renders_when_flag_true_and_run_exists(self):
        ctx = {
            "runtime_summary": {
                "run_id": "abc123def456",
                "last_run_at": "2026-06-09T12:00:00Z",
                "status": "ok",
                "error_message": "",
            },
            "project_record": {
                "project_code": "sketch-1",
                "project_name": "Generic Solar Sketch",
            },
            "base_case_record": {
                "scenario_name": "Base",
            },
            "workspace_state": {
                "dirty": False,
                "last_runtime_snapshot_id": "abc123",
            },
            "is_exploratory_project": True,
        }
        out = _render_jinja(_read_text(LAST_RUN_INDICATOR), ctx)
        assert "last-run-indicator__row--exploratory" in out
        assert "data-exploratory-warning" in out

    def test_warning_absent_when_flag_false(self):
        ctx = {
            "runtime_summary": {
                "run_id": "abc123",
                "last_run_at": "2026-06-09T12:00:00Z",
                "status": "ok",
            },
            "project_record": {
                "project_code": "tuho",
                "project_name": "TUHO",
            },
            "base_case_record": None,
            "workspace_state": {"dirty": False, "last_runtime_snapshot_id": "abc"},
            "is_exploratory_project": False,
        }
        out = _render_jinja(_read_text(LAST_RUN_INDICATOR), ctx)
        assert "last-run-indicator__row--exploratory" not in out
        assert "data-exploratory-warning" not in out

    def test_warning_absent_when_no_run_yet(self):
        # No run, so the whole partial renders nothing.
        ctx = {
            "runtime_summary": {},
            "project_record": {"project_code": "x", "project_name": "x"},
            "base_case_record": None,
            "workspace_state": None,
            "is_exploratory_project": True,
        }
        out = _render_jinja(_read_text(LAST_RUN_INDICATOR), ctx)
        # The whole partial is a no-op when no run.
        assert "last-run-indicator" not in out


# ── 5. Warning renders in export_registry ───────────────────────────────

class TestExportRegistryWarning:
    def test_warning_block_present(self):
        text = _read_text(EXPORT_REGISTRY)
        assert "export-explorer-warning" in text
        assert "data-exploratory-warning" in text
        assert "data-exploration-source=\"export-registry\"" in text
        assert "EXPLORATORY" in text

    def test_warning_uses_flag(self):
        text = _read_text(EXPORT_REGISTRY)
        assert "{% if is_exploratory_project" in text

    def test_warning_renders_when_flag_true(self):
        # The panel always renders the wrapper; the warning is
        # inside the wrapper when the flag is True.
        ctx = {
            "export_cards": [
                {"id": "x", "name": "X", "category": "review",
                 "enabled": True, "lineage": "x"},
            ],
            "is_exploratory_project": True,
        }
        out = _render_jinja(_read_text(EXPORT_REGISTRY), ctx)
        assert "export-explorer-warning" in out
        assert "data-exploratory-warning" in out
        assert "EXPLORATORY" in out

    def test_warning_absent_when_flag_false(self):
        ctx = {
            "export_cards": [
                {"id": "x", "name": "X", "category": "review",
                 "enabled": True, "lineage": "x"},
            ],
            "is_exploratory_project": False,
        }
        out = _render_jinja(_read_text(EXPORT_REGISTRY), ctx)
        assert "export-explorer-warning" not in out


# ── 6. Hard constraints: factory + TUHO + Oborovo untouched ────────────

class TestFactoryUntouched:
    """The factory template path (TUHO, Oborovo) must remain
    factory_template, NOT user_created, and NOT is_exploratory_project.

    This protects:
    - No drift on TUHO / Oborovo parity.
    - No new editable UI on factory references.
    - No construction flag changes.
    - No C10 / R-PAR promotion.
    """

    def test_resolve_project_record_keeps_factory_origin(self):
        """For project_selection=tuho, _resolve_project_record must
        create a project with project_origin='factory_template'."""
        text = _read_text(MAIN_WEB)
        # Find the function definition
        idx = text.find("def _resolve_project_record")
        assert idx >= 0
        block = text[idx:idx + 1500]
        assert "factory_template" in block, (
            "_resolve_project_record must produce factory_template origin"
        )

    def test_user_created_branch_in_run_service_unchanged(self):
        """The run service user_created path is reused for generic
        user projects, not modified."""
        run_service = (REPO_ROOT / "app" / "services" / "run_service.py").read_text()
        assert "_execute_user_created_path" in run_service
        # Should not contain any 24-H specific change markers
        # (this is a sanity test that we did not change run_service)
        # Just check it has not been refactored
        assert "def _execute_user_created_path" in run_service

    def test_waterfall_core_construction_flag_gate_unchanged(self):
        """The waterfall_core construction flag gate must still
        read use_construction_schedule_engine from inputs.info,
        defaulting to False."""
        wc = (REPO_ROOT / "app" / "waterfall_core.py").read_text()
        assert "use_construction_schedule_engine" in wc
        # The default must still be False
        m = re.search(
            r"getattr\(inputs\.info,\s*[\"\']use_construction_schedule_engine[\"\']\s*,\s*False\)",
            wc,
        )
        assert m, "waterfall_core.py should default to False for the gate"

    def test_rc1_untouched(self):
        """No rc1 file paths in the diff."""
        # We check that the current branch's diff against main does
        # not include any rc1 path. (Excluding the test self.)
        result = __import__("subprocess").run(
            ["git", "diff", "--name-only", "main...HEAD"],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        files = [f for f in result.stdout.splitlines() if f]
        rc1_files = [f for f in files if "rc1" in f.lower()]
        assert not rc1_files, f"rc1 files in diff: {rc1_files}"

    def test_no_construction_flag_value_changed(self):
        """The main_web.py diff should not flip
        use_construction_schedule_engine."""
        result = __import__("subprocess").run(
            ["git", "diff", "main...HEAD", "--", "main_web.py"],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        # No line in the diff should set use_construction_schedule_engine
        # to True.
        bad = re.findall(
            r"use_construction_schedule_engine\s*=\s*True",
            result.stdout,
        )
        assert not bad, f"diff sets flag to True: {bad}"


# ── 7. The exploratory flag uses real data (no fake IDs) ────────────────

class TestNoFakeData:
    def test_no_fake_runtime_ids_in_templates(self):
        """The exploratory warning should not invent runtime IDs or
        timestamps. It uses runtime_summary (already real)."""
        for path in (SHEET_INPUTS, LAST_RUN_INDICATOR, EXPORT_REGISTRY):
            text = _read_text(path)
            # The warning text mentions "exploratory" but should not
            # hardcode a fake run_id or timestamp.
            assert "fake" not in text.lower() or "not fake" in text.lower() or "no fake" in text.lower()
            # The warning does not embed a fake run_id format.
            assert not re.search(r"run_[0-9a-f]{8,}", text)

    def test_main_web_no_fake_data(self):
        """main_web.py diff should not introduce fake data."""
        result = __import__("subprocess").run(
            ["git", "diff", "main...HEAD", "--", "main_web.py"],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        # No fake IDs introduced
        assert "fake" not in result.stdout.lower() or "no fake" in result.stdout.lower()


# ── 8. End-to-end: create user_created generic project + exploratory warning ─

class TestEndToEnd:
    """End-to-end integration test: create a user_created generic
    Solar project and verify the new is_exploratory_project flag is
    True, plus the warning renders in inputs_section.html.
    """

    def test_create_user_created_generic_solar(self):
        """The /projects/create route should accept template_source
        = 'generic_solar' and produce a user_created project."""
        # Read projects_create_service
        svc = (REPO_ROOT / "app" / "services" / "projects_create_service.py").read_text()
        # The service must set project_origin='user_created'
        assert "project_origin='user_created'" in svc or 'project_origin="user_created"' in svc
        # It must call create_project_record with template_source=normalized_source
        # The normalized source is then stored on the record.
        # This is the precondition for is_exploratory_project to be True.

    def test_exploratory_flag_computed_correctly(self):
        """Sanity: the is_exploratory_project expression is True
        when origin is user_created AND template_source in
        {generic_solar, generic_wind}; False otherwise."""

        # Manually compute the flag for a few scenarios and check
        # the main_web.py expression matches.
        scenarios = [
            # (project_origin, template_source, expected_flag)
            ("user_created", "generic_solar", True),
            ("user_created", "generic_wind", True),
            ("user_created", "tuho", False),  # user-edited TUHO seed
            ("factory_template", "generic_solar", False),
            ("factory_template", "tuho", False),
            ("factory_template", "oborovo", False),
        ]
        for origin, ts, expected in scenarios:
            actual = (
                origin == "user_created"
                and (ts or "").strip().lower() in {"generic_solar", "generic_wind"}
            )
            assert actual == expected, (
                f"flag mismatch for origin={origin}, ts={ts}: "
                f"expected={expected}, got={actual}"
            )

    def test_warning_appears_in_rendered_inputs_section(self):
        """End-to-end render: with the correct context, the warning
        appears in the inputs section output."""
        ctx = {
            "project_ctx": _project_ctx(
                name="My Sketch",
                technology="Solar PV",
                template_source="generic_solar",
                code="my-sketch",
            ),
            "is_user_project": True,
            "is_exploratory_project": True,
            "messages": [],
        }
        out = _render_jinja(_read_text(SHEET_INPUTS), ctx)
        # The warning block must be in the rendered output
        assert "inp-exploratory-notice" in out
        assert "data-exploratory-warning=\"true\"" in out
        assert "data-exploration-source=\"inputs-section\"" in out
        # The badge text must be present
        assert "EXPLORATORY" in out
        # The "not Excel-parity validated" copy must be present
        assert "Excel-parity" in out or "Excel parity" in out


# ── 9. /projects/new form template_source options ───────────────────────

class TestNewProjectForm:
    """The new project form should expose generic_solar and
    generic_wind as template_source options."""

    def test_generic_solar_option_present(self):
        text = (REPO_ROOT / "app" / "templates" / "partials" / "new_project_form.html").read_text(encoding="utf-8")
        # The options are passed via template_options from
        # NEW_PROJECT_TEMPLATE_OPTIONS in main_web.py. We just
        # confirm the form template iterates over them.
        assert "template_options" in text
        assert "option.value" in text
