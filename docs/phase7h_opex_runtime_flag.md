# Phase 7H OPEX Runtime Flag

This branch adds a runtime integration path for the offline OPEX line-item
engine behind `ProjectInfo.use_opex_line_item_engine`, which defaults to
`False`.

Default projects continue to use the legacy OPEX schedule. When the flag is
enabled for TUHO (`TUHO-WIND-1`), the runtime adapter uses the Phase 7H TUHO
template and converts annual line-item totals into the existing per-period OPEX
schedule. Unsupported projects raise a clear error instead of silently applying
the TUHO template.

The adapter is deliberately isolated from `domain.waterfall` and exposes the
annual engine result for future audit/export work. No SHL, revenue, tax, senior
debt, R99, construction, cache, or UI behavior is changed.
