"""Period Engine: transforms financial close date into a sequence of dated periods.

This module establishes the temporal axis for all financial calculations.
It generates period metadata (start/end dates, year indices, flags) matching
the structure of the Excel CF sheets.

FincoGPT calibration note:
- Excel semi-annual models use period-end to period-end day counts for operating
  rows, not inclusive calendar-day counts.
- Near-zero COD stubs at June 30 / Dec 31 are rolled into the next meaningful
  operating period.
- Oborovo COD 2030-06-29 therefore produces first operating period ending
  2030-12-31 with 184 days (2030-06-30 to 2030-12-31).
"""
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any, List, Sequence
from dateutil.relativedelta import relativedelta
import calendar


class PeriodFrequency(Enum):
    """Frequency of periods within a year."""
    ANNUAL = 1
    SEMESTRIAL = 2
    QUARTERLY = 4


class PeriodAxisConvention(str, Enum):
    """Explicit policy for construction and operating-period boundary semantics."""
    COD_ANCHOR_TWO_CONSTRUCTION_COLUMNS = "cod_anchor_two_construction_columns"
    OPERATING_BOUNDARY_SINGLE_CONSTRUCTION_COLUMN = "operating_boundary_single_construction_column"


@dataclass(frozen=True)
class PeriodMeta:
    """Immutable metadata for a single period."""
    index: int
    start_date: date
    end_date: date
    year_index: int
    period_in_year: int
    is_construction: bool
    is_operation: bool
    is_ppa_active: bool
    days_in_period: int
    day_fraction: float
    is_leap_year: bool
    # Derived operating-period counters. Construction periods keep defaults.
    operating_period_index: int = -1
    operating_year_index: int = 0


class PeriodEngine:
    """Generates period sequence from financial close to end of horizon."""

    def __init__(
        self,
        financial_close: date,
        construction_months: int,
        horizon_years: int,
        ppa_years: int,
        frequency: PeriodFrequency = PeriodFrequency.SEMESTRIAL,
        cod_date: date | None = None,
        period_axis_convention: PeriodAxisConvention | str = (
            PeriodAxisConvention.COD_ANCHOR_TWO_CONSTRUCTION_COLUMNS
        ),
    ) -> None:
        self.fc = financial_close
        self.construction_months = construction_months
        self.horizon_years = horizon_years
        self.ppa_years = ppa_years
        self.freq = self._coerce_frequency(frequency)
        self.period_axis_convention = self._coerce_period_axis_convention(
            period_axis_convention
        )
        derived_cod = self._add_months(financial_close, construction_months)
        if cod_date is not None and cod_date != derived_cod:
            raise ValueError(
                "PERIOD_AXIS_COD_MISMATCH: explicit cod_date "
                f"{cod_date.isoformat()} != financial_close + construction_months "
                f"{derived_cod.isoformat()}"
            )
        self._cod = cod_date or derived_cod
        self._operating_start = self._last_semiannual_end_on_or_after_cod()
        self._periods_per_year = self.freq.value
        if self.freq != PeriodFrequency.SEMESTRIAL:
            raise ValueError(
                "PERIOD_AXIS_FREQUENCY_UNSUPPORTED: canonical runtime axis currently "
                "requires SEMESTRIAL frequency"
            )
        if isinstance(horizon_years, bool) or int(horizon_years) != horizon_years or horizon_years <= 0:
            raise ValueError("PERIOD_AXIS_HORIZON_INVALID: horizon_years must be a positive integer")
        if ppa_years < 0:
            raise ValueError("PERIOD_AXIS_PPA_TERM_INVALID: ppa_years must be >= 0")
        self._operating_period_count = int(horizon_years) * self._periods_per_year
        ppa_anchor = (
            self._operating_start
            if self.period_axis_convention
            == PeriodAxisConvention.OPERATING_BOUNDARY_SINGLE_CONSTRUCTION_COLUMN
            else self._cod
        )
        self._ppa_end = self._add_years(ppa_anchor, ppa_years)
        self._periods = self._build_periods()
        validate_canonical_period_axis(
            self._periods,
            expected_operating_periods=self._operating_period_count,
        )
        self._horizon_end = self._periods[-1].end_date

    @property
    def cod(self) -> date:
        """Commercial Operation Date (end of construction)."""
        return self._cod

    @property
    def ppa_end(self) -> date:
        """End date of PPA tariff period."""
        return self._ppa_end

    @property
    def horizon_end(self) -> date:
        """End of investment horizon."""
        return self._horizon_end

    def _add_months(self, d: date, months: int) -> date:
        """Add months to a date."""
        return d + relativedelta(months=months)

    def _add_years(self, d: date, years: float) -> date:
        """Add years (int or float) to a date. Supports fractional years like 12.5."""
        if isinstance(years, float) and not years.is_integer():
            whole = int(years)
            months = int((years - whole) * 12)
            return d + relativedelta(years=whole, months=months)
        return d + relativedelta(years=int(years))

    def _coerce_period_axis_convention(
        self,
        value: PeriodAxisConvention | str,
    ) -> PeriodAxisConvention:
        """Resolve explicit period-axis policy values."""
        if isinstance(value, PeriodAxisConvention):
            return value
        try:
            return PeriodAxisConvention(str(value))
        except ValueError as exc:
            allowed = ", ".join(v.value for v in PeriodAxisConvention)
            raise ValueError(
                f"Unknown period_axis_convention={value!r}; expected one of: {allowed}"
            ) from exc

    def _coerce_frequency(self, value: object) -> PeriodFrequency:
        """Accept the typed input enum without weakening supported frequencies."""
        if isinstance(value, PeriodFrequency):
            return value
        member_name = getattr(value, "name", None)
        if isinstance(member_name, str) and member_name in PeriodFrequency.__members__:
            return PeriodFrequency[member_name]
        try:
            return PeriodFrequency(value)  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise ValueError(f"PERIOD_AXIS_FREQUENCY_INVALID: {value!r}") from exc

    def _days_between(self, start: date, end: date) -> int:
        """Days between two period-boundary dates (end - start)."""
        return (end - start).days

    def _next_semiannual_end_after(self, d: date) -> date:
        """Return the next June 30 / Dec 31 date strictly after d."""
        jun_30 = date(d.year, 6, 30)
        dec_31 = date(d.year, 12, 31)
        if d < jun_30:
            return jun_30
        if d < dec_31:
            return dec_31
        return date(d.year + 1, 6, 30)

    def _last_semiannual_end_on_or_after_cod(self, threshold_days: int = 7) -> date:
        """Return starting boundary for first meaningful operating period.

        Excel rolls very short COD-to-period-end stubs into the next full-ish
        operating period. The start boundary is the nearby semi-annual end date
        when COD is within threshold days before it; otherwise COD itself.
        """
        if self._cod.month <= 6:
            boundary = date(self._cod.year, 6, 30)
        else:
            boundary = date(self._cod.year, 12, 31)
        days_to_boundary = (boundary - self._cod).days
        if 0 <= days_to_boundary < threshold_days:
            return boundary
        return self._cod

    def _semiannual_operating_denominator(self, period_end: date) -> float:
        """Source workbook denominator for semiannual operating periods."""
        if period_end.month == 6:
            return 366.0 if calendar.isleap(period_end.year) else 365.0
        if period_end.month == 12:
            next_year = period_end.year + 1
            return 366.0 if calendar.isleap(next_year) else 365.0
        return 366.0 if calendar.isleap(period_end.year) else 365.0

    def periods(self) -> tuple[PeriodMeta, ...]:
        """Return the immutable canonical construction and operating axis."""
        return self._periods

    def _build_periods(self) -> tuple[PeriodMeta, ...]:
        if self.period_axis_convention == PeriodAxisConvention.OPERATING_BOUNDARY_SINGLE_CONSTRUCTION_COLUMN:
            return self._source_aligned_operating_boundary_periods()
        return self._cod_anchor_two_construction_column_periods()

    def _source_aligned_operating_boundary_periods(self) -> tuple[PeriodMeta, ...]:
        """Generate source-aligned periods with one construction column."""
        periods: List[PeriodMeta] = []

        # === Y0: Construction period (FC to operating boundary) ===
        #
        # Source workbooks expose one pre-operating model column, followed by
        # operating periods that start on the semiannual boundary on or just
        # after COD. Splitting construction into two semiannual columns creates
        # an extra non-source period and shifts Base CFADS, senior debt service,
        # and SHL cash one period downstream.
        construction_end = self._operating_start
        days_y0 = self._days_between(self.fc, construction_end)
        y0_is_leap = calendar.isleap(construction_end.year)
        periods.append(PeriodMeta(
            index=0,
            start_date=self.fc,
            end_date=construction_end,
            year_index=0,
            period_in_year=1,
            is_construction=True,
            is_operation=False,
            is_ppa_active=False,
            days_in_period=days_y0,
            day_fraction=days_y0 / (366.0 if y0_is_leap else 365.0),
            is_leap_year=y0_is_leap,
        ))

        # === Operation periods ===
        current_date = construction_end
        period_index = 1
        year_index = 1
        period_in_year = 1
        operating_period_index = 0
        operating_year_index = 1

        while operating_period_index < self._operating_period_count:
            end = self._next_semiannual_end_after(current_date)
            days = self._days_between(current_date, end)
            if current_date == self._cod and current_date.day == 1:
                days += 1
            ppa_active = current_date < self._ppa_end
            denominator = self._semiannual_operating_denominator(end)
            is_leap = denominator == 366.0
            periods.append(PeriodMeta(
                index=period_index,
                start_date=current_date,
                end_date=end,
                year_index=year_index,
                period_in_year=period_in_year,
                is_construction=False,
                is_operation=True,
                is_ppa_active=ppa_active,
                days_in_period=days,
                day_fraction=days / denominator,
                is_leap_year=is_leap,
                operating_period_index=operating_period_index,
                operating_year_index=operating_year_index,
            ))

            period_index += 1
            current_date = end
            if period_in_year == 1:
                period_in_year = 2
            else:
                period_in_year = 1
                year_index += 1
                operating_year_index += 1
            operating_period_index += 1

        return tuple(periods)

    def _cod_anchor_two_construction_column_periods(self) -> tuple[PeriodMeta, ...]:
        """Generate meaningful six-month construction segments and operation."""
        periods: List[PeriodMeta] = []

        construction_start = self.fc
        construction_index = 0
        while construction_start < self._operating_start:
            candidate = self._add_months(construction_start, 6)
            # Fold a near-boundary remainder into the current meaningful segment.
            if candidate >= self._operating_start or (
                self._operating_start - candidate
            ).days < 7:
                construction_end = self._operating_start
            else:
                construction_end = candidate
            days = self._days_between(construction_start, construction_end)
            is_leap = calendar.isleap(construction_end.year)
            periods.append(PeriodMeta(
                index=construction_index,
                start_date=construction_start,
                end_date=construction_end,
                year_index=0,
                period_in_year=(construction_index % 2) + 1,
                is_construction=True,
                is_operation=False,
                is_ppa_active=False,
                days_in_period=days,
                day_fraction=days / (366.0 if is_leap else 365.0),
                is_leap_year=is_leap,
            ))
            construction_index += 1
            construction_start = construction_end

        # === Operation periods ===
        current_date = self._last_semiannual_end_on_or_after_cod()
        period_index = construction_index
        year_index = 1
        period_in_year = 1
        operating_period_index = 0
        operating_year_index = 1

        while operating_period_index < self._operating_period_count:
            end = self._next_semiannual_end_after(current_date)
            days = self._days_between(current_date, end)
            if current_date == self._cod and current_date.day == 1:
                days += 1
            ppa_active = current_date < self._ppa_end
            is_leap = calendar.isleap(end.year)
            denominator = 366.0 if is_leap else 365.0
            periods.append(PeriodMeta(
                index=period_index,
                start_date=current_date,
                end_date=end,
                year_index=year_index,
                period_in_year=period_in_year,
                is_construction=False,
                is_operation=True,
                is_ppa_active=ppa_active,
                days_in_period=days,
                day_fraction=days / denominator,
                is_leap_year=is_leap,
                operating_period_index=operating_period_index,
                operating_year_index=operating_year_index,
            ))

            period_index += 1
            current_date = end
            if period_in_year == 1:
                period_in_year = 2
            else:
                period_in_year = 1
                year_index += 1
                operating_year_index += 1
            operating_period_index += 1

        return tuple(periods)

    def operation_periods(self) -> tuple[PeriodMeta, ...]:
        """Returns only operation periods (excludes construction)."""
        return tuple(p for p in self.periods() if p.is_operation)

    def ppa_periods(self) -> tuple[PeriodMeta, ...]:
        """Returns only PPA-active operation periods."""
        return tuple(p for p in self.periods() if p.is_ppa_active)

    def period_dates(self) -> tuple[date, ...]:
        """Returns end_dates for all periods."""
        return tuple(p.end_date for p in self.periods())


def validate_canonical_period_axis(
    periods: Sequence[PeriodMeta],
    *,
    expected_operating_periods: int | None = None,
) -> None:
    """Fail closed when a consumer receives a malformed financial axis.

    Checks (in order):
      1.  Axis is non-empty.
      2.  Indices are unique and form 0-based contiguous range.
      3.  Per-period: positive duration, mutually exclusive phase flags,
          date continuity, finite+positive day_fraction,
          days_in_period consistent with date span.
      4.  Construction periods form one contiguous prefix (no construction
          after operation begins).
      5.  Operating periods form one contiguous suffix.
      6.  Operating period counters are coherent (operating_period_index,
          operating_year_index, period_in_year).
      7.  Operating count equals expected_operating_periods when supplied.
      8.  Operating sequential indices are 0-based and contiguous.
      9.  Final operating period has more than one day (no terminal one-day stub).
    """
    import math as _math

    if not periods:
        raise ValueError("PERIOD_AXIS_EMPTY")
    indices = tuple(p.index for p in periods)
    if len(set(indices)) != len(indices):
        raise ValueError("PERIOD_AXIS_DUPLICATE_INDICES")
    if indices != tuple(range(len(periods))):
        raise ValueError("PERIOD_AXIS_NON_CONTIGUOUS_OR_OUT_OF_ORDER")

    operation_started = False
    for position, period in enumerate(periods):
        # 3a. positive duration
        if period.days_in_period <= 0 or period.end_date <= period.start_date:
            raise ValueError(
                f"PERIOD_AXIS_NON_POSITIVE_DURATION: period_index={period.index}"
            )
        # 3b. mutually exclusive phase flags
        if period.is_construction == period.is_operation:
            raise ValueError(
                f"PERIOD_AXIS_PHASE_FLAGS_INVALID: period_index={period.index}"
            )
        # 3c. date continuity
        if position and period.start_date != periods[position - 1].end_date:
            raise ValueError(
                f"PERIOD_AXIS_GAP_OR_OVERLAP: period_index={period.index}"
            )
        # 3d. day_fraction finite and positive
        if not _math.isfinite(period.day_fraction) or period.day_fraction <= 0.0:
            raise ValueError(
                f"PERIOD_AXIS_DAY_FRACTION_INVALID: period_index={period.index} "
                f"day_fraction={period.day_fraction!r}"
            )
        # 3e. days_in_period consistent with date span (allow +1 for COD-on-month-start)
        calendar_days = (period.end_date - period.start_date).days
        if period.days_in_period not in (calendar_days, calendar_days + 1):
            raise ValueError(
                f"PERIOD_AXIS_DAYS_IN_PERIOD_MISMATCH: period_index={period.index} "
                f"days_in_period={period.days_in_period} calendar_days={calendar_days}"
            )
        # 4. no construction after operation begins
        if period.is_operation:
            operation_started = True
        elif operation_started and period.is_construction:
            raise ValueError(
                f"PERIOD_AXIS_CONSTRUCTION_AFTER_OPERATION: period_index={period.index}"
            )

    # 5. operating periods form contiguous suffix (already implied by 4, but verify)
    construction = tuple(p for p in periods if p.is_construction)
    operating = tuple(p for p in periods if p.is_operation)
    if construction and operating:
        if construction[-1].index >= operating[0].index:
            raise ValueError(
                "PERIOD_AXIS_PHASE_ORDER_INVALID: construction and operating overlap"
            )

    # 6. operating period counters coherent
    for op_pos, op in enumerate(operating):
        if op.operating_period_index != op_pos:
            raise ValueError(
                f"PERIOD_AXIS_OPERATING_INDICES_INVALID: period_index={op.index} "
                f"expected_op_idx={op_pos} actual={op.operating_period_index}"
            )
        expected_year = op_pos // 2 + 1
        expected_pip = op_pos % 2 + 1
        if op.operating_year_index != expected_year:
            raise ValueError(
                f"PERIOD_AXIS_OPERATING_YEAR_INDEX_INVALID: period_index={op.index} "
                f"expected={expected_year} actual={op.operating_year_index}"
            )
        if op.period_in_year != expected_pip:
            raise ValueError(
                f"PERIOD_AXIS_PERIOD_IN_YEAR_INVALID: period_index={op.index} "
                f"expected={expected_pip} actual={op.period_in_year}"
            )

    # 7. operating count check
    if expected_operating_periods is not None and len(operating) != expected_operating_periods:
        raise ValueError(
            "PERIOD_AXIS_OPERATING_COUNT_MISMATCH: "
            f"expected={expected_operating_periods}, actual={len(operating)}"
        )

    # 8. operating sequential indices (already validated above via 6)

    # 9. no terminal one-day stub in operating periods
    if operating and operating[-1].days_in_period <= 1:
        raise ValueError(
            f"PERIOD_AXIS_TERMINAL_STUB: final operating period has "
            f"days_in_period={operating[-1].days_in_period}"
        )


def map_period_vector(
    period_indices: Sequence[int],
    values: Sequence[Any],
    *,
    label: str,
    expected_indices: tuple[int, ...] | None = None,
) -> dict[int, Any]:
    """Map an axis-aligned vector without truncation, overwrite, or reordering.

    When ``expected_indices`` is provided (the independently-derived canonical
    axis), this function compares the supplied ``period_indices`` against it
    using an exact immutable tuple comparison BEFORE any dict construction.
    This catches missing, extra, shifted, and reordered periods that would
    otherwise be silently swallowed by the dict.

    Error codes:
      AXIS_PERIOD_DUPLICATE  — duplicate raw indices in the supplied vector
      AXIS_LENGTH_MISMATCH   — len(period_indices) != len(expected_indices)
      AXIS_PERIOD_MISSING    — expected index absent from supplied indices
      AXIS_PERIOD_EXTRA      — supplied index not in expected_indices
      AXIS_PERIOD_SHIFTED    — indices match as a set but are offset/reordered
      PERIOD_VECTOR_LENGTH_MISMATCH — len(period_indices) != len(values)
      PERIOD_VECTOR_DUPLICATE_INDICES — duplicate raw indices (no expected given)
      PERIOD_VECTOR_OUT_OF_ORDER     — not strictly increasing (no expected given)
    """
    indices = tuple(period_indices)
    vector = tuple(values)

    # --- Step 1: duplicate check (must fire before anything else) ---
    if len(set(indices)) != len(indices):
        raise ValueError(f"AXIS_PERIOD_DUPLICATE: {label}")

    # --- Step 2: exact-axis membership check (authoritative comparison) ---
    if expected_indices is not None:
        expected = tuple(expected_indices)
        if len(indices) != len(expected):
            supplied_set = set(indices)
            expected_set = set(expected)
            missing = expected_set - supplied_set
            extra = supplied_set - expected_set
            if missing and not extra:
                raise ValueError(
                    f"AXIS_PERIOD_MISSING: {label} missing={sorted(missing)}"
                )
            if extra and not missing:
                raise ValueError(
                    f"AXIS_PERIOD_EXTRA: {label} extra={sorted(extra)}"
                )
            raise ValueError(
                f"AXIS_LENGTH_MISMATCH: {label} "
                f"expected={len(expected)} supplied={len(indices)}"
            )
        if indices != expected:
            supplied_set = set(indices)
            expected_set = set(expected)
            missing = expected_set - supplied_set
            extra = supplied_set - expected_set
            if missing:
                raise ValueError(
                    f"AXIS_PERIOD_MISSING: {label} missing={sorted(missing)}"
                )
            if extra:
                raise ValueError(
                    f"AXIS_PERIOD_EXTRA: {label} extra={sorted(extra)}"
                )
            # same set, wrong order/offset within same length — shifted or reordered
            raise ValueError(
                f"AXIS_PERIOD_SHIFTED: {label} "
                f"expected={expected} supplied={indices}"
            )

    # --- Step 3: parallel-vector length check ---
    if len(indices) != len(vector):
        raise ValueError(
            f"PERIOD_VECTOR_LENGTH_MISMATCH: {label} indices={len(indices)} "
            f"values={len(vector)}"
        )

    # --- Step 4: order check (when no expected_indices provided) ---
    if expected_indices is None:
        if any(curr <= prev for prev, curr in zip(indices, indices[1:])):
            raise ValueError(f"PERIOD_VECTOR_OUT_OF_ORDER: {label}")

    return {idx: vector[position] for position, idx in enumerate(indices)}


def hash_engine_for_cache(e: "PeriodEngine") -> tuple:
    """Deterministic hash for PeriodEngine inputs (for cache key)."""
    return (
        e.fc,
        e.construction_months,
        e.horizon_years,
        e.ppa_years,
        e.freq,
        e.cod,
        e.period_axis_convention.value,
    )
