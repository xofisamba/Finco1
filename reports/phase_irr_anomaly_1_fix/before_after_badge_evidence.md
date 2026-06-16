# IRR-ANOMALY-1-FIX: Before/After Badge Evidence

## Before (commit 3aadc8a — pre-fix)

```html
<!-- _matrix_run_result.html — M4 matrix run badge (pre-fix) -->
<div id="matrix-run-badge-{{ scenario_id }}" class="matrix-run-badge-wrap">
  {% if run_ok %}
    <span class="matrix-run-badge matrix-run-badge--run">Run ✓</span>
    {% if min_dscr is not none %}
      <span class="matrix-run-kpi" data-m4-kpi="min_dscr">DSCR {{ min_dscr }}</span>
    {% endif %}
    {% if equity_irr is not none %}
      <span class="matrix-run-kpi" data-m4-kpi="equity_irr">IRR {{ equity_irr }}</span>
    {% endif %}
  {% else %}
    ...
  {% endif %}
</div>
```

### Observed values (TUHO, tariff haircut 60 → 55):

| Field shown | Pre-fix value | What it actually is |
|---|---|---|
| "IRR" | 7.85% | `equity_irr` |
| "DSCR" | 1.3430 | `actual_min_dscr` (pinned by sculpt) |

For comparison, the SAME engine run produces:
- `project_irr` = 6.78% (the *real* project IRR for tariff=55)
- `actual_avg_dscr` = 1.5193 (the *real* avg DSCR)

The pilot user saw:
- Base: 7.33% IRR (project_irr) + 1.51x DSCR (avg_dscr)
- Downside: 7.85% IRR (equity_irr!) + 1.343x DSCR (min_dscr!)

This created the impression that lowering tariff increased IRR by 0.52pp.

## After (commit c8172f6 — post-fix)

```html
<!-- _matrix_run_result.html — M4 matrix run badge (post-fix) -->
<div id="matrix-run-badge-{{ scenario_id }}" class="matrix-run-badge-wrap">
  {% if run_ok %}
    <span class="matrix-run-badge matrix-run-badge--run">Run ✓</span>
    {% if avg_dscr is not none %}
      <span class="matrix-run-kpi" data-m4-kpi="avg_dscr">DSCR {{ avg_dscr }}</span>
    {% endif %}
    {% if project_irr is not none %}
      <span class="matrix-run-kpi" data-m4-kpi="project_irr">IRR {{ project_irr }}</span>
    {% endif %}
  {% else %}
    ...
  {% endif %}
</div>
```

### Observed values (TUHO, tariff haircut 60 → 55):

| Field shown | Post-fix value | What it actually is |
|---|---|---|
| "IRR" | 6.78% | `project_irr` |
| "DSCR" | 1.52x | `actual_avg_dscr` |

This now matches the Dashboard run summary semantics, and the
pilot user will see:
- Base: 7.33% IRR + 1.51x DSCR
- Downside: 6.78% IRR + 1.52x DSCR

The honest comparison: lower tariff → lower IRR (as expected for a downside).

## M4 route diff (main_web.py:4742-4753)

### Before
```python
kpis = result.get("kpis", {})
min_dscr_raw = kpis.get("min_dscr")
equity_irr_raw = kpis.get("equity_irr")
min_dscr = f"{min_dscr_raw:.4f}" if min_dscr_raw is not None else None
equity_irr = f"{float(equity_irr_raw) * 100:.2f}%" if equity_irr_raw is not None else None
```

### After
```python
kpis = result.get("kpis", {})
# IRR-ANOMALY-1-FIX: matrix badge now uses the same top-level
# metrics as the Dashboard Run summary (project_irr + avg_dscr)
# so Base vs Downside comparisons are not misled by mixing
# Project IRR with Equity IRR, or Avg DSCR with Min DSCR.
# Phase: presentation-only fix. Engine output and overrides
# are unchanged.
project_irr_raw = kpis.get("project_irr")
avg_dscr_raw = kpis.get("avg_dscr")
project_irr = f"{float(project_irr_raw) * 100:.2f}%" if project_irr_raw is not None else None
avg_dscr = f"{avg_dscr_raw:.2f}x".replace(".00x", ".0x") if avg_dscr_raw is not None else None
```

## Engine parity (pinned by tests)

- `app/waterfall_core.py` MD5: `6bf49f33efc989736c17cea0cb9b7723` (unchanged)
- TUHO baseline (post-fix):
  - `project_irr` = 0.073309 (7.33%)
  - `actual_avg_dscr` = 1.508914
  - `actual_min_dscr` = 1.342992
  - (matches pre-fix baseline exactly)
- Oborovo path: unchanged
