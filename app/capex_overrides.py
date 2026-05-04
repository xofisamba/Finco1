"""CapEx scaling helpers — proportional scaling of CapexItem line items."""
from dataclasses import replace, fields as dc_fields, is_dataclass

from domain.inputs import CapexStructure, CapexItem


def scale_capex_items(capex: CapexStructure, target_total_capex: float) -> CapexStructure:
    """Return a new CapexStructure where CapexItem amounts and financial-cost scalars
    are all scaled proportionally so the resulting total_capex equals target_total_capex.

    Only CapexItem fields and the scalar financing-cost fields (idc_keur, bank_fees_keur,
    etc.) are scaled. Commitment fees, reserve accounts, and other items that are
    not part of the hard-capex base are left unchanged.
    """
    current_total = capex.total_capex
    if current_total <= 0:
        return capex
    scale = target_total_capex / current_total

    if not is_dataclass(capex):
        return capex

    # Scalar non-CapexItem fields that contribute to total_capex_before_idc
    # (excluded: commitment_fees_keur, reserve_accounts_keur — not part of hard capex base)
    _SCALAR_CAPEX_FIELDS = (
        "idc_keur",
        "bank_fees_keur",
        "other_financial_keur",
        "vat_costs_keur",
    )

    updates = {}
    for f in dc_fields(capex):
        val = getattr(capex, f.name)
        if is_dataclass(val) and hasattr(val, 'amount_keur'):
            # It's a CapexItem — scale amount_keur
            updates[f.name] = replace(val, amount_keur=val.amount_keur * scale)
        elif f.name in _SCALAR_CAPEX_FIELDS and val:
            updates[f.name] = val * scale

    if not updates:
        return capex
    return replace(capex, **updates)
