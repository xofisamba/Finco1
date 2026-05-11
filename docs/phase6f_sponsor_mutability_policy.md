# Phase 6F-C — Sponsor Mutability & Layering Policy

**Repository:** xofisamba/Finco1
**Branch:** `phase6f-sponsor-mutability-policy`
**Date:** 2026-05-11
**Type:** Architecture Policy Document
**Scope:** Documentation only — no implementation changes

---

## Status

**POLICY ACCEPTED** — To be enforced in Phase 7A/7B implementation.

---

## Context

Phase 6F-B introduced `EquityInjection` — an immutable schema for sponsor equity
injection events. Phase 7 will introduce sponsor cashflow results, sponsor IRR, and
potentially a sponsor waterfall. Before that work begins, a clear mutability policy
is required to prevent architectural drift.

This document establishes the policy for what may mutate and what must never mutate
in the sponsor-facing layer of the model.

---

## 1. Current Sponsor-Readiness State

### What exists

| Component | Status | Immutability |
|-----------|--------|--------------|
| `EquityInjection` | ✅ Phase 6F-B | Fully immutable — `__slots__`, internal `_metadata_tuple`, NaN/Inf validation |
| `EquityInjection.frozen_metadata` | ✅ Immutable | Returns sorted tuple; no mutation path |
| `EquityInjection.audit_note` | ✅ Property | Returns constant string |
| `EquityInjection.with_metadata()` | ✅ Non-mutating | Returns new instance |
| `TaxAssumptionSnapshot` | ✅ Phase 6D.2 | `@dataclass(frozen=True)` |
| `TaxTemplateSnapshot` | ✅ Phase 6D.2 | `@dataclass(frozen=True)` |
| `TaxOverrideSnapshot` | ✅ Phase 6D.2 | `@dataclass(frozen=True)` |
| `ResolvedTaxConfigSnapshot` | ✅ Phase 6D.2 | `@dataclass(frozen=True)` |
| `HoldCoTaxResult` | ⚠️ Schema only | Schema defined; active computation not yet connected |
| `SPVTaxResult` | ✅ Phase 6B | `@dataclass(frozen=True)` |

### What is coming

| Component | Phase | Expected immutability |
|-----------|-------|----------------------|
| `SponsorCashflowResult` | 7A | Fully immutable; derived from `EquityInjection` + waterfall outputs |
| `SponsorCapitalAccount` | 7A | Immutable snapshots; capital account balance computed, not mutated |
| `SponsorIRRResult` | 7B | Derived; read-only output of sponsor waterfall |
| `SponsorWaterfallResult` | 7B | Immutable; no intermediate state mutations |

### Sponsor IRR readiness

Sponsor IRR computation is **not yet implemented**. When it is introduced in Phase 7B,
it must consume derived cashflow outputs. It must not mutate input records.

---

## 2. Why Mutability Policy Matters

### Determinism requirement

The model must produce identical outputs given identical inputs every time.
If sponsor cashflow records can be mutated after construction, the same inputs
produce different outputs on successive runs — violating the reproducibility
requirement.

**Without a mutability policy:**
- Test results become non-reproducible
- Audit trails become unreliable
- Sponsor due diligence reports may reflect mutated state
- Sponsor IRR calculations become non-deterministic

### Audit integrity

Sponsor equity injection records, tax assumption snapshots, and derived cashflow
results form a governance audit trail. If these records can be mutated, the trail
loses its evidentiary value.

### Separation of concerns

- **Input records** (what the user/sponsor provided) must be preserved exactly
- **Derived results** (what the model computed) must be reproducible from inputs
- **Audit snapshots** (frozen point-in-time captures) must never change

If any of these layers mutates, the chain of evidence breaks.

### Sponsor covenant compliance

Sponsor IRR and MOIC are used in covenant compliance calculations. If underlying
cashflow records mutate between runs, covenant calculations become unverifiable.

---

## 3. Immutable Input Layer

The **immutable input layer** consists of records that represent what a user or
external system provided as input. These records must never be modified after
construction.

### Components

- `EquityInjection` — sponsor equity injection events
- project input records / model input schemas — project financial inputs (CAPEX, OPEX, debt structure, etc.)
- `HoldCoTaxInputs` — HoldCo tax configuration inputs
- `TaxTemplate` — tax template definitions (user-provided or system-loaded)
- `TaxTemplateOverride` — user overrides to tax templates
- Any future sponsor-provided input schema

### Policy

1. **Construction is the only mutation point.** Once an input record is constructed,
   it is immutable. There are no setter methods, no `update()` operations, and no
   direct field assignment.
2. **Inputs are validated at construction.** Invalid inputs are rejected at construction
   time, not corrected silently.
3. **Edits produce new objects.** To change an input, a new instance is created with
   the desired changes. The original is preserved unchanged.
4. **Metadata is frozen.** Any metadata attached to an input record is stored as an
   immutable sorted tuple. Only immutable JSON scalar values (`str`, `int`, `float`,
   `bool`, `None`) are accepted in metadata.

### Immutability enforcement

- `EquityInjection` uses `__slots__` + manual `__init__` with `object.__setattr__`
  for immutable field setting. No property setters exist.
- All other input schema classes use `@dataclass(frozen=True)` or equivalent
  immutable patterns.
- Frozen dataclasses use `object.__setattr__` in `__post_init__` for any internal
  normalization (e.g., converting `dict` metadata to sorted tuples).

---

## 4. Derived Result Layer

The **derived result layer** consists of records that are computed from immutable
inputs. They are deterministic outputs — never inputs to further computation
in a way that would require mutation.

### Components

- `SPVTaxResult` — SPV CIT computed per period (derived from `SPVTaxEngineInputs`)
- `HoldCoTaxResult` — HoldCo CIT computed per period (derived from `HoldCoTaxInputs`)
- `TaxAssumptionSnapshot` — frozen tax assumptions captured at a point in time
- `SponsorCashflowResult` — sponsor-level cashflows derived from waterfall outputs
  (Phase 7A)
- `SponsorCapitalAccount` — capital account balance derived from equity injections
  and distributions (Phase 7A)

### Policy

1. **Results are derived, not mutated.** A result is computed by a pure function
   from immutable inputs. The same inputs always produce the identical result.
2. **Results are stored, not computed on-the-fly.** When a result is requested,
   the pre-computed result is returned. No computation happens at access time.
3. **Results are immutable.** Like inputs, result records use frozen dataclasses
   or equivalent immutable patterns. There are no mutation paths.
4. **Results reference inputs, not vice versa.** Results do not hold mutable
   references to input records. They hold the computed values directly.

### Reproducibility

All derived results must be reproducible:
- Same inputs → same outputs, every run
- No reliance on system clock, mutable global state, or external data lookups
- If a result is recomputed, it must match the previously stored result exactly

---

## 5. Audit Snapshot Layer

The **audit snapshot layer** consists of frozen point-in-time captures of
configuration or results. They are immutable archives — not working state.

### Components

- `TaxAssumptionSnapshot` — complete tax configuration at a point in time
- `TaxTemplateSnapshot` — single template's frozen state
- `TaxOverrideSnapshot` — override record frozen at capture time
- `ResolvedTaxConfigSnapshot` — resolved tax config frozen at capture time
- Future snapshot types for sponsor configuration (Phase 7A+)

### Policy

1. **Snapshots are write-once, read-many.** A snapshot is created once and
   never modified. It is an archive, not a working document.
2. **Snapshots are named and timestamped.** Each snapshot has a `snapshot_label`
   (human-readable name) and `created_at` (timestamp). These enable audit
   traceability.
3. **Snapshots carry audit notes.** Every snapshot type includes an `audit_note`
   field confirming it is an audit-only artifact.
4. **Snapshots do not reference mutable state.** A snapshot captures the state of
   its target at creation time. It does not maintain live references to mutable
   objects.
5. **Snapshot comparison enables change detection.** Two snapshots of the same
   type at different times can be compared to detect configuration drift.

### Immutability in snapshots

All snapshot dataclasses are `@dataclass(frozen=True)`. Where normalization
occurs (e.g., dict → sorted tuple in metadata), it happens in `__post_init__`
and the normalized form is stored via `object.__setattr__`. After construction,
there are no mutation paths.

---

## 6. What May Mutate vs What Must Never Mutate

### May mutate — mutable working state

| Item | Rationale | Constraints |
|------|-----------|-------------|
| **User form / UI state** (Phase 7 future) | Temporary working state in a UI; discarded on save | Must not leak into immutable schema or result layer |
| **Draft `EquityInjection` before save** (future UI) | Pre-commit draft can change | Must become immutable on explicit "save" action |
| **In-memory computation caches** | Transient caches for performance | Must not be confused with immutable results; recomputable |

### Must never mutate — immutable records

| Item | Rationale |
|------|-----------|
| `EquityInjection` after construction | Audit trail, governance artifact |
| `EquityInjection.frozen_metadata` tuple | Internal immutable storage |
| `TaxAssumptionSnapshot` after creation | Audit archive |
| `TaxTemplateSnapshot` after creation | Audit archive |
| `TaxOverrideSnapshot` after creation | Audit archive |
| `ResolvedTaxConfigSnapshot` after creation | Audit archive |
| `SPVTaxResult` after construction | Derived, reproducible output |
| `HoldCoTaxResult` after construction | Derived, reproducible output |
| `SponsorCashflowResult` (Phase 7A) | Derived output; sponsor covenant evidence |
| Any future `SponsorCapitalAccount` snapshot | Immutable capital account history |
| project input records / model input schemas after construction | Immutable model input |
| `TaxTemplate` after construction | Immutable configuration |
| `TaxTemplateOverride` after construction | Immutable override record |

### The mutation boundary

```
MUTABLE (ephemeral)     → IMMUTABLE (committed)
─────────────────────────────────────────────
draft form state          → EquityInjection (save action)
draft override form       → TaxTemplateOverride (save action)
user-provided dict        → normalized frozen snapshot
```

**Important:** Mutable ephemeral state must never be confused with immutable
committed records. Any "edit" operation on an immutable record produces a new
object — the original is preserved.

---

## 7. EquityInjection Treatment

`EquityInjection` is a **read-only governance artifact once created**.

### Construction policy

- All fields are set at construction time via `__init__`
- Validation is strict: invalid inputs raise exceptions, no silent correction
- `amount_keur` must be finite and >= 0
- `investor_id`, `target_entity`, `purpose` must be non-empty strings
- `metadata` is normalized to a sorted immutable tuple on construction

### Post-construction policy

- No field may be modified after construction
- `metadata` property returns a fresh dict on each access — mutations of the
  returned dict do not affect the internal immutable tuple
- `frozen_metadata` returns the immutable tuple directly
- `with_metadata(**kwargs)` returns a **new** `EquityInjection` — the original
  is unchanged

### Audit trail

- `audit_note` property returns a constant string confirming the record is
  an audit-only artifact
- `frozen_metadata` preserves the exact key-value pairs provided at construction
- No mutation path exists to alter any field after construction

### Phase 7A integration

When sponsor capital account is computed in Phase 7A:
- `EquityInjection` records are **read** to compute capital contributions
- No `EquityInjection` record is ever modified as a side effect of computation
- Capital account balance is a **derived result**, stored in a separate record

---

## 8. Future SponsorCashflowResult Treatment

`SponsorCashflowResult` (Phase 7A) must follow the same immutability principles
as `EquityInjection` and tax result schemas.

### Schema design principles

1. **Derived, not mutated.** `SponsorCashflowResult` is computed from immutable
   inputs (equity injections, SPV distributions, HoldCo obligations, tax payments).
   The computation is a pure function. The result is stored, not mutated.
2. **Per-period breakdown.** The result carries period-by-period cashflow
   components (equity injected, distributions received, taxes paid, etc.) as
   frozen tuples.
3. **No internal state beyond construction.** Once constructed, a
   `SponsorCashflowResult` has no mutable state. It is an immutable record.
4. **Audit note included.** The result includes an `audit_note` property
   confirming it is a derived output, not a user-provided input.

### Anticipated schema (Phase 7A design, not implemented)

```python
@dataclass(frozen=True)
class SponsorCashflowResult:
    period_index: int
    equity_injected_keur: float        # from EquityInjection records
    distribution_received_keur: float  # from HoldCo distributions
    wht_paid_keur: float               # from HoldCo WHT calculations
    cit_paid_keur: float               # from HoldCo CIT (cash timing applied)
    net_cashflow_keur: float           # derived
    audit_note: str                    # "AUDIT-ONLY: derived output..."
```

### Sponsor IRR integration (Phase 7B)

When Sponsor IRR is computed (Phase 7B):
- `SponsorCashflowResult` records are **read** as inputs to the IRR calculation
- No `SponsorCashflowResult` record is mutated by the IRR computation
- The IRR result is a separate `SponsorIRRResult` derived output

---

## 9. Persistence-Readiness Constraints

The immutability policy makes the model naturally persistence-ready. The following
constraints must be observed if persistence is added in a future phase.

### Serialization

All immutable records must be JSON-serializable:
- All tuple fields contain only JSON-serializable values
- Metadata values are restricted to immutable JSON scalars: `str`, `int`,
  `float`, `bool`, `None`
- No `datetime` objects with non-isoformat representations (use ISO strings)
- No bytes or arbitrary objects

### Unique identification

Each immutable record type must have a natural unique identifier:
- `EquityInjection`: `(investor_id, target_entity, period_index, purpose)` or
  a generated UUID
- `TaxAssumptionSnapshot`: `snapshot_label` + `created_at` timestamp
- `SponsorCashflowResult`: period index + sponsor investor ID

### Read-only persistence

If persistence is added:
- Records are **written once** and never updated
- Any "edit" produces a new record with a new identifier
- Old records are preserved for audit trail
- Database schema supports append-only semantics

### Versioning

If schema changes are required:
- Old records remain valid under the old schema
- New records use the new schema
- Downstream consumers handle both versions

---

## 10. Explicit Non-Scope

The following are explicitly out of scope for this policy document:

| Item | Reason |
|------|--------|
| Sponsor IRR implementation | Phase 7B topic |
| Promote waterfall | Phase 7B topic |
| Sponsor cashflow computation | Phase 7A topic |
| Sponsor capital account computation | Phase 7A topic |
| Editable persistence | Future Phase — not designed |
| Role system / access control | Future Phase — not designed |
| Approval workflow | Future Phase — not designed |
| UI mutable state management | Future Phase — context-dependent |
| Draft/pre-commit state | Future Phase UI concern |
| Multi-sponsor aggregation schema | Phase 7A+ (may be needed) |

---

## 11. Recommendation for Phase 7A/7B

### Phase 7A — Sponsor Cashflow & Capital Account

**Schema design checklist:**
- [ ] `SponsorCashflowResult` is `@dataclass(frozen=True)` or equivalent
- [ ] All period arrays are `tuple[float, ...]`, not `list`
- [ ] `audit_note` property included on every result schema
- [ ] No internal mutable state after construction
- [ ] Metadata values restricted to immutable JSON scalars
- [ ] `SponsorCapitalAccount` uses immutable snapshots per period

**Integration checklist:**
- [ ] `EquityInjection` records are read-only inputs to capital account computation
- [ ] No `EquityInjection` field is modified as a side effect of computation
- [ ] Capital account balance is a derived result, not a mutation of existing records
- [ ] All derived results reference immutable inputs; no live mutable references

### Phase 7B — Sponsor IRR

**Schema design checklist:**
- [ ] `SponsorIRRResult` is `@dataclass(frozen=True)` or equivalent
- [ ] `audit_note` property included
- [ ] `SponsorIRRResult` references `SponsorCashflowResult` records, not mutable state
- [ ] No internal state mutation during IRR computation

**Integration checklist:**
- [ ] IRR computation is a pure function: same inputs → same output, every run
- [ ] IRR result does not mutate any `EquityInjection` or `SponsorCashflowResult`
- [ ] IRR result stored separately; original cashflow records preserved unchanged
- [ ] Audit trail links IRR result back to the cashflow records it was derived from

### Mutability enforcement in code review

Phase 7A/7B implementations should be reviewed against this checklist:
- [ ] No `setattr()` on immutable records after construction (except `object.__setattr__`
  in `__post_init__` for normalization)
- [ ] No `list` fields in result schemas — use `tuple`
- [ ] No `dict` in metadata — normalized to sorted tuple
- [ ] No `with_metadata()` that mutates the original
- [ ] No `datetime.utcnow()` — use `datetime.now(timezone.utc)` for timestamps
- [ ] All test suites run with identical seeds for reproducibility

---

*End of Policy Document — Phase 6F-C Sponsor Mutability & Layering Policy*
*Branch: phase6f-sponsor-mutability-policy*
*Enforcement: Phase 7A/7B implementation*
