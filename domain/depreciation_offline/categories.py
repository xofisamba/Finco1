"""Asset category registry and helpers."""

from domain.depreciation_offline.config import AssetCategoryRule, DepreciationTemplate

# -------------------------------------------------------------------
# Croatia template defaults (from Excel Inputs D358–D379)
# Main CAPEX: 20 years; financing costs (IDC/commitment/bank fees): 12 years
# -------------------------------------------------------------------

CROATIA_TEMPLATE = DepreciationTemplate(
    template_id="croatia",
    template_name="Croatia — TUHO Wind Farm",
    defaults={
        "turbines": 20,          # Production unit / turbines
        "epc": 20,               # EPC Contract
        "grid_connection": 20,   # Grid connection
        "project_rights": 20,   # Project Rights
        "idc": 12,               # IDC / Interest During Construction
        "commitment_fees": 12,   # Commitment fees
        "bank_fees": 12,         # Bank fees / arrangement fees
        "other": 20,             # Other CAPEX — conservative fallback
    },
    notes="Based on Excel Inputs D358–D379 for TUHO. "
          "Main CAPEX categories use 20-year useful life. "
          "IDC / commitment fees / bank fees use 12-year useful life.",
)


# -------------------------------------------------------------------
# Conservative fallback template (30-year straight-line)
# -------------------------------------------------------------------

DEFAULT_TEMPLATE = DepreciationTemplate(
    template_id="default",
    template_name="Default — 30-year conservative",
    defaults={
        "turbines": 30,
        "epc": 30,
        "grid_connection": 30,
        "project_rights": 30,
        "idc": 30,
        "commitment_fees": 30,
        "bank_fees": 30,
        "other": 30,
    },
    notes="Conservative fallback template. "
          "Emits DeprecationWarning when falling back to 30 years.",
)


TEMPLATE_REGISTRY = {
    "croatia": CROATIA_TEMPLATE,
    "default": DEFAULT_TEMPLATE,
}


def get_template(template_id: str) -> DepreciationTemplate:
    """Return a template by id, falling back to DEFAULT_TEMPLATE."""
    return TEMPLATE_REGISTRY.get(template_id, DEFAULT_TEMPLATE)


def build_category(
    category_id: str,
    category_name: str,
    capex_amount_keur: float,
    useful_life_years: int,
    start_period: int = 0,
    *,
    residual_value_keur: float = 0.0,
    is_financing_cost: bool = False,
    source_reference: str = "",
    frequency: str = "semiannual",
    depreciation_method: str = "straight_line",
    end_period: int | None = None,
) -> AssetCategoryRule:
    """Convenience constructor for an AssetCategoryRule."""
    return AssetCategoryRule(
        category_id=category_id,
        category_name=category_name,
        capex_amount_keur=capex_amount_keur,
        useful_life_years=useful_life_years,
        depreciation_method=depreciation_method,
        start_period=start_period,
        end_period=end_period,
        residual_value_keur=residual_value_keur,
        is_financing_cost=is_financing_cost,
        source_reference=source_reference,
        frequency=frequency,
    )