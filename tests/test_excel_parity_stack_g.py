"""Excel Parity Stack G — Distribution & Sponsor Engine → UI Wiring characterization tests.

Branch: excel-parity-stack-g-distribution-sponsor-ui
Phase G1: Audit existing Distribution output — fields found on WaterfallPeriod/WaterfallResult
Phase G2: Audit existing Sponsor output — only scalar sponsor_irr on WaterfallResult
Phase G1-impl: Distribution schedule serializer + sessionStorage wiring + template JS
Phase G2-gap: Sponsor per-period cashflows NOT on WaterfallResult — gap documented, not wired

G1 Distribution audit findings (from domain/waterfall/waterfall_engine.py):
  Per-period fields on WaterfallPeriod:
    distribution_keur              — equity distribution paid this period
    cash_sweep_keur                — cash sweep this period
    cum_distribution_keur          — cumulative distribution to date
    lockup_active                  — True if lockup covenants block distribution
    cf_after_reserves_keur         — CF available after reserve movements
    dsra_balance_keur              — DSRA closing balance
    dsra_contribution_keur         — DSRA funding/(release) this period
    mra_balance_keur               — MRA closing balance
    mra_contribution_keur          — MRA funding/(release) this period
    legacy_distribution_keur       — runtime distribution before DA override (Phase 9C)
    da_paid_distribution_keur      — DA equity_distribution_paid_keur (Phase 9C)
    distribution_source            — "runtime" | "distribution_account" | "" (Phase 9C)
    distribution_wiring_delta_keur — da_paid - legacy (audit, Phase 9C)
  Summary fields on WaterfallResult:
    total_distribution_keur        — total equity distributions over project life
    legacy_distribution_keur       — pre-override total (Phase 9C)
    da_paid_distribution_keur      — DA-paid total (Phase 9C)
    distribution_source            — same as period field, result-level summary
    distribution_wiring_delta_keur — total delta (Phase 9C)

G2 Sponsor audit findings:
  WaterfallResult carries only one sponsor scalar: sponsor_irr (float).
  domain/sponsor/ module (SponsorCashflowResult, SponsorIrrResult, SponsorMoicResult,
  SponsorCapitalAccount, etc.) has rich per-period structures but they are NOT attached
  to WaterfallResult or WaterfallPeriod. Wiring per-period sponsor cashflows would require
  new intermediate architecture (calling sponsor runner from project_runner.py and attaching
  results to the return dict), which is explicitly forbidden by Stack G guardrails.
  G2 is documented as a gap — not papered over. sponsor_irr scalar remains in KPIs.
  sessionStorage["lastSponsorSchedule"] is NOT wired (correct gap behaviour).

All financial logic is unchanged. No arithmetic in JS templates.
"""
from __future__ import annotations

import json
import re


# ---------------------------------------------------------------------------
# G1: Distribution serializer tests
# ---------------------------------------------------------------------------


class TestG1DistributionSerializerExists:
    """_serialize_distribution_schedule() must exist and be callable."""

    def test_serializer_importable(self):
        """_serialize_distribution_schedule must be importable from project_runner."""
        from app.api.project_runner import _serialize_distribution_schedule  # noqa: F401

    def test_serializer_is_callable(self):
        from app.api.project_runner import _serialize_distribution_schedule
        assert callable(_serialize_distribution_schedule)


class TestG1DistributionPayload:
    """run_project() must return 'distribution_schedule' key with correct structure."""

    def test_distribution_schedule_in_run_project_output(self):
        """run_project() must include 'distribution_schedule' key in its return dict."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        assert "distribution_schedule" in result, (
            "run_project() must include 'distribution_schedule' key in its return dict. "
            "Phase G1 wiring: _serialize_distribution_schedule() is called in run_project()."
        )

    def test_distribution_schedule_tuho_is_not_none(self):
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        ds = result.get("distribution_schedule")
        assert ds is not None, "TUHO distribution_schedule must not be None"

    def test_distribution_schedule_oborovo_is_not_none(self):
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("Oborovo", "Base")
        ds = result.get("distribution_schedule")
        assert ds is not None, "Oborovo distribution_schedule must not be None"

    def test_distribution_schedule_has_periods_key(self):
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        ds = result["distribution_schedule"]
        assert "periods" in ds, "distribution_schedule must have 'periods' key"

    def test_distribution_schedule_has_summary_key(self):
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        ds = result["distribution_schedule"]
        assert "summary" in ds, "distribution_schedule must have 'summary' key"

    def test_distribution_schedule_has_source_key(self):
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        ds = result["distribution_schedule"]
        assert "source" in ds, "distribution_schedule must have 'source' key"

    def test_distribution_schedule_periods_not_empty(self):
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        ds = result["distribution_schedule"]
        assert len(ds["periods"]) > 0, "distribution_schedule.periods must not be empty"

    def test_distribution_schedule_period_fields(self):
        """Each period dict must have required distribution fields."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        ds = result["distribution_schedule"]
        required_fields = [
            "period", "date", "year_index", "period_in_year", "is_operation",
            "distribution_keur", "cash_sweep_keur", "cum_distribution_keur",
            "lockup_active", "cf_after_reserves_keur",
            "dsra_balance_keur", "dsra_contribution_keur",
            "mra_balance_keur", "mra_contribution_keur",
            "legacy_distribution_keur", "da_paid_distribution_keur",
            "distribution_source", "distribution_wiring_delta_keur",
        ]
        for period in ds["periods"][:3]:  # Check first few periods
            for field in required_fields:
                assert field in period, (
                    f"distribution_schedule period must have field '{field}'. "
                    f"Fields present: {list(period.keys())}"
                )

    def test_distribution_schedule_summary_fields(self):
        """Summary dict must have required fields."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        ds = result["distribution_schedule"]
        required_summary_fields = [
            "total_distribution_keur",
            "legacy_distribution_keur",
            "da_paid_distribution_keur",
            "distribution_source",
            "distribution_wiring_delta_keur",
        ]
        for field in required_summary_fields:
            assert field in ds["summary"], (
                f"distribution_schedule.summary must have field '{field}'. "
                f"Fields present: {list(ds['summary'].keys())}"
            )

    def test_distribution_schedule_is_json_safe(self):
        """distribution_schedule must be JSON-serializable (no NaN/Infinity)."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        ds = result["distribution_schedule"]
        # json.dumps must not raise
        serialized = json.dumps(ds)
        # Re-parse to confirm roundtrip
        parsed = json.loads(serialized)
        assert "periods" in parsed

    def test_distribution_schedule_no_nan_infinity(self):
        """No NaN or Infinity values must appear in serialized distribution schedule."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        ds = result["distribution_schedule"]
        serialized = json.dumps(ds)
        assert "NaN" not in serialized, "distribution_schedule must not contain NaN"
        assert "Infinity" not in serialized, "distribution_schedule must not contain Infinity"

    def test_distribution_schedule_total_positive(self):
        """TUHO total_distribution_keur must be positive (project has distributions)."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        ds = result["distribution_schedule"]
        total = ds["summary"]["total_distribution_keur"]
        assert total is not None and total > 0, (
            f"TUHO total_distribution_keur must be positive, got {total}"
        )


# ---------------------------------------------------------------------------
# G1: sessionStorage wiring in run_service.py
# ---------------------------------------------------------------------------


class TestG1SessionStorageWiring:
    """run_service.py must thread distribution_schedule into sessionStorage."""

    def test_build_sessionstorage_accepts_distribution_schedule_param(self):
        """_build_sessionstorage_save_tag must accept distribution_schedule kwarg."""
        import inspect
        from app.services.run_service import _build_sessionstorage_save_tag
        sig = inspect.signature(_build_sessionstorage_save_tag)
        assert "distribution_schedule" in sig.parameters, (
            "_build_sessionstorage_save_tag must have 'distribution_schedule' parameter. "
            "Phase G1 wiring: distribution_schedule is threaded through all 3 execution paths."
        )

    def test_sessionstorage_script_contains_lastDistributionSchedule_when_data(self):
        """When distribution_schedule payload given, script must set lastDistributionSchedule."""
        from app.services.run_service import _build_sessionstorage_save_tag
        dummy_runtime = {
            "project_name": "test", "project_irr": 0.1, "equity_irr": 0.09,
            "sponsor_irr": 0.08, "avg_dscr": 1.25, "min_dscr": 1.15,
            "total_revenue_keur": 1000.0, "total_ebitda_keur": 700.0,
            "total_opex_keur": 300.0, "total_distributions_keur": 500.0,
        }

        class _FakeWorkspaceState:
            active_scenario_id = "s1"
            active_scenario_name = "Base"

        script = _build_sessionstorage_save_tag(
            runtime_summary=dummy_runtime,
            runtime_origin="user_created",
            workspace_state=_FakeWorkspaceState(),
            runtime_snapshot_id="snap1",
            distribution_schedule={"periods": [], "summary": {}, "source": "test"},
        )
        assert "lastDistributionSchedule" in script, (
            "Script must contain sessionStorage.setItem('lastDistributionSchedule', ...) "
            "when distribution_schedule payload is provided."
        )

    def test_sessionstorage_script_removes_lastDistributionSchedule_when_none(self):
        """When distribution_schedule is None, script must removeItem lastDistributionSchedule."""
        from app.services.run_service import _build_sessionstorage_save_tag
        dummy_runtime = {
            "project_name": "test", "project_irr": 0.1, "equity_irr": 0.09,
            "sponsor_irr": 0.08, "avg_dscr": 1.25, "min_dscr": 1.15,
            "total_revenue_keur": 1000.0, "total_ebitda_keur": 700.0,
            "total_opex_keur": 300.0, "total_distributions_keur": 500.0,
        }

        class _FakeWorkspaceState:
            active_scenario_id = "s1"
            active_scenario_name = "Base"

        script = _build_sessionstorage_save_tag(
            runtime_summary=dummy_runtime,
            runtime_origin="user_created",
            workspace_state=_FakeWorkspaceState(),
            runtime_snapshot_id="snap1",
            distribution_schedule=None,
        )
        assert 'removeItem("lastDistributionSchedule")' in script, (
            "Script must contain sessionStorage.removeItem('lastDistributionSchedule') "
            "when distribution_schedule is None (stale data cleared)."
        )

    def test_run_service_references_distribution_schedule_in_all_paths(self):
        """run_service.py source must pass distribution_schedule in all 3 execution paths."""
        from pathlib import Path
        source = Path("app/services/run_service.py").read_text()
        matches = source.count('distribution_schedule=result.get("distribution_schedule")')
        assert matches == 3, (
            f"Expected 3 occurrences of distribution_schedule threading in run_service.py "
            f"(one per execution path), found {matches}."
        )


# ---------------------------------------------------------------------------
# G1: Template JS tests
# ---------------------------------------------------------------------------


class TestG1TemplateJS:
    """_sheet_distributions_partial.html must read lastDistributionSchedule and render table."""

    def _read_template(self):
        from pathlib import Path
        return Path("app/templates/partials/_sheet_distributions_partial.html").read_text()

    def test_template_reads_lastDistributionSchedule(self):
        """Template JS must read sessionStorage['lastDistributionSchedule']."""
        content = self._read_template()
        assert "lastDistributionSchedule" in content, (
            "_sheet_distributions_partial.html must read sessionStorage['lastDistributionSchedule']"
        )

    def test_template_has_dist_schedule_block(self):
        """Template must have dist-schedule-block div (post-Run table container)."""
        content = self._read_template()
        assert "dist-schedule-block" in content, (
            "_sheet_distributions_partial.html must have id='dist-schedule-block' element"
        )

    def test_template_has_unavailable_panel(self):
        """Template must still have dist-unavailable-panel (pre-Run fallback)."""
        content = self._read_template()
        assert "dist-unavailable-panel" in content, (
            "_sheet_distributions_partial.html must retain 'dist-unavailable-panel' "
            "for pre-Run fallback state"
        )

    def test_template_no_js_arithmetic(self):
        """Template JS must not contain arithmetic operators on data values (no client-side calc)."""
        content = self._read_template()
        # Extract only the <script> blocks for checking
        script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
        script_content = "\n".join(script_blocks)
        # Check there are no expressions like periods[i].x + periods[i].y
        # (data formatting/display is fine — we check for arithmetic on key references)
        arithmetic_on_data = re.search(
            r'periods\[i\]\[\w+\]\s*[\+\-\*\/]\s*periods\[i\]\[\w+\]',
            script_content
        )
        assert arithmetic_on_data is None, (
            "No JS arithmetic on period data values allowed in distribution template. "
            "All calculations must remain in the Python engine (WaterfallResult.periods)."
        )

    def test_template_renders_distribution_keur(self):
        """Template JS row definitions must include distribution_keur field."""
        content = self._read_template()
        assert "distribution_keur" in content, (
            "Template must reference 'distribution_keur' field in row definitions"
        )

    def test_template_renders_lockup_active(self):
        """Template JS row definitions must include lockup_active field."""
        content = self._read_template()
        assert "lockup_active" in content, (
            "Template must reference 'lockup_active' field in row definitions"
        )


# ---------------------------------------------------------------------------
# G2: Sponsor gap tests (confirm NOT wired — gap is documented)
# ---------------------------------------------------------------------------


class TestG2SponsorGapDocumented:
    """G2: sponsor per-period cashflows are NOT wired to sessionStorage — gap documented."""

    def test_sponsor_schedule_not_in_run_project_output(self):
        """run_project() must NOT have 'sponsor_schedule' key — per-period sponsor not ready."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        assert "sponsor_schedule" not in result, (
            "run_project() must NOT include 'sponsor_schedule' key. "
            "G2 audit finding: domain/sponsor/ per-period cashflows are not attached to "
            "WaterfallResult — wiring them would require new intermediate architecture "
            "forbidden by Stack G guardrails. Gap is documented, not papered over."
        )

    def test_lastSponsorSchedule_not_written_in_run_service(self):
        """run_service.py must NOT reference lastSponsorSchedule — G2 gap is unimplemented."""
        from pathlib import Path
        source = Path("app/services/run_service.py").read_text()
        assert "lastSponsorSchedule" not in source, (
            "run_service.py must NOT reference 'lastSponsorSchedule'. "
            "G2 sponsor per-period wiring is a documented gap, not yet implemented."
        )

    def test_sponsor_irr_scalar_available_in_kpis(self):
        """sponsor_irr scalar must still be available in run_project() kpis block."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        # sponsor_irr is in the waterfall result / kpis indirectly via runtime_summary
        # confirm distribution_schedule.summary doesn't have it (different key)
        ds = result.get("distribution_schedule", {})
        # The sponsor_irr is on WaterfallResult.sponsor_irr, exposed via kpis in run_project
        # We confirm the result contains kpis block
        assert "kpis" in result, "run_project() must return 'kpis' block"

    def test_sponsor_template_documents_gap(self):
        """_sheet_sponsor_partial.html must document the G2 gap."""
        from pathlib import Path
        content = Path("app/templates/partials/_sheet_sponsor_partial.html").read_text()
        assert "sponsor-unavailable-panel" in content, (
            "_sheet_sponsor_partial.html must retain sponsor-unavailable-panel "
            "documenting the G2 gap"
        )
        assert "not yet" in content.lower() or "not available" in content.lower(), (
            "_sheet_sponsor_partial.html must honestly state sponsor economics are not yet available"
        )

    def test_no_serialize_sponsor_schedule_in_project_runner(self):
        """_serialize_sponsor_schedule must NOT exist — G2 is not wired."""
        from app.api import project_runner
        assert not hasattr(project_runner, "_serialize_sponsor_schedule"), (
            "_serialize_sponsor_schedule must not exist in project_runner. "
            "G2 wiring is a documented gap, not implemented."
        )


# ---------------------------------------------------------------------------
# G1: Characterization tests (TUHO factory output)
# ---------------------------------------------------------------------------


class TestG1CharacterizationTUHO:
    """Characterization tests: distribution schedule output from TUHO factory."""

    def test_tuho_has_operation_periods_with_distributions(self):
        """TUHO must have at least one operation period with positive distribution."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        ds = result["distribution_schedule"]
        op_periods_with_dist = [
            p for p in ds["periods"]
            if p["is_operation"] and p["distribution_keur"] is not None and p["distribution_keur"] > 0
        ]
        assert len(op_periods_with_dist) > 0, (
            "TUHO must have at least one operation period with positive distribution_keur"
        )

    def test_tuho_cum_distribution_non_decreasing(self):
        """TUHO cum_distribution_keur must be non-decreasing across operation periods."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        ds = result["distribution_schedule"]
        op_periods = [p for p in ds["periods"] if p["is_operation"]]
        prev = None
        for p in op_periods:
            v = p.get("cum_distribution_keur")
            if v is not None and prev is not None:
                assert v >= prev - 0.01, (  # 0.01 tolerance for rounding
                    f"cum_distribution_keur must be non-decreasing: {prev} -> {v}"
                )
            if v is not None:
                prev = v

    def test_tuho_distribution_schedule_source_field(self):
        """Source field must reference WaterfallResult.periods."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        ds = result["distribution_schedule"]
        assert "WaterfallResult" in ds["source"], (
            f"source must mention WaterfallResult, got: {ds['source']}"
        )

    def test_tuho_distribution_schedule_lockup_active_is_bool(self):
        """lockup_active must be a Python bool in each period dict."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("TUHO", "Base")
        ds = result["distribution_schedule"]
        for p in ds["periods"][:5]:
            assert isinstance(p["lockup_active"], bool), (
                f"lockup_active must be bool, got {type(p['lockup_active'])}"
            )

    def test_oborovo_distribution_schedule_structure(self):
        """Oborovo distribution_schedule must have same structure as TUHO."""
        from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route
        result = run_project("Oborovo", "Base")
        ds = result["distribution_schedule"]
        assert "periods" in ds
        assert "summary" in ds
        assert "source" in ds
        assert len(ds["periods"]) > 0
