"""Phase 6A — Tax template resolver.

Applies TaxTemplateOverride objects to a base TaxTemplate immutably,
producing a ResolvedTaxConfig. No mutation of the base template.

Phase 6A supports simple top-level field overrides only.
Nested field-path replacement (with '.') is not implemented yet.
"""
from __future__ import annotations

from domain.tax.templates.inputs import (
    TaxTemplate,
    TaxTemplateOverride,
    ResolvedTaxConfig,
    CITTier,
    TaxDepreciationRule,
)


# Valid override targets (simple top-level fields on TaxTemplate)
_VALID_OVERRIDE_FIELDS = frozenset({
    "country_code",
    "template_name",
    "tax_year",
    "cit_tiers",
    "depreciation_rules",
    "withholding_tax_dividends",
    "withholding_tax_interest",
    "loss_carryforward_years",
    "thin_cap_ratio",
    "interest_limitation_pct_ebitda",
    "metadata",
})


def resolve_tax_template(
    base_template: TaxTemplate,
    overrides: tuple[TaxTemplateOverride, ...],
) -> ResolvedTaxConfig:
    """Apply overrides to a TaxTemplate and return a ResolvedTaxConfig.

    This is a **pure function**: the base_template is never mutated.
    Override application is order-preserving; on duplicate field_path,
    the last override wins.

    Parameters
    ----------
    base_template : TaxTemplate
        The template to apply overrides to.
    overrides : tuple[TaxTemplateOverride, ...]
        Zero or more overrides to apply. Empty tuple = no change.

    Returns
    -------
    ResolvedTaxConfig
        Contains the resolved template (with overrides applied),
        the override list, and merged metadata.

    Raises
    ------
    ValueError
        If an override targets an invalid or unsupported field_path,
        or if override values fail TaxTemplate validation.

    Examples
    --------
    >>> hr_tpl = get_builtin_tax_templates()[0]  # HR_SIMPLE_2026
    >>> override = TaxTemplateOverride(
    ...     override_name="relax_wht",
    ...     field_path="withholding_tax_interest",
    ...     override_value=0.05,
    ...     reason="Treaty rate HR-ME"
    ... )
    >>> result = resolve_tax_template(hr_tpl, (override,))
    >>> result.resolved_metadata_dict
    {'note': 'illustrative only', ...}
    """
    # Build override map (last wins for duplicates)
    override_map: dict[str, TaxTemplateOverride] = {}
    for ov in overrides:
        if ov.field_path not in _VALID_OVERRIDE_FIELDS:
            raise ValueError(
                f"Invalid override field_path {ov.field_path!r}. "
                f"Valid fields: {sorted(_VALID_OVERRIDE_FIELDS)}"
            )
        override_map[ov.field_path] = ov

    if not override_map:
        # No overrides: resolved metadata = base template metadata
        return ResolvedTaxConfig(
            base_template=base_template,
            overrides=(),
            resolved_metadata=base_template.metadata,
        )

    # Start from base template field values
    fields = {
        "country_code": base_template.country_code,
        "template_name": base_template.template_name,
        "tax_year": base_template.tax_year,
        "cit_tiers": base_template.cit_tiers,
        "depreciation_rules": base_template.depreciation_rules,
        "withholding_tax_dividends": base_template.withholding_tax_dividends,
        "withholding_tax_interest": base_template.withholding_tax_interest,
        "loss_carryforward_years": base_template.loss_carryforward_years,
        "thin_cap_ratio": base_template.thin_cap_ratio,
        "interest_limitation_pct_ebitda": base_template.interest_limitation_pct_ebitda,
        "metadata": dict(base_template.metadata),
    }

    # Apply each override
    for field_path, ov in override_map.items():
        fields[field_path] = ov.override_value

    # Coerce list→tuple for cit_tiers and depreciation_rules if overridden
    for list_field in ("cit_tiers", "depreciation_rules"):
        val = fields[list_field]
        if isinstance(val, list):
            fields[list_field] = tuple(val)
        elif not isinstance(val, tuple):
            raise ValueError(
                f"{list_field} override must be list or tuple, got {type(val).__name__}"
            )

    # Merge metadata (base + override if metadata field was overridden)
    if "metadata" in override_map:
        override_md = override_map["metadata"].override_value
        if isinstance(override_md, dict):
            fields["metadata"] = dict(override_md)
        elif isinstance(override_md, tuple):
            fields["metadata"] = dict(override_md)
        else:
            fields["metadata"] = dict(override_md)

    # Build resolved metadata as tuple of tuples
    resolved_metadata_tuples = tuple(
        (str(k), str(v)) for k, v in fields["metadata"].items()
    )

    # Construct the resolved TaxTemplate (validation runs via __post_init__)
    try:
        resolved_template = TaxTemplate(
            country_code=fields["country_code"],
            template_name=fields["template_name"],
            tax_year=fields["tax_year"],
            cit_tiers=fields["cit_tiers"],
            depreciation_rules=fields["depreciation_rules"],
            withholding_tax_dividends=fields["withholding_tax_dividends"],
            withholding_tax_interest=fields["withholding_tax_interest"],
            loss_carryforward_years=fields["loss_carryforward_years"],
            thin_cap_ratio=fields["thin_cap_ratio"],
            interest_limitation_pct_ebitda=fields["interest_limitation_pct_ebitda"],
            metadata=resolved_metadata_tuples,
        )
    except Exception as e:
        raise ValueError(
            f"Override produced invalid resolved TaxTemplate: {e}"
        ) from e

    return ResolvedTaxConfig(
        base_template=base_template,
        overrides=tuple(overrides),
        resolved_metadata=resolved_metadata_tuples,
    )
