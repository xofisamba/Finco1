# WaterfallPeriod Mutability Policy

**Scope:** `domain/waterfall/` — `WaterfallPeriod` dataclass
**Status:** Mutable by design — see rationale below

---

## Current Design

`WaterfallPeriod` is a plain `@dataclass` (not frozen). It is mutable by design, as an architectural trade-off made during Phase 4C SHL integration. This document records that decision and its implications.

---

## Why WaterfallPeriod is Mutable

### Phase 4C SHL Enrichment Bridge

After the base waterfall is computed for an SPV, Phase 4C needs to annotate each waterfall period with SHL interest and principal flows that originate at the portfolio level (not the SPV level). The cleanest integration bridge without broader architectural changes is to write those values directly onto the period objects after the waterfall has run.

```python
# domain/portfolio/shl/integration.py
def inject_shl_into_waterfall_periods(wf_periods, shl_lookup):
    for p in wf_periods:
        p.shl_interest_keur = float(interest)   # mutation
        p.shl_principal_keur = float(principal)  # mutation
```

The alternative — returning an enriched copy, or threading an enrichment context through the waterfall — would require changes to the waterfall engine itself and to all callers. That refactor is deferred.

### DSRF-Adjusted Distributions (Phase 2)

DSRF-adjusted distributions are kept in a separate field `SPVOutput.adjusted_period_distributions_keur`. This field is set by the DSRF runner and read by HoldCo. It does **not** mutate `waterfall_result.periods[].distribution_keur`. This separation means the base waterfall result is never modified by DSRF.

---

## Current Enrichment-Writable Fields

The following fields on `WaterfallPeriod` may be written by enrichment hooks (not by the base waterfall engine itself):

| Field | Written by | Phase |
|---|---|---|
| `shl_interest_keur` | `inject_shl_into_waterfall_periods()` | Phase 4C |
| `shl_principal_keur` | `inject_shl_into_waterfall_periods()` | Phase 4C |

No other fields are written by enrichment hooks. The base waterfall engine only reads and writes its own result fields.

---

## Collision Policy

When an enrichment hook writes to a waterfall period, it must not silently overwrite values that were already set by another enrichment pass or by the SPV-level waterfall engine.

**Current policy (enforced since Phase 4C SHL guard, PR #13):**

For each `WaterfallPeriod` field that is written by enrichment:
- If the existing value is `> 0` and the incoming value is `> 0` → raise `ValueError` (explicit collision — caller must resolve)
- If the incoming value is `> 0` and existing is `== 0` → set incoming value
- If the incoming value is `== 0` and existing is `> 0` → preserve existing value (do not overwrite with 0)
- Both `== 0` → set to `0.0`

This applies to `shl_interest_keur` and `shl_principal_keur` in `inject_shl_into_waterfall_periods()`.

---

## Why an Immutable Refactor is Deferred

Changing `WaterfallPeriod` to `@dataclass(frozen=True)` would require:

1. Replacing all in-place mutations (`p.shl_interest_keur = x`) with `replace()` calls throughout the integration layer
2. Updating all callers that rely on waterfall period object identity (e.g., `id(p)` comparisons, if any)
3. Potentially updating downstream consumers (HoldCo runner, cash ledger adapters) that read from these objects
4. A broader review to ensure no caller depends on mutation behavior

This refactor is a future cleanup sprint item. It does not block Phase 5D or any subsequent phase because:

- The mutation is **isolated to one integration function** (`inject_shl_into_waterfall_periods`)
- That function is fully tested with collision guards
- Phase 5D retained cash logic will write to its **own** result objects (new dataclasses), not to `WaterfallPeriod` directly

---

## Future Direction

Two possible paths for a future immutable cleanup:

### Option A — `replace()` Based Enrichment

```python
def enrich_period(p: WaterfallPeriod, interest, principal) -> WaterfallPeriod:
    return replace(p,
        shl_interest_keur=float(interest),
        shl_principal_keur=float(principal),
    )
```

Cleaner but requires callers to use the returned object.

### Option B — Explicit `EnrichedWaterfallPeriod`

```python
@dataclass(frozen=True)
class EnrichedWaterfallPeriod:
    base: WaterfallPeriod        # original immutable copy
    shl_interest_keur: float     # enrichment overlay
    shl_principal_keur: float

    def __getattr__(self, name):
        # proxy undefined attrs to base
        return getattr(self.base, name)
```

Keeps original and enrichment separate. Better for audit. More disruptive to adopt.

### Option C — Cash Ledger as Primary Audit Layer

Phase 5A/5B cash ledger (`domain/portfolio/cash_ledger/`) provides a fully immutable audit trail that does not rely on mutation at all. As Phase 5D retained cash logic is added, the cash ledger can serve as the authoritative record of what was enriched — potentially reducing the need to store enrichment data on `WaterfallPeriod` itself.

---

## Summary

| Property | Value |
|---|---|
| `WaterfallPeriod` mutability | Mutable by design (Phase 4C decision) |
| Enrichment-writable fields | `shl_interest_keur`, `shl_principal_keur` only |
| Collision enforcement | ✅ PR #13 — raises `ValueError` on double non-zero |
| Immutable refactor | Deferred — isolated scope, does not block current phases |
| Phase 5D impact | None — 5D writes to new result objects, not `WaterfallPeriod` |

*This policy was established as part of the Phase 5D readiness review (2026-05-10) to document an intentional architectural choice that was previously implicit.*