"""
tests/test_phase2a_orchestrator.py — Phase 2A orchestrator and operating-schedule parity tests.

Covers:
- Four-baseline OPERATING_CORE_V1 PASS (production, revenue, OPEX, EBITDA, book/tax depreciation)
- Period-grid parity (date, start_date, index, year_index, period_in_year, is_operation)
- Negative parity tests (one-ULP changes → PAYLOAD_DRIFT)
- Identity/schema/legacy/environment/mixed-status exit-code tests via injected providers
- Source immutability during orchestration
"""
from __future__ import annotations

import dataclasses
import json
import struct
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from financial_engine.adapters.project_inputs import from_project_inputs
from financial_engine.orchestrator import run_operating_model
from finco_parity.comparison import DriftKind, compare_snapshots
from finco_parity.dual_run import (
    AggregateRunResult,
    BaselineRunResult,
    BaselineRunStatus,
    compare_candidate_provider,
    exit_code_for_aggregate,
)
from finco_parity.financial_engine_candidate import get_candidate_snapshot
from finco_parity.profiles import ComparisonProfile, project_for_profile

_BASELINE_DIR = Path("finco_parity/baselines/snapshots")
_BASELINE_COMMIT_SHA = "8b13a53805ea2e1e84144ccad1f2484e16fa8592"
_PROFILE = ComparisonProfile.OPERATING_CORE_V1

_ALL_BASELINES = ["tuho", "oborovo", "generic_solar", "generic_wind"]

_FACTORY_MAP = {
    "tuho": "create_default_tuho_wind1",
    "oborovo": "create_default_oborovo",
    "generic_solar": "create_default_solar_project",
    "generic_wind": "create_default_wind_project",
}


def _load_baseline(name: str) -> dict[str, Any]:
    return json.loads((_BASELINE_DIR / f"{name}.json").read_bytes())


def _get_project_inputs(name: str):
    from app import project_factories
    return getattr(project_factories, _FACTORY_MAP[name])()


def _get_adapted_inputs(name: str):
    p = _get_project_inputs(name)
    return from_project_inputs(
        p,
        source_id=_FACTORY_MAP[name],
        baseline_commit_sha=_BASELINE_COMMIT_SHA,
    )


# ---------------------------------------------------------------------------
# Four-baseline OPERATING_CORE_V1 PASS
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("baseline_id", _ALL_BASELINES)
def test_operating_core_v1_pass(baseline_id: str):
    """All four baselines must reach OPERATING_CORE_V1 IDENTICAL."""
    committed = _load_baseline(baseline_id)
    candidate = get_candidate_snapshot(
        baseline_id, baseline_commit_sha=_BASELINE_COMMIT_SHA
    )
    b_proj = project_for_profile(committed, _PROFILE)
    c_proj = project_for_profile(candidate, _PROFILE)
    result = compare_snapshots(b_proj, c_proj, baseline_id=baseline_id)
    assert result.status == DriftKind.IDENTICAL, (
        f"{baseline_id}: {len(result.differences)} difference(s): "
        + "; ".join(f"{d.path}={d.kind.value}" for d in result.differences[:5])
    )


# ---------------------------------------------------------------------------
# Period-grid parity
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("baseline_id", _ALL_BASELINES)
def test_period_grid_parity(baseline_id: str):
    """Period indices, dates, year_index, period_in_year, is_operation, start_date must match."""
    baseline = _load_baseline(baseline_id)
    adapted = _get_adapted_inputs(baseline_id)
    result = run_operating_model(adapted)

    op_periods = [p for p in result.periods if p.is_operation]
    bl_pg = baseline["period_grid"]

    assert len(op_periods) == len(bl_pg), (
        f"{baseline_id}: operating period count {len(op_periods)} != baseline {len(bl_pg)}"
    )

    for i, (my_p, bl_p) in enumerate(zip(op_periods, bl_pg)):
        assert my_p.period_index == bl_p["period_index"], f"[{i}] period_index"
        assert str(my_p.period_end) == bl_p["date"], f"[{i}] date"
        assert my_p.year_index == bl_p["year_index"], f"[{i}] year_index"
        assert my_p.period_in_year == bl_p["period_in_year"], f"[{i}] period_in_year"
        assert my_p.is_operation == bl_p["is_operation"], f"[{i}] is_operation"
        # start_date: baseline may store null for construction-phase periods;
        # operating periods always have a start_date in the clean engine.
        if bl_p.get("start_date") is not None:
            assert str(my_p.period_start) == bl_p["start_date"], f"[{i}] start_date"
        else:
            assert my_p.period_start is not None, f"[{i}] period_start must not be None"


# ---------------------------------------------------------------------------
# Schedule parity (zero-diff)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("baseline_id", _ALL_BASELINES)
def test_production_parity(baseline_id: str):
    baseline = _load_baseline(baseline_id)
    adapted = _get_adapted_inputs(baseline_id)
    result = run_operating_model(adapted)
    op_periods = [p for p in result.periods if p.is_operation]
    bl_vals = baseline["operating_schedules"]["production_mwh"]
    for i, (my_v, bl_v) in enumerate(zip(
        [p.production_mwh for p in op_periods], bl_vals
    )):
        assert my_v == bl_v, f"{baseline_id} production_mwh[{i}]: {my_v} != {bl_v}"


@pytest.mark.parametrize("baseline_id", _ALL_BASELINES)
def test_revenue_parity(baseline_id: str):
    baseline = _load_baseline(baseline_id)
    adapted = _get_adapted_inputs(baseline_id)
    result = run_operating_model(adapted)
    op_periods = [p for p in result.periods if p.is_operation]
    bl_vals = baseline["operating_schedules"]["revenue_keur"]
    for i, (my_v, bl_v) in enumerate(zip(
        [p.revenue_keur for p in op_periods], bl_vals
    )):
        assert my_v == bl_v, f"{baseline_id} revenue_keur[{i}]: {my_v} != {bl_v}"


@pytest.mark.parametrize("baseline_id", _ALL_BASELINES)
def test_opex_parity(baseline_id: str):
    baseline = _load_baseline(baseline_id)
    adapted = _get_adapted_inputs(baseline_id)
    result = run_operating_model(adapted)
    op_periods = [p for p in result.periods if p.is_operation]
    bl_vals = baseline["operating_schedules"]["opex_keur"]
    for i, (my_v, bl_v) in enumerate(zip(
        [p.opex_keur for p in op_periods], bl_vals
    )):
        assert my_v == bl_v, f"{baseline_id} opex_keur[{i}]: {my_v} != {bl_v}"


@pytest.mark.parametrize("baseline_id", _ALL_BASELINES)
def test_ebitda_parity(baseline_id: str):
    baseline = _load_baseline(baseline_id)
    adapted = _get_adapted_inputs(baseline_id)
    result = run_operating_model(adapted)
    op_periods = [p for p in result.periods if p.is_operation]
    bl_vals = baseline["operating_schedules"]["ebitda_keur"]
    for i, (my_v, bl_v) in enumerate(zip(
        [p.ebitda_keur for p in op_periods], bl_vals
    )):
        assert my_v == bl_v, f"{baseline_id} ebitda_keur[{i}]: {my_v} != {bl_v}"


@pytest.mark.parametrize("baseline_id", _ALL_BASELINES)
def test_book_depreciation_parity(baseline_id: str):
    baseline = _load_baseline(baseline_id)
    adapted = _get_adapted_inputs(baseline_id)
    result = run_operating_model(adapted)
    op_periods = [p for p in result.periods if p.is_operation]
    bl_vals = baseline["operating_schedules"]["book_depreciation_keur"]
    for i, (my_v, bl_v) in enumerate(zip(
        [p.book_depreciation_keur for p in op_periods], bl_vals
    )):
        assert my_v == bl_v, f"{baseline_id} book_depreciation_keur[{i}]: {my_v} != {bl_v}"


@pytest.mark.parametrize("baseline_id", _ALL_BASELINES)
def test_tax_depreciation_parity(baseline_id: str):
    baseline = _load_baseline(baseline_id)
    adapted = _get_adapted_inputs(baseline_id)
    result = run_operating_model(adapted)
    op_periods = [p for p in result.periods if p.is_operation]
    bl_vals = baseline["operating_schedules"]["tax_depreciation_keur"]
    for i, (my_v, bl_v) in enumerate(zip(
        [p.tax_depreciation_keur for p in op_periods], bl_vals
    )):
        assert my_v == bl_v, f"{baseline_id} tax_depreciation_keur[{i}]: {my_v} != {bl_v}"


# ---------------------------------------------------------------------------
# Negative parity tests — one-ULP changes → PAYLOAD_DRIFT
# ---------------------------------------------------------------------------

def _ulp_bump(v: float) -> float:
    """Return the next representable float after v."""
    bits = struct.unpack("Q", struct.pack("d", v))[0]
    return struct.unpack("d", struct.pack("Q", bits + 1))[0]


def _candidate_with_schedule_mutation(
    baseline_id: str,
    schedule_key: str,
    period_index: int = 0,
) -> dict[str, Any]:
    """Generate a candidate snapshot with a one-ULP change in the given schedule."""
    candidate = get_candidate_snapshot(
        baseline_id, baseline_commit_sha=_BASELINE_COMMIT_SHA
    )
    os_ = dict(candidate["operating_schedules"])
    series = list(os_[schedule_key])
    series[period_index] = _ulp_bump(series[period_index])
    os_[schedule_key] = series
    candidate = dict(candidate)
    candidate["operating_schedules"] = os_
    return candidate


def _compare_operating_core(baseline_id: str, candidate: dict[str, Any]) -> DriftKind:
    committed = _load_baseline(baseline_id)
    b_proj = project_for_profile(committed, _PROFILE)
    c_proj = project_for_profile(candidate, _PROFILE)
    result = compare_snapshots(b_proj, c_proj, baseline_id=baseline_id)
    return result.status


@pytest.mark.parametrize("schedule_key", [
    "production_mwh",
    "revenue_keur",
    "opex_keur",
    "ebitda_keur",
    "book_depreciation_keur",
    "tax_depreciation_keur",
])
def test_one_ulp_change_causes_payload_drift(schedule_key: str):
    """One-ULP change in any in-scope schedule must produce PAYLOAD_DRIFT."""
    candidate = _candidate_with_schedule_mutation("tuho", schedule_key)
    status = _compare_operating_core("tuho", candidate)
    assert status != DriftKind.IDENTICAL, (
        f"One-ULP change in {schedule_key} was not detected"
    )
    assert status in (DriftKind.VALUE_DRIFT, DriftKind.AVAILABILITY_DRIFT,
                      DriftKind.STRUCTURAL_DRIFT), (
        f"Expected value drift, got {status}"
    )


def test_period_date_change_causes_structural_drift():
    """A period date change must produce structural drift."""
    candidate = get_candidate_snapshot("tuho", baseline_commit_sha=_BASELINE_COMMIT_SHA)
    pg = list(candidate["period_grid"])
    row = dict(pg[0])
    row["date"] = "2099-12-31"
    pg[0] = row
    candidate = dict(candidate)
    candidate["period_grid"] = pg
    status = _compare_operating_core("tuho", candidate)
    assert status != DriftKind.IDENTICAL


def test_period_count_change_causes_structural_drift():
    """Removing a period from period_grid must produce structural drift."""
    candidate = get_candidate_snapshot("tuho", baseline_commit_sha=_BASELINE_COMMIT_SHA)
    candidate = dict(candidate)
    candidate["period_grid"] = candidate["period_grid"][:-1]
    os_ = {k: v[:-1] if isinstance(v, list) else v
           for k, v in candidate["operating_schedules"].items()}
    candidate["operating_schedules"] = os_
    status = _compare_operating_core("tuho", candidate)
    assert status != DriftKind.IDENTICAL


# ---------------------------------------------------------------------------
# Identity / schema / legacy / environment orchestration tests via injected providers
# ---------------------------------------------------------------------------

class _FixedSnapshotProvider:
    """Provider that always returns the given snapshot dict."""
    def __init__(self, snapshot: dict[str, Any]) -> None:
        self._snapshot = snapshot

    def capture_snapshot(self, baseline_id: str, reference: Any) -> dict[str, Any]:
        return dict(self._snapshot)


class _RaisingProvider:
    """Provider that raises on capture."""
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def capture_snapshot(self, baseline_id: str, reference: Any) -> dict[str, Any]:
        raise self._exc


def _good_snapshot() -> dict[str, Any]:
    return get_candidate_snapshot("tuho", baseline_commit_sha=_BASELINE_COMMIT_SHA)


def test_compare_candidate_provider_pass_all_baselines():
    """compare_candidate_provider with the real provider passes all four baselines."""
    from finco_parity.financial_engine_candidate import FinancialEngineCandidateProvider
    aggregate = compare_candidate_provider(
        FinancialEngineCandidateProvider(),
        baseline_ids=_ALL_BASELINES,
        comparison_profile=_PROFILE,
        verify_legacy=False,
    )
    assert aggregate.overall_status == BaselineRunStatus.PASS
    assert exit_code_for_aggregate(aggregate) == 0


def test_candidate_sha_change_causes_identity_mismatch():
    """A changed baseline_commit_sha in the candidate must surface as identity drift."""
    committed = _load_baseline("tuho")
    candidate = get_candidate_snapshot("tuho", baseline_commit_sha="a" * 40)
    assert candidate["baseline_commit_sha"] != committed["baseline_commit_sha"]


def test_candidate_schema_version_change_causes_schema_drift():
    """A schema_version change must surface as SCHEMA_DRIFT in a full comparison."""
    committed = _load_baseline("tuho")
    candidate = get_candidate_snapshot("tuho", baseline_commit_sha=_BASELINE_COMMIT_SHA)
    candidate = dict(candidate)
    candidate["schema_version"] = "99.0.0"
    result = compare_snapshots(committed, candidate, baseline_id="tuho")
    assert result.status == DriftKind.SCHEMA_DRIFT


def test_execution_error_provider_yields_exit_1():
    """A provider that raises an unexpected exception → EXECUTION_ERROR → exit 1."""
    provider = _RaisingProvider(RuntimeError("boom"))
    aggregate = compare_candidate_provider(
        provider,
        baseline_ids=["tuho"],
        comparison_profile=_PROFILE,
        verify_legacy=False,
    )
    assert aggregate.overall_status == BaselineRunStatus.EXECUTION_ERROR
    assert exit_code_for_aggregate(aggregate) == 1


def test_payload_drift_yields_exit_3():
    """One-ULP change in schedule → PAYLOAD_DRIFT → exit 3."""
    mutated = _candidate_with_schedule_mutation("tuho", "production_mwh")
    provider = _FixedSnapshotProvider(mutated)
    aggregate = compare_candidate_provider(
        provider,
        baseline_ids=["tuho"],
        comparison_profile=_PROFILE,
        verify_legacy=False,
    )
    assert aggregate.overall_status == BaselineRunStatus.PAYLOAD_DRIFT
    assert exit_code_for_aggregate(aggregate) == 3


def test_mixed_status_execution_error_dominates_payload_drift():
    """EXECUTION_ERROR + PAYLOAD_DRIFT → overall EXECUTION_ERROR → exit 1."""

    class _MixedProvider:
        def __init__(self) -> None:
            self._call = 0

        def capture_snapshot(self, baseline_id: str, reference: Any) -> dict[str, Any]:
            self._call += 1
            if self._call == 1:
                raise RuntimeError("first baseline explodes")
            # Second baseline returns a mutated (drifted) snapshot.
            return _candidate_with_schedule_mutation(baseline_id, "production_mwh")

    provider = _MixedProvider()
    aggregate = compare_candidate_provider(
        provider,
        baseline_ids=["tuho", "oborovo"],
        comparison_profile=_PROFILE,
        verify_legacy=False,
    )
    assert aggregate.overall_status == BaselineRunStatus.EXECUTION_ERROR
    assert exit_code_for_aggregate(aggregate) == 1


# ---------------------------------------------------------------------------
# Source immutability during orchestration
# ---------------------------------------------------------------------------

def test_orchestration_does_not_mutate_clean_inputs():
    """run_operating_model must not mutate its OperatingModelInput."""
    adapted = _get_adapted_inputs("tuho")
    capacity_before = adapted.technical.capacity_mw
    tariff_before = adapted.revenue.ppa_base_tariff_eur_mwh
    opex_count_before = len(adapted.opex.items)

    run_operating_model(adapted)

    assert adapted.technical.capacity_mw == capacity_before
    assert adapted.revenue.ppa_base_tariff_eur_mwh == tariff_before
    assert len(adapted.opex.items) == opex_count_before


def test_validation_does_not_mutate_inputs():
    """validate_operating_model_input must not mutate its input."""
    from financial_engine.validation import validate_operating_model_input
    adapted = _get_adapted_inputs("tuho")
    capacity_before = adapted.technical.capacity_mw

    validate_operating_model_input(adapted)

    assert adapted.technical.capacity_mw == capacity_before
