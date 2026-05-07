# Main Post-Merge Status

**Updated:** 2026-05-07
**HEAD:** `1cab0fe` (v1.4-bankable-runtime-active checkpoint)

---

## Architecture Summary

```
Streamlit UI (port 8501) / FastAPI / CLI
  ↓ run_demo_project()
  → ui_runner.py
    → WaterfallRunner / WaterfallRunConfig
      → waterfall_core.run_waterfall_v3_core()
        → depreciation (bankable path when advanced_capex_line_items provided)
        → tax shield via dep * p.day_fraction (single application)
```

---

## Depreciation Architecture

| Asset | Tax Life | Book Life | Convention | Status |
|-------|----------|-----------|-----------|--------|
| Solar Modules | 20y | 25y | FULL_YEAR | ✅ Runtime-active |
| Inverters | 10y | 10y | FULL_YEAR | ✅ Runtime-active |
| Grid Connection | 20y | 20y | FULL_YEAR | ✅ Runtime-active |
| Transformer | 20y | 20y | FULL_YEAR | ✅ Runtime-active |
| Civil Works (EPC) | 20y | 25y | FULL_YEAR | ✅ Runtime-active |
| Development Soft | 5y | 5y | FULL_YEAR | ✅ Runtime-active |
| Contingency | 5y | 5y | proportional | ✅ Runtime-active |
| Land | 0y | 0y | non-depreciable | ✅ Runtime-active |

---

## Readying For

| Use Case | Readiness | Notes |
|----------|-----------|-------|
| Internal advisory | ✅ GO | Bankable framework in place |
| Controlled B2B pilot | ✅ GO | With caveats |
| HTMX production | ❌ Not yet | Need Excel disclosure + auth first |
| Bankability positioning | ✅ GO | Framework supports it |

---

## rc1 Status

**FROZEN** — not modified since creation.
SHA: `b425a07` (v1.2.1 release)
