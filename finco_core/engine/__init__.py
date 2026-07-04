"""
finco_core.engine — Top-level financial engine orchestration.

Extraction target (V2-3): FinancialEngine entry point that accepts
RunConfiguration and returns a typed EngineResult. Orchestrates all
domain subpackages (waterfall, tax, debt, SHL, depreciation, sponsor).

Runtime contract:
    RunConfiguration → FinancialEngine → EngineResult

No post-engine mutation. No identity dispatch. One execution path.
"""
