"""Solar Validation Case 2 — higher tariff scenario."""
from app.project_factories import create_default_solar_project
from dataclasses import replace

description = "Solar PV with 10% tariff upside"

inputs = create_default_solar_project()
inputs = replace(inputs, revenue=replace(inputs.revenue, 
    ppa_base_tariff=inputs.revenue.ppa_base_tariff * 1.10))

expected_outputs = {
    "project_irr": 0.11,
}