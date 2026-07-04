"""
finco_core.tax — Tax engine.

Extraction target (V2-3): TaxEngine, LossCarryforward (5-year rolling,
Croatian CIT §16, expire_before_use=True), holdco tax calculations,
tax bridge (reconciliation-only per Phase 0 Z2).

Source: domain/tax/

Critical invariant: LCF methodology is NOT calibrated to the Excel Golden
Model where Excel is wrong. Finco intentionally keeps the correct Croatian
§16 treatment.
"""
