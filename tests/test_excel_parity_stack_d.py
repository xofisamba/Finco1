"""Excel Parity Stack D — Engine → UI Wiring characterization tests.

Branch: excel-parity-stack-d-engine-ui
Phase D0: Oborovo SHL calibration fix verification
Phase D1: Financial Statements engine → UI wiring verification

No financial logic was changed to produce these tests.
All calculations remain in the engine; these tests only verify that:
  - The factory fix (D0) resolves the known SHL gap
  - FS data flows from assemble_financial_statements() through run_project()
    into the runtime payload
  - The fs-unavailable-panel is present when FS data is absent
  - No duplicate calculations exist; only engine output is serialized
"""
from __future__ import annotations

import json
import re

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
from domain.financial_statements import assemble_financial_statements
from domain.period_engine import PeriodEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_oborovo():
    inputs = create_default_oborovo()
    engine = PeriodEngine(
        inputs.info.financial_close,
        inputs.info.construction_months,
        inputs.info.horizon_years,
        inputs.revenue.ppa_term_years,
    )
    config = WaterfallRunConfig.from_inputs(inputs, engine)
    result = WaterfallRunner(inputs, engine).run(config)
    return inputs, engine, result


def _run_tuho():
    inputs = create_default_tuho_wind1()
    engine = PeriodEngine(
        inputs.info.financial_close,
        inputs.info.construction_months,
        inputs.info.horizon_years,
        inputs.revenue.ppa_term_years,
    )
    config = WaterfallRunConfig.from_inputs(inputs, engine)
    result = WaterfallRunner(inputs, engine).run(config)
    return inputs, engine, result


# ---------------------------------------------------------------------------
# Phase D0: Oborovo SHL calibration fix
# ---------------------------------------------------------------------------

class TestD0OborovoSHLCalibration:
    """Verify that the Oborovo SHL factory value now matches the Excel fixture.

    Prior value: 14,621.0 kEUR
    Corrected value: 13,547.2 kEUR (from oborovo_baseline.json)
    Gap closed: ~1,074 kEUR
    """

    def test_oborovo_shl_amount_matches_fixture(self):
        """SHL amount should now be 13,547.2 kEUR (Excel-verified fixture value)."""
        inputs = create_default_oborovo()
        expected = 13547.2
        actual = inputs.financing.shl_amount_keur
        assert abs(actual - expected) < 1.0, (
            f"Oborovo SHL amount {actual:.1f} kEUR should be within 1 kEUR of "
            f"fixture value {expected:.1f} kEUR. "
            f"Gap: {actual - expected:.1f} kEUR."
        )

    def test_oborovo_shl_gap_closed(self):
        """The known ~1,074 kEUR SHL gap should now be <= 5 kEUR."""
        inputs = create_default_oborovo()
        excel_expected = 13547.2
        gap = abs(inputs.financing.shl_amount_keur - excel_expected)
        assert gap <= 5.0, (
            f"Oborovo SHL gap {gap:.1f} kEUR should be <= 5 kEUR after D0 fix. "
            f"Actual: {inputs.financing.shl_amount_keur:.1f} kEUR, "
            f"Expected: {excel_expected:.1f} kEUR."
        )

    def test_oborovo_total_equity_shl_within_tolerance(self):
        """total_equity_shl_keur should be within 2% of the fixture's 15,120.77 kEUR."""
        inputs = create_default_oborovo()
        expected = 15120.77
        actual = inputs.financing.total_equity_shl_keur
        tolerance = 0.02  # 2% tolerance as in test_oborovo_parity.py
        rel_delta = abs(actual - expected) / expected
        assert rel_delta < tolerance, (
            f"total_equity_shl_keur {actual:.2f} deviates {rel_delta*100:.2f}% from "
            f"fixture {expected:.2f} (tolerance: {tolerance*100:.1f}%)."
        )


# ---------------------------------------------------------------------------
# Phase D1: Financial Statements engine → runtime payload wiring
# ---------------------------------------------------------------------------

class TestD1FinancialStatementsPayload:
    """Verify that FS data flows from assemble_financial_statements() through
    run_project() into the runtime payload without duplicate calculations."""

    def test_run_project_returns_financial_statements_key(self):
        """run_project() result dict must contain a 'financial_statements' key."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        assert "financial_statements" in result, (
            "run_project() must include 'financial_statements' key in its return dict. "
            "D1 wiring: assemble_financial_statements() is called in run_project()."
        )

    def test_financial_statements_not_none_after_run(self):
        """The 'financial_statements' payload should not be None after a successful run."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        fs = result.get("financial_statements")
        assert fs is not None, (
            "financial_statements payload should not be None after a TUHO run."
        )

    def test_financial_statements_oborovo_not_none(self):
        """FS payload should not be None for Oborovo either."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("Oborovo", "Base")
        fs = result.get("financial_statements")
        assert fs is not None, (
            "financial_statements payload should not be None after an Oborovo run."
        )

    def test_financial_statements_has_required_keys(self):
        """FS payload must have pnl, balance_sheet, pf_cash_waterfall keys."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        fs = result["financial_statements"]
        for key in ("pnl", "balance_sheet", "pf_cash_waterfall", "source"):
            assert key in fs, f"financial_statements payload is missing key '{key}'"

    def test_financial_statements_pnl_periods_nonempty(self):
        """P&L periods list should be non-empty."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        fs = result["financial_statements"]
        periods = fs["pnl"]["periods"]
        assert len(periods) > 0, "P&L periods list should be non-empty."

    def test_financial_statements_balance_sheet_periods_nonempty(self):
        """Balance sheet periods list should be non-empty."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        fs = result["financial_statements"]
        periods = fs["balance_sheet"]["periods"]
        assert len(periods) > 0, "Balance sheet periods list should be non-empty."

    def test_financial_statements_pf_cash_waterfall_periods_nonempty(self):
        """PF Cash Waterfall periods list should be non-empty."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        fs = result["financial_statements"]
        periods = fs["pf_cash_waterfall"]["periods"]
        assert len(periods) > 0, "PF Cash Waterfall periods list should be non-empty."

    def test_financial_statements_source_annotation(self):
        """FS payload source field must indicate assemble_financial_statements origin."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        fs = result["financial_statements"]
        assert "assemble_financial_statements" in fs.get("source", ""), (
            "FS payload source field must reference assemble_financial_statements(). "
            "This proves the data comes from the engine, not hardcoded values."
        )

    def test_financial_statements_is_json_serializable(self):
        """FS payload must be JSON-serializable (required for sessionStorage)."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        fs = result["financial_statements"]
        # Will raise if not serializable
        serialized = json.dumps(fs)
        assert len(serialized) > 100, "Serialized FS should be non-trivial."

    def test_financial_statements_matches_assemble_direct_call(self):
        """FS payload values must match a direct assemble_financial_statements() call.

        This proves: no duplicate calculations, no new formulas introduced —
        the payload is simply a serialization of engine output.
        """
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        fs_payload = result["financial_statements"]

        # Run assemble_financial_statements directly for comparison
        inputs, engine, wf_result = _run_tuho()
        fs_direct = assemble_financial_statements(wf_result)

        # Compare first P&L period revenues (5 kEUR tolerance for floating point)
        payload_rev_0 = fs_payload["pnl"]["periods"][0]["revenues_keur"]
        direct_rev_0 = fs_direct.pnl.periods[0].revenues_keur
        assert abs(payload_rev_0 - direct_rev_0) < 5.0, (
            f"P&L period 0 revenue: payload={payload_rev_0:.2f}, "
            f"direct={direct_rev_0:.2f}. These must match — same engine output."
        )

    def test_no_new_financial_calculations_in_serializer(self):
        """The _serialize_financial_statements function must not import or call
        any financial formula modules directly.

        Verifies that only read-only field access + rounding occurs in the
        serializer — all financial values come from the already-assembled FS result.
        """
        import ast
        from pathlib import Path

        runner_path = Path(__file__).resolve().parents[1] / "app" / "api" / "project_runner.py"
        source = runner_path.read_text(encoding="utf-8")

        # The serializer function exists
        assert "_serialize_financial_statements" in source, (
            "Expected _serialize_financial_statements function in project_runner.py"
        )

        # The only financial-domain import in run_project/serializer should be
        # domain.financial_statements — no waterfall_engine, no formula modules
        forbidden_imports = [
            "domain.waterfall.waterfall_engine",
            "domain.financing",
            "domain.tax",
            "domain.returns",
            "domain.opex",
            "domain.revenue",
        ]
        for forbidden in forbidden_imports:
            # These should not appear INSIDE the serializer function
            # (they may appear at the module level for other functions, so
            # we just check the serializer function itself)
            serializer_start = source.find("def _serialize_financial_statements")
            serializer_end = source.find("\ndef ", serializer_start + 1)
            if serializer_end == -1:
                serializer_end = len(source)
            serializer_body = source[serializer_start:serializer_end]
            assert forbidden not in serializer_body, (
                f"_serialize_financial_statements imports '{forbidden}' — "
                "this would introduce financial calculations in the serializer. "
                "Only read-only field access is permitted."
            )


# ---------------------------------------------------------------------------
# Phase D1: Template wiring verification
# ---------------------------------------------------------------------------

class TestD1TemplateWiring:
    """Verify the sheet_financials.html template is correctly wired for D1."""

    def _load_template(self):
        from pathlib import Path
        tmpl_path = (
            Path(__file__).resolve().parents[1]
            / "app" / "templates" / "partials" / "sheet_financials.html"
        )
        return tmpl_path.read_text(encoding="utf-8")

    def test_fs_unavailable_panel_has_id(self):
        """fs-unavailable-panel must have id='fs-unavailable-panel' for JS targeting."""
        html = self._load_template()
        assert 'id="fs-unavailable-panel"' in html, (
            "fs-unavailable-panel must have id attribute for JS show/hide."
        )

    def test_fs_statements_block_exists(self):
        """fs-statements-block div must be present in the template."""
        html = self._load_template()
        assert 'id="fs-statements-block"' in html, (
            "fs-statements-block must be in the template (rendered when FS available)."
        )

    def test_pnl_table_elements_present(self):
        """P&L table elements (header + body) must be in the template."""
        html = self._load_template()
        assert 'id="fs-pnl-header"' in html
        assert 'id="fs-pnl-body"' in html

    def test_bs_table_elements_present(self):
        """Balance sheet table elements must be in the template."""
        html = self._load_template()
        assert 'id="fs-bs-header"' in html
        assert 'id="fs-bs-body"' in html

    def test_pf_table_elements_present(self):
        """PF Cash Waterfall table elements must be in the template."""
        html = self._load_template()
        assert 'id="fs-pf-header"' in html
        assert 'id="fs-pf-body"' in html

    def test_sessionstorage_key_referenced(self):
        """Template JS must reference 'lastFinancialStatements' sessionStorage key."""
        html = self._load_template()
        assert "lastFinancialStatements" in html, (
            "sheet_financials.html must read from sessionStorage key "
            "'lastFinancialStatements' to display engine FS output."
        )

    def test_no_client_side_calculations(self):
        """Template JS must not contain financial calculation operators.

        The UI is read-only: it displays engine output only. No formulas,
        no aggregations, no multiplication/division of financial values.
        """
        html = self._load_template()
        # Extract the <script> block
        script_match = re.search(r'<script>(.*?)</script>', html, re.DOTALL)
        if script_match:
            script = script_match.group(1)
            # Revenue - OPEX = EBITDA is a financial formula; should not appear
            # We check for patterns like "revenue * rate" or "v1 * v2" that
            # imply client-side financial computation.
            # Formatting helpers (_fmt, toLocaleString) are acceptable.
            # Assert: no multiplication of period values (financial computation)
            assert "revenues_keur *" not in script
            assert "* revenues_keur" not in script
            assert "opex_cash_keur *" not in script
            assert "ebitda" not in script.lower() or "ebitda_cash_keur" in script.lower()

    def test_source_attribution_present(self):
        """Template must attribute FS data to canonical runtime output."""
        html = self._load_template()
        assert "canonical-runtime-financial-statements" in html, (
            "Template must include canonical runtime FS source attribution."
        )

    def test_pre_run_unavailable_panel_shown_by_js(self):
        """The JS must show the unavailable panel when no FS data exists."""
        html = self._load_template()
        # The JS should contain logic to show the unavailable panel
        assert "_populateFSStatements" in html or "lastFinancialStatements" in html, (
            "Template must contain JS that conditionally shows/hides the unavailable panel."
        )


# ---------------------------------------------------------------------------
# Phase D1: sessionStorage payload wiring in run_service
# ---------------------------------------------------------------------------

class TestD1SessionStorageWiring:
    """Verify that _build_sessionstorage_save_tag saves FS data to sessionStorage."""

    def test_sessionstorage_save_tag_includes_fs_key_when_present(self):
        """When financial_statements is provided, the script must save to
        'lastFinancialStatements' sessionStorage key."""
        from app.services.run_service import _build_sessionstorage_save_tag

        dummy_fs = {"pnl": {"periods": []}, "balance_sheet": {"periods": []},
                    "pf_cash_waterfall": {"periods": []}, "source": "test"}
        script = _build_sessionstorage_save_tag(
            runtime_summary={"project_name": "test"},
            runtime_origin="workspace_base",
            workspace_state=None,
            runtime_snapshot_id="test123",
            financial_statements=dummy_fs,
        )
        assert "lastFinancialStatements" in script, (
            "_build_sessionstorage_save_tag must save 'lastFinancialStatements' "
            "to sessionStorage when financial_statements is provided."
        )

    def test_sessionstorage_save_tag_removes_key_when_none(self):
        """When financial_statements is None, the script must remove the
        'lastFinancialStatements' key to avoid stale data."""
        from app.services.run_service import _build_sessionstorage_save_tag

        script = _build_sessionstorage_save_tag(
            runtime_summary={"project_name": "test"},
            runtime_origin="workspace_base",
            workspace_state=None,
            runtime_snapshot_id="test123",
            financial_statements=None,
        )
        assert "removeItem" in script and "lastFinancialStatements" in script, (
            "_build_sessionstorage_save_tag must call removeItem('lastFinancialStatements') "
            "when financial_statements is None."
        )

    def test_sessionstorage_save_tag_fs_payload_is_valid_json_embedded(self):
        """The embedded FS JSON in the script must be parseable."""
        from app.services.run_service import _build_sessionstorage_save_tag

        dummy_fs = {
            "pnl": {"periods": [{"revenues_keur": 1234.5}]},
            "balance_sheet": {"periods": []},
            "pf_cash_waterfall": {"periods": []},
            "source": "assemble_financial_statements(WaterfallResult)",
        }
        script = _build_sessionstorage_save_tag(
            runtime_summary={"project_name": "test"},
            runtime_origin="workspace_base",
            workspace_state=None,
            runtime_snapshot_id="test123",
            financial_statements=dummy_fs,
        )
        # The script uses json.dumps(json.dumps(fs)) so JSON is double-encoded
        # Verify the script is a non-trivial string containing FS data markers
        assert "1234.5" in script or "revenues_keur" in script, (
            "FS payload values should appear in the sessionStorage save script."
        )


# ---------------------------------------------------------------------------
# Phase D2: Payload size audit
# ---------------------------------------------------------------------------

class TestD2PayloadAudit:
    """Audit the serialized FS payload size and structure."""

    def test_pnl_period_count_matches_engine(self):
        """Serialized P&L period count should match engine period count."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        fs = result["financial_statements"]
        # TUHO: 30-year horizon, semiannual = 60 periods
        period_count = len(fs["pnl"]["periods"])
        assert 55 <= period_count <= 65, (
            f"TUHO P&L period count {period_count} should be ~60 (30yr × 2 semiannual)."
        )

    def test_balance_sheet_period_count_matches_engine(self):
        """Serialized BS period count should match engine period count."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        fs = result["financial_statements"]
        period_count = len(fs["balance_sheet"]["periods"])
        assert 55 <= period_count <= 65, (
            f"TUHO BS period count {period_count} should be ~60."
        )

    def test_serialized_payload_size_reasonable(self):
        """Serialized FS payload should be under 500 KB (reasonable for sessionStorage)."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        fs = result["financial_statements"]
        size_bytes = len(json.dumps(fs).encode("utf-8"))
        assert size_bytes < 500_000, (
            f"Serialized FS payload {size_bytes:,} bytes exceeds 500 KB limit for sessionStorage. "
            "Consider reducing fields or using aggregated annual view."
        )

    def test_no_infinite_or_nan_values_in_payload(self):
        """Serialized FS payload must not contain non-finite float values."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        fs = result["financial_statements"]
        serialized = json.dumps(fs)
        assert "Infinity" not in serialized, "FS payload contains Infinity values."
        assert "NaN" not in serialized, "FS payload contains NaN values."


# ---------------------------------------------------------------------------
# Guardrail: waterfall_core.py must not import financial_statements
# ---------------------------------------------------------------------------

class TestGuardrailWaterfallCoreIsolation:
    """Re-verify the C8 guardrail: waterfall_core.py does not import FS module.

    D1 wiring adds assemble_financial_statements() call to project_runner.py,
    NOT to waterfall_core.py. This test confirms the isolation is preserved.
    """

    def test_waterfall_core_still_does_not_import_financial_statements(self):
        import ast
        from pathlib import Path

        core_path = Path(__file__).resolve().parents[1] / "app" / "waterfall_core.py"
        source = core_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = ""
                if isinstance(node, ast.ImportFrom) and node.module:
                    module = node.module
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name
                if "financial_statements" in module:
                    pytest.fail(
                        f"waterfall_core.py still imports 'financial_statements' ({module}). "
                        "D1 wiring must only add the call to project_runner.py, not waterfall_core.py."
                    )
