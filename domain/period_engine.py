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

        # === Operation periods ===
        current_date = self._last_semiannual_end_on_or_after_cod()
        period_index = 2
        year_index = 1
        period_in_year = 1

        while current_date < self._horizon_end:
            end = self._next_semiannual_end_after(current_date)
            if end > self._horizon_end:
                end = self._horizon_end
            days = self._days_between(current_date, end)
            if days <= 0:
                break

            ppa_active = current_date < self._ppa_end
            is_leap = calendar.isleap(end.year)
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
                day_fraction=days / (366.0 if is_leap else 365.0),
                is_leap_year=is_leap,
            ))

            period_index += 1
            current_date = end
            if period_in_year == 1:
                period_in_year = 2
            else:
                period_in_year = 1
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
