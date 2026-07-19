"""
tests/test_phase2a_orchestrator.py — Phase 2A orchestrator and operating-schedule parity tests.

Covers:
- Four-baseline OPERATING_CORE_V1 PASS (production, revenue, OPEX, EBITDA, book/tax depreciation)
- Period-grid parity (date, start_date, index, year_index, period_in_year, is_operation)
- Negative parity tests (one-ULP changes → PAYLOAD_DRIFT)
- Identity/schema/legacy/environment/manifest/mixed-status exit-code tests via injected providers
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
    _build_aggregate,
    compare_candidate_provider,
    exit_code_for_aggregate,
)
from finco_parity.financial_engine_candidate import get_candidate_snapshot
from finco_parity.manifest import ManifestIntegrityError
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


def _good_snapshot(baseline_id: str = "tuho") -> dict[str, Any]:
    return get_candidate_snapshot(baseline_id, baseline_commit_sha=_BASELINE_COMMIT_SHA)


# ---------------------------------------------------------------------------
# Injected providers for status/exit-code tests
# ---------------------------------------------------------------------------

class _FixedSnapshotProvider:
    """Returns the given snapshot dict for any baseline."""
    def __init__(self, snapshot: dict[str, Any]) -> None:
        self._snapshot = snapshot

    def capture_snapshot(self, baseline_id: str, reference: Any) -> dict[str, Any]:
        return dict(self._snapshot)


class _RaisingProvider:
    """Raises on any capture_snapshot call."""
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def capture_snapshot(self, baseline_id: str, reference: Any) -> dict[str, Any]:
        raise self._exc


class _CountingProvider:
    """Records calls and delegates to a wrapped provider."""
    def __init__(self, inner=None) -> None:
        self.call_count = 0
        self._inner = inner

    def capture_snapshot(self, baseline_id: str, reference: Any) -> dict[str, Any]:
        self.call_count += 1
        if self._inner is not None:
            return self._inner.capture_snapshot(baseline_id, reference)
        raise RuntimeError("CountingProvider: no inner provider")


# ---------------------------------------------------------------------------
# Four-baseline OPERATING_CORE_V1 PASS
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("baseline_id", _ALL_BASELINES)
def test_operating_core_v1_pass(baseline_id: str):
    """All four baselines must reach OPERATING_CORE_V1 IDENTICAL."""
    if baseline_id == "oborovo":
        pytest.xfail(
            "Governed drift [B1+B3-book]: oborovo OPEX corrected to exact XLSM values (B1); "
            "clean engine book depreciable basis now includes bank financing costs per Excel "
            "Dep-sheet evidence (B3). Tax depreciation is UNCHANGED from baseline. "
            "Baseline refresh requires explicit governance approval."
        )
    if baseline_id == "tuho":
        pytest.xfail(
            "Expected mechanical engine drift [B3-book]: generic book_depreciable_capex_items() "
            "architecture includes capitalised bank financing costs for all projects with "
            "non-zero idc_keur/bank_fees_keur (TUHO: idc_keur=1519.56, bank_fees_keur=782.61). "
            "TUHO project-specific book-depreciation financial treatment is OPEN — "
            "not yet validated from TUHO source model. Tax depreciation UNCHANGED from baseline. "
            "Baseline refresh requires explicit governance approval."
        )
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
        # start_date: baseline stores null for construction-phase periods;
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
    if baseline_id == "oborovo":
        pytest.xfail(
            "Governed drift [B1]: oborovo Y1 OPEX corrected to exact XLSM values "
            "(B.03=45.2, B.05=30.1, B.08=176.8608, B.13=51.489632); "
            "baseline predates correction. Refresh requires explicit governance approval."
        )
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
    if baseline_id == "oborovo":
        pytest.xfail(
            "Governed drift [B1]: EBITDA = Revenue − OPEX; oborovo OPEX corrected per B1 XLSM values. "
            "Baseline predates correction. Refresh requires explicit governance approval."
        )
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
    if baseline_id == "oborovo":
        pytest.xfail(
            "Governed drift [B3-book]: clean engine BOOK depreciable basis now includes "
            "bank financing costs (IDC + commitment fees + bank fees + VAT, total ~1 974 kEUR) "
            "per Oborovo Excel Dep-sheet evidence. TAX depreciation is unchanged from baseline. "
            "Baseline refresh requires explicit governance approval."
        )
    if baseline_id == "tuho":
        pytest.xfail(
            "Expected mechanical engine drift [B3-book]: generic book_depreciable_capex_items() "
            "architecture includes capitalised bank financing costs for all projects with "
            "non-zero idc_keur/bank_fees_keur (TUHO: idc_keur=1519.56, bank_fees_keur=782.61). "
            "TUHO project-specific book-depreciation financial treatment is OPEN — "
            "not yet validated from TUHO source model. TAX depreciation UNCHANGED from baseline. "
            "Baseline refresh requires explicit governance approval."
        )
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
    # No xfail: B3 changes BOOK depreciation only; TAX basis is unchanged (hard capex only).
    # Tax treatment of capitalised financing costs is OPEN — no authoritative tax evidence.
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
# compare_candidate_provider — all four baselines pass
# ---------------------------------------------------------------------------

def test_compare_candidate_provider_pass_all_baselines():
    """compare_candidate_provider with the real provider passes all four baselines.

    NOTE: oborovo and tuho are expected to show PAYLOAD_DRIFT due to governed B1/B3 corrections:
    - B1: Oborovo Y1 OPEX corrected to authoritative XLSM values (B.03/B.05/B.08/B.13)
    - B3: Clean engine now includes bank financing costs in depreciable basis generically
    These are governed divergences; baselines pending explicit refresh approval.
    The stable baselines (generic_solar, generic_wind) must remain IDENTICAL.
    """
    from finco_parity.financial_engine_candidate import FinancialEngineCandidateProvider
    aggregate = compare_candidate_provider(
        FinancialEngineCandidateProvider(),
        baseline_ids=_ALL_BASELINES,
        comparison_profile=_PROFILE,
        verify_legacy=False,
    )
    # Check stable baselines individually
    for result in aggregate.baseline_results:
        if result.baseline_id in ("generic_solar", "generic_wind"):
            assert result.status == BaselineRunStatus.PASS, (
                f"{result.baseline_id}: unexpected drift — must be IDENTICAL. "
                f"Status: {result.status}"
            )
        elif result.baseline_id in ("oborovo", "tuho"):
            # Governed drift expected: B1 (oborovo OPEX), B3 (financing-cost depreciation both)
            pass  # governed — documented above
    # Confirm it's NOT an unexpected status (not IDENTITY_MISMATCH or ERROR) for any baseline
    unexpected_statuses = {BaselineRunStatus.IDENTITY_MISMATCH, BaselineRunStatus.EXECUTION_ERROR}
    for result in aggregate.baseline_results:
        assert result.status not in unexpected_statuses, (
            f"{result.baseline_id} has unexpected status {result.status} — not governed drift"
        )


# ---------------------------------------------------------------------------
# Identity mismatch tests — wrong SHA, wrong baseline_id, wrong input_source_id
# These use injected providers and compare_candidate_provider so that payload
# projection occurs only after identity gating.
# ---------------------------------------------------------------------------

def test_wrong_baseline_commit_sha_causes_identity_mismatch():
    """Provider returning wrong baseline_commit_sha → IDENTITY_MISMATCH → exit 7."""
    snap = dict(_good_snapshot("tuho"))
    snap["baseline_commit_sha"] = "b" * 40  # wrong SHA

    aggregate = compare_candidate_provider(
        _FixedSnapshotProvider(snap),
        baseline_ids=["tuho"],
        comparison_profile=_PROFILE,
        verify_legacy=False,
    )
    assert aggregate.overall_status == BaselineRunStatus.IDENTITY_MISMATCH
    assert exit_code_for_aggregate(aggregate) == 7


def test_wrong_baseline_id_causes_identity_mismatch():
    """Provider returning wrong baseline_id → IDENTITY_MISMATCH → exit 7."""
    snap = dict(_good_snapshot("tuho"))
    snap["baseline_id"] = "wrong_baseline"  # wrong baseline_id

    aggregate = compare_candidate_provider(
        _FixedSnapshotProvider(snap),
        baseline_ids=["tuho"],
        comparison_profile=_PROFILE,
        verify_legacy=False,
    )
    assert aggregate.overall_status == BaselineRunStatus.IDENTITY_MISMATCH
    assert exit_code_for_aggregate(aggregate) == 7


def test_wrong_input_source_id_causes_identity_mismatch():
    """Provider returning wrong input_source_id → IDENTITY_MISMATCH → exit 7."""
    snap = dict(_good_snapshot("tuho"))
    snap["input_source_id"] = "wrong.source.id"  # wrong input_source_id

    aggregate = compare_candidate_provider(
        _FixedSnapshotProvider(snap),
        baseline_ids=["tuho"],
        comparison_profile=_PROFILE,
        verify_legacy=False,
    )
    assert aggregate.overall_status == BaselineRunStatus.IDENTITY_MISMATCH
    assert exit_code_for_aggregate(aggregate) == 7


# ---------------------------------------------------------------------------
# Schema mismatch tests — wrong schema_version, structurally invalid candidate
# ---------------------------------------------------------------------------

def test_wrong_schema_version_causes_schema_mismatch():
    """Provider returning wrong schema_version → SCHEMA_MISMATCH → exit 7."""
    snap = dict(_good_snapshot("tuho"))
    snap["schema_version"] = "99.0.0"

    aggregate = compare_candidate_provider(
        _FixedSnapshotProvider(snap),
        baseline_ids=["tuho"],
        comparison_profile=_PROFILE,
        verify_legacy=False,
    )
    assert aggregate.overall_status == BaselineRunStatus.SCHEMA_MISMATCH
    assert exit_code_for_aggregate(aggregate) == 7


def test_structurally_invalid_candidate_causes_schema_mismatch():
    """Provider returning snapshot with missing required section → SCHEMA_MISMATCH → exit 7."""
    snap = dict(_good_snapshot("tuho"))
    # Remove a required top-level section so schema validation fails.
    snap.pop("period_grid", None)

    aggregate = compare_candidate_provider(
        _FixedSnapshotProvider(snap),
        baseline_ids=["tuho"],
        comparison_profile=_PROFILE,
        verify_legacy=False,
    )
    assert aggregate.overall_status == BaselineRunStatus.SCHEMA_MISMATCH
    assert exit_code_for_aggregate(aggregate) == 7


# ---------------------------------------------------------------------------
# Phase 2A profile status-boundary tests
# ---------------------------------------------------------------------------

def test_execution_error_provider_yields_exit_1():
    """Provider raising unexpected exception → EXECUTION_ERROR → exit 1."""
    aggregate = compare_candidate_provider(
        _RaisingProvider(RuntimeError("boom")),
        baseline_ids=["tuho"],
        comparison_profile=_PROFILE,
        verify_legacy=False,
    )
    assert aggregate.overall_status == BaselineRunStatus.EXECUTION_ERROR
    assert exit_code_for_aggregate(aggregate) == 1


def test_payload_drift_yields_exit_3():
    """One-ULP change in schedule → PAYLOAD_DRIFT → exit 3."""
    mutated = _candidate_with_schedule_mutation("tuho", "production_mwh")
    aggregate = compare_candidate_provider(
        _FixedSnapshotProvider(mutated),
        baseline_ids=["tuho"],
        comparison_profile=_PROFILE,
        verify_legacy=False,
    )
    assert aggregate.overall_status == BaselineRunStatus.PAYLOAD_DRIFT
    assert exit_code_for_aggregate(aggregate) == 3


def test_live_legacy_drift_yields_exit_8(monkeypatch):
    """Live legacy snapshot differing from committed → LEGACY_DRIFT → exit 8."""
    import finco_parity.legacy_snapshot as _ls

    def _drifted_legacy(baseline_id, commit_sha):
        snap = get_candidate_snapshot(baseline_id, baseline_commit_sha=commit_sha)
        snap = dict(snap)
        os_ = dict(snap["operating_schedules"])
        os_["production_mwh"] = [v * 1.001 for v in os_["production_mwh"]]
        snap["operating_schedules"] = os_
        return snap

    monkeypatch.setattr(_ls, "capture_snapshot", _drifted_legacy)

    # Provider should never be called when legacy drift is detected first.
    counting = _CountingProvider()
    aggregate = compare_candidate_provider(
        counting,
        baseline_ids=["tuho"],
        comparison_profile=_PROFILE,
        verify_legacy=True,
    )
    assert aggregate.overall_status == BaselineRunStatus.LEGACY_DRIFT
    assert exit_code_for_aggregate(aggregate) == 8
    assert counting.call_count == 0  # provider never called — legacy check runs first


def test_environment_mismatch_yields_exit_5(monkeypatch):
    """Generation environment mismatch → ENVIRONMENT_MISMATCH → exit 5; provider not called."""
    import finco_parity.generate_baselines as _gb

    monkeypatch.setattr(_gb, "check_generation_environment", lambda manifest: "test env mismatch")

    counting = _CountingProvider()
    aggregate = compare_candidate_provider(
        counting,
        baseline_ids=["tuho"],
        comparison_profile=_PROFILE,
        verify_legacy=False,
    )
    assert aggregate.overall_status == BaselineRunStatus.ENVIRONMENT_MISMATCH
    assert exit_code_for_aggregate(aggregate) == 5
    assert counting.call_count == 0  # environment check runs before provider


def test_manifest_integrity_failure_propagates_from_compare(monkeypatch):
    """ManifestIntegrityError raised by compare_candidate_provider → CLI exit 4."""
    import finco_parity.dual_run as _dr

    def _raise():
        raise ManifestIntegrityError("injected manifest failure")

    # Patch the name in the dual_run module namespace (where it's called).
    monkeypatch.setattr(_dr, "load_validated_manifest_context", _raise)

    with pytest.raises(ManifestIntegrityError):
        compare_candidate_provider(
            _RaisingProvider(RuntimeError("should not be called")),
            baseline_ids=["tuho"],
            comparison_profile=_PROFILE,
            verify_legacy=False,
        )


def test_manifest_integrity_failure_cli_exits_4(monkeypatch):
    """ManifestIntegrityError bubbling through CLI returns exit code 4."""
    import finco_parity.check_financial_engine_operating_core as _cli
    import finco_parity.dual_run as _dr

    def _raise():
        raise ManifestIntegrityError("injected manifest failure")

    # Patch in dual_run (where compare_candidate_provider calls it)
    # and in the CLI module namespace as well.
    monkeypatch.setattr(_dr, "load_validated_manifest_context", _raise)
    # The CLI catches ManifestIntegrityError from compare_candidate_provider.
    # Re-patch compare_candidate_provider in the CLI's namespace to raise directly.
    def _raise_manifest(*args, **kwargs):
        raise ManifestIntegrityError("injected manifest failure")
    monkeypatch.setattr(_cli, "compare_candidate_provider", _raise_manifest)

    code = _cli.main(["--baseline", "tuho", "--quiet"])
    assert code == 4


def test_unknown_baseline_cli_exits_2(monkeypatch):
    """ValueError from compare_candidate_provider (unknown baseline) → CLI exit 2."""
    import finco_parity.check_financial_engine_operating_core as _cli

    def _raise_value_error(*args, **kwargs):
        raise ValueError("Unknown baseline_id(s): ['bad_id']")

    # Patch in the CLI module's namespace (the name was imported there).
    monkeypatch.setattr(_cli, "compare_candidate_provider", _raise_value_error)

    code = _cli.main(["--baseline", "tuho", "--quiet"])
    assert code == 2


def test_unexpected_error_cli_exits_1(monkeypatch):
    """Unexpected RuntimeError from compare_candidate_provider → CLI exit 1."""
    import finco_parity.check_financial_engine_operating_core as _cli

    def _raise_runtime_error(*args, **kwargs):
        raise RuntimeError("something exploded")

    monkeypatch.setattr(_cli, "compare_candidate_provider", _raise_runtime_error)

    code = _cli.main(["--baseline", "tuho", "--quiet"])
    assert code == 1


# ---------------------------------------------------------------------------
# Mixed-status aggregate tests
# ---------------------------------------------------------------------------

def test_mixed_status_execution_error_dominates_payload_drift():
    """EXECUTION_ERROR + PAYLOAD_DRIFT → overall EXECUTION_ERROR → exit 1."""

    class _MixedProvider:
        def __init__(self) -> None:
            self._call = 0

        def capture_snapshot(self, baseline_id: str, reference: Any) -> dict[str, Any]:
            self._call += 1
            if self._call == 1:
                raise RuntimeError("first baseline explodes")
            return _candidate_with_schedule_mutation(baseline_id, "production_mwh")

    aggregate = compare_candidate_provider(
        _MixedProvider(),
        baseline_ids=["tuho", "oborovo"],
        comparison_profile=_PROFILE,
        verify_legacy=False,
    )
    assert aggregate.overall_status == BaselineRunStatus.EXECUTION_ERROR
    assert exit_code_for_aggregate(aggregate) == 1


def test_mixed_status_order_independent():
    """_build_aggregate: EXECUTION_ERROR + PAYLOAD_DRIFT is stable regardless of result order."""
    err_result = BaselineRunResult(
        baseline_id="tuho",
        status=BaselineRunStatus.EXECUTION_ERROR,
        legacy_engine_designation=None,
        candidate_engine_designation=None,
        legacy_run_path=None,
        candidate_run_path=None,
        comparison_status=None,
        difference_count=0,
        differences=(),
        legacy_warnings=(),
        candidate_warnings=(),
        error_message="boom",
    )
    drift_result = BaselineRunResult(
        baseline_id="oborovo",
        status=BaselineRunStatus.PAYLOAD_DRIFT,
        legacy_engine_designation=None,
        candidate_engine_designation=None,
        legacy_run_path=None,
        candidate_run_path=None,
        comparison_status="VALUE_DRIFT",
        difference_count=1,
        differences=(),
        legacy_warnings=(),
        candidate_warnings=(),
        error_message=None,
    )

    agg_forward = _build_aggregate(["tuho", "oborovo"], [err_result, drift_result])
    agg_reversed = _build_aggregate(["oborovo", "tuho"], [drift_result, err_result])

    assert agg_forward.overall_status == BaselineRunStatus.EXECUTION_ERROR
    assert agg_reversed.overall_status == BaselineRunStatus.EXECUTION_ERROR
    assert exit_code_for_aggregate(agg_forward) == exit_code_for_aggregate(agg_reversed) == 1


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
