# Finco One v2 — Architecture

**Status**: Active — skeleton established V2-1  
**Baseline**: Finco1-RC2 @ `b52d39c79683a1ff6965ef197422056a541a81ab`

---

## Architectural Goals

1. **Preserve the proven financial engine** — port without reimplementing. Every validated formula, parity result, and invariant must survive extraction intact.
2. **Eliminate the application shell** — the Streamlit monolith is not ported. Only the mathematical engine crosses over.
3. **Enforce stable package boundaries** — dependencies flow in one direction only; reversals are prohibited.
4. **Make parity a first-class citizen** — `finco_parity` is a package, not an afterthought. CI fails on any parity drift.
5. **No identity dispatch** — capability flags in input models are the sole dispatch mechanism. Engine behaviour must never branch on project name or code.
6. **No post-engine mutation** — financial fields computed by the engine are not overridden after the engine returns. The tax bridge is reconciliation-only.

---

## Package Map

```
finco_core/          Pure financial engine. No web. No UI. No DB.
    inputs/          Typed input models and run configuration.
    engine/          Orchestration entry point. One execution path.
    waterfall/       Period-level cashflow computation kernel.
    tax/             Tax engine, loss carryforward, CIT.
    debt/            Senior debt schedule, sculpting, covenants.
    depreciation/    Book and tax depreciation ledger.
    shl/             Shareholder loan engine.
    sponsor/         Sponsor cashflow and equity IRR.
    audit/           Typed, immutable audit output contract.
    exports/         Typed, serialisable export output contract.
    validation/      Input boundary validation.

finco_app/           Application wrapper. Depends on finco_core.
    api/             FastAPI routes and OpenAPI schema.
    services/        Use-case orchestration.
    persistence/     Storage for projects, runs, snapshots, exports.

finco_parity/        Parity harness. Depends on finco_core only.
    fixtures/        Canonical input configurations for reference projects.
    golden/          Expected KPI baseline outputs.
    regression/      Parametrised regression tests.

finco_ui/            (V2-7) Product UI. Depends on API contract only.
```

---

## Dependency Direction

```
finco_core
    ↑
    │  (depends on)
finco_app
    ↑
    │  (depends on)
finco_ui

finco_core
    ↑
    │  (depends on)
finco_parity
```

**Prohibited:**
- `finco_core` importing from `finco_app`
- `finco_core` importing from `finco_parity`
- `finco_core` importing from `finco_ui`
- `finco_app` importing from `finco_ui`
- `finco_parity` importing from `finco_app`
- Any package importing from `tests/`

Circular imports are a build-time error.

---

## Runtime Contract

### The one execution path

```
ProjectInputs          Typed dataclass. Validated at boundary.
       │
       ▼
RunConfiguration       Frozen config derived from ProjectInputs.
       │               Capability flags only — no identity dispatch.
       ▼
FinancialEngine        Deterministic computation.
       │               Given identical RunConfiguration → identical EngineResult.
       ▼
EngineResult           Typed, immutable. Never mutated after production.
       │
       ▼
AuditResult            Read-only structured view. Adds provenance, diagnostic
       │               fields. Does not modify financial values.
       ▼
ExportResult           Serialisable output. Excel / CSV / JSON ready.
       │
       ▼
API                    HTTP response. Depends on ExportResult schema.
       │
       ▼
UI                     Renders API responses. No direct engine access.
```

### Invariants

- `EngineResult` is produced once and never modified.
- `cf_after_tax_keur` and all period-level financial fields are set by the waterfall engine and never overridden downstream.
- The tax bridge produces `cash_tax_bridge_reconciliation_keur` only — a reconciliation field, not a cashflow override.
- `RunConfiguration` has no `project_code` field. Capability flags in `ProjectInputs` are the sole dispatch mechanism.

---

## Architectural Rules

### No identity dispatch

The engine must never branch on a project name, code, or string identifier at runtime. The old pattern:

```python
# PROHIBITED — eliminated in Stack AC + Phase 0 Y3
if code == "TUHO-WIND-1":
    use_tax_bridge = True
```

must never reappear. Capability flags in `ProjectInputs` / `FinancingParams` are the only permitted dispatch mechanism:

```python
# CORRECT
if config.use_tax_bridge_engine:
    ...
```

### No post-engine mutation

Financial outputs are computed by `FinancialEngine` and returned as `EngineResult`. No downstream layer (audit, export, API, UI) may modify financial field values. The audit layer adds metadata; it does not change numbers.

### No runtime reads from `tests/`

No production code in `finco_core`, `finco_app`, or `finco_ui` imports from or reads files in `tests/` or `finco_parity/` at runtime. Parity fixtures are test infrastructure.

### One execution path

There is exactly one code path from `ProjectInputs` to `EngineResult`. Feature variants are controlled by capability flags in `ProjectInputs`, not by branching at the call site. This makes the engine deterministic and auditable.

### Typed outputs only

`EngineResult`, `AuditResult`, and `ExportResult` are typed dataclasses or Pydantic models. No `dict` or `Any` return types on public engine interfaces.

### Engine independent of UI

`finco_core` has no knowledge of HTTP request shapes, session state, Streamlit widgets, or rendering concerns. The UI depends on the API contract; it never calls engine code directly.

---

## Parity Philosophy

The extraction programme does not reproduce financial behaviour from first principles. It ports proven behaviour from `Finco1-RC2`. Parity is not a nice-to-have — it is the acceptance criterion for every extraction milestone.

**Parity tolerance windows (RC2 baseline):**

| KPI | Tolerance |
|-----|-----------|
| equity_irr | ±0.05% |
| actual_avg_dscr | ±0.001 |
| total_tax_keur | ±500 kEUR |
| total_distributions | ±200 kEUR |

A PR that causes parity drift outside these windows is not mergeable, regardless of other properties.

---

## LCF Invariant

The Loss Carryforward methodology (5-year rolling, Croatian CIT §16, `expire_before_use=True`) is correct and must not be changed to match the Excel Golden Model where the Excel model is wrong. Finco intentionally diverges from Excel on LCF. This is documented, not a bug.

---

*See also: `docs/RC2_BASELINE.md`, `docs/FINCO_V2_CONTROLLED_EXTRACTION_PLAN.md`, `docs/EXTRACTION_STRATEGY_UPDATE.md`*
