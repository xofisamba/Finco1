"""
finco_core.validation — Input validation layer.

Extraction target (V2-2): boundary validation for ProjectInputs and
FinancingParams. Called before RunConfiguration is built. Produces
typed validation errors; does not raise exceptions into engine code.

Source: domain/validation.py
"""
