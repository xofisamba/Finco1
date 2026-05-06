"""Project inputs schema — validated DTO for custom project inputs.

Architecture:
  JSON/YAML/API request
       ↓
  ProjectInputsSchema (validation only — no business logic)
       ↓
  input_adapter.build_projectinputs()
       ↓
  existing domain ProjectInputs  (frozen dataclass)
       ↓
  run_demo_project() / waterfall runner

This module is intentionally separate from the domain layer.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import Optional


class RevenueInput(BaseModel):
    """Revenue assumptions. All fields optional — defaults come from factory."""
    tariff_eur_mwh: Optional[float] = Field(None, gt=0, description="Feed-in tariff EUR/MWh")
    p50_hours: Optional[float] = Field(None, gt=0, description="P50 annual generation hours")
    degradation_pct: Optional[float] = Field(None, ge=0, le=5, description="Annual degradation %")


class CapexInput(BaseModel):
    """CAPEX assumptions."""
    total_capex_keur: Optional[float] = Field(None, ge=0, description="Total CAPEX in kEUR")


class OpexInput(BaseModel):
    """OPEX assumptions."""
    opex_y1_keur: Optional[float] = Field(None, ge=0, description="Y1 OPEX in kEUR")
    inflation_pct: Optional[float] = Field(None, ge=0, description="Annual OPEX inflation %")


class DebtInput(BaseModel):
    """Debt / financing assumptions."""
    gearing_pct: Optional[float] = Field(None, ge=0, le=100, description="Gearing ratio %")
    senior_debt_keur: Optional[float] = Field(None, ge=0, description="Senior debt override in kEUR")
    interest_rate_pct: Optional[float] = Field(None, gt=0, description="All-in interest rate %")
    tenor_years: Optional[int] = Field(None, gt=0, description="Debt tenor in years")
    target_dscr: Optional[float] = Field(None, gt=0, description="Target DSCR")


class ProjectInputsSchema(BaseModel):
    """Root input schema for custom project definitions.

    All fields are optional — unspecified fields inherit factory defaults.
    The adapter layer (input_adapter.py) merges this schema with factory defaults.
    """
    project_type: str = "Solar"
    project_name: Optional[str] = None
    capacity_mw: Optional[float] = Field(None, gt=0, description="Capacity in MW")
    scenario: str = "Base"
    revenue: Optional[RevenueInput] = None
    capex: Optional[CapexInput] = None
    opex: Optional[OpexInput] = None
    debt: Optional[DebtInput] = None

    @field_validator('project_type')
    @classmethod
    def project_type_valid(cls, v: str) -> str:
        if v not in ("Solar", "Wind"):
            raise ValueError(f"project_type must be Solar or Wind, got '{v}'")
        return v

    @field_validator('scenario')
    @classmethod
    def scenario_valid(cls, v: str) -> str:
        if v not in ("Base", "Downside", "Upside"):
            raise ValueError(f"scenario must be Base, Downside, or Upside, got '{v}'")
        return v


class ValidateRequest(BaseModel):
    """API request body for /validate endpoint."""
    inputs: ProjectInputsSchema


class ValidateResponse(BaseModel):
    """API response body for /validate endpoint."""
    valid: bool
    errors: list[str]
    warnings: list[str] = []
