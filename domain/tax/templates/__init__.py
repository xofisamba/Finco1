"""Phase 6A — Tax template architecture.

Schema, registry, and resolver for declarative tax configurations.
No active tax calculations. No tax cashflows. No deferred tax.
"""
from domain.tax.templates.registry import get_builtin_tax_templates
from domain.tax.templates.resolver import resolve_tax_template

__all__ = [
    "get_builtin_tax_templates",
    "resolve_tax_template",
]
