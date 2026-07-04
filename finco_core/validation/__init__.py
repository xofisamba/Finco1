"""
finco_core.validation — Input validation layer.

Extraction target (V2-2): boundary validation for ProjectInputs and
FinancingParams. Called before RunConfiguration is built. Produces
typed validation errors; does not raise exceptions into engine code.

Source: domain/validation.py

V2-3: Forward shims to domain validation module.
"""
from domain.validation import (
    ValidationIssue,
    ModelWarning,
    MODEL_WARNING_CODES,
    validate_project_inputs,
    validate_portfolio_inputs,
    warn_model_unrealistic,
    dscr_reconciliation_fields,
)

__all__ = [
    "ValidationIssue",
    "ModelWarning",
    "MODEL_WARNING_CODES",
    "validate_project_inputs",
    "validate_portfolio_inputs",
    "warn_model_unrealistic",
    "dscr_reconciliation_fields",
]
