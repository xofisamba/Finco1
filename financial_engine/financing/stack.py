"""Pure G2A funding-stack and construction draw reconciliation."""

from __future__ import annotations

from datetime import date

from finco_core.inputs import SponsorFundingMode

from financial_engine.financing.contracts import (
    ConstructionFundingPeriod,
    ConstructionFundingResult,
)


GENERIC_MVP_DRAW_POLICY = "GENERIC_MVP_SPONSOR_FIRST_LINEAR_USES"


def reconcile_financing_stack(
    *,
    total_project_uses_keur: float,
    final_senior_commitment_keur: float,
    junior_or_other_main_project_funding_keur: float,
    share_capital_keur: float,
    share_premium_keur: float,
    other_equity_funding_before_shl_keur: float,
    sponsor_funding_mode: SponsorFundingMode,
) -> tuple[float, float]:
    """Return (derived SHL cash principal, derived additional equity).

    Canonical sponsor funding stack (G2A_SHARE_PREMIUM_SOURCE_OMITTED fix):
      1. Share Capital
      2. Share Premium  <- explicitly subtracted; not silently aliased
      3. Other explicit committed equity before residual
      4. Derived residual: SHL (SHARE_CAPITAL_THEN_SHL) or additional equity (EQUITY_ONLY)

    residual = Uses - Senior - Junior - Share Capital - Share Premium - Other Committed Equity
    """
    values = (
        total_project_uses_keur,
        final_senior_commitment_keur,
        junior_or_other_main_project_funding_keur,
        share_capital_keur,
        share_premium_keur,
        other_equity_funding_before_shl_keur,
    )
    if any(value < 0.0 for value in values):
        raise ValueError("G2A funding-stack inputs must be non-negative")

    residual = (
        total_project_uses_keur
        - final_senior_commitment_keur
        - junior_or_other_main_project_funding_keur
        - share_capital_keur
        - share_premium_keur
        - other_equity_funding_before_shl_keur
    )
    if residual < -1e-8:
        raise ValueError(
            "G2A_FIXED_SOURCES_EXCEED_TOTAL_PROJECT_USES: "
            f"funding excess={-residual:.9f} kEUR"
        )
    residual = max(0.0, residual)
    if sponsor_funding_mode == SponsorFundingMode.SHARE_CAPITAL_THEN_SHL:
        return residual, 0.0
    if sponsor_funding_mode == SponsorFundingMode.EQUITY_ONLY:
        return 0.0, residual
    raise ValueError(f"Unsupported sponsor_funding_mode={sponsor_funding_mode!r}")


def build_construction_funding_schedule(
    *,
    construction_period_count: int,
    total_project_uses_keur: float,
    senior_keur: float,
    junior_keur: float,
    share_capital_keur: float,
    share_premium_keur: float,
    other_committed_equity_keur: float,
    additional_equity_keur: float,
    shl_cash_keur: float,
    shl_cash_per_period_keur: "tuple[float, ...] | None" = None,
    period_dates: "tuple[tuple[date | None, date | None, date | None], ...] | None" = None,
) -> ConstructionFundingResult:
    """Allocate linear generic uses through the documented sponsor-first waterfall.

    Waterfall order (capital-class transparency):
      Share Capital -> Share Premium -> Other Committed Equity -> Additional Equity
      -> SHL -> Junior -> Senior

    This is an explicit generic MVP audit policy, not a claim that the source
    workbook draws each facility linearly. It has no IDC or operating-model effect.
    """
    if construction_period_count <= 0:
        raise ValueError("construction_period_count must be positive")
    # BLOCKER C: validate period_dates length when provided.
    if period_dates is not None and len(period_dates) != construction_period_count:
        raise ValueError(
            f"G2A_PERIOD_DATES_LENGTH_MISMATCH: period_dates length {len(period_dates)} "
            f"!= construction_period_count {construction_period_count}"
        )
    # BLOCKER C: validate per-period SHL draws when provided.
    if shl_cash_per_period_keur is not None:
        if len(shl_cash_per_period_keur) != construction_period_count:
            raise ValueError(
                "G2A_SHL_PER_PERIOD_LENGTH_MISMATCH: shl_cash_per_period_keur length "
                f"{len(shl_cash_per_period_keur)} != construction_period_count {construction_period_count}"
            )
        if abs(sum(shl_cash_per_period_keur) - shl_cash_keur) > 1e-6:
            raise ValueError(
                "G2A_SHL_PER_PERIOD_SUM_MISMATCH: sum of per-period SHL draws "
                f"{sum(shl_cash_per_period_keur):.6f} != shl_cash_keur {shl_cash_keur:.6f}"
            )
    source_caps = {
        "share": share_capital_keur,
        "share_premium": share_premium_keur,
        "other_committed": other_committed_equity_keur,
        "additional_equity": additional_equity_keur,
        "shl": shl_cash_keur,
        "junior": junior_keur,
        "senior": senior_keur,
    }
    if abs(sum(source_caps.values()) - total_project_uses_keur) > 1e-7:
        raise ValueError("G2A_SOURCES_DO_NOT_EQUAL_USES")

    remaining = dict(source_caps)
    cumulative = {key: 0.0 for key in source_caps}
    cumulative_uses = 0.0
    rows: list[ConstructionFundingPeriod] = []
    for index in range(1, construction_period_count + 1):
        uses = (
            total_project_uses_keur / construction_period_count
            if index < construction_period_count
            else total_project_uses_keur - cumulative_uses
        )
        draws: dict[str, float] = {}
        if shl_cash_per_period_keur is not None:
            # BLOCKER C fix: SHL draw fixed per timing-resolved schedule.
            # Non-SHL sources fill remaining need in waterfall order.
            draws["shl"] = shl_cash_per_period_keur[index - 1]
            remaining["shl"] -= draws["shl"]
            cumulative["shl"] += draws["shl"]
            need = uses - draws["shl"]
            for key in ("share", "share_premium", "other_committed", "additional_equity",
                        "junior", "senior"):
                draw = min(need, remaining[key])
                draws[key] = draw
                remaining[key] -= draw
                cumulative[key] += draw
                need -= draw
        else:
            need = uses
            for key in ("share", "share_premium", "other_committed", "additional_equity",
                        "shl", "junior", "senior"):
                draw = min(need, remaining[key])
                draws[key] = draw
                remaining[key] -= draw
                cumulative[key] += draw
                need -= draw
        if abs(uses - sum(draws.values())) > 1e-8:
            raise ValueError(f"G2A_PERIOD_FUNDING_SHORTFALL: period={index}, shortfall={uses - sum(draws.values())}")

        sources = sum(draws.values())
        cumulative_uses += uses
        cumulative_sources = sum(cumulative.values())
        # BLOCKER C: populate canonical period dates when provided.
        _p_start: date | None = None
        _p_end: date | None = None
        _cf_date: date | None = None
        if period_dates is not None:
            _p_start, _p_end, _cf_date = period_dates[index - 1]
        rows.append(ConstructionFundingPeriod(
            period_index=index,
            project_cash_uses_keur=uses,
            senior_draw_keur=draws["senior"],
            junior_or_other_main_funding_draw_keur=draws["junior"],
            share_capital_draw_keur=draws["share"],
            share_premium_draw_keur=draws["share_premium"],
            other_committed_equity_draw_keur=draws["other_committed"],
            additional_equity_draw_keur=draws["additional_equity"],
            shl_cash_draw_keur=draws["shl"],
            total_sponsor_cash_draw_keur=(
                draws["share"] + draws["share_premium"] + draws["other_committed"]
                + draws["additional_equity"] + draws["shl"]
            ),
            total_sources_keur=sources,
            sources_uses_difference_keur=sources - uses,
            cumulative_project_cash_uses_keur=cumulative_uses,
            cumulative_senior_draw_keur=cumulative["senior"],
            cumulative_junior_or_other_main_funding_draw_keur=cumulative["junior"],
            cumulative_share_capital_draw_keur=cumulative["share"],
            cumulative_share_premium_draw_keur=cumulative["share_premium"],
            cumulative_other_committed_equity_draw_keur=cumulative["other_committed"],
            cumulative_additional_equity_draw_keur=cumulative["additional_equity"],
            cumulative_shl_cash_draw_keur=cumulative["shl"],
            cumulative_total_sources_keur=cumulative_sources,
            cumulative_sources_uses_difference_keur=cumulative_sources - cumulative_uses,
            period_start=_p_start,
            period_end=_p_end,
            cashflow_date=_cf_date,
        ))

    return ConstructionFundingResult(
        policy=GENERIC_MVP_DRAW_POLICY,
        periods=tuple(rows),
        maximum_period_difference_keur=max(abs(row.sources_uses_difference_keur) for row in rows),
        maximum_cumulative_difference_keur=max(
            abs(row.cumulative_sources_uses_difference_keur) for row in rows
        ),
    )
