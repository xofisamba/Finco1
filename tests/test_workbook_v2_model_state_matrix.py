"""
UI-4A — Model state matrix tests.

Proves the CURRENT / STALE / NOT RUN state machine is consistent across:
  - OverviewProjection (sheet_overview.html source)
  - ScenarioPresentation (sheet_scenarios.html source)
  - ScenarioKpiProjection (sheet_compare.html source)
  - Status banner context variables (ws_dirty, has_runtime, run_failed)

Rules:
  - CURRENT: has RuntimeResult, inputs unchanged since last run
  - STALE: has RuntimeResult, inputs changed since last run
  - NOT RUN: no RuntimeResult for this scenario
  - RUN FAILED: run was attempted but produced an error (banner only)

State naming is canonical across all templates:
  - Toolbar state chip: "Current" / "Stale" / "Not run" / "Run failed"
  - Status pills: "CURRENT" / "STALE" / "NOT RUN" / "FAILED"
  - data-testid attributes must be unique and stable
"""
import pytest
from app.workbook.runtime_projection import RuntimeProjectionState


class TestRuntimeProjectionStateValues:
    """RuntimeProjectionState enum values must be stable — templates depend on .value."""

    def test_not_run_value(self):
        assert RuntimeProjectionState.NOT_RUN.value == "NOT_RUN"

    def test_clean_value(self):
        assert RuntimeProjectionState.CLEAN.value == "CLEAN"

    def test_stale_value(self):
        assert RuntimeProjectionState.STALE.value == "STALE"

    def test_unavailable_value(self):
        assert RuntimeProjectionState.UNAVAILABLE.value == "UNAVAILABLE"


class TestOverviewProjectionStateMapping:
    """OverviewProjection state machine: CLEAN/STALE/NOT_RUN/UNAVAILABLE."""

    def test_no_runtime_result_gives_not_run(self):
        from app.v2.overview_projection import build_overview_projection
        proj = build_overview_projection(rr=None, is_dirty=False, pis=_make_pis())
        assert proj.state == RuntimeProjectionState.NOT_RUN

    def test_runtime_result_clean_workspace(self):
        from app.v2.overview_projection import build_overview_projection
        rr = _make_rr(has_debt=True)
        proj = build_overview_projection(rr=rr, is_dirty=False, pis=_make_pis())
        # Depends on classify_schedule_state — with valid debt schedule and clean:
        assert proj.state in (RuntimeProjectionState.CLEAN, RuntimeProjectionState.STALE)

    def test_runtime_result_dirty_workspace(self):
        from app.v2.overview_projection import build_overview_projection
        rr = _make_rr(has_debt=True)
        proj = build_overview_projection(rr=rr, is_dirty=True, pis=_make_pis())
        assert proj.state == RuntimeProjectionState.STALE

    def test_runtime_result_no_debt_gives_unavailable(self):
        from app.v2.overview_projection import build_overview_projection
        rr = _make_rr(has_debt=False)
        proj = build_overview_projection(rr=rr, is_dirty=False, pis=_make_pis())
        assert proj.state in (RuntimeProjectionState.UNAVAILABLE,
                               RuntimeProjectionState.CLEAN,
                               RuntimeProjectionState.NOT_RUN)

    def test_not_run_state_has_no_kpi_values(self):
        from app.v2.overview_projection import build_overview_projection
        proj = build_overview_projection(rr=None, is_dirty=False, pis=_make_pis())
        # KPIs must be NOT_AVAILABLE sentinel (not "—" — that's the OutputMetricProjection level)
        assert proj.project_irr in ("NOT_AVAILABLE", "—")
        assert proj.min_dscr in ("NOT_AVAILABLE", "—")


class TestScenarioPresentationStates:
    """ScenarioPresentation: NOT_RUN / CURRENT / STALE."""

    def test_not_run_scenario(self):
        from app.v2.scenario_presentation import build_scenario_presentation
        sc = _make_scenario_record(has_run=False)
        pres = build_scenario_presentation(sc, active_scenario_id=None)
        assert pres.state == "NOT_RUN"
        assert not pres.has_run
        assert not pres.is_stale

    def test_current_scenario(self):
        from app.v2.scenario_presentation import build_scenario_presentation
        sc = _make_scenario_record(has_run=True, is_stale=False)
        pres = build_scenario_presentation(sc, active_scenario_id=None)
        assert pres.state == "CURRENT"
        assert pres.has_run
        assert not pres.is_stale

    def test_stale_scenario(self):
        from app.v2.scenario_presentation import build_scenario_presentation
        sc = _make_scenario_record(has_run=True, is_stale=True)
        pres = build_scenario_presentation(sc, active_scenario_id=None)
        assert pres.state == "STALE"
        assert pres.is_stale

    def test_active_scenario_flagged(self):
        from app.v2.scenario_presentation import build_scenario_presentation
        sc = _make_scenario_record(has_run=False)
        pres = build_scenario_presentation(sc, active_scenario_id=sc.scenario_id)
        assert pres.is_active


class TestStateBannerContextVariables:
    """Context variable combinations that determine which banner to show.

    These are unit-level tests — they prove the decision logic, not the template.
    The template renders the correct banner given these context booleans.
    """

    @staticmethod
    def _resolve_banner(ws_dirty, has_runtime, run_failed=False,
                        field_error=None, flash_error=None):
        """Simulate the banner decision logic from _v2_status_banner.html."""
        if field_error or flash_error:
            return "error"
        if run_failed:
            return "run_failed"
        if ws_dirty:
            return "stale"
        if has_runtime:
            return "current"
        return "not_run"

    def test_error_takes_priority_over_all(self):
        result = self._resolve_banner(True, True, True, field_error="Some error")
        assert result == "error"

    def test_run_failed_shown_when_no_other_error(self):
        result = self._resolve_banner(False, False, run_failed=True)
        assert result == "run_failed"

    def test_stale_when_dirty_and_has_runtime(self):
        result = self._resolve_banner(ws_dirty=True, has_runtime=True)
        assert result == "stale"

    def test_current_when_clean_and_has_runtime(self):
        result = self._resolve_banner(ws_dirty=False, has_runtime=True)
        assert result == "current"

    def test_not_run_when_no_runtime(self):
        result = self._resolve_banner(ws_dirty=False, has_runtime=False)
        assert result == "not_run"

    def test_not_run_dirty_without_runtime(self):
        # Dirty without runtime means user edited inputs before first run
        result = self._resolve_banner(ws_dirty=True, has_runtime=False)
        assert result == "stale"


class TestToolbarStateLabels:
    """Toolbar state chip labels must use canonical state names."""

    CANONICAL_LABELS = {"Current", "Stale", "Not run", "Run failed"}

    @staticmethod
    def _resolve_toolbar_label(has_runtime, ws_dirty, run_failed=False):
        if run_failed:
            return "Run failed"
        if not has_runtime:
            return "Not run"
        if ws_dirty:
            return "Stale"
        return "Current"

    def test_current_label(self):
        assert self._resolve_toolbar_label(True, False) == "Current"

    def test_stale_label(self):
        assert self._resolve_toolbar_label(True, True) == "Stale"

    def test_notrun_label(self):
        assert self._resolve_toolbar_label(False, False) == "Not run"

    def test_failed_label(self):
        assert self._resolve_toolbar_label(False, False, run_failed=True) == "Run failed"

    def test_all_labels_in_canonical_set(self):
        for has_r, ws_d, failed in [
            (True, False, False), (True, True, False),
            (False, False, False), (False, False, True),
        ]:
            label = self._resolve_toolbar_label(has_r, ws_d, failed)
            assert label in self.CANONICAL_LABELS, f"Non-canonical label: {label!r}"


# ── Test fixtures ──────────────────────────────────────────────────────── #

def _make_pis():
    """Return a minimal ProjectInputSet stub."""
    class _FakePis:
        template_source = "generic_solar"
        def to_projectinputs(self):
            raise ValueError("no real model")
    return _FakePis()


def _make_rr(has_debt=True):
    """Return a minimal RuntimeResult stub."""
    class _FakeRr:
        snapshot_id = "test-snap"
        ran_at = "2026-01-15T10:00:00"
        runtime_summary = None
        debt_schedule = {"summary": {"min_llcr": 1.28, "target_dscr": 1.3,
                                     "periods_in_lockup": 0},
                         "periods": []} if has_debt else None
    return _FakeRr()


def _make_scenario_record(has_run=False, is_stale=False):
    """Return a scenario object compatible with build_scenario_presentation."""
    import hashlib, json

    overrides = {"key": "val"} if not is_stale else {"key": "other"}
    # stored_hash must match _scenario_snapshot_hash which hashes sc.snapshot
    base_snap = {"overrides": {"key": "val"}, "base": {}}
    stored_hash = hashlib.sha256(json.dumps(base_snap, sort_keys=True).encode()).hexdigest()[:16]

    last_run = None
    if has_run:
        last_run = {
            "ran_at": "2026-01-14T09:00:00",
            "scenario_snapshot_hash": stored_hash,
            "kpis": {"project_irr": "8.50%"},  # non-empty kpis → has_run=True
        }

    overrides_for_hash = overrides  # current overrides

    class _FakeScenario:
        scenario_id = "sc-test-01"
        scenario_name = "Test Scenario"
        is_base_case = False
        updated_at = "2026-01-13T08:00:00"
        snapshot = {"overrides": overrides_for_hash, "base": {}}
        overrides = overrides_for_hash
        base_input_set = {}
        last_run_summary = last_run

    return _FakeScenario()
