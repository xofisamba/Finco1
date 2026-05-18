"""Depreciation engine — generates straight-line schedules per asset category."""

import warnings
from typing import Optional

from domain.depreciation_offline.config import AssetCategoryRule, DepreciationConfig
from domain.depreciation_offline.result import DepreciationScheduleEntry, DepreciationScheduleResult


class DepreciationEngine:
    """Generates straight-line depreciation schedules for configured asset categories.

    The engine is offline-only. It does not integrate with the runtime waterfall.
    """

    def __init__(self, config: DepreciationConfig):
        self.config = config

    def generate(self) -> list[DepreciationScheduleResult]:
        """Generate depreciation schedules for all configured asset categories."""
        results = []
        for category in self.config.asset_categories:
            result = self._generate_for_category(category)
            results.append(result)
        return results

    def _generate_for_category(self, category: AssetCategoryRule) -> DepreciationScheduleResult:
        """Generate a depreciation schedule for a single asset category."""
        method = category.depreciation_method
        if method not in ("straight_line", "zero_after_life"):
            raise ValueError(
                f"Unsupported depreciation method '{method}' for category '{category.category_id}'. "
                "Supported: 'straight_line', 'zero_after_life'."
            )
        return self._straight_line(category)

    def _straight_line(self, category: AssetCategoryRule) -> DepreciationScheduleResult:
        """Generate a straight-line (zero-after-life) depreciation schedule."""
        if category.residual_value_keur > category.capex_amount_keur:
            raise ValueError(
                f"residual_value ({category.residual_value_keur}) cannot exceed "
                f"capex_amount ({category.capex_amount_keur}) for category '{category.category_id}'."
            )

        depreciable = category.depreciable_basis_keur()
        total_periods = category.useful_life_periods()
        active_end = category.start_period + total_periods  # exclusive

        # If end_period is explicitly provided, cap at that
        if category.end_period is not None:
            active_end = min(active_end, category.end_period + 1)

        if depreciable <= 0:
            # Non-depreciable asset — all zero
            entries = [
                DepreciationScheduleEntry(
                    period_index=i,
                    book_depreciation_keur=0.0,
                    tax_depreciation_keur=0.0,
                    cumulative_book_keur=0.0,
                    cumulative_tax_keur=0.0,
                    remaining_book_basis_keur=category.capex_amount_keur,
                    remaining_tax_basis_keur=category.capex_amount_keur,
                    is_zero_after_life=True,
                )
                for i in range(self.config.period_count)
            ]
            return DepreciationScheduleResult(
                category_id=category.category_id,
                entries=entries,
                total_book_depreciation_keur=0.0,
                total_tax_depreciation_keur=0.0,
                frequency=category.frequency,
            )

        # Per-period amount
        active_period_count = max(0, active_end - category.start_period)
        if active_period_count == 0:
            period_amount = 0.0
        else:
            period_amount = depreciable / active_period_count

        # Fallback warning
        if (
            self.config.fallback_warning_enabled
            and category.category_id == "other"
            and category.useful_life_years == 30
        ):
            warnings.warn(
                "DepreciationWarning: Category 'other' using 30-year fallback "
                "useful life. Set explicit useful_life_years from project inputs to silence.",
                DeprecationWarning,
                stacklevel=2,
            )

        entries: list[DepreciationScheduleEntry] = []
        cumulative_book = 0.0
        cumulative_tax = 0.0

        for i in range(self.config.period_count):
            if i < category.start_period or i >= active_end:
                # Before start or after useful life ends
                book_dep = 0.0
                is_zero = True
            else:
                book_dep = period_amount
                is_zero = False

            cumulative_book += book_dep
            remaining_book = max(category.residual_value_keur, category.capex_amount_keur - cumulative_book)
            remaining_tax = remaining_book  # Simplified: same as book for now

            entries.append(
                DepreciationScheduleEntry(
                    period_index=i,
                    book_depreciation_keur=book_dep,
                    tax_depreciation_keur=book_dep,  # Simplified: tax = book for now
                    cumulative_book_keur=cumulative_book,
                    cumulative_tax_keur=cumulative_book,
                    remaining_book_basis_keur=remaining_book,
                    remaining_tax_basis_keur=remaining_tax,
                    is_zero_after_life=is_zero,
                )
            )

        return DepreciationScheduleResult(
            category_id=category.category_id,
            entries=entries,
            total_book_depreciation_keur=cumulative_book,
            total_tax_depreciation_keur=cumulative_book,
            frequency=category.frequency,
        )


def aggregate(results: list[DepreciationScheduleResult]) -> DepreciationScheduleResult:
    """Sum book depreciation across multiple category results.

    Returns a DepreciationScheduleResult where each entry's book_depreciation_keur
    is the sum across all input results, and tax_depreciation_keur is taken from the
    first result that has a non-zero tax value.

    Note: this is a simple sum; callers needing more sophisticated aggregation
    (e.g. separate book/tax totals) should build custom aggregation.
    """
    if not results:
        raise ValueError("aggregate() requires at least one result")
    if len(results) == 1:
        return results[0]

    # Build a map of period_index → combined book depreciation
    from collections import defaultdict

    book_by_period: dict[int, float] = defaultdict(float)
    tax_by_period: dict[int, float] = {}
    cum_book_by_period: dict[int, float] = {}
    cum_tax_by_period: dict[int, float] = {}
    rem_book_by_period: dict[int, float] = {}
    rem_tax_by_period: dict[int, float] = {}
    zero_by_period: dict[int, bool] = {}
    first_entries = {r.entries[0].period_index: r for r in results}

    for result in results:
        for entry in result.entries:
            idx = entry.period_index
            book_by_period[idx] += entry.book_depreciation_keur
            if idx not in tax_by_period and entry.tax_depreciation_keur != 0.0:
                tax_by_period[idx] = entry.tax_depreciation_keur
            # For cumulative/remaining, use the first result's values
            if idx not in cum_book_by_period:
                cum_book_by_period[idx] = entry.cumulative_book_keur
                cum_tax_by_period[idx] = entry.cumulative_tax_keur
                rem_book_by_period[idx] = entry.remaining_book_basis_keur
                rem_tax_by_period[idx] = entry.remaining_tax_basis_keur
                zero_by_period[idx] = entry.is_zero_after_life

    all_indices = sorted(book_by_period.keys())
    entries = [
        DepreciationScheduleEntry(
            period_index=idx,
            book_depreciation_keur=book_by_period[idx],
            tax_depreciation_keur=tax_by_period.get(idx, 0.0),
            cumulative_book_keur=cum_book_by_period[idx],
            cumulative_tax_keur=cum_tax_by_period[idx],
            remaining_book_basis_keur=rem_book_by_period[idx],
            remaining_tax_basis_keur=rem_tax_by_period[idx],
            is_zero_after_life=zero_by_period[idx],
        )
        for idx in all_indices
    ]

    total_book = sum(r.total_book_depreciation_keur for r in results)
    total_tax = sum(r.total_tax_depreciation_keur for r in results)

    return DepreciationScheduleResult(
        category_id="aggregate",
        entries=entries,
        total_book_depreciation_keur=total_book,
        total_tax_depreciation_keur=total_tax,
        frequency=results[0].frequency,
    )