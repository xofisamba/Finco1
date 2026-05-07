# Excel Depreciation Roadmap

## Future Excel Disclosure: Tax/Book Separation

When the bankable runtime path is activated, Excel export should include separate tax and book depreciation schedules.

---

## Planned Excel Tabs

### Tab: "Tax Depreciation"
Per-asset-class table showing annual tax depreciation:

| Asset Class | Tax Life | Y1 | Y2 | ... | Y20 |
|-------------|---------|----|----|-----|-----|
| Solar Modules | 20y | X | X | ... | X |
| Inverters | 10y | X | X | ... | X |
| Grid Connection | 20y | X | X | ... | X |
| Development Soft | 5y | X | X | ... | X |
| Civil Works (EPC) | 25y | X | X | ... | X |
| Contingency | 5y | X | X | ... | X |
| **Total** | — | X | X | ... | X |

### Tab: "Book Depreciation"
Same structure with book lives (typically longer for solar: 25y for modules, 10y for inverters).

### Tab: "Depreciation Summary"
Reconciliation:
- Opening NBV
- + Tax depreciation (annual)
- + Book depreciation (annual)  
- = Closing NBV (tax)
- = Closing NBV (book)

---

## Known Limitations

1. **COD year partial period:** Tax/book schedules show full-year amounts; actual period depreciation is pro-rated by `day_fraction` in waterfall. Excel tab should note this.
2. **Contingency allocation:** Proportional to depreciable basis — not separately disclosed at individual item level.
3. **Mid-year convention:** Not yet implemented — schedules assume full-year convention.
4. **Inflation adjustment:** Not modeled — tax basis is historical cost only.

---

## Advisory Caveats

Excel depreciation disclosures are:
- Based on straight-line method (tax and book)
- Subject to local tax authority确认 (BIH/HR tax treatment)
- Not adjusted for early replacement, impairment, or revaluation
- Part of model output, not audited financial statements

---
