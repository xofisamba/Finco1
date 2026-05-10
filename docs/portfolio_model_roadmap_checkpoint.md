# Portfolio Model Roadmap — Checkpoint

**Last updated:** Phase 5C (2026-05-10)
**Main SHA:** e7492f4

---

## Merged Milestones

| Milestone | Phase | Key Files | Status |
|-----------|-------|-----------|--------|
| Portfolio MVP | Phase 1 | `domain/portfolio/independent/` | ✅ |
| DSRF | Phase 2 | `domain/portfolio/independent/dsrf/` | ✅ |
| HoldCo aggregation | Phase 3B | `domain/portfolio/holdco/` | ✅ |
| SHL straight-line engine | Phase 4A | `domain/portfolio/shl/` | ✅ |
| SHL upstream integration | Phase 4B | `HoldCoPeriodResult` + `shl_interest_keur`, `shl_principal_keur` fields | ✅ |
| SHL E2E enrichment | Phase 4C | `domain/portfolio/shl/integration.py` | ✅ |
| Cash ledger foundation | Phase 5A | `domain/portfolio/cash_ledger/` (inputs, result, runner, adapters) | ✅ |
| Cash ledger integration | Phase 5B | `domain/portfolio/cash_ledger/orchestrator.py` | ✅ |

---

## Current Phase

**Phase 5C** — Retained cash / distribution constraint architecture (design only)
- Branch: `portfolio-retained-cash-semantics`
- Doc: `docs/phase5c_retained_cash_distribution_constraints.md`
- Status: Design documentation — no code changes

---

## Roadmap (All Phases)

| Phase | Focus | Status |
|-------|-------|--------|
| Phase 1 | Portfolio MVP | ✅ Merged |
| Phase 2 | DSRF | ✅ Merged |
| Phase 3A | HoldCo basic aggregation | ✅ Merged |
| Phase 3B | HoldCo SHL-ready fields | ✅ Merged |
| Phase 4A | SHL straight-line engine | ✅ Merged |
| Phase 4B | HoldCo SHL-ready | ✅ Merged |
| Phase 4C | SHL E2E integration | ✅ Merged |
| Phase 5A | Cash ledger foundation | ✅ Merged |
| Phase 5B | Cash ledger integration | ✅ Merged |
| **Phase 5C** | **Retained cash/distribution constraint design** | 📐 Current |
| Phase 5D | HoldCoCashAccount implementation | Planned |
| Phase 5E | Sponsor waterfall | Planned |
| Phase 5F | Tax engine foundation | Planned |

---

## Next Steps (Upcoming)

1. **Phase 5C design review** — align on open questions before Phase 5D implementation
2. **Phase 5D.1** — data models for distribution constraints (`DistributionBlockReason`, `DistributionConstraint`, `CashAvailableForDistribution`)
3. **Phase 5D.2** — `compute_cash_available_for_distribution()` pure calculation helper
4. **Phase 5D.3** — SPV retained cash overlay (audit-only)
5. **Phase 5D.4** — HoldCo retained cash overlay (audit-only)
6. **Phase 5D.5** — optional enforcement mode

---

## Long-Running Non-Scope

The following are explicitly deferred beyond near-term phases:

- Tax engine (template-based, withholding, ATAD, transfer pricing)
- HoldCo IRR computation
- Sponsor IRR computation
- Sponsor waterfall (equity cascade tiers with multiple tranches)
- Legal dividend tests (solvency, distributable profits under local law)
- Monthly model
- Pooled financing redesign
- Refinancing logic