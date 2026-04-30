"""Period Engine: transforms financial close date into a sequence of dated periods.

This module establishes the temporal axis for all financial calculations.
It generates period metadata (start/end dates, year indices, flags) matching
the structure of the Excel CF sheets.

FincoGPT calibration note:
- When COD falls within a few days before June 30, Excel does not model a
  near-zero one-day operating stub as a full operating period.
- For Oborovo COD 2030-06-29, the first meaningful operating period in the
  extracted Excel fixture ends 2030-12-31.
"""
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import List
from dateutil.relativedelta import relativedelta
import calendar


class PeriodFrequency(Enum):
    """Frequency of periods within a year."""
    ANNUAL = 1
    SEMESTRIAL = 2
    QUARTERLY = 4


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


def _semestrial_end(from_date: date, period_in_year: int) -> date:
    """Return conventional period end date for semi-annual periods."""
    if period_in_year == 1:
        return date(from_date.year, 6, 30)
    return date(from_date.year, 12, 31)


class PeriodEngine:
    """Generates period sequence from financial close to end of horizon."""

    def __init__(
        self,
        financial_close: date,
        construction_months: int,
        horizon_years: int,
        ppa_years: int,
        frequency: PeriodFrequency = PeriodFrequency.SEMESTRIAL,
    ) -> None:
        self.fc = financial_close
        self.construction_months = construction_months
        self.horizon_years = horizon_years
        self.ppa_years = ppa_years
        self.freq = frequency
        self._cod = self._add_months(financial_close, construction_months)
        self._horizon_end = self._add_years(self._cod, horizon_years)
        self._ppa_end = self._add_years(self._cod, ppa_years)
        self._periods_per_year = frequency.value

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

    def _days_between(self, start: date, end: date) -> int:
        """Days between two dates (end - start)."""
        return (end - start).days

    def periods(self) -> List[PeriodMeta]:
        """Generate all periods from construction through horizon."""
        periods: List[PeriodMeta] = []

        # === Y0: Construction period (FC to COD) ===
        y0_h1_end = self._add_months(self.fc, 6)
        y0_h2_end = self._cod

        days_y0h1 = self._days_between(self.fc, y0_h1_end)
        y0_h1_is_leap = calendar.isleap(y0_h1_end.year)
        periods.append(PeriodMeta(
            index=0,
            start_date=self.fc,
            end_date=y0_h1_end,
            year_index=0,
            period_in_year=1,
            is_construction=True,
            is_operation=False,
            is_ppa_active=False,
            days_in_period=days_y0h1,
            day_fraction=days_y0h1 / (366.0 if y0_h1_is_leap else 365.0),
            is_leap_year=y0_h1_is_leap,
        ))

        days_y0h2 = self._days_between(y0_h1_end, y0_h2_end)
        y0_h2_is_leap = calendar.isleap(y0_h2_end.year)
        periods.append(PeriodMeta(
            index=1,
            start_date=y0_h1_end,
            end_date=y0_h2_end,
            year_index=0,
            period_in_year=2,
            is_construction=True,
            is_operation=False,
            is_ppa_active=False,
            days_in_period=days_y0h2,
            day_fraction=days_y0h2 / (366.0 if y0_h2_is_leap else 365.0),
            is_leap_year=y0_h2_is_leap,
        ))

        # === Operation periods: COD to horizon_end ===
        THRESHOLD_DAYS = 7
        current_date = self._cod

        if current_date.month <= 6:
            jun_30 = date(current_date.year, 6, 30)
        else:
            jun_30 = date(current_date.year + 1, 6, 30)
        days_to_jun_30 = (jun_30 - current_date).days

        # If COD would create a near-zero stub before June 30, Excel rolls the
        # first operating period to Dec 31. This is required for Oborovo
        # (COD 2030-06-29 → first extracted operating period 2030-12-31).
        if 0 <= days_to_jun_30 < THRESHOLD_DAYS:
            p1_end = date(current_date.year, 12, 31)
            p2_end = date(current_date.year + 1, 6, 30)
            p1_period_in_year = 1
            p2_period_in_year = 2
        else:
            if current_date.month <= 6:
                p1_end = date(current_date.year, 6, 30)
                p2_end = date(current_date.year, 12, 31)
            else:
                p1_end = date(current_date.year + 1, 6, 30)
                p2_end = date(current_date.year + 1, 12, 31)
            p1_period_in_year = 1
            p2_period_in_year = 2

        period_index = 2
        year_index = 1

        for end, pi_year in [(p1_end, p1_period_in_year), (p2_end, p2_period_in_year)]:
            if end > self._horizon_end:
                end = self._horizon_end
            days = self._days_between(current_date, end)
            ppa_active = current_date < self._ppa_end
            is_leap = calendar.isleap(end.year)
            periods.append(PeriodMeta(
                index=period_index,
                start_date=current_date,
                end_date=end,
                year_index=year_index,
                period_in_year=pi_year,
                is_construction=False,
                is_operation=True,
                is_ppa_active=ppa_active,
                days_in_period=days,
                day_fraction=days / (366.0 if is_leap else 365.0),
                is_leap_year=is_leap,
            ))
            period_index += 1
            current_date = date(end.year, end.month, end.day) + __import__('datetime').timedelta(days=1)

        year_index += 1

        while current_date < self._horizon_end:
            if current_date.month <= 6:
                h1_end = date(current_date.year, 6, 30)
                h2_end = date(current_date.year, 12, 31)
            else:
                h1_end = date(current_date.year, 12, 31)
                h2_end = date(current_date.year + 1, 6, 30)

            for h, end in [(1, h1_end), (2, h2_end)]:
                if current_date >= self._horizon_end:
                    break
                if end > self._horizon_end:
                    end = self._horizon_end
                days = self._days_between(current_date, end)
                ppa_active = current_date < self._ppa_end
                is_leap = calendar.isleap(end.year)
                periods.append(PeriodMeta(
                    index=period_index,
                    start_date=current_date,
                    end_date=end,
                    year_index=year_index,
                    period_in_year=h,
                    is_construction=False,
                    is_operation=True,
                    is_ppa_active=ppa_active,
                    days_in_period=days,
                    day_fraction=days / (366.0 if is_leap else 365.0),
                    is_leap_year=is_leap,
                ))
                period_index += 1
                current_date = date(end.year, end.month, end.day) + __import__('datetime').timedelta(days=1)

            year_index += 1

        return periods

    def operation_periods(self) -> List[PeriodMeta]:
        """Returns only operation periods (excludes construction)."""
        return [p for p in self.periods() if p.is_operation]

    def ppa_periods(self) -> List[PeriodMeta]:
        """Returns only PPA-active operation periods."""
        return [p for p in self.periods() if p.is_ppa_active]

    def period_dates(self) -> List[date]:
        """Returns end_dates for all periods."""
        return [p.end_date for p in self.periods()]


def hash_engine_for_cache(e: "PeriodEngine") -> tuple:
    """Deterministic hash for PeriodEngine inputs (for cache key)."""
    return (e.fc, e.construction_months, e.horizon_years, e.ppa_years, e.freq)
