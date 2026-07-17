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
    NonFiniteError,
    normalize_value,
    normalize_snapshot,
    _safe_float,
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


def _snap_with_period(n: int = 1) -> dict[str, Any]:
    """Minimal snapshot with n period rows and matching schedule lengths.

    Matches the real-baseline structure:
    - start_date and is_construction are None in period rows (listed in unavailable_fields)
    - financing.senior_debt.opening_keur and drawdown_keur are all-None (listed)
    - financing.shl.opening_keur is all-None (listed)
    - financing.equity.injections_keur is all-None (listed)
    - financial_statements is None → listed in unavailable_sections
    """
    snap = _minimal_snapshot()
    snap["period_grid"] = [
        {
            "period_index": idx,
            "date": f"2025-{6 * (idx + 1):02d}-30",
            "year_index": idx + 1,
            "period_in_year": 1,
            "is_operation": True,
            "start_date": None,
            "is_construction": None,
        }
        for idx in range(n)
    ]
    # Fix date for idx=0: 2025-06-30; idx=1: 2025-12-30; etc.
    # Simpler: use hardcoded dates that are valid ISO strings.
    dates = ["2025-06-30", "2025-12-31", "2026-06-30", "2026-12-31"]
    for i, row in enumerate(snap["period_grid"]):
        row["date"] = dates[i] if i < len(dates) else f"202{i+5}-06-30"

    for k in snap["operating_schedules"]:
        snap["operating_schedules"][k] = [100.0] * n
    for k in snap["tax_and_cfads"]:
        snap["tax_and_cfads"][k] = [50.0] * n

    # senior_debt: opening and drawdown are all-None (unavailable); rest are populated
    snap["financing"]["senior_debt"]["opening_keur"] = [None] * n
    snap["financing"]["senior_debt"]["drawdown_keur"] = [None] * n
    snap["financing"]["senior_debt"]["closing_keur"] = [5000.0] * n
    snap["financing"]["senior_debt"]["interest_keur"] = [50.0] * n
    snap["financing"]["senior_debt"]["principal_keur"] = [100.0] * n
    snap["financing"]["senior_debt"]["debt_service_keur"] = [150.0] * n
    snap["financing"]["senior_debt"]["dscr"] = [1.2] * n
    snap["financing"]["senior_debt"]["llcr"] = [1.4] * n
    snap["financing"]["senior_debt"]["plcr"] = [1.5] * n
    snap["financing"]["senior_debt"]["dsra_balance_keur"] = [0.0] * n
    snap["financing"]["senior_debt"]["dsra_contribution_keur"] = [0.0] * n
    snap["financing"]["senior_debt"]["cash_sweep_keur"] = [0.0] * n

    # shl: opening is all-None; rest are populated
    snap["financing"]["shl"]["opening_keur"] = [None] * n
    snap["financing"]["shl"]["interest_keur"] = [10.0] * n
    snap["financing"]["shl"]["principal_keur"] = [0.0] * n
    snap["financing"]["shl"]["service_keur"] = [10.0] * n
    snap["financing"]["shl"]["closing_keur"] = [1000.0] * n
    snap["financing"]["shl"]["pik_keur"] = [0.0] * n
    snap["financing"]["shl"]["gross_accrued_interest_keur"] = [0.0] * n

    # equity: injections is all-None; rest are populated
    snap["financing"]["equity"]["distribution_keur"] = [200.0] * n
    snap["financing"]["equity"]["injections_keur"] = [None] * n
    snap["financing"]["equity"]["cf_after_reserves_keur"] = [200.0] * n
    snap["financing"]["equity"]["lockup_active"] = [False] * n

    # unavailable_fields: all all-None series
    snap["unavailable_fields"] = {
        "financing.equity": ["injections_keur"],
        "financing.senior_debt": ["drawdown_keur", "opening_keur"],
        "financing.shl": ["opening_keur"],
        "period_grid": ["is_construction", "start_date"],
    }

    # financial_statements is None → listed in unavailable_sections
    snap["unavailable_sections"] = ["financial_statements"]
    snap["financial_statements"] = None

    snap["returns"]["project_irr"] = 0.08
    snap["returns"]["equity_irr"] = 0.12
    snap["returns"]["sponsor_irr"] = 0.10
    snap["returns"]["min_llcr"] = 1.3
    snap["returns"]["total_distribution_keur"] = 1000.0
    snap["returns"]["total_revenue_keur"] = 5000.0
    return snap


# ---------------------------------------------------------------------------
# Section A: UNAVAILABLE sentinel
# ---------------------------------------------------------------------------

class TestUnavailableSentinel:
    def test_unavailable_is_none(self):
        assert UNAVAILABLE is None

    def test_unavailable_distinct_from_zero_float(self):
        assert UNAVAILABLE != 0.0

    def test_unavailable_distinct_from_zero_int(self):
        assert UNAVAILABLE != 0

    def test_schema_version_string(self):
        assert isinstance(SCHEMA_VERSION, str)
        assert SCHEMA_VERSION == "1.0.0"


# ---------------------------------------------------------------------------
# Section B: validate_snapshot — top-level structure
# ---------------------------------------------------------------------------

class TestValidateSnapshotRequiredKeys:
    def test_valid_empty_snapshot_passes(self):
        snap = _minimal_snapshot()
        validate_snapshot(snap)

    def test_valid_snapshot_with_period_passes(self):
        snap = _snap_with_period()
        validate_snapshot(snap)

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

    def test_empty_engine_designation_raises(self):
        snap = _minimal_snapshot(engine_designation="")
        with pytest.raises(SnapshotValidationError, match="engine_designation"):
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

    @staticmethod
    def _full_period_row(period_index: int) -> dict:
        return {
            "period_index": period_index,
            "date": "2025-06-30",
            "year_index": 1,
            "period_in_year": 1,
            "is_operation": True,
            "start_date": None,
            "is_construction": None,
        }

    def test_duplicate_period_indices_raises(self):
        snap = _minimal_snapshot(period_grid=[
            self._full_period_row(0), self._full_period_row(0),
        ])
        with pytest.raises(SnapshotValidationError, match="duplicate"):
            validate_snapshot(snap)

    def test_unsorted_period_indices_raises(self):
        snap = _minimal_snapshot(period_grid=[
            self._full_period_row(1), self._full_period_row(0),
        ])
        with pytest.raises(SnapshotValidationError, match="sorted"):
            validate_snapshot(snap)

    def test_sorted_period_indices_passes(self):
        snap = _snap_with_period(n=2)
        assert snap["period_grid"][0]["period_index"] == 0
        assert snap["period_grid"][1]["period_index"] == 1
        validate_snapshot(snap)

    def test_non_finite_in_operating_schedules_raises(self):
        snap = _snap_with_period()
        snap["operating_schedules"]["revenue_keur"] = [float("nan")]
        with pytest.raises(SnapshotValidationError, match="Non-finite"):
            validate_snapshot(snap)

    def test_operating_schedules_length_mismatch_raises(self):
        snap = _snap_with_period()
        snap["operating_schedules"]["revenue_keur"] = [1.0, 2.0]
        with pytest.raises(SnapshotValidationError, match="length"):
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

    def test_missing_senior_debt_raises(self):
        snap = _minimal_snapshot()
        del snap["financing"]["senior_debt"]
        with pytest.raises(SnapshotValidationError, match="senior_debt"):
            validate_snapshot(snap)

    def test_missing_returns_raises(self):
        snap = _minimal_snapshot()
        del snap["returns"]
        with pytest.raises(SnapshotValidationError):
            validate_snapshot(snap)

    def test_returns_missing_total_distribution_keur_raises(self):
        snap = _snap_with_period()
        del snap["returns"]["total_distribution_keur"]
        with pytest.raises(SnapshotValidationError, match="total_distribution_keur"):
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

    def test_unavailable_fields_is_dict(self):
        snap = _minimal_snapshot()
        assert isinstance(snap["unavailable_fields"], dict)

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

    def test_returns_has_total_distribution_keur(self):
        snap = _minimal_snapshot()
        assert "total_distribution_keur" in snap["returns"]

    def test_returns_has_min_llcr(self):
        snap = _minimal_snapshot()
        assert "min_llcr" in snap["returns"]

    def test_financing_senior_has_llcr(self):
        snap = _minimal_snapshot()
        assert "llcr" in snap["financing"]["senior_debt"]

    def test_tax_and_cfads_has_cfads_variants(self):
        snap = _minimal_snapshot()
        tac = snap["tax_and_cfads"]
        for key in ("cf_after_tax_keur", "r69_fcf_banks_keur", "r84_fcf_junior_keur"):
            assert key in tac, f"Missing CFADS field: {key}"

    def test_distribution_key_is_singular(self):
        snap = _minimal_snapshot()
        eq = snap["financing"]["equity"]
        assert "distribution_keur" in eq
        assert "distributions_keur" not in eq


# ---------------------------------------------------------------------------
# Section D: _safe_float — strict numeric conversion
# ---------------------------------------------------------------------------

class TestSafeFloat:
    def test_int_converted(self):
        assert _safe_float(42) == 42.0

    def test_float_passes(self):
        assert _safe_float(3.14) == pytest.approx(3.14)

    def test_zero_passes(self):
        assert _safe_float(0.0) == 0.0

    # NaN and inf → NonFiniteError (subclass of NormalizationError)
    def test_nan_raises_nonfinite_error(self):
        with pytest.raises(NonFiniteError, match="NaN"):
            _safe_float(float("nan"))

    def test_nan_is_also_normalization_error(self):
        with pytest.raises(NormalizationError):
            _safe_float(float("nan"))

    def test_pos_inf_raises_nonfinite_error(self):
        with pytest.raises(NonFiniteError, match="Infinite"):
            _safe_float(float("inf"))

    def test_neg_inf_raises_nonfinite_error(self):
        with pytest.raises(NonFiniteError, match="Infinite"):
            _safe_float(float("-inf"))

    # Wrong types → NormalizationError (not NonFiniteError)
    def test_bool_raises_normalization_error_not_nonfinite(self):
        with pytest.raises(NormalizationError) as exc_info:
            _safe_float(True)
        assert not isinstance(exc_info.value, NonFiniteError)

    def test_non_numeric_string_raises_normalization_error_not_nonfinite(self):
        with pytest.raises(NormalizationError) as exc_info:
            _safe_float("not_a_number")
        assert not isinstance(exc_info.value, NonFiniteError)

    def test_none_raises_normalization_error_not_nonfinite(self):
        with pytest.raises(NormalizationError) as exc_info:
            _safe_float(None)
        assert not isinstance(exc_info.value, NonFiniteError)

    def test_list_raises_normalization_error(self):
        with pytest.raises(NormalizationError) as exc_info:
            _safe_float([1.0])
        assert not isinstance(exc_info.value, NonFiniteError)

    def test_dict_raises_normalization_error(self):
        with pytest.raises(NormalizationError) as exc_info:
            _safe_float({"v": 1.0})
        assert not isinstance(exc_info.value, NonFiniteError)

    def test_decimal_converted(self):
        assert _safe_float(float(Decimal("1.5"))) == pytest.approx(1.5)

    def test_numeric_string_succeeds(self):
        # float("3.14") is valid — numeric strings are accepted.
        assert _safe_float("3.14") == pytest.approx(3.14)


class TestGetFloatTypeSafety:
    """_get_float must absorb NonFiniteError but propagate NormalizationError (wrong types)."""

    @dataclasses.dataclass
    class _Obj:
        good: float = 1.5
        nan_val: float = float("nan")
        inf_val: float = float("inf")
        bool_val: bool = True
        list_val: list = dataclasses.field(default_factory=lambda: [1.0])

    def test_good_value_returned(self):
        from finco_parity.normalization import _get_float
        obj = self._Obj()
        assert _get_float(obj, "good", []) == pytest.approx(1.5)

    def test_nan_converted_to_unavailable_with_warning(self):
        from finco_parity.normalization import _get_float
        obj = self._Obj()
        warnings: list[str] = []
        result = _get_float(obj, "nan_val", warnings)
        assert result is None
        assert len(warnings) == 1

    def test_inf_converted_to_unavailable_with_warning(self):
        from finco_parity.normalization import _get_float
        obj = self._Obj()
        warnings: list[str] = []
        result = _get_float(obj, "inf_val", warnings)
        assert result is None
        assert len(warnings) == 1

    def test_bool_attr_raises_normalization_error(self):
        from finco_parity.normalization import _get_float
        obj = self._Obj()
        with pytest.raises(NormalizationError) as exc_info:
            _get_float(obj, "bool_val", [])
        assert not isinstance(exc_info.value, NonFiniteError)

    def test_list_attr_raises_normalization_error(self):
        from finco_parity.normalization import _get_float
        obj = self._Obj()
        with pytest.raises(NormalizationError) as exc_info:
            _get_float(obj, "list_val", [])
        assert not isinstance(exc_info.value, NonFiniteError)


# ---------------------------------------------------------------------------
# Section E: normalize_value — primitive types
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

    def test_nan_raises(self):
        with pytest.raises(NormalizationError):
            normalize_value(float("nan"))

    def test_inf_raises(self):
        with pytest.raises(NormalizationError):
            normalize_value(float("inf"))

    def test_date_to_iso(self):
        d = datetime.date(2025, 6, 15)
        assert normalize_value(d) == "2025-06-15"

    def test_datetime_to_date_iso(self):
        dt = datetime.datetime(2025, 6, 15, 12, 30, 0)
        assert normalize_value(dt) == "2025-06-15"

    def test_zero_float_preserved(self):
        assert normalize_value(0.0) == 0.0

    def test_zero_int_preserved(self):
        assert normalize_value(0) == 0


# ---------------------------------------------------------------------------
# Section F: normalize_value — containers
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
# Section G: normalize_value — enum and dataclass
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
# Section H: normalize_snapshot — mock WaterfallResult
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class _MockPeriod:
    period: int
    date: datetime.date
    year_index: int
    period_in_year: int
    is_operation: bool
    generation_mwh: float
    revenue_keur: float
    opex_keur: float
    ebitda_keur: float
    depreciation_keur: float
    taxable_profit_keur: float
    tax_keur: float
    cf_after_tax_keur: float
    senior_interest_keur: float
    senior_principal_keur: float
    senior_ds_keur: float
    dscr: float
    llcr: float
    plcr: float
    lockup_active: bool
    distribution_keur: float
    cash_sweep_keur: float
    senior_balance_keur: float
    shl_interest_keur: float = 0.0
    shl_principal_keur: float = 0.0
    shl_service_keur: float = 0.0
    shl_balance_keur: float = 0.0
    shl_pik_keur: float = 0.0
    shl_gross_accrued_interest_keur: float = 0.0
    dsra_contribution_keur: float = 0.0
    dsra_balance_keur: float = 0.0
    cf_after_reserves_keur: float = 0.0
    tax_depreciation_audit_keur: float = 0.0
    fiscal_reintegration_audit_keur: float = 0.0
    taxable_income_before_losses_audit_keur: float = 0.0
    tax_loss_opening_audit_keur: float = 0.0
    tax_loss_used_audit_keur: float = 0.0
    tax_loss_closing_audit_keur: float = 0.0
    taxable_profit_after_losses_audit_keur: float = 0.0
    cit_accrual_audit_keur: float = 0.0
    cash_tax_current_period_audit_keur: float = 0.0
    corporate_tax_cash_keur: float = 0.0
    cash_tax_bridge_reconciliation_keur: float = 0.0
    r69_fcf_banks_keur: float = 0.0
    r84_fcf_junior_keur: float = 0.0
    r99_fcf_for_distribution_keur: float = 0.0
    r102_fcf_for_shl_keur: float = 0.0
    fcf_for_shl_keur: float = 0.0


@dataclasses.dataclass
class _MockWaterfallResult:
    periods: list[_MockPeriod]
    project_irr: float = 0.0
    equity_irr: float = 0.0
    sponsor_irr: float = 0.0
    project_npv: float = 0.0
    equity_npv: float = 0.0
    avg_dscr: float = 0.0
    min_dscr: float = 0.0
    actual_avg_dscr: float = 0.0
    actual_min_dscr: float = 0.0
    min_llcr: float = 0.0
    min_plcr: float = 0.0
    periods_in_lockup: int = 0
    total_revenue_keur: float = 0.0
    total_opex_keur: float = 0.0
    total_ebitda_keur: float = 0.0
    total_tax_keur: float = 0.0
    total_senior_ds_keur: float = 0.0
    total_shl_service_keur: float = 0.0
    total_distribution_keur: float = 0.0
    equity_irr_method: str = "equity_only"


def _make_mock_result(n_periods: int = 3) -> _MockWaterfallResult:
    periods = []
    for i in range(n_periods):
        periods.append(_MockPeriod(
            period=i,
            date=datetime.date(2025 + i, 6, 30),
            year_index=i + 1,
            period_in_year=1,
            is_operation=True,
            generation_mwh=1000.0 * (i + 1),
            revenue_keur=500.0 * (i + 1),
            opex_keur=100.0 * (i + 1),
            ebitda_keur=400.0 * (i + 1),
            depreciation_keur=50.0,
            taxable_profit_keur=350.0 * (i + 1),
            tax_keur=80.0 * (i + 1),
            cf_after_tax_keur=320.0 * (i + 1),
            senior_interest_keur=30.0,
            senior_principal_keur=70.0,
            senior_ds_keur=100.0,
            dscr=1.3,
            llcr=1.5,
            plcr=2.0,
            lockup_active=False,
            distribution_keur=200.0 * (i + 1),
            cash_sweep_keur=0.0,
            senior_balance_keur=10000.0 - 70.0 * i,
        ))
    return _MockWaterfallResult(
        periods=periods,
        project_irr=0.08,
        equity_irr=0.12,
        avg_dscr=1.3,
        min_llcr=1.5,
        total_revenue_keur=sum(p.revenue_keur for p in periods),
        total_distribution_keur=sum(p.distribution_keur for p in periods),
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
            unavailable_fields={
                "financing.equity": ["injections_keur"],
                "financing.senior_debt": ["drawdown_keur", "opening_keur"],
                "financing.shl": ["opening_keur"],
                "period_grid": ["is_construction", "start_date"],
            },
            unavailable_sections=["financial_statements"],
        )
        validate_snapshot(snap)

    def test_period_grid_length(self):
        result = _make_mock_result(n_periods=3)
        snap = normalize_snapshot(
            result, baseline_id="t", engine_designation="e",
            baseline_commit_sha="x", run_path_id="r", input_source_id="i",
        )
        assert len(snap["period_grid"]) == 3

    def test_period_grid_sorted(self):
        result = _make_mock_result(n_periods=3)
        snap = normalize_snapshot(
            result, baseline_id="t", engine_designation="e",
            baseline_commit_sha="x", run_path_id="r", input_source_id="i",
        )
        indices = [r["period_index"] for r in snap["period_grid"]]
        assert indices == sorted(indices)

    def test_period_grid_captures_date(self):
        result = _make_mock_result(n_periods=1)
        snap = normalize_snapshot(
            result, baseline_id="t", engine_designation="e",
            baseline_commit_sha="x", run_path_id="r", input_source_id="i",
        )
        assert snap["period_grid"][0]["date"] == "2025-06-30"

    def test_period_grid_is_construction_unavailable(self):
        result = _make_mock_result(n_periods=1)
        snap = normalize_snapshot(
            result, baseline_id="t", engine_designation="e",
            baseline_commit_sha="x", run_path_id="r", input_source_id="i",
        )
        assert snap["period_grid"][0]["is_construction"] is None

    def test_period_grid_start_date_unavailable(self):
        result = _make_mock_result(n_periods=1)
        snap = normalize_snapshot(
            result, baseline_id="t", engine_designation="e",
            baseline_commit_sha="x", run_path_id="r", input_source_id="i",
        )
        assert snap["period_grid"][0]["start_date"] is None

    def test_returns_project_irr(self):
        result = _make_mock_result()
        snap = normalize_snapshot(
            result, baseline_id="t", engine_designation="e",
            baseline_commit_sha="x", run_path_id="r", input_source_id="i",
        )
        assert snap["returns"]["project_irr"] == pytest.approx(0.08)

    def test_returns_min_llcr(self):
        result = _make_mock_result()
        snap = normalize_snapshot(
            result, baseline_id="t", engine_designation="e",
            baseline_commit_sha="x", run_path_id="r", input_source_id="i",
        )
        assert snap["returns"]["min_llcr"] == pytest.approx(1.5)

    def test_returns_total_distribution_keur(self):
        result = _make_mock_result(n_periods=2)
        snap = normalize_snapshot(
            result, baseline_id="t", engine_designation="e",
            baseline_commit_sha="x", run_path_id="r", input_source_id="i",
        )
        # Mock has distribution_keur: 200, 400 → total=600; WaterfallResult.total_distribution_keur=600
        assert snap["returns"]["total_distribution_keur"] == pytest.approx(600.0)

    def test_distribution_key_singular(self):
        result = _make_mock_result(n_periods=1)
        snap = normalize_snapshot(
            result, baseline_id="t", engine_designation="e",
            baseline_commit_sha="x", run_path_id="r", input_source_id="i",
        )
        eq = snap["financing"]["equity"]
        assert "distribution_keur" in eq
        assert "distributions_keur" not in eq

    def test_financing_llcr_captured(self):
        result = _make_mock_result(n_periods=1)
        snap = normalize_snapshot(
            result, baseline_id="t", engine_designation="e",
            baseline_commit_sha="x", run_path_id="r", input_source_id="i",
        )
        llcr = snap["financing"]["senior_debt"]["llcr"]
        assert isinstance(llcr, list)
        assert llcr[0] == pytest.approx(1.5)

    def test_schema_version_set(self):
        result = _make_mock_result()
        snap = normalize_snapshot(
            result, baseline_id="t", engine_designation="e",
            baseline_commit_sha="x", run_path_id="r", input_source_id="i",
        )
        assert snap["schema_version"] == SCHEMA_VERSION

    def test_warnings_included(self):
        result = _make_mock_result()
        snap = normalize_snapshot(
            result, baseline_id="t", engine_designation="e",
            baseline_commit_sha="x", run_path_id="r", input_source_id="i",
            warnings=["test warning"],
        )
        assert "test warning" in snap["warnings"]

    def test_zero_preserved_not_replaced(self):
        result = _make_mock_result(n_periods=1)
        result.periods[0].generation_mwh = 0.0
        snap = normalize_snapshot(
            result, baseline_id="t", engine_designation="e",
            baseline_commit_sha="x", run_path_id="r", input_source_id="i",
        )
        assert snap["operating_schedules"]["production_mwh"][0] == 0.0

    def test_missing_attribute_yields_unavailable_series_with_warning(self):
        result = _make_mock_result(n_periods=2)
        # Remove an attribute to simulate a missing field
        delattr(result.periods[0], "generation_mwh")
        warnings: list[str] = []
        from finco_parity.normalization import normalize_operating_schedules
        op = normalize_operating_schedules(result, warnings)
        assert all(v is None for v in op["production_mwh"])
        assert any("generation_mwh" in w for w in warnings)

    def test_unavailable_fields_key_in_snapshot(self):
        result = _make_mock_result()
        snap = normalize_snapshot(
            result, baseline_id="t", engine_designation="e",
            baseline_commit_sha="x", run_path_id="r", input_source_id="i",
        )
        assert "unavailable_fields" in snap
        assert isinstance(snap["unavailable_fields"], dict)


# ---------------------------------------------------------------------------
# Section I: Negative tests for comprehensive schema validation
# ---------------------------------------------------------------------------

class TestNegativeSchemaValidation:
    """Required negative tests proving validation fails for invalid snapshots."""

    # --- tax_and_cfads ---

    def test_empty_tax_and_cfads_raises(self):
        snap = _snap_with_period()
        snap["tax_and_cfads"] = {}
        with pytest.raises(SnapshotValidationError, match="empty"):
            validate_snapshot(snap)

    def test_missing_tax_and_cfads_key_raises(self):
        snap = _snap_with_period()
        del snap["tax_and_cfads"]["cf_after_tax_keur"]
        with pytest.raises(SnapshotValidationError, match="tax_and_cfads missing"):
            validate_snapshot(snap)

    def test_tax_and_cfads_scalar_where_series_required_raises(self):
        snap = _snap_with_period()
        snap["tax_and_cfads"]["cf_after_tax_keur"] = 100.0
        with pytest.raises(SnapshotValidationError, match="list"):
            validate_snapshot(snap)

    def test_tax_and_cfads_wrong_series_length_raises(self):
        snap = _snap_with_period()
        snap["tax_and_cfads"]["cf_after_tax_keur"] = [50.0, 50.0]
        with pytest.raises(SnapshotValidationError, match="length"):
            validate_snapshot(snap)

    # --- financing sections ---

    def test_missing_financing_shl_raises(self):
        snap = _snap_with_period()
        del snap["financing"]["shl"]
        with pytest.raises(SnapshotValidationError, match="shl"):
            validate_snapshot(snap)

    def test_missing_financing_equity_raises(self):
        snap = _snap_with_period()
        del snap["financing"]["equity"]
        with pytest.raises(SnapshotValidationError, match="equity"):
            validate_snapshot(snap)

    def test_missing_senior_debt_required_field_raises(self):
        snap = _snap_with_period()
        del snap["financing"]["senior_debt"]["dscr"]
        with pytest.raises(SnapshotValidationError, match="senior_debt missing"):
            validate_snapshot(snap)

    def test_missing_shl_required_field_raises(self):
        snap = _snap_with_period()
        del snap["financing"]["shl"]["pik_keur"]
        with pytest.raises(SnapshotValidationError, match="shl missing"):
            validate_snapshot(snap)

    def test_missing_equity_required_field_raises(self):
        snap = _snap_with_period()
        del snap["financing"]["equity"]["cf_after_reserves_keur"]
        with pytest.raises(SnapshotValidationError, match="equity missing"):
            validate_snapshot(snap)

    def test_senior_debt_scalar_where_series_required_raises(self):
        snap = _snap_with_period()
        snap["financing"]["senior_debt"]["closing_keur"] = 5000.0
        with pytest.raises(SnapshotValidationError, match="list"):
            validate_snapshot(snap)

    def test_senior_debt_wrong_series_length_raises(self):
        snap = _snap_with_period()
        snap["financing"]["senior_debt"]["closing_keur"] = [5000.0, 5000.0]
        with pytest.raises(SnapshotValidationError, match="length"):
            validate_snapshot(snap)

    def test_shl_scalar_where_series_required_raises(self):
        snap = _snap_with_period()
        snap["financing"]["shl"]["closing_keur"] = 1000.0
        with pytest.raises(SnapshotValidationError, match="list"):
            validate_snapshot(snap)

    def test_equity_scalar_where_series_required_raises(self):
        snap = _snap_with_period()
        snap["financing"]["equity"]["distribution_keur"] = 200.0
        with pytest.raises(SnapshotValidationError, match="list"):
            validate_snapshot(snap)

    # --- returns ---

    def test_returns_missing_required_key_raises(self):
        snap = _snap_with_period()
        del snap["returns"]["project_npv"]
        with pytest.raises(SnapshotValidationError, match="returns missing"):
            validate_snapshot(snap)

    def test_returns_missing_equity_irr_method_raises(self):
        snap = _snap_with_period()
        del snap["returns"]["equity_irr_method"]
        with pytest.raises(SnapshotValidationError, match="returns missing"):
            validate_snapshot(snap)

    # --- unavailable_fields semantic rules ---

    def test_unknown_unavailable_section_path_raises(self):
        snap = _snap_with_period()
        snap["unavailable_fields"]["nonexistent_section"] = ["some_field"]
        with pytest.raises(SnapshotValidationError, match="unknown section path"):
            validate_snapshot(snap)

    def test_unknown_unavailable_field_raises(self):
        snap = _snap_with_period()
        snap["unavailable_fields"]["financing.senior_debt"] = [
            "drawdown_keur", "opening_keur", "nonexistent_field"
        ]
        with pytest.raises(SnapshotValidationError, match="unknown field"):
            validate_snapshot(snap)

    def test_duplicate_unavailable_field_raises(self):
        snap = _snap_with_period()
        snap["unavailable_fields"]["financing.senior_debt"] = [
            "drawdown_keur", "drawdown_keur", "opening_keur"
        ]
        with pytest.raises(SnapshotValidationError, match="duplicate"):
            validate_snapshot(snap)

    def test_unsorted_unavailable_field_list_raises(self):
        snap = _snap_with_period()
        # Reverse the order of a field list that is currently sorted
        snap["unavailable_fields"]["financing.senior_debt"] = [
            "opening_keur", "drawdown_keur"  # reversed (drawdown < opening alphabetically)
        ]
        with pytest.raises(SnapshotValidationError, match="sorted"):
            validate_snapshot(snap)

    def test_all_none_series_not_listed_in_unavailable_fields_raises(self):
        """An all-None series not listed in unavailable_fields must fail."""
        snap = _snap_with_period()
        # Make dsra_balance_keur all-None (not currently listed)
        snap["financing"]["senior_debt"]["dsra_balance_keur"] = [None]
        with pytest.raises(SnapshotValidationError, match="all-None series"):
            validate_snapshot(snap)

    def test_populated_field_listed_as_unavailable_raises(self):
        """A populated field declared unavailable must fail."""
        snap = _snap_with_period()
        # closing_keur has [5000.0] but we declare it unavailable
        snap["unavailable_fields"]["financing.senior_debt"] = [
            "closing_keur", "drawdown_keur", "opening_keur"
        ]
        with pytest.raises(SnapshotValidationError, match="non-None values"):
            validate_snapshot(snap)

    # --- period-grid row types ---

    def test_period_row_malformed_date_raises(self):
        snap = _snap_with_period()
        snap["period_grid"][0]["date"] = "30-06-2025"  # wrong format
        with pytest.raises(SnapshotValidationError, match="ISO date"):
            validate_snapshot(snap)

    def test_period_row_date_none_raises(self):
        snap = _snap_with_period()
        snap["period_grid"][0]["date"] = None
        with pytest.raises(SnapshotValidationError, match="ISO date"):
            validate_snapshot(snap)

    def test_period_row_period_index_float_raises(self):
        snap = _snap_with_period()
        snap["period_grid"][0]["period_index"] = 0.0
        with pytest.raises(SnapshotValidationError, match="integer"):
            validate_snapshot(snap)

    def test_period_row_is_operation_numeric_raises(self):
        snap = _snap_with_period()
        snap["period_grid"][0]["is_operation"] = 1  # int masquerading as bool
        with pytest.raises(SnapshotValidationError, match="bool"):
            validate_snapshot(snap)

    def test_period_row_is_construction_int_raises(self):
        snap = _snap_with_period()
        snap["period_grid"][0]["is_construction"] = 0  # int where bool or None expected
        with pytest.raises(SnapshotValidationError, match="bool or None"):
            validate_snapshot(snap)

    # --- financial_statements bidirectional consistency ---

    def test_financial_statements_none_without_unavailable_section_entry_raises(self):
        snap = _snap_with_period()
        snap["financial_statements"] = None
        snap["unavailable_sections"] = []  # missing the required entry
        with pytest.raises(SnapshotValidationError, match="unavailable_sections"):
            validate_snapshot(snap)

    def test_available_financial_statements_listed_unavailable_raises(self):
        snap = _snap_with_period()
        snap["financial_statements"] = {"pnl": {}, "balance_sheet": {}, "pf_cash_waterfall": {}}
        snap["unavailable_sections"] = ["financial_statements"]  # incorrectly listed
        with pytest.raises(SnapshotValidationError, match="unavailable_sections"):
            validate_snapshot(snap)

    def test_financial_statements_missing_pnl_raises(self):
        snap = _snap_with_period()
        snap["financial_statements"] = {"balance_sheet": {}, "pf_cash_waterfall": {}}
        snap["unavailable_sections"] = []
        with pytest.raises(SnapshotValidationError, match="pnl"):
            validate_snapshot(snap)

    def test_financial_statements_missing_balance_sheet_raises(self):
        snap = _snap_with_period()
        snap["financial_statements"] = {"pnl": {}, "pf_cash_waterfall": {}}
        snap["unavailable_sections"] = []
        with pytest.raises(SnapshotValidationError, match="balance_sheet"):
            validate_snapshot(snap)

    def test_financial_statements_available_passes(self):
        snap = _snap_with_period()
        snap["financial_statements"] = {
            "pnl": {"data": []},
            "balance_sheet": {"data": []},
            "pf_cash_waterfall": {"data": []},
        }
        snap["unavailable_sections"] = []
        validate_snapshot(snap)  # Must not raise

    # --- unavailable_sections rules ---

    def test_unavailable_sections_unknown_name_raises(self):
        snap = _snap_with_period()
        snap["unavailable_sections"] = ["financial_statements", "unknown_section"]
        with pytest.raises(SnapshotValidationError, match="unknown name"):
            validate_snapshot(snap)

    def test_unavailable_sections_duplicate_raises(self):
        snap = _snap_with_period()
        snap["unavailable_sections"] = ["financial_statements", "financial_statements"]
        with pytest.raises(SnapshotValidationError, match="duplicate"):
            validate_snapshot(snap)
