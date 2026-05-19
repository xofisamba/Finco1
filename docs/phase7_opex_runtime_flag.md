# Phase 7 — OPEX Runtime Flag (Stage 3)

## Purpose

Wire the already-calibrated OPEX line-item engine into runtime behind an explicit default-off flag. Activate for TUHO to close the +733 kEUR runtime gap.

## Prior Evidence

This stage builds on three completed stages:

1. **B-code source map (PR #92 / Stage 1):** All 13 B-groups (B.01–B.13) mapped to `domain/opex/templates/tuho.py`. Python offline engine = 84,674.78 kEUR = Excel annual total. +733 kEUR delta classified as `RUNTIME_OPT_IN` gap, not calibration error.

2. **Semiannual projection audit (PR #93 / Stage 2):** Actual-day projection convention validated. Python semiannual projection vs Excel CF!R38: max period delta = 4.77 kEUR, horizon delta = 0.00 kEUR. Current `projections.py` uses actual-day fractions — already correct. Stage 3 runtime flag eligible.

3. **Offline OPEX engine parity:** Python `compute_annual_opex()` = 84,674.78 kEUR = Excel `OpEx!R105`. Period-level delta vs Excel CF!R38 = 0.00 kEUR (exact match for all 60 periods with actual-day split).

## Flag Name and Default

- **Flag name:** `use_opex_line_item_engine`
- **Default value:** `False`
- **Location:** `domain/inputs.py` → `Info` dataclass field
- **Already exists** — confirmed present at `domain/inputs.py:91`

## Flag-Off Behavior (Default)

When `use_opex_line_item_engine = False` (default):
- TUHO: legacy scalar OPEX path via `opex_schedule_period()` from `domain/opex/projections.py`
- Oborovo: legacy scalar OPEX path (no change)
- TUHO OPEX total (flag-off): **85,408.27 kEUR** (runtime)
- Oborovo OPEX total (flag-off): **51,220.76 kEUR** (runtime)
- All other modules unchanged (revenue, debt, tax, SHL)

## Flag-On Behavior (TUHO Only)

When `use_opex_line_item_engine = True` for TUHO:
1. `build_runtime_opex_schedule()` is called via `waterfall_core.py`
2. `build_tuho_opex_template()` builds the TUHO line-item template
3. `compute_annual_opex()` computes annual OPEX (84,674.78 kEUR exact match to Excel)
4. `period.day_fraction` projects annual → semiannual periods (actual-day convention)
5. `period.opex_keur` is overridden with line-item value
6. EBITDA and downstream cash flow reflect line-item OPEX

**TUHO OPEX total (flag-on):** **84,674.78 kEUR** (vs Excel CF!R38: 84,674.78 kEUR, delta = 0.00 kEUR)

## TUHO Scope

- Only TUHO-WIND-1 is supported
- Supported project code: `"TUHO-WIND-1"`
- Oborovo is **guarded** — attempting flag-on for Oborovo raises `ValueError`

## Expected OPEX Totals

| Source | Total (kEUR) | Notes |
|--------|-------------|-------|
| Excel CF!R38 / OpEx!R105 | 84,674.78 | Annual incl. contingencies |
| Python offline engine | 84,674.78 | `compute_annual_opex` = exact match |
| Python flag-off runtime | 85,408.27 | Legacy scalar path |
| Python flag-on runtime | 84,674.78 | Line-item engine active |
| **Gap corrected** | **733.49 kEUR** | flag-on closes runtime gap |

## Period Tolerance

- **Max per-period delta:** ≤ 5 kEUR (strict threshold)
- **Actual flag-on vs Excel:** 0.00 kEUR max delta (exact match)
- **Horizon delta:** 0.00 kEUR (exact match)

## Downstream Effects (Flag-On)

| Metric | Flag-Off | Flag-On | Change |
|--------|----------|---------|--------|
| Total OPEX | 85,408.27 kEUR | 84,674.78 kEUR | −733.49 kEUR |
| Total EBITDA | 338,435.34 kEUR | 339,168.83 kEUR | +733.49 kEUR |
| Revenue | 423,843.61 kEUR | 423,843.61 kEUR | 0.00 kEUR ✅ |
| Senior Principal | 43,359.00 kEUR | 43,359.00 kEUR | 0.00 kEUR ✅ |
| Senior Interest | 22,467.39 kEUR | 22,444.89 kEUR | −22.50 kEUR (minor, cash-flow timing) |

**Only OPEX and EBITDA change.** Revenue and debt structure are unaffected. Interest changes by < 23 kEUR due to cash-flow timing within DSCR constraint — this is expected behavior as the waterfall schedules debt service based on available cash after OPEX.

## Oborovo Guard

- Attempting `use_opex_line_item_engine=True` for Oborovo raises `ValueError: OPEX line-item runtime engine is only supported for TUHO-WIND-1`
- Oborovo flag-off output is **unchanged** (51,220.76 kEUR)
- No Oborovo OPEX template exists yet

## R99/R102 BLOCKED

R99 and R102 remain BLOCKED. No SHL FCF runtime source. No R99/R102 promotion.

## Known Limitations

1. **Interest change of 22.50 kEUR:** Flag-on changes the cash-flow timing, which slightly affects the senior interest schedule (but not total principal). This is correct waterfall behavior — debt service is scheduled based on available cash after OPEX. Total principal repaid is identical (43,359.00 kEUR).

2. **Oborovo not yet supported:** No Oborovo OPEX template exists. Oborovo remains guarded with default-off flag.

3. **Stage 3 is TUHO-only.**

## Recommended Next Branch

`phase7-opex-inflation-decomposition` — Decompose the OPEX line-item template into inflation components for sensitivity analysis. Validate that each B-code group inflates independently at its documented rate.

Alternative: `phase7-model-stack-blueprint` if pausing OPEX implementation to consolidate architecture first.

## Implementation Details

### Flag Location
```python
# domain/inputs.py
@dataclass(frozen=True
class Info:
    use_opex_line_item_engine: bool = False  # line 91
```

### Waterfall Wiring
```python
# app/waterfall_core.py (lines 102-107)
if getattr(inputs.info, "use_opex_line_item_engine", False):
    from domain.opex.runtime_adapter import build_runtime_opex_schedule
    opex_period = build_runtime_opex_schedule(inputs, engine).period_schedule_keur
```

### Runtime Adapter
```python
# domain/opex/runtime_adapter.py
SUPPORTED_TUHO_CODES = {"TUHO-WIND-1"}

def build_runtime_opex_schedule(inputs, engine) -> RuntimeOpexAdapterResult:
    # Validates project code, builds annual + period schedules using actual-day fractions
```

### Projection Convention
The adapter uses `period.day_fraction` (actual-day from calendar) — confirmed correct in Stage 2 audit. No changes needed to `projections.py`.