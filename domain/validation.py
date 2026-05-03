"""Central input validation for generic project and portfolio inputs."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ValidationIssue:
    severity: str  # "error" | "warning"
    field: str
    message: str

def validate_project_inputs(inputs) -> tuple[ValidationIssue, ...]:
    issues = []
    fin = inputs.financing
    tax = inputs.tax
    capex = inputs.capex
    info = inputs.info
    rev = inputs.revenue

    # Errors
    if hasattr(inputs.technical, 'capacity_mw') and inputs.technical.capacity_mw <= 0:
        issues.append(ValidationIssue("error", "capacity_mw", "Capacity must be positive"))
    if info.horizon_years <= 0:
        issues.append(ValidationIssue("error", "horizon_years", "Horizon years must be positive"))
    if info.construction_months < 0:
        issues.append(ValidationIssue("error", "construction_months", "Construction months cannot be negative"))
    if tax.corporate_rate < 0 or tax.corporate_rate > 1:
        issues.append(ValidationIssue("error", "corporate_rate", "Tax rate must be between 0 and 1"))
    if fin.target_dscr <= 1.0:
        issues.append(ValidationIssue("error", "target_dscr", "Target DSCR must exceed 1.0"))
    if fin.lockup_dscr <= 1.0:
        issues.append(ValidationIssue("error", "lockup_dscr", "Lockup DSCR must exceed 1.0"))
    if fin.senior_tenor_years <= 0:
        issues.append(ValidationIssue("error", "senior_tenor_years", "Senior tenor must be positive"))
    if fin.senior_tenor_years > info.horizon_years:
        issues.append(ValidationIssue("error", "senior_tenor_years", "Senior tenor cannot exceed horizon"))
    if capex.total_capex <= 0:
        issues.append(ValidationIssue("error", "capex.total_capex", "Total capex must be positive"))

    # BESS validation
    if hasattr(inputs, 'bess') and inputs.bess is not None:
        bess = inputs.bess
        bess_eff = getattr(bess, 'roundtrip_efficiency', None) or getattr(bess, 'round_trip_efficiency', None)
        if bess_eff is None or bess_eff <= 0 or bess_eff > 1:
            issues.append(ValidationIssue("error", "bess.roundtrip_efficiency", "BESS efficiency must be between 0 and 1"))
        if getattr(bess, 'cycles_per_year', 0) < 0:
            issues.append(ValidationIssue("error", "bess.cycles_per_year", "BESS cycles per year cannot be negative"))

    # Warnings
    if rev.ppa_term_years > info.horizon_years:
        issues.append(ValidationIssue("warning", "ppa_term_years", "PPA term exceeds horizon — may extend beyond project life"))
    if fin.gearing_ratio < 0 or fin.gearing_ratio > 1:
        issues.append(ValidationIssue("warning", "gearing_ratio", "Gearing ratio should be between 0 and 1"))
    if fin.shl_rate < 0:
        issues.append(ValidationIssue("warning", "shl_rate", "SHL rate cannot be negative"))
    if hasattr(inputs.technical, 'degradation') and inputs.technical.degradation < 0:
        issues.append(ValidationIssue("warning", "degradation", "Degradation cannot be negative"))
    if rev.ppa_base_tariff <= 0:
        issues.append(ValidationIssue("warning", "ppa_base_tariff", "Tariff should be positive"))

    return tuple(issues)


def validate_portfolio_inputs(inputs) -> tuple[ValidationIssue, ...]:
    issues = []

    if len(inputs.projects) < 2:
        issues.append(ValidationIssue("error", "projects", "Portfolio requires at least 2 projects"))

    codes = [p.info.code for p in inputs.projects]
    if len(codes) != len(set(codes)):
        issues.append(ValidationIssue("error", "projects", "Portfolio contains duplicate project codes"))

    if inputs.shared_financing is None:
        issues.append(ValidationIssue("error", "shared_financing", "Portfolio requires shared_financing"))

    return tuple(issues)