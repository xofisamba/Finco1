# Phase 7H TUHO OPEX Template Mapping

This PR adds an offline-only OPEX line-item engine and TUHO OPEX template. It is
not wired into waterfall runtime, factories, revenue, tax, SHL, senior debt, or
UI behavior.

## Scope

- `domain/opex/line_items.py`: line-item schema.
- `domain/opex/engine.py`: annual-first OPEX calculation.
- `domain/opex/result.py`: annual/group/item result objects.
- `domain/opex/templates/tuho.py`: TUHO template for Excel parity tests.

## TUHO Template Rules

- B.01 includes Bazefield and has base total 280 kEUR with 2% inflation.
- B.02.1 is an explicit annual schedule and is not inflated.
- B.02 group inflation is zero to avoid double-inflating the explicit schedule.
- B.07 uses the standard inflation exponent where Y1 is not inflated.
- B.11 uses an explicit 30-year active flag tuple: Y1-Y14 active, Y15-Y30 inactive.
- B.13 is one percent-of-selected-groups item at 6% of B.01-B.12.
- B.13 does not reference itself and group `contingency_pct` remains zero.

## Excel Parity

Expected 30-year total OPEX is 84,674.78 kEUR. The template parity tests assert
every annual total against the Excel annual values within 0.01 kEUR.

## Runtime Safety

The engine is offline only. No runtime adapter, project factory flag, waterfall
wiring, or model output change is included in this scope.
