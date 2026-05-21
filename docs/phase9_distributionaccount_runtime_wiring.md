# Phase 9C: DistributionAccount Runtime Wiring

**Status:** Implemented, not yet merged
**Branch:** `phase9-distributionaccount-runtime-wiring`
**Based on:** PR #150 merge (`6aa56308aae6d335989eb51e6308935e9608741b`)

---

## Overview

Phase 9C adds an explicit default-off flag that wires the DistributionAccount's `equity_distribution_paid_keur` into the runtime's `distribution_keur`. The waterfall result becomes a pass-through alias: `distribution_keur` is set to the DA's computed value, not the other way around.

**This is a controlled default-off transition.** No runtime behavior changes unless the flag is explicitly set to `True`.

---

## Flag

```python
use_distributionaccount_runtime_wiring: bool = False
```

Added to `run_waterfall_v3_core()` in `app/waterfall_core.py`.

---

## Behavior

### `flag=False` (default, legacy)

```
distribution_keur = WaterfallEngine.distribution_keur  # unchanged
distribution_source = ''                                # empty
legacy_distribution_keur = 0
da_paid_distribution_keur = 0
distribution_wiring_delta_keur = 0
```

Exact legacy runtime behavior. No changes to any output.

### `flag=True` (DA wired)

```
distribution_keur = equity_distribution_paid_keur   # DA economic mode
distribution_source = 'distribution_account'
legacy_distribution_keur = original distribution_keur  # before override
da_paid_distribution_keur = equity_distribution_paid_keur
distribution_wiring_delta_keur = da_paid - legacy
total_distribution_keur = sum(period distribution_keur)  # recalculated
```

`distribution_keur` becomes a **pass-through alias** of DA's `equity_distribution_paid_keur`.
There is exactly one runtime distribution source.

---

## TUHO Validation (baseline)

| Metric | Value |
|--------|-------|
| Legacy total distribution | ~326,165 kEUR |
| DA-paid total (flag=True) | ~284,552 kEUR |
| Delta | ~-41,613 kEUR |
| Non-zero distribution periods | 48 / 61 |
| Lockup periods zeroed | 13 / 61 |

**Why the delta?** Economic mode evaluates the lockup gate (senior tenor = 14 semi-annual periods = periods 1-13). In legacy runtime mode, distributions flow in lockup periods (before SHL balance is cleared). DA economic mode correctly zeros distributions during lockup. This is expected, not a bug.

---

## Oborovo Policy

**Blocked.** Oborovo has TUHO-specific gates (R99, R102) that do not apply to it. DA runtime wiring for Oborovo would need a separate guard design. Currently:

```
flag=True for non-TUHO → guard fires
distribution_source = 'oborovo_guard_blocked'
distribution_keur = unchanged (legacy)
da_paid_distribution_keur = 0.0
distribution_wiring_delta_keur = 0.0
```

Oborovo runs unchanged regardless of the flag.

---

## R99/R102 Governance

**BLOCKED. Not changed by this flag.**

- flag=True uses `audit_economic_mode=True` in the DA engine (gates evaluated, not promoted)
- Lockup periods (1-13) still zero distributions — R99/R102 remain evaluated as gates
- No R99/R102 promotion occurs in `_apply_distributionaccount_runtime_wiring`
- This flag does **not** enable governed-mode promotion

---

## Supported Flag Combinations

| Combination | Supported |
|-------------|-----------|
| baseline (flag=False) | ✅ |
| DA runtime wiring only (flag=True) | ✅ TUHO only |
| tax_bridge only | ✅ (PR #150) |
| tax_bridge + DA wiring | ✅ TUHO only |
| CO2 revenue bridge | ✅ (PR #147) |
| CO2 revenue + DA wiring | ✅ TUHO only |
| shl_canonical + DA wiring | ✅ TUHO only |
| deprec_canonical + DA wiring | ✅ TUHO only |
| shl+deprec + DA wiring | ✅ TUHO only |
| Oborovo + DA wiring | ❌ blocked by guard |

All TUHO-supported combinations from the dual-run matrix (baseline, shl_canonical, deprec_canonical, shl+deprec, co2_revenue_bridge, co2_cit_bridge, shl+co2_revenue, tax_bridge, shl+deprec+tax_bridge) are compatible with DA runtime wiring.

---

## Non-Goals (Not Changed)

- ❌ R99/R102 promotion — remains BLOCKED in governed mode
- ❌ SHL R102 port wiring — unchanged
- ❌ SponsorEngine distribution handoff — unchanged
- ❌ SeniorDebtSizing rewrite — unchanged
- ❌ TaxEngine rewrite — unchanged
- ❌ Oborovo runtime wiring — blocked by guard
- ❌ UI changes
- ❌ Excel export expansion
- ❌ Scalar calibration offsets

---

## Audit Metadata

Per-period fields on `WaterfallPeriod` (added to `domain/waterfall/waterfall_engine.py`):

| Field | Type | Description |
|-------|------|-------------|
| `legacy_distribution_keur` | float | Runtime distribution before override (flag=True) |
| `da_paid_distribution_keur` | float | DA equity_distribution_paid_keur |
| `distribution_source` | str | `'distribution_account'` or `'oborovo_guard_blocked'` |
| `distribution_wiring_delta_keur` | float | da_paid - legacy |

Result-level fields on `WaterfallResult`:

| Field | Type | Description |
|-------|------|-------------|
| `legacy_distribution_keur` | float | Pre-wiring total |
| `da_paid_distribution_keur` | float | DA-computed total |
| `distribution_source` | str | `'distribution_account'` or `'oborovo_guard_blocked'` |
| `distribution_wiring_delta_keur` | float | Total delta |

---

## Rollback Plan

To disable DA runtime wiring at runtime:

```python
result = run_waterfall_v3_core(
    ...,
    use_distributionaccount_runtime_wiring=False,  # default
)
```

`distribution_keur` returns to exact legacy behavior with no metadata attached.

---

## Files Changed

| File | Change |
|------|--------|
| `app/waterfall_core.py` | Flag parameter + `_apply_distributionaccount_runtime_wiring()` function + Oborovo guard |
| `domain/waterfall/waterfall_engine.py` | Audit metadata fields on `WaterfallPeriod` and `WaterfallResult` |
| `tests/test_phase9_distributionaccount_runtime_wiring.py` | 28 tests covering flag behavior, TUHO, Oborovo guard, audit metadata, governance |
| `docs/phase9_distributionaccount_runtime_wiring.md` | This document |
| `reports/phase9_distributionaccount_runtime_wiring_validation.csv` | Validation report (TUHO + Oborovo flag combinations) |