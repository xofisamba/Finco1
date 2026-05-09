# P1 Pre-SHL Stabilization Plan

## Status

**Implemented:** P1.1 (SHL-ready fields), P1.2 (max-period alignment)
**Planned:** P1.3–P1.6 (see sections below)

## Context
Phase 3A/3B HoldCo skeleton is complete and merged to `main` via PR #4. P0 stabilization is done. Before starting the SHL (Subordinated HoldCo Loan) phase, several cleanup and improvement tasks are needed to ensure the codebase is solid.

---

## 1. SHL-Ready HoldCo Contribution Fields ✅ IMPLEMENTED

**Implemented in commits `91bdeb3` and `b7c5a82` (portfolio-stabilization-p1).**

When SHL is implemented, HoldCo will receive three types of cash flows from SPVs:
- **Dividends** — profit distribution after debt service
- **SHL interest** — interest income on the subordinated loan
- **SHL principal** — principal repayment on the subordinated loan

These should be tracked separately in `HoldCoPeriodResult` and `HoldCoSPVContribution`:

```python
@dataclass
class HoldCoSPVContribution:
    period: int
    spv_code: str
    ownership_pct: float
    # Existing
    spv_distribution_keur: float       # gross SPV distribution
    holdco_share_keur: float            # HoldCo's portion after ownership %
    # New SHL-ready fields
    dividend_keur: float = 0.0          # dividend component
    shl_interest_keur: float = 0.0     # SHL interest income
    shl_principal_keur: float = 0.0    # SHL principal repayment
```

Period-level breakdown:
```python
@dataclass
class HoldCoPeriodResult:
    period: int
    contributions: tuple[HoldCoSPVContribution, ...]
    gross_income_keur: float           # sum of holdco_share_keur
    holdco_opex_keur: float
    taxable_income_keur: float
    tax_keur: float
    distribution_to_sponsor_keur: float
    holdco_irr: Optional[float] = None  # TBD — not implementing yet
    # New
    dividend_keur: float = 0.0          # sum of dividends from all SPVs
    shl_interest_keur: float = 0.0      # sum of SHL interest
    shl_principal_keur: float = 0.0     # sum of SHL principal
```

**Implementation detail:** `dividend_keur = holdco_share` (ownership-adjusted HoldCo-level dividend inflow). SHL interest/principal remain 0.0 until SHL is implemented.

---

## 2. HoldCo Period Alignment Improvements ✅ IMPLEMENTED

**Implemented in commit `91bdeb3` (portfolio-stabilization-p1).**

Previous approach used `min()` truncation based on first SPV. Now uses `max()` with zero-padding:

- `num_periods = max(period_counts.values())` across all SPVs with waterfall data
- Shorter SPVs contribute `0.0` after their final period
- Warning says "max-period" instead of "shortest truncation"
- Longer SPVs are never truncated

```python
# P1.2: max-period alignment
num_periods = max(period_counts_by_spv.values())
# Zero-padding: period_idx >= len(spv_periods_data) → spv_dist = 0.0
```

---

## 3. Explicit Future Tax Treatment Separation

Currently tax treatment is a single `HoldCoEntity.tax_rate_pa`. When SHL arrives, three distinct tax treatments will be needed:

| Flow | Tax treatment |
|------|---------------|
| Dividends | Subject to participation exemption or standard corporate tax |
| SHL interest | Deductible at SPV level, taxable at HoldCo level |
| SHL principal | Generally not taxable (return of capital) |

**Planning notes:**
- `HoldCoEntity` needs separate tax fields or a tax allocation model
- Keep current `tax_rate_pa` as default/fallback
- New fields should be optional with sensible defaults
- Do NOT implement tax calculation logic — only field definitions

---

## 4. Future Retained Earnings Support

HoldCo may need to retain a portion of distributions for:
- Tax reserve
- Reinvestment buffer
- Contingency fund

This would add:
- `HoldCoEntity.retained_earnings_pct` — percentage of distribution to retain
- `HoldCoPeriodResult.retained_earnings_keur` — amount retained this period
- `HoldCoResult.total_retained_earnings_keur` — cumulative

**Note:** Not implementing yet. Planning only.

---

## 5. Warning System Cleanup

Current warnings are string-based and scattered. A structured warning system would help:

```python
@dataclass
class HoldCoWarning:
    code: str           # e.g., "PERIOD_MISMATCH", "OPEX_OVERRUN"
    spv_code: str       # optional
    period: int         # optional
    message: str
    severity: str       # "INFO", "WARNING", "ERROR"
```

**Scope:**
- Define `HoldCoWarning` dataclass in `result.py`
- Replace string-based warnings in `HoldCoResult.warnings` with `tuple[HoldCoWarning, ...]`
- Update `runner.py` to emit structured warnings
- Update tests to check warning codes rather than string content

**Note:** Do NOT retroactively change `SPVOutput.warnings` — only new code uses structured warnings.

---

## 6. Orchestration Cleanup Opportunities

Current `app/portfolio_orchestrator.py` wraps both independent and HoldCo paths. As the system grows:

**Potential improvements:**
1. Separate `IndependentPortfolioRunner` and `HoldCoPortfolioRunner` as distinct classes
2. Add a `PortfolioResult.to_dict()` for serialization
3. Add `PortfolioMode` validation — fail fast if HoldCo mode has no ownerships
4. Consider consolidating `PortfolioRunOutput` into a unified result type

**Note:** These are cleanup items, not new features. Keep the current functional approach.

---

## Implementation Order

1. **Field additions** (Section 1) — lowest risk, no logic changes
2. **Period alignment** (Section 2) — small targeted change
3. **Warning system** (Section 5) — additive, backward compatible
4. **Tax separation** (Section 3) — field additions, no logic
5. **Orchestration cleanup** (Section 6) — refactor, no feature changes
6. **Retained earnings** (Section 4) — optional, depends on future needs

---

## Constraints
- Do NOT implement SHL logic
- Do NOT implement tax calculation
- Do NOT add HoldCo IRR or Sponsor IRR
- Do NOT add monthly model
- Do NOT redesign pooled financing
- All changes must pass existing tests