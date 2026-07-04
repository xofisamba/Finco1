"""
finco_core.waterfall — Waterfall engine.

Extraction target (V2-3): WaterfallEngine, WaterfallPeriod, WaterfallResult,
run_waterfall, period generation. The innermost financial computation kernel.

Post-engine mutation is prohibited. cf_after_tax_keur is computed once by
the waterfall and never overridden. The tax bridge is reconciliation-only
(cash_tax_bridge_reconciliation_keur), per Phase 0 Z2.

Source: domain/waterfall/
"""
