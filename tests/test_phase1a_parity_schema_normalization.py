"""
Phase 1A — Tests for finco_parity.schema and finco_parity.normalization.

Scope: unit tests only.  No engine execution.  No database.  No filesystem.
"""
from __future__ import annotations

import dataclasses
import datetime
import enum
import math
from decimal import Decimal
from typing import Any

import pytest

from finco_parity.schema import (
    SCHEMA_VERSION,
    UNAVAILABLE,
    SnapshotValidationError,
    build_empty_snapshot,
    validate_snapshot,
)
from finco_parity.normalization import (
    NormalizationError,
    normalize_value,
    normalize_snapshot,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_snapshot(**overrides) -> dict[str, Any]:
    """Build a structurally valid minimal snapshot."""
    base = build_empty_snapshot(
        baseline_id="test_baseline",
        engine_designation="test_engine",
        baseline_commit_sha="abc123",
        run_path_id="test.run_path",
        input_source_id="test.input_source",
    )
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Section A: UNAVAILABLE sentinel
# ---------------------------------------------------------------------------

class TestUnavailableSentinel:
    def test_unavailable_is_none(self):
        assert UNAVAILABLE is None

    def test_unavailable_distinct_from_zero(self):
        assert UNAVAILABLE != 0.0
        assert UNAVAILABLE != 0


# ---------------------------------------------------------------------------
# Section B: validate_snapshot — required keys
# ---------------------------------------------------------------------------

class TestValidateSnapshotRequiredKeys:
    def test_valid_empty_snapshot_passes(self):
        snap = _minimal_snapshot()
        validate_snapshot(snap)  # must not raise

    def test_wrong_schema_version_raises(self):
        snap = _minimal_snapshot(schema_version="0.0.1")
        with pytest.raises(SnapshotValidationError, match="schema_version"):
            validate_snapshot(snap)

    def test_missing_baseline_id_raises(self):
        snap = _minimal_snapshot()
        del snap["baseline_id"]
        with pytest.raises(SnapshotValidationError):
            validate_snapshot(snap)

    def test_empty_baseline_id_raises(self):
        snap = _minimal_snapshot(baseline_id="")
        with pytest.raises(SnapshotValidationError, match="baseline_id"):
            validate_snapshot(snap)

    def test_missing_period_grid_raises(self):
        snap = _minimal_snapshot()
        del snap["period_grid"]
        with pytest.raises(SnapshotValidationError):
            validate_snapshot(snap)

    def test_period_grid_not_list_raises(self):
        snap = _minimal_snapshot(period_grid={})
        with pytest.raises(SnapshotValidationError, match="period_grid"):
            validate_snapshot(snap)

    def test_period_grid_row_missing_period_index_raises(self):
        snap = _minimal_snapshot(period_grid=[{"no_period_index": 0}])
        with pytest.raises(SnapshotValidationError, match="period_index"):
            validate_snapshot(snap)

    def test_period_grid_row_not_dict_raises(self):
        snap = _minimal_snapshot(period_grid=[42])
        with pytest.raises(SnapshotValidationError):
            validate_snapshot(snap)

    def test_missing_operating_schedules_raises(self):
        snap = _minimal_snapshot()
        del snap["operating_schedules"]
        with pytest.raises(SnapshotValidationError):
            validate_snapshot(snap)

    def test_operating_schedules_not_dict_raises(self):
        snap = _minimal_snapshot(operating_schedules=[])
        with pytest.raises(SnapshotValidationError, match="operating_schedules"):
            validate_snapshot(snap)

    def test_missing_financing_raises(self):
        snap = _minimal_snapshot()
        del snap["financing"]
        with pytest.raises(SnapshotValidationError):
            validate_snapshot(snap)

    def test_financing_not_dict_raises(self):
        snap = _minimal_snapshot(financing=[])
        with pytest.raises(SnapshotValidationError, match="financing"):
            validate_snapshot(snap)

    def test_missing_returns_raises(self):
        snap = _minimal_snapshot()
        del snap["returns"]
        with pytest.raises(SnapshotValidationError):
            validate_snapshot(snap)

    def test_returns_not_dict_raises(self):
        snap = _minimal_snapshot(returns=[])
        with pytest.raises(SnapshotValidationError, match="returns"):
            validate_snapshot(snap)

    def test_warnings_not_list_raises(self):
        snap = _minimal_snapshot(warnings="oops")
        with pytest.raises(SnapshotValidationError, match="warnings"):
            validate_snapshot(snap)

    def test_unavailable_sections_not_list_raises(self):
        snap = _minimal_snapshot(unavailable_sections="oops")
        with pytest.raises(SnapshotValidationError, match="unavailable_sections"):
            validate_snapshot(snap)

    def test_non_dict_snapshot_raises(self):
        with pytest.raises(SnapshotValidationError, match="dict"):
            validate_snapshot([])

    def test_period_grid_with_valid_row_passes(self):
        snap = _minimal_snapshot(period_grid=[{"period_index": 0, "start_date": "2025-01-01"}])
        validate_snapshot(snap)  # must not raise


# ---------------------------------------------------------------------------
# Section C: build_empty_snapshot structure
# ---------------------------------------------------------------------------

class TestBuildEmptySnapshot:
    def test_schema_version_correct(self):
        snap = _minimal_snapshot()
        assert snap["schema_version"] == SCHEMA_VERSION

    def test_all_required_keys_present(self):
        snap = _minimal_snapshot()
        validate_snapshot(snap)

    def test_period_grid_empty_list(self):
        snap = _minimal_snapshot()
        assert snap["period_grid"] == []

    def test_warnings_empty_list(self):
        snap = _minimal_snapshot()
        assert snap["warnings"] == []

    def test_financing_has_senior_debt(self):
        snap = _minimal_snapshot()
        assert "senior_debt" in snap["financing"]

    def test_financing_has_shl(self):
        snap = _minimal_snapshot()
        assert "shl" in snap["financing"]

    def test_financing_has_equity(self):
        snap = _minimal_snapshot()
        assert "equity" in snap["financing"]

    def test_financial_statements_unavailable(self):
        snap = _minimal_snapshot()
        assert snap["financial_statements"] is UNAVAILABLE


# ---------------------------------------------------------------------------
# Section D: normalize_value — primitive types
# ---------------------------------------------------------------------------

class TestNormalizeValuePrimitives:
    def test_none_passes_through(self):
        assert normalize_value(None) is None

    def test_bool_true(self):
        assert normalize_value(True) is True

    def test_bool_false(self):
        assert normalize_value(False) is False

    def test_int_passes_through(self):
        assert normalize_value(42) == 42

    def test_float_passes_through(self):
        assert normalize_value(3.14) == pytest.approx(3.14)

    def test_str_passes_through(self):
        assert normalize_value("hello") == "hello"

    def test_decimal_to_float(self):
        result = normalize_value(Decimal("1.5"))
        assert isinstance(result, float)
        assert result == pytest.approx(1.5)

    def test_nan_becomes_none(self):
        assert normalize_value(float("nan")) is None

    def test_inf_becomes_none(self):
        assert normalize_value(float("inf")) is None

    def test_neg_inf_becomes_none(self):
        assert normalize_value(float("-inf")) is None

    def test_date_to_iso(self):
        d = datetime.date(2025, 6, 15)
        assert normalize_value(d) == "2025-06-15"

    def test_datetime_to_date_iso(self):
        dt = datetime.datetime(2025, 6, 15, 12, 30, 0)
        assert normalize_value(dt) == "2025-06-15"

    def test_zero_float_preserved(self):
        # 0.0 must remain 0.0, not become None
        assert normalize_value(0.0) == 0.0

    def test_zero_int_preserved(self):
        assert normalize_value(0) == 0


# ---------------------------------------------------------------------------
# Section E: normalize_value — containers
# ---------------------------------------------------------------------------

class TestNormalizeValueContainers:
    def test_list_recursed(self):
        assert normalize_value([1, 2, 3]) == [1, 2, 3]

    def test_tuple_to_list(self):
        assert normalize_value((1, 2)) == [1, 2]

    def test_dict_keys_str(self):
        result = normalize_value({1: "a"})
        assert "1" in result

    def test_dict_values_recursed(self):
        result = normalize_value({"k": Decimal("2.0")})
        assert isinstance(result["k"], float)

    def test_nested_list(self):
        assert normalize_value([[1, 2], [3, 4]]) == [[1, 2], [3, 4]]

    def test_empty_list(self):
        assert normalize_value([]) == []

    def test_empty_dict(self):
        assert normalize_value({}) == {}


# ---------------------------------------------------------------------------
# Section F: normalize_value — enum and dataclass
# ---------------------------------------------------------------------------

class _Color(enum.Enum):
    RED = "red"
    BLUE = 2


@dataclasses.dataclass
class _SimplePoint:
    x: float
    y: float
    label: str = "origin"


class TestNormalizeValueEnumDataclass:
    def test_str_enum_value(self):
        assert normalize_value(_Color.RED) == "red"

    def test_int_enum_value(self):
        assert normalize_value(_Color.BLUE) == 2

    def test_dataclass_fields(self):
        p = _SimplePoint(x=1.0, y=2.0)
        result = normalize_value(p)
        assert isinstance(result, dict)
        assert result["x"] == 1.0
        assert result["y"] == 2.0
        assert result["label"] == "origin"

    def test_dataclass_keys_sorted(self):
        p = _SimplePoint(x=1.0, y=2.0, label="z")
        result = normalize_value(p)
        assert list(result.keys()) == sorted(result.keys())

    def test_unsupported_type_raises(self):
        class _Blob:
            pass
        with pytest.raises(NormalizationError):
            normalize_value(_Blob())


# ---------------------------------------------------------------------------
# Section G: normalize_snapshot — smoke test (mock WaterfallResult)
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class _MockPeriod:
    period: int
    year_index: float
    period_in_year: int
    start_date: datetime.date
    end_date: datetime.date
    is_operation: bool
    is_construction: bool
    generation_mwh: float
    revenue_keur: float
    opex_keur: float
    ebitda_keur: float
    depreciation_keur: float
    tax_keur: float
    cf_after_tax_keur: float
    senior_interest_keur: float
    senior_principal_keur: float
    senior_ds_keur: float
    dscr: float
    senior_balance_keur: float
    tax_depreciation_audit_keur: float
    shl_opening_keur: float = 0.0
    shl_interest_keur: float = 0.0
    shl_principal_keur: float = 0.0
    shl_balance_keur: float = 0.0
    shl_pik_accrual_keur: float = 0.0
    distributions_keur: float = 0.0
    equity_injection_keur: float = 0.0
    taxable_income_keur: float = 0.0
    deductible_interest_keur: float = 0.0
    disallowed_interest_keur: float = 0.0
    loss_carryforward_keur: float = 0.0
    fiscal_reintegration_keur: float = 0.0
    dsra_balance_keur: float = 0.0


@dataclasses.dataclass
class _MockWaterfallResult:
    periods: list[_MockPeriod]
    project_irr: float | None = None
    equity_irr: float | None = None
    avg_dscr: float | None = None
    actual_avg_dscr: float | None = None
    min_dscr: float | None = None
    actual_min_dscr: float | None = None
    total_revenue_keur: float | None = None
    total_ebitda_keur: float | None = None
    total_opex_keur: float | None = None
    total_tax_keur: float | None = None
    total_senior_ds_keur: float | None = None
    total_distributions_keur: float | None = None
    equity_irr_method: str | None = None


def _make_mock_result(n_periods: int = 3) -> _MockWaterfallResult:
    periods = []
    for i in range(n_periods):
        periods.append(_MockPeriod(
            period=i,
            year_index=float(i),
            period_in_year=1,
            start_date=datetime.date(2025, 1, 1),
            end_date=datetime.date(2025, 12, 31),
            is_operation=(i > 0),
            is_construction=(i == 0),
            generation_mwh=1000.0 * i,
            revenue_keur=500.0 * i,
            opex_keur=100.0 * i,
            ebitda_keur=400.0 * i,
            depreciation_keur=50.0 * i,
            tax_keur=80.0 * i,
            cf_after_tax_keur=320.0 * i,
            senior_interest_keur=30.0 * i,
            senior_principal_keur=70.0 * i,
            senior_ds_keur=100.0 * i,
            dscr=1.3 if i > 0 else 0.0,
            senior_balance_keur=10000.0 - 70.0 * i,
            tax_depreciation_audit_keur=60.0 * i,
        ))
    return _MockWaterfallResult(
        periods=periods,
        project_irr=0.08,
        equity_irr=0.12,
        avg_dscr=1.3,
        total_revenue_keur=sum(p.revenue_keur for p in periods),
    )


class TestNormalizeSnapshot:
    def test_snapshot_passes_validation(self):
        result = _make_mock_result()
        snap = normalize_snapshot(
            result,
            baseline_id="test",
            engine_designation="test_engine",
            baseline_commit_sha="abc",
            run_path_id="test.path",
            input_source_id="test.source",
        )
        validate_snapshot(snap)

    def test_period_grid_length(self):
        result = _make_mock_result(n_periods=3)
        snap = normalize_snapshot(
            result,
            baseline_id="test",
            engine_designation="test_engine",
            baseline_commit_sha="abc",
            run_path_id="test.path",
            input_source_id="test.source",
        )
        assert len(snap["period_grid"]) == 3

    def test_period_grid_sorted(self):
        result = _make_mock_result(n_periods=3)
        snap = normalize_snapshot(
            result,
            baseline_id="test",
            engine_designation="test_engine",
            baseline_commit_sha="abc",
            run_path_id="test.path",
            input_source_id="test.source",
        )
        indices = [r["period_index"] for r in snap["period_grid"]]
        assert indices == sorted(indices)

    def test_returns_project_irr(self):
        result = _make_mock_result()
        snap = normalize_snapshot(
            result,
            baseline_id="test",
            engine_designation="test_engine",
            baseline_commit_sha="abc",
            run_path_id="test.path",
            input_source_id="test.source",
        )
        assert snap["returns"]["project_irr"] == pytest.approx(0.08)

    def test_none_irr_remains_none(self):
        result = _make_mock_result()
        result.project_irr = None
        snap = normalize_snapshot(
            result,
            baseline_id="test",
            engine_designation="test_engine",
            baseline_commit_sha="abc",
            run_path_id="test.path",
            input_source_id="test.source",
        )
        assert snap["returns"]["project_irr"] is None

    def test_schema_version_set(self):
        result = _make_mock_result()
        snap = normalize_snapshot(
            result,
            baseline_id="test",
            engine_designation="test_engine",
            baseline_commit_sha="abc",
            run_path_id="test.path",
            input_source_id="test.source",
        )
        assert snap["schema_version"] == SCHEMA_VERSION

    def test_warnings_included(self):
        result = _make_mock_result()
        snap = normalize_snapshot(
            result,
            baseline_id="test",
            engine_designation="test_engine",
            baseline_commit_sha="abc",
            run_path_id="test.path",
            input_source_id="test.source",
            warnings=["test warning"],
        )
        assert "test warning" in snap["warnings"]

    def test_nan_period_value_becomes_none(self):
        result = _make_mock_result(n_periods=1)
        result.periods[0].generation_mwh = float("nan")
        snap = normalize_snapshot(
            result,
            baseline_id="test",
            engine_designation="test_engine",
            baseline_commit_sha="abc",
            run_path_id="test.path",
            input_source_id="test.source",
        )
        assert snap["operating_schedules"]["production_mwh"][0] is None

    def test_zero_not_replaced_by_none(self):
        result = _make_mock_result(n_periods=1)
        result.periods[0].generation_mwh = 0.0
        snap = normalize_snapshot(
            result,
            baseline_id="test",
            engine_designation="test_engine",
            baseline_commit_sha="abc",
            run_path_id="test.path",
            input_source_id="test.source",
        )
        assert snap["operating_schedules"]["production_mwh"][0] == 0.0
