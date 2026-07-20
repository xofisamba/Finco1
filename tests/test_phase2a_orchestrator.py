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
    if baseline_id == "oborovo":
        # B2 governed drift: FIRST_FULL_CALENDAR_YEAR_AS_BASE policy corrects H2 PPA-term periods.
        # H2 periods (Dec-31 period_end) during years 2031–2042 where legacy
        # AFTER_FIRST_FULL_OPERATING_YEAR applied escalation one year early.
        # H1 periods and post-PPA periods must be identical to baseline.
        # Expected drifting indices: 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22
        _B2_DRIFT_INDICES = frozenset({2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22})
        # Authoritative candidate values for every B2 period (FIRST_FULL_CALENDAR_YEAR_AS_BASE,
        # COD=29-Jun-2030, base_tariff=57.00, ppa_index=0.02).
        # Wrong magnitude in an allowed period FAILS this guard.
        _B2_EXPECTED_CANDIDATE: dict[int, float] = {
            2:  3236.870791604059,
            4:  3277.768293496598,
            6:  3337.426835584944,
            8:  3388.918576702460,
            10: 3441.236626714986,
            12: 3484.846589316390,
            14: 3548.404376921701,
            16: 3603.280964973387,
            18: 3659.037644345373,
            20: 3705.536246168231,
            22: 3773.247440717053,
        }
        _TOL = 1e-6  # kEUR tolerance
        actual_drift_indices: set[int] = set()
        cand_revenues = [p.revenue_keur for p in op_periods]
        for i, (cand_v, bl_v) in enumerate(zip(cand_revenues, bl_vals)):
            if cand_v != bl_v:
                actual_drift_indices.add(i)
        assert frozenset(actual_drift_indices) == _B2_DRIFT_INDICES, (
            f"oborovo B2 revenue drift set mismatch.\n"
            f"  actual:   {sorted(actual_drift_indices)}\n"
            f"  expected: {sorted(_B2_DRIFT_INDICES)}\n"
            "Unrelated revenue periods must be identical to baseline."
        )
        for i, expected_v in _B2_EXPECTED_CANDIDATE.items():
            actual_v = cand_revenues[i]
            assert abs(actual_v - expected_v) < _TOL, (
                f"oborovo B2 revenue_keur[{i}]: candidate={actual_v!r}, "
                f"expected={expected_v!r}, delta={actual_v - expected_v!r}. "
                f"Wrong magnitude in B2-governed period."
            )
        return

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
# compare_candidate_provider — exact freeze guard
# ---------------------------------------------------------------------------

# Exact governed drift surface per baseline (Phase 2E freeze).
# Each entry is the set of schedule names (path prefix before [N]) that may drift.
# Any path outside this set causes the guard to fail.
#
# Oborovo: B1 authoritative OPEX source correction propagates to opex_keur and ebitda_keur;
#          B3 book depreciation basis (financing costs included) propagates to book_depreciation_keur.
#          No production, revenue, tax_depreciation, financing, or other schedule drift is allowed.
#
# TUHO: B3 generic book_depreciable_capex_items() architecture produces drift in book_depreciation_keur
#       for all projects with non-zero idc_keur/bank_fees_keur.
#       TUHO project-specific financial treatment is OPEN — not source-validated.
#       No production, opex, ebitda, revenue, tax_depreciation, or other schedule drift is allowed.
_GOVERNED_DRIFT_SCHEDULES: dict[str, frozenset[str]] = {
    "oborovo": frozenset({
        "operating_schedules.opex_keur",
        "operating_schedules.revenue_keur",   # B2: PPA indexation policy corrected to FIRST_FULL_CALENDAR_YEAR_AS_BASE
        "operating_schedules.ebitda_keur",
        "operating_schedules.book_depreciation_keur",
    }),
    "tuho": frozenset({
        "operating_schedules.book_depreciation_keur",
    }),
    "generic_solar": frozenset(),   # must be IDENTICAL (Jan-1 COD: FIRST_FULL_CY == AFTER_OY)
    "generic_wind": frozenset(),   # must be IDENTICAL (legacy unmigrated path preserved)
}


def _drift_schedule_names(differences) -> frozenset[str]:
    """Extract the schedule name (path prefix before '[N]') from each difference."""
    names: set[str] = set()
    for d in differences:
        # e.g. 'operating_schedules.opex_keur[12]' → 'operating_schedules.opex_keur'
        bracket = d.path.find("[")
        prefix = d.path[:bracket] if bracket != -1 else d.path
        names.add(prefix)
    return frozenset(names)


def test_compare_candidate_provider_pass_all_baselines():
    """Phase 2E freeze guard: exact governed drift surface for all four baselines.

    generic_solar must be IDENTICAL (no policy migration; legacy path preserved).
    generic_wind must be IDENTICAL (no policy migration; legacy path preserved).
    oborovo may drift only in opex_keur, revenue_keur, ebitda_keur, book_depreciation_keur (B1+B2+B3).
    tuho may drift only in book_depreciation_keur (B3 generic architecture; OPEN treatment).
    Any additional drift field fails this guard.
    """
    from finco_parity.manifest import SNAPSHOTS_DIR

    for baseline_id in _ALL_BASELINES:
        snap_path = SNAPSHOTS_DIR / f"{baseline_id}.json"
        with open(snap_path) as f:
            baseline_snap = json.load(f)

        candidate = get_candidate_snapshot(
            baseline_id, baseline_commit_sha=_BASELINE_COMMIT_SHA
        )
        b_proj = project_for_profile(baseline_snap, _PROFILE)
        c_proj = project_for_profile(candidate, _PROFILE)
        result = compare_snapshots(b_proj, c_proj, baseline_id=baseline_id)

        allowed = _GOVERNED_DRIFT_SCHEDULES[baseline_id]
        actual = _drift_schedule_names(result.differences)
        unexpected = actual - allowed

        assert not unexpected, (
            f"[{baseline_id}] unexpected drift in schedule(s) outside governed surface: "
            f"{sorted(unexpected)}. "
            f"Governed surface: {sorted(allowed)}. "
            f"Total diffs: {len(result.differences)}."
        )


def test_freeze_guard_rejects_unrelated_drift():
    """Proof: injecting production_mwh drift into oborovo fails the exact freeze guard.

    Demonstrates that the guard is not vacuously broad — a one-ULP production mutation
    adds 'operating_schedules.production_mwh' to the drift set which is outside the
    governed surface and must cause an assertion failure.
    """
    from finco_parity.manifest import SNAPSHOTS_DIR

    baseline_id = "oborovo"
    snap_path = SNAPSHOTS_DIR / f"{baseline_id}.json"
    with open(snap_path) as f:
        baseline_snap = json.load(f)

    # Inject a one-ULP mutation into production_mwh at period 0
    mutated = _candidate_with_schedule_mutation(baseline_id, "production_mwh")
    b_proj = project_for_profile(baseline_snap, _PROFILE)
    c_proj = project_for_profile(mutated, _PROFILE)
    result = compare_snapshots(b_proj, c_proj, baseline_id=baseline_id)

    allowed = _GOVERNED_DRIFT_SCHEDULES[baseline_id]
    actual = _drift_schedule_names(result.differences)
    unexpected = actual - allowed

    # The guard must detect the injected drift
    assert "operating_schedules.production_mwh" in unexpected, (
        "Injection test failed: production_mwh mutation was not detected as unexpected drift"
    )


def test_b2_magnitude_guard_rejects_wrong_revenue_in_allowed_period():
    """Proof: wrong revenue magnitude inside an allowed B2 period fails the B2 exact guard.

    Even though index 2 is in _B2_DRIFT_INDICES (the set is correct), a wrong magnitude
    must still fail.  This proves the guard is not satisfied by direction-only checks.
    """
    baseline = _load_baseline("oborovo")
    adapted = _get_adapted_inputs("oborovo")
    result = run_operating_model(adapted)
    op_periods = [p for p in result.periods if p.is_operation]
    bl_vals = baseline["operating_schedules"]["revenue_keur"]

    # Build candidate revenues with a wrong magnitude at period 2 (a B2 period)
    candidate_revenues = [p.revenue_keur for p in op_periods]
    # Inject a +1 kEUR mutation at period 2 (B2 allowed period)
    bad_revenues = list(candidate_revenues)
    bad_revenues[2] = candidate_revenues[2] + 1.0

    _B2_DRIFT_INDICES = frozenset({2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22})
    _B2_EXPECTED_CANDIDATE = {
        2:  3236.870791604059,
        4:  3277.768293496598,
        6:  3337.426835584944,
        8:  3388.918576702460,
        10: 3441.236626714986,
        12: 3484.846589316390,
        14: 3548.404376921701,
        16: 3603.280964973387,
        18: 3659.037644345373,
        20: 3705.536246168231,
        22: 3773.247440717053,
    }
    _TOL = 1e-6

    # The drift-index set is still correct (period 2 still drifts from baseline)
    actual_drift_indices: set[int] = set()
    for i, (cand_v, bl_v) in enumerate(zip(bad_revenues, bl_vals)):
        if cand_v != bl_v:
            actual_drift_indices.add(i)
    assert frozenset(actual_drift_indices) == _B2_DRIFT_INDICES, (
        "Precondition: injected magnitude-only mutation should not change drift index set"
    )

    # But the magnitude check must FAIL
    magnitude_violations = []
    for i, expected_v in _B2_EXPECTED_CANDIDATE.items():
        actual_v = bad_revenues[i]
        if abs(actual_v - expected_v) >= _TOL:
            magnitude_violations.append((i, actual_v, expected_v))

    assert magnitude_violations, (
        "Expected magnitude guard to detect wrong revenue at period 2, but it passed. "
        "The guard must reject wrong magnitudes inside B2-allowed periods."
    )
    assert any(i == 2 for i, _, _ in magnitude_violations), (
        f"Expected violation at period 2, got: {magnitude_violations}"
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
